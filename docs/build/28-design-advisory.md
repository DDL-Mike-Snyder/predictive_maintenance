# Build Framework 28 — System Test & Design Advisory (`design-advisory`)

| | |
|---|---|
| **Slug** | `design-advisory` (document 03 §3.1, verbatim) |
| **Directory** | `services/design-advisory/` |
| **Python package** | `fathom_design_advisory` |
| **Base path** | `/api/v1/design-advisory/` |
| **Database** | `fathom-design-advisory-pg`, schema `design_advisory`. Exactly one logical database (03 §15 obligation 13) |
| **Edge profile** | **None.** Enterprise only, per `docs/build/11-outbox-sync-library.md` §1.2. Outbox, inbox, and clock discipline are still mandatory (03 §15 obligation 11) |
| **Substitution posture** | Core program capability. Not a substitution candidate (04 §10). Test-data ingest may federate to program engineering data systems as an adapter concern |
| **Governing architecture** | 04 §10 in full; 03 §6 `design-advisory` catalog rows; 03 §7.2 and **§7.2.1**; 05 D21 |

---

## 0. How to read this document, and what it depends on that does not yet exist

This document instantiates `docs/build/09-monorepo-and-conventions.md` for one sub-application. **Everything in 09 applies and is not restated**: the four-layer scaffold (09 §4.1), the Dockerfile and chart skeletons (09 §4.3–4.4), the shared middleware for idempotency, ETag, correlation, and problem details (09 §5), the shared Definition of Done (09 §8), and the shared DO-NOT list (09 §9). Where this document adds a rule it is additive; **nothing in 09 is removed or relaxed.**

### 0.1 Document 03 was corrected on the day this was written — three changes bind here

| Change in 03 | Consequence for this sub-application |
|---|---|
| **`producer_node` added to the envelope** (§5.4) | Enterprise-only, so `producer_node` is the constant `"enterprise"` on every published event. Asserted by a test (§13, T-ENV-1) rather than assumed, because a constant nobody checks is a constant that drifts |
| **`authority_class` vocabulary added at §7.2.1** | `redesign_case` is **this sub-application's proposal kind**, and §7.2.1 fixes its minimum authority as `design_authority` at every blast radius, with dual control at fleet scope. The value is set **by this sub-application at creation** from the §7.2.1 table and re-validated at adjudication. See §6.4, and the §16 correction on the class-scope dual-control tension |
| **`eic` added to `SystemRef` and `InstalledItemRef`** (§3.3), federation and human reference only, never a join key | Load-bearing here more than anywhere else. Real engineering drawings, qualification reports, and test files are filed **by EIC and drawing number, not by NIIN**, and EIC is *"a class code of variable specificity."* The test-data ingest adapter must resolve EIC → NIIN and **record the ambiguity when the resolution is one-to-many**. See §3.2.4 |

### 0.2 Two build documents this one depends on do not exist yet

`docs/build/22-pdm.md` and `docs/build/25-failure-intelligence.md` are being authored in parallel and are **absent from the repository at the time of writing**. This document therefore:

- **Does not invent Failure Intelligence's evidence-strength scale.** The passthrough rule in §8 is specified so that it is enforceable *without knowing the scale* — by verbatim carry plus digest equality over the structured object as received. When document 25 fixes the scale, nothing here changes. This is deliberate: a rule that depends on the scale's shape would have to be rewritten, and a rewritten invariant is an invariant that gets weakened.
- **States the reciprocal obligation it requires of PdM** (§7.4) as a numbered binding to be reflected in document 22, rather than assuming it. Document 04 §4's Phase 3 question — *"How `design_change.projected` scenarios are represented without contaminating operational predictions"* — is answered **from the producer side** here. The consumer side belongs to 22.

### 0.3 Where document 07 is silent, and what this document does about it

**Document 07 does not cover Navy test, qualification, or developmental-engineering data systems at all.** Its §2 system landscape covers CDMD-OA, SCLSIS, 3-M/MDS, RSUPPLY, ICAS, CASREP, and Navy ERP; its §10 gap register lists nothing about test or qualification data because the subject was never in scope. The nearest adjacent content is §5.6 (TMA/TMI ranking) and §5.5 (the reliability formulas), both of which are used here — see §3.5.2.

**Consequence, stated rather than papered over:** the `test_kind`, `test_regime`, and test-condition vocabularies in §3.2 are **program-defined placeholders**, namespaced so they cannot be mistaken for a Navy or standards code, and carrying a `code_authority` column exactly as `docs/build/12-reference-data-taxonomy.md` §2.3 does for the same reason. **No Navy-specific test-data schema is asserted anywhere in this document.** This is 09 DO-NOT-32 applied to the one sub-application where the temptation is strongest, because the domain — qualification testing — sounds specifiable from general knowledge and is not.

Three specific things that would be needed for a real ingest adapter and are **not available**: the record layout of NAVSEA qualification and first-article test reports; the identifier scheme by which those reports are filed and retrieved; and the authoritative source system, if one exists, for design dependency and interface data below the CDMD-OA configuration level. All three are logged in §15 as blocking questions, not resolved by invention.

---

## 1. Purpose and scope

**Purpose (04 §10).** Assemble the engineering case for component redesign from field failure evidence, causal findings, and test data, including dependency impact and cost, **for a design authority to act upon.**

### 1.1 The framing that governs every other decision in this document

> **The output is a decision package for a human authority, not a decision.** Redesign is an acquisition action with programmatic, contractual, and airworthiness or seaworthiness implications far exceeding this system's scope. The sub-application assembles evidence and estimates to a standard that a design engineer can evaluate and defend, **and stops there.** — document 04 §10

This sub-application is the **terminal consumer in the causal pipeline** and the one whose output has the most acquisition and programmatic consequence if wrong. A wrong prediction wastes a maintenance window. A wrong redesign business case commits engineering funding, contract scope, and configuration authority against evidence that will be re-examined by people whose job is to find its defects. The framing above is therefore not a disclaimer; it is a **structural constraint on the API surface.**

### 1.2 The boundary, enforced in the API rather than asserted in prose

Four structural enforcements. Each is a schema or route property that makes the prohibited thing unrepresentable, not a rule someone must remember.

| # | Enforcement | Mechanism |
|---|---|---|
| **E1** | **No `RedesignCase` state means "approved."** | `case_status` is the enum `draft \| assembled \| published \| superseded \| withdrawn`. There is no `approved`, no `authorized`, no `directed`. `published` means *released to a design authority as a decision package*, which is asserted in the column comment and in the OpenAPI description. A `PATCH` carrying any unknown status value fails Pydantic validation before it reaches a service (§3.6) |
| **E2** | **No operation records a redesign decision, and none can be added silently.** | **[AMENDMENT — narrowed.]** `POST /redesign-cases` now exists (added above, closing `42-redesign-case-builder.md` §18 item 1) — but it creates an empty `draft` row, recording no decision, no scope, and no recommendation; every value a design authority would need to disagree with is still absent until `/assemble` and `/estimate` run and a proposal is adjudicated. A case reaches `published` **only** as the effect of a human adjudicating a `redesign_case` proposal (§6.5). The service exposes no route that accepts an adjudication outcome for a *redesign*, as distinct from for a *proposal*. A contract test enumerates every route and asserts none matches a decision-verb pattern (§13, T-NODECISION-1), **and a second test asserts `POST /redesign-cases`'s response carries no field beyond `id`, `candidate_id`, `dossier_id`, `case_status`, and timestamps** — the creation route is checked for silence, not merely absence of a decision verb |
| **E3** | **`recommendation` is structurally non-directive.** | `RedesignRecommendation.stance` is a closed vocabulary containing no approval value: `redesign_warranted_for_evaluation`, `insufficient_evidence`, `monitor_and_reassess`, `no_action_indicated`. `limitations[]` and `evidence_gaps[]` are **required and non-empty** — a recommendation that claims no limitations cannot be persisted (§3.6). This is what makes "to a standard a design engineer can evaluate and defend" checkable: the case states what it does not know |
| **E4** | **The only authority-bearing write is a proposal.** | `POST /proposals` (`kind=redesign_case`) is the sole `proposal-only` operation, and its `authority_class` is set by this service from 03 §7.2.1 to `design_authority` unconditionally. Every other write is internal bookkeeping on this service's own aggregates |

**Owns** (04 §10): test and qualification data, component failure-mode dossiers, the design dependency graph, redesign candidates and cases, cost estimates, and proposals targeting this sub-application.

**Does not own:** causal findings (Failure Intelligence), maintenance history (Scheduling), predictions (PdM), the failure-mode vocabulary (Reference Data, 03 §14), **or design authority itself.**

### 1.3 Position in the causal pipeline, and the framing inherited from D21

Design Advisory sits at the end of: telemetry → anomaly candidate → **human tag** → causal hypothesis → **human adjudication** → causal finding → redesign dossier → redesign case → **human adjudication** → design authority.

Two human gates precede this sub-application and one follows it. It must not weaken any of them.

**Finding D21 (05 §2, HIGH) — the confounded causal loop** — applies transitively. Failure Intelligence's comparative population analysis compares hulls whose intervention histories were assigned by the model under test. 05 §4.1's recommendation is a policy-frozen holdout plus statistical correction, and `maintenance_action.recorded` now carries `triggering_driver`, `triggering_prediction_id`, and `policy_version` so that treatment assignment is conditionable. **Design Advisory's obligation is narrower and absolute:** it consumes Failure Intelligence's output as *adjudicated hypotheses with declared strength and declared unaddressed confounders*, and it may not present them as anything else. The `treatment_assignment_handling` field of `causal_finding.published` is carried into every dossier citation (§3.3) precisely so that a design authority reading a business case can see whether the causal claim behind it was corrected for confounding by indication.

**And the loop must not be closed here.** Design Advisory consumes `prediction.updated` and `prediction.invalidated`. It uses them for population and consequence context only. It **never** uses a prediction as evidence for a causal claim in a dossier — the same restriction 04 §9 places on Failure Intelligence's own use of `prediction.updated`, for the same reason. See DO-NOT-DA-6.

---

## 2. Technology decisions specific to this sub-application

Everything not listed here is 09 §2 unchanged.

| Concern | Decision | Justification |
|---|---|---|
| **Dependency graph storage** | **PostgreSQL edge table + recursive CTE.** No graph database | 04 §10 states it directly: *"Graph traversal is served from PostgreSQL recursive queries unless Phase 3 establishes depth requirements exceeding what that supports."* Reinforced by 03 §15 obligation 13 and 09 DO-NOT-3 (one logical database): a graph engine would be a second storage engine requiring separate justification, and the traversal here is depth-bounded at 6 over an edge set whose realistic cardinality at demonstration scale is ~2,500 NIINs (06 §7). §4 specifies the exact query. **The revisit trigger is stated, not left implicit:** if Phase 3 establishes required depth > 6, or a traversal p95 exceeding the 06 §7 latency budget of 1.5 s, that is the condition under which this decision is reopened — by ADR, with measurements |
| **Traversal packaging** | A SQL set-returning function `design_advisory.impact(...)` — **not** an ORM traversal in Python | One implementation, one behaviour, serving the API, the case builder, and the completeness computation identically. This follows the precedent set by `reference_data.resolve_forward` in doc 12 §9.1, and for the same reason: a second implementation of a graph walk is a second set of results |
| **Detailed cost roll-up** | Executed **in-service in SQL**, not in Domino | It is an aggregation over this service's own edge table and its own cost-factor tables. Nothing about it is a learned model. Sending it to Domino would require exporting the graph, which 09 DO-NOT-1 forbids |
| **Parametric cost model** | Deterministic in-service formula by default; **optionally** a Domino Endpoint, **proxied** per 03 §8.3, config-gated, with the deterministic path as fallback | Any learned component belongs in Domino (04 §10 plane placement). But a business case that cannot be produced when an Endpoint is unavailable is a capability with a single point of failure, and Endpoints have no serving-path SLO (01 §3 correction 2). Fallback is mandatory and the estimate records which path produced it in `CostEstimate.model_ref` |
| **Test artifact storage** | S3/MinIO for the artifacts; PostgreSQL for the record metadata and the **absence** rows | 04 §10. The absence rows are the point — see §3.2 |
| **Practitioner UI** | Domino App under `apps/practitioner` | 04 §10: the audience holds Domino accounts and *"the workflow benefits from proximity to the causal analysis."* Reads base path at runtime from `DOMINO_RUN_HOST_PATH` (09 §2.6 constraint 2) |
| **No synchronous peer calls** | NetworkPolicy egress: own Postgres, Redpanda, `auth`, `audit`, `reference-data`. **No peer to `failure-intel` or `pdm`** | 03 principle 2. Causal citations are captured from the event at dossier-assembly time and stored verbatim (§3.3); drill-down from a citation to Failure Intelligence's evidence is **composed by the gateway** (04 §11), not proxied here. This is what lets §8's passthrough rule be enforced by a digest rather than by trusting a live re-fetch |

---

## 3. Data model

Schema `design_advisory`. Enum types declared once, at the top, following doc 12's convention.

```sql
-- ---------------------------------------------------------------------------
-- Vocabularies.  Every one of these is program-defined unless annotated
-- otherwise.  None is a Navy or standards code set: document 07 covers no
-- test/qualification data system (§0.3), and 09 DO-NOT-32 forbids inventing
-- one here or in a shared package.
-- ---------------------------------------------------------------------------

CREATE TYPE design_advisory.code_authority AS ENUM (
    'program-defined',        -- authored by this program; the honest default here
    'standards-verified',     -- transcribed from an acquired primary source
    'federated'               -- received from an external engineering data system
);

CREATE TYPE design_advisory.test_record_status AS ENUM (
    -- PRESENT
    'present',                -- artifact held, values parsed, outcome meaningful
    'present_unparsed',       -- artifact held; values NOT machine-readable
    -- ABSENT.  Each of these is a ROW, not a missing row.  See §3.2.1.
    'absent_not_performed',   -- affirmatively established: the test was not done
    'absent_not_located',     -- probably performed; record cannot be located
    'absent_not_required',    -- the qualification regime did not require it
    'absent_unknown'          -- coverage expected, nothing established either way
);

CREATE TYPE design_advisory.test_outcome AS ENUM ('pass', 'fail', 'partial', 'inconclusive');

CREATE TYPE design_advisory.node_kind AS ENUM ('part', 'artifact');

CREATE TYPE design_advisory.dependency_relation AS ENUM (
    'interfaces_with',        -- 04 §10 "its interfaces"
    'fits_into',              -- 04 §10 "its fit"
    'supports',               -- 04 §10 "its supported and supporting items"
    'documented_by',          -- 04 §10 "its technical documentation"   [artifact]
    'allowance_listed_in',    -- 04 §10 "its allowance lists"           [artifact]
    'training_covered_by'     -- 04 §10 "and training"                  [artifact]
);

CREATE TYPE design_advisory.dependency_source_kind AS ENUM (
    'cdmd_oa_federation',     -- 07 §2: the authoritative configuration source
    'engineering_drawing',
    'apl_derived',            -- 07 §4.1: APL/AEL structure
    'sme_asserted',
    'inferred_cooccurrence',  -- derived from co-replacement patterns
    'unverified_import'
);

CREATE TYPE design_advisory.candidate_status AS ENUM (
    'identified', 'qualifying', 'gate_passed', 'gate_failed', 'case_drafted', 'withdrawn'
);

CREATE TYPE design_advisory.case_status AS ENUM (
    -- Deliberately contains no 'approved'.  See §1.2 E1.  A case is a decision
    -- PACKAGE; 'published' means released to a design authority, never approved.
    'draft', 'assembled', 'published', 'superseded', 'withdrawn'
);

CREATE TYPE design_advisory.recommendation_stance AS ENUM (
    -- Closed and non-directive.  See §1.2 E3.
    'redesign_warranted_for_evaluation',
    'insufficient_evidence',
    'monitor_and_reassess',
    'no_action_indicated'
);

CREATE TYPE design_advisory.cost_method AS ENUM ('parametric', 'dependency_rollup');

CREATE TYPE design_advisory.citation_posture AS ENUM ('supporting', 'contra');
```

### 3.1 The aggregate map

| Aggregate (04 §10) | Root table | Scope | `changed_since` read | Projected by |
|---|---|---|---|---|
| `TestRecord` | `test_record` | `niin` | Yes | — (internal; served on request) |
| `FailureDossier` | `failure_dossier` | `niin` | Yes | `knowledge-retrieval` (drill-down) |
| `DesignDependency` | `dependency_edge` | `niin` | Yes | — |
| `RedesignCandidate` | `redesign_candidate` | `niin` | Yes | `fleet-status`, `notification` |
| `RedesignCase` | `redesign_case` | `niin` | Yes | `fleet-status`, `audit` |
| `CostEstimate` | `cost_estimate` | child of candidate/case | via parent | — |
| `DesignScenario` | `design_scenario` | `niin` | Yes | `pdm` (§7) |
| `Proposal` | `proposal` | per 03 §7.2 | Yes | `gateway`, `audit` |

`DesignScenario` is not in 04 §10's aggregate table but is required to publish `design_change.projected` as a first-class, separately-topiced, separately-stored thing rather than as a side effect of a case. §16 records this as an addition to 04 §10.

#### 3.1.1 `part_ref` — the read-model table every aggregate keys on

Every table below carries `niin REFERENCES design_advisory.part_ref(niin)`. That table is a **read model**, not an owned aggregate:

```sql
-- Projection of PartRef (03 §3.3), built from Registry and Reference Data
-- `changed_since` reads -- never from the event bus  [D5].  It exists as a real
-- table with a real primary key so that every FK in this schema is enforced by
-- the database rather than by hope: a dossier, a dependency edge, or a test
-- record naming a NIIN the system does not know is a defect, and the cheapest
-- place to catch it is the insert.
CREATE TABLE design_advisory.part_ref (
    niin             text PRIMARY KEY,      -- the join key (03 §3.3)
    nsn              text,                  -- human reference / federation only
    apl              text,                  -- 07 §4.1 format
    equipment_family text NOT NULL,         -- required on every part  [D35]
    synced_at        timestamptz NOT NULL DEFAULT now(),
    classification   jsonb NOT NULL
);
```

`equipment_family` is `NOT NULL` because 03 §3.3 makes it *"a required attribute of every part"* `[D35]`, and the test coverage profile scopes on it (§3.2.1). It is owned and versioned by Reference Data; this is a copy of served content, never an independent definition (doc 12 DO-NOT-1).

### 3.2 `TestRecord` — absence is a row, never a missing row

This is the schema realisation of 04 §10's key decision:

> **Test data is treated as sparse and heterogeneous.** Qualification data for legacy components is frequently incomplete, inconsistently formatted, and decades old. The design assumes partial coverage and **represents absence explicitly rather than treating missing test data as absence of concern.**

The defect this prevents is specific and is the most likely single error in a redesign business case: a component with no qualification data on file reads, to any query that looks for failures, exactly like a component that was qualified and passed. `SELECT ... WHERE outcome = 'fail'` returns nothing in both cases. A cost model or a priority score fed by that query silently treats an unknown as a clean bill of health.

#### 3.2.1 Three tables, and why absence needs all three

