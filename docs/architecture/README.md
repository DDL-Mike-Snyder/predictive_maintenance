# FATHOM Architecture Documentation

FATHOM — Fleet Asset Tracking, Health & Operational Maintenance — is a Navy multi-domain predictive-maintenance and fleet-sustainment platform spanning surface, subsurface, and unmanned assets.

Architecture is being developed in three approval-gated phases:

| Phase | Scope | Status |
|---|---|---|
| 1 | High-level system architecture | **Approved** |
| 2 | High-level architecture per sub-application | Draft — pending approval |
| 3 | Detailed architecture, one sub-application at a time | Not started |

## Documents

| Document | Phase | Contents |
|---|---|---|
| [01 — System Architecture](01-system-architecture.md) | 1 | Plane model, nine-sub-application decomposition, shared kernel, tiered modeling contract, agentic layer, Kubernetes deployment, off-ramp seams, Navy domain grounding |
| [02 — Domino Platform Assessment](02-domino-platform-assessment.md) | 1 | Primary-source assessment of Domino capability; the basis for every platform-boundary decision in document 01; the specific Domino changes required for Domino to host the entire program |
| [03 — Integration Contracts](03-integration-contracts.md) | 2 | API conventions, event backbone and catalog, shared payload schemas, the substitution protocol and conformance suites, edge reconciliation policy, agent tool binding |
| [04 — Sub-Application Architectures](04-subapplication-architectures.md) | 2 | High-level architecture for each of the nine sub-applications and the platform layer; recommended Phase 3 sequence |
| [05 — Architecture Review Findings](05-architecture-review-findings.md) | 2 | Register of 51 consistency findings and 37 design findings from adversarial review, with disposition per finding and the remediation sequence |
| [06 — Demonstration Decisions and Assumptions](06-demo-decisions-and-assumptions.md) | 2 | Resolves the six open decisions from document 05. Records each decision, the assumption it rests on, and the alternative if the assumption fails. Contains the capacity model, the consolidated assumption register, and the mapping from assumptions to program requirements if funded |

## Reading order

Document 01 is the architecture of record; document 02 supplies its evidence and governs §3 and §12 of it.

Document 03 is binding on document 04 and on all Phase 3 design. Where the two conflict, document 03 prevails.

Document 05 governs all four. Findings recorded there are open until the cited document changes or a decision is recorded; remediation is in progress and its sequence is document 05 §5.

## Remediation status

| Tranche | Scope | Status |
|---|---|---|
| 1 | Document 03 contract fixes | **Complete** (rev 2) |
| 2 | Document 01 fixes | Pending |
| 3 | Document 04 fixes, including event-catalog reconciliation | Pending |
| 4 | Document 02 fixes | Pending |
| 5 | The six decisions in document 05 §4 | **Decided** — recorded in document 06 |
| 6 | Capacity model | **Decided** — document 06 §7, provisional pending Navy data-systems research |

Phase 3 detailed design should not begin before tranches 1–4 are complete and the document 05 §4 decisions are recorded.

## Handling

Both documents are **internal**. Document 02 cites unreleased roadmap material, unsigned product requirements documents, and internal engineering discussion, and is not for external or customer distribution.
