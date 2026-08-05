"""End-to-end: the real app, real HTTP requests, §5.6's binding-refusal
logic and the non-Postgres-specific half of its activation effects
(deactivate the superseded binding, queue a re-score, publish
`model_binding.activated`).

SQLite for speed (see tests/conftest.py's rationale, and
test_bulk_ingest_e2e.py's own precedent for business-logic end-to-end tests
living here despite not using a real Postgres container). Deliberately NOT
covered here: actually invalidating the superseded binding's predictions,
which calls `pdm.invalidate_prediction()`, a real SECURITY DEFINER function
that exists only in real PostgreSQL (same boundary
`repositories/prediction.py`'s own docstring already documents for RLS) --
see test_model_binding_grants.py for that half, exercised against a real
container and the actual `fathom_pdm_serving` role.
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
from fathom_pdm.models import (
    Base,
    CalibrationRecord,
    LabelSet,
    ModelBinding,
    PropensityModel,
    ScoringRun,
)
from fathom_py_common.idempotency import IdempotencyBase
from fathom_sync import Base as SyncBase
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
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
        await conn.run_sync(SyncBase.metadata.create_all)
        await conn.run_sync(IdempotencyBase.metadata.create_all)
        await conn.run_sync(Base.metadata.create_all)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield app, client

    await app.state.engine.dispose()


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


async def _seed_label_set(
    app, *, equipment_family: str, taxonomy_version: str, propensity_accepted: bool | None
) -> uuid.UUID:
    """`propensity_accepted=None` seeds a label set with NO propensity model
    at all (the `unaccepted_propensity_model` refusal's other trigger)."""
    maker = async_sessionmaker(app.state.engine, expire_on_commit=False)
    async with maker() as session:
        propensity_model_id = None
        if propensity_accepted is not None:
            propensity_model_id = uuid.uuid4()
            session.add(
                PropensityModel(
                    propensity_model_id=propensity_model_id,
                    spec_version="v1",
                    grid="weekly",
                    policy_version_strata=["v1"],
                    fit_artifact_uri="s3://bucket/propensity/v1",
                    positivity_min_k=5,
                    ess=200,
                    max_stabilized_weight=10,
                    mean_stabilized_weight=1.0,
                    calibration_of_propensity={},
                    pms_sensitivity={},
                    accepted=propensity_accepted,
                    fitted_at=_now(),
                )
            )
        label_set_id = uuid.uuid4()
        session.add(
            LabelSet(
                label_set_id=label_set_id,
                equipment_family=equipment_family,
                taxonomy_version=taxonomy_version,
                window_start=_now(),
                window_end=_now(),
                stratum="treated",
                propensity_model_id=propensity_model_id,
                artifact_uri="s3://bucket/label-sets/v1",
                feature_definition_time=_now(),
                feature_data_time_max=_now(),
                ipcw_summary={},
                built_at=_now(),
                classification={"level": "U"},
            )
        )
        await session.commit()
    return label_set_id


async def _seed_calibration_record(
    app, *, tier: int, equipment_family: str, taxonomy_version: str, powered: bool
) -> None:
    maker = async_sessionmaker(app.state.engine, expire_on_commit=False)
    async with maker() as session:
        session.add(
            CalibrationRecord(
                tier=tier,
                equipment_family=equipment_family,
                horizon_days=90,
                reference_class="niin_fleet",
                taxonomy_version=taxonomy_version,
                stratum="treated",
                calibration_population=200,
                effective_sample_size=180,
                events_observed=40,
                powered=powered,
                gate_passed=True,
                method="isotonic",
                reliability_curve={},
                weighted_calibration_error=0.02,
                unweighted_calibration_error=0.05,
                drift_state="stable",
                drift_evidence={},
                computed_at=_now(),
                window_start=_now(),
                window_end=_now(),
                classification={"level": "U"},
            )
        )
        await session.commit()


def _headers() -> dict[str, str]:
    return {"Idempotency-Key": str(uuid.uuid4()), "X-Fathom-Principal": "test-operator"}


async def _create_binding(
    client, *, tier: int, equipment_family: str, taxonomy_version: str, label_set_id: uuid.UUID
) -> dict:
    resp = await client.post(
        "/api/v1/pdm/model-bindings",
        json={
            "tier": tier,
            "equipment_family": equipment_family,
            "taxonomy_version": taxonomy_version,
            "registry_model_version": "v1",
            "registry_model_uri": "domino://registered-models/pdm-tier0/v1",
            "approval_ref": "governance-ref-1",
            "label_set_id": str(label_set_id),
        },
        headers=_headers(),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_activate_refuses_on_unaccepted_propensity_model(app_and_client) -> None:
    app, client = app_and_client
    label_set_id = await _seed_label_set(
        app, equipment_family="pump-centrifugal", taxonomy_version="tax-1", propensity_accepted=False
    )
    binding = await _create_binding(
        client, tier=0, equipment_family="pump-centrifugal", taxonomy_version="tax-1", label_set_id=label_set_id
    )

    resp = await client.post(
        f"/api/v1/pdm/model-bindings/{binding['binding_id']}/activate", headers=_headers()
    )
    assert resp.status_code == 409, resp.text
    assert (
        resp.json()["type"]
        == "urn:fathom:problem:pdm:model-binding-refused:unaccepted_propensity_model"
    )


@pytest.mark.asyncio
async def test_activate_refuses_when_label_set_has_no_propensity_model(app_and_client) -> None:
    app, client = app_and_client
    label_set_id = await _seed_label_set(
        app, equipment_family="pump-centrifugal", taxonomy_version="tax-1", propensity_accepted=None
    )
    binding = await _create_binding(
        client, tier=0, equipment_family="pump-centrifugal", taxonomy_version="tax-1", label_set_id=label_set_id
    )

    resp = await client.post(
        f"/api/v1/pdm/model-bindings/{binding['binding_id']}/activate", headers=_headers()
    )
    assert resp.status_code == 409, resp.text
    assert (
        resp.json()["type"]
        == "urn:fathom:problem:pdm:model-binding-refused:unaccepted_propensity_model"
    )


@pytest.mark.asyncio
async def test_activate_refuses_on_unpowered_family(app_and_client) -> None:
    app, client = app_and_client
    label_set_id = await _seed_label_set(
        app, equipment_family="pump-centrifugal", taxonomy_version="tax-1", propensity_accepted=True
    )
    # A calibration record exists for the triple, but not a POWERED one.
    await _seed_calibration_record(
        app, tier=0, equipment_family="pump-centrifugal", taxonomy_version="tax-1", powered=False
    )
    binding = await _create_binding(
        client, tier=0, equipment_family="pump-centrifugal", taxonomy_version="tax-1", label_set_id=label_set_id
    )

    resp = await client.post(
        f"/api/v1/pdm/model-bindings/{binding['binding_id']}/activate", headers=_headers()
    )
    assert resp.status_code == 409, resp.text
    assert (
        resp.json()["type"]
        == "urn:fathom:problem:pdm:model-binding-refused:unpowered_label_set_family"
    )


@pytest.mark.asyncio
async def test_activate_refuses_when_no_calibration_record_for_triple(app_and_client) -> None:
    app, client = app_and_client
    label_set_id = await _seed_label_set(
        app, equipment_family="pump-centrifugal", taxonomy_version="tax-1", propensity_accepted=True
    )
    # Powered, but for a DIFFERENT family -- the family-scoped powered check
    # passes, the triple-scoped existence check must still refuse.
    await _seed_calibration_record(
        app, tier=0, equipment_family="pump-centrifugal", taxonomy_version="tax-1", powered=True
    )
    binding = await _create_binding(
        client, tier=1, equipment_family="pump-centrifugal", taxonomy_version="tax-1", label_set_id=label_set_id
    )

    resp = await client.post(
        f"/api/v1/pdm/model-bindings/{binding['binding_id']}/activate", headers=_headers()
    )
    assert resp.status_code == 409, resp.text
    assert (
        resp.json()["type"] == "urn:fathom:problem:pdm:model-binding-refused:no_calibration_record"
    )


@pytest.mark.asyncio
async def test_activate_succeeds_and_is_idempotent_against_reactivation(app_and_client) -> None:
    app, client = app_and_client
    label_set_id = await _seed_label_set(
        app, equipment_family="pump-centrifugal", taxonomy_version="tax-1", propensity_accepted=True
    )
    await _seed_calibration_record(
        app, tier=0, equipment_family="pump-centrifugal", taxonomy_version="tax-1", powered=True
    )
    binding = await _create_binding(
        client, tier=0, equipment_family="pump-centrifugal", taxonomy_version="tax-1", label_set_id=label_set_id
    )

    resp = await client.post(
        f"/api/v1/pdm/model-bindings/{binding['binding_id']}/activate", headers=_headers()
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["activated_at"] is not None

    # A second activate call on the same, already-active binding must
    # refuse rather than silently double-fire the effects below.
    resp2 = await client.post(
        f"/api/v1/pdm/model-bindings/{binding['binding_id']}/activate", headers=_headers()
    )
    assert resp2.status_code == 409, resp2.text
    assert resp2.json()["type"] == "urn:fathom:problem:pdm:model-binding-already-activated"


@pytest.mark.asyncio
async def test_activating_a_new_binding_supersedes_the_old_one(app_and_client) -> None:
    """§8.1's `binding_deactivated` trigger: activating binding B for a
    triple that binding A already actively serves must deactivate A and
    queue a `binding_activation` re-score, inside binding B's own
    activation, not a separate step. (The other half of this trigger --
    that A's own active predictions get genuinely invalidated -- needs the
    real `pdm.invalidate_prediction()` function and is covered in
    test_model_binding_grants.py instead.)"""
    app, client = app_and_client
    label_set_id = await _seed_label_set(
        app, equipment_family="pump-centrifugal", taxonomy_version="tax-1", propensity_accepted=True
    )
    await _seed_calibration_record(
        app, tier=0, equipment_family="pump-centrifugal", taxonomy_version="tax-1", powered=True
    )

    binding_a = await _create_binding(
        client, tier=0, equipment_family="pump-centrifugal", taxonomy_version="tax-1", label_set_id=label_set_id
    )
    resp_a = await client.post(
        f"/api/v1/pdm/model-bindings/{binding_a['binding_id']}/activate", headers=_headers()
    )
    assert resp_a.status_code == 200, resp_a.text

    binding_b = await _create_binding(
        client, tier=0, equipment_family="pump-centrifugal", taxonomy_version="tax-1", label_set_id=label_set_id
    )
    resp_b = await client.post(
        f"/api/v1/pdm/model-bindings/{binding_b['binding_id']}/activate", headers=_headers()
    )
    assert resp_b.status_code == 200, resp_b.text

    maker = async_sessionmaker(app.state.engine, expire_on_commit=False)
    async with maker() as session:
        refreshed_a = (
            await session.execute(
                select(ModelBinding).where(ModelBinding.binding_id == uuid.UUID(binding_a["binding_id"]))
            )
        ).scalar_one()
        assert refreshed_a.deactivated_at is not None

        rescore_runs = (
            (await session.execute(select(ScoringRun).where(ScoringRun.trigger == "binding_activation")))
            .scalars()
            .all()
        )
        assert len(rescore_runs) == 1
        assert rescore_runs[0].status == "queued"
        # SQLite's JSON-backed variant round-trips these as plain strings,
        # not `uuid.UUID` (unlike the real ARRAY(UUID) Postgres column) --
        # compare as strings so this test holds on both dialects.
        assert [str(b) for b in rescore_runs[0].model_bindings] == [binding_b["binding_id"]]