```sql
-- (a) The vocabulary of test kinds.  PROGRAM-DEFINED PLACEHOLDER (§0.3).
CREATE TABLE design_advisory.test_kind (
    test_kind_code   text PRIMARY KEY,
    code_authority   design_advisory.code_authority NOT NULL,
    label            text NOT NULL,
    description      text NOT NULL,
    is_qualification boolean NOT NULL,   -- qualification vs developmental
    created_at       timestamptz NOT NULL DEFAULT now(),

    -- The fabrication guard, copied deliberately from doc 12 §2.3's
    -- `extension_codes_are_namespaced`.  A program-defined code is namespaced so
    -- that it cannot be mistaken for, or collide with, a code from a standard
    -- this program has not read.  Document 07 supplies NO test-data code set.
    CONSTRAINT program_codes_are_namespaced CHECK (
        (code_authority = 'program-defined'  AND test_kind_code ~ '^FATHOM-TK-[0-9]{3}$')
     OR (code_authority <> 'program-defined' AND test_kind_code !~ '^FATHOM-TK-')
    )
);

-- (b) The coverage profile: what SHOULD have a record.  This is the table that
--     makes "no row at all" detectable.  Without it, absence is only ever the
--     absence of a row, which no query can distinguish from absence of concern.
CREATE TABLE design_advisory.test_coverage_profile (
    profile_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_kind       text NOT NULL CHECK (scope_kind IN ('niin', 'equipment_family')),
    niin             text REFERENCES design_advisory.part_ref(niin),
    equipment_family text,               -- 03 §3.3 [D35]; owned by reference-data
    test_kind_code   text NOT NULL REFERENCES design_advisory.test_kind(test_kind_code),
    expectation      text NOT NULL CHECK (expectation IN ('expected', 'optional')),
    basis            text NOT NULL,      -- WHY this is expected.  Non-null on purpose
    profile_version  text NOT NULL,
    classification   jsonb NOT NULL,

    CONSTRAINT exactly_one_scope CHECK (
        (scope_kind = 'niin'             AND niin IS NOT NULL AND equipment_family IS NULL)
     OR (scope_kind = 'equipment_family' AND equipment_family IS NOT NULL AND niin IS NULL)
    ),
    CONSTRAINT profile_unique UNIQUE (scope_kind, niin, equipment_family, test_kind_code, profile_version)
);

-- (c) The records themselves — present AND absent.
CREATE TABLE design_advisory.test_record (
    test_record_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    niin               text NOT NULL REFERENCES design_advisory.part_ref(niin),
    test_kind_code     text NOT NULL REFERENCES design_advisory.test_kind(test_kind_code),

    record_status      design_advisory.test_record_status NOT NULL,
    outcome            design_advisory.test_outcome,        -- NULL unless status='present'
    absence_basis      text,                                -- NOT NULL for absence statuses
    absence_established_by text,
    absence_established_at timestamptz,

    -- Conditions and results.  Deliberately jsonb and deliberately unvalidated
    -- against a Navy schema: document 07 supplies none (§0.3).  A `conditions_
    -- schema_ref` names whatever the ingest adapter parsed it against, so the
    -- shape is auditable even though it is not program-standardised.
    conditions         jsonb,
    results            jsonb,
    conditions_schema_ref text,

    test_performed_at  timestamptz,       -- when the test ran, where known
    report_ref         text,              -- object-store key of the artifact
    report_identifier  text,              -- the external report/drawing number
    -- Federation identity.  03 §3.3 as corrected: EIC is carried for federation
    -- and human reference ONLY and is NEVER a join key.  See §3.2.4.
    eic                text,
    eic_resolution     jsonb,             -- how NIIN was derived from EIC, and whether ambiguous

    source_system      text,
    code_authority     design_advisory.code_authority NOT NULL,
    ingested_at        timestamptz NOT NULL DEFAULT now(),
    superseded_by      uuid REFERENCES design_advisory.test_record(test_record_id),
    classification     jsonb NOT NULL,

    -- --- the three constraints that make absence honest --------------------
    CONSTRAINT outcome_only_when_present CHECK (
        (record_status = 'present'  AND outcome IS NOT NULL)
     OR (record_status <> 'present' AND outcome IS NULL)
    ),
    CONSTRAINT absence_carries_a_basis CHECK (
        (record_status::text LIKE 'absent%' AND absence_basis IS NOT NULL)
     OR (record_status::text NOT LIKE 'absent%')
    ),
    CONSTRAINT absence_holds_no_artifact CHECK (
        (record_status::text NOT LIKE 'absent%') OR (report_ref IS NULL AND results IS NULL)
    )
);

CREATE INDEX tr_niin_kind ON design_advisory.test_record (niin, test_kind_code)
    WHERE superseded_by IS NULL;
CREATE INDEX tr_status    ON design_advisory.test_record (record_status)
    WHERE superseded_by IS NULL;
```

`outcome_only_when_present` is the load-bearing constraint. It makes it **impossible to write an absence row that also carries an outcome**, which is the shape a well-meaning ingest adapter produces when it decides that "no failures found" is a reasonable default for a missing report.

#### 3.2.2 The qualification-credit rule, and the only sanctioned read

Nothing in costing, priority scoring, or case assembly may read `outcome` without also reading `record_status`. That is a rule a reviewer cannot enforce across a codebase, so it is made structural:

```sql
-- Generated, not computed at read time, so no query can accidentally omit the
-- status half of the predicate.
ALTER TABLE design_advisory.test_record
    ADD COLUMN qualification_credit boolean
    GENERATED ALWAYS AS (record_status = 'present' AND outcome = 'pass') STORED;

-- The ONLY sanctioned read for scoring, costing, and dossier assembly.
-- Direct SELECT from test_record inside services/ is a lint failure (§13).
CREATE VIEW design_advisory.test_coverage_v AS
SELECT p.scope_kind,
       coalesce(p.niin, tr.niin)              AS niin,
       p.test_kind_code,
       p.expectation,
       p.basis                                AS expectation_basis,
       coalesce(tr.record_status, 'absent_unknown'::design_advisory.test_record_status)
                                              AS record_status,
       tr.outcome,
       tr.absence_basis,
       coalesce(tr.qualification_credit, false) AS qualification_credit,
       (tr.test_record_id IS NULL)            AS materialised_absence,
       tr.test_record_id,
       tr.test_performed_at,
       tr.report_ref
  FROM design_advisory.test_coverage_profile p
  LEFT JOIN design_advisory.test_record tr
         ON tr.niin           = p.niin
        AND tr.test_kind_code = p.test_kind_code
        AND tr.superseded_by IS NULL;
```

Three properties follow, and they are what "represents absence explicitly" actually means in code:

1. **A `LEFT JOIN` from the profile, never from the records.** Every expected test kind produces a row. A NIIN with zero `test_record` rows does not produce an empty result; it produces one `absent_unknown` row per profile entry, with `materialised_absence = true`.
2. **`qualification_credit` is `false` for every absence status, including `absent_not_required`.** *Not required* is a statement about the qualification regime, not evidence about the component. It suppresses a finding of concern; it never creates a finding of confidence.
3. **`coalesce(..., false)`** on the credit column, so a NULL from the outer join can never be read as truthy by an ORM that maps NULL to absent-and-therefore-fine.

#### 3.2.3 `absent_unknown` versus `absent_not_located`

These are not the same claim and the distinction survives into the case. `absent_not_located` asserts that someone looked; `absent_unknown` asserts that nobody has. A `RedesignCase` reports the counts separately (§3.6), because "we searched and the 1987 qualification file is gone" and "we have not searched" carry different weight to a reviewer, and collapsing them into a single "missing" count is the kind of loss that makes a business case indefensible on its first challenge.

#### 3.2.4 EIC resolution — the doc 03 §3.3 correction applied

Engineering and test artefacts in this domain are filed by EIC and by drawing number. The NIIN, which is this system's join key for a part type, is frequently *not* on the report. So:

- `test_record.niin` is **always** the join key and is **NOT NULL**.
- `test_record.eic` is carried for federation and human reference only. **No query joins on it.** (09 DO-NOT-5; 03 §3.3.)
- `eic_resolution` records the derivation as data:

```json
{
  "eic": "AB12CD3",
  "eic_specificity_chars": 7,
  "resolution_method": "reference_data_crosswalk | sme_assignment | apl_lookup",
  "candidate_niins": ["012345678", "012345679"],
  "resolved_niin": "012345678",
  "ambiguous": true,
  "ambiguity_basis": "EIC recorded at 4-character equipment-category specificity; 2 NIINs in family",
  "resolved_by": "…", "resolved_at": "…"
}
```

`ambiguous: true` **propagates into the dossier and into `dependency_completeness`'s sibling field `test_attribution_ambiguity`** (§3.6). NAVSEAINST 4790.8 Appendix A, quoted in 03 §3.3, makes EIC *"a class code of variable specificity"* — *"Where the EIC is known to more than four digits, it should be recorded at that level."* A four-character EIC identifies an equipment category, not a part. Silently attaching a 1990 test report for an equipment category to one NIIN in that category, and then costing a redesign on it, is a fabrication with a paper trail. Recording the ambiguity costs one jsonb column.

### 3.3 `FailureDossier` — consolidated evidence per NIIN

An immutable, versioned snapshot. Assembly is cheap and re-runnable; a *published* dossier is never mutated, because a business case cites a dossier and a mutable citation is not a citation.

```sql
CREATE TABLE design_advisory.failure_dossier (
    dossier_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    niin              text NOT NULL REFERENCES design_advisory.part_ref(niin),
    dossier_version   int  NOT NULL,
    assembled_at      timestamptz NOT NULL DEFAULT now(),
    assembled_by      text NOT NULL,          -- principal or agent workload identity

    -- Provenance sufficient to trace any operator-visible figure to its sources
    -- (03 §15 obligation 9).  `inputs_digest` is over the canonical JSON of every
    -- input reference and version, so an identical re-assembly is detectable and
    -- a changed one is explainable.
    inputs_digest     char(64) NOT NULL,
    taxonomy_version  text NOT NULL,          -- doc 12: every label carries its version
    read_model_watermarks jsonb NOT NULL,     -- per-consumed-topic lag at assembly time

    affected_population jsonb NOT NULL,       -- installed-item counts by class/hull; 06 §7 scale
    classification    jsonb NOT NULL,         -- union of inputs (03 §7.3, inherited_from)

    CONSTRAINT dossier_version_unique UNIQUE (niin, dossier_version)
);
```

`read_model_watermarks` is unusual and deliberate. A dossier assembled while the `causal_finding` read model was four hours stale is a different artefact from one assembled current, and a design authority reviewing a case six weeks later has no other way to know. This is the provenance obligation (03 §15 obligation 9) taken literally.

#### 3.3.1 `dossier_causal_citation` — the passthrough carrier

**This table is the mechanism for §8.** Its design constraint is that it must be *impossible* to record a strength assessment of this sub-application's own.

```sql
CREATE TABLE design_advisory.dossier_causal_citation (
    citation_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    dossier_id        uuid NOT NULL REFERENCES design_advisory.failure_dossier(dossier_id),
    posture           design_advisory.citation_posture NOT NULL,

    -- --- identity of the cited finding, as Failure Intelligence issued it ----
    hypothesis_id     uuid NOT NULL,
    hypothesis_version int  NOT NULL,
    adjudication_id   uuid NOT NULL,
    adjudication_state text NOT NULL,        -- as received; NOT re-derived here
    adjudicated_by    text NOT NULL,
    adjudicated_at    timestamptz NOT NULL,
    source_event_id   uuid NOT NULL,         -- the causal_finding.published event_id

    -- --- THE VERBATIM CARRY.  §8. -----------------------------------------
    -- The structured evidence-strength object exactly as served by failure-intel.
    -- Opaque here BY DESIGN: this service does not parse it, rank it, threshold
    -- it, summarise it into a column, or combine it with another citation's.
    evidence_strength         jsonb    NOT NULL,
    evidence_strength_schema_version text NOT NULL,
    evidence_strength_digest  char(64) NOT NULL,   -- SHA-256 over canonical JSON
    confounders_unaddressed   jsonb    NOT NULL,   -- as received.  Empty array is a CLAIM
    treatment_assignment_handling jsonb NOT NULL,  -- 03 §6; D21

    -- --- taxonomy binding, per doc 12 --------------------------------------
    failure_mode_lineage_id uuid NOT NULL,   -- doc 12 §2.3: lineage_id, NOT code, resolves
    failure_mode_code       text NOT NULL,   -- human reference; resolvable via lineage
    taxonomy_version        text NOT NULL,
    attribution_confidence  numeric(3,2),
    attribution_agreement   text CHECK (attribution_agreement IN ('both','pma_only','maintenance_only')),

    classification    jsonb NOT NULL,

    CONSTRAINT citation_unique UNIQUE (dossier_id, hypothesis_id, hypothesis_version)

    -- ABSENT BY DESIGN, and their absence is asserted by a schema test (T-PASS-4):
    --   * no local_strength / strength_rank / strength_score column
    --   * no strength_summary or strength_prose column
    --   * no combined_strength / consolidated_strength column
    --   * no is_strong / meets_threshold boolean
    -- Each of those is a place a strength judgment could be authored HERE, which
    -- is exactly what document 04 §9's framing forbids.  See §8.2.
);

CREATE INDEX dcc_dossier   ON design_advisory.dossier_causal_citation (dossier_id, posture);
CREATE INDEX dcc_hypothesis ON design_advisory.dossier_causal_citation (hypothesis_id, hypothesis_version);
```

**`posture` separates supporting from contra citations.** 04 §9: *"Rejections and negative findings are retained. A hypothesis examined and found unsupported is valuable knowledge and prevents rediscovery."* A dossier may and should cite a rejected hypothesis — but only as `contra`, and a `contra` citation never counts toward the evidentiary floor in the costing gate (§5.3). Without the split, "we examined this and it wasn't supported" and "this supports redesign" occupy the same list.

#### 3.3.2 The remaining dossier children

```sql
CREATE TABLE design_advisory.dossier_field_failure (
    dossier_id        uuid NOT NULL REFERENCES design_advisory.failure_dossier(dossier_id),
    installed_item_id uuid NOT NULL,        -- the PHYSICAL item (03 §3.3, C10)
    asset_id          uuid NOT NULL,
    position_id       uuid NOT NULL,
    occurred_at       timestamptz NOT NULL,
    recorded_at       timestamptz NOT NULL, -- audit uses recorded_at (03 §5.4)
    source_kind       text NOT NULL CHECK (source_kind IN
                          ('maintenance_action','installed_item_removal','casrep_severity')),
    source_ref        text NOT NULL,
    failure_indicator boolean NOT NULL,     -- corrective vs preventive; 04 §4's determinative input
    m3_status_code    char(1),              -- 07 §5.4: Status 2/3 is the Navy's own severity filter
    findings_code     text,
    triggering_driver text,                 -- D1/D21: treatment assignment
    triggering_prediction_id uuid,
    policy_version    text,
    baseline_id       uuid NOT NULL,
    baseline_epoch    bigint NOT NULL,
    PRIMARY KEY (dossier_id, installed_item_id, occurred_at, source_kind)
);

CREATE TABLE design_advisory.dossier_test_coverage (
    dossier_id       uuid NOT NULL REFERENCES design_advisory.failure_dossier(dossier_id),
    test_kind_code   text NOT NULL,
    record_status    design_advisory.test_record_status NOT NULL,
    outcome          design_advisory.test_outcome,
    qualification_credit boolean NOT NULL,
    materialised_absence boolean NOT NULL,
    absence_basis    text,
    test_record_id   uuid,
    PRIMARY KEY (dossier_id, test_kind_code),
    -- The same guard as the source table, restated at the snapshot boundary so a
    -- defective assembler cannot write a credited absence into a dossier.
    CONSTRAINT snapshot_credit_requires_present CHECK (
        qualification_credit = false OR (record_status = 'present' AND outcome = 'pass')
    )
);
```

`dossier_test_coverage` is populated from `test_coverage_v`, so **a dossier always carries one row per expected test kind**, present or absent. There is no code path by which a dossier's test section is silently empty.

### 3.4 `DesignDependency` — the graph edge type

Two node kinds, and the distinction is what keeps the traversal bounded and semantically correct.

- **`part` nodes** are NIINs. They are traversable: a redesign propagates through them.
- **`artifact` nodes** are the non-part impact targets 04 §10 enumerates — technical documentation, allowance lists, training. They are **leaves**: a redesign impacts them, but nothing propagates *through* a technical manual to a further component. Modelling them as terminal is not a simplification; treating an IETM as a traversable node would let the blast radius leak into every component that manual happens to also cover.

```sql
CREATE TABLE design_advisory.dependency_artifact (
    artifact_id     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_kind   text NOT NULL CHECK (artifact_kind IN
                        ('technical_publication','allowance_list','training_product')),
    external_ref    text NOT NULL,       -- IETM/TM number, APL/AEL number (07 §4.1), course id
    label           text NOT NULL,
    classification  jsonb NOT NULL,
    CONSTRAINT artifact_unique UNIQUE (artifact_kind, external_ref)
);

CREATE TABLE design_advisory.dependency_edge (
    edge_id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    relation        design_advisory.dependency_relation NOT NULL,

    -- Canonical direction, stored ONCE.  Both orientations are generated in the
    -- traversal (§4.2), never duplicated as rows: duplicated inverse rows are the
    -- classic way an edge count — and therefore a completeness ratio — doubles.
    src_kind        design_advisory.node_kind NOT NULL,
    src_niin        text REFERENCES design_advisory.part_ref(niin),
    src_artifact_id uuid REFERENCES design_advisory.dependency_artifact(artifact_id),
    dst_kind        design_advisory.node_kind NOT NULL,
    dst_niin        text REFERENCES design_advisory.part_ref(niin),
    dst_artifact_id uuid REFERENCES design_advisory.dependency_artifact(artifact_id),

    -- --- provenance, which is what completeness is computed from -----------
    source_kind     design_advisory.dependency_source_kind NOT NULL,
    source_ref      text NOT NULL,
    verified_by     text,
    verified_at     timestamptz,
    confidence      numeric(3,2) CHECK (confidence > 0 AND confidence <= 1),
    notes           text,

    valid_from      timestamptz NOT NULL DEFAULT now(),
    valid_to        timestamptz,
    retracted_at    timestamptz,
    retraction_reason text,
    classification  jsonb NOT NULL,

    CONSTRAINT src_endpoint_exact CHECK (
        (src_kind = 'part'     AND src_niin IS NOT NULL AND src_artifact_id IS NULL)
     OR (src_kind = 'artifact' AND src_artifact_id IS NOT NULL AND src_niin IS NULL)
    ),
    CONSTRAINT dst_endpoint_exact CHECK (
        (dst_kind = 'part'     AND dst_niin IS NOT NULL AND dst_artifact_id IS NULL)
     OR (dst_kind = 'artifact' AND dst_artifact_id IS NOT NULL AND dst_niin IS NULL)
    ),
    -- An artifact is a LEAF.  It is never the source of an edge, so nothing can
    -- be reached THROUGH it.  This is what bounds the traversal semantically
    -- rather than only by the depth cap.
    CONSTRAINT artifacts_are_leaves CHECK (src_kind = 'part'),
    CONSTRAINT no_self_edge CHECK (src_niin IS DISTINCT FROM dst_niin OR src_niin IS NULL),
    CONSTRAINT retraction_paired CHECK ((retracted_at IS NULL) = (retraction_reason IS NULL)),
    CONSTRAINT verification_paired CHECK ((verified_by IS NULL) = (verified_at IS NULL))
);

CREATE INDEX de_src ON design_advisory.dependency_edge (src_niin, relation)
    WHERE retracted_at IS NULL;
CREATE INDEX de_dst ON design_advisory.dependency_edge (dst_niin, relation)
    WHERE retracted_at IS NULL AND dst_kind = 'part';
CREATE INDEX de_dst_artifact ON design_advisory.dependency_edge (dst_artifact_id)
    WHERE retracted_at IS NULL AND dst_kind = 'artifact';
```

#### 3.4.1 Traversal policy is data, not code

Whether a redesign of A propagates to B depends on the relation and its direction, and **nothing upstream specifies the answer**. So the policy is a seeded table, marked as a placeholder, rather than a `CASE` expression somebody has to find.

