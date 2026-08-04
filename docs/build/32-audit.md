# Build Framework 32 — Audit & Provenance Platform Service

| | |
|---|---|
| **Status** | Draft rev 1. Binding on the `audit` platform service, and — through §6.4, §6.5, and §11.3 — on **every other sub-application and platform service in the system** |
| **Scope** | The `audit` platform service: the immutable, append-only, correlated record of predictions, tags, proposals, adjudications, agent tool invocations, model and agent promotions, and the complete event envelope of every catalogued event; **and the system-wide data-remediation machinery that makes finding D15 closeable** — envelope-level encryption with a declared key hierarchy, the crypto-shred purge protocol across every store, tombstone semantics for compacted topics, and cross-repository ship/shore correlation |
| **Derived from** | [03 — Integration Contracts](../architecture/03-integration-contracts.md) §5.4, §6, §7.3, §8.5, §13, §15 · [04 — Sub-Application Architectures](../architecture/04-subapplication-architectures.md) §11 · [05 — Review Findings](../architecture/05-architecture-review-findings.md) **D15**, D13, D12, D29 · [08 — Standards Alignment](../architecture/08-standards-alignment.md) §3.3, §3.5, §3.6, §5.5, §7 · [09 — Monorepo & Conventions](09-monorepo-and-conventions.md) · [10 — Shared Packages](10-shared-packages.md) §4.5, §4.8 · [11 — Outbox & Sync Library](11-outbox-sync-library.md) §4, §5, §10, §11 |
| **Precedence** | Document 03 prevails on any contract surface. Document 09 prevails on layout, stack, and conventions. Document 11 prevails on outbox, inbox, clock, and reconciliation mechanism. This document prevails on remediation, key management, purge, and audit-record structure — including where that means **adding** a contract term to document 03 (§16) |
| **Control basis** | Every NIST citation in this document is grounded in **document 08 §3.5** (CP-10(2), AU-4(1), AU-6(3), AU-9(3), AU-10, AU-12(1), SC-8/SC-8(1), SC-16, SC-28/SC-28(1)) or **document 08 §3.3** (SC-45, SC-45(1) as DoD Zero Trust Overlays tailoring additions, with the 1 ms / daily / 1 s parameters). **No other control is cited.** Per document 08 §7, **AU-8(1) and AU-8(2) are withdrawn and are never cited** |
| **Verification note** | Product names in §5.5 are plausible selections against the posture document 08 establishes, **not settled facts**. FIPS 140-3 certificate numbers, CMVP validation status, and DoD Impact Level authorization for any named product must be verified against the CMVP validated-modules list and the DoD Cloud Catalog at implementation time |
| **Classification** | Internal |

---

## 0. How to read this document, and why it exists at all

Finding **D15** is dispositioned FIX and is described in document 05 §2.4 as an **accreditation blocker**:

> **D15** ⚠ HIGH — **No purge path, so a classification spillage is unrecoverable.** Remediation would require deletion from an immutable audit store, nine read models, append-only tag stores, indefinitely compacted topics, every inbox and outbox, the vector index, object-store evidence, and Domino traces. Several stated invariants forbid it. This is an accreditation blocker.

Document 03 §13 converts that finding into four obligations. Read it in full before reading further; it is short, and it is largely this document's specification:

1. **Envelope-level encryption with per-classification keys.** Crypto-shredding a key is the purge mechanism where physical deletion is impossible.
2. **A declared purge protocol** covering every store, including Domino-side traces and gateway-held read models, with an owner and a tested procedure.
3. **An explicit statement per store** of whether it is legally immutable or operationally append-only. The two require different remediation.
4. **Tombstone semantics for compacted topics** that preserve the compaction invariant.

Document 03 §13 closes: *"This is an accreditation prerequisite, not a refinement."*

**Three things follow, and they set this document's shape.**

**First, the tension is real and must be resolved, not narrated.** Document 04 §11 defines this service as an *"immutable, append-only record… an accreditation artifact."* Document 03 §11 makes anomaly tags *"append-only; never overwritten or deleted"* and maintenance action records *"edge-authoritative, append-only."* Document 11 §8.4 refuses to rewrite a published event for three independent reasons, one of which is D15 itself. This service is therefore the store that most resists remediation *by design*, and it is simultaneously the store that must remediate. If the resolution here is weak, the platform has no spillage-remediation story anywhere — because every other store's remediation is coordinated from here.

The resolution, stated once and then specified: **nothing in the append-only store is ever modified or deleted. Purge is the destruction of key material held outside that store, in a hardware security module. The record survives; its readability does not.** Everything in §5 and §6 is the mechanics of making that provable rather than merely asserted.

**Second, this service is the one that makes obligation 9 satisfiable for everybody else.** Document 03 §15 obligation 9 binds every implementation, including substitutes: *"Records provenance for every derived value it publishes — inputs, versions, and computation reference — sufficient to trace any operator-visible figure to its sources."* No sub-application can satisfy that alone, because a derived value's inputs are other sub-applications' outputs, and document 03 principle 2 forbids the synchronous calls that would let a service walk the chain itself. The provenance graph in §4.5 is the shared substrate. A sub-application discharges obligation 9 by writing edges here; the closure query in §10.4 is what makes the obligation *observable*.

**Third, `sync_quality` lives or dies here.** Document 03 §5.4: *"`sync_quality` is retained permanently… it is the only way to re-derive true ordering after the fact. Without it that information is gone. Skew is indistinguishable from tampering to an assessor, and non-repudiation claims collapse if the time is contestable."* Document 11 §10.5 exports it to Audit before an outbox row becomes prunable, and document 11 §13 open question 10 asks this document to confirm that Audit accepts a per-event attestation at full event volume. §4.4 and §16.2 answer it.

Three markers are used, following document 09 §1.3:

- **[03 §n]**, **[08 §n]**, **[11 §n]** — dictated by the cited document. Not negotiable at implementation time.
- **[ESTABLISHED HERE]** — the architecture documents do not specify this. This document decides, and states why.
- **[AMENDMENT REQUIRED]** — this document's design needs a change to a document upstream of it. Every instance is consolidated in §16 with the exact edit. **An implementer follows this document and does not wait**, but the amendment is a release-blocking item because document 03 is what binds substitutes.

---

## 1. Purpose and scope

### 1.1 What this service is

Per document 04 §11:

> **Audit & Provenance.** Immutable, append-only record of predictions, tags, proposals, adjudications, agent tool invocations with full request and response, and model and agent version promotions. Correlated by `X-Correlation-Id` and by `trace_ref` to Domino agent traces. This is an accreditation artifact and its retention and integrity requirements should be treated as external obligations rather than internal preferences.

Concretely, five responsibilities:

| # | Responsibility | Source |
|---|---|---|
| 1 | **The correlated record.** Every prediction, tag, proposal, adjudication, tool invocation, model binding, agent promotion, and clock-step observation, correlated by `correlation_id`, `causation_id`, and `trace_ref` | 04 §11, 03 §8.5, 11 §4.5 |
| 2 | **The complete event envelope of every catalogued event**, including the whole `clock` block and its `sync_quality` attestation, retained permanently | 03 §5.4, 11 §10.5 |
| 3 | **The provenance graph.** The input→derived edge set that makes document 03 §15 obligation 9 satisfiable and that makes `ClassificationLabel.inherited_from[]` auditable rather than decorative | 03 §7.3, §15.9 |
| 4 | **Non-repudiation.** Verification and permanent retention of producer signatures over records and their clock attestations, plus an independent admission countersignature and hash chain | AU-10, AU-9(3) [08 §3.5] |
| 5 | **The remediation authority.** Owner of the key hierarchy, the purge protocol, the purge closure computation, the cross-store coordination, and the purge certificate | 03 §13 [D15] |

Responsibility 5 is what makes this a substantial Phase 3 design rather than a log sink, and it is why this document is disproportionately about remediation.

### 1.2 What this service is not

| Not | Because | Where it lives |
|---|---|---|
| **An operational log aggregator** | Structured JSON to stdout with `correlation_id` on every line is document 09 §4.8's concern and goes to the cluster's log stack. Audit records are *domain* records with signatures, classification labels, and retention obligations — a different lifecycle entirely | 09 §4.8 |
| **A metrics or tracing backend** | OpenTelemetry is instrumented-but-off (09 §2.2) and `X-Correlation-Id` is the contractual correlation mechanism. `trace_ref` here is a *reference into* Domino's tracing, not a copy of it | 09 §2.2, 03 §8.5 |
| **A query surface for domain state** | Consumers maintain read models from events; agents obtain state through tools. Audit answers *what happened and where did this figure come from*, never *what is true now* | 03 principle 2 |
| **An agent tool surface** | **No audit operation is `x-agent-eligible`.** See §14 item 9 for the reasoning; it is a D13 aggregation channel and a D14 amplifier, and the prohibition is deliberate | [ESTABLISHED HERE] |
| **The taxonomy, model, or agent registry** | Reference Data owns the vocabulary; Domino owns model artifacts; PdM owns bindings. Audit records the *promotion and binding events*, not the artifacts | 03 §14 |
| **A cross-domain guard** | Cross-level flow occurs only through an accredited guard (03 §5.1, §12). Audit enforces the target level and refuses; it never transforms | 03 §12, D13 |

### 1.3 Deployment profile

**Audit has an edge profile, and this is load-bearing.** Document 03 §11 grows the afloat profile to edge-authoritative maintenance action records and edge-resident candidate generation (document 06 §4). Those actions produce provenance and tool invocations while the hull is dark. If audit were shore-only, the highest-consequence records in the system — a submarine's six weeks of maintenance actions, its agent tool calls, its clock-step observations — would have no accountability record at the moment they were created, and would be reconstructed ashore by someone who was not there. That is D8's failure mode wearing a compliance badge.

| Profile | `producer_node` [03 §5.4] | Runs |
|---|---|---|
| **Enterprise** | `enterprise` | The authoritative repository. Holds the union after reconciliation |
| **Edge** | `edge:<asset_id>` | One instance per edge-profiled hull. Its own database, its own outbox, its own monotonic sequence, its own HSM partition (§5.11). **Never merged into the enterprise store — correlated, per §9** |

The two repositories are **correlated, not merged**. AU-6(3) [08 §3.5] is *"correlate ship and shore repositories"*, and §9 specifies the mechanism. A merge would require rewriting `producer_node` and `monotonic_seq`, which document 11 §8.4 prohibits for reasons that terminate in D15.

---

## 2. Traceability

Every requirement this document discharges, with the section that discharges it. A reviewer should be able to check this table and stop.

| Source | Requirement | Discharged in |
|---|---|---|
| 03 §13.1 | Envelope-level encryption with per-classification keys; crypto-shred as the purge mechanism | §5.2–§5.8 |
| 03 §13.2 | A declared purge protocol covering every store, with an owner and a tested procedure | §6, §12.2 |
| 03 §13.3 | An explicit statement per store of legally immutable versus operationally append-only | §4.1, §6.3 |
| 03 §13.4 | Tombstone semantics for compacted topics preserving the compaction invariant | §7 |
| 03 §7.3 | `ClassificationLabel` with `inherited_from[]`; the provenance-inheritance obligation | §4.2, §4.5 |
| 03 §15.9 | Provenance for every derived value, traceable to sources | §4.5, §10.4 |
| 03 §15.4 | Classification labels on every response and event; inheritance on derived values | §4.2, §10, §11 |
| 03 §5.4 | Full envelope including `clock` and permanent `sync_quality` retention | §4.4, §8.3 |
| 03 §6 | Broad consumption; `audit` named as consumer in seven catalog rows and required for many more | §11.2, §16.1 |
| 03 §8.5 | Tool invocations with full request and response, correlated by `trace_ref` | §4.3 |
| 03 §8.3 | Accountable-autonomous runs recorded with the accountable human owner | §4.3 |
| 04 §11 | Immutable append-only record; correlation by `X-Correlation-Id` and `trace_ref`; accreditation artifact | §4, §8, §9 |
| 05 D15 | A purge path exists for every store | §5, §6, §7 |
| 05 D13 | No post-filtering; label inheritance; aggregation is a classification event | §10.6, §14.7 |
| 05 D29 | Skew auditable rather than invisible | §4.4, §8.3, §9.4 |
| 08 §3.5 | CP-10(2), AU-4(1), AU-6(3), AU-9(3), AU-10, AU-12(1), SC-8/(1), SC-16, SC-28/(1) | §15.6, and inline |
| 08 §3.3 | SC-45/SC-45(1); 1 ms granularity, daily comparison, 1 s resync | §4.4, §8.3 |
| 11 §10.5 | `sync_quality` exported to Audit before an outbox row is prunable | §4.4 |
| 11 §13 OQ-10 | Confirm Audit accepts a per-event attestation at full event volume | §4.4, §16.2 |
| 11 §10.1 | `purge_by_selector` covering outbox, inbox, quarantine, object references | §6.3 |
| 09 §8 | The shared Definition of Done, reproduced and extended, nothing removed | §15 |

---

## 3. Position in the system

```
                    ┌──────────────────────────────────────────────┐
   every service ──▶│  outbox (11 §2)  ──relay──▶  Redpanda topics │
   (provenance and  └──────────────────────────────────────────────┘
    domain events)                     │
                                       │  audit subscribes to ALL of it (§11.2)
                                       ▼
        ┌────────────────────────────────────────────────────────────────┐
        │  audit                                                          │
        │                                                                 │
        │   ingest ──▶ verify signature ──▶ countersign ──▶ chain ──▶ DB  │
        │      │              │                                  │        │
        │      │              └── fail ──▶ quarantine + audit     │        │
        │      │                          (never a silent drop)   │        │
        │      ▼                                                  ▼        │
        │   encrypt under R-DEK ◀── HSM Wrap ──── key hierarchy (§5)      │
        │                                                                 │
        │   provenance graph · dissemination ledger · attestations        │
        │                                                                 │
        │   ┌─────────────────── Remediation Coordinator ──────────────┐  │
        │   │  purge proposal ▶ dual control ▶ closure ▶ quarantine ▶  │  │
        │   │  per-store purge ▶ HSM key destroy ▶ verify ▶ certify    │  │
        │   └──────────┬────────────────────────────────┬─────────────┘  │
        └──────────────┼────────────────────────────────┼────────────────┘
                       │ POST /remediations             │ fathom.audit.remediation.v1
                       │ (command, acknowledged)        │ (fact, discoverable)
                       ▼                                ▼
        nine sub-applications · gateway · knowledge-retrieval ·
        notification · tool-server · sync · Domino trace store · object store
```

Two edges in that diagram are new contract surface and are consolidated as amendments in §16:

- **`POST /api/v1/{slug}/remediations`** on every sub-application and platform service — the acknowledged command path. §6.4.
- **The dissemination report** from every consumer's inbox — how audit knows which stores hold a copy of a logical record. §4.6.

Without the second, purge closure across nine read models is guesswork, and a purge certificate that guesses is worthless to an assessor.

---

## 4. Data model

One logical database, `fathom-audit-pg`, per document 03 §15 obligation 13 and document 09 §2.3. Object storage (S3/MinIO per document 09 §2.1) holds oversized payloads by reference, encrypted under the same envelope as the inline case — document 11 §10.1's rule that *"a reference is not an exemption"* applies here verbatim.

### 4.1 Immutability class — the per-store, per-record-type declaration

Document 03 §13.3 requires **an explicit statement per store** of whether it is legally immutable or operationally append-only, *"because the two require different remediation."* Document 04 §11 calls this whole store "immutable, append-only," which is exactly the conflation the obligation exists to prevent. **This section makes the distinction per record type, and the classification is a stored column, not a convention.**

```python
class ImmutabilityClass(StrEnum):
    LEGALLY_IMMUTABLE      = "legally-immutable"
    OPERATIONALLY_APPEND_ONLY = "operationally-append-only"
```

The two differ in exactly one respect, and it is the respect that matters:

| | `operationally-append-only` | `legally-immutable` |
|---|---|---|
| Row mutated or deleted, ever | **No** | **No** |
| Content may become unreadable by design | **Yes** — crypto-shred (§5.8) | **No** — shred is refused at the API boundary |
| Spillage remediation | Purge the low-side copies; shred the canonical record | **Re-wrap upward and contain** (§5.10). The record is retained and readable to appropriately cleared holders; every lower-side copy is shredded |
| Who can order it | `security_officer` under dual control (§6.1) | The same, and the outcome is *never* destruction of the canonical record |

**The re-wrap is the whole resolution of the legal-immutability tension, and it deserves to be said plainly:** reclassifying a record upward is a change to *which key wraps its data-encryption key*, not a change to the record. The ciphertext is untouched, the signature still verifies, the hash chain is intact, and the record has become unreadable to everyone below the new level. A record can therefore be *both* legally immutable *and* remediable, which document 05 D15 assumes to be impossible and which is the reason it was dispositioned as a blocker.

**The declaration, per record type:**

| Record type | Class | Why |
|---|---|---|
| `event_ingest` — the full envelope of a catalogued event | operationally-append-only | Audit's copy is a derived record; the producer's outbox row and the topic are the origin. Shreddable |
| `prediction_recorded` | operationally-append-only | Derived, recomputable, no external legal effect |
| `tool_invocation` | operationally-append-only | Full request and response may contain retrieved corpus text (03 §9), which is exactly the untrusted, potentially-mislabeled content most likely to spill |
| `agent_run` (authority class, accountable owner, checkpoint) | operationally-append-only | Accountability metadata; content-free of domain payload |
| `attestation` — `sync_quality` and clock steps | operationally-append-only, **and never purged in practice** | Carries no domain payload, therefore no spillage risk. Retained permanently (03 §5.4). See §5.4 on its key-group treatment |
| `anomaly_tag_adjudication` | **legally-immutable** | Document 03 §11: anomaly tags are *"append-only; never overwritten or deleted; supersession recorded"* — *"human judgments are evidence"* |
| `maintenance_action_recorded` | **legally-immutable** | The 3-M record is the statutory maintenance record (document 07; NAVSEAINST 4790.8). Also the label stream for every model in the system (03 §6) |
| `proposal_adjudication` where the proposal `kind` has **external legal effect** (`requisition`) or `blast_radius` is `class`/`fleet` | **legally-immutable** | Document 03 §7.2: dual control is mandatory *"for any kind with external legal effect."* A destroyed adjudication of a legally effective act destroys the accountability for that act |
| `proposal_adjudication`, all other kinds | operationally-append-only | Item- and asset-scoped judgments with no external legal effect |
| `model_binding_activated`, `agent_promotion` | **legally-immutable** | Document 04 §11: *"an accreditation artifact."* Destroying the record of which model version served which tier destroys the accreditation basis |
| `purge_record`, `purge_receipt`, `purge_certificate` | **legally-immutable** | A purge must remain auditable forever (§6.6). Also: they live in their own purge group so no key destruction can reach them (§5.4) |
| `integrity_checkpoint` | **legally-immutable** | The chain's anchors. Destroying one destroys the proof that nothing else was destroyed |
| `quarantine_record` | operationally-append-only | A record that failed signature verification is quarantined, never dropped (11 §10.2) — and quarantine is exactly where hostile or mislabeled content accumulates |

