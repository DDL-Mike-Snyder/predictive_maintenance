# Standards Alignment for the Four Cross-Cutting Items

| | |
|---|---|
| **Status** | Draft |
| **Purpose** | Establish which military, federal, and commercial standards apply to each of the four cross-cutting items that precede Phase 3, what each requires, and what the program must do to align |
| **Scope** | The four items in [04 §12](04-subapplication-architectures.md): the unified taxonomy, the outbox and sync library, the tool manifest model, and the synthetic data strategy |
| **Research date** | 4 August 2026. ASSIST records reflect "Data updated: 03 Aug 2026" |
| **Method** | Public sources only. Primary documents were retrieved and text-extracted where hosts permitted; several DoD issuances were obtained through archival raw-file routes and read directly rather than through secondary summaries |
| **Classification** | Internal |

---

## 1. How to read this document

Three markings are used, and the distinction is operative:

| Marking | Meaning |
|---|---|
| **Mandatory** | Applies by statute, regulation, or DoD issuance |
| **Recommended** | Not compelled, but alignment is materially defensible and the alternative is weaker |
| **Informative** | Useful vocabulary or structure to borrow. Conformance is not pursued |

**Currency was verified for every standard, and several widely-cited documents turned out to be cancelled or superseded.** §7 lists them. Citing a cancelled standard as authoritative is a defect a reviewer finds in seconds, and the reliability domain is unusually full of them.

Where a value could not be verified from a primary source it is marked **UNVERIFIED** rather than filled in. §8 consolidates those.

---

## 2. Cross-cutting item 1 — the unified taxonomy

The requirement: one controlled vocabulary serving three capture points — anomaly classification at post-mission review, maintenance findings coding at work completion, and failure modes in causal analysis. This resolves findings **C8** and **D31** and the open question at document 04 §6.

### 2.1 Applicable standards

| Standard | Revision / date | Status | Applicability |
|---|---|---|---|
| **MIL-STD-3034A** — Reliability-Centered Maintenance Process | Rev A, 29 Apr 2014; Notice 1 (validation) 15 Apr 2019 | **Active.** Prepared by **NAVSEA SEA 05S**. Supersedes MIL-STD-3034 and MIL-P-24534A(NAVY) | **Mandatory** — Navy ship RCM |
| **ISO 14224:2016** — Collection and exchange of reliability and maintenance data for equipment | 3rd ed., 2016-09-16, 272 pp, ISO/TC 67 | Current. Paid | **Recommended — the structural anchor** |
| **SAE GEIA-STD-0007C** — Logistics Product Data | Rev C, 6 Nov 2019. DoD adoption notice **Active, 30 Apr 2024** | Current. Successor to MIL-STD-1388-2B LSAR | **Mandatory** if logistics product data is a deliverable |
| **NAVSEAINST 4790.8** — Ships' 3-M Manual | Rev 8B (13 Nov 2003) is the publicly retrievable copy; 8C and 8D exist | Current at 8D (UNVERIFIED) | **Mandatory** — findings capture |
| **DoDI 4151.22** — Condition-Based Maintenance Plus for Materiel Maintenance | Effective **14 Aug 2020**; reissues and cancels the 16 Oct 2012 version | Current | **Mandatory** |
| **DoD Manual 4151.22-M** — Reliability Centered Maintenance | 30 Jun 2011, as amended | Current | **Mandatory** — the DoD-level RCM manual |
| **DoD CBM+ Guidebook** | **Aug 2024** (DoDI 4151.22 still cites the May 2008 edition) | Current | **Recommended** |
| **NAVAIR 00-25-403** — Naval Aviation RCM Process | Editions 2001, 2005, 1 Jun 2016; current revision UNVERIFIED | Standing naval-aviation RCM authority | **Mandatory** if aviation or unmanned aviation is in scope |
| **SAE JA1011 / JA1012** — RCM evaluation criteria and guide | **JA1011_202411, 5 Nov 2024** (supersedes 2009); JA1012 Rev A, Aug 2011 | Current. Paid | **Recommended** — the conformance test for any RCM claim |
| **IEEE 1856-2017** — Framework for Prognostics and Health Management of Electronic Systems | Approved 28 Sep 2017 | Active; no revision project | **Recommended** — PHM capability vocabulary |
| **ISO 13374-1/-2/-3/-4** — Condition monitoring and diagnostics: data processing, communication, presentation | -1:2003 (confirmed 2021), -2:2007, -3:2012, -4:2015 | All current. Paid | **Recommended** — processing architecture |
| **MIMOSA OSA-CBM** | v3.3.1, 29 Jun 2010 | Current. The ISO 13374 reference implementation. **Developed 2001 with US Navy funding under the Dual Use Science and Technology program** | **Recommended** |
| **ASD S5000F** — In-service data feedback | Issue 3.0, Apr 2021 | Current. Paid | **Recommended** — interchange |
| **S1000D** | Issue 6, 1 Sep 2024 | Current. **Free to download** | **Recommended** — fault isolation data modules |
| **MIL-STD-40051-2D** — Digital technical information for page-based manuals | Rev D, 2021 | Active | **Recommended** |
| **IEC 60812:2018** — FMEA and FMECA | 3rd ed., 10 Aug 2018, 165 pp | Current. Paid | **Recommended** where FMECA rigor is required |
| **ANSI/AIAA S-102.2.4** — Performance-Based FMECA Requirements | Revision and date **UNVERIFIED** | The FMECA reference in the DoD product-support stack | **Recommended**, subject to verification |
| **MIL-HDBK-338B** — Electronic Reliability Design Handbook | Rev B with **Notice 3, 23 Feb 2026** | Active | **Informative** — safe citation for reliability practice |
| **MIL-HDBK-217F Notice 2** | 28 Feb 1995. **There is no Revision G** | Not updated by DoD since 1995 | **Informative** — cold-start prior only |

### 2.2 The recommendation: three standards, three non-overlapping jobs

| Layer | Standard | Why |
|---|---|---|
| **Semantics** — definitions and consequence model | **MIL-STD-3034A §3** | Navy-authored, Active, revalidated 2019. Its definitions cover precisely the concepts the three capture points disagree about. Adopting them verbatim settles the dispute by authority rather than negotiation |
| **Structure** — hierarchy and code sets | **ISO 14224:2016**, levels 6–9 and Annex B | The only standard supplying a complete, coded, published failure-mode vocabulary bound to an equipment taxonomy, explicitly designed as a *"reliability thesaurus"* |
| **Contract** — export and interchange | **SAE GEIA-STD-0007C**, with **ASD S5000F** for in-service feedback | DoD-adopted. Whatever the internal model, the taxonomy must export into LSA-050 (RCM Results) and LSA-058 (FMECA Results) or it cannot be delivered |

### 2.3 MIL-STD-3034A definitions — adopt verbatim

