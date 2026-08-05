"""The transactional outbox. Document 11 §2.

Three invariants (11 §2.2): `emit()` writes through the ambient transaction
and never opens a connection or session factory of its own; it never
publishes (that is exclusively the relay's job, §2.4); a service commits
state+event together or neither.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from fathom_schemas import (
    ClassificationLabel,
    EventScope,
    EventSubject,
    FathomModel,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .clock import MonotonicSequencer
from .models import OutboxRow

_SCOPE_PARTITION_FIELD: dict[EventScope, str | None] = {
    EventScope.ASSET: "asset_id",
    EventScope.SYSTEM: "system_id",
    EventScope.INSTALLED_ITEM: "asset_id",  # partition on the OWNING ASSET, not the item
    EventScope.NIIN: "niin",
    EventScope.CLASS: "class_id",
    EventScope.MISSION: "mission_id",
    EventScope.TYCOM: "tycom_id",
    EventScope.FLEET: None,
}


class SigningPort(Protocol):
    """Record signing / envelope encryption is Audit's key-custody domain
    (32-audit.md §5, Vault/HSM). This package defines the seam a service
    wires into; it does not implement key management itself.

    `verify`/`decrypt` are `sign`/`encrypt`'s own inverses, needed by the
    relay (§2.5's `verify_signature(row)`, detecting at-rest tampering
    before publish) and the consumer (§6, turning a stored ciphertext back
    into the payload dict `dispatch()` needs) respectively -- neither
    existed until this pair of components needed them for real."""

    def sign(self, payload_sha256: bytes) -> tuple[bytes, str]:
        """Returns (record_signature, signing_key_id)."""
        ...

    def verify(self, payload_sha256: bytes, signature: bytes, signing_key_id: str) -> bool:
        """The inverse of `sign` -- recomputes the signature over
        `payload_sha256` under `signing_key_id` and compares. Does NOT
        recompute `payload_sha256` from the stored payload bytes itself;
        that half of tamper detection needs no key material, so the relay
        does it directly with `hashlib.sha256`, not through this port."""
        ...

    def encrypt(self, payload_json: bytes) -> tuple[bytes | None, str]:
        """Returns (payload_ciphertext, payload_kek_id). A production
        implementation may instead choose payload_ref for oversized results
        (D27) -- that path is the caller's decision, not this port's."""
        ...

    def decrypt(self, payload_ciphertext: bytes, kek_id: str) -> bytes:
        """The inverse of `encrypt` -- returns the payload JSON bytes."""
        ...


@dataclass(frozen=True)
class EventId:
    value: UUID


class UnitOfWork:
    """Wraps an `AsyncSession` inside its ambient transaction. Exposes no
    `commit()` -- mechanically enforcing that `emit()` never closes a
    transaction it did not open (11 §2.2's third invariant)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session


class OutboxWriter:
    """Document 11 §2.2's port, concretely implemented over SQLAlchemy."""

    def __init__(
        self,
        *,
        producer_slug: str,
        producer_version: str,
        producer_node_id: str,
        signer: SigningPort,
        sequencer: MonotonicSequencer | None = None,
        default_shard_count: int = 8,
    ) -> None:
        self._producer_slug = producer_slug
        self._producer_version = producer_version
        self._producer_node_id = producer_node_id
        self._signer = signer
        self._sequencer = sequencer or MonotonicSequencer()
        self._shard_count = default_shard_count

    async def emit(
        self,
        uow: UnitOfWork,
        *,
        event_type: str,
        event_version: int,
        aggregate: str,
        aggregate_id: str,
        topic: str,
        scope: EventScope,
        subject: EventSubject,
        payload: FathomModel,
        classification: ClassificationLabel,
        source_time: object,
        recorded_at: object,
        occurred_at: object,
        baseline_epoch: int | None = None,
        causation_id: UUID | None = None,
        compaction_key: str | None = None,
        replay: bool = False,
    ) -> EventId:
        """Write one outbox row inside the caller's ambient transaction.

        `partition_key` is NEVER a caller-supplied parameter -- it is
        derived from `scope`/`subject` here, because per-asset ordering is
        load-bearing (03 §5.1), not a caller convenience.
        """
        partition_key = self._derive_partition_key(scope, subject)
        if compaction_key is not None and compaction_key == partition_key:
            raise ValueError(
                f"compaction_key must never equal partition_key (D5) -- both were {partition_key!r}"
            )

        seq_range = await self._sequencer.next(
            uow.session,
            producer_slug=self._producer_slug,
            producer_node_id=self._producer_node_id,
        )
        monotonic_seq = seq_range.start

        event_id = uuid.uuid4()
        payload_json = payload.canonical_json()
        payload_sha256 = _sha256(payload_json)
        record_signature, signing_key_id = self._signer.sign(payload_sha256)
        payload_ciphertext, payload_kek_id = self._signer.encrypt(payload_json)

        row = OutboxRow(
            event_id=str(event_id),
            producer_slug=self._producer_slug,
            producer_version=self._producer_version,
            producer_node_id=self._producer_node_id,
            monotonic_seq=monotonic_seq,
            hlc_physical_ms=int(time.time() * 1000),
            hlc_logical=0,
            hlc_node_id=self._producer_node_id,
            event_type=event_type,
            event_version=event_version,
            topic=topic,
            partition_key=partition_key,
            compaction_key=compaction_key,
            aggregate=aggregate,
            aggregate_id=aggregate_id,
            scope=scope.value,
            subject=subject.wire_dict(),
            baseline_epoch=baseline_epoch,
            classification=classification.wire_dict(),
            correlation_id=str(uuid.uuid4()),
            causation_id=str(causation_id) if causation_id else None,
            replay=replay,
            occurred_at=occurred_at,  # type: ignore[arg-type]
            recorded_at=recorded_at,  # type: ignore[arg-type]
            source_time=source_time,  # type: ignore[arg-type]
            ingest_time=None,
            sync_quality={},
            payload_ciphertext=payload_ciphertext,
            payload_ref=None,
            payload_sha256=payload_sha256,
            payload_kek_id=payload_kek_id,
            record_signature=record_signature,
            signing_key_id=signing_key_id,
            shard=_shard_for(partition_key, self._shard_count),
            attempt_count=0,
        )
        uow.session.add(row)
        await uow.session.flush()
        return EventId(event_id)

    def _derive_partition_key(self, scope: EventScope, subject: EventSubject) -> str:
        if scope is EventScope.FLEET:
            return "fleet"
        field = _SCOPE_PARTITION_FIELD[scope]
        # FLEET (the one key whose value is None) already returned above.
        assert field is not None  # noqa: S101
        value = getattr(subject, field)
        if value is None:
            raise ValueError(f"scope={scope.value!r} requires `{field}` to derive a partition key")
        return str(value)


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _shard_for(partition_key: str, shard_count: int) -> int:
    digest = hashlib.blake2b(partition_key.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big") % shard_count
