"""`GET /api/v1/pdm/criticality`. Document 22-pdm.md §11.3: returns only
the latest row with `published_at IS NOT NULL` per NIIN -- an in-flight
migration's §8.3 steps 1-4 row is never exposed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fathom_contracts import SideEffects, Substitution, operation_extra
from fathom_py_common import ProblemException
from sqlalchemy.ext.asyncio import AsyncSession

from fathom_pdm.deps import Principal, current_principal, get_session
from fathom_pdm.repositories.criticality import CriticalityRepository

router = APIRouter()

_criticality_repo = CriticalityRepository()


@router.get(
    "/criticality",
    openapi_extra=operation_extra(
        operation_id="pdm_get_criticality",
        substitution=Substitution.REQUIRED,
        side_effects=SideEffects.NONE,
        summary="Criticality tier for a NIIN, published row only.",
        aggregate="criticality_assessment",
    ),
)
async def get_criticality(
    niin: str,
    principal: Principal = Depends(current_principal),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    row = await _criticality_repo.get_latest_published_for_niin(session, niin)
    if row is None:
        raise ProblemException(
            type="urn:fathom:problem:pdm:criticality-not-found",
            title="No published criticality assessment for this NIIN",
            status=404,
        )
    return {
        "assessment_id": str(row.assessment_id),
        "niin": row.niin,
        "equipment_family": row.equipment_family,
        "score": float(row.score),
        "proposed_tier": row.proposed_tier,
        "data_availability_ceiling": row.data_availability_ceiling,
        "assigned_tier": row.assigned_tier,
        "tier_policy_version": row.tier_policy_version,
        "published_at": row.published_at.isoformat() if row.published_at else None,
    }
