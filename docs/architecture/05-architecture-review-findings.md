# Architecture Review — Findings Register

| | |
|---|---|
| **Status** | Open. Dispositions recorded; remediation in progress |
| **Review date** | 4 August 2026 |
| **Scope reviewed** | Documents 01–04 at the state following the rev-4 tool-surface amendment |
| **Method** | Two independent adversarial review passes: one for internal consistency and verifiable defects, one for design flaws with concrete failure scenarios |
| **Result** | 51 consistency findings (C1–C51), 37 design findings (D1–D37) |
| **Classification** | Internal |

---

## 1. Purpose and how to use this register

This register exists because the volume and severity of findings exceed what can be silently absorbed into revisions. Several findings invalidate decisions already approved at Phase 1 and Phase 2, and eleven require a program decision rather than an editorial fix.

Dispositions are:

| Disposition | Meaning |
|---|---|
| **FIX** | Unambiguous defect. Corrected in the cited document; no decision required |
| **DECIDE** | Requires a program decision before it can be corrected. Enumerated in §4 |
| **PHASE 3** | Genuine gap, correctly deferred to detailed design, but recorded so it is not lost |
| **REJECT** | Reviewed and not accepted, with reasoning stated |

Nothing is closed by acknowledgement. A finding is closed when the cited document changes or a decision in §4 is recorded.

---

## 2. Design findings

Severity as assessed by the reviewer. Findings that change an approved contract are marked ⚠.

### 2.1 Statistical and modeling integrity

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| **D1** ⚠ | HIGH | **Informative censoring.** Prediction-driven preventive replacement censors exactly the items about to fail. Every stated method (Weibull MLE, Cox, calibration) assumes non-informative censoring. Over time observed failures become a biased low-hazard subsample, fitted MTBF rises, `p_failure` decays, and the fleet drifts back to run-to-failure. The calibration monitor *accelerates* this, because a prevented failure reads as over-prediction and the correction pushes probabilities down. Every feedback signal points the wrong way and nothing detects it. Corollary: "predicted CASREPs avoided" is an unmeasurable counterfactual as designed | **DECIDE** §4.1 |
| **D7** ⚠ | HIGH | **Cross-tier comparability is not achievable by calibration.** A tier-0 marginal population rate and a tier-3 item-conditional probability can both be perfectly calibrated in their own reference classes and remain incomparable. The optimizer will systematically starve high-hazard tier-0 items and over-serve tier-3 tails. Separately, `confidence` is overloaded to carry both sharpness and cold-start fallback depth — one scalar cannot carry both and stay orderable. And calibration cells are unidentifiable at demo scale: tier-0 long-tail NIINs at 90 days need 10⁴–10⁵ item-horizons per cell | **DECIDE** §4.2 |
| **D19** ⚠ | HIGH | **Tier-0 cannot produce a meaningful per-item RUL.** Tier 0 is defined as the random-failure population, i.e. Weibull β≈1, i.e. memoryless — so conditional residual life is identical for a new and a nine-year-old item. The UI renders it indistinguishably from a tier-3 distribution. Tier 0 also has no usage counters, so its only clock is calendar time | **DECIDE** §4.2 |
| **D21** ⚠ | HIGH | **Confounded causal loop.** Causal features → predictions → interventions → labels → causal features. Comparative population analysis compares hulls whose intervention histories were assigned by the model under test (confounding by indication), producing oscillation at the retraining period. `maintenance_action.recorded` carries no triggering prediction or policy version, so Failure Intelligence cannot condition on treatment assignment even in principle | **FIX** + **DECIDE** §4.1 |
| **D22** | MED-HIGH | **Definition-time leakage survives point-in-time correctness.** `as_of` constrains data time only. Indicator definitions and channel mappings are explicitly recomputed over history, so a model trained at `as_of=2025-03-01` receives values computed by a definition authored in 2026 by someone who had seen the 2025 failures. The Registry solves this with bitemporality; Condition & Telemetry offers only `as_of`. Also: confirmed anomaly tags carry mission `occurred_at` but were authored with hindsight | **FIX** |
| **D23** | MED-HIGH | **`drivers[]` cannot be produced honestly.** At tier 2, attributions over correlated channels are unidentified and will reorder run to run on unchanged data. At tier 3 the field reads as causal and the Maintainer Copilot renders it as a reason — an unadjudicated back channel delivering causal claims to the deckplate, bypassing the constraint Failure Intelligence is deliberately built around. `evidence_ref` is unsatisfiable for a model-internal attribution | **FIX** |
| **D34** | MED | Deferrals are characterized as evidence the prediction overstated urgency. A deferral is a capacity or operational-tempo decision at least as often as a disagreement with the risk estimate; feeding it back as the latter biases models toward under-prediction | **FIX** |
| **D35** | MED | "Equipment family" partitions model bindings and calibration records but is defined nowhere in the shared kernel | **FIX** |
| **D36** | MED | **Tier migration produces uncaused fleet-wide step changes.** A sensor-installation campaign migrates hundreds of NIINs from tier 0 to tier 2; `p_failure` shifts from population rate to item-conditional estimate — a discontinuous level shift with no physical cause. Hysteresis damps oscillation around a threshold, not a level shift. Also, `criticality_tier.assigned` is not an invalidation trigger, so tier-0 and tier-2 predictions coexist | **FIX** |

