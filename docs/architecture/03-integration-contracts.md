# Phase 2 — Integration Contracts

| | |
|---|---|
| **Status** | Draft — pending approval with document 04 |
| **Scope** | The contracts binding sub-applications to one another and to agents: API conventions, the event backbone and catalog, shared payload schemas, the substitution protocol, edge reconciliation policy, and the agent tool surface and manifest model |
| **Companion documents** | [01 — System Architecture](01-system-architecture.md) · [04 — Sub-Application Architectures](04-subapplication-architectures.md) |
| **Classification** | Internal |

---

## 1. Why this document precedes the sub-application designs

Phase 1 established that a sub-application is a discipline deployed independently, and that an entire discipline may be assumed by a partner system. That property is delivered by contracts, not by intentions. If the contracts are specified after the sub-applications, each sub-application will have encoded assumptions about its neighbors that the contracts must then accommodate, and the substitution property will be lost in the accommodation.

The contracts specified here are therefore binding on document 04 and on all Phase 3 detailed designs. A sub-application may choose any internal structure; it may not vary its contract surface.

---

## 2. Contract principles

1. **The contract is the API plus the published events plus the conformance suite.** Nothing else is a contract. Database schemas, internal message formats, and library types are private to a sub-application regardless of who can technically reach them.
2. **No synchronous cross-sub-application calls on a compute path.** A sub-application that needs another's data at compute time maintains a local read model, populated from events. Synchronous reads are permitted only for user-facing composition, and that composition is performed by the API gateway rather than by sub-applications calling one another in chains. This is the principal defense against a distributed system that fails like a monolith.
3. **Events carry facts, not instructions.** An event states what happened in the producer's domain. It does not direct a consumer to act. A producer that needs a specific action taken elsewhere issues a command against that sub-application's API and accepts the response.
4. **Canonical identity is never re-minted.** Every payload referencing an asset, equipment, or part uses the identifiers defined in the shared kernel. No sub-application invents a local surrogate and exposes it.
5. **Backward-compatible evolution by default; major versions for anything else.** Additive optional fields require no version change. Removals, renames, type changes, and semantic changes require a new major version served alongside the prior one.
6. **Every contract has an executable conformance suite.** A partner implementation is judged conformant by passing the suite, not by review. This is what makes substitution a procurement decision rather than an integration project (§8).
7. **Classification travels with data.** Every event envelope and every API response carries a classification label. Consumers enforce it; producers never assume the consumer will.

---

## 3. REST API conventions

Applicable to all sub-applications and to the platform services.

| Concern | Convention |
|---|---|
| Style | Resource-oriented REST over HTTPS. JSON request and response bodies |
| Specification | OpenAPI 3.1, generated from code, published to the contracts package, and validated in continuous integration against the committed specification |
| Base path | `/api/v{major}/` — major version in the path. Minor and patch changes are not reflected in the path |
| Naming | Plural resource collections, `kebab-case` paths, `snake_case` JSON fields |
| Identity | Canonical identifiers only (§4). Composite lookups accept query parameters rather than encoded composite keys |
| Pagination | Cursor-based: `?limit=&cursor=`; responses return `next_cursor` and never a total count on unbounded collections |
| Filtering | Explicit named parameters. No general-purpose query language on the public surface |
| Errors | RFC 9457 problem details. `type` is a stable URI; `detail` is human-readable and never used for control flow by clients |
| Idempotency | All unsafe methods accept `Idempotency-Key`. Required for any operation reachable from an agent proposal or an edge sync |
| Concurrency | `ETag` on resources supporting update; `If-Match` required on `PUT` and `PATCH`. Lost-update conditions return 412 |
| Correlation | `X-Correlation-Id` accepted and propagated; generated when absent. Emitted on every log line and every event |
| Authentication | OIDC bearer tokens. Service-to-service calls use client-credentials tokens with the calling workload's identity |
| Delegated authority | Agent-originated calls carry the requesting user's delegated token, never a service principal (document 01, §8.5) |
| Authorization | Enforced by the receiving sub-application against ABAC attributes including classification and need-to-know. Never delegated to the gateway alone |
| Classification | `X-Classification` on responses; per-field redaction where a response mixes levels |
| Rate limiting | Per-caller-identity token bucket at the gateway; per-sub-application limits declared in its chart |
| Health | `/healthz` liveness, `/readyz` readiness including dependency checks, `/metrics` Prometheus |
| Time | RFC 3339 with explicit offset, UTC on the wire. Zulu-only in payloads; local presentation is a client concern |

