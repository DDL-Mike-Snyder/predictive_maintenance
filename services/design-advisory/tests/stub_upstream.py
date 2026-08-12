"""Michael's own test double for Paul's `api/reads.py` + Marc's
`api/actions.py` (`docs/demo/redesign-case-builder-demo-plan.md`,
"Michael" section: *"You do not need Paul's or Marc's code to start.
Build against a tiny local stub server that returns the exact JSON
shapes from §1.3/§1.5... so you can develop and test your orchestration
logic in isolation."*).

**This file is NOT part of the real design-advisory service and is not
one of Michael's owned files** (`api/agent.py`, `agent/derive.py`,
`agent/narrative.py`) -- it exists purely so `test_agent_e2e.py` can
verify `api/agent.py`'s orchestration logic against something real and
running, per this codebase's own established discipline (`CLAUDE.md`:
"assume every 'done' is wrong until you personally verify it"). Delete
this whole `tests/` directory once Paul's and Marc's real
`reads.py`/`actions.py` exist and swap in for real integration testing --
this is scaffolding, not a second implementation to keep in sync.

Implements exactly the five seeded candidates from §1.5, in memory (no
SQLite -- a real DB round-trip is Paul's own thing to verify, not
Michael's), plus real G1-G6 gate logic (§1.4) and real
assemble/create-case/propose logic (Marc's spec, §"Marc" tasks 2-5) --
close enough to the real contract that a pass against this stub is real
signal about `api/agent.py`'s own logic, not just a smoke test of syntax.

Also implements the three list-by-`candidate_id` filters `api/agent.py`'s
own module docstring documents as an assumption about Paul's real
`reads.py` (impact-snapshots, cost-estimates, gate-decisions) -- if
Paul's real service doesn't grow these, `api/agent.py` needs them added
there, not removed here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="design-advisory-stub (Michael's test double, not real Paul/Marc code)")

GATE_COST_FLOOR_USD = 250_000
GATE_PRIORITY_FLOOR = 0.55
GATE_COMPLETENESS_FLOOR = 0.60
GATE_FIELD_FAILURE_FLOOR = 8

# In-memory tables, keyed by id -- reset on process restart, which is the
# whole point: a fresh, deterministic stub per test run.
CANDIDATES: dict[str, dict] = {}
DOSSIERS: dict[str, dict] = {}
IMPACT_SNAPSHOTS: dict[str, dict] = {}
COST_ESTIMATES: dict[str, dict] = {}
GATE_DECISIONS: dict[str, dict] = {}
CASES: dict[str, dict] = {}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _seed() -> None:
    """Exactly §1.5's five candidates."""
    rows = [
        {
            "niin": "013456789",
            "nomenclature": "Hydraulic Actuator, Primary Flight Control",
            "priority_score": 0.82,
            "completeness_ratio": 0.78,
            "field_failure_count": 14,
            "citations": [
                {
                    "posture": "supporting",
                    "strength_band": "strong",
                    "adjudication_state": "published",
                    "confounders_unaddressed": [],
                    "failure_mode_code": "FM-ACTUATOR-01",
                    "narrative_summary": (
                        "Repeated seal extrusion under duty-cycle load, strongly supported."
                    ),
                }
            ],
            "point_estimate_usd": 1_450_000,
        },
        {
            "niin": "013456790",
            "nomenclature": "Auxiliary Seawater Pump Impeller",
            "priority_score": 0.71,
            "completeness_ratio": 0.42,
            "field_failure_count": 11,
            "citations": [
                {
                    "posture": "supporting",
                    "strength_band": "moderate",
                    "adjudication_state": "published",
                    "confounders_unaddressed": ["duty-cycle variation not controlled"],
                    "failure_mode_code": "FM-IMPELLER-02",
                    "narrative_summary": "Cavitation-driven erosion, moderately supported.",
                }
            ],
            "point_estimate_usd": 610_000,
        },
        {
            "niin": "013456791",
            "nomenclature": "Digital Multiplexer Card, Combat System",
            "priority_score": 0.31,
            "completeness_ratio": 0.75,
            "field_failure_count": 10,
            "citations": [
                {
                    "posture": "supporting",
                    "strength_band": "strong",
                    "adjudication_state": "published",
                    "confounders_unaddressed": [],
                    "failure_mode_code": "FM-MUX-03",
                    "narrative_summary": (
                        "Thermal-cycling solder-joint fatigue, strongly supported."
                    ),
                }
            ],
            "point_estimate_usd": 900_000,
        },
        {
            "niin": "013456792",
            "nomenclature": "Shipboard HVAC Compressor Unit",
            "priority_score": 0.63,
            "completeness_ratio": 0.71,
            "field_failure_count": 3,
            "citations": [
                {
                    "posture": "contra",
                    "strength_band": "moderate",
                    "adjudication_state": "published",
                    "confounders_unaddressed": [],
                    "failure_mode_code": "FM-HVAC-04",
                    "narrative_summary": (
                        "Proposed refrigerant-charge hypothesis, rejected on review."
                    ),
                }
            ],
            "point_estimate_usd": 480_000,
        },
        {
            "niin": "013456793",
            "nomenclature": "Gas Turbine Module Bearing Assembly",
            "priority_score": 0.61,
            "completeness_ratio": 0.68,
            "field_failure_count": 9,
            "citations": [
                {
                    "posture": "supporting",
                    "strength_band": "weak",
                    "adjudication_state": "published",
                    "confounders_unaddressed": [
                        "ambient temperature not logged",
                        "maintenance interval not controlled",
                    ],
                    "failure_mode_code": "FM-BEARING-05",
                    "narrative_summary": "Spalling on inner race, weakly supported and confounded.",
                }
            ],
            "point_estimate_usd": 610_000,
        },
    ]

    for row in rows:
        candidate_id = str(uuid.uuid4())
        dossier_id = str(uuid.uuid4())
        impact_snapshot_id = str(uuid.uuid4())
        estimate_id = str(uuid.uuid4())

        citations = [
            {
                "citation_id": str(uuid.uuid4()),
                "posture": c["posture"],
                "hypothesis_id": str(uuid.uuid4()),
                "adjudication_state": c["adjudication_state"],
                "strength_band": c["strength_band"],
                "band_limiting_axis": "confound_control",
                "treatment_handling": "as_treated",
                "gate_verdict": "proceed",
                "confounders_unaddressed": c["confounders_unaddressed"],
                "failure_mode_code": c["failure_mode_code"],
                "narrative_summary": c["narrative_summary"],
            }
            for c in row["citations"]
        ]
        test_coverage = [
            {
                "test_kind_code": "vibration-endurance",
                "record_status": "present",
                "outcome": "pass",
                "qualification_credit": True,
                "absence_basis": None,
            },
            {
                "test_kind_code": "environmental-salt-fog",
                "record_status": "absent_not_performed",
                "outcome": None,
                "qualification_credit": False,
                "absence_basis": "Legacy component, predates current qualification regime.",
            },
        ]

        CANDIDATES[candidate_id] = {
            "candidate_id": candidate_id,
            "niin": row["niin"],
            "nomenclature": row["nomenclature"],
            "equipment_family": "demo-family",
            "status": "identified",
            "driver_kinds": ["causal_finding"],
            "driver_evidence": {"summary": "Seeded for the RCB demo."},
            "priority_score": row["priority_score"],
            "pdm_criticality_tier": 2,
            "affected_population": {"item_count": 40, "hull_count": 6},
            "created_from": "causal_finding",
            "dossier_id": dossier_id,
            "created_at": _now(),
        }
        DOSSIERS[dossier_id] = {
            "dossier_id": dossier_id,
            "candidate_id": candidate_id,
            "niin": row["niin"],
            "dossier_version": 1,
            "assembled_at": _now(),
            "inputs_digest": uuid.uuid4().hex,
            "taxonomy_version": "v3-demo",
            "affected_population": {"item_count": 40, "hull_count": 6},
            "causal_citations": citations,
            "field_failure_count": row["field_failure_count"],
            "test_coverage": test_coverage,
        }
        IMPACT_SNAPSHOTS[impact_snapshot_id] = {
            "impact_snapshot_id": impact_snapshot_id,
            "candidate_id": candidate_id,
            "computed_at": _now(),
            "max_depth_requested": 3,
            "edges_touched": 20,
            "edges_verified": int(20 * row["completeness_ratio"]),
            "completeness_ratio": row["completeness_ratio"],
            "nodes_expanded": 15,
            "nodes_truncated_at_depth": 0 if row["completeness_ratio"] >= 1.0 else 2,
            "artifact_leaves_reached": 4,
            "unverified_by_relation": {"interfaces_with": 4, "supports": 9},
            "unverified_by_source_kind": {"inferred_cooccurrence": 11},
            "is_bounded_below": row["completeness_ratio"] < 1.0,
            "impacted_parts": ["013456700", "013456701"],
            "impacted_artifacts": ["TM-4410-15/2", "APL-991-04"],
        }
        COST_ESTIMATES[estimate_id] = {
            "estimate_id": estimate_id,
            "candidate_id": candidate_id,
            "case_id": None,
            "method": "parametric",
            "cost_model_version": "v0-demo",
            "point_estimate_usd": float(row["point_estimate_usd"]),
            "low_usd": float(row["point_estimate_usd"]) * 0.65,
            "high_usd": float(row["point_estimate_usd"]) * 1.35,
            "interval_basis": "±35%, demo heuristic band",
            "confidence": 0.6,
            "assumptions": ["Parametric model, no dependency-graph rollup yet."],
            "impact_snapshot_id": None,
            "coverage_ratio": None,
            "is_lower_bound": False,
        }