### 2.2 Distributed-systems correctness

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| **D2** ⚠ | HIGH | **The inbox protocol silently drops events.** "Record `event_id` before processing" is not at-least-once-safe: a crash between recording and committing the state change makes the event permanently suppressed on redelivery. Applied to `configuration.baseline_changed`, predictions for a replaced item are never invalidated — precisely the outcome document 04 calls the failure most likely to destroy operator trust, introduced by the inbox rule itself | **FIX** |
| **D3** ⚠ | HIGH | **Invalidation races batch scoring; no baseline fencing.** A long scoring job reads baseline B1, the baseline becomes B2 mid-run, and the job's stale result lands after the invalidation and wins — and looks fresher by `computed_at`. Nothing requires PdM to reject a result whose baseline is superseded | **FIX** |
| **D4** ⚠ | HIGH | **Per-asset ordering is per-topic, not global.** Configuration, prediction, and invalidation live on different topics, so a consumer can see a prediction computed under B2 before it has processed B1→B2. `causation_id` exists but no consumer rule uses it and no consumer can block on an unseen antecedent | **FIX** |
| **D5** ⚠ | HIGH | **Read models cannot be rebuilt, and the compaction key is wrong.** Domain events retain 30 days, so a month-14 rebuild has a 13-month hole. PdM's maintenance-history read model is a system of record with no rebuild path. Compaction key = partition key = `asset_id`, so compacting the prediction topic collapses to one event per hull and discards every other item's predictions. No sub-application exposes a snapshot or `changed_since` read | **FIX** |
| **D6** ⚠ | HIGH | **The optimizer has neither a consistent snapshot nor atomic reservation.** It solves over a stale non-atomic mixture, then reserves per-NIIN with no batch, no TTL, no two-phase confirm and no compensating release. 37 of 40 reservations succeed, the 38th fails, orphans persist and 37 spurious availability events degrade every other asset's planning. `lead time` is named as a hard constraint but exists in no Supply event or operation | **FIX** |
| **D20** | HIGH | Scheduling↔Supply has no convergence criterion, and an undeclared PdM↔Failure-Intelligence cycle exists | **FIX** |
| **D27** | MED-HIGH | Fleet-wide batch scoring has no feasible feature-serving or write path at stated scale (~3×10⁶ predictions/run; per-asset prediction events of tens of MB against a default 1 MB broker limit, each also written as an outbox row) | **FIX** |
| **D28** | MED-HIGH | Per-asset partitioning serializes the largest recovery burst; the edge outbox doubles telemetry storage with no pruning rule | **PHASE 3** |
| **D29** | MED-HIGH | **No time-synchronization design**, while last-writer-wins and monotonic-max both depend on trusted clocks across disconnected nodes | **FIX** |
| **D30** | MED-HIGH | **No backfill path**, and replaying history through the event bus fires live side effects (notifications, work candidates, requisitions) | **FIX** |
| **D32** | MED-HIGH | The gateway becomes a stateful all-domain, all-classification consumer to build the unified adjudication queue, contradicting its stated stateless-composition role | **FIX** |
| **D33** | MED | Condition & Telemetry owns two databases, violating one-database-per-service; TimescaleDB is not a CloudNativePG configuration setting | **FIX** |

