"""Marc's file: the "action" endpoints that run the actual gate/costing
pipeline -- docs/demo/redesign-case-builder-demo-plan.md, "Marc" section.
Implements the real gate logic (§1.4, from docs/build/28-design-advisory.md
§5.2-§5.4) and the draft->assemble->propose lifecycle of a redesign_case
(28 §3.6). This is the one file Marc owns in the shared
`services/design-advisory` skeleton -- it imports
`fathom_design_advisory.models`/`db` (Paul's) and nothing else in this
package."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fathom_design_advisory.config import Settings
from fathom_design_advisory.db import get_session_dependency, get_settings_dependency
from fathom_design_advisory.models import (
    CostEstimate,
    FailureDossier,
    GateDecision,
    ImpactSnapshot,
    RedesignCandidate,
    RedesignCase,
)

router = APIRouter(prefix="/api/v1/design-advisory", tags=["design-advisory:actions"])


def _row_to_dict(row: object) -> dict:
    return {c.key: getattr(row, c.key) for c in row.__table__.columns}  # type: ignore[attr-defined]


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def _get_candidate_or_404(session: AsyncSession, candidate_id: str) -> RedesignCandidate:
    candidate = await session.get(RedesignCandidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"no redesign_candidate {candidate_id}")
    return candidate


async def _get_dossier_for_candidate_or_404(
    session: AsyncSession, candidate: RedesignCandidate
) -> FailureDossier:
    if candidate.dossier_id is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"candidate {candidate.candidate_id} has no dossier_id set -- "
                "seed data isn't linked yet"
            ),
        )
    dossier = await session.get(FailureDossier, candidate.dossier_id)
    if dossier is None:
        raise HTTPException(
            status_code=404, detail=f"no failure_dossier {candidate.dossier_id}"
        )
    return dossier


async def _get_impact_snapshot_for_candidate_or_404(
    session: AsyncSession, candidate_id: str
) -> ImpactSnapshot:
    stmt = select(ImpactSnapshot).where(ImpactSnapshot.candidate_id == candidate_id)
    snapshot = (await session.execute(stmt)).scalars().first()
    if snapshot is None:
        raise HTTPException(
            status_code=404, detail=f"no impact_snapshot for candidate {candidate_id}"
        )
    return snapshot


async def _get_parametric_estimate_for_candidate_or_404(
    session: AsyncSession, candidate_id: str
) -> CostEstimate:
    stmt = select(CostEstimate).where(
        CostEstimate.candidate_id == candidate_id, CostEstimate.method == "parametric"
    )
    estimate = (await session.execute(stmt)).scalars().first()
    if estimate is None:
        raise HTTPException(
            status_code=404,
            detail=f"no parametric cost_estimate for candidate {candidate_id}",
        )
    return estimate


# ---------------------------------------------------------------------------
# 1. Parametric estimate -- [SIMPLIFIED] the seed script already created
#    this row; this endpoint looks it up and returns it (idempotent).
# ---------------------------------------------------------------------------


@router.post("/redesign-candidates/{candidate_id}/parametric-estimate")
async def parametric_estimate(
    candidate_id: str, session: AsyncSession = Depends(get_session_dependency)
) -> dict:
    await _get_candidate_or_404(session, candidate_id)
    estimate = await _get_parametric_estimate_for_candidate_or_404(session, candidate_id)
    return _row_to_dict(estimate)


# ---------------------------------------------------------------------------
# 2. Gate evaluation -- the real logic, §1.4.
# ---------------------------------------------------------------------------


def _evaluate_gate_conditions(
    *,
    candidate: RedesignCandidate,
    dossier: FailureDossier,
    impact_snapshot: ImpactSnapshot,
    cost_estimate: CostEstimate,
    settings: Settings,
) -> tuple[dict[str, bool], list[str]]:
    g1 = cost_estimate.point_estimate_usd >= settings.gate_cost_floor_usd
    g2 = candidate.priority_score >= settings.gate_priority_floor
    g3 = impact_snapshot.completeness_ratio >= settings.gate_completeness_floor
    g4 = not any(
        row.get("record_status") == "absent_unknown" for row in dossier.test_coverage
    )
    g5 = dossier.field_failure_count >= settings.gate_field_failure_floor or any(
        citation.get("posture") == "supporting"
        and citation.get("adjudication_state") == "published"
        for citation in dossier.causal_citations
    )
    g6 = candidate.status in {"identified", "qualifying", "gate_passed", "gate_failed"}

    condition_results = {
        "G1_cost_floor": g1,
        "G2_priority_floor": g2,
        "G3_completeness_floor": g3,
        "G4_test_coverage_assessed": g4,
        "G5_evidentiary_floor": g5,
        "G6_state_consistency": g6,
    }
    failed_conditions = [name for name, passed in condition_results.items() if not passed]
    return condition_results, failed_conditions


@router.post("/redesign-candidates/{candidate_id}/evaluate-gate")
async def evaluate_gate(
    candidate_id: str,
    session: AsyncSession = Depends(get_session_dependency),
    settings: Settings = Depends(get_settings_dependency),
) -> dict:
    candidate = await _get_candidate_or_404(session, candidate_id)
    dossier = await _get_dossier_for_candidate_or_404(session, candidate)
    impact_snapshot = await _get_impact_snapshot_for_candidate_or_404(session, candidate_id)
    cost_estimate = await _get_parametric_estimate_for_candidate_or_404(session, candidate_id)

    condition_results, failed_conditions = _evaluate_gate_conditions(
        candidate=candidate,
        dossier=dossier,
        impact_snapshot=impact_snapshot,
        cost_estimate=cost_estimate,
        settings=settings,
    )
    decision = "pass" if not failed_conditions else "fail"

    gate_decision = GateDecision(
        gate_decision_id=str(uuid.uuid4()),
        candidate_id=candidate_id,
        dossier_id=dossier.dossier_id,
        impact_snapshot_id=impact_snapshot.impact_snapshot_id,
        decision=decision,
        condition_results=condition_results,
        failed_conditions=failed_conditions,
        thresholds_in_force={
            "GATE_COST_FLOOR_USD": settings.gate_cost_floor_usd,
            "GATE_PRIORITY_FLOOR": settings.gate_priority_floor,
            "GATE_COMPLETENESS_FLOOR": settings.gate_completeness_floor,
            "GATE_FIELD_FAILURE_FLOOR": settings.gate_field_failure_floor,
        },
        gate_policy_version="v0-demo-placeholder",
        computed_at=_now(),
    )
    session.add(gate_decision)

    candidate.status = "gate_passed" if decision == "pass" else "gate_failed"

    await session.commit()
    return _row_to_dict(gate_decision)


# ---------------------------------------------------------------------------
# 3. Create a draft redesign_case.
# ---------------------------------------------------------------------------


class CreateCaseRequest(BaseModel):
    candidate_id: str


@router.post("/redesign-cases")
async def create_case(
    body: CreateCaseRequest, session: AsyncSession = Depends(get_session_dependency)
) -> dict:
    candidate = await _get_candidate_or_404(session, body.candidate_id)
    if candidate.dossier_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"candidate {candidate.candidate_id} has no dossier_id set",
        )

    existing_stmt = select(RedesignCase).where(
        RedesignCase.candidate_id == body.candidate_id,
        RedesignCase.case_status != "withdrawn",
    )
    existing = (await session.execute(existing_stmt)).scalars().first()
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                f"a non-withdrawn redesign_case ({existing.case_id}) already exists "
                f"for candidate {body.candidate_id}"
            ),
        )

    case = RedesignCase(
        case_id=str(uuid.uuid4()),
        candidate_id=body.candidate_id,
        dossier_id=candidate.dossier_id,
        case_version=1,
        case_status="draft",
    )
    session.add(case)
    await session.commit()
    return _row_to_dict(case)


# ---------------------------------------------------------------------------
# 4. Assemble -- the real precondition (gate must have passed) plus every
#    field 28 §3.6's assembled_is_complete constraints require.
# ---------------------------------------------------------------------------


class AssembleCaseRequest(BaseModel):
    recommendation_stance: str
    recommendation_limitations: list[str]
    recommendation_evidence_gaps: list[str]
    narrative_sections: list[dict[str, str]]


async def _get_latest_gate_decision(
    session: AsyncSession, candidate_id: str
) -> GateDecision | None:
    stmt = (
        select(GateDecision)
        .where(GateDecision.candidate_id == candidate_id)
        .order_by(GateDecision.computed_at.desc())
    )
    return (await session.execute(stmt)).scalars().first()


def _test_coverage_summary(test_coverage: list[dict[str, Any]]) -> dict[str, Any]:
    by_record_status: dict[str, int] = {}
    for row in test_coverage:
        record_status = row.get("record_status", "unknown")
        by_record_status[record_status] = by_record_status.get(record_status, 0) + 1
    return {
        "by_record_status": by_record_status,
        "absent_unknown_count": by_record_status.get("absent_unknown", 0),
    }


@router.post("/redesign-cases/{case_id}/assemble")
async def assemble_case(
    case_id: str,
    body: AssembleCaseRequest,
    session: AsyncSession = Depends(get_session_dependency),
) -> dict:
    case = await session.get(RedesignCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"no redesign_case {case_id}")

    gate_decision = await _get_latest_gate_decision(session, case.candidate_id)
    if gate_decision is None or gate_decision.decision != "pass":
        raise HTTPException(
            status_code=409,
            detail=(
                f"candidate {case.candidate_id} has not passed the gate -- "
                "cannot assemble a case (28 §5.5's precondition)"
            ),
        )

    candidate = await _get_candidate_or_404(session, case.candidate_id)
    dossier = await _get_dossier_for_candidate_or_404(session, candidate)
    impact_snapshot = await _get_impact_snapshot_for_candidate_or_404(
        session, case.candidate_id
    )
    parametric_estimate = await _get_parametric_estimate_for_candidate_or_404(
        session, case.candidate_id
    )

    coverage_ratio = impact_snapshot.completeness_ratio
    is_lower_bound = coverage_ratio < 1.0
    rollup_estimate = CostEstimate(
        estimate_id=str(uuid.uuid4()),
        candidate_id=case.candidate_id,
        case_id=case.case_id,
        method="dependency_rollup",
        cost_model_version="v0-demo",
        point_estimate_usd=parametric_estimate.point_estimate_usd * 1.4,
        low_usd=None,
        high_usd=None,
        interval_basis=None,
        confidence=parametric_estimate.confidence,
        assumptions=[
            *parametric_estimate.assumptions,
            "Detailed roll-up derived from the parametric estimate "
            "(x1.4, v0-demo heuristic) -- see cost_model_version.",
        ],
        impact_snapshot_id=impact_snapshot.impact_snapshot_id,
        coverage_ratio=coverage_ratio,
        is_lower_bound=is_lower_bound,
    )
    session.add(rollup_estimate)

    case.niin = candidate.niin
    case.scope_description = f"Redesign evaluation for {candidate.niin}"
    case.dependency_completeness = _row_to_dict(impact_snapshot)
    case.impact_snapshot_id = impact_snapshot.impact_snapshot_id
    case.test_coverage_summary = _test_coverage_summary(dossier.test_coverage)
    case.cost_estimate_id = rollup_estimate.estimate_id
    case.recommendation_stance = body.recommendation_stance
    case.recommendation_basis_refs = [c.get("citation_id") for c in dossier.causal_citations]
    case.recommendation_limitations = body.recommendation_limitations
    case.recommendation_evidence_gaps = body.recommendation_evidence_gaps
    case.narrative_sections = body.narrative_sections
    case.assembled_at = _now()
    case.case_status = "assembled"

    await session.commit()
    return _row_to_dict(case)


# ---------------------------------------------------------------------------
# 5. Propose -- [demo-only endpoint, not in the real 28 API surface]. This
#    is the entire "adjudication" story this demo tells.
# ---------------------------------------------------------------------------


@router.post("/redesign-cases/{case_id}/propose")
async def propose_case(
    case_id: str, session: AsyncSession = Depends(get_session_dependency)
) -> dict:
    case = await session.get(RedesignCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"no redesign_case {case_id}")
    if case.case_status != "assembled":
        raise HTTPException(
            status_code=409,
            detail=f"redesign_case {case_id} is '{case.case_status}', not 'assembled'",
        )

    case.case_status = "proposed"
    case.proposal_id = str(uuid.uuid4())
    await session.commit()
    return _row_to_dict(case)