These become the platform's vocabulary. All are quoted from §3.

| Term | Definition |
|---|---|
| **Functional failure** (3.9.1) | *"The inability of an item to perform a specific function within specified limits."* |
| **Hidden failure** (3.9.2) | *"A functional failure which is not observable to the operating crew during their routine duties."* |
| **Potential failure** (3.9.3) | *"A definable and measurable condition that indicates a functional failure is imminent."* |
| **Failure cause** (3.10) | *"The underlying stimulant of the failure or the root process which leads to failure, including defects in design, process, quality, maintenance, or part application."* |
| **Failure effects** (3.11) | *"describe what happens when a failure mode occurs if no other action is taken."* |
| **Failure mode** (3.12) | *"The specific condition causing a functional failure (often best described by the material condition at the point of failure)."* |
| **Dominant failure mode** (3.12.1) | *"A cause of failure that is important because of a high probability and severity or high probability or severity of the failure."* |
| **Failure consequence** (3.5.2) | *"The measure of safety, environmental, mission, and economic impact of an item's functional failure caused by a specific failure mode."* |
| **Functionally significant item** (3.15.2) | *"An item whose functional failure has safety, statutory, regulatory, mission, or major economic consequences."* |

**§3.9.3 is the single most valuable definition located in the entire standards review.** *"A definable and measurable condition that indicates a functional failure is imminent"* is, in NAVSEA's own words, exactly what this platform produces. **The program should adopt "potential failure" as the term for its core output** rather than an invented one. §3.12.1 *dominant failure mode* is the natural prioritisation key for a prediction backlog, and §3.5.2's four consequence axes map directly onto proposal triage and the optimiser's consequence weighting.

MIL-STD-3034A also establishes that **RCM is the foundation of CBM**: *"RCM methodology provides the foundation for a Condition Based Maintenance (CBM) program,"* with **Appendix F a mandatory appendix** on the RCM/CBM+ relationship. Its twelve phases place FMEA at Phase 4 and terminate in the Maintenance Requirement Card and Maintenance Index Page — the artifacts a maintainer actually works from.

Eighteen Data Item Descriptions in the DI-SESS-809xx and 818xx series correspond to the phase artifacts. **Failure Intelligence's `FailureMode` and `Attribution` aggregates should be shaped so they can export into them**, because that is how RCM analysis is contracted.

### 2.4 ISO 14224 structure

Nine taxonomy levels. Levels 1–5 are business and plant context; **levels 6–9 are the equipment parent-child chain to which reliability and maintenance data attaches.**

| ISO 14224 level | Maps to |
|---|---|
| 1–5 (industry → plant) | Navy → domain → class → hull → plant |
| **6 — equipment class** | ESWBS / EIC |
| **7 — subunit** | Equipment subdivision |
| **8 — maintainable item** | **`InstalledItem`**, identified by IUID |
| **9 — part** | NIIN |

⚠️ Two implementation guides differ on the exact normative labels for levels 6–9. The structural claim is consistent; **confirm labels against the purchased standard before publishing a data dictionary.**

Failure modes are **three-letter codes**. Verified examples: `AIR` abnormal instrument reading · `BRD` breakdown · `ELP` external leakage, process medium · `ELU` external leakage, utility medium · `FTS` failure to start on demand · `PLU` plugged or choked · `STD` structural deficiency.

⚠️ **The complete Annex B code set is UNVERIFIED and paywalled.** Six retrieval routes were attempted without success. **Recommendation: purchase the standard.** It is a roughly $300 purchase that directly de-risks the program's central data-model decision, and no free substitute exists.

### 2.5 Navy 3-M code sets — and a corrected premise

**"How Malfunctioned" is not a field on the OPNAV 4790/2K.** It belongs to the Naval Aviation Maintenance Program lineage (VIDS/MAF, OPNAV 4790/60). The ships 3-M code sets are:

**CAUSE (CAS)** — *"The code best describing the cause of the failure or malfunction when need for maintenance was first discovered… this field provides valuable data to the equipment manager; without it, only the fact that the equipment failed is known."*

`1` abnormal environment · `2` manufacturer or installation defects · `3` lack of knowledge or skill · `4` communications problem · `5` inadequate instruction or procedure · `6` inadequate design · `7` normal wear and tear · `8` corrosion condition · `0` other or no malfunction

**WHEN DISCOVERED (WND)** — `1` lighting off or starting · `2` normal operation · `3` during operability tests · `4` during inspection · `5` shifting operational modes · `6` during PMS · `7` securing · `8` during AEC program · `9` no failure, PMS accomplishment only · `0` not applicable

**ACTION TAKEN** — two characters, first from a fixed list (`1` completed with parts from supply · `2` completed, parts not drawn · `3` completed, no parts required · `4` cancelled · and others), second TYCOM-specified. Modifiers on `1`/`2`/`3` include **`A` "maintenance requirement could have been deferred," `B` "was necessary," `C` "should have been done sooner."**

⚠️ These are transcribed from **4790.8B (13 November 2003)**. Revisions C and D exist. **Re-baseline every code list against the current revision before implementation and treat any delta as a taxonomy version bump.**

### 2.6 Two findings that resolve open items with external authority

**EIC cannot be an instance identifier — now citable.** NAVSEAINST 4790.8 Appendix A defines EIC as *"a 7-character code that identifies the equipment. The first position identifies the system; the first and second characters together identify the subsystem; the third and fourth together identify the equipment category,"* and — decisively — *"Where the EIC is known to more than four digits, it should be recorded at that level."*

**EIC is a class or category code of variable specificity.** That is the primary-source justification for document 03 §3.3's rule forbidding `eic` as a join key, and it confirms findings **C2** and **C10** were correct.

**The instance identifier should be IUID.** DoDI 4151.22 §1.2.d requires *"serialized item management (SIM) in accordance with DoDI 4151.19 and item unique identification (IUID) in accordance with DoDI 8320.04 to enhance CBM+ data collection and analysis,"* and §1.2.l requires their use *"to optimize RCM and CBM+ data analytics."* **`InstalledItem` identity should therefore be the IUID or serialised identity**, which gives finding C10 an externally mandated resolution rather than an internal preference.

### 2.7 The authority for choosing a taxonomy at all

**DoDI 4151.22 §1.2.j**, verbatim:

> *"Data should be in a format that is interoperable with enterprise information technology architectures while conforming to non-proprietary, open industry standards that support data capture, integration, storage, and exchange across sustainment functional tiers and organizational levels. **Accept data in proprietary formats only by exception.**"*

That is the citation authorising — indeed obliging — adoption of ISO 14224 and GEIA-STD-0007 rather than an invented internal scheme.

