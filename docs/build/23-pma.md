# Build Framework 23 — Post-Mission Analysis (`pma`)

| | |
|---|---|
| **Status** | Draft rev 1 |
| **Slug** | `pma` (document 03 §3.1). Directory `services/pma/`, package `fathom_pma`, base path `/api/v1/pma/` |
| **Purpose** | Build specification for the sub-application that converts completed missions into human-confirmed anomaly labels through a bounded review workflow — the supervised signal on which the entire causal-analysis capability depends |
| **Resolves / implements** | **D17** (adjudication capacity unmodeled; the precision-without-recall metric trap), **D18** (the PMA Pre-Screener cannot run afloat), **C36** (evidence-package storage claimed by two owners), **C8/D31** (three claimed taxonomy owners), and the decisions recorded in 06 §4 and 06 §6 |
| **Binding contracts** | [03 §3.3](../architecture/03-integration-contracts.md), [03 §4](../architecture/03-integration-contracts.md), [03 §5](../architecture/03-integration-contracts.md), [03 §6](../architecture/03-integration-contracts.md) PMA rows, [03 §7.2 and §7.2.1](../architecture/03-integration-contracts.md), [03 §9](../architecture/03-integration-contracts.md), [03 §11](../architecture/03-integration-contracts.md), [03 §14](../architecture/03-integration-contracts.md), [03 §15](../architecture/03-integration-contracts.md), [04 §8](../architecture/04-subapplication-architectures.md) |
| **Conventions** | [09 — Monorepo & Conventions](09-monorepo-and-conventions.md) (binding on layout, scaffold, API mechanics, and the Definition of Done), [10 — Shared Packages](10-shared-packages.md), [11 — Outbox & Sync Library](11-outbox-sync-library.md), [12 — Reference Data & Taxonomy](12-reference-data-taxonomy.md), [13 — Synthetic Data Generator](13-synthetic-data-generator.md) |
| **Quantities** | Every figure is cited from [06 §6](../architecture/06-demo-decisions-and-assumptions.md) or [06 §7](../architecture/06-demo-decisions-and-assumptions.md). No quantity in this document is invented (09 §9.5 item 31) |
| **Classification** | Internal. The service operates at U for the synthetic demonstration (03 §12) |

---

## 0. Read this first

Two facts govern every decision in this document, and an implementer who internalises nothing else should internalise these.

**First: this sub-application is the single point of failure for the causal capability.** Document 01 §8.2 states that the labeling burden "represents the most probable single point of failure in the concept." Failure Intelligence, tier-3 modeling, and every causal claim the program intends to make rest on the tag stream this service produces.

**Second: it can fail invisibly, and its dashboard will look excellent while it does.** This is D17, and it is worth quoting in full because it is the reason this document is shaped the way it is:

> *"The metric trap: precision is measured against human adjudication, rejections train detectors to be quieter, volume drops, precision rises and review duration falls — **both governing metrics improve monotonically** — while recall collapses and nothing measures recall, because there is no independent ground truth."*

Everything in §5 exists to make that failure mode observable. The seeded-canary mechanism is not instrumentation bolted onto a working pipeline; it is the only thing that distinguishes a working pipeline from a dead one. An implementation that ships §3 and defers §5 has shipped the failure mode, not the capability.

A third fact, from D18, closes the other half: **candidate generation is edge-resident**, because a submarine returning from a six-week patrol whose reviews have empty candidate sets contributes zero confirmed tags from precisely the domain where failures are most informative.

---

## 1. Purpose and scope

### 1.1 Purpose

Per document 04 §8: **convert completed missions into human-confirmed anomaly labels through a bounded review workflow, producing the supervised signal on which causal analysis depends.**

The workflow is **bounded review, not open authoring** (04 §8). A reviewer is presented a finite, ranked candidate set to confirm or reject. A reviewer is never presented an interface for discovering anomalies in raw telemetry, because — 01 §8.2 — "voluntary annotation of telemetry by crews following an extended underway period is not a reliable assumption."

### 1.2 Ownership boundary

**Owns** (04 §8): the review workflow and its state; candidate anomaly queues; **taxonomy assignments** against the Reference Data vocabulary; confirmed and rejected tags with reviewer provenance; evidence packages; reviewer qualification records and the label-weighting function; the canary plant registry and the recall estimator; the admission-control gate; and `Proposal` aggregates whose `target_sub_app` is `pma`.

**Does not own:**

| Not owned | Owner | Consequence for this build |
|---|---|---|
| The taxonomy vocabulary itself | `reference-data` (03 §14, 12 §1) | PMA holds a read-through cache of one projection and no independent definition (12 DO-NOT-1) |
| Telemetry samples, health indicators, mission records, **automated detections** | `telemetry` (04 §3) | `DetectedAnomaly` "seeds the Post-Mission Analysis candidate queue but is never itself a label" (04 §3) |
| The detector ensemble and the edge pre-screener runtime | `telemetry` (11 §1.2) | PMA consumes `anomaly.detected`; it cannot start, stop, or tune a detector (§5.6) |
| Causal interpretation and attribution | `failure-intel` (04 §9) | A tag is an assignment, never an attribution (03 §14) |
| Predictions | `pdm` | PMA never publishes or corrects a prediction |
| Maintenance action records | `maintenance` (03 §11, edge-authoritative there) | Consumed as **review context only** (§2.7) |
| Vocabulary extension approval | `failure-intel` (12 §7.1) | PMA proposes novel signatures; it never approves one |

### 1.3 What this document does not cover

| Out of scope | Governed by |
|---|---|
| Repository layout, scaffold, Dockerfile, middleware, problem details, idempotency, ETag mechanics | 09 §3–§5 |
| Outbox, inbox, clock discipline, conflict-policy machinery, provisional identity, divergence-budget tracker | 11 |
| Canonical schema shapes (`Proposal`, `EventEnvelope`, `ClassificationLabel`) | 10 §4 |
| Taxonomy structure, versioning, crosswalk mechanics, publication | 12 |
| Canary *designation* in the corpus, label-corruption rates, the edge scenario fixtures | 13 §13, §9.10, §15 |
| The reviewer UI's visual design and flows | Deferred to the look-and-feel wave (09 §1.2). §3.6 states only the API properties the ~45 s budget requires |
| The PMA Pre-Screener agent's prompt, manifest, and evaluation set | `agents/pma-prescreener/`, per 01 §8 and 03 §8 |

### 1.4 Substitution posture

Per 04 §8: **core program capability, not a substitution candidate.** "The tag stream is the program's most distinctive data asset." Consequence for this build: the `x-substitution: required` subset is exactly the eight operations document 04 §8 lists (§3.7), and everything added here for workflow, capacity, and quality measurement is `internal`. Adding operations to the required subset would enlarge a substitution burden nobody intends to discharge.

---

## 2. Data model

PostgreSQL, one logical database `fathom-pma-pg`, schema `pma` (09 §2.3, obligation 13). Object storage bucket `fathom-pma-evidence` for evidence packages — **PMA's own bucket, never Telemetry's** (§2.6). Migrations per 09 §4.2.

Four invariants govern the whole schema and are stated before the tables because every table obeys them:

- **I1 — Every tag and every rejection carries `taxonomy_version`.** 03 §14: *"A training set assembled across an unversioned revision is silently corrupt and undetectably so."* There is no unversioned label anywhere in this schema.
- **I2 — Tags and rejections are append-only and immutable except for supersession marking**, enforced by trigger (§2.4), not by convention. 03 §11: *"Anomaly tags | Append-only; never overwritten or deleted; supersession recorded | Human judgments are evidence."*
- **I3 — Canary ground truth is a withheld column set.** No canary column appears in any reviewer-reachable projection, and the reviewer-facing wire models contain no field into which one could be serialised (§2.3, §5.2). This is the same discipline 13 §8.6 applies to the generator's truth partition, for the same reason: a single accidental join destroys the metric while leaving no visible symptom.
- **I4 — Every aggregate declares a conflict policy.** 11 §7.2's registry enumerates PMA's aggregates at startup and fails if one is neither declared nor explicitly defaulted (C20). PMA's declarations are in §7.3.

### 2.1 `MissionReview`

```sql
CREATE TYPE pma.review_kind  AS ENUM ('primary', 're_review');
CREATE TYPE pma.review_state AS ENUM (
    'pending_evidence',            -- created; evidence packages not yet materialised
    'deferred_admission_control',  -- admission control engaged; NOT opened (§5.6)
    'open',                        -- opened and claimable; mission_review.opened published
    'completed',
    'abandoned'                    -- claim lapsed and reassignment declined; retained, never deleted
);

CREATE TABLE pma.mission_review (
    review_id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id            uuid NOT NULL,
    asset_id              uuid NOT NULL,          -- the partition key for this aggregate's topic (§8.2)
    review_kind           pma.review_kind NOT NULL DEFAULT 'primary',
    blinded_from_review_id uuid REFERENCES pma.mission_review(review_id),   -- §6.4
    state                 pma.review_state NOT NULL DEFAULT 'pending_evidence',
    candidate_cap         int  NOT NULL,          -- 12 for the demonstration (06 §6)
    assigned_reviewer_id  text,
    claimed_by            text,
    claimed_until         timestamptz,            -- lease; evaluated on a MONOTONIC clock (03 §5.4)
    taxonomy_version_pin  text NOT NULL,          -- §4.3: pinned at creation, never re-pinned
    baseline_id           uuid NOT NULL,
    baseline_epoch        bigint NOT NULL,
    ranker_version        text NOT NULL,          -- §3.3
    injector_version      text NOT NULL,          -- §5.3
    opened_at             timestamptz,
    completed_at          timestamptz,
    duration_seconds      numeric(10,3),          -- MONOTONIC-measured (09 §4.8), not a timestamp difference
    producer_node         text NOT NULL,          -- 'enterprise' | 'edge:<asset_id>'  (03 §5.4)
    version               bigint NOT NULL DEFAULT 1,   -- ETag source (09 §5.4)
    classification        jsonb NOT NULL,
    CONSTRAINT re_review_has_origin
        CHECK ((review_kind = 're_review') = (blinded_from_review_id IS NOT NULL)),
    CONSTRAINT opened_has_timestamp
        CHECK (state <> 'open' OR opened_at IS NOT NULL),
    CONSTRAINT completed_has_duration
        CHECK (state <> 'completed' OR (completed_at IS NOT NULL AND duration_seconds IS NOT NULL))
);
```

Three notes:

**`duration_seconds` is monotonic-measured.** Review duration is a governing product metric (04 §8) and one half of the D17 metric trap — the half that *improves* as the pipeline dies. Computing it as `completed_at - opened_at` would let a mandated STIG backward clock step (V-260520, 03 §5.4) produce a negative or absurd duration, and at the edge that step fires at reconnect. The service records a monotonic start reading and derives the duration from monotonic deltas; the wall-clock timestamps are for display and audit only.

**`taxonomy_version_pin` is set at creation and never changed.** If Reference Data publishes a new version mid-review, the reviewer's signature choices do not change underneath them (§4.3).

**`state = 'deferred_admission_control'` is a first-class state, not an error.** A mission whose review cannot be opened because the backlog exceeds the admission threshold is recorded, retained, and openable later. Nothing is dropped (§5.6 rule 3).

### 2.2 `AnomalyCandidate`

```sql
CREATE TYPE pma.candidate_origin  AS ENUM ('detector', 'agent', 'canary');   -- WITHHELD (I3)
CREATE TYPE pma.detection_origin  AS ENUM ('enterprise', 'edge');            -- from anomaly.detected (03 §6)
CREATE TYPE pma.candidate_state   AS ENUM (
    'queued_unadmitted',           -- persisted from an event; not in any review
    'admitted',                    -- in a review's bounded set
    'adjudicated',
    'held_on_antecedent',          -- baseline_epoch ahead of the local read model (03 §5.4)
    'held_no_evidence',            -- evidence could not be materialised (§2.6)
    'grouped_duplicate'            -- representative of its group is elsewhere (§3.4)
);

CREATE TABLE pma.anomaly_candidate (
    candidate_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id             uuid REFERENCES pma.mission_review(review_id),
    mission_id            uuid NOT NULL,
    asset_id              uuid NOT NULL,
    installed_item_id     uuid NOT NULL,        -- the PHYSICAL item (03 §3.3)
    position_id           uuid NOT NULL,        -- the LOCATION. Never interchangeable [C10, D9]
    system_id             uuid,
    window_start          timestamptz NOT NULL,
    window_end            timestamptz NOT NULL,
    channels_implicated   text[] NOT NULL,
    detector_version      text,                 -- as reported by telemetry; never synthesised (§5.3)
    detector_score        numeric,              -- as reported; never synthesised
    detection_origin      pma.detection_origin NOT NULL,
    source_event_id       uuid,                 -- the anomaly.detected event_id
    source_proposal_id    uuid,                 -- set where origin = 'agent'
    candidate_group_id    uuid NOT NULL,        -- near-duplicates linked, never merged away (11 §7.3)
    state                 pma.candidate_state NOT NULL DEFAULT 'queued_unadmitted',
    rank_score            numeric,              -- §3.3
    rank_stratum          smallint,             -- 0..2 tercile; the injection-matching key (§5.3)
    rank_components       jsonb,                -- the full score vector, for audit (obligation 9)
    presentation_ordinal  smallint,             -- 1..cap within its review
    baseline_id           uuid NOT NULL,
    baseline_epoch        bigint NOT NULL,
    evidence_package_id   uuid,
    producer_node         text NOT NULL,
    version               bigint NOT NULL DEFAULT 1,
    classification        jsonb NOT NULL,

    -- ── WITHHELD (I3). Never selected by any reviewer-facing repository method. ──
    origin                pma.candidate_origin NOT NULL,

    CONSTRAINT window_ordered CHECK (window_end > window_start),
    CONSTRAINT admitted_has_review
        CHECK (state NOT IN ('admitted','adjudicated') OR review_id IS NOT NULL),
    CONSTRAINT agent_origin_has_proposal
        CHECK ((origin = 'agent') = (source_proposal_id IS NOT NULL))
);

CREATE INDEX ac_review_ordinal ON pma.anomaly_candidate (review_id, presentation_ordinal);
CREATE INDEX ac_backlog        ON pma.anomaly_candidate (state)
    WHERE state IN ('queued_unadmitted','admitted');     -- the admission-control counter (§5.6)
CREATE INDEX ac_group          ON pma.anomaly_candidate (candidate_group_id);
```

**`origin` and `detection_origin` are orthogonal, and conflating them is the defect this pair exists to prevent.**

- `origin` (`detector | agent | canary`) records **which PMA code path created the row**. It is withheld.
- `detection_origin` (`enterprise | edge`) is the field `anomaly.detected` carries (03 §6) and records **where the detection was computed**. It is not withheld; it is operationally useful and carries no information about canary status.

**`origin = 'canary'` does not mean the candidate's content is synthetic.** Per 13 §13.1, *"a canary must be produced by the same code path, from the same parameter distributions, as an ordinary fault"* — the generator's `truth/canaries.py` "contains no signal-generation code at all: it selects which already-generated faults are designated canaries." A canary candidate row therefore carries a **real** window, a **real** `detector_version`, a **real** `detector_score`, and a **real** `source_event_id`, all copied from the underlying detection. `origin` records who assembled the row, not what is in it. §5.3 specifies the two provenances by which that happens, and neither fabricates a detection.

**Why `origin` is withheld rather than merely unused.** If `origin` appeared in the reviewer-facing projection it would be a one-field oracle: a reviewer who could see it would score canaries perfectly and the recall estimate would become a measurement of nothing. 06 §6 marks canary detectability MEDIUM confidence with the consequence stated plainly — *"if reviewers learn to spot canaries, they stop measuring recall."* §5.2 gives the enforcement.

### 2.3 `CanaryPlant` — the withheld ground-truth link

```sql
CREATE TYPE pma.canary_provenance AS ENUM ('designated', 'admitted');   -- §5.3
CREATE TYPE pma.canary_outcome    AS ENUM ('pending', 'confirmed', 'rejected', 'unadjudicated');

CREATE TABLE pma.canary_plant (
    plant_id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- ── the planted ground truth. WITHHELD (I3). ──
    truth_ref                text NOT NULL,     -- generator ground-truth key (13 §8.7 canary_injection_id)
    truth_mode_lineage_id    uuid NOT NULL,      -- the true failure mode's lineage_id (12 §2.3)
    truth_taxonomy_version   text NOT NULL,
    truth_window_start       timestamptz NOT NULL,
    truth_window_end         timestamptz NOT NULL,

    -- ── the plant's binding to a real detection and a real review ──
    installed_item_id        uuid NOT NULL,
    mission_id               uuid NOT NULL,
    asset_id                 uuid NOT NULL,
    source_event_id          uuid NOT NULL,      -- the REAL anomaly.detected this plant rides on
    candidate_id             uuid REFERENCES pma.anomaly_candidate(candidate_id),
    review_id                uuid REFERENCES pma.mission_review(review_id),
    provenance               pma.canary_provenance,
    injected_at              timestamptz,
    injector_version         text,

    -- ── outcome, written only at adjudication or review completion ──
    outcome                  pma.canary_outcome NOT NULL DEFAULT 'pending',
    outcome_recorded_at      timestamptz,
    resulting_tag_id         uuid,
    signature_agreed         boolean,            -- §5.5: classification quality, NOT recall

    staged_for_node          text NOT NULL,      -- 'enterprise' | 'edge:<asset_id>'  (§7.4)
    consumed                 boolean NOT NULL DEFAULT false,
    classification           jsonb NOT NULL,

    CONSTRAINT injected_is_complete
        CHECK ((candidate_id IS NULL) = (injected_at IS NULL)),
    CONSTRAINT outcome_has_time
        CHECK (outcome = 'pending' OR outcome_recorded_at IS NOT NULL)
);

CREATE UNIQUE INDEX cp_one_plant_per_candidate ON pma.canary_plant (candidate_id)
    WHERE candidate_id IS NOT NULL;
CREATE INDEX cp_pool ON pma.canary_plant (staged_for_node, mission_id) WHERE NOT consumed;
```

Three properties are load-bearing:

**The plant table is a separate table, not columns on `anomaly_candidate`.** A reviewer-facing `SELECT *` on the candidate table then cannot leak plant data even by accident, and the repository methods that serve reviewers do not reference `pma.canary_plant` at all — a fact asserted by static test (§9.4).

**`resulting_tag_id` and `outcome` are written only at adjudication.** Nothing about a plant is written while the reviewer is looking at it, because a write is an observable event: metrics, audit records, and outbox rows all move. §5.4 makes this explicit for metrics.

**A plant is bound to a real detection by `source_event_id`, and the binding is mandatory.** There is no path by which a plant becomes a candidate without a real underlying detection. This is the schema-level form of 13 §13.1's rule.

### 2.4 `AnomalyTag` — append-only, taxonomy-assigned

```sql
CREATE TABLE pma.anomaly_tag (
    tag_id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id              uuid NOT NULL REFERENCES pma.anomaly_candidate(candidate_id),
    review_id                 uuid NOT NULL REFERENCES pma.mission_review(review_id),
    mission_id                uuid NOT NULL,
    asset_id                  uuid NOT NULL,
    installed_item_id         uuid NOT NULL,
    position_id               uuid NOT NULL,
    window_start              timestamptz NOT NULL,
    window_end                timestamptz NOT NULL,

    -- ── the taxonomy ASSIGNMENT (03 §14: PMA owns assignments, not the vocabulary) ──
    signature_key             text NOT NULL,        -- from GET /taxonomy/projections/pma (§4.1)
    taxonomy_version          text NOT NULL,        -- I1. MANDATORY, no default
    is_novel_escape           boolean NOT NULL,     -- the unclassified/novel escape (12 §2.8)
    novel_description         text,                 -- reviewer free text; UNTRUSTED CONTENT (03 §9)
    resolved_lineage_ids      uuid[] NOT NULL DEFAULT '{}',  -- crosswalk result, CACHED and recomputable
    crosswalk_resolved_at     timestamptz,

    -- ── reviewer provenance and label weight (§6) ──
    reviewer_id               text NOT NULL,
    reviewer_persona          text NOT NULL,        -- 'ships_force' | 'shore_analyst'  (06 §6)
    qualification_snapshot_id uuid NOT NULL REFERENCES pma.reviewer_qualification_snapshot(snapshot_id),
    label_weight              numeric(4,3) NOT NULL,
    weight_components         jsonb NOT NULL,       -- stored so a re-weighting is re-derivable
    weighting_version         text NOT NULL,
    dwell_seconds             numeric(10,3) NOT NULL,   -- MONOTONIC-measured
    low_dwell                 boolean NOT NULL,     -- §6.3: excluded from the primary training set

    -- ── evidence and configuration binding ──
    evidence_package_id       uuid NOT NULL REFERENCES pma.evidence_package(package_id),
    evidence_content_hash     text NOT NULL,        -- pinned: the basis cannot change after the fact
    baseline_id               uuid NOT NULL,
    baseline_epoch            bigint NOT NULL,

    -- ── agent provenance, where the tag arose from an adjudicated proposal ──
    source_proposal_id        uuid,
    proposing_agent_id        text,
    proposing_agent_version   text,
    proposing_llm_version     text,
    proposing_trace_ref       text,

    -- ── supersession (I2) ──
    supersedes_tag_id         uuid REFERENCES pma.anomaly_tag(tag_id),
    superseded_by_tag_id      uuid REFERENCES pma.anomaly_tag(tag_id),
    superseded_at             timestamptz,
    supersession_rationale    text,

    hindsight                 boolean NOT NULL DEFAULT true,   -- 11 §5, [D22]
    occurred_at               timestamptz NOT NULL,   -- when the anomaly occurred, at sea
    recorded_at               timestamptz NOT NULL,   -- when the reviewer authored the tag
    producer_node             text NOT NULL,
    classification            jsonb NOT NULL,

    CONSTRAINT novel_escape_has_description
        CHECK (NOT is_novel_escape OR novel_description IS NOT NULL),
    CONSTRAINT supersession_is_paired
        CHECK ((superseded_by_tag_id IS NULL) = (superseded_at IS NULL)),
    CONSTRAINT no_self_supersession CHECK (superseded_by_tag_id <> tag_id),
    CONSTRAINT weight_is_bounded CHECK (label_weight > 0 AND label_weight <= 1)
);
```

