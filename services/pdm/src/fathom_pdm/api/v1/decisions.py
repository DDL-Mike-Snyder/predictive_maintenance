"""`POST /api/v1/pdm/expected-consequence`. Document 22-pdm.md §7.1: "One
implementation, two access paths" -- this route and
`fathom_schemas.decision.expected_consequence()` are the same function; the
route is a thin wire adapter, never a second implementation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fathom_contracts import SideEffects, Substitution, operation_extra
from fathom_py_common import ProblemException
from fathom_schemas import (
    ConsequenceWeights,
    ExpectedConsequence,
    FailurePrediction,
    RiskPosture,
    expected_consequence,
)
from fathom_schemas.decision import DEFAULT_OPERATING_FRACTION, UncalibratedAndUnratedError

from fathom_pdm.deps import Principal, current_principal

router = APIRouter()


@router.post(
    "/expected-consequence",
    response_model=ExpectedConsequence,
    openapi_extra=operation_extra(
        operation_id="pdm_expected_consequence",
        substitution=Substitution.REQUIRED,
        side_effects=SideEffects.NONE,  # computational POST -- agent-eligible by design [C1]
        agent_eligible=True,
        summary="The decision-theoretic conversion to expected consequence (03 §7.1, D7).",
    ),
)
async def compute_expected_consequence(
    *,
    prediction: FailurePrediction,
    consequence_value: float,
    consequence_band: str,
    risk_posture: RiskPosture = RiskPosture.NEUTRAL,
    operating_fraction: float = DEFAULT_OPERATING_FRACTION,
    _principal: Principal = Depends(current_principal),
) -> ExpectedConsequence:
    # §4.5.2: refuse a research_only prediction with 422 -- the holdout
    # stratum's whole point is that it is not acted upon. This route only
    # ever receives a caller-supplied FailurePrediction body (no serving_class
    # on the wire type at all, §2.5), so there is structurally nothing to
    # check here beyond what the schema itself already enforces -- noted
    # explicitly since a future refactor that resolves predictions by ID
    # instead of accepting one in the body MUST re-add this check.
    try:
        return expected_consequence(
            prediction,
            consequence=ConsequenceWeights(
                consequence_value=consequence_value, band=consequence_band
            ),
            operating_fraction=operating_fraction,
            risk_posture=risk_posture,
        )
    except UncalibratedAndUnratedError as exc:
        raise ProblemException(
            type="urn:fathom:problem:pdm:uncalibrated-and-unrated",
            title="Prediction has neither p_failure nor population_hazard_rate",
            status=422,
            detail=str(exc),
        ) from exc