**And a useful verified negative: DoDI 4151.22 contains the word "taxonomy" zero times.** DoD policy requires open-standard, interoperable CBM+ data and *"precise failure mode identification based on both field and depot repair data"* (§4), but **prescribes no failure taxonomy.** The anchor choice is therefore a documented program decision, not a compliance default, and it should be made deliberately and recorded.

### 2.8 How the three capture points reconcile

**One vocabulary, one owner, three declared projections.**

The taxonomy becomes a single versioned reference dataset owned by **Reference Data**. Document 04 currently gives Post-Mission Analysis a taxonomy service and Failure Intelligence another; both become read-through clients of one registry.

**The external forcing function is DoDI 8320.02**, which requires authoritative data sources to be registered and *"structural metadata, including vocabularies, taxonomies, and ontologies"* to be published. **A vocabulary with three owners cannot be registered as an authoritative source.** That converts finding C8 from internal tidiness into a compliance obligation.

**Registry entry shape** — MIL-STD-3034A semantics, ISO 14224 structure:

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

**The three projections:**

| Capture point | Projection | Reconciliation rule |
|---|---|---|
| **Post-Mission Analysis** | A **coarsened subset** keyed on `observable_signature`, plus an explicit `unclassified/novel` escape. Reviewers select observable signatures, not mechanisms — they are watching telemetry, not tearing down equipment | Every confirmed tag carries `taxonomy_version`. Because tags are append-only and never overwritten (document 03 §11), a taxonomy revision **never rewrites historical tags** — it records a crosswalk, and superseded tags retain both codes. Novel signatures become proposals to Reference Data, adjudicated by Failure Intelligence |
| **Maintenance findings** | The **3-M code sets** — CAUSE, WHEN DISCOVERED, ACTION TAKEN — because maintainers must keep filing the 4790/2K and cannot be asked to learn a second vocabulary at the deckplate | A published, versioned crosswalk from `{CAUSE, WHEN DISCOVERED, ACTION TAKEN, EIC}` to failure-mode code. It is **many-to-many and lossy by construction**: 3-M CAUSE has nine values and is a *cause* code, not a *mode* code. **Carry the ambiguity as data — `candidate_modes[]` with confidence — rather than forcing one code and silently corrupting the labels.** This is the most common way maintenance-derived training data goes bad |
| **Failure Intelligence** | The **full vocabulary**, and sole authority to extend it | Owns the content; Reference Data owns registry, versioning, and publication. Its `Attribution` is the arbitration record when a tag and a findings code disagree. **That disagreement is a retained first-class signal, not an error to clean** |

**Four non-negotiables:**

1. **Every label carries `taxonomy_version`.** A training set assembled across an unversioned revision is silently corrupt and the corruption is undetectable afterwards. This is also a compliance requirement, since DoDM 5000.101 mandates data-drift detection and data-card documentation of dataset limitations.
2. **The crosswalk is a delivered, reviewable artifact**, not a mapping buried in code. It is what a substituting implementation must reproduce under document 03 §10, and it is the DoDI 8320.07 obligation to register vocabularies and business rules.
3. **Reconcile at read time, never at write time.** Each capture point stores what its user actually asserted, in that user's vocabulary; the unified view is computed. **Normalising on write destroys the disagreement data that is the entire reason for having three capture points.**
4. **Instance identity is IUID, not EIC** (§2.6).

### 2.9 A free conformance claim worth taking

**MIMOSA OSA-CBM v3.3.1** implements ISO 13374's six processing blocks: **DA** data acquisition → **DM** data manipulation → **SD** state detection → **HA** health assessment → **PA** prognostic assessment → **AG** advisory generation. It was *"developed in 2001 by an industry team partially funded by the Navy through a Dual Use Science and Technology program,"* because *"the Navy sought standardization to reduce costs and increase interoperability for maintenance operations."*

**The platform's pipeline already is that chain** — telemetry ingest (DA/DM) → health indicators (SD) → anomaly detection (SD/HA) → prediction (PA) → proposal (AG). Naming it as such converts an internal design into a standards-conformance claim with Navy provenance, at essentially zero cost. **IEEE 1856-2017** supplies the complementary PHM capability vocabulary, and a tier scheme justified against it is more defensible than one justified internally.

Licensing note: the OSA-CBM specification is publicly available but under the MIMOSA License Agreement. Fine for architectural conformance; check before redistributing schema artifacts.

---

## 3. Cross-cutting item 2 — the outbox and sync library

### 3.1 The central finding

**No DoD standard exists for message queuing, guaranteed delivery, or afloat-to-ashore data reconciliation.** Confirmed by complete enumeration. MIL-STD-6016 is export-controlled and irrelevant (slotted TDMA track exchange), MIL-STD-2525 is symbology, and MIL-STD-2045-47001 is an application-layer framing format — message framing, not durable queuing, acknowledgement, or reconciliation.

**The outbox semantics, sequencing, acknowledgement, and conflict-resolution policy are therefore the program's to design and declare.** What MOSA requires is that they be exposed as a severable module with a published, machine-readable interface — which is exactly what document 03 §11 does. **That section is a MOSA asset and the program should say so.**

### 3.2 Applicable standards

