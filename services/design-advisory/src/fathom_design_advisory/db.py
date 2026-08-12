"""Async engine / sessionmaker wiring and the `get_session` FastAPI
dependency (plan §Paul task 4). No Alembic for this demo — tables are
created with a plain `create_all()` at startup.

The engine and sessionmaker are built by `main.create_app()` and stashed
on `app.state`; `get_session` reads them from the request, matching every
other service's own `deps.py::get_session`. The standalone seed script
(`scripts/seed_demo_data.py`) builds its own engine via `build_engine`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from fathom_design_advisory.config import Settings
from fathom_design_advisory.models import Base


def build_engine(settings: Settings) -> AsyncEngine:
    connect_args = (
        {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    )
    return create_async_engine(settings.database_url, connect_args=connect_args)


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_all(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One session per request, committed on clean exit. Action endpoints
    (owned by other contributors) that write rows rely on this commit."""
    session_maker: async_sessionmaker[AsyncSession] = request.app.state.session_maker
    async with session_maker() as session:
        yield session
        await session.commit()