### Deprecation policy

A superseded major version is served for a minimum of two release cycles after its successor reaches general availability. `Deprecation` and `Sunset` headers are emitted for the whole of that window. Removal requires evidence that no caller has used the version for one full cycle, drawn from per-version call metrics.

---

## 4. Canonical identity in payloads

The shared kernel (document 01, §6) defines the identity hierarchy. Its representation on the wire is fixed here.

```
AssetRef {
  asset_id          # stable internal UUID, the join key everywhere
  hull_or_tail      # e.g. "DDG-113", "SSN-796", "MQ-25-004" — display and human reference
  uic               # Unit Identification Code
  class_id          # e.g. "DDG-51-FLTIIA"
  domain            # surface | subsurface | unmanned
}

EquipmentRef {
  equipment_id      # stable internal UUID
  eic               # Equipment Identification Code
  eswbs             # ESWBS code of the parent system
  position          # installation position, unique within the asset
}

PartRef {
  niin              # National Item Identification Number
  nsn               # full National Stock Number where known
  apl               # Allowance Parts List reference
}
```

Three rules govern their use:

- `asset_id`, `equipment_id`, and `niin` are the join keys. `hull_or_tail`, `eic`, and `nsn` are carried for human reference and for federation with external systems, and are never used as join keys internally because external systems reissue and reformat them.
- Any payload identifying a component identifies it as the triple `(asset_id, equipment_id, niin)` plus `position`. A NIIN alone is a part type, not an installed component, and predictions attach to installed components.
- Every payload referencing configuration carries the `baseline_id` under which it was computed. A prediction computed against a superseded configuration baseline is invalid, and consumers must be able to detect that without inference.

---

## 5. Event backbone

### 5.1 Transport and topology

Kafka API via Redpanda. One topic per aggregate type per producing sub-application. Topics are not shared between producers.

**Topic naming:** `fathom.<sub-application>.<aggregate>.v<major>`

Examples: `fathom.registry.configuration.v1`, `fathom.pdm.prediction.v1`, `fathom.pma.anomaly-tag.v1`.

**Partition key:** `asset_id` for all asset-scoped events, which guarantees per-asset ordering — the only ordering guarantee the design relies upon. Fleet-scoped events partition on the aggregate identifier. No design may depend on cross-asset ordering.

**Retention:** seven days for high-volume derived streams, thirty days for domain events, and indefinite compacted retention for state-carrying topics such as configuration baselines and criticality tier assignments. Retention is a contract, not an operational setting, because consumers rebuilding read models depend on it.

### 5.2 Delivery semantics

At-least-once delivery. Every consumer is idempotent, keyed on `event_id`. Exactly-once is not assumed anywhere in the design, and any consumer whose correctness requires it is regarded as incorrectly designed.

**Transactional outbox in every producer.** A state change and the event announcing it are written in one database transaction; a relay publishes from the outbox to the broker. This eliminates the failure mode where a sub-application commits a change and then fails before publishing, and it is simultaneously the mechanism enabling disconnected edge operation (§9). It is not optional in any sub-application.

**Inbox on every consumer.** Received `event_id` values are recorded before processing, providing idempotency and a replay boundary.

### 5.3 Envelope

Every event on every topic carries this envelope. The `payload` is the only part that varies by event type.

