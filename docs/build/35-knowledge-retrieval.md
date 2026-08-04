# Knowledge & Retrieval — Configuration-Aware, Classification-Enforcing Retrieval

| | |
|---|---|
| **Status** | Draft |
| **Slug** | `knowledge-retrieval` (document 03 §3.1; platform service, `platform/knowledge-retrieval/`) |
| **Purpose** | Build specification for the platform service that ingests the unstructured corpus — IETMs and technical manuals, 3-M maintenance narratives, CASREP text, test reports, engineering change proposals — chunks and embeds it on pgvector, and serves it under **two hard filters applied inside a single database query**: the requesting asset's as-maintained configuration, and the requester's clearance |
| **Resolves** | Finding **D14** (no prompt-injection threat model — this service owns the corpus the finding is about) and the query-time half of **D13** (post-filtering for classification leaks the existence of records). Contributes the vector-index leg of **D15** (purge path) |
| **Primary technical source** | [04 §11](../architecture/04-subapplication-architectures.md) "Knowledge & Retrieval" in full; [03 §7.3](../architecture/03-integration-contracts.md) and [03 §9](../architecture/03-integration-contracts.md) in full; [01 §8.3](../architecture/01-system-architecture.md), [01 §8.5](../architecture/01-system-architecture.md), [01 §8.8](../architecture/01-system-architecture.md) |
| **Binding contracts** | [03 §3.3](../architecture/03-integration-contracts.md) (identity, and the EIC prohibition), [03 §4](../architecture/03-integration-contracts.md) and [§4.1](../architecture/03-integration-contracts.md), [03 §5](../architecture/03-integration-contracts.md), [03 §6](../architecture/03-integration-contracts.md) (`configuration.baseline_changed` names this service a declared consumer), [03 §7.2](../architecture/03-integration-contracts.md) (`evidence[].source_trust`), [03 §7.3](../architecture/03-integration-contracts.md), [03 §8](../architecture/03-integration-contracts.md), [03 §9](../architecture/03-integration-contracts.md), [03 §12](../architecture/03-integration-contracts.md), [03 §13](../architecture/03-integration-contracts.md), [03 §15](../architecture/03-integration-contracts.md) |
| **Depends on** | [04 §2](../architecture/04-subapplication-architectures.md)'s **stable, architecture-level** Registry API surface — `GET /assets/{id}/configuration?as_of=&as_known_at=`, `GET /classes/{id}/template` — cited at that level deliberately, because `docs/build/20-registry.md` does not exist yet. Nothing in this document depends on a written sibling build doc |
| **Conventions** | [`09-monorepo-and-conventions.md`](09-monorepo-and-conventions.md) (scaffold §4, API rules §5, DoD §8, DO-NOT §9), [`10-shared-packages.md`](10-shared-packages.md) (`ClassificationLabel` §4.8, `SourceTrust`/`Evidence` §4.7), [`11-outbox-sync-library.md`](11-outbox-sync-library.md) (outbox, inbox, monotonic clock) |
| **Classification** | Internal. The service operates single-level at `U` for the synthetic demonstration ([03 §12](../architecture/03-integration-contracts.md), [06 §5](../architecture/06-demo-decisions-and-assumptions.md)). **The multi-level mechanism is nevertheless built and tested with two synthetic levels**, because it is not retrofittable — see §5.3 |

---

## 0. How to read this document

Document 04 §11 marks this service **"Substantial Phase 3 design required"** and then names the two requirements that dominate it:

> *"**Configuration-aware retrieval.** Results are filtered by the target asset's as-maintained configuration baseline, so a maintainer is never presented a procedure for a variant not installed. This requires that corpus documents carry applicability metadata — class, configuration, and effective date — which for legacy technical documentation is a substantial data-preparation problem rather than an indexing detail."*
>
> *"**Classification enforcement at query time.** Filtering must occur within the query rather than by removing results afterward, because post-filtering leaks the existence of records the requester is not cleared to know about."*

Both are stated as *filters*. Neither is a filter. Each is a **query shape**, and the whole point of §4 and §5 is that they are the *same* query shape — one SQL statement in which the similarity search, the applicability predicate, and the clearance predicate are indistinguishable parts of one plan. Sections 4 and 5 therefore contain literal SQL rather than prose, because prose is where this design fails: every intuitive implementation of "filtered retrieval" is `retrieve(k) → filter → return`, and that implementation is the defect.

Section 6 is the D14 section. It is short because the honest answer to prompt injection is structural and small: this service returns retrieved text in a shape that cannot be mistaken for an instruction, tags its trust and provenance, and **enforces no domain policy whatsoever** — that is the receiving sub-application's job per 03 §9 item 2, and any attempt to make it this service's job weakens the real control.

Read §7 before believing the service is safe. Configuration-aware retrieval requires this service to hold *some* configuration facts, and a service that holds configuration facts is one operation away from becoming a second, unauthoritative source of current state. §7 is how that operation is prevented from ever being written.

---

## 1. Purpose and scope

### 1.1 What this service is

The **unstructured** half of document 01 §8.3's grounding split:

> *"**Structured** — live sub-application APIs invoked as tools. Authoritative for current state. Agents must not answer state questions from parametric memory or from the vector store. **Unstructured** — the Knowledge & Retrieval service: IETMs and technical manuals, 3-M narrative text, CASREP narratives, test reports, and engineering change proposals."*

It serves **procedural and narrative knowledge with citations**. It never serves a fact about what is happening now.

### 1.2 In scope

1. **Corpus ingest** across five source types (§2.1), with a per-type chunking contract (§2.2).
2. **Applicability metadata extraction** — the problem 04 §11 calls *"a substantial data-preparation problem rather than an indexing detail"* — as a three-pass pipeline with a fail-closed default and an SME review queue (§2.4).
3. **Embedding and vector storage on pgvector** (01 §14, 09 §2.3: pgvector, this service only, its own cluster), with embedding-model versioning as a hard query predicate (§2.6).
4. **A configuration applicability read model** derived from `registry.configuration.baseline_changed` plus authoritative reads of 04 §2's configuration endpoint (§3.6). It is an **input** to retrieval and is never exposed.
5. **The retrieval query** — one statement, three predicates (§4, §5).
6. **The `retrieved_context` return shape**, `source_trust` propagation, and ingest-time provenance (§6).
7. **A declared purge path** covering the vector index, which 03 §13 and D15 name explicitly (§10).

### 1.3 Out of scope

- **Any current-state fact.** No predictions, no readiness, no operational status, no live configuration answers. §7 specifies the mechanical enforcement, not the good intention.
- **Domain policy enforcement.** APL authorization, bounded interval deltas, baseline presence — these are validation rules on the *receiving* operation (03 §9 item 2). This service does not check, warn about, or refuse to serve content that would lead to a bad proposal.
- **Agent prompt assembly.** How a `retrieved_context` block is placed in a prompt is a Wave-5 / `tool-server` and `agents/*` concern. This service's obligation is to make the correct placement *possible and the incorrect placement awkward* (§6.1).
- **Running the injection evaluation.** Golden question sets and promotion gates are agent evaluation (01 §8.8). This service **supplies the adversarial corpus content** those tests need (§6.3) and does not grade anything.
- **Authoring or correcting technical documentation.** The SME review queue (§2.4) records an applicability determination against an unmodified source document. Chunk bodies are never edited (§6.4).
- **The ingest compute itself.** Document parsing, chunking, and LLM-assisted extraction run as Domino Jobs and deliver results through this service's bulk ingest operation (§2.7, §12.2) — the D10/C7-compliant pattern, identical to how PdM receives scoring results.

### 1.4 The one-sentence design thesis

**The count of records withheld from a query is never computed anywhere in this system** — not in SQL, not in Python, not in a metric, not in a log line, not in an audit record — because the predicate that withholds them is inside the index scan, and therefore no channel exists that could leak it.

Everything in §5 is mechanism in service of that sentence.

---

## 2. Corpus ingest and chunking

### 2.1 The five source types

Named in 04 §11 and 01 §5. Each carries different structure, and structure is what determines both chunking and how much of the applicability problem is free.

| `source_type` | What it is | Structure available | Applicability available? | `origin` typically |
|---|---|---|---|---|
| `ietm` | Interactive Electronic Technical Manual — modular, tagged, with data-module codes | **High.** XML data modules, step hierarchy, explicit applicability elements | **Structured** — parse it | `program` or `vendor` |
| `technical_manual` | Legacy TM, frequently a scanned PDF with an OCR layer | **Low.** Headings, front matter, an applicability or effectivity page if you are lucky | **Mostly unstructured** — this is the hard case | `program` or `vendor` |
| `three_m_narrative` | 2-Kilo narrative blocks. Per [07 §5.3](../architecture/07-navy-data-systems.md): record types `BA`–`BT`, `CA`–`CT`, `MA`–`MT`, layout `1-13 JCN · 14-17 date · 18-77 narrative` — **60 characters of text per block**, assembled across continuation blocks | **High**, and the text is tiny | **Structured and exact** — the record carries JCN → UIC → asset, and the action carries `installed_item_id` | `program` |
| `casrep` | Casualty report. Four types in sequence — `INITIAL`, `UPDATE`, `CORRECT`, `CANCEL`; categories 2–4 ([07 §5.8](../architecture/07-navy-data-systems.md)) | **Medium.** Structured header, free-text narrative paragraphs | **Structured from the header** | `program` |
| `test_report` | Test and evaluation report with a test-article configuration section and results tables | **Medium.** Sectioned, tabular | **Semi-structured** — the article configuration section is the applicability, in prose | `program` or `external` |
| `ecp` | Engineering change proposal | **Medium–high.** Cover sheet plus an affected-configuration-items list | **Structured** — the affected-items list *is* the applicability | `vendor` or `external` |

⚠️ **Source-format detail is deliberately thin, per 09 DO-NOT #32.** *"Do not add Navy schema detail here or in a shared package on the basis of general knowledge."* [07 §10](../architecture/07-navy-data-systems.md) records that the current 3-M data element dictionary, the modern 120 Card Format, and CASREP per-set field lists are **NOT PUBLICLY FOUND**, and IETM/S1000D applicability semantics were not researched in documents 01–08 at all. Every parser in §2.2 is therefore written against a **declared adapter interface with a documented, testable assumption set**, and the assumption set is an OD item (§14, OD-2).

### 2.2 Chunking — the per-type contract

Two rules govern every row of this table and matter more than the numbers in it.

**Rule A — a chunk boundary is a safety decision, not a tokenization decision.** A maintainer acting on half a procedural step is a mishap. Where a boundary is semantically load-bearing — a procedural step, a 2-Kilo narrative record, a WARNING/CAUTION block — the chunker **does not cross it and does not use overlap to paper over it.**

**Rule B — where overlap would duplicate a load-bearing unit, carry a `parent_context` header instead.** Every chunk stores, separately from `body`, an immutable `parent_context` string: document title and revision, data-module code or section path, and the step path. It is prepended for embedding and returned as `citation`, so a chunk is interpretable standing alone without duplicating a step into two chunks — and a duplicated step is exactly how a maintainer performs an action twice.

| `source_type` | Chunk unit | Target / hard cap (tokens) | Overlap | Non-negotiable invariant |
|---|---|---|---|---|
| `ietm` | One data module. Long procedures split at step boundaries only | 400–800 / **1024** | **0** | **A WARNING or CAUTION governing a step is duplicated into every chunk of that step's procedure.** A safety notice separated from the action it governs is the worst defect this service can produce |
| `technical_manual` | Heading-bounded section, then a sliding window inside the section | 500 / **1024** | **100** | A window never crosses a heading. A table is never split (§below) |
| `three_m_narrative` | **The whole narrative, reassembled across all continuation blocks. Never split.** | ~60–900 chars / n/a | n/a | Blocks `BA`–`BT` for one JCN reassemble in block order into one chunk. A 60-character fragment is not a retrievable unit of meaning |
| `casrep` | Whole message when under cap; otherwise one chunk per narrative paragraph with the structured header re-prepended into `parent_context` | 512 / **1024** | **0** | The `INITIAL`/`UPDATE`/`CORRECT`/`CANCEL` sequence for one casualty is linked by `casualty_ref`, and a `CANCEL` **supersedes its predecessors** (§3.1 `superseded_by`) — a cancelled casualty must not surface as current narrative |
| `test_report` | Per section; each table kept whole and linearized to text | 800 / **1200** | **100** | **A table is never split.** A results table split mid-row produces a chunk asserting a measurement it does not contain |
| `ecp` | Cover sheet as one chunk; technical description per section | 600 / **1024** | **100** | **The affected-configuration-items list is parsed into applicability metadata and is *not* embedded as prose.** Embedding it invites a semantic match on a list of part numbers, which retrieves the ECP for assets it does not affect |

**Token counting** uses the tokenizer of the pinned embedding model (§2.6), not a character heuristic, and the cap is enforced by truncation-with-error rather than silent truncation: a chunk that will not fit after boundary-respecting splitting fails the ingest run for that document and enters the review queue. Silent truncation loses the end of a procedure, which is where the torque values are.

**Deduplication.** `content_hash` is `sha256(normalized_body || parent_context)`. Identical chunks arriving from two documents are stored once with two `document_chunk_source` rows, so a citation resolves to the document the user actually holds. Per [13 §9.10](13-synthetic-data-generator.md), duplicate 2-Kilos with different JSNs are an expected generated corruption — dedup must key on content, not on JCN.

### 2.3 What is embedded versus what is stored

| Field | Embedded? | Returned? | Why |
|---|---|---|---|
| `parent_context` | **Yes**, prepended | Yes, as `citation` | Recovers the context that Rule B declined to duplicate |
| `body` | Yes | Yes | The content |
| applicability metadata | **No** | Yes | It is a predicate, not semantics. Embedding it makes the applicability filter *soft*, and a soft applicability filter is the failure 04 §11 forbids |
| classification metadata | **No** | Yes (as `ClassificationLabel`) | Same reason, with a security consequence |
| `source_trust` | **No** | Yes | Ditto |

### 2.4 The applicability-metadata extraction problem

This is the section 04 §11 is pointing at. State the problem exactly: **a legacy technical manual does not tell you which hulls it applies to in a machine-readable way, and the naive default — "no applicability metadata means it applies to everything" — is precisely the failure mode the requirement exists to prevent.**

#### 2.4.1 Three passes, with declining confidence and rising review