| Standard | Revision / date | Status | Applicability |
|---|---|---|---|
| **DoDI 8510.01** — Risk Management Framework for DoD Systems | **19 Jul 2022** (retitled from "…for DoD IT") | In force | **Mandatory** |
| **DoDI 8500.01** — Cybersecurity | 14 Mar 2014, Change 1 effective 7 Oct 2019 | In force | **Mandatory** |
| **CNSSI 1253** — Security Categorization and Control Selection for National Security Systems | 1 Aug 2022 | Current. **Uses separate C/I/A levels, not high-water mark** | **Mandatory** if NSS |
| **CNSSP 32** | — | Current | **Mandatory** if NSS. Requires FedRAMP High plus CNSSI 1253 Appendix D overlays at HHx |
| **NIST SP 800-53 Rev 5** | Release 5.2.0 | Current | **Mandatory** |
| **CSP SRG** — Cloud Service Provider Security Requirements Guide | **V1R7, 30 Jun 2026** | Current. **Replaced the Cloud Computing SRG on 14 Jun 2024** | **Mandatory** |
| Cloud Mission Owner Network SRG / OS SRG | V1R2 (30 Jan 2025) / V1R3 (13 Aug 2025) | Current | **Mandatory** |
| **Container Platform SRG** | **V2R4**, 28 Oct 2025, 188 rules | Current | **Mandatory** |
| **Kubernetes STIG** | **V2R6**, 1 Apr 2026, 92 rules. **Zero time-sync rules** | Current | **Mandatory** |
| **OpenShift 4.x STIG** | V2R6, 1 Jul 2026, 83 rules | Current | **Mandatory** if OpenShift |
| **ASD STIG** — Application Security and Development | **V6R4**, 1 Oct 2025 | Current | **Mandatory** |
| RHEL 9 STIG / Ubuntu 22.04 STIG | V2R5 each, 2 Jul 2025 | Current | **Mandatory** |
| **DoD Zero Trust Overlays** | **v1.1, Jun 2024** | Current. **The only document that both accommodates DDIL and supplies the SC-45/AU-8 parameters** | **Mandatory** as tailoring source |
| DoD Zero Trust Reference Architecture | v2.0, Jul 2022 | Current. ⚠️ **Does not address DDIL at all** | **Informative.** Do not cite as DDIL authority |
| **DoD API Technical Guidance** | **MVCR 3, Mar 2026**, OUSD(R&E), 124 pp | Current. **The only current DoD document addressing DDIL testing and code paths** | **Recommended** |
| **DoDI 8540.01** — Cross Domain Policy | 8 May 2015, Change 1 2017 | Current | **Conditional** — only if crossing classification levels |
| **10 U.S.C. §§ 4401–4403** — MOSA | §4401 renumbered by **PL 116-283 (FY2021 NDAA)**. ⚠️ **PL 119-60 (18 Dec 2025) amended §§4402 and 4403** — content unretrieved | In force | **Mandatory** |
| **DoDI 4650.08 / DoDD 4650.05** — PNT and Navigation Warfare | 27 Dec 2018 (Chg 1 2020) / 9 Jun 2016 (Chg 3 2023) | Current | **Mandatory** |
| RFC 5905 / RFC 8915 — NTPv4 / Network Time Security | Jun 2010 / Sep 2020 | Proposed Standard. ⚠️ **NTPv5 is an Internet-Draft, not usable for planning** | **Recommended** |
| OMG DDS / RTPS / DDS-Security / DDS-XTypes | 1.4 / 2.5 / 1.2 / 1.3 | Current | **Informative** — QoS vocabulary; not the ship-to-shore wire |
| DDS-TSN | 1.0 **beta 2** | ⚠️ **Beta — not normative, do not cite** | — |
| FACE Technical Standard | Ed. 3.2, 2 Aug 2023 | Current | **Informative** |
| MIL-STD-2045-47001 | Rev E reported 1 Feb 2021; likely **not** cancelled | ASSIST record unobtainable | **Informative** — substantively irrelevant |

### 3.3 Three findings that changed the design

**Same-level ship-to-shore synchronisation is not a cross-domain problem.** DoDI 8540.01 §1.a scopes itself to *"the interconnection of information systems of **different security domains**,"* and the CSP SRG states plainly that *"Impact Levels do not apply to FedRAMP baselines. **Impact Levels are a DoW construct only.**"* Two same-level unclassified enclaves are one security domain. This should be stated explicitly in the system security plan, because programs routinely and expensively mis-scope same-level replication as a cross-domain solution — which would put **Reliable Human Review** in the synchronisation path and destroy the automated-sync story. Crossing *classification* levels is genuinely cross-domain and a different design.

**Impact Level 5 no longer covers CUI.** Redefined 2 July 2025: IL4 expanded to cover both Moderate and High confidentiality and integrity and is now the CUI level; IL5 became "Unclassified National Security System / National Security Information." **This requires a written authorising-official determination of NSS status**, which also settles federal AI-policy applicability. One memo, two questions.

**Compliance guarantees a non-monotonic clock at exactly the wrong moment.** Ubuntu 22.04 STIG rule **V-260520** mandates `makestep 1 -1` — unlimited backward steps on any offset exceeding one second — and that step fires precisely when a disconnected node reconnects and drains its outbox. Two writes from one process can carry inverted timestamps.

Meanwhile the **DoD Zero Trust Overlays v1.1** select **SC-45 and SC-45(1)** as tailoring additions — neither is in the SP 800-53B Moderate or High baseline — and set audit time-stamp granularity at **1 millisecond**, comparison **at least daily**, and a **1 second** resync threshold. And the **Kubernetes STIG contains zero time-synchronisation rules**, so correctness is inherited entirely from the host OS STIG; a skewed node silently poisons every pod on it.

**Consequences, all now in document 03 §5.4:** ordering and deduplication key on `(producer, monotonic_seq)` or a hybrid logical clock, never on wall time; durations and backoff use a monotonic clock; every event carries a `sync_quality` attestation retained permanently, because **skew is indistinguishable from tampering to an assessor** and non-repudiation claims collapse if the time is contestable. **A local stratum-1 reference with GNSS plus rubidium or OCXO holdover is a hardware requirement, not a configuration choice.**

⚠️ **NAVWAR waiver exposure.** DoDI 4650.08 states that *"reliance on civil, commercial, or foreign sources as the primary means of obtaining PNT information… is not authorized without a waiver."* A shipboard platform taking time from a commercial GNSS receiver or NTP appliance as its primary source may require a CJCSI 6130.01G waiver. Also verified: **neither DoDI 4650.08 nor DoDD 4650.05 designates USNO as the DoD time standard** — do not invent a policy citation for that.

### 3.4 Why DDS is not the ship-to-shore wire

From the specifications themselves: RTPS designs for *"multicast and best-effort transports"*; participant discovery uses a **StatelessWriter with `reliabilityLevel = BEST_EFFORT`** under a `leaseDuration`, after which *"any resources associated to the Participant and its Endpoints can be freed"*; and DDS's RELIABLE guarantee is footnoted *"subject to timeouts that indicate loss of communication with a particular subscriber."* Multicast is not routed over satellite, and after an outage exceeding the lease the reliable match tears down.

Three specifics worth carrying into the outbox design regardless:

- **DURABILITY_SERVICE `history_depth` defaults to 1.** Enable persistence and forget this and the "durable" store keeps one sample per instance. **State depth explicitly.**
- **DESTINATION_ORDER `BY_RECEPTION_TIMESTAMP`** (the default) permits each subscriber to converge on a different final value; `BY_SOURCE_TIMESTAMP` converges deterministically — but on each writer's own wall clock, so under skew it converges deterministically *on the wrong value*.
- **OWNERSHIP is bound to LIVELINESS**, so a disconnected ship *loses* ownership — the exact opposite of edge-authoritative mission records. **Do not copy that binding.** Now recorded explicitly in document 03 §11.

**Recommended split:** DDS or a CNCF broker intra-ship where a shipboard bus already exists; a durable transactional outbox drained over authenticated, idempotent HTTPS or gRPC with resume-from-offset for ship-to-shore.

### 3.5 Controls to claim explicitly

**CP-10(2) Transaction Recovery** — *"Implement transaction recovery for systems that are transaction-based"* — is in **both** the Moderate and High baselines, and it is the control the outbox directly satisfies. Also: **AU-4(1)** transfer to alternate storage, **AU-6(3)** correlate ship and shore repositories, **AU-9(3)**, **AU-12(1)** with 1 ms as the stated correlation parameter, **AU-10** sign outbox records at the ship, **SC-16** bind classification and provenance to synced records, **SC-28/SC-28(1)** and **SC-8/SC-8(1)** with mission-owner sole key control. **Encrypt the outbox at rest on the ship** — it is a persistent CUI or NSI store.

