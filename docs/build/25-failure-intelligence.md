# Build 25 — Failure Intelligence

| | |
|---|---|
| **Status** | Draft |
| **Slug** | `failure-intel` (document [03 §3.1](../architecture/03-integration-contracts.md)) |
| **Purpose** | Build specification for the sub-application that determines *why* components fail — causal hypotheses with adjudicated evidence, failure-mode attribution, and the versioned causal feature definitions consumed by PdM's tier-3 models |
| **Governing framing** | [04 §9](../architecture/04-subapplication-architectures.md): **outputs are adjudicated hypotheses with explicit evidence strength, never automated conclusions.** Every mechanism in this document exists to make that structurally true rather than culturally hoped-for |
| **Resolves** | **D21** (confounded causal loop) at the consuming end — 03 rev 2 supplied `triggering_driver` / `triggering_prediction_id` / `policy_version`; this document specifies the runtime checks that *use* them. Also **D20** (the undeclared PdM↔Failure-Intelligence cycle), **D23** (the unadjudicated causal back channel), and doc 12's **OD-6** |
| **Primary technical sources** | [04 §9](../architecture/04-subapplication-architectures.md) in full; [05 D1, D20, D21, D22, D23](../architecture/05-architecture-review-findings.md); [06 §2](../architecture/06-demo-decisions-and-assumptions.md); [08 §2](../architecture/08-standards-alignment.md) |
| **Binding contracts** | [03 §3.3](../architecture/03-integration-contracts.md), [03 §4](../architecture/03-integration-contracts.md), [03 §5.4](../architecture/03-integration-contracts.md), [03 §6](../architecture/03-integration-contracts.md), [03 §7.1](../architecture/03-integration-contracts.md), [03 §7.2](../architecture/03-integration-contracts.md), [03 §7.2.1](../architecture/03-integration-contracts.md), [03 §14](../architecture/03-integration-contracts.md), [03 §15](../architecture/03-integration-contracts.md) |
| **Depends on** | [09 — Monorepo and Conventions](09-monorepo-and-conventions.md), [10 — Shared Packages](10-shared-packages.md), [11 — Outbox and Sync](11-outbox-sync-library.md), [12 — Reference Data / Unified Taxonomy](12-reference-data-taxonomy.md), [13 — Synthetic Data Generator](13-synthetic-data-generator.md) |
| **Classification** | Internal. The service operates at U for the synthetic demonstration ([03 §12](../architecture/03-integration-contracts.md)) |

---

## 1. Purpose and scope

**Purpose**, per [04 §9](../architecture/04-subapplication-architectures.md): *"Determine why components fail, using confirmed anomaly tags, mission data, and maintenance findings, and publish adjudicated causal findings to Predictive Maintenance and Design Advisory."*

### 1.1 The framing that governs every other section

Document 04 §9 states it as the sub-application's most important decision, and it is quoted here in full because everything below is an implementation of it:

> **"Outputs are adjudicated hypotheses, not automated conclusions.** This is the most important framing decision in the sub-application and it should be stated plainly in program material. Causal inference from observational data, without designed interventions, yields hypotheses of varying strength — not established causes. The sub-application therefore produces candidate findings with explicit evidence and strength, which an engineer adjudicates before publication. Presenting algorithmically derived causes as established fact to a design authority would be both wrong and, on first contradiction, fatal to the program's credibility."

Three consequences are load-bearing and are built as mechanisms, not as guidance:

1. **No hypothesis is published without an adjudication record** naming a human, a claim lease, and an authority class (§5.2).
2. **The operator- and engineer-facing statement text is generated from a band-keyed template, never authored free-hand** (§4.5). Causal verbs are unlocked only at the top strength band, and a lint gate enforces it.
3. **No method may run against a population containing model-assigned interventions unless it declares and satisfies a treatment-assignment strategy** (§3.1). This is D21's remedy expressed as a runtime gate that refuses, not as a policy statement that is remembered.

### 1.2 Ownership boundary

**Owns** ([04 §9](../architecture/04-subapplication-architectures.md)):

- Causal hypotheses, their evidence, their computed strength, and their adjudication state.
- **Attributions** — the binding of an observed failure to a failure mode — and, per [08 §2.8](../architecture/08-standards-alignment.md), the **arbitration record** when a PMA signature tag and a Scheduling findings coding disagree.
- The engineering adjudication workflow for findings, and **sole authority to approve extensions to the unified taxonomy's content**.
- The versioned `CausalFeatureSet` published to PdM.
- Negative findings — hypotheses examined and found unsupported — retained permanently.

**Does not own:**

| Not owned | Owner | The precise boundary |
|---|---|---|
| The taxonomy itself — registry, versioning, publication | Reference Data | FI owns the *content decision*; Reference Data owns the *register*. §6 |
| Tag assignments | Post-Mission Analysis | FI consumes `anomaly_tag.confirmed` / `.rejected`; it never authors a tag |
| Findings codings | Maintenance Execution & Scheduling | Stored as filed, in 3-M codes. FI reconciles at read time, never normalises on write |
| Telemetry, health indicators, indicator definitions | Condition & Telemetry | FI references definitions with their `definition_version` and definition-time (D22) |
| Predictions, model bindings, tier assignment | PdM | FI publishes feature *definitions*; PdM decides what to bind |
| Redesign recommendations and business cases | Design Advisory | FI supplies the evidence; it does not cost it or recommend |

### 1.3 In scope

1. The four aggregates of [04 §9](../architecture/04-subapplication-architectures.md) — `FailureMode` (a local reference, §2.2), `CausalHypothesis` (§2.3), `Attribution` (§2.5), `CausalFeatureSet` (§2.6) — plus the three the design requires and 04 §9 leaves implicit: `DiscoveryRun` (§2.7), `TreatmentCensus` (§2.8), and `AdjudicationRecord` (§5.2).
2. The **method portfolio** (§3), with a declared treatment-assignment strategy, identifiability preconditions, and an explicit failure mode per method.
3. The **evidence-strength scale** (§4) as a structured, computed, versioned artifact.
4. **Causal feature admission** (§5) and the structural prevention of a weak hypothesis propagating into operational predictions.
5. **Taxonomy extension authority** (§6) — the exact Reference Data API interaction and the `taxonomy_version` propagation rules.
6. **Negative findings retention** (§7) and the anti-rediscovery mechanism.

### 1.4 Out of scope

- **Model training and model artifacts.** Discovery executes in Domino (`models/causal/`); the artifacts live in Domino's registry. FI records run references and ingests results through a bulk fenced API operation, never a direct datastore write ([09 §9.1](09-monorepo-and-conventions.md) item 1, D10/C7).
- **Any edge profile.** [11 §—](11-outbox-sync-library.md) places `failure-intel` in the enterprise-only set. The outbox, inbox, and clock discipline are still implemented without exception (obligation 11, [03 §15](../architecture/03-integration-contracts.md)).
- **Agent proposal intake.** [04 §9](../architecture/04-subapplication-architectures.md) lists no `POST /proposals` on this sub-application and none is added. FI therefore publishes no `fathom.failure-intel.proposal.v1` topic. Agents read FI through `x-agent-eligible` GET and compute-only POST operations (§8) and propose to *Reference Data*, not to FI.
- **Deciding what a taxonomy entry's code or structure is.** FI approves content; Reference Data authors the register (§6, doc 12 DO-NOT-6 in mirror image).

### 1.5 The two cycles, declared

Finding **D20** records *"an undeclared PdM↔Failure-Intelligence cycle."* It is declared here, and it is broken by a typed rule rather than by sequencing.

```
      causal_feature_set.updated (definitions)
   FI ─────────────────────────────────────────────▶ PdM
      ◀─────────────────────────────────────────────
      prediction.updated (TREATMENT ASSIGNMENT ONLY)
```

[04 §9](../architecture/04-subapplication-architectures.md) fixes the second edge's semantics exactly: *"`prediction.updated` is consumed for one purpose only: to record which population received model-assigned intervention, so that comparative population analysis can condition on treatment assignment. **It is never used as evidence for a causal finding.**"*

Enforced three ways, none of which is a convention:

| Control | Mechanism |
|---|---|
| Predictions cannot become evidence | `evidence_record.kind` has no `prediction` member, and a CHECK constraint plus an API-boundary rejection refuse it (§2.4). The `Proposal` evidence vocabulary of [03 §7.2](../architecture/03-integration-contracts.md) *does* admit `prediction`; FI's hypothesis evidence deliberately does not |
| Method code cannot reach the prediction read model | The prediction projection lives in schema `failure_intel_treatment`, reachable only through `population.treatment`. `importlinter.ini` forbids `fathom_failure_intel.methods.* -> fathom_failure_intel.readmodels.prediction` and `-> ...repositories.*` |
| The loop cannot feed itself unnoticed | The **feedback-provenance check** (§3.2), which refuses or restricts when the analysis window's interventions were assigned by a policy that already consumed the feature under examination |

The second cycle is FI↔Reference Data: FI approves vocabulary extensions and then consumes the published version (§6). It is acyclic in *authority* — FI never publishes a version — and is therefore not a correctness hazard, only a sequencing one.

---

## 2. Data model

PostgreSQL. **One logical database**, schema `failure_intel` for domain state and schema `failure_intel_treatment` for the treatment-assignment projection — two schemas of one owned cluster, per obligation 13 ([03 §15](../architecture/03-integration-contracts.md), D33). Object storage for discovery-run artifacts and evidence bundles. Migrations per [09](09-monorepo-and-conventions.md).

Five invariants govern the whole schema. They are stated before the tables because every table obeys them.

| | Invariant | Why |
|---|---|---|
| **I1** | **No taxonomy content is stored, anywhere, beyond `(lineage_id, taxonomy_version)` and a read-through cache.** | Doc 12 DO-NOT-1 / finding C8. Enforced by doc 12's `tax-single-source` monorepo scan, to which this service contributes |
| **I2** | **Every label, attribution, hypothesis, and feature entry carries `taxonomy_version`.** | [08 §2.8](../architecture/08-standards-alignment.md) non-negotiable 1. There is no unversioned row |
| **I3** | **No `CausalHypothesis` row may exist without a `treatment_census_id`.** `NOT NULL`, no default. | D21. A hypothesis whose treatment-assignment posture is unrecorded is not a hypothesis, it is a correlation with a UUID |
| **I4** | **`strength_band` is computed, never authored.** A human adjudicator may lower it; no path raises it. | [04 §9](../architecture/04-subapplication-architectures.md): strength must be *"expressed consistently"* across two consumers making different decisions |
| **I5** | **Nothing is ever deleted or overwritten.** Corrections are new rows with a supersession link; negative findings are retained permanently (§7). | [04 §9](../architecture/04-subapplication-architectures.md): *"Rejections and negative findings are retained."* Plus obligation 9's provenance duty |

### 2.1 Enumerations

```sql
CREATE SCHEMA failure_intel;
CREATE SCHEMA failure_intel_treatment;

-- §3: how a method handles treatment assignment. NO DEFAULT, deliberately (§3.1).
CREATE TYPE failure_intel.treatment_handling AS ENUM (
    'not_applicable',              -- permitted ONLY where contrast_arity = 1 (§3.1)
    'treatment_as_node',           -- structure learning: intervention is an explicit node
    'restricted_to_policy_frozen', -- analysis restricted to the policy-frozen stratum (06 §2)
    'propensity_modeled',
    'ipcw_corrected',
    'propensity_and_ipcw'
);

-- §3.2: the gate's verdict on one (method, population) pair.
CREATE TYPE failure_intel.gate_verdict AS ENUM (
    'proceed',            -- census shows no model-assigned and no unknown-driver treatment
    'proceed_corrected',  -- treatment present, declared strategy satisfied
    'restricted',         -- population rewritten to the policy-frozen stratum, re-censused
    'refused'             -- run recorded, no hypothesis emitted
);

-- §2.8: how one maintenance action's driver classifies. Unknown is NEVER policy-independent.
CREATE TYPE failure_intel.driver_class AS ENUM (
    'model_assigned',       -- a prediction contributed to the decision
    'policy_independent',   -- periodicity, casualty, or access-only opportunism
    'unknown'               -- driver absent, or a value not in the declared mapping. Fail-safe
);

CREATE TYPE failure_intel.adjudication_state AS ENUM (
    'draft', 'under_analysis', 'awaiting_adjudication',
    'published',        -- an adjudicated hypothesis, at its computed band
    'unsupported',      -- examined, evidence does not support it. RETAINED (§7)
    'refuted',          -- examined, evidence contradicts it. RETAINED (§7)
    'withdrawn',        -- the question was ill-posed. RETAINED, with the reason
    'superseded'        -- replaced by a later hypothesis over the same fingerprint (§7.2)
);

CREATE TYPE failure_intel.strength_band AS ENUM ('S0','S1','S2','S3','S4');   -- §4

CREATE TYPE failure_intel.finding_class AS ENUM
    ('supported', 'unsupported', 'refuted', 'superseded');

CREATE TYPE failure_intel.agreement_class AS ENUM
    ('both', 'pma_only', 'maintenance_only', 'neither');   -- doc 12 §9.1

CREATE TYPE failure_intel.feature_standing AS ENUM
    ('monitored',   -- S2 admission: mandatory ablation and a review date (§5.4)
     'standing',    -- S3+ admission
     'retired');
```

`driver_class` deserves its own note, because the fail-safe direction is the whole point. [13 §8.4](13-synthetic-data-generator.md) enumerates five `triggering_driver` values (`pms_periodicity`, `casualty`, `prediction`, `opportunistic`, `opportunistic_pms`) and [13 §9.10](13-synthetic-data-generator.md) deliberately generates records with the field **missing** — *"the propensity model must handle missingness in the treatment record, which is the realistic production condition."* [03 §6](../architecture/03-integration-contracts.md) names the field but **does not enumerate its vocabulary** (recorded as **OD-3**, §13). FI therefore holds a declared mapping table, and:

- An absent `triggering_driver` classifies as `unknown`.
- A driver value **not present in the mapping** classifies as `unknown` — never as `policy_independent`.
- `unknown` counts toward the gate's confounding-risk numerator exactly as `model_assigned` does (§3.2).

A defaults-to-benign mapping is how a confounded population passes a gate silently. This one defaults to hostile.

### 2.2 `failure_mode` — a LOCAL REFERENCE, not a copy

[04 §9](../architecture/04-subapplication-architectures.md) lists `FailureMode` as *"A taxonomy entry: physical mechanism, observable signature, affected populations."* Read literally as an owned aggregate, that is finding **C8** rebuilt: a second taxonomy store. Doc 12's single-ownership resolution is binding, and [12 §4](12-reference-data-taxonomy.md) already states what FI holds: *"Nothing normative. Its `FailureMode` aggregate (document 04 §9) references registry entries by `(lineage_id, taxonomy_version)`."*

So the aggregate is split. What FI owns is the *analysis annotation* on a mode; what Reference Data owns is the mode.

```sql
-- FI-owned analysis state ABOUT a mode. Contains no vocabulary content (I1).
CREATE TABLE failure_intel.failure_mode_ref (
    mode_lineage_id       uuid    NOT NULL,   -- -> reference_data.failure_mode_entry.lineage_id
    taxonomy_version      text    NOT NULL,   -- the version this annotation was authored against
    -- Analysis state. FI's own facts, not the registry's.
    population_scope      jsonb   NOT NULL,   -- {equipment_families[], niins[], class_ids[], domains[]}
                                              -- "affected populations" from 04 §9 — an FI conclusion
    discovery_eligible    boolean NOT NULL,   -- below §3's declared minimum population, discovery
                                              -- is not attempted (04 §9 Phase 3 question)
    min_population_basis  text    NOT NULL,   -- how the threshold was determined, reviewable
    watch_reason          text,               -- why this mode is under active analysis
    taxonomy_review_required boolean NOT NULL DEFAULT false,  -- set on a split/narrowed
                                              -- supersession of this lineage (§6.4)
    first_attributed_at   timestamptz,
    attribution_count     int     NOT NULL DEFAULT 0,   -- maintained projection, not a source fact
    classification        jsonb   NOT NULL,              -- ClassificationLabel, 03 §7.3
    PRIMARY KEY (mode_lineage_id, taxonomy_version)
);

-- The read-through cache. The ONLY local copy of served content, and it is a copy (doc 12 DO-NOT-1).
CREATE TABLE failure_intel.taxonomy_cache (
    taxonomy_version   text        NOT NULL,
    fetched_at         timestamptz NOT NULL,
    source_etag        text        NOT NULL,
    payload            jsonb       NOT NULL,   -- verbatim GET /taxonomy response body
    PRIMARY KEY (taxonomy_version)
);
```

Three properties matter:

- **`GET /failure-modes` on this service is a projection, not a second register.** It joins `failure_mode_ref` to the cached Reference Data payload and echoes `taxonomy_version` and `code_authority` from the source. It never serves a code, definition, or signature that did not arrive from `GET /api/v1/reference-data/taxonomy`.
- **`{id}` in `GET /failure-modes/{id}` is `mode_lineage_id`**, which is Reference Data's stable resolution key ([12 §2.3](12-reference-data-taxonomy.md): *"`lineage_id` is the resolution key, not `code`"*). Not the three-letter code, which is renameable across a major bump.
- **`code_authority` is carried through, never flattened.** Where the subject mode is a `fathom-extension` placeholder (doc 12 **OD-1** path (b)), every rendering says so and §4.3's cap applies.

### 2.3 `causal_hypothesis`

[04 §9](../architecture/04-subapplication-architectures.md): *"A proposed causal relationship with method, evidence, strength, and adjudication state."*

