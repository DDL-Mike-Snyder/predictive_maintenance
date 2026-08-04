# Demonstration Decisions and Assumptions

| | |
|---|---|
| **Status** | Decided. Resolves the six open decisions in [05 §4](05-architecture-review-findings.md) |
| **Purpose** | Record a decision for each open question, the assumption it rests on, the alternative if that assumption does not hold, and — where the assumption is a statement about the operating environment — the program requirement it would become if funded (§9) |
| **Applicability** | Decisions are marked **DEMO** (applies to the demonstration only), **PRODUCTION** (the intended production position), or **BOTH** |
| **Provisional content** | The capacity figures in §7 are engineering estimates pending the Navy data-systems research in progress. Figures carrying LOW confidence are flagged and must be revised, not merely confirmed |
| **Classification** | Internal |

---

## 1. How to read this document

Each decision is stated in one sentence, then broken into what it assumes, what it costs, and what replaces it if the assumption fails. The alternatives are recorded because a demonstration assumption that quietly hardens into a production commitment is how programs acquire defects they cannot explain later.

Two principles governed these choices:

1. **Where the demonstration can show a hard problem being handled correctly, that is worth more than avoiding the problem.** A synthetic environment has ground truth that a real fleet does not, and several of the findings in document 05 are more persuasive demonstrated than described.
2. **A demonstration simplification is acceptable; a demonstration misrepresentation is not.** Where the demo runs a reduced posture, the documents say so plainly rather than implying the reduced posture is the design.

---

## 2. Decision 1 — Causal validity and the headline metric

**Decision (BOTH).** Adopt a **policy-frozen holdout** as the designed mechanism, implement it in the demonstration as a simulated holdout, retain counterfactual ground truth in the synthetic generator, and **replace "predicted CASREPs avoided" as the primary metric with a directly measurable one**.

### What this means concretely

| Element | Demo | Production |
|---|---|---|
| Holdout population | 10% of installed items, stratified across equipment families and all three domains, maintained on unmodified PMS periodicity and excluded from prediction-driven intervention | Same mechanism, population size and composition negotiated with the Navy |
| Treatment record | `maintenance_action.recorded` carries `triggering_driver`, `triggering_prediction_id`, `policy_version` (already implemented, document 03 rev 2) | Same |
| Statistical correction | Inverse-probability-of-censoring weighting plus propensity modeling of the intervention policy, applied alongside the holdout rather than instead of it | Same |
| Counterfactual truth | The generator retains each item's **true failure time regardless of intervention**, enabling exact measurement of what the corrected estimator recovers | Unavailable. This is why the holdout exists |

### The metric change

"Predicted CASREPs avoided" is a counterfactual and is not measurable in production. It is replaced by a two-tier metric set:

| Tier | Metric | Measurable in production? |
|---|---|---|
| **Primary** | **Warning lead-time coverage** — the proportion of corrective maintenance actions preceded by a raised risk flag at or beyond a stated horizon, with the lead-time distribution | **Yes, directly.** Requires no counterfactual |
| **Primary** | **Actionable precision** — the proportion of raised flags resolved by a maintenance action that found the predicted condition | Yes, from findings coding |
| Secondary | Estimated CASREPs avoided, with a confidence interval, computed on the holdout stratum only and labelled as an estimate | Only with the holdout |

Warning lead-time coverage is the right primary metric because it is what a maintainer actually cares about — *did the system tell me in time* — and because it cannot be gamed by suppressing predictions.

### Why the demonstration is stronger for this, not weaker

The demo can show the failure mode and the correction side by side: a naive estimator drifting toward run-to-failure over simulated operating time, against a corrected estimator holding calibration, with the generator's ground truth as the referee. Methodological rigor of this kind is a differentiator in a defense evaluation, and it is only demonstrable because the environment is synthetic.

### Assumptions and alternatives

| Assumption | Confidence | If it does not hold |
|---|---|---|
| The Navy will accept, in production, that a designated population is deliberately excluded from predictive optimization | **LOW.** This is a policy question, not a technical one, and a TYCOM may reject it outright | Fall back to statistical correction alone: IPCW plus propensity modeling, with the drift risk stated in program material and the secondary metric withdrawn. Materially weaker and dependent on correct propensity specification, but honest |
| A 10% holdout is statistically sufficient | MEDIUM. Adequate for common failure modes; too small for rare ones | Stratify the holdout by base rate rather than uniformly, over-sampling low-rate families; or accept that rare modes are uncorrectable and say so |
| Findings coding will be good enough to determine whether a flag "found the predicted condition" | **LOW.** This depends on capture discipline at the deckplate | Actionable precision degrades to a coarser binary from the corrective/preventive flag alone. Warning lead-time coverage survives, since it needs only the action record |

