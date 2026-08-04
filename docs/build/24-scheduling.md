# Build Framework 24 — Maintenance Execution & Scheduling (`maintenance`)

| | |
|---|---|
| **Status** | Draft rev 2 — reconciled against `22-pdm.md`, `26-supply.md`, and `09 §4.4.2` now that all three have landed. Phase 3 build framework for one sub-application |
| **Slug** | `maintenance` — canonical, per [03 §3.1](../architecture/03-integration-contracts.md). Display abbreviation "Scheduling". Directory `services/maintenance/`, package `fathom_maintenance` |
| **Scope** | Aggregates, API surface, the scheduling optimizer and its reservation protocol, findings capture as a labeling problem, JCN generation, edge-authoritative maintenance action recording, deferral handling, events, testing, deployment, and the Definition of Done for this sub-application |
| **Derived from** | [03 — Integration Contracts](../architecture/03-integration-contracts.md) §3, §4, §5, §6 (Scheduling rows), §7.1, §7.2, §7.2.1, §9, §11, §14, §15 · [04 — Sub-Application Architectures](../architecture/04-subapplication-architectures.md) §6, §7 · [05 — Review Findings](../architecture/05-architecture-review-findings.md) **D6, D8, D20, D34**, and D1, D7, D9, D16, D19, D21, D29, D34 · [06 — Demonstration Decisions](../architecture/06-demo-decisions-and-assumptions.md) §2, §3, §4, §7, §9.2 · [07 — Navy Data Systems](../architecture/07-navy-data-systems.md) §5 · [09 — Monorepo and Conventions](09-monorepo-and-conventions.md) · [10 — Shared Packages](10-shared-packages.md) §4.7 · [11 — Outbox and Sync Library](11-outbox-sync-library.md) §5, §7, §8, §9 · [12 — Reference Data and Taxonomy](12-reference-data-taxonomy.md) §2.6, §2.9, §4, §9 · [13 — Synthetic Data Generator](13-synthetic-data-generator.md) §9.10, §11.5, §15 |
| **Precedence** | Document 03 prevails on any contract surface. Document 09 prevails on layout, stack, and conventions. This document prevails on Scheduling's internal design |
| **Parallel-authoring note** | Rev 1 was written before `docs/build/22-pdm.md` and `docs/build/26-supply.md` landed, and carried three **[RECONCILE RC-n]** assumptions. **Both siblings have now landed and all three are closed** — two of them *against* rev 1's assumption. §4.2 now consumes PdM's conversion rather than implementing its own (RC-1); §4.5 now matches Supply's actual reservation-set request and its actual release semantics (RC-2, the material correction in this revision); §5.4's `triggering_driver` vocabulary is corrected to the values PdM and the generator both use (RC-3). Resolution detail is in §16.1 |
| **Classification** | Internal |

**Decision markers**, per [09 §1.3](09-monorepo-and-conventions.md):

- **[03 §n]**, **[04 §n]**, **[06 §n]**, **[07 §n]** — dictated by an architecture document. Not negotiable at implementation time.
- **[ESTABLISHED HERE]** — the architecture documents do not specify it; this document makes the call once so it is not made differently in three places inside one service.
- **[PLACEHOLDER — Phase 3 SME]** — a formulation, weight, or threshold that is an engineering proposal standing in for subject-matter validation. It must run, and it must be labelled illustrative wherever an operator sees its output ([06 §3](../architecture/06-demo-decisions-and-assumptions.md), assumption A8).
- **[OPEN]** — genuinely undecided; listed in §16. Not to be resolved locally without recording it.
- **[RECONCILE RC-n]** — an assumption about a sibling build document, to be confirmed or corrected when that document lands. **All three are now closed; see §16.1.**

---

## 1. Purpose and scope

**Purpose**, per [04 §6](../architecture/04-subapplication-architectures.md): convert predictions, planned maintenance requirements, and actual casualties into work candidates; plan those candidates into availability windows subject to real constraints; and capture executed maintenance as the label stream on which the entire predictive capability depends.

### 1.1 Owned

Work candidates, work orders, deferrals, PMS periodicity records, availability definitions, work packages, the scheduling optimizer and its persisted runs, executed maintenance history, the client-side reservation-set projection, and proposals targeting this sub-application.

### 1.2 Not owned

