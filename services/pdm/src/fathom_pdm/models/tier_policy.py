"""`pdm.tier_policy`. Document 22-pdm.md §2.2. Reviewable, versioned rule set."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from . import Base

_JsonVariant = JSON().with_variant(JSONB(), "postgresql")


class TierPolicy(Base):
    __tablename__ = "tier_policy"
    __table_args__ = ({"schema": "pdm"},)

    policy_version: Mapped[str] = mapped_column(String, primary_key=True)
    weights: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    band_thresholds: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    hysteresis: Mapped[dict] = mapped_column(_JsonVariant, nullable=False)
    sme_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    approved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
