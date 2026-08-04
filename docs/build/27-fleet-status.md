# Build Framework 27 — Fleet Status & Readiness

| | |
|---|---|
| **Status** | Build framework, rev 1. Prescriptive — an implementer follows it rather than interpreting it |
| **Slug** | `fleet-status` (document 03 §3.1) |
| **Purpose** | Build specification for the sub-application that composes the fleet-wide advisory readiness picture: readiness rollups from installed item to fleet, predicted casualty risk with hysteresis, and the explanation graph behind every displayed figure |
| **Resolves** | **C35** (Fleet Status disclaims owning any source fact while owning `RiskFlag`) and **C37** (consumed-event list was prose, not event names) from [05](../architecture/05-architecture-review-findings.md); implements the **D13** aggregation policy settled in [06 §5](../architecture/06-demo-decisions-and-assumptions.md); consumes the corrected **p_failure**-nullable contract and so closes **OQ-10** of [10](10-shared-packages.md) in the consuming direction |
| **Primary technical source** | [04 §5](../architecture/04-subapplication-architectures.md) in full. Every ownership, aggregate, and key-decision statement in this document is transcribed from it |
| **Binding contracts** | [03](../architecture/03-integration-contracts.md) §3.3, §4, §4.1, §5.1–§5.5, §6, §7.1, §7.3, §12, §15 · [04](../architecture/04-subapplication-architectures.md) §5, §12 · [05](../architecture/05-architecture-review-findings.md) D13, C35, C37 · [06](../architecture/06-demo-decisions-and-assumptions.md) §2, §3, §5, §7 |
| **Conventions** | Repository layout, service scaffold, layering, REST mechanisms, migrations, CI, container and chart conventions, and the shared Definition of Done are in [09 — Monorepo and Conventions](09-monorepo-and-conventions.md). Canonical types are in [10 — Shared Packages](10-shared-packages.md). Outbox, inbox, and relay are in [11 — Outbox / Sync Library](11-outbox-sync-library.md). This document adds Fleet-Status-specific requirements only and restates none of them |
| **Classification** | Internal. The service operates at a single level, U, for the synthetic demonstration ([03 §12](../architecture/03-integration-contracts.md), [06 §5](../architecture/06-demo-decisions-and-assumptions.md)). **The aggregation policy of §3 is nonetheless implemented and tested in full**, because it constrains the scoring formula and cannot be retrofitted |

---

## 0. How to read this document

Three markers are used, following [09 §1.3](09-monorepo-and-conventions.md), and they are load-bearing:

- **[03 §n]**, **[04 §n]**, **[06 §n]** — the decision is dictated by an architecture document. Not negotiable at implementation time.
- **[ESTABLISHED HERE]** — the architecture documents do not specify this. This document makes the call so that the implementation does not make it silently. The reasoning is stated. Numeric values so marked are **tunable placeholders**, and every one of them lives in a single constants module with its citation, per [10 §4.6](10-shared-packages.md)'s "do not invent" rule.
- **[OPEN]** — genuinely undecided, listed in §14, and blocking or near-blocking. Do not resolve one of these locally inside this service.

Two invariants govern every table in this document, and they are stated here because they are the reason the document exists:

> **I1 — Nothing this service publishes is an observed fact.** Every figure is derived, every derived figure decomposes to a source record held by another sub-application, and the decomposition is a primary output rather than a diagnostic feature `[04 §5]`.
>
> **I2 — Aggregation is a classification event.** *"A rollup whose value moves when a compartmented item degrades discloses that item's existence"* `[03 §7.3, D13]`. This is a property of the **formula**, not of the presentation layer, and §3 discharges it in the formula.

---

## 1. Purpose and scope

### 1.1 Ownership boundary, and the C35 correction verified

Transcribed from [04 §5](../architecture/04-subapplication-architectures.md):

> **Owns:** readiness scoring methodology, rollup computation, risk thresholds and hysteresis, the fleet read model, and the explanation graph behind every displayed figure.
>
> **Does not own:** any *observed* fact. This sub-application is derived-data only. **It is authoritative for its own methodology and for the `RiskFlag` assertions that methodology produces, and for nothing else.**

**C35 is verified as corrected.** Finding C35 recorded that *"Fleet Status disclaims owning any source fact while owning and publishing risk flags."* [04 §5](../architecture/04-subapplication-architectures.md) now carries the corrected wording quoted above, which resolves the contradiction by distinguishing two kinds of ownership: no ownership of **observed** facts, full ownership of a **derived assertion** and of the methodology that produces it. [05 §3.2](../architecture/05-architecture-review-findings.md) still states C35 in its original terms; that is the finding register retaining the historical statement of the defect, not an outstanding defect. The implementation consequence is concrete and is enforced in §13:

| Claim | Permitted? | Why |
|---|---|---|
| "Fleet Status owns no data" | **No** | It owns `RiskFlag`, `ReadinessAssessment`, `DegradationContributor`, and `MethodologyVersion` as derived assertions, with an audit trail and an accountable methodology version. Saying otherwise is C35 reintroduced |
| "Fleet Status owns no *observed* fact" | Yes | Every input arrives by event from its owning producer. No sensor reading, maintenance record, configuration item, or prediction originates here |
| "A `RiskFlag` is a fact about the equipment" | **No** | It is an assertion by a named, versioned methodology about the equipment. The distinction is what makes the flag falsifiable and the methodology reviewable |

### 1.2 In scope

1. `ReadinessAssessment`, `RiskFlag`, `DegradationContributor` (§2), and the two supporting aggregates this document adds: `RiskFlagTransition` and `MethodologyVersion`.
2. The **exclusion-stable rollup formula** and the three-view aggregation policy of [06 §5](../architecture/06-demo-decisions-and-assumptions.md) (§3). This is the load-bearing section.
3. Derivation of a contributor's degradation from each input kind, including the **null `p_failure`** case (§4).
4. The **explanation graph**: structure, persistence, evidence references, `inherited_from[]` walkability, and the traversal (§5).
5. Risk-flag state machine, thresholds, and hysteresis (§6).
6. Warning lead-time coverage: an explicit ownership determination and the computation (§7).
7. Advisory-not-authoritative labelling at the API level (§8).
8. All 21 consumed events, all 3 published events, and the CQRS projector as an event-to-read-model mapping (§9).
9. API surface (§10), boundary and deployment deltas (§11), testing (§12).

### 1.3 Out of scope

| Out of scope | Owner |
|---|---|
| Any observed fact — telemetry, configuration, maintenance history, predictions, supply position | The producing sub-application, per [03 §6](../architecture/03-integration-contracts.md) |
| The UI. This document specifies the **API-level** advisory contract a UI must surface (§8), not the UI | `apps/web` |
| Notification routing, escalation, and acknowledgement | `notification` `[04 §11]`; and it is a Phase 3 question in [04 §5](../architecture/04-subapplication-architectures.md) |
| The **definition** of the warning-lead-time-coverage metric and its authoritative computation | Determined in §7 to belong to the cross-cutting effectiveness-analytics path, not here |
| Model quality, calibration, tier assignment | `pdm` `[04 §4]` |
| Any writeback to a source system, any work-order creation, any requisition | `maintenance`, `supply` |
| Deployment, container, chart, and CI mechanics | [09 §4.3, §4.4, §6](09-monorepo-and-conventions.md); §11 lists only the deltas |

### 1.4 Why this service is designed last, and why one decision could not wait

[04 §12](../architecture/04-subapplication-architectures.md) places Fleet Status **8 of 9** in the Phase 3 sequence: *"Derived-data only. Best designed once its sources are settled."* That is correct for every part of this design except one. [06 §5](../architecture/06-demo-decisions-and-assumptions.md) states that the aggregation policy is settled **now**, ahead of this document, *"because it constrains the readiness scoring methodology and cannot be retrofitted"*, and [05 §4.4](../architecture/05-architecture-review-findings.md) repeats it: *"The aggregation-channel policy should be decided now regardless, because it constrains the readiness scoring methodology."*

So the ordering of this document is: the formula first (§3), because the formula is the accreditation artifact; everything else after.

### 1.5 The one constraint an engineer would not think to check for

Readiness scoring looks like a weighting problem. It is a weighting problem **subject to an information-flow constraint**, and the constraint is not discoverable from the readiness requirement itself. Stated plainly:

> A readiness score is a channel. If the number moves when a compartmented contributor degrades, an uncleared viewer learns that a compartmented contributor exists and is degrading — from nothing but a number moving. If the number's *scale* depends on the compartmented set, the viewer learns its magnitude even when nothing moves. Both are disclosures, and neither is fixed by redaction, filtering, or access control on the explanation graph, because the leak is in the arithmetic.

This is finding **D13**, and its Fleet Status consequence is the **exclusion-stability** requirement of [06 §5](../architecture/06-demo-decisions-and-assumptions.md) rule 4: *"the same formula must produce a coherent score over a subset of contributors. This rules out several otherwise attractive formulations."* §3.6 enumerates which ones.

---

## 2. Data model

### 2.1 Invariants

Every table in this section obeys these, and the tests in §12 assert them:

- **V1 — No source-of-truth data.** PostgreSQL, one logical database `[03 §15 obligation 13]`, holding a read model and derived assertions only. Fully rebuildable `[04 §5]`.
- **V2 — Rebuild is from `changed_since` reads, never from the event bus** `[03 §5.1, D5]`.
- **V3 — Contributor weights are contributor-local.** A weight is a function of the contributor alone. No weight may be defined by reference to the contributor set it appears in. §3.6 explains why this is a security property and not a modelling preference.
- **V4 — Scores are derived, contributors are stored.** No per-clearance score is persisted. A view is computed from the stored contributor rows at read time. This is what makes the exclusion-stability test in §12.1 a test over one dataset rather than a comparison of two pipelines.
- **V5 — Assessments cite an immutable methodology version and are never recomputed under a later one.** Recomputing history under a new methodology silently rewrites the warning-lead-time record of §7.
- **V6 — Absence is never zero.** Neither an excluded contributor (§3) nor an uncalibrated one (§4) nor an unassessed one contributes 0. Absence is declared, counted, and typed.

### 2.2 `ReadinessAssessment`

Scoped per [04 §5](../architecture/04-subapplication-architectures.md): *"Scoped to an asset, system, or fleet grouping, with score components and effective time."* Score **components**, not a scalar — decomposability is the key decision, so the aggregate carries the decomposition, not a summary of it.

```
readiness_assessment
  assessment_id                 uuid pk
  scope                         enum: asset | system | fleet | tycom   -- [AMENDMENT — closes OD-2]
  subject_asset_id              uuid null
  subject_system_id             uuid null
  subject_tycom_id              text null      -- 10-shared-packages.md §4.5's EventScope.TYCOM / tycom_id,
                                                 -- added specifically for this row. [AMENDMENT] Previously
                                                 -- `fleet_grouping`/`subject_grouping_id`, a scope this
                                                 -- document invented because 03 §5.4's vocabulary had no
                                                 -- middle echelon — 10 §4.5 added TYCOM in response, and
                                                 -- this document never adopted it, leaving two competing,
                                                 -- mutually unaware conventions live at once
  methodology_version           text not null  -- FK; immutable (V5)
  aggregation_exponent          numeric not null   -- p of §3.2, recorded per assessment
  contributor_set_revision      int not null   -- increments when the contributor SET changes,
                                               -- independently of any degradation change
  score_full                    numeric null   -- R(C): the union-of-all-contributors evaluation.
                                               -- NEVER served below the union label. Null when
                                               -- the contributor set is empty
  degradation_full              numeric null   -- D(C) = 1 - score_full/100, retained so parent
                                               -- rollups compose without recomputing children
  restricted_contributor_count  int not null default 0
  unassessed_contributor_count  int not null default 0
  contributor_count_full        int not null
  effective_at                  timestamptz not null   -- occurred_at semantics [03 §5.4]
  computed_at                   timestamptz not null   -- recorded_at semantics; NOT a freshness arbiter
  scoring_clock                 jsonb not null   -- monotonic_seq / hlc / sync_quality [03 §5.4]
  freshness                     enum: current | degraded | refused
  staleness_detail              jsonb not null   -- per-source read-model lag at computation time
  baseline_epoch_low_water      int not null     -- min epoch across contributing assets [03 §5.4]
  classification_label_full     jsonb not null   -- ClassificationLabel.union over ALL contributors
  delta_attribution             jsonb null       -- §3.11
  inputs_digest                 text not null    -- hash over contributor rows; rebuild determinism
  version                       int not null     -- ETag source [09 §5]
```

`score_full` is stored because the high-side view is a real view with real consumers, and because parent rollups compose from child degradations (§3.10). It is a **stored high-side value with a released-view discipline**, not a value that any handler may return without evaluating the requester's clearance. That discipline is enforced in the repository layer, not in the API layer: `repositories/readiness.py` exposes no method that returns `score_full`, only `evaluate_view(assessment_id, visibility_predicate)`.

### 2.3 `DegradationContributor`

[04 §5](../architecture/04-subapplication-architectures.md): *"A single traceable contribution to a readiness reduction."* This is the explanation-graph node. **Every score decomposes to these, exactly and exhaustively** (§5).

```
degradation_contributor
  contributor_id             uuid pk
  assessment_id              uuid fk -> readiness_assessment
  parent_contributor_id      uuid null   -- tree edge for system -> item nesting (§3.10)
  kind                       enum (§5.2): prediction | anomaly | health_indicator |
                             casualty_candidate | deferral | parts_shortfall |
                             requisition_delay | planned_mitigation | causal_finding |
                             redesign_signal | configuration_invalidation |
                             tier_transition | child_scope
  subject_installed_item_id  uuid null
  subject_system_id          uuid null
  subject_niin               text null
  weight                     numeric not null check (weight > 0)  -- INTRINSIC (V3)
  weight_basis               enum: criticality_tier | mission_criticality |
                             composite_criticality | grouping_weight
  weight_basis_ref           text not null      -- e.g. pdm criticality assessment ref
  weight_revision_reason     enum null: initial | tier_reassignment |
                             mission_criticality_change | methodology_change
  degradation                numeric null check (degradation between 0 and 1)
                             -- NULL ONLY where basis = unassessed. Never 0 as a stand-in (V6)
  basis                      enum: calibrated_item | population_hazard | observed_indicator |
                             observed_anomaly | accepted_risk | supply_constrained |
                             adjudicated_finding | child_rollup | unassessed
  uncalibrated               bool not null default false      -- §4
  reference_class            enum null: item | niin_fleet | equipment_family | class_estimate
  calibration_population     int null
  p_failure                  numeric null      -- carried through, nullable, verbatim [03 §7.1]
  population_hazard_rate     numeric null
  rul_p50_days               numeric null      -- null unless reference_class is item-conditional
  confidence                 numeric null      -- sharpness and fit only [03 §7.1]
  fallback_level             int null           -- 0..4, distinct from confidence [D7]
  sharpness                  numeric null
  horizon_days               int null
  render_hint                enum: point_estimate | population_band | observed | qualitative
  evidence_kind              enum: record | document_chunk | prediction | trace   [03 §7.2]
  evidence_ref               text not null      -- resolvable URI into the owning sub-application
  source_event_id            uuid not null      -- inbox idempotency key [03 §5.2]
  source_event_type          text not null
  source_producer            text not null
  source_producer_node       text not null      -- "enterprise" | "edge:<asset_id>"  [03 §5.4]
  source_monotonic_seq       bigint not null    -- THE ordering key; never source_time [03 §5.4]
  baseline_id                uuid null
  baseline_epoch             int null
  classification_label       jsonb not null     -- includes inherited_from[] [03 §7.3]
  stale                      bool not null default false
  observed_at                timestamptz not null
  created_at                 timestamptz not null
```

Three fields deserve emphasis:

- **`weight` is intrinsic and the check constraint is `> 0`, not `>= 0`.** A zero-weight contributor is a contributor that cannot appear in a decomposition, which is a contributor that cannot be explained. Transparency-only nodes (`model_binding.activated`, `asset.status_changed`) are **not** contributors; they are context rows in a separate table (§9.3).
- **`source_producer_node` is mandatory** because [03 §5.4](../architecture/03-integration-contracts.md) makes `(producer, producer_node, monotonic_seq)` the dedup and ordering key: *"a sub-application with an edge profile runs as two independent instances of the SAME slug, each minting its own monotonic_seq — without this field their sequences collide and the dedup key silently drops an event."* Fleet Status consumes from `telemetry`, `maintenance`, and `pdm`, all of which have or will have edge profiles. Projecting on `(producer, monotonic_seq)` alone would silently drop contributor rows and produce a readiness score that is wrong in the direction of optimism.
- **`degradation` is nullable only for `basis = unassessed`,** and a null there is not folded into the numerator. §4.4.

### 2.4 `RiskFlag`

[04 §5](../architecture/04-subapplication-architectures.md): *"A predicted casualty risk with severity, horizon, and evidence."* This is the one assertion Fleet Status owns outright (§1.1).

```
risk_flag
  flag_id                              uuid pk
  installed_item_id                    uuid not null
  asset_id                             uuid not null
  system_id                            uuid null
  state                                enum: candidate | raised | evidence_invalidated |
                                       mitigation_in_progress | clearing | cleared | suppressed
  severity                             enum (§6.2)
  predicted_casualty_category_candidate int null   -- 2..4; "candidate", never an assertion (§8)
  horizon_days                         int not null
  reference_class                      enum not null    -- thresholds are PER reference class (§6.2)
  uncalibrated                         bool not null
  driving_statistic                    numeric not null -- the contributor degradation d_i
  raise_threshold                      numeric not null -- recorded, not looked up, at transition
  clear_threshold                      numeric not null
  methodology_version                  text not null
  first_crossed_at                     timestamptz null -- when the raise threshold was first met
  first_crossed_monotonic              bigint null
  raised_at                            timestamptz null
  dwell_cycles_observed                int not null default 0
  dwell_monotonic_ms                   bigint not null default 0
  clear_first_met_at                   timestamptz null
  cleared_at                           timestamptz null
  clear_cause                          enum null: statistic_below_clear_threshold |
                                       item_left_baseline | methodology_suppression
  evidence_refs                        jsonb not null   -- non-empty
  classification_label                 jsonb not null
  version                              int not null
```

### 2.5 `RiskFlagTransition` — the append-only flag ledger

Added by this document `[ESTABLISHED HERE]`. It is required for three independent reasons, and each alone would justify it: hysteresis correctness is only auditable against a transition history; `casrep_risk.raised` / `casrep_risk.cleared` must be reconstructible for replay and for the outbox; and it is the **sole input Fleet Status contributes to warning lead-time coverage** (§7).

```
risk_flag_transition
  transition_id          uuid pk
  flag_id                uuid fk -> risk_flag
  from_state             enum null
  to_state               enum not null
  cause                  text not null
  driving_statistic      numeric not null
  raise_threshold        numeric not null
  clear_threshold        numeric not null
  methodology_version    text not null
  reference_class        enum not null
  uncalibrated           bool not null
  horizon_days           int not null
  scoring_run_id         uuid null        -- the pdm run that moved the statistic
  dwell_cycles_at        int not null
  dwell_monotonic_ms_at  bigint not null
  clock                  jsonb not null   -- monotonic_seq / hlc / sync_quality [03 §5.4]
  recorded_at            timestamptz not null   -- audit uses recorded_at [03 §5.4]
  published_event_id     uuid null
  classification_label   jsonb not null
```

**Append-only, no `UPDATE` grant, no `DELETE` grant on the table's role.** A migration that adds an updatable column to this table is a review failure.

### 2.6 `MethodologyVersion`

The methodology is the thing Fleet Status is authoritative for (§1.1). It is therefore an aggregate, not a config file.

