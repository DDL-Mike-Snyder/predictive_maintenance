# Build Framework 21 — Condition & Telemetry (`telemetry`)

| | |
|---|---|
| **Status** | Wave 2 build framework. Binding on the Phase 3 detailed design of `services/telemetry/` |
| **Deliverable** | `services/telemetry/` — one codebase, **two deployment profiles** (enterprise and edge), one TimescaleDB cluster per profile |
| **Source of truth** | [03 — Integration Contracts](../architecture/03-integration-contracts.md) §3.3, §4, §5.4, §6 (Telemetry rows), §11, §15 · [04 — Sub-Application Architectures](../architecture/04-subapplication-architectures.md) §3, §1, §12 · [05 — Review Findings](../architecture/05-architecture-review-findings.md) **D22**, **D18**, **D9**, **D29**, D5, D33, D28 · [06 — Demonstration Decisions](../architecture/06-demo-decisions-and-assumptions.md) §4, §7 · [07 — Navy Data Systems](../architecture/07-navy-data-systems.md) §10 (the ICAS gap) |
| **Siblings** | [09 — Monorepo & Conventions](09-monorepo-and-conventions.md) (layout, scaffold, Definition of Done template) · [10 — Shared Packages](10-shared-packages.md) (canonical schemas, conformance harness) · [11 — Outbox & Sync Library](11-outbox-sync-library.md) (**this service is its heaviest consumer**) · [13 — Synthetic Data Generator](13-synthetic-data-generator.md) (**the input this service must actually survive**) |
| **Precedence** | Document 03 prevails on any contract surface. Document 09 prevails on layout, stack, and conventions. Where document 04 §3's sketch conflicts with document 03's form, document 03 prevails and the divergence is recorded in §15 |
| **Classification** | Internal |

---

## 0. How to read this document, and what makes it load-bearing

This is the second-most consequential service in the system after the Registry, for three reasons that are structural rather than a matter of emphasis.

1. **Point-in-time correctness lives here, and document 04 §3's version of it is insufficient.** Finding **D22** establishes that `as_of` constrains *data* time only, while indicator definitions and channel mappings are explicitly recomputed over history — so a model trained at `as_of=2025-03-01` receives values computed by a definition authored in 2026 by someone who had already seen the 2025 failures. The Registry solved this with bitemporality; this service must solve it the same way. §5 and §6 are the whole of that solution, and if they are wrong every downstream model silently trains on leaked information and reports excellent offline metrics that do not survive the field. That failure is undetectable from the outside, which is why the obligation is enforced in the API rather than trusted to modelers.
2. **This is the sub-application with the realest edge profile.** Document 01 §12 names Condition & Telemetry in the afloat resident subset; document 06 §4 grows that profile further by making anomaly candidate generation edge-resident. Three domains with wildly different data profiles (document 06 §7) meet one canonical sample model here, and one of them — subsurface — delivers weeks of backlog in a single burst at reconnection. **An edge instance and the enterprise instance are two independent deployment instances of the same slug**, each minting its own monotonic sequence, which is exactly the condition `producer_node` was added to document 03 §5.4 to make representable.
3. **The clock-discipline module of document 11 §4 gets its heaviest use here.** Burst ingest at reconnection is precisely when the STIG-mandated `makestep 1 -1` backward step fires (**D29**), and this service is the one processing millions of samples across that discontinuity.

**Every rule below carries a "why this matters" note where the rule is load-bearing**, following document 11's convention and for the same reason: the shortest path from correct code to broken code is an implementer who does not know why a line exists and simplifies it.

Rules trace to a document section or a finding. Where this document decides something the architecture does not dictate, it is flagged **`DECISION`** with its justification. Where it extends or corrects a source document, it is flagged and recorded in §15.

### 0.1 Read these first, in this order

1. Document 03 §3.3 (identity, `InstalledItemRef`, the provisional-identity note), §5.4 **in full including the entire clock-discipline subsection**, §6's Telemetry rows, §11's policy table.
2. Document 04 §3 in full.
3. Document 11 §4 (clock discipline), §7 (conflict policy), §8 (provisional identity), §9 (the coordinator). This service consumes all four.
4. Document 13 §9 (the ten-stage noise and corruption pipeline). **That pipeline's output is this service's realistic input.** An ingest design validated only against clean data is not validated.
5. Document 07 §10 before writing a single sensor specific — see §2.5.

### 0.2 Traceability

| Finding / contract | Where it is discharged |
|---|---|
| **D22** — definition-time leakage survives point-in-time correctness | §3.4 (versioned definitions), §3.1 (bitemporal mappings), **§5** (the resolver), **§6** (recomputation), §10.2 (the leakage test) |
| **D18** — the pre-screener cannot run afloat; no candidate source at all | **§7**, §11.3 |
| **D9** — monotonic-max counters on the wrong key | §3.5, §8.3, §10.5 |
| **D29** — no time-synchronization design | §4.6, §5.4, §8.1, §10.6 |
| **D5** — read models cannot be rebuilt; compaction key wrong | §8.2 (per-topic compaction decisions), §9.4 (`changed_since`) |
| **D33** — Telemetry owns two databases | §2.3 (one cluster, two schemas) |
| **D28** — the edge outbox doubles telemetry storage | §2.3, §11.4 |
| 03 §11 — telemetry samples/batches append-only-deduplicated | §8.3, conflict policy `APPEND_ONLY_DEDUP` |
| 03 §11 — health indicators recomputable-supersede | §6.4, and the correction in §6.5 |
| 03 §11 — anomaly candidates edge-generatable, enterprise **adds** | §7.4 |
| 03 §11 — usage counters monotonic-merge on `(installed_item_id, counter_epoch)` | §3.5 |
| 03 §5.4 — `producer_node` on every envelope | §8.1 |
| 04 §3 — three ingest profiles, one storage model | **§4** |
| 04 §3 — the channel registry is the hard part | **§3.1** |
| 07 §10 — ICAS channel taxonomy not publicly found | **§2.5** — declared as a gap, not filled |

---

## 1. Purpose and scope

### 1.1 Purpose

Per document 04 §3: **ingest, store, and serve condition data, usage counters, and mission records across three operating domains with radically different data profiles, and produce versioned health indicators suitable for modeling.**

The operative word in that sentence is *versioned*. An indicator that cannot be recomputed over history when its definition improves is unusable, because definition improvement is a routine need. An indicator that *is* recomputed over history, without definition-time bookkeeping, poisons every training set assembled before the recomputation. Both halves are this service's problem and §5–§6 exist to hold them simultaneously.

### 1.2 Ownership boundary

**Owns** (04 §3): raw telemetry samples; **the channel registry and semantic mapping**; health indicator definitions and computed values; usage counter values; mission records; data quality assessments; automated anomaly detections.

**Does not own:** configuration (Registry); human anomaly tags (Post-Mission Analysis); predictions (PdM); causal interpretation (Failure Intelligence); the unit hierarchy, equipment families, or the failure-mode taxonomy (Reference Data, per 03 §14 and `[D35]`).

Two boundary clarifications that prevent recurring confusion:

- **Usage counter *values* are owned here; the installed item they attach to is not** (04 §2's Registry boundary, and `[C6]`, which found three claimed custodians for counters). A counter epoch opens and closes in response to Registry events; the Registry never writes a counter value.
- **Evidence packages for Post-Mission Analysis are materialized into PMA's own object store from this service's replay source, via this service's API** (04 §8, closing `[C36]` which found the storage claimed by both). This service owns the *replay source*; it does not own the evidence package.

### 1.3 What this document governs, and what it does not

| Governed here | Governed elsewhere |
|---|---|
| The channel registry schema and its versioning mechanics (§3.1) | The unit hierarchy and equipment-family vocabulary — Reference Data (12) |
| The three ingest adapters and the canonical sample model (§4) | Outbox, inbox, relay, clock discipline, conflict-policy enforcement, provisional identity — document 11 |
| The bitemporal feature-serving API and its query logic (§5) | `EventEnvelope`, `ClassificationLabel`, conformance harness — document 10 |
| Indicator definition versioning and recomputation (§6) | The synthetic corpus this service is tested against — document 13 |
| What runs afloat versus ashore (§7) | Indicator *content* (which spectral features, which thermodynamic derivations) — Phase 3, per family, informed by document 13 §7 |
| Envelope construction for all six published events (§8) | Detector *model* development and training — Domino, per 01 §7 |
| Two Helm profiles and their boundaries (§11) | Any Navy sensor specific — document 07, and see §2.5 |
| Every quantity is cited from 06 §7 or 13 §2 | Quantities are never invented here (09 §9.5 item 31) |

---

## 2. Service shape

### 2.1 Location and identity

Per document 09 §3.1 and §7.1, with no variation:

| Form | Value |
|---|---|
| Canonical slug (03 §3.1) | `telemetry` |
| Directory | `services/telemetry/` |
| Python distribution / package | `fathom-telemetry` / `fathom_telemetry` |
| API base path | `/api/v1/telemetry/` |
| Consumer group | `fathom-telemetry-v1` |
| Kubernetes label | `fathom.navy/service: telemetry` |
| Conformance directory | `packages/contracts/conformance/telemetry/` |
| Manifest directory | `packages/agent-tooling/manifests/telemetry/` |
| Topics | `fathom.telemetry.<aggregate>.v1` — enumerated in §8.2 |

### 2.2 Two deployment profiles of one slug

**This is the fact from which most of this document follows.**

| | Enterprise | Edge |
|---|---|---|
| `producer_node` (03 §5.4) | `enterprise` | `edge:<asset_id>` |
| Deployed | Once, on the Sustainment Plane | Once per afloat hull. **Demo: one SSN** (06 §4) |
| Monotonic sequence space | Its own | Its own, independent |
| Authors indicator definitions and channel mappings | **Yes, exclusively** | **Never** (§6.6) |
| Computes indicator values | Yes | Yes, from replicated read-only definitions |
| Runs detectors | Full ensemble, as Domino Jobs | Threshold + trending, in-cluster, on exported artifacts (§7) |
| Serves `/features` | Yes | Yes, resolved against **its own** knowledge sequence (§5.5) |
| Reaches enterprise services | Yes, per 09 §4.4.2's sanctioned edges | **No.** Only the `sync` coordinator (§11.3) |
| Edge reconciliation coordinator | Shore end active on the demo hull's peer; otherwise inert (11 §9.2) | Active |

> **Why this matters.** Document 11 §4.2 records the defect: document 03 §5.4 originally keyed ordering and deduplication on `(producer, monotonic_seq)`, where `producer` is "slug plus version." An edge instance and the enterprise instance are two nodes each minting its own sequence, so `(telemetry, 41)` is ambiguous — two different events collide on the dedup key and **one is silently dropped**. Document 03 §5.4 now carries `producer_node` explicitly and states the three-part key. This service is the reason that field exists, because it is the primary sub-application with a genuine edge deployment profile. Nothing in this codebase keys on two parts.

**`DECISION` — `producer_node` literal form follows document 03 §5.4, not document 11 §4.2's examples.** Document 03 §5.4 specifies `"enterprise" | "edge:<asset_id>"`. Document 11 §4.2, written before the correction landed, illustrates `telemetry@ashore-1` / `telemetry@ssn796`. Document 03 prevails (09's front-matter "Precedence" row). The value is the literal string `enterprise`, or `edge:` concatenated with the asset's `asset_id` UUID, and it is also carried as `clock.hlc.node_id`. Recorded in §15 as a correction document 11 should absorb.

### 2.3 Data stores — one logical database, two schemas

Finding **D33**: "Condition & Telemetry owns two databases, violating one-database-per-service." Document 03 §15.13's escape is explicit: *"Where a sub-application requires two storage engines, they are separate schemas of one owned cluster or are separately justified in Phase 3."*

| Store | Contents | Placement |
|---|---|---|
| **TimescaleDB cluster `fathom-telemetry-ts`** (09 §2.3) | Two schemas of one cluster. `ts`: sample and indicator-value hypertables with tiered continuous aggregates. `meta`: channel registry, indicator definitions, mission records, quality assessments, counters, candidates, **and the outbox, inbox, and `producer_sequence` tables** | Per profile. Enterprise in `fathom-data`; edge co-resident on the hull |
| **Object storage** (S3 API; MinIO in the demo — 09 §2.1) | Raw mission payloads retained for replay and PMA evidence; unmanned raw 10 Hz sortie objects (13 §2.2); `payload_ref` targets for `telemetry.batch_ingested` | Per profile |

Three rules:

1. **The outbox lives in `fathom-telemetry-ts`, in the same cluster as the hypertables**, per document 11 §2.7. `outbox.emit()` must be transactional with the ingest write, and there is no atomic two-database commit.
2. **`ts` and `meta` are schemas, not databases.** One `AsyncEngine`, one Alembic history, one credential. TimescaleDB hypertable DDL is `op.execute()` raw SQL inside ordinary Alembic revisions (09 §2.2).
3. **Telemetry never stores sample payloads inline in the outbox** (11 §2.6). `telemetry.batch_ingested` carries a `payload_ref` into object storage; the outbox row carries the envelope plus the reference. This is what prevents the storage doubling **D28** describes, and it is the same discipline `[D27]` imposes on `prediction.updated`.

### 2.4 Plane placement

Per document 04 §3, corrected for the edge profile:

- **Sustainment Plane:** ingest, storage, serving, the channel registry, the counter accumulator, mission boundary detection, the quality assessor, the indicator computation engine, and the point-in-time feature server. Both profiles.
- **Domino:** indicator *definition development*, detector *training*, and the full enterprise detector ensemble executing as scheduled Jobs that write results back through this service's bulk ingest operations (§9.3). **Telemetry never transits a Domino Endpoint** (04 §3, 02 §4.3).
- **Afloat:** no Domino component is resident or reachable (01 §12). Edge detectors execute exported artifacts in the edge inference runtime (§7.2).

### 2.5 The ICAS gap — declared, not filled

Document 01 §5 describes this sub-application as performing *"Sensor and ICAS-style ingest"*; document 01 §0 lists ICAS in the glossary as *"Integrated Condition Assessment System — existing Navy shipboard condition monitoring"*; document 04 §3 states that *"Surface assets deliver near-continuous HM&E monitoring in the manner of ICAS."*

**Document 07 §10 lists "ICAS channel taxonomy" under "Confirmed CAC-gated or unpublished."** There is no ICAS section anywhere in document 07. No channel names, tag conventions, record layouts, sampling rates, quality flags, or point-type vocabulary from ICAS or any other Navy condition-monitoring system were located in public-source research.

Consequences, all binding:

1. **No ICAS channel name, tag format, point type, or quality-flag value appears anywhere in this service, its schemas, its fixtures, or its documentation.** Document 07 §1's prohibition on fabrication is operative, not aspirational, and document 07's own framing is the reason: *"Fabricated schema detail is worse than an acknowledged gap, because a reviewer recognises it immediately."* The channel registry is designed so that ICAS semantics can be *loaded as data* when a CAC-gated source becomes available, and it carries no assumption about what those semantics are.
2. **Channel keys are program-defined and opaque**, in the same posture document 13 §6.3 adopts for family keys: shape-correct, value-reserved, explicitly synthetic. The `quantity` vocabulary in §3.1 is drawn from document 13 §7.4's `FamilySpec.channels.quantity` enumeration — which is a *generator* vocabulary written for this program, not a claim about any Navy system.
3. **"ICAS-style" is a statement about the *ingest profile*, not about a schema.** What documents 01 and 04 assert, and all they assert, is that surface HM&E monitoring is near-continuous. That is a rate and a cadence, and document 06 §7 supplies the rate (40 spotlight channels at 1 Hz, 200 routine channels at 1/minute). §4.3 implements exactly that and nothing more.
4. **A federation adapter is a Phase 3 item blocked on the source.** Document 04 §3 already anticipates the shape — *"an external historian or platform-provided data lake supplying raw samples, in which case this sub-application retains the channel registry, indicators, and feature serving while delegating sample storage."* The `source_tag_mapping` table (§3.1) is that seam. It is deliberately generic over source systems because we do not know what the real one looks like.

Recorded as **OQ-1** in §13. Document 07 §10's three highest-value follow-ups do not include ICAS; if the channel taxonomy matters to the demonstration's credibility with a NAVSEA reviewer, it should be added there rather than guessed at here.

---

## 3. Data model

Layering per document 09 §4.1. Everything below is `models/` (private SQLAlchemy) plus `schemas/` (Pydantic wire models importing canonical kernel types from `packages/canonical-schemas`, never redefining them).

### 3.0 The knowledge sequence — the spine of everything definition-time

Before the aggregates, the mechanism they all reference.

**`DECISION` — this service maintains a single gap-free monotonic `knowledge_seq` per `producer_node`, advanced by every act of learning, and every row representing something knowable carries the `knowledge_seq` at which it became knowable.**

An act of learning is any of:

| Act | Advances `knowledge_seq` |
|---|---|
| A telemetry batch is admitted | Yes — one allocation per batch |
| An indicator definition version is published | Yes |
| A channel definition, binding, or source-tag mapping version is published | Yes |
| A downsample reduction version is registered (§4.4) | Yes |
| A detector version is registered (§7.3) | Yes |
| An indicator recomputation run completes | Yes — one allocation per run |
| A usage counter observation is admitted | Yes |
| An edge record is **admitted at the shore ingress** | Yes — see §5.5, this is the important one |
| A sample's *data time* passes | **No.** Data time is not knowledge time |

Implementation is document 11 §4.3's `MonotonicSequencer` under the key `("telemetry", producer_node_id)` with a distinct logical stream name `knowledge`, allocated **inside the caller's transaction** so the sequence and the row it stamps commit together. It is gap-free for the same reason the event sequence is: a gap is unambiguous loss, and a receiver that has seen 41 and 43 can demand 42.

```sql
CREATE TABLE meta.knowledge_log (
  knowledge_seq   bigint      PRIMARY KEY,          -- gap-free, from MonotonicSequencer
  producer_node   text        NOT NULL,             -- 'enterprise' | 'edge:<asset_id>'
  kind            text        NOT NULL,             -- see the table above
  ref_kind        text        NOT NULL,             -- 'indicator_definition' | 'source_tag_mapping' | ...
  ref_id          text        NOT NULL,
  -- THE resolution column.  Set by THIS node, never by a producer.  See §5.4.
  known_at        timestamptz NOT NULL,
  authored_by     text        NULL,                 -- principal, where a human authored it
  correlation_id  uuid        NOT NULL,
  CONSTRAINT knowledge_log_node CHECK (producer_node IN ('enterprise') OR producer_node LIKE 'edge:%')
);
CREATE UNIQUE INDEX knowledge_log_at ON meta.knowledge_log (known_at, knowledge_seq);
```

Why an integer sequence rather than comparing timestamps everywhere:

- **It reuses a pattern the system already understands.** `baseline_epoch` is a monotonic per-asset configuration epoch that fences correctness (03 §5.4, `[D3, D4]`). `knowledge_seq` is a monotonic per-node definition epoch that fences leakage. Same shape, same reasoning.
- **It reduces the whole of §5's fencing to integer comparison.** One timestamp comparison happens, once, at the top of the query, against a single-clock column (§5.4). Everything downstream is `<=` on a bigint. That is what makes the resolver auditable and what keeps document 11 §11.5's static gate 4 satisfiable.
- **It makes edge-versus-enterprise knowability correct by construction** (§5.5).

### 3.1 `Channel` — the channel registry

> Document 04 §3: *"The channel registry is the integration surface, and it is the hard part. Mapping raw sensor tags to canonical channels per equipment type is where real deployments consume their schedule. The registry is therefore an explicit, versioned, reviewable artifact with its own lifecycle rather than configuration embedded in ingest code. A mapping change is a versioned event, because it changes the meaning of historical data."*

Finding **C51** records that document 01 §5 omitted the channel registry entirely, which document 04 §3 calls the hardest part of the sub-application. It is four tables, not one, and the separation is the design.

#### 3.1.1 `channel_definition` — the canonical measurement channel

What a channel *is*, independent of any hull, any item, and any acquisition system.

```sql
CREATE TABLE meta.channel_definition (
  channel_key        text     NOT NULL,        -- opaque, stable, program-defined.  See §2.5
  channel_version    integer  NOT NULL,
  quantity           text     NOT NULL,        -- vibration_rms | temperature | pressure | flow |
                                               -- torque | sensitivity_db | leak_rate |
                                               -- efficiency_proxy | speed | current | level
                                               -- (13 §7.4 FamilySpec.channels.quantity)
  unit_code          text     NOT NULL,        -- FROM REFERENCE DATA's unit hierarchy.  Never free text
  unit_version        text    NOT NULL,        -- the reference-data version the unit was resolved at
  value_type         text     NOT NULL,        -- continuous | counter | boolean | categorical
  sample_semantics   text     NOT NULL,        -- instantaneous | mean_over_interval |
                                               -- max_over_interval | event
  nominal_min        double precision NULL,    -- plausibility band, NOT an alarm limit
  nominal_max        double precision NULL,
  saturation_min     double precision NULL,    -- the transducer's range.  Feeds CLIPPED detection (§4.6)
  saturation_max     double precision NULL,
  description        text     NOT NULL,

  published_seq      bigint   NOT NULL REFERENCES meta.knowledge_log(knowledge_seq),
  superseded_seq     bigint   NULL     REFERENCES meta.knowledge_log(knowledge_seq),
  supersedes         integer  NULL,            -- prior channel_version
  review_state       text     NOT NULL,        -- draft | in_review | published | superseded

  PRIMARY KEY (channel_key, channel_version),
  CONSTRAINT channel_def_published_reviewed
    CHECK (review_state <> 'published' OR published_seq IS NOT NULL),
  CONSTRAINT channel_def_unit_not_freetext CHECK (unit_code = lower(unit_code) AND unit_code !~ ' ')
);
```

- **`unit_code` resolves against Reference Data and is never a string a developer typed.** Reference Data owns the unit hierarchy (04 §11). A channel whose unit cannot be resolved at the declared `unit_version` fails publication. A unit mismatch between a mapping's `transform` output and the channel's declared unit is a publication failure, not a runtime surprise (§10.4).
- **`nominal_*` is a plausibility band, `saturation_*` is the transducer's physical range, and they are different things.** The quality assessor uses the first to flag `IMPLAUSIBLE` and the second to flag `CLIPPED` (document 13 §9.2 stage 1: *"an extreme excursion saturates rather than reading its true value. A model that extrapolates from a clipped peak is wrong, and clipped peaks are common in real vibration data"*). Conflating them makes saturation invisible.

#### 3.1.2 `channel_binding` — per-equipment-type binding

Document 04 §3's aggregate note: *"A canonical measurement channel bound to an equipment type."* Binding is where domain-specific rate lives, because the same canonical channel is sampled at 1 Hz on a surface hull, 1/minute on a submarine, and 10 Hz on an unmanned vehicle (06 §7).

```sql
CREATE TABLE meta.channel_binding (
  binding_id         uuid     PRIMARY KEY,
  binding_version    integer  NOT NULL,
  channel_key        text     NOT NULL,
  channel_version    integer  NOT NULL,
  equipment_family   text     NOT NULL,        -- FROM REFERENCE DATA, versioned  [D35]
  family_version     text     NOT NULL,
  domain             text     NOT NULL,        -- surface | subsurface | unmanned  (03 §3.3 AssetRef)
  role               text     NOT NULL,        -- primary | secondary | decoy   (13 §7.3)
  sharing            text     NOT NULL,        -- dedicated | shared            (13 §7.3)
  expected_rate_hz   numeric  NOT NULL,        -- 1 | 0.016666 | 10 per 06 §7.  Drives completeness
  required_for       text[]   NOT NULL,        -- indicator_key[] that cannot compute without it

  valid_from         timestamptz NOT NULL,     -- DATA time
  valid_to           timestamptz NULL,
  published_seq      bigint   NOT NULL REFERENCES meta.knowledge_log(knowledge_seq),
  superseded_seq     bigint   NULL REFERENCES meta.knowledge_log(knowledge_seq),

  FOREIGN KEY (channel_key, channel_version)
    REFERENCES meta.channel_definition(channel_key, channel_version),
  CONSTRAINT binding_rate_positive CHECK (expected_rate_hz > 0)
);
```

- **`role = decoy` is published, not hidden.** Document 13 §7.3 requires *"at least one channel per spotlight family is a decoy: it correlates with the degradation state through a shared confounder (load, ambient temperature) without being caused by the fault. Spurious feature selection must have something to select."* Suppressing decoys from the feature surface would defeat the trap; publishing the role is what lets `contributing_factors`' stability analysis (03 §7.1, `[D23]`) demonstrate that it resists.
- **`sharing = shared` is the attribution-ambiguity flag.** Per document 13 §7.3, a lube-oil temperature serving both a bearing set and its cooler means *"a degradation signature does not identify which item caused it."* That ambiguity is carried as data (§3.1.4), never resolved by assumption.
- **`expected_rate_hz` is what makes completeness computable.** Without a declared expected rate, "how many samples should have arrived" is unanswerable, and document 04 §3's requirement that consumers *"distinguish 'no fault observed' from 'not observed'"* cannot be met.

