"""`pdm.propensity_model`. Document 22-pdm.md §2.4.

Schema-only, per the boundary `models/__init__.py` documents: the columns
this table needs exist so `model_binding`'s activation refusal (§5.6 --
"a binding cannot be activated unless its `propensity_model.accepted` is
true") is a real query against a real row, not a stub. Fitting a real
propensity model (§4.3/§4.4's IPCW weight computation) is the substantial
second vertical slice `models/__init__.py` already defers -- out of scope
here.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, Boolean, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from . import Base

_JsonVariant = JSON().with_variant(JSONB(), "postgresql")
_TextArray = ARRAY(String).with_variant(JSON(), "sqlite")


class PropensityModel(Base):
    __tablename__ = "propensity_model"
    __table_args__ = {"schema": "pdm"}

    propensity_model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    spec_version: Mapped[str] = mapped_column(String, nullable=False)
    fitted_on_label_set: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    grid: Mapped[str] = mapped_column(String, nullable=False)
    policy_version_strata: Mapped[list[str]] = mapped_column(_TextArray, nullable=False, default=list)
    fit_artifact_uri: Mapped[str] = mapped_column(String, nullable=False)
    # diagnostics that are refusal gates, not reports (§4.4)
    positivity_min_k: Mapped[float] = mapped_column(Numeric, nullable=False)
    ess: Mapped[float] = mapped_column(Numeric, nullable=False)
    max_stabilized_weight: Mapped[float] = mapped_column(Numeric, nullable=False)
    mean_stabilized_weight: Mapped[float] = mapped_column(Numeric, nullable=False)
    calibration_of_propensity: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    pms_sensitivity: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    fitted_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
