# Reference Data — Unified Taxonomy Registry

| | |
|---|---|
| **Status** | Draft |
| **Slug** | `reference-data` (document 03 §3.1) |
| **Purpose** | Build specification for the platform service that is the sole owner of the FATHOM unified taxonomy — its definition, versioning, crosswalks, and publication — and of `equipment_family` |
| **Resolves** | Findings **C8** and **D31** (three claimed owners of one vocabulary) and **D35** (`equipment_family` defined nowhere in the shared kernel), document 05 |
| **Primary technical source** | [08 §2](../architecture/08-standards-alignment.md) in full. Every taxonomy value in this document is transcribed from it |
| **Binding contracts** | [03 §3.3](../architecture/03-integration-contracts.md), [03 §4](../architecture/03-integration-contracts.md), [03 §7.2](../architecture/03-integration-contracts.md), [03 §10](../architecture/03-integration-contracts.md), [03 §14](../architecture/03-integration-contracts.md), [04 §11](../architecture/04-subapplication-architectures.md) |
| **Conventions** | `docs/build/09-monorepo-and-conventions.md`, `docs/build/10-shared-packages.md` |
| **Classification** | Internal. The service itself operates at U for the synthetic demonstration (03 §12) |

---

## 1. Purpose and scope

Reference Data is the **single authoritative source** for the FATHOM unified taxonomy. Document 03 §14 states it without qualification:

> *"Reference Data is the single owner of the unified taxonomy — definition, versioning, publication. Post-Mission Analysis owns tag assignments; Failure Intelligence owns attributions and is the sole authority to extend the vocabulary; Scheduling owns findings codings. None owns the vocabulary itself `[C8, D31]`."*

Three sub-applications assign taxonomy terms to observations. None of them owns the terms:

| Sub-application | Owns | Does not own |
|---|---|---|
| Post-Mission Analysis (`pma`) | Tag **assignments** — which observable signature a reviewer confirmed on which mission window | The signature list |
| Maintenance Execution & Scheduling (`maintenance`) | Findings **codings** — the 3-M codes a maintainer filed on a 4790/2K | The 3-M code sets, and the mapping from them to failure modes |
| Failure Intelligence (`failure-intel`) | **Attributions**, and the sole authority to **extend** the vocabulary's content | The registry, versioning, and publication of what it extends |

### 1.1 Why single ownership is not a matter of taste

Document 08 §2.8 converts this from internal tidiness into external compliance:

> *"The external forcing function is DoDI 8320.02, which requires authoritative data sources to be registered and 'structural metadata, including vocabularies, taxonomies, and ontologies' to be published. **A vocabulary with three owners cannot be registered as an authoritative source.**"*

A build that leaves PMA or Failure Intelligence with an independent taxonomy store does not merely risk drift — it forfeits the registration claim. §7 of this document specifies what "published" means operationally so the claim is actually satisfiable.

### 1.2 In scope

1. The **`FailureModeEntry` registry** — the full vocabulary, per document 08 §2.8.
2. The **MIL-STD-3034A §3 definitions** adopted verbatim as the platform's semantic layer (08 §2.3).
3. The **Navy 3-M code sets** — CAUSE, WHEN DISCOVERED, ACTION TAKEN (08 §2.5).
4. The **three declared projections** and the crosswalks between them (08 §2.8).
5. **Taxonomy versioning** — semver, supersession, non-destructive revision.
6. **`equipment_family`** — owned by Reference Data, versioned, a required attribute of every part (03 §3.3, finding D35).
7. **Publication** — a served schema endpoint, a data dictionary export, and the versioned package.
8. The **proposal intake** by which PMA and Failure Intelligence submit novel signatures and modes.

### 1.3 Out of scope

- **Assignments of any kind.** Reference Data never stores a tag, a findings coding, or an attribution. It stores what those may say.
- **Adjudication of vocabulary content.** Reference Data operates the workflow; Failure Intelligence decides (08 §2.8, 03 §14).
- **Reconciliation at write time.** Prohibited by document 08 §2.8 non-negotiable 3. Reference Data supplies the crosswalks with which consumers reconcile at read time; it does not normalise anything on anyone's behalf.
- **Unit hierarchy, ESWBS/EIC code sets, and general enumerations.** These are also Reference Data responsibilities per document 04 §11, but they are separable work items and are not specified here beyond the `equipment_class` reference into ESWBS/EIC.

### 1.4 The standards anchor — three standards, three non-overlapping jobs

Transcribed from document 08 §2.2. This is a **documented program decision**, not a compliance default: document 08 §2.7 records the verified negative that *"DoDI 4151.22 contains the word 'taxonomy' zero times."* DoDI 4151.22 §1.2.j is the authority for choosing open standards at all — *"Accept data in proprietary formats only by exception."*

| Layer | Standard | Role in this service |
|---|---|---|
| **Semantics** | MIL-STD-3034A §3 (Rev A, 29 Apr 2014; Notice 1, 15 Apr 2019; NAVSEA SEA 05S) | The nine definitions, adopted verbatim, are seed reference content and the meaning of the semantic columns |
| **Structure** | ISO 14224:2016, levels 6–9 and Annex B | The nine-level hierarchy and the three-letter failure-mode codes. **Annex B is paywalled and UNVERIFIED — see §5.4** |
| **Contract** | SAE GEIA-STD-0007C (Rev C, DoD adoption notice Active 30 Apr 2024), with ASD S5000F | The export contract. The registry must export into LSA-050 (RCM Results) and LSA-058 (FMECA Results) |

Per document 08 §2.3, the program **adopts "potential failure" as the term for its core output** — MIL-STD-3034A 3.9.3, *"A definable and measurable condition that indicates a functional failure is imminent"* — rather than an invented term. `potential_failure_def` on every registry entry is where that measurable precursor condition lives, and it is the CBM+ hook.

---

## 2. Data model

PostgreSQL. One logical database, per obligation 13 (03 §15). Schema `reference_data`. Migrations per `docs/build/09-monorepo-and-conventions.md`.

Two invariants govern the whole schema and are stated before the tables because every table obeys them:

- **I1 — Every entry and every crosswalk record carries `taxonomy_version`.** Document 08 §2.8 non-negotiable 1: *"A training set assembled across an unversioned revision is silently corrupt and the corruption is undetectable afterwards."* There is no unversioned row anywhere in this schema.
- **I2 — Rows in a published version are immutable except for supersession marking.** Enforced by trigger (§6.3), not by convention.

### 2.1 `taxonomy_version` — the version register

```sql
CREATE TYPE reference_data.version_status AS ENUM ('draft', 'published', 'deprecated');

CREATE TABLE reference_data.taxonomy_version (
    version              text PRIMARY KEY,          -- semver, e.g. '1.0.0'
    status               reference_data.version_status NOT NULL DEFAULT 'draft',
    predecessor_version  text REFERENCES reference_data.taxonomy_version(version),
    semantics_anchor     text NOT NULL,             -- 'MIL-STD-3034A Rev A, Notice 1 (2019-04-15)'
    structure_anchor     text NOT NULL,             -- 'ISO 14224:2016 3rd ed. (2016-09-16)'
    export_anchor        text NOT NULL,             -- 'SAE GEIA-STD-0007C Rev C'
    m3_manual_revision   text NOT NULL,             -- 'NAVSEAINST 4790.8B (2003-11-13)'
    release_note         text NOT NULL,
    published_at         timestamptz,
    published_by         text,
    CONSTRAINT version_is_semver CHECK (version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),
    CONSTRAINT published_has_provenance
        CHECK (status <> 'published' OR (published_at IS NOT NULL AND published_by IS NOT NULL))
);
```

`m3_manual_revision` is a first-class column because document 08 §2.5 requires it: *"These are transcribed from 4790.8B (13 November 2003). Revisions C and D exist. Re-baseline every code list against the current revision before implementation and **treat any delta as a taxonomy version bump**."* A re-baseline is a schema-visible event, not a data cleanup.

**Semver policy.**

| Change | Bump | Rationale |
|---|---|---|
| New entry, new crosswalk row, new equipment family | **minor** | Purely additive; no held reference changes meaning |
| Entry superseded, split, merged, or deprecated; crosswalk row withdrawn; 3-M re-baseline delta | **major** | A consumer's held reference now resolves through a supersession record |
| Editorial correction to `release_note`, non-semantic text, or provenance metadata | **patch** | No consumer-visible semantic change. Never permitted on a semantic column of a published version (§6.3) |

### 2.2 `milstd_3034a_term` — the semantic layer

```sql
CREATE TABLE reference_data.milstd_3034a_term (
    term_key         text NOT NULL,          -- 'functional_failure'
    taxonomy_version text NOT NULL REFERENCES reference_data.taxonomy_version(version),
    clause           text NOT NULL,          -- '3.9.1'
    term_label       text NOT NULL,          -- 'Functional failure'
    definition_text  text NOT NULL,          -- verbatim quotation from MIL-STD-3034A §3
    source_standard  text NOT NULL DEFAULT 'MIL-STD-3034A Rev A',
    is_verbatim      boolean NOT NULL DEFAULT true,
    PRIMARY KEY (term_key, taxonomy_version)
);
```

`is_verbatim` exists so a paraphrase can never masquerade as standard text. Document 08 §2.3 says *"adopt verbatim"*; a row with `is_verbatim = true` asserts the text is quoted, and the seed loader (§5.1) refuses to set it on any string it did not read from the transcription fixture.

### 2.3 `failure_mode_entry` — the `FailureModeEntry` schema

Document 08 §2.8's registry entry shape, transcribed field-for-field. The source block is reproduced here so the correspondence is auditable:

```
FailureModeEntry {
  code                    # ISO 14224 Annex B three-letter code, extended per equipment class
  taxonomy_version        # semver. Every label carries the version it was assigned under
  equipment_class         # ISO 14224 L6 -> ESWBS / EIC
  subdivision             # ISO 14224 L7
  maintainable_item       # ISO 14224 L8 -> InstalledItem, IUID per DoDI 8320.04
  functional_failure_ref  # MIL-STD-3034A 3.9.1 — the function lost
  failure_effect          # MIL-STD-3034A 3.11
  consequence_class       # safety | environmental | mission | economic | hidden | regulatory
  evident_or_hidden       # MIL-STD-3034A 3.13.2 / 3.13.3
  is_dominant             # MIL-STD-3034A 3.12.1 — prioritisation key
  cause_candidates[]      # ISO 14224 cause codes, crosswalked to 3-M CAUSE 1–8,0
  observable_signature    # what Condition & Telemetry can see — the CBM+ hook
  detection_methods[]     # ISO 14224 detection method
  potential_failure_def   # MIL-STD-3034A 3.9.3 — the measurable precursor condition
}
```

