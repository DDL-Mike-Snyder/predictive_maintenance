"""Clock discipline. Document 11 §4, D29: no wall clock ever arbitrates a
merge, a timeout, a retry backoff, or a lease expiry.

Ubuntu 22.04 STIG rule V-260520 mandates unlimited backward clock steps
whenever offset exceeds one second -- which fires precisely when a
disconnected node reconnects and drains its outbox. Every duration in this
module is measured with `time.monotonic()`, never `datetime.now()`.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ProducerSequenceRow


@dataclass(frozen=True)
class HybridLogicalClock:
    physical: int
    logical: int
    node_id: str

    def __lt__(self, other: HybridLogicalClock) -> bool:
        return (self.physical, self.logical, self.node_id) < (
            other.physical,
            other.logical,
            other.node_id,
        )


class MonotonicSequencer:
    """Gap-free, strictly increasing sequence per (producer_slug,
    producer_node_id). Allocated INSIDE the caller's transaction so the
    sequence and the outbox row commit together. Document 11 §4.3.

    Hard rules: `producer_node_id` is never reused for a different
    deployment (a restored backup needs a new node id); the sequence never
    resets, ever.
    """

    async def next(
        self, session: AsyncSession, *, producer_slug: str, producer_node_id: str, count: int = 1
    ) -> range:
        stmt = (
            update(ProducerSequenceRow)
            .where(
                ProducerSequenceRow.producer_slug == producer_slug,
                ProducerSequenceRow.producer_node_id == producer_node_id,
            )
            .values(next_seq=ProducerSequenceRow.next_seq + count)
            .returning(ProducerSequenceRow.next_seq)
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            # First allocation for this key -- seed the row at 1, then retry once.
            session.add(
                ProducerSequenceRow(
                    producer_slug=producer_slug,
                    producer_node_id=producer_node_id,
                    next_seq=1 + count,
                )
            )
            await session.flush()
            return range(1, 1 + count)
        new_next = row
        first_allocated = new_next - count
        return range(first_allocated, new_next)


def monotonic_backoff(
    attempt: int, *, base_ms: int = 100, cap_ms: int = 60_000, jitter: float = 0.2
) -> float:
    """Document 11 §2.5. Monotonic, jittered backoff in seconds. Never a
    wall-clock computation."""
    raw_ms = min(cap_ms, base_ms * (2**attempt))
    jitter_ms = raw_ms * jitter * (2 * random.random() - 1)  # noqa: S311 - non-cryptographic jitter
    return max(0.0, (raw_ms + jitter_ms) / 1000.0)


class MonotonicDeadline:
    """A deadline measured against `time.monotonic()`, never wall time.
    Used for shard leases, antecedent-wait deadlines, and lease expiry."""

    __slots__ = ("_deadline",)

    def __init__(self, duration_seconds: float) -> None:
        self._deadline = time.monotonic() + duration_seconds

    @property
    def elapsed(self) -> bool:
        return time.monotonic() >= self._deadline

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self._deadline - time.monotonic())
