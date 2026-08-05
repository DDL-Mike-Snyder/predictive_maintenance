import datetime as dt
from uuid import uuid4

import pytest
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


def _clock() -> Clock:
    now = dt.datetime.now(dt.UTC)
    return Clock(
        monotonic_seq=1,
        hlc=HybridLogicalClock(physical=1, logical=0, node_id="enterprise"),
        source_time=now,
        ingest_time=now,
        sync_quality=SyncQuality(
            time_source=TimeSource.GNSS,
            offset_ms=0.5,
            dispersion_ms=1.0,
            seconds_since_sync=5.0,
            step_occurred=False,
        ),
    )


def _label() -> ClassificationLabel:
    return ClassificationLabel(level=ClassificationLevel.U)


def test_asset_scope_requires_exactly_asset_id() -> None:
    env = EventEnvelope(
        event_id=uuid4(),
        event_type="fathom.pdm.prediction.updated",
        event_version=1,
        occurred_at=dt.datetime.now(dt.UTC),
        recorded_at=dt.datetime.now(dt.UTC),
        producer=ProducerRef(slug=SubAppSlug.PDM, version="1.0.0"),
        producer_node="enterprise",
        correlation_id="corr-1",
        scope=EventScope.ASSET,
        subject=EventSubject(asset_id=uuid4()),
        classification=_label(),
        replay=False,
        clock=_clock(),
    )
    assert env.dedup_key == ("pdm", "enterprise", 1)


def test_installed_item_scope_requires_both_fields() -> None:
    with pytest.raises(ValueError, match="requires BOTH"):
        EventEnvelope(
            event_id=uuid4(),
            event_type="fathom.pdm.prediction.updated",
            event_version=1,
            occurred_at=dt.datetime.now(dt.UTC),
            recorded_at=dt.datetime.now(dt.UTC),
            producer=ProducerRef(slug=SubAppSlug.PDM, version="1.0.0"),
            producer_node="enterprise",
            correlation_id="corr-1",
            scope=EventScope.INSTALLED_ITEM,
            subject=EventSubject(installed_item_id=uuid4()),  # missing asset_id
            classification=_label(),
            replay=False,
            clock=_clock(),
        )


def test_event_type_slug_must_match_producer() -> None:
    with pytest.raises(ValueError, match="does not match producer"):
        EventEnvelope(
            event_id=uuid4(),
            event_type="fathom.registry.asset.registered",
            event_version=1,
            occurred_at=dt.datetime.now(dt.UTC),
            recorded_at=dt.datetime.now(dt.UTC),
            producer=ProducerRef(slug=SubAppSlug.PDM, version="1.0.0"),
            producer_node="enterprise",
            correlation_id="corr-1",
            scope=EventScope.ASSET,
            subject=EventSubject(asset_id=uuid4()),
            classification=_label(),
            replay=False,
            clock=_clock(),
        )


def test_classification_union_takes_highest_level() -> None:
    low = ClassificationLabel(level=ClassificationLevel.U, derived_from="src-a")
    high = ClassificationLabel(level=ClassificationLevel.CUI, derived_from="src-b")
    merged = ClassificationLabel.union(low, high, derived_from="derived-value-1")
    assert merged.level is ClassificationLevel.CUI
    assert set(merged.inherited_from) == {"src-a", "src-b"}
