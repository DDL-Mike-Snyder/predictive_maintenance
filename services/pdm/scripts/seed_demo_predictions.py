"""Seeds a handful of realistic predictions through PdM's REAL bulk-ingest
API (never direct SQL) -- for demoing 51-operator-console.md §11's Fleet-
Risk Triage screen (`apps/web`'s `FleetRiskTriage`) against real data
instead of mocks. Run against any real, migrated PdM instance:

    PDM_BASE_URL=http://localhost:8001 python scripts/seed_demo_predictions.py

Covers the cases §11.3/§11.4 actually render differently: an `item`-
conditional prediction with a real `rul` distribution and contributing
factors (the deep-dive box's real content), a `niin_fleet` and an
`equipment_family` prediction (population_hazard_rate, no `rul`), and a
`class_estimate` prediction below the calibration floor (the
`UncalibratedCell` case -- `p_failure` null, `population_hazard_rate`
present, per 03 §7.1/22 §6.3's DB-enforced consequences).
"""

from __future__ import annotations

import datetime as dt
import os
import uuid

import httpx

BASE_URL = os.environ.get("PDM_BASE_URL", "http://localhost:8001")
PRINCIPAL = "demo-seed-script"


def _prediction(
    *,
    reference_class: str,
    horizon_days: int,
    p_failure: float | None,
    calibration_population: int | None,
    population_hazard_rate: float | None,
    rul: dict | None,
    fallback_level: int,
    contributing_factors: list[dict],
    tier: int,
    scoring_run_id: str,
) -> dict:
    now = dt.datetime.now(dt.UTC).isoformat()
    return {
        "asset_id": str(uuid.uuid4()),
        "installed_item_id": str(uuid.uuid4()),
        "position_id": str(uuid.uuid4()),
        "niin": "123456789",
        "equipment_family": "diesel_generator",
        "baseline_id": str(uuid.uuid4()),
        "baseline_epoch": 0,
        "horizon_days": horizon_days,
        "p_failure": p_failure,
        "reference_class": reference_class,
        "sharpness": 0.7,
        "calibration_population": calibration_population,
        "rul": rul,
        "population_hazard_rate": population_hazard_rate,
        "confidence": 0.75,
        "fallback_level": fallback_level,
        "tier": tier,
        "contributing_factors": contributing_factors,
        "model_version": "demo-seed-v1",
        "scoring_run_id": scoring_run_id,
        "computed_at": now,
    }


def main() -> None:
    headers = {
        "X-Fathom-Principal": PRINCIPAL,
        "Idempotency-Key": f"demo-seed-{uuid.uuid4()}",
    }
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        scoring_run_resp = client.post(
            "/api/v1/pdm/scoring-runs",
            json={"stratum": "operational", "scope": {"equipment_family": "diesel_generator"}},
            headers=headers,
        )
        scoring_run_resp.raise_for_status()
        scoring_run_id = scoring_run_resp.json()["scoring_run_id"]
        print(f"scoring_run_id = {scoring_run_id}")  # noqa: T201 -- this IS the script's output

        predictions = [
            _prediction(
                reference_class="item",
                horizon_days=30,
                p_failure=0.42,
                calibration_population=250,
                population_hazard_rate=None,
                rul={"p10": 45, "p50": 90, "p90": 160, "unit": "days"},
                fallback_level=0,
                contributing_factors=[
                    {
                        "factor": "vibration_rms_trend",
                        "contribution": 0.31,
                        "attribution_method": "shap_treeexplainer",
                        "stability": 0.86,
                        "observation_ref": "fathom://telemetry/health-indicator/demo-1",
                    },
                    {
                        "factor": "oil_particulate_count",
                        "contribution": 0.18,
                        "attribution_method": "shap_treeexplainer",
                        "stability": 0.71,
                        "observation_ref": "fathom://telemetry/health-indicator/demo-2",
                    },
                ],
                tier=3,
                scoring_run_id=scoring_run_id,
            ),
            _prediction(
                reference_class="item",
                horizon_days=14,
                p_failure=0.81,
                calibration_population=180,
                population_hazard_rate=None,
                rul={"p10": 8, "p50": 20, "p90": 42, "unit": "days"},
                fallback_level=0,
                contributing_factors=[
                    {
                        "factor": "coolant_temp_delta",
                        "contribution": 0.44,
                        "attribution_method": "cox_partial_effect",
                        "stability": 0.79,
                        "observation_ref": "fathom://telemetry/health-indicator/demo-3",
                    },
                ],
                tier=3,
                scoring_run_id=scoring_run_id,
            ),
            _prediction(
                reference_class="niin_fleet",
                horizon_days=60,
                p_failure=0.19,
                calibration_population=340,
                population_hazard_rate=0.0031,
                rul=None,
                fallback_level=1,
                contributing_factors=[],
                tier=1,
                scoring_run_id=scoring_run_id,
            ),
            _prediction(
                reference_class="equipment_family",
                horizon_days=90,
                p_failure=0.07,
                calibration_population=1200,
                population_hazard_rate=0.0012,
                rul=None,
                fallback_level=2,
                contributing_factors=[],
                tier=0,
                scoring_run_id=scoring_run_id,
            ),
            _prediction(
                reference_class="class_estimate",
                horizon_days=30,
                p_failure=None,
                calibration_population=12,
                population_hazard_rate=0.0045,
                rul=None,
                fallback_level=4,
                contributing_factors=[],
                tier=0,
                scoring_run_id=scoring_run_id,
            ),
        ]

        ingest_resp = client.post(
            f"/api/v1/pdm/scoring-runs/{scoring_run_id}/predictions",
            json={"predictions": predictions},
            headers={**headers, "Idempotency-Key": f"demo-seed-ingest-{uuid.uuid4()}"},
        )
        ingest_resp.raise_for_status()
        print(ingest_resp.json())  # noqa: T201 -- this IS the script's output


if __name__ == "__main__":
    main()
