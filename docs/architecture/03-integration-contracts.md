# Phase 2 — Integration Contracts

| | |
|---|---|
| **Status** | Draft rev 2 — incorporates review remediation tranche 1 |
| **Scope** | The contracts binding sub-applications to one another and to agents: canonical identity, API conventions, the event backbone and catalog, shared payload schemas, agent authority and tool surfaces, the substitution protocol, edge reconciliation, and data-remediation obligations |
| **Companion documents** | [01 — System Architecture](01-system-architecture.md) · [04 — Sub-Application Architectures](04-subapplication-architectures.md) · [05 — Review Findings](05-architecture-review-findings.md) |
| **Classification** | Internal |

## Revision history

| Rev | Change |
|---|---|
| 1 | Initial contracts: conventions, event backbone and catalog, shared schemas, substitution protocol, edge policy, agent tool binding |
| 2 | Review remediation tranche 1. Canonical slugs and identity model corrected (`installed_item_id`, `SystemRef`, equipment family); inbox semantics corrected; baseline epoch fencing and antecedent ordering added; compaction key separated from partition key; snapshot and backfill reads made mandatory; agent eligibility moved from HTTP method to declared side-effect class; agent authority classes added for autonomous runs; obligations split into externally conformable contract terms and program implementation terms; `FailurePrediction` and `Proposal` schemas corrected; untrusted-content and data-remediation sections added; conflict-policy defaults added. Traceability to findings in document 05 is cited inline as `[Dn]` and `[Cn]` |

---

## 1. Why this document precedes the sub-application designs

Phase 1 established that a sub-application is a discipline deployed independently, and that an entire discipline may be assumed by a partner system. That property is delivered by contracts, not by intentions. If the contracts are specified after the sub-applications, each sub-application will have encoded assumptions about its neighbors that the contracts must then accommodate, and the substitution property will be lost in the accommodation.

The contracts specified here are binding on document 04 and on all Phase 3 detailed designs. A sub-application may choose any internal structure; it may not vary its contract surface.

---

## 2. Contract principles

1. **The contract is the API plus the published events plus the conformance suite.** Nothing else is a contract. Database schemas, internal message formats, and library types are private to a sub-application regardless of who can technically reach them.
2. **No synchronous cross-sub-application calls on a compute path.** A sub-application that needs another's data at compute time maintains a local read model, populated from events. Synchronous reads are permitted only for user-facing composition, and that composition is performed by the API gateway rather than by sub-applications calling one another in chains. This is the principal defense against a distributed system that fails like a monolith.
3. **Events carry facts, not instructions.** An event states what happened in the producer's own domain. It does not direct a consumer to act, and it does not report a fact belonging to another domain `[C32]`. A producer that needs a specific action taken elsewhere issues a command against that sub-application's API and accepts the response.
4. **Canonical identity is never re-minted.** Every payload referencing an asset, system, installed item, or part uses the identifiers defined in §4. No sub-application invents a local surrogate and exposes it.
5. **Backward-compatible evolution by default; major versions for anything else.** Additive optional fields require no version change. Removals, renames, type changes, and semantic changes require a new major version served alongside the prior one.
6. **Every contract has an executable conformance suite,** and every obligation in a contract is externally observable. An obligation that cannot be observed from outside a black-box implementation is a program implementation standard, not a contract term, and is recorded separately (§11) `[D24]`.
7. **Classification travels with data, and derived values inherit it.** Every event envelope and every API response carries a classification label. Any derived value carries the union of its inputs' labels, enforced by the same provenance machinery that §11 requires. Producers segregate by classification; consumers additionally enforce (§7.3, §12) `[D13]`.
8. **Retrieved and user-supplied content is untrusted data, never instruction** (§9) `[D14]`.
9. **Every store has a remediation path.** Append-only is an integrity property, not an excuse for unrecoverable data (§13) `[D15]`.

---

## 3. Canonical identifiers and vocabulary

### 3.1 Sub-application slugs

One canonical slug per sub-application, used without variation in topic names, event `producer` fields, `target_sub_app` values, API base paths, conformance directories, and manifest directories `[C27, C28]`.

| Sub-application (canonical name) | Slug | Display abbreviation |
|---|---|---|
| Asset & Configuration Registry | `registry` | Registry |
| Condition & Telemetry | `telemetry` | Telemetry |
| Predictive Maintenance | `pdm` | PdM |
| Fleet Status & Readiness | `fleet-status` | Fleet Status |
| Maintenance Execution & Scheduling | `maintenance` | Scheduling |
| Supply Chain & Inventory | `supply` | Supply |
| Post-Mission Analysis | `pma` | PMA |
| Failure Intelligence | `failure-intel` | Failure Intelligence |
| System Test & Design Advisory | `design-advisory` | Design Advisory |

Platform services use `gateway`, `auth`, `reference-data`, `knowledge-retrieval`, `audit`, `notification`, `sync`, `tool-server`.

### 3.2 Domain vocabulary

One term per concept. Losing variants are not to be used in any document or identifier `[C29]`.

| Concept | Canonical term | Not |
|---|---|---|
| A physical item occupying a position | **installed item** | equipment, component, part instance |
| A named persistent installation location | **position** | slot, location |
| An ESWBS-aligned grouping within an asset | **system** | subsystem, group |
| A part type in the catalog | **part** | component, item |
| An underway period, patrol, or sortie | **mission** | mission event, mission record |
| A deployed discipline service | **sub-application** | sub-app, service, microservice |
| A Domino inference deployment | **Domino Endpoint** (always qualified) | endpoint |
| An HTTP route on a sub-application | **operation** | endpoint |

### 3.3 Identity references

```
AssetRef {
  asset_id           # stable internal UUID; the join key
  hull_or_tail       # "DDG 113", "SSN 796", "MQ-25 004" — human reference only.
                     # SPACE, never a hyphen: SECNAVINST 5030.8D Enclosure 6 states
                     # "Hyphens will not be used in the hull number of any ship or
                     # craft." Trailing N denotes nuclear propulsion; a leading "T-"
                     # denotes Military Sealift Command.
  uic                # Unit Identification Code. 5 characters; a 6-character form
                     # carries a leading Service identifier, and Navy ships use
                     # R (Pacific) or V (Atlantic) in DoDAAC contexts
  class_id           # class designation. The Navy expresses ship class as the LEAD
                     # HULL NUMBER (68 for NIMITZ, 51 for ARLEIGH BURKE), so the
                     # internal identifier carries both that and the flight or block
  domain             # surface | subsurface | unmanned
}

SystemRef {                                                          # [C31]
  system_id          # stable internal UUID; the join key
  eswbs              # ESWBS code — human reference and external federation only
  eic?               # Equipment Identification Code, where the system level has one.
                     # Federation and human reference only — never a join key [see rule below]
}

PositionRef {
  position_id        # stable internal UUID; the join key
  position_code      # "233-04-A" — human reference only
  system_id
}

InstalledItemRef {                                                   # [C10, D9]
  installed_item_id  # stable internal UUID; the join key. Identifies the PHYSICAL ITEM
  iuid               # Item Unique Identification per DoDI 8320.04, where assigned.
                     # DoDI 4151.22 §1.2.d and §1.2.l require serialized item management
                     # and IUID "to optimize RCM and CBM+ data analytics", so this is the
                     # externally mandated instance identity — not the EIC
  eic?               # Equipment Identification Code of the class this item instantiates.
                     # Federation and human reference only — never a join key
  position_id        # where it is installed
  niin               # what it is
  serial_or_lot      # where tracked
  installed_at
}

PartRef {
  niin               # National Item Identification Number; the join key
  nsn                # full National Stock Number where known
  apl                # Allowance Parts List reference
  equipment_family   # canonical grouping for model binding and calibration [D35]
}
```

Four rules govern their use:

- **`asset_id`, `system_id`, `position_id`, `installed_item_id`, and `niin` are the join keys.** `hull_or_tail`, `eswbs`, `position_code`, and `nsn` are carried for human reference and for federation with external systems, and are never used as join keys internally, because external systems reissue and reformat them.
- **EIC is never a join key, and this is documented rather than preferential.** NAVSEAINST 4790.8 Appendix A defines the Equipment Identification Code as *"a 7-character code… The first position identifies the system; the first and second characters together identify the subsystem; the third and fourth together identify the equipment category,"* and adds *"Where the EIC is known to more than four digits, it should be recorded at that level."* EIC is therefore a **class code of variable specificity**, not an instance identifier. It is carried on `SystemRef` and `InstalledItemRef` for federation and human reference only.
- **A payload identifying a physical item identifies it as `installed_item_id`.** A payload identifying a location identifies it as `position_id`. The distinction is load-bearing: remaining useful life, usage accumulation, and failure history attach to the installed item, and a payload that conflates the two produces the inherited-degradation failure document 04 §2 exists to prevent `[C10]`.
- A NIIN alone is a part type, not an installed item.
- Every payload referencing configuration carries `baseline_id` and `baseline_epoch` (§5.4). A prediction computed against a superseded baseline is invalid, and consumers must be able to detect that without inference.

**`equipment_family`** partitions model bindings, calibration records, and reference classes. It is defined and served by Reference Data, is versioned, and is a required attribute of every part `[D35]`.

**Provisional installed-item identity.** An edge deployment may mint an `installed_item_id` locally as a client-generated UUID with `provisional: true`. The Registry confirms or supersedes it on reconciliation. Without this, a ship that replaces an item at sea cannot attribute usage or maintenance to the correct physical item `[D9, D8]`.

---

## 4. REST API conventions

Applicable to all sub-applications and platform services.

| Concern | Convention |
|---|---|
| Style | Resource-oriented REST over HTTPS. JSON bodies |
| Specification | OpenAPI 3.1, generated from code, published to the contracts package, validated in CI against the committed specification |
| Base path | `/api/v{major}/{sub-application-slug}/…` — slug from §3.1, major version in the path. This prevents collision at the single gateway ingress `[C25]` |
| Naming | Plural resource collections; `kebab-case` paths; `snake_case` JSON fields. **Carve-out:** singleton and query-projection resources may be singular where no collection semantics exist, and must be enumerated in the sub-application's specification `[C23]` |
| Sub-resource actions | `POST /{collection}/{id}/{action}` is sanctioned for state transitions and computations that are not naturally resource creation. The action is a verb in `kebab-case`. Every such operation declares `x-side-effects` (§4.1) `[C24]` |
| Identity | Canonical identifiers from §3.3 only. Version selectors are query parameters, never path identifiers `[C24]` |
| Pagination | Cursor-based: `?limit=&cursor=`; responses return `next_cursor`; no total count on unbounded collections |
| **Snapshot and change-feed reads** | **Every sub-application exposes `GET /{collection}?changed_since=&cursor=` over each aggregate a consumer maintains a read model of.** This is the rebuild path; the event bus is not `[D5, D25, D30]` |
| Filtering | Explicit named parameters. No general-purpose query language on the public surface |
| Errors | RFC 9457 problem details. `type` is a stable URI; `detail` is never used for control flow |
| Idempotency | All unsafe methods accept `Idempotency-Key`. Required for any operation reachable from an agent proposal, a bulk write, or an edge sync |
| Concurrency | `ETag` on updatable resources; `If-Match` required on `PUT`, `PATCH`, and on proposal adjudication (§8.2). Lost updates return 412 |
| Bulk writes | Where a batch process writes results, the receiving sub-application exposes a bulk, idempotent, fenced operation. Direct database access by any other workload is prohibited `[D10, C7]` |
| Correlation | `X-Correlation-Id` accepted, generated when absent, propagated to every log line, event, and downstream call |
| Authentication | OIDC bearer tokens. Service-to-service calls carry the calling workload's identity |
| Agent authority | Per §8.3. Interactive agent calls carry the user's delegated token; autonomous runs carry an accountable workload identity |
| Authorization | Enforced by the receiving sub-application against ABAC attributes including classification, caveats, and compartments. Never delegated to the gateway alone |
| Classification | `X-Classification` on responses; per-field redaction where a response mixes levels |
| Rate limiting | Per-caller-identity token bucket at the gateway; per-sub-application limits declared in its chart |
| Health | `/healthz`, `/readyz` including dependency and read-model-staleness checks, `/metrics` |
| Time | RFC 3339 with explicit offset, UTC on the wire |

### 4.1 Operation annotations

Every operation declares two annotations, validated in CI.

| Annotation | Values | Purpose |
|---|---|---|
| `x-substitution` | `required` \| `internal` | Whether a substituting implementation must provide it (§10) |
| `x-side-effects` | `none` \| `proposal-only` \| `state-changing` | The basis for agent eligibility (§8.1) |

`x-side-effects: none` asserts the operation does not alter domain state. It is permitted on `GET` and on computational `POST` operations such as scenario analysis and planning. **Agent eligibility is determined by declared side-effect class, not by HTTP method** — a method check wrongly excludes the compute-only `POST` operations that three of the seven agents require `[C1, D11]`.

### Deprecation policy

A superseded major version is served for a minimum of two release cycles after its successor reaches general availability, with `Deprecation` and `Sunset` headers throughout. Removal requires per-version call metrics showing no caller for one full cycle.

---

## 5. Event backbone

### 5.1 Transport and topology

Kafka API via Redpanda. One topic per aggregate type per producing sub-application; topics are never shared between producers.

**Topic naming:** `fathom.<slug>.<aggregate>.v<major>`, `snake_case` for the aggregate token. Examples: `fathom.registry.configuration_baseline.v1`, `fathom.pdm.prediction.v1`, `fathom.pma.anomaly_tag.v1` `[C26]`.

**Partition key:** `asset_id` for asset-scoped events, guaranteeing per-asset ordering **within a topic** — which is the only ordering guarantee the design relies on `[D4]`. Fleet-scoped, NIIN-scoped, and class-scoped events partition on their own scope identifier. No design may depend on cross-asset or cross-topic ordering except through the antecedent rule in §5.4.

**Compaction key ≠ partition key.** Where a topic is compacted, the compaction key is the *aggregate* key — `installed_item_id`, or `(niin, location)`, or `baseline_id` — not the partition key. Compacting on `asset_id` would collapse a hull's entire prediction history to a single record `[D5]`.

**Classification segregation.** Topics are segregated by classification level and compartment. A topic carries exactly one classification, declared in its registration; cross-level flow occurs only through an accredited guard. For the unclassified synthetic demonstration a single level is used and this is stated explicitly rather than implied to be multi-level capable `[D13]`. See §12.

**Retention.** Seven days for high-volume derived streams; thirty days for domain events; compacted indefinite retention for state-carrying topics. Retention is bounded deliberately, and **the event bus is not a rebuild source.** Read-model rebuild uses the `changed_since` reads of §4 `[D5]`.

### 5.2 Delivery semantics

At-least-once delivery. Every consumer is idempotent on `event_id`. Exactly-once is assumed nowhere.

**Transactional outbox in every program-built producer.** A state change and the event announcing it are written in one database transaction; a relay publishes from the outbox. This eliminates the failure mode where a sub-application commits a change and then fails before publishing, and it is the substrate for disconnected edge operation (§11).

**Inbox: record and apply in one transaction.** The `event_id` record and the resulting state change commit together. Where that is impossible, the inbox row carries `processed_at` and **only rows with `processed_at` set suppress redelivery.** Recording receipt before processing is prohibited: a crash between the two permanently suppresses the event, and applied to `configuration.baseline_changed` it silently prevents prediction invalidation `[D2]`.

**Consumer staleness is observable.** Every consumer exposes read-model lag on `/readyz` and `/metrics`. Any computation with a correctness dependency on freshness declares a staleness bound and refuses to run outside it — the scheduling optimizer in particular `[D6]`.

### 5.3 Backfill and replay

Historical load and replay never traverse the live event bus, because replay would fire live side effects — notifications, work candidates, requisitions `[D30]`.

