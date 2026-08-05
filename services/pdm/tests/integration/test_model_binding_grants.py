"""22-pdm.md §5.6, exercised against a real PostgreSQL connection
authenticated as `fathom_pdm_serving` -- the role the running service
actually uses, not the migration-owning superuser. Mirrors
test_event_consumers.py's own pattern and its own reason for existing:
"a newly created table grants nothing beyond its owner by default" (HANDOFF
bug #11) was only ever caught this way, not by reading the migration.

This is the first place a permission-denied on `pdm.propensity_model`,
`pdm.label_set`, or `pdm.model_binding` -- had this migration's grants been
wrong or missing -- would actually surface.
"""

from __future__ import annotations

import datetime as dt
import os
import uuid
from typing import TYPE_CHECKING

import psycopg
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from fathom_pdm.models import (
    CalibrationRecord,
    LabelSet,
    Prediction,
    PredictionProvenance,
    PropensityModel,
    ScoringRun,
)
from fathom_pdm.repositories.model_binding import ModelBindingRepository
from fathom_pdm.repositories.prediction import PredictionRepository
from fathom_pdm.services import model_binding as model_binding_service
from fathom_pdm.signer import EnvelopeSigner
from fathom_schemas import ClassificationLabel, ClassificationLevel
from fathom_sync import OutboxWriter, UnitOfWork
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.postgres import PostgresContainer

if TYPE_CHECKING:
    from collections.abc import Iterator

_SERVICE_ROOT = __file__.rsplit("/tests/", 1)[0]

_ENV_DEFAULTS = {
    "FATHOM_EVENTS__BROKERS": "test-broker:9093",
    "FATHOM_EVENTS__SCHEMA_REGISTRY": "http://test-schema-registry",
    "FATHOM_AUTH__ISSUER": "https://test-issuer",
    "FATHOM_AUTH__JWKS_URL": "https://test-issuer/jwks",
    "FATHOM_AUDIT__BASE_URL": "http://test-audit",
    "FATHOM_REFERENCE_DATA__BASE_URL": "http://test-reference-data",
}


@pytest.fixture(scope="module")
def pg_container() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        "postgres:16-alpine", dbname="pdm", username="pdm_owner", password="pdm_owner"  # noqa: S106
    ) as pg:
        yield pg


@pytest.fixture(scope="module")
def owner_dsn(pg_container: PostgresContainer) -> str:
    host = pg_container.get_container_host_ip()
    port = pg_container.get_exposed_port(5432)
    async_url = f"postgresql+asyncpg://pdm_owner:pdm_owner@{host}:{port}/pdm"

    prior = os.environ.get("FATHOM_DATABASE__URL")
    os.environ["FATHOM_DATABASE__URL"] = async_url
    for key, value in _ENV_DEFAULTS.items():
        os.environ.setdefault(key, value)
    try:
        cfg = Config(f"{_SERVICE_ROOT}/alembic.ini")
        cfg.set_main_option("script_location", f"{_SERVICE_ROOT}/src/fathom_pdm/migrations")
        command.upgrade(cfg, "head")
    finally:
        if prior is None:
            os.environ.pop("FATHOM_DATABASE__URL", None)
        else:
            os.environ["FATHOM_DATABASE__URL"] = prior

    return f"postgresql://pdm_owner:pdm_owner@{host}:{port}/pdm"


