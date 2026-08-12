import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { fetchCandidates, runDraft, runQualify, submitProposal } from "./api";
import {
  CONDITION_LABELS,
  CONDITION_ORDER,
  GATE_THRESHOLDS,
  STANCE_LABELS,
  type CausalCitation,
  type QualificationReport,
  type RedesignCandidate,
} from "./fixtures";

// docs/build/42-redesign-case-builder.md §1 -- the agent composes a
// package for a human to evaluate; it never decides (B1-B4). The two
// places that rule actually shows up on screen: `suggested_stance` is
// always rendered with an explicit "pending human review" label, never
// as a decision (see the stance row in the draft panel below), and a
// failed gate is always shown as an honest refusal message, never
// silently drafted around.
//
// [SCOPE, this pass] Built against docs/demo/redesign-case-builder-demo
// -plan.md §1's contract, against hand-written fixtures (api.ts) rather
// than a real backend -- see that file's own header comment for exactly
// what a real integration swap looks like. Layout follows
// apps/web/src/features/pdm/FleetRiskTriage.tsx's own precedent: a
// candidate list, a qualification detail panel, and an action/draft
// panel, in that order, matching the same `.sheet`/`.box` wireframe
// vocabulary (styles/global.css) rather than inventing new classes.

function formatUsd(value: number): string {
  return `$${Math.round(value).toLocaleString()}`;
}

function formatPct(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}

function formatStance(stance: string): string {
  return STANCE_LABELS[stance as keyof typeof STANCE_LABELS] ?? stance;
}

// 28 §5.3's G1-G6, explained generically from whatever the running
// report/candidate actually carry -- never a per-candidate hardcoded
// string, per this file's own "definition of done."
function failureExplanation(
  code: string,
  report: QualificationReport,
  candidate: RedesignCandidate,
): string {
  switch (code) {
    case "G1_cost_floor":
      return `Parametric cost estimate (${formatUsd(report.parametric_estimate.point_estimate_usd)}) is below the ${formatUsd(GATE_THRESHOLDS.costFloorUsd)} floor for detailed evaluation.`;
    case "G2_priority_floor":
      return `Priority score (${candidate.priority_score.toFixed(2)}) is below the ${GATE_THRESHOLDS.priorityFloor.toFixed(2)} floor — this NIIN is well-evidenced, but not enough currently depends on it to justify detailed cost estimation.`;
    case "G3_completeness_floor":
      return `Dependency completeness is ${formatPct(report.dependency_completeness.completeness_ratio)} (floor: ${formatPct(GATE_THRESHOLDS.completenessFloor)}) — populate the dependency graph for this NIIN before a detailed cost estimate can be justified.`;
    case "G4_test_coverage_assessed":
      return "One or more test-coverage records for this NIIN have an unresolved (absent_unknown) status and must be assessed before gating can proceed.";
    case "G5_evidentiary_floor": {
      const hasContraOnly = report.causal_citation_refs.every((c) => c.posture !== "supporting");
      return hasContraOnly
        ? "The only causal evidence on file for this NIIN is contra — a contradicting hypothesis is never counted toward the evidentiary floor, regardless of how well it was adjudicated."
        : `Neither the field-failure count nor a published, supporting causal citation meets the evidentiary floor (${GATE_THRESHOLDS.fieldFailureFloor} field failures, or one published supporting citation).`;
    }
    case "G6_state_consistency":
      return "This candidate is not currently in a state eligible for gate evaluation.";
    default:
      return code;
  }
}

function CitationRow({ citation }: { citation: CausalCitation }) {
  return (
    <tr>
      <td>
        <span className={`chip ${citation.posture === "supporting" ? "good" : "critical"}`}>
          {citation.posture}
        </span>
      </td>
      <td>{citation.strength_band}</td>
      <td>{citation.failure_mode_code}</td>
      <td>
        {citation.confounders_unaddressed.length > 0 ? (
          <span className="chip warning">{citation.confounders_unaddressed.length} unaddressed</span>
        ) : (
          <span className="chip neutral">none noted</span>
        )}
      </td>
    </tr>
  );
}

