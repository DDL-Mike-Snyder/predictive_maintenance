// Hand-written fixtures matching docs/demo/redesign-case-builder-demo-plan.md
// §1.3 (data shapes) and §1.5 (the five seed candidates and their exact
// gate outcomes). Built before any of Paul/Marc/Michael's services exist,
// per this file's own instruction ("You do not need Paul/Marc/Michael's
// services running to build this"). Field names are copied verbatim from
// §1.3/§1.5/§1.2 so that swapping api.ts's bodies for real fetch calls at
// integration doesn't require touching this file or the component at all.
//
// [SCOPE] IDs here are readable demo slugs ("cand-1", not a real UUID) --
// harmless, since nothing in this feature parses or assumes UUID format;
// the real backend will hand back real `str(uuid.uuid4())` values and
// nothing here cares.

// ---- §1.2 vocabularies ----
export type CandidateStatus =
  | "identified"
  | "qualifying"
  | "gate_passed"
  | "gate_failed"
  | "case_drafted"
  | "withdrawn";
export type CaseStatus = "draft" | "assembled" | "proposed" | "published" | "superseded" | "withdrawn";
export type RecommendationStance =
  | "redesign_warranted_for_evaluation"
  | "insufficient_evidence"
  | "monitor_and_reassess"
  | "no_action_indicated";
export type CostMethod = "parametric" | "dependency_rollup";
export type CitationPosture = "supporting" | "contra";
export type TestRecordStatus =
  | "present"
  | "present_unparsed"
  | "absent_not_performed"
  | "absent_not_located"
  | "absent_not_required"
  | "absent_unknown";
export type GateVerdict = "proceed" | "proceed_corrected" | "restricted" | "refused";
export type StrengthBand = "strong" | "moderate" | "weak" | "insufficient";

// §1.4 -- must match services/design-advisory's config.py defaults exactly.
export const GATE_THRESHOLDS = {
  costFloorUsd: 250_000,
  priorityFloor: 0.55,
  completenessFloor: 0.6,
  fieldFailureFloor: 8,
};

export const CONDITION_ORDER = [
  "G1_cost_floor",
  "G2_priority_floor",
  "G3_completeness_floor",
  "G4_test_coverage_assessed",
  "G5_evidentiary_floor",
  "G6_state_consistency",
] as const;

export const CONDITION_LABELS: Record<string, string> = {
  G1_cost_floor: "Cost floor",
  G2_priority_floor: "Priority floor",
  G3_completeness_floor: "Dependency completeness floor",
  G4_test_coverage_assessed: "Test coverage assessed",
  G5_evidentiary_floor: "Evidentiary floor",
  G6_state_consistency: "Candidate state consistency",
};

export const STANCE_LABELS: Record<RecommendationStance, string> = {
  redesign_warranted_for_evaluation: "Redesign warranted for evaluation",
  insufficient_evidence: "Insufficient evidence",
  monitor_and_reassess: "Monitor and reassess",
  no_action_indicated: "No action indicated",
};

// ---- §1.3 data model ----
export interface RedesignCandidate {
  candidate_id: string;
  niin: string;
  nomenclature: string;
  equipment_family: string;
  status: CandidateStatus;
  driver_kinds: string[];
  driver_evidence: { summary: string };
  priority_score: number;
  pdm_criticality_tier: number;
  affected_population: { item_count: number; hull_count: number };
  created_from: string;
  dossier_id: string | null;
  created_at: string;
}

export interface CausalCitation {
  citation_id: string;
  posture: CitationPosture;
  hypothesis_id: string;
  adjudication_state: string;
  strength_band: StrengthBand;
  band_limiting_axis: string;
  treatment_handling: string;
  gate_verdict: GateVerdict;
  confounders_unaddressed: string[];
  failure_mode_code: string;
  narrative_summary: string;
}

export interface TestCoverageRow {
  test_kind_code: string;
  record_status: TestRecordStatus;
  outcome: string | null;
  qualification_credit: boolean;
  absence_basis: string | null;
}

export interface FailureDossier {
  dossier_id: string;
  candidate_id: string;
  niin: string;
  dossier_version: number;
  assembled_at: string;
  inputs_digest: string;
  taxonomy_version: string;
  affected_population: { item_count: number; hull_count: number };
  causal_citations: CausalCitation[];
  field_failure_count: number;
  test_coverage: TestCoverageRow[];
}

export interface ImpactSnapshot {
  impact_snapshot_id: string;
  candidate_id: string;
  computed_at: string;
  max_depth_requested: number;
  edges_touched: number;
  edges_verified: number;
  completeness_ratio: number;
  nodes_expanded: number;
  nodes_truncated_at_depth: number;
  artifact_leaves_reached: number;
  unverified_by_relation: Record<string, number>;
  unverified_by_source_kind: Record<string, number>;
  is_bounded_below: boolean;
  impacted_parts: string[];
  impacted_artifacts: string[];
}