#### 3.1.3 `source_tag_mapping` — the versioned mapping from raw sensor tags

**This is the integration surface, and it is bitemporal in exactly the Registry's sense.**

```sql
CREATE TABLE meta.source_tag_mapping (
  mapping_id         uuid     PRIMARY KEY,
  mapping_version    integer  NOT NULL,
  asset_id           uuid     NOT NULL,        -- mappings are PER HULL.  Class template in §3.1.5
  source_system      text     NOT NULL,        -- opaque acquisition-system identifier.  See §2.5
  source_tag         text     NOT NULL,        -- the raw tag string AS IT APPEARS ON THE WIRE
  channel_key        text     NOT NULL,
  channel_version    integer  NOT NULL,

  -- WHAT the tag observes.  Exactly one of these, and the choice is load-bearing.
  attachment         text     NOT NULL,        -- position_wired | item_integral
  position_id        uuid     NULL,            -- required when attachment = position_wired
  installed_item_id  uuid     NULL,            -- required when attachment = item_integral

  transform          jsonb    NOT NULL,        -- declarative: {scale, offset, unit_from, unit_to,
                                               --  clamp?, deadband?}.  NEVER code.  See below
  confidence         text     NOT NULL,        -- asserted | inferred | provisional
  evidence_ref       text     NULL,            -- drawing, survey, vendor sheet, walkdown record

  -- DATA time: which SAMPLES this mapping applies to.
  valid_from         timestamptz NOT NULL,
  valid_to           timestamptz NULL,
  -- KNOWLEDGE time: when we came to BELIEVE it.
  published_seq      bigint   NOT NULL REFERENCES meta.knowledge_log(knowledge_seq),
  superseded_seq     bigint   NULL REFERENCES meta.knowledge_log(knowledge_seq),
  authored_by        text     NOT NULL,
  review_state       text     NOT NULL,        -- draft | in_review | published | superseded

  FOREIGN KEY (channel_key, channel_version)
    REFERENCES meta.channel_definition(channel_key, channel_version),
  CONSTRAINT mapping_attachment_exclusive CHECK (
    (attachment = 'position_wired' AND position_id IS NOT NULL AND installed_item_id IS NULL) OR
    (attachment = 'item_integral'  AND installed_item_id IS NOT NULL AND position_id IS NULL)
  ),
  CONSTRAINT mapping_valid_range CHECK (valid_to IS NULL OR valid_to > valid_from)
);

-- One published mapping per (asset, source_system, source_tag) per data-time instant.
CREATE EXTENSION IF NOT EXISTS btree_gist;
ALTER TABLE meta.source_tag_mapping
  ADD CONSTRAINT mapping_no_overlap
  EXCLUDE USING gist (
    asset_id WITH =, source_system WITH =, source_tag WITH =,
    tstzrange(valid_from, valid_to) WITH &&
  ) WHERE (review_state = 'published');
```

Four rules, each closing a specific defect.

**(a) Bitemporality, stated as the Registry states it.** `valid_from`/`valid_to` say which *samples* the mapping applies to. `published_seq` says when we came to believe it. A mapping correction entered three weeks late — a walkdown discovers that tag `X` was wired to the wrong position all along — **changes valid time without rewriting knowledge time.** Document 04 §2 makes exactly this argument for configuration: *"A configuration correction entered three weeks late changes valid time without rewriting record time, so a prediction computed on stale information remains explicable rather than appearing to have been computed from data that contradicts it."*

> **Why this matters.** Finding **D22**, in its own words: *"Indicator definitions and channel mappings are explicitly recomputed over history, so a model trained at `as_of=2025-03-01` receives values computed by a definition authored in 2026 by someone who had seen the 2025 failures. The Registry solves this with bitemporality; Condition & Telemetry offers only `as_of`."* Mappings are named in that finding alongside definitions. A bitemporal indicator definition on top of a single-temporal mapping table leaks through the mapping. Both halves are required, and this is the mapping half.

**(b) `attachment` — sensors are position-wired; features are item-attributed.** A transducer is bolted to a location. It observes whatever item currently occupies that position. So the common case is `attachment = position_wired`, and resolution to `installed_item_id` happens **through the Registry's configuration at the sample's data time** (§4.5). `attachment = item_integral` is permitted only where the sensor physically travels with the item — an instrumented bearing housing, a smart actuator — and is then a mapping the ship must correct when the item is landed.

> **Why this matters.** This is **D9**'s defect in its telemetry form. Document 03 §3.3: *"remaining useful life, usage accumulation, and failure history attach to the installed item, and a payload that conflates the two produces the inherited-degradation failure document 04 §2 exists to prevent."* If a mapping bound a tag directly to an `installed_item_id` and the pump at that position were replaced, every subsequent sample would be attributed to the item that was landed — the new pump would inherit its predecessor's vibration history, and the RUL model's most important covariate would be silently corrupt. Position-wiring plus data-time configuration resolution is what prevents that, and it is why `installed_item.installed` and `installed_item.removed` are correctness dependencies for this service (04 §3) rather than informational events.

**(c) `transform` is declarative data, never code.** `{scale, offset, unit_from, unit_to, clamp?, deadband?}` evaluated by a fixed interpreter. Rationale: document 04 §3 requires the registry to be *"an explicit, versioned, reviewable artifact with its own lifecycle rather than configuration embedded in ingest code."* An expression language or a plugin hook re-embeds the mapping in code, defeats review, and makes the mapping version meaningless because the code can change under a fixed version. A transform that cannot be expressed declaratively is a channel-definition problem (the wrong `quantity` or `unit`), not a transform problem.

**(d) `confidence = provisional` is admissible and is not the same as unmapped.** Real integrations begin with inferred mappings from tag-naming conventions and converge through walkdowns. `provisional` mappings produce samples, and those samples produce indicator values, and both carry the mapping version — so when the walkdown corrects the mapping, the correction is a new `mapping_version` at a new `published_seq`, history is recomputed under the new version, and **a model trained before the walkdown still sees exactly what it saw.** An unmapped tag is a different case and is quarantined (§4.5), never dropped.

#### 3.1.4 `channel_item_map` — the derived many-to-many projection

```sql
CREATE TABLE meta.channel_item_map (
  channel_key        text     NOT NULL,
  installed_item_id  uuid     NOT NULL,
  position_id        uuid     NOT NULL,
  asset_id           uuid     NOT NULL,
  sharing            text     NOT NULL,        -- from the binding
  attribution_weight numeric  NULL,            -- NULL where genuinely unresolvable.  Never defaulted to 1
  valid_from         timestamptz NOT NULL,
  valid_to           timestamptz NULL,
  derived_at_seq     bigint   NOT NULL REFERENCES meta.knowledge_log(knowledge_seq),
  PRIMARY KEY (channel_key, installed_item_id, valid_from)
);
```

Derived from `source_tag_mapping` ⋈ Registry configuration. **Emitted through `GET /channels/{channel_key}/items` and `GET /installed-items/{id}/channels` so attribution ambiguity is visible to a modeler rather than hidden inside the feature server.** Document 13 §7.3 records the generator side: *"The generator emits the many-to-many channel-to-item map as data (`telemetry/channel_item_map`), and ground truth records which item actually caused each excursion. Any model that resolves attribution correctly has earned it."* The service's obligation is to hand the modeler the same ambiguity the generator created — `attribution_weight IS NULL` where a shared channel genuinely cannot apportion, never a fabricated 1.0.

#### 3.1.5 `channel_registry_version` and the class template

**`DECISION` — `channel_registry_version` is not a fifth table. It is the `knowledge_seq` of the most recent registry publication.**

```
channel_registry_version(at_seq) :=
  max(knowledge_seq) FROM meta.knowledge_log
   WHERE ref_kind IN ('channel_definition','channel_binding','source_tag_mapping',
                      'reduction_version')
     AND knowledge_seq <= at_seq
```

Justification: a second version counter would have to be kept consistent with the knowledge sequence, and two counters that can disagree are one counter and a bug. Every `indicator_value` row records the resolved `channel_registry_version` so the value is auditable against exactly the registry state that produced it, and `health_indicator.computed` carries it in the payload (§8.2).

**Class template.** Bindings and mappings are provisioned per hull from a class template on `asset.registered` (§8.3), then deviate — the same class-template-plus-deviation shape document 04 §2 adopts for configuration, and for the same reason: *"Ships of one class diverge substantially over their service lives."* The template is `review_state = 'draft'` on arrival at a new hull. **Nothing computes from a draft mapping**; provisioning does not imply review.

#### 3.1.6 The mapping-change event, and why it is not published yet

Document 04 §3 states: *"A mapping change is a versioned event, because it changes the meaning of historical data."*

