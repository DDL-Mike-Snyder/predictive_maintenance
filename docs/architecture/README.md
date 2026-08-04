# FATHOM Architecture Documentation

FATHOM — Fleet Asset Tracking, Health & Operational Maintenance — is a Navy multi-domain predictive-maintenance and fleet-sustainment platform spanning surface, subsurface, and unmanned assets.

Architecture is being developed in three approval-gated phases:

| Phase | Scope | Status |
|---|---|---|
| 1 | High-level system architecture | Draft rev 3 — pending approval |
| 2 | High-level architecture per sub-application | Not started |
| 3 | Detailed architecture, one sub-application at a time | Not started |

## Documents

| Document | Contents |
|---|---|
| [01 — Phase 1 System Architecture](01-system-architecture.md) | Plane model, nine-sub-application decomposition, shared kernel, tiered modeling contract, agentic layer, Kubernetes deployment, off-ramp seams, Navy domain grounding |
| [02 — Domino Platform Assessment](02-domino-platform-assessment.md) | Primary-source assessment of Domino capability; the basis for every platform-boundary decision in document 01; the specific Domino changes required for Domino to host the entire program |

## Reading order

Document 01 is the architecture of record. Document 02 supplies its evidence and should be read alongside §3 and §12 of document 01, which it directly governs.

## Handling

Both documents are **internal**. Document 02 cites unreleased roadmap material, unsigned product requirements documents, and internal engineering discussion, and is not for external or customer distribution.