**`hindsight = true` is not decoration.** 11 §5 requires `emit()` to stamp a hindsight marker on aggregates declared hindsight-authored, "confirmed anomaly tags, in particular," because 03 §5.4 forbids feature computation from using `occurred_at` for any value authored with hindsight `[D22]`. A tag's `occurred_at` is mission time; its `recorded_at` is review time; on a returning submarine the two are six weeks apart. A feature pipeline that keys on `occurred_at` has leaked the future into the past.

**`label_weight > 0` is a constraint, not a convention.** A zero-weight label is a deletion performed by arithmetic. Exclusion is expressed by flags with reasons (`low_dwell`, and the export filters of §6.5), never by driving a weight to zero, because a weight of zero is indistinguishable from a weighting bug.

**Immutability is a trigger, taking the form document 12 §6.3 established for published taxonomy rows** — the same mechanism, because the failure mode is the same well-intentioned `UPDATE`:

```sql
CREATE OR REPLACE FUNCTION pma.forbid_tag_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'anomaly tags are never deleted (tag %). 03 §11: human judgments are evidence',
            OLD.tag_id;
    END IF;

    -- The ONLY permitted mutation: supersession marking, write-once.
    IF OLD.superseded_by_tag_id IS NOT NULL THEN
        RAISE EXCEPTION 'tag % is already superseded; supersession marking is write-once', OLD.tag_id;
    END IF;
    IF ROW(NEW.*) IS DISTINCT FROM ROW(OLD.*)
       AND (NEW.tag_id, NEW.candidate_id, NEW.signature_key, NEW.taxonomy_version,
            NEW.is_novel_escape, NEW.installed_item_id, NEW.position_id,
            NEW.window_start, NEW.window_end, NEW.reviewer_id, NEW.label_weight,
            NEW.weighting_version, NEW.evidence_package_id, NEW.evidence_content_hash,
            NEW.baseline_epoch, NEW.occurred_at, NEW.recorded_at)
        IS DISTINCT FROM
           (OLD.tag_id, OLD.candidate_id, OLD.signature_key, OLD.taxonomy_version,
            OLD.is_novel_escape, OLD.installed_item_id, OLD.position_id,
            OLD.window_start, OLD.window_end, OLD.reviewer_id, OLD.label_weight,
            OLD.weighting_version, OLD.evidence_package_id, OLD.evidence_content_hash,
            OLD.baseline_epoch, OLD.occurred_at, OLD.recorded_at)
    THEN
        RAISE EXCEPTION
          'anomaly tag % is immutable; a changed judgment is a NEW tag with supersedes_tag_id set '
          '(03 §11, 11 §7.3 APPEND_ONLY_IMMUTABLE)', OLD.tag_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER anomaly_tag_immutable
    BEFORE UPDATE OR DELETE ON pma.anomaly_tag
    FOR EACH ROW EXECUTE FUNCTION pma.forbid_tag_mutation();
```

An equivalent trigger applies to `pma.tag_rejection` and to `pma.evidence_package`. `resolved_lineage_ids` and `crosswalk_resolved_at` are deliberately *outside* the immutable column set: they are a cache of a Reference Data read (12 §6.4 forward resolution) and are recomputable at any time from `(signature_key, taxonomy_version)`, which is the immutable pair. Caching a resolution is not authoring a label.

**A tag is never invalidated by a configuration change.** This is a genuine and load-bearing asymmetry with PdM. `configuration.baseline_changed` invalidates predictions (03 §6: "a correctness signal rather than an informational one"), but a human observation of a telemetry window remains true after the equipment is replaced. PMA records `baseline_epoch` on the tag so a consumer knows the configuration it was assigned under, applies epoch fencing to *candidate admission* (§3.5), and never retracts a tag. An implementation that invalidates tags on baseline change has destroyed evidence.

### 2.5 `TagRejection` — retained as a negative label, with a reason class that matters

```sql
CREATE TYPE pma.rejection_reason_class AS ENUM (
    'normal_for_this_equipment',   -- a genuine negative: normal in this condition
    'normal_for_this_condition',   -- a genuine negative: explained by operating condition
    'already_known_and_repaired',  -- a POSITIVE about the equipment, a negative about novelty
    'sensor_artifact',             -- evidence about the SENSOR, not the equipment
    'wrong_installed_item',        -- attribution error; not evidence of health  [C10, D9]
    'duplicate_of_candidate',      -- bookkeeping; carries no label information
    'insufficient_evidence',       -- carries NO information about equipment state
    'out_of_scope_window',
    'other'
);

CREATE TABLE pma.tag_rejection (
    rejection_id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id           uuid NOT NULL REFERENCES pma.anomaly_candidate(candidate_id),
    review_id              uuid NOT NULL REFERENCES pma.mission_review(review_id),
    installed_item_id      uuid NOT NULL,
    position_id            uuid NOT NULL,
    mission_id             uuid NOT NULL,
    asset_id               uuid NOT NULL,
    window_start           timestamptz NOT NULL,
    window_end             timestamptz NOT NULL,
    reason_class           pma.rejection_reason_class NOT NULL,
    reason_text            text,
    is_negative_label      boolean NOT NULL,       -- DERIVED from reason_class; see below
    duplicate_of_candidate_id uuid,
    reviewer_id            text NOT NULL,
    qualification_snapshot_id uuid NOT NULL,
    label_weight           numeric(4,3) NOT NULL,
    weighting_version      text NOT NULL,
    dwell_seconds          numeric(10,3) NOT NULL,
    low_dwell              boolean NOT NULL,
    evidence_package_id    uuid NOT NULL,
    taxonomy_version       text NOT NULL,          -- I1: the vocabulary offered, for later analysis
    baseline_epoch         bigint NOT NULL,
    occurred_at            timestamptz NOT NULL,
    recorded_at            timestamptz NOT NULL,
    producer_node          text NOT NULL,
    classification         jsonb NOT NULL,
    CONSTRAINT duplicate_names_its_original
        CHECK ((reason_class = 'duplicate_of_candidate') = (duplicate_of_candidate_id IS NOT NULL))
);
```

**`is_negative_label` is the most consequential column in this table, and it exists for the same reason `deferral_reason_class` exists in Scheduling.** Finding D34: deferrals were characterised as evidence the prediction overstated urgency, when "a deferral is a capacity or operational-tempo decision at least as often as a disagreement with the risk estimate; feeding it back as the latter biases models toward under-prediction."

Rejections carry precisely the same defect, and it is the mechanism of the D17 trap. `insufficient_evidence` means the reviewer could not tell. `sensor_artifact` is evidence about instrumentation. `wrong_installed_item` is an attribution error. **None of the three is evidence that the equipment was healthy**, and training a detector on all rejections indiscriminately teaches it to be quieter about exactly the cases humans found hard — which raises precision, shortens reviews, and collapses recall. The mapping is declared once, in code, and is versioned:

```python
# services/pma/src/fathom_pma/services/labels.py
NEGATIVE_LABEL_CLASSES: frozenset[RejectionReasonClass] = frozenset({
    RejectionReasonClass.NORMAL_FOR_THIS_EQUIPMENT,
    RejectionReasonClass.NORMAL_FOR_THIS_CONDITION,
})
"""The ONLY rejection classes that constitute evidence the equipment was healthy.

Everything else is bookkeeping, instrumentation evidence, an attribution error, or an
admission that the reviewer could not tell.  Widening this set requires an ADR citing
D34's reasoning, because the failure it produces — detectors trained toward silence —
is the mechanism of the D17 metric trap and is invisible in precision.
"""
```

Consequence enforced downstream: the label export (§6.5) partitions on `is_negative_label`, and the detector-training extract may not include a rejection with `is_negative_label = false`.

### 2.6 `EvidencePackage` — immutable, and materialised through Telemetry's API only

Document 04 §8 states the resolution of **C36** ("Evidence-package storage is claimed by both Telemetry and PMA") without ambiguity: the evidence package is *"the immutable telemetry window and context supporting a candidate. **Materialised into PMA's own object store at review open, from Telemetry's replay source via its API.**"*

```sql
CREATE TYPE pma.evidence_state AS ENUM ('materialising', 'materialised', 'failed', 'superseded');

CREATE TABLE pma.evidence_package (
    package_id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id          uuid NOT NULL REFERENCES pma.anomaly_candidate(candidate_id),
    review_id             uuid NOT NULL REFERENCES pma.mission_review(review_id),
    state                 pma.evidence_state NOT NULL DEFAULT 'materialising',

    -- what was fetched, from whom, with exactly which parameters (obligation 9)
    source_calls          jsonb NOT NULL,   -- [{operation, params, as_of, as_known_at, http_status,
                                            --   response_etag, byte_count, fetched_at}]
    telemetry_completeness jsonb NOT NULL,  -- Telemetry's completeness record: distinguishes
                                            -- "no fault observed" from "not observed" (04 §3)
    object_manifest       jsonb NOT NULL,   -- [{key, bytes, sha256, media_type, role}]
    content_hash          text NOT NULL,    -- Merkle root over object_manifest, sorted by key
    bucket                text NOT NULL,    -- fathom-pma-evidence. NEVER a telemetry bucket
    total_bytes           bigint NOT NULL,
    materialised_at       timestamptz,
    materialisation_node  text NOT NULL,
    superseded_by_package_id uuid REFERENCES pma.evidence_package(package_id),
    purge_class           text NOT NULL,    -- 'operationally_append_only' (03 §13 item 3)
    classification        jsonb NOT NULL,   -- union of inputs; inherited_from populated (03 §7.3)
    CONSTRAINT materialised_has_hash
        CHECK (state <> 'materialised' OR (materialised_at IS NOT NULL AND content_hash <> ''))
);
```

**Package composition.** One package per candidate, containing: the implicated channels' samples over the candidate window plus a symmetric context margin; the health-indicator series over the same span with `definition_version`; the operating-condition covariates for the window (13 §9.5 emits them as data, and without them a reviewer cannot distinguish degradation from a load change); the mission record and its completeness assessment; the candidate's own detector attribution; the last three `maintenance_action.recorded` entries for that installed item (§2.7); and the PdM cached prediction for the item at review time **marked degraded if served from an edge cache** (11 §7.3).

**The five source operations, and nothing else.** Materialisation calls Telemetry's published contract (04 §3 API surface):

| Purpose | Telemetry operation |
|---|---|
| The replayable sample window | `GET /missions/{mission_id}/telemetry` |
| Indicator series with definition version | `GET /health-indicators?installed_item_id=&from=&to=&as_of=` |
| Point-in-time-correct covariates | `GET /features?installed_item_id=&feature_set=&as_of=&as_known_at=` |
| The detection under review, and its siblings | `GET /anomalies?mission_id=` |
| Mission boundaries and completeness | `GET /missions/{mission_id}` |

`as_of` and `as_known_at` are both supplied and both recorded. `as_of` alone is insufficient: D22 establishes that indicator definitions are recomputed over history, so a package materialised today from a definition authored today misrepresents what was knowable at mission end. Recording both parameters in `source_calls` makes the package's temporal basis auditable rather than assumed.

**Two prohibitions, both structural.** PMA never reads Telemetry's TimescaleDB, and PMA never reads Telemetry's object store — the store 04 §3 describes as holding "raw mission payloads retained for replay and for Post-Mission Analysis evidence." That sentence is the source of C36 and must be read as *Telemetry retains the replay source; PMA reads it through the API*. NetworkPolicy is what makes this true rather than aspirational (§10.3), and the DoD item in 09 §8.6 — "no direct database access from outside the owning service" — is asserted from both sides.

**Immutability, concretely.** A package becomes immutable when its review opens. Enforcement is three-layered because object stores and databases fail differently: the bucket has versioning and object-lock in governance mode for the package prefix; the row's trigger forbids mutation of `object_manifest` and `content_hash`; and every tag pins `evidence_content_hash`, so a package that somehow changed is detectable by comparison rather than only by trust. A genuine need to re-materialise creates a **new** package with `superseded_by_package_id` set on the old one; existing tags continue to reference the old package forever. 04 §8's reason is exact: "immutable once a review opens so that a tag's basis cannot change after the fact."

**Failure is a state, not an exception.** If materialisation cannot complete — Telemetry unreachable, a replay gap, a completeness record showing the window was never observed — the package lands in `failed`, the candidate moves to `held_no_evidence`, and **the review does not open**. A candidate with no evidence is not reviewable at 45 seconds; presenting one produces a reflex rejection, which is a false negative injected by the platform itself. Materialisation is retried with monotonic backoff up to a deadline, after which the candidate is retained for a later attempt.

### 2.7 Consumed-event read models

PMA maintains four read models, each rebuilt from `changed_since` reads and never from the event bus (03 §5.1, D5).

| Read model | Fed by | Used for |
|---|---|---|
| `rm_configuration` | `configuration.baseline_changed`, plus `GET /registry/installed-items?changed_since=` for rebuild | Epoch fencing (§3.5); `equipment_class` for the taxonomy projection filter (§4.2); provisional-identity alias resolution (11 §8) |
| `rm_mission` | `mission.completed`, `telemetry.batch_ingested` | Review creation trigger; data-completeness gating |
| `rm_detection` | `anomaly.detected` | Candidate creation (§3.1) |
| `rm_maintenance_context` | `maintenance_action.recorded` | Review context and retrospective tag-quality assessment |

**`maintenance_action.recorded` is consumed for review context, and this is confirmed in the 03 §6 catalog** — the row lists `pma` among its consumers alongside `pdm`, `failure-intel`, `registry`, `supply`, and `design-advisory`. Document 04 §8 gives the reason: it lets a review "present what was subsequently found and repaired alongside the candidate window — the single most useful context a reviewer can have."

Three rules on this read model, because it is the most misusable data PMA holds:

1. **The maintenance record is context, never ground truth.** A findings code on a 4790/2K is the maintainer's assertion in the 3-M vocabulary; the reviewer's signature is an observation in the PMA projection. 12 §9.3 is binding: *"that disagreement is a retained first-class signal, not an error to clean."* PMA never adjusts, pre-fills, or defaults a signature choice from a findings code, and never auto-confirms a candidate because a repair was recorded.
2. **The 3-M side is set-valued.** A findings record resolves to `candidate_modes[]` with confidence, never one mode (12 DO-NOT-2). The read model stores the full candidate set and the evidence package renders it as a set. A `LIMIT 1` anywhere on this path is a review rejection.
3. **The record may be wrong, and the generator guarantees it will be.** 13 §9.10 emits wrong findings codes, **wrong-item attribution**, date rounding, duplicate 2-Kilos, corrective/preventive misclassification, missing `triggering_driver`, and narrative-code inconsistency. Wrong-item attribution is the dangerous one: a record filed against a sibling position must not cause a tag to attach to the wrong `installed_item_id`. PMA joins maintenance context on `installed_item_id` and displays the `position_id` alongside it so a mismatch is visible to the reviewer rather than silently absorbed `[C10, D9]`. §9.5 tests each corruption class.

### 2.8 `Proposal` — kind `anomaly_tag`

The schema is fixed by 03 §7.2 and implemented once in `packages/canonical-schemas` (10 §4.7). PMA owns proposals whose `target_sub_app` is `pma`; the only kind it accepts is `anomaly_tag`. The service-local projection stores the canonical shape plus the adjudication bookkeeping, and PMA sets four fields at creation from 03 §7.2.1 rather than accepting them from the proposer:

| Field | Value PMA sets | Authority |
|---|---|---|
| `authority_class` | **`maintainer`** | 03 §7.2.1 minimum-authority table: `anomaly_tag` at `item`/`asset` radius requires `maintainer` — the Ship's Force Maintainer role, whose sub-application context the table gives as "Confirms anomaly tags, item-scoped work candidates" |
| `blast_radius` | `item` | An anomaly tag is a statement about one installed item's one window |
| `requires_dual_control` | `false` by default | Item scope, no external legal effect (03 §7.2). A deployment may *strengthen* this to `true` for signatures whose crosswalked modes carry `consequence_class = safety`; it may never weaken it |
| `valid_until` | Review deadline plus a configured margin | 10 §4.7 reads 03 §7.2's "absent means no expiry is permitted" as making the field mandatory |

**`anomaly_tag` has no class or fleet radius, and PMA enforces that at the boundary.** The 03 §7.2.1 table marks both cells "— (not applicable at this scope)". A proposal arriving with `blast_radius` of `class` or `fleet` is rejected with `422` and `urn:fathom:problem:pma:blast-radius-not-permitted`. This is not pedantry: the whole point of the authority-versus-blast-radius check (D16) is that "an `interval_change` suppressing a preventive task across a class is not the same act as confirming an anomaly tag, and must not be adjudicable by the same authority." Permitting a class-scoped `anomaly_tag` would create precisely the ambiguity the table removes.

**[AMENDMENT — corrected and resolved.]** This note previously typed `authority_class` as an opaque string per 10 §4.7's then-open **OQ-13** — *"the vocabulary of `authority_class` is undefined"* — and had PMA validate against a **five**-value list (`maintainer | planner | supply_officer | design_authority | fleet_authority`) as its own stopgap enforcement point, pending the shared package narrowing `NonEmptyStr` to a `StrEnum`. That five-value list omitted `security_officer` — a real defect, not just a stale note: PMA's own validation would have **rejected** a valid `security_officer` value on any proposal it owned requiring that authority. Both halves are now resolved: `10-shared-packages.md` §4.6b/§4.7 defines the real six-value `AuthorityClass` `StrEnum` (`security_officer` included) and retypes `Proposal.authority_class` to it, closing OQ-13 — so PMA asserts `maintainer` for every proposal it owns and validates against the shared package's own enum, not a locally duplicated list.

**Re-validation at adjudication is mandatory and PMA's list is specific** (03 §7.2 rule 2, D16). At `POST /proposals/{id}/adjudicate` the service re-checks, in order, and rejects on the first failure:

1. `valid_until` has not passed (monotonic-evaluated lease semantics; 09 §5.4).
2. `baseline_epoch` is not superseded in `rm_configuration`.
3. The `installed_item_id` is present in the current baseline, and is not an unreconciled provisional identity that the Registry has since **superseded** (11 §8.4 — the alias is resolved and the proposal re-pointed, or rejected if the supersession changed the physical item).
4. The evidence package still verifies against its `content_hash`.
5. The proposed `signature_key` still exists at the current published `taxonomy_version`; if not, `POST /taxonomy/resolve` is called and the adjudicator is required to re-select from the resolved set rather than having a substitution applied on their behalf (§4.4).

Approval creates an `AnomalyTag` whose `reviewer_id` is **the human adjudicator**, with the agent recorded in `proposing_agent_id`/`proposing_agent_version`/`proposing_llm_version`/`proposing_trace_ref`. 01 §8.2 is unambiguous: "Human confirmation remains the label of record; the agent only proposes." Rejection creates a `TagRejection` with a `reason_class` supplied by the adjudicator.

---

## 3. The review orchestrator and candidate ranking

### 3.1 The pipeline, in order

The orchestrator is a state machine driven by consumed events. Stages are strictly ordered, and the order is part of the specification because it is what guarantees a review never opens with unmaterialised evidence or an unfenced epoch.

| # | Stage | Trigger | Output |
|---|---|---|---|
| 1 | **Candidate capture** | `anomaly.detected` inbox handler; `POST /proposals` | `AnomalyCandidate` in `queued_unadmitted`. Never dropped, never deduplicated away |
| 2 | **Review creation** | `mission.completed` inbox handler | `MissionReview` in `pending_evidence`, with `taxonomy_version_pin`, `baseline_epoch`, `candidate_cap` |
| 3 | **Admission gate** | Synchronous, in stage 2's transaction | If the backlog exceeds the threshold (§5.6): state `deferred_admission_control`, stop |
| 4 | **Epoch fence** | Per candidate | Candidates whose `baseline_epoch` is ahead of `rm_configuration` move to `held_on_antecedent` and are excluded from this assembly (§3.5) |
| 5 | **Grouping** | Per candidate set | Near-duplicates over the same `(installed_item_id, window)` are linked into a `candidate_group_id`; one representative is eligible for admission (§3.4) |
| 6 | **Ranking** | Per eligible set | `rank_score`, `rank_components`, `rank_stratum` on every eligible candidate |
| 7 | **Bounded selection** | Greedy under diversity caps | `cap` admitted candidates, plus an ordered `reserve` |
| 8 | **Canary injection** | §5.3 | Plants bound to candidates; set membership adjusted stratum-for-stratum |
| 9 | **Evidence materialisation** | Per admitted candidate | `EvidencePackage` in `materialised`, or the candidate is held and replaced from `reserve` |
| 10 | **Open** | All admitted candidates have materialised evidence | State `open`; `mission_review.opened` published in the same transaction as the state change |
| 11 | **Adjudication** | Reviewer operations | `AnomalyTag` / `TagRejection`, each with its event |
| 12 | **Completion** | `POST /reviews/{id}/complete` | Plant outcomes resolved, metrics updated, `mission_review.completed` published |
| 13 | **Re-review sampling** | On completion, 5% (§6.4) | A `re_review` `MissionReview` over the identical candidate set and packages |