| Pass | Method | Applies to | `extraction_method` | Confidence |
|---|---|---|---|---|
| **1** | **Deterministic structured extraction.** Per-type parsers over source structure: IETM applicability elements, ECP affected-items lists, CASREP headers, 3-M record identity resolved through the Registry | `ietm`, `ecp`, `casrep`, `three_m_narrative` | `structured` | **1.0 by construction.** Not a model output; a parse |
| **2** | **Pattern extraction over semi-structured legacy.** Effectivity/applicability front-matter tables, hull-number and hull-range lists, alteration and field-change markers, effective-date blocks | `technical_manual`, `test_report` | `pattern` | Parse coverage: the fraction of the applicability statement the grammar consumed. Anything unparsed lowers it |
| **3** | **LLM-assisted extraction over unstructured legacy** | residual `technical_manual`, `test_report` | `llm_assisted` | Model-reported, then **discounted** per §2.4.2 |

#### 2.4.2 Pass 3, specified so it is auditable rather than magical

Four constraints, each closing a specific way LLM extraction fails silently:

1. **Constrained output against the applicability schema** (§3.3). No free text. An unparseable response is a failure, not a partial success.
2. **Every asserted field carries `evidence_span`** — the verbatim quoted source substring that justifies it, plus its character offset. A field with no span is discarded before it is stored. This makes an SME's review a *verification* task ("does this quote say that?") rather than a re-extraction task, which is the difference between a reviewable queue and an unreviewable one.
3. **`unknown` is a legal and preferred value.** The prompt requires abstention over inference. A model that guesses "applies to all DDG 51 class" from a manual that never says so produces exactly the wrong-variant procedure the requirement forbids.
4. **Two independent extraction passes with different prompts, and disagreement is dispositive.** Field-level agreement is required; any disagreement forces that field to `unknown` and the chunk to review. Self-reported confidence is recorded but is **never** the gate on its own — a confident wrong answer and a confident right answer are indistinguishable in that number.

#### 2.4.3 The gate, and the fail-closed default

```
applicability_scope_state ∈ { resolved , narrowed , unknown }
```

| Condition | `scope_state` | Retrievable in `asset_scoped` mode? | Review |
|---|---|---|---|
| `extraction_method ∈ {structured}` | `resolved` | **Yes** | none |
| `pattern`, coverage ≥ 0.90, no field `unknown` | `resolved` | **Yes** | sampled audit at 5% |
| `pattern`, coverage < 0.90, **or** any field `unknown` | `narrowed` | **Only for the dimensions that did resolve**; an unresolved dimension excludes the chunk | `pending_sme` |
| `llm_assisted`, any confidence | `narrowed` | **No, until reviewed.** No LLM-derived applicability auto-publishes | `pending_sme`, mandatory |
| Nothing extracted, or two-pass disagreement on every field | `unknown` | **No** | `pending_sme` |
| SME confirmed | `resolved` | Yes | `reviewed`, with `reviewed_by`, `reviewed_at` |
| SME rejected | `unknown` | No | `rejected`, chunk withdrawn from `asset_scoped` retrieval permanently |

**The load-bearing decision: `unknown` applicability is not universal applicability.** It is *no* applicability. `scope_state = 'unknown'` is excluded by the `asset_scoped` predicate in §4.2 and is reachable only through the `unscoped` mode, which is `x-substitution: internal`, **not** `x-agent-eligible`, and exists solely for the SME review surface. An agent cannot retrieve unreviewed applicability, in any manifest, by construction.

The cost is honest and must be stated to the program: **on first ingest of a legacy corpus, a large fraction of chunks will be unretrievable pending review.** That is the correct failure direction, and a design that inverts it to get a demo working has removed the requirement rather than implemented it.

#### 2.4.4 ⚠️ REQUIRES SME VALIDATION — explicitly, and before build

Everything in §2.4 is an **engineering proposal with no Navy authority behind it.** The following must be set by a technical-documentation SME and the relevant In-Service Engineering Agent, and are recorded as OD-1:

- The 0.90 pattern-coverage threshold, the 5% audit rate, and the mandatory-review rule for `llm_assisted` — all three are invented numbers, and 09 DO-NOT #31 forbids inventing quantities.
- Whether `narrowed` partial retrieval is acceptable at all, or whether any unresolved dimension must exclude a chunk outright.
- The applicability dimension set of §3.3 — in particular whether alteration/field-change markers are the right encoding of 04 §2's per-asset deviation model for *documentation* applicability.
- Who is authorized to make an applicability determination. This is a technical-authority act, not a data-entry act, and if the answer is "the ISEA" then the review queue is an ISEA workflow with a throughput limit that constrains ingest scheduling.
- Whether an LLM-assisted determination is admissible as an engineering determination **at all**. If it is not, pass 3 becomes a triage aid that pre-populates a human form and nothing more — which the design already supports and should be the assumed posture until an authority says otherwise.

### 2.5 Embedding, model versioning, and the reindex

- **`EmbeddingPort`**, mirroring 01 §8.6's `LLMPort`. Demonstration: Domino AI Gateway. Air-gapped/production: an in-cluster model server in `fathom-sustainment` or a Domino LLM Endpoint (01 §8.6), reachable as an ordinary `toServices` NetworkPolicy peer.
- **`embedding_model_id` is pinned in `Settings`, stored on every chunk, and is a hard predicate in the retrieval query** (§4.2, predicate 1). A query embedded by model A compared against chunks embedded by model B produces plausible, ranked, wrong results with no error anywhere — the worst available failure mode. If the configured model does not match any indexed chunk set, retrieval returns **empty**, and readiness reports the mismatch. It does not silently compare across spaces.
- **Re-embedding is a `reindex_run`**, not an in-place update: new rows under the new `embedding_model_id` in a new partition, then an atomic cutover of the `Settings` pin, then withdrawal of the old set. Both sets coexist during cutover; the predicate keeps them from mixing.
- Dimension, index type, and distance operator are pinned together with the model, because they are one decision: HNSW with cosine distance (`vector_cosine_ops`, `<=>`), `m`/`ef_construction` in `values.yaml`, DDL via `op.execute()` inside an ordinary Alembic revision (09 §2.2).

### 2.6 The provenance record — written at ingest, never inferred

03 §9 item 5 is unambiguous: *"Corpus ingest records authorship and provenance, and content from outside the program is **marked at ingest rather than inferred later**."*

```
document {
  document_id                # UUID, this service's own aggregate identity
  source_type                # ietm | technical_manual | three_m_narrative | casrep | test_report | ecp
  title, publication_ref     # TM number, data-module code root, CASREP DTG, ECP number, JCN
  revision, revision_date

  # --- authorship and origin. Set at ingest. Immutable. ---
  origin                     # program | vendor | external      <- the decision, made once
  authoring_org, author_ref  # organization and, where known, individual
  authored_at
  received_from              # the delivery channel: contract deliverable, vendor portal,
                             #   fleet submission, public source
  received_at

  # --- ingest facts ---
  ingest_run_id, ingested_at
  content_hash               # sha256 of the retained original
  original_object_ref        # S3/MinIO ref to the unmodified original (01 §14)
  parser_version             # the adapter that produced the chunks

  # --- classification, DECLARED AT SOURCE ---
  classification             # ClassificationLabel (03 §7.3, package 10 §4.8)
  classification_source      # source_marking | determination
  classification_authority   # who determined it, where classification_source=determination

  # --- lifecycle ---
  supersedes[], superseded_by, superseded_at, withdrawn_at, withdrawal_reason
}
```

**`source_trust` is derived from `origin` at ingest by a single total function and is never recomputed:**

```python
# platform/knowledge-retrieval/src/fathom_knowledge_retrieval/services/trust.py
_TRUST: Final[Mapping[Origin, SourceTrust]] = {
    Origin.PROGRAM: SourceTrust.PROGRAM,   # 03 §7.2 vocabulary, from packages/canonical-schemas
    Origin.VENDOR:  SourceTrust.VENDOR,
    Origin.EXTERNAL: SourceTrust.EXTERNAL,
}
```

There is no default branch, no inference from filename or authoring organization, and no later "upgrade" of trust. `origin` is a required field of the bulk ingest body; an ingest that omits it is a `422`, not a `program` default. **A default here would be the D14 vulnerability in one line of code**: vendor manuals and ECPs are exactly the content the finding names, and a permissive default marks them as program content.

Two classification rules follow document 08 §5.4–5.5 and apply per chunk, not per document:

- **Marking is not inherited from convenience.** A chunk's label defaults to its document's label but may be *raised* per chunk where the document mixes levels (08 §5.5's per-field redaction principle applied at chunk granularity). It may never be lowered — lowering is a decontrolling act and 08 §5.4 is explicit that no pipeline is a competent decontrolling authority.
- **Naval Nuclear Propulsion Information is scoped explicitly and early** (08 §5.6 action 4). [07 §4](../architecture/07-navy-data-systems.md) notes cognizance code `0S` covers *reactor plant technical manuals*; any document whose source cognizance or content indicates propulsion-plant scope is refused at ingest unless `cui_categories` contains `SP-NNPI` and the deployment declares NNPI handling. `CUI//SP-NNPI` is a materially more restrictive regime and discovering it after ingest is not recoverable (§10).

---

## 3. Data model

Standard scaffold per 09 §4.2; `<pkg>` is `fathom_knowledge_retrieval`. One logical database, `fathom-knowledge-retrieval-pg`, a CloudNativePG `Cluster` on a pgvector-bearing image (09 §2.3: *"pgvector | Knowledge & Retrieval only, on its own cluster"*).

### 3.1 Tables

| Table | Aggregate | Notes |
|---|---|---|
| `document` | root | §2.6. Operationally append-only with a purge path (§10) |
| `document_chunk` | child of `document` | **Partitioned.** Carries body, embedding, applicability, classification, trust. §3.2 |
| `document_chunk_source` | link | Content-dedup: one chunk, N originating documents |
| `applicability_review` | root | The SME queue. `ETag`/`If-Match` on decisions |
| `ingest_run` | root | Bulk ingest fencing and idempotency |
| `reindex_run` | root | §2.5 cutover |
| `config_applicability_context` | read model | §3.6. **Never exposed on the API** (§7) |
| `retrieval_audit` | append-only | §5.5. Records what *was* returned; cannot record what was withheld |
| `outbox`, `inbox`, `idempotency_keys` | infrastructure | `packages/py-sync`, `packages/py-common` |

### 3.2 `document_chunk` — the DDL that matters

```sql
CREATE TABLE document_chunk (
    chunk_id                uuid        NOT NULL,
    document_id             uuid        NOT NULL REFERENCES document(document_id),
    ordinal                 int         NOT NULL,
    version                 int         NOT NULL DEFAULT 1,       -- 09 §5.4 ETag source

    -- ---------- content ----------
    body                    text        NOT NULL,
    parent_context          text        NOT NULL,                 -- §2.2 Rule B
    content_hash            bytea       NOT NULL,
    token_count             int         NOT NULL,

    -- ---------- embedding ----------
    embedding_model_id      text        NOT NULL,                 -- §2.5 hard predicate
    embedding               vector(1024) NOT NULL,

    -- ---------- APPLICABILITY (04 §11: class, configuration, effective date) ----------
    applicable_class_ids        uuid[]    NOT NULL DEFAULT '{}',  -- '{}' == class-agnostic
    applicable_template_revisions int4range,                      -- the "baseline range"; §3.3
    applicable_niins            text[]    NOT NULL DEFAULT '{}',  -- '{}' == not NIIN-scoped
    requires_alterations        text[]    NOT NULL DEFAULT '{}',  -- ALL must be present
    precludes_alterations       text[]    NOT NULL DEFAULT '{}',  -- NONE may be present
    effective_date_range        tstzrange NOT NULL
                                DEFAULT tstzrange('-infinity','infinity'),
    applicability_scope_state   text      NOT NULL,               -- resolved|narrowed|unknown
    applicability_confidence    numeric(4,3),
    extraction_method           text      NOT NULL,               -- structured|pattern|llm_assisted|sme
    review_state                text      NOT NULL,               -- none|pending_sme|reviewed|rejected

    -- ---------- CLASSIFICATION (03 §7.3) ----------
    -- The scalar/array columns are the QUERYABLE projection of `classification`.
    -- `classification` is the wire object returned to the caller. A trigger keeps
    -- them consistent; they are never set independently (§3.4).
    level                   smallint    NOT NULL,                 -- 0=U 1=CUI 2=S 3=TS
    compartments            text[]      NOT NULL DEFAULT '{}',
    dissemination           text[]      NOT NULL DEFAULT '{}',
    cui_categories          text[]      NOT NULL DEFAULT '{}',
    classification          jsonb       NOT NULL,                 -- full ClassificationLabel

    -- ---------- trust and provenance (03 §7.2, §9, D14) ----------
    source_trust            text        NOT NULL,                 -- program|vendor|external
    injection_signals       text[]      NOT NULL DEFAULT '{}',    -- §6.4. FLAGS, not a filter
    quarantined_at          timestamptz,

    -- ---------- lifecycle ----------
    created_at              timestamptz NOT NULL DEFAULT now(),
    superseded_at           timestamptz,
    withdrawn_at            timestamptz,

    PRIMARY KEY (level, chunk_id),           -- partition key must be in the PK
    CONSTRAINT chunk_scope_state  CHECK (applicability_scope_state IN ('resolved','narrowed','unknown')),
    CONSTRAINT chunk_level_range  CHECK (level BETWEEN 0 AND 3),
    CONSTRAINT chunk_cui_at_level CHECK (cardinality(cui_categories) = 0 OR level >= 1)
        -- mirrors ClassificationLabel._cui_categories_only_at_cui (package 10 §4.8)
) PARTITION BY LIST (level);

CREATE TABLE document_chunk_u   PARTITION OF document_chunk FOR VALUES IN (0);
CREATE TABLE document_chunk_cui PARTITION OF document_chunk FOR VALUES IN (1);
CREATE TABLE document_chunk_s   PARTITION OF document_chunk FOR VALUES IN (2);
CREATE TABLE document_chunk_ts  PARTITION OF document_chunk FOR VALUES IN (3);
```

`PARTITION BY LIST (level)` is a security decision, not a performance one — §5.3.

### 3.3 Applicability semantics, and why a chunk cannot carry a `baseline_id` range

The obvious encoding of "configuration baseline range" is a range of `baseline_id`s. **It is unimplementable, and the reason is a fact about the Registry's model rather than a preference.** Per 04 §2, a `ConfigurationBaseline` is *"a bitemporal snapshot of **an asset's** installed configuration"* carrying a monotonic per-asset `baseline_epoch` (01 §6). Baselines are **per-asset**; a technical manual is not. A chunk carrying `baseline_id BETWEEN x AND y` would be asserting applicability against one hull's private numbering.

Applicability is therefore expressed in the vocabulary 04 §2 actually offers — *"a class template plus an explicit ordered deviation set per asset"* — decomposed into four independent dimensions, each of which the resolved per-asset baseline can answer:

| Dimension | Column | Semantics | Empty/NULL means |
|---|---|---|---|
| **Class** | `applicable_class_ids uuid[]` | The asset's `class_id` (03 §3.3: the Navy's lead-hull-number form, carrying flight/block) must be a member | class-agnostic; applies to any class |
| **Configuration baseline** | `applicable_template_revisions int4range` | The asset's resolved **class-template revision** (04 §2's `GET /classes/{id}/template`) must be contained | not template-scoped |
| **Deviation, positive** | `requires_alterations text[]` | **All** listed alterations/field changes must be present in the asset's applied set | no alteration prerequisite |
| **Deviation, negative** | `precludes_alterations text[]` | **No** listed alteration may be present | no alteration exclusion |
| **Part identity** | `applicable_niins text[]` | Must **overlap** the asset's installed NIIN set | not NIIN-scoped |
| **Effective date** | `effective_date_range tstzrange` | The retrieval `as_of` must be contained | always effective |

