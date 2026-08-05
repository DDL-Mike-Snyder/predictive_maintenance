"""The consumer inbox. Document 11 §3.

"Record and apply in one transaction. The `event_id` record and the
resulting state change commit together. Where that is impossible, the inbox
row carries `processed_at` and only rows with `processed_at` set suppress
redelivery. Recording receipt before processing is prohibited: a crash
between the two permanently suppresses the event." (D2)
"""

from __future__ import annotations

import datetime as dt
import time
from typing import Protocol
from uuid import UUID

from fathom_schemas import EventEnvelope
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import InboxRow


class EpochFence(Protocol):
    """Document 11 §3.5. The antecedent rule (D3/D4): a consumer receiving
    an event whose `baseline_epoch` is ahead of its own configuration read
    model must block until the antecedent lands."""

    async def current_epoch(self, session: AsyncSession, asset_id: str) -> int: ...


class FenceDecision:
    __slots__ = ("blocked", "required_epoch")

    def __init__(self, *, blocked: bool, required_epoch: int | None = None) -> None:
        self.blocked = blocked
        self.required_epoch = required_epoch


async def evaluate_fence(
    fence: EpochFence, session: AsyncSession, envelope: EventEnvelope
) -> FenceDecision:
    if envelope.baseline_epoch is None:
        return FenceDecision(blocked=False)
    asset_id = envelope.subject.asset_id
    if asset_id is None:
        return FenceDecision(blocked=False)
    current = await fence.current_epoch(session, str(asset_id))
    if envelope.baseline_epoch > current:
        return FenceDecision(blocked=True, required_epoch=envelope.baseline_epoch)
    return FenceDecision(blocked=False)


class Inbox:
    """The record/apply/mark-processed primitive every consumer handler
    calls, always inside the caller's own transaction."""

    async def already_applied(self, session: AsyncSession, event_id: UUID) -> bool:
        """The ONLY permitted suppression query (11 §3.4): constrained on
        `processed_at IS NOT NULL`, never on `event_id` alone."""
        stmt = select(InboxRow.event_id).where(
            InboxRow.event_id == str(event_id), InboxRow.processed_at.is_not(None)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def record(self, session: AsyncSession, envelope: EventEnvelope) -> None:
        """`processed_at` LEFT NULL here -- set only by `mark_processed`."""
        now = dt.datetime.now(dt.UTC)
        session.add(
            InboxRow(
                event_id=str(envelope.event_id),
                producer_slug=str(envelope.producer.slug.value),
                producer_node_id=envelope.producer_node,
                monotonic_seq=envelope.clock.monotonic_seq,
                event_type=envelope.event_type,
                aggregate=envelope.event_type.rsplit(".", 1)[0].split(".", 2)[-1],
                topic=envelope.event_type,
                received_at=now,
                ingest_time=envelope.clock.ingest_time,
                sync_quality=envelope.clock.sync_quality.wire_dict(),
                replay=envelope.replay,
            )
        )
        await session.flush()

    async def record_blocked(
        self, session: AsyncSession, envelope: EventEnvelope, *, on_epoch: int
    ) -> None:
        now = dt.datetime.now(dt.UTC)
        session.add(
            InboxRow(
                event_id=str(envelope.event_id),
                producer_slug=str(envelope.producer.slug.value),
                producer_node_id=envelope.producer_node,
                monotonic_seq=envelope.clock.monotonic_seq,
                event_type=envelope.event_type,
                aggregate=envelope.event_type.rsplit(".", 1)[0].split(".", 2)[-1],
                topic=envelope.event_type,
                received_at=now,
                ingest_time=envelope.clock.ingest_time,
                sync_quality=envelope.clock.sync_quality.wire_dict(),
                replay=envelope.replay,
                blocked_on_epoch=on_epoch,
                blocked_since_mono=int(time.monotonic() * 1000),
            )
        )
        await session.flush()

    async def mark_processed(self, session: AsyncSession, event_id: UUID) -> None:
        await session.execute(
            update(InboxRow)
            .where(InboxRow.event_id == str(event_id))
            .values(processed_at=dt.datetime.now(dt.UTC))
        )
