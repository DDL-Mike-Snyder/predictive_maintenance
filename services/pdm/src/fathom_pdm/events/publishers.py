"""Domain fact -> outbox row, via `packages/py-sync`. Called from
`services/`, inside the caller's transaction (03 §5.2). Document 09 §4.2.
"""

from __future__ import annotations

import uuid

from fathom_schemas import ClassificationLabel, EventScope, EventSubject, FathomModel
from fathom_sync import EventId, OutboxWriter, UnitOfWork


class ModelBindingActivated(FathomModel):
    """22-pdm.md §5.6: "publishes `model_binding.activated` with the
    binding, the approval reference, and the `label_set_id` and
    `propensity_model_id` the model was fitted on." Consumers are `audit`
    and `fleet-status` (03 §6) -- neither exists as code yet; see this
    module's own `[NOTE]` on `PredictionUpdated` for the same scoping
    caveat, which applies identically here."""

    binding_id: uuid.UUID
    tier: int
    equipment_family: str
    taxonomy_version: str
    registry_model_version: str
    registry_model_uri: str
    approval_ref: str
    label_set_id: uuid.UUID
    propensity_model_id: uuid.UUID | None


async def publish_model_binding_activated(
    outbox: OutboxWriter,
    uow: UnitOfWork,
    *,
    binding_id: uuid.UUID,
    tier: int,
    equipment_family: str,
    taxonomy_version: str,
    registry_model_version: str,
    registry_model_uri: str,
    approval_ref: str,
    label_set_id: uuid.UUID,
    propensity_model_id: uuid.UUID | None,
    classification: ClassificationLabel,
    occurred_at,
    recorded_at,
) -> EventId:
    payload = ModelBindingActivated(
        binding_id=binding_id,
        tier=tier,
        equipment_family=equipment_family,
        taxonomy_version=taxonomy_version,
        registry_model_version=registry_model_version,
        registry_model_uri=registry_model_uri,
        approval_ref=approval_ref,
        label_set_id=label_set_id,
        propensity_model_id=propensity_model_id,
    )
    return await outbox.emit(
        uow,
        event_type="fathom.pdm.model_binding.activated",
        event_version=1,
        aggregate="model_binding",
        aggregate_id=str(binding_id),
        topic="fathom.pdm.model_binding.v1",
        scope=EventScope.FLEET,
        subject=EventSubject(),
        payload=payload,
        classification=classification,
        source_time=occurred_at,
        recorded_at=recorded_at,
        occurred_at=occurred_at,
        # D5: compaction key is the aggregate key (the binding), never the
        # partition key -- FLEET scope's partition key is the constant
        # "fleet", so this can never collide with it (D5's own check), but
        # naming it explicitly still says what's being compacted on.
        compaction_key=str(binding_id),
    )


class PredictionUpdated(FathomModel):
    """[NOTE] The full spec (03 §5.5) wants every event payload defined in
    `packages/canonical-schemas` for schema-registry compatibility checking.
    Scoped locally to this service for this vertical slice -- move to
    canonical-schemas before this catalog entry is treated as conformant.

    D27: references the run artifact rather than inlining every prediction
    -- an event carrying N predictions inline could exceed the broker
    message limit, and per-item detail is already queryable via
    `GET /predictions?scoring_run_id=`.
    """

    scoring_run_id: uuid.UUID
    predictions_written: int
    reference_class_summary: tuple[str, ...]


async def publish_prediction_updated(
    outbox: OutboxWriter,
    uow: UnitOfWork,
    *,
    scoring_run_id: uuid.UUID,
    asset_id: uuid.UUID,
    installed_item_id: uuid.UUID,
    baseline_epoch: int,
    predictions_written: int,
    reference_class_summary: tuple[str, ...],
    classification: ClassificationLabel,
    occurred_at,
    recorded_at,
) -> EventId:
    payload = PredictionUpdated(
        scoring_run_id=scoring_run_id,
        predictions_written=predictions_written,
        reference_class_summary=reference_class_summary,
    )
    return await outbox.emit(
        uow,
        event_type="fathom.pdm.prediction.updated",
        event_version=1,
        aggregate="prediction",
        aggregate_id=str(scoring_run_id),
        topic="fathom.pdm.prediction.v1",
        scope=EventScope.INSTALLED_ITEM,
        subject=EventSubject(installed_item_id=installed_item_id, asset_id=asset_id),
        payload=payload,
        classification=classification,
        baseline_epoch=baseline_epoch,
        source_time=occurred_at,
        recorded_at=recorded_at,
        occurred_at=occurred_at,
        # D5: compaction key is the aggregate key (the item), never the
        # partition key (the asset) -- compacting on asset_id would collapse
        # a hull's entire prediction history to one record.
        compaction_key=str(installed_item_id),
    )