```sql
CREATE TABLE failure_intel.causal_hypothesis (
    hypothesis_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- ── the causal claim, structured. Never free text.
    subject_mode_lineage  uuid NOT NULL,       -- the failure mode in question
    subject_taxonomy_version text NOT NULL,    -- I2
    exposure              jsonb NOT NULL,      -- {kind: channel_feature | config_attribute |
                                               --  operating_regime | maintenance_practice |
                                               --  part_source | environment,
                                               --  ref, definition_version, definition_time}
    claimed_direction     text NOT NULL        -- 'increases_hazard' | 'decreases_hazard' |
        CHECK (claimed_direction IN                -- 'shortens_time_to_failure' |
               ('increases_hazard','decreases_hazard',   -- 'no_effect' (a testable null, §7)
                'shortens_time_to_failure','no_effect')),
    population_spec       jsonb NOT NULL,      -- the EXACT input population: family, niins,
                                               -- hulls, classes, domains, window, and the
                                               -- baseline_epoch bounds it was valid under
    contrast_spec         jsonb,               -- NULL where contrast_arity = 1. Arm definitions

    -- ── anti-rediscovery (§7.2). Deterministic over the four fields above.
    fingerprint           bytea NOT NULL,
    supersedes_hypothesis_id uuid REFERENCES failure_intel.causal_hypothesis(hypothesis_id),
    novelty_basis         text,                -- REQUIRED when superseding (§7.2)

    -- ── method and provenance
    primary_method_id     text NOT NULL,       -- §3's registry key, e.g. 'M3.compop'
    primary_method_version text NOT NULL,
    discovery_run_id      uuid NOT NULL REFERENCES failure_intel.discovery_run(run_id),

    -- ── D21. NOT NULL, no default. Invariant I3.
    treatment_census_id   uuid NOT NULL REFERENCES failure_intel.treatment_census(census_id),
    treatment_handling    failure_intel.treatment_handling NOT NULL,
    gate_verdict          failure_intel.gate_verdict NOT NULL,

    -- ── strength. Computed (I4).
    strength              jsonb NOT NULL,      -- the §4.2 EvidenceStrength document
    strength_band         failure_intel.strength_band NOT NULL,
    band_limiting_axis    text NOT NULL,       -- which axis caps the band — the actionable field
    strength_rule_version text NOT NULL,       -- the versioned derivation rule set (§4.4)

    -- ── adjudication
    adjudication_state    failure_intel.adjudication_state NOT NULL DEFAULT 'draft',
    adjudication_record_id uuid REFERENCES failure_intel.adjudication_record(record_id),
    published_band        failure_intel.strength_band,   -- what was actually published
    superseded_by_hypothesis_id uuid REFERENCES failure_intel.causal_hypothesis(hypothesis_id),

    -- ── the claim lease itself. [AMENDMENT -- closes 52-practitioner-apps.md §13
    -- correction 12.] POST /hypotheses/{id}/claim (§8.1) has always required one,
    -- but no column ever held it -- the lease this whole document assumes existed
    -- had nowhere to live. Mirrors 30-gateway.md §4.5's identical pair for proposals.
    claimed_by             text,
    claimed_until          timestamptz,          -- MONOTONIC deadline in application code;
                                                  -- stored as wall-clock only for operator display
    -- [AMENDMENT] row_version is the ETag source -- nothing else on this row
    -- changes deterministically on every write, so adjudication_record.claim_etag
    -- (below) had no column to be computed FROM. Bumped by exactly one on every
    -- UPDATE that changes claim state, adjudication state, or the second
    -- signature (a trigger, or the single write transaction each of those is
    -- already required to be); ETag is str(row_version). Same mechanism 03 §7.2
    -- rule 3 requires generically; stated concretely here because no document
    -- gives one universal implementation and each owner must supply its own.
    row_version            bigint NOT NULL DEFAULT 1,
    -- ── the second signature, for dual control at S3/S4 (§5.2). A second
    -- adjudicator otherwise has no way to see one is outstanding.
    second_signature_outstanding boolean NOT NULL DEFAULT false,

    created_at            timestamptz NOT NULL DEFAULT now(),
    classification        jsonb NOT NULL,

    -- A refused gate can never yield a published hypothesis. Defence in depth for §3.2.
    CONSTRAINT refused_is_never_published CHECK (
        gate_verdict <> 'refused' OR adjudication_state <> 'published'),
    -- I4: adjudication may lower the band, never raise it.
    CONSTRAINT override_lowers_only CHECK (
        published_band IS NULL OR published_band <= strength_band),
    -- §5.1: publication requires an adjudication record.
    CONSTRAINT published_has_adjudication CHECK (
        adjudication_state <> 'published' OR adjudication_record_id IS NOT NULL),
    -- [AMENDMENT] §5.2's dual-control rule ("S3+ requires dual control") was
    -- asserted in prose and enforced nowhere -- this CHECK only required AN
    -- adjudication record, any record, regardless of strength_band. A single
    -- adjudicator could publish an S3/S4 finding alone. Enforced here: at S3
    -- or S4, second_signature_outstanding must be false at publication, i.e.
    -- the second signature was actually obtained, not merely flagged pending.
    CONSTRAINT dual_control_enforced_at_s3_plus CHECK (
        adjudication_state <> 'published'
        OR strength_band < 'S3'
        OR second_signature_outstanding = false),
    -- §7.2: a repeat fingerprint must declare what is new.
    CONSTRAINT supersession_declares_novelty CHECK (
        (supersedes_hypothesis_id IS NULL) = (novelty_basis IS NULL)),
    -- 'not_applicable' is legal only for single-arm methods; also checked at registration (§3.1).
    CONSTRAINT contrast_requires_handling CHECK (
        contrast_spec IS NULL OR treatment_handling <> 'not_applicable'),
    -- The claim lease is paired, exactly like every other claim in this program.
    CONSTRAINT claim_is_paired CHECK (
        (claimed_by IS NULL) = (claimed_until IS NULL))
);

-- [AMENDMENT] second_signature_outstanding's own lifecycle, previously
-- unspecified ("no rule for who sets or clears it"): set true by the FIRST
-- adjudication record at S3/S4 (decision='approve' with band_after >= S3),
-- cleared false by a SECOND adjudication_record on the same hypothesis whose
-- second_adjudicator is distinct from the first record's adjudicated_by. The
-- API layer enforces the distinctness rule; dual_control_enforced_at_s3_plus
-- above is the CHECK-level backstop that makes "cleared without a real second
-- signer" unrepresentable at publication regardless of an application bug.

CREATE UNIQUE INDEX ch_fingerprint_live ON failure_intel.causal_hypothesis (fingerprint)
    WHERE adjudication_state NOT IN ('superseded','withdrawn');
CREATE INDEX ch_mode    ON failure_intel.causal_hypothesis (subject_mode_lineage, strength_band);
CREATE INDEX ch_state   ON failure_intel.causal_hypothesis (adjudication_state, strength_band);
```

`contrast_requires_handling` is the constraint a reviewer should read twice. It makes it impossible to store a two-arm comparative hypothesis that claims treatment assignment is not applicable — which is precisely the shape D21 describes.

### 2.4 `evidence_record`

```sql
-- NOTE: no 'prediction' member. §1.5. This is not an omission.
CREATE TYPE failure_intel.evidence_kind AS ENUM (
    'anomaly_tag',          -- pma, confirmed. Carries its taxonomy_version as filed
    'tag_rejection',        -- pma, rejected. A labeled negative
    'maintenance_action',   -- maintenance. 3-M codes as filed, plus the treatment record
    'removal',              -- registry, installed_item.removed with failure indicator
    'telemetry_window',     -- an object-store reference to an immutable window
    'attribution',          -- an FI attribution (§2.5)
    'discovery_artifact',   -- a run output: fitted model, graph, diagnostics
    'test_result',          -- design-advisory test evidence. The S4 unlock (§4.3)
    'document_chunk',       -- knowledge-retrieval. Carries source_trust (D14)
    'negative_control'      -- §3.7's falsification battery result
);

CREATE TABLE failure_intel.evidence_record (
    evidence_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    hypothesis_id     uuid REFERENCES failure_intel.causal_hypothesis(hypothesis_id),
    attribution_id    uuid REFERENCES failure_intel.attribution(attribution_id),
    kind              failure_intel.evidence_kind NOT NULL,
    ref               text NOT NULL,          -- canonical identifier or object key
    subject           jsonb NOT NULL,         -- 03 §5.4 scope identifiers
    taxonomy_version  text,                   -- where the evidence carries a label (I2)
    source_trust      text NOT NULL           -- 03 §7.2 [D14]
        CHECK (source_trust IN ('program','vendor','external')),
    observed_at       timestamptz NOT NULL,   -- occurred_at of the underlying fact
    recorded_at       timestamptz NOT NULL,   -- 03 §5.4: audit and hindsight use this
    definition_version text,                  -- D22: the definition that computed the value
    definition_time   timestamptz,            -- D22: when that definition was AUTHORED
    excerpt           text,
    relevance         text,
    classification    jsonb NOT NULL,
    CONSTRAINT evidence_attaches_to_one CHECK (
        (hypothesis_id IS NULL) <> (attribution_id IS NULL)),
    -- D22: a derived value whose definition was authored after the observation window closed
    -- carries hindsight. Recorded, and it caps the strength band (§4.3).
    CONSTRAINT definition_time_paired CHECK (
        (definition_version IS NULL) = (definition_time IS NULL))
);
```

**Why there is no `prediction` evidence kind.** [04 §9](../architecture/04-subapplication-architectures.md) forbids predictions as evidence, and an enum without the member is a stronger control than a validation rule someone can relax. A prediction reaches FI only through the treatment projection (§2.8), and the import-linter contract keeps method code away from it (§1.5).

**Why `definition_time` is a column and not a note.** Finding **D22**: *"a model trained at `as_of=2025-03-01` receives values computed by a definition authored in 2026 by someone who had seen the 2025 failures."* An FI hypothesis resting on such a value is not point-in-time honest, and the axis in §4.3 caps it at S1. Recording the definition's authoring time is the only way the check is computable.

### 2.5 `attribution` — and the arbitration record

[04 §9](../architecture/04-subapplication-architectures.md): *"A binding of an observed failure to a failure mode, with confidence."* [08 §2.8](../architecture/08-standards-alignment.md) adds the second job, and it is the harder one: *"Its `Attribution` is the arbitration record when a tag and a findings code disagree. **That disagreement is a retained first-class signal, not an error to clean.**"*

```sql
CREATE TABLE failure_intel.attribution (
    attribution_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- ── what failed. Instance identity is IUID-backed installed_item_id (08 §2.8 non-neg. 4).
    installed_item_id   uuid NOT NULL,        -- 03 §3.3 join key. NEVER eic, NEVER position_id
    asset_id            uuid NOT NULL,
    niin                char(9) NOT NULL,
    mission_id          uuid,                 -- where the observation is mission-scoped
    failure_observed_at timestamptz NOT NULL, -- occurred_at of the failure event
    baseline_epoch      bigint NOT NULL,      -- 03 §5.4. The configuration it occurred under

    -- ── what it is attributed to. A REFERENCE (I1).
    mode_lineage_id     uuid NOT NULL,
    taxonomy_version    text NOT NULL,        -- FI's working version at arbitration time
    confidence          numeric(3,2) NOT NULL CHECK (confidence > 0 AND confidence <= 1),

    -- ── THE ARBITRATION RECORD. Both sides retained, always (doc 12 §9.2, §9.3).
    agreement_class     failure_intel.agreement_class NOT NULL,
    pma_side            jsonb NOT NULL,       -- [{tag_ref, signature_key AS FILED,
                                              --   taxonomy_version AS FILED, reviewer,
                                              --   qualification, candidate_modes[]{lineage,
                                              --   confidence, resolve_hops}}]
    maintenance_side    jsonb NOT NULL,       -- [{action_ref, cause_code, when_discovered_code,
                                              --   action_taken_code, eic_prefix_matched,
                                              --   taxonomy_version AS FILED,
                                              --   candidate_modes[]{lineage, confidence, hops}}]
    candidate_modes     jsonb NOT NULL,       -- the FULL reconciled candidate set with both
                                              -- sides' confidences. NEVER truncated, NEVER LIMIT 1
    arbitration_basis   text NOT NULL,        -- the engineering rationale a reliability
                                              -- engineer would sign
    arbitration_note    text,

    adjudicated_by      text NOT NULL,        -- §5.2's authority
    adjudicated_at      timestamptz NOT NULL DEFAULT now(),
    superseded_by_attribution_id uuid REFERENCES failure_intel.attribution(attribution_id),
    classification      jsonb NOT NULL,

    -- Doc 12 DO-NOT-2, applied at the consuming end: the candidate set is never collapsed.
    CONSTRAINT candidates_non_empty CHECK (jsonb_array_length(candidate_modes) >= 1),
    -- A disagreement MUST retain both sides. An empty side with a disagreement class is
    -- how the signal gets quietly dropped.
    CONSTRAINT disagreement_retains_both CHECK (
        agreement_class <> 'both'
        OR (jsonb_array_length(pma_side) > 0 AND jsonb_array_length(maintenance_side) > 0)),
    CONSTRAINT no_self_supersession CHECK (superseded_by_attribution_id <> attribution_id)
);

CREATE INDEX attr_item    ON failure_intel.attribution (installed_item_id, failure_observed_at);
CREATE INDEX attr_mode    ON failure_intel.attribution (mode_lineage_id, taxonomy_version);
CREATE INDEX attr_mission ON failure_intel.attribution (mission_id) WHERE mission_id IS NOT NULL;
```

**The reconciliation is executed, not reimplemented.** The candidate sets in `pma_side` and `maintenance_side` are produced by calling Reference Data's `POST /taxonomy/resolve` and the two crosswalk reads, then joining exactly as [12 §9.1](12-reference-data-taxonomy.md) specifies — `FULL OUTER JOIN`, resolution per side at each side's own held version, `agreement` as an output column and never a filter, ranked and never truncated. FI contributes the consumer-driven test `tax-xw-reconcile-retains` ([12 §8.3](12-reference-data-taxonomy.md)) against that behaviour.

**Where the two sides disagree, the attribution records an arbitration, not a correction.** [12 §9.3](12-reference-data-taxonomy.md)'s worked example is the canonical case: a reviewer saw an abnormal instrument reading, a maintainer who opened the pump filed *normal wear and tear*. `agreement_class = 'neither'` or a partial overlap is a legitimate, publishable outcome; the `confidence` reflects it; and both filings survive byte-identical in their own vocabularies at their own `taxonomy_version`. Nothing in this service writes back to a PMA tag or a Scheduling findings record — they are other sub-applications' facts.

### 2.6 `causal_feature_set`

[04 §9](../architecture/04-subapplication-architectures.md): *"Versioned feature definitions derived from adjudicated findings, consumed by tier-3 models"*, admitted *"only after adjudication and only as a versioned feature-set entry."*

```sql
CREATE TABLE failure_intel.causal_feature_set (
    feature_set_version   text PRIMARY KEY,       -- semver
    status                text NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','published','deprecated')),
    predecessor_version   text REFERENCES failure_intel.causal_feature_set(feature_set_version),
    taxonomy_version      text NOT NULL,          -- the version its modes resolve under (I2)
    strength_rule_version text NOT NULL,          -- §4.4. Pinned, so admissions are auditable
    release_note          text NOT NULL,
    published_at          timestamptz,
    published_by          text,
    CONSTRAINT cfs_semver CHECK (feature_set_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),
    CONSTRAINT cfs_published_has_provenance CHECK (
        status <> 'published' OR (published_at IS NOT NULL AND published_by IS NOT NULL))
);

CREATE TABLE failure_intel.causal_feature_entry (
    feature_set_version   text NOT NULL
        REFERENCES failure_intel.causal_feature_set(feature_set_version),
    feature_key           text NOT NULL,          -- stable slug; the contract with PdM
    -- ── the definition. A REFERENCE to Condition & Telemetry's definition, with D22 provenance.
    definition_ref        text NOT NULL,          -- indicator/channel definition identifier
    definition_version    text NOT NULL,
    definition_time       timestamptz NOT NULL,   -- REQUIRED. 03 §6's catalog row names it
    computation_spec      jsonb NOT NULL,         -- transform, window, normalisation, units
    -- ── the provenance that makes admission auditable
    source_hypothesis_id  uuid NOT NULL REFERENCES failure_intel.causal_hypothesis(hypothesis_id),
    strength_band_at_admission failure_intel.strength_band NOT NULL,
    treatment_census_id   uuid NOT NULL           -- the census behind the admitting hypothesis
        REFERENCES failure_intel.treatment_census(census_id),
    standing              failure_intel.feature_standing NOT NULL,
    admission_record_id   uuid NOT NULL REFERENCES failure_intel.adjudication_record(record_id),
    review_due            date NOT NULL,          -- every entry has one; §5.4
    retired_at            timestamptz,
    retirement_reason     text,
    applicable_scope      jsonb NOT NULL,         -- equipment families, niins, classes, domains
    classification        jsonb NOT NULL,
    PRIMARY KEY (feature_set_version, feature_key),

    -- §5.3 THE ADMISSION FLOOR. A weak hypothesis cannot become a feature, structurally.
    CONSTRAINT admission_floor CHECK (strength_band_at_admission >= 'S2'),
    -- S2 evidence may only ever be a MONITORED feature (§5.4).
    CONSTRAINT s2_is_monitored_only CHECK (
        strength_band_at_admission > 'S2' OR standing IN ('monitored','retired')),
    CONSTRAINT retirement_is_paired CHECK ((retired_at IS NULL) = (retirement_reason IS NULL))
);
```

Published versions are frozen by trigger, on the pattern of [12 §6.3](12-reference-data-taxonomy.md) — a `BEFORE UPDATE OR DELETE` function that permits exactly one mutation on a published row (retirement marking, once) and raises on any change to `definition_ref`, `definition_version`, `definition_time`, `computation_spec`, `source_hypothesis_id`, or `strength_band_at_admission`. The failure mode being prevented is identical to doc 12's: a well-intentioned `UPDATE` that adjusts a computation spec, after which every tier-3 model trained against that version was trained on something else.

`admission_floor` is the mechanism behind 04 §9's key decision — *"This prevents a weak hypothesis from silently propagating into operational predictions"* — and it is a CHECK constraint rather than a workflow step because a workflow step is skippable under schedule pressure.

### 2.7 `discovery_run` and the method registry

```sql
CREATE TABLE failure_intel.discovery_run (
    run_id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    method_id           text NOT NULL,       -- §3 registry key
    method_version      text NOT NULL,
    requested_by        text NOT NULL,
    population_spec     jsonb NOT NULL,      -- as REQUESTED, before any gate rewrite
    effective_population_spec jsonb,         -- as RUN, after a 'restricted' rewrite (§3.2)
    treatment_census_id uuid REFERENCES failure_intel.treatment_census(census_id),
    gate_verdict        failure_intel.gate_verdict,
    gate_reason         text,                -- REQUIRED on 'refused'. The refusal is a record
    status              text NOT NULL DEFAULT 'requested'
        CHECK (status IN ('requested','gated','running','complete','refused','failed')),
    domino_run_ref      text,                -- the Domino Job/Flow execution reference
    artifact_prefix     text,                -- object-store prefix for outputs
    as_of               timestamptz NOT NULL,      -- point-in-time boundary of the input data
    read_model_lag_at_start jsonb NOT NULL,   -- §11.3's staleness attestation, per stream
    started_at          timestamptz,
    completed_at        timestamptz,
    CONSTRAINT refusal_has_reason CHECK (status <> 'refused' OR gate_reason IS NOT NULL),
    CONSTRAINT restricted_records_rewrite CHECK (
        gate_verdict <> 'restricted' OR effective_population_spec IS NOT NULL)
);
```

**A refused run is a first-class row.** It is not an exception log line and not a skipped iteration. `GET /discovery-runs?status=refused` is a supported query, the refusal reason is human-readable, and §10.2's test asserts the row exists. A gate whose refusals are invisible is a gate nobody can audit.

The method registry itself is code, not data, because a declaration that can be edited without a code review is not a declaration:

```python
# src/fathom_failure_intel/methods/registry.py
@dataclass(frozen=True, kw_only=True)
class MethodDeclaration:
    method_id: str
    method_version: str
    causal_question: str
    contrast_arity: int                       # 1 = within-population; >1 = comparative
    treatment_handling: TreatmentHandling      # NO DEFAULT. Registration fails without it
    propensity_spec: PropensitySpec | None     # required iff handling involves propensity
    requires_covariates: frozenset[str]
    min_events_expression: str                 # e.g. 'events_per_parameter >= 10'
    known_failure_modes: tuple[str, ...]       # §3. Non-empty, asserted at registration
    placeholder_pending_sme: bool               # §3.8

def register(decl: MethodDeclaration, fn: MethodFn) -> None:
    if decl.contrast_arity > 1 and decl.treatment_handling is TreatmentHandling.NOT_APPLICABLE:
        raise MethodRegistrationError(                     # D21, at import time
            f"{decl.method_id}: contrast_arity={decl.contrast_arity} forbids "
            "treatment_handling='not_applicable'. Declare propensity_modeled, "
            "propensity_and_ipcw, or restricted_to_policy_frozen.")
    if decl.treatment_handling in _PROPENSITY_HANDLINGS and decl.propensity_spec is None:
        raise MethodRegistrationError(
            f"{decl.method_id}: declares propensity handling with no PropensitySpec.")
    if not decl.known_failure_modes:
        raise MethodRegistrationError(
            f"{decl.method_id}: known_failure_modes is empty. A method whose failure mode "
            "is undocumented cannot contribute to an evidence-strength assessment.")
    _REGISTRY[decl.method_id] = (decl, fn)
```

The first check is D21's remedy at the earliest possible moment: a comparative method that declares treatment assignment inapplicable **fails at import**, so the service does not start. This is deliberately earlier than the runtime gate — it catches the developer, not the analyst.

### 2.8 `treatment_census` — the D21 record

This is the table the rest of the document turns on. It is the persisted answer to *"did the population I just analysed contain interventions assigned by the model under test?"*

