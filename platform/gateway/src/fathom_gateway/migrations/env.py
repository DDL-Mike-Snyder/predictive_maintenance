"""Async Alembic env. Document 09 §4.2.

Reads the database URL from `Settings` (`FATHOM_DATABASE__URL`) -- the same
single source of truth the running service uses, per §4.5's rule that
`config.py` is the only place that reads the environment. `alembic.ini`
deliberately carries no `sqlalchemy.url` for this reason.

`target_metadata` is a list of two `DeclarativeBase` metadatas, not the
three `services/pdm` carries: this service's own `gateway_session` table,
plus `fathom_py_common`'s `idempotency_keys` table (the `idempotency_guard`
dependency, installed in `main.py`, needs it). No `fathom_sync` metadata --
this service has no `fathom-sync` dependency at all (see pyproject.toml):
it owns no outbox and consumes no broker, see
`observability/readiness.py`'s docstring for why.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from fathom_gateway.config import Settings
from fathom_gateway.models import Base
from fathom_py_common.idempotency import IdempotencyBase
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = [Base.metadata, IdempotencyBase.metadata]


def _database_url() -> str:
    return Settings().database.url  # type: ignore[call-arg]


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql`. Emits SQL without a live connection."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, include_schemas=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _database_url()
    connectable = async_engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