- **Backfill** uses the bulk write operations of §4, with `X-Backfill: true`, which suppresses downstream notification and command generation while still producing events marked `replay: true` in the envelope.
- **Replay** for read-model rebuild uses `changed_since` reads.
- Consumers must ignore or handle `replay: true` events idempotently and must not raise operator-visible alerts from them.

### 5.4 Envelope

```
EventEnvelope {
  event_id            # UUID; the consumer idempotency key
  event_type          # "fathom.<slug>.<aggregate>.<verb>" — snake_case throughout [C26]
  event_version       # major version of the payload schema
  occurred_at         # when the fact became true in the domain
  recorded_at         # when the producer persisted it
  producer            # slug from §3.1, plus version
  producer_node       # which DEPLOYMENT INSTANCE of that slug emitted this event:
                     # "enterprise" | "edge:<asset_id>". Required because a sub-application
                     # with an edge profile runs as two independent instances of the SAME
                     # slug, each minting its own monotonic_seq — without this field their
                     # sequences collide and the dedup key in §5.4 silently drops an event
  correlation_id
  causation_id        # event_id of the immediately preceding event, where applicable
  scope               # asset | system | installed_item | niin | class | mission | tycom | fleet   [C11]
  subject {           # exactly one scope identifier required, matching `scope`,
                     # EXCEPT scope=fleet, which requires none — fleet is the one
                     # singleton scope covering the entire fleet rather than one member of it
    asset_id?
    system_id?
    installed_item_id?
    niin?
    class_id?
    mission_id?      # required when scope=mission (e.g. mission.completed, mission_review.*)
    tycom_id?         # required when scope=tycom — an administrative Navy echelon
                     # (Type Commander), not an equipment class; added for Fleet
                     # Status's readiness rollup, which reports at asset/tycom/fleet
                     # echelons and has no other scope that fits the middle tier
  }
  baseline_epoch?     # monotonic per-asset configuration epoch, where applicable [D3, D4]
  classification
  replay              # boolean; true for backfill-generated events
}
```

`occurred_at` and `recorded_at` are distinct because they diverge materially here: a mission anomaly occurred at sea and was recorded when the ship reconnected. Consumers computing over time choose deliberately; audit uses `recorded_at`. **Feature computation must not use `occurred_at` for any value authored with hindsight** (§7.1, `[D22]`).

**Baseline epoch and the antecedent rule.** Each asset's configuration carries a monotonically increasing `baseline_epoch`. Any event whose correctness depends on configuration carries the epoch it was computed under. A consumer that receives an event with an epoch ahead of its own configuration read model **must block that event until the antecedent configuration event is applied**, resolved via `causation_id` or by reading `changed_since` from the Registry. This supplies the cross-topic causal ordering that per-asset partitioning does not `[D3, D4]`.

**Clock discipline. No wall clock ever arbitrates a merge.**

This is stronger than a caution, and the reason is a mandated STIG behavior rather than a hypothetical. The Ubuntu 22.04 STIG rule **V-260520** requires `makestep 1 -1` — unlimited backward clock steps whenever the offset exceeds one second — and that step fires *precisely* when a disconnected node reconnects and begins draining its outbox. Two writes from one process can therefore carry inverted wall-clock timestamps. Compliance guarantees a non-monotonic clock at exactly the moment ordering matters most.

Every event therefore carries:

```
clock {
  monotonic_seq      # per-producer monotonically increasing sequence. THE ordering key
  hlc                # hybrid logical clock: (physical, logical, node_id)
  source_time        # producing node's wall clock at the domain event
  ingest_time        # receiving node's wall clock at acceptance
  sync_quality {     # the attestation that makes skew auditable rather than invisible
    time_source          # gnss | usno_authenticated | upstream_ntp | holdover | unsynced
    offset_ms            # last measured offset
    dispersion_ms        # accumulated uncertainty — the published epsilon
    seconds_since_sync
    step_occurred        # true if a backward step landed since the last record
  }
}
```

Four rules follow:

- **Ordering and deduplication use `(producer, producer_node, monotonic_seq)` or the HLC.** Never `source_time`. Consumers apply idempotently on that key or on a content hash. `producer_node` is required precisely because an edge-profiled sub-application is two deployment instances of one slug, each with its own sequence.
- **Durations, timeouts, retry backoff, and lease expiry use a monotonic clock**, never the wall clock. A wall-clock backoff loop storms or hangs the instant a step lands — again, at reconnection.
- **`dispersion_ms` is a published epsilon that grows while disconnected, and the application branches on it.** Small epsilon permits wall-clock-assisted presentation; epsilon exceeding the inter-write interval forces causal-only ordering and forbids any timestamp arbitration. A time service that declares itself untrusted is far safer than one confidently serving wrong time.
- **`sync_quality` is retained permanently.** It converts "our timestamps drifted" from an audit finding into a bounded, documented condition, and it is the only way to re-derive true ordering after the fact. Without it that information is gone. Skew is indistinguishable from tampering to an assessor, and non-repudiation claims collapse if the time is contestable.

**Time-service requirement.** DoD Zero Trust Overlays v1.1 select SC-45 and SC-45(1) as tailoring additions — neither is in the SP 800-53B Moderate or High baseline — and set audit time-stamp granularity at **1 millisecond**, comparison **at least daily**, and a **1 second** resync threshold. A hull disconnected for weeks cannot meet that from a shore path, so a local stratum-1 reference with holdover is a hardware requirement, not a configuration choice. The Kubernetes STIG contains no time-synchronization rules at all, so correctness is inherited entirely from the host OS STIG and a skewed node silently poisons every pod on it `[D29]`.

### 5.5 Schema governance

Payload schemas live in `packages/canonical-schemas`, publish as versioned Python and TypeScript libraries, and register in a schema registry enforcing compatibility on publish. AsyncAPI documents generate from the same source. A producer cannot publish an event whose payload fails registry validation.

---

## 6. Event catalog

Producer-owned. A consumer listed here has a declared dependency, binding under §10.

**Agents are never direct topic consumers.** Agents obtain state through tools (document 01 §8.3). Where a downstream capability is realized by an agent, the consumer named here is the platform component that bridges to it `[C19]`.

**`audit` is a universal consumer, listed explicitly on every row below rather than assumed.** Its declared dependency is on the §5.4 envelope — the complete `clock` block, the signature, and a well-formed `ClassificationLabel` with `inherited_from[]` on derived aggregates — never on any payload. Its consumer-driven conformance suites assert envelope properties only, so payload evolution never breaks it, and it is exempt from every producer's version-bump obligation (§2 principle 5) for exactly that reason. It is listed explicitly rather than left implicit because an implementation's own `catalog.py` ≡ `values.yaml` ≡ this document three-way equality check (document 09 §8.2) fails on a real, non-wildcard audit subscription otherwise `[amendment 03-5]`.

### Asset & Configuration Registry (`registry`)

| Event | Payload summary | Consumers |
|---|---|---|
| `asset.registered` | AssetRef, class, commissioning data | `fleet-status`, `pdm`, `telemetry`, `audit` |
| `asset.status_changed` | operational status, OFRP phase, deployment state | `fleet-status`, `maintenance`, `pdm`, `audit` |
| `configuration.baseline_changed` | `baseline_id`, `baseline_epoch`, changed installed-item set, effective date | `pdm`, `pma`, `knowledge-retrieval`, `failure-intel`, `fleet-status`, `maintenance`, `supply`, `telemetry`, `audit` |
| `installed_item.installed` | InstalledItemRef, position, install date, source work order, usage-at-install | `pdm`, `telemetry`, `supply`, `audit` |
| `installed_item.removed` | InstalledItemRef, removal date, disposition, failure indicator | `pdm`, `failure-intel`, `supply`, `design-advisory`, `telemetry`, `audit` |
| `installed_item.identity_resolved` | `provisional_id`, `canonical_id`, `resolution` (`confirmed`\|`superseded`), evidence, `baseline_epoch` | `pdm`, `telemetry`, `supply`, `failure-intel`, `design-advisory`, `audit` |
| `allowance.updated` | COSAL/APL/AEL revision for an asset | `supply`, `maintenance`, `audit` |