As a concrete schema, with the two array fields normalised into child tables (§2.4, §2.5):

```sql
CREATE TYPE reference_data.consequence_class AS ENUM
    ('safety', 'environmental', 'mission', 'economic', 'hidden', 'regulatory');

CREATE TYPE reference_data.evidence_visibility AS ENUM ('evident', 'hidden');

CREATE TYPE reference_data.code_authority AS ENUM (
    'iso-14224-verified',      -- transcribed from a primary source; see §5.2
    'iso-14224-transcribed',   -- from the purchased standard, once acquired
    'fathom-extension'         -- program-synthesised placeholder; see §5.4
);

CREATE TABLE reference_data.failure_mode_entry (
    entry_id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    lineage_id              uuid NOT NULL,        -- stable across versions; the resolution key
    code                    text NOT NULL,
    code_authority          reference_data.code_authority NOT NULL,
    taxonomy_version        text NOT NULL REFERENCES reference_data.taxonomy_version(version),
    equipment_class         text NOT NULL,        -- ISO 14224 L6 -> ESWBS / EIC. NEVER a join key
    subdivision             text,                 -- ISO 14224 L7
    maintainable_item       text,                 -- ISO 14224 L8 item-type designation; see note
    functional_failure_ref  text NOT NULL,        -- MIL-STD-3034A 3.9.1 — the function lost
    failure_effect          text NOT NULL,        -- MIL-STD-3034A 3.11
    consequence_class       reference_data.consequence_class NOT NULL,
    evident_or_hidden       reference_data.evidence_visibility NOT NULL,
    is_dominant             boolean NOT NULL DEFAULT false,   -- MIL-STD-3034A 3.12.1
    observable_signature    text,                 -- the CBM+ hook; null where not observable
    potential_failure_def   text,                 -- MIL-STD-3034A 3.9.3
    definition_text         text NOT NULL,        -- the code's own definition (e.g. 'breakdown')
    superseded_by_entry_id  uuid REFERENCES reference_data.failure_mode_entry(entry_id),
    superseded_at           timestamptz,
    created_at              timestamptz NOT NULL DEFAULT now(),
    created_by              text NOT NULL,
    source_proposal_id      uuid,                 -- provenance when created from a proposal
    classification          jsonb NOT NULL,       -- ClassificationLabel, 03 §7.3

    -- Generated so the uniqueness constraint behaves with a NULL subdivision (a class-level
    -- entry) rather than silently permitting duplicates, since NULL <> NULL in a UNIQUE index.
    subdivision_key         text GENERATED ALWAYS AS (coalesce(subdivision, '')) STORED,

    CONSTRAINT entry_unique_per_version
        UNIQUE (code, equipment_class, subdivision_key, taxonomy_version),
    CONSTRAINT extension_codes_are_namespaced CHECK (
        (code_authority = 'fathom-extension' AND code ~ '^FATHOM-EXT-[0-9]{3}$')
     OR (code_authority <> 'fathom-extension' AND code ~ '^[A-Z]{3}$')
    ),
    CONSTRAINT supersession_is_paired
        CHECK ((superseded_by_entry_id IS NULL) = (superseded_at IS NULL)),
    CONSTRAINT no_self_supersession CHECK (superseded_by_entry_id <> entry_id)
);

CREATE INDEX fme_lineage_version ON reference_data.failure_mode_entry (lineage_id, taxonomy_version);
CREATE INDEX fme_code_version    ON reference_data.failure_mode_entry (code, taxonomy_version);
CREATE INDEX fme_signature       ON reference_data.failure_mode_entry (observable_signature)
    WHERE observable_signature IS NOT NULL;
```

Four notes carry real design weight:

**`lineage_id` is the resolution key, not `code`.** A code can be renamed or split across a major bump. `lineage_id` is stable across versions and is what supersession records and crosswalks reference (§6). This is what makes a consumer holding `(code = 'BRD', taxonomy_version = '1.0.0')` resolvable forever.

**`equipment_class` is an ESWBS/EIC class code and is never a join key.** Document 03 §3.3, with the primary-source justification in document 08 §2.6: NAVSEAINST 4790.8 Appendix A makes EIC *"a class code of variable specificity"* — *"Where the EIC is known to more than four digits, it should be recorded at that level."* Any query joining `equipment_class` to `system_id` is a defect. `SystemRef` carries `eswbs` for human reference and federation only; `system_id` is the join key.

**`maintainable_item` carries an item-*type* designation, not an instance IUID.** Document 08 §2.8 annotates the field *"ISO 14224 L8 -> InstalledItem, IUID per DoDI 8320.04."* Taken literally as an instance identity, the vocabulary would grow to fleet size and a taxonomy entry would exist per serial number. The build interpretation is that the registry names the maintainable-item **class** at ISO L8, and the IUID binding happens at assignment time on the PMA tag or the Failure Intelligence `Attribution` — where document 08 §2.8 non-negotiable 4 (*"Instance identity is IUID, not EIC"*) properly applies. **This interpretation is Open Decision OD-4 (§11); it is not resolved here.**

**`extension_codes_are_namespaced` is the fabrication guard.** ISO 14224 failure-mode codes are exactly three uppercase letters. A hyphenated prefixed form cannot collide with any present or future ISO code. The constraint makes it structurally impossible to insert an invented three-letter code without also asserting `code_authority` in `('iso-14224-verified','iso-14224-transcribed')`, which the seed loader and the review checklist both gate on. See §5.4 and DO-NOT-3.

### 2.4 `failure_mode_cause_candidate` — `cause_candidates[]`

```sql
CREATE TABLE reference_data.failure_mode_cause_candidate (
    entry_id          uuid NOT NULL REFERENCES reference_data.failure_mode_entry(entry_id),
    taxonomy_version  text NOT NULL REFERENCES reference_data.taxonomy_version(version),
    iso_cause_code    text,          -- ISO 14224 cause code. UNVERIFIED source; see §5.4
    iso_cause_label   text,
    m3_cause_code     char(1)        -- crosswalk to 3-M CAUSE 1-8, 0
        REFERENCES reference_data.navy_3m_code_stub(code),   -- see §2.6
    confidence        numeric(3,2) CHECK (confidence > 0 AND confidence <= 1),
    basis             text NOT NULL, -- how this correspondence was established
    ordinal           int NOT NULL,
    PRIMARY KEY (entry_id, ordinal),
    CONSTRAINT at_least_one_cause_side CHECK (iso_cause_code IS NOT NULL OR m3_cause_code IS NOT NULL)
);
```

Document 08 §2.8 specifies `cause_candidates[]` as *"ISO 14224 cause codes, crosswalked to 3-M CAUSE 1–8,0."* The array is plural in the source and is modelled plural here: a single failure mode has several candidate causes and the correspondence to a nine-value 3-M cause code is not injective. **The ISO 14224 cause code list is behind the same paywall as Annex B and is UNVERIFIED (§5.4);** rows may therefore be seeded with `m3_cause_code` populated and `iso_cause_code` null until the standard is acquired.

### 2.5 `failure_mode_detection_method` — `detection_methods[]`

```sql
CREATE TABLE reference_data.failure_mode_detection_method (
    entry_id          uuid NOT NULL REFERENCES reference_data.failure_mode_entry(entry_id),
    taxonomy_version  text NOT NULL REFERENCES reference_data.taxonomy_version(version),
    detection_method  text NOT NULL,   -- ISO 14224 detection method. UNVERIFIED list; see §5.4
    method_authority  reference_data.code_authority NOT NULL,
    ordinal           int NOT NULL,
    PRIMARY KEY (entry_id, ordinal)
);
```

The ISO 14224 detection-method list is likewise unverified. `method_authority` carries the same three-value discipline as `code_authority` so a program-authored method string can never be read as standard content.

### 2.6 Navy 3-M code sets

```sql
CREATE TYPE reference_data.m3_code_set AS ENUM
    ('CAUSE', 'WHEN_DISCOVERED', 'ACTION_TAKEN_FIRST', 'ACTION_TAKEN_MODIFIER');

CREATE TABLE reference_data.navy_3m_code (
    code_set          reference_data.m3_code_set NOT NULL,
    code              char(1) NOT NULL,
    taxonomy_version  text NOT NULL REFERENCES reference_data.taxonomy_version(version),
    label             text NOT NULL,          -- transcribed from the manual
    source_revision   text NOT NULL,          -- 'NAVSEAINST 4790.8B (2003-11-13)'
    set_is_complete   boolean NOT NULL,       -- false where the transcription is partial
    PRIMARY KEY (code_set, code, taxonomy_version)
);

-- Referenced by §2.4 as navy_3m_code_stub: a view restricting to the CAUSE set of the
-- current published version, so the FK in failure_mode_cause_candidate cannot point at a
-- WHEN DISCOVERED code. Implemented as a CAUSE-only unique index plus a composite FK in
-- the migration; presented as a stub here for readability.
```

`set_is_complete` is required by the source. Document 08 §2.5 gives CAUSE and WHEN DISCOVERED as complete enumerations but gives ACTION TAKEN's first character as *"`1` … `2` … `3` … `4` cancelled · **and others**"*, with the second character *"TYCOM-specified."* Seeding ACTION_TAKEN_FIRST with `set_is_complete = false` is the only honest representation, and it is what makes §5.3's gap visible to a consumer rather than silently absent.

### 2.7 `equipment_family` — finding D35

Document 03 §3.3: *"`equipment_family` partitions model bindings, calibration records, and reference classes. It is defined and served by Reference Data, is versioned, and is a required attribute of every part `[D35]`."* It appears on `PartRef` alongside `niin`, `nsn`, and `apl`.

```sql
CREATE TABLE reference_data.equipment_family (
    family_id               text NOT NULL,      -- stable slug, e.g. 'centrifugal-pump-lo'
    version                 text NOT NULL REFERENCES reference_data.taxonomy_version(version),
    name                    text NOT NULL,
    description             text NOT NULL,
    superseded_by_family_id text,
    superseded_at           timestamptz,
    created_at              timestamptz NOT NULL DEFAULT now(),
    classification          jsonb NOT NULL,
    PRIMARY KEY (family_id, version),
    CONSTRAINT family_supersession_is_paired
        CHECK ((superseded_by_family_id IS NULL) = (superseded_at IS NULL))
);

CREATE TABLE reference_data.part_family_assignment (
    niin              char(9) NOT NULL,        -- the part join key, 03 §3.3
    family_id         text NOT NULL,
    taxonomy_version  text NOT NULL REFERENCES reference_data.taxonomy_version(version),
    basis             text NOT NULL,           -- how the assignment was determined
    PRIMARY KEY (niin, taxonomy_version),
    FOREIGN KEY (family_id, taxonomy_version)
        REFERENCES reference_data.equipment_family(family_id, version)
);
```