### 2.3 Edge and DDIL

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| **D8** ⚠ | HIGH | **The edge design excludes capture of the label stream the system depends on.** `MaintenanceAction` lives in the work-order aggregate, which the edge may not commit, and Scheduling is not in the afloat subset. A submarine dark six weeks repairs a pump at sea and cannot record the corrective/preventive determination, findings coding, parts consumed, or failure timing — the four highest-value fields — until weeks later, reconstructed by someone who was not there. Label capture is excluded from exactly the operating mode where the most informative failures occur | **DECIDE** §4.3 |
| **D9** ⚠ | HIGH | **Monotonic-max counters reintroduce the inherited-degradation failure.** The edge cannot mint a new `InstalledItem` identity (configuration is enterprise-authoritative), so it accumulates hours against the *replaced* item. Max-merge then either credits the old item with hours it never ran or gives the new pump its predecessor's age. Also: max-merge is irreversible, so one sensor glitch permanently pins a counter; and real hour meters get replaced and reset, with no representation for a reset | **FIX** |
| **D18** ⚠ | HIGH | **The PMA Pre-Screener cannot run afloat**, and the unsupervised detectors are Domino Jobs, so afloat there is no candidate source at all. Review degrades to the open-ended authoring the design declares unreliable. Submarines — least instrumented, highest consequence — contribute zero confirmed tags | **DECIDE** §4.3 |

### 2.4 Security, classification, and safety

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| **D13** ⚠ | HIGH | **"Consumers enforce" yields system-high or a leak.** Kafka authorization is per topic, so a mixed-classification topic forces every consumer to be accredited at the highest level present and to materialize that content into its own database — system-high by construction, at which point labels are decorative. Worse, the **aggregation channel is unaddressed**: a readiness rollup that moves when a compartmented fitting degrades leaks its existence, and the explanation graph hands over the pointer. No label-inheritance rule for derived values exists | **DECIDE** §4.4 |
| **D14** ⚠ | HIGH | **No prompt-injection threat model.** The retrieval corpus is free text authored by thousands of people, including parties outside the program (vendor manuals, ECPs). A crafted or careless passage produces a requisition proposal with a substituted NIIN, a fluent rationale, and *genuine* citations that satisfy the non-empty-evidence gate mechanically. The propose-don't-commit boundary reduces the entire security posture to the attentiveness of a time-pressured reviewer — which the design elsewhere concedes is the weakest link | **FIX** |
| **D15** ⚠ | HIGH | **No purge path, so a classification spillage is unrecoverable.** Remediation would require deletion from an immutable audit store, nine read models, append-only tag stores, indefinitely compacted topics, every inbox and outbox, the vector index, object-store evidence, and Domino traces. Several stated invariants forbid it. This is an accreditation blocker | **FIX** |
| **D12** ⚠ | HIGH | **Delegated user authority is unsatisfiable for autonomous work.** Three of the design's own paths have no requesting user: the event-triggered PMA Pre-Screener, the scheduled Readiness Narrative and scheduled evaluation, and `POST /what-if` via a Domino Endpoint whose auth is a static token with no per-caller audit. Also unaddressed: consent-gated tokens expiring mid-run when platform maintenance restarts the agent pod | **FIX** |
| **D16** ⚠ | HIGH | **Proposals have no staleness, no claim, and no authority model.** A `work_candidate` sits five weeks, the equipment is replaced, validation happened at creation, and approval executes against a configuration that no longer exists. The queue is eventually consistent with no claim or lease, so two planners approve the same proposal and two work orders result. And one `adjudicated_by` field spans a maintainer's anomaly tag and an `interval_change` that suppresses a preventive task across an entire class — no dual control, no authority-versus-blast-radius check | **FIX** |

