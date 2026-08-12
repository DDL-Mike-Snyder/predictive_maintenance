"""Michael's rule-based derivation logic (`docs/demo/redesign-case-builder-demo-plan.md`
"Michael" section, task 1 -- a demo-scoped stand-in for
`docs/build/42-redesign-case-builder.md` §4.5's real evidence-gap/
limitation derivation).

These two functions are the deterministic half of the agent's job. 42
§1.3's Carried/Derived/Composed table is explicit that evidence gaps and
limitations are DERIVED -- plain, auditable, non-LLM code -- never
composed by the language model. `agent/narrative.py` calls these and
hands their *output* to the model as carried context; the model is never
allowed to invent its own gap/limitation text, and never sees the raw
dossier/impact-snapshot rows directly.

Both functions are contractually non-empty. This mirrors 28 §3.6's real
schema constraint on `recommendation_limitations`/
`recommendation_evidence_gaps` (non-empty once a case is assembled), and
is also the whole ethical point of 42 §1.2 B4: the agent must never have
nothing to say. Neither function needs an explicit fallback branch to
satisfy this for this demo's own §1.5 seed data -- every one of the five
seed candidates has at least one truncated/incomplete impact snapshot
(`is_bounded_below` is always true in the seed data) and at least one
citation, so rule 3 of each function always fires -- but each still ends
with the general case handled honestly rather than assuming the seed
data's shape holds for inputs nobody has seeded yet.
"""

from __future__ import annotations

_STRENGTH_RANK = {"strong": 3, "moderate": 2, "weak": 1, "insufficient": 0}


def derive_evidence_gaps(dossier: dict, impact_snapshot: dict) -> list[str]:
    """Deterministic evidence-gap derivation.

    Rules, in the order given by the build plan:
      1. Every `test_coverage` row whose `record_status` starts with
         `"absent"` contributes one gap naming the test kind and its
         `absence_basis` (28 §3.2/§3.3.2).
      2. Every citation with `posture == "contra"` contributes the fixed
         warning below -- 28 §3.3.1's rule that a contra citation is
         never counted as supporting evidence, stated so a reader knows
         one was examined and rejected, not silently omitted.
      3. If the impact snapshot is `is_bounded_below`, one gap states the
         real `completeness_ratio` and flags the traversal as truncated
         or incomplete (42 §4.3's whole point -- never bury this).

    Always returns a non-empty list.
    """
    gaps: list[str] = []

    for row in dossier.get("test_coverage", []):
        record_status = row.get("record_status", "")
        if record_status.startswith("absent"):
            test_kind = row.get("test_kind_code", "an unspecified test")
            basis = row.get("absence_basis") or "no basis on record"
            gaps.append(f"No usable test record for {test_kind} ({record_status}): {basis}")

    for citation in dossier.get("causal_citations", []):
        if citation.get("posture") == "contra":
            gaps.append(
                "A contradicting causal hypothesis was also examined for this "
                "failure mode and is not counted as supporting evidence."
            )

    if impact_snapshot.get("is_bounded_below"):
        ratio = impact_snapshot.get("completeness_ratio")
        ratio_text = f"{ratio:.0%}" if isinstance(ratio, int | float) else "an unknown fraction"
        gaps.append(
            "Dependency-graph traversal was truncated or incomplete -- only "
            f"{ratio_text} of the graph has been verified "
            f"(completeness_ratio={ratio!r})."
        )

    if not gaps:
        gaps.append(
            "No specific evidence gaps were identified by rule for this "
            "candidate; treat this as a preliminary, rule-based assessment "
            "rather than an exhaustive audit of the underlying evidence."
        )

    return gaps


def derive_limitations(cost_estimate: dict, dossier: dict) -> list[str]:
    """Deterministic limitation derivation.

    Rules, in the order given by the build plan:
      1. Any citation with a non-empty `confounders_unaddressed` list
         contributes a limitation listing them **verbatim** -- 42's core
         non-negotiable rule (§1.2 B4 / §1.3): confounders are never
         summarized or softened away.
      2. If `cost_estimate["is_lower_bound"]`, one limitation states that
         plainly, citing the real `coverage_ratio`.
      3. Always: one generic limitation naming the `strength_band` of the
         weakest *supporting* citation, so a reader never mistakes a
         passed gate for strong evidence -- the entire point of candidate
         #5 in §1.5, and the reason this rule has no "skip if strong"
         escape hatch.

    Always returns a non-empty list (rule 3 always contributes exactly
    one item, even with zero supporting citations).
    """
    limitations: list[str] = []

    for citation in dossier.get("causal_citations", []):
        confounders = citation.get("confounders_unaddressed") or []
        if confounders:
            failure_mode = citation.get("failure_mode_code", "this failure mode")
            confounder_list = "; ".join(confounders)
            limitations.append(f"Confounders not addressed for {failure_mode}: {confounder_list}")

    if cost_estimate.get("is_lower_bound"):
        coverage_ratio = cost_estimate.get("coverage_ratio") or 0.0
        limitations.append(
            "This cost estimate is a lower bound -- it reflects only the "
            f"{coverage_ratio:.0%} of the dependency graph that has been verified."
        )

    citations = dossier.get("causal_citations", [])
    supporting = [c for c in citations if c.get("posture") == "supporting"]
    if supporting:
        weakest = min(supporting, key=lambda c: _STRENGTH_RANK.get(c.get("strength_band"), 0))
        limitations.append(
            "The weakest supporting citation for this candidate has "
            f"strength_band={weakest.get('strength_band')!r} -- a passed gate "
            "reflects cost, priority, and completeness thresholds, not "
            "evidentiary strength."
        )
    else:
        limitations.append(
            "No supporting causal citation exists for this candidate; any "
            "recommendation here rests on the other gate inputs alone."
        )

    return limitations