---

## 3. Decision 2 — The prediction contract

**Decision (BOTH).** Replace cross-tier probability comparability with a declared **reference class**, suppress per-item remaining-useful-life below an item-conditional reference class, separate cold-start depth from confidence, and gate publication on calibration population. Implemented in document 03 rev 2 §7.1.

### What this means concretely

- `reference_class` ∈ {`item`, `niin_fleet`, `equipment_family`, `class_estimate`} is required on every prediction. Consumers may branch on reference class; they still must not branch on tier.
- `rul` is emitted **only** where the reference class is item-conditional. Otherwise `population_hazard_rate` is emitted and `rul` is null. A memoryless population fit cannot produce a per-item residual life, and rendering one indistinguishably from a tier-3 distribution misleads the operator.
- `fallback_level` (0–4) carries cold-start depth; `confidence` carries sharpness and fit only.
- **Calibration population gate: n ≥ 50 item-horizons in the calibration cell** to publish a calibrated `p_failure`. Below that, the prediction publishes at `reference_class = class_estimate` with a population hazard rate and no calibrated probability.
- The scheduling optimizer converts to **expected consequence** per reference class rather than comparing raw probabilities. Consequence weights come from equipment criticality, which the Registry already carries.

### Assumptions and alternatives

| Assumption | Confidence | If it does not hold |
|---|---|---|
| Operators will accept an interface that presents two different output shapes — a distribution for instrumented items, a rate for the long tail | MEDIUM | Present a unified visual treatment where the long tail shows a rate band explicitly labelled as population-derived, visually distinct from an item distribution, and never fed to the optimizer as item-specific. The contract is unchanged; only presentation converges |
| n ≥ 50 is an appropriate gate | MEDIUM. Chosen as a practical floor, not derived | Raise for high-consequence families where a miscalibrated probability is costly; lower only with a documented widening of the published interval |
| Synthetic data volume can populate tier-2 and tier-3 calibration cells for the spotlight families | HIGH, because generation volume is a design parameter (§7) | Reduce the number of spotlight families and concentrate volume |
| The optimizer can be given defensible consequence weights | **LOW.** These are a program judgment requiring subject-matter validation | Use a coarse three-band criticality weighting for the demo, clearly labelled as illustrative, and make weight elicitation a Phase 3 workshop item |

---

## 4. Decision 3 — Edge scope

**Decision (BOTH).** Grow the afloat profile. Add an **edge-authoritative, append-only maintenance action record** separable from work-order authorization, and make **anomaly candidate generation edge-resident**. Conflict policies implemented in document 03 rev 2 §11.

**Decision (DEMO).** Exercise the afloat profile on **one submarine only**, with a single scripted disconnect-and-reconnect cycle, implemented as a physically separate deployment rather than a simulated queue.

### What this means concretely

| Element | Position |
|---|---|
| What the ship owns | The fact of what was done: action taken, findings code, parts consumed, corrective-versus-preventive determination, failure timing. Append-only, reconciled ashore |
| What the server retains | Authority over what was *authorized* — work orders, requisitions, configuration baselines |
| Candidate generation afloat | The detector ensemble and a small pre-screener run in the edge inference runtime against exported artifacts. The enterprise **adds** candidates on reconnect rather than being the sole source |
| Installed-item identity afloat | Client-minted UUID with `provisional: true`, confirmed or superseded by the Registry on reconciliation |
| Demo scope | One SSN, disconnected for a simulated six weeks, conducting one at-sea corrective repair and two mission reviews while dark |

The separation between recording what was done and authorizing what may be done is correct independently of the edge case. It is how maintenance documentation actually works, and adopting it removes an artificial coupling rather than adding a special case.

### Why a real deployment rather than a simulated queue

A simulated disconnect that only delays events does not exercise provisional identity minting, conflict resolution, divergence budgets, or degraded-mode presentation — which are the parts most likely to be wrong. The cost is one additional small deployment target; the return is that the DDIL story is demonstrated rather than asserted, and document 02 established that this is the single area where the platform provides nothing.