### 2.5 Human-in-the-loop viability

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| **D17** ⚠ | HIGH | **Adjudication capacity is unmodeled, and both governing metrics improve while the pipeline dies.** No document contains a single throughput figure. The design's own targets imply ~10 seconds per candidate including evidence inspection — a reflex, not a review. The metric trap: precision is measured against human adjudication, rejections train detectors to be quieter, volume drops, precision rises and review duration falls — **both governing metrics improve monotonically** — while recall collapses and nothing measures recall, because there is no independent ground truth | **DECIDE** §4.5 |

### 2.6 Substitution and platform

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| **D24** ⚠ | MED-HIGH | **No partner can pass the conformance suite.** Several obligations — transactional outbox, inbox, per-log-line correlation IDs, owning exactly one database — are internal implementation properties unobservable from outside a black box and therefore unconformable by an executable suite. Either the obligation is unenforceable, or it is enforceable and no partner qualifies. Separately, the required Supply surface omits lead time, condition codes, and interchangeability, all of which the optimizer already depends on | **FIX** |
| **D25** | MED-HIGH | The migration sequence breaks at write cutover (the substitute has no history and consumers cannot rebuild) and double-issues legally-effective documents at shadow | **FIX** |
| **D26** ⚠ | MED-HIGH | **Five Domino capabilities are still assumed that document 02 rules out**: Extensions for practitioner surfaces (Cloud-only, but the target is self-managed OpenShift and air-gap); drift monitoring (all scoring is Flows on remote data planes, where Model Monitor is unsupported); air-gap (the *Domino application runtime itself* installs packages at pod start — a platform blocker presented as program discipline); prompt and manifest governance (not found in Domino, yet the pin is called load-bearing); and agent hosting caps and durability (10 apps / 4 active runs per project, 300s timeout against dossier assembly, restart-by-maintenance) | **FIX** |
| **D31** | MED-HIGH | Three sub-applications own the same vocabulary and no runtime authority reconciles them | **FIX** (see C8) |

### 2.7 The cross-cutting gap

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| **D37** ⚠ | MED-HIGH | **There is not one quantitative figure in any of the four documents.** No fleet size, installed items per asset, telemetry rate, proposals per day, reviewer count, scoring window, event rate, storage envelope, or latency budget. Yet at least eight architectural decisions already depend on those numbers — batch-first scoring, per-asset partitioning, retention tiers, the unified queue, the candidate cap, per-asset event batching, rollup tiering, and the divergence budget. At least three may not survive contact with the numbers | **DECIDE** §4.6 |

### 2.8 Findings surfaced during build-framework authoring (Wave 1–3)

Writing an executable specification against the corrected contracts surfaced defects the four review passes did not, precisely because generating real code forces every ambiguity to resolve one way or another. Most were fixed inline in document 03 as they surfaced (envelope `producer_node`, `p_failure` gating, the §7.2.1 authority table, `eic` fields, several stale cross-references) and are not re-numbered here. One requires a program decision rather than an editorial fix.

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| **D38** | MED-HIGH | **No plan exists to generate the unstructured corpus Knowledge & Retrieval exists to serve.** The synthetic data generator (`docs/build/13`) produces structured configuration, telemetry, maintenance, and supply data in depth, but "corpus" there means that structured dataset throughout — never IETMs, 3-M maintenance narratives, CASREP text, test reports, or engineering change proposals as free text with applicability metadata. Document 04 §11 calls unstructured corpus preparation "a substantial data-preparation problem," and it has no generation plan at all, structured or otherwise. Two consequences: Knowledge & Retrieval's own build document has nothing to serve, and finding D14's adversarial golden-question sets (injection-resistance testing for agent evaluation) have no source content to draw adversarial passages from | **DECIDE** — see below |

