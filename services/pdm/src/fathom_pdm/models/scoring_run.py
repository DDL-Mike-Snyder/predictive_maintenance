"""`pdm.scoring_run`. Document 22-pdm.md §2.4.

`stratum` on the run -- rather than only on the prediction -- is what makes
holdout isolation a SINGLE structural check instead of a per-row filter a
refactor can drop. `fenced_out` is a first-class terminal status (D3), not
a failure: the baseline moved underneath the run and it was correctly
refused at publication.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, CheckConstraint, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from . import Base

# [CORRECTION -- see models/prediction.py's own comment for the full
# account.] `none_as_null=True` on both sides: without it, a Python `None`
# bound to `baseline_epoch_at_publish`/`rejection_summary` serializes as the
# JSON string `"null"`, not SQL `NULL`.
_JsonVariant = JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql")
_UuidArray = ARRAY(UUID(as_uuid=True)).with_variant(JSON(), "sqlite")


class ScoringRun(Base):
    __tablename__ = "scoring_run"
    __table_args__ = (
        CheckConstraint(
            "stratum IN ('operational','holdout_research')", name="scoring_run_stratum"
        ),
        CheckConstraint(
            "trigger IN ('scheduled','mission_completed','on_demand','tier_migration',"
            "'invalidation_rescore','binding_activation','design_change_projection')",
            name="scoring_run_trigger",
        ),
        CheckConstraint(
            "status IN ('queued','running','ingesting','published','fenced_out','failed')",
            name="scoring_run_status",
        ),
        {"schema": "pdm"},
    )

    scoring_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    stratum: Mapped[str] = mapped_column(String, nullable=False)
    trigger: Mapped[str] = mapped_column(String, nullable=False)
    scope: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    baseline_epoch_at_start: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    baseline_epoch_at_publish: Mapped[dict | None] = mapped_column(_JsonVariant, nullable=True)
    model_bindings: Mapped[list] = mapped_column(_UuidArray, nullable=False, default=list)
    label_set_ids: Mapped[list] = mapped_column(_UuidArray, nullable=False, default=list)
    feature_definition_time: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    domino_execution_ref: Mapped[str] = mapped_column(String, nullable=False)
    predictions_written: Mapped[int | None] = mapped_column(Integer, nullable=True)
    predictions_rejected: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rejection_summary: Mapped[dict | None] = mapped_column(_JsonVariant, nullable=True)
    read_model_lag_at_start: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    classification: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
