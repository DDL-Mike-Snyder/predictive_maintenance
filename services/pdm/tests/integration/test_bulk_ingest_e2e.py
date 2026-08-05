"""End-to-end: build the real app, seed the schema, POST a bulk-ingest
request through the full middleware stack (correlation, problem handlers,
idempotency, session-per-request), and read the prediction back.

Uses SQLite for speed (see tests/conftest.py's rationale) -- the real
CI/production target is PostgreSQL via testcontainers (09 §2.2), which is
the only place row-level security itself can be exercised (SQLite has no
RLS at all).

[NOTE -- real bug found while writing this test.] `starlette.testclient
.TestClient` manages its own internal event loop for the ASGI app, separate
from whatever loop a test's own `await`s run in. aiosqlite's connections are
loop-bound; seeding the schema via a plain `asyncio.run(...)` call (a THIRD
loop) before using `TestClient` made the seeded rows invisible to the
app's own requests even with `poolclass=StaticPool` -- StaticPool keeps one
Python connection *object* alive, but a connection created under one event
loop is not usable from another. Using `httpx.AsyncClient` with
`ASGITransport` instead keeps the whole test -- seeding and requests alike
-- on the ONE loop pytest-asyncio provides for an `async def` test.
"""

from __future__ import annotations

import datetime as dt
import uuid

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
from fathom_pdm.models import Base, ScoringRun
from fathom_py_common.idempotency import IdempotencyBase
from fathom_sync import Base as SyncBase
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker


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
    def _register_least(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
        dbapi_connection.create_function("LEAST", 2, min)

    async with app.state.engine.begin() as conn:
        # `fathom_sync.Base` (outbox/inbox/producer_sequence) is a SEPARATE
        # DeclarativeBase from PdM's own `Base` -- both metadatas must be
        # created. Alembic's real migration (services/pdm/src/fathom_pdm/
        # migrations/versions/) must do the same in its `upgrade()`.
        await conn.run_sync(SyncBase.metadata.create_all)
        await conn.run_sync(IdempotencyBase.metadata.create_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield app, client

    await app.state.engine.dispose()


async def _seed_scoring_run(app, scoring_run_id: uuid.UUID) -> None:
    maker = async_sessionmaker(app.state.engine, expire_on_commit=False)
    async with maker() as session:
        now = dt.datetime.now(dt.UTC)
        session.add(
            ScoringRun(
                scoring_run_id=scoring_run_id,
                stratum="operational",
                trigger="on_demand",
                scope={"asset_ids": []},
                baseline_epoch_at_start={},
                feature_definition_time=now,
                domino_execution_ref="domino-job-test-run",
                read_model_lag_at_start={},
                status="running",
                classification={"level": "U"},
            )
        )
        await session.commit()


def _prediction_payload(*, asset_id: str, installed_item_id: str) -> dict:
    now = dt.datetime.now(dt.UTC).isoformat()
    return {
        "asset_id": asset_id,
        "installed_item_id": installed_item_id,
        "position_id": str(uuid.uuid4()),
        "niin": "012345678",
        "equipment_family": "pump-centrifugal",
        "baseline_id": str(uuid.uuid4()),
        "baseline_epoch": 1,
        "horizon_days": 90,
        "p_failure": 0.15,
        "reference_class": "item",
        "sharpness": 0.5,
        "calibration_population": 120,
        "rul": {"p10": 10, "p50": 40, "p90": 90, "unit": "days"},
        "population_hazard_rate": None,
        "confidence": 0.8,
        "fallback_level": 0,
        "tier": 2,
        "contributing_factors": [],
        "model_version": "tier2-degradation-1.0.0",
        "scoring_run_id": str(uuid.uuid4()),
        "computed_at": now,
    }


@pytest.mark.asyncio
async def test_bulk_ingest_then_get_prediction(app_and_client) -> None:
    app, client = app_and_client
    scoring_run_id = uuid.uuid4()
    await _seed_scoring_run(app, scoring_run_id)

    asset_id = str(uuid.uuid4())
    installed_item_id = str(uuid.uuid4())
    payload = {"predictions": [_prediction_payload(asset_id=asset_id, installed_item_id=installed_item_id)]}

    resp = await client.post(
        f"/api/v1/pdm/scoring-runs/{scoring_run_id}/predictions",
        json=payload,
        headers={"Idempotency-Key": "ingest-1", "X-Fathom-Principal": "domino-job-test"},
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["predictions_written"] == 1
    assert body["predictions_rejected"] == 0

    # Replay with the same Idempotency-Key must not double-write.
    resp2 = await client.post(
        f"/api/v1/pdm/scoring-runs/{scoring_run_id}/predictions",
        json=payload,
        headers={"Idempotency-Key": "ingest-1", "X-Fathom-Principal": "domino-job-test"},
    )
    assert resp2.headers.get("Idempotency-Replayed") == "true"
    assert resp2.json() == body


@pytest.mark.asyncio
async def test_bulk_ingest_rejects_missing_idempotency_key(app_and_client) -> None:
    app, client = app_and_client
    scoring_run_id = uuid.uuid4()
    await _seed_scoring_run(app, scoring_run_id)
    payload = {
        "predictions": [
            _prediction_payload(asset_id=str(uuid.uuid4()), installed_item_id=str(uuid.uuid4()))
        ]
    }
    resp = await client.post(f"/api/v1/pdm/scoring-runs/{scoring_run_id}/predictions", json=payload)
    assert resp.status_code == 400
    assert resp.json()["type"] == "urn:fathom:problem:common:idempotency-key-required"


@pytest.mark.asyncio
async def test_bulk_ingest_unknown_scoring_run_is_404(app_and_client) -> None:
    _app, client = app_and_client
    payload = {
        "predictions": [
            _prediction_payload(asset_id=str(uuid.uuid4()), installed_item_id=str(uuid.uuid4()))
        ]
    }
    resp = await client.post(
        f"/api/v1/pdm/scoring-runs/{uuid.uuid4()}/predictions",
        json=payload,
        headers={"Idempotency-Key": "k", "X-Fathom-Principal": "p"},
    )
    assert resp.status_code == 404
    assert resp.json()["type"] == "urn:fathom:problem:pdm:scoring-run-not-found"
