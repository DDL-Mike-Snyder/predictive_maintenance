"""Domain fact -> outbox row, via `packages/py-sync`. Called from
`services/`, inside the caller's transaction (03 §5.2). Document 09 §4.2.
"""

from __future__ import annotations

import uuid

from fathom_schemas import ClassificationLabel, EventScope, EventSubject, FathomModel
from fathom_sync import EventId, OutboxWriter, UnitOfWork


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
