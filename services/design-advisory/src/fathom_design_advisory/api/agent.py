"""`/api/v1/design-advisory/agent/*` -- Michael's orchestration endpoints
(`docs/demo/redesign-case-builder-demo-plan.md` "Michael" section, task 3;
a demo-scoped simplification of `docs/build/42-redesign-case-builder.md`
§4.1's two invocations, `qualify` and `draft`).

This file talks to Paul's read endpoints and Marc's action endpoints
purely over HTTP (`httpx.AsyncClient`, base URL from the
`DESIGN_ADVISORY_BASE_URL` env var, default `http://localhost:8002`) --
it never imports `fathom_design_advisory.models`/`.db` directly. That
mirrors 42 §2.1's real "exclusively through [an API], never direct DB
access" boundary, even though the tool-server layer that would normally
enforce it (34-tool-server.md) is out of scope for this demo (§0.1).

**[ASSUMPTION, demo-only]** -- noted here per the build plan's own Ground
Rules ("if the shared contract is ambiguous in a way that blocks you,
post it immediately and pick the more-demoable interpretation yourself...
note what you assumed in your commit message"). §1.3/§1.6 of the plan
document Paul's `api/reads.py` with only get-by-id endpoints for
impact-snapshots/cost-estimates, and no read endpoint at all for gate
decisions -- but `qualify`/`draft` both need to look these up **by
candidate_id**, which this file doesn't otherwise have an id for ahead of
time. This file assumes three list-by-`candidate_id` filters exist on
Paul's `reads.py` (mirroring exactly the
`GET /impact-snapshots?candidate_id=` filter Michael's own section
already anticipated needing):

  - `GET /impact-snapshots?candidate_id=`                  -> list, take [0]
  - `GET /cost-estimates?candidate_id=&method=parametric`  -> list, take [0]
  - `GET /gate-decisions?candidate_id=`                    -> list, most
    recent by `computed_at` (28 §5.2: re-evaluation writes a new row every
    time, so "the" gate decision for a candidate is always "the latest
    one")

If Paul's real implementation doesn't have these, add them -- each is a
few lines in `reads.py`, and this file has no other way to reach these
rows given only a `candidate_id`.
"""

from __future__ import annotations

import os
import uuid
from http import HTTPStatus

import httpx
from fastapi import APIRouter, HTTPException
from fathom_design_advisory.agent.derive import derive_evidence_gaps, derive_limitations
from fathom_design_advisory.agent.narrative import compose_narrative
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/design-advisory/agent", tags=["agent"])

_DEFAULT_BASE_URL = "http://localhost:8002"


def _base_url() -> str:
    return os.environ.get("DESIGN_ADVISORY_BASE_URL", _DEFAULT_BASE_URL)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=_base_url(), timeout=20.0)


def _raise_for_upstream_status(response: httpx.Response, path: str) -> None:
    if response.status_code < HTTPStatus.BAD_REQUEST:
        return
    try:
        detail = response.json()
    except ValueError:
        detail = response.text or f"upstream returned {response.status_code} for {path}"
    # Propagate Paul's/Marc's own status code and message verbatim -- a 404
    # "no dossier assembled yet" or a 409 "gate has not passed" is real
    # signal a caller needs, not something to flatten into a generic 502.
    # (Only an actual transport failure, caught below, becomes a 502.)
    raise HTTPException(status_code=response.status_code, detail=detail) from None


async def _request(
    client: httpx.AsyncClient, method: str, path: str, **kwargs: object
) -> httpx.Response:
    try:
        return await client.request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=HTTPStatus.BAD_GATEWAY,
            detail=f"upstream design-advisory call failed: {method} {path}: {exc}",
        ) from exc


async def _get(client: httpx.AsyncClient, path: str) -> dict:
    response = await _request(client, "GET", path)
    _raise_for_upstream_status(response, path)
    return response.json()


async def _get_list(client: httpx.AsyncClient, path: str) -> list[dict]:
    response = await _request(client, "GET", path)
    _raise_for_upstream_status(response, path)
    return response.json()


async def _post(client: httpx.AsyncClient, path: str, body: dict) -> dict:
    response = await _request(client, "POST", path, json=body)
    _raise_for_upstream_status(response, path)
    return response.json()


async def _first_or_404(client: httpx.AsyncClient, path: str, what: str) -> dict:
    rows = await _get_list(client, path)
    if not rows:
        raise HTTPException(status_code=404, detail=f"no {what} found via {path}")
    return rows[0]


def _latest_gate_decision(rows: list[dict]) -> dict | None:
    if not rows:
        return None
    return max(rows, key=lambda r: r.get("computed_at", ""))


class QualificationReport(BaseModel):
    """Trimmed to what this demo slice actually has -- 42 §3.2.1's real
    shape includes several fields (taxonomy resolution, Failure
    Intelligence preflight, retrieval hits) this demo never computes,
    per §0.1.
    """

    run_id: str
    candidate_id: str
    niin: str
    dossier_id: str
    impact_snapshot_id: str
    dependency_completeness: dict
    parametric_estimate: dict
    gate_decision_id: str
    gate_decision: str
    condition_results: dict
    failed_conditions: list[str]
    causal_citation_refs: list[dict]
    derived_evidence_gaps: list[str]
    outcome: str


class DraftRequest(BaseModel):
    """Optional -- only needed when `case_id` doesn't exist yet and the
    caller wants this endpoint to create the draft case itself via Marc's
    `POST /redesign-cases` (see the `draft` handler's docstring).
    """

    candidate_id: str | None = None