```
methodology_version
  version                text pk           -- semver
  aggregation_exponent   numeric not null  -- p (§3.2)
  weight_function        jsonb not null    -- contributor-local weight derivation (V3)
  degradation_transforms jsonb not null    -- one per (kind, reference_class) pair (§4.2)
  thresholds             jsonb not null    -- §6.2, per reference class
  hysteresis             jsonb not null    -- band ratio, dwell cycles, dwell duration
  staleness_bounds       jsonb not null    -- §9.5
  effective_from         timestamptz not null
  approved_by            text not null
  approval_ref           text not null
  frozen                 bool not null default false   -- true once effective_from has passed
```

A frozen row is immutable. `GET /methodology/{version}` serves it, because an operator who cannot read the methodology cannot dispute the score, and a methodology that cannot be disputed will be dismissed `[04 §5]`.

### 2.7 Local read models

Built from events and rebuildable from `changed_since` reads (V2). None is a source of truth.

| Read model | Built from | Why Fleet Status needs it |
|---|---|---|
| `rm_asset` | `asset.registered`, `asset.status_changed` | Scope enumeration, OFRP phase, deployment state |
| `rm_configuration_tree` | `configuration.baseline_changed` + Registry `changed_since` | `system_id` → `asset_id` resolution. **This closes OQ-10's sibling, OQ-2** of [10 §11](10-shared-packages.md): `SystemRef` carries no `asset_id`, and *"Fleet Status scopes readiness to a system and needs the asset"*. The adopted reading — *"No parent fields added. Consumers resolve the chain through the Registry's `changed_since` reads"* — is implemented here and nowhere else |
| `rm_criticality` | `criticality_tier.assigned` | The **weight** source. Intrinsic per NIIN and equipment context (V3) |
| `rm_prediction` | `prediction.updated`, `prediction.invalidated` + PdM `changed_since` | Contributor derivation (§4). `prediction.updated` *"references the run artifact rather than inline result sets"* `[03 §6, D27]`, so the projector dereferences via PdM's API |
| `rm_supply` | `part_availability.changed`, `requisition.status_changed`, `allowance_shortfall.detected` | Shortfall and delay contributors |
| `rm_maintenance` | `work_candidate.created`, `work_order.opened`, `deferral.recorded`, `work_package.proposed`, `work_package.approved` | Deferral contributors and mitigation state |
| `rm_indicator` | `health_indicator.computed`, `anomaly.detected` | Observed-condition contributors |
| `rm_context` | `model_binding.activated`, `mission_review.completed`, `causal_finding.published`, `redesign_candidate.created`, `redesign_case.published` | Explanation-graph context and qualitative contributors |

---

## 3. The scoring methodology and the exclusion-stable rollup

### 3.1 The invariant, stated formally

Let a scope have contributor set $C$. Each contributor $i$ carries an **intrinsic** weight $w_i > 0$ (V3) and a degradation $d_i \in [0,1]$, where $0$ is full capability and $1$ is fully degraded. Let $V \subseteq C$ be the subset visible to a given requester under [03 §4](../architecture/03-integration-contracts.md)'s locally-enforced ABAC evaluation.

A rollup function $R$ is **exclusion-stable** if and only if all four hold:

| | Property | Statement |
|---|---|---|
| **ES-1** | **Closure and range invariance** | $R(V)$ is defined for every $V \subseteq C$ and takes values on the same fixed interval with the same interpretation for every $V$. The attainable range does not depend on $V$ |
| **ES-2** | **No residual-mass disclosure** | $R(V)$ is a function of $\{(w_i, d_i) : i \in V\}$ **only**. It may not depend on $\lvert C \rvert$, on $\sum_{i \in C} w_i$, or on any property of $C \setminus V$ |
| **ES-3** | **Movement invariance** | $\partial R(V) / \partial d_k = 0$ for every $k \notin V$. Adding, removing, or perturbing an invisible contributor cannot change $R(V)$ by any amount, including a rounding-level amount |
| **ES-4** | **Exact decomposability** | There exist attribution shares $s_i$ over $i \in V$ with $\sum_{i \in V} s_i = 1$ exactly, such that the total deduction $\bigl(R_{\max} - R(V)\bigr)$ apportions as $s_i \cdot \bigl(R_{\max} - R(V)\bigr)$. The explanation graph accounts for the displayed number with no residual `[04 §5]` |

ES-4 is [04 §5](../architecture/04-subapplication-architectures.md)'s decomposability requirement. ES-1 through ES-3 are [06 §5](../architecture/06-demo-decisions-and-assumptions.md)'s exclusion-stability requirement, made checkable. A formula satisfying ES-1..3 but not ES-4 is secure and useless; a formula satisfying ES-4 but not ES-1..3 is useful and leaks. Both are required simultaneously, which is what makes this narrower than it looks.

### 3.2 The formula: a weight-renormalized power mean

$$
D(V) \;=\; \left( \frac{\sum_{i \in V} w_i\, d_i^{\,p}}{\sum_{i \in V} w_i} \right)^{1/p}
\qquad\qquad
R(V) \;=\; 100 \,\bigl(1 - D(V)\bigr)
$$

with, per contributor $i \in V$, the attribution share

$$
s_i \;=\; \frac{w_i\, d_i^{\,p}}{\sum_{j \in V} w_j\, d_j^{\,p}}
$$

and the released contributor weight

$$
\tilde{w}_i \;=\; \frac{w_i}{\sum_{j \in V} w_j}
$$

**$p = 3$** `[ESTABLISHED HERE]`, tunable, stored per assessment in `aggregation_exponent` and per methodology version. $p$ is uniform across views and across levels of the rollup tree; a view-dependent $p$ would itself be a channel.

Why a power mean rather than the arithmetic mean it generalizes: at $p = 1$ this is a weighted average, and a weighted average of ~1,200 installed items dilutes one catastrophically degraded critical item into invisibility — an operationally worthless readiness score. At $p \to \infty$ it degenerates to $\max_i d_i$, which is exclusion-stable but violates ES-4, since one contributor takes the entire share and the rest are attributed zero, leaving an operator with no ranked action list. $p = 3$ is worst-case-leaning while keeping every contributor's share strictly positive and reportable. The exclusion-stability proof is identical for all $p \ge 1$, so the tuning knob is safe by construction: **$p$ can be re-tuned without re-accrediting the aggregation policy.** That is the practical payoff of separating ES-1..3 from the choice of $p$.

Verification against §3.1:

- **ES-1.** $D(V)$ is a power mean of values in $[0,1]$, hence in $[0,1]$; $R(V) \in [0,100]$ for every non-empty $V$, always. The attainable range is $[0,100]$ regardless of $V$.
- **ES-2.** The denominator is $\sum_{i \in V} w_i$ — the visible weight sum. Nothing about $C \setminus V$ appears anywhere in the expression. There is no residual mass to read off.
- **ES-3.** $d_k$ for $k \notin V$ appears in neither numerator nor denominator, so the partial derivative is identically zero. This is exact, not approximate: the low-side score is **bit-identical** before and after any change to an invisible contributor, which is what §12.1 asserts.
- **ES-4.** $D(V)^p = \sum_{i \in V} \tilde{w}_i d_i^{\,p}$ decomposes additively in the $p$-th power, and normalizing gives $\sum_{i \in V} s_i = 1$ exactly. The shares are reported directly and sum to the displayed deduction.

**Composition.** For a parent scope whose contributors are child scopes, set $d_{\text{child}} = D(V_{\text{child}})$ — which is already in $[0,1]$ by ES-1 — and apply the same formula with intrinsic parent weights. Exclusion-stability is therefore **closed under composition**: item → system → asset → fleet is stable at every level because each level's input is a value produced by a stable evaluation of the level below. This is the property that makes a fleet rollup safe, and it is the reason the formula is defined on degradation rather than on score.

### 3.3 Worked example

One asset, four contributors, $p = 3$. Contributor `c4` is compartmented and invisible to an uncleared viewer.

| | Contributor | $w_i$ | $d_i$ | `basis` |
|---|---|---|---|---|
| `c1` | Main reduction gear | 0.40 | 0.55 | `calibrated_item` (`p_failure` 0.62 @ 90 d, `reference_class` `item`) |
| `c2` | Fire pump 2 | 0.15 | 0.30 | `population_hazard` (**`p_failure` null**, $\lambda = 0.004/\text{d}$, $h = 90$ — §4) |
| `c3` | Chilled-water pump | 0.10 | 0.12 | `observed_indicator` |
| `c4` | *(compartmented)* | 0.35 | 0.80 | `calibrated_item`, `compartments: [X]` |

**High-side view, $V = C$.** $\sum w = 1.00$; $\sum w_i d_i^3 = 0.06655 + 0.00405 + 0.00017 + 0.17920 = 0.24997$; $D = 0.24997^{1/3} = 0.6300$; $R = \mathbf{37.0}$.
Shares: `c4` 71.7 %, `c1` 26.6 %, `c2` 1.6 %, `c3` 0.1 %. Deductions sum to 63.0.

**Default (low-side) view, $V = \{c_1, c_2, c_3\}$.** $\sum w = 0.65$; $\sum w_i d_i^3 = 0.07077$; $0.07077 / 0.65 = 0.10888$; $D = 0.10888^{1/3} = 0.4775$; $R = \mathbf{52.2}$.
Shares: `c1` 94.0 %, `c2` 5.7 %, `c3` 0.2 %. Deductions sum to 47.8 — exactly the displayed deduction. Released weights are $\tilde w = (0.615, 0.231, 0.154)$.

**Now degrade the invisible contributor:** `c4` goes $0.80 \to 0.95$. High-side $R$ falls $37.0 \to 28.2$. Low-side $R$ stays **52.2, to the last stored digit**. ES-3 holds. Nothing an uncleared viewer can observe moved.

### 3.4 Why a naive fixed-weight sum is not exclusion-stable

The obvious formulation. Weights are fixed fractions of the full contributor set, summing to 1 over $C$; the score is a simple deduction:

$$
R_{\text{naive}}(V) \;=\; 100\Bigl(1 - \sum_{i \in V} w_i d_i\Bigr), \qquad \sum_{i \in C} w_i = 1
$$

On the example: high side $\sum w_i d_i = 0.22 + 0.045 + 0.012 + 0.28 = 0.557$, so $R = 44.3$. Low side $= 0.277$, so $R = 72.3$. It satisfies ES-3 and ES-4. It fails **ES-1 and ES-2**, three separate ways, and each is a disclosure:

1. **The residual weight is published outright.** Decomposability (ES-4) requires the response to state each contributor's weight — an operator cannot audit a score whose weights are hidden, and the methodology is a published artifact (§2.6). The visible weights sum to 0.65. The complement, **0.35, is the compartmented set's share of the asset's total criticality** — a *magnitude*, which [06 §5](../architecture/06-demo-decisions-and-assumptions.md) rule 1 prohibits disclosing: *"a `restricted_contributors_present` boolean with a count — never a description, a system, or a magnitude."* One subtraction defeats the policy.
2. **The attainable floor discloses the same magnitude a second way.** If every visible contributor fails completely ($d_i = 1$ for all $i \in V$), $R_{\text{naive}}$ bottoms out at $100 \times 0.35 = 35$, not 0. The low-side score is confined to $[35, 100]$ and the high-side to $[0, 100]$. The floor is observable over time from a single badly degraded asset, and it is a direct readout of the compartmented weight mass. This is the ES-1 failure: the range depends on $V$.
3. **The two views are on different scales, so any cross-clearance comparison discloses a degradation value.** A cleared and an uncleared operator looking at the same asset see 44.3 and 72.3. The difference, 28.0, equals $100 \times w_{c4} \times d_{c4} = 100 \times 0.35 \times 0.80$ exactly. Given the weight (channel 1), the uncleared viewer recovers $d_{c4} = 0.80$ — the compartmented item's degradation, to full precision, from two numbers on two screens.

Renormalization defeats all three. Under §3.2 the low-side response publishes $\tilde w = (0.615, 0.231, 0.154)$, which sum to 1 by construction; there is no residual to subtract, no truncated floor, and the two views are not on a common scale that can be differenced to recover anything.

### 3.5 Why a naive average — computed once, published to everyone — is worse

The other obvious formulation, and the more common one in practice, because it looks like an efficiency: compute the score once over all contributors, publish that one number to every viewer, and merely filter the *explanation* by clearance.

$$
R_{\text{single}} \;=\; 100\Bigl(1 - \tfrac{1}{|C|}\textstyle\sum_{i \in C} d_i\Bigr) \quad\text{(or any aggregate over } C\text{), published to all}
$$

This fails **ES-3 and ES-4**, and it is the exact channel D13 describes:

- The published number is 44.3, and the visible contributors account for 27.7 points of deduction. A **28.0-point residual** is displayed but unexplained. ES-4 fails, so [04 §5](../architecture/04-subapplication-architectures.md)'s decomposability requirement fails too — *"A readiness figure that cannot be decomposed into contributing degradations... will be dismissed by operators — correctly."* Here it is worse than dismissible: the residual's **size** is the compartmented contribution.
- When `c4` degrades $0.80 \to 0.95$, the published number moves and **no visible contributor changed**. The uncleared viewer observes an unexplained movement, from which the existence of a hidden contributor follows immediately, and its trend follows from the sequence of movements. This is D13 verbatim: *"a readiness rollup that moves when a compartmented fitting degrades leaks its existence, and the explanation graph hands over the pointer."*
- No amount of access control on the explanation graph repairs it, because the leak is in the number. This is why [03 §7.3](../architecture/03-integration-contracts.md) says the aggregation policy *"constrains the readiness scoring methodology and is not a presentation concern."*

Note the ordering: the naive fixed-weight sum (§3.4) is a *static* leak of magnitude; the naive single computation is a *dynamic* leak of existence and trend. The renormalized power mean closes both.

### 3.6 Formulations ruled out, and the rule that rules them out

[06 §5](../architecture/06-demo-decisions-and-assumptions.md) says exclusion-stability *"rules out several otherwise attractive formulations."* Here they are, together with the single structural test that catches all of them: **if the weight or the transform of contributor $i$ is a function of any contributor other than $i$, the formula is not exclusion-stable.** That is invariant V3, and it is a security property, not a modelling preference.

| Formulation | Why it is attractive | Why it fails |
|---|---|---|
| Fixed weights as fractions of the full contributor set | Weights sum to 1; the score reads as "percent capability lost" | §3.4. Residual mass, truncated floor, differenceable views |
| Single computation, filtered presentation | One computation, one cache, one number; obviously consistent across viewers | §3.5. Unexplained residual and unexplained movement |
| Rank- or percentile-based weights ("this item is in the worst decile of the asset") | Naturally scale-free and robust to outliers | The rank of a visible item **changes when an invisible item is excluded**. ES-3 fails: perturbing $d_k$ for $k \notin V$ reorders the visible set and moves $R(V)$ |
| Softmax or any set-normalized attention over contributors | Smoothly emphasizes the worst without a hard max | The normalizer runs over the set. Removing a contributor rescales every remaining weight in a way that depends on the removed contributor's degradation. ES-2 and ES-3 both fail |
| Top-$k$ ("score the 5 worst contributors") | Matches how operators triage | Membership of the top-$k$ depends on invisible contributors. Excluding a compartmented item **promotes a visible item into the set**, changing $R(V)$. ES-3 fails, and the promotion is itself a signal |
| Count-based scoring ("$n$ of $m$ systems degraded") | Trivially explicable to a stakeholder | $m$ is $\lvert C \rvert$. ES-2 fails by inspection. Using $\lvert V \rvert$ instead is stable but discards weight entirely |
| Fleet-wide percentile normalization of an asset's score | Makes cross-hull comparison immediate | The reference distribution is built over the full fleet contributor population, which includes compartmented contributors on other hulls. ES-2 fails across scopes rather than within one, which is harder to see and no less real |
| $\max_i d_i$ (worst contributor) | Exclusion-stable, and operationally intuitive | ES-4 fails: one contributor takes the whole attribution, the rest are attributed 0, and the explanation graph cannot rank action. This is the $p \to \infty$ limit of §3.2, and the reason $p$ is finite |

### 3.7 The three views, and the rule that the low side never claims completeness

Implementing [06 §5](../architecture/06-demo-decisions-and-assumptions.md)'s aggregation policy exactly:

| View | $V$ | Who | Response |
|---|---|---|---|
| **Default** (rule 1: *exclusion*) | Contributors at or below the requester's clearance, caveats, and compartments, evaluated locally against ABAC attributes `[03 §4]` | Every requester, no parameter needed | Renormalized score per §3.2, renormalized weights, exact shares, **plus the disclosure block below** |
| **High-side** (rule 2) | $C$ — the union of all contributor labels | Only requesters cleared to `classification_label_full` | Same formula, $V = C$. Response labelled at the union; `restricted_contributors_present: false` |
| **Suppressed** (§3.9) | $V = \emptyset$ with $C \neq \emptyset$ | Any requester for whom nothing is visible | **No score.** `score: null`, `suppression_reason: "all_contributors_restricted"` |

Every readiness and explanation response, in **every** view, carries this block. It is a required, non-nullable member of the response body — never a metadata sidecar, never a header alone — implementing rule 3 (*"A low-side rollup never presents itself as complete. The boolean is displayed, not buried in metadata"*):

```json
"contributor_disclosure": {
  "restricted_contributors_present": true,
  "restricted_contributor_count": 1,
  "view": "default",
  "completeness": "partial",
  "statement": "This score is computed over the contributors visible at your access level. Contributors above that level are excluded from the computation and are not reflected in this figure."
}
```

**Why the renormalized formula still needs this boolean — the point that is easy to miss.** §3.2 is *too* coherent. It produces a well-formed score on $[0, 100]$, with weights summing to 1 and shares summing to the deduction exactly. A low-side viewer inspecting it finds nothing wrong, no residual, and no missing mass. It looks **complete**. That is precisely the hazard: silent renormalization converts a partial view into something indistinguishable from a total view, and the operator acts on 52.2 as though it were the asset's readiness rather than the readiness attributable to contributors they may know about.

Two concrete consequences follow, and both are disclosures the formula alone does not prevent:

1. **Cross-clearance comparison becomes a surprise.** Without the boolean, a cleared operator saying "I show 37" to an uncleared operator showing 52 produces an unexplained discrepancy, and the *surprise itself* is the information — the uncleared operator learns hidden contributors exist, and learns it in an uncontrolled setting with no bound on what else is inferred. With the boolean and count published, the discrepancy is **expected and bounded**: it discloses existence and a count, which is exactly what policy already sanctions, and nothing more. Publishing is therefore *more* protective than silence. This is the reasoning behind rule 3, and it is why the boolean is a security control rather than a courtesy.
2. **Operational error.** A 52.2 that presents as complete will be used to decide the asset is deployable. A 52.2 that presents as partial will be escalated to someone cleared to see 37.0. The boolean is the escalation trigger, and without it the escalation never happens.

### 3.8 Two forbidden fields, and the release rule for weights

Three implementation rules that the formula does not enforce by itself:

- **Release renormalized weights only, always, in every view.** $\tilde w_i$ is released; the intrinsic $w_i$ is not, **even in the high-side view**. Not "not released when contributors are excluded" — never. If raw weights were released when nothing is excluded and renormalized weights when something is, the *presence of the branch* is observable from whether the weights sum to 1, which reintroduces the residual-mass channel through the back door. Structural identity across views is the control. This is enforced in the serializer: the response schema has no field for an intrinsic weight.
- **`visible_weight_share` and every field like it are forbidden.** The single most natural field an engineer adds in the name of transparency — "your view covers 65 % of this asset's criticality weight" — is $\sum_{i \in V} w_i$ published directly. It is the §3.4 leak with a friendly label. Also forbidden by the same argument: `total_contributor_count`, `excluded_weight`, `coverage_fraction`, `score_full`, any `*_of_total` field, and any field whose value is a function of $C \setminus V$. Enforced by `fs-forbidden-fields` (§12.1) as a schema-level denylist over the response models, not as a code review convention.
- **Shares over the uncalibrated subset are safe, because they are shares over $V$.** `uncalibrated_share` $= \sum_{i \in V,\, \text{uncal}} \tilde w_i$ (§4.5) is releasable precisely because its denominator is the visible weight sum. The test is mechanical: a ratio whose denominator ranges over $V$ is releasable; a ratio whose denominator ranges over $C$ is not.

