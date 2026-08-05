"""22-pdm.md §3.2-§3.4: the scoring formula, raw-band step function,
hysteresis gate, and data-availability ceiling. Pure functions -- no DB, no
event consumers (see `fathom_pdm.services.criticality`'s module docstring
for the deliberate scope boundary)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fathom_pdm.services.criticality import (
    DEFAULT_BAND_THRESHOLDS,
    DEFAULT_HYSTERESIS,
    DEFAULT_WEIGHTS,
    CriticalityInputs,
    DataAvailabilityInputs,
    PriorAssessment,
    assigned_tier,
    compute_score,
    data_availability_ceiling,
    raw_band,
    resolve_proposed_tier,
)


def _inputs(**overrides: Decimal) -> CriticalityInputs:
    base = {
        "mission_criticality": Decimal(50),
        "consequence_of_failure": Decimal(50),
        "casrep_history": Decimal(50),
        "sensor_availability": Decimal(50),
        "fleet_population": Decimal(50),
    }
    base.update(overrides)
    return CriticalityInputs(**base)


def test_compute_score_uniform_inputs_returns_that_value() -> None:
    # A weighted average of five identical values is that value, regardless
    # of the weights (as long as they sum sensibly) -- the simplest possible
    # correctness check on the formula shape.
    assert compute_score(_inputs(), DEFAULT_WEIGHTS) == Decimal("50.00")


def test_compute_score_stays_within_0_100_for_extreme_inputs() -> None:
    # Guards the "100 x" formula-inconsistency fix documented in the module:
    # a naive transcription of 22-pdm.md's literal formula against already
    # [0,100] inputs would produce values up to 10,000.
    all_max = _inputs(
        mission_criticality=Decimal(100),
        consequence_of_failure=Decimal(100),
        casrep_history=Decimal(100),
        sensor_availability=Decimal(100),
        fleet_population=Decimal(100),
    )
    assert compute_score(all_max, DEFAULT_WEIGHTS) == Decimal("100.00")


def test_compute_score_respects_weight_ordering() -> None:
    # Mission-criticality is weighted highest; moving it alone should move
    # the score more than moving the lowest-weighted input (fleet_population)
    # by the same amount.
    baseline = compute_score(_inputs(), DEFAULT_WEIGHTS)
    mission_up = compute_score(_inputs(mission_criticality=Decimal(60)), DEFAULT_WEIGHTS)
    population_up = compute_score(_inputs(fleet_population=Decimal(60)), DEFAULT_WEIGHTS)
    assert (mission_up - baseline) > (population_up - baseline)


@pytest.mark.parametrize(
    ("score", "expected_tier"),
    [
        (Decimal("34.99"), 0),
        (Decimal("35.00"), 1),
        (Decimal("59.99"), 1),
        (Decimal("60.00"), 2),
        (Decimal("79.99"), 2),
        (Decimal("80.00"), 3),
        (Decimal("100.00"), 3),
    ],
)
def test_raw_band_edges(score: Decimal, expected_tier: int) -> None:
    assert raw_band(score, DEFAULT_BAND_THRESHOLDS) == expected_tier


def test_resolve_proposed_tier_no_prior_adopts_raw_band_immediately() -> None:
    assert (
        resolve_proposed_tier(
            current_score=Decimal(90),
            current_raw_band=3,
            current_tier_policy_version="v1",
            prior=None,
            band_thresholds=DEFAULT_BAND_THRESHOLDS,
            hysteresis=DEFAULT_HYSTERESIS,
        )
        == 3
    )


def test_resolve_proposed_tier_no_crossing_holds_steady() -> None:
    prior = PriorAssessment(score=Decimal(50), proposed_tier=1, tier_policy_version="v1")
    assert (
        resolve_proposed_tier(
            current_score=Decimal(52),
            current_raw_band=1,
            current_tier_policy_version="v1",
            prior=prior,
            band_thresholds=DEFAULT_BAND_THRESHOLDS,
            hysteresis=DEFAULT_HYSTERESIS,
        )
        == 1
    )


def test_resolve_proposed_tier_crossing_without_margin_holds() -> None:
    # raw_band says 2 (score=61), but only 1 point past the tier_2 edge (60)
    # -- short of the 5-point margin -- so proposed_tier must hold at 1.
    prior = PriorAssessment(score=Decimal(55), proposed_tier=1, tier_policy_version="v1")
    assert (
        resolve_proposed_tier(
            current_score=Decimal(61),
            current_raw_band=2,
            current_tier_policy_version="v1",
            prior=prior,
            band_thresholds=DEFAULT_BAND_THRESHOLDS,
            hysteresis=DEFAULT_HYSTERESIS,
        )
        == 1
    )


def test_resolve_proposed_tier_first_sighting_with_margin_still_holds() -> None:
    # Margin cleared (score=66, 6 points past the tier_2 edge), but this is
    # the FIRST assessment showing it -- prior.score=55 wasn't even past the
    # edge. Must hold one more cycle per the 2-consecutive-assessments rule.
    prior = PriorAssessment(score=Decimal(55), proposed_tier=1, tier_policy_version="v1")
    assert (
        resolve_proposed_tier(
            current_score=Decimal(66),
            current_raw_band=2,
            current_tier_policy_version="v1",
            prior=prior,
            band_thresholds=DEFAULT_BAND_THRESHOLDS,
            hysteresis=DEFAULT_HYSTERESIS,
        )
        == 1
    )


def test_resolve_proposed_tier_persisted_crossing_adopts_raw_band() -> None:
    # Same candidate crossing (tier 1 -> 2) with sufficient margin on BOTH
    # this assessment (66) and the one before it (67) -- persisted across 2
    # consecutive assessments, so proposed_tier now adopts raw_band.
    prior = PriorAssessment(score=Decimal(67), proposed_tier=1, tier_policy_version="v1")
    assert (
        resolve_proposed_tier(
            current_score=Decimal(66),
            current_raw_band=2,
            current_tier_policy_version="v1",
            prior=prior,
            band_thresholds=DEFAULT_BAND_THRESHOLDS,
            hysteresis=DEFAULT_HYSTERESIS,
        )
        == 2
    )


def test_resolve_proposed_tier_downward_crossing_uses_held_tiers_own_edge() -> None:
    # Held at tier 2 (edge = tier_2's own threshold, 60), dropping to raw_band
    # 0 -- a multi-band drop. Margin must be measured against 60 (the edge of
    # the tier being LEFT), not tier_1's threshold (35).
    prior_no_margin = PriorAssessment(score=Decimal(58), proposed_tier=2, tier_policy_version="v1")
    # score=56 is only 4 points below 60 -- short of margin -- must hold at 2.
    assert (
        resolve_proposed_tier(
            current_score=Decimal(56),
            current_raw_band=1,
            current_tier_policy_version="v1",
            prior=prior_no_margin,
            band_thresholds=DEFAULT_BAND_THRESHOLDS,
            hysteresis=DEFAULT_HYSTERESIS,
        )
        == 2
    )


def test_resolve_proposed_tier_policy_version_change_resets_hysteresis() -> None:
    # A policy activation is its own controlled, dry-run-gated event (§3.5);
    # hysteresis does not carry over from the retired policy's bands.
    prior = PriorAssessment(score=Decimal(58), proposed_tier=1, tier_policy_version="v1")
    assert (
        resolve_proposed_tier(
            current_score=Decimal(61),
            current_raw_band=2,
            current_tier_policy_version="v2",
            prior=prior,
            band_thresholds=DEFAULT_BAND_THRESHOLDS,
            hysteresis=DEFAULT_HYSTERESIS,
        )
        == 2
    )


def test_data_availability_ceiling_tier_3_requires_all_three() -> None:
    full = DataAvailabilityInputs(
        spotlight_grade_coverage_mapped=True,
        adjudicated_causal_finding_exists=True,
        causal_feature_set_definition_pinned=True,
        condition_sensor_channels_mapped_and_reporting=True,
        usage_counter_unbroken_since_install=True,
    )
    assert data_availability_ceiling(full) == 3

    missing_one = DataAvailabilityInputs(
        spotlight_grade_coverage_mapped=True,
        adjudicated_causal_finding_exists=True,
        causal_feature_set_definition_pinned=False,
        condition_sensor_channels_mapped_and_reporting=True,
        usage_counter_unbroken_since_install=True,
    )
    assert data_availability_ceiling(missing_one) == 2


def test_data_availability_ceiling_zero_when_nothing_available() -> None:
    nothing = DataAvailabilityInputs(
        spotlight_grade_coverage_mapped=False,
        adjudicated_causal_finding_exists=False,
        causal_feature_set_definition_pinned=False,
        condition_sensor_channels_mapped_and_reporting=False,
        usage_counter_unbroken_since_install=False,
    )
    assert data_availability_ceiling(nothing) == 0


def test_assigned_tier_is_the_lesser_of_proposed_and_ceiling() -> None:
    # The mission-critical-but-uninstrumented case §3.3 calls out by name:
    # a high proposed_tier capped hard by a zero ceiling.
    assert assigned_tier(proposed_tier=3, ceiling=0) == 0
    assert assigned_tier(proposed_tier=1, ceiling=3) == 1
