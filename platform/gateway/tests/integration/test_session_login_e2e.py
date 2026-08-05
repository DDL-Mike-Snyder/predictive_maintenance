"""End-to-end: the FULL authorization-code+PKCE login/callback/whoami/logout
lifecycle (`api/v1/session.py`) driven against a REAL Keycloak, run via
`testcontainers.keycloak.KeycloakContainer` -- not a stub, not a mocked
token endpoint. Task #18's "Keycloak testcontainer" half (the "real PdM
instance" half is `test_passthrough_proxy_e2e.py`, in this same directory).

[Real, reproducible testcontainers/Keycloak gotcha, found by actually
running this against a live container -- not documented anywhere in
Keycloak's own docs.] Provisioning the realm/client/user via
`KeycloakAdmin`'s REST API at runtime (the obvious approach, and what an
earlier draft of this fixture did) produces a client that is fully visible
to the admin API (`get_clients()` lists it, `get_client()` shows
`enabled: true`) but the user-facing `/protocol/openid-connect/auth`
endpoint still returns `error=client_not_found` for it, every time,
reproduced against both Keycloak 25.0.4 and 23.0.7 in this environment.
Realm IMPORT at container startup (`with_realm_import_file`,
`fixtures/fathom-realm.json`) does not have this problem -- confirmed by
toggling only the provisioning method with every other variable held
fixed. The fix here is to provision this way, not to work around the
symptom (e.g. retrying the admin API call), since the failure is in
admin-API-created-client visibility to the auth endpoint's own client
cache, not in anything this test controls.

A real Keycloak login form has no stable CSS selector/name library to
target, so the login POST target is scraped from the rendered HTML's own
`action="..."` attribute with a plain regex -- fragile in the way any
screen-scrape is, but this is a test fixture reaching an OSS product's
actual login page, not a maintained integration surface; a regex is
proportionate here, not a place to add an HTML-parsing dependency.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import pytest_asyncio
from fathom_gateway.config import (
    DatabaseSettings,
    OidcSettings,
    PdmUpstreamSettings,
    SessionSettings,
    Settings,
)
from fathom_gateway.main import create_app
from httpx import ASGITransport, AsyncClient
from testcontainers.community.keycloak import KeycloakContainer

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FIXTURES_DIR = Path(__file__).parent / "fixtures"
_REALM_NAME = "fathom"
_CLIENT_ID = "gateway"
_CLIENT_SECRET = "gateway-test-secret"  # noqa: S105 -- test-only literal, see per-file-ignore reasoning in root pyproject.toml
_REDIRECT_URI = "https://gateway.test/api/v1/gateway/session/callback"
_USERNAME = "testuser"
_PASSWORD = "testpass"  # noqa: S105 -- test-only literal


@pytest.fixture(scope="module")
def real_keycloak():
    container = KeycloakContainer("quay.io/keycloak/keycloak:25.0.4")
    container.with_realm_import_file(str(_FIXTURES_DIR / "fathom-realm.json"))
    container.start()
    try:
        yield container.get_url()
    finally:
        container.stop()


def _gateway_settings(*, issuer: str) -> Settings:
    return Settings(
        database=DatabaseSettings(url="sqlite+aiosqlite://"),
        oidc=OidcSettings(
            issuer=issuer,
            client_id=_CLIENT_ID,
            client_secret=_CLIENT_SECRET,
            redirect_uri=_REDIRECT_URI,
        ),
        session=SessionSettings(cookie_signing_key="test-signing-key"),
        # This test never exercises a pass-through route, but `create_app()`
        # always builds that router (main.py), so it still needs a real,
        # parseable openapi.json to load at startup.
        pdm=PdmUpstreamSettings(
            base_url="http://test-pdm",
            openapi_path=str(_REPO_ROOT / "services" / "pdm" / "openapi.json"),
        ),
    )


@pytest_asyncio.fixture
async def gateway_client(real_keycloak):
    issuer = f"{real_keycloak}/realms/{_REALM_NAME}"
    app = create_app(_gateway_settings(issuer=issuer))

    from fathom_gateway.models import Base
    from fathom_py_common.idempotency import IdempotencyBase

    async with app.state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(IdempotencyBase.metadata.create_all)

    transport = ASGITransport(app=app)
    # `https`, not `http` -- every cookie `api/v1/session.py` sets carries
    # `secure=True`, and httpx's cookie jar (correctly) won't store or
    # re-attach a Secure-flagged cookie for a plain-http origin, the same
    # rule a real browser enforces.
    async with AsyncClient(transport=transport, base_url="https://gateway.test") as client:
        yield client

    await app.state.http_client.aclose()
    await app.state.engine.dispose()


def _authenticate_with_real_keycloak(authorize_url: str) -> str:
    """Drives the REAL Keycloak login form over a REAL network connection
    (a separate httpx.Client, not the gateway's in-process ASGI transport --
    this part of the flow genuinely leaves the gateway process, exactly as
    a real browser would). Returns the `redirect_uri?code=...&state=...`
    URL Keycloak issues after a successful login, WITHOUT following it
    (`https://gateway.test` is not a real, reachable host)."""
    browser = httpx.Client(follow_redirects=True)
    login_page = browser.get(authorize_url)
    action_match = re.search(r'action="([^"]+)"', login_page.text)
    assert action_match, f"no login form found: {login_page.text[:500]}"
    form_action = html.unescape(action_match.group(1))

    login_response = browser.post(
        form_action,
        data={"username": _USERNAME, "password": _PASSWORD},
        follow_redirects=False,
    )
    assert login_response.status_code == 302, login_response.text
    location = login_response.headers["location"]
    assert location.startswith(_REDIRECT_URI), location
    return location


@pytest.mark.asyncio
async def test_full_login_callback_whoami_logout_against_real_keycloak(gateway_client) -> None:
    client = gateway_client

    # 1. GET /session/login -- the gateway's own PKCE+state generation,
    # redirecting to the REAL Keycloak's real authorization endpoint.
    login_resp = await client.get("/api/v1/gateway/session/login")
    assert login_resp.status_code == 302
    authorize_url = login_resp.headers["location"]
    assert "/protocol/openid-connect/auth" in authorize_url
    assert client.cookies.get("fathom_login") is not None

    # 2. Actually authenticate against the real Keycloak, over the real
    # network -- not a stub.
    redirect_location = _authenticate_with_real_keycloak(authorize_url)
    query = parse_qs(urlparse(redirect_location).query)
    code, state = query["code"][0], query["state"][0]

    # 3. GET /session/callback -- the gateway's own code-exchange, against
    # Keycloak's real token endpoint. `client` still carries the
    # `fathom_login` cookie set in step 1.
    callback_resp = await client.get(
        "/api/v1/gateway/session/callback", params={"code": code, "state": state}
    )
    assert callback_resp.status_code == 302, callback_resp.text
    assert client.cookies.get("fathom_session") is not None
    csrf_token = client.cookies.get("fathom_csrf")
    assert csrf_token is not None

    # 4. GET /session -- whoami, cookie-only.
    whoami_resp = await client.get("/api/v1/gateway/session")
    assert whoami_resp.status_code == 200
    assert "session_id" in whoami_resp.json()

    # 5. POST /session/logout -- real revoke() call against Keycloak's own
    # /protocol/openid-connect/revoke endpoint (best-effort; the assertion
    # here is that this doesn't 500, and that the LOCAL session is gone
    # afterward, matching 30-gateway.md §8.1.2's own "destroyed regardless").
    logout_resp = await client.post(
        "/api/v1/gateway/session/logout",
        headers={"X-Fathom-CSRF": csrf_token, "Idempotency-Key": "test-logout-key-1"},
    )
    assert logout_resp.status_code == 200, logout_resp.text

    whoami_after_logout = await client.get("/api/v1/gateway/session")
    assert whoami_after_logout.status_code == 404


@pytest.mark.asyncio
async def test_callback_rejects_state_mismatch(gateway_client) -> None:
    client = gateway_client
    login_resp = await client.get("/api/v1/gateway/session/login")
    authorize_url = login_resp.headers["location"]

    redirect_location = _authenticate_with_real_keycloak(authorize_url)
    query = parse_qs(urlparse(redirect_location).query)
    code = query["code"][0]

    resp = await client.get(
        "/api/v1/gateway/session/callback", params={"code": code, "state": "wrong-state"}
    )
    assert resp.status_code == 400
    assert resp.json()["type"] == "urn:fathom:problem:gateway:oidc-state-mismatch"