Two hard prohibitions:

- **EIC is not an applicability key.** 03 §3.3 and 09 DO-NOT #5: *"EIC is a class code of variable specificity, not an instance identifier"*, carried *"for federation and human reference only."* [07 §5.3](../architecture/07-navy-data-systems.md) puts a 7-character EIC at positions 57–63 of a 2-Kilo, and it is tempting precisely because it is *there*. It is stored on `document.publication_ref` metadata for human reference and appears in **no** predicate. `applicable_niins` and `applicable_class_ids` are the keys.
- **`applicable_class_ids = '{}'` is "any class"; it is never a substitute for `unknown`.** An extractor that cannot determine class writes `scope_state = 'unknown'`, not an empty array. Conflating "applies to everything" with "we do not know" is the single most likely way this design is silently defeated, and it is why `scope_state` is a separate column with its own predicate rather than being inferred from array emptiness.

### 3.4 The classification projection, and why it is trigger-maintained

`classification jsonb` is the wire object; `level`/`compartments`/`dissemination`/`cui_categories` are its indexable projection. Two sources of truth for one fact is a defect, so:

```sql
CREATE FUNCTION chunk_project_classification() RETURNS trigger AS $$
BEGIN
    NEW.level           := fathom_level_ordinal(NEW.classification->>'level');
    NEW.compartments    := fathom_jsonb_text_array(NEW.classification->'compartments');
    NEW.dissemination   := fathom_jsonb_text_array(NEW.classification->'dissemination');
    NEW.cui_categories  := fathom_jsonb_text_array(NEW.classification->'cui_categories');
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER chunk_project_classification_biu
    BEFORE INSERT OR UPDATE OF classification ON document_chunk
    FOR EACH ROW EXECUTE FUNCTION chunk_project_classification();
```

The projection is **derived in the database**, so no application path can write a `level` that disagrees with the label it will return. Since `level` is the partition key, an `UPDATE` that raises a chunk's classification moves it between partitions — permitted (PostgreSQL row movement) and audited; a `DOWNGRADE` is blocked by a separate `BEFORE UPDATE` trigger that raises unless the session carries an explicit `fathom.declassification_authority` GUC. Downgrading is a classification-authority act, not a data fix.

### 3.5 Indexes

```sql
-- ANN index PER PARTITION. §5.3: a low-side query's index scan never traverses
-- a high-side graph, because it never opens that partition's index.
CREATE INDEX chunk_u_hnsw ON document_chunk_u
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
-- ... one per partition, identical parameters.

-- Applicability: GIN on the array dimensions, evaluated as base-relation quals
-- alongside the ANN scan (§4.4).
CREATE INDEX chunk_u_class_gin ON document_chunk_u USING gin (applicable_class_ids);
CREATE INDEX chunk_u_niin_gin  ON document_chunk_u USING gin (applicable_niins);
CREATE INDEX chunk_u_eff_gist  ON document_chunk_u USING gist (effective_date_range);

-- A PARTIAL index carrying the invariant predicates, so the common retrieval path
-- never sees withdrawn, superseded, quarantined, or unknown-applicability rows at all.
CREATE INDEX chunk_u_hnsw_live ON document_chunk_u
    USING hnsw (embedding vector_cosine_ops)
    WHERE withdrawn_at IS NULL
      AND superseded_at IS NULL
      AND quarantined_at IS NULL
      AND applicability_scope_state <> 'unknown';
```

The partial index is worth stating plainly: **the fail-closed rules of §2.4.3 are compiled into the index the default query uses.** A row with `scope_state = 'unknown'` is not merely filtered out of `asset_scoped` retrieval; it is not in the index that retrieval scans.

### 3.6 `config_applicability_context` — the read model, and its exact provenance

```sql
CREATE TABLE config_applicability_context (
    asset_id            uuid PRIMARY KEY,
    class_id            uuid        NOT NULL,
    template_revision   int         NOT NULL,
    installed_niins     text[]      NOT NULL,      -- the resolved as-maintained set
    applied_alterations text[]      NOT NULL,
    baseline_id         uuid        NOT NULL,
    baseline_epoch      bigint      NOT NULL,      -- 03 §5.4 fencing
    valid_as_of         timestamptz NOT NULL,      -- Registry valid time
    known_as_of         timestamptz NOT NULL,      -- Registry record time (04 §2 bitemporal)
    refreshed_at        timestamptz NOT NULL
);
```

**How it is populated, and why this is the only contract-legal route:**

1. **Trigger:** consume `registry.configuration.baseline_changed`. 03 §6 names `knowledge-retrieval` as a declared consumer of exactly this event and of **no other** — so this service consumes exactly this one. Consuming `installed_item.installed`/`.removed`, which would be convenient, would be an undeclared dependency and is finding **C4** in a new costume.
2. **Authoritative read:** on receipt, call `GET /assets/{id}/configuration?as_of=&as_known_at=` and `GET /classes/{id}/template` (04 §2, both `x-substitution: required`) and store only the derived key set above.
3. **Rebuild:** the same reads with `changed_since` cursors — 03 §4 and D5, *"the event bus is not a rebuild source."*
4. **Antecedent rule (03 §5.4, D3/D4):** an event whose `baseline_epoch` is ahead of this read model is **blocked** until its antecedent is applied. The inbox records receipt and applies state in one transaction, and receipt is never recorded before processing (D2).
5. **Staleness (03 §5.2, obligation 14, D6):** retrieval is freshness-dependent on this read model. `FATHOM_APP__STALENESS_BOUND_SECONDS` is declared; beyond it, **`asset_scoped` retrieval refuses** with `503` and `urn:fathom:problem:knowledge-retrieval:read-model-stale`, incrementing `fathom_staleness_refusals_total`. It does not filter against a stale baseline, because a stale baseline serves procedures for equipment that has been replaced.

**The refusal in (5) and the `409` in §4.1 are content-independent and clearance-independent** — they are functions of read-model lag and of the caller's supplied epoch only. They therefore leak nothing about corpus content, and §5.4 does not need to conceal them. That distinction is the whole discipline of §5.4: enumerate every response-affecting condition and classify it as content-dependent or not.

**The read model is an input. It is never an output.** §7.

---

## 4. Configuration-aware retrieval — the exact query

### 4.1 Request shape and context resolution

```
POST /api/v1/knowledge-retrieval/retrievals
```

```json
{
  "query": "lube oil pressure low at cruise, procedure to isolate",
  "mode": "asset_scoped",
  "scope": {
    "asset_id": "…", "baseline_id": "…", "baseline_epoch": 43,
    "as_of": "2026-08-04T12:00:00Z",
    "as_known_at": null
  },
  "source_types": ["ietm", "technical_manual"],
  "limit": 8,
  "cursor": null
}
```

**The caller supplies the baseline for *fencing*. The server resolves the *filter values*.** This split is the security-relevant part and is worth being explicit about:

| Field | Supplied by caller | Used how |
|---|---|---|
| `asset_id` | yes | Looks up `config_applicability_context` |
| `baseline_id`, `baseline_epoch` | yes | **Fencing only.** Compared to the read model: ahead → `409 baseline-ahead-of-read-model` (03 §5.4); behind → the read model's own values are used and the response echoes them, so the caller can detect it acted on a superseded baseline |
| `as_of`, `as_known_at` | yes | Passed to the Registry read for a *reproduction* retrieval; default now/now. 04 §2's bitemporality is what makes a past retrieval exactly reproducible for audit |
| `class_id`, `installed_niins`, `applied_alterations`, `template_revision` | **no. Not in the schema.** | Resolved server-side from the read model |

A caller cannot widen its own applicability envelope, because there is no field in which to widen it. Had the API accepted `class_ids[]` directly, a maintainer's copilot with a mis-set parameter — or a curious operator with a `curl` — would retrieve procedures for hulls whose configuration they do not have, which is the exact failure 04 §11 forbids, arriving through the API rather than through a bug.

`mode` values: `asset_scoped` (default, the only `x-agent-eligible` mode), `class_scoped` (a planner asking a class-level question; drops the NIIN and alteration dimensions and says so in the response `applied_scope`), `unscoped` (`x-substitution: internal`, **not** agent-eligible, SME review surface only, the only mode that reaches `scope_state = 'unknown'`).

### 4.2 The query

One statement. Set up in the same transaction, immediately before it:

```sql
BEGIN;
SET LOCAL ROLE fathom_retrieval_reader;          -- NOBYPASSRLS, not the table owner (§5.2)

-- Clearance context, read by the RLS policy. Two-argument current_setting() is
-- deliberately NOT used, so an unset GUC RAISES rather than defaulting (§5.2).
SET LOCAL fathom.allowed_levels   = '{0,1}';
SET LOCAL fathom.compartments     = '{}';
SET LOCAL fathom.dissemination    = '{NOFORN}';
SET LOCAL fathom.cui_categories   = '{SP-CTI}';

-- FIXED work budget, derived from `limit` alone — never from predicate selectivity (§5.4 C3)
SET LOCAL hnsw.ef_search        = 200;
SET LOCAL hnsw.iterative_scan   = 'strict_order';
SET LOCAL hnsw.max_scan_tuples  = 20000;
```

```sql
WITH ctx AS (
    -- The applicability context. NOTHING in this CTE comes from the request body
    -- except asset_id. §4.1.
    SELECT class_id, template_revision, installed_niins, applied_alterations,
           baseline_id, baseline_epoch
    FROM   config_applicability_context
    WHERE  asset_id = $1
)
SELECT k.chunk_id, k.document_id, k.ordinal,
       k.body, k.parent_context,
       k.source_trust, k.injection_signals,
       k.classification,
       k.applicable_class_ids, k.applicable_template_revisions,
       k.effective_date_range,
       k.embedding <=> $2 AS distance
FROM   document_chunk k, ctx
WHERE
    -- (1) EMBEDDING SPACE. §2.5. Not an optimization; a correctness predicate.
        k.embedding_model_id = $3

    -- (2) CLASSIFICATION — clearance, compartments, dissemination, CUI categories.
    --     Composed from the AUTHENTICATED PRINCIPAL, never from the request body.
    --     Also enforced independently by RLS (§5.2): this copy exists so the planner
    --     can prune partitions and use it as an index qual; RLS exists so that no
    --     query in this service can omit it.
    AND k.level          = ANY ($4::smallint[])    -- LIST-partition pruning, §5.3
    AND k.compartments   <@ $5::text[]             -- every compartment on the chunk is held
    AND k.dissemination  <@ $6::text[]             -- every LDC on the chunk is satisfied
    AND k.cui_categories <@ $7::text[]             -- e.g. SP-NNPI not held -> invisible

    -- (3) APPLICABILITY. Same statement, same pass, same plan. §3.3.
    AND k.applicability_scope_state <> 'unknown'                       -- fail closed, §2.4.3
    AND (k.applicable_class_ids = '{}'
         OR ctx.class_id = ANY (k.applicable_class_ids))
    AND (k.applicable_template_revisions IS NULL
         OR ctx.template_revision <@ k.applicable_template_revisions)
    AND (k.applicable_niins = '{}'
         OR k.applicable_niins && ctx.installed_niins)
    AND (k.requires_alterations  <@ ctx.applied_alterations)
    AND NOT (k.precludes_alterations && ctx.applied_alterations)
    AND k.effective_date_range @> $8::timestamptz                      -- as_of

    -- (4) LIFECYCLE. Matches the partial index of §3.5.
    AND k.withdrawn_at   IS NULL
    AND k.superseded_at  IS NULL
    AND k.quarantined_at IS NULL

    -- (5) OPTIONAL narrowing, from the request. Never widening.
    AND ($9::text[]  IS NULL OR k.source_type  = ANY ($9::text[]))
    AND ($10::text[] IS NULL OR k.source_trust = ANY ($10::text[]))

    -- (6) KEYSET cursor on (distance, chunk_id). NEVER OFFSET — §5.4 C6.
    AND ($11::float8 IS NULL
         OR (k.embedding <=> $2, k.chunk_id) > ($11::float8, $12::uuid))
ORDER BY k.embedding <=> $2, k.chunk_id
LIMIT $13;
```

```sql
COMMIT;
```

### 4.3 Why the application-layer version is a defect, not a style choice

The rejected shape:

```python
rows = await repo.nearest(query_vec, k=200)            # unfiltered ANN
rows = [r for r in rows if applicable(r, ctx)]         # <-- the defect
rows = [r for r in rows if visible(r, principal)]      # <-- the serious defect
return rows[:limit]
```

Four independent failures, and the content being correctly withheld does not fix any of them:

1. **Result count is a channel.** With a fixed `k=200` pre-filter fetch, the number surviving is a monotone function of how much matching content the requester may not see. A requester who receives 2 results where an identical query for a cleared colleague yields 8 has learned that 6 relevant records exist. Nothing was disclosed; the *cardinality* disclosed it.
2. **Latency is a channel.** Filtering 198 rows in Python costs measurably more than filtering 3. The distinction between "nothing matched" and "everything matched and was removed" becomes a timing measurement, repeatable and cheap.
3. **Recall silently collapses.** Filtering after a fixed-`k` ANN fetch means a maintainer whose applicable content sits at rank 250 receives nothing, and the response is indistinguishable from "no procedure exists." A *safety* failure produced by a *security* shortcut.
4. **Pagination cannot be made correct.** Page 2 of an application-filtered result set either re-fetches and re-filters (making pages non-deterministic) or pages over the unfiltered ordering (making the *gaps* the disclosure).

