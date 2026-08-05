"""The event envelope. Document 03 §5.4.

Every field is required at the type level except where the contract itself
says a field is conditional (`causation_id`, `baseline_epoch`). This is the
one and only definition of the envelope shape in the corpus -- every
service's `events/publishers.py` constructs one of these, and `packages/py-sync`
persists it into the outbox verbatim (as columns, not as an opaque blob).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from ._base import FathomModel, Niin, NonEmptyStr, UtcDateTime
from .classification import ClassificationLabel
from .slugs import AnySlug
from .topics import EVENT_TYPE_RE


class EventScope(StrEnum):
    """Document 03 §5.4 `scope` [C11]."""

    ASSET = "asset"
    SYSTEM = "system"
    INSTALLED_ITEM = "installed_item"
    NIIN = "niin"
    CLASS = "class"
    MISSION = "mission"
    TYCOM = "tycom"
    FLEET = "fleet"


class EventSubject(FathomModel):
    """Exactly one scope identifier is required, matching `scope`, EXCEPT
    `scope=fleet` (none) and `scope=installed_item` (BOTH `installed_item_id`
    AND `asset_id`, together -- an amendment closing a partition-key
    derivation defect: `EventScope.INSTALLED_ITEM`'s partition key is
    `asset_id`, which the outbox cannot derive from `installed_item_id` alone).
    """

    asset_id: UUID | None = None
    system_id: UUID | None = None
    installed_item_id: UUID | None = None
    niin: Niin | None = None
    class_id: NonEmptyStr | None = None
    mission_id: UUID | None = None
    tycom_id: NonEmptyStr | None = None


_SCOPE_SUBJECT_FIELD: dict[EventScope, str | None] = {
    EventScope.ASSET: "asset_id",
    EventScope.SYSTEM: "system_id",
    EventScope.INSTALLED_ITEM: "installed_item_id",
    EventScope.NIIN: "niin",
    EventScope.CLASS: "class_id",
    EventScope.MISSION: "mission_id",
    EventScope.TYCOM: "tycom_id",
    EventScope.FLEET: None,
}


class TimeSource(StrEnum):
    GNSS = "gnss"
    USNO_AUTHENTICATED = "usno_authenticated"
    UPSTREAM_NTP = "upstream_ntp"
    HOLDOVER = "holdover"
    UNSYNCED = "unsynced"


class SyncQuality(FathomModel):
    """The attestation that makes clock skew auditable rather than invisible.
    Retained permanently -- never dropped, even after reconnection."""

    time_source: TimeSource
    offset_ms: float
    dispersion_ms: float = Field(ge=0.0, description="THE PUBLISHED EPSILON.")
    seconds_since_sync: float = Field(ge=0.0)
    step_occurred: bool


class HybridLogicalClock(FathomModel):
    physical: int = Field(ge=0)
    logical: int = Field(ge=0)
    node_id: NonEmptyStr

    def __lt__(self, other: HybridLogicalClock) -> bool:
        return (self.physical, self.logical, self.node_id) < (
            other.physical,
            other.logical,
            other.node_id,
        )


class Clock(FathomModel):
    """Document 03 §5.4, D29. No wall clock ever arbitrates a merge."""

    monotonic_seq: int = Field(ge=0, description="THE ORDERING KEY, per producer_node.")
    hlc: HybridLogicalClock
    source_time: UtcDateTime = Field(description="NEVER an ordering/merge key.")
    ingest_time: UtcDateTime
    sync_quality: SyncQuality


class ProducerRef(FathomModel):
    slug: AnySlug
    version: NonEmptyStr


class EventEnvelope(FathomModel):
    event_id: UUID
    event_type: str = Field(pattern=EVENT_TYPE_RE.pattern)
    event_version: int = Field(ge=1)
    occurred_at: UtcDateTime = Field(
        description="Domain fact time. NEVER used for hindsight-authored values [D22]."
    )
    recorded_at: UtcDateTime = Field(description="When the producer persisted it. Audit uses this.")
    producer: ProducerRef
    producer_node: NonEmptyStr = Field(
        description=(
            "'enterprise' | 'edge:<asset_id>' -- which DEPLOYMENT INSTANCE of "
            "`producer.slug` emitted this. Required because an edge-profiled "
            "sub-application runs as two independent instances of one slug, "
            "each minting its own monotonic_seq."
        )
    )
    correlation_id: NonEmptyStr
    causation_id: UUID | None = Field(default=None)
    scope: EventScope
    subject: EventSubject
    baseline_epoch: int | None = Field(default=None, ge=0)
    classification: ClassificationLabel
    replay: bool = Field(description="True for backfill-generated events [D30].")
    clock: Clock

    @model_validator(mode="after")
    def _exactly_one_scope_identifier(self) -> Self:
        if self.scope is EventScope.FLEET:
            populated = [
                f for f in EventSubject.model_fields if getattr(self.subject, f) is not None
            ]
            if populated:
                raise ValueError(f"scope='fleet' requires an empty subject; got {populated}")
            return self

        if self.scope is EventScope.INSTALLED_ITEM:
            if self.subject.installed_item_id is None or self.subject.asset_id is None:
                raise ValueError(
                    "scope='installed_item' requires BOTH installed_item_id AND "
                    "asset_id on subject (asset_id is the partition key)"
                )
            return self

        field = _SCOPE_SUBJECT_FIELD[self.scope]
        # The type is `str | None` only for FLEET's sake; every other branch
        # above returns before reaching here, so `self.scope` is never FLEET
        # (the one key whose value is None) at this point.
        assert field is not None  # noqa: S101
        populated = [f for f in EventSubject.model_fields if getattr(self.subject, f) is not None]
        if populated != [field]:
            raise ValueError(
                f"scope={self.scope.value!r} requires exactly `{field}`; got {populated}"
            )
        return self

    @model_validator(mode="after")
    def _event_type_matches_producer(self) -> Self:
        m = EVENT_TYPE_RE.match(self.event_type)
        if m is None:
            raise ValueError(f"malformed event_type: {self.event_type!r}")
        if m.group("slug") != self.producer.slug.value:
            raise ValueError(
                f"event_type slug {m.group('slug')!r} does not match producer "
                f"{self.producer.slug.value!r}"
            )
        return self

    @property
    def dedup_key(self) -> tuple[str, str, int]:
        """(producer.slug, producer_node, clock.monotonic_seq)."""
        return (str(self.producer.slug.value), self.producer_node, self.clock.monotonic_seq)

    def precedes(self, other: EventEnvelope) -> bool:
        if self.producer.slug == other.producer.slug and self.producer_node == other.producer_node:
            return self.clock.monotonic_seq < other.clock.monotonic_seq
        return self.clock.hlc < other.clock.hlc

    @property
    def timestamp_arbitration_permitted(self) -> bool:
        sq = self.clock.sync_quality
        return not sq.step_occurred and sq.time_source not in (
            TimeSource.HOLDOVER,
            TimeSource.UNSYNCED,
        )