Predictions ([PdM](../architecture/04-subapplication-architectures.md#4-predictive-maintenance)), parts availability and reservations themselves (Supply — Scheduling holds a projection and Supply is authoritative), configuration (Registry — though completion of work *triggers* configuration change), the failure-mode vocabulary (Reference Data owns the vocabulary; Scheduling owns findings *codings* only, per [03 §14](../architecture/03-integration-contracts.md)).

### 1.3 Why this sub-application carries disproportionate risk

Three properties make Scheduling different from its siblings, and each of them is a review finding rather than an opinion.

1. **It is the sole source of the label stream.** `maintenance_action.recorded` is the training signal for every model in the system ([03 §6](../architecture/03-integration-contracts.md)). A capture defect here does not surface as a Scheduling bug; it surfaces months later as a PdM calibration drift with no traceable cause.
2. **It is the sole source of PdM's causal correction.** `triggering_driver`, `triggering_prediction_id`, and `policy_version` are populated *here* and nowhere else. Without them, "neither calibration nor causal analysis can condition on the intervention policy" `[D1, D21]`. A plausible-but-wrong value in these fields is worse than a missing one, because missingness is modellable and fabrication is not (§5.4).
3. **It is the only sub-application that issues an externally-consequential command to another sub-application on behalf of the whole fleet.** A reservation holds real stock. A reservation protocol without atomicity and compensation "orphans persist and 37 spurious availability events degrade every other asset's planning" `[D6]`.

The two highest-severity items in this document are therefore §4.5 (the reservation saga, closing D6) and §7 (edge-authoritative recording, closing D8). Everything else is ordinary domain engineering by comparison.

### 1.4 The one structural decision everything else follows from

**What was done and what was authorized are two aggregates, in two tables, under two conflict policies, joined by a nullable foreign key.** [03 §11](../architecture/03-integration-contracts.md):

> | **Maintenance action records** | **Edge-authoritative, append-only** | The ship records what it *did*; the server retains authority over what was *authorized*. Separating them is what permits label capture afloat `[D8]` |
> | Work orders and authorizations | Server-authoritative; edge submits requests | Maintenance authority does not fork |

[06 §4](../architecture/06-demo-decisions-and-assumptions.md) adds the reason this is right independent of the edge case:

> The separation between recording what was done and authorizing what may be done is correct independently of the edge case. It is how maintenance documentation actually works, and adopting it removes an artificial coupling rather than adding a special case.

[04 §6](../architecture/04-subapplication-architectures.md) still lists a `MaintenanceAction` aggregate ("Executed work: findings, parts consumed, and the corrective-versus-preventive determination") *alongside* `MaintenanceActionRecord`. **There is exactly one aggregate here, and it is `MaintenanceActionRecord`.** `MaintenanceAction` as a member of the work-order aggregate is the precise shape of the defect D8 describes — "`MaintenanceAction` lives in the work-order aggregate, which the edge may not commit" — and building both would rebuild the defect beside its own fix. Recorded as a correction to document 04 in §17.

---

## 2. Traceability

Every review finding this document is responsible for, and where it is discharged. A reviewer may read the right-hand column and stop.

| Finding | Substance | Discharged in |
|---|---|---|
| **D6** ⚠ HIGH | Optimizer has neither a consistent snapshot nor atomic reservation; per-NIIN reservation orphans stock and emits spurious availability events | §4.1 (snapshot + watermark), §4.5 (the saga), §4.6 (convergence), §11.3 (the proof test) |
| **D8** ⚠ HIGH | Edge design excludes capture of the label stream; a submarine dark six weeks cannot record the four highest-value fields | §1.4, §3.4, §7, §11.4 |
| **D20** HIGH | Scheduling↔Supply has no convergence criterion | §4.6 |
| **D34** MED | Deferrals miscategorized as prediction-quality evidence | §3.5, §8 |
| **D1** ⚠ HIGH | Informative censoring; treatment record required on every action | §5.4, §5.6 |
| **D21** ⚠ HIGH | Confounded causal loop; `maintenance_action.recorded` carried no triggering prediction or policy version | §5.4 |
| **D7** ⚠ HIGH | Cross-tier comparability unachievable; optimizer must convert to expected consequence per reference class | §4.2 |
| **D19** ⚠ HIGH | No per-item RUL below an item-conditional reference class | §4.2 |
| **D9** ⚠ HIGH | Item-versus-position identity; provisional identity afloat | §3.2 (merge keys), §7.3 |
| **D16** ⚠ HIGH | Proposals need staleness, claim, and authority-versus-blast-radius | §3.9 |
| **D29** MED-HIGH | No wall clock arbitrates anything | §4.5 (monotonic deadlines), §10.1 |
| **C10** | `position_id` is not `installed_item_id` | §3.2, §3.4 |
| **C19** | Agents are never direct topic consumers | §9.4 |
| **C20** | Conflict policy declared per aggregate, complete-or-fail | §3.11 |
| **D24** | Substitution obligations: `lead_time` and `condition_code` must exist on Supply's surface or the hard constraint is unsatisfiable | §3.8, §4.1 refusal 4, §10.5 |
| **OQ-13** ([10 §11](10-shared-packages.md)) | `authority_class` vocabulary was undefined, blocking D16's authority check | §3.9 — **resolved** by [03 §7.2.1](../architecture/03-integration-contracts.md) for `work_candidate` and `interval_change` |

**What changed in rev 2.** Three sibling build documents landed after rev 1 and closed its three open assumptions. The material change is §4.5: rev 1's reservation protocol assumed a release-by-client-key operation that Supply does not provide, which would have failed in the compensation path — under fault, where D6 lives. §4.5.5 replaces it with three mechanisms that need no change to Supply. §4.2 deletes Scheduling's locally-invented risk conversion in favour of PdM's, and §5.4.1 corrects a `triggering_driver` vocabulary that would have silently biased every IPCW weight PdM computes. §§14–18 complete the document.

---

## 3. Data model

PostgreSQL, one logical database `maintenance`, one CloudNativePG cluster ([09 §8.4](09-monorepo-and-conventions.md), obligation 13). Schema `maintenance`. SQLAlchemy models under `src/fathom_maintenance/models/`, one module per aggregate.

Identity throughout is [03 §3.3](../architecture/03-integration-contracts.md): `asset_id`, `system_id`, `position_id`, `installed_item_id`, `niin` are the join keys. `eic`, `apl`, `hull_or_tail`, `eswbs`, `position_code`, `nsn`, and **`jcn`** are carried for human reference and external federation and are **never** join keys.

> **The JCN is not a join key, and this is not a stylistic choice.** [13 §9.10](13-synthetic-data-generator.md) generates "duplicate 2-Kilos — same job written twice with different JSNs" as a realistic corruption. A design that keys on the JCN cannot represent that input, so it will either reject real records or silently merge two distinct actions. `action_record_id` is the key; the JCN is a reporting identifier (§6).

### 3.1 Aggregate inventory

| Aggregate | Table | Mutability | Conflict policy ([03 §11](../architecture/03-integration-contracts.md)) | Edge-writable |
|---|---|---|---|---|
| `WorkCandidate` | `work_candidate` | Append-only lineage; `status` mutable | default: enterprise-authoritative, not edge-writable | No |
| `WorkOrder` | `work_order` | Mutable, state machine | `SERVER_AUTHORITATIVE_EDGE_SUBMITS` | **No** — edge submits requests |
| `MaintenanceActionRecord` | `maintenance_action_record` | **INSERT only** | `EDGE_AUTHORITATIVE_APPEND_ONLY` | **Yes — the only one** |
| `Deferral` | `deferral` | INSERT only; supersession by new row | default | No |
| `Availability` | `availability` | Mutable | default | No |
| `WorkPackage` | `work_package` | Mutable, saga state | `SERVER_AUTHORITATIVE_EDGE_SUBMITS` | No |
| `ReservationSet` (projection) | `reservation_set` | Mutable, saga state | default (Supply is authoritative) | No |
| `PmsRequirement` | `pms_requirement` | Mutable, versioned | default | No |
| `Proposal` | `proposal` | Append-only; adjudication server-only | `APPEND_ONLY_SERVER_ADJUDICATED` | Create yes, adjudicate no |
| `OptimizerRun` | `optimizer_run`, `candidate_disposition` | INSERT only | default | No |
| `JsnBlockLease` | `jsn_block_lease` | Mutable at issue; consumed monotonically | `SERVER_AUTHORITATIVE_EDGE_SUBMITS` (issued ashore, consumed afloat) | Consume yes, issue no |

Registration is declarative and complete-or-fail, per [11 §7.2](11-outbox-sync-library.md) `[C20]`:

```python
# src/fathom_maintenance/events/policies.py
policies = ConflictPolicyRegistry.declare(
    service="maintenance",
    policies=[
        EdgeAuthoritativeAppendOnly(
            aggregate="maintenance_action_record",
            divergence_budget=DivergenceBudget(
                # MUST exceed the planned patrol length. 11 §9.1: "the ship goes read-only
                # for maintenance recording halfway through the patrol, and D8 returns
                # wearing a compliance badge." 06 §4 scripts 42 days; 90 gives headroom.
                max_disconnection=timedelta(days=90),
                max_unreconciled_records=None,   # deliberately unbounded: see §7.5
            ),
        ),
        ServerAuthoritativeEdgeSubmits(aggregate="work_order"),
        ServerAuthoritativeEdgeSubmits(aggregate="work_package"),
        ServerAuthoritativeEdgeSubmits(aggregate="jsn_block_lease"),
        AppendOnlyServerAdjudicated(aggregate="proposal"),
        # every remaining owned aggregate is explicitly defaulted, not silently defaulted
        *[EnterpriseAuthoritativeNotEdgeWritable(aggregate=a, default=True) for a in (
            "work_candidate", "deferral", "availability", "reservation_set",
            "pms_requirement", "optimizer_run", "candidate_disposition",
        )],
    ],
)
```

### 3.2 `WorkCandidate` — three drivers, one lifecycle

```
WorkCandidate {
  candidate_id                uuid  PK
  -- what
  asset_id, system_id?, position_id, installed_item_id, niin, equipment_family
  identity_provisional        bool          # 03 §3.3; true where the item was minted afloat
  eic?                        char(7)       # federation and human reference only
  apl?                        text          # EIC+APL is the Navy's stated composite key [07 §5.1]
  baseline_id, baseline_epoch               # 03 §5.4; a candidate is invalid past its epoch
  -- which driver
  driver                      enum { prediction | pms | casualty }
  driver_is_timing_determinant bool         # see merge rule 4
  merged_from_drivers[]       enum[]        # empty unless this candidate is a merge product
  merged_candidate_ids[]      uuid[]        # the superseded sources, retained forever
  -- driver = prediction  (all null otherwise)
  source_prediction_id?, source_scoring_run_id?, prediction_computed_at?
  reference_class?            enum { item | niin_fleet | equipment_family | class_estimate }
  p_failure?                  numeric       # NULL is meaningful, not zero  [03 §7.1]
  population_hazard_rate?     numeric       # the only rate-like figure below the n>=50 gate
  rul_p50_days?, rul_unit?                  # only where reference_class is item-conditional [D19]
  horizon_days?, fallback_level?, calibration_population?
  model_version?
  -- driver = pms  (all null otherwise)
  pms_requirement_id?, mrc_ref?
  periodicity_basis?          enum { calendar | usage }
  periodicity_value?, periodicity_unit?
  usage_counter_epoch?                      # 03 §11; a reset invalidates a usage-based due date
  due_at_earliest?, due_at_latest?
  interval_policy_version?
  -- driver = casualty  (all null otherwise)
  casrep_ref?, casrep_category?             # 2..4 [07 §5.8]
  casualty_reported_at?
  status_code?                char(1)       # 3-M STATUS. 2 = inoperative, 3 = degraded [07 §5.4]
  -- common
  estimated_scope { man_hours, skill_class, duration_hours,
                    required_parts[{ niin, quantity, interchangeable_group_ref? }] }
  expected_consequence?       ExpectedConsequence   # §4.2. Optimizer-populated, never client-set
  driver_disagreement?        { pms_due_at, prediction_horizon_days, delta_days, retained: true }
  policy_version              text          # the candidate-generation policy AT CREATION  [D21]
  status                      enum { open | packaged | authorized | deferred |
                                     superseded | withdrawn | closed }
  withdrawn_reason?           enum { baseline_superseded | prediction_invalidated |
                                     item_removed | duplicate | operator }
  created_by                  text          # "generator:prediction" | "generator:pms" |
                                            # "api:<principal>" | "proposal:<proposal_id>"
  taxonomy_version?           text
  classification, correlation_id, created_at, monotonic_seq
}
```

#### 3.2.1 The three generators

| Driver | Input | Generator | Notes |
|---|---|---|---|
| `prediction` | `prediction.updated` → local prediction read model; `casrep_risk.raised` from Fleet Status | `services/candidates/from_prediction.py` | Gated on the admission filter of §4.3 |
| `pms` | `PmsRequirement` catalog × `usage_counter.updated` / calendar tick | `services/candidates/from_pms.py` | Usage-based due dates are keyed on `(installed_item_id, counter_type, counter_epoch)`; a `usage_counter.reset` **recomputes** the due date rather than carrying it forward |
| `casualty` | `POST /work-candidates` with `driver=casualty`, authored by ship's force or an RMC planner | API only | See the gap below |

> **`casrep_risk.raised` is a prediction, not a casualty.** [03 §6](../architecture/03-integration-contracts.md) defines it as "installed item, **predicted** category, horizon, evidence references", published by Fleet Status. A candidate generated from it therefore carries `driver = prediction` and `source_prediction_id` resolved from the event's evidence references — **not** `driver = casualty`. The name invites the opposite coding, and the opposite coding is a silent corruption of D1's correction: prediction-driven interventions would be recorded as routine responses to equipment failure, the treatment record would say no policy assigned them, and the informative-censoring correction would be computed against a treatment population missing exactly the items the model acted on. A unit test asserts this mapping by name (§11.5).

> **[OPEN OQ-1] No event announces an actual casualty.** The [03 §6](../architecture/03-integration-contracts.md) catalog contains `casrep_risk.raised` and `casrep_risk.cleared` (both Fleet Status, both predictive) and no producer of an *occurred* casualty. Scheduling's `casualty` driver is therefore API-originated only, which is defensible — a casualty is authored by a human, and [07 §5.8](../architecture/07-navy-data-systems.md)'s CASREP INITIAL is a message, not a telemetry fact — but it means no sub-application can subscribe to casualties. Raised for a catalog decision; interim position is API-only origination, recorded in the README.

#### 3.2.2 Merge logic — a predicted failure and a scheduled preventive task on one item

[04 §6](../architecture/04-subapplication-architectures.md) names this the interaction that matters most: "a predicted failure and a scheduled preventive task on the same item should merge rather than compete." Its Phase 3 question — "how prediction-driven and PMS-driven candidates merge, and who adjudicates when they disagree" — is answered here.

**Trigger.** A new candidate `C_new` for installed item `I` merges with an open candidate `C_old` for `I` when **both** hold:

1. `C_new.installed_item_id == C_old.installed_item_id`. **Merge is keyed on the installed item, never the position** `[C10, D9]`. Two items successively occupying one position are two items; merging their candidates is the inherited-degradation defect at the planning layer.
2. Scope overlap, defined as either (a) `estimated_scope.required_parts` intersect on `niin` or on `interchangeable_group_ref`, or (b) the PMS requirement's covered failure modes intersect the prediction's `candidate_modes[]`, resolved through Reference Data's crosswalk ([12 §2.9](12-reference-data-taxonomy.md), `GET /crosswalk/3m-codes`). Overlap is computed over the **full candidate-mode set**, never a highest-confidence pick — [12 §2.9](12-reference-data-taxonomy.md) is explicit that flattening the many-to-many mapping "silently corrupts every label derived from maintenance findings."

**Rules.**

| # | Rule | Why |
|---|---|---|
| 1 | Merge only within one `baseline_epoch`. A candidate whose epoch is superseded is `withdrawn`, never merged | 03 §5.4. Merging across epochs plans work against a configuration that no longer exists |
| 2 | The merge product is a **new** candidate. Both sources move to `superseded` and are retained forever, with `merged_candidate_ids` pointing back | Append-only lineage. The merge is itself evidence, and the disagreement in rule 6 is only inspectable if both sources survive |
| 3 | `estimated_scope` is a **union by task**, not a sum. Where the PMS task subsumes the corrective task, man-hours are the larger of the two, not the total | Summing double-counts capacity, and the optimizer then starves the availability of real work to make room for phantom hours |
| 4 | **`driver` of the merge product is the driver that changed the timing.** Formally: `prediction` if `merged.due_at_latest < C_pms.due_at_latest − timing_tolerance_days`, else `pms`. `driver_is_timing_determinant` records that this test was applied | This is the load-bearing rule. The intuitive alternative — "a PMS task existed, so call it `pms`" — reclassifies every prediction-accelerated intervention as routine periodicity. The treatment record then attributes the intervention to a policy that did not make it, the propensity model sees no treatment where a treatment occurred, and D1's informative censoring is reintroduced *undetectably*, because the data looks clean and complete `[D1, D21]` |
| 5 | A `casualty` candidate **merges in**; it never merges away a prediction candidate's `source_prediction_id`, which is retained on the product | That linkage is the measurement for **warning lead-time coverage**, the primary effectiveness metric ([06 §2](../architecture/06-demo-decisions-and-assumptions.md)). Dropping it on the ground that the item already failed makes the program's headline metric uncomputable in exactly the cases that matter |
| 6 | **Disagreement is retained as data, not resolved.** Where the prediction says act now and the PMS interval says act in 400 days, the product carries `driver_disagreement { pms_due_at, prediction_horizon_days, delta_days }` and the explanation (§4.4) surfaces it | Normalising on write destroys the disagreement signal, which is the same error [12 §2.9](12-reference-data-taxonomy.md) and [03 §14](../architecture/03-integration-contracts.md) forbid at the vocabulary layer |
| 7 | **Adjudication of the disagreement is the planner's, at package approval.** Changing the PMS interval itself is a separate act, reachable only through an `interval_change` proposal with the authority of §3.9 | 03 §9 item 2: "an `interval_change` must fall within a bounded delta and route to PMS authority." An optimizer that silently suppressed a preventive task because a model disagreed with it would be doing, without authority, precisely what §7.2.1 requires `fleet_authority` and dual control to do |

`timing_tolerance_days` — **[PLACEHOLDER — Phase 3 SME]** 14 days. It exists so that a prediction landing a fortnight before a PMS due date is not recorded as having driven the work when the work was going to happen anyway.

### 3.3 `WorkOrder` — what was authorized

```
WorkOrder {
  work_order_id               uuid PK
  jcn                         char(13)  UNIQUE            # §6
  asset_id, system_id?, position_id, installed_item_id
  work_center                 char(4)                     # left-justified, space-padded [07 §5.2]
  originating_candidate_id?   uuid → work_candidate
  driver                      enum { prediction | pms | casualty }   # denormalized, IMMUTABLE
  policy_version_at_authorization  text
  work_package_id?, availability_id?
  planned_window              { start, end }
  status                      enum { requested | authorized | scheduled | in_work |
                                     completed | cancelled | deferred }
  status_code?                char(1)                     # 3-M STATUS (2/3 filter) [07 §5.4]
  authorized_by, authorized_at, authority_class            # 03 §7.2.1 vocabulary
  baseline_id, baseline_epoch
  version                     int                         # ETag source
  classification, correlation_id, created_at, monotonic_seq
}
```

State machine, in `services/work_order_state.py`, as an explicit transition table — not `if` statements scattered across the API layer:

```
requested ──authorize──▶ authorized ──schedule──▶ scheduled ──start──▶ in_work ──▶ completed
    │                        │                        │                   │
    └──cancel──▶ cancelled ◀─┴────────────────────────┴───────────────────┘
                             └──defer──▶ deferred ──▶ (new planned_window) ──▶ scheduled
```

Two properties are enforced structurally rather than by convention:

- **`driver` is copied from the originating candidate at authorization and is immutable thereafter.** A trigger rejects `UPDATE` on the column. It is the treatment-assignment mechanism (§5.4) and must not drift when a planner edits a window.
- **The edge cannot reach `authorized`.** At the edge, `POST /work-orders` is converted to a request at the API boundary and stored in the local request queue ([11 §7.3](11-outbox-sync-library.md), `SERVER_AUTHORITATIVE_EDGE_SUBMITS`), returning `202` with the queued request's identifier and an explicit `authorization_pending_ashore` marker. `PATCH` to `status: authorized` at the edge returns `423` with `type: urn:fathom:problem:maintenance:not-edge-writable`. **The edge never fabricates an authorization** — and, per §7, it never needs to in order to record what it did.

### 3.4 `MaintenanceActionRecord` — edge-authoritative, append-only

This is the label stream. The schema below is exact, and every field is justified by a cited requirement or is not present.

```
MaintenanceActionRecord {
  -- identity ---------------------------------------------------------------
  action_record_id            uuid PK         # CLIENT-minted (uuid4). Doubles as the
                                              # Idempotency-Key. Client-minted so a
                                              # disconnected hull can create it with no
                                              # server round trip.
  producer_node               text            # "enterprise" | "edge:<asset_id>"  [03 §5.4]
  monotonic_seq               bigint          # per-producer-node. THE ordering key. Never a clock
  jcn                         char(13)?       # §6. NULLABLE — see §6.4
  jcn_assignment_deferred     bool
  supersedes_action_record_id uuid?           # append-only correction chain
  supersession_reason         enum?           { transcription_error | wrong_item_attribution |
                                                reclassification | coding_completed_ashore |
                                                parts_record_added }
  -- what physical thing -----------------------------------------------------
  asset_id, system_id?, position_id, installed_item_id
  identity_provisional        bool            # 03 §3.3; 11 §8. True where minted afloat
  eic?                        char(7)         # federation / human reference only [03 §3.3]
  apl?                        text            # EIC + APL: the Navy's composite key [07 §5.1]
  niin?                       char(9)
  work_center                 char(4)
  -- what was done -----------------------------------------------------------
  action_taken_code           varchar(2)      # 3-M ACTION TAKEN, 1-2 chars [08 §2.5]
  action_taken_set_complete   bool            # mirrors Reference Data's set_is_complete [12 §2.6]
  narrative                   text?           # UNTRUSTED free text. 03 §9. Never an instruction
  man_hours                   numeric?        # C5 MHRS [07 §5.3]
  parts_consumed[]            { niin, quantity, condition_code?,
                                reservation_set_id?, requisition_doc_no? }
  parts_record_absent         bool            # EXPLICIT, never inferred from an empty list
  -- the determination (Tier A field 1) [06 §9.2] -----------------------------
  maintenance_class           enum { corrective | preventive | opportunistic_preventive |
                                     no_defect_found | cannibalization }
  maintenance_class_basis     enum { observed_failure | observed_degradation |
                                     scheduled_interval | inspection_finding | directed }
  failure_indicator           bool            # DERIVED, never captured. §5.3
  failure_indicator_rule_version  text
  -- findings coding as filed (Tier A field 2) --------------------------------
  findings {
    cause_code                char(1)         # 3-M CAUSE (CAS)          [08 §2.5]
    when_discovered_code      char(1)         # 3-M WHEN DISCOVERED (WND)
    status_code               char(1)         # 3-M STATUS. 2/3 = mission-degrading [07 §5.4]
    deferral_code?            char(1)         # 2-Kilo block 9 (DFR)     [07 §5.3]
    taxonomy_version          text            # MANDATORY. 03 §14
  }
  findings_completed_ashore   bool            # 06 §4 assumption A5 fallback
  findings_coder_was_observer bool            # false = coded by someone who was not there
  -- failure timing (Tier A field 3) -----------------------------------------
  failure_detected_at         { earliest, latest, basis }   # INTERVAL-CENSORED. §5.5
  action_started_at, action_completed_at
  -- the treatment record (Tier A field 4; D1 / D21) --------------------------
  triggering_driver?          enum { prediction | pms_periodicity | casualty |
                                     opportunistic | opportunistic_pms }
                                              # NULL == "unknown". §5.4.1
  triggering_candidate_id?    uuid
  triggering_prediction_id?   uuid
  prediction_in_evidence_id?  uuid            # §5.4.2. NOT the treatment field
  triggering_prediction_ref?  { scoring_run_id, model_version, reference_class,
                                p_failure?, population_hazard_rate?, horizon_days,
                                computed_at, fallback_level }
  policy_version?             text
  holdout_member              bool            # 06 §2, 13 §10: policy-frozen population
  -- authorization linkage: NULLABLE BY DESIGN -------------------------------
  work_order_id               uuid?           # NULL is legal and expected
  authorization_state         enum { authorized | unauthorized_at_time_of_action |
                                     authorization_pending_ashore }
  -- provenance --------------------------------------------------------------
  recorded_by                 text
  recorded_at                 timestamptz     # when the producer persisted it
  occurred_at                 timestamptz     # when the work was done. May be weeks earlier
  classification, correlation_id, baseline_id, baseline_epoch
  sync_quality                jsonb           # 03 §5.4. Retained permanently
}
```

#### 3.4.1 The separation, mechanically

| Concern | What was DONE | What was AUTHORIZED |
|---|---|---|
| Aggregate | `MaintenanceActionRecord` | `WorkOrder` |
| Table | `maintenance.maintenance_action_record` | `maintenance.work_order` |
| Mutability | **INSERT only.** `UPDATE` and `DELETE` are revoked from the application role; a `BEFORE UPDATE OR DELETE` trigger raises. Corrections are new rows with `supersedes_action_record_id` | Mutable via the state machine, `ETag`/`If-Match` |
| Authority | **Edge-authoritative.** The shore *applies* the record; it may not modify, reject, or reorder it ([11 §7.3](11-outbox-sync-library.md)) | Server-authoritative. The edge submits requests |
| Write path | `POST /maintenance-action-records` — available at both enterprise and edge | `POST /work-orders` — enterprise only; `202`-queued at the edge |
| Link | `work_order_id` **nullable FK**, not enforced at the edge (where `work_order` is a read-through cache plus a request queue, so the referent may legitimately not exist locally) | — |
| Read-time join | `LEFT JOIN` on `work_order_id`, plus a reporting-only correlation on `jcn` | — |

**The nullable FK is the whole fix.** D8 exists because the action lived inside the aggregate the edge may not commit. Making the link optional, and making the record's identity client-minted, is what decouples label capture from authorization. Two consequences are stated so nobody re-couples them later:

- **A `MaintenanceActionRecord` with `work_order_id = NULL` is a complete, first-class, publishable record.** It is not a draft, not a stub, and not "pending". `authorization_state` records the *authorization* fact separately, and `unauthorized_at_time_of_action` is a legitimate terminal value — a pump repaired at sea under the CO's authority was not unauthorized in any operational sense, and the field records the documentary state, not a judgment.
- **Reconciliation never back-fills `work_order_id` by inference.** If a shore work order for the same equipment exists, the two coexist; a link is created only where the record was created *from* a work order or where a human explicitly associates them, and the association is itself a new superseding row with `supersession_reason = parts_record_added`-style provenance. [13 §15.2](13-synthetic-data-generator.md) generates exactly this conflict — "the enterprise, while the ship is dark, authorizes a work order for the same equipment… on reconnect the action record and the authorization must coexist without either overwriting the other" — and a heuristic auto-link is how that test starts passing for the wrong reason.

#### 3.4.2 Why `no_defect_found` and `cannibalization` are their own classes

`maintenance_class` is a five-value enum rather than the corrective/preventive binary [04 §6](../architecture/04-subapplication-architectures.md) implies, for two reasons that both bear on label quality:

- **`no_defect_found`.** Without it, an investigation that found nothing is coded `corrective` (work was reactive) or `preventive` (nothing was wrong). Coded `corrective`, it becomes a failure in PdM's label set that never happened, inflating observed hazard and pushing calibration the wrong way — the same directional error D1 describes, arriving by a different route. `failure_indicator` is false for this class by construction.
- **`cannibalization`.** A part removed serviceable to support another hull is neither corrective nor preventive on the donor item, and the donor's item history must not record a failure. It is also the case where `parts_consumed[]` and `installed_item.removed` disagree unless the class is explicit.

The corrective/preventive binary PdM needs is recovered by a **derivation** (§5.3), not by narrowing the capture vocabulary — capture is richer than the label, and the label is a function of the capture with a version on it.

### 3.5 `Deferral` — and the D34 discrimination

```
Deferral {
  deferral_id                 uuid PK
  work_candidate_id?          uuid            # exactly one of these two is required
  work_order_id?              uuid
  asset_id, installed_item_id, position_id
  deferral_reason_class       enum { capacity | tempo | parts_unavailable | risk_disagreement }
                                              # REQUIRED. NO DEFAULT. NOT NULLABLE.  [D34]
  reason_narrative            text            # untrusted free text; never the classification
  revised_window              { earliest, latest }
  deferral_code?              char(1)         # 2-Kilo block 9 (DFR)  [07 §5.3]
  -- risk acceptance
  risk_accepted_by            text
  risk_acceptance_authority   enum            # AuthorityClass, 03 §7.2.1
  accepted_expected_consequence  ExpectedConsequence?   # what the optimizer said, at deferral time
  -- ONLY populated where deferral_reason_class = risk_disagreement
  prediction_ref?             { prediction_id, scoring_run_id, model_version,
                                reference_class, p_failure?, population_hazard_rate?,
                                horizon_days, computed_at }
  disagreement?               { asserted_rul_days?, asserted_probability_band?, basis }
  -- provenance
  policy_version              text
  classification, correlation_id, created_at, monotonic_seq, producer_node
}
```

**Two validation rules, both `422`, and they run in both directions.** This is the entirety of the D34 fix at the capture layer, and it is four lines of code that decide whether the fleet's models drift.

```python
# src/fathom_maintenance/services/deferrals.py
def validate(d: DeferralCreate) -> None:
    if d.deferral_reason_class is RiskDisagreement:
        # A disagreement with the risk estimate is a claim ABOUT a specific prediction.
        # Without the referent and the basis it is not evidence, it is a mood.
        require(d.prediction_ref is not None, "deferral.risk_disagreement_requires_prediction_ref")
        require(d.disagreement and d.disagreement.basis, "deferral.risk_disagreement_requires_basis")
    else:
        # THE DIRECTION THAT MATTERS. A capacity, tempo, or parts decision carrying a
        # `disagreement` block is D34 in one line of code: PdM's calibration monitor reads
        # that block, and an RMC's manning shortfall becomes evidence the model over-predicted.
        require(d.disagreement is None, "deferral.non_disagreement_must_not_assert_disagreement")
```

**No default on `deferral_reason_class`, and no free-text-only path.** A defaulted `risk_disagreement` manufactures the bias D34 describes; a defaulted `capacity` discards real disagreement that would have corrected the model. Either default is a silent, directional, unrecoverable error, so the field is required and unset is a `422`. `reason_narrative` is additional colour and is never parsed to infer the class.

Full handling, including who consumes which class, is §8.

### 3.6 `Availability`

```
Availability {
  availability_id             uuid PK
  asset_id
  availability_type           enum { CMAV | SRA | DSRA | EDSRA | ROH | continuous_maintenance }
  window                      { start, end }
  executing_activity          { activity_uic, activity_type }   # RMC, IMA, depot, ship's force
  capacity[]                  { skill_class, available_man_hours, calendar_bounds }
  ofrp_phase                  enum { maintenance | basic | integrated | sustainment | deployed }
  blackout_windows[]          { start, end, reason }
  status                      enum { planned | committed | executing | closed }
  version                     int
}
```

[06 §7](../architecture/06-demo-decisions-and-assumptions.md) fixes the demonstration at **6 availabilities across the fleet over 24 months, including 1 DSRA**. Capacity modelling fidelity is [04 §6](../architecture/04-subapplication-architectures.md)'s Phase 3 question ("whether the demonstration includes RMC capacity modeling or treats capacity as unconstrained"); this build **models capacity**, at `(skill_class, calendar)` granularity, because an optimizer with unconstrained capacity has no binding constraint to explain and the explanation requirement (§4.4) becomes vacuous.

### 3.7 `WorkPackage` — carrier of the saga state

```
WorkPackage {
  work_package_id             uuid PK
  availability_id             uuid
  optimizer_run_id            uuid            # the run that produced it. Required
  candidate_ids[]             uuid[]
  input_watermark             jsonb           # §4.1. Persisted, republished in the explanation
  saga_state                  enum            # §4.5. THE reservation protocol state
  reservation_intent_id?      uuid            # → reservation_set. At most one non-terminal
  replan_generation           int             # §4.6 convergence counter
  superseded_by_package_id?   uuid
  constraint_satisfaction_summary  jsonb
  approved_by?, approved_at?, approval_authority_class?
  version                     int
  classification, correlation_id, created_at, monotonic_seq
}
```

### 3.8 `ReservationSet` — the client-side projection of what Supply confirms

**Supply owns reservations. This is a projection, and the distinction is load-bearing.**

```
ReservationSet {
  reservation_intent_id       uuid PK         # CLIENT-minted, BEFORE the call. The Idempotency-Key.
                                              # NOT a release handle — see §4.5.4 rule R2
  reservation_set_id?         uuid            # SUPPLY's identifier. The ONLY release handle.
                                              # Null until learned. §4.5.4 R2
  work_package_id             uuid            # sent as `for_work_package_id`
  asset_id                    uuid            # REQUIRED by Supply; a set serves one asset [26 §3.3]
  lines[]                     { line_ref, niin, location_id, quantity,
                                acceptable_condition_codes[], purpose_code?,
                                for_work_order_id?, expected_stock_epoch,
                                lead_time_days? }        # lead_time is LOCAL, not sent
  fence                       text            # "strict" ALWAYS. §4.1.1
  state                       enum            # mirrors the saga state for this intent
  -- expiry: two representations, deliberately
  supply_expires_at?          timestamptz     # Supply's TTL, MIRRORED FOR DISPLAY ONLY
  monotonic_deadline          int             # derived at receipt. THE timer.  [D29]
  extend_count                int             # Supply caps at 8 [26 §2.6]. §4.5.5
  attempt_count               int
  last_attempt_monotonic      int
  confirmed_event_id?         uuid            # from reservation_set.confirmed
  released_event_id?          uuid            # from reservation_set.released
  release_cause?              text
  terminal_reason?            text
}
```

**Field-level correspondence with Supply's request, because rev 1 guessed four of these wrong.** [26 §3.3](26-supply.md) is the authority; the mapping is stated so the adapter is not written from memory:

| Scheduling | Supply's request field | Rev 1's error |
|---|---|---|
| `reservation_intent_id` | `Idempotency-Key` **header only** | Rev 1 sent it as a `client_reference` body field. **No such field exists** |
| `work_package_id` | `for_work_package_id` | Named `work_package_id` |
| `asset_id` | `asset_id`, **required** | Omitted entirely |
| `lines[].line_ref` | `line_ref`, unique within the request | Absent; Supply `422`s `duplicate-line-ref` |
| `lines[].location_id` | `location_id` (uuid) | Sent as an optional `location` |
| `lines[].acceptable_condition_codes` | same, defaults `["A"]` | Sent a singular `condition_code` |
| `lines[].expected_stock_epoch` | required under `fence: "strict"` | Absent; Supply `422`s `fence-requires-epoch` |
| — | `interchangeable_group_ref` | **Not a Supply field.** Substitution is resolved by Scheduling *before* the call (§4.5.2) |

`max_lines` is **250** by default ([26 §3.3](26-supply.md)). A package exceeding it is split into multiple sets by availability slot, and each set is an independent saga — a package is not atomic across sets, so the split point is chosen so that a rejected set is independently replannable.

Four properties, each closing a specific way this goes wrong:

- **`supply_expires_at` is never used for a local timing decision.** Every timer — reattempt backoff, TTL-before-approval, reaper eligibility — reads `monotonic_deadline`. The STIG-mandated backward clock step (`makestep 1 -1`, V-260520) fires at reconnection, and "a wall-clock backoff loop storms or hangs the instant a step lands" [03 §5.4](../architecture/03-integration-contracts.md) `[D29]`. A lint rule forbids arithmetic on `supply_expires_at` outside the presentation layer.
- **The HTTP response is a fast path; `reservation_set.confirmed` is the authority.** A `201` with no corroborating event inside the declared bound resolves to `RESERVATION_INDETERMINATE`, not `RESERVED` (§4.5). Trusting the response alone reintroduces the orphan by a narrower window.
- **`lead_time_days` and `condition_code` are carried because the optimizer depends on them.** D6 notes "`lead time` is named as a hard constraint but exists in no Supply event or operation"; [03 §6](../architecture/03-integration-contracts.md) rev 2 adds `lead_time` and `condition_code` to `part_availability.changed` and `GET /lead-times` to Supply's required surface `[D24]`. If a substituting Supply implementation omits them, the constraint in §4.3 is unsatisfiable and the optimizer must refuse to solve rather than solve without it. Note the direction: `lead_time_days` is an **input to the solve**, held locally, and is never sent on the reservation — Supply does not take it.
- **`reservation_set_id`, not `reservation_intent_id`, is the release handle.** This is the correction rev 1 got backwards and it is load-bearing enough to have its own rule (§4.5.4 R2). Supply's `DELETE` is by *Supply's* identifier ([26 §3.9](26-supply.md)); there is no release-by-client-key operation, and rev 1's assumption that `{id}` would accept a client reference was wrong. The recovery path for "we hold something and do not know its id" is §4.5.5, and it works without any change to Supply.

### 3.9 `Proposal` — `work_candidate` and `interval_change`

Schema fixed by [03 §7.2](../architecture/03-integration-contracts.md); the Python model is `packages/canonical-schemas` ([10 §4.7](10-shared-packages.md)). Scheduling is the owning sub-application for two kinds, and must therefore set and re-validate `authority_class` and `blast_radius` from the [03 §7.2.1](../architecture/03-integration-contracts.md) table.

| `kind` | `item` / `asset` | `class` | `fleet` |
|---|---|---|---|
| `work_candidate` | `maintainer` or `planner` | `planner` | `fleet_authority` |
| `interval_change` | `planner` | `fleet_authority` + dual control | `fleet_authority` + dual control |

**`blast_radius` is derived from what the payload mutates, never from what the proposer declares.** [ESTABLISHED HERE], and it is the substance of D16's "authority-versus-blast-radius check":

```python
# src/fathom_maintenance/services/proposals.py
def derive_blast_radius(kind: ProposalKind, payload: dict) -> BlastRadius:
    if kind is ProposalKind.WORK_CANDIDATE:
        # A work candidate names one installed item, or one asset's item set, or a
        # class-wide campaign. Scope follows the referenced identity set.
        if payload.get("installed_item_id"):            return BlastRadius.ITEM
        if payload.get("asset_id"):                     return BlastRadius.ASSET
        if payload.get("class_id"):                     return BlastRadius.CLASS
        return BlastRadius.FLEET

    if kind is ProposalKind.INTERVAL_CHANGE:
        # THE TRAP. An MRC is a CLASS-level artifact. Changing the MRC changes the
        # periodicity for every hull in the class, so the blast radius is `class`
        # EVEN IF the proposal was raised from one hull's screen and declares itself
        # item-scoped. Only a hull-local deviation record is `asset`.
        target = payload["interval_target"]
        if target["kind"] == "pms_requirement":                     # the MRC itself
            return BlastRadius.CLASS
        if target["kind"] == "asset_local_deviation":
            return BlastRadius.ASSET
        raise ValidationError("interval_change.unknown_target_kind")
```

An `interval_change` scoped `class` therefore requires `fleet_authority` **and** dual control. Accepting a proposer-declared `item` scope on a change to a class-wide MRC is precisely the case [03 §7.2](../architecture/03-integration-contracts.md) describes: "an `interval_change` suppressing a preventive task across a class is not the same act as confirming an anomaly tag, and must not be adjudicable by the same authority."

**Validation rules at the API boundary, per [03 §9](../architecture/03-integration-contracts.md) item 2 — enforced regardless of what an agent proposed or why:**

| Rule | Kind | Behaviour on failure |
|---|---|---|
| The `installed_item_id` must be present in the **current** baseline | `work_candidate` | `422 urn:fathom:problem:maintenance:item-not-in-baseline` |
| The interval delta must fall within a bounded range — **[PLACEHOLDER — Phase 3 SME]** ±25% of the current interval | `interval_change` | `422 urn:fathom:problem:maintenance:interval-delta-out-of-bounds`. **Rejected on validation, before authority is even consulted**: an out-of-bounds change is not a thing a sufficiently senior person may approve, it is a thing that must be raised as a PMS change through PMS authority |
| `evidence[]` non-empty, and a proposal resting solely on `source_trust != program` is flagged to the adjudicator | both | `422` if empty; flag if non-program |
| Re-validation at adjudication against current configuration; reject on superseded `baseline_epoch` or elapsed `valid_until` | both | `409 urn:fathom:problem:maintenance:proposal-stale` |
| Adjudication requires `POST /proposals/{id}/claim` then `If-Match` on the claimed ETag | both | `412` on a stale ETag; `409` on an unclaimed adjudication |

`authority_class` is set at creation from the table and **re-derived and re-checked at adjudication**, because the scope may have been corrected in between ([03 §7.2.1](../architecture/03-integration-contracts.md)). This resolves [10 §11](10-shared-packages.md)'s **OQ-13** for Scheduling's two kinds: the vocabulary is now defined, so D16's authority check is implementable, and it is implemented here rather than typed as an opaque string.

### 3.10 `PmsRequirement`

```
PmsRequirement {
  pms_requirement_id          uuid PK
  mrc_ref                     text            # Maintenance Requirement Card reference
  applies_to                  { class_id?, niin?, equipment_family?, eic_prefix? }
  periodicity_basis           enum { calendar | usage }
  periodicity_value, periodicity_unit         # days | steaming_hours | eoh | cycles | dives
  covered_failure_modes[]      { lineage_id, taxonomy_version }   # for the §3.2.2 merge test
  skill_class, estimated_man_hours, required_parts[]
  interval_policy_version     text            # bumped by an approved interval_change
  superseded_by?              uuid            # append-only versioning
  asset_local_deviations[]     { asset_id, periodicity_value, authority_ref }
}
```

`eic_prefix` is matched **by prefix, never by equality** — [08 §2.6](../architecture/08-standards-alignment.md) via [12 §2.9](12-reference-data-taxonomy.md): "Where the EIC is known to more than four digits, it should be recorded at that level," so a record may carry 4 characters or 7 and equality silently drops the coarse ones.

### 3.11 Purge path

Per [03 §13](../architecture/03-integration-contracts.md) and [09 §8.4](09-monorepo-and-conventions.md), each store declares whether it is legally immutable or operationally append-only:

| Store | Status | Purge mechanism |
|---|---|---|
| `maintenance_action_record` | **Operationally append-only** — a 3-M documentation record, not a legally immutable one | Crypto-shredding the per-classification KEK ([11 §10.1](11-outbox-sync-library.md)) plus `purge_by_selector`. Row-level deletion is available to the declared purge protocol *only*, never to the application role |
| `deferral`, `optimizer_run`, `candidate_disposition` | Operationally append-only | Same |
| `work_order`, `work_candidate`, `work_package`, `availability`, `pms_requirement`, `reservation_set` | Mutable | Ordinary deletion under the purge protocol |
| Outbox / inbox / quarantine | Per [11 §10.1](11-outbox-sync-library.md) | Library-provided |

**"Append-only" is never cited as a reason a spillage cannot be remediated** `[D15]`.

---

## 4. The scheduling optimizer

Component layout under `src/fathom_maintenance/services/optimizer/`:

```
optimizer/
├── watermark.py        # §4.1  input watermark + consistent snapshot + staleness refusal
├── consequence.py      # §4.2  reference-class → expected consequence conversion
├── admission.py        # §4.3  candidate admission filter (incl. the policy-frozen holdout)
├── model.py            # §4.3  CP-SAT model construction. Constraints as data
├── solve.py            # §4.3  solve, deterministic
├── explain.py          # §4.4  dispositions for EVERY candidate, included and excluded
├── reservation_saga.py # §4.5  the two-phase reservation protocol with compensation
└── convergence.py      # §4.6  replan generation bounds, D20
```

The order is the pipeline order, and the pipeline is: **watermark → convert → admit → solve → explain → (create package) → reserve → confirm → approve → publish.** No step may be skipped, and `solve` never reaches the network.

### 4.1 Staleness bound and the input watermark — D6's first half

D6: "The optimizer has neither a consistent snapshot nor atomic reservation. It solves over a stale non-atomic mixture." [03 §5.2](../architecture/03-integration-contracts.md) states the remedy as a contract term: "Any computation with a correctness dependency on freshness declares a staleness bound and refuses to run outside it — **the scheduling optimizer in particular** `[D6]`."

**Consistent snapshot.** Every read model the optimizer touches lives in Scheduling's one database (obligation 13), which makes the snapshot free and unambiguous: the watermark build and all solver input reads execute inside **one `REPEATABLE READ` transaction**. Inputs are materialized into an in-memory problem instance, the transaction commits, and the solve runs outside it. A solve that read a second time, after commit, would be solving over a mixture again — so the model builder takes the materialized instance and has no database handle at all. That is a constructor-level guarantee, not a discipline.

```python
@dataclass(frozen=True)
class SourceWatermark:
    source: str                    # "pdm.prediction" | "supply.part_availability" | ...
    last_applied_event_id: UUID | None
    last_applied_seq: dict[str, int]      # {producer_node: monotonic_seq}
    lag_seconds: float                    # from the inbox, measured monotonically
    bound_seconds: float                  # declared, per source, in values.yaml

@dataclass(frozen=True)
class InputWatermark:
    snapshot_txid: int
    solved_at_monotonic: int
    sources: tuple[SourceWatermark, ...]
    baseline_epoch_per_asset: Mapping[UUID, int]
    stock_epoch: Mapping[tuple[str, UUID], int]   # (niin, location_id) -> epoch. §4.1.1
    conversion_version: str               # §4.2, from fathom_schemas.decision
    solver_version: str
    seed: int
```

#### 4.1.1 `stock_epoch` — the snapshot the optimizer solved against, carried into the reservation

Supply's `POST /reservation-sets` takes `fence: "strict"` and **requires `expected_stock_epoch` on every line** ([26 §3.3](26-supply.md)). That field is not an implementation detail of Supply's — it is the other end of D6's consistent-snapshot requirement, and Scheduling is the only party that can supply it correctly.

The mechanism: the optimizer records, inside the §4.1 snapshot transaction, the `stock_epoch` of every `(niin, location_id)` its `rm_part_availability` read model used. Those epochs are persisted on `optimizer_run.input_watermark` and replayed as `expected_stock_epoch` when the package reserves. **If stock moved between the solve and the reservation, Supply's fence rejects the set rather than granting a hold against a position the optimizer never saw.** That converts a stale-read race into a clean `RESERVATION_REJECTED` and a bounded replan (§4.6), which is the outcome D6 wants — the alternative, `fence: "none"`, would reserve successfully against a changed position and produce a plan whose feasibility was never actually verified.

**A rejection on the fence is therefore a correct outcome and must not be retried unchanged.** It enters generation `g+1` as a refreshed availability read, exactly like a failed line under §4.6 rule 2. Retrying with the same epoch would loop forever; retrying with `fence: "none"` to "make it work" is the single most tempting way to reintroduce D6 after it has been fixed, and it is on the §14 DO-NOT list for that reason.

**Refusal conditions.** All five are `409` with distinct problem types, all increment `fathom_staleness_refusals_total{reason}`, and none is a warning:

| # | Condition | Problem type suffix | Why refusal beats degradation |
|---|---|---|---|
| 1 | Any source's `lag_seconds > bound_seconds` | `staleness-bound-exceeded` | A plan built on a week-old availability picture reserves stock that is gone |
| 2 | Any in-scope asset has a **blocked antecedent** — an event held pending an unapplied `configuration.baseline_changed` ([11 §3.5](11-outbox-sync-library.md)) | `antecedent-unresolved` | The configuration is known to be in flux; planning against either side of it is guessing `[D3, D4]` |
| 3 | Any consumed prediction is in `invalidated` state | `prediction-invalidated-in-scope` | "Silent staleness after a component replacement is the failure mode most likely to destroy operator trust permanently" ([04 §4](../architecture/04-subapplication-architectures.md)) |
| 4 | Supply's required lead-time surface is unavailable or returns no `lead_time` for an in-scope NIIN | `lead-time-unavailable` | Lead time is a **hard** constraint (§4.3). Solving without it produces a plan that cannot execute, which is worse than no plan `[D6, D24]` |
| 5 | `dispersion_ms` on any in-scope source's `sync_quality` exceeds the declared epsilon, forcing causal-only ordering | `clock-dispersion-exceeded` | 03 §5.4: beyond that epsilon "forbids any timestamp arbitration". Windows are wall-clock quantities; planning them under untrusted time is not defensible |

Declared bounds — **[PLACEHOLDER — Phase 3 SME]**, in `values.yaml` under `app.config.stalenessBounds`, seconds:

```yaml
stalenessBounds:
  pdm.prediction:                 86400   # daily scoring cadence for tiers 0-1 [06 §7]
  pdm.criticality_tier:          604800
  supply.part_availability:        3600   # the tightest bound: it gates reservation feasibility
  supply.requisition:              3600
  supply.allowance_shortfall:     86400
  registry.configuration_baseline:  900   # correctness-critical; epoch fencing depends on it
  telemetry.usage_counter:        86400
  fleet-status.casrep_risk:        3600
  failure-intel.causal_finding:   604800
```

`GET /readyz` reports each source's lag against its bound, and the optimizer's own readiness is `degraded` (not failed) while any bound is exceeded — the service is functioning in a defined mode ([11 §9.1](11-outbox-sync-library.md)).

The watermark is persisted on `optimizer_run` and republished in the explanation, which makes a solution reproducible: same watermark, same seed, same solver version, byte-identical solution (§11.5).

### 4.2 The decision-theoretic conversion — D7 and D19

[03 §7.1](../architecture/03-integration-contracts.md), the note this sub-application is the primary consumer of:

> **`reference_class` replaces cross-tier probability comparability.** A tier-0 population rate and a tier-3 item-conditional probability can each be perfectly calibrated and remain incomparable. Consumers do not compare `p_failure` across reference classes; **the scheduling optimizer applies a per-class decision-theoretic conversion to expected consequence** `[D7]`.

[06 §3](../architecture/06-demo-decisions-and-assumptions.md): "The scheduling optimizer converts to **expected consequence** per reference class rather than comparing raw probabilities. Consequence weights come from equipment criticality, which the Registry already carries."

This is the correction Scheduling exists to apply, because Scheduling is the only consumer whose objective function trades risk **across a mixed-tier population**: one availability contains tier-0 valves and tier-3 pumps, and the optimizer must rank them against each other. Fleet Status renders; Supply provisions; only Scheduling *compares*.

#### 4.2.1 Where the conversion lives — **[RC-1 CLOSED: Scheduling does not implement it]**

**Rev 1 assumed Scheduling might own this arithmetic. It does not.** [22 §7](22-pdm.md) specifies the conversion and states the ownership explicitly: *"This section does, and PdM owns it, because the reference-class semantics being converted are PdM's."* Rev 1's reconciliation table (below, retained as §4.2.4) called the shared-library outcome the preferred one; that is the outcome, so **`optimizer/consequence.py` contains no conversion arithmetic of its own.** Rev 1's James–Stein shrinkage formulation is **deleted**, not deprecated — PdM's epistemic-interval mechanism (below) does the same job by a different and better-specified route, and keeping a second implementation alive is exactly the "nine transcriptions produce nine subtly different conversions" failure [22 §7.1](22-pdm.md) cites [10 §1.1](10-shared-packages.md) about.

**One implementation, two access paths** ([22 §7.1](22-pdm.md)):

| Path | Use in Scheduling |
|---|---|
| `fathom_schemas.decision.expected_consequence(...)` in `packages/canonical-schemas` | **The path the optimizer uses.** A pure function, no I/O, callable inside the §4.1 snapshot transaction and on the solve path |
| `POST /api/v1/pdm/expected-consequence` | **Not used on the solve path.** A synchronous PdM call inside a solve would violate 03 principle 2 and make the optimizer's availability a function of PdM's. Available for operator-facing "what would this score now" reads only |

`optimizer/consequence.py` is therefore a thin adapter, and its whole job is to assemble PdM's three inputs correctly:

```python
# src/fathom_maintenance/services/optimizer/consequence.py
from fathom_schemas.decision import (
    expected_consequence, ExpectedConsequence, RiskPosture, UncalibratedAndUnrated,
)

def score(cand: WorkCandidate, *, window_start, weights, calendar) -> ExpectedConsequence:
    """Assemble PdM's inputs. Compute NOTHING that PdM's function computes."""
    return expected_consequence(
        cand.prediction,                                  # the FailurePrediction, verbatim
        consequence=weights.for_item(cand),               # from Registry criticality. §4.2.3
        operating_fraction=calendar.operating_fraction(   # planned operating / calendar days
            cand.asset_id, until=window_start),
        risk_posture=weights.posture_for(cand),           # NEUTRAL | AVERSE. §4.2.3
    )
```

**The returned shape**, per [22 §7.2](22-pdm.md) — Scheduling reads these fields and adds none:

```python
class ExpectedConsequence(FathomModel):
    p_event_horizon:  float     # on a COMMON basis across reference classes
    p_event_lower:    float     # epistemic interval, widened by fallback_level and cell size
    p_event_upper:    float
    basis:            Basis     # item_conditional | class_rate_converted
    consequence_value: float    # C, in the optimizer's cost units
    expected_consequence: float # THE only rankable quantity
    timing_basis:     TimingBasis   # rul_quantiles | mean_residual_life_from_rate | none
    timing_p10: float | None    # None unless timing_basis is rul_quantiles
    timing_p50: float | None
    conversion_version: str
    inputs_digest:    str
```

**The conversion, per reference class** ([22 §7.3](22-pdm.md)) — restated here only so a Scheduling implementer can recognise a wrong answer, never to be re-implemented:

| Case | `reference_class` | `p_event_horizon` | `timing_basis` |
|---|---|---|---|
| A | `item` | `p_failure` (already item-conditional over the horizon) | `rul_quantiles`; `timing_p10/p50` from `rul` |
| B | `niin_fleet`, `equipment_family`, `class_estimate` | `1 − exp(−population_hazard_rate × h_op)` where `h_op = horizon_days × operating_fraction` | `mean_residual_life_from_rate`; `timing_p50 = 1/rate`, **`timing_p10 = None`** |
| C | `p_failure` null (below the n≥50 gate) | Case B's arithmetic, unchanged. Raises `UncalibratedAndUnrated` only if the rate is *also* absent, which the schema forbids | as B |

Two details in that table are Scheduling's responsibility to get right, because PdM cannot check them:

- **`operating_fraction` is Scheduling's input, and omitting it overstates the horizon by ~50%.** [22 §7.3](22-pdm.md): the hazard rate is per *operating* day, the planning horizon is *calendar* days, and converting one against the other without the factor is "a large silent error in the optimizer's favour" — it would make every class-rate item look less urgent than it is. Scheduling sources it from the mission calendar where planned operations exist and otherwise uses the documented **0.667** sea-going tempo approximation ([07 §5.5](../architecture/07-navy-data-systems.md), [13 §11.1](13-synthetic-data-generator.md)), which is the same constant that appears in the MTBF formula of §5.8.
- **`timing_p10 = None` must be propagated, never defaulted.** It is D19's shape constraint carried into the decision layer: a class rate implies a mean residual life and does not imply a 10th percentile of an item's residual life. Constraint C2's window arithmetic reads `timing_p50` in that case and a lint rule forbids `timing_p10 or <default>`.

**Risk posture is what closes D7's specific prediction.** [22 §7.4](22-pdm.md): under `AVERSE`, `expected_consequence = p_event_upper × consequence_value`; under `NEUTRAL`, `p_event_horizon × consequence_value`. A tier-0 item's class rate carries a wide epistemic interval, so `AVERSE` lets it "compete on the risk it might actually pose rather than on a population average that is confidently too low for the worst items in the class," while a tier-3 item's sharp interval gains almost nothing from the same posture. **The asymmetry in the correction matches the asymmetry in the defect** — which is why rev 1's shrinkage factor was not merely redundant but pointed the wrong way: shrinking toward a broader base rate moves a thin high-hazard cell *down*, deepening exactly the tier-0 starvation D7 predicts.

#### 4.2.2 Four hard rules, enforced in code

1. **A NULL `p_failure` is never read as zero.** [03 §7.1](../architecture/03-integration-contracts.md): "A consumer that treats a missing `p_failure` as zero, rather than as 'uncalibrated,' reintroduces the comparability defect this field exists to prevent." **The mechanism that makes this impossible for the optimizer is PdM's function, not Scheduling's care** ([22 §6.3](22-pdm.md)): it accepts a null `p_failure`, derives the consequence from `population_hazard_rate`, and raises `UncalibratedAndUnrated` only when both are absent. Scheduling's obligation is to let that exception propagate: the candidate is admitted with `disposition = unscorable`, `reason_code = unscorable_no_calibrated_rate`, and is **surfaced to the planner** rather than dropped. An unscorable high-criticality item is exactly the item a planner must see. Catching the exception and substituting a number is the one way to reintroduce the defect from Scheduling's side.
2. **The optimizer ranks on `expected_consequence` and on nothing else** ([22 §7.5](22-pdm.md) rule 1). Not `p_failure`, not `p_event_horizon`, not `confidence`, not `tier`. "A `FailurePrediction` reaching an optimizer objective function without passing through this conversion is the D7 defect." Enforced statically: a lint rule fails the build if `p_failure` is referenced anywhere under `optimizer/` outside `consequence.py`'s adapter call.
3. **`rul` and `timing_*` inform *when*, never *how much*** ([22 §7.5](22-pdm.md) rule 2, `[D19]`). They enter as window constraints (C2), never as ranking magnitude. No `rul` is read where `reference_class` is not item-conditional; the field is absent by contract and reading a default would fabricate a residual-life distribution for a memoryless population.
4. **Never branch on `tier`.** `tier` is transparency only ([03 §7.1](../architecture/03-integration-contracts.md)). A lint rule forbids `tier` appearing in any conditional inside `optimizer/`; lint rule FTH006 ([22 §7.5](22-pdm.md) rule 4) flags a `tier` comparison globally. Branching on `reference_class` is required, and `comparable_with()` ([10 §4.6](10-shared-packages.md)) remains the only sanctioned raw-field comparison.
5. **`fallback_level` is not folded into the ranking as if it were confidence.** PdM's function already consumes it, in the one place it belongs — widening the epistemic interval via `fallback_multiplier` ([22 §7.4](22-pdm.md), **[PLACEHOLDER P-16]**). Scheduling multiplies it into nothing. It enters Scheduling's output only as a presentation field on the disposition and, optionally, as a tie-break, because "one scalar cannot carry both sharpness and epistemic reference-class depth and remain orderable."
6. **`conversion_version` and `inputs_digest` are recorded on the run** ([22 §7.5](22-pdm.md) rule 3). A scheduling decision must be reconstructible and the conversion is part of the decision. Both are persisted on `optimizer_run` and echoed in every `CandidateDisposition`, which is what makes §11.5's determinism test meaningful across a PdM library upgrade: the version changes, so the difference is attributable.
7. **A `research_only` prediction never reaches the conversion.** [22 §7.5](22-pdm.md) rule 5: the served operation returns `422` for one, "because the conversion's only purpose is to feed action, and the holdout stratum's whole point is that it is not acted upon." Scheduling's admission filter (§4.3) excludes holdout items from prediction-driven candidates *before* scoring, so the case should be unreachable; if the library raises it anyway, that is a holdout-leak alarm and the run aborts rather than degrading.

#### 4.2.3 Consequence weights

Three bands, from `criticality_tier.assigned` and the Registry's criticality attributes: **[PLACEHOLDER — Phase 3 SME]** `mission_essential = 10.0`, `mission_degrading = 3.0`, `routine = 1.0`.

**The weights are Scheduling's input to supply, and this is settled rather than assumed.** [22 §1.2](22-pdm.md) is explicit that "PdM does not own consequence weights — §7's conversion takes them as an *input*… a weight table hard-coded in `services/pdm` would make a program judgment into a code constant." They originate in Registry criticality and Scheduling passes them, so the ownership chain has no gap and no duplication.

[06 §3](../architecture/06-demo-decisions-and-assumptions.md) assumption A8 rates the defensibility of these weights **LOW** and prescribes the exact treatment: "Use a coarse three-band criticality weighting for the demo, clearly labelled as illustrative, and make weight elicitation a Phase 3 workshop item." Consequently the weights are (a) in `values.yaml`, not code, (b) echoed in every explanation payload with `weights_are_illustrative: true`, and (c) rendered with that marker wherever an operator sees a ranking. A ranking whose weights are presented as authoritative is not credible to a planner and should not be.

**Risk posture is configured beside the weights, because it is the same kind of judgment.** [22 §7.4](22-pdm.md) **[PLACEHOLDER P-17]** sets the default as `AVERSE` for the highest consequence band and `NEUTRAL` otherwise, and says why it is a parameter rather than a formula: "it encodes how much the Navy is willing to spend to avoid an unlikely severe failure. Stating it as a posture parameter rather than burying it in a formula is what makes it reviewable." Scheduling therefore carries `riskPosture.byBand` in `values.yaml` and surfaces the posture in every explanation — a planner comparing two rankings must be able to see that one was produced under a risk-averse posture, because that, and not a change in the fleet, may be the entire difference between them.

#### 4.2.4 How RC-1 actually closed

Rev 1 enumerated four possible outcomes. **Two of them happened at once**, and recording which is not bookkeeping — it is the difference between a version bump and a silent change in fleet-wide ranking behaviour:

| Rev 1's anticipated case | Outcome |
|---|---|
| Shared library in `packages/canonical-schemas` | **Yes.** `fathom_schemas.decision`, beside `FailurePrediction` ([22 §7.1](22-pdm.md)). Rev 1 called this the preferred outcome and it is the one that landed |
| Also a served operation | **Yes**, `POST /api/v1/pdm/expected-consequence` — but *not* used on the solve path (§4.2.1) |
| Materially different functional form | **Yes.** PdM converts through the hazard rate with an `operating_fraction`, and expresses epistemic depth as an *interval plus a risk posture* rather than as rev 1's multiplicative shrinkage. Rev 1's own rule for this case was "adopts PdM's form," which is what §4.2.1 does |
| Calibration metadata only, conversion left to the consumer | No |

Because the functional form changed, `conversion_version` changes, and **no historical `optimizer_run` is recomputed** — each retains the version it was solved under. That is the property that keeps a library upgrade from being mistaken for a change in the fleet, and it is why the version is persisted on the run rather than read from the deployed package at report time.

### 4.3 The constraint model — **[PLACEHOLDER — Phase 3 SME]**

[04 §6](../architecture/04-subapplication-architectures.md) specifies the model's *character* — "Decision variables assign candidates to windows. Constraints include parts availability and lead time, executing-activity capacity, OFRP phase, deployment dates, system criticality, and prerequisite relationships between work items. The objective trades predicted casualty risk against cost and capacity" — and leaves formulation and solver selection to Phase 3 ("Optimizer formulation and solver selection, and whether the problem size at fleet scale admits exact solution or requires heuristics"). The following is a complete, runnable proposal, marked as a placeholder in its entirety.

**Solver.** Google OR-Tools **CP-SAT**. Rationale: the problem is a bounded assignment with integer capacity and precedence constraints, CP-SAT gives proofs of optimality and infeasibility cores at demonstration scale, and — decisively for §4.4 — an infeasibility core is directly renderable as an explanation. A MIP solver would serve equally; a hand-rolled heuristic would not, because it cannot say *why* a candidate was excluded.

**Admission filter (`admission.py`)**, applied before model construction:

| Filter | Effect | Source |
|---|---|---|
| `baseline_epoch` matches the asset's current epoch | else `withdrawn(baseline_superseded)` | 03 §5.4 |
| Prediction not `invalidated` | else `withdrawn(prediction_invalidated)` | 04 §4 |
| Installed item present in the current baseline | else `withdrawn(item_removed)` | 03 §9 item 2 |
| **Policy-frozen holdout**: an item with `holdout_member = true` is excluded from **prediction-driven** candidates only; its PMS and casualty candidates plan normally | `excluded(holdout_excluded)` | [06 §2](../architecture/06-demo-decisions-and-assumptions.md), [13 §10.3](13-synthetic-data-generator.md) |
| Unscorable (rule 1 of §4.2.2) | `unscorable`, surfaced to the planner, not modelled | 03 §7.1 |

> **The holdout is an admission filter, not a branch in the ranking logic.** [13 §10.3](13-synthetic-data-generator.md) is explicit about this, and the reason is that a ranking-stage branch leaks: a holdout item that survives admission and is then down-weighted has still been *treated* by the policy, which destroys the unconfounded stratum the holdout exists to provide. Excluding at admission, with a recorded reason, keeps the stratum clean and keeps the exclusion visible.

**Decision variables.** `x[c, w] ∈ {0,1}` — candidate `c` assigned to window `w`, where `w` ranges over the availability's schedulable slots plus one **deferral sink** `w_∞` representing "not in this availability". Exactly one assignment per candidate: `Σ_w x[c,w] == 1`.

**Objective (minimize).**

```
Σ_c Σ_w  x[c,w] · risk_cost(c, w)
  + λ_cost     · Σ_c Σ_w x[c,w] · cost(c)
  + λ_capacity · Σ_w overtime[w]
  + λ_churn    · Σ_c reassignment_penalty(c)      # stability across replan generations
```

where `risk_cost(c, w) = expected_consequence(c, exposure_window(now, w.start))` — the risk **accrued while waiting**, and `exposure_window(now, w_∞.start)` is the full planning horizon. This framing is what makes the output answer [04 §6](../architecture/04-subapplication-architectures.md)'s primary question — "whether an item survives the deployment or must enter the next availability work package" — rather than producing dates. Weights `λ_cost`, `λ_capacity`, `λ_churn`: **[PLACEHOLDER — Phase 3 SME]**.

**Constraints.**

| # | Constraint | Form |
|---|---|---|
| C1 | Capacity per `(availability, skill_class, calendar bucket)` | `Σ_c x[c,w] · man_hours(c, skill) ≤ capacity(w, skill) + overtime[w]` |
| C2 | **Parts availability with lead time** | `x[c,w] = 0` where `arrival_day(niin) > w.start` for any required NIIN, with `arrival_day` from on-hand, due-in, or `GET /lead-times`; interchangeable groups relax the NIIN to its group |
| C3 | Prerequisites | `x[c1,w1] = 1 ∧ x[c2,w2] = 1 ⟹ index(w1) ≤ index(w2)` |
| C4 | OFRP phase eligibility | `x[c,w] = 0` where the candidate's work class is not permitted in `w.ofrp_phase` |
| C5 | Deployment and blackout windows | `x[c,w] = 0` inside a blackout |
| C6 | Item-down mutual exclusion | two candidates requiring the same item out of service cannot share a slot |
| C7 | **Criticality floor** | a candidate whose `expected_consequence` exceeds `criticality_floor` must be assigned to a real window **or** deferred through §8's explicit path with recorded risk acceptance — it may not be silently assigned to `w_∞` |

C7 is the constraint that makes the deferral record honest: without it, the sink absorbs high-consequence work with no human signature, and the deferral evidence D34 depends on is never created.

**Determinism.** `num_search_workers = 1`, fixed `random_seed`, fixed `max_time_in_seconds`, fixed constraint insertion order. CP-SAT is only reproducible single-threaded, and reproducibility is a Definition-of-Done item (§15.8), so throughput is traded for it deliberately. At [06 §7](../architecture/06-demo-decisions-and-assumptions.md)'s scale — 12 assets, ~8,400 installed items, 6 availabilities — this is comfortable. **Production (~300 hulls) requires decomposition per availability and is explicitly out of scope for this build**; the Phase 3 question about fleet-scale exact solution is answered "not attempted", not "solved".

### 4.4 Explanation generation — every candidate, included and excluded

[04 §6](../architecture/04-subapplication-architectures.md): "Critically, every included and every excluded candidate carries a reason. A planner presented with an unexplained schedule will discard it and plan manually, which is the observed failure mode for optimization tools in this domain."

```
CandidateDisposition {
  optimizer_run_id, candidate_id
  disposition                 enum { included | excluded | deferred | unscorable | withdrawn }
  reason_code                 enum   # CONTROLLED VOCABULARY. Never free text
  window_assigned?            uuid
  expected_consequence?       ExpectedConsequence
  consequence_rank?           int
  binding_constraint?         enum   # which constraint bound, from the CP-SAT core
  slack?                      numeric
  counterfactual?             text   # "included if C1 capacity for skill_class MM
                                     #  increased by 14 man-hours"
  driver_disagreement?        jsonb  # carried through from the merge, §3.2.2
  fallback_level?             int
  weights_are_illustrative    bool   # always true while §4.2.3 stands
}
```

Reason-code vocabulary: `capacity_exhausted`, `parts_lead_time`, `parts_unavailable`, `prerequisite_unmet`, `ofrp_phase_conflict`, `deployment_blackout`, `availability_full`, `item_down_conflict`, `lower_expected_consequence`, `criticality_floor_deferred`, `baseline_superseded`, `prediction_invalidated`, `item_removed`, `unscorable_no_calibrated_rate`, `holdout_excluded`, `duplicate_of_merged_candidate`.

**Totality is asserted, not intended.** A run is invalid unless `count(dispositions) == count(candidates_in_scope)`; the assertion runs inside the same transaction that persists the run, and a mismatch aborts it. Without this, "every candidate carries a reason" degrades to "most candidates carry a reason", and the one silently dropped candidate is the one the planner needed.

**Where the reason comes from.** For `excluded` candidates the binding constraint is read from CP-SAT's **infeasibility core** for the pinned-inclusion sub-problem (assume `x[c,w] = 1`, re-solve, read the core), and the counterfactual from the constraint's slack. That is more expensive than an unexplained solve and it is not optional — it is the whole reason CP-SAT was chosen over a heuristic.

Served at `GET /work-packages/{id}/explanation`, `x-side-effects: none`, agent-eligible, `p95 < 4 s` per [06 §7](../architecture/06-demo-decisions-and-assumptions.md)'s explanation-decomposition budget.

### 4.5 The reservation protocol — D6's second half

D6, in full: "it solves over a stale non-atomic mixture, then reserves per-NIIN with no batch, no TTL, no two-phase confirm and no compensating release. **37 of 40 reservations succeed, the 38th fails, orphans persist and 37 spurious availability events degrade every other asset's planning.**"

The remedy has four parts, and all four are required: an atomic multi-NIIN reservation operation on Supply's side, a **client-minted intent identifier that is the idempotency key** (and a defined way to learn Supply's identifier, which is the release handle), a saga with named states and explicit compensation, and a reaper that re-drives any non-terminal state after a crash.

**Supply's half is built and its shape constrains ours.** [26 §3.2](26-supply.md) states the fix in the type system: *"`ReservationSet` has no `pending` state and no `partial` state."* States are `confirmed | consumed | released | expired` only, and `POST` returns `201 confirmed` or holds nothing at all — the infeasible response carries `reservation_set_id: null` explicitly so that *"a caller must not be able to read a set identifier out of a failure and then attempt to release it"* ([26 §3.7](26-supply.md)). Two consequences for this document:

- **There is no distributed transaction to join, and Scheduling must not invent one.** [26 §3.12](26-supply.md): *"Across the Scheduling↔Supply boundary, the protocol is a lease, not a transaction… The compensating action for a Scheduling crash after confirmation is TTL expiry — automatic, requiring no coordinator, no orchestrator state, and no liveness assumption about the crashed party,"* and *"any proposal to add one must first explain what property the TTL lease fails to provide."* This document adds none. The saga below is **local** bookkeeping over a remote lease, not a two-phase commit, and the phrase "two-phase" is avoided deliberately: phase two is a *corroboration*, not a commit.
- **The TTL is the backstop that makes every unrecoverable case bounded.** Where Scheduling cannot determine what it holds and cannot learn Supply's identifier, the hold expires on its own within `ttl_seconds`. Orphan *lifetime* is therefore bounded by construction even in the worst case, and the saga's job is to make orphan *existence* rare rather than to be the only thing standing between the fleet and a leak.

#### 4.5.1 The exact API call sequence

```
Scheduling                                                    Supply
──────────                                                    ──────
1. POST /api/v1/maintenance/work-packages/plan                 (no call. Solve is local, over the
   → optimizer_run_id, dispositions, explanation                snapshot of §4.1. 03 principle 2)

2. POST /api/v1/maintenance/work-packages
   { optimizer_run_id, availability_id }
   → work_package_id, saga_state = SOLVED

3. POST /api/v1/maintenance/work-packages/{id}/reserve
   ── in ONE local transaction, BEFORE any network call:
        mint reservation_intent_id = uuid4()
        INSERT reservation_set(reservation_intent_id, lines, state=RESERVING,
                               monotonic_deadline = now_monotonic() + reserve_timeout)
        UPDATE work_package SET saga_state=RESERVING, reservation_intent_id=…
        COMMIT                                    ← the intent exists before the risk does
   ── then, and only then:
        POST /api/v1/supply/reservation-sets  ───────────────▶  atomic, multi-NIIN, TTL
            Idempotency-Key: <reservation_intent_id>        ← the intent id travels HERE,
            X-Correlation-Id: <correlation_id>                and ONLY here
            { asset_id,
              for_work_package_id: <work_package_id>,
              ttl_seconds: 172800,
              fence: "strict",                              ← ALWAYS. §4.1.1
              lines: [ { line_ref, niin, location_id, quantity,
                         acceptable_condition_codes: ["A"],
                         purpose_code?, for_work_order_id?,
                         expected_stock_epoch } , … ] }      ALL lines or NONE
                                              ◀───────────────  201 { reservation_set_id,
                                                                      state:"confirmed",
                                                                      expires_at, lines[] }
                                                                 or 409 / 422 (NOTHING held;
                                                                    reservation_set_id: null)
                                                                 or 5xx / timeout (UNKNOWN)
   ── on 201: PERSIST reservation_set_id IMMEDIATELY, in its own committed transaction,
              before any further work.        ← this is the release handle. §4.5.4 R2

4. corroborate:  reservation_set.confirmed  ◀── fathom.supply.reservation_set.v1
   → saga_state = RESERVED
   → publish work_package.proposed  (carries reservation_set reference, per 03 §6)

5. POST /api/v1/maintenance/work-packages/{id}/approve      (planner, If-Match, authority
   ── requires saga_state == RESERVED and monotonic_deadline not elapsed            = planner)
   → saga_state = APPROVED
   → publish work_package.approved            ← ONLY here. 03 §6: "published only after
   → open WorkOrders, publish work_order.opened  reservation confirmation" [D6]

   compensation, any failure at 3 or 4, WHERE reservation_set_id IS KNOWN:
        DELETE /api/v1/supply/reservation-sets/{reservation_set_id}  ──────────▶
            Idempotency-Key: <fresh uuid>                            (204 if confirmed,
                                              ◀───────────────────    204 if already released
                                                                      /expired/consumed,
                                                                      404 if unknown)
                                                                     reservation_set.released
        → saga_state = RELEASED → REPLAN_REQUIRED

   compensation WHERE reservation_set_id IS NOT KNOWN:  §4.5.5
```

**Release is idempotent by intent, not merely by key** ([26 §3.9](26-supply.md)): a `DELETE` on a set already `released`, `expired`, or `consumed` returns `204` **and emits no second event**, because "emitting `reservation_set.released` twice for one set would be worse than an error: Scheduling's read model would restore availability twice." Scheduling therefore never needs to check state before releasing, and must not treat a `404` as a failure — a `404` means nothing is held, which is the outcome compensation exists to reach.

#### 4.5.2 Substitution is resolved before the call, not by Supply

Supply's line schema has no `interchangeable_group_ref` ([26 §3.3](26-supply.md)): a line names one `niin` at one `location_id`. Interchangeable groups therefore live entirely on Scheduling's side of the boundary — the optimizer relaxes a required NIIN to its group during constraint C2 (§4.3), and by the time the reservation is built **a specific NIIN has been chosen**.

This is the correct division and not a Supply gap. A group-valued reservation would require Supply to make a substitution decision, and the substitution decision is a maintenance-engineering judgment about whether a form-fit-function alternative is acceptable for *this* task — it depends on the candidate's scope, not on what happens to be in the storeroom. Pushing it into Supply would put an engineering judgment behind a stock query. What Scheduling records, so the decision is not lost, is the group it relaxed and the NIIN it chose, on the `CandidateDisposition` (§4.4); a substitution that a planner would have rejected is then visible in the explanation rather than discovered at the deckplate.

#### 4.5.3 Saga states

Persisted on `work_package.saga_state` and mirrored on `reservation_set.state`. Terminal states are marked ▪.

| State | Meaning | Exit |
|---|---|---|
| `SOLVED` | Solution persisted with watermark and explanation. **No external effect whatsoever** | → `RESERVING` on `/reserve`; ▪ `ABANDONED` on operator discard |
| `RESERVING` | Intent minted and committed; `POST` in flight or outcome not yet corroborated | → `RESERVED`, `RESERVATION_REJECTED`, or `RESERVATION_INDETERMINATE` |
| `RESERVED` | `201` **and** a matching `reservation_set.confirmed` | → `APPROVAL_PENDING` on publish of `work_package.proposed`; → `EXPIRED_UNAPPROVED` on deadline |
| `RESERVATION_REJECTED` | `409`/`422`: at least one line unsatisfiable. **Atomicity means nothing is held, so there is nothing to compensate** | → `REPLAN_REQUIRED`, with the failing lines recorded as generation-`g+1` constraints |
| `RESERVATION_INDETERMINATE` | Timeout, 5xx, connection loss, or `201` with no corroborating event inside the bound. **We do not know whether Supply holds stock, and we may not know its identifier.** The state D6 has no representation for | → `RESERVED` on late corroboration; → `RESERVING` on idempotent re-issue (§4.5.5 step 1, which also *learns the identifier*); → `RELEASE_PENDING` once the identifier is known; → `AWAITING_TTL_EXPIRY` when it cannot be learned |
| `AWAITING_TTL_EXPIRY` | Identifier unlearnable after `max_reserve_attempts` — Supply unreachable. **Bounded, not orphaned:** the lease expires on its own | → `RELEASED` on `reservation_set.released` (cause `expired`); → `RELEASE_PENDING` if the identifier is learned late |
| `RELEASE_PENDING` | Compensating `DELETE` issued against a **known** `reservation_set_id` | → `RELEASED` on `204`/`404` or `reservation_set.released` |
| `RELEASED` | Compensation confirmed. Nothing is held | → `REPLAN_REQUIRED` |
| `APPROVAL_PENDING` | Proposed to the planner; reservation held; TTL running on `monotonic_deadline` | → `APPROVED`; → `EXPIRED_UNAPPROVED` |
| `EXPIRED_UNAPPROVED` | TTL elapsed before approval; Supply auto-released and published `reservation_set.released` | → `REPLAN_REQUIRED`. **`work_package.approved` is never published from here** |
| `REPLAN_REQUIRED` | Feasible set has shrunk; a new generation is permitted | → new `optimizer_run` at `replan_generation + 1`, or ▪ `REPLAN_EXHAUSTED` |
| ▪ `APPROVED` | Committed. `work_package.approved` published; work orders opened | — |
| ▪ `REPLAN_EXHAUSTED` | Generation bound reached (§4.6). Operator-visible, fully explained | — |
| ▪ `ABANDONED` | Operator discard. **Requires a completed release first** — the transition from any state holding a reservation goes through `RELEASE_PENDING` | — |

#### 4.5.4 The seven rules that make orphans impossible

| # | Rule | The failure it forecloses |
|---|---|---|
| **R1** | **Persist before call.** The `RESERVING` row commits before the HTTP request is sent. The outbox covers events, not outbound commands, so the saga log is the command's durability | A crash between "decide to reserve" and "reserve" leaves no record, and the reservation Supply may have created has no owner. This is the classic orphan |
| **R2** | **The intent id is client-minted and is the `Idempotency-Key`. It is *not* a release handle.** Supply's `reservation_set_id` is the only release handle, and it is persisted the instant it is learned, in its own committed transaction, before anything else happens | Rev 1 assumed one value could do both jobs and it cannot: [26 §3.9](26-supply.md)'s `DELETE` is by Supply's identifier only. What makes an indeterminate outcome recoverable is instead **idempotent re-issue** — [26 §3.3](26-supply.md) guarantees that the same `Idempotency-Key` with the same body "returns the **original** `201` with the original `reservation_set_id`. No second set, no second event" — so re-issue is both safe *and* the mechanism by which the release handle is learned (§4.5.5). Persisting the id late, or only in memory, is the remaining way to orphan a set |
| **R3** | **At most one non-terminal intent per work package**, enforced by `CREATE UNIQUE INDEX … ON reservation_set (work_package_id) WHERE state NOT IN (terminal states)` | Two concurrent `/reserve` calls double-reserving the same package. A database constraint, not a mutex |
| **R4** | **Never loop per NIIN.** One `POST /reservation-sets` carrying every line. A lint rule fails the build if `reservation` appears inside a loop body in `reservation_saga.py`, and §11.3 asserts call counts | D6 verbatim: "reserves per-NIIN with no batch… 37 of 40 succeed, the 38th fails" |
| **R5** | **The event is the authority, the response is the fast path.** `RESERVED` requires both. `201` with no `reservation_set.confirmed` inside `confirm_corroboration_bound` → `RESERVATION_INDETERMINATE` | A `201` lost or fabricated on a retried proxy hop leaves the client believing it holds stock it does not, and the availability picture disagrees with the plan |
| **R6** | **A reaper re-drives every non-terminal state.** A background sweep (monotonic, every 30 s) selects `reservation_set` rows past `monotonic_deadline` in a non-terminal state and advances the saga. Idempotent, leader-elected, and it is the only thing that runs after a pod dies mid-saga | Every "we crashed at the worst moment" scenario. Without a reaper the saga is a best-effort convention |
| **R7** | **`work_package.approved` is published from `APPROVED` only**, and `APPROVED` is reachable only from `RESERVED`. Enforced by the state machine **and** by an event-tap conformance assertion (§11.3) | [03 §6](../architecture/03-integration-contracts.md): "`work_package.approved` — published only after reservation confirmation `[D6]`". Supply, Fleet Status, and Registry all act on that event; publishing it early commits the fleet to a plan whose parts are not held |

#### 4.5.5 Recovering from `RESERVATION_INDETERMINATE` without a client-key release

This is the subsection rev 1 did not need and rev 2 does, because Supply released by its own identifier rather than by the client's. **Three ordered mechanisms, none of which requires a change to Supply**, and the last of which cannot fail:

**Step 1 — idempotent re-issue, which is also the identifier lookup.** Re-`POST` with the *same* `Idempotency-Key` and a byte-identical body. Per [26 §3.3](26-supply.md) this returns the original `201` and the original `reservation_set_id`, creating no second set and emitting no second event. The identifier is persisted and the saga proceeds to `RESERVED` or `RELEASE_PENDING` as appropriate. The body must be byte-identical: a differing body with the same key returns `422 idempotency-key-reuse`, so the request is serialised canonically once and stored on the `reservation_set` row rather than rebuilt from the package at retry time — a package that was re-solved in between would otherwise produce a different body and lock the key permanently.

**Step 2 — the change feed, if re-issue itself cannot complete.** `GET /reservation-sets?asset_id=&state=confirmed&changed_since=` ([26 §7.4](26-supply.md)) and match on `for_work_package_id`, which Supply persists ([26 §2.6](26-supply.md)) precisely as "Scheduling's reference, opaque here." R3's at-most-one-non-terminal-intent invariant is what makes the match unambiguous: there can be no second confirmed set for the same package to confuse it.

**Step 3 — the TTL, which always terminates.** If Supply is unreachable, the saga enters `AWAITING_TTL_EXPIRY` and the hold lapses within `ttl_seconds` ([26 §3.8](26-supply.md)), emitting `reservation_set.released` with cause `expired`. This is [26 §3.12](26-supply.md)'s stated design intent — the compensating action for a crashed or partitioned requester is expiry, "requiring no coordinator, no orchestrator state, and no liveness assumption about the crashed party."

> **Why this is stronger than rev 1's proposed contract change, not weaker.** Rev 1 declared release-by-client-key "a hard requirement, not a preference," on the reasoning that a client cannot release what it cannot name. That reasoning had a hole: it assumed the client's only source of the name is the lost response. Idempotent re-issue is a second source, the change feed is a third, and the TTL bounds the case where all sources fail. The result needs **no cross-service change**, which matters because a protocol whose correctness depends on a counterparty amending its API is not a protocol that is fixed today. `ttl_seconds` is set to **48 h** (§12.1) rather than something shorter *because* it is the backstop: it must comfortably exceed a planner's approval window while still bounding the worst-case orphan lifetime to something an operator can be told.

#### 4.5.6 Holding a reservation across a slow approval — `extend`, and its cap

A planner's approval is a human act on a human timescale, and a TTL long enough to accommodate the slowest of them would defeat the point of having one. [26 §7.4](26-supply.md) provides `POST /reservation-sets/{id}/extend`, which exists for exactly this: without it a package awaiting adjudication must "either hold an unbounded reservation — defeating the TTL — or release and re-reserve, reintroducing the race at the exact moment of approval."

| Rule | Detail |
|---|---|
| When | In `APPROVAL_PENDING`, when `monotonic_deadline` is within `extend_lead_seconds` (**[PLACEHOLDER — Phase 3 SME]** 3600) |
| Requires | `If-Match` on the set's ETag, `Idempotency-Key`, `{ ttl_seconds }` |
| Cap | `extend_count ≤ 8`, enforced by Supply's CHECK ([26 §2.6](26-supply.md)) "so an extension loop cannot become an unbounded hold by another route" |
| On cap reached | The package moves to `EXPIRED_UNAPPROVED` **at the deadline**, and the planner is notified *before* it does. A silently-expiring package is how a planner learns not to trust the tool |
| No re-confirmation | `reservation_set.confirmed` is **not** re-emitted — "an extension changes expiry, not confirmation" ([26 §7.4](26-supply.md)). The saga must not wait for a corroborating event it will never receive; `monotonic_deadline` is recomputed from the `200` response's `expires_at` |
| On `409 reservation-set-expired` | The set **is not resurrected** — resurrection "would require re-verifying every line's availability, which is a new reservation set by definition." → `EXPIRED_UNAPPROVED` → `REPLAN_REQUIRED` |

#### 4.5.7 Two gaps in the catalog, flagged rather than papered over

- **[OPEN OQ-2] There is no `work_package.retracted` event.** `EXPIRED_UNAPPROVED` and `REPLAN_REQUIRED` after a published `work_package.proposed` leave consumers (`supply`, `fleet-status`) holding a proposal that will never be approved. Interim position: the superseding proposal carries `supersedes_work_package_id`, and consumers treat a superseded proposal as retracted. This is weaker than an explicit event, because a consumer that never receives the successor never learns. Raised for a catalog addition.
- **[OPEN OQ-3] `Idempotency-Key` retention for edge-reachable operations** is [09 §10](09-monorepo-and-conventions.md)'s open question 5 and is set by document 11 alongside the divergence budget. Scheduling's requirement is stated: retention must exceed the maintenance-action-record divergence budget (90 days, §3.1), because a queued work-order request replayed after reconnection must still deduplicate.

### 4.6 The Scheduling ↔ Supply convergence criterion — D20

D20: "Scheduling↔Supply has no convergence criterion." [04 §1](../architecture/04-subapplication-architectures.md) declares the cycle intentional — "Scheduling and Supply negotiate work against parts availability… event-mediated, so neither creates a synchronous dependency" — but an intentional cycle without a termination proof is an oscillation.

Four mechanisms, and the loop terminates because of the second:

1. **Bounded generations.** `max_replan_generations = 3` per `(availability_id, planning_epoch)` — **[PLACEHOLDER — Phase 3 SME]**. On exhaustion the package enters ▪`REPLAN_EXHAUSTED`, operator-visible with the full explanation of what could not be satisfied. A bound alone is not convergence; it is a stop.
2. **Monotone feasible-set contraction — the actual convergence argument.** A NIIN line that failed reservation in generation `g` **must** enter generation `g+1` as a *hard* constraint, in exactly one of three forms: (a) its `arrival_day` from Supply's `lead_time`, (b) a substitute from its `interchangeable_group`, or (c) the candidate excluded with `reason_code = parts_unavailable`. It is never re-proposed unchanged. Each generation therefore solves over a strictly smaller feasible set, so the sequence is finite and monotone regardless of the bound. **Re-proposing an unchanged line is the non-convergence**, and it is the natural implementation, which is why it is called out.
3. **Replan triggers are enumerated, and `part_availability.changed` is not one of them.** Replans are triggered only by (a) an explicit `POST /work-packages/plan`, (b) a reservation failure inside the saga, (c) `allowance_shortfall.detected` or `requisition.status_changed` **for a NIIN in the current package**. Supply's availability stream is high-volume and continuous; treating it as a trigger is the oscillation D20 names. Availability changes update the read model and are consumed at the *next* planning cycle.
4. **Rate limit.** A minimum monotonic interval between replans per availability — **[PLACEHOLDER — Phase 3 SME]** 15 minutes — plus `λ_churn` in the objective (§4.3) so a replan does not needlessly reshuffle a plan a planner has already read.

No synchronous Supply read occurs on the compute path in any of this. The solve reads Scheduling's own `part_availability` read model; the reservation is a **command**, issued after the solve, and commands are permitted (03 principle 3: "A producer that needs a specific action taken elsewhere issues a command against that sub-application's API and accepts the response").

---

## 5. Findings capture as a labeling problem

[04 §6](../architecture/04-subapplication-architectures.md): "Capture design therefore optimizes for label quality… **Treating this as a data-entry form rather than as the system's primary training input is the most likely way for the program to produce a predictive capability that cannot improve.**"

[06 §9.2](../architecture/06-demo-decisions-and-assumptions.md) makes four fields a **Tier A** program requirement — "the capability does not work without this": the corrective-versus-preventive determination, the findings code against the controlled vocabulary, failure timing, and the triggering driver. "The four fields are the entire supervised signal; without them no tier improves over time."

### 5.1 The capture flow

```
                 ┌─────────────────────────────────────────────────┐
                 │ POST /maintenance-action-records                │  the ONLY writer
                 │   Idempotency-Key: <action_record_id>           │
                 │   work_order_id: <uuid> | null   ← nullable     │
                 └────────────────────┬────────────────────────────┘
                                      │
   ┌──────────────────────────────────▼──────────────────────────────────┐
   │ 1. schema validation (blocking)                                     │
   │    - maintenance_class present, from the enum                        │
   │    - findings.* codes valid against the CACHED 3-M projection        │
   │      (12 §4: code lists for form rendering AND validation)           │
   │    - findings.taxonomy_version present and known                     │
   │    - triggering_* ABSENT from the request  → 422 if present  (§5.4)  │
   │    - failure_detected_at interval well-formed (earliest <= latest)   │
   │ 2. quality validation (NON-blocking; emits warnings, accepts row)    │
   │    - §5.7's realistic-input rules                                    │
   │ 3. derive: failure_indicator (§5.3)                                  │
   │ 4. derive: triggering_driver / triggering_prediction_id /            │
   │            policy_version   (§5.4 — the ONLY writer of these)        │
   │ 5. assign JCN, or defer assignment (§6.4)                            │
   │ 6. resolve holdout_member from the local read model                  │
   │ 7. ONE TRANSACTION:                                                  │
   │      INSERT maintenance_action_record                                │
   │      INSERT outbox row  →  maintenance_action.recorded               │
   │      (11 §2.3: the state change and its event, atomically)           │
   │ 8. → 201 with the full record and any quality warnings               │
   └─────────────────────────────────────────────────────────────────────┘
```

`POST /work-orders/{id}/actions` from [04 §6](../architecture/04-subapplication-architectures.md) is retained in the contract and implemented as a **thin non-authoritative wrapper**: it constructs the same `MaintenanceActionRecordCreate` with `work_order_id` bound from the path and delegates to the same service function. It creates no second aggregate and no second table. It is kept because it is in the published surface and because it is the natural shape for the enterprise flow — but it must never be the *only* path, because a work-order-scoped-only writer is D8's exact shape (§1.4).

**Step 2 is non-blocking, and this is a deliberate, load-bearing choice.** [13 §9.10](13-synthetic-data-generator.md) generates wrong findings codes, wrong-item attribution, corrective/preventive misclassification, missing parts records, narrative–code contradiction, duplicate 2-Kilos, date rounding, and missing `triggering_driver` — because those are the realistic production conditions. An API that rejects them produces one of two outcomes: the deckplate stops recording (D8 by attrition), or someone enters whatever passes validation (corruption that is now invisible). So: **accept the record, record the doubt.** Quality warnings are persisted on the row, exported to Audit, and surfaced on `GET /maintenance-history` so that label consumers can weight or exclude — which is a decision for the label constructor, not for the capture API.

### 5.2 The corrective-versus-preventive determination — API field and validation

Not a UI design. The following is the API contract for the determination, and the UI-facing requirement it imposes.

| Element | Specification |
|---|---|
| Field | `maintenance_class`, five-value enum (§3.4), **required, no default, not nullable** |
| Second field | `maintenance_class_basis`, required, five-value enum. Records *how* the determination was made |
| UI-facing requirement | **The determination may not be pre-selected, and it may not be derivable by the client from any other field the form already contains.** No default, no "most likely" pre-fill, no inference from `action_taken_code`. A pre-selected radio button is answered by inertia, and [13 §9.10](13-synthetic-data-generator.md) calls corrective/preventive misclassification "the single most damaging label error, because it directly corrupts the supervised signal" |
| Cross-validation (non-blocking warning) | `maintenance_class = preventive` with `findings.when_discovered_code ∈ {2,3,5}` (normal operation, operability tests, shifting modes) is *suspicious*, because preventive work is normally discovered during PMS (`6`) or inspection (`4`). Warning `maintenance_class_inconsistent_with_when_discovered`, never a rejection — a genuine preventive task discovered during normal operation exists |
| Cross-validation (non-blocking warning) | `maintenance_class = corrective` with `findings.status_code ∉ {2,3}` — a corrective action on equipment that was neither inoperative nor degraded. Warning `corrective_without_degrading_status` |
| Cross-validation (non-blocking warning) | `maintenance_class = no_defect_found` with a non-empty `parts_consumed[]`. Warning `no_defect_found_with_parts` |
| Never permitted | Deriving `maintenance_class` server-side from `action_taken_code` or from the narrative. The determination is a human judgment, and the server's job is to require it, not to guess it |

### 5.3 `failure_indicator` — derived, versioned, never captured

[04 §4](../architecture/04-subapplication-architectures.md): "The `failure_indicator` on `maintenance_action.recorded` distinguishing corrective from preventive action is the determinative input" to PdM's censoring-aware label construction.

```python
FAILURE_INDICATOR_RULE_VERSION = "fi-1"

def derive_failure_indicator(r: MaintenanceActionRecordCreate) -> bool:
    """The corrective/preventive BINARY PdM needs, as a versioned function of the RICHER
    five-value capture. Capture is not narrowed to fit the label; the label is derived
    from the capture and carries the version of its own derivation, so a rule change is
    detectable in the label set instead of silently re-labelling history."""
    if r.maintenance_class in (NO_DEFECT_FOUND, CANNIBALIZATION):
        return False                     # §3.4.2: neither is a failure of this item
    if r.maintenance_class in (PREVENTIVE, OPPORTUNISTIC_PREVENTIVE):
        return False
    if r.findings.when_discovered_code == "9":
        return False                     # "no failure, PMS accomplishment only" [08 §2.5]
    return True                          # corrective
```

`failure_indicator_rule_version` is stored on the row and published in the event payload. Re-derivation of history under a new rule produces **new** rows (append-only, `supersession_reason = reclassification`), never an in-place update — the same non-destructive-revision principle [12 §6](12-reference-data-taxonomy.md) applies to the taxonomy.

**The Status 2/3 filter is exposed, not applied.** [07 §5.4](../architecture/07-navy-data-systems.md): "Status 2 is inoperative and Status 3 is degraded performance. Limiting 2-Kilo data to Status 2 and 3 eliminates approximately 75% of all 2-Kilos written and provides the basis for measuring mission degrading performance. **This is the Navy's own severity filter, and it should be the platform's label filter.**" Scheduling therefore captures `status_code` on every record and offers `GET /maintenance-history?status_code=2,3`, but does **not** pre-filter its event stream: `maintenance_action.recorded` is published for every action, and the filter is applied by the consumer that needs it. Filtering at the producer would make the ~75% invisible and would break `MAINT_EFFECT`, which is computed over *all* actions ([07 §5.7](../architecture/07-navy-data-systems.md)).

### 5.4 `triggering_driver`, `triggering_prediction_id`, `policy_version` — the exact logic

This is the input to PdM's entire causal-validity correction ([06 §2](../architecture/06-demo-decisions-and-assumptions.md)) and is populated nowhere else in the system.

**Rule 0 — these three fields are server-derived and are rejected on input.** There is no API field for them. A request carrying any of the three returns `422 urn:fathom:problem:maintenance:treatment-record-is-derived`. Rationale: they encode a *causal* claim about why an intervention occurred. A UI, an integration, or an agent asserting that claim directly is exactly the "unadjudicated back channel delivering causal claims" D23 forbids in a different context, and here it would corrupt the treatment-assignment record the correction depends on.

**Resolution chain.**

```python
# src/fathom_maintenance/services/treatment_record.py
def derive_treatment_record(r: MaintenanceActionRecordCreate, *, uow) -> TreatmentRecord:

    candidate = _resolve_candidate(r, uow=uow)

    # ── no candidate: the action was unsolicited ────────────────────────────
    if candidate is None:
        # A repair with no candidate behind it. Common afloat, and common ashore for
        # emergent work. NULL is the HONEST value and PdM's propensity model is
        # specified to handle missingness in the treatment record — 13 §9.10 generates
        # "missing triggering_driver" precisely so that path is exercised. NULL rather
        # than a sentinel string: see §5.4.1.
        return TreatmentRecord(driver=None,
                               candidate_id=None,
                               prediction_id=None,
                               policy_version=None)

    if candidate.driver is Driver.PREDICTION:
        # THE case the correction exists for.
        return TreatmentRecord(
            driver=Driver.PREDICTION,
            candidate_id=candidate.candidate_id,
            prediction_id=candidate.source_prediction_id,          # non-null by construction
            prediction_ref=_snapshot_prediction(candidate),        # frozen at candidate creation
            # THE POLICY IN FORCE WHEN THE CANDIDATE WAS CREATED — not when the action was
            # recorded. The candidate is the treatment assignment; attributing it to the
            # policy running weeks later credits a policy that made no decision.
            policy_version=candidate.policy_version,
        )

    if candidate.driver is Driver.PMS:
        return TreatmentRecord(
            # PMS_PERIODICITY, not PMS. PdM's CHECK constraint spells it out and the
            # generator agrees; see §5.4.1.
            driver=Driver.PMS_PERIODICITY,
            candidate_id=candidate.candidate_id,
            prediction_id=None,                                    # NULL. No prediction assigned it
            policy_version=candidate.interval_policy_version,      # non-null. §5.4.3
        )

    if candidate.driver is Driver.CASUALTY:
        return TreatmentRecord(
            driver=Driver.CASUALTY,
            candidate_id=candidate.candidate_id,
            prediction_id=None,                                    # NULL
            policy_version=None,                                   # NULL: the equipment assigned
        )                                                          #  the treatment, not a policy

    if candidate.driver is Driver.OPPORTUNISTIC:
        # THE SPLIT THAT MATTERS. An availability opened access; the question PdM's
        # censoring classification turns on is whether a PREDICTION contributed to the
        # decision to use that access on THIS item (13 §8.4).
        #   contributed     -> `opportunistic`      -> DEPENDENT censoring
        #   only periodicity-> `opportunistic_pms`  -> conditionally independent
        # Collapsing these is "the most likely implementation error" (22 §4.2).
        if candidate.prediction_contributed:
            return TreatmentRecord(
                driver=Driver.OPPORTUNISTIC,
                candidate_id=candidate.candidate_id,
                prediction_id=candidate.source_prediction_id,      # NON-NULL. 13: null unless
                prediction_ref=_snapshot_prediction(candidate),    #  driver in {prediction,
                policy_version=candidate.policy_version,           #  opportunistic}
            )
        return TreatmentRecord(
            driver=Driver.OPPORTUNISTIC_PMS,
            candidate_id=candidate.candidate_id,
            prediction_id=None,                                    # NULL
            policy_version=candidate.interval_policy_version,
        )
```

**`_resolve_candidate` — and the one place guessing is forbidden.**

```python
def _resolve_candidate(r, *, uow) -> WorkCandidate | None:
    # 1. Explicit, via the work order. The only unambiguous path.
    if r.work_order_id:
        wo = uow.work_orders.get(r.work_order_id)
        if wo and wo.originating_candidate_id:
            return uow.candidates.get(wo.originating_candidate_id)
        return None

    # 2. No work order (the edge path, and emergent ashore work). Attempt resolution
    #    ONLY where it is unambiguous: exactly ONE open candidate for this INSTALLED ITEM
    #    whose window overlaps the failure-detection interval.
    open_c = uow.candidates.open_for_item(
        installed_item_id=r.installed_item_id,          # NEVER position_id [C10, D9]
        overlapping=r.failure_detected_at,
    )
    if len(open_c) == 1:
        return open_c[0]

    # 3. Zero or many. Return None → driver = unknown.
    #    A FABRICATED LINK IS WORSE THAN A MISSING ONE. Missingness is modellable and is
    #    generated as a test case (13 §9.10); a wrong prediction_id enters the propensity
    #    model as a treatment that was never assigned, and no downstream check can detect it
    #    because the record is internally consistent. Do not add a nearest-match heuristic.
    return None
```

#### 5.4.1 The vocabulary — **[RC-3 CLOSED, and rev 1 was wrong twice]**

Neither [03 §6](../architecture/03-integration-contracts.md) nor [03 §7](../architecture/03-integration-contracts.md) enumerates `triggering_driver`'s values; the row says only "`triggering_driver`, `triggering_prediction_id`, `policy_version`". Two documents *do* enumerate them, **and they agree with each other**:

- [22 §2.3](22-pdm.md): `CHECK (triggering_driver IN ('pms_periodicity','casualty','prediction','opportunistic','opportunistic_pms'))`
- [13 §8.4](13-synthetic-data-generator.md): the same five, with `opportunistic` defined as "an availability or another work item opened access, **and a prediction contributed to the decision**" and `opportunistic_pms` as "an availability opened access and **only periodicity** contributed"

Rev 1 emitted `{prediction, pms, casualty, opportunistic, unknown}`. Two defects, both of which would have been silent:

| Rev 1 | Correct | Consequence of rev 1 |
|---|---|---|
| `pms` | **`pms_periodicity`** | PdM's `CHECK` **rejects the row**. This one is loud, and is the lucky case |
| *(absent)* | **`opportunistic_pms`** | **Silent and severe.** Every availability-of-opportunity intervention would be emitted as `opportunistic`, which [22 §4.2](22-pdm.md) classifies as **dependent** censoring. Purely periodicity-driven work would be counted as prediction-driven treatment, inflating the dependent-censoring population and biasing every IPCW weight. [22 §4.2](22-pdm.md) names this exact collapse "the most likely implementation error in this table" |
| `unknown` | **NULL** | PdM's `CHECK` rejects the string `'unknown'`; its column is nullable and NULL is how missingness is represented. A sentinel string would have failed the insert |

**`unknown` is therefore a presentation value, not a wire value.** The column is NULL, the event field is absent, and `GET /maintenance-history` renders it as "unknown" for humans. This preserves rev 1's substantive point — missingness is honest and must never be fabricated (§5.4's `_resolve_candidate`) — while representing it the way the consumer's schema requires. `fathom_maintenance_treatment_record_unknown_ratio` (§13) counts NULLs.

