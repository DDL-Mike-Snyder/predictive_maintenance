"""Real end-to-end: a real Kafka broker (testcontainers) and a real
Postgres (testcontainers) -- `OutboxRelay` claims and publishes real rows,
`InboundConsumer` subscribes and receives them back, deserialized into the
exact `EventEnvelope` shape `dispatch()` needs. This is the one place the
whole outbox->relay->Kafka->consumer->inbox chain is exercised for real
rather than reviewed as design; SQLite can't stand in here (no `FOR UPDATE
SKIP LOCKED` support, and there is no real broker to substitute for).

Needs Docker reachable -- same requirement as test_rls_holdout_isolation.py
in services/pdm (see that file's own docstring for the Podman/DOCKER_HOST
note if `docker ps` fails).
"""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import AsyncIterator, Iterator

import confluent_kafka
import pytest
import pytest_asyncio
from fathom_schemas import (
    ClassificationLabel,
    ClassificationLevel,
    EventScope,
    EventSubject,
    FathomModel,
)
from fathom_sync.consumer import InboundConsumer
from fathom_sync.models import Base
from fathom_sync.outbox import OutboxWriter, UnitOfWork
from fathom_sync.relay import OutboxRelay
from fathom_sync.testing import InsecureTestSigner
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.community.kafka import KafkaContainer
from testcontainers.community.postgres import PostgresContainer


class _TestPayload(FathomModel):
    message: str


@pytest.fixture(scope="module")
def kafka_container() -> Iterator[KafkaContainer]:
    with KafkaContainer() as kafka:
        yield kafka


@pytest.fixture(scope="module")
def pg_container() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        "postgres:16-alpine",
        dbname="sync",
        username="sync",
        password="sync",  # noqa: S106
    ) as pg:
        yield pg


@pytest_asyncio.fixture
async def session_maker(pg_container: PostgresContainer) -> AsyncIterator[async_sessionmaker]:
    host = pg_container.get_container_host_ip()
    port = pg_container.get_exposed_port(5432)
    engine = create_async_engine(f"postgresql+asyncpg://sync:sync@{host}:{port}/sync")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _unique_topic() -> str:
    return f"fathom.pdm.test_relay.v1.{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_relay_publishes_and_consumer_receives_it(
    session_maker: async_sessionmaker, kafka_container: KafkaContainer
) -> None:
    topic = _unique_topic()
    outbox = OutboxWriter(
        producer_slug="pdm",
        producer_version="1.0",
        producer_node_id="enterprise",
        signer=InsecureTestSigner(),
    )
    asset_id = uuid.uuid4()
    now = dt.datetime.now(dt.UTC)

    async with session_maker() as session:
        uow = UnitOfWork(session)
        await outbox.emit(
            uow,
            event_type="fathom.pdm.test_relay.emitted",
            event_version=1,
            aggregate="test_relay",
            aggregate_id=str(asset_id),
            topic=topic,
            scope=EventScope.ASSET,
            subject=EventSubject(asset_id=asset_id),
            payload=_TestPayload(message="hello from the relay"),
            classification=ClassificationLabel(level=ClassificationLevel.U),
            source_time=now,
            recorded_at=now,
            occurred_at=now,
        )
        await session.commit()

    bootstrap = kafka_container.get_bootstrap_server()
    producer = confluent_kafka.Producer({"bootstrap.servers": bootstrap})
    relay = OutboxRelay(producer=producer, signer=InsecureTestSigner(), worker_id="test-worker-1")

    async with session_maker() as session:
        stats = await relay.run_once(session)
    assert sum(s.published for s in stats) == 1
    assert sum(s.quarantined for s in stats) == 0

    consumer = confluent_kafka.Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": "test-consumer-group",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    inbound = InboundConsumer(consumer=consumer, topics=[topic])

    received: list[tuple[str, dict]] = []

    async def _dispatch(_session, envelope, payload) -> None:
        received.append((envelope.event_type, payload))

    result = None
    for _ in range(20):  # poll until the message arrives or we give up
        result = await inbound.poll_and_dispatch(session_maker, _dispatch, timeout=1.0)
        if result.outcome == "dispatched":
            break
    assert result is not None
    assert result.outcome == "dispatched"
    assert received == [("fathom.pdm.test_relay.emitted", {"message": "hello from the relay"})]

    consumer.close()
    producer.flush(5)