**Document 03 §6's Telemetry catalog contains six events, and none of them is a channel-mapping event.** Publishing a seventh would violate document 09 §8.2's Definition of Done (`events/catalog.py` must equal document 03 §6's rows for this slug) and document 13 §14.2's rule that *"every emitted type must exist in the 03 §6 event catalog."* So:

1. **A mapping change is recorded as a versioned entity and advances `knowledge_seq`.** That satisfies the substance of 04 §3's requirement — the change is versioned and history's meaning is traceable.
2. **It is surfaced to consumers through `GET /channels?changed_since=` and `GET /channel-mappings?changed_since=`** (03 §4's mandatory snapshot/change-feed reads).
3. **Its downstream consequence is announced through `health_indicator.computed`**, which carries a bumped `channel_registry_version` and `recomputation_reason: channel_mapping_change`. Adding those two fields to the payload is an additive optional change requiring no version bump (03 principle 5).
4. **No new topic and no new event type is created.** Recorded as **OQ-2** in §13: document 03 §6 should gain a `channel_mapping.version_published` row with consumers `pdm` and `pma`, or document 04 §3's sentence should be read as satisfied by (1)–(3). This document does not decide it unilaterally.

### 3.2 `TelemetryBatch`

Document 04 §3: *"An ingested unit of samples with provenance, time range, and quality assessment."*

```sql
CREATE TABLE meta.telemetry_batch (
  batch_id           uuid        PRIMARY KEY,
  asset_id           uuid        NOT NULL,
  mission_id         uuid        NULL,            -- resolved by the boundary detector (§4.7)
  domain_profile     text        NOT NULL,        -- surface | subsurface | unmanned

  -- PROVENANCE (04 §3)
  producer_node      text        NOT NULL,        -- 'enterprise' | 'edge:<asset_id>'.  03 §5.4
  source_system      text        NOT NULL,
  source_batch_ref   text        NULL,            -- the SOURCE's own batch identity, preserved
  adapter_key        text        NOT NULL,        -- which IngestAdapter accepted it (§4.2)
  adapter_version    text        NOT NULL,
  reduction_version  text        NULL,            -- §4.4.  NOT NULL for unmanned
  raw_payload_ref    text        NULL,            -- s3:// object.  NOT NULL where raw is retained
  raw_payload_sha256 bytea       NULL,
  idempotency_key    text        NOT NULL,        -- 03 §4; required for edge sync
  ingest_monotonic_seq bigint    NOT NULL,        -- THE ordering key.  11 §4.3

  -- TIME RANGE.  Data time, from the source's own timebase.
  data_time_from     timestamptz NOT NULL,
  data_time_to       timestamptz NOT NULL,
  -- KNOWLEDGE time.  Set by THIS node at admission.  Never by the producer.
  known_at_seq       bigint      NOT NULL REFERENCES meta.knowledge_log(knowledge_seq),

  -- CLOCK ATTESTATION.  Copied from the envelope, retained permanently (03 §5.4, 11 §10.5)
  sync_quality       jsonb       NOT NULL,
  timebase_degraded  boolean     NOT NULL,        -- dispersion_ms > inter-sample interval.  §4.6

  -- QUALITY ASSESSMENT (04 §3).  Absence is recorded, never inferred
  channel_set        text[]      NOT NULL,
  sample_count       bigint      NOT NULL,
  expected_sample_count bigint   NOT NULL,        -- from binding.expected_rate_hz × active window
  completeness       numeric     NOT NULL,        -- sample_count / expected_sample_count
  quality            jsonb       NOT NULL,        -- QualityAssessment; see §4.6
  observation_state  text        NOT NULL,        -- observed | partially_observed | not_observed

  classification     jsonb       NOT NULL,        -- 03 §7.3
  correlation_id     uuid        NOT NULL,

  CONSTRAINT batch_time_range CHECK (data_time_to >= data_time_from),
  CONSTRAINT batch_completeness CHECK (completeness >= 0),
  CONSTRAINT batch_node CHECK (producer_node = 'enterprise' OR producer_node LIKE 'edge:%'),
  CONSTRAINT batch_reduction_when_unmanned
    CHECK (domain_profile <> 'unmanned' OR reduction_version IS NOT NULL)
);
CREATE UNIQUE INDEX batch_dedup
  ON meta.telemetry_batch (producer_node, ingest_monotonic_seq);
CREATE INDEX batch_changed_since ON meta.telemetry_batch (known_at_seq);
```

Three fields carry more weight than their size suggests.

- **`producer_node`.** The dedup index is `(producer_node, ingest_monotonic_seq)`, never `ingest_monotonic_seq` alone. A submarine's batch 41 and the enterprise's batch 41 are different batches; a two-part key silently drops one (§2.2).
- **`observation_state`.** `not_observed` is a first-class value and is **not** the same as `completeness = 0`. A submarine dark for six weeks did not observe; a surface hull whose channel died observed nothing. Document 04 §3: consumers must *"distinguish 'no fault observed' from 'not observed.'"* Document 13 §7.5 states the generator's half: *"A generator that emits gaps without completeness metadata has manufactured a silent bias in every downstream label."* The service's half is that the state is stored, exposed on `/features` (§5.3), and never defaulted.
- **`known_at_seq` is set by the admitting node.** For an enterprise-ingested batch it is allocated at ingest. For an edge-originated batch arriving on reconnect it is allocated **at the shore ingress**, weeks after `data_time_to`. That is not an artifact; it is the honest semantics, and §5.5 explains why it is the mechanism that makes the submarine case leak-free.

### 3.3 The canonical sample model

**One sample model. There is no second one.** Document 04 §3's key decision: *"three ingest adapters over one canonical channel and sample model, rather than three storage designs."*

```sql
CREATE TABLE ts.sample (
  channel_key        text        NOT NULL,
  channel_version    integer     NOT NULL,
  asset_id           uuid        NOT NULL,
  position_id        uuid        NOT NULL,        -- where the transducer is
  installed_item_id  uuid        NULL,            -- resolved at DATA time.  NULL => unattributed
  data_time          timestamptz NOT NULL,        -- THE domain time of the observation
  value              double precision NULL,       -- NULL => ABSENT.  Never 0, never a sentinel
  sample_quality     smallint    NOT NULL,        -- bitmask; see SampleQuality in §4.6
  batch_id           uuid        NOT NULL,
  mapping_version    integer     NOT NULL,
  known_at_seq       bigint      NOT NULL,
  PRIMARY KEY (channel_key, asset_id, data_time, batch_id)
);
SELECT create_hypertable('ts.sample', 'data_time', chunk_time_interval => INTERVAL '1 day');
SELECT add_dimension('ts.sample', 'asset_id', number_partitions => 16);
```

- **`value IS NULL` means absent.** Document 13 §9.6 stage 5: *"the sample is absent, not zero."* A zero in a vibration channel is a physically meaningful reading. A pipeline that writes 0 for a dropped sample has manufactured a measurement.
- **`installed_item_id` is nullable and the nullability is deliberate.** A sample whose position is not in the current baseline, or whose position is momentarily unoccupied, is retained with `installed_item_id = NULL` and surfaced through `GET /quality`. It is never dropped and never attributed by guess.
- **Rollups are continuous aggregates over this one table** (1-minute, 1-hour, 1-day), per document 04 §3's "tiered rollups" and document 13 §7.5's out-of-window aggregate emission. Retention differs by tier and is declared in the Helm values (§11.4), not in code.

### 3.4 `HealthIndicator` — a versioned **definition** plus computed **values**

Document 04 §3: *"A versioned derived feature definition and its computed values"*, and: *"Health indicators are deterministic, versioned, and replayable — not models."*

**The separation of definition from value is what closes D22.** Two tables, and the definition table is the one that carries definition time.

#### 3.4.1 `indicator_definition`

```sql
CREATE TABLE meta.indicator_definition (
  indicator_key      text     NOT NULL,          -- opaque, stable
  definition_version integer  NOT NULL,
  feature_set        text     NOT NULL,          -- the ?feature_set= selector of §5
  feature_set_version integer NOT NULL,
  equipment_family   text     NOT NULL,          -- from Reference Data, versioned  [D35]
  family_version     text     NOT NULL,

  -- THE COMPUTATION.  Deterministic, declarative, replayable (04 §3)
  spec               jsonb    NOT NULL,          -- see the four required members below
  input_channels     text[]   NOT NULL,          -- channel_key[]; resolved through the binding
  window_seconds     integer  NOT NULL,
  window_alignment   text     NOT NULL,          -- calendar | mission_anchored | event_anchored
  min_completeness   numeric  NOT NULL,          -- below this the value is NOT emitted.  See §5.3
  unit_code          text     NOT NULL,
  unit_version       text     NOT NULL,

  -- DEFINITION TIME.  The whole point.  [D22]
  published_seq      bigint   NOT NULL REFERENCES meta.knowledge_log(knowledge_seq),
  superseded_seq     bigint   NULL REFERENCES meta.knowledge_log(knowledge_seq),
  supersedes         integer  NULL,
  authored_by        text     NOT NULL,
  authored_rationale text     NOT NULL,          -- required.  A definition change is reviewable
  review_state       text     NOT NULL,          -- draft | in_review | published | superseded
  spec_sha256        bytea    NOT NULL,          -- over the canonical serialization of `spec`

  PRIMARY KEY (indicator_key, definition_version),
  CONSTRAINT indicator_def_published
    CHECK (review_state <> 'published' OR published_seq IS NOT NULL),
  CONSTRAINT indicator_def_min_completeness CHECK (min_completeness > 0 AND min_completeness <= 1)
);
```

`spec` has four required members, and the constraint is that all four are declarative:

| Member | Contents |
|---|---|
| `pipeline[]` | An ordered list of typed operators — `resample`, `filter`, `normalize_by`, `aggregate`, `spectral_band`, `thermodynamic`, `ratio`, `robust_center`, `slope` — each with typed parameters. A fixed interpreter, not an expression language |
| `normalization` | Which operating-condition covariates the indicator normalizes against, named explicitly. Document 13 §9.5 makes this the load-bearing property: *"The degradation contribution is often smaller than the operating-condition contribution"* |
| `missing_policy` | `refuse` \| `interpolate_bounded` \| `carry_forward_bounded`, with bounds. **Never an unbounded fill.** The chosen policy is recorded on every value it produced |
| `outlier_policy` | `retain` \| `flag_only` \| `robust_center`. **Removal is a definition decision, hence versioned, hence visible to `as_known_at`** (§4.6) |

> **Why `authored_rationale` is `NOT NULL`.** A definition change silently rewrites the meaning of every historical value computed under it. The rationale is the artifact a reliability engineer reads two years later when a model's behavior changed and nobody remembers why. It costs a sentence and it is the difference between a versioned artifact and a version number.

#### 3.4.2 `indicator_value`

```sql
CREATE TABLE ts.indicator_value (
  value_seq          bigint      NOT NULL,        -- per-node monotonic, unique.  THE tiebreak (§5.2)
  installed_item_id  uuid        NOT NULL,        -- NOT position_id.  03 §3.3
  indicator_key      text        NOT NULL,
  definition_version integer     NOT NULL,        -- WHICH definition produced this
  window_start       timestamptz NOT NULL,        -- DATA time
  window_end         timestamptz NOT NULL,        -- DATA time.  THE data-time fence column (§5.2)
  value              double precision NOT NULL,
  unit_code          text        NOT NULL,

  -- provenance sufficient to trace any operator-visible figure (03 §15.9)
  channel_registry_version bigint NOT NULL,       -- §3.1.5
  contributing_channels text[]   NOT NULL,
  contributing_batches uuid[]    NOT NULL,
  sample_count       integer     NOT NULL,
  expected_sample_count integer  NOT NULL,
  completeness       numeric     NOT NULL,
  quality_flags      integer     NOT NULL,        -- union of contributing sample_quality
  missing_policy_applied text    NOT NULL,
  outlier_policy_applied text    NOT NULL,

  -- KNOWLEDGE time.  One allocation per computation run (§3.0)
  known_at_seq       bigint      NOT NULL,
  computation_run_id uuid        NOT NULL,
  producer_node      text        NOT NULL,        -- 'enterprise' | 'edge:<asset_id>'
  is_current         boolean     NOT NULL,        -- LATEST-SERVING CONVENIENCE ONLY.  See §6.5

  PRIMARY KEY (installed_item_id, indicator_key, window_end, value_seq)
);
SELECT create_hypertable('ts.indicator_value', 'window_end',
                         chunk_time_interval => INTERVAL '7 days');

-- One value per (item, indicator, window, definition, registry version) per run.
CREATE UNIQUE INDEX indicator_value_run_unique ON ts.indicator_value
  (installed_item_id, indicator_key, window_start, window_end,
   definition_version, channel_registry_version, computation_run_id);

-- THE resolver's index.  Column order matches §5.2's predicate order exactly.
CREATE INDEX indicator_value_resolve ON ts.indicator_value
  (installed_item_id, indicator_key, window_end DESC, known_at_seq DESC, value_seq DESC);
```

**Values are append-only. A recomputation inserts; it never updates a value row.** `is_current` is maintained for latest-serving convenience and **the bitemporal resolver of §5.2 never reads it** (§6.5 explains why that separation is mandatory rather than tidy).

### 3.5 `UsageCounter` — keyed on `(installed_item_id, counter_epoch)`

Document 03 §11, as corrected: *"Monotonic merge keyed on `(installed_item_id, counter_epoch)`; `usage_counter.reset` opens a new epoch; authoritative correction permitted with provenance and exempt from monotonicity. Keying on position rather than item would credit a new item with its predecessor's hours. Unqualified max-merge makes one sensor glitch permanent `[D9]`."*

```sql
CREATE TABLE meta.usage_counter_epoch (
  installed_item_id  uuid        NOT NULL,        -- THE key.  There is NO position_id column here
  counter_type       text        NOT NULL,        -- steaming_hours | eoh | cycles | sorties | dives
                                                  -- (03 §7.1's `rul.unit` vocabulary)
  counter_epoch      integer     NOT NULL,        -- 1-based; opened by install, advanced by reset

  epoch_opening_value numeric    NOT NULL,        -- the meter reading at epoch open
  carry_forward_total numeric    NOT NULL,        -- Σ prior epochs' contributions.  See below
  current_value      numeric     NOT NULL,        -- the MERGED value within this epoch
  unit_code          text        NOT NULL,

  opened_reason      text        NOT NULL,        -- item_installed | meter_replaced |
                                                  -- meter_rollover | meter_zeroed_at_overhaul |
                                                  -- datasource_changed
  opened_at          timestamptz NOT NULL,        -- DATA time
  opened_seq         bigint      NOT NULL REFERENCES meta.knowledge_log(knowledge_seq),
  closed_at          timestamptz NULL,
  closed_seq         bigint      NULL REFERENCES meta.knowledge_log(knowledge_seq),
  final_value        numeric     NULL,            -- frozen on close.  Never recomputed

  is_open            boolean     NOT NULL,
  producer_node      text        NOT NULL,

  PRIMARY KEY (installed_item_id, counter_type, counter_epoch),
  CONSTRAINT counter_one_open_epoch EXCLUDE (installed_item_id WITH =, counter_type WITH =)
    WHERE (is_open),
  CONSTRAINT counter_closed_has_final
    CHECK (is_open OR (closed_at IS NOT NULL AND final_value IS NOT NULL)),
  CONSTRAINT counter_epoch_positive CHECK (counter_epoch >= 1)
);

CREATE TABLE meta.usage_counter_observation (
  observation_id     uuid        PRIMARY KEY,
  installed_item_id  uuid        NOT NULL,
  counter_type       text        NOT NULL,
  counter_epoch      integer     NOT NULL,
  observed_value     numeric     NOT NULL,
  data_time          timestamptz NOT NULL,
  known_at_seq       bigint      NOT NULL,
  producer_node      text        NOT NULL,
  monotonic_seq      bigint      NOT NULL,
  merge_decision     text        NOT NULL,        -- applied | ignored_subsumed | correction
  -- Correction provenance.  Required when merge_decision = 'correction' (03 §11)
  correction_authority text      NULL,
  correction_reason  text        NULL,
  correction_evidence_ref text   NULL,
  corrected_from     numeric     NULL,
  CONSTRAINT observation_correction_provenance CHECK (
    merge_decision <> 'correction' OR
    (correction_authority IS NOT NULL AND correction_reason IS NOT NULL
     AND correction_evidence_ref IS NOT NULL AND corrected_from IS NOT NULL)
  ),
  FOREIGN KEY (installed_item_id, counter_type, counter_epoch)
    REFERENCES meta.usage_counter_epoch(installed_item_id, counter_type, counter_epoch)
);
CREATE UNIQUE INDEX observation_dedup
  ON meta.usage_counter_observation (producer_node, monotonic_seq);
```

#### 3.5.1 The exact reset-opens-new-epoch mechanic

```
OPEN  epoch 1, on installed_item.installed (§8.3):
        epoch_opening_value  := usage_at_install        -- from InstalledItemRef; 0 for a new item,
                                                        -- the prior life for a rotable
        carry_forward_total  := 0
        current_value        := usage_at_install
        opened_reason        := 'item_installed'
        emit usage_counter.updated

MERGE within an open epoch N, on an observation (11 §7.4):
        if observation.is_authoritative_correction:
            current_value := observation.observed_value          -- EXEMPT from monotonicity
            record correction provenance; emit usage_counter.updated {correction: true}
        elif observation.observed_value > current_value:
            current_value := observation.observed_value           -- max() over a DOMAIN QUANTITY
            emit usage_counter.updated
        else:
            record merge_decision = 'ignored_subsumed'; emit nothing

RESET, on POST /usage-counters/{item}/{type}/resets  (a sanctioned sub-resource action, 03 §4):
   ONE transaction:
     1. epoch N:  final_value := current_value
                  closed_at   := reset.data_time
                  closed_seq  := allocate knowledge_seq
                  is_open     := false
     2. epoch N+1: epoch_opening_value := reset.new_meter_reading    -- usually 0, NOT assumed
                   carry_forward_total := epoch N's carry_forward_total
                                          + (epoch N's final_value - epoch N's epoch_opening_value)
                   current_value       := reset.new_meter_reading
                   opened_reason       := reset.reason
                   is_open             := true
     3. emit usage_counter.reset  {counter_epoch_closed: N, counter_epoch_opened: N+1,
                                   reason, meter_replacement_reference, final_value}
     4. emit usage_counter.updated for epoch N+1
   -- Values NEVER merge across counter_epoch.  A replaced hour meter legitimately reads
   -- LOWER than the one it replaced, and a cross-epoch max() would pin the counter forever.

CLOSE, on installed_item.removed (§8.3):
        close the open epoch; freeze final_value.  Do NOT open a new epoch.
        The replacement item gets its OWN (installed_item_id, counter_type, 1).
```

**The quantity models consume is `life_to_date`, and it is derived, not merged:**

```
life_to_date(item, counter_type) :=
    carry_forward_total(open epoch) + (current_value - epoch_opening_value) of the open epoch
  + Σ over closed epochs after the open one   -- (empty; there is exactly one open epoch)
```

That separation is the whole design. **Monotonic merge operates on `current_value` within one epoch. The model-facing figure spans epochs and is a sum.** Conflating them is how a meter replacement becomes either a loss of the item's accumulated life or a spurious drop to zero in the RUL model's clock.

> **Why this matters — all three of D9's bugs, in this service's terms.** (a) *Keying.* There is **no `position_id` column on either counter table**, so position-keying is unwritable. A new pump at position `233-04-A` starts at its own `(installed_item_id, counter_type, 1)`; it cannot inherit the predecessor's hours because the predecessor's rows are keyed on a different item. (b) *Irreversibility.* Document 03 §11 and document 11 §7.4: *"Unqualified max-merge makes one sensor glitch permanent."* An authoritative correction may **lower** `current_value`, is exempt from monotonicity, and carries authority, reason, evidence, and the value it corrected from — all four `NOT NULL`, enforced by CHECK. (c) *Resets.* *"Real hour meters get replaced and reset, with no representation for a reset."* `counter_epoch` plus `usage_counter.reset` is that representation, and the exclusion constraint guarantees exactly one open epoch per `(item, counter_type)` so "which epoch is current" is never a query with two answers.

### 3.6 `MissionRecord`

Document 04 §3: *"An underway period, patrol, or sortie, with boundaries and data completeness."* Document 03 §11: *"Edge-authoritative on creation; enterprise-authoritative thereafter."*

```sql
CREATE TABLE meta.mission_record (
  mission_id         uuid        PRIMARY KEY,     -- 03 §3.2: "mission", never "mission event"
  asset_id           uuid        NOT NULL,
  mission_type       text        NOT NULL,        -- underway_period | patrol | sortie
  started_at         timestamptz NOT NULL,        -- DATA time
  ended_at           timestamptz NULL,
  boundary_source    text        NOT NULL,        -- reported | inferred | reconciled  (04 §3 Q4)
  boundary_evidence  jsonb       NOT NULL,        -- which channels/reports; how reconciled
  ofrp_phase         text        NULL,            -- covariate; from Registry's asset read model

  -- DATA COMPLETENESS per mission (04 §3), not per batch
  expected_channel_set text[]    NOT NULL,        -- from bindings in force over the mission
  observed_channel_set text[]    NOT NULL,
  completeness       numeric     NOT NULL,
  observation_state  text        NOT NULL,        -- observed | partially_observed | not_observed
  gap_intervals      jsonb       NOT NULL,        -- [{from,to,cause}] — enumerated, never summarized

  -- AUTHORITY, per 03 §11's EDGE_AUTHORITATIVE_THEN_ENTERPRISE (11 §7.3)
  created_by_node    text        NOT NULL,
  authority          text        NOT NULL,        -- edge | enterprise
  authority_transitioned_at_seq bigint NULL,      -- recorded ON THE RECORD, never inferred

  known_at_seq       bigint      NOT NULL,
  classification     jsonb       NOT NULL,
  CONSTRAINT mission_ended_after_started CHECK (ended_at IS NULL OR ended_at > started_at)
);
```

- **`boundary_source` answers document 04 §3's open question explicitly** (*"Mission boundary determination: reported, inferred from telemetry, or both with reconciliation"*) with `reconciled` as the designed case and `boundary_evidence` recording how. §4.7 gives the detector.
- **`authority` and `authority_transitioned_at_seq` are stored, not derived.** Document 11 §7.3: *"The transition is recorded on the record itself so authority is never ambiguous mid-flight."* A mission whose authority must be inferred from whether the ship is currently reachable is bound to liveliness, which document 03 §11 singles out as the DDS anti-pattern.
- **`gap_intervals` enumerates, and does not summarize.** A single completeness scalar cannot tell a reviewer whether the missing hour was at the start of the patrol or across the failure.

### 3.7 `DetectedAnomaly` — with `origin`

Document 04 §3: *"An automated, unsupervised detection. Distinct from a human tag."* Document 03 §6's catalog row, as corrected: *"installed item, window, detector version, score, channels implicated, origin (`enterprise` | `edge`)."*

```sql
CREATE TABLE meta.detected_anomaly (
  candidate_id       uuid        PRIMARY KEY,
  installed_item_id  uuid        NOT NULL,
  asset_id           uuid        NOT NULL,
  mission_id         uuid        NULL,
  window_start       timestamptz NOT NULL,        -- DATA time
  window_end         timestamptz NOT NULL,

  -- THE FIELD THE CORRECTED CATALOG ADDS
  origin             text        NOT NULL,        -- 'enterprise' | 'edge'
  producer_node      text        NOT NULL,        -- 'enterprise' | 'edge:<asset_id>'

  detector_key       text        NOT NULL,
  detector_version   text        NOT NULL,
  detector_artifact_digest bytea NULL,            -- NOT NULL for artifact-backed detectors (§7.3)
  detector_class     text        NOT NULL,        -- threshold | trending | residual |
                                                  -- multivariate | spectral | reconstruction
  score              double precision NOT NULL,
  score_scale        text        NOT NULL,        -- how to read `score`.  Never a bare number
  channels_implicated text[]     NOT NULL,
  indicators_implicated text[]   NOT NULL,
  evidence_ref       text        NOT NULL,        -- replay-source reference for PMA (§1.2)

  -- GROUPING.  Enterprise ADDS; it does not replace (§7.4)
  candidate_group_id uuid        NOT NULL,        -- near-duplicates linked, both origins retained
  superseded_by      uuid        NULL,            -- NEVER set by an enterprise pass over edge output

  -- Sensor-fault discrimination.  See §4.6 and 13 §9.6
  attributed_to      text        NOT NULL,        -- equipment | sensor | operating_condition |
                                                  -- unknown
  definition_state_seq bigint    NOT NULL,        -- knowledge_seq the detector ran under
  known_at_seq       bigint      NOT NULL,
  classification     jsonb       NOT NULL,

  CONSTRAINT anomaly_origin CHECK (origin IN ('enterprise','edge')),
  CONSTRAINT anomaly_origin_matches_node CHECK (
    (origin = 'enterprise' AND producer_node = 'enterprise') OR
    (origin = 'edge'       AND producer_node LIKE 'edge:%')
  ),
  CONSTRAINT anomaly_window CHECK (window_end > window_start)
);
CREATE INDEX anomaly_by_group ON meta.detected_anomaly (candidate_group_id);
CREATE INDEX anomaly_by_mission ON meta.detected_anomaly (mission_id, origin);
```

- **`anomaly_origin_matches_node` is a CHECK, not a convention.** An `origin = 'edge'` candidate emitted by the enterprise instance is a bug in the merge path, and it is exactly the bug that would let an enterprise recomputation launder itself as edge output and thereby appear to satisfy **D18** while having replaced the edge set.
- **`attributed_to = 'sensor'` exists because document 13 §9.6 requires it.** A stuck-at-value channel *"reports a plausible constant"* and is labeled a **sensor** fault in ground truth, *"never as equipment degradation — a model that predicts equipment failure from a dead sensor is making the error this case exists to expose."* A candidate whose only evidence is a stuck channel is raised with `attributed_to = 'sensor'`, is still surfaced (a dead sensor is a real maintenance finding), and is **excluded from the equipment-degradation candidate stream PMA ranks**.
- **`score_scale` accompanies every `score`.** A bare number from a threshold detector and a bare number from a reconstruction detector are not comparable, and the same reasoning document 03 §7.1 applies to `reference_class` applies here at smaller stakes.
- **`superseded_by` has one legal writer: a *later edge or enterprise pass over its own prior output*.** It is never set by an enterprise pass over edge candidates. §7.4 states the rule and §10.5 tests it.

### 3.8 `QualityAssessment` — an owned aggregate, not a decoration

Document 04 §3 lists "data quality assessments" in the ownership boundary. They are stored per batch (inline `quality` jsonb) and per `(asset, channel, day)` as a materialized projection served by `GET /quality`, because the operationally useful question is "which channels on this hull are lying to me" and that is not answerable from batch rows.

```
QualityAssessment {
  completeness, sample_count, expected_sample_count
  flag_counts { absent, clipped, stuck, implausible, imputed, duplicate, impulse }
  stuck_runs[]        { channel_key, from, to, held_value }
  clipped_fraction    per channel
  timebase { degraded: bool, dispersion_ms, step_occurred, inter_sample_interval_ms }
  mnar_indicator      # completeness correlated with indicator level; see 13 §9.11
  observation_state
}
```

`mnar_indicator` deserves a note. Document 13 §9.11 makes dropout probability *"correlated with the degradation state,"* which means *"missingness carries information about the label, so imputation choices change results and a complete-case analysis is biased."* This service cannot fix that, and must not try. It **measures and publishes** the correlation so a modeler can condition on it — which is why `completeness` appears on every feature in the §5.3 response rather than only in a diagnostics view.

---

## 4. The three ingest adapters

Document 04 §3's key decision, in full: *"Three ingest profiles, one storage model. Surface assets deliver near-continuous HM&E monitoring in the manner of ICAS. Submarines deliver bursts on reconnection with constrained egress and possible gaps of weeks. Unmanned vehicles deliver dense per-sortie dumps at sortie end. The design accommodates these as three ingest adapters over one canonical channel and sample model, rather than three storage designs. Data completeness is recorded per batch and per mission so that downstream consumers can distinguish 'no fault observed' from 'not observed.'"*

### 4.1 The pipeline is fixed; only the adapter varies

```
POST /telemetry-batches  ──▶  IngestPipeline.run(raw, ctx)
                                 │
   ┌─────────────────────────────┴──────────────────────────────┐
   │  1. adapter.accept(raw, ctx)        -> AcceptDecision       │  admission control
   │  2. adapter.frame(raw, ctx)         -> [FramedWindow]       │  batch boundaries
   │  3. adapter.decode(window, ctx)     -> [RawReading]         │  wire -> readings
   │  4. SHARED  ChannelMapper.map()     -> [CanonicalSample]    │  §4.5 — NOT the adapter's
   │  5. adapter.reduce(samples, ctx)    -> [CanonicalSample]    │  downsampling; identity for 2 of 3
   │  6. SHARED  QualityAssessor.assess() -> QualityAssessment   │  §4.6 — NOT the adapter's
   │  7. adapter.retain_raw(raw, ctx)    -> ObjectRef | None     │  object storage
   │  8. adapter.mission_hint(window)    -> MissionBoundaryHint  │  §4.7
   └─────────────────────────────┬──────────────────────────────┘
                                 │
   9.  ONE TRANSACTION:  insert ts.sample rows
                       + insert meta.telemetry_batch
                       + allocate knowledge_seq
                       + update mission_record completeness
                       + outbox.emit("fathom.telemetry.telemetry_batch.ingested")
```

**Steps 4 and 6 are shared and are not overridable.** That is the point of "one storage model": channel resolution and quality assessment must be identical across domains or the three profiles become three semantics. An adapter that needed its own mapper would be declaring that its samples mean something different, which is the outcome document 04 §3 rejects.

**Step 9 is one transaction, and `outbox.emit()` is inside it**, per document 11 §2.3's only sanctioned write shape. The batch, its samples, its knowledge-sequence allocation, and the event announcing it commit together or none of them do.

### 4.2 The exact interface each adapter implements

```python
# services/telemetry/src/fathom_telemetry/ingest/adapter.py
from typing import ClassVar, Protocol, Iterator

from fathom_schemas.identity import InstalledItemId, PositionId
from fathom_sync.clock import SourceTime          # NOT ORDERABLE — 11 §4.7


class DomainProfile(StrEnum):
    SURFACE     = "surface"
    SUBSURFACE  = "subsurface"
    UNMANNED    = "unmanned"


class SampleQuality(IntFlag):
    """Bitmask on ts.sample.sample_quality.  Every flag traces to a document 13 §9 stage."""
    OK          = 0
    ABSENT      = 1 << 0    # 13 §9.6 stage 5.  value IS NULL.  Never 0
    CLIPPED     = 1 << 1    # 13 §9.2 stage 1 — saturated against channel_definition.saturation_*
    STUCK       = 1 << 2    # 13 §9.6 stage 5 — plausible constant.  A SENSOR fault (§4.6)
    IMPLAUSIBLE = 1 << 3    # outside channel_definition.nominal_*
    IMPUTED     = 1 << 4    # filled by a definition's bounded missing_policy.  NEVER by ingest
    DUPLICATE   = 1 << 5    # 13 §9.7 stage 6 — deduplicated; the survivor is unflagged
    IMPULSE     = 1 << 6    # 13 §9.7 stage 6 — flagged, NOT removed (§4.6)
    TIMEBASE    = 1 << 7    # 13 §9.8 stage 7 — data_time is not trustworthy to sample precision


class CanonicalSample(NamedTuple):
    """THE sample model.  There is no second one.  [04 §3]"""
    channel_key: str
    channel_version: int
    asset_id: AssetId
    position_id: PositionId                  # where the transducer is
    installed_item_id: InstalledItemId | None  # resolved at DATA time; None => unattributed
    data_time: datetime                      # the source's own timebase, UTC, RFC 3339
    value: float | None                      # None => ABSENT
    sample_quality: SampleQuality
    source_tag: str
    mapping_version: int


class IngestAdapter(Protocol):
    """One implementation per domain profile.  THREE, and there will not be a fourth
    without a document 04 §3 amendment."""

    profile: ClassVar[DomainProfile]
    adapter_key: ClassVar[str]
    adapter_version: ClassVar[str]

    # --- admission -------------------------------------------------------------
    def accept(self, raw: RawPayload, ctx: IngestContext) -> AcceptDecision:
        """Admission control BEFORE any decode.  Returns Accept | Defer | Reject.

        Defer carries a monotonic retry-after (11 §4.6) and is how back-pressure is
        expressed; Reject carries an RFC 9457 problem type.  Reject NEVER discards:
        the payload is written to the quarantine object store first.  A rejected
        payload is a lost observation, and a lost observation is unrecoverable.
        """

    # --- framing ---------------------------------------------------------------
    def frame(self, raw: RawPayload, ctx: IngestContext) -> Iterator[FramedWindow]:
        """Split the payload into batch-sized windows.  A FramedWindow carries
        data_time_from/to, the source's own batch reference where one exists, and
        the source's monotonic_seq where one exists.  Framing is where the three
        profiles differ most (§4.3-§4.5)."""

    # --- decode ----------------------------------------------------------------
    def decode(self, window: FramedWindow, ctx: IngestContext) -> Iterator[RawReading]:
        """Wire format -> (source_tag, source_time, raw_value).  NO channel
        resolution here — that is the shared mapper's job and must not vary."""

    # --- reduction (downsampling) ----------------------------------------------
    def reduce(self, samples: Iterator[CanonicalSample],
               ctx: IngestContext) -> Iterator[CanonicalSample]:
        """Identity for surface and subsurface.  Unmanned downsamples 10 Hz -> 1 Hz.

        A NON-IDENTITY reduce() MUST declare ctx.reduction_version, and that version
        is registered in the knowledge log (§3.0), because DOWNSAMPLING IS A
        DEFINITION-TIME ACT.  See §4.4.
        """

    # --- raw retention ---------------------------------------------------------
    def retain_raw(self, raw: RawPayload, ctx: IngestContext) -> ObjectRef | None:
        """Write the raw payload to object storage where the profile requires it.
        Returns the reference recorded on telemetry_batch.raw_payload_ref."""

    # --- mission boundaries ----------------------------------------------------
    def mission_hint(self, window: FramedWindow,
                     ctx: IngestContext) -> MissionBoundaryHint | None:
        """A hint, never a decision.  The shared MissionBoundaryDetector (§4.7)
        reconciles hints against reported boundaries."""
```

Two things the interface deliberately does **not** contain:

- **No `map()` and no `assess()`.** Steps 4 and 6 are shared functions the pipeline calls, not Protocol members, so an adapter cannot override them. Making them Protocol members would make overriding them look sanctioned.
- **No `now()`, no clock, and no ordering.** `IngestContext` supplies `monotonic_seq` allocation (11 §4.3), the `SyncQuality` cache snapshot (11 §4.6), and `MonotonicDeadline` for any timeout. An adapter that reads a wall clock fails document 11 §11.5's static gate 5.

### 4.3 Surface — near-continuous

Rate, from document 06 §7: **40 spotlight channels/asset at 1 Hz plus 200 routine channels/asset at 1/minute.**

| Step | Behavior |
|---|---|
| `accept` | Streaming micro-batches over the API. Admits on `Idempotency-Key`; `Defer` with a monotonic retry-after when the hypertable write queue exceeds its bound |
| `frame` | Fixed 60-second **data-time** windows with a declared late-arrival grace (default 300 s). A reading arriving after the grace opens a *new* batch for the window it belongs to rather than mutating a closed batch — batches are append-only (03 §11) |
| `decode` | Per-source codec; no ICAS-specific format is assumed (§2.5) |
| `reduce` | **Identity.** 1 Hz is the storage rate |
| `retain_raw` | `None`. The samples *are* the record; retaining the wire form would double storage for no replay benefit |
| `mission_hint` | Underway indication from bindings whose `required_for` includes the underway indicator set; reconciled against reported boundaries (§4.7) |
| `observation_state` | `observed` when completeness ≥ the binding's expectation; `partially_observed` on gaps within an active window; `not_observed` outside active windows (13 §7.5) |

The one non-obvious rule: **a surface channel outside an active window is not incomplete, it is inactive.** Document 13 §7.5 gates sample generation on asset operating, equipment energized, and an active window, and emits 1-minute aggregates otherwise. `expected_sample_count` is computed against the *active* window, not against wall time, or every in-port day reports 100% data loss.

### 4.4 Unmanned — dense per-sortie, and the reduction-version trap

Rate, from document 06 §7: **100 channels at 10 Hz per sortie, downsampled at ingest to 1 Hz for storage, raw retained per sortie in object storage.**

| Step | Behavior |
|---|---|
| `accept` | Whole-sortie dump at sortie end. Chunked, resumable, `Idempotency-Key` on the sortie |
| `frame` | One batch per `(sortie, channel group)`; the sortie is the natural mission (§4.7) — a sortie *is* a mission per 03 §3.2 |
| `decode` | Per-vehicle codec |
| `reduce` | **10 Hz → 1 Hz. This is the load-bearing step.** See below |
| `retain_raw` | **Required.** The 10 Hz object is written to object storage per document 13 §14.1 (*"per-sortie objects in object storage, never as rows"*) and referenced from the batch, so full-rate analysis and PMA evidence remain possible |
| `mission_hint` | Sortie boundaries are reported by the vehicle; `boundary_source = 'reported'` is the normal case |

**`DECISION` — the downsample reduction is a declared, versioned artifact registered in the knowledge log, and every sample carries its `reduction_version` through the batch.**

The 1 Hz sample emitted from ten 10 Hz readings is not one of them; it is a statistic. The reduction therefore emits a **fixed tuple per second**, not a single mean:

```
reduce_10hz_to_1hz(readings) -> mean, min, max, count, rms, peak
```

each landing in its own canonical channel (`<channel_key>.mean`, `.min`, `.max`, `.rms`, `.peak`), all bound in the registry, all with `sample_semantics` declaring which they are. A single mean destroys exactly the information vibration analysis needs, and document 13 §9.2 warns that clipped peaks are common — a mean hides both the clipping and the peak.

> **Why the version matters, and why this is a D22 catch rather than an implementation detail.** Changing the downsampler changes the value of every historical 1 Hz sample it produced. If the reduction is unversioned, a downsampler improvement in 2026 silently rewrites the meaning of 2025's unmanned telemetry, and a model trained `as_of=2025-06-01` receives values a 2026 engineer produced. That is **precisely D22's failure mode arriving through a path neither the finding nor document 04 §3 names**, because the finding names definitions and mappings. `reduction_version` is registered in the knowledge log (§3.0), is folded into `channel_registry_version` (§3.1.5), and is therefore fenced by `as_known_at` like everything else. A reduction change triggers recomputation from the retained raw objects — which is the second reason `retain_raw` is required.

### 4.5 Subsurface — burst on reconnect, and the shared channel mapper

Rate, from document 06 §7: **150 channels/asset at 1/minute, transmitted in burst on reconnect.** Volume, from document 13 §15.3: six weeks × 150 channels × 1/minute is *"on the order of 9×10⁶ samples arriving in one burst."*

| Step | Behavior |
|---|---|
| `accept` | Chunked, resumable, idempotent on `event_id` per document 11 §9.3's resume-from-offset. **Priority class 4** — bulk telemetry drains last and is interruptible, so it cannot starve the label stream. Admits under an explicit backlog budget; `Defer` with a monotonic retry-after on breach |
| `frame` | **Preserves the ship's own batch boundaries and its own `monotonic_seq`.** The submarine framed these batches; re-framing them ashore would break the gap-free loss detection document 11 §4.3 provides |
| `decode` | Per-source codec |
| `reduce` | **Identity.** 1/minute is already the storage rate |
| `retain_raw` | Optional per deployment; the compressed burst is retained where egress budget permits |
| `mission_hint` | Patrol boundaries reported by the ship, reconciled; a patrol is one mission |
| `observation_state` | **The six weeks before reconnect are `not_observed`, not `completeness = 0`** |

Three properties of this adapter carry the most risk in the whole ingest surface.

**(a) `data_time` is weeks behind `known_at`, and both are recorded.** Document 03 §5.4: *"`occurred_at` and `recorded_at` are distinct because they diverge materially here: a mission anomaly occurred at sea and was recorded when the ship reconnected."* Document 13 §14.2 makes the divergence a generated feature *"because a corpus where the two are always equal cannot detect that error."* This service records `data_time` from the ship's timebase and allocates `known_at_seq` at shore admission, and §5.5 is where that pays.

**(b) The burst arrives across a mandated backward clock step.** Document 13 §15.3 generates it deliberately: *"A backward wall-clock step (STIG `makestep 1 -1`), `step_occurred = true`, and two writes from one process carrying inverted `source_time`. Any consumer that arbitrates on `source_time` produces the wrong answer, which is the point."* Ordering within the burst comes from `(producer_node, monotonic_seq)`; `source_time` is a `SourceTime` whose comparison operators raise (11 §4.7). Where `sync_quality.dispersion_ms` exceeds the inter-sample interval, the batch is stamped `timebase_degraded = true`, every sample in it carries `SampleQuality.TIMEBASE`, and indicator windows over the affected range are widened and flagged rather than silently computed on untrustworthy timestamps.

**(c) Never `X-Backfill: true`.** Document 11 §9.3: *"Edge records are live facts arriving late, not replay. They must fire their normal side effects ashore."* A six-week-old patrol's telemetry is a first emission of a real fact. Marking it `replay: true` would suppress the notification, candidate, and mission-review generation that the patrol is supposed to trigger — which is exactly the outcome **D18** describes from the other direction.

#### The shared channel mapper (step 4)

```python
def map(readings: Iterator[RawReading], ctx: IngestContext) -> Iterator[CanonicalSample]:
    for r in readings:
        m = registry.resolve_mapping(
            asset_id=ctx.asset_id, source_system=ctx.source_system, source_tag=r.source_tag,
            at_data_time=r.source_time,             # DATA time: which mapping APPLIES
            at_knowledge_seq=ctx.knowledge_seq,     # KNOWLEDGE time: which mapping we BELIEVE
        )
        if m is None:
            quarantine.record_unmapped_tag(r, ctx)   # NEVER dropped.  Surfaced on GET /quality
            continue

        if m.attachment == "position_wired":
            # THE anti-inherited-degradation resolution.  Registry configuration AT DATA TIME.
            item = config_read_model.installed_item_at(m.position_id, at=r.source_time)
            installed_item_id = item.installed_item_id if item else None   # None, never a guess
            position_id = m.position_id
        else:                                        # item_integral
            installed_item_id = m.installed_item_id
            position_id = config_read_model.position_of(m.installed_item_id, at=r.source_time)

        yield CanonicalSample(
            channel_key=m.channel_key, channel_version=m.channel_version,
            asset_id=ctx.asset_id, position_id=position_id,
            installed_item_id=identity_alias.resolve(installed_item_id),   # 11 §8.4
            data_time=r.source_time,
            value=transform.apply(m.transform, r.raw_value),   # declarative; §3.1.3
            sample_quality=SampleQuality.OK,                   # assessed at step 6, not here
            source_tag=r.source_tag, mapping_version=m.mapping_version,
        )
```

Four rules:

1. **`resolve_mapping` takes both a data time and a knowledge sequence.** A single-argument resolver is the D22 leak in the mapping path.
2. **An unmapped tag is quarantined, never dropped.** A dropped reading is an unrecoverable lost observation, and the tag is almost always a mapping gap rather than garbage — it is the integration surface's normal state early in a deployment.
3. **`installed_item_id` comes from the Registry read model at the *sample's* data time.** Not "current configuration." That is what makes replacement-at-sea correct.
4. **`identity_alias.resolve()` from document 11 §8.4 wraps the result**, so a sample recorded against a provisional identity remains queryable by both the provisional and the canonical id after the Registry adjudicates.

### 4.6 The shared quality assessor (step 6) — never silently repair

**One rule governs this entire component: the ingest pipeline records, flags, and quantifies. It does not repair.** Repair — interpolation, outlier removal, robust centering — is an *indicator-definition* decision (§3.4.1's `missing_policy` and `outlier_policy`), is therefore versioned, and is therefore visible to `as_known_at`. Repair performed at ingest is unversioned, invisible, and irreversible.

> **Why this matters.** A repair at ingest is a definition-time act performed outside the definition-time bookkeeping. It changes the meaning of the stored sample with no version, so a recomputation cannot undo it and `as_known_at` cannot fence it. Every repair the pipeline is tempted to perform is available as a versioned definition operator; taking it at ingest converts a reviewable, replayable decision into a silent one.

How each of document 13 §9's ten stages is handled:

| Stage (13 §9) | Assessor behavior |
|---|---|
| **1 — sensor transfer**: bias, sensitivity, clipping, quantization | Saturation against `channel_definition.saturation_*` → `CLIPPED`; per-channel `clipped_fraction` reported. Bias and sensitivity are **not** corrected at ingest: they are persistent per-channel offsets and a *"real, learnable nuisance"* (13 §9.2), and correcting them would require a calibration model that is a definition, not a pipeline step |
| **2 — stationary + pink noise** | Nothing. Noise is signal at this layer. Filtering is a definition operator |
| **3 — drift with recalibration steps** | PMS calibration events are recorded against the channel; a step at a recorded calibration is **not** an anomaly and is excluded from step-based detection (§7.2). Document 13 §9.4: *"a step at recalibration that is not a physical change. Any detector that treats steps as events must contend with recalibration steps"* |
| **4 — operating-condition confounding** | Operating-condition covariates are ingested **as ordinary channels** and exposed on `/features`, so normalization is possible for a definition that does the work (13 §9.5: *"emitted as data"*). The assessor does not normalize |
| **5 — dropout, gaps, stuck-at-value** | Per-sample absence → `ABSENT`, `value IS NULL`. Burst outages → `gap_intervals` on the mission. **Stuck-at-value → `STUCK`, and the run is recorded in `stuck_runs`** with its held value; a candidate resting on it is `attributed_to = 'sensor'` (§3.7). Domain-structural absence → `observation_state = 'not_observed'` |
| **6 — impulses, frozen runs, duplicates** | Impulses → `IMPULSE`, **flagged and retained**; removal is `outlier_policy`. Duplicates → deduplicated within a batch on `(channel_key, data_time, source_tag)` and across batches on `(producer_node, monotonic_seq)`; the survivor is unflagged, the discard is counted |
| **7 — timebase corruption** | `sync_quality` copied to the batch and retained permanently (11 §10.5). `dispersion_ms` > inter-sample interval → `timebase_degraded` + `TIMEBASE` on every sample. `step_occurred` recorded. **Ordering never consults `source_time`** |
| **8 — cross-channel structure, decoys** | Common-mode excursions detected across channels sharing an acquisition unit and reported; a candidate whose implicated channels are all common-mode is `attributed_to = 'operating_condition'`. **Decoy channels are not suppressed** (§3.1.2) |
| **9 — label and record corruption** | Not this service's stream — maintenance records are Scheduling's. But **duplicate 2-Kilos and wrong-item attribution reach this service through `installed_item.*`**, so the mapper's `identity_alias.resolve()` and the `installed_item_id IS NULL` path are the defenses |
| **10 — missing not at random** | `mnar_indicator` computed and published (§3.8). `completeness` is on **every feature** in the §5.3 response, not only in diagnostics, so a modeler can condition on it |

### 4.7 Mission boundary detection

`MissionBoundaryDetector` is shared, and it **reconciles** rather than choosing, which is document 04 §3's open question answered:

```
1. Reported boundary, where the ship or vehicle reports one     -> candidate A
2. Inferred boundary, from underway-indication channels and
   the onset/cessation of sample delivery                        -> candidate B
3. Reconcile:
     A only            -> boundary_source = 'reported'
     B only            -> boundary_source = 'inferred'
     A and B agree     -> 'reported',   evidence records the agreement
     A and B disagree  -> 'reconciled', A wins, and BOTH are recorded in
                          boundary_evidence with the delta.  A disagreement is
                          never averaged and never silently resolved
4. On mission end:  compute completeness over the bindings in force across the
   mission, enumerate gap_intervals, set observation_state, emit mission.completed
```

**Reported wins on disagreement, and the disagreement is retained.** A ship's report of when it got underway is an operational fact; telemetry onset is a proxy. But an unrecorded disagreement is exactly the kind of quiet data-quality signal that would otherwise be discovered two years later, so it is retained and surfaced on `GET /quality`.

---

## 5. The bitemporal feature-serving API

**This is the single most important operation in this service.** Everything in §3 and §4 exists so that this query can be answered correctly.

Document 04 §3's statement of the requirement: *"Point-in-time correct feature serving. The feature read API accepts an as-of timestamp and returns only what was knowable at that instant. This is the single mechanism preventing target leakage, which is the most common cause of predictive-maintenance programs that report strong offline metrics and fail in the field. The obligation is enforced in the API rather than trusted to modelers."*

Finding **D22** establishes that an as-of timestamp alone does not achieve it.

### 5.1 The exact operation

```
GET /api/v1/telemetry/features
      ?installed_item_id={uuid}          # REQUIRED. The PHYSICAL ITEM (03 §3.3). Repeatable
      &feature_set={string}              # REQUIRED. Selects the indicator set and its version
      &as_of={rfc3339|latest}            # REQUIRED, no default.      DATA time
      &as_known_at={rfc3339|latest}      # REQUIRED, no default.      DEFINITION time  [D22]
      &from={rfc3339}                    # optional window floor on window_start
      &window_alignment={calendar|mission_anchored|event_anchored}   # optional filter
      &resolution_token={opaque}         # optional. Replay an EXACT prior resolution (§5.6)
      &limit={int}&cursor={opaque}       # 03 §4 cursor pagination
```

```python
@router.get(
    "/features",
    response_model=Page[FeatureVector],
    **operation(substitution=Substitution.REQUIRED,     # 03 §4.1
                side_effects=SideEffects.NONE,
                agent_eligible=True),                    # a read; 03 §8.1 permits it
)
async def get_features(
    installed_item_id: Annotated[list[InstalledItemId], Query(min_length=1)],
    feature_set: str,
    as_of: DataTimeSelector,            # RFC 3339 with offset, or the literal "latest"
    as_known_at: KnowledgeTimeSelector, # RFC 3339 with offset, or the literal "latest"
    ...
) -> Page[FeatureVector]: ...
```

**`DECISION` — both parameters are required, with no default, and `latest` is an explicit literal.**

Justification. A default on `as_known_at` is the leak. If omitting it means "latest," then every modeler who does not know about D22 — which is every modeler who has not read finding D22 — writes a leaking query and gets a plausible answer. Document 04 §3 is explicit that *"the obligation is enforced in the API rather than trusted to modelers,"* and a defaulted parameter is trust dressed as a signature. Making `latest` an explicit literal means:

- Operational serving (Fleet Status dashboards, live indicator views) writes `as_known_at=latest` and is unaffected.
- Training-set assembly cannot reach `latest` by accident.
- `as_known_at=latest` appears in the access log, in the audit record, and in the response's `resolution` block, so a leaking training run is **discoverable after the fact** rather than invisible.

The response additionally carries `definition_time_unconstrained: true` and the header `X-Feature-Definition-Time: unconstrained` whenever `as_known_at=latest`, for the same reason.

### 5.2 The query logic — resolving both constraints simultaneously

Three fences must hold at once. They are independent, and dropping any one of them reopens the leak.

| Fence | Constrains | Column |
|---|---|---|
| **F1 — data time** | Only observations whose window had closed by `as_of` | `indicator_value.window_end <= :as_of` |
| **F2 — definition time** | Only indicator definitions **authored** by `as_known_at` | `indicator_definition.published_seq <= :resolved_seq` |
| **F3 — knowledge time on the value** | Only values that had been **computed and admitted** by `as_known_at` | `indicator_value.known_at_seq <= :resolved_seq` |

F2 without F3 leaks: the definition existed at `as_known_at`, but a *later* recomputation under that same definition may have consumed samples that arrived after `as_known_at` — late-arriving subsurface burst data whose `data_time` is inside `as_of` but whose admission is after `as_known_at`. F3 without F2 leaks: the value was computed before `as_known_at`, but a definition authored afterward may have produced a newer value for the same window, and taking the newest value for the window would pick it.

```sql
-- services/telemetry/src/fathom_telemetry/repositories/features.py
--
-- POINT-IN-TIME + DEFINITION-TIME RESOLUTION.  DO NOT "SIMPLIFY" THIS.
--   [document 04 §3 · document 05 finding D22 · document 03 §5.4]
--
-- Three fences, all required:
--   F1  window_end      <= :as_of         -- DATA time
--   F2  published_seq   <= :resolved_seq  -- DEFINITION time (which definition)
--   F3  known_at_seq    <= :resolved_seq  -- KNOWLEDGE time (which computation of it)
--
-- Removing F2 gives document 04 §3's original design, which D22 found leaky.
-- Removing F3 lets late-arriving data leak through a definition that predates it.
-- Removing F1 is not point-in-time correctness at all.
--
WITH
-- ── Step 0.  Resolve as_known_at to ONE integer.  §5.4 explains why this is the
--             only timestamp comparison in the whole resolver.
knowledge AS (
  SELECT coalesce(max(knowledge_seq), 0) AS resolved_seq
    FROM meta.knowledge_log
   WHERE producer_node = :this_node                -- §5.5: THIS node's knowledge
     AND known_at     <= :as_known_at              -- the single timestamp comparison
),

-- ── Step 1.  F2 — DEFINITION TIME.  The definition versions IN FORCE at as_known_at.
--             A definition published later is invisible; a definition superseded
--             later is still the one in force, and that is the point.
defs AS (
  SELECT d.indicator_key, d.definition_version, d.spec_sha256, d.unit_code,
         d.min_completeness, d.published_seq, d.authored_by, d.feature_set_version
    FROM meta.indicator_definition d
   CROSS JOIN knowledge k
   WHERE d.feature_set    = :feature_set
     AND d.review_state  IN ('published', 'superseded')
     AND d.published_seq <= k.resolved_seq                        -- F2
     AND (d.superseded_seq IS NULL OR d.superseded_seq > k.resolved_seq)
),

-- ── Step 2.  F1 + F3, and pick ONE value per (item, indicator, window).
--             Ordering is by known_at_seq then value_seq — both monotonic integers
--             from the sequencer of document 11 §4.3.  NEVER by a timestamp.
candidates AS (
  SELECT v.installed_item_id, v.indicator_key, v.definition_version,
         v.window_start, v.window_end, v.value, v.unit_code,
         v.channel_registry_version, v.contributing_channels, v.contributing_batches,
         v.sample_count, v.expected_sample_count, v.completeness, v.quality_flags,
         v.missing_policy_applied, v.outlier_policy_applied,
         v.known_at_seq, v.value_seq, v.producer_node,
         d.min_completeness, d.authored_by AS definition_authored_by,
         row_number() OVER (
           PARTITION BY v.installed_item_id, v.indicator_key,
                        v.window_start, v.window_end
           ORDER BY v.known_at_seq DESC, v.value_seq DESC     -- integers only.  [D29]
         ) AS rn
    FROM ts.indicator_value v
    JOIN defs d
      ON  d.indicator_key      = v.indicator_key
      AND d.definition_version = v.definition_version          -- F2, joined not filtered
   CROSS JOIN knowledge k
   WHERE v.installed_item_id = ANY(:installed_item_ids)
     AND v.window_end       <= :as_of                          -- F1
     AND v.window_start     >= coalesce(:from, '-infinity'::timestamptz)
     AND v.known_at_seq     <= k.resolved_seq                  -- F3
  -- NOTE: v.is_current is NOT referenced.  It is a latest-serving convenience and
  -- reading it here would collapse the bitemporal history to the present.  §6.5.
)

-- ── Step 3.  Emit, and suppress below the definition's own completeness floor.
--             A suppressed feature is reported in coverage.missing_indicators with
--             reason 'insufficient_completeness'.  It is NEVER emitted as NULL.
SELECT * FROM candidates
 WHERE rn = 1
   AND completeness >= min_completeness
 ORDER BY installed_item_id, indicator_key, window_end
 LIMIT :limit;
```

And the second query, run in the same transaction and the same snapshot, which is what makes absence explicit:

```sql
-- ── Step 4.  COVERAGE.  Which requested indicators produced nothing, and WHY.
--             Absence with a reason is the difference between "no data" and
--             "silently zero".  A modeler who reads NULL as 0 has been misled by
--             the API, not by their own carelessness.
SELECT d.indicator_key,
       CASE
         WHEN NOT EXISTS (SELECT 1 FROM ts.indicator_value v
                           WHERE v.indicator_key = d.indicator_key
                             AND v.installed_item_id = ANY(:installed_item_ids))
              THEN 'no_data'
         WHEN NOT EXISTS (SELECT 1 FROM candidates c
                           WHERE c.indicator_key = d.indicator_key)
              THEN 'no_value_within_fences'
         ELSE 'insufficient_completeness'
       END AS reason
  FROM defs d
 WHERE d.indicator_key NOT IN (SELECT indicator_key FROM candidates WHERE rn = 1)
UNION ALL
-- Indicators in the feature set that did not YET EXIST at as_known_at.
SELECT d.indicator_key, 'not_defined_at_as_known_at'
  FROM meta.indicator_definition d CROSS JOIN knowledge k
 WHERE d.feature_set = :feature_set
   AND d.review_state IN ('published','superseded')
   AND d.published_seq > k.resolved_seq
   AND d.indicator_key NOT IN (SELECT indicator_key FROM defs);
```

**`not_defined_at_as_known_at` is the row that makes D22's remedy honest.** An indicator authored after `as_known_at` is not missing data — it is a feature that did not exist in the world at the moment the model is pretending to be trained. Returning it as absent-with-that-reason lets a modeler see the shape of their own knowledge horizon. Returning it as `NULL` would invite imputation of a feature that had not been invented.

### 5.3 The response

```
FeatureVectorPage {
  items[] FeatureVector, next_cursor
}

FeatureVector {
  installed_item_id
  feature_set, feature_set_version
  as_of, as_known_at                      # echoed exactly as requested
  definition_time_unconstrained            # true iff as_known_at=latest.  §5.1

  resolution {                             # PROVENANCE.  03 §15.9 obligation 9
    resolved_knowledge_seq                 # the integer everything was fenced on
    resolved_at                            # this node's known_at for that seq (display)
    producer_node                          # WHOSE knowledge.  §5.5
    channel_registry_version               # §3.1.5
    taxonomy_version                       # 03 §14 — every label carries it
    indicator_definitions[] {
      indicator_key, definition_version, spec_sha256, published_seq,
      authored_by, authored_rationale
    }
    resolution_token                       # opaque, replayable.  §5.6
  }

  features[] {
    indicator_key, window_start, window_end, value, unit_code
    definition_version, channel_registry_version
    quality {
      completeness, sample_count, expected_sample_count
      flags[]                              # ABSENT|CLIPPED|STUCK|IMPLAUSIBLE|IMPUTED|
                                           # DUPLICATE|IMPULSE|TIMEBASE
      missing_policy_applied, outlier_policy_applied
    }
    provenance {
      contributing_channels[], contributing_batches[]
      known_at_seq, value_seq, producer_node    # 'enterprise' or 'edge:<asset_id>'
    }
  }

  coverage {                               # ABSENCE IS EXPLICIT.  Never implied by omission
    missing_indicators[] { indicator_key, reason }
      # not_defined_at_as_known_at | no_data | no_value_within_fences |
      # insufficient_completeness
    data_time_gaps[]     { from, to, cause, observation_state }
    mnar_indicator                         # §3.8 / 13 §9.11
  }

  classification                           # 03 §7.3, with inherited_from as the union
                                           # of every contributing input's label  [D13]
}
```

Three response properties that are obligations, not conveniences:

- **`quality.completeness` on every feature.** Document 13 §9.11 makes missingness informative about the label. A feature server that hides completeness has removed the covariate a modeler needs to handle MNAR at all.
- **`classification.inherited_from` is the union of contributing inputs' labels**, per document 03 §7.3 and obligation §15.4. A feature is a derived value; document 09 §9.4 item 23 makes publishing one without the union a defect.
- **`provenance.producer_node`** tells a modeler that a given value was computed afloat rather than ashore. Under `RECOMPUTABLE_SUPERSEDE` (§6.5) an enterprise recomputation of the same window under the same definition will later win, and a training set assembled before that recomputation legitimately contains edge values. Hiding which is which would make the difference undebuggable.

### 5.4 The one timestamp comparison, and why it does not violate D29

Step 0 compares `:as_known_at` against `meta.knowledge_log.known_at`. Document 11 §4.7's prohibition is absolute — *"NO function in this library ever compares two `source_time` values to decide precedence"* — and document 09 §9.2 item 7 forbids letting a wall clock arbitrate anything. This comparison is licensed, and the licence is narrow and must be understood rather than assumed:

1. **It arbitrates nothing between nodes.** It is a query predicate translating a caller-supplied instant into a position in a single, local, gap-free integer sequence. No merge, no precedence, no last-writer-wins.
2. **`known_at` is written by exactly one clock.** It is set by the admitting node — like `clock.ingest_time` (03 §5.4) and unlike `source_time` — and `meta.knowledge_log` is per-`producer_node`. There is one writer and one clock per row set.
3. **`known_at` is monotonically non-decreasing with `knowledge_seq` by construction.** It is derived from document 11 §4.4's `_guarded_physical_ms()` — a monotonic-anchored estimate, never a raw `CLOCK_REALTIME` read — so a STIG backward step cannot make the log non-monotonic. The `UNIQUE (known_at, knowledge_seq)` index makes a regression a constraint violation rather than a silent corruption.
4. **The comparison is against `known_at`, never against `source_time`, `occurred_at`, `recorded_at`, or `computed_at`.** `SourceTime` still raises on comparison (11 §4.7), and document 11 §11.5's static gate 4 still holds across this service.

**Definition-time authoring is enterprise-only precisely so this holds** (§6.6). If the edge could author definitions, the knowledge log would have two writers with two clocks and the resolution would be a cross-node timestamp comparison — which is D29 exactly. The edge's read-only definition registry is not a convenience; it is what keeps this comparison single-clocked.

### 5.5 Edge knowledge versus enterprise knowledge — where the two hardest findings meet

`meta.knowledge_log` is per `producer_node`, and `/features` resolves against **the serving node's own knowledge sequence**. The consequence is the sharpest property in this document:

> **An edge-computed indicator value becomes knowable *ashore* only when the shore ingress admits it.**

Concretely, following document 06 §4's scripted six-week SSN disconnection:

| Day | Event | `knowledge_seq` allocated | Visible to an enterprise `/features` query at `as_known_at`… |
|---|---|---|---|
| 0 | Disconnect | — | — |
| 9 | Edge computes an indicator over a window ending day 9 | **On the edge**, seq E-1041 | Not at all. The enterprise has never heard of it |
| 20 | Edge detector raises a candidate from it | On the edge, seq E-1102 | Not at all |
| 42 | Reconnect; coordinator drains (11 §9.3, priority class 3 then 4) | **Ashore**, seq S-88417 | day ≥ 42 only |
| 43 | Enterprise recomputes the same window under its full ensemble | Ashore, seq S-88602 | day ≥ 43 |

A model trained with `as_of = day 30, as_known_at = day 30` sees **neither** the edge value nor the enterprise recomputation, even though the edge value's `window_end` is day 9 and therefore satisfies F1. That is correct: on day 30 the enterprise did not know it. A model trained with `as_of = day 30, as_known_at = day 50` sees the enterprise recomputation, because by day 50 it did.

> **Why this matters.** Document 03 §5.4 warns that *"a mission anomaly occurred at sea and was recorded when the ship reconnected"* and that *"feature computation must not use `occurred_at` for any value authored with hindsight."* The subsurface profile makes that divergence six weeks wide (06 §7, 13 §15.3) — the largest data-time-to-knowledge-time gap in the system. **The submarine is therefore not an awkward special case for D22; it is the case that makes D22 concrete and testable.** Any implementation that fenced only on data time would hand a model trained "as of day 30" the results of a detector ensemble that ran on day 43, and offline metrics would be excellent. §10.2's `test_d22_edge_values_not_knowable_before_admission` is the regression test, and it is mandatory.

A corollary worth stating because it will otherwise be discovered as a bug: **the edge's own `/features` responses are resolved against the edge's sequence**, so an edge detector on day 20 correctly sees the day-9 edge value. The two nodes give different, and both correct, answers to the same question. `resolution.producer_node` in the response is what makes that legible.

### 5.6 `resolution_token` — replayability, and the mechanism the leakage test uses

Every response carries an opaque `resolution_token` encoding, signed, exactly what was resolved:

```
resolution_token := base64url(sign(
    producer_node, resolved_knowledge_seq, as_of, feature_set, feature_set_version,
    channel_registry_version, taxonomy_version,
    sha256(sorted[(indicator_key, definition_version, spec_sha256)])
))
```

Passing it back as `?resolution_token=` **replaces** `as_known_at` resolution with the encoded state and returns byte-identical features, or fails with `409` `urn:fathom:problem:telemetry:resolution-unreproducible` if any encoded input no longer exists (a crypto-shredded classification key, a purged retention tier — 03 §13). Failing loudly is the requirement; silently resolving to something near-enough would make a training set irreproducible while appearing to reproduce.

Two uses:

- **`POST /features/batch` (§9.2) resolves once and stamps every item with one token**, so an entire training set shares a single knowledge state. Assembling a training set item-by-item across a definition publication would otherwise produce a set that is internally inconsistent in exactly the way D22 describes — some rows pre-definition, some post.
- **§10.2's leakage test asserts token equality**, which is a stronger assertion than value equality: two runs can agree on values by luck and disagree on what they resolved.

### 5.7 Refusals

All RFC 9457 (03 §4, 09 §5.2), all with `type` declared in `schemas/problems.py`:

| Condition | Status | `type` |
|---|---|---|
| `as_of` or `as_known_at` absent | 400 | `urn:fathom:problem:telemetry:time-selector-required` |
| `as_known_at < as_of` (both explicit) | 422 | `urn:fathom:problem:telemetry:knowledge-precedes-data` |
| `as_known_at` in the future | 422 | `urn:fathom:problem:telemetry:knowledge-time-in-future` |
| `as_known_at` before the earliest `knowledge_log` entry | 422 | `urn:fathom:problem:telemetry:knowledge-time-before-epoch` |
| `feature_set` unknown at the resolved seq | 404 | `urn:fathom:problem:telemetry:feature-set-not-defined` |
| `resolution_token` no longer reproducible | 409 | `urn:fathom:problem:telemetry:resolution-unreproducible` |
| `installed_item_id` resolves to a provisional identity still unadjudicated | 200 + marker | `identity_provisional: true` on the vector (11 §8.2). **Not an error** |

`as_known_at < as_of` is a 422 rather than a warning because it is incoherent: it asks for data up to a time later than the knowledge horizon, which is the leak stated as a request. Extension members carry the two values so a caller does not parse `detail` (03 §4).

### 5.8 `/health-indicators` must take `as_known_at` too

Document 04 §3 lists `GET /health-indicators?installed_item_id=&from=&to=&as_of=` — with `as_of` and **no** `as_known_at`.

**`DECISION` — `as_known_at` is added to `/health-indicators` and is required there on the same terms as on `/features`.** Justification: document 04 §1 states that where it and document 03 conflict, *"document 03 prevails and this document is in error,"* and D22's disposition is FIX. A leak-free `/features` beside a leak-prone `/health-indicators` over the same underlying `ts.indicator_value` table is not a partial remedy; it is a remedy plus a bypass, and the bypass is the more convenient operation. The two operations differ only in shaping — `/health-indicators` returns a per-indicator time series, `/features` returns per-item vectors — and both resolve through the identical §5.2 predicate. Recorded in §15 as an extension of document 04 §3's signature.

---

## 6. Indicator definition versioning and recomputation

Document 04 §3: *"Health indicators are deterministic, versioned, and replayable — not models. Indicator computation is feature engineering: filtering, aggregation, spectral features, thermodynamic derivations. Keeping it deterministic and versioned means indicators can be recomputed over history when a definition improves, which is a routine need and impossible if indicator logic lives inside model code."*

Recomputation over history is therefore a designed, routine operation — and it is exactly the operation D22 identifies as the leak. Both facts are true, and §5's fences are what make them compatible.

### 6.1 A definition change is a new version, never an edit

```
POST /indicator-definitions                     -> draft, definition_version = max + 1
POST /indicator-definitions/{key}/{ver}/publish -> allocates knowledge_seq; sets published_seq;
                                                   sets superseded_seq on the prior version;
                                                   REQUIRES authored_rationale
```

Rules, all enforced at the API boundary:

1. **A published definition version is immutable.** `spec`, `input_channels`, `window_seconds`, `min_completeness`, and `unit_code` cannot be altered after publication; `spec_sha256` is checked on every read of the row and a mismatch is an integrity incident. An edit is a new version.
2. **Publication is the act that advances `knowledge_seq`, and it is the only act that does.** Drafting does not. A definition in review is not knowledge.
3. **`authored_rationale` and `authored_by` are required at publication.** A definition change silently rewrites the meaning of every historical value computed under it; the rationale is what a reliability engineer reads two years later.
4. **Publication does not recompute.** It makes the definition available. Recomputation is a separate, explicit, auditable operation (§6.3). Coupling them would make a definition publication an unbounded compute job, and would make "publish but do not yet recompute" — the normal state during a staged rollout — unrepresentable.
5. **The prior version is retained forever with its `superseded_seq` set.** `superseded_seq` is what makes §5.2's F2 predicate work: *"the definition in force at `as_known_at`"* requires knowing when it stopped being in force.

### 6.2 What is versioned, and what is therefore fenced

Every definition-time artifact in this service, and where it enters §5's F2/F3 fences:

| Artifact | Version column | Enters the fence via |
|---|---|---|
| Indicator definition | `definition_version` + `published_seq` | F2 directly |
| Channel definition | `channel_version` + `published_seq` | `channel_registry_version` on the value; F3 |
| Channel binding | `binding_version` + `published_seq` | `channel_registry_version`; F3 |
| **Source tag mapping** | `mapping_version` + `published_seq` | `channel_registry_version`; F3. **Named in D22** |
| **Downsample reduction** | `reduction_version` | `channel_registry_version`; F3. §4.4 |
| Detector | `detector_version` + `definition_state_seq` | Candidates, not features (§7.3) |
| Taxonomy | `taxonomy_version` (Reference Data, 03 §14) | `resolution.taxonomy_version` |
| Reference-data units and equipment families | `unit_version`, `family_version` (03 §3.3, `[D35]`) | Pinned on definitions and bindings |

**Anything that can change the numeric value of a historical feature is on this list, or it is a leak.** The list is the checklist for reviewing any future change to this service: if a new mechanism can alter a stored value's meaning and does not appear here with a version and a `published_seq`, D22 has been reopened through a new path — which is exactly how `reduction_version` (§4.4) came to be on it.

### 6.3 Recomputation over history

```
POST /recomputations
{
  scope: { installed_item_id[] | equipment_family | asset_id | fleet }
  indicator_keys[]                 # explicit.  No wildcard  [C38's reasoning]
  definition_version               # WHICH version to compute under.  Required
  data_time_from, data_time_to     # the historical range
  reason                           # definition_change | channel_mapping_change |
                                   # reduction_change | data_correction | backfill
  triggering_ref                   # the definition/mapping/reduction version that motivated it
}
-> 202 Accepted { recomputation_run_id, estimated_windows }
```

Execution, as a scheduled Domino Job for enterprise scope or in-cluster for a bounded scope, writing back through `POST /health-indicator-values` (§9.3) — never by SQL (09 §9.1 item 1, `[D10, C7]`):

```
1. ALLOCATE ONE knowledge_seq for the whole run.  Every value the run produces shares it.
      -> all values in a run become knowable TOGETHER, which is what makes a training set
         assembled at any as_known_at internally consistent (§5.6)
2. Resolve the channel registry state:  channel_registry_version := that same seq
3. For each (item, window) in scope:
      recompute from ts.sample under definition_version
      INSERT a NEW ts.indicator_value row:
          definition_version       := as requested
          channel_registry_version := resolved above
          known_at_seq             := the run's seq
          value_seq                := allocated per row from the MonotonicSequencer
          computation_run_id       := the run
      -- NEVER UPDATE.  NEVER DELETE.  An UPDATE here is the D22 leak in one statement.
4. Maintain is_current for latest-serving only (§6.5)
5. emit health_indicator.computed  { ..., definition_version, definition_time,
                                     channel_registry_version, recomputation_reason }
6. Record the run: scope, counts, definition_version, triggering_ref, duration, operator
```

Three properties:

- **Append-only, always.** A recomputation inserts rows. `ts.indicator_value` has no `UPDATE` path outside `is_current` maintenance, and a repository method that updates `value` does not exist.
- **One `knowledge_seq` per run, many `value_seq` per run.** The run-level seq is the knowability boundary; the per-row seq is the deterministic tiebreak in §5.2's `row_number()`. Two counters with two jobs, and neither can do the other's.
- **`triggering_ref` closes the audit loop.** Given a value, one can reach the definition version that produced it, the run that computed it, and the artifact change that motivated the run.

### 6.4 The interaction with `as_known_at`, worked

The scenario D22 describes, run against this design. A definition `vib_band_rms` v3 is published on 2026-04-01 improving load normalization; recomputation covers 2024-01-01 onward.

| Query | Resolved seq | F2 selects | F3 admits | Result |
|---|---|---|---|---|
| `as_of=2025-03-01`, `as_known_at=2025-03-01` | pre-v3 | **v2** (v3's `published_seq` > resolved) | only values computed by 2025-03-01 | The v2 values as they stood. **v3 is invisible.** `coverage` reports nothing missing |
| `as_of=2025-03-01`, `as_known_at=2026-05-01` | post-recompute | **v3** | the recomputation's values | v3's recomputed values over the same historical windows |
| `as_of=2025-03-01`, `as_known_at=2026-03-31` | after v3 drafted, before published | **v2** | pre-v3 values | v2. **A draft is not knowledge** (§6.1 rule 2) |
| `as_of=2025-03-01`, `as_known_at=latest` | now | v3 | everything | v3 values, plus `definition_time_unconstrained: true` and the response header |

> **The property to hold onto.** A model trained "as of" an early date **never sees a later-authored definition**, and it never sees the later recomputation of an earlier definition either. Both halves are needed and F2 and F3 are respectively what supply them. The first row of that table is the entire remedy for D22, and §10.2's test asserts it by recomputing a historical training set under a frozen definition-time and requiring byte-identical output.

### 6.5 `RECOMPUTABLE_SUPERSEDE`, and the correction document 11 makes to it

Document 03 §11: *"Health indicators — Recomputable; enterprise recomputation supersedes. Rationale: derived data."*

Document 11 §7.3 refines it, and the refinement is load-bearing: *"Precedence is `origin == enterprise` **first**, then HLC — origin, not recency, is the discriminator. Edge values are retained and marked superseded so the disagreement remains inspectable. `definition_version` and definition-time are part of the key: recomputation under a *newer definition* is a new value, not a supersession `[D22]`."*

So supersession is scoped tightly:

```
Supersession applies ONLY within an identical key:
   (installed_item_id, indicator_key, window_start, window_end,
    definition_version, channel_registry_version)

Across DIFFERENT definition_version or channel_registry_version:
   the newer computation is a NEW VALUE, not a supersession.  Both are retained
   with their own known_at_seq, and §5.2 picks between them by FENCE, not by flag.
```

**`DECISION` — `is_current` is a materialized latest-serving convenience, and the bitemporal resolver never reads it.**

This is the most easily-broken rule in the service and it has a one-line failure mode. `is_current` answers "what should a dashboard show now." §5.2 answers "what was knowable at a past instant." If the resolver filtered on `is_current`, every historical query would collapse to the present, `as_known_at` would become decorative, and **D22 would be reopened while all three fences remained visibly present in the SQL.** The `-- NOTE:` comment in §5.2 exists so that a reader adding an index or an optimization sees the prohibition at the point of temptation. §10.2's `test_d22_resolver_ignores_is_current` asserts it directly by flipping every `is_current` and requiring the resolver's output to be unchanged.

The two mechanisms compose correctly precisely because they are separate: an enterprise recomputation of an edge-computed window sets `is_current` on its own row and clears it on the edge row, while the edge row keeps its own `known_at_seq` — so a query at an `as_known_at` before the recomputation still returns the edge value, correctly labelled `provenance.producer_node = 'edge:<asset_id>'` (§5.3).

### 6.6 Definitions are never authored at the edge

**Hard rule.** The edge profile holds a **replicated, read-only** copy of the channel registry and the indicator definitions, at a pinned `channel_registry_version` and definition set, delivered shore-to-ship by the coordinator (11 §9.3(e)). The edge's definition-management operations are absent from its router, not merely authorization-denied.

Three reasons, and the third is the one that would otherwise be discovered late:

1. **Contract.** Document 03 §11's default rule: any aggregate not listed is enterprise-authoritative and not edge-writable. Indicator definitions and channel mappings are not listed, so the default binds.
2. **Reviewability.** Document 04 §3 requires the registry to be *"an explicit, versioned, reviewable artifact."* Twelve hulls each authoring definitions produces twelve divergent feature semantics and no reviewable artifact at all.
3. **Clock discipline.** A single-writer knowledge log is what makes §5.4's one timestamp comparison legitimate. Edge authoring would give it two writers on two clocks across a disconnection, and resolving `as_known_at` would become a cross-node timestamp comparison — **D29, arriving through the leakage remedy.**

What happens when a mission needs an indicator the edge's pinned set lacks: **nothing is invented afloat.** The indicator is absent, the absence is recorded (`coverage.missing_indicators`, reason `not_defined_at_as_known_at` against the edge's own sequence), and the value is computed ashore on reconnect under the enterprise definition, arriving with an enterprise `known_at_seq`.

---

## 7. The edge-resident detector ensemble and pre-screener

Finding **D18**, in full: *"The PMA Pre-Screener cannot run afloat, and the unsupervised detectors are Domino Jobs, so afloat there is no candidate source at all. Review degrades to the open-ended authoring the design declares unreliable. Submarines — least instrumented, highest consequence — contribute zero confirmed tags."*

Document 06 §4 resolves it: *"The detector ensemble and a small pre-screener run in the edge inference runtime against exported artifacts. The enterprise **adds** candidates on reconnect rather than being the sole source."* Document 01 §12 makes it structural: *"Anomaly candidate generation is edge-resident… Otherwise a returning submarine's reviews had empty candidate sets and review degraded to the open-ended authoring the design declares unreliable."*

**Detector *execution* is this service's responsibility. Candidate *review* is PMA's.** The reduced pre-screener agent is PMA's edge component (04 §8); what this service owes it is a populated candidate stream afloat.

### 7.1 What runs where

| Detector class | Afloat | Ashore | Requires | Why |
|---|---|---|---|---|
| **`threshold`** | **Yes** | Yes | Nothing but the channel registry | Static and adaptive limits from `channel_definition.nominal_*` and the family spec. Wholly deterministic, no artifact, no training. Document 06 §4's stated floor: *"run only threshold and trending detectors afloat"* |
| **`trending`** | **Yes** | Yes | Indicator definitions | Robust slope / EWMA over health indicators with declared normalization. Deterministic. Must contend with SF-03's sawtooth floor and SF-01's run-in plateau (13 §7.2) |
| **`residual`** | **Conditional** | Yes | An exported normalization artifact | Indicator versus expected-under-operating-condition. Runs afloat **iff** the artifact exports and fits the edge envelope. Document 06 §4's assumption is HIGH confidence on export (*"document 02 confirms model export is a supported pattern with Navy precedent"*) with the stated fallback if it does not hold |
| `multivariate` | No | Yes | Full-fidelity cross-channel history | Covariance over the full channel set at full resolution |
| `spectral` | No | Yes | Raw-rate data | Full-resolution spectral feature extraction, principally against retained unmanned raw objects (§4.4) |
| `reconstruction` | No | Yes | A trained autoencoder plus a fleet-wide baseline | Needs the fleet population a hull does not have |
| **Cross-hull population comparison** | **No** | Yes | Other hulls | A hull cannot compare itself to hulls it cannot reach. Not a capability gap; a definitional one |
| **Detector *training*, of any class** | **Never** | Domino only | — | Document 01 §12: no Domino component is resident or reachable afloat. The edge **executes exported artifacts**; it does not train, tune, or select |

The asymmetry is real and must be presented as such rather than smoothed over: **the edge candidate stream is genuinely of lower recall than the enterprise stream.** That is why the enterprise adds on reconnect (§7.4) and why document 06 §4's fallback is *"accept lower candidate quality on the disconnected leg"* rather than pretending parity. What is not acceptable — and what D18 found — is an **empty** afloat candidate set.

### 7.2 The detector interface

```python
class Detector(Protocol):
    detector_key: ClassVar[str]
    detector_version: ClassVar[str]
    detector_class: ClassVar[DetectorClass]
    runs_at_edge: ClassVar[bool]
    requires_artifact: ClassVar[bool]

    def required_inputs(self) -> DetectorInputs:
        """Declares the indicator_keys, channel_keys, and history depth required.
        A detector whose inputs are unavailable does NOT run and does NOT emit a
        low-confidence guess — the absence is recorded on the mission's coverage."""

    def detect(self, window: DetectionWindow, ctx: DetectorContext) -> Iterator[Candidate]:
        """Inputs come from the SAME §5.2 resolver every consumer uses, at
        as_known_at = this node's current knowledge.  A detector NEVER reads
        ts.indicator_value directly: a detector on a private query path is a
        detector that can see what /features would have fenced.
        """
```

Two rules with teeth:

- **Detectors read through the feature resolver, not the table.** A detector that queried `ts.indicator_value` directly could ignore `min_completeness`, `is_current`, and the fences, and would then raise candidates from data the rest of the system considers unknowable. A lint forbids `ts.indicator_value` in `detectors/`.
- **Recalibration steps are excluded from step-based detection**, per document 13 §9.4: *"a step at recalibration that is not a physical change. Any detector that treats steps as events must contend with recalibration steps."* The exclusion is a shared input filter, not per-detector discipline, because six detectors will not each remember.

### 7.3 Detector versions are definition-time artifacts

Registering a detector version advances `knowledge_seq` (§3.0), and every candidate records the `definition_state_seq` it ran under (§3.7).

```
POST /detectors                     -> draft
POST /detectors/{key}/{ver}/publish -> allocates knowledge_seq
                                       artifact_digest required where requires_artifact
```

Why: a detector version change alters which candidates would have been raised over history. Recording the knowledge state a candidate ran under means "why did we not catch this in March" is answerable with the March detector set rather than today's — the same reasoning as §6.2, applied to candidates rather than features.

**Exported artifacts** are pinned by `artifact_digest` (SHA-256) recorded on every candidate. The edge holds artifacts delivered shore-to-ship (11 §9.3(e)); it never fetches one at runtime (01 §12: nothing is installed or retrieved at container start, `[D26]`). An artifact whose digest does not match its registration fails detector startup — the detector does not run degraded.

### 7.4 Origin tagging, and how the enterprise ADDS

Conflict policy `EDGE_GENERATABLE`, declared for aggregate `anomaly_candidate` (§8.4). Document 11 §7.3: *"Both sides may create. Enterprise **adds** on reconnect; it never replaces or prunes the edge set. Near-duplicate candidates over the same `(installed_item_id, window)` are linked as a candidate group with both origins preserved, never merged away."*

Origin tagging at emission:

```python
candidate = DetectedAnomaly(
    ...,
    origin        = "edge" if ctx.producer_node.startswith("edge:") else "enterprise",
    producer_node = ctx.producer_node,            # 'enterprise' | 'edge:<asset_id>'
    detector_key=d.detector_key, detector_version=d.detector_version,
    detector_artifact_digest=d.artifact_digest,
    definition_state_seq=ctx.knowledge_seq,
    attributed_to=classify_attribution(evidence),  # equipment | sensor | operating_condition
)
```

`origin` is derived from `producer_node`, never passed in, and the `anomaly_origin_matches_node` CHECK (§3.7) makes a mismatch unstorable.

The merge on reconnect, exactly:

```python
class EdgeGeneratable(ConflictPolicy):
    aggregate = "anomaly_candidate"
    policy_id = PolicyId.EDGE_GENERATABLE

    def merge(self, ctx, local, incoming) -> MergeDecision:
        # 1. Exact duplicate on the three-part dedup key -> Ignore.  Transport artifact.
        if local and dedup_key(local) == dedup_key(incoming):
            return MergeDecision.Ignore(reason="duplicate")

        # 2. NEAR-duplicate: overlapping (installed_item_id, window) from the OTHER origin.
        #    LINK into a candidate group.  DO NOT merge, DO NOT supersede, DO NOT prune.
        group = self.group_for(incoming)          # by (installed_item_id, window overlap)
        incoming.candidate_group_id = group.id if group else uuid4()
        return MergeDecision.Apply(incoming)

        # There is NO branch that sets superseded_by on a record of the other origin,
        # and no branch that deletes.  [D18]

    @final
    def _never_prunes_other_origin(self) -> None:
        """Asserted by test_d18_enterprise_adds_candidates_never_replaces (§10.5)."""
```

Four invariants:

1. **The enterprise pass over a mission never sets `superseded_by` on an edge candidate, and never deletes one.** `superseded_by` has exactly one legal use: a later pass superseding *its own node's* prior output.
2. **Candidates the edge found and the enterprise did not must survive**, per document 13 §15.2 Case 3 — *"the failure mode being an enterprise recomputation that quietly discards them."* They are the highest-value candidates in the set: the edge saw the mission live.
3. **The candidate *group* is what PMA ranks**, so a reviewer sees one item under document 06 §6's cap of 12 rather than the same anomaly twice, while both origins remain retained and inspectable. Grouping is a presentation join, not a data deletion.
4. **Overlapping enterprise candidates are generated deliberately in the test corpus.** Document 13 §15.2: *"Enterprise-generated candidates on the same missions after reconnect, deliberately overlapping the edge set, so deduplication and merge semantics are exercised rather than assumed."*

### 7.5 What the edge must hold to do this at all

| Artifact | Delivery | Authority |
|---|---|---|
| Channel registry (definitions, bindings, mappings) at a pinned version | Shore-to-ship, coordinator (11 §9.3(e)) | Read-only. §6.6 |
| Indicator definitions at a pinned set | Shore-to-ship | Read-only. §6.6 |
| Detector artifacts, digest-pinned | Shore-to-ship | Read-only |
| Reference data: units, equipment families, taxonomy version | Shore-to-ship snapshot, version-pinned | Read-only. Cached, never a compute-path call (09 §4.4.2) |
| Registry configuration read model | Inbox from `installed_item.*`, `configuration.baseline_changed` | Read-only + provisional minting (11 §8) |
| Cached predictions | Inbox, with an explicit staleness horizon | **Presented as degraded** (03 §11). Not this service's aggregate |

**A pinned version the edge cannot satisfy is a recorded absence, never an improvisation.** If a mission's channels have no published mapping in the edge's pinned registry, samples are ingested and quarantined as unmapped (§4.5), indicators do not compute, detectors do not run, and the mission's `coverage` records it. The samples are retained and mapped ashore. Nothing is guessed afloat, because a guess afloat is a guess that cannot be reviewed for six weeks.

---

## 8. Events published and consumed

### 8.1 Envelope construction, including `producer_node`

`outbox.emit()` (11 §2.3) builds the full document 03 §5.4 envelope. This service supplies the domain arguments; the library supplies the clock block, the sequence, the signature, and the encryption. **No service code hand-rolls an envelope.**

```python
# services/telemetry/src/fathom_telemetry/events/publishers.py
#
# PRODUCER NODE.  [03 §5.4 · 11 §4.2]
# This slug runs as TWO INDEPENDENT DEPLOYMENT INSTANCES — the enterprise instance
# and one edge instance per afloat hull — each minting its OWN monotonic_seq.  Without
# producer_node in the dedup key, (telemetry, 41) is ambiguous: two different events
# collide and ONE IS SILENTLY DROPPED.  Condition & Telemetry is the sub-application
# that made document 03 add this field.  Nothing here keys on two parts.
#
# The literal form is document 03 §5.4's: "enterprise" | "edge:<asset_id>".
# (Document 11 §4.2's `telemetry@ssn796` examples predate the correction — see §15.)

PRODUCER_NODE: Final[str] = (
    "enterprise" if settings.deployment.profile is Profile.ENTERPRISE
    else f"edge:{settings.deployment.asset_id}"
)
```

`settings.deployment.profile` and `settings.deployment.asset_id` come from `config.py` — the only module reading the environment (09 §4.5) — populated from the Helm profile (§11.1). `asset_id` is **required and startup-fatal when absent** on the edge profile: an edge instance that could not name its hull would emit `edge:None` and collide with every other hull.

Per document 11 §4.3, `producer_node_id` is never reused for a different deployment and a restored database backup requires a new node id.

### 8.2 Published events — all six document 03 §6 rows

Every row below is document 03 §6's Telemetry catalog verbatim in its payload summary, with this document supplying topic, keys, and retention.

| `event_type` | Topic | Aggregate | Partition key | Compaction key | Scope / subject | Consumers (03 §6) |
|---|---|---|---|---|---|---|
| `fathom.telemetry.telemetry_batch.ingested` | `fathom.telemetry.telemetry_batch.v1` | `telemetry_batch` | `asset_id` | — not compacted | `asset` / `asset_id` | `pdm`, `pma`, `failure-intel` |
| `fathom.telemetry.health_indicator.computed` | `fathom.telemetry.health_indicator.v1` | `health_indicator` | `asset_id` | — not compacted | `installed_item` / `installed_item_id` | `pdm`, `fleet-status` |
| `fathom.telemetry.usage_counter.updated` | `fathom.telemetry.usage_counter.v1` | `usage_counter` | `asset_id` | — not compacted | `installed_item` / `installed_item_id` | `pdm`, `maintenance` |
| `fathom.telemetry.usage_counter.reset` | `fathom.telemetry.usage_counter.v1` | `usage_counter` | `asset_id` | — not compacted | `installed_item` / `installed_item_id` | `pdm`, `maintenance` |
| `fathom.telemetry.mission.completed` | `fathom.telemetry.mission.v1` | `mission` | `asset_id` | — not compacted | **`mission`** / `mission_id` | `pma`, `failure-intel` |
| `fathom.telemetry.anomaly.detected` | `fathom.telemetry.anomaly.v1` | `anomaly` | `asset_id` | — not compacted | `installed_item` / `installed_item_id` | `pma`, `fleet-status` |

Four decisions embedded in that table.

**(a) Batch-level, never sample-level.** Document 03 §6: *"Batch-level rather than sample-level, deliberately. Per-sample events would constitute an event storm carrying no additional information."* At document 06 §7's ~5M samples/day fleet-wide, per-sample events are not a scaling concern to be optimized; they are a category error.

**(b) `telemetry.batch_ingested` carries a `payload_ref`, never inline samples.** Per document 11 §2.6 and the discipline `[D27]` imposes on `prediction.updated`. The payload carries asset, time range, `channel_set`, `sample_count`, `expected_sample_count`, `completeness`, `observation_state`, `quality`, `producer_node`, and the object reference. Nine million samples from a reconnecting submarine (13 §15.3) do not go through the broker.

**(c) `DECISION` — no Telemetry topic is compacted, and the reasoning differs per topic.**

- `telemetry_batch`, `health_indicator`, `anomaly`: **compaction would destroy the history the design depends on.** For `health_indicator` this is acute: compacting on any key would discard the recomputation history that definition-time correctness is built from, so `as_known_at` would be answerable from the database and not from the event stream, and a consumer's rebuild would silently lose D22's remedy. For `anomaly`, compaction would prune candidates, which is `[D18]` by another route.
- `usage_counter`: compaction is genuinely attractive — a compacted state-carrying topic keyed on `installed_item_id|counter_type|counter_epoch` is exactly the right shape for "current value per epoch," and it is emphatically **not** `asset_id` (`[D5]`). But `usage_counter.updated` and `usage_counter.reset` are one aggregate and therefore one topic (03 §5.1: one topic per aggregate type per producer), and they cannot share a compaction key without one discarding the other — a reset compacted away is a lost epoch boundary, which is `[D9]`'s third bug. **Resolution: not compacted, 30-day retention, rebuild via `changed_since`** (03 §5.1, §4, `[D5]`). If a future revision wants compaction here, `reset` must become its own aggregate, which is a document 03 §6 change. Recorded as **OQ-3**.

Retention follows document 03 §5.1: **7 days** for `telemetry_batch` (a high-volume derived stream), **30 days** for the other four. Read-model rebuild uses `changed_since` in every case — the event bus is not a rebuild source (`[D5]`, 09 §9.2 item 9).

**(d) `DECISION` — `mission.completed` has `scope = mission` and partition key `asset_id`, and the two are independent.**

Document 03 §5.4 is explicit that `mission_id` is *"required when scope=mission (e.g. `mission.completed`, `mission_review.*`)"*, so the scope is settled. Document 03 §5.1 assigns `asset_id` to asset-scoped events and lets *"fleet-scoped, NIIN-scoped, and class-scoped events partition on their own scope identifier"* — mission is not in that list. A mission is an occurrence belonging to one asset, and per-asset ordering of missions is a property consumers need (a hull's patrol N precedes patrol N+1), while per-mission ordering is vacuous because each mission completes once. So the partition key is `asset_id` while the scope is `mission`. **Scope and partition key answer different questions and this document states so explicitly**, because conflating them is easy and the resulting mistake — partitioning on `mission_id` — would scatter one hull's missions across partitions and forfeit the only ordering guarantee the design relies on (03 §5.1, `[D4]`).

**[AMENDMENT — OQ-4 resolved.]** Document 10 §4.5's `EventScope` enum previously had no `MISSION` member and its `SCOPE_SUBJECT_FIELD` map no mission entry, while its own docstring observed that *"`mission_id` appears in `subject` but NO `scope` value selects it."* Document 03 §5.4 settled it, and document 10 §4.5 now carries `EventScope.MISSION` and the corresponding `SCOPE_SUBJECT_FIELD` entry.

**Payload additions to document 03 §6's summaries**, all additive-optional and therefore requiring no major version (03 principle 5):

| Event | Added field | Why |
|---|---|---|
| `health_indicator.computed` | `channel_registry_version` | A recomputation driven by a mapping change has an unchanged `definition_version`; without this the consumer cannot tell the value changed (§3.1.6) |
| `health_indicator.computed` | `recomputation_reason` | `definition_change` \| `channel_mapping_change` \| `reduction_change` \| `data_correction` \| `backfill` |
| `health_indicator.computed` | `known_at_seq` | So a consumer's read model can reproduce §5.2's F3 fence locally |
| `telemetry.batch_ingested` | `observation_state`, `expected_sample_count` | Document 04 §3's "no fault observed" versus "not observed" is not expressible from `completeness` alone |
| `usage_counter.updated` | `counter_epoch`, `carry_forward_total`, `life_to_date`, `correction` | §3.5. `counter_epoch` is required by 03 §11's merge key; `life_to_date` is what PdM and Scheduling actually need |
| `usage_counter.reset` | `counter_epoch_closed`, `counter_epoch_opened`, `final_value` | The epoch boundary must be unambiguous to a consumer merging counters |
| `anomaly.detected` | `candidate_group_id`, `attributed_to`, `detector_artifact_digest`, `score_scale` | §3.7 |

Per document 03 §5.5 and document 10 §4, every payload schema lives in `packages/canonical-schemas` and registers with the schema registry; this service cannot publish an unregistered payload.

**The edge instance publishes all six event types.** That is the direct consequence of §2.2: two deployment instances of one slug, distinguished only by `producer_node`, each with its own sequence space. `events/catalog.py`'s `PUBLISHES` is identical in both profiles, which is what document 09 §8.2's reconciliation against document 03 §6 requires.

### 8.3 Consumed events, and the correctness dependency each carries

Document 04 §3: *"Events consumed: `asset.registered`, `installed_item.installed`, `installed_item.removed`, `configuration.baseline_changed`. Counters and indicators attach to installed items, so item lifecycle events are a correctness dependency: a replacement opens a new counter epoch rather than continuing the prior item's accumulation."* Enumerated explicitly, never wildcarded (`[C38]`).

All handlers run under document 11 §3.4's consume loop: record and apply in **one** transaction, epoch fence **before** any state change, `processed_at` set inside the same transaction, Kafka offset committed only after. The mandatory `# INBOX SEMANTICS — DO NOT "SIMPLIFY" THIS` comment template of document 11 §3.2 appears verbatim above the dispatch, and CI checks for it.

| Event | Handler behavior |
|---|---|
| `asset.registered` | Create the asset read-model row; provision channel bindings and mappings from the class template as `review_state = 'draft'` (§3.1.5). **Nothing computes from a draft mapping.** Set the domain profile, which selects the ingest adapter |
| `installed_item.installed` | **Open counter epoch 1** per counter type, seeded at `usage_at_install`, `carry_forward_total = 0` (§3.5.1). Activate position→item resolution from `installed_at`. **The new item inherits nothing** — not counters, not indicator history, not candidates `[D9]` |
| `installed_item.removed` | Close the open epoch; freeze `final_value`. Stop attributing samples on that position to that item from the removal date. Do **not** delete the item's samples, indicators, or candidates: they are the observations that item generated |
| `installed_item.identity_resolved` **[AMENDMENT — closes OQ-5]** | `resolution: superseded` — alias `provisional_id` to `canonical_id` via `IdentityAliasResolver` (11 §8.4); every counter, indicator, and candidate keyed on the provisional id resolves through the alias from this point. `resolution: confirmed` — no-op, `provisional_id == canonical_id` already |
| `configuration.baseline_changed` | **[AMENDMENT]** Resolve `changed_items` vs `changed_items_ref` first (20 §6.2 — exactly one is set; an initial baseline is always the ref form, not inline). Epoch-fence first (11 §3.5). Re-resolve position→item attribution for affected positions. **See the rule below** |

**The `configuration.baseline_changed` rule, because it is where two findings compose.**

A baseline change is not a retroactive rewrite of sample attribution. Document 04 §2's bitemporal argument applies directly: the Registry tracks valid time and record time separately, and *"a configuration correction entered three weeks late changes valid time without rewriting record time."* So:

1. **Forward effect.** The mapper's position→item resolution (§4.5) reads the configuration read model at each sample's data time, so a baseline change is picked up automatically for samples whose data time falls in its new validity range. No rewriting is needed.
2. **Retroactive-valid-time effect.** Where the change carries a valid-time range in the past — the correction case — affected indicator values are recomputed under a **new `knowledge_seq`** with `reason = data_correction`. New rows, never updates.
3. **The consequence that matters.** A query at an `as_known_at` **before** the correction still returns the pre-correction values, correctly attributed to what we believed then. A query after it returns the corrected values. A model audited against its own training set therefore still reconciles.

> **Why this matters.** Document 04 §4 calls silent staleness after a component replacement *"the failure mode most likely to destroy operator trust permanently,"* and document 11 §3.2 records that the naive inbox rule reintroduces it by itself. This service's exposure is different in kind and equally damaging: a baseline correction that retroactively rewrote historical feature values in place would make every previously-trained model unreproducible and every previous audit unexplainable, with no error anywhere. Recomputation under a new knowledge sequence is what makes a correction *and* the history of having been wrong both available.

**`installed_item.identity_resolved`.** **[AMENDMENT — closes OQ-5; see §14's register entry below, which this paragraph previously contradicted.]** Document 11 §8.4 introduces this event so consumers can resolve provisional edge-minted identities. Document 03 §6's Registry catalog now carries it, on the same `fathom.registry.installed_item.v1` topic as `.installed`/`.removed`, naming `telemetry` as a consumer. **This service subscribes to it**, extending the existing `installed_item.*` handler (§9.3) rather than adding a new one: on `resolution: superseded`, the provisional `installed_item_id` is aliased to the `canonical_id` via `fathom-sync`'s `IdentityAliasResolver` (11 §8.4), and every subsequent sample, indicator, and candidate keyed on the provisional id resolves through the alias; on `confirmed`, `provisional_id == canonical_id` and the handler is a no-op (11 §8.4's designed common case).

### 8.4 Conflict policies — declared completely, or startup fails

Per document 11 §7.2's complete-or-fail registry (`[C20]`):

```python
policies = ConflictPolicyRegistry.declare(
    service="telemetry",
    policies=[
        AppendOnlyDedup(aggregate="telemetry_batch",
                        divergence_budget=DivergenceBudget(max_disconnection=timedelta(days=60))),
        AppendOnlyDedup(aggregate="sample",
                        divergence_budget=DivergenceBudget(max_disconnection=timedelta(days=60))),
        RecomputableSupersede(aggregate="health_indicator",
                        divergence_budget=DivergenceBudget(max_disconnection=timedelta(days=60))),
        EdgeGeneratable(aggregate="anomaly_candidate",
                        divergence_budget=DivergenceBudget(max_disconnection=timedelta(days=60))),
        MonotonicMergeKeyed(aggregate="usage_counter",
                        divergence_budget=DivergenceBudget(max_disconnection=timedelta(days=60))),
        EdgeAuthoritativeThenEnterprise(aggregate="mission_record",
                        divergence_budget=DivergenceBudget(max_disconnection=timedelta(days=60))),
        # Definition-time aggregates take the §11 DEFAULT explicitly: enterprise-authoritative,
        # NOT edge-writable.  This is §6.6 expressed as a policy declaration.
        EnterpriseAuthoritativeNotEdgeWritable(aggregate="channel_definition", default=True),
        EnterpriseAuthoritativeNotEdgeWritable(aggregate="channel_binding",    default=True),
        EnterpriseAuthoritativeNotEdgeWritable(aggregate="source_tag_mapping", default=True),
        EnterpriseAuthoritativeNotEdgeWritable(aggregate="indicator_definition", default=True),
        EnterpriseAuthoritativeNotEdgeWritable(aggregate="detector",           default=True),
        EnterpriseAuthoritativeNotEdgeWritable(aggregate="quality_assessment", default=True),
    ],
)
```

**Every budget exceeds 42 days.** Document 11 §9.1's binding constraint applied to this service: document 06 §4 scripts a six-week disconnect, so a budget below it means the demonstration breaches the budget it exists to satisfy — the hull goes explicitly read-only for telemetry ingest or candidate generation halfway through the patrol, and D18 returns wearing a compliance badge. 60 days gives headroom over the scripted 42 (13 §15.1's `t: 42d`). The **storage** envelope, not the time budget, is the real constraint afloat; §11.4 gives the derivation.

Note `MonotonicMergeKeyed`'s key is `(installed_item_id, counter_type, counter_epoch)` (11 §7.4) — **never `position_id`**, and never merged across `counter_epoch`.

---

## 9. API surface

All operations under `/api/v1/telemetry/`, all carrying `x-substitution` and `x-side-effects` via document 09 §5.1's `operation()` helper, all validated at import time, at startup, and in CI.

### 9.1 Reads

| Operation | `x-substitution` | `x-side-effects` | Agent | Notes |
|---|---|---|---|---|
| `GET /features?installed_item_id=&feature_set=&as_of=&as_known_at=` | required | none | yes | **§5.** Both time selectors required |
| `GET /health-indicators?installed_item_id=&from=&to=&as_of=&as_known_at=` | required | none | yes | §5.8. `as_known_at` added to 04 §3's signature |
| `GET /usage-counters?installed_item_id=&as_of=` | required | none | yes | Returns per-epoch rows **and** `life_to_date` (§3.5.1) |
| `GET /assets/{asset_id}/channels` | required | none | yes | Bindings and mappings in force; `?as_of=&as_known_at=` optional |
| `GET /channels/{channel_key}` | required | none | yes | Definition, all versions |
| `GET /channels/{channel_key}/items` | required | none | yes | The many-to-many map (§3.1.4). Attribution ambiguity, exposed |
| `GET /installed-items/{id}/channels` | required | none | yes | The inverse |
| `GET /missions?asset_id=&from=&to=` | required | none | yes | |
| `GET /missions/{mission_id}` | required | none | yes | Boundaries, completeness, `gap_intervals` |
| `GET /missions/{mission_id}/telemetry` | required | none | no | The replay source. PMA materializes evidence from it (§1.2). Not agent-selected: response size |
| `GET /anomalies?mission_id=&origin=&attributed_to=` | required | none | yes | 04 §3. `origin` filter is how PMA sees both sets |
| `GET /telemetry-batches?asset_id=&from=&to=` | required | none | no | |
| `GET /quality?asset_id=&channel_key=&from=&to=` | required | none | yes | §3.8. **Singular path — enumerated in `x-naming-carve-outs`** as a query projection (03 §4, `[C23]`) |
| `GET /indicator-definitions?feature_set=&as_known_at=` | required | none | yes | The definition registry, definition-time resolvable |
| `GET /detectors` | internal | none | no | |

### 9.2 Compute-only

| Operation | `x-substitution` | `x-side-effects` | Agent | Notes |
|---|---|---|---|---|
| `POST /features/batch` | required | **none** | no | **The training-set assembly path.** One `resolution_token` for the whole set (§5.6). A compute-only `POST` — exactly the class `[C1, D11]` found wrongly excluded by an HTTP-method eligibility gate. Not agent-selected because of response size, not because of eligibility |

### 9.3 Writes

| Operation | `x-substitution` | `x-side-effects` | Notes |
|---|---|---|---|
| `POST /telemetry-batches` | required | state-changing | **§4.** `Idempotency-Key` required. `X-Backfill` accepted. Resource-oriented form of 04 §3's `POST /ingest/telemetry` — see §15 |
| `POST /usage-counter-observations` | required | state-changing | Bulk, idempotent. 04 §3's `POST /ingest/usage` |
| `POST /health-indicator-values` | required | state-changing | **Bulk, idempotent, fenced.** The Domino Job write-back path for indicator computation and recomputation (04 §3's `POST /ingest/indicators`). Never SQL (`[D10, C7]`) |
| `POST /anomaly-candidates` | required | state-changing | Bulk, idempotent. The Domino Job write-back for the enterprise detector ensemble (04 §3's `POST /ingest/detections`) |
| `POST /usage-counters/{installed_item_id}/{counter_type}/resets` | required | state-changing | §3.5.1. A sanctioned sub-resource action (03 §4) |
| `POST /missions/{mission_id}/complete` | required | state-changing | Sanctioned sub-resource action. Finalizes completeness, emits `mission.completed` |
| `POST /recomputations` | internal | state-changing | §6.3 |
| `POST /indicator-definitions` · `.../{key}/{ver}/publish` | internal | state-changing | §6.1. **Absent from the edge router** (§6.6) |
| `POST /channels` · `POST /channel-bindings` · `POST /channel-mappings` · `.../{id}/publish` | internal | state-changing | §3.1. **Absent from the edge router** |
| `POST /detectors` · `.../{key}/{ver}/publish` | internal | state-changing | §7.3. **Absent from the edge router** |

**All four bulk write paths are idempotent and baseline-epoch fenced** (03 §4, `[D3]`), wrap `BaselineFencedComputation` (11 §3.5), and refuse a result computed under a superseded epoch.

### 9.4 `changed_since` reads — mandatory, per projected aggregate

Document 03 §4: *"Every sub-application exposes `GET /{collection}?changed_since=&cursor=` over each aggregate a consumer maintains a read model of. This is the rebuild path; the event bus is not `[D5, D25, D30]`."*

| Collection | Projected by | `changed_since` cursor column |
|---|---|---|
| `/telemetry-batches` | `pdm`, `pma`, `failure-intel` | `known_at_seq` |
| `/health-indicators` | `pdm`, `fleet-status` | `known_at_seq` |
| `/usage-counters` | `pdm`, `maintenance` | `known_at_seq` |
| `/missions` | `pma`, `failure-intel` | `known_at_seq` |
| `/anomalies` | `pma`, `fleet-status` | `known_at_seq` |
| `/channels`, `/channel-mappings` | — (no declared consumer) | `published_seq`. Exposed anyway: it is how a mapping change reaches consumers absent an event (§3.1.6) |
| `/indicator-definitions` | — | `published_seq` |

**`changed_since` cursors on `known_at_seq`, not on a timestamp.** A timestamp cursor across a STIG backward step either re-delivers or skips (`[D29]`); a gap-free integer cursor cannot. The `?changed_since=` parameter accepts an integer sequence position, and a rebuild that resumes from a sequence position is exact.

### 9.5 Agent tool manifests

`packages/agent-tooling/manifests/telemetry/`:

| Manifest | Purpose | Operations |
|---|---|---|
| `telemetry-condition-lookup.v1` | The Maintainer Copilot's condition surface: what is this item's health, how complete is the data | `GET /health-indicators`, `GET /usage-counters`, `GET /anomalies`, `GET /quality`, `GET /installed-items/{id}/channels` |
| `telemetry-mission-context.v1` | PMA Pre-Screener candidate context | `GET /missions/{id}`, `GET /anomalies?mission_id=`, `GET /features` |

Both select only `x-side-effects: none` operations (03 §8.1), pin an API major version, ship manifest conformance tests that run inside this service's suite (03 §8.4), and declare a reviewed `purpose` (03 §8.5). Per document 09 §8.7, an unowned manifest is deleted rather than inherited.

**A manifest note that is a safety property, not a preference.** `telemetry-condition-lookup.v1` sets `as_known_at=latest` as a parameter default and **`as_of=latest`** likewise, because an agent answering "how is this pump doing" wants current condition. That is the correct default for that task and it is visible in the manifest, which is a versioned reviewed artifact — which is exactly the property that makes the `latest` literal safe (§5.1). No manifest defaults `as_known_at` for a training-shaped task, because no agent assembles training sets.

---

## 10. Testing

### 10.1 Conformance suite wiring

Per document 09 §4.7, unmodified. `packages/contracts/conformance/telemetry/` holds the shared suite; `services/telemetry/tests/conformance/test_suite.py` is eight lines collecting it; `conftest.py` supplies exactly four fixtures — `conformance_target`, `event_tap`, `fault_injector`, `reference_dataset`. **No shared conformance test is skipped, xfailed, subclassed, or edited** (09 §8.5). The reference dataset comes from `data/synthetic/` (document 13), not from hand-written fixtures.

Five categories per document 03 §10, with this service's specifics:

| Category | Telemetry specifics |
|---|---|
| **Contract** | Every `x-substitution: required` operation; the §5.7 refusal matrix; cursor pagination on all seven `changed_since` collections; `Idempotency-Key` on all four bulk writes; `ETag`/`If-Match` on definitions and mappings |
| **Event** | All six event types with the full envelope including `producer_node`; within-partition ordering per `asset_id`; compaction-key absence asserted on all four topics; payload registry validation |
| **Fault injection** | Document 11 §11.1's full matrix × every state-changing operation. `AFTER_INBOX_INSERT_BEFORE_APPLY` is mandatory and is D2's regression test |
| **Consumer-driven** | Contributed **into** this suite by `pdm`, `pma`, `fleet-status`, `failure-intel` (03 §6's declared consumers). Contributed **by** this service into `registry`'s suite for the four events it consumes. `[C3]` — a declared consumer contributing no test is an unmet Definition-of-Done item |
| **Manifest** | Both §9.5 manifests |

Four tiers per document 09 §4.7 — `unit`, `integration` (real TimescaleDB and real Redpanda via testcontainers), `contract`, `conformance` — plus one addition this service needs:

**`tests/leakage/` is a fifth tier and a distinct CI job.** Justification: the leakage tests are slow (they publish definitions, recompute history, and re-assemble training sets), they are the tests that must never be allowed to soft-fail, and separating them makes "did the leakage suite run" answerable from the pipeline rather than from a test-selection expression. Flagged as an extension of document 09 §4.7 in §15.

### 10.2 The bitemporal feature API — leakage detection

Finding D22's remedy, made executable. **This is the most important test in the service.**

```python
# services/telemetry/tests/leakage/test_definition_time.py

async def test_d22_frozen_definition_time_recompute_is_identical(svc, gen):
    """Recompute a historical training set under a FROZEN definition-time and assert
    identity.  [D22's remedy · 04 §3 · §5.2]

    The assertion is IDENTITY, not similarity, and it is asserted on the resolution
    token as well as on the values — two runs can agree on values by luck and
    disagree on what they resolved.
    """
    T, K = "2025-03-01T00:00:00Z", "2025-03-01T00:00:00Z"
    items = gen.spotlight_items(n=60)                      # 13 §7.1

    # 1. The training set as it stood.
    S1 = await svc.features_batch(items, feature_set="pdm_tier2_v1", as_of=T, as_known_at=K)
    assert S1.resolution.resolution_token

    # 2. Author a NEW definition version whose values differ over windows ending < T.
    v_new = await svc.publish_indicator_definition(
        indicator_key="vib_band_rms",
        spec=gen.improved_normalization_spec(),            # measurably different values
        authored_rationale="load normalization improved after reviewing 2025 failures",
    )
    assert v_new.published_seq > S1.resolution.resolved_knowledge_seq

    # 3. Author a channel MAPPING correction with retroactive valid_from < T.
    #    D22 names mappings alongside definitions; a definition-only test misses half.
    await svc.publish_channel_mapping_correction(
        asset_id=items[0].asset_id, source_tag="TAG-0412",
        corrected_position_id=gen.other_position(), valid_from="2024-06-01T00:00:00Z",
    )

    # 4. Ingest LATE-ARRIVING samples whose data_time < T but whose admission is > K.
    #    This is the submarine burst (§5.5) and it is the fence F3 exists for.
    await svc.ingest_subsurface_burst(gen.burst(data_time_from="2025-02-01",
                                               data_time_to="2025-02-28"))

    # 5. Recompute all of history under the new definition and the new mapping.
    await svc.recompute(scope="fleet", indicator_keys=["vib_band_rms"],
                        definition_version=v_new.definition_version,
                        data_time_from="2024-01-01", data_time_to="2026-06-01",
                        reason="definition_change")

    # 6. THE ASSERTION.  Same as_of, same as_known_at -> byte-identical.
    S2 = await svc.features_batch(items, feature_set="pdm_tier2_v1", as_of=T, as_known_at=K)
    assert S2 == S1
    assert S2.resolution.resolution_token == S1.resolution.resolution_token
    assert all(f.definition_version < v_new.definition_version for f in S2.all_features())

    # 7. THE TEST MUST PROVE THE LEAK EXISTS, or it is not testing anything.
    #    (Same discipline as 11 §11.2's test_d29_backward_step_does_not_reorder.)
    S3 = await svc.features_batch(items, feature_set="pdm_tier2_v1",
                                 as_of=T, as_known_at="latest")
    assert S3 != S1, "no definition-time-sensitive value changed; the test is vacuous"
    assert S3.definition_time_unconstrained is True
    assert any(f.definition_version == v_new.definition_version for f in S3.all_features())
```

The rest of the leakage suite, each named for what it guards:

| Test | Assertion |
|---|---|
| `test_d22_definition_authored_after_as_known_at_is_absent_with_reason` | An indicator published after `as_known_at` appears in `coverage.missing_indicators` with `reason='not_defined_at_as_known_at'` and **never as a null-valued feature.** A null invites imputation of a feature that had not been invented |
| `test_d22_edge_values_not_knowable_before_admission` | **§5.5.** An edge-computed value with `window_end` on day 9 of a 42-day disconnect is invisible to an enterprise query at `as_known_at` = day 30, and visible at day 43. Asserted on document 13 §15's scripted scenario, not on a hand-built fixture |
| `test_d22_resolver_ignores_is_current` | **§6.5.** Flip `is_current` on every row; assert §5.2's output is unchanged. Guards the one-line reintroduction of D22 with all three fences visibly present |
| `test_d22_mapping_correction_does_not_rewrite_knowledge_time` | A retroactive `valid_from` correction produces a new `mapping_version` at a new `published_seq`; queries before it are unchanged |
| `test_d22_reduction_version_is_definition_time` | **§4.4.** Change the unmanned 10 Hz→1 Hz reduction; recompute from retained raw; assert a pre-change `as_known_at` is unchanged |
| `test_d22_late_arriving_data_within_as_of_is_fenced_by_f3` | Removing F3 alone must break this test. Asserted by running the resolver with F3 disabled behind a test-only flag and requiring a difference |
| `test_d22_f2_removal_breaks_the_suite` | The mirror: with F2 disabled, the frozen-recompute test must fail. **Both fence-removal tests exist so that neither fence can be dropped as redundant** |
| `test_d22_batch_shares_one_resolution` | `POST /features/batch` over 500 items straddling a definition publication yields one `resolution_token` for all of them; no item resolves post-publication |
| `test_d22_no_wildcard_definition_selection` | A `feature_set` resolves to an explicit definition set; no query path returns "the latest of everything" |

### 10.3 Ingest against the generator's deliberately corrupted data

Document 13 §9's ten-stage pipeline **is** this service's realistic input. The ingest suite is parameterized over the generator's noise stages, and the corpus is document 13's, loaded through `reference_dataset`.

| Test | Guards | Source |
|---|---|---|
| `test_absent_sample_is_null_not_zero` | `value IS NULL`; no row carries a sentinel; completeness reflects it | 13 §9.6 |
| `test_burst_dropout_recorded_as_gap_intervals` | Correlated outage runs appear as enumerated intervals, not as a completeness scalar | 13 §9.6 |
| `test_stuck_at_value_is_a_sensor_fault_not_degradation` | A plausible constant run → `STUCK` + `stuck_runs`; any candidate from it is `attributed_to='sensor'` and is excluded from the equipment stream | 13 §9.6 |
| `test_clipped_peak_flagged_and_fraction_reported` | Saturation against `saturation_*` → `CLIPPED`; `clipped_fraction` per channel; no extrapolation | 13 §9.2 |
| `test_impulse_flagged_not_removed` | `IMPULSE` set, sample retained; removal only via a definition's `outlier_policy` | 13 §9.7 |
| `test_duplicate_samples_deduplicated_idempotently` | Within-batch and cross-batch dedup; the discard counted, the survivor unflagged | 13 §9.7 |
| `test_recalibration_step_is_not_an_anomaly` | A step at a recorded calibration raises no candidate | 13 §9.4 |
| `test_operating_condition_covariates_are_ingested_as_channels` | Confounders are queryable, so normalization is possible for a definition that does the work | 13 §9.5 |
| `test_decoy_channel_is_not_suppressed` | `role='decoy'` channels appear on `/features` with the role published | 13 §7.3, §9.9 |
| `test_shared_channel_attribution_weight_is_null_not_one` | A shared channel's `attribution_weight` is NULL where unresolvable; never fabricated | 13 §7.3 |
| `test_mnar_correlation_measured_and_published` | `mnar_indicator` is non-zero on the shipped corpus and appears in `coverage` | 13 §9.11 |
| `test_subsurface_six_week_gap_is_not_observed_not_zero_completeness` | `observation_state='not_observed'`; document 04 §3's distinction holds | 13 §9.6, 04 §3 |
| `test_unmapped_tag_quarantined_never_dropped` | An unmapped tag lands in quarantine and on `GET /quality`; sample count reconciles | §4.5 |
| `test_ingest_never_repairs` | Over the whole corpus, no stored sample value differs from the decoded-and-transformed source value. **A single repair anywhere fails this test** | §4.6 |
| `test_noise_ablation_corridor_reflected_in_quality_flags` | Against document 13 §16.3's noise-disabled and noise-enabled datasets, flag counts differ in the expected direction. Couples this service's assessor to the generator's V&V corridor rather than to a private notion of "clean" | 13 §16.3 |

`test_ingest_never_repairs` is the one to keep. Every other test in the table can be satisfied by handling one corruption; that test asserts the global property §4.6 rests on, and it is the one an optimization will break.

### 10.4 Channel registry versioning

| Test | Assertion |
|---|---|
| `test_mapping_bitemporal_correction` | Retroactive `valid_from` changes data-time applicability without altering `published_seq` of prior versions; the exclusion constraint prevents overlapping published mappings |
| `test_mapping_no_overlap_enforced_by_constraint` | Two published mappings for one `(asset, source_system, source_tag)` over overlapping data time is a constraint violation, not an application check |
| `test_position_wired_resolution_at_data_time` | **The anti-inherited-degradation test.** Replace an item mid-history; assert samples before the swap attribute to the old item and after to the new, from one unchanged `position_wired` mapping |
| `test_item_integral_mapping_follows_the_item` | An `item_integral` mapping does not re-attribute on position change |
| `test_unit_mismatch_rejected_at_publication` | A `transform` whose output unit differs from the channel's declared `unit_code` fails publication, not runtime |
| `test_unit_must_resolve_against_reference_data` | An unresolvable `unit_code` fails publication |
| `test_draft_mapping_produces_no_samples` | Class-template provisioning does not imply review (§3.1.5) |
| `test_two_hulls_divergent_mappings` | Per-hull deviation from one class template; neither hull's mapping affects the other |
| `test_channel_registry_version_is_knowledge_seq_projection` | No second counter; the projection of §3.1.5 matches for a thousand random sequence positions |
| `test_channel_version_supersession_retains_prior` | A superseded channel version remains readable and remains the version historical samples cite |

### 10.5 Edge, counters, and candidates

Document 11 §11.4's suite applies in full. Telemetry-specific additions, run against document 13 §15's scripted scenarios with `expected_post_reconciliation` as golden files:

| Test | Guards |
|---|---|
| `test_d9_counter_keyed_on_item_not_position` | Replace an item at a position; the new item's epoch 1 starts at its own `usage_at_install`. **Asserted structurally too: neither counter table has a `position_id` column** |
| `test_d9_reset_opens_new_epoch_and_carries_forward` | §3.5.1's exact mechanic: prior epoch's `final_value` frozen, `carry_forward_total` accumulated, `life_to_date` continuous across the reset, `current_value` discontinuous |
| `test_d9_no_merge_across_counter_epoch` | A post-reset meter reading lower than the pre-reset final value does not trigger a max-merge |
| `test_d9_authoritative_correction_can_lower_counter` | With all four provenance fields; without any one of them the write is rejected by CHECK |
| `test_d9_exactly_one_open_epoch` | The exclusion constraint holds under concurrent observations |
| `test_d18_enterprise_adds_candidates_never_replaces` | After an enterprise pass over a mission the edge candidate set is **intact**: same count, same ids, no `superseded_by` set on any edge-origin row, no deletions |
| `test_d18_edge_only_candidates_survive_reconnect` | Candidates the edge found and the enterprise did not are present post-reconciliation (13 §15.2 Case 3) |
| `test_d18_edge_detectors_run_with_no_domino_reachable` | Threshold and trending detectors produce candidates with the Domino network path blackholed |
| `test_d18_origin_matches_producer_node` | The CHECK constraint; and no code path sets `origin` other than from `producer_node` |
| `test_d18_candidate_group_preserves_both_origins` | Overlapping enterprise and edge candidates group without either being merged away |
| `test_d18_detector_artifact_digest_mismatch_fails_startup` | A detector does not run degraded on an unverified artifact |
| `test_edge_cannot_author_definitions` | §6.6. The operations are **absent from the edge router**, asserted by route inspection, not by a 403 |
| `test_provisional_identity_usage_attribution` | 13 §15.2 Case 1a/1b/1c: the new item starts at zero, the retired item keeps its hours, in all three sub-cases |
| `test_divergence_budget_exceeds_scripted_patrol` | Every declared budget > 42 days (§8.4); a shorter budget fails CI |
| `test_write_authority_independent_of_connectivity` | No `is_connected()` reachable from any merge; asserted by call-graph inspection (11 §11.4) |

### 10.6 Clock discipline under burst ingest

Document 11 §11.2's suite applies in full and is not restated. What this service adds is the burst:

| Test | Assertion |
|---|---|
| `test_d29_burst_ingest_across_backward_step_preserves_order` | Ingest 9×10⁶ samples (13 §15.3) with `SkewableClock.step_backward(1h)` mid-drain; assert ordering by `(producer_node, monotonic_seq)` is correct **and that ordering by `source_time` would be wrong** — the inversion must be proven to exist |
| `test_d29_dispersion_exceeding_inter_sample_interval_marks_timebase_degraded` | After 42 days of holdover, `dispersion_ms` > the 60-second inter-sample interval → `timebase_degraded`, `TIMEBASE` on every sample, `CAUSAL_ONLY` ordering mode |
| `test_d29_producer_node_prevents_sequence_collision` | Edge sequence 41 and enterprise sequence 41 both survive admission as distinct events. **Remove `producer_node` from the dedup index and this test must fail** |
| `test_d29_known_at_log_is_monotonic_across_step` | `meta.knowledge_log.known_at` is non-decreasing with `knowledge_seq` across a backward step; the UNIQUE index holds |
| `test_d29_resolver_compares_no_source_time` | Call-graph inspection over §5.2's resolver: no `SourceTime` comparison anywhere in the tree |
| `test_d29_ingest_deadlines_are_monotonic` | Adapter `Defer` retry-after and every ingest timeout use `MonotonicDeadline` |

### 10.7 Static gates

Document 11 §11.5's nine gates apply. This service adds five, in the `lint` stage:

1. **No `ts.indicator_value` reference outside `repositories/features.py` and `repositories/indicators.py`.** Guards §7.2's detector rule and prevents a second, unfenced query path.
2. **No `is_current` reference inside `repositories/features.py`.** Guards §6.5.
3. **No `position_id` column, attribute, or dict key in any usage-counter module.** Guards `[D9]` structurally.
4. **No `UPDATE ts.indicator_value SET value` anywhere.** Guards §6.3's append-only property.
5. **No default value for `as_of` or `as_known_at` in any router signature, schema, or manifest for a training-shaped operation.** Guards §5.1.

Plus document 09 §6.2's ten PR jobs unchanged, all blocking, none soft-fail.

---

## 11. Deployment — two Helm variants

Document 01 §12's afloat resident subset explicitly includes Condition & Telemetry. Document 06 §4 scopes the demonstration to **one SSN, as a physically separate deployment rather than a simulated queue**, because *"a simulated disconnect that only delays events does not exercise provisional identity minting, conflict resolution, divergence budgets, or degraded-mode presentation — which are the parts most likely to be wrong."*

### 11.1 One chart, two profiles

**`DECISION` — one Helm chart with a `profile` key and two committed values files, not two charts.**

Document 09 §2.4 fixes "one chart per service." Two charts would fork the templates, and forked templates drift: the edge chart would miss a security-context change, or the enterprise chart would miss a probe fix, and the divergence would be discovered on a hull. One chart with `profile: enterprise | edge` gating template blocks keeps every shared invariant literally shared, and the two values files are the reviewable statement of what differs.

```
services/telemetry/helm/
├── Chart.yaml                    # depends on the _fathom-common library chart
├── values.yaml                   # the shared shape of document 09 §4.4.1
├── values-enterprise.yaml        # profile: enterprise
├── values-edge.yaml              # profile: edge
├── templates/
│   ├── deployment.yaml           # the API workload
│   ├── deployment-worker.yaml    # inbox consumer + indicator computation.  §11.5
│   ├── deployment-detector.yaml  # {{ if eq .Values.profile "edge" }} only.  §7
│   ├── networkpolicy.yaml        # §11.3 — rendered from values, never hard-coded
│   ├── migration-job.yaml        # pre-install,pre-upgrade; backoffLimit: 0
│   ├── configmap.yaml · externalsecret.yaml · service.yaml
│   ├── hpa.yaml                  # {{ if eq .Values.profile "enterprise" }}
│   ├── scaledobject.yaml         # KEDA on consumer lag; enterprise only
│   ├── servicemonitor.yaml
│   └── poddisruptionbudget.yaml  # {{ if gt (int .Values.replicaCount) 1 }}
└── tests/                        # helm-unittest — run against BOTH values files.  §11.6
```

Two Argo CD Applications under `deploy/argocd/`: `telemetry-enterprise` (dev auto-sync, staging and production manual per document 09 §6.3) and `telemetry-edge-<hull>` (manual sync always — a hull is not auto-synced from shore).

### 11.2 Resource profiles

Sized from document 06 §7 and document 13 §2.2's rates. No figure here is invented; each is derived from a cited rate and the derivation is stated (09 §9.5 item 31).

**Enterprise** — fleet-wide ingest at ~5M samples/day plus recomputation write-back.

```yaml
# values-enterprise.yaml
profile: enterprise
deployment:
  producerNode: enterprise          # -> FATHOM_DEPLOYMENT__PROFILE
  assetId: ""                       # MUST be empty on this profile

replicaCount: 3                     # API
resources:
  requests: { cpu: 500m, memory: 1Gi }
  limits:   { cpu: "2",  memory: 4Gi }
  # Ingest is CPU-bound on decode + channel resolution, not I/O-bound: ~5M samples/day
  # (06 §7) with burst concentration at reconnect and sortie end.

workers:
  enabled: true
  replicaCount: 2
  resources:
    requests: { cpu: "1", memory: 2Gi }
    limits:   { cpu: "4", memory: 8Gi }

detectors:
  edgeResident: false               # the ensemble runs as Domino Jobs (§7.1)

autoscaling:
  mode: keda                        # consumer lag, per 01 §11 for event workers
  minReplicas: 2
  maxReplicas: 8
  kedaLagThreshold: 1000

database:
  clusterName: fathom-telemetry-ts  # TimescaleDB, 09 §2.3.  ONE cluster, two schemas [D33]
  name: telemetry
  poolSize: 20

app:
  config:
    stalenessBoundSeconds: 300
    retention:
      rawSampleDays: 90             # then 1-minute continuous aggregate
      minuteAggregateDays: 400      # covers 06 §7's 24-month history at aggregate fidelity
      hourAggregateDays: 1100
      indicatorValueDays: 0         # 0 = never pruned.  See the note below
    outbox:
      minRetentionHours: 168
      pruneRequiresShoreAck: false
      inlinePayloadMaxBytes: 65536  # 11 §2.6; batch payloads always exceed it -> payload_ref
```

**`indicatorValueDays: 0` — indicator values are never pruned, and that is a D22 consequence.** Pruning them would make `as_known_at` unanswerable for any window older than the retention horizon, and a training set assembled last year would become unreproducible. Raw samples can be rolled up because they can be recomputed from aggregates for most purposes and from retained raw objects for unmanned; indicator values *are* the definition-time record. Their purge path is crypto-shredding by classification key (03 §13.1), not retention expiry, which is what satisfies document 09 §8.4's declared-purge-path item without reopening the leak.

**Edge** — one hull, 150 channels at 1/minute (06 §7), single node pool.

```yaml
# values-edge.yaml
profile: edge
deployment:
  producerNode: ""                  # DERIVED: "edge:" + assetId.  §8.1
  assetId: "<the hull's asset_id>"   # REQUIRED. Startup-fatal when absent

replicaCount: 1                     # a hull has one node pool
resources:
  requests: { cpu: 250m, memory: 512Mi }
  limits:   { cpu: "1",  memory: 2Gi }
  # 150 channels at 1/minute = 216,000 samples/day (06 §7).  Two orders of magnitude
  # below the enterprise rate; the binding constraint afloat is storage, not CPU.

workers:
  enabled: true
  replicaCount: 1
  resources:
    requests: { cpu: 500m, memory: 1Gi }
    limits:   { cpu: "2",  memory: 3Gi }

detectors:
  edgeResident: true                # §7
  replicaCount: 1
  classes: [threshold, trending, residual]     # residual iff the artifact exports (§7.1)
  resources:
    requests: { cpu: 500m, memory: 1Gi }
    limits:   { cpu: "2",  memory: 4Gi }
  artifactVolume:
    size: 5Gi                       # exported artifacts, digest-pinned, shore-delivered

autoscaling:
  mode: none                        # HPA/KEDA need metrics infrastructure a hull may not run
poddisruptionbudget:
  enabled: false                    # single replica

database:
  clusterName: fathom-telemetry-ts-edge
  poolSize: 5

app:
  config:
    stalenessBoundSeconds: 3600     # a hull's read models are legitimately staler
    retention:
      rawSampleDays: 0              # NEVER pruned before shore acknowledgement.  See §11.4
      indicatorValueDays: 0
    outbox:
      minRetentionHours: 1440       # 60 days > the scripted 42 (13 §15.1)
      pruneRequiresShoreAck: true   # 11 §2.6 — MANDATORY at the edge  [D28]
    divergenceBudgets:              # §8.4.  All > 42 days
      telemetry_batch:   60d
      sample:            60d
      health_indicator:  60d
      anomaly_candidate: 60d
      usage_counter:     60d
      mission_record:    60d
    degradedMode:
      predictionStalenessHorizonDays: 7   # 03 §11: beyond it, shown as expired, not predicted
```

### 11.3 NetworkPolicy — the profiles differ here most

Document 01 §11's default-deny plus explicit allow, rendered from values and from nothing else (09 §4.4.2).

**Enterprise egress** — exactly document 09 §4.4.2's sanctioned set, no additions:

```yaml
networkPolicy:
  enabled: true                     # NEVER false in any environment
  ingress:
    fromServices: [gateway]         # 01 §5: the gateway composes.  Domino Jobs write back
                                    # THROUGH the gateway (09 §4.4.2), so no domino-compute rule
    fromNamespaces: []
    allowPrometheusScrape: true
  egress:
    toOwnDatabase: true             # fathom-telemetry-ts only
    toEventBus: true                # Redpanda brokers + schema registry
    toServices: [auth, audit, reference-data]    # the ONLY in-namespace egress
    toNamespaces: []
    allowDNS: true
```

**Edge egress** — no path to any enterprise service:

```yaml
networkPolicy:
  enabled: true
  ingress:
    fromServices: [gateway-edge, pma, sync]     # the afloat operator surface, PMA afloat,
                                                # and the coordinator
    fromNamespaces: []
    allowPrometheusScrape: true
  egress:
    toOwnDatabase: true             # fathom-telemetry-ts-edge
    toEventBus: true                # the EDGE Redpanda.  11 §1.3: the relay is never inert
    toServices: [sync, auth, audit] # sync = the coordinator.  auth/audit are EDGE-RESIDENT
    toNamespaces: []                # <- EMPTY.  No cross-namespace, no shore path
    allowDNS: true
    toShore: false                  # this service NEVER opens a ship-to-shore connection
```

Four rules, and the first is the one that must be tested rather than trusted:

1. **The edge instance has no route to any enterprise service, and every byte to shore traverses the `sync` coordinator.** Not `gateway`, not `pdm`, not `registry`, not `reference-data` ashore. A helm-unittest spec asserts that the rendered edge egress peer set contains no enterprise peer and does not contain `gateway`.
   > **Why this matters.** A single convenience egress rule — "just let telemetry call the Registry directly to resolve an item" — makes the edge silently dependent on connectivity. Six weeks dark, that call times out, and either ingest blocks or the resolution is guessed. Document 03 principle 2 already forbids synchronous cross-sub-application calls on a compute path; afloat, the same rule is the difference between a degraded mode and an outage. Every shore-bound interaction goes through a durable outbox drained by the coordinator (11 §9.3), which is the *only* component whose correctness under a six-week partition has been designed.
2. **`reference-data` is absent from edge egress deliberately.** The edge holds a version-pinned replicated snapshot (§7.5) delivered shore-to-ship. Document 09 §4.4.2 already requires reference-data to be cached and *"not a compute-path dependency"*; afloat, caching becomes replication.
3. **`auth` and `audit` are edge egress peers, and this is an extension of document 01 §12's enumerated afloat subset.** Document 03 §4 requires authorization enforced by the receiving sub-application and §15.9 requires provenance recording, neither of which is satisfiable afloat against a shore service. Recorded as **OQ-6**: document 01 §12 should enumerate edge-resident `auth` and `audit`.
4. **`networkPolicy.enabled` is never `false`, in either profile, in any environment** (09 §9.5 item 30). The policy is what converts principle 1 from convention into a CI-testable invariant.

### 11.4 Edge storage — the constraint that actually binds

Document 11 §13 records OQ 9: D28's telemetry storage question is *"only half closed… the absolute edge storage envelope for a six-week subsurface burst needs a number in the capacity model before hull provisioning."* Here is the derivation, from cited figures only.

| Quantity | Value | Source |
|---|---|---|
| Channels | 150/asset | 06 §7 |
| Rate | 1/minute | 06 §7 |
| Samples/day | 150 × 1,440 = **216,000** | derived |
| Scripted disconnection | 42 days | 06 §4, 13 §15.1 |
| Samples accumulated | ≈ **9.07 × 10⁶** | derived; matches 13 §15.3's *"on the order of 9×10⁶"* |

Three stores accumulate, and only the first is bounded by the sample count:

1. **`ts.sample`** — 9.07×10⁶ rows. Compressed TimescaleDB rows at this width are on the order of tens of bytes, so **sub-gigabyte**.
2. **The outbox** — one row per *batch*, not per sample, because events are batch-level (03 §6) and payloads are by reference (11 §2.6). At one batch per channel-hour that is 150 × 24 × 42 ≈ 151,000 envelope rows, each carrying signature, `sync_quality`, and classification. **Small, and small only because of the batch-level and payload-ref decisions.**
3. **Object storage** for `payload_ref` batch payloads — the dominant term, and the one requiring a provisioned figure.

**`DECISION` — the edge declares a provisioned storage envelope, `/readyz` degrades before exhaustion, and the divergence budget's real trigger afloat is bytes, not days.**

```yaml
app:
  config:
    edgeStorage:
      provisionedGiB: <set at hull provisioning>
      readyzDegradeAtFraction: 0.70    # 11 §2.6: "a hull discovers the problem before
                                       # the database stops accepting writes"
      divergenceBudgetBytesFraction: 0.85   # breach -> explicit read-only for telemetry
                                            # ingest ONLY; other aggregates unaffected
```

Per document 11 §9.1's breach rules, all four hold: writes to *that aggregate* refuse with `423` and `type: .../divergence-budget-exceeded`; the operator interface shows a persistent per-aggregate banner; **other aggregates are unaffected** — a telemetry-storage breach must not stop maintenance action recording, which would reintroduce `[D8]` by a different route; and nothing already recorded is discarded. A concrete `provisionedGiB` remains a capacity-model item and is not invented here (**OQ-7**).

### 11.5 The second workload, and why the skeleton grows

Document 09 §4.2's skeleton renders one `deployment.yaml`. This service renders three (two on the enterprise profile).

**`DECISION` — `deployment-worker.yaml` and `deployment-detector.yaml` are added, and an ADR is filed per document 09 §7.5.**

Justification: the API workload's latency budget (06 §7: p95 < 1.5 s for fleet and asset views) and the ingest/computation workload's throughput profile are incompatible in one pod. A nine-million-sample burst drain in the same process as `/features` makes the resolver's latency a function of reconnection timing. Separating them lets KEDA scale the worker on consumer lag while HPA scales the API on request rate (01 §11), which is exactly the split document 09 §2.4 anticipates without providing the template. The detector workload is separate again because afloat it must be independently resource-capped: a detector run must never starve ingest, since ingest is the only irreplaceable function (a missed detection is recoverable ashore; a dropped sample is not).

All three share the chart's security context, probes, image digest, and `Settings`. `/healthz` and `/readyz` are identical across them, with the readiness checks of document 09 §5.6 plus two:

| Check | Fails when |
|---|---|
| `channel_registry_loaded` | The pinned channel registry version is unavailable — the mapper cannot resolve, so the pod must not accept ingest |
| `indicator_definitions_loaded` | The pinned definition set is unavailable — the resolver would silently return `coverage.missing_indicators` for everything |

Both matter most on the edge profile, where the registry arrives by replication and a partial delivery must not present as a healthy pod serving empty features.

### 11.6 Chart tests

`helm unittest` runs against **both** values files, and the suite is not considered passing unless both do:

| Spec | Asserts |
|---|---|
| `networkpolicy_egress_equals_values_enterprise` | Rendered egress peer set **equals** `values-enterprise.yaml`'s declared set exactly — no extra peer, no wildcard (09 §4.4.2, 01 §11) |
| `networkpolicy_egress_equals_values_edge` | The same for the edge profile |
| `networkpolicy_edge_has_no_enterprise_peer` | **§11.3 rule 1.** No enterprise service, no `gateway`, `toNamespaces` empty |
| `networkpolicy_never_disabled` | `enabled: true` in both, unconditionally |
| `edge_requires_asset_id` | `profile: edge` with an empty `assetId` fails template rendering |
| `enterprise_forbids_asset_id` | `profile: enterprise` with a non-empty `assetId` fails rendering |
| `edge_prune_requires_shore_ack` | `pruneRequiresShoreAck: true` on the edge profile, unconditionally (11 §2.6, `[D28]`) |
| `divergence_budgets_exceed_scripted_patrol` | Every declared budget > 42 days (§8.4) |
| `edge_has_no_hpa_or_keda` | `autoscaling.mode: none` afloat |
| `security_context_identical_across_profiles` | Non-root UID 65532, `readOnlyRootFilesystem: true`, `drop: [ALL]`, `seccompProfile: RuntimeDefault` — the shared invariants that a two-chart split would eventually diverge on |
| `migration_hook_backoff_zero` | `backoffLimit: 0` in both (01 §11) |

---

## 12. Explicit DO-NOT list

Each item carries the finding that makes it a defect rather than a preference. A reviewer may cite the number and stop reading.

### 12.1 Point-in-time correctness

| # | Do not | Because |
|---|---|---|
| 1 | **Constrain features on data time only.** Do not add an `as_of`-only feature operation, do not default `as_known_at`, and do not accept a request that omits it | **`[D22]`** — *"`as_of` constrains data time only. Indicator definitions and channel mappings are explicitly recomputed over history, so a model trained at `as_of=2025-03-01` receives values computed by a definition authored in 2026 by someone who had seen the 2025 failures."* The result is excellent offline metrics and field failure, undetectable from outside. §5.1, §5.8 |
| 2 | **Read `is_current` in the bitemporal resolver.** Not as a filter, not as an optimization, not "to skip superseded rows" | **`[D22]`** via §6.5 — it collapses every historical query to the present while all three fences remain visibly present in the SQL. This is the one-line reintroduction of the finding. `test_d22_resolver_ignores_is_current` |
| 3 | **Drop F2 or F3 as redundant.** They are not. F2 selects *which definition*; F3 selects *which computation of it* | **`[D22]`** — F2 alone lets late-arriving data leak through a definition that predates it; F3 alone lets a later-authored definition win the window. §5.2, and both fence-removal tests in §10.2 |
| 4 | **`UPDATE ts.indicator_value SET value`.** A recomputation inserts | **`[D22]`** — an in-place update destroys the definition-time history and makes every prior training set unreproducible. §6.3 |
| 5 | **Repair data at ingest** — interpolate a gap, drop an outlier, correct a calibration bias, or normalize a confounder | §4.6 — repair is a *definition-time* act. Performed at ingest it is unversioned, invisible to `as_known_at`, and irreversible. Every repair is available as a versioned definition operator. `test_ingest_never_repairs` |
| 6 | **Introduce a mechanism that can change a historical value without a version and a `published_seq`** | §6.2's list *is* the review checklist. `reduction_version` (§4.4) is on it because downsampling was exactly such a mechanism and was not on the finding's list |
| 7 | **Prune indicator values on a retention schedule** | §11.2 — it makes `as_known_at` unanswerable beyond the horizon. The purge path is crypto-shredding (03 §13.1), not expiry |
| 8 | **Use `occurred_at` as a feature timestamp** | 03 §5.4, **`[D22]`** — *"feature computation must not use `occurred_at` for any value authored with hindsight."* Feature time is `window_end` (data) and `known_at_seq` (knowledge) |

### 12.2 Identity, counters, and attribution

| # | Do not | Because |
|---|---|---|
| 9 | **Key a usage counter on `position_id`**, or merge across `counter_epoch`, or make max-merge unconditional | **`[D9]`** — *"Keying on position rather than item would credit a new item with its predecessor's hours. Unqualified max-merge makes one sensor glitch permanent."* All three bugs, §3.5.1. There is no `position_id` column on either counter table, and a static gate keeps it that way |
| 10 | **Bind a `source_tag_mapping` directly to `installed_item_id`** unless the sensor physically travels with the item | **`[D9]`** in its telemetry form — a position-wired sensor bound to an item attributes the replacement pump's vibration to the pump that was landed. Resolution is through Registry configuration **at the sample's data time**. §3.1.3(b), §4.5 |
| 11 | **Conflate `position_id` with `installed_item_id`** anywhere | 03 §3.3, `[C10, D9]` — the inherited-degradation defect the whole model exists to prevent |
| 12 | **Drop an unmapped tag, or attribute a sample by guess** | §4.5 — a dropped reading is an unrecoverable lost observation, and an unmapped tag is the integration surface's normal early state, not garbage. Quarantine, and `installed_item_id IS NULL` |
| 13 | **Mint any identifier other than `installed_item_id` at the edge** | 03 §2.4, 11 §8.2 — *"canonical identity is never re-minted."* Not `asset_id`, not `position_id`, not `channel_key` |

### 12.3 The edge

| # | Do not | Because |
|---|---|---|
| 14 | **Make candidate generation enterprise-only**, or let an enterprise pass replace, supersede, prune, or deduplicate-away an edge candidate | **`[D18]`** — *"afloat there is no candidate source at all. Review degrades to the open-ended authoring the design declares unreliable. Submarines — least instrumented, highest consequence — contribute zero confirmed tags."* The enterprise **adds**. §7.4 |
| 15 | **Author an indicator definition, channel mapping, or detector version at the edge** | §6.6 — three reasons, and the third is that it would give the knowledge log two writers on two clocks and make `as_known_at` resolution a cross-node timestamp comparison. **`[D29]`** arriving through the leakage remedy |
| 16 | **Give the edge instance an egress rule to any enterprise service** | §11.3 rule 1 — one convenience rule makes the edge silently connectivity-dependent, and six weeks dark it either blocks or guesses. Everything shore-bound goes through the coordinator |
| 17 | **Mark edge-drained records `X-Backfill: true` or `replay: true`** | 11 §9.3 — *"Edge records are live facts arriving late, not replay. They must fire their normal side effects ashore."* Suppressing them removes the mission reviews the patrol is supposed to trigger, which is `[D18]` from the other direction |
| 18 | **Set a divergence budget below the scripted patrol length** | 11 §9.1 — the hull goes explicitly read-only halfway through the patrol and `[D8]`/`[D18]` return wearing a compliance badge. §8.4, all budgets 60 days |
| 19 | **Bind write authority to liveliness.** No `is_connected()` in any merge decision | 03 §11, 08 §3.4 — *"DDS binds OWNERSHIP to LIVELINESS, so a dark ship would lose authority over the mission records it alone can produce"* |
| 20 | **Run a detector on an unverified artifact, or fetch one at runtime** | §7.3, 01 §12, `[D26]` — nothing is retrieved or installed at container start. A digest mismatch fails startup; the detector does not run degraded |
| 21 | **Treat `completeness = 0` as equivalent to `not_observed`** | 04 §3 — *"consumers can distinguish 'no fault observed' from 'not observed'."* A dark submarine did not observe; a dead channel observed nothing. Different facts, different downstream inferences. §3.2 |

### 12.4 Time, events, and ordering

| # | Do not | Because |
|---|---|---|
| 22 | **Let a wall clock arbitrate anything** — ordering, dedup, merge, tie-breaks, lease expiry, retry backoff, `changed_since` cursors | **`[D29]`** — Ubuntu STIG **V-260520** mandates `makestep 1 -1`, and the step fires precisely when a reconnecting hull drains nine million samples. Order on `(producer_slug, producer_node, monotonic_seq)` or the HLC. §5.4 states the single licensed timestamp comparison and why it is licensed |
| 23 | **Key dedup on two parts.** `(producer, monotonic_seq)` is ambiguous for this slug | 03 §5.4, 11 §4.2 — this service *is* the reason `producer_node` exists: two deployment instances of one slug, each minting its own sequence, colliding on the dedup key, one silently dropped. §2.2, §8.1 |
| 24 | **Emit per-sample events** | 03 §6 — *"Per-sample events would constitute an event storm carrying no additional information."* At ~5M samples/day (06 §7) it is a category error, not a scaling concern |
| 25 | **Inline sample payloads in an event or in the outbox** | `[D27]`, `[D28]`, 11 §2.6 — nine million samples do not go through the broker, and the edge outbox must not double telemetry storage. `payload_ref` always |
| 26 | **Compact any Telemetry topic** | `[D5]` for the key, and §8.2(c) for the reason: compacting `health_indicator` discards the recomputation history definition-time correctness is built from, and compacting `usage_counter` discards either a reset or an update, which is `[D9]`'s third bug |
| 27 | **Set a compaction key equal to a partition key** | `[D5]` — the general rule, enforced by the outbox CHECK constraint (11 §2.2) |
| 28 | **Rebuild a read model from the event bus** | `[D5]` — retention is 7/30 days deliberately. `changed_since` on `known_at_seq`. §9.4 |
| 29 | **Publish an event type absent from document 03 §6's catalog** | 09 §8.2, 13 §14.2 — including a channel-mapping event, however much document 04 §3 wants one. §3.1.6 records the disciplined handling and **OQ-2** requests the contract change |
| 30 | **Record inbox receipt before processing** | **`[D2]`** — only rows with `processed_at` set suppress redelivery. Applied to `configuration.baseline_changed` it silently prevents re-attribution, and document 11 §3.2's comment template is mandatory verbatim |

### 12.5 Boundaries and domain honesty

| # | Do not | Because |
|---|---|---|
| 31 | **Assert any ICAS channel name, tag format, point type, sampling convention, or quality-flag value** | 07 §10 lists the ICAS channel taxonomy as confirmed unpublished; 07 §1's prohibition on fabrication is operative — *"Fabricated schema detail is worse than an acknowledged gap, because a reviewer recognises it immediately."* §2.5 |
| 32 | **Add any other Navy schema detail from general knowledge** | 09 §9.5 item 32 — 3-M code sets, COSAL structure, FLIS, identifier formats come from document 07 |
| 33 | **Invent a quantity** — a rate, a volume, a channel count, a retention horizon, a latency budget | 09 §9.5 item 31, `[D37]` — cite 06 §7 or 13 §2, or derive from them and state the derivation (§11.4) |
| 34 | **Write to another service's database, or let a Domino Job write to this one** | `[D10, C7]` — detector and indicator results enter through the bulk, idempotent, fenced operations of §9.3. A Domino Job is an API client, never a database client |
| 35 | **Call another sub-application synchronously on a compute path** | 03 principle 2 — the mapper reads a *local* configuration read model, not the Registry API. Afloat this is the difference between degraded mode and outage (§11.3) |
| 36 | **Own a second database** | `[D33]`, 03 §15.13 — `ts` and `meta` are schemas of one owned cluster, and the outbox is in that same cluster (11 §2.7) |
| 37 | **Suppress a decoy channel from the feature surface** | 13 §7.3 — *"Spurious feature selection must have something to select."* Publish the role; do not hide the channel |
| 38 | **Fabricate an `attribution_weight` for a shared channel** | 13 §7.3 — attribution ambiguity is real and is carried as data. NULL where unresolvable, never 1.0 |
| 39 | **Raise an equipment-degradation candidate from a stuck sensor** | 13 §9.6 — *"a model that predicts equipment failure from a dead sensor is making the error this case exists to expose."* `attributed_to = 'sensor'`, surfaced, excluded from the equipment stream. §3.7 |
| 40 | **Let a detector read `ts.indicator_value` directly** | §7.2 — a private query path is a path that can see what `/features` would have fenced |

---

## 13. Open questions for the orchestrating process

Recorded rather than resolved locally, because each affects a document this one is downstream of.

| # | Question | Impact | Interim position |
|---|---|---|---|
| **OQ-1** | **The ICAS channel taxonomy is unavailable** (07 §10). Documents 01 §5/§6.1 and 04 §3 reference ICAS; no schema detail exists in document 07 | A federation adapter cannot be designed, and demonstration credibility with a NAVSEA reviewer rests on channel semantics being plausible | §2.5: opaque program-defined channel keys, a `quantity` vocabulary drawn from 13 §7.4, and **nothing asserted about ICAS**. If it matters, add it to document 07 §10's follow-up list |
| **OQ-2** | **RESOLVED.** Document 03 §6 now carries `channel_mapping.version_published` (consumers `pdm`, `pma`), added against this finding. | — | The `changed_since` / `channel_registry_version` fallback described in §3.1.6 remains correct for consumers that don't subscribe to the new event; it is not superseded, only supplemented |
| **OQ-3** | **`usage_counter.updated` and `.reset` are one aggregate, hence one topic, and cannot share a compaction key** | The most natural state-carrying topic in this service cannot be compacted | §8.2(c): not compacted, 30-day retention, `changed_since` rebuild. Compaction requires `reset` to become its own aggregate — a document 03 §6 change |
| **OQ-4** | ~~**Document 10 §4.5's `EventScope` has no `MISSION` member**~~ **[RESOLVED.]** `10-shared-packages.md` §4.5 now has `EventScope.MISSION` and a `SCOPE_SUBJECT_FIELD` entry mapping it to `mission_id` | Closed — no correction needed | **Resolved.** `mission.completed` is constructible from the shared schema package as published |
| **OQ-5** | **RESOLVED.** Document 03 §6 now carries `installed_item.identity_resolved` as a Registry row on the existing `installed_item.*` topic, added against this finding. | — | §8.3's consumption path (resolve via `IdentityAliasResolver`) is unchanged; the event just has a catalog row now |
| **OQ-6** | **Document 01 §12's afloat subset does not enumerate `auth` or `audit`**, while 03 §4 requires local authorization and §15.9 requires provenance recording | The edge NetworkPolicy declares peers the architecture has not sanctioned | §11.3 rule 3: declare them, flag it. Document 01 §12 should enumerate edge-resident `auth` and `audit` |
| **OQ-7** | **The edge storage envelope has no provisioned figure** — document 11 §13 OQ 9, half-closed | Hull provisioning is blocked; the byte-based divergence trigger has no threshold | §11.4 gives the derivation (≈9.07×10⁶ samples over 42 days, sub-gigabyte for `ts.sample`, object storage dominant) and the mechanism. The number belongs in the capacity model |
| **OQ-8** | **`min_completeness` per indicator has no program-sourced value** | Below-floor suppression is the difference between a sparse feature and a fabricated one, and the floor determines which | Bundle-owned per family, like document 13 §7.4's parameters. Do not default it in code; `POST /indicator-definitions` requires it |
| **OQ-9** | **Whether tier-2 residual detectors export to the edge runtime** — document 06 §4's assumption, HIGH confidence, with a stated fallback | Afloat candidate quality | §7.1: `residual` is conditional on export. Fallback per 06 §4: threshold and trending only, *"and accept lower candidate quality on the disconnected leg."* Test both configurations |
| **OQ-10** | **Relay shard count** (11 §13 item 8) for the highest-volume producer in the system | Per-partition ordering under burst drain | Default 8 enterprise, **1 edge** (one hull, one asset, one partition — concurrency buys nothing and risks the ordering guarantee). Drain-to-empty migration path |
| **OQ-11** | **`sync_quality` retention at Telemetry's event volume** (11 §13 item 10) | Audit must accept a per-event attestation record at this service's rate | Batch-level events keep the rate at ~151,000 envelopes per hull per 42 days (§11.4), not per-sample. Audit's build document should confirm |
| **OQ-12** | **Idempotency retention for edge-reachable operations** (09 §10 item 5, 11 §13 item 7) | A hull's retry window is weeks, not 24 hours | 60 days on the edge profile's bulk write paths, matching the divergence budget. Confirm with document 11 |

---

## 14. Definition of Done

The shared Definition of Done in [09 §8](09-monorepo-and-conventions.md#8-the-shared-definition-of-done) applies **in full and nothing is removed**, as does document 11 §14's per-consuming-service list (items 9–18). This service adds the following. Copy the whole set into `services/telemetry/README.md` and tick it there.

### 14.1 The three the prompt for this document names, first because they are the gates

- [ ] **The bitemporal feature API leakage test passes.** `tests/leakage/test_definition_time.py::test_d22_frozen_definition_time_recompute_is_identical` is green, including step 7's proof that the leakage path exists — a vacuous test is a failing test. All nine tests in §10.2's table are green, and `tests/leakage/` runs as its own blocking CI job. *(§5, §6, `[D22]`)*
- [ ] **Both Helm variants deploy.** `helm lint`, `helm template | kubeconform --strict`, and `helm unittest` are green **against both `values-enterprise.yaml` and `values-edge.yaml`**, all eleven specs in §11.6 pass, and both Argo CD Applications are committed under `deploy/argocd/`. The edge variant has been deployed to a network-partitioned target and has completed document 13 §15's scripted 42-day scenario against its golden file. *(§11, 06 §4, 01 §12)*
- [ ] **Channel registry versioning is tested.** All ten tests in §10.4 are green, including `test_position_wired_resolution_at_data_time` (the anti-inherited-degradation test) and `test_mapping_bitemporal_correction`. *(§3.1, `[D22]`, `[D9]`)*

### 14.2 Point-in-time correctness

- [ ] `GET /features` implements §5.1's signature exactly, with **both** `as_of` and `as_known_at` required and `latest` an explicit literal. No default anywhere in the router, the schema, or a manifest for a training-shaped operation.
- [ ] All three fences (F1, F2, F3) are present in the resolver, and **both fence-removal tests** fail when their fence is disabled.
- [ ] `is_current` appears nowhere in `repositories/features.py`; the static gate enforces it; `test_d22_resolver_ignores_is_current` is green.
- [ ] `coverage.missing_indicators` distinguishes all four reasons, and `not_defined_at_as_known_at` is emitted rather than a null feature.
- [ ] `resolution_token` round-trips byte-identically and returns `409` rather than a near-enough resolution.
- [ ] `POST /features/batch` stamps one resolution across the whole set.
- [ ] `GET /health-indicators` requires `as_known_at` on the same terms (§5.8).
- [ ] Every artifact in §6.2's table has a version column and a `published_seq`, and the table is reproduced in the README as the review checklist.
- [ ] `ts.indicator_value` has no `UPDATE ... SET value` path; the static gate enforces it.
- [ ] `indicatorValueDays: 0` in both profiles, with the crypto-shredding purge path declared per document 09 §8.4.

### 14.3 Ingest

- [ ] Exactly **three** `IngestAdapter` implementations, over **one** `CanonicalSample` model, with `map()` and `assess()` shared and not overridable. *(04 §3)*
- [ ] Every test in §10.3 green, **including `test_ingest_never_repairs` over the whole document 13 corpus**.
- [ ] `value IS NULL` for absence throughout; no sentinel value anywhere.
- [ ] `observation_state` set on every batch and every mission; `gap_intervals` enumerated, never summarized.
- [ ] `reduction_version` registered in the knowledge log and non-null on every unmanned batch; raw 10 Hz objects retained and referenced.
- [ ] Unmapped tags quarantined and surfaced on `GET /quality`; sample counts reconcile.
- [ ] `mnar_indicator` computed, published on `coverage`, and non-zero on the shipped corpus.

### 14.4 Edge and events

- [ ] `producer_node` is `enterprise` or `edge:<asset_id>` per document 03 §5.4's literal form, on every envelope, from a single `Final` constant; `assetId` is startup-fatal when absent on the edge profile.
- [ ] Dedup and ordering use `(producer_slug, producer_node, monotonic_seq)` everywhere; `test_d29_producer_node_prevents_sequence_collision` fails if `producer_node` is removed from the index.
- [ ] All six document 03 §6 event types published from **both** profiles, with `events/catalog.py` `PUBLISHES`/`CONSUMES` equal to `helm/values.yaml` equal to document 03 §6's Telemetry rows in both profiles. `python tools/check_event_catalog.py` exits 0.
- [ ] No topic compacted; the reasoning for each recorded in the README (§8.2(c)).
- [ ] Twelve conflict policies declared or explicitly defaulted; the registry's startup enumeration passes; **every divergence budget exceeds 42 days**.
- [ ] Every test in §10.5 and §10.6 green, including `test_d18_enterprise_adds_candidates_never_replaces`, `test_d9_reset_opens_new_epoch_and_carries_forward`, and `test_d29_burst_ingest_across_backward_step_preserves_order`.
- [ ] `test_edge_cannot_author_definitions` green by **route inspection**, not by a 403.
- [ ] Edge NetworkPolicy contains no enterprise peer and no `gateway`; `toNamespaces` empty; asserted by helm-unittest.
- [ ] No `position_id` in any usage-counter module; static gate enforces it.

### 14.5 Domain honesty and governance

- [ ] **No ICAS channel name, tag format, point type, or quality-flag value appears anywhere in the service, its schemas, its fixtures, or its documentation.** §2.5's posture is restated in the README with the document 07 §10 citation.
- [ ] Every quantity in the service and its chart traces to document 06 §7, document 13 §2, or a stated derivation from them (§11.4).
- [ ] All five static gates of §10.7 implemented, plus document 11 §11.5's nine.
- [ ] All five conformance categories green; consumer-driven tests present from all four declared consumers; this service's consumer-driven tests contributed into `registry`'s suite.
- [ ] Both agent manifests pass manifest conformance; `purpose` reviewed for overlap.
- [ ] Every **OQ** in §13 the service had to resolve locally is recorded in the README as a local resolution and raised for a program decision (09 §8.7).
- [ ] ADRs filed for the extensions in §15 — the second and third workloads (§11.5), the fifth test tier (§10.1), and `as_known_at` on `/health-indicators` (§5.8).

---

## 15. Corrections and extensions to the source documents

Each is a defect or a gap in the cited document, not a decision of this one, except where marked **extension** — those are decisions of this document requiring an ADR per document 09 §7.5.

| # | Document | Issue | This document's handling |
|---|---|---|---|
| 1 | **11 §4.2** | Illustrates `producer_node` as `telemetry@ashore-1` / `telemetry@ssn796`. Document 03 §5.4 now specifies `"enterprise" \| "edge:<asset_id>"` | Follows document 03 (09's front-matter "Precedence" row). Document 11 should absorb the literal form. §2.2, §8.1 |
| 2 | **10 §4.5** | ~~`EventScope` has no `MISSION` member and `SCOPE_SUBJECT_FIELD` no mission entry; its `dedup_key` is the two-part `(producer.slug, clock.monotonic_seq)`; the envelope has no `producer_node`.~~ **[RESOLVED, both halves.]** `producer_node` exists and `dedup_key`/`precedes` are three-part, matching `11-outbox-sync-library.md`'s `DedupKey`; `EventScope.MISSION` and its `SCOPE_SUBJECT_FIELD` entry exist too (OQ-4, also resolved) | Closed — no correction needed | **Resolved**, both the envelope and the three-part key |
| 3 | **04 §3** | Lists `GET /health-indicators?...&as_of=` with no `as_known_at`, which is a leak beside a leak-free `/features` | **Extension.** `as_known_at` added and required. §5.8, ADR required |
| 4 | **04 §3** | Lists `POST /ingest/telemetry`, `/ingest/usage`, `/ingest/indicators`, `/ingest/detections` — an RPC shape document 03 §4 does not sanction (`[C23, C24]`) | Resource-oriented forms: `POST /telemetry-batches`, `/usage-counter-observations`, `/health-indicator-values`, `/anomaly-candidates`. Document 03 §4 prevails per document 04 §1. §9.3 |
| 5 | **04 §3** | Requires a mapping change to be "a versioned event"; document 03 §6's catalog has no such event | Versioned entity + `changed_since` + `channel_registry_version` on `health_indicator.computed`. No uncatalogued publication. **OQ-2**, §3.1.6 |
| 6 | **04 §3** | Says nothing about `as_known_at` at all, so its statement of point-in-time correctness is D22's defect as written | §5 supplies the corrected design. Document 04 §3 should be amended in the tranche-3 remediation |
| 7 | **01 §12** | Enumerates the afloat subset without `auth` or `audit`, while document 03 §4 requires local authorization and §15.9 provenance recording | **Extension.** Declared as edge egress peers. **OQ-6**, §11.3 |
| 8 | **09 §4.2** | The per-service skeleton renders one `deployment.yaml`; this service needs three | **Extension.** `deployment-worker.yaml` and `deployment-detector.yaml`. §11.5, ADR required |
| 9 | **09 §4.7** | Four test tiers; the leakage suite belongs in none of them and must not be selectable away | **Extension.** `tests/leakage/` as a fifth tier and its own blocking CI job. §10.1, ADR required |
| 10 | **11 §13 OQ 9** | The edge telemetry storage envelope is half-closed | §11.4 supplies the derivation and the mechanism; the provisioned figure remains a capacity-model item. **OQ-7** |
| 11 | **06 §7 / 13 §2.2** | The unmanned row says "downsampled at ingest to 1 Hz" without naming the reduction, which reads as a single statistic | §4.4 emits a fixed tuple (mean, min, max, count, rms, peak) as separate bound channels, and versions the reduction. A single mean would hide both clipping and peaks (13 §9.2) |


