"""Wire request/response models for `/scoring-runs`. Document 22-pdm.md
§10, §11.3 (line ~1356). `trigger` is never a request field -- this
operation is always the `'on_demand'` CHECK-constraint value (services/
scoring.py's own `create_scoring_run`), the same server-sets-what-it-alone-
knows pattern `serving_class`/`censoring_correction` already use elsewhere
in this service."""

from __future__ import annotations

import uuid
from typing import Literal

from fathom_schemas import FathomModel, UtcDateTime


class CreateScoringRunRequest(FathomModel):
    stratum: Literal["operational", "holdout_research"]
    scope: dict[str, object]


class ScoringRunResponse(FathomModel):
    scoring_run_id: uuid.UUID
    stratum: str
    trigger: str
    scope: dict[str, object]
    status: str
    feature_definition_time: UtcDateTime
