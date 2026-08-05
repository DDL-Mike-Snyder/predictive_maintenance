"""`pdm.prediction_provenance`. Document 22-pdm.md §2.6.

Obligation 9: provenance "sufficient to trace any operator-visible figure
to its sources." `suppressed_factors` is retained rather than discarded --
D23's defect is *displaying* an unidentified attribution, not computing one.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from . import Base

# [CORRECTION -- see models/prediction.py's own comment for the full
# account.] `none_as_null=True` on both sides: without it, a Python `None`
# bound to `transition_annotation` serializes as the JSON string `"null"`,
# not SQL `NULL`.
_JsonVariant = JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql")


class PredictionProvenance(Base):
    __tablename__ = "prediction_provenance"
    __table_args__ = ({"schema": "pdm"},)

    provenance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scoring_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    model_binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    label_set_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    propensity_model_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    calibration_record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    gate_decision: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    feature_observations: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    feature_definition_time: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fallback_path: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    attribution_method: Mapped[str | None] = mapped_column(String, nullable=True)
    stability_threshold_applied: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    suppressed_factor_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suppressed_factors: Mapped[list] = mapped_column(_JsonVariant, nullable=False, default=list)
    transition_annotation: Mapped[dict | None] = mapped_column(_JsonVariant, nullable=True)
    read_model_lag: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    per_asset_label_lag_days: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    classification: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
