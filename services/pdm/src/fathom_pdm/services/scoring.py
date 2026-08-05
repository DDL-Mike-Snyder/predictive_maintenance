"""Bulk, idempotent, baseline-fenced prediction ingest. Document 22-pdm.md
§11.3, 09 §4.1: this is the ONLY layer that opens a transaction and the
ONLY layer that calls the outbox.

01 §3 correction 2 / 09 §9 item 1: this is the operation Domino scoring
Jobs write through -- a Domino Job is an HTTP client of this API (via the
gateway, per 09 §4.4.2's sanctioned `domino-compute -> gateway` edge), never
a direct database client.
"""

from __future__ import annotations

import datetime as dt
import uuid

from fathom_schemas import CALIBRATION_POPULATION_FLOOR, ClassificationLabel, FailurePrediction
from fathom_sync import OutboxWriter, UnitOfWork

from fathom_pdm.events.publishers import publish_prediction_updated
from fathom_pdm.models import Prediction, PredictionProvenance, ScoringRun
from fathom_pdm.repositories.prediction import PredictionRepository


class ScoringRunNotFoundError(Exception):
    pass


class ScoringRunFencedOutError(Exception):
    """D3: the baseline moved underneath the run. The result is correctly
    refused at publication -- `fenced_out` is a first-class terminal status,
    not a failure."""


async def create_scoring_run(
    uow: UnitOfWork,
    *,
    stratum: str,
    scope: dict[str, object],
    classification: ClassificationLabel,
) -> ScoringRun:
    """22-pdm.md §10's on-demand re-score (`POST /scoring-runs`). Mints a
    `queued` row for whatever later triggers the real Domino Job -- this
    operation does not itself invoke Domino; that orchestration is out of
    scope for this vertical slice, the same boundary
    `services/model_binding.py`'s own `rescore_run` already documents.
    `model_bindings`/`label_set_ids` stay empty: which bindings actually
    serve this run is resolved by the scoring process itself once a real
    Job runs against this row, not knowable at request time.
    """
    now = dt.datetime.now(dt.UTC)
    scoring_run = ScoringRun(
        stratum=stratum,
        trigger="on_demand",
        scope=scope,
        # [PLACEHOLDER] same boundary as every other queued scoring_run in
        # this vertical slice (see services/model_binding.py's own
        # rescore_run) -- real baseline/read-model-lag snapshots come from
        # configuration/read-model infrastructure this slice doesn't build.
        baseline_epoch_at_start={},
        model_bindings=[],
        label_set_ids=[],
        feature_definition_time=now,
        domino_execution_ref="queued",
        read_model_lag_at_start={},
        status="queued",
        classification=classification.wire_dict(),
    )
    uow.session.add(scoring_run)
    await uow.session.flush()
    return scoring_run


_SERVING_CLASS_BY_STRATUM = {
    "operational": "actionable",
    "holdout_research": "research_only",
}


async def bulk_ingest_predictions(
    uow: UnitOfWork,
    outbox: OutboxWriter,
    prediction_repo: PredictionRepository,
    *,
    scoring_run: ScoringRun,
    predictions: list[FailurePrediction],
    classification: ClassificationLabel,
    current_baseline_epoch: int,
) -> tuple[int, int, list[str]]:
    """Returns (written, rejected, rejection_reasons).

    `serving_class` is written by this operation from `scoring_run.stratum`
    -- the wire request schema does NOT contain the field; a caller cannot
    set it, override it, or observe it except through the projection their
    credential permits (§4.5).
    """
    session = uow.session

    # D3: baseline fencing. A prediction computed against a baseline_epoch
    # behind the current one is fenced out at ingest, not silently accepted.
    if any(p.baseline_epoch < current_baseline_epoch for p in predictions):
        raise ScoringRunFencedOutError(
            f"scoring_run {scoring_run.scoring_run_id} computed against a baseline "
            f"epoch behind the current one ({current_baseline_epoch})"
        )

    serving_class = _SERVING_CLASS_BY_STRATUM[scoring_run.stratum]

    written = 0
    rejected = 0
    rejection_reasons: list[str] = []
    reference_classes: set[str] = set()
    last_asset_id: uuid.UUID | None = None
    last_installed_item_id: uuid.UUID | None = None

    for pred in predictions:
        # The schema's own validators (_rul_only_when_item_conditional,
        # _calibration_gate) already enforce D19/06 §3 at construction time;
        # the database's CHECK constraints are the second, independent
        # enforcement layer (defense in depth, not redundancy for its own sake).
        provenance = PredictionProvenance(
            scoring_run_id=scoring_run.scoring_run_id,
            model_binding_id=uuid.uuid4(),  # [PLACEHOLDER] real binding resolution, §5.6
            label_set_id=uuid.uuid4(),  # [PLACEHOLDER]
            gate_decision={
                "cell_key": {
                    "tier": pred.tier,
                    "equipment_family": pred.equipment_family,
                    "reference_class": pred.reference_class.value,
                },
                "n": pred.calibration_population,
                "gate_passed": (pred.calibration_population or 0) >= CALIBRATION_POPULATION_FLOOR,
            },
            feature_observations={},
            feature_definition_time=pred.computed_at,
            fallback_path={"level": pred.fallback_level},
            suppressed_factors=[],
            read_model_lag={},
            classification=classification.wire_dict(),
        )
        session.add(provenance)
        await session.flush()

        row = Prediction(
            scoring_run_id=scoring_run.scoring_run_id,
            asset_id=pred.asset_id,
            installed_item_id=pred.installed_item_id,
            position_id=pred.position_id,
            niin=pred.niin,
            equipment_family=pred.equipment_family,
            baseline_id=pred.baseline_id,
            baseline_epoch=pred.baseline_epoch,
            horizon_days=pred.horizon_days,
            p_failure=pred.p_failure,
            reference_class=pred.reference_class.value,
            sharpness=pred.sharpness,
            calibration_population=pred.calibration_population,
            rul=pred.rul.wire_dict() if pred.rul else None,
            population_hazard_rate=pred.population_hazard_rate,
            confidence=pred.confidence,
            fallback_level=pred.fallback_level,
            tier=pred.tier,
            contributing_factors=[f.wire_dict() for f in pred.contributing_factors],
            model_version=pred.model_version,
            computed_at=pred.computed_at,
            serving_class=serving_class,
            provenance_id=provenance.provenance_id,
            classification=classification.wire_dict(),
        )
        await prediction_repo.insert(session, row)
        written += 1
        reference_classes.add(pred.reference_class.value)
        last_asset_id = pred.asset_id
        last_installed_item_id = pred.installed_item_id

    scoring_run.predictions_written = written
    scoring_run.predictions_rejected = rejected
    scoring_run.status = "published"
    scoring_run.completed_at = dt.datetime.now(dt.UTC)

    if written > 0 and last_asset_id is not None and last_installed_item_id is not None:
        now = dt.datetime.now(dt.UTC)
        await publish_prediction_updated(
            outbox,
            uow,
            scoring_run_id=scoring_run.scoring_run_id,
            asset_id=last_asset_id,
            installed_item_id=last_installed_item_id,
            baseline_epoch=current_baseline_epoch,
            predictions_written=written,
            reference_class_summary=tuple(sorted(reference_classes)),
            classification=classification,
            occurred_at=now,
            recorded_at=now,
        )

    return written, rejected, rejection_reasons
