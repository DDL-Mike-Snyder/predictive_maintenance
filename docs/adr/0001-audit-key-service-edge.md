# 0001 — `audit` → key service (Vault/HSM) NetworkPolicy edge

## Status

Accepted.

## Context

Document 01 §11 and `09-monorepo-and-conventions.md` §4.4.2 establish a default-deny NetworkPolicy in which the only permitted egress for the nine domain sub-applications is to their own database, the event bus, and `auth`/`audit`/`reference-data`. No sub-application, including `audit`, was permitted an edge to a key-management service.

`32-audit.md` §5.2 Decision 2 establishes that crypto-shred purge and rewrap require an entity holding wrap/unwrap authority over per-classification KEKs and purge-group shred nonces, and that this authority is never exported to the services encrypting under those keys — each service calls `emit()` (`11-outbox-sync-library.md` §2.3), which wraps and unwraps locally against a key handle, but the root authority to mint, rewrap, or destroy a key class or a shred nonce sits with the key service alone. Audit is the component that executes a purge or rewrap once a `security_officer`-adjudicated `Proposal` (document 03 §7.2.1, amendment 03-1/03-2) approves one — via `POST /{slug}/remediations` (document 03 §15 obligation 17) on every sub-application it owns a purge path for, and via the key service directly for the shred/rewrap operation itself. Without an egress edge to the key service, `audit` cannot execute the one operation its entire build document exists to specify.

## Decision

Add `audit` → key service (Vault/HSM) as a sanctioned NetworkPolicy edge, scoped to `audit` only. No other sub-application receives this edge; each of the nine domain services continues to reach the key service only indirectly, through the `emit()`/inbox wrap-unwrap calls that `11-outbox-sync-library.md` performs against a locally cached key handle, never against the key service's administrative surface.

## Consequences

- `docs/build/09-monorepo-and-conventions.md` §4.4.2's sanctioned-edge table gains this row (amendment 09-1); the rendered egress peer set for `audit`'s Helm chart includes it via the `networkPolicy.egress.toKeyService` boolean (amendment 09-3), which is `false` by default and rejected as `true` on any chart other than `audit`'s.
- The helm-unittest assertion that the rendered egress peer set equals the values-declared set (§4.4.1, §8.6) applies unchanged — this edge is not an exemption from that invariant, only an addition to the declared set for one service.
- A future service requiring the same edge (a second component with purge authority) requires its own ADR; this decision does not generalize the edge to "any service with a documented need."