### 3.6 Two operational constraints

**Iron Bank confers no authorisation and no STIG inheritance**, verbatim: *"Hardened containers do not have a Certificate to Field (CtF) or an Authority to Operate (ATO)."* What is inherited is a body of evidence. And it is **available at IL2 only**, so the supply-chain path into an IL4 or IL5 enclave — and the disconnected mirror that implies — is the program's problem. Its remediation clocks (Critical: justify 5 days, mitigate 15) are a poor fit for a hull offline for weeks. **Surface that tension to the authorising official early.**

**Multiple CANES baselines are simultaneously fielded**, which is a real constraint on the compatibility matrix that document 03's substitution protocol and conformance suites must accommodate.

⚠️ Also note: the **DoD Zero Trust Overlays' DDIL grant is hedged** — *"DDIL environments may be able to support disconnected functions but will be managed by centralized ICAM solutions."* That authorises a centrally-governed cached policy decision point, not an autonomous shipboard one, which is a real constraint on the machine-to-machine authentication dependency in document 01 §8.7.

---

## 4. Cross-cutting item 3 — the tool manifest model

### 4.1 Applicable standards

| Standard | Revision / date | Status | Applicability |
|---|---|---|---|
| **10 U.S.C. §§ 4401–4403** — MOSA | Renumbered by PL 116-283. ⚠️ PL 119-60 amendments unretrieved | In force | **Mandatory** |
| **DoDM 5000.101** — AI Test and Evaluation | Dec 2024 | Current. ⚠️ **§1.1.b excludes generative AI** | **Mandatory** for supervised models; **inapplicable** to LLM surfaces |
| **DoD AI Ethical Principles + RAI Toolkit** | — | Current. No carve-out | **Mandatory** |
| **EO 14319** — Unbiased AI Principles | — | In force | **Mandatory** |
| **NIST AI 600-1** — Generative AI Profile | — | Current | **Recommended — the primary substantive guidance for the agent surface** |
| **DoDI 8320.02** — Data sharing | — | Current | **Mandatory** — registration of authoritative sources and publication of vocabularies |
| **DoDAF** | — | Current | **Recommended** — expected deliverable views |
| MIL-STD-961 · DI-IPSC-81434 / 81436 | — | Active | **Informative** — interface documentation |

### 4.2 The statutory hook for the contracts approach

**10 U.S.C. § 4401(c)(1)(B)(ii)** requires **machine-readable interfaces**. That is a direct statutory anchor for the OpenAPI-plus-conformance-suite approach in document 03, and it elevates the substitution property from good engineering practice to statutory alignment.

⚠️ **Terminology trap:** the statutory term is **"modular system interface."** *"Key interface"* is legacy OSJTF language and is not statutory. Use the statutory term in program material.

### 4.3 The AI governance split

**DoDM 5000.101 §1.1.b**, verbatim: *"This issuance **does not apply to reinforcement learning, generative AI, and other advanced types of AI** and will be updated when OT&E and LFT&E procedures for these applications mature."* §1.1.a(5) confirms the positive scope is *"with a focus on supervised learning applications."*

| Surface | Governing authority |
|---|---|
| **PdM models** (supervised) | DoDM 5000.101 applies in full — model cards, data cards, four-tier datasets, drift detection |
| **Agent surfaces** (generative) | DoDM 5000.101 **does not apply by its own terms.** DoD AI Ethical Principles and RAI Toolkit, EO 14319, and **NIST AI 600-1** as the primary substantive risk taxonomy |

**Practical consequence:** produce model cards for the agent surface as a voluntary ethical-principles artifact, **not** as a 5000.101 compliance item. Claiming a mandate that carries a written exclusion is precisely what a reviewer finds.

### 4.4 A clean negative worth citing

**A complete enumeration of the ASSIST standardisation space returns nothing on AI or machine learning.** Searching title, keywords, and scope across all statuses: "artificial intelligence" → 1 irrelevant record; "machine learning" → 1 irrelevant record. **No MIL-STD, MIL-HDBK, or Data Item Description addresses AI or ML at all.**

This is useful rather than merely absent: it means the manifest model, agent authority classes, and evaluation regime are program design decisions to be declared, and there is no standard the program is failing to meet.

---

## 5. Cross-cutting item 4 — the synthetic data strategy

### 5.1 Applicable standards

| Standard | Revision / date | Status | Applicability |
|---|---|---|---|
| **DoDI 5000.61** — M&S Verification, Validation, and Accreditation | **Effective 17 Sep 2024**; reissues and cancels the 9 Dec 2009 version | Current | **Recommended — the documentation content specification** |
| **MIL-STD-3022 w/ Change 1** — Documentation of VV&A for Models and Simulations | Base Jan 2008; **Change 1, 5 Apr 2012** | **Current and expressly directed for use** by DoDI 5000.61 §3.2 | **Recommended — the template set** |
| **DoDM 5000.102** — M&S VV&A (DOT&E) | Effective 9 Dec 2024 | Current. **Does not supersede MIL-STD-3022 or DoDI 5000.61** | **Mandatory** if under DOT&E oversight |
| **DoD VV&A Recommended Practices Guide** | Current edition; version and date not stated | Current. Contains the **Data Quality Templates** invoked normatively by DoDI 5000.61 §3.1.a(6) | **Recommended** |
| **DoDM 5000.101** | Dec 2024 | Current | **Mandatory** — four-tier dataset regime, data cards, drift detection |
| **DoDI 5200.48** — Controlled Unclassified Information | **Effective 6 Mar 2020** | Current | **Mandatory** |
| **DoDI 5230.24** — Distribution Statements on DoD Technical Information | **Effective 10 Jan 2023.** Statement X is cancelled | Current | **Mandatory** |
| **32 CFR Part 2002** + NARA CUI Registry | Effective 14 Sep 2016 | In force | **Mandatory** |
| **NIST SP 800-171 Rev 3** | May 2024, 14 families | Final | **Mandatory** for non-federal systems |
| NIST SP 800-172 Rev 3 | Final Public Draft, 29 Sep 2025 | ⚠️ **Not final — do not cite as a requirement** | — |
| **NIST SP 800-226** — Evaluating Differential Privacy Guarantees | Mar 2025 | Final | **Informative** |
| ASME VVUQ1-2022 | 30 Dec 2022 | Current. Cited in DoDI 5000.61 References | **Informative** — UQ terminology |
| **NASA PCoE Prognostics Data Set Repository** | C-MAPSS, N-CMAPSS, IMS bearings, FEMTO/PRONOSTIA, Li-ion battery, milling, IGBT | Public, free | **Informative** |