export interface CostEstimate {
  estimate_id: string;
  candidate_id: string;
  case_id: string | null;
  method: CostMethod;
  cost_model_version: string;
  point_estimate_usd: number;
  low_usd: number | null;
  high_usd: number | null;
  interval_basis: string | null;
  confidence: number | null;
  assumptions: string[];
  impact_snapshot_id: string | null;
  coverage_ratio: number | null;
  is_lower_bound: boolean;
}

export interface GateDecision {
  gate_decision_id: string;
  candidate_id: string;
  dossier_id: string;
  impact_snapshot_id: string;
  decision: "pass" | "fail";
  condition_results: Record<string, boolean>;
  failed_conditions: string[];
  thresholds_in_force: typeof GATE_THRESHOLDS;
  gate_policy_version: string;
  computed_at: string;
}

// 42-redesign-case-builder.md §3.2.1, trimmed to what this slice actually
// carries (see Michael's section of the demo plan for the exact trim).
export interface QualificationReport {
  run_id: string;
  candidate_id: string;
  niin: string;
  dossier_id: string;
  impact_snapshot_id: string;
  dependency_completeness: ImpactSnapshot;
  parametric_estimate: CostEstimate;
  gate_decision_id: string;
  gate_decision: "pass" | "fail";
  condition_results: Record<string, boolean>;
  failed_conditions: string[];
  causal_citation_refs: CausalCitation[];
  derived_evidence_gaps: string[];
  outcome: "gate_pass" | "gate_fail";
}

// The assembled `redesign_case` row Michael's `draft` endpoint returns
// (28 §3.6), fully populated -- only ever produced for a gate-passing
// candidate.
export interface CaseDraftPackage {
  case_id: string;
  candidate_id: string;
  niin: string;
  dossier_id: string;
  case_version: number;
  case_status: CaseStatus;
  scope_description: string;
  dependency_completeness: ImpactSnapshot;
  impact_snapshot_id: string;
  test_coverage_summary: { by_record_status: Record<string, number>; absent_unknown_count: number };
  cost_estimate_id: string;
  cost_estimate: CostEstimate;
  recommendation_stance: RecommendationStance;
  recommendation_basis_refs: string[];
  recommendation_limitations: string[];
  recommendation_evidence_gaps: string[];
  narrative_sections: { heading: string; body: string }[];
  assembled_at: string;
  proposal_id: string | null;
}

// ---- §1.5 seed candidates ----

const CITATION_1: CausalCitation = {
  citation_id: "citation-1",
  posture: "supporting",
  hypothesis_id: "hyp-1",
  adjudication_state: "published",
  strength_band: "strong",
  band_limiting_axis: "none",
  treatment_handling: "as_treated",
  gate_verdict: "proceed",
  confounders_unaddressed: [],
  failure_mode_code: "FM-FATIGUE-02",
  narrative_summary:
    "Repeated field failures of the primary actuator's control valve correlate strongly with duty-cycle-adjusted flight hours, with confound controls for hull class and maintenance interval.",
};

const CITATION_2: CausalCitation = {
  citation_id: "citation-2",
  posture: "supporting",
  hypothesis_id: "hyp-2",
  adjudication_state: "published",
  strength_band: "moderate",
  band_limiting_axis: "confound_control",
  treatment_handling: "as_treated",
  gate_verdict: "proceed",
  confounders_unaddressed: ["duty-cycle variation not controlled"],
  failure_mode_code: "FM-CORROSION-04",
  narrative_summary:
    "Impeller pitting correlates with seawater intake temperature; duty-cycle variation across the fleet was not fully controlled for.",
};

const CITATION_3: CausalCitation = {
  citation_id: "citation-3",
  posture: "supporting",
  hypothesis_id: "hyp-3",
  adjudication_state: "published",
  strength_band: "strong",
  band_limiting_axis: "none",
  treatment_handling: "as_treated",
  gate_verdict: "proceed",
  confounders_unaddressed: [],
  failure_mode_code: "FM-THERMAL-11",
  narrative_summary:
    "Multiplexer card failures show a strong, well-controlled association with sustained thermal cycling in the combat system's equipment bay.",
};

const CITATION_4: CausalCitation = {
  citation_id: "citation-4",
  posture: "contra",
  hypothesis_id: "hyp-4",
  adjudication_state: "published",
  strength_band: "insufficient",
  band_limiting_axis: "sample_size",
  treatment_handling: "intention_to_treat",
  gate_verdict: "restricted",
  confounders_unaddressed: ["compressor duty cycle not logged consistently across the sample"],
  failure_mode_code: "FM-VIBRATION-07",
  narrative_summary:
    "The hypothesized link between compressor vibration and bearing wear did not survive adjudication; the contra finding indicates no reliable association at current sample sizes.",
};