```sql
-- The projection of maintenance_action.recorded. Its own schema, reachable only through
-- population.treatment (§1.5). One row per maintenance action in scope.
CREATE TABLE failure_intel_treatment.maintenance_action_projection (
    action_ref            text PRIMARY KEY,
    installed_item_id     uuid NOT NULL,
    asset_id              uuid NOT NULL,
    niin                  char(9) NOT NULL,
    occurred_at           timestamptz NOT NULL,
    recorded_at           timestamptz NOT NULL,
    failure_indicator     boolean,
    -- The three fields D21 required and 03 rev 2 supplied.
    triggering_driver     text,                    -- NULLABLE by design; 13 §9.10
    triggering_prediction_id uuid,
    policy_version        text,
    -- FI's fail-safe classification (§2.1).
    driver_class          failure_intel.driver_class NOT NULL,
    driver_mapping_version text NOT NULL,          -- which mapping produced driver_class
    -- Resolution of the prediction reference, for propensity covariate availability (§3.3).
    prediction_resolved   boolean NOT NULL DEFAULT false,
    prediction_covariates jsonb,                   -- reference_class, p_failure, horizon_days,
                                                   -- fallback_level, sharpness, model_version
    baseline_epoch        bigint NOT NULL,
    event_id              uuid NOT NULL            -- 03 §5.2 idempotency
);

CREATE INDEX map_item_time ON failure_intel_treatment.maintenance_action_projection
    (installed_item_id, occurred_at);
CREATE INDEX map_driver     ON failure_intel_treatment.maintenance_action_projection
    (driver_class, policy_version);

-- The census: an immutable, referenceable measurement over one (population, window, contrast).
CREATE TABLE failure_intel.treatment_census (
    census_id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    computed_at           timestamptz NOT NULL DEFAULT now(),
    population_spec       jsonb NOT NULL,          -- the resolved item set, not a query string
    resolved_item_count   int NOT NULL,
    window_start          timestamptz NOT NULL,
    window_end            timestamptz NOT NULL,
    driver_mapping_version text NOT NULL,

    -- ── per-arm counts. One object per contrast arm; a single object where arity = 1.
    arms                  jsonb NOT NULL,
    -- arms[] := { arm_key, item_count, action_count,
    --             model_assigned_count, policy_independent_count, unknown_count,
    --             model_assigned_fraction, unknown_fraction,
    --             confounding_risk_fraction,        -- (model_assigned + unknown) / action_count
    --             policy_versions[], prediction_resolve_rate,
    --             policy_frozen_item_count, policy_frozen_fraction }

    -- ── the derived quantities the gate branches on (§3.2)
    max_confounding_risk_fraction numeric(5,4) NOT NULL,
    differential_exposure         numeric(5,4),    -- max - min across arms. NULL when arity = 1
    policy_version_count          int NOT NULL,
    worst_prediction_resolve_rate numeric(5,4) NOT NULL,
    feedback_provenance           text NOT NULL    -- §3.2's self-fulfilling-evidence check
        CHECK (feedback_provenance IN ('clean','contaminated','unknown')),
    holdout_available             boolean NOT NULL,
    holdout_event_count           int NOT NULL,
    classification                jsonb NOT NULL
);
```

The census SQL is short, and it is worth reading because it is the entire empirical basis of the gate:

```sql
-- Per contrast arm, over the resolved item set and the analysis window.
SELECT
    :arm_key                                                        AS arm_key,
    count(DISTINCT m.installed_item_id)                             AS item_count,
    count(*)                                                        AS action_count,
    count(*) FILTER (WHERE m.driver_class = 'model_assigned')       AS model_assigned_count,
    count(*) FILTER (WHERE m.driver_class = 'policy_independent')   AS policy_independent_count,
    count(*) FILTER (WHERE m.driver_class = 'unknown')              AS unknown_count,
    -- The gate's numerator. UNKNOWN COUNTS AS RISK (§2.1's fail-safe).
    (count(*) FILTER (WHERE m.driver_class IN ('model_assigned','unknown')))::numeric
        / nullif(count(*), 0)                                       AS confounding_risk_fraction,
    array_agg(DISTINCT m.policy_version) FILTER (WHERE m.policy_version IS NOT NULL)
                                                                    AS policy_versions,
    -- Propensity covariate availability (§3.3): every model-assigned action must resolve
    -- to the prediction the policy acted on, or the treatment model is unidentifiable.
    (count(*) FILTER (WHERE m.driver_class = 'model_assigned' AND m.prediction_resolved))::numeric
        / nullif(count(*) FILTER (WHERE m.driver_class = 'model_assigned'), 0)
                                                                    AS prediction_resolve_rate
  FROM failure_intel_treatment.maintenance_action_projection m
 WHERE m.installed_item_id = ANY(:resolved_items)      -- a RESOLVED SET, never a predicate
   AND m.occurred_at >= :window_start
   AND m.occurred_at <  :window_end
   AND m.baseline_epoch <= :max_baseline_epoch;        -- 03 §5.4 epoch fencing
```

Two details are structural rather than incidental. **The item set is resolved before the census runs, and the census is computed over that literal set** — not over a predicate that a later query could evaluate differently. And **`occurred_at` is the analysis clock while `recorded_at` is retained**, because [03 §5.4](../architecture/03-integration-contracts.md) requires the distinction and an at-sea repair recorded weeks later would otherwise fall outside its own window.

### 2.9 API model

The wire model is the schema with the JSONB documents typed. `snake_case` fields per [03 §4](../architecture/03-integration-contracts.md); types published from `packages/canonical-schemas` per [10](10-shared-packages.md). An abbreviated `CausalHypothesis` response, showing the fields a consumer actually branches on:

```json
{
  "hypothesis_id": "…uuid…",
  "subject_mode": { "lineage_id": "…uuid…", "taxonomy_version": "1.2.0",
                    "code": "ELP", "code_authority": "iso-14224-verified" },
  "exposure": { "kind": "operating_regime", "ref": "regime:high-flow-demand",
                "definition_version": "3.1.0", "definition_time": "2026-02-11T00:00:00Z" },
  "claimed_direction": "shortens_time_to_failure",
  "statement": "Corroborated hypothesis: sustained high-flow-demand operation is associated
                with earlier external process-medium leakage in SF-02 wear rings across 4 hulls
                of 1 class. Treatment assignment was propensity-modeled; residual confounding
                by maintenance-queue position is enumerated and not excluded.",
  "strength_band": "S2",
  "band_limiting_axis": "diversity",
  "strength_rule_version": "1.0.0",
  "treatment_handling": "propensity_and_ipcw",
  "gate_verdict": "proceed_corrected",
  "treatment_census_ref": "/api/v1/failure-intel/hypotheses/…/treatment-census",
  "adjudication": { "state": "published", "adjudicated_by": "…", "authority_class":
                    "design_authority", "dual_control": true },
  "admissible_as_causal_feature": true,
  "admissible_as_primary_redesign_driver": false
}
```

`statement` is generated (§4.5). `admissible_as_causal_feature` and `admissible_as_primary_redesign_driver` are computed from the band by the table in §4.3 and served explicitly, so that PdM and Design Advisory do not each re-derive the policy from the band and drift apart.

---

## 3. The causal discovery method portfolio

[04 §9](../architecture/04-subapplication-architectures.md): *"**Method portfolio rather than a single technique.** Causal discovery over observational data constrained by domain-supplied structure, survival analysis with covariates, comparative population analysis across hulls and classes, and signature matching against known failure modes. Each carries different assumptions and different failure modes, and agreement across methods is itself evidence. Phase 3 selects the specific portfolio."*

Document 04 names four method *families* and does not name algorithms. Where a specific algorithm is proposed below it is marked **[PLACEHOLDER — Phase 3 SME validation]** and carries `placeholder_pending_sme = true` in its declaration, which surfaces in every published finding's provenance. Nothing in the strength scale treats a placeholder method's output as if the choice were settled.

### 3.1 The treatment-assignment declaration — D21's remedy, stated

Finding **D21**'s remedy is quoted here verbatim, because §3.2 is its implementation and the wording matters:

> **"Require every Failure Intelligence method to declare how it handles treatment assignment, and forbid comparative population analysis across populations with model-assigned interventions unless the propensity is modeled."**

Two obligations, and both are enforced by mechanism:

**Obligation 1 — every method declares.** `MethodDeclaration.treatment_handling` has **no default value**. A method adapter that omits it fails to construct (`dataclass` with no default, `kw_only`), and a method whose declaration is inconsistent with its `contrast_arity` fails at `register()` — at import time, before the service starts (§2.7). Test `fi-method-declares` enumerates the registry and asserts every entry has a non-null declaration, a non-empty `known_failure_modes`, and a `PropensitySpec` wherever the handling implies one.

**Obligation 2 — comparative analysis is forbidden on model-assigned populations unless propensity is modeled.** This cannot be a registration-time check, because whether a *particular* population contains model-assigned interventions is a fact about data, not about code. It is therefore a runtime gate, specified next.

### 3.2 The gate — a runtime check at the population loader

**The gate is an admission filter at the input boundary, not a branch in the analysis.** This mirrors [13 §10.3](13-synthetic-data-generator.md)'s rule for the generator's holdout, for the same reason it gives: *"the naive approach — score everything, then skip holdout items when acting — leaves a prediction-shaped hole that any subsequent refactor can fill."* A gate applied inside a method is a gate the next method forgets.

Method adapters cannot obtain rows. There is exactly one way in:

```python
# src/fathom_failure_intel/population/loader.py
#
# The ONLY path by which a method adapter obtains data. Enforced by importlinter.ini:
#   forbidden: fathom_failure_intel.methods.* -> fathom_failure_intel.repositories.*
#   forbidden: fathom_failure_intel.methods.* -> fathom_failure_intel.readmodels.prediction
# A method function's signature takes GatedPopulation, so it cannot be called with anything else.

def load_population(spec: PopulationSpec, method_id: str, run: DiscoveryRun) -> GatedPopulation:
    decl, _ = registry.get(method_id)

    items = resolve_items(spec)                       # a literal set, not a predicate (§2.8)
    census = compute_census(items, spec.window, spec.arms, decl)
    persist(census)                                    # referenceable forever, before any verdict

    verdict, reason, effective = _adjudicate(decl, census, spec)
    run.record_gate(census, verdict, reason, effective)

    if verdict is GateVerdict.REFUSED:
        raise TreatmentAssignmentGateError(reason, census_id=census.census_id)
    if verdict is GateVerdict.RESTRICTED:
        items = resolve_items(effective)               # the policy-frozen stratum ∩ requested
        census = compute_census(items, effective.window, effective.arms, decl)
        persist(census)
        if census.max_confounding_risk_fraction > 0:   # must now be clean, or refuse
            raise TreatmentAssignmentGateError(
                "restriction did not eliminate model-assigned treatment", census.census_id)
        if census.holdout_event_count < decl.min_events(census):
            raise TreatmentAssignmentGateError(
                f"policy-frozen stratum has {census.holdout_event_count} events; "
                f"method requires {decl.min_events(census)}", census.census_id)

    return GatedPopulation(items=items, census=census, verdict=verdict, declaration=decl)
```

**How the check actually determines whether the population includes model-assigned interventions.** It queries the `maintenance_action.recorded` projection — the event whose `triggering_driver`, `triggering_prediction_id`, and `policy_version` fields exist for exactly this purpose ([03 §6](../architecture/03-integration-contracts.md): *"The three added fields record the treatment-assignment mechanism, without which neither calibration nor causal analysis can condition on the intervention policy `[D1, D21]`"*). The census SQL of §2.8 classifies every action in the resolved item set and window into `model_assigned` / `policy_independent` / `unknown`, and computes per arm:

```
confounding_risk_fraction = (model_assigned_count + unknown_count) / action_count
```

`unknown` is in the numerator. That is the single most important decision in this section: [13 §9.10](13-synthetic-data-generator.md) generates records with `triggering_driver` absent, and treating an absent driver as periodicity-driven is how a confounded population passes a clean gate.

**The verdict table.** The trigger is *presence*, not magnitude — exactly as D21 words it. No invented threshold is required.

| Census condition | Declared handling | Verdict | Consequence |
|---|---|---|---|
| `max_confounding_risk_fraction = 0` in every arm | any | `proceed` | The unconfounded case. Includes a contrast wholly within the policy-frozen stratum, and a historical window predating any prediction-driven policy |
| `> 0`, `contrast_arity = 1` | `not_applicable`, `ipcw_corrected`, or `treatment_as_node` | `proceed_corrected` | Within-population methods make no cross-arm contrast; treatment enters as a covariate, a node, or a censoring weight |
| `> 0`, `contrast_arity > 1` | `propensity_modeled` or `propensity_and_ipcw`, **and** every precondition in §3.3 passes | `proceed_corrected` | D21's sanctioned path |
| `> 0`, `contrast_arity > 1` | `restricted_to_policy_frozen` | `restricted` | Population rewritten to the policy-frozen stratum ([06 §2](../architecture/06-demo-decisions-and-assumptions.md), [13 §10](13-synthetic-data-generator.md)), re-censused, must come back clean |
| `> 0`, `contrast_arity > 1` | any propensity handling, **any §3.3 precondition failing** | **`refused`** | `TreatmentAssignmentGateError`. No hypothesis row. Run persisted with the census and the reason |
| `> 0`, `contrast_arity > 1` | `not_applicable` | unreachable | Rejected at import (§2.7). If it somehow reaches the gate it refuses, and `contrast_requires_handling` (§2.3) would refuse the row anyway |
| `feedback_provenance = 'contaminated'` or `'unknown'` | anything other than `restricted_to_policy_frozen` | **`refused`**, with a restriction hint | §3.4 |

**What happens on refusal.** The `discovery_run` row persists with `status = 'refused'`, `gate_verdict = 'refused'`, the `treatment_census_id`, and a human-readable `gate_reason`. `POST /discovery-runs` returns `409` with RFC 9457 problem type `urn:fathom:problem:failure-intel:treatment-assignment-gate`, whose `detail` names the failing arm and precondition and whose extension members carry the census reference. Nothing is emitted, nothing is published, and the refusal is queryable. A refusal is an output of this service, not an error in it.

**The self-fulfilling-evidence check (`feedback_provenance`).** D21's loop is *causal features → predictions → interventions → labels → causal features*. Handling treatment assignment for a *single* generation of the loop is insufficient if the exposure under examination is itself a feature that the intervening policy already consumed — the analysis would then be recovering its own prior. The check is:

1. Take the hypothesis's `exposure.ref`. Resolve whether it is, or descends from, a `feature_key` in any published `causal_feature_set` (a local join — FI owns this table).
2. If it does, take the `policy_versions[]` from the census and determine whether any of them consumed that feature set version.
3. `clean` — no policy version in the window consumed it. `contaminated` — at least one did. `unknown` — the mapping from `policy_version` to consuming feature-set version cannot be evaluated.

**`unknown` is treated as `contaminated`.** FI cannot presently evaluate step 2: `policy_version` arrives on `maintenance_action.recorded` and nothing in [03 §6](../architecture/03-integration-contracts.md) resolves it to a consuming `causal_feature_set` version, and FI is not a declared consumer of `model_binding.activated` (adding one undeclared would be finding **C4** in a new costume). The conservative default is therefore the shipped behaviour — such a hypothesis must restrict to the policy-frozen stratum or refuse — and the missing link is recorded as **OD-1** (§13), the highest-priority open decision in this document.

### 3.3 Propensity preconditions — also runtime checks

"Propensity is modeled" is a claim that can be made falsely. These preconditions are what make it checkable, and each one refuses rather than warns.

| # | Precondition | Check | On failure |
|---|---|---|---|
| **P1** | **Treatment-model inputs are available.** The propensity model must be fit on what the policy actually saw | `worst_prediction_resolve_rate = 1.0` — every `model_assigned` action resolves through `triggering_prediction_id` to a retrievable prediction record with `reference_class`, `p_failure` or `population_hazard_rate`, `horizon_days`, `fallback_level`, `sharpness` | Refuse, unless the method additionally declares a missingness model and the unresolved fraction is reported on the strength axis |
| **P2** | **`policy_version` is a covariate wherever policy changed** | If `census.policy_version_count > 1`, assert `policy_version ∈ PropensitySpec.covariates`. [13 §8.4](13-synthetic-data-generator.md) guarantees at least one policy shift in the 24-month window precisely so this is exercised | Refuse. A propensity model that pools across policy regimes estimates a treatment mechanism that never existed |
| **P3** | **Declared confounders are present** | `PropensitySpec.covariates ⊆` the columns actually materialised for the population. Capacity and queue position are named confounders — [13 §8.4](13-synthetic-data-generator.md): *"Interventions therefore queue, and the queue is a confounder that a naive analysis will miss — which is the point"* | Refuse, naming the missing covariate |
| **P4** | **Positivity / common support** | Estimated propensities lie within common support across arms; units off support are **trimmed and the trimmed fraction reported**. The gate refuses if the trimmed fraction exceeds `gate.fi_max_trimmed_fraction` | Refuse. Reported on the strength axis when it passes |
| **P5** | **Balance is achieved, not assumed** | Post-weighting worst absolute standardized mean difference across declared covariates ≤ `gate.fi_max_balance_smd` | Refuse. `balance_worst_smd` is recorded either way and feeds §4.3's axis A4 |
| **P6** | **A negative control exists and passes** | The arm-membership probe: predict arm membership (or `policy_frozen`) from **pre-treatment** covariates. Mirrors [13 §16.2](13-synthetic-data-generator.md)'s probe **B-X6**, deliberately, so a method validated against the generator is validated against the same instrument the generator validates itself with | Does not refuse on its own; a failing or unavailable negative control caps axis A4 at level 1 and therefore the band at S1 |

`gate.fi_max_trimmed_fraction` and `gate.fi_max_balance_smd` are **configured with no default**, and the service refuses to run a propensity-handling method until the program sets them. This follows [13 §16.4](13-synthetic-data-generator.md)'s discipline exactly: the *form* of the test is derivable and is prescribed here; the *practical margin* is a program judgment and is not invented. Recorded as **OD-2** (§13).

### 3.4 Method M1 — constraint-based structure learning over a domain-constrained graph

| | |
|---|---|
| **Method id** | `M1.structure` — **[PLACEHOLDER — Phase 3 SME validation]** |
| **Proposed algorithm** | **PC-stable** (order-independent PC) over a tiered background-knowledge constraint set, with **FCI** run as a mandatory companion because FCI admits latent confounders and PC does not |
| **Causal question** | Of the candidate covariates associated with mode M, which could be a cause, and which are explained away by another covariate — is the vibration-band feature a cause, a descendant, or a sibling? |
| **`contrast_arity`** | 1 (within a single population) |
| **`treatment_handling`** | **`treatment_as_node`.** Intervention is an explicit node carrying the intervention indicator, `driver_class`, and `policy_version`; background knowledge forbids edges from it into the pre-treatment tier. Omitting the treatment node while the census shows `confounding_risk_fraction > 0` **refuses** |
| **Data requirements** | Item-level panel with point-in-time-correct covariates (D22: `definition_time` ≤ window close); a committed tiered background-knowledge file (design and configuration attributes → operating covariates → degradation indicators → treatment → failure event); a declared conditional-independence test — partial correlation where the Gaussian assumption is defensible, a kernel-based test otherwise, **declared per run, never inferred** |
| **Evidence-strength contribution** | Contributes to `method_agreement` and to `n_*` counts. **An unoriented edge in the CPDAG contributes "association not explained by the measured covariates" and never a direction** — `claimed_direction` may not be set from an unoriented edge. Alone, M1 caps at **S2** |
| **Known failure modes** | (a) **Causal sufficiency and faithfulness are assumptions, not findings** — an unmeasured common cause makes PC's output confidently wrong, which is why FCI is mandatory and a PC/FCI disagreement is recorded as an explicit contradiction rather than resolved by preference. (b) **Edge instability from multiple testing** across many channels — the same defect D23 identifies at tier 2, where *"attributions over correlated channels are unidentified and will reorder run to run on unchanged data."* Mitigation: bootstrap edge stability reported per edge, and edges below the declared stability floor are suppressed from the hypothesis entirely, on the pattern of [03 §7.1](../architecture/03-integration-contracts.md)'s `stability` rule. (c) **Sample size versus conditioning-set order** — [13 §2](13-synthetic-data-generator.md)'s envelope gives ~249 spotlight items and ~180 CASREP-severity events across ~120 families; conditioning sets beyond a low order are unidentifiable, so `min_events_expression` bounds the maximum order and the method refuses beyond it rather than returning a graph nobody should believe. (d) **Selection bias from informative censoring** (D1) — the panel is a survivor sample, so M1's population must be either IPCW-weighted or holdout-restricted before its graph means anything |

### 3.5 Method M2 — survival analysis with covariates, IPCW-corrected

