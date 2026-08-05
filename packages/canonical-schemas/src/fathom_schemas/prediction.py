"""`FailurePrediction`. Document 03 §7.1.

Note what consumers must never do (DO-NOT items 20-21, 09-monorepo-and-conventions.md):
never branch on `tier` (branch on `reference_class`); never treat a null
`p_failure` as zero; never fold `fallback_level` into `confidence`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from ._base import FathomModel, Niin, NonEmptyStr, UtcDateTime
from .constants import CALIBRATION_POPULATION_FLOOR


class ReferenceClass(StrEnum):
    ITEM = "item"
    NIIN_FLEET = "niin_fleet"
    EQUIPMENT_FAMILY = "equipment_family"
    CLASS_ESTIMATE = "class_estimate"

    @property
    def is_item_conditional(self) -> bool:
        return self is ReferenceClass.ITEM


class RulUnit(StrEnum):
    DAYS = "days"
    STEAMING_HOURS = "steaming_hours"
    EOH = "eoh"
    CYCLES = "cycles"
    SORTIES = "sorties"
    DIVES = "dives"


class Rul(FathomModel):
    p10: float = Field(ge=0.0)
    p50: float = Field(ge=0.0)
    p90: float = Field(ge=0.0)
    unit: RulUnit

    @model_validator(mode="after")
    def _quantiles_ordered(self) -> Self:
        if not (self.p10 <= self.p50 <= self.p90):
            raise ValueError(
                f"RUL quantiles must be ordered p10<=p50<=p90; got {self.p10}, {self.p50}, {self.p90}"
            )
        return self


class ContributingFactor(FathomModel):
    """Renamed from `drivers` [D23]. A causal statement must cite an
    adjudicated Failure Intelligence hypothesis -- this is never one."""

    factor: NonEmptyStr
    contribution: float
    attribution_method: NonEmptyStr
    stability: float = Field(description="Rank stability across runs or bootstrap.")
    observation_ref: NonEmptyStr = Field(
        description="Points at a feature observation, NOT at itself."
    )

    def is_displayable(self, stability_threshold: float) -> bool:
        return self.stability >= stability_threshold


class FailurePrediction(FathomModel):
    asset_id: UUID
    installed_item_id: UUID
    position_id: UUID
    niin: Niin
    equipment_family: NonEmptyStr
    baseline_id: UUID
    baseline_epoch: int = Field(ge=0)
    horizon_days: int = Field(gt=0)
    p_failure: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "NULL when calibration_population < 50. A predicted probability "
            "that cannot be calibrated must not be emitted merely because the "
            "field exists; omission is the honest signal."
        ),
    )
    reference_class: ReferenceClass
    sharpness: float = Field(description="Dispersion relative to the reference-class base rate.")
    calibration_population: int | None = Field(default=None, ge=0)
    rul: Rul | None = Field(default=None, description="Omitted where not item-conditional.")
    population_hazard_rate: float | None = Field(
        default=None, ge=0.0, description="Emitted INSTEAD OF `rul` for non-item reference classes."
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Sharpness-and-fit confidence only.")
    fallback_level: int = Field(ge=0, le=4, description="Cold-start depth, NOT folded into confidence.")
    tier: int = Field(ge=0, le=3, description="Transparency only. Never branch on this -- FTH006.")
    contributing_factors: tuple[ContributingFactor, ...] = Field(default=())
    model_version: NonEmptyStr
    scoring_run_id: UUID
    computed_at: UtcDateTime

    @model_validator(mode="after")
    def _rul_only_when_item_conditional(self) -> Self:
        if self.reference_class.is_item_conditional:
            if self.rul is None:
                raise ValueError("reference_class='item' is item-conditional and REQUIRES `rul`")
            if self.population_hazard_rate is not None:
                raise ValueError(
                    "`population_hazard_rate` is emitted INSTEAD OF `rul`, for "
                    "non-item reference classes only"
                )
        else:
            if self.rul is not None:
                raise ValueError(
                    f"reference_class={self.reference_class.value!r} is not "
                    "item-conditional, so `rul` must be omitted"
                )
            if self.population_hazard_rate is None:
                raise ValueError(
                    f"reference_class={self.reference_class.value!r} REQUIRES `population_hazard_rate`"
                )
        return self

    @model_validator(mode="after")
    def _calibration_gate(self) -> Self:
        n = self.calibration_population
        if n is None:
            return self
        if n < CALIBRATION_POPULATION_FLOOR and self.reference_class is not ReferenceClass.CLASS_ESTIMATE:
            raise ValueError(
                f"calibration_population={n} is below the gate of "
                f"{CALIBRATION_POPULATION_FLOOR}; reference_class must be 'class_estimate'"
            )
        if n < CALIBRATION_POPULATION_FLOOR:
            if self.p_failure is not None:
                raise ValueError(
                    f"calibration_population={n} is below the gate: p_failure MUST be null"
                )
            if self.population_hazard_rate is None:
                raise ValueError(
                    f"calibration_population={n} is below the gate: "
                    "population_hazard_rate is REQUIRED when p_failure is null"
                )
        return self

    def comparable_with(self, other: FailurePrediction) -> bool:
        """THE only sanctioned cross-prediction comparison of raw fields.
        Never a `tier` comparison -- lint rule FTH006 forbids it statically."""
        return self.reference_class is other.reference_class

    def is_stale_against(self, current_baseline_epoch: int) -> bool:
        return self.baseline_epoch < current_baseline_epoch