const CITATION_5: CausalCitation = {
  citation_id: "citation-5",
  posture: "supporting",
  hypothesis_id: "hyp-5",
  adjudication_state: "published",
  strength_band: "weak",
  band_limiting_axis: "confound_control",
  treatment_handling: "as_treated",
  gate_verdict: "proceed_corrected",
  confounders_unaddressed: [
    "duty-cycle variation not controlled",
    "sample spans two bearing-assembly design revisions without separation",
  ],
  failure_mode_code: "FM-BEARING-09",
  narrative_summary:
    "Bearing-assembly wear correlates with turbine run-hours, but the association is weak and confounded by an unaddressed design-revision mix in the sample.",
};

export const CANDIDATES: RedesignCandidate[] = [
  {
    candidate_id: "cand-1",
    niin: "013456789",
    nomenclature: "Hydraulic Actuator, Primary Flight Control",
    equipment_family: "flight-control-hydraulics",
    status: "identified",
    driver_kinds: ["causal_finding"],
    driver_evidence: { summary: "Strong, published causal citation plus 14 recorded field failures." },
    priority_score: 0.82,
    pdm_criticality_tier: 1,
    affected_population: { item_count: 214, hull_count: 18 },
    created_from: "causal_finding",
    dossier_id: "dossier-1",
    created_at: "2026-08-01T09:00:00Z",
  },
  {
    candidate_id: "cand-2",
    niin: "013456790",
    nomenclature: "Auxiliary Seawater Pump Impeller",
    equipment_family: "auxiliary-seawater-systems",
    status: "identified",
    driver_kinds: ["causal_finding"],
    driver_evidence: { summary: "Moderate, published causal citation; dependency graph under-verified." },
    priority_score: 0.71,
    pdm_criticality_tier: 2,
    affected_population: { item_count: 96, hull_count: 12 },
    created_from: "causal_finding",
    dossier_id: "dossier-2",
    created_at: "2026-08-01T09:05:00Z",
  },
  {
    candidate_id: "cand-3",
    niin: "013456791",
    nomenclature: "Digital Multiplexer Card, Combat System",
    equipment_family: "combat-system-electronics",
    status: "identified",
    driver_kinds: ["causal_finding"],
    driver_evidence: { summary: "Strong, published causal citation; little depends on this NIIN." },
    priority_score: 0.31,
    pdm_criticality_tier: 3,
    affected_population: { item_count: 58, hull_count: 9 },
    created_from: "causal_finding",
    dossier_id: "dossier-3",
    created_at: "2026-08-01T09:10:00Z",
  },
  {
    candidate_id: "cand-4",
    niin: "013456792",
    nomenclature: "Shipboard HVAC Compressor Unit",
    equipment_family: "hvac-systems",
    status: "identified",
    driver_kinds: ["causal_finding"],
    driver_evidence: { summary: "Only causal finding on file for this NIIN is contra (rejected hypothesis)." },
    priority_score: 0.63,
    pdm_criticality_tier: 3,
    affected_population: { item_count: 140, hull_count: 22 },
    created_from: "causal_finding",
    dossier_id: "dossier-4",
    created_at: "2026-08-01T09:15:00Z",
  },
  {
    candidate_id: "cand-5",
    niin: "013456793",
    nomenclature: "Gas Turbine Module Bearing Assembly",
    equipment_family: "gas-turbine-modules",
    status: "identified",
    driver_kinds: ["causal_finding"],
    driver_evidence: { summary: "Weak, confounded published causal citation; 9 recorded field failures." },
    priority_score: 0.61,
    pdm_criticality_tier: 2,
    affected_population: { item_count: 132, hull_count: 14 },
    created_from: "causal_finding",
    dossier_id: "dossier-5",
    created_at: "2026-08-01T09:20:00Z",
  },
];

