"""Model-registry binding creation and activation. Document 22-pdm.md §5.6,
§8.1, §8.2. 09 §4.1: this is the ONLY layer that opens a transaction and the
ONLY layer that calls the outbox -- mirrors `services/scoring.py`'s own
boundary.

"PdM does not promote, does not gate promotion, and does not host a
`promote` operation... PdM's contribution to that pipeline is the
**binding refusal**... Those are checks on PdM's own aggregates and are
enforceable here." (§5.6) -- the three refusal checks below are
deliberately scoped to `propensity_model`/`calibration_record`, never to a
live call against Domino's own Model Registry API: PdM records a registry
version, it never mints or validates one (03 §14).
"""

from __future__ import annotations

import datetime as dt
import uuid

from fathom_schemas import ClassificationLabel
from fathom_sync import OutboxWriter, UnitOfWork

from fathom_pdm.events.publishers import publish_model_binding_activated
from fathom_pdm.models import ModelBinding, ScoringRun
from fathom_pdm.repositories.model_binding import ModelBindingRepository
from fathom_pdm.repositories.prediction import PredictionRepository

# §2.2: the only value the `censoring_correction` CHECK constraint permits.
# A binding always records this -- not a caller-supplied field (D1 reintroduced
# is exactly what a wider value would mean; see the model's own docstring).
_CENSORING_CORRECTION = "ipcw_stabilized"


class BindingNotFoundError(Exception):
    pass


class BindingAlreadyActivatedError(Exception):
    pass


class BindingRefusedError(Exception):
    """§5.6's binding refusal. `reason` is one of `unaccepted_propensity_model`,
    `unpowered_label_set_family`, `no_calibration_record`."""

    def __init__(self, reason: str, detail: str) -> None:
        self.reason = reason
        super().__init__(detail)


async def create_binding(
    uow: UnitOfWork,
    repo: ModelBindingRepository,
    *,
    tier: int,
    equipment_family: str,
    taxonomy_version: str,
    registry_model_version: str,
    registry_model_uri: str,
    approval_ref: str,
    label_set_id: uuid.UUID,
) -> ModelBinding:
    """A draft, unactivated binding -- `activated_at`/`deactivated_at` both
    NULL. Not yet in effect; `activate_binding` is the state-changing step
    §5.6's refusal logic guards."""
    binding = ModelBinding(
        tier=tier,
        equipment_family=equipment_family,
        taxonomy_version=taxonomy_version,
        registry_model_version=registry_model_version,
        registry_model_uri=registry_model_uri,
        approval_ref=approval_ref,
        label_set_id=label_set_id,
        censoring_correction=_CENSORING_CORRECTION,
    )
    await repo.insert(uow.session, binding)
    return binding


async def activate_binding(
    uow: UnitOfWork,
    outbox: OutboxWriter,
    binding_repo: ModelBindingRepository,
    prediction_repo: PredictionRepository,
    *,
    binding_id: uuid.UUID,
    classification: ClassificationLabel,
) -> ModelBinding:
    """§5.6's binding refusal, then (on success) the three effects the spec
    ties to activation: deactivate and re-score-queue the superseded binding
    (§8.1's `binding_deactivated` invalidation trigger), activate this one,
    publish `model_binding.activated`."""
    session = uow.session
    binding = await binding_repo.get_by_id(session, binding_id)
    if binding is None:
        raise BindingNotFoundError(str(binding_id))
    if binding.activated_at is not None:
        raise BindingAlreadyActivatedError(str(binding_id))

    label_set = await binding_repo.get_label_set(session, binding.label_set_id)
    propensity_model_id = label_set.propensity_model_id if label_set is not None else None
    propensity_model = (
        await binding_repo.get_propensity_model(session, propensity_model_id)
        if propensity_model_id is not None
        else None
    )
    if propensity_model is None or not propensity_model.accepted:
        raise BindingRefusedError(
            "unaccepted_propensity_model",
            f"binding {binding_id}'s label set {binding.label_set_id} has no "
            "accepted propensity model",
        )

    if not await binding_repo.powered_calibration_exists_for_family(
        session, binding.equipment_family
    ):
        raise BindingRefusedError(
            "unpowered_label_set_family",
            f"no powered calibration record exists for family {binding.equipment_family!r}",
        )

    if not await binding_repo.calibration_exists_for_triple(
        session,
        tier=binding.tier,
        equipment_family=binding.equipment_family,
        taxonomy_version=binding.taxonomy_version,
    ):
        raise BindingRefusedError(
            "no_calibration_record",
            f"no calibration record exists for (tier={binding.tier}, "
            f"equipment_family={binding.equipment_family!r}, "
            f"taxonomy_version={binding.taxonomy_version!r})",
        )

    now = dt.datetime.now(dt.UTC)

    previous = await binding_repo.get_active_for_triple(
        session,
        tier=binding.tier,
        equipment_family=binding.equipment_family,
        taxonomy_version=binding.taxonomy_version,
    )
    if previous is not None:
        previous.deactivated_at = now
        superseded_predictions = await prediction_repo.get_all_active_for_model_binding(
            session, model_binding_id=previous.binding_id
        )
        for prediction in superseded_predictions:
            await prediction_repo.invalidate(
                session, prediction.prediction_id, cause="binding_deactivated"
            )

        rescore_run = ScoringRun(
            stratum="operational",
            trigger="binding_activation",
            scope={"tier": binding.tier, "equipment_family": binding.equipment_family},
            # [PLACEHOLDER] real baseline/read-model-lag snapshots come from
            # the configuration/read-model infrastructure this vertical
            # slice doesn't build (same boundary as services/scoring.py's
            # own placeholders) -- this run is queued, not executed, here.
            baseline_epoch_at_start={},
            # str(...), not the raw UUID: `ScoringRun.model_bindings`'s
            # SQLite variant is a plain JSON column, and the stdlib JSON
            # encoder cannot serialize a `uuid.UUID` -- a gap this is the
            # first code path to hit, since every prior test left these two
            # array columns empty. SQLAlchemy's `UUID(as_uuid=True)` bind
            # processor accepts a string on the real-Postgres path too, so
            # this is portable, not a SQLite-only workaround.
            model_bindings=[str(binding.binding_id)],
            label_set_ids=[str(binding.label_set_id)],
            feature_definition_time=now,
            domino_execution_ref="queued",
            read_model_lag_at_start={},
            status="queued",
            classification=classification.wire_dict(),
        )
        session.add(rescore_run)
        await session.flush()

    binding.activated_at = now

    await publish_model_binding_activated(
        outbox,
        uow,
        binding_id=binding.binding_id,
        tier=binding.tier,
        equipment_family=binding.equipment_family,
        taxonomy_version=binding.taxonomy_version,
        registry_model_version=binding.registry_model_version,
        registry_model_uri=binding.registry_model_uri,
        approval_ref=binding.approval_ref,
        label_set_id=binding.label_set_id,
        propensity_model_id=propensity_model_id,
        classification=classification,
        occurred_at=now,
        recorded_at=now,
    )

    return binding
