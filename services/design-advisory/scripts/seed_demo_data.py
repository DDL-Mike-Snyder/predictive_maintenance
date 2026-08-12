"""Seed exactly the five demo candidates from plan §1.5, each with its
failure dossier (citations + test coverage), impact snapshot, and its
*parametric* cost estimate.

Run standalone:  python scripts/seed_demo_data.py
Idempotent: skips any candidate whose NIIN already exists, so it is safe to
re-run while debugging.

Deliberately does NOT create gate_decision or redesign_case rows — those
are written live by the action / agent endpoints when the demo runs the
qualify / draft flow (plan §Paul task 7).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
import pathlib
import sys
import uuid

# Make the package importable when run as `python scripts/seed_demo_data.py`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from fathom_design_advisory.config import Settings  # noqa: E402
from fathom_design_advisory.db import (  # noqa: E402
    build_engine,
    build_sessionmaker,
    create_all,
)
from fathom_design_advisory.models import (  # noqa: E402
    CostEstimate,
    FailureDossier,
    ImpactSnapshot,
    RedesignCandidate,
)


def _now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


def _present(test_kind: str) -> dict:
    return {
        "test_kind_code": test_kind,
        "record_status": "present",
        "outcome": "pass",
        "qualification_credit": True,
        "absence_basis": None,
    }


def _absent(test_kind: str, basis: str) -> dict:
    return {
        "test_kind_code": test_kind,
        "record_status": "absent_not_performed",
        "outcome": None,
        "qualification_credit": False,
        "absence_basis": basis,
    }


def _supporting_citation(
    strength_band: str, failure_mode_code: str, summary: str, confounders: list[str] | None = None
) -> dict:
    return {
        "citation_id": _uid(),
        "posture": "supporting",
        "hypothesis_id": _uid(),
        "adjudication_state": "published",
        "strength_band": strength_band,
        "band_limiting_axis": "confound_control" if confounders else "none",
        "treatment_handling": "as_treated",
        "gate_verdict": "proceed",
        "confounders_unaddressed": confounders or [],
        "failure_mode_code": failure_mode_code,
        "narrative_summary": summary,
    }


def _contra_citation(failure_mode_code: str, summary: str) -> dict:
    return {
        "citation_id": _uid(),
        "posture": "contra",
        "hypothesis_id": _uid(),
        "adjudication_state": "published",
        "strength_band": "moderate",
        "band_limiting_axis": "none",
        "treatment_handling": "as_treated",
        "gate_verdict": "proceed",
        "confounders_unaddressed": [],
        "failure_mode_code": failure_mode_code,
        "narrative_summary": summary,
    }


# --- The five candidates, plan §1.5 -----------------------------------------
# Each spec captures the fields that drive the gate story; the rest are
# plausible, consistent fillers. `completeness_ratio` is authoritative
# (the edges_* numbers are illustrative and merely consistent with it).
CANDIDATES: list[dict] = [
    {
        # #1 — clean happy path, PASS all G1–G6.
        "niin": "013456789",
        "nomenclature": "Hydraulic Actuator, Primary Flight Control",
        "equipment_family": "flight-control-hydraulics",
        "priority_score": 0.82,
        "pdm_criticality_tier": 5,
        "affected_population": {"item_count": 46, "hull_count": 12},
        "completeness_ratio": 0.78,
        "field_failure_count": 14,
        "point_estimate_usd": 1_450_000.0,
        "citations": [
            _supporting_citation(
                "strong",
                "FM-SEAL-EXTRUSION-02",
                "Adjudicated causal link between elevated return-line pressure "
                "and primary seal extrusion; treatment effect stable across hulls.",
            )
        ],
        "test_coverage": [
            _present("environmental-vibration"),
            _absent(
                "environmental-salt-fog",
                "Legacy component, predates current qualification regime.",
            ),
        ],
        "impacted_parts": ["014111222", "014333444"],
        "impacted_artifacts": ["TM-4410-15/2", "APL-991-04"],
    },
    {
        # #2 — FAIL G3 only (dependency completeness below floor).
        "niin": "013456790",
        "nomenclature": "Auxiliary Seawater Pump Impeller",
        "equipment_family": "seawater-systems",
        "priority_score": 0.71,
        "pdm_criticality_tier": 4,
        "affected_population": {"item_count": 88, "hull_count": 20},
        "completeness_ratio": 0.42,
        "field_failure_count": 11,
        "point_estimate_usd": 610_000.0,
        "citations": [
            _supporting_citation(
                "moderate",
                "FM-CAVITATION-07",
                "Cavitation-driven blade erosion linked to off-design flow; "
                "moderate strength of evidence.",
            )
        ],
        "test_coverage": [
            _present("hydrostatic-pressure"),
            _absent(
                "erosion-endurance",
                "Test rig unavailable at the responsible activity; not performed.",
            ),
        ],
        "impacted_parts": ["014555666", "014777888"],
        "impacted_artifacts": ["TM-4320-10/1", "APL-772-11"],
    },
    {
        # #3 — FAIL G2 only (priority below floor).
        "niin": "013456791",
        "nomenclature": "Digital Multiplexer Card, Combat System",
        "equipment_family": "combat-system-electronics",
        "priority_score": 0.31,
        "pdm_criticality_tier": 2,
        "affected_population": {"item_count": 210, "hull_count": 31},
        "completeness_ratio": 0.75,
        "field_failure_count": 10,
        "point_estimate_usd": 900_000.0,
        "citations": [
            _supporting_citation(
                "strong",
                "FM-SOLDER-FATIGUE-01",
                "Thermal-cycling solder-joint fatigue well established; strong "
                "evidence, but the affected population is peripheral to mission risk.",
            )
        ],
        "test_coverage": [
            _present("thermal-cycling"),
            _present("emi-susceptibility"),
            _absent(
                "extended-burn-in",
                "Superseded by supplier acceptance testing; not separately performed.",
            ),
        ],
        "impacted_parts": ["014999000", "015111222"],
        "impacted_artifacts": ["TM-4110-22/3", "APL-334-02"],
    },
    {
        # #4 — FAIL G5 only (no evidentiary floor: contra citation only).
        "niin": "013456792",
        "nomenclature": "Shipboard HVAC Compressor Unit",
        "equipment_family": "hvac-refrigeration",
        "priority_score": 0.63,
        "pdm_criticality_tier": 3,
        "affected_population": {"item_count": 54, "hull_count": 18},
        "completeness_ratio": 0.71,
        "field_failure_count": 3,
        "point_estimate_usd": 480_000.0,
        "citations": [
            _contra_citation(
                "FM-COMPRESSOR-SEIZE-05",
                "Hypothesized refrigerant-contamination cause was examined and "
                "adjudicated CONTRA — it does not explain the observed failures.",
            )
        ],
        "test_coverage": [
            _present("refrigerant-charge"),
            _absent(
                "vibration-endurance",
                "Deferred pending redesign decision; not performed.",
            ),
        ],
        "impacted_parts": ["015333444", "015555666"],
        "impacted_artifacts": ["TM-4530-08/1", "APL-118-09"],
    },
    {
        # #5 — PASS all G1–G6, but evidence is weak/confounded.
        "niin": "013456793",
        "nomenclature": "Gas Turbine Module Bearing Assembly",
        "equipment_family": "propulsion-gas-turbine",
        "priority_score": 0.61,
        "pdm_criticality_tier": 4,
        "affected_population": {"item_count": 24, "hull_count": 9},
        "completeness_ratio": 0.68,
        "field_failure_count": 9,
        "point_estimate_usd": 610_000.0,
        "citations": [
            _supporting_citation(
                "weak",
                "FM-BEARING-SPALL-03",
                "Suggestive association between start-cycle count and bearing "
                "spalling, but confounded; weak strength band.",
                confounders=[
                    "duty-cycle variation not controlled",
                    "lube-oil lot not tracked across the sample",
                ],
            )
        ],
        "test_coverage": [
            _present("bearing-endurance"),
            _absent(
                "lube-oil-analysis",
                "Historical oil samples not retained; analysis could not be performed.",
            ),
        ],
        "impacted_parts": ["015777888", "015999000"],
        "impacted_artifacts": ["TM-4210-14/2", "APL-556-07"],
    },
]


def _build_impact_snapshot(candidate_id: str, spec: dict) -> ImpactSnapshot:
    r = spec["completeness_ratio"]
    edges_touched = 60
    edges_verified = round(edges_touched * r)
    nodes_truncated = 0 if r >= 1.0 else max(1, round((1.0 - r) * 8))
    return ImpactSnapshot(
        impact_snapshot_id=_uid(),
        candidate_id=candidate_id,
        computed_at=_now(),
        max_depth_requested=4,
        edges_touched=edges_touched,
        edges_verified=edges_verified,
        completeness_ratio=r,
        nodes_expanded=round(edges_touched * 0.7),
        nodes_truncated_at_depth=nodes_truncated,
        artifact_leaves_reached=len(spec["impacted_artifacts"]),
        unverified_by_relation={"interfaces_with": edges_touched - edges_verified - 5, "supports": 5},
        unverified_by_source_kind={"inferred_cooccurrence": edges_touched - edges_verified},
        # true whenever completeness_ratio < 1.0 OR nodes_truncated_at_depth > 0.
        is_bounded_below=(r < 1.0) or (nodes_truncated > 0),
        impacted_parts=spec["impacted_parts"],
        impacted_artifacts=spec["impacted_artifacts"],
    )


async def _seed_one(session: AsyncSession, spec: dict) -> bool:
    existing = (
        await session.execute(
            select(RedesignCandidate).where(RedesignCandidate.niin == spec["niin"])
        )
    ).scalar_one_or_none()
    if existing is not None:
        return False  # idempotent skip

    candidate_id = _uid()
    dossier_id = _uid()

    dossier = FailureDossier(
        dossier_id=dossier_id,
        candidate_id=candidate_id,
        niin=spec["niin"],
        dossier_version=1,
        assembled_at=_now(),
        inputs_digest=uuid.uuid4().hex,  # demo-only, never verified
        taxonomy_version="v3-demo",
        affected_population=spec["affected_population"],
        causal_citations=spec["citations"],
        field_failure_count=spec["field_failure_count"],
        test_coverage=spec["test_coverage"],
    )
    snapshot = _build_impact_snapshot(candidate_id, spec)
    point = spec["point_estimate_usd"]
    cost = CostEstimate(
        estimate_id=_uid(),
        candidate_id=candidate_id,
        case_id=None,
        method="parametric",
        cost_model_version="v0-demo",
        point_estimate_usd=point,
        low_usd=round(point * 0.65, 2),
        high_usd=round(point * 1.35, 2),
        interval_basis="±35%, demo heuristic band",
        confidence=0.6,
        assumptions=[
            "Parametric model v0-demo keyed on component class and criticality tier.",
            "Excludes integration, re-qualification, and installation labor.",
        ],
        impact_snapshot_id=None,  # parametric: not derived from the graph
        coverage_ratio=None,
        is_lower_bound=False,
    )
    candidate = RedesignCandidate(
        candidate_id=candidate_id,
        niin=spec["niin"],
        nomenclature=spec["nomenclature"],
        equipment_family=spec["equipment_family"],
        status="identified",
        driver_kinds=["causal_finding"],
        driver_evidence={"summary": f"Causal finding raised {spec['nomenclature']} for review."},
        priority_score=spec["priority_score"],
        pdm_criticality_tier=spec["pdm_criticality_tier"],
        affected_population=spec["affected_population"],
        created_from="causal_finding",
        dossier_id=dossier_id,  # linked at seed time
        created_at=_now(),
    )

    session.add_all([dossier, snapshot, cost, candidate])
    return True


async def main() -> None:
    settings = Settings()
    engine = build_engine(settings)
    await create_all(engine)
    session_maker = build_sessionmaker(engine)

    seeded = 0
    async with session_maker() as session:
        for spec in CANDIDATES:
            if await _seed_one(session, spec):
                seeded += 1
        await session.commit()
    await engine.dispose()

    # Log the RESOLVED absolute file path, not just the URL string — a
    # relative sqlite path resolves against CWD, so the server and this
    # seed can silently target two different files if started from
    # different directories (review finding N2).
    db_display = settings.database_url
    if settings.database_url.startswith("sqlite"):
        file_part = settings.database_url.split(":///")[-1]
        db_display = f"{settings.database_url}  (resolved file: {os.path.abspath(file_part)})"
    print(f"Seed complete: {seeded} new candidate(s) inserted, "  # noqa: T201
          f"{len(CANDIDATES) - seeded} already present. DB: {db_display}")


if __name__ == "__main__":
    asyncio.run(main())
