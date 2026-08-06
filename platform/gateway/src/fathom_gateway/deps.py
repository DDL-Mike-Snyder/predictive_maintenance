"""FastAPI dependencies: session, current identity, CSRF. Document 09 §4.2."""

from __future__ import annotations

import base64
import datetime as dt
import json
import uuid

from fastapi import Cookie, Depends, Header, Request, Response
from fathom_py_common import ProblemException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fathom_gateway.config import Settings
from fathom_gateway.models import GatewaySessionRow
from fathom_gateway.oidc import OidcClient

__all__ = [
    "current_gateway_session",
    "get_oidc_client",
    "get_session",
    "get_settings",
    "verify_csrf",
]


async def get_session(request: Request) -> AsyncSession:
    """`main.py`'s session middleware attaches `request.state.db_session`
    per request. This dependency exposes it under a stable name, matching
    every other service's own `deps.py::get_session`."""
    return request.state.db_session


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_oidc_client(request: Request) -> OidcClient:
    return request.app.state.oidc_client


async def _auto_provision_demo_session(
    session: AsyncSession, response: Response
) -> GatewaySessionRow:
    """[ADDITIVE, opt-in -- `SessionSettings.demo_auto_login`, default
    `False`.] Real Keycloak+OIDC login needs a Keycloak reachable from
    BOTH the gateway process and an arbitrary end-user's own browser --
    for a Domino-App-hosted demo, that means a second public-facing App
    just to expose Keycloak, real infrastructure this demo doesn't need.
    This mints a session with no login step at all, so a Domino-hosted
    demo has *something* rather than a login screen with nowhere real to
    redirect to. `access_token` is a well-formed-but-unsigned JWT shape
    (matches `oidc.py::principal_id_from_access_token`'s own decode-only
    contract) carrying a fixed demo `sub` -- never checked against a real
    issuer, because there is no real issuer in this mode."""
    session_id = str(uuid.uuid4())
    now = dt.datetime.now(dt.UTC)
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    payload = (
        base64.urlsafe_b64encode(json.dumps({"sub": "domino-demo-user"}).encode())
        .decode()
        .rstrip("=")
    )
    row = GatewaySessionRow(
        session_id=session_id,
        access_token=f"{header}.{payload}.sig",
        expires_at=now + dt.timedelta(hours=8),
        created_at=now,
    )
    session.add(row)
    await session.flush()
    response.set_cookie(
        "fathom_session", session_id, max_age=28800, httponly=True, secure=True, samesite="lax"
    )
    return row


async def current_gateway_session(
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    fathom_session: str | None = Cookie(default=None),
) -> GatewaySessionRow:
    """30-gateway.md §8.1.2: `GET /session` (and the pass-through proxy,
    which needs the stored `access_token`) is **cookie-only** -- it never
    accepts a bearer token, because the whole point of the BFF shape is
    that the browser holds no token to present. `404` on no session,
    matching a missing resource -- not `401`, since the caller did nothing
    wrong by not (yet) having authenticated."""
    if fathom_session is None:
        if settings.session.demo_auto_login:
            return await _auto_provision_demo_session(session, response)
        raise ProblemException(
            type="urn:fathom:problem:gateway:no-session",
            title="No active session",
            status=404,
        )
    row = (
        await session.execute(
            select(GatewaySessionRow).where(GatewaySessionRow.session_id == fathom_session)
        )
    ).scalar_one_or_none()
    if row is None:
        raise ProblemException(
            type="urn:fathom:problem:gateway:no-session",
            title="No active session",
            status=404,
        )
    # [SQLite-only dialect gap, test-only -- production always runs
    # PostgreSQL via asyncpg, which round-trips `DateTime(timezone=True)`
    # faithfully.] SQLite has no native timezone-aware datetime type, so a
    # value written with tzinfo comes back naive on read -- caught only by
    # actually running this dependency against a seeded row, not by
    # reviewing the column type. Same shape as the other SQLite-only
    # quirks services/pdm/src/fathom_pdm/main.py's own comment documents.
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=dt.UTC)
    if expires_at < dt.datetime.now(dt.UTC):
        raise ProblemException(
            type="urn:fathom:problem:gateway:no-session",
            title="No active session",
            status=404,
        )
    return row


async def verify_csrf(
    fathom_csrf: str | None = Cookie(default=None),
    x_fathom_csrf: str | None = Header(default=None, alias="X-Fathom-CSRF"),
) -> None:
    """30-gateway.md §8.1.2: double-submit CSRF, required and matched on
    every state-changing GATEWAY-OWNED operation (the spec scopes this to
    the gateway's own surface, not the pass-through one -- §8.1.2's own
    wording). Applied explicitly per-route (`Depends(verify_csrf)`) rather
    than as a global dependency, since it must NOT run on `/session/login`
    /`/session/callback` (unauthenticated by design, no `fathom_csrf`
    cookie exists yet) or on pass-through routes."""
    if fathom_csrf is None or x_fathom_csrf is None or fathom_csrf != x_fathom_csrf:
        raise ProblemException(
            type="urn:fathom:problem:gateway:csrf-mismatch",
            title="CSRF token missing or mismatched",
            status=403,
        )