```
EventEnvelope {
  event_id            # UUID, the idempotency key for consumers
  event_type          # e.g. "fathom.registry.configuration.baseline_changed"
  event_version       # major version of the payload schema
  occurred_at         # when the fact became true in the domain
  recorded_at         # when the producer persisted it
  producer            # sub-application identifier and version
  correlation_id      # request or process that ultimately caused this
  causation_id        # event_id of the immediately preceding event, where applicable
  subject {           # what the event is about; enables coarse filtering without decoding payload
    asset_id
    equipment_id?
    niin?
    mission_id?
  }
  classification      # classification label of the payload
  payload { ... }
}
```

`occurred_at` and `recorded_at` are distinct because they diverge materially in this system. A mission anomaly occurred at sea; it was recorded when the ship reconnected. Any consumer computing over time must choose deliberately, and several sub-applications require `occurred_at` while audit requires `recorded_at`.

### 5.4 Schema governance

Payload schemas live in `packages/canonical-schemas`, are published as a versioned library in both Python and TypeScript, and are registered in a schema registry enforcing compatibility on publish. AsyncAPI documents are generated from the same source. A producer cannot publish an event whose payload fails registry validation.

---

## 6. Event catalog

Producer-owned. A consumer listed here has a declared dependency, which the substitution protocol (§8) treats as binding.

### Asset & Configuration Registry

| Event | Payload summary | Consumers |
|---|---|---|
| `asset.registered` | AssetRef, class, commissioning data | Fleet Status, PdM, Telemetry |
| `asset.status_changed` | operational status, OFRP phase, deployment state | Fleet Status, Scheduling, PdM |
| `configuration.baseline_changed` | new `baseline_id`, changed equipment set, effective date | **PdM (invalidates predictions)**, PMA, Knowledge & Retrieval, Failure Intelligence |
| `equipment.installed` | EquipmentRef, PartRef, position, install date, source work order | PdM, Telemetry, Supply |
| `equipment.removed` | EquipmentRef, removal date, disposition, failure indicator | PdM, Failure Intelligence, Supply |
| `allowance.updated` | COSAL/APL/AEL revision for an asset | Supply, Scheduling |

`configuration.baseline_changed` is the most consequential event in the system. It invalidates every prediction attached to affected equipment and requires re-scoring. Consumers must treat it as a correctness signal rather than an informational one.

### Condition & Telemetry

| Event | Payload summary | Consumers |
|---|---|---|
| `telemetry.batch_ingested` | asset, time range, channel set, sample counts, quality flags | PdM, PMA, Failure Intelligence |
| `health_indicator.computed` | equipment, indicator set, values, computation version | PdM, Fleet Status |
| `usage_counter.updated` | equipment, counter type, cumulative value, as-of time | PdM, Scheduling |
| `mission.completed` | mission_id, asset, type, period, data completeness | **PMA (opens review)**, Failure Intelligence |
| `anomaly.detected` | equipment, window, detector version, score, channels implicated | PMA (candidate seeding), Fleet Status |

Batch-level rather than sample-level events, deliberately. A destroyer's engineering plant and a UUV sortie together generate volumes that would make per-sample events an event storm carrying no additional information.

### Predictive Maintenance

| Event | Payload summary | Consumers |
|---|---|---|
| `prediction.updated` | `FailurePrediction` set for an asset, scoring run reference | Fleet Status, Scheduling, Supply, Design Advisory |
| `criticality_tier.assigned` | equipment, NIIN, tier, contributing factors | Fleet Status, Scheduling, governance reporting |
| `model_version.promoted` | model reference, tier, Domino registry version, approval reference | Audit, Fleet Status (provenance display) |
| `prediction.invalidated` | affected predictions and cause, typically a baseline change | Fleet Status, Scheduling |

### Fleet Status & Readiness

| Event | Payload summary | Consumers |
|---|---|---|
| `readiness.recomputed` | asset or fleet scope, score components, contributing degradations | Notification, Readiness Narrative agent |
| `casrep_risk.raised` | equipment, predicted category, horizon, evidence references | Notification, Scheduling, Supply |
| `casrep_risk.cleared` | equipment, cause of clearance | Notification, Scheduling |

### Maintenance Execution & Scheduling