`equipment_family` shares the taxonomy's version register rather than carrying an independent version line. A model binding pinned to `taxonomy_version` then pins its reference class too, which is what PdM's tier bindings require (03 §14: *"PdM owns which registry version serves which tier and family"*).

`part_family_assignment` makes the NIIN→family binding a served reference dataset with a primary key of exactly one family per NIIN per version — that is what "required attribute of every part" means operationally, and the conformance test in §8.2 asserts total coverage of the demo NIIN set. **Whether Reference Data owns the assignment or only the family definition is Open Decision OD-5 (§11).** Document 03 says only *"defined and served by Reference Data"*; this build reads the assignment as reference data because the alternative is Supply and Registry each deciding, which is finding C8 in a different costume.

### 2.8 `crosswalk_pma_signature` — the PMA projection

Document 08 §2.8: PMA receives *"a coarsened subset keyed on `observable_signature`, plus an explicit `unclassified/novel` escape. Reviewers select observable signatures, not mechanisms — they are watching telemetry, not tearing down equipment."*

```sql
CREATE TABLE reference_data.pma_signature (
    signature_key     text NOT NULL,      -- what a reviewer selects
    taxonomy_version  text NOT NULL REFERENCES reference_data.taxonomy_version(version),
    signature_label   text NOT NULL,      -- reviewer-facing wording
    is_novel_escape   boolean NOT NULL DEFAULT false,
    equipment_class   text,               -- null = applies across classes
    PRIMARY KEY (signature_key, taxonomy_version)
);

CREATE TABLE reference_data.crosswalk_pma_signature (
    signature_key      text NOT NULL,
    entry_lineage_id   uuid NOT NULL,     -- -> failure_mode_entry.lineage_id
    taxonomy_version   text NOT NULL REFERENCES reference_data.taxonomy_version(version),
    confidence         numeric(3,2) CHECK (confidence > 0 AND confidence <= 1),
    basis              text NOT NULL,
    PRIMARY KEY (signature_key, entry_lineage_id, taxonomy_version),
    FOREIGN KEY (signature_key, taxonomy_version)
        REFERENCES reference_data.pma_signature(signature_key, taxonomy_version)
);
```

The crosswalk is many-to-many in both directions and for a substantive reason: one observable signature (an abnormal instrument reading) is consistent with several mechanisms, and one mechanism presents through several signatures. A coarsened *subset* is a set-valued relation by construction. The `is_novel_escape` row is the *"explicit `unclassified/novel` escape"* the source requires; a tag against it is well-formed data and becomes a proposal (§7.2), not a validation error.

### 2.9 `crosswalk_3m` — the Scheduling projection, many-to-many and lossy

This table is the single most defect-prone artifact in the service. Document 08 §2.8, verbatim:

> *"A published, versioned crosswalk from `{CAUSE, WHEN DISCOVERED, ACTION TAKEN, EIC}` to failure-mode code. It is **many-to-many and lossy by construction**: 3-M CAUSE has nine values and is a *cause* code, not a *mode* code. **Carry the ambiguity as data — `candidate_modes[]` with confidence — rather than forcing one code and silently corrupting the labels.** This is the most common way maintenance-derived training data goes bad."*

```sql
CREATE TABLE reference_data.crosswalk_3m (
    crosswalk_id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    taxonomy_version        text NOT NULL REFERENCES reference_data.taxonomy_version(version),

    -- the 3-M tuple. NULL means "unconstrained on this element", which is how a
    -- coarse mapping is expressed without inventing a wildcard value.
    cause_code              char(1),        -- CAUSE (CAS)
    when_discovered_code    char(1),        -- WHEN DISCOVERED (WND)
    action_taken_code       varchar(2),     -- ACTION TAKEN, 1-2 chars
    eic_prefix              varchar(7),     -- EIC prefix, variable specificity (08 §2.6)

    -- the candidate_modes[] element, one row per candidate
    candidate_entry_lineage uuid NOT NULL,  -- -> failure_mode_entry.lineage_id
    confidence              numeric(3,2) NOT NULL
        CHECK (confidence > 0 AND confidence <= 1),
    basis                   text NOT NULL,  -- engineering rationale, reviewable
    adjudicated_by          text NOT NULL,  -- failure-intel identity (§7)

    CONSTRAINT tuple_not_wholly_null CHECK (
        cause_code IS NOT NULL OR when_discovered_code IS NOT NULL
     OR action_taken_code IS NOT NULL OR eic_prefix IS NOT NULL
    ),
    CONSTRAINT one_row_per_tuple_candidate UNIQUE (
        taxonomy_version, cause_code, when_discovered_code,
        action_taken_code, eic_prefix, candidate_entry_lineage
    )
);

COMMENT ON TABLE reference_data.crosswalk_3m IS
  'MANY-TO-MANY AND LOSSY BY CONSTRUCTION (doc 08 s2.8). One 3-M tuple maps to a SET of
   candidate modes with confidence. Adding a UNIQUE index on the 3-M tuple alone, or a
   "primary candidate" flag consumed as if authoritative, silently corrupts every label
   derived from maintenance findings. Test tax-xw-3m-cardinality asserts against it.';
```

Two build details make the cardinality survive future maintenance:

- **The uniqueness constraint includes `candidate_entry_lineage`.** A unique index on the tuple alone is the forcing error, and it is exactly the migration a well-meaning engineer writes when a duplicate-key report lands. §8.3 adds a test that inspects `pg_indexes` and fails if any unique index exists over the 3-M tuple without the candidate column.
- **There is no `is_primary` column, deliberately.** A primary-candidate flag is a one-to-one mapping with extra steps: every downstream consumer will select on it and the ambiguity will be gone. Consumers rank by `confidence` at read time and are handed the full candidate set (§5, §8.1). Adding such a flag requires overturning DO-NOT-2.

`eic_prefix` is matched by prefix, never by equality, because document 08 §2.6 quotes NAVSEAINST 4790.8 Appendix A: *"Where the EIC is known to more than four digits, it should be recorded at that level."* A findings record may carry 4 characters or 7; prefix matching is the only correct join, and `eic_prefix` remains a class discriminator, never an instance key.

### 2.10 `taxonomy_supersession` — non-destructive revision

```sql
CREATE TYPE reference_data.supersession_relation AS ENUM
    ('renamed', 'split', 'merged', 'narrowed', 'broadened', 'deprecated');

CREATE TABLE reference_data.taxonomy_supersession (
    superseded_lineage_id   uuid NOT NULL,
    superseding_lineage_id  uuid,           -- NULL only for 'deprecated' with no successor
    from_version            text NOT NULL REFERENCES reference_data.taxonomy_version(version),
    to_version              text NOT NULL REFERENCES reference_data.taxonomy_version(version),
    relation                reference_data.supersession_relation NOT NULL,
    confidence              numeric(3,2) CHECK (confidence > 0 AND confidence <= 1),
    rationale               text NOT NULL,
    adjudicated_by          text NOT NULL,
    recorded_at             timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (superseded_lineage_id, superseding_lineage_id, to_version),
    CONSTRAINT deprecated_may_lack_successor
        CHECK (superseding_lineage_id IS NOT NULL OR relation = 'deprecated'),
    CONSTRAINT no_self_reference CHECK (superseded_lineage_id <> superseding_lineage_id)
);
```

Supersession is itself many-to-many: a `split` produces several successor rows for one predecessor, a `merged` several predecessors for one successor. This is a separate table rather than a column for that reason — `superseded_by_entry_id` on `failure_mode_entry` (§2.3) records the simple rename case for query convenience and is populated from this table, never independently.

### 2.11 `taxonomy_proposal` — vocabulary extension intake

Conforms to the `Proposal` schema fixed by document 03 §7.2, with `target_sub_app = 'reference-data'`. Fields below are the service-local projection; the full envelope and the four rules of §7.2 (non-empty evidence with `source_trust`, re-validation at approval, claim-gated adjudication, authority checked against blast radius) apply unchanged.

```sql
CREATE TYPE reference_data.proposal_kind AS ENUM (
    'novel_signature',        -- from pma: a reviewer found something the subset cannot express
    'new_failure_mode',       -- from failure-intel: extend the vocabulary
    'crosswalk_revision',     -- from failure-intel or maintenance: a mapping is wrong
    'equipment_family_change'
);

CREATE TYPE reference_data.proposal_status AS ENUM
    ('proposed', 'claimed', 'approved', 'rejected', 'superseded', 'expired');

CREATE TABLE reference_data.taxonomy_proposal (
    proposal_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kind                 reference_data.proposal_kind NOT NULL,
    proposer_sub_app     text NOT NULL,        -- slug, 03 §3.1
    proposer_identity    text NOT NULL,
    against_version      text NOT NULL REFERENCES reference_data.taxonomy_version(version),
    payload              jsonb NOT NULL,       -- the proposed entry / signature / crosswalk row
    evidence             jsonb NOT NULL,       -- 03 §7.2: required, non-empty, source_trust
    rationale            text NOT NULL,
    confidence           numeric(3,2),
    agent_id             text,
    agent_version        text,
    llm_version          text,
    trace_ref            text,
    authority_class      text NOT NULL,
    blast_radius         text NOT NULL,        -- item | asset | class | fleet
    requires_dual_control boolean NOT NULL,
    valid_until          timestamptz,
    status               reference_data.proposal_status NOT NULL DEFAULT 'proposed',
    claimed_by           text,
    claimed_until        timestamptz,
    adjudicated_by       text,
    adjudicated_at       timestamptz,
    adjudication_note    text,
    resulting_version    text REFERENCES reference_data.taxonomy_version(version),
    classification       jsonb NOT NULL,

    CONSTRAINT evidence_non_empty CHECK (jsonb_array_length(evidence) > 0),
    CONSTRAINT approver_is_authorised CHECK (
        status <> 'approved' OR adjudicated_by LIKE 'failure-intel:%'
    )
);
```

`approver_is_authorised` encodes document 03 §14 and document 08 §2.8 as a database constraint: Failure Intelligence is *"the sole authority to extend the vocabulary."* The identity-prefix form is a placeholder for the ABAC attribute check performed at the API boundary (§3.3); the constraint is a defence in depth, not the primary control.

### 2.12 API model