| | |
|---|---|
| **Method id** | `M2.survival` |
| **Proposed specification** | Cox proportional hazards with time-varying covariates, plus a Weibull AFT parametric companion; **inverse-probability-of-censoring weighting** for informative censoring; **cause-specific hazards** (with a Fine–Gray subdistribution companion) for the competing-risk split. **[PLACEHOLDER for the AFT/Fine–Gray companions — Phase 3 SME validation]** |
| **Causal question** | Does exposure X shorten time-to-failure for mode M, conditional on the measured covariates, and by how much? |
| **`contrast_arity`** | 1 |
| **`treatment_handling`** | **`ipcw_corrected`** at minimum; **`propensity_and_ipcw`** whenever the exposure of interest could itself have been policy-assigned |
| **Data requirements** | `observed_event_time` and event type; the competing-risk distinction between *failure* and *preventive replacement* — which maps exactly onto [13 §8.1](13-synthetic-data-generator.md)'s composition `failure \| preventive_replacement \| admin_censor \| mission_end_censor`; point-in-time-correct covariate histories; the treatment record for the censoring model; `events_per_parameter` above the declared floor |
| **Evidence-strength contribution** | A hazard ratio or acceleration factor with a confidence interval, plus the proportional-hazards test result and the censoring composition. Populates axis A5 (`censoring`) and contributes a direction to `claimed_direction` |
| **Known failure modes** | (a) **Informative censoring is the headline defect and it is not hypothetical** — D1: *"prediction-driven preventive replacement censors exactly the items about to fail. Every stated method (Weibull MLE, Cox, calibration) assumes non-informative censoring… fitted MTBF rises, `p_failure` decays, and the fleet drifts back to run-to-failure."* Untreated, M2 does not merely lose power, it drifts in a known direction. IPCW is therefore mandatory and its weights' provenance is recorded. (b) **Competing risks silently treated as censoring** inflates estimated survival: a preventive replacement is not a censored failure, it is a different event, and the cause-specific formulation is required rather than optional. (c) **PH violation** — the test result is reported and a violation caps the direction claim to the AFT companion's. (d) **Immortal time bias** if the exposure window is defined using post-baseline information; the point-in-time loader forbids it structurally. (e) **Thin cells** — [13 §16.4](13-synthetic-data-generator.md) states thin cells *"are the expected condition, not the exception"*; below the events-per-parameter floor M2 refuses or collapses covariates and records which |

### 3.6 Method M3 — comparative population analysis with explicit propensity modeling

**This is D21's method.** It is the one the finding names, and the one the gate exists for.

