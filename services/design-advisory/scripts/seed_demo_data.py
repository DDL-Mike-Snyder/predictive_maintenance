#!/usr/bin/env python
"""Seeds exactly the five candidates from
docs/demo/redesign-case-builder-demo-plan.md §1.5, each with its dossier
(citations + test_coverage), impact snapshot, and parametric cost_estimate.

Deliberately does NOT create gate_decision or redesign_case rows -- those
are written live by Marc's `evaluate-gate`/`redesign-cases`/`assemble`
endpoints when the demo actually runs the qualify/draft flow.

Idempotent: skips any candidate whose NIIN already exists. Safe to re-run.

    DESIGN_ADVISORY_DATABASE_URL=... python scripts/seed_demo_data.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fathom_design_advisory.config import Settings
from fathom_design_advisory.db import create_all, make_engine, make_session_maker
from fathom_design_advisory.models import (
    CostEstimate,
    FailureDossier,
    ImpactSnapshot,
    RedesignCandidate,
)
from sqlalchemy import select


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _citation(
    *,
    posture: str,
    strength_band: str,
    adjudication_state: str = "published",
    gate_verdict: str = "proceed",
    confounders_unaddressed: list[str] | None = None,
    band_limiting_axis: str = "confound_control",
    failure_mode_code: str = "FM-CORROSION-04",
    narrative_summary: str = "",
) -> dict[str, Any]:
    return {
        "citation_id": str(uuid.uuid4()),
        "posture": posture,
        "hypothesis_id": str(uuid.uuid4()),
        "adjudication_state": adjudication_state,
        "strength_band": strength_band,
        "band_limiting_axis": band_limiting_axis,
        "treatment_handling": "as_treated",
        "gate_verdict": gate_verdict,
        "confounders_unaddressed": confounders_unaddressed or [],
        "failure_mode_code": failure_mode_code,
        "narrative_summary": narrative_summary,
    }


def _test_coverage_row(
    *,
    test_kind_code: str,
    record_status: str,
    outcome: str | None = None,
    qualification_credit: bool = False,
    absence_basis: str | None = None,
) -> dict[str, Any]:
    return {
        "test_kind_code": test_kind_code,
        "record_status": record_status,
        "outcome": outcome,
        "qualification_credit": qualification_credit,
        "absence_basis": absence_basis,
    }


def _parametric_cost_estimate(candidate_id: str, point_estimate_usd: float) -> CostEstimate:
    return CostEstimate(
        estimate_id=str(uuid.uuid4()),
        candidate_id=candidate_id,
        case_id=None,
        method="parametric",
        cost_model_version="v0-demo",
        point_estimate_usd=point_estimate_usd,
        low_usd=round(point_estimate_usd * 0.65, 2),
        high_usd=round(point_estimate_usd * 1.35, 2),
        interval_basis="±35%, demo heuristic band",
        confidence=0.7,
        assumptions=[
            "Parametric estimate scaled from equipment-family historical cost data.",
            "Does not reflect a verified dependency-graph roll-up (see assemble step).",
        ],
        impact_snapshot_id=None,
        coverage_ratio=None,
        is_lower_bound=False,
    )


# Five candidates, exactly per §1.5. Each tuple:
# (niin, nomenclature, equipment_family, priority_score, pdm_criticality_tier,
#  completeness_ratio, field_failure_count, citations, test_coverage,
#  point_estimate_usd, impacted_parts, impacted_artifacts)
CANDIDATES: list[dict[str, Any]] = [
    {
        "niin": "013456789",
        "nomenclature": "Hydraulic Actuator, Primary Flight Control",
        "equipment_family": "flight-control-hydraulics",
        "priority_score": 0.82,
        "pdm_criticality_tier": 1,
        "completeness_ratio": 0.78,
        "field_failure_count": 14,
        "citations": [
            _citation(
                posture="supporting",
                strength_band="strong",
                narrative_summary=(
                    "Repeated seal extrusion under high-cycle loading, well-controlled "
                    "for duty-cycle confounds."
                ),
            )
        ],
        "test_coverage": [
            _test_coverage_row(
                test_kind_code="hydraulic-endurance-cycle",
                record_status="present",
                outcome="pass",
                qualification_credit=True,
            ),
            _test_coverage_row(
                test_kind_code="seal-material-compatibility",
                record_status="present",
                outcome="pass",
                qualification_credit=True,
            ),
            _test_coverage_row(
                test_kind_code="environmental-salt-fog",
                record_status="absent_not_performed",
                absence_basis="Legacy component, predates current qualification regime.",
            ),
        ],
        "point_estimate_usd": 1_450_000,
        "impacted_parts": ["014455001", "014455002"],
        "impacted_artifacts": ["TM-4410-15/2", "APL-991-04"],
    },
    {
        "niin": "013456790",
        "nomenclature": "Auxiliary Seawater Pump Impeller",
        "equipment_family": "seawater-cooling",
        "priority_score": 0.71,
        "pdm_criticality_tier": 2,
        "completeness_ratio": 0.42,
        "field_failure_count": 11,
        "citations": [
            _citation(
                posture="supporting",
                strength_band="moderate",
                confounders_unaddressed=["duty-cycle variation not controlled"],
                narrative_summary="Cavitation erosion linked to intermittent duty cycling.",
            )
        ],
        "test_coverage": [
            _test_coverage_row(
                test_kind_code="impeller-cavitation-erosion",
                record_status="present",
                outcome="pass",
                qualification_credit=True,
            ),
            _test_coverage_row(
                test_kind_code="environmental-salt-fog",
                record_status="absent_not_performed",
                absence_basis="Legacy component, predates current qualification regime.",
            ),
        ],
        "point_estimate_usd": 610_000,
        "impacted_parts": ["014455010"],
        "impacted_artifacts": ["TM-4410-22/1"],
    },
    {
        "niin": "013456791",
        "nomenclature": "Digital Multiplexer Card, Combat System",
        "equipment_family": "combat-system-electronics",
        "priority_score": 0.31,
        "pdm_criticality_tier": 3,
        "completeness_ratio": 0.75,
        "field_failure_count": 10,
        "citations": [
            _citation(
                posture="supporting",
                strength_band="strong",
                narrative_summary="Thermal-cycling induced solder-joint fatigue, well controlled.",
            )
        ],
        "test_coverage": [
            _test_coverage_row(
                test_kind_code="thermal-cycling",
                record_status="present",
                outcome="pass",
                qualification_credit=True,
            ),
            _test_coverage_row(
                test_kind_code="vibration-random",
                record_status="present",
                outcome="pass",
                qualification_credit=True,
            ),
        ],
        "point_estimate_usd": 900_000,
        "impacted_parts": ["014455020", "014455021", "014455022"],
        "impacted_artifacts": ["TM-9999-01/3"],
    },
    {
        "niin": "013456792",
        "nomenclature": "Shipboard HVAC Compressor Unit",
        "equipment_family": "hvac",
        "priority_score": 0.63,
        "pdm_criticality_tier": 2,
        "completeness_ratio": 0.71,
        "field_failure_count": 3,
        "citations": [
            _citation(
                posture="contra",
                strength_band="insufficient",
                adjudication_state="published",
                gate_verdict="refused",
                narrative_summary=(
                    "Proposed bearing-wear hypothesis was examined and rejected -- "
                    "failures traced to installation error, not a design defect."
                ),
            )
        ],
        "test_coverage": [
            _test_coverage_row(
                test_kind_code="compressor-endurance-run",
                record_status="present",
                outcome="pass",
                qualification_credit=True,
            ),
            _test_coverage_row(
                test_kind_code="environmental-salt-fog",
                record_status="absent_not_performed",
                absence_basis="Legacy component, predates current qualification regime.",
            ),
        ],
        "point_estimate_usd": 480_000,
        "impacted_parts": ["014455030"],
        "impacted_artifacts": ["TM-5900-04/1"],
    },
    {
        "niin": "013456793",
        "nomenclature": "Gas Turbine Module Bearing Assembly",
        "equipment_family": "gas-turbine",
        "priority_score": 0.61,
        "pdm_criticality_tier": 1,
        "completeness_ratio": 0.68,
        "field_failure_count": 9,
        "citations": [
            _citation(
                posture="supporting",
                strength_band="weak",
                confounders_unaddressed=[
                    "duty-cycle variation not controlled",
                    "maintenance-interval drift not controlled",
                ],
                narrative_summary=(
                    "Bearing spalling observed; causal link to design tolerance is "
                    "plausible but confounded by inconsistent maintenance intervals."
                ),
            )
        ],
        "test_coverage": [
            _test_coverage_row(
                test_kind_code="bearing-load-endurance",
                record_status="present",
                outcome="pass",
                qualification_credit=True,
            ),
            _test_coverage_row(
                test_kind_code="lubricant-degradation",
                record_status="present",
                outcome="pass",
                qualification_credit=True,
            ),
            _test_coverage_row(
                test_kind_code="environmental-salt-fog",
                record_status="absent_not_performed",
                absence_basis="Legacy component, predates current qualification regime.",
            ),
        ],
        "point_estimate_usd": 610_000,
        "impacted_parts": ["014455040", "014455041"],
        "impacted_artifacts": ["TM-2400-08/2", "APL-773-11"],
    },
]


async def seed() -> None:
    settings = Settings()
    engine = make_engine(settings.database_url)
    await create_all(engine)
    session_maker = make_session_maker(engine)

    async with session_maker() as session:
        for spec in CANDIDATES:
            existing = (
                await session.execute(
                    select(RedesignCandidate).where(RedesignCandidate.niin == spec["niin"])
                )
            ).scalars().first()
            if existing is not None:
                print(f"skip {spec['niin']} -- already seeded")  # noqa: T201
                continue

            candidate_id = str(uuid.uuid4())
            dossier_id = str(uuid.uuid4())

            dossier = FailureDossier(
                dossier_id=dossier_id,
                candidate_id=candidate_id,
                niin=spec["niin"],
                dossier_version=1,
                assembled_at=_now(),
                inputs_digest=uuid.uuid4().hex,
                taxonomy_version="v3-demo",
                affected_population={"item_count": 42, "hull_count": 6},
                causal_citations=spec["citations"],
                field_failure_count=spec["field_failure_count"],
                test_coverage=spec["test_coverage"],
            )
            session.add(dossier)

            candidate = RedesignCandidate(
                candidate_id=candidate_id,
                niin=spec["niin"],
                nomenclature=spec["nomenclature"],
                equipment_family=spec["equipment_family"],
                status="identified",
                driver_kinds=["causal_finding"],
                driver_evidence={"summary": spec["citations"][0]["narrative_summary"]},
                priority_score=spec["priority_score"],
                pdm_criticality_tier=spec["pdm_criticality_tier"],
                affected_population={"item_count": 42, "hull_count": 6},
                created_from="causal_finding",
                dossier_id=dossier_id,
                created_at=_now(),
            )
            session.add(candidate)
            # Autoflush ordering across plain FK columns (no ORM
            # relationship()) isn't guaranteed -- flush explicitly between
            # sibling adds, same fix as CLAUDE.md bug #15.
            await session.flush()

            completeness_ratio = spec["completeness_ratio"]
            impact_snapshot = ImpactSnapshot(
                impact_snapshot_id=str(uuid.uuid4()),
                candidate_id=candidate_id,
                computed_at=_now(),
                max_depth_requested=3,
                edges_touched=120,
                edges_verified=round(120 * completeness_ratio),
                completeness_ratio=completeness_ratio,
                nodes_expanded=64,
                nodes_truncated_at_depth=0 if completeness_ratio >= 1.0 else 5,
                artifact_leaves_reached=len(spec["impacted_artifacts"]),
                unverified_by_relation={"interfaces_with": 4, "supports": 9},
                unverified_by_source_kind={"inferred_cooccurrence": 11},
                is_bounded_below=completeness_ratio < 1.0,
                impacted_parts=spec["impacted_parts"],
                impacted_artifacts=spec["impacted_artifacts"],
            )
            session.add(impact_snapshot)

            cost_estimate = _parametric_cost_estimate(candidate_id, spec["point_estimate_usd"])
            session.add(cost_estimate)

            await session.commit()
            print(f"seeded {spec['niin']} -- {spec['nomenclature']} ({candidate_id})")  # noqa: T201

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