A `legal_hold` boolean is additionally settable per record and per closure. **A legal hold is a hard refusal, not a warning**: a purge whose closure intersects a held record fails at proposal validation with `urn:fathom:problem:audit:legal-hold-conflict` and names the held record ids. Overriding requires a new proposal with the hold released first, by the authority that set it, recorded as its own audit record. There is no force flag.

### 4.2 The record spine

```sql
CREATE TABLE audit_record (
  -- Identity and admission order (audit's OWN producer identity, 11 §4.2)
  record_id            uuid        NOT NULL PRIMARY KEY,
  admitted_node_id     text        NOT NULL,      -- 'enterprise' | 'edge:<asset_id>'
  admitted_seq         bigint      NOT NULL,      -- audit's gap-free monotonic sequence (11 §4.3)
  admitted_hlc_physical_ms bigint  NOT NULL,
  admitted_hlc_logical integer     NOT NULL,
  ingest_time          timestamptz NOT NULL,      -- ms granularity, AU-12(1) [08 §3.5]

  -- What this is
  record_type          text        NOT NULL,      -- §4.1's table
  immutability_class   text        NOT NULL,      -- §4.1. CHECK-constrained to the enum
  legal_hold           boolean     NOT NULL DEFAULT false,
  retention_class      text        NOT NULL,      -- §4.8

  -- Correlation (04 §11: "correlated by X-Correlation-Id and by trace_ref")
  correlation_id       uuid        NOT NULL,
  causation_id         uuid        NULL,
  trace_ref            text        NULL,          -- into Domino's trace store, 03 §8.5

  -- Provenance of the record itself (03 §5.4)
  producer_slug        text        NOT NULL,
  producer_version     text        NOT NULL,
  producer_node        text        NOT NULL,      -- 'enterprise' | 'edge:<asset_id>' [03 §5.4]
  producer_monotonic_seq bigint    NULL,          -- NULL only for HTTP-path records (§10.2)
  source_event_id      uuid        NULL,          -- the ingested envelope, where applicable
  occurred_at          timestamptz NULL,          -- recorded, NEVER compared [11 §4.7]
  recorded_at          timestamptz NOT NULL,      -- "audit uses recorded_at" [03 §5.4]

  -- Subject (03 §5.4: exactly one identifier matching scope; fleet requires none)
  scope                text        NOT NULL,
  subject              jsonb       NOT NULL,
  baseline_epoch       bigint      NULL,
  identity_provisional boolean     NOT NULL DEFAULT false,   -- [11 §8.2]

  -- Classification, with the inheritance chain (03 §7.3)
  classification       jsonb       NOT NULL,      -- ClassificationLabel incl. inherited_from[]
  key_class            text        NOT NULL,      -- §5.3, derived from classification
  purge_group_id       uuid        NOT NULL,      -- §5.4. THE shred handle

  -- Payload, envelope-encrypted (§5.6). No plaintext column exists.
  payload_ciphertext   bytea       NULL,
  payload_ref          text        NULL,          -- s3:// when above inline_max; same envelope
  payload_aad_sha256   bytea       NOT NULL,      -- AAD binding: see §5.6
  wrapped_dek          bytea       NOT NULL,      -- R-DEK wrapped under the PG-KEK, HSM-only unwrap
  wrapped_dek_key_id   text        NOT NULL,      -- HSM handle of the wrapping PG-KEK
  payload_hmac         bytea       NOT NULL,      -- keyed, NOT a bare hash. §8.5
  payload_hmac_key_id  text        NOT NULL,

  -- Non-repudiation (AU-10, AU-9(3) [08 §3.5])
  producer_signature   bytea       NULL,          -- verbatim from the outbox row [11 §10.2]
  producer_signing_key_id text     NULL,
  signature_status     text        NOT NULL,      -- verified | unverifiable | absent
  attestation          jsonb       NOT NULL,      -- the SIGNED unit: clock + sync_quality. §8.3
  admission_signature  bytea       NOT NULL,      -- audit's countersignature. §8.4
  admission_key_id     text        NOT NULL,

  -- Hash chain (AU-9(3))
  chain_prev_hash      bytea       NOT NULL,
  chain_hash           bytea       NOT NULL,

  -- Purge state. NOTHING here is ever set by a mutation of content.
  purged_by            uuid        NULL REFERENCES purge(purge_id),
  purged_at            timestamptz NULL,
  rewrapped_from_key_class text    NULL,          -- §5.10

  CONSTRAINT audit_seq_unique UNIQUE (admitted_node_id, admitted_seq),
  CONSTRAINT audit_payload_present CHECK (payload_ciphertext IS NOT NULL
                                          OR payload_ref IS NOT NULL),
  CONSTRAINT audit_no_plaintext CHECK (payload_ciphertext IS NULL
                                       OR length(payload_ciphertext) > 0)
);
```

Five things about this table are deliberate and should not be "simplified" by an implementer.

1. **There is no plaintext payload column, and no code path that could populate one.** §5.6's writer is the only ingress, exactly as document 11 §2.3 makes `emit()` the only ingress to the outbox.
2. **`purged_at` is metadata about the record, not a modification of it.** It is set once, from NULL, by the purge coordinator. The content columns are never touched: the content became unreadable when the HSM destroyed the PG-KEK. This is the property that lets audit be append-only *and* purgeable, and it is why the `wrapped_dek` stays in the row rather than in a mutable side table — a side table would have to be deleted, and its deletion would live on in WAL, base backups, and replicas.
3. **`attestation` is a single JSONB blob, not exploded columns.** It is inside the producer's signature (document 11 §10.2 signs over `sync_quality`), so splitting it into indexed columns as the *storage of record* would make signature verification depend on a lossless round-trip through a schema. Indexed projections exist in `attestation_index` (§4.4); the signed blob is authoritative.
4. **`admitted_seq` is audit's own gap-free monotonic sequence** per document 11 §4.3, using audit's own `producer_node_id`. Two consequences: an assessor gets loss detection over the audit stream itself, and audit provides an admission ordering independent of any producer's contested clock (§8.4).
5. **`occurred_at` is stored and never compared.** The `SourceTime` type of document 11 §4.7 raises on comparison; document 11 §11.5 gate 4 greps for comparisons over `source_time`/`occurred_at`/`recorded_at`. Audit's query layer sorts on `admitted_seq` and the HLC, never on a wall clock, and document 03 §5.4 is explicit that *"audit uses `recorded_at`"* for *presentation* — a display value, not an ordering key.

### 4.3 Tool invocation records

Document 03 §8.5: *"Tool invocations, with full request and response, are recorded to Audit & Provenance and correlated to the Domino trace by `trace_ref`."* Document 03 §8.3 adds two requirements this table exists to satisfy: every accountable_autonomous run is *"recorded to Audit with the accountable owner"*, and every Domino Endpoint call is proxied so that *"a Sustainment Plane service attaches caller identity to the audit record"* — because an Endpoint's static token *"carries no caller identity and no per-caller audit trail"* (document 02 §4.3, finding D12).

```sql
CREATE TABLE tool_invocation (
  record_id            uuid   NOT NULL PRIMARY KEY REFERENCES audit_record(record_id),
  agent_id             text   NOT NULL,
  agent_version        text   NOT NULL,
  manifest_name        text   NOT NULL,      -- packages/agent-tooling/manifests/<slug>/… [03 §8.2]
  manifest_version     text   NOT NULL,
  llm_version          text   NULL,
  prompt_version       text   NULL,          -- pinned together as one unit [03 §8.4]
  target_slug          text   NOT NULL,      -- §3.1 slug of the sub-application called
  operation_id         text   NOT NULL,      -- OpenAPI operationId [09 §7.3]
  api_major            integer NOT NULL,
  declared_side_effects text  NOT NULL,      -- none | proposal-only [03 §4.1, §8.1]
  agent_authority      text   NOT NULL,      -- delegated | accountable_autonomous [03 §8.3].
                                              -- Named agent_authority, not authority_class, to
                                              -- avoid colliding with 03 §7.2.1's Proposal field
                                              -- of the same bare name (31 §2.5 amendment A-2)
  principal_id         text   NULL,          -- the human, for delegated
  accountable_owner    text   NULL,          -- the NAMED human, for accountable_autonomous
  proxied_endpoint     text   NULL,          -- the Domino Endpoint, where proxied [03 §8.3, D12]
  http_status          integer NOT NULL,
  duration_ms          integer NOT NULL,     -- MONOTONIC-measured [09 §4.8]
  outcome              text   NOT NULL,      -- ok | error | terminated-token-expiry | checkpointed
  resumable_checkpoint_ref text NULL,        -- [03 §8.3: mid-run token expiry is a defined condition]

  CONSTRAINT ti_authority_owner CHECK (
    (agent_authority = 'delegated'               AND principal_id    IS NOT NULL) OR
    (agent_authority = 'accountable_autonomous'  AND accountable_owner IS NOT NULL)),
  CONSTRAINT ti_no_state_changing CHECK (declared_side_effects IN ('none','proposal-only'))
);
```

The full request and response bodies are **payload** on the spine row, encrypted per §5.6. They are the single highest-risk content in the store: a tool response can contain retrieved corpus text, which document 03 §9 designates untrusted and which is *"free text authored by thousands of people, including parties outside the program."* Two rules follow, both enforced:

- **`ti_no_state_changing` is a database constraint, not a comment.** Document 03 §8.1 permits `x-agent-eligible` only where side effects are `none` or `proposal-only`. If a `state-changing` invocation ever reaches audit, the insert fails and pages, because its existence means the CI gate of document 09 §6.2 job 4 and the import-time raise of document 09 §5.1 were both bypassed. Audit is the last place that can notice.
- **Tool request and response bodies are never returned by any read operation in plaintext form to a caller whose ABAC attributes do not dominate the record's label**, and never post-filtered (§10.6). The retrieval corpus is where a mislabeled payload is most likely to originate, so this table is the most likely purge target in the system.

### 4.4 Event ingest records and the attestation stream

Every ingested envelope is stored complete: all of document 03 §5.4's fields, the whole `clock` block, and `sync_quality` with all five sub-fields. The envelope shape is `packages/canonical-schemas`' (document 10 §4.5) and audit **imports it rather than redefining it** — document 09 §4.1's rule that canonical kernel types are imported, never redefined, applies with force here, because a divergent copy of the envelope in the audit store would make the signature unverifiable.

```sql
CREATE TABLE attestation_index (        -- indexed PROJECTION; audit_record.attestation is authoritative
  record_id            uuid   NOT NULL PRIMARY KEY REFERENCES audit_record(record_id),
  producer_slug        text   NOT NULL,
  producer_node        text   NOT NULL,
  monotonic_seq        bigint NOT NULL,
  hlc_physical_ms      bigint NOT NULL,
  hlc_logical          integer NOT NULL,
  hlc_node_id          text   NOT NULL,
  time_source          text   NOT NULL,   -- gnss|usno_authenticated|upstream_ntp|holdover|unsynced
  offset_ms            double precision NOT NULL,
  dispersion_ms        double precision NOT NULL,   -- the published epsilon; may be 'Infinity'
  seconds_since_sync   integer NOT NULL,
  step_occurred        boolean NOT NULL,
  source_time          timestamptz NOT NULL,        -- recorded, never compared [11 §4.7]
  ingest_time          timestamptz NOT NULL         -- ms granularity [AU-12(1), 08 §3.5]
) PARTITION BY RANGE (ingest_time);
```

**Answering document 11 open question 10 — does Audit accept a per-event attestation at full event volume?** **Yes, with three declared properties, and one honest gap.**

1. **The attestation row carries no domain payload.** It is envelope metadata only. It therefore has no independent spillage risk and needs no per-record purge group — attestations join the class-level group of §5.4, which is why the `attestation` record type is marked "never purged in practice" in §4.1.
2. **The table is range-partitioned on `ingest_time`, monthly**, so retention and vacuum are partition operations rather than row deletes. `sync_quality` is retained permanently (document 03 §5.4, document 11 DO-NOT item 20), so partitions are detached to the object-store tier under AU-4(1) *"transfer to alternate storage"* [08 §3.5], never dropped.
3. **`dispersion_ms` is `double precision` and must accept `Infinity`**, because document 11 §4.6's honesty rule sets `time_source = unsynced` and `dispersion_ms = +inf` when the sampler has no reading. A schema that cannot store infinity forces a fabricated value, which document 11 DO-NOT item 19 prohibits. This is the kind of detail that silently defeats the whole attestation scheme.
4. **The gap, stated rather than filled:** document 06 §7 gives ~5M telemetry *samples*/day and ~25,000 predictions per scoring run, but **no per-topic event rate** — and document 03 §6 is deliberately batch-level, so samples do not map to events. The attestation table's absolute sizing therefore cannot be computed from the capacity model as it stands. Per document 09 DO-NOT item 31, no number is invented here; this is raised as **OQ-3** in §17 and as a request to the capacity model, which document 05 D37 and document 06 §7's own "Assumptions and alternatives" already flag as incomplete.

### 4.5 The provenance graph — how obligation 9 becomes satisfiable

Document 03 §15 obligation 9 is a **contract term** — externally observable, binding on substitutes. Document 03 §7.3 requires *"every derived value carries the union of its inputs' labels, recorded in `inherited_from` and enforced by the provenance obligation in §15."* Document 10 §4.8's `ClassificationLabel.union()` computes the label; nothing yet stores the *edges*, and without the edges `inherited_from[]` is a list of references into nothing.

```sql
CREATE TABLE provenance_edge (
  derived_record_id  uuid NOT NULL REFERENCES audit_record(record_id),
  input_ref          text NOT NULL,      -- a record_id, event_id, observation_ref, or s3:// URI
  input_record_id    uuid NULL REFERENCES audit_record(record_id),  -- resolved, where resolvable
  edge_kind          text NOT NULL,      -- see table below
  input_version      text NULL,          -- model_version, definition_version, taxonomy_version…
  computation_ref    text NULL,          -- scoring_run_id, trace_ref, job id [obligation 9]
  PRIMARY KEY (derived_record_id, input_ref, edge_kind)
);
CREATE INDEX provenance_edge_reverse ON provenance_edge (input_record_id);
```

| `edge_kind` | Populated from | Why it matters for purge closure |
|---|---|---|
| `label_inheritance` | `ClassificationLabel.inherited_from[]` [03 §7.3] | The definitive spillage-propagation edge. If input X was mislabeled, every derived value carrying X in `inherited_from` inherited the wrong label |
| `feature_observation` | `FailurePrediction.contributing_factors[].observation_ref` [03 §7.1] | Points at the feature observation with point-in-time provenance. A spilled telemetry batch reaches predictions here |
| `evidence` | `Proposal.evidence[].ref`, with `source_trust` [03 §7.2, D14] | A proposal resting on a spilled document chunk. `source_trust` is retained so `external`-trust evidence is queryable |
| `model_input` | Scoring run manifests, `model_binding.activated` | Which model version consumed which data |
| `taxonomy` | `taxonomy_version` on every label [03 §14, 08 §2.8] | A taxonomy revision never rewrites historical tags; the crosswalk edge is how the two coexist |
| `antecedent` | `causation_id` [03 §5.4] | Causal chain for cross-topic ordering forensics |
| `supersession` | Anomaly-tag supersession [03 §11] | Human judgments are evidence; supersession is recorded, not overwritten |

**The reverse index is the load-bearing part.** Purge closure is a reverse-reachability query from the spilled record: *what did this contaminate?* Forward reachability answers *where did this figure come from?*, which is obligation 9's user-facing question. One table serves both, and the two queries are §10.4's two operations.

**Edges are written by the producing service, in its own transaction, through its outbox.** A derived value's edges are known only to the service that derived it, so they cannot be inferred here. Document 10 §4.8's `union()` refuses to emit a derived event whose `inherited_from` is empty when the aggregate is declared derived (document 11 §10.4); this document adds the corresponding audit-side gate: **an `event_ingest` record for an aggregate declared derived, arriving with zero `label_inheritance` edges, is admitted and flagged** — never rejected, because rejecting it would lose the record — and it increments `fathom_audit_provenance_incomplete_total{producer,event_type}` and fails that producer's Definition of Done. Admit and flag, never drop, is the same rule as signature failure (§8.6).

### 4.6 The dissemination ledger — how audit knows which stores hold a copy

**This is the piece without which D15's cross-store remediation cannot be more than a hope**, and it is the single most important addition this document makes to the platform.

The purge protocol must enumerate every store holding a copy of a logical record. Three candidate mechanisms, and only the third works:

| Mechanism | Verdict |
|---|---|
| Derive holders from document 03 §6's declared consumer lists | **Insufficient.** The catalog declares who *may* consume, not who *did*. A consumer down for a day, a read model rebuilt from `changed_since` after the fact, a gateway cache — all invisible. And a purge certificate built on "should have" is not evidence |
| Ask every store at purge time ("do you hold record R?") | **Insufficient and unsafe.** It requires every store to support arbitrary content search, which for the vector index means a query that leaks the existence of records (D13, document 03 §7.3), and for Domino traces means an interface Domino does not offer (document 02) |
| **Consumers report each apply; audit maintains the ledger** | **Chosen.** The inbox already writes atomically with the state change (document 03 §5.2, D2) and already exports `sync_quality` to audit (document 11 §10.5). One more field group on the same export is nearly free, transactional, and survives disconnection because it rides the consumer's own outbox |

```sql
CREATE TABLE dissemination (
  source_event_id  uuid  NOT NULL,     -- or the audit record_id for non-event paths
  holder_slug      text  NOT NULL,     -- 03 §3.1 slug, no variation
  holder_node      text  NOT NULL,     -- 'enterprise' | 'edge:<asset_id>'
  holder_store     text  NOT NULL,     -- read-model / index / cache / object-store / trace name
  applied_at       timestamptz NOT NULL,
  materialized     boolean NOT NULL,   -- true if content, not just a reference, was stored
  purge_receipt_id uuid  NULL REFERENCES purge_receipt(receipt_id),
  purged_at        timestamptz NULL,
  PRIMARY KEY (source_event_id, holder_slug, holder_node, holder_store)
);
```

**`materialized` is the field that makes the ledger honest.** Document 03 §6 requires large results to be *referenced, not inlined* (D27): `prediction.updated` carries *"references to the run artifact rather than inline result sets."* A consumer that stored only the reference has no content to purge, and its purge is a no-op receipt — but the *object store* holding the artifact does have content, and it appears as its own ledger row. Conflating those two produces a certificate that purges nine read models and leaves the payload sitting in MinIO.

**[AMENDMENT REQUIRED — 11-1]** Document 11 §10.5 exports `sync_quality` to Audit. It must additionally export a dissemination record per inbox apply, and per read-model rebuild via `ChangedSinceRebuilder` (document 11 §2.8) — the rebuild path is the one an implementer forgets, and it is precisely how a purged record returns from the dead. §16.2 has the exact edit.

### 4.7 The integrity chain

AU-9(3) [08 §3.5] is claimed by cryptographic protection of audit information. Three layers:

1. **Per-node hash chain.** `chain_hash = SHA-256(chain_prev_hash ‖ canonical(record header) ‖ payload_hmac)`, chained per `admitted_node_id` in `admitted_seq` order. Insertion, removal, or reordering breaks the chain at the point of tampering.
2. **Merkle checkpoints.** Every N records and at least hourly, a `integrity_checkpoint` record seals a Merkle root over the interval, signed with audit's admission key, carrying `(admitted_node_id, first_seq, last_seq, merkle_root, prev_checkpoint_hash)`. Checkpoints are `legally-immutable` (§4.1) and live in their own purge group, so **no key destruction can ever reach the proof that nothing was destroyed**.
3. **Cross-node anchoring.** On reconciliation (§9), each node's checkpoints are counter-anchored into the other repository's chain. A ship's chain becomes verifiable ashore without merging the stores, which is AU-6(3) correlation rather than consolidation.

**The chain is computed over hashes, never over plaintext.** That is what makes §5.8's crypto-shred compatible with §8: destroying a key destroys readability and leaves verifiability entirely intact. An assessor can prove a purged record was not tampered with, which is a stronger position than either "we deleted it, trust us" or "we kept it, sorry."

### 4.8 Retention

| `retention_class` | Applies to | Retention | Basis |
|---|---|---|---|
| `permanent` | `attestation`, `integrity_checkpoint`, `purge_*`, provenance edges, dissemination ledger | Indefinite. Partitions transfer to the object-store tier, never dropped | 03 §5.4 (`sync_quality` permanent); AU-4(1) [08 §3.5] |
| `accreditation` | `model_binding_activated`, `agent_promotion`, `proposal_adjudication`, `anomaly_tag_adjudication`, `maintenance_action_recorded` | Indefinite | 04 §11 "accreditation artifact" |
| `program` | `event_ingest`, `prediction_recorded`, `tool_invocation`, `agent_run` | **[OPEN — OQ-1]** No document states a retention period. Interim: indefinite, because a shorter period cannot be invented (document 09 DO-NOT 31) and because the accreditation body sets it | §17 |
| `quarantine` | `quarantine_record` | Indefinite until adjudicated, then `program` | 11 §10.2 |

**Retention expiry is not purge.** Expiry is scheduled, class-wide, and requires no authority beyond the declared policy; purge is an unscheduled remediation of specific content under §6's authority check. Both destroy content; only one is an incident. The distinction is a column (`purge.reason_class`) and a metric, because conflating them lets a purge hide inside routine housekeeping.

---

## 5. Envelope-level encryption and the key hierarchy

### 5.1 The requirement, and what "per-classification keys" cannot mean

Document 03 §13.1: *"Envelope-level encryption with per-classification keys. Crypto-shredding a key is the purge mechanism where physical deletion is impossible."* Document 08 §3.5 adds SC-28/SC-28(1) *"with mission-owner sole key control"*, and document 11 §10.1 already stores outbox payloads *"under a per-classification KEK."*

**Taken literally, one key per classification level is unusable as a purge mechanism, and this must be said before the design.** The demonstration is single-level unclassified (document 03 §12, document 06 §5). One key for the level means crypto-shredding it destroys *every record in the system*. Even in production with four levels and compartments, destroying a compartment's key to remediate one spilled maintenance narrative would destroy every record in that compartment — the remediation is more damaging than the spillage, so it would never be authorized, so the purge path would exist on paper and never be used. **A purge mechanism whose granularity exceeds the granularity of the incident is not a purge mechanism.**

The resolution: **purge granularity must equal key granularity, so the hierarchy needs a level below classification.** Per-classification keys are retained — they do real work for cryptographic separation under SC-28(1) and for mass shred — but the *shred handle* is a finer key beneath them.

### 5.2 The four-tier hierarchy

```
Tier 0   ROOT CMK  — one per classification LEVEL (U | CUI | S | TS)
         Generated in and never exported from the HSM. Never destroyed.
         Mission-owner sole key control [SC-28(1), 08 §3.5].
             │  wraps
             ▼
Tier 1   KC-KEK  — one per (key_class × key_epoch).   §5.3
         key_class = level + compartments + cui_categories + dissemination
         Resident in the HSM. Rotated on epoch advance.
         Destroying one shreds an entire class-epoch — the mass-shred lever,
         used for "this compartment is decontrolled/stood down", never for an
         individual spillage.
             │  wraps
             ▼
Tier 2   PG-KEK  — one per purge_group.   §5.4    ◀── THE SHRED HANDLE
         Generated in the HSM, resident in the HSM, NEVER exported in any form.
         Wrapped form persisted in the HSM's own key store only.
         Destroying one is the purge primitive (§5.8).
             │  wraps
             ▼
Tier 3   R-DEK   — one per audit record. AES-256-GCM.
         Generated in the service, used once, plaintext zeroized immediately.
         Wrapped form (`audit_record.wrapped_dek`) stored IN THE RECORD ROW.
```

**Two decisions in that diagram are the ones that matter, and both are [ESTABLISHED HERE].**

**Decision 1 — the wrapped R-DEK is stored in the append-only row, not in a mutable side table.** The naive design puts key material in a separate table and purges by deleting the row, leaving the audit store untouched. It fails: a Postgres `DELETE` lives on in WAL, in base backups, in physical replicas, in the shore replica, and on backup tape. "We deleted the key row" is unprovable and, worse, probably false. Storing the wrapped DEK inside the append-only row and **making the purge primitive an HSM key destruction** means every copy of the wrapped DEK anywhere — row, WAL, backup, replica, tape — becomes simultaneously useless, because none of them can be unwrapped without a key that no longer exists. **The purge is always an HSM operation, never a database operation.** That single inversion is what makes an append-only store purgeable.

**Decision 2 — PG-KEKs are never exported, in any form, ever.** Not wrapped, not to a backup, not to a key-escrow, not to the edge. There is no `ExportKey` code path, and a static gate asserts it (§12.5). The reason is directly about proof: unreadability can only be *demonstrated* if no copy of the key can exist outside the module that destroyed it. An escrowed copy turns "provably unreadable" into "unreadable unless someone has the escrow," which no assessor should accept and which the program should not want to defend.

Consequence to accept honestly: **an HSM cluster loss destroys the readability of everything under it.** The mitigation is HSM-native cluster replication and partition backup *within the FIPS boundary* — key material replicated between HSMs under the vendor's own cloning/backup protocol, never exported to the application. Tier 0 root CMKs are additionally backed up to HSM-vendor backup tokens held under two-person control. Tier 1 and Tier 2 keys are cluster-replicated but **not** token-backed, and this is deliberate: a token backup of a PG-KEK is exactly the escrowed copy Decision 2 forbids. The trade is stated, not hidden: we accept that catastrophic HSM-cluster loss renders records unreadable, in exchange for a purge that is provable.

### 5.3 `key_class` derivation

`key_class` is a deterministic, canonical function of the record's `ClassificationLabel` (document 03 §7.3, document 10 §4.8):

```python
def key_class(label: ClassificationLabel) -> str:
    """Canonical, stable, order-independent. The SAME label always yields the same
    key_class, in every service, in every language binding. [ESTABLISHED HERE]

        kc:<level>:<sorted compartments>:<sorted cui_categories>:<sorted dissemination>

    Deliberately EXCLUDES: derived_from, inherited_from (provenance, not access
    control) and distribution_statement (a marking obligation under DoDI 5230.24,
    not a cryptographic separation boundary — and per document 10 §4.8 it cannot
    always be mechanically unioned).
    """
```

- **Compartments and CUI categories are in the key class** because they are the separations whose breach is catastrophic and whose holders differ. SC-28(1) cryptographic protection at rest is claimed per class, and SC-16 binding of classification to the record is enforced by construction: the AAD of §5.6 includes `key_class`, so a record cannot be decrypted under a different class's key even by an authorized operator with both keys.
- **`dissemination[]` is in the key class** because a NOFORN record and its otherwise-identical releasable sibling must not share key material; the whole point of the control is a different holder set.
- **Cardinality is bounded and must stay bounded.** For the single-level unclassified demonstration there is exactly one `key_class`. In production the count is the number of *actually occurring* label combinations, which is small; a registry table records each observed class with first-seen and record count, and a metric alerts on class-count growth so that an accidental explosion (a free-text field leaking into a label) is visible. `key_class` is registered on first use, never pre-enumerated.

### 5.4 `purge_group_id` derivation — the shred handle

The purge group is **the unit of independently destroyable content**. Choosing it is the central design decision of this document, because it fixes both the granularity of remediation and the cost of key management.

```python
def purge_group_id(record: AuditRecord) -> UUID:
    """[ESTABLISHED HERE] Deterministic UUIDv5 over the group selector.

    Group selector, by record class:

      A. DOMAIN-PAYLOAD RECORDS  (event_ingest, tool_invocation, prediction_recorded,
         and every record whose payload can carry mislabeled content)
             ("record", record_id)
         -> ONE PURGE GROUP PER RECORD. Maximum granularity: a single logical
            record can be destroyed with zero collateral.

      B. ATTESTATION RECORDS  (sync_quality, clock steps)
             ("attestation", key_class, day_bucket(ingest_time))
         -> A shared group. These carry envelope metadata only, never domain
            payload, so they have no independent spillage risk (§4.4). Grouping
            them by class-day keeps key count proportional to time rather than
            to event volume, which is what makes the answer to document 11's
            open question 10 affirmative rather than aspirational.

      C. REMEDIATION AND INTEGRITY RECORDS  (purge_*, integrity_checkpoint)
             ("remediation-invariant",)
         -> A SINGLE, PERMANENT group whose PG-KEK is registered as
            NON-DESTRUCTIBLE in the HSM policy. No purge can ever reach the
            record that a purge occurred, or the proof that nothing else was
            removed. This is a policy attribute on the key, not a convention
            in code.
    """
```

**Why per-record for class A, despite the key count.** The alternative — grouping by correlation, subject, or day — was rejected because in every case the group is larger than the incident. A spillage is one payload; if the group is a day of one asset's telemetry, remediation destroys a day of one asset's telemetry, and the authority will decline. Then the purge path is theoretical, and D15 is open again with more paperwork. The cost of per-record granularity is one HSM-resident key per domain-payload record, and it is paid deliberately.

**The cost is bounded by an HSM-side derivation, not by storing a key blob per record.** Tier-2 PG-KEKs are **derived** inside the module from the Tier-1 KC-KEK and the `purge_group_id` — a KDF the HSM performs, so no per-group blob is stored — **except** that a derived key cannot be destroyed independently, which is the entire requirement. The resolution is a per-group **shred nonce**: the PG-KEK is `KDF(KC-KEK, purge_group_id ‖ shred_nonce)` where `shred_nonce` is a small random value held in an HSM-resident, HSM-policy-protected table. Destroying a group = **destroying its shred nonce inside the module**, after which the PG-KEK is unrederivable and every wrapped R-DEK under it is permanently unwrappable. Storage is 16 bytes per group inside the FIPS boundary rather than a full key object, the destruction is a single module operation with a signed receipt, and Decision 2 holds because the nonce never leaves the module either.

**This is the mechanism to implement.** It is stated at this length because a reader who takes away only "per-classification keys" will build the unusable version, and a reader who takes away only "per-record keys" will conclude the HSM cannot hold them.

### 5.5 KMS/HSM selection

Document 08's posture constrains this hard: IL4 for CUI and IL5 for unclassified NSS (document 08 §3.3 — *"IL5 no longer covers CUI"*, redefined 2 July 2025, and requiring *"a written authorising-official determination of NSS status"*); self-managed OpenShift with air-gapped enclaves (document 01 §12); *"mission-owner sole key control"* (document 08 §3.5); and *"IL5 requires physical or NSA-validated cryptographic separation"* (document 08 §6).

**Selection [ESTABLISHED HERE]:**

| Layer | Selection | Why |
|---|---|---|
| **Root of trust** | An **on-premises FIPS 140-3 Level 3 network HSM cluster** — Thales Luna Network HSM or Entrust nShield Connect XC — with a dedicated partition per classification level, accessed over PKCS#11 | Mission-owner sole key control is unsatisfiable with CSP-managed keys, and an air-gapped enclave cannot reach a cloud KMS. Level 3 gives the physical separation document 08 §6 requires at IL5 |
| **Key-management API** | **HashiCorp Vault Enterprise Transit** (or OpenBao) with the HSM as seal and PKCS#11 backend; `wrap`, `unwrap`, `derive`, `destroy`, and a signed audit log | The application needs an audited, policy-gated wrap/unwrap API with dual-control on destroy. Vault supplies it; raw PKCS#11 from application code would put key policy in application code |
| **Edge** | A **PCIe/portable HSM per edge-profiled hull** (Luna PCIe or nShield Solo XC) with its own partition and its own Vault instance | A hull dark for six weeks cannot reach shore for an unwrap. §5.11 |
| **Development and CI** | **SoftHSM2** behind the same PKCS#11 interface, plus Vault in dev mode | Testcontainers-based integration tests (document 09 §2.2) must exercise the real code path. **A SoftHSM key is never valid in any deployed environment**, asserted at startup |
| **Rejected** | AWS KMS / CloudHSM, Azure Key Vault Managed HSM | Air-gap and sole-key-control. Recorded so it is not re-litigated |

**Verification note, restated because it matters:** FIPS certificate numbers, current firmware validation status, and any IL4/IL5 authorization claim for a named product must be checked against the CMVP validated-modules list and the DoD Cloud Catalog at implementation time. Document 08 §1 marks unverified values **UNVERIFIED** rather than filling them in; the same discipline applies here. Document 08 §3.6's Iron Bank constraint also applies: *"Hardened containers do not have a Certificate to Field or an Authority to Operate"*, so the Vault image confers evidence, not authorization.

### 5.6 The write path

```python
class AuditWriter:
    """The ONLY ingress to audit_record. There is no other insert path, exactly as
    document 11 §2.3 makes emit() the only ingress to the outbox."""

    async def admit(self, uow: UnitOfWork, candidate: AdmissionCandidate) -> RecordId:
        # 1. Verify the producer signature over the canonical field set of 11 §10.2,
        #    INCLUDING sync_quality. Failure -> quarantine + audit, never a drop (§8.6).
        # 2. Countersign (§8.4) and extend the hash chain (§4.7), inside this transaction.
        # 3. key_class  := key_class(candidate.classification)          # §5.3
        #    purge_group:= purge_group_id(candidate)                    # §5.4
        # 4. R-DEK := csprng(32)
        #    aad    := canonical(record_id, record_type, key_class, purge_group_id,
        #                        producer_slug, producer_node, producer_monotonic_seq,
        #                        classification, immutability_class)
        #    ct     := AES-256-GCM(R-DEK, plaintext, aad)
        #    wrapped:= vault.transit.wrap(pg_kek_handle(purge_group), R-DEK)
        #    zeroize(R-DEK, plaintext)
        # 5. payload_hmac := HMAC-SHA-256(hmac_key(key_class), plaintext)   # §8.5
        # 6. INSERT audit_record(...)                                       # same transaction
        # 7. outbox.emit(uow, ...)  for audit's own published facts (§11.1)
```

Four properties, each enforced mechanically rather than by discipline:

- **AAD binds the ciphertext to its classification, key class, purge group, and producer identity.** A ciphertext moved to a row with a different label will not decrypt. This is SC-16 [08 §3.5] — *"bind classification and provenance to synced records"* — implemented as a cryptographic property instead of a validation rule, which means it survives a bug in the validation rule.
- **The plaintext exists only inside `admit()`**, is never logged (document 09 §4.8 forbids logging request bodies of state-changing operations and retrieved corpus text), and is zeroized. `payload_ciphertext` is the only representation persisted.
- **The insert, the chain extension, and audit's own outbox row are one transaction** (document 03 §5.2, CP-10(2) [08 §3.5]). Audit is a program-built service and the universal outbox obligation binds it without exception (document 03 §15.11, document 11 DO-NOT 17).
- **`admit()` never opens a transaction and never commits**, per document 11 §2.3's `UnitOfWork` rule. Audit's `services/` layer owns the boundary (document 09 §4.1).

### 5.7 The read path

```
GET → ABAC authorization in THIS service [03 §15.7]  → dominance check: the principal's
      clearance/compartments must DOMINATE audit_record.classification  → vault.transit.unwrap
      → AES-256-GCM decrypt with AAD → project → X-Classification on the response
```

Four rules:

1. **Authorization is evaluated here, never delegated to the gateway** (document 03 §4, obligation 7).
2. **Filtering is inside the query, never post-hoc** (document 03 §7.3, D13): *"post-filtering leaks the existence of records."* The dominance predicate is a SQL predicate over `key_class`, so an undominated record is never a row in the result set and never contributes to a count, a cursor, or a `next_cursor`. §10.6 details the consequences for pagination.
3. **`Unwrap` failure is a first-class, semantically distinct outcome.** `KeyDestroyed` → `410 Gone`, `urn:fathom:problem:audit:record-purged`, with the purge id and the certificate reference and **no content**. `KeyUnavailable` (HSM unreachable) → `503`, `urn:fathom:problem:audit:key-service-unavailable`. Conflating them would make a purge indistinguishable from an outage, which is precisely the ambiguity an assessor probes.
4. **Every unwrap is audited in the HSM's own log**, independently of this service. An audit store whose only record of its own reads is itself is not evidence; the HSM log is the independent witness.

### 5.8 The crypto-shred procedure

This is the purge primitive. Every store's purge in §6.3 ultimately reduces to it or to a physical deletion where physical deletion is genuinely possible.

```
PROCEDURE crypto_shred(purge_group_id, purge_id):

 1. PRECONDITION  the purge is adjudicated under §6.1, the closure is SEALED (§6.2 phase 3),
                  and no record in the group is legally-immutable or under legal hold
                  (§4.1). Violation -> refuse; the purge FAILS, it does not partially apply.

 2. RECORD FIRST  Write the purge_target rows for every record_id in the group, with
                  record_type, classification LABEL, payload_hmac, and the record's
                  dissemination rows. NOTHING is destroyed before the description of
                  what is being destroyed is durable. (§6.6)

 3. DESTROY       vault.transit.destroy(shred_nonce(purge_group_id))
                  — a single operation inside the FIPS boundary, under HSM dual-control
                    policy, returning a SIGNED destruction receipt.
                  — the PG-KEK becomes unrederivable (§5.4).
                  — EVERY wrapped R-DEK under it — in the row, in WAL, in every base
                    backup, in every physical replica, in the shore replica, on every
                    backup tape, in every snapshot — becomes permanently unwrappable,
                    simultaneously, with no action required at any of those locations.

 4. STAMP         UPDATE audit_record SET purged_by = :purge_id, purged_at = now()
                  WHERE purge_group_id = :pg
                  — metadata only. Content columns UNTOUCHED. The append-only
                    invariant is intact: no row deleted, no content modified.

 5. PROVE         §5.9. Sampled unwrap attempts, the HSM receipt, the key census,
                  and the countersigned certificate.

 6. PUBLISH       remediation.purge_executed on fathom.audit.remediation.v1 (§6.5),
                  carrying the purge id, selectors, and receipt reference — never content.
```

