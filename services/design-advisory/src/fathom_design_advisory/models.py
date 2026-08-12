"""SQLAlchemy 2.0 declarative models for the Redesign Case Builder demo
(plan §1.3, simplified from docs/build/28-design-advisory.md §3).

Conventions for this demo, per the plan:
  * SQLite always — **no `schema=` qualification** anywhere (one flat
    namespace), mirroring `platform/gateway/src/fathom_gateway/models.py`.
  * All ids are string UUIDs (`str(uuid.uuid4())`); all timestamps are
    ISO-8601 UTC *strings*, not `DateTime` columns.
  * Nested structures (lists/objects) are `JSON` columns, not child tables
    — the real spec normalizes several of these; this demo flattens them
    for speed and says so.
  * Id cross-references are documented as logical foreign keys in comments
    but declared as plain `String` columns with **no `ForeignKey`
    constraint**. This is deliberate: `redesign_candidate.dossier_id` and
    `failure_dossier.candidate_id` reference each other, so real FK
    constraints would create a circular dependency that deadlocks
    `create_all` / row insertion order. Nothing in this demo needs
    referential enforcement.
"""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# `JSON(none_as_null=True)` so a Python `None` bound to a nullable JSON
# column stores as SQL NULL rather than the JSON string "null" — the exact
# footgun the repo's own CLAUDE.md bug #14 records.
_NullableJson = JSON(none_as_null=True)


class RedesignCandidate(Base):
    """plan §1.3 `redesign_candidate`."""

    __tablename__ = "redesign_candidate"

    candidate_id: Mapped[str] = mapped_column(String, primary_key=True)
    niin: Mapped[str] = mapped_column(String, nullable=False)
    # demo-only convenience field (not in the real schema), harmless.
    nomenclature: Mapped[str] = mapped_column(String, nullable=False)
    equipment_family: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # candidate_status
    driver_kinds: Mapped[list] = mapped_column(JSON, nullable=False)  # list[str]
    driver_evidence: Mapped[dict] = mapped_column(JSON, nullable=False)  # object
    # [SIMPLIFIED] real spec (28 §3.5.2) is a Pythagorean vector magnitude;
    # demo uses a plain 0.0–1.0 score seeded directly.
    priority_score: Mapped[float] = mapped_column(Float, nullable=False)
    pdm_criticality_tier: Mapped[int] = mapped_column(Integer, nullable=False)  # 1–5
    affected_population: Mapped[dict] = mapped_column(JSON, nullable=False)  # {item_count, hull_count}
    created_from: Mapped[str] = mapped_column(String, nullable=False)
    # logical FK -> failure_dossier.dossier_id; set once a dossier assembled.
    dossier_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class FailureDossier(Base):
    """plan §1.3 `failure_dossier` (28 §3.3, flattened: citations /
    field-failures / test-coverage carried as JSON arrays on the row)."""

    __tablename__ = "failure_dossier"

    dossier_id: Mapped[str] = mapped_column(String, primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String, nullable=False)  # logical FK
    niin: Mapped[str] = mapped_column(String, nullable=False)
    dossier_version: Mapped[int] = mapped_column(Integer, nullable=False)  # always 1
    assembled_at: Mapped[str] = mapped_column(String, nullable=False)
    inputs_digest: Mapped[str] = mapped_column(String, nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String, nullable=False)
    affected_population: Mapped[dict] = mapped_column(JSON, nullable=False)
    causal_citations: Mapped[list] = mapped_column(JSON, nullable=False)  # list[object] (§1.3 shape)
    field_failure_count: Mapped[int] = mapped_column(Integer, nullable=False)
    test_coverage: Mapped[list] = mapped_column(JSON, nullable=False)  # list[object] (§1.3 shape)


class ImpactSnapshot(Base):
    """plan §1.3 `impact_snapshot` (28 §4.4 `dependency_completeness`
    shape — field names must match verbatim; every downstream artifact
    carries this object by reference)."""

    __tablename__ = "impact_snapshot"

    impact_snapshot_id: Mapped[str] = mapped_column(String, primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String, nullable=False)  # logical FK
    computed_at: Mapped[str] = mapped_column(String, nullable=False)
    max_depth_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    edges_touched: Mapped[int] = mapped_column(Integer, nullable=False)
    edges_verified: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    nodes_expanded: Mapped[int] = mapped_column(Integer, nullable=False)
    nodes_truncated_at_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    artifact_leaves_reached: Mapped[int] = mapped_column(Integer, nullable=False)
    unverified_by_relation: Mapped[dict] = mapped_column(JSON, nullable=False)
    unverified_by_source_kind: Mapped[dict] = mapped_column(JSON, nullable=False)
    # true whenever completeness_ratio < 1.0 OR nodes_truncated_at_depth > 0.
    is_bounded_below: Mapped[bool] = mapped_column(Boolean, nullable=False)
    impacted_parts: Mapped[list] = mapped_column(JSON, nullable=False)  # list[str] NIINs
    impacted_artifacts: Mapped[list] = mapped_column(JSON, nullable=False)  # list[str]


