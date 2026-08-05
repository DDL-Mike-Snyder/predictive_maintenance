"""Async Alembic env. Document 09 §4.2.

Reads the database URL from `Settings` (`FATHOM_DATABASE__URL`) -- the same
single source of truth the running service uses, per §4.5's rule that
`config.py` is the only place that reads the environment. `alembic.ini`
deliberately carries no `sqlalchemy.url` for this reason.

`target_metadata` is a LIST of three separate `DeclarativeBase` metadatas,
not one: PdM's own models, `fathom_sync`'s outbox/inbox/producer_sequence
tables, and `fathom_py_common`'s idempotency_keys table. Every service
includes all three in its own migration history (11-outbox-sync-library.md
§2.2: there is no shared migration path, and the outbox/inbox tables live
in each service's own database). Autogenerate against a list of metadatas
is supported directly by Alembic 1.13+.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from fathom_pdm.config import Settings
from fathom_pdm.models import Base
from fathom_py_common.idempotency import IdempotencyBase
from fathom_sync import Base as SyncBase
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = [Base.metadata, SyncBase.metadata, IdempotencyBase.metadata]


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
    connectable = async_engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
