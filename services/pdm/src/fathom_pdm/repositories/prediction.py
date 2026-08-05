"""The only place SQL is written for `pdm.prediction`. Document 09 §4.1:
accepts and returns domain/model objects, never Pydantic wire schemas.
Never commits -- the caller (`services/`) owns the transaction.

Row-level security (22-pdm.md §4.5) is transparent to this layer BY DESIGN:
the repository writes ordinary queries, and which rows are visible/writable
is determined by which PostgreSQL role the connection authenticates as --
that is the entire point of RLS over an application-level `WHERE` filter.
This means RLS itself cannot be exercised by the SQLite-backed unit-test
harness (SQLite has no RLS); it requires a real PostgreSQL connection under
both `fathom_pdm_serving` and `fathom_pdm_research` roles, which
`tests/integration/` (testcontainers, real Postgres) is responsible for.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fathom_pdm.models import Prediction


class PredictionRepository:
    async def insert(self, session: AsyncSession, prediction: Prediction) -> None:
        session.add(prediction)
        await session.flush()

    async def get_by_id(self, session: AsyncSession, prediction_id: uuid.UUID) -> Prediction | None:
        return (
            await session.execute(select(Prediction).where(Prediction.prediction_id == prediction_id))
        ).scalar_one_or_none()

    async def get_active_for_item_horizon(
        self, session: AsyncSession, *, installed_item_id: uuid.UUID, horizon_days: int
    ) -> Prediction | None:
        """The current serving-relevant row for this (item, horizon) --
        used by invalidation (§8.1) to find what needs superseding."""
        stmt = (
            select(Prediction)
            .where(
                Prediction.installed_item_id == installed_item_id,
                Prediction.horizon_days == horizon_days,
                Prediction.status == "active",
            )
            .order_by(Prediction.computed_at.desc())
            .limit(1)
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def invalidate(
        self, session: AsyncSession, prediction: Prediction, *, cause: str, at
    ) -> None:
        prediction.status = "invalidated"
        prediction.invalidation_cause = cause
        prediction.invalidated_at = at
        await session.flush()