```sql
CREATE TABLE design_advisory.relation_traversal_policy (
    relation         design_advisory.dependency_relation PRIMARY KEY,
    traverse_forward boolean NOT NULL,   -- src -> dst
    traverse_reverse boolean NOT NULL,   -- dst -> src
    expands_forward  boolean NOT NULL,   -- may the traversal continue past dst?
    expands_reverse  boolean NOT NULL,
    forward_weight   numeric(3,2) NOT NULL CHECK (forward_weight > 0 AND forward_weight <= 1),
    reverse_weight   numeric(3,2) NOT NULL CHECK (reverse_weight > 0 AND reverse_weight <= 1),
    policy_version   text NOT NULL,
    rationale        text NOT NULL,
    is_placeholder   boolean NOT NULL DEFAULT true
);
```

**Seed — PLACEHOLDER pending Phase 3 SME validation (OD-3, §15).** The weights in particular are structural placeholders; they are not derived from any source document and must not be presented as engineering judgment.

| `relation` | fwd | rev | exp-fwd | exp-rev | w-fwd | w-rev | Rationale |
|---|---|---|---|---|---|---|---|
| `interfaces_with` | ✔ | ✔ | ✔ | ✔ | 1.00 | 1.00 | Symmetric. Changing either side of an interface impacts the other, and impact propagates onward through the mating item's own interfaces |
| `fits_into` | ✔ | ✔ | ✔ | ✗ | 1.00 | 0.80 | Redesigning the fitted item impacts its housing and onward. Redesigning the housing impacts the fitted item, but does not propagate past it |
| `supports` | ✔ | ✔ | ✔ | ✗ | 1.00 | 0.60 | *A supports B.* Redesigning A propagates to B and onward. Redesigning B may require A to change, but that does not propagate past A |
| `documented_by` | ✔ | ✗ | ✗ | ✗ | 1.00 | — | Leaf. A redesign requires a documentation change; a documentation change is not a redesign driver |
| `allowance_listed_in` | ✔ | ✗ | ✗ | ✗ | 1.00 | — | Leaf. COSAL/APL/AEL revision is a cost line (07 §4), not a propagation path |
| `training_covered_by` | ✔ | ✗ | ✗ | ✗ | 1.00 | — | Leaf |

#### 3.4.2 Which sources can count as verified

Also data, and also a guard: two source kinds can **never** count as verified, no matter who stamps them.

```sql
CREATE TABLE design_advisory.dependency_source_policy (
    source_kind         design_advisory.dependency_source_kind PRIMARY KEY,
    is_verifiable_source boolean NOT NULL,
    rationale           text NOT NULL
);
```

| `source_kind` | `is_verifiable_source` | Rationale |
|---|---|---|
| `cdmd_oa_federation` | true | 07 §2: *"the single authoritative source of information regarding ship's component configuration…"* |
| `engineering_drawing` | true | A primary engineering artefact |
| `apl_derived` | true | 07 §4.1/§4.2: documented APL/AEL structure |
| `sme_asserted` | true | A named engineer's assertion is verifiable evidence when attributed and dated |
| `inferred_cooccurrence` | **false** | A statistical co-replacement pattern is a hypothesis about a dependency, not a dependency. It may seed an edge for an SME to confirm; it may never be counted as known |
| `unverified_import` | **false** | By definition |

**An edge counts as verified iff `is_verifiable_source AND verified_by IS NOT NULL AND verified_at IS NOT NULL`.** Stamping `verified_by` on an `inferred_cooccurrence` edge does nothing, which is the anti-gaming property: completeness cannot be improved by asserting confidence, only by producing a source.

### 3.5 `RedesignCandidate`

```sql
CREATE TABLE design_advisory.redesign_candidate (
    candidate_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    niin              text NOT NULL REFERENCES design_advisory.part_ref(niin),
    status            design_advisory.candidate_status NOT NULL DEFAULT 'identified',
    dossier_id        uuid REFERENCES design_advisory.failure_dossier(dossier_id),

    -- Driver evidence: WHY this NIIN was flagged.  Non-empty enforced in the
    -- service layer and by the API schema; a candidate with no driver is noise.
    driver_kinds      text[] NOT NULL CHECK (cardinality(driver_kinds) > 0),
    driver_evidence   jsonb NOT NULL,

    priority_score    numeric(6,4),
    priority_method   text,             -- scoring model identity + version
    priority_components jsonb,          -- per-attribute contribution; §3.5.2
    pdm_criticality_tier smallint,      -- CONSUMED from PdM, never recomputed
    pdm_criticality_ref  text,

    affected_population jsonb NOT NULL,
    created_from      text NOT NULL CHECK (created_from IN
                          ('causal_finding','failure_rate_threshold','test_gap','manual','agent')),
    created_at        timestamptz NOT NULL DEFAULT now(),
    classification    jsonb NOT NULL
);
```

#### 3.5.1 Criticality is consumed, not recomputed

04 §10's Phase 3 question — *"Priority scoring for candidates, and how it reconciles with PdM criticality scoring"* — is resolved here in the only direction that does not create two competing criticality numbers: **PdM owns criticality; this service consumes `criticality_tier.assigned` into a read model and uses the tier as an input to priority, never as an output it re-derives.** `pdm_criticality_tier` is a stored copy with a reference, not a local computation. Reconciliation is therefore structural rather than procedural: there is only one criticality assessment in the system and this service reads it.

#### 3.5.2 Priority scoring — anchored on doc 07 §5.6, weights unresolved

Document 07 §5.6 documents the Navy's existing priority corrective-action process, and it is the right anchor:

> Six attributes over a two-year window: 2-Kilo volume, man-hours, parts cost, high-priority failures (Status 2/3 plus Priority 1–3 CASREPs), high-priority downtime, and CASREP volume. Attributes scaled so **three sigma equals 1.0**, combined by **Pythagorean vector addition**.

`priority_components` records each of the six scaled attribute values plus the PdM tier as a seventh input, and `priority_score` is their vector magnitude. **Using the Navy's own scaling and combination rule rather than inventing a weighted sum is deliberate** — 07 §5.6 notes this process is *"the closest existing analogue"* to the platform's own scoring, and a figure computed the Navy's way is a figure a Navy reviewer can check.

**What is NOT resolved:** whether the PdM tier enters as a seventh vector component, as a multiplier, or as a filter. Marked **OD-4 (§15), placeholder pending Phase 3 SME validation.** The interim implementation treats it as a seventh component and records `priority_method = 'tmi-vector-v0-placeholder'` so that every score carries the fact that its formulation is provisional.

### 3.6 `RedesignCase` — with `dependency_completeness` as a required, structured field

```sql
CREATE TABLE design_advisory.redesign_case (
    case_id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id      uuid NOT NULL REFERENCES design_advisory.redesign_candidate(candidate_id),
    niin              text NOT NULL REFERENCES design_advisory.part_ref(niin),
    dossier_id        uuid NOT NULL REFERENCES design_advisory.failure_dossier(dossier_id),
    case_version      int  NOT NULL,
    case_status       design_advisory.case_status NOT NULL DEFAULT 'draft',

    scope_description text NOT NULL,

    -- --- 04 §10's key decision, as a REQUIRED structured field -------------
    -- "dependency completeness is itself reported so a reader knows how much of
    --  the impact is known."  NOT NULL: a case cannot exist without it.
    dependency_completeness jsonb NOT NULL,
    impact_snapshot_id uuid NOT NULL REFERENCES design_advisory.impact_snapshot(snapshot_id),

    -- Test-evidence completeness, reported for the same reason
    test_coverage_summary   jsonb NOT NULL,
    test_attribution_ambiguity jsonb NOT NULL,   -- §3.2.4

    cost_estimate_id  uuid REFERENCES design_advisory.cost_estimate(estimate_id),
    projected_benefit jsonb,
    scenario_id       uuid REFERENCES design_advisory.design_scenario(scenario_id),

    -- --- E3: structurally non-directive ------------------------------------
    recommendation_stance design_advisory.recommendation_stance,
    recommendation_basis_refs jsonb,
    recommendation_limitations jsonb,
    recommendation_evidence_gaps jsonb,

    assembled_at      timestamptz,
    published_at      timestamptz,
    published_via_proposal_id uuid,     -- the ONLY route to 'published'.  §6.5
    classification    jsonb NOT NULL,

    CONSTRAINT case_version_unique UNIQUE (candidate_id, case_version),

    -- Assembly completeness: an assembled or published case has everything.
    CONSTRAINT assembled_is_complete CHECK (
        case_status NOT IN ('assembled','published')
        OR (cost_estimate_id IS NOT NULL
            AND recommendation_stance IS NOT NULL
            -- E3: limitations and evidence gaps are REQUIRED and NON-EMPTY.
            AND jsonb_typeof(recommendation_limitations) = 'array'
            AND jsonb_array_length(recommendation_limitations) > 0
            AND jsonb_typeof(recommendation_evidence_gaps) = 'array'
            AND jsonb_array_length(recommendation_evidence_gaps) > 0)
    ),
    -- E2: 'published' is reachable ONLY as the effect of an adjudicated proposal.
    CONSTRAINT published_requires_adjudicated_proposal CHECK (
        case_status <> 'published'
        OR (published_via_proposal_id IS NOT NULL AND published_at IS NOT NULL)
    )
);
```

`dependency_completeness` shape, computed by and only by the traversal in §4:

```json
{
  "computed_at": "2026-08-04T14:02:11.000000+00:00",
  "graph_snapshot_id": "…",
  "max_depth_requested": 3,
  "edges_touched": 47,
  "edges_verified": 29,
  "completeness_ratio": 0.6170,
  "nodes_expanded": 12,
  "nodes_truncated_at_depth": 3,
  "artifact_leaves_reached": 8,
  "unverified_by_relation": {
    "interfaces_with": 4, "fits_into": 2, "supports": 9, "allowance_listed_in": 3
  },
  "unverified_by_source_kind": { "inferred_cooccurrence": 11, "unverified_import": 7 },
  "is_bounded_below": true
}
```

Three properties are load-bearing:

- **`completeness_ratio` is never defaulted, never rounded up, and never absent.** `NOT NULL` on the column; a service-layer guard rejects a completeness object whose `edges_touched` disagrees with the snapshot it references.
- **`nodes_truncated_at_depth > 0` means the blast radius is provably incomplete regardless of the ratio.** A traversal that hit the depth cap with expandable nodes remaining has an unknown number of untouched edges, so a ratio of 1.0 over the edges it *did* touch is not a claim of totality. `is_bounded_below` is `true` whenever `completeness_ratio < 1.0` **or** `nodes_truncated_at_depth > 0`.
- **`unverified_by_relation` and `unverified_by_source_kind` are reported, not just the aggregate.** Nine unverified `supports` edges and nine unverified `training_covered_by` edges are very different exposures, and an aggregate ratio hides which one you have.

### 3.7 `CostEstimate` — with `method`

```sql
CREATE TABLE design_advisory.cost_estimate (
    estimate_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id      uuid NOT NULL REFERENCES design_advisory.redesign_candidate(candidate_id),
    case_id           uuid REFERENCES design_advisory.redesign_case(case_id),

    method            design_advisory.cost_method NOT NULL,   -- 04 §10: parametric | dependency_rollup
    cost_model_version text NOT NULL,
    model_ref         text NOT NULL,      -- 'inservice:<fn>@<ver>' | 'domino-endpoint:<name>@<ver>'

    point_estimate_usd numeric(14,2) NOT NULL,
    low_usd           numeric(14,2),
    high_usd          numeric(14,2),
    interval_basis    text,               -- how the interval was derived; NULL means none claimed
    confidence        numeric(3,2) CHECK (confidence > 0 AND confidence <= 1),

    -- Non-empty by constraint.  An estimate with no stated assumptions is not
    -- reviewable, and 04 §10 requires estimates "to a standard that a design
    -- engineer can evaluate and defend".
    assumptions       jsonb NOT NULL CHECK (jsonb_array_length(assumptions) > 0),
    cost_lines        jsonb,              -- rollup only: per-edge/per-artifact lines
    inputs_digest     char(64) NOT NULL,

    -- --- the rollup honesty fields ----------------------------------------
    impact_snapshot_id uuid REFERENCES design_advisory.impact_snapshot(snapshot_id),
    coverage_ratio    numeric(5,4),       -- copied from the snapshot it rolled up
    is_lower_bound    boolean NOT NULL,

    computed_at       timestamptz NOT NULL DEFAULT now(),
    classification    jsonb NOT NULL,

    -- A dependency roll-up MUST name the traversal it rolled up.  Without it,
    -- the total is unattributable.
    CONSTRAINT rollup_names_its_traversal CHECK (
        method <> 'dependency_rollup'
        OR (impact_snapshot_id IS NOT NULL AND coverage_ratio IS NOT NULL)
    ),
    -- THE RULE: a roll-up over an incomplete graph is a LOWER BOUND, and says so.
    CONSTRAINT rollup_incomplete_is_lower_bound CHECK (
        method <> 'dependency_rollup'
        OR (is_lower_bound = (coverage_ratio < 1.0))
    ),
    CONSTRAINT interval_paired CHECK (
        (low_usd IS NULL) = (high_usd IS NULL)
        AND (low_usd IS NULL OR (low_usd <= point_estimate_usd AND point_estimate_usd <= high_usd))
        AND (low_usd IS NULL) = (interval_basis IS NULL)
    )
);
```

`rollup_incomplete_is_lower_bound` is the constraint that makes the dependency-completeness reporting consequential rather than decorative. A detailed estimate that rolled up 61% of the edges it touched is **structurally a lower bound on cost**, and the schema will not let it be recorded as anything else. That single fact — *this number can only go up* — is what a design authority most needs and what an unqualified total silently destroys.

`interval_paired`'s third clause is deliberate: an interval may not be recorded without stating how it was derived. A ±30% band with no basis is a decoration that reads as rigour.

---

## 4. The dependency graph and the impact traversal

04 §10:

> **Dependency impact requires an explicit graph, and its absence is the usual reason redesign estimates are wrong.** Redesigning a component affects its interfaces, its fit, its supported and supporting items, its technical documentation, its allowance lists, and its training. The dependency graph makes that blast radius **computable rather than a matter of recollection**, and dependency completeness is itself reported so a reader knows how much of the impact is known.

"Traverse dependencies" is not a specification. What follows is the query.

### 4.1 The snapshot table — why the traversal is persisted

```sql
CREATE TABLE design_advisory.impact_snapshot (
    snapshot_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    root_niin         text NOT NULL REFERENCES design_advisory.part_ref(niin),
    max_depth         int  NOT NULL CHECK (max_depth BETWEEN 1 AND 6),
    as_of             timestamptz NOT NULL,
    policy_version    text NOT NULL,      -- relation_traversal_policy version in force
    computed_at       timestamptz NOT NULL DEFAULT now(),
    result            jsonb NOT NULL,     -- the full traversal output, verbatim
    dependency_completeness jsonb NOT NULL,
    edges_digest      char(64) NOT NULL,  -- over the sorted edge_id list touched
    classification    jsonb NOT NULL
);

CREATE INDEX is_root ON design_advisory.impact_snapshot (root_niin, computed_at DESC);
```

A `RedesignCase` and a `dependency_rollup` `CostEstimate` both reference a snapshot rather than re-running the traversal. **The graph mutates**; a case published in March that cites "47 edges touched, 61.7% verified" must remain reproducible in July when nine of those edges have been retracted and twelve added. `edges_digest` makes an unchanged re-run detectable and a changed one explainable. This is 03 §15 obligation 9 (provenance for every derived value) applied to the figure most likely to be challenged.

### 4.2 The traversal query, exactly

Packaged as a set-returning function so that **one implementation serves the API, the case builder, and the completeness computation** — the precedent is `reference_data.resolve_forward` in doc 12 §9.1, adopted for the same reason: a second implementation of a graph walk produces a second set of answers.