const DOSSIERS: Record<string, FailureDossier> = {
  "cand-1": {
    dossier_id: "dossier-1",
    candidate_id: "cand-1",
    niin: "013456789",
    dossier_version: 1,
    assembled_at: "2026-08-01T10:00:00Z",
    inputs_digest: "a1b2c3d4e5f60718",
    taxonomy_version: "v3-demo",
    affected_population: { item_count: 214, hull_count: 18 },
    causal_citations: [CITATION_1],
    field_failure_count: 14,
    test_coverage: [
      {
        test_kind_code: "vibration-endurance",
        record_status: "present",
        outcome: "pass",
        qualification_credit: true,
        absence_basis: null,
      },
      {
        test_kind_code: "environmental-salt-fog",
        record_status: "absent_not_performed",
        outcome: null,
        qualification_credit: false,
        absence_basis: "Legacy component, predates current qualification regime.",
      },
      {
        test_kind_code: "hydraulic-pressure-cycling",
        record_status: "present",
        outcome: "pass",
        qualification_credit: true,
        absence_basis: null,
      },
    ],
  },
  "cand-2": {
    dossier_id: "dossier-2",
    candidate_id: "cand-2",
    niin: "013456790",
    dossier_version: 1,
    assembled_at: "2026-08-01T10:05:00Z",
    inputs_digest: "b2c3d4e5f6071829",
    taxonomy_version: "v3-demo",
    affected_population: { item_count: 96, hull_count: 12 },
    causal_citations: [CITATION_2],
    field_failure_count: 11,
    test_coverage: [
      {
        test_kind_code: "seawater-immersion",
        record_status: "present",
        outcome: "pass",
        qualification_credit: true,
        absence_basis: null,
      },
      {
        test_kind_code: "cavitation-resistance",
        record_status: "absent_not_performed",
        outcome: null,
        qualification_credit: false,
        absence_basis: "Test kind added to the qualification catalog after this impeller's original acceptance.",
      },
    ],
  },
  "cand-3": {
    dossier_id: "dossier-3",
    candidate_id: "cand-3",
    niin: "013456791",
    dossier_version: 1,
    assembled_at: "2026-08-01T10:10:00Z",
    inputs_digest: "c3d4e5f607182930",
    taxonomy_version: "v3-demo",
    affected_population: { item_count: 58, hull_count: 9 },
    causal_citations: [CITATION_3],
    field_failure_count: 10,
    test_coverage: [
      {
        test_kind_code: "thermal-cycling",
        record_status: "present",
        outcome: "pass",
        qualification_credit: true,
        absence_basis: null,
      },
      {
        test_kind_code: "emi-emc",
        record_status: "present",
        outcome: "pass",
        qualification_credit: true,
        absence_basis: null,
      },
      {
        test_kind_code: "shock-half-sine",
        record_status: "absent_not_required",
        outcome: null,
        qualification_credit: false,
        absence_basis:
          "Card is not in a shock-critical mounting location per the combat system's own qualification plan.",
      },
    ],
  },
  "cand-4": {
    dossier_id: "dossier-4",
    candidate_id: "cand-4",
    niin: "013456792",
    dossier_version: 1,
    assembled_at: "2026-08-01T10:15:00Z",
    inputs_digest: "d4e5f60718293041",
    taxonomy_version: "v3-demo",
    affected_population: { item_count: 140, hull_count: 22 },
    causal_citations: [CITATION_4],
    field_failure_count: 3,
    test_coverage: [
      {
        test_kind_code: "vibration-endurance",
        record_status: "present",
        outcome: "fail",
        qualification_credit: false,
        absence_basis: null,
      },
      {
        test_kind_code: "bearing-life-accelerated",
        record_status: "absent_not_performed",
        outcome: null,
        qualification_credit: false,
        absence_basis: "Scheduled for next qualification cycle; not yet performed.",
      },
    ],
  },
  "cand-5": {
    dossier_id: "dossier-5",
    candidate_id: "cand-5",
    niin: "013456793",
    dossier_version: 1,
    assembled_at: "2026-08-01T10:20:00Z",
    inputs_digest: "e5f6071829304152",
    taxonomy_version: "v3-demo",
    affected_population: { item_count: 132, hull_count: 14 },
    causal_citations: [CITATION_5],
    field_failure_count: 9,
    test_coverage: [
      {
        test_kind_code: "bearing-life-accelerated",
        record_status: "present_unparsed",
        outcome: null,
        qualification_credit: false,
        absence_basis: null,
      },
      {
        test_kind_code: "lubricant-contamination",
        record_status: "present",
        outcome: "pass",
        qualification_credit: true,
        absence_basis: null,
      },
      {
        test_kind_code: "overspeed",
        record_status: "absent_not_performed",
        outcome: null,
        qualification_credit: false,
        absence_basis: "Requires a dedicated test rig not currently available at the qualifying activity.",
      },
    ],
  },
};

