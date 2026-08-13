import {
  type RedesignCandidate,
  type QualificationReport,
  type CaseDraftPackage,
} from "./fixtures";

// [B-3 integration fix] These call the real design-advisory backend
// through the gateway (same-origin `/api/v1/design-advisory/...`, proxied
// to the gateway by Vite in dev -- see vite.config.ts). The fixtures in
// fixtures.ts are retained only as the source of the TypeScript types
// above; no fixture DATA is served anymore.
//
// Every state-changing (`POST`) call carries an `Idempotency-Key` header:
// the gateway annotates these operations `x-side-effects: state-changing`
// and its middleware refuses them (HTTP 400) without the header (09 §8.1).
// `credentials: "include"` sends the gateway session cookie (demo_auto_login
// establishes one transparently in the demo).
//
// [NOTE] `runDraft` takes a `candidateId`, not a `caseId` -- the UI has no
// case_id before drafting. The real agent `draft` endpoint operates on a
// case_id, so runDraft first resolves (or creates) the candidate's
// redesign_case, then drafts it.

const BASE = "/api/v1/design-advisory";

function idempotencyKey(): string {
  return crypto.randomUUID();
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { credentials: "include" });
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status} ${await res.text()}`);
  }
  return (await res.json()) as T;
}

async function postJson<T>(path: string, body: unknown = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "content-type": "application/json",
      "Idempotency-Key": idempotencyKey(),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`POST ${path} failed: ${res.status} ${await res.text()}`);
  }
  return (await res.json()) as T;
}

export async function fetchCandidates(): Promise<RedesignCandidate[]> {
  return getJson<RedesignCandidate[]>("/redesign-candidates");
}

export async function runQualify(candidateId: string): Promise<QualificationReport> {
  return postJson<QualificationReport>(`/agent/candidates/${candidateId}/qualify`);
}

export async function runDraft(candidateId: string): Promise<CaseDraftPackage> {
  // Resolve the candidate's case, then draft it. On the freshly-seeded demo
  // DB no case exists, so this always creates then drafts. The extra
  // branches keep a re-click from failing: the agent `draft` endpoint only
  // accepts a case in `draft` status (409 otherwise), so an
  // already-assembled/proposed case is returned as-is instead of redrafted.
  const existing = await getJson<{ case_id: string; case_status: string }[]>(
    `/redesign-cases?candidate_id=${candidateId}`,
  );
  const alreadyDrafted = existing.find(
    (c) => c.case_status === "assembled" || c.case_status === "proposed",
  );
  if (alreadyDrafted) {
    return getJson<CaseDraftPackage>(`/redesign-cases/${alreadyDrafted.case_id}`);
  }
  const draftCase = existing.find((c) => c.case_status === "draft");
  const caseId = draftCase
    ? draftCase.case_id
    : (await postJson<{ case_id: string }>("/redesign-cases", { candidate_id: candidateId }))
        .case_id;
  return postJson<CaseDraftPackage>(`/agent/cases/${caseId}/draft`, {});
}

export async function submitProposal(
  caseId: string,
): Promise<{ case_id: string; case_status: "proposed"; proposal_id: string }> {
  const proposed = await postJson<{
    case_id: string;
    case_status: "proposed";
    proposal_id: string;
  }>(`/redesign-cases/${caseId}/propose`);
  return proposed;
}