**`prediction_contributed` is a field on `WorkCandidate`, not an inference.** The `opportunistic` / `opportunistic_pms` split cannot be derived after the fact — whether a prediction contributed to a decision is a fact about the decision, and by the time the action is recorded the only honest source is what was recorded when the candidate was opportunistically added to a package. It is set by the optimizer at package construction and is immutable, for the same reason `WorkOrder.driver` is (§3.3).

#### 5.4.2 Merged candidates, and the field rev 1 overloaded

Rev 1 held that where a prediction was raised but periodicity determined the timing, the record should carry `(driver=pms, prediction_id=non-null)`, glossed as "*a flag was raised, and it did not change what we did.*" **The substantive judgment is right and the encoding is wrong**, and the corrected vocabulary shows why:

- [13 §8.4](13-synthetic-data-generator.md) states `triggering_prediction_id` is "null unless driver = prediction | opportunistic". The pair `(pms_periodicity, non-null prediction_id)` is unrepresentable in the generator's own convention, so no test corpus would ever contain it and the path would be unexercised.
- Worse, [22 §4.2](22-pdm.md)'s censoring classification is "a total function of three recorded fields… and of nothing else," keyed on `triggering_driver`. A non-null `triggering_prediction_id` on a `pms_periodicity` row is *invisible* to it. Rev 1's field would have been written and never read.

