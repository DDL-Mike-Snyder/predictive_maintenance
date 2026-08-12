"""The one module that reads the environment; everything else takes
`Settings` by injection (09 §4.5, same discipline as
`platform/gateway/src/fathom_gateway/config.py`).

The four gate thresholds live here (plan §1.4) so that the action layer's
`evaluate-gate` reads them from one typed place rather than hardcoding them
at the call site. They carry the exact `v0-demo-placeholder` defaults the
plan pins; the real spec (28 §5.4) has *no* default at all.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DESIGN_ADVISORY_", extra="forbid")

    # env var DESIGN_ADVISORY_DATABASE_URL; SQLite-always for this demo.
    database_url: str = "sqlite+aiosqlite:///./design_advisory.db"

    # Gate thresholds (plan §1.4), overridable via
    # DESIGN_ADVISORY_GATE_* env vars but defaulted so the service just
    # starts. Read by the (not-Paul-owned) evaluate-gate action.
    gate_cost_floor_usd: float = 250_000
    gate_priority_floor: float = 0.55
    gate_completeness_floor: float = 0.60
    gate_field_failure_floor: int = 8
