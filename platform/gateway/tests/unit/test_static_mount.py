"""`config.py::AppSettings.static_dir` -- the opt-in Domino-App-hosting
path (main.py's own comment: "makes gateway + UI one same-origin Domino
App"). Verifies the additive design: unset, `create_app()` behaves
exactly as every other test in this suite already assumes; set, it mounts
real files and still lets every API/health route win over the SPA
fallback."""

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


def _settings(*, static_dir: str | None) -> Settings:
    return Settings(
        app=AppSettings(static_dir=static_dir),
        database=DatabaseSettings(url="sqlite+aiosqlite://"),
        oidc=OidcSettings(
            issuer="https://test-issuer/realms/fathom",
            client_id="gateway",
            client_secret="test-secret",
            redirect_uri="https://gateway.test/api/v1/gateway/session/callback",
        ),
        session=SessionSettings(cookie_signing_key="test-signing-key"),
        pdm=PdmUpstreamSettings(
            base_url="http://test-pdm",
            openapi_path=str(_REPO_ROOT / "services" / "pdm" / "openapi.json"),
        ),
    )


def test_static_dir_unset_registers_no_catch_all_route() -> None:
    app = create_app(_settings(static_dir=None))
    schema = app.openapi()
    assert "/{full_path}" not in str(schema["paths"].keys())


@pytest.mark.asyncio
async def test_static_dir_set_serves_spa_without_shadowing_api_routes(tmp_path) -> None:
    static_dir = tmp_path / "dist"
    (static_dir / "assets").mkdir(parents=True)
    (static_dir / "index.html").write_text("<html>fathom demo</html>")
    (static_dir / "assets" / "app.js").write_text("console.log('real asset');")

    app = create_app(_settings(static_dir=str(static_dir)))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://gateway.test") as c:
        root = await c.get("/")
        assert root.status_code == 200
        assert "fathom demo" in root.text

        spa_route = await c.get("/pdm")  # a client-side route with no server file
        assert spa_route.status_code == 200
        assert "fathom demo" in spa_route.text

        asset = await c.get("/assets/app.js")
        assert asset.status_code == 200
        assert "real asset" in asset.text

        # The catch-all is registered LAST -- confirms it never shadows a
        # real API route (session lookup, no cookie -> the real 404).
        api = await c.get("/api/v1/gateway/session")
        assert api.status_code == 404
        assert api.json()["type"] == "urn:fathom:problem:gateway:no-session"

        healthz = await c.get("/healthz")
        assert healthz.status_code == 200

    await app.state.http_client.aclose()
    await app.state.engine.dispose()


@pytest.mark.asyncio
async def test_static_dir_unset_leaves_root_path_unhandled() -> None:
    app = create_app(_settings(static_dir=None))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://gateway.test") as c:
        root = await c.get("/")
        assert root.status_code == 404  # no route claims "/" at all -- unchanged prior behavior
    await app.state.http_client.aclose()
    await app.state.engine.dispose()