Stage 10 is the only place `mission_review.opened` is emitted, and stage 9 gates it. That ordering is the mechanism behind the ~45 s target: the reviewer never waits on a cross-service fetch, because every fetch happened before they were notified.

### 3.2 Review creation and the assembly transaction

```python
# services/pma/src/fathom_pma/services/orchestrator.py

async def on_mission_completed(self, uow: UnitOfWork, ev: MissionCompleted) -> None:
    async with uow.begin():                                   # 09 §4.1: services/ owns the transaction
        gate = await self.admission.evaluate(scope_node=self.node_id)      # §5.6
        review = await self.reviews.create(
            mission_id=ev.mission_id,
            asset_id=ev.asset_id,
            candidate_cap=self.settings.app.candidate_cap,     # 12 — 06 §6
            taxonomy_version_pin=await self.taxonomy.current_published_version(),
            baseline_id=ev.baseline_id,
            baseline_epoch=ev.baseline_epoch,
            ranker_version=RANKER_VERSION,
            injector_version=INJECTOR_VERSION,
            state=(ReviewState.DEFERRED_ADMISSION_CONTROL if gate.engaged
                   else ReviewState.PENDING_EVIDENCE),
        )
        if gate.engaged:
            await self.audit.record_admission_deferral(review, gate)
            return                                            # no event: nothing was opened

        eligible = await self.candidates.eligible_for(ev.mission_id, review.baseline_epoch)
        grouped  = self.grouper.group(eligible)                        # stage 5
        ranked   = self.ranker.rank(grouped, review)                  # stage 6
        selected, reserve = self.selector.select(ranked, cap=review.candidate_cap)   # stage 7
        selected = await self.canary.inject(uow, review, selected, reserve)          # stage 8
        await self.candidates.admit(uow, review, selected)
    # evidence materialisation (stage 9) runs OUTSIDE this transaction: it performs network I/O
    # and must not hold a database transaction open across it.
    await self.evidence.materialise_for(review)                # completes -> stage 10 opens the review
```

Two mechanical points. The admission gate is evaluated **inside** the creation transaction so that a burst of `mission.completed` events cannot race past a threshold that one of them crossed. Evidence materialisation is **outside** it, because holding a Postgres transaction open across an HTTP fetch of tens of megabytes is how a service exhausts its connection pool.

### 3.3 The ranking function — expected informativeness

04 §8 requires candidates "ranked by expected informativeness" and leaves the function to Phase 3 (it is an explicit Phase 3 question there). This is the function, with weights in configuration and the version pinned on every review.

```python
# services/pma/src/fathom_pma/services/ranking.py
RANKER_VERSION = "pma-ranker-1.0.0"

@dataclass(frozen=True)
class RankWeights:
    detector_confidence:      float = 0.20
    ensemble_disagreement:    float = 0.20
    label_scarcity:           float = 0.20
    maintenance_corroboration:float = 0.15
    novelty:                  float = 0.10
    consequence:              float = 0.10   # BOUNDED: see the bias note below
    evidence_completeness:    float = 0.05
```

| Component | Definition | Why it is informative |
|---|---|---|
`detector_confidence` | The detector's score, **normalised within `detector_version`** using that version's observed score distribution over the trailing window | A raw score is not comparable across detector versions or across the edge/enterprise split. Normalising within version is what stops a detector re-release from silently reordering every review |
`ensemble_disagreement` | Spread across the detectors that scored the window, plus disagreement with PdM's cached prediction for the item | A candidate on which the machinery already agrees teaches little; a candidate on which it disagrees resolves a disagreement, which is the highest-value use of 45 seconds of human attention |
`label_scarcity` | `1 / (1 + n)` where `n` is the count of confirmed tags for `(equipment_family, signature_key)` at the pinned taxonomy version | Directly serves the calibration-population gate: 06 §3 suppresses `p_failure` below `calibration_population = 50`, so labels in thin cells are worth strictly more than labels in full ones |
`maintenance_corroboration` | A `maintenance_action.recorded` on the same `installed_item_id` within the window plus a configured lag | 04 §8: "the single most useful context a reviewer can have." Corroborated candidates are faster **and** more reliably labelled — the one component that improves both halves of the throughput/quality trade |
`novelty` | The candidate's channel signature crosswalks to no entry at the pinned version | Feeds the novel-signature proposal path (§4.4), which is how the vocabulary grows |
`consequence` | Max `consequence_class` severity over the candidate's crosswalked modes, times PdM criticality tier | Operationally obvious, and **deliberately the smallest weight of the substantive components** |
`evidence_completeness` | Telemetry's completeness record for the window | A window with a data gap cannot be reviewed well. This component is a mild preference; a hard failure is handled at stage 9, not here |