const SNAPSHOTS: Record<string, ImpactSnapshot> = {
  "cand-1": {
    impact_snapshot_id: "snapshot-1",
    candidate_id: "cand-1",
    computed_at: "2026-08-01T10:30:00Z",
    max_depth_requested: 3,
    edges_touched: 132,
    edges_verified: 103,
    completeness_ratio: 0.78,
    nodes_expanded: 58,
    nodes_truncated_at_depth: 2,
    artifact_leaves_reached: 37,
    unverified_by_relation: { interfaces_with: 4, supports: 9, requires: 16 },
    unverified_by_source_kind: { inferred_cooccurrence: 11, manual_annotation: 18 },
    is_bounded_below: true,
    impacted_parts: ["013456650", "013456701", "013456622"],
    impacted_artifacts: ["TM-4410-15/2", "APL-991-04", "DWG-2201-C"],
  },
  "cand-2": {
    impact_snapshot_id: "snapshot-2",
    candidate_id: "cand-2",
    computed_at: "2026-08-01T10:35:00Z",
    max_depth_requested: 3,
    edges_touched: 140,
    edges_verified: 59,
    completeness_ratio: 0.42,
    nodes_expanded: 71,
    nodes_truncated_at_depth: 9,
    artifact_leaves_reached: 22,
    unverified_by_relation: { interfaces_with: 14, supports: 31, requires: 36 },
    unverified_by_source_kind: { inferred_cooccurrence: 52, manual_annotation: 29 },
    is_bounded_below: true,
    impacted_parts: ["013456611", "013456777"],
    impacted_artifacts: ["TM-4510-08/1", "APL-772-19"],
  },
  "cand-3": {
    impact_snapshot_id: "snapshot-3",
    candidate_id: "cand-3",
    computed_at: "2026-08-01T10:40:00Z",
    max_depth_requested: 3,
    edges_touched: 96,
    edges_verified: 72,
    completeness_ratio: 0.75,
    nodes_expanded: 44,
    nodes_truncated_at_depth: 1,
    artifact_leaves_reached: 29,
    unverified_by_relation: { interfaces_with: 6, supports: 5, requires: 13 },
    unverified_by_source_kind: { inferred_cooccurrence: 16, manual_annotation: 8 },
    is_bounded_below: true,
    impacted_parts: ["013456845"],
    impacted_artifacts: ["TM-6630-22/4"],
  },
  "cand-4": {
    impact_snapshot_id: "snapshot-4",
    candidate_id: "cand-4",
    computed_at: "2026-08-01T10:45:00Z",
    max_depth_requested: 3,
    edges_touched: 88,
    edges_verified: 63,
    completeness_ratio: 0.71,
    nodes_expanded: 39,
    nodes_truncated_at_depth: 2,
    artifact_leaves_reached: 24,
    unverified_by_relation: { interfaces_with: 8, supports: 10, requires: 7 },
    unverified_by_source_kind: { inferred_cooccurrence: 14, manual_annotation: 11 },
    is_bounded_below: true,
    impacted_parts: ["013456903"],
    impacted_artifacts: ["TM-4120-19/1", "APL-556-02"],
  },
  "cand-5": {
    impact_snapshot_id: "snapshot-5",
    candidate_id: "cand-5",
    computed_at: "2026-08-01T10:50:00Z",
    max_depth_requested: 3,
    edges_touched: 110,
    edges_verified: 75,
    completeness_ratio: 0.68,
    nodes_expanded: 52,
    nodes_truncated_at_depth: 4,
    artifact_leaves_reached: 31,
    unverified_by_relation: { interfaces_with: 9, supports: 14, requires: 12 },
    unverified_by_source_kind: { inferred_cooccurrence: 22, manual_annotation: 13 },
    is_bounded_below: true,
    impacted_parts: ["013456410", "013456455", "013456488"],
    impacted_artifacts: ["TM-1810-33/6", "APL-330-07"],
  },
};

const PARAMETRIC_ASSUMPTIONS = [
  "Parametric cost model v0-demo, scaled from equipment_family baseline.",
  "Assumes standard depot-level integration labor rates.",
  "Excludes long-lead procurement risk premium.",
];

const PARAMETRIC_ESTIMATES: Record<string, CostEstimate> = {
  "cand-1": {
    estimate_id: "cost-parametric-1",
    candidate_id: "cand-1",
    case_id: null,
    method: "parametric",
    cost_model_version: "v0-demo",
    point_estimate_usd: 1_450_000,
    low_usd: 1_050_000,
    high_usd: 1_900_000,
    interval_basis: "±30%, demo heuristic band",
    confidence: 0.7,
    assumptions: PARAMETRIC_ASSUMPTIONS,
    impact_snapshot_id: null,
    coverage_ratio: null,
    is_lower_bound: false,
  },
  "cand-2": {
    estimate_id: "cost-parametric-2",
    candidate_id: "cand-2",
    case_id: null,
    method: "parametric",
    cost_model_version: "v0-demo",
    point_estimate_usd: 610_000,
    low_usd: 400_000,
    high_usd: 820_000,
    interval_basis: "±35%, demo heuristic band",
    confidence: 0.55,
    assumptions: PARAMETRIC_ASSUMPTIONS,
    impact_snapshot_id: null,
    coverage_ratio: null,
    is_lower_bound: false,
  },
  "cand-3": {
    estimate_id: "cost-parametric-3",
    candidate_id: "cand-3",
    case_id: null,
    method: "parametric",
    cost_model_version: "v0-demo",
    point_estimate_usd: 900_000,
    low_usd: 650_000,
    high_usd: 1_150_000,
    interval_basis: "±30%, demo heuristic band",
    confidence: 0.6,
    assumptions: PARAMETRIC_ASSUMPTIONS,
    impact_snapshot_id: null,
    coverage_ratio: null,
    is_lower_bound: false,
  },
  "cand-4": {
    estimate_id: "cost-parametric-4",
    candidate_id: "cand-4",
    case_id: null,
    method: "parametric",
    cost_model_version: "v0-demo",
    point_estimate_usd: 480_000,
    low_usd: 320_000,
    high_usd: 640_000,
    interval_basis: "±35%, demo heuristic band",
    confidence: 0.5,
    assumptions: PARAMETRIC_ASSUMPTIONS,
    impact_snapshot_id: null,
    coverage_ratio: null,
    is_lower_bound: false,
  },
  "cand-5": {
    estimate_id: "cost-parametric-5",
    candidate_id: "cand-5",
    case_id: null,
    method: "parametric",
    cost_model_version: "v0-demo",
    point_estimate_usd: 610_000,
    low_usd: 410_000,
    high_usd: 830_000,
    interval_basis: "±35%, demo heuristic band",
    confidence: 0.5,
    assumptions: PARAMETRIC_ASSUMPTIONS,
    impact_snapshot_id: null,
    coverage_ratio: null,
    is_lower_bound: false,
  },
};