### 5.2 No DoD synthetic-data standard was identified

Searched: the CDAO and Responsible AI corpus, the December 2024 DOT&E issuance set, DoDI 5000.97 Digital Engineering, the DoD Data/Analytics/AI Adoption Strategy, DoDI 5000.61 in full text, and the VV&A Recommended Practices Guide index.

⚠️ **Report this with its qualification.** Several hosts were inaccessible and DoDM 5000.102 is not archived anywhere reachable. **State it as "no synthetic-data standard identified; confirm with CDAO and the program's DOT&E action officer" — not as "none exists."**

What *does* govern is assembled from three directions:

1. **The VV&A regime**, because synthetic data produced by a degradation or physics model *is* a model output, and DoDI 5000.61's scope expressly includes *"associated data."*
2. **DoDM 5000.101's dataset regime** — four tiers with a withheld, operationally representative independent test set including out-of-distribution samples, plus *"documentation of dataset preparation, quality, governance, suitability, limitations, and a sustainability plan"* and mandatory data cards. **The "limitations" clause is where synthetic-data fidelity caveats belong.**
3. **NIST**, for the methods DoD does not supply — AI 600-1 for generative risk, SP 800-226 for differential-privacy evaluation if any generator is fitted to real data.

### 5.3 MIL-STD-3022 is current — the open question is resolved

**DoDI 5000.61 §3.2**, verbatim:

> *"Military Standard 3022 provides recommended templates for documenting VV&A. M&S practitioners **should use the Military Standard 3022 templates to the maximum extent practicable.** These templates address the minimum VV&A documentation requirements described in Paragraph 3.1."*

Its References list carries MIL-STD-3022 by its Change 1 date and notes availability on ASSIST. **A September 2024 DoD Instruction directing its use is materially stronger evidence than a status flag.**

The relationship is policy-plus-templates, not supersession: DoDI 5000.61 §3.1 sets minimum documentation content; MIL-STD-3022 supplies the templates. **DoDM 5000.102 supersedes neither** — DoDI 5000.61 §2.2 assigns DOT&E the lane for M&S supporting operational and live-fire test and evaluation, and 5000.102 is that delegated instrument.

**DoDI 5000.61 §3.1 requires three content groups:** VV&A context (dates, responsible party, version identification, **intended use**, accreditation criteria, activities performed, and *"sources of data, the date stamp of data, as well as associated metadata, in accordance with the data quality templates"*); V&V implementation and results (including *"capabilities, limitations, risks, potential impacts to the specific intended use, and assumptions"*); and accreditation results (activities, assessment, and the accreditation decision).

**§3.3 adds maturity and confidence assessments and uncertainty quantification.** For a platform whose contract output is `rul.p10/p50/p90` and a calibrated `p_failure`, **UQ is not an add-on — it is the product**, and §3.3 makes it part of the accreditation basis.

**The phrase "for a specific intended use" appears in all three of the standard's accreditation definitions.** That is the hook for scoping accreditation narrowly and affordably.

### 5.4 The classification question, answered from primary text

**Does schema-derived synthetic data raise CUI or classification concerns?**

The synthetic *values* are not automatically controlled — DoDI 5200.48 states that *"any new document created with information **derived** from legacy material **must be marked as CUI if the information qualifies as CUI**,"* so the test is applied to the new content rather than inherited. But three other things in the same artifact usually are controlled, and the determination belongs to the Original Classification Authority and the Security Classification Guide, not to engineering.

- **The schema is the exposed surface, not the values.** Controlled Technical Information covers *"technical data or computer software"* including *"specifications."* A field catalogue naming Navy equipment with its ESWBS and EIC decomposition, APL and AEL structure, NIIN identifiers, failure modes, and maintenance periodicities *is* technical information with military application — and a synthetic dataset ships that schema whether or not its rows are fabricated. **This is the most likely trigger, and it is the part programs overlook because they reason about "the data" rather than "the artifact."**
- **Fitted parameters carry more than rows do.** Real failure rates, MTBF values, inspection intervals, and degradation rates for *identified* Navy equipment are the reliability characteristics of a Navy platform. **The more faithful the synthesis, the weaker the argument that control was broken.**
- **Compilation is a cited concern.** DoDI 5200.48: *"OCAs will determine if **aggregated CUI** under their control should be classified,"* and *"**CTI compiled or aggregated may become classified.**"* A fleet-scale corpus correlating equipment inventory, failure behaviour, and maintenance intervals is exactly that.
- **Statistical synthesis is not a recognised decontrolling mechanism.** Nothing makes a transformation pipeline a competent decontrolling authority. **Treating generation as automatic decontrol is the specific error to avoid.**

### 5.5 Marking corrections that affect the design

**"FOUO" and "U//FOUO" are retired.** DoDI 5200.48 §3.4.b: *"There is **no requirement to add the 'U,'** signifying unclassified, to the banner and footer **as was required with the old FOUO marking (i.e., U//FOUO)**."* Document 03 §7.3's `ClassificationLabel` example lists `FOUO` as a caveat and must be corrected.

**Minimum marking is "CUI" in banner *and* footer**, plus a five-line **CUI designation indicator**. Lines 3 (*"all types of CUI contained in the document"*) and 4 (*"the distribution statement or the dissemination controls applicable"*) are structured fields — external justification for `ClassificationLabel` carrying a typed category list and dissemination-control list rather than free text.

**Constrain caveats to the ten authorised Limited Dissemination Controls:** NOFORN, FED ONLY, FEDCON, NOCON, DL ONLY, RELIDO, REL TO, DISPLAY ONLY, AC, AWP.

**Distribution statements** per DoDI 5230.24 Table 1: **CTI → B, C, D, E**. ⚠️ **The "Test and Evaluation" category is limited to B and C**, which constrains how a synthetic T&E corpus may be marked. Statement X is cancelled.

**System categorisation:** *"DoD information systems processing, storing, or transmitting CUI will be categorized at the 'moderate' confidentiality impact level."*

### 5.6 Recommendation

**Five actions on markings and controls:**

1. **Separate the artifact into four independently markable pieces: generator code · schema · fitted parameters · generated rows.** This is the highest-leverage decision in this area. A determination that the parameters are CTI then does not contaminate the rows, and a synthetic corpus can be shared at a lower level than the generator that produced it. Conflating them forces the whole repository to the highest level.
2. **Fabricate the identifiers.** Structurally valid but non-real EIC, ESWBS, hull, UIC, APL, and NIIN values from a declared fictitious range, documented in the dataset card. Real identifiers are the cheapest path to a CTI determination and buy nothing for model development.
3. **Do not fit generator parameters to real controlled data for the unclassified demonstration.** Use the NASA, FEMTO, and IMS open sources plus engineering judgment. **The way to keep the demonstration unclassified is to ensure no controlled parameter ever enters the generator.**
4. **Assume CUI//SP-CTI for the schema and parameter set until an OCA says otherwise**, with Distribution Statement B through E. **Scope Naval Nuclear Propulsion Information in or out explicitly and early** — CUI//SP-NNPI is a materially more restrictive regime and attaches the moment carrier or submarine propulsion-plant equipment is in scope.
5. **Constrain `ClassificationLabel` to the authorised vocabulary** and carry designation-indicator lines 3 and 4 as typed fields.

