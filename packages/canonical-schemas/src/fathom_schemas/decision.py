"""The decision-theoretic conversion from `FailurePrediction` to expected
consequence. Document 22-pdm.md §7 -- authored here because 10-shared-packages.md
does not yet specify this module, even though 22-pdm.md §7.1 states it "ships
in `packages/canonical-schemas` as `fathom_schemas.decision`, beside
`FailurePrediction`". Treat 22-pdm.md §7 as authoritative for this module's
behavior, not any future revision of the shared-packages doc that disagrees
without citing a reason.

"Consumers do not compare `p_failure` across reference classes; the scheduling
optimizer applies a per-class decision-theoretic conversion to expected
consequence `[D7]`." (03 §7.1)
"""

from __future__ import annotations

import math
from enum import StrEnum

from pydantic import Field

from ._base import FathomModel, NonEmptyStr
from .prediction import FailurePrediction, ReferenceClass

CONVERSION_VERSION = "1.0.0"

# [PLACEHOLDER P-16] 22-pdm.md §7.4.
_FALLBACK_MULTIPLIER: dict[int, float] = {0: 1.0, 1: 1.3, 2: 1.6, 3: 2.2, 4: 3.0}

# [PLACEHOLDER P-16 continued] Sea-going tempo approximation, 07 §5.5 / 13 §11.1.
DEFAULT_OPERATING_FRACTION = 0.667


class Basis(StrEnum):
    ITEM_CONDITIONAL = "item_conditional"
    CLASS_RATE_CONVERTED = "class_rate_converted"


class TimingBasis(StrEnum):
    RUL_QUANTILES = "rul_quantiles"
    MEAN_RESIDUAL_LIFE_FROM_RATE = "mean_residual_life_from_rate"
    NONE = "none"


class RiskPosture(StrEnum):
    """[PLACEHOLDER P-17] Program decision, not an analytic one -- 22-pdm.md
    §7.4: "it encodes how much the Navy is willing to spend to avoid an
    unlikely severe failure." Default AVERSE for the highest consequence
    band, NEUTRAL otherwise."""

    NEUTRAL = "NEUTRAL"
    AVERSE = "AVERSE"


class ConsequenceWeights(FathomModel):
    """Sourced from Registry criticality. NOT owned by PdM -- 22-pdm.md §7.1.

    [PLACEHOLDER] The canonical shape of this type belongs to 20-registry.md,
    which has not yet defined it in a form this package can import. This is
    a minimal stand-in carrying exactly what `expected_consequence()` needs
    (the cost-unit value itself, plus the band it was derived from, for
    provenance) -- replace with an import from Registry's own build once
    that shape exists, rather than growing this class ad hoc.
    """

    consequence_value: float = Field(description="C, in the optimizer's cost units.")
    band: NonEmptyStr = Field(description="The criticality band this value was derived from.")


class ExpectedConsequence(FathomModel):
    p_event_horizon: float = Field(description="Probability of the event within the horizon, on a COMMON basis.")
    p_event_lower: float = Field(description="Epistemic interval, widened by fallback_level and cell size.")
    p_event_upper: float
    basis: Basis
    consequence_value: float
    expected_consequence: float = Field(description="THE only rankable quantity.")
    timing_basis: TimingBasis
    timing_p10: float | None = Field(default=None, description="None unless timing_basis is rul_quantiles.")
    timing_p50: float | None = Field(default=None)
    conversion_version: str
    inputs_digest: str


class UncalibratedAndUnrated(ValueError):
    """Raised only if `p_failure` AND `population_hazard_rate` are BOTH
    absent -- the schema's own `_rul_only_when_item_conditional`/
    `_calibration_gate` validators forbid this combination, so this should
    be unreachable in practice; it exists as a defensive backstop, never a
    normal control-flow path (22-pdm.md §7.3 Case C)."""


def _base_half_width(calibration_population: int | None) -> float:
    """Binomial/Wilson half-width on the cell count. A missing
    `calibration_population` on an otherwise-valid prediction is a producer
    defect (PdM always populates it, 22-pdm.md §2.1) -- fail loudly rather
    than silently widening or narrowing the interval."""
    if calibration_population is None:
        raise ValueError("calibration_population is required to compute the epistemic interval")
    n = max(calibration_population, 1)
    # z=1.96 (95%) Wilson half-width at p=0.5 (the widest case), used as a
    # cell-size-only proxy -- deliberately conservative and symmetric.
    z = 1.96
    return z * math.sqrt(0.25 / n)


def expected_consequence(
    pred: FailurePrediction,
    *,
    consequence: ConsequenceWeights,
    operating_fraction: float = DEFAULT_OPERATING_FRACTION,
    risk_posture: RiskPosture,
) -> ExpectedConsequence:
    """22-pdm.md §7. One implementation, two access paths (this function, and
    `POST /api/v1/pdm/expected-consequence`) -- nine transcriptions would
    produce nine subtly different conversions."""
    if pred.p_failure is None and pred.population_hazard_rate is None:
        raise UncalibratedAndUnrated(
            "both p_failure and population_hazard_rate are absent; the schema "
            "should have forbidden this combination already"
        )

    timing_p10: float | None = None
    timing_p50: float | None = None

    if pred.reference_class is ReferenceClass.ITEM:
        # Case A.
        assert pred.p_failure is not None  # guaranteed by _rul_only_when_item_conditional
        p_event_horizon = pred.p_failure
        basis = Basis.ITEM_CONDITIONAL
        timing_basis = TimingBasis.RUL_QUANTILES
        if pred.rul is not None:
            timing_p10 = pred.rul.p10
            timing_p50 = pred.rul.p50
    else:
        # Case B (niin_fleet | equipment_family | class_estimate), and Case C
        # (p_failure null, below the gate) is exactly this branch too, since
        # the calibration gate forces reference_class to class_estimate below n=50.
        assert pred.population_hazard_rate is not None
        h_op = pred.horizon_days * operating_fraction
        p_event_horizon = 1.0 - math.exp(-pred.population_hazard_rate * h_op)
        basis = Basis.CLASS_RATE_CONVERTED
        timing_basis = TimingBasis.MEAN_RESIDUAL_LIFE_FROM_RATE
        timing_p50 = 1.0 / pred.population_hazard_rate
        # timing_p10 stays None -- there is no p10 for a class rate. Never synthesize one.

    half_width = _base_half_width(pred.calibration_population) * _FALLBACK_MULTIPLIER[pred.fallback_level]
    p_event_lower = max(0.0, p_event_horizon - half_width)
    p_event_upper = min(1.0, p_event_horizon + half_width)

    if risk_posture is RiskPosture.NEUTRAL:
        expected = p_event_horizon * consequence.consequence_value
    else:
        expected = p_event_upper * consequence.consequence_value

    inputs_digest = pred.content_hash()

    return ExpectedConsequence(
        p_event_horizon=p_event_horizon,
        p_event_lower=p_event_lower,
        p_event_upper=p_event_upper,
        basis=basis,
        consequence_value=consequence.consequence_value,
        expected_consequence=expected,
        timing_basis=timing_basis,
        timing_p10=timing_p10,
        timing_p50=timing_p50,
        conversion_version=CONVERSION_VERSION,
        inputs_digest=inputs_digest,
    )
