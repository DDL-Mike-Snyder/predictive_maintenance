"""Read-only (`GET`) endpoints. docs/demo/redesign-case-builder-demo-plan.md,
Paul's task 6. Plain dicts back out -- no over-engineered response schemas
under this time pressure, just every field named in §1.3 present under its
exact key name."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fathom_design_advisory.db import get_session_dependency
from fathom_design_advisory.models import (
    CostEstimate,
    FailureDossier,
    GateDecision,
    ImpactSnapshot,
    RedesignCandidate,
    RedesignCase,
)

router = APIRouter(prefix="/api/v1/design-advisory", tags=["design-advisory:reads"])


def _row_to_dict(row: object) -> dict:
    return {c.key: getattr(row, c.key) for c in row.__table__.columns}  # type: ignore[attr-defined]


@router.get("/redesign-candidates")
async def list_candidates(
    status: str | None = None,
    session: AsyncSession = Depends(get_session_dependency),
) -> list[dict]:
    stmt = select(RedesignCandidate)
    if status is not None:
        stmt = stmt.where(RedesignCandidate.status == status)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(r) for r in rows]


@router.get("/redesign-candidates/{candidate_id}")
async def get_candidate(
    candidate_id: str, session: AsyncSession = Depends(get_session_dependency)
) -> dict:
    row = await session.get(RedesignCandidate, candidate_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no redesign_candidate {candidate_id}")
    return _row_to_dict(row)


@router.get("/dossiers/{dossier_id}")
async def get_dossier(
    dossier_id: str, session: AsyncSession = Depends(get_session_dependency)
) -> dict:
    row = await session.get(FailureDossier, dossier_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no failure_dossier {dossier_id}")
    return _row_to_dict(row)


@router.get("/impact-snapshots")
async def list_impact_snapshots(
    candidate_id: str | None = None,
    session: AsyncSession = Depends(get_session_dependency),
) -> list[dict]:
    stmt = select(ImpactSnapshot)
    if candidate_id is not None:
        stmt = stmt.where(ImpactSnapshot.candidate_id == candidate_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(r) for r in rows]


@router.get("/impact-snapshots/{impact_snapshot_id}")
async def get_impact_snapshot(
    impact_snapshot_id: str, session: AsyncSession = Depends(get_session_dependency)
) -> dict:
    row = await session.get(ImpactSnapshot, impact_snapshot_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"no impact_snapshot {impact_snapshot_id}"
        )
    return _row_to_dict(row)


@router.get("/cost-estimates")
async def list_cost_estimates(
    candidate_id: str | None = None,
    method: str | None = None,
    session: AsyncSession = Depends(get_session_dependency),
) -> list[dict]:
    # B-2 integration fix: the agent `draft` path fetches the parametric
    # cost estimate via `GET /cost-estimates?candidate_id=&method=parametric`
    # (api/agent.py). Filter on both, mirroring `/impact-snapshots`.
    stmt = select(CostEstimate)
    if candidate_id is not None:
        stmt = stmt.where(CostEstimate.candidate_id == candidate_id)
    if method is not None:
        stmt = stmt.where(CostEstimate.method == method)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(r) for r in rows]


@router.get("/cost-estimates/{estimate_id}")
async def get_cost_estimate(
    estimate_id: str, session: AsyncSession = Depends(get_session_dependency)
) -> dict:
    row = await session.get(CostEstimate, estimate_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no cost_estimate {estimate_id}")
    return _row_to_dict(row)


@router.get("/gate-decisions")
async def list_gate_decisions(
    candidate_id: str | None = None,
    session: AsyncSession = Depends(get_session_dependency),
) -> list[dict]:
    # B-2 integration fix: the agent `draft`/`qualify` paths fetch gate
    # decisions via `GET /gate-decisions?candidate_id=` and take the most
    # recent (api/agent.py::_latest_gate_decision).
    stmt = select(GateDecision)
    if candidate_id is not None:
        stmt = stmt.where(GateDecision.candidate_id == candidate_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(r) for r in rows]


@router.get("/redesign-cases")
async def list_cases(
    candidate_id: str | None = None,
    session: AsyncSession = Depends(get_session_dependency),
) -> list[dict]:
    stmt = select(RedesignCase)
    if candidate_id is not None:
        stmt = stmt.where(RedesignCase.candidate_id == candidate_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(r) for r in rows]


@router.get("/redesign-cases/{case_id}")
async def get_case(
    case_id: str, session: AsyncSession = Depends(get_session_dependency)
) -> dict:
    row = await session.get(RedesignCase, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no redesign_case {case_id}")
    return _row_to_dict(row)
