#!/usr/bin/env python3
"""Domino Job entrypoint for tier-0 fleet scoring. docs/build/22-pdm.md
§5.1/§5.4: "All tiers write through PdM's bulk ingest API... A Domino Job
holds a workload identity and is an API client, never a database client"
(also 09-monorepo-and-conventions.md §9.1 item 1) -- this script is exactly
that. It reads the population this run scores from --input-file, computes
the tier-0 contract's shape, and POSTs the result to PdM's bulk-ingest
endpoint. It never imports fathom_pdm and never touches PdM's database: a
Domino Job's own compute environment is provisioned independently of this
monorepo's package graph, and this script depends on nothing beyond the
stdlib for its CORE deliverable (the HTTP round trip), so that deliverable
still runs with no install step even in a minimal environment.

[PLACEHOLDER -- out of scope, see 22-pdm.md §5.1 and this service's own
CLAUDE.md "What's NOT built yet for PdM"] The two-parameter Weibull MLE /
IPCW-weighted fit tier 0's method actually specifies is NOT implemented
here -- it needs real per-(equipment_family, niin) telemetry and
failure-label infrastructure this vertical slice does not build.
`_score_population` below computes a structurally-valid stand-in instead
(every item published as the one shape a fit-free stand-in can honestly
claim -- see its own docstring) so the wiring this script exists to prove
-- real Domino execution context in, a real HTTP round trip to PdM's own
API out -- can be built and exercised for real without pretending the
statistics behind it are real too.

Also NOT built here, same reason: creating the scoring_run itself.
`POST /scoring-runs` (22-pdm.md §10, line ~1356) is a declared, now
IMPLEMENTED PdM endpoint (services/pdm/src/fathom_pdm/api/v1/
scoring_runs.py) that mints a `queued` row an operator or an orchestrator
must still call explicitly -- this script continues to take an existing
--scoring-run-id rather than minting one itself, since the orchestration
that decides WHEN to create and schedule a real scoring run is Domino
Flow/Job-scheduling infrastructure, out of scope for the same reason the
fit above is.

**MLflow/Experiment Manager + Model Registry integration, added once a
real Domino workspace was reachable to verify it against.** `mlflow` is
NOT a stdlib import, but it is pre-installed in every real Domino compute
environment specifically for this integration (confirmed live: `import
mlflow` succeeds and `MLFLOW_TRACKING_URI` is auto-injected, no install
step) -- a different category from a third-party statistics library this
script would have to vendor itself. It is still wrapped best-effort
(`_log_to_experiment_manager`): a tracking-server hiccup must never break
this script's actual deliverable, the bulk-ingest HTTP round trip, so a
logging failure is caught, printed as a warning, and the run proceeds.
Registers the one artifact a fit-free stand-in can honestly describe as a
"model" -- the constant `population_hazard_rate` and the run's own
metadata -- under `registered_model_name`, never a real Weibull fit this
script does not compute.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone


def domino_execution_ref() -> str:
    """Every Domino Job/Workspace gets `DOMINO_RUN_ID` injected
    automatically by the platform -- no config needed, unlike
    `--base-url`/`PDM_API_BASE_URL` below, which is this script's own
    target and something Domino has no reason to know about."""
    return os.environ.get("DOMINO_RUN_ID", "unknown-run")


def score_population(
    items: list[dict], *, scoring_run_id: str, horizon_days: int, model_version: str
) -> list[dict]:
    """[PLACEHOLDER] see module docstring. Every item is published as
    `reference_class='class_estimate'`, `p_failure=None`,
    `population_hazard_rate` present, `rul=None` -- 22-pdm.md §5.5's own
    last row, and the one shape a fit-free stand-in can honestly emit: a
    population rate, not a confident per-item distribution it never fit."""
    # `timezone.utc`, not the `datetime.UTC` alias a linter targeting this
    # repo's services/packages (Python 3.12+) would suggest: a Domino Job's
    # own compute environment is provisioned independently of that, and IS
    # older here in practice -- `datetime.UTC` (3.11+) crashed this script
    # the first time it was actually run inside the real workspace
    # (Python 3.10). `timezone.utc` has worked since Python 3.2.
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"  # noqa: UP017
    predictions = []
    for item in items:
        predictions.append(
            {
                "asset_id": item["asset_id"],
                "installed_item_id": item["installed_item_id"],
                "position_id": item["position_id"],
                "niin": item["niin"],
                "equipment_family": item["equipment_family"],
                "baseline_id": item["baseline_id"],
                "baseline_epoch": item["baseline_epoch"],
                "horizon_days": horizon_days,
                "p_failure": None,
                "reference_class": "class_estimate",
                "sharpness": 0.0,
                "calibration_population": item.get("calibration_population"),
                "rul": None,
                "population_hazard_rate": item.get("population_hazard_rate", 0.0001),
                "confidence": 0.2,
                "fallback_level": 4,
                "tier": 0,
                "contributing_factors": [],
                "model_version": model_version,
                "scoring_run_id": scoring_run_id,
                "computed_at": now,
            }
        )
    return predictions


def post_predictions(
    base_url: str,
    scoring_run_id: str,
    predictions: list[dict],
    *,
    idempotency_key: str,
    principal: str,
    timeout: float = 45.0,
) -> tuple[int, dict]:
    """§11.3: bulk ingest is idempotent and baseline-epoch fenced -- the
    `Idempotency-Key` here is derived from this Job's own execution ref, so
    a re-run of the SAME Domino run against the SAME scoring run replays
    rather than double-writes."""
    url = f"{base_url}/api/v1/pdm/scoring-runs/{scoring_run_id}/predictions"
    body = json.dumps({"predictions": predictions}).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310 -- base_url is operator-supplied config, not user input
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
            # [PLACEHOLDER] stands in for a real OIDC workload-identity
            # bearer token (31-auth.md) -- packages/py-common/authz.py's own
            # `current_principal` is the same documented placeholder on the
            # receiving side, for this same vertical slice.
            "X-Fathom-Principal": principal,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def log_to_experiment_manager(
    *,
    scoring_run_id: str,
    horizon_days: int,
    model_version: str,
    predictions: list[dict],
    execution_ref: str,
    registered_model_name: str = "fathom-pdm-tier0-historical",
) -> dict[str, object]:
    """Best-effort. Logs this run's params/metrics to Domino's Experiment
    Manager and registers the one artifact a fit-free stand-in can
    honestly describe as a model -- see this module's own docstring for
    why a tracking failure here must never fail the run. Returns {} on
    any failure, including `mlflow` being unavailable at all."""
    try:
        # Deliberately deferred; see module docstring.
        import mlflow  # noqa: PLC0415
        from mlflow.exceptions import MlflowException  # noqa: PLC0415
        from mlflow.tracking import MlflowClient  # noqa: PLC0415
    except ImportError as exc:
        print(  # noqa: T201 -- this script's own log line, see module docstring
            json.dumps(
                {"warning": "mlflow unavailable, skipping experiment tracking", "detail": str(exc)}
            )
        )
        return {}

    try:
        username = os.environ.get("DOMINO_STARTING_USERNAME", "unknown")
        project = os.environ.get("DOMINO_PROJECT_NAME", "predictive_maintenance")
        mlflow.set_experiment(f"{project}-tier0-historical-{username}")

        hazard_rates = [
            p["population_hazard_rate"]
            for p in predictions
            if p["population_hazard_rate"] is not None
        ]
        mean_hazard_rate = statistics.fmean(hazard_rates) if hazard_rates else 0.0

        with mlflow.start_run(run_name=f"tier0-{scoring_run_id}") as run:
            mlflow.log_params(
                {
                    "scoring_run_id": scoring_run_id,
                    "horizon_days": horizon_days,
                    "model_version": model_version,
                    "domino_execution_ref": execution_ref,
                    # 22-pdm.md §5.1's real Weibull MLE/IPCW fit is NOT
                    # implemented -- see this module's own docstring.
                    "method": "fit_free_population_stand_in",
                }
            )
            mlflow.log_metrics(
                {
                    "items_scored": len(predictions),
                    "population_hazard_rate_mean": mean_hazard_rate,
                }
            )

            with tempfile.TemporaryDirectory() as tmpdir:
                artifact_path = os.path.join(tmpdir, "tier0_stand_in.json")  # noqa: PTH118
                with open(artifact_path, "w") as fh:  # noqa: PTH123
                    json.dump(
                        {
                            "method": "fit_free_population_stand_in",
                            "note": (
                                "NOT a real Weibull MLE/IPCW fit -- see 22-pdm.md §5.1 "
                                "and this script's own module docstring."
                            ),
                            "population_hazard_rate_mean": mean_hazard_rate,
                            "items_scored": len(predictions),
                        },
                        fh,
                        indent=2,
                    )
                mlflow.log_artifact(artifact_path, artifact_path="model")

            run_id = run.info.run_id
            # [CORRECTION -- found running this against the real Domino
            # workspace for the first time.] `mlflow.register_model()`
            # rejects a plain `log_artifact()`-logged path in MLflow 3.x --
            # it now requires a proper "logged model" entity (created by
            # the `log_model()` family), which this stand-in artifact
            # deliberately isn't (it's a JSON note, not a framework model).
            # The lower-level `MlflowClient` calls below have no such
            # requirement; `create_registered_model` needs the "already
            # exists" case handled explicitly since (unlike
            # `register_model`) it does not create-or-get.
            client = MlflowClient()
            try:
                client.create_registered_model(registered_model_name)
            except MlflowException as exc:
                if "RESOURCE_ALREADY_EXISTS" not in str(exc):
                    raise
            version = client.create_model_version(
                name=registered_model_name,
                source=f"runs:/{run_id}/model",
                run_id=run_id,
            )
    except Exception as exc:  # noqa: BLE001 -- observability must never break the core deliverable
        print(json.dumps({"warning": "experiment tracking failed", "detail": str(exc)}))  # noqa: T201
        return {}
    else:
        return {
            "experiment_run_id": run_id,
            "registered_model_name": registered_model_name,
            "registered_model_version": version.version,
            "registered_model_uri": f"models:/{registered_model_name}/{version.version}",
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scoring-run-id", required=True)
    parser.add_argument("--input-file", required=True, help="JSON list of items to score")
    parser.add_argument("--horizon-days", type=int, default=90)
    parser.add_argument(
        "--base-url", default=os.environ.get("PDM_API_BASE_URL", "http://localhost:8000")
    )
    parser.add_argument("--model-version", default="tier0-historical-placeholder-0.1.0")
    args = parser.parse_args(argv)

    with open(args.input_file) as fh:  # noqa: PTH123
        items = json.load(fh)

    predictions = score_population(
        items,
        scoring_run_id=args.scoring_run_id,
        horizon_days=args.horizon_days,
        model_version=args.model_version,
    )

    execution_ref = domino_execution_ref()

    experiment_result = log_to_experiment_manager(
        scoring_run_id=args.scoring_run_id,
        horizon_days=args.horizon_days,
        model_version=args.model_version,
        predictions=predictions,
        execution_ref=execution_ref,
    )

    status, body = post_predictions(
        args.base_url,
        args.scoring_run_id,
        predictions,
        idempotency_key=f"{execution_ref}:{args.scoring_run_id}",
        principal=f"domino-job:{execution_ref}",
    )
    # A Domino Job's stdout is its log -- this print IS the deliverable,
    # not debug noise a linter tuned for services/packages should flag.
    print(  # noqa: T201
        json.dumps(
            {
                "status": status,
                "domino_execution_ref": execution_ref,
                "body": body,
                "experiment_manager": experiment_result,
            }
        )
    )
    _http_ok_ceiling = 300
    return 0 if status < _http_ok_ceiling else 1


if __name__ == "__main__":
    sys.exit(main())