`configuration.baseline_changed` is the most consequential event in the system. It invalidates every prediction attached to affected installed items, carries the new epoch, and is a correctness signal rather than an informational one.

`installed_item.identity_resolved` closes **OQ-5**, raised by Telemetry's build-framework agent: document 11 §8.4 already specifies this event (it resolves a provisional edge-minted `InstalledItem` identity to its permanent one, or supersedes it, and the library's `IdentityAliasResolver` is built on it) and names its consumer set, but the row was missing here. Same topic as `installed_item.installed`/`.removed` (`fathom.registry.installed_item.v1`), so a consumer of either of those already receives it and need only extend its handler.

### Condition & Telemetry (`telemetry`)

| Event | Payload summary | Consumers |
|---|---|---|
| `telemetry.batch_ingested` | asset, time range, channel set, sample counts, quality flags | `pdm`, `pma`, `failure-intel`, `audit` |
| `health_indicator.computed` | installed item, indicator set, values, definition version, definition-time | `pdm`, `fleet-status`, `audit` |
| `usage_counter.updated` | installed item, counter type, cumulative value, `counter_epoch`, as-of time | `pdm`, `maintenance`, `audit` |
| `usage_counter.reset` | installed item, counter type, reason, meter replacement reference | `pdm`, `maintenance`, `audit` |
| `mission.completed` | mission_id, asset, type, period, data completeness | `pma`, `failure-intel`, `audit` |

`pma`'s consumption of `mission.completed` includes the bridge for the PMA Pre-Screener agent's event trigger. §8's principle — *"agents are never direct topic consumers... the consumer named here is the platform component that bridges to it"* — is satisfied by a non-agent run-initiator component shipped from `agents/pma-prescreener/` itself (specified in `41-pma-prescreener.md` §2.2): it holds no prompt, calls no LLM, and makes no tool call, so it is not the agent in the sense §8 forbids, even though its process boundary sits under `agents/` rather than under `platform/`. This is recorded here, closing `41-pma-prescreener.md`'s **PS-OQ-1**, rather than adding a tenth platform-service row to 01 §5's inventory for a component with no domain responsibility of its own.
| `anomaly.detected` | installed item, window, detector version, score, channels implicated, origin (`enterprise` \| `edge`) | `pma`, `fleet-status`, `audit` |
| `channel_mapping.version_published` | channel/binding/mapping id, new version, `channel_registry_version`, effective date | `pdm`, `pma`, `audit` |

`channel_mapping.version_published` closes **OQ-2**, raised by the same agent: document 04 §3 requires a channel-mapping change to be "a versioned event," but §6's catalog had none, forcing Telemetry to fall back to `changed_since` reads plus a bumped `channel_registry_version` on `health_indicator.computed`. That fallback remains correct and is not superseded — it is how a mapping change reaches a consumer that doesn't subscribe to this new event — but the event itself was the missing, cheaper path for `pdm` and `pma`, which already react to registry-version bumps.

Batch-level rather than sample-level, deliberately. Per-sample events would constitute an event storm carrying no additional information.

### Predictive Maintenance (`pdm`)

| Event | Payload summary | Consumers |
|---|---|---|
| `prediction.updated` | scoring run reference, affected scope, **references to the run artifact rather than inline result sets** `[D27]` | `fleet-status`, `maintenance`, `supply`, `design-advisory`, `failure-intel`, `audit` |
| `prediction.invalidated` | affected scope, cause, `baseline_epoch` | `fleet-status`, `maintenance`, `supply`, `design-advisory`, `audit` |
| `criticality_tier.assigned` | NIIN, equipment family, tier, contributing factors, transition annotation | `fleet-status`, `maintenance`, `audit` |
| `model_binding.activated` | which registry model version now serves which tier and family, approval reference | `audit`, `fleet-status` |

`model_binding.activated` replaces the former `model_version.promoted`: model promotion occurs in Domino's registry, which is not PdM's domain, whereas the binding is `[C32]`. **Tier reassignment is an invalidation trigger** — affected predictions are invalidated and re-scored before publication, and the transition is annotated so a level shift is not read as fleet degradation `[D36]`.

### Fleet Status & Readiness (`fleet-status`)

| Event | Payload summary | Consumers |
|---|---|---|
| `readiness.recomputed` | scope, score components, contributing degradations, classification union | `notification`, `audit` |
| `casrep_risk.raised` | installed item, predicted category, horizon, evidence references | `notification`, `maintenance`, `supply`, `audit` |
| `casrep_risk.cleared` | installed item, cause of clearance | `notification`, `maintenance`, `audit` |

### Maintenance Execution & Scheduling (`maintenance`)

| Event | Payload summary | Consumers |
|---|---|---|
| `work_candidate.created` | installed item, driver, estimated scope | `supply`, `fleet-status`, `audit` |
| `work_order.opened` | work order, installed item, planned window, work package | `supply`, `fleet-status`, `registry`, `audit` |
| `maintenance_action.recorded` | installed item, action taken, parts consumed, findings code, `failure_indicator`, **`triggering_driver`, `triggering_prediction_id`, `policy_version`** `[D1, D21]` | `pdm`, `failure-intel`, `registry`, `supply`, `pma`, `design-advisory`, `audit` |
| `deferral.recorded` | installed item, `deferral_reason_class`, revised window, risk accepted | `fleet-status`, `pdm`, `audit` |
| `work_package.proposed` | availability, candidate set, constraint satisfaction summary, reservation-set reference | `supply`, `fleet-status`, `audit` |
| `work_package.approved` | availability, committed work set — **published only after reservation confirmation** `[D6]` | `supply`, `fleet-status`, `registry`, `audit` |

`maintenance_action.recorded` is the label stream for every model in the system. The three added fields record the treatment-assignment mechanism, without which neither calibration nor causal analysis can condition on the intervention policy `[D1, D21]`.

`deferral_reason_class` distinguishes capacity, operational tempo, parts unavailability, and disagreement with the risk estimate. Only the last is evidence about prediction quality; treating all deferrals as such biases models toward under-prediction `[D34]`.

### Supply Chain & Inventory (`supply`)

| Event | Payload summary | Consumers |
|---|---|---|
| `part_availability.changed` | NIIN, location, on-hand, due-in, allowance position, **`lead_time`, `condition_code`, interchangeable group** `[D6, D24]` | `maintenance`, `fleet-status`, `design-advisory`, `audit` |
| `requisition.status_changed` | document number, NIIN, status, projected availability | `maintenance`, `fleet-status`, `audit` |
| `allowance_shortfall.detected` | asset, NIIN, allowance versus on-hand, driver | `maintenance`, `fleet-status`, `notification`, `audit` |
| `reservation_set.confirmed` | reservation set, NIIN quantities, expiry | `maintenance`, `audit` |
| `reservation_set.released` | reservation set, cause | `maintenance`, `audit` |

### Post-Mission Analysis (`pma`)

| Event | Payload summary | Consumers |
|---|---|---|
| `mission_review.opened` | mission_id, asset, candidate set, assigned reviewer, candidate origin | `notification`, `audit` |
| `anomaly_tag.confirmed` | installed item, window, taxonomy classification, reviewer, qualification, evidence | `failure-intel`, `pdm`, `audit` |
| `anomaly_tag.rejected` | candidate reference, rejection reason, reviewer | `failure-intel`, `audit` |
| `mission_review.completed` | mission_id, tag counts, review duration, reviewer, canary outcomes | `fleet-status`, `audit` |

`anomaly_tag.*` reaches agent evaluation through `audit`, which exports to Domino's Experiment Manager. Domino workloads do not consume Kafka topics `[C19]`.

### Failure Intelligence (`failure-intel`)

