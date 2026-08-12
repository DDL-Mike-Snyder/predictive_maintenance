"""Settings for the Redesign Case Builder demo service.

Deliberately plain `pydantic_settings.BaseSettings` -- this demo skips
`fathom-py-common`'s stricter conventions for speed
(docs/demo/redesign-case-builder-demo-plan.md §0.1/Paul's task 1).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DESIGN_ADVISORY_", extra="forbid")

    database_url: str = "sqlite+aiosqlite:///./design_advisory.db"

    # Gate thresholds, docs/demo/redesign-case-builder-demo-plan.md §1.4.
    # `v0-demo-placeholder` -- the real spec (28-design-advisory.md §5.4)
    # has no default at all; these concrete numbers are this demo's own.
    gate_cost_floor_usd: float = 250_000
    gate_priority_floor: float = 0.55
    gate_completeness_floor: float = 0.60
    gate_field_failure_floor: int = 8