**Documentation to produce:**

- **The four MIL-STD-3022 products** — Accreditation Plan, V&V Plan, V&V Report, Accreditation Report — populated against DoDI 5000.61 §3.1's three content groups. Data Item Descriptions **DI-MSSM-81750** through **81753** are the CDRL vehicles, all revalidated 4 February 2026.
- **A narrow accreditation-for-intended-use statement**, exploiting the "specific intended use" language: *accredited for pipeline validation, interface conformance testing, and reviewer-workflow rehearsal; **not** accredited as evidence of model performance for fielding.*
- **A data card per synthetic dataset and a model card per model**, with the dataset card stating generator version, parameter provenance, fidelity claims **and their limits**, the identifier-fabrication scheme, and known distributional divergences.
- **A fidelity-evaluation protocol** — marginal and joint distribution comparison, failure-mode prevalence, censoring and truncation behaviour, and above all **whether a model trained on synthetic data transfers to real data.** This is where synthetic data fails silently.
- **A written statement that no model trained solely on synthetic data is a candidate for operational use.** DoDM 5000.101 requires the independent test set to be operationally representative, which synthetic data cannot satisfy by construction. Say it in the architecture rather than discovering it at a test-readiness review.
- **A program Synthetic Data Generation and Validation Plan**, citing DoDI 5000.61 §3.1 and MIL-STD-3022 for structure, DoDM 5000.101 for the dataset regime, NIST AI 600-1 for risk, and DoDI 5200.48 and 5230.24 for marking. More defensible than either silence or an invented standard number.

### 5.7 Convergence with the program's highest-consequence assumption

Assumption **A1** in document 06 §8 — that synthetic failure physics will be realistic enough for tier-2 and tier-3 modelling to be meaningful — is the highest-consequence assumption in the program, and its mitigation was **adversarial generator validation: trivial baselines must perform poorly before the data is accepted.**

That mitigation *is* the V&V evidence DoDI 5000.61 requires. **It should therefore be structured as a formal V&V plan under MIL-STD-3022 rather than as an internal engineering check.** The same work satisfies both, and framing it as the compliance artifact makes it far harder to skip under schedule pressure.

**On public reference datasets:** the NASA Prognostics Center of Excellence repository is the credible public foundation — C-MAPSS and N-CMAPSS turbofan degradation, IMS and FEMTO bearing run-to-failure, Li-ion battery, milling, IGBT thermal overstress. ⚠️ **State the domain mismatch honestly.** These are aero-propulsion, bearing, and battery datasets: excellent for validating a modelling *pipeline* — RUL calibration, censoring behaviour, drift detection, horizon selection — and poor as proxies for shipboard HM&E behaviour, OFRP mission profiles, or the 3-M documentation loop. Using them for pipeline V&V and saying so is defensible; presenting them as representative of Navy shipboard equipment is not.

**No public Navy maintenance or PHM reference dataset was found.** Plan on generating the corpus; do not plan on finding one.

---

## 6. Consolidated compliance table

| Standard / policy | Item | Applicability | What the program must do |
|---|---|---|---|
| MIL-STD-3034A | 1 | Mandatory | Adopt §3 definitions verbatim; align Failure Intelligence to the twelve phases; shape aggregates for DI-SESS export; treat Appendix F as the CBM+ linkage |
| ISO 14224:2016 | 1 | Recommended — anchor | **Purchase and transcribe Annex B.** Map levels 6–9 to ESWBS → EIC → InstalledItem(IUID) → NIIN |
| SAE GEIA-STD-0007C | 1 | Mandatory if LPD is a deliverable | Export to LSA-050 and LSA-058 |
| NAVSEAINST 4790.8 | 1 | Mandatory | Adopt CAUSE / WHEN DISCOVERED / ACTION TAKEN as the findings projection; publish a versioned many-to-many crosswalk; re-baseline against the current revision |
| DoDI 4151.22 · DoD 4151.22-M | 1 | Mandatory | Cite §1.2.j as the open-standards authority; implement RCM per 4151.22-M; **IUID, not EIC, is instance identity** (§1.2.d/l) |
| DoDI 8320.02 | 1, 3 | Mandatory | Register the taxonomy as an authoritative source with a single owner; publish vocabularies and business rules |
| IEEE 1856 · ISO 13374 · MIMOSA OSA-CBM | 1 | Recommended | Map the pipeline onto DA/DM/SD/HA/PA/AG and cite the Navy DUST provenance |
| MIL-STD-1629A | 1 | **DO NOT CITE** | Cancelled 4 Aug 1998, "(NO S/S DOCUMENT)." Use ANSI/AIAA S-102.2.4 or IEC 60812:2018 |
| MIL-STD-2173 / MIL-HDBK-2173 | 1 | **DO NOT CITE** | Both cancelled 1999. Use NAVAIR 00-25-403 |
| CNSSP 32 · CNSSI 1253 | 2 | Mandatory if NSS | Establish NSS status in writing; FedRAMP High plus Appendix D overlays at HHx; separate C/I/A levels |
| CSP SRG V1R7 + Mission Owner SRGs | 2 | Mandatory | **Do not cite the superseded Cloud Computing SRG.** IL5 requires physical or NSA-validated cryptographic separation |
| Impact Level scoping | 2 | **Decision required** | **IL5 no longer covers CUI.** CUI-only → IL4 (HHx); NSS → IL5. Written AO determination |
| Container Platform SRG V2R4 · Kubernetes STIG V2R6 · ASD STIG V6R4 · host OS STIGs | 2 | Mandatory | Build into the image pipeline. **Argue time correctness at the host-OS layer — the Kubernetes STIG has no time rules** |
| DoD Zero Trust Overlays v1.1 | 2 | Mandatory tailoring source | Select SC-45 and SC-45(1); adopt 1 ms granularity, daily comparison, 1 s resync. **Never cite the withdrawn AU-8(1)** |
| DoD ZT Reference Architecture v2.0 | 2 | Informative | **Not DDIL authority** |
| API Technical Guidance MVCR 3 | 2, 3 | Recommended | Cite for DDIL testing, alternate code paths, and §9.1.6 real-time-system isolation. **Not** authority for outbox design |
| DoDI 8540.01 | 2 | Conditional | Only if crossing classification levels. Engage the cross-domain support element at Pre-RMF Step 0 |
| DoDI 4650.08 / DoDD 4650.05 | 2 | Mandatory | NAVWAR-environment testing; check for a CJCSI 6130.01G waiver if commercial GNSS or NTP is primary |
| CP-10(2), AU-4(1), AU-6(3), AU-10, AU-12(1), SC-8, SC-16, SC-28 | 2 | Mandatory | Claim explicitly; CP-10(2) is what the outbox satisfies |
| Iron Bank | 2 | Informative | **No ATO or STIG inheritance; IL2 only.** Plan the IL2-to-enclave path and a disconnected mirror |
| 10 U.S.C. §§ 4401–4403 | 2, 3 | Mandatory | Use the statutory term **"modular system interface."** Retrieve PL 119-60 amendments |
| DoDM 5000.101 | 3, 4 | Mandatory for supervised models | Four-tier datasets with a withheld operationally representative independent set; data cards; drift detection. **Does not apply to generative surfaces** |
| DoD AI Ethical Principles · EO 14319 · NIST AI 600-1 | 3 | Mandatory / Recommended | The governance stack for the agent surface |
| DoDI 5000.61 + MIL-STD-3022 + VV&A RPG Data Quality Templates | 4 | Recommended | Four VV&A products against §3.1's three content groups, with narrow accreditation-for-intended-use, plus maturity and UQ per §3.3 |
| DoDM 5000.102 | 4 | Mandatory under DOT&E oversight | Read it; confirm it does not displace MIL-STD-3022's templates |
| DoDI 5200.48 · 32 CFR 2002 · NARA CUI Registry | 4 | Mandatory | Banner and footer; five-line designation indicator; moderate categorisation; **remove FOUO and U//FOUO**; scope NNPI; route aggregation to the OCA |
| DoDI 5230.24 | 4 | Mandatory | Statements B–E for CTI; **T&E category limited to B and C**; Statement X cancelled |
| NIST SP 800-171 Rev 3 | 4 | Mandatory for non-federal systems | Flow down via DFARS 252.204-7012 |
| NIST SP 800-172 Rev 3 | 4 | **DO NOT CITE as a requirement** | Still a Final Public Draft |
| NASA PCoE datasets | 4 | Informative | Pipeline validation only; **state the domain mismatch** |