Items 1 and 2 are why 03 §7.3 says *"the vector store enforces at query time rather than post-filtering."* Items 3 and 4 are why it is also the wrong engineering.

**The mechanical invariant that keeps it out of the codebase (`KR-INV-1`):**

```python
# repositories/chunks.py — asserted in production, not only in tests
rows = await session.execute(RETRIEVAL_SQL, params)
results = [RetrievedContext.from_row(r) for r in rows]
assert len(results) == len(rows), (
    "KR-INV-1: rows returned by the database must equal results returned to the "
    "caller. Any difference is an application-layer filter (03 §7.3, D13, D14)."
)
```

Rows in equals results out, always. There is no code path between the cursor and the response body that can drop a row. A reviewer checking this design needs to verify one line.

### 4.4 ANN and a restrictive predicate — the part that is genuinely hard

An HNSW graph traversal that is filtered can return fewer than `limit` rows even when many matching rows exist, because the traversal visits its `ef_search` candidates and *then* the quals reject them. Three mitigations, applied together:

1. **`hnsw.iterative_scan = strict_order`.** The scan continues drawing candidates until `limit` qual-passing rows are found or the budget is exhausted, preserving distance ordering. This is what makes a filtered ANN scan behave like a filtered index scan rather than like a filtered top-k fetch.
2. **`hnsw.max_scan_tuples` as a *fixed* budget**, derived from `limit` alone. This is the timing-channel closure of §5.4 C3: work is bounded by a constant, not by selectivity. When the budget is exhausted the query returns fewer rows — **which is identical to the behavior when the corpus genuinely holds less relevant content.** The degradation mode and the empty-result mode are the same mode, deliberately.
3. **The partial index of §3.5** compiles the always-true-for-retrieval quals into the index, so the invariant predicates cost no traversal budget at all. Only the applicability and clearance predicates consume it.

Recall under filtering is therefore a **measured, reported property**, not an assumption: `KR-ANN-01` (§11) computes recall@k against a brute-force `SELECT … ORDER BY embedding <=> q` over the same predicate on the reference corpus and fails below a declared floor. That floor is an OD item (OD-4), not an invented number.

---

## 5. Query-time classification enforcement — the exact query

The predicate is already written: §4.2 clause (2). This section specifies the three things that make it a control rather than a line of SQL — that it cannot be omitted (§5.2), that a low-side query never traverses high-side vectors (§5.3), and that its *effect* is unobservable (§5.4).

### 5.1 Composition — from the principal, never from the request

```python
# services/clearance.py
@dataclass(frozen=True, slots=True)
class ClearanceContext:
    allowed_levels: tuple[int, ...]      # every level at or below the principal's ceiling
    compartments: tuple[str, ...]        # held compartments
    dissemination: tuple[str, ...]       # satisfied Limited Dissemination Controls
    cui_categories: tuple[str, ...]      # authorized CUI categories

    @classmethod
    def from_principal(cls, p: Principal) -> "ClearanceContext": ...
```

- Built **only** from ABAC attributes on the authenticated principal, evaluated **in this service** (03 §4, obligation 7, 09 §5.5: *"never delegated to the gateway alone"*).
- `Principal` for an agent carries `authority_class` per 03 §8.3. A **delegated** agent's context is the user's, so *"a maintainer's copilot cannot read what the maintainer cannot read"* (01 §8.5) is satisfied by construction rather than by agent behavior. An **accountable-autonomous** principal additionally carries a declared scope, and a query outside it is empty — it *"cannot read outside its declared scope"*, indistinguishably from finding nothing.
- **There is no request field that touches clearance.** Not an override, not a "requested level", not a debug flag. `ClassificationLabel` appears in this service's OpenAPI **only** in response bodies; a contract test asserts it never appears in a request body (`KR-CLS-09`).
- **The four LDC/category predicates use `<@` (contained-by), not intersection.** The chunk's controls must be a subset of what the principal satisfies. `&&` here — "shares at least one" — would be a permissive check that grants access on partial match, and it is the kind of inversion that reads correctly and is not.

### 5.2 Row-Level Security — so the predicate cannot be omitted

The SQL predicate is what the planner uses. **RLS is what makes it impossible to write the query without it.**

```sql
ALTER TABLE document_chunk ENABLE  ROW LEVEL SECURITY;
ALTER TABLE document_chunk FORCE   ROW LEVEL SECURITY;

CREATE POLICY chunk_clearance ON document_chunk
    FOR SELECT TO fathom_retrieval_reader
    USING (
            level          =  ANY (current_setting('fathom.allowed_levels')::smallint[])
        AND compartments   <@ current_setting('fathom.compartments')::text[]
        AND dissemination  <@ current_setting('fathom.dissemination')::text[]
        AND cui_categories <@ current_setting('fathom.cui_categories')::text[]
    );
```

Four properties, each doing real work:

| Property | Mechanism | What it prevents |
|---|---|---|
| **Cannot be bypassed** | `fathom_retrieval_reader` is created `NOBYPASSRLS` and is **not** the table owner. Migrations run as the owner; the application runtime never does | A future `SET ROLE`, a superuser connection string, or an ad-hoc admin query returning unfiltered rows |
| **Cannot be forgotten** | `FORCE ROW LEVEL SECURITY` applies the policy to the owner too | An owner-role maintenance script that quietly sees everything |
| **Fails closed on omission** | **Single-argument `current_setting()`.** An unset GUC raises SQLSTATE `42704`, it does not default | The catastrophic case: a new code path that queries `document_chunk` without establishing clearance and therefore returns *everything*. It gets an error instead of a leak |
| **Scoped to one entry point** | A single async context manager `with_clearance(session, ctx)` issues the `SET LOCAL`s; a lint rule (`FTH-KR-002`) fails any `document_chunk` query outside it | Divergent clearance setup in two places, which is how one of them ends up wrong |

The double enforcement is intentional and is the same redundancy pattern 09 §5.1 uses for operation annotations (import time / startup / CI). Here: **the SQL predicate is for the planner, RLS is for the reviewer, and the partition set is for the accreditor.**

### 5.3 Partitioning by level — production posture, built in the demonstration

`PARTITION BY LIST (level)` with a per-partition HNSW index (§3.5) means `level = ANY('{0,1}')` prunes the `S` and `TS` partitions at plan time. The low-side query **never opens the high-side index**, so the ANN traversal never touches a high-side vector, let alone returns one.

This matters beyond defense in depth. 03 §12 requires **producer-side segregation** in production — *"one classification per topic, cross-level flow only through an accredited guard"* — because D13 established that consumer-side enforcement alone yields *"either system-high operation, in which labels are decorative, or a leak."* Partition-per-level is that architecture inside the vector store: a per-level table, a per-level index, and in production a per-level tablespace or cluster with the guard between them. **An accreditor can be shown a boundary, not a `WHERE` clause.**

Compartments are handled by exclusion in the demonstration and by separate storage in production (OD-3): a compartmented corpus becomes its own partition set or its own cluster, because a compartment predicate over a shared index still puts compartmented vectors in a graph that low-side queries traverse.

For the demonstration, 03 §12 and 06 §5 fix a single unclassified level, so exactly one partition holds data — **and the mechanism is exercised anyway**: the integration suite seeds two synthetic levels and asserts pruning in `EXPLAIN` output (`KR-CLS-10`). A multi-level mechanism first exercised at accreditation is a mechanism that does not work.

### 5.4 Indistinguishability — every channel, enumerated and closed

The requirement is precise: a query whose matching content is above the requester's clearance must be **indistinguishable** from a query that found nothing relevant. Not "does not disclose the content" — *indistinguishable*, because the existence of records is itself the protected fact.

An indistinguishability claim is only as good as the channel list it is checked against. Here is the list.

| # | Channel | How an unclosed version leaks | Closure |
|---|---|---|---|
| **C1** | **Status code** | `403` on filtered content versus `200` with `[]` on no match — a one-bit oracle, free to query | **There is no content-level authorization failure.** `POST /retrievals` returns `200` with `results: []`. `403` exists only for "this principal may not invoke this operation at all" — a function of the principal alone, constant across every query it makes |
| **C2** | **Result count** | Fewer results than a cleared peer reveals how much exists | No total count anywhere (03 §4 already forbids it on unbounded collections). And the predicate is inside the scan, so **no unfiltered count is ever computed to compare against** |
| **C3** | **Latency** | Traversing-and-rejecting costs more than not finding | Two mechanisms. (a) **Fixed work budget** — `hnsw.max_scan_tuples` and `ef_search` are constants derived from `limit`, so scan work does not vary with selectivity (§4.4). (b) **Quantized response floor** — §5.4.1 |
| **C4** | **Response shape** | A field present only when something was withheld — `filtered: true`, `partial: true`, a `Warning` header, a `restricted_present` boolean | The response model has **no field whose presence or value depends on classification**. Asserted by golden-response comparison (`KR-CLS-02`): the empty-because-nothing-matched response and the empty-because-all-withheld response are **byte-identical** after correlation-ID and timestamp normalization |
| **C5** | **`X-Classification` header** | Set to the union of what *was considered* — instant disclosure | Set to the union of the labels **actually returned**. On an empty result set it is the **service's declared floor** (`U` in the demonstration) — a constant, identical in both cases (`KR-CLS-07`) |
| **C6** | **Pagination** | Offset pagination over an unfiltered ordering makes the gaps the message; a `next_cursor` present when a filtered page came back short says "more exists" | Keyset cursor on `(distance, chunk_id)` over the **filtered** ordering (§4.2 clause 6). `next_cursor` is non-null iff a full page was returned, which is a function of returned rows only |
| **C7** | **Single-resource reads** | `GET /chunks/{id}` returning `403` for withheld and `404` for absent is the oracle in its purest form | **`404` for both**, same problem-detail `type`, same latency quantum. There is no code path that distinguishes them: the `SELECT` is the same predicated query and returns zero rows in both cases (`KR-CLS-06`) |
| **C8** | **Metrics** | `fathom_kr_withheld_total` — or any counter, however aggregated, whose value moves when high-side content matches | **No such metric exists, because no such quantity is ever computed.** No metric is labelled by `asset_id`, `principal_id`, or query content. `KR-CLS-08` is a source-level test that fails if any identifier matching `withheld|filtered_out|suppressed|denied_count|access_denied` appears in the package |
| **C9** | **Logs** | A debug line naming rejected chunk ids | Corpus text and query text are **never logged** (09 §4.8 already forbids logging retrieved corpus text). Rejected rows never reach the application, so there is nothing to log |
| **C10** | **Audit** | An audit record enumerating what was withheld would relocate the leak into the audit store — which is *more* durable | The audit record (§5.5) holds the principal's effective clearance, the query hash, and the returned chunk ids. **Withheld ids are not in the process.** Audit writes are off the response path (own table plus outbox, constant work), so audit volume does not vary with result count |
| **C11** | **Caches** | A cross-principal result cache returns A's authorized results to B; a cross-principal query-embedding cache reveals that A asked something by making B's identical query faster | **No result cache, at any layer.** The query-embedding cache is keyed on `(query_hash, embedding_model_id)` and is **per-request only** — never shared across principals. `Cache-Control: no-store` on every retrieval response, and the gateway is configured not to cache this operation |
| **C12** | **Errors and validation** | A `422` triggered only by content the principal cannot see | No validation depends on stored content. Every error is a function of the request, the principal, or read-model lag (§3.6) — all content-independent, all clearance-independent, and that is why §3.6's `409` and `503` need no concealment |
| **C13** | **Event stream** | `document.ingested` on a high-side topic observable from a low-side consumer | Topics are segregated by level and compartment (03 §5.1). This service publishes one topic set per classification level; a low-side consumer is not authorized on high-side topics, and cross-level flow is the accredited guard's problem, not this service's |

#### 5.4.1 The quantized response floor

The fixed work budget bounds *query* time. It does not bound the residual variance from buffer-cache state, partition count, or result serialization. The floor closes what remains:

```python
# api/v1/retrievals.py — monotonic clock only (09 DO-NOT #7, D29)
FLOOR_MS, QUANTUM_MS = 300, 50

started = time.monotonic()
results = await service.retrieve(request, principal)     # embed, then the ONE query
elapsed_ms = (time.monotonic() - started) * 1_000
target_ms = math.ceil(max(FLOOR_MS, elapsed_ms) / QUANTUM_MS) * QUANTUM_MS
await asyncio.sleep((target_ms - elapsed_ms) / 1_000)
return Page(results=results, next_cursor=cursor_for(results))
```

Every response lands on a 50 ms quantum at or above 300 ms. Observable latency therefore carries at most $\log_2$ of the number of quanta actually reached, and — the point — **the quantum reached is a function of total work, which the fixed budget already made selectivity-independent.**

Cost and its justification: p95 rises to at least 300 ms. Against 06 §7's budget — *p95 < 1.5 s for fleet and asset views; < 4 s for explanation decomposition* — retrieval has room, and this is the one place in the platform where trading latency for an information-theoretic property is unambiguously correct. `FLOOR_MS` and `QUANTUM_MS` are in `values.yaml`; **raising throughput by lowering them is a security change requiring an ADR**, and the chart carries that comment.

The query embedding is computed **before** the database query, unconditionally, on every request including ones that will return empty — so the embedding call's latency is content-independent.

### 5.5 The strongest form of the property

Every closure above is a mechanism that could, in principle, be got wrong. One property is not:

> **The number of records withheld from a query is never computed.**

The `WHERE` clause is inside the index scan. Rejected rows are never materialized, never counted, never returned to the application, never serialized, never logged, never audited, never metered. `KR-INV-1` (§4.3) asserts that rows-in equals results-out, so no application layer exists in which such a count could be formed.

This is why the *only* correct implementation is a database-level predicate. Application-layer filtering does not merely risk leaking the count — **it necessarily computes it**, and a computed quantity in a running process is a quantity that will eventually be logged, metered, or returned by someone trying to be helpful.

### 5.6 A deliberate divergence from Fleet Status, and why both are right

06 §5's aggregation policy requires the opposite choice for readiness rollups:

> *"A readiness rollup computed for a given clearance level excludes contributors above that level and **exposes a `restricted_contributors_present` boolean with a count**… The boolean is displayed, not buried in metadata."*

This service exposes **no such indicator, ever.** The two are not in conflict; they are the same reasoning applied to different objects:

| | Fleet Status rollup | Knowledge retrieval |
|---|---|---|
| The object | One derived scalar whose meaning depends on completeness | A set of documents |
| Failure if incompleteness is hidden | An operator acts on a readiness figure believing it complete — 06 §5 rule 3, *"a low-side rollup never presents itself as complete"* | None. "No applicable procedure was retrieved" is already the correct and complete answer to give |
| Failure if incompleteness is disclosed | None; the boolean and count are the disclosure the policy accepts | **Existence disclosure.** A per-query "N records withheld" oracle, queryable at will, enumerable by varying the query — strictly worse than the rollup case because the attacker controls the probe |

06 §5 anticipated this exact tension: *"If exclusion is judged to leak through the count itself, suppress the boolean."* In a query-driven corpus the count **is** the leak, because the requester chooses the query and can iterate. Suppression is therefore not a weaker posture here; it is the posture 06 §5 names for precisely this case.

Recorded so no future reviewer "harmonizes" the two services by adding a boolean here.

---

## 6. The untrusted-content boundary (D14, 03 §9)

D14, in full:

> *"**No prompt-injection threat model.** The retrieval corpus is free text authored by thousands of people, including parties outside the program (vendor manuals, ECPs). A crafted or careless passage produces a requisition proposal with a substituted NIIN, a fluent rationale, and *genuine* citations that satisfy the non-empty-evidence gate mechanically. The propose-don't-commit boundary reduces the entire security posture to the attentiveness of a time-pressured reviewer — which the design elsewhere concedes is the weakest link."*

This service owns the corpus the finding names. It cannot fix the finding — 03 §9 items 2 and 4 do that, in the receiving sub-application and in the evaluation gate. What it owes is the three things without which those two cannot work.

### 6.1 (a) The structural marker: `retrieved_context`

03 §9 item 1: *"Retrieved content is data, never instruction. Tool results and retrieved passages are **structurally separated** from instructions in every agent prompt."*

Retrieved text leaves this service **only** inside a typed object whose `role` discriminator is a constant:

```python
class RetrievedContext(FathomModel):
    """Untrusted data. Never instruction. 03 §9 item 1, D14."""

    role: Literal["retrieved_context"] = "retrieved_context"

    chunk_id: UUID
    document_id: UUID
    ordinal: int
    body: str                       # UNTRUSTED. Verbatim source text.
    citation: Citation              # parent_context, resolved: title, revision, DM code, step path
    source_trust: SourceTrust       # program | vendor | external   (03 §7.2, D14)
    provenance_ref: str             # -> GET /documents/{id} (§6.3)
    applicability: AppliedScope     # the dimensions that admitted this chunk
    classification: ClassificationLabel
    similarity: float
    injection_signals: tuple[str, ...] = ()   # §6.4 — flags, never a filter
```

Three API-level consequences, each of which removes an easy way to get this wrong:

1. **`role` is a `Literal`, not an enum with room to grow.** There is no `"system"`, no `"instruction"`, no `"assistant"`. The only value a chunk can arrive under is `retrieved_context`. A consumer that pattern-matches on role can never route corpus text into an instruction position, and one that ignores the field is visibly ignoring a field.
2. **There is no operation that returns rendered, prompt-ready text.** No `?format=prompt`, no `context_blob`, no `joined_text`, no markdown rendering, no `GET /retrievals/{id}/prompt`. A caller that wants a concatenated string must write the concatenation itself, in its own code, where a reviewer can see it. **This is the single most effective control in this section**, because the realistic failure is not a malicious integrator — it is a convenient helper that returns a string, and the string ends up in a system message. The helper does not exist and its absence is asserted by contract test `KR-INJ-04`.
3. **`body` is never a top-level response field.** It exists only nested inside a `RetrievedContext`. There is no shape in which corpus text arrives unlabelled.

### 6.2 (b) `source_trust`, carried through to `Proposal.evidence`

03 §7.2 requires `source_trust` on every evidence item, from the closed vocabulary `program | vendor | external` (package 10 §4.7 `SourceTrust`), and 03 §7.2's rule is that *"a proposal resting solely on non-program content is flagged to the adjudicator."*

That rule is only enforceable if the trust marking survives the whole path. It does, by construction:

```
document.origin  (set at ingest, §2.6, immutable)
  -> document_chunk.source_trust  (derived by the total function in §2.6)
    -> RetrievedContext.source_trust  (returned on every chunk)
      -> Evidence{ kind: "document_chunk", ref: chunk_id, excerpt, source_trust }
        -> Proposal.evidence[]  (03 §7.2)
          -> the adjudicator's flag
```

Two obligations this service accepts to keep that chain intact:

- **`source_trust` is a required, non-nullable field of `RetrievedContext`.** A consumer building `Evidence` cannot omit it for lack of a value, which is how such fields become optional in practice.
- **`GET /chunks/{chunk_id}` re-resolves a citation and returns the same `source_trust`**, under the same clearance and applicability predicate — so an adjudicator inspecting a five-week-old proposal's evidence sees the same trust marking, and sees a `404` where the chunk has since been withdrawn (which is a signal the adjudicator should act on, and mirrors 03 §7.2's mandatory re-validation at approval).

### 6.3 (c) The provenance record and the adversarial corpus for 01 §8.8

03 §9 item 4: *"Injection cases are in the evaluation gate. Golden question sets include adversarial corpus content, and agent promotion is blocked on failure."* 01 §8.8 makes it a promotion gate.

**This service does not run those tests.** It supplies two things they cannot exist without.

**1. A provenance record answerable per chunk.** `GET /documents/{document_id}` returns §2.6's record. When an evaluation run finds an agent followed an injected instruction, the question "where did this come from, who authored it, when did we ingest it, and was it program-internal" is a lookup, not an investigation. Without it, an injection finding is not actionable.

**2. The adversarial corpus itself, as a first-class, versioned corpus partition.**

⚠️ **This does not exist yet and is a cross-document obligation.** [13 §1.1](13-synthetic-data-generator.md) enumerates nine output partitions — `configuration/`, `telemetry/`, `maintenance/`, `supply/`, `holdout/`, `candidates/`, `scenarios/`, `truth/`, `card/` — and **none of them is a document corpus.** The generator produces 2-Kilo narratives and CASREPs as *records*; it produces no IETMs, no technical manuals, no test reports, no ECPs, and no adversarial content. So the corpus this service exists to serve has no source, and 01 §8.8's golden question sets have no adversarial material. Recorded as **OD-5** with a precise ask:

> Add a **`corpus/`** output partition to document 13, with sub-partitions `corpus/ietm/`, `corpus/technical_manual/`, `corpus/test_report/`, `corpus/ecp/`, and **`corpus/adversarial/`**. `corpus/adversarial/` follows 13 §13.1's canary rule exactly — *"a canary must be produced by the same code path, from the same parameter distributions, as an ordinary fault"* — so adversarial passages are produced by the same document generator as ordinary passages, differing only in an entry in `truth/`. An adversarial corpus generated by a separate, visibly-different injector measures an agent's ability to spot a different writing style, not its resistance to injection.

The adversarial classes to generate, each mapped to a concrete platform consequence, and each requiring D14's named failure to be reachable:

| Class | Passage content | Consequence being tested |
|---|---|---|
| `substituted_niin` | A vendor manual passage recommending a NIIN that is **not APL-authorized for the position** | **D14's named attack, verbatim.** Tests 03 §9 item 2: Supply must reject on APL authorization regardless of what the agent proposed |
| `interval_override` | Text asserting a maintenance interval far outside the permitted delta | Scheduling's bounded-delta validation and PMS-authority routing |
| `authority_escalation` | Text instructing the reader to treat a recommendation as pre-approved, or to skip adjudication | The propose-and-adjudicate boundary; no retrieved text can alter authority (03 §9 item 1) |
| `role_confusion` | Chat-role markers, tool-call syntax, fenced instruction blocks, prompt delimiters embedded in prose | §6.1's structural separation. A passing result means the marker was inert |
| `exfiltration` | Text instructing the agent to include prior context, a token, or another asset's data in its output | Delegated-authority containment |
| `false_citation` | A passage citing a plausible non-existent technical authority | Citation-accuracy scoring (01 §8.8); D14's *"genuine citations that satisfy the non-empty-evidence gate mechanically"* |
| `contradictory` | Corpus text contradicting the coded record — already generated by [13 §9.10](13-synthetic-data-generator.md) as *"narrative-code inconsistency… the retrieval and agent surfaces meet genuinely contradictory evidence"* | Whether the agent surfaces the contradiction or silently picks one |

