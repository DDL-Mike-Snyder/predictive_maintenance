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

`invalidate()` calls `pdm.invalidate_prediction()`, a SECURITY DEFINER
function, rather than issuing a plain `UPDATE` -- a research_only row is
not SELECT-visible to `fathom_pdm_serving` at all (that's the isolation
guarantee), so it could never be loaded into a `Prediction` object to
update in the first place, and no policy on this role's own UPDATE can
reach it either: PostgreSQL gates UPDATE's implicit read through the same
SELECT policy as a plain query. The function is the one narrow, audited
exception; see the migration for the full account.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from fathom_pdm.models import Prediction, PredictionProvenance


class PredictionRepository:
    async def insert(self, session: AsyncSession, prediction: Prediction) -> None:
        session.add(prediction)
        await session.flush()

    async def get_by_id(self, session: AsyncSession, prediction_id: uuid.UUID) -> Prediction | None:
        return (
            await session.execute(
                select(Prediction).where(Prediction.prediction_id == prediction_id)
            )
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

    async def list_active(
        self,
        session: AsyncSession,
        *,
        asset_id: uuid.UUID | None = None,
        installed_item_id: uuid.UUID | None = None,
        niin: str | None = None,
        equipment_family: str | None = None,
        reference_class: str | None = None,
        limit: int = 50,
    ) -> list[Prediction]:
        """22-pdm.md §10's `GET /predictions` -- [SCOPE, this demo pass]
        supports the filters actually needed for the triage table; no
        `changed_since`/opaque cursor yet (a plain `limit`, not full
        cursor pagination -- 09's `Page[T]`/`CursorParams` convention is
        not wired here, a named simplification, not an oversight).
        Deliberately has NO `min_probability` parameter at all -- 51
        -operator-console.md §11.2's own rule, `ui-never-sends-min-
        probability`, is honored at the one place that can enforce it:
        this method never accepts the argument to begin with."""
        stmt = select(Prediction).where(Prediction.status == "active")
        if asset_id is not None:
            stmt = stmt.where(Prediction.asset_id == asset_id)
        if installed_item_id is not None:
            stmt = stmt.where(Prediction.installed_item_id == installed_item_id)
        if niin is not None:
            stmt = stmt.where(Prediction.niin == niin)
        if equipment_family is not None:
            stmt = stmt.where(Prediction.equipment_family == equipment_family)
        if reference_class is not None:
            stmt = stmt.where(Prediction.reference_class == reference_class)
        stmt = stmt.order_by(Prediction.computed_at.desc()).limit(limit)
        return list((await session.execute(stmt)).scalars().all())

    async def get_all_active_for_item(
        self, session: AsyncSession, *, installed_item_id: uuid.UUID
    ) -> list[Prediction]:
        """Every currently-active prediction for this item, across all
        horizons -- §8.1: a configuration/removal event invalidates *every*
        prediction attached to the affected item, not one horizon."""
        stmt = select(Prediction).where(
            Prediction.installed_item_id == installed_item_id,
            Prediction.status == "active",
        )
        return list((await session.execute(stmt)).scalars().all())

    async def get_all_active_for_model_binding(
        self, session: AsyncSession, *, model_binding_id: uuid.UUID
    ) -> list[Prediction]:
        """§8.1's `binding_deactivated` trigger: every active prediction the
        superseded binding produced, via `prediction_provenance.model_binding_id`
        (`prediction` carries no `model_binding_id` column of its own)."""
        stmt = (
            select(Prediction)
            .join(
                PredictionProvenance,
                Prediction.provenance_id == PredictionProvenance.provenance_id,
            )
            .where(
                PredictionProvenance.model_binding_id == model_binding_id,
                Prediction.status == "active",
            )
        )
        return list((await session.execute(stmt)).scalars().all())

    async def invalidate(
        self, session: AsyncSession, prediction_id: uuid.UUID, *, cause: str
    ) -> bool:
        """Invalidates by id, not by a pre-loaded object -- a research_only
        row can never be loaded under `fathom_pdm_serving` to begin with.
        Returns whether a row was actually found and invalidated."""
        result = await session.execute(
            text("SELECT pdm.invalidate_prediction(:prediction_id, :cause)"),
            {"prediction_id": str(prediction_id), "cause": cause},
        )
        return bool(result.scalar_one())
