# Build 13 — Synthetic Data Generator

| | |
|---|---|
| **Status** | Build specification. Prescriptive — an implementer follows it rather than interpreting it |
| **Purpose** | Specify the generator that produces the entire FATHOM demonstration dataset: configuration, telemetry, maintenance history, CASREPs, supply and allowance data, the policy-frozen holdout population, the counterfactual ground truth, and the scripted edge-disconnection scenarios |
| **Why this document is unusually detailed** | Assumption **A1** in [06 §8](../architecture/06-demo-decisions-and-assumptions.md) — *synthetic failure physics are realistic enough that tier-2/3 modeling is meaningful* — is the highest-consequence assumption in the program. If this generator produces failure signatures that are too clean, every downstream model looks excellent, the demonstration misleads, and the failure is discovered by a Navy stakeholder rather than by us. Three areas are where that happens: **noise injection** (§9), **fidelity validation** (§16), and **identifier fabrication** (§6). Those three sections are written so that no design decision is left to the implementer |
| **Binding inputs** | [03 Integration Contracts](../architecture/03-integration-contracts.md) §3.3, §5.4, §11 · [05 Findings](../architecture/05-architecture-review-findings.md) D1 · [06 Demo Decisions](../architecture/06-demo-decisions-and-assumptions.md) §2, §4, §6, §7, §8 · [07 Navy Data Systems](../architecture/07-navy-data-systems.md) §3–§8 · [08 Standards Alignment](../architecture/08-standards-alignment.md) §5 |
| **Conventions** | Repository layout, language, tooling, CI, and the shared Definition of Done template are in [09 — Monorepo and Conventions](09-monorepo-and-conventions.md). This document adds generator-specific requirements only |
| **Classification** | Internal. The artifact-level marking posture for what this generator *produces* is §4 |

---

## 1. Purpose, scope, and what this generator is not

### 1.1 What it produces

One command produces one immutable, addressable **dataset** — a versioned corpus with a data card, a V&V report, and a withheld ground-truth partition.

| Output partition | Contents | Consumed by |
|---|---|---|
| `configuration/` | 12 assets, their system/position trees, ~8,400 installed items with install histories, the item catalogue, allowance documents | Registry, Supply |
| `telemetry/` | Sample-level channels for spotlight items; hourly aggregates for the long tail; per-sortie raw objects for unmanned | Condition & Telemetry, PdM |
| `maintenance/` | 24 months, ~14,000 maintenance actions as 2-Kilo-shaped records with findings coding, ~180 CASREP-severity events, 6 availabilities | Scheduling, PdM, Failure Intelligence |
| `supply/` | SNSL allowance rows with derivation basis, ~6,000 requisitions, carcass transactions, stock positions | Supply |
| `holdout/` | The policy-frozen population manifest — 10% of installed items (§10) | PdM, Fleet Status, evaluation |
| `candidates/` | Anomaly candidates with the 15% seeded-canary population (§13) | PMA, adjudication rehearsal |
| `scenarios/` | The scripted single-SSN six-week disconnect fixtures (§15) | Edge deployment test suite |
| **`truth/`** | **Counterfactual ground truth: true failure time per item regardless of intervention, degradation trajectories including their post-intervention continuation, policy decision inputs, canary tags** | **Evaluation only. Never an input to any training or scoring path (§8.6)** |
| `card/` | The data card (§17) and the MIL-STD-3022 evidence bundle (§16.6) | Program, accreditation |

### 1.2 What it is not

- **It is not a model of a real Navy platform.** No row, parameter, or nomenclature string identifies real equipment. §19 is the operative constraint and it is not negotiable for convenience.
- **It is not evidence of model performance.** Every dataset ships the narrow accreditation statement in §16.5 verbatim, in machine-readable form, in its own data card.
- **It is not a source of training data for anything fielded.** Per [08 §5.6](../architecture/08-standards-alignment.md): *no model trained solely on synthetic data is a candidate for operational use*, because DoDM 5000.101 requires an operationally representative independent test set and synthetic data cannot satisfy that by construction. This statement is a required field of the data card, not a footnote.
- **It is not a fixture library.** Fixtures for unit tests are small, hand-written, and live with the service under test. This generator produces a corpus, and a service test that needs 8,400 installed items to pass is testing the wrong thing.

### 1.3 The one-sentence design thesis

The generator is built as **two processes that cannot see each other** — a failure process that owns truth and an intervention policy that owns treatment — plus a **noise and label-corruption layer between them and the observable output**, and an **adversarial harness that refuses to release the dataset until trivial methods have demonstrably failed on it**. Everything else in this document is mechanism in service of those three things.

---

## 2. The capacity envelope

These figures are authoritative. They come from [06 §7](../architecture/06-demo-decisions-and-assumptions.md) except where [07 §8](../architecture/07-navy-data-systems.md) supersedes, which is marked. The generator **fails the build** if a realized figure departs from its target by more than the stated tolerance (§18.4).

### 2.1 Fleet and configuration

| Quantity | Value | Source | Tolerance |
|---|---|---|---|
| Surface assets | 5, DDG 51 Flight IIA class | 06 §7 | exact |
| Subsurface assets | 3, VIRGINIA class | 06 §7 | exact |
| Unmanned assets | 4 — 2 large UUV, 2 USV | 06 §7 | exact |
| **Total assets** | **12** | 06 §7 | exact |
| Installed items per surface asset | ~1,200 (deliberate HM&E subset, ESWBS 200/300/500) | 06 §7, retained by 07 §8 | ±5% |
| Per subsurface asset | ~600 | 06 §7 | ±5% |
| Per unmanned asset | ~150 | 06 §7 | ±5% |
| **Total installed items** | **~8,400** | 06 §7 | ±5% |
| Distinct NIINs in the catalogue | **~4,000–6,000** | **07 §8 supersedes** 06 §7's ~2,500 | within band |
| Equipment families | ~120 | 06 §7 | ±5 |
| **Spotlight families** | **6** | 06 §7 | exact |
| Spotlight installed items | ~250 | 06 §7 | ±10 |
| Policy-frozen holdout | 10% of installed items (~840) | 06 §2 | exact percentage |

### 2.2 Telemetry

| Quantity | Value | Source |
|---|---|---|
| Surface spotlight channels | 40 channels/asset at 1 Hz | 06 §7 |
| Surface routine channels | 200 channels/asset at 1/minute | 06 §7 |
| Subsurface | 150 channels/asset at 1/minute, delivered in burst on reconnect | 06 §7 |
| Unmanned | 100 channels at 10 Hz per sortie, downsampled to 1 Hz at ingest, raw retained per sortie in object storage | 06 §7 |
| Live ingest rate | ~5M samples/day fleet-wide | 06 §7 |
| Historical generation | 24 months, tiered: full fidelity for spotlight items, 1/hour aggregates for the long tail | 06 §7 |
| **Historical row budget** | **~1.5×10⁹ spotlight rows before rollup; ~4×10⁷ long-tail rows** | 06 §7 (marked LOW confidence there) |

**Two reconciliations the implementer must not discover the hard way.** Both are consequences of the figures above, not departures from them.

1. **The spotlight row budget is only achievable with windowed generation.** Surface spotlight alone at a continuous 1 Hz is 5 assets × 40 channels × 6.31×10⁷ seconds ≈ **1.26×10¹⁰ rows**, roughly an order of magnitude over the whole budget; unmanned at 1 Hz downsampled across ~1,536 sorties is of the same order. Therefore sample-level generation is **duty-cycle gated and windowed**: a spotlight channel produces 1 Hz samples only inside an *active window* — the asset is underway or on sortie, the equipment is energized, and the window is either mission-anchored or degradation-anchored (§7.5). Outside active windows the same channel produces 1-minute aggregates. Window widths and the deep-fidelity sortie sample fraction are **open program decisions** (§21, OPD-3); the budget is not.
2. **The ~5M samples/day live rate implies a staggered mission calendar.** One instrumented surface asset underway plus one submarine at sea plus ~2 sorties/day lands near 5M–7M samples/day; five surface assets underway concurrently does not. The mission calendar generator (§7.2) must therefore stagger underway periods in OFRP fashion rather than drawing them independently, and the realized daily live rate is a checked figure.

### 2.3 Prediction, scoring, missions, maintenance, supply, agents

| Quantity | Value | Source |
|---|---|---|
| Horizons per item | 3 — 30, 90, 180 days | 06 §7 |
| Predictions per scoring run | ~25,000 | 06 §7 |
| Scoring cadence | daily for tiers 0–1; per-mission-completion for tiers 2–3 | 06 §7 |
| Missions per month | ~70 — 5 surface underway periods, 1 submarine patrol, ~64 unmanned sorties | 06 §6 |
| Candidates per month | ~840 (70 × candidate cap 12) | 06 §6 |
| Seeded canaries | **15% of candidates** are known-positive faults injected by the generator | 06 §6 |
| Double-blind re-review | 5% of completed reviews | 06 §6 |
| Maintenance actions over 24 months | ~14,000 | 06 §7, retained 07 §8 |
| Corrective proportion | ~35% | 06 §7 |
| **Status 2 or 3 proportion** | **~25%** | 07 §5.4, 07 §8 |
| CASREP-severity events | ~180 over 24 months | 06 §7, retained 07 §8 |
| Availabilities | 6 across the fleet, including 1 DSRA | 06 §7 |
| Requisitions | ~6,000 over 24 months | 06 §7 |
| Agents represented | 3 — Maintainer Copilot, PMA Pre-Screener, Redesign Case Builder | 06 §7 |
| Agent proposals per day | < 20 | 06 §7 |

**The corrective / Status 2-3 interaction is a constraint, not two independent draws.** ~35% of 14,000 ≈ 4,900 corrective actions, and ~25% of 14,000 ≈ 3,500 Status 2 or 3. Status 2 (inoperative) and Status 3 (degraded) are corrective conditions, so the generator must produce Status 2/3 as a **subset of corrective** — approximately 3,500 of the 4,900 corrective actions carry Status 2 or 3, and the remaining ~1,400 corrective actions are Status 1 minor corrective work. Drawing the two proportions independently produces preventive actions marked inoperative, which a 3-M analyst reads as a defect on sight. The label filter downstream is Status 2/3 ([07 §5.4](../architecture/07-navy-data-systems.md)), so this ratio directly determines label volume.

**Fleet-scale reference cardinalities** from 07 §8 — ~43,000 APLs and ~4,200 EICs in the TMA/TMI analysis population, >60,000 APLs fleetwide — are **not generation targets.** They are the proportionality argument that a curated single-hull HM&E subset in the low thousands is credible, and they belong in the data card's fidelity-claims section, not in the generator's output.

---

## 3. Module structure

One Python package, one CLI, seven pipeline stages. Stage boundaries are enforced boundaries, not organizational suggestions — three of them exist specifically to make a causal or classification error impossible rather than merely discouraged.

### 3.1 Pipeline stages

| # | Stage | Reads | Writes | Enforced property |
|---|---|---|---|---|
| 1 | `plan` | run config, parameter bundle | plan manifest: fleet skeleton, row budget allocation, seed tree root | Fails if the planned row count exceeds §2.2's budget |
| 2 | `configure` | plan | `configuration/` | Identifier rules (§6) applied at the only place identifiers are minted |
| 3 | **`truth`** | plan, parameter bundle | **`truth/`, sealed** | Draws every latent failure time and full degradation trajectory. **Cannot import `policy/`** |
| 4 | **`policy`** | plan, `configuration/`, **`truth/` through the veil only** | intervention schedule, simulated predictions | **Cannot read a latent failure time.** Enforced by the veil adapter (§8.3) plus an import contract |
| 5 | `observe` | truth trajectories, intervention schedule | `telemetry/`, `maintenance/`, `candidates/` | Applies the noise and label-corruption pipeline (§9). The only stage that writes observable data |
| 6 | `supply` | `maintenance/`, `configuration/` | `supply/` | BRF is computed from generated 3-M usage, closing the real loop (§12) |
| 7 | `validate` | `observed` partitions, `truth/` | `card/`, V&V report | The adversarial harness (§16). **Exit non-zero blocks release** |

`scenario` is a separate entry point that composes stages 2–6 over a scripted timeline (§15).

### 3.2 Layout

```
data/synthetic/                                  # per 01 §11 monorepo layout
  generator/                                     # ── ARTIFACT 1: generator code
    pyproject.toml
    importlinter.ini                             # the separation contracts of §8.3 and §18.3
    src/fathom_synth/
      cli.py                 # fathom-synth plan|configure|truth|policy|observe|supply|validate|card|scenario
      config.py              # RunConfig: dataset_id, master_seed, budgets, identity_mode, profile
      rng.py                 # the deterministic seed tree (§18.1)
      params.py              # the ONLY module that reads the parameter bundle. Loader, not values
      veil.py                # GroundTruthVeil — the observable-only projection (§8.3)
      budget.py              # row budget planner and enforcer
      fleet/
        fleet_builder.py     # assets, UICs, hulls, class designations
        hierarchy_schemes.py # HSCI-selected scheme registry; ESWBS is one variant, not the universe
        position_tree.py     # systems -> positions
        install_history.py   # position -> ordered installed items, replacements, provisional cases
        catalogue.py         # NIIN catalogue with NSN/NICN/LICN/CAGE heterogeneity
      identity/                                  # §6. Every identifier is minted here or nowhere
        niin.py  cage_part.py  eic.py  apl_ael.py  uic_hull.py  jcn.py  docnum.py
        reserved.py          # the reserved blocks and the banned-real-value list
        checks.py            # post-generation identifier assertions run by `validate`
      families/
        registry.py          # family plugin registry, keyed on OPAQUE family_key
        spec.py              # FamilySpec dataclass: the parameter schema of §7.4
        physics/                                 # archetypes, NOT named equipment
          bearing_spall.py            # SF-01
          hydraulic_wear_step.py      # SF-02
          fouling_reset.py            # SF-03
          multicomponent_efficiency.py# SF-04
          stiction_intermittent.py    # SF-05
          sensitivity_loss_ingress.py # SF-06
      truth/
        failure_process.py   # T*, onset, P-F interval, trajectory. NO import of policy/
        trajectory.py        # continues past intervention, always
        canaries.py          # §13 — same code path as ordinary faults, by construction
        store.py             # sealed writer; hash-manifests the truth partition
      policy/
        intervention.py      # the simulated maintenance system
        pms.py               # unmodified PMS periodicity
        holdout.py           # admission filter (§10.3)
        predictions.py       # the simulated prediction stream the policy acts on
      telemetry/
        channels.py          # channel registry, many-to-many channel<->item mapping (§7.3)
        windows.py           # active-window and duty-cycle gating
        sampling.py          # per-domain ingest profiles: surface / burst / per-sortie
        noise/                                   # §9 — one module per stage, ordered
          s1_transfer.py s2_stationary.py s3_drift.py s4_confounding.py
          s5_dropout.py s6_impulse.py s7_timebase.py s8_crosschannel.py
          s9_label.py s10_mnar.py
          pipeline.py        # the fixed order, and the ablation switch the harness uses
      longtail/
        navy_reliability.py  # MTBF / MDT / T(pf) / Ao exactly as 07 §5.5 states them
        event_sampler.py     # Poisson event generation from seeded MTBF
      maintenance/
        two_kilo.py  casrep.py  findings.py  availability.py
      supply/
        allowance.py         # UR = POP x BRF / 4 and the four documented thresholds
        requisition.py  carcass.py  nha_redirect.py  price.py
      scenarios/
        edge_disconnect.py   # §15
      emit/
        writers.py  events.py  datacard.py
    tests/
  harness/                                       # §16 — ships with the generator
    baselines/  gates/  power.py  report/
  schema/                                        # ── ARTIFACT 2: schema
    tables/*.sql  events/*.avsc  codesets/*.yaml
    datacard.schema.json  ground_truth.schema.json  holdout_manifest.schema.json
  scenarios/edge/*.yaml                          # scripted scenario definitions + golden files
  profiles/{smoke,ci,full}.yaml                  # run configs; `smoke` must complete in < 5 min
docs/vva/                                        # the four MIL-STD-3022 products (§16.6)
  accreditation-plan.md  vv-plan.md  vv-report.md  accreditation-report.md
```

**Parameters and generated rows deliberately do not appear in that tree.** That is the subject of §4.

---

## 4. The four-artifact separation, made concrete

[08 §5.6](../architecture/08-standards-alignment.md) calls this *the highest-leverage decision in this area*: separate the artifact into four independently markable pieces so that a Controlled Technical Information determination on one does not contaminate the others. [08 §5.4](../architecture/08-standards-alignment.md) explains why the parameters are the likely trigger — *real failure rates, MTBF values, inspection intervals, and degradation rates for identified Navy equipment are the reliability characteristics of a Navy platform*, and *the more faithful the synthesis, the weaker the argument that control was broken.*

Separation is only real if it is structural. A four-way conceptual distinction inside one git repository is one `git clone` away from being no distinction at all.

### 4.1 The four artifacts

| # | Artifact | Location | Version identity | Assumed marking until an OCA rules | May contain |
|---|---|---|---|---|---|
| **1** | **Generator code** | `data/synthetic/generator/` in the monorepo | git SHA + semver | **Unclassified**, Distribution D | Mechanism, distribution *forms*, code-set *field names*, the reserved-block rules. **No equipment nomenclature, no reliability constants, no real identifier values** |
| **2** | **Schema** | `data/synthetic/schema/` in the monorepo | semver, published with `packages/canonical-schemas` | **CUI//SP-CTI assumed**, Distribution B–E (08 §5.6 action 4) | Field catalogue, table DDL, code-set enumerations, the data-card and ground-truth schemas |
| **3** | **Fitted parameters** | **Outside the monorepo.** Separate repository `fathom-genparams`, published as an OCI artifact, pulled by digest | semver + `sha256:` digest | **CUI//SP-CTI assumed**, Distribution B–E | Per-family physics constants, hazard parameters, noise magnitudes, code-value distributions, the generic functional nomenclature, the seeded UIC/FSC tables |
| **4** | **Generated rows** | Object store `s3://fathom-synthetic/<dataset_id>/` (MinIO in the demo). Never committed | `dataset_id` = content hash of the plan + digests of artifacts 1–3 | **Unclassified**, per the data card | Realizations only. **No parameter values, no parameter names, no bundle digests beyond the single provenance reference** |

`docs/vva/` and the data cards are documentation *about* artifacts 1–4 and are marked to the highest level of what they quote — which is why they quote parameter *provenance classes* and never parameter *values*.

### 4.2 How a determination on the parameters fails to propagate to the rows

Four mechanisms, all of which are tested (§18.3):

1. **The bundle is not in the repository, and cannot be added.** `params.py` resolves the bundle from `FATHOM_GENPARAMS` — an OCI reference pinned by digest — and mounts it read-only at `/params`. CI enforces a deny-rule: any file under the monorepo matching the bundle's manifest schema, or any path matching `**/params/**`, `**/*.params.yaml`, `**/reliability*.yaml`, fails the build. A developer who wants a local bundle uses `oras pull`; a developer who commits one is rejected before review.
2. **The code cannot name the equipment.** Generator code addresses families by **opaque `family_key`** (`SF-01` … `SF-06`, `LT-0001` … `LT-0114`). Human-readable nomenclature, ESWBS assignment, FSC assignment, and every physics constant arrive from the bundle at run time. A banned-literal scan (§18.3) fails the build if generator source contains any string from the banned list — real APL/AEL/EIC values quoted in 07, real equipment designations, or any decimal literal registered as a reliability constant in the bundle's key index.
3. **The rows carry a digest, never a value.** Row-level provenance is exactly one field: `parameter_bundle_digest`, a `sha256:` reference. No generated row, column name, partition name, file name, or metadata key reproduces a bundle key or a bundle value. The `validate` stage runs a **parameter-leakage scan**: for every numeric bundle scalar, assert that no generated column's summary statistics reproduce it within 1×10⁻⁶ relative tolerance in a position where it would be recoverable — that is, no column is a constant equal to a parameter, and no column's exact mean, minimum, or maximum equals one. Realizations *drawn from* a distribution are the intended output; a column that literally *is* a parameter is a leak.
4. **The generated rows are inference-resistant by volume, not by claim, and this is stated rather than assumed.** A sufficiently large corpus permits re-estimating the parameters that produced it. That is a property of synthetic data generally and is **disclosed in the data card** (§17.2, field `inference_disclosure`) rather than argued away. [08 §5.4](../architecture/08-standards-alignment.md) is explicit that *statistical synthesis is not a recognised decontrolling mechanism*; the defense is that the parameters were never fitted to controlled data in the first place (§4.3), so what is recoverable is engineering judgment about fabricated equipment.