```sql
CREATE OR REPLACE FUNCTION design_advisory.impact(
    p_root_niin  text,
    p_max_depth  int         DEFAULT 3,
    p_as_of      timestamptz DEFAULT now()
) RETURNS jsonb
LANGUAGE sql STABLE AS $$
WITH RECURSIVE
params AS (
    SELECT p_root_niin AS root_niin,
           -- Hard cap 6, hard floor 1.  A caller cannot request an unbounded walk;
           -- the cap is the guard that keeps this a PostgreSQL-shaped problem
           -- (04 §10: "unless Phase 3 establishes depth requirements exceeding
           -- what that supports").
           LEAST(GREATEST(coalesce(p_max_depth, 3), 1), 6) AS max_depth,
           p_as_of AS as_of
),

-- ---------------------------------------------------------------------------
-- (1) Present every stored edge in BOTH orientations, but only the orientations
--     `relation_traversal_policy` sanctions.  Edges are stored once in canonical
--     direction (§3.4); orientations are GENERATED here, never duplicated as rows,
--     because duplicated inverse rows double the edge count and therefore corrupt
--     the completeness ratio.
-- ---------------------------------------------------------------------------
live_edge AS (
    SELECT e.*
      FROM design_advisory.dependency_edge e, params
     WHERE e.retracted_at IS NULL
       AND e.valid_from <= params.as_of
       AND (e.valid_to IS NULL OR e.valid_to > params.as_of)
),
directed AS (
    -- forward: src -> dst
    SELECT e.edge_id, e.relation, 'forward'::text AS orientation,
           e.src_niin                            AS from_niin,
           e.dst_kind                            AS to_kind,
           e.dst_niin                            AS to_niin,
           e.dst_artifact_id                     AS to_artifact_id,
           p.expands_forward                     AS expands,
           p.forward_weight                      AS weight,
           e.source_kind, e.verified_by, e.verified_at, e.confidence
      FROM live_edge e
      JOIN design_advisory.relation_traversal_policy p ON p.relation = e.relation
     WHERE p.traverse_forward
    UNION ALL
    -- reverse: dst -> src.  Only where dst is a part; an artifact is a leaf and is
    -- never a source (enforced by `artifacts_are_leaves` in §3.4), so there is no
    -- reverse orientation to generate for it.
    SELECT e.edge_id, e.relation, 'reverse'::text,
           e.dst_niin,
           e.src_kind, e.src_niin, e.src_artifact_id,
           p.expands_reverse,
           p.reverse_weight,
           e.source_kind, e.verified_by, e.verified_at, e.confidence
      FROM live_edge e
      JOIN design_advisory.relation_traversal_policy p ON p.relation = e.relation
     WHERE p.traverse_reverse
       AND e.dst_kind = 'part'
),

-- ---------------------------------------------------------------------------
-- (2) The walk.  Depth-limited, cycle-safe, artifact-terminal.
-- ---------------------------------------------------------------------------
walk AS (
    -- depth 1: everything one sanctioned hop from the root
    SELECT d.edge_id, d.relation, d.orientation,
           d.from_niin, d.to_kind, d.to_niin, d.to_artifact_id,
           d.expands, d.weight, d.source_kind, d.verified_by, d.verified_at, d.confidence,
           1                                              AS depth,
           d.weight                                       AS path_weight,
           ARRAY[params.root_niin, d.to_niin]::text[]     AS part_path
      FROM directed d, params
     WHERE d.from_niin = params.root_niin

    UNION ALL

    SELECT d.edge_id, d.relation, d.orientation,
           d.from_niin, d.to_kind, d.to_niin, d.to_artifact_id,
           d.expands, d.weight, d.source_kind, d.verified_by, d.verified_at, d.confidence,
           w.depth + 1,
           w.path_weight * d.weight,
           w.part_path || d.to_niin
      FROM walk w
      JOIN directed d ON d.from_niin = w.to_niin
      JOIN params ON true
     WHERE w.to_kind = 'part'          -- an artifact is terminal: never expanded THROUGH
       AND w.expands                   -- the arriving orientation permits continuation
       AND w.depth < params.max_depth   -- depth bound
       -- Cycle prevention.  `part_path` carries the NIINs already on THIS path;
       -- artifacts need no entry because they are never expanded.  This is a
       -- per-path check, not a global visited-set: the same NIIN legitimately
       -- appears on two different paths at two different depths, and a global
       -- visited-set would silently drop the second, understating the blast radius.
       AND NOT (d.to_niin = ANY(w.part_path))
       AND d.to_niin IS DISTINCT FROM params.root_niin
),

-- ---------------------------------------------------------------------------
-- (3) Verification status, per DISTINCT edge.  DISTINCT ON edge_id, not on
--     (edge_id, orientation): a symmetric edge traversed in both directions is
--     ONE edge of known-or-unknown provenance, not two.
-- ---------------------------------------------------------------------------
edge_touched AS (
    SELECT DISTINCT ON (w.edge_id)
           w.edge_id, w.relation, w.source_kind,
           (sp.is_verifiable_source
            AND w.verified_by IS NOT NULL
            AND w.verified_at IS NOT NULL)                AS is_verified,
           min(w.depth)  OVER (PARTITION BY w.edge_id)    AS first_depth
      FROM walk w
      JOIN design_advisory.dependency_source_policy sp ON sp.source_kind = w.source_kind
     ORDER BY w.edge_id, w.depth
),

-- ---------------------------------------------------------------------------
-- (4) Truncation: part nodes reached AT the depth cap that still have sanctioned
--     outbound orientations.  These are the nodes whose onward edges were never
--     touched, so the ratio in (5) is a ratio over an incomplete edge set and the
--     result must say so.
-- ---------------------------------------------------------------------------
frontier AS (
    SELECT DISTINCT w.to_niin
      FROM walk w, params
     WHERE w.to_kind = 'part'
       AND w.depth = params.max_depth
       AND w.expands
       AND EXISTS (SELECT 1 FROM directed d WHERE d.from_niin = w.to_niin)
),

-- ---------------------------------------------------------------------------
-- (5) Completeness, computed IN THE SAME STATEMENT as the traversal.  A separate
--     query could disagree with the walk it claims to describe — different
--     `as_of`, a concurrent retraction, a different policy version.  The reported
--     completeness is therefore the completeness OF THE TRAVERSAL THAT RAN.
-- ---------------------------------------------------------------------------
completeness AS (
    SELECT count(*)::int                                        AS edges_touched,
           count(*) FILTER (WHERE is_verified)::int              AS edges_verified,
           CASE WHEN count(*) = 0 THEN NULL
                ELSE round(count(*) FILTER (WHERE is_verified)::numeric
                           / count(*)::numeric, 4)
           END                                                  AS completeness_ratio,
           (SELECT count(DISTINCT to_niin)::int FROM walk WHERE to_kind = 'part')      AS nodes_expanded,
           (SELECT count(*)::int FROM frontier)                                        AS nodes_truncated_at_depth,
           (SELECT count(DISTINCT to_artifact_id)::int FROM walk WHERE to_kind = 'artifact')
                                                                                       AS artifact_leaves_reached,
           (SELECT coalesce(jsonb_object_agg(relation, n), '{}'::jsonb)
              FROM (SELECT relation, count(*)::int AS n FROM edge_touched
                     WHERE NOT is_verified GROUP BY relation) r)                       AS unverified_by_relation,
           (SELECT coalesce(jsonb_object_agg(source_kind, n), '{}'::jsonb)
              FROM (SELECT source_kind, count(*)::int AS n FROM edge_touched
                     WHERE NOT is_verified GROUP BY source_kind) s)                    AS unverified_by_source_kind
      FROM edge_touched
)

SELECT jsonb_build_object(
    'root_niin',  (SELECT root_niin FROM params),
    'as_of',      (SELECT as_of     FROM params),
    'max_depth_requested', (SELECT max_depth FROM params),
    'policy_version', (SELECT max(policy_version) FROM design_advisory.relation_traversal_policy),

    'impacted_parts', (
        SELECT coalesce(jsonb_agg(x ORDER BY x->>'min_depth', x->>'niin'), '[]'::jsonb)
          FROM (SELECT jsonb_build_object(
                    'niin',        w.to_niin,
                    'min_depth',   min(w.depth),
                    'max_path_weight', round(max(w.path_weight), 4),
                    'relations',   jsonb_agg(DISTINCT w.relation),
                    'verified_edge_count', count(*) FILTER (
                        WHERE (SELECT is_verified FROM edge_touched et WHERE et.edge_id = w.edge_id)),
                    'edge_count',  count(DISTINCT w.edge_id))
                  FROM walk w WHERE w.to_kind = 'part' GROUP BY w.to_niin) t(x)),

    'impacted_artifacts', (
        SELECT coalesce(jsonb_agg(jsonb_build_object(
                    'artifact_id',  a.artifact_id,
                    'artifact_kind',a.artifact_kind,
                    'external_ref', a.external_ref,
                    'via_relation', w.relation,
                    'min_depth',    min(w.depth))
                 ORDER BY a.artifact_kind, a.external_ref), '[]'::jsonb)
          FROM walk w
          JOIN design_advisory.dependency_artifact a ON a.artifact_id = w.to_artifact_id
         WHERE w.to_kind = 'artifact'
         GROUP BY a.artifact_id, a.artifact_kind, a.external_ref, w.relation),

    'truncated_at_depth', (SELECT coalesce(jsonb_agg(to_niin ORDER BY to_niin), '[]'::jsonb) FROM frontier),

    'dependency_completeness', (
        SELECT jsonb_build_object(
            'computed_at',              now(),
            'max_depth_requested',      (SELECT max_depth FROM params),
            'edges_touched',            c.edges_touched,
            'edges_verified',           c.edges_verified,
            'completeness_ratio',       c.completeness_ratio,
            'nodes_expanded',           c.nodes_expanded,
            'nodes_truncated_at_depth', c.nodes_truncated_at_depth,
            'artifact_leaves_reached',  c.artifact_leaves_reached,
            'unverified_by_relation',   c.unverified_by_relation,
            'unverified_by_source_kind',c.unverified_by_source_kind,
            -- The claim that matters: is this blast radius provably partial?
            'is_bounded_below', (coalesce(c.completeness_ratio, 0) < 1.0
                                 OR c.nodes_truncated_at_depth > 0))
          FROM completeness c),

    'edges_digest', (
        SELECT encode(sha256(coalesce(string_agg(edge_id::text, ',' ORDER BY edge_id), '')::bytea), 'hex')
          FROM edge_touched)
);
$$;
```

### 4.3 The eight properties that make this query correct

Each corresponds to a way a naive traversal gets a blast radius wrong.

| # | Property | The defect it prevents |
|---|---|---|
| 1 | **Both orientations generated from a singly-stored edge** | Storing inverse rows doubles `edges_touched`, halving the apparent unverified fraction. A completeness ratio you can improve by inserting duplicate rows is not a measurement |
| 2 | **Orientation is policy-driven, per relation** | Traversing every relation symmetrically makes every technical manual a hub: two unrelated components sharing an IETM appear mutually dependent. Traversing everything forward-only misses that redesigning a housing impacts what fits in it |
| 3 | **`expands` is separate from `traverse`** | An edge can be *in* the blast radius without being a path *through* which impact continues. Conflating them is what makes `supports` chains run to arbitrary depth in the wrong direction |
| 4 | **Artifacts are terminal, enforced by a CHECK constraint** | Without `artifacts_are_leaves`, one mis-ingested edge with an artifact source turns a training product into a traversable hub |
| 5 | **Per-path cycle detection, not a global visited-set** | A global visited-set drops the second and subsequent paths to a node. The same NIIN reached at depth 1 via `interfaces_with` and at depth 2 via `supports` is two distinct impact routes, and dropping one **understates** the radius — the error direction that produces confident, cheap, wrong estimates |
| 6 | **`DISTINCT ON (edge_id)` for verification, ignoring orientation** | A symmetric edge counted twice, once verified and once not, yields an incoherent ratio |
| 7 | **Completeness computed in the same statement** | A second query runs at a different instant against a possibly-changed graph and reports the completeness of a traversal that never happened |
| 8 | **`nodes_truncated_at_depth` reported alongside the ratio** | A depth-capped walk can score 1.0 on the edges it touched while an unknown number of edges were never reached. The ratio alone would read as totality; `is_bounded_below` prevents that reading |

### 4.4 `dependency_completeness`, defined precisely

```
edge_verified(e)  ⇔  dependency_source_policy[e.source_kind].is_verifiable_source
                     ∧ e.verified_by IS NOT NULL
                     ∧ e.verified_at IS NOT NULL

E                 =  { distinct edge_id touched by the traversal }
completeness_ratio = |{ e ∈ E : edge_verified(e) }| / |E|          (NULL when |E| = 0)

is_bounded_below  ⇔  completeness_ratio < 1.0  ∨  nodes_truncated_at_depth > 0
```

**Worked example.** Root NIIN `012345678`, `max_depth = 3`. The walk touches 47 distinct edges across 12 part nodes and 8 artifact leaves. Of those, 29 come from `cdmd_oa_federation`, `engineering_drawing`, `apl_derived`, or `sme_asserted` **and** carry a `verified_by`/`verified_at` pair. 11 come from `inferred_cooccurrence` and 7 from `unverified_import` — both `is_verifiable_source = false`, so neither can count however they are stamped.

`completeness_ratio = 29/47 = 0.6170`. Three part nodes sat at depth 3 with sanctioned outbound edges, so `nodes_truncated_at_depth = 3` and `is_bounded_below = true`.

A case built on this snapshot reports: *38% of the dependency edges in this blast radius have no verified source, and the radius is bounded below because the traversal was capped at depth 3 with three expandable nodes remaining.* A `dependency_rollup` cost estimate over it is recorded with `is_lower_bound = true` (§3.7).

**Why the ratio is over edges rather than nodes.** Cost accrues per dependency, not per component: one NIIN with four unverified interface edges is four unknown cost lines. A node-based ratio would count that as a single unknown.

### 4.5 The two dependency operations

```
GET /api/v1/design-advisory/dependencies?niin=&depth=&relation=&as_of=&limit=&cursor=
```
The **neighbourhood read**: edges within `depth` hops, cursor-paginated, no traversal semantics claimed, no completeness object. `x-substitution: required`, `x-side-effects: none`, `x-agent-eligible: true`. `depth` defaults to 1 and is capped at 6.

```
GET /api/v1/design-advisory/dependencies/{niin}/impact?max_depth=&as_of=&persist=
```
The **traversal**. Returns exactly the `design_advisory.impact(...)` document. `x-substitution: required`, `x-side-effects: none`, `x-agent-eligible: true`.

- `impact` is a **query-projection singular sub-resource**, so it is enumerated in `x-naming-carve-outs` with the reason, per 03 §4's carve-out rule `[C23]`.
- `persist=true` writes an `impact_snapshot` row and returns its `snapshot_id`. **This does not make the operation `state-changing`**: it alters no domain state, only the provenance record of a computation, exactly as 03 §4.1 permits for computational operations. The service records the snapshot under the caller's identity and the operation remains agent-eligible, which is what lets the Redesign Case Builder cite a reproducible traversal without holding a write authority.
- Response carries `X-Classification` as the union of every edge's label (03 §7.3, `inherited_from`).
- `422` with `urn:fathom:problem:design-advisory:unknown-niin` when the root NIIN is not in the read model; **never an empty successful result**, because an empty impact set and an unknown part are different facts.

---

## 5. Two-stage costing, with an explicit gate

04 §10:

> **Two-stage costing.** A fast parametric estimate qualifies candidates; a detailed dependency-rollup estimate is produced for candidates that survive qualification. Producing detailed estimates for every candidate is wasted effort, and producing only parametric estimates yields business cases that do not withstand review.

The gate between the stages is the part that is usually left implicit. Here it is a persisted decision record and an API precondition.

### 5.1 Stage 1 — the parametric estimator

```
POST /api/v1/design-advisory/redesign-candidates/{id}/parametric-estimate
```
`x-substitution: required` · `x-side-effects: none` · `x-agent-eligible: true`

A pure computation: fast, re-derivable, persists nothing. Inputs are the candidate's driver evidence, `affected_population`, PdM criticality tier, the NIIN's `part_availability` read-model figures (unit cost, `lead_time`, `condition_code` — 03 §6 `[D6, D24]`), and the count of impacted parts and artifacts at `max_depth = 1`. Output is a `CostEstimate` document with `method = parametric`, unpersisted.

Deliberately shallow: stage 1 must not traverse the graph deeply, or it is not fast and the two-stage split buys nothing.

### 5.2 The gate — a persisted, reproducible decision

```sql
CREATE TABLE design_advisory.gate_decision (
    gate_decision_id  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id      uuid NOT NULL REFERENCES design_advisory.redesign_candidate(candidate_id),
    decision          text NOT NULL CHECK (decision IN ('pass','fail')),
    evaluated_at      timestamptz NOT NULL DEFAULT now(),
    evaluated_by      text NOT NULL,

    -- Every threshold value IN FORCE at evaluation, recorded on the row.  A gate
    -- outcome must be reproducible after the thresholds change; a decision that
    -- cites "the configured floor" is not reproducible.
    thresholds_in_force jsonb NOT NULL,
    gate_policy_version text NOT NULL,

    -- Per-condition outcome, so a 'fail' says WHICH condition failed.
    condition_results jsonb NOT NULL,

    parametric_estimate jsonb NOT NULL,     -- the stage-1 result, verbatim
    dossier_id        uuid NOT NULL REFERENCES design_advisory.failure_dossier(dossier_id),
    impact_snapshot_id uuid NOT NULL REFERENCES design_advisory.impact_snapshot(snapshot_id),

    superseded_by     uuid REFERENCES design_advisory.gate_decision(gate_decision_id),
    classification    jsonb NOT NULL
);

CREATE UNIQUE INDEX gd_one_live_per_candidate
    ON design_advisory.gate_decision (candidate_id) WHERE superseded_by IS NULL;
```

**Append-only, superseded never overwritten.** New evidence — a fresh causal finding, more field failures, a newly verified edge — re-evaluates the gate and writes a new row pointing the old one at it. A candidate that failed the gate in March and passed in June has both facts on the record, which is exactly what a reviewer asking "why did this become a priority?" needs.

### 5.3 The gate condition, exactly

```
GATE_PASS(candidate c, dossier d, snapshot s, parametric p)  ⇔

  (G1)  p.point_estimate_usd            ≥  COST_FLOOR_USD
  (G2)  c.priority_score                ≥  PRIORITY_FLOOR
  (G3)  s.dependency_completeness.completeness_ratio  ≥  COMPLETENESS_FLOOR
  (G4)  |{ t ∈ d.test_coverage : t.record_status = 'absent_unknown' }|  =  0
  (G5)  ( |{ f ∈ d.field_failures : f.failure_indicator }|  ≥  FIELD_FAILURE_FLOOR )
        ∨ ( |{ x ∈ d.causal_citations : x.posture = 'supporting'
                                      ∧ x.adjudication_state = 'published' }|  ≥  1 )
  (G6)  c.status ∈ { 'identified', 'qualifying' }   ∧   c.dossier_id = d.dossier_id
```

Each condition, and why it is that condition:

| | Condition | Rationale |
|---|---|---|
| **G1** | Parametric cost meets a floor | The entire point of the gate. Detailed estimation is expensive; below some cost the redesign is not a programmatic decision worth a dependency roll-up |
| **G2** | Priority meets a floor | A costly redesign of something nothing depends on and nothing fails is still not worth detailed estimation |
| **G3** | Dependency completeness meets a floor | **A dependency roll-up over a graph that is mostly unverified produces a number with false precision.** Below the floor, the correct next action is to *populate the graph*, not to cost it. The gate failure names this as the remedy in `condition_results` |
| **G4** | **Test coverage has been *assessed*** — zero `absent_unknown` rows | Note carefully what this does **not** require: it does not require that tests exist, that they passed, or that coverage is complete. Legacy components frequently have no qualification data and that must not bar analysis (04 §10). It requires only that every expected test kind has been **looked at** and its status established — `present`, `absent_not_performed`, `absent_not_located`, or `absent_not_required`. `absent_unknown` means nobody has checked, and a business case whose test section says "we have not looked" is not defensible |
| **G5** | An evidentiary floor, **disjunctive** | Some evidence must exist, or stage 2 is costing a hypothesis. Either enough corrective field failures, or at least one *published* supporting causal citation |
| **G6** | State and dossier consistency | Prevents gating a candidate against a dossier that is not its own |

**G5 deliberately does not threshold on evidence strength, and this is the most important design decision in the gate.** It would be easy to write `∧ strength ≥ MODERATE`. That would be wrong for two reasons. First, it would require this sub-application to *rank* Failure Intelligence's strength values, which is precisely the authoring of a local strength judgment that §8 forbids. Second, **whether a given evidence strength justifies a redesign is a design-authority judgment, not a cost-efficiency judgment.** The gate exists to decide where to spend estimation effort. Smuggling an evidentiary sufficiency test into it would move a decision that belongs to a human into a configuration constant. A weak-but-published finding on an expensive, high-priority, widely-depended-upon component may well warrant a detailed estimate — and the resulting case will carry that weak strength verbatim into the design authority's hands, which is the correct outcome.

`contra` citations never satisfy G5 (§3.3.1).

### 5.4 The thresholds are placeholders, and the service will not start without them

**No source document supplies any of these values.** 04 §10 lists cost-model depth as an open Phase 3 question; 06 §7 supplies no cost figures at all. 09 DO-NOT-31 forbids inventing quantities.

So, following the pattern doc 10 §4.6 establishes for `CONTRIBUTING_FACTOR_STABILITY_FLOOR` — *"deliberately ABSENT, because no document supplies a value"* — the thresholds are **required settings with no defaults**:

```python
# services/design-advisory/src/fathom_design_advisory/config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FATHOM_", frozen=True)

    # ---- Stage-2 gate thresholds -------------------------------------------
    # PLACEHOLDER — pending Phase 3 SME validation.  OD-1 (§15).
    #
    # NO DEFAULTS, DELIBERATELY.  These are program judgments about where to
    # spend engineering estimation effort.  No architecture document supplies a
    # value, and 09 DO-NOT-31 forbids inventing one.  A default here would be an
    # invented number that ships, gets used, and is never revisited because it
    # never looked like a decision.  Absent configuration -> the service fails to
    # start with a message naming this section.
    gate_cost_floor_usd: Decimal
    gate_priority_floor: Decimal
    gate_completeness_floor: Decimal        # 0 < x <= 1
    gate_field_failure_floor: int
    gate_policy_version: str                # e.g. "v0-placeholder"

    @field_validator("gate_policy_version")
    @classmethod
    def _placeholder_is_declared(cls, v: str) -> str:
        # Until Phase 3 validates the thresholds, the policy version MUST say so.
        # Every gate_decision row carries it, so every downstream artefact that
        # depended on a placeholder gate is identifiable later by a single query.
        return v
```

Values are supplied per environment in `values-dev.yaml` with `gate_policy_version: "v0-placeholder"`, and **every `gate_decision` row carries that string**. When Phase 3 sets real thresholds, one query identifies every candidate, case, and estimate that passed a placeholder gate. That is the difference between a placeholder and a guess.

### 5.5 Stage 2 — the detailed roll-up, and the gate enforced in the API

