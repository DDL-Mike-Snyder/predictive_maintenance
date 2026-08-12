"""Michael's LLM-composed narrative section
(`docs/demo/redesign-case-builder-demo-plan.md` "Michael" section, task 2
-- a demo-scoped stand-in for `docs/build/42-redesign-case-builder.md`
§1.3's "Composed" row).

**The single rule this file exists to protect**: 42 §1.3 --
*"A model selecting `redesign_warranted_for_evaluation` is a model making
a recommendation,"* which 04 §10 places outside this system entirely.
`_select_suggested_stance` below picks the stance in plain, deterministic
code, before the model is ever invoked. The model (or, on any failure,
the template fallback) is only ever asked to write the human-readable
*prose* -- never to choose *what* the recommendation is.

**The second rule**: 42 §5.6 -- every number in the narrative must come
from the carried figures this module is handed as arguments, never be
invented. The prompt sent to the model contains only carried figures
(never a raw dossier/impact-snapshot dump), and both the model path and
the template fallback are built exclusively from this function's own
arguments.

[ASSUMPTION, demo-only, noted per the build plan's own Ground Rules
("post it immediately and pick the more-demoable interpretation
yourself... note what you assumed")]: this repo has no `LLMPort`
implementation anywhere (42 §17 OD-RCB-1 / §18 correction 6 -- the port
doesn't exist in `packages/py-common` or `packages/canonical-schemas`),
and the `dominodatalab:ai-gateway` skill the build plan names was not
available in this build environment (no Domino credentials either). Per
the plan's own instruction ("do not burn more than 15 minutes chasing AI
Gateway auth issues... a templated-but-numerically-honest narrative is a
fine demo outcome"), this module talks to a generic OpenAI-compatible
chat-completions endpoint over plain `httpx` -- no new dependency, no SDK
-- gated on two env vars (`DESIGN_ADVISORY_AI_GATEWAY_URL`,
`DESIGN_ADVISORY_AI_GATEWAY_API_KEY`) that are expected to be unset
outside a real Domino workspace with AI Gateway access. Unset (or any
failure at all -- bad response shape, timeout, network error) always
falls back to the fixed template below; the fallback path is exercised
and verified in this build, since no AI Gateway credentials exist in this
environment.
"""

from __future__ import annotations

import json
import logging
import os

import httpx

logger = logging.getLogger(__name__)

# 28 §5.4 / this demo's own §1.4 gate threshold. Duplicated here rather
# than imported from Paul's `config.py` -- this module intentionally has
# no dependency on `fathom_design_advisory.config` (Paul's file, not
# touched by this section). Keep this in sync with
# `fathom_design_advisory.config.Settings.gate_field_failure_floor` if
# that default is ever changed there.
GATE_FIELD_FAILURE_FLOOR = 8

_STRENGTH_RANK = {"strong": 3, "moderate": 2, "weak": 1, "insufficient": 0}

# Never let a hung AI Gateway call eat into the "do not burn more than 15
# minutes" budget this section is held to -- fail fast, fall back.
_AI_GATEWAY_TIMEOUT_S = 8.0


