# 0002 — `audit` → object store NetworkPolicy edge

## Status

Accepted.

## Context

`32-audit.md` retains oversized attestation and provenance records by reference rather than inline, the same pattern document 03 §5.1 establishes for large prediction result sets (`[D27]`) — a `payload_ref` pointing at object storage rather than an inline blob in the audit database. `11-outbox-sync-library.md` §10.1 states the governing rule for every service that does this: "`payload_ref` objects are encrypted with the same KEK class. A reference is not an exemption." Audit's own oversized records are subject to the same rule, and enforcing it requires `audit` to reach the object store directly — to write the encrypted reference payload and, during a purge, to delete it rather than merely dropping a database row that pointed at it.

No sub-application had a NetworkPolicy edge to the object store; document 01 §11's default-deny plus `09-monorepo-and-conventions.md` §4.4.2's sanctioned-edge table did not anticipate a service other than the object-store-backed platforms (Knowledge & Retrieval, Tool Server evidence handling) needing this edge, and audit's need was discovered while writing `32-audit.md`, not anticipated in Wave 1.

## Decision

Add `audit` → object store as a sanctioned NetworkPolicy edge, scoped to `audit` only. Audit writes and deletes its own oversized referenced records directly; it does not proxy through another service's object-store access, and no other domain sub-application gains this edge as a side effect of this decision.

## Consequences

- `docs/build/09-monorepo-and-conventions.md` §4.4.2's sanctioned-edge table gains this row (amendment 09-1); rendered via `networkPolicy.egress.toObjectStore` (amendment 09-3), `false` by default and rejected as `true` outside `audit`'s chart.
- Physical deletion on purge (as opposed to crypto-shred) is the correct remediation for this store, following the same reasoning `03-integration-contracts.md` §13 item 5 already applies to the vector index: an object-store reference is not shredded by destroying a key if the object itself remains reachable by anyone still holding the reference. Audit's `POST /{slug}/remediations` purge path for this store performs deletion, not shredding.
- The helm-unittest egress-equality assertion (§4.4.1, §8.6) applies unchanged.
