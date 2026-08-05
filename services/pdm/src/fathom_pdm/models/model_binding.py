"""`pdm.model_binding`. Document 22-pdm.md §2.2, §5.6.

Binds a Domino registry model version to a `(tier, equipment_family,
taxonomy_version)` triple. `registry_model_version`/`registry_model_uri` are
opaque strings PdM records, never mints -- Domino owns the model artifacts
and the registry (03 §14). `censoring_correction` is `CHECK`-constrained to
its one legal value on purpose (§2.2's own note): widening it requires an
ADR, not a code change.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from . import Base


class ModelBinding(Base):
    __tablename__ = "model_binding"
    __table_args__ = (
        CheckConstraint("tier BETWEEN 0 AND 3", name="model_binding_tier_range"),
        CheckConstraint(
            "censoring_correction IN ('ipcw_stabilized')", name="model_binding_censoring_correction"
        ),
        UniqueConstraint("tier", "equipment_family", "taxonomy_version", "activated_at"),
        {"schema": "pdm"},
    )

    binding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    equipment_family: Mapped[str] = mapped_column(String, nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String, nullable=False)
    registry_model_version: Mapped[str] = mapped_column(String, nullable=False)
    registry_model_uri: Mapped[str] = mapped_column(String, nullable=False)
    approval_ref: Mapped[str] = mapped_column(String, nullable=False)
    label_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pdm.label_set.label_set_id"), nullable=False
    )
    censoring_correction: Mapped[str] = mapped_column(String, nullable=False)
    activated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deactivated_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
