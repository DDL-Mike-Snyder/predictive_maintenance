import {
  CANDIDATES,
  QUALIFICATION_REPORTS,
  DRAFT_PACKAGES,
  type RedesignCandidate,
  type QualificationReport,
  type CaseDraftPackage,
} from "./fixtures";

// [SCOPE, this pass] Every function below resolves from the hand-written
// fixtures in fixtures.ts, after a fixed delay so the UI's loading states
// are real and visible, not instant -- per the demo plan's own
// instruction (Bella's section, task 2). Each function's signature is
// deliberately stable so that swapping the body for a real call at
// integration is a five-line diff, not a rewrite; the real paths are
// exactly `/api/v1/design-advisory/...`, documented call-by-call below,
// per Paul's/Marc's/Michael's sections of
// docs/demo/redesign-case-builder-demo-plan.md.
//
// [NOTE] `runDraft` takes a `candidateId`, not a `caseId` -- the UI never
// has a case_id in hand before drafting for the first time (no case
// exists yet at that point; Michael's agent `draft` endpoint creates one
// via Marc's `POST /redesign-cases` itself if none exists). Only after a
// draft resolves does the UI have the `case_id` that `submitProposal`
// needs.

const DEMO_DELAY_MS = 800;

function resolveAfterDelay<T>(value: T): Promise<T> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(value), DEMO_DELAY_MS);
  });
}

export async function fetchCandidates(): Promise<RedesignCandidate[]> {
  return resolveAfterDelay(CANDIDATES);
  // Real: GET /api/v1/design-advisory/redesign-candidates
}

export async function runQualify(candidateId: string): Promise<QualificationReport> {
  const report = QUALIFICATION_REPORTS[candidateId];
  if (!report) {
    throw new Error(`No qualification fixture for candidate ${candidateId}`);
  }
  return resolveAfterDelay(report);
  // Real: POST /api/v1/design-advisory/agent/candidates/{candidateId}/qualify
}

export async function runDraft(candidateId: string): Promise<CaseDraftPackage> {
  const draft = DRAFT_PACKAGES[candidateId];
  if (!draft) {
    throw new Error(`No draft fixture for candidate ${candidateId} -- did its gate pass?`);
  }
  return resolveAfterDelay(draft);
  // Real: POST /api/v1/design-advisory/agent/cases/{case_id}/draft
  // (case_id resolved server-side from candidateId if no draft case exists yet)
}

export async function submitProposal(
  caseId: string,
): Promise<{ case_id: string; case_status: "proposed"; proposal_id: string }> {
  const result = {
    case_id: caseId,
    case_status: "proposed" as const,
    proposal_id: `demo-proposal-${caseId}`,
  };
  return resolveAfterDelay(result);
  // Real: POST /api/v1/design-advisory/redesign-cases/{caseId}/propose
}
