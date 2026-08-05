"""`BaselineFencedComputation`. Document 11 §3.5's producer-side half of the
antecedent rule (D3): guards any long-running computation whose result
depends on configuration. Reads `baseline_epoch` at start; re-reads at
publish; REFUSES to publish a result computed under a superseded epoch.

The consumer-side half (a consumer blocking an event whose epoch is ahead
of its own read model) is `evaluate_fence()`/`EpochFence` in `inbox.py` --
the two are deliberately separate mechanisms for the two different
directions this same defect can occur.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class BaselineReader(Protocol):
    async def current_epoch(self, asset_id: str) -> int: ...


class BaselineSuperseded(Exception):
    """Raised at publish time when the epoch read at computation start no
    longer matches current configuration for one or more assets in scope."""

    def __init__(self, superseded_assets: dict[str, tuple[int, int]]) -> None:
        # {asset_id: (epoch_at_start, current_epoch)}
        self.superseded_assets = superseded_assets
        super().__init__(f"baseline superseded for {len(superseded_assets)} asset(s)")


@dataclass
class BaselineFencedComputation:
    reader: BaselineReader
    epoch_at_start: dict[str, int]

    @classmethod
    async def start(cls, reader: BaselineReader, asset_ids: list[str]) -> BaselineFencedComputation:
        epoch_at_start = {asset_id: await reader.current_epoch(asset_id) for asset_id in asset_ids}
        return cls(reader=reader, epoch_at_start=epoch_at_start)

    async def assert_still_current(self) -> dict[str, int]:
        """Call immediately before publishing. Returns
        `epoch_at_publish` per asset on success; raises `BaselineSuperseded`
        if any asset's configuration moved underneath the computation."""
        superseded: dict[str, tuple[int, int]] = {}
        epoch_at_publish: dict[str, int] = {}
        for asset_id, started_epoch in self.epoch_at_start.items():
            current = await self.reader.current_epoch(asset_id)
            epoch_at_publish[asset_id] = current
            if current != started_epoch:
                superseded[asset_id] = (started_epoch, current)
        if superseded:
            raise BaselineSuperseded(superseded)
        return epoch_at_publish