| Event | Payload summary | Consumers |
|---|---|---|
| `work_candidate.created` | equipment, driver (prediction, PMS, or casualty), estimated scope | Supply (demand signal), Fleet Status |
| `work_order.opened` | work order, equipment, planned window, work package | Supply, Fleet Status, Registry |
| `maintenance_action.recorded` | equipment, action taken, parts consumed, findings, failure indicator | **PdM (training label)**, Failure Intelligence, Registry, Supply |
| `deferral.recorded` | equipment, deferral reason, revised window, risk accepted | Fleet Status, PdM |
| `work_package.proposed` | availability, candidate set, constraint satisfaction summary | Supply, Fleet Status |
| `work_package.approved` | availability, committed work set | Supply, Fleet Status, Registry |

`maintenance_action.recorded` is the second most consequential event in the system. It is the source of the failure labels on which every tier of model depends, and its `failure_indicator` field — whether the action was corrective following failure or preventive before it — is the single field that determines label quality. Phase 3 must treat its capture as a first-order design problem rather than a form field.

### Supply Chain & Inventory

| Event | Payload summary | Consumers |
|---|---|---|
| `part_availability.changed` | NIIN, location, on-hand, due-in, allowance position | Scheduling, Fleet Status |
| `requisition.status_changed` | document number, NIIN, status, projected availability | Scheduling, Fleet Status, Supply Expediter agent |
| `allowance_shortfall.detected` | asset, NIIN, allowance versus on-hand, driver | Scheduling, Fleet Status |

### Post-Mission Analysis

| Event | Payload summary | Consumers |
|---|---|---|
| `mission_review.opened` | mission_id, asset, candidate anomaly set, assigned reviewer | Notification |
| `anomaly_tag.confirmed` | equipment, window, taxonomy classification, reviewer, evidence | **Failure Intelligence**, PdM (label enrichment) |
| `anomaly_tag.rejected` | candidate reference, rejection reason, reviewer | **Failure Intelligence (negative label)**, agent evaluation |
| `mission_review.completed` | mission_id, tag counts, review duration, reviewer | Fleet Status, agent evaluation |

### Failure Intelligence

| Event | Payload summary | Consumers |
|---|---|---|
| `causal_finding.published` | failure mode, hypothesized cause, strength of evidence, affected population | **PdM**, Design Advisory, Fleet Status |
| `failure_mode.attributed` | equipment or NIIN, failure mode taxonomy, confidence | Design Advisory, PdM |
| `causal_feature_set.updated` | feature definitions and versions available to tier-3 models | **PdM** |

### System Test & Design Advisory

| Event | Payload summary | Consumers |
|---|---|---|
| `redesign_candidate.created` | NIIN, driver evidence, affected population, preliminary priority | Fleet Status, Notification |
| `redesign_case.published` | NIIN, dependency impact, cost estimate, recommendation | Fleet Status, PEO reporting |
| `design_change.projected` | NIIN, projected reliability improvement, effective configuration | PdM (forward-looking scenarios) |

### Proposals — convention, not a sub-application

Every sub-application that accepts agent proposals publishes to `fathom.<sub-application>.proposal.v1` using a common payload schema (§7.2). This permits the API gateway to construct a unified adjudication queue by consuming a topic pattern, without any sub-application knowing that a unified queue exists.

| Event | Consumers |
|---|---|
| `proposal.created` | Gateway (unified queue), Notification |
| `proposal.adjudicated` | Agent evaluation, Audit, and the originating agent's training corpus |

---

## 7. Shared payload schemas

Three schemas cross sub-application boundaries and are therefore defined once, in the contracts package, rather than per sub-application.

### 7.1 FailurePrediction

Reproduced from document 01 §7 as the canonical wire form. Tier-invariant by construction; consumers must not branch on `tier`.

```
FailurePrediction {
  asset_id, equipment_id, niin, position
  baseline_id            # configuration baseline this was computed against
  horizon_days
  p_failure              # calibrated probability within horizon
  rul {                  # distribution, never a point estimate
    p10, p50, p90        # in the equipment's native usage unit
    unit                 # days | steaming_hours | eoh | cycles | sorties
  }
  confidence             # comparable across tiers
  tier                   # 0..3, transparency only
  drivers[] {            # ranked; may be empty at tier 0
    factor, contribution, evidence_ref
  }
  model_version          # resolvable in the Domino registry
  scoring_run_id
  computed_at
}
```

