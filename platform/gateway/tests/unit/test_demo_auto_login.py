"""`SessionSettings.demo_auto_login` -- deps.py's own additive, opt-in
escape hatch for a Domino-App-hosted demo with no Keycloak reachable
from both the gateway and an arbitrary browser. Default `False`; every
existing test in this suite already assumes that default and keeps
passing unmodified."""

from __future__ import annotations

from pathlib import Path

import pytest
from fathom_gateway.config import (
    AppSettings,
    DatabaseSettings,
    OidcSettings,
    PdmUpstreamSettings,
    SessionSettings,
    Settings,
)
from fathom_gateway.main import create_app
from httpx import ASGITransport, AsyncClient

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _settings(*, demo_auto_login: bool) -> Settings:
    return Settings(
        app=AppSettings(),
        database=DatabaseSettings(url="sqlite+aiosqlite://"),
        oidc=OidcSettings(
            issuer="https://test-issuer/realms/fathom",
            client_id="gateway",
            client_secret="test-secret",
            redirect_uri="https://gateway.test/api/v1/gateway/session/callback",
        ),
        session=SessionSettings(
            cookie_signing_key="test-signing-key", demo_auto_login=demo_auto_login
        ),
        pdm=PdmUpstreamSettings(
            base_url="http://test-pdm",
            openapi_path=str(_REPO_ROOT / "services" / "pdm" / "openapi.json"),
        ),
    )


@pytest.mark.asyncio
async def test_default_still_requires_a_real_session() -> None:
    app = create_app(_settings(demo_auto_login=False))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://gateway.test") as c:
        resp = await c.get("/api/v1/gateway/session")
        assert resp.status_code == 404
        assert resp.json()["type"] == "urn:fathom:problem:gateway:no-session"
    await app.state.http_client.aclose()
    await app.state.engine.dispose()


@pytest.mark.asyncio
async def test_demo_auto_login_mints_a_session_with_no_cookie_present() -> None:
    from fathom_gateway.models import Base

    app = create_app(_settings(demo_auto_login=True))
    async with app.state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://gateway.test") as c:
        resp = await c.get("/api/v1/gateway/session")
        assert resp.status_code == 200
        assert "session_id" in resp.json()
        assert c.cookies.get("fathom_session") is not None

        # The SAME auto-provisioned session persists across a second call
        # -- not a fresh one minted every request.
        first_id = resp.json()["session_id"]
        second = await c.get("/api/v1/gateway/session")
        assert second.json()["session_id"] == first_id
    await app.state.http_client.aclose()
    await app.state.engine.dispose()