```
POST /api/v1/design-advisory/redesign-cases/{id}/estimate
```
`x-substitution: required` · `x-side-effects: state-changing` · **not** agent-eligible · `Idempotency-Key` required · `If-Match` required

Body: `{ "method": "parametric" | "dependency_rollup", "impact_snapshot_id": "…" }`

**The gate is a precondition on this operation.** With `method = dependency_rollup`:

```
409 Conflict
Content-Type: application/problem+json

{ "type":   "urn:fathom:problem:design-advisory:gate-not-passed",
  "title":  "Detailed dependency roll-up requires a passed qualification gate",
  "status": 409,
  "detail": "candidate 7f3c… has gate_decision f19a… decision=fail",
  "candidate_id": "7f3c…",
  "gate_decision_id": "f19a…",
  "failed_conditions": ["G3"],
  "remedy": "dependency_completeness.completeness_ratio 0.41 < COMPLETENESS_FLOOR 0.60; \
             populate or verify dependency edges for this NIIN before costing" }
```

Four properties:

1. **The gate is enforced at the API boundary, not in the estimator.** A caller cannot obtain a detailed roll-up by any route without a live `gate_decision` with `decision = 'pass'`.
2. **`failed_conditions` names the conditions by identifier**, so the response is actionable and the gate is debuggable. `detail` is never used for control flow (03 §4).
3. **`method = parametric` is always permitted** — recording the cheap estimate on a case is not gated.
4. **The stage-2 estimator refuses to run outside its staleness bound.** Roll-up cost lines depend on `part_availability.changed` (unit cost, lead time, condition code). Per 03 §5.2 and 09 DO-NOT rules, the operation declares a staleness bound on the `part_availability` read model and returns `503` with `urn:fathom:problem:design-advisory:read-model-stale`, incrementing `fathom_staleness_refusals_total`, rather than costing against figures weeks old. The parametric estimator declares no such bound, which is part of what makes it the fast stage.

### 5.6 What the roll-up actually rolls up

Per-line cost against the `impact_snapshot`, so the estimate's structure mirrors the traversal that justified it:

| Cost line class | Driven by | Source grounding |
|---|---|---|
| Redesign engineering | root NIIN, driver complexity | Program cost model — placeholder (OD-2) |
| Interface rework | `impacted_parts` reached via `interfaces_with` / `fits_into` | Per-edge factor — placeholder |
| Supported-item impact | `impacted_parts` via `supports` | Per-edge factor — placeholder |
| Technical publication revision | `impacted_artifacts` kind `technical_publication` | Per-artifact factor — placeholder |
| Allowance revision | `impacted_artifacts` kind `allowance_list` | 07 §4.2/§4.3 supply documented COSAL/APL structure and the allowance-computation rule; the **cost** of a revision is not documented — placeholder |
| Training product revision | `impacted_artifacts` kind `training_product` | Placeholder |
| Qualification re-test | `dossier_test_coverage` rows requiring re-test | Placeholder, and **absence-aware**: an `absent_not_located` qualification test that the redesign would require is a re-test cost line, whereas the same test recorded `present`/`pass` is not. This is where §3.2's absence representation converts directly into money |

Every factor is `PLACEHOLDER` in `cost_model_version` and enumerated in `assumptions[]` on the resulting estimate, so no reader of a demonstration case can mistake the factors for validated rates. **OD-2 (§15).**

The last row is worth stating plainly, because it is the payoff of the whole absence design: **a component whose qualification history cannot be located is more expensive to redesign than one whose qualification passed**, because the redesign must re-establish what was lost. A schema that represented missing test data as a missing row could not produce that cost line at all — it would cost the two components identically, and be wrong in the optimistic direction.

---

## 6. The redesign case builder workflow

Document 01 §8.1 names the **Redesign Case Builder** agent — *"Assembles the evidence dossier — failure history, causal attribution, test data, dependency impact, cost estimate — and drafts the business case"* — for the PEO and design engineer. It is one of the three agents in demonstration scope (06 §7). Per 03 §8, it reaches this sub-application **only through its published API as tools**, and per 01 §8.4 and 03 §7.2 it **never writes domain state**.

### 6.1 The workflow, with the side-effect class of every step

| # | Step | Operation | `x-side-effects` | Agent-eligible | Note |
|---|---|---|---|---|---|
| 1 | Identify or select the candidate | `GET /redesign-candidates?status=&min_priority=` | `none` | ✔ | |
| 2 | Assemble / read the dossier | `POST /dossiers/assemble` then `GET /dossiers/{id}` | `none` | ✔ | See §6.2 — assembly is a computation, not a state change |
| 3 | Field failure history | included in the dossier | `none` | ✔ | From the `maintenance_action.recorded` / `installed_item.removed` read models |
| 4 | Causal findings | included in the dossier, **verbatim strength** | `none` | ✔ | §8. Never upgraded, never paraphrased in place of the object |
| 5 | Test data, **absence explicit** | included in the dossier | `none` | ✔ | One row per expected test kind; §3.2.2 |
| 6 | Dependency impact | `GET /dependencies/{niin}/impact?persist=true` | `none` | ✔ | §4.5 |
| 7 | Parametric estimate | `POST /redesign-candidates/{id}/parametric-estimate` | `none` | ✔ | §5.1 |
| 8 | Evaluate the gate | `POST /redesign-candidates/{id}/evaluate-gate` | `none` | ✔ | §6.3 — computes and returns; recording is a provenance write |
| 9 | Draft the case | `POST /redesign-cases/{id}/assemble` — **not agent-reachable** | `state-changing` | ✗ | §6.4 |
| 10 | Detailed roll-up | `POST /redesign-cases/{id}/estimate` — **not agent-reachable** | `state-changing` | ✗ | §5.5, gate-gated |
| 11 | **Propose** the case | `POST /proposals` (`kind=redesign_case`) | **`proposal-only`** | ✔ | §6.4. The agent's terminal act |
| 12 | Adjudicate | `POST /proposals/{id}/claim`, then `POST /proposals/{id}/adjudicate` | `state-changing` | ✗ | **Human, `design_authority`.** §6.5 |
| 13 | Publish | *no operation* — an effect of step 12 | — | — | §6.5 |

**Steps 1–8 and 11 are the agent's entire reach.** Everything the agent does is either a read-only assembly or a proposal. Steps 9, 10, and 12 are human or service operations.

Two clean consequences fall out of the 03 §4.1 side-effect model, and neither is available under an HTTP-method gate (`[C1, D11]`): the compute-only `POST` operations at steps 2, 7, and 8 are agent-eligible despite being `POST`s, and the `POST`s at steps 9 and 10 are excluded despite being structurally similar. **This sub-application is a third instance of the pattern C1/D11 was raised to fix**, alongside `pdm-whatif` and `POST /work-packages/plan`.

### 6.2 Why dossier assembly is `x-side-effects: none`

`POST /dossiers/assemble` writes a `failure_dossier` row. That looks like a state change, and the classification needs justifying rather than asserting.

03 §4.1: *"`x-side-effects: none` asserts the operation does not alter **domain state**. It is permitted on `GET` and on computational `POST` operations such as scenario analysis and planning."*

A dossier is a **snapshot of evidence this service already holds**, deterministic in its inputs, carrying `inputs_digest` and `read_model_watermarks`. It asserts nothing new about the world; it makes a computation reproducible. Re-running it with identical inputs yields an identical digest. Nothing downstream is triggered, no event is published, no other aggregate transitions. It is the provenance record of a read, in the same category as `?persist=true` on the impact traversal (§4.5).

**The boundary that keeps this honest:** a `none` operation in this service may write only *snapshot and provenance* tables — `failure_dossier` and children, `impact_snapshot`, `gate_decision`. It may **never** write `redesign_candidate`, `redesign_case`, `cost_estimate`, `design_scenario`, or `proposal`, and it may never emit an outbox row. That is a lint rule over the `services/` layer (§13, T-SIDEEFFECT-1), not a convention.

### 6.3 Gate evaluation, split from gate consumption

`POST /redesign-candidates/{id}/evaluate-gate` (`none`, agent-eligible) evaluates §5.3, writes the `gate_decision` provenance row, and returns the decision with `condition_results`. It **does not** transition the candidate.

`redesign_candidate.status` moves to `gate_passed` / `gate_failed` in step 9's `state-changing` operation. The split matters: an agent may compute and record *that the gate evaluated to pass*, and a service operation acts on it. An agent whose reach extended to the status transition would be advancing a candidate through a workflow, which is a decision.

### 6.4 The proposal — `design_authority` per the new 03 §7.2.1

`POST /proposals` · `x-substitution: required` · `x-side-effects: proposal-only` · `x-agent-eligible: true` · `Idempotency-Key` **required** (03 §4: required for any operation reachable from an agent proposal).

Fields this service sets itself, never accepting them from the caller:

```python
# services/design-advisory/src/fathom_design_advisory/services/proposals.py
#
# Document 03 §7.2.1: "A proposal's `authority_class` field is set BY THE OWNING
# SUB-APPLICATION at creation, from this table, and re-validated at adjudication."
# Design Advisory owns `redesign_case`, so this function is the authoritative
# implementation of that table's `redesign_case` row.

def authority_for_redesign_case(blast_radius: BlastRadius) -> tuple[str, bool]:
    """Return (authority_class, requires_dual_control).

    Document 03 §7.2.1, `redesign_case` row:
        item/asset -> design_authority
        class      -> design_authority
        fleet      -> design_authority + dual control

    Document 03 §7.2 rule 4 is STRICTER at class scope: "Dual control is
    MANDATORY at class and fleet scope and for any kind with external legal
    effect."  §7.2.1's table annotates "+ dual control" only on the fleet cell.

    THE STRICTER RULE IS APPLIED.  §7.2.1 is a MINIMUM-AUTHORITY table -- its own
    closing sentence says Phase 3 "may not remove the minimum this table
    establishes" -- it is not an exhaustive dual-control table, and §7.2 rule 4
    is unqualified.  `packages/canonical-schemas`' Proposal validator already
    forces dual control at class and fleet scope, so the alternative reading is
    not even representable.  Recorded as correction #3 in §16.
    """
    return (
        AuthorityClass.DESIGN_AUTHORITY,
        blast_radius in (BlastRadius.CLASS, BlastRadius.FLEET),
    )
```

`blast_radius` is derived from the dossier's `affected_population`, never supplied by the caller:

| Affected population | `blast_radius` |
|---|---|
| One installed item | `item` |
| Items confined to one asset | `asset` |
| Items across multiple hulls of one class | `class` |
| Items spanning classes | `fleet` |

Everything else follows 03 §7.2 and doc 10 §4.7 unchanged: `evidence[]` required and non-empty with `source_trust` per item; `baseline_id` / `baseline_epoch` carried and **re-validated at adjudication**; `valid_until` set; claim-then-`If-Match` adjudication; `target_sub_app = "design-advisory"`.

**Evidence composition for a `redesign_case` proposal.** `evidence[]` must include, at minimum, the `case_id`, the `dossier_id`, the `impact_snapshot_id`, the `gate_decision_id`, and the `cost_estimate_id`. `source_trust` is `program` for each. Any retrieved document chunk supporting the rationale carries its own `source_trust` per 03 §9, and **a proposal resting solely on non-program content is flagged to the adjudicator** — for this proposal kind that flag is close to disqualifying, and the adjudication UI surfaces it prominently.

**[AMENDMENT — closes `42-redesign-case-builder.md` §18 item 4.]** `payload`'s shape for this `kind` was unspecified here, though §6.5 below dereferences `proposal.payload["case_id"]` and 03 §7.2 makes `payload` *"the domain object, validated by the owning sub-application"* — this service, not the agent that proposes it. Adopted from `42-redesign-case-builder.md` §6.2, whose Redesign Case Builder is the reference sender:

```
RedesignCaseProposalPayload {
  case_id                       # required. Dereferenced at §6.5 below
  case_version                  # required. The version the agent read at its step 10
  candidate_id
  dossier_id, dossier_version
  impact_snapshot_id
  gate_decision_id
  cost_estimate_id
  scenario_id?                  # only where a DesignScenario already exists; §7.2

  carried_digests { dossier, impact_snapshot, gate_decision }   # attestations, not
                                                                 # assertions — this
                                                                 # service re-validates
                                                                 # against current state
                                                                 # at adjudication regardless
  narrative_sections[] { section, text, source_pointers[] }

  evidence_gaps[]  { code, basis_ref, quantities }              # derived, complete,
  limitations[]    { code, basis_ref, quantities }              # no model output

  prompt_digest, manifest_pins[], renderer_versions[]
}
```