### 4.3 Parameter provenance is a typed, enforced field

Every scalar in the bundle carries a provenance class. The `params` loader **refuses to load a bundle** in which any scalar lacks one, and refuses class P4 unconditionally.

| Class | Meaning | Example admissible source |
|---|---|---|
| **P1** | Derived from an open, published dataset | NASA PCoE C-MAPSS / N-CMAPSS, IMS bearings, FEMTO/PRONOSTIA, Li-ion, milling, IGBT ([08 §5.1](../architecture/08-standards-alignment.md)) |
| **P2** | Engineering judgment, documented, about fabricated equipment | A plausible fouling time constant for a notional oil cooler |
| **P3** | A published Navy formula or published code set | `UR = POP × BRF / 4`; the MTBF/MDT/Ao formulas; COG, SMR, DIC code sets |
| **P4** | **Fitted to real Navy reliability, maintenance, or configuration data** | **Prohibited. Loader raises. This is [08 §5.6](../architecture/08-standards-alignment.md) action 3 and §19's first entry** |

P1 use carries a mandatory paired caveat: the bundle field `domain_transfer_note` must be populated, and its content propagates verbatim into the data card. NASA PCoE sources are aero-propulsion, bearing, and battery data; they anchor *difficulty and pipeline behavior*, never *representativeness of shipboard HM&E* ([08 §5.7](../architecture/08-standards-alignment.md)).

### 4.4 What each artifact may be shared as

The point of the separation is that these four answers can differ:

- A partner may receive **artifact 4** (rows) plus its data card and build a conformance implementation, without receiving the generator.
- A partner may receive **artifact 1** (code) and reproduce nothing, because the bundle is absent — which is the correct behavior, and `plan` fails with an explicit message rather than substituting defaults. **There are no default parameter values anywhere in generator code.** A hardcoded fallback would silently reintroduce the coupling this section exists to prevent.
- **Artifacts 2 and 3** travel together to accreditation and to the OCA, and are the artifacts the CUI determination is actually about.

---

## 5. Fleet, configuration, and catalogue generation

Stage `configure`. All identifiers are minted by §6; this section specifies structure.

### 5.1 Assets

Twelve assets per §2.1. Each carries the `AssetRef` shape of [03 §3.3](../architecture/03-integration-contracts.md): `asset_id` (UUID, the join key), `hull_or_tail`, `uic`, `class_id`, `domain`.

- **`class_id` carries the class expressed as the lead hull number** — 51 for ARLEIGH BURKE — plus flight or block, because that is how the Navy expresses ship class ([07 §3.1](../architecture/07-navy-data-systems.md), Record Type 1 `CLASS`).
- **`hull_or_tail` renders with a space and never a hyphen.** SECNAVINST 5030.8D Enclosure 6: *"Hyphens will not be used in the hull number of any ship or craft."* Trailing `N` denotes nuclear propulsion; leading `T-` denotes Military Sealift Command. This is a corrected finding ([07 §3.5](../architecture/07-navy-data-systems.md), 07 §9) and §18.2 asserts it with a regex over every emitted row, not only at mint time.
- **Unmanned assets carry a tail-style designator**, not a hull number, and are associated with a parent unit rather than being independently NVR-listed (§6.4).
- SCLSIS **Record Type 1**'s six fields are generated per asset: `UIC`, `STATUS`, `HSCI`, `TYCOM`, `STHN`, `CLASS`. `TYCOM` values are NOT PUBLICLY FOUND ([07 §3.1](../architecture/07-navy-data-systems.md)) — the field is generated from a reserved synthetic set and flagged in the data card's divergence list, never populated with a guessed real value.

### 5.2 Hierarchy is scheme-aware, not ESWBS-fixed

[07 §3.4](../architecture/07-navy-data-systems.md) is a correction with a real design consequence: **HSC is the Hierarchical Structure Code, its format varies by ship, and Record Type 1 carries `HSCI` to say which scheme applies.** An architecture that assumes one universal layout is wrong.

The generator therefore ships a **scheme registry** (`hierarchy_schemes.py`) with at least two schemes instantiated across the fleet, so that every consumer's scheme-awareness is exercised rather than asserted:

| Scheme | Applied to | Structure |
|---|---|---|
| `ESWBS-like` | 5 surface assets | Three-level numeric groups, generated within ESWBS 200/300/500 bands only |
| `VARIANT-A` | 3 subsurface + 4 unmanned assets | A different segment count and width, selected by a different `HSCI` value |

**ESWBS code content is NOT PUBLICLY FOUND** ([07 §3.4](../architecture/07-navy-data-systems.md), §10), and the informally circulating nine-group summary table is *unusable* — 07 records that ESWBS `843` = ballast contradicts it. Consequences, both mandatory:

1. Generated ESWBS-like codes come from a **reserved synthetic band** whose values are structurally shaped but are not presented as real ESWBS values.
2. The generator **never emits the informal nine-group mapping**, and no bundle field may encode it. A reviewer who recognizes a fabricated ESWBS group table stops believing the rest of the dataset, which is precisely 07's evidentiary argument: *fabricated schema detail is worse than an acknowledged gap.*

### 5.3 Systems, positions, and installed items

The three-level distinction is load-bearing and is where the inherited-degradation defect enters if it is fudged (`[C10]`, [03 §3.3](../architecture/03-integration-contracts.md), 04 §2).

```
Asset ──< System (SystemRef: system_id, eswbs)
           └──< Position (PositionRef: position_id, position_code, system_id)
                  └──< InstalledItem history, ordered, non-overlapping
                        (InstalledItemRef: installed_item_id, iuid, position_id,
                         niin, serial_or_lot, installed_at)
```

Generation order and rules:

1. **Positions are generated first and are permanent.** Position count per asset is the §2.1 installed-item count; a position is occupied by at most one item at any instant.
2. **Every position gets an install history**, not a single item. Over 24 months a position holds 1 to *n* items. `install_history.py` produces the sequence with non-overlapping intervals and a `superseded_by` chain.
3. **A replacement is a new `installed_item_id` with a new IUID and zero accumulated usage.** No item ever inherits its predecessor's usage, degradation state, or trajectory. This is the single most consequential configuration rule in the generator: violate it and remaining-useful-life becomes meaningless while the dataset still looks fine (`[C10, D9]`).
4. **IUID is instance identity, not EIC.** DoDI 4151.22 §1.2.d/l make serialized item management and IUID the externally mandated instance identity; EIC is a class code of variable specificity and is **never a join key** ([03 §3.3](../architecture/03-integration-contracts.md), [08 §6](../architecture/08-standards-alignment.md)). The generator emits `iuid` on every installed item and emits `eic` for federation and human reference only.
5. **Registry holds a usage-at-installation snapshot** and it is a copy, not authoritative (01 §6). The generator emits it as such, with a deliberate small fraction of snapshots that disagree with the authoritative counter series, because that disagreement is a real condition the pipeline must tolerate.
6. **`baseline_epoch` is monotonic per asset** and increments on every configuration change. Every emitted event carrying configuration dependence carries `baseline_id` and `baseline_epoch` ([03 §5.4](../architecture/03-integration-contracts.md) `[D3, D4]`).
7. **A configuration change emits an OPNAV 4790/CK-shaped transaction** ([07 §3.6](../architecture/07-navy-data-systems.md)). Transaction and action code values are NOT PUBLICLY FOUND; generate from a reserved set and record the divergence. **There is no "ASI number"** — ASI is the Automated Shore Interface *batch process* (07 §9), so the generator models it as a batch event (`JSS117` Unit / `JSS135` Force) and never as an identifier field.

### 5.4 SCLSIS Record Type 2 and the RIC / RIN distinction

Each installed item emits a configuration-item record shaped on SCLSIS **Record Type 2**'s 41 fields as enumerated in [07 §3.1](../architecture/07-navy-data-systems.md). Field *lengths* are NOT PUBLICLY FOUND; the schema declares generated lengths and the data card lists this as a known structural divergence.

Three fields must be right because they are the ones commonly confused (07 §3.1, 07 §9):

| Field | Semantics the generator must honor |
|---|---|
| **`RIC`** | Repairable Identification Code — **this is the field that carries the APL or AEL number** |
| **`RIN`** | Record Identification Number — an internal record address for automated retrieval. A surrogate, **not** a domain identifier, and never used as a join key in generated data |
| **`PAR RIC`** | The RIC of the equipment carrying supply support when an item has **no APL or AEL of its own**. A real parent-fallback mechanism: the generator gives a bundle-specified fraction of installed items no own `RIC` and a populated `PAR RIC`, so the fallback path is exercised |

### 5.5 The catalogue is heterogeneous

[07 §7.2](../architecture/07-navy-data-systems.md) names catalogue homogeneity as something *almost no synthetic dataset gets right*. The generated catalogue of ~4,000–6,000 distinct items carries all five documented forms ([07 §4.8](../architecture/07-navy-data-systems.md)), in bundle-specified proportions, with these invariants:

| Form | Structure | Invariant the generator enforces |
|---|---|---|
| NSN-shaped | FSC + NCB + item number | Stored as **NCB and item number separately**, not as a monolithic NIIN — FLIS does, and the composite-key pattern is `(NCB_CD, I_I_NBR, MOE_RULE_NBR, EFF_DT)` |
| Permanent NICN | `LL` in positions 5–6 **and `C` in position 7** | Requisitioned via DD 1348-6 |
| Temporary NICN | `LL` in 5–6, any letter except `C` in 7 | A subset converts to NSN during the 24 months, and the conversion carries status code **`BG`** |
| LICN | FSC of a similar item + `LL` + 7 alphanumeric | **Never appears in any supply transaction.** Asserted over all generated transactions (§18.2) |
| CAGE + part number | 5 + up to 32 | Escalates to DD 1348-6 above 10 characters |

Federal Supply Classification realism: 78 groups, 645 classes; FSG 60 (Fiber Optics) **is** assigned and FSG 33 is **unassigned** (07 §9 — the inverse of a premise that was wrong). Unassigned FSGs are 21, 27, 33, 50, 57, 64, 82, 86, 90, 92, 97, 98.

Every catalogue item also carries the real code values that make a dataset read as naval ([07 §4.6](../architecture/07-navy-data-systems.md), §4.7): **COG** weighted toward `2S`, `7H`, `3H`, `1H`, `9N`; **SMR** at six positions with **recoverability at position 5 only** (07 §9); MCC; AAC; unit of issue including **`SO` = Shot** (15 fathoms, correct for anchor chain). Fund codes and project codes are left **blank** — the values are NOT PUBLICLY FOUND and they map to real appropriations ([07 §7.2](../architecture/07-navy-data-systems.md)).

---

## 6. Identifier fabrication

This is one of the three places the generator most likely goes wrong, so every rule here is a rule, not a guideline. `identity/` is the **only** place in the generator that mints an identifier; a module that constructs one inline fails review and fails the import contract in §18.3.

Two source documents conflict on one point, and §6.4 resolves it explicitly rather than silently choosing.

### 6.1 The governing objective

An identifier must be simultaneously:

1. **Structurally correct** — correct length, correct field widths, correct positional semantics, so a Navy logistician reads it as well-formed ([07 §7.1](../architecture/07-navy-data-systems.md)).
2. **Unambiguously fabricated** — structurally incapable of colliding with a real identifier, so that no generated row can be mistaken for, or accidentally reference, real controlled material ([08 §5.6](../architecture/08-standards-alignment.md) action 2).

Where those two objectives conflict, **objective 2 wins and the resulting realism loss is recorded in the data card's divergence list.** The reverse choice — realism first, non-collision by luck — is what makes a CTI determination cheap for an assessor to reach.

### 6.2 The reserved item-identifier block, and why it is structural

The honest position first: **the real NSN item-number space cannot be reserved by inspection.** NSNs are 13 numeric characters, FLIS access was blocked throughout the research in 07, and no public source consulted establishes an unassigned numeric NIIN range. Choosing a numeric block and asserting it is free would be luck, and 07 §1's evidentiary rule — *do not fabricate; leave blank or generate from a reserved synthetic range* — forbids dressing that up.

There is exactly one structural guarantee available from public sources, and the generator uses it: **a real NSN is all-numeric, and the Navy's own local-item convention places alphabetic characters in defined positions.** An identifier containing an alphabetic character in a position an NSN requires to be numeric cannot be a real NSN — not improbably, but by construction.

**Block A — the default block, all catalogue items.**

```
FSC (4, REAL)  ||  "LL" (positions 5-6)  ||  7 alphanumeric (positions 7-13)
                    ^^^^ the NCB positions of a real NSN are numeric.
                         "LL" is the documented Navy local-item marker (07 §4.8).
```

- Position 7 = `C` → **permanent NICN**, requisitionable via DD 1348-6.
- Position 7 = any other letter → **temporary NICN**, a subset of which converts to Block B during the 24-month window with status code `BG`.
- Same shape with `transaction_eligible = false` → **LICN**, local use only, never in a transaction.
- **FSCs are real**, drawn from the verified shipboard HM&E classes in [07 §4.8](../architecture/07-navy-data-systems.md): **2010** ship and boat propulsion components · **2030** deck machinery · **2040** marine hardware and hull items · **4320** power and hand pumps · **4410** industrial boilers · **4420** heat exchangers and steam condensers · **4620** water distillation · **4810** valves powered · **4820** valves non-powered · **5845** underwater sound equipment · **6320** shipboard alarm and signal systems · **6605** navigational instruments · **6680** / **6685** flow, level, pressure and temperature measuring. The FSC list lives in the bundle; the *rule that FSCs are real* lives in the code.

**Block B — the all-numeric block, used only where an all-numeric NIIN is required.**

```
FSC in an UNASSIGNED FSG  ||  9 numeric
    ^^ FSG 33 is unassigned (07 §9). No NSN is ever assigned within an unassigned FSG,
       so a 33xx-classed item cannot collide with a real NSN.
```

Block B exists because Block A alone cannot exercise two real code paths: the **temporary-NICN-to-NSN conversion** (07 §4.8: *periodically converted to NSN; conversion carries status code `BG`*) needs a numeric target, and any consumer keyed on all-numeric NIINs needs at least one. Block B is therefore **small** — the converted subset plus a numeric-path coverage sample, on the order of a few percent of the catalogue, exact fraction bundle-owned. Reserved expansion FSGs, in order of use: 33, then 21, 27, 50, 57, 64, 82, 86, 90, 92, 97, 98.

**Declared divergence.** The FATHOM catalogue is overwhelmingly Navy-local-item-coded, where a real COSAL is majority NSN. Consequence, stated in the data card: **any analysis keyed on NCB values, or on the NSN-versus-NICN mix, is not representative.** The compensating realism gain is genuine — the DD 1348-6 escalation path, LICN transaction exclusion, and `BG` conversion are all exercised, and most synthetic datasets exercise none of them.

**Every item row additionally carries `synthetic: true` and `catalog_authority = "FATHOM-SYNTH"`.** Belt and braces: the structural argument is the guarantee, the flag is what a human sees.

### 6.3 EIC, APL, AEL — shape-correct, value-reserved