**What becomes unreadable, precisely.** Every `audit_record` whose `purge_group_id` is the destroyed group, in every copy of the database that exists or will ever be restored. Including: a base backup taken before the purge and restored afterwards; a physical replica; the shore replica of an edge store; a snapshot in object storage. **Restoring a pre-purge backup does not resurrect the content** — this is the property that a delete-based purge can never offer, and it is the single strongest argument for this design. A restored backup yields rows whose `wrapped_dek` cannot be unwrapped and whose `purged_at` may be NULL; the `purge` table is itself replicated, so the restored system reconciles the stamp on first read.

**What does not become unreadable, and must be handled separately by §6.3:** copies held by *other* stores under *their own* keys. A read model that materialized the payload into its own tables encrypted it under its own key hierarchy; audit's key destruction does not touch it. **This is the whole reason §6.4's command path and §6.5's notification exist**, and it is why "we crypto-shredded the audit store" is not a spillage remediation. It is one row of the closure.

### 5.9 Proving unreadability, rather than claiming it

Four independent proofs, all sealed into the purge certificate (§6.6). Independence is the point: an assessor should not have to trust this service.

| # | Proof | Verifiable by |
|---|---|---|
| 1 | **HSM destruction receipt** — signed by the module: key handle, group id, destruction timestamp, operator identities under dual control, and the module's serial and firmware version | Verifying the HSM's signature with the module's public key. No audit-service involvement |
| 2 | **Negative unwrap evidence** — after destruction, the service attempts `unwrap` for a sample of purged record ids and records each module error verbatim. **100% of records explicitly named in the spillage report**, plus 100% of the group where it is ≤ 10,000 records, else a documented random sample sized in the certificate | Repeating the attempt. Anyone with read access to the store and the HSM can re-run it and must get the same failure |
| 3 | **Key census** — an HSM audit-log query showing zero `export`, `clone`, `backup`, and `derive-to-external` operations for the group over its entire lifetime, plus the static gate (§12.5) proving no such code path exists | Reading the HSM's own log. This is what closes "unless someone kept a copy" |
| 4 | **Independent countersignature** — the certificate is signed by audit *and* countersigned by Vault/HSM over the same content, so a forged certificate requires compromising both | Verifying two signatures with two independently held public keys |

Proof 2 is the one that turns the claim into evidence, and it is the reason `test_purge_certificate_records_unwrap_failures` (§12.2) is a Definition-of-Done item rather than a nice-to-have. A purge that produced no negative evidence is not a completed purge, and the certificate cannot be sealed without it.

### 5.10 Re-wrap — reclassification without mutation

For a `legally-immutable` record (§4.1), destruction is refused. The remediation is:

```
PROCEDURE rewrap(record_id, new_key_class, purge_id):
 1. new_pg   := purge_group_id for the record under new_key_class
 2. dek      := vault.transit.unwrap(old_pg_kek, wrapped_dek)      # inside the HSM session
 3. new_wrap := vault.transit.wrap(new_pg_kek, dek); zeroize(dek)
 4. append a REWRAP record (its own audit_record, legally-immutable) carrying
    old_key_class, new_key_class, authority, purge_id
 5. UPDATE audit_record SET wrapped_dek = :new_wrap, wrapped_dek_key_id = :new_id,
           key_class = :new_key_class, rewrapped_from_key_class = :old
     WHERE record_id = :id
 6. destroy the OLD purge group's shred nonce  → every LOW-SIDE copy of that wrapped
    DEK (backups, replicas, the low-side shore replica) becomes unwrappable
 7. correct the stored ClassificationLabel via an APPEND-ONLY correction record; the
    original label is retained, because a mislabeling is itself evidence (§6.6)
```

**Step 5 modifies key-wrapping metadata, not content.** The ciphertext, the `payload_hmac`, the producer signature, the admission countersignature, and the hash chain are all untouched and all still verify — because §4.7's chain covers the record header and the payload HMAC, and `wrapped_dek` is deliberately excluded from both the chain input and the signed field set of document 11 §10.2. That exclusion is a design requirement, not an accident: **the record's integrity must be independent of which key currently wraps it**, or reclassification and key rotation would both be indistinguishable from tampering.

Step 6 is why re-wrap is a real remediation and not a relabeling exercise: the *low-side* copies genuinely die, and the canonical record genuinely survives. **Shred low-side, re-wrap high-side.** This is also the correct handling of the routine case document 03 §13 describes — *"a mislabeled payload reaching a lower-side topic is a routine expected incident"* — because in that case the content is not itself illegitimate; it was in the wrong place.

### 5.11 Edge key custody

| Concern | Rule |
|---|---|
| Edge HSM scope | An edge partition holds Tier 0 and Tier 1 keys for **the levels that hull operates at**, and Tier 2 shred nonces **only for purge groups it minted**. It never holds a shred nonce for a shore-minted group |
| Why | A hull may be boarded, salvaged, or lost (document 11 §10.1). A captured edge HSM must not be able to unwrap the fleet's records — only that hull's own |
| Cross-node purge | Destroying a shore group does **not** reach a copy held on a disconnected hull. The purge enters `pending-at-node` and cannot be certified complete until that node acknowledges (§6.7). **This is a stated limitation, not a gap to paper over** |
| Key transport | A shore purge order for an edge-held record travels as a `remediation` command in coordinator priority class 0 (document 11 §9.3), ahead of everything including provisional identity, because a spillage remediation outranks a data-quality concern |
| Rotation while dark | KC-KEK epoch advance cannot reach a disconnected hull. The edge continues on its current epoch and reconciles on reconnect; records carry their `wrapped_dek_key_id`, so a stale epoch is decryptable, never orphaned |

---

## 6. The declared purge protocol

Document 03 §13.2 requires *"a declared purge protocol covering every store, including Domino-side traces and gateway-held read models, with an owner and a tested procedure."*

**Owner: the `audit` service's Remediation Coordinator.** Sole owner. No other service initiates a cross-store purge, and no other service may destroy content in response to anything other than a coordinator command or the corresponding published fact.

### 6.1 Who can trigger a purge

**Decision [ESTABLISHED HERE]: a new authority class, `security_officer`, under mandatory two-person dual control, with a `fleet_authority` counter-signature at class or fleet blast radius. A purge is a `Proposal`.**

**Why not `fleet_authority` alone**, which document 03 §7.2.1 makes the highest authority class. §7.2.1's classes are *operational and engineering* organizational roles: `maintainer` is Ship's Force, `planner` is an RMC/Availability Planner, `fleet_authority` is a TYCOM Readiness Officer. A TYCOM Readiness Officer is not a classification authority and has no role in spillage adjudication; the decision to destroy classified content sits with the Information System Security Manager and, for classification determinations, the Original Classification Authority — document 08 §5.4 is explicit that *"the determination belongs to the Original Classification Authority and the Security Classification Guide, not to engineering."* Routing a spillage purge to a readiness officer puts the wrong person's name on an irreversible security action.

**Why not a security role alone.** A purge destroys evidence. The closure may include maintenance action records that are the label stream for every model in the system (document 03 §6), predictions an operator acted on, and adjudications that authorized real work. When the blast radius crosses more than one asset, an operational authority must accept that operational consequence. So:

```
AuthorityClass = maintainer | planner | supply_officer | design_authority
               | fleet_authority | security_officer          # ← added [AMENDMENT 03-1]
```

| Blast radius of the closure | Required authority |
|---|---|
| `item` / `asset` | `security_officer` **+ a second, distinct `security_officer`** (two-person integrity) |
| `class` / `fleet` | The above **+ `fleet_authority` counter-signature** |
| Closure includes any `legally-immutable` record | The above **+** the purge is automatically converted to a **re-wrap** proposal (§5.10). Destruction of a legally-immutable record is not an available action at any authority level |
| Closure includes a record under `legal_hold` | **Refused.** The hold is released first, by the authority that set it, as its own adjudicated act (§4.1) |

**A purge is a `Proposal`, and this is the most consequential structural decision in this section.** Document 03 §7.2 already supplies exactly the machinery an irreversible high-authority action needs, and every piece of it was added to close D16: `evidence[]` required and non-empty; re-validation at approval (*"validation at creation is insufficient"*); adjudication requires a claim and `If-Match` on the claimed ETag (*"without this the eventually-consistent queue permits two approvals"*); `requires_dual_control`; `authority_class` checked against `blast_radius`; `valid_until`. Building a parallel approval path for purges would reproduce every D16 defect in the one place where a duplicate execution is unrecoverable.

```
kind = anomaly_tag | work_candidate | requisition | interval_change
     | redesign_case | configuration_change | purge        # ← added [AMENDMENT 03-2]
```

with `target_sub_app = audit`, published on `fathom.audit.proposal.v1` per document 03 §6's proposals convention, so the gateway's unified adjudication queue picks it up from the topic pattern with no gateway change.

**Three hard constraints on purge proposals, beyond §7.2's:**

1. **No agent may create or adjudicate a purge proposal.** `x-side-effects` on the purge-proposal operation is `state-changing`, so document 03 §8.1 already forecloses agent eligibility; additionally the coordinator rejects any proposal whose principal's `fathom.agent.authority` claim is `accountable_autonomous` (document 03 §8.3, 31 §2.5) and any proposal carrying an `agent_id`. A prompt-injected purge (D14) is the worst available outcome in this system.
2. **`evidence[]` must include the spillage report** — the incident reference, the mislabeling determination, and its authority — with `source_trust: program`. A purge proposal resting on non-program evidence is refused, not merely flagged.
3. **`valid_until` is mandatory and short** (default 72 hours). Document 03 §7.2 requires re-validation at adjudication; for a purge, re-validation recomputes the closure, because a closure computed five days ago may have grown as derived values were published. **The closure is recomputed and re-sealed at adjudication, and a growth beyond the adjudicated scope aborts the purge and requires a new proposal.**

### 6.2 The seven phases

```
 1 REPORT     A spillage is reported. A purge proposal is created (§6.1) with the
              spillage report as evidence. Nothing is destroyed. Nothing is quarantined.

 2 CONTAIN    On CLAIM of the proposal (before adjudication), the coordinator issues
              POST /{slug}/remediations {action: quarantine} to every holder in the
              provisional closure. Quarantine DENIES READS and BLOCKS FURTHER
              DERIVATION; it destroys nothing and is fully reversible. This is the
              fast, safe, early action, and it is why claim-before-adjudicate matters:
              it stops the spread while the authority deliberates.

 3 ENUMERATE  Compute the closure: reverse reachability over provenance_edge (§4.5)
              ∪ the dissemination ledger (§4.6) ∪ topic/compaction-key locations.
              SEAL it: write purge_target rows for every (record, holder, store)
              triple. Nothing is destroyed before the list of what will be destroyed
              is durable and signed. Publish nothing yet.

 4 ADJUDICATE Dual control per §6.1, with claim + If-Match (03 §7.2). Re-validate:
              recompute the closure and compare to the sealed set. Growth -> ABORT.
              Legally-immutable members -> convert to re-wrap (§5.10). Legal hold ->
              REFUSE.

 5 EXECUTE    Per §6.3's order: leaves inward, audit last, HSM key destruction last
              of all. Each holder returns a signed purge receipt; each receipt is an
              append-only audit record.

 6 VERIFY     §5.9's four proofs, per store. For compacted topics, §7's forced
              compaction and re-consume check. Any store that cannot prove ->
              pending-at-node (§6.7), and the purge is INCOMPLETE, not "completed
              with exceptions".

 7 CERTIFY    Seal the purge certificate (§6.6), countersigned by the HSM. Publish
              remediation.purge_certified. Lift quarantine on records NOT in the
              final closure. Quarantine on purged records is redundant but retained.
```

**Phase 2 before phase 4 is deliberate and is the operationally important choice.** Adjudication under dual control takes hours at best. Containment is reversible, destroys nothing, requires only a claim, and stops both further reads and further derivation — which is what actually limits the damage. A protocol that waits for full authority before doing anything lets the closure grow while the paperwork moves.

### 6.3 What gets purged, in what order, across which stores

**Order principle: leaves inward. Destroy the copies first, the coordination record last, and the key last of all.** Two reasons, both practical. The audit store is the only place that knows the closure and holds the receipts, so destroying it early would destroy the coordination record mid-coordination. And until the HSM key is destroyed, every step is retryable and the content is still recoverable for a legitimately re-scoped purge — an OCA amending the scope after phase 5 has begun is a realistic event, and a protocol that has already destroyed the key cannot comply.

| Order | Store | Mechanism | Class [03 §13.3] | Who executes |
|---|---|---|---|---|
| 1 | **Gateway view-model caches and the unified adjudication queue** | Evict by key; the queue is rebuilt from the topic pattern | ephemeral | `gateway` |
| 2 | **Nine sub-application read models** | Per-store crypto-shred of the holder's own key, or physical `DELETE`/`UPDATE … SET NULL` where the store is genuinely mutable — the read model is a projection, not a system of record, and document 03 §5.1 makes it rebuildable from `changed_since` | operationally append-only (projections) | each sub-application |
| 3 | **Vector index (`knowledge-retrieval`, pgvector)** | Delete the embedding rows **and** the chunk text. Embeddings are inversion-vulnerable, so an embedding retained without its text is still a copy | operationally append-only | `knowledge-retrieval` |
| 4 | **Object-store evidence and `payload_ref` artifacts** | Crypto-shred the object's DEK; then delete the object. Both, in that order — versioned buckets and replicas make deletion alone unreliable | operationally append-only | owning service |
| 5 | **Inboxes and outboxes, and quarantine tables** | `purge_by_selector(...)` — document 11 §10.1 already provides it *"covering the outbox, the inbox, the quarantine tables, and the object-store payload references"* | operationally append-only | `packages/py-sync` |
| 6 | **Domino trace store and Experiment Manager exports** | Delete the trace by `trace_ref`; re-export the affected evaluation set with the record excluded. **Domino is a platform this program does not control** — document 02 rules out several assumed capabilities (D26), so trace deletion may reduce to *deleting the export and recording that the upstream trace could not be reached*. That outcome is `pending-at-node`, not "complete" | **[OPEN — OQ-2]** | `audit` coordinator + Domino admin |
| 7 | **Compacted topics** | §7: redacted replacement at the compaction key, then forced compaction; null tombstone where the key itself is the spillage | operationally append-only | producing service |
| 8 | **Non-compacted topics** | No action. Retention is 7/30 days (document 03 §5.1) and the envelope payload is already ciphertext, so step 10 renders the retained bytes unreadable before they age out | operationally append-only | — |
| 9 | **The audit store itself** | §5.8 steps 2 and 4: seal targets, stamp metadata. No row deleted, no content modified | per §4.1, **per record type** | `audit` |
| 10 | **The HSM shred nonce** | §5.8 step 3. Last of all, under dual control, with a signed receipt | — | HSM, dual control |

**Step 2 deserves a note on the tension it resolves.** A read model is a projection and is rebuildable from `changed_since` reads (document 03 §4, D5), so physical deletion there is safe and cheap. But some read models are, in practice, systems of record — document 05 D5 says exactly that of PdM's maintenance-history read model. A store in that position must declare itself `operationally append-only` with envelope encryption of its own, and purge by crypto-shred rather than deletion. **The `POST /remediations` contract (§6.4) requires every service to declare, per store, which mechanism it uses**, and that declaration is the document 03 §13.3 statement for that store. This document supplies audit's; the sibling build documents supply theirs, and the Definition of Done in document 09 §8.4 already requires it: *"A declared purge path for every store this service owns, stating whether it is legally immutable or operationally append-only."*

### 6.4 `POST /{slug}/remediations` — the new universal contract term

**[AMENDMENT REQUIRED — 03-3]** Every sub-application and platform service exposes:

```
POST   /api/v1/{slug}/remediations           x-substitution: required
                                             x-side-effects: state-changing
                                             Idempotency-Key: required
GET    /api/v1/{slug}/remediations/{id}      x-substitution: required
                                             x-side-effects: none
```

```jsonc
// request
{
  "remediation_id": "uuid",          // the coordinator's purge_id; the idempotency key
  "action": "quarantine | purge | rewrap | release",
  "selectors": [
    { "kind": "event_id",          "value": "…" },
    { "kind": "record_id",         "value": "…" },
    { "kind": "installed_item_id", "value": "…" },
    { "kind": "correlation_id",    "value": "…" },
    { "kind": "compaction_key",    "value": "…", "topic": "fathom.pdm.prediction.v1" }
  ],
  "new_key_class": "kc:…",           // rewrap only
  "authority": { "authority_class": "security_officer", "adjudicators": ["…","…"] },
  "closure_ref": "…"                 // the sealed closure, for the holder's own audit record
}

// response 200 — the purge receipt
{
  "remediation_id": "uuid",
  "holder_slug": "pdm",
  "holder_node": "enterprise",
  "stores": [
    { "store": "prediction_read_model", "immutability_class": "operationally-append-only",
      "mechanism": "physical-delete", "records_affected": 42, "verified": true },
    { "store": "evidence_objects",      "immutability_class": "operationally-append-only",
      "mechanism": "crypto-shred", "records_affected": 3,
      "key_destruction_receipt": "…", "verified": true }
  ],
  "outcome": "complete | partial | pending | refused",
  "pending_reason": null,
  "receipt_signature": "…",          // signed by the HOLDER's key, not audit's
  "receipt_key_id": "…"
}
```

Five requirements on every implementation:

1. **Idempotent on `remediation_id`** (document 03 §4). A purge command will be retried; a second execution must return the first receipt, not re-purge.
2. **The receipt is signed by the holder**, so the certificate aggregates independently-attributable statements rather than audit's assertions about other services.
3. **`outcome: partial` and `pending` are legitimate and must be reported honestly.** A holder that cannot reach its object store says so. A holder that fabricates `complete` corrupts the certificate, which is the one artifact an assessor reads.
4. **`refused` is legitimate exactly once:** a selector resolving to a record the holder classifies `legally-immutable`. The holder names the records and the coordinator converts to `rewrap`.
5. **It is a contract term, not a program implementation standard** (document 03 §10, D24). It is externally observable — call it, get a signed receipt, verify the content is gone — so a substituting implementation must provide it, and the conformance suite can assert it. A partner platform emitting from an ontology can satisfy it; that is the test document 03 §10 sets for any obligation.

**Consequently, document 03 §15 gains obligation 17** (§16.1), and `packages/contracts/conformance/_shared/remediation/` gains a suite every service collects.

### 6.5 How downstream holders are notified — command *and* fact

Two channels, with different jobs. Both are required, and the reason is document 03 principle 3.

**The command — `POST /{slug}/remediations`.** Document 03 principle 3 is explicit: *"Events carry facts, not instructions… A producer that needs a specific action taken elsewhere issues a command against that sub-application's API and accepts the response."* A purge order is an instruction. Publishing it as an event would violate the principle that keeps this system's event bus semantically clean, and — practically — an event gives no acknowledgement, and a purge without acknowledgement cannot be certified.

