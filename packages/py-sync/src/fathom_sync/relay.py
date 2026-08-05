"""The outbox relay. Document 11 §2.4-2.6: a transactional claim-based
poller, not a CDC/logical-replication consumer -- see §2.4's own table for
why (always-active, no separate deployment to go inert, disconnected-edge
safe, no extra STIG surface).

**Scope, deliberately drawn here.** This is the core claim/publish/mark-
published/quarantine loop, built and tested against a real Kafka
container. Explicitly NOT built in this pass, matching this vertical
slice's own established boundary style (see CLAUDE.md):

- **Multi-worker-safe shard coordination.** Claiming uses `time.monotonic()`
  -derived lease deadlines (`OutboxRow.claimed_until_mono`), which are only
  self-consistent within ONE process's own clock reference -- §2.5's own
  pseudocode inherits this property, it is not introduced here. A second
  relay worker computing its own monotonic deadline cannot precisely agree
  with the first about when a lease has truly expired; the two workers'
  monotonic epochs are offset by an unknown constant. Correct for exactly
  one relay replica (matches every real invocation this pass tests
  against); genuinely unsafe for N>1 without a shared, server-authoritative
  clock for the compare-and-swap. Flagged, not silently papered over.
- **Backfill mode / `X-Backfill` suppression** (§2.8) -- a separate
  cross-cutting feature.
- **Pruning / retention policy** (§2.6).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import or_, select, update

from .models import OutboxQuarantineRow, OutboxRow
from .outbox import SigningPort

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class KafkaProducerPort(Protocol):
    """The exact slice of `confluent_kafka.Producer` the relay uses --
    named here so tests can substitute a fake without a real broker for
    the claim/quarantine logic, and so this module does not hard-depend on
    `confluent_kafka`'s own types in its own signatures."""

    def produce(self, topic: str, *, key: bytes, value: bytes, callback: object) -> None: ...
    def poll(self, timeout: float) -> int: ...
    def flush(self, timeout: float) -> int: ...


class SignatureVerificationError(Exception):
    """Raised when `verify_signature` (§2.5) detects at-rest tampering --
    the exact scenario `record_signature` exists to catch. Quarantines the
    row like any other publish failure; does not raise past `run_once`."""


@dataclass(frozen=True)
class ShardRunStats:
    shard: int
    published: int
    quarantined: int


def _wire_message(row: OutboxRow, decrypted_payload_json: bytes) -> bytes:
    """The Kafka message body: 03 §5.4's envelope fields flattened at the
    top level (no prior document mandates a wire *message* shape, only the
    logical envelope) plus `payload`, the decrypted domain payload dict --
    a consumer needs both to call `dispatch(session, envelope, payload)`
    (services/pdm/src/fathom_pdm/events/consumers.py's own signature)."""
    envelope = {
        "event_id": row.event_id,
        "event_type": row.event_type,
        "event_version": row.event_version,
        "producer": {"slug": row.producer_slug, "version": row.producer_version},
        "producer_node": row.producer_node_id,
        "scope": row.scope,
        "subject": row.subject,
        "baseline_epoch": row.baseline_epoch,
        "classification": row.classification,
        "correlation_id": row.correlation_id,
        "causation_id": row.causation_id,
        "replay": row.replay,
        "occurred_at": row.occurred_at.isoformat(),
        "recorded_at": row.recorded_at.isoformat(),
        "clock": {
            "monotonic_seq": row.monotonic_seq,
            "hlc": {
                "physical": row.hlc_physical_ms,
                "logical": row.hlc_logical,
                "node_id": row.hlc_node_id,
            },
            "source_time": row.source_time.isoformat(),
            # ingest_time deliberately omitted -- 11 §6's own table: "Stamped
            # by the receiver on acceptance." The producer's own OutboxRow
            # always stores it as None (outbox.py's emit()); consumer.py
            # stamps a real value itself rather than reading a meaningless one.
            "sync_quality": row.sync_quality,
        },
        "payload": json.loads(decrypted_payload_json),
    }
    return json.dumps(envelope).encode("utf-8")


