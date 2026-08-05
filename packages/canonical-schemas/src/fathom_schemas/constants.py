"""Thresholds sourced from document 06, each cited. Nothing here is invented
(09-monorepo-and-conventions.md DO-NOT 31: "do not invent quantities")."""

from __future__ import annotations

CALIBRATION_POPULATION_FLOOR: int = 50
"""Document 06 §3 Decision 2 (MEDIUM confidence). Below this cell count PdM
publishes no calibrated `p_failure` at all -- see 22-pdm.md §6.2."""

PREDICTION_HORIZONS_DAYS: tuple[int, ...] = (30, 90, 180)
"""Document 06 §7. Not enforced as a CHECK on `horizon_days` -- a demonstration
convention, not a hard schema constraint."""