**The fact — `remediation.purge_executed` on `fathom.audit.remediation.v1`.** This is a fact in audit's own domain: *a purge of logical record R occurred in the audit store at time T under authority A*. It carries the purge id, the selectors, the classification label of what was purged, the certificate reference, and **no content**. Four jobs the command path cannot do:

| Job | Why the command cannot do it |
|---|---|
| **Reach a holder that was down** | The command gets a connection error. The event is durable, and the holder processes it on recovery through its normal inbox |
| **Reach a holder the coordinator did not know about** | The dissemination ledger (§4.6) is good, not omniscient — a store commissioned yesterday, a cache nobody declared. Every consumer of the topic learns of the purge whether or not audit knew to ask |
| **Protect a read model rebuilt after the purge** | The rebuild path is `changed_since` reads (document 03 §4, D5), and a rebuild replays the producer's current state. A holder must apply the purge fact *after* every rebuild, so `remediation.*` is a **standing filter on the rebuild path**, not a one-time command. This is the most easily missed failure mode in the entire design: a correctly purged read model resurrects the content next Tuesday when someone rebuilds it |
| **Carry the topic tombstone** | §7's redacted replacement is published by the producing service in response to the fact |

**The rule that makes both safe:** the command is *authoritative and acknowledged*; the event is *discoverable and idempotent*. A holder that receives the event without having received the command executes the purge and reports a receipt through `POST /audit/remediation-receipts` (§10.5). A holder that receives both does the work once, idempotently on `remediation_id`.

**And the rule that keeps the event from becoming an instruction:** the event states what audit did. A consumer's obligation to act on it comes from the contract (obligation 17), not from the event's content. That is the same structure as `configuration.baseline_changed` — a fact whose consumers are contractually obliged to invalidate predictions (document 03 §6) — and it is why this design does not need an exception to principle 3.

### 6.6 The purge record and certificate — auditing a purge without retaining what was purged

Document 03 §13 requires the purge itself to be auditable. Document 09 DO-NOT item 24 and this document's §14 item 2 require that it be auditable **without retaining the purged content**. Those pull in opposite directions, and the resolution is a precise answer to "what may be retained about content that must not be retained."

| Retained | Not retained | Why |
|---|---|---|
| `record_id`, `record_type`, `purge_group_id` | — | Identifiers, not content |
| The `ClassificationLabel` — including `inherited_from[]` and the **mislabeling correction** | — | The label is metadata and is the evidence of the spillage. Destroying it destroys the reason for the purge |
| `payload_hmac` and `payload_hmac_key_id` | The plaintext; any reversible digest | §8.5: a **keyed** HMAC, whose key dies with the group, so a guess cannot be confirmed |
| Selector values (`event_id`, `installed_item_id`, `compaction_key`) | — | Unless the identifier *is* the spillage — a compartmented `installed_item_id` — in which case the selector is stored under the **high-side** key class and the certificate carries only its HMAC |
| Counts, per-store receipts, mechanisms, timestamps, authorities, adjudicator identities | — | The auditable substance of the act |
| The four proofs of §5.9 | — | The point of the certificate |
| A **category** description ("a maintenance narrative excerpt mislabeled U, actually S//compartment X") | Any quotation, excerpt, field value, or paraphrase of the content | An assessor needs to know what *kind* of thing was purged. A quotation would recreate the spillage inside the record of its remediation |

**Two structural protections:**

1. **The purge record lives in the `remediation-invariant` purge group** (§5.4 class C), whose shred nonce is registered non-destructible in HSM policy. A purge can never destroy the record that a purge occurred — enforced by key policy inside the module, not by application logic.
2. **The certificate is append-only and countersigned.** It is sealed once, at phase 7, and never amended. A later discovery (a holder that reports `pending` reconciling six weeks later, §6.7) produces a **supplemental** certificate chained to the first, exactly as document 03 §11 records anomaly-tag supersession rather than overwriting.

### 6.7 `pending-at-node` — the honest incomplete state

A purge cannot complete while any holder is unreachable. The commonest case is intended: a hull dark for six weeks (document 06 §4) holding a copy in its read model, its inbox, and its own audit store.

```
purge.state:  proposed → claimed → adjudicated → executing → verifying
                                                     │
                                                     ├─▶ certified            (all holders complete)
                                                     ├─▶ certified-partial    (≥1 pending-at-node)
                                                     └─▶ aborted              (closure grew; §6.2 ph.4)
```

Rules:

- **`certified-partial` is never displayed, logged, or reported as "complete."** A metric `fathom_audit_purge_pending_nodes{purge_id}` is exported, `/readyz` reports degraded while any purge has pending nodes, and the operator interface shows the pending set with the node identity and the elapsed duration. Document 11 §9.1's principle applies: never a silent failure, never a generic error.
- **The pending command rides coordinator priority class 0** (document 11 §9.3), ahead of provisional identity submissions, because a spillage outranks a data-quality concern. **[AMENDMENT REQUIRED — 11-2]**: document 11 §9.3's priority table has no remediation class; §16.2 has the edit.
- **The hull's own audit store executes the purge locally on receipt**, using its own HSM partition (§5.11), and returns a receipt signed by its own key. The receipt reconciles ashore and produces the supplemental certificate.
- **Divergence budget interaction, and a deliberate exception.** Document 11 §9.1 makes `EXPLICIT_READ_ONLY` *"the only permitted value"* for `on_breach`. For the audit store that would be wrong: refusing audit writes stops the accountability record for every other service on the hull, which is a worse outcome than an over-budget backlog, and there is no basis in document 08 for making audit-write refusal a required response. **Audit declares `on_breach: ALERT_AND_DEGRADE`** — storage-headroom readiness degradation, a persistent operator banner, and a shore-visible overdue-contact signal — and never refuses an audit write. **[AMENDMENT REQUIRED — 11-3]**, §16.2.
- **Audit's own divergence budget must exceed the planned patrol length**, for the same reason document 11 §9.1 requires it of maintenance action records and anomaly tags. An audit store that hits its budget mid-patrol is a hull operating without an accountability record.

---

## 7. Tombstone semantics for compacted topics

Document 03 §13.4 requires *"tombstone semantics for compacted topics that preserve the compaction invariant."* Document 03 §5.1 sets the context: compaction key is the **aggregate** key — `installed_item_id`, `(niin, location)`, `baseline_id` — never the partition key, because *"compacting on `asset_id` would collapse a hull's entire prediction history to a single record"* (D5). Document 11 §2.2 enforces that with a CHECK constraint.

**The invariant to preserve:** *at most one live record per compaction key.* Note "at most" — a key with zero live records is consistent with the invariant, which is what makes a null tombstone admissible at all.

### 7.1 The two-step mechanism

**Step 1 — a redacted replacement at the same compaction key. This is the primary mechanism.**

The producing service publishes a new event on the same topic, with the **same partition key and the same compaction key**, whose envelope is complete and validly signed and whose payload is:

```jsonc
{
  "$schema": "fathom.common.redacted_payload.v1",
  "redacted": true,
  "purge_id": "uuid",
  "purged_at": "2026-08-04T13:22:05.041Z",
  "authority_class": "security_officer",
  "certificate_ref": "audit://purge/…/certificate",
  "payload_hmac": "…",            // keyed; the key died with the group (§8.5)
  "original_event_id": "uuid",
  "original_classification": { /* the corrected label */ }
}
```

Why this is the primary mechanism, in three points:

1. **It preserves the invariant by construction.** Exactly one live record remains at that compaction key. Compaction then collects every prior value at the key — which is the log-compaction guarantee doing the deletion work, with no null tombstone required.
2. **It preserves discoverability of the fact while removing the content.** A consumer replaying the topic learns that a record existed at this key and was purged, under whose authority, with a verifiable reference. A null tombstone alone erases the key and leaves a consumer unable to distinguish "purged" from "aggregate deleted" from "never existed" — three states with different obligations.
3. **It keeps the envelope stream intact.** The record is signed, sequenced, and chained normally. Document 11 §8.4's rule holds absolutely: **no published event is ever rewritten.** A redacted replacement is a new event, not an edit.

**Step 2 — a null-value tombstone at the compaction key, only where the key itself is the spillage.**

The compaction key is retained in the log even for a redacted record, and sometimes the key *is* the sensitive item — a compartmented `installed_item_id`, or a `(niin, location)` pair whose existence discloses a fitting. In that case, and only in that case, the producing service additionally publishes a **null-value record at that key** (Kafka/Redpanda-native tombstone). After `delete.retention.ms` elapses, the key itself is removed from the compacted log.

The cost is explicit and must be accepted deliberately: **step 2 removes the fact that a record existed at that key**, which is why it is not the default. The fact survives in the audit store and in the purge certificate; it does not survive in the topic.

### 7.2 Forcing compaction, and proving it happened

**Log compaction is not a deletion guarantee with a bounded time**, and treating it as one is how a "purged" record stays readable for a month. Three properties bite:

- The **active segment is never compacted**. A record in the active segment is untouched until the segment rolls.
- Compaction runs when `min.cleanable.dirty.ratio` is met — by default, when enough of the log is dirty.
- `delete.retention.ms` governs how long tombstones themselves persist before removal.

The protocol therefore **forces** it, per topic, at phase 6:

```
1. Alter the topic:  min.cleanable.dirty.ratio = 0
                     max.compaction.lag.ms     = <declared bound>
                     delete.retention.ms       = <declared bound>   # step-2 tombstones only
2. Force a segment roll so the redacted record and any tombstone leave the active segment.
3. Wait for the cleaner to pass the affected partitions (observed, not assumed).
4. VERIFY: consume the topic from offset 0 with a purpose-built verifier and assert
     (a) exactly one live record at the compaction key, and it is the redacted one
         (or zero live records, where step 2 applied);
     (b) no record anywhere in the partition carries the purged payload's ciphertext
         or the original event_id in a payload position;
     (c) the redacted record's signature verifies.
5. Restore the topic configuration and record the before/after in the purge receipt.
```

Step 4 is the "prove it, don't claim it" rule of §5.9 applied to the broker, and it is `test_purge_tombstone_survives_recompaction` in §12.3.

### 7.3 Why the tombstone is hygiene and the crypto-shred is the guarantee

**The event payload on the wire is already ciphertext.** Document 11 §2.2's outbox row holds `payload_ciphertext` under a per-classification KEK, `emit()` encrypts and there is no plaintext path, and `payload_ref` objects are encrypted under the same class. The published envelope therefore carries ciphertext, and **when the shred nonce is destroyed in §5.8 step 3, every retained copy of that ciphertext — in the active segment, in an uncompacted segment, in a replica, in a consumer's local buffer, in a tiered-storage archive — becomes unreadable immediately, without any broker cooperation at all.**

That inverts the usual dependency and is the crux of the answer to D15's "indefinitely compacted topics":

- **Crypto-shred is the guarantee.** It is immediate, requires no broker action, applies to every copy simultaneously, and is provable by §5.9.
- **Tombstone plus forced compaction is hygiene.** It removes the ciphertext bytes and the key's discoverability, bounds storage, and satisfies an assessor who reasonably asks whether the bytes are still there.

A design that relied on compaction alone would have a window measured in segment-roll intervals during which the content was recoverable by anyone with the key — and would have no answer at all for a topic whose retention is `compacted indefinite` (document 03 §5.1). A design that relied on crypto-shred alone would leave unreadable ciphertext accumulating forever. Both, in that order of dependence.

---

## 8. Non-repudiation and signing

AU-10 [08 §3.5] is claimed as *"sign outbox records at the ship."* AU-9(3) is claimed as cryptographic protection of audit information.

### 8.1 Where signing happens: at the producing node

Document 11 §10.2 already specifies it, and audit **does not re-specify or duplicate it**. `emit()` signs at insert, over the canonical serialization of:

```
event_id, event_type, event_version, producer_slug, producer_version, producer_node_id,
monotonic_seq, hlc, scope, subject, baseline_epoch, classification, payload_sha256,
source_time, sync_quality, replay
```

Two properties of that field set are what audit depends on, and neither may change without an amendment to document 11:

- **The signature is over `payload_sha256`, not over the payload.** Therefore **crypto-shredding a payload does not break its signature.** A purged record's producer signature still verifies, its admission countersignature still verifies, and its chain link still verifies. Shred destroys readability, not verifiability. Without this property the purge protocol would be indistinguishable from tampering, and AU-10 would collapse the moment the first purge ran.
- **The signature covers `sync_quality`.** Document 11 §10.2: *"a clock attestation cannot be edited after the fact. This is what makes 'skew is indistinguishable from tampering to an assessor' (08 §3.3) a solved problem rather than a finding."*

### 8.2 What audit does on admission

1. **Verify** the producer signature against the producer's registered signing key for `signing_key_id`, over the exact field set above, recomputed canonically. `signature_status ∈ {verified, unverifiable, absent}`.
2. **Countersign** (§8.4).
3. **Chain** (§4.7), inside the same transaction.
4. **Store the signature and its key id verbatim.** Not a boolean "we checked." An assessor must be able to re-verify from the stored record years later, with audit's own verification logic out of the loop.

### 8.3 `sync_quality` is retained *inside* the signed unit, not alongside it

This is the concrete form of document 08 §3.3's *"skew is indistinguishable from tampering to an assessor."*

`audit_record.attestation` is **one JSONB blob containing the entire `clock` block** — `monotonic_seq`, `hlc`, `source_time`, `ingest_time`, and all five `sync_quality` fields — stored byte-for-byte as it entered the signature computation. `attestation_index` (§4.4) is a *projection* for querying and is explicitly not authoritative.

Why the storage shape matters, and it is not a stylistic preference:

- **Verification requires the exact bytes.** Exploding `sync_quality` into typed columns as the storage of record makes signature verification depend on a lossless round-trip through a schema, through a JSON serializer's key ordering, and through a float formatter. `dispersion_ms` may be `Infinity` (document 11 §4.6). A round-trip that renders it `null`, `1e999`, or `9.0e+307` produces a verification failure indistinguishable from tampering — and the failure appears months later, in bulk, for exactly the disconnected-node records that matter most.
- **Retaining them separately is the specific defect to avoid.** A signature over a clock attestation stored in a different table with a different lifecycle, a different retention policy, and a different purge group is a signature over something that can silently diverge from what it signs. `attestation` shares the record's row, the record's chain link, and the record's retention class (`permanent`, §4.8).
- **`sync_quality` is never purged.** It carries no domain payload (§4.4), it lives in the class-day group (§5.4 class B), and document 11 DO-NOT item 20 forbids pruning it. A purge that destroyed clock attestations would destroy the only means of re-deriving true ordering across the purged interval — and would do so at precisely the moment an assessor is looking hardest.

**The forensic payoff, stated concretely.** An assessor examining two records from one producer whose `recorded_at` values are inverted has, in the same signed unit: `monotonic_seq` (the true order), `hlc` (a total order across nodes), `step_occurred = true` (the STIG-mandated `makestep 1 -1` fired here — document 08 §3.3, rule V-260520), `dispersion_ms` (the published epsilon at that moment), and `time_source = holdover` (why). The inversion is a documented, bounded, signed condition rather than an unexplained timestamp anomaly. That is the difference between a finding and a footnote, and it is the entire reason document 03 §5.4 retains `sync_quality` permanently.

### 8.4 Audit's admission countersignature

Audit countersigns every admitted record with its own key, over: `record_id, admitted_node_id, admitted_seq, admitted_hlc, ingest_time, chain_prev_hash, producer_signature (or its absence), payload_hmac, key_class, purge_group_id`.

Three things this buys that the producer signature cannot:

1. **An independent time anchor.** If a producer's clock is contested, audit's admission order — a gap-free monotonic sequence on a node with its own attested `sync_quality` — is a second, independently signed ordering. Two contestable clocks are far better than one, because their disagreement is itself measurable.
2. **Proof of admission**, distinct from proof of authorship. A producer can prove it wrote a record; only audit can prove the record was admitted, when, in what order, and under which key class.
3. **Coverage of unverifiable records.** A record whose producer signature fails is quarantined and countersigned anyway, so the *fact of the failure* is non-repudiable even though the record is not.

`wrapped_dek` is deliberately **excluded** from the countersigned set, so re-wrap (§5.10) and key rotation do not invalidate it. Stated in both places because an implementer who adds it "for completeness" breaks reclassification.

### 8.5 `payload_hmac`, not `payload_sha256`, in the audit store

Document 11 §2.2 stores `payload_sha256` *"over plaintext canonical form"* in the outbox, and the producer signs over it. Audit additionally stores a **keyed** HMAC, and retains the HMAC — not the hash — in the purge record.

