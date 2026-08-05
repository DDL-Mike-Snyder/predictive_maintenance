"""The inbound consume loop. Document 11 §3.4, §6.

**Scope, deliberately drawn here**, mirroring `relay.py`'s own boundary
note: this is the generic message-pump -- subscribe, poll, deserialize the
wire message `relay.py` produces, open one transaction, call the caller's
own `dispatch(session, envelope, raw_payload)`, commit, THEN commit the
Kafka offset. It deliberately does NOT itself call `Inbox`/`EpochFence` --
`services/pdm/src/fathom_pdm/events/consumers.py::dispatch_event` already
owns that (its own module docstring: "this module is the business-logic
layer a consumer loop calls once it has already deserialized an envelope"),
and duplicating inbox/fencing mechanics at the loop level here would fight
that existing, tested design rather than complete it. A future service
whose own dispatch function does NOT already embed inbox handling would
call `Inbox`/`evaluate_fence` itself, using the exact §3.4 sequence, from
inside its own `dispatch`.

Explicitly NOT built in this pass: the "blocked-row sweeper" that retries
events an `EpochFence` blocked after the antecedent lands (§3.5) -- neither
of PdM's own two wired handlers uses epoch fencing today (`installed_item
.removed` carries no `baseline_epoch` at all; `configuration.baseline_
changed` IS the antecedent, not something fenced against something
earlier), so there is nothing yet to prove this against for real.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from fathom_schemas import (
    Clock,
    EventEnvelope,
    EventSubject,
    HybridLogicalClock,
    ProducerRef,
    SubAppSlug,
    SyncQuality,
    TimeSource,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class KafkaMessagePort(Protocol):
    """The exact slice of a `confluent_kafka.Message` the consumer uses --
    named for the same reason as `relay.KafkaProducerPort`."""

    def value(self) -> bytes | None: ...
    def error(self) -> object | None: ...


class KafkaConsumerPort(Protocol):
    def subscribe(self, topics: list[str]) -> None: ...
    def poll(self, timeout: float) -> KafkaMessagePort | None: ...
    def commit(self, message: KafkaMessagePort, *, asynchronous: bool) -> None: ...


@dataclass(frozen=True)
class PollResult:
    """What one `poll_and_dispatch` call did, for the caller's own
    logging/metrics loop -- deliberately not raising for the routine
    "nothing to do" and "unhandled type, logged" outcomes."""

    outcome: str  # "empty" | "dispatched" | "unhandled_type" | "deserialize_error"
    event_type: str | None = None


_PLACEHOLDER_SYNC_QUALITY: dict[str, object] = {
    "time_source": TimeSource.UNSYNCED,
    "offset_ms": 0.0,
    "dispersion_ms": 0.0,
    "seconds_since_sync": 0.0,
    "step_occurred": False,
}
"""`OutboxWriter.emit()` (outbox.py) has always hardcoded `sync_quality={}`
-- no producer anywhere in this codebase populates the real attestation
§4.6 describes, so there is nothing real to round-trip through the wire.
`Clock.sync_quality` is non-optional (canonical-schemas' own contract), so
reconstructing an `EventEnvelope` on the consume side needs SOME value;
`UNSYNCED` is the honest one (never claim NTP-quality timing that was
never measured), and any real fields a future emit-side fix does populate
still override these via the merge below."""


def _envelope_from_wire(raw: dict[str, object]) -> tuple[EventEnvelope, dict[str, object]]:
    """The inverse of `relay._wire_message` -- reconstructs the
    `EventEnvelope` canonical-schemas object plus the raw payload dict
    `dispatch()` needs, from the flattened wire JSON `relay.py` produces.

    `ingest_time` is deliberately NEVER read from the wire -- §6's own
    table: "Stamped by the receiver on acceptance." The producer has no
    meaningful value for it (`OutboxWriter.emit()` always stores `None`);
    this function stamps `now()` itself, matching the property every
    consumer handler (e.g. `Inbox.record()`) already assumes it can read
    straight off the envelope it was handed.
    """
    clock_raw = raw["clock"]
    assert isinstance(clock_raw, dict)  # noqa: S101 -- our own wire format, not external input
    hlc_raw = clock_raw["hlc"]
    assert isinstance(hlc_raw, dict)  # noqa: S101
    producer_raw = raw["producer"]
    assert isinstance(producer_raw, dict)  # noqa: S101
    subject_raw = raw["subject"]
    assert isinstance(subject_raw, dict)  # noqa: S101
    sync_quality_raw = clock_raw["sync_quality"]
    assert isinstance(sync_quality_raw, dict)  # noqa: S101

    envelope = EventEnvelope(
        event_id=raw["event_id"],
        event_type=raw["event_type"],
        event_version=raw["event_version"],
        producer=ProducerRef(
            slug=SubAppSlug(producer_raw["slug"]), version=producer_raw["version"]
        ),
        producer_node=raw["producer_node"],
        scope=raw["scope"],
        subject=EventSubject(**subject_raw),
        baseline_epoch=raw["baseline_epoch"],
        classification=raw["classification"],
        correlation_id=raw["correlation_id"],
        causation_id=raw["causation_id"],
        replay=raw["replay"],
        occurred_at=dt.datetime.fromisoformat(str(raw["occurred_at"])),
        recorded_at=dt.datetime.fromisoformat(str(raw["recorded_at"])),
        clock=Clock(
            monotonic_seq=clock_raw["monotonic_seq"],
            hlc=HybridLogicalClock(
                physical=hlc_raw["physical"], logical=hlc_raw["logical"], node_id=hlc_raw["node_id"]
            ),
            source_time=dt.datetime.fromisoformat(str(clock_raw["source_time"])),
            ingest_time=dt.datetime.now(dt.UTC),
            sync_quality=SyncQuality(**{**_PLACEHOLDER_SYNC_QUALITY, **sync_quality_raw}),
        ),
    )
    payload = raw["payload"]
    assert isinstance(payload, dict)  # noqa: S101
    return envelope, payload


class InboundConsumer:
    """§3.4's generic message pump. `dispatch` is caller-provided --
    typically a service's own `events.consumers.dispatch_event`."""

    def __init__(self, *, consumer: KafkaConsumerPort, topics: list[str]) -> None:
        self._consumer = consumer
        self._topics = topics
        consumer.subscribe(topics)

    async def poll_and_dispatch(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        dispatch: Callable[[AsyncSession, EventEnvelope, dict], Awaitable[None]],
        *,
        # timeout is forwarded verbatim to confluent_kafka's own synchronous
        # poll(timeout) -- not an asyncio cancellation scope, hence the
        # suppression on the next line.
        timeout: float = 1.0,  # noqa: ASYNC109
        unhandled_error_type: type[Exception] = Exception,
    ) -> PollResult:
        """Polls for exactly one message. Returns immediately with
        `outcome="empty"` if none is available within `timeout` -- the
        caller's own loop decides how to pace repeated calls."""
        message = self._consumer.poll(timeout)
        if message is None:
            return PollResult(outcome="empty")
        if message.error() is not None:
            logger.warning("kafka poll error: %s", message.error())
            return PollResult(outcome="deserialize_error")

        raw_bytes = message.value()
        if raw_bytes is None:
            return PollResult(outcome="deserialize_error")

        try:
            raw = json.loads(raw_bytes)
            envelope, payload = _envelope_from_wire(raw)
        except Exception:
            logger.exception("failed to deserialize inbound message")
            return PollResult(outcome="deserialize_error")

        try:
            async with session_maker() as session:
                await dispatch(session, envelope, payload)
                await session.commit()
        except unhandled_error_type as exc:
            # events/consumers.py's own UnhandledEventTypeError (or an
            # equivalent a future service's dispatch raises): route to
            # log/dead-letter, per that exception's own docstring -- never
            # crash the loop over one declared-but-unimplemented type. The
            # Kafka offset commits anyway: redelivering a message dispatch
            # can never handle changes nothing.
            logger.warning("unhandled event_type=%s: %s", envelope.event_type, exc, exc_info=True)
            self._consumer.commit(message, asynchronous=False)
            return PollResult(outcome="unhandled_type", event_type=envelope.event_type)

        # The Kafka offset commits after the database transaction, never
        # before (§3.4: "Offset-then-apply is D2 wearing a different hat").
        self._consumer.commit(message, asynchronous=False)
        return PollResult(outcome="dispatched", event_type=envelope.event_type)
