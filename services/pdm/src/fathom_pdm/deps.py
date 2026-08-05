"""FastAPI dependencies: session, principal, if_match, idempotency.
Document 09 §4.2.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from fathom_py_common import Principal, current_principal
from fathom_sync import OutboxWriter, UnitOfWork
from sqlalchemy.ext.asyncio import AsyncSession

__all__ = ["Principal", "current_principal", "get_outbox_writer", "get_session", "get_uow"]


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """`main.py`'s session middleware attaches `request.state.db_session`
    per request (needed so `FathomIdempotentRoute` and the handler share one
    transaction). This dependency exposes it under a stable name."""
    yield request.state.db_session


async def get_uow(request: Request) -> UnitOfWork:
    return UnitOfWork(request.state.db_session)


def get_outbox_writer(request: Request) -> OutboxWriter:
    return request.app.state.outbox_writer