@pytest.mark.asyncio
async def test_relay_run_once_does_not_republish(session_maker: async_sessionmaker) -> None:
    topic = _unique_topic()
    outbox = OutboxWriter(
        producer_slug="pdm",
        producer_version="1.0",
        producer_node_id="enterprise",
        signer=InsecureTestSigner(),
    )
    now = dt.datetime.now(dt.UTC)
    async with session_maker() as session:
        uow = UnitOfWork(session)
        await outbox.emit(
            uow,
            event_type="fathom.pdm.test_relay.emitted",
            event_version=1,
            aggregate="test_relay",
            aggregate_id="fleet",
            topic=topic,
            scope=EventScope.FLEET,
            subject=EventSubject(),
            payload=_TestPayload(message="idempotent republish check"),
            classification=ClassificationLabel(level=ClassificationLevel.U),
            source_time=now,
            recorded_at=now,
            occurred_at=now,
        )
        await session.commit()

    published_messages: list[bytes] = []

    class _RecordingProducer:
        def produce(self, _topic, *, key, value, callback) -> None:  # noqa: ARG002
            published_messages.append(value)

        def poll(self, timeout: float) -> int:  # noqa: ARG002
            return 0

        def flush(self, timeout: float) -> int:  # noqa: ARG002
            return 0

    relay = OutboxRelay(
        producer=_RecordingProducer(), signer=InsecureTestSigner(), worker_id="test-worker-2"
    )

    async with session_maker() as session:
        stats1 = await relay.run_once(session)
    async with session_maker() as session:
        stats2 = await relay.run_once(session)

    assert sum(s.published for s in stats1) == 1
    assert sum(s.published for s in stats2) == 0  # already published -- not reclaimed
    assert len(published_messages) == 1


@pytest.mark.asyncio
async def test_relay_quarantines_after_max_attempts(session_maker: async_sessionmaker) -> None:
    topic = _unique_topic()
    outbox = OutboxWriter(
        producer_slug="pdm",
        producer_version="1.0",
        producer_node_id="enterprise",
        signer=InsecureTestSigner(),
    )
    now = dt.datetime.now(dt.UTC)
    async with session_maker() as session:
        uow = UnitOfWork(session)
        await outbox.emit(
            uow,
            event_type="fathom.pdm.test_relay.emitted",
            event_version=1,
            aggregate="test_relay",
            aggregate_id="fleet",
            topic=topic,
            scope=EventScope.FLEET,
            subject=EventSubject(),
            payload=_TestPayload(message="always fails to publish"),
            classification=ClassificationLabel(level=ClassificationLevel.U),
            source_time=now,
            recorded_at=now,
            occurred_at=now,
        )
        await session.commit()

    class _AlwaysFailingProducer:
        def produce(self, _topic, *, key, value, callback) -> None:  # noqa: ARG002
            raise RuntimeError("broker unreachable (test double)")

        def poll(self, timeout: float) -> int:  # noqa: ARG002
            return 0

        def flush(self, timeout: float) -> int:  # noqa: ARG002
            return 0

    relay = OutboxRelay(
        producer=_AlwaysFailingProducer(),
        signer=InsecureTestSigner(),
        worker_id="test-worker-3",
        max_attempts=3,
        lease_seconds=0.0,  # reclaim immediately on the next run_once, no need to sleep
    )

    from fathom_sync.models import OutboxQuarantineRow, OutboxRow
    from sqlalchemy import select

    for _ in range(3):
        async with session_maker() as session:
            await relay.run_once(session)

    async with session_maker() as session:
        remaining = (await session.execute(select(OutboxRow))).scalars().all()
        quarantined = (await session.execute(select(OutboxQuarantineRow))).scalars().all()

    assert remaining == []
    assert len(quarantined) == 1
    assert quarantined[0].attempt_count == 3
    assert "broker unreachable" in quarantined[0].last_error