| Identifier | Structural rule the generator enforces | Reservation rule |
|---|---|---|
| **EIC** | **7 alphanumeric**, positionally segmented: position 1 = system, 1–2 = subsystem, 3–4 = equipment category. **Truncated EICs are legitimate** — a 2-character value identifies a subsystem only, and the generator emits a bundle-specified fraction of truncated EICs because real data contains them ([07 §3.2](../architecture/07-navy-data-systems.md), [03 §3.3](../architecture/03-integration-contracts.md)) | First position drawn from a program-reserved character set, plus a **banned-value list** containing every real EIC published in 07 §3.2 (`QK0V000`, `QM93000`, `QW71000`, `TB04000`, `TB04600`, `5515000`, `5515100`, `5515300`) and all of their 2- and 4-character truncations. **Residual collision risk is accepted and is harmless**, because EIC is never a join key — a collision affects display and federation only, never identity |
| **HM&E APL** | **9 characters**, first two digits = equipment/component category | Reserved category pair from the bundle. Never a real published value |
| **Ordnance APL / ORDALT / MACHALT** | 9 characters; ordnance first two `00`, ORDALT `0R`, MACHALT carries an alpha in the **6th** position | Generated only if ordnance is in scope for the run; HM&E-focused runs omit them |
| **Electronic / GFCS APL** | **8 characters**, carries a Section B in circuit-symbol-number sequence | Section B generated only where the consumer requires it |
| **Miscellaneous Repair Parts List** | 9 characters, always begins **`89`** | Real prefix, reserved remainder |
| **Allowance Components List** | **10 characters**, last two `CA`–`CZ` except `X`; **identifies no parts** | The no-parts property is enforced, not decorative |
| **AEL** | **10–11 characters — model both and state the ambiguity** ([07 §4.1](../architecture/07-navy-data-systems.md): Appendix B says 10, Appendix D's positional scheme implies 11, real examples show both). First-digit series honored: `1-`/`2-` HM&E, `3-NDI` portable COTS, `3-HZ` HazMat, `7-` portable electronics test equipment. HM&E categories such as `1-38xxx` air purifying and ventilation, `2-4700x` portable pumps, `2-88xxx` damage control, `2-93xxx` fire fighting are used as *category semantics* | Reserved remainder. Banned-value list contains `A004230048`, `A00423A068`, `0-00423A105`, `00423A759`, `701110382`, `701110383`, `052050008`, `616050177C` |
| **`P` prefix** | Indicates an **incomplete APL**. A bundle-specified fraction of APLs carries it | — |

**The composite key is generated as a composite key.** [07 §5.1](../architecture/07-navy-data-systems.md) records the Navy asserting it directly: *"Both the EIC and APL/AEL numbers are necessary to provide complete identification."* The generator must reproduce both halves of the documented worked example — two *identical* items in different applications sharing an APL with **different EICs**, and two *different* items in one system sharing an EIC with **different APLs**. Both cases are required in every dataset, and §18.2 asserts their presence. A generator that produces a 1:1 EIC-to-APL mapping has silently removed the reason the composite key exists.

**No generated identifier is ever paired with real equipment nomenclature.** Not `LM2500`, not `AN/UYQ-70`, not `MK 41`, not any real type designation, including in comments, test fixtures, sample data, or documentation examples. §19 states why: pairing a fabricated reliability characteristic with an identified real system is exactly the CTI pattern [08 §5.4](../architecture/08-standards-alignment.md) describes, and it is the one shortcut that converts an unclassified demonstration into a controlled one.

### 6.4 UIC and hull number — a conflict between source documents, resolved

[07 §7.1](../architecture/07-navy-data-systems.md) directs **real UICs from the Naval Vessel Register for the instantiated hulls**. [08 §5.6](../architecture/08-standards-alignment.md) action 2 directs **fabricated hull and UIC values from a declared fictitious range**. Both cannot hold for the same asset, and the conflict is not cosmetic: a real UIC paired with a real hull number identifies a specific commissioned ship, and the generator then attaches fabricated reliability behavior to an identified Navy platform — the precise pattern [08 §5.4](../architecture/08-standards-alignment.md) warns weakens the CTI-avoidance argument.

**Resolution: a two-mode configuration with the safe mode as default.** `RunConfig.identity_mode` is a required field with no default value, so the choice is always explicit and always lands in the data card.

| Mode | Behavior | When permitted |
|---|---|---|
| **`fabricated`** — **the default** | Class designation is real and generic (`DDG 51 Flight IIA` names a public class, not a hull). Hull numbers come from a declared fictitious block. **UICs are minted with an alphabetic character in position 1** — SECNAVINST 5400.48 defines the UIC as *"a five or six-character **alphanumeric** code"*, while every real ship UIC cited in [07 §3.3](../architecture/07-navy-data-systems.md) is five numeric, so an alpha-leading UIC is well-formed and structurally distinguishable. The fleet is named as a fictitious force in every operator-facing surface | Always. No determination required |
| **`nvr_seeded`** | The generator's fleet config is **seeded** with real five-character UICs obtained from the Naval Vessel Register (`nvr.navy.mil` — public), one per instantiated hull, per the 07 §7.1 posture. The generator does not invent them and does not ship them: they are a required config input, absent by default, and the run fails if the mode is selected without them | Only with a **written program determination** recorded in the data card field `identity_mode_authorization`. The determination is a program decision, not an engineering one |

Rules that hold in **both** modes:

- **UIC is modeled as five characters, with an optional leading Service prefix in DoDAAC and requisition contexts.** Navy DoDAAC first position is N, Q, R, or V; **ships use `R` (Pacific) or `V` (Atlantic)** ([07 §3.3](../architecture/07-navy-data-systems.md)). So the six-character form is derived, never stored as a second independent identifier.
- **The UIC is the first five characters of every requisition document number and every JCN** (07 §3.7). Generated across three sub-applications from one source, never re-derived.
- **Unmanned vehicles do not receive a vessel UIC.** Vehicle-level UICs are NOT PUBLICLY FOUND. Unmanned assets are associated with a parent unit that carries the UIC, and the vehicle carries a tail-style designator plus its internal `asset_id`. Requisitions and JCNs for unmanned equipment use the parent unit's UIC — which is also the operationally correct behavior, and is recorded as an assumption in the data card.
- **Hull number rendering is asserted globally**: no emitted string in any partition matches a hyphenated hull pattern (§18.2).

### 6.5 Transaction identifiers

| Identifier | Rule | Source |
|---|---|---|
| **Requisition document number** | **14 characters**: service code (`N` other than fleet, `R` Pacific Fleet, `V` Atlantic Fleet) + requisitioner UIC (5) + Julian date `YDDD` (4) + serial (4), **serial excluding the letters `I` and `O`** | [07 §4.4](../architecture/07-navy-data-systems.md) |
| **JCN** | **13 characters**: UIC (5 numeric) + Work Center (4 alphanumeric, left justified; 4 positions on ships, 3 at intermediate activities) + Job Sequence Number (4) | [07 §5.2](../architecture/07-navy-data-systems.md) |
| **JSN first position** | **Identifies the tool or organization that created the 2-Kilo**, and exists explicitly to support data mining and aggregation. FATHOM declares **its own originator alpha code** for prediction-driven 2-Kilos. Originator values are centrally controlled and NOT PUBLICLY FOUND, so the declared code is drawn from a reserved character and **recorded in the data card** field `jsn_originator_code` | [07 §5.2](../architecture/07-navy-data-systems.md) |
| **Transportation control number** | 17 characters where in-transit visibility is generated | [07 §4.9](../architecture/07-navy-data-systems.md) |
| **DIC values** | **Real code values throughout**, with the documented third-character semantics: `_1` requisitioner, `_2` supplementary addressee, `_6` ICP-to-storage, `_8` to DAAS, `_9` from DAAS; `A` domestic NSN, `B` domestic part number, `1` overseas NSN | [07 §4.5](../architecture/07-navy-data-systems.md) |
| **Never generated** | RDD codes `444`, `N__`, `E__`; unit of issue `ST`; routing identifier codes `S9M`, `S9T`, `SMS`, `NRP`. All either NOT FOUND or affirmatively wrong | [07 §4.5](../architecture/07-navy-data-systems.md) |

### 6.6 CAGE codes — an acknowledged residual

CAGE is 5 alphanumeric characters. **No structural reservation rule for CAGE was established from the public sources in 07**, so this generator does not claim one. Two rules follow:

1. Synthetic CAGE values are drawn from a program-declared table in the bundle, every part row carries `cage_synthetic = true`, and the **residual collision risk is disclosed in the data card** rather than argued away.
2. `reserved.py` carries a `TODO(OPD-1)` referencing §21: if the exclusion of the letters `I` and `O` from assigned CAGE codes is confirmed in DoD 4100.39-M Volume 8, switch to minting CAGE values containing exactly one `I` or `O`, which converts this from a disclosed residual into a structural guarantee. Until confirmed, **do not assert it** — that is the 07 §1 evidentiary rule applied to our own work.

### 6.7 Unit price

Unit price uses **implied two decimals**, with a `D` in the units position at or above $10M ([07 §7.2](../architecture/07-navy-data-systems.md), DoD 4100.39-M Vol 12). The generator stores prices as integers in implied-two-decimal form and formats on emit; a float price column anywhere in the output is a defect, because it is the specific detail that reveals a dataset was designed in a spreadsheet. Price bands must straddle the two documented thresholds — **$2,000** (price-sensitive sparing at 4.0) and **$10K** (the CASREP add-back ceiling) — so §12's allowance rules are actually exercised.

---

## 7. The spotlight-family generation engine

Six equipment families ([06 §7](../architecture/06-demo-decisions-and-assumptions.md), a program choice, HIGH confidence) receive full-fidelity generation: sample-level telemetry, explicit degradation physics, and item-conditional failure timing. The remaining ~114 families are generated statistically (§11). The spotlight construct is what makes tiered modeling demonstrable at affordable volume, and it mirrors reality, where sensor coverage is concentrated.

### 7.1 The six families

Nomenclature is **generic and functional by requirement** (§6.3, §19). Each family is a *class of machinery with a characteristic degradation mode*, not a Navy type designation.

| Key | Family (generic functional nomenclature) | Domains | FSC | Degradation archetype | Parameter provenance |
|---|---|---|---|---|---|
| **SF-01** | Rolling-element bearing set, motor-driven auxiliary machinery | surface, subsurface, unmanned | 4320 / 2010 | **Two-stage spall**: stochastic initiation, then accelerating defect growth | P1 — IMS, FEMTO/PRONOSTIA run-to-failure |
| **SF-02** | Centrifugal seawater service pump — wear-ring and impeller erosion with mechanical-seal failure | surface, subsurface | 4320 | **Slow hydraulic wear with abrupt step failures** | P2 with P1 anchoring |
| **SF-03** | Plate-type lube-oil cooler / heat exchanger — fouling | surface, subsurface | 4420 | **Asymptotic fouling with incomplete cleaning resets** (sawtooth) | P2, heat-transfer fouling form |
| **SF-04** | Aero-derivative gas-turbine generator set — multi-component efficiency and flow degradation | surface | 2010 | **Multi-component modifier drift under multiple operating regimes** | P1 — C-MAPSS / N-CMAPSS |
| **SF-05** | Motor-operated valve actuator — stiction and torque-signature degradation | surface, subsurface, unmanned | 4810 | **Intermittent, partially self-resolving stiction episodes** | P2 |
| **SF-06** | Underwater electroacoustic transducer group — sensitivity loss and water ingress | subsurface, unmanned | 5845 | **Gradual sensitivity loss plus a large no-precursor failure fraction** | P2 |

**Spotlight item allocation — 249 items, within the ~250 target of §2.1:**

| Key | Surface (5 assets) | Subsurface (3) | Unmanned (4) | Total |
|---|---|---|---|---|
| SF-01 | 10 × 5 = 50 | 6 × 3 = 18 | 2 × 4 = 8 | 76 |
| SF-02 | 6 × 5 = 30 | 4 × 3 = 12 | — | 42 |
| SF-03 | 4 × 5 = 20 | 3 × 3 = 9 | — | 29 |
| SF-04 | 3 × 5 = 15 | — | — | 15 |
| SF-05 | 8 × 5 = 40 | 5 × 3 = 15 | 1 × 4 = 4 | 59 |
| SF-06 | — | 4 × 3 = 12 | 4 × 4 = 16 | 28 |
| **Total** | **155** | **66** | **28** | **249** |

Two properties of this allocation are deliberate and must survive any re-tuning. **Every domain carries at least three families**, so cross-domain population comparison is possible for more than one archetype. And **no family exists in only one asset**, because a family present on a single hull cannot support the cross-hull population comparison that the causal analysis depends on ([06 §7](../architecture/06-demo-decisions-and-assumptions.md)).

### 7.2 What "realistic" means per family

Each family's specification below states the trajectory form, the observable signature, and — most importantly — **the specific naive method the family must defeat**. A family that does not defeat at least one trivial method has failed its purpose, because the harness in §16 will then pass a baseline that should fail.

**SF-01 — bearing spall. Must defeat: linear trend extrapolation to a fixed threshold.**

- Stage 1, initiation: `T_init ~ Weibull(β, η)` with `β` in the wear-out range (bundle-owned, > 1 so a constant-rate baseline is measurably wrong), scaled by a load covariate and an item-level manufacturing-lot quality draw.
- Stage 2, propagation: defect area follows an accelerating power law `da/dt = C · a^m` with `m > 1`, so the trajectory is **hyperbolic, not linear** — the last 15% of life contains most of the observable change.
- Observable: vibration RMS in the defect band ∝ `a^0.5` with envelope modulation at bearing-defect frequencies and their sidebands; temperature rises only in the final fraction of stage 2 and only a few degrees above the load-explained baseline. A model that has not normalized for load will attribute load changes to degradation.
- **Required non-monotonicity: the run-in plateau.** After initial spalling, surface smoothing produces a real, documented temporary *decrease* in vibration amplitude before the final rise. A linear trend fitted through a plateau either misses the failure or fires early. This single feature is the main reason SF-01 exists.
- P-F interval: right-skewed lognormal. Its median and dispersion are bundle-owned, and the dispersion must be wide enough that a fixed lead-time rule cannot work.

**SF-02 — hydraulic wear with step failures. Must defeat: continuous-degradation assumptions and single-threshold alarms.**

- Clearance grows roughly linearly in cumulative pumped-hours × an abrasivity covariate; developed head degrades as a function of clearance.
- **The performance deficit is only observable at high flow demand.** At low demand the pump meets the requirement and looks healthy. Observability is therefore confounded with operating profile, and a model trained on in-port data will not transfer to underway data.
- Seal failure is a **step**: hazard rises with clearance, but the event is abrupt and the leak-rate channel jumps. A bundle-specified fraction of SF-02 failures have a continuous precursor and the remainder do not.

**SF-03 — fouling with resets. Must defeat: monotonic-degradation models and any trend fitted across a maintenance event.**

- Fouling resistance approaches an asymptote: `R(t) = R∞ · (1 − e^(−t/τ))`.
- **Cleaning at PMS periodicity resets `R` incompletely**, leaving a residual that accumulates across cycles. The signal is a sawtooth with a rising floor — so the useful feature is the *floor*, not the level, and a model fitted to the level sees repeated "recoveries" it cannot explain.
- The observable ΔT is strongly confounded by **seasonal seawater inlet temperature**, which the generator supplies as an environmental covariate with an annual cycle. A trend on raw ΔT tracks the season, not the fouling. This is the family that punishes un-normalized trending.

**SF-04 — multi-component efficiency drift. Must defeat: single-regime trending and unit-to-unit pooling.**

- Per-component efficiency and flow modifiers degrade with an exponential-in-cycles form after a randomized healthy period; sensor channels are nonlinear functions of `(operating condition, modifiers)`.
- **At least three operating regimes** are required (bundle-owned regime definitions), with regime-dependent sensor gain, so features must be regime-normalized.
- **Unit-to-unit initial wear variation** is required, so a fleet-pooled model without item-level random effects is measurably worse than one with them. This is the property that makes the tier-2/tier-3 distinction visible in the results.
- Failure is a composite margin crossing, not a single-channel threshold.

**SF-05 — intermittent stiction. Must defeat: fixed-window feature extraction and regularly-sampled assumptions.**

- Latent stiction state `S(t)` is a positive-drift random walk. Each actuation draws breakaway torque `τ_b = f(S) + noise`; failure is failure-to-stroke when `τ_b` exceeds actuator capability.
- **Observable only at actuation events**, which are irregular and driven by operations — so the sampling is event-driven, not periodic, and gaps carry information. A generator that emits SF-05 on a fixed grid has destroyed the family's entire purpose.
- **Lubrication and exercise events partially reset `S`**, producing genuine self-resolution. This creates unavoidable false-positive pressure: an alarm that fires on a rising `S` that then self-resolves is not a modeling error, and the adjudication rehearsal needs those cases to be real.

**SF-06 — sensitivity loss and water ingress. Must defeat: the assumption that all failures are predictable.**

- Gradual sensitivity decline in dB with depth-cycle and temperature dependence, plus discrete element dropouts.
- **A large fraction of SF-06 failures are abrupt water ingress with no precursor above noise.** The fraction is bundle-owned and substantial.
- This family exists to impose a **hard ceiling on achievable warning lead-time coverage**. Without it, the headline metric in [06 §2](../architecture/06-demo-decisions-and-assumptions.md) can approach 1.0 on synthetic data, which is exactly the flattery A1 warns about.

**The unpredictable fraction is a general requirement, not an SF-06 feature.** Every family — spotlight and long-tail — declares `unpredictable_fraction`: the share of true failures whose precursor is not detectable above the noise floor at any horizon. A fleet-wide floor is enforced by the `plan` stage, and the harness reports the **realized achievable ceiling** on lead-time coverage in the V&V report (§16.4, gate G-6). A dataset on which perfect prediction is possible is an invalid dataset.

### 7.3 Channel allocation and the many-to-many channel map

The §2.2 channel budgets are **per asset**, not per item, and the arithmetic matters: 40 surface spotlight channels against ~31 spotlight items per surface asset is roughly 1.3 channels per item. That is not a shortfall to be engineered around — it is the real condition, and it produces two properties the platform needs.

| Domain | Budget (§2.2) | Allocation | Consequence |
|---|---|---|---|
| Surface | 40 channels/asset at 1 Hz | ~8 items receive a **dedicated triple** (vibration, temperature, pressure or flow); the remaining ~23 items are served only by **shared** channels | Sensor availability varies *within* a family, so tier assignment differs between two instances of the same equipment |
| Subsurface | 150 channels/asset at 1/minute, burst on reconnect | ~22 items/asset, so most items receive a dedicated set at coarse cadence | Rich coverage, poor temporal resolution, and weeks-long delivery gaps |
| Unmanned | 100 channels at 10 Hz per sortie | ~7 items/asset — the densest per-item coverage in the fleet | Highest fidelity, shortest duty cycles, per-sortie discontinuity |

Two required properties fall out of this:

1. **Attribution ambiguity is real.** A shared channel — a lube-oil temperature serving both a bearing set and its cooler — means a degradation signature does not identify which item caused it. The generator emits the **many-to-many channel-to-item map** as data (`telemetry/channel_item_map`), and ground truth records which item actually caused each excursion. Any model that resolves attribution correctly has earned it.
2. **Sensor availability is a first-class covariate.** Partially-observed items are what make the instrumentation-investment business case in [06 §9.3](../architecture/06-demo-decisions-and-assumptions.md) demonstrable: holding criticality fixed and varying sensor availability requires items that differ in sensor availability alone. The generator produces matched pairs — same family, same duty, one instrumented and one not — and records the pairing in ground truth.

Additionally, **at least one channel per spotlight family is a decoy**: it correlates with the degradation state through a shared confounder (load, ambient temperature) without being caused by the fault. Spurious feature selection must have something to select.

### 7.4 The `FamilySpec` parameter schema

Every family — spotlight and long-tail — is fully described by this schema. **The schema lives in code (`families/spec.py`); the values live in the bundle (§4).** Any illustrative range mentioned in this document is non-authoritative; the bundle is the only source.

```yaml
family_key:              SF-01              # opaque. The ONLY family reference in code
nomenclature:            <generic functional string>       # bundle
taxonomy:
  eswbs_band:            <reserved synthetic band>
  fsc:                   <real FSC from 07 §4.8>
  smr:                   <6-position code; recoverability at position 5>
  cog:                   <2S | 7H | 3H | 1H | 9N | ...>
  iso14224_failure_modes: [<code>, ...]      # per 08 §2.4 anchoring
population:
  domains:               [surface, subsurface, unmanned]
  items_per_asset:       {surface: 10, subsurface: 6, unmanned: 2}
  population_basis:      equipment_count | platform_count   # 07 §5.5. See §11.2
reliability:
  form:                  weibull | two_stage | lognormal
  shape_beta:            <bundle>           # must be > 1 for wear-out families
  scale_eta_days:        <bundle>
  covariates:            [load, ambient_temp, duty_cycle, lot_quality, ofrp_phase]
  covariate_effects:     {<covariate>: <coefficient>}
  lot_quality:           {n_lots: <int>, dispersion: <bundle>}
  unpredictable_fraction: <bundle>           # §7.2. Floor enforced by `plan`
degradation:
  archetype:             bearing_spall | hydraulic_wear_step | fouling_reset |
                         multicomponent_efficiency | stiction_intermittent |
                         sensitivity_loss_ingress
  archetype_params:      {<per-archetype, see §7.2>}
  pf_interval:           {form: lognormal, median_days: <bundle>, sigma: <bundle>}
  reset_behavior:        none | partial_reset | full_reset   # SF-03 uses partial_reset
  observability:         periodic | event_driven            # SF-05 uses event_driven
channels:
  - channel_key:         <opaque>
    quantity:            vibration_rms | temperature | pressure | flow | torque |
                         sensitivity_db | leak_rate | efficiency_proxy
    role:                primary | secondary | decoy
    sharing:             dedicated | shared
    domain_rates:        {surface: 1Hz, subsurface: 1/min, unmanned: 10Hz}
    signal_map:          <archetype state -> channel value transform>
noise:                   {<the ten stages of §9, each with its parameters>}
maintenance:
  pms_periodicity_days:  <bundle>
  mdt:                   {form: lognormal, median_days: <bundle>, sigma: <bundle>}
  findings_codes:        [<3-M CAUSE / WHEN DISCOVERED / ACTION TAKEN values>]
  status_2_3_propensity: <bundle>            # feeds the §2.3 ~25% constraint
supply:
  apl_category:          <reserved category pair>
  nha_family_key:        <family_key | null> # non-null required where SMR source is XA
  repairable:            true | false        # derived from SMR recoverability D/L vs Z
  unit_price_cents:      <bundle>            # implied two decimals
  brf_seed:              <bundle>            # §12.1 — the initial replacement factor
provenance:
  parameter_classes:     {<param>: P1|P2|P3} # P4 rejected by the loader (§4.3)
  domain_transfer_note:  <required where any P1 is present>
```

`plan` validates every `FamilySpec` against this schema and **fails on any missing field.** There is no default for any physics or reliability value, for the reason in §4.4: a default would put a reliability constant into artifact 1.

### 7.5 Active windows, duty cycling, and the row budget

Sample-level generation is gated by three conditions in order, and a sample exists only when all three hold:

1. **The asset is operating** — underway, on patrol, or on sortie, per the mission calendar (§7.6).
2. **The equipment is energized** — per a family duty-cycle model. A fire pump does not run continuously.
3. **The timestamp falls inside an active window** — either *mission-anchored* (a bounded window at mission start and end, where post-mission analysis operates) or *degradation-anchored* (a window preceding and following each true onset and each true failure, so the interesting physics is captured at full rate).

Outside active windows the same channel emits **1-minute aggregates** (mean, min, max, count, and a completeness flag). Long-tail items emit **1-hour aggregates** only (§11).

`budget.py` runs during `plan`:

- Computes the projected row count per `(domain × family × fidelity)` cell.
- **Fails the build** if the projected spotlight total exceeds the §2.2 budget of ~1.5×10⁹ rows before rollup, or the long-tail total exceeds ~4×10⁷.
- Emits the realized allocation into the data card, so the fidelity claim is quantified rather than asserted.

Window widths and the deep-fidelity sortie fraction are **OPD-3** in §21: 06 §7 marks the row-count figure LOW confidence, so the budget is a constraint to be honored and the window parameters are the free variables that honor it.

**Completeness is recorded, never inferred.** Per 04 §3's ingest design, every batch and mission carries a completeness record so a consumer can distinguish *"no fault observed"* from *"not observed."* A generator that emits gaps without completeness metadata has manufactured a silent bias in every downstream label.

### 7.6 The mission calendar

Generated first, because everything else is conditioned on it. Per month across the fleet: **5 surface underway periods, 1 submarine patrol, ~64 unmanned sorties — ~70 missions** ([06 §6](../architecture/06-demo-decisions-and-assumptions.md)).

- **Underway periods are staggered, not independent.** §2.2's reconciliation requires it to land the ~5M samples/day live rate, and OFRP phasing is the operationally correct reason for it. `RunConfig` carries the maximum concurrent-underway count; the calendar generator respects it.
- **6 availabilities across 24 months, including 1 DSRA** ([06 §7](../architecture/06-demo-decisions-and-assumptions.md)). An availability suppresses operation, resets deferred maintenance in bulk, and is the natural home for the opportunistic-intervention driver in §8.4.
- OFRP phase is an emitted covariate on assets and a covariate in family reliability models, because maintenance opportunity and operating severity both track it.
- Submarine missions produce **no telemetry delivery until reconnect** (§9.6, §15).

---

## 8. The causal core — failure process, intervention policy, and censoring

This is the single most important mechanic in the generator. [05 D1](../architecture/05-architecture-review-findings.md) states the problem: *prediction-driven preventive replacement censors exactly the items about to fail*, every stated method assumes non-informative censoring, and over time *observed failures become a biased low-hazard subsample, fitted MTBF rises, `p_failure` decays, and the fleet drifts back to run-to-failure* — with every feedback signal pointing the wrong way and nothing detecting it. [06 §2](../architecture/06-demo-decisions-and-assumptions.md) makes the response a design commitment: a policy-frozen holdout, statistical correction, and **counterfactual ground truth retained by the generator so that what the corrected estimator recovers can be measured exactly against truth.**

That is only possible if the generator gets the causal semantics exactly right. The requirement is precise and narrow:

> **Simulate the intervention policy as a process that is separate from, and downstream of, the underlying failure process. The policy may consume anything a real maintenance system could observe. The policy may never alter, truncate, or inform the ground truth.**

### 8.1 Two processes, one composition

| | Failure process (stage `truth`) | Intervention policy (stage `policy`) |
|---|---|---|
| **Owns** | `T*` (true failure time), degradation onset, the P-F interval, the complete trajectory | Intervention times, drivers, and the simulated prediction stream |
| **Reads** | Plan, configuration, parameter bundle, environmental covariates, mission calendar | Plan, configuration, and the **observable projection only** (§8.3) |
| **Writes** | `truth/`, sealed and hash-manifested | Intervention schedule, `policy_version` |
| **May import** | Nothing from `policy/` | Nothing from `truth.failure_process`; only `veil.GroundTruthVeil` |
| **Runs** | First, to completion, sealed before stage 4 begins | Second, against a read-only sealed artifact |

The observable record is then **composed**, in stage `observe`:

```
observed_event_time  = min(T*, C_policy, C_admin, C_mission_end)
observed_event_type  = failure                 if T*        is the minimum
                       preventive_replacement  if C_policy  is the minimum
                       admin_censor            if C_admin   is the minimum   (end of the 24-month window)
                       mission_end_censor      if C_mission_end is the minimum (unmanned per-sortie)
```

`T*` is **always retained** in `truth/`, whether or not it was ever reached. The trajectory is **always continued past the intervention** to `T*` and beyond, and stored as the counterfactual — because "what would have happened" is the quantity the corrected estimator is trying to recover, and it must exist as data for the recovery to be measurable.

### 8.2 Ordering is enforced by artifact sealing, not by convention

A comment saying "draw truth first" is not a control. The stage boundary is:

1. `truth` draws every `T*`, every onset, and every trajectory, writes them, computes a Merkle manifest over the partition, and writes `truth/MANIFEST.sha256`.
2. The manifest is **verified at the start of stage `policy` and again at the start of stage `observe`.** A mismatch aborts the run. If a policy decision had written back into truth, the manifest would not verify.
3. `truth/` is opened read-only thereafter. In the containerized run this is a read-only mount; locally it is chmod-enforced and manifest-verified.

The consequence to internalize: **the policy cannot retroactively change what was going to happen, because what was going to happen is already sealed and hashed by the time the policy runs.** That is what makes the counterfactual credible rather than merely claimed.

### 8.3 The veil — the only interface between truth and policy

`veil.GroundTruthVeil` is a sealed adapter. It is the only symbol from the truth partition that `policy/` may import, and it exposes exactly one method family:

```python
class GroundTruthVeil:
    """Observable-only projection of the truth partition.

    Exposes what a real maintenance system could see at time t and nothing else.
    Every method takes `t` and is monotone in it: no method returns information
    dated after `t`, for any t.
    """
    def channel_samples_up_to(self, item_id, t) -> Samples: ...      # POST-noise (§9) values only
    def maintenance_history_up_to(self, item_id, t) -> Records: ...  # with label noise applied
    def usage_counters_up_to(self, item_id, t) -> Counters: ...
    def pms_schedule(self, item_id) -> Schedule: ...
    def predictions_up_to(self, item_id, t) -> Predictions: ...      # None if policy_frozen (§10.3)
```

Five prohibitions, each enforced by a mechanism rather than by care:

| Prohibition | Mechanism |
|---|---|
| The policy cannot read `T*`, onset, the P-F interval, or the noise-free signal | Those fields are not reachable through the veil. `truth.store` exposes no public reader other than the veil constructor |
| The policy cannot read any value dated after `t` | `t`-monotonicity is a property test: for random `(item, t1 < t2)`, every method's result at `t1` is a prefix of its result at `t2` (§18.3) |
| The policy cannot import the failure process | `importlinter.ini` forbids `fathom_synth.policy.* -> fathom_synth.truth.failure_process`, `.trajectory`, `.canaries` |
| The policy cannot see pre-noise channel values | The veil reads the post-noise partition. Stage `observe` writes noise for the *policy-visible* prefix before the policy consumes it; the pipeline interleaves per time-step rather than generating all noise afterward |
| Nobody can quietly widen the veil | Any change to `veil.py`'s public surface requires the harness's gate **G-4** (ground-truth leakage probe, §16.4) to be re-run and its result recorded in the V&V report. The gate is CI-blocking |

**Adversarial self-test of the veil.** `tests/test_veil_cheating.py` constructs a deliberately cheating policy variant that reads `T*` directly, runs a reduced dataset through it, and **asserts that gate G-4 fails**. A harness that cannot detect a cheating policy cannot certify an honest one, so this test guards the guard. It is a required test, not an optional one.

### 8.4 The intervention policy

`policy/intervention.py` simulates a maintenance system. It runs forward in time on a daily step and emits interventions with a recorded driver. Every emitted maintenance action carries the three treatment-record fields already implemented in [03 rev 2](../architecture/03-integration-contracts.md) and required by [06 §2](../architecture/06-demo-decisions-and-assumptions.md): `triggering_driver`, `triggering_prediction_id`, and `policy_version`.

| `triggering_driver` | Trigger | Eligible on holdout items? |
|---|---|---|
| `pms_periodicity` | Unmodified PMS interval reached | **Yes** |
| `casualty` | The item has actually failed — a corrective action | **Yes** |
| `prediction` | A simulated prediction crossed the policy's action threshold | **No (§10.3)** |
| `opportunistic` | An availability or another work item opened access, and a prediction contributed to the decision | **No** |
| `opportunistic_pms` | An availability opened access and only periodicity contributed | Yes |

Policy properties that must hold:

- **`policy_version` changes at least once during the 24 months.** A single frozen policy makes propensity modeling trivially easy and hides the versioning requirement; a policy shift partway through the window is both realistic and necessary to exercise `policy_version` as a covariate.
- **The policy's action threshold is imperfect.** It acts on the simulated prediction stream, which is itself noisy, so the policy sometimes intervenes on a healthy item and sometimes misses a degrading one. A policy with perfect discrimination produces a degenerate propensity model.
- **The policy has capacity limits.** Interventions compete for maintenance opportunity: a bounded number per asset per in-port period, subject to parts availability from §12. Interventions therefore queue, and the queue is a confounder that a naive analysis will miss — which is the point.
- **The policy records what it saw.** For every intervention and every non-intervention decision at threshold, `policy/` writes the decision inputs into the truth partition's `policy_inputs` table (written by stage `policy` into its own partition, then merged into `truth/` read-only after sealing of the failure-process partition). Without the decision inputs, the correct propensity model is not identifiable even in principle, and the demonstration cannot show a corrected estimator recovering truth.
- **An intervention creates a replacement item** with a new `installed_item_id`, new IUID, zero usage, and an independently drawn `T*` (§5.3 rule 3).

### 8.5 Informative censoring is a required output, not a side effect

This inverts the usual quality criterion, so it is stated flatly: **if the generated dataset does not exhibit informative censoring, the generator has failed.** The demonstration's central methodological claim — a naive estimator drifting toward run-to-failure against a corrected estimator holding calibration, with generator ground truth as the referee ([06 §2](../architecture/06-demo-decisions-and-assumptions.md)) — requires the bias to be present and measurable.

Mechanism: because the policy preferentially removes items with short residual life, the surviving observed-failure set is a biased low-hazard subsample. The generator does not add this bias; it emerges from the two-process design. But it must be **verified to emerge**, at sufficient magnitude, and that is harness gate **G-5** (§16.4):

- Fit a naive Weibull MLE treating all censoring as non-informative, on the observed record.
- Fit the same estimator on the truth record, where every `T*` is known.
- **Assert that the naive fit's MTBF is inflated relative to truth by a margin that is statistically significant** at α = 0.05 by a bootstrap over items, per spotlight family and fleet-wide.
- **Assert the drift direction over time**: the naive fit's MTBF estimated on an expanding window must trend upward over the 24 months. That is the drift D1 describes, and seeing it in the synthetic data is the proof that the demonstration has something real to correct.

The *magnitude* threshold — how much inflation is enough to make the correction visibly worth having — is **OPD-4** in §21. The significance test is derivable and prescribed; the practical-significance margin is a program decision.

### 8.6 The truth partition is withheld, structurally

The ground-truth partition is the most dangerous artifact this generator produces, because a single accidental join makes every downstream metric meaningless while leaving no visible symptom.

| Control | Implementation |
|---|---|
| Separate location | `s3://fathom-synthetic/<dataset_id>/truth/` — a distinct prefix with its own bucket policy |
| Separate credential | Training, scoring, and feature pipelines run under a role with **no read permission** on `truth/`. Evaluation runs under a distinct role that can read `truth/` and **cannot write** to any observed partition |
| Distinct file naming | Every truth file is named `*.truth.parquet`, so a glob written by a hurried engineer does not silently pick it up |
| Schema-level marking | Every truth table carries a required column-level annotation `withheld: true` in `schema/ground_truth.schema.json`, and the readers in `packages/py-common` refuse to load a table so annotated unless constructed with an explicit `EvaluationContext` |
| CI check | A repository-wide scan fails the build if any file outside `harness/` or an evaluation notebook references a `*.truth.parquet` path or the truth prefix (§18.3) |
| Data card declaration | The card names the truth artifact and states that it is withheld, so a downstream consumer knows it exists and knows it is not theirs |

### 8.7 The ground-truth record schema

Declared normatively in `schema/ground_truth.schema.json`. One row per installed item per lifetime.

```yaml
# ── identity
installed_item_id            # UUID, the join key
asset_id, domain, position_id, family_key, niin
predecessor_item_id          # null for the first item in a position
# ── the failure process (never influenced by policy)
true_failure_time            # T*. ALWAYS populated, even when intervention preceded it
true_failure_mode            # taxonomy code + taxonomy_version (03 §14)
degradation_onset_time       # the P in the P-F interval
potential_failure_time       # the F. MIL-STD-3034A §3.9.3 term (08 §9)
pf_interval_days             # derived, retained for convenience
precursor_detectable         # false for the unpredictable_fraction (§7.2)
trajectory_ref               # object key: the full noise-free trajectory to T* and beyond
# ── the observable composition
observed_event_time
observed_event_type          # failure | preventive_replacement | admin_censor | mission_end_censor
censoring_reason
censored_informatively       # true where the policy acted on a degradation signal
residual_life_at_censoring   # T* - observed_event_time. The counterfactual quantity of interest
# ── the treatment record
intervening_policy_version
triggering_driver            # §8.4
triggering_prediction_id     # null unless driver = prediction | opportunistic
intervention_decision_inputs_ref
# ── holdout and canary
policy_frozen                # §10
holdout_stratum              # null unless policy_frozen
canary                       # §13
canary_injection_id
# ── attribution and reproducibility
causing_item_for_shared_channel   # §7.3 attribution ambiguity resolution
instrumentation_match_pair_id     # §7.3 matched instrumented/uninstrumented pair
seed_lineage                 # (master_seed, stream_path) — regenerates this item alone (§18.1)
parameter_bundle_digest      # the ONLY parameter reference in any row (§4.2)
```

`residual_life_at_censoring` is the column the entire causal-validity demonstration turns on. It is defined for every intervened item and is unavailable in production by construction — which is [06 §2](../architecture/06-demo-decisions-and-assumptions.md)'s stated reason the holdout exists at all.

---

## 9. Noise and corruption — the ten-stage pipeline

The second of the three places this generator goes wrong. [06 §7](../architecture/06-demo-decisions-and-assumptions.md)'s A1 mitigation names four requirements — *inject realistic sensor noise, drift, dropout, and mislabelled maintenance records* — and this section turns them into an ordered, parameterized, ablatable pipeline so that "we added noise" is a measurable claim rather than an assurance.

### 9.1 Rules that govern the whole pipeline

1. **The order is fixed and is part of the specification.** Noise is not commutative: quantizing before adding drift is a different dataset than the reverse. `noise/pipeline.py` applies stages 1 → 10 in order, and the order is asserted by test.
2. **Every stage is individually switchable**, because the harness's ablation gate (§16.3) depends on being able to disable all of them.
3. **Every stage's parameters live in the bundle**, keyed by `(family_key, channel_key, domain)`. No magnitude appears in generator code.
4. **Noise is applied to the policy-visible prefix before the policy consumes it** (§8.3). The simulated maintenance system sees the same corrupted data a real one would.
5. **The noise-free trajectory is retained in `truth/`** so the harness can quantify signal-to-noise per family and report the achievable ceiling (§7.2).
6. **No stage may be tuned to make a model perform better.** Parameters are set from provenance (§4.3) and then left alone. If a downstream model performs poorly, that is a finding about the model, not a reason to clean the data. This rule is what A1 is actually about, and it is restated in §19.

### 9.2 Stage 1 — sensor transfer

Applied per channel, in this sub-order: **static bias → sensitivity (scale) error → range clipping → quantization.**

- Static bias and sensitivity error are drawn **once per channel instance** and are persistent, so per-item calibration offsets are a real, learnable nuisance.
- Range clipping means an extreme excursion saturates rather than reading its true value. A model that extrapolates from a clipped peak is wrong, and clipped peaks are common in real vibration data.
- Quantization uses a bundle-specified ADC bit depth. Quantization matters most where the useful signal is small relative to the range — which is exactly the early-degradation regime.

### 9.3 Stage 2 — stationary noise

Additive per-sample noise with **two components**: Gaussian with per-channel σ expressed as a fraction of nominal, plus a **1/f (pink) component**. Pink noise is required and is not decoration: white-only noise is trivially removed by averaging, which makes early detection easier on synthetic data than on real data. Getting this wrong is one of the quieter ways to build an over-clean dataset.

### 9.4 Stage 3 — time-correlated drift

A random-walk calibration drift per channel, with **partial resets at PMS calibration events**. Two consequences must be visible in the data: a slow drift indistinguishable from slow degradation over short windows, and a **step at recalibration** that is not a physical change. Any detector that treats steps as events must contend with recalibration steps.

### 9.5 Stage 4 — operating-condition confounding

**The most important stage in the pipeline.** Channel values depend on operating condition — load, ambient and seawater temperature (with an annual cycle), speed, depth, sortie profile, OFRP phase — with family-specific sensitivity. The degradation contribution is often *smaller* than the operating-condition contribution.

This is what makes C-MAPSS hard and what most hand-rolled synthetic datasets omit. Requirements:

- Confounding magnitude is bundle-owned and, for at least SF-03 and SF-04, must **exceed** the degradation signal magnitude over a substantial portion of life.
- The operating-condition covariates are **emitted as data**, so normalization is possible for a model that does the work.
- At least one confounder is **only partially observable** — its proxy channel is noisy — so perfect normalization is not achievable.

### 9.6 Stage 5 — dropout and gaps

Four distinct mechanisms, all required:

| Mechanism | Behavior |
|---|---|
| Per-sample dropout | Bernoulli at a bundle rate; the sample is absent, not zero |
| Burst dropout | A two-state Markov chain producing correlated outage runs — the realistic form for comms and multiplexed acquisition |
| Whole-channel outage | A channel fails for a period. **Includes stuck-at-value faults**, where the channel reports a plausible constant. Stuck sensors are a distinct fault class and are labeled as **sensor** faults in truth, never as equipment degradation — a model that predicts equipment failure from a dead sensor is making the error this case exists to expose |
| Domain-structural gaps | Subsurface channels deliver **nothing until reconnect** (§15); unmanned channels exist only within sorties; surface channels are gated by §7.5's active windows |

Absence is always accompanied by a **completeness record** (§7.5).

### 9.7 Stage 6 — impulses and artifacts

Heavy-tailed impulse contamination at a bundle rate (isolated extreme samples with no physical cause), plus frozen-value runs shorter than a stage-5 outage, plus occasional duplicated samples. Robust statistics must have something to be robust against.

### 9.8 Stage 7 — timebase corruption

Aligned with [03 §5.4](../architecture/03-integration-contracts.md), which is a mandated-behavior problem rather than a hypothetical: the Ubuntu 22.04 STIG rule V-260520 requires `makestep 1 -1`, so a **backward clock step fires precisely when a disconnected node reconnects and drains its outbox.**

- Per-sample timestamp jitter.
- **Backward clock steps at reconnect**, with `clock.step_occurred = true`.
- `sync_quality` fully populated on every emitted batch: `time_source` cycling through `gnss | upstream_ntp | holdover | unsynced`, `offset_ms`, and a **`dispersion_ms` that grows monotonically while disconnected** — and for the six-week scenario in §15 it must grow to exceed the inter-write interval, which is the condition that forbids timestamp arbitration entirely.
- Ordering keys are always correct even when wall clocks are not: `(producer, monotonic_seq)` and the HLC are internally consistent, because they are what consumers must use. A generator that corrupts the monotonic sequence is testing a different failure than the one the architecture addresses.

### 9.9 Stage 8 — cross-channel structure

Per-channel independent noise is unrealistically easy to average away. Required:

- **Correlated noise** via a bundle-specified covariance across channels sharing an acquisition unit or a physical space.
- **Common-mode excursions** — a power transient moves several channels at once, resembling a fault and being none.
- **The decoy channel** of §7.3 is realized here: it tracks the degradation state through a shared confounder while having no causal relationship to the fault. Contributing-factor attribution ([03 §7.1](../architecture/03-integration-contracts.md): attribution method plus a stability measure, suppressed below a stability threshold) needs a genuine trap to demonstrate that it resists.

### 9.10 Stage 9 — label and record corruption

The maintenance record side, and the requirement A1's mitigation names explicitly. Rates are bundle-owned; every corruption is recorded in truth so that label quality is measurable rather than merely present.

| Corruption | Realistic cause | Downstream effect it forces |
|---|---|---|
| Wrong findings code | Deckplate coding under time pressure | Findings-based labels are noisy, so actionable precision has a ceiling ([06 §2](../architecture/06-demo-decisions-and-assumptions.md) A5) |
| **Wrong-item attribution** | Action recorded against a sibling position | Item-level labels are sometimes attached to the wrong physical item — the defect that position-versus-item confusion produces `[C10]` |
| Date rounding | Recorded at end of shift, or on the next in-port day | Failure timing is coarser than telemetry timing, so lead-time computation must handle interval-censored event times |
| Missing parts record | `UN`/`UF`/`UP` record absent | `MAINT_EFFECT` ([07 §5.7](../architecture/07-navy-data-systems.md)) cannot be computed for some actions |
| Narrative-code inconsistency | Free text disagrees with the coded fields | The retrieval and agent surfaces meet genuinely contradictory evidence |
| Duplicate 2-Kilos | Same job written twice with different JSNs | Deduplication is required, and naive counting inflates failure rates |
| Corrective/preventive misclassification | The determination is a judgment | The single most damaging label error, because it directly corrupts the supervised signal ([06 §9.2](../architecture/06-demo-decisions-and-assumptions.md) Tier A) |
| Missing `triggering_driver` | Field not captured | The propensity model must handle missingness in the treatment record, which is the realistic production condition |

**Findings coding uses the real 3-M projections and carries the ambiguity as data.** Per [03 §14](../architecture/03-integration-contracts.md), 3-M CAUSE is a *cause* code rather than a *mode* code, so one findings record maps to a **set** of candidate modes: the generator emits `candidate_modes[]` with confidence, never a single forced code, and every label carries `taxonomy_version`. Normalizing to one code on write destroys the disagreement signal that the three capture points exist to produce.

### 9.11 Stage 10 — missing not at random

Dropout probability is **correlated with the degradation state**: instrumentation in a hot, vibrating, degraded space fails more often than instrumentation on a healthy machine. This means missingness carries information about the label, so imputation choices change results and a complete-case analysis is biased. It is the most sophisticated stage in the pipeline and the one most often absent from synthetic data.

The correlation coefficient is bundle-owned and must be non-zero for every spotlight family. The harness reports the realized correlation in the V&V report so the property is documented rather than assumed.

### 9.12 The two-sided corridor

Noise injection has two failure modes, not one, and the pipeline must be validated against both:

- **Too clean** — trivial baselines succeed, models look excellent, the demonstration misleads. This is A1.
- **Too noisy** — nothing works, the data is unlearnable, and the tiered-modeling story cannot be told at all. This failure mode is less discussed and equally fatal to the demonstration.

The harness therefore enforces a corridor from both sides (§16.3, gates G-1 and G-2): with noise **disabled**, trivial baselines *must succeed* — proving a learnable physical signal exists; with noise **enabled at shipped settings**, trivial baselines *must fail* and a reference tier-2/3 model *must still clear a floor*. Neither half of that statement is optional.

---

## 10. The policy-frozen holdout

[06 §2](../architecture/06-demo-decisions-and-assumptions.md): **10% of installed items, stratified across equipment families and all three domains, maintained on unmodified PMS periodicity and excluded from prediction-driven intervention.** In the demonstration it is simulated; the mechanism is identical to the production design, and 06 §9.2 records it as a Tier B program requirement on the enterprise (a TYCOM instruction or CBM+ implementation policy).

### 10.1 Selection

- **~840 items — exactly 10% of the ~8,400** installed items. The percentage is exact; the count follows the realized item total.
- **Stratified across equipment families and all three domains.** Allocation is proportional by `(family_key × domain)` cell, with a **floor of 3 items per cell** where the cell exists, so no family is unrepresented.
- Selection is by **position**, not by item, and holds for the position's entire install history. Otherwise a replacement would silently leave the holdout mid-window and the stratum would not be policy-frozen at all — it would be policy-frozen only until the first intervention, which is the exact opposite of the design.
- Selection is deterministic from the seed tree (§18.1) and is written to `holdout/manifest.parquet` with a digest recorded in the data card.
- **Holdout items are otherwise ordinary.** Same physics, same noise, same parameters. The only difference in the world is which interventions the policy is permitted to make.

**A thinness to state plainly.** 10% of ~250 spotlight items is ~25 items — below the n ≥ 50 item-horizon calibration gate of [06 §3](../architecture/06-demo-decisions-and-assumptions.md) for most per-family cells. The spotlight holdout therefore supports the **aggregate** bias-and-correction demonstration but **not per-family calibrated estimates**. 06 §2 anticipates this (*a 10% holdout is statistically sufficient* — MEDIUM confidence, *too small for rare ones*) and offers stratification by base rate as the alternative. **OPD-5** in §21 records the available move: hold the fleet-wide 10% fixed as 06 §2 requires while re-weighting *within* it to over-sample spotlight families and low-rate families. That is a program decision because it trades long-tail holdout coverage for spotlight statistical power.

### 10.2 Marking

`policy_frozen: true` appears in three places, and all three must agree — an agreement the harness asserts:

| Location | Purpose |
|---|---|
| `configuration/positions` and `configuration/installed_items` | So every consumer of configuration knows, without a join to an evaluation artifact |
| `holdout/manifest.parquet` | The authoritative list, with `holdout_stratum` and the selection seed |
| `truth/` (§8.7) | So evaluation can partition by stratum |

The flag is **visible to consumers on purpose.** A hidden holdout is not implementable in production — a TYCOM instruction that designates a reference population necessarily makes the designation visible — and hiding it in the demonstration would demonstrate a mechanism the Navy could not adopt.

### 10.3 Exclusion is an admission filter, not a branch in the ranking logic

This is the implementation rule that matters. The naive approach — score everything, then skip holdout items when acting — leaves a prediction-shaped hole that any subsequent refactor can fill. Instead:

```python
# policy/holdout.py — applied at the policy's INPUT boundary
def visible_predictions(item, t, veil):
    if item.policy_frozen:
        return []                      # not filtered later. Never loaded.
    return veil.predictions_up_to(item.item_id, t)
```

Consequences, all enforced:

1. `GroundTruthVeil.predictions_up_to` returns empty for a policy-frozen item, so the prediction stream for holdout items is not merely unused — it is unreachable by the policy.
2. The only drivers reachable for a holdout item are `pms_periodicity`, `casualty`, and `opportunistic_pms`. The `prediction` and `opportunistic` drivers cannot be constructed, because their construction requires a prediction object the policy never received.
3. **Post-generation audit assertion** (§18.2, and harness gate G-7): zero maintenance actions on policy-frozen items carry `triggering_driver ∈ {prediction, opportunistic}`, and zero carry a non-null `triggering_prediction_id`. The assertion is over the emitted rows, so it holds regardless of how the policy was implemented.
4. **The holdout's failures are generated normally.** Holdout items fail at their true `T*` far more often than treated items do, because nothing intervenes early. That is the entire value of the stratum: an uninfluenced failure-time distribution to compare the corrected estimator against.

### 10.4 What the holdout makes measurable

| Quantity | How | Available in production? |
|---|---|---|
| True failure-time distribution, untreated | Directly from the holdout stratum's observed record | **Yes** — this is why the holdout is designed rather than simulated |
| Bias of the naive estimator | Naive fit on treated items vs. holdout fit | Yes |
| Recovery of the corrected estimator | IPCW plus propensity-corrected fit vs. holdout fit, **and** vs. full generator truth | Partially. The comparison against generator truth is demo-only, and is the reason the counterfactual is retained ([06 §2](../architecture/06-demo-decisions-and-assumptions.md)) |
| Estimated CASREPs avoided | On the holdout stratum only, with a confidence interval, **labelled as an estimate** | Only with the holdout — 06 §2 makes this the secondary metric for exactly this reason |

---

## 11. The long-tail statistical engine and the maintenance record layer

~114 of ~120 families, and roughly 8,150 of ~8,400 installed items, are generated **without underlying sample-level telemetry**. [06 §7](../architecture/06-demo-decisions-and-assumptions.md) anticipates this explicitly as the response to A4: *generate failure and maintenance history without underlying telemetry for non-spotlight items, which tiers 0–1 do not require.*

The design rule for this engine: **generate from the Navy's own reliability mathematics, not from an arbitrary distribution.** [07 §5.5](../architecture/07-navy-data-systems.md) publishes the formulas verbatim, and using them is *a cheap, high-credibility choice* that makes the platform's estimates directly comparable to the Navy's own. It also produces a property no arbitrary distribution gives us: a tier-0 fit performed with the Navy formula **recovers the seeded parameter**, which turns tier-0 correctness into a checkable assertion (§16.4, gate G-8).

### 11.1 The formulas, exactly as documented

```
Ao      = Uptime / (Uptime + Downtime)
T(pf)   = MTBF / (MTBF + MDT)
MTBF    = 1 / (Failures / (30.44 × 0.667 × Population))     [days]
```

`30.44` is days in an average month; **`0.667` is the sea-going operating-tempo approximation** — the Navy's own statement that for sea-going systems operating tempo is approximated as 2/3 of calendar time. Their product, **20.30 operating days per calendar month**, is the constant the generator uses. It appears in exactly one place, `longtail/navy_reliability.py`, as `OPERATING_DAYS_PER_MONTH = 30.44 * 0.667`, written as the product of its two documented factors so that its provenance is legible in the code.

### 11.2 Generation is the formula inverted

Given a family's seeded `MTBF_days` and its installed `Population`, the expected monthly failure count is:

```
E[failures per calendar month] = 30.44 × 0.667 × Population / MTBF_days
```

The generator draws each month's failure count as **Poisson** with that mean, allocates events to items with hazard weighting by usage and covariates, and then assigns each event a date within the month conditioned on the mission calendar (failures cluster in operating time, not calendar time — which is what the 0.667 factor encodes).

**`Population` follows the documented split.** [07 §5.5](../architecture/07-navy-data-systems.md): population is *actual equipment count for large HM&E, or platform count for small HM&E such as pumps and valves.* `FamilySpec.population.population_basis` carries `equipment_count` or `platform_count` per family, and the generator uses the declared basis. This is not a detail: a tier-0 fit using platform count against data generated with equipment count disagrees with the seeded MTBF by the average per-platform quantity, and the resulting mismatch looks exactly like a modeling defect.

**Tier-0 recoverability is an assertion.** For every long-tail family, a Weibull and an MTBF fit performed on the generated record must recover the seeded `MTBF_days` within the Poisson confidence interval implied by the family's realized event count. Families whose event count is too small for the interval to be informative are reported as **"not powered"** rather than passed silently (§16.4).

**Shape matters.** `shape_beta` must be greater than 1 for wear-out families, because if every long-tail family is effectively exponential then a constant-rate baseline is *correct* and tier 0 has nothing to demonstrate. A bundle-specified minority of families are genuinely random-failure (β ≈ 1) — that population is real, and it is also the population 06 §7's tier model assigns to tier 0 deliberately.

### 11.3 MDT, and why it must be coupled to supply

MDT is documented as *"the mean number of days from the opening of Status 2 or 3 2-Kilos until the CASREPs are corrected and the 2-Kilos closed. MDT is all-inclusive"* ([07 §5.5](../architecture/07-navy-data-systems.md)). **All-inclusive means it includes awaiting-parts time.**

So MDT cannot be an independent draw. The generator composes it:

```
MDT = administrative_delay + maintenance_labor_time + AWAITING_PARTS_TIME + verification_time
```

where `AWAITING_PARTS_TIME` comes from §12's supply simulation — zero when the part was on board per the SNSL allowance, and a requisition lead time when it was not. The consequences are the ones the program exists to create: **`Ao` and `T(pf)` become emergent properties of the allowance quality**, and improving allowance accuracy visibly improves availability. If MDT were an independent draw, the platform's entire supply value proposition would be invisible in its own demonstration data.

`Ao` and `T(pf)` are **never generated directly.** They are computed from the emitted records, and the harness verifies that recomputing them from the observed corpus reproduces the intended family values within tolerance.

### 11.4 Long-tail telemetry

Long-tail items emit **1/hour aggregates only** — the tier that §2.2's ~4×10⁷ long-tail row figure corresponds to. Per aggregate row: mean, min, max, sample count, completeness flag, and the operating-condition covariates. That is sufficient for tier-1 survival models with usage and environmental covariates and insufficient for tier-2 degradation trending, which is the correct and intended distinction.

Usage counters are emitted for all items regardless of tier: steaming hours, engine operating hours, sortie hours, cycles, dives — domain-specific units under the common `UsageCounter` shape (01 §6). Counter epochs and the reset semantics of [03 §11](../architecture/03-integration-contracts.md) are exercised in §15.

### 11.5 The maintenance record layer

Applies to spotlight and long-tail alike. ~14,000 maintenance actions over 24 months, with the §2.3 mix constraint.

**2-Kilo-shaped records** per the layout in [07 §5.3](../architecture/07-navy-data-systems.md), treated as *structurally indicative but historical* — the current data element dictionary and the modern 120 Card Format are NOT PUBLICLY FOUND, and the generator says so in the data card rather than inventing them:

| Record type | Generated content |
|---|---|
| `B1` deferred maintenance action | `1-5 UIC` · `6-9 WC` · `10-13 JSN` (`1-13` = JCN) · `14-17 ACTN DATE` · `57-63 EIC` · `64 WND` · `65 STA` · `66 CAS` · `67 DFR` · `79-80 record type` |
| `C5` closure | `1-5 UIC` · `6-9 WC` · `10-13 JSN` · `14-17 ACTN DATE` · `45-46 SFAT` · `47-50 MHRS` · `58 TI` |
| `M1` / `M5` | Non-deferred action and closure |
| `BA`–`BT`, `CA`–`CT`, `MA`–`MT` | Narrative: `1-13 JCN` · `14-17 date` · `18-77 narrative` |
| `UN` / `UF` / `UP` | Parts records — the join to §12, and the source of BRF |

Blocks 6–9 (**When Discovered, Status, Cause, Deferral**) are single-character adjacent fields, and position 57–63 independently confirms the 7-character EIC. The generator emits both the fixed-width form and a structured form; the fixed-width form exists so that an ingest adapter can be tested against a real wire shape.

**Status codes are the label filter, and the ratio is documented, not chosen.** [07 §5.4](../architecture/07-navy-data-systems.md): *Status 2 is inoperative and Status 3 is degraded performance. Limiting 2-Kilo data to Status 2 and 3 eliminates approximately 75% of all 2-Kilos written.* Hence ~25% Status 2/3, as a subset of the ~35% corrective, per §2.3.

**Every maintenance action carries the four Tier A label-bearing fields** that [06 §9.2](../architecture/06-demo-decisions-and-assumptions.md) names as the program's non-negotiable data requirement — corrective-versus-preventive determination, findings code against the controlled vocabulary, failure timing, and the triggering driver — plus `policy_version` and `triggering_prediction_id`. Stage 9 noise (§9.10) corrupts a bundle-specified fraction of them, because the realistic production condition is partial capture, and a pipeline that only works on complete records will not work.

**JSN first-position originator coding** (§6.5) is applied: prediction-driven 2-Kilos carry FATHOM's declared originator alpha, and the field is therefore usable for exactly the aggregation analysis [07 §5.2](../architecture/07-navy-data-systems.md) says it exists to support.

### 11.6 CASREPs

~180 CASREP-severity events over 24 months — roughly 5% of the ~3,500 Status 2/3 actions.

- **Four types generated in sequence**: `INITIAL`, `UPDATE`, `CORRECT`, `CANCEL`. INITIAL carries the status of the casualty and the parts or assistance needed, because that is what operational and staff authorities use to set resource priorities ([07 §5.8](../architecture/07-navy-data-systems.md)). `CANCEL` sequences are generated for a small fraction — a real occurrence and a case downstream consumers usually mishandle.
- **Categories 2–4** by severity. Per-set field lists (NWP 1-03.1) are NOT PUBLICLY FOUND, so the generator produces the documented type/category structure and the public CASREP-to-COSAL cross-reference layout — `CASREP RATING | NIIN | COSAL ALLOWED | CASREP DEMAND QTY | DEMAND LISTING` with C-2 and C-3 ratings — and marks the field-level gap in the data card.
- CASREPs drive **priority 01–03 requisitions** and are the escalation path a prediction is intended to prevent. In the generated corpus, a CASREP on an item where a prediction had been raised and acted on **must be rarer** than on a comparable item where it was not — and that difference must be measurable on the holdout comparison, not asserted.
- **Counterfactual linkage**: for every intervened item whose `T*` fell inside the window, `truth/` records whether the avoided failure would have been CASREP-severity. That is the ground truth behind the secondary metric in [06 §2](../architecture/06-demo-decisions-and-assumptions.md).

### 11.7 Availabilities and the TMA/TMI reference population

6 availabilities across 24 months including 1 DSRA ([06 §7](../architecture/06-demo-decisions-and-assumptions.md)). Each suppresses operation, clears deferred work in bulk, and enables the `opportunistic` drivers of §8.4.

The generator also emits the six **TMA/TMI attributes** per family over a rolling two-year window — 2-Kilo volume, man-hours, parts cost, high-priority failures (Status 2/3 plus Priority 1–3 CASREPs), high-priority downtime, and CASREP volume ([07 §5.6](../architecture/07-navy-data-systems.md)) — because the tier assignment engine is positioned as that process's successor and needs its inputs to exist in the demonstration data. Attribute scaling (three sigma = 1.0, combined by Pythagorean vector addition) is a consumer concern, not a generator concern; the generator supplies the six raw attributes.

Report-shaped outputs are generated to the documented field sets so the Fleet Status KPIs are computable: **`L0106` / SLICR** with `APL`, `EIC`, `FAILURES`, `SF_MNHRS`, `PART_ISSUES`, `REPLCMNT_COST`, `IMA_MNHRS`, `VISITS`, `ACTIONS`, `OWNSHP_COST`, `COSAL`, `NET_COSAL`, `GROSS_COSAL`, `LOG_TIME`, **`MAINT_EFFECT`**; and `L0201`'s ten highest-`TOTAL_PRICE` parts per system ([07 §5.7](../architecture/07-navy-data-systems.md)). `MAINT_EFFECT` — *the probability of all required repair parts for a given maintenance action being onboard* — must be **computable from the generated records and must not be a generated column**, because it is an outcome KPI and generating it directly would make the demonstration's headline supply metric a fabrication rather than a measurement.

---

## 12. Supply, allowance, and requisition generation

The generated supply corpus must close the loop the program exists to improve: 3-M usage produces the Best Replacement Factor, BRF produces the allowance, allowance quality produces awaiting-parts time, and awaiting-parts time produces MDT and therefore `Ao` (§11.3).

### 12.1 The allowance computation, reproduced exactly

```
UR = POP × BRF / 4
```

where `UR` is the usage rate, `POP` the installed population, and **`BRF` the Best Replacement Factor — actual fleet-reported usage as recorded in the 3-M system, updated annually** ([07 §4.3](../architecture/07-navy-data-systems.md)).

Generation order is therefore mandatory and is the whole point:

1. Generate maintenance actions and their `UN`/`UF`/`UP` parts records (§11.5).
2. **Compute BRF from those generated parts records** — not from a bundle constant. `brf_seed` in `FamilySpec` initializes only the first annual period, before generated history exists.
3. Recompute annually, as the real process does. The dataset therefore contains a BRF revision, and the effect of a revision on allowance is visible.
4. Compute `UR` and apply the four documented rules:

| Rule | Value |
|---|---|
| Carried as an on-board repair part | `UR ≥ 0.50` |
| May be excluded | `UR < 0.125` |
| Price-sensitive sparing | Items ≥ $2,000 spared at 4.0 |
| CASREP add-back | One hit for a Category 3 or 4 casualty in a class over two years, items < $10K, flagged **Allowance Derivation Code `Y`** |

Sparing models are named on the allowance record: `.5 Price Sensitive FLSIP Plus`, `.25 FLSIP`, `.10 MOD-FLSIP`, `RBS`, `TRIDENT`.

### 12.2 The SNSL and the Derivation Code

COSAL structure is generated as **three parts, not five** (07 §4.2, and 07 §9's corrected premise): Part I's six index sections including Section C (APL/AEL → EIC) and Section D (EIC → APL/AEL); Part II Sections A and C; **Part III, the SNSL**, in its seven sections — A Storeroom Items, B Operating Space Items, CF Maintenance Assistance Modules, CR Ready Service Spares, D alternate-number cross-reference, E General Use Consumable List, F Forms and Publications.

The scope exclusion is honored verbatim: the COSAL does **not** include ship's store stocks, resale clothing, bulk fuels, subsistence items, expendable ordnance, or repair parts for aircraft. Generating any of those into a COSAL is a recognizable error.

**Part III Section A — the SNSL — carries all fourteen documented fields**, including the many-to-many part-to-equipment linkage and the **Derivation Code**, *a code used to reflect what determined the computed SNSL allowance*. [07 §4.2](../architecture/07-navy-data-systems.md) calls this *the single most demo-relevant field located in the entire study*, because a predictive system that writes a new derivation basis is filling a field the Navy already has.

Its **value set is NOT PUBLICLY FOUND** (it lives in NAVSUP P-488, itself unlocated). Therefore:

- The generator emits Derivation Code values from a **reserved synthetic set**, with **one documented exception: `Y` for the CASREP add-back**, which 07 §4.3 does publish.
- The reserved set is declared in the data card, and closing this gap is a named follow-up (07 §10 ranks NAVSUP P-488 among the three highest-return retrievals).
- On-board allowance table column bands are honored: `1 | 2 | 3 | 4 | 5-8 | 9-20 | 21-50` equipments, with AELs using eight columns selected by CDMD-OA's `AEL COL` field.

### 12.3 The demand model branches on SMR, and the branches are not optional

[07 §4.7](../architecture/07-navy-data-systems.md): *SMR is the most important table for demand modelling*, because the source code partitions the demand model itself. Every branch below must be present in the generated corpus, and §18.2 asserts each is non-empty:

| Source code | Generated behavior |
|---|---|
| `P*` | Stocked and forecastable — ordinary demand |
| **`XA`** | **No independent demand.** A predicted failure on an XA part generates **next-higher-assembly demand** via `nha_redirect.py`, using `FamilySpec.supply.nha_family_key`. A requisition for an XA part itself is a defect, and is asserted absent |
| `K*` | Kit-driven demand |
| `M*` / `A*` | Demand for raw material or components |
| **`PB` insurance, `PG` sustained life support** | **Little or no demand history — exactly where prediction has the highest value.** The generator must produce a meaningful population of these, because they are the strongest part of the value story and a corpus without them cannot tell it |

**Recoverability drives the second branch.** Position 5 = `D` or `L` means a depot-level repairable: a carcass and rotable-pool problem, not consumption. `Z` means a true consumable. Repairables generate the **full carcass flow** ([07 §4.6](../architecture/07-navy-data-systems.md), §6): advice codes `5G` exchange certification / `5S` remain-in-place / `5R` release of planned requirement with turn-in / `5D` increased allowance or stockage objective / `5A` surveyed as beyond repair; turn-in `BC1`; condition progression `F → M → A`; carcass tracking job `JSL326`; purpose code A→V/W with status `RV`. A repairable that is generated as a consumption is the error a logistician spots first.

**COG carries funding, ICP, and — with recoverability — carcass obligation.** Distribution weighted toward `2S`, `7H`, `3H`, `1H`, `9N` per 07 §4.6.

### 12.4 Requisitions

~6,000 over 24 months. Document numbers per §6.5.

**Predicted requirements are generated correctly, and this is a design rule with a stated reason.** [07 §4.5](../architecture/07-navy-data-systems.md): *a predicted failure is not yet "unable to perform."*

| Element | Rule |
|---|---|
| Urgency of Need | **`C`, or `B` where degradation is already impairing performance. Never `A`.** Generating UND `A` for a not-yet-failed item is logically wrong and a logistician will notice |
| Required delivery date | Forward-dated, consistent with the prediction horizon |
| Advice code | **`2L`** — *quantity exceeds normal demands; however, this is a confirmed valid requirement* — the officially sanctioned encoding for a prediction-driven abnormal quantity |
| Linkage | By **JCN**, with the distinct JSN originator alpha of §6.5 |
| Priority | From the Force/Activity Designator × UND matrix. CASREP-driven requisitions reach priority 01–03; predicted requisitions do not |

**The four documented predicted-demand pathways** of [07 §6](../architecture/07-navy-data-systems.md) are all generated, because each exercises a different consumer:

1. **Near-term need** → `A0A` requisition with `2L`, UND `B`/`C`, forward RDD.
2. **Beyond-horizon need** → Special Program Requirement **`DYA`** → ICP status `DYK`/`PA`, or **`PB`** held until procurement lead time from the support date → **`PR`** when immediate requisition is needed.
3. **Protecting specific assets** → reservation `BRR` or planned requirement `BPR` with **purpose code `S`**; `BFU` on drawdown-date lapse.
4. **Structural change** → OPNAV 4790/CK → CDMD-OA → WSF → ASI (`JSS117`) → revised SNSL allowance quantity with an updated **Derivation Code**.

**Retail level setting** is generated in the documented preview form: RSUPPLY Level Setting (`JSI205`) in **Trial Run** mode producing a Reorder Review listing with revised AMD, RO, and RP, gated by the **Recomputation Test percentage** (suggested range 020–030) — *designed to prevent massive adjustments in RO resulting from insignificant changes in AMD*. AMD is computed over a 6–24 month base period; endurance levels are generated at the documented values (1.0 = 30 days, 1.5 = 45, 2.0 = 60, 2.5 = 75). Trial Run mode is exactly the Navy's own mechanism for previewing a change before committing it, and generating it means the platform's recommendations land in a form the Navy already accepts.

Requisition status progresses through real DIC families: `A0_` requisition, `AE_` supply status, `AS_` shipment status, `AC_`/`AK_` cancellation; the `BRR/BRA/BRC/BRF/BRS/BRX` reservation lifecycle; `BPR/BPA/BPC/BPD` planned requirement lifecycle; `DYA → DYK` special program requirement.

**Awaiting-parts time is emitted per requisition** and is what §11.3 consumes. A requisition that is never filled is a real outcome and is generated at a bundle-specified rate.

---

## 13. Seeded canaries

[06 §6](../architecture/06-demo-decisions-and-assumptions.md): **15% of candidates are known-positive faults injected by the generator**, which is what *makes recall measurable without independent ground truth.* Against ~840 candidates per month, that is ~126 canary candidates per month.

### 13.1 The one rule that makes canaries valid

**A canary must be produced by the same code path, from the same parameter distributions, as an ordinary fault.** The only difference between a canary and an ordinary fault is that `truth/` records `canary: true` and a `canary_injection_id`.

If canaries are generated by a separate injector — a synthetic spike, a scaled template, a shortened trajectory — then canary recall is not an unbiased estimate of recall on ordinary faults, and the recall metric that [06 §6](../architecture/06-demo-decisions-and-assumptions.md) introduces to close the precision/recall trap silently measures the wrong population. `truth/canaries.py` therefore contains **no signal-generation code at all**: it selects which already-generated faults are designated canaries, and nothing else.

### 13.2 Detectability is a monitored property

06 §6 flags the risk directly: *if reviewers learn to spot canaries, they stop measuring recall* — with the mitigation to *vary density and injection realism, and treat canary detectability as a monitored property.* Accordingly:

- **Density varies** across the window around the 15% target rather than being a constant fraction per review batch.
- **Distributional indistinguishability is a test, not a hope.** §18.2 runs a two-sample test on feature summaries of canary versus non-canary faults *within family and severity band* and **fails the build if the null of identical distribution is rejected.** This is the rare case where failing to reject is the passing condition, and the test therefore reports its power alongside its p-value — a low-power test that fails to reject proves nothing, and the harness marks that case as unproven rather than passed.
- Canary flags are in `truth/` only (§8.6). A canary flag reachable from the observed corpus destroys the metric outright.

### 13.3 The exhaustively-labelled reference sample

06 §6's second countermeasure to the metric trap requires *an exhaustively-labelled holdout sample of missions — feasible because the generator knows the truth — providing a reference independent of adjudication behavior.* The generator emits it: a bundle-specified sample of missions in which **every** anomaly, whether or not it was surfaced as a candidate, is enumerated in `truth/`. This is the denominator that makes true recall — not just canary recall — computable for those missions, and it is the reference against which reviewer-behavior drift is detected.

---

## 14. Output formats and event emission

### 14.1 Files

Columnar Parquet for every tabular partition, partitioned by `(domain, asset_id, month)` for telemetry and by `(asset_id, month)` elsewhere. Fixed-width text additionally for the 2-Kilo layout (§11.5) and for MILSTRIP-shaped transactions, so ingest adapters can be tested against a wire shape rather than a convenience shape. Unmanned raw 10 Hz sortie data is written as **per-sortie objects in object storage**, per §2.2, and never as rows.

### 14.2 Events

The generator emits a replayable event stream conforming to [03 §5.4](../architecture/03-integration-contracts.md)'s `EventEnvelope`, so that the demonstration can be populated by replay rather than by bulk load — which exercises the real ingest paths.

Requirements:

- `event_type` follows `fathom.<slug>.<aggregate>.<verb>` in snake_case, and every emitted type **must exist in the [03 §6](../architecture/03-integration-contracts.md) event catalog.** `tools/check_event_catalog.py` already reconciles the catalog in both directions; the generator's emitted-type list is added as a third input to that check, so a generator that invents an event fails CI.
- `scope` and `subject` agree, with exactly one scope identifier populated.
- **`occurred_at` and `recorded_at` diverge materially and deliberately** — a submarine anomaly occurred at sea and was recorded weeks later at reconnect. This divergence is a generated feature, because [03 §5.4](../architecture/03-integration-contracts.md) warns that *feature computation must not use `occurred_at` for any value authored with hindsight* `[D22]`, and a corpus where the two are always equal cannot detect that error.
- `replay: true` on backfill-generated events.
- `clock` fully populated per §9.8, including `sync_quality` retained permanently.
- `baseline_epoch` populated wherever configuration dependence exists, with **antecedent ordering preserved**: an event whose epoch is ahead of the configuration read model must be preceded in the stream by its antecedent configuration event, reachable via `causation_id` `[D3, D4]`.
- Payloads validate against `packages/canonical-schemas`. A generator payload that fails registry validation is a generator defect, not a schema exception — the same rule producers live under.

### 14.3 Predictions are not generated

The generator emits the **simulated prediction stream that the intervention policy consumed** (§8.4), clearly named as such (`policy/simulated_predictions`), and it is **not** a substitute for the platform's own predictions. It exists because the policy had to act on something, and because the propensity model needs the treatment-assignment inputs.

Real predictions come from the models, through the PdM bulk ingest API, and carry `reference_class`, `fallback_level`, `confidence`, and the calibration-population gate of [06 §3](../architecture/06-demo-decisions-and-assumptions.md). A dataset that shipped pre-made predictions would let a pipeline appear to work without any model in it — a way to pass an integration test while demonstrating nothing.

---

## 15. The disconnection scenario generator

[06 §4](../architecture/06-demo-decisions-and-assumptions.md) scopes the demonstration's edge exercise: **one SSN, disconnected for a simulated six weeks, conducting one at-sea corrective repair and two mission reviews while dark**, implemented as a physically separate deployment rather than a simulated queue — because *a simulated disconnect that only delays events does not exercise provisional identity minting, conflict resolution, divergence budgets, or degraded-mode presentation, which are the parts most likely to be wrong.*

The generator's job is to produce that scenario as **reproducible scripted fixtures the edge deployment's test suite consumes**, with expected post-reconciliation state as golden files.

### 15.1 Form

`data/synthetic/scenarios/edge/*.yaml`, one file per scenario, each carrying:

```yaml
scenario_id:        edge-ssn-6wk-provisional-identity
seed:               <fixed. Reproducibility is the point>
base_dataset_id:    <the dataset this scenario is consistent with>
asset:              <the single SSN's asset_id>
timeline:
  - t: 0d           event: disconnect            # outbound, last sync
  - t: 9d           event: <scenario-specific>
  - ...
  - t: 42d          event: reconnect             # six weeks
expected_post_reconciliation:            # the golden file, asserted by the edge test suite
  registry: [...]
  maintenance_actions: [...]
  candidates: [...]
  usage_counters: [...]
assertions:
  - <one per contract obligation exercised>
```

The scenarios are generated by `scenarios/edge_disconnect.py` over stages 2–6, so they are consistent with the main dataset rather than hand-authored beside it. A hand-authored edge fixture drifts from the corpus within one sprint.

### 15.2 The three required cases

**Case 1 — provisional identity across a mid-disconnect item replacement.** [03 §11](../architecture/03-integration-contracts.md): the edge *may mint an `installed_item_id` locally as a client-generated UUID with `provisional: true`*, and the Registry *confirms or supersedes it on reconciliation* `[D9, D8]`. Configuration baselines are enterprise-authoritative because *two divergent views of what is installed is the most damaging available conflict.*

Three sub-cases are generated, because the interesting one is not the happy path:

| Sub-case | Generated situation | Expected outcome |
|---|---|---|
| 1a Confirmed | Ship replaces an item at sea; shore has no competing record | Registry **confirms** the provisional UUID; it becomes permanent |
| 1b **Superseded** | Shore independently recorded the same physical replacement from a supply transaction under a different identifier | Registry **supersedes** the provisional UUID, with the supersession recorded and edge-held references remapped. **This is where the defects are** |
| 1c Duplicate mint | The same physical replacement is recorded twice afloat, producing two provisional UUIDs | Reconciliation collapses them; usage and maintenance attach to one item, and the collapse is auditable |

All three must produce a **correct usage attribution**: the new item starts at zero, and the retired item keeps its hours. Getting this wrong credits a new item with its predecessor's life `[D9]` — the defect that makes RUL meaningless while leaving the data looking clean.

**Case 2 — edge-authoritative maintenance action recording.** [03 §11](../architecture/03-integration-contracts.md) makes maintenance action records **edge-authoritative and append-only** — *the ship records what it did; the server retains authority over what was authorized.* [06 §4](../architecture/06-demo-decisions-and-assumptions.md) scopes it to *the fact of what was done: action taken, findings code, parts consumed, corrective-versus-preventive determination, failure timing.*

The generated scenario contains the one at-sea corrective repair, plus deliberate conflicts:

- The enterprise, while the ship is dark, **authorizes a work order** for the same equipment. On reconnect the action record (edge-authoritative) and the authorization (server-authoritative) must coexist without either overwriting the other. This is the split the design exists to create, and a test suite that never sees both halves at once has not tested it.
- An enterprise-side attempt to **modify** the edge-recorded action is generated and must be **rejected**, because the record is append-only; supersession is recorded instead.
- A **minimal three-field capture** variant is generated — what was replaced, when, corrective or preventive — per 06 §4's stated fallback if capture discipline is poor (A5). Label construction must still succeed from it, and findings coding is completed ashore **with the reviewer flagged as non-observer**.
- **`triggering_driver` is recorded afloat.** The at-sea repair carries `casualty`, not `prediction` — the edge holds only a stale prediction cache and cannot be the authority for a prediction-driven decision.

**Case 3 — edge-resident candidate generation.** [03 §11](../architecture/03-integration-contracts.md): anomaly candidates are **edge-generatable**, and the *enterprise adds further candidates on reconnect* `[D18]` — it adds, it does not replace. 06 §4 puts the detector ensemble and a small pre-screener in the edge inference runtime against exported artifacts.

The generated scenario provides the two while-dark mission reviews and:

- Edge-generated candidates from the two missions, produced by detectors running on **exported model artifacts** rather than a Domino-resident model.
- Enterprise-generated candidates on the same missions after reconnect, **deliberately overlapping** the edge set, so deduplication and merge semantics are exercised rather than assumed.
- Candidates the edge found and the enterprise did not, which must **survive** reconnection — the failure mode being an enterprise recomputation that quietly discards them.
- **Anomaly tags** applied afloat are append-only, never overwritten or deleted, with supersession recorded, because human judgments are evidence.
- Predictions displayed afloat are presented as **degraded**, from a cache with an explicit staleness horizon.

### 15.3 Cross-cutting mechanics every scenario must exercise

These are not separate scenarios; they are conditions layered onto the three above, and they are where the contracts in [03 §5.4](../architecture/03-integration-contracts.md) and [03 §11](../architecture/03-integration-contracts.md) are actually tested.

| Mechanic | Generated condition |
|---|---|
| **Burst telemetry on reconnect** | Six weeks of 150 channels at 1/minute for one hull — on the order of 9×10⁶ samples arriving in one burst. The reconnect path must absorb it, and the divergence budget must be evaluated against it |
| **Clock step at reconnect** | A backward wall-clock step (STIG `makestep 1 -1`), `step_occurred = true`, and two writes from one process carrying inverted `source_time`. Any consumer that arbitrates on `source_time` produces the wrong answer, which is the point |
| **Dispersion exceeding the inter-write interval** | `dispersion_ms` grows across six weeks of holdover until it exceeds the inter-write interval, which **forbids timestamp arbitration entirely** and forces causal-only ordering |
| **Usage counter epoch** | A counter reset occurs during the disconnect, opening a new epoch. Merge is keyed on `(installed_item_id, counter_epoch)`, and an unqualified max-merge would make a single sensor glitch permanent `[D9]`. An authoritative correction with provenance, exempt from monotonicity, is also generated |
| **Divergence budget breach** | At least one aggregate exceeds its declared maximum tolerable disconnection, so the operator interface must degrade to explicitly read-only for that aggregate rather than accumulating unbounded unreconciled state |
| **Out-of-order and duplicate delivery** | Events arrive out of order and duplicated; deduplication on `(producer, monotonic_seq)` or a content hash must be idempotent |
| **Write authority is not bound to liveliness** | The dark hull retains authority over its own records throughout — the property [03 §11](../architecture/03-integration-contracts.md) singles out as the one where the DDS ownership model is actively wrong for this design |

### 15.4 Consumption

The edge deployment's test suite loads a scenario, replays its timeline against a network-partitioned edge instance, reconnects, and asserts against `expected_post_reconciliation`. A scenario whose golden file must be regenerated to make a test pass is a **contract change** and requires the same review as an edit to [03 §11](../architecture/03-integration-contracts.md). That rule is what keeps golden files from becoming a record of current behavior instead of intended behavior.

---

## 16. The adversarial fidelity validation harness

The third of the three places this generator goes wrong, and the reason the document exists.

### 16.1 Dual purpose, stated explicitly

Two documents converge on the same work, and the harness is deliberately built to satisfy both at once:

- [06 §7](../architecture/06-demo-decisions-and-assumptions.md) and [06 §8](../architecture/06-demo-decisions-and-assumptions.md) A1 require **adversarial generator validation: trivial baselines must fail before the data is accepted.** *A generator on which trivial methods succeed is invalid.*
- [08 §5.7](../architecture/08-standards-alignment.md) observes that this mitigation **is** the V&V evidence DoDI 5000.61 requires, and directs that it be *structured as a formal V&V plan under MIL-STD-3022 rather than as an internal engineering check* — because *the same work satisfies both, and framing it as the compliance artifact makes it far harder to skip under schedule pressure.* [08 §9](../architecture/08-standards-alignment.md) lists "restructure generator validation as a MIL-STD-3022 V&V plan" as an immediate engineering action.

So the harness is **one mechanism with two outputs**: a CI gate that blocks dataset release, and the evidence body for the four MIL-STD-3022 products in §16.6. Neither is a by-product of the other. This dual purpose is stated in the V&V Plan's introduction and in every data card, so that a future reader does not "simplify" the harness into an internal check and unknowingly delete the program's compliance evidence for its highest-consequence assumption.

### 16.2 The baselines, named per tier

`harness/baselines/` implements each of these. They are **fixed** — a baseline may not be weakened to help a gate pass, and any change to a baseline's implementation is recorded in the V&V Report with its rationale.

| ID | Tier | Baseline | Why this one |
|---|---|---|---|
| **B0-a** | 0 | Constant-hazard (exponential MLE) on observed intervals | If a memoryless fit is as good as a Weibull fit, the long tail has no wear-out structure and tier 0 demonstrates nothing (§11.2) |
| **B0-b** | 0 | Fleet-mean MTBF applied to every item | The zero-information reference |
| **B0-c** | 0 | Majority class — "no failure within the horizon" | The trap for any accuracy-based metric at a low base rate |
| **B1** | 1 | Hours-since-install threshold, single global cutoff | If this matches a survival model with covariates, the covariates are inert |
| **B2-a** | 2 | **Single-channel linear trend extrapolation to a fixed threshold** | The classic. §7.2's plateau, sawtooth, and confounding features exist specifically to defeat it |
| **B2-b** | 2 | Last-value threshold alarm | Detects only what is already obvious |
| **B2-c** | 2 | Per-channel z-score with a fixed 3σ trigger | Should be defeated by operating-condition confounding (§9.5) |
| **B3** | 3 | The best tier-2 configuration **without** causal features and **without** regime normalization | Isolates what tier 3 actually adds |
| **R-ref** | 2–3 | A **reference model** — a modest, honestly-tuned degradation model | The *floor* side of §9.12's corridor. Not a baseline to defeat; a check that the data is learnable at all |

**Leakage and artifact probes.** These are baselines in form and defect detectors in purpose. Each must perform at chance:

| ID | Probe | Catches |
|---|---|---|
| **B-X1** | Predict the label from row order, file order, or partition position | Generation-order artifacts — the most common way synthetic data leaks its labels |
| **B-X2** | Predict the label from identifiers alone: `niin`, `serial_or_lot`, `installed_item_id`, `iuid` | Sequential or seed-correlated identifiers. A UUID that encodes generation order is a label |
| **B-X3** | Predict the label from metadata alone: record count, channel count, file size, timestamp granularity | Structural leakage — degrading items having longer records because more windows were generated |
| **B-X4** | Permutation control: the reference model on label-permuted data | Any residual leakage the other three miss. Performance must collapse to chance |
| **B-X5** | Predict `canary` from observed features (§13.2) | Canaries generated by a different code path |
| **B-X6** | Predict `policy_frozen` from observed **pre-intervention** features | A holdout population that differs from the treated population in something other than treatment, which would invalidate every comparison against it |

### 16.3 The ablation gate — both sides of the corridor

Run on a reduced profile (`profiles/ci.yaml`) so it is affordable per commit, and on the full profile before release.

| Gate | Condition | Interpretation of failure |
|---|---|---|
| **G-1** | With **all ten noise stages disabled**, B2-a and B2-c **must succeed** on spotlight families at a clear margin above chance | The physics is not producing a learnable degradation signal. The generator is emitting noise dressed as physics, and nothing downstream can work |
| **G-2** | With **noise enabled at shipped settings**, **every** trivial baseline **must fail** (§16.4 defines "fail") | **This is A1's gate.** The data is too clean and the demonstration would mislead. Do not proceed |
| **G-3** | With noise enabled, **R-ref must clear a performance floor** | The data is unlearnable noise. The tiered-modeling story cannot be told, and no amount of modeling effort will fix the dataset |

G-1 and G-2 together are the point: a dataset must be one where **the signal exists and is hard to extract.** Either alone is satisfiable by an invalid dataset.

### 16.4 What "fail" means, quantitatively

The instruction from [06 §7](../architecture/06-demo-decisions-and-assumptions.md) is that trivial baselines must perform *poorly*. Turning that into a test requires care, because an arbitrary absolute threshold presented as settled would be worse than an honest gap. The harness therefore splits the question into a part that is **derivable** and a part that is a **program decision**, and states which is which.

**Derivable, and therefore prescribed now.** A chance-level reference is computable exactly for every metric used:

- For **warning lead-time coverage** at horizon *h* ([06 §2](../architecture/06-demo-decisions-and-assumptions.md)'s primary metric): the chance reference is a random flagger with the **same flag budget** as the baseline under test. Its expected coverage equals its flag rate, and its distribution is available in closed form and by simulation.
- For **actionable precision**: the chance reference is the base rate of the predicted condition among flagged items.
- For **PR-AUC** on horizon classification: the chance reference is the positive base rate.
- For **RUL error**: the chance reference is the family's marginal residual-life predictor — the best constant.
- For **calibration**: a reliability diagram against the base rate, with PICP for the `p10/p50/p90` interval that [03 §7.1](../architecture/03-integration-contracts.md) actually publishes.

**The statistical gate, prescribed and not arbitrary:**

> **G-2 passes only if, for every trivial baseline, on every spotlight family and fleet-wide, the baseline's advantage over its flag-budget-matched chance reference is not statistically significant at α = 0.05 by a one-sided permutation test with at least 1,000 permutations — and the test is reported with its power.**

This is a real quantitative criterion that requires no invented number, and it fails in the right direction: a baseline that is *reliably* a little better than chance fails the gate, which is correct, because a trivially reliable predictor means the dataset is trivially predictable.

**Not derivable, and therefore an open program decision (OPD-2, §21):** the *practical-significance* margin. There is a legitimate program question — how much better than chance a trivial baseline may be while the dataset is still considered adequately hard — and it depends on what the demonstration must show and to whom. The harness implements the margin as a configured value `gate.g2_practical_margin` with **no default**, and `validate` refuses to run until the program sets it. Likewise **G-3**'s floor for R-ref is `gate.g3_reference_floor`, also without a default. Recommended derivation method for both, offered as method rather than as a number: run R-ref and B2-a on NASA PCoE C-MAPSS FD001 to establish the spread between a trivial and a competent method on a dataset of accepted difficulty, and set the FATHOM margins in that neighborhood — **with the domain-mismatch caveat of [08 §5.7](../architecture/08-standards-alignment.md) attached, because that procedure anchors difficulty only and says nothing about representativeness of shipboard HM&E.**

**Power is reported, never assumed.** Every gate reports the event count it was evaluated on and the power of its test. A family with too few failure events is marked **"gate not powered"** in the V&V Report and **does not pass** — it is explicitly unproven. Silent passes on thin data are the failure mode that would let this whole harness become decorative. With ~180 CASREP-severity events and ~3,500 Status 2/3 actions across ~120 families, thin cells are the expected condition, not the exception.

**The full gate set:**

| Gate | Asserts | Section |
|---|---|---|
| **G-1** | Noise-off: trivial baselines succeed — the signal exists | §16.3 |
| **G-2** | **Noise-on: every trivial baseline fails — A1's gate** | §16.3, §16.4 |
| **G-3** | Noise-on: R-ref clears the floor — the data is learnable | §16.3 |
| **G-4** | **Ground-truth leakage: probes B-X1…B-X6 all at chance** | §16.2, §8.3 |
| **G-5** | **Informative censoring is present and drifting** — naive MTBF inflated vs truth, significantly, and trending up over the window | §8.5 |
| **G-6** | The achievable ceiling on lead-time coverage is **below 1.0** by the family-declared unpredictable fractions | §7.2 |
| **G-7** | **Holdout integrity**: zero prediction-driven interventions on policy-frozen items; holdout is distributionally indistinguishable from treated on pre-intervention features (B-X6) | §10.3 |
| **G-8** | **Navy-formula recoverability**: tier-0 MTBF fits recover seeded values within the Poisson interval; recomputed `Ao` and `T(pf)` match intended values | §11.2, §11.3 |
| **G-9** | **Capacity conformance**: every §2 figure realized within tolerance, including the row budget and the ~5M/day live rate | §2, §18.4 |
| **G-10** | **Realism rules**: every rule in [07 §7.2](../architecture/07-navy-data-systems.md) asserted over emitted rows | §18.2 |
| **G-11** | **Artifact separation**: no parameter leakage into rows; bundle absent from the repository; truth partition unreferenced outside evaluation paths | §4.2, §18.3 |
| **G-12** | **Distributional fidelity**: marginal and joint distribution comparison against intended distributions; failure-mode prevalence; censoring and truncation behavior | §16.5 |

`validate` exits non-zero on any gate failure or any unpowered gate, and **release tooling refuses to publish a dataset whose `card/vv-report.json` contains a non-pass.** The gate is not advisory.

### 16.5 The fidelity-evaluation protocol and the transfer caveat

[08 §5.6](../architecture/08-standards-alignment.md) specifies the protocol content: *marginal and joint distribution comparison, failure-mode prevalence, censoring and truncation behavior, and above all **whether a model trained on synthetic data transfers to real data.** This is where synthetic data fails silently.*

G-12 covers the first three. The fourth **cannot be evaluated**, because no real Navy shipboard PHM dataset is available — [08 §5.7](../architecture/08-standards-alignment.md) records that no public Navy maintenance or PHM reference dataset was found and directs the program to *plan on generating the corpus; do not plan on finding one.*

The harness therefore does the only honest thing available: it **runs the transfer evaluation on what exists and labels the result precisely.** A model trained on FATHOM synthetic bearing data is evaluated on IMS/FEMTO run-to-failure data, and a model trained on FATHOM SF-04 data is evaluated on C-MAPSS. The result is reported as **pipeline transfer evidence** — it demonstrates that the modeling pipeline generalizes across datasets — and is **explicitly not** evidence of transfer to Navy shipboard HM&E. The V&V Report carries that distinction as a labeled limitation, and the data card carries it as a field. Presenting PCoE-derived transfer results as representative of Navy equipment is prohibited by §19.

The unevaluable fourth item is recorded as an **open limitation in the Accreditation Report**, not quietly omitted. It is the single largest residual risk in the generator's V&V, and it is why the accreditation statement below is narrow.

### 16.6 The four MIL-STD-3022 products

MIL-STD-3022 w/ Change 1 is current and **expressly directed for use** by DoDI 5000.61 §3.2, which states that practitioners *should use the Military Standard 3022 templates to the maximum extent practicable* ([08 §5.3](../architecture/08-standards-alignment.md)). Data Item Descriptions **DI-MSSM-81750 through 81753** are the CDRL vehicles, all revalidated 4 February 2026 ([08 §5.6](../architecture/08-standards-alignment.md)).

Content is populated against DoDI 5000.61 §3.1's **three content groups** — VV&A context (dates, responsible party, version identification, **intended use**, accreditation criteria, activities performed, and *sources of data, the date stamp of data, as well as associated metadata, in accordance with the data quality templates*); V&V implementation and results (including *capabilities, limitations, risks, potential impacts to the specific intended use, and assumptions*); and accreditation results — plus §3.3's **maturity and confidence assessments and uncertainty quantification.** [08 §5.3](../architecture/08-standards-alignment.md) notes that for a platform whose contract output is `rul.p10/p50/p90` and a calibrated `p_failure`, **UQ is not an add-on — it is the product**, and §3.3 makes it part of the accreditation basis.

Skeletons live in `docs/vva/` and are populated by `validate`; the sections marked *generated* are written from harness output, so they cannot drift from the code.

**`docs/vva/accreditation-plan.md` — DI-MSSM-81750**

1. **Intended use statement** — verbatim §16.7. The narrow scope is set here, before evidence is gathered, because scoping accreditation after the fact is how programs end up accrediting more than they can support.
2. Accreditation authority and responsible party; program identification.
3. **Accreditation criteria** — the gate table of §16.4, each gate mapped to the intended-use element it supports. A gate that supports no element of the intended use is removed; an intended-use element with no gate is a gap and is listed as such.
4. Acceptability criteria for residual risk, including the unevaluable transfer item of §16.5.
5. M&S description: the four artifacts of §4, each with its version identity and marking.
6. Planned V&V activities, schedule, and the resources they require.
7. Configuration management: dataset identity, seed policy, reproducibility claim (§18.1).

**`docs/vva/vv-plan.md` — DI-MSSM-81751**

1. **The dual-purpose statement of §16.1**, first, so a reader understands why an engineering gate is a compliance artifact.
2. Verification approach — is the generator built right: unit, property, and statistical tests (§18).
3. Validation approach — is it the right generator: the adversarial gate set, the ablation corridor, the leakage probes, the fidelity-evaluation protocol.
4. **Data V&V per the VV&A Recommended Practices Guide Data Quality Templates**, invoked normatively by DoDI 5000.61 §3.1.a(6) ([08 §5.1](../architecture/08-standards-alignment.md)): data sources, **date stamps**, and associated metadata for every parameter, which is exactly what §4.3's provenance classes carry.
5. **Assumptions and limitations, declared in advance** — A1 named as the assumption under test, plus §6.2's catalogue divergence, §6.6's CAGE residual, and every NOT-PUBLICLY-FOUND field generated from a reserved range.
6. Uncertainty quantification approach per §3.3: propagation of parameter uncertainty into the generated corpus, and the calibration/PICP evaluation of published intervals.
7. Acceptance criteria and their status — **prescribed where derivable (§16.4), marked as open program decisions where not.**

**`docs/vva/vv-report.md` — DI-MSSM-81752.** Generated. Per-gate result with test statistic, p-value, **power**, event count, and pass / fail / **not-powered**; the ablation corridor results; the realized distributional comparisons; the parameter provenance register with date stamps; the leakage-probe results; the pipeline-transfer result **with the §16.5 label**; a **maturity and confidence assessment**; and a limitations register with impact on the specific intended use. Machine-readable twin at `card/vv-report.json`, which is what release tooling reads.

**`docs/vva/accreditation-report.md` — DI-MSSM-81753.** The accreditation decision, the criteria assessment, residual risk including the unevaluable transfer question, and the accreditation statement of §16.7 as the operative conclusion. Signed by the accreditation authority, who is not the generator's implementer — a separation this document cannot enforce but does state.

### 16.7 The accreditation-for-intended-use statement

[08 §5.3](../architecture/08-standards-alignment.md) records that *the phrase "for a specific intended use" appears in all three of the standard's accreditation definitions*, and that this is the hook for scoping accreditation narrowly and affordably. [08 §5.6](../architecture/08-standards-alignment.md) supplies the language.

The following text is **required, verbatim, in three places**: the Accreditation Plan, the Accreditation Report, and — as the value of the data card field `accreditation_statement` — **in the generator's own output metadata for every dataset it produces**:

> **Accredited for pipeline validation, interface conformance testing, and reviewer-workflow rehearsal; not accredited as evidence of model performance for fielding.**

And, per [08 §5.6](../architecture/08-standards-alignment.md)'s requirement for a written statement, the data card field `operational_use_prohibition` carries:

> **No model trained solely on synthetic data is a candidate for operational use.** DoDM 5000.101 requires the independent test set to be operationally representative, which synthetic data cannot satisfy by construction.

Both strings live in `schema/datacard.schema.json` as `const` values. They are not templated, not paraphrased, and not configurable, because a caveat that can be edited per dataset is a caveat that will be edited.

---

## 17. Data cards

**A required artifact, not optional documentation.** DoDM 5000.101 mandates data cards and *documentation of dataset preparation, quality, governance, suitability, limitations, and a sustainability plan* — and [08 §5.2](../architecture/08-standards-alignment.md) identifies the **limitations clause as where synthetic-data fidelity caveats belong.** [08 §5.6](../architecture/08-standards-alignment.md) specifies the content: *generator version, parameter provenance, fidelity claims **and their limits**, the identifier-fabrication scheme, and known distributional divergences.*

One card per generated dataset, at `card/datacard.json` plus a rendered `card/datacard.md`. Written by `emit/datacard.py` during `validate`, validated against `schema/datacard.schema.json`, and **a dataset without a schema-valid card cannot be published** — the writer emits the card and the release check re-validates it independently.

### 17.1 Schema

```yaml
# ─────────────── identity ───────────────
dataset_id:                  <str, required>   # content hash of plan + artifact digests
generated_at:                <RFC3339, required>
generator:
  version:                   <semver, required>
  git_sha:                   <str, required>
  schema_version:            <semver, required>          # artifact 2
  parameter_bundle:
    reference:               <str, required>             # oci://... — reference, never values
    digest:                  <sha256, required>
    version:                 <semver, required>
run_config:
  master_seed:               <int, required>
  profile:                   smoke | ci | full
  identity_mode:             fabricated | nvr_seeded     # §6.4, required, no default
  identity_mode_authorization: <str | null>              # REQUIRED non-null if nvr_seeded
  reproducibility_claim:     <str, required>             # §18.1

# ─────────────── the required caveats (const in schema) ───────────────
accreditation_statement:     "Accredited for pipeline validation, interface conformance
                              testing, and reviewer-workflow rehearsal; not accredited as
                              evidence of model performance for fielding."
operational_use_prohibition: "No model trained solely on synthetic data is a candidate for
                              operational use. DoDM 5000.101 requires the independent test
                              set to be operationally representative, which synthetic data
                              cannot satisfy by construction."

# ─────────────── parameter provenance (§4.3) ───────────────
parameter_provenance:
  classes_present:           [P1, P2, P3]                # P4 impossible; loader rejects
  class_counts:              {P1: <int>, P2: <int>, P3: <int>}
  open_sources_used:         [<C-MAPSS | N-CMAPSS | IMS | FEMTO | ...>]
  domain_transfer_note:      <str, required if any P1>   # verbatim from the bundle
  fitted_to_real_controlled_data: false                  # const false. §19 entry 1
  date_stamps:               {<source>: <date>}          # DoDI 5000.61 §3.1 data quality templates

# ─────────────── fidelity claims AND their limits ───────────────
fidelity:
  claims:
    - claim:                 <str>                       # e.g. "tier-0 MTBF fits recover seeded values"
      evidence_gate:         <G-1 … G-12>
      scope:                 <families / domains it holds for>
  limits:
    - limit:                 <str>
      consequence:           <str, required>             # what a consumer must NOT conclude
  transfer_evaluation:
    performed_on:            [<PCoE dataset>, ...]
    result:                  <summary>
    label:                   "pipeline transfer evidence only; not evidence of transfer to
                              Navy shipboard HM&E behaviour"     # const. §16.5
    navy_reference_dataset_available: false               # const false. 08 §5.7
  unevaluable:
    - item:                  "transfer of a synthetic-trained model to real Navy shipboard data"
      reason:                "no public Navy maintenance or PHM reference dataset exists"

# ─────────────── identifier fabrication scheme (§6) ───────────────
identifiers:
  niin_block_a:              {form: "FSC(real) + LL + 7 alphanumeric",
                              guarantee: "alphabetic NCB positions cannot occur in a real NSN"}
  niin_block_b:              {form: "FSC in unassigned FSG + 9 numeric",
                              fsg_reserved: [33], guarantee: "no NSN is assigned in an unassigned FSG"}
  fsc_source:                "real, from 07 §4.8 verified shipboard HM&E classes"
  fsc_list:                  [<the FSCs actually used>]
  uic_scheme:                <fabricated alpha-leading | nvr_seeded>
  hull_rendering:            "space, never hyphen (SECNAVINST 5030.8D Encl 6)"
  eic_scheme:                {form: "7 alphanumeric, positionally segmented, truncation permitted",
                              reservation: "reserved first position + banned-real-value list",
                              residual_risk: "EIC is never a join key; collision affects display only"}
  apl_ael_scheme:            {apl_hme: 9, apl_electronic: 8, ael: "10-11 (ambiguity per 07 §4.1)",
                              reservation: "reserved category pair + banned-real-value list"}
  cage_scheme:               {source: "program-declared synthetic table",
                              structural_guarantee: false,
                              residual_risk: "no structural CAGE reservation rule established
                                              from public sources (§6.6, OPD-1)"}
  jsn_originator_code:       <the declared alpha>
  nomenclature_policy:       "generic functional descriptions only; no real Navy type
                              designation appears in any artifact"
  synthetic_markers:         ["synthetic: true on every catalogue item",
                              "catalog_authority = FATHOM-SYNTH"]

# ─────────────── known distributional divergences ───────────────
divergences:
  - divergence:              "catalogue is overwhelmingly Navy-local-item-coded; a real COSAL
                              is majority NSN"
    cause:                   "§6.2 non-collision guarantee takes precedence over mix realism"
    consequence:             "analyses keyed on NCB values or NSN-vs-NICN mix are not representative"
  - divergence:              "ESWBS, TYCOM, OPNAV 4790/CK, and Derivation Code values are
                              reserved synthetic, not real"
    cause:                   "values NOT PUBLICLY FOUND (07 §3.4, §3.1, §3.6, §4.2, §10)"
    consequence:             "code-value distributions must not be cited as Navy-representative"
  - divergence:              "SCLSIS field lengths are generator-declared"
    cause:                   "lengths NOT PUBLICLY FOUND (07 §3.1)"
    consequence:             "fixed-width interop with a real SCLSIS feed is unverified"
  - divergence:              "configuration is a deliberate HM&E subset (ESWBS 200/300/500),
                              ~1,200 items per surface asset against a far larger real record"
    cause:                   "06 §7 scope decision; proportionality argued from 07 §8"
    consequence:             "absolute configuration counts are not representative; ratios are"
  - divergence:              "2-Kilo layout is historical (1987-1992 extract); the current data
                              element dictionary and 120 Card Format are NOT PUBLICLY FOUND"
    cause:                   "07 §5.3"
    consequence:             "wire-format conformance to current 3-M is unverified"
  # ... one entry per divergence, each with a mandatory consequence

# ─────────────── realized capacity (§2, §18.4) ───────────────
capacity_realized:
  assets:                    {surface: 5, subsurface: 3, unmanned: 4}
  installed_items:           <int>
  distinct_niins:            <int>
  equipment_families:        <int>
  spotlight_families:        6
  spotlight_items:           <int>
  maintenance_actions:       <int>
  corrective_fraction:       <float>
  status_2_3_fraction:       <float>
  casrep_events:             <int>
  requisitions:              <int>
  spotlight_rows:            <int>          # against the ~1.5e9 budget
  longtail_rows:             <int>          # against the ~4e7 budget
  live_rate_samples_per_day: <float>        # against ~5M
  budget_conformance:        pass | fail

# ─────────────── holdout, canaries, ground truth ───────────────
holdout:
  fraction:                  0.10
  item_count:                <int>
  stratification:            "proportional by (family x domain), floor 3 per cell"
  manifest_digest:           <sha256>
  integrity_gate:            G-7 pass | fail
canaries:
  candidate_fraction:        0.15
  same_code_path_as_ordinary_faults: true    # const true. §13.1
  indistinguishability_test: {statistic: <float>, p_value: <float>, power: <float>,
                              verdict: not_rejected | rejected | underpowered}
ground_truth:
  artifact:                  "truth/"
  status:                    withheld
  withheld_from:             ["all training paths", "all scoring paths", "all feature pipelines"]
  readable_by:               ["evaluation role only"]
  contains_counterfactuals:  true
  rationale:                 "06 §2 — retained so the corrected estimator's recovery can be
                              measured against truth"

# ─────────────── V&V (§16) ───────────────
vv:
  harness_version:           <semver>
  run_id:                    <str>
  gates:                     {G-1: pass, G-2: pass, ..., G-12: pass}
  not_powered:               [<gate/family pairs>]
  open_program_decisions:    [OPD-1, OPD-2, ...]           # §21, unresolved at generation time
  products:                  {accreditation_plan: <path>, vv_plan: <path>,
                              vv_report: <path>, accreditation_report: <path>}
  dodm_5000_101_tier:        <the four-tier dataset assignment>

# ─────────────── marking and governance ───────────────
marking:
  dataset_marking:           <UNCLASSIFIED | CUI//SP-CTI | ...>   # per OCA determination
  determination_status:      assumed | oca_determined
  schema_marking:            "CUI//SP-CTI assumed until OCA determination (08 §5.6 action 4)"
  parameter_marking:         "CUI//SP-CTI assumed until OCA determination"
  distribution_statement:    <B | C | D | E | null>
  nnpi_scope:                in | out                      # 08 §5.6 requires this explicitly
  aggregation_referred_to_oca: true | false                 # DoDI 5200.48 compilation concern
  inference_disclosure:      "a sufficiently large corpus permits re-estimating the parameters
                              that produced it; the defence is that no parameter was fitted to
                              controlled data (§4.3), not that synthesis decontrols"
governance:
  owner:                     <team>
  sustainability_plan:       <path>                         # DoDM 5000.101
  retention:                 <policy>
  supersedes:                <dataset_id | null>
```

### 17.2 Three fields that exist because omitting them is the likely error

- **`fidelity.limits[].consequence` is mandatory per limit.** A limitation stated without its consequence gets read as boilerplate. "Configuration is a subset" means nothing; "absolute configuration counts are not representative, ratios are" tells a consumer what not to conclude.
- **`inference_disclosure`** exists because [08 §5.4](../architecture/08-standards-alignment.md) is explicit that *statistical synthesis is not a recognised decontrolling mechanism* and *treating generation as automatic decontrol is the specific error to avoid.* The card states the real defense — the parameters were never controlled — rather than an invalid one.
- **`marking.nnpi_scope`** is required because [08 §5.6](../architecture/08-standards-alignment.md) directs the program to *scope Naval Nuclear Propulsion Information in or out explicitly and early*: CUI//SP-NNPI is a materially more restrictive regime and *attaches the moment carrier or submarine propulsion-plant equipment is in scope.* With 3 VIRGINIA-class assets in the fleet, this is a live question and not a theoretical one. The default posture for the demonstration is **out of scope**, achieved by excluding propulsion-plant equipment from the generated configuration — reactor-plant COG `0S` and any nuclear-plant AEL series (`6-` Nuclear Reactor Plant) are not generated, and `plan` fails if a bundle attempts them.

---

## 18. Determinism, seeding, and testing

### 18.1 The seed tree

**Reproducibility claim:** for a fixed `(generator git SHA, parameter bundle digest, run config, master seed)`, the generator produces **byte-identical output** in every partition except `card/generated_at`.

Naive sequential seeding does not achieve this, because adding one family shifts every subsequent draw and silently changes the entire dataset. `rng.py` therefore implements a **hierarchical seed tree**: each generation site derives its stream from a path.

```python
def stream(master_seed: int, path: str) -> Generator:
    # path e.g. "/asset/03/family/SF-01/item/0117/truth/failure_time"
    return default_rng(blake2b(f"{master_seed}:{path}".encode(), digest_size=32).digest())
```

Consequences, all of which are requirements:

- **Independence**: adding a family, reordering iteration, or parallelizing across assets changes no other stream.
- **Regeneration in isolation**: a single item's trajectory can be regenerated from its `seed_lineage` (§8.7) for debugging, without regenerating the dataset.
- **Parallel-safe**: workers derive their own streams; no shared RNG state exists anywhere in the generator, and a module that calls a global `random` function fails review and the import contract.
- **Golden-hash test**: `profiles/smoke.yaml` output hashes are committed, and CI fails on any change. When a change is intended, the hash update is part of the diff and is reviewed — which makes "this refactor was supposed to be behavior-preserving" a checkable claim.

### 18.2 Correctness tests over emitted rows

Assertions run over the **emitted output**, not over the functions that produced it, because the failure mode being guarded is a row that reaches a consumer.

**Identifier and realism rules** — one test per rule in [07 §7.2](../architecture/07-navy-data-systems.md), all gate G-10:

| Assertion | Source |
|---|---|
| No emitted string in any partition matches a hyphenated hull pattern | 07 §3.5 |
| Every NIIN is in Block A or Block B; none is a real-form all-numeric NIIN in an assigned FSG | §6.2 |
| Every FSC is real and in the declared list; no unassigned FSG appears outside Block B | 07 §4.8 |
| The catalogue contains all five item-identification forms in the declared proportions | 07 §4.8 |
| **No LICN appears in any supply transaction** | 07 §4.8 |
| Status 2/3 fraction = ~25% ± tolerance, and is a subset of corrective | 07 §5.4, §2.3 |
| **No predicted requirement carries UND `A`**; predicted requirements carry `C` or `B` with a forward RDD | 07 §4.5 |
| No requisition exists for an `XA`-source part; every such demand appears against the next higher assembly | 07 §4.7 |
| Every repairable (COG `7_`, recoverability `D`/`L`) has a carcass transaction; no repairable is consumed | 07 §4.6, §4.7 |
| Unit price is integral in implied-two-decimal form; `D` in the units position at or above $10M; no float price column exists | 07 §7.2 |
| Fund codes and project codes are blank | 07 §7.2 |
| Requisition document numbers are 14 characters with serials excluding `I` and `O` | 07 §4.4 |
| JCNs are 13 characters; the JSN first position carries the declared originator for prediction-driven actions | 07 §5.2 |
| SMR codes are 6 positions with recoverability at position 5 only | 07 §4.7, §9 |
| EICs are 7 characters or a legitimate truncation; no banned real value appears | 07 §3.2 |
| Both documented EIC↔APL composite-key cases are present | 07 §5.1 |
| At least two `HSCI` schemes appear across the fleet; no consumer-visible assumption of a universal ESWBS layout | 07 §3.4 |
| No real Navy type designation appears in any emitted string | §6.3, §19 |
| No installed item's usage or degradation state is inherited from its predecessor | §5.3 |

**Statistical tests** — that the *intended* distributions were actually produced:

- Kolmogorov–Smirnov on each family's realized failure-time marginal against its intended distribution.
- Seeded-MTBF recovery per long-tail family within the Poisson interval (G-8).
- Realized `Ao` and `T(pf)`, recomputed from emitted records, against intended values (G-8).
- Realized noise magnitudes per stage against bundle parameters; realized MNAR correlation non-zero per spotlight family (§9.11).
- Canary indistinguishability, **with power reported** (§13.2).
- Holdout balance on pre-intervention features (B-X6, G-7).
- Censoring composition: the fractions of failure / preventive / admin / mission-end censoring, and the informative-censoring magnitude (G-5).

### 18.3 Separation-boundary tests

These exist so that **a future code change cannot quietly violate §4 or §8.3**. All are CI-blocking and roll up to gates G-4 and G-11.

`importlinter.ini` contracts:

| Contract | Forbidden |
|---|---|
| `truth-cannot-see-policy` | `fathom_synth.truth.*` → `fathom_synth.policy.*` |
| `policy-cannot-see-truth-internals` | `fathom_synth.policy.*` → `fathom_synth.truth.failure_process`, `.trajectory`, `.canaries`, `.store` |
| `params-single-entry` | any module except `fathom_synth.params` reading the bundle path or `FATHOM_GENPARAMS` |
| `identity-single-mint` | any module outside `fathom_synth.identity` constructing a NIIN, EIC, APL, AEL, UIC, JCN, or document number |
| `no-global-rng` | any module importing `random` or calling `numpy.random.*` module-level functions |
| `families-opaque` | any module in `fathom_synth.*` outside `params` referencing a nomenclature string |

Repository and content checks:

| Check | Fails on |
|---|---|
| **Bundle-absence check** | Any file under the monorepo matching the bundle manifest schema, or paths `**/params/**`, `**/*.params.yaml`, `**/reliability*.yaml` |
| **Banned-literal scan** | Any real APL/AEL/EIC/UIC value published in 07, any real Navy type designation, or any decimal literal registered in the bundle's key index, appearing in generator source, tests, fixtures, or docs |
| **Parameter-leakage scan** | Any generated column that is constant-equal to a bundle scalar, or whose exact mean/min/max equals one, within 1e-6 relative tolerance (§4.2) |
| **Truth-reference scan** | Any reference to `*.truth.parquet` or the truth prefix outside `harness/` and declared evaluation paths (§8.6) |
| **Veil monotonicity property test** | Any veil method whose result at `t1` is not a prefix of its result at `t2 > t1` (§8.3) |
| **Veil-cheating self-test** | A deliberately cheating policy that is **not** caught by gate G-4 (§8.3) |
| **No-default-parameters test** | `plan` succeeding with the bundle absent (§4.4) |
| **Event-catalog check** | Any emitted `event_type` absent from the [03 §6](../architecture/03-integration-contracts.md) catalog, via `tools/check_event_catalog.py` (§14.2) |

### 18.4 Capacity conformance

`validate` compares every realized figure against §2 and its tolerance, writes the comparison into the data card's `capacity_realized`, and fails on any breach (G-9). Explicitly checked: asset counts (exact), installed-item counts (±5%), distinct NIINs (within the 4,000–6,000 band), family and spotlight counts, maintenance-action count and its corrective / Status 2-3 composition, CASREP count, requisition count, the two row budgets, and the live-rate figure.

A capacity breach is a **hard failure, not a warning**, for a specific reason: these figures are the ones a reviewer checks against the architecture documents, and a dataset that quietly contains 11,000 installed items makes every capacity claim in documents 06 and 07 wrong.

---

## 19. Explicit DO-NOT list

Each entry is a prohibition with its authority. Every one of these is a shortcut someone will propose under schedule pressure, which is why they are enumerated rather than implied.

| # | Do not | Why, and authority |
|---|---|---|
| **1** | **Do not fit generator parameters to real controlled Navy data** for the unclassified demonstration — not reliability data, not maintenance history, not configuration extracts, not "just for calibration" | [08 §5.6](../architecture/08-standards-alignment.md) action 3: *the way to keep the demonstration unclassified is to ensure no controlled parameter ever enters the generator.* Use the open PCoE/FEMTO/IMS sources plus engineering judgment. Enforced: provenance class **P4 is rejected by the loader** (§4.3) |
| **2** | **Do not let generated rows carry real equipment-specific reliability values, even "realistic-looking" ones**, and do not pair any generated identifier with a real Navy type designation | [08 §5.4](../architecture/08-standards-alignment.md): *real failure rates, MTBF values, inspection intervals, and degradation rates for identified Navy equipment are the reliability characteristics of a Navy platform*, and **the more faithful the synthesis to a real system, the weaker the argument that control was broken.** Enforced: banned-literal scan, parameter-leakage scan, nomenclature policy (§6.3, §18.3) |
| **3** | **Do not let the intervention policy alter, truncate, or inform ground-truth failure time** — and do not "simplify" by stopping the trajectory at intervention | [05 D1](../architecture/05-architecture-review-findings.md) and [06 §2](../architecture/06-demo-decisions-and-assumptions.md). The counterfactual is the referee; without it the demonstration's central methodological claim is unverifiable. Enforced: two-process separation, artifact sealing, the veil, gates G-4 and G-5 (§8) |
| **4** | **Do not present NASA PCoE-derived validation as representative of Navy shipboard equipment** | [08 §5.7](../architecture/08-standards-alignment.md): these are aero-propulsion, bearing, and battery datasets — *excellent for validating a modelling pipeline and poor as proxies for shipboard HM&E behaviour, OFRP mission profiles, or the 3-M documentation loop.* **They validate the PIPELINE only.** Enforced: the const label in §16.5 and the data card's `transfer_evaluation.label` |
| **5** | Do not commit the parameter bundle, or add a default parameter value to generator code | §4.2, §4.4. A hardcoded fallback re-couples the artifacts that §4 exists to separate, and does it invisibly |
| **6** | Do not tune noise parameters to improve model performance | §9.1 rule 6. That is the exact mechanism by which A1 comes true |
| **7** | Do not weaken a trivial baseline to make gate G-2 pass | §16.2. The baseline is the instrument; adjusting the instrument to get the reading you want is not a validation |
| **8** | Do not let a gate pass on unpowered data | §16.4. "Not powered" is a distinct verdict and it does not pass |
| **9** | Do not make the truth partition readable by any training, scoring, or feature path | §8.6. One accidental join invalidates every metric with no visible symptom |
| **10** | Do not generate canaries through a separate code path from ordinary faults | §13.1. Canary recall then measures a population that does not exist, and the metric introduced to close the precision/recall trap silently reopens it |
| **11** | Do not fabricate a value for a field marked NOT PUBLICLY FOUND | [07 §1](../architecture/07-navy-data-systems.md): *the prohibition on fabrication is operative, not aspirational.* Generate from a reserved range and declare it. *Fabricated schema detail is worse than an acknowledged gap, because a reviewer recognises it immediately* |
| **12** | Do not emit the informal ESWBS nine-group summary table, or any guessed ESWBS/TYCOM/Derivation/4790-CK code values presented as real | §5.2, §12.2, [07 §3.4](../architecture/07-navy-data-systems.md) — the informal table is contradicted by a real value and is unusable |
| **13** | Do not use modernized-away organization names or retired markings: **NAVICP, FISC, SPAWAR, DBOF, DRMS** are now NAVSUP WSS, NAVSUP FLC, NAVWAR, NWCF, DLA Disposition Services; **"FOUO" and "U//FOUO" are retired** | [07 §1](../architecture/07-navy-data-systems.md) — *getting the codes right and the organisation names wrong is the most likely way to look dated.* [08 §5.5](../architecture/08-standards-alignment.md) for the marking |
| **14** | Do not generate reactor-plant or nuclear-propulsion equipment into the demonstration configuration | §17.2. NNPI is a materially more restrictive regime and *attaches the moment carrier or submarine propulsion-plant equipment is in scope* ([08 §5.6](../architecture/08-standards-alignment.md)) |
| **15** | Do not ship a dataset without a schema-valid data card, or edit the two const caveat strings | §16.7, §17 |
| **16** | Do not treat statistical synthesis as decontrol | [08 §5.4](../architecture/08-standards-alignment.md): *nothing makes a transformation pipeline a competent decontrolling authority.* The determination belongs to the OCA and the SCG, not to engineering |
| **17** | Do not generate the platform's own predictions as data | §14.3. It lets a pipeline appear to work with no model in it |

---

## 20. Definition of Done

The shared Definition of Done template in [09 — Monorepo and Conventions](09-monorepo-and-conventions.md) applies in full: tests, coverage, lint and type gates, ADR for any architecturally significant choice, conformance to [03](../architecture/03-integration-contracts.md), documentation updated, no unreviewed golden-file changes, CI green on the required checks.

Generator-specific gates, all additive and all CI-enforced:

| # | Gate | Verified by |
|---|---|---|
| 1 | **The fidelity harness passes on the full profile** — every gate G-1…G-12 `pass`, with **no gate in `not_powered`** for any spotlight family | `card/vv-report.json`; release tooling refuses a non-pass (§16.4) |
| 2 | **The two-sided corridor holds** — G-1 (signal exists with noise off) and G-2 (trivial baselines fail with noise on) and G-3 (reference model clears the floor) | §16.3 |
| 3 | **Informative censoring is present and drifting** | G-5 (§8.5) |
| 4 | **Data cards are generated and schema-valid**, with both const caveat strings intact, every `fidelity.limits[]` carrying a `consequence`, and every divergence enumerated | `schema/datacard.schema.json` validation, re-run independently at release (§17) |
| 5 | **The four-artifact separation is verified** — bundle absent from the repository, no parameter leakage into rows, no truth reference outside evaluation paths, every import contract satisfied, `plan` fails without a bundle | G-11 and §18.3 |
| 6 | **The holdout population is correctly excluded from simulated intervention** — zero prediction-driven interventions on policy-frozen items, holdout balanced on pre-intervention features, manifest digest recorded | G-7 and §10.3 |
| 7 | **The four MIL-STD-3022 products exist and are populated** — Accreditation Plan, V&V Plan, V&V Report, Accreditation Report — against DoDI 5000.61 §3.1's three content groups plus §3.3 maturity and UQ, with the narrow accreditation statement verbatim | §16.6, §16.7 |
| 8 | **Capacity conformance**: every §2 figure within tolerance and recorded in the card | G-9 and §18.4 |
| 9 | **Reproducibility**: byte-identical output for a fixed `(SHA, bundle digest, config, seed)`; smoke-profile golden hashes committed and unchanged, or changed deliberately in a reviewed diff | §18.1 |
| 10 | **Realism rules**: every rule in [07 §7.2](../architecture/07-navy-data-systems.md) asserted over emitted rows | G-10 and §18.2 |
| 11 | **Edge scenarios generated with golden files**, and the edge deployment's test suite green against them; any golden-file change reviewed as a contract change | §15 |
| 12 | **Open program decisions are recorded, not silently defaulted** — every unresolved OPD in §21 listed in the card's `vv.open_program_decisions`, and no gate threshold silently defaulted | §21 |

---

## 21. Open program decisions

Recorded here rather than resolved with an invented number. Each is a genuine program judgment; each blocks something specific; none is blocked on engineering.

| ID | Decision | Blocks | Current handling | Owner |
|---|---|---|---|---|
| **OPD-1** | Whether the exclusion of the letters `I` and `O` from assigned CAGE codes is confirmed in DoD 4100.39-M Volume 8 | Converting CAGE fabrication from a disclosed residual risk to a structural guarantee (§6.6) | Program-declared synthetic CAGE table; residual risk disclosed in the data card | Engineering research |
| **OPD-2** | **The practical-significance margin for gate G-2** — how much better than its flag-budget-matched chance reference a trivial baseline may be while the dataset is still considered adequately hard. Also **G-3's reference-model floor** | Dataset release. The significance test is prescribed (§16.4); the margin is not | `gate.g2_practical_margin` and `gate.g3_reference_floor` have **no defaults**; `validate` refuses to run until set. Recommended derivation method in §16.4, with the PCoE domain-mismatch caveat attached | Program, with engineering recommendation |
| **OPD-3** | Active-window widths and the deep-fidelity sortie sample fraction | Nothing — the budget is enforced regardless. But the choice determines *where* fidelity is concentrated | Set in `RunConfig`; realized allocation recorded in the card. 06 §7 marks the row-count figure LOW confidence, so the budget is the constraint and these are the free variables (§7.5) | Engineering, reviewed by program |
| **OPD-4** | The magnitude threshold for gate G-5 — how much naive-estimator bias is enough to make the correction visibly worth demonstrating | Nothing hard; G-5's significance test stands alone | Significance test enforced; magnitude reported and not gated (§8.5) | Program |
| **OPD-5** | Whether to re-weight the holdout **within** the fixed fleet-wide 10% to over-sample spotlight and low-rate families | Per-family calibrated estimates on the holdout stratum (§10.1) | Proportional allocation with a floor of 3 per cell; the thinness is stated in the card | Program, per 06 §2's stated alternative |
| **OPD-6** | **`identity_mode`** — fabricated identifiers (default) versus NVR-seeded real UICs, which requires a written determination | Nothing; the default is safe. But 07 §7.1 and 08 §5.6 conflict and the program must own the resolution (§6.4) | `fabricated` default; `nvr_seeded` requires `identity_mode_authorization` in the card | Program |
| **OPD-7** | The OCA determination on the schema and parameter bundle, the NNPI scoping decision, and the aggregation referral under DoDI 5200.48 | Nothing in the demonstration; everything about distribution | CUI//SP-CTI assumed for artifacts 2 and 3, Distribution B–E; NNPI scoped **out** by excluding propulsion-plant equipment (§17.2) | Program / OCA, per [08 §5.6](../architecture/08-standards-alignment.md) action 4 |
| **OPD-8** | Retrieval of **NAVSUP P-488** (the only known location of **Derivation Code** values), **NAVSUP P-485 Volume II**, and the **GEIA-STD-0007 / MIL-STD-1388-2B LSAR** reliability data elements | Replacing three reserved synthetic code sets with real values, and the formal bridge from a predicted failure to an allowance quantity | Reserved synthetic sets, declared in the card | Program, per [07 §10](../architecture/07-navy-data-systems.md)'s three highest-return follow-ups |
