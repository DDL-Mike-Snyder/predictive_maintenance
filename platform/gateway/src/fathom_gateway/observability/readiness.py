"""Registers this service's `ReadinessCheck` callables. Document 09 §5.6's
five mandatory checks (database, migrations, broker, read_model_lag,
outbox_drain) apply to a service that owns an outbox/consumes a broker --
`platform/gateway` (this vertical slice) does neither: it has no
`fathom_sync` dependency at all (see pyproject.toml), so only `database`
is a real check here. Not fabricating always-true placeholders for
infrastructure this service doesn't have."""

from __future__ import annotations

from fathom_py_common import ReadinessCheck, make_check
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def register_checks(engine: AsyncEngine) -> list[ReadinessCheck]:
    async def _database() -> tuple[bool, str | None]:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001 -- readiness check must never raise
            return False, str(exc)
        else:
            return True, None

    return [make_check("database", _database)]
