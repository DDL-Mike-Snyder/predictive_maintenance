"""`pdm.label_set`. Document 22-pdm.md §2.3.

Schema-only, same boundary as `propensity_model.py`: exists so
`model_binding.label_set_id`'s FK is real and so §5.6's "its label set's
`powered` is true for the family" refusal check can resolve a real
`equipment_family`/`propensity_model_id`. Building `label_observation` and
the IPCW/censoring pipeline that actually populates these rows for real is
the second vertical slice `models/__init__.py` defers -- out of scope here.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from . import Base

_JsonVariant = JSON().with_variant(JSONB(), "postgresql")


class LabelSet(Base):
    __tablename__ = "label_set"
    __table_args__ = (
        CheckConstraint(
            "stratum IN ('treated','policy_frozen','combined')", name="label_set_stratum"
        ),
        {"schema": "pdm"},
    )

    label_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    equipment_family: Mapped[str] = mapped_column(String, nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String, nullable=False)
    window_start: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    grid: Mapped[str] = mapped_column(String, nullable=False, default="weekly")
    stratum: Mapped[str] = mapped_column(String, nullable=False)
    propensity_model_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pdm.propensity_model.propensity_model_id"), nullable=True
    )
    artifact_uri: Mapped[str] = mapped_column(String, nullable=False)
    feature_definition_time: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    feature_data_time_max: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ipcw_summary: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    built_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    classification: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