**The decision.** Whether the demonstration needs a synthetic unstructured corpus at all, and if so, at what depth: a handful of representative excerpts per source type sufficient to exercise the retrieval and classification-enforcement mechanics, or a larger library approaching what a real Knowledge & Retrieval deployment would index. This is a distinct content-generation problem from the structured generator — likely requiring either template-based synthesis of technical narrative text in correct Navy vocabulary, or LLM-authored synthetic documents with a fidelity-review pass, neither of which the structured generator's techniques (parametric distributions, degradation physics) address. Recorded here rather than decided unilaterally, in the same spirit as the ISO 14224 purchase decision and the holdout re-weighting decision in document 06.

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| **D39** | MED | **Canary-based recall measurement has no production sourcing story.** Document 06 §6 and PMA's build document (`docs/build/23`) specify seeded known-positive canaries as the mechanism that makes recall measurable, and both correctly note the mechanism depends on ground truth the *synthetic generator* holds. Nothing addresses where a fielded system — with no generator and no planted ground truth — draws canaries from. The demonstration's recall-measurement story does not transfer to production as designed | **DECIDE** — see below |

**The decision.** Candidate production sourcing mechanisms, none yet evaluated: a curated gold set of historically confirmed anomalies replayed as regression canaries; a periodic SME-authored synthetic-injection set maintained outside the generator; or accepting that production recall can only be *estimated* via the double-blind re-review sampling document 06 §6 already specifies, with canary-based measurement understood as a demonstration-only validation of the mechanism rather than a fielded capability. This is a document 06 §9-style question — what the demonstration's mechanism implies the enterprise must supply to keep working after fielding — and belongs in that section's Tier B program-requirements framing once decided.

---

## 3. Consistency findings

Compressed. Full detail, including exact quotations and recommended fixes, is in the review record. All are FIX unless noted.

### 3.1 High severity

| ID | Finding |
|---|---|
| **C1** | The `x-agent-eligible` rule introduced at rev 4 makes the `pdm-whatif` manifest listed in the same section impossible to build. Same defect blocks `POST /work-packages/plan` and `POST /scoring-runs`. Duplicates **D11** |
| **C2** | Document 03 §7.1 claims to "reproduce" document 01 §7's `FailurePrediction` but materially changes it; and 01 §7's use of `eic` as a join key violates 03 §4's own identity rule. The **approved artifact is the non-conformant one** |
| **C3** | **21 consumers declared in the 03 event catalog are not shown consuming in 04.** Each is an unbuildable consumer-driven conformance test |
| **C4** | Four events consumed in 04 by sub-applications the catalog does not declare as consumers — undeclared dependencies that a conformant substitution would break |
| **C5** | Registry and Condition & Telemetry omit "Events consumed" entirely, though the catalog declares them as consumers |
| **C6** | Usage counters have two owners in 01 §5 and a third custodian in §6 |
| **C7** | Domino Jobs writing directly into PdM's datastore contradicts principle 1 and obligation 4, and bypasses the outbox. Duplicates **D10** |
| **C8** | The unified taxonomy has three claimed owners (PMA, Failure Intelligence, Reference Data) and a fourth capture point in Scheduling. Duplicates **D31** |
| **C9** | Three incompatible integer identities exist for the same nine sub-applications (01 §5 numbering, 04 §1 diagram labels, 04 §12 sequence) |
| **C10** | **No canonical identifier exists for `InstalledItem`**, defeating document 04's most consequential modeling decision. It is undefined whether `equipment_id` identifies the position-bound slot or the physical item. Compounds **D9** |
| **C11** | The event envelope makes `asset_id` mandatory, but ~nine catalogued events have no asset scope |
| **C12** | `Proposal` is owned by "the executing sub-application", but no sub-application in 04 lists it in its Owns boundary or aggregate table |

### 3.2 Medium severity