So the treatment field carries only the treatment, and the metric gets its own field:

| Field | Meaning | Read by |
|---|---|---|
| `triggering_prediction_id` | **The prediction the policy acted on.** Non-null only where `driver ∈ {prediction, opportunistic}` | PdM's propensity model ([22 §4.2](22-pdm.md)) |
| `prediction_in_evidence_id` | A prediction that was raised for this item and was *not* the treatment assignment | **Warning lead-time coverage only** ([06 §2](../architecture/06-demo-decisions-and-assumptions.md)) |

This keeps rev 1's real concern intact — dropping the linkage "would silently understate" the program's headline metric, which is measured over "corrective maintenance actions preceded by a raised risk flag" — while keeping the treatment record clean. **[RECONCILE RC-4]**: `prediction_in_evidence_id` is not in [03 §6](../architecture/03-integration-contracts.md)'s payload list and is proposed as an addition (§17). Until it is accepted, the metric may be computed by joining through `triggering_candidate_id` to the merged candidate's retained `merged_candidate_ids`, which is lossless but slower; **no implementation may recover it by putting the id back into `triggering_prediction_id`.**

#### 5.4.3 Decision table

| Origin | `triggering_driver` | `triggering_prediction_id` | `policy_version` |
|---|---|---|---|
| Work order from a `prediction` candidate | `prediction` | candidate's `source_prediction_id` | candidate's `policy_version` |
| Work order from a `pms` candidate | `pms_periodicity` | **NULL** | `interval_policy_version` — see §5.4.4 |
| Work order from a `casualty` candidate | `casualty` | **NULL** | **NULL** |
| Merge product, prediction determined timing | `prediction` | retained `source_prediction_id` | candidate's `policy_version` |
| Merge product, PMS determined timing | `pms_periodicity` | **NULL** (id goes to `prediction_in_evidence_id`, §5.4.2) | `interval_policy_version` |
| Availability opened access, **a prediction contributed** | `opportunistic` | candidate's `source_prediction_id` | candidate's `policy_version` |
| Availability opened access, **only periodicity contributed** | `opportunistic_pms` | **NULL** | `interval_policy_version` |
| Edge-recorded at-sea repair | `casualty` | NULL | NULL |
| No candidate, or ambiguous candidate | **NULL** (rendered "unknown") | NULL | NULL |
| Holdout (policy-frozen) item | never `prediction` or `opportunistic` — see below | **NULL always** | per driver |
| Client attempted to supply any of the three | — | — | `422`, request rejected |