### 3.9 The empty visible set

If $V = \emptyset$ and $C \neq \emptyset$ — every contributor at a scope is compartmented — the formula is undefined (division by zero). The naive rescue is $R(\emptyset) = 100$, "no visible degradation." That is the worst available outcome: it presents a fully compartmented, possibly failed asset as perfectly ready.

**Rule.** $V = \emptyset$ with $C \neq \emptyset$ returns `score: null`, `suppression_reason: "all_contributors_restricted"`, `restricted_contributors_present: true`, and HTTP 200 — not 403, because a 403 discloses that something exists at a scope the requester asked about, whereas a suppressed score with a stated reason discloses the same existence *within the policy that already permits disclosing existence and a count*, and does so without varying the status code by clearance. `V = ∅` with `C = ∅` — a genuinely unassessed scope, e.g. a newly registered asset — returns `score: null`, `suppression_reason: "no_contributors"`, `restricted_contributors_present: false`. The two null-score cases are distinguishable by reason and are never conflated.

This is invariant **V6** applied to clearance, and §4.4 is the same invariant applied to calibration. **In both cases the answer to a missing input is to declare the gap, never to impute a zero.** That symmetry is deliberate and is the single most useful generalization in this document.

### 3.10 Rollup up the tree

| Level | Contributors | Intrinsic weight source |
|---|---|---|
| Installed item | Predictions, anomalies, indicators, deferrals, shortfalls for that item | `criticality_tier.assigned` contributing factors, per NIIN and equipment context `[04 §4]` |
| System | Its installed items, as `kind = child_scope` contributors | System mission-criticality from `rm_configuration_tree` |
| Asset | Its systems, as `child_scope` contributors | Asset-level mission-criticality; OFRP phase may modulate the transform, never the weight of another contributor |
| Fleet / TYCOM | Its assets, as `child_scope` contributors | Grouping weight — hull tasking. Scope mechanism resolved (`tycom`/`tycom_id`, **OD-2**); the weighting figure itself remains `[OPEN]` |

Each level applies §3.2 unchanged with $d_{\text{child}} = D(V_{\text{child}})$. Two propagation rules:

- **`restricted_contributors_present` propagates upward as a logical OR.** If any descendant scope excluded a contributor, the ancestor's disclosure block says so. Silence at fleet level about an exclusion four levels down is rule 3 violated at the level operators actually look at.
- **`restricted_contributor_count` propagates as a sum over descendants.** At fleet scope this is coarse and safe. At **system** scope a count of 1 alongside a named system is very nearly the *"description... or system"* that [06 §5](../architecture/06-demo-decisions-and-assumptions.md) rule 1 prohibits — the count and the scope together identify the thing. This document implements [06 §5](../architecture/06-demo-decisions-and-assumptions.md) as written (boolean and count at every scope) and raises the narrow-scope case as **OD-1**, which [06 §5](../architecture/06-demo-decisions-and-assumptions.md)'s own assumption table already contemplates: *"If exclusion is judged to leak through the count itself, suppress the boolean..."*

### 3.11 Delta attribution — why the score moved

A renormalized score moves for four reasons, and only one of them is degradation. Publishing a movement without saying which is how a methodology change gets read as fleet decline — the failure D36 already fixed for PdM's tier transitions, where *"the transition is annotated so a level shift is not read as fleet degradation."*

Every `readiness.recomputed` and every assessment response therefore carries `delta_attribution` against the previous assessment at that scope:

```json
"delta_attribution": {
  "previous_assessment_id": "…", "previous_score": 55.1, "score": 52.2, "delta": -2.9,
  "from_degradation_change":    -3.4,
  "from_weight_change":          0.0,
  "from_contributor_set_change": 0.5,
  "from_methodology_change":     0.0,
  "contributor_set_changed":     true,
  "exclusion_set_changed":       false,
  "weight_revision_reason":      null
}
```

Rules:
- The four components sum to `delta` `[ESTABLISHED HERE]`; computed by re-evaluating the formula holding each factor at its previous value in a fixed order recorded in the methodology version, so the decomposition is reproducible.
- A weight change caused by `criticality_tier.assigned` sets `weight_revision_reason: tier_reassignment` and is attributed to `from_weight_change`, never to degradation `[03 §6, D36]`.
- **`exclusion_set_changed: true`** whenever `restricted_contributor_count` changed between consecutive assessments. This matters because a contributor whose *label* is upgraded mid-life leaves $V$, and $R(V)$ then jumps with no visible cause — a re-run of the §3.5 leak arriving through relabelling rather than through arithmetic. The annotation makes the jump attributable to a label change rather than to degradation. It discloses no more than the count already does.

---

## 4. Null `p_failure`, and the uncalibrated contribution

### 4.1 What the corrected contract says

[03 §7.1](../architecture/03-integration-contracts.md) as corrected:

> `p_failure?` — *calibrated within its declared reference class.* **NULL when `calibration_population < 50`** (document 06 §3's gate) — below the gate the cell publishes `population_hazard_rate` only, with `reference_class` forced to `class_estimate`. *"A predicted probability that cannot be calibrated must not be emitted merely because the field exists; omission is the honest signal."*

and the consumer obligation, stated as a defect to be avoided:

> *"A consumer that treats a missing `p_failure` as zero, rather than as 'uncalibrated,' reintroduces the comparability defect this field exists to prevent."*

Fleet Status is that consumer, at the largest scale in the system. Of ~8,400 installed items in the demonstration envelope, only ~250 are spotlight items with full-fidelity sensor coverage `[06 §7]`. **The overwhelming majority of contributors to any readiness rollup will carry a null `p_failure`.** Handling the null as zero would not produce a slightly optimistic score; it would produce a score computed almost entirely from ~3 % of the fleet's installed items, with the other 97 % silently asserted to be risk-free. The readiness figure would be structurally blind to the long tail, and it would look excellent.

### 4.2 One transform per reference class, never a shared one

Because *"consumers do not compare `p_failure` across reference classes"* and *"they may, and must, branch on `reference_class`"* `[03 §7.1]`, the derivation of $d_i$ from a `FailurePrediction` is a **per-reference-class** transform, declared in `methodology_version.degradation_transforms`. The transforms convert each prediction into **expected consequence within its own class** and only then aggregate — the same device [03 §7.1](../architecture/03-integration-contracts.md) mandates for the scheduling optimizer: *"the scheduling optimizer applies a per-class decision-theoretic conversion to expected consequence."* Comparing probabilities across classes is prohibited; aggregating consequences is not.

| `reference_class` | `p_failure` | Transform to $d_i$ | `basis` | `uncalibrated` | `render_hint` |
|---|---|---|---|---|---|
| `item` | non-null | $d_i = g_{\text{item}}(p_{\text{failure}}, h)$ — calibrated probability mapped through the consequence curve for the item's criticality band; `rul.p50` sharpens the horizon banding | `calibrated_item` | `false` | `point_estimate` |
| `niin_fleet`, `equipment_family` | non-null | $d_i = g_{\text{pop-cal}}(p_{\text{failure}}, h)$ — a **distinct** curve; the probability is calibrated but not item-conditional, and `rul` is absent by contract `[D19]` | `calibrated_item` is **not** used; `population_hazard` with `p_failure` carried | `true` | `population_band` |
| `class_estimate` | **null** (below the n ≥ 50 gate) | $d_i = g_{\text{pop}}(\lambda, h) = 1 - e^{-\lambda h}$ over `population_hazard_rate` $\lambda$ and `horizon_days` $h$, then through the consequence curve | `population_hazard` | `true` | `population_band` |
| any | null **and** `population_hazard_rate` null | **No transform.** §4.4 | `unassessed` | `true` | `qualitative` |

Three hard rules on the null case:

- **$d_i$ is derived from `population_hazard_rate`, and it is strictly positive whenever $\lambda > 0$.** The example in §3.3 shows it concretely: $\lambda = 0.004/\text{day}$ over 90 days gives $1 - e^{-0.36} = 0.30$, a substantial contribution. `c2` accounts for 5.7 % of the low-side deduction. Under a null-as-zero implementation it would account for 0 %, and `c1`'s share would inflate to 99.7 % — the score would rise and the explanation would misattribute.
- **`rul` is null and no residual-life figure is synthesized.** Non-item reference classes carry `population_hazard_rate` *instead of* `rul` `[03 §7.1, D19]`, because *"a memoryless population fit cannot produce a per-item residual-life distribution, and rendering one indistinguishably from a tier-3 distribution misleads the operator."* `rul_p50_days` stays null on the contributor row and the explanation node renders a band, not a date.
- **The weight is not discounted for being uncalibrated.** The tempting move is to down-weight uncalibrated contributors to reflect epistemic uncertainty. Do not. With ~97 % of items uncalibrated, a weight discount is a systematic, invisible suppression of the long tail — a second route to the same blindness as null-as-zero, arrived at more respectably. Uncertainty is reported (§4.5), not multiplied into the weight. It also violates V3, since any calibration-dependent weight is not a function of the contributor's intrinsic criticality.

### 4.3 The no-implicit-zero rule, mechanically enforced

Prose prohibitions on null coalescing do not survive contact with a codebase. Three enforcement layers:

1. **The contributor row cannot represent "null means zero."** `degradation` is `numeric null` with a `CHECK` that it is null **only** when `basis = 'unassessed'`. A projector that coalesced a null `p_failure` to 0 would have to write `degradation = 0`, which is legal — so the second layer exists.
2. **A sentinel type at the derivation boundary.** The transform functions accept `p_failure: float | None` and are forbidden from writing `p_failure or 0.0`, `p_failure if p_failure else 0`, `float(p_failure or 0)`, or `coalesce(p_failure, 0)`. Enforced by lint rule **`FS-NULL-001`** `[ESTABLISHED HERE]`, an AST rule in the pattern of [10 §4.4](10-shared-packages.md)'s `FTH00n` family: any boolean-coercion or coalesce whose left operand is a `p_failure`-typed expression is a lint failure. The permitted form is an explicit `if p_failure is None:` branch that selects the `class_estimate` transform.
3. **The behavioural test** `fs-null-pfailure` (§12.2), which asserts the score is *strictly lower* with the uncalibrated contributor present than absent, and a mutation test asserting that replacing the null branch with a zero fails the suite.

### 4.4 The genuinely unassessed contributor

If `p_failure` **and** `population_hazard_rate` are both null — no rate of any kind, e.g. a NIIN with no fleet history and no class estimate — there is no defensible $d_i$. Options are: impute zero (forbidden by V6), impute a peer value (fabrication, and it would violate V3 since the imputed value depends on other contributors), or declare the gap.

**Rule.** `basis = 'unassessed'`, `degradation = null`, the contributor is **excluded from the numerator and from the denominator**, and it is declared:

```json
"score_integrity": {
  "unassessed_contributor_count": 3,
  "assessed_contributor_count": 41,
  "uncalibrated_share": 0.62,
  "statement": "3 contributors could not be assessed at any reference class and are excluded from the computation. They are listed in the explanation graph."
}
```

`unassessed_contributor_count` is safe to publish where `restricted_contributor_count`-adjacent quantities would not be, because unassessed contributors are **visible** — they appear in the explanation graph with their identity, their kind, and the reason. Nothing is hidden; a measurement is missing. That distinction is the whole difference between §3.9 and §4.4, and it is worth stating in the response text so an operator does not read the two counts as the same kind of gap.

### 4.5 Distinguishable in the explanation graph, numerically and visually

[04 §5](../architecture/04-subapplication-architectures.md) requires the explanation graph to be a primary output. An uncalibrated contribution must be distinguishable there without the operator having to know the contract. Every contributor node carries, and every explanation response surfaces:

| Field | Purpose |
|---|---|
| `basis` | `calibrated_item` vs `population_hazard` vs `unassessed` — the primary discriminator, an enum, never a computed adjective |
| `uncalibrated` | Boolean, so a client filters without parsing `basis` |
| `reference_class` | `item` \| `niin_fleet` \| `equipment_family` \| `class_estimate` `[03 §7.1]` |
| `calibration_population` | The $n$ behind the cell. Null where ungated. Shows *how far* below 50 |
| `fallback_level` | 0..4 cold-start depth, **separate from `confidence`** `[03 §7.1, D7]` |
| `confidence`, `sharpness` | Sharpness and fit only. Never read as epistemic depth |
| `p_failure` | Carried through as **null**, not omitted and not zeroed, so a client can see the null |
| `population_hazard_rate` | The figure actually used |
| `rul_p50_days` | Null for non-item classes; a client that renders a date from a null is failing visibly rather than silently |
| `render_hint` | `population_band` for uncalibrated, `point_estimate` for calibrated. Discharges [06 §3](../architecture/06-demo-decisions-and-assumptions.md)'s alternative: *"a rate band explicitly labelled as population-derived, visually distinct from an item distribution"* |
| `uncalibrated_share` (assessment level) | $\sum_{i \in V,\,\text{uncal}} \tilde w_i$ — "62 % of this score's weight rests on population estimates, not item-conditional calibration." Computed over $V$, hence releasable (§3.8) |

`render_hint` is an API-level field rather than a UI concern for the same reason the advisory label is (§8): the UI is not necessarily ours `[04 §5]` — *"the sub-application most likely to be duplicated by a customer's existing dashboard"* — so the distinction must be carried in the contract, where an external presentation layer cannot fail to receive it.

### 4.6 Consequence for `packages/canonical-schemas` — OQ-10 is now closed

[10 §11](10-shared-packages.md) records **OQ-10** as a Phase 3 blocker:

> §7.1 lists `p_failure` unconditionally, but document 06 §3 says that below the n≥50 calibration gate the prediction publishes *"with a population hazard rate and no calibrated probability."* Those cannot both hold. **`p_failure` required** (03 is binding)... If document 06's reading is correct, `p_failure` must become nullable — a **major** schema change. Reconcile before Phase 3.

[03 §7.1](../architecture/03-integration-contracts.md) has since been corrected and now states the nullability explicitly. **Document 06's reading was correct, and the major schema change is required.** This document does not make that change — it is [10](10-shared-packages.md)'s to make — but it depends on it, and it names the exact edits so the dependency is not discovered by a runtime validation error:

| Location in [10](10-shared-packages.md) | Current | Required |
|---|---|---|
| `FailurePrediction.p_failure` (§4.6) | `float = Field(ge=0.0, le=1.0, …)` | `float \| None = Field(default=None, ge=0.0, le=1.0, …)` |
| `_calibration_gate` validator (§4.6) | Rejects a sub-floor prediction that is not `class_estimate` | Additionally: **require** `p_failure is None` when `calibration_population < CALIBRATION_POPULATION_FLOOR`, and require `population_hazard_rate is not None` in that case. A non-null `p_failure` below the gate must be rejected at the boundary, not accepted and consumed |
| Golden-vector corpus (§4.9) | — | Add `FailurePrediction/valid/null_p_failure_below_gate.json` and `invalid/p_failure_present_below_gate.json` |
| OQ-10 (§11) | Open, Phase 3 blocker | **Closed** by the 03 §7.1 correction, resolved in favour of nullability |

Logged as **OD-4**. Until it lands, `fleet-status` treats a non-null `p_failure` accompanied by `calibration_population < 50` as a **contract violation of the producer**, rejects the contributor derivation, records the row as `basis = 'unassessed'`, and increments `fathom_contract_violations_total{producer="pdm"}` — it does not silently use the ungated probability. A consumer that quietly accepts malformed input is how a schema defect survives to production.

---

## 5. The explanation graph

### 5.1 Structure, and why it is persisted rather than recomputed

Nodes are `DegradationContributor` rows; edges are `parent_contributor_id` within a scope and `child_scope` contributors across scopes. The root is a `ReadinessAssessment`.

**The graph is written in the same database transaction as the assessment that summarizes it** `[ESTABLISHED HERE]`. It is never rebuilt at query time. The reason is not performance:

> If the explanation is recomputed at query time from current read-model state, and the score was computed at $t_0$, the two can disagree — inputs moved in between. An operator then sees a score whose explanation does not add up to it, which is ES-4 violated in practice even though the formula satisfies it in theory. Worse, the discrepancy is indistinguishable, from the operator's side, from the §3.5 leak. Persisting the decomposition with the score makes ES-4 a **structural** property of the stored data rather than a property of a computation that happens to be repeated identically.

`inputs_digest` on the assessment is a hash over its contributor rows, so a rebuild that produces a different decomposition is detected rather than inferred (§12.7).

### 5.2 Contributor kinds and their `evidence_ref` targets

Every contributor resolves to a source record held by its owning sub-application, per obligation 9 `[03 §15]`: *"Records provenance for every derived value it publishes — inputs, versions, and computation reference — sufficient to trace any operator-visible figure to its sources."* [04 §5](../architecture/04-subapplication-architectures.md) names the four required terminal kinds — *"a prediction, a casualty, a deferral, or a parts shortfall"* — and this table is the full set.

| `kind` | Source event | `evidence_kind` | `evidence_ref` target | Owner |
|---|---|---|---|---|
| `prediction` | `prediction.updated` | `prediction` | `/api/v1/pdm/predictions/{id}` and `/predictions/{id}/provenance` | `pdm` |
| `configuration_invalidation` | `prediction.invalidated`, `configuration.baseline_changed` | `record` | `/api/v1/pdm/predictions/{id}`; `baseline_id` + `baseline_epoch` | `pdm`, `registry` |
| `tier_transition` | `criticality_tier.assigned` | `record` | `/api/v1/pdm/criticality?niin=` | `pdm` |
| `observed_anomaly` → `anomaly` | `anomaly.detected` | `record` | telemetry anomaly record; detector version, window, channels implicated, `origin` | `telemetry` |
| `health_indicator` | `health_indicator.computed` | `record` | indicator record with **definition version and definition-time** | `telemetry` |
| `casualty_candidate` | derived within Fleet Status from the above | `record` | the contributing evidence set; **never asserts a CASREP exists** (§8) | *(this service)* |
| `deferral` | `deferral.recorded` | `record` | deferral record carrying **`deferral_reason_class`** | `maintenance` |
| `planned_mitigation` | `work_candidate.created`, `work_order.opened`, `work_package.proposed`, `work_package.approved` | `record` | work candidate / work order / work package | `maintenance` |
| `parts_shortfall` | `allowance_shortfall.detected` | `record` | shortfall record: allowance vs on-hand, driver | `supply` |
| `requisition_delay` | `part_availability.changed`, `requisition.status_changed` | `record` | requisition document number, projected availability, `lead_time`, `condition_code` | `supply` |
| `causal_finding` | `causal_finding.published` | `record` | adjudicated hypothesis; `strength_band`/`band_limiting_axis`/`strength_rule_version`; `treatment_handling` | `failure-intel` |
| `redesign_signal` | `redesign_candidate.created`, `redesign_case.published` | `record` | candidate / case | `design-advisory` |
| `child_scope` | *(internal)* | `record` | the child `ReadinessAssessment` | *(this service)* |

Two constraints on the kinds:

- **`deferral` contributors branch on `deferral_reason_class`.** [03 §6](../architecture/03-integration-contracts.md): *"`deferral_reason_class` distinguishes capacity, operational tempo, parts unavailability, and disagreement with the risk estimate. Only the last is evidence about prediction quality; treating all deferrals as such biases models toward under-prediction"* `[D34]`. Fleet Status is not a model, but the same distinction governs the readiness contribution: a deferral for **capacity** or **optempo** is accepted risk and contributes; a deferral recording **disagreement with the risk estimate** must not be double-counted against the same prediction that already contributes. The transform is declared per class in the methodology version, and the disagreement class contributes 0 weight *as a separate contributor* — it is instead recorded as a `render_hint: qualitative` annotation on the prediction contributor it disputes.
- **`causal_finding` and `redesign_signal` contribute qualitatively, never quantitatively.** [03 §7.1](../architecture/03-integration-contracts.md) requires that *"a causal statement must cite an adjudicated Failure Intelligence hypothesis"* and that agents *"must not render [contributing factors] in causal language"*. These nodes appear in the explanation graph as annotations with `degradation = null`, `basis = 'unassessed'`-adjacent handling, and `weight` excluded from the aggregate. They explain *why* a contributor is degrading; they do not add to the deduction, because doing so would double-count the prediction they explain.

### 5.3 The traversal

`GET /api/v1/fleet-status/readiness/{assessment_id}/explanation` decomposes a figure into its contributors, recursively across child scopes, each with resolvable provenance.

```sql
-- Executed under a visibility predicate bound from the requester's ABAC attributes.
-- The predicate is a JOIN condition, NOT a post-filter (§5.5).
WITH RECURSIVE visible_contrib AS (
    SELECT c.*, 0 AS depth, c.contributor_id::text AS path
      FROM degradation_contributor c
      JOIN fn_label_visible(c.classification_label, :principal_attrs) v ON v.visible
     WHERE c.assessment_id = :assessment_id
       AND c.parent_contributor_id IS NULL
  UNION ALL
    SELECT c.*, p.depth + 1, p.path || '>' || c.contributor_id::text
      FROM degradation_contributor c
      JOIN visible_contrib p
        ON c.parent_contributor_id = p.contributor_id
        OR (p.kind = 'child_scope' AND c.assessment_id = p.child_assessment_id)
      JOIN fn_label_visible(c.classification_label, :principal_attrs) v ON v.visible
     WHERE p.depth < :max_depth
),
-- Renormalization runs over the VISIBLE set only. ES-2 by construction: no CTE in this
-- query may reference degradation_contributor without fn_label_visible.
norm AS (
    SELECT sum(weight)                                    AS w_sum,
           sum(weight * power(degradation, :p))            AS num
      FROM visible_contrib
     WHERE basis <> 'unassessed' AND degradation IS NOT NULL
)
SELECT vc.contributor_id, vc.path, vc.depth, vc.kind, vc.basis, vc.uncalibrated,
       vc.reference_class, vc.calibration_population, vc.p_failure,
       vc.population_hazard_rate, vc.rul_p50_days, vc.fallback_level,
       vc.confidence, vc.sharpness, vc.horizon_days, vc.render_hint,
       vc.weight / n.w_sum                                        AS released_weight,
       vc.weight * power(vc.degradation, :p) / nullif(n.num, 0)    AS attribution_share,
       vc.degradation,
       vc.evidence_kind, vc.evidence_ref,
       vc.source_event_id, vc.source_event_type, vc.source_producer,
       vc.source_producer_node, vc.source_monotonic_seq,
       vc.baseline_id, vc.baseline_epoch, vc.stale,
       vc.classification_label -> 'inherited_from'                AS inherited_from
  FROM visible_contrib vc CROSS JOIN norm n
 ORDER BY attribution_share DESC NULLS LAST, vc.path;
```

Response shape, with the two mandatory blocks from §3.7 and §4.4 at the root:

```json
{
  "assessment_id": "…", "scope": "asset", "subject": {"asset_id": "…"},
  "advisory": { "…": "§8.1" },
  "advisory_readiness_score": 52.2,
  "degradation": 0.4775,
  "aggregation": {"formula": "weight_renormalized_power_mean", "exponent": 3,
                  "methodology_version": "1.4.0"},
  "contributor_disclosure": { "…": "§3.7 — always present, every view" },
  "score_integrity":        { "…": "§4.4 — always present, every view" },
  "delta_attribution":      { "…": "§3.11" },
  "contributors": [
    {"contributor_id": "…", "path": "…", "kind": "prediction",
     "basis": "calibrated_item", "uncalibrated": false, "reference_class": "item",
     "released_weight": 0.615, "attribution_share": 0.940, "degradation": 0.55,
     "deduction_points": 44.9, "render_hint": "point_estimate",
     "evidence": {"kind": "prediction", "ref": "/api/v1/pdm/predictions/…",
                  "provenance_ref": "/api/v1/pdm/predictions/…/provenance"},
     "source": {"event_id": "…", "event_type": "fathom.pdm.prediction.updated",
                "producer": "pdm", "producer_node": "enterprise", "monotonic_seq": 918273},
     "classification": {"level": "U", "inherited_from": ["…"]}},
    {"contributor_id": "…", "kind": "prediction",
     "basis": "population_hazard", "uncalibrated": true,
     "reference_class": "class_estimate", "p_failure": null,
     "calibration_population": 17, "population_hazard_rate": 0.004,
     "rul_p50_days": null, "fallback_level": 3,
     "released_weight": 0.231, "attribution_share": 0.057, "degradation": 0.30,
     "deduction_points": 2.7, "render_hint": "population_band",
     "evidence": {"…": "…"}, "source": {"…": "…"}}
  ]
}
```

`deduction_points` $= s_i \times (100 - R(V))$, and the `deduction_points` over all contributors sum to $100 - R(V)$ exactly, to the declared tolerance. That equality is the whole point of the endpoint, and `fs-decomp` (§12.4) asserts it on every assessment in the reference dataset.

**Latency budget:** p95 < 4 s for explanation decomposition, p95 < 1.5 s for fleet and asset views `[06 §7]`. `max_depth` defaults to the full tree; a client requesting fleet-scope explanation at full depth traverses ~8,400 leaves, so the endpoint is cursor-paginated over contributors ordered by `attribution_share DESC` — the ordering an operator wants anyway — with the two disclosure blocks repeated on every page so a client that reads only page 1 cannot miss them.

### 5.4 `inherited_from[]` must be walkable

[03 §7.3](../architecture/03-integration-contracts.md): *"Every derived value carries the union of its inputs' labels, recorded in `inherited_from` and enforced by the provenance obligation in §15."* "Walkable" means each reference resolves to a retrievable label, and the chain terminates at a `derived_from` classification-authority reference. Rules:

- Each contributor's `classification_label.inherited_from[]` holds the label references of **its own** inputs — the prediction, the indicator, the deferral it came from.
- The assessment's `classification_label_full` is `ClassificationLabel.union(*all_contributor_labels, derived_from=…)`, using the shared helper from [10 §4.8](10-shared-packages.md) and never a local reimplementation. That helper's docstring already draws the boundary this document works inside: *"it does not implement the aggregation policy of §7.3 / document 06 §5... This method computes a label; it does not decide what to aggregate."* Fleet Status decides what to aggregate; the helper labels it.
- **The released label of a view is the union over $V$, not over $C$.** This is not a detail. If the response carried `classification_label_full`, the label itself would name a compartment that appears only on an excluded contributor — disclosing by marking what §3.2 was careful not to disclose by arithmetic. So: `released_label = ClassificationLabel.union(*[c.label for c in V])`, and `inherited_from[]` in a released response lists only the visible inputs' references, with the excluded count carried in `contributor_disclosure` (§3.7) and nowhere else.
- `ClassificationLabel.union` **raises** on an un-orderable `distribution_statement` combination (OQ-16 of [10 §11](10-shared-packages.md)). Fleet Status does not catch and default that exception. It fails the assessment computation, records `freshness: refused` with the reason, and increments a counter — because a derived readiness figure whose classification cannot be mechanically determined must not be published under a guessed marking. Logged as **OD-5**.

### 5.5 Clearance is enforced in the join, and the low-side traversal is shape-identical

[03 §7.3](../architecture/03-integration-contracts.md), on the vector store, states the principle generally: *"enforces at query time rather than post-filtering, because post-filtering leaks the existence of records."* [04 §11](../architecture/04-subapplication-architectures.md) repeats it. It applies here at least as strongly, because the explanation graph is what D13 calls the pointer: *"the explanation graph hands over the pointer."*

| Requirement | Implementation |
|---|---|
| No post-filter | `fn_label_visible(...)` is an inner join in every CTE that touches `degradation_contributor`. A CI check (`fs-no-postfilter`) greps the repository layer for any `degradation_contributor` reference not accompanied by the visibility join in the same statement |
| Counts come from a counter, not from filtered rows | `restricted_contributor_count` is read from `readiness_assessment`, computed at write time. It is **never** derived at read time as `count(all) - count(visible)`, because that computation requires an unfiltered read in the same query, which is a post-filter with extra steps |
| Identical shape across views | The low-side response has the same keys, the same nesting, and the same disclosure blocks as the high-side response. Only values differ. No key is present in one view and absent in the other |
| No side channel through cardinality or timing | `fs-excl-timing` (§12.1) asserts that response size and query latency for a scope with restricted contributors are statistically indistinguishable from a scope without them at equal **visible** cardinality. Where they are not, the assessment pads by materializing the visible decomposition into a fixed-shape projection at write time |
| No leak through errors | Problem-details responses for a restricted scope are byte-identical to those for a non-existent scope in `type`, `title`, and `status`. `detail` never names a compartment, a system, or a contributor. §10.4 |
| No leak through ETag | The `ETag` is derived from the **view's** version, not the assessment's `version` column, since the latter increments when an invisible contributor changes and a changing ETag on an unchanged body is a change notification (ES-3 defeated through HTTP caching). `ETag = W/"<view_hash>"` where `view_hash` covers only the released payload |

The ETag rule is the subtlest item in this document and the easiest to get wrong: §3.2 guarantees the low-side *number* does not move, and a naively derived ETag then announces the movement anyway.

---

## 6. Risk flags and hysteresis

[04 §5](../architecture/04-subapplication-architectures.md): *"A flag that raises and clears as a probability oscillates around a threshold trains operators to ignore flags. Raise and clear thresholds differ, and a minimum dwell time applies before either transition."* No numeric values are given there, so every value below is `[ESTABLISHED HERE]` and a **tunable placeholder**, living in `methodology_version.thresholds` and `methodology_version.hysteresis` with its citation. [04 §5](../architecture/04-subapplication-architectures.md)'s Phase 3 question — *"Threshold and hysteresis values, and whether they vary by class or OFRP phase"* — remains open as **OD-3**.

### 6.1 States

| State | Meaning | Event published |
|---|---|---|
| `candidate` | Raise threshold met; raise dwell not yet satisfied. **Not operator-visible as a flag** | none |
| `raised` | Raise dwell satisfied | `casrep_risk.raised` |
| `evidence_invalidated` | The prediction behind the flag was invalidated. **Distinct from cleared** (§6.4) | none — the flag remains raised in the operator's view, annotated |
| `mitigation_in_progress` | A work order was opened against the item. Still raised | none |
| `clearing` | Clear threshold met; clear dwell not yet satisfied. **Still raised** | none |
| `cleared` | Clear dwell satisfied, or the item left the baseline, or authorized suppression | `casrep_risk.cleared` |
| `suppressed` | Methodology-authority suppression, audited, with a named approver | `casrep_risk.cleared` with cause |

Only two of the seven states publish an event, which is deliberate: the whole purpose of hysteresis is that intermediate states do not reach the operator.

### 6.2 Thresholds, per reference class

The driving statistic is the item's contributor degradation $d_i$ at the flag's horizon — the *same* quantity the score uses, so a flag and a score can never disagree about an item.

Thresholds are declared **per reference class**, because a `class_estimate` degradation and an item-conditional degradation are not comparable `[03 §7.1, D7]`. Using one threshold set for both is the comparability defect, re-created in the threshold table instead of in the probability.

**One tunable governs the band:** `clear_threshold = raise_threshold × (1 − band_ratio)`, `band_ratio = 0.30`.

| `reference_class` | `severity` | Raise ($d \ge$) | Clear ($d <$) | Raise dwell | Clear dwell | `predicted_casualty_category_candidate` |
|---|---|---|---|---|---|---|
| `item` | `advisory_watch` | 0.35 | 0.245 | 2 cycles **and** 48 h | 3 cycles **and** 7 d | 2 |
| `item` | `casualty_risk_moderate` | 0.55 | 0.385 | 2 cycles **and** 48 h | 3 cycles **and** 7 d | 3 |
| `item` | `casualty_risk_high` | 0.75 | 0.525 | 1 cycle **and** 24 h | 4 cycles **and** 14 d | 4 |
| `niin_fleet`, `equipment_family`, `class_estimate` | `advisory_watch_population` | 0.45 | 0.315 | 3 cycles **and** 96 h | 3 cycles **and** 14 d | 2 |
| `niin_fleet`, `equipment_family`, `class_estimate` | `casualty_risk_moderate_population` | 0.65 | 0.455 | 3 cycles **and** 96 h | 3 cycles **and** 14 d | 3 |
| *(uncalibrated)* | **no `_high` severity exists** | — | — | — | — | — |

Three principles are encoded, and each is a design commitment rather than a number:

1. **Raise fast, clear slow.** The clear dwell always exceeds the raise dwell, and it lengthens with severity. A category-4 candidate takes 4 cycles and 14 days to clear and 1 cycle and 24 hours to raise. Asymmetry is the point: the cost of a late raise is a casualty, the cost of an early clear is a casualty that was already detected and then un-detected, which is worse because it consumed and then destroyed the operator's trust.
2. **Uncalibrated flags raise higher and dwell longer, and cannot reach top severity.** A population hazard rate cannot support an item-specific high-severity assertion — the same reasoning that makes `rul` unemittable for non-item reference classes `[03 §7.1, D19]`. The severity vocabulary is suffixed `_population` so that Notification and Maintenance can route differently and **no consumer can accidentally compare the two ladders**.
3. **Both dwell conditions must be met.** Not either — both. Cycles alone is wrong because a stalled scoring pipeline stops the clock. Duration alone is wrong because scoring cadence varies by more than an order of magnitude: *"Daily for tiers 0–1, per-mission-completion for tiers 2–3"* `[06 §7]`. A submarine item scored per-patrol may see one update in six weeks, and a 48-hour wall-clock dwell would then raise on a single observation, which is no hysteresis at all.

### 6.3 Dwell measurement, and the clock discipline that constrains it

[03 §5.4](../architecture/03-integration-contracts.md): *"Durations, timeouts, retry backoff, and lease expiry use a monotonic clock, never the wall clock. A wall-clock backoff loop storms or hangs the instant a step lands."* The STIG rule **V-260520** mandates `makestep 1 -1`, so a backward clock step is guaranteed at reconnection — exactly when an edge-produced burst of `health_indicator.computed` and `anomaly.detected` events arrives and drives the statistic.

| Quantity | Measured by | Never by |
|---|---|---|
| Dwell duration | `dwell_monotonic_ms`, accumulated from a monotonic source | `now() - raised_at`, or any difference of wall-clock timestamps |
| Dwell cycles | Count of distinct `scoring_run_id` values observed for the item since `first_crossed_at` | `computed_at` ordering — *"a stale result looks fresher by `computed_at`"* `[D3]` |
| Event ordering into the state machine | `(source_producer, source_producer_node, source_monotonic_seq)` or the HLC | `source_time` `[03 §5.4]` |
| Audit of the transition | `recorded_at`, retained with the full `clock` block including `sync_quality` | — |

Two further rules:

- **A high `dispersion_ms` forbids duration-based dwell entirely.** [03 §5.4](../architecture/03-integration-contracts.md): *"epsilon exceeding the inter-write interval forces causal-only ordering and forbids any timestamp arbitration."* Where the contributing events' `sync_quality.dispersion_ms` exceeds the dwell duration, the duration condition is **unevaluable** and the cycle condition alone governs, with the transition annotated `dwell_basis: cycles_only`. Silently trusting the duration under a large epsilon is timestamp arbitration under another name.
- **`replay: true` events advance no dwell timer and raise no flag** `[03 §5.3]`: *"Consumers must ignore or handle `replay: true` events idempotently and must not raise operator-visible alerts from them."*

### 6.4 Invalidation is not a clear — the most important rule in this section

When `prediction.invalidated` arrives — most consequentially from `configuration.baseline_changed`, which [03 §6](../architecture/03-integration-contracts.md) calls *"the most consequential event in the system"* and *"a correctness signal rather than an informational one"* — the flag resting on that prediction transitions to **`evidence_invalidated`**, not to `cleared`.

In that state: the flag **remains operator-visible as raised**, annotated *"the evidence behind this flag was invalidated by a configuration change and re-scoring is pending"*; **no `casrep_risk.cleared` is published**; and the **dwell timer is frozen, not reset** — so when a fresh prediction arrives, accumulated dwell resumes rather than restarting, and an item does not escape a raise by having its baseline changed repeatedly.

The reason is [04 §4](../architecture/04-subapplication-architectures.md)'s: *"Silent staleness after a component replacement is the failure mode most likely to destroy operator trust permanently."* A flag that disappears the moment its evidence is invalidated is worse than silent staleness — it is **active false reassurance**, and it is trivially reachable, since replacing a nearby component changes the baseline epoch for the whole asset.

### 6.5 The three permitted clear causes, and a gap in the consumed-event list

| `clear_cause` | Trigger available to Fleet Status |
|---|---|
| `statistic_below_clear_threshold` | The driving statistic falls below the clear threshold for the clear dwell |
| `item_left_baseline` | The installed item is no longer in the asset's configuration. **Derived from `configuration.baseline_changed`**, whose payload carries the *"changed installed-item set"* `[03 §6]` |
| `methodology_suppression` | Explicit, audited, named-approver suppression via an internal operation |

**Note what is not on this list, and why.** "The maintenance action fixed it" is not a clear cause, because **`maintenance_action.recorded` is not in Fleet Status's consumed set.** [03 §6](../architecture/03-integration-contracts.md) lists its consumers as `pdm`, `failure-intel`, `registry`, `supply`, `pma`, `design-advisory` — not `fleet-status`. Fleet Status therefore learns that a repair happened only indirectly: as a `configuration.baseline_changed` if the item was replaced, or as a subsequent `prediction.updated` with a lower probability once PdM re-scores.

The consequence is a real and stated limitation: **a flag on a repaired-but-not-replaced item persists until the next scoring cycle moves the statistic**, which for a tier-2/3 item is the next mission completion. `work_order.opened` is available and moves the flag to `mitigation_in_progress`, which is the right partial mitigation — the operator sees "raised, work in progress" rather than "raised, ignored" — but it is not a clear, because an opened work order is not a completed repair.

This is not a defect to work around locally. It is logged as **OD-6**, and it is the same gap that §7 turns on.

---

## 7. Warning lead-time coverage — an ownership determination

### 7.1 The determination

[06 §2](../architecture/06-demo-decisions-and-assumptions.md) makes **warning lead-time coverage** the program's primary effectiveness metric, replacing "predicted CASREPs avoided": *"the proportion of corrective maintenance actions preceded by a raised risk flag at or beyond a stated horizon, with the lead-time distribution."*

**Determination.** Fleet Status **does not own this metric, does not define it, and must not be its authoritative computation.** It owns and publishes the metric's flag-side input — the `RiskFlagTransition` ledger of §2.5 — as a first-class, versioned, `changed_since`-readable contract, and it *displays* the metric as a clearly attributed, read-only figure sourced from elsewhere.

This is stated explicitly rather than resolved by silent omission, because the metric names a "raised risk flag", the only thing that raises risk flags is this service, and the natural inference is that the metric therefore lives here. That inference is wrong for four independent reasons.

### 7.2 Why not here

1. **Fleet Status cannot compute it. It does not consume the numerator's other half.** The metric's denominator is *corrective maintenance actions*, which are `maintenance_action.recorded` events carrying `failure_indicator` — and [03 §6](../architecture/03-integration-contracts.md) does not list `fleet-status` as a consumer of that event (§6.5). Fleet Status has the flags and no access to the corrective actions. Any implementation here begins with a request to amend [03 §6](../architecture/03-integration-contracts.md), which should be a signal that the metric is being placed in the wrong service rather than a formality to push through.
2. **Measuring your own effectiveness inside the service that tunes the thresholds is the metric trap [06 §6](../architecture/06-demo-decisions-and-assumptions.md) exists to close.** That section names the pattern precisely: a governing metric improves while the capability degrades, and *"both precision and review duration improve while recall collapses."* The Fleet Status analogue is direct and easy: lowering every raise threshold in §6.2 raises lead-time coverage monotonically, at the cost of a flood of flags that trains operators to ignore flags — the exact failure hysteresis exists to prevent. [06 §2](../architecture/06-demo-decisions-and-assumptions.md) says the metric *"cannot be gamed by suppressing predictions"*, which is true; it can be gamed by **lowering thresholds**, and the party holding the thresholds must not also hold the scoreboard. Independent computation is the control, exactly as canary recall is computed independently of the reviewers it measures.
3. **The metric is evaluated against a policy-frozen holdout stratum Fleet Status has no knowledge of and should not acquire.** [06 §2](../architecture/06-demo-decisions-and-assumptions.md) defines a 10 % holdout *"excluded from prediction-driven intervention"*, and the metric set is interpreted against it, with treatment assignment recorded in `triggering_driver`, `triggering_prediction_id`, and `policy_version` on `maintenance_action.recorded` `[D1, D21]`. Holdout membership is a label-construction and causal-inference concept belonging to `pdm` and the analytics path. If Fleet Status knew which items were in the holdout, it would be one refactor away from *scoring them differently*, which destroys the holdout.
4. **Its sibling primary metric is uncomputable here on the same grounds, and the two must not be split.** *"Actionable precision — the proportion of raised flags resolved by a maintenance action that found the predicted condition"* `[06 §2]` requires findings coding, which Fleet Status does not consume. Computing one primary metric here and the other elsewhere would give the two halves of one metric set different owners, different refresh cadences, and different definitions of "flag raised" — and they are reported side by side, which is precisely how the pair is supposed to work.

### 7.3 Where it belongs

**The cross-cutting effectiveness-analytics path, anchored on `audit`.** [04 §11](../architecture/04-subapplication-architectures.md) makes `audit` the *"immutable, append-only record of predictions, tags, proposals, adjudications... correlated by `X-Correlation-Id`"*, and [03 §6](../architecture/03-integration-contracts.md) already routes evaluation data through it: *"`anomaly_tag.*` reaches agent evaluation through `audit`, which exports to Domino's Experiment Manager. Domino workloads do not consume Kafka topics"* `[C19]`. That is the same shape this metric needs: joined across producers, computed outside the services being measured, exported to the platform where model and program evaluation already lives, and reported on the same dashboard as canary recall and actionable precision per [06 §6](../architecture/06-demo-decisions-and-assumptions.md).

It is also where the metric's inputs already converge — `maintenance_action.recorded` with its treatment-assignment fields, holdout membership, findings coding, and (once §7.4 lands) the flag-transition ledger. **No sub-application holds all four, and none should.**

This assignment is not made by any current architecture document — [06 §2](../architecture/06-demo-decisions-and-assumptions.md) defines the metric without naming an owner. Raised as **OD-7**, with the recommendation above.

**OD-7 resolved.** `32-audit.md` §10.7 (amendment) adds `GET /effectiveness/warning-lead-time-coverage`, implementing this section's formula exactly, joined from the universal-consumer feed amendment 03-5 already gives `audit` over `risk_flag_transition` and `maintenance_action.recorded`. §7.6 below calls this operation.

### 7.4 What Fleet Status therefore owes, exactly

The flag side of the metric is a genuine Fleet Status obligation, because nobody else can reconstruct it: `casrep_risk.raised` on the bus is retained 7–30 days `[03 §5.1]`, and *"the event bus is not a rebuild source"* `[D5]`. Without a durable, queryable ledger the metric is uncomputable over a 24-month history.

| Obligation | Requirement |
|---|---|
| **Append-only transition ledger** | §2.5. No `UPDATE`, no `DELETE`. Retained for the full demonstration history, not on the event-retention window |
| **`changed_since` read** | `GET /risk-flags/transitions?changed_since=&cursor=&limit=` — obligation 5 `[03 §15]`. This is the metric's ingest path |
| **A stated definition of "raised at horizon $h$"** | A transition to `raised` with `horizon_days >= h`, at `recorded_at`. Fleet Status **defines its own term** — what a raise *is* — and nothing beyond it. The analytics layer defines the metric |
| **`methodology_version` on every transition** | So the analytics layer can stratify by methodology and detect that a coverage improvement coincided with a threshold change. Without this, threshold-gaming is invisible to the very metric designed to be un-gameable |
| **`reference_class` and `uncalibrated` on every transition** | So coverage attributable to calibrated item-conditional flags is reportable separately from coverage attributable to population estimates. Aggregating them would let long-tail population flags, which fire on ~97 % of items, inflate a figure read as item-level predictive skill |
| **No recomputation of history** | V5. Re-deriving past assessments under a new methodology would silently rewrite the ledger the metric is computed from |

### 7.5 The computation, specified

Specified here so the ledger's shape can be verified against it, and so the analytics owner inherits a definition rather than writing a second one. The computation itself is **not** implemented in `services/fleet-status`.

For a horizon $h$ (each of 30, 90, 180 days `[06 §7]`), a window $W$, and a stratum $S$ (equipment family, domain, reference class, holdout membership, methodology version):

$$
\text{Coverage}(h, W, S) \;=\;
\frac{\bigl|\{\,a \in A(W,S) \;:\; \exists\, t \in T(a),\; t.\texttt{to\_state} = \texttt{raised},\; t.\texttt{horizon\_days} \ge h,\; 0 < \text{lead}(a,t) \le h \,\}\bigr|}
     {\bigl|A(W,S)\bigr|}
$$

where $A(W,S)$ is the set of **corrective** maintenance actions in $W \cap S$ (`maintenance_action.recorded` with `failure_indicator` indicating a corrective action), $T(a)$ is the set of transitions on the same `installed_item_id`, and

$$
\text{lead}(a, t) \;=\; a.\texttt{recorded\_at} - t.\texttt{recorded\_at}
$$

Rules that make the figure defensible rather than merely computable:

- **Lead time is measured on `recorded_at`, not `occurred_at`.** [03 §5.4](../architecture/03-integration-contracts.md): *"audit uses `recorded_at`"*, and *"feature computation must not use `occurred_at` for any value authored with hindsight"* `[D22]`. A maintenance action's `occurred_at` can be backdated at shore-side coding, which would manufacture lead time out of an administrative delay.
- **The flag must have been raised, not merely a candidate.** A `candidate` transition does not count: it was never operator-visible (§6.1), so it warned nobody. This is the single most likely place for the metric to be inflated by an implementer who queries `risk_flag` instead of `risk_flag_transition`.
- **A flag in `evidence_invalidated` still counts as raised**, because it remained operator-visible (§6.4). Conversely, a flag that reached `cleared` **before** the action, and was not re-raised, does not count — the system warned and then withdrew the warning, and the operator was not warned at the time it mattered.
- **Report the lead-time distribution, not only the proportion** `[06 §2]`: p10 / p50 / p90 of $\text{lead}(a,t)$ over the covered subset, plus the count of $A(W,S)$, plus the uncovered count. A coverage figure without its denominator is not interpretable.
- **Stratify by `reference_class` and by methodology version, always.** Per §7.4.
- **Report against the chance reference.** [13 §16](13-synthetic-data-generator.md) fixes it: *"the chance reference is a random flagger with the same flag budget as the baseline under test. Its expected coverage equals its flag rate."* Coverage reported without the flag rate cannot be distinguished from coverage bought by flagging everything, and that is the threshold-gaming channel of §7.2 made visible.
- **The achievable ceiling is below 1.0 and must be shown.** [13 §7.2, §16.4 gate G-6](13-synthetic-data-generator.md): every equipment family declares an `unpredictable_fraction`, and *"a dataset on which perfect prediction is possible is an invalid dataset."* On synthetic data the ceiling is known, so coverage is reported **as a fraction of the achievable ceiling** as well as absolutely. Omitting it invites a demonstration that reports 0.94 against an achievable 0.95 as though the remaining 0.06 were an engineering shortfall.

### 7.6 What Fleet Status displays

Fleet Status may surface the metric on its own read surface — it is the readiness-facing service and the figure belongs next to the readiness picture — under three constraints:

1. **Read-only and attributed.** The value is fetched from `audit`'s `GET /effectiveness/warning-lead-time-coverage` (§7.3's OD-7 resolution, `32-audit.md` §10.7) and returned with `"source": "audit"`, `"computed_at"`, and `"definition_ref"`. Fleet Status never computes it, never caches it past its stated freshness, and never derives a variant of it.
2. **Never viewer-filtered.** A coverage figure computed over only the flags a given viewer can see is **not the program metric** — it is a different statistic with the same name, and it would move as clearance changes. The metric is computed high-side once and released only at scopes where the aggregate is releasable at the requester's level. If it cannot be released, the field is `null` with `suppression_reason`, exactly as in §3.9. It is **never** silently recomputed over the visible subset. This is the §3.5 leak reappearing in a metric panel, and it is easy to introduce precisely because filtering-by-clearance is the correct default everywhere else in this service.
3. **Labelled advisory like everything else** (§8).

