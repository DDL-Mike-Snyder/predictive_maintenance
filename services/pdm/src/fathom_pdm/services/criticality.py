"""The criticality scorer and tier assignment engine. Document 22-pdm.md
§3.2-§3.4: a reviewable, versioned rule set that produces an auditable
score, not a model output (04 §4).

**Scope boundary, deliberately drawn here.** This module implements the
*mechanism* §3.2-§3.4 specify -- the weighted-sum formula, the raw-band
step function, the hysteresis hold/adopt rule, and the ceiling/min. It does
NOT implement:
  - §3.1's per-input normalization (Registry band mapping for
    mission-criticality/consequence-of-failure, the IPCW-weighted and
    compartment-scoped CASREP-rate and fleet-population curves). Those are
    read-model projections requiring Registry/Scheduling event consumers
    that don't exist yet (a much larger undertaking than "the algorithm").
    This module takes the five inputs already normalized to [0, 100], per
    §3.1's own "Normalization to 0-100" column.
  - §3.3's `data_availability_ceiling` inputs (spotlight-grade coverage,
    adjudicated causal findings, condition/sensor mapping, usage-counter
    continuity) -- also read-model projections from Telemetry/Failure
    Intelligence/Scheduling. `data_availability_ceiling()` below takes
    those as already-resolved booleans.
Wiring the actual read models that produce these inputs is event-consumer
work (see CLAUDE.md).

**A formula inconsistency resolved here, not literally transcribed.** §3.2
gives `score = 100 x sum(w_j * x_j) / sum(w_j)`. Applied to x_j already on a
[0, 100] scale (as §3.1 specifies), that produces values up to 10,000, not
the documented and range-checked [0, 100] `score` field. The "100 x" factor
is only correct if x_j is a [0, 1] fraction. Since §3.1 explicitly
normalizes each input to [0, 100] for storage, this implementation uses
`score = sum(w_j * x_j) / sum(w_j)` -- a weighted average of already-[0,100]
values is itself in [0, 100], with no extra factor needed. `raw_band`'s
thresholds (80/60/35) are unambiguous only under this reading.

**All numeric placeholders (weights, band edges, hysteresis margin/window)
are [PLACEHOLDER P-2/P-3/P-4], pending Phase 3 SME validation** -- per
`tier_policy.sme_validated`, they live in the versioned `TierPolicy` row,
not hardcoded here. `DEFAULT_TIER_POLICY` below is the not-yet-validated
starting point the spec itself proposes.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import TypedDict

_TWO_PLACES = Decimal("0.01")


class TierPolicyWeights(TypedDict):
    mission_criticality: float
    consequence_of_failure: float
    casrep_history: float
    sensor_availability: float
    fleet_population: float


class BandThresholds(TypedDict):
    """Lower-bound score for each tier; below `tier_1` is tier 0."""

    tier_1: float
    tier_2: float
    tier_3: float


class HysteresisParams(TypedDict):
    min_point_crossing: float
    # Only a 2-consecutive-assessment window is implemented (resolve_proposed_tier
    # looks back exactly one prior row) -- present for the row's own record-keeping,
    # not read by this module. Widening the window needs more history than one
    # prior row, i.e. a resolve_proposed_tier signature change, not just a config bump.
    persistence_assessments: int


#: §3.2's proposed weights [PLACEHOLDER P-2], §3.3's proposed band edges
#: [PLACEHOLDER P-3], §3.4's proposed hysteresis parameters [PLACEHOLDER P-4].
#: Not SME-validated -- ships with `tier_policy.sme_validated = False`.
DEFAULT_WEIGHTS: TierPolicyWeights = {
    "mission_criticality": 0.30,
    "consequence_of_failure": 0.25,
    "casrep_history": 0.20,
    "sensor_availability": 0.15,
    "fleet_population": 0.10,
}
DEFAULT_BAND_THRESHOLDS: BandThresholds = {"tier_1": 35, "tier_2": 60, "tier_3": 80}
DEFAULT_HYSTERESIS: HysteresisParams = {"min_point_crossing": 5, "persistence_assessments": 2}


@dataclass(frozen=True, slots=True)
class CriticalityInputs:
    """The five §3.1 inputs, already normalized to [0, 100]. See this
    module's docstring for why normalization itself is out of scope here."""

    mission_criticality: Decimal
    consequence_of_failure: Decimal
    casrep_history: Decimal
    sensor_availability: Decimal
    fleet_population: Decimal


@dataclass(frozen=True, slots=True)
class DataAvailabilityInputs:
    """§3.3's ceiling conditions, already resolved to booleans by the
    caller's own read-model lookups."""

    spotlight_grade_coverage_mapped: bool
    adjudicated_causal_finding_exists: bool
    causal_feature_set_definition_pinned: bool
    condition_sensor_channels_mapped_and_reporting: bool
    usage_counter_unbroken_since_install: bool