**The holdout row is an invariant, not a convention.** [13 §10.3](13-synthetic-data-generator.md) consequence 2: "the only drivers reachable for a holdout item are `pms_periodicity`, `casualty`, and `opportunistic_pms`… their construction requires a prediction object the policy never received." PdM enforces it twice — `holdout_has_no_dependent_censoring` as a `CHECK` ([22 §2.3](22-pdm.md)) and harness gate G-7 — and Scheduling's admission filter (§4.3) is what makes it true upstream. §11.5 asserts it directly rather than relying on the filter's correctness.

#### 5.4.4 `policy_version` on a non-prediction driver — **confirmed by PdM**

Rev 1 set `policy_version` non-null for PMS-driven actions, against a literal reading of "if from PMS or casualty, these fields are null," and flagged it for PdM to overrule. **PdM did not overrule it — it requires it.** [22 §2.3](22-pdm.md) annotates the column "*the intervention policy's version, a **REQUIRED** covariate*", and [22 §4.3](22-pdm.md) fits the propensity model **stratified by `policy_version`**, because [13 §8.4](13-synthetic-data-generator.md) guarantees the policy changes at least once in the window and "a single frozen policy makes propensity modeling trivially easy and hides the versioning requirement. One pooled fit across a policy change estimates neither policy."

Rev 1's reasoning therefore stands as written: a PMS periodicity **is** an intervention policy, an approved `interval_change` changes it (§3.9), and if every PMS-driven action carried a null policy version then an interval change that halved a periodicity fleet-wide — a large, deliberate change in treatment assignment — would be invisible in the treatment record, with the resulting shift in observed hazard attributable to nothing. `casualty` remains NULL because no policy assigned it: the equipment did.

One consequence worth stating because it constrains PdM's stratification and not just Scheduling's write: **`policy_version` values are drawn from two distinct namespaces** — the candidate-generation policy for `prediction` and `opportunistic`, and `interval_policy_version` for the PMS-derived drivers. They must not be pooled into one stratum by string equality. Scheduling emits them prefixed (`cgp:<semver>` and `ipv:<semver>`) so the namespaces cannot silently collide, and this is **[RECONCILE RC-5]** against [22 §4.3](22-pdm.md), which does not state a prefix convention (§17).

**`holdout_member`** is resolved from the local read model at capture and stamped on the record, so that a holdout item's actions are identifiable in the label stream without a join to a population definition that may have changed ([06 §2](../architecture/06-demo-decisions-and-assumptions.md), [13 §10.2](13-synthetic-data-generator.md)).

### 5.5 Failure timing — interval-censored, because that is what is recorded

`failure_detected_at { earliest, latest, basis }`, where `basis ∈ {observed_at_time | end_of_shift | next_inport_day | unknown_within_window}`.

[13 §9.10](13-synthetic-data-generator.md) generates date rounding — "recorded at end of shift, or on the next in-port day" — with the stated downstream consequence: "failure timing is coarser than telemetry timing, so **lead-time computation must handle interval-censored event times**." A single `failure_detected_at` timestamp forces the capturer to invent precision, and warning lead-time coverage (the primary metric) is then computed against a fabricated instant. The interval is the honest representation; `earliest == latest` is the precise case and is not special.

`occurred_at` on the envelope is set from `action_completed_at`; `recorded_at` from persistence time. [03 §5.4](../architecture/03-integration-contracts.md): "they diverge materially here: a mission anomaly occurred at sea and was recorded when the ship reconnected." Consumers computing over time choose deliberately, and **feature computation must not use `occurred_at` for any value authored with hindsight** — an ashore-completed findings coding is hindsight-authored, so records with `findings_completed_ashore = true` are stamped by the library's `hindsight` marker ([11 §5](11-outbox-sync-library.md)) `[D22]`.

### 5.6 Findings coding against the 3-M code sets

**Scheduling captures 3-M codes, as filed, and stores nothing else.** [03 §14](../architecture/03-integration-contracts.md): "Scheduling captures the 3-M code sets (CAUSE, WHEN DISCOVERED, ACTION TAKEN) because maintainers cannot be asked to learn a second vocabulary at the deckplate." [12 §4](12-reference-data-taxonomy.md) is exact about what Scheduling holds locally: "The code lists for form rendering and validation, with `set_is_complete` surfaced. **Never the crosswalk resolution** — findings are stored as filed, in 3-M codes."

| Concern | Mechanism |
|---|---|
| Code lists | Read-through cache of `GET /api/v1/reference-data/taxonomy/projections/3m`, keyed by `taxonomy_version`, refreshed on `taxonomy_version.published` ([12 §3.4](12-reference-data-taxonomy.md)) |
| Validation | `findings.cause_code`, `when_discovered_code`, `action_taken_code` validated against the cached lists. **Where `set_is_complete = false`, an unknown code is accepted with a warning, not rejected** — [12 §2.6](12-reference-data-taxonomy.md) seeds `ACTION_TAKEN_FIRST` incomplete because the source is incomplete, and rejecting an unlisted-but-real code would make the platform stricter than 3-M |
| Version | `findings.taxonomy_version` is **mandatory** on every record. "A training set assembled across an unversioned revision is silently corrupt and undetectably so" ([03 §14](../architecture/03-integration-contracts.md)) |
| Mode resolution | **Not done here.** Scheduling never writes a failure mode. Consumers resolve `{CAUSE, WND, ACTION TAKEN, EIC}` → `candidate_modes[]` with confidence through `GET /crosswalk/3m-codes` at read time ([12 §9.1](12-reference-data-taxonomy.md)) |
| Ambiguity | Carried as data. 3-M CAUSE is a *cause* code with nine values, not a mode code, so one findings record maps to a **set** of candidate modes. Scheduling must not pick one, must not cache a resolution, and must not surface a single "resolved mode" on any read |
| EIC | Carried on the record for federation, matched **by prefix** in the crosswalk, never a join key |
| Vocabulary extension | `POST /api/v1/reference-data/taxonomy/proposals` with kind `crosswalk_revision` — Scheduling may propose, never approve ([12 §3.3](12-reference-data-taxonomy.md)) |

> **Why Scheduling storing a resolved mode would be a defect and not a convenience.** The three capture points exist to *disagree*: PMA records an observable signature, Scheduling records a 3-M cause code, Failure Intelligence works in the full vocabulary, and [12 §9.2](12-reference-data-taxonomy.md)'s `FULL OUTER JOIN` over both crosswalks is what makes the disagreement visible — "`pma_only` and `maintenance_only` rows are the interesting ones." A cached resolution inside Scheduling turns a lossy many-to-many mapping into a false one-to-one at the moment of capture, and every downstream consumer inherits the falsehood with no way to detect it.

### 5.7 Realistic-input handling — the eight corruptions

[13 §9.10](13-synthetic-data-generator.md) enumerates the label and record corruptions the generator injects. Each is accepted, and each produces a specific, named, non-blocking signal. §11.6 tests exactly this table.

| Corruption ([13 §9.10](13-synthetic-data-generator.md)) | Capture behaviour | Signal emitted |
|---|---|---|
| Wrong findings code | Accepted | none detectable at capture — this is the irreducible noise ceiling on actionable precision ([06 §2](../architecture/06-demo-decisions-and-assumptions.md) A5). Recorded as a known limitation, not a warning |
| **Wrong-item attribution** (recorded against a sibling position) | Accepted | `warning: item_not_in_open_candidate_set` where no candidate exists for the item but one exists for a sibling position in the same system. **The warning names the sibling; the record is not moved.** Correcting it is a human act producing a superseding row with `supersession_reason = wrong_item_attribution` |
| Date rounding | Accepted | `failure_detected_at.basis` records it structurally (§5.5). No warning needed — the interval *is* the representation |
| Missing parts record | Accepted | `parts_record_absent = true` must be explicitly set; an empty `parts_consumed[]` with `parts_record_absent = false` raises `warning: parts_record_ambiguous`. `MAINT_EFFECT` is uncomputable for those actions and must be reported as uncomputable, not as zero ([07 §5.7](../architecture/07-navy-data-systems.md)) |
| Narrative–code inconsistency | Accepted | no capture-time check. The narrative is untrusted free text (03 §9) and is never parsed to validate a coded field |
| **Duplicate 2-Kilos** (same job, two JSNs) | Both accepted | dedup is on `action_record_id`, never on `jcn`. `warning: probable_duplicate_action` where another record exists for the same `(installed_item_id, action_taken_code, overlapping failure interval)`. Naive counting inflates failure rates, so `GET /maintenance-history` exposes the warning and never silently collapses the pair |
| **Corrective/preventive misclassification** | Accepted | the cross-validation warnings of §5.2. The most damaging error, and the only defence is that the field is required, unpre-filled, and paired with `maintenance_class_basis` |
| Missing `triggering_driver` | Accepted | resolves to **NULL**, rendered "unknown" (§5.4.1). Never fabricated |

### 5.8 Navy reliability arithmetic Scheduling makes computable

Scheduling does not compute MTBF, MDT, or Ao — PdM and Fleet Status do ([07 §5.11](../architecture/07-navy-data-systems.md)) — but it owns the records those formulas consume, and the formulas dictate which fields must exist. [07 §5.5](../architecture/07-navy-data-systems.md), verbatim:

```
Ao      = Uptime / (Uptime + Downtime)
T(pf)   = MTBF / (MTBF + MDT)
MTBF    = 1 / (Failures / (30.44 × 0.667 × Population))     [days]
```

MDT is "the mean number of days from the **opening of Status 2 or 3 2-Kilos** until the… CASREPs are corrected and the **2-Kilos closed**. MDT is all-inclusive." Two capture obligations follow, and they are why `WorkOrder` carries `status_code` and why the record carries both `action_started_at` and `action_completed_at`:

- The **opening** instant of a Status 2/3 deferred action is `work_order.created_at` where the order exists, and `failure_detected_at.earliest` where it does not. Both must be queryable, because an edge-recorded action has no opening work order.
- The **closing** instant is `action_completed_at`. "All-inclusive" means awaiting-parts time is inside MDT, which is why `parts_consumed[].requisition_doc_no` matters: it is the join to Supply's requisition lifecycle and therefore the decomposition of MDT into repair time versus awaiting-parts time.

The JCN shares its UIC with the requisition document number, and [07 §5.2](../architecture/07-navy-data-systems.md) names that "the natural join between the maintenance and supply sub-applications."

---

## 6. JCN generation

[07 §5.2](../architecture/07-navy-data-systems.md), JFMM Vol VI ¶19.2.3.2, exact: **thirteen characters — UIC (5 numeric) + Work Center (4 alphanumeric, left justified) + Job Sequence Number (4)**. Work Center is 4 positions on ships, 3 at intermediate activities.

And the finding this section exists to implement:

> *"**The first position of the JSN is used to identify the tool or organization that created the 2-Kilo.**… The specific value contained within the first position of the JSN **provides enhanced data mining capabilities and facilitates data aggregation and analysis.**"*
>
> Originator values are controlled centrally. **A predictive system would legitimately carry its own originator alpha code**, and the field exists explicitly to support the analysis this platform performs. This should be in the demonstration.

### 6.1 Format

```
 positions:  1  2  3  4  5   6  7  8  9   10  11  12  13
            ┌──────────────┬─────────────┬──────────────────┐
            │     UIC      │ Work Center │  Job Sequence No │
            │  5 numeric   │ 4 alnum, LJ │       4          │
            └──────────────┴─────────────┴──────────────────┘
                                          ▲   └── 3 chars: base-36 counter
                                          └────── ORIGINATOR ALPHA
```

- **UIC** — from `AssetRef.uic`, 5 characters. [03 §3.3](../architecture/03-integration-contracts.md) notes a 6-character form carries a leading Service identifier; where one is held, the leading identifier is **stripped for the JCN** and the full form retained on the asset. Stripping is recorded, not silent.
- **Work Center** — 4 positions, **left justified, space-padded**. `"38A "` and not `" 38A"` or `"38A"`. The padding is not cosmetic: the [07 §5.3](../architecture/07-navy-data-systems.md) 2-Kilo layout puts Work Center at fixed positions 6–9, and an intermediate activity's 3-character code must occupy 6–8 with 9 blank. Stored padded, validated padded (`^[A-Z0-9]{1,4} *$` with total length 4).
- **JSN position 1 — the FATHOM originator alpha.**
- **JSN positions 2–4** — a base-36 counter (`0-9A-Z`), 46,656 values per allocation scope.

### 6.2 The FATHOM originator alpha — **[ESTABLISHED HERE]**

**Value: `F`.** Configured as `FATHOM_APP__JSN_ORIGINATOR_ALPHA`, default `F`, and the reasoning matters more than the letter:

1. **It must be an alpha.** Ship's force JSN allocation conventionally uses numeric ranges, so an alpha first position is structurally unlikely to collide with a locally-issued sequence.
2. **It must be one character**, because the field is one character and the counter needs the other three.
3. **It is a request, not an assumption.** [07 §5.2](../architecture/07-navy-data-systems.md): "Originator values are controlled centrally." `F` is therefore reserved-for-demonstration, recorded as such in the dataset's data card ([13 §17](13-synthetic-data-generator.md)), and **[OPEN OQ-4]**: the production value requires central assignment via TYCOM / NAVSEA. Because it is configuration and not code, that assignment changes one Helm value and no logic.
4. **Different originators for different drivers are deliberately *not* used.** A first impulse is `P` for prediction-driven and `S` for scheduled — but the field identifies "the tool or organization that created the 2-Kilo", and the tool is FATHOM in every case. The driver is already recorded, with far more fidelity, in `triggering_driver` (§5.4). Splitting the originator would make FATHOM's total contribution unaggregatable, which defeats the exact data-mining purpose [07 §5.2](../architecture/07-navy-data-systems.md) says the field exists to serve.

[13 §11.5](13-synthetic-data-generator.md) already applies this convention in the synthetic corpus — "prediction-driven 2-Kilos carry FATHOM's declared originator alpha, and the field is therefore usable for exactly the aggregation analysis 07 §5.2 says it exists to support" — so the generator and this service must agree on the configured value. A conformance test asserts the corpus's originator matches the service's configuration.

### 6.3 Counter allocation

```
JsnBlockLease {
  lease_id            uuid PK
  uic                 char(5)
  work_center         char(4)
  originator_alpha    char(1)
  block_start         int          # inclusive, base-10; rendered base-36
  block_size          int
  next_offset         int          # monotonically consumed
  issued_to_node      text         # "enterprise" | "edge:<asset_id>"
  issued_at, exhausted_at?
}
```

- **Allocation scope** is `(uic, work_center, originator_alpha)`. Uniqueness of the resulting JCN is enforced by `UNIQUE (jcn)` on both `work_order` and — as a partial index over non-null values — `maintenance_action_record`.
- **Enterprise allocation** takes the next offset inside a lease under `SELECT … FOR UPDATE`. Gap-free is not required (a JSN is an identifier, not a sequence with meaning), but monotonic-within-lease is.
- **Edge allocation uses a pre-issued block.** Blocks are issued ashore and synchronised to the hull at the last contact; the edge consumes from its own block only. **This is what lets a disconnected ship mint a real JCN with no server round trip**, and it is why two nodes can never mint the same JCN: the blocks are disjoint by construction, and `JsnBlockLease` is `SERVER_AUTHORITATIVE_EDGE_SUBMITS` — the edge consumes, it never issues.
- Block size — **[PLACEHOLDER — Phase 3 SME]** 512 per `(uic, work_center)` per issuance, sized against [06 §7](../architecture/06-demo-decisions-and-assumptions.md)'s ~14,000 actions over 24 months fleet-wide, which is far below any plausible six-week consumption for one hull.

### 6.4 Block exhaustion afloat — the JCN is never allowed to block a record

If an edge block is exhausted mid-disconnection, the record is **accepted** with `jcn = NULL` and `jcn_assignment_deferred = true`, and the JCN is assigned ashore during reconciliation, monotonically, in `monotonic_seq` order.

This is the same reasoning as [11 §9.1](11-outbox-sync-library.md) breach rule 3 ("a telemetry breach must not stop maintenance action recording — that would reintroduce D8 by a different route"). **Refusing a maintenance action record because an identifier pool ran dry is D8 wearing a compliance badge.** A record without a JCN is still a complete label; a label that was never captured is not recoverable. `jcn_assignment_deferred` is surfaced on `/metrics` as `fathom_maintenance_jcn_deferred_total` so the condition is visible rather than discovered later.

---

## 7. Edge-authoritative maintenance action recording

[06 §4](../architecture/06-demo-decisions-and-assumptions.md) is about this sub-application. The decision, verbatim: "Grow the afloat profile. Add an **edge-authoritative, append-only maintenance action record** separable from work-order authorization." Demo scope: "One SSN, disconnected for a simulated six weeks, conducting one at-sea corrective repair and two mission reviews while dark," as "a physically separate deployment rather than a simulated queue."

D8, verbatim: "A submarine dark six weeks repairs a pump at sea and cannot record the corrective/preventive determination, findings coding, parts consumed, or failure timing — **the four highest-value fields** — until weeks later, reconstructed by someone who was not there. Label capture is excluded from exactly the operating mode where the most informative failures occur."

[11 §1.2](11-outbox-sync-library.md) fixes the scope of Scheduling's edge profile precisely: **"Yes, one path only** — edge-authoritative, append-only maintenance action records `[D8]`. Work orders, authorizations and work packages remain server-authoritative and are *not* edge-writable."

### 7.1 What the edge instance can and cannot do

| Capability | Edge | Mechanism |
|---|---|---|
| `POST /maintenance-action-records` | **Yes — authoritative** | `EDGE_AUTHORITATIVE_APPEND_ONLY`. Client-minted `action_record_id`, local JCN from a pre-issued block (§6.3), full findings coding, outbox row in the same transaction |
| `POST /maintenance-action-records` with `work_order_id = null` | **Yes — the normal case afloat** | The nullable FK of §3.4.1 |
| `GET /maintenance-history` (local records) | Yes | Local read |
| `GET /work-orders`, `GET /work-candidates`, `GET /availabilities` | Yes, from cache, with a staleness marker | `ENTERPRISE_AUTHORITATIVE_NOT_EDGE_WRITABLE` read path |
| Cached predictions | Yes, **presented as degraded**, with an explicit staleness horizon; expired values shown as expired, not as predictions | `ENTERPRISE_AUTHORITATIVE_CACHED_DEGRADED` ([11 §7.3](11-outbox-sync-library.md)) |
| `POST /work-orders` | **No.** Converted to a queued *request*, `202`, `authorization_pending_ashore` | `SERVER_AUTHORITATIVE_EDGE_SUBMITS` |
| `PATCH /work-orders/{id}` to `authorized` | **No.** `423 urn:fathom:problem:maintenance:not-edge-writable` | Same |
| `POST /work-packages/plan`, `/reserve`, `/approve` | **No.** The optimizer does not run afloat; reservations are never issued from the edge | `optimizer.enabled: false`; the reserve/approve routes are gated |
| `POST /proposals` | Create yes; adjudicate no (`Reject`ed and returned as a request) | `APPEND_ONLY_SERVER_ADJUDICATED` |
| Mint an `installed_item_id` for an item replaced at sea | Yes, **provisional** | [11 §8](11-outbox-sync-library.md); §7.3 below |

**The write gate is asserted at startup, not merely enforced at request time.** `main.py` calls `assert_edge_write_surface()`, which enumerates every route whose `x-side-effects` is `state-changing`, intersects it with the profile's declared edge allowlist — exactly `{POST /maintenance-action-records, POST /proposals, POST /work-orders (as request), POST /work-candidates (as request)}` — and **fails the pod** on any addition. A `423` at request time depends on a developer having remembered the gate; a startup assertion catches the change that forgot it.

### 7.2 How a disconnected ship records what it did

```
DAY 0    last sync. Hull holds: cached predictions (with staleness horizon), work-order
         cache, PMS catalogue, taxonomy version pinned, JSN block lease, divergence budget.

DAY 9    a lube-oil pump fails at sea. Ship's force repairs it.

         POST /api/v1/maintenance/maintenance-action-records
           Idempotency-Key: 8f2c…   (== action_record_id, client-minted)
           {
             action_record_id: 8f2c…,
             work_order_id: null,                 ← NO AUTHORIZATION EXISTS. Legal.
             authorization_state: "unauthorized_at_time_of_action",
             asset_id: <SSN>, position_id: <P>, installed_item_id: <NEW, provisional>,
             identity_provisional: true,
             jcn: "21847 38A F0G7",
             maintenance_class: "corrective",
             maintenance_class_basis: "observed_failure",
             findings: { cause_code: "7",          # normal wear and tear
                         when_discovered_code: "2",# normal operation
                         status_code: "2",         # inoperative
                         taxonomy_version: "1.1.0" },
             findings_completed_ashore: false,
             findings_coder_was_observer: true,    ← the person who did the work coded it
             failure_detected_at: { earliest: …, latest: …, basis: "observed_at_time" },
             parts_consumed: [ { niin: …, quantity: 1 } ],
             man_hours: 6.5
           }

         ONE local transaction:
           INSERT maintenance_action_record            (INSERT-only table)
           INSERT outbox row → maintenance_action.recorded
                                 producer_node = "edge:<asset_id>"
                                 monotonic_seq = <edge sequence>
                                 clock.sync_quality = { time_source: "holdover",
                                                        dispersion_ms: <growing>, … }
           COMMIT
         → 201. The label exists. It is on the hull. It is not going to be reconstructed
           weeks later by someone who was not there.

DAY 9    server-derived, at capture, ashore-independent:
           triggering_driver          = "casualty"    ← §5.4; the edge holds only a stale
           triggering_prediction_id   = null            prediction cache and can never be
           policy_version             = null            the authority for a prediction-driven
                                                        decision [13 §15.2]
           failure_indicator          = true          ← §5.3, derived locally, versioned

DAY 9–42 the record sits in the outbox, encrypted at rest under the per-classification KEK
         (11 §10.1), signed (AU-10), with sync_quality retained. Divergence budget for
         maintenance_action_record = 90 days > 42, so no read-only degradation occurs.

DAY 42   reconnect. Coordinator drains in priority order (11 §9.3):
           class 0  provisional identity submissions   ← FIRST, ALWAYS
           class 1  maintenance action records, anomaly tags, mission records
           class 2  work-order and requisition request queues
           class 3  usage counters, health indicators, candidates
           class 4  bulk telemetry (last, interruptible)
```

Three properties of that drain are correctness matters, not optimisations:

- **Identity before aggregates.** Provisional identity resolution precedes the drain of anything referencing it ([11 §8.3](11-outbox-sync-library.md)). Otherwise the shore applies a maintenance record against an item the Registry has not adjudicated.
- **Priority classes exist so the label stream is not starved.** Six weeks of burst telemetry for one hull is on the order of 9×10⁶ samples ([13 §15.3](13-synthetic-data-generator.md)); without class ordering it "would saturate a narrow link and starve the label stream for hours or days" ([11 §9.3](11-outbox-sync-library.md)).
- **Edge drain never carries `X-Backfill` or `replay: true`.** "A six-week-old maintenance action from a submarine is a first emission of a real fact" ([11 §9.3](11-outbox-sync-library.md)). It must fire its normal side effects ashore — PdM's label ingestion, Registry's configuration change, Supply's consumption. Marking it replay would suppress exactly the effects the record exists to produce.

### 7.3 Provisional installed-item identity

The pump replaced at sea is a **new physical item**, and configuration is enterprise-authoritative. Per [03 §3.3](../architecture/03-integration-contracts.md) and [11 §8](11-outbox-sync-library.md), the edge mints a uuid4 in the canonical namespace with `provisional: true`, and Scheduling's obligations are narrow and specific:

- Every record and event referencing it carries `identity_provisional: true`. A consumer must be able to tell without inference.
- Scheduling **does not** mint the identity itself — it calls `ProvisionalIdentityMinter` from `fathom_sync` ([11 §8.2](11-outbox-sync-library.md)). No other identifier is ever minted afloat.
- Scheduling **never rewrites a published record's subject** on supersession. The Registry publishes `installed_item.identity_resolved`, and Scheduling's read models resolve through `IdentityAliasResolver` at read time ([11 §8.4](11-outbox-sync-library.md)). Records are signed; rewriting the subject is indistinguishable from tampering.
- Where the Registry **supersedes** the provisional id (sub-case 1b of [13 §15.2](13-synthetic-data-generator.md) — "this is where the defects are"), the maintenance action record is untouched and the alias carries the join. Where it **rejects** (physically impossible), the record is quarantined for human adjudication and **never discarded**.

### 7.4 Reconciliation ashore — `EDGE_AUTHORITATIVE_APPEND_ONLY`

[11 §7.3](11-outbox-sync-library.md), the strategy class this record was designed against:

> **`EDGE_AUTHORITATIVE_APPEND_ONLY`** — maintenance action records: The edge is the authority. The shore **applies** the record; it may not modify, reject, or reorder it. Corrections are new append-only records with provenance and a non-observer flag.

Concretely, on the shore side:

| Situation | Outcome |
|---|---|
| Record arrives, no local counterpart | `Apply`. Inserted verbatim, including its `producer_node` and `monotonic_seq` |
| Record arrives twice (duplicate delivery) | `Ignore(duplicate)` on `action_record_id` — **never** on `jcn` (§3) |
| Records arrive out of order | Applied as received; order is `(producer, producer_node, monotonic_seq)`, never `source_time`. A backward clock step at reconnect is expected `[D29]` |
| The shore authorized a work order for the same equipment while the hull was dark | **Both persist.** Neither overwrites the other. `work_order_id` stays null on the edge record unless a human associates them (§3.4.1) |
| An enterprise process attempts to **modify** the edge record | **Rejected.** The table is INSERT-only and the policy forbids it. A supersession row is recorded instead |
| Findings coding is completed ashore because afloat capture was minimal | A **new** record with `supersedes_action_record_id`, `findings_completed_ashore = true`, `findings_coder_was_observer = false`. Both rows retained |
| Shore disagrees with the corrective/preventive determination | A supersession with `supersession_reason = reclassification`. The original is retained, and the disagreement is inspectable — which is what makes it usable as inter-rater signal rather than lost as an overwrite |

**Write authority is never bound to liveliness.** [03 §11](../architecture/03-integration-contracts.md) singles this out as the property where "the DDS ownership model is actively wrong for this design: DDS binds OWNERSHIP to LIVELINESS, so a dark ship would *lose* authority over the mission records it alone can produce." `ConflictPolicy._forbid_liveliness_binding` makes it structural: there is no `is_connected()` input to any merge decision ([11 §7.2](11-outbox-sync-library.md)).

### 7.5 The minimal-capture fallback

[06 §4](../architecture/06-demo-decisions-and-assumptions.md) assumption A5 is rated **LOW** confidence — ship's force may not record afloat without enterprise prompting — with a stated fallback: "The edge record degrades to a minimal three-field capture — what was replaced, when, corrective or preventive — which is still sufficient for label construction. Findings coding is completed ashore with the reviewer flagged as non-observer."

Implemented as a declared minimum, not a second schema:

| Required in the minimal profile | Optional |
|---|---|
| `installed_item_id` (what) | `findings.*` except `taxonomy_version` |
| `failure_detected_at` (when, interval-censored) | `man_hours`, `narrative` |
| `maintenance_class` + `maintenance_class_basis` (corrective or preventive) | `parts_consumed[]` — with `parts_record_absent = true` |
| `action_taken_code` | `eic`, `apl` |

`GET /maintenance-history` exposes `capture_completeness ∈ {minimal | partial | full}` so a label consumer can weight accordingly. `max_unreconciled_records` on the divergence budget is deliberately `None` (§3.1): bounding the *count* of maintenance action records a dark hull may accumulate would mean refusing the 501st repair record, which is D8 restated as a quota.

---

## 8. Deferral handling — and why only `risk_disagreement` is prediction-quality evidence

[04 §6](../architecture/04-subapplication-architectures.md) rev 1 stated: "A deferral with accepted risk is a human judgment that the prediction overstated urgency, and it is informative to both the models and to calibration monitoring." **D34 corrects that**: "A deferral is a capacity or operational-tempo decision at least as often as a disagreement with the risk estimate; feeding it back as the latter biases models toward under-prediction." [03 §6](../architecture/03-integration-contracts.md) rev 2 implements the correction as `deferral_reason_class`.

### 8.1 The four classes and where each one goes

| `deferral_reason_class` | What it actually says | Prediction-quality evidence? | The consumer it is *for* |
|---|---|---|---|
| `capacity` | The executing activity did not have the man-hours or the skill | **No.** It says nothing about the item's hazard | RMC capacity modelling; Fleet Status |
| `tempo` | Operational schedule did not permit the work | **No.** The deployment moved, the pump did not | Fleet Status; OFRP planning |
| `parts_unavailable` | The materiel was not there | **No.** And it is a *supply* signal, not a model signal | Supply — allowance position, `MAINT_EFFECT`, BRF feedback ([07 §5.7](../architecture/07-navy-data-systems.md)) |
| `risk_disagreement` | A qualified human, having seen the prediction, judged it overstated the urgency | **Yes. Only this one.** | PdM calibration monitoring |

**Why the discrimination is directional and therefore dangerous.** Capacity, tempo, and parts deferrals are *systematically* more common than genuine disagreement, and they are *systematically* correlated with high workload — which is correlated with high failure rates. Fed back as "the model over-predicted," they push probabilities down precisely on the busiest, most degraded hulls. That is the same directional error as D1's censoring loop, arriving from a second direction, and — as with D1 — "every feedback signal points the wrong way and nothing detects it."

### 8.2 Mechanism

- **The class is required with no default**, and the `disagreement` block is required on `risk_disagreement` and forbidden on the other three (§3.5). Those are the only two validations that matter, and they are enforced at the API boundary.
- **`deferral.recorded` publishes all four classes, correctly typed.** Scheduling does not filter, and it does not tell PdM what to do with them: "Events carry facts, not instructions" (03 principle 3). The discrimination is the consumer's, and PdM's **consumer-driven conformance test** — contributed into `packages/contracts/conformance/maintenance/consumers/pdm/` — asserts that the class is always present, never defaulted, and that a non-`risk_disagreement` deferral never carries a `disagreement` block. That test is what makes the contract binding on a substituting Scheduling implementation.
- **`accepted_expected_consequence` snapshots what the optimizer said at deferral time**, including `conversion_method_version` and `weights_are_illustrative`. Without it, a later change to the consequence weights makes historical risk-acceptance decisions unreadable.
- **Risk acceptance carries an authority.** `risk_acceptance_authority` uses the [03 §7.2.1](../architecture/03-integration-contracts.md) `AuthorityClass` vocabulary; a deferral of a candidate above `criticality_floor` (constraint C7, §4.3) requires at least `planner`. This is what makes constraint C7 more than a modelling nicety: high-consequence work cannot slide into the deferral sink without a signature.

---

## 9. API surface

Base path `/api/v1/maintenance/` ([03 §4](../architecture/03-integration-contracts.md), `[C25]`). Every operation declares `x-substitution` and `x-side-effects`; `x-agent-eligible` is asserted only where `x-side-effects` is `none` or `proposal-only` (obligation 8, `[C1/D11]`).

### 9.1 Operations

| Operation | `x-substitution` | `x-side-effects` | Agent | Notes |
|---|---|---|---|---|
| `GET /work-candidates?asset_id=&installed_item_id=&driver=&status=&changed_since=&limit=&cursor=` | `required` | `none` | yes | [04 §6](../architecture/04-subapplication-architectures.md) |
| `GET /work-candidates/{id}` | `required` | `none` | yes | |
| `POST /work-candidates` | `required` | `state-changing` | no | Includes `driver=casualty` origination (§3.2.1) |
| `GET /work-orders?asset_id=&status=&changed_since=&cursor=`, `GET /work-orders/{id}` | `required` | `none` | yes | |
| `POST /work-orders` | `required` | `state-changing` | no | `202` + queued request at the edge |
| `PATCH /work-orders/{id}` | `required` | `state-changing` | no | `If-Match` required |
| **`POST /maintenance-action-records`** | `required` | `state-changing` | no | **The only writer of the label stream.** `work_order_id` nullable. Edge-writable |
| `POST /work-orders/{id}/actions` | `required` | `state-changing` | no | Thin wrapper on the above (§5.1). Retained from [04 §6](../architecture/04-subapplication-architectures.md) |
| `GET /maintenance-action-records?installed_item_id=&asset_id=&niin=&status_code=&changed_since=&cursor=` | `required` | `none` | yes | The rebuild path for PdM, Failure Intelligence, PMA, Supply, Registry, Design Advisory. **`niin=` added** — `[amendment]`, `42-redesign-case-builder.md` §18 item 12: every NIIN-scoped consumer (Design Advisory, Supply, Failure Intelligence) needs fleet-wide history for a part type, and without it that requires fanning in through Registry for no reason |
| `GET /maintenance-history?installed_item_id=&niin=&status_code=&capture_completeness=` | `required` | `none` | yes | [04 §6](../architecture/04-subapplication-architectures.md). Human/agent-facing projection over the above. **`niin=` added**, same correction |
| `POST /deferrals` | `required` | `state-changing` | no | §3.5 validations |
| `GET /deferrals?asset_id=&deferral_reason_class=&changed_since=&cursor=` | `required` | `none` | yes | |
| `GET /availabilities?asset_id=&changed_since=&cursor=`, `GET /availabilities/{id}` | `required` | `none` | yes | |
| `GET /availabilities/{id}/work-package` | `required` | `none` | yes | Singleton carve-out, enumerated in `x-naming-carve-outs` |
| **`POST /work-packages/plan`** | `required` | **`none`** | **yes** | **Solve only. Reserves nothing.** See §9.2 |
| `POST /work-packages` | `required` | `state-changing` | no | Materialises a solved run as a package |
| **`POST /work-packages/{id}/reserve`** | `required` | `state-changing` | no | Enters the saga (§4.5) |
| **`POST /work-packages/{id}/approve`** | `required` | `state-changing` | no | `If-Match`; authority `planner`; requires `saga_state == RESERVED` |
| `POST /work-packages/{id}/release` | `required` | `state-changing` | no | Explicit compensation; idempotent |
| `GET /work-packages/{id}`, `GET /work-packages?availability_id=&changed_since=&cursor=` | `required` | `none` | yes | |
| `GET /work-packages/{id}/explanation` | `required` | `none` | yes | [04 §6](../architecture/04-subapplication-architectures.md); §4.4 |
| `GET /optimizer-runs/{id}` | `internal` | `none` | no | Inputs, watermark, model, solution, dispositions |
| `POST /proposals` | `required` | `proposal-only` | yes | `work_candidate`, `interval_change` (§3.9) |
| `GET /proposals?status=&kind=&cursor=` | `required` | `none` | yes | |
| `POST /proposals/{id}/claim` | `required` | `state-changing` | no | `If-Match`. Lease, per [03 §7.2](../architecture/03-integration-contracts.md) `[D16]` |
| `POST /proposals/{id}/adjudicate` | `required` | `state-changing` | no | `If-Match` on the claimed ETag; authority re-derived (§3.9) |
| `POST /maintenance-action-records/bulk` | `required` | `state-changing` | no | Bulk, idempotent, epoch-fenced. `X-Backfill: true` suppresses side effects `[D30]` |
| `GET /pms-requirements?…`, `POST /pms-requirements` | `internal` | `none` / `state-changing` | read only | PMS catalogue administration |
| Optimizer configuration | `internal` | `state-changing` | no | Weights, bounds, `stalenessBounds` overrides |
| `GET /healthz`, `GET /readyz`, `GET /metrics` | `internal` | `none` | no | Per [03 §4](../architecture/03-integration-contracts.md) |

`changed_since` snapshot reads exist for **every** aggregate a declared consumer projects — work candidates, work orders, maintenance action records, deferrals, work packages, proposals — because "the event bus is not a rebuild source" `[D5]`.

### 9.2 Why `plan` is `x-side-effects: none` and `reserve` is separate

[04 §6](../architecture/04-subapplication-architectures.md) declares the planning operation `x-side-effects: none` and therefore agent-eligible — the Work-Package Planner agent calls it. **That declaration is only true if planning reserves nothing**, so the operation is split:

- `POST /work-packages/plan` solves over the §4.1 snapshot, persists an `OptimizerRun` with its dispositions, and returns the solution and explanation. It creates no `WorkPackage`, holds no stock, and emits no domain event. Persisting the run is a provenance write, not a domain state change — the same posture as PdM's `POST /scoring-runs`, which [04 §4](../architecture/04-subapplication-architectures.md) also declares `none`.
- `POST /work-packages` then `/reserve` then `/approve` are each `state-changing` and none is agent-eligible.

**A single `plan` operation that also reserved would be a declared-`none` operation holding fleet stock**, reachable by an agent under `x-agent-eligible`. That is the C1/D11 eligibility gate defeated from the inside — the annotation would be correct in form and false in substance — and it is worth the extra two operations to make it impossible.

### 9.3 Problem types

All errors are `application/problem+json` per [03 §4](../architecture/03-integration-contracts.md), under `urn:fathom:problem:maintenance:`. The set is closed; adding one is a contract change.

| Suffix | Status | Raised when |
|---|---|---|
| `not-edge-writable` | 423 | A server-authoritative aggregate is written at the edge (§3.3, §7.1) |
| `treatment-record-is-derived` | 422 | A client supplied `triggering_driver`, `triggering_prediction_id`, or `policy_version` (§5.4 rule 0) |
| `item-not-in-baseline` | 422 | `work_candidate` proposal names an item absent from the current baseline (§3.9) |
| `interval-delta-out-of-bounds` | 422 | `interval_change` exceeds the bounded delta — rejected *before* authority is consulted (§3.9) |
| `proposal-stale` | 409 | Superseded `baseline_epoch` or elapsed `valid_until` at adjudication (§3.9) |
| `staleness-bound-exceeded`, `antecedent-unresolved`, `prediction-invalidated-in-scope`, `lead-time-unavailable`, `clock-dispersion-exceeded` | 409 | The five optimizer refusals (§4.1). Distinct types, never one generic "not ready" |
| `reservation-not-confirmed` | 409 | `/approve` called when `saga_state != RESERVED` (§4.5.4 R7) |
| `reservation-deadline-elapsed` | 409 | `/approve` after `monotonic_deadline`; the hold is gone (§4.5.6) |
| `replan-exhausted` | 409 | Generation bound reached (§4.6) |
| `deferral.*` (three) | 422 | The §3.5 class validations |
| `jcn-block-exhausted` | **never raised** | §6.4. Recorded here as a deliberate absence: the record is accepted with a null JCN instead |

### 9.4 Agent access — agents are never topic consumers `[C19]`

[03 §6](../architecture/03-integration-contracts.md): "**Agents are never direct topic consumers.** Agents obtain state through tools (document 01 §8.3). Where a downstream capability is realized by an agent, the consumer named here is the platform component that bridges to it `[C19]`." [09 §10](09-monorepo-and-conventions.md) rule 15 repeats it.

Scheduling's compliance is structural rather than asserted:

- **No agent subscribes to `fathom.maintenance.*`.** Every consumer in §10.2 is a sub-application or a platform component. The Work-Package Planner agent named in [04 §6](../architecture/04-subapplication-architectures.md) reaches Scheduling only through tool-server proxied HTTP against the operations marked `x-agent-eligible` in §9.1.
- **Agent-eligible means `x-side-effects: none` or `proposal-only`, with no exceptions in this service.** The planner agent can `plan`, read explanations, and raise proposals. It cannot `POST /work-packages`, cannot `/reserve`, cannot `/approve`, and cannot write a maintenance action record. The three most consequential operations in this document are unreachable by any agent, and §9.2 explains why `plan` had to be split for that to be true.
- **`POST /maintenance-action-records` is not agent-eligible even though it is a capture operation.** An agent asserting what a maintainer did is a fabricated label, and the whole of §5 exists to prevent fabricated labels. Capture is a human act with a human's identity on it (`recorded_by`, `findings_coder_was_observer`).
- **Proposals carry a human identity even when raised by an agent.** [03 §7.2.1](../architecture/03-integration-contracts.md): "An agent's delegated token still carries a human's identity and roles, and it is that identity's roles that are checked here." The §3.9 authority check therefore operates on the human, and an accountable-autonomous agent cannot adjudicate its own proposal.

### 9.5 Agent tool manifests

**[AMENDMENT — closes a BLOCKING gap.]** §9.4 above reasons at length about the Work-Package Planner reaching this service "through tool-server proxied HTTP against the operations marked `x-agent-eligible` in §9.1" and then shipped no manifest for it to reach them through. Flagged by `40-copilot.md` §16 correction 8 (blocking) as gap C.

`packages/agent-tooling/manifests/maintenance/`:

| Manifest | Consumer | Purpose | Operations |
|---|---|---|---|
| `maintenance-history-lookup.v1` | Maintainer Copilot | Read-only maintenance-history surface: what has been done to this item, what's open against this hull, why something hasn't been fixed yet | `GET /maintenance-history?installed_item_id=&status_code=&capture_completeness=`, `GET /maintenance-action-records?installed_item_id=&asset_id=&status_code=&…`, `GET /deferrals?asset_id=&deferral_reason_class=&…`, `GET /work-orders?asset_id=&status=&…` (`status=open` default), `GET /work-orders/{id}`, `GET /availabilities?asset_id=&…` |
| `maintenance-work-package-planner.v1` | Work-Package Planner (out of demonstration scope, 06 §7) | The planner's own binding — `POST /work-packages/plan` and its explanation read, per §9.2's split from `reserve`/`approve`. Not detailed here; this agent is not built in this wave | `POST /work-packages/plan` (`x-side-effects: none`, §9.2), `GET /work-packages/{id}/explanation` |

**`maintenance-history-lookup.v1`'s selection is fully specified in `40-copilot.md` §4.2.4**, including task-scoped descriptions, parameter defaults, and the deliberate exclusions (`POST /work-packages/plan` — the planner's, not this agent's; `POST /proposals`/`GET /proposals`; every `state-changing` row). Reproduced here only by reference, per the convention `21-telemetry.md` §9.5 and `22-pdm.md` §10.1 use — the manifest's home is this service's directory and its conformance test belongs in this service's suite (03 §8.4), even though another document did the selection work.

Both manifests select only `x-side-effects: none` operations (03 §8.1), pin `api_major: 1`, ship a conformance test inside this service's suite, and declare a reviewed `purpose` (03 §8.5). `POST /maintenance-action-records` remains **excluded from every manifest** regardless of consumer — §9.4's third bullet is unconditional, not agent-specific.

---

## 10. Events

### 10.1 Envelope construction

Every event is built by `fathom_sync.emit()` ([11 §5](11-outbox-sync-library.md)); no envelope is hand-rolled. Fields Scheduling supplies:

| Envelope field | Value |
|---|---|
| `event_id` | uuid4, minted by the library |
| `event_type` | `fathom.maintenance.<aggregate>.<verb>`, `snake_case` `[C26]` |
| `event_version` | `1` |
| `occurred_at` | the domain instant — `action_completed_at`, `authorized_at`, `approved_at`, candidate creation |
| `recorded_at` | persistence time |
| `producer` | `maintenance` + service version |
| **`producer_node`** | `"enterprise"`, **or `"edge:<asset_id>"` for a record captured afloat** |
| `correlation_id` | from `X-Correlation-Id`, minted when absent |
| `causation_id` | the `event_id` of the immediately preceding event where one exists — e.g. `reservation_set.confirmed` → `work_package.approved`; `prediction.updated` → `work_candidate.created` |
| `scope` / `subject` | exactly one identifier matching `scope` `[C11]` |
| `baseline_epoch` | present on every event whose correctness depends on configuration — all six |
| `classification` | `ClassificationLabel`, with `inherited_from` as the union of inputs on derived values (`expected_consequence` inherits from the prediction) |
| `replay` | `false` except from the bulk/backfill path |
| `clock` | full block: `monotonic_seq`, `hlc`, `source_time`, `ingest_time`, `sync_quality` (all six sub-fields) |

**`producer_node` matters here more than anywhere else in the system.** Scheduling runs as two independent instances of one slug, and both write to the same aggregate family. Without `producer_node`, the enterprise and edge `monotonic_seq` sequences collide and "the dedup key silently drops an event" ([03 §5.4](../architecture/03-integration-contracts.md)) — and the event it drops is a maintenance action record, i.e. a label. A CI test asserts every edge-emitted envelope carries `edge:<asset_id>` and that the edge profile's `PUBLISHES` set is exactly `{fathom.maintenance.maintenance_action.v1}`.

### 10.2 Published events

| Event | Topic | Partition key | Compaction key | `scope` / `subject` | Consumers ([03 §6](../architecture/03-integration-contracts.md)) |
|---|---|---|---|---|---|
| `work_candidate.created` | `fathom.maintenance.work_candidate.v1` | `asset_id` | `candidate_id` | `installed_item` / `installed_item_id` | `supply`, `fleet-status` |
| `work_order.opened` | `fathom.maintenance.work_order.v1` | `asset_id` | `work_order_id` | `installed_item` / `installed_item_id` | `supply`, `fleet-status`, `registry` |
| **`maintenance_action.recorded`** | `fathom.maintenance.maintenance_action.v1` | `asset_id` | `action_record_id` | `installed_item` / `installed_item_id` | `pdm`, `failure-intel`, `registry`, `supply`, `pma`, `design-advisory` |
| `deferral.recorded` | `fathom.maintenance.deferral.v1` | `asset_id` | `deferral_id` | `installed_item` / `installed_item_id` | `fleet-status`, `pdm` |
| `work_package.proposed` | `fathom.maintenance.work_package.v1` | `asset_id` | `work_package_id` | `asset` / `asset_id` | `supply`, `fleet-status` |
| `work_package.approved` | `fathom.maintenance.work_package.v1` | `asset_id` | `work_package_id` | `asset` / `asset_id` | `supply`, `fleet-status`, `registry` |
| `proposal.created` / `.adjudicated` / `.expired` | `fathom.maintenance.proposal.v1` | `asset_id` (or `class_id` at class scope) | `proposal_id` | per the proposal's subject | `gateway`, `notification`, `audit` |

**Compaction key is never the partition key** `[D5]`. Compacting `maintenance_action.v1` on `asset_id` would collapse a hull's entire maintenance history to one record — the label stream, deleted by a broker setting.

The partition key is `asset_id` while the envelope's `subject` carries only `installed_item_id`. The producer resolves the hull from its own read model, and **that resolution must work offline at the edge** — it does, because the edge holds the configuration cache for its own hull and needs no other.

### 10.3 `maintenance_action.recorded` — the corrected payload

[03 §6](../architecture/03-integration-contracts.md): "installed item, action taken, parts consumed, findings code, `failure_indicator`, **`triggering_driver`, `triggering_prediction_id`, `policy_version`** `[D1, D21]`… The three added fields record the treatment-assignment mechanism, without which neither calibration nor causal analysis can condition on the intervention policy."

```
maintenance_action.recorded payload {
  action_record_id, jcn?, supersedes_action_record_id?, supersession_reason?
  installed_item_id, position_id, asset_id, system_id?, niin?
  identity_provisional, eic?, apl?, work_center
  action_taken_code, action_taken_set_complete
  man_hours?, parts_consumed[], parts_record_absent
  maintenance_class, maintenance_class_basis
  failure_indicator, failure_indicator_rule_version
  findings { cause_code, when_discovered_code, status_code, deferral_code?,
             taxonomy_version }
  findings_completed_ashore, findings_coder_was_observer
  failure_detected_at { earliest, latest, basis }
  action_started_at, action_completed_at
  triggering_driver?, triggering_candidate_id?, triggering_prediction_id?
  triggering_prediction_ref?, policy_version?          ← the three corrected fields
  prediction_in_evidence_id?                           ← §5.4.2. [RECONCILE RC-4]
  holdout_member
  work_order_id?, authorization_state                  ← nullable BY DESIGN
  capture_completeness
  quality_warnings[]                                   ← §5.7. Doubt travels with the record
}
```

**`triggering_driver` is one of exactly five values or absent** — `prediction | pms_periodicity | casualty | opportunistic | opportunistic_pms`, per §5.4.1. There is no `unknown` on the wire; absence *is* unknown. The consumer-driven conformance test PdM contributes (§10.5) asserts the enum and asserts that `triggering_prediction_id` is present whenever the driver is `prediction` or `opportunistic` and absent otherwise, because [22 §4.2](22-pdm.md) treats an unresolvable treatment reference as "a data-quality defect, recorded and counted" that can mark a whole label set `powered = false`.

`narrative` is **excluded from the event payload** and served only from `GET /maintenance-action-records/{id}`. It is untrusted free text (03 §9), it is the largest field, and every consumer of this event is a structured consumer. `payload_ref` is not required at [06 §7](../architecture/06-demo-decisions-and-assumptions.md)'s volumes (~14,000 actions over 24 months), and no event here approaches the broker limit `[D27]`.

### 10.4 Consumed events

Enumerated, never wildcarded `[C38]`. `EVENT_HANDLERS` in `events/consumers.py` is keyed by `event_type`; `events/catalog.py`'s `CONSUMES` must equal `helm/values.yaml`'s `events.consumes` must equal [03 §6](../architecture/03-integration-contracts.md)'s rows, enforced by `tools/check_event_catalog.py`.

| Consumed event | Read model | Effect |
|---|---|---|
| `prediction.updated` | `rm_prediction` | Generate/refresh `prediction`-driven candidates. **`p_failure` may be null** — store as null, never zero (§4.2.2). Store `reference_class`, `calibration_population`, `fallback_level`, `population_hazard_rate` |
| `prediction.invalidated` | `rm_prediction` | Withdraw affected candidates (`prediction_invalidated`); refuse to solve while any in-scope prediction is invalidated (§4.1 refusal 3) |
| `criticality_tier.assigned` | `rm_criticality` | Refresh consequence weights; re-score affected candidates. The transition annotation is retained so a level shift is not read as fleet degradation `[D36]` |
| `casrep_risk.raised` | `rm_casrep_risk` | Generate a candidate with **`driver = prediction`**, `source_prediction_id` from the evidence references — **not** `casualty` (§3.2.1) |
| `casrep_risk.cleared` | `rm_casrep_risk` | Withdraw the corresponding candidate where no other driver holds it open |
| `part_availability.changed` | `rm_part_availability` | Update availability, `lead_time`, `condition_code`, interchangeable group. **Not a replan trigger** (§4.6 rule 3) |
| `requisition.status_changed` | `rm_requisition` | Projected availability; replan trigger **only** for a NIIN in the current package |
| `allowance_shortfall.detected` | `rm_allowance` | Replan trigger for an in-package NIIN; feeds `parts_unavailable` deferral evidence |
| `allowance.updated` | `rm_allowance` | Validate `estimated_scope.required_parts` against the revised COSAL/APL position |
| `reservation_set.confirmed` | `reservation_set` | **Saga: `RESERVING`/`INDETERMINATE` → `RESERVED`.** The authority for confirmation (§4.5 rule R5) |
| `reservation_set.released` | `reservation_set` | Saga: `RELEASE_PENDING` → `RELEASED`; or `RESERVED` → `EXPIRED_UNAPPROVED` on TTL expiry |
| `asset.status_changed` | `rm_asset` | OFRP phase and deployment constraints (C4, C5) |
| `configuration.baseline_changed` | `rm_configuration` | **Epoch fence.** Withdraw candidates on removed items; advance `baseline_epoch`; block ahead-of-epoch events until the antecedent applies `[D3, D4]` |
| `usage_counter.updated` | `rm_usage` | Recompute usage-based PMS due dates, keyed on `(installed_item_id, counter_type, counter_epoch)` |
| `usage_counter.reset` | `rm_usage` | **Open a new epoch and recompute** the due date — never carry the prior epoch's accumulation forward `[D9]` |
| `causal_finding.published` | `rm_causal_finding` | Annotate candidates whose failure mode has an adjudicated cause; surface in the explanation. **Never auto-changes an interval** — that requires an `interval_change` proposal (§3.9) |
| `taxonomy_version.published`, `taxonomy_entry.superseded`, `crosswalk.published` | `rm_taxonomy_3m` | Refresh the cached 3-M projection (§5.6). **[OPEN OQ-5]** — [12 §3.4](12-reference-data-taxonomy.md) logs as OD-7 that platform-service topics are absent from [03 §6](../architecture/03-integration-contracts.md)'s catalog, so these three cannot yet have consumer-driven conformance tests |

Every handler is idempotent on `event_id`, and the inbox records receipt and applies state **in one transaction**; only rows with `processed_at` set suppress redelivery `[D2]`.

### 10.5 Consumer-driven conformance tests Scheduling owes

Per [03 §10](../architecture/03-integration-contracts.md) and [09 §4.7](09-monorepo-and-conventions.md), a declared consumer contributes a test into the producer's suite at `packages/contracts/conformance/<producer>/consumers/maintenance/`. Scheduling owes one to `pdm`, `supply`, `registry`, `telemetry`, `fleet-status`, `failure-intel`, and (pending OQ-5) `reference-data`. Each asserts the guarantee Scheduling actually depends on — for `pdm`, that `p_failure` may be null with `reference_class = class_estimate` and that `population_hazard_rate` is then present; for `supply`, that `part_availability.changed` carries `lead_time` and `condition_code` `[D24]`.

---

## 11. Testing

Four tiers per [09 §4.7](09-monorepo-and-conventions.md). The three tests below are the ones this document exists to require.

### 11.1 Conformance suite wiring

```python
# services/maintenance/tests/conformance/test_suite.py
"""Collects the shared conformance suite for this slug into this service's test run.

The suite lives in packages/contracts/conformance/maintenance/ (path fixed by 03 §10).
Do not add, skip, or modify tests here. Fixtures are in conftest.py.
"""
from fathom_contracts.conformance.maintenance import *      # noqa: F401,F403
```

`tests/conformance/conftest.py` supplies exactly the four fixtures — `conformance_target`, `event_tap`, `fault_injector`, `reference_dataset` — and nothing else. No shared test is edited, skipped, xfailed, or subclassed.

The reference dataset is the synthetic corpus from `data/synthetic/` ([13](13-synthetic-data-generator.md)), which already contains the label corruptions (§11.6) and the edge scenarios (§11.4), so the conformance run and the defect-specific tests draw on one corpus rather than on hand-authored fixtures that drift.

### 11.2 Supply is a contract-verified fake, not a mock

Reservation tests run against Supply's **reference implementation** from `packages/contracts/conformance/supply/` ([26 §9.2](26-supply.md)), driven by Supply's committed OpenAPI, wrapped in a fault-injecting proxy.

