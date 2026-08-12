"""Engine/session wiring -- SQLite always for this demo (no Postgres
branch needed, docs/demo/redesign-case-builder-demo-plan.md/Paul's task 4)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from fathom_design_advisory.config import Settings
from fathom_design_advisory.models import Base


def make_engine(database_url: str) -> AsyncEngine:
    engine_kwargs: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        engine_kwargs["poolclass"] = StaticPool
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    return create_async_engine(database_url, **engine_kwargs)


async def create_all(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def make_session_maker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session_dependency(request: Request) -> AsyncIterator[AsyncSession]:
    session_maker = request.app.state.session_maker
    async with session_maker() as session:
        yield session


def get_settings_dependency(request: Request) -> Settings:
    return request.app.state.settings
