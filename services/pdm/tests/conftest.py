"""Document 09-monorepo-and-conventions.md §4.7: `conftest.py` provides the
app fixture, db container, broker container, principal factory.

Production runs against real PostgreSQL via CloudNativePG (09 §2.1) and
real Redpanda, exercised in `tests/integration/` via testcontainers. The
`db_session` fixture here uses SQLite for `tests/unit/` -- fast, no
container required -- bridging two Postgres-specific things SQLite lacks:
schema qualification (`pdm.*`) and the `LEAST()` scalar function used by
`tier_is_capped`.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Settings has NO defaults for anything environment-specific (09 §4.5) --
# by design, so a missing FATHOM_DATABASE__URL fails loudly rather than
# silently connecting to localhost. `fathom_pdm.main` executes `app =
# create_app()` at MODULE level (09 §4.6's own template), so simply
# IMPORTING it -- which any test file under tests/ that imports
# `fathom_pdm.main` will do -- requires these to already be set. Pytest
# imports conftest.py before collecting sibling test files, so setting them
# here (module level, not inside a fixture) is what makes that import
# succeed; individual tests override with their own real Settings() where
# it matters (see tests/integration/test_bulk_ingest_e2e.py's `_settings()`).
os.environ.setdefault("FATHOM_DATABASE__URL", "sqlite+aiosqlite://")
os.environ.setdefault("FATHOM_EVENTS__BROKERS", "test-broker:9093")
os.environ.setdefault("FATHOM_EVENTS__SCHEMA_REGISTRY", "http://test-schema-registry")
os.environ.setdefault("FATHOM_AUTH__ISSUER", "https://test-issuer")
os.environ.setdefault("FATHOM_AUTH__JWKS_URL", "https://test-issuer/jwks")
os.environ.setdefault("FATHOM_AUDIT__BASE_URL", "http://test-audit")
os.environ.setdefault("FATHOM_REFERENCE_DATA__BASE_URL", "http://test-reference-data")

from fathom_pdm.models import Base
from fathom_py_common.idempotency import IdempotencyBase
from fathom_sync import Base as SyncBase


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://", execution_options={"schema_translate_map": {"pdm": None}}
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _register_least(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        dbapi_connection.create_function("LEAST", 2, min)

    async with engine.begin() as conn:
        # Two separate DeclarativeBase metadatas (fathom_sync's outbox/inbox/
        # producer_sequence tables, and PdM's own) -- both are needed.
        await conn.run_sync(SyncBase.metadata.create_all)
        await conn.run_sync(IdempotencyBase.metadata.create_all)
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session

    await engine.dispose()
