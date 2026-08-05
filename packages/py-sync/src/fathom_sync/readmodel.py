"""Read-model lag tracking and the staleness-bound refusal gate.
Document 11 §3.6, 03 §5.2, obligation 14, finding D6.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import timedelta


class StalenessBoundExceeded(Exception):
    """Raised by `require_fresh()`. A freshness-dependent computation must
    refuse to run rather than act on stale configuration -- the scheduling
    optimizer is the case named explicitly in document 11."""


@dataclass
class ReadinessCheckResult:
    name: str
    healthy: bool
    detail: str | None = None


@dataclass
class ReadModelLag:
    """One instance per consumed topic. `observe()` is called by the
    consumer's inbox dispatch on every applied event; `lag()` compares the
    last-observed monotonic timestamp against the current one."""

    _last_observed_monotonic: dict[str, float] = field(default_factory=dict)
    _blocked_count: int = 0

    def observe(self, topic: str) -> None:
        self._last_observed_monotonic[topic] = time.monotonic()

    def lag(self, topic: str) -> timedelta:
        last = self._last_observed_monotonic.get(topic)
        if last is None:
            return timedelta.max
        return timedelta(seconds=time.monotonic() - last)

    def set_blocked_events(self, count: int) -> None:
        self._blocked_count = count

    def blocked_events(self) -> int:
        return self._blocked_count

    def readyz(self, bounds: dict[str, timedelta]) -> ReadinessCheckResult:
        for topic, bound in bounds.items():
            if self.lag(topic) > bound:
                return ReadinessCheckResult(
                    name="read_model_lag",
                    healthy=False,
                    detail=f"{topic} lag {self.lag(topic)} exceeds bound {bound}",
                )
        return ReadinessCheckResult(name="read_model_lag", healthy=True)

    def require_fresh(self, bound: timedelta, *, computation: str, topic: str) -> None:
        if self.lag(topic) > bound:
            raise StalenessBoundExceeded(
                f"{computation} refuses to run: {topic} lag {self.lag(topic)} exceeds bound {bound}"
            )