@dataclass(frozen=True, slots=True)
class PriorAssessment:
    """The minimal state `resolve_proposed_tier` needs from the immediately
    preceding assessment row for this (niin, equipment_family) -- nothing
    else, since `proposed_tier` is itself the fully hysteresis-settled
    value (22-pdm.md §3.4: "the two never need to be reconciled after the
    fact"). Construct from a `CriticalityAssessment` row's own
    `score`/`proposed_tier`/`tier_policy_version` columns."""

    score: Decimal
    proposed_tier: int
    tier_policy_version: str


def compute_score(inputs: CriticalityInputs, weights: TierPolicyWeights) -> Decimal:
    """§3.2. See this module's docstring for why this omits the spec's
    literal "100 x" factor."""
    numerator = (
        Decimal(str(weights["mission_criticality"])) * inputs.mission_criticality
        + Decimal(str(weights["consequence_of_failure"])) * inputs.consequence_of_failure
        + Decimal(str(weights["casrep_history"])) * inputs.casrep_history
        + Decimal(str(weights["sensor_availability"])) * inputs.sensor_availability
        + Decimal(str(weights["fleet_population"])) * inputs.fleet_population
    )
    denominator = sum(Decimal(str(w)) for w in weights.values())
    return (numerator / denominator).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def raw_band(score: Decimal, band_thresholds: BandThresholds) -> int:
    """§3.3. Pure, memoryless function of `score` alone -- never itself
    persisted (that's `proposed_tier`'s job, via `resolve_proposed_tier`)."""
    if score >= Decimal(str(band_thresholds["tier_3"])):
        return 3
    if score >= Decimal(str(band_thresholds["tier_2"])):
        return 2
    if score >= Decimal(str(band_thresholds["tier_1"])):
        return 1
    return 0


def _band_edge(prior_tier: int, *, direction_up: bool, band_thresholds: BandThresholds) -> Decimal:
    """The score threshold that bounds the tier currently held
    (`prior.proposed_tier`) on the side the new `raw_band` is crossing
    toward -- moving up, the threshold that must be cleared to *enter* the
    next tier; moving down, the threshold that must be cleared to *exit*
    the tier currently held. Using the held tier's own boundary (rather
    than, say, the target tier's) is what makes this correct even for a
    multi-band jump: "5 points past the edge" means 5 points past the
    boundary of the band being left, however far past it lands."""
    key_tier = prior_tier + 1 if direction_up else prior_tier
    return Decimal(str(band_thresholds[f"tier_{key_tier}"]))  # type: ignore[literal-required]


def resolve_proposed_tier(
    *,
    current_score: Decimal,
    current_raw_band: int,
    current_tier_policy_version: str,
    prior: PriorAssessment | None,
    band_thresholds: BandThresholds,
    hysteresis: HysteresisParams,
) -> int:
    """§3.3/§3.4's hysteresis gate: the value actually written as
    `proposed_tier`.

    Needs only the single immediately-preceding assessment row (`prior`),
    not a persisted crossing counter -- `prior.proposed_tier` already
    encodes every earlier hysteresis decision, and `prior.score` is enough
    to ask "did the identical candidate crossing also show sufficient
    margin one assessment ago," which is exactly the "persisted across 2
    consecutive assessments" test.

    A `tier_policy_version` change resets hysteresis (adopts `raw_band`
    immediately): a policy activation is its own controlled, dry-run-gated
    event (§3.5) that mandates a full fleet re-score, not a continuation of
    whatever the previous policy's bands were tracking.
    """
    if prior is None:
        return current_raw_band
    if prior.tier_policy_version != current_tier_policy_version:
        return current_raw_band
    if current_raw_band == prior.proposed_tier:
        return current_raw_band  # no crossing pending

    direction_up = current_raw_band > prior.proposed_tier
    edge = _band_edge(
        prior.proposed_tier, direction_up=direction_up, band_thresholds=band_thresholds
    )
    margin = Decimal(str(hysteresis["min_point_crossing"]))

    def _margin_ok(score: Decimal) -> bool:
        return (score - edge >= margin) if direction_up else (edge - score >= margin)

    if not _margin_ok(current_score):
        return prior.proposed_tier  # crossing candidate exists but hasn't cleared the margin yet

    prior_raw_band = raw_band(prior.score, band_thresholds)
    if prior_raw_band == current_raw_band and _margin_ok(prior.score):
        return current_raw_band  # persisted across 2 consecutive assessments -> adopt

    return prior.proposed_tier  # first sighting with sufficient margin; hold one more cycle


def data_availability_ceiling(inputs: DataAvailabilityInputs) -> int:
    """§3.3's ceiling. A mission-critical NIIN with no instrumentation is a
    tier-0 item with a high score, not a tier-3 item with fabricated
    inputs -- see `assigned_tier`."""
    if (
        inputs.spotlight_grade_coverage_mapped
        and inputs.adjudicated_causal_finding_exists
        and inputs.causal_feature_set_definition_pinned
    ):
        return 3
    if inputs.condition_sensor_channels_mapped_and_reporting:
        return 2
    if inputs.usage_counter_unbroken_since_install:
        return 1
    return 0


def assigned_tier(proposed_tier: int, ceiling: int) -> int:
    """`tier_is_capped` (the DB CHECK constraint), computed here so a
    caller never has to derive it separately from what it writes."""
    return min(proposed_tier, ceiling)