---

## 8. Advisory, not authoritative — at the API level

[04 §5](../architecture/04-subapplication-architectures.md), key decision 1:

> **Advisory overlay, not a readiness system of record.** Navy readiness reporting has authoritative systems and formal definitions. This sub-application produces a *predictive* readiness view intended to inform action ahead of formal reporting. **It must not present itself as, or be mistaken for, authoritative readiness reporting.** Terminology, labelling, and interface language are constrained accordingly, and this is an **accreditation and acceptance concern rather than a stylistic one**.

We are not designing the UI. That makes this harder, not easier, because [04 §5](../architecture/04-subapplication-architectures.md) also names Fleet Status *"the sub-application most likely to be duplicated by a customer's existing dashboard. The API is designed to be consumed by an external presentation layer for exactly that reason."* An external dashboard will not inherit our labelling conventions. **The advisory character must therefore be carried in the contract, in a form a consuming UI cannot receive-and-discard without noticing.** Four mechanisms, deliberately redundant:

### 8.1 A required response member

Every 2xx response from every readiness, risk-flag, explanation, and status-summary operation carries a required, non-nullable `advisory` object as a **top-level member of the body**:

```json
"advisory": {
  "authoritative": false,
  "character": "predictive-advisory",
  "system_of_record": false,
  "statement": "Predictive advisory readiness view. Not authoritative Navy readiness reporting and not a system of record. Intended to inform action ahead of formal reporting.",
  "methodology_version": "1.4.0",
  "methodology_ref": "/api/v1/fleet-status/methodology/1.4.0",
  "display_requirement": "must_be_surfaced"
}
```

- **Top-level, not nested in metadata, not a `_links` entry, not an envelope wrapper.** The same argument as [06 §5](../architecture/06-demo-decisions-and-assumptions.md) rule 3 makes for the contributor disclosure: a consuming UI reads the fields it renders, and burying the label guarantees it is dropped.
- **Non-nullable and non-omittable.** `fs-advisory-present` (§12.5) asserts its presence on every 200 from every operation in the table of §10.1, by enumerating the OpenAPI response schemas rather than by testing a sample of endpoints.
- `display_requirement: "must_be_surfaced"` is a machine-readable assertion a consuming client can be conformance-tested against. It is the hook that makes "the UI must show this" checkable rather than aspirational.

### 8.2 A response header

`X-FATHOM-Advisory: predictive-advisory; authoritative=false; methodology=1.4.0`

on every response from this service, including problem-details responses. Set by service-local middleware registered after the classification middleware, so the fixed order of [09 §5](09-monorepo-and-conventions.md) is preserved. Header **and** body, because a proxy, a BFF view-model composition `[04 §11]`, or a client SDK may drop either one, and the two failure modes are independent.

### 8.3 Terminology lint — `FS-TERM-001`

Following the precedent of [10 §4.4](10-shared-packages.md)'s `FTH005`, which rejects the retired `FOUO` markings as string literals anywhere in the monorepo, a forbidden-term rule runs over `services/fleet-status/**`, its OpenAPI description strings, and any `apps/web` module importing its types. The list is **proposed** `[ESTABLISHED HERE]` and must be validated by program subject-matter experts — [04 §5](../architecture/04-subapplication-architectures.md)'s Phase 3 question 2 asks *"whether rollups must align to specific Navy readiness constructs and reporting categories, and the terminology constraints that follow"*. Logged as **OD-8**.

| Forbidden in an identifier, response field, enum value, or description | Because |
|---|---|
| `readiness_status`, `readiness_state`, `readiness_rating` | Reads as a reported status. Use `advisory_readiness_score` |
| Authoritative readiness-reporting category names and letter/number rating ladders | These are the vocabulary of the authoritative systems this service must not be mistaken for. A field named after a report line item will be pasted into that report |
| `mission_capable`, `fully_mission_capable`, `partially_mission_capable`, and their abbreviations, as computed field names | Same. These are formal determinations made elsewhere |
| `casrep` **as an assertion that one exists** | Permitted only in the compound forms `casrep_risk`, `casrep_risk.raised`, `casrep_risk.cleared`, and `predicted_casualty_category_candidate`. A field named `casrep` asserts a casualty report exists; this service predicts risk of one |
| `certified`, `verified`, `official`, `authoritative`, `system_of_record` as positive assertions about our output | Direct contradiction of the key decision. Permitted only in the negated forms of §8.1 |
| `compliant`, `reportable` | Imply the figure satisfies an external reporting obligation |

The rule is a denylist on identifiers and on string literals in OpenAPI descriptions, with an allowlist of the sanctioned compounds. It fails the build, per [09 §6](09-monorepo-and-conventions.md)'s "no soft-fail job".

### 8.4 The specification itself

- `info.description` in `services/fleet-status/openapi.json` opens with the §8.1 statement verbatim.
- Every readiness, risk-flag, explanation, and status-summary operation's `description` opens with it too. An agent tool manifest is generated from OpenAPI `[03 §8.2]`, so the operation description is what an LLM-backed agent sees — and the Readiness Narrative agent's whole job is to put this figure into prose. An agent that narrates a readiness score as authoritative is the highest-likelihood realization of the risk this section exists to prevent.
- Operation extension `x-fathom-advisory: true` on every such operation. This is an **additional** extension beyond the two [03 §4.1](../architecture/03-integration-contracts.md) requires; it does not replace or modify `x-substitution` or `x-side-effects` `[ESTABLISHED HERE]`.
- `GET /methodology/{version}` is `x-substitution: required`. A substituting implementation that serves scores without serving its methodology cannot honour the advisory framing, since "advisory" is only meaningful if the advice's basis is inspectable.

### 8.5 Field naming, positively stated

| Concept | Field | Not |
|---|---|---|
| The score | `advisory_readiness_score` | `readiness_score`, `readiness`, `score`, `rating` |
| The complement | `degradation` | `capability_loss`, `downgrade` |
| The flag | `risk_flag`, severity `casualty_risk_*` | `casrep`, `casualty` |
| The predicted category | `predicted_casualty_category_candidate` | `casrep_category`, `casualty_category` |
| The contributor | `degradation_contributor` | `deficiency`, `discrepancy`, `finding` — each is a term of art elsewhere |

---

## 9. Events

### 9.1 Published

Topics per [09 §7.1](09-monorepo-and-conventions.md)'s mechanical derivation: `fathom.fleet-status.<aggregate>.v1`, aggregate token `snake_case`. Consumer group `fathom-fleet-status-v1`.

| Event | Topic | Payload | Consumers `[03 §6]` |
|---|---|---|---|
| `readiness.recomputed` | `fathom.fleet-status.readiness.v1` | scope, score components, contributing degradations, classification union | `notification` |
| `casrep_risk.raised` | `fathom.fleet-status.casrep_risk.v1` | installed item, predicted category **candidate**, horizon, evidence references, severity, `reference_class`, `uncalibrated`, `methodology_version`, driving statistic, thresholds | `notification`, `maintenance`, `supply` |
| `casrep_risk.cleared` | `fathom.fleet-status.casrep_risk.v1` | installed item, cause of clearance, `methodology_version` | `notification`, `maintenance` |

Four rules:

- **Every publication goes through the transactional outbox**, in the same transaction as the state change `[03 §5.2, §15 obligation 11]`, using `packages/py-sync` per [11](11-outbox-sync-library.md). Obligation 11 is explicit that this binds *"including sub-applications with no current edge profile."* Fleet Status has none; the obligation applies regardless.
- **Partition keys.** `casrep_risk.*` on `asset_id` `[03 §5.1]`. `readiness.recomputed` on `asset_id` for asset- and system-scoped assessments. For **fleet scope**, [03 §5.4](../architecture/03-integration-contracts.md) requires *no* subject identifier — *"fleet is the one singleton scope covering the entire fleet"* — so there is no scope identifier to partition on. A fixed literal key `"fleet"` is used, yielding a single partition and therefore total ordering for fleet-scoped events, which is correct for a singleton. Logged as **OD-2**.
- **`readiness.recomputed` carries the classification union, so it is published at that union.** [03 §6](../architecture/03-integration-contracts.md) puts *"classification union"* in the payload, and [03 §5.1](../architecture/03-integration-contracts.md) requires *"a topic carries exactly one classification."* Consequence in production: the event is published to the topic accredited at the union, and **the default (low-side) view is API-only** — computed per request under the requester's ABAC attributes, never published as an event. Notification therefore cannot populate a low-side notification body from the event payload; it must re-read `GET /readiness` under each recipient's authority. For the single-level demonstration every topic is at U and this is moot, which is exactly why it must be written down now. Logged as **OD-9**.
- **`x-side-effects` and the proposal convention.** Fleet Status **accepts no agent proposals** and publishes **no** `fathom.fleet-status.proposal.v1` topic. [03 §6](../architecture/03-integration-contracts.md)'s proposal convention binds *"every sub-application accepting agent proposals"*, and this one does not: it owns no observed fact for an agent to propose a change to, and its two owned assertions are outputs of a versioned methodology rather than adjudicable records. The Readiness Narrative agent consumes this service read-only. Every operation is therefore `x-side-effects: none` except the internal methodology and recomputation operations, which are `state-changing` and **not** `x-agent-eligible` `[03 §4.1, §8.1]`.

### 9.2 Consumed — all 21, enumerated

[04 §5](../architecture/04-subapplication-architectures.md): *"This is the largest consumed set in the system, which follows from Fleet Status being derived-data only. Rev 1 expressed it as prose categories, which made it impossible to determine whether a declared dependency in document 03 §6 was satisfied"* — finding **C37**.

Enumerated exactly as [03 §6](../architecture/03-integration-contracts.md) lists `fleet-status` as a consumer. This list has been reconciled row by row against [03 §6](../architecture/03-integration-contracts.md) and against [04 §5](../architecture/04-subapplication-architectures.md), and **all three agree at 21 events**. Enumerated, never wildcarded — [04 §4](../architecture/04-subapplication-architectures.md) records why: *"Rev 1 subscribed to 'all Registry events, all Telemetry events,' which cannot be conformance-tested and silently auto-subscribes to any future event a producer adds"* `[C38]`.