// §1.4's gate logic, applied by hand against the numbers above -- these
// six booleans (and therefore `decision`/`failed_conditions`) must match
// §1.5's table exactly; that table is this fixture's ground truth.
const GATE_DECISIONS: Record<string, GateDecision> = {
  "cand-1": {
    gate_decision_id: "gate-1",
    candidate_id: "cand-1",
    dossier_id: "dossier-1",
    impact_snapshot_id: "snapshot-1",
    decision: "pass",
    condition_results: {
      G1_cost_floor: true,
      G2_priority_floor: true,
      G3_completeness_floor: true,
      G4_test_coverage_assessed: true,
      G5_evidentiary_floor: true,
      G6_state_consistency: true,
    },
    failed_conditions: [],
    thresholds_in_force: GATE_THRESHOLDS,
    gate_policy_version: "v0-demo-placeholder",
    computed_at: "2026-08-01T11:00:00Z",
  },
  "cand-2": {
    gate_decision_id: "gate-2",
    candidate_id: "cand-2",
    dossier_id: "dossier-2",
    impact_snapshot_id: "snapshot-2",
    decision: "fail",
    condition_results: {
      G1_cost_floor: true,
      G2_priority_floor: true,
      G3_completeness_floor: false,
      G4_test_coverage_assessed: true,
      G5_evidentiary_floor: true,
      G6_state_consistency: true,
    },
    failed_conditions: ["G3_completeness_floor"],
    thresholds_in_force: GATE_THRESHOLDS,
    gate_policy_version: "v0-demo-placeholder",
    computed_at: "2026-08-01T11:05:00Z",
  },
  "cand-3": {
    gate_decision_id: "gate-3",
    candidate_id: "cand-3",
    dossier_id: "dossier-3",
    impact_snapshot_id: "snapshot-3",
    decision: "fail",
    condition_results: {
      G1_cost_floor: true,
      G2_priority_floor: false,
      G3_completeness_floor: true,
      G4_test_coverage_assessed: true,
      G5_evidentiary_floor: true,
      G6_state_consistency: true,
    },
    failed_conditions: ["G2_priority_floor"],
    thresholds_in_force: GATE_THRESHOLDS,
    gate_policy_version: "v0-demo-placeholder",
    computed_at: "2026-08-01T11:10:00Z",
  },
  "cand-4": {
    gate_decision_id: "gate-4",
    candidate_id: "cand-4",
    dossier_id: "dossier-4",
    impact_snapshot_id: "snapshot-4",
    decision: "fail",
    condition_results: {
      G1_cost_floor: true,
      G2_priority_floor: true,
      G3_completeness_floor: true,
      G4_test_coverage_assessed: true,
      G5_evidentiary_floor: false,
      G6_state_consistency: true,
    },
    failed_conditions: ["G5_evidentiary_floor"],
    thresholds_in_force: GATE_THRESHOLDS,
    gate_policy_version: "v0-demo-placeholder",
    computed_at: "2026-08-01T11:15:00Z",
  },
  "cand-5": {
    gate_decision_id: "gate-5",
    candidate_id: "cand-5",
    dossier_id: "dossier-5",
    impact_snapshot_id: "snapshot-5",
    decision: "pass",
    condition_results: {
      G1_cost_floor: true,
      G2_priority_floor: true,
      G3_completeness_floor: true,
      G4_test_coverage_assessed: true,
      G5_evidentiary_floor: true,
      G6_state_consistency: true,
    },
    failed_conditions: [],
    thresholds_in_force: GATE_THRESHOLDS,
    gate_policy_version: "v0-demo-placeholder",
    computed_at: "2026-08-01T11:20:00Z",
  },
};

