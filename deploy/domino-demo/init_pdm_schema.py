"""Creates PdM's schema against a real FILE-based SQLite database (not the
usual in-memory `sqlite+aiosqlite://` every test in this repo uses -- a
Domino App's `app.sh` starts PdM as a genuinely separate process from
this init step, and in-memory SQLite is per-connection, so nothing
written here would be visible to that process otherwise).

Registers `LEAST()` for the same reason `platform/gateway/tests
/integration/test_passthrough_proxy_e2e.py`'s own `_SCHEMA_SETUP_SCRIPT`
does: SQLite has no built-in `LEAST()`, which `criticality_assessment`'s
`tier_is_capped` CHECK constraint needs at CREATE TABLE time. This demo
never seeds a criticality_assessment row, but the table is still created
alongside every other one, so the function must still be registered.

Usage: PDM_DB_PATH=/path/to/pdm.db python init_pdm_schema.py
"""

from __future__ import annotations

import asyncio
import os

from fathom_pdm.models import Base
from fathom_py_common.idempotency import IdempotencyBase
from fathom_sync import Base as SyncBase
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine

DB_PATH = os.environ["PDM_DB_PATH"]


async def main() -> None:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{DB_PATH}",
        execution_options={"schema_translate_map": {"pdm": None}},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _register_least(dbapi_connection: object, _connection_record: object) -> None:
        dbapi_connection.create_function("LEAST", 2, min)  # type: ignore[attr-defined]

    async with engine.begin() as conn:
        await conn.run_sync(SyncBase.metadata.create_all)
        await conn.run_sync(IdempotencyBase.metadata.create_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print(f"PdM schema created at {DB_PATH}")  # noqa: T201 -- this IS the script's output


if __name__ == "__main__":
    asyncio.run(main())
