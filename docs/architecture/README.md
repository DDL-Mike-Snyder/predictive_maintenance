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

## Reading order

Document 01 is the architecture of record; document 02 supplies its evidence and governs §3 and §12 of it.

Document 03 is binding on document 04 and on all Phase 3 design. Where the two conflict, document 03 prevails.

## Handling

Both documents are **internal**. Document 02 cites unreleased roadmap material, unsigned product requirements documents, and internal engineering discussion, and is not for external or customer distribution.
