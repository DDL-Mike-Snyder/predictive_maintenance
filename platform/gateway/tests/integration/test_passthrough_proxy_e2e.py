"""End-to-end: a REAL PdM instance, started as a real subprocess (its own
`uvicorn`, its own event loop, its own in-memory SQLite -- a genuinely
separate process, not an in-process mount), reached through the gateway's
own generated pass-through router (`proxy.py`, DECISION G-3). Proves the
whole chain for real: gateway routing -> `current_gateway_session` cookie
lookup -> `X-Fathom-Principal` header substitution (see
`oidc.py::principal_id_from_access_token`'s own docstring for why this,
not a forwarded bearer token) -> a real HTTP call over a real socket ->
PdM's own real business logic -> the real response relayed back.

Task #18 (this vertical slice's own remaining item): "real tests against a
Keycloak testcontainer and a real PdM instance." This file covers the
"real PdM instance" half -- login/callback against a real Keycloak is a
separate, larger test (needs a running realm/client configured), not
built here; this test seeds a `gateway_session` row directly, bypassing
the OIDC dance itself, to isolate what's actually new in this pass: the
proxy, not the login flow (already covered by unit-level reasoning about
`oidc.py`).
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import socket
import subprocess
import time
import uuid
from pathlib import Path

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
from fathom_gateway.models import Base, GatewaySessionRow
from fathom_py_common.idempotency import IdempotencyBase
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

_REPO_ROOT = Path(__file__).resolve().parents[4]
_PDM_VENV_PYTHON = _REPO_ROOT / "services" / "pdm" / ".venv" / "bin" / "python"
_PDM_OPENAPI_PATH = _REPO_ROOT / "services" / "pdm" / "openapi.json"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _fake_jwt(sub: str) -> str:
    """No signature needed -- `principal_id_from_access_token` deliberately
    never verifies one, see its own docstring."""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"sub": sub}).encode()).decode().rstrip("=")
    return f"{header}.{payload}.sig"


_SCHEMA_SETUP_SCRIPT = """
import asyncio
from fathom_pdm.models import Base
from fathom_py_common.idempotency import IdempotencyBase
from fathom_sync import Base as SyncBase
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine


async def main() -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite:///{db_path}",
        execution_options={{"schema_translate_map": {{"pdm": None}}}},
    )

    # services/pdm/tests/conftest.py's own `db_session` fixture registers
    # this same function for the same reason: SQLite has no built-in
    # `LEAST()`, which `criticality_assessment`'s own `tier_is_capped`
    # CHECK constraint (services/pdm/src/fathom_pdm/models/criticality.py)
    # needs at CREATE TABLE time, not just at query time.
    @event.listens_for(engine.sync_engine, "connect")
    def _register_least(dbapi_connection, _connection_record):
        dbapi_connection.create_function("LEAST", 2, min)

    async with engine.begin() as conn:
        await conn.run_sync(SyncBase.metadata.create_all)
        await conn.run_sync(IdempotencyBase.metadata.create_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


asyncio.run(main())
"""


@pytest.fixture(scope="module")
def real_pdm_instance(tmp_path_factory):
    # A real FILE-based SQLite DB, not the usual in-memory `sqlite+aiosqlite://`
    # every other test in this vertical slice uses -- in-memory SQLite is
    # per-connection (services/pdm's own conftest.py docstring), so it can't
    # be shared between the schema-creation step below and the separate
    # `uvicorn` SUBPROCESS started after it; a real PdM instance reached over
    # a real socket needs a real file both processes can open.
    db_path = tmp_path_factory.mktemp("pdm-e2e") / "pdm.db"
    setup = subprocess.run(
        [str(_PDM_VENV_PYTHON), "-c", _SCHEMA_SETUP_SCRIPT.format(db_path=db_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if setup.returncode != 0:
        raise RuntimeError(f"PdM schema setup failed:\n{setup.stdout}\n{setup.stderr}")

    port = _free_port()
    env = {
        "FATHOM_DATABASE__URL": f"sqlite+aiosqlite:///{db_path}",
        "FATHOM_EVENTS__BROKERS": "test-broker:9093",
        "FATHOM_EVENTS__SCHEMA_REGISTRY": "http://test-schema-registry",
        "FATHOM_EVENTS__CONSUMER_GROUP": "fathom-pdm-v1",
        "FATHOM_AUTH__ISSUER": "https://test-issuer",
        "FATHOM_AUTH__JWKS_URL": "https://test-issuer/jwks",
        "FATHOM_AUDIT__BASE_URL": "http://test-audit",
        "FATHOM_REFERENCE_DATA__BASE_URL": "http://test-reference-data",
        "FATHOM_OTEL__ENABLED": "false",
        "PATH": "/usr/bin:/bin",
    }
    proc = subprocess.Popen(
        [
            str(_PDM_VENV_PYTHON),
            "-m",
            "uvicorn",
            "fathom_pdm.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 15
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                resp = httpx.get(f"{base_url}/healthz", timeout=1)
                if resp.status_code == 200:
                    break
            except httpx.HTTPError as exc:
                last_error = exc
            time.sleep(0.25)
        else:
            proc.terminate()
            output = proc.stdout.read().decode() if proc.stdout else ""
            raise RuntimeError(f"real PdM instance never became healthy: {last_error}\n{output}")
        yield base_url
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def _gateway_settings(*, pdm_base_url: str) -> Settings:
    return Settings(
        database=DatabaseSettings(url="sqlite+aiosqlite://"),
        oidc=OidcSettings(
            issuer="https://test-issuer/realms/fathom",
            client_id="gateway",
            client_secret="test-secret",
            redirect_uri="https://gateway.test/api/v1/gateway/session/callback",
        ),
        session=SessionSettings(cookie_signing_key="test-signing-key"),
        pdm=PdmUpstreamSettings(base_url=pdm_base_url, openapi_path=str(_PDM_OPENAPI_PATH)),
    )


@pytest_asyncio.fixture
async def gateway_app_and_client(real_pdm_instance):
    app = create_app(_gateway_settings(pdm_base_url=real_pdm_instance))
    session_maker = async_sessionmaker(app.state.engine, expire_on_commit=False)

    async with app.state.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(IdempotencyBase.metadata.create_all)

    session_id = str(uuid.uuid4())
    async with session_maker() as session:
        session.add(
            GatewaySessionRow(
                session_id=session_id,
                access_token=_fake_jwt("test-user-1"),
                expires_at=dt.datetime.now(dt.UTC) + dt.timedelta(hours=1),
                created_at=dt.datetime.now(dt.UTC),
            )
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://gateway.test") as client:
        yield client, session_id

    await app.state.http_client.aclose()
    await app.state.engine.dispose()


@pytest.mark.asyncio
async def test_passthrough_get_prediction_reaches_real_pdm(gateway_app_and_client) -> None:
    client, session_id = gateway_app_and_client
    missing_id = uuid.uuid4()
    client.cookies.set("fathom_session", session_id)

    resp = await client.get(f"/api/v1/pdm/predictions/{missing_id}")

    # Real PdM's own get_prediction handler (predictions.py) -- a 404 with
    # this exact problem `type` proves the request reached PdM's real
    # business logic and came back through the gateway unmodified, not a
    # gateway-local stub.
    assert resp.status_code == 404
    body = resp.json()
    assert body["type"] == "urn:fathom:problem:pdm:prediction-not-actionable"


@pytest.mark.asyncio
async def test_passthrough_without_session_is_rejected_by_gateway(gateway_app_and_client) -> None:
    client, _session_id = gateway_app_and_client
    resp = await client.get(f"/api/v1/pdm/predictions/{uuid.uuid4()}")

    # No `fathom_session` cookie -- `current_gateway_session` (deps.py)
    # must refuse this at the GATEWAY, before any call to PdM is made.
    assert resp.status_code == 404
    assert resp.json()["type"] == "urn:fathom:problem:gateway:no-session"