The reason is a real re-identification channel. A retained SHA-256 over purged plaintext lets anyone who can guess the plaintext *confirm* the guess. Domain payloads are highly guessable: enumerable identifiers, small field sets, short code values from published code sets (document 08 §2.5's 3-M CAUSE has nine values). Retaining a bare hash of purged content re-creates a confirmation oracle for exactly the content the purge destroyed, and does so inside the record of the remediation.

So: `payload_hmac = HMAC-SHA-256(hmac_key(key_class), canonical(plaintext))`, where the HMAC key is itself wrapped under the record's PG-KEK and **dies in the same shred**. After the purge, the HMAC is a useless 32 bytes: it still proves *that the purge record refers to a specific payload* (a pre-purge verifier can confirm it), and it cannot confirm any guess. The producer's signed `payload_sha256` remains inside the signed attestation for AU-10 verification of the record as authored — but it is not projected, not indexed, and not copied into the purge record.

### 8.6 Verification failure: quarantine and audit, never a silent drop

Document 11 §10.2 and DO-NOT item 21 are binding: *"Verification failure quarantines and audits; it never silently drops — a dropped record is a lost maintenance action, and a lost maintenance action is a lost label."*

| Failure | Response |
|---|---|
| Signature invalid | Admit to `quarantine_record` with `signature_status = unverifiable`, chained and countersigned. Publish `integrity.signature_verification_failed`. Page. **The content is retained**, encrypted, because it may be a genuine record from a corrupted store — or evidence of an attack |
| Signing key unknown | Same, `pending-key-registration`. A key rotation that outran its registration is a routine cause and must not destroy records |
| `sync_quality` absent | Reject at the API boundary with `422`. Document 11 §4.6's honesty rule means a producer with no reading reports `unsynced` and infinite dispersion; **absence is a bug, not a state** |
| `sync_quality` present but internally inconsistent | Admit, flag, `fathom_audit_attestation_anomalies_total`. Audit records what it was told and never corrects an attestation |
| Chain discontinuity detected | Admit, seal an out-of-band `integrity_checkpoint` recording the discontinuity, page. **Never repair the chain** — a repaired chain is a destroyed one |

---

## 9. Cross-repository correlation — AU-6(3)

Document 08 §3.5: *"**AU-6(3)** correlate ship and shore repositories."* Document 11 §10.5: *"`(producer_node_id, monotonic_seq)` plus `correlation_id` is the correlation key. Wall time is not, and cannot be, that key."*

### 9.1 The correlation keys

| Key | Correlates | Source |
|---|---|---|
| `(producer_slug, producer_node, monotonic_seq)` | A producer's stream across both repositories. **Gap-free**, so a gap is unambiguous loss, not a benign absence | 11 §4.2, §4.3 |
| `correlation_id` | One user or agent action across every service, both nodes, and every log line | 03 §4, 09 §4.8 |
| `causation_id` | Antecedent chains across topics | 03 §5.4 |
| `trace_ref` | Into Domino agent traces | 04 §11, 03 §8.5 |
| `(admitted_node_id, admitted_seq)` | Audit's own admission order per repository | §4.2 |
| `hlc` | A total order across nodes with no shared clock | 11 §4.4 |

**`producer_node` is what makes any of this work**, and document 11 §4.2 explains why it had to be added: an edge instance and the enterprise instance of one slug are *"two nodes each minting its own monotonic sequence, so `(telemetry, 41)` is ambiguous — two different events collide on the dedup key, and one is silently dropped."* For audit specifically, a collision would mean a shore record silently replacing a ship record — losing the audit record of a maintenance action performed at sea, which is the exact class of record the edge profile was grown to capture (D8).

### 9.2 The gap register — loss detection as a first-class artifact

```sql
CREATE TABLE sequence_watermark (
  producer_slug text NOT NULL, producer_node text NOT NULL,
  last_contiguous_seq bigint NOT NULL,
  highest_seen_seq    bigint NOT NULL,
  PRIMARY KEY (producer_slug, producer_node)
);
CREATE TABLE sequence_gap (
  producer_slug text NOT NULL, producer_node text NOT NULL,
  missing_seq   bigint NOT NULL,
  first_noticed_ingest_time timestamptz NOT NULL,
  state text NOT NULL,          -- open | re-requested | filled | unrecoverable
  PRIMARY KEY (producer_slug, producer_node, missing_seq)
);
```

- A gap is **detected**, not inferred: the sequence is gap-free by construction (document 11 §4.3), so a missing value is loss.
- Gaps are re-requested through the coordinator's resume-from-offset (document 11 §9.3), which returns `{producer_node: last_contiguous_seq}` and resumes at `+1`.
- **An `unrecoverable` gap is an accreditation-relevant fact and is reported as such**: it appears on `/readyz` as degraded, in `fathom_audit_sequence_gaps{producer,node,state}`, and in a signed `integrity_checkpoint`. An audit repository with silent holes is not an accreditation artifact; one with *declared, bounded, dated* holes still is.

### 9.3 Reconciliation on reconnect

Audit rides document 11 §9.3's coordinator, adding nothing of its own:

1. **Identity resolution precedes aggregate drain** (document 11 §8.3), so audit records referencing a provisional `installed_item_id` are correlated after the mapping is settled. Audit stores `identity_provisional` and resolves through `IdentityAliasResolver` (document 11 §8.4) at read time — **and never rewrites a stored subject**, per document 11 DO-NOT 13, whose third justification is D15 itself.
2. **Priority class 0 for remediation commands, then class 1 for the label stream** (§6.7's amendment, document 11 §9.3).
3. **Never `X-Backfill` for edge drain** (document 11 §9.3): a six-week-old audit record is a first emission of a real fact arriving late, not a replay. Marking it `replay: true` would suppress the side effects that must fire ashore.
4. **Shore ingress verifies before admitting**, stamps `ingest_time`, checks the classification label against the target's declared level, and records `sync_quality` permanently (document 11 §9.3b).
5. **Cross-anchoring** (§4.7) makes the hull's chain verifiable ashore without merging the repositories.

### 9.4 Why wall time cannot be the correlation key, restated for the assessor

An assessor's natural first question is "can you line up the ship's log and the shore's log?" The answer must not be "by timestamp," and the reason is documentary rather than theoretical: the Ubuntu 22.04 STIG rule **V-260520** mandates `makestep 1 -1` — unlimited backward steps on any offset above one second — and that step fires *precisely* when a disconnected node reconnects and drains its outbox (document 08 §3.3, document 03 §5.4). Compliance guarantees a non-monotonic clock at the exact moment correlation matters most.

So the ordering keys are sequence and HLC, and the *explanation* of any timestamp anomaly is the retained `sync_quality`: `step_occurred`, `dispersion_ms`, `time_source`, `seconds_since_sync`. Document 08 §3.3's SC-45/SC-45(1) parameters — **1 ms** audit time-stamp granularity, comparison **at least daily**, **1 s** resync threshold — are met on `recorded_at` and `ingest_time` (document 11 §10.5, AU-12(1)); where a hull cannot meet them from a shore path, the attestation says so, which document 03 §5.4 calls converting *"'our timestamps drifted' from an audit finding into a bounded, documented condition."*

Per document 08 §7: **AU-8(1) and AU-8(2) are withdrawn in SP 800-53 Rev 5** and are never cited; the parameters come from SC-45/SC-45(1) as selected by the DoD Zero Trust Overlays v1.1.

---

## 10. API surface

Base path `/api/v1/audit/` (document 03 §4, document 09 §7.1). Every operation carries `x-substitution` and `x-side-effects` via `packages/py-common`'s `operation()` helper (document 09 §5.1). **No operation is `x-agent-eligible`** (§14 item 9).

### 10.1 Record ingest

| Operation | `x-sub` | `x-side-effects` | Notes |
|---|---|---|---|
| `POST /records` | required | state-changing | Single record. `Idempotency-Key` required |
| `POST /records/bulk` | required | state-changing | The bulk, idempotent, fenced write path document 03 §4 requires (D10/C7). `X-Backfill` honoured |

**The primary ingest path is not HTTP — it is the event bus, and this is a deliberate architectural choice.** Domain provenance rides each service's own outbox (document 11 §2.3), so it is transactional with the state change, survives a six-week disconnection, and cannot be lost by an HTTP failure. The HTTP path exists for components with no outbox and no domain database — `gateway`, `tool-server`, and the Domino Endpoint proxy of document 03 §8.3 — and for them it is **fire-and-forget with local durable spooling**.

**A domain transaction never depends on an audit write succeeding.** Document 09 §4.4.2 sanctions the `any service → audit` HTTP edge for obligation 9, and it is easy to read that as "call audit synchronously in the request path." A service that did so would fail domain writes when audit was redeploying, and would have coupled every write path in the system to one platform service — for a platform service whose only job is to record what happened. §14 item 11 makes this a DO-NOT.

### 10.2 Query

| Operation | `x-sub` | `x-side-effects` | Notes |
|---|---|---|---|
| `GET /records` | required | none | Cursor-paginated, no total count. Filters: `correlation_id`, `record_type`, `producer_slug`, `producer_node`, `scope`, subject identifiers, `recorded_since` |
| `GET /records?changed_since=&cursor=` | required | none | Obligation 5. The rebuild path for the gateway's provenance view |
| `GET /records/{record_id}` | required | none | `ETag`. `410` + `urn:fathom:problem:audit:record-purged` when shredded |
| `GET /correlations/{correlation_id}` | required | none | The full correlated trace across both repositories. **`x-naming-carve-outs`**: query projection, no collection semantics (document 03 §4, C23) |
| `GET /attestations` | required | none | `sync_quality` forensics: filter by producer, node, `step_occurred`, dispersion threshold, interval |
| `GET /sequence-gaps` | required | none | §9.2's register. AU-6(3) evidence |

### 10.3 Integrity

| Operation | `x-sub` | `x-side-effects` | Notes |
|---|---|---|---|
| `POST /verifications` | required | none | **Compute-only `POST`** — exactly the case document 03 §4.1 sanctions (C1/D11). Verifies signatures, chain, and checkpoints over a stated interval; returns a signed verification report. Changes no state |
| `GET /checkpoints` | required | none | Signed Merkle checkpoints |
| `GET /quarantine` | required | none | Records that failed verification |
| `POST /quarantine/{id}/adjudications` | internal | state-changing | Human disposition of a quarantined record. `If-Match` |

### 10.4 Provenance — the surface that discharges obligation 9 for everyone

| Operation | `x-sub` | `x-side-effects` | Notes |
|---|---|---|---|
| `GET /lineage/{record_id}` | required | none | **Forward** closure: inputs, versions, computation references. *"Sufficient to trace any operator-visible figure to its sources"* (obligation 9). Depth-limited, cursor-paginated |
| `GET /lineage/{record_id}/dependents` | required | none | **Reverse** closure: what this contaminated. The purge-closure query |
| `POST /lineage/closures` | required | none | Compute-only. A closure over a selector set, with per-store holder resolution from the dissemination ledger. This is what phase 3 of §6.2 calls |

`GET /lineage/{record_id}` is the operation an operator's "why does this figure say 0.31?" ultimately resolves to, and it is why obligation 9 is a *contract* term rather than an aspiration: it is externally observable, and the conformance suite asserts that a published derived value's inputs are retrievable.

### 10.5 Remediation

| Operation | `x-sub` | `x-side-effects` | Notes |
|---|---|---|---|
| `POST /proposals` | required | state-changing | A `purge` (or `rewrap`) proposal per document 03 §7.2. `Idempotency-Key`. Rejects agent principals and `accountable_autonomous` |
| `POST /proposals/{id}/claim` | required | state-changing | Lease. Triggers phase 2 containment (§6.2) |
| `PATCH /proposals/{id}` | required | state-changing | Adjudication. `If-Match` required (D16, document 09 §5.4). Dual control enforced per §6.1 |
| `GET /purges` · `GET /purges/{id}` | required | none | State machine, sealed closure, per-store receipts, pending nodes |
| `GET /purges/{id}/certificate` | required | none | The certificate of §6.6, with §5.9's four proofs. **Query projection carve-out** |
| `POST /audit/remediation-receipts` | required | state-changing | A holder reporting a receipt for a purge it learned of via the **event** rather than the command (§6.5) |
| `POST /remediations` | required | state-changing | **Audit's own implementation of the universal operation** (§6.4). Audit purges its own store through the same contract every other service implements — no privileged internal path |
| `GET /remediations/{id}` | required | none | Per §6.4 |

Audit implementing `POST /remediations` against itself is not symmetry for its own sake: it means the conformance suite that proves nine services can purge also proves audit can, and it removes the special case that would otherwise be the least-tested code in the most important store.

### 10.6 Classification enforcement on every read

| Rule | Mechanism |
|---|---|
| Authorization in this service, never the gateway | `Depends(require_authz(...))` (document 09 §5.5), obligation 7 |
| **Filtering inside the query, never post-hoc** | The dominance predicate is SQL over `key_class`. Document 03 §7.3: *"post-filtering leaks the existence of records"* (D13) |
| Cursors must not leak | The cursor is over a stable sort key **within the filtered set**. A cursor whose gaps reveal suppressed rows is a leak, and `test_cursor_reveals_no_suppressed_rows` asserts it |
| No total counts | Document 03 §4 forbids them on unbounded collections; here a count is also an aggregation channel |
| `X-Classification` on every response, per-field redaction where levels mix | Document 03 §4, document 09 §5.5 |
| **Aggregation is a classification event** | Document 03 §7.3, D13. Any audit operation returning a count, rate, or rollup over mixed labels applies document 06 §5's exclusion-by-default policy and exposes `restricted_contributors_present` with a count — *"never a description, a system, or a magnitude"* |

The last row is easy to overlook in an audit service and is a real leak: "how many tool invocations touched asset X last week" moves when a compartmented record is added, which discloses its existence. Audit is the highest-cardinality aggregation surface in the system.

### 10.7 Effectiveness analytics — the home OD-7 asked for

**[AMENDMENT — closes a BLOCKING gap for the operator console.]** `27-fleet-status.md` §7 determines that warning lead-time coverage — document 06 §2's primary program effectiveness metric — belongs on *"the cross-cutting effectiveness-analytics path, anchored on `audit`"* (its own **OD-7**), specifies the full computation in its §7.5 to the precision an implementer needs, and declines to compute it itself so as not to fall into 06 §6's metric trap of owning both the thresholds and the scoreboard. No document before this amendment gave that anchor an actual operation, and `50-ui-design-system.md` §13 correction 2 found the gap when the approved wireframe's Fleet Overview and Vehicle Detail sheets rendered the metric as a headline KPI with nothing to call.

| Operation | `x-sub` | `x-side-effects` | Notes |
|---|---|---|---|
| `GET /effectiveness/warning-lead-time-coverage?scope=&id=&horizon_days=&stratum=` | required | none | Computes `27-fleet-status.md` §7.5's formula exactly — audit is already positioned to, since amendment 03-5 makes it a universal consumer of `risk_flag_transition`'s `changed_since` feed and of `maintenance_action.recorded`, the two streams the formula joins on `installed_item_id`. Response carries the coverage fraction **and** every disclosure §7.5 requires: the lead-time distribution (p10/p50/p90), the covered and uncovered counts, the chance reference and flag rate, and the achievable-ceiling fraction. `scope`/`id` per document 03 §5.4's vocabulary (`asset`, `tycom`, `fleet`); `stratum` selects `reference_class` and methodology version, per §7.5's rule that this figure is always stratified |

**Why here rather than a new platform service.** Audit already receives every event this computation needs (the universal-consumer amendment), already exports evaluation figures externally (`evaluation_export.completed`, §11.1), and already carries the aggregation-is-a-classification-event discipline of §10.6 that this figure needs too — a coverage rate computed over a mixed-classification population is exactly the aggregation channel §10.6's last row warns about, and `restricted_contributors_present` applies to this response the same way it applies to every other rollup this service serves. A dedicated effectiveness-analytics service was the alternative `27-fleet-status.md` §7.3 left open; this amendment takes the smaller step of using the component already positioned to answer, rather than adding an eighth platform-service inventory row for one metric.

**Response is read-only and attributed**, matching `27-fleet-status.md` §7.6's own constraint on its callers: `"source": "audit"`, `"computed_at"`, `"definition_ref"` pointing at that document's §7.5. Fleet Status's own display remains subject to that section's three constraints regardless of where the number now comes from.

---

## 11. Events

### 11.1 Published

All on audit's own topics, `fathom.audit.<aggregate>.v1`, through audit's own outbox (document 03 §15.11 binds audit too). **[AMENDMENT REQUIRED — 03-4]**: document 03 §6 has no audit-produced rows; §16.1 supplies them.

| Topic | Event | Payload summary | Consumers |
|---|---|---|---|
| `fathom.audit.remediation.v1` | `remediation.purge_executed` | purge_id, selectors, classification label, certificate_ref, **no content** | all nine, `gateway`, `knowledge-retrieval`, `notification`, `sync` |
| | `remediation.purge_certified` | purge_id, per-store outcomes, pending nodes, certificate_ref | as above |
| | `remediation.rewrap_executed` | record selectors, old and new `key_class`, authority | as above |
| | `remediation.quarantine_ordered` / `..._lifted` | selectors, reason class | as above |
| `fathom.audit.integrity.v1` | `integrity.checkpoint_sealed` | node, seq range, merkle_root, signature | `notification` |
| | `integrity.signature_verification_failed` | producer, node, seq, quarantine ref | `notification` |
| | `integrity.sequence_gap_unrecoverable` | producer, node, missing seq range | `notification` |
| `fathom.audit.attestation.v1` | `attestation.clock_step_recorded` | node, measured `skew_ms`, `sync_quality` | `notification` |
| `fathom.audit.evaluation_export.v1` | `evaluation_export.completed` | export id, interval, record counts, destination | `notification` |
| `fathom.audit.proposal.v1` | `proposal.created` / `.adjudicated` / `.expired` | Document 03 §7.2 | `gateway`, `notification` |

`attestation.clock_step_recorded` discharges document 11 §4.5: *"A backward step is an audit event, emitted to Audit with the measured `skew_ms`… a measured, timestamped, signed record of 'the STIG-mandated step fired here, by this much' is the difference between a bounded documented condition and a finding."*

`evaluation_export.completed` discharges document 03 §6's note that *"`anomaly_tag.*` reaches agent evaluation through `audit`, which exports to Domino's Experiment Manager. Domino workloads do not consume Kafka topics"* (C19).

**Compaction keys.** `fathom.audit.remediation.v1` is compacted on `purge_id`; `integrity.v1` on `(admitted_node_id, checkpoint_seq)`. Neither equals the partition key (`purge_id` scope / node), per document 03 §5.1's rule and document 11 §2.2's CHECK constraint (D5).

### 11.2 Consumed — the broad subscription, and the catalog problem it creates

Audit consumes **all 40 catalogued domain event types across the nine sub-applications, plus `proposal.created`, `proposal.adjudicated`, and `proposal.expired` on each of the nine `fathom.<slug>.proposal.v1` topics.** Every one is enumerated explicitly in `src/fathom_audit/events/catalog.py` as `CONSUMES`.

**Two constraints collide here, and the collision must be resolved rather than finessed.**

- Document 09 DO-NOT 14 and finding **C38**: *"no wildcard subscriptions"* — they cannot be conformance-tested and auto-subscribe to future events. So audit may not subscribe to `fathom.*`.
- Document 09 §8.2's Definition of Done: `catalog.py` `CONSUMES` must **equal** `helm/values.yaml` `events.consumes` must **equal** document 03 §6's catalog rows for this slug. But document 03 §6 names `audit` as a consumer in only **seven** rows: `criticality_tier.assigned`, `model_binding.activated`, `anomaly_tag.rejected`, `mission_review.completed`, `redesign_case.published`, `proposal.adjudicated`, `proposal.expired`.

So a correct, explicit, broad audit subscription **fails** `tools/check_event_catalog.py` today. The resolution is not to weaken the check — it is the mechanism that caught C3–C5 — but to fix the catalog. **[AMENDMENT REQUIRED — 03-5]**: document 03 §6 adds `audit` as a declared consumer on **every** row, with a standing note that audit is a universal consumer whose dependency is on the *envelope*, not the payload. §16.1 has the wording.

Consequences that follow, and each is a real Definition-of-Done item rather than a formality:

1. **Audit contributes a consumer-driven test to all nine producers' conformance suites** (document 03 §10, document 09 §4.7). One shared module per producer at `packages/contracts/conformance/<producer>/consumers/audit/`, asserting the four properties audit actually depends on: a complete document 03 §5.4 envelope including the whole `clock` block; a verifiable signature over document 11 §10.2's field set; a well-formed `ClassificationLabel` with `inherited_from[]` populated on derived aggregates; and `sync_quality` present with all five fields, `unsynced`/infinite permitted, absent not permitted. **Audit depends on the envelope, not the payload** — which is what makes one shared module viable across forty event types and keeps audit from becoming a consumer that breaks whenever any payload evolves.
2. **A payload schema change never breaks audit**, by construction: audit stores the payload as ciphertext plus a canonical hash and does not parse it. Provenance edges arrive as declared envelope-adjacent structures, not as payload interpretation.
3. **KEDA scaling on consumer lag** (document 09 §2.4), because audit is the broadest consumer in the system and the one most exposed to a reconnection burst (D28).
4. **`stalenessBoundSeconds` is declared but audit refuses no computation on it.** Document 03 §15.14 requires refusal only for computations with a correctness dependency on freshness; audit's job is to record what arrives, whenever it arrives. Lag is exposed on `/readyz` and `/metrics` per obligation 14, and a lagging audit consumer degrades readiness — it never rejects a record.

---

## 12. Testing

Four tiers per document 09 §4.7, plus the shared harnesses from document 11 §11 and `packages/contracts/conformance/audit/`. The two tests the parent requirement names explicitly are §12.2's end-to-end purge and §12.4's signature verification; both are Definition-of-Done items.

### 12.1 Fixtures this service must supply

```python
# platform/audit/tests/conformance/conftest.py — the four document 09 §4.7 fixtures, plus:

@pytest.fixture
async def softhsm_vault() -> KeyService:
    """SoftHSM2 behind PKCS#11 + Vault dev, exercising the REAL wrap/unwrap/derive/destroy
    code path (§5.5). A mock key service would leave the only code path that can
    irreversibly destroy data untested, which is unacceptable."""

@pytest.fixture
async def stub_holder() -> StubHolder:
    """A downstream consumer stub implementing POST /remediations and GET /remediations/{id}
    (§6.4), with an inspectable inbox, a real read-model table, and a real object-store
    bucket. It records every command and every event it receives and returns SIGNED
    receipts. This is what §12.2's notification assertion asserts against."""

@pytest.fixture
async def compacted_topic() -> CompactedTopic:
    """A Redpanda topic with compaction on an aggregate key != partition key, plus
    force_compaction() and consume_from_beginning() (§7.2)."""
```

### 12.2 The end-to-end purge test — required

```python
async def test_end_to_end_purge(audit, stub_holder, softhsm_vault, event_tap):
    """Trigger a purge; assert the record is unreadable HERE; assert a notification
    reached a stub downstream consumer AND that the consumer purged its own copy.
    [03 §13, D15]"""

    # ---- arrange: a spilled record with a derived dependent and a downstream copy
    src = await audit.admit(event_ingest(payload=b"MISLABELED", classification=U))
    drv = await audit.admit(prediction(inherited_from=[src.record_id]))     # §4.5 edge
    await stub_holder.consume(src)                                          # materialized copy
    assert await stub_holder.holds_content(src.event_id)
    assert await audit.read_payload(src.record_id) == b"MISLABELED"         # readable BEFORE

    # ---- act: propose, claim (containment), adjudicate under dual control, execute
    p = await audit.post_purge_proposal(selectors=[src.event_id],
                                        evidence=[spillage_report(source_trust="program")])
    await audit.claim(p)
    assert stub_holder.last_command.action == "quarantine"                  # §6.2 phase 2
    assert not await stub_holder.reads_allowed(src.event_id)
    await audit.adjudicate(p, adjudicators=[so_1, so_2], if_match=p.etag)   # §6.1

    purge = await audit.await_purge(p.purge_id)

    # ---- assert 1: unreadable in THIS service, and provably so
    with pytest.raises(RecordPurged):
        await audit.read_payload(src.record_id)
    assert (await audit.get_record(src.record_id)).status == 410
    assert await softhsm_vault.unwrap_fails(src.purge_group_id)             # §5.9 proof 2
    assert purge.certificate.hsm_destruction_receipt is not None            # §5.9 proof 1
    assert purge.certificate.unwrap_failure_samples                        # §5.9 proof 2
    assert purge.certificate.key_census.exports == 0                       # §5.9 proof 3
    assert verify_two_signatures(purge.certificate)                        # §5.9 proof 4

    # ---- assert 2: the closure caught the DERIVED record via inherited_from
    assert drv.record_id in purge.closure                                   # §4.5

    # ---- assert 3: the append-only invariant held
    assert await audit.row_count() == before_count + purge_record_count     # nothing deleted
    assert await audit.chain_verifies()                                     # §4.7 intact
    assert await audit.producer_signature_verifies(src.record_id)           # §8.1: shred != tamper

    # ---- assert 4: THE NOTIFICATION REACHED THE STUB, BOTH WAYS
    cmd = stub_holder.commands_for(purge.purge_id)                          # §6.4 command
    assert cmd.action == "purge" and cmd.selectors == [src.event_id]
    assert event_tap.saw("remediation.purge_executed", purge_id=purge.purge_id)   # §6.5 fact
    assert not await stub_holder.holds_content(src.event_id)                # it actually purged
    r = purge.receipts_by_holder["stub-holder"]
    assert r.outcome == "complete" and verify_holder_signature(r)            # §6.4 signed receipt
    assert purge.state == "certified"                                       # not partial

    # ---- assert 5: the purge is audited WITHOUT the purged content  [09 DO-NOT 24]
    rec = await audit.get_purge_record(purge.purge_id)
    assert b"MISLABELED" not in canonical_bytes(rec)
    assert rec.classification_label is not None and rec.payload_hmac is not None
    assert rec.immutability_class == "legally-immutable"
    assert rec.purge_group_id == REMEDIATION_INVARIANT_GROUP                # §5.4 class C
    with pytest.raises(PurgeGroupNotDestructible):                          # unreachable by design
        await audit.purge(selectors=[rec.record_id])
```

Companion cases, each required:

| Test | Asserts |
|---|---|
| `test_purge_survives_backup_restore` | Restore a pre-purge base backup; the record is **still** unreadable. This is §5.8's headline property and the one a delete-based design cannot pass |
| `test_purge_closure_includes_object_store_and_vector_index` | An `s3://` evidence artifact and a pgvector chunk both appear in the closure and both report receipts. **Deleting the embedding without the chunk text fails the test** |
| `test_purge_not_resurrected_by_read_model_rebuild` | Purge; rebuild the stub's read model from `changed_since`; the content does **not** return, because `remediation.*` is a standing filter on the rebuild path (§6.5) |
| `test_legally_immutable_record_is_rewrapped_not_destroyed` | A `maintenance_action_recorded` in the closure converts to re-wrap; low-side copies shredded; the canonical record readable at the new class; signature and chain verify (§5.10) |
| `test_legal_hold_refuses_purge` | Hard refusal naming the held records; no partial application; no force flag exists |
| `test_purge_aborts_when_closure_grew_since_adjudication` | A derived value published between seal and adjudication aborts the purge (§6.2 phase 4) |
| `test_purge_pending_at_disconnected_node_is_not_certified_complete` | A disconnected stub yields `certified-partial`, a pending metric, degraded `/readyz`, and a supplemental certificate on reconnect (§6.7) |
| `test_purge_requires_dual_control_and_if_match` | Single adjudicator → refused; missing `If-Match` → `428`; concurrent adjudication → `412` (D16) |
| `test_agent_principal_cannot_propose_or_adjudicate_purge` | `accountable_autonomous` and any `agent_id` refused (§6.1, D14) |
| `test_purge_resumable_at_every_injection_point` | Document 11 §11.1's matrix over the purge state machine: never half-applied, always resumable, key destruction only after every prior phase is durable |

### 12.3 Tombstone tests

| Test | Asserts |
|---|---|
| `test_redacted_replacement_preserves_compaction_invariant` | Exactly one live record at the compaction key; it is the redacted one; its signature verifies |
| `test_purge_tombstone_survives_recompaction` | Force compaction, roll segments, consume from offset 0: purged content absent, invariant holds, config restored (§7.2) |
| `test_null_tombstone_removes_key_where_key_is_the_spillage` | After `delete.retention.ms`, zero live records at the key; the fact survives in audit and the certificate (§7.1 step 2) |
| `test_compaction_key_never_equals_partition_key` | Every audit topic. CHECK constraint **and** test (D5, document 11 §11.3) |
| `test_ciphertext_in_uncompacted_segment_is_unreadable_after_shred` | §7.3: crypto-shred is the guarantee; compaction is hygiene |

### 12.4 Signature-verification tests — required

| Test | Asserts |
|---|---|
| `test_valid_signature_admitted_and_stored_verbatim` | `signature_status = verified`; the signature and key id are re-verifiable from the stored record with audit's verifier out of the loop |
| `test_tampered_payload_quarantined_not_dropped` | Content retained, `unverifiable`, `integrity.signature_verification_failed` published, page fired (document 11 DO-NOT 21) |
| **`test_tampered_sync_quality_fails_verification`** | Flip `step_occurred`, then `dispersion_ms`, then `time_source`; each fails. **This is the test that proves `sync_quality` is inside the signature** and that document 08 §3.3's "skew is indistinguishable from tampering" is closed (document 11 §10.2) |
| `test_signature_still_verifies_after_crypto_shred` | Shred, then verify: passes. Because the signature is over `payload_sha256` (§8.1). **The single most important interaction in this document** |
| `test_signature_still_verifies_after_rewrap` | Re-wrap changes `wrapped_dek` only; producer signature, countersignature, and chain all verify (§5.10, §8.4) |
| `test_infinite_dispersion_round_trips_byte_identically` | `dispersion_ms = +inf` survives storage and verification (§4.4, §8.3) |
| `test_admission_countersignature_independent_of_producer` | A record with an absent producer signature is still countersigned and chained (§8.4) |
| `test_chain_break_is_detected_never_repaired` | Discontinuity → out-of-band checkpoint + page; no repair path exists (§8.6) |
| `test_payload_hmac_is_keyed_and_dies_with_the_group` | Pre-purge: a correct guess confirms. Post-purge: it cannot (§8.5) |

### 12.5 Static gates (CI `lint` stage, per document 09 §6.2 job 1)

Document 11 §11.5's nine gates apply in full, plus:

1. **No `ExportKey`, `clone`, `backup`, or `derive-to-external` call for any Tier-1 or Tier-2 key.** §5.2 Decision 2 — this is the gate that makes §5.9 proof 3 an architectural claim rather than a hope.
2. **No plaintext payload column, no plaintext payload log line, no plaintext in any exception message or problem `detail`.**
3. **No insert into `audit_record` outside `AuditWriter.admit()`** — bypassing it would skip verification, countersignature, chain extension, and encryption.
4. **No `DELETE` or content-column `UPDATE` on `audit_record`** anywhere in the codebase. The only permitted `UPDATE` targets are `purged_by`, `purged_at`, `wrapped_dek`, `wrapped_dek_key_id`, `key_class`, `rewrapped_from_key_class`, and `legal_hold`, asserted column-by-column.
5. **No `x-agent-eligible: true` on any audit operation** (§14 item 9).
6. **No SoftHSM key id valid in a non-dev `Settings`** — asserted at startup, not only in CI.
7. **No post-filtering**: no Python-side classification filtering after a query; the dominance predicate must appear in SQL (D13).

### 12.6 Test tiers

| Tier | Content |
|---|---|
| `tests/unit/` | `key_class` and `purge_group_id` determinism and canonicality; closure computation over synthetic provenance graphs; `ImmutabilityClass` decision table |
| `tests/integration/` | Real Postgres + real Redpanda + SoftHSM/Vault via testcontainers. Every §12.2–§12.4 case |
| `tests/contract/` | Document 09 §4.7's six, plus `test_no_operation_is_agent_eligible` and `test_purged_record_returns_410_with_no_content` |
| `tests/conformance/` | `packages/contracts/conformance/audit/` unmodified, plus `_shared/remediation/` (§6.4) and `_shared/sync/` (document 11 §11) |

---

## 13. Deployment

Document 09 §4.2's skeleton, unvaried. `platform/audit/`, package `fathom_audit`, database `fathom-audit-pg`, consumer group `fathom-audit-v1`.

### 13.1 `values.yaml` deltas from document 09 §4.4.1

```yaml
slug: audit
apiMajor: 1

app:
  config:
    stalenessBoundSeconds: 600          # exposed on /readyz; audit refuses no work on it (§11.2)
    inlinePayloadMaxBytes: 65536        # above this -> payload_ref [11 §2.6]
    attestationPartitionInterval: 1mo   # §4.4
    purgeGroupCacheSize: 4096

keyService:                             # [ESTABLISHED HERE] — new section, audit-specific
  vaultAddr: https://vault.fathom-data.svc.cluster.local:8200
  transitMount: fathom-audit
  pkcs11Library: /usr/lib/softhsm/libsofthsm2.so   # dev only; HSM client lib in cluster
  rootKeyPerLevel: { U: fathom-root-u, CUI: fathom-root-cui }
  requireHardwareBackedKeys: true       # startup FAILS if the module reports software-only
  dualControlOnDestroy: true            # Vault policy; asserted at startup, not assumed

database:
  clusterName: fathom-audit-pg
  name: audit

events:
  consumerGroup: fathom-audit-v1
  publishes: [fathom.audit.remediation.v1, fathom.audit.integrity.v1,
              fathom.audit.attestation.v1, fathom.audit.evaluation_export.v1,
              fathom.audit.proposal.v1]
  consumes: [ ... all 40 domain event types + 9 proposal topics, enumerated ... ]

autoscaling:
  mode: keda                            # broadest consumer; reconnection bursts [D28]
  kedaLagThreshold: 5000

networkPolicy:
  ingress:
    fromServices: [gateway, registry, telemetry, pdm, fleet-status, maintenance,
                   supply, pma, failure-intel, design-advisory,
                   auth, reference-data, knowledge-retrieval, notification,
                   tool-server, sync]
  egress:
    toOwnDatabase: true
    toEventBus: true
    toServices: [auth]                  # NOT reference-data: audit resolves no taxonomy
    toKeyService: true                  # ← NEW SANCTIONED EDGE. [AMENDMENT REQUIRED — 09-1]
    toObjectStore: true                 # ← NEW SANCTIONED EDGE. [AMENDMENT REQUIRED — 09-1]
```

**Two new NetworkPolicy edges, and document 09 DO-NOT 30 requires an ADR plus a change to document 09 for each.** They are `docs/adr/0001-audit-key-service-edge.md` and `docs/adr/0002-audit-object-store-edge.md`, and §16.3 has the document 09 §4.4.2 table rows. The helm-unittest assertion that the rendered egress peer set **equals** the values-declared set (document 09 §4.4.1, §8.6) applies unchanged — audit gets no exemption from the invariant that makes principle 1 testable.

**Audit's ingress set is the broadest in the system, and that is correct rather than a smell**: document 09 §4.4.2 sanctions `any service → audit` for obligation 9. The egress set is correspondingly narrow: audit calls `auth` for JWKS, the key service, the object store, its own database, and the broker. It calls **no sub-application** — which is what keeps a service that everything depends on from depending on anything.

### 13.2 Readiness

Document 09 §5.6's five mandatory checks, plus:

| Check | Fails when |
|---|---|
| `key_service` | Vault/HSM unreachable, or reports software-only keys while `requireHardwareBackedKeys` is set. **Audit must not accept records it cannot encrypt** |
| `chain_head` | The chain head does not verify against the latest checkpoint |
| `pending_purges` | Degraded (not failed) while any purge has pending nodes (§6.7) |
| `sequence_gaps` | Degraded while any gap is `open` or `unrecoverable` (§9.2) |
| `divergence` | Degraded per §6.7's `ALERT_AND_DEGRADE`. **Never read-only** |

### 13.3 Metrics

Document 09 §5.6's fixed names, plus:

```
fathom_audit_records_admitted_total{record_type,producer,node,signature_status}
fathom_audit_signature_failures_total{producer,node,reason}
fathom_audit_provenance_incomplete_total{producer,event_type}
fathom_audit_attestation_anomalies_total{producer,node}
fathom_audit_sequence_gaps{producer,node,state}
fathom_audit_purges_total{outcome}                      # certified|certified-partial|aborted|refused
fathom_audit_purge_pending_nodes{purge_id}
fathom_audit_purge_duration_seconds{phase}              # monotonic-measured
fathom_audit_key_classes_registered                     # §5.3 explosion alarm
fathom_audit_purge_groups_total{record_class}
fathom_audit_unwrap_failures_total{reason}              # key-destroyed vs key-unavailable
fathom_audit_rewraps_total{from_key_class,to_key_class}
```

---

## 14. Explicit DO-NOT list

Each item carries the finding or citation that makes it a defect rather than a preference.

1. **Do not create a store with no purge path. Do not treat append-only as an excuse for unrecoverable data.** Document 03 principle 9: *"Every store has a remediation path. Append-only is an integrity property, not an excuse for unrecoverable data."* This service is where that principle either holds for the whole platform or fails for it. *(**D15**; 03 §13, 09 DO-NOT 24)*
2. **Do not retain purged content in the record of its purge.** No excerpt, no quotation, no field value, no paraphrase, no reversible digest. A bare `SHA-256` over purged plaintext is a confirmation oracle for guessable payloads — retain a **keyed** HMAC whose key dies in the same shred. *(§6.6, §8.5; **D15**)*
3. **Do not make a purge unauditable.** A purge leaves a permanent, append-only, countersigned record in the non-destructible `remediation-invariant` key group. There is no purge that erases the fact of a purge. *(§5.4, §6.6; 03 §13)*
4. **Do not delete or modify a row in `audit_record` to purge it.** Destroy key material in the HSM. A `DELETE` lives on in WAL, base backups, replicas, and tape, so "we deleted it" is unprovable and probably false — and it breaks the append-only invariant document 04 §11 makes an accreditation property. *(§5.2 Decision 1, §5.8)*
5. **Do not export a Tier-1 or Tier-2 key, or a shred nonce, in any form** — not wrapped, not escrowed, not to backup, not to the edge. Unreadability is only provable if no copy can exist outside the module that destroyed it. *(§5.2 Decision 2, §5.9 proof 3)*
6. **Do not use one key per classification level as the shred handle.** Destroying it destroys every record at that level, so the purge would never be authorized and D15 would be open with more paperwork. Purge granularity must equal key granularity. *(§5.1, §5.4)*
7. **Do not destroy a `legally-immutable` record.** Re-wrap upward and shred the low-side copies. The distinction is document 03 §13.3's requirement, and destroying an anomaly tag, a 3-M maintenance action, a legally effective adjudication, or a model-binding approval destroys evidence, a statutory record, accountability, or the accreditation basis respectively. *(§4.1, §5.10; 03 §11, §13.3)*
8. **Do not post-filter for classification, and do not leak through counts or cursors.** Filtering happens inside the query; removing results afterward leaks the existence of records. Audit is the highest-cardinality aggregation surface in the system, so document 03 §7.3's "aggregation is a classification event" binds hardest here. *(**D13**; 03 §7.3, §12)*
9. **Do not make any audit operation `x-agent-eligible`.** The audit store is every domain's records at the union of their labels — an agent tool over it is a D13 aggregation channel; its tool-invocation payloads contain retrieved corpus text, so it is a D14 amplifier; and an agent that can read the audit store can read the evidence for every proposal it might make. *(**D13**, **D14**; 03 §8.1, §9)*
10. **Do not let an agent propose or adjudicate a purge.** `accountable_autonomous` principals and any proposal carrying an `agent_id` are refused. A prompt-injected purge is the worst available outcome in this system. *(**D14**; 03 §8.3, §9)*
11. **Do not make a domain transaction's success depend on an audit HTTP call.** Provenance rides the producing service's own outbox — transactional, survives six weeks of disconnection, cannot be lost by an HTTP failure. The sanctioned HTTP edge is for components with no outbox, fire-and-forget with local spooling. *(§10.1; 03 §5.2, 09 §4.4.2)*
12. **Do not publish a purge order as an event.** Events carry facts, not instructions. The order goes over `POST /{slug}/remediations` and is acknowledged with a signed receipt; the *fact* that a purge occurred is published, and it carries no content. *(03 principle 3; §6.5)*
13. **Do not treat a purge as complete while any holder is unreachable.** `certified-partial` is never reported, displayed, or logged as "complete." A hull dark for six weeks holding a copy means the purge is incomplete, and saying so is the whole value of the certificate. *(§6.7)*
14. **Do not forget the rebuild path.** A read model rebuilt from `changed_since` after a purge resurrects the content unless `remediation.*` is a standing filter on the rebuild path. This is the most easily missed failure mode in the design. *(§6.5; **D5**)*
15. **Do not rely on log compaction as a deletion guarantee.** The active segment is never compacted, and `min.cleanable.dirty.ratio` is not a deadline. Crypto-shred is the guarantee; forced compaction plus a re-consume verification is hygiene. *(§7.2, §7.3; 03 §13.4)*
16. **Do not set the compaction key equal to the partition key**, on audit's topics or anyone's. *(**D5**; 03 §5.1, 11 §2.2)*
17. **Do not rewrite a published event, ever** — not to correct a label, not to canonicalize a provisional identity, not to redact. It breaks AU-10 signatures, violates append-only policies, and requires the coordinated global mutation D15 identifies as the blocker. Publish a redacted replacement or a mapping event. *(**D15**; 11 §8.4, DO-NOT 13)*
18. **Do not repair a broken hash chain.** A repaired chain is a destroyed one. Seal an out-of-band checkpoint recording the discontinuity, and page. *(§8.6; AU-9(3), 08 §3.5)*
19. **Do not drop a record that fails signature verification.** Quarantine and audit. *"A dropped record is a lost maintenance action, and a lost maintenance action is a lost label."* *(11 §10.2, DO-NOT 21)*
20. **Do not store `sync_quality` separately from the signature that covers it, and do not prune it.** Skew is indistinguishable from tampering to an assessor; retained separately it can silently diverge from what it signs, and pruned it takes the only means of re-deriving true ordering with it. *(§8.3; 03 §5.4, 08 §3.3, 11 DO-NOT 20)*
21. **Do not fabricate a `sync_quality` value.** `unsynced` with infinite dispersion is the honest report, and the schema must accept `Infinity`. *(11 §4.6, DO-NOT 19)*
22. **Do not compare, sort, `max`, or `min` over `source_time`, `occurred_at`, or `recorded_at`.** Order on `(producer_slug, producer_node, monotonic_seq)` or the HLC; measure durations monotonically. *(**D29**; 03 §5.4, 11 §4.7, §11.5)*
23. **Do not cite AU-8(1) or AU-8(2).** Withdrawn in SP 800-53 Rev 5; the parameters live in SC-45/SC-45(1) as selected by the DoD Zero Trust Overlays. *(08 §7, §6)*
24. **Do not cite a control with no basis in document 08.** The set is CP-10(2), AU-4(1), AU-6(3), AU-9(3), AU-10, AU-12(1), SC-8/SC-8(1), SC-16, SC-28/SC-28(1) from §3.5, and SC-45/SC-45(1) from §3.3. Adding an invented control is exactly the defect document 08 §7 exists to prevent. *(08 §3.3, §3.5)*
25. **Do not use "FOUO" or "U//FOUO", and do not put a caveat outside the ten authorized Limited Dissemination Controls into a label or a `key_class`.** Retired markings; lint rule `FTH005` rejects them as literals. *(08 §5.5; 03 §7.3, 10 §4.8)*
26. **Do not invent quantities.** Retention periods, attestation volumes, and storage envelopes come from document 06 §7 or are recorded as open questions. *(**D37**; 09 DO-NOT 31)*
27. **Do not make audit read-only when its divergence budget breaches.** Refusing audit writes stops the accountability record for every service on the hull. Alert and degrade. *(§6.7)*
28. **Do not use a wildcard subscription** to implement the broad consumption of §11.2. Enumerate all forty-nine event types, and fix document 03 §6's catalog instead of weakening the check that caught C3–C5. *(**C38**; 09 DO-NOT 14)*

---

## 15. Definition of Done

**Document 09 §8 applies in full and nothing is removed.** Every box in §8.1 through §8.7 must be ticked for `platform/audit` before this service is complete. The items below are **additional**.

### 15.1 Data model and immutability

- [ ] Every record type in §4.1 carries an `ImmutabilityClass`, CHECK-constrained, and the per-store declaration document 03 §13.3 requires is in the README. *(03 §13.3)*
- [ ] `legal_hold` is enforced as a hard refusal at proposal validation, with no force flag anywhere in the codebase. *(§4.1)*
- [ ] No plaintext payload column exists; static gate §12.5.2 green. *(§5.6)*
- [ ] `AuditWriter.admit()` is the only insert path; static gate §12.5.3 green. *(§5.6)*
- [ ] No `DELETE` and no content-column `UPDATE` on `audit_record`; static gate §12.5.4 green, column-by-column. *(§5.8)*
- [ ] `attestation` stores the whole signed `clock` block byte-identically; `attestation_index` is a projection only; `Infinity` round-trips. *(§4.4, §8.3)*
- [ ] Provenance edges are written for all seven `edge_kind` values, and an `event_ingest` for a derived aggregate with zero `label_inheritance` edges is **admitted and flagged**, never dropped. *(§4.5; obligation 9)*
- [ ] The dissemination ledger records `materialized` correctly, and rebuilds via `ChangedSinceRebuilder` produce ledger rows. *(§4.6; amendment 11-1)*

### 15.2 Key hierarchy

- [ ] All four tiers implemented as specified; `key_class` and `purge_group_id` deterministic, canonical, and identical across language bindings. *(§5.2–§5.4)*
- [ ] The `remediation-invariant` group's shred nonce is registered **non-destructible in HSM policy**, and a test proves a purge targeting a purge record raises. *(§5.4, §12.2)*
- [ ] No export/clone/backup/derive-to-external path for any Tier-1 or Tier-2 key; static gate §12.5.1 green. *(§5.2 Decision 2)*
- [ ] `requireHardwareBackedKeys` fails startup against a software-only module; no SoftHSM key id is valid outside dev. *(§13.1, §12.5.6)*
- [ ] AAD binds `key_class`, `purge_group_id`, classification, and producer identity; a ciphertext moved to a differently-labelled row fails to decrypt. *(§5.6; SC-16)*
- [ ] Vault destroy policy requires dual control, asserted at startup rather than assumed. *(§13.1)*

### 15.3 Purge protocol

- [ ] All seven phases implemented, with containment at **claim** rather than at adjudication. *(§6.2)*
- [ ] `security_officer` authority class, two-person integrity, and `fleet_authority` counter-signature at class/fleet scope. *(§6.1; amendment 03-1)*
- [ ] A purge is a `Proposal` with claim, `If-Match`, dual control, re-validation, and `valid_until`; closure growth aborts. *(§6.1, §6.2; **D16**)*
- [ ] `POST /remediations` and `GET /remediations/{id}` implemented **by audit against its own store**, through the same contract every other service implements. *(§6.4, §10.5)*
- [ ] All four proofs of §5.9 produced for every purge; a certificate cannot seal without negative unwrap evidence. *(§5.9)*
- [ ] `certified-partial` never reported as complete; pending nodes on `/readyz`, on the metric, and in the operator interface. *(§6.7)*
- [ ] Purge order follows §6.3's ten steps, audit ninth and key destruction tenth. *(§6.3)*
- [ ] Remediation commands ride coordinator priority class 0. *(§6.7; amendment 11-2)*
- [ ] Audit's `on_breach` is `ALERT_AND_DEGRADE` and audit never refuses a write; its divergence budget exceeds the scripted patrol length. *(§6.7; amendment 11-3)*

### 15.4 Tombstones, signing, correlation

- [ ] Redacted-replacement publication at the compaction key, plus the null tombstone only where the key is the spillage. *(§7.1)*
- [ ] Forced compaction with the four-step verification and configuration restoration, recorded in the receipt. *(§7.2)*
- [ ] Producer signature verified over document 11 §10.2's exact field set and stored verbatim with its key id. *(§8.2)*
- [ ] Admission countersignature excludes `wrapped_dek`, so re-wrap and rotation do not invalidate it. *(§8.4)*
- [ ] `payload_hmac` is keyed and its key dies with the group; no bare hash of purged plaintext is retained, indexed, or projected. *(§8.5)*
- [ ] Hash chain per node, Merkle checkpoints at least hourly, cross-anchored on reconnection; no repair path. *(§4.7, §8.6)*
- [ ] Gap register populated, gaps re-requested, `unrecoverable` gaps surfaced on `/readyz`, in metrics, and in a signed checkpoint. *(§9.2; AU-6(3))*
- [ ] Control-mapping evidence produced for CP-10(2), AU-4(1), AU-6(3), AU-9(3), AU-10, AU-12(1), SC-8/SC-8(1), SC-16, SC-28/SC-28(1), SC-45/SC-45(1), and referenced from the SSP. **AU-8(1)/(2) absent.** *(08 §3.3, §3.5, §7)*

### 15.5 Events, API, tests, deployment

- [ ] All forty-nine consumed event types enumerated explicitly; no wildcard; `catalog.py` = `values.yaml` = document 03 §6 after amendment 03-5; `tools/check_event_catalog.py` exits 0. *(§11.2; **C38**, C3–C5)*
- [ ] Consumer-driven tests contributed to all nine producers' suites, asserting the four envelope properties. *(§11.2; 03 §10)*
- [ ] Audit's published events registered in document 03 §6 (amendment 03-4) and in `asyncapi.yaml` with no drift. *(§11.1)*
- [ ] No operation is `x-agent-eligible`; static gate §12.5.5 green; contract test asserts it. *(§14 item 9)*
- [ ] `410` + `urn:fathom:problem:audit:record-purged` for a shredded record, with no content; `503` distinguished for key-service unavailability. *(§5.7)*
- [ ] Classification filtering in SQL; cursor-leak test green; no total counts; aggregation policy applied to every count-returning operation. *(§10.6; **D13**)*
- [ ] **`test_end_to_end_purge` green**, including the stub-holder notification assertions, the backup-restore case, and the audited-without-content assertion. *(§12.2)*
- [ ] **All of §12.4's signature tests green**, in particular `test_tampered_sync_quality_fails_verification` and `test_signature_still_verifies_after_crypto_shred`. *(§12.4)*
- [ ] Document 11 §11's harnesses collected unmodified: full fault-injection matrix, all clock-skew tests, `test_d29_source_time_comparison_raises`. *(11 §11, §14)*
- [ ] Two ADRs committed for the new NetworkPolicy edges; helm-unittest egress-equality assertion green. *(§13.1; 09 §4.4.2, DO-NOT 30)*
- [ ] Both edge and enterprise profiles deployed and reconciled in test, including a purge ordered ashore for an edge-held record across a simulated six-week disconnection. *(§1.3, §6.7, §9.3)*

---

## 16. Amendments required to upstream documents

Every item is a change this document's design requires in a document upstream of it. An implementer follows this document immediately; each amendment is release-blocking because document 03 is what binds substitutes.

**All fourteen amendments below (03-1 through 03-6, 11-1 through 11-5, 09-1 through 09-3) have been applied** to their respective documents, verified against the live files rather than assumed from this table. Two ADRs were written for the 09-1 NetworkPolicy edges (`docs/adr/0001-audit-key-service-edge.md`, `docs/adr/0002-audit-object-store-edge.md`) per document 09 DO-NOT 30's requirement. `python3 tools/check_event_catalog.py` passes with the amended catalog.

### 16.1 Document 03 — Integration Contracts

| # | Section | Edit |
|---|---|---|
| **03-1** | §7.2.1 | Add `security_officer` to `AuthorityClass` (ISSM/ISSO). Add its row to the class table. Add a `purge` row to the minimum-authority table: `item`/`asset` → `security_officer` + dual control; `class`/`fleet` → `security_officer` + dual control + `fleet_authority` counter-signature. Reasoning per §6.1: §7.2.1's existing classes are operational and engineering roles, and document 08 §5.4 places classification determinations with the OCA and the SCG, *"not… engineering."* |
| **03-2** | §7.2 | Add `purge` (and `rewrap`) to `Proposal.kind`. Add the standing rule that a purge proposal may never be created or adjudicated by an agent principal or an `accountable_autonomous` identity. |
| **03-3** | §13 + §15 | Add obligation **17**, as a **contract term** (externally observable, binding on substitutes): *"Exposes a remediation operation (`POST /{slug}/remediations`) accepting quarantine, purge, rewrap, and release actions over declared selectors, idempotent on the remediation id, returning a receipt signed by the implementation and stating, per store it owns, whether that store is legally immutable or operationally append-only and which mechanism was used."* Cross-reference from §13.2 and §13.3. |
| **03-4** | §6 | Add an "Audit & Provenance (`audit`)" producer block with the five topics and ten event types of §11.1. Document 03 §6 currently lists audit only as a consumer, so a conformant audit service publishes events no catalog declares. |
| **03-5** | §6 | Add `audit` as a declared consumer on **every** row, with a standing note: *"`audit` is a universal consumer. Its declared dependency is on the §5.4 envelope — the complete `clock` block, the signature, and a well-formed `ClassificationLabel` with `inherited_from[]` on derived aggregates — not on any payload. Its consumer-driven tests assert envelope properties only, so payload evolution never breaks it."* Without this, an explicit non-wildcard audit subscription fails document 09 §8.2's three-way catalog equality. |
| **03-6** | §5.4 | Adopt `producer_node` explicitly in the dedup and ordering key, as document 11 §13 item 1 already requests. Audit's cross-repository correlation (§9) depends on it, and without it a shore audit record silently displaces a ship record. |

### 16.2 Document 11 — Outbox & Sync Library

| # | Section | Edit |
|---|---|---|
| **11-1** | §10.5 | The inbox must export a **dissemination record** per apply — `(source_event_id, holder_slug, holder_node, holder_store, applied_at, materialized)` — alongside the existing `sync_quality` export, **and `ChangedSinceRebuilder` must do the same for every rebuild**. §4.6 explains why the rebuild path is the one that resurrects purged content. |
| **11-2** | §9.3 | Add a **priority class 0-R** above provisional identity: remediation commands and purge receipts. A spillage remediation outranks a data-quality concern. |
| **11-3** | §9.1 | `on_breach` currently names `EXPLICIT_READ_ONLY` as *"the only permitted value."* Add `ALERT_AND_DEGRADE`, permitted **only** for the audit store, because refusing audit writes stops the accountability record for every service on the hull and no document-08 control requires it. |
| **11-4** | §10.1, §13 OQ-10 | **Answered here:** Audit accepts a per-event attestation at full event volume (§4.4) — monthly range partitions, no domain payload, class-day purge groups, `Infinity`-capable dispersion, partitions transferred to object storage under AU-4(1) and never dropped. The absolute sizing is blocked on a per-topic event rate the capacity model does not yet contain (§17 OQ-3). Also confirm that `purge_by_selector` accepts a coordinator-issued `remediation_id` and returns a **signed** receipt per §6.4. |
| **11-5** | §10.2 | State explicitly that the signature covers `payload_sha256` **and not the payload**, and that `wrapped_dek` / key-wrapping metadata are **excluded** from the signed set. Both properties are load-bearing for §8.1 and §5.10; an implementer who "completes" the field set breaks purge and reclassification simultaneously. |

### 16.3 Document 09 — Monorepo & Conventions

| # | Section | Edit |
|---|---|---|
| **09-1** | §4.4.2 sanctioned-edge table | Add two rows: **`audit` → key service (Vault/HSM)** — *"the only service holding wrap/unwrap authority; §5.2 Decision 2 forbids exporting key material, so the module must be reachable"*; and **`audit` → object store** — *"oversized payloads by reference, encrypted under the same envelope (§5.6); 11 §10.1's rule that a reference is not an exemption."* Each with an ADR under `docs/adr/`. |
| **09-2** | §8.4 | The existing item *"A declared purge path for every store this service owns, stating whether it is legally immutable or operationally append-only"* should additionally require the `POST /{slug}/remediations` implementation and its conformance collection, once amendment 03-3 lands. |
| **09-3** | §4.4.1 | Note that `values.networkPolicy.egress` gains optional `toKeyService` and `toObjectStore` booleans, rendered from values and from nothing else, so the egress-equality helm-unittest assertion still holds exactly. |

---

## 17. Open questions

Recorded rather than resolved locally, per document 09 §1.3 and DO-NOT 31.

| # | Question | Impact if unresolved | Interim position |
|---|---|---|---|
| **OQ-1** | **Retention period for `program`-class records** (`event_ingest`, `prediction_recorded`, `tool_invocation`, `agent_run`). No architecture document states one, and document 04 §11 says retention *"should be treated as external obligations rather than internal preferences"* without naming the obligation | Storage envelope unbounded; expiry indistinguishable from purge in planning | Indefinite retention, partitions transferred to object storage under AU-4(1). Raise with the authorizing official; do not invent a period |
| **OQ-2** | **Domino trace purge.** Can a trace be deleted from Domino's trace store, and by what interface? Document 02 rules out five assumed capabilities (D26) and document 03 §13.2 explicitly requires *"Domino-side traces"* in the purge protocol | The purge certificate reports `pending-at-node` for Domino permanently, which is honest but unsatisfying to an assessor | Delete the audit-side export and record that the upstream trace could not be reached. Escalate to the Domino platform request list in document 02 §6 |
| **OQ-3** | **Per-topic event rate.** Document 06 §7 gives sample rates and prediction counts but no event rate, and document 03 §6 is batch-level, so samples do not map to events | Attestation-table sizing (§4.4) and audit's storage envelope cannot be computed. Answers document 11 OQ-10 only qualitatively | Declared shape, no number. Raise against the capacity model, which document 05 D37 already flags as incomplete |
| **OQ-4** | **Who is the `security_officer`, organizationally**, and is a second one available afloat? Two-person integrity requires two cleared individuals, and a hull may carry one | A purge of an edge-held record may be unadjudicable afloat | Purge adjudication is shore-side; the hull executes an adjudicated command. This is defensible but should be confirmed with the program |
| **OQ-5** | **HSM procurement and the edge footprint.** One HSM per edge-profiled hull is a hardware line item, alongside document 08 §9's stratum-1 time reference | §5.11's edge key custody is unimplementable without it, and a shared shore HSM would break the six-week disconnection case | Raise with document 08 §9's immediate-actions list, where the time-reference budget item already sits |
| **OQ-6** | **Purge-group key count at production scale.** §5.4's 16-byte-nonce-per-group design bounds the cost, but ~300 hulls at production volume is untested against real HSM capacity and destroy-operation throughput | A purge of a large closure could take an unacceptable time inside the module | Measure against the selected HSM before hull provisioning. The escape hatch is a coarser class-A grouping, which costs remediation granularity and must be an explicit, recorded trade |
| **OQ-7** | **Sibling build documents 20–28** do not yet exist. Each must declare its stores' immutability classes and implement `POST /remediations` | Nine services could each invent a remediation surface | §6.4's request/response shape and the `_shared/remediation/` conformance suite are the specification. Any sibling document that varies it needs an ADR |
