"""`/api/v1/gateway/session/*`. Document 30-gateway.md §8.1.2: the four
session-lifecycle routes -- login, callback, whoami, logout. HTTP + cookie
shape only; the OIDC protocol detail lives in `oidc.py`, the session-row
persistence in `models.py`."""

from __future__ import annotations

import contextlib
import datetime as dt
import secrets
import uuid

from fastapi import APIRouter, Cookie, Depends, Request
from fathom_contracts import SideEffects, Substitution, operation_extra
from fathom_py_common import ProblemException, persist_idempotent_response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from fathom_gateway.config import Settings
from fathom_gateway.deps import (
    current_gateway_session,
    get_oidc_client,
    get_session,
    get_settings,
    verify_csrf,
)
from fathom_gateway.models import GatewaySessionRow
from fathom_gateway.oidc import OidcClient, generate_pkce, generate_state

router = APIRouter()

_LOGIN_COOKIE_NAME = "fathom_login"
_LOGIN_COOKIE_MAX_AGE = 300  # 5 minutes -- the OIDC round trip has no reason to take longer


def _login_serializer(settings: Settings) -> URLSafeTimedSerializer:
    """Signs the short-lived `fathom_login` cookie (state + PKCE verifier)
    -- see `config.py`'s own `SessionSettings.cookie_signing_key`
    docstring for why this one cookie is signed while `gateway_session`'s
    id is not."""
    return URLSafeTimedSerializer(settings.session.cookie_signing_key, salt="fathom-gateway-login")


@router.get(
    "/session/login",
    openapi_extra=operation_extra(
        operation_id="gateway_session_login",
        substitution=Substitution.INTERNAL,
        side_effects=SideEffects.NONE,
        summary="Begin OIDC authorization-code+PKCE login; redirects to Keycloak.",
    ),
)
async def session_login(
    settings: Settings = Depends(get_settings),
    oidc: OidcClient = Depends(get_oidc_client),
) -> RedirectResponse:
    pkce = generate_pkce()
    state = generate_state()
    login_cookie = _login_serializer(settings).dumps({"state": state, "verifier": pkce.verifier})

    response = RedirectResponse(url=oidc.authorize_url(state=state, pkce=pkce), status_code=302)
    response.set_cookie(
        _LOGIN_COOKIE_NAME,
        login_cookie,
        max_age=_LOGIN_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@router.get(
    "/session/callback",
    openapi_extra=operation_extra(
        operation_id="gateway_session_callback",
        substitution=Substitution.INTERNAL,
        side_effects=SideEffects.STATE_CHANGING,
        summary="OIDC redirect_uri: exchange code for a token, create the server-side session.",
        idempotency_exempt=True,
    ),
)
async def session_callback(
    *,
    code: str,
    state: str,
    settings: Settings = Depends(get_settings),
    oidc: OidcClient = Depends(get_oidc_client),
    session: AsyncSession = Depends(get_session),
    fathom_login: str | None = Cookie(default=None),
) -> RedirectResponse:
    if fathom_login is None:
        raise ProblemException(
            type="urn:fathom:problem:gateway:oidc-state-mismatch",
            title="Missing login cookie",
            status=400,
        )
    try:
        login_data = _login_serializer(settings).loads(fathom_login, max_age=_LOGIN_COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired) as exc:
        raise ProblemException(
            type="urn:fathom:problem:gateway:oidc-state-mismatch",
            title="Invalid or expired login cookie",
            status=400,
        ) from exc
    if login_data["state"] != state:
        raise ProblemException(
            type="urn:fathom:problem:gateway:oidc-state-mismatch",
            title="State mismatch",
            status=400,
        )

    tokens = await oidc.exchange_code(code=code, code_verifier=login_data["verifier"])

    now = dt.datetime.now(dt.UTC)
    session_id = str(uuid.uuid4())
    session.add(
        GatewaySessionRow(
            session_id=session_id,
            access_token=tokens.access_token,
            expires_at=now + dt.timedelta(seconds=tokens.expires_in),
            created_at=now,
        )
    )
    await session.flush()

    response = RedirectResponse(url=settings.session.landing_url, status_code=302)
    response.delete_cookie(_LOGIN_COOKIE_NAME)
    response.set_cookie(
        "fathom_session",
        session_id,
        max_age=tokens.expires_in,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    # NOT httponly -- 30-gateway.md §8.1.2's double-submit pattern requires
    # apps/web's own JS to read this value and echo it back as the
    # X-Fathom-CSRF header (see deps.py::verify_csrf).
    response.set_cookie(
        "fathom_csrf",
        secrets.token_urlsafe(24),
        max_age=tokens.expires_in,
        httponly=False,
        secure=True,
        samesite="lax",
    )
    return response


@router.get(
    "/session",
    openapi_extra=operation_extra(
        operation_id="gateway_get_session",
        substitution=Substitution.INTERNAL,
        side_effects=SideEffects.NONE,
        summary="The caller's own session identity block.",
    ),
)
async def get_session_identity(
    current: GatewaySessionRow = Depends(current_gateway_session),
) -> dict:
    # [PLACEHOLDER] the real identity block (31-auth.md §3.2's
    # `fathom.identity` shape -- authority classes, holdout membership,
    # duty status) requires decoding `current.access_token`'s own claims,
    # not built in this vertical slice. This proves the session lookup
    # itself (cookie -> row -> not-expired) works end to end.
    return {"session_id": current.session_id, "expires_at": current.expires_at.isoformat()}


@router.post(
    "/session/logout",
    openapi_extra=operation_extra(
        operation_id="gateway_session_logout",
        substitution=Substitution.INTERNAL,
        side_effects=SideEffects.STATE_CHANGING,
        summary="Destroy the local session and revoke its access token at Keycloak.",
    ),
)
async def session_logout(
    *,
    request: Request,
    current: GatewaySessionRow = Depends(current_gateway_session),
    session: AsyncSession = Depends(get_session),
    oidc: OidcClient = Depends(get_oidc_client),
    _csrf: None = Depends(verify_csrf),
) -> dict:
    # Best-effort: §8.1.2 -- "the LOCAL session is destroyed regardless" of
    # whether Keycloak's own revoke call succeeds.
    with contextlib.suppress(Exception):
        await oidc.end_session(access_token=current.access_token)
    await session.delete(current)
    await session.flush()
    result = {"status": "logged_out"}
    await persist_idempotent_response(request, result, 200)
    return result