// derive_evidence_gaps, applied by hand per Michael's rules (demo plan,
// Michael's section, agent/derive.py): one gap per "absent*"
// test_coverage row (naming the test kind + absence_basis), one gap per
// contra citation, one gap for is_bounded_below. Always non-empty.
const EVIDENCE_GAPS: Record<string, string[]> = {
  "cand-1": [
    "No environmental-salt-fog testing has been performed for this NIIN — absence basis: Legacy component, predates current qualification regime.",
    "Dependency-graph verification is 78% complete for this NIIN; the traversal was truncated or otherwise incomplete below full confidence.",
  ],
  "cand-2": [
    "No cavitation-resistance testing has been performed for this NIIN — absence basis: Test kind added to the qualification catalog after this impeller's original acceptance.",
    "Dependency-graph verification is 42% complete for this NIIN; the traversal was truncated or otherwise incomplete below full confidence.",
  ],
  "cand-3": [
    "No shock-half-sine testing has been performed for this NIIN — absence basis: Card is not in a shock-critical mounting location per the combat system's own qualification plan.",
    "Dependency-graph verification is 75% complete for this NIIN; the traversal was truncated or otherwise incomplete below full confidence.",
  ],
  "cand-4": [
    "No bearing-life-accelerated testing has been performed for this NIIN — absence basis: Scheduled for next qualification cycle; not yet performed.",
    "A contradicting causal hypothesis was also examined for this failure mode and is not counted as supporting evidence.",
    "Dependency-graph verification is 71% complete for this NIIN; the traversal was truncated or otherwise incomplete below full confidence.",
  ],
  "cand-5": [
    "No overspeed testing has been performed for this NIIN — absence basis: Requires a dedicated test rig not currently available at the qualifying activity.",
    "Dependency-graph verification is 68% complete for this NIIN; the traversal was truncated or otherwise incomplete below full confidence.",
  ],
};

function buildQualificationReport(candidateId: string): QualificationReport {
  const dossier = DOSSIERS[candidateId];
  const snapshot = SNAPSHOTS[candidateId];
  const gate = GATE_DECISIONS[candidateId];
  return {
    run_id: `run-${candidateId}`,
    candidate_id: candidateId,
    niin: dossier.niin,
    dossier_id: dossier.dossier_id,
    impact_snapshot_id: snapshot.impact_snapshot_id,
    dependency_completeness: snapshot,
    parametric_estimate: PARAMETRIC_ESTIMATES[candidateId],
    gate_decision_id: gate.gate_decision_id,
    gate_decision: gate.decision,
    condition_results: gate.condition_results,
    failed_conditions: gate.failed_conditions,
    causal_citation_refs: dossier.causal_citations,
    derived_evidence_gaps: EVIDENCE_GAPS[candidateId],
    outcome: gate.decision === "pass" ? "gate_pass" : "gate_fail",
  };
}

export const QUALIFICATION_REPORTS: Record<string, QualificationReport> = Object.fromEntries(
  CANDIDATES.map((c) => [c.candidate_id, buildQualificationReport(c.candidate_id)]),
);