@pytest.fixture(scope="module")
def serving_async_url(pg_container: PostgresContainer, owner_dsn: str) -> Iterator[str]:
    with psycopg.connect(owner_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("CREATE ROLE test_binding_login LOGIN PASSWORD 'binding'")
        cur.execute("GRANT fathom_pdm_serving TO test_binding_login")

    host = pg_container.get_container_host_ip()
    port = pg_container.get_exposed_port(5432)
    yield f"postgresql+asyncpg://test_binding_login:binding@{host}:{port}/pdm"

    with psycopg.connect(owner_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("REVOKE fathom_pdm_serving FROM test_binding_login")
        cur.execute("DROP ROLE test_binding_login")


@pytest_asyncio.fixture
async def session(serving_async_url: str) -> AsyncSession:
    """Every query in this fixture's session runs AS `fathom_pdm_serving`."""
    engine = create_async_engine(serving_async_url)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def owner_session(owner_dsn: str) -> AsyncSession:
    async_url = owner_dsn.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def _seed_powered_family(
    owner_session: AsyncSession, *, equipment_family: str, taxonomy_version: str
) -> uuid.UUID:
    """As the owner (standing in for whatever process would eventually run
    the label/propensity/calibration pipeline -- not `fathom_pdm_serving`,
    which per this migration's grants can only ever READ these three)."""
    now = dt.datetime.now(dt.UTC)
    propensity_model_id = uuid.uuid4()
    owner_session.add(
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
            accepted=True,
            fitted_at=now,
        )
    )
    # Flushed separately: `label_set.propensity_model_id` is a plain FK
    # column, not an ORM `relationship()`, so autoflush ordering has no
    # dependency graph to sort by -- without this, the two inserts can
    # (and did, once observed against a real container) land in either
    # order in the same flush, and label_set's insert 500s with a real FK
    # violation whenever it loses the race.
    await owner_session.flush()
    label_set_id = uuid.uuid4()
    owner_session.add(
        LabelSet(
            label_set_id=label_set_id,
            equipment_family=equipment_family,
            taxonomy_version=taxonomy_version,
            window_start=now,
            window_end=now,
            stratum="treated",
            propensity_model_id=propensity_model_id,
            artifact_uri="s3://bucket/label-sets/v1",
            feature_definition_time=now,
            feature_data_time_max=now,
            ipcw_summary={},
            built_at=now,
            classification={"level": "U"},
        )
    )
    owner_session.add(
        CalibrationRecord(
            tier=0,
            equipment_family=equipment_family,
            horizon_days=90,
            reference_class="niin_fleet",
            taxonomy_version=taxonomy_version,
            stratum="treated",
            calibration_population=200,
            effective_sample_size=180,
            events_observed=40,
            powered=True,
            gate_passed=True,
            method="isotonic",
            reliability_curve={},
            weighted_calibration_error=0.02,
            unweighted_calibration_error=0.05,
            drift_state="stable",
            drift_evidence={},
            computed_at=now,
            window_start=now,
            window_end=now,
            classification={"level": "U"},
        )
    )
    await owner_session.commit()
    return label_set_id


@pytest.mark.asyncio
async def test_create_and_activate_binding_as_serving_role(
    session: AsyncSession, owner_session: AsyncSession
) -> None:
    label_set_id = await _seed_powered_family(
        owner_session, equipment_family="pump-centrifugal", taxonomy_version="tax-1"
    )

    binding_repo = ModelBindingRepository()
    prediction_repo = PredictionRepository()
    uow = UnitOfWork(session)
    outbox = OutboxWriter(
        producer_slug="pdm",
        producer_version="1.0",
        producer_node_id="enterprise",
        signer=EnvelopeSigner(),
    )

    # INSERT on pdm.model_binding, as fathom_pdm_serving -- would fail with
    # "permission denied for table model_binding" if this migration's grant
    # were missing, exactly as bug #11 did for pdm.scoring_run before it
    # was fixed.
    binding = await model_binding_service.create_binding(
        uow,
        binding_repo,
        tier=0,
        equipment_family="pump-centrifugal",
        taxonomy_version="tax-1",
        registry_model_version="v1",
        registry_model_uri="domino://registered-models/pdm-tier0/v1",
        approval_ref="governance-ref-1",
        label_set_id=label_set_id,
    )
    await session.commit()

    # SELECT on pdm.propensity_model and pdm.label_set (the §5.6 refusal
    # checks), UPDATE on pdm.model_binding (activation) -- all as
    # fathom_pdm_serving.
    activated = await model_binding_service.activate_binding(
        uow,
        outbox,
        binding_repo,
        prediction_repo,
        binding_id=binding.binding_id,
        classification=ClassificationLabel(level=ClassificationLevel.U),
    )
    await session.commit()
    assert activated.activated_at is not None

    reloaded = await binding_repo.get_by_id(owner_session, binding.binding_id)
    assert reloaded is not None
    assert reloaded.activated_at is not None


async def _seed_active_prediction_for_binding(
    owner_session: AsyncSession, *, model_binding_id: uuid.UUID
) -> uuid.UUID:
    now = dt.datetime.now(dt.UTC)
    scoring_run_id = uuid.uuid4()
    owner_session.add(
        ScoringRun(
            scoring_run_id=scoring_run_id,
            stratum="operational",
            trigger="scheduled",
            scope={},
            baseline_epoch_at_start={},
            feature_definition_time=now,
            domino_execution_ref="test-run",
            read_model_lag_at_start={},
            status="published",
            classification={"level": "U"},
        )
    )
    # Same reason as `_seed_powered_family`'s own flush: these are plain FK
    # columns, not ORM `relationship()`s, so autoflush has no dependency
    # graph to order these three inserts by.
    await owner_session.flush()
    provenance_id = uuid.uuid4()
    owner_session.add(
        PredictionProvenance(
            provenance_id=provenance_id,
            scoring_run_id=scoring_run_id,
            model_binding_id=model_binding_id,
            label_set_id=uuid.uuid4(),
            gate_decision={},
            feature_observations={},
            feature_definition_time=now,
            fallback_path={},
            suppressed_factor_count=0,
            suppressed_factors=[],
            read_model_lag={},
            classification={"level": "U"},
        )
    )
    await owner_session.flush()
    prediction_id = uuid.uuid4()
    owner_session.add(
        Prediction(
            prediction_id=prediction_id,
            scoring_run_id=scoring_run_id,
            asset_id=uuid.uuid4(),
            installed_item_id=uuid.uuid4(),
            position_id=uuid.uuid4(),
            niin="012345678",
            equipment_family="pump-centrifugal",
            baseline_id=uuid.uuid4(),
            baseline_epoch=1,
            horizon_days=90,
            p_failure=None,
            reference_class="niin_fleet",
            sharpness=0.5,
            calibration_population=200,
            population_hazard_rate=0.01,
            confidence=0.7,
            fallback_level=1,
            tier=0,
            contributing_factors=[],
            model_version="tier0-1.0.0",
            computed_at=now,
            status="active",
            serving_class="actionable",
            provenance_id=provenance_id,
            classification={"level": "U"},
        )
    )
    await owner_session.commit()
    return prediction_id


@pytest.mark.asyncio
async def test_activation_invalidates_superseded_binding_predictions_via_real_function(
    session: AsyncSession, owner_session: AsyncSession
) -> None:
    """The other half of §8.1's `binding_deactivated` trigger that
    test_model_binding_e2e.py's SQLite suite cannot cover: `pdm
    .invalidate_prediction()` is a real `SECURITY DEFINER` function, not
    ORM-portable SQL (`repositories/prediction.py`'s own docstring). Only a
    real Postgres connection, authenticated as the actual
    `fathom_pdm_serving` role, proves the superseded binding's predictions
    are genuinely invalidated -- not merely that `activate_binding` runs
    without raising."""
    label_set_id = await _seed_powered_family(
        owner_session, equipment_family="pump-centrifugal-2", taxonomy_version="tax-1"
    )
    binding_repo = ModelBindingRepository()
    prediction_repo = PredictionRepository()
    uow = UnitOfWork(session)
    outbox = OutboxWriter(
        producer_slug="pdm", producer_version="1.0", producer_node_id="enterprise", signer=EnvelopeSigner()
    )
    classification = ClassificationLabel(level=ClassificationLevel.U)

    binding_a = await model_binding_service.create_binding(
        uow,
        binding_repo,
        tier=0,
        equipment_family="pump-centrifugal-2",
        taxonomy_version="tax-1",
        registry_model_version="v1",
        registry_model_uri="domino://registered-models/pdm-tier0/v1",
        approval_ref="governance-ref-1",
        label_set_id=label_set_id,
    )
    await session.commit()
    await model_binding_service.activate_binding(
        uow, outbox, binding_repo, prediction_repo, binding_id=binding_a.binding_id,
        classification=classification,
    )
    await session.commit()

    prediction_id = await _seed_active_prediction_for_binding(
        owner_session, model_binding_id=binding_a.binding_id
    )

    binding_b = await model_binding_service.create_binding(
        uow,
        binding_repo,
        tier=0,
        equipment_family="pump-centrifugal-2",
        taxonomy_version="tax-1",
        registry_model_version="v2",
        registry_model_uri="domino://registered-models/pdm-tier0/v2",
        approval_ref="governance-ref-2",
        label_set_id=label_set_id,
    )
    await session.commit()
    await model_binding_service.activate_binding(
        uow, outbox, binding_repo, prediction_repo, binding_id=binding_b.binding_id,
        classification=classification,
    )
    await session.commit()

    superseded = (
        await owner_session.execute(select(Prediction).where(Prediction.prediction_id == prediction_id))
    ).scalar_one()
    assert superseded.status == "invalidated"
    assert superseded.invalidation_cause == "binding_deactivated"
