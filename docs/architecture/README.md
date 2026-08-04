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
| [03 — Integration Contracts](03-integration-contracts.md) | 2 | Canonical identity and vocabulary, API conventions, event backbone and catalog, shared payload schemas, agent authority and tool surfaces, the substitution protocol and conformance suites, edge reconciliation, untrusted content, data remediation |
| [04 — Sub-Application Architectures](04-subapplication-architectures.md) | 2 | High-level architecture for each of the nine sub-applications and the platform layer; recommended Phase 3 sequence |
| [05 — Architecture Review Findings](05-architecture-review-findings.md) | 2 | Register of 51 consistency findings and 37 design findings from adversarial review, with disposition per finding and the remediation sequence |
| [06 — Demonstration Decisions and Assumptions](06-demo-decisions-and-assumptions.md) | 2 | Resolves the six open decisions from document 05. Records each decision, the assumption it rests on, and the alternative if the assumption fails. Contains the capacity model, the consolidated assumption register, and the mapping from assumptions to program requirements if funded |
| [07 — Navy Data Systems and Synthetic Data Schemas](07-navy-data-systems.md) | 2 | Schema-level documentation of the Navy systems this platform models — CDMD-OA/SCLSIS, 3-M, RSUPPLY, COSAL, FLIS, MILSTRIP — from public sources, with how each drives each sub-application, the synthetic-data identifier policy, and revised capacity figures |
| [08 — Standards Alignment](08-standards-alignment.md) | 2 | The military, federal, and commercial standards applying to each of the four cross-cutting items; what each requires; the consolidated compliance table; the do-not-cite list of cancelled and superseded documents; and the taxonomy anchoring decision |

## Reading order

Document 01 is the architecture of record; document 02 supplies its evidence and governs §3 and §12 of it.

Document 03 is binding on document 04 and on all Phase 3 design. Where the two conflict, document 03 prevails.

Document 05 governs all of them. Findings recorded there are open until the cited document changes or a decision is recorded; remediation is in progress and its sequence is document 05 §5.

## Remediation status

| Tranche | Scope | Status |
|---|---|---|
| 1 | Document 03 contract fixes | **Complete** (rev 2) |
| 2 | Document 01 fixes | **Complete** (rev 5) |
| 3 | Document 04 fixes, including event-catalog reconciliation | **Complete** — reconciliation verified by `tools/check_event_catalog.py` |
| 4 | Document 02 fixes | **Complete** |
| 5 | The six decisions in document 05 §4 | **Decided** — recorded in document 06 |
| 6 | Capacity model | **Decided** — document 06 §7, provisional pending Navy data-systems research |

Tranches 1–4 are complete and the six decisions are recorded, so Phase 3 detailed design is unblocked on the review findings. The remaining prerequisites are the four cross-cutting items in document 04 §12, now with standards backing in document 08.

`tools/check_event_catalog.py` reconciles the document 03 event catalog against document 04's declarations in both directions and exits non-zero on any discrepancy. Run it from the repository root after editing either document.

## Standards posture

Document 08 carries the compliance position. Three items there are program actions rather than engineering ones and have lead time: a **written authorizing-official determination of NSS status** (which settles IL4-versus-IL5 and federal AI-policy applicability in one memo), **purchase of ISO 14224:2016** (Annex B is the taxonomy anchor's deliverable content and has no free substitute), and **re-baselining the 3-M code sets** against the current NAVSEAINST 4790.8 revision.

## Handling

All documents are **internal**. Document 02 in particular cites unreleased roadmap material, unsigned product requirements documents, and internal engineering discussion, and is not for external or customer distribution.

Documents 07 and 08 rest entirely on public sources and mark every unverified claim as such. Neither reproduces controlled content, but the schema catalogue in document 07 is the kind of artifact that attracts a Controlled Technical Information determination — see document 08 §5.4 before distributing either outside the program.