@router.post("/candidates/{candidate_id}/qualify", response_model=QualificationReport)
async def qualify(candidate_id: str) -> QualificationReport:
    """42 §4.1 steps 1-3, 6-8, simplified: fetch candidate + dossier +
    impact snapshot, run Marc's parametric-estimate then evaluate-gate,
    derive evidence gaps. Steps 4-5 (taxonomy resolution, Failure
    Intelligence preflight) and the retrieval step are skipped per §0.1 --
    all of that data is pre-seeded by Paul rather than fetched live.
    """
    candidates_path = f"/api/v1/design-advisory/redesign-candidates/{candidate_id}"
    async with _client() as client:
        candidate = await _get(client, candidates_path)
        dossier_id = candidate.get("dossier_id")
        if not dossier_id:
            raise HTTPException(
                status_code=409,
                detail=f"candidate {candidate_id} has no dossier assembled yet; cannot qualify",
            )
        dossier = await _get(client, f"/api/v1/design-advisory/dossiers/{dossier_id}")
        impact_snapshot = await _first_or_404(
            client,
            f"/api/v1/design-advisory/impact-snapshots?candidate_id={candidate_id}",
            "impact snapshot",
        )

        parametric_estimate = await _post(client, f"{candidates_path}/parametric-estimate", {})
        gate_decision = await _post(client, f"{candidates_path}/evaluate-gate", {})

    evidence_gaps = derive_evidence_gaps(dossier, impact_snapshot)
    outcome = "gate_pass" if gate_decision.get("decision") == "pass" else "gate_fail"

    return QualificationReport(
        run_id=str(uuid.uuid4()),
        candidate_id=candidate_id,
        niin=candidate.get("niin", ""),
        dossier_id=dossier_id,
        impact_snapshot_id=impact_snapshot.get("impact_snapshot_id", ""),
        dependency_completeness=impact_snapshot,
        parametric_estimate=parametric_estimate,
        gate_decision_id=gate_decision.get("gate_decision_id", ""),
        gate_decision=gate_decision.get("decision", ""),
        condition_results=gate_decision.get("condition_results", {}),
        failed_conditions=gate_decision.get("failed_conditions", []),
        causal_citation_refs=dossier.get("causal_citations", []),
        derived_evidence_gaps=evidence_gaps,
        outcome=outcome,
    )


@router.post("/cases/{case_id}/draft")
async def draft(case_id: str, body: DraftRequest | None = None) -> dict:
    """42 §4.1 steps 10-12, simplified: load the draft case (creating it
    via Marc's `POST /redesign-cases` first if `case_id` doesn't resolve
    and a `candidate_id` was supplied), pull the dossier/snapshot/cost
    estimate/gate decision it needs, derive limitations + evidence gaps,
    compose the narrative, then call Marc's own
    `POST /redesign-cases/{id}/assemble` to persist the result -- this
    file never writes to the DB directly, persistence happens exactly
    once, in Marc's endpoint.
    """
    body = body or DraftRequest()

    async with _client() as client:
        try:
            case = await _get(client, f"/api/v1/design-advisory/redesign-cases/{case_id}")
        except HTTPException as exc:
            if exc.status_code == HTTPStatus.NOT_FOUND and body.candidate_id:
                case = await _post(
                    client,
                    "/api/v1/design-advisory/redesign-cases",
                    {"candidate_id": body.candidate_id},
                )
                case_id = case["case_id"]
            else:
                raise

        if case.get("case_status") != "draft":
            raise HTTPException(
                status_code=409,
                detail=(
                    f"case {case_id} is not in draft status "
                    f"(status={case.get('case_status')!r}); refusing to draft again"
                ),
            )

        candidate_id = case["candidate_id"]
        candidates_path = f"/api/v1/design-advisory/redesign-candidates/{candidate_id}"
        candidate = await _get(client, candidates_path)
        dossier = await _get(client, f"/api/v1/design-advisory/dossiers/{case['dossier_id']}")
        impact_snapshot = await _first_or_404(
            client,
            f"/api/v1/design-advisory/impact-snapshots?candidate_id={candidate_id}",
            "impact snapshot",
        )
        cost_estimate = await _first_or_404(
            client,
            f"/api/v1/design-advisory/cost-estimates?candidate_id={candidate_id}&method=parametric",
            "parametric cost estimate",
        )
        gate_decisions_path = f"/api/v1/design-advisory/gate-decisions?candidate_id={candidate_id}"
        gate_rows = await _get_list(client, gate_decisions_path)
        gate_decision = _latest_gate_decision(gate_rows)
        if gate_decision is None or gate_decision.get("decision") != "pass":
            raise HTTPException(
                status_code=409,
                detail=f"candidate {candidate_id} has not passed the gate; refusing to draft",
            )

        evidence_gaps = derive_evidence_gaps(dossier, impact_snapshot)
        limitations = derive_limitations(cost_estimate, dossier)
        narrative = await compose_narrative(
            candidate=candidate,
            dossier=dossier,
            impact_snapshot=impact_snapshot,
            cost_estimate=cost_estimate,
            gate_decision=gate_decision,
            limitations=limitations,
            evidence_gaps=evidence_gaps,
        )

        assembled = await _post(
            client,
            f"/api/v1/design-advisory/redesign-cases/{case_id}/assemble",
            {
                "recommendation_stance": narrative["suggested_stance"],
                "recommendation_limitations": limitations,
                "recommendation_evidence_gaps": evidence_gaps,
                "narrative_sections": narrative["narrative_sections"],
            },
        )

    return assembled
