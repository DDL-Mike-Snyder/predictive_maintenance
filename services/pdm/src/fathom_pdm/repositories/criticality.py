"""The only place SQL is written for `pdm.criticality_assessment`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from fathom_pdm.models import CriticalityAssessment

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession


class CriticalityRepository:
    async def insert(self, session: AsyncSession, assessment: CriticalityAssessment) -> None:
        session.add(assessment)
        await session.flush()

    async def get_latest_published_for_niin(
        self, session: AsyncSession, niin: str
    ) -> CriticalityAssessment | None:
        """§8.3: only the latest row with `published_at IS NOT NULL` is
        served -- an in-flight migration's steps 1-4 row is never exposed."""
        stmt = (
            select(CriticalityAssessment)
            .where(
                CriticalityAssessment.niin == niin,
                CriticalityAssessment.published_at.is_not(None),
            )
            .order_by(CriticalityAssessment.published_at.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_prior_for_hysteresis(
        self, session: AsyncSession, *, niin: str, equipment_family: str
    ) -> CriticalityAssessment | None:
        """The immediately preceding assessment for this (niin,
        equipment_family) -- deliberately unfiltered by `published_at`,
        unlike `get_latest_published_for_niin`. §3.3/§3.4's hysteresis
        rule tracks consecutive *assessments*, and `services.criticality
        .resolve_proposed_tier` needs the actual immediately-prior one to
        correctly detect a persisted crossing, not merely the latest one
        an external caller was allowed to see."""
        stmt = (
            select(CriticalityAssessment)
            .where(
                CriticalityAssessment.niin == niin,
                CriticalityAssessment.equipment_family == equipment_family,
            )
            .order_by(CriticalityAssessment.effective_at.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_by_id(
        self, session: AsyncSession, assessment_id: uuid.UUID
    ) -> CriticalityAssessment | None:
        return (
            await session.execute(
                select(CriticalityAssessment).where(
                    CriticalityAssessment.assessment_id == assessment_id
                )
            )
        ).scalar_one_or_none()