Two fields exist specifically to prevent silent incorrectness. `baseline_id` allows a consumer to detect that a prediction predates a configuration change. `rul.unit` prevents the class of error in which a submarine's counter is compared against a UUV's.

### 7.2 Proposal

Owned by the executing sub-application; schema shared so the gateway can present one queue.

```
Proposal {
  proposal_id
  kind                   # anomaly_tag | work_candidate | requisition |
                         # interval_change | redesign_case
  target_sub_app
  subject { asset_id, equipment_id?, niin?, mission_id? }
  payload                # the domain object, validated by the owning sub-application
  evidence[] {           # required and non-empty
    kind                 # record | document_chunk | prediction | trace
    ref, excerpt?, relevance?
  }
  rationale
  confidence
  agent_id, agent_version, llm_version, trace_ref
  status                 # proposed | approved | rejected | superseded
  adjudicated_by, adjudicated_at, adjudication_note
  classification
}
```

`evidence` is required and must be non-empty. A proposal without citations is rejected at the API boundary rather than presented to a human, which enforces document 01 principle 8 mechanically rather than by convention. `trace_ref` resolves to the Domino agent trace, connecting each proposal to the reasoning that produced it.

### 7.3 ClassificationLabel

```
ClassificationLabel {
  level                  # U | CUI | S | TS
  caveats[]              # e.g. NOFORN, FOUO handling
  compartments[]
  derived_from           # classification authority reference
}
```

Carried on every envelope and response. Enforcement is the consumer's obligation. The vector store enforces at query time rather than by post-filtering retrieved results, because post-filtering leaks the existence of records.

---

## 8. Substitution protocol

The requirement is that a partner system — Palantir for supply and documents being the working example — can assume ownership of an entire discipline. This section defines what that requires, so that substitution is an integration exercise with a defined completion test rather than an open-ended project.

### What a substituting implementation must provide

1. **The required subset of the sub-application's OpenAPI contract.** Each sub-application's specification marks operations `required-for-substitution` or `internal`. Only the former binds a substitute. Document 04 identifies the required subset per sub-application.
2. **Every event the sub-application publishes**, with the envelope of §5.3, the payload schemas of the catalog, the declared partition key, and at-least-once semantics.
3. **Canonical identity acceptance.** The substitute must accept and return `asset_id`, `equipment_id`, and `niin`, whatever its internal identifiers. Identity translation is the substitute's responsibility, not its consumers'.
4. **Classification labelling** on every response and event.
5. **A conformance run.** See below.

### What a substituting implementation need not provide

Internal endpoints, administrative surfaces, the sub-application's data model, its read models, and any behavior not exercised by the conformance suite. A substitute is free to be a thin façade over a partner platform.

### Conformance suites

Each sub-application ships an executable conformance suite in `packages/contracts/conformance/<sub-application>/`, comprising:

- **Contract tests** — every `required-for-substitution` operation exercised against the OpenAPI specification, including error cases, pagination, idempotency, and concurrency behavior.
- **Event tests** — a driver asserting that specified domain actions produce the specified events, with correct envelopes, keys, and ordering.
- **Consumer-driven tests** — contributed by each declared consumer, asserting the specific guarantees that consumer depends upon. These are the tests that catch the substitution which technically conforms but breaks a neighbor.
- **Manifest tests** — for every tool manifest targeting the sub-application, assertions that its declared behavior matches actual API behavior (§10.4). This is what makes a conformant substitution automatically a conformant tool surface.
- **A reference dataset** — synthetic Navy data sufficient to run the suite deterministically.

A partner implementation is accepted when the suite passes. This is the concrete form of the plug-and-play requirement: not an architectural aspiration but a test run with a pass or fail outcome.

### Migration sequence

