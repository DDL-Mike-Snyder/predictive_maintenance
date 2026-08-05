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
stdlib so it runs in that environment with no install step at all.

[PLACEHOLDER -- out of scope, see 22-pdm.md §5.1 and this service's own
HANDOFF.md "What's NOT built yet for PdM"] The two-parameter Weibull MLE /
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
`POST /scoring-runs` (22-pdm.md §10, line ~1356) is a declared but
not-yet-implemented PdM endpoint, so this script takes an existing
--scoring-run-id rather than minting one -- the orchestration that creates
and schedules scoring runs is Domino Flow/Job-scheduling infrastructure,
out of scope for the same reason the fit above is.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
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
    status, body = post_predictions(
        args.base_url,
        args.scoring_run_id,
        predictions,
        idempotency_key=f"{execution_ref}:{args.scoring_run_id}",
        principal=f"domino-job:{execution_ref}",
    )
    # A Domino Job's stdout is its log -- this print IS the deliverable,
    # not debug noise a linter tuned for services/packages should flag.
    print(json.dumps({"status": status, "domino_execution_ref": execution_ref, "body": body}))  # noqa: T201
    _http_ok_ceiling = 300
    return 0 if status < _http_ok_ceiling else 1


if __name__ == "__main__":
    sys.exit(main())
