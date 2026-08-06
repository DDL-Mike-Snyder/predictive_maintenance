"""`/api/v1/pdm/predictions*`, `/api/v1/pdm/scoring-runs/*`. Document
22-pdm.md §11.3. HTTP shape only -- never touches a session directly beyond
what `deps.py` hands it, never emits SQL (09 §4.1)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fathom_contracts import SideEffects, Substitution, operation_extra
from fathom_py_common import ProblemException, persist_idempotent_response
from fathom_schemas import ClassificationLabel, ClassificationLevel
from fathom_sync import OutboxWriter, UnitOfWork
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fathom_pdm.deps import Principal, current_principal, get_outbox_writer, get_session, get_uow
from fathom_pdm.models import Prediction, ScoringRun
from fathom_pdm.repositories.prediction import PredictionRepository
from fathom_pdm.schemas.prediction import BulkPredictionIngestRequest, BulkPredictionIngestResult
from fathom_pdm.services.scoring import ScoringRunFencedOutError, bulk_ingest_predictions

router = APIRouter()

_prediction_repo = PredictionRepository()


def _serialize_prediction(row: Prediction) -> dict[str, object]:
    """Shared by `get_prediction` and `list_predictions` -- 51-operator-
    console.md §11.3/§11.5's own column and deep-dive field lists, all of
    which already exist on the model; this just stops truncating them on
    the wire. `status`/`serving_class` are intentionally NOT both exposed
    verbatim per §11.3's own rule (`serving_class` never rendered) --
    `serving_class` is checked, never returned."""
    return {
        "prediction_id": str(row.prediction_id),
        "asset_id": str(row.asset_id),
        "installed_item_id": str(row.installed_item_id),
        "niin": row.niin,
        "equipment_family": row.equipment_family,
        "reference_class": row.reference_class,
        "p_failure": float(row.p_failure) if row.p_failure is not None else None,
        "population_hazard_rate": (
            float(row.population_hazard_rate) if row.population_hazard_rate is not None else None
        ),
        "calibration_population": row.calibration_population,
        "confidence": float(row.confidence),
        "sharpness": float(row.sharpness),
        "fallback_level": row.fallback_level,
        "tier": row.tier,
        "horizon_days": row.horizon_days,
        "rul": row.rul,
        "contributing_factors": row.contributing_factors,
        "model_version": row.model_version,
        "computed_at": row.computed_at.isoformat(),
        "status": row.status,
    }


@router.post(
    "/scoring-runs/{scoring_run_id}/predictions",
    response_model=BulkPredictionIngestResult,
    status_code=202,
    openapi_extra=operation_extra(
        operation_id="pdm_bulk_ingest_predictions",
        substitution=Substitution.REQUIRED,
        side_effects=SideEffects.STATE_CHANGING,
        summary=(
            "Bulk, idempotent, baseline-fenced prediction ingest -- the Domino scoring "
            "Job write path."
        ),
        aggregate="prediction",
    ),
)
async def bulk_ingest(
    *,
    request: Request,
    scoring_run_id: uuid.UUID,
    body: BulkPredictionIngestRequest,
    _principal: Principal = Depends(current_principal),
    session: AsyncSession = Depends(get_session),
    uow: UnitOfWork = Depends(get_uow),
    outbox: OutboxWriter = Depends(get_outbox_writer),
) -> BulkPredictionIngestResult:
    scoring_run = (
        await session.execute(select(ScoringRun).where(ScoringRun.scoring_run_id == scoring_run_id))
    ).scalar_one_or_none()
    if scoring_run is None:
        raise ProblemException(
            type="urn:fathom:problem:pdm:scoring-run-not-found",
            title="Scoring run not found",
            status=404,
        )

    # [PLACEHOLDER] real classification derives from the union of each
    # item's own installed-item classification (03 §7.3); a single U label
    # stands in for this vertical slice.
    classification = ClassificationLabel(level=ClassificationLevel.U)

    try:
        written, rejected, reasons = await bulk_ingest_predictions(
            uow,
            outbox,
            _prediction_repo,
            scoring_run=scoring_run,
            predictions=list(body.predictions),
            classification=classification,
            # [PLACEHOLDER] real current_baseline_epoch comes from the
            # configuration read model fed by configuration.baseline_changed.
            current_baseline_epoch=scoring_run.baseline_epoch_at_start.get("_all_", 0)
            if isinstance(scoring_run.baseline_epoch_at_start, dict)
            else 0,
        )
    except ScoringRunFencedOutError as exc:
        scoring_run.status = "fenced_out"
        raise ProblemException(
            type="urn:fathom:problem:pdm:baseline-superseded",
            title="Prediction baseline is superseded",
            status=409,
            detail=str(exc),
        ) from exc

    result = BulkPredictionIngestResult(
        scoring_run_id=scoring_run_id,
        predictions_written=written,
        predictions_rejected=rejected,
        rejection_summary=tuple(reasons),
    )
    # Same transaction the domain effect committed in (09 §5.3's storage
    # rule) -- `uow.session` and `session` are the same object here.
    await persist_idempotent_response(request, result.wire_dict(), 202)
    return result


@router.get(
    "/predictions/{prediction_id}",
    openapi_extra=operation_extra(
        operation_id="pdm_get_prediction",
        substitution=Substitution.REQUIRED,
        side_effects=SideEffects.NONE,
        summary="One prediction.",
        aggregate="prediction",
    ),
)
async def get_prediction(
    prediction_id: uuid.UUID,
    _principal: Principal = Depends(current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    row = await _prediction_repo.get_by_id(session, prediction_id)
    if row is None or row.serving_class != "actionable":
        # 22-pdm.md §11.3: 404 + prediction-not-actionable for a research
        # prediction -- RLS already makes the row invisible to this
        # connection's role if it's research_only; this second check is
        # defense in depth against a future refactor that queries as a
        # broader-privileged role by mistake.
        raise ProblemException(
            type="urn:fathom:problem:pdm:prediction-not-actionable",
            title="Prediction not found or not actionable",
            status=404,
        )
    return _serialize_prediction(row)


@router.get(
    "/predictions",
    openapi_extra=operation_extra(
        operation_id="pdm_list_predictions",
        substitution=Substitution.REQUIRED,
        side_effects=SideEffects.NONE,
        summary="Active predictions, filtered. Never accepts min_probability (51 §11.2).",
        aggregate="prediction",
    ),
)
async def list_predictions(
    *,
    asset_id: uuid.UUID | None = None,
    installed_item_id: uuid.UUID | None = None,
    niin: str | None = None,
    equipment_family: str | None = None,
    reference_class: str | None = None,
    limit: int = 50,
    _principal: Principal = Depends(current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    rows = await _prediction_repo.list_active(
        session,
        asset_id=asset_id,
        installed_item_id=installed_item_id,
        niin=niin,
        equipment_family=equipment_family,
        reference_class=reference_class,
        limit=limit,
    )
    # research_only rows are already invisible to fathom_pdm_serving (RLS);
    # this second filter is the same defense-in-depth get_prediction's own
    # comment already establishes for the by-id case.
    return {
        "predictions": [
            _serialize_prediction(row) for row in rows if row.serving_class == "actionable"
        ]
    }