| Event | Payload summary | Consumers |
|---|---|---|
| `causal_finding.published` | failure mode, hypothesized cause, evidence strength, affected population, treatment-assignment handling | `pdm`, `design-advisory`, `fleet-status`, `maintenance`, `audit` |
| `failure_mode.attributed` | installed item or NIIN, failure mode, confidence | `design-advisory`, `pdm`, `audit` |
| `causal_feature_set.updated` | feature definitions and versions available to tier-3 models, definition-time | `pdm`, `audit` |

### System Test & Design Advisory (`design-advisory`)

| Event | Payload summary | Consumers |
|---|---|---|
| `redesign_candidate.created` | NIIN, driver evidence, affected population, preliminary priority | `fleet-status`, `notification`, `audit` |
| `redesign_case.published` | NIIN, dependency impact, cost estimate, recommendation | `fleet-status`, `audit` |
| `design_change.projected` | NIIN, projected reliability improvement, effective configuration | `pdm`, `audit` |

### Audit & Provenance (`audit`) `[amendment 03-4]`

Audit is a consumer of every row above (the standing note at the top of this section) and is also a producer in its own right, on its own topics. This block was missing from rev 2 — Audit's build-framework agent flagged that a conformant audit service publishes events no version of this catalog declared.

| Topic | Event | Payload summary | Consumers |
|---|---|---|---|
| `fathom.audit.remediation.v1` | `remediation.purge_executed` | `purge_id`, selectors, classification label, `certificate_ref`, **no content** | all nine domain sub-applications, `gateway`, `knowledge-retrieval`, `notification`, `sync` |
| | `remediation.purge_certified` | `purge_id`, per-store outcomes, pending nodes, `certificate_ref` | as above |
| | `remediation.rewrap_executed` | record selectors, old and new `key_class`, authority | as above |
| | `remediation.quarantine_ordered` / `.quarantine_lifted` | selectors, reason class | as above |
| `fathom.audit.integrity.v1` | `integrity.checkpoint_sealed` | node, seq range, merkle root, signature | `notification` |
| | `integrity.signature_verification_failed` | producer, node, seq, quarantine ref | `notification` |
| | `integrity.sequence_gap_unrecoverable` | producer, node, missing seq range | `notification` |
| `fathom.audit.attestation.v1` | `attestation.clock_step_recorded` | node, measured `skew_ms`, `sync_quality` | `notification` |
| `fathom.audit.evaluation_export.v1` | `evaluation_export.completed` | export id, interval, record counts, destination | `notification` |

Audit's `purge`/`rewrap`-kind proposals follow the generic convention below rather than a separate block: `fathom.audit.proposal.v1` carries `proposal.created`/`.adjudicated`/`.expired` for the proposals Audit itself owns, exactly as any other proposal-accepting sub-application's topic does.

### Proposals — a convention

Every sub-application accepting agent proposals publishes to `fathom.<slug>.proposal.v1` using the §8.2 schema, permitting the gateway to build a unified adjudication queue from a topic pattern without any sub-application knowing the queue exists.

| Event | Consumers |
|---|---|
| `proposal.created` | `gateway`, `notification` |
| `proposal.adjudicated` | `audit`, and the owning sub-application |
| `proposal.expired` | `gateway`, `audit`, `notification` |

---

## 7. Shared payload schemas

### 7.1 FailurePrediction

**This supersedes the illustrative shape in document 01 §7** `[C2]`.

```
FailurePrediction {
  asset_id, installed_item_id, position_id, niin, equipment_family
  baseline_id, baseline_epoch
  horizon_days
  p_failure?               # calibrated within its declared reference class.
                          # NULL when calibration_population < 50 (document 06 §3's
                          # gate) — below the gate the cell publishes population_hazard_rate
                          # only, with reference_class forced to class_estimate. A predicted
                          # probability that cannot be calibrated must not be emitted merely
                          # because the field exists; omission is the honest signal
  reference_class          # item | niin_fleet | equipment_family | class_estimate
  sharpness                # dispersion relative to the reference-class base rate
  calibration_population   # n backing the calibration cell. Gates p_failure at n >= 50
  rul {                    # OMITTED where reference_class is not item-conditional
    p10, p50, p90, unit    # days | steaming_hours | eoh | cycles | sorties | dives
  } | null
  population_hazard_rate   # emitted instead of `rul` for non-item reference classes
  confidence               # sharpness-and-fit confidence only
  fallback_level           # 0..4; cold-start depth, NOT encoded in `confidence`
  tier                     # 0..3, transparency only
  contributing_factors[] {           # renamed from `drivers` [D23]
    factor
    contribution
    attribution_method               # required
    stability                        # rank stability across runs or bootstrap
    observation_ref                  # the feature observation, with point-in-time provenance
  }
  model_version, scoring_run_id, computed_at
}
```

Four corrections are embedded, and each closes a defect that would otherwise be silent:

- **`reference_class` replaces cross-tier probability comparability.** A tier-0 population rate and a tier-3 item-conditional probability can each be perfectly calibrated and remain incomparable. Consumers do not compare `p_failure` across reference classes; the scheduling optimizer applies a per-class decision-theoretic conversion to expected consequence `[D7]`.
- **`p_failure` is gated on `calibration_population`, per document 06 §3.** Below n=50 in the calibration cell, no calibrated probability is published at all — `p_failure` is null, `reference_class` is forced to `class_estimate`, and `population_hazard_rate` is the only rate-like figure available. A consumer that treats a missing `p_failure` as zero, rather than as "uncalibrated," reintroduces the comparability defect this field exists to prevent.
- **`rul` is omitted where the reference class is not item-conditional.** A memoryless population fit cannot produce a per-item residual-life distribution, and rendering one indistinguishably from a tier-3 distribution misleads the operator `[D19]`.
- **`fallback_level` is separate from `confidence`.** One scalar cannot carry both sharpness and epistemic reference-class depth and remain orderable `[D7]`.
- **`contributing_factors` requires `attribution_method` and `stability`,** and `observation_ref` points at a feature observation rather than at itself. Factors below a stability threshold are suppressed from display, and agents must not render them in causal language — a causal statement must cite an adjudicated Failure Intelligence hypothesis `[D23]`.

Tier invariance survives as **shape** invariance: consumers must not branch on `tier`. They may, and must, branch on `reference_class`.

### 7.2 Proposal

```
Proposal {
  proposal_id                                                        # [C30]
  kind                   # anomaly_tag | work_candidate | requisition |
                         # interval_change | redesign_case | configuration_change |  [C39]
                         # purge | rewrap
                         # purge and rewrap may never be created or adjudicated by an
                         # agent principal or an accountable-autonomous identity — no
                         # exception, regardless of x-side-effects (document 08 §5.4
                         # places classification determinations with the OCA and SCG,
                         # never with engineering, and never with an agent)
  target_sub_app         # slug from §3.1
  subject { … }          # scope identifiers per §5.4
  baseline_id, baseline_epoch                                        # [D16]
  payload                # the domain object, validated by the owning sub-application
  evidence[] {           # required, non-empty
    kind                 # record | document_chunk | prediction | trace
    ref, excerpt?, relevance?
    source_trust         # program | vendor | external      [D14]
  }
  rationale, confidence
  agent_id, agent_version, llm_version, trace_ref
  authority_class        # required authority to adjudicate (§7.2.1)   [D16]
  blast_radius           # item | asset | class | fleet              [D16]
  requires_dual_control  # boolean; true for class or fleet scope, and for
                         # any kind with external legal effect
  valid_until            # expiry; absent means no expiry is permitted
  status                 # proposed | claimed | approved | rejected | superseded | expired
  claimed_by, claimed_until                                          # [D16]
  adjudicated_by, adjudicated_at, adjudication_note
  second_adjudicator, second_adjudicated_at                          # dual control
  classification
}
```

Four rules make this safe rather than merely descriptive:

- **`evidence` is required and non-empty,** rejected at the API boundary if absent. But a non-empty evidence list is not sufficient: evidence carries `source_trust`, and a proposal resting solely on non-program content is flagged to the adjudicator `[D14]`.
- **Re-validation at approval is mandatory.** The owning sub-application re-validates `payload` against current configuration at adjudication time and rejects if `baseline_epoch` is superseded or `valid_until` has passed. Validation at creation is insufficient `[D16]`.
- **Adjudication requires a claim.** `POST /proposals/{id}/claim` obtains a lease; adjudication requires `If-Match` on the claimed ETag. Without this the eventually-consistent queue permits two approvals and two work orders `[D16]`.
- **Authority is checked against blast radius.** An `interval_change` suppressing a preventive task across a class is not the same act as confirming an anomaly tag, and must not be adjudicable by the same authority. Dual control is mandatory at class and fleet scope and for any kind with external legal effect `[D16]`.

#### 7.2.1 Authority classes for adjudication

**This is distinct from the agent authority classes in §8.3.** §8.3 governs which credential an *agent* calls with (delegated versus accountable-autonomous); this section governs which *human organizational role* is permitted to adjudicate a proposal, given its `kind` and `blast_radius`. An agent's delegated token still carries a human's identity and roles, and it is that identity's roles that are checked here.

```
AuthorityClass = maintainer | planner | supply_officer | design_authority | fleet_authority |
                  security_officer
```

| Class | Organizational role (document 01 §4) | Sub-application context |
|---|---|---|
| `maintainer` | Ship's Force Maintainer | Confirms anomaly tags, item-scoped work candidates |
| `planner` | RMC / Availability Planner | Work packages, asset-scoped scheduling decisions |
| `supply_officer` | (Supply role, ship or RMC) | Requisitions, expedites |
| `design_authority` | PEO / Design Engineer | Redesign cases |
| `fleet_authority` | TYCOM Readiness Officer | Class- or fleet-scoped interval changes; dual control's second signature at that scope |
| `security_officer` | ISSM / ISSO | Crypto-shred purges and re-wraps `[03-1]` — deliberately distinct from the operational and engineering roles above: document 08 §5.4 places classification determinations with the OCA and the SCG, "not… engineering," and a purge is a classification-adjacent act, not an operational one |

**Minimum authority by blast radius, per proposal kind:**

| `kind` | `item`/`asset` | `class` | `fleet` |
|---|---|---|---|
| `anomaly_tag` | `maintainer` | — (not applicable at this scope) | — |
| `work_candidate` | `maintainer` or `planner` | `planner` | `fleet_authority` |
| `requisition` | `supply_officer` | `supply_officer` | `fleet_authority` |
| `interval_change` | `planner` | `fleet_authority` + dual control | `fleet_authority` + dual control |
| `redesign_case` | `design_authority` | `design_authority` | `design_authority` + dual control |
| `configuration_change` | `maintainer` (edge-submitted) then Registry confirmation | — | — |
| `purge` / `rewrap` | `security_officer` + dual control | `security_officer` + dual control + `fleet_authority` counter-signature | `security_officer` + dual control + `fleet_authority` counter-signature |

A proposal's `authority_class` field is set by the owning sub-application at creation, from this table, and re-validated at adjudication (§7.2's re-validation rule) in case the scope was corrected between proposal and adjudication. Phase 3 per-sub-application design may add finer-grained roles within a class (e.g. splitting `planner` by RMC), but may not remove the minimum this table establishes.

**Some cells accept more than one class** — `work_candidate` at item or asset scope accepts `maintainer` *or* `planner` — and a singular field cannot carry an alternative set. The **policy evaluation, not the field, is authoritative**: adjudication checks the adjudicator's held roles for membership in the cell's full allow-set, generated from this table, never a single-value equality check and never a rank comparison between classes (there is no implicit hierarchy — a `fleet_authority` does not automatically satisfy a `maintainer` requirement, since these are organizational roles, not levels of the same authority). `Proposal.authority_class` itself records one representative value from the cell — for display, audit, and queue filtering — and is re-validated against the full allow-set, not against that single recorded value, at adjudication time. **"Minimum" in the table above means minimum authority, not a hierarchy floor:** it identifies the least-privileged role or roles the cell accepts, not a rank threshold above which any higher-ranked class also qualifies.