**Why `consequence` is capped, stated explicitly because it is counter-intuitive.** Ranking by consequence maximises operational relevance and *biases the label set toward severe modes*. A training corpus assembled from consequence-ranked reviews under-represents the benign and the early-precursor cases, which are exactly what a P-F-interval model needs (MIL-STD-3034A 3.9.3's "definable and measurable condition that indicates a functional failure is imminent", 12 §5.1). The weight is bounded, the resulting severity distribution of confirmed tags is reported in the quality metrics of §5.5, and a drift toward severity is a monitored condition rather than a discovery made during model training.

**Determinism and auditability.** `rank()` is a pure function of `(candidate set, RankWeights, ranker_version, taxonomy_version_pin, rm_* snapshot digest)`. The full component vector is persisted per candidate in `rank_components`, satisfying obligation 9 and making "why was this candidate in the set, and why was that one not" answerable months later. A ranker change is a version bump and is diffable over the reference dataset.

### 3.4 Bounded selection under diversity caps

Top-`cap` by score is wrong in a specific, predictable way: one degrading sensor or one noisy channel produces a dozen high-scoring candidates on one installed item and consumes the entire review. Selection is therefore greedy under caps.

```python
CAP_PER_INSTALLED_ITEM  = 3
CAP_PER_EQUIPMENT_FAMILY = 6          # ceil(cap / 2) at cap = 12
CAP_PER_CANDIDATE_GROUP  = 1          # the representative; the group is linked, never merged (11 §7.3)

def select(ranked: list[Ranked], cap: int) -> tuple[list[Ranked], list[Ranked]]:
    """Greedy admission under diversity caps.  Returns (admitted, reserve-in-rank-order).

    The reserve is ordered and retained because stages 8 and 9 both need a
    same-stratum replacement source: canary injection displaces, and an evidence
    failure vacates.  A candidate that is neither admitted nor reserved returns to
    'queued_unadmitted' and is eligible for a later review of the same mission.
    """
```

**Group representatives are a reconciliation requirement, not an aesthetic one.** 11 §7.3's `EDGE_GENERATABLE` policy states that near-duplicate candidates over the same `(installed_item_id, window)` "are linked as a candidate group with both origins preserved, never merged away." After a reconnect, the enterprise adds candidates that overlap the edge set by construction (13 §15.2 case 3 generates the overlap deliberately). PMA presents one representative per group, preferring the **edge** candidate where a group spans both origins — because the edge candidate is the one a reviewer afloat may already have seen, and because it carries the detector attribution actually used at the time.

### 3.5 Epoch fencing, and what it does and does not fence

03 §5.4's antecedent rule: a consumer receiving an event whose `baseline_epoch` is ahead of its own configuration read model "must block that event until the antecedent configuration event is applied." PMA implements this through the shared inbox (11 §3.5) and applies it at exactly one place in its own logic:

- **Candidate admission is fenced.** A candidate whose window spans, or whose epoch is ahead of, the locally-applied configuration goes to `held_on_antecedent`, increments `fathom_inbox_events_total{outcome="blocked_on_antecedent"}`, and is retried when the antecedent arrives.
- **Tags are not fenced and not invalidated** (§2.4). The tag records the epoch it was assigned under and that is the end of PMA's obligation. A consumer that needs to know whether the configuration has since changed reads the epoch.
- **Provisional identities are resolved, not blocked.** An edge-minted `installed_item_id` with `provisional: true` (03 §3.3, 11 §8) is a legitimate subject for a candidate and a tag afloat. On reconnect the Registry confirms or supersedes it; PMA resolves through the alias table (11 §8.4) so tags authored afloat point at the confirmed identity without any tag being rewritten.

### 3.6 The ~45 s per candidate constraint as an API obligation

06 §6 sets the capacity model: candidate cap **12**, target review duration **≤ 10 minutes**, **45 s per candidate including evidence inspection**, with the note that "the earlier implied ~10 s was a reflex, not a review." This document does not design the UI (09 §1.2 defers look-and-feel), but the target is unachievable unless the API is shaped for it, so the API obligations are stated here and tested in §9.7.

| Obligation | Mechanism |
|---|---|
| **One round trip for the whole set** | `GET /reviews/{id}/candidates?include=evidence_manifest` returns all `cap` candidates with their evidence manifests in one response, each object referenced by `GET /evidence-packages/{id}/objects/{key}` (§3.7's amendment — proxied through this service, never a pre-signed direct-to-bucket URL). Default page size equals `candidate_cap`, so cursor pagination exists (03 §4) but is never exercised at the cap |
| **No cross-service fetch during review** | Evidence is materialised at stage 9, before the review opens. A reviewer request never fans out to Telemetry |
| **Pre-signed URLs outlive the review** | Object URLs are issued with an expiry of at least the review budget plus margin, so the twelfth candidate's plot does not 403 at minute nine |
| **Prefetch of the next review** | `GET /reviews/next?reviewer=` returns the next claimable review, already `open` and materialised, so a reviewer finishing one review does not wait for another to assemble. A singular query projection: enumerated in `x-naming-carve-outs` with a reason (09 §5.1, C23) |
| **Sequential adjudication without a round trip per decision** | `POST /reviews/{id}/adjudications` accepts an array of confirm/reject decisions, idempotent on `Idempotency-Key`, applied in one transaction. The per-candidate `confirm` / `reject` operations of 04 §8 remain and remain `required`; the batch operation is the latency path |
| **Reviewer lease** | `POST /reviews/{id}/claim` takes a monotonic-evaluated lease, so two reviewers are never adjudicating one review — the same defect D16 identifies for proposals, in the review workflow |
| **Dwell is measured, per candidate** | The client reports per-candidate dwell with each decision; the service records it and clamps it to the review's own monotonic duration so a reported dwell cannot exceed elapsed time. `fathom_pma_candidate_dwell_seconds` is a histogram, not a mean — a mean of 45 s over a bimodal distribution of 8 s and 90 s is the shape D17 warns about, and only a histogram shows it |
| **Latency budget** | p95 < 1.5 s for the candidate-set fetch and p95 < 4 s for the evidence render, per 06 §7's operator budget for fleet/asset views and explanation decomposition respectively |

**If 45 s proves wrong, the cap moves and this document changes.** 06 §6 marks the figure MEDIUM confidence — "untested with actual maintainers" — with the stated consequence that "if real inspection takes 2–3 minutes, the candidate cap drops to 4–5 and candidate ranking becomes far more consequential." `candidate_cap` is therefore a Helm value, not a constant, and the ranker is built to be worth improving.

### 3.7 API surface

Base path `/api/v1/pma/`. Every operation carries `x-substitution` and `x-side-effects`; `x-agent-eligible` appears only where side effects are `none` or `proposal-only` (03 §8.1, obligation 8, C1/D11). The eight operations document 04 §8 marks Required are marked `required` here and nothing else is.

| Operation | Purpose | `x-substitution` | `x-side-effects` | `x-agent-eligible` |
|---|---|---|---|---|
| `GET /reviews?asset_id=&status=&reviewer=&changed_since=&limit=&cursor=` | Review queue; `changed_since` is the rebuild path for `audit` and `fleet-status` | `required` | `none` | yes |
| `GET /reviews/{id}` | One review with `ETag` | `required` | `none` | yes |
| `GET /reviews/{id}/candidates?include=&limit=&cursor=` | The bounded set, optionally with evidence manifests (§3.6) | `required` | `none` | **no** — see below |
| `POST /reviews/{id}/candidates/{cid}/confirm` | Create an `AnomalyTag` | `required` | `state-changing` | no |
| `POST /reviews/{id}/candidates/{cid}/reject` | Create a `TagRejection` | `required` | `state-changing` | no |
| `POST /reviews/{id}/complete` | Close the review; resolve plant outcomes; publish | `required` | `state-changing` | no |
| `GET /tags?installed_item_id=&mission_id=&taxonomy=&changed_since=&cursor=` | The label stream, for `failure-intel` and `pdm` | `required` | `none` | yes |
| `GET /taxonomy?version=&equipment_class=` | **Read-through view** of Reference Data's PMA projection (§4.1). Not an independent vocabulary | `required` | `none` | yes |
| `POST /proposals` | Agent-originated anomaly candidates (03 §7.2) | `required` | `proposal-only` | yes |
| `GET /rejections?installed_item_id=&changed_since=&cursor=` | Negative labels, for `failure-intel` and `audit` | `required` | `none` | yes |
| `GET /proposals?status=&cursor=`, `GET /proposals/{id}` | Proposal queue for the gateway's unified view | `required` | `none` | yes |
| `POST /proposals/{id}/claim` | Adjudication lease; `If-Match` required (03 §7.2 rule 3) | `required` | `state-changing` | no |
| `POST /proposals/{id}/adjudicate` | Approve/reject with re-validation (§2.8); `If-Match` required. **Reserved for a proposal never admitted into a review's bounded set** — see the amendment below | `required` | `state-changing` | no |
| `POST /reviews/{id}/claim` | Reviewer lease | `internal` | `state-changing` | no |
| `POST /reviews/{id}/adjudications` | Bulk sequential adjudication (§3.6) | `internal` | `state-changing` | no |
| `GET /reviews/next?reviewer=` | Prefetch. Singular carve-out | `internal` | `none` | no |
| `GET /candidates?changed_since=&cursor=` | Candidate change feed (internal rebuild) | `internal` | `none` | no |
| `GET /evidence-packages/{id}` | Manifest: `object_manifest`, `content_hash`, `bucket` | `internal` | `none` | no |
| `GET /evidence-packages/{id}/objects/{key}` | **[amendment, closes `51-operator-console.md` §22 row 59, blocking]** Streams the object's bytes through this service, proxied by the gateway's existing pass-through — **not** a pre-signed direct-to-bucket URL. No document declared whether an operator's browser can reach the `fathom-pma-evidence` bucket's endpoint, and 03 §4's single-ingress principle (*"prevents collision at the single gateway ingress"*) argues against opening a second one for object storage specifically. This operation keeps evidence access inside the one ingress the rest of the contract already relies on; `GET /evidence-packages/{id}/objects` (plural, no key) is retired — it was never more than the pre-signed-URL shape this replaces | `internal` | `none` | no |
| `POST /tags/bulk` | Backfill of historical labels; `X-Backfill: true`; fenced on `baseline_epoch` (03 §4, §5.3) | `internal` | `state-changing` | no |
| `GET /quality-metrics?window=&scope_node=` | **Precision and canary recall jointly** (§5.5). ABAC-restricted | `internal` | `none` | **no** |
| `GET /admission-control?scope_node=` | Gate state, backlog, threshold, basis. Singular carve-out | `internal` | `none` | no |
| `POST /admission-control/override` | Time-boxed override; dual control; audited (§5.7) | `internal` | `state-changing` | no |
| `GET /reviewers/{id}/qualifications` , `POST /reviewers/{id}/qualifications` | Qualification management (§6) | `internal` | `state-changing` | no |
| `GET /labels/export?...` | Training extract, gated on holdout inclusion (§6.5) | `internal` | `none` | **no** |
| `GET /healthz` , `GET /readyz` , `GET /metrics` | Per 03 §4 | `internal` | `none` | no |

**`GET /reviews/{id}/candidates` is deliberately not agent-eligible**, despite being a read with no side effects. It is the operation that returns candidate sets, and an agent with broad read access to candidate sets across many reviews is the one caller positioned to *learn* a canary tell from aggregate structure — the failure 06 §6 names. The pre-screener has no need for it: it reads Telemetry and proposes. Withholding eligibility costs nothing and closes an avenue. Recorded here as an `[ESTABLISHED HERE]` decision so a manifest author does not add it later without reading this paragraph.

**[AMENDMENT — closes `41-pma-prescreener.md` §20 item 4, flagged as blocking.]** An agent-originated candidate was reachable through two independent adjudication surfaces — the reviewer's `POST /reviews/{id}/candidates/{cid}/confirm`/`.../reject` and the proposal's `POST /proposals/{id}/adjudicate` — plus the gateway's unified queue (built from `fathom.pma.proposal.v1`, `30-gateway.md` §4.1). If both were live and independent, one candidate could be adjudicated twice, double-counting the scarce reviewer-hour budget **D17** exists to protect. The rule, stated once so it cannot drift:

- **The reviewer's `confirm`/`reject` on a candidate that was admitted into a review's bounded set *is* the adjudication of that candidate's proposal, if it has one.** Both the `AnomalyTag`/`TagRejection` and the proposal's `approved`/`rejected` transition happen in the **same transaction** (§8.5 already requires this transaction for the resulting events; it now also carries the proposal state change).
- **`POST /proposals/{id}/adjudicate` is reachable only for a proposal that was never admitted** — rejected by admission control (§5.6/§5.7) before a review ever saw it, or superseded before a review opened. Calling it against an admitted proposal's `id` returns `409 urn:fathom:problem:pma:already-adjudicated-via-review`.
- **The gateway's unified queue renders an admitted agent proposal as `claimed_by_review`**, not `proposed` — it is not a second pending item, it is a status reflection of the review that already owns it.

**Problem detail types**, declared once in `schemas/problems.py` per 09 §5.2, `urn:` scheme (never `https://`, 09 §5.2 and DO-NOT 26):

```
urn:fathom:problem:pma:admission-control-engaged      429  Retry-After set (§5.6)
urn:fathom:problem:pma:evidence-not-materialised      409
urn:fathom:problem:pma:review-not-claimed             409
urn:fathom:problem:pma:candidate-already-adjudicated  409
urn:fathom:problem:pma:tag-immutable                  409
urn:fathom:problem:pma:baseline-superseded            409  baseline_epoch_submitted / _current
urn:fathom:problem:pma:signature-unknown-at-version   422  resolved_alternatives[] (§4.4)
urn:fathom:problem:pma:blast-radius-not-permitted     422  (§2.8)
urn:fathom:problem:pma:divergence-budget-exceeded     423  (11 §9.1)
urn:fathom:problem:pma:quality-metrics-forbidden      403  (§5.5 ABAC)
```

---

## 4. Consuming the taxonomy projection

03 §14 fixes the ownership: "Reference Data is the single owner of the unified taxonomy — definition, versioning, publication. Post-Mission Analysis owns tag *assignments*." 12 §4 fixes the mechanics: PMA holds "a cache keyed by `taxonomy_version`" of one projection, and PMA's own `GET /taxonomy` "remains in PMA's contract as a **read-through view of this service**, not an independent vocabulary."

### 4.1 The three operations PMA calls, by name

Verified against the live operation table in 12 §3.1:

| Purpose | Reference Data operation |
|---|---|
| **The reviewer's choice list** — the coarsened subset keyed on `observable_signature`, including exactly one `is_novel_escape` row | `GET /taxonomy/projections/pma?version=&equipment_class=` |
| **Signature ↔ failure-mode resolution, both directions** — used to populate `resolved_lineage_ids`, to compute signature agreement (§5.5), and to render candidate modes | `GET /crosswalk/pma-signatures?version=&signature_key=&code=&changed_since=&cursor=` |
| **The current published version, and the version register** | `GET /taxonomy/versions` |
| **Forward resolution of held references** when exporting or re-adjudicating historical labels | `POST /taxonomy/resolve` |
| **Novel-signature and crosswalk-revision proposals** | `POST /taxonomy/proposals` |

PMA does **not** call `GET /taxonomy` on Reference Data. That returns the full vocabulary and is Failure Intelligence's projection (12 §4). PMA holding the full vocabulary would be finding C8 reintroduced.

### 4.2 The cache, and the one permitted local copy

```python
# services/pma/src/fathom_pma/services/taxonomy.py

class TaxonomyProjectionCache:
    """Read-through cache of GET /taxonomy/projections/pma, keyed by taxonomy_version.

    This is the ONLY local copy of taxonomy content permitted anywhere in this service
    (12 DO-NOT-1).  There is no signature enum in code, no signature list in a form
    component, no hard-coded failure-mode code, and no family list in configuration.
    Enforced repository-wide by the `tax-single-source` static check (12 §8.1), which
    fails the build on any taxonomy literal outside reference-data and its package.
    """
    async def signatures(self, version: str, equipment_class: str | None) -> Signatures: ...
    async def resolve(self, signature_key: str, version: str) -> tuple[UUID, ...]: ...
```

Cache entries are immutable, keyed by version, and never evicted while a review pins them. `equipment_class` is passed as a **filter parameter** obtained from `rm_configuration` (the system's ESWBS/EIC class code) and is **never used as a join key** — 03 §3.3 and 12 DO-NOT-7: EIC is "a class code of variable specificity, not an instance identifier." Joins are on `system_id`, `installed_item_id`, `niin`, and `lineage_id`.

**Refresh, and an open catalog problem.** 12 §3.4 declares `taxonomy_version.published`, `taxonomy_entry.superseded`, and `crosswalk.published` on `fathom.reference-data.taxonomy.v1` with `pma` among the consumers — but flags **OD-7**: document 03 §6's catalog "covers the nine sub-applications and does not enumerate platform services," so those topics have no catalog rows. 09 §6.2 job 6 reconciles `events/catalog.py` against 03 §6 in both directions and fails on a mismatch.

**Interim position, recorded so it is not treated as settled** (09 §1.3): PMA does **not** subscribe to `fathom.reference-data.taxonomy.v1`. It refreshes the cache by polling `GET /taxonomy/versions` with `If-None-Match` on a configured interval and on every review creation, which keeps the catalog reconciliation gate green and costs one conditional GET. When OD-7 lands and the rows exist in 03 §6, the subscription replaces the poll and the poll becomes the fallback. §13 carries the item.

### 4.3 Version pinning across a review

A review pins `taxonomy_version_pin` at creation (§2.1) and every tag and rejection in it carries that version (I1). Three consequences:

1. **The reviewer's choice list does not change mid-review.** If Reference Data publishes `1.3.0` while a review pinned at `1.2.0` is open, the reviewer continues to select from `1.2.0`.
2. **A ship at sea produces perfectly valid labels at an older version.** 12 §4's edge paragraph states it directly: "a ship reviewing at `1.2.0` while shore has published `1.3.0` produces perfectly valid, resolvable labels. This is the direct payoff of invariant I1."
3. **Nothing is ever rewritten.** 12 §6.2: a held `(signature_key, taxonomy_version)` pair "remains byte-identical across every future version bump," and meaning is recovered by forward resolution at read time. PMA never migrates a historical tag to a new version, and 12 DO-NOT-5's reasoning applies transitively: a silent re-pin changes the meaning of every label under it.

### 4.4 The novel-signature path — PMA proposes, Failure Intelligence approves

12 §2.8 requires the projection to carry "an explicit `unclassified/novel` escape," and §7.2 specifies the flow. PMA's implementation:

1. The reviewer selects the `is_novel_escape` signature and describes what they observed. **The tag is created and is valid data, not a validation error** (12 §7.2: "PMA stores that tag — it is valid data, not an error").
2. `anomaly_tag.confirmed` publishes with `signature_key` = the escape row and `is_novel_escape = true`, so downstream consumers can see immediately that this label is pending vocabulary work.
3. PMA submits `POST /taxonomy/proposals` to Reference Data with `kind = novel_signature`, `against_version` = the review's pin, evidence non-empty (03 §7.2) comprising the evidence package reference and the reviewer's description, and `proposer_sub_app = 'pma'`.
4. **Failure Intelligence adjudicates. PMA cannot.** 12 §3.3 gives PMA "may propose: `novel_signature`, `crosswalk_revision`; may approve: **No**", and 12 §2.11's `approver_is_authorised` database constraint enforces it a second time at Reference Data.
5. On approval and publication, the original tag is **never rewritten**; it resolves forward through the crosswalk to the new entry, "and both the escape tag and the resolved mode are visible" (12 §7.2).

Two disciplines on the free text. It is **untrusted content** in the 03 §9 sense the moment it can reach an agent prompt or the retrieval corpus: structurally separated from instructions, never able to alter tool selection, and carried as evidence with `source_trust: program`. And a novel-signature proposal is not a licence to invent a code: PMA proposes a *signature*, and any code that results is Reference Data's to mint under 12 DO-NOT-3's `FATHOM-EXT-nnn` discipline.

**Two distinct proposal directions, and confusing them is a real error.** PMA is the **owner and adjudicator** of `Proposal` with `target_sub_app = 'pma'`, `kind = 'anomaly_tag'` (§2.8), published on `fathom.pma.proposal.v1`. PMA is a **proposer** to Reference Data for `novel_signature` and `crosswalk_revision`, and those proposals live in Reference Data's aggregate and appear on `fathom.reference-data.proposal.v1`. PMA never publishes another sub-application's proposal events.

### 4.5 Reconciliation is at read time, and PMA does not normalise

12 §9.3 quotes 08 §2.8 non-negotiable 3: "**Reconcile at read time, never at write time.** Each capture point stores what its user actually asserted, in that user's vocabulary; the unified view is computed." PMA stores the signature the reviewer chose. It does not translate it to a 3-M code, does not translate a findings code into a signature, and does not offer an operation that accepts a 3-M tuple and returns one signature for storage (12 DO-NOT-8). The operational example 12 §9.3 gives is exactly PMA's case: "a reviewer watching telemetry saw an abnormal instrument reading; a maintainer who opened the pump filed *normal wear and tear*. Neither is wrong and they are not the same claim." Preserving that disagreement is the reason three capture points exist.

---

## 5. Recall measurement, canary injection, and admission control

**This section is the reason the document exists.** D17: precision is measured against human adjudication, rejections train detectors toward silence, volume falls, and "both governing metrics improve monotonically — while recall collapses and nothing measures recall, because there is no independent ground truth." 06 §6 supplies the three countermeasures and their parameters; this section specifies them as code.

### 5.1 What is measured, and the decomposition that makes it honest

Recall is not one quantity. It is a composition of two, and conflating them produces a metric that cannot locate a failure.

| Metric | Definition | Measures | Source of truth |
|---|---|---|---|
| **Canary recall** | confirmed canaries / adjudicated planted canaries | **Adjudication-stage recall**: does the reviewer confirm a true positive that reaches them? | The plant registry (§2.3), from the generator's canary designation (13 §13) |
| **End-to-end recall** | confirmed tags matching truth anomalies / all truth anomalies in the mission | **The composite**, including detector recall and cap truncation | The exhaustively-labelled reference sample (13 §13.3) |
| **Precision** | confirmed tags / adjudicated candidates | Candidate quality — the metric that rises as the pipeline dies | Adjudication outcomes |

Canary recall is the *fast* signal: every review contributes, and it responds within days to a reviewer beginning to reject-to-finish. End-to-end recall is the *complete* signal but exists only for the reference-sample missions, where the generator "enumerates every anomaly, whether or not it was surfaced as a candidate" (13 §13.3). Both are required. Canary recall alone cannot see a detector that stopped firing; end-to-end recall alone cannot be computed often enough to be an operational alarm.

06 §6's second countermeasure is exactly this: "**Rejections are not the sole training signal.** An exhaustively-labelled holdout sample of missions — feasible because the generator knows the truth — provides a reference independent of adjudication behavior."

### 5.2 The one rule, inherited from the generator, and its enforcement in PMA

13 §13.1: **"A canary must be produced by the same code path, from the same parameter distributions, as an ordinary fault."** If canaries were generated by a separate injector — "a synthetic spike, a scaled template, a shortened trajectory" — then "canary recall is not an unbiased estimate of recall on ordinary faults, and the recall metric that 06 §6 introduces to close the precision/recall trap silently measures the wrong population."

PMA inherits that rule and adds the second half of it, because the generator's guarantee covers the *signal* and PMA must guarantee the *presentation*:

> **A canary candidate must be indistinguishable from an ordinary candidate in every field, artefact, and timing observable by a reviewer.**

Four enforcement mechanisms, each a mechanism rather than a discipline:

| Mechanism | Implementation |
|---|---|
| **No canary field exists in any reviewer-facing wire model** | `AnomalyCandidateView` in `schemas/candidates.py` has no `origin`, no `canary_*`, and no `plant_*` member. A field that does not exist cannot be leaked by a serialiser change, a debug flag, or an `include=` parameter |
| **No reviewer-facing repository method references the plant table** | `repositories/candidates.py` methods serving reviewer operations do not join `pma.canary_plant`. Asserted by a static check over the module's SQL (§9.4) |
| **Detector attribution is copied, never synthesised** | A plant rides on a real `anomaly.detected` (`source_event_id` is `NOT NULL`, §2.3). `detector_version` and `detector_score` are the real values. There is no code path that writes a detector version PMA invented |
| **Runtime distributional indistinguishability monitor** | A scheduled job runs two-sample tests over every field of the reviewer-facing projection, canary versus non-canary, **within mission type and rank stratum**, and reports p-values *with power*. Mirrors 13 §13.2's build-time test: "this is the rare case where failing to reject is the passing condition… a low-power test that fails to reject proves nothing, and the harness marks that case as unproven rather than passed" |

The monitor is the important one, because it is the only mechanism that catches a tell introduced *later* — a new field, a changed default, a differing latency. The build-time test in §9.4 proves the schema is clean today; the monitor proves the data stays clean.

**Canary status is never surfaced before adjudication, in any channel.** Not in an event (§8.4), not in a metric (§5.4), not in an audit record read by a supervisor, not in a notification. The one channel that carries canary information is `mission_review.completed`, which 03 §6 specifies as carrying "canary outcomes" — published *after* the reviewer's decisions are final, in aggregate counts only.

### 5.3 The injector

Density is **15% of candidates** (06 §6), which at cap 12 is an expected 1.8 canaries per review and, against 06 §6's ~840 candidates per month, ~126 planted canaries per month.

**Density varies rather than being constant per review**, because 06 §6's mitigation for canary detectability is to "vary density and injection realism," and because a constant "at least one canary per review" is itself a tell — a reviewer who has found one plant would know to stop looking. The count is drawn per review, and the draw admits zero.

```python
# services/pma/src/fathom_pma/services/canary.py
INJECTOR_VERSION       = "pma-canary-injector-1.0.0"
CANARY_DENSITY_TARGET  = 0.15            # 06 §6
CANARY_P_BOUNDS        = (0.08, 0.25)    # the controller's clamp
CANARY_MAX_PER_REVIEW  = 4               # bound: never dominate a review
CONTROLLER_GAIN        = 0.5


class CanaryProvenance(StrEnum):
    DESIGNATED = "designated"   # the ranker would have admitted this candidate anyway
    ADMITTED   = "admitted"     # a REAL sub-cap detection, promoted into the set


class CanaryInjector:
    """Binds planted canaries to real candidates inside a bounded review set.

    Two provenances, and NEITHER fabricates a detection:

      DESIGNATED — the plant's underlying detection is already in `selected`.  Injection is
        pure bookkeeping: the set does not change at all.  Measures reviewer recall on
        candidates the reviewer would have seen regardless.

      ADMITTED — the plant's underlying detection is in `reserve`, i.e. it is a real
        detection the cap would have truncated.  It is promoted, displacing the
        lowest-ranked non-canary admitted candidate FROM THE SAME RANK STRATUM.  Measures
        reviewer recall on the marginal candidates the cap drops — which is where recall
        collapse appears first, because a reviewer under time pressure rejects the
        unconvincing ones and the unconvincing ones live at the margin.

    A plant whose underlying detection is in NEITHER set is unusable for this review and is
    left in the pool.  It is never made usable by synthesising a detection: that would
    violate 13 §13.1 and make canary recall an estimate of nothing.
    """

    def inject(
        self,
        uow: UnitOfWork,
        review: MissionReview,
        selected: list[Ranked],          # the cap-length admitted set, rank-ordered
        reserve: list[Ranked],           # sub-cap remainder, rank-ordered
    ) -> list[Ranked]:
        rng = self._rng(review.review_id)            # deterministic per review; seeded, reproducible
        p_eff = self._controller_p()                 # §5.3.1
        n_target = min(CANARY_MAX_PER_REVIEW, rng.binomial(review.candidate_cap, p_eff))

        pool = self._available_plants(review.mission_id, self.node_id)   # unconsumed, this mission
        planted = 0
        for plant in self._shuffled(pool, rng):
            if planted >= n_target:
                break
            hit = self._find(selected, plant.source_event_id)
            if hit is not None:
                self._bind(uow, plant, hit, CanaryProvenance.DESIGNATED, review)
                planted += 1
                continue

            promotable = self._find(reserve, plant.source_event_id)
            if promotable is None:
                continue                              # unusable here; leave in pool

            victim = self._lowest_non_canary_in_stratum(selected, promotable.rank_stratum)
            if victim is None:
                continue                              # stratum full of canaries; skip rather than distort
            selected.remove(victim)
            selected.append(promotable)
            self._return_to_queue(uow, victim)        # NOT dropped: back to queued_unadmitted
            self._bind(uow, plant, promotable, CanaryProvenance.ADMITTED, review)
            planted += 1

        self._record_density(uow, review, planted, n_target, p_eff)
        selected.sort(key=lambda c: -c.rank_score)    # presentation order is rank order (§5.3.2)
        for ordinal, cand in enumerate(selected, start=1):
            cand.presentation_ordinal = ordinal
        return selected
```

#### 5.3.1 The density controller

A per-review binomial draw gives realistic variance but its long-run mean drifts with pool availability — plants are unusable when their detection is neither selected nor reserved, so realised density runs below target. The recall estimator's denominator depends on the realised count, not the target, so drift does not bias the estimate; but it does erode statistical power, and below the gate of §5.5 it stops the estimate being published at all. A bounded proportional controller corrects it:

```python
def _controller_p(self) -> float:
    """Nudge p toward the realised-density target without making per-review density constant.

    realised = planted / candidates_admitted, over the trailing controller window.
    """
    realised = self._realised_density_trailing()
    error = CANARY_DENSITY_TARGET - realised
    return min(max(CANARY_DENSITY_TARGET + CONTROLLER_GAIN * error, *CANARY_P_BOUNDS[:1]),
               CANARY_P_BOUNDS[1])
```

The clamp matters as much as the gain. An uncapped controller responding to a depleted pool would drive `p` upward until nearly every candidate was a plant, which is both spottable and a waste of adjudication capacity on candidates whose answer is known. When the controller saturates at the upper bound and realised density is still below target, that is a **pool-depletion alarm** (§5.4), not something to compensate away.

#### 5.3.2 Why rank-stratum matching, and why presentation stays rank-ordered

Two spottability channels exist beyond field content: **where in the set** a canary appears, and **how good it looks**.

Presentation order is rank order, because best-first is what makes 45 seconds per candidate achievable — an implementation that randomised presentation would trade the capacity model for a marginal anti-detection gain. Position is therefore informative about rank, so rank must be made uninformative about canary status. Stratum-matched displacement does exactly that: a promoted plant replaces a non-canary from its own tercile, so the canary rank distribution equals the non-canary rank distribution by construction. A reviewer who learns "plants are the weak ones near the bottom" learns something false.

The `DESIGNATED` provenance contributes no distortion at all, since the set is unchanged. It is the majority of plants in a healthy pool, and it is the cheapest possible injection: a canary that is simply a candidate the reviewer was always going to see.

#### 5.3.3 The plant pool

| Concern | Position |
|---|---|
| **Where plants come from** | The generator designates already-generated faults as canaries (13 §13.1) and records `canary` / `canary_injection_id` in `truth/` (13 §8.7). PMA's plant registry is loaded from that designation set for the demonstration |
| **How the pool is loaded** | An operator-run load into `pma.canary_plant` under an evaluation identity, never by a reviewer-reachable operation, and never from the observed corpus (13 §13.2: "canary flags are in `truth/` only… a canary flag reachable from the observed corpus destroys the metric outright") |
| **Production path** | Where no generator exists, plants are drawn from *historically confirmed tags on other hulls* replayed as candidates for the same equipment family — a real detection, a known outcome, and no synthesis. Recorded as an open item (§13) because it introduces a distribution-shift question the demonstration does not have to answer |
| **Depletion** | A pool with no usable plant for a mission is a monitored, alarmed condition, not a silent zero. `fathom_pma_canary_pool_remaining` and the `canary_pool` readiness check (§10.4) |
| **Reuse** | A consumed plant is never re-planted for the same reviewer. Re-planting the same window to the same person converts a recall probe into a memory test |

### 5.4 Recall computation

```python
# services/pma/src/fathom_pma/services/recall.py
RECALL_MIN_PLANTS = 30      # publication gate; see the note below


@dataclass(frozen=True)
class CanaryRecall:
    value: float | None            # None when gated
    status: Literal["published", "insufficient_canaries"]
    numerator: int                 # confirmed plants
    denominator: int               # adjudicated plants (distinct plant_id)
    ci_low: float | None           # Wilson score interval, 95%
    ci_high: float | None
    coverage: float                # adjudicated plants / planted plants  -> queue health
    window_start: datetime
    window_end: datetime
    scope_node: str


def canary_recall(session, window: Window, scope_node: str) -> CanaryRecall:
    """confirmed canaries / planted canaries, per 06 §6.

    Three definitional choices, each of which is a decision:

    1. The DENOMINATOR is *adjudicated* plants, not all planted plants.  A plant sitting in
       an unopened or abandoned review is not evidence about reviewer behaviour, and
       counting it would make a queue backlog look like a recall collapse — which would
       fire the alarm for the wrong reason and teach operators to distrust it.  Queue health
       is reported separately as `coverage`, so nothing is hidden by the choice.

    2. A plant is CONFIRMED if the reviewer created an AnomalyTag against its candidate, at
       ANY signature including the novel escape.  Recall is about detection, not
       classification.  Classification quality is `signature_agreed` and is reported
       separately (§5.5); folding it in would let a taxonomy disagreement read as a missed
       detection.

    3. Observations are CLUSTERED ON plant_id.  A plant that appears in a primary review and
       again in a double-blind re-review (§6.4) yields two correlated observations of one
       plant; counting both would understate the interval.  One observation per plant, from
       the PRIMARY review, and the re-review observation feeds inter-reviewer agreement
       instead.
    """
    rows = session.execute(
        """
        SELECT p.plant_id, p.outcome
          FROM pma.canary_plant p
          JOIN pma.mission_review r ON r.review_id = p.review_id
         WHERE p.staged_for_node = :node
           AND r.review_kind = 'primary'
           AND p.outcome_recorded_at >= :start AND p.outcome_recorded_at < :end
           AND p.outcome IN ('confirmed', 'rejected', 'unadjudicated')
        """,
        {"node": scope_node, "start": window.start, "end": window.end},
    ).all()

    planted = session.scalar(
        """SELECT count(*) FROM pma.canary_plant
            WHERE staged_for_node = :node AND injected_at >= :start AND injected_at < :end""",
        {"node": scope_node, "start": window.start, "end": window.end},
    )

    denominator = len(rows)
    numerator = sum(1 for r in rows if r.outcome == "confirmed")
    coverage = (denominator / planted) if planted else 0.0

    if denominator < RECALL_MIN_PLANTS:
        return CanaryRecall(None, "insufficient_canaries", numerator, denominator,
                            None, None, coverage, window.start, window.end, scope_node)

    lo, hi = wilson_interval(numerator, denominator, confidence=0.95)
    return CanaryRecall(numerator / denominator, "published", numerator, denominator,
                        lo, hi, coverage, window.start, window.end, scope_node)
```

**`unadjudicated` counts as a miss, and the reason is the metric trap itself.** A review that reached `completed` with a plant never adjudicated is a reviewer who ran out of time or attention on that candidate. That is exactly the behaviour D17 predicts and exactly what recall must capture. Only plants in reviews that never completed — `abandoned` or still `open` — are excluded from both numerator and denominator, and `coverage` exposes how many those are.

**The publication gate mirrors 06 §3's calibration gate, deliberately.** PdM publishes no `p_failure` below `calibration_population = 50` because "a predicted probability that cannot be calibrated must not be emitted merely because the field exists; omission is the honest signal" (03 §7.1). A recall estimate over eight plants has a Wilson interval spanning most of the unit interval and would be read as a number. Below 30 adjudicated plants the value is `null` with `status = "insufficient_canaries"`, and the interval is always published alongside the point estimate so nobody reads 0.83 as precision-grade.

At ~126 plants per month (06 §6), a monthly window clears the gate comfortably and a weekly window does not. Windows are therefore reported at 30 days rolling as the primary, with a 7-day secondary that will frequently show `insufficient_canaries` — and showing that honestly is better than a weekly figure with an interval nobody displays.

**Metrics are updated at review completion only.** A gauge that moved when a plant was *admitted* would let a reviewer with cluster metrics access infer that their current review contains a plant. All canary metrics are written in the completion transaction:

```
fathom_pma_canary_recall{scope_node,window}              gauge, null-gated
fathom_pma_canary_recall_ci_low / _ci_high{...}          gauge
fathom_pma_canary_coverage{scope_node,window}            gauge
fathom_pma_canary_plants_total{scope_node,outcome}       counter, incremented at completion
fathom_pma_canary_pool_remaining{scope_node}             gauge
fathom_pma_canary_density_realised{scope_node}           gauge
fathom_pma_precision{scope_node,window}                  gauge
fathom_pma_quality_divergence{scope_node,window}         gauge 0/1  (§5.5)
```

### 5.5 Surfacing: precision and recall cannot be served apart

06 §6's first countermeasure: "**Canary recall** is reported alongside precision on the same dashboard. A precision improvement accompanied by a canary-recall decline is flagged, not celebrated."

"On the same dashboard" is a request that a dashboard author can decline. This build makes it structural: **there is one operation, and its response model makes both fields required.**

```python
class QualityMetrics(FathomModel):
    """The joint quality report.  There is no operation that returns precision alone.

    D17's trap is that precision and review duration improve while recall collapses.  A
    caller that could fetch precision without recall could build the dashboard that shows
    the trap.  This model makes that impossible: `canary_recall` is a required member, and
    when it is gated the response carries `precision_interpretable = False` and a reason.
    """
    window: Window
    scope_node: str
    precision: float
    precision_denominator: int
    canary_recall: CanaryRecall                       # required member, never omitted
    end_to_end_recall: EndToEndRecall | None          # reference-sample missions only (§5.1)
    precision_interpretable: bool
    precision_caveat: str | None
    quality_divergence: bool                          # precision up AND canary recall down
    divergence_detail: str | None
    signature_agreement: float | None                 # confirmed plants whose signature
                                                      #   crosswalks to the truth lineage
    inter_reviewer_kappa: KappaReport | None           # §6.4
    severity_distribution: dict[str, float]           # the §3.3 consequence-bias monitor
    reviewer_rejection_rates: dict[str, RateReport]   # per-reviewer drift (06 §6)
    weighting_version: str
```

**Divergence detection.** `quality_divergence` is true when, over two consecutive 30-day windows, precision rose by more than a configured epsilon **and** the canary-recall point estimate fell by more than a configured epsilon with non-overlapping Wilson intervals. The interval condition matters: without it, ordinary sampling noise at n≈126 raises the flag monthly and the alarm is ignored within a quarter. When it fires, the response carries `divergence_detail` naming both movements, an alert fires (§5.8), and an Audit record is written.

**`signature_agreement` is reported and is not recall.** A confirmed plant whose assigned `signature_key` crosswalks (via `GET /crosswalk/pma-signatures`) to the plant's `truth_mode_lineage_id` agrees; one that does not is a *classification* error on a correct *detection*. Reporting them separately is what stops a taxonomy problem from being read as a reviewer problem. Because the crosswalk is many-to-many (12 §2.8), agreement is evaluated at lineage-set intersection, never by string equality of signature keys — and a `LIMIT 1` on the crosswalk here would silently deflate agreement (12 DO-NOT-2).

**Authorisation.** `GET /quality-metrics` is ABAC-restricted to a program quality role, not the reviewer role, and returns `403` with `urn:fathom:problem:pma:quality-metrics-forbidden` otherwise. A reviewer who could read their own canary outcomes could calibrate against them, which is the detectability failure again.

### 5.6 Admission control

06 §6: "**Admission control** | If unadjudicated candidates exceed 3× monthly throughput, candidate generation halts and an alarm raises | Prevents unbounded queue growth masquerading as capability."

#### 5.6.1 The exact trigger condition

```python
# services/pma/src/fathom_pma/services/admission.py
ADMISSION_MULTIPLIER      = 3.0      # 06 §6
CLEARANCE_MULTIPLIER      = 2.0      # hysteresis band  [ESTABLISHED HERE]
CLEARANCE_DWELL           = timedelta(hours=1)      # monotonic-measured
WARMUP_PERIOD             = timedelta(days=30)
PLANNED_MONTHLY_THROUGHPUT = 840     # 06 §6: 70 missions x 12 candidates


@dataclass(frozen=True)
class AdmissionState:
    engaged: bool
    backlog: int
    threshold: float
    throughput: int
    throughput_basis: Literal["observed", "planned_warmup"]
    scope_node: str
    engaged_since: datetime | None
    override: OverrideRecord | None


def evaluate(session, scope_node: str, now_mono: float) -> AdmissionState:
    backlog = session.scalar(
        """SELECT count(*) FROM pma.anomaly_candidate
            WHERE producer_node = :node
              AND state IN ('queued_unadmitted', 'admitted')""",
        {"node": scope_node},
    )

    if _node_uptime(scope_node) < WARMUP_PERIOD:
        throughput, basis = PLANNED_MONTHLY_THROUGHPUT, "planned_warmup"
    else:
        throughput, basis = _adjudications_trailing_30d(session, scope_node), "observed"

    threshold = ADMISSION_MULTIPLIER * throughput
    ...
```

Every term is defined, because each has a wrong reading that produces a broken gate:

| Term | Definition | The wrong reading it forecloses |
|---|---|---|
| **backlog** | Candidates in `queued_unadmitted` or `admitted` for this scope node. Includes canaries; excludes `held_on_antecedent`, `held_no_evidence`, and `grouped_duplicate` | Counting only admitted candidates hides the real queue: the events keep arriving whether or not reviews open |
| **throughput** | Distinct adjudications — confirmations plus rejections — with `recorded_at` in the trailing 30 days, for this scope node | Counting *reviews* rather than adjudications makes the threshold insensitive to a cap change |
| **inherited adjudications excluded** | A reconnect-time enterprise duplicate that inherits an edge adjudication (§7.5) is **not** counted | Counting them inflates throughput after every reconnect, raising the threshold precisely when the queue is largest |
| **warmup** | For the first 30 days of a scope node's life, throughput is 06 §6's planned 840/month | Observed throughput starts at zero, so a literal reading halts generation on day one, before anyone has reviewed anything |
| **zero throughput is not a special case** | After warmup, if observed throughput is 0 then the threshold is 0 and any backlog engages the gate | This is *correct*: nobody is reviewing, so nothing should be queuing. Adding a floor here would defeat the entire control — a permanent floor means a pipeline with no reviewers never halts and the dashboard never says so |
| **scope node** | `enterprise` or `edge:<asset_id>`, evaluated independently (§7.6) | A shore backlog must not halt a submarine's afloat reviews, and a hull's patrol backlog must not halt the fleet |
| **hysteresis** | Engaged at `backlog > 3 × throughput`; clears at `backlog ≤ 2 × throughput` sustained for one monotonic hour | Clearing at the engage threshold flaps: each admitted review changes the backlog by one and the gate oscillates, producing an alert storm that gets silenced |

#### 5.6.2 What "halts" means, operationally

This is the question the requirement leaves open, and answering it wrongly in either direction is a defect. **The detector does not stop. Review admission stops.**

| Layer | Behaviour when engaged | Why |
|---|---|---|
| **1. The detector ensemble keeps running; PMA's own afloat pre-screener keeps running too** | PMA does nothing to `telemetry`'s ensemble, and does not gate its own afloat pre-screener (§9.3) on enterprise admission control | The ensemble is `telemetry`'s (04 §3, 11 §1.2 — **not** PMA's, correcting this document's own earlier misattribution, §7.1); at the edge it is the ship's only candidate source. PMA has no authority over a sibling sub-application's workload, and 03 principle 3 forbids emitting an event to instruct one. The afloat pre-screener is PMA's own (11 §1.2), and it has no admission-control signal to gate on regardless — the enterprise queue it would gate against is unreachable across a disconnection |
| **2. `anomaly.detected` is still consumed and still persisted** | Candidates land in `queued_unadmitted` and stay there | Delivery is at-least-once and the inbox must apply (03 §5.2, D2). Dropping events to relieve a queue would lose detections permanently and silently — the precise class of failure the inbox rule exists to prevent |
| **3. No new `MissionReview` opens** | `mission.completed` creates the review in `deferred_admission_control`; **no `mission_review.opened` event is published** | This is the halt. It is the only lever that actually reduces the rate at which unadjudicated work accumulates, because it stops converting detections into reviewer-facing obligations |
| **4. Open reviews continue** | A claimed, open review is completable | Halting mid-review would waste materialised evidence and reviewer time, and would depress throughput — making the gate self-reinforcing |
| **5. `POST /proposals` is refused** | `429` with `urn:fathom:problem:pma:admission-control-engaged` and `Retry-After` | **[AMENDMENT — closes `41-pma-prescreener.md` §20 item 5.]** Proposals arrive over HTTP and can be refused with a retryable status; events cannot. Refusing them halts the enterprise pre-screener's contribution and, per 03 §8.3, gives its accountable owner a signal. **This is a target refusal with a valid, unexpired token — a routine, designed condition — and it is distinct from 31 §4.4's authority-lapse protocol, which is the response to an expired or revoked delegation.** The run stops and the refusal is recorded as a run outcome (`terminated_target_refused`, or `completed` with the cause carried in the audit record — `31-auth.md` §20 item 6 records which); it does not create a proposal after the refusal, and it is **not** the checkpoint-and-terminate sequence 31 §4.4 specifies for a lapsed delegation, because no authority event occurred here |
| **6. Re-review sampling pauses** | The 5% double-blind sample is suspended while engaged | Re-review consumes scarce adjudication capacity to measure agreement. When capacity is the binding constraint, spending it on measurement rather than on the backlog inverts the priority. The suspension is recorded so the agreement series has a documented gap rather than an unexplained one |
| **7. The alarm** | Prometheus alert on `fathom_pma_admission_control_engaged == 1`, an Audit record, a `/readyz` degraded entry, and a persistent operator banner sourced from `GET /admission-control` | Mirrors 11 §9.1's divergence-budget treatment: "never a silent failure, never a generic error, never a disabled button with no explanation" |
| **8. Nothing is discarded** | Every deferred review and queued candidate is retained in full and processed when the gate clears | 11 §9.1 rule 4, and D18's lesson that an enterprise pass which quietly discards candidates is the failure mode |

**Asymmetry between events and proposals, justified.** Layer 2 persists and layer 5 refuses. The distinction is transport, not preference: an event that has been delivered must be applied or the at-least-once contract is broken; an API call can be refused with a status its caller is required to handle. Both halves reduce accumulation — one by refusing new agent work, the other by refusing to convert detections into reviews.

**No new event type is introduced for the halt.** 03 §6 defines PMA's four events and 09 §8.2 requires `events/catalog.py`, the Helm values, and the 03 §6 catalog to be equal. Announcing admission control on a Kafka topic would require a catalog addition, which is document 03's to make — the same governance point 12 §3.4 raises as OD-7. The halt is therefore surfaced through metrics, `/readyz`, Audit, and a read operation, and §13 records the option of adding an event if operators want one.

### 5.7 The override

An override exists because a halt can be wrong — a bulk backfill, a detector misconfiguration, a scheduled surge with contracted reviewers.

```
POST /admission-control/override
  { scope_node, expires_at, justification, second_approver }
```

Requirements, all mandatory: a bounded `expires_at` (there is no permanent override, and the request is rejected without one); two distinct approvers holding at least the `planner` role from 03 §7.2.1's vocabulary; a free-text justification recorded to Audit with both identities; and continued alarming — an override suppresses the *gate*, never the *alert*. `fathom_pma_admission_control_override_active` is a separate gauge, so "we are running with the safety off" is visible rather than inferred from the absence of the halt.

### 5.8 Alerting rules shipped with the chart

```yaml
# services/pma/helm/templates/prometheusrule.yaml (values-gated)
- alert: PmaAdmissionControlEngaged
  expr: fathom_pma_admission_control_engaged == 1
  for: 5m
  labels: { severity: critical }
  annotations:
    summary: "PMA candidate admission halted on {{ $labels.scope_node }}"
    runbook: "docs/build/23-pma.md#56-admission-control"

- alert: PmaQualityDivergence            # the D17 alarm
  expr: fathom_pma_quality_divergence == 1
  for: 1h
  labels: { severity: critical }
  annotations:
    summary: "Precision rose while canary recall fell — D17 metric trap indication"

- alert: PmaCanaryRecallUnmeasurable
  expr: fathom_pma_canary_recall_status{status="insufficient_canaries"} == 1
  for: 45d
  labels: { severity: warning }
  annotations:
    summary: "Canary recall has been unpublishable for 45 days: recall is not being measured"

- alert: PmaCanaryPoolExhausted
  expr: fathom_pma_canary_pool_remaining < 4
  for: 15m
  labels: { severity: warning }
```

`PmaCanaryRecallUnmeasurable` deserves note: an unmeasurable recall is not a neutral state. It is the state D17 describes, reached by a different route — the metric is absent rather than falsely reassuring. A long stretch of `insufficient_canaries` must be as visible as a declining recall.

---

## 6. Reviewer qualification and label weighting

04 §8: "Label quality varies by reviewer. Recording who tagged what, with what qualification, permits label weighting and disagreement analysis, and is necessary for any defensible claim about training data quality." 06 §6's third countermeasure: "**Reviewer qualification weights labels**, and per-reviewer rejection rates are monitored for drift."

### 6.1 Qualification records and snapshots

```sql
CREATE TYPE pma.qualification_source AS ENUM
    ('system_of_record', 'supervisor_attested', 'self_declared');

CREATE TABLE pma.reviewer (
    reviewer_id     text PRIMARY KEY,        -- the OIDC subject. No local surrogate (03 principle 4)
    persona         text NOT NULL,           -- 'ships_force' | 'shore_analyst'  (06 §6)
    uic             text,
    billet          text,
    is_observer     boolean NOT NULL DEFAULT false,   -- 06 §4: findings completed ashore by a
                                                     -- NON-OBSERVER is flagged as such
    active          boolean NOT NULL DEFAULT true,
    classification  jsonb NOT NULL
);

CREATE TABLE pma.reviewer_qualification (
    qualification_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    reviewer_id       text NOT NULL REFERENCES pma.reviewer(reviewer_id),
    kind              text NOT NULL,        -- 'nec' | 'watchstation' | 'family_endorsement' | 'training'
    equipment_family  text,                 -- family_id from reference-data (12 §2.7); null = general
    reference         text NOT NULL,        -- the credential reference
    source            pma.qualification_source NOT NULL,
    valid_from        timestamptz NOT NULL,
    valid_until       timestamptz,
    recorded_by       text NOT NULL,
    classification    jsonb NOT NULL
);

-- An immutable snapshot, taken at adjudication, of what was true then.
CREATE TABLE pma.reviewer_qualification_snapshot (
    snapshot_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    reviewer_id       text NOT NULL,
    taken_at          timestamptz NOT NULL,
    persona           text NOT NULL,
    is_observer       boolean NOT NULL,
    tier              smallint NOT NULL,     -- 0..2, derived; see §6.2
    qualification_ids uuid[] NOT NULL,
    agreement_kappa   numeric(4,3),          -- shrunken; §6.4
    agreement_n       int,
    classification    jsonb NOT NULL
);
```

**Why a snapshot rather than a join.** A tag's weight must be re-derivable years later from what was true at adjudication, not from what is true at query time. A reviewer's qualifications lapse, are added, and are corrected; joining live would silently re-weight a two-year-old training set on the day a credential expired. This is the same bitemporal discipline D22 demands of feature definitions, applied to reviewer metadata.

### 6.2 The weighting function

```python
# services/pma/src/fathom_pma/services/weighting.py
WEIGHTING_VERSION = "pma-weighting-1.0.0"

QUAL_TIER_WEIGHT = {2: 1.00,   # endorsed for this equipment family
                    1: 0.85,   # generally qualified reviewer, no family endorsement
                    0: 0.65}   # observer / unqualified for this family
OBSERVER_PENALTY  = 0.90       # 06 §4: findings completed ashore by a non-observer
AGREEMENT_FLOOR   = 0.70       # w_agreement is never punitive beyond this
WEIGHT_FLOOR      = 0.30       # never zero: a zero-weight label is a deletion by arithmetic


def label_weight(snap: QualificationSnapshot, family_id: str | None) -> tuple[float, dict]:
    w_qual = QUAL_TIER_WEIGHT[snap.tier_for(family_id)]
    w_obs  = OBSERVER_PENALTY if snap.is_observer else 1.0
    w_agree = max(AGREEMENT_FLOOR, snap.agreement_kappa or 1.0)   # 1.0 when unmeasured
    w = max(WEIGHT_FLOOR, w_qual * w_obs * w_agree)
    return w, {"w_qual": w_qual, "w_observer": w_obs, "w_agreement": w_agree,
               "tier": snap.tier_for(family_id), "agreement_n": snap.agreement_n,
               "weighting_version": WEIGHTING_VERSION}
```

Four rules that make this defensible rather than arbitrary:

1. **Components are stored, not just the product** (`weight_components`, §2.4). A weighting-version change is then re-derivable over historical labels without re-deriving the qualification state, satisfying obligation 9.
2. **An unmeasured reviewer is not penalised.** `w_agreement` defaults to 1.0 when no re-review data exists. Penalising the unmeasured would make the first month of any new reviewer's labels systematically light, which is a bias, not a quality control.
3. **The weight has a floor and never reaches zero** (§2.4's constraint). Exclusion is expressed by flags with reasons.
4. **Dwell is not in the product.** See §6.3.

### 6.3 Dwell time is a flag, not a multiplier

The tempting design is a continuous dwell term: faster review, lower weight. It is wrong twice. Dwell is not competence — an endorsed maintainer recognising a familiar signature in twelve seconds is not producing a worse label than a novice taking ninety. And a continuous penalty is directly Goodhartable: reviewers learn to linger, dwell inflates, the metric improves, and nothing about label quality has changed.

Dwell is used as **one bounded anomaly detector**, aimed at exactly the behaviour D17 names:

```python
DWELL_REFLEX_FLOOR = 8.0   # seconds.  D17: the design's own targets implied "~10 seconds per
                           # candidate including evidence inspection — a reflex, not a review"

low_dwell = dwell_seconds < DWELL_REFLEX_FLOOR
```

A `low_dwell` label keeps its full weight, is retained in full, and is **excluded from the primary training extract** (§6.5) with the reason recorded. Per-reviewer `low_dwell` rates are reported in the quality metrics as drift indicators. A reviewer whose `low_dwell` rate rises is the leading indicator of the reject-to-finish behaviour, and it is visible before canary recall moves.

### 6.4 Double-blind re-review and inter-reviewer agreement

06 §6: "Double-blind re-review | 5% of completed reviews re-reviewed by a second reviewer | Inter-reviewer agreement and per-reviewer bias."

| Element | Mechanism |
|---|---|
| **Sampling** | On completion, with probability 0.05, a `re_review` `MissionReview` is created with `blinded_from_review_id` set. Sampling is deterministic from a seeded hash of `review_id` so the sample is reproducible and auditable, not re-rollable |
| **Identical inputs** | The re-review references the **same** `EvidencePackage` rows. This is why immutability matters operationally as well as evidentially (§2.6): if the package could change, disagreement would be confounded with a changed basis |
| **Blindness is enforced server-side** | The re-review's candidate query excludes the first pass's tags and rejections **inside the query**, never by filtering the response. This is the same rule 03 §7.3 imposes for classification — "post-filtering leaks the existence of records" — applied to blinding, where a filtered-out field in a response payload is exactly as visible to a determined client |
| **Reviewer exclusion** | The second reviewer is never the first, and never a reviewer who saw any plant in that set before |
| **Agreement** | Cohen's κ over the per-candidate confirm/reject decision, plus **lineage-resolved** signature agreement over pairs both confirmed: two different `signature_key` values that crosswalk to an intersecting `lineage_id` set count as agreement, and both the raw and lineage-resolved figures are reported |
| **Small-n honesty** | 5% of ~70 reviews per month is ~3.5 re-reviews per month, so a per-reviewer κ is unstable by construction. Per-reviewer κ is an **empirical-Bayes shrinkage** toward the pool mean, published with `agreement_n` and an interval, and the pool-level κ is the primary figure. Reporting a per-reviewer κ from four reviews as a scalar would be the same error as an ungated `p_failure` |
| **Canaries carry through** | The plants in a re-reviewed set are the same plants. They yield a second observation of the same plant, which is why the recall estimator clusters on `plant_id` (§5.4 note 3) |
| **Suspended under admission control** | §5.6.2 layer 6, with the gap recorded |

**Canary outcomes and reviewer weight — the tension, and the decision.** A reviewer who misses every plant is producing genuinely poor labels, so canary outcomes are relevant to weighting. But if reviewers receive per-reviewer canary feedback, canary detection becomes a thing to optimise, and 06 §6 is explicit about the consequence: "if reviewers learn to spot canaries, they stop measuring recall." The decision: **per-reviewer canary outcomes are an audited program-level quality signal, reviewed with a lag, and are never surfaced to the reviewer or to their supervisor as a performance figure during a measurement window.** They do not enter `label_weight` in `WEIGHTING_VERSION = 1.0.0`. `w_agreement`, which is derived from re-review and *is* legitimately shareable, carries the reviewer-quality signal instead. Recorded as an explicit judgment so a later version does not quietly reverse it.

### 6.5 The label export gate

D17's second countermeasure, made mechanical. `GET /labels/export` refuses to serve a training extract unless the request either includes the exhaustively-labelled reference-sample partition or explicitly acknowledges its absence:

```
GET /labels/export?window=&purpose=detector_training
                  &include_reference_sample=true
                  &reference_sample_ref=<13 §13.3 partition ref>
```

| Rule | Enforcement |
|---|---|
| A `detector_training` extract must include the reference sample, or carry `acknowledge_adjudication_only=true`, which is recorded to Audit with the caller's identity | `422` otherwise |
| Every extract carries `adjudication_only: bool` in its manifest | So a model card can state it |
| Rejections are partitioned on `is_negative_label` (§2.5) and the `false` partition is excluded from `detector_training` | The D34-analogue: training on "I could not tell" teaches silence |
| `low_dwell` labels are excluded from the primary partition and served separately | §6.3 |
| Every exported label carries `taxonomy_version`, `label_weight`, `weighting_version`, `reviewer_persona`, and the qualification snapshot id | I1 and obligation 9 |
| The export never includes canary status | I3. The evaluation partition that *does* is served under the evaluation role only, mirroring 13 §8.6's separate-credential control |

---

## 7. Edge deployment profile

11 §1.2 gives PMA an edge profile: "**Yes** — Afloat mission review and anomaly tagging; small edge pre-screener `[D18]`." 06 §4 scopes the demonstration: **one SSN, a simulated six-week disconnect, one at-sea corrective repair and two mission reviews while dark**, as "a physically separate deployment rather than a simulated queue."

### 7.1 What runs afloat, and what does not

| Component | Afloat? | Note |
|---|---|---|
| Review orchestrator, ranker, selector | **Yes** | The full pipeline of §3.1 |
| Evidence materialisation | **Yes**, against the **edge** Telemetry instance | The base URL is a Helm value; afloat it resolves to the on-hull Telemetry service. No shore round trip exists, so the six-week disconnect does not block materialisation |
| Tag and rejection creation | **Yes** | Append-only, `producer_node = edge:<asset_id>` |
| Canary injection and afloat recall | **Yes**, from a **pre-staged** plant pool | §7.4 |
| Admission control | **Yes**, scoped to the node | §7.6 |
| Taxonomy projection | **Yes**, from the pinned versioned package | 12 §4: "an edge deployment holds the published version as a versioned package and pins to it for the duration of a disconnection" |
| Proposal **creation** | Yes (queued) | Append-only; edge may create |
| Proposal **adjudication** | **No** | 03 §11: "adjudication server-authoritative and claim-gated." An edge-originated adjudication is `Reject`ed and returned as a request (11 §7.3) |
| Reviewer qualification **authoring** | **No** | A read-only snapshot is pre-staged. A reviewer cannot self-qualify at sea |
| Novel-signature **approval** | **No** | 12 §4: "a novel-signature proposal raised afloat queues in the outbox and adjudicates ashore" |
| **The detector ensemble** | Yes — but it is **`telemetry`'s**, not PMA's. **The small edge pre-screener is this service's own** | **[AMENDMENT — this row previously misattributed both to `telemetry`; corrected against 11 §1.2 itself.]** 11 §1.2's table gives the `telemetry` row *"edge-resident detector ensemble producing anomaly candidates `[D18]`"* and the `pma` row *"[a]float mission review and anomaly tagging; **small edge pre-screener** `[D18]`"* — two different rows, two different owners. 04 §8 and 21 §7 both agree with 11 §1.2 against this document's prior text. PMA consumes `anomaly.detected` with `origin: edge` from `telemetry`'s detectors **and** hosts the small, deterministic, no-model afloat pre-screener itself (§9.3) |

That last row is the D18 boundary and was the single most misread line in this design — misread in this document's own prior text, per the amendment above. 01 §12 and 06 §4 put the detector ensemble and a reduced pre-screener afloat; 11 §1.2 assigns the **ensemble** to `telemetry` and the **pre-screener** to `pma`. PMA's afloat obligation is therefore twofold: host the small, deterministic pre-screener itself, **and** have a **working review workflow that consumes whatever candidates arrive** from it (and from `telemetry`'s ensemble), including none — a review with an empty eligible set is created, recorded, and closed as such, never presented as an authoring surface (04 §8).

### 7.2 Producer node identity

03 §5.4 fixes the envelope vocabulary: `producer_node` is `"enterprise" | "edge:<asset_id>"`, and it is "required because a sub-application with an edge profile runs as two independent instances of the SAME slug, each minting its own `monotonic_seq` — without this field their sequences collide and the dedup key silently drops an event."

| Field | Enterprise | Edge |
|---|---|---|
| Envelope `producer_node` (03 §5.4) | `enterprise` | `edge:6f2c…` (the asset UUID) |
| Library `producer_node_id` / `clock.hlc.node_id` (11 §4.2) | `pma@ashore-1` | `pma@ssn796` |
| Consumer group | `fathom-pma-v1` | `fathom-pma-v1-edge-<asset>` |
| Dedup and ordering key | `(producer_slug, producer_node_id, monotonic_seq)` — the three-part key of 11 §4.2, never two parts | same |

The sequence never resets, and `producer_node_id` is never reused for a different deployment (11 §4.3). A restored edge database requires a new node id.

### 7.3 Conflict policies — all PMA aggregates declared

11 §7.2's registry is complete-or-fail: it enumerates every owned aggregate at startup and fails if one is neither declared nor explicitly defaulted (C20). PMA's declaration:

```python
# services/pma/src/fathom_pma/events/policies.py
policies = ConflictPolicyRegistry.declare(
    service="pma",
    policies=[
        EdgeGeneratable(                       # 03 §11: "Anomaly candidates | Edge-generatable"
            aggregate="anomaly_candidate",
            divergence_budget=DivergenceBudget(max_disconnection=timedelta(days=90)),
        ),
        AppendOnlyImmutable(                   # 03 §11: "Anomaly tags | Append-only; never
            aggregate="anomaly_tag",           #   overwritten or deleted; supersession recorded"
            divergence_budget=DivergenceBudget(max_disconnection=timedelta(days=90)),
        ),
        AppendOnlyImmutable(
            aggregate="tag_rejection",
            divergence_budget=DivergenceBudget(max_disconnection=timedelta(days=90)),
        ),
        AppendOnlyServerAdjudicated(           # 03 §11: "Proposals | Append-only; adjudication
            aggregate="proposal",              #   server-authoritative and claim-gated"
        ),
        EdgeAuthoritativeThenEnterprise(       # NOT in 03 §11's table; declared here, §7.3 note
            aggregate="mission_review",
            divergence_budget=DivergenceBudget(max_disconnection=timedelta(days=90)),
        ),
        AppendOnlyDedup(                       # immutable objects; dedup on content_hash
            aggregate="evidence_package",
            divergence_budget=DivergenceBudget(max_disconnection=timedelta(days=90)),
        ),
        EnterpriseAuthoritativeNotEdgeWritable(aggregate="reviewer", default=True),
        EnterpriseAuthoritativeNotEdgeWritable(aggregate="reviewer_qualification", default=True),
        EnterpriseAuthoritativeNotEdgeWritable(aggregate="canary_plant", default=True),
    ],
)
```

**`mission_review` is not in 03 §11's table, so the default would apply — and the default would break the design.** 03 §11's default rule is "enterprise-authoritative and not edge-writable," which would forbid a ship from creating a review afloat and would restore D18 by a different route: candidates would exist, and there would be no review to put them in. PMA therefore declares it explicitly, choosing the policy 03 §11 gives to **mission records** — `EDGE_AUTHORITATIVE_THEN_ENTERPRISE` — for the same reason: the ship knows the review happened and may be the only witness, and after the first successful reconciliation authority moves ashore so a re-review or reassignment can be run from there. 11 §7.3 requires the transition to be "recorded on the record itself so authority is never ambiguous mid-flight." Declaring a policy for an aggregate 03 §11 does not enumerate is exactly what 03 §11 anticipates ("Phase 3 enumerates exceptions per sub-application") and what C20 exists to force.

**`canary_plant` is enterprise-authoritative and pre-staged.** The edge cannot mint plants — it has no ground truth — and it must not be able to, because a locally-mintable plant is a locally-forgeable recall figure.

### 7.4 Divergence budgets, and the constraint that binds them

11 §9.1's binding constraint, stated for the demonstration: "**the maintenance-action-record and anomaly-tag budgets must exceed the planned patrol length**, or the demonstration's own scenario breaches the budget it is meant to satisfy — the ship goes read-only for maintenance recording halfway through the patrol, and D8 returns wearing a compliance badge."

PMA declares **90 days** for every edge-writable aggregate, against a scripted 42-day disconnect (13 §15.1). Three of them are less obvious than `anomaly_tag` and each would break the workflow if set short:

- `evidence_package` — a breach refuses writes to that aggregate, so evidence cannot be materialised, so no review can open. A short evidence budget silently halts afloat review.
- `mission_review` — a breach means no review can be created at all.
- `anomaly_candidate` — a breach means arriving detections cannot be persisted, which would drop them.

Breach behaviour is the library's, unchanged: `423 Locked` with problem details, a per-aggregate operator banner, other aggregates unaffected, and nothing already recorded discarded (11 §9.1).

**The pre-staged plant pool.** A patrol needs plants provisioned *before* disconnect, because the edge cannot ask shore for them. Sizing for the demonstration: 2 reviews × 12 candidates × 0.15 ≈ 4 expected plants; **12 are staged** to absorb the variance of the binomial draw and the unusability of plants whose detection the edge never produces. The pool is stored in the edge database like every other PMA aggregate and therefore inherits 11 §10.1's encryption at rest — which matters more here than ashore, since the outbox and its neighbours sit "on a hull that may be boarded, salvaged, or lost." Pool exhaustion afloat degrades `/readyz` and alarms; it never silently stops planting, because silently not planting means silently not measuring recall.

### 7.5 Reconnect and reconciliation

The coordinator (11 §9.2, §9.3) is active on the demonstration hull and its shore counterpart. PMA's obligations at reconnect:

| Obligation | Behaviour |
|---|---|
| **Enterprise adds candidates; it never replaces the edge set** | 03 §11 and 11 §7.3's `EDGE_GENERATABLE`: "Enterprise **adds** on reconnect; it never replaces or prunes the edge set." 13 §15.2 case 3 generates overlapping enterprise candidates deliberately, plus "candidates the edge found and the enterprise did not, which must **survive** reconnection — the failure mode being an enterprise recomputation that quietly discards them" |
| **Overlaps become candidate groups** | Linked on `(installed_item_id, window)` with both origins preserved, never merged away (§3.4) |
| **An already-adjudicated edge candidate is not re-presented** | The enterprise duplicate joins the group and records an `inherited_adjudication` referencing the edge tag or rejection. Re-presenting it would spend scarce capacity re-deciding a decided question |
| **Inherited adjudications are excluded from throughput and from canary denominators** | §5.6.1. Counting them would inflate the admission threshold at exactly the moment the backlog is largest, and would double-count a plant outcome |
| **Tags append; nothing is overwritten** | A shore reviewer who disagrees creates a **new** tag with `supersedes_tag_id`; both survive with both reviewers and both timestamps (11 §7.3 `APPEND_ONLY_IMMUTABLE`) |
| **Afloat canary outcomes reconcile** | Plant outcomes recorded afloat arrive as part of the tag/rejection stream and the `mission_review.completed` payload; shore recomputes recall over the union, scoped per node **and** fleet-wide |
| **Clock discipline** | A backward wall-clock step fires at reconnect by mandate (V-260520). Ordering is `(producer, producer_node, monotonic_seq)` or HLC, never `source_time`. `dispersion_ms` grown over six weeks exceeds the inter-write interval, which "forbids timestamp arbitration entirely and forces causal-only ordering" (13 §15.3) |
| **Out-of-order and duplicate delivery** | Idempotent on `event_id` via the inbox's `processed_at` predicate; dedup on the three-part key |
| **Priority** | PMA's aggregates are drain class 1 — "maintenance action records, anomaly tags, mission records… the label stream" (11 §9.3) — ahead of bulk telemetry, which is class 4 and interruptible. Six weeks of burst telemetry must not starve the label stream |
| **Provisional identity** | Tags authored afloat against a provisional `installed_item_id` resolve through the alias table on confirmation or supersession (11 §8.4). No tag is rewritten |
| **Not a replay** | Edge records drain as **live facts arriving late**, never with `X-Backfill` and never `replay: true` (11 §9.3): "a six-week-old maintenance action from a submarine is a first emission of a real fact" |

### 7.6 Per-node admission control

Admission control is evaluated per scope node (§5.6.1), and this is a correctness requirement rather than a convenience — the same reasoning 11 §9.1 rule 3 applies to divergence budgets ("a telemetry breach must not stop maintenance action recording — that would reintroduce D8 by a different route").

- The edge evaluates its own backlog against its own reviewer's throughput. A shore backlog can never halt afloat review.
- The edge's warmup throughput is sized to the patrol rather than to 06 §6's fleet monthly figure: two reviews at cap 12 is 24 candidates, so a fleet-scaled threshold would never engage afloat and a fleet-scaled *floor* would be meaningless. The edge value is a Helm value with the patrol plan as its basis.
- The demonstration's scripted scenario must not engage the edge gate. That is an assertion in the edge test suite (§9.6), not an assumption.

---

## 8. Events published and consumed

### 8.1 Catalog conformance

09 §8.2 requires `src/fathom_pma/events/catalog.py` `PUBLISHES`/`CONSUMES` to equal `helm/values.yaml` `events.publishes`/`events.consumes` to equal document 03 §6's rows for this slug, reconciled by `tools/check_event_catalog.py` and `tools/check_service_events.py` in CI job 6. No wildcards (C38).

```python
# services/pma/src/fathom_pma/events/catalog.py
PUBLISHES: frozenset[str] = frozenset({
    "fathom.pma.mission_review.opened",
    "fathom.pma.mission_review.completed",
    "fathom.pma.anomaly_tag.confirmed",
    "fathom.pma.anomaly_tag.rejected",
    "fathom.pma.proposal.created",
    "fathom.pma.proposal.adjudicated",
    "fathom.pma.proposal.expired",
})

CONSUMES: frozenset[str] = frozenset({
    "fathom.telemetry.mission.completed",
    "fathom.telemetry.anomaly.detected",
    "fathom.telemetry.telemetry_batch.ingested",
    "fathom.registry.configuration_baseline.changed",  # [AMENDMENT — corrected.] Was the
    # doc-20 §3.2 catalog LABEL, not the wire event_type — 20 §3.2 is explicit that "the
    # catalog label is a cross-reference only and never appears on a wire." EVENT_HANDLERS
    # keyed on the old string never matched, so epoch fencing and candidate-admission
    # gating never fired against a baseline change — a silent D2-class failure with no
    # error. 27-fleet-status.md, 24-scheduling.md, and 09 all use the correct wire name.
    "fathom.maintenance.maintenance_action.recorded",
    "fathom.auth.agent_run.v1",  # [AMENDMENT] agent_run.completed only, filtered to
    # agent_id='pma-prescreener' — closes the pre-screen quiesce window (41-pma-prescreener.md
    # §2.3) without a direct call to the agent, which 03 principle 2 forbids. Correlated to
    # the waiting review via mission_id in the event's subjects (31-auth.md §11.1).
})
# NOT subscribed, deliberately: fathom.reference-data.taxonomy.* — those topics have no
# document 03 §6 catalog rows (12 §3.4, OD-7), so subscribing would fail CI job 6.  The
# projection cache is refreshed by conditional polling instead (§4.2).
```

Each consumed type is confirmed present in 03 §6 with `pma` listed as a consumer: `mission.completed` (Telemetry), `anomaly.detected` (Telemetry), `telemetry.batch_ingested` (Telemetry), `configuration.baseline_changed` (Registry), and `maintenance_action.recorded` (Scheduling — the row lists `pdm`, `failure-intel`, `registry`, `supply`, **`pma`**, `design-advisory`).

### 8.2 Topics, keys, and retention

| Topic | Aggregate | Partition key | Compaction | Retention |
|---|---|---|---|---|
| `fathom.pma.mission_review.v1` | `mission_review` | `asset_id` | **None** | 30 days (domain events) |
| `fathom.pma.anomaly_tag.v1` | `anomaly_tag`, `tag_rejection` | `asset_id` | **None** | 30 days |
| `fathom.pma.proposal.v1` | `proposal` | `asset_id` | **None** | 30 days |

Three decisions:

**Partition key is `asset_id`, including for mission-scoped events.** 03 §5.1 keys asset-scoped events on `asset_id` "guaranteeing per-asset ordering within a topic — which is the only ordering guarantee the design relies on." `mission_review.*` carries `scope = mission` and therefore `subject.mission_id` only (03 §5.4: exactly one scope identifier matching `scope`), but the partition key is taken from the payload's `asset_id`. Keying on `mission_id` would scatter a hull's review history across partitions and buy no useful ordering, since a mission is a bounded event with at most a few review records.

**No PMA topic is compacted.** Every PMA aggregate is append-only history whose value is the history: compaction would discard superseded tags, which 03 §11 forbids deleting, and would discard rejections, which are negative labels. Were compaction ever introduced, the compaction key would be the **aggregate** key — `review_id`, `tag_id`, `proposal_id` — never the partition key, since "compacting on `asset_id` would collapse a hull's entire prediction history to a single record" (03 §5.1, D5) and would do exactly the same to a hull's tag history.

**Rebuild is via `changed_since`, not the bus.** `GET /tags?changed_since=`, `GET /rejections?changed_since=`, `GET /reviews?changed_since=` exist for that purpose (obligation 5, D5).

### 8.3 Envelope construction

Every event is emitted through `packages/py-sync`'s `emit()` inside the caller's transaction (11 §2.3). No PMA module constructs an envelope, calls a Kafka producer, or inserts into `outbox` directly — each is a CI lint failure (11 §2.3).

```python
# services/pma/src/fathom_pma/events/publishers.py

async def publish_tag_confirmed(uow: UnitOfWork, outbox: OutboxWriter, tag: AnomalyTag) -> None:
    outbox.emit(
        uow,
        event_type="fathom.pma.anomaly_tag.confirmed",
        aggregate="anomaly_tag",
        aggregate_id=str(tag.tag_id),
        scope=Scope.INSTALLED_ITEM,                       # 03 §5.4 scope vocabulary
        subject=Subject(installed_item_id=tag.installed_item_id),   # exactly one [C11]
        payload=AnomalyTagConfirmed.from_domain(tag),     # packages/canonical-schemas
        classification=tag.classification,                # inherited_from = union of inputs
        baseline_epoch=tag.baseline_epoch,
        causation_id=tag.source_detection_event_id,        # the anomaly.detected it answers
    )
```

The envelope the library fills (11 §5, 03 §5.4) carries `event_id`, `event_type`, `event_version`, `occurred_at`, `recorded_at`, `producer` (`pma` + version), **`producer_node`** (`enterprise` | `edge:<asset_id>`), `correlation_id`, `causation_id`, `scope`, `subject`, `baseline_epoch`, `classification`, `replay`, and the full `clock` block including `sync_quality`'s six sub-fields.

Three PMA-specific envelope obligations:

1. **`hindsight = true` on tag events.** 11 §5: `emit()` stamps the marker on "aggregates declared hindsight-authored (confirmed anomaly tags, in particular) so feature pipelines cannot silently use `occurred_at`" `[D22]`. PMA declares `anomaly_tag` and `tag_rejection` hindsight-authored.
2. **`occurred_at` is mission time; `recorded_at` is review time.** They diverge by weeks for a returning submarine, which 03 §5.4 gives as the motivating example: "a mission anomaly occurred at sea and was recorded when the ship reconnected."
3. **`causation_id` points at the `anomaly.detected` event the tag answers**, giving the antecedent chain a consumer can walk.

### 8.4 The four PMA events, exactly

#### `mission_review.opened` → `notification`

`scope = mission`, `subject.mission_id`. Payload per 03 §6 — "mission_id, asset, candidate set, assigned reviewer, candidate origin":

```
{ mission_id, asset_id, review_id, review_kind,
  candidate_ids[], candidate_count, candidate_cap,
  assigned_reviewer_id, reviewer_persona,
  candidate_origin: { enterprise: n, edge: m },       # DETECTION origin (03 §6), not canary
  taxonomy_version_pin, ranker_version,
  baseline_id, baseline_epoch, producer_node }
```

**No canary information appears in this event, in any form.** `candidate_origin` is the `enterprise`/`edge` detection split. Notification consumes this event and Kafka is broadly readable in-cluster; a canary count here would be an oracle available before adjudication, which is I3's whole subject. Evidence is referenced by candidate id, never inlined (D27).

#### `anomaly_tag.confirmed` → `failure-intel`, `pdm`

`scope = installed_item`, `subject.installed_item_id`. Payload per 03 §6 — "installed item, window, taxonomy classification, reviewer, qualification, evidence":

```
{ tag_id, installed_item_id, position_id, asset_id, mission_id,
  window_start, window_end,
  signature_key, taxonomy_version, is_novel_escape, resolved_lineage_ids[],
  reviewer_id, reviewer_persona, qualification_tier, qualification_snapshot_id,
  label_weight, weight_components, weighting_version, low_dwell,
  evidence_package_id, evidence_content_hash,
  supersedes_tag_id?, source_proposal_id?, proposing_agent_id?, proposing_agent_version?,
  baseline_id, baseline_epoch, hindsight: true, producer_node }
```

`label_weight` travels with the label because the consumers that train on it must weight it, and asking them to fetch it separately guarantees some of them will not.

#### `anomaly_tag.rejected` → `failure-intel`, `audit`

`scope = installed_item`. Payload per 03 §6 — "candidate reference, rejection reason, reviewer":

```
{ rejection_id, candidate_id, installed_item_id, position_id, asset_id, mission_id,
  window_start, window_end,
  reason_class, is_negative_label, duplicate_of_candidate_id?,
  reviewer_id, qualification_snapshot_id, label_weight, weighting_version, low_dwell,
  evidence_package_id, taxonomy_version, baseline_epoch, producer_node }
```

`is_negative_label` is on the wire precisely so a consumer cannot mistake a `insufficient_evidence` rejection for evidence of health (§2.5).

#### `mission_review.completed` → `fleet-status`, `audit`

`scope = mission`. Payload per 03 §6 — "mission_id, tag counts, review duration, reviewer, canary outcomes":

```
{ mission_id, asset_id, review_id, review_kind,
  confirmed_count, rejected_count, unadjudicated_count,
  duration_seconds,                                   # MONOTONIC-measured
  candidate_dwell_p50, candidate_dwell_p95, low_dwell_count,
  reviewer_id, reviewer_persona,
  canary_outcomes: { planted: n, confirmed: c, rejected: r, unadjudicated: u },
  taxonomy_version_pin, producer_node }
```

**This is the only PMA event that carries canary information, and it carries aggregate counts only.** Publishing per-candidate canary flags — even after adjudication — would let anyone with topic access accumulate a fingerprint library of which windows are plants, which destroys future measurement on the same corpus. Counts support fleet-level recall aggregation and support nothing else. Publication after completion is safe because the reviewer's decisions are final and immutable by then.

### 8.5 Proposal events

Per 03 §6's proposal convention, on `fathom.pma.proposal.v1`, using the §7.2 schema, "permitting the gateway to build a unified adjudication queue from a topic pattern without any sub-application knowing the queue exists":

| Event | Consumers |
|---|---|
| `proposal.created` | `gateway`, `notification` |
| `proposal.adjudicated` | `audit`, and PMA itself |
| `proposal.expired` | `gateway`, `audit` |

`proposal.adjudicated` for an approved `anomaly_tag` is published in the **same transaction** as the resulting `AnomalyTag` and its `anomaly_tag.confirmed` event. Two events, one state change, one transaction — otherwise a crash between them produces a tag with no adjudication record or an adjudication with no tag.

**Agents are never direct topic consumers** (C19, 03 §6). `anomaly_tag.*` reaches agent evaluation through `audit`, which exports to Domino's Experiment Manager. PMA does not publish to Domino and does not know it exists.

---

## 9. Testing

Four tiers per 09 §4.7 — `unit`, `integration`, `contract`, `conformance` — none interchangeable. Test IDs below are stable suite names.

### 9.1 Conformance suite wiring

The shared suite lives at `packages/contracts/conformance/pma/` (path fixed by 03 §10). The service collects it unmodified and supplies exactly four fixtures. **No shared conformance test may be edited, skipped, xfailed, or subclassed** (09 §4.7).

```python
# services/pma/tests/conformance/test_suite.py
"""Collects the shared conformance suite for this slug into this service's test run.

The suite lives in packages/contracts/conformance/pma/ (path fixed by document 03 §10).
Do not add, skip, or modify tests here.  Fixtures are in conftest.py.
"""
from fathom_contracts.conformance.pma import *          # noqa: F401,F403
```

`tests/conformance/conftest.py` provides `conformance_target`, `event_tap`, `fault_injector`, and `reference_dataset` exactly as 09 §4.7 specifies. `reference_dataset` loads the synthetic Navy dataset from `data/synthetic` — including, for PMA, a plant pool, a set of label-corruption cases, and the reference-sample missions, since deterministic runs of §9.3 and §9.5 depend on them.

**Consumer-driven tests PMA contributes** into each producer's suite (03 §10, and 09 §4.7's note that a declared consumer contributing no test has an unmet DoD item):

| Contributed into | Test | Asserts |
|---|---|---|
| `conformance/telemetry/consumers/pma/` | `pma-consumes-mission-completed` | `mission.completed` carries `mission_id`, `asset_id`, period, and a data-completeness assessment sufficient to gate review creation |
| | `pma-consumes-anomaly-detected` | `anomaly.detected` carries installed item, window, `detector_version`, score, channels implicated, **and `origin` in `{enterprise, edge}`** — the field D18's resolution depends on |
| | `pma-requires-replay-api` | The five materialisation operations of §2.6 exist, accept `as_of` **and** `as_known_at` where declared, and return a completeness record distinguishing "no fault observed" from "not observed" |
| `conformance/registry/consumers/pma/` | `pma-consumes-baseline-changed` | `baseline_epoch` is present and monotonic per asset, so epoch fencing is implementable |
| `conformance/maintenance/consumers/pma/` | `pma-consumes-maintenance-action` | The record carries findings coding **as a candidate set**, parts consumed, corrective/preventive determination, failure timing, and `triggering_driver` — and that `installed_item_id` and `position_id` are distinct fields `[C10]` |
| `conformance/reference-data/consumers/pma/` | `tax-proj-pma` (12 §8.1, contributed by PMA) | `GET /taxonomy/projections/pma` returns a non-empty coarsened set per `equipment_class` with exactly one `is_novel_escape` row; every signature resolves to ≥1 entry via `GET /crosswalk/pma-signatures`; the response echoes `taxonomy_version` |

### 9.2 Contract and event tests

Standard per 09 §4.7 and 03 §10, with PMA specifics: spec-drift, annotation coverage, RFC 9457 on every declared problem type, idempotency on all `state-changing` and `proposal-only` operations, `If-Match` on proposal adjudication and review claim, `changed_since` over tags/rejections/reviews, cursor pagination, and event tests asserting envelope completeness, the `asset_id` partition key, within-partition ordering, and the `hindsight` marker on tag events. Fault-injection tests interrupt tag creation and review completion mid-operation and assert **no state change without its event** (obligation 2) — the substitutable form of the outbox obligation (D24).

### 9.3 Recall measurement — the specific test D17 requires

```python
# packages/contracts/conformance/pma/test_recall.py

def test_pma_recall_arithmetic(target, reference_dataset):
    """pma-canary-recall-arithmetic.

    Plant a known set, script known reviewer behaviour, assert the computed recall is
    exactly the arithmetic the definition requires — including the Wilson interval, the
    coverage figure, and the clustering rule.  This is the test that proves the metric
    closing D17 actually computes what it claims.
    """
    # 40 plants across 20 reviews at cap 12, all reviews completed.
    plants = reference_dataset.plant_pool(n=40)
    reviews = target.run_reviews(count=20, plants=plants)

    # Scripted reviewer: confirm exactly 26 plants, reject 11, leave 3 unadjudicated.
    outcome = target.script_adjudication(reviews, confirm_plants=26, reject_plants=11,
                                         leave_unadjudicated=3)
    assert outcome.plants_adjudicated == 40          # unadjudicated-in-a-completed-review counts

    m = target.get("/quality-metrics?window=30d&scope_node=enterprise").json()
    r = m["canary_recall"]

    assert r["status"] == "published"                 # 40 >= RECALL_MIN_PLANTS
    assert r["numerator"] == 26
    assert r["denominator"] == 40                     # 11 rejected + 3 unadjudicated are MISSES
    assert r["value"] == pytest.approx(26 / 40)
    lo, hi = wilson_interval(26, 40, 0.95)
    assert (r["ci_low"], r["ci_high"]) == pytest.approx((lo, hi))
    assert r["coverage"] == pytest.approx(1.0)

    # Precision cannot be served without recall.
    assert "precision" in m and "canary_recall" in m
    assert m["precision_interpretable"] is True


def test_pma_recall_gate(target, reference_dataset):
    """pma-canary-recall-gate.  Below 30 adjudicated plants the value is null, not a number."""
    target.run_reviews(count=5, plants=reference_dataset.plant_pool(n=8))
    r = target.get("/quality-metrics?window=7d&scope_node=enterprise").json()["canary_recall"]
    assert r["value"] is None
    assert r["status"] == "insufficient_canaries"
    assert r["denominator"] == 8
    # and precision is explicitly marked uninterpretable rather than shown bare
    m = target.get("/quality-metrics?window=7d&scope_node=enterprise").json()
    assert m["precision_interpretable"] is False and m["precision_caveat"]


def test_pma_recall_excludes_abandoned(target, reference_dataset):
    """Plants in an abandoned or still-open review are in NEITHER numerator nor denominator,
    and `coverage` exposes them."""


def test_pma_recall_clusters_on_plant(target, reference_dataset):
    """pma-canary-recall-clustering.  A plant appearing in a primary review and again in a
    double-blind re-review contributes ONE observation; the interval matches the clustered
    n, not the doubled n."""


def test_pma_quality_divergence_flag(target, reference_dataset):
    """pma-quality-divergence.  Two consecutive windows in which precision rises and canary
    recall falls with non-overlapping intervals set quality_divergence = true and produce an
    audit record.  Overlapping intervals do NOT set it (noise must not raise the alarm)."""
```

### 9.4 Canary indistinguishability and non-leakage

| Test | Asserts |
|---|---|
| `pma-canary-schema-clean` | `AnomalyCandidateView` and every reviewer-reachable response model contain **no** `origin`, `canary_*`, `plant_*`, or `truth_*` member. A schema walk over the committed `openapi.json`, so the check holds against what a substitute and the UI actually read |
| `pma-canary-no-plant-join` | A static check over `repositories/candidates.py`: no reviewer-facing method references `pma.canary_plant`. Fails on the SQL, not on the intent |
| `pma-canary-no-leak-fuzz` | Every read operation, called with a reviewer principal across the reference dataset, is asserted to contain no plant id, no `truth_ref`, and no `origin` value in any response body — including error bodies and `include=` expansions |
| `pma-canary-abac` | A reviewer principal receives `403` on `GET /quality-metrics` and on every plant-bearing operation; the evaluation role receives `200` |
| `pma-canary-indistinguishable` | Two-sample tests over every field of the reviewer-facing projection, canary versus non-canary, within mission type and rank stratum. **Failing to reject is the passing condition**, and the test reports its power: a low-power failure-to-reject is marked **unproven, not passed** (13 §13.2's rule, adopted verbatim) |
| `pma-canary-rank-stratum-matched` | Over ≥200 injections, the canary rank-stratum histogram is statistically indistinguishable from the non-canary histogram (§5.3.2) |
| `pma-canary-density` | Realised density converges to 0.15 ± tolerance over the reference window; per-review counts are **not** constant; some reviews contain zero plants; no review exceeds `CANARY_MAX_PER_REVIEW`; the controller stays inside `CANARY_P_BOUNDS` |
| `pma-canary-no-synthesis` | Every plant-bound candidate has a non-null `source_event_id` resolving to a real `anomaly.detected`, and its `detector_version`/`detector_score` equal that event's values byte-for-byte. **There is no code path that writes a detector attribution PMA invented** (13 §13.1) |
| `pma-canary-metrics-timing` | No canary metric or audit record moves between injection and review completion (§5.4) |
| `pma-canary-displacement-safe` | A displaced non-canary candidate returns to `queued_unadmitted` and is eligible for a later review — never dropped |

### 9.5 Label-corruption tests, from the generator's stage 9

13 §9.10 emits eight corruption classes. Each gets a test asserting PMA's behaviour under it, because "the review workflow must handle exactly the corrupted, ambiguous inputs the generator produces" is a contract on this service, not a hope.

| Generator corruption (13 §9.10) | Test | Required PMA behaviour |
|---|---|---|
| **Wrong findings code** | `pma-corrupt-findings-code` | The maintenance context is displayed as asserted; the reviewer's signature is not pre-filled, defaulted, or nudged from it; the resulting disagreement is retained and visible (12 §9.3) |
| **Wrong-item attribution** | `pma-corrupt-wrong-item` | The tag attaches to the candidate's `installed_item_id`, never to the maintenance record's. `position_id` is displayed alongside so the mismatch is visible. **No tag ever moves to a different installed item because of a maintenance record** `[C10, D9]` |
| **Date rounding** | `pma-corrupt-date-rounding` | Corroboration matching uses an interval, not equality; a record rounded to end-of-shift still corroborates a window earlier that day; lead-time figures downstream are not computed by PMA |
| **Missing parts record** | `pma-corrupt-missing-parts` | Absence renders as absence, never as zero |
| **Narrative–code inconsistency** | `pma-corrupt-narrative-conflict` | Both are shown; narrative text is carried as untrusted content and cannot alter a default (03 §9) |
| **Duplicate 2-Kilos** | `pma-corrupt-duplicate-2k` | The read model deduplicates for display and does not inflate a corroboration count; the duplicate is retained |
| **Corrective/preventive misclassification** | `pma-corrupt-corrective-preventive` | PMA does not infer a signature from the determination; a misclassified record does not change any tag |
| **Missing `triggering_driver`** | `pma-corrupt-missing-driver` | Missingness is represented as missing, never defaulted to `pms_periodicity` |
| **3-M ambiguity** | `pma-corrupt-3m-set-valued` | A findings tuple resolving to ≥2 candidate modes renders **all** of them with confidences. Fails on any scalar collapse or `LIMIT 1` (12 DO-NOT-2, `tax-xw-3m-cardinality`) |

Two cross-cutting assertions over the same fixtures: an evidence package materialised over a window with a **stuck-at-value** channel (13 §9.6) presents the channel as a sensor fault rather than as degradation; and a candidate whose window falls in a **structural gap** (subsurface channels delivering nothing until reconnect) is held with `held_no_evidence` rather than shown with an empty plot.

### 9.6 The edge disconnect/reconnect test

Consumes the generator's scenario fixtures directly — `data/synthetic/scenarios/edge/*.yaml`, primarily **case 3, edge-resident candidate generation** (13 §15.2), with the cross-cutting mechanics of 13 §15.3 layered on. 13 §15.4 fixes the protocol: "the edge deployment's test suite loads a scenario, replays its timeline against a network-partitioned edge instance, reconnects, and asserts against `expected_post_reconciliation`." And the rule that keeps the golden files honest: "a scenario whose golden file must be regenerated to make a test pass is a **contract change** and requires the same review as an edit to 03 §11."

`pma-edge-six-week`, against `edge-ssn-6wk-*` at t=0d disconnect → t=42d reconnect:

| Assertion | Source |
|---|---|
| Two mission reviews are created, opened, and completed **while dark**, with evidence materialised from the on-hull Telemetry instance | 06 §4 demo scope |
| Tags authored afloat carry `producer_node = edge:<asset_id>` and a monotonic sequence independent of the enterprise instance | 03 §5.4, 11 §4.2 |
| Canaries are injected afloat from the pre-staged pool; afloat canary recall is computed on the hull and appears in `mission_review.completed`'s aggregate counts | §7.4, §8.4 |
| Enterprise candidates added at reconnect **add**, never replace; edge-only candidates survive | 03 §11, 13 §15.2 case 3 |
| Overlapping candidates form groups with both origins preserved; already-adjudicated edge candidates are not re-presented | §3.4, §7.5 |
| Inherited adjudications are **excluded** from throughput and from canary denominators | §5.6.1, §7.5 |
| A shore reviewer disagreeing produces a **new** tag with `supersedes_tag_id`; the afloat tag survives unmodified; an attempted `UPDATE` raises at the trigger | §2.4, 11 §7.3 |
| The backward clock step at reconnect (`step_occurred = true`, inverted `source_time` on two writes from one process) changes no ordering outcome | 13 §15.3, 03 §5.4 |
| `dispersion_ms` grown across six weeks exceeds the inter-write interval, and the merge path consults no wall clock | 13 §15.3 |
| Out-of-order and duplicated delivery is idempotent on `event_id` and on the three-part key | 03 §5.2, 11 §4.8 |
| **No PMA divergence budget is breached during the 42-day patrol** | §7.4, 11 §9.1 |
| **The edge admission-control gate does not engage** during the scripted scenario | §7.6 |
| Tags authored against a provisional `installed_item_id` resolve through the alias table on confirmation **and** on supersession (sub-cases 1a/1b/1c), with no tag rewritten | 13 §15.2 case 1, 11 §8.4 |
| Edge records drain as live facts: no `X-Backfill`, no `replay: true`, side effects fire ashore | 11 §9.3 |
| PMA aggregates drain at priority class 1, ahead of six weeks of burst telemetry | 11 §9.3 |

### 9.7 Admission control and capacity tests

| Test | Asserts |
|---|---|
| `pma-admission-warmup` | Within the first 30 days, throughput basis is `planned_warmup` at 840/month; the gate does not engage on day one with an empty history |
| `pma-admission-engage` | Steady state: backlog at exactly `3 × throughput` does **not** engage; one candidate more does. The boundary is tested, not assumed |
| `pma-admission-zero-throughput` | After warmup with zero adjudications in 30 days, any backlog engages the gate. This is the intended behaviour and there is no floor that defeats it |
| `pma-admission-hysteresis` | Clearance requires `backlog ≤ 2 × throughput` sustained one monotonic hour; the gate does not flap at the engage boundary |
| `pma-admission-halt-semantics` | While engaged: no `mission_review.opened` is published; reviews are created in `deferred_admission_control`; **`anomaly.detected` is still consumed and persisted**; open reviews remain completable; `POST /proposals` returns `429` with `Retry-After`; re-review sampling is suspended and the gap is recorded |
| `pma-admission-nothing-dropped` | Every candidate and deferred review present at engagement is present and processable after clearance |
| `pma-admission-per-node` | An enterprise breach does not engage the edge gate, and vice versa |
| `pma-admission-override` | An override requires a bounded expiry and two distinct `planner`-or-above approvers, is audited with both identities, and does **not** suppress the alert |
| `pma-admission-inherited-not-counted` | Reconnect-time inherited adjudications do not raise the threshold |
| `pma-capacity-45s` | With the reference dataset, `GET /reviews/{id}/candidates?include=evidence_manifest` returns the full cap with materialised manifests in one round trip inside the p95 budget (06 §7: 1.5 s views, 4 s explanation decomposition), and `GET /reviews/next` returns a pre-materialised review |
| `pma-capacity-cap-configurable` | `candidate_cap` is read from configuration; nothing in the service hard-codes 12 |

### 9.8 Weighting and re-review tests

`pma-weight-components-stored` (product re-derivable from components); `pma-weight-floor` (never zero, never above one); `pma-weight-unmeasured-not-penalised` (`w_agreement = 1.0` absent re-review data); `pma-weight-snapshot-frozen` (a later qualification change does not re-weight an existing tag); `pma-dwell-flag-not-multiplier` (a fast label keeps full weight, is flagged, and is excluded from the primary export); `pma-rereview-blind-server-side` (the first pass's outcomes are excluded **in the query**, asserted by inspecting the SQL and by a response-content check); `pma-rereview-sampling-deterministic` (5% ± tolerance, reproducible from the seed); `pma-rereview-kappa-shrunk` (per-reviewer κ is shrunk, published with `agreement_n` and an interval, and the pool figure is primary); `pma-export-gate` (a `detector_training` extract without the reference sample and without acknowledgement returns `422`; `is_negative_label = false` rejections are excluded).

---

## 10. Deployment

### 10.1 Charts

One chart per service (09 §2.4), two values files, both of which must deploy:

```
services/pma/helm/
├── Chart.yaml                  # depends on the _fathom-common library chart
├── values.yaml                 # ENTERPRISE
├── values-dev.yaml
├── values-edge.yaml            # EDGE — one SSN (06 §4)
├── templates/
│   ├── deployment.yaml  service.yaml  configmap.yaml  externalsecret.yaml
│   ├── networkpolicy.yaml       # §10.3
│   ├── hpa.yaml                 # enterprise only
│   ├── servicemonitor.yaml  prometheusrule.yaml        # §5.8
│   ├── migration-job.yaml       # pre-install,pre-upgrade; backoffLimit 0
│   └── poddisruptionbudget.yaml # enterprise only
└── tests/                       # helm-unittest, including the egress-equality assertion
```

Umbrella charts per 01 §11: `deploy/helm/fathom-sustainment/` includes the enterprise release; `deploy/helm/fathom-edge/` includes the edge release for the demonstration hull.

### 10.2 The two variants

| Key | Enterprise (`values.yaml`) | Edge (`values-edge.yaml`) |
|---|---|---|
| `slug` / `apiMajor` | `pma` / `1` | `pma` / `1` |
| `replicaCount` | `2` | `1` |
| `autoscaling.mode` | `keda` (consumer lag on five consumed types) | `none` |
| `app.config.producerNode` | `enterprise` | `edge:<asset_id>` — **never `enterprise`**, asserted by helm-unittest |
| `app.config.candidateCap` | `12` (06 §6) | `12` |
| `app.config.canaryDensityTarget` | `0.15` (06 §6) | `0.15` |
| `app.config.admissionMultiplier` | `3.0` (06 §6) | `3.0` |
| `app.config.plannedMonthlyThroughput` | `840` (06 §6) | patrol-scaled (§7.6) |
| `app.config.reReviewFraction` | `0.05` (06 §6) | `0.05` |
| `app.config.stalenessBoundSeconds` | `300` | `Infinity`-equivalent: staleness refusal is disabled for disconnected operation and the degraded mode is displayed instead (11 §9.1) |
| `app.config.telemetryBaseUrl` | via `gateway` (§10.3) | the on-hull Telemetry service |
| `app.config.referenceDataMode` | `runtime` (read-through API) | `pinned_package` (12 §7.4) |
| `database.clusterName` | `fathom-pma-pg` | `fathom-pma-pg-edge` |
| `objectStore.bucket` | `fathom-pma-evidence` | `fathom-pma-evidence-edge` (local MinIO, object-lock enabled) |
| `sync.edgeCoordinatorEnabled` | `false` | **`true`** (11 §9.2 — the one legitimately inert component, active here) |
| `sync.divergenceBudgets` | not applicable | 90 days for `anomaly_candidate`, `anomaly_tag`, `tag_rejection`, `mission_review`, `evidence_package` (§7.4) |
| `canaryPool.preStaged` | `false` | `true`, 12 plants (§7.4) |
| `resources` | requests 200m/512Mi, limits 1/1Gi | requests 100m/256Mi, limits 500m/512Mi |
| `podDisruptionBudget` | enabled | disabled (single replica) |

`events.publishes` / `events.consumes` in both files equal `catalog.py` exactly (§8.1), reconciled by CI job 6.

### 10.3 NetworkPolicy, and the one edge that needs an ADR

Default-deny plus explicit allow, rendered from `values.networkPolicy` and nothing else; the helm-unittest assertion requires the rendered egress peer set to **equal** the declared set (09 §4.4.2).

```yaml
networkPolicy:
  enabled: true                      # NEVER false in any environment
  ingress:
    fromServices: [gateway]
    allowPrometheusScrape: true
  egress:
    toOwnDatabase: true
    toEventBus: true
    toServices: [auth, audit, reference-data, gateway]   # gateway: see below
    toNamespaces: []
    allowDNS: true
```

**`pma → gateway` is not in 09 §4.4.2's sanctioned edge set and requires an ADR.** Evidence materialisation must read Telemetry (§2.6), and 09 §4.4.2 forbids sub-application → sub-application traffic outright, citing 03 principle 2. The position taken here, to be recorded as `docs/adr/NNNN-pma-evidence-materialisation-egress.md`:

- Materialisation is **not a compute path** in 03 principle 2's sense. It is an asynchronous, retried, out-of-band bulk transfer that gates a workflow state transition; no request/response path and no correctness property depends on its latency. Its nearest existing analogue is the one cross-namespace rule 09 §4.4.2 already sanctions — Domino scoring Jobs writing to PdM **through the gateway**.
- It routes **through the gateway** for the reason 09 gives for that precedent: a single ingress and caller identity attached in one place. The rejected alternative is a direct `pma → telemetry` rule, rejected because it would need repeating for every future evidence consumer and would weaken the invariant NetworkPolicy exists to hold.
- At the **edge** the peer is the on-hull Telemetry service, and the same reasoning and the same ADR apply.
- This is a genuine tension in the source documents rather than a convenience, and §13 records it as an item for 09 §4.4.2 to absorb.

Two prohibitions restated as policy rather than as prose: PMA holds no credential for Telemetry's TimescaleDB and no credential for Telemetry's bucket (C36, and 09 §8.6's DoD item).

### 10.4 Health, readiness, and metrics

`/healthz` is process-local only. `/readyz` aggregates the five mandatory checks of 09 §5.6 — `database`, `migrations`, `broker`, `read_model_lag` (for all five consumed types against `stalenessBoundSeconds`), `outbox_drain` — plus four PMA checks:

| Check | Fails or degrades when |
|---|---|
| `evidence_materialisation` | Oldest `materialising` package exceeds its deadline, or the failure rate over the trailing window exceeds a bound |
| `taxonomy_projection` | No pinned projection is cached, or the pinned version is older than a configured bound with no refresh succeeding |
| `admission_control` | **Degraded, not failed**, while engaged — the service is functioning in a defined mode, exactly as 11 §9.1 treats a divergence breach — enumerating backlog, threshold, and basis |
| `canary_pool` | Edge: remaining plants below the patrol requirement. **Degraded**, alarmed, and never silent: an exhausted pool means recall is no longer being measured |

Metrics are the fixed names of 09 §5.6 plus the PMA set of §5.4, plus `fathom_pma_review_duration_seconds`, `fathom_pma_candidate_dwell_seconds`, `fathom_pma_evidence_materialisation_seconds`, `fathom_pma_evidence_materialisation_failures_total`, `fathom_pma_admission_control_engaged`, `fathom_pma_admission_backlog_ratio`, `fathom_pma_admission_control_override_active`, `fathom_pma_interreviewer_kappa`, and `fathom_pma_novel_signature_proposals_total`.

### 10.5 Purge path

03 §13 and D15 require a declared purge path per store, stating whether it is legally immutable or operationally append-only:

| Store | Class | Purge mechanism |
|---|---|---|
| `anomaly_tag`, `tag_rejection` | **Operationally append-only** | Envelope-level encryption with per-classification keys; crypto-shredding the KEK is the purge (03 §13.1, 11 §10.1). Row-level deletion is forbidden by trigger |
| `evidence_package` objects | Operationally append-only, object-locked | Same KEK class; `payload_ref` objects are not an exemption (11 §10.1). Object-lock is governance mode, not compliance mode, precisely so a lawful purge is possible |
| `canary_plant` | Operationally append-only | Same; the truth link is the most sensitive data PMA holds and is encrypted under the same discipline |
| Outbox / inbox / quarantine | Library-owned | `purge_by_selector(...)` (11 §10.1) |
| Read models | Rebuildable | Truncate and rebuild from `changed_since` |

---

## 11. Explicit DO-NOT list

Each item carries the finding that makes it a defect rather than a preference. A reviewer may cite the ID and stop reading.

### 11.1 The metric trap

1. **Do not train solely on adjudication outcomes.** Precision measured against human adjudication improves as reviewers reject to finish; the exhaustively-labelled reference sample (13 §13.3) is the reference independent of adjudication behaviour, and the export gate of §6.5 is the mechanism. *(**D17**, 06 §6 countermeasure 2, 01 §8.8)*
2. **Do not treat all rejections as negative labels.** `insufficient_evidence`, `sensor_artifact`, `wrong_installed_item`, and `duplicate_of_candidate` are not evidence that equipment was healthy. Training on them teaches detectors to be quiet about the cases humans found hard, which raises precision, shortens reviews, and collapses recall. The reason class and `is_negative_label` exist for this. *(**D17**, and **D34** by direct analogy)*
3. **Do not report precision without recall.** There is one quality operation and its response model makes both required. Do not add an operation, a metric, or a dashboard panel that serves precision alone. *(**D17**, 06 §6 countermeasure 1)*
4. **Do not let canary status be observable before adjudication** — not in a wire model, not in an event, not in a metric, not in a log line, not in a latency difference. A reviewer who can identify plants makes recall a measurement of nothing. *(06 §6, 13 §13.2)*
5. **Do not synthesise a canary.** A plant rides on a real detection, with the real detector version and the real score. A separate injector — a synthetic spike, a scaled template, a shortened trajectory — makes canary recall an unbiased estimate of nothing. *(13 §13.1)*
6. **Do not publish a recall figure below the plant gate, and do not publish a point estimate without its interval.** Omission is the honest signal, exactly as it is for `p_failure` below `calibration_population = 50`. *(06 §3's discipline, 03 §7.1)*
7. **Do not floor the admission threshold after warmup.** Zero adjudications means zero throughput means the gate engages, and that is the intended behaviour. A permanent floor produces a pipeline with no reviewers that never halts and never says so. *(**D17**, 06 §6)*
8. **Do not use dwell time as a continuous weight multiplier.** It is Goodhartable and it is not competence. Use the reflex floor as a flag. *(**D17**'s "~10 seconds… a reflex, not a review")*

### 11.2 The edge

9. **Do not assume enterprise-only candidate generation.** The detector ensemble and a reduced pre-screener are edge-resident, PMA's review workflow must function fully disconnected, and enterprise candidates **add** on reconnect rather than replacing. An enterprise pass that overwrites or prunes the edge set restores the defect. *(**D18**, 03 §11, 06 §4, 11 §7.3)*
10. **Do not host a detector in PMA.** Candidate generation afloat is `telemetry`'s (11 §1.2). PMA consumes `anomaly.detected` with `origin: edge`. *(04 §3, 04 §8, 11 §1.2)*
11. **Do not stop a sibling's detector to relieve a queue,** and do not emit an event intended to. Events carry facts, not instructions. What halts is review admission. *(03 principle 3, C32; §5.6.2)*
12. **Do not drop a candidate to relieve a queue.** Delivery is at-least-once and the inbox must apply. Nothing already recorded is ever discarded. *(03 §5.2, **D2**, 11 §9.1 rule 4)*
13. **Do not let a wall clock arbitrate anything** — not merges, not review duration, not lease expiry, not backoff. A mandated backward step (STIG V-260520) fires at reconnect. Order on `(producer, producer_node, monotonic_seq)` or the HLC. *(**D29**, 03 §5.4, 11 §4)*
14. **Do not key dedup on two parts.** The key is `(producer_slug, producer_node_id, monotonic_seq)`; the enterprise and edge instances of `pma` are two nodes of one slug. *(03 §5.4, 11 §4.2)*
15. **Do not let a divergence budget expire mid-patrol.** Every PMA edge-writable aggregate's budget exceeds the planned patrol length, evidence packages and reviews included. *(11 §9.1, **D8**)*
16. **Do not let the edge mint a canary plant or adjudicate a proposal.** A locally-mintable plant is a locally-forgeable recall figure; adjudication is server-authoritative and claim-gated. *(03 §11, 11 §7.3)*

### 11.3 Tags, evidence, and the taxonomy

17. **Do not mutate or delete a tag or a rejection.** A changed judgment is a new record with `supersedes_tag_id`; both survive. Enforced by trigger. *(03 §11, 11 §7.3)*
18. **Do not invalidate a tag on `configuration.baseline_changed`.** Predictions are invalidated; human observations are not. The tag records the epoch it was assigned under. *(03 §6, §2.4 here)*
19. **Do not read Telemetry's database or object store.** Evidence is materialised through Telemetry's published API into PMA's own bucket. *(**C36**, 04 §8, 09 §8.6)*
20. **Do not let an evidence package change after a review opens,** and do not open a review whose evidence did not materialise. A candidate with no evidence produces a reflex rejection — a false negative injected by the platform. *(04 §8)*
21. **Do not use `occurred_at` as a feature timestamp for a tag.** Tags are hindsight-authored and the marker exists to prevent it. *(**D22**, 03 §5.4, 11 §5)*
22. **Do not embed taxonomy content beyond a read-through cache** — no signature enum, no code list, no family list, anywhere in this service. *(12 DO-NOT-1, **C8/D31**)*
23. **Do not collapse a many-to-many crosswalk.** No `LIMIT 1`, no primary-mode selection, no scalar where the data holds a set — including in signature-agreement computation. *(12 DO-NOT-2)*
24. **Do not normalise on write.** Store the signature the reviewer chose; never translate a findings code into a signature or a signature into a 3-M code for storage. The disagreement is the signal. *(12 DO-NOT-8, 12 §9.3, 03 §14)*
25. **Do not approve a vocabulary change.** PMA proposes novel signatures; Failure Intelligence is the sole approval authority. *(03 §14, 12 §3.3, 12 §7.1)*
26. **Do not re-pin a historical tag to a newer taxonomy version.** Resolve forward at read time. *(12 §6.2, 12 DO-NOT-5)*
27. **Do not conflate `position_id` with `installed_item_id`,** and do not let a mis-attributed maintenance record move a tag to a different item. *(**C10**, **D9**)*

### 11.4 Proposals, agents, and authority

28. **Do not let an agent write a tag.** Every agent-originated candidate is a `Proposal`; the human adjudicator is the reviewer of record. *(01 principle 7, 01 §8.2, 03 §7.2)*
29. **Do not adjudicate without a claim and `If-Match`, and do not validate only at creation.** Re-validate against current configuration, `valid_until`, evidence hash, and signature existence. *(**D16**, 03 §7.2)*
30. **Do not accept an `anomaly_tag` proposal at class or fleet blast radius,** and do not set an authority class other than `maintainer` for one. *(03 §7.2.1, **D16**)*
31. **Do not treat reviewer free text or retrieved content as instruction.** Domain policy is enforced in the operation regardless of what an agent proposed or why; a non-empty evidence list is necessary and never sufficient. *(**D14**, 03 §9)*
32. **Do not make `GET /reviews/{id}/candidates` agent-eligible.** *(§3.7)*

### 11.5 Platform

33. **Do not add a PMA event type without a document 03 §6 catalog row.** The catalog is reconciled in both directions and a unilateral addition breaks CI and the consumer-driven suite. *(**C3–C5**, **C37**, 09 §6.2 job 6)*
34. **Do not subscribe to a topic with no catalog row** — including Reference Data's taxonomy topics until OD-7 lands. *(12 §3.4 OD-7, **C38**)*
35. **Do not compact a PMA topic,** and never set a compaction key equal to a partition key. *(**D5**, 03 §5.1)*
36. **Do not treat the event bus as a rebuild source.** *(**D5**)*
37. **Do not drain edge records as replay.** They are live facts arriving late; `X-Backfill` and `replay: true` are for history. *(11 §9.3, **D30**)*
38. **Do not disable `networkPolicy.enabled` or add an undeclared peer.** The `pma → gateway` edge requires the ADR of §10.3. *(01 §11, 09 §4.4.2)*
39. **Do not invent a quantity.** Cap 12, 45 s, 15%, 5%, 3×, 840/month, 42 days all come from 06 §6, §7, and 13 §15. *(**D37**, 09 §9.5 item 31)*
40. **Do not put a program implementation standard in the conformance suite.** Assert the observable property — no state change without its event, by fault injection. *(**D24**, 03 §10)*

---

## 12. Definition of Done

The shared Definition of Done in [09 §8](09-monorepo-and-conventions.md) applies **in full and unmodified** — §8.1 contract and specification, §8.2 events, §8.3 outbox/inbox/read models, §8.4 data and storage, §8.5 conformance and tests, §8.6 deployment and boundary, §8.7 documentation and governance. Nothing is removed. Copy it into `services/pma/README.md` and tick it there.

Service-specific additions, all of which must hold:

### 12.1 The three items this document exists to add

- [ ] **Canary injection is implemented and tested.** `pma-canary-schema-clean`, `pma-canary-no-plant-join`, `pma-canary-no-leak-fuzz`, `pma-canary-abac`, `pma-canary-indistinguishable` (with power reported), `pma-canary-rank-stratum-matched`, `pma-canary-density`, `pma-canary-no-synthesis`, `pma-canary-metrics-timing`, and `pma-canary-displacement-safe` all green. *(§5.2, §5.3, §9.4; 06 §6, 13 §13)*
- [ ] **Admission control is implemented and tested.** `pma-admission-warmup`, `-engage` (at the exact boundary), `-zero-throughput`, `-hysteresis`, `-halt-semantics`, `-nothing-dropped`, `-per-node`, `-override`, and `-inherited-not-counted` all green, and `GET /admission-control` reports backlog, threshold, throughput, and basis. *(§5.6, §9.7; 06 §6)*
- [ ] **Both Helm variants deploy.** The enterprise release and the edge release each install, migrate, pass `/readyz`, and pass `helm lint`, `helm template | kubeconform --strict`, and `helm unittest` — including the egress-equality assertion and the assertion that the edge variant's `producerNode` is not `enterprise`. *(§10.1, §10.2; 01 §11, 01 §12)*

### 12.2 Recall measurement

- [ ] `pma-canary-recall-arithmetic`, `-gate`, `-excludes-abandoned`, and `-clustering` green; the Wilson interval is published with every point estimate. *(§5.4, §9.3)*
- [ ] `GET /quality-metrics` returns precision and canary recall from **one** operation, with `precision_interpretable` false whenever recall is gated. There is no operation that returns precision alone. *(§5.5)*
- [ ] `pma-quality-divergence` green, and the `PmaQualityDivergence` alert rule ships in the chart. *(§5.5, §5.8)*
- [ ] End-to-end recall is computed over the generator's exhaustively-labelled reference-sample missions and reported alongside canary recall. *(§5.1, 13 §13.3)*
- [ ] `PmaCanaryRecallUnmeasurable` alerts after 45 days of `insufficient_canaries`. An absent recall metric is as visible as a falling one. *(§5.8)*

### 12.3 Labels, taxonomy, and quality

- [ ] Every tag and rejection carries `taxonomy_version`; no unversioned label exists. `pma-corrupt-3m-set-valued` green. *(I1, 03 §14)*
- [ ] The immutability trigger is proven **live**, not mocked: an `UPDATE` of a semantic column raises, a `DELETE` raises, a second supersession marking raises. *(§2.4; 12 §8.2's `tax-ver-freeze` pattern)*
- [ ] `tax-single-source` green — no taxonomy literal anywhere in `services/pma/`. *(12 §8.1, DO-NOT-1)*
- [ ] `tax-proj-pma` contributed to Reference Data's suite and green. *(12 §8.1)*
- [ ] The novel-signature path is exercised end to end: escape tag created, proposal submitted to Reference Data, adjudicated by `failure-intel`, resolved forward after publication, original tag unrewritten. *(§4.4, 12 §7.2)*
- [ ] `is_negative_label` is derived from `reason_class` in one versioned place, and the export gate refuses a `detector_training` extract that violates §6.5. *(§2.5, §6.5)*
- [ ] All nine label-corruption tests of §9.5 green, including `pma-corrupt-wrong-item`. *(13 §9.10)*
- [ ] Reviewer qualification snapshots are immutable, weight components are stored, and `pma-weight-*` plus `pma-rereview-*` are green. *(§6)*

### 12.4 Evidence and the C36 boundary

- [ ] Evidence packages are materialised **only** through Telemetry's five published operations, with `as_of` and `as_known_at` recorded in `source_calls`. *(§2.6)*
- [ ] PMA holds no credential for Telemetry's database or bucket, and NetworkPolicy admits no such peer. *(**C36**, 09 §8.6)*
- [ ] A package is immutable from review open, proven at all three layers (object lock, trigger, tag-pinned hash). *(§2.6)*
- [ ] A review never opens with an unmaterialised or failed package. *(§3.1 stage 9/10)*
- [ ] The `pma → gateway` egress ADR is written and merged. *(§10.3)*

### 12.5 Edge

- [ ] `pma-edge-six-week` green against the generator's `edge-ssn-6wk-*` scenarios, with every row of §9.6's table asserted. *(13 §15)*
- [ ] Every PMA aggregate has a declared conflict policy; the registry's startup enumeration passes with no implicit default. *(§7.3, **C20**, 11 §7.2)*
- [ ] `mission_review` is declared `EDGE_AUTHORITATIVE_THEN_ENTERPRISE` with the rationale recorded in the README. *(§7.3)*
- [ ] Divergence budgets for all five edge-writable aggregates exceed the planned patrol length. *(§7.4, 11 §9.1)*
- [ ] The pre-staged canary pool is provisioned, encrypted at rest, sized with margin, and its exhaustion degrades `/readyz` and alarms. *(§7.4, §10.4)*
- [ ] `producer_node` is `enterprise` or `edge:<asset_id>` per 03 §5.4, and the three-part dedup key is used everywhere. *(§7.2)*

### 12.6 Governance

- [ ] `README.md` records: purpose, owned aggregates, published and consumed events, **conflict policy per aggregate**, staleness bound, sanctioned NetworkPolicy peers, and the local resolutions of every `[OPEN]` item in §13.
- [ ] Every deviation from documents 03 or 09 carries an ADR — at minimum the §10.3 egress ADR.
- [ ] Every open item in §13 is either resolved and this document updated, or explicitly accepted as a demonstration-scope risk with a named owner. **The plant-pool production path (PMA-OD-2) and the reviewer-availability assumption cannot be closed by silence.**

---

## 13. Open items

| ID | Item | Owner | Consequence if unresolved |
|---|---|---|---|
| **PMA-OD-1** | **The `pma → gateway` egress for evidence materialisation is not in 09 §4.4.2's sanctioned edge set.** §10.3 takes a position and requires an ADR; 09 §4.4.2 should absorb the edge, or 03 principle 2 should state explicitly that out-of-band bulk materialisation is not a compute path | Architecture + 09's owner | Every implementer re-litigates it, or one of them adds a direct `pma → telemetry` rule and the invariant erodes |
| **PMA-OD-2** | **Where canary plants come from in production**, where no generator knows the truth. §5.3.3's proposal is replayed historically-confirmed tags from other hulls, which introduces a distribution-shift question | Program + Failure Intelligence | Canary recall is a demonstration-only mechanism, and D17's countermeasure does not survive to production — which is where the reviewers are scarcest |
| **PMA-OD-3** | **OD-7 (12 §3.4): `fathom.reference-data.*` topics have no 03 §6 catalog rows.** PMA polls instead of subscribing (§4.2) | Architecture | A taxonomy publication is noticed on a poll interval rather than immediately; and the consumer-driven conformance test for those topics cannot be written |
| **PMA-OD-4** | **`authority_class` is typed as an opaque string in `packages/canonical-schemas` (10 OQ-13).** 03 §7.2.1 now supplies the vocabulary; the package should narrow to a `StrEnum` | 10's owner | D16's authority check is enforced per-service rather than by the shared type, so a sub-application can still set a nonsense value |
| **PMA-OD-5** | **Whether the ~45 s per candidate figure survives contact with maintainers** (06 §6, MEDIUM). If real inspection is 2–3 minutes, the cap drops to 4–5 and ranking becomes far more consequential | Program | The capacity model, the candidate cap, and the ranker's value are all provisional together |
| **PMA-OD-6** | **Whether reviewers exist at all in production** — 06 §6 marks this "**LOW.** This is the program's largest non-technical risk," with the stated fallback of retaining the pre-screener as an advisory surface and dropping the supervised causal pipeline | Program | A materially smaller product, which 06 §6 says "should be surfaced early rather than discovered late" |
| **PMA-OD-7** | Whether admission-control engagement should be a published event. §5.6.2 declines to invent one; adding it requires a 03 §6 catalog row | Architecture | Shore learns of a hull's halt on reconnect through metrics and audit rather than through an event, which is adequate but not ideal |
| **PMA-OD-8** | Whether per-reviewer canary outcomes should ever enter `label_weight`. §6.4 decides no for `weighting-1.0.0` and records the tension | Program + Failure Intelligence | Reviewer-quality weighting rests on re-review agreement alone, whose per-reviewer n is small by construction |
| **PMA-OD-9** | Reviewer assignment policy — by billet, by qualification, or by asset (04 §8's Phase 3 question). This build assigns by persona and family endorsement and leaves the policy configurable | Program | Assignment interacts with the qualification weighting of §6.2, so a policy change re-weights the corpus |