| # | Producer | Event | Topic |
|---|---|---|---|
| 1 | `registry` | `asset.registered` | `fathom.registry.asset.v1` |
| 2 | `registry` | `asset.status_changed` | `fathom.registry.asset.v1` |
| 3 | `registry` | `configuration.baseline_changed` | `fathom.registry.configuration_baseline.v1` |
| 4 | `telemetry` | `health_indicator.computed` | `fathom.telemetry.health_indicator.v1` |
| 5 | `telemetry` | `anomaly.detected` | `fathom.telemetry.anomaly.v1` |
| 6 | `pdm` | `prediction.updated` | `fathom.pdm.prediction.v1` |
| 7 | `pdm` | `prediction.invalidated` | `fathom.pdm.prediction.v1` |
| 8 | `pdm` | `criticality_tier.assigned` | `fathom.pdm.criticality_tier.v1` |
| 9 | `pdm` | `model_binding.activated` | `fathom.pdm.model_binding.v1` |
| 10 | `maintenance` | `work_candidate.created` | `fathom.maintenance.work_candidate.v1` |
| 11 | `maintenance` | `work_order.opened` | `fathom.maintenance.work_order.v1` |
| 12 | `maintenance` | `deferral.recorded` | `fathom.maintenance.deferral.v1` |
| 13 | `maintenance` | `work_package.proposed` | `fathom.maintenance.work_package.v1` |
| 14 | `maintenance` | `work_package.approved` | `fathom.maintenance.work_package.v1` |
| 15 | `supply` | `part_availability.changed` | `fathom.supply.part_availability.v1` |
| 16 | `supply` | `requisition.status_changed` | `fathom.supply.requisition.v1` |
| 17 | `supply` | `allowance_shortfall.detected` | `fathom.supply.allowance_shortfall.v1` |
| 18 | `pma` | `mission_review.completed` | `fathom.pma.mission_review.v1` |
| 19 | `failure-intel` | `causal_finding.published` | `fathom.failure-intel.causal_finding.v1` |
| 20 | `design-advisory` | `redesign_candidate.created` | `fathom.design-advisory.redesign_candidate.v1` |
| 21 | `design-advisory` | `redesign_case.published` | `fathom.design-advisory.redesign_case.v1` |

**Explicitly not consumed**, recorded because each is a plausible mistaken addition and two of them are load-bearing absences: `installed_item.installed`, `installed_item.removed`, `allowance.updated`, `telemetry.batch_ingested`, `usage_counter.updated`, `usage_counter.reset`, `mission.completed`, **`maintenance_action.recorded`** (§6.5, §7.2 — OD-6), `reservation_set.confirmed`, `reservation_set.released`, `mission_review.opened`, `anomaly_tag.confirmed`, `anomaly_tag.rejected`, `failure_mode.attributed`, `causal_feature_set.updated`, `design_change.projected`.

`services/fleet-status/src/fathom_fleet_status/events/catalog.py` declares `CONSUMES: frozenset[str]` with exactly these 21 and `PUBLISHES: frozenset[str]` with exactly the 3 of §9.1. `tools/check_event_catalog.py` and `tools/check_service_events.py` reconcile it against [03 §6](../architecture/03-integration-contracts.md) and against `helm/values.yaml` in CI job 6 `[09 §6]`. A 22nd subscription cannot be added without the reconciliation failing, which is what closes C37 structurally rather than editorially.

### 9.3 The projector — event to read-model effect

One handler per event type in `EVENT_HANDLERS: dict[str, Handler]`. Every handler is idempotent on `event_id`, records the inbox row and applies state in one transaction `[03 §5.2, §15 obligation 12]`, and **never** records receipt before processing: *"a crash between the two permanently suppresses the event, and applied to `configuration.baseline_changed` it silently prevents prediction invalidation"* `[D2]`.

Column meanings: **Contributor** = does this event create, update, or delete a `DegradationContributor`? **Recompute** = does it trigger a `ReadinessAssessment` recomputation, and at which scopes?

| # | Event | Read-model effect | Contributor | Recompute |
|---|---|---|---|---|
| 1 | `asset.registered` | Insert `rm_asset`; create scope rows for asset and its systems | No — context only | Yes: initial assessment, typically `no_contributors` (§3.9) |
| 2 | `asset.status_changed` | Update `rm_asset` operational status, OFRP phase, deployment state | No — context. **Not a degradation**: an asset in a maintenance phase is not "degraded", and scoring it as such would make the OFRP cycle read as fleet decline | Yes: the transform may be OFRP-phase-conditioned; never another contributor's weight (V3) |
| 3 | `configuration.baseline_changed` | Update `rm_configuration_tree`; advance `baseline_epoch`; **apply the antecedent rule (§9.4)**; retire contributors for items no longer in the baseline; mark surviving prediction contributors `stale` | Delete (item left baseline) + `configuration_invalidation` insert | Yes, asset → fleet. Also drives `item_left_baseline` clears (§6.5) |
| 4 | `health_indicator.computed` | Upsert `rm_indicator` keyed on (installed item, indicator, definition version) | Upsert `health_indicator`, `basis = observed_indicator` | Yes, item → fleet |
| 5 | `anomaly.detected` | Insert `rm_indicator` anomaly row with detector version, window, channels, `origin` | Upsert `observed_anomaly` | Yes, item → fleet |
| 6 | `prediction.updated` | Dereference the run artifact via PdM's API — the event *"references the run artifact rather than inline result sets"* `[D27]` — and upsert `rm_prediction` | Upsert `prediction`; derive $d_i$ per §4.2; **null `p_failure` → `population_hazard`, never zero** | Yes, item → fleet. Also drives flag evaluation (§6) |
| 7 | `prediction.invalidated` | Mark `rm_prediction` invalidated with cause and `baseline_epoch` | Update contributor `stale = true`; insert `configuration_invalidation` | Yes. Flags → `evidence_invalidated`, **never cleared** (§6.4) |
| 8 | `criticality_tier.assigned` | Upsert `rm_criticality`: tier, contributing factors, transition annotation | Update contributor **`weight`** (the weight source) with `weight_revision_reason = tier_reassignment` | Yes, with `delta_attribution.from_weight_change` populated so the shift is not read as degradation `[D36]` |
| 9 | `model_binding.activated` | Insert `rm_context` binding row with approval reference | No — transparency only, zero weight, not a contributor (§2.3) | No. Annotates subsequent assessments |
| 10 | `work_candidate.created` | Upsert `rm_maintenance` candidate with driver and estimated scope | Upsert `planned_mitigation` | Yes: a planned mitigation modulates the *projected* trajectory, never the current degradation |
| 11 | `work_order.opened` | Upsert `rm_maintenance` work order with planned window | Upsert `planned_mitigation` | Yes. Moves the flag to `mitigation_in_progress` — **not a clear** (§6.5) |
| 12 | `deferral.recorded` | Upsert `rm_maintenance` deferral with `deferral_reason_class`, revised window, risk accepted | Upsert `deferral`, `basis = accepted_risk`; **branch on `deferral_reason_class`** — the disagreement class annotates rather than contributes (§5.2, D34) | Yes, item → fleet |
| 13 | `work_package.proposed` | Upsert `rm_maintenance` package with constraint-satisfaction summary and reservation-set reference | Update `planned_mitigation` projected-window | Yes (projection only) |
| 14 | `work_package.approved` | Upsert committed work set — *"published only after reservation confirmation"* `[D6]`, so this is the first trustworthy commitment | Update `planned_mitigation` to committed | Yes (projection only) |
| 15 | `part_availability.changed` | Upsert `rm_supply` on (NIIN, location) with on-hand, due-in, `lead_time`, `condition_code`, interchangeable group | Upsert `requisition_delay` where a mitigation depends on the NIIN. **Interchangeable group is honoured**: an available substitute means no shortfall `[D24]` | Yes, item → fleet |
| 16 | `requisition.status_changed` | Upsert `rm_supply` requisition with status and projected availability | Upsert `requisition_delay` | Yes |
| 17 | `allowance_shortfall.detected` | Upsert `rm_supply` shortfall with allowance vs on-hand and driver | Upsert `parts_shortfall` — one of the four terminal kinds [04 §5](../architecture/04-subapplication-architectures.md) names | Yes, item → fleet |
| 18 | `mission_review.completed` | Insert `rm_context` review row with tag counts, duration, reviewer, canary outcomes | No — context. Canary outcomes belong to the recall metric `[06 §6]`, not to readiness | No |
| 19 | `causal_finding.published` | Insert `rm_context` adjudicated hypothesis with `strength_band`, affected population, `treatment_handling` | Insert `causal_finding` as a **qualitative annotation**, `degradation = null`, weight excluded. Never a quantitative contribution (§5.2) | No. Annotates the prediction contributors it explains |
| 20 | `redesign_candidate.created` | Insert `rm_context` candidate with driver evidence and preliminary priority | Insert `redesign_signal`, qualitative | No |
| 21 | `redesign_case.published` | Insert `rm_context` case with dependency impact and recommendation | Update `redesign_signal`, qualitative | No |

Two projector-wide rules:

- **Recomputation is debounced, not per-event.** ~25,000 predictions per scoring run `[06 §7]` would trigger ~25,000 fleet recomputations if each event recomputed eagerly. Handlers mark scopes dirty; a recomputation worker coalesces per `(scope, subject)` on a short interval, computes bottom-up so each level's children are current, and emits **one** `readiness.recomputed` per scope per coalescing window. `delta_attribution` (§3.11) is computed against the previous published assessment, not against the previous intermediate state, so a coalesced batch reports one honest delta rather than a sequence of partial ones.
- **A contributor's row records the event that produced it.** `source_event_id`, `source_event_type`, `source_producer`, `source_producer_node`, `source_monotonic_seq`. This is obligation 9 `[03 §15]` discharged at row level, and it is what makes §5.3's traversal a provenance walk rather than a join.

### 9.4 The antecedent rule and epoch fencing

[03 §5.4](../architecture/03-integration-contracts.md): *"A consumer that receives an event with an epoch ahead of its own configuration read model **must block that event until the antecedent configuration event is applied**, resolved via `causation_id` or by reading `changed_since` from the Registry."*

Fleet Status implements this in a shared gate ahead of every handler:

- Any event carrying `baseline_epoch` greater than `rm_configuration_tree`'s epoch for that asset is **parked**, not dropped and not applied. Resolution is attempted first via `causation_id`, then by a Registry `changed_since` read.
- Parked events are visible: `fathom_readmodel_lag_seconds` and a parked-event gauge, both on `/metrics` and reflected in `/readyz` `[03 §5.2]`.
- A prediction contributor is never derived from a `FailurePrediction` whose `baseline_epoch` is behind `rm_configuration_tree` — *"a prediction computed against a superseded baseline is invalid, and consumers must be able to detect that without inference"* `[03 §3.3 rule 5]`. Such a contributor is marked `stale = true` and rendered as stale; `computed_at` is never used to make this determination, since *"a stale result looks fresher by `computed_at`"* `[D3]`.
- `readiness_assessment.baseline_epoch_low_water` records the minimum epoch across contributing assets, so a consumer can fence on it too.

### 9.5 Staleness bounds and refusal

Obligation 14 `[03 §15]`: *"Exposes read-model lag, and refuses freshness-dependent computation outside its declared staleness bound."* [03 §5.2](../architecture/03-integration-contracts.md): *"Any computation with a correctness dependency on freshness declares a staleness bound and refuses to run outside it"* `[D6]`.

Declared bounds, per source, in `methodology_version.staleness_bounds` `[ESTABLISHED HERE]`, tunable:

| Source | Soft bound → `freshness: degraded` | Hard bound → refuse |
|---|---|---|
| `pdm` predictions | 6 h | 48 h |
| `registry` configuration | 15 min | 2 h |
| `telemetry` indicators and anomalies | 2 h | 24 h |
| `supply` availability and requisitions | 12 h | 72 h |
| `maintenance` deferrals and work | 6 h | 48 h |

Behaviour: past the soft bound, affected contributors are marked `stale`, the assessment carries `freshness: degraded` with `staleness_detail` naming the lagging source, and computation proceeds. Past the hard bound, **no new assessment is published**; the last good assessment is served with its age and `freshness: refused`, and `fathom_staleness_refusals_total{service="fleet-status",computation="readiness_rollup"}` increments `[09 §5]`. Configuration has the tightest bound because a stale configuration read model makes the antecedent rule of §9.4 unenforceable, which corrupts everything downstream of it.

Refusing is the correct behaviour and it is worth stating why, because it looks like an outage: a readiness score computed from a 3-day-old prediction set is not a slightly stale score. It is a confident assertion about a fleet the service can no longer see, and it is the one output an operator will act on without checking.

### 9.6 Rebuild

*"CQRS read model built entirely from events... The read model is rebuildable from event history, which is also what makes the retention guarantees in document 03 §5.1 load-bearing"* `[04 §5]`. Reconciled with [03 §5.1](../architecture/03-integration-contracts.md)'s stronger rule — *"the event bus is not a rebuild source. Read-model rebuild uses the `changed_since` reads of §4"* `[D5]` — the operative requirement is:

- **Steady state** is event-driven (§9.3). **Rebuild** is from each producer's `changed_since` read, never from the bus (V2). A rebuild that replayed the bus would both exceed retention and re-fire the flag state machine, publishing a storm of `casrep_risk.raised` for flags already raised — the live-side-effect failure `[D30]` warns about.
- Rebuild is deterministic: replaying the same `changed_since` snapshot under the same `methodology_version` reproduces byte-identical assessments and an identical `inputs_digest` (§12.7).
- Historical assessments are **not** recomputed under a later methodology (V5). A rebuild reconstructs each assessment under the methodology version it originally cited.

---

## 10. API surface

Base path `/api/v1/fleet-status/` `[03 §4, 09 §7.1]`. Mechanisms — pagination, `changed_since`, problem details, idempotency, ETag, headers, middleware order — are [09 §5](09-monorepo-and-conventions.md)'s and are not restated.

### 10.1 Operations

| Operation | Purpose | `x-substitution` | `x-side-effects` | `x-agent-eligible` |
|---|---|---|---|---|
| `GET /readiness?scope=&asset_id=&system_id=&tycom_id=&view=&as_of=&changed_since=&limit=&cursor=` | Advisory readiness assessments. `scope` ∈ `asset` \| `system` \| `fleet` \| `tycom` [**AMENDMENT** — was `fleet_grouping`/`grouping_id`, closing OD-2]; `view` ∈ `default` \| `high-side`, default `default` | `required` | `none` | yes |
| `GET /readiness/{assessment_id}` | One assessment with score components and both disclosure blocks. `ETag` per §5.5 | `required` | `none` | yes |
| `GET /readiness/{assessment_id}/explanation?max_depth=&kind=&limit=&cursor=` | The explanation graph decomposition (§5.3) | `required` | `none` | yes |
| `GET /risk-flags?severity=&horizon_days=&asset_id=&installed_item_id=&state=&reference_class=&changed_since=&limit=&cursor=` | Risk flags. `changed_since` because `maintenance` and `supply` project them `[03 §15 obligation 5]` | `required` | `none` | yes |
| `GET /risk-flags/{flag_id}` | One flag with evidence references and hysteresis state | `required` | `none` | yes |
| `GET /risk-flags/{flag_id}/transitions?limit=&cursor=` | The append-only ledger for one flag (§2.5) | `required` | `none` | yes |
| `GET /risk-flags/transitions?changed_since=&limit=&cursor=` | The fleet-wide transition change feed. **The warning-lead-time-coverage ingest path** (§7.4) | `required` | `none` | yes |
| `GET /assets/{id}/status-summary` | The single-asset operator view: score, top contributors by share, open flags, freshness | `required` | `none` | yes |
| `GET /methodology`, `GET /methodology/{version}` | The published scoring methodology (§2.6, §8.4) | `required` | `none` | yes |
| `POST /readiness/recomputations` | Force recomputation of a scope. Bounded, idempotent, rate-limited | `internal` | `state-changing` | no |
| `POST /methodology-versions`, `POST /methodology-versions/{v}/activate` | Methodology authoring and activation. `If-Match` required; dual approval | `internal` | `state-changing` | no |
| `POST /risk-flags/{flag_id}/suppress` | Audited suppression with a named approver (§6.1). `Idempotency-Key` required | `internal` | `state-changing` | no |
| `GET /healthz`, `GET /readyz`, `GET /metrics` | Per [03 §4](../architecture/03-integration-contracts.md) | `internal` | `none` | no |

Naming carve-outs to enumerate in `x-naming-carve-outs` per [09 §5](09-monorepo-and-conventions.md), each with a reason: `/readiness` (a query projection, not a collection of "readinesses"), `/methodology` (a singleton projection over the active version), `/assets/{id}/status-summary` (a named projection, fixed by [04 §5](../architecture/04-subapplication-architectures.md)).

`/assets/{id}` is namespaced under this service's base path, so the `[C25]` collision at a single gateway ingress does not arise.

### 10.2 The `view` parameter, and what it does not do

`view=default` is the [06 §5](../architecture/06-demo-decisions-and-assumptions.md) rule-1 exclusion view; `view=high-side` is rule 2. Three rules:

- **`view` is a request for a computation, not an authorization claim.** `view=high-side` from a requester not cleared to the assessment's `classification_label_full` returns `403` with `urn:fathom:problem:fleet-status:view-not-authorized`. It does **not** silently downgrade to the default view, because a silent downgrade means a caller cannot tell which view they received, and a caller who believes they have the high-side view when they do not is worse off than one who is refused.
- **Every response states which view produced it**, in `contributor_disclosure.view`. Always, including `high-side`.
- **`view` never widens what ABAC permits.** Authorization is evaluated locally against ABAC attributes including classification, caveats, and compartments `[03 §4]`, never delegated to the gateway `[03 §15 obligation 7]`. `view` selects among computations the requester is already entitled to.

### 10.3 Authority

| Actor `[01 §4, 03 §7.2.1]` | May read default view | May read high-side view | May propose | May approve |
|---|---|---|---|---|
| Ship's Force Maintainer (`maintainer`) | Own asset | Per clearance | — (no proposals accepted, §9.1) | — |
| RMC / Availability Planner (`planner`) | Assets in their RMC | Per clearance | — | — |
| Supply role (`supply_officer`) | Assets in scope | Per clearance | — | — |
| TYCOM Readiness Officer (`fleet_authority`) | Fleet and groupings | Per clearance | — | Methodology activation (dual control) |
| Readiness Narrative agent | Per the delegated user's authority `[03 §8.3]` | Per the delegated user's clearance | — | — |
| `notification`, `maintenance`, `supply` (workload identities) | Per workload ABAC attributes | Per workload attributes | — | — |

Methodology activation requires **dual control** `[ESTABLISHED HERE]`, by analogy with [03 §7.2](../architecture/03-integration-contracts.md)'s rule that dual control is mandatory *"at class and fleet scope"*: a methodology change alters every readiness figure in the fleet simultaneously, which is fleet blast radius by any reading. `fleet_authority` plus a second signature.

The agent row matters: an interactive agent carries the user's delegated token `[03 §4, §8.3]`, so **an agent never sees more than its principal**. An accountable-autonomous credential must not be used to read readiness on a user's behalf, because that would let an uncleared user receive high-side content through an agent — clearance laundering, and it defeats §3 entirely.

### 10.4 Problem types

Declared once as an enum in `schemas/problems.py` `[09 §5]`. `type` is a URN.

| `type` | Status | When |
|---|---|---|
| `urn:fathom:problem:fleet-status:view-not-authorized` | 403 | `view=high-side` beyond the requester's clearance (§10.2) |
| `urn:fathom:problem:fleet-status:assessment-not-found` | 404 | No assessment. **Byte-identical in `type`, `title`, and `status` to the response for a scope whose every contributor is restricted, per §5.5** |
| `urn:fathom:problem:fleet-status:staleness-bound-exceeded` | 409 | Hard staleness bound; extension members carry the lagging source and lag (§9.5) |
| `urn:fathom:problem:fleet-status:methodology-frozen` | 409 | Attempt to modify an effective methodology version (§2.6) |
| `urn:fathom:problem:fleet-status:baseline-superseded` | 409 | Recomputation requested against a superseded epoch |
| `urn:fathom:problem:common:version-conflict` | 412 | `If-Match` CAS failure `[09 §5]` |

**No problem `detail` may name a compartment, a restricted contributor, a system, or a count beyond what `contributor_disclosure` already discloses.** `detail` is never used for control flow `[03 §4]`, and here it is also a disclosure surface — an error message is the most commonly overlooked one.

---

## 11. Deployment and boundary

[09 §4.3, §4.4, §6](09-monorepo-and-conventions.md) govern the container, chart, network policy, and pipeline in full: pinned base image digest, nothing installed at container start, non-root UID 65532, read-only root filesystem, all capabilities dropped, migrations as a `pre-upgrade` Helm hook, ten blocking CI jobs. None of it is restated. Only the deltas:

| Delta | Requirement |
|---|---|
| **Datastore** | One PostgreSQL cluster `fathom-fleet-status-pg`, one logical database `[03 §15 obligation 13]`. **No TimescaleDB, no pgvector.** A read model and derived assertions only (V1) |
| **NetworkPolicy egress** | Default-deny plus an explicit allow set of exactly: own Postgres, Redpanda, and the **eight producer APIs** whose `changed_since` reads are the rebuild path — `registry`, `telemetry`, `pdm`, `maintenance`, `supply`, `pma`, `failure-intel`, `design-advisory` — plus the effectiveness-analytics read of §7.6, plus OIDC. `values.networkPolicy.egress` must **equal** the rendered peer set exactly `[09 §4.4.2]`. This is the largest legitimate egress set of any sub-application, which is the deployment-level shadow of the largest consumed-event set; it is enumerated, and a ninth peer is a review failure |
| **No ingress from Domino** | The Readiness Narrative agent reaches this service through the API Gateway, subject to the machine-to-machine authentication dependency `[04 §5, 01 §8.7]`. No direct Domino → service path |
| **Scaling** | Two workloads in one chart: the API deployment scales on request latency against the p95 < 1.5 s budget `[06 §7]`; the projector/recomputation worker scales on consumer lag via a KEDA `ScaledObject` `[09 §4.4]`. They scale independently because a scoring-run burst is a projector event, not an API event |
| **Readiness checks** | The five mandatory checks `[09 §5]` — `database`, `migrations`, `broker`, `read_model_lag`, `outbox_drain` — plus a Fleet-Status-specific `parked_events` check for §9.4's antecedent gate, and `staleness_bounds` reflecting §9.5 |
| **Plane** | Sustainment Plane entirely `[04 §5]` |
| **Substitution** | Not a substitution candidate, but the API is designed for an external presentation layer `[04 §5]`. Every operator-facing operation is `x-substitution: required`, and `GET /methodology/{version}` is required for the reason in §8.4 |

---

## 12. Testing

Four tiers by path, per [09 §4.7](09-monorepo-and-conventions.md): `tests/unit/`, `tests/integration/`, `tests/contract/`, `tests/conformance/`. No pytest markers. Stable kebab test IDs prefixed `fs-`.

### 12.1 Exclusion-stability — the section that matters most

Every test here runs over **one** stored contributor set, evaluated at two clearance levels, so it tests the formula rather than comparing two pipelines (invariant V4).

| Test | Asserts |
|---|---|
| `fs-excl-invariant` | Given one `assessment_id` with contributors including one carrying `compartments: ["TEST-X"]`, evaluated as a cleared principal and an uncleared principal: **(a)** both scores lie in [0, 100]; **(b)** both decompositions' `deduction_points` sum to `100 − score` within 1e-9; **(c)** the low-side `released_weight` values sum to 1.0 within 1e-9; **(d)** the low-side response carries `restricted_contributors_present: true` and `restricted_contributor_count: 1`; **(e)** the low-side `released_label` contains no compartment appearing only on the excluded contributor; **(f)** the excluded contributor's id, `installed_item_id`, `system_id`, `niin`, kind, and `evidence_ref` appear **nowhere** in the low-side response, its headers, its ETag, or any problem body |
| `fs-excl-movement` (**ES-3**) | Mutate the excluded contributor's `degradation` across its full range, in 20 steps. The low-side score, every `released_weight`, every `attribution_share`, the response body bytes, and the `ETag` are **identical at every step**. Not "within tolerance" — identical |
| `fs-excl-scale` (**ES-2**) | Property test (Hypothesis) over random contributor sets, weights, and degradations: $R(V)$ is invariant to adding, removing, or perturbing any contributor not in $V$; and $R(V)$ is unchanged when $\lvert C \rvert$ changes with $V$ fixed |
| `fs-excl-naive-negative` | **A pinning test on the defect.** The naive fixed-weight formula of §3.4 and the naive single-computation formula of §3.5 are implemented in the test module and asserted to **fail** `fs-excl-scale` and `fs-excl-movement` respectively. If a future refactor makes either pass, the test fails — meaning the invariant has been weakened, not that the naive form was fixed. This is the guard against someone "simplifying" §3.2 back into §3.4 |
| `fs-excl-empty` | All contributors restricted → `score: null`, `suppression_reason: "all_contributors_restricted"`, HTTP **200**, `restricted_contributors_present: true`. **Never 100, never 0, never 403** (§3.9) |
| `fs-excl-no-contributors` | $C = \emptyset$ → `score: null`, `suppression_reason: "no_contributors"`, `restricted_contributors_present: false`. Distinguishable from the above |
| `fs-excl-shape` | Low-side and high-side responses have identical key sets at every nesting level; no key present in one and absent in the other (§5.5) |
| `fs-excl-timing` | Over 200 paired requests, response size and latency for a scope with restricted contributors are statistically indistinguishable (two-sample test, declared alpha) from a scope without them at equal **visible** cardinality (§5.5) |
| `fs-excl-error-parity` | The problem response for a fully-restricted scope is byte-identical in `type`, `title`, and `status` to that for a non-existent scope (§10.4) |
| `fs-excl-etag` | The `ETag` is derived from the view hash, not `readiness_assessment.version`: mutating an invisible contributor bumps `version` and leaves the low-side `ETag` unchanged (§5.5) |
| `fs-forbidden-fields` | Schema-level denylist over every response model: no `visible_weight_share`, `total_contributor_count`, `excluded_weight`, `coverage_fraction`, `score_full`, or any `*_of_total` field. Asserted against the generated OpenAPI, so a field cannot be added without failing (§3.8) |
| `fs-no-postfilter` | Static check: every SQL statement referencing `degradation_contributor` in `repositories/` carries the `fn_label_visible` join in the same statement (§5.5) |
| `fs-excl-compose` | Exclusion-stability holds at item, system, asset, and fleet scope simultaneously over one tree, and `restricted_contributors_present` propagates upward as an OR (§3.10) |
| `fs-excl-relabel` | Upgrading a contributor's label mid-series sets `exclusion_set_changed: true` and attributes the score jump to `from_contributor_set_change`, not to degradation (§3.11) |

**These tests run in the single-level unclassified demonstration**, against a synthetic compartment fixture (`compartments: ["TEST-X"]`) present in the reference dataset. That is the entire point: [06 §5](../architecture/06-demo-decisions-and-assumptions.md) settles the aggregation policy now *"because it constrains the readiness scoring methodology and cannot be retrofitted"*, and a policy that is never exercised because the demonstration is single-level is a policy that is not implemented. `fs-excl-*` passing is the evidence that it is.

### 12.2 Null `p_failure`

| Test | Asserts |
|---|---|
| `fs-null-pfailure` | A `FailurePrediction` with `p_failure: null`, `reference_class: class_estimate`, `calibration_population: 17`, `population_hazard_rate: 0.004`, `rul: null` yields a contributor with `basis: population_hazard`, `uncalibrated: true`, `degradation > 0`, and `render_hint: population_band`; and the assessment score is **strictly lower** than the score computed over the same set with that contributor removed |
| `fs-null-not-zero` | The same prediction does **not** yield `degradation == 0`, and the score differs from the score produced by a deliberately-zeroed variant. Includes a mutation test: replacing the `if p_failure is None` branch with a zero coalesce fails the suite |
| `fs-null-lint` | `FS-NULL-001` fires on `p_failure or 0.0`, `p_failure if p_failure else 0`, `float(p_failure or 0)`, and `coalesce(p_failure, 0)` (§4.3) |
| `fs-null-no-rul` | No `rul_p50_days` is synthesized for a non-item reference class; the explanation node renders a band, not a date `[D19]` |
| `fs-null-no-weight-discount` | The contributor's `weight` is identical to the weight the same item would carry with a calibrated prediction. Uncertainty is reported, never multiplied into the weight (§4.2) |
| `fs-null-distinguishable` | The explanation response exposes `basis`, `uncalibrated`, `reference_class`, `calibration_population`, `fallback_level`, `p_failure: null`, `population_hazard_rate`, and `render_hint` on the node (§4.5) |
| `fs-null-share` | `uncalibrated_share` equals $\sum_{i \in V, \text{uncal}} \tilde w_i$, computed over $V$ and not over $C$ (§3.8) |
| `fs-unassessed` | Both `p_failure` and `population_hazard_rate` null → `basis: unassessed`, `degradation: null`, excluded from numerator **and** denominator, declared in `score_integrity.unassessed_contributor_count`, and **not** folded in as 0 (§4.4) |
| `fs-ungated-violation` | A prediction with non-null `p_failure` and `calibration_population < 50` is treated as a producer contract violation: contributor recorded `unassessed`, counter incremented, ungated probability **not** used (§4.6) |
| `fs-null-crossclass` | No code path compares `p_failure` across reference classes; thresholds are looked up per reference class (§6.2). Lint rule `FTH006` (no branching on `tier`) also passes `[10 §4.4]` |

### 12.3 Hysteresis

| Test | Asserts |
|---|---|
| `fs-hyst-oscillation` | Driving the statistic in a sawtooth across the raise threshold, amplitude within the band, for 50 cycles: exactly **one** `casrep_risk.raised` and **zero** `casrep_risk.cleared` on the event tap |
| `fs-hyst-band` | For every severity in every reference class, `clear_threshold == raise_threshold × (1 − 0.30)` to stored precision, and `clear_threshold < raise_threshold` |
| `fs-hyst-dwell-both` | A raise requires **both** the cycle count and the monotonic duration. Satisfying one alone does not raise. Verified in both directions |
| `fs-hyst-monotonic-clock` | With a simulated backward wall-clock step of 3600 s during the dwell window (the STIG `makestep 1 -1` behaviour `[03 §5.4]`), dwell accounting and the resulting transition are unchanged |
| `fs-hyst-dispersion` | Where contributing events carry `sync_quality.dispersion_ms` exceeding the dwell duration, the transition records `dwell_basis: cycles_only` and the duration condition is not evaluated (§6.3) |
| `fs-hyst-invalidation` | `prediction.invalidated` moves the flag to `evidence_invalidated`; the flag stays operator-visible; **no `casrep_risk.cleared` is published**; the dwell timer is frozen, not reset; and dwell resumes on the next valid prediction (§6.4) |
| `fs-hyst-workorder` | `work_order.opened` moves the flag to `mitigation_in_progress` and does **not** clear it (§6.5) |
| `fs-hyst-clear-causes` | Only the three causes of §6.5 can produce `cleared`. `item_left_baseline` is driven from `configuration.baseline_changed`'s changed-item set |
| `fs-hyst-replay` | `replay: true` events advance no dwell timer and raise no flag `[03 §5.3]` |
| `fs-hyst-uncal-ladder` | An uncalibrated contributor cannot reach `casualty_risk_high`; its severities carry the `_population` suffix; its thresholds and dwells are the uncalibrated row (§6.2) |
| `fs-hyst-ledger` | Every state transition appends exactly one `risk_flag_transition` row with the full clock block; the table rejects `UPDATE` and `DELETE` (§2.5) |

### 12.4 Decomposability and provenance

| Test | Asserts |
|---|---|
| `fs-decomp-exact` | For every assessment in the reference dataset, at both views: $\sum_i$ `deduction_points` $= 100 -$ `advisory_readiness_score` within 1e-9, and $\sum_i$ `attribution_share` $= 1$ within 1e-9 (**ES-4**) |
| `fs-decomp-terminal` | Every contributor resolves to one of the kinds of §5.2, and the four kinds [04 §5](../architecture/04-subapplication-architectures.md) names — prediction, casualty, deferral, parts shortfall — are each exercised by the reference dataset |
| `fs-decomp-evidence` | Every `evidence_ref` resolves against a live producer instance (integration tier), returning 200 |
| `fs-decomp-inherited` | `inherited_from[]` is walkable: each reference resolves to a retrievable label and the chain terminates at a `derived_from` authority reference. Depth-limited, cycle-detecting (§5.4) |
| `fs-decomp-released-label` | The released label is `union` over $V$, not over $C$, and `ClassificationLabel.union` from `packages/canonical-schemas` is used — no local reimplementation (§5.4) |
| `fs-decomp-persisted` | The explanation graph is written in the same transaction as the assessment; a fault injected between the two leaves neither (§5.1) |
| `fs-decomp-qualitative` | `causal_finding` and `redesign_signal` nodes carry `degradation: null` and contribute zero to the aggregate (§5.2) |
| `fs-delta-sums` | `delta_attribution`'s four components sum to `delta`, and a `criticality_tier.assigned`-driven weight change is attributed to `from_weight_change` with `weight_revision_reason: tier_reassignment` (§3.11, D36) |
| `fs-latency` | p95 < 1.5 s for fleet and asset views, p95 < 4 s for explanation decomposition, at the [06 §7](../architecture/06-demo-decisions-and-assumptions.md) capacity envelope |

### 12.5 Advisory framing

| Test | Asserts |
|---|---|
| `fs-advisory-present` | Enumerating the generated OpenAPI: every 2xx response schema for every operation in §10.1's public rows contains a required, non-nullable top-level `advisory` object with `authoritative: false` |
| `fs-advisory-header` | `X-FATHOM-Advisory` is present on every response including problem responses |
| `fs-advisory-descriptions` | `info.description` and every public operation `description` open with the §8.1 statement; every such operation carries `x-fathom-advisory: true` |
| `fs-term` | `FS-TERM-001` (§8.3) passes over `services/fleet-status/**`, the generated OpenAPI descriptions, and any `apps/web` module importing these types; and fires on each forbidden term in a fixture |
| `fs-disclosure-present` | `contributor_disclosure` and `score_integrity` are required top-level members of every readiness, explanation, and status-summary 200 response, in **every** view, and on **every page** of a paginated explanation (§3.7, §4.4, §5.3) |

### 12.6 Events and the projector

| Test | Asserts |
|---|---|
| `fs-events-21` | `events/catalog.py`'s `CONSUMES` equals exactly the 21 event types of §9.2 and `PUBLISHES` exactly the 3 of §9.1; reconciled against [03 §6](../architecture/03-integration-contracts.md) and `helm/values.yaml` by `tools/check_event_catalog.py` and `tools/check_service_events.py` `[09 §6 job 6]`. **No wildcard subscription exists** `[C38]` |
| `fs-proj-<n>` (21 tests) | One test per row of §9.3, asserting the stated read-model effect, contributor effect, and recomputation scope |
| `fs-proj-idempotent` | Redelivering every event type produces no duplicate contributor row and no duplicate published event; idempotency is on `event_id` `[03 §5.2]` |
| `fs-proj-node` | Two events with identical `(producer, monotonic_seq)` but different `producer_node` are both applied — the `[03 §5.4]` collision the field exists to prevent |
| `fs-proj-inbox-atomic` | Inbox row and state change commit together; a fault between them leaves the event redeliverable. **Receipt is never recorded before processing** `[D2]` |
| `fs-proj-epoch-block` | An event whose `baseline_epoch` exceeds the configuration read model's is parked, not dropped and not applied, and resolves via `causation_id` or a Registry `changed_since` read (§9.4) |
| `fs-proj-debounce` | A 25,000-prediction scoring run yields one `readiness.recomputed` per scope per coalescing window, with `delta_attribution` computed against the last **published** assessment (§9.3) |
| `fs-outbox` | Every published event passes through the outbox in the state-change transaction; fault injection between commit and relay loses nothing `[03 §15 obligations 2, 11]` |
| `fs-partition-fleet` | Fleet-scoped `readiness.recomputed` uses the fixed `"fleet"` partition key and carries no subject identifier `[03 §5.4]` (§9.1, OD-2) |
| `fs-no-proposals` | No `fathom.fleet-status.proposal.v1` topic is registered and no operation is `x-agent-eligible` with `x-side-effects: state-changing` (§9.1) |

### 12.7 Rebuild, staleness, and consumer-driven contributions

| Test | Asserts |
|---|---|
| `fs-rebuild-changed-since` | A full read-model rebuild uses only producers' `changed_since` reads. **The bus is not consulted** — asserted by denying the broker during rebuild `[D5]` |
| `fs-rebuild-deterministic` | Rebuild reproduces byte-identical assessments and `inputs_digest` under the same `methodology_version`; and reconstructs historical assessments under the version each originally cited, not the current one (V5) |
| `fs-rebuild-no-side-effects` | Rebuild publishes no `casrep_risk.*` and raises no operator-visible alert `[D30]` |
| `fs-stale-degraded` / `fs-stale-refuse` | Soft bound → `freshness: degraded` with `staleness_detail`; hard bound → no new assessment, last good served with its age, `fathom_staleness_refusals_total` incremented (§9.5) |
| `fs-lag-observable` | `fathom_readmodel_lag_seconds{service="fleet-status",event_type=…}` is exported per consumed event type and reflected in `/readyz` `[03 §5.2]` |

**Consumer-driven contract tests Fleet Status contributes.** Per [09 §4.7](09-monorepo-and-conventions.md), a consumer's expectations live in the **producer's** conformance suite at `packages/contracts/conformance/<producer>/consumers/fleet-status/`. Being the largest consumer in the system, this service owes the largest set — one directory per producer, eight in all, covering all 21 events:

| Producer suite | Fleet Status asserts |
|---|---|
| `registry/consumers/fleet-status/` | `configuration.baseline_changed` carries the changed installed-item set and a monotonically increasing `baseline_epoch`; `asset.status_changed` carries OFRP phase |
| `telemetry/consumers/fleet-status/` | `health_indicator.computed` carries the definition version and definition-time; `anomaly.detected` carries detector version, window, channels, and `origin` |
| `pdm/consumers/fleet-status/` | **`prediction.updated`'s referenced run artifact contains `FailurePrediction` records with nullable `p_failure`**, `reference_class` forced to `class_estimate` below the gate, `population_hazard_rate` present there, and `rul` null there (§4.6). Also: `criticality_tier.assigned` carries the transition annotation `[D36]` |
| `maintenance/consumers/fleet-status/` | `deferral.recorded` carries `deferral_reason_class` from the four-value vocabulary `[D34]`; `work_package.approved` is published only after reservation confirmation `[D6]` |
| `supply/consumers/fleet-status/` | `part_availability.changed` carries `lead_time`, `condition_code`, and the interchangeable group `[D24]` |
| `pma/consumers/fleet-status/` | `mission_review.completed` carries tag counts and canary outcomes |
| `failure-intel/consumers/fleet-status/` | `causal_finding.published` carries `strength_band` and `treatment_handling` |
| `design-advisory/consumers/fleet-status/` | `redesign_candidate.created` and `redesign_case.published` carry the affected population |

A shared conformance test is never edited, skipped, xfailed, or subclassed here; if one is wrong it is fixed in `packages/contracts` for everyone `[09 §4.7]`.

### 12.8 Platform obligations

The contract obligations of [03 §15](../architecture/03-integration-contracts.md) and the conformance suite at `packages/contracts/conformance/fleet-status/` are the real gate; the tests above are additive to it, not a substitute. Coverage floor 80 % on `services/` and `repositories/` `[09 §4.7]`. Obligations 1–10 and 11–16 are exercised by the shared suite; §12.1–§12.7 cover what the shared suite cannot know about, which is this service's methodology.

---

## 13. Explicit DO-NOT list

Each entry is a prohibition with its authority. Every one is a shortcut someone will propose under schedule pressure — and the first six are shortcuts that look like *good engineering*, which is why they are enumerated rather than implied.