def _select_suggested_stance(dossier: dict) -> tuple[str, str]:
    """The ONE place `suggested_stance` gets decided -- in code, by rule.

    Rules (demo build plan, "Michael" section, task 2):
      - Zero published+supporting citations -> `insufficient_evidence`.
      - `field_failure_count` below the floor AND the only support is a
        single `weak` citation with unaddressed confounders ->
        `no_action_indicated`.
      - The strongest supporting citation is `weak` OR has unaddressed
        confounders -> `monitor_and_reassess` (this is candidate #5 in
        §1.5: the gate passing is not the same as the evidence being
        strong).
      - Otherwise -> `redesign_warranted_for_evaluation` (candidate #1).

    Returns `(stance, basis)` -- `basis` is a short, carried-figures-only
    explanation of *why* this stance was picked, handed to the model (or
    the template) to expand into prose. The model never sees this
    function and is never asked to reproduce or second-guess its output.
    """
    citations = dossier.get("causal_citations", [])
    supporting = [
        c
        for c in citations
        if c.get("posture") == "supporting" and c.get("adjudication_state") == "published"
    ]
    field_failure_count = dossier.get("field_failure_count", 0)

    if not supporting:
        return (
            "insufficient_evidence",
            "No published, supporting causal citation exists for this "
            "candidate; there is no positive evidentiary basis for a "
            "redesign recommendation.",
        )

    strongest = max(supporting, key=lambda c: _STRENGTH_RANK.get(c.get("strength_band"), 0))
    single_weak_confounded = (
        len(supporting) == 1
        and strongest.get("strength_band") == "weak"
        and bool(strongest.get("confounders_unaddressed"))
    )

    if field_failure_count < GATE_FIELD_FAILURE_FLOOR and single_weak_confounded:
        return (
            "no_action_indicated",
            f"Field-failure count ({field_failure_count}) is below the "
            f"{GATE_FIELD_FAILURE_FLOOR}-event floor this program treats as a "
            "meaningful pattern, and the only supporting citation is weak "
            "with unaddressed confounders.",
        )

    if strongest.get("strength_band") == "weak" or bool(strongest.get("confounders_unaddressed")):
        confounders = strongest.get("confounders_unaddressed") or []
        qualifier = (
            f"with unaddressed confounders ({', '.join(confounders)})"
            if confounders
            else "without a stronger corroborating citation"
        )
        return (
            "monitor_and_reassess",
            "The gate's cost, priority, and completeness thresholds are met, "
            f"but the strongest supporting citation is rated "
            f"{strongest.get('strength_band')!r} {qualifier} -- passing the "
            "gate is not the same as the evidence being strong.",
        )

    return (
        "redesign_warranted_for_evaluation",
        "The gate passed on every condition and the strongest supporting "
        f"citation is rated {strongest.get('strength_band')!r} with no "
        "unaddressed confounders.",
    )


def _template_sections(
    *,
    candidate: dict,
    dossier: dict,
    impact_snapshot: dict,
    cost_estimate: dict,
    limitations: list[str],
    stance_basis: str,
) -> list[dict]:
    """Fixed f-string prose, plugging in only carried figures. This is the
    fallback path -- see module docstring -- and is expected to be the
    path actually exercised in this build environment (no AI Gateway
    credentials present).
    """
    niin = candidate.get("niin", "unknown NIIN")
    nomenclature = candidate.get("nomenclature")
    citations = dossier.get("causal_citations", [])
    supporting = [c for c in citations if c.get("posture") == "supporting"]
    citation_line = (
        "; ".join(
            f"{c.get('failure_mode_code', 'unspecified failure mode')} "
            f"({c.get('strength_band', 'unknown')} strength, "
            f"{c.get('adjudication_state', 'unknown')})"
            for c in supporting
        )
        or "no supporting citation on record"
    )

    evidence_summary = (
        f"{niin}" + (f" ({nomenclature})" if nomenclature else "") + " has "
        f"{dossier.get('field_failure_count', 0)} recorded field failures and "
        f"{len(supporting)} supporting causal citation(s): {citation_line}."
    )

    point_estimate = cost_estimate.get("point_estimate_usd")
    cost_line = (
        f"Parametric point estimate: ${point_estimate:,.0f}."
        if isinstance(point_estimate, int | float)
        else "No point estimate on record."
    )
    completeness_ratio = impact_snapshot.get("completeness_ratio")
    completeness_clause = (
        f" Dependency-graph completeness is {completeness_ratio:.0%}"
        if isinstance(completeness_ratio, int | float)
        else " Dependency-graph completeness is unrecorded"
    )
    is_bounded_below = impact_snapshot.get("is_bounded_below")
    bounded_clause = ", and this is a bounded-below estimate." if is_bounded_below else "."
    impact_line = completeness_clause + bounded_clause

    return [
        {"heading": "Evidence Summary", "body": evidence_summary},
        {"heading": "Cost and Impact", "body": cost_line + impact_line},
        {"heading": "Limitations", "body": " ".join(limitations)},
        {"heading": "Recommendation Basis", "body": stance_basis},
    ]


async def _try_ai_gateway(prompt_context: dict) -> list[dict] | None:
    """Attempt the Domino AI Gateway. Returns `None` on ANY failure --
    unset config, network error, bad response shape -- so the caller
    always has a safe, unconditional fallback. Never raises.
    """
    base_url = os.environ.get("DESIGN_ADVISORY_AI_GATEWAY_URL")
    if not base_url:
        return None
    api_key = os.environ.get("DESIGN_ADVISORY_AI_GATEWAY_API_KEY")

    system_prompt = (
        "You write short, plain-English sections for a redesign-case "
        "narrative read by Navy design engineers. You are given a fixed "
        "set of carried figures as JSON. Use ONLY the numbers in that "
        "JSON -- never state a dollar figure, percentage, or count that is "
        "not present verbatim in the input. Do not recommend a course of "
        "action or state a stance; a stance has already been decided "
        "outside of you and is provided only as context. Respond with a "
        'JSON object of the exact shape {"sections": [{"heading": "...", '
        '"body": "..."}, ...]} with 2-3 sections such as "Evidence '
        'Summary", "Cost and Impact", "Limitations".'
    )
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=_AI_GATEWAY_TIMEOUT_S) as client:
            response = await client.post(
                base_url,
                headers=headers,
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": json.dumps(prompt_context)},
                    ],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            body = response.json()
        content = body["choices"][0]["message"]["content"]
        sections = _parse_and_validate_sections(content)
    except Exception:
        logger.warning(
            "AI Gateway narrative composition failed; falling back to template", exc_info=True
        )
        return None
    return sections