// Only candidates #1 and #5 pass the gate (§1.5) -- a draft package only
// ever exists for those two. `derive_limitations`/`compose_narrative`
// applied by hand per Michael's section's own rules.
export const DRAFT_PACKAGES: Record<string, CaseDraftPackage> = {
  "cand-1": {
    case_id: "case-1",
    candidate_id: "cand-1",
    niin: "013456789",
    dossier_id: "dossier-1",
    case_version: 1,
    case_status: "assembled",
    scope_description: "Redesign evaluation for 013456789",
    dependency_completeness: SNAPSHOTS["cand-1"],
    impact_snapshot_id: "snapshot-1",
    test_coverage_summary: {
      by_record_status: { present: 2, absent_not_performed: 1 },
      absent_unknown_count: 0,
    },
    cost_estimate_id: "cost-rollup-1",
    cost_estimate: {
      estimate_id: "cost-rollup-1",
      candidate_id: "cand-1",
      case_id: "case-1",
      method: "dependency_rollup",
      cost_model_version: "v0-demo",
      point_estimate_usd: 2_030_000,
      low_usd: 1_470_000,
      high_usd: 2_660_000,
      interval_basis: "±30%, demo heuristic band, dependency-rollup scaled",
      confidence: 0.6,
      assumptions: [
        "Dependency-rollup scaling factor (1.4x parametric) is a demo heuristic, not a real bottom-up estimate.",
        "Reflects only verified dependency-graph edges as of the impact snapshot.",
        "Excludes long-lead procurement risk premium.",
      ],
      impact_snapshot_id: "snapshot-1",
      coverage_ratio: 0.78,
      is_lower_bound: true,
    },
    recommendation_stance: "redesign_warranted_for_evaluation",
    recommendation_basis_refs: ["citation-1"],
    recommendation_limitations: [
      "This cost estimate is a lower bound — it reflects only the 78% of the dependency graph that has been verified.",
      "The strongest available supporting evidence for this NIIN has been assessed as strong; this recommendation should still be weighed against that evidentiary ceiling, not treated as certainty.",
    ],
    recommendation_evidence_gaps: EVIDENCE_GAPS["cand-1"],
    narrative_sections: [
      {
        heading: "Evidence Summary",
        body: "One published, strong-band causal citation (FM-FATIGUE-02) supports a redesign evaluation for this actuator, with 14 field failures recorded and no contra findings on file.",
      },
      {
        heading: "Cost and Impact",
        body: "The parametric cost estimate is $1,450,000; a dependency-rollup estimate against the verified portion of the dependency graph (78% complete) comes to $2,030,000, and should be read as a lower bound given the graph is not fully verified.",
      },
      {
        heading: "Limitations",
        body: "Even with a passing gate and a strong-band citation, environmental-salt-fog testing has never been performed on this legacy component, and the dependency graph underlying the cost figure above is only 78% verified.",
      },
      {
        heading: "Recommendation Basis",
        body: "Given a strong, published supporting citation, a field-failure count well above the evidentiary floor, and no contradicting evidence, this evaluation is recommended for further redesign consideration.",
      },
    ],
    assembled_at: "2026-08-12T14:32:00Z",
    proposal_id: null,
  },
  "cand-5": {
    case_id: "case-5",
    candidate_id: "cand-5",
    niin: "013456793",
    dossier_id: "dossier-5",
    case_version: 1,
    case_status: "assembled",
    scope_description: "Redesign evaluation for 013456793",
    dependency_completeness: SNAPSHOTS["cand-5"],
    impact_snapshot_id: "snapshot-5",
    test_coverage_summary: {
      by_record_status: { present_unparsed: 1, present: 1, absent_not_performed: 1 },
      absent_unknown_count: 0,
    },
    cost_estimate_id: "cost-rollup-5",
    cost_estimate: {
      estimate_id: "cost-rollup-5",
      candidate_id: "cand-5",
      case_id: "case-5",
      method: "dependency_rollup",
      cost_model_version: "v0-demo",
      point_estimate_usd: 854_000,
      low_usd: 574_000,
      high_usd: 1_162_000,
      interval_basis: "±35%, demo heuristic band, dependency-rollup scaled",
      confidence: 0.45,
      assumptions: [
        "Dependency-rollup scaling factor (1.4x parametric) is a demo heuristic, not a real bottom-up estimate.",
        "Reflects only verified dependency-graph edges as of the impact snapshot.",
        "Excludes long-lead procurement risk premium.",
      ],
      impact_snapshot_id: "snapshot-5",
      coverage_ratio: 0.68,
      is_lower_bound: true,
    },
    recommendation_stance: "monitor_and_reassess",
    recommendation_basis_refs: ["citation-5"],
    recommendation_limitations: [
      "Unaddressed confounders in the supporting evidence: duty-cycle variation not controlled; sample spans two bearing-assembly design revisions without separation.",
      "This cost estimate is a lower bound — it reflects only the 68% of the dependency graph that has been verified.",
      "The only supporting evidence for this NIIN has been assessed as weak; a passing gate does not mean the underlying evidence is strong.",
    ],
    recommendation_evidence_gaps: EVIDENCE_GAPS["cand-5"],
    narrative_sections: [
      {
        heading: "Evidence Summary",
        body: "One published, weak-band causal citation (FM-BEARING-09) is the only supporting evidence for this bearing assembly; 9 field failures are on file, just above the evidentiary floor.",
      },
      {
        heading: "Cost and Impact",
        body: "The parametric cost estimate is $610,000; a dependency-rollup estimate against the verified portion of the dependency graph (68% complete) comes to $854,000, and should be read as a lower bound given the graph is not fully verified.",
      },
      {
        heading: "Limitations",
        body: "The supporting citation is weak-band and carries two unaddressed confounders — duty-cycle variation, and an unseparated mix of bearing-assembly design revisions in the sample — that were never controlled for.",
      },
      {
        heading: "Recommendation Basis",
        body: "The gate passed on cost, priority, completeness, and evidentiary-floor conditions, but the only supporting evidence is weak and confounded. That combination is recommended for continued monitoring and reassessment, not for redesign evaluation, until stronger or better-controlled evidence is available.",
      },
    ],
    assembled_at: "2026-08-12T14:40:00Z",
    proposal_id: null,
  },
};
