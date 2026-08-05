"""22-pdm.md §8.1's two externally-evented invalidation triggers, exercised
against a real PostgreSQL connection authenticated as `fathom_pdm_serving`
-- the role the running service actually uses -- not the migration-owning
superuser every other integration test in this session used until now.

[NOTE -- real bug found while writing this test.] Connecting as
`fathom_pdm_serving` instead of the superuser for the first time surfaced
that this role had a grant on `pdm.prediction` alone: every other table its
own code touches (`scoring_run`, `prediction_provenance`,
`criticality_assessment`, `inbox`, `outbox`, `producer_sequence`,
`idempotency_keys`) had no grant to it at all, so bulk ingest, the
idempotency middleware, the monotonic sequencer, and every inbox-consuming
handler would have failed with "permission denied" in a real deployment.
Fixed in the migration and in `docs/build/22-pdm.md` §4.5 -- see the
migration's own comment for the full account. This test is the first place
that failure mode would have actually been caught.
"""

from __future__ import annotations

import datetime as dt
import itertools
import os
import uuid
from typing import TYPE_CHECKING

import confluent_kafka
import psycopg
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from fathom_pdm.events.consumers import (
    ConfigurationBaselineChanged,
    InstalledItemRemoved,
    UnhandledEventTypeError,
    dispatch_event,
    handle_configuration_baseline_changed,
    handle_installed_item_removed,
)
from fathom_pdm.signer import EnvelopeSigner
from fathom_schemas import (
    ClassificationLabel,
    ClassificationLevel,
    Clock,
    EventEnvelope,
    EventScope,
    EventSubject,
    HybridLogicalClock,
    ProducerRef,
    SubAppSlug,
    SyncQuality,
    TimeSource,
)
from fathom_sync import InboundConsumer, OutboxRelay, OutboxWriter, UnitOfWork
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.community.kafka import KafkaContainer
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
        "postgres:16-alpine",
        dbname="pdm",
        username="pdm_owner",
        password="pdm_owner",  # noqa: S106
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
    """A login role that's a member of `fathom_pdm_serving` -- standing in
    for the real service credential, exactly as the RLS test suite does."""
    with psycopg.connect(owner_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("CREATE ROLE test_consumer_login LOGIN PASSWORD 'consumer'")
        cur.execute("GRANT fathom_pdm_serving TO test_consumer_login")

    host = pg_container.get_container_host_ip()
    port = pg_container.get_exposed_port(5432)
    yield f"postgresql+asyncpg://test_consumer_login:consumer@{host}:{port}/pdm"

    with psycopg.connect(owner_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("REVOKE fathom_pdm_serving FROM test_consumer_login")
        cur.execute("DROP ROLE test_consumer_login")


@pytest.fixture(scope="module")
def kafka_container() -> Iterator[KafkaContainer]:
    with KafkaContainer() as kafka:
        yield kafka


@pytest.fixture(scope="module")
def relay_async_url(pg_container: PostgresContainer, owner_dsn: str) -> Iterator[str]:
    """A login role that's a member of `fathom_pdm_relay` -- the role the
    new migration (20260805170000_pdm_outbox_relay.py) actually grants
    SELECT/UPDATE on `outbox` to. Connecting as this role, not the
    migration-owning superuser, is the whole point: every prior grant bug
    in this corpus (#7, #11, #13, #17 -- see CLAUDE.md) was caught only by
    running as the real role, never by reading the GRANT statement."""
    with psycopg.connect(owner_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("CREATE ROLE test_relay_login LOGIN PASSWORD 'relay'")
        cur.execute("GRANT fathom_pdm_relay TO test_relay_login")

    host = pg_container.get_container_host_ip()
    port = pg_container.get_exposed_port(5432)
    yield f"postgresql+asyncpg://test_relay_login:relay@{host}:{port}/pdm"

    with psycopg.connect(owner_dsn, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("REVOKE fathom_pdm_relay FROM test_relay_login")
        cur.execute("DROP ROLE test_relay_login")


@pytest_asyncio.fixture
async def session(serving_async_url: str) -> AsyncSession:
    """Every query in this fixture's session runs AS `fathom_pdm_serving`
    (via role membership) -- this is the point of this test file."""
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


_monotonic_seq = itertools.count(1)


def _envelope(
    event_type: str,
    *,
    subject: EventSubject,
    scope: EventScope,
    producer_slug: SubAppSlug = SubAppSlug.REGISTRY,
) -> EventEnvelope:
    now = dt.datetime.now(dt.UTC)
    return EventEnvelope(
        event_id=uuid.uuid4(),
        event_type=event_type,
        event_version=1,
        occurred_at=now,
        recorded_at=now,
        producer=ProducerRef(slug=producer_slug, version="1.0.0"),
        producer_node="enterprise",
        correlation_id=f"corr-{uuid.uuid4()}",
        scope=scope,
        subject=subject,
        classification=ClassificationLabel(level=ClassificationLevel.U),
        replay=False,
        clock=Clock(
            monotonic_seq=next(_monotonic_seq),
            hlc=HybridLogicalClock(physical=1, logical=0, node_id="enterprise"),
            source_time=now,
            ingest_time=now,
            sync_quality=SyncQuality(
                time_source=TimeSource.GNSS,
                offset_ms=0.1,
                dispersion_ms=1.0,
                seconds_since_sync=1.0,
                step_occurred=False,
            ),
        ),
    )


async def _seed_active_prediction(
    owner_session: AsyncSession, *, installed_item_id: uuid.UUID, horizon_days: int = 30
) -> uuid.UUID:
    scoring_run_id = uuid.uuid4()
    provenance_id = uuid.uuid4()
    prediction_id = uuid.uuid4()

    await owner_session.execute(
        text(
            """
            INSERT INTO pdm.scoring_run (
                scoring_run_id, stratum, trigger, scope, baseline_epoch_at_start,
                model_bindings, label_set_ids, feature_definition_time,
                domino_execution_ref, read_model_lag_at_start, status, classification
            ) VALUES (:id, 'operational', 'scheduled', '{}', '{}', '{}', '{}', now(),
                      'test-run', '{}', 'published', '{}')
            """
        ),
        {"id": scoring_run_id},
    )
    await owner_session.execute(
        text(
            """
            INSERT INTO pdm.prediction_provenance (
                provenance_id, scoring_run_id, model_binding_id, label_set_id,
                gate_decision, feature_observations, feature_definition_time,
                fallback_path, suppressed_factor_count, suppressed_factors,
                read_model_lag, classification
            ) VALUES (:pid, :sid, :mbid, :lsid, '{}', '{}', now(), '{}', 0, '[]', '{}', '{}')
            """
        ),
        {
            "pid": provenance_id,
            "sid": scoring_run_id,
            "mbid": uuid.uuid4(),
            "lsid": uuid.uuid4(),
        },
    )
    await owner_session.execute(
        text(
            """
            INSERT INTO pdm.prediction (
                prediction_id, scoring_run_id, asset_id, installed_item_id, position_id,
                niin, equipment_family, baseline_id, baseline_epoch, horizon_days,
                p_failure, reference_class, sharpness, calibration_population,
                population_hazard_rate, confidence, fallback_level, tier,
                contributing_factors, model_version, computed_at, status,
                serving_class, provenance_id, classification
            ) VALUES (
                :prediction_id, :sid, :asset_id, :installed_item_id, :position_id,
                '000000000', 'test-family', :baseline_id, 1, :horizon_days,
                0.1, 'class_estimate', 0.5, 100,
                0.01, 0.8, 0, 1,
                '[]', 'test-model-v1', now(), 'active',
                'actionable', :pid, '{}'
            )
            """
        ),
        {
            "prediction_id": prediction_id,
            "sid": scoring_run_id,
            "asset_id": uuid.uuid4(),
            "installed_item_id": installed_item_id,
            "position_id": uuid.uuid4(),
            "baseline_id": uuid.uuid4(),
            "horizon_days": horizon_days,
            "pid": provenance_id,
        },
    )
    await owner_session.commit()
    return prediction_id


@pytest.mark.asyncio
async def test_configuration_baseline_changed_invalidates_every_affected_item(
    session: AsyncSession, owner_session: AsyncSession
) -> None:
    item_a = uuid.uuid4()
    item_b = uuid.uuid4()
    pred_a = await _seed_active_prediction(owner_session, installed_item_id=item_a)
    pred_b = await _seed_active_prediction(owner_session, installed_item_id=item_b)

    envelope = _envelope(
        "fathom.registry.configuration_baseline.changed",
        scope=EventScope.FLEET,
        subject=EventSubject(),
    )
    payload = ConfigurationBaselineChanged(
        baseline_id=uuid.uuid4(),
        baseline_epoch=2,
        changed_installed_item_ids=(item_a, item_b),
        effective_date=dt.datetime.now(dt.UTC),
    )

    await handle_configuration_baseline_changed(session, envelope, payload)
    await session.commit()

    for pred_id in (pred_a, pred_b):
        result = await owner_session.execute(
            text("SELECT status, invalidation_cause FROM pdm.prediction WHERE prediction_id = :id"),
            {"id": pred_id},
        )
        status, cause = result.one()
        assert (status, cause) == ("invalidated", "baseline_changed")


@pytest.mark.asyncio
async def test_configuration_baseline_changed_is_idempotent_on_redelivery(
    session: AsyncSession, owner_session: AsyncSession
) -> None:
    item_id = uuid.uuid4()
    await _seed_active_prediction(owner_session, installed_item_id=item_id)

    envelope = _envelope(
        "fathom.registry.configuration_baseline.changed",
        scope=EventScope.FLEET,
        subject=EventSubject(),
    )
    payload = ConfigurationBaselineChanged(
        baseline_id=uuid.uuid4(),
        baseline_epoch=3,
        changed_installed_item_ids=(item_id,),
        effective_date=dt.datetime.now(dt.UTC),
    )

    await handle_configuration_baseline_changed(session, envelope, payload)
    await session.commit()

    # Redelivery of the SAME event_id -- D2: already `processed_at`-marked,
    # so this must be a no-op, not a second (harmless here, but not always)
    # invalidation attempt.
    await handle_configuration_baseline_changed(session, envelope, payload)
    await session.commit()


@pytest.mark.asyncio
async def test_installed_item_removed_invalidates_that_items_predictions(
    session: AsyncSession, owner_session: AsyncSession
) -> None:
    item_id = uuid.uuid4()
    pred_id = await _seed_active_prediction(owner_session, installed_item_id=item_id)

    envelope = _envelope(
        "fathom.registry.installed_item.removed",
        scope=EventScope.INSTALLED_ITEM,
        subject=EventSubject(installed_item_id=item_id, asset_id=uuid.uuid4()),
    )
    payload = InstalledItemRemoved(
        installed_item_id=item_id,
        removal_date=dt.datetime.now(dt.UTC),
        disposition="scrapped",
        failure_indicator=False,
    )

    await handle_installed_item_removed(session, envelope, payload)
    await session.commit()

    result = await owner_session.execute(
        text("SELECT status, invalidation_cause FROM pdm.prediction WHERE prediction_id = :id"),
        {"id": pred_id},
    )
    status, cause = result.one()
    assert (status, cause) == ("invalidated", "item_removed")


@pytest.mark.asyncio
async def test_dispatch_event_raises_for_unwired_event_type(session: AsyncSession) -> None:
    envelope = _envelope(
        "fathom.telemetry.telemetry_batch.ingested",
        scope=EventScope.ASSET,
        subject=EventSubject(asset_id=uuid.uuid4()),
        producer_slug=SubAppSlug.TELEMETRY,
    )
    with pytest.raises(UnhandledEventTypeError):
        await dispatch_event(session, envelope, {})


@pytest.mark.asyncio
async def test_the_whole_chain_for_real_registry_emit_relay_kafka_consumer_dispatch(
    owner_session: AsyncSession,
    relay_async_url: str,
    serving_async_url: str,
    kafka_container: KafkaContainer,
) -> None:
    """The vertical-slice proof for `packages/py-sync`'s new `relay.py`/
    `consumer.py`: a real emitted-and-signed outbox row, relayed through a
    real Kafka broker by a connection authenticated as the new
    `fathom_pdm_relay` role (not the superuser), consumed by a real
    `InboundConsumer`, and dispatched into PdM's own real
    `dispatch_event` -- running as `fathom_pdm_serving`, the role the
    service actually authenticates as in production.

    `producer_slug="registry"` here is a deliberate test-only shortcut:
    Registry doesn't exist as running code, so there is no real Registry
    outbox to relay from. PdM's own outbox table stands in as a convenient
    surface to get a real, signed row onto a real broker -- clearly scoped
    to proving the relay/consumer chain, not Registry's own emit path.
    """
    item_id = uuid.uuid4()
    pred_id = await _seed_active_prediction(owner_session, installed_item_id=item_id)

    topic = f"fathom.registry.installed_item.v1.{uuid.uuid4().hex[:8]}"
    # producer_node_id is deliberately NOT "enterprise" -- this module's
    # other tests hand-construct envelopes for producer_slug="registry"
    # under that exact node id via their own Python-side `_monotonic_seq`
    # counter (never touching the real `producer_sequence` table at all).
    # This is the only test in the module that goes through the REAL
    # `MonotonicSequencer`, so a shared node id would allocate seq=1 twice
    # against the module-scoped Postgres container's `inbox_seq_unique`
    # constraint -- a real collision between two independent sequence
    # sources, not a production bug.
    emitting_outbox = OutboxWriter(
        producer_slug="registry",
        producer_version="1.0",
        producer_node_id="enterprise-relay-proof",
        signer=EnvelopeSigner(),
    )
    now = dt.datetime.now(dt.UTC)
    uow = UnitOfWork(owner_session)
    await emitting_outbox.emit(
        uow,
        event_type="fathom.registry.installed_item.removed",
        event_version=1,
        aggregate="installed_item",
        aggregate_id=str(item_id),
        topic=topic,
        scope=EventScope.INSTALLED_ITEM,
        subject=EventSubject(installed_item_id=item_id, asset_id=uuid.uuid4()),
        payload=InstalledItemRemoved(
            installed_item_id=item_id,
            removal_date=now,
            disposition="scrapped",
            failure_indicator=False,
        ),
        classification=ClassificationLabel(level=ClassificationLevel.U),
        source_time=now,
        recorded_at=now,
        occurred_at=now,
    )
    await owner_session.commit()

    bootstrap = kafka_container.get_bootstrap_server()
    relay_engine = create_async_engine(relay_async_url)
    relay = OutboxRelay(
        producer=confluent_kafka.Producer({"bootstrap.servers": bootstrap}),
        signer=EnvelopeSigner(),
        worker_id="test-relay-worker",
    )
    async with async_sessionmaker(relay_engine, expire_on_commit=False)() as relay_session:
        stats = await relay.run_once(relay_session)
    await relay_engine.dispose()
    assert sum(s.published for s in stats) == 1
    assert sum(s.quarantined for s in stats) == 0

    serving_engine = create_async_engine(serving_async_url)
    serving_maker = async_sessionmaker(serving_engine, expire_on_commit=False)
    consumer = confluent_kafka.Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": "test-pdm-consumer-group",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    inbound = InboundConsumer(consumer=consumer, topics=[topic])

    result = None
    for _ in range(20):
        result = await inbound.poll_and_dispatch(
            serving_maker, dispatch_event, timeout=1.0, unhandled_error_type=UnhandledEventTypeError
        )
        if result.outcome == "dispatched":
            break
    consumer.close()
    await serving_engine.dispose()

    assert result is not None
    assert result.outcome == "dispatched"

    result_row = await owner_session.execute(
        text("SELECT status, invalidation_cause FROM pdm.prediction WHERE prediction_id = :id"),
        {"id": pred_id},
    )
    status, cause = result_row.one()
    assert (status, cause) == ("invalidated", "item_removed")