The wire model is the schema with the two child tables re-inlined as arrays, so the API returns exactly the `FailureModeEntry` shape document 08 §2.8 specifies. `snake_case` fields per document 03 §4. Types published from `packages/canonical-schemas` per `docs/build/10-shared-packages.md`.

```json
{
  "code": "BRD",
  "code_authority": "iso-14224-verified",
  "taxonomy_version": "1.0.0",
  "lineage_id": "…uuid…",
  "equipment_class": "233",
  "subdivision": null,
  "maintainable_item": null,
  "functional_failure_ref": "…",
  "failure_effect": "…",
  "consequence_class": "mission",
  "evident_or_hidden": "evident",
  "is_dominant": false,
  "cause_candidates": [
    { "iso_cause_code": null, "m3_cause_code": "7",
      "iso_cause_label": null, "confidence": 0.6, "basis": "…" }
  ],
  "observable_signature": "…",
  "detection_methods": [ { "detection_method": "…", "method_authority": "…" } ],
  "potential_failure_def": "…",
  "definition_text": "breakdown",
  "superseded_by": null,
  "classification": { "level": "U", "cui_categories": [], "dissemination": [] }
}
```

---

## 3. API surface

Base path `/api/v1/reference-data/…` per document 03 §4. Every operation declares `x-substitution` and `x-side-effects`; `x-agent-eligible` is asserted only where `x-side-effects` is `none` or `proposal-only`, per obligation 8 (03 §15) and finding C1/D11. Annotation semantics and CI validation are specified in `docs/build/09-monorepo-and-conventions.md`; generated clients and the OpenAPI publication path are in `docs/build/10-shared-packages.md`.

### 3.1 Operations

| Operation | Purpose | `x-substitution` | `x-side-effects` | `x-agent-eligible` |
|---|---|---|---|---|
| `GET /taxonomy?version=&equipment_class=&code=&changed_since=&limit=&cursor=` | The full vocabulary at a version. Default `version` is the current published one. `changed_since` is the rebuild path | `required` | `none` | yes |
| `GET /taxonomy/entries/{code}?version=&equipment_class=` | One entry, resolved forward through supersession if the requested version is superseded (§6.4) | `required` | `none` | yes |
| `GET /taxonomy/versions` | The version register: every version, status, anchors, `m3_manual_revision`, release note | `required` | `none` | yes |
| `GET /taxonomy/definitions?version=` | The nine MIL-STD-3034A terms with clause references and verbatim text | `required` | `none` | yes |
| `GET /taxonomy/projections/pma?version=&equipment_class=` | The **coarsened PMA subset**: signatures including the novel escape. The projection PMA renders | `required` | `none` | yes |
| `GET /taxonomy/projections/3m?version=` | The 3-M code sets with `set_is_complete` and `source_revision`. The projection Scheduling renders | `required` | `none` | yes |
| `GET /equipment-families?version=&changed_since=&limit=&cursor=` | Family definitions | `required` | `none` | yes |
| `GET /equipment-families/{family_id}?version=` | One family | `required` | `none` | yes |
| `GET /part-families?niin=&version=&changed_since=&cursor=` | NIIN→family assignments (§2.7, subject to OD-5) | `required` | `none` | yes |
| `GET /crosswalk/pma-signatures?version=&signature_key=&code=&changed_since=&cursor=` | Signature↔code crosswalk, both directions | `required` | `none` | yes |
| `GET /crosswalk/3m-codes?version=&cause=&when_discovered=&action_taken=&eic=&changed_since=&cursor=` | `{CAUSE, WND, ACTION TAKEN, EIC}` → `candidate_modes[]` with confidence. **Always returns the full candidate set** | `required` | `none` | yes |
| `POST /taxonomy/resolve` | Bulk forward-resolution of held `(code, taxonomy_version)` references to a target version. Computational; no state change | `required` | `none` | yes |
| `POST /taxonomy/proposals` | Submit a novel signature or a vocabulary extension. Open to `pma`, `failure-intel`, `maintenance` | `required` | `proposal-only` | yes |
| `GET /taxonomy/proposals?status=&proposer=&cursor=` | Proposal queue | `required` | `none` | yes |
| `POST /taxonomy/proposals/{id}/claim` | Adjudication lease, per 03 §7.2. `If-Match` required | `required` | `state-changing` | no |
| `POST /taxonomy/proposals/{id}/adjudicate` | Approve or reject. **`failure-intel` authority only** (§7.1) | `required` | `state-changing` | no |
| `GET /taxonomy/export/data-dictionary?version=&format=` | The published data dictionary — the DoDI 8320.02 publication artifact (§7.3) | `required` | `none` | yes |
| `GET /taxonomy/export/geia-0007c?version=` | LSA-050 / LSA-058 export projection (08 §2.2) | `required` | `none` | yes |
| `POST /taxonomy/versions` | Open a draft version | `internal` | `state-changing` | no |
| `POST /taxonomy/versions/{version}/publish` | Publish a draft, freezing it (§6.3) | `internal` | `state-changing` | no |
| `POST /taxonomy/versions/{version}/entries` | Author entries into a draft | `internal` | `state-changing` | no |
| `POST /taxonomy/supersessions` | Record a supersession into a draft | `internal` | `state-changing` | no |
| `GET /healthz`, `GET /readyz`, `GET /metrics` | Per 03 §4 | `internal` | `none` | no |

### 3.2 Why `version` is a query parameter and not `GET /taxonomy/{version}`

Document 03 §4 is explicit: *"Identity | Canonical identifiers from §3.3 only. **Version selectors are query parameters, never path identifiers** `[C24]`."* `GET /taxonomy/{version}` reads naturally and is disallowed. `GET /taxonomy?version=1.0.0` is the conforming form and is what the OpenAPI contract publishes.

Two consequences worth recording:

- `GET /taxonomy` with no `version` returns the current published version and echoes it in the body and in an `ETag`. It never returns a draft.
- Document 04 §9 lists `GET /causal-feature-sets/{version}` on Failure Intelligence, which violates the same rule. It is not this document's to fix, but it should be raised — the pattern will be copied otherwise. Logged as OD-6.

### 3.3 Authority

| Actor | May read | May propose | May approve |
|---|---|---|---|
| `pma` | All projections and crosswalks | `novel_signature`, `crosswalk_revision` | No |
| `maintenance` | 3-M projection, crosswalks, families | `crosswalk_revision` | No |
| `failure-intel` | Everything | `new_failure_mode`, `crosswalk_revision`, `equipment_family_change` | **Yes — sole approval authority** |
| `pdm`, `design-advisory`, `fleet-status`, others | All read operations | No | No |
| Agents | Read operations and `POST /taxonomy/proposals` under delegated authority (03 §8.3) | Yes, as proposals | **Never** |

Approval is enforced at the API boundary against ABAC attributes per obligation 7 (03 §15) — never delegated to the gateway alone — and again by the `approver_is_authorised` constraint (§2.11). `blast_radius` for a vocabulary change is `class` or `fleet` by nature, so `requires_dual_control` is true for essentially every approval per document 03 §7.2.

### 3.4 Events

Reference Data publishes on `fathom.reference-data.taxonomy.v1` and `fathom.reference-data.proposal.v1`:

| Event | Consumers |
|---|---|
| `taxonomy_version.published` | `pma`, `maintenance`, `failure-intel`, `pdm`, `design-advisory`, `gateway`, `audit` |
| `taxonomy_entry.superseded` | `pma`, `maintenance`, `failure-intel`, `audit` |
| `crosswalk.published` | `pma`, `maintenance`, `failure-intel`, `audit` |
| `equipment_family.updated` | `pdm`, `supply`, `registry`, `audit` |
| `proposal.created`, `proposal.adjudicated`, `proposal.expired` | Per 03 §6's proposal convention |

⚠️ **Document 03 §6's event catalog covers the nine sub-applications and does not enumerate platform services.** These topics must be added to it, with consumers declared, before the consumer-driven conformance tests of document 03 §10 can be written against them. Logged as OD-7.

Per obligation 2, no state change without its event; per obligation 11, the transactional outbox is implemented without exception (03 §15).

### 3.5 Agent tool manifests

