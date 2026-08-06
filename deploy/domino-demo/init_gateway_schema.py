"""Creates the gateway's schema (`gateway_session` + `idempotency_keys`)
against a real FILE-based SQLite database -- see `init_pdm_schema.py`'s
own docstring for why file-based, not in-memory.

Usage: GATEWAY_DB_PATH=/path/to/gateway.db python init_gateway_schema.py
"""

from __future__ import annotations

import asyncio
import os

from fathom_gateway.models import Base
from fathom_py_common.idempotency import IdempotencyBase
from sqlalchemy.ext.asyncio import create_async_engine

DB_PATH = os.environ["GATEWAY_DB_PATH"]


async def main() -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{DB_PATH}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(IdempotencyBase.metadata.create_all)
    await engine.dispose()
    print(f"Gateway schema created at {DB_PATH}")  # noqa: T201 -- this IS the script's output


if __name__ == "__main__":
    asyncio.run(main())