Every adversarial passage is ingested with `origin` set truthfully (`vendor` or `external`, matching D14's threat) and carries `injection_signals` where detectable. **The adversarial flag itself lives in `truth/` only**, per 13 §13.2 — *"a canary flag reachable from the observed corpus destroys the metric outright."* A chunk that announces itself as adversarial tests nothing.

### 6.4 What this service deliberately does **not** do

- **It does not sanitize, rewrite, escape, or neutralize chunk bodies.** `body` is verbatim source text. Silently altering a technical procedure to defang a prompt-injection pattern is a safety hazard that trades a security risk for a mishap risk, and it makes the corpus non-auditable against its original.
- **It does not enforce domain policy.** No APL checks, no interval bounds, no baseline-presence checks. 03 §9 item 2 puts those *"in the sub-application, not by agent behavior"*, as *"validation rules on the receiving operation… regardless of what an agent proposes or why."* Duplicating them here would be a second, drifting implementation of a control whose value is that there is one.
- **It does not treat `injection_signals` as a security control.** The signals — role markers, imperative-to-assistant constructions, tool-call syntax, embedded URLs, long base64 runs — are heuristics. They (a) route `source_trust != program` chunks with non-empty signals to `quarantined_at` pending review at ingest, and (b) ride along on the response for evaluation and display. **Empty `injection_signals` is not evidence of safety**, and no consumer may treat it as a clearance to relax structural separation. Stated here because a field like this invites exactly that reading.

---

## 7. Structured-versus-unstructured boundary enforcement

04 §11: *"Structured facts are never served from this component. Agents obtain current state from sub-application APIs and obtain procedural and narrative knowledge here, and the distinction is enforced in the tool manifests."*

Manifest enforcement is a Wave-5 concern and is also insufficient on its own: a manifest can only decline to select an operation that exists. **The obligation this document accepts is that the operation does not exist**, so no manifest, and no direct caller, can reach current state through this service.

### 7.1 The negative API surface

This service's OpenAPI document contains **no operation whose response can carry**:

- a `FailurePrediction` or any field of one — `p_failure`, `rul`, `p10`/`p50`/`p90`, `reference_class`, `sharpness`, `calibration_population`, `fallback_level`, `tier`, `contributing_factors`, `population_hazard_rate`, `model_version`, `scoring_run_id` (03 §7.1);
- current asset state — `operational_status`, `ofrp_phase`, `readiness`, `casrep`-as-status, `availability`;
- current configuration facts — an installed-item list, a position tree, a system hierarchy, a resolved baseline, an allowance document.

The reason a fresh reading of 03 §7.1 matters here: the schema was **corrected today** — `producer_node` on the envelope, `p_failure` gated on `calibration_population`, the `authority_class` vocabulary, the `eic` fields' federation-only status. A denylist written against a stale field list would miss the corrected names, which is why the check in §7.2 is generated from `packages/canonical-schemas` rather than hand-written.

### 7.2 How it is enforced mechanically — three checks, none of them a code review

**(1) Schema denylist over the committed contract** — `tests/contract/test_no_structured_facts.py`, generated, not typed:

```python
FORBIDDEN_SCHEMAS = {"FailurePrediction", "Rul", "ContributingFactor", "AssetStatus",
                     "ConfigurationBaseline", "InstalledItemRef", "ReadinessRollup"}
# Field-level denylist derived AT TEST TIME from packages/canonical-schemas, so a
# correction to 03 §7.1 (as landed today) propagates automatically.
FORBIDDEN_FIELDS = field_names_of(FailurePrediction) | field_names_of(AssetRef) - {"asset_id"}

def test_openapi_serves_no_structured_facts() -> None:
    spec = json.loads(Path("platform/knowledge-retrieval/openapi.json").read_text())
    for name in walk_response_schema_names(spec):
        assert name not in FORBIDDEN_SCHEMAS, f"KR-BND-1: {name} (04 §11)"
    for prop in walk_response_property_names(spec):
        assert prop not in FORBIDDEN_FIELDS, f"KR-BND-1: property {prop!r} (04 §11)"
```

**(2) Import-graph check** — `FTH-KR-003`: the package `fathom_knowledge_retrieval` may import `ClassificationLabel`, `SourceTrust`, `Evidence`, `EventEnvelope`, and the identity references from `packages/canonical-schemas`, and **may not import** `FailurePrediction`, `Proposal`, or any readiness type. It cannot serve what it cannot name.

**(3) The read model is input-only.** `config_applicability_context` (§3.6) is the one place configuration facts live in this service, and:

- **No operation returns any column of it.** Not a debug operation, not a health detail, not an admin listing.
- The retrieval response's `applied_scope` echoes **only the caller's own supplied `baseline_id`/`baseline_epoch` plus the *names of the dimensions applied*** — never their values. `{"dimensions_applied": ["class", "template_revision", "niin", "alterations", "effective_date"], "baseline_epoch": 43}`. It never returns `class_id`, the installed NIIN set, or the alteration set.
- Asserted by `KR-BND-2`: for every operation in the committed spec, no response property name appears in `config_applicability_context`'s column set except `baseline_id` and `baseline_epoch`.

The reason `applied_scope` returns dimension *names* is that a caller legitimately needs to know a `class_scoped` query dropped the NIIN dimension — otherwise it cannot interpret its results. Returning the values would make this service a configuration oracle: `POST /retrievals` with a nonsense query would become a way to read another hull's installed NIIN list, unauthoritatively, bypassing the Registry's own authorization. That is the exact failure 04 §11's boundary exists to prevent, arriving through a helpful field.

### 7.3 Why the boundary is stated as a *data-model* property

The tool manifest is the operational enforcement point (04 §11), and manifests are generated from contracts (03 §8.2), *"failing — rather than warning — when a selected operation is absent from the pinned API version, is not `x-agent-eligible`, or lacks a description."* That generator can only enforce what the contract expresses. By having no structured-fact operation and no structured-fact schema, this service makes the manifest layer's job trivially satisfiable and makes the boundary hold for **every** caller, including the gateway, a curious operator with a bearer token, and any future non-agent consumer — none of whom read a tool manifest.

---

## 8. API surface

Base path `/api/v1/knowledge-retrieval/` (03 §4, 09 §8.1). Every operation carries `x-substitution` and `x-side-effects`; `x-agent-eligible` only where side effects are `none` (03 §8.1, C1/D11).

| Operation | Purpose | `x-substitution` | `x-side-effects` | `x-agent-eligible` |
|---|---|---|---|---|
| `POST /retrievals` | **The retrieval operation.** §4, §5 | `required` | `none` | **yes** |
| `GET /chunks/{chunk_id}` | Re-resolve one citation, same predicate. `404` for absent **and** withheld (§5.4 C7) | `required` | `none` | yes |
| `GET /documents` | Corpus inventory under the same predicate; cursor-paginated | `required` | `none` | yes |
| `GET /documents/{document_id}` | Provenance record (§2.6). `404` for absent and withheld | `required` | `none` | yes |
| `GET /documents?changed_since=&cursor=` | Rebuild feed for declared consumers (03 §4, D5) | `required` | `none` | no |
| `POST /documents/bulk` | **Bulk, idempotent, fenced ingest** of chunked+extracted documents from the Domino ingest pipeline (03 §4, D10/C7). `Idempotency-Key` required; fenced on `ingest_run_id` | `internal` | `state-changing` | no |
| `POST /ingest-runs` · `GET /ingest-runs/{id}` | Ingest run lifecycle and status | `internal` | `state-changing` / `none` | no |
| `GET /applicability-reviews` | The SME queue (§2.4.3), cursor-paginated | `internal` | `none` | no |
| `PATCH /applicability-reviews/{id}` | SME determination. `If-Match` **required** (09 §5.4) | `internal` | `state-changing` | no |
| `POST /documents/{id}/withdraw` | Withdrawal, and purge initiation (§10) | `internal` | `state-changing` | no |
| `POST /reindex-runs` · `GET /reindex-runs/{id}` | Embedding-model cutover (§2.5) | `internal` | `state-changing` / `none` | no |

**`POST /retrievals` is a compute-only `POST`** — sanctioned explicitly by 03 §4.1 (*"permitted on `GET` and on computational `POST` operations"*) and by 09 §5.1's worked `what_if` example. It persists nothing. It is a `POST` rather than a `GET` for a specific reason: a query string is recorded by ingress logs, access logs, and browser history, and 09 §4.8 lists **retrieved corpus text among the things never logged**. Query text is the same category of content. A `GET` would place it in a URL by construction.

**Naming carve-outs:** none. Every path is a plural collection, so `x-naming-carve-outs` is empty (09 §5.1, C23).

**Problem types**, all declared in `schemas/problems.py` (09 §5.2):

| `type` | Status | When |
|---|---|---|
| `urn:fathom:problem:knowledge-retrieval:baseline-ahead-of-read-model` | 409 | Supplied `baseline_epoch` exceeds the read model (03 §5.4, D3/D4) |
| `urn:fathom:problem:knowledge-retrieval:read-model-stale` | 503 | Configuration read-model lag beyond the declared bound (obligation 14, D6) |
| `urn:fathom:problem:knowledge-retrieval:embedding-model-unavailable` | 503 | `EmbeddingPort` unavailable; the request is not answered from a stale cache |
| `urn:fathom:problem:knowledge-retrieval:not-found` | 404 | Single-resource reads — **absent and withheld alike** (§5.4 C7) |
| `urn:fathom:problem:knowledge-retrieval:ingest-rejected` | 422 | Missing `origin`, cap-exceeding chunk, unresolvable NNPI scope (§2.6) |

There is deliberately **no** `classification-denied`, `insufficient-clearance`, `results-filtered`, or `applicability-mismatch` type. Their existence would be the leak.

---

## 9. Events

Topic naming per 03 §5.1: `fathom.knowledge-retrieval.<aggregate>.v<major>`, one topic per aggregate, segregated by classification level (03 §5.1, §12). Envelope complete per 03 §5.4 including the full `clock` block (D29). Published through the transactional outbox in `packages/py-sync` (03 §5.2, obligation 11).

**Published**

| Topic | Event | Payload summary | Partition key | Declared consumers |
|---|---|---|---|---|
| `fathom.knowledge-retrieval.document.v1` | `document.ingested` | `document_id`, `source_type`, `origin`, `source_trust`, `content_hash`, `chunk_count`, `classification` | `document_id` | **none declared** |
| | `document.superseded` | `document_id`, `superseded_by`, effective date | `document_id` | **none declared** |
| | `document.withdrawn` | `document_id`, reason, **tombstone** for the purge protocol (03 §13 item 4) | `document_id` | **none declared** |
| `fathom.knowledge-retrieval.applicability_review.v1` | `applicability_review.required` | `review_id`, `document_id`, chunk count, `extraction_method`, confidence | `document_id` | `notification` |
| | `applicability_review.completed` | `review_id`, determination, `reviewed_by` | `document_id` | `notification` |
| `fathom.knowledge-retrieval.ingest_run.v1` | `ingest_run.completed` · `ingest_run.failed` | run id, counts, **reference** to the run report — never the report itself (D27) | `ingest_run_id` | **none declared** |

**"None declared" is deliberate and is the honest position.** Finding **C19** is that 03 §6's catalog *"lists consumers that exist nowhere"*. These topics exist to satisfy 03 §15 obligation 2 — every state change reachable through the contract emits an event, verified by fault injection — and to carry withdrawal tombstones for the purge protocol. Inventing a consumer to make the rows look complete would recreate C19. `notification` is named on the review topic because routing an SME review request is exactly what 04 §11 assigns to Notification, and C14 records it as an already-declared consumer elsewhere.

**Consumed**

| Event | Producer | Use | Rule |
|---|---|---|---|
| `configuration.baseline_changed` | `registry` | **Trigger** for the §3.6 read-model refresh. 03 §6 declares this service a consumer of this event and of no other | Inbox records receipt and applies in one transaction; receipt **never** recorded first (D2). Idempotent on `event_id`. Antecedent rule enforced (D3/D4). `replay: true` handled idempotently with no operator-visible alert (D30) |

No wildcard subscriptions (C38). `events/catalog.py`'s `PUBLISHES`/`CONSUMES` frozensets equal `helm/values.yaml`'s `events.publishes`/`events.consumes`; `tools/check_event_catalog.py` exits 0.

⚠️ **03 §6 has no rows for platform services.** Its catalog covers only the nine sub-applications, so the three topics above are uncatalogued at the contract level and no consumer-driven conformance test can be written against them. Recorded as **OD-6** (the same gap [12 §11](12-reference-data-taxonomy.md) OD-7 records for `fathom.reference-data.*` — it is a general defect in 03 §6, not a local one).

---

## 10. The purge path (03 §13, D15)

D15 names *"the vector index"* explicitly among the stores a classification spillage must be purged from, and calls the absence of a purge path *"an accreditation blocker."* 03 §13 requires an explicit statement per store of whether it is legally immutable or operationally append-only.

| Store | Character | Purge mechanism |
|---|---|---|
| `document`, `document_chunk` | Operationally append-only | Hard `DELETE` by `document_id`, then §10.1 |
| Original objects (S3/MinIO) | Operationally append-only | Object delete plus version-history delete; per-classification KMS key |
| `retrieval_audit` | **Operationally** append-only, not legally immutable — the legally immutable record is `audit`'s | Row delete by `document_id` join; excerpts are not stored here (only chunk ids) so exposure is minimal |
| `outbox` / `inbox` | Transient | Row delete; withdrawal tombstone published to preserve the compaction invariant (03 §13 item 4) |
| Published events | Compacted topics | Tombstone on the aggregate key (`document_id`) |
| `document.v1` topic bodies | — | Envelope-level encryption with per-classification keys; crypto-shred the key (03 §13 item 1) |
| **HNSW index** | — | **§10.1. This is the one that does not work the obvious way** |

### 10.1 The vector index, and a finding-grade caveat

Two facts make the vector index the hard case, and both should be stated to the accreditor rather than discovered:

1. **A `DELETE` does not remove the vector from the index.** HNSW index tuples retain the vector value until vacuumed, and graph structure retains connectivity. A purge must therefore run, in order: `DELETE`, `VACUUM (INDEX_CLEANUP ON) document_chunk_<partition>`, then `REINDEX INDEX CONCURRENTLY` on the affected partition's HNSW indexes. `KR-PRG-01` verifies it adversarially: after purge, a nearest-neighbour probe **using the deleted chunk's own embedding as the query** must not return it, at any `ef_search`.

2. **⚠️ Crypto-shredding does not cover embeddings, and this extends D15.** 03 §13 item 1 offers *"envelope-level encryption with per-classification keys. Crypto-shredding a key is the purge mechanism where physical deletion is impossible."* **An embedding cannot be encrypted at rest and remain searchable** — the ANN index operates on plaintext vectors by construction. And an embedding is not a hash: it is a lossy but genuine derivative of its source text, and inversion attacks on text embeddings are an active and improving area. **A spilled chunk's embedding must therefore be treated as spilled content and physically deleted**, and the "encrypt and shred" fallback is unavailable for this one store. Recorded as **OD-7**: 03 §13's remediation mechanism has a gap at the vector index, and the design compensates with physical deletion plus `REINDEX`, which requires the store to be genuinely deletable — which it is, and which is why `document_chunk` is declared operationally append-only rather than immutable.

`POST /documents/{id}/withdraw` initiates the sequence, publishes the tombstone, and records the run to `audit`. The procedure is **tested, not documented**: `KR-PRG-01` through `KR-PRG-04` run it end to end against a seeded spillage in the integration suite.

---

## 11. Testing

Conformance suite at `packages/contracts/conformance/knowledge-retrieval/`, structured per 03 §10: contract, event, fault-injection, consumer-driven, manifest, plus a reference dataset. Test IDs below are the suite's stable names. Integration tests use real PostgreSQL-with-pgvector and real Redpanda via testcontainers (09 §2.2), images mirrored and digest-pinned.

### 11.1 `KR-INV` — the invariants that make everything else checkable

| ID | Assertion |
|---|---|
| `KR-INV-1` | **Rows returned by the database equal results returned to the caller**, for every retrieval in the entire suite. Enforced by a session-level instrumentation fixture, not by inspection. Any application-layer filter fails this (§4.3) |
| `KR-INV-2` | Every retrieval executes **exactly one** `SELECT` against `document_chunk`. Asserted by statement counting. Two queries means a two-pass design crept in |
| `KR-INV-3` | `EXPLAIN (VERBOSE)` for the retrieval plan shows the applicability **and** classification predicates as quals on the base relation or its partitions — never as a `Filter` above a `Subquery Scan` over an unpredicated ANN scan |

### 11.2 `KR-CFG` — configuration-filter correctness

The requirement, stated as a test: *a chunk applicable to Class A but not Class B is retrievable for a Class-A asset and not for a Class-B asset.*

| ID | Assertion |
|---|---|
| `KR-CFG-01` | Chunk with `applicable_class_ids = {A}`: **retrievable** for a Class-A asset, **absent** for a Class-B asset, same query text, same principal |
| `KR-CFG-02` | Class-B asset's response is byte-identical to the response for a query with no corpus match at all (after correlation-ID/timestamp normalization) |
| `KR-CFG-03` | `applicable_template_revisions = [3,5)`: retrievable at asset template revision 4, absent at 5 |
| `KR-CFG-04` | `requires_alterations = {ALT-7}`: absent until the asset's baseline carries ALT-7, retrievable after |
| `KR-CFG-05` | `precludes_alterations = {ALT-9}`: retrievable until the asset carries ALT-9, absent after |
| `KR-CFG-06` | `applicable_niins`: retrievable only where the NIIN set overlaps the asset's installed set |
| `KR-CFG-07` | `effective_date_range`: retrievable at an `as_of` inside the range, absent outside; and a **reproduction** retrieval with an historical `as_of`/`as_known_at` returns the historical result set exactly (04 §2 bitemporality) |
| `KR-CFG-08` | **`scope_state = 'unknown'` is absent in `asset_scoped` and `class_scoped` modes**, present in `unscoped` (§2.4.3) |
| `KR-CFG-09` | **The applicability envelope is not caller-widenable.** Fuzz the request body with `class_id`, `class_ids`, `installed_niins`, `template_revision`, `applicability` and assert the response is unchanged and unknown fields are rejected (`extra="forbid"`) |
| `KR-CFG-10` | `baseline_epoch` ahead of the read model → `409`; behind → results computed against the read model's values with the echo showing it |
| `KR-CFG-11` | Read-model lag beyond the staleness bound → `503`, `fathom_staleness_refusals_total` incremented; **not** an empty result set (an empty set here would be a safety failure disguised as a security success) |

### 11.3 `KR-CLS` — classification enforcement and indistinguishability

The requirement, stated as a test: *"no results" and "results filtered by clearance" are indistinguishable — identical latency distribution, identical response shape.*

| ID | Assertion |
|---|---|
| `KR-CLS-01` | A chunk above the principal's clearance is never returned, at any `limit`, any cursor depth, any `ef_search` |
| `KR-CLS-02` | **Response bytes identical.** Case A: query matching nothing. Case B: identical query where every match is above clearance. Normalize correlation id and timestamps; compare bytes — headers included |
| `KR-CLS-03` | **Latency distributions indistinguishable.** n ≥ 2,000 paired samples per case; two-sided equivalence test on the quantized-latency distribution with a declared margin. **The test reports its power alongside its p-value and fails as *unproven* if power is below the declared floor** — the discipline [13 §13.2](13-synthetic-data-generator.md) established for canary indistinguishability, where failing to reject is the passing condition and a low-power test proves nothing |
| `KR-CLS-04` | A `SELECT` on `document_chunk` outside `with_clearance()` **raises** SQLSTATE `42704`. The fail-closed property, tested rather than asserted (§5.2) |
| `KR-CLS-05` | The runtime role is `NOBYPASSRLS` and is not the table owner; a direct connection as that role sees only policy-permitted rows; `FORCE ROW LEVEL SECURITY` is on |
| `KR-CLS-06` | `GET /chunks/{id}` and `GET /documents/{id}`: **`404` with identical problem-detail body and identical latency quantum** for absent and for withheld |
| `KR-CLS-07` | `X-Classification` on an empty result set equals the service's declared floor, identically in both cases |
| `KR-CLS-08` | **Source-level:** no identifier, metric name, log key, or response field in the package matches `withheld|filtered_out|suppressed|denied_count|access_denied|restricted_present` |
| `KR-CLS-09` | `ClassificationLabel` appears in **no** request schema in the committed `openapi.json`; no request field influences clearance |
| `KR-CLS-10` | With two synthetic levels seeded, `EXPLAIN` shows the high-side partitions **pruned** — a low-side query does not open the high-side index (§5.3) |
| `KR-CLS-11` | Compartment, dissemination, and CUI-category predicates use containment: a chunk with `{NOFORN}` is invisible to a principal without it; a chunk with `{SP-NNPI}` is invisible to a principal authorized only for `{SP-CTI}` |
| `KR-CLS-12` | Keyset pagination: page 2 of a heavily-filtered result set has no gaps, no offset artifacts, and `next_cursor` is non-null iff a full page was returned |
| `KR-CLS-13` | **No cross-principal cache.** Principal A queries; principal B issues the identical query; B's latency distribution is statistically identical to a cold query, and B's results are B's own |
| `KR-CLS-14` | A classification **downgrade** `UPDATE` without `fathom.declassification_authority` raises; an **upgrade** succeeds and moves the row between partitions (§3.4) |

### 11.4 `KR-INJ` — injection-resistance smoke test

Scoped honestly: this service cannot pass or fail an agent. These tests assert that the corpus content and return shape necessary for the 01 §8.8 gate exist and behave.

| ID | Assertion |
|---|---|
| `KR-INJ-01` | Every adversarial class in §6.3's table is present in the reference corpus, ingested with truthful `origin`, and **retrievable** — an adversarial corpus that is silently unretrievable tests nothing |
| `KR-INJ-02` | Every retrieved chunk carries `role = "retrieved_context"`; no response shape exists in which `body` appears outside a `RetrievedContext` |
| `KR-INJ-03` | `source_trust` is present and non-null on every chunk; it round-trips into an `Evidence` object and matches `document.origin` exactly |
| `KR-INJ-04` | **No operation returns rendered, prompt-ready, or concatenated text.** Scan the committed spec for any response property whose type is a bare string carrying corpus text outside `RetrievedContext.body`. Also asserts no `format`, `render`, or `as_prompt` parameter exists (§6.1) |
| `KR-INJ-05` | `role_confusion` passages containing chat-role markers and tool-call syntax are returned **verbatim, unmodified** (no sanitization, §6.4) and are structurally contained within `RetrievedContext` |
| `KR-INJ-06` | `injection_signals` is populated for the detectable classes; a `vendor`/`external` chunk with non-empty signals is `quarantined_at` and therefore **absent** from retrieval until reviewed |
| `KR-INJ-07` | `GET /documents/{id}` returns a complete provenance record for every adversarial chunk — the lookup that makes an injection finding actionable (§6.3) |
| `KR-INJ-08` | An empty `injection_signals` array does not change any response field, header, or behavior — it is not a safety assertion (§6.4) |

### 11.5 `KR-CHK`, `KR-APP`, `KR-EMB`, `KR-ANN`, `KR-BND`, `KR-PRG`

| ID | Assertion |
|---|---|
| `KR-CHK-01` | No chunk exceeds its type's hard cap; over-cap input fails the run rather than truncating |
| `KR-CHK-02` | **A WARNING or CAUTION governing a step appears in every chunk of that step's procedure** (§2.2, `ietm`) |
| `KR-CHK-03` | A 2-Kilo narrative is reassembled across all continuation blocks into one chunk and is never split |
| `KR-CHK-04` | A test-report results table is never split across chunks |
| `KR-CHK-05` | An ECP's affected-items list is present as applicability metadata and **absent** from any embedded body |
| `KR-CHK-06` | A `CANCEL` CASREP supersedes its predecessors, which become non-retrievable |
| `KR-APP-01` | Pass-3 output with no `evidence_span` is discarded before storage |
| `KR-APP-02` | Two-pass disagreement on a field forces that field to `unknown` and the chunk to `pending_sme` |
| `KR-APP-03` | No `llm_assisted` extraction auto-publishes, at any confidence |
| `KR-APP-04` | An SME rejection makes the chunk permanently non-retrievable in scoped modes; the decision requires `If-Match` and is audited |
| `KR-EMB-01` | A query embedded by model B against a corpus embedded by model A returns **empty** and reports the mismatch on `/readyz`; it never compares across spaces |
| `KR-EMB-02` | Both embedding sets coexist during a `reindex_run` cutover with no cross-space result |
| `KR-ANN-01` | **Recall@k under the full predicate** measured against brute-force exact search over the same predicate on the reference corpus; fails below the declared floor (OD-4) |
| `KR-ANN-02` | Budget exhaustion returns fewer rows and is **indistinguishable** from a genuinely sparse corpus in shape and latency quantum |
| `KR-BND-1` | No forbidden schema or field in any response, with the field list generated from `packages/canonical-schemas` at test time (§7.2) |
| `KR-BND-2` | No response property matches a `config_applicability_context` column except `baseline_id`, `baseline_epoch` |
| `KR-BND-3` | Import-graph: `FailurePrediction`, `Proposal`, and readiness types are not importable from this package |
| `KR-PRG-01` | After purge, a nearest-neighbour probe **using the purged chunk's own embedding** does not return it, at any `ef_search` (§10.1) |
| `KR-PRG-02` | Purge removes the row, the object, the audit rows, and publishes the tombstone; the compaction invariant holds |
| `KR-PRG-03` | The full spillage remediation runbook executes end to end against a seeded spillage |
| `KR-PRG-04` | `REINDEX` is actually executed and completes; a purge that skips it fails `KR-PRG-01` (the test that catches the mistake) |

Plus the shared 03 §10 categories: contract tests over every `x-substitution: required` operation including errors, pagination, idempotency, and concurrency; event tests on envelope, key, and ordering; **fault injection** asserting no state change without its event; consumer-driven tests contributed into `registry`'s suite for `configuration.baseline_changed`; and manifest tests for every manifest in `packages/agent-tooling/manifests/knowledge-retrieval/`.

---

## 12. Deployment

### 12.1 Runtime

Standard 09 §4.3/§4.4 shape: multi-stage Dockerfile, non-root UID 65532, read-only root filesystem, all capabilities dropped, nothing installed at container start (D26), base image digest-pinned. One uvicorn worker per container, HPA on request rate for the API deployment; a separate `KEDA`-scaled consumer deployment for the `configuration.baseline_changed` inbox.

**Database:** `fathom-knowledge-retrieval-pg`, a CloudNativePG `Cluster` on a **pgvector-bearing image**, digest-pinned. One logical database (obligation 13). Alembic migrations as a `pre-upgrade,pre-install` Helm hook with `backoffLimit: 0`; HNSW and GIN DDL via `op.execute()` (09 §2.2). Role separation is part of the migration: owner role for DDL, `fathom_retrieval_reader` (`NOBYPASSRLS`) for the runtime — the `KR-CLS-05` property is created by a migration, not by an operator.

**Readiness checks** (09 §5.6): database, migration head equality, broker, **configuration read-model lag**, outbox depth, **`EmbeddingPort` reachability**, and **`embedding_model_id` coverage** — if the pinned model matches no indexed chunk set, the service is *not ready*, because retrieval would return empty for a reason no operator would diagnose from an empty result.

**Configuration** (`.env.example`, complete and CI-reconciled with `Settings`):

```dotenv
FATHOM_APP__LOG_LEVEL=INFO
FATHOM_APP__STALENESS_BOUND_SECONDS=900        # config read model; §3.6 refusal threshold
FATHOM_RETRIEVAL__LATENCY_FLOOR_MS=300        # §5.4.1 SECURITY PARAMETER — ADR to change
FATHOM_RETRIEVAL__LATENCY_QUANTUM_MS=50       # §5.4.1 SECURITY PARAMETER — ADR to change
FATHOM_RETRIEVAL__HNSW_EF_SEARCH=200
FATHOM_RETRIEVAL__HNSW_MAX_SCAN_TUPLES=20000  # §5.4 C3 fixed work budget
FATHOM_RETRIEVAL__DEFAULT_LIMIT=8
FATHOM_RETRIEVAL__MAX_LIMIT=50
FATHOM_EMBEDDING__MODEL_ID=<pinned>           # §2.5 hard query predicate
FATHOM_EMBEDDING__DIMENSION=1024
FATHOM_EMBEDDING__BASE_URL=http://embeddings.fathom-sustainment.svc.cluster.local:8000
FATHOM_DATABASE__URL=postgresql+asyncpg://knowledge_retrieval@localhost:5432/knowledge_retrieval
FATHOM_EVENTS__BROKERS=localhost:9093
FATHOM_EVENTS__SCHEMA_REGISTRY=http://localhost:8081
FATHOM_EVENTS__CONSUMER_GROUP=fathom-knowledge-retrieval-v1
FATHOM_AUTH__ISSUER=https://keycloak.internal/realms/fathom
FATHOM_AUTH__JWKS_URL=https://keycloak.internal/realms/fathom/protocol/openid-connect/certs
FATHOM_AUDIT__BASE_URL=http://audit.fathom-sustainment.svc.cluster.local:8000
FATHOM_REFERENCE_DATA__BASE_URL=http://reference-data.fathom-sustainment.svc.cluster.local:8000
FATHOM_REGISTRY__BASE_URL=http://registry.fathom-sustainment.svc.cluster.local:8000
FATHOM_OTEL__ENABLED=false
```

### 12.2 Where the ingest compute runs — and why it is a Domino Job

Chunking, document parsing, and pass-3 LLM extraction need heavy parsing libraries and LLM access. Rather than give this service either, **the ingest pipeline runs as a Domino Job/Flow and delivers results through `POST /documents/bulk`** — with a workload identity, an `Idempotency-Key`, and `ingest_run_id` fencing.

This is the D10/C7 pattern verbatim, identical to how PdM receives scoring results, and it reuses the **one** sanctioned `domino-compute → gateway` NetworkPolicy rule (09 §4.4.2). No new cross-namespace edge is needed for ingest, this service acquires no LLM dependency, and 09 DO-NOT #1 holds without a special case: *"A Domino Job is an API client, never a database client."*

The service therefore makes exactly **one** synchronous outbound call on the retrieval path: the query embedding. Its latency is content-independent (§5.4 C3), and it is served by an in-cluster `EmbeddingPort` peer.

### 12.3 NetworkPolicy — declared egress, and two amendments to 09 §4.4.2

| Peer | Purpose | Sanctioned by |
|---|---|---|
| own CloudNativePG cluster | storage | 09 §4.4.2 |
| Redpanda brokers + schema registry | events | 09 §4.4.2 |
| `kube-dns` | discovery | 09 §4.4.2 |
| `auth` | JWKS / introspection; ABAC evaluated locally | 09 §4.4.2 |
| `audit` | provenance (obligation 9) | 09 §4.4.2 |
| `reference-data` | enumerations, cached | 09 §4.4.2 |
| **`registry`** | **§3.6's `changed_since` rebuild and configuration reads** | ⚠️ **not in 09 §4.4.2 — OD-8** |
| **`embeddings`** (in-cluster `EmbeddingPort`) | query embedding | ⚠️ **not in 09 §4.4.2 — OD-8** |

⚠️ **09 §4.4.2's sanctioned-edge table has a general gap, and this service is where it surfaces.** The table permits `gateway → the nine` and forbids `sub-application → sub-application`, but 03 §4 and D5 require **every declared consumer** to rebuild its read model from the producer's `changed_since` reads — an HTTP edge from consumer to producer that the table does not sanction for anyone. 03 §6 names `knowledge-retrieval` a declared consumer of `configuration.baseline_changed`, so this service needs it.

**Position taken here:** declare the `knowledge-retrieval → registry` edge explicitly, restricted to the rebuild path, with an ADR under `docs/adr/` and an amendment to 09 §4.4.2 (OD-8). It does **not** violate 03 principle 2, because principle 2 forbids synchronous cross-sub-application calls **on compute paths** — and a read-model rebuild is definitionally not a compute path. A lint rule and `KR-INV-2`'s statement counting enforce the restriction: **no Registry call occurs during `POST /retrievals`.** The alternative — routing rebuild reads through `gateway` — is rejected because it makes the gateway a dependency of every consumer's rebuild and inverts 01 §5's composition-only role.

The `helm/tests/` assertion is mandatory and unchanged: the rendered egress peer set **equals** `values.networkPolicy.egress` exactly and contains nothing else.

---

## 13. Explicit DO-NOT list

Extends 09 §9; removes nothing from it. Each item carries the finding that makes it a defect rather than a preference.

**DO-NOT-1 — Do not post-filter for classification. Filter in the query.**
Not "for now." Not "just for the demo, it's single-level anyway." Not "in a helper that we'll inline later." The predicate is in the SQL and independently in RLS. Removing results after retrieval leaks the existence of records through result count and latency, and — worse — it *computes* the withheld count, which is a quantity that will eventually be logged, metered, or returned. *(**D13**; 03 §7.3, 09 §9.4 item 22)*

**DO-NOT-2 — Do not add any response field, header, status code, metric, or log line whose presence or value depends on what was withheld.**
No `filtered: true`, no `partial`, no `restricted_present`, no `Warning`, no `403` for content, no `withheld_total`, no debug mode that reveals it. Fleet Status's `restricted_contributors_present` boolean (06 §5) is correct **there** and is an existence oracle **here**; §5.6 records why, so nobody harmonizes them. *(**D13**; 03 §7.3, 06 §5)*

**DO-NOT-3 — Do not distinguish "absent" from "withheld" on a single-resource read.**
`404`, same body, same latency quantum, both cases, no exceptions. A `403` here is the leak in its purest and most easily-exploited form. *(**D13**; 03 §7.3)*

**DO-NOT-4 — Do not let retrieved content be indistinguishable from instructions in an agent's context.**
Corpus text leaves this service only inside `RetrievedContext` with `role = "retrieved_context"`. Do not add an operation returning rendered, joined, or prompt-ready text; do not add a `format=prompt` parameter; do not "help" a caller by concatenating. The convenient helper is how the corpus reaches a system-role message. *(**D14**; 03 §9 item 1, 09 §9.3 item 19)*

**DO-NOT-5 — Do not serve a structured or current-state fact from this service.**
No prediction, no readiness, no operational status, no configuration answer. Not through a debug operation, not through a health detail, not as a "convenience" field on a retrieval response. Agents get state from sub-application APIs; this service serves procedural and narrative knowledge with citations. *(04 §11, 01 §8.3)*

**DO-NOT-6 — Do not return the resolved applicability *values* to the caller.**
Dimension names, yes; `class_id`, the installed NIIN set, the alteration set, `template_revision`, no. Returning them makes retrieval an unauthoritative configuration oracle that bypasses the Registry's own authorization — DO-NOT-5's violation arriving through a helpful field. *(04 §11, 04 §2)*

**DO-NOT-7 — Do not accept applicability parameters from the caller.**
The request names an asset and an epoch. The server resolves `class_id`, NIINs, alterations, and template revision from its read model. A caller-supplied class list is a caller-widenable envelope, and a maintainer will then be shown a procedure for a variant not installed — which is the requirement, inverted, delivered through the API. *(04 §11)*

**DO-NOT-8 — Do not treat unknown applicability as universal applicability.**
`scope_state = 'unknown'` is excluded from scoped retrieval and is not in the partial index that scoped retrieval scans. An empty `applicable_class_ids` array means "class-agnostic" and is never written by an extractor that failed to determine class. Conflating the two silently defeats the entire configuration-aware design while every test still passes. *(04 §11)*

**DO-NOT-9 — Do not auto-publish an LLM-derived applicability determination.**
Any confidence. Any prompt. Pass 3 produces review candidates with quoted evidence spans, not determinations. And do not let a "high-confidence" threshold be quietly introduced to clear a review backlog — the backlog is the cost of the requirement, not a bug in it. *(04 §11; **D14** by analogy — an unreviewed model output governing what a maintainer is shown)*

**DO-NOT-10 — Do not derive, upgrade, or default `source_trust`.**
It is a total function of `origin`, and `origin` is required at ingest and immutable. No filename heuristic, no organization-name lookup, no `program` default. A permissive default marks vendor manuals and ECPs — D14's named threat surface — as program content, and the adjudicator's flag never fires. *(**D14**; 03 §7.2, 03 §9 item 5)*

**DO-NOT-11 — Do not sanitize, rewrite, or "neutralize" a chunk body, and do not treat `injection_signals` as a control.**
Verbatim source text or nothing. Editing a technical procedure to defang a prompt pattern trades a security risk for a mishap risk and makes the corpus unauditable against its original. An empty signal array is not evidence of safety and grants no relaxation of structural separation. The real controls are 03 §9 items 2 and 4, and they live elsewhere. *(**D14**; 03 §9 items 2 and 4)*

**DO-NOT-12 — Do not enforce domain policy here.**
No APL authorization check, no interval-delta bound, no baseline-presence validation, no refusal to serve content that might lead to a bad proposal. Those are validation rules on the **receiving** operation and hold *"regardless of what an agent proposes or why."* A second implementation here will drift from the first, and the drift will be discovered when the two disagree in production. *(03 §9 item 2)*

**DO-NOT-13 — Do not compare across embedding spaces.**
`embedding_model_id` is a hard query predicate. A cross-space comparison returns fluent, ranked, wrong results with no error anywhere, which is the worst failure mode available to a retrieval system. Fail empty and report it on `/readyz`. *(§2.5)*

**DO-NOT-14 — Do not cache retrieval results, or share any query-derived cache across principals.**
A result cache serves A's authorized results to B. A shared query-embedding cache makes B's identical query faster and thereby reveals that A asked it. `Cache-Control: no-store`, per-request only. *(**D13**; 03 §7.3)*

**DO-NOT-15 — Do not raise throughput by lowering the latency floor or quantum without an ADR.**
They are security parameters, not tuning knobs, and they are the closure of the timing channel that separates "no results" from "results withheld." The chart carries that comment; do not delete the comment either. *(**D13**; 03 §7.3)*

**DO-NOT-16 — Do not assume a `DELETE` purges the vector index.**
`DELETE`, then `VACUUM`, then `REINDEX`, then verify with a nearest-neighbour probe using the purged embedding itself. And do not rely on crypto-shredding for embeddings: they cannot be encrypted and remain searchable, and they are genuine derivatives of their source text (§10.1). *(**D15**; 03 §13)*

**DO-NOT-17 — Do not consume a Registry event this service is not a declared consumer of.**
03 §6 declares exactly one: `configuration.baseline_changed`. `installed_item.installed`/`.removed` would be convenient and would be an undeclared dependency that a conformant substitution breaks. Refresh from the authoritative configuration read instead. *(**C4**; 03 §6, §10)*

**DO-NOT-18 — Do not invent a consumer for this service's topics.**
An uncatalogued topic with no consumer is honest; an invented consumer is finding C19 recreated. Add the topics to 03 §6 (OD-6) and let real consumers declare themselves. *(**C19**; 03 §6)*

---

## 14. Open decisions

| ID | Decision | Owner | Consequence if unresolved |
|---|---|---|---|
| **OD-1** | **⚠️ SME validation of the entire §2.4 applicability-extraction approach** — thresholds, the auto-publish gate, `narrowed` partial retrieval, who is authorized to make a determination, and whether an LLM-assisted determination is admissible as an engineering determination at all | Technical-documentation SME + ISEA + program engineering | **The highest-consequence open item in this document.** Every number in §2.4.3 is invented, which 09 DO-NOT #31 forbids. If LLM-assisted determination is inadmissible, pass 3 becomes a triage aid and the review workload is materially larger — which changes ingest scheduling, not the design |
| **OD-2** | Source-format adapter assumptions: IETM applicability element semantics, legacy TM effectivity conventions, ECP affected-items list structure, CASREP header fields. [07 §10](../architecture/07-navy-data-systems.md) records the 3-M dictionary, the 120 Card Format, and CASREP per-set field lists as **NOT PUBLICLY FOUND** | Program, with 3-M and technical-publications SMEs | Six parsers written against undocumented formats. Each is isolated behind an adapter interface, so the blast radius is contained, but none can be validated |
| **OD-3** | **Compartment storage strategy in production** — separate partition set, separate cluster, or exclusion only (§5.3) | Accreditor + security architecture | A compartment predicate over a shared HNSW index still puts compartmented vectors in a graph low-side queries traverse. Defensible, but it is an accreditor's call, not an engineer's |
| **OD-4** | **The recall@k floor under the full predicate** (`KR-ANN-01`), and `ef_search`/`max_scan_tuples` values | PdM + program engineering, against 06 §7 | Currently invented (09 DO-NOT #31). Too low and maintainers silently miss applicable procedures; too high and the fixed work budget stops being fixed |
| **OD-5** | **Add a `corpus/` output partition to document 13**, including `corpus/adversarial/` built under 13 §13.1's same-code-path rule (§6.3) | Synthetic-data owner + architecture | **The corpus this service exists to serve has no source, and 01 §8.8's adversarial golden question sets have no material.** This blocks both the retrieval demonstration and D14's evaluation gate |
| **OD-6** | Add `fathom.knowledge-retrieval.*` topics and their consumers to 03 §6's catalog. 03 §6 covers only the nine sub-applications | Architecture | No consumer-driven conformance test can be written for these topics. Same gap [12 §11](12-reference-data-taxonomy.md) OD-7 records for `reference-data` — a general defect in 03 §6 |
| **OD-7** | **Resolve 03 §13's crypto-shredding gap at the vector index** (§10.1): embeddings cannot be encrypted and remain searchable, and are genuine derivatives of their source | Accreditor + architecture | D15 is an accreditation blocker and its stated remediation mechanism does not cover this store. The design compensates with physical deletion plus `REINDEX`; the accreditor must accept that substitution explicitly |
| **OD-8** | **Amend 09 §4.4.2's sanctioned-edge table** to cover consumer→producer `changed_since` rebuild edges generally, and this service's `registry` and `embeddings` peers specifically (§12.3) | Architecture, via ADR | A NetworkPolicy that blocks the rebuild path 03 §4 and D5 mandate. Affects **every** declared consumer, not only this service |
| **OD-9** | Embedding model selection and pin, plus the air-gapped serving path (01 §8.6) | Program + Domino | Dimension, index parameters, tokenizer, and chunk caps are all downstream of it. A model change after ingest is a full `reindex_run` over the corpus |
| **OD-10** | Ingest throughput and corpus scale. 06 §7 gives no document-count figure | Program, against 06 §7 | 09 DO-NOT #31 forbids inventing it. HNSW build parameters, review-queue capacity, and the ingest schedule all depend on it |

---

## 15. Corrections to source documents

Found while reconciling. Each is a defect in the cited document, not a decision of this one.

| # | Document | Defect | Correction | Status |
|---|---|---|---|---|
| 1 | **04 §11** | Says applicability metadata is *"class, configuration, and effective date"*, which reads as a per-asset baseline range. Baselines are **per-asset** (04 §2: *"a bitemporal snapshot of **an asset's** installed configuration"*), so a chunk cannot carry one | Applicability is class + **class-template revision** range + alteration predicates + effective date (§3.3) | **Applied in §3.3.** 04 §11's phrasing should be tightened, since a literal reading is unimplementable |
| 2 | **03 §6** | The event catalog has rows only for the nine sub-applications. Platform services publish events (obligation 2 requires it) with nowhere to declare them | Add platform-service sections | Not applied; flagged as OD-6. Same defect as 12 §11 OD-7 |
| 3 | **09 §4.4.2** | The sanctioned-edge table permits no consumer→producer HTTP edge, yet 03 §4 and D5 make `changed_since` rebuild reads mandatory for every declared consumer | Add a general rebuild-path edge class | Not applied; flagged as OD-8. **Affects every consumer, not only this service** |
| 4 | **03 §13** | Offers crypto-shredding as the purge mechanism *"where physical deletion is impossible"*, and names the vector index among the stores. **Embeddings cannot be encrypted and remain searchable**, so the mechanism does not apply to the store the finding names | State that the vector index requires physical deletion plus `REINDEX`, and that embeddings are content-bearing derivatives | Not applied; flagged as OD-7. Extends **D15** |
| 5 | **13 §1.1** | Nine output partitions, none of which is a document corpus. The service 04 §11 designs has no corpus to serve, and 01 §8.8's adversarial golden question sets have no source material | Add `corpus/`, including `corpus/adversarial/` | Not applied; flagged as OD-5 |
| 6 | **04 §11 vs 06 §5** | 03 §7.3 forbids any disclosure that leaks record existence; 06 §5 **requires** a `restricted_contributors_present` boolean with a count for rollups. Read together without §5.6's reasoning they appear to conflict, and a future reviewer will "harmonize" them | Note in 04 §11 that the retrieval corpus is the case 06 §5 anticipates when it says *"if exclusion is judged to leak through the count itself, suppress the boolean"* | **Reasoning applied in §5.6.** Both documents would benefit from the cross-reference |

---

## 16. Definition of Done

The shared Definition of Done in [`09-monorepo-and-conventions.md` §8](09-monorepo-and-conventions.md) applies **in full** — OpenAPI 3.1 generated from code and CI-validated, `x-substitution`/`x-side-effects`/`x-agent-eligible` coverage, `changed_since` reads, cursor pagination, RFC 9457 problem details, `Idempotency-Key`, `ETag`/`If-Match`, `X-Correlation-Id`, `X-Classification`, local ABAC authorization, transactional outbox, inbox record-and-apply, antecedent rule, monotonic-clock discipline, read-model lag on `/readyz` and `/metrics`, one logical database, digest-pinned non-root images, NetworkPolicy equality assertion, and conformance suite green. Nothing is removed.

Service-specific additions, all of which must hold:

1. **`KR-INV-1`, `KR-INV-2`, and `KR-INV-3` green.** Rows-in equals results-out; exactly one `SELECT` per retrieval; both predicates appear as base-relation quals in the plan. **If only three things are verified in a review, these are the three.**
2. **All of `KR-CFG-01` … `KR-CFG-11` green**, including `KR-CFG-01`'s Class-A/Class-B pair and `KR-CFG-09`'s non-widenable-envelope fuzz.
3. **All of `KR-CLS-01` … `KR-CLS-14` green**, and specifically: `KR-CLS-02` byte-identical responses; **`KR-CLS-03` latency equivalence with its power reported and above the declared floor**; `KR-CLS-04` fail-closed on an unset clearance GUC; `KR-CLS-06` `404` for absent and withheld alike; `KR-CLS-08` no `withheld`-shaped symbol anywhere in the package.
4. **RLS is live and cannot be bypassed.** Policy created by migration, `FORCE ROW LEVEL SECURITY` on, runtime role `NOBYPASSRLS` and not the owner, single-argument `current_setting()` throughout. Verified against a live database, not asserted in a comment.
5. **Partition-per-level exists and is exercised.** Four partitions, per-partition HNSW indexes, and `KR-CLS-10` showing high-side pruning in `EXPLAIN` with two synthetic levels seeded — **even though the demonstration is single-level.**
6. **`KR-INJ-01` … `KR-INJ-08` green**, including `KR-INJ-04`: **no operation returns rendered or prompt-ready text**, and no `format`/`render`/`as_prompt` parameter exists.
7. **`source_trust` round-trips.** `document.origin` → chunk → `RetrievedContext` → `Evidence` → `Proposal.evidence[]`, with no default and no inference anywhere on the path (`KR-INJ-03`).
8. **`KR-BND-1`, `KR-BND-2`, `KR-BND-3` green** — the negative API surface, generated from `packages/canonical-schemas` at test time so that today's 03 §7.3 corrections and any future ones propagate automatically.
9. **`KR-CHK-02` green** — a WARNING or CAUTION is never separated from the step it governs. This is the safety invariant of the chunker and it is not negotiable for retrieval quality.
10. **The purge path is executed, not documented.** `KR-PRG-01` … `KR-PRG-04` green, including the adversarial probe that uses the purged chunk's own embedding as the query, and the `REINDEX` that the probe exists to catch the absence of.
11. **`KR-ANN-01` green against a declared recall floor**, with the floor recorded as an OD-4 resolution rather than an invented number.
12. **⚠️ OD-1 is resolved, or the service is explicitly accepted as demonstration-only with a named owner.** §2.4's thresholds and the admissibility of LLM-assisted applicability determination are engineering proposals with no Navy authority. Shipping them silently would put an unreviewed model output in the path that decides which procedure a maintainer is shown, which is D14's failure pattern relocated from the corpus to the metadata.
13. **OD-5 is filed against document 13.** Without a `corpus/` partition this service has nothing to serve and D14's evaluation gate has no adversarial material — so item 6's tests pass against fixtures and prove nothing about the platform.
14. **Every open decision in §14 is either resolved and this document updated, or explicitly accepted as a demonstration-scope risk with a named owner.** OD-1, OD-5, and OD-7 cannot be closed by silence.