| ID | Finding |
|---|---|
| **C13** | Document 01 cites "companion document §5" twice for platform requests that live in 02 §6 / §6.1 |
| **C14** | Three mutually inconsistent platform-service inventories; Notification is a declared consumer in five catalog rows but appears in no 01 inventory |
| **C15** | The event bus is placed in two different planes |
| **C16** | The glossary's Sustainment Plane definition contradicts the §3 plane allocation; no Data & Infrastructure Plane entry exists |
| **C17** | MCP tool servers are mandated on the Sustainment Plane but appear in no component inventory or monorepo path |
| **C18** | Document 04 asserts Domino agent hosting unconditionally in four places, never acknowledging the §8.7 contingency that 01 §15 makes an approval item |
| **C19** | The catalog lists consumers that exist nowhere ("governance reporting", "PEO reporting", "the originating agent's training corpus") and lists **agents as direct event consumers**, contradicting the rule that agents obtain state only through tools |
| **C20** | The conflict-policy table covers ten aggregates; document 04 defines roughly fifty |
| **C21** | The universal outbox is implemented inside a component declared "inert in the demonstration" — if outbox drain is inert, no event reaches the broker |
| **C22** | Document 02 contradicts itself on whether tier-weighted promotion gating is expressible today; the claim propagates into 01 §7 and §9 |
| **C23** | Ten operations across 04 violate 03's plural-collection naming rule |
| **C24** | Six RPC-shaped operations violate 03's resource-oriented REST convention with no sanctioned action pattern |
| **C25** | Three sub-applications define operations under `/assets/{id}` with no path-namespacing convention, colliding at a single gateway ingress |
| **C26** | Event names are inconsistently qualified and cased between the envelope example, the topic scheme, and the catalog |
| **C27** | **No canonical sub-application identifier is ever defined**, though four schemes reference one (topics, conformance paths, manifest paths, `target_sub_app`) and the monorepo uses different slugs |
| **C28** | Sub-application display names vary across and within documents — seven of nine have two or more spellings |
| **C29** | Domain-object terminology drift: **six labels for the component level**, three for mission, three for position; "Endpoint" carries two unrelated meanings with no disambiguation |
| **C30** | `Proposal` field names diverge between 01 §8.4 (`id`) and 03 §7.2 (`proposal_id`) |
| **C31** | No canonical identifier exists for the System level, though readiness is scoped to it |
| **C32** | PdM publishes `model_version.promoted`, a fact occurring in Domino's registry — outside PdM's domain, violating the events-carry-own-domain-facts principle |
| **C33** | Document 04 §11 promises two annotated services and delivers one |
| **C34** | 01 §16 and 04 §12 give different Phase 3 sequences |
| **C35** | Fleet Status disclaims owning any source fact while owning and publishing risk flags |
| **C36** | Evidence-package storage is claimed by both Telemetry and PMA |
| **C37** | Fleet Status's consumed-event list is prose, not event names — the single largest source of the C3 mismatches |
| **C38** | PdM uses wildcard subscriptions ("all Registry events, all Telemetry events"), which cannot be conformance-tested and auto-subscribe to future events |
| **C39** | The conflict policy requires "proposed" configuration changes with no matching proposal kind and no endpoint |
| **C40** | Document 02's version framing makes 6.3.0 simultaneously outside the assessed set, shipped, and in design |
| **C41** | 01 asserts an Extensions constraint 02 never establishes, and 04 uses Apps instead. Compounds **D26** |

### 3.3 Low severity

| ID | Finding |
|---|---|
| **C42** | Fourteen acronyms used without glossary entries (CQRS, MTBF, OMMS-NG, NAVSUP, UUV, LDUUV, AMMO, CAC/PIV, OPA, vLLM, LLM, GA, AsyncAPI, CUI, NOFORN/FOUO); two entries defined but never used |
| **C43** | 01 §16 says "four user types in §4"; §4 shows five actors |
| **C44** | 04 §1 states a template order the document never follows, and omits events from the stated template |
| **C45** | 01 §9 cites companion document §4 where §4.4 is meant |
| **C46** | README says "Both documents" of a four-document set |
| **C47** | The 01 §10 data-flow diagram contains two non-components, omits two adjudication targets, and omits five agent tool edges |
| **C48** | 02 §9 claims two documentation contradictions and records one |
| **C49** | 04's substitution column values do not use 03's marker names |
| **C50** | 01's status line understates rev 4, which added a new unapproved approval item and imposed a change on a downstream document |
| **C51** | 01 §5 omits the channel registry, which 04 §3 calls the hardest part of Condition & Telemetry |

### 3.4 Verified sound