class OutboxRelay:
    """§2.5's algorithm. One instance per relay process; `run_once` sweeps
    every shard once. Callers loop `run_once` on their own interval (§2.4:
    "~50-200ms with adaptive interval" -- the interval/scheduling itself is
    the caller's, not this class's, concern)."""

    def __init__(
        self,
        *,
        producer: KafkaProducerPort,
        signer: SigningPort,
        worker_id: str,
        shard_count: int = 8,
        batch_size: int = 50,
        lease_seconds: float = 30.0,
        max_attempts: int = 12,
        publish_timeout_seconds: float = 10.0,
    ) -> None:
        self._producer = producer
        self._signer = signer
        self._worker_id = worker_id
        self._shard_count = shard_count
        self._batch_size = batch_size
        self._lease_ms = int(lease_seconds * 1000)
        self._max_attempts = max_attempts
        self._publish_timeout = publish_timeout_seconds

    async def run_once(self, session: AsyncSession) -> list[ShardRunStats]:
        return [await self._run_shard(session, shard) for shard in range(self._shard_count)]

    async def _run_shard(self, session: AsyncSession, shard: int) -> ShardRunStats:
        rows = await self._claim_batch(session, shard)
        published = 0
        quarantined = 0
        for row in rows:  # STRICTLY sequential within a shard -- §2.5's own rule
            ok, error = await self._publish_one(session, row)
            if ok:
                published += 1
            elif row.attempt_count >= self._max_attempts:
                await self._quarantine(session, row, last_error=error or "unknown")
                quarantined += 1
        return ShardRunStats(shard=shard, published=published, quarantined=quarantined)

    async def _claim_batch(self, session: AsyncSession, shard: int) -> list[OutboxRow]:
        now_mono_ms = int(time.monotonic() * 1000)
        candidate_ids = (
            (
                await session.execute(
                    select(OutboxRow.outbox_id)
                    .where(
                        OutboxRow.shard == shard,
                        OutboxRow.published_at.is_(None),
                        or_(
                            OutboxRow.claimed_until_mono.is_(None),
                            OutboxRow.claimed_until_mono < now_mono_ms,
                        ),
                    )
                    .order_by(OutboxRow.outbox_id)
                    .limit(self._batch_size)
                    .with_for_update(skip_locked=True)
                )
            )
            .scalars()
            .all()
        )
        if not candidate_ids:
            return []
        await session.execute(
            update(OutboxRow)
            .where(OutboxRow.outbox_id.in_(candidate_ids))
            .values(claimed_by=self._worker_id, claimed_until_mono=now_mono_ms + self._lease_ms)
        )
        await session.commit()
        rows = (
            (
                await session.execute(
                    select(OutboxRow)
                    .where(OutboxRow.outbox_id.in_(candidate_ids))
                    .order_by(OutboxRow.outbox_id)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    async def _publish_one(self, session: AsyncSession, row: OutboxRow) -> tuple[bool, str | None]:
        try:
            self._verify_signature(row)
            decrypted = self._signer.decrypt(row.payload_ciphertext or b"", row.payload_kek_id)
            message = _wire_message(row, decrypted)
            await self._produce_and_wait(row.topic, key=row.partition_key, value=message)
        except Exception as exc:  # noqa: BLE001 -- any publish failure is an attempt, not a crash
            row.attempt_count += 1
            await session.commit()
            return False, str(exc)

        row.published_at = dt.datetime.now(dt.UTC)
        row.attempt_count += 1
        await session.commit()
        return True, None

    def _verify_signature(self, row: OutboxRow) -> None:
        """§2.5's `verify_signature(row)`. Two independent checks, split by
        whether they need key material (see `SigningPort`'s own docstring):
        the payload hash needs none, so it's recomputed directly here; the
        signature needs the signing key, so it goes through the port."""
        if hashlib.sha256(row.payload_ciphertext or b"").digest() != row.payload_sha256:
            raise SignatureVerificationError(
                f"outbox_id={row.outbox_id}: payload_sha256 does not match stored payload -- "
                "at-rest tampering"
            )
        if not self._signer.verify(row.payload_sha256, row.record_signature, row.signing_key_id):
            raise SignatureVerificationError(
                f"outbox_id={row.outbox_id}: record_signature does not verify -- at-rest tampering"
            )

    async def _produce_and_wait(self, topic: str, *, key: str, value: bytes) -> None:
        """confluent_kafka's `Producer` is not natively asyncio-compatible
        (its C client callbacks fire from `poll()`/`flush()`, not awaits) --
        run the blocking produce+flush in a thread so this coroutine still
        yields, and raise if `flush()` reports undelivered messages after
        `publish_timeout_seconds` (§2.5: "awaiting broker acknowledgement
        each time")."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._produce_sync, topic, key, value)

    def _produce_sync(self, topic: str, key: str, value: bytes) -> None:
        errors: list[Exception] = []

        def _on_delivery(err: object, _msg: object) -> None:
            if err is not None:
                errors.append(RuntimeError(str(err)))

        self._producer.produce(topic, key=key.encode("utf-8"), value=value, callback=_on_delivery)
        undelivered = self._producer.flush(self._publish_timeout)
        if undelivered:
            raise RuntimeError(f"{undelivered} message(s) still undelivered after flush timeout")
        if errors:
            raise errors[0]

    async def _quarantine(self, session: AsyncSession, row: OutboxRow, *, last_error: str) -> None:
        session.add(
            OutboxQuarantineRow(
                outbox_id=row.outbox_id,
                event_id=row.event_id,
                event_type=row.event_type,
                topic=row.topic,
                shard=row.shard,
                attempt_count=row.attempt_count,
                last_error=last_error,
                quarantined_at=dt.datetime.now(dt.UTC),
            )
        )
        await session.delete(row)
        await session.commit()
