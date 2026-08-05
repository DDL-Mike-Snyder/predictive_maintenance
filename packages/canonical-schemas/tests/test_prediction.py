import datetime as dt
from uuid import uuid4

import pytest

from fathom_schemas import (
    Basis,
    ConsequenceWeights,
    FailurePrediction,
    ReferenceClass,
    RiskPosture,
    Rul,
    RulUnit,
    TimingBasis,
    UncalibratedAndUnrated,
    expected_consequence,
)


def _base_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "asset_id": uuid4(),
        "installed_item_id": uuid4(),
        "position_id": uuid4(),
        "niin": "012345678",
        "equipment_family": "pump-centrifugal",
        "baseline_id": uuid4(),
        "baseline_epoch": 1,
        "horizon_days": 90,
        "reference_class": ReferenceClass.ITEM,
        "sharpness": 0.5,
        "calibration_population": 120,
        "confidence": 0.8,
        "fallback_level": 0,
        "tier": 2,
        "model_version": "tier2-degradation-1.0.0",
        "scoring_run_id": uuid4(),
        "computed_at": dt.datetime.now(dt.timezone.utc),
        "p_failure": 0.12,
        "rul": Rul(p10=10, p50=40, p90=90, unit=RulUnit.DAYS),
    }
    kwargs.update(overrides)
    return kwargs


def test_item_conditional_prediction_round_trips() -> None:
    pred = FailurePrediction(**_base_kwargs())
    assert pred.wire_dict()["p_failure"] == pytest.approx(0.12)
    assert pred.content_hash()  # non-empty, deterministic


def test_rul_forbidden_off_item_reference_class() -> None:
    with pytest.raises(ValueError, match="not item-conditional"):
        FailurePrediction(
            **_base_kwargs(
                reference_class=ReferenceClass.NIIN_FLEET,
                p_failure=None,
                rul=Rul(p10=10, p50=40, p90=90, unit=RulUnit.DAYS),
                population_hazard_rate=0.002,
            )
        )


def test_calibration_gate_forces_class_estimate_below_floor() -> None:
    with pytest.raises(ValueError, match="below the gate"):
        FailurePrediction(
            **_base_kwargs(
                reference_class=ReferenceClass.NIIN_FLEET,
                p_failure=None,
                rul=None,
                calibration_population=10,
                population_hazard_rate=0.002,
            )
        )


def test_below_gate_class_estimate_requires_null_p_failure() -> None:
    with pytest.raises(ValueError, match="p_failure MUST be null"):
        FailurePrediction(
            **_base_kwargs(
                reference_class=ReferenceClass.CLASS_ESTIMATE,
                p_failure=0.2,
                rul=None,
                calibration_population=10,
                population_hazard_rate=0.002,
            )
        )


def test_expected_consequence_item_conditional_case_a() -> None:
    pred = FailurePrediction(**_base_kwargs())
    result = expected_consequence(
        pred,
        consequence=ConsequenceWeights(consequence_value=1000.0, band="high"),
        risk_posture=RiskPosture.NEUTRAL,
    )
    assert result.basis is Basis.ITEM_CONDITIONAL
    assert result.timing_basis is TimingBasis.RUL_QUANTILES
    assert result.timing_p10 == 10
    assert result.expected_consequence == pytest.approx(0.12 * 1000.0)


def test_expected_consequence_class_rate_never_synthesizes_p10() -> None:
    pred = FailurePrediction(
        **_base_kwargs(
            reference_class=ReferenceClass.CLASS_ESTIMATE,
            p_failure=None,
            rul=None,
            calibration_population=10,
            population_hazard_rate=0.002,
            fallback_level=4,
        )
    )
    result = expected_consequence(
        pred,
        consequence=ConsequenceWeights(consequence_value=1000.0, band="high"),
        risk_posture=RiskPosture.AVERSE,
    )
    assert result.basis is Basis.CLASS_RATE_CONVERTED
    assert result.timing_p10 is None
    assert result.timing_p50 == pytest.approx(1 / 0.002)
    # AVERSE uses the upper bound, so expected consequence must be >= the point estimate's contribution
    assert result.expected_consequence >= result.p_event_horizon * 1000.0


def test_uncalibrated_and_unrated_is_unreachable_via_schema() -> None:
    # The schema's own validators should make this combination impossible to construct,
    # which is exactly what protects expected_consequence() from ever needing to raise.
    with pytest.raises(ValueError):
        FailurePrediction(
            **_base_kwargs(
                reference_class=ReferenceClass.CLASS_ESTIMATE,
                p_failure=None,
                rul=None,
                population_hazard_rate=None,
            )
        )