The consistency review confirmed: all ordered lists sequentially numbered; all 59 tables cell-consistent; all section numbers sequential with no duplicates or skips; every event published in 04 present in the 03 catalog; every catalog event has at least one consumer; all five `Proposal` kinds have exactly one executing sub-application with a proposal endpoint; the seven agents are consistent across 01 §8.1, §11, and §16; and all package paths in 03 match the 01 §11 monorepo layout.

---

## 4. Decisions required — RESOLVED

> **All six decisions below were taken on 4 August 2026 and are recorded, with their assumptions and alternatives, in [06 — Demonstration Decisions and Assumptions](06-demo-decisions-and-assumptions.md).** Dispositions move from **DECIDE** to **FIX**; the fixes are carried in the remediation tranches in §5. The options analysis below is retained as the basis for each decision.
>
> | Decision | Resolution | Document 06 |
> |---|---|---|
> | §4.1 Causal validity | Policy-frozen holdout (10%, simulated in demo) plus statistical correction; "CASREPs avoided" replaced by warning lead-time coverage as primary metric | §2 |
> | §4.2 Prediction contract | Declared reference class replaces comparability; per-item RUL suppressed below item-conditional class; calibration gated at n ≥ 50 | §3 |
> | §4.3 Edge scope | Profile grows: edge-authoritative maintenance action records and edge-resident candidate generation. Demo exercises one SSN with a real partitioned deployment | §4 |
> | §4.4 Classification | Demo single-level unclassified, stated explicitly; production segregated; aggregation policy settled now as exclusion-by-default with a disclosed contributor count | §5 |
> | §4.5 Human capacity | Candidate cap 12, ~45 s per candidate, 15% seeded canaries for recall, 5% double-blind re-review, admission control at 3× throughput | §6 |
> | §4.6 Capacity model | 12 assets, ~8,400 installed items, 6 spotlight equipment families, 24 months tiered history, ~25,000 predictions per run | §7 |

These cannot be resolved editorially. Each changes program scope, operational practice, or an approved contract.

### 4.1 Causal validity — is an unconfounded stratum maintained? (D1, D21)

The system's central statistical claims are unrecoverable without a population whose maintenance is *not* assigned by the model. Three options:

| Option | Consequence |
|---|---|
| **Policy-frozen holdout** — a designated equipment population maintained on unmodified PMS periodicity, excluded from prediction-driven intervention | Gives an unconfounded stratum for calibration and causal analysis, and the only honest basis for a "CASREPs avoided" claim. Requires the Navy to agree that some equipment is deliberately not optimized |
| **Statistical correction only** — inverse-probability-of-censoring weighting, propensity modeling of the intervention policy, treatment recorded as a covariate | No operational concession. Materially weaker, depends on correct propensity specification, and cannot fully identify the counterfactual |
| **Accept the bias, and say so** | Cheapest. Requires abandoning the "CASREPs avoided" metric and stating the drift risk in program material |

**Recommendation:** the policy-frozen holdout for a small, deliberately chosen population, plus statistical correction. For the demonstration, simulate the holdout so the mechanism is visible.

Regardless of option: `maintenance_action.recorded` must carry `triggering_driver`, `triggering_prediction_id`, and `policy_version`. That is a FIX and is being applied.

### 4.2 The prediction contract — what replaces cross-tier comparability? (D7, D19)

The approved contract promises `p_failure` and `confidence` are comparable across tiers. That promise cannot be kept. Options:

| Option | Consequence |
|---|---|
| **Replace comparability with declared reference class** — add `reference_class`, `sharpness`, `fallback_level`, and `calibration_population`; the optimizer applies a per-tier decision-theoretic conversion rather than comparing raw probabilities | Honest and implementable. Consumers gain complexity: they must handle reference class, which weakens the "never branch on tier" simplification |
| **Suppress tier-0 per-item RUL** — publish a population hazard rate and no per-item distribution below tier 1 | Removes the memorylessness problem at source. The operator UI must then render two different things, which the tier-invariance principle was designed to avoid |
| **Keep the contract, accept incorrectness** | Not recommended. The optimizer's tier-0 starvation is silent and systematic |

