"""`Idempotency-Key` handling. Document 03 §4, 09-monorepo-and-conventions.md §5.3.

Storage: the service's OWN database, table `idempotency_keys` --
[ESTABLISHED HERE] there is no Redis/shared cache in the 01 §11 inventory,
and using the owned database keeps the replay record in the same
transaction as the effect.

[AMENDMENT -- real bug, found while building services/pdm.] This was
originally a custom `APIRoute` subclass (`FathomIdempotentRoute`), installed
by setting `app.router.route_class`. That silently enforced nothing: every
resource router in the per-service scaffold (09 §4.2) is its own
`APIRouter()` instance, constructed with the DEFAULT `route_class`, and
FastAPI does not propagate a parent router's `route_class` onto a child
router included via `include_router()` -- each router's `route_class` is
independent unless explicitly passed at construction. Discovered because a
missing-Idempotency-Key request returned 401 (from the `current_principal`
dependency running unguarded) instead of the expected 400: the custom Route
class was never actually in the dispatch path for any of PdM's real routes.

Fixed by converting this to a FastAPI **dependency** instead of a Route
subclass. Dependencies declared at `FastAPI(dependencies=[...])` construction
time DO cascade through every level of `include_router()` nesting (this is
how FastAPI's own dependency-merging works, unlike `route_class`), and a
dependency runs after routing has matched -- so `request.scope["route"]` is
already the correct, matched route by the time it executes.

The one thing a plain dependency cannot do is *replace* the response the
handler would have produced (a dependency can only inject a value into the
handler or raise); an idempotent replay must skip calling the handler
entirely and return the ORIGINAL response verbatim. `IdempotentReplay` plus
its own dedicated exception handler (registered by the same
`install_idempotency_middleware` call) is what supplies that: the
dependency raises it in place of a match, and the handler reconstructs the
exact prior `Response` -- status, body, and the `Idempotency-Replayed`
header -- bypassing the RFC 9457 problem-detail shape entirely, since this
is not an error.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any

from fastapi import Depends, FastAPI, Header, Request, Response
from sqlalchemy import JSON, DateTime, Integer, String, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .problems import ProblemException

_JsonVariant = JSON().with_variant(JSONB(), "postgresql")


class IdempotencyBase(DeclarativeBase):
    pass


class IdempotencyKeyRow(IdempotencyBase):
    """Document 09 §5.3. Primary key `(key, route_id, principal_id)` --
    scoping by route and principal prevents one caller's key colliding with
    another's."""

    __tablename__ = "idempotency_keys"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    route_id: Mapped[str] = mapped_column(String, primary_key=True)
    principal_id: Mapped[str] = mapped_column(String, primary_key=True)
    request_hash: Mapped[str] = mapped_column(String, nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict[str, Any]] = mapped_column(_JsonVariant, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def _request_hash(body: bytes, path: str, query: str) -> str:
    """Over the canonicalized body plus path and query, EXCLUDING
    `X-Correlation-Id` -- the same logical retry from a different request
    has a different correlation ID and must still replay."""
    h = hashlib.sha256()
    h.update(path.encode())
    h.update(b"?")
    h.update(query.encode())
    h.update(b"\n")
    h.update(body)
    return h.hexdigest()


class IdempotentReplay(Exception):
    """Raised by `idempotency_guard` when a prior response for this key
    already exists. Caught by its own exception handler, which reconstructs
    the exact original response -- this is not an error."""

    def __init__(self, *, status_code: int, body: dict[str, Any]) -> None:
        self.status_code = status_code
        self.body = body


async def idempotency_guard(
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> None:
    """Installed as a GLOBAL dependency (`FastAPI(dependencies=[Depends(...)])`)
    so it runs for every route regardless of router nesting -- see the
    module docstring for why this replaced a Route-subclass approach."""
    route = request.scope.get("route")
    side_effects = getattr(route, "openapi_extra", None) or {}
    side_effects = side_effects.get("x-side-effects")
    if side_effects not in ("proposal-only", "state-changing"):
        return

    if idempotency_key is None:
        raise ProblemException(
            type="urn:fathom:problem:common:idempotency-key-required",
            title="Idempotency-Key required",
            status=400,
            detail=f"x-side-effects={side_effects!r} requires an Idempotency-Key header",
        )

    body = await request.body()
    principal_id = getattr(request.state, "principal_id", None) or "anonymous"
    session: AsyncSession = request.state.db_session
    route_id = getattr(route, "unique_id", None) or getattr(route, "name", "unknown")
    req_hash = _request_hash(body, request.url.path, str(request.url.query))

    existing = (
        await session.execute(
            select(IdempotencyKeyRow).where(
                IdempotencyKeyRow.key == idempotency_key,
                IdempotencyKeyRow.route_id == route_id,
                IdempotencyKeyRow.principal_id == principal_id,
            )
        )
    ).scalar_one_or_none()

    if existing is None:
        # Record the intent to write here (route_id/principal_id/key/hash)
        # is deferred to `_persist_idempotency_record`, called by the
        # handler itself after it has a real response to store -- a
        # dependency has no hook after the handler runs, only before.
        request.state.idempotency_pending = (idempotency_key, route_id, principal_id, req_hash)
        return

    if existing.request_hash != req_hash:
        raise ProblemException(
            type="urn:fathom:problem:common:idempotency-key-reuse",
            title="Idempotency-Key reuse with a different request",
            status=409,
        )
    raise IdempotentReplay(status_code=existing.response_status, body=existing.response_body)


async def persist_idempotent_response(request: Request, response_body: dict[str, Any], status_code: int) -> None:
    """Called explicitly by a handler (or a thin service-layer wrapper)
    immediately after producing its response, INSIDE the same transaction
    the domain effect committed in -- so the idempotency record and the
    effect are atomic, matching 09 §5.3's storage rule. A no-op if this
    request was never flagged pending by `idempotency_guard` (i.e. its
    `x-side-effects` doesn't require a key)."""
    pending = getattr(request.state, "idempotency_pending", None)
    if pending is None:
        return
    key, route_id, principal_id, req_hash = pending
    session: AsyncSession = request.state.db_session
    session.add(
        IdempotencyKeyRow(
            key=key,
            route_id=route_id,
            principal_id=principal_id,
            request_hash=req_hash,
            response_status=status_code,
            response_body=response_body,
            created_at=dt.datetime.now(dt.timezone.utc),
            expires_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=24),
        )
    )
    await session.flush()


def install_idempotency_middleware(app: FastAPI) -> None:
    """Adds `idempotency_guard` as a dependency on every route (cascades
    through all router nesting) and registers `IdempotentReplay`'s handler.
    Must be called before `app.include_router(...)` so the dependency is
    already in `app.router.dependencies` when routers are attached -- but
    per FastAPI's own dependency-merging, calling it after works too, since
    `app.dependencies` is read at route-resolution time, not at
    `include_router()` time.
    """
    app.router.dependencies.append(Depends(idempotency_guard))

    @app.exception_handler(IdempotentReplay)
    async def _handle_replay(request: Request, exc: IdempotentReplay) -> Response:
        return Response(
            content=json.dumps(exc.body).encode(),
            status_code=exc.status_code,
            media_type="application/json",
            headers={"Idempotency-Replayed": "true"},
        )
