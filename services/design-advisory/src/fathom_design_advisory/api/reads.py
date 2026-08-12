"""Read-only (GET) endpoints (plan §Paul task 6).

Every response is a plain dict built directly from the row's own columns,
so the JSON keys match plan §1.3's field names verbatim — Marc, Michael,
and Bella all type these names from the plan document without seeing this
code, so the field names are the contract.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fathom_design_advisory.db import get_session
from fathom_design_advisory.models import (
    CostEstimate,
    FailureDossier,
    ImpactSnapshot,
    RedesignCandidate,
    RedesignCase,
)

router = APIRouter(prefix="/api/v1/design-advisory", tags=["design-advisory:reads"])


def _row_to_dict(row: Any) -> dict[str, Any]:
    """Every column, by its exact name — no hand-maintained response
    schema to drift from plan §1.3."""
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


@router.get("/redesign-candidates")
async def list_candidates(
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    stmt = select(RedesignCandidate)
    if status is not None:
        stmt = stmt.where(RedesignCandidate.status == status)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(r) for r in rows]


@router.get("/redesign-candidates/{candidate_id}")
async def get_candidate(
    candidate_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = await session.get(RedesignCandidate, candidate_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"redesign_candidate {candidate_id} not found")
    return _row_to_dict(row)


@router.get("/dossiers/{dossier_id}")
async def get_dossier(
    dossier_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = await session.get(FailureDossier, dossier_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"failure_dossier {dossier_id} not found")
    return _row_to_dict(row)


@router.get("/impact-snapshots/{impact_snapshot_id}")
async def get_impact_snapshot(
    impact_snapshot_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = await session.get(ImpactSnapshot, impact_snapshot_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"impact_snapshot {impact_snapshot_id} not found"
        )
    return _row_to_dict(row)


@router.get("/cost-estimates/{estimate_id}")
async def get_cost_estimate(
    estimate_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = await session.get(CostEstimate, estimate_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"cost_estimate {estimate_id} not found")
    return _row_to_dict(row)


@router.get("/redesign-cases")
async def list_cases(
    candidate_id: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    stmt = select(RedesignCase)
    if candidate_id is not None:
        stmt = stmt.where(RedesignCase.candidate_id == candidate_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [_row_to_dict(r) for r in rows]


@router.get("/redesign-cases/{case_id}")
async def get_case(
    case_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = await session.get(RedesignCase, case_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"redesign_case {case_id} not found")
    return _row_to_dict(row)