| | |
|---|---|
| **Method id** | `M3.compop` |
| **Proposed specification** | Stabilized inverse-probability-of-treatment weighting on a declared propensity model, with a matched-design companion (propensity or coarsened-exact matching) as a sensitivity analysis. **[PLACEHOLDER for the matching companion — Phase 3 SME validation]** |
| **Causal question** | Does population A exhibit a different rate of mode M than population B — across hulls, classes, configuration variants, part sources, or maintenance practices? |
| **`contrast_arity`** | **≥ 2.** This is what makes `not_applicable` a registration error (§2.7) |
| **`treatment_handling`** | **`propensity_modeled`, `propensity_and_ipcw`, or `restricted_to_policy_frozen`.** Nothing else registers |
| **Data requirements** | The census (§2.8); resolvable `triggering_prediction_id` for every model-assigned action (P1); `policy_version` (P2); the declared confounder set including **maintenance-queue position and parts availability**, which [13 §8.4](13-synthetic-data-generator.md) makes a real confounder by construction; OFRP phase and environmental covariates, since [13 §9.5](13-synthetic-data-generator.md) requires operating-condition confounding to *exceed* the degradation signal over a substantial portion of life for at least two spotlight families |
| **Evidence-strength contribution** | A population-level risk difference or ratio with the full census attached, plus balance diagnostics, trimmed fraction, and the negative-control result. **Caps at S2 unless the contrast is wholly within the policy-frozen stratum or a matched design corroborates it** (§4.3's axis A4) |
| **Known failure modes** | (a) **Confounding by indication — D21 exactly**: *"Comparative population analysis compares hulls whose intervention histories were assigned by the model under test… producing oscillation at the retraining period."* The gate is the control; the census is the evidence that the control was applied. (b) **Unmeasured confounding** by operating tempo, environment, and crew practice — enumerated as `residual_confounders[]` with a stated direction of bias per confounder, and a hypothesis whose residual confounder could reverse the sign cannot exceed S1. (c) **Positivity violation** — arms that do not overlap on the propensity score are not comparable; P4 trims and reports rather than silently extrapolating. (d) **Missing `triggering_driver`** ([13 §9.10](13-synthetic-data-generator.md)) — handled by the fail-safe classification, not by imputation to the benign class. (e) **Arm definition after the fact** — arms are declared in `contrast_spec` and resolved to a literal item set *before* the census runs, so an arm cannot be redrawn once the result is seen |

### 3.7 Method M4 — signature matching against the ISO 14224 taxonomy

| | |
|---|---|
| **Method id** | `M4.signature` |
| **Causal question** | **None.** M4 answers an *attribution* question: does this observation match a known mode's `observable_signature` / `potential_failure_def`, and does the PMA/Scheduling disagreement narrow the candidate set? |
| **`contrast_arity`** | 1 |
| **`treatment_handling`** | `not_applicable` — legal, because M4 makes no population contrast |
| **Data requirements** | `anomaly_tag.confirmed` with its signature and `taxonomy_version` as filed; `maintenance_action.recorded` with 3-M codes as filed; both Reference Data crosswalks; `POST /taxonomy/resolve` for per-side forward resolution; the [12 §9.1](12-reference-data-taxonomy.md) join, executed as specified |
| **Output** | An `Attribution` (§2.5) with `agreement_class`, both sides retained, and the full candidate set. **Not a causal hypothesis** |
| **Evidence-strength contribution** | Contributes `n_independent_observations` and the attribution confidence to a *separate* hypothesis's evidence. **It contributes nothing to a causal direction and cannot by itself lift a hypothesis above S1** — a signature match establishes what failed, never why |
| **Known failure modes** | (a) **The crosswalk is many-to-many and lossy by construction** — doc 12 DO-NOT-2. Any `LIMIT 1`, any "primary candidate", any scalar-valued response corrupts every label derived from maintenance findings; [08 §2.8](../architecture/08-standards-alignment.md) calls it *"the most common way maintenance-derived training data goes bad."* (b) **Vocabulary poverty** — doc 12 §5.4: with only the seven verified ISO 14224 codes, *"the crosswalk degenerates toward one-to-one and the design's central property becomes untestable."* M4's credibility is therefore **gated on doc 12's OD-1**, and under placeholder path (b) every attribution to a `fathom-extension` mode is marked as such everywhere it renders and caps at S2 (§4.3, axis A7). (c) **`taxonomy_version` skew** between the tag and the finding — resolved per side at each side's own held version, never both at the target (doc 12 §9.2). (d) **Treating disagreement as error** — doc 12 §9.3: the disagreement *"is a retained first-class signal, not an error to clean."* An M4 implementation that reports a single "best" mode has destroyed the reason three capture points exist |

### 3.8 Method M5 — the falsification battery (a required companion, not a discovery method)

| | |
|---|---|
| **Method id** | `M5.falsify` |
| **Purpose** | Attempt to break the hypothesis. Every hypothesis at S2 or above must carry an M5 result |
| **`contrast_arity`** | Inherits the hypothesis under test |
| **`treatment_handling`** | Inherits, and re-runs the gate on its own populations |
| **Battery** | **Negative-control outcome** — a mode with no plausible mechanism for exposure X; an effect there indicates unmeasured confounding. **Negative-control exposure** — a covariate with no plausible mechanism for mode M. **Placebo time shift** — the exposure window shifted to a period before it could have acted. **Arm-membership probe** — P6, mirroring [13 §16.2](13-synthetic-data-generator.md)'s B-X6. **Leakage probes** on the FI feature path, mirroring B-X1…B-X3, because a hypothesis learned from a generation artifact is worse than no hypothesis |
| **Evidence-strength contribution** | A pass populates axis A4 level 3. A **failure** moves the hypothesis to `refuted` and it is retained as a negative finding (§7). **Unavailability** — no valid negative control exists for this mode — is recorded as `unavailable` and caps the band at S2, because "we could not try to break it" is not the same as "we tried and failed" |
| **Known failure mode** | The battery's own validity depends on the negative control being genuinely null. A control chosen for convenience produces a reassuring pass. Every control's justification is recorded in `arbitration_basis`-style prose that a reliability engineer signs, and the control set per equipment family is reviewed as an artifact |

### 3.9 Method agreement, and how disagreement is handled

[04 §9](../architecture/04-subapplication-architectures.md): *"Each carries different assumptions and different failure modes, and **agreement across methods is itself evidence.**"* Two rules keep that honest:

- **Agreement counts only across differing identifying assumptions.** M1 and M2 agreeing tells you less than M2 and M3 agreeing, because M1 and M2 share the no-unmeasured-confounder assumption while M3's identification rests on the propensity model. Axis A3 (§4.3) distinguishes *concordant* from *concordant across differing assumptions*, and only the latter reaches level 3.
- **Disagreement is recorded, never averaged.** A method that contradicts the claim populates `methods_contradicting[]`, sets `agreement_class = 'contradicted'`, and drives axis A3 to level 0 — which drives the band to **S0** and routes the hypothesis to `refuted` or back to `under_analysis` with the contradiction attached. There is no reconciliation step that quietly drops the dissenting method, because that step is how a portfolio becomes a single technique with extra ceremony.

---

## 4. Evidence strength standardization

[04 §9](../architecture/04-subapplication-architectures.md): *"**Evidence strength is explicit and standardized.** Every hypothesis carries what supports it, how many independent observations, across how many hulls and classes, by what method, and what confounders remain unaddressed. Downstream consumers — PdM deciding whether to admit a causal feature, and Design Advisory building a business case — make different decisions at different strength levels, and **can only do so if strength is expressed consistently.**"*

Two design consequences follow, and they are the reason this section is a schema and not a rubric:

1. **Strength is a structured document, not prose.** A paragraph describing evidence cannot be compared across hypotheses, cannot gate an admission, and cannot be tested. Every element 04 §9 enumerates is a typed field below.
2. **The band is derived, and the derivation is versioned.** [04 §9](../architecture/04-subapplication-architectures.md)'s Phase 3 question asks for a scale *"interpretable by engineers who are not statisticians."* The five bands are therefore plain-English, the axes are ordinal, and the **worst axis wins** — so the answer to "why is this only S2?" is always one field, `band_limiting_axis`.

### 4.1 What the scale is not

It is not a confidence, a probability, or a score. Nothing sums, nothing averages, and nothing trades off — a hypothesis with 10,000 observations on one hull and unmodeled treatment assignment is **not** stronger than one with 60 observations across three classes in the policy-frozen stratum, and any scheme that adds the axes would say it was. The composition rule is minimum, deliberately.

### 4.2 The `EvidenceStrength` document

```json
{
  "strength_rule_version": "1.0.0",

  "observations": {
    "n_independent_observations": 74,        // deduplicated per installed_item_id per event
    "n_installed_items": 61,
    "n_hulls": 4,
    "n_classes": 1,
    "n_domains": 1,                          // surface | subsurface | unmanned
    "n_failure_events": 23,                  // the identifying quantity, not the row count
    "n_required_by_method": 20,              // from min_events_expression, computed per run
    "observation_ratio": 1.15                // n_failure_events / n_required_by_method
  },

  "diversity": {
    "band": "multi_hull_single_class",       // single_item | single_hull |
                                             // multi_hull_single_class | multi_class | multi_domain
    "hull_list_ref": "…",                    // resolvable, not inlined
    "single_hull_dominance": 0.41            // largest hull's share of events. A concentration flag
  },

  "method_agreement": {
    "methods_run":           [ {"method_id": "M3.compop", "version": "1.2.0",
                                "placeholder_pending_sme": false},
                               {"method_id": "M2.survival", "version": "1.1.0",
                                "placeholder_pending_sme": false} ],
    "methods_supporting":    ["M3.compop", "M2.survival"],
    "methods_contradicting": [],
    "methods_indeterminate": ["M1.structure"],   // ran, produced an unoriented edge
    "identifying_assumptions_distinct": true,     // §3.9's rule
    "agreement_class": "concordant_distinct_assumptions"
                       // contradicted | single_method | concordant | concordant_distinct_assumptions
                       // | interventionally_confirmed
  },

  "confounder_assessment": {
    "treatment_census_ref": "…census_id…",       // REQUIRED. Invariant I3
    "gate_verdict": "proceed_corrected",
    "treatment_handling": "propensity_and_ipcw",
    "max_confounding_risk_fraction": 0.38,
    "unknown_driver_fraction": 0.06,
    "differential_exposure": 0.22,               // across arms
    "policy_versions_spanned": 2,
    "feedback_provenance": "clean",
    "propensity_spec_ref": "…",
    "balance_worst_smd": 0.041,
    "trimmed_fraction": 0.03,
    "prediction_resolve_rate": 1.0,
    "negative_control": { "status": "pass",      // pass | fail | unavailable
                          "controls": [ {"kind": "outcome", "ref": "…", "result": "null"} ] },
    "residual_confounders": [
      { "name": "maintenance_queue_position",
        "direction_of_bias": "toward_the_claim",   // toward | away | unknown
        "could_reverse_sign": false,
        "why_unaddressed": "queue position is not captured in the action record; proxied by
                            availability phase only" }
    ]
  },

  "censoring": {
    "informative_censoring_present": true,
    "handling": "ipcw",                          // none | ipcw | holdout_restricted | both
    "composition": { "failure": 0.31, "preventive_replacement": 0.44,
                     "admin_censor": 0.22, "mission_end_censor": 0.03 },
    "ipcw_weight_diagnostics_ref": "…"
  },

  "integrity": {
    "definition_time_integrity": "pass",         // pass | fail | unknown  — D22
    "definition_time_worst_case": "2026-02-11T00:00:00Z",
    "window_close": "2026-06-30T00:00:00Z",
    "point_in_time_loader_version": "…",
    "taxonomy_version": "1.2.0",
    "subject_code_authority": "iso-14224-verified"   // doc 12 §2.3. 'fathom-extension' caps at S2
  },

  "band": "S2",
  "band_limiting_axis": "diversity",
  "axis_levels": { "A1_observations": 2, "A2_diversity": 2, "A3_agreement": 3,
                   "A4_confounding": 2, "A5_censoring": 2 },
  "caps_applied": []
}
```

### 4.3 The axes, and the band derivation

Five ordinal axes. Each level is defined structurally so that two engineers scoring the same hypothesis get the same answer.

**A1 — observation count.** Relative to the method's own identifiability requirement, never an absolute *n*, because [13 §16.4](13-synthetic-data-generator.md) makes thin cells the expected condition and an absolute floor would either exclude everything or mean nothing.

| Level | Condition |
|---|---|
| 0 | `observation_ratio < 1` — below the method's declared minimum. The method should have refused |
| 1 | `1 ≤ ratio < m₁` |
| 2 | `m₁ ≤ ratio < m₂` |
| 3 | `m₂ ≤ ratio < m₃` |
| 4 | `ratio ≥ m₃` |

`m₁, m₂, m₃` are `strength.observation_multipliers`, shipped as `[2, 4, 8]` in `strength_rule_version 1.0.0`, **versioned rather than hard-coded**, and flagged for SME review as **OD-4**. The multipliers are a convention; the *form* — a ratio against a declared requirement — is the part that is defensible.

**A2 — population diversity.** Purely structural; no numbers, no judgment.

| Level | Condition |
|---|---|
| 0 | A single installed item |
| 1 | A single hull |
| 2 | Multiple hulls, one class |
| 3 | Multiple classes |
| 4 | Multiple domains (surface / subsurface / unmanned) |

A `single_hull_dominance` above `strength.max_hull_dominance` demotes A2 by one level, because four hulls of which one supplies 90% of events is a single-hull study wearing a multi-hull label. [13 §7.1](13-synthetic-data-generator.md) makes this checkable by construction: *"no family exists in only one asset, because a family present on a single hull cannot support the cross-hull population comparison that the causal analysis depends on."*

**A3 — method agreement.**

| Level | Condition |
|---|---|
| 0 | Any method contradicts the claim |
| 1 | One method supports it; no corroboration |
| 2 | Two or more methods concordant, sharing identifying assumptions |
| 3 | Two or more methods concordant with **distinct** identifying assumptions, and M5's battery passed |
| 4 | A designed intervention or a Design Advisory test result confirms the mechanism (`evidence_kind = 'test_result'`) |

**A4 — confounder assessment.** The D21 axis.

| Level | Condition |
|---|---|
| 0 | `gate_verdict = 'refused'`, or `treatment_handling` unsatisfied, or `feedback_provenance ≠ 'clean'` |
| 1 | `proceed_corrected` with balance not achieved, or a residual confounder that `could_reverse_sign`, or `negative_control.status ∈ {fail, unavailable}`, or `unknown_driver_fraction > 0` with no missingness model |
| 2 | Propensity modeled, all §3.3 preconditions passed, balance achieved, residuals enumerated with a stated direction and none sign-reversing |
| 3 | Level 2 **plus** a passing negative control, **or** the contrast restricted to the policy-frozen stratum (`gate_verdict = 'restricted'`) |
| 4 | Policy-frozen stratum **plus** a designed intervention |

The policy-frozen stratum reaching level 3 directly is the point of [06 §2](../architecture/06-demo-decisions-and-assumptions.md)'s decision: it *"gives an unconfounded stratum for calibration and causal analysis, and the only honest basis for a 'CASREPs avoided' claim."* A finding built there does not depend on a correctly specified propensity model, which is the weakness [06 §2](../architecture/06-demo-decisions-and-assumptions.md) names in the correction-only alternative.

**A5 — censoring.**

| Level | Condition |
|---|---|
| 0 | Informative censoring present and unaddressed (D1) |
| 1 | IPCW applied, no weight diagnostics |
| 2 | IPCW applied with diagnostics reported |
| 3 | Holdout-restricted, so the censoring mechanism is policy-independent |
| 4 | Both — holdout-restricted **and** corrected, with the two agreeing |

**Derivation.** Prescribed, monotone, and implemented in `strength/rules.py` under `strength_rule_version`:

```
raw_band       = S{ min(A1, A2, A3, A4, A5) }
band           = apply_caps(raw_band)
band_limiting_axis = argmin(A1..A5), ties broken in axis order A4, A5, A3, A2, A1
```

Two caps, applied after the minimum and recorded in `caps_applied[]`:

| Cap | Trigger | Effect |
|---|---|---|
| **C-DT** | `definition_time_integrity ∈ {fail, unknown}` | Cap at **S1**. D22: a value computed by a definition authored after the window closed carries hindsight, and no amount of population diversity repairs that |
| **C-TAX** | `subject_code_authority = 'fathom-extension'` | Cap at **S2**. Doc 12 §5.4 / OD-1: a finding about a program-synthesised placeholder mode cannot be an established finding about an ISO 14224 mode |

Ties break toward A4 first because when two axes are equally limiting, the confounding axis is the one a consumer most needs to know about.

### 4.4 The bands, and what each one authorizes

This table is the contract between the two consumers 04 §9 names. It is served on the API (`admissible_as_*` in §2.9) so neither consumer re-derives it.

| Band | Plain-English meaning | PdM — causal feature admission | Design Advisory — business case | Scheduling | Agents |
|---|---|---|---|---|---|
| **S0** | Contradicted, or the gate refused. Not a finding | **No.** A published S0 is a defect | No | No | Not renderable |
| **S1** | **Examined, not established.** One method, or a narrow population, or unresolved confounding | **No** — the admission floor is S2 (§2.6's CHECK) | May cite as a reason to *collect data*, never as a driver | No | May be summarised as an open question, in the S1 template only |
| **S2** | **Corroborated hypothesis.** Multiple methods, treatment assignment handled, censoring addressed | **Yes, as `monitored` only** — mandatory ablation, mandatory `review_due` (§5.4) | Supporting evidence; **not** the primary driver of a `redesign_candidate` | No interval change | Renderable in the S2 template |
| **S3** | **Adjudicated finding, strong evidence.** Distinct-assumption agreement, multi-class, falsification passed, no sign-reversing residual | **Yes, as `standing`** | **May be the primary driver** of a `redesign_candidate` | Supports `interval_change` at item/asset scope (`planner`, [03 §7.2.1](../architecture/03-integration-contracts.md)) | Renderable in the S3 template |
| **S4** | **Confirmed by intervention or test.** A designed intervention or a Design Advisory test result confirms the mechanism | Yes, as `standing` | Yes, and sufficient alone | Supports `interval_change` at class/fleet scope — `fleet_authority` **plus dual control** per [03 §7.2.1](../architecture/03-integration-contracts.md) | The **only** band whose template uses causal verbs |

### 4.5 The statement template — how "never present a hypothesis as an established cause" is enforced

Prose is where the framing decision dies. A published finding's operator- and engineer-facing text is therefore **generated from a band-keyed template**, from the structured fields, and is never authored free-hand:

| Band | Template opening (fixed) | Forbidden vocabulary |
|---|---|---|
| S1 | *"Examined, not established: {exposure} is **associated with** {mode} in {population}. {confounding_clause}"* | causes, caused by, root cause, because, due to, drives, results in |
| S2 | *"Corroborated hypothesis: {exposure} is **associated with** {mode} across {diversity}. Treatment assignment was {handling}. {residual_clause}"* | same |
| S3 | *"Adjudicated finding, strong evidence: {exposure} **is assessed to shorten time to** {mode} across {diversity}. {residual_clause}"* | causes, root cause |
| S4 | *"Confirmed: {exposure} **causes** {mode} in {population}, confirmed by {confirmation_ref}."* | — |

`{confounding_clause}` and `{residual_clause}` are themselves generated from `residual_confounders[]` and are **not omittable**: a template render with a non-empty residual list and an empty clause fails. Test `fi-language-gate` (§10.3) asserts the forbidden vocabulary never appears in a rendered statement below its unlocking band, over every hypothesis in the reference dataset.

This closes the back channel finding **D23** describes. [03 §7.1](../architecture/03-integration-contracts.md) requires that *"agents must not render them in causal language — a causal statement must cite an adjudicated Failure Intelligence hypothesis,"* and [10 §7.5](10-shared-packages.md) reviews manifest descriptions against it. That rule is only safe if the thing being cited is itself honestly worded. Agents may quote the generated `statement` and must not re-word it; FI's manifests carry that constraint in their task-scoped descriptions.

### 4.6 Recomputation, and why a band can fall

Strength is recomputed when any input changes — new observations, a new method result, a taxonomy supersession (§6.4), a falsification result, or a `strength_rule_version` bump. Recomputation is a **new** `strength` document on the same hypothesis with the prior retained (I5).

**A band may fall, and a fall has consequences.** If a recomputation drops a published hypothesis below S2, every `causal_feature_entry` sourced from it is retired in the next feature-set version (§5.5) and `causal_finding.published` is re-emitted with the new band. A design in which strength can only ratchet upward would be a design in which the first optimistic assessment is permanent.

---

## 5. Causal feature admission

[04 §9](../architecture/04-subapplication-architectures.md): *"**Causal features are versioned and admitted deliberately.** A causal finding becomes a tier-3 model feature only after adjudication and only as a versioned feature-set entry. This prevents a weak hypothesis from silently propagating into operational predictions, and it keeps the PdM contract's `contributing_factors` field meaningful."*

### 5.1 The workflow

| # | Step | Actor | Mechanism | Gate |
|---|---|---|---|---|
| 1 | **Discovery run requested** | Reliability engineer, or a scheduled Flow | `POST /discovery-runs` with a `PopulationSpec` and `method_id` | The §3.2 gate. `refused` ends it here, with a record |
| 2 | **Results ingested** | Domino Job (workload identity) | `POST /discovery-runs/{id}/results` — bulk, idempotent, fenced on `as_of` and `baseline_epoch`. **Never a direct datastore write** ([09 §9.1](09-monorepo-and-conventions.md) item 1, D10/C7) | Rejected if the run's `gate_verdict` is `refused`, or the fence is stale |
| 3 | **Hypothesis drafted** | Discovery orchestrator | `causal_hypothesis` row at `draft`, with `treatment_census_id` (I3) and computed strength (I4) | `ch_fingerprint_live` — a repeat of a prior examination must declare novelty (§7.2) |
| 4 | **Prior examination check** | Orchestrator | The fingerprint lookup of §7.2. A hit attaches the prior finding to the draft | A draft that repeats an `unsupported` fingerprint without `novelty_basis` is refused |
| 5 | **Falsification** | Orchestrator | M5 battery (§3.8). Required for any draft whose computed band is S2+ | A failure routes to `refuted` and retains it |
| 6 | **Adjudication** | Engineering authority | Claim, then `POST /hypotheses/{id}/adjudicate` (§5.2) | `If-Match` on the claimed ETag; dual control where required |
| 7 | **Publication** | Service | `adjudication_state = 'published'`; `causal_finding.published` emitted with the census and handling | `refused_is_never_published`, `published_has_adjudication` |
| 8 | **Feature admission** | Engineering authority, separately | `POST /causal-feature-set-admissions` — a **distinct act** from publishing the finding | `admission_floor` (≥ S2), `s2_is_monitored_only` |
| 9 | **Feature-set publication** | Service | New `causal_feature_set` version published and frozen; `causal_feature_set.updated` emitted with `definition_time` | Definition-time integrity (§5.3) |

**Step 7 and step 8 are deliberately separate.** Publishing a finding is an epistemic act; admitting a feature into operational scoring is an operational one, with a different blast radius. Collapsing them would mean every published finding automatically reaches tier-3 models, which is precisely the silent propagation 04 §9 forbids.

### 5.2 Adjudication authority

```sql
CREATE TABLE failure_intel.adjudication_record (
    record_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_kind       text NOT NULL
        CHECK (subject_kind IN ('hypothesis','attribution','feature_admission',
                                'taxonomy_proposal')),
    subject_ref        text NOT NULL,
    decision           text NOT NULL
        CHECK (decision IN ('approve','reject','downgrade','defer','retire','withdraw')),
        -- 'withdraw' produces adjudication_state = 'withdrawn' [amendment, closes
        -- 52-practitioner-apps.md §13 correction 14]: that state was reachable per
        -- §7.1's "adjudicator judgment, with the reason required" prose, but no
        -- decision value produced it -- the state existed with no path to it.
    band_before        failure_intel.strength_band,
    band_after         failure_intel.strength_band,
    authority_class    text NOT NULL,              -- 03 §7.2.1 vocabulary
    adjudicated_by     text NOT NULL,
    adjudicated_at     timestamptz NOT NULL DEFAULT now(),
    second_adjudicator text,                       -- dual control
    second_adjudicated_at timestamptz,
    claim_etag         text NOT NULL,              -- [AMENDMENT] causal_hypothesis.row_version
                                                    -- AT CLAIM TIME, stringified -- the lease
                                                    -- this decision was made under
    note               text NOT NULL,              -- REQUIRED. A decision with no reason is not one
    evidence_reviewed  jsonb NOT NULL,             -- what was actually in front of the adjudicator
    classification     jsonb NOT NULL,
    -- I4 restated at the adjudication layer: a downgrade may only lower.
    CONSTRAINT downgrade_lowers CHECK (
        decision <> 'downgrade' OR band_after < band_before),
    CONSTRAINT dual_control_paired CHECK (
        (second_adjudicator IS NULL) = (second_adjudicated_at IS NULL))
);
```

**Which authority class.** [03 §7.2.1](../architecture/03-integration-contracts.md) fixes the vocabulary — **[AMENDMENT]** `maintainer | planner | supply_officer | design_authority | fleet_authority | security_officer` (six, not the five originally stated here — `security_officer` was added by amendment 03-1) — and its minimum-authority table enumerates the **eight** `Proposal` kinds of [03 §7.2](../architecture/03-integration-contracts.md) (not six — `purge`/`rewrap` were added by amendment 03-2). **It has no row for a causal finding, a feature admission, or a taxonomy extension.** That is a genuine gap, and this document does not invent a class to fill it. The interim assignment, recorded as **OD-5** (§13):

| Act | Blast radius | Minimum authority (interim) | Dual control |
|---|---|---|---|
| Publish a hypothesis at S1/S2 | class (a finding is class- or NIIN-scoped by nature) | `design_authority` | No |
| Publish at S3/S4 | class | `design_authority` | **Yes** |
| Downgrade or retire a published finding | class | `design_authority` | No — lowering is always permitted, per I4's asymmetry |
| Arbitrate an `Attribution` | item | `design_authority`. **Explicitly not `maintainer`** — arbitrating a PMA/Scheduling disagreement is a reliability-engineering judgment, not a deckplate confirmation | No |
| Admit a `monitored` feature (S2) | class | `design_authority` | No |
| Admit a `standing` feature (S3+) | class | `design_authority` | **Yes** |
| Approve a taxonomy extension | class/fleet | `design_authority` (§6.2) | **Yes** — doc 12 §3.3: vocabulary blast radius is class or fleet by nature |

[03 §7.2.1](../architecture/03-integration-contracts.md) permits Phase 3 to *"add finer-grained roles within a class"* but not to remove the minimum.

**OD-5 resolved.** `[amendment, closes 52-practitioner-apps.md §13 correction 17]` — the wireframe names "Reliability Engineer" as this document's adjudicating persona, but the six-member `AuthorityClass` enum (`31-auth.md` §2.4) has no such role and §13 item 12 forbids a seventh. The persona named on the sheet could not perform the sheet's primary action. Resolved exactly as anticipated above: **`reliability_engineer` is a Keycloak realm sub-role composited into `design_authority`** — it grants everything `design_authority` grants (so the authority-matrix check in `31-auth.md` §6.4 needs no change; a principal holding `reliability_engineer` satisfies any cell requiring `design_authority`) and exists purely so the identity block, the audit record, and the operator console can display the finer-grained role a Failure Intelligence adjudicator actually holds, per this table's use of it. Recorded as **realm role composition**, not a new `AuthorityClass` value — the enum stays six. Billet mapping (which humans hold `reliability_engineer` versus plain `design_authority`) is a personnel-source question, out of this document's scope. Sheet H's `RE` card and footnote need the corresponding correction, from *"review-only"* to *"adjudicates, via `reliability_engineer` composited into `design_authority`."*

**[AMENDMENT] Where it actually surfaces, closing a gap the resolution above left open.** `fathom.identity.authority_classes[]` is filtered to the six canonical `AuthorityClass` values (`31-auth.md` §3.1 rule 3) — `reliability_engineer` is not one of them and would be silently dropped if that were the intended carrier, defeating the display purpose stated above before it ever reached a screen. It instead surfaces on **`fathom.identity.qualifications[]`** (`31-auth.md` §2.3), the identity block's existing free-text realm-sub-role list, unfiltered by the six-value enum and already present in every identity block for an unrelated reason (feeding `anomaly_tag.confirmed`'s reviewer-qualification field). `adjudication_record.authority_class` (currently a bare `text NOT NULL` with no `CHECK`) is written as `design_authority` regardless — the enum stays six there too — with `qualifications` consulted only for display, never for authorization.

**Adjudication requires a claim.** `POST /hypotheses/{id}/claim` obtains a lease; adjudication requires `If-Match` on the claimed ETag and returns 412 otherwise. This is [03 §7.2](../architecture/03-integration-contracts.md)'s rule, applied here for the same reason: *"Without this the eventually-consistent queue permits two approvals."*

**Re-validation at adjudication is mandatory.** Before recording the decision the service re-checks: the census is still the current one for that population and window; `baseline_epoch` bounds in `population_spec` have not been superseded by a `configuration.baseline_changed`; the subject mode's `taxonomy_version` has not been superseded by a `split` or `narrowed` relation (§6.4); and the strength document was computed under the current `strength_rule_version`. Any failure returns 409 with the reason. [03 §7.2](../architecture/03-integration-contracts.md): *"Validation at creation is insufficient."*

### 5.3 The admission gate, in three layers

| Layer | Control |
|---|---|
| **Database** | `admission_floor` — `strength_band_at_admission >= 'S2'`. `s2_is_monitored_only`. Both CHECK constraints on `causal_feature_entry` (§2.6) |
| **API** | `POST /causal-feature-set-admissions` rejects with 422 where the source hypothesis is not `published`, or its band is below S2, or its `gate_verdict` is `refused`, or the adjudicating identity equals the proposing identity for a `standing` admission |
| **Definition-time integrity** | The admitted feature's `definition_ref` / `definition_version` must have `definition_time` **at or before** the close of the source hypothesis's observation window. A definition authored later is hindsight-contaminated (D22) and is rejected outright, not merely capped |

The three layers exist because [12 §8.4](12-reference-data-taxonomy.md) demonstrates the value of the pattern for a directly analogous authority rule: *"Both layers tested independently."* A constraint alone is bypassable by a migration; an API check alone is bypassable by a backfill.

### 5.4 `monitored` versus `standing`

An S2 hypothesis is *corroborated*, not *established*. Admitting its feature as if it were established would reintroduce silent propagation at one band higher. So S2 admissions are structurally provisional:

| Property | `monitored` (S2) | `standing` (S3+) |
|---|---|---|
| Ablation | **Mandatory.** PdM must be able to score with the feature disabled, and the tier-3 evaluation reports both. A feature that does not improve the ablation comparison is retired at its review date | Recommended |
| `review_due` | Required, and short | Required |
| Renders in `contributing_factors` | Yes, but the operator-facing explanation cites the S2 statement template, so the hedge travels with the feature | Yes |
| Retirement on band fall | Automatic (§5.5) | Automatic |

The `review_due` interval is a program decision, not an engineering one, and is **OD-6** (§13). The field is `NOT NULL` so it cannot be silently omitted while the interval is undecided.

### 5.5 Retirement, and the one event that is missing

A published feature is retired when its source hypothesis falls below S2, is refuted, is superseded, or when its `review_due` passes without a re-adjudication, or when a taxonomy split invalidates its population (§6.4). Retirement is expressed as:

- A **new** `causal_feature_set` version — a **major** bump, since a consumer's held reference changes meaning — with the entry carrying `retired_at` and `retirement_reason`.
- `causal_feature_set.updated` emitted, carrying the retirement so PdM can stop binding the feature.
- `causal_finding.published` re-emitted with `finding_class ∈ {unsupported, refuted, superseded}`, so Design Advisory learns that a case's evidentiary basis moved.

**The honest addition this design wants and does not have** is a distinct `causal_finding.retracted` event. [03 §6](../architecture/03-integration-contracts.md)'s catalog gives Failure Intelligence exactly three events, and this document does not add an undeclared one — an undeclared producer event is finding **C4** in reverse. Expressing retraction through `finding_class` on `causal_finding.published` works but overloads a publication event with a withdrawal, which every consumer must remember to branch on. Recorded as **OD-7** (§13).

---

## 6. Taxonomy extension authority

### 6.1 The division of authority, stated exactly

This is the division most easily got wrong, so both sources are quoted rather than paraphrased.

[03 §14](../architecture/03-integration-contracts.md):

> *"**Taxonomy.** Reference Data is the single owner of the unified taxonomy — definition, versioning, publication. Post-Mission Analysis owns tag *assignments*; **Failure Intelligence owns *attributions* and is the sole authority to *extend* the vocabulary**; Scheduling owns findings *codings*. None owns the vocabulary itself `[C8, D31]`."*

[08 §2.8](../architecture/08-standards-alignment.md), the Failure Intelligence projection row:

> *"The **full vocabulary**, and sole authority to extend it. **Owns the content; Reference Data owns registry, versioning, and publication.** Its `Attribution` is the arbitration record when a tag and a findings code disagree. That disagreement is a retained first-class signal, not an error to clean."*

And [12 §7.1](12-reference-data-taxonomy.md)'s one-line summary, which is the operative form:

> *"**Reference Data never decides what a failure mode is. Failure Intelligence never publishes a version.**"*

| Concern | Failure Intelligence | Reference Data |
|---|---|---|
| What a failure mode *is* — its mechanism, signature, cause candidates, consequence class | **Decides.** Approves or rejects every extension | Never decides. Doc 12 DO-NOT-6 |
| Whether an entry enters the register, under what code, at what version | Never | **Decides.** Authors into a draft, publishes, freezes |
| The code value, namespace discipline, `code_authority` | Never assigns | **Owns.** Doc 12's `extension_codes_are_namespaced` guard |
| Semver bump class, supersession relation, crosswalk publication | Supplies the `relation` and `rationale` at adjudication | **Owns** the register mechanics and the published artifact |
| Local storage of vocabulary content | **Prohibited** beyond a read-through cache (I1, doc 12 DO-NOT-1) | The single source |

FI therefore holds **no taxonomy tables**. Its `failure_mode_ref` (§2.2) stores analysis state keyed on Reference Data's `lineage_id`, and its cache is a verbatim copy of served content. Doc 12's `tax-single-source` monorepo scan — *"a static check… asserting no sub-application package contains a taxonomy literal"* — covers `services/failure-intel/` like every other package, and FI's build fails on a violation.

### 6.2 Approving a novel signature proposed by PMA

The end-to-end path, with the exact operations. [08 §2.8](../architecture/08-standards-alignment.md): *"Novel signatures become proposals to Reference Data, adjudicated by Failure Intelligence."*

| # | Step | Who | Operation / mechanism |
|---|---|---|---|
| 1 | A reviewer selects the `is_novel_escape` signature and describes what they saw. **The tag is valid data, not an error** (doc 12 §7.2) | `pma` | PMA stores the tag; FI receives it as `anomaly_tag.confirmed` and it becomes evidence |
| 2 | PMA submits the extension request | `pma` | `POST /api/v1/reference-data/taxonomy/proposals` with `kind = 'novel_signature'`, `proposer_sub_app = 'pma'`, non-empty `evidence[]` with `source_trust` ([03 §7.2](../architecture/03-integration-contracts.md)) |
| 3 | FI learns of it | `failure-intel` | Consumes `proposal.created` on `fathom.reference-data.proposal.v1` ([12 §3.4](12-reference-data-taxonomy.md)) into a local adjudication work-item read model. **Not** a queue FI owns — the authoritative queue is `GET /api/v1/reference-data/taxonomy/proposals` |
| 4 | An FI adjudicator takes the lease | `failure-intel` | `POST /api/v1/reference-data/taxonomy/proposals/{id}/claim`, `If-Match` on the claimed ETag. Doc 12 §7.1: *"Without the claim, an eventually-consistent queue permits two approvals"* |
| 5 | FI assembles the adjudication packet locally | `failure-intel` | The PMA tag and its evidence package; every FI `Attribution` whose `pma_side` carries the escape signature; the current crosswalk candidates for the implicated `equipment_class`; any `CausalHypothesis` over the same population. Persisted as `adjudication_record.evidence_reviewed` |
| 6 | Decision | `failure-intel` | `POST /api/v1/reference-data/taxonomy/proposals/{id}/adjudicate` with `approve` or `reject` and a **required** note. `design_authority` + **dual control** (§5.2, doc 12 §3.3) |
| 7 | Reference Data authors | `reference-data` | Doc 12 §7.1: *"Approval does not publish. It authorises authoring."* Reference Data inserts the entry and the signature crosswalk row into an **open draft** |
| 8 | Reference Data publishes | `reference-data` | `POST /taxonomy/versions/{version}/publish`. Emits `taxonomy_version.published` |
| 9 | FI absorbs the new version | `failure-intel` | §6.4's propagation. The original escape tag is **never rewritten**; on publication it resolves through the crosswalk to the new entry and both remain visible (doc 12 §7.2) |

**Rejection is a first-class outcome.** A rejected `novel_signature` leaves the PMA tag intact and valid — the escape tag was a truthful report of what a reviewer saw — and the rejection note is what tells PMA whether the signature was a duplicate of an existing one, an artifact, or a real observation that does not warrant a vocabulary entry. FI records the rejection locally against the signature so a second identical proposal arrives with the prior attached (the same anti-rediscovery principle as §7).

### 6.3 Proposing a new failure mode from FI's own analysis

Same endpoint, `kind = 'new_failure_mode'`, `proposer_sub_app = 'failure-intel'`. FI is both proposer and approver here, and that is a hazard the design must address explicitly rather than note.

**Four controls on self-approval:**

1. **Separation of duties is enforced, not requested.** The proposing identity may not be the adjudicating identity. Checked by Reference Data at its API boundary against ABAC attributes (doc 12 §3.3) and asserted independently by FI's contributed conformance test `fi-tax-self-approval`. Doc 12's `approver_is_authorised` CHECK only tests the `failure-intel:` prefix and cannot see this — which is why the test exists at the boundary layer where it can.
2. **Dual control is mandatory.** Vocabulary blast radius is `class` or `fleet` by nature (doc 12 §3.3), so two distinct FI-authorized identities are required. Same-identity dual control is a 422 at the boundary.
3. **Evidence is required and is checked locally before submission.** A `new_failure_mode` proposal must reference at least one FI `Attribution` or `CausalHypothesis` that motivated it, with `source_trust = 'program'`. FI's own pre-submission validator refuses to construct a proposal without one — a mode invented from a literature reading with no field observation behind it is not an extension, it is a guess with a UUID. [03 §7.2](../architecture/03-integration-contracts.md)'s non-empty-evidence rule is the floor, not the standard.
4. **The extension request never carries a code.** FI supplies mechanism, signature, consequence class, cause candidates, and `potential_failure_def` (MIL-STD-3034A 3.9.3, [08 §2.3](../architecture/08-standards-alignment.md)); Reference Data assigns the code and the `code_authority`. An FI payload containing a `code` field is rejected — assigning a three-letter code is exactly the fabrication doc 12 DO-NOT-3 prohibits, and FI is the sub-application most tempted to do it.

**Shape the proposal so it exports.** [08 §2.3](../architecture/08-standards-alignment.md): *"Eighteen Data Item Descriptions in the DI-SESS-809xx and 818xx series correspond to the phase artifacts. **Failure Intelligence's `FailureMode` and `Attribution` aggregates should be shaped so they can export into them**, because that is how RCM analysis is contracted."* The proposal payload therefore uses Reference Data's `FailureModeEntry` field names verbatim ([12 §2.3](12-reference-data-taxonomy.md)), so nothing is remapped between FI's proposal and the register's entry, and the GEIA-STD-0007C LSA-050 / LSA-058 export path ([12 §3.1](12-reference-data-taxonomy.md)) is satisfied by construction rather than by a translation layer nobody maintains.

### 6.4 How a `taxonomy_version` bump propagates

FI consumes `taxonomy_version.published`, `taxonomy_entry.superseded`, and `crosswalk.published` ([12 §3.4](12-reference-data-taxonomy.md); these topics are absent from [03 §6](../architecture/03-integration-contracts.md)'s catalog, which doc 12 records as its **OD-7** and this document reflects as **OD-8**).

```
taxonomy_version.published (v_new)
  │
  ├─ 1. Refresh the read-through cache for v_new. The prior version's cache row is retained,
  │     because held references at older versions must remain resolvable (doc 12 §6.4).
  │
  ├─ 2. Bulk forward-resolve every held reference:
  │        POST /api/v1/reference-data/taxonomy/resolve
  │        body: [{lineage_id, held_version}, …]   -> [{lineage_id, target, hops, relation}]
  │     over every Attribution.mode_lineage_id, failure_mode_ref, causal_hypothesis
  │     .subject_mode_lineage, and causal_feature_entry's applicable modes.
  │
  ├─ 3. RECORD the resolution; NEVER rewrite the stored reference.
  │     hops = 0  -> unchanged; nothing to do.
  │     hops > 0  -> a resolution provenance row is written, and the branch below applies.
  │
  ├─ 4. Branch on the supersession `relation`:
  │        renamed | merged | broadened  -> no population change. Provenance recorded only.
  │        split   | narrowed            -> THE POPULATION DEFINITION MAY HAVE CHANGED.
  │        deprecated                    -> the mode may no longer be assigned.
  │
  └─ 5. For split | narrowed | deprecated:
           failure_mode_ref.taxonomy_review_required := true
           every affected causal_hypothesis        -> re-adjudication required
           every derived causal_feature_entry      -> review_due := now (immediate)
```

**Why `split` and `narrowed` are the consequential relations.** A hypothesis is a claim about a *population defined by a failure mode*. When that mode splits into two, the claim's subject no longer exists as a single thing: the evidence may support the claim for one successor and not the other, and averaging across both is exactly the label corruption [08 §2.8](../architecture/08-standards-alignment.md) warns about in a different guise. Such a hypothesis therefore returns to adjudication with the split recorded, and any feature derived from it becomes immediately reviewable rather than quietly continuing to serve tier-3 models under a subject that has been redefined.

**Nothing is rewritten, ever.** [12 §6.2](12-reference-data-taxonomy.md): *"A Failure Intelligence attribution holds `(lineage_id, taxonomy_version)`… All three remain byte-identical across every future version bump."* An FI attribution filed at `1.0.0` still reads `1.0.0` at `4.7.0`, and its meaning is recovered by resolving forward on demand. That is what makes a training set assembled in 2029 across 2026 and 2027 labels auditable rather than *"silently corrupt"*.

**A major bump does not invalidate an in-flight adjudication silently.** §5.2's re-validation rule catches it: an adjudication attempted against a hypothesis whose subject mode was superseded by a `split` since drafting returns 409 with a resolution hint, mirroring doc 12 §7.1's own re-validation behaviour.

### 6.5 The Annex B decision, and why it is FI's problem

Doc 12's **OD-1** — purchase ISO 14224:2016 and transcribe Annex B, or bridge with `FATHOM-EXT-nnn` placeholders — names *"Program management + Failure Intelligence"* as the owner. The consequence for this sub-application is direct and worth stating in one place, because it is a credibility question, not a data-loading one.

[12 §5.4](12-reference-data-taxonomy.md): *"Seven failure-mode codes cannot cover the equipment populations a tier-2/tier-3 demonstration requires. **Failure Intelligence needs enough mode granularity for attribution to be non-trivial**… With seven codes, the crosswalk degenerates toward one-to-one and the design's central property becomes untestable."*

| Path | Effect on Failure Intelligence |
|---|---|
| **(a) Purchase and transcribe** (doc 12's recommendation) | M4 signature matching has real discriminating power; the PMA/Scheduling arbitration record has genuine disagreements to arbitrate; `cause_candidates[]` and `detection_methods[]` are populated, which M4 uses; attributions can claim ISO 14224 conformance |
| **(b) `FATHOM-EXT-nnn` placeholders as a bridge** | M4 degenerates toward one-to-one, so the arbitration record is mostly `both` and the disagreement signal — the whole reason for three capture points — is untestable. Every attribution to a placeholder mode is marked in every rendering, **caps at S2 by cap C-TAX** (§4.3), and **no `causal_finding.published` may claim ISO 14224 conformance**. Placeholders supersede cleanly to real codes on acquisition (doc 12 §5.4), so the bridge is non-destructive |

Under path (b) the demonstration can still show the *mechanism* — gate, census, strength, adjudication, admission — honestly, because none of those depend on vocabulary richness. What it cannot show is attribution that looks like real attribution. That distinction belongs in program material rather than being discovered by a design engineer at a review. Carried as **OD-9** (§13), pointing at doc 12's OD-1.

---

## 7. Negative findings retention

[04 §9](../architecture/04-subapplication-architectures.md): *"**Rejections and negative findings are retained.** A hypothesis examined and found unsupported is valuable knowledge and prevents rediscovery."*

Two distinct jobs are hiding in that sentence — *retain* and *prevent rediscovery* — and only the first is satisfied by not deleting rows. Preventing rediscovery requires the retained finding to be **findable by the next analyst who asks the same question in different words**, which requires a canonical form of "the same question."

### 7.1 Retention: state, not a separate table

A negative finding is a `causal_hypothesis` row in `unsupported`, `refuted`, or `withdrawn`, retained in full — its evidence, its census, its strength document, its method versions, and its adjudication record. There is no second table, deliberately: a separate "negative findings" store would drift in schema and would not be reached by the strength recomputation, the taxonomy propagation, or the fingerprint index.

| State | Meaning | What made it that |
|---|---|---|
| `unsupported` | Examined; the evidence does not support the claim | Band computed at S0/S1 with no path to improvement on the available data, and an adjudicator recorded it |
| `refuted` | Examined; the evidence contradicts the claim | A method contradicted it (§3.9, axis A3 level 0), or M5's falsification battery failed |
| `withdrawn` | The question was ill-posed | Adjudicator judgment, with the reason required |

`claimed_direction` admits `'no_effect'` precisely so that **a null is a first-class hypothesis**. "We tested whether part source affects seal life and found no effect at S3 strength" is one of the most useful things this sub-application can tell Design Advisory, and it is unrepresentable in a schema where every hypothesis must assert an effect.

**Negative findings are published.** `causal_finding.published` carries `finding_class ∈ {unsupported, refuted}` for them, because the four declared consumers need them:

| Consumer | Why a negative finding matters to it |
|---|---|
| `pdm` | An `unsupported` or `refuted` hypothesis whose feature was previously admitted triggers retirement (§5.5). Without the negative, a retired feature looks like an unexplained regression |
| `design-advisory` | *"It is not the design"* is as decisive for a business case as the positive, and prevents a redesign case being built on a hypothesis FI has already broken |
| `fleet-status` | Suppresses a contributing-degradation narrative that rests on a withdrawn claim |
| `maintenance` | Prevents an interval-change rationale surviving its evidentiary basis |

**Retention is permanent, and the purge path is declared.** Nothing in this schema is deleted. Per [03 §13](../architecture/03-integration-contracts.md) and finding D15, the service declares each store as legally immutable or operationally append-only in its README, with envelope-level encryption and crypto-shredding as the remediation mechanism for a classification spillage. Append-only is *"an integrity property, not a licence for unrecoverable data."*

### 7.2 Preventing rediscovery: the fingerprint

```python
# src/fathom_failure_intel/hypotheses/fingerprint.py
#
# Deterministic over the four fields that define the QUESTION, canonicalised so that two
# analysts asking the same question in different orderings collide. Deliberately EXCLUDES
# method, run, window end, and analyst: the same question examined by a better method with
# more data is the same question, and that is the case we want to detect.

def fingerprint(h: HypothesisDraft) -> bytes:
    canonical = {
        "subject_mode_lineage": str(h.subject_mode_lineage),
        "exposure":       canonicalise_exposure(h.exposure),        # kind + ref, definition-agnostic
        "claimed_direction": h.claimed_direction,
        "population":     canonicalise_population(h.population_spec),  # sorted family/class/domain
                                                                       # sets; NOT the item list
        "contrast":       canonicalise_contrast(h.contrast_spec),      # sorted arm keys
    }
    return blake2b(json.dumps(canonical, sort_keys=True).encode(), digest_size=32).digest()
```

The partial unique index `ch_fingerprint_live` (§2.3) permits exactly one live hypothesis per fingerprint. The orchestrator's behaviour on a collision is the mechanism that closes 04 §9's requirement:

| Collision with | Behaviour |
|---|---|
| A `published` hypothesis | Refuse the draft. This question has a live answer; update *it* — recompute strength with the new evidence (§4.6) rather than opening a rival row |
| An `unsupported` / `refuted` / `withdrawn` hypothesis | **Refuse the draft unless `supersedes_hypothesis_id` and `novelty_basis` are both set** (constraint `supersession_declares_novelty`). The prior finding, its census, and its adjudication note are attached to the new draft and shown to the adjudicator |
| Nothing | Proceed |

`novelty_basis` must state what changed, and the orchestrator validates that it is one of the enumerated grounds rather than free text: **more observations** (a materially higher `observation_ratio`), **a new method** (a `method_id` not in the prior's `methods_run`), **a different arm or population**, **a new `taxonomy_version`** (particularly after a `split`, §6.4), **a corrected gate posture** (the prior refused or was capped at A4 level 1 and the new run is restricted or propensity-modeled), or **a new falsification result**. "Re-run with fresh eyes" is not a ground, and the check is what stops the register filling with the same negative finding at six-month intervals.

### 7.3 The surfaces that make retention useful

- `GET /hypotheses?status=unsupported,refuted&mode_lineage_id=&niin=` — the negative-findings register as a normal query.
- `POST /hypotheses/prior-examination-check` — **compute-only, `x-side-effects: none`, `x-agent-eligible`.** Given a proposed subject, exposure, direction, and population, it returns the fingerprint and every prior examination with its state, band, adjudication note, and census. This is the operation a reliability engineer or the Diagnostic Assistant agent calls *before* requesting a discovery run, and it is the difference between a retained negative finding and a findable one.
- Every refused `discovery_run` (§2.7) is queryable alongside them. "We tried and the gate refused for want of a treatment record" is itself knowledge, and it points at a data-capture gap rather than a physical one.

---

## 8. API surface

Base path `/api/v1/failure-intel/…` per [03 §4](../architecture/03-integration-contracts.md). Every operation declares `x-substitution` and `x-side-effects`; `x-agent-eligible` is asserted only where side effects are `none` or `proposal-only` (obligation 8, C1/D11). Annotation semantics and CI validation per [09 §5.1](09-monorepo-and-conventions.md); generation and publication per [10 §5](10-shared-packages.md).

### 8.1 Operations

| Operation | Purpose | `x-substitution` | `x-side-effects` | `x-agent-eligible` |
|---|---|---|---|---|
| `GET /failure-modes?equipment_class=&taxonomy_version=&changed_since=&limit=&cursor=` | FI's analysis annotations joined to the Reference Data projection. Echoes `taxonomy_version` and `code_authority` | `required` | `none` | yes |
| `GET /failure-modes/{mode_lineage_id}?taxonomy_version=` | One mode's annotation. `{id}` is `lineage_id`, Reference Data's resolution key — never the three-letter code | `required` | `none` | yes |
| `GET /hypotheses?niin=&installed_item_id=&mode_lineage_id=&status=&min_strength=&claimed=&awaiting_second_signature=&changed_since=&limit=&cursor=` | 04 §9's surface. `min_strength` takes a band (`S2`), and the response carries `admissible_as_*`. **`claimed` (`any\|none\|me\|other`) and `awaiting_second_signature` added** `[amendment, closes 52-practitioner-apps.md §13 corrections 12 and 15]` — mirroring `30-gateway.md` §4.5's identical filters for the proposal queue. Without them a second adjudicator has no way to see a hypothesis is already claimed, or to find hypotheses awaiting their own signature | `required` | `none` | yes |
| `GET /hypotheses/{id}` | One hypothesis with its generated `statement`, band, and limiting axis | `required` | `none` | yes |
| `GET /hypotheses/{id}/evidence` | 04 §9's surface. Evidence records with `source_trust` and D22 definition-time fields | `required` | `none` | yes |
| **`GET /hypotheses/{id}/treatment-census`** | **The D21 transparency surface.** The full per-arm census, gate verdict, propensity spec reference, balance diagnostics, and residual confounders behind this hypothesis | `required` | `none` | yes |
| **`POST /populations/preflight`** | **The gate, callable without running an analysis.** Body: a `PopulationSpec` and `method_id`. Returns the census and the verdict. Computational, no state change — the `x-side-effects: none` POST pattern C1/D11 exists for | `required` | `none` | yes |
| `POST /hypotheses/prior-examination-check` | §7.3. Fingerprint plus every prior examination. Computational | `required` | `none` | yes |
| `POST /hypotheses/{id}/claim` | Adjudication lease. `If-Match` required ([03 §7.2](../architecture/03-integration-contracts.md)) | `required` | `state-changing` | no |
| `POST /hypotheses/{id}/adjudicate` | 04 §9's surface. Approve, reject, downgrade, defer. `If-Match` on the claimed ETag; re-validation per §5.2 | `required` | `state-changing` | no |
| `GET /attributions?installed_item_id=&mission_id=&niin=&mode_lineage_id=&changed_since=&cursor=` | 04 §9's surface. Both sides of the arbitration and the full candidate set | `required` | `none` | yes |
| `GET /attributions/{id}` | One attribution, with `agreement_class` and both filings as filed | `required` | `none` | yes |
| `POST /attributions/{id}/arbitrate` | Record or revise the arbitration. A revision creates a new row with a supersession link (I5) | `required` | `state-changing` | no |
| `GET /causal-feature-sets?version=&changed_since=&limit=&cursor=` | 04 §9's surface, **with doc 12's OD-6 corrected** — see §8.2 | `required` | `none` | yes |
| `GET /causal-feature-sets/entries?version=&feature_key=&equipment_family=&cursor=` | Entries with `definition_ref`, `definition_version`, `definition_time`, `strength_band_at_admission`, `standing`, `review_due` | `required` | `none` | yes |
| `POST /causal-feature-set-admissions` | §5.1 step 8. A resource creation, not a verb on a version path. Three-layer gate per §5.3. **Body `{feature_key, definition_ref, definition_version, definition_time, computation_spec, source_hypothesis_id, standing, applicable_scope, review_due?}`** `[amendment, closes 52-practitioner-apps.md §13 correction 16]` — every `NOT NULL` semantic column of `causal_feature_entry` (§2.6) except the four the service derives and never accepts from the caller: `feature_set_version` (the open draft), `strength_band_at_admission` and `treatment_census_id` (both read off the source hypothesis), and `admission_record_id` (minted by the adjudication this operation itself is gated on). `review_due` defaults per §5.4's cadence if omitted | `internal` | `state-changing` | no |
| `POST /discovery-runs` | Request a run. Applies the §3.2 gate synchronously and may return 409 with the gate problem type | `internal` | `state-changing` | no |
| `GET /discovery-runs?status=&method_id=&cursor=` | Run register, **including `status=refused`** with the reason and census | `internal` | `none` | no |
| `POST /discovery-runs/{id}/results` | Bulk, idempotent, **fenced** result ingest from a Domino Job under a workload identity. The only write path for discovery output ([03 §4](../architecture/03-integration-contracts.md) bulk writes, D10/C7) | `internal` | `state-changing` | no |
| `POST /causal-feature-sets/{version}/publish` | Publish and freeze a draft feature set | `internal` | `state-changing` | no |
| `GET /healthz`, `GET /readyz`, `GET /metrics` | Per [03 §4](../architecture/03-integration-contracts.md), including read-model lag and the staleness bound of §11.3 | `internal` | `none` | no |

### 8.2 Two conventions corrected, and one carve-out

**Doc 12's OD-6 is resolved here.** [12 §3.2](12-reference-data-taxonomy.md) records it: *"Document 04 §9 lists `GET /causal-feature-sets/{version}` on Failure Intelligence, which violates the same rule. It is not this document's to fix, but it should be raised — the pattern will be copied otherwise."* [03 §4](../architecture/03-integration-contracts.md) is explicit — *"Version selectors are query parameters, never path identifiers `[C24]`"* — so the conforming form is `GET /causal-feature-sets?version=`, and that is what the OpenAPI contract publishes. `GET /causal-feature-sets` with no `version` returns the current published set and echoes it in the body and in an `ETag`; it never returns a draft.

**`POST /causal-feature-sets/{version}/publish` is legal** because `{version}` there is the resource being acted on, not a version *selector* — the same shape as doc 12's `POST /taxonomy/versions/{version}/publish`. Selecting a representation is a query parameter; naming the resource a state transition applies to is a path segment.

**One naming carve-out**, enumerated in `x-naming-carve-outs` with its reason per [03 §4](../architecture/03-integration-contracts.md) `[C23]`: `POST /populations/preflight` is a computational sub-resource action on a collection that has no read surface (FI does not serve populations; it evaluates them). The alternative, `POST /population-preflights`, would model a preflight as a persisted resource — which it is not, since the census it persists is reachable through `GET /hypotheses/{id}/treatment-census` and `GET /discovery-runs`.

### 8.3 Why `POST /populations/preflight` is agent-eligible and matters

It is the operation that makes the D21 gate a shared, inspectable fact rather than an internal one. Before PdM admits a feature or Design Advisory builds a case, either can ask: *for this population and this method, what does the treatment census look like, and would the gate let it run?* The answer arrives with no analysis, no state change, and no adjudication — which is exactly the compute-only POST profile [03 §4.1](../architecture/03-integration-contracts.md) sanctions and finding C1/D11 exists to protect.

It is also the operation the Diagnostic Assistant and Redesign Case Builder agents need in order to avoid asserting a causal claim whose basis the gate would refuse. Manifests selecting it carry a task-scoped description stating that a `refused` verdict means *no causal claim may be made from this population*, and [10 §7.5](10-shared-packages.md)'s manifest description review checks for it.

---

## 9. Events

Topics: `fathom.failure-intel.causal_finding.v1`, `fathom.failure-intel.failure_mode.v1`, `fathom.failure-intel.causal_feature_set.v1`. Naming per [03 §5.1](../architecture/03-integration-contracts.md) `[C26]`. **No proposal topic** — FI accepts no agent proposals (§1.4).

### 9.1 Published — exactly the three in the catalog

`producer = 'failure-intel'` and **`producer_node = 'enterprise'` always**, since FI has no edge profile ([11](11-outbox-sync-library.md)). The field is populated rather than omitted: [03 §5.4](../architecture/03-integration-contracts.md) makes it required, and a consumer's dedup key is `(producer, producer_node, monotonic_seq)`.

| Event | Payload | Scope / partition key | Consumers ([03 §6](../architecture/03-integration-contracts.md)) |
|---|---|---|---|
| `causal_finding.published` | `hypothesis_id`; failure mode as `(lineage_id, taxonomy_version, code, code_authority)`; `exposure`; `claimed_direction`; generated `statement`; `finding_class`; `strength_band`; `band_limiting_axis`; `strength_rule_version`; **`treatment_handling`**; `gate_verdict`; `treatment_census_ref`; `population_spec`; `admissible_as_causal_feature`; `admissible_as_primary_redesign_driver`; adjudication provenance; `classification` with `inherited_from` | `niin` or `class` | `pdm`, `design-advisory`, `fleet-status`, `maintenance` |
| `failure_mode.attributed` | `attribution_id`; `installed_item_id` **or** `niin`; mode reference; `confidence`; `agreement_class`; the **full** `candidate_modes[]`; `taxonomy_version`; `baseline_epoch`; adjudication provenance | `installed_item` or `niin` | `design-advisory`, `pdm` |
| `causal_feature_set.updated` | `feature_set_version`; `taxonomy_version`; `strength_rule_version`; per entry: `feature_key`, `definition_ref`, `definition_version`, **`definition_time`**, `computation_spec`, `source_hypothesis_id`, `strength_band_at_admission`, `standing`, `review_due`, `applicable_scope`, and `retired_at` / `retirement_reason` where retired | `fleet` (a feature set is fleet-wide; [03 §5.4](../architecture/03-integration-contracts.md) makes `fleet` the one scope requiring no subject identifier) | `pdm` |

Three payload notes:

- **`treatment_assignment handling` is a catalog-mandated field, not an addition.** [03 §6](../architecture/03-integration-contracts.md)'s row for `causal_finding.published` reads *"failure mode, hypothesized cause, evidence strength, affected population, **treatment-assignment handling**."* It ships as `treatment_handling` plus `gate_verdict` plus a resolvable `treatment_census_ref`, because the declaration alone does not tell a consumer whether the declaration was *satisfied*.
- **`definition-time` is likewise catalog-mandated** on `causal_feature_set.updated` (*"feature definitions and versions available to tier-3 models, definition-time"*), and it is what lets PdM detect D22 leakage in its own training assembly.
- **Nothing large is inlined** (D27). Census details, evidence bundles, discovery artifacts, and hull lists are references into the API or object store. A feature-set update carries definitions, never observations.

### 9.2 Consumed — exactly the eight in the catalog, plus Reference Data's

No wildcards; every type is named explicitly (C38). Each feeds a read model rebuilt from `changed_since` reads, never from the bus (D5).

| Event | Producer | What FI does with it | Read model |
|---|---|---|---|
| `anomaly_tag.confirmed` | `pma` | The supervised signal. Evidence, and the `pma_side` of an arbitration. Carries its `taxonomy_version` as filed | `tags` |
| `anomaly_tag.rejected` | `pma` | A labeled negative. Evidence, and input to the negative-findings register | `tags` |
| `mission.completed` | `telemetry` | Mission boundaries for windowing and mission-scoped attribution | `missions` |
| `maintenance_action.recorded` | `maintenance` | **The treatment record and the label stream.** 3-M codes as filed for the `maintenance_side` of an arbitration; `triggering_driver` / `triggering_prediction_id` / `policy_version` for the census | `maintenance_action_projection` (schema `failure_intel_treatment`) |
| `telemetry.batch_ingested` | `telemetry` | Data availability and window quality flags. FI reads sample data through Telemetry's API, not from the event | `telemetry_windows` |
| `installed_item.removed` | `registry` | Removal with a failure indicator triggers an attribution candidate; also closes the item's exposure window | `items` |
| `configuration.baseline_changed` | `registry` | **A correctness signal.** Bounds `population_spec.baseline_epoch`; a redesign changes the item, so a hypothesis's population may no longer be the population it was drawn from. The antecedent rule of [03 §5.4](../architecture/03-integration-contracts.md) applies — an event ahead of the local configuration read model is **blocked** (D3/D4) | `configuration` |
| `prediction.updated` | `pdm` | **Treatment assignment only, never evidence** (§1.5). Resolves `triggering_prediction_id` to the prediction covariates the propensity model requires (§3.3 P1) | `prediction` (schema `failure_intel_treatment`; unreachable from `methods.*`) |
| `taxonomy_version.published`, `taxonomy_entry.superseded`, `crosswalk.published`, `proposal.created`, `proposal.adjudicated` | `reference-data` | §6.2's work items and §6.4's propagation | `taxonomy_cache`, `taxonomy_proposal_workitems` |

The Reference Data topics are declared consumers in [12 §3.4](12-reference-data-taxonomy.md) but absent from [03 §6](../architecture/03-integration-contracts.md)'s catalog, which covers the nine sub-applications and not the platform services. Until they are added, FI's consumer-driven conformance tests against them cannot be written — doc 12's OD-7, carried here as **OD-8**.

### 9.3 The inbox rule, applied where it bites hardest

Every consumer records receipt and applies state in **one** transaction; where impossible, only rows with `processed_at` set suppress redelivery (D2, [03 §5.2](../architecture/03-integration-contracts.md)). For FI the highest-consequence instance is `maintenance_action.recorded`: a receipt recorded before the projection commits permanently suppresses that action on redelivery, and a **missing** action is indistinguishable from a policy-independent population in the census. The inbox defect would therefore manifest not as a missing record but as a *cleaner-looking gate*, which is the worst available failure mode. §11.3's staleness bound and §10.4's fault-injection test both target it.

---

## 10. Testing

Conformance suite at `packages/contracts/conformance/failure-intel/`, structured per [03 §10](../architecture/03-integration-contracts.md): contract, event, fault-injection, consumer-driven, manifest, and a reference dataset. Test IDs are the suite's stable names.

### 10.1 The reference dataset

The suite's fixtures come from [13](13-synthetic-data-generator.md)'s generator, at the `profiles/ci.yaml` reduced profile for per-commit runs and the full profile before release. Three artifacts are required and their access discipline is the generator's, not this service's:

| Artifact | Used for | Access |
|---|---|---|
| Observed partitions — configuration, telemetry, maintenance records, tags | Every test. The only data FI's own code paths may read | Normal service credentials |
| `holdout/manifest.parquet` | The `restricted_to_policy_frozen` path. `policy_frozen` is **visible to consumers on purpose** ([13 §10.2](13-synthetic-data-generator.md)) | Normal service credentials |
| `truth/` — `true_failure_time`, `residual_life_at_censoring`, `censored_informatively`, `triggering_driver` | **Assertions only**, in the harness, under an explicit `EvaluationContext` | [13 §8.6](13-synthetic-data-generator.md)'s evaluation role. FI service code has no read permission, and a repository-wide scan fails the build on any `*.truth.parquet` reference outside the harness |

That separation is what makes §10.2's assertions meaningful: the method under test cannot see the answer it is being scored against.

### 10.2 Confounding resistance — the required test

**`fi-confound-resist`.** This is the test D21's remedy demands, and it asserts the gate is a runtime control rather than a documented intention. It runs M3 (`M3.compop`) against a generator scenario the generator **deliberately confounds** — [13 §8.4](13-synthetic-data-generator.md) guarantees the necessary properties: the intervention policy acts on a noisy prediction stream, `policy_version` changes at least once in the window, interventions compete for bounded maintenance capacity so queue position is a real confounder, and [13 §9.10](13-synthetic-data-generator.md) drops `triggering_driver` on some records.

The contrast under test is two arms of the same spotlight family on different hulls whose model-assigned intervention fractions differ materially. Four cases, all required:

| Case | Setup | Assertion |
|---|---|---|
| **A — refusal on an undeclared method** | A method variant identical to M3 but declaring `treatment_handling = 'not_applicable'` | **`register()` raises `MethodRegistrationError` at import.** The service does not start. Asserted by importing the variant module inside `pytest.raises` |
| **B — refusal on an unsatisfied declaration** | M3 declaring `propensity_modeled` with a `PropensitySpec` that **omits `policy_version`**, against a census showing `policy_version_count = 2` | `POST /discovery-runs` returns **409** with problem type `urn:fathom:problem:failure-intel:treatment-assignment-gate`; **no `causal_hypothesis` row exists**; a `discovery_run` row exists with `status='refused'`, a non-null `gate_reason` naming precondition **P2**, and a persisted `treatment_census_id`. The same shape is asserted for each of P1, P3, P4, P5 independently |
| **C — correction, two-sided** | M3 correctly specified: `propensity_and_ipcw`, all §3.3 preconditions passing | **Both sides asserted.** (i) The **naive unadjusted** contrast is biased in the direction the generator's truth partition establishes, and the bias is statistically significant by a bootstrap over items at α = 0.05. (ii) The **corrected** estimate recovers the truth-partition effect within the declared tolerance, and its confidence interval covers it. A test asserting only (ii) would pass on a dataset with no confounding to resist |
| **D — restriction, and its honest limit** | M3 declaring `restricted_to_policy_frozen` | The gate rewrites the population to the holdout stratum ∩ requested; `effective_population_spec` is recorded; the re-census returns `max_confounding_risk_fraction = 0`; the resulting hypothesis carries `gate_verdict='restricted'` and axis A4 level 3. **And**: where the restricted stratum falls below the method's event requirement the run **refuses** — [13 §10.1](13-synthetic-data-generator.md) makes this the *expected* outcome for per-family contrasts (*"10% of ~250 spotlight items is ~25 items — below the n ≥ 50 item-horizon calibration gate… for most per-family cells"*), so the test asserts a refusal at family granularity and a success at aggregate granularity |

Case C is deliberately shaped as [13 §16.3](13-synthetic-data-generator.md)'s two-sided corridor: the generator asserts both that the signal exists with noise off (G-1) and that trivial baselines fail with noise on (G-2), because *"either alone is satisfiable by an invalid dataset."* The same logic holds here. A confounding-resistance test that only checks the corrected estimator is satisfiable by a dataset with no confounding, and one that only checks the gate refuses is satisfiable by a gate that refuses everything.

**`fi-confound-adversarial` — guarding the guard.** A deliberately cheating method adapter that bypasses `population.load_population` and reads the repository or the prediction read model directly is committed under `tests/adversarial/`, and the test asserts that the import-linter contract **fails** on it and that CI would therefore block. This mirrors [13 §8.3](13-synthetic-data-generator.md)'s `test_veil_cheating.py` and its reasoning verbatim: *"A harness that cannot detect a cheating policy cannot certify an honest one, so this test guards the guard. It is a required test, not an optional one."*

**`fi-confound-unknown-driver`.** A population in which some records have `triggering_driver` absent and **no** record has a model-assigned driver. Asserts `unknown_count > 0`, `confounding_risk_fraction > 0`, and that the gate treats the population as confounded — not clean. This is the fail-safe direction of §2.1, and it is the assertion that would fail if someone "fixed" the mapping to default missing drivers to periodicity.

**`fi-confound-feedback-provenance`.** An exposure that is a `feature_key` from a published `causal_feature_set`, in a window whose `policy_version` mapping cannot be evaluated. Asserts `feedback_provenance = 'unknown'` and that the gate refuses or restricts (§3.2). Asserts the same for an explicitly contaminated mapping once OD-1 is resolved; until then the test pins the conservative default so a future resolution cannot silently loosen it.

### 10.3 Framing, strength, and admission

| Test | Asserts |
|---|---|
| `fi-strength-monotone` | Degrading any single axis by one level never raises the band; the band equals the axis minimum after caps; `band_limiting_axis` equals the argmin under the declared tie order. Property-based over generated strength documents |
| `fi-strength-no-upgrade` | An adjudicator cannot raise a band, at the API boundary **and** by the `override_lowers_only` constraint. Both layers tested independently |
| `fi-strength-caps` | C-DT caps at S1 for a `fail`/`unknown` definition-time integrity; C-TAX caps at S2 for a `fathom-extension` subject mode; `caps_applied[]` records both |
| `fi-strength-rule-version` | Two hypotheses computed under different `strength_rule_version` values are never compared by band in any served response; a recomputation under a new rule version writes a new strength document and retains the prior |
| **`fi-language-gate`** | **Over every hypothesis in the reference dataset**, the rendered `statement` contains no vocabulary forbidden at its band (§4.5) — no "causes", "root cause", "because", "due to", "drives", "results in" below S4. A residual-confounder list that is non-empty with an empty `{residual_clause}` fails the render |
| `fi-admission-floor` | An S1 hypothesis cannot be admitted, at the API (422) and at the database (`admission_floor`). An S2 admission with `standing='standing'` is rejected by `s2_is_monitored_only` |
| `fi-admission-definition-time` | A feature whose `definition_time` postdates the source hypothesis's window close is **rejected**, not capped (§5.3). D22 |
| `fi-admission-separation` | For a `standing` admission the adjudicating identity may not equal the proposing identity; dual control requires two distinct identities |
| `fi-featureset-freeze` | After publication, an `UPDATE` of any semantic column on `causal_feature_entry` raises; a `DELETE` raises; a second retirement marking raises. Executed against the live trigger, not mocked (doc 12 §8.2's pattern) |
| `fi-featureset-retire-on-fall` | Recomputing a source hypothesis below S2 produces a major feature-set bump with the entry retired and `causal_feature_set.updated` emitted carrying the retirement |
| `fi-prediction-not-evidence` | `evidence_kind` has no `prediction` member; an API attempt to attach one returns 422; the import-linter contract forbidding `methods.* -> readmodels.prediction` is present and passing. Three layers, all asserted (§1.5) |
| `fi-method-declares` | Every registry entry has a non-null `treatment_handling`, non-empty `known_failure_modes`, a `PropensitySpec` where the handling implies one, and a `min_events_expression`. Enumerated over the live registry, so a new method cannot be added without them |

### 10.4 Attribution, taxonomy, and events

| Test | Asserts |
|---|---|
| `fi-attr-retains-both` | A deliberately disagreeing tag/finding pair produces an attribution with both sides populated, `agreement_class ≠ 'both'`, and the **full** candidate set. Fails if any candidate is dropped or the response is scalar-valued. Contributed into Reference Data's suite as the consumer half of `tax-xw-reconcile-retains` ([12 §8.3](12-reference-data-taxonomy.md)) |
| `fi-attr-version-skew` | A tag filed at `1.0.0` and a finding filed at `1.1.0` resolve **per side at each side's own held version**, then compare at the target. Resolving both directly at the target fails the test |
| `fi-attr-no-limit-one` | No code path applies `LIMIT 1`, `ORDER BY … LIMIT`, or a "primary candidate" selection to a candidate-mode set. Static check plus a behavioural assertion on the API (doc 12 DO-NOT-2) |
| `fi-tax-no-content` | FI's contribution to doc 12's `tax-single-source`: no taxonomy literal — no code list, signature list, 3-M list, or definition string — anywhere under `services/failure-intel/` |
| `fi-tax-self-approval` | A `new_failure_mode` proposal whose adjudicating identity equals the proposing identity is rejected at Reference Data's boundary; dual control with the same identity twice is rejected. Contributed into Reference Data's `tax-gov-*` family |
| `fi-tax-no-code-in-payload` | An FI extension payload containing a `code` field is rejected before submission (§6.3 control 4) |
| `fi-tax-split-review` | Publishing a taxonomy version that **splits** a mode FI holds sets `taxonomy_review_required`, moves affected hypotheses to re-adjudication, and sets `review_due = now` on every derived feature entry (§6.4) |
| `fi-tax-never-rewritten` | Snapshot every FI attribution row and hash it; publish two taxonomy versions including a rename, split, merge, and deprecation; re-snapshot and assert **every attribution row is byte-identical**. The mirror of doc 12's `tax-ver-historical-labels`, from the consuming side |
| `fi-event-envelope` | Every published event carries the full [03 §5.4](../architecture/03-integration-contracts.md) envelope including `producer_node = 'enterprise'` and the complete `clock` block with all six `sync_quality` sub-fields |
| `fi-event-catalog-parity` | `events/catalog.py` `PUBLISHES`/`CONSUMES` equal `helm/values.yaml` equal [03 §6](../architecture/03-integration-contracts.md)'s rows for `failure-intel`. `python tools/check_event_catalog.py` exits 0 (C3–C5, C37, C38) |
| `fi-event-census-carried` | Every `causal_finding.published` carries `treatment_handling`, `gate_verdict`, and a **resolvable** `treatment_census_ref`; every `causal_feature_set.updated` carries `definition_time` on every entry. The two catalog-mandated fields of §9.1 |
| `fi-fault-inbox` | Fault injection: interrupt between inbox receipt and the `maintenance_action_projection` commit; assert the event is **redelivered** and the projection converges. §9.3's failure mode — a suppressed action makes the census look cleaner than the world is |
| `fi-fault-no-state-without-event` | Interrupt mid-adjudication and mid-publication; assert no state change without its event, per obligation 2 |
| `fi-rediscovery-blocked` | A draft repeating an `unsupported` fingerprint without `novelty_basis` is refused; with an enumerated `novelty_basis` it proceeds and the prior finding is attached to the adjudication packet. `ch_fingerprint_live` asserted at the database independently |
| `fi-negative-published` | An `unsupported` and a `refuted` hypothesis each emit `causal_finding.published` with the matching `finding_class`; a `no_effect` claimed direction round-trips |

### 10.5 Platform obligations

Per [03 §10](../architecture/03-integration-contracts.md) and [03 §15](../architecture/03-integration-contracts.md), and reproduced from [09 §8](09-monorepo-and-conventions.md) without removal: `changed_since` snapshot reads over every projected aggregate; cursor pagination; RFC 9457 problem details with `urn:fathom:problem:failure-intel:*` types declared in the spec; `ETag`/`If-Match`; `Idempotency-Key` on all unsafe methods; `X-Correlation-Id` propagation to every log line, event, and downstream call; `X-Classification` on every response with per-field redaction; classification `inherited_from` as the union of inputs on every derived value (D13 — a causal finding is a derived value over tags, findings, and telemetry, and its label is their union); fault injection asserting no state change without its event; and OpenAPI annotation coverage with `x-agent-eligible` only where side effects are `none` or `proposal-only`.

---

## 11. Deployment and operations

### 11.1 Placement

Scaffold per [09 §4](09-monorepo-and-conventions.md), at `services/failure-intel/`, package `fathom_failure_intel`. The layering is mandatory and unvaried: `api → services → repositories → models`, with `services/` owning the transaction boundary and the outbox call.

One service-specific addition to the skeleton, and it is the structural half of §3.2:

```
src/fathom_failure_intel/
├── api/v1/                  # hypotheses, attributions, failure_modes, causal_feature_sets,
│                            #   discovery_runs, populations
├── population/              # THE GATE. The only path from a spec to rows
│   ├── loader.py            #   load_population() -> GatedPopulation  (§3.2)
│   ├── census.py            #   compute_census()                      (§2.8)
│   ├── treatment.py         #   the ONLY reader of schema failure_intel_treatment
│   └── holdout.py           #   the policy-frozen restriction rewrite
├── methods/                 # M1…M5 adapters. May import `population`, nothing below it
│   └── registry.py          #   register() — the import-time D21 check (§2.7)
├── strength/                # rules.py, versioned by strength_rule_version (§4.4)
│   └── templates.py         #   the band-keyed statement templates (§4.5)
├── adjudication/            # claim leases, re-validation, adjudication records
├── taxonomy/                # the Reference Data client, cache, and forward resolution (§6)
├── events/                  # catalog.py, publishers, inbox handlers
├── readmodels/              # tags, missions, items, configuration, telemetry_windows
│   └── prediction.py        #   UNREACHABLE from methods.* by import-linter contract
└── repositories/            # the only place SQL is written
```

`importlinter.ini` contracts, CI-blocking:

```ini
[importlinter:contract:methods-go-through-the-gate]
name = Method adapters cannot bypass the treatment-assignment gate
type = forbidden
source_modules  = fathom_failure_intel.methods
forbidden_modules =
    fathom_failure_intel.repositories
    fathom_failure_intel.readmodels.prediction
    fathom_failure_intel.population.treatment

[importlinter:contract:strength-is-pure]
name = Strength derivation reads no data
type = forbidden
source_modules  = fathom_failure_intel.strength
forbidden_modules = fathom_failure_intel.repositories, fathom_failure_intel.readmodels
```

The second contract exists because a strength rule that can query is a strength rule that can be tuned to the answer.

### 11.2 Planes, stores, and Domino

Per [04 §9](../architecture/04-subapplication-architectures.md): *"service and adjudication workflow on the Sustainment Plane. All causal discovery executes in Domino as Jobs and Flows, with exploratory analysis in Workspaces. Practitioner-facing causal exploration is a Domino App, since its audience is reliability engineers who hold Domino accounts."*

| Concern | Decision |
|---|---|
| Service and adjudication UI | Sustainment Plane. **Enterprise only — no edge profile** ([11](11-outbox-sync-library.md)). Outbox, inbox, and clock discipline implemented without exception (obligation 11) |
| Discovery execution | Domino Jobs and Flows from `models/causal/`. Results return through `POST /discovery-runs/{id}/results` under a workload identity — **a Domino Job is an API client, never a database client** ([09 §9.1](09-monorepo-and-conventions.md) item 1) |
| Practitioner surface | A Domino **App**, not an Extension — [02](../architecture/02-domino-platform-assessment.md) rules Extensions out for self-managed OpenShift and air-gap, and finding **D26** records the assumption as a platform blocker. Subject to D26's hosting caps and the 300 s timeout, so long-running exploration is a Job, not an App request |
| Data stores | PostgreSQL, **one logical database**, schemas `failure_intel` and `failure_intel_treatment` (obligation 13, D33). Object storage for discovery artifacts and evidence bundles, immutable once a hypothesis references them |
| Conflict policy | The [03 §11](../architecture/03-integration-contracts.md) default accepted explicitly in the README: **enterprise-authoritative, not edge-writable**, for every aggregate (obligation 16, C20) |
| NetworkPolicy egress | Default-deny plus explicit allow: `reference-data`, `telemetry`, `registry`, `pma`, `maintenance` (read APIs), the broker, the object store, and its own database. **No peer for `pdm`** — the prediction data arrives by event, and a synchronous path would invite exactly the evidence use §1.5 forbids |

### 11.3 The staleness bound — a confounding control, not a freshness nicety

Obligation 14 requires that *"any computation with a correctness dependency on freshness declares a staleness bound and refuses to run outside it."* For FI the dependency is unusually sharp, and it is worth stating why rather than picking a number and moving on.

**A lagging `maintenance_action.recorded` projection does not make the census stale. It makes it wrong in the reassuring direction.** Actions not yet projected are actions the census does not count — and the actions most likely to be in flight are recent ones, which in a prediction-driven fleet skew model-assigned. A lagging projection therefore reports a *lower* `confounding_risk_fraction` than the truth, and the gate is more likely to say `proceed`.

So:

- Every `discovery_run` records `read_model_lag_at_start` **per consumed stream**, and it is retained with the run.
- Discovery **refuses** to start when the `maintenance_action.recorded` or `prediction.updated` projection lag exceeds the declared bound, incrementing `fathom_staleness_refusals_total`. The refusal is a `discovery_run` row with `status='refused'`, like every other refusal.
- `/readyz` exposes per-stream lag; the bound is a chart value.
- The bound's **value** is a program decision informed by the capacity model ([05 §4.6](../architecture/05-architecture-review-findings.md)) and is **OD-10** (§13). The field is required so it cannot be silently absent while the value is undecided.

`sync_quality` and `dispersion_ms` from [03 §5.4](../architecture/03-integration-contracts.md) are retained on every ingested event, permanently. An analysis window whose boundary falls inside a period of degraded time sync is a window whose event ordering is contestable, and the run records the epsilon rather than discovering it at an audit.

### 11.4 Observability

Beyond the shared surface, four metrics exist because they are the ones that reveal this service failing quietly:

| Metric | Why |
|---|---|
| `fathom_fi_gate_verdicts_total{verdict, method_id}` | A sudden collapse in `refused` is not good news; it usually means a mapping changed or a projection lagged |
| `fathom_fi_confounding_risk_fraction{method_id}` (histogram) | The distribution of what the gate is actually seeing. A drift toward zero warrants investigation, not celebration |
| `fathom_fi_unknown_driver_fraction` | Rising `unknown` is a capture-discipline regression in Scheduling, visible here first |
| `fathom_fi_published_by_band_total{band}` | A published population drifting toward high bands without a corresponding rise in test evidence is the signature of grade inflation in adjudication |

---

## 12. Explicit DO-NOT list

Each entry carries the finding or source that makes it a defect rather than a preference. A reviewer may cite the ID and stop reading.

**DO-NOT-1 — Do not run comparative population analysis on a population containing model-assigned interventions without modeling the propensity.**
Not "for the demo". Not "the fractions look small". Not "we'll note it in the write-up". This is finding **D21**'s remedy verbatim, and it is enforced at four layers: `register()` at import (§2.7), the gate at the population loader (§3.2), the `contrast_requires_handling` CHECK (§2.3), and `refused_is_never_published` (§2.3). Restricting to the policy-frozen stratum ([06 §2](../architecture/06-demo-decisions-and-assumptions.md)) is the sanctioned alternative; proceeding is not. *Enforced by `fi-confound-resist`, `fi-confound-adversarial`, `fi-method-declares`.*

**DO-NOT-2 — Do not treat a missing `triggering_driver` as policy-independent.**
Absent, or a value outside the declared mapping, classifies as `unknown` and counts as confounding risk. [13 §9.10](13-synthetic-data-generator.md) generates the missingness deliberately because it *"is the realistic production condition."* Defaulting it to periodicity is how a confounded population passes a clean gate, and the resulting finding is wrong in a direction nobody checks. *Enforced by `fi-confound-unknown-driver`.*

**DO-NOT-3 — Do not present a hypothesis as an established cause.**
[04 §9](../architecture/04-subapplication-architectures.md): *"Presenting algorithmically derived causes as established fact to a design authority would be both wrong and, on first contradiction, fatal to the program's credibility."* Causal verbs are unlocked at S4 only, statement text is generated from the band-keyed template and never authored, and agents may quote but not re-word it. This closes **D23**'s back channel, and [03 §7.1](../architecture/03-integration-contracts.md)'s rule — *"a causal statement must cite an adjudicated Failure Intelligence hypothesis"* — is only safe if the cited statement is itself honestly worded. *Enforced by `fi-language-gate`.*

**DO-NOT-4 — Do not store taxonomy content locally beyond a reference and a read-through cache.**
Not a code list "for validation". Not a signature enum in a form. Not a definition string in a docstring rendered to a user. FI holds `(lineage_id, taxonomy_version)` and a verbatim cache of served content. This is finding **C8** / **D31**, fixed once in doc 12; the build must not reintroduce it, and DoDI 8320.02's registration claim does not survive a second owner. *Enforced by doc 12's `tax-single-source` and `fi-tax-no-content`.*

**DO-NOT-5 — Do not let a prediction become evidence.**
[04 §9](../architecture/04-subapplication-architectures.md): `prediction.updated` *"is never used as evidence for a causal finding."* `evidence_kind` has no `prediction` member, the projection lives in its own schema, and the import-linter keeps method code away from it. A model's output as input to the causal analysis that produces the model's features is **D20**'s cycle closing on itself. *Enforced by `fi-prediction-not-evidence`.*

**DO-NOT-6 — Do not admit a causal feature below S2, and do not admit an S2 feature as `standing`.**
[04 §9](../architecture/04-subapplication-architectures.md): admission *"prevents a weak hypothesis from silently propagating into operational predictions, and it keeps the PdM contract's `contributing_factors` field meaningful."* The floor is a CHECK constraint, not a workflow step, because a workflow step is skippable. *Enforced by `fi-admission-floor`.*

**DO-NOT-7 — Do not collapse the many-to-many crosswalk, and do not "clean" a PMA/Scheduling disagreement.**
No `LIMIT 1`, no primary-candidate selection, no single "best" mode. Doc 12 DO-NOT-2 and DO-NOT-8; [08 §2.8](../architecture/08-standards-alignment.md): the disagreement *"is a retained first-class signal, not an error to clean"*, and forcing the mapping is *"the most common way maintenance-derived training data goes bad."* FI is the arbitration record, which means it records the disagreement — it does not resolve it away. *Enforced by `fi-attr-retains-both`, `fi-attr-no-limit-one`.*

**DO-NOT-8 — Do not raise a strength band by any path other than recomputation from evidence.**
An adjudicator may lower. Nothing raises. A hypothesis is not stronger because a stakeholder needs it to be, and a scale that can be adjusted downstream of its inputs is not a scale. *Enforced by `fi-strength-no-upgrade` at both layers.*

**DO-NOT-9 — Do not rewrite a historical attribution, tag reference, or findings reference on a taxonomy bump.**
Resolve forward at read time and record the resolution with its `hops` (§6.4). [12 §6.2](12-reference-data-taxonomy.md): held references *"remain byte-identical across every future version bump."* A rewrite changes the meaning of every training set assembled under the old version, undetectably. *Enforced by `fi-tax-never-rewritten`.*

**DO-NOT-10 — Do not delete a negative finding, a refused run, or a superseded hypothesis.**
[04 §9](../architecture/04-subapplication-architectures.md): retained knowledge *"prevents rediscovery."* A refused run is knowledge about a data-capture gap. Deletion is available only through the declared purge protocol for a classification remediation ([03 §13](../architecture/03-integration-contracts.md), D15), never as cleanup. *Enforced by `fi-rediscovery-blocked`, `fi-negative-published`.*

**DO-NOT-11 — Do not assign a taxonomy code, publish a taxonomy version, or approve your own extension proposal.**
FI decides content; Reference Data owns the register; the proposing identity is never the approving identity, and dual control means two distinct identities. Inventing a plausible three-letter code is doc 12 DO-NOT-3, and it is a compliance misstatement rather than a shortcut. *Enforced by `fi-tax-no-code-in-payload`, `fi-tax-self-approval`.*

**DO-NOT-12 — Do not use `eic`, `eswbs`, `equipment_class`, `hull_or_tail`, `position_code`, or `nsn` as a join key.**
Join on `installed_item_id`, `system_id`, `asset_id`, `niin`, `lineage_id`. [08 §2.6](../architecture/08-standards-alignment.md) makes EIC *"a class or category code of variable specificity"* from primary text, and [03 §3.3](../architecture/03-integration-contracts.md) carries `eic?` on `SystemRef` and `InstalledItemRef` for federation and human reference **only**. Instance identity is IUID-backed `installed_item_id`. Conflating `position_id` with `installed_item_id` is the inherited-degradation defect (**C10**, **D9**) — and in this service it would attribute one item's failure history to its successor.

**DO-NOT-13 — Do not run discovery outside the declared staleness bound.**
§11.3. A lagging treatment projection produces a census that under-reports confounding risk, which makes the gate more permissive exactly when it should be less so.

**DO-NOT-14 — Do not claim ISO 14224 conformance for a finding whose subject mode is a `FATHOM-EXT-nnn` placeholder.**
Doc 12 §5.4 / OD-1. Cap C-TAX applies, the marker travels with every rendering, and the GEIA-STD-0007C export carries non-standard codes. §6.5.

---

## 13. Open decisions

Recorded rather than resolved with an invented value. Each is a genuine judgment; each blocks something specific.

| ID | Decision | Blocks | Current handling | Owner |
|---|---|---|---|---|
| **OD-1** | **How `policy_version` resolves to the consuming `causal_feature_set` version**, so the feedback-provenance check (§3.2) can be evaluated. Options: add the feature-set version to the treatment record; have PdM publish a policy manifest; or make FI a declared consumer of `model_binding.activated` (which requires a [03 §6](../architecture/03-integration-contracts.md) catalog amendment, not a local decision) | D21's loop cannot be closed empirically. The check reports `unknown` and every affected hypothesis must restrict to the policy-frozen stratum or refuse | Conservative default shipped: `unknown` is treated as contaminated. Pinned by `fi-confound-feedback-provenance` so a future resolution cannot loosen it silently | Architecture + PdM + Scheduling |
| **OD-2** | **`gate.fi_max_trimmed_fraction` and `gate.fi_max_balance_smd`** — the practical margins for propensity positivity and balance (§3.3 P4, P5) | Any propensity-handling method. The *form* of both tests is prescribed; the margin is not | **No defaults.** The service refuses to run a propensity-handling method until set, on [13 §16.4](13-synthetic-data-generator.md)'s pattern | Program, with engineering recommendation |
| **OD-3** | **The `triggering_driver` vocabulary is not enumerated in [03 §6](../architecture/03-integration-contracts.md).** FI's driver-class mapping is currently derived from [13 §8.4](13-synthetic-data-generator.md)'s five generator values | A mapping built on a generator's vocabulary rather than a contract's. Every unmapped value degrades to `unknown`, which is safe but progressively useless | Fail-safe mapping with `driver_mapping_version` recorded on every projection row and census | Architecture + Scheduling |
| **OD-4** | `strength.observation_multipliers` `[2, 4, 8]` and `strength.max_hull_dominance` — the A1 and A2 thresholds (§4.3) | Nothing hard; shipped values are versioned in `strength_rule_version` and auditable | Shipped as stated, flagged for SME review. The ratio *form* is the defensible part | Failure Intelligence + reliability SME |
| **OD-5** | ~~**The authority class for publishing a causal finding, arbitrating an attribution, and admitting a feature.** [03 §7.2.1](../architecture/03-integration-contracts.md)'s minimum-authority table has no row for any of them~~ **[RESOLVED — this row was stale: §5.2 declared it resolved, this row still carried it as interim. `reliability_engineer` is settled as a realm sub-role composited into `design_authority`, surfaced via `fathom.identity.qualifications[]` (§5.2), not a new `AuthorityClass` value]** | Closed — no correction needed | **Resolved in §5.2.** `design_authority`, dual control at S3+ and for all vocabulary change | Resolved |
| **OD-6** | The `review_due` interval for `monitored` (S2) features, and the ablation reporting cadence PdM owes (§5.4) | Nothing structural; the field is `NOT NULL` | Set per admission by the adjudicator until a standing interval exists | Program + PdM |
| **OD-7** | **Whether a distinct `causal_finding.retracted` event is added to [03 §6](../architecture/03-integration-contracts.md)'s catalog** (§5.5) | Consumers must branch on `finding_class` inside a publication event to detect a withdrawal, which is easy to miss | Retraction expressed through `finding_class` on `causal_finding.published`. No undeclared producer event is added | Architecture |
| **OD-8** | Add `fathom.reference-data.*` topics and their consumers to [03 §6](../architecture/03-integration-contracts.md)'s catalog (doc 12's OD-7) | FI's consumer-driven conformance tests for the taxonomy and proposal topics cannot be written | Consumed with locally documented expectations; tests deferred and named | Architecture |
| **OD-9** | **Doc 12's OD-1** — purchase ISO 14224:2016 and transcribe Annex B, or bridge with `FATHOM-EXT-nnn` placeholders (§6.5) | M4's discriminating power, the arbitration record's testability, and any ISO 14224 conformance claim on a finding. **A gate on this sub-application's demonstration credibility**, not only doc 12's | Cap C-TAX at S2, placeholder markers in every rendering, no conformance claim | Program management + Failure Intelligence |
| **OD-10** | The staleness bound per consumed stream (§11.3), informed by the capacity model ([05 §4.6](../architecture/05-architecture-review-findings.md)) | Discovery cannot declare a defensible refusal threshold | Field required, value set per environment in the chart and recorded in the README | Program + engineering |
| **OD-11** | Minimum population thresholds below which discovery is not attempted per method and equipment family ([04 §9](../architecture/04-subapplication-architectures.md)'s Phase 3 question) | `discovery_eligible` on `failure_mode_ref` and each method's `min_events_expression` are presently expressed as formulas without family-specific floors | Expressed as `events_per_parameter`-style formulas, evaluated per run, with `min_population_basis` recorded and reviewable | Failure Intelligence + reliability SME |
| **OD-12** | **Whether the synthetic demonstration data can support credible causal discovery at all**, and if not, how the capability is demonstrated honestly ([04 §9](../architecture/04-subapplication-architectures.md)'s Phase 3 question) | The framing of the demonstration, not its construction. [13 §10.1](13-synthetic-data-generator.md)'s holdout thinness means per-family causal claims are unlikely to clear S3 | The mechanism — gate, census, strength, adjudication, admission — is demonstrable regardless and is what should be shown. Any per-family causal claim is reported at its computed band with its limiting axis, and aggregate-level claims are labelled as such | Program |

---

## 14. Definition of Done

The shared Definition of Done in [09 §8](09-monorepo-and-conventions.md) applies **in full and unmodified** — contract and specification, events, outbox/inbox/read models, data and storage, conformance and tests, deployment and boundary, documentation and governance. Nothing is removed.

Service-specific additions, all of which must hold:

1. **The gate is a runtime control, proven.** `fi-confound-resist` green on all four cases — import-time refusal, precondition refusal with a persisted census and no hypothesis row, the two-sided correction assertion against the generator's truth partition, and the restriction path including its refusal at family granularity. `fi-confound-adversarial` green: a method that bypasses `population.load_population` fails the import-linter contract.
2. **No hypothesis without a census.** Invariant I3 asserted at the database; `fi-confound-unknown-driver` and `fi-confound-feedback-provenance` green; `GET /hypotheses/{id}/treatment-census` serves a complete per-arm census for every published finding in the reference dataset.
3. **Every method declares.** `fi-method-declares` green over the live registry. Every method in §3 has a non-default `treatment_handling`, a non-empty `known_failure_modes`, a `min_events_expression`, and — where it is one — a `placeholder_pending_sme` flag that surfaces in published provenance.
4. **Strength is computed, versioned, and cannot be inflated.** `fi-strength-monotone`, `fi-strength-no-upgrade`, `fi-strength-caps`, `fi-strength-rule-version` green. `strength_rule_version` pinned on every feature set.
5. **The framing survives contact with prose.** `fi-language-gate` green over every hypothesis in the reference dataset. No causal verb below S4; no empty residual clause with a non-empty residual list.
6. **Admission cannot leak a weak hypothesis.** `fi-admission-floor`, `fi-admission-definition-time`, `fi-admission-separation`, `fi-featureset-freeze`, `fi-featureset-retire-on-fall` green. The floor tested at the API and at the database independently.
7. **The taxonomy boundary holds.** `fi-tax-no-content` green and contributing to doc 12's `tax-single-source`; `fi-tax-self-approval`, `fi-tax-no-code-in-payload`, `fi-tax-split-review`, `fi-tax-never-rewritten` green. FI owns no taxonomy table.
8. **The arbitration record retains disagreement.** `fi-attr-retains-both`, `fi-attr-version-skew`, `fi-attr-no-limit-one` green, and the consumer half of Reference Data's `tax-xw-reconcile-retains` contributed and green in *its* suite.
9. **Negative findings are retained and findable.** `fi-rediscovery-blocked` and `fi-negative-published` green. `POST /hypotheses/prior-examination-check` served, agent-eligible, and exercised by a manifest test.
10. **Predictions are not evidence.** `fi-prediction-not-evidence` green at all three layers; the NetworkPolicy egress set contains no `pdm` peer.
11. **Events match the catalog exactly.** `fi-event-catalog-parity` green and `python tools/check_event_catalog.py` exits 0. `fi-event-census-carried` green — the two catalog-mandated fields (`treatment-assignment handling`, `definition-time`) present on every relevant event. `producer_node = 'enterprise'` on every event.
12. **Staleness refuses rather than degrades.** The bound declared per consumed stream, exposed on `/readyz`, and `fathom_staleness_refusals_total` incrementing on refusal. `read_model_lag_at_start` recorded on every `discovery_run`.
13. **Every open decision in §13 is either resolved and this document updated, or explicitly accepted as a demonstration-scope risk with a named owner.** **OD-1** and **OD-9** in particular cannot be closed by silence: OD-1 is the empirical closure of D21's loop, and OD-9 gates whether attribution in the demonstration resembles attribution at all.