**A `purge` or `rewrap` proposal may never be created or adjudicated by an agent principal or an `accountable-autonomous` identity, with no exception** `[03-1, 03-2]`. This is stricter than every other row in the table above: those permit an agent to *propose* (subject to §8.3's authority checks) even where a human must adjudicate. Purge and rewrap admit no agent role on either side of the transaction, regardless of `x-side-effects` classification, because the act is irreversible (§13) and classification-adjacent rather than operational.

### 7.3 ClassificationLabel

```
ClassificationLabel {
  level                  # U | CUI | S | TS
  cui_categories[]       # CUI Registry categories present, e.g. SP-CTI, SP-NNPI, SP-EXPT.
                         # Corresponds to line 3 of the DoDI 5200.48 designation indicator
  dissemination[]        # constrained to the ten authorized Limited Dissemination Controls:
                         # NOFORN | FED ONLY | FEDCON | NOCON | DL ONLY | RELIDO |
                         # REL TO | DISPLAY ONLY | AC | AWP.
                         # "FOUO" and "U//FOUO" are RETIRED markings (DoDI 5200.48 §3.4.b)
  distribution_statement # A..F or REL TO, per DoDI 5230.24 Table 1.
                         # Corresponds to line 4 of the designation indicator
  compartments[]
  derived_from           # classification authority reference
  inherited_from[]       # input label references, for derived values   [D13]
}
```

The category and dissemination lists are typed rather than free text because DoDI 5200.48 requires a five-line CUI designation indicator whose third and fourth lines are *"all types of CUI contained in the document"* and *"the distribution statement or the dissemination controls applicable"* — structured obligations, not annotations. Minimum marking is `CUI` in both banner and footer; the older `U//FOUO` form is retired.

Producers segregate by topic; consumers additionally enforce. **Every derived value carries the union of its inputs' labels,** recorded in `inherited_from` and enforced by the provenance obligation in §15. The vector store enforces at query time rather than post-filtering, because post-filtering leaks the existence of records.

**Aggregation is a classification event.** A rollup whose value moves when a compartmented item degrades discloses that item's existence. Fleet Status either excludes compartmented contributors from a rollup, or classifies the rollup at the union and computes a separate low-side view. This constrains the readiness scoring methodology and is not a presentation concern `[D13]`.

---

## 8. Agent authority and tool surfaces

Document 01 §8.0 establishes that sub-application APIs constitute the agent tool surface by construction, that the relationship is one-to-many, and that substitution-safety and tool-safety are the same property. This section specifies the mechanism and the authority model.

### 8.1 Two-level exposure: eligibility and selection

**Eligibility — a safety gate in the OpenAPI specification.** `x-agent-eligible` may be asserted only where `x-side-effects` is `none` or `proposal-only` (§4.1). Validated in CI, so no manifest author can select a state-changing operation. This is declared by side-effect class rather than by HTTP method, because compute-only `POST` operations are both safe and necessary `[C1, D11]`.

**Selection — a tuning decision in a manifest.** A manifest names a subset of eligible operations and supplies task-scoped descriptions, parameter defaults, and result shaping. This is the consuming agent's decision and requires no API change.

### 8.2 Manifests are versioned, owned artifacts

```
packages/agent-tooling/manifests/<slug>/<manifest-name>.v<major>.yaml
```

| Field | Purpose |
|---|---|
| `name`, `version` | Manifest identity, versioned independently of the API |
| `target` | Sub-application slug and the API major version written against |
| `owner` | Consuming agent, or `curated` for shared manifests |
| `purpose` | Task or persona served; reviewed for overlap |
| `operations[]` | Selected operation identifiers with task-scoped description, parameter defaults, optional result projection |

Generation emits MCP-style descriptors and **fails** — rather than warns — when a selected operation is absent from the pinned API version, is not `x-agent-eligible`, or lacks a description.

Predictive Maintenance backs at least three manifests over one unchanged API: `pdm-fleet-triage` (broad, ranked, read-heavy), `pdm-equipment-deepdive` (narrow, provenance-rich), and `pdm-whatif` (interactive scenario, using the `x-side-effects: none` computational operation).

### 8.3 Agent authority classes

The requirement that agents act as the requesting user is unsatisfiable for event-triggered and scheduled work, which has no requesting user. Two classes are therefore defined `[D12]`.

| Class | Applies to | Authority | Constraints |
|---|---|---|---|
| **Delegated** | Interactive agents invoked by a user | The user's delegated token | Reach bounded by the user's own authorization, evaluated by the receiving sub-application |
| **Accountable autonomous** | Event-triggered and scheduled agents — PMA Pre-Screener, Readiness Narrative, scheduled evaluation | A scoped short-lived workload identity with a **named accountable human owner** | Restricted to `x-side-effects: none` and `proposal-only`. Cannot read outside its declared scope. Every run recorded to Audit with the accountable owner |

Two further requirements:

- **Domino Endpoint calls are proxied.** A Domino Endpoint authenticates with a static token carrying no caller identity and no per-caller audit trail (document 02 §4.3). Every Endpoint call is therefore made through a Sustainment Plane service that attaches caller identity to the audit record `[D12]`.
- **Mid-run token expiry is a defined condition.** An agent run whose delegated token expires, or whose pod is restarted by platform maintenance, terminates and records a resumable checkpoint. It does not silently continue under a service identity, and it does not create a proposal after its authority has lapsed `[D12]`.

### 8.4 Versioning, conformance, and proliferation

Manifest version and API major version are independent. An agent artifact pins **both**, plus its prompt and model version, promoted together as one registered unit. Manifest changes are subject to the same regression gates as prompt changes.

Each manifest ships a conformance test asserting its declared behavior matches actual API behavior — every selected operation exists and is eligible, descriptions accurately characterize returns, parameter defaults are valid, result projections match response schemas. Manifest tests run inside the sub-application conformance suite (§10), so a conformant substitution is automatically a conformant tool surface.

Proliferation controls: every manifest declares a `purpose` reviewed for overlap; manifests are owned, and an unowned manifest is deleted rather than inherited; shared manifests are marked `curated` and maintained centrally.

### 8.5 Invocation properties

- Tool invocations, with full request and response, are recorded to Audit & Provenance and correlated to the Domino trace by `trace_ref`.
- Tool servers run on the Sustainment Plane as the `tool-server` platform service, since Domino provides no MCP registry, discovery, or governance (document 02 §4.2) `[C17]`.
- Because manifests generate from published contracts, third parties may develop tool surfaces against these sub-applications without program involvement.

---

## 9. Untrusted content

The retrieval corpus is IETMs, maintenance narratives, casualty reports, test reports, and engineering change proposals — free text authored by thousands of people, including parties outside the program. It is untrusted input `[D14]`.

1. **Retrieved content is data, never instruction.** Tool results and retrieved passages are structurally separated from instructions in every agent prompt. No retrieved text can alter an agent's tool selection or authority.
2. **Domain policy is enforced in the sub-application, not by agent behavior.** A requisition proposal's NIIN must be APL-authorized for that position; an `interval_change` must fall within a bounded delta and route to PMS authority; a `work_candidate` must reference an installed item present in the current baseline. These are validation rules on the receiving operation, and they hold regardless of what an agent proposes or why.
3. **Evidence provenance is surfaced.** `source_trust` on each evidence item, and a proposal resting solely on non-program content is flagged to the adjudicator.
4. **Injection cases are in the evaluation gate.** Golden question sets include adversarial corpus content, and agent promotion is blocked on failure.
5. **Corpus ingest records authorship and provenance,** and content from outside the program is marked at ingest rather than inferred later.

The propose-and-adjudicate boundary is a genuine control, but on its own it reduces the security posture to the attentiveness of a time-pressured reviewer. Items 2 and 4 are what make it more than that.

---

## 10. Substitution protocol

### What a substituting implementation must provide

1. **The `x-substitution: required` subset** of the sub-application's OpenAPI contract, including the `changed_since` snapshot reads of §4.
2. **Every event the sub-application publishes**, with the §5.4 envelope, catalog payload schemas, declared partition key, and at-least-once semantics.
3. **Canonical identity acceptance** per §3.3. Identity translation is the substitute's responsibility, not its consumers'.
4. **Classification labelling** on every response and event.
5. **A historical backfill capability** — the substitute must be able to serve history through `changed_since`, or the program must retain the incumbent's event archive in object storage indefinitely. Without one of these, write cutover leaves every consumer unable to rebuild `[D25]`.
6. **A conformance run** (below).

### Contract obligations versus program implementation standards

The obligations in §15 divide in two, and conflating them makes the protocol unusable `[D24]`.

- **Contract terms** are externally observable and conformance-testable: events accompany state changes; identity is canonical; classification is labelled; correlation IDs propagate on responses; snapshot reads work; idempotency and concurrency behave as specified.
- **Program implementation standards** are internal properties unobservable from outside a black box: the transactional outbox, the consumer inbox, per-log-line correlation IDs, one database per service. **These bind program-built sub-applications and cannot bind a substitute.**

For a substitute, the outbox obligation is replaced by the observable property it exists to guarantee: **no state change without a corresponding event**, verified by a fault-injection driver that interrupts the substitute mid-operation and asserts convergence. A partner platform emitting from an ontology or a change-feed can satisfy that; it will not implement our outbox, and no test could tell whether it had.

### Conformance suites

`packages/contracts/conformance/<slug>/` contains:

- **Contract tests** — every `x-substitution: required` operation against the specification, including errors, pagination, idempotency, and concurrency.
- **Event tests** — a driver asserting specified domain actions produce specified events with correct envelopes and keys, and correct ordering *within a partition*.
- **Fault-injection tests** — interruption mid-operation, asserting no state change without its event.
- **Consumer-driven tests** — contributed by each declared consumer in §6, asserting the guarantees that consumer depends upon. These catch the substitution that conforms and still breaks a neighbor.
- **Manifest tests** — per §8.4.
- **A reference dataset** — synthetic Navy data sufficient for deterministic runs.

### Migration sequence

1. **Shadow** — the substitute receives the same inputs, with **externally-effective commands intercepted and suppressed**: requisition creation and reservation confirmation have real-world effect and must not be double-issued `[D25]`.
2. **Dual publish** — both implementations publish to the same topic under distinct producer identities, with a declared cutover fence, so no change is lost or duplicated at the switchover instant.
3. **Read cutover** — the gateway routes reads to the substitute only once consumer read models are being fed by the substitute's events, so the interface and the optimizer cannot disagree about the same NIIN.
4. **Write cutover** — the substitute becomes sole writer and producer.
5. **Decommission** — the incumbent is removed. Its event archive is retained in object storage indefinitely, not merely for the topic retention period.

---

## 11. Edge reconciliation policy

Per-aggregate policies are contracts between enterprise and edge instances, declared here so behavior cannot diverge between ships.

**Default rule.** Any aggregate not listed is **enterprise-authoritative and not edge-writable.** Phase 3 enumerates exceptions per sub-application; it does not re-derive defaults `[C20]`.

| Aggregate | Policy | Rationale |
|---|---|---|
**No policy below compares wall-clock timestamps across nodes.** Where an earlier revision said "last-writer-wins," the winner is determined by `(producer, producer_node, monotonic_seq)` or hybrid logical clock per §5.4, never by `source_time`. A mandated STIG clock step fires at reconnection, so timestamp arbitration would invert exactly when the outbox drains `[D29]`.

| Telemetry samples and batches | Append-only; deduplicated on `(producer, producer_node, monotonic_seq)` | Immutable observations; duplication is a transport artifact |
| Health indicators | Recomputable; enterprise recomputation supersedes | Derived data |
| Anomaly candidates | **Edge-generatable**; enterprise adds further candidates on reconnect | Afloat review requires a local candidate source `[D18]` |
| Anomaly tags | Append-only; never overwritten or deleted; supersession recorded | Human judgments are evidence |
| Proposals | Append-only; adjudication server-authoritative and claim-gated | Two adjudications is a real conflict |
| **Maintenance action records** | **Edge-authoritative, append-only** | The ship records what it *did*; the server retains authority over what was *authorized*. Separating them is what permits label capture afloat `[D8]` |
| Work orders and authorizations | Server-authoritative; edge submits requests | Maintenance authority does not fork |
| Mission records | Edge-authoritative on creation; enterprise-authoritative thereafter | The ship knows the mission occurred |
| Predictions | Enterprise-authoritative; edge holds a cache with an explicit staleness horizon, presented as degraded | Edge inference is a degraded mode and must display as such |
| — | **Write authority is never bound to liveliness.** A disconnected hull retains authority over its own records | This is where the DDS ownership model is actively wrong for this design: DDS binds OWNERSHIP to LIVELINESS, so a dark ship would *lose* authority over the mission records it alone can produce. The opposite of what is required |
| Requisitions | Server-authoritative; edge queues submissions | External legal effect |
| Configuration baselines | Enterprise-authoritative; edge submits configuration-change proposals and may mint **provisional** installed-item identities | Two divergent views of what is installed is the most damaging available conflict |
| Usage counters | Monotonic merge keyed on `(installed_item_id, counter_epoch)`; `usage_counter.reset` opens a new epoch; authoritative correction permitted with provenance and exempt from monotonicity | Keying on position rather than item would credit a new item with its predecessor's hours. Unqualified max-merge makes one sensor glitch permanent `[D9]` |

**Divergence budget.** Each edge deployment declares a maximum tolerable disconnection per aggregate, beyond which the operator interface degrades to explicitly read-only for that aggregate rather than accumulating unbounded unreconciled state. Phase 3 sets values, informed by the capacity model (document 05 §4.6).

---

## 12. Classification posture

For the unclassified synthetic demonstration the system operates at a single level, and this is stated rather than implied to be multi-level capable.

The production requirement is producer-side segregation: one classification per topic, cross-level flow only through an accredited guard, mandatory label inheritance on derived values (§7.3), and an aggregation policy for rollups. Consumer-side enforcement alone yields either system-high operation — in which labels are decorative — or a leak `[D13]`.

---

## 13. Data remediation

Append-only is an integrity property, not a licence for unrecoverable data. A mislabeled payload reaching a lower-side topic is a routine expected incident, and remediation must be possible across the audit store, nine read models, tag stores, compacted topics, inboxes and outboxes, the vector index, object-store evidence, and Domino traces `[D15]`.

1. **Envelope-level encryption with per-classification keys.** Crypto-shredding a key is the purge mechanism where physical deletion is impossible.
2. **A declared purge protocol** covering every store, including Domino-side traces and gateway-held read models, with an owner and a tested procedure — the externally observable form of this is §15 obligation 17's `POST /{slug}/remediations` operation.
3. **An explicit statement per store** of whether it is legally immutable or operationally append-only. The two require different remediation, and obligation 17's receipt is where an implementation states, per store, which applies and which mechanism was used.
4. **Tombstone semantics for compacted topics** that preserve the compaction invariant.
5. **Crypto-shred does not apply to the vector index, and this is a distinct remediation class.** An embedding used for nearest-neighbor search must remain in a plaintext-comparable form for the index to compute distances; encrypting it defeats the search it exists to serve, so there is no key to shred. Purge for this store is **physical row deletion plus a rebuild of the affected index partition** — point deletion alone is insufficient, because a graph-structured index (e.g. HNSW) can retain proximity information about a removed node in its connectivity until the graph is rebuilt. Partitioning the index by classification level, as Knowledge & Retrieval's build specification does, bounds a rebuild to the affected partition rather than the whole corpus.

This is an accreditation prerequisite, not a refinement.

---

## 14. Agent, model, and taxonomy authority

- **Taxonomy.** Reference Data is the single owner of the unified taxonomy — definition, versioning, publication. Post-Mission Analysis owns tag *assignments*; Failure Intelligence owns *attributions* and is the sole authority to *extend* the vocabulary; Scheduling owns findings *codings*. None owns the vocabulary itself `[C8, D31]`.

  **Single ownership is an external obligation, not a preference.** DoDI 8320.02 requires authoritative data sources to be registered and *"structural metadata, including vocabularies, taxonomies, and ontologies"* to be published. A vocabulary with three owners cannot be registered as an authoritative source.

  **The vocabulary is anchored on published standards** (document 08 §2): MIL-STD-3034A §3 supplies the semantics, ISO 14224 levels 6–9 and Annex B supply the structure and codes, and SAE GEIA-STD-0007C is the export contract. DoDI 4151.22 §1.2.j is the authority: data must conform to *"non-proprietary, open industry standards… Accept data in proprietary formats only by exception."*

  **Three projections, reconciled at read time.** Post-Mission Analysis presents a coarsened subset keyed on observable signature; Scheduling captures the 3-M code sets (CAUSE, WHEN DISCOVERED, ACTION TAKEN) because maintainers cannot be asked to learn a second vocabulary at the deckplate; Failure Intelligence works in the full vocabulary. A published, versioned, **many-to-many** crosswalk maps between them, and 3-M CAUSE is a *cause* code rather than a *mode* code, so one findings record maps to a **set** of candidate modes. **Carry that ambiguity as data — `candidate_modes[]` with confidence — rather than forcing a single code and silently corrupting the labels.** Normalising on write would destroy the disagreement signal that is the entire reason for having three capture points.

  **Every label carries `taxonomy_version`.** A training set assembled across an unversioned revision is silently corrupt and undetectably so. A taxonomy revision never rewrites historical tags; it records a crosswalk and marks superseded entries, retaining both.
- **Equipment family.** Owned by Reference Data, versioned, required on every part `[D35]`.
- **Model bindings.** PdM owns which registry version serves which tier and family; Domino owns the model artifacts and the registry.

---

## 15. Obligations

### Contract terms — externally observable, bind every implementation including substitutes

1. Publishes an OpenAPI 3.1 specification, generated from code, verified in CI, with `x-substitution` and `x-side-effects` on every operation.
2. Emits an event for every state change reachable through its contract; no state change without its event, verified by fault injection.
3. Accepts and returns canonical identifiers per §3.3.
4. Carries classification labels on every response and event, and label inheritance on derived values.
5. Exposes `changed_since` snapshot reads over every aggregate a declared consumer projects.
6. Honors `Idempotency-Key`, `ETag`/`If-Match`, and `X-Correlation-Id` propagation.
7. Enforces authorization locally against ABAC attributes, never relying solely on the gateway.
8. Declares `x-agent-eligible` only where `x-side-effects` is `none` or `proposal-only`.
9. Records provenance for every derived value it publishes — inputs, versions, and computation reference — sufficient to trace any operator-visible figure to its sources.
10. Ships and passes its conformance suite.

### Program implementation standards — bind program-built sub-applications only

11. Implements the transactional outbox, without exception, including sub-applications with no current edge profile.
12. Implements a consumer inbox that records receipt and applies state in one transaction (§5.2).
13. Owns exactly one logical database and reaches no other. Where a sub-application requires two storage engines, they are separate schemas of one owned cluster or are separately justified in Phase 3 `[D33]`.
14. Exposes read-model lag, and refuses freshness-dependent computation outside its declared staleness bound.
15. Emits `X-Correlation-Id` on every log line.
16. Declares its conflict policy per aggregate, or accepts the §11 default.

### Contract term added by amendment `[03-3]`

17. **Exposes a remediation operation** (`POST /{slug}/remediations`) accepting `quarantine`, `purge`, `rewrap`, and `release` actions over declared selectors, idempotent on the remediation id, returning a receipt signed by the implementation and stating, per store it owns, whether that store is legally immutable or operationally append-only and which mechanism was used. Numbered 17 rather than inserted into the contract-terms list above to avoid renumbering obligations already cited elsewhere by number (§13.2, §13.3, and multiple build documents cite 5, 9, and 14 specifically) — it is nonetheless a **contract term**, externally observable and binding on substitutes, not a program implementation standard. §13 items 1–3 specify what the receipt must be able to certify; this is the operation that does the certifying.