| # | Do not | Why, and authority |
|---|---|---|
| **1** | **Do not let a rollup's value or scale depend on a contributor the viewer cannot see.** Not through a fixed weight denominator, not through a rank, not through a top-$k$, not through a percentile, not through a count of "total systems", not through a set-normalized transform | [03 §7.3](../architecture/03-integration-contracts.md) `[D13]`: ***"Aggregation is a classification event.** A rollup whose value moves when a compartmented item degrades discloses that item's existence."* [05 D13](../architecture/05-architecture-review-findings.md): *"a readiness rollup that moves when a compartmented fitting degrades leaks its existence, and the explanation graph hands over the pointer."* Enforced: `fs-excl-movement`, `fs-excl-scale`, `fs-excl-naive-negative` (§12.1) |
| **2** | **Do not publish any field that is a function of the excluded set.** No `visible_weight_share`, no `total_contributor_count`, no `excluded_weight`, no `coverage_fraction`, no `score_full`, no `*_of_total`. Not "for transparency", not "for debugging", not behind a feature flag | [06 §5](../architecture/06-demo-decisions-and-assumptions.md) rule 1: a boolean and a count, *"never a description, a system, or a **magnitude**."* Every such field is the magnitude with a friendly name (§3.4, §3.8). Enforced: `fs-forbidden-fields` |
| **3** | **Do not silently renormalize.** A low-side rollup never presents itself as complete. `contributor_disclosure` is a required top-level body member in every view, on every page | [06 §5](../architecture/06-demo-decisions-and-assumptions.md) rule 3: *"No silent substitution... The boolean is displayed, not buried in metadata."* §3.7 explains why the *coherence* of the renormalized formula makes this more necessary, not less. Enforced: `fs-disclosure-present` |
| **4** | **Do not return 100, or 0, when every contributor is restricted.** Return `score: null` with `suppression_reason` | §3.9. A fully-compartmented, possibly-failed asset presented as perfectly ready is the worst available output, and it is what a naive `sum/count` guard produces. Enforced: `fs-excl-empty` |
| **5** | **Do not post-filter the explanation graph, and do not derive the restricted count from filtered rows.** Enforce clearance in the join; read the count from the write-time counter | [03 §7.3](../architecture/03-integration-contracts.md): the vector store *"enforces at query time rather than post-filtering, **because post-filtering leaks the existence of records**."* [04 §11](../architecture/04-subapplication-architectures.md) repeats it. Enforced: `fs-no-postfilter`, `fs-excl-timing`, `fs-excl-error-parity` |
| **6** | **Do not derive the `ETag` from `readiness_assessment.version`.** Derive it from the released view's hash | §5.5. `version` increments when an *invisible* contributor changes; a changing ETag on an unchanged body is a change notification, and it defeats ES-3 through HTTP caching after the formula got it right. Enforced: `fs-excl-etag` |
| **7** | **Do not treat a null `p_failure` as zero risk.** Not `p_failure or 0.0`, not `coalesce(p_failure, 0)`, not "the default is fine because it's usually populated" | [03 §7.1](../architecture/03-integration-contracts.md): *"A consumer that treats a missing `p_failure` as zero, rather than as 'uncalibrated,' reintroduces the comparability defect this field exists to prevent."* ~97 % of demonstration items are uncalibrated `[06 §7]`, so this is not an edge case — it is the normal path. Enforced: `FS-NULL-001`, `fs-null-not-zero`, `fs-null-lint` (§12.2) |
| **8** | **Do not discount an uncalibrated contributor's weight to reflect uncertainty** | §4.2. With ~97 % of items uncalibrated, a weight discount is a systematic invisible suppression of the long tail — null-as-zero arrived at respectably — and it violates V3. Report uncertainty (`uncalibrated_share`, `fallback_level`, `render_hint`); never multiply it into the weight. Enforced: `fs-null-no-weight-discount` |
| **9** | **Do not compare `p_failure` across reference classes, and do not use one threshold ladder for calibrated and uncalibrated flags** | [03 §7.1](../architecture/03-integration-contracts.md) `[D7]`: *"Consumers do not compare `p_failure` across reference classes... They may, and must, branch on `reference_class`."* A shared threshold table re-creates the defect in §6.2 instead of in the probability. Enforced: `fs-null-crossclass`, `fs-hyst-uncal-ladder` |
| **10** | **Do not synthesize a remaining-useful-life figure for a non-item reference class** | [03 §7.1](../architecture/03-integration-contracts.md) `[D19]`: *"a memoryless population fit cannot produce a per-item residual-life distribution, and rendering one indistinguishably from a tier-3 distribution misleads the operator."* Enforced: `fs-null-no-rul` |
| **11** | **Do not clear a risk flag because its evidence was invalidated.** `prediction.invalidated` → `evidence_invalidated`, flag stays visible, dwell frozen | §6.4. [04 §4](../architecture/04-subapplication-architectures.md): *"Silent staleness after a component replacement is the failure mode most likely to destroy operator trust permanently."* A vanishing flag is worse — active false reassurance, and trivially reachable by changing a nearby component. Enforced: `fs-hyst-invalidation` |
| **12** | **Do not measure dwell on a wall clock, and do not order events by `source_time`** | [03 §5.4](../architecture/03-integration-contracts.md): STIG **V-260520** mandates `makestep 1 -1`, so a backward step is *guaranteed* at reconnection. *"Ordering and deduplication use `(producer, producer_node, monotonic_seq)` or the HLC. Never `source_time`."* Enforced: `fs-hyst-monotonic-clock`, `fs-hyst-dispersion`, `fs-proj-node` |
| **13** | **Do not claim this service owns no data.** It owns `RiskFlag`, `ReadinessAssessment`, `DegradationContributor`, and `MethodologyVersion` as **derived assertions**, and it is accountable for the methodology that produces them | Finding **C35** `[05 §3.2]`: *"Fleet Status disclaims owning any source fact while owning and publishing risk flags."* The corrected [04 §5](../architecture/04-subapplication-architectures.md) wording is *"does not own any **observed** fact... is authoritative for its own methodology and for the `RiskFlag` assertions that methodology produces."* Both halves are load-bearing; asserting the first without the second is C35 reintroduced (§1.1) |
| **14** | **Do not present output as authoritative readiness reporting**, and do not name a field after a formal reporting category or rating ladder | [04 §5](../architecture/04-subapplication-architectures.md): *"It must not present itself as, or be mistaken for, authoritative readiness reporting... this is an **accreditation and acceptance concern rather than a stylistic one**."* Enforced: `FS-TERM-001`, `fs-advisory-present`, `fs-advisory-header`, `fs-advisory-descriptions` (§12.5) |
| **15** | **Do not publish a score without its decomposition**, and do not recompute the explanation at query time | [04 §5](../architecture/04-subapplication-architectures.md): *"A readiness figure that cannot be decomposed into contributing degradations... will be dismissed by operators — correctly. The explanation graph is a primary output, not a diagnostic feature."* Query-time recomputation can disagree with the stored score, which is ES-4 violated in practice and indistinguishable from the D13 leak (§5.1). Enforced: `fs-decomp-exact`, `fs-decomp-persisted` |
| **16** | **Do not write to any datastore you do not own, and do not read a source fact synchronously on a compute path** | [03 §2, §15 obligation 13](../architecture/03-integration-contracts.md) `[D10, C7]`. [04 §5](../architecture/04-subapplication-architectures.md): *"No synchronous fan-out to other sub-applications."* Producer APIs are read for `changed_since` rebuild and for `evidence_ref` dereference — never inside a rollup computation |
| **17** | **Do not rebuild the read model from the event bus** | [03 §5.1](../architecture/03-integration-contracts.md) `[D5]`: *"the event bus is not a rebuild source. Read-model rebuild uses the `changed_since` reads of §4."* Replay would also re-fire the flag state machine and storm `casrep_risk.raised` `[D30]`. Enforced: `fs-rebuild-changed-since`, `fs-rebuild-no-side-effects` |
| **18** | **Do not wildcard a subscription**, and do not add a 22nd consumed event without amending [03 §6](../architecture/03-integration-contracts.md) first | Findings **C37** and **C38**. [04 §4](../architecture/04-subapplication-architectures.md): a wildcard *"cannot be conformance-tested and silently auto-subscribes to any future event a producer adds."* Enforced: `fs-events-21` |
| **19** | **Do not recompute historical assessments under a new methodology version** | V5, §7.4. It silently rewrites the flag and score history that warning lead-time coverage is computed from, which is the program's primary effectiveness metric `[06 §2]`. Enforced: `fs-rebuild-deterministic` |
| **20** | **Do not compute warning lead-time coverage in this service, and never compute it over a viewer-filtered flag set** | §7. Owning both the thresholds and the scoreboard is the metric trap of [06 §6](../architecture/06-demo-decisions-and-assumptions.md); a clearance-filtered coverage figure is a different statistic wearing the metric's name, and it reintroduces §3.5's channel in a metrics panel |
| **21** | **Do not let an agent read readiness under an accountable-autonomous credential on a user's behalf** | [03 §8.3, §4](../architecture/03-integration-contracts.md): interactive agent calls carry the **user's delegated token**. An autonomous credential would let an uncleared user receive high-side content through an agent — clearance laundering, which defeats §3 entirely (§10.3) |
| **22** | **Do not treat an OFRP phase change, a tier reassignment, or a methodology change as degradation** | `[D36]`: *"the transition is annotated so a level shift is not read as fleet degradation."* §2.7, §3.11, §9.3 rows 2 and 8. Enforced: `fs-delta-sums` |
| **23** | **Do not accept a prediction that violates the calibration gate** — a non-null `p_failure` with `calibration_population < 50` | [06 §3](../architecture/06-demo-decisions-and-assumptions.md), [03 §7.1](../architecture/03-integration-contracts.md). Quietly consuming malformed input is how a schema defect survives to production (§4.6). Enforced: `fs-ungated-violation` |

---

## 14. Open decisions

Recorded here rather than resolved with an invented number. Each is a genuine program or architecture judgment; each blocks something specific.

| ID | Decision | Blocks | Current handling | Owner |
|---|---|---|---|---|
| **OD-1** | Whether `restricted_contributor_count` may be disclosed at **narrow** scopes. At system scope, a count of 1 plus the named system is very nearly the *"description... or system"* [06 §5](../architecture/06-demo-decisions-and-assumptions.md) rule 1 prohibits | The release posture of `contributor_disclosure` below asset scope | [06 §5](../architecture/06-demo-decisions-and-assumptions.md) implemented as written — boolean **and** count at every scope. A `count_suppressed` variant is designed but not enabled. [06 §5](../architecture/06-demo-decisions-and-assumptions.md)'s own assumption table anticipates this: *"If exclusion is judged to leak through the count itself, suppress the boolean..."* | Accreditation / security architecture |
| **OD-2** | ~~`scope=tycom` appears in [04 §5]'s API surface but **is not in [03 §5.4]'s scope vocabulary**... so a TYCOM-scoped rollup has nowhere to put its identifier~~ **[CLOSED — amendment, 10-shared-packages.md §4.5.]** `10-shared-packages.md` added `EventScope.TYCOM` (`"tycom"`) and `tycom_id` to the canonical envelope specifically in response to this row. §2.2 above adopts it: `scope` is `asset \| system \| fleet \| tycom`, with `subject_tycom_id` the row's own column. **[AMENDMENT]** This document itself had not adopted the fix its own request produced until now — §2.2, the `GET /readiness` operation, and the partition key for TYCOM-scoped `readiness.recomputed` all now use `tycom`/`tycom_id`, not the `fleet_grouping`/`subject_grouping_id` this row previously proposed and this document had drifted onto independently | Closed | Resolved in `10-shared-packages.md` §4.5; adopted here |
| **OD-3** | The hysteresis threshold and dwell values of §6.2, and *"whether they vary by class or OFRP phase"* | Operator acceptance. Thresholds that are wrong in either direction destroy trust — too low floods, too high misses | Defaults proposed as **tunable placeholders** with `band_ratio = 0.30`, in `methodology_version`, changeable as one row. [04 §5](../architecture/04-subapplication-architectures.md)'s Phase 3 question, verbatim | Program SMEs + `fleet_authority` |
| **OD-4** | `packages/canonical-schemas` must make `FailurePrediction.p_failure` nullable and tighten `_calibration_gate` (§4.6). **OQ-10 of [10 §11](10-shared-packages.md) is resolved in favour of nullability by the corrected [03 §7.1](../architecture/03-integration-contracts.md)**; the schema change has not landed | Every consumer of `FailurePrediction`, not only this one. [10 §12](10-shared-packages.md) lists OQ-10 as a Phase 3 blocker | This service treats a non-null `p_failure` below the gate as a producer contract violation and records the contributor `unassessed` (§4.6) rather than using the ungated probability | Owner of [10](10-shared-packages.md) / `packages/canonical-schemas` |
| **OD-5** | `ClassificationLabel.union` **raises** on an un-orderable `distribution_statement` combination (OQ-16 of [10 §11](10-shared-packages.md)). Fleet Status unions labels on **every** assessment, so it will hit this before any other service | Any CUI-bearing deployment. Not the unclassified demonstration | Not caught, not defaulted. The assessment computation fails with `freshness: refused` and a counter increments (§5.4) | Architecture (document 03 §7.3) + [10](10-shared-packages.md) |
| **OD-6** | Whether `maintenance_action.recorded` should be added to Fleet Status's consumed set in [03 §6](../architecture/03-integration-contracts.md) | Clearing a flag on a **repaired-but-not-replaced** item before the next scoring cycle (§6.5); and any local computation of warning lead-time coverage (§7.2) | Not added. `work_order.opened` gives `mitigation_in_progress`, which is a partial mitigation, and the limitation is stated to operators. **Recommendation: do not add it** — §7 argues the metric belongs elsewhere, and adding the event to satisfy the metric would place the metric here by accident | Architecture (document 03 §6) |
| **OD-7** | Formal assignment of **warning lead-time coverage** and **actionable precision** to an owner. [06 §2](../architecture/06-demo-decisions-and-assumptions.md) defines the primary effectiveness metric and names no owner | The program's primary effectiveness metric being computed at all, by anyone | §7's determination: the cross-cutting effectiveness-analytics path anchored on `audit`, exporting to Domino's Experiment Manager as `anomaly_tag.*` already does `[C19]`. Fleet Status ships the flag-transition ledger and its `changed_since` read regardless (§7.4), so the metric is not blocked on this decision — only its home is | Program + architecture |
| **OD-8** | Validation of the `FS-TERM-001` forbidden-term list (§8.3) against actual Navy readiness-reporting vocabulary, and *"whether rollups must align to specific Navy readiness constructs and reporting categories"* | The accreditation and acceptance argument of [04 §5](../architecture/04-subapplication-architectures.md)'s key decision 1 | Proposed list enforced in CI now, erring toward over-prohibition. Additions are cheap; a term discovered late in an accreditation review is not. [04 §5](../architecture/04-subapplication-architectures.md)'s Phase 3 question, verbatim | Program SMEs |
| **OD-9** | In production, whether `readiness.recomputed` — which carries the classification union `[03 §6]` on a topic carrying exactly one classification `[03 §5.1]` — requires a per-level topic, or whether Notification re-reads the API per recipient | Production notification routing at more than one level. Moot for the single-level demonstration, which is precisely why it is recorded now | The event is published at the union; the default view is **API-only** and never published; Notification must re-read under each recipient's authority (§9.1) | Architecture + `notification` |
| **OD-10** | The aggregation exponent $p = 3$ and the weight function of §3.2 — *"Readiness scoring methodology and its validation against operator judgment, **which is the acceptance risk for this sub-application**"* | Operator acceptance, which [04 §5](../architecture/04-subapplication-architectures.md) names the single acceptance risk here | $p = 3$ as a tunable placeholder. **The exclusion-stability proof of §3.2 holds for every $p \ge 1$**, so $p$ and the weight function can be re-tuned against operator judgment without re-opening the aggregation policy or re-accrediting it. That separation is deliberate | Program SMEs + `fleet_authority` |

---

## 15. Definition of Done

The shared Definition of Done template in [09 §8](09-monorepo-and-conventions.md) applies **in full** and nothing is removed: OpenAPI 3.1 generated from code and committed with no drift, `x-substitution` and `x-side-effects` on every operation, `changed_since` reads over every projected aggregate, AsyncAPI committed, outbox and inbox implemented, one owned logical database, RFC 9457 problem details, idempotency, ETag/`If-Match`, correlation propagation, read-model lag exposed, migrations as a pre-upgrade hook, container and chart checks, the conformance suite green, and all ten blocking CI jobs green.

Fleet-Status-specific gates, all additive and all CI-enforced:

| # | Gate | Verified by |
|---|---|---|
| 1 | **The exclusion-stability invariant holds.** Every `fs-excl-*` test green, including `fs-excl-movement` asserting **bit-identical** low-side output across the full range of an invisible contributor's degradation, and `fs-excl-naive-negative` pinning both naive formulations as failures | §12.1 |
| 2 | **A synthetic compartmented contributor exists in the reference dataset and the exclusion path is exercised**, notwithstanding the single-level unclassified demonstration. A policy that is never executed is not implemented | §12.1, [06 §5](../architecture/06-demo-decisions-and-assumptions.md) |
| 3 | **No response schema can express a function of the excluded set.** `fs-forbidden-fields` green against the generated OpenAPI, not against source | §12.1, §3.8 |
| 4 | **Null `p_failure` is handled as uncalibrated, never as zero.** `fs-null-*` and `fs-unassessed` green; `FS-NULL-001` green; the mutation test proving a zero-coalesce fails the suite | §12.2 |
| 5 | **Every score decomposes exactly.** `fs-decomp-exact` green on every assessment in the reference dataset at both views; every `evidence_ref` resolves; `inherited_from[]` is walkable to a `derived_from` authority | §12.4 |
| 6 | **Hysteresis does not oscillate and invalidation does not clear.** `fs-hyst-oscillation` green over 50 sawtooth cycles; `fs-hyst-invalidation` and `fs-hyst-monotonic-clock` green | §12.3 |
| 7 | **All 21 consumed and 3 published events reconcile** across `events/catalog.py`, `helm/values.yaml`, and [03 §6](../architecture/03-integration-contracts.md), with no wildcard. All 21 `fs-proj-*` tests green. **This closes C37 structurally** | §12.6 |
| 8 | **The advisory framing is unavoidable at the API level.** `fs-advisory-*`, `fs-term`, and `fs-disclosure-present` green; `x-fathom-advisory: true` on every public operation; `info.description` opens with the advisory statement | §12.5 |
| 9 | **Consumer-driven contract tests are contributed to all eight producer suites**, covering all 21 events, and every one passes against the producer's current implementation | §12.7 |
| 10 | **The read model rebuilds deterministically from `changed_since` reads with the broker denied**, reproduces `inputs_digest`, reconstructs historical assessments under their original methodology versions, and publishes no `casrep_risk.*` | §12.7 |
| 11 | **The staleness bounds are declared, exposed, and enforced** — soft bound degrades, hard bound refuses, `fathom_staleness_refusals_total` increments, and `/readyz` reflects lag and parked events | §9.5, §12.7 |
| 12 | **The published methodology is retrievable and complete.** `GET /methodology/{version}` serves the weight function, the exponent, every transform, every threshold, and every hysteresis parameter for the version any assessment cites; frozen versions are immutable | §2.6, §8.4 |
| 13 | **The flag-transition ledger is append-only and has a `changed_since` read**, carrying `methodology_version`, `reference_class`, and `uncalibrated` on every row, so warning lead-time coverage is computable by its owner over the full history | §2.5, §7.4 |
| 14 | **Both halves of the C35 correction appear in the service README and OpenAPI description** — owns no *observed* fact; **is** authoritative for its methodology and its `RiskFlag` assertions | §1.1 |
| 15 | **Every open decision in §14 is either resolved and this document updated, or explicitly accepted as a demonstration-scope risk with a named owner.** **OD-4 is a hard gate**: until `FailurePrediction.p_failure` is nullable in `packages/canonical-schemas`, the contract this service consumes does not match the contract [03 §7.1](../architecture/03-integration-contracts.md) specifies, and gate 4 is passing against a schema that would reject the very payload it is designed to handle. **OD-7 is a program gate**: the primary effectiveness metric has no owner, and this document declines to become one by default | §14 |

