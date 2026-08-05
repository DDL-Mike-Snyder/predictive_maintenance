"""`pdm.prediction` -- the stored `FailurePrediction`, with lifecycle.
Document 22-pdm.md §2.5.

Row-level security (the holdout isolation mechanism, §4.5) is NOT
expressible through SQLAlchemy's declarative model layer -- `ENABLE ROW
LEVEL SECURITY`, `CREATE POLICY`, `CREATE ROLE`, and `GRANT` are raw DDL,
applied in the Alembic migration (`migrations/versions/`), not here. This
module defines the table's own shape and CHECK constraints only.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from . import Base

_JsonVariant = JSON().with_variant(JSONB(), "postgresql")


class Prediction(Base):
    __tablename__ = "prediction"
    __table_args__ = (
        UniqueConstraint("installed_item_id", "horizon_days", "scoring_run_id"),
        CheckConstraint("horizon_days > 0", name="prediction_horizon_positive"),
        CheckConstraint(
            "p_failure IS NULL OR (p_failure >= 0 AND p_failure <= 1)", name="prediction_p_failure_range"
        ),
        CheckConstraint(
            "population_hazard_rate IS NULL OR population_hazard_rate >= 0",
            name="prediction_hazard_rate_nonneg",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="prediction_confidence_range"
        ),
        CheckConstraint("fallback_level BETWEEN 0 AND 4", name="prediction_fallback_level_range"),
        CheckConstraint("tier BETWEEN 0 AND 3", name="prediction_tier_range"),
        # [D19] the corrected 03 §7.1 conditionals, enforced in the database.
        CheckConstraint(
            "(reference_class = 'item' AND rul IS NOT NULL AND population_hazard_rate IS NULL) "
            "OR (reference_class <> 'item' AND rul IS NULL AND population_hazard_rate IS NOT NULL)",
            name="rul_only_when_item_conditional",
        ),
        # 03 §7.1, 06 §3.
        CheckConstraint(
            "(calibration_population >= 50) "
            "OR (reference_class = 'class_estimate' AND p_failure IS NULL "
            "AND population_hazard_rate IS NOT NULL)",
            name="calibration_gate",
        ),
        CheckConstraint(
            "p_failure IS NULL OR calibration_population >= 50",
            name="p_failure_requires_a_calibrated_cell",
        ),
        # §6.3: a cell below the gate is, by definition, one where item and
        # NIIN-fleet history were insufficient, so fallback_level cannot be 0-2.
        CheckConstraint(
            "calibration_population >= 50 OR fallback_level >= 3",
            name="sub_gate_is_deep_fallback",
        ),
        {"schema": "pdm"},
    )

    prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scoring_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pdm.scoring_run.scoring_run_id"), nullable=False
    )
    # 03 §7.1, transcribed. The Pydantic model in canonical-schemas is the executable copy.
    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    installed_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    position_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    niin: Mapped[str] = mapped_column(String(9), nullable=False)
    equipment_family: Mapped[str] = mapped_column(String, nullable=False)
    baseline_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    baseline_epoch: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    p_failure: Mapped[float | None] = mapped_column(Numeric, nullable=True)  # NULLABLE, 03 §7.1 as corrected
    reference_class: Mapped[str] = mapped_column(String, nullable=False)
    sharpness: Mapped[float] = mapped_column(Numeric, nullable=False)
    calibration_population: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # PdM always populates it -- see 22-pdm.md §2.5 note
    rul: Mapped[dict | None] = mapped_column(_JsonVariant, nullable=True)  # {p10,p50,p90,unit} or NULL
    population_hazard_rate: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    confidence: Mapped[float] = mapped_column(Numeric, nullable=False)
    fallback_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    contributing_factors: Mapped[list] = mapped_column(_JsonVariant, nullable=False, default=list)
    model_version: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # PdM-internal lifecycle and serving control. NOT on the wire contract.
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    serving_class: Mapped[str] = mapped_column(String, nullable=False)  # §4.5. Set by the server, never the caller
    invalidated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidation_cause: Mapped[str | None] = mapped_column(String, nullable=True)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pdm.prediction.prediction_id"), nullable=True
    )
    provenance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pdm.prediction_provenance.provenance_id"), nullable=False
    )
    classification: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