### Assumptions and alternatives

| Assumption | Confidence | If it does not hold |
|---|---|---|
| A second lightweight Kubernetes deployment is affordable within demo scope | MEDIUM | Fall back to a logical edge — same code, same conflict-resolution paths, same provisional identities, but co-located and network-partitioned rather than separately deployed. Preserves the correctness demonstration, weakens the deployment-footprint claim |
| Exported model artifacts can run in the edge runtime without Domino | HIGH. Document 02 confirms model export is a supported pattern with Navy precedent | If export proves impractical for tier-2 detectors, run only threshold and trending detectors afloat and accept lower candidate quality on the disconnected leg |
| Six weeks is a representative disconnection period | MEDIUM | Parameterize it. The divergence budget is a declared value per aggregate, so the period is configuration rather than design |
| Ship's force will record maintenance actions afloat without enterprise prompting | **LOW.** This is the same capture-discipline risk as D1 | The edge record degrades to a minimal three-field capture — what was replaced, when, corrective or preventive — which is still sufficient for label construction. Findings coding is completed ashore with the reviewer flagged as non-observer |

---

## 5. Decision 4 — Classification posture

**Decision (DEMO).** Operate **single-level, unclassified synthetic data throughout**, stated explicitly in every document rather than implied to be multi-level capable.

**Decision (PRODUCTION).** Producer-side segregation — one classification per topic, cross-level flow only through an accredited guard, mandatory label inheritance on derived values.

**Decision (BOTH).** **Settle the aggregation policy now**, because it constrains the readiness scoring methodology and cannot be retrofitted.

### The aggregation policy

A rollup whose value moves when a compartmented item degrades discloses that item's existence, and an explanation graph then supplies the pointer. Therefore:

1. **Default: exclusion.** A readiness rollup computed for a given clearance level excludes contributors above that level and exposes a `restricted_contributors_present` boolean with a count — never a description, a system, or a magnitude.
2. **High-side view.** A separate rollup is computed at the union of contributor labels, available only to appropriately cleared viewers.
3. **No silent substitution.** A low-side rollup never presents itself as complete. The boolean is displayed, not buried in metadata.
4. **Decomposability constraint.** Because rollups must decompose to source records (document 04 §5), and exclusion changes the decomposition, the scoring methodology must be exclusion-stable — the same formula must produce a coherent score over a subset of contributors. This rules out several otherwise attractive formulations and is the reason this decision cannot wait.

### Assumptions and alternatives

| Assumption | Confidence | If it does not hold |
|---|---|---|
| The demonstration will use only unclassified synthetic data | HIGH, and it is a program constraint rather than a prediction | If any real CUI enters the demo, the CUI marking and handling obligations under DoDI 5200.48 apply immediately, and the single-level posture must be re-stated as CUI-high rather than unclassified |
| Exclusion is the acceptable default rather than union-classification | MEDIUM. Accreditors differ on this | If exclusion is judged to leak through the count itself, suppress the boolean and accept that low-side viewers see a rollup with no indication of incompleteness — which is a worse operational outcome and should be argued against |
| Topic-per-classification is affordable in production | MEDIUM. It multiplies topics and complicates the gateway | A single topic at system-high with all consumers accredited to that level. Simpler and defensible, but every consumer inherits the highest classification present, which is the outcome document 05 D13 describes as making labels decorative |

---

## 6. Decision 5 — Human adjudication capacity

**Decision (BOTH).** Adopt an explicit capacity model with admission control, seeded canaries for recall estimation, and double-blind re-review for inter-reviewer agreement. **Recall becomes a tracked metric with equal standing to precision.**

### The model