function ConditionChecklist({
  report,
  candidate,
}: {
  report: QualificationReport;
  candidate: RedesignCandidate;
}) {
  return (
    <div className="table-scroll">
      <table className="wf">
        <caption>Gate conditions (28 §5.3) — thresholds v0-demo-placeholder</caption>
        <thead>
          <tr>
            <th>Condition</th>
            <th>Result</th>
          </tr>
        </thead>
        <tbody>
          {CONDITION_ORDER.map((code) => {
            const pass = report.condition_results[code];
            return (
              <tr key={code}>
                <td>{CONDITION_LABELS[code]}</td>
                <td>
                  <span className={`chip ${pass ? "good" : "critical"}`}>{pass ? "pass" : "fail"}</span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {report.failed_conditions.length > 0 && (
        <ul style={{ marginTop: "var(--sp-4)" }}>
          {report.failed_conditions.map((code) => (
            <li key={code} className="sheet-note" style={{ marginBottom: "var(--sp-2)" }}>
              {failureExplanation(code, report, candidate)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function QualificationPanel({
  candidate,
  report,
}: {
  candidate: RedesignCandidate;
  report: QualificationReport;
}) {
  const snapshot = report.dependency_completeness;
  const estimate = report.parametric_estimate;
  return (
    <div className="col box">
      <span className="box-label">Qualification report — {candidate.niin}</span>
      <div className="box-content">
        <div className="row" style={{ alignItems: "center", marginBottom: "var(--sp-5)" }}>
          <span className={`chip ${report.outcome === "gate_pass" ? "good" : "critical"}`}>
            gate {report.gate_decision}
          </span>
          {snapshot.is_bounded_below && (
            <span className="chip warning">
              dependency completeness {formatPct(snapshot.completeness_ratio)} — bounded below
            </span>
          )}
        </div>

        <ConditionChecklist report={report} candidate={candidate} />

        <div className="row wrap-mobile" style={{ marginTop: "var(--sp-6)" }}>
          <div className="col box">
            <span className="box-label">Parametric cost estimate</span>
            <div className="box-content">
              <p style={{ fontSize: "var(--fs-500)", margin: "0 0 var(--sp-3)" }}>
                {formatUsd(estimate.point_estimate_usd)}
              </p>
              {estimate.low_usd !== null && estimate.high_usd !== null && (
                <p className="sheet-note" style={{ margin: 0 }}>
                  Range {formatUsd(estimate.low_usd)}–{formatUsd(estimate.high_usd)} ({estimate.interval_basis})
                </p>
              )}
            </div>
          </div>
          <div className="col box">
            <span className="box-label">Causal citations</span>
            <div className="box-content table-scroll">
              <table className="wf">
                <thead>
                  <tr>
                    <th>Posture</th>
                    <th>Strength</th>
                    <th>Failure mode</th>
                    <th>Confounders</th>
                  </tr>
                </thead>
                <tbody>
                  {report.causal_citation_refs.map((c) => (
                    <CitationRow key={c.citation_id} citation={c} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function EvidenceCaveatsBox({ limitations, evidenceGaps }: { limitations: string[]; evidenceGaps: string[] }) {
  return (
    <div
      className="box"
      style={{
        borderColor: "var(--warning)",
        background: "var(--warning-bg)",
      }}
    >
      <span className="box-label" style={{ background: "var(--warning-bg)", color: "var(--warning)" }}>
        What this recommendation does not know
      </span>
      <div className="box-content">
        <p style={{ fontWeight: 700, margin: "0 0 var(--sp-2)" }}>Limitations</p>
        <ul style={{ marginTop: 0 }}>
          {limitations.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
        <p style={{ fontWeight: 700, margin: "var(--sp-4) 0 var(--sp-2)" }}>Evidence gaps</p>
        <ul style={{ marginTop: 0, marginBottom: 0 }}>
          {evidenceGaps.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function RedesignCaseBuilder() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const candidatesQuery = useQuery({
    queryKey: ["design-advisory", "candidates"],
    queryFn: fetchCandidates,
  });

  const qualifyMutation = useMutation({ mutationFn: runQualify });
  const draftMutation = useMutation({ mutationFn: runDraft });
  const proposeMutation = useMutation({ mutationFn: submitProposal });

  const candidates = candidatesQuery.data ?? [];
  const selected = candidates.find((c) => c.candidate_id === selectedId) ?? null;
  // Guard against a stale mutation result surviving a new selection (the
  // mutations aren't keyed by candidate, so react-query alone won't clear
  // last candidate's report/draft when selectCandidate resets them).
  const report = qualifyMutation.variables === selectedId ? qualifyMutation.data ?? null : null;
  const draft = draftMutation.variables === selectedId ? draftMutation.data ?? null : null;

  function selectCandidate(candidateId: string) {
    setSelectedId(candidateId);
    qualifyMutation.reset();
    draftMutation.reset();
    proposeMutation.reset();
  }

  return (
    <section className="sheet">
      <div className="titleblock">
        <div className="tb-left">
          <span className="sheet-no">DEMO / REDESIGN CASE BUILDER</span>
          <h2>Redesign Case Builder</h2>
          <span className="persona">Design engineer — candidate qualification &amp; case drafting</span>
        </div>
        <div className="tb-right">
          Doc 42 §1<br />
          Doc 28 §5
        </div>
      </div>

      <div className="sheet-body">
        {candidatesQuery.isLoading && <p aria-busy="true">Loading candidates…</p>}
        {candidatesQuery.isError && <p role="alert">Couldn't load redesign candidates</p>}

        {candidates.length > 0 && (
          <div className="box">
            <span className="box-label">Redesign candidates</span>
            <div className="box-content table-scroll">
              <table className="wf">
                <thead>
                  <tr>
                    <th>NIIN</th>
                    <th>Nomenclature</th>
                    <th>Status</th>
                    <th className="num">Priority score</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((c) => (
                    <tr
                      key={c.candidate_id}
                      onClick={() => selectCandidate(c.candidate_id)}
                      aria-selected={c.candidate_id === selectedId}
                      style={{
                        cursor: "pointer",
                        background: c.candidate_id === selectedId ? "var(--paper-2)" : undefined,
                      }}
                    >
                      <td>{c.niin}</td>
                      <td>{c.nomenclature}</td>
                      <td>
                        <span className="chip neutral">{c.status}</span>
                      </td>
                      <td className="num">{c.priority_score.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="sheet-note" style={{ marginTop: "var(--sp-4)" }}>
              Click a candidate to run qualification. This list does not rank candidates by expected
              consequence — that ranking is not built in this demo.
            </p>
          </div>
        )}

        {selected && (
          <div className="box">
            <span className="box-label">Qualify — {selected.niin}</span>
            <div className="box-content">
              {qualifyMutation.isPending && <p aria-busy="true">Running qualification…</p>}
              {qualifyMutation.isError && <p role="alert">Qualification failed for this candidate</p>}
              {!report && !qualifyMutation.isPending && (
                <button className="btn primary" onClick={() => qualifyMutation.mutate(selected.candidate_id)}>
                  Run Qualification
                </button>
              )}
            </div>
          </div>
        )}

        {selected && report && <QualificationPanel candidate={selected} report={report} />}

        {selected && report && report.outcome === "gate_pass" && (
          <div className="box">
            <span className="box-label">Draft case — {selected.niin}</span>
            <div className="box-content">
              {!draft && !draftMutation.isPending && (
                <button className="btn primary" onClick={() => draftMutation.mutate(selected.candidate_id)}>
                  Draft Case
                </button>
              )}
              {draftMutation.isPending && <p aria-busy="true">Drafting case…</p>}
              {draftMutation.isError && <p role="alert">Drafting failed for this case</p>}

              {draft && (
                <>
                  <div className="col box" style={{ marginBottom: "var(--sp-5)" }}>
                    <span className="box-label">Narrative</span>
                    <div className="box-content">
                      {draft.narrative_sections.map((section) => (
                        <div key={section.heading} style={{ marginBottom: "var(--sp-5)" }}>
                          <p style={{ fontWeight: 700, margin: "0 0 var(--sp-2)" }}>{section.heading}</p>
                          <p style={{ margin: 0 }}>{section.body}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  <EvidenceCaveatsBox
                    limitations={draft.recommendation_limitations}
                    evidenceGaps={draft.recommendation_evidence_gaps}
                  />

                  <div
                    className="row"
                    style={{ alignItems: "center", marginTop: "var(--sp-6)", marginBottom: "var(--sp-6)" }}
                  >
                    <span className="chip accent">Suggested — pending human review</span>
                    <strong>{formatStance(draft.recommendation_stance)}</strong>
                  </div>

                  {draft.case_status === "proposed" || proposeMutation.data ? (
                    <p className="sheet-note">
                      Proposal submitted — awaiting design-authority adjudication (not implemented in this
                      demo).
                    </p>
                  ) : (
                    <button
                      className="btn primary"
                      onClick={() => proposeMutation.mutate(draft.case_id)}
                      disabled={proposeMutation.isPending}
                    >
                      {proposeMutation.isPending ? "Submitting…" : "Submit Proposal"}
                    </button>
                  )}
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
