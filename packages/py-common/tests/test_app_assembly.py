import datetime as dt

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from fathom_contracts import SideEffects, Substitution, operation_extra
from fathom_py_common import (
    ProblemException,
    assert_operation_annotations,
    fathom_operation_id,
    install_classification_middleware,
    install_correlation_middleware,
    install_health_routes,
    install_idempotency_middleware,
    install_problem_handlers,
    make_check,
    persist_idempotent_response,
)
from fathom_py_common.idempotency import IdempotencyBase
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool


@pytest.fixture(autouse=True)
def _clear_operation_registry() -> None:
    """`fathom_contracts.operation.REGISTRY` is process-global (by design --
    it exists so a real service's own single `main.py` assembly catches a
    duplicate operationId at import time). Tests that rebuild an app
    per-test need to reset it between runs; production code never does."""
    from fathom_contracts.operation import REGISTRY

    REGISTRY.clear()


def _build_app() -> FastAPI:
    app = FastAPI(generate_unique_id_function=fathom_operation_id("pdm"))

    install_correlation_middleware(app)
    install_problem_handlers(app, slug="pdm")
    install_classification_middleware(app)
    install_idempotency_middleware(app)

    @app.get(
        "/api/v1/pdm/predictions",
        openapi_extra=operation_extra(
            operation_id="pdm_list_predictions",
            substitution=Substitution.REQUIRED,
            side_effects=SideEffects.NONE,
            summary="List predictions",
            agent_eligible=True,
        ),
    )
    async def list_predictions() -> dict[str, list[object]]:
        return {"items": []}

    @app.get(
        "/api/v1/pdm/predictions/{prediction_id}",
        openapi_extra=operation_extra(
            operation_id="pdm_get_prediction",
            substitution=Substitution.REQUIRED,
            side_effects=SideEffects.NONE,
            summary="Get one prediction",
        ),
    )
    async def get_prediction(prediction_id: str) -> dict[str, str]:
        if prediction_id == "missing":
            raise ProblemException(
                type="urn:fathom:problem:pdm:prediction-not-actionable",
                title="Prediction not found",
                status=404,
            )
        return {"prediction_id": prediction_id}

    async def _db_check() -> tuple[bool, str | None]:
        return True, None

    install_health_routes(app, checks=[make_check("database", _db_check)])
    assert_operation_annotations(app)
    return app


def test_app_assembles_and_asserts_annotations() -> None:
    app = _build_app()
    client = TestClient(app)

    resp = client.get("/api/v1/pdm/predictions")
    assert resp.status_code == 200
    assert "X-Correlation-Id" in resp.headers


def test_correlation_id_echoed_and_generated_when_absent() -> None:
    client = TestClient(_build_app())
    resp = client.get("/api/v1/pdm/predictions", headers={"X-Correlation-Id": "my-corr-id"})
    assert resp.headers["X-Correlation-Id"] == "my-corr-id"

    resp2 = client.get("/api/v1/pdm/predictions")
    assert resp2.headers["X-Correlation-Id"]  # minted, non-empty


def test_problem_exception_produces_rfc9457_body() -> None:
    client = TestClient(_build_app())
    resp = client.get("/api/v1/pdm/predictions/missing")
    assert resp.status_code == 404
    assert resp.headers["content-type"] == "application/problem+json"
    body = resp.json()
    assert body["type"] == "urn:fathom:problem:pdm:prediction-not-actionable"
    assert body["status"] == 404


def test_readyz_reports_degraded_when_a_check_fails() -> None:
    app = FastAPI()

    async def _failing_check() -> tuple[bool, str | None]:
        return False, "broker unreachable"

    install_health_routes(app, checks=[make_check("broker", _failing_check)])
    client = TestClient(app)
    resp = client.get("/readyz")
    assert resp.status_code == 503
    body = resp.json()
    assert body["checks"]["broker"]["healthy"] is False


def test_missing_annotation_fails_startup() -> None:
    app = FastAPI()

    @app.get("/api/v1/pdm/unannotated")
    async def unannotated() -> dict[str, str]:
        return {}

    with pytest.raises(RuntimeError, match="missing"):
        assert_operation_annotations(app)


@pytest.mark.asyncio
async def test_idempotency_key_required_on_state_changing_operation() -> None:
    # httpx.AsyncClient + ASGITransport, not starlette's TestClient: TestClient
    # manages its OWN internal event loop for dispatching ASGI calls, separate
    # from this test function's own pytest-asyncio loop. aiosqlite connections
    # are loop-bound, so a session/engine created in this test's loop and then
    # used via TestClient's different loop silently talks to a different
    # in-memory database. Keeping everything on the one loop this async test
    # runs under is what makes the seeded schema and the request handler agree.
    app = FastAPI()
    install_correlation_middleware(app)
    install_problem_handlers(app, slug="pdm")
    install_idempotency_middleware(app)

    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(IdempotencyBase.metadata.create_all)

    from sqlalchemy.ext.asyncio import async_sessionmaker

    maker = async_sessionmaker(engine, expire_on_commit=False)

    @app.middleware("http")
    async def _attach_session(request, call_next):  # type: ignore[no-untyped-def]
        async with maker() as session:
            request.state.db_session = session
            response = await call_next(request)
            await session.commit()
            return response

    @app.post(
        "/api/v1/pdm/scoring-runs/{run_id}/predictions",
        openapi_extra=operation_extra(
            operation_id="pdm_bulk_ingest_predictions",
            substitution=Substitution.REQUIRED,
            side_effects=SideEffects.STATE_CHANGING,
            summary="Bulk ingest",
        ),
    )
    async def bulk_ingest(request: Request, run_id: str) -> dict[str, str]:
        body = {"run_id": run_id, "at": dt.datetime.now(dt.UTC).isoformat()}
        await persist_idempotent_response(request, body, 200)
        return body

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/api/v1/pdm/scoring-runs/r1/predictions")
        assert resp.status_code == 400
        assert resp.json()["type"] == "urn:fathom:problem:common:idempotency-key-required"

        resp2 = await client.post(
            "/api/v1/pdm/scoring-runs/r1/predictions",
            headers={"Idempotency-Key": "key-1", "X-Fathom-Principal": "svc-a"},
        )
        assert resp2.status_code == 200
        first_body = resp2.json()

        # Replay: same key, same body -> replayed, not re-executed (same timestamp).
        resp3 = await client.post(
            "/api/v1/pdm/scoring-runs/r1/predictions",
            headers={"Idempotency-Key": "key-1", "X-Fathom-Principal": "svc-a"},
        )
        assert resp3.headers.get("Idempotency-Replayed") == "true"
        assert resp3.json() == first_body

    await engine.dispose()