**Recommendation:** both of the first two. Tier invariance survives as *shape* invariance; comparability is replaced by an explicit reference class and a per-tier decision conversion the optimizer owns.

### 4.3 Edge scope — does the afloat profile grow? (D8, D18)

Two findings converge: afloat, the system can neither capture maintenance actions nor generate anomaly candidates. Both defeat the label pipeline in the domain where labels matter most.

| Option | Consequence |
|---|---|
| **Grow the afloat profile** — add an edge-authoritative, append-only `MaintenanceActionRecord` separable from work-order authorization, plus an edge-resident detector ensemble and small pre-screener | Fixes both. Increases afloat footprint and Phase 3 scope. Requires provisional client-minted installed-item identities reconciled ashore |
| **Accept degraded afloat capture** — paper reconstruction ashore | Concedes that submarine data, the highest-consequence domain, is systematically poorer. Undermines the three-domain span the demonstration is built to show |

**Recommendation:** grow the profile. The distinction between recording *what was done* (a fact the ship owns) and *what was authorized* (a server decision) is correct in its own right, independent of the edge case.

### 4.4 Classification architecture — segregate or run system-high? (D13)

| Option | Consequence |
|---|---|
| **Producer-side segregation** — topic per classification level and compartment, cross-level flow only through an accredited guard; mandatory label inheritance as the union of inputs on every derived value; an explicit aggregation policy for readiness rollups | Defensible at accreditation. Multiplies topics, complicates the gateway, and requires Fleet Status either to exclude compartmented contributors or to classify rollups at the union with a separate low-side view |
| **Run system-high for the demonstration, defer** | Acceptable for an unclassified synthetic demo, provided the documents say so plainly rather than implying the current design is multi-level capable |

**Recommendation:** system-high for the demonstration with an explicit statement, and the segregated design documented as the production requirement. The aggregation-channel policy should be decided now regardless, because it constrains the readiness scoring methodology.

### 4.5 Human capacity — what are the real numbers? (D17)

The design's viability rests on adjudication throughput that has never been quantified, and its two governing metrics can both improve while the capability dies. Required: a capacity model (proposals per day, reviewers, adjudications per reviewer-hour, queue-growth bound, admission control), seeded known-positive canaries to estimate recall, and periodic double-blind re-review for inter-reviewer agreement. Recall must become a tracked metric or precision optimization will destroy the pipeline.

**This needs program input.** No amount of design work substitutes for knowing how many people will actually review.

### 4.6 A capacity model before Phase 3 (D37)

Order-of-magnitude figures with stated confidence for: fleet size and composition; installed items per asset by domain; telemetry rate per domain; predictions per scoring run and the acceptable scoring window; event rates per topic; proposals per day; storage envelope; and operator latency budget. Eight already-made decisions depend on these, and at least three may not survive the numbers.

**Recommendation:** produce this as a short document before Phase 3 detailed design begins. Synthetic-data design (the fourth cross-cutting item) cannot proceed sensibly without it either.

---

## 5. Remediation sequence

| Tranche | Contents | Rationale |
|---|---|---|
| **1** | Document 03 contract fixes: identity model, envelope, event semantics, agent eligibility, obligations split, shared schemas | 03 is binding on 04, so it must be correct first |
| **2** | Document 01 fixes: prediction contract, plane and inventory consistency, Domino capability reconciliation, injection and purge, glossary | Depends on the 03 contract being settled |
| **3** | Document 04 fixes: event catalog reconciliation (C3–C5, C37, C38), ownership boundaries, API naming, per-sub-application corrections | Largest mechanical volume; depends on tranches 1 and 2 |
| **4** | Document 02 fixes: C22, C40, C48, Extensions row | Independent; can proceed in parallel |
| **5** | The six §4 decisions, then the amendments each implies | Blocked on program input |
| **6** | Capacity model, then re-examination of the eight dependent decisions | Blocked on §4.6 |

Phase 3 detailed design should not begin before tranches 1–4 are complete and the §4 decisions are recorded, because several findings would otherwise be built into nine sub-application designs simultaneously.
