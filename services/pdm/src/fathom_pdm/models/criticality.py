"""`pdm.criticality_assessment`. Document 22-pdm.md §2.1.

`tier_is_capped` and `migration_requires_rescore` are the two invariants of
§3 and §8 expressed where they cannot be bypassed -- rejected by the
database, not a code review. `proposed_tier` here is already
hysteresis-settled by the time a row is written (see 22-pdm.md §3.3/§3.4's
`raw_band`/`proposed_tier` split, which lives in the service layer, not
this model).
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from . import Base

# [CORRECTION -- see models/prediction.py's own comment for the full
# account.] `none_as_null=True` on both sides: without it, a Python `None`
# bound to `attributable_level_shift` serializes as the JSON string
# `"null"`, not SQL `NULL`.
_JsonVariant = JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql")


class CriticalityAssessment(Base):
    __tablename__ = "criticality_assessment"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="criticality_score_range"),
        CheckConstraint("proposed_tier BETWEEN 0 AND 3", name="criticality_proposed_tier_range"),
        CheckConstraint(
            "data_availability_ceiling BETWEEN 0 AND 3", name="criticality_ceiling_range"
        ),
        CheckConstraint("assigned_tier BETWEEN 0 AND 3", name="criticality_assigned_tier_range"),
        CheckConstraint("previous_tier IS NULL OR previous_tier BETWEEN 0 AND 3", name="criticality_previous_tier_range"),
        CheckConstraint(
            "assigned_tier = LEAST(proposed_tier, data_availability_ceiling)",
            name="tier_is_capped",
        ),
        CheckConstraint(
            "published_at IS NULL OR previous_tier IS NULL OR rescore_scoring_run_id IS NOT NULL",
            name="migration_requires_rescore",  # §8.3, D36
        ),
        {"schema": "pdm"},
    )

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    niin: Mapped[str] = mapped_column(String(9), nullable=False)
    equipment_family: Mapped[str] = mapped_column(String, nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String, nullable=False)
    system_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    class_id: Mapped[str | None] = mapped_column(String, nullable=True)  # NULL = fleet-wide assessment
    input_mission_criticality: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    input_consequence_of_failure: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    input_casrep_history: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    input_sensor_availability: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    input_fleet_population: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    input_provenance: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    proposed_tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    data_availability_ceiling: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    assigned_tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tier_policy_version: Mapped[str] = mapped_column(
        String, ForeignKey("pdm.tier_policy.policy_version"), nullable=False
    )
    previous_tier: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    transition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    transition_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    rescore_scoring_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pdm.scoring_run.scoring_run_id"), nullable=True
    )
    attributable_level_shift: Mapped[dict | None] = mapped_column(_JsonVariant, nullable=True)
    published_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # NULL until §8.3 step 5
    effective_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    superseded_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    classification: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