def _parse_and_validate_sections(content: str) -> list[dict]:
    """Raise (any exception, caught by the caller) if the model's response
    isn't the exact `{"sections": [{"heading": ..., "body": ...}, ...]}`
    shape this module requires -- separated out so `_try_ai_gateway`'s own
    `try` block never raises directly, only calls something that can.
    """
    parsed = json.loads(content)
    sections = parsed["sections"]
    if not isinstance(sections, list) or not sections:
        raise ValueError("AI Gateway returned no sections")
    for section in sections:
        if not isinstance(section, dict) or "heading" not in section or "body" not in section:
            raise ValueError("AI Gateway section missing heading/body")
    return sections


async def compose_narrative(
    *,
    candidate: dict,
    dossier: dict,
    impact_snapshot: dict,
    cost_estimate: dict,
    gate_decision: dict,
    limitations: list[str],
    evidence_gaps: list[str],
) -> dict:
    """Compose the narrative for a case whose gate has already passed.

    Returns `{"narrative_sections": [...], "suggested_stance": str,
    "suggested_stance_basis": str}`. Raises `ValueError` if called for a
    candidate whose gate did not pass -- 42 §1.3's own model never drafts
    a case for a failed gate, and this function refuses to paper over a
    caller mistake rather than silently composing a narrative for one.
    """
    if gate_decision.get("decision") != "pass":
        raise ValueError(
            "compose_narrative must never be called for a candidate whose "
            "gate has not passed (42 §1.3) -- this is a caller error, not a "
            "demo path this function should itself accommodate."
        )

    stance, stance_basis = _select_suggested_stance(dossier)

    prompt_context = {
        "niin": candidate.get("niin"),
        "nomenclature": candidate.get("nomenclature"),
        "field_failure_count": dossier.get("field_failure_count"),
        "supporting_citations": [
            {
                "failure_mode_code": c.get("failure_mode_code"),
                "strength_band": c.get("strength_band"),
                "adjudication_state": c.get("adjudication_state"),
                "narrative_summary": c.get("narrative_summary"),
            }
            for c in dossier.get("causal_citations", [])
            if c.get("posture") == "supporting"
        ],
        "point_estimate_usd": cost_estimate.get("point_estimate_usd"),
        "completeness_ratio": impact_snapshot.get("completeness_ratio"),
        "is_bounded_below": impact_snapshot.get("is_bounded_below"),
        "condition_results": gate_decision.get("condition_results"),
        # Carried so the model never writes prose that contradicts a gap
        # already on record -- it is not asked to restate these verbatim,
        # `agent/derive.py`'s own output already does that in the UI.
        "derived_evidence_gaps": evidence_gaps,
        # Context only -- the model is never asked to choose this, only to
        # write prose consistent with a stance already decided in code.
        "stance_decided_outside_this_prompt": stance,
    }

    sections = await _try_ai_gateway(prompt_context)
    used_path = "ai_gateway"
    if sections is None:
        used_path = "template"
        sections = _template_sections(
            candidate=candidate,
            dossier=dossier,
            impact_snapshot=impact_snapshot,
            cost_estimate=cost_estimate,
            limitations=limitations,
            stance_basis=stance_basis,
        )
    else:
        # The model wrote Evidence Summary / Cost and Impact / Limitations
        # prose from the carried context; the stance *basis* itself stays
        # ours, in code -- never delegated to the model's own account of
        # why a stance it never picked was picked.
        sections = [*sections, {"heading": "Recommendation Basis", "body": stance_basis}]

    logger.info("narrative composed via %s path for niin=%s", used_path, candidate.get("niin"))

    return {
        "narrative_sections": sections,
        "suggested_stance": stance,
        "suggested_stance_basis": stance_basis,
    }
