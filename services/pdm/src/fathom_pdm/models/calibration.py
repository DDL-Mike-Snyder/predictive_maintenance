"""`pdm.calibration_record`. Document 22-pdm.md §2.7, §6.1.

The cell key is `(tier, equipment_family, horizon_days, reference_class,
taxonomy_version, stratum, compartments)` -- `compartments` closes a real
cross-compartment classification-aggregation leak found in this session's
adversarial review: a compartmented hull's item-horizon observation could
otherwise flip a *visible* item's `p_failure` from null to a value,
fleet-wide. A record is only ever built from `label_observation` rows whose
own `compartments` is a subset of this record's own.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from . import Base

_JsonVariant = JSON().with_variant(JSONB(), "postgresql")
_TextArray = ARRAY(String).with_variant(JSON(), "sqlite")


class CalibrationRecord(Base):
    __tablename__ = "calibration_record"
    __table_args__ = (
        UniqueConstraint(
            "tier",
            "equipment_family",
            "horizon_days",
            "reference_class",
            "taxonomy_version",
            "stratum",
            "compartments",
            "window_end",
        ),
        CheckConstraint("tier BETWEEN 0 AND 3", name="calibration_tier_range"),
        CheckConstraint("stratum IN ('treated','policy_frozen')", name="calibration_stratum"),
        CheckConstraint(
            "method IN ('isotonic','beta','identity_suppressed')", name="calibration_method"
        ),
        CheckConstraint(
            "drift_state IN ('stable','warning','drifting','withdrawn')",
            name="calibration_drift_state",
        ),
        {"schema": "pdm"},
    )

    calibration_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # the cell key. §6.1
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    equipment_family: Mapped[str] = mapped_column(String, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_class: Mapped[str] = mapped_column(String, nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String, nullable=False)
    stratum: Mapped[str] = mapped_column(String, nullable=False)
    compartments: Mapped[list[str]] = mapped_column(_TextArray, nullable=False, default=list)
    # population and power
    calibration_population: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # resolved item-horizon observations, WITHIN THIS COMPARTMENT SCOPE. THE gate input
    effective_sample_size: Mapped[float] = mapped_column(Numeric, nullable=False)
    events_observed: Mapped[float] = mapped_column(Numeric, nullable=False)
    powered: Mapped[bool] = mapped_column(Boolean, nullable=False)
    gate_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # the fit
    method: Mapped[str] = mapped_column(String, nullable=False)
    fit_artifact_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    reliability_curve: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    weighted_calibration_error: Mapped[float] = mapped_column(Numeric, nullable=False)
    unweighted_calibration_error: Mapped[float] = mapped_column(Numeric, nullable=False)
    picp_rul: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    # drift
    drift_state: Mapped[str] = mapped_column(String, nullable=False)
    drift_evidence: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    computed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_start: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    classification: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