**This is not a stylistic preference — it is the control that caught RC-2.** Rev 1 assumed `POST /reservation-sets` accepted a `client_reference` body field and that `DELETE /reservation-sets/{id}` accepted it as a release handle. Both were wrong (§3.8, §4.5.5). A hand-written mock would have encoded rev 1's assumptions faithfully, passed every test in this document, and failed on first contact with Supply — and it would have failed in the compensation path, i.e. only under fault, i.e. exactly where D6 lives. A test suite that validates a document's assumptions rather than the counterparty's contract is worse than no suite, because it converts an integration failure into a production one.

Two standing rules follow:

- **The request body is validated against Supply's committed OpenAPI schema, not against an example in this document.** Where they disagree, Supply's schema wins and this document is wrong (per the Precedence row).
- **An unimplemented Supply operation fails loudly** as an unmet cross-service dependency rather than being stubbed. The `extend` path (§4.5.6) in particular must not be faked: a stub that always succeeds would hide the `extend_count ≤ 8` cap, and the cap is what stops an extension loop from becoming the unbounded hold the TTL exists to prevent.

### 11.3 `test_no_orphaned_reservations_under_partial_failure` — D6's remedy, verified

The single most important test in this sub-application.

**Shape.** A matrix over (a) fifteen fault points × (b) two hidden Supply outcomes, each run to saga convergence, then asserted.

| Fault point | Injected |
|---|---|
| F1 | Crash after `RESERVING` commit, before the HTTP send |
| F2 | Connection reset during send |
| F3 | Supply receives and creates the set; response lost |
| F4 | Supply receives and rejects (409); response lost |
| F5 | Supply returns 5xx after creating the set |
| F6 | Supply returns 5xx without creating the set |
| F7 | Read timeout exceeding `reserve_timeout` |
| F8 | `201` returned, `reservation_set.confirmed` never published |
| F9 | `201` returned, `reservation_set.confirmed` published late (after the corroboration bound) |
| F10 | Crash after `RESERVED`, before publishing `work_package.proposed` |
| F11 | Crash during compensating `DELETE`; pod restarts; reaper takes over |
| F12 | `201` received but the process dies **before `reservation_set_id` is persisted** — the R2 case rev 1 could not represent. Recovery is by idempotent re-issue (§4.5.5 step 1) |
| F13 | As F12, and Supply is then unreachable for the whole `max_reserve_attempts` window — the saga must reach `AWAITING_TTL_EXPIRY` and then `RELEASED` on the expiry event, with no operator action |
| F14 | `422 fence-requires-epoch` / stale `expected_stock_epoch` rejection — must land in `RESERVATION_REJECTED` → `REPLAN_REQUIRED` with a **refreshed** epoch, never retried unchanged and never retried with `fence: "none"` (§4.1.1) |
| F15 | `extend` returns `409 reservation-set-expired` — must reach `EXPIRED_UNAPPROVED`, never resurrect the set, and never publish `work_package.approved` (§4.5.6) |

**Invariants asserted after convergence, for every cell:**

1. **No orphan.** `supply.reservations_held(work_package_id)` is non-empty **if and only if** the saga's terminal state is `APPROVED` or its current state is `RESERVED`/`APPROVAL_PENDING`. In every `REPLAN_REQUIRED`, `REPLAN_EXHAUSTED`, `ABANDONED`, or `EXPIRED_UNAPPROVED` outcome, held reservations are **empty**.
2. **No premature approval.** Over the `event_tap`, for every `work_package.approved`, a `reservation_set.confirmed` with the matching `reservation_set_id` appears **earlier** in the tap. Asserted as an ordering predicate over the tap, not as a state check `[D6]`, [03 §6](../architecture/03-integration-contracts.md).
3. **No per-NIIN loop.** Exactly one `POST /reservation-sets` per attempt, carrying **all** lines; zero calls to any per-item reservation operation. Asserted by call count and by request-body line count, which is what would have caught "37 of 40 succeed."
4. **At most one non-terminal intent** per work package throughout (the R3 partial unique index is also asserted to exist in `pg_indexes`).
5. **Idempotent re-issue creates no second set.** Where the saga re-issues, Supply's set count for that `Idempotency-Key` is exactly 1, and exactly one `reservation_set.confirmed` appears in the tap. Asserted against Supply's store, not against Scheduling's belief about it.
6. **Release is idempotent.** A second `DELETE` on the same `reservation_set_id` yields `204`, and **no second `reservation_set.released` is emitted** ([26 §3.9](26-supply.md)) — asserted over the tap, because a double release would restore availability twice in Scheduling's own read model.
7. **No wall-clock timing.** A backward clock step is injected during the saga; every deadline still fires correctly `[D29]`.
8. **The reaper alone is sufficient.** A variant kills the pod at each fault point with no client retry; the reaper converges the saga unaided.
9. **The body sent is schema-valid against Supply's OpenAPI**, carries `fence: "strict"`, and carries an `expected_stock_epoch` on every line that equals the epoch recorded in the run's `input_watermark`. This is the assertion that would have caught rev 1's four field errors (§3.8) at build time rather than at integration.
10. **Orphan lifetime is bounded even in the unrecoverable case.** In F13, no reservation outlives `ttl_seconds`; the test advances Supply's clock rather than waiting, and asserts the terminal state is reached with zero held reservations and zero operator interventions.

A property-based variant (Hypothesis) generates random fault sequences and line counts and asserts invariants 1–4 as a stateful machine, because the fifteen enumerated points are the ones imagined, and D6 was found by imagining one that had not been.

### 11.4 `test_edge_recording_six_week_disconnect` — D8's remedy, verified

Loads `data/synthetic/scenarios/edge/edge-ssn-6wk-*.yaml` ([13 §15](13-synthetic-data-generator.md)), replays the timeline against a **network-partitioned** edge instance, reconnects, and asserts against the scenario's `expected_post_reconciliation` golden file. Per [13 §15.4](13-synthetic-data-generator.md), **a golden file regenerated to make a test pass is a contract change** and requires the same review as an edit to [03 §11](../architecture/03-integration-contracts.md).

| # | Assertion | Source |
|---|---|---|
| 1 | `POST /maintenance-action-records` succeeds while disconnected, with `work_order_id = null` and full findings coding | [06 §4](../architecture/06-demo-decisions-and-assumptions.md), D8 |
| 2 | `POST /work-orders` at the edge returns `202` + queued request; `PATCH … status=authorized` returns `423`; **no authorization is ever fabricated afloat** | [03 §11](../architecture/03-integration-contracts.md) |
| 3 | `assert_edge_write_surface()` fails the pod when a state-changing route is added to the edge profile without an allowlist change | §7.1 |
| 4 | On reconnect, the edge action record and the shore-authorized work order for the same equipment **both persist**, neither overwritten | [13 §15.2](13-synthetic-data-generator.md) |
| 5 | An enterprise `UPDATE` of the edge record is **rejected**; a supersession row is recorded instead | [11 §7.3](11-outbox-sync-library.md) |
| 6 | Minimal three-field capture yields a usable label; ashore completion sets `findings_completed_ashore = true`, `findings_coder_was_observer = false` | [06 §4](../architecture/06-demo-decisions-and-assumptions.md) A5 |
| 7 | The at-sea repair carries `triggering_driver = "casualty"`, `triggering_prediction_id = null`, `policy_version = null` | [13 §15.2](13-synthetic-data-generator.md) |
| 8 | Every edge-emitted envelope carries `producer_node = "edge:<asset_id>"`; the edge `PUBLISHES` set is exactly `{fathom.maintenance.maintenance_action.v1}` | [03 §5.4](../architecture/03-integration-contracts.md) |
| 9 | Provisional identity: the new pump starts at zero usage, the retired item keeps its hours, across confirmed / **superseded** / duplicate-mint sub-cases | [13 §15.2](13-synthetic-data-generator.md) cases 1a–1c |
| 10 | A backward clock step and `dispersion_ms` exceeding the inter-write interval do not reorder or drop records; ordering is `(producer, producer_node, monotonic_seq)` | [13 §15.3](13-synthetic-data-generator.md) |
| 11 | Duplicate and out-of-order delivery are idempotent on `action_record_id` | [13 §15.3](13-synthetic-data-generator.md) |
| 12 | The `maintenance_action_record` divergence budget **exceeds** the scenario's 42 days — a `helm unittest` assertion on the chart, so the demonstration cannot breach the budget it exists to satisfy | [11 §9.1](11-outbox-sync-library.md) |
| 13 | A telemetry divergence breach does **not** gate maintenance action recording | [11 §9.1](11-outbox-sync-library.md) rule 3 |
| 14 | JSN block exhaustion afloat yields an accepted record with `jcn = null`, `jcn_assignment_deferred = true`, assigned ashore in `monotonic_seq` order | §6.4 |

### 11.5 Optimizer and treatment-record tests

| Test | Asserts |
|---|---|
| `test_refuses_outside_staleness_bound` | Each of the five §4.1 refusals returns its distinct problem type and increments `fathom_staleness_refusals_total{reason}` |
| `test_snapshot_is_consistent` | A concurrent writer committing during a solve does not change the solution; the run's `snapshot_txid` is recorded |
| `test_explanation_totality` | `count(dispositions) == count(candidates_in_scope)`, and the run aborts on mismatch |
| `test_solve_is_deterministic` | Same watermark + seed + solver version → byte-identical solution and dispositions |
| `test_null_p_failure_is_not_zero` | A `class_estimate` candidate with a high `population_hazard_rate` **out-ranks** an `item`-class candidate with a low `p_failure`. This is D7's exact failure mode inverted into a test |
| `test_conversion_is_not_reimplemented` | Static: no arithmetic on `p_failure`, `population_hazard_rate`, or `rul` appears anywhere under `optimizer/` outside `consequence.py`'s call to `fathom_schemas.decision`. Guards RC-1's closure against a well-meaning reintroduction (§4.2.1) |
| `test_operating_fraction_is_supplied` | A class-rate candidate scored with `operating_fraction = 1.0` ranks materially higher than the same candidate at `0.667`; the adapter never passes the default silently where a mission calendar exists (§4.2.1) |
| `test_timing_p10_not_synthesized` | `timing_p10 is None` for every `class_rate_converted` basis, and constraint C2 reads `timing_p50` in that case `[D19]` |
| `test_risk_posture_surfaces` | The posture and `conversion_version` appear in every disposition and explanation payload (§4.2.3) |
| `test_triggering_driver_vocabulary` | Emitted values are a subset of PdM's five; `pms` and the string `unknown` **never** appear on the wire; absence encodes unknown (§5.4.1) |
| `test_opportunistic_split_is_preserved` | An opportunistic intervention where a prediction contributed emits `opportunistic` with a non-null `triggering_prediction_id`; one where only periodicity contributed emits `opportunistic_pms` with a null one. The two are never collapsed `[22 §4.2]` |
| `test_pms_merge_does_not_pollute_treatment_field` | A merge product whose timing was set by periodicity emits `triggering_prediction_id = null` and carries the id in `prediction_in_evidence_id` (§5.4.2) |
| `test_holdout_never_carries_prediction_treatment` | No policy-frozen item's record carries `triggering_driver ∈ {prediction, opportunistic}` or a non-null `triggering_prediction_id` — [13 §10.3](13-synthetic-data-generator.md) gate G-7, asserted on Scheduling's emissions |
| `test_policy_version_namespaces_do_not_collide` | `cgp:` and `ipv:` prefixes are present and distinct across drivers (§5.4.4) |
| `test_no_tier_branch` | Static check: `tier` appears in no conditional under `optimizer/` |
| `test_no_rul_below_item_class` | `rul` is never read where `reference_class != item` `[D19]` |
| `test_holdout_is_admission_filter` | Holdout items produce no prediction-driven candidate and DO produce PMS/casualty candidates; `reason_code = holdout_excluded` |
| `test_casrep_risk_maps_to_prediction_driver` | A `casrep_risk.raised`-derived candidate has `driver = prediction`, never `casualty` (§3.2.1) |
| `test_merge_driver_is_timing_determinant` | A prediction pulling a PMS task forward yields `driver = prediction`; a prediction inside the tolerance yields `pms`; `source_prediction_id` is retained in both (§3.2.2 rules 4–5) |
| `test_treatment_record_rejects_client_values` | Any of the three fields on the request → `422` (§5.4 rule 0) |
| `test_treatment_record_never_guesses` | Zero or ≥2 open candidates for the item → `triggering_driver` **NULL**, and no `triggering_prediction_id` |
| `test_deferral_class_validations` | `risk_disagreement` without `prediction_ref` → `422`; `capacity` with a `disagreement` block → `422`; missing class → `422` (§3.5) |
| `test_convergence_is_monotone` | A failed NIIN line never re-appears unchanged in generation `g+1`; `part_availability.changed` triggers no replan; `REPLAN_EXHAUSTED` is reached and explained `[D20]` |
| `test_interval_change_blast_radius` | A proposal declaring `item` scope on a class-wide MRC is derived as `class` and requires `fleet_authority` + dual control (§3.9) `[D16]` |

### 11.6 `test_findings_capture_under_label_corruption`

Drives the eight [13 §9.10](13-synthetic-data-generator.md) corruptions through `POST /maintenance-action-records` and asserts the §5.7 table row by row. The two properties that make it meaningful:

- **Every corrupted record is accepted (`201`).** A capture API that rejects realistic deckplate input causes the recording to stop, which is D8 by attrition. Any `4xx` other than the three deliberate ones (missing `maintenance_class`, malformed interval, client-supplied treatment field) fails the test.
- **Every corruption is either represented structurally or flagged.** Asserted per row: `candidate_modes[]` is never flattened to a single mode; duplicates dedup on `action_record_id` and not on `jcn`; `parts_record_absent` is explicit; interval-censored timing survives date rounding; missing `triggering_driver` becomes NULL; wrong-item attribution produces a warning naming the sibling position **without moving the record**.

A third assertion guards the ceiling honestly: the wrong-findings-code corruption produces **no** warning, and the test asserts that, because the alternative is a false claim that capture-time validation can detect it. [06 §2](../architecture/06-demo-decisions-and-assumptions.md) A5 rates this LOW confidence and names actionable precision as the metric that degrades; pretending otherwise in a test would hide it.

### 11.7 Fault-injection and event tests

- **Fault injection**: interrupt every state-changing operation mid-flight and assert **no state change without its event** (obligation 2). This is the observable property that stands in for the outbox in a substitution context `[D24]` — the outbox itself is a program implementation standard and is not in the conformance suite.
- **Event tests**: envelope completeness including the full `clock` block, `producer_node` correctness in both profiles, partition-key correctness, compaction-key ≠ partition-key, and within-partition ordering.
- `tools/check_event_catalog.py` exits 0: `catalog.py` ≡ `values.yaml` ≡ [03 §6](../architecture/03-integration-contracts.md).

---

## 12. Deployment

**One image, one chart, two values files.** [ESTABLISHED HERE]. The edge is never a separate build: a divergent edge image is how the edge code path stops being exercised, and D8 exists because the edge was an afterthought. The image is promoted **by digest** and the same digest runs on the hull.

### 12.1 Enterprise variant — `helm/values.yaml`

```yaml
slug: maintenance
apiMajor: 1
profile: enterprise                        # ADDED KEY, this service. Drives the write gate

image:
  repository: registry.internal/fathom/maintenance
  digest: ""                               # sha256:… set by CI on merge
  pullSecrets: [fathom-registry]

replicaCount: 2

resources:
  requests: { cpu: 250m, memory: 512Mi }    # the solver is the driver of these figures
  limits:   { cpu: "2",  memory: 2Gi }

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 65532
  runAsGroup: 65532
  fsGroup: 65532
  seccompProfile: { type: RuntimeDefault }
containerSecurityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities: { drop: ["ALL"] }
nodeSelector: { fathom.navy/pool: program }

app:
  logLevel: INFO
  config:
    stalenessBoundSeconds: 3600            # the service-wide floor; per-source below
    stalenessBounds: { … }                 # §4.1
    jsnOriginatorAlpha: "F"                # §6.2. Reserved for the demonstration
    jsnBlockSize: 512
    consequenceWeights: { missionEssential: 10.0, missionDegrading: 3.0, routine: 1.0 }
    weightsAreIllustrative: true           # §4.2.3. Rendered to the operator
    riskPosture:                           # §4.2.3. 22 §7.4 [PLACEHOLDER P-17]
      missionEssential: AVERSE
      missionDegrading: NEUTRAL
      routine: NEUTRAL
    operatingFractionDefault: 0.667         # §4.2.1. 07 §5.5 sea-going tempo
    # NOTE: no conversionMethodVersion. The conversion is fathom_schemas.decision and its
    # `conversion_version` is read FROM the library and recorded on the run (§4.2.1).
    # A configurable version here would let a chart edit silently relabel provenance.
    failureIndicatorRuleVersion: "fi-1"
    maxReplanGenerations: 3
    minReplanIntervalSeconds: 900
    intervalChangeMaxDeltaFraction: 0.25
    timingToleranceDays: 14
    reserveTimeoutSeconds: 30
    confirmCorroborationBoundSeconds: 120
    maxReserveAttempts: 3
    reservationTtlSeconds: 172800          # 48 h. Within Supply's [60, 604800] range
                                           # [26 §3.3]. This is the ORPHAN LIFETIME BOUND
                                           # in the unrecoverable case (§4.5.5 step 3)
    reservationFence: strict               # §4.1.1. NEVER "none"
    extendLeadSeconds: 3600                # §4.5.6. Extend before the deadline, not after
    maxReservationLines: 250               # mirrors Supply's max_lines [26 §3.3]
    reaperIntervalSeconds: 30

optimizer:
  enabled: true
  solver: cp-sat
  numSearchWorkers: 1                      # determinism over throughput. §4.3
  maxTimeSeconds: 300
  seed: 20260804

database:
  clusterName: fathom-maintenance-pg
  name: maintenance
  secretRef: fathom-maintenance-pg-app
  poolSize: 10
  maxOverflow: 5
migrations: { enabled: true, backoffLimit: 0 }

events:
  brokers: redpanda.fathom-data.svc.cluster.local:9093
  schemaRegistry: http://redpanda.fathom-data.svc.cluster.local:8081
  consumerGroup: fathom-maintenance-v1
  publishes:
    - fathom.maintenance.work_candidate.v1
    - fathom.maintenance.work_order.v1
    - fathom.maintenance.maintenance_action.v1
    - fathom.maintenance.deferral.v1
    - fathom.maintenance.work_package.v1
    - fathom.maintenance.proposal.v1
  consumes:
    - fathom.pdm.prediction.v1
    - fathom.pdm.criticality_tier.v1
    - fathom.fleet-status.casrep_risk.v1
    - fathom.supply.part_availability.v1
    - fathom.supply.requisition.v1
    - fathom.supply.allowance_shortfall.v1
    - fathom.supply.reservation_set.v1
    - fathom.registry.asset.v1
    - fathom.registry.configuration_baseline.v1
    - fathom.registry.allowance_document.v1     # [AMENDMENT] was allowance.v1, a topic Registry never publishes on (20 §3.1)
    - fathom.telemetry.usage_counter.v1
    - fathom.failure-intel.causal_finding.v1
    - fathom.reference-data.taxonomy.v1          # pending OQ-5
  # MUST equal src/fathom_maintenance/events/catalog.py. tools/check_event_catalog.py

autoscaling:
  mode: hpa
  minReplicas: 2
  maxReplicas: 6
  targetRequestsPerSecond: 50

sync:
  outboxRelay: { enabled: true }           # ALWAYS. Not disableable [C21]
  edgeCoordinator: { enabled: false }      # the ONE legitimately inert component
  divergenceBudgets:
    maintenance_action_record: { maxDisconnection: 90d }

networkPolicy:
  enabled: true                            # NEVER false
  ingress:
    fromServices: [gateway]
    fromNamespaces: []
    allowPrometheusScrape: true
  egress:
    toOwnDatabase: true
    toEventBus: true
    toServices: [auth, audit, reference-data, gateway]   # `gateway` carries the reservation
                                                         # command to Supply. See the note below
    toNamespaces: []
    allowDNS: true
```

> **`supply` is deliberately absent from `egress.toServices`, and the reservation call routes through `gateway`. [OQ-6 CLOSED — the through-gateway exception.]**
>
> [09 §4.4.2](09-monorepo-and-conventions.md) forbids the direct path: "sub-application → sub-application | **NO** | 03 principle 2. This is the whole point of the policy." §4.5's reservation is nevertheless a Scheduling → Supply HTTP call, explicitly sanctioned by [03 principle 3](../architecture/03-integration-contracts.md) ("A producer that needs a specific action taken elsewhere **issues a command against that sub-application's API** and accepts the response"). Rev 1 recorded this as an open conflict with three candidate resolutions and took (a) as an interim position.
>
> **That interim position is now the documented pattern, and rev 1's own preference was right.** [09 §4.4.2](09-monorepo-and-conventions.md) records: *"The through-gateway exception is now a pattern, not three coincidences. Domino scoring writes, tool-server proxying, and PMA evidence materialisation each independently arrived at the same shape: an asynchronous, non-compute-path transfer routed through the gateway rather than a direct sub-application edge, specifically to avoid a point-to-point rule that would need repeating for every future instance of the same need. A fourth sub-application requiring an equivalent transfer should default to this pattern rather than re-deriving it, and cite this paragraph rather than opening a fourth ADR."*
>
> So: `egress.toServices: [auth, audit, reference-data, gateway]`, **no ADR**, and rev 1's alternatives (b) a point-to-point exception and (c) an asynchronous command topic are both dropped — (b) is the rule the pattern exists to avoid, and (c) would weaken R5's corroboration for no benefit.
>
> **One qualification, stated because the pattern's own wording invites it.** The pattern describes "asynchronous, non-compute-path" transfers, and the reservation is synchronous and is on the planning path. It is *not* on the **solve** path — §4.5 issues it strictly after the solve completes, and §4.6 confirms "no synchronous Supply read occurs on the compute path in any of this" — so 03 principle 2's prohibition is satisfied. But a reviewer should know the fourth instance is not identical to the first three: it is a *command* with a response the caller blocks on, and it inherits `gateway`'s availability as a dependency of the reservation step. That is acceptable because the saga already treats an unreachable Supply as `RESERVATION_INDETERMINATE` and recovers through §4.5.5, so a gateway outage degrades to a state the protocol already handles rather than to a new one. Recorded in the README against [09 §4.4.2](09-monorepo-and-conventions.md) as a widening of the pattern's stated scope from "asynchronous" to "asynchronous or off-compute-path", for confirmation by the owner of document 09 (**[RECONCILE RC-6]**, §17).

### 12.2 Edge variant — `helm/values-edge.yaml`

```yaml
profile: edge                              # drives assert_edge_write_surface() at startup
edge:
  assetId: "<the SSN's asset_id>"
  producerNode: "edge:<asset_id>"          # stamped on every emitted envelope

replicaCount: 1                            # one hull, one instance
autoscaling: { mode: none }                # no HPA afloat

resources:
  requests: { cpu: 100m, memory: 256Mi }   # no solver
  limits:   { cpu: 500m, memory: 512Mi }

optimizer:
  enabled: false                           # the optimizer does not run afloat.
                                           # No reservations are ever issued from the edge

app:
  config:
    edgeWriteAllowlist:                    # asserted at startup; a pod-fail on addition
      - "POST /maintenance-action-records"
      - "POST /proposals"
      - "POST /work-orders"                # accepted as a QUEUED REQUEST only (202)
      - "POST /work-candidates"            # queued request only
    predictionCacheStalenessHorizonSeconds: 604800   # beyond this, shown as EXPIRED,
                                                     # not as a prediction [11 §7.3]
    jsnOriginatorAlpha: "F"                # identical to enterprise
    jsnBlockSize: 512                      # pre-issued lease; consumed, never issued

database:
  clusterName: fathom-maintenance-pg-edge  # single-instance CloudNativePG on the hull
  name: maintenance
  poolSize: 5
migrations: { enabled: true, backoffLimit: 0 }   # identical migration path. No edge-only schema

events:
  brokers: redpanda.fathom-edge.svc.cluster.local:9093
  consumerGroup: fathom-maintenance-edge-v1
  publishes:
    - fathom.maintenance.maintenance_action.v1     # EXACTLY ONE. Asserted in CI
  consumes:
    - fathom.pdm.prediction.v1                     # cache only, degraded presentation
    - fathom.registry.configuration_baseline.v1
    - fathom.telemetry.usage_counter.v1
    - fathom.reference-data.taxonomy.v1

sync:
  outboxRelay: { enabled: true }
  edgeCoordinator: { enabled: true }              # ACTIVE on this hull and its shore end
  divergenceBudgets:
    maintenance_action_record:
      maxDisconnection: 90d                       # > the 42-day scenario. Asserted in helm tests
      maxUnreconciledRecords: null                # deliberately unbounded (§7.5)
      onBreach: EXPLICIT_READ_ONLY

networkPolicy:
  enabled: true
  ingress:
    fromServices: [gateway]                        # the hull's local gateway
  egress:
    toOwnDatabase: true
    toEventBus: true
    toServices: [auth, audit, reference-data, sync]  # `sync` carries the ship-to-shore drain
    toNamespaces: []
    allowDNS: true
```

Deployed via Argo CD under `deploy/argocd/`, `dev` auto-sync, staging and production manual. The edge Application targets the hull cluster and pins the **same digest** as enterprise.

---

## 13. Observability

Beyond [09 §5.6](09-monorepo-and-conventions.md)'s baseline, the following are required because they are the signals that would reveal the two failure modes this document is built around.

| Metric | Why it exists |
|---|---|
| `fathom_maintenance_reservation_saga_state{state}` (gauge) | A non-zero count in `RESERVATION_INDETERMINATE` or `RELEASE_PENDING` that does not drain is D6 in progress |
| `fathom_maintenance_reservation_orphan_suspected_total` | Incremented when the reaper finds a non-terminal intent older than `3 × reserve_timeout`. **Should be flat at zero**; a non-zero value is an alert, not a curiosity |
| `fathom_maintenance_reservation_calls_total{operation}` | Proves the no-loop property in production, not only in test |
| `fathom_staleness_refusals_total{reason}` | Required by [09 §8.3](09-monorepo-and-conventions.md); the five §4.1 reasons are distinguished |
| `fathom_maintenance_action_records_total{producer_node, capture_completeness}` | The label stream's actual volume, split by hull-versus-shore. A hull whose count is zero across a patrol is D8 recurring operationally |
| `fathom_maintenance_treatment_record_unknown_ratio` | The fraction of records with a **NULL** `triggering_driver` (§5.4.1). PdM's propensity model handles missingness; a *rising* ratio means capture linkage is degrading |
| `fathom_maintenance_deferrals_total{deferral_reason_class}` | Class mix. If `risk_disagreement` approaches 100%, someone has found it the path of least resistance and D34 has returned through the UI |
| `fathom_maintenance_jcn_deferred_total` | §6.4 block exhaustion |
| `fathom_sync_divergence_seconds{aggregate}` and `..._breached` | Library-provided ([11 §9.1](11-outbox-sync-library.md)); surfaced per aggregate |
| `fathom_maintenance_optimizer_solve_seconds`, `..._infeasible_total` | Solver health; an infeasible run must be explained, never retried silently |

Log `event` values are stable snake_case strings: `reservation_intent_minted`, `reservation_indeterminate`, `reservation_compensated`, `saga_reaped`, `staleness_refusal`, `action_record_captured`, `treatment_record_unknown`, `edge_write_rejected`, `jcn_assignment_deferred`, `merge_applied`, `replan_exhausted`.

---

## 14. Explicit DO-NOT list

Per [09 §1.3](09-monorepo-and-conventions.md)'s template. Every item is a specific, plausible implementation choice that would reintroduce a named finding. These are not style preferences; each one has a review finding or a cited contract behind it.

**The reservation protocol — D6**