| Parameter | Demo value | Basis |
|---|---|---|
| Candidate cap per review | **12** | Bounded review at a realistic per-candidate inspection time |
| Target review duration | **≤ 10 minutes** | 45 s per candidate including evidence inspection. The earlier implied ~10 s was a reflex, not a review |
| Reviewer personas | 2 (ship's force, shore analyst) | Sufficient to demonstrate qualification weighting and disagreement analysis |
| Missions per month (demo fleet) | ~70 — 5 surface underway periods, 1 submarine patrol, ~64 unmanned sorties | §7 |
| Candidates per month | ~840 | 70 × 12 |
| Adjudication load | ~10.5 reviewer-hours per month | 840 × 45 s |
| **Seeded canaries** | **15% of candidates** are known-positive faults injected by the generator | Makes recall measurable without independent ground truth |
| Double-blind re-review | 5% of completed reviews re-reviewed by a second reviewer | Inter-reviewer agreement and per-reviewer bias |
| Admission control | If unadjudicated candidates exceed 3× monthly throughput, candidate generation halts and an alarm raises | Prevents unbounded queue growth masquerading as capability |

### Closing the metric trap

The trap is that a reviewer under time pressure rejects to finish, rejections train detectors to be quieter, and both precision and review duration improve while recall collapses. Three countermeasures:

1. **Canary recall** is reported alongside precision on the same dashboard. A precision improvement accompanied by a canary-recall decline is flagged, not celebrated.
2. **Rejections are not the sole training signal.** An exhaustively-labelled holdout sample of missions — feasible because the generator knows the truth — provides a reference independent of adjudication behavior.
3. **Reviewer qualification weights labels**, and per-reviewer rejection rates are monitored for drift.

### Assumptions and alternatives

| Assumption | Confidence | If it does not hold |
|---|---|---|
| 45 s per candidate is realistic | MEDIUM. Untested with actual maintainers | Instrument it in the demo and revise. If real inspection takes 2–3 minutes, the candidate cap drops to 4–5 and candidate ranking becomes far more consequential |
| 15% canary density is detectable-but-not-obvious | MEDIUM | If reviewers learn to spot canaries, they stop measuring recall. Vary density and injection realism, and treat canary detectability as a monitored property |
| Reviewers will be available at all in production | **LOW.** This is the program's largest non-technical risk | If adjudication capacity is genuinely unavailable, the causal capability must be rescoped: retain the pre-screener as an advisory surface, drop the supervised causal pipeline, and state that Failure Intelligence operates on maintenance findings coding alone. That is a materially smaller product and should be surfaced early rather than discovered late |

---

## 7. Decision 6 — The capacity model

**Decision (DEMO).** Adopt the figures below as the demonstration's design envelope. Every figure carries a confidence marking; LOW-confidence figures are to be revised against the Navy data-systems research, not merely confirmed.

### Fleet composition

| Domain | Count | Representative class | Confidence |
|---|---|---|---|
| Surface | 5 | DDG 51 Flight IIA | HIGH — a program choice |
| Subsurface | 3 | VIRGINIA-class | HIGH — a program choice |
| Unmanned | 4 | 2 large UUV, 2 USV | HIGH — a program choice |
| **Total assets** | **12** | | |

Twelve assets is the smallest fleet that exercises the three-domain span, gives a plausible fleet-level rollup, and supports cross-hull population comparison for causal analysis.

### Configuration scale

| Quantity | Value | Confidence |
|---|---|---|
| Tracked installed items per surface asset | ~1,200 | **LOW.** A real DDG configuration record is far larger; this is a deliberate HM&E-focused subset (ESWBS 200/300/500) |
| Per subsurface asset | ~600 | **LOW** |
| Per unmanned asset | ~150 | **LOW** |
| **Total installed items** | **~8,400** | LOW |
| Distinct NIINs | ~2,500 | LOW |
| Equipment families | ~120 | MEDIUM |
| **Spotlight families** (full-fidelity sensor coverage, tiers 2–3) | **6** | HIGH — a program choice |
| Spotlight installed items | ~250 | HIGH |

The spotlight construct is the central scaling decision: full-fidelity synthetic telemetry and failure physics for six equipment families across all three domains, with the remaining long tail generated at low fidelity for tier-0 and tier-1 modeling. This is what makes the tiered-modeling story demonstrable at affordable data volume — and it mirrors reality, where sensor coverage is concentrated.

### Prediction and scoring

| Quantity | Value | Confidence |
|---|---|---|
| Horizons per item | 3 (30, 90, 180 days) | MEDIUM |
| Predictions per scoring run | ~25,000 | HIGH, derived |
| Target scoring window | < 60 minutes for a full fleet run | MEDIUM |
| Scoring cadence | Daily for tiers 0–1, per-mission-completion for tiers 2–3 | MEDIUM |

At ~25,000 predictions per run, the scale concern raised as D27 does not bind the demonstration. It binds production at ~300 hulls, where the same design yields ~3×10⁶ predictions per run, and the event-referencing pattern adopted in document 03 rev 2 is what preserves headroom.

### Telemetry

| Quantity | Value | Confidence |
|---|---|---|
| Surface: spotlight channels | 40 channels/asset at 1 Hz | MEDIUM |
| Surface: routine channels | 200 channels/asset at 1/minute | MEDIUM |
| Unmanned: per sortie | 100 channels at 10 Hz, downsampled at ingest to 1 Hz for storage, raw retained per sortie in object storage | MEDIUM |
| Subsurface | 150 channels at 1/minute, transmitted in burst on reconnect | MEDIUM |
| Live ingest rate | ~5M samples/day fleet-wide | MEDIUM, derived |
| Historical generation | **24 months, tiered**: full fidelity for spotlight items, 1/hour aggregates for the long tail | HIGH — a program choice |
| Estimated historical row count | ~1.5×10⁹ spotlight rows before rollup; ~4×10⁷ long-tail rows | LOW |

The historical volume is the single largest technical risk in the synthetic data effort, and the tiered approach is what keeps it tractable. Full-fidelity generation of 24 months across all 8,400 items would produce volumes inappropriate to a demonstration.

### Supply, maintenance, and agents

| Quantity | Value | Confidence |
|---|---|---|
| Maintenance actions generated over 24 months | ~14,000 | LOW |
| Corrective proportion | ~35% | LOW |
| CASREP-severity events | ~180 over 24 months | LOW |
| Availabilities represented | 6 across the fleet, including 1 DSRA | MEDIUM |
| Requisitions | ~6,000 over 24 months | LOW |
| Agents in demo | 3 — Maintainer Copilot, PMA Pre-Screener, Redesign Case Builder | HIGH |
| Agent proposals per day | < 20 | MEDIUM |
| Operator latency budget | p95 < 1.5 s for fleet and asset views; < 4 s for explanation decomposition | MEDIUM |

### Assumptions and alternatives

| Assumption | Confidence | If it does not hold |
|---|---|---|
| A 12-asset fleet is credible to Navy evaluators | MEDIUM | Expand to a full DESRON or squadron equivalent. The design is unaffected; generation cost scales roughly linearly, and the spotlight construct absorbs most of it |
| Configuration counts are within an order of magnitude | **LOW.** Pending research | If real HM&E configuration is 10× larger, the long-tail generation shifts from row-level to statistical: generate failure and maintenance history without underlying telemetry for non-spotlight items, which tiers 0–1 do not require |
| 24 months of history is sufficient for tier-0 Weibull fits and causal population comparison | MEDIUM. Adequate for common modes, thin for rare ones | Extend to 60 months for the long tail only, which is cheap because long-tail generation is statistical rather than sample-level |
| Synthetic failure physics will be realistic enough that tier-2/3 models are meaningful | **LOW, and this is the most consequential assumption in the program** | If the generator produces signatures too clean, models will appear excellent and the demonstration will mislead. Mitigation: inject realistic sensor noise, drift, dropout, and mislabelled maintenance records; validate that a naive baseline performs *poorly* on the synthetic data before accepting it. A generator on which trivial methods succeed is invalid |

---

## 8. Consolidated assumption register

The assumptions most likely to be wrong, and most damaging if wrong, in priority order.

| # | Assumption | Confidence | Damage if false | Alternative |
|---|---|---|---|---|
| A1 | Synthetic failure physics are realistic enough for tier-2/3 modeling to be meaningful | LOW | The demonstration misleads. Highest-consequence assumption in the program | Adversarial generator validation: trivial baselines must fail before the data is accepted (§7) |
| A2 | Adjudication capacity exists in production | LOW | The supervised causal pipeline is unbuildable | Rescope Failure Intelligence to findings coding only, and say so early (§6) |
| A3 | The Navy accepts a policy-frozen holdout | LOW | No unconfounded stratum; the secondary metric is withdrawn | IPCW and propensity correction alone, with drift risk stated (§2) |
| A4 | Configuration counts are within an order of magnitude of the estimate | LOW | Synthetic data effort is mis-sized | Statistical rather than sample-level long-tail generation (§7) |
| A5 | Capture discipline at the deckplate is adequate for findings coding | LOW | Label quality degrades; actionable precision becomes uncomputable | Minimal three-field capture afloat, coded ashore with non-observer flagged (§4) |
| A6 | Operators accept two output shapes across reference classes | MEDIUM | Interface rejection | Converge presentation, keep the contract (§3) |
| A7 | A second edge deployment is affordable in demo scope | MEDIUM | DDIL story weakens from demonstrated to asserted | Logical edge: same code paths, network-partitioned, co-located (§4) |
| A8 | Consequence weights for the optimizer can be defensibly set | LOW | Schedule recommendations are not credible to planners | Coarse three-band criticality weighting, labelled illustrative (§3) |
| A9 | 45 s per candidate is realistic | MEDIUM | Capacity model is wrong by 3–4× | Instrument and revise; candidate cap drops and ranking matters more (§6) |
| A10 | Exclusion is the acceptable aggregation default | MEDIUM | Accreditation friction | Union classification with a separate low-side view (§5) |

---

## 9. Assumptions as program requirements

The assumption register in §8 was written defensively — each row a risk to be mitigated. That framing understates what the register actually contains. Most of these assumptions are statements about the operating environment, and a funded program of record does not have to accept its operating environment as given. It can specify it.

This reframes the register from a list of things that might go wrong into **the program's requirements on the enterprise**: what the Navy would need to record, retain, staff, and instrument for condition-based maintenance to work at all. Stated that way, the same content becomes a value proposition and an adoption roadmap rather than a set of caveats, and it positions the capability as driving CBM+ implementation rather than being limited by the current state of maintenance data.

The distinction matters in a specific way. A tool that accommodates poor configuration data and inconsistent maintenance coding will produce weak predictions indefinitely, and the weakness will be attributed to the analytics. A program that specifies the minimum data required to produce a defensible prediction — and can demonstrate the difference — converts a data-quality problem from an excuse into a funded line of effort.

### 9.1 Tiering the asks

An unbounded set of enterprise demands makes a program unadoptable. The requirements below are therefore tiered by whether the capability functions without them.

| Tier | Meaning |
|---|---|
| **A** | The capability does not work without this. Non-negotiable dependency |
| **B** | The capability works but is materially weaker. Strong recommendation with a demonstrable return |
| **C** | Valuable, and the program can proceed without it. Candidates for later phases |

### 9.2 Enterprise data and policy requirements

| From | Program requirement | Tier | Form it would take |
|---|---|---|---|
| A5 | **Minimum label-bearing fields on every maintenance action** — corrective versus preventive determination, findings code against the controlled vocabulary, failure timing, and the triggering driver where one exists | **A** | A 3-M data requirement, potentially implemented as required fields in the maintenance action record. The four fields are the entire supervised signal; without them no tier improves over time |
| A4 | **Position-level configuration fidelity** — configuration records that distinguish a position from the item installed in it, with install dates and usage at installation | **A** | A configuration data quality line of effort against CDMD-OA. Predictions attach to physical items; a configuration baseline that cannot distinguish a replacement from its predecessor makes remaining-useful-life meaningless |
| A2 | **Adjudication capacity** — a designated reliability analyst function with allocated time, whether a billet, an ISEA function, or an RMC role | **A** | A manning or task-order requirement. The causal capability is supervised; without human adjudication it reduces to findings-coding analysis |
| A3 | **A reliability reference population** — a designated, policy-frozen population maintained on unmodified periodicity and excluded from prediction-driven intervention | **B** | A TYCOM instruction or CBM+ implementation policy. Directly analogous to a control group in test and evaluation, which is established practice; the novelty is applying it to sustainment rather than to acquisition |
| D8 | **Afloat maintenance recording** — the ability for ship's force to record what was done while disconnected, separable from work-order authorization | **B** | An afloat capability requirement. Supports 3-M documentation independently of any predictive capability, which makes it easier to justify |
| A1 | **Instrumentation expansion** on prioritized equipment families | **B** | A CBM+ instrumentation investment line, prioritized by §9.3 |

### 9.3 The tiering model as an investment prioritization tool

The criticality scorer and tier assignment engine were designed to select a modeling approach. They answer a second question at no additional cost, and it is arguably the more valuable one for a sponsor:

> For each NIIN currently at tier 0 or 1, what would it take to move it to tier 2 or 3, and what readiness return would that produce?

The scorer already computes mission criticality, casualty history, consequence of failure, **sensor availability**, and fleet population. Holding the first four fixed and varying the fifth produces a ranked list of instrumentation investments with an estimated readiness return for each. That output is a sensor-investment business case generator, and it is a direct product of the tiered architecture rather than an additional feature.

This should be an explicit program deliverable. It converts the tiering model from an internal implementation detail into a planning instrument a sponsor can act on, and it gives the program a defensible answer to the question of where instrumentation money should go — currently a judgment call in most CBM+ programs.

### 9.4 Architectural properties that become program contributions

Several decisions taken for internal correctness generalize beyond this program and are publishable as practice.

| Property | Contribution |
|---|---|
| **Warning lead-time coverage** as the primary effectiveness metric | A CBM+ effectiveness measure that is directly measurable, requires no counterfactual, and cannot be gamed by suppressing predictions. Current practice leans on avoided-failure counts, which are unmeasurable. This is a candidate for enterprise adoption |
| **Treatment-record fields** on maintenance actions | A causal-integrity standard. Any predictive-maintenance program that intervenes on its own predictions has the informative-censoring problem in document 05 D1, and almost none record the intervention. Recording it is cheap and is the prerequisite for any defensible effectiveness claim |
| **Propose, adjudicate, execute** with authority checked against blast radius | An AI governance pattern for operational DoD systems: agents never commit state, authority scales with consequence, and dual control applies at class and fleet scope. Directly responsive to responsible-AI policy expectations |
| **Reference-class disclosure** on every prediction | A model-transparency standard. Publishing the reference class and calibration population alongside a probability prevents the silent incomparability described in document 05 D7, and is a stronger transparency posture than a model card |
| **Executable conformance suites** per discipline | The mechanism by which a modular open systems approach becomes testable rather than declaratory. A partner implementation is certified by a test run, not by review |
| **Exclusion-stable rollups** | A multi-level aggregation pattern that avoids disclosing the existence of compartmented contributors through a readiness score |

### 9.5 What should not be baked in

Distinguishing genuine program requirements from demonstration scaffolding is necessary, or the program will inherit constraints that exist only because a demo needed to be small.

| Demonstration choice | Status |
|---|---|
| 12-asset fleet, 6 spotlight equipment families | Scaffolding. Sized for demonstrability, not derived from any operational requirement |
| Single-level unclassified operation (§5) | Scaffolding. The production position is producer-side segregation |
| Simulated policy-frozen holdout | Scaffolding for the mechanism; the mechanism itself is a Tier B requirement |
| Three agents rather than seven | Scaffolding |
| Synthetic data throughout | Scaffolding, and the assumption most likely to flatter the results (A1) |
| 24 months of history, tiered generation | Scaffolding |

### 9.6 Consequence for program narrative

If funded, the program's position changes from *a system that consumes Navy maintenance data* to *a capability that specifies what must be recorded to make condition-based maintenance work, and demonstrates the difference*. The Tier A requirements in §9.2 are the specification; the tiering model in §9.3 is the investment roadmap; and the contributions in §9.4 are what the program offers the enterprise beyond its own scope.

The risk in this posture is over-reach: a program that demands extensive enterprise change before delivering anything will not be adopted. The tiering exists to manage that. Tier A items are genuinely prerequisite and should be stated as such. Tier B items should be accompanied by a demonstrated return, which the demonstration is positioned to provide. Tier C items should not be raised in an initial funding conversation at all.

---

## 10. Propagation

These decisions change documents already written. Remediation tranches in document 05 §5 absorb them.

| Decision | Documents affected | Status |
|---|---|---|
| §2 Causal validity, treatment record | 03 §6 (done, rev 2); 01 §13 metric change; 04 §4 and §9 method statements | 03 complete; 01 and 04 in tranches 2–3 |
| §3 Prediction contract | 03 §7.1 (done, rev 2); 01 §7 must be replaced by a pointer; 04 §4 calibration and cold-start text | 03 complete; 01 and 04 pending |
| §4 Edge scope | 03 §11 (done, rev 2); 01 §12 afloat subset; 04 §6 and §8 plane placement and aggregates | 03 complete; 01 and 04 pending |
| §5 Classification | 03 §12 (done, rev 2); 01 §0 and §5; 04 §5 scoring methodology constraint | 03 complete; 01 and 04 pending |
| §6 Human capacity | 01 §8.8 metrics; 04 §8 review parameters; new metric definitions | Pending |
| §7 Capacity model | Referenced by 04 §12 cross-cutting item 4; informs every Phase 3 design | Pending |

Document 05 §4 dispositions are hereby resolved from **DECIDE** to **FIX**, with the fixes carried in the remaining tranches.
