"""Registers this service's `ReadinessCheck` callables. Document 09 §5.6:
five mandatory checks in every service -- database, migrations, broker,
read_model_lag, outbox_drain.
"""

from __future__ import annotations

from fathom_py_common import ReadinessCheck, make_check
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from fathom_pdm.config import Settings


def register_checks(settings: Settings, engine: AsyncEngine) -> list[ReadinessCheck]:
    async def _database() -> tuple[bool, str | None]:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True, None
        except Exception as exc:  # noqa: BLE001 -- readiness check must never raise
            return False, str(exc)

    async def _migrations() -> tuple[bool, str | None]:
        # [PLACEHOLDER] Compares the image-baked Alembic head against the
        # database's `alembic_version` table. Not yet wired to a real
        # revision history in this vertical slice.
        return True, None

    async def _broker() -> tuple[bool, str | None]:
        # [PLACEHOLDER] Producer metadata reachability against
        # settings.events.brokers -- confluent-kafka-python client, not yet
        # wired for this vertical slice (no live Redpanda in this pass).
        return True, None

    async def _read_model_lag() -> tuple[bool, str | None]:
        # [PLACEHOLDER] Wire to a real fathom_sync.ReadModelLag instance once
        # inbox consumers are implemented for this service.
        return True, None

    async def _outbox_drain() -> tuple[bool, str | None]:
        # [PLACEHOLDER] Pending outbox depth / oldest-pending age, per
        # 11-outbox-sync-library.md §2.6.
        return True, None

    return [
        make_check("database", _database),
        make_check("migrations", _migrations),
        make_check("broker", _broker),
        make_check("read_model_lag", _read_model_lag),
        make_check("outbox_drain", _outbox_drain),
    ]
