"""`/api/v1/pdm/scoring-runs`. Document 22-pdm.md §10 (line ~1356).
`POST /scoring-runs/{id}/predictions` (bulk ingest) lives in predictions.py
-- this file owns the scoring_run resource itself. HTTP shape only -- never
touches a session directly beyond what `deps.py` hands it, never emits SQL
(09 §4.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fathom_contracts import SideEffects, Substitution, operation_extra
from fathom_py_common import persist_idempotent_response
from fathom_schemas import ClassificationLabel, ClassificationLevel
from fathom_sync import UnitOfWork

from fathom_pdm.deps import Principal, current_principal, get_uow
from fathom_pdm.models import ScoringRun
from fathom_pdm.schemas.scoring_run import CreateScoringRunRequest, ScoringRunResponse
from fathom_pdm.services import scoring as scoring_service

router = APIRouter()


def _to_response(scoring_run: ScoringRun) -> ScoringRunResponse:
    return ScoringRunResponse(
        scoring_run_id=scoring_run.scoring_run_id,
        stratum=scoring_run.stratum,
        trigger=scoring_run.trigger,
        scope=scoring_run.scope,
        status=scoring_run.status,
        feature_definition_time=scoring_run.feature_definition_time,
    )


@router.post(
    "/scoring-runs",
    response_model=ScoringRunResponse,
    status_code=201,
    openapi_extra=operation_extra(
        operation_id="pdm_create_scoring_run",
        substitution=Substitution.REQUIRED,
        side_effects=SideEffects.NONE,
        agent_eligible=True,
        summary="On-demand re-score. Computes; does not alter domain state (04 §4).",
        idempotency_required=True,
    ),
)
async def create_scoring_run(
    *,
    request: Request,
    body: CreateScoringRunRequest,
    _principal: Principal = Depends(current_principal),
    uow: UnitOfWork = Depends(get_uow),
) -> ScoringRunResponse:
    # [PLACEHOLDER] real classification derives from the union of the
    # requested scope's own installed-item classification (03 §7.3);
    # matches services/scoring.py's own placeholder for this vertical slice.
    classification = ClassificationLabel(level=ClassificationLevel.U)

    scoring_run = await scoring_service.create_scoring_run(
        uow, stratum=body.stratum, scope=body.scope, classification=classification
    )
    result = _to_response(scoring_run)
    # Same transaction the row was created in (09 §5.3's storage rule) --
    # `uow.session` and the middleware's `request.state.db_session` are the
    # same object here, same as predictions.py's own bulk_ingest.
    await persist_idempotent_response(request, result.wire_dict(), 201)
    return result