_seed()


# --------------------------------------------------------------------- #
# Paul's reads.py, stood in for
# --------------------------------------------------------------------- #


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@app.get("/api/v1/design-advisory/redesign-candidates")
async def list_candidates(status: str | None = None) -> list[dict]:
    rows = list(CANDIDATES.values())
    if status:
        rows = [r for r in rows if r["status"] == status]
    return rows


@app.get("/api/v1/design-advisory/redesign-candidates/{candidate_id}")
async def get_candidate(candidate_id: str) -> dict:
    row = CANDIDATES.get(candidate_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no such candidate: {candidate_id}")
    return row


@app.get("/api/v1/design-advisory/dossiers/{dossier_id}")
async def get_dossier(dossier_id: str) -> dict:
    row = DOSSIERS.get(dossier_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no such dossier: {dossier_id}")
    return row


@app.get("/api/v1/design-advisory/impact-snapshots/{impact_snapshot_id}")
async def get_impact_snapshot(impact_snapshot_id: str) -> dict:
    row = IMPACT_SNAPSHOTS.get(impact_snapshot_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"no such impact snapshot: {impact_snapshot_id}"
        )
    return row


@app.get("/api/v1/design-advisory/impact-snapshots")
async def list_impact_snapshots(candidate_id: str = Query(...)) -> list[dict]:
    """[ASSUMPTION endpoint] -- see `api/agent.py`'s module docstring."""
    return [r for r in IMPACT_SNAPSHOTS.values() if r["candidate_id"] == candidate_id]


@app.get("/api/v1/design-advisory/cost-estimates/{estimate_id}")
async def get_cost_estimate(estimate_id: str) -> dict:
    row = COST_ESTIMATES.get(estimate_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no such cost estimate: {estimate_id}")
    return row


@app.get("/api/v1/design-advisory/cost-estimates")
async def list_cost_estimates(
    candidate_id: str = Query(...), method: str | None = None
) -> list[dict]:
    """[ASSUMPTION endpoint] -- see `api/agent.py`'s module docstring."""
    rows = [r for r in COST_ESTIMATES.values() if r["candidate_id"] == candidate_id]
    if method:
        rows = [r for r in rows if r["method"] == method]
    return rows


@app.get("/api/v1/design-advisory/gate-decisions")
async def list_gate_decisions(candidate_id: str = Query(...)) -> list[dict]:
    """[ASSUMPTION endpoint] -- see `api/agent.py`'s module docstring."""
    return [r for r in GATE_DECISIONS.values() if r["candidate_id"] == candidate_id]


@app.get("/api/v1/design-advisory/redesign-cases")
async def list_cases(candidate_id: str | None = None) -> list[dict]:
    rows = list(CASES.values())
    if candidate_id:
        rows = [r for r in rows if r["candidate_id"] == candidate_id]
    return rows


@app.get("/api/v1/design-advisory/redesign-cases/{case_id}")
async def get_case(case_id: str) -> dict:
    row = CASES.get(case_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"no such case: {case_id}")
    return row


# --------------------------------------------------------------------- #
# Marc's actions.py, stood in for
# --------------------------------------------------------------------- #


@app.post("/api/v1/design-advisory/redesign-candidates/{candidate_id}/parametric-estimate")
async def parametric_estimate(candidate_id: str) -> dict:
    for row in COST_ESTIMATES.values():
        if row["candidate_id"] == candidate_id and row["method"] == "parametric":
            return row
    raise HTTPException(status_code=404, detail=f"no parametric estimate seeded for {candidate_id}")


@app.post("/api/v1/design-advisory/redesign-candidates/{candidate_id}/evaluate-gate")
async def evaluate_gate(candidate_id: str) -> dict:
    candidate = CANDIDATES.get(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"no such candidate: {candidate_id}")
    dossier = DOSSIERS[candidate["dossier_id"]]
    snapshot = next(r for r in IMPACT_SNAPSHOTS.values() if r["candidate_id"] == candidate_id)
    estimate = next(
        r
        for r in COST_ESTIMATES.values()
        if r["candidate_id"] == candidate_id and r["method"] == "parametric"
    )

    g1 = estimate["point_estimate_usd"] >= GATE_COST_FLOOR_USD
    g2 = candidate["priority_score"] >= GATE_PRIORITY_FLOOR
    g3 = snapshot["completeness_ratio"] >= GATE_COMPLETENESS_FLOOR
    g4 = all(row["record_status"] != "absent_unknown" for row in dossier["test_coverage"])
    g5 = dossier["field_failure_count"] >= GATE_FIELD_FAILURE_FLOOR or any(
        c["posture"] == "supporting" and c["adjudication_state"] == "published"
        for c in dossier["causal_citations"]
    )
    g6 = candidate["status"] in {"identified", "qualifying", "gate_passed", "gate_failed"}

    condition_results = {
        "G1_cost_floor": g1,
        "G2_priority_floor": g2,
        "G3_completeness_floor": g3,
        "G4_test_coverage_assessed": g4,
        "G5_evidentiary_floor": g5,
        "G6_state_consistency": g6,
    }
    decision = "pass" if all(condition_results.values()) else "fail"
    failed_conditions = [k for k, v in condition_results.items() if not v]

    gate_decision_id = str(uuid.uuid4())
    row = {
        "gate_decision_id": gate_decision_id,
        "candidate_id": candidate_id,
        "dossier_id": dossier["dossier_id"],
        "impact_snapshot_id": snapshot["impact_snapshot_id"],
        "decision": decision,
        "condition_results": condition_results,
        "failed_conditions": failed_conditions,
        "thresholds_in_force": {
            "GATE_COST_FLOOR_USD": GATE_COST_FLOOR_USD,
            "GATE_PRIORITY_FLOOR": GATE_PRIORITY_FLOOR,
            "GATE_COMPLETENESS_FLOOR": GATE_COMPLETENESS_FLOOR,
            "GATE_FIELD_FAILURE_FLOOR": GATE_FIELD_FAILURE_FLOOR,
        },
        "gate_policy_version": "v0-demo-placeholder",
        "computed_at": _now(),
    }
    GATE_DECISIONS[gate_decision_id] = row
    candidate["status"] = "gate_passed" if decision == "pass" else "gate_failed"
    return row


class CreateCaseRequest(BaseModel):
    candidate_id: str


@app.post("/api/v1/design-advisory/redesign-cases")
async def create_case(body: CreateCaseRequest) -> dict:
    candidate = CANDIDATES.get(body.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail=f"no such candidate: {body.candidate_id}")
    existing = [
        r
        for r in CASES.values()
        if r["candidate_id"] == body.candidate_id and r["case_status"] != "withdrawn"
    ]
    if existing:
        raise HTTPException(
            status_code=409, detail=f"an active case already exists for {body.candidate_id}"
        )

    case_id = str(uuid.uuid4())
    row = {
        "case_id": case_id,
        "candidate_id": body.candidate_id,
        "niin": None,
        "dossier_id": candidate["dossier_id"],
        "case_version": 1,
        "case_status": "draft",
        "scope_description": None,
        "dependency_completeness": None,
        "impact_snapshot_id": None,
        "test_coverage_summary": None,
        "cost_estimate_id": None,
        "recommendation_stance": None,
        "recommendation_basis_refs": None,
        "recommendation_limitations": None,
        "recommendation_evidence_gaps": None,
        "narrative_sections": None,
        "assembled_at": None,
        "proposal_id": None,
    }
    CASES[case_id] = row
    return row


class AssembleRequest(BaseModel):
    recommendation_stance: str
    recommendation_limitations: list[str]
    recommendation_evidence_gaps: list[str]
    narrative_sections: list[dict]


@app.post("/api/v1/design-advisory/redesign-cases/{case_id}/assemble")
async def assemble_case(case_id: str, body: AssembleRequest) -> dict:
    case = CASES.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"no such case: {case_id}")
    candidate_id = case["candidate_id"]
    candidate = CANDIDATES[candidate_id]
    dossier = DOSSIERS[case["dossier_id"]]
    snapshot = next(r for r in IMPACT_SNAPSHOTS.values() if r["candidate_id"] == candidate_id)
    parametric = next(
        r
        for r in COST_ESTIMATES.values()
        if r["candidate_id"] == candidate_id and r["method"] == "parametric"
    )
    latest_gate = max(
        (r for r in GATE_DECISIONS.values() if r["candidate_id"] == candidate_id),
        key=lambda r: r["computed_at"],
        default=None,
    )
    if latest_gate is None or latest_gate["decision"] != "pass":
        raise HTTPException(
            status_code=409, detail=f"gate has not passed for candidate {candidate_id}"
        )

    coverage_ratio = snapshot["completeness_ratio"]
    rollup_id = str(uuid.uuid4())
    rollup = {
        "estimate_id": rollup_id,
        "candidate_id": candidate_id,
        "case_id": case_id,
        "method": "dependency_rollup",
        "cost_model_version": "v0-demo",
        "point_estimate_usd": parametric["point_estimate_usd"] * 1.4,
        "low_usd": None,
        "high_usd": None,
        "interval_basis": None,
        "confidence": None,
        "assumptions": [
            "Dependency roll-up scales the parametric estimate by 1.4x, demo heuristic."
        ],
        "impact_snapshot_id": snapshot["impact_snapshot_id"],
        "coverage_ratio": coverage_ratio,
        "is_lower_bound": coverage_ratio < 1.0,
    }
    COST_ESTIMATES[rollup_id] = rollup

    by_record_status: dict[str, int] = {}
    for row in dossier["test_coverage"]:
        by_record_status[row["record_status"]] = by_record_status.get(row["record_status"], 0) + 1

    case.update(
        {
            "niin": candidate["niin"],
            "scope_description": f"Redesign evaluation for {candidate['niin']}",
            "dependency_completeness": dict(snapshot),
            "impact_snapshot_id": snapshot["impact_snapshot_id"],
            "test_coverage_summary": {
                "by_record_status": by_record_status,
                "absent_unknown_count": by_record_status.get("absent_unknown", 0),
            },
            "cost_estimate_id": rollup_id,
            "recommendation_stance": body.recommendation_stance,
            "recommendation_basis_refs": [c["citation_id"] for c in dossier["causal_citations"]],
            "recommendation_limitations": body.recommendation_limitations,
            "recommendation_evidence_gaps": body.recommendation_evidence_gaps,
            "narrative_sections": body.narrative_sections,
            "case_status": "assembled",
            "assembled_at": _now(),
        }
    )
    return case


@app.post("/api/v1/design-advisory/redesign-cases/{case_id}/propose")
async def propose_case(case_id: str) -> dict:
    case = CASES.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"no such case: {case_id}")
    case["case_status"] = "proposed"
    case["proposal_id"] = str(uuid.uuid4())
    return case