**[AMENDMENT — closes a BLOCKING gap.]** §3.1 marks fourteen operations `x-agent-eligible: yes` and this document named no manifest for any of them, though 35 §11.5 already refers to manifests existing against this service by inference. Flagged by `40-copilot.md` §16 correction 9 (blocking, downstream of correction 6's `ToolTargetSlug` widening in `10-shared-packages.md` §7.2).

`packages/agent-tooling/manifests/reference-data/`:

| Manifest | Consumer | Purpose | Operations |
|---|---|---|---|
| `reference-data-vocabulary-lookup.v1` | Maintainer Copilot | Resolve a taxonomy code, a MIL-STD-3034A term, an equipment family, or a 3-M crosswalk into readable text — never gloss one from parametric memory (01 §8.3) | `GET /taxonomy/entries/{code}?version=&equipment_class=`, `GET /taxonomy/definitions?version=`, `GET /equipment-families/{family_id}?version=`, `GET /crosswalk/3m-codes?version=&cause=&when_discovered=&action_taken=&eic=&…` |

**This manifest's selection is fully specified in `40-copilot.md` §4.2.6**, including the reason each operation is necessary rather than nice (a coded maintenance record is otherwise unrenderable except by guessing) and the deliberate exclusions (`POST /taxonomy/proposals` — `proposal-only`, foreclosed to this read-only agent; the full `GET /taxonomy` browse; export projections; every `internal` row). Reproduced here only by reference, per the convention `21-telemetry.md` §9.5 uses — the manifest's home is this service's directory and its conformance test belongs in this service's suite (03 §8.4).

Selects only `x-side-effects: none` operations, pins `api_major: 1`, ships a conformance test inside this service's suite, and declares a reviewed `purpose` (03 §8.5). Blocked, as of this writing, on `10-shared-packages.md` §7.2's `ManifestTarget.slug` widening — this service is a `PlatformServiceSlug`, not a `SubAppSlug`, and could not be named as a manifest target until that correction lands (it has, in this reconciliation pass).

---

## 4. Consumer integration — the three projections

Document 08 §2.8: *"One vocabulary, one owner, three declared projections."* Each consumer holds a **read-through cache** of its projection and nothing more (DO-NOT-1).

| Consumer | Projection | Retrieves via | Stores locally |
|---|---|---|---|
| **`pma`** | Coarsened subset keyed on `observable_signature`, plus the `unclassified/novel` escape. *"Reviewers select observable signatures, not mechanisms"* | `GET /taxonomy/projections/pma` | A cache keyed by `taxonomy_version`, refreshed on `taxonomy_version.published`. Its own `GET /taxonomy` (document 04 §8) remains in PMA's contract as a **read-through view of this service**, not an independent vocabulary |
| **`maintenance`** | The 3-M code sets, *"because maintainers must keep filing the 4790/2K and cannot be asked to learn a second vocabulary at the deckplate"* | `GET /taxonomy/projections/3m` | The code lists for form rendering and validation, with `set_is_complete` surfaced. **Never the crosswalk resolution** — findings are stored as filed, in 3-M codes |
| **`failure-intel`** | The full vocabulary, and sole authority to extend it | `GET /taxonomy` plus both crosswalks | Nothing normative. Its `FailureMode` aggregate (document 04 §9) references registry entries by `(lineage_id, taxonomy_version)`; its `Attribution` is the arbitration record |

**Edge behaviour.** Reference Data is enterprise-authoritative; under document 03 §11's default rule *"any aggregate not listed is enterprise-authoritative and not edge-writable."* An edge deployment holds the published version as a versioned package (§7.4) and pins to it for the duration of a disconnection. It cannot author entries, and it cannot approve a proposal — a novel-signature proposal raised afloat queues in the outbox and adjudicates ashore. Because the pinned version is explicit in every tag, a ship reviewing at `1.2.0` while shore has published `1.3.0` produces perfectly valid, resolvable labels. This is the direct payoff of invariant I1.

---

## 5. Seed data

Version `1.0.0`. Every value below is transcribed from document 08. Nothing is added.

The seed loader lives at `services/reference-data/seed/` and reads from fixture files that record, per row, the source document and clause. It refuses to set `is_verbatim = true` or `code_authority = 'iso-14224-verified'` on any value not present in the transcription fixture. This is what keeps the fabrication guard operative in the code path as well as in the schema.

### 5.1 MIL-STD-3034A definitions — nine terms, adopted verbatim (08 §2.3)

All quoted from MIL-STD-3034A §3. `taxonomy_version = '1.0.0'`, `is_verbatim = true`, `source_standard = 'MIL-STD-3034A Rev A'`.

| `term_key` | `clause` | `term_label` | `definition_text` |
|---|---|---|---|
| `functional_failure` | 3.9.1 | Functional failure | *"The inability of an item to perform a specific function within specified limits."* |
| `hidden_failure` | 3.9.2 | Hidden failure | *"A functional failure which is not observable to the operating crew during their routine duties."* |
| `potential_failure` | 3.9.3 | Potential failure | *"A definable and measurable condition that indicates a functional failure is imminent."* |
| `failure_cause` | 3.10 | Failure cause | *"The underlying stimulant of the failure or the root process which leads to failure, including defects in design, process, quality, maintenance, or part application."* |
| `failure_effects` | 3.11 | Failure effects | *"describe what happens when a failure mode occurs if no other action is taken."* |
| `failure_mode` | 3.12 | Failure mode | *"The specific condition causing a functional failure (often best described by the material condition at the point of failure)."* |
| `dominant_failure_mode` | 3.12.1 | Dominant failure mode | *"A cause of failure that is important because of a high probability and severity or high probability or severity of the failure."* |
| `failure_consequence` | 3.5.2 | Failure consequence | *"The measure of safety, environmental, mission, and economic impact of an item's functional failure caused by a specific failure mode."* |
| `functionally_significant_item` | 3.15.2 | Functionally significant item | *"An item whose functional failure has safety, statutory, regulatory, mission, or major economic consequences."* |

Three of these are load-bearing beyond documentation, per document 08 §2.3: 3.9.3 is the definition of the platform's core output and populates `potential_failure_def`; 3.12.1 is *"the natural prioritisation key for a prediction backlog"* and is `is_dominant`; 3.5.2's four consequence axes map onto `consequence_class` and the optimiser's consequence weighting.

⚠️ **Clause-reference discrepancy.** Document 08 §2.8's registry shape annotates `evident_or_hidden` as *"MIL-STD-3034A 3.13.2 / 3.13.3"*, but §2.3's transcribed definitions place hidden failure at **3.9.2**. Clauses 3.13.2 and 3.13.3 are not among the nine verified definitions. The `evident` / `hidden` column values are safe; the clause citation is not, and must not be printed in the data dictionary until confirmed against the standard. Logged as OD-3.

### 5.2 ISO 14224 failure-mode codes — seven verified (08 §2.4)

Document 08 §2.4: *"Failure modes are three-letter codes. Verified examples: …"*. `code_authority = 'iso-14224-verified'`.

| `code` | `definition_text` |
|---|---|
| `AIR` | abnormal instrument reading |
| `BRD` | breakdown |
| `ELP` | external leakage, process medium |
| `ELU` | external leakage, utility medium |
| `FTS` | failure to start on demand |
| `PLU` | plugged or choked |
| `STD` | structural deficiency |

**These seven are the entire verified code set. No eighth code exists in any verified source available to the program.**

⚠️ **UNVERIFIED — ISO 14224 Annex B is paywalled.** Document 08 §2.4: *"The complete Annex B code set is UNVERIFIED and paywalled. Six retrieval routes were attempted without success. Recommendation: purchase the standard. It is a roughly $300 purchase that directly de-risks the program's central data-model decision, and no free substitute exists."* The same paywall covers the ISO 14224 **cause code** list (§2.4 of this document) and the **detection method** list (§2.5), both of which are referenced by the `FailureModeEntry` shape and both of which seed empty.

⚠️ **ISO 14224 level labels are also unconfirmed.** Document 08 §2.4: *"Two implementation guides differ on the exact normative labels for levels 6–9. The structural claim is consistent; confirm labels against the purchased standard before publishing a data dictionary."* Since §7.3 makes publishing a data dictionary the DoDI 8320.02 compliance act, this is a **blocker on the publication claim**, not a documentation nicety. The nine-level structure seeds as:

| ISO 14224 level | Maps to | FATHOM binding |
|---|---|---|
| 1–5 (industry → plant) | Navy → domain → class → hull → plant | Context; `AssetRef.domain`, `class_id`, `uic` (03 §3.3) |
| **6 — equipment class** | ESWBS / EIC | `failure_mode_entry.equipment_class`. Class code, never a join key |
| **7 — subunit** | Equipment subdivision | `failure_mode_entry.subdivision` |
| **8 — maintainable item** | `InstalledItem`, identified by IUID | `failure_mode_entry.maintainable_item` (item type — see §2.3 note and OD-4) |
| **9 — part** | NIIN | `PartRef.niin`, and the `part_family_assignment` key |

### 5.3 Navy 3-M code sets (08 §2.5)

All rows: `source_revision = 'NAVSEAINST 4790.8B (2003-11-13)'`, `taxonomy_version = '1.0.0'`.

Document 08 §2.5 also corrects a premise the program should stop repeating: *"'How Malfunctioned' is not a field on the OPNAV 4790/2K. It belongs to the Naval Aviation Maintenance Program lineage (VIDS/MAF, OPNAV 4790/60)."* No such field is seeded.

**CAUSE (CAS)** — `set_is_complete = true`. Definition from the manual: *"The code best describing the cause of the failure or malfunction when need for maintenance was first discovered… this field provides valuable data to the equipment manager; without it, only the fact that the equipment failed is known."*

| `code` | `label` |
|---|---|
| `1` | abnormal environment |
| `2` | manufacturer or installation defects |
| `3` | lack of knowledge or skill |
| `4` | communications problem |
| `5` | inadequate instruction or procedure |
| `6` | inadequate design |
| `7` | normal wear and tear |
| `8` | corrosion condition |
| `0` | other or no malfunction |

**WHEN DISCOVERED (WND)** — `set_is_complete = true`.

| `code` | `label` |
|---|---|
| `1` | lighting off or starting |
| `2` | normal operation |
| `3` | during operability tests |
| `4` | during inspection |
| `5` | shifting operational modes |
| `6` | during PMS |
| `7` | securing |
| `8` | during AEC program |
| `9` | no failure, PMS accomplishment only |
| `0` | not applicable |

**ACTION TAKEN** — two characters. First character `set_is_complete = **false**`; document 08 §2.5 gives *"a fixed list (`1` … `2` … `3` … `4` cancelled · **and others**)"*. Only the four documented values are seeded.

| `code` | `label` |
|---|---|
| `1` | completed with parts from supply |
| `2` | completed, parts not drawn |
| `3` | completed, no parts required |
| `4` | cancelled |

**ACTION TAKEN modifiers** (`ACTION_TAKEN_MODIFIER`), applicable to first characters `1`/`2`/`3`, `set_is_complete = false`:

| `code` | `label` |
|---|---|
| `A` | *"maintenance requirement could have been deferred"* |
| `B` | *"was necessary"* |
| `C` | *"should have been done sooner"* |

The **second character is TYCOM-specified** and is therefore not a platform enumeration at all. It is stored as filed and passed through; the demo defines no values for it.

⚠️ **The 3-M seed is baselined on a 2003 revision.** Document 08 §2.5: *"Revisions C and D exist. Re-baseline every code list against the current revision before implementation and treat any delta as a taxonomy version bump."* The `m3_manual_revision` column on `taxonomy_version` exists to make the re-baseline an explicit major version event. Logged as OD-2.

### 5.4 The seed set is too small for tier-2/3 demonstration — an open program decision

Seven failure-mode codes cannot cover the equipment populations a tier-2/tier-3 demonstration requires. Failure Intelligence needs enough mode granularity for attribution to be non-trivial; PMA's coarsened subset needs enough signatures for review to look like review; the 3-M crosswalk needs enough candidate modes for its many-to-many character to be visible rather than theoretical. **With seven codes, the crosswalk degenerates toward one-to-one and the design's central property becomes untestable.**

**This is not resolved here.** Two paths, and the program must choose:

**(a) Purchase ISO 14224:2016 and transcribe Annex B.** Roughly $300. Document 08 §2.4 already recommends it: *"directly de-risks the program's central data-model decision, and no free substitute exists."* It additionally unblocks the cause code list, the detection method list, and the level 6–9 normative labels — which §7.3 makes a prerequisite of the publication claim. **Recommended.** Seeded codes get `code_authority = 'iso-14224-transcribed'`.

**(b) Synthesise placeholder codes in a clearly-marked extension namespace.**

- **Naming convention: `FATHOM-EXT-nnn`**, where `nnn` is a zero-padded ordinal (`FATHOM-EXT-001`). ISO 14224 failure-mode codes are exactly three uppercase letters; a hyphenated, prefixed, digit-bearing form **cannot collide with any present or future ISO code**, which is the whole point of the convention.
- Every such row carries `code_authority = 'fathom-extension'`, enforced by the `extension_codes_are_namespaced` CHECK constraint (§2.3).
- The API renders them with an explicit `code_authority` field, never flattened away; the data dictionary export (§7.3) segregates them under a heading naming them as program placeholders and not standard content; the reviewer-facing PMA projection labels them visibly.
- On acquiring the standard, each placeholder is **superseded** to its real ISO code via `taxonomy_supersession` with `relation = 'renamed'` — which is exactly the mechanism §6 exists to support, so the migration is non-destructive and historical labels survive it. This is a genuine advantage of (b) as a bridge rather than a substitute for (a).

The cost of (b) alone is that no conformance or interoperability claim against ISO 14224 can be made, GEIA-STD-0007C export carries non-standard codes, and the DoDI 4151.22 §1.2.j argument for open standards is weakened precisely where it was strongest. **The recommendation is (a), with (b) as a bridge until the purchase clears.** Logged as **OD-1** — the highest-priority open decision in this document.

### 5.5 Equipment families

**No external standard supplies an equipment-family enumeration.** Document 03 §3.3 defines the concept and its ownership; nothing in documents 01, 03, or 08 enumerates values. The seed is therefore **program-defined content**, and is marked as such — it is not standard content and must never be presented as such.

Phase 3 derives the family list from the demonstration NIIN set in the Asset & Configuration Registry, under the constraint that a family must be a valid partition for model binding and calibration (03 §14: PdM binds tier and family). Naming convention: lowercase kebab-case slugs. No specific families are asserted in this document, because inventing them here would be exactly the fabrication this document prohibits elsewhere. The §8.2 conformance test asserts total NIIN coverage once the list exists — which is what makes *"required attribute of every part"* enforceable rather than aspirational.

### 5.6 Crosswalk seed

Both crosswalks seed with only those rows whose `basis` can be stated in a sentence a reliability engineer would sign. With seven codes and nine 3-M cause values, the honest initial 3-M crosswalk is sparse and heavily many-to-many — for example, CAUSE `7` *normal wear and tear* is consistent with several modes and by itself distinguishes none of them. **Sparse and ambiguous is the correct initial state.** Filling the matrix to look complete is the exact failure document 08 §2.8 names: *"the most common way maintenance-derived training data goes bad."*

Every crosswalk row requires `adjudicated_by` — a Failure Intelligence identity — including seed rows. Seed content is adjudicated content, not a bypass.

---

## 6. Versioning and non-destructive revision

Document 08 §2.8's reconciliation rule for PMA states the requirement: *"Because tags are append-only and never overwritten (document 03 §11), a taxonomy revision **never rewrites historical tags** — it records a crosswalk, and superseded tags retain both codes."* Reference Data's job is to make that resolvable years later.

### 6.1 The mechanism

1. **Draft.** `POST /taxonomy/versions` opens a draft at the next semver per the §2.1 policy. Drafts are invisible to `GET /taxonomy` without an explicit `version`.
2. **Author.** New and revised entries are inserted as **new rows** carrying the draft version. An entry whose semantics change gets a new `entry_id` under the **same `lineage_id`**. Rows in prior published versions are not touched.
3. **Supersede.** Where an entry is retired, renamed, split, or merged, a `taxonomy_supersession` record links predecessor lineage to successor lineage with `relation`, `rationale`, `confidence`, and `adjudicated_by`. `failure_mode_entry.superseded_by_entry_id` / `superseded_at` are set on the **old row** — the only mutation any published row ever receives.
4. **Crosswalk.** Crosswalk rows are inserted for the new version. Prior-version crosswalk rows remain queryable exactly as published.
5. **Publish.** `POST /taxonomy/versions/{version}/publish` sets `status = 'published'` with provenance, freezes the version (§6.3), emits `taxonomy_version.published`, and cuts a package release (§7.4).

### 6.2 What consumers hold, and why nothing breaks

A PMA tag holds `(signature_key, taxonomy_version)`. A Scheduling findings record holds 3-M codes as filed plus `taxonomy_version`. A Failure Intelligence attribution holds `(lineage_id, taxonomy_version)`. **All three remain byte-identical across every future version bump.** Meaning is recovered by resolving the held version forward, on demand, at read time (§6.4). Nothing is rewritten, nowhere, ever — which is what makes a training set assembled in 2029 across labels from 2026 and 2027 auditable rather than *"silently corrupt"* (08 §2.8 non-negotiable 1).

### 6.3 Enforcement — a trigger, not a convention

```sql
CREATE OR REPLACE FUNCTION reference_data.forbid_published_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    v_status reference_data.version_status;
BEGIN
    SELECT status INTO v_status
      FROM reference_data.taxonomy_version WHERE version = OLD.taxonomy_version;

    IF v_status = 'draft' THEN
        RETURN NEW;                          -- drafts are freely editable
    END IF;

    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'taxonomy entries in a published version cannot be deleted (entry %)',
            OLD.entry_id;
    END IF;

    -- The ONLY permitted mutation of a published row: supersession marking, once.
    IF ROW(NEW.*) IS DISTINCT FROM ROW(OLD.*) THEN
        IF OLD.superseded_by_entry_id IS NOT NULL THEN
            RAISE EXCEPTION 'entry % is already superseded; supersession is write-once',
                OLD.entry_id;
        END IF;
        IF (NEW.code, NEW.equipment_class, NEW.subdivision, NEW.maintainable_item,
            NEW.functional_failure_ref, NEW.failure_effect, NEW.consequence_class,
            NEW.evident_or_hidden, NEW.is_dominant, NEW.observable_signature,
            NEW.potential_failure_def, NEW.definition_text, NEW.taxonomy_version)
         IS DISTINCT FROM
           (OLD.code, OLD.equipment_class, OLD.subdivision, OLD.maintainable_item,
            OLD.functional_failure_ref, OLD.failure_effect, OLD.consequence_class,
            OLD.evident_or_hidden, OLD.is_dominant, OLD.observable_signature,
            OLD.potential_failure_def, OLD.definition_text, OLD.taxonomy_version)
        THEN
            RAISE EXCEPTION
              'semantic columns of a published taxonomy entry are immutable (entry %); '
              'author a new entry under the same lineage_id and record a supersession',
              OLD.entry_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER fme_published_immutable
    BEFORE UPDATE OR DELETE ON reference_data.failure_mode_entry
    FOR EACH ROW EXECUTE FUNCTION reference_data.forbid_published_mutation();
```

Equivalent triggers apply to `milstd_3034a_term`, `navy_3m_code`, `crosswalk_pma_signature`, `crosswalk_3m`, `pma_signature`, and `equipment_family`. Crosswalk and code-set rows admit **no** permitted mutation at all: they are insert-only within a draft and frozen at publication.

A database-level guarantee matters here because the failure mode is a well-intentioned `UPDATE` that fixes a typo in a definition — after which every label assigned under that version means something slightly different than it did, undetectably. The trigger turns that into an error at the point of the attempt.

### 6.4 Forward resolution

```sql
-- Resolve a held (code, taxonomy_version) reference to its representation at a target version.
WITH RECURSIVE forward AS (
    SELECT e.lineage_id, 0 AS hops
      FROM reference_data.failure_mode_entry e
     WHERE e.code = :held_code
       AND e.taxonomy_version = :held_version
  UNION ALL
    SELECT s.superseding_lineage_id, f.hops + 1
      FROM forward f
      JOIN reference_data.taxonomy_supersession s
        ON s.superseded_lineage_id = f.lineage_id
     WHERE s.superseding_lineage_id IS NOT NULL
       AND f.hops < 32                       -- cycle guard
)
SELECT DISTINCT e.*, f.hops
  FROM forward f
  JOIN reference_data.failure_mode_entry e
    ON e.lineage_id = f.lineage_id
   AND e.taxonomy_version = :target_version
 ORDER BY f.hops;
```

Three properties of this query are the contract, exposed as `POST /taxonomy/resolve`:

- **It returns a set, not a row.** A `split` resolves to several successors. Callers receive all of them.
- **A held version is never refused.** `GET /taxonomy?version=1.0.0` serves `1.0.0` as published even at current `4.7.0`. Deprecated versions remain readable; `status = 'deprecated'` signals "do not assign new labels", never "cannot resolve".
- **`hops = 0` means the reference is still current.** Consumers can distinguish "unchanged" from "resolved through supersession" and record which, in provenance.

---

## 7. Governance and publication

### 7.1 Propose versus approve

| Step | Actor | Mechanism |
|---|---|---|
| Propose | `pma` (novel signatures from review), `failure-intel` (new modes, crosswalk revisions), `maintenance` (crosswalk revisions), or an agent under delegated authority | `POST /taxonomy/proposals` — `x-side-effects: proposal-only`, evidence required and non-empty with `source_trust` (03 §7.2) |
| Claim | Failure Intelligence adjudicator | `POST /taxonomy/proposals/{id}/claim`, lease-based, `If-Match` on the claimed ETag. Without the claim, an eventually-consistent queue permits two approvals (03 §7.2) |
| Approve or reject | **Failure Intelligence only** | `POST /taxonomy/proposals/{id}/adjudicate`. Dual control required at `class` and `fleet` blast radius, which is nearly all vocabulary change |
| Author | Reference Data, into an open draft | Approval does not publish. It authorises authoring |
| Publish | Reference Data | `POST /taxonomy/versions/{version}/publish` |

The split is doctrinal, from document 08 §2.8: Failure Intelligence *"Owns the content; Reference Data owns registry, versioning, and publication."* Reference Data never decides what a failure mode is. Failure Intelligence never publishes a version.

Re-validation at approval is mandatory per document 03 §7.2: the proposal's `against_version` and payload are re-checked at adjudication time, and a proposal against a version superseded since submission is rejected with a resolution hint rather than approved against stale content.

### 7.2 The novel-signature path

Document 08 §2.8: *"Novel signatures become proposals to Reference Data, adjudicated by Failure Intelligence."* Concretely: a reviewer selects the `is_novel_escape` signature and describes what they saw. PMA stores that tag — it is valid data, not an error — and emits a `novel_signature` proposal. Failure Intelligence adjudicates. If approved, a new entry and a new signature crosswalk row are authored into the next draft. The original tag is **never rewritten**; on publication it resolves through the crosswalk to the new entry, and both the escape tag and the resolved mode are visible. That is the same non-destructive machinery as §6, applied to novelty rather than revision.

### 7.3 What "published" means — the DoDI 8320.02 obligation

DoDI 8320.02 requires authoritative data sources to be registered and *"structural metadata, including vocabularies, taxonomies, and ontologies"* to be published. Document 08 §2.8 names it the forcing function for single ownership. Publication is satisfied by **all four** of the following, not by any one:

1. **A served schema endpoint.** `GET /taxonomy/export/data-dictionary?version=&format=` returns the machine-readable dictionary: every entry, definition with clause reference, code set with `source_revision` and `set_is_complete`, both crosswalks with confidences, the supersession graph, and the standards anchors. Formats: JSON and CSV. Plus the OpenAPI 3.1 contract itself, generated from code and published to the contracts package.
2. **A human-readable data dictionary export.** The same content rendered for review and for inclusion in accreditation and delivery artifacts. **Blocked on OD-1 and the level-label confirmation of §5.2** — a dictionary asserting unconfirmed ISO level labels or unmarked synthesised codes is worse than none, because it converts an internal uncertainty into a published claim.
3. **Registration as the authoritative source.** A registry record naming `reference-data` as the single authoritative source for the FATHOM unified taxonomy and for `equipment_family`, with the endpoint, owner, and version cadence. The program action is to identify the applicable DoD data catalog and file it; this document cannot complete that step, and it is the residue of OD-8.
4. **The versioned package** (§7.4), so build-time consumers pin the same content the endpoint serves.

Document 08 §2.8 non-negotiable 2 governs artifact 1 and 2 jointly: *"The crosswalk is a delivered, reviewable artifact, not a mapping buried in code. It is what a substituting implementation must reproduce under document 03 §10, and it is the DoDI 8320.07 obligation to register vocabularies and business rules."* A crosswalk that exists only as a SQL table with no export does not satisfy this.

### 7.4 Distribution

Document 04 §11: *"Distributed as a versioned package and served for runtime resolution."* Both, and they are the same content:

- **Package.** `packages/reference-data-taxonomy`, released on every published version, carrying the frozen dataset, generated types, and the resolution helper. Consumed at build time. Publication mechanics and versioning discipline per `docs/build/10-shared-packages.md`.
- **Runtime.** The API above, for consumers that must resolve a version they did not build against — which includes every consumer reading historical labels.

A CI check asserts the package contents are byte-identical to what `GET /taxonomy/export/data-dictionary` serves for that version. Two publication channels that can disagree are one channel and one bug.

---

## 8. Testing

Conformance suite at `packages/contracts/conformance/reference-data/`, structured per document 03 §10: contract, event, fault-injection, consumer-driven, manifest, and a reference dataset. Test IDs below are the suite's stable names.

### 8.1 Consumer projection conformance — the C8 regression guard

One test per consumer, contributed by that consumer per document 03 §10's consumer-driven requirement. Each asserts the consumer can obtain **everything it needs from this service alone**.

| Test | Asserts |
|---|---|
| `tax-proj-pma` | `GET /taxonomy/projections/pma` returns a non-empty coarsened signature set for every `equipment_class` in the reference dataset, including exactly one `is_novel_escape` row; every signature resolves to ≥1 entry via `GET /crosswalk/pma-signatures`; the response echoes `taxonomy_version` |
| `tax-proj-3m` | `GET /taxonomy/projections/3m` returns all nine CAUSE values, all ten WHEN DISCOVERED values, and the ACTION TAKEN first-character and modifier sets with `set_is_complete = false` and `source_revision` present on every row |
| `tax-proj-fi` | `GET /taxonomy` returns the full vocabulary with all fourteen `FailureModeEntry` fields present on every entry (arrays may be empty, keys may not be absent); `GET /taxonomy/definitions` returns all nine MIL-STD-3034A terms with clause references |
| `tax-proj-pdm` | `GET /equipment-families` and `GET /part-families` cover every NIIN in the reference dataset — no part lacks a family (finding D35) |
| `tax-single-source` | **The C8 guard.** A static check over the monorepo asserting no sub-application package contains a taxonomy literal — no hard-coded failure-mode code list, 3-M code list, signature list, or family list outside `packages/reference-data-taxonomy` and this service. Fails the build on violation |

### 8.2 Non-destructive revision

| Test | Asserts |
|---|---|
| `tax-ver-freeze` | After publishing `1.0.0`, an `UPDATE` of any semantic column raises; a `DELETE` raises; a second supersession marking raises. Executed against the live trigger, not mocked |
| `tax-ver-historical-labels` | Publish `1.0.0`; snapshot every row of every table with its hash; publish `2.0.0` including a rename, a split, a merge, and a deprecation; **re-snapshot and assert every `1.0.0` row is unchanged except for `superseded_by_entry_id`/`superseded_at` on the specific superseded entries.** This is the test that proves *"a taxonomy revision never rewrites historical tags"* |
| `tax-ver-resolve-old` | A reference held at `1.0.0` resolves at `2.0.0` for every relation type: `renamed` → 1 result, `split` → n>1 results, `merged` → 1 result reached from each predecessor, `deprecated` with no successor → empty result plus an explicit deprecation reason rather than a 404 |
| `tax-ver-serve-old` | `GET /taxonomy?version=1.0.0` returns `1.0.0` content byte-identical to the published snapshot after arbitrarily many subsequent publications |
| `tax-ver-semver` | A version containing a supersession cannot publish as a minor or patch bump; an additive-only version cannot publish as a major bump |
| `tax-ver-package-parity` | The released package for a version is byte-identical to the data dictionary export for that version (§7.4) |

### 8.3 Crosswalk cardinality — the "don't flatten it" guard

| Test | Asserts |
|---|---|
| `tax-xw-3m-cardinality` | The reference dataset contains at least one 3-M tuple mapping to **two or more** candidate modes with distinct confidences, and `GET /crosswalk/3m-codes` for that tuple returns **all** of them. Fails if the response is scalar-valued or truncated |
| `tax-xw-3m-no-unique` | Inspects `pg_indexes` and fails if any unique index or constraint exists over `(taxonomy_version, cause_code, when_discovered_code, action_taken_code, eic_prefix)` **without** `candidate_entry_lineage`. This is a structural guard against the specific future migration that would silently make the mapping one-to-one |
| `tax-xw-3m-no-primary` | Fails if a column named `is_primary`, `primary_mode`, `best_match`, or equivalent exists on `crosswalk_3m` (DO-NOT-2) |
| `tax-xw-pma-cardinality` | At least one signature maps to ≥2 entries and at least one entry maps to ≥2 signatures, and both directions of `GET /crosswalk/pma-signatures` return complete sets |
| `tax-xw-eic-prefix` | A findings tuple carrying a 7-character EIC matches a crosswalk row whose `eic_prefix` is 4 characters; a 4-character EIC does not match a 7-character prefix. Prefix semantics, not equality (08 §2.6) |
| `tax-xw-reconcile-retains` | The §9 reconciliation query over a deliberately disagreeing tag/finding pair returns **both** interpretations with an `agreement` classification, and never collapses to one. Fails if any candidate is dropped |

### 8.4 Fabrication and provenance guards

| Test | Asserts |
|---|---|
| `tax-seed-verbatim` | All nine MIL-STD-3034A definitions match the transcription fixture character-for-character, and no row has `is_verbatim = true` without a fixture entry |
| `tax-seed-code-authority` | Exactly the seven verified codes carry `code_authority = 'iso-14224-verified'`. Any additional three-letter code fails the build. Any `fathom-extension` code not matching `^FATHOM-EXT-[0-9]{3}$` fails |
| `tax-seed-3m-exact` | CAUSE and WHEN DISCOVERED labels match the transcription fixture exactly; ACTION TAKEN sets carry `set_is_complete = false` |
| `tax-seed-unverified-marked` | The data dictionary export contains the paywall caveat for Annex B, the cause code list, the detection method list, the level 6–9 labels, and the 4790.8B baseline. **A dictionary that omits any of them fails the build** |
| `tax-gov-approval-authority` | A proposal approval attempted by `pma` or `maintenance` identity is rejected at the API boundary **and** by the database constraint. Both layers tested independently |
| `tax-gov-evidence-required` | A proposal with empty `evidence` is rejected at the API boundary (03 §7.2) |
| `tax-gov-claim-required` | Adjudication without a held claim, or with a stale ETag, returns 412 |

### 8.5 Platform obligations

Per document 03 §10 and §15: `changed_since` snapshot reads over every projected aggregate; cursor pagination; RFC 9457 problem details; `ETag`/`If-Match`; `Idempotency-Key` on all unsafe methods; `X-Correlation-Id` propagation; `X-Classification` on every response; fault injection asserting no state change without its event; OpenAPI annotation coverage — `x-substitution` and `x-side-effects` on **every** operation, with `x-agent-eligible` only where side effects are `none` or `proposal-only`.

---

## 9. Crosswalk semantics — read-time reconciliation

The scenario: Failure Intelligence is assembling evidence on one installed item. PMA confirmed a tag at `taxonomy_version = '1.0.0'` using an observable signature. Scheduling filed a findings record at `'1.1.0'` using 3-M codes. They used different vocabularies. Failure Intelligence needs both, at its own working version.

### 9.1 The join pattern

```sql
WITH target AS (SELECT :target_version::text AS v),

-- PMA side: signature -> candidate modes, at the version the tag was assigned under,
-- then forward-resolved to the target version.
pma_side AS (
    SELECT DISTINCT
           r.lineage_id,
           x.confidence,
           'pma'::text AS source,
           :pma_signature_key AS source_term,
           :pma_tag_version  AS source_version
      FROM reference_data.crosswalk_pma_signature x
      JOIN reference_data.resolve_forward(x.entry_lineage_id,
                                          :pma_tag_version,
                                          (SELECT v FROM target)) AS r(lineage_id) ON true
     WHERE x.signature_key     = :pma_signature_key
       AND x.taxonomy_version  = :pma_tag_version
),

-- Scheduling side: the 3-M tuple -> candidate_modes[] with confidence. NULL crosswalk
-- elements are unconstrained; eic matches by PREFIX because EIC specificity varies (08 §2.6).
m3_side AS (
    SELECT DISTINCT
           r.lineage_id,
           c.confidence,
           'maintenance'::text AS source,
           concat_ws('/', :cas, :wnd, :act, :eic) AS source_term,
           :finding_version AS source_version
      FROM reference_data.crosswalk_3m c
      JOIN reference_data.resolve_forward(c.candidate_entry_lineage,
                                          :finding_version,
                                          (SELECT v FROM target)) AS r(lineage_id) ON true
     WHERE c.taxonomy_version = :finding_version
       AND (c.cause_code           IS NULL OR c.cause_code           = :cas)
       AND (c.when_discovered_code IS NULL OR c.when_discovered_code = :wnd)
       AND (c.action_taken_code    IS NULL OR c.action_taken_code    = :act)
       AND (c.eic_prefix           IS NULL OR :eic LIKE c.eic_prefix || '%')
)

SELECT e.code,
       e.definition_text,
       e.consequence_class,
       e.is_dominant,
       p.confidence AS pma_confidence,
       m.confidence AS m3_confidence,
       CASE WHEN p.lineage_id IS NOT NULL AND m.lineage_id IS NOT NULL THEN 'both'
            WHEN p.lineage_id IS NOT NULL                              THEN 'pma_only'
            ELSE 'maintenance_only'
       END AS agreement,
       p.source_term    AS pma_term,     p.source_version AS pma_version,
       m.source_term    AS m3_term,      m.source_version AS m3_version
  FROM pma_side p
  FULL OUTER JOIN m3_side m ON m.lineage_id = p.lineage_id
  JOIN reference_data.failure_mode_entry e
    ON e.lineage_id = coalesce(p.lineage_id, m.lineage_id)
   AND e.taxonomy_version = (SELECT v FROM target)
 ORDER BY (coalesce(p.confidence, 0) + coalesce(m.confidence, 0)) DESC;
```

`resolve_forward(lineage_id, from_version, to_version)` is the §6.4 recursive CTE packaged as a set-returning function, so the same resolution logic serves the API, the package helper, and this query. One implementation, one behaviour.

### 9.2 The four properties that make this correct

- **`FULL OUTER JOIN`, never `INNER`.** An inner join returns only the modes both vocabularies agree on — which is precisely the disagreement data being thrown away. `pma_only` and `maintenance_only` rows are the interesting ones.
- **Resolution happens per side, at each side's own held version.** Both are then compared at the target. Resolving both at the target version directly would assume they were assigned under it.
- **`agreement` is an output column, not a filter.** The caller receives the classification. Nothing upstream decides on their behalf.
- **The result is ranked, never truncated.** `ORDER BY` combined confidence is a presentation convenience. Dropping low-confidence candidates converts a lossy many-to-many mapping into a false one-to-one at the last possible moment, which is the failure this whole design exists to prevent.

### 9.3 Disagreement is a retained signal, not a defect

Restated from document 08 §2.8, because it is the rule most likely to be optimised away by a well-meaning implementer:

> Failure Intelligence *"Owns the content; Reference Data owns registry, versioning, and publication. Its `Attribution` is the arbitration record when a tag and a findings code disagree. **That disagreement is a retained first-class signal, not an error to clean.**"*

And non-negotiable 3:

> *"**Reconcile at read time, never at write time.** Each capture point stores what its user actually asserted, in that user's vocabulary; the unified view is computed. **Normalising on write destroys the disagreement data that is the entire reason for having three capture points.**"*

Operationally: a reviewer watching telemetry saw an abnormal instrument reading; a maintainer who opened the pump filed *normal wear and tear*. Neither is wrong and they are not the same claim. If the write path had normalised both to one code, the fact that the observable signature and the physical finding pointed different directions — which is exactly the kind of fact that improves a detector, invalidates a signature, or reveals a second failure mode — would not exist anywhere in the system. Reference Data supplies the crosswalks and the resolution function; it does not supply an answer, because there is no single answer to supply.

---

## 10. Explicit DO-NOT list

**DO-NOT-1 — No consuming sub-application embeds taxonomy content beyond a read-through cache.**
Not a hard-coded code list "for the demo". Not a signature enum in a form component. Not a 3-M code list in a validation module. Not a family list in a model-binding config. A read-through cache keyed by `taxonomy_version`, invalidated on `taxonomy_version.published`, is the only permitted local copy, and it is a copy of served content — never an independent definition. Enforced by `tax-single-source` (§8.1). *This is finding C8. It was fixed once; the build must not reintroduce it.*

**DO-NOT-2 — Do not force the many-to-many crosswalk into a one-to-one mapping.**
No unique index on the 3-M tuple alone. No `is_primary` / `best_match` / `primary_mode` column. No API response that returns a scalar mode where the data holds a set. No consumer-side `LIMIT 1` on a candidate list. Document 08 §2.8: 3-M CAUSE *"is a cause code, not a mode code"*, the mapping is *"many-to-many and lossy by construction"*, and forcing it is *"the most common way maintenance-derived training data goes bad."* Enforced by `tax-xw-3m-no-unique` and `tax-xw-3m-no-primary`.

**DO-NOT-3 — Do not fabricate ISO 14224 codes.**
Only the seven verified codes may carry `code_authority = 'iso-14224-verified'`. Any program-synthesised code lives in the `FATHOM-EXT-nnn` namespace with `code_authority = 'fathom-extension'`, is visibly marked everywhere it is rendered, and is segregated in the data dictionary. Inventing a plausible-looking three-letter code is a compliance misstatement, not a shortcut. Enforced by the `extension_codes_are_namespaced` constraint and `tax-seed-code-authority`.

**DO-NOT-4 — Do not omit the UNVERIFIED caveats from published artifacts.**
The data dictionary and every published export must carry: Annex B is paywalled and unverified; the ISO cause code and detection method lists are unverified; the ISO level 6–9 labels differ between implementation guides and are unconfirmed; the 3-M code sets are baselined on NAVSEAINST 4790.8B (2003) with revisions C and D extant; MIL-STD-3034A clauses 3.13.2/3.13.3 are cited by the source schema but were not verified. Enforced by `tax-seed-unverified-marked`.

**DO-NOT-5 — Do not mutate a published version.**
Not to fix a typo. Not to correct a mistranslated definition. Author a new version and record a supersession. A silent edit changes the meaning of every label already assigned under that version, undetectably and irreversibly.

**DO-NOT-6 — Do not let Reference Data adjudicate vocabulary content.**
Failure Intelligence approves. Reference Data operates registry, versioning, and publication. A convenience path letting a Reference Data operator add an entry without adjudication recreates a second content owner.

**DO-NOT-7 — Do not use `equipment_class`, `eswbs`, or EIC as a join key.**
Class codes of variable specificity, per document 03 §3.3 and document 08 §2.6. Join on `system_id`, `installed_item_id`, `niin`, `lineage_id`. Instance identity is IUID (08 §2.8 non-negotiable 4).

**DO-NOT-8 — Do not normalise on write, anywhere, for any consumer's convenience.**
Including a "helpful" endpoint that accepts a 3-M tuple and returns one mode for storage. If such an operation exists, some consumer will store its output as a label and the disagreement signal is gone.

---

## 11. Open decisions

| ID | Decision | Owner | Consequence if unresolved |
|---|---|---|---|
| **OD-1** | **Purchase ISO 14224:2016 and transcribe Annex B (recommended), or adopt `FATHOM-EXT-nnn` placeholders as a bridge (§5.4)** | Program management + Failure Intelligence | Seven codes cannot support a tier-2/3 demonstration, and the crosswalk's many-to-many character becomes untestable. Also blocks the cause code list, the detection method list, the level 6–9 labels, and therefore the §7.3 data dictionary |
| **OD-2** | Re-baseline the 3-M code sets against NAVSEAINST 4790.8C/8D (08 §2.5) | Program, with 3-M SME | Codes are 23 years stale; any delta is a major version bump post-launch, invalidating in-flight labels' comparability |
| **OD-3** | Confirm MIL-STD-3034A clauses 3.13.2 / 3.13.3 for `evident_or_hidden`, or re-cite to 3.9.2 (§5.1) | Failure Intelligence | A published dictionary would carry an unverified clause citation |
| **OD-4** | Confirm that `maintainable_item` carries an item **type** at ISO L8 rather than an instance IUID (§2.3) | Failure Intelligence + Registry | Read as instance identity, the registry grows to fleet size and one entry exists per serial number |
| **OD-5** | Confirm Reference Data owns the NIIN→`equipment_family` **assignment**, not only the family definition (§2.7) | Registry + Supply + PdM | Supply and Registry each assign independently, which is finding C8 in a different costume |
| **OD-6** | Correct `GET /causal-feature-sets/{version}` on Failure Intelligence to a query-parameter selector (document 03 §4 `[C24]`, §3.2 here) | Failure Intelligence | An inconsistent version-selector convention propagates by imitation |
| **OD-7** | Add `fathom.reference-data.*` topics and their consumers to document 03 §6's event catalog (§3.4) | Architecture | Consumer-driven conformance tests for these topics cannot be written |
| **OD-8** | Identify the applicable DoD data catalog and file the DoDI 8320.02 authoritative-source registration (§7.3) | Program compliance | Single ownership is built but the registration claim is unfiled, which is the compliance obligation this service exists to satisfy |

---

## 12. Definition of Done

The shared Definition of Done template in `docs/build/09-monorepo-and-conventions.md` applies in full — OpenAPI 3.1 generated from code and CI-validated, annotation coverage, migrations, observability, classification labelling, outbox, and conformance suite green.

Service-specific additions, all of which must hold:

1. **Seed loads and validates.** Version `1.0.0` publishes with the nine MIL-STD-3034A definitions, the seven verified ISO 14224 codes, and the 3-M code sets exactly as transcribed in §5. `tax-seed-*` green.
2. **All three projections retrievable.** `tax-proj-pma`, `tax-proj-3m`, `tax-proj-fi`, `tax-proj-pdm` green, contributed by each consumer.
3. **`tax-single-source` green** — no taxonomy literal anywhere in the monorepo outside this service and its package.
4. **Non-destructive revision demonstrated.** `tax-ver-historical-labels` proves a two-version bump including rename, split, merge, and deprecation leaves every prior row unchanged. `tax-ver-freeze` proves the trigger, live.
5. **Many-to-many preserved.** `tax-xw-3m-cardinality`, `tax-xw-3m-no-unique`, `tax-xw-3m-no-primary`, `tax-xw-pma-cardinality`, `tax-xw-reconcile-retains` green.
6. **Publication artifacts exist.** Data dictionary export served and reviewed, package released, parity check green, all UNVERIFIED caveats present. OD-8 filed or explicitly waived by the program with the waiver recorded here.
7. **Governance enforced at both layers.** `tax-gov-*` green: approval authority, evidence, and claim gating tested at the API boundary and at the database independently.
8. **Every open decision in §11 is either resolved and this document updated, or explicitly accepted as a demonstration-scope risk with a named owner.** OD-1 in particular is a gate on tier-2/3 demonstration credibility and cannot be closed by silence.