---

## 7. Do not cite — cancelled, superseded, or misattributed

| Document | Status |
|---|---|
| **MIL-STD-1629A** (FMECA) | **Cancelled 4 Aug 1998.** ASSIST title reads "(NO S/S DOCUMENT)" — no superseding DoD standard |
| **MIL-STD-2173(AS)** | Cancelled 1 Sep 1999 |
| **MIL-HDBK-2173(AS)** | Cancelled 30 Nov 1999. Use NAVAIR 00-25-403 |
| **DoD Cloud Computing SRG v1r4** | Superseded 14 Jun 2024 by the CSP SRG |
| **AU-8(1) / AU-8(2)** | Withdrawn in NIST SP 800-53 Rev 5; moved to SC-45(1) / SC-45(2) |
| **Distribution Statement X** | Cancelled; use the export-control category |
| **"FOUO" / "U//FOUO"** | Retired by DoDI 5200.48 |
| **NIST SP 800-172 Rev 3** | Final Public Draft — not a requirement |
| **DDS-TSN 1.0** | Beta — not normative |
| **NTPv5** | Internet-Draft — not usable for planning |
| **DoDI 8510.01 dated 2014** | Reissued **19 Jul 2022** and retitled. Widely-mirrored older citation is stale |
| **DoDI 5000.61 dated 2009** | Reissued **17 Sep 2024** |
| **DoDI 5000.02 dated 2015** | Current version is 23 Jan 2020 |
| **"Key interface"** | Legacy OSJTF term; the statutory term is "modular system interface" |
| **"How Malfunctioned" as a 2-Kilo field** | It is a Naval Aviation field (VIDS/MAF), not a ships 3-M field |
| **MIL-HDBK-217 Revision G** | Does not exist. Notice 2 (1995) is the last issue |

**Organisational renaming.** Multiple current DoD documents now read "Developed by DISA for the DoW," and the Department of Defense to Department of War renaming is visible in primary-source mastheads. **Cite issuance numbers, not organisation names.**

---

## 8. Unverified — do not present as fact

**Taxonomy:** the complete ISO 14224 Annex B code set and the exact normative labels for levels 6–9 (paywalled; six retrieval routes attempted) · ANSI/AIAA S-102.2.4 revision and date · SAE JA1011's seven evaluation questions · NAVSEAINST 4790.8 current revision and whether its code sets changed · NAVAIR 00-25-403 current revision · whether a Navy S1000D business-rules standard exists · NAVSEAINST 4790.27 and OPNAVINST 4790.16 dates.

**Outbox and DDIL:** the ASSIST record for MIL-STD-2045-47001 · the contents of CNSSI 1253E Attachment 3 (FOUO) · the DoD instrument designating a time standard (DoDI 4650.08 and DoDD 4650.05 ruled out by full-text search) · CJCSI 6130.01G · PL 119-60's amendments to 10 U.S.C. §§ 4402–4403 · whether any current Navy requirement mandates DDS · **any public afloat bandwidth or latency figure — none obtained; do not put a rate or latency number in a deliverable.**

**Synthetic data:** MIL-STD-3022's ASSIST status field (status established instead by DoDI 5000.61 §3.2) · DoDM 5000.102's text · the VV&A Recommended Practices Guide version and date · DoDM 5200.01 Volume 1's compilation text · whether any DoD synthetic-data guidance exists behind inaccessible hosts · whether any Navy PHM reference dataset is publicly released.

---

## 9. Immediate actions

| Action | Owner | Why now |
|---|---|---|
| **Obtain a written AO determination of NSS status** | Program | Drives IL4-versus-IL5 and the entire control set; also settles federal AI-policy applicability. One memo, two questions |
| **Purchase ISO 14224:2016** | Program | Annex B is the deliverable content for the taxonomy anchor and has no free substitute |
| **Re-baseline the 3-M code sets against the current NAVSEAINST 4790.8 revision** | Engineering | The published sets are from 2003; any delta is a taxonomy version bump |
| **Remove FOUO and U//FOUO from document 03 §7.3** | Engineering | Retired marking |
| **State in the SSP that same-level ship-to-shore sync is not cross-domain** | Program | Forecloses an expensive mis-scope that would put human review in the sync path |
| **Budget a local stratum-1 time reference with holdover** | Program | 1 ms granularity while disconnected is not otherwise achievable |
| **Adopt "potential failure" as the term for the platform's core output** | Architecture | MIL-STD-3034A §3.9.3 defines it exactly; a NAVSEA term beats an invented one |
| **Restructure generator validation as a MIL-STD-3022 V&V plan** | Engineering | Same work, and it becomes the compliance artifact for the program's highest-consequence assumption |