Substitution proceeds in four steps, and the design supports each without code change in consumers:

1. **Shadow** — the substitute runs alongside the incumbent, receiving the same inputs; outputs are compared and divergence reported.
2. **Read cutover** — the gateway routes read traffic to the substitute; the incumbent continues to publish events.
3. **Write cutover** — the substitute becomes the writer and event producer; the incumbent becomes read-only.
4. **Decommission** — the incumbent is removed; its topics are retained for their declared retention period to permit consumer read-model rebuilds.

---

## 9. Edge reconciliation policy

Document 01 §12 establishes that the afloat off-ramp rests on the transactional outbox and on per-aggregate conflict policy. Those policies are declared here because they are contracts between the enterprise and edge instances of the same sub-application, and a policy declared per-deployment rather than per-aggregate would produce divergent behavior between ships.

| Aggregate | Policy | Rationale |
|---|---|---|
| Telemetry samples and batches | Append-only; last-writer-wins on duplicate keys | Immutable observations. Duplicate submission is a transport artifact, not a conflict |
| Health indicators | Recomputable; enterprise recomputation supersedes edge | Derived data. The enterprise has more computation and more context |
| Anomaly tags | Append-only; never overwritten, never deleted | Human judgments are evidence. A tag superseded by later review is marked superseded, retaining both |
| Proposals | Append-only; adjudication is server-authoritative | Two adjudications of one proposal is a real conflict; the enterprise record governs |
| Mission records | Edge-authoritative on creation, enterprise-authoritative thereafter | The ship knows the mission occurred; the enterprise reconciles it against fleet context |
| Predictions | Enterprise-authoritative; edge holds a cache with an explicit staleness horizon | Edge inference is a degraded mode and must present as such to the operator |
| Work orders | Server-authoritative; edge submits requests, never commits | Maintenance authority does not fork |
| Requisitions | Server-authoritative; edge queues submissions | Supply documents have external legal effect |
| Configuration baselines | Enterprise-authoritative; edge changes queue as proposed changes | Two divergent views of what is installed is the most damaging conflict available, and must be impossible by construction |
| Usage counters | Monotonic merge — maximum value per counter wins | Counters only increase. Maximum is correct and commutative, so replay order is immaterial |

**Divergence budget.** Each edge deployment declares a maximum tolerable disconnection period per aggregate, beyond which the operator interface degrades to explicitly read-only for that aggregate rather than accumulating unbounded unreconciled state. Phase 3 sets the values per sub-application.

---

## 10. Agent tool surfaces

Document 01 §8.0 establishes that sub-application APIs constitute the agent tool surface by construction, that the relationship is one-to-many, and that substitution-safety and tool-safety are the same property. This section specifies the mechanism.

### 10.1 Two-level model: eligibility and selection

A single boolean per operation cannot express several differently-scoped manifests over one API. Exposure is therefore decomposed into two decisions taken at different levels by different owners.

**Eligibility — a safety gate, declared in the OpenAPI specification.** Each operation carries `x-agent-eligible: true|false`, defaulting to false. Eligibility may be asserted only for `GET` operations and for proposal-creation endpoints. This is validated in continuous integration against the specification, so no manifest author can select an operation that commits domain state. This enforces document 01 principle 7 at build time rather than by prompt instruction, and it is the sub-application owner's decision.

**Selection — a tuning decision, declared in a manifest.** A manifest names a subset of eligible operations and supplies task-scoped descriptions, parameter defaults, and result shaping. This is the consuming agent's decision, and it requires no API change.

The separation is what permits agent tuning to iterate at agent cadence while the API iterates at contract cadence.

### 10.2 Manifests are versioned, owned artifacts

```
packages/agent-tooling/manifests/<sub-application>/<manifest-name>.v<major>.yaml
```

Each manifest declares:

| Field | Purpose |
|---|---|
| `name`, `version` | Manifest identity. Versioned independently of the API |
| `target` | Sub-application identifier and the **API major version** the manifest is written against |
| `owner` | The consuming agent, or `curated` for shared manifests under central ownership |
| `purpose` | The task or persona the manifest serves. Reviewed for overlap against existing manifests |
| `operations[]` | Selected operation identifiers, each with a task-scoped description, parameter defaults, and optional result projection |