1. **Do not loop per NIIN.** One `POST /reservation-sets` carrying every line, always. *(D6 verbatim: "reserves per-NIIN… 37 of 40 succeed, the 38th fails." §4.5.4 R4; lint-enforced.)*
2. **Do not send the reservation before committing the intent row.** *(§4.5.4 R1. A crash in that gap is the classic orphan.)*
3. **Do not treat `reservation_intent_id` as a release handle.** Supply releases by *its* `reservation_set_id` only. *(§4.5.4 R2; [26 §3.9](26-supply.md). This is rev 1's error — do not restore it.)*
4. **Do not defer persisting `reservation_set_id`.** It is committed in its own transaction the instant the `201` is read. *(§4.5.1; fault point F12.)*
5. **Do not set `fence: "none"` to make a rejected reservation succeed.** A fence rejection means the optimizer solved against a stock position that no longer exists, and the correct response is a replan with refreshed availability. *(§4.1.1. The single most tempting way to undo D6's fix after it is in place.)*
6. **Do not retry a fence rejection with the same `expected_stock_epoch`.** It will fail forever. *(§4.1.1, §4.6 rule 2.)*
7. **Do not treat a `201` as confirmation.** `RESERVED` requires the `201` **and** a corroborating `reservation_set.confirmed`. *(§4.5.4 R5.)*
8. **Do not publish `work_package.approved` from any state but `APPROVED`, reachable only from `RESERVED`.** *([03 §6](../architecture/03-integration-contracts.md): "published only after reservation confirmation" `[D6]`; §4.5.4 R7.)*
9. **Do not resurrect an expired reservation set.** Re-verifying every line is a new set by definition. *([26 §7.4](26-supply.md); §4.5.6.)*
10. **Do not introduce a distributed transaction, orchestrator, or distributed lock manager across the Supply boundary.** *([26 §3.12](26-supply.md): "any proposal to add one must first explain what property the TTL lease fails to provide.")*
11. **Do not do arithmetic on `supply_expires_at`.** Every timer reads `monotonic_deadline`. *(`[D29]`; §3.8, lint-enforced.)*
12. **Do not make `part_availability.changed` a replan trigger.** *(§4.6 rule 3 — this is D20's oscillation.)*
13. **Do not re-propose an unchanged failed NIIN line in the next generation.** *(§4.6 rule 2 — this is the non-convergence, and it is the natural implementation.)*

**Edge-authoritative recording — D8**

14. **Do not require a `WorkOrder` to record a `MaintenanceActionRecord`.** `work_order_id` is nullable by design and a null is a complete record. *(D8; §1.4, §3.4.1.)*
15. **Do not let the edge fabricate an authorization.** `POST /work-orders` afloat is a queued request; `PATCH` to `authorized` is `423`. *([03 §11](../architecture/03-integration-contracts.md); §3.3.)*
16. **Do not modify, reject, or reorder an edge record ashore.** Corrections are new rows with `supersedes_action_record_id`. *([11 §7.3](11-outbox-sync-library.md); §7.4 — the table is INSERT-only and the trigger enforces it.)*
17. **Do not auto-link an edge record to a shore work order by heuristic.** *(§3.4.1; [13 §15.2](13-synthetic-data-generator.md) generates exactly this conflict, and an auto-link is how that test passes for the wrong reason.)*
18. **Do not bind write authority to connectivity.** No `is_connected()` input to any merge decision. *([03 §11](../architecture/03-integration-contracts.md) on the DDS liveliness defect; §7.4.)*
19. **Do not bound the number of unreconciled action records.** `max_unreconciled_records` is deliberately `None`; refusing the 501st repair record is D8 as a quota. *(§7.5.)*
20. **Do not refuse a record because the JSN block is exhausted.** Accept with a null JCN. *(§6.4 — "D8 wearing a compliance badge.")*
21. **Do not let a telemetry divergence breach gate maintenance recording.** *([11 §9.1](11-outbox-sync-library.md) rule 3.)*
22. **Do not mark the edge drain `replay: true` or `X-Backfill`.** A six-week-old action is a first emission of a real fact and must fire its side effects. *([11 §9.3](11-outbox-sync-library.md); §7.2.)*
23. **Do not key deduplication on `jcn`.** `action_record_id` only — duplicate 2-Kilos with different JSNs are real input. *(§3, §5.7; [13 §9.10](13-synthetic-data-generator.md).)*

**The label stream and the treatment record — D1, D21, D34**

24. **Do not accept `triggering_driver`, `triggering_prediction_id`, or `policy_version` from a client.** Server-derived, `422` on input. *(§5.4 rule 0.)*
25. **Do not guess a candidate linkage.** Zero or ≥2 open candidates → NULL. **A fabricated link is worse than a missing one**, because missingness is modellable and fabrication is internally consistent and undetectable. *(§5.4; do not add a nearest-match heuristic.)*
26. **Do not emit `pms` or `unknown` as `triggering_driver` values.** The five values are PdM's; absence encodes unknown. *(§5.4.1.)*
27. **Do not collapse `opportunistic` and `opportunistic_pms`.** *([22 §4.2](22-pdm.md): "the most likely implementation error in this table.")*
28. **Do not put a non-treatment prediction id into `triggering_prediction_id`.** Use `prediction_in_evidence_id`. *(§5.4.2.)*
29. **Do not derive `maintenance_class` server-side, pre-select it in a UI, or infer it from `action_taken_code`.** *(§5.2; [13 §9.10](13-synthetic-data-generator.md) calls its misclassification "the single most damaging label error.")*
30. **Do not default `deferral_reason_class`.** Either default is a silent, directional, unrecoverable bias. *(`[D34]`; §3.5.)*
31. **Do not let a non-`risk_disagreement` deferral carry a `disagreement` block.** *(§3.5 — this is D34 in one line of code.)*
32. **Do not reject realistic deckplate input.** The eight corruptions are accepted and flagged, never refused; a rejecting capture API stops the recording. *(§5.7 — D8 by attrition.)*
33. **Do not parse the narrative to validate a coded field.** Untrusted free text, never an instruction. *([03 §9](../architecture/03-integration-contracts.md).)*
34. **Do not pre-filter the event stream to Status 2/3.** Capture all, expose the filter. *(§5.3 — `MAINT_EFFECT` is computed over all actions.)*
35. **Do not store a resolved failure mode.** Scheduling stores 3-M codes as filed; resolution is the consumer's at read time. *([12 §4](12-reference-data-taxonomy.md); §5.6 — a cached resolution turns a many-to-many mapping into a false one-to-one.)*
36. **Do not omit `findings.taxonomy_version`.** *([03 §14](../architecture/03-integration-contracts.md): "silently corrupt and undetectably so.")*
37. **Do not infer a missing parts record from an empty list.** `parts_record_absent` is explicit. *(§5.7; `MAINT_EFFECT` must report uncomputable, never zero.)*

**The optimizer and the conversion — D7, D19**

38. **Do not re-implement the decision-theoretic conversion.** Import `fathom_schemas.decision`. *(§4.2.1; [22 §7.1](22-pdm.md).)*
39. **Do not rank on anything but `expected_consequence`.** *([22 §7.5](22-pdm.md) rule 1: "A `FailurePrediction` reaching an optimizer objective function without passing through this conversion is the D7 defect.")*
40. **Do not treat a null `p_failure` as zero**, and do not catch `UncalibratedAndUnrated` and substitute a number. *([03 §7.1](../architecture/03-integration-contracts.md); §4.2.2 rule 1.)*
41. **Do not omit `operating_fraction`.** It overstates the horizon by ~50% in the optimizer's favour. *([22 §7.3](22-pdm.md); §4.2.1.)*
42. **Do not synthesize `timing_p10` where the basis is a class rate.** *(`[D19]`; [22 §7.3](22-pdm.md).)*
43. **Do not branch on `tier`.** *([03 §7.1](../architecture/03-integration-contracts.md); lint-enforced under `optimizer/`.)*
44. **Do not call PdM synchronously on the solve path.** *(03 principle 2; §4.2.1.)*
45. **Do not read the database during model construction.** The builder takes a materialized instance and holds no handle. *(§4.1 — a constructor-level guarantee, not a discipline.)*
46. **Do not degrade instead of refusing when a staleness bound is exceeded.** *([03 §5.2](../architecture/03-integration-contracts.md) names the optimizer specifically `[D6]`.)*
47. **Do not down-weight holdout items instead of excluding them at admission.** A ranking-stage branch leaks: the item has still been treated. *([13 §10.3](13-synthetic-data-generator.md); §4.3.)*
48. **Do not ship a candidate without a disposition.** Totality is asserted inside the persisting transaction. *(§4.4 — "most candidates carry a reason" is the failure.)*
49. **Do not run the solver multi-threaded.** CP-SAT is reproducible only single-threaded, and reproducibility is a DoD item. *(§4.3, §15.8.)*
50. **Do not merge candidates on `position_id`.** Merge is keyed on `installed_item_id`. *(`[C10, D9]`; §3.2.2 rule 1.)*
51. **Do not classify a merge product's driver as `pms` because a PMS task existed.** The driver is whichever changed the timing. *(§3.2.2 rule 4 — the intuitive alternative reintroduces D1 undetectably.)*
52. **Do not code a `casrep_risk.raised` candidate as `driver = casualty`.** It is a prediction. *(§3.2.1.)*
53. **Do not let the optimizer suppress a preventive task.** Changing an interval requires an `interval_change` proposal with `fleet_authority` and dual control. *([03 §7.2.1](../architecture/03-integration-contracts.md); §3.2.2 rule 7.)*
54. **Do not accept a proposer-declared `blast_radius`.** Derive it from what the payload mutates. *(`[D16]`; §3.9 — an MRC change is class-scoped even when raised from one hull's screen.)*

**General**

55. **Do not make an agent a direct topic consumer.** *(`[C19]`; §9.4.)*
56. **Do not make `plan` reserve anything.** A declared-`none` agent-eligible operation must not hold fleet stock. *(`[C1/D11]`; §9.2.)*
57. **Do not wildcard event subscriptions.** *(`[C38]`; §10.4.)*
58. **Do not use the partition key as the compaction key.** *(`[D5]`; §10.2 — compacting the label stream on `asset_id` deletes a hull's history via a broker setting.)*
59. **Do not build a divergent edge image.** One image, one chart, two values files. *(§12 — a divergent edge image is how the edge path stops being exercised, and that is how D8 happened.)*
60. **Do not cite "append-only" as a reason a spillage cannot be remediated.** *(`[D15]`; §3.11.)*

---

## 15. Definition of Done

Each item is objectively verifiable. A sub-application is not done because its endpoints return `200`.

### 15.1 The reservation protocol — D6

1. `POST /reservation-sets` is called **at most once per attempt**, carrying every line, with `fence: "strict"` and an `expected_stock_epoch` on every line drawn from the run's `input_watermark`. Proven by call-count and body assertions in §11.3 invariants 3 and 9, and by `fathom_maintenance_reservation_calls_total` in production.
2. The fourteen saga states of §4.5.3 exist as a persisted enum with an explicit transition table, and `RESERVATION_INDETERMINATE` and `AWAITING_TTL_EXPIRY` are both reachable and both drain.
3. `test_no_orphaned_reservations_under_partial_failure` passes across all fifteen fault points × two hidden outcomes, plus the Hypothesis variant.
4. **No `work_package.approved` appears in the event tap without an earlier matching `reservation_set.confirmed`** — asserted as an ordering predicate, not a state check.
5. The R3 partial unique index exists in `pg_indexes`, and the R4 no-loop lint rule is in CI.
6. The reaper converges every saga unaided with no client retry (§11.3 invariant 8), and `fathom_maintenance_reservation_orphan_suspected_total` is flat at zero across a full demonstration run.
7. Orphan lifetime is bounded in the unrecoverable case: F13 terminates on TTL expiry with zero held reservations and zero operator action.
8. `extend` is exercised, its `extend_count ≤ 8` cap is observed, and a capped package notifies the planner *before* expiring.

### 15.2 Edge-authoritative recording — D8

9. A network-partitioned edge instance accepts `POST /maintenance-action-records` with `work_order_id = null` and **all four Tier A fields** — determination, findings coding, failure timing, treatment record — with no shore round trip.
10. The same instance returns `202` for `POST /work-orders` and `423` for `PATCH … authorized`. No authorization is ever minted afloat.
11. `assert_edge_write_surface()` fails the pod when a state-changing route is added without an allowlist change.
12. `test_edge_recording_six_week_disconnect` passes all fourteen assertions against the [13 §15](13-synthetic-data-generator.md) golden file, unregenerated.
13. `maintenance_action_record` is INSERT-only in the deployed schema: `UPDATE`/`DELETE` revoked from the application role **and** a trigger that raises. Verified against the live database, not the migration source.
14. The divergence budget (90 d) exceeds the scenario (42 d), asserted in `helm unittest`.
15. On reconnect, an edge record and a concurrently-authorized shore work order for the same equipment both persist, neither overwritten, with no inferred link.
16. `fathom_maintenance_action_records_total{producer_node}` shows a non-zero `edge:<asset_id>` count for the patrol.

### 15.3 The label stream

17. All four [06 §9.2](../architecture/06-demo-decisions-and-assumptions.md) Tier A fields are non-null on every record where they are derivable, and `capture_completeness` is set on every record.
18. `triggering_driver` is one of PdM's five values or absent; `pms` and `unknown` never appear on the wire; PdM's consumer-driven conformance test passes.
19. `opportunistic` and `opportunistic_pms` are both emitted by the demonstration corpus and are never collapsed.
20. Zero policy-frozen items carry `triggering_driver ∈ {prediction, opportunistic}` or a non-null `triggering_prediction_id` — gate G-7, asserted on Scheduling's own emissions.
21. `test_findings_capture_under_label_corruption` passes: all eight corruptions accepted, each represented or flagged per §5.7, and the wrong-findings-code case produces **no** warning.
22. `failure_indicator` is derived and carries `failure_indicator_rule_version`; no client can set it.
23. `findings.taxonomy_version` is non-null on 100% of records.
24. `fathom_maintenance_treatment_record_unknown_ratio` is reported, and its trend is reviewed rather than merely emitted.

### 15.4 Deferrals — D34

25. `deferral_reason_class` is `NOT NULL` with no database default and no API default; unset is `422`.
26. A `disagreement` block on a `capacity`, `tempo`, or `parts_unavailable` deferral is `422`, and the test asserts **both** directions.
27. `deferral.recorded` publishes all four classes; Scheduling filters none.
28. `fathom_maintenance_deferrals_total{deferral_reason_class}` shows a plausible mix — a `risk_disagreement` share approaching 100% is treated as a defect, not as a finding about the models.

### 15.5 The optimizer

29. `optimizer/consequence.py` contains **no** conversion arithmetic; `test_conversion_is_not_reimplemented` passes.
30. Every `CandidateDisposition` carries `conversion_version` and `inputs_digest`, and `count(dispositions) == count(candidates_in_scope)` for every run.
31. Every excluded candidate carries a `binding_constraint` from the CP-SAT core and a counterfactual.
32. All five staleness refusals return distinct problem types and increment their labelled counter.
33. `GET /work-packages/{id}/explanation` meets `p95 < 4 s` at [06 §7](../architecture/06-demo-decisions-and-assumptions.md) scale.
34. Every operator-visible ranking renders `weights_are_illustrative` and the risk posture.
35. `test_convergence_is_monotone` passes; `REPLAN_EXHAUSTED` is reachable and fully explained.

### 15.6 Navy fidelity

36. Every JCN is exactly 13 characters, `UIC(5) + WorkCenter(4, left-justified space-padded) + JSN(4)`, with the FATHOM originator alpha in JSN position 1, matching the generator's corpus.
37. A JSN block exhausted afloat yields an accepted record with `jcn = null`, assigned ashore in `monotonic_seq` order.
38. `status_code` is captured on every record and exposed as a filter, not applied as one.
39. `action_started_at`, `action_completed_at`, and the `failure_detected_at` interval are all present, making MDT and Ao computable by their consumers; `parts_consumed[].requisition_doc_no` supports the awaiting-parts decomposition.
40. The EIC is matched by prefix, never by equality, and is never a join key.

### 15.7 Events, API, and deployment

41. `tools/check_event_catalog.py` exits 0: `catalog.py` ≡ `values.yaml` ≡ [03 §6](../architecture/03-integration-contracts.md), in both profiles.
42. Every envelope carries the full `clock` block and a correct `producer_node`; the edge `PUBLISHES` set is exactly one topic, asserted in CI.
43. `changed_since` exists for every aggregate a declared consumer projects `[D5]`.
44. `x-agent-eligible` appears only on `x-side-effects: none` or `proposal-only` operations; no agent can reach `/work-packages`, `/reserve`, `/approve`, or the capture endpoint.
45. Fault injection shows **no state change without its event** for every state-changing operation.
46. The rendered NetworkPolicy's egress peer set equals `values.networkPolicy.egress` exactly, `gateway` included and `supply` excluded.
47. The same image digest runs at enterprise and edge.

### 15.8 Reproducibility and provenance

48. Same `input_watermark` + seed + solver version + `conversion_version` → **byte-identical** solution and dispositions. `num_search_workers = 1` in the deployed chart.
49. Every `optimizer_run` persists its watermark, including `stock_epoch`, and no historical run is recomputed when `conversion_version` changes.
50. Every placeholder in this document is labelled illustrative wherever an operator sees its output, and the §16 list is current.

---

## 16. Reconciliation, placeholders, and open questions

### 16.1 Reconciliation items — status

Rev 1 raised RC-1 through RC-3 against siblings authored in parallel. All three are closed; two new ones and one carried item remain.

| Item | Counterparty | Status |
|---|---|---|
| **RC-1** — ownership of the decision-theoretic conversion | [22 §7](22-pdm.md) | **CLOSED.** PdM owns it; ships as `fathom_schemas.decision`. Scheduling's local implementation deleted, including rev 1's shrinkage term. §4.2.1, §4.2.4 |
| **RC-2** — `DELETE` by client intent key | [26 §3.9](26-supply.md) | **CLOSED AGAINST rev 1's assumption.** No `client_reference` field exists; release is by Supply's `reservation_set_id`. Recovery is by idempotent re-issue, the change feed, then TTL — no Supply change required. §3.8, §4.5.5 |
| **RC-3** — `policy_version` nullability on non-prediction drivers | [22 §2.3](22-pdm.md) | **CLOSED IN rev 1's FAVOUR.** PdM requires it as a stratification covariate. §5.4.4. The `triggering_driver` *vocabulary*, however, was wrong in rev 1 and is corrected in §5.4.1 |
| **RC-4** — `prediction_in_evidence_id` | [03 §6](../architecture/03-integration-contracts.md) | **OPEN.** Proposed catalog addition (§17). Interim: join through `triggering_candidate_id`. Never overload `triggering_prediction_id` |
| **RC-5** — `policy_version` namespace prefixes (`cgp:` / `ipv:`) | [22 §4.3](22-pdm.md) | **OPEN.** PdM strata must not pool the two namespaces by string equality (§5.4.4) |
| **RC-6** — through-gateway pattern scope | [09 §4.4.2](09-monorepo-and-conventions.md) | **OPEN, low risk.** The pattern says "asynchronous, non-compute-path"; Scheduling's reservation is synchronous and off the *solve* path. Position taken, confirmation requested (§12.1) |

### 16.2 Open questions

| # | Question | Interim position |
|---|---|---|
| **OQ-1** | No event announces an *occurred* casualty; the catalog has only predictive `casrep_risk.*` | `casualty` driver is API-originated only (§3.2.1). Raised for a catalog decision |
| **OQ-2** | No `work_package.retracted` event, so a consumer holding a `proposed` package never learns it was abandoned | Successor carries `supersedes_work_package_id`; consumers treat a superseded proposal as retracted. Weaker than an explicit event (§4.5.7) |
| **OQ-3** | `Idempotency-Key` retention for edge-reachable operations | Must exceed the 90-day divergence budget (§4.5.7). Set by document 11 |
| **OQ-4** | The production JSN originator alpha requires central TYCOM/NAVSEA assignment | `F`, reserved for demonstration, in the data card. One Helm value to change (§6.2) |
| **OQ-5** | Platform-service topics (Reference Data taxonomy) are absent from [03 §6](../architecture/03-integration-contracts.md)'s catalog, so the three taxonomy events cannot carry consumer-driven conformance tests | Consumed and handled; conformance deferred (§10.4). Logged as OD-7 by [12 §3.4](12-reference-data-taxonomy.md) |
| **OQ-6** | ~~Scheduling → Supply network path~~ | **CLOSED** by [09 §4.4.2](09-monorepo-and-conventions.md)'s through-gateway pattern (§12.1) |
| **OQ-13** | ~~`authority_class` vocabulary undefined~~ | **CLOSED** by [03 §7.2.1](../architecture/03-integration-contracts.md) (§3.9) |

### 16.3 Placeholders requiring SME validation

Every one of these runs, and every one is labelled illustrative wherever an operator sees its effect ([06 §3](../architecture/06-demo-decisions-and-assumptions.md) assumption A8).

| Placeholder | Value | Where |
|---|---|---|
| Consequence weights | 10.0 / 3.0 / 1.0 | §4.2.3 — A8 rates defensibility **LOW**; a Phase 3 workshop item |
| Risk posture by band | `AVERSE` / `NEUTRAL` / `NEUTRAL` | §4.2.3; [22 §7.4](22-pdm.md) P-17 — a program decision, not an analytic one |
| Staleness bounds | nine values, 900–604800 s | §4.1 |
| Objective weights `λ_cost`, `λ_capacity`, `λ_churn` | — | §4.3 |
| The whole constraint model and solver choice | CP-SAT, C1–C7 | §4.3 — [04 §6](../architecture/04-subapplication-architectures.md) leaves formulation to Phase 3 |
| `timing_tolerance_days` | 14 | §3.2.2 |
| `interval_change` bounded delta | ±25% | §3.9 |
| `max_replan_generations`, min replan interval | 3, 15 min | §4.6 |
| `reservationTtlSeconds`, `extendLeadSeconds`, `maxReserveAttempts` | 48 h, 1 h, 3 | §12.1 |
| JSN block size | 512 | §6.3 |

**Fleet-scale solving is answered "not attempted," not "solved."** At [06 §7](../architecture/06-demo-decisions-and-assumptions.md)'s scale (12 assets, ~8,400 items, 6 availabilities) the single-threaded deterministic solve is comfortable. Production (~300 hulls) requires decomposition per availability and is explicitly out of scope for this build (§4.3).

---

## 17. Corrections required to upstream documents

Raised here rather than fixed silently, per the Precedence row.

| Document | Correction | Why |
|---|---|---|
| [04 §6](../architecture/04-subapplication-architectures.md) | **Remove the `MaintenanceAction` aggregate.** Document 04 lists both `MaintenanceAction` ("executed work: findings, parts consumed, and the corrective-versus-preventive determination") *inside the work-order aggregate* and `MaintenanceActionRecord`. There is exactly one aggregate and it is `MaintenanceActionRecord` | `MaintenanceAction` in the work-order aggregate **is** the defect D8 describes — "it lives in the work-order aggregate, which the edge may not commit." Building both would rebuild the defect beside its own fix (§1.4) |
| [04 §6](../architecture/04-subapplication-architectures.md) | **Correct the deferral-feedback statement.** Rev 1 of 04 §6 says a deferral with accepted risk "is a human judgment that the prediction overstated urgency, and it is informative to… calibration monitoring" | D34 corrects this: only `risk_disagreement` is prediction-quality evidence. Document 03 §6 already implements the correction via `deferral_reason_class`; document 04's prose still asserts the uncorrected version (§8) |
| [03 §6](../architecture/03-integration-contracts.md) | **Add `prediction_in_evidence_id`** to `maintenance_action.recorded`'s payload | Warning lead-time coverage is [06 §2](../architecture/06-demo-decisions-and-assumptions.md)'s primary effectiveness metric and is measured over corrective actions preceded by a raised flag. Without a field for a *non-treatment* prediction, the only ways to record it are to overload `triggering_prediction_id` (which corrupts PdM's censoring classification, §5.4.2) or to lose it. **RC-4** |
| [03 §6](../architecture/03-integration-contracts.md) | **Enumerate `triggering_driver`'s five values normatively** | The field is named but never enumerated. Its vocabulary currently exists only in [22 §2.3](22-pdm.md) and [13 §8.4](13-synthetic-data-generator.md). Rev 1 of *this* document independently invented a sixth value and mis-spelled a seventh — evidence that the omission is load-bearing, not cosmetic (§5.4.1) |
| [03 §6](../architecture/03-integration-contracts.md) | **Add a `work_package.retracted` event**, or state that supersession is the retraction mechanism | **OQ-2**: `supply` and `fleet-status` act on `work_package.proposed` and have no way to learn it was abandoned if they never receive the successor (§4.5.7) |
| [03 §6](../architecture/03-integration-contracts.md) | **Add a producer for an *occurred* casualty**, or record that none exists by design | **OQ-1**: the catalog has only predictive `casrep_risk.*`, so no sub-application can subscribe to a casualty (§3.2.1) |
| [09 §4.4.2](09-monorepo-and-conventions.md) | **Widen the through-gateway pattern's stated scope** from "asynchronous, non-compute-path" to "asynchronous, or synchronous but off the compute path" | Scheduling's reservation command is the fourth instance and is synchronous. It satisfies 03 principle 2 (nothing synchronous on the *solve* path) but not the pattern's literal wording. **RC-6** (§12.1) |
| [22 §4.3](22-pdm.md) | **Confirm the `policy_version` namespace prefixes** `cgp:` / `ipv:` | Two distinct policy namespaces reach PdM in one column; stratifying on raw string equality would pool them. **RC-5** (§5.4.4) |
| [26 §3.3](26-supply.md) | *No change requested.* | Recorded deliberately: rev 1 asked Supply for release-by-client-key and called it "a hard requirement." It is not required — §4.5.5's three mechanisms close the gap with no Supply change. The request is withdrawn |

---

## 18. Quick reference for an implementing agent

**If you read nothing else.**

1. **Two aggregates, not one.** `MaintenanceActionRecord` (what was done — edge-authoritative, INSERT-only, client-minted id, `work_order_id` nullable) and `WorkOrder` (what was authorized — server-authoritative). Joined by a nullable FK. Never re-couple them. *(§1.4)*
2. **The reservation is a lease, not a transaction.** Commit the intent row → `POST /reservation-sets` (one call, all lines, `fence: "strict"`, `expected_stock_epoch` from the watermark) → **persist Supply's `reservation_set_id` immediately** → wait for `reservation_set.confirmed` → planner approves → *then* publish `work_package.approved`. Compensate by `DELETE` on Supply's id; if you never learned it, re-issue with the same `Idempotency-Key` to learn it; if Supply is gone, the TTL expires the hold. *(§4.5)*
3. **You do not implement the risk conversion.** Import `fathom_schemas.decision.expected_consequence` and supply `consequence`, `operating_fraction`, and `risk_posture`. Rank on `expected_consequence` and nothing else. *(§4.2)*
4. **Three fields decide whether PdM's statistics are valid**, and you are their only author: `triggering_driver` (five values, absence means unknown), `triggering_prediction_id` (non-null only for `prediction` and `opportunistic`), `policy_version` (non-null for PMS drivers too, namespaced). **Never guess a linkage.** *(§5.4)*
5. **Accept bad data; record the doubt.** Wrong codes, wrong items, duplicates, missing parts records, misclassifications — all `201`, all flagged. A capture API that rejects deckplate reality stops the label stream, which is D8 by attrition. *(§5.7)*
6. **`deferral_reason_class` is required with no default**, and only `risk_disagreement` is evidence about a prediction. *(§3.5, §8)*
7. **The edge writes exactly one aggregate.** Everything else is a read-through cache or a queued request, and the startup assertion fails the pod if that changes. *(§7.1)*
8. **When in doubt about a contract surface, document 03 wins; about layout and conventions, document 09; about Supply's API, document 26's committed OpenAPI — not the examples in this document.**

**The two tests that matter most:** `test_no_orphaned_reservations_under_partial_failure` (§11.3) and `test_edge_recording_six_week_disconnect` (§11.4). If either is skipped, xfailed, or has its golden file regenerated, the finding it discharges is back.