class CostEstimate(Base):
    """plan §1.3 `cost_estimate` (28 §3.7)."""

    __tablename__ = "cost_estimate"

    estimate_id: Mapped[str] = mapped_column(String, primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String, nullable=False)  # logical FK
    case_id: Mapped[str | None] = mapped_column(String, nullable=True)  # logical FK
    method: Mapped[str] = mapped_column(String, nullable=False)  # parametric | dependency_rollup
    cost_model_version: Mapped[str] = mapped_column(String, nullable=False)
    point_estimate_usd: Mapped[float] = mapped_column(Float, nullable=False)
    low_usd: Mapped[float | None] = mapped_column(Float, nullable=True)  # nullable together
    high_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    interval_basis: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0–1
    assumptions: Mapped[list] = mapped_column(JSON, nullable=False)  # list[str], non-empty
    impact_snapshot_id: Mapped[str | None] = mapped_column(String, nullable=True)  # required if rollup
    coverage_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)  # rollup only
    # 28 §3.7's load-bearing constraint: MUST equal coverage_ratio < 1.0
    # when method == 'dependency_rollup'.
    is_lower_bound: Mapped[bool] = mapped_column(Boolean, nullable=False)


class GateDecision(Base):
    """plan §1.3 `gate_decision` (28 §5.2/§5.3). Rows are WRITTEN by the
    action layer at demo time (not seeded); the model lives here because
    it belongs to the service's own schema."""

    __tablename__ = "gate_decision"

    gate_decision_id: Mapped[str] = mapped_column(String, primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String, nullable=False)  # logical FK
    dossier_id: Mapped[str] = mapped_column(String, nullable=False)  # logical FK
    impact_snapshot_id: Mapped[str] = mapped_column(String, nullable=False)  # logical FK
    decision: Mapped[str] = mapped_column(String, nullable=False)  # pass | fail
    condition_results: Mapped[dict] = mapped_column(JSON, nullable=False)  # {G1..G6: bool}
    failed_conditions: Mapped[list] = mapped_column(JSON, nullable=False)  # list[str]
    thresholds_in_force: Mapped[dict] = mapped_column(JSON, nullable=False)
    gate_policy_version: Mapped[str] = mapped_column(String, nullable=False)
    computed_at: Mapped[str] = mapped_column(String, nullable=False)


class RedesignCase(Base):
    """plan §1.3 `redesign_case` (28 §3.6). Rows are WRITTEN by the action
    layer at demo time; almost every column is null until assembled."""

    __tablename__ = "redesign_case"

    case_id: Mapped[str] = mapped_column(String, primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String, nullable=False)  # logical FK
    niin: Mapped[str | None] = mapped_column(String, nullable=True)  # null until assembled
    dossier_id: Mapped[str] = mapped_column(String, nullable=False)  # logical FK
    case_version: Mapped[int] = mapped_column(Integer, nullable=False)  # 1
    case_status: Mapped[str] = mapped_column(String, nullable=False)  # draft->assembled->proposed
    scope_description: Mapped[str | None] = mapped_column(String, nullable=True)
    dependency_completeness: Mapped[dict | None] = mapped_column(_NullableJson, nullable=True)
    impact_snapshot_id: Mapped[str | None] = mapped_column(String, nullable=True)
    test_coverage_summary: Mapped[dict | None] = mapped_column(_NullableJson, nullable=True)
    cost_estimate_id: Mapped[str | None] = mapped_column(String, nullable=True)
    recommendation_stance: Mapped[str | None] = mapped_column(String, nullable=True)
    recommendation_basis_refs: Mapped[list | None] = mapped_column(_NullableJson, nullable=True)
    # non-empty once assembled (28 §3.6 constraint).
    recommendation_limitations: Mapped[list | None] = mapped_column(_NullableJson, nullable=True)
    recommendation_evidence_gaps: Mapped[list | None] = mapped_column(_NullableJson, nullable=True)
    # [demo addition] not a column in the real 28 schema (the real
    # CaseDraftPackage is unpersisted, per 42 §1.3) — persisted here purely
    # so the UI can re-fetch it. list[{heading, body}].
    narrative_sections: Mapped[list | None] = mapped_column(_NullableJson, nullable=True)
    assembled_at: Mapped[str | None] = mapped_column(String, nullable=True)
    # demo: a random string once "proposed".
    proposal_id: Mapped[str | None] = mapped_column(String, nullable=True)