Generation emits MCP-style descriptors. Generation fails, rather than warns, when a selected operation is absent from the pinned API version, is not `x-agent-eligible`, or lacks a description.

Illustrating the fan-out, Predictive Maintenance backs at least three manifests over one unchanged API:

| Manifest | Purpose | Character |
|---|---|---|
| `pdm-fleet-triage` | Rank and filter risk across a fleet or unit | Broad, read-heavy, aggregate-oriented |
| `pdm-equipment-deepdive` | Investigate one installed item | Narrow, provenance-rich, driver and evidence oriented |
| `pdm-whatif` | Interactive scenario analysis | Tier-3 bound, latency-sensitive |

### 10.3 Independent versioning, and the pin

Manifest version and API major version are independent. An agent artifact pins **both**, alongside its prompt and model version, and all four are promoted together as one registered unit.

This pin is load-bearing rather than formal. An agent evaluated against one manifest and deployed against another is not an evaluated agent, and with several manifests per API the opportunity for that mismatch is correspondingly larger. Manifest changes are therefore subject to the same regression gates as prompt changes (document 01 §8.8).

### 10.4 Manifest conformance

Conformance extends from APIs to manifests. Each manifest ships a conformance test asserting that its **declared behavior matches the API's actual behavior**: that every selected operation exists and is eligible, that descriptions accurately characterize what the operation returns, that parameter defaults are valid, and that result projections match response schemas.

Because manifests generate from contracts rather than implementations, a conformant substitution preserves every manifest written against the discipline it assumes (document 01 §8.0). Manifest conformance runs as part of the sub-application conformance suite in §8, which means a partner implementation is certified as a tool surface by the same run that certifies it as a service.

### 10.5 Controlling proliferation

Uncontrolled manifest growth produces overlapping tools with ambiguous selection semantics, which measurably degrades agent performance and is a harder failure to diagnose than an outright error. Three controls apply:

- Every manifest declares a `purpose`, and new manifests are reviewed for overlap against existing manifests for the same sub-application.
- Manifests are owned. An unowned manifest is deleted rather than inherited.
- Manifests for shared use are marked `curated` and maintained centrally, so that common surfaces do not fork per agent.

### 10.6 Invocation properties

- **Delegated authority.** Every tool call carries the requesting user's delegated token. An agent's reach is bounded by its user's authorization, evaluated by the receiving sub-application, never by the manifest.
- **Audit.** Tool invocations, including full request and response, are recorded to Audit & Provenance and correlated to the Domino agent trace by `trace_ref`.
- **Hosting.** Tool servers run on the Sustainment Plane, since Domino provides no MCP registry, discovery, or governance (document 02 §4.2).
- **Third-party development.** Because manifests generate from published contracts, a partner, another program, or a customer's own agents may develop tool surfaces against these sub-applications without program involvement. This is a deliberate platform property, and the contracts and conformance suites are the artifacts that make it exercisable.

---

## 11. Non-negotiable obligations

Every sub-application, without exception:

1. Publishes its OpenAPI 3.1 specification to the contracts package, generated from code and verified in continuous integration.
2. Implements the transactional outbox. No exceptions, including sub-applications with no current edge deployment profile.
3. Implements a consumer inbox and is idempotent on `event_id`.
4. Owns exactly one database and reaches no other.
5. Enforces authorization locally against ABAC attributes, never relying solely on the gateway.
6. Carries classification labels on every response and event.
7. Emits `X-Correlation-Id` on every log line and propagates it to every event and downstream call.
8. Ships and passes its conformance suite.
9. Declares its conflict policy per aggregate (§9).
10. Records provenance for every derived value it publishes — inputs, versions, and computation reference — such that any figure presented to an operator can be traced to its sources.
11. Declares `x-agent-eligible` per operation, asserted only for `GET` operations and proposal-creation endpoints, and validated in continuous integration (§10.1).
