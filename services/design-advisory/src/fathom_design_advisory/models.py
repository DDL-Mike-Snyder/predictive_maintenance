"""SQLAlchemy 2.0 models for the Redesign Case Builder demo -- simplified
from docs/build/28-design-advisory.md §3, per
docs/demo/redesign-case-builder-demo-plan.md §1.3. SQLite only, single flat
namespace: no `schema=` kwarg anywhere (unlike services/pdm's real
Postgres/RLS-bearing tables)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class RedesignCandidate(Base):
    __tablename__ = "redesign_candidate"

    candidate_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    niin: Mapped[str] = mapped_column(String, nullable=False)
    nomenclature: Mapped[str] = mapped_column(String, nullable=False)
    equipment_family: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    driver_kinds: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    driver_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    pdm_criticality_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    affected_population: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_from: Mapped[str] = mapped_column(String, nullable=False)
    dossier_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("failure_dossier.dossier_id"), nullable=True
    )
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class FailureDossier(Base):
    __tablename__ = "failure_dossier"

    dossier_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("redesign_candidate.candidate_id"), nullable=False
    )
    niin: Mapped[str] = mapped_column(String, nullable=False)
    dossier_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    assembled_at: Mapped[str] = mapped_column(String, nullable=False)
    inputs_digest: Mapped[str] = mapped_column(String, nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String, nullable=False)
    affected_population: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    causal_citations: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    field_failure_count: Mapped[int] = mapped_column(Integer, nullable=False)
    test_coverage: Mapped[list[Any]] = mapped_column(JSON, nullable=False)


class ImpactSnapshot(Base):
    __tablename__ = "impact_snapshot"

    impact_snapshot_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("redesign_candidate.candidate_id"), nullable=False
    )
    computed_at: Mapped[str] = mapped_column(String, nullable=False)
    max_depth_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    edges_touched: Mapped[int] = mapped_column(Integer, nullable=False)
    edges_verified: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    nodes_expanded: Mapped[int] = mapped_column(Integer, nullable=False)
    nodes_truncated_at_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    artifact_leaves_reached: Mapped[int] = mapped_column(Integer, nullable=False)
    unverified_by_relation: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    unverified_by_source_kind: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_bounded_below: Mapped[bool] = mapped_column(Boolean, nullable=False)
    impacted_parts: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    impacted_artifacts: Mapped[list[Any]] = mapped_column(JSON, nullable=False)


class CostEstimate(Base):
    __tablename__ = "cost_estimate"

    estimate_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("redesign_candidate.candidate_id"), nullable=False
    )
    case_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("redesign_case.case_id"), nullable=True
    )
    method: Mapped[str] = mapped_column(String, nullable=False)
    cost_model_version: Mapped[str] = mapped_column(String, nullable=False, default="v0-demo")
    point_estimate_usd: Mapped[float] = mapped_column(Float, nullable=False)
    low_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    interval_basis: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    assumptions: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    impact_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    coverage_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_lower_bound: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class GateDecision(Base):
    __tablename__ = "gate_decision"

    gate_decision_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("redesign_candidate.candidate_id"), nullable=False
    )
    dossier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("failure_dossier.dossier_id"), nullable=False
    )
    impact_snapshot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("impact_snapshot.impact_snapshot_id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String, nullable=False)
    condition_results: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    failed_conditions: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    thresholds_in_force: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    gate_policy_version: Mapped[str] = mapped_column(
        String, nullable=False, default="v0-demo-placeholder"
    )
    computed_at: Mapped[str] = mapped_column(String, nullable=False)


class RedesignCase(Base):
    __tablename__ = "redesign_case"

    case_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("redesign_candidate.candidate_id"), nullable=False
    )
    niin: Mapped[str | None] = mapped_column(String, nullable=True)
    dossier_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("failure_dossier.dossier_id"), nullable=False
    )
    case_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    case_status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    scope_description: Mapped[str | None] = mapped_column(String, nullable=True)
    dependency_completeness: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    impact_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    test_coverage_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    cost_estimate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recommendation_stance: Mapped[str | None] = mapped_column(String, nullable=True)
    recommendation_basis_refs: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    recommendation_limitations: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    recommendation_evidence_gaps: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    # [demo addition] not a column in the real 28 schema -- the real
    # CaseDraftPackage is unpersisted (42-redesign-case-builder.md §1.3).
    # Persisted here purely so the UI has something to re-fetch.
    narrative_sections: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    assembled_at: Mapped[str | None] = mapped_column(String, nullable=True)
    proposal_id: Mapped[str | None] = mapped_column(String, nullable=True)
