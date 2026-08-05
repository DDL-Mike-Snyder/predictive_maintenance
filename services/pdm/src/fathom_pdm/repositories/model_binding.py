"""The only place SQL is written for `pdm.model_binding`, and (read-only,
for the §5.6 activation-refusal checks) `pdm.label_set`, `pdm.propensity_model`,
`pdm.calibration_record`."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import exists, select

from fathom_pdm.models import CalibrationRecord, LabelSet, ModelBinding, PropensityModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ModelBindingRepository:
    async def insert(self, session: AsyncSession, binding: ModelBinding) -> None:
        session.add(binding)
        await session.flush()

    async def get_by_id(self, session: AsyncSession, binding_id: uuid.UUID) -> ModelBinding | None:
        return (
            await session.execute(select(ModelBinding).where(ModelBinding.binding_id == binding_id))
        ).scalar_one_or_none()

    async def get_active_for_triple(
        self, session: AsyncSession, *, tier: int, equipment_family: str, taxonomy_version: str
    ) -> ModelBinding | None:
        """§5.6/§8.1: the binding an activation supersedes -- one active
        binding per `(tier, equipment_family, taxonomy_version)` triple."""
        stmt = select(ModelBinding).where(
            ModelBinding.tier == tier,
            ModelBinding.equipment_family == equipment_family,
            ModelBinding.taxonomy_version == taxonomy_version,
            ModelBinding.activated_at.is_not(None),
            ModelBinding.deactivated_at.is_(None),
        )
        return (await session.execute(stmt)).scalar_one_or_none()

    async def get_label_set(self, session: AsyncSession, label_set_id: uuid.UUID) -> LabelSet | None:
        return (
            await session.execute(select(LabelSet).where(LabelSet.label_set_id == label_set_id))
        ).scalar_one_or_none()

    async def get_propensity_model(
        self, session: AsyncSession, propensity_model_id: uuid.UUID
    ) -> PropensityModel | None:
        return (
            await session.execute(
                select(PropensityModel).where(
                    PropensityModel.propensity_model_id == propensity_model_id
                )
            )
        ).scalar_one_or_none()

    async def powered_calibration_exists_for_family(
        self, session: AsyncSession, equipment_family: str
    ) -> bool:
        """§5.6: "its label set's `powered` is true for the family." `powered`
        lives on `calibration_record` (§2.7), keyed per family (among other
        things) -- there is no separate `label_set.powered` column."""
        stmt = select(
            exists().where(
                CalibrationRecord.equipment_family == equipment_family,
                CalibrationRecord.powered.is_(True),
            )
        )
        return bool((await session.execute(stmt)).scalar_one())

    async def calibration_exists_for_triple(
        self, session: AsyncSession, *, tier: int, equipment_family: str, taxonomy_version: str
    ) -> bool:
        """§5.6: "a calibration record exists for at least one cell of the
        triple" -- existence only, regardless of `powered`."""
        stmt = select(
            exists().where(
                CalibrationRecord.tier == tier,
                CalibrationRecord.equipment_family == equipment_family,
                CalibrationRecord.taxonomy_version == taxonomy_version,
            )
        )
        return bool((await session.execute(stmt)).scalar_one())
