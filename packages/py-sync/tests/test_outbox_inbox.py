import datetime as dt
from uuid import uuid4

import pytest
import pytest_asyncio
from fathom_schemas import (
    ClassificationLabel,
    ClassificationLevel,
    EventScope,
    EventSubject,
    FailurePrediction,
    ReferenceClass,
    Rul,
    RulUnit,
)
from fathom_sync import (
    Base,
    EpochFence,
    EventId,
    Inbox,
    MonotonicSequencer,
    OutboxWriter,
    UnitOfWork,
    evaluate_fence,
)
from fathom_sync.models import OutboxRow
from fathom_sync.testing import FixedEpochFence, InsecureTestSigner
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _prediction() -> FailurePrediction:
    return FailurePrediction(
        asset_id=uuid4(),
        installed_item_id=uuid4(),
        position_id=uuid4(),
        niin="012345678",
        equipment_family="pump-centrifugal",
        baseline_id=uuid4(),
        baseline_epoch=1,
        horizon_days=90,
        reference_class=ReferenceClass.ITEM,
        sharpness=0.5,
        calibration_population=120,
        confidence=0.8,
        fallback_level=0,
        tier=2,
        model_version="tier2-degradation-1.0.0",
        scoring_run_id=uuid4(),
        computed_at=dt.datetime.now(dt.UTC),
        p_failure=0.12,
        rul=Rul(p10=10, p50=40, p90=90, unit=RulUnit.DAYS),
    )


@pytest.mark.asyncio
async def test_emit_writes_one_outbox_row_with_derived_partition_key(session: AsyncSession) -> None:
    writer = OutboxWriter(
        producer_slug="pdm",
        producer_version="1.0.0",
        producer_node_id="enterprise",
        signer=InsecureTestSigner(),
    )
    asset_id = uuid4()
    pred = _prediction()
    now = dt.datetime.now(dt.UTC)

    async with session.begin():
        event_id = await writer.emit(
            UnitOfWork(session),
            event_type="fathom.pdm.prediction.updated",
            event_version=1,
            aggregate="prediction",
            aggregate_id=str(pred.scoring_run_id),
            topic="fathom.pdm.prediction.v1",
            scope=EventScope.ASSET,
            subject=EventSubject(asset_id=asset_id),
            payload=pred,
            classification=ClassificationLabel(level=ClassificationLevel.U),
            source_time=now,
            recorded_at=now,
            occurred_at=now,
            baseline_epoch=1,
        )

    assert isinstance(event_id, EventId)
    from sqlalchemy import select

    rows = (await session.execute(select(OutboxRow))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.partition_key == str(asset_id)
    assert row.published_at is None
    assert row.event_id == str(event_id.value)


@pytest.mark.asyncio
async def test_compaction_key_equal_to_partition_key_is_rejected(session: AsyncSession) -> None:
    writer = OutboxWriter(
        producer_slug="pdm",
        producer_version="1.0.0",
        producer_node_id="enterprise",
        signer=InsecureTestSigner(),
    )
    asset_id = uuid4()
    pred = _prediction()
    now = dt.datetime.now(dt.UTC)

    with pytest.raises(ValueError, match="compaction_key must never equal partition_key"):
        async with session.begin():
            await writer.emit(
                UnitOfWork(session),
                event_type="fathom.pdm.prediction.updated",
                event_version=1,
                aggregate="prediction",
                aggregate_id=str(pred.scoring_run_id),
                topic="fathom.pdm.prediction.v1",
                scope=EventScope.ASSET,
                subject=EventSubject(asset_id=asset_id),
                payload=pred,
                classification=ClassificationLabel(level=ClassificationLevel.U),
                source_time=now,
                recorded_at=now,
                occurred_at=now,
                compaction_key=str(asset_id),  # == partition key, D5 violation
            )


@pytest.mark.asyncio
async def test_monotonic_sequencer_is_gap_free_per_producer_node(session: AsyncSession) -> None:
    sequencer = MonotonicSequencer()
    async with session.begin():
        first = await sequencer.next(session, producer_slug="pdm", producer_node_id="enterprise")
        second = await sequencer.next(session, producer_slug="pdm", producer_node_id="enterprise")
    assert list(first) == [1]
    assert list(second) == [2]


@pytest.mark.asyncio
async def test_inbox_suppresses_only_after_processed_at_set(session: AsyncSession) -> None:
    inbox = Inbox()
    from fathom_schemas import (
        Clock,
        EventEnvelope,
        ProducerRef,
        SubAppSlug,
        SyncQuality,
        TimeSource,
    )

    now = dt.datetime.now(dt.UTC)
    envelope = EventEnvelope(
        event_id=uuid4(),
        event_type="fathom.registry.configuration_baseline.changed",
        event_version=1,
        occurred_at=now,
        recorded_at=now,
        producer=ProducerRef(slug=SubAppSlug.REGISTRY, version="1.0.0"),
        producer_node="enterprise",
        correlation_id="corr-1",
        scope=EventScope.ASSET,
        subject=EventSubject(asset_id=uuid4()),
        classification=ClassificationLabel(level=ClassificationLevel.U),
        replay=False,
        clock=Clock(
            monotonic_seq=1,
            hlc=hybrid_logical_clock_shim(),
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

    async with session.begin():
        assert not await inbox.already_applied(session, envelope.event_id)
        await inbox.record(session, envelope)

    # Not yet processed -- must NOT suppress redelivery.
    async with session.begin():
        assert not await inbox.already_applied(session, envelope.event_id)

    async with session.begin():
        await inbox.mark_processed(session, envelope.event_id)

    async with session.begin():
        assert await inbox.already_applied(session, envelope.event_id)


def hybrid_logical_clock_shim():
    from fathom_schemas import HybridLogicalClock

    return HybridLogicalClock(physical=1, logical=0, node_id="enterprise")


@pytest.mark.asyncio
async def test_epoch_fence_blocks_ahead_of_current_epoch(session: AsyncSession) -> None:
    from fathom_schemas import (
        Clock,
        EventEnvelope,
        HybridLogicalClock,
        ProducerRef,
        SubAppSlug,
        SyncQuality,
        TimeSource,
    )

    now = dt.datetime.now(dt.UTC)
    asset_id = uuid4()
    envelope = EventEnvelope(
        event_id=uuid4(),
        event_type="fathom.pdm.prediction.updated",
        event_version=1,
        occurred_at=now,
        recorded_at=now,
        producer=ProducerRef(slug=SubAppSlug.PDM, version="1.0.0"),
        producer_node="enterprise",
        correlation_id="corr-2",
        scope=EventScope.ASSET,
        subject=EventSubject(asset_id=asset_id),
        baseline_epoch=5,
        classification=ClassificationLabel(level=ClassificationLevel.U),
        replay=False,
        clock=Clock(
            monotonic_seq=2,
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

    behind_fence: EpochFence = FixedEpochFence(epoch=3)
    decision = await evaluate_fence(behind_fence, session, envelope)
    assert decision.blocked
    assert decision.required_epoch == 5

    current_fence: EpochFence = FixedEpochFence(epoch=5)
    decision2 = await evaluate_fence(current_fence, session, envelope)
    assert not decision2.blocked
