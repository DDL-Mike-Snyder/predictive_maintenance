"""End-to-end: build the real app, POST /scoring-runs through the full
middleware stack (correlation, problem handlers, idempotency, session-per-
request), and read the created row back.

22-pdm.md §10: `x-side-effects: none` (it computes; does not alter domain
state) but `Idempotency-Key` required anyway -- the first operation in this
corpus to need that combination. `packages/contracts`' `idempotency_required`
flag and `packages/py-common`'s `idempotency_guard` update exist specifically
so this works through the SHARED middleware (09 §8.1's own requirement),
not a local, one-off check in this route. `test_create_scoring_run_rejects_
missing_idempotency_key` is the test that would fail if that wiring ever
regressed back to side-effects-only enforcement.

Uses SQLite for speed (see tests/conftest.py's rationale) -- same event-loop
discipline as test_bulk_ingest_e2e.py (httpx.AsyncClient + ASGITransport,
not starlette's TestClient, so seeding and requests share one loop).
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from fathom_pdm.config import (
    AuditSettings,
    AuthSettings,
    DatabaseSettings,
    EventsSettings,
    ReferenceDataSettings,
    Settings,
)
from fathom_pdm.main import create_app
from fathom_pdm.models import Base
from fathom_py_common.idempotency import IdempotencyBase
from fathom_sync import Base as SyncBase
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event


def _settings() -> Settings:
    return Settings(
        database=DatabaseSettings(url="sqlite+aiosqlite://"),
        events=EventsSettings(brokers="x", schema_registry="y"),
        auth=AuthSettings(issuer="x", jwks_url="y"),
        audit=AuditSettings(base_url="x"),
        reference_data=ReferenceDataSettings(base_url="x"),
    )


@pytest_asyncio.fixture
async def app_and_client():
    from fathom_contracts.operation import REGISTRY

    REGISTRY.clear()
    app = create_app(_settings())

    @event.listens_for(app.state.engine.sync_engine, "connect")
    def _register_least(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        dbapi_connection.create_function("LEAST", 2, min)

    async with app.state.engine.begin() as conn:
        await conn.run_sync(SyncBase.metadata.create_all)
        await conn.run_sync(IdempotencyBase.metadata.create_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield app, client

    await app.state.engine.dispose()


@pytest.mark.asyncio
async def test_create_scoring_run_succeeds(app_and_client) -> None:
    _app, client = app_and_client
    resp = await client.post(
        "/api/v1/pdm/scoring-runs",
        json={"stratum": "operational", "scope": {"equipment_family": "pump-centrifugal"}},
        headers={"Idempotency-Key": "create-1", "X-Fathom-Principal": "operator-1"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["stratum"] == "operational"
    assert body["trigger"] == "on_demand"
    assert body["status"] == "queued"
    assert body["scope"] == {"equipment_family": "pump-centrifugal"}
    assert body["scoring_run_id"]


@pytest.mark.asyncio
async def test_create_scoring_run_replay_via_idempotency_key(app_and_client) -> None:
    _app, client = app_and_client
    payload = {"stratum": "holdout_research", "scope": {"niin": "012345678"}}
    headers = {"Idempotency-Key": "create-2", "X-Fathom-Principal": "operator-1"}

    resp = await client.post("/api/v1/pdm/scoring-runs", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    first_body = resp.json()

    # Same key, same body -> replayed verbatim, not a second scoring_run.
    resp2 = await client.post("/api/v1/pdm/scoring-runs", json=payload, headers=headers)
    assert resp2.headers.get("Idempotency-Replayed") == "true"
    assert resp2.json() == first_body


@pytest.mark.asyncio
async def test_create_scoring_run_rejects_missing_idempotency_key(app_and_client) -> None:
    """The load-bearing test for this whole feature: side_effects=none
    alone would make the shared middleware skip enforcement entirely (09
    §8.1's general rule) -- this only 400s because `idempotency_required`
    on the operation declaration overrides that default."""
    _app, client = app_and_client
    resp = await client.post(
        "/api/v1/pdm/scoring-runs",
        json={"stratum": "operational", "scope": {}},
    )
    assert resp.status_code == 400
    assert resp.json()["type"] == "urn:fathom:problem:common:idempotency-key-required"


@pytest.mark.asyncio
async def test_create_scoring_run_rejects_invalid_stratum(app_and_client) -> None:
    _app, client = app_and_client
    resp = await client.post(
        "/api/v1/pdm/scoring-runs",
        json={"stratum": "not-a-real-stratum", "scope": {}},
        headers={"Idempotency-Key": "create-3", "X-Fathom-Principal": "operator-1"},
    )
    assert resp.status_code == 422
