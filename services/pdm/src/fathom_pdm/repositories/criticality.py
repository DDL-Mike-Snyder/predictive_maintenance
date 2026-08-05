"""The only place SQL is written for `pdm.criticality_assessment`."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fathom_pdm.models import CriticalityAssessment


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