**Deliberately absent:** `recommendation_stance`, `recommendation_limitations`, `recommendation_evidence_gaps` (those exist only on the case, written by the human at `assemble` — duplicating them into the payload would create a second, agent-authored version an adjudicator could act on instead of the committed one); `evidence_strength` or any strength band (cited by reference to the dossier, never copied, per §6.3's rules above); a cost figure (cited by `cost_estimate_id`, never restated as a number that could disagree with it); `blast_radius` and `authority_class` (this service derives both, per the function above — never caller-supplied).

Added to `packages/canonical-schemas` alongside `Proposal`, with golden vectors per `10-shared-packages.md` §4.9's convention for the other typed payload shapes.

### 6.5 Publication is an effect of human adjudication — E2, mechanically

The service consumes its own `proposal.adjudicated` event. On `status = approved`:

```python
async with uow.begin():
    case = await repo.transition_case(
        case_id=proposal.payload["case_id"],
        to_status=CaseStatus.PUBLISHED,
        published_via_proposal_id=proposal.proposal_id,   # NOT NULL constraint, §3.6
    )
    outbox.emit(
        uow,
        event_type="fathom.design-advisory.redesign_case.published",
        aggregate="redesign_case", aggregate_id=str(case.case_id),
        scope=Scope.NIIN, subject=Subject(niin=case.niin),
        payload=RedesignCasePublished.from_domain(case),
        classification=case.classification,
        baseline_epoch=case.baseline_epoch,
    )
```

`published_requires_adjudicated_proposal` (§3.6) makes the `published` state **unreachable without a proposal identifier**, and no route accepts a `case_status` value directly. Publication therefore cannot occur without a human with `design_authority` having adjudicated — plus a second signature at class or fleet scope.

**And publication is still not a redesign decision.** `redesign_case.published` means *this decision package has been reviewed for adequacy by a design authority and released*. What the design authority then does about the redesign happens in acquisition and configuration-management processes entirely outside this system, and the event carries no field capable of expressing such an outcome. The distinction is stated in the aggregate's description, in the event's AsyncAPI description, and in the practitioner UI, because it is the one a reader is most likely to collapse.

### 6.6 Agent authority and the manifest

| Invocation mode | Authority class (03 §8.3) | Notes |
|---|---|---|
| Interactive, invoked by a PEO or design engineer | **Delegated** — the user's token | Reach bounded by that user's own authorization, evaluated here, never by the gateway alone |
| Triggered by `causal_finding.published` for a high-priority NIIN | **Accountable autonomous** — scoped short-lived workload identity with a **named accountable human owner** | Restricted to `none` and `proposal-only`; cannot read outside its declared scope; every run recorded to Audit with the owner |

Manifest: `packages/agent-tooling/manifests/design-advisory/design-advisory-redesign-case.v1.yaml`, `owner: redesign-case-builder`, selecting exactly the nine agent-eligible operations at steps 1–8 and 11. Its conformance test (03 §8.4) runs inside this service's conformance suite, so a conformant substitution is automatically a conformant tool surface.

**Mid-run authority lapse** (03 §8.3): a run whose delegated token expires terminates with a resumable checkpoint. It does not continue under a service identity and **does not create a proposal after its authority has lapsed** — enforced here by re-validating the principal at `POST /proposals` rather than trusting the token presented at run start.

**Untrusted content** (03 §9): test reports, engineering change proposals, and CASREP narratives are named in 03 §9 as part of the untrusted corpus. Retrieved text is data, never instruction. Domain policy — the gate, the authority table, the passthrough rule, the absence rules — is enforced **in this service**, regardless of what an agent proposed or why.

---

## 7. `design_change.projected` segregation

04 §10:

> **Projected design changes feed back to Predictive Maintenance.** A `design_change.projected` event permits PdM to model the forward reliability effect of a proposed change, which is what converts a redesign case from an assertion about cost into an assertion about readiness. **It must be strictly segregated from operational predictions.**

04 §4's Phase 3 question — *"How `design_change.projected` scenarios are represented without contaminating operational predictions"* — is answered here **from the producer side**. Document 05 records no separate finding on this contamination path; the requirement rests on 04 §10's sentence and 04 §4's open question, which is why the producer-side mechanism is made structural rather than procedural.

### 7.1 A separate aggregate on a separate topic

```sql
CREATE TABLE design_advisory.design_scenario (
    scenario_id       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    niin              text NOT NULL REFERENCES design_advisory.part_ref(niin),
    candidate_id      uuid NOT NULL REFERENCES design_advisory.redesign_candidate(candidate_id),
    case_id           uuid REFERENCES design_advisory.redesign_case(case_id),

    -- Single-valued enum, deliberately.  A field that can only say
    -- 'counterfactual_projection' can never be absent, defaulted, or made to
    -- mean 'actual' by a future value.  If a second scenario kind is ever
    -- needed it is a schema change with a review, not a new enum label.
    scenario_kind     text NOT NULL DEFAULT 'counterfactual_projection'
                          CHECK (scenario_kind = 'counterfactual_projection'),
    hypothetical      boolean NOT NULL DEFAULT true CHECK (hypothetical),

    -- A HYPOTHETICAL configuration reference, namespaced so it is structurally
    -- un-joinable to a real baseline_id.  See §7.2.
    scenario_baseline_ref text NOT NULL
        CHECK (scenario_baseline_ref ~ '^scenario:[0-9a-f-]{36}$'),
    -- Provenance: the REAL baseline the projection was computed against.
    -- Distinctly named so it cannot be read as the projection's own baseline.
    computed_against_baseline_id    uuid   NOT NULL,
    computed_against_baseline_epoch bigint NOT NULL,

    projected_reliability_effect jsonb NOT NULL,
    projection_method  text NOT NULL,
    projection_assumptions jsonb NOT NULL CHECK (jsonb_array_length(projection_assumptions) > 0),
    evidence_basis     jsonb NOT NULL,     -- dossier / snapshot / citation refs

    created_at        timestamptz NOT NULL DEFAULT now(),
    withdrawn_at      timestamptz,
    classification    jsonb NOT NULL
);
```

Topic: `fathom.design-advisory.design_change.v1` — **its own topic**, distinct from `fathom.design-advisory.redesign_case.v1`. Partition key `niin`; compaction key `scenario_id`. A consumer subscribing to redesign cases does not receive projections, and vice versa; a consumer wanting projections must subscribe to a topic whose name says what it carries.

### 7.2 Five mechanisms, and what each one blocks

| # | Mechanism | The contamination it makes impossible |
|---|---|---|
| **M1** | **Separate topic, separate aggregate, separate table** | A projection cannot arrive on the path a consumer reads for actual state. Handler code cannot fall through from one to the other |
| **M2** | **`scenario_kind` is a single-valued enum and `hypothetical` is a `CHECK`-forced `true`** | The tag cannot be absent, cannot be defaulted to something else, and cannot be flipped. There is no representable payload of this type that is not marked hypothetical |
| **M3** | **`scenario_baseline_ref` is namespaced `scenario:<uuid>` and is not a `baseline_id`** | **The strongest of the five.** A projection's configuration reference cannot be joined to a real configuration baseline, because it is not in the identifier space of one. A consumer that tries to resolve it against the Registry gets nothing — a loud failure, not a silent match. 03 §6 summarises this payload as carrying *"effective configuration"*; that is realised as `projected_configuration_delta` plus this namespaced reference, and **never** as a real `baseline_id`. §16 records the interpretation |
| **M4** | **`scope = niin`; `subject` carries only `niin`.** Never `installed_item_id`, never `asset_id` | A projection **cannot name a physical item**, so it cannot be joined onto an operational prediction row, which is keyed on `installed_item_id` (03 §7.1). The join that would produce a contaminated per-item prediction has no key to join on. Asserted by an event test (T-SEG-1) |
| **M5** | **Envelope `baseline_epoch` carries the epoch the projection was computed against** | A projection computed against a superseded baseline is *detectable as stale* by the ordinary antecedent rule (03 §5.4), so PdM can discard it rather than modelling a change against configuration that no longer exists. This mechanism deliberately *uses* the epoch machinery for staleness while M3 keeps it away from identity |

M3 and M4 together are what make the segregation structural. Even a defective consumer that ignored `scenario_kind` entirely could not produce a per-item operational prediction from this payload, because the payload contains no installed item and no real baseline.

### 7.3 The payload

```
DesignChangeProjected {
  scenario_id
  scenario_kind                  # const "counterfactual_projection"
  hypothetical                   # const true
  niin
  scenario_baseline_ref          # "scenario:<uuid>" — NOT a baseline_id
  projected_configuration_delta {          # 03 §6's "effective configuration"
    replaces_niin, introduces_niin?, interface_changes[], artifact_revisions[]
  }
  projected_reliability_effect {
    metric                       # mtbf_days | failure_rate | mdt_days | ao
    baseline_value, projected_value, direction
    horizon_days
    basis                        # how the projection was derived
    uncertainty                  # or explicit null; never an unqualified point figure
  }
  projection_method, projection_assumptions[]
  evidence_basis { dossier_id, impact_snapshot_id, causal_citation_ids[] }
  case_id?, candidate_id
  computed_against_baseline_id, computed_against_baseline_epoch
  classification
}
```

`projected_reliability_effect.metric` uses the Navy's own reliability quantities per 07 §5.5 — `Ao = Uptime / (Uptime + Downtime)`, `MTBF = 1 / (Failures / (30.44 × 0.667 × Population))`, `T(pf) = MTBF / (MTBF + MDT)`, with `0.667` the documented sea-going operating-tempo approximation. 07 §5.5 notes that using these *"rather than generic reliability mathematics is a cheap, high-credibility choice"*, and it makes a projected improvement directly comparable to the Navy's own figures.

`uncertainty` is required to be present-or-explicitly-null. A projected reliability improvement stated as a bare point value, in a document whose purpose is to justify funding, is the single most misreadable figure this sub-application produces.

### 7.4 The reciprocal obligation on PdM — binding DA→PDM-1

`docs/build/22-pdm.md` does not exist at the time of writing (§0.2). The following is stated as a **required consumer obligation** to be reflected there, and is the answer to 04 §4's Phase 3 question from the consumer side:

> **DA→PDM-1.** On consuming `design_change.projected`, PdM must:
> 1. write results into a **scenario-scoped store**, keyed on `scenario_id`, never into the operational prediction store;
> 2. **never** emit a `FailurePrediction` on `fathom.pdm.prediction.v1` whose `scoring_run_id` derives from a scenario input;
> 3. **never** treat the event as an invalidation or re-scoring trigger for operational predictions — the invalidation triggers remain `configuration.baseline_changed` and tier reassignment (03 §6, `[D36]`);
> 4. discard or re-derive a scenario result once `computed_against_baseline_epoch` is superseded (M5);
> 5. present scenario output only in explicitly forward-looking surfaces, per 04 §4's *"forward-looking scenarios"* framing.

**Design Advisory contributes the consumer-driven test that guards the other direction.** Per 03 §10, consumer-driven tests are contributed by a consumer into a producer's suite. Design Advisory consumes `prediction.updated` and `prediction.invalidated`, so it contributes into `packages/contracts/conformance/pdm/`:

> **`test_no_scenario_reference_on_operational_predictions`** — no event on `fathom.pdm.prediction.v1` carries a `scenario_id`, a `scenario_baseline_ref`, or a `baseline_id` matching `^scenario:`. A conformant PdM — program-built or substituted — fails its own suite if a projection leaks into the operational prediction stream.

That test is the one enforceable half of DA→PDM-1 available from this side, and it happens to guard the exact failure mode that matters: not that PdM models scenarios wrongly, but that a scenario result reaches consumers as an operational prediction.

### 7.5 Belt and braces — the inbound filter

Design Advisory's own `prediction` read model **rejects any prediction carrying a scenario reference**, logs it at `error`, and increments `fathom_scenario_leak_detected_total`. Design Advisory is the producer of projections and a consumer of predictions, so it is the one place in the system positioned to detect the loop closing. Discarding silently would hide a real defect; the counter is an alerting condition.

This also closes the loop on **D21** from this direction: a projection cannot return through PdM into a dossier's evidence, because the dossier's field-failure and citation sources are the maintenance and causal read models, and the prediction read model — which is used for population context only — refuses scenario-derived rows. See DO-NOT-DA-6.

---

## 8. Causal-finding evidence-strength passthrough

The rule this section exists to make unbreakable:

> **R-PASSTHROUGH.** A `FailureDossier` citing a Failure Intelligence hypothesis carries that hypothesis's **original structured evidence-strength value**, byte-for-byte as Failure Intelligence adjudicated and published it. It never carries a locally-derived strength, never a prose paraphrase in place of the structured object, never a value combined across citations, and never a rendering that implies more certainty than the original.

### 8.1 Why this is the highest-stakes rule in the document

04 §9's framing, which this sub-application is the principal consumer of:

> **Outputs are adjudicated hypotheses, not automated conclusions.** … Causal inference from observational data, without designed interventions, yields **hypotheses of varying strength — not established causes**. … **Presenting algorithmically derived causes as established fact to a design authority would be both wrong and, on first contradiction, fatal to the program's credibility.**

Note the object of that sentence: *to a design authority*. **This sub-application is the path by which a causal finding reaches a design authority.** It is the specific mechanism 04 §9 is warning about. And 04 §9 adds that *"Design Advisory building a business case"* makes different decisions at different strength levels and *"can only do so if strength is expressed consistently."*

The failure mode is not malice; it is ordinary summarisation. A structured strength object saying *"3 independent observations across 2 hulls of 1 class, method: comparative population analysis, unaddressed confounders: [treatment assignment by the model under test], adjudication: published-weak"* becomes, in a business-case narrative, *"analysis has identified the cause of these failures."* Every word of that is a defensible-looking summary and the whole is false. One reviewer with access to the original finding ends the program's credibility on causal analysis.

### 8.2 The mechanism — four properties, each independently sufficient to catch a violation

**(1) Verbatim carry with a digest.** `dossier_causal_citation.evidence_strength` is `jsonb NOT NULL`, stored exactly as received on `causal_finding.published`. `evidence_strength_digest` is SHA-256 over its **canonical JSON** — the same canonicalisation `packages/canonical-schemas` uses for byte-stable serialization (doc 10 §4.1). The invariant:

```
digest(citation.evidence_strength) == citation.evidence_strength_digest
   ∧  citation.evidence_strength_digest == digest(source_finding.evidence_strength)
```

**This is enforceable today, without knowing the scale.** It requires no ordering over strength values, no interpretation of the object, and no dependency on document 25's contents. Any mutation — a dropped `confounders_unaddressed` entry, a rounded observation count, a changed adjudication label — breaks the digest.

```python
# packages/py-common/src/fathom_py_common/passthrough.py
def carry_evidence_strength(finding: CausalFindingPublished) -> CarriedStrength:
    """Capture an evidence-strength object for citation.  R-PASSTHROUGH.

    The object is OPAQUE here.  This function does not parse it, rank it,
    threshold it, or normalise it -- it canonicalises and digests it.  That is
    deliberate: any transformation is a place a value could change, and the
    whole point is that none can.
    """
    canonical = canonical_json(finding.evidence_strength)   # doc 10 §4.1
    return CarriedStrength(
        evidence_strength=finding.evidence_strength,
        evidence_strength_schema_version=finding.evidence_strength_schema_version,
        evidence_strength_digest=sha256(canonical).hexdigest(),
        source_event_id=finding.event_id,
    )
```

Shared rather than local, so all nine services capture it identically and no service can implement a "helpful" variant.

**(2) No column can express a local strength.** Enumerated in §3.3.1 and asserted by a schema test: no `local_strength`, `strength_rank`, `strength_score`, `strength_summary`, `strength_prose`, `combined_strength`, `consolidated_strength`, `is_strong`, or `meets_threshold`. A rule enforced by the absence of a place to write the violation cannot be violated by a well-meaning implementer under deadline.

**(3) Prose is derived, never substituted.** A human-readable rendering is legitimate — a design engineer should not have to read raw JSON. But:

- The rendering is produced by **one shared deterministic renderer** in `packages/py-common`, from the structured object, at read time. It is never persisted as the citation's representation.
- Every API response and every export containing a citation **contains the structured object**. The renderer's output is an *additional* field, never a replacement. A response schema in which `evidence_strength` is optional is a contract-test failure.
- The renderer is **information-preserving over the fields that bound certainty**: observation count, hull count, class count, method, unaddressed confounders, and adjudication state all appear in its output. It has no code path that omits `confounders_unaddressed`, and a golden-vector test asserts that a strength object with unaddressed confounders never renders without them.
- The renderer emits **no causal verb**. Its vocabulary is fixed: *"hypothesis, adjudicated <state> by Failure Intelligence"*, never *"cause"*, *"caused by"*, *"root cause"*, or *"determined"*. This is 09 DO-NOT-20's rule (*"do not render `contributing_factors` in causal language"*) applied to the sub-application where causal language is most tempting — because here the finding genuinely *is* a causal hypothesis, and the licence that grants is exactly one word wide: it may be called a hypothesis.

**(4) No aggregation across citations.** 04 §9 notes that *"agreement across methods is itself evidence"* — and that judgment belongs to **Failure Intelligence's strength scorer**, which sees the whole method portfolio. This sub-application holds citations side by side and never combines them. Three weak hypotheses pointing the same way do not become one moderate hypothesis in a dossier. If they should, Failure Intelligence says so in a finding of its own, with its own adjudication, and *that* is what gets cited.

### 8.3 Ranking, when document 25 lands

`min_strength` appears on Failure Intelligence's own `GET /hypotheses?…&min_strength=` (04 §9), so an ordering exists on the strength scale. When document 25 fixes it:

- The ordering is expressed as **one pure function in `packages/canonical-schemas`**, over the structured object, owned by the schema package and not by any consumer.
- This service may **call** it — to sort citations for display, or to let a design authority filter — and may **never** persist its output as a citation field.
- The strengthened invariant becomes `rank(cited) == rank(source)` **in addition to** digest equality. Digest equality remains primary because it catches changes that leave the rank unmoved, which is the subtler and more likely defect: dropping one unaddressed confounder from a five-item list rarely changes a coarse rank and materially changes what a reviewer concludes.

**Until then, digest equality is the whole enforcement, and it is sufficient.** This is why §0.2 states the dependency rather than waiting on it.

### 8.4 What a citation looks like on the wire

```json
{
  "citation_id": "…",
  "posture": "supporting",
  "hypothesis_id": "…", "hypothesis_version": 3,
  "adjudication_id": "…", "adjudication_state": "published",
  "adjudicated_by": "…", "adjudicated_at": "2026-05-14T09:12:00.000000+00:00",
  "source_event_id": "…",

  "evidence_strength": { "…verbatim structured object from failure-intel…" },
  "evidence_strength_schema_version": "1.0.0",
  "evidence_strength_digest": "9f2c…",
  "confounders_unaddressed": [
    { "confounder": "treatment assignment by the model under test",
      "handling": "not addressed", "reference": "05 §4.1 / D21" }
  ],
  "treatment_assignment_handling": { "…as received…" },

  "failure_mode": { "lineage_id": "…", "code": "BRD", "taxonomy_version": "1.1.0" },
  "attribution_confidence": 0.72,
  "attribution_agreement": "pma_only",

  "rendered_strength": "Hypothesis, adjudicated published by Failure Intelligence. …
                        1 unaddressed confounder: treatment assignment by the model
                        under test.",
  "rendered_by": "fathom-py-common/strength-renderer@1.0.0"
}
```

`rendered_strength` sits **beside** `evidence_strength`, never instead of it, and names its renderer version so a rendering can be reproduced or repudiated.

`attribution_agreement: "pma_only"` is carried through from doc 12 §9.1's crosswalk output. Doc 12 §9.2: *"`agreement` is an output column, not a filter. The caller receives the classification. Nothing upstream decides on their behalf."* A design authority reading that the observable signature and the maintainer's physical finding pointed **different directions** is receiving exactly the signal doc 12 §9.3 exists to preserve — and a business case that quietly resolved the disagreement would have destroyed it at the last possible moment.

---

## 9. API surface

Base path `/api/v1/design-advisory/`. Every operation declares `x-substitution` and `x-side-effects` through `packages/contracts`' `operation_extra(...)` decorator (doc 10 §5.1), which gates `x-agent-eligible` at import time.

### 9.1 Operations

| Operation | Sub. | Side effects | Agent | Notes |
|---|---|---|---|---|
| `GET /dossiers?niin=&changed_since=&limit=&cursor=` | required | `none` | ✔ | Change-feed read (03 §4, `[D5]`) |
| `GET /dossiers/{id}` | required | `none` | ✔ | Full dossier incl. verbatim citations |
| `POST /dossiers/assemble` | required | `none` | ✔ | §6.2. Writes snapshot + provenance only. **Body `{niin, candidate_id, as_of?}`** `[amendment, 42 §18 item 3]` |
| `GET /redesign-candidates?status=&min_priority=&niin=&changed_since=&limit=&cursor=` | required | `none` | ✔ | 04 §10 |
| `GET /redesign-candidates/{id}` | required | `none` | ✔ | |
| `POST /redesign-candidates/{id}/parametric-estimate` | required | `none` | ✔ | §5.1, stage 1. **Body `{}`** — all inputs are server-side against the candidate and its dossier `[amendment, 42 §18 item 3]` |
| `POST /redesign-candidates/{id}/evaluate-gate` | required | `none` | ✔ | §6.3. **Body `{dossier_id, impact_snapshot_id}`** — both `NOT NULL` on the `gate_decision` row this operation writes (§5.3), so both must arrive on the request `[amendment, 42 §18 item 3]` |
| `GET /redesign-candidates/{id}/gate-decisions` | internal | `none` | ✔ | Full append-only history |
| `GET /redesign-cases?niin=&status=&changed_since=&limit=&cursor=` | required | `none` | ✔ | |
| `GET /redesign-cases/{id}` | required | `none` | ✔ | 04 §10 |
| `POST /redesign-cases` | required | `state-changing` | ✗ | **[AMENDMENT — closes a BLOCKING gap, `42-redesign-case-builder.md` §18 item 1.]** Body `{candidate_id, dossier_id}`. Mints the `{id}` every downstream route on this aggregate presupposes and that nothing previously created. `case_status` fixed at `draft`, not caller-settable. Does **not** record a redesign decision — see the revised E2 below |
| `POST /redesign-cases/{id}/assemble` | required | `state-changing` | ✗ | §6.1 step 9 |
| `POST /redesign-cases/{id}/estimate` | required | `state-changing` | ✗ | 04 §10. **Gate-gated** (§5.5) |
| `GET /dependencies?niin=&depth=&relation=&as_of=&changed_since=&limit=&cursor=` | required | `none` | ✔ | 04 §10, neighbourhood |
| `GET /dependencies/{niin}/impact?max_depth=&as_of=&persist=` | required | `none` | ✔ | 04 §10, §4.5. Naming carve-out |
| `GET /impact-snapshots/{id}` | required | `none` | ✔ | Reproducibility of a cited traversal |
| `GET /cost-estimates/{id}` | required | `none` | ✔ | **[amendment, closes `30-gateway.md` §3.2's `redesign_case_detail` cost-estimate fragment, which had no operation to resolve `redesign_case.cost_estimate_id` by]** Method, assumptions, `is_lower_bound`, and the two-stage state |
| `GET /test-records?niin=&test_kind=&record_status=&changed_since=&limit=&cursor=` | required | `none` | ✔ | 04 §10 |
| `GET /test-records/{id}` | required | `none` | ✔ | |
| `GET /test-coverage?niin=` | required | `none` | ✔ | `test_coverage_v`, **absence rows included**. Naming carve-out (query projection) |
| `GET /design-scenarios?niin=&changed_since=&limit=&cursor=` | required | `none` | ✔ | §7 |
| `GET /design-scenarios/{id}` | required | `none` | ✔ | |
| `POST /design-scenarios` | required | `state-changing` | ✗ | Publishes `design_change.projected` |
| `POST /proposals` | required | **`proposal-only`** | ✔ | §6.4. `kind=redesign_case` only |
| `GET /proposals?status=&case_id=&changed_since=&limit=&cursor=` | required | `none` | ✔ | **`case_id` added** `[amendment, closes 52-practitioner-apps.md §13 correction 18]` — filters on `payload.case_id` (§6.2's `RedesignCaseProposalPayload`), this service's own domain object, not the gateway's opaque queue projection. Without it, a review surface reached by `case_id` (the practitioner app's Sheet 09, or the console's `redesign_case_detail` drill-down) has no way to find the live proposal it must adjudicate — `redesign_case.published_via_proposal_id` is set only *after* publication, which is exactly when adjudication is already over |
| `POST /proposals/{id}/claim` | required | `state-changing` | ✗ | 03 §7.2 rule 3 |
| `POST /proposals/{id}/adjudicate` | required | `state-changing` | ✗ | `If-Match` required; `design_authority` |
| `POST /test-records/bulk` | required | `state-changing` | ✗ | Bulk, idempotent, fenced (03 §4, `[D10/C7]`). `X-Backfill` honoured |
| `POST /dependencies/bulk` | required | `state-changing` | ✗ | Graph population from federation |
| Test-data ingest admin, graph administration, cost-model configuration, coverage-profile administration, traversal-policy administration | internal | `state-changing` | ✗ | 04 §10 |

**Naming carve-outs**, enumerated in the specification per 03 §4 `[C23]`: `dependencies/{niin}/impact` (query projection over a traversal, no collection semantics) and `test-coverage` (query projection over `test_coverage_v`).

### 9.2 Problem types

All `application/problem+json`, RFC 9457, `type` a stable `urn:` URI — never `https://`, per 09 DO-NOT-26 (no dereferenceable external URI in an air-gapped deployment).

| `type` | Status | Raised when |
|---|---|---|
| `urn:fathom:problem:design-advisory:unknown-niin` | 422 | Root NIIN absent from the read model (§4.5) |
| `urn:fathom:problem:design-advisory:gate-not-passed` | 409 | `dependency_rollup` requested without a passing gate (§5.5) |
| `urn:fathom:problem:design-advisory:gate-thresholds-unconfigured` | 503 | Gate evaluation attempted with unset thresholds (§5.4) |
| `urn:fathom:problem:design-advisory:read-model-stale` | 503 | Roll-up outside its `part_availability` staleness bound (§5.5) |
| `urn:fathom:problem:design-advisory:case-incomplete` | 422 | `assemble` with missing estimate, stance, limitations, or evidence gaps (§3.6) |
| `urn:fathom:problem:design-advisory:evidence-strength-mismatch` | 422 | A citation whose digest disagrees with its object (§8.2) |
| `urn:fathom:problem:design-advisory:authority-insufficient` | 403 | Adjudication by a principal lacking `design_authority`, or missing second signature |
| `urn:fathom:problem:design-advisory:baseline-superseded` | 409 | Re-validation at adjudication finds a superseded epoch (03 §7.2 rule 2) |
| `urn:fathom:problem:design-advisory:coverage-profile-missing` | 422 | Dossier assembly for a NIIN with no coverage profile — **absence cannot be established against nothing** |
| `urn:fathom:problem:design-advisory:depth-exceeded` | 422 | `max_depth` above the hard cap of 6 |

`coverage-profile-missing` deserves note: it is a **refusal to assemble** rather than a silent empty test section. Without a coverage profile the `LEFT JOIN` in §3.2.2 has nothing to left-join from, so "no expected tests" and "we do not know what was expected" would be indistinguishable — which is the exact defect §3.2 exists to prevent, reappearing one level up.

### 9.3 Cross-cutting

Per 09 §5, unchanged and not restated: `Idempotency-Key` on all unsafe methods and required on `state-changing` and `proposal-only`; `ETag`/`If-Match` on updatable resources and mandatory on proposal adjudication; `X-Correlation-Id` accepted, minted, echoed, propagated; `X-Classification` on every response with per-field redaction where levels mix; ABAC authorization enforced **in this service**; cursor pagination with no total count; RFC 3339 UTC timestamps throughout.

---

## 10. Events

### 10.1 Published

Topics: `fathom.design-advisory.<aggregate>.v1`. Partition key is the scope identifier — `niin` for all three domain events, since all are NIIN-scoped (03 §5.1). **Compaction key is the aggregate key, never the partition key** (`[D5]`): compacting on `niin` would collapse a part's entire case history to one record.

| Event | Topic | Partition key | Compaction key | Payload summary (03 §6) | Consumers |
|---|---|---|---|---|---|
| `redesign_candidate.created` | `…redesign_candidate.v1` | `niin` | `candidate_id` | NIIN, driver evidence, affected population, preliminary priority | `fleet-status`, `notification` |
| `redesign_case.published` | `…redesign_case.v1` | `niin` | `case_id` | NIIN, dependency impact, cost estimate, recommendation | `fleet-status`, `audit` |
| `design_change.projected` | `…design_change.v1` | `niin` | `scenario_id` | NIIN, projected reliability improvement, effective configuration | `pdm` |
| `proposal.created` / `.adjudicated` / `.expired` | `fathom.design-advisory.proposal.v1` | `proposal_id` | `proposal_id` | 03 §7.2 schema | `gateway`, `notification`, `audit`, self |

`redesign_case.published` carries `dependency_completeness` in full, not a scalar. A consumer receiving a case's cost estimate without the completeness of the graph it was rolled up over has the number and not its qualification, and `fleet-status` in particular must be able to present a redesign-driven readiness figure with its uncertainty intact.

**Envelope.** Full 03 §5.4 envelope on every event, including the complete `clock` block with all six `sync_quality` sub-fields. `producer = "design-advisory"` with version; **`producer_node = "enterprise"` always** (§0.1). `replay: true` handled idempotently with no operator-visible alert.

### 10.2 Consumed — enumerated, no wildcards

Exactly 03 §6's declared set for `design-advisory`:

| Event | Producer | Used for |
|---|---|---|
| `causal_finding.published` | `failure-intel` | Citations, **verbatim strength capture** (§8.2). Candidate identification |
| `failure_mode.attributed` | `failure-intel` | Attribution and taxonomy binding on dossiers |
| `maintenance_action.recorded` | `maintenance` | Field failure history; `failure_indicator`, `triggering_driver`, `triggering_prediction_id`, `policy_version` (`[D1, D21]`) |
| `installed_item.removed` | `registry` | Removals with failure indicator and disposition |
| `prediction.updated` | `pdm` | **Population and consequence context only.** Never evidence for a causal claim (DO-NOT-DA-6) |
| `prediction.invalidated` | `pdm` | Marks context stale; drops scenario-tainted rows (§7.5) |
| `part_availability.changed` | `supply` | Cost inputs: unit cost, `lead_time`, `condition_code`, interchangeable group (`[D6, D24]`) |

`src/fathom_design_advisory/events/catalog.py`'s `PUBLISHES`/`CONSUMES` frozensets must **equal** `helm/values.yaml`'s `events.publishes`/`events.consumes` and **equal** 03 §6's rows for this slug. `python tools/check_event_catalog.py` exits 0 (09 §8.6).

**One conflict, flagged rather than silently resolved.** `docs/build/11-outbox-sync-library.md` §9 introduces `installed_item.identity_resolved` on `fathom.registry.installed_item.v1` and names `design-advisory` among its consumers, but that event is **not in 03 §6's catalog**. Subscribing to it would fail `check_event_catalog.py`; not subscribing means a dossier can cite a provisional installed-item identity later superseded. **Interim position:** do not subscribe; dossier field-failure rows carry `installed_item_id` as received, and a superseded provisional identity is reconciled at the next dossier assembly via `changed_since` on the Registry. Recorded as §16 correction #4, requiring a 03 §6 catalog addition.

### 10.3 Consumer-driven tests this service contributes

Per 03 §10, into each producer's suite:

| Into | Assertion |
|---|---|
| `failure-intel` | `causal_finding.published` carries a structured `evidence_strength`, its `schema_version`, `confounders_unaddressed`, `treatment_assignment_handling`, and the adjudication identity — **the inputs R-PASSTHROUGH needs to exist at all** |
| `pdm` | No operational `prediction.updated` carries a `scenario_id`, `scenario_baseline_ref`, or `baseline_id` matching `^scenario:` (§7.4) |
| `maintenance` | `maintenance_action.recorded` carries `failure_indicator`, `triggering_driver`, `triggering_prediction_id`, `policy_version` (`[D1, D21]`) |
| `registry` | `installed_item.removed` carries disposition and failure indicator |
| `supply` | `part_availability.changed` carries `lead_time` and `condition_code` (`[D24]`) |

---

## 11. Read models, staleness, and conflict policy

| Read model | Built from | Staleness bound | Consumer of the bound |
|---|---|---|---|
| `rm_causal_finding` | `causal_finding.published`, `failure_mode.attributed` | Declared; dossier assembly records the watermark rather than refusing | §3.3 `read_model_watermarks` |
| `rm_field_failure` | `maintenance_action.recorded`, `installed_item.removed` | Declared; recorded, not refused | |
| `rm_part_availability` | `part_availability.changed` | **Refuses** outside bound | Stage-2 roll-up (§5.5) |
| `rm_criticality` | `criticality_tier.assigned` (via `prediction.updated` scope) | Declared | Priority scoring (§3.5.1) |
| `rm_prediction_context` | `prediction.updated`, `prediction.invalidated` | Declared | **Scenario-filtered** (§7.5) |
| `rm_part_ref` | Registry/Reference Data `changed_since` reads | Declared | NIIN and `equipment_family` resolution |

**Rebuild is from `changed_since` reads, never from the event bus** (`[D5]`). Lag on `/readyz` and `/metrics`; `fathom_staleness_refusals_total` incremented on refusal.

**The asymmetry is deliberate.** Only the cost roll-up refuses. Dossier assembly against a slightly-stale causal read model produces an *honest* artefact — it records the watermark, and a design authority can see it. Costing against stale part prices produces a *wrong number* with no marker. Refusal belongs where staleness is invisible in the output.

**Conflict policy.** No aggregate is edge-writable. 03 §11's default — **enterprise-authoritative, not edge-writable** — is accepted explicitly for every aggregate, and stated in the README (03 §15 obligation 16, `[C20]`). Consistent with doc 11 §1.2, which places `design-advisory` in the no-edge-profile group.

**Antecedent rule.** Events whose `baseline_epoch` is ahead of the local configuration read model are **blocked** until the antecedent applies (`[D3, D4]`), via `packages/py-sync`'s epoch fencing. Ordering and dedup on `(producer, producer_node, monotonic_seq)` or the HLC — never `source_time` (`[D29]`).

---

## 12. Deployment

Per 09 §4.3–4.4 and §2.4, unchanged. Sub-application specifics:

| Concern | Value |
|---|---|
| Namespace | `fathom-sustainment` |
| Database | `fathom-design-advisory-pg` (CloudNativePG, in `fathom-data`) |
| Object storage | MinIO bucket `fathom-design-advisory` — test artefacts, case exports |
| Scaling | HPA on request rate; **KEDA on consumer lag** for the event worker (09 §2.4) |
| Edge profile | None. Outbox, inbox, clock discipline still mandatory (doc 11 §1.2) |
| Domino | Cost-model development and any learned parametric component. Practitioner case review as a Domino App under `apps/practitioner`, base path from `DOMINO_RUN_HOST_PATH` |
| Migrations | Alembic, forward-only, `pre-upgrade,pre-install` Helm hook, `backoffLimit: 0` |

**NetworkPolicy egress — the complete sanctioned peer set.** The helm-unittest assertion requires the rendered egress peer set to **equal** `values.networkPolicy.egress` exactly (09 §4.2).

| Peer | Why |
|---|---|
| `fathom-design-advisory-pg` | Its own database. No other |
| Redpanda | Outbox relay and inbox consumer |
| `auth` | Token introspection, ABAC attributes |
| `audit` | Provenance and tool-invocation records |
| `reference-data` | Taxonomy and `equipment_family`, read-through cache keyed on `taxonomy_version` (doc 12 DO-NOT-1) |
| MinIO | Test artefacts and case exports |
| *(ingress only)* `gateway` | User-facing composition and agent tool calls |

**No peer to `failure-intel`, `pdm`, `maintenance`, `supply`, or `registry`** — every one of those is an event-fed read model (03 principle 2, 09 DO-NOT-2). Drill-down from a citation to Failure Intelligence's evidence is composed by the gateway. **This is what makes R-PASSTHROUGH enforceable by digest**: the strength object is captured once from the event and never re-fetched, so there is no live call whose response could differ from what was cited.

If the parametric cost model is served from a Domino Endpoint, that call is **proxied** through a Sustainment Plane service attaching caller identity (03 §8.3, 09 DO-NOT rules), config-gated, one declared cross-namespace rule, with the deterministic in-service path as fallback (§2).

---

## 13. Testing

Everything in 09 §8.5 applies. Below are the tests specific to this sub-application. **The first two groups are mandatory and named in the task that commissioned this document**; each is written so that it fails on the defect rather than on a proxy for it.

### 13.1 Evidence-strength passthrough — the anti-upgrade suite

| ID | Test | Asserts |
|---|---|---|
| **T-PASS-1** | **A low-evidence-strength causal finding cannot be silently upgraded when cited in a dossier.** Publish a `causal_finding.published` whose `evidence_strength` is at the weakest end of its scale, with two `confounders_unaddressed` entries and `adjudication_state = "published"`. Assemble a dossier. Then: (a) `GET /dossiers/{id}` returns `evidence_strength` **byte-identical** to the published object under canonical JSON; (b) `evidence_strength_digest` equals the digest computed from the source event; (c) the response contains **no** field expressing a strength assessment other than the carried object; (d) both `confounders_unaddressed` entries are present; (e) a direct repository write attempting to store a mutated object — one confounder removed, observation count incremented — is rejected by the digest check with `evidence-strength-mismatch`; (f) the same, with the object unchanged but the digest recomputed to match the mutation, is *also* rejected, because the digest is verified against the **source event**, not against the stored object alone | R-PASSTHROUGH (§8.2 property 1) |
| **T-PASS-2** | Prose cannot replace the object. The response schema makes `evidence_strength` **required**; a response containing `rendered_strength` without it fails schema validation. The renderer is deterministic across 40 golden strength objects; every rendering containing a non-empty `confounders_unaddressed` mentions each one; **no** rendering contains `cause`, `caused`, `root cause`, `determined`, `proves`, `confirms`, or `establishes` | §8.2 property 3; 09 DO-NOT-20 |
| **T-PASS-3** | No aggregation. Cite three weak hypotheses in one dossier; assert the response contains three independent citations, each with its own digest, and **no** combined, consolidated, or maximum strength anywhere | §8.2 property 4 |
| **T-PASS-4** | **Schema test:** introspect `dossier_causal_citation`'s columns and assert none matches `%strength%` other than `evidence_strength`, `evidence_strength_schema_version`, `evidence_strength_digest`; and none matches `is_strong`, `meets_threshold`, `combined_%`, `consolidated_%`, `%_rank`, `%_score`. **A future migration adding a place to author a local strength fails this test** | §8.2 property 2 |
| **T-PASS-5** | `contra` citations never satisfy the gate's G5, and never appear in a supporting-evidence projection | §3.3.1, §5.3 |
| **T-PASS-6** | The gate does not threshold on strength: two candidates identical but for strength — one weakest, one strongest — both pass G5 given one published supporting citation each | §5.3 rationale |

**Why T-PASS-1(f) is the test that matters.** Any implementation will pass (a)–(e) with a naive digest-on-write. Verifying against the source event is what catches the case where a service recomputes the digest over already-mutated content — which is exactly what a well-meaning "normalise then hash" refactor produces.

### 13.2 Dependency completeness

| ID | Test | Asserts |
|---|---|---|
| **T-COMPLETE-1** | **The dependency-completeness test.** Seed a graph with an exactly known verified/unverified split: 10 edges from `cdmd_oa_federation` with `verified_by`/`verified_at`, 6 from `inferred_cooccurrence`, 4 from `unverified_import`. Traverse. Assert `edges_touched = 20`, `edges_verified = 10`, `completeness_ratio = 0.5000` exactly, `unverified_by_source_kind = {inferred_cooccurrence: 6, unverified_import: 4}`, `is_bounded_below = true` | §4.4 |
| **T-COMPLETE-2** | Stamping `verified_by`/`verified_at` on the 6 `inferred_cooccurrence` and 4 `unverified_import` edges leaves `completeness_ratio` at `0.5000`. **Completeness cannot be improved by asserting confidence** | §3.4.2 anti-gaming |
| **T-COMPLETE-3** | A symmetric `interfaces_with` edge traversed in both orientations counts **once**: `edges_touched` increments by 1, not 2 | §4.3 property 1 |
| **T-COMPLETE-4** | Depth truncation. Seed a 5-deep chain, traverse at `max_depth = 3`: `nodes_truncated_at_depth > 0`, `truncated_at_depth` names the frontier NIINs, and `is_bounded_below = true` **even when `completeness_ratio = 1.0000`** | §4.3 property 8 |
| **T-COMPLETE-5** | Cycle safety. A→B→C→A returns finite results; the same NIIN reachable by two distinct paths appears with both, and neither path is dropped | §4.3 property 5 |
| **T-COMPLETE-6** | Artifacts are leaves. Two unrelated NIINs sharing a `technical_publication`: traversing from one does **not** reach the other | §4.3 property 4 |
| **T-COMPLETE-7** | `completeness_ratio` is `NULL`, not `1.0`, when `edges_touched = 0`; the API renders an isolated NIIN as an explicit empty impact set with `edges_touched: 0`, never a successful-looking total | §4.2 |
| **T-COMPLETE-8** | A `RedesignCase` cannot be inserted with a `dependency_completeness` whose `edges_touched` disagrees with its `impact_snapshot_id`; and cannot be inserted with a NULL completeness at all | §3.6 |
| **T-COMPLETE-9** | `is_lower_bound` on a `dependency_rollup` estimate is `true` iff `coverage_ratio < 1.0`, enforced by the constraint, tested from both sides | §3.7 |

### 13.3 Test-data absence

| ID | Asserts |
|---|---|
| **T-ABSENCE-1** | A NIIN with a 5-entry coverage profile and **zero** `test_record` rows yields **5** `absent_unknown` coverage rows with `materialised_absence = true` — never an empty list |
| **T-ABSENCE-2** | `qualification_credit` is `false` for every absence status including `absent_not_required`; `true` only for `present` + `pass` |
| **T-ABSENCE-3** | `outcome_only_when_present`, `absence_carries_a_basis`, and `absence_holds_no_artifact` each reject their violating insert |
| **T-ABSENCE-4** | Gate condition G4 fails when any `absent_unknown` row remains, and **passes** when every row is an established absence — absence does not bar qualification, unassessed coverage does |
| **T-ABSENCE-5** | An `absent_not_located` qualification test the redesign requires produces a re-test cost line; the same test `present`/`pass` does not |
| **T-ABSENCE-6** | Dossier assembly for a NIIN with no coverage profile returns `coverage-profile-missing` (422), not an empty test section |
| **T-ABSENCE-7** | An ambiguous EIC→NIIN resolution propagates `ambiguous: true` into `test_attribution_ambiguity` on the case |

### 13.4 The costing gate

| ID | Asserts |
|---|---|
| **T-GATE-1** | `POST /redesign-cases/{id}/estimate` with `method=dependency_rollup` and no passing gate returns **409** `gate-not-passed` with `failed_conditions` naming the conditions. No estimate row is written |
| **T-GATE-2** | The service **fails to start** with any gate threshold unset; the message names §5.4. No default is substituted |
| **T-GATE-3** | Every `gate_decision` row carries `thresholds_in_force` and `gate_policy_version`; a threshold change does not alter a historical decision's recorded values |
| **T-GATE-4** | Re-evaluation supersedes rather than overwrites; `gd_one_live_per_candidate` permits exactly one live decision |
| **T-GATE-5** | `method=parametric` is never gated |
| **T-GATE-6** | Roll-up refuses outside the `part_availability` staleness bound with **503** and increments `fathom_staleness_refusals_total`; parametric does not refuse |

### 13.5 Decision-package boundary

| ID | Asserts |
|---|---|
| **T-NODECISION-1** | Enumerate every route in the generated `openapi.json`; **none** matches `/(approve|authorize|decide|direct|implement|execute)/` outside the proposal-adjudication path. `case_status` has no `approved` value. A `PATCH` carrying `case_status: "approved"` returns 422 |
| **T-NODECISION-2** | `published` is unreachable without `published_via_proposal_id`; a direct repository write attempting it violates the constraint |
| **T-NODECISION-3** | `assemble` is rejected with `case-incomplete` when `recommendation_limitations` or `recommendation_evidence_gaps` is empty |
| **T-NODECISION-4** | `recommendation_stance` rejects any value outside the four non-directive values |
| **T-SIDEEFFECT-1** | **Lint + integration:** every operation declared `x-side-effects: none` writes only `failure_dossier`(+children), `impact_snapshot`, `gate_decision`, and emits **no** outbox row. Asserted by running each `none` operation against a real database and diffing the outbox and every domain table |
| **T-AUTH-1** | A `redesign_case` proposal is created with `authority_class = "design_authority"` at **every** blast radius; a caller-supplied value is ignored |
| **T-AUTH-2** | `requires_dual_control` is forced `true` at `class` **and** `fleet`; adjudication with one signature at those scopes returns 403 `authority-insufficient` |
| **T-AUTH-3** | Adjudication by a principal without `design_authority` returns 403 at every blast radius, including `item` |
| **T-AUTH-4** | Re-validation at adjudication rejects a superseded `baseline_epoch` (409) and an elapsed `valid_until` |

### 13.6 Scenario segregation

| ID | Asserts |
|---|---|
| **T-SEG-1** | **Event test.** `design_change.projected` publishes to `fathom.design-advisory.design_change.v1`; envelope `scope = "niin"` and `subject` contains **only** `niin`. A payload carrying `installed_item_id`, `asset_id`, or a `baseline_id` fails schema validation |
| **T-SEG-2** | `scenario_kind` accepts only `counterfactual_projection`; `hypothetical` cannot be `false`; `scenario_baseline_ref` rejects anything not matching `^scenario:<uuid>$` |
| **T-SEG-3** | `redesign_case.published` and `design_change.projected` never share a topic; a `redesign_case` subscriber receives no projections |
| **T-SEG-4** | The inbound prediction read model rejects a prediction carrying a scenario reference, logs at `error`, and increments `fathom_scenario_leak_detected_total` |
| **T-SEG-5** | Envelope `baseline_epoch` on a projection equals `computed_against_baseline_epoch`, so staleness is detectable by the antecedent rule |
| **T-ENV-1** | `producer_node == "enterprise"` on every published event |

### 13.7 The shared categories

Per 09 §8.5 and 03 §10, in `packages/contracts/conformance/design-advisory/`: contract tests over every `x-substitution: required` operation including errors, pagination, idempotency, and concurrency; event tests for envelopes, keys, and within-partition ordering; **fault-injection tests** interrupting mid-operation and asserting no state change without its event; the consumer-driven tests of §10.3 contributed outward; manifest tests for `design-advisory-redesign-case.v1`; a deterministic synthetic reference dataset.

**Synthetic data gap.** `docs/build/13-synthetic-data-generator.md` generates **no** test records, coverage profiles, or dependency edges — it mentions this sub-application only once, in the agent-count row. The reference dataset for this service must therefore be authored here, in `packages/contracts/conformance/design-advisory/dataset/`, seeded deterministically, and 13 needs an addition. §16 correction #5.

Also: `schemathesis` against the committed `openapi.json`; `helm lint`, `helm template | kubeconform --strict`, `helm unittest` including the NetworkPolicy equality assertion; `pytest tests/unit tests/integration tests/contract tests/conformance` green with the 09 §7.4 coverage floor.

---

## 14. Explicit DO-NOT list

09 §9's thirty-two items apply unchanged. These are additional and specific to this sub-application. Each cites the framing that makes it a defect rather than a preference.

**DA-1 — Do not produce a redesign decision. Ever, by any route.**
No operation, no state, no event, no field, and no agent output may express that a redesign is approved, authorized, directed, or scheduled. The output is a **decision package**. 04 §10: *"Redesign is an acquisition action with programmatic, contractual, and airworthiness or seaworthiness implications far exceeding this system's scope. The sub-application assembles evidence and estimates to a standard that a design engineer can evaluate and defend, and stops there."* Enforced by E1–E4 (§1.2) and T-NODECISION-1..4. **This is the core framing of the sub-application; every other rule here is downstream of it.**

**DA-2 — Do not re-state a causal finding's evidence strength as anything other than what Failure Intelligence adjudicated.**
Not a local score. Not a rank. Not a threshold boolean. Not a prose paraphrase *in place of* the structured object. Not a strength combined across citations. 04 §9: causal inference over observational data yields *"hypotheses of varying strength — not established causes"*, and *"presenting algorithmically derived causes as established fact to a design authority would be both wrong and, on first contradiction, fatal to the program's credibility."* **This sub-application is the path to the design authority.** §8; T-PASS-1..6.

**DA-3 — Do not use causal language for a causal finding beyond calling it a hypothesis.**
The permitted vocabulary is *"hypothesis, adjudicated <state> by Failure Intelligence"*. Not *cause*, *root cause*, *caused by*, *determined*, *proves*, *confirms*, or *establishes* — in a rendered strength, a case narrative, an agent response, or a UI label. 09 DO-NOT-20 (`[D23]`) applied where the temptation is strongest. §8.2 property 3.

**DA-4 — Do not let a forward-looking projection reach the operational prediction path.**
Separate topic, single-valued scenario tag, namespaced non-joinable scenario baseline, NIIN-only subject, inbound scenario filter. 04 §10: *"It must be strictly segregated from operational predictions."* §7; T-SEG-1..5. And do not "simplify" the scenario baseline into a real `baseline_id` for the convenience of a consumer's join — **the un-joinability is the mechanism.**

**DA-5 — Do not treat missing test data as absence of concern.**
No empty test section, no `outcome` on an absence row, no qualification credit for `absent_not_required`, no `LEFT JOIN` from records instead of from the coverage profile. 04 §10: *"The design assumes partial coverage and represents absence explicitly rather than treating missing test data as absence of concern."* §3.2; T-ABSENCE-1..7.

**DA-6 — Do not use a prediction as evidence for a causal claim, and do not close the D21 loop here.**
`prediction.updated` is consumed for population and consequence context only. This mirrors 04 §9's restriction on Failure Intelligence — *"It is never used as evidence for a causal finding"* — and matters more here, because a business case citing a model's own output as evidence for the phenomenon the model was trained on is circular in a way that survives casual review. **05 D21**; §1.3, §7.5.

**DA-7 — Do not report dependency completeness as total, and do not omit it.**
`dependency_completeness` is `NOT NULL` on every case; `is_bounded_below` is set whenever the ratio is below 1.0 **or** the traversal truncated; a `dependency_rollup` estimate over an incomplete graph is recorded as a **lower bound**. 04 §10: *"dependency completeness is itself reported so a reader knows how much of the impact is known."* §3.6, §3.7, §4.4.

**DA-8 — Do not improve completeness by asserting confidence.**
`inferred_cooccurrence` and `unverified_import` can never count as verified, whatever `verified_by` says. A statistical co-replacement pattern is a hypothesis about a dependency, not a dependency. §3.4.2; T-COMPLETE-2.

**DA-9 — Do not produce a detailed dependency roll-up for a candidate that has not passed the gate.**
Enforced at the API boundary with 409, not in the estimator, and not by convention. 04 §10: *"Producing detailed estimates for every candidate is wasted effort, and producing only parametric estimates yields business cases that do not withstand review."* §5.5.

**DA-10 — Do not put an evidence-strength threshold in the costing gate.**
The gate decides where to spend estimation effort. Whether a given strength justifies a redesign is a **design-authority judgment**, and moving it into a configuration constant both violates DA-2 and relocates a human decision into a settings file. §5.3 (G5).

**DA-11 — Do not invent Navy test or qualification data schemas.**
Document 07 covers no test/qualification data system. `test_kind`, `test_regime`, and condition vocabularies are program-defined, namespaced `FATHOM-TK-###`, and carry `code_authority`. 09 DO-NOT-32; doc 12's fabrication-guard pattern. §0.3, §3.2.1.

**DA-12 — Do not ship a gate threshold, cost factor, or traversal weight as a plain default.**
No defaults on gate thresholds; the service fails to start without them. Cost factors and traversal weights carry `PLACEHOLDER` markers and appear in `assumptions[]` and `policy_version`. 09 DO-NOT-31. §5.4, §3.4.1, §5.6.

**DA-13 — Do not join on `eic`, and do not silently resolve an ambiguous EIC to one NIIN.**
NAVSEAINST 4790.8 Appendix A makes EIC *"a class code of variable specificity"* (03 §3.3). Test artefacts arrive keyed by EIC and drawing number; the adapter resolves to NIIN and **records the ambiguity as data**. 09 DO-NOT-5; §3.2.4.

**DA-14 — Do not recompute criticality.**
PdM owns it. Consume `criticality_tier.assigned`; use the tier as a priority input. Two criticality numbers in one system is a defect regardless of which is better. §3.5.1.

**DA-15 — Do not flatten a taxonomy citation.**
Cite by `lineage_id` with `taxonomy_version`, carry `attribution_agreement` as received, and never resolve a `pma_only`/`maintenance_only` disagreement on the design authority's behalf. Doc 12 DO-NOT-1, DO-NOT-2, §9.3. §3.3.1, §8.4.

---

## 15. Open decisions and placeholders

Every item is a value or choice **no source document supplies**. None is resolved by invention. Each names what unblocks it.

| ID | Question | Interim position | Unblocked by |
|---|---|---|---|
| **OD-1** | Gate thresholds: `COST_FLOOR_USD`, `PRIORITY_FLOOR`, `COMPLETENESS_FLOOR`, `FIELD_FAILURE_FLOOR` | **No defaults.** Required config; service fails to start without them; `gate_policy_version = "v0-placeholder"` on every decision row | Phase 3 SME validation. 04 §10's *"Cost model depth"* question |
| **OD-2** | Cost factors for every roll-up line (§5.6) | `PLACEHOLDER` in `cost_model_version`; enumerated in `assumptions[]` on every estimate | Phase 3 cost-model work |
| **OD-3** | Traversal direction and weights per relation (§3.4.1) | Seeded table, `is_placeholder = true`, `policy_version` on every snapshot | Phase 3 SME validation. 04 §10's *"Dependency graph population"* question |
| **OD-4** | How PdM criticality tier enters the priority score (§3.5.2) | Seventh vector component; `priority_method = "tmi-vector-v0-placeholder"` | 04 §10's *"Priority scoring… and how it reconciles with PdM criticality"* |
| **OD-5** | **Test/qualification data model and formats** | Program-defined placeholder vocabularies, namespaced and authority-marked (§3.2.1) | **A primary source. Document 07 has none** (§0.3). 04 §10's *"Test data model and formats"* |
| **OD-6** | Authoritative source for design dependency and interface data below the CDMD-OA configuration level | `sme_asserted` and `apl_derived` edges only, at demonstration scale | Program research. Not answerable from public sources per 07 §10 |
| **OD-7** | Whether stage 2 is in demonstration scope at all | Built and gated; whether it *runs* in the demo is a config and data question | 04 §10: *"Whether the demonstration implements the second stage is a Phase 3 scope question"* |
| **OD-8** | Whether the demonstration names an actual design authority | Authority checked as `design_authority`; the named individual is a program decision | 04 §10's *"Whether the demonstration represents an actual redesign decision workflow with a named authority"* |
| **OD-9** | Failure Intelligence's evidence-strength scale and its ordering | Digest-equality enforcement only; no ranking (§8.3) | `docs/build/25-failure-intelligence.md`. 04 §9's *"Evidence strength scale definition"* |
| **OD-10** | PdM's scenario-result representation | Binding DA→PDM-1 stated (§7.4); producer side complete | `docs/build/22-pdm.md`. 04 §4's Phase 3 question |
| **OD-11** | Synthetic test records, coverage profiles, and dependency edges | Authored in this service's conformance dataset | Doc 13 addition. §16 correction #5 |

---

## 16. Corrections to source documents

Each is a defect or gap in the cited document, not a decision of this one.

| # | Document | Issue | Disposition |
|---|---|---|---|
| **1** | **10 §4.7 / OQ-13** | `Proposal.authority_class` is typed as *"an opaque string"* because *"the vocabulary is therefore undefined in document 03"* — OQ-13, *"the most consequential open question in this package."* **03 §7.2.1 now defines it**, added the same day this document was written | **OQ-13 is resolved.** `packages/canonical-schemas` must add `AuthorityClass = maintainer \| planner \| supply_officer \| design_authority \| fleet_authority \| security_officer` as a `StrEnum`, retype the field, and add the §7.2.1 minimum-authority table as a cross-field validator. **Applied in this document's §6.4, and now also in `10-shared-packages.md` §4.6b/§4.7 — both sides done** |
| **2** | **10 §4.7** | The `Proposal` model's docstring cites 03 §7.2's *"§9.3"* cross-reference for the authority vocabulary and notes 03 §9 has no §9.3 | 03 §7.2's cross-reference should now read **§7.2.1**. Flagged; joins the 09 §11 item 8 list of 03 cross-reference defects |
| **3** | **03 §7.2 vs §7.2.1** | §7.2 rule 4: *"Dual control is mandatory at class and fleet scope."* §7.2.1's table annotates *"+ dual control"* on `redesign_case` only at **fleet**. The two disagree at class scope | **The stricter reading is applied**: dual control at class *and* fleet. §7.2.1 is a *minimum-authority* table — its own closing sentence forbids removing the minimum it establishes — not an exhaustive dual-control table, and §7.2 rule 4 is unqualified. Doc 10's validator already forces it, so the weaker reading is unrepresentable. **03 §7.2.1 should annotate the class cell** to remove the ambiguity |
| **4** | **03 §6 vs 11 §9** | Doc 11 introduces `installed_item.identity_resolved` and names `design-advisory` among its consumers; the event is absent from 03 §6's catalog. Subscribing fails `check_event_catalog.py`; not subscribing risks citing a superseded provisional identity | **Not subscribed.** Provisional identities reconcile at next dossier assembly via `changed_since`. **03 §6 needs the catalog row**, or doc 11 §9 needs to drop the consumer claim |
| **5** | **13 (synthetic data)** | Generates no test records, coverage profiles, or dependency edges; references this sub-application once, in the agent-count row. Without them, neither the two-stage costing nor the completeness reporting can be demonstrated | Reference dataset authored in `packages/contracts/conformance/design-advisory/dataset/`. **Doc 13 needs a Design Advisory section**. OD-11 |
| **6** | **04 §10 aggregates** | No aggregate covers `design_change.projected`, though 04 §10 requires the event. A projection published as a side effect of a case would share the case's topic and storage — the opposite of *"strictly segregated"* | `DesignScenario` added as a first-class aggregate with its own table and topic (§7.1). **04 §10's aggregate table needs the row** |
| **7** | **04 §10 API surface** | Lists `POST /redesign-cases/{id}/estimate` but no operation for stage-1 qualification or the gate, so the two-stage design has no API expression and the gate no enforcement point | `POST /redesign-candidates/{id}/parametric-estimate` and `POST /redesign-candidates/{id}/evaluate-gate` added, both `x-side-effects: none` (§5.1, §6.3). **04 §10's API table needs the rows** |
| **8** | **07 (Navy data systems)** | **No coverage of test, qualification, or developmental-engineering data systems**, and §10's gap register does not list the omission because the subject was never in scope. This is the one sub-application whose primary owned data type has no documented Navy source | Stated as a gap (§0.3); vocabularies namespaced and authority-marked; three specific research needs logged as OD-5 and OD-6. **07 §10 should list test/qualification data systems among the outstanding gaps**, so the omission is visible to the next reader |
| **9** | **05 (review findings)** | Contains **no finding** on `design_change.projected` contaminating operational predictions, despite 04 §10 requiring strict segregation and 04 §4 listing it as an unresolved Phase 3 question. The two review passes did not reach it | Producer-side mechanism specified (§7.2); consumer obligation stated as DA→PDM-1 (§7.4). Flagged: **this is an unreviewed contamination path**, and the fact that it survived two adversarial passes is itself worth recording |

---

## 17. Definition of Done

**09 §8 in full, reproduced into `services/design-advisory/README.md` and ticked there. Nothing in it is removed.** The items below are additional.

### 17.1 Decision-package boundary

- [ ] No route matches an approval/authorization/direction verb outside proposal adjudication; `case_status` has no `approved` value. *(§1.2 E1–E2; T-NODECISION-1)*
- [ ] `published` is unreachable without `published_via_proposal_id`. *(§3.6; T-NODECISION-2)*
- [ ] `recommendation_limitations` and `recommendation_evidence_gaps` are required non-empty on every assembled or published case. *(§1.2 E3; T-NODECISION-3)*
- [ ] `recommendation_stance` is the four-value non-directive vocabulary. *(T-NODECISION-4)*
- [ ] Every `x-side-effects: none` operation writes only snapshot/provenance tables and emits no outbox row. *(§6.2; T-SIDEEFFECT-1)*
- [ ] `authority_class = design_authority` at every blast radius; dual control forced at class and fleet. *(03 §7.2.1; T-AUTH-1..3)*

### 17.2 Evidence-strength passthrough

- [ ] `evidence_strength` carried verbatim with a digest verified against the **source event**. *(§8.2; T-PASS-1)*
- [ ] No column can express a local, combined, or thresholded strength. *(T-PASS-4)*
- [ ] Every response containing a citation contains the structured object; prose is additional and version-stamped. *(T-PASS-2)*
- [ ] The renderer preserves confounders and emits no causal verb. *(DA-3; T-PASS-2)*
- [ ] No aggregation across citations. *(T-PASS-3)*
- [ ] `contra` citations never satisfy the gate. *(T-PASS-5)*

### 17.3 Dependency graph and completeness

- [ ] Traversal is a single SQL function; completeness computed in the same statement. *(§4.2; T-COMPLETE-1)*
- [ ] Edges stored once; both orientations generated; symmetric edges counted once. *(T-COMPLETE-3)*
- [ ] Per-path cycle detection; artifacts terminal; depth capped at 6. *(T-COMPLETE-5, -6)*
- [ ] `is_bounded_below` set on truncation even at ratio 1.0. *(T-COMPLETE-4)*
- [ ] Unverifiable source kinds can never count as verified. *(T-COMPLETE-2)*
- [ ] `dependency_completeness` `NOT NULL` on every case and consistent with its snapshot. *(T-COMPLETE-8)*
- [ ] `dependency_rollup` over an incomplete graph is recorded as a lower bound. *(T-COMPLETE-9)*

### 17.4 Two-stage costing

- [ ] Stage 1 is `x-side-effects: none` and persists nothing. *(§5.1)*
- [ ] Stage 2 refused with 409 `gate-not-passed` and `failed_conditions` absent a passing gate. *(T-GATE-1)*
- [ ] Gate thresholds have **no defaults**; the service fails to start without them. *(T-GATE-2)*
- [ ] Every `gate_decision` carries `thresholds_in_force` and `gate_policy_version`; append-only with supersession. *(T-GATE-3, -4)*
- [ ] The gate does **not** threshold on evidence strength. *(DA-10; T-PASS-6)*
- [ ] Roll-up refuses outside its staleness bound. *(T-GATE-6)*

### 17.5 Test data and absence

- [ ] Coverage profile exists per NIIN in scope; assembly refuses without one. *(T-ABSENCE-6)*
- [ ] Absence is a row; `qualification_credit` false for every absence status. *(T-ABSENCE-1, -2)*
- [ ] All three absence constraints enforced. *(T-ABSENCE-3)*
- [ ] G4 requires assessment, not presence. *(T-ABSENCE-4)*
- [ ] EIC carried for federation only; ambiguity recorded and propagated. *(DA-13; T-ABSENCE-7)*
- [ ] Vocabularies namespaced `FATHOM-TK-###` with `code_authority`; **no Navy test schema asserted**. *(DA-11; §0.3)*

### 17.6 Scenario segregation

- [ ] Separate topic, separate aggregate, separate table. *(T-SEG-3)*
- [ ] `scenario_kind` single-valued; `hypothetical` forced true; `scenario_baseline_ref` namespaced and non-joinable. *(T-SEG-2)*
- [ ] `scope = niin`; subject carries only `niin`; no `installed_item_id`, `asset_id`, or `baseline_id` in the payload. *(T-SEG-1)*
- [ ] Envelope `baseline_epoch` equals `computed_against_baseline_epoch`. *(T-SEG-5)*
- [ ] Inbound scenario filter active with its counter. *(T-SEG-4)*
- [ ] DA→PDM-1 recorded in the README as a binding on `docs/build/22-pdm.md`. *(§7.4)*
- [ ] The `pdm` consumer-driven test asserting no scenario reference on operational predictions is contributed. *(§10.3)*

### 17.7 Events, catalog, and documentation

- [ ] `producer_node == "enterprise"` on every event. *(§0.1; T-ENV-1)*
- [ ] `catalog.py` `PUBLISHES`/`CONSUMES` equal `values.yaml` equal 03 §6; `check_event_catalog.py` exits 0; **no wildcards**. *(09 §8.2)*
- [ ] The `installed_item.identity_resolved` discrepancy is recorded in the README with its interim position. *(§16 #4)*
- [ ] All eleven open decisions in §15 recorded in the README as local resolutions and raised for program decision. *(09 §8.7)*
- [ ] All nine §16 corrections raised against their owning documents.
- [ ] `README.md` states purpose, owned aggregates, published and consumed events, the conflict policy (03 §11 default accepted for every aggregate), the `part_availability` staleness bound, and the sanctioned NetworkPolicy peers.
- [ ] Every deviation from 09 carries an ADR under `docs/adr/`.

