# Navy Data Systems and Synthetic Data Schemas

| | |
|---|---|
| **Status** | Draft. Supersedes the LOW-confidence configuration estimates in [06 §7](06-demo-decisions-and-assumptions.md) |
| **Purpose** | Document the Navy data systems this platform models, at schema level, from public sources; and specify how each drives each sub-application |
| **Why this matters** | Realism of identifiers, code values, and record structures is what makes the demonstration credible to Navy stakeholders. Fabricated schema detail is worse than an acknowledged gap, because a reviewer recognises it immediately |
| **Research date** | 4 August 2026 |
| **Sources** | Public only: OPNAV and NAVSEA instructions, NAVSUP publications, JFMM, NAVEDTRA training manuals, DoD 4100.39-M, DTR 4500.9-R, PLCS DEX, Naval Vessel Register, NPS theses |
| **Classification** | Internal |

---

## 1. Evidentiary rules

Every concrete claim below carries a public source. Three markings are used throughout:

| Marking | Meaning |
|---|---|
| **DOCUMENTED** | Verbatim from a cited public source |
| **PARTIALLY DOCUMENTED** | Structure established, values or lengths incomplete |
| **NOT PUBLICLY FOUND** | Searched and not located. **Do not fabricate.** Leave the field blank or generate from a reserved synthetic range |

The prohibition on fabrication is operative, not aspirational. Research corrected eight premises that were carried into the original briefs — including three that would have been built directly into schemas. Those corrections are recorded in §9.

**Currency caveat.** Several core publications are dated 1997–2005. The *code structures* are stable and still normative — the June 2026 Defense Transportation Regulation cites the MILSTRIP manual normatively, and the October 2025 status-code appendix matches the 1998 series and count. But **organizational names have changed** and must be modernised: NAVICP → NAVSUP WSS, FISC → NAVSUP FLC, SPAWAR → NAVWAR, DBOF → NWCF, DRMS → DLA Disposition Services. Getting the codes right and the organisation names wrong is the most likely way to look dated.

---

## 2. System landscape

| System | Role | Public documentation |
|---|---|---|
| **CDMD-OA** | Configuration Data Managers Database–Open Architecture. *"The single authoritative source of information regarding ship's component configuration, software, and identification of associated logistics support"* | Part A of NAVSEA Technical Specification 9090-700D reproduced verbatim in PAFOS Chapter 7. Spec itself CAC-gated |
| **SCLSIS** | Ship Configuration and Logistics Support Information System — the process and data flow around CDMD-OA | PLCS DEX business information model publishes 47 real field names |
| **WSF** | Weapon Systems File. *"The parts level (Level C), parts inventory portions, and related secondary ship component level configuration data files (Level A)"* | PAFOS Chapter 7 |
| **3-M / OMMS-NG** | Maintenance and Material Management. Organisational-level maintenance documentation and the source of all failure labels | OPNAVINST 4790.4 series; JFMM Vol VI; NAVEDTRA 14326; NPS theses publish an 80-column record layout |
| **RSUPPLY** | Afloat supply, inventory, and financial management. Unit Level on small combatants and submarines; Force Level on large decks | **NAVSUP P-732 (374 pp) publishes the actual relational schema** |
| **Navy ERP** | SAP-based financial and wholesale supply system of record for six systems commands, 62,000 users | Program level only. **SAP tables, tcodes, and Z-objects are genuinely not public** |
| **COSAL** | Coordinated Shipboard Allowance List — the authoritative allowance document | NAVSUP P-485 Vol I ¶2090–2094; PAFOS Appendix A; NAVEDTRA 14079 |
| **OARS** | Open Architecture Retrieval System — ten-year maintenance history extracted from 3-M | JFMM Vol VI Chapter 32 |
| **CASREP** | Casualty Report — the ground-truth field-failure record | NAVEDTRA 14326; JFMM |
| **FLIS** | Federal Logistics Information System — the item catalogue. DB2 relational, ~1,000 group tables, ~5,400 data record numbers | DoD 4100.39-M, 18 volumes, Distribution Statement A |
| **MILSTRIP / MILSTRAP / DLMS** | Requisition and inventory transaction standards | NAVSUP P-409 (90 pp) |

### The answer to the GCSS-Army question

**There is no Navy ERP public training corpus comparable to GCSS-Army's.** Three independent research streams confirmed it. No SAP table names, transaction codes, IDoc types, custom objects, or Business Process Procedures are public; training sits behind CAC.

**The afloat corpus is nevertheless richer than GCSS-Army's for this problem.** RSUPPLY's user guide publishes real `table.column` names. The COSAL and allowance structures are documented field by field. JFMM Vol VI publishes the Navy's own reliability formulas. The 3-M side gives a real 80-column wire format. Predictive maintenance lives on the afloat side, which is the well-documented side.

**Consequent posture:** build ERP-facing objects on generic, publicly-known SAP MM and PM semantics — purchase requisition to purchase order to goods receipt; maintenance notification to order to material reservation — and take **every Navy-specific identifier and code value from the afloat publications**. Frame it as *SAP-shaped process, Navy-standard identifiers*. Do not assert specific Navy ERP table configurations; that is the one thing a Navy ERP functional analyst would catch.

---

## 3. Configuration and identity — Asset & Configuration Registry

### 3.1 SCLSIS record types — DOCUMENTED

The PLCS DEX business information model (© US DoD 2010) publishes 47 verbatim `SCLSIS: Record Type N, FIELD NAME (ABBR)` mappings. This is the closest public artefact to a SCLSIS data dictionary.

**Record Type 1 — ship header, 6 fields**

| Field | Abbr | Note |
|---|---|---|
| Unit Identification Code | `UIC` | See §3.3 |
| Ship Status | `STATUS` | |
| Hierarchical Structure Code Indicator | `HSCI` | Identifies *which* HSC scheme this ship uses (§3.4) |
| Type Commander Code | `TYCOM` | Values NOT PUBLICLY FOUND |
| Ship Type and Hull Number | `STHN` | A single field with separate type and hull portions |
| Ship Class | `CLASS` | **Expressed as the lead hull number** — 68 for NIMITZ, 51 for ARLEIGH BURKE |

**Record Type 2 — configuration item, 41 fields**

`SEI` · `SN` · `EIC` · `QTY` · `PAR SN` · `CAGE` · `SC` · `HSC` · `EFD` · `ESD` · `MCC` · `SCAT` · `CEI` · `MEC` · `FBM MEC` · `SAC` · `RPTG DATE` · `RPTG ACT` · `RPTG ID` · `RIN` · `RIC` · `PAR RIC` · `EIN` · `DISC` · `AEL COL` · `DO/VC` · `VSAC` · `VALDATE` · `VALWORTH` · `RNV` · `INSTDATE` · `ISC` · `LOC` · `NHA` · `PRID` · `PSDN` · `PSDIN` · `PSDN TNC` · `ISEA`

**Record Type 3** is `Lsd_metadata`, marked out of scope. Field list NOT PUBLICLY FOUND.

**Two fields carry the load, and they are easily confused:**

- **`RIC` — Repairable Identification Code.** *"Uniquely identifies a particular commodity. When the code is related to an Allowance Parts List or an Allowance Equipage List, it is known as an APL or AEL, respectively."* **This is the field that carries the APL/AEL number.**
- **`RIN` — Record Identification Number.** *"Identifies a record within the WSF/SCLSIS/SNAP/NTCSS databases… The RIN is basically an address used by these databases for automated retrieval."* An internal surrogate, not a domain identifier.
- **`PAR RIC`** is the RIC of the equipment that carries supply support when an item has no APL or AEL of its own — a real parent-fallback mechanism worth modelling.

Field **lengths** are NOT PUBLICLY FOUND except where a 3-M form field publishes one.

### 3.2 EIC — Equipment Identification Code — DOCUMENTED

**Seven alphanumeric characters**, confirmed by three independent sources (NAVEDTRA 14326, NAVSEAINST 4790.8C Appendix A, and a 3-M record layout with a 7-character field at positions 57–63). *"Identifies a specific hardware item from the highest to the lowest level. That is system to the component/subassembly level."*

Positionally segmented, and **truncated EICs are legitimate** — a two-character value such as `QD` identifies a subsystem only.

**Real values:** `QK0V000`, `QM93000`, `QW71000`, `TB04000`, `TB04600`, `5515000`, `5515100`, `5515300`.

### 3.3 UIC — DOCUMENTED, and a correction

SECNAVINST 5400.48 ¶2c: *"A **five or six-character** alphanumeric code… In systems using a six-character UIC, the first character of the UIC is a Service identifier."* Navy DoDAAC first position is N, Q, R, or V, and **ships use `R` (Pacific) or `V` (Atlantic)**.

So `R21313` is the six-character DoDAAC-prefixed form of the five-character UIC `21313`. **Model UIC as five characters, with an optional leading Service prefix in DoDAAC and requisition contexts.**

**Real UICs from the Naval Vessel Register:** DDG 51 = `21487` · CVN 68 = `03368` · SSN 774 = `23013` · LCS 1 = `20126` · LCC 20 = `20001` · SSN 780 = `20002`. Twenty-three TICONDEROGA-class UICs are also available (CG 47 = `21281` through CG 69 = `21684`).

### 3.4 HSC and ESWBS — PARTIALLY DOCUMENTED, with a correction

**HSC is Hierarchical Structure Code**, not "Hull, Ship, Class." *"Identifies the functional/hierarchical relationship of the ship, ship system and equipment… The numbering method may differ in type."* Because the format varies by ship, Record Type 1 carries **`HSCI`** to identify which scheme applies. **There is therefore no single fixed HSC layout**, and an architecture that assumes one is wrong. Sibling schemes: AILSIN, CIN, FGC.

**ESWBS** is one such scheme. Document number is contested: `S9040-AC-IDX-010` per JFMM Vol VII Appendix 4E (FY23 and FY26 editions, three independent confirmations) versus `S9040-AA-IDX-010` per the 2010 PLCS DEX — most likely a revision change. **Cite `-AC-` as current.** The **code content is NOT PUBLICLY FOUND**, and any nine-group summary table circulating informally should be treated as unusable (ESWBS `843` = ballast contradicts it).

**Design consequence for the Registry:** the ESWBS hierarchy in document 01 §6 must be modelled as *one instance of a variant scheme selected by `HSCI`*, not as the universal structure. This is a real change to the Phase 3 design of the Registry.

### 3.5 Hull number rendering — DOCUMENTED, and a correction already applied

SECNAVINST 5030.8D Enclosure 6: *"**Hyphens will not be used in the hull number of any ship or craft.**"*

Correct: `DDG 51`, `CVN 68`, `SSN 774`, `LCS 1`, `T-AO 187`. Trailing `N` denotes nuclear propulsion; leading `T-` denotes Military Sealift Command; `F` denotes foreign construction.

The popular `DDG-51` form is contrary to instruction and is the kind of detail a Navy reviewer notices on sight. Documents 01, 03, and 06 have been corrected.

### 3.6 Configuration change transaction

**OPNAV 4790/CK, Configuration Change Form.** *"Whenever any system, equipment, component, or unit within the ship is installed, removed, modified, or relocated, the change must be reported."* Transaction and action **code values are NOT PUBLICLY FOUND.**

Data flow: 3-M up-line reporting → **RAD/RADWeb** (*"the data file transfer and tracking mechanism for CDMD-OA"*) → CDMD-OA → WSF → **ASI (Automated Shore Interface)** batch, processed in RSUPPLY by job `JSS117` (Unit) or `JSS135` (Force) → ship's allowance files.

**ASI is a batch synchronisation process, not an identifier.** An earlier brief modelled an "ASI number"; there is no such thing.

**Onboard roles:** the Supply Officer is the Configuration Manager for afloat activities; the 3-M Coordinator manages the maintenance data subsystem; the Leading Storekeeper is the RSUPPLY functional area supervisor.

### 3.7 Drives which sub-application

| Element | Sub-application | Use |
|---|---|---|
| SCLSIS Record Types 1–2 | **Registry** | The configuration item model. `RIC`/`PAR RIC` supply the parts-support linkage; `INSTDATE` and `SN` support installed-item identity |
| EIC (7 char, truncatable) | Registry, PdM, Scheduling | Equipment identity and the maintenance join key |
| UIC | Registry, Scheduling, Supply | Ship identity; also the first five characters of every requisition document number and every JCN |
| HSCI / HSC variants | **Registry** | Hierarchy must be scheme-aware, not ESWBS-fixed |
| OPNAV 4790/CK | Registry, Scheduling | The configuration-change transaction that closes the maintenance-to-configuration loop |

---

## 4. Allowance and parts — Supply Chain & Inventory

### 4.1 APL and AEL number formats — DOCUMENTED

PAFOS Chapter 6 Appendix B: *"Ordnance Fire Control Systems and Electronics systems have eight (8) characters. Hull, Mechanical, and Electrical (HM&E) equipment have nine characters. Use of APL prefixes and suffixes can expand the number to a total of 11 characters. Allowance Equipage Lists (AELs) have 10 characters."*

| Type | Length | Structure |
|---|---|---|
| HM&E APL | 9 | First two digits = equipment/component category |
| Ordnance APL | 9 | First two characters `00` |
| ORDALT | 9 | First two characters `0R` |
| MACHALT (HM&E) | 9 | Alpha character in the 6th position |
| Electronic / GFCS APL | 8 | Carries a Section B in circuit-symbol-number sequence |
| Miscellaneous Repair Parts List | 9 | Always begins `89` |
| Allowance Components List | 10 | Last two characters `CA`–`CZ` except `X`; identifies no parts |

A `P` prefix indicates an **incomplete APL**.

**AEL first-digit series:** `0-` Ordnance Equipage · `1-`/`2-` HM&E · `3-NDI` Portable COTS · `3-HZ` HazMat Consumables · `4-` Flag/staff · `5-` FBM · `6-` Nuclear Reactor Plant · `7-` Portable Electronics Test Equipment · `8-` TRIDENT · `9-` Nuclear Weapons.

HM&E AEL categories: `1-34xxx` Galley · `1-38xxx` Air Purifying and Ventilation · `2-2400x` Navigational · `2-4700x` Portable Pumps · `2-88xxx` Damage Control · `2-93xxx` Fire Fighting · `2-95xxx` Diving.

⚠️ The source is internally inconsistent on AEL length — Appendix B says 10, Appendix D's positional scheme implies 11, and real examples show both (`A004230048` at 10; `2-260034096` at 11). **Model 10–11 and state the ambiguity.**

**Real values, all publicly sourced:** APLs `00423A759`, `701110382` (LM2500 gas turbine main fuel control), `701110383` (compressor inlet temperature sensor), `052050008`, `616050177C`. AELs `A004230048` (AEGIS antenna group), `A00423A068` (AN/UYQ-70 support equipment), `0-00423A105` (MK 41 Mod 15).

### 4.2 COSAL structure — DOCUMENTED, and a correction

**Three parts, not five.** PAFOS Appendix A-2.1: *"Automated COSALs are structured in **three** major parts."*

- **Part I** — six index sections: SOEAPL (summary of effective APLs/AELs); Section A alphabetical by noun name; Section B by service application; Section C APL/AEL → EIC; Section D EIC → APL/AEL; Section E AILSIN/FGC → APL/AEL
- **Part II** — Section A APLs; Section B circuit symbol data (now on separate media); Section C AELs
- **Part III** — the SNSL, in seven sections: A Storeroom Items; B Operating Space Items; CF Maintenance Assistance Modules; CR Ready Service Spares; D alternate-number cross-reference; E General Use Consumable List; F Forms and Publications

Scope exclusion, verbatim: *"The COSAL does not include ship's store stocks, resale clothing, bulk fuels, subsistence items, expendable ordnance, or repair parts for aircraft."*

**Part III Section A — the SNSL** is the shipboard allowance table and the join between predicted failure and parts allowance. Fourteen fields (NAVSUP P-485 Vol I ¶2094), including the many-to-many part-to-equipment linkage and the **Derivation Code** — *"A code used to reflect what determined the computed SNSL allowance."*

The **Derivation Code is the single most demo-relevant field located in the entire study.** Its whole purpose is recording *why* an allowance is what it is. A predictive system that writes a new derivation basis is filling a field the Navy already has. Its **value set is NOT PUBLICLY FOUND** (it lives in NAVSUP P-488, itself unlocated).

On-board allowance table column bands: `1 | 2 | 3 | 4 | 5-8 | 9-20 | 21-50` equipments. AELs use eight columns, selected by CDMD-OA's `AEL COL` field.

### 4.3 Allowance computation — DOCUMENTED, and directly implementable

```
UR = POP × BRF / 4
```

where UR is the usage rate, POP the installed population, and **BRF the Best Replacement Factor** — *"the actual Fleet reported usage… as reported by fleet users and recorded in the 3-M system"*, updated annually.

| Rule | Value |
|---|---|
| Carried as an on-board repair part | UR ≥ 0.50 |
| May be excluded | UR < 0.125 |
| Price-sensitive sparing | Items ≥ $2,000 spared at 4.0 |
| CASREP add-back | One hit for a Category 3 or 4 casualty in a class over two years, items < $10K, flagged **Allowance Derivation Code `Y`** |

Models: `.5 Price Sensitive FLSIP Plus`, `.25 FLSIP`, `.10 MOD-FLSIP`, `RBS`, `TRIDENT`.

**This closes the loop the program exists to improve.** BRF is fleet-reported 3-M usage; the platform's contribution is a better-informed replacement factor and a defensible derivation basis. The formula is simple enough to reproduce exactly and to show being displaced by a model-derived estimate.

### 4.4 Requisition document number — DOCUMENTED, exact

Fourteen characters (NAVSUP P-409):

| Positions | Element | Example |
|---|---|---|
| 30 | Service code | `N` |
| 31–35 | Requisitioner UIC | `21487` |
| 36–39 | Julian date `YDDD` | `6058` |
| 40–43 | Serial, excluding letters `I` and `O` | `2101` |

Navy service codes: **`N`** other than fleet, **`R`** Pacific Fleet, **`V`** Atlantic Fleet.

### 4.5 Transaction vocabulary — DOCUMENTED

Approximately 120 A-series, 90 intra-Navy B-series, and 110 D-series document identifier codes, with **systematic third-character semantics** that make generation tractable: `_1` requisitioner, `_2` supplementary addressee, `_6` ICP-to-storage, `_8` to DAAS, `_9` from DAAS; `A` domestic NSN, `B` domestic part number, `1` overseas NSN.

Load-bearing families: **A0_** requisition · **AE_** supply status · **AS_** shipment status · **AC_/AK_** cancellation · **BRR/BRA/BRC/BRF/BRS/BRX** reservation lifecycle · **BPR/BPA/BPC/BPD** planned requirement lifecycle · **DYA→DYK** special program requirement.

**Advice code `2L`** is the officially sanctioned encoding for a prediction-driven abnormal quantity: *"Quantity reflected in the quantity field exceeds normal demands; however, this is a confirmed valid requirement."*

**The 5-series advice codes are the complete depot-level-repairable carcass vocabulary** — `5G` exchange certification, `5S` remain-in-place, `5R` release of planned requirement with turn-in, `5D` initial requirement or **increased allowance/stockage objective**, `5A` surveyed as missing or damaged beyond repair.

**Priority designators** come from the Force/Activity Designator × Urgency of Need matrix. **Design rule: a predicted failure is not yet "unable to perform."** Predicted requirements carry UND `C`, or `B` where degradation is already impairing performance, with a forward required delivery date. Generating UND `A` for a not-yet-failed item is logically wrong and a logistician will notice.

**Not to be used:** RDD codes `444`, `N__`, `E__`; unit of issue `ST`; routing identifier codes `S9M`, `S9T`, `SMS`, `NRP`. All either NOT FOUND or affirmatively wrong.

### 4.6 Cognizance symbols — DOCUMENTED

**COG is the single most important Navy-specific field in the supply model.** It simultaneously encodes funding source, responsible inventory control point, and — with SMR recoverability — whether a carcass obligation exists.

First character: `1, 3, 5, 7` Navy Stock Account, requisitioner pays · `9` Defense Stock Fund purchase held in NSA, pays · `2, 4, 6, 8` Appropriations Purchase Account, issued without charge · `0` not carried in the stores account. Ninety-four symbols are in use.

Shipboard HM&E: **`2S`** major shipboard HM&E equipment (NAVSEA, APA) · **`7H`** depot-level repairable shipboard and base equipment (NAVSUP WSS, NWCF) · **`3H`** field-level repairables · **`1H`** general consumables · `9N`/`9C`/`9G`/`9Z` Navy-owned DLA material · `0S` reactor plant technical manuals.

A distribution weighted toward `2S`, `7H`, `3H`, `1H`, and `9N` is defensible for shipboard HM&E.

### 4.7 SMR codes — DOCUMENTED, six positions

Current authority: AR 700-82 / SECNAVINST 4410.23A / AFMAN 21-106, 29 August 2020.

Structure: **source (1–2) + maintenance use (3) + maintenance repair (4) + recoverability (5) + Service option (6)**. Recoverability is **one** character, not two.

Navy-specific: positions 3–5 map onto **Afloat (`F`) / Ashore (`H`) / both (`G`, Navy only) / Depot (`D`)** rather than the Army's crew-field-sustainment ladder; `Z` in position 3 is Navy-only; numeric ship-class sub-codes `2`–`6` are Navy-only.

**SMR is the most important table for demand modelling**, because the source code partitions the demand model itself:

| Source | Demand behaviour |
|---|---|
| `P*` | Stocked and forecastable |
| **`XA`** | **No independent demand — requirement is met by replacing the next higher assembly.** A prediction on an XA part must be translated into next-higher-assembly demand |
| `K*` | Kit-driven |
| `M*` / `A*` | Demand is for raw material or components |
| **`PB` insurance, `PG` sustained life support** | Little or no demand history. **Exactly where prediction has the highest value** |

Recoverability `D` or `L` means a depot-level repairable — a carcass and rotable-pool problem, not a consumption problem. `Z` means a true consumable. **The demand model must branch here.**

### 4.8 Item identification — DOCUMENTED

NSN = FSC (4) + NCB (2) + item number (7). FLIS stores NCB and item number **separately**, not as a monolithic NIIN. Composite key pattern from real FLIS group tables: `(NCB_CD, I_I_NBR, MOE_RULE_NBR, EFF_DT)`.

**A realistic shipboard catalogue is heterogeneous**, and almost no synthetic dataset gets this right:

| Form | Structure | Rule |
|---|---|---|
| NSN | FSC + NCB + item number | Standard |
| Permanent NICN | `LL` in positions 5–6 **and `C` in position 7** | Requisitioned via DD 1348-6 |
| Temporary NICN | `LL` in 5–6, any letter except `C` in 7 | Periodically converted to NSN; conversion carries status code `BG` |
| LICN | FSC of a similar item + `LL` + 7 alphanumeric | **Never appears in supply transactions** — local use only |
| CAGE + part number | 5 + up to 32 | Escalates to DD 1348-6 above 10 characters |

**Federal Supply Classification: 78 groups, 645 classes.** Unassigned: 21, 27, 33, 50, 57, 64, 82, 86, 90, 92, 97, 98. FSG 60 (Fiber Optics) **is** assigned.

Shipboard HM&E classes that mark a dataset as genuinely naval: **2010** ship and boat propulsion components · **2030** deck machinery · **2040** marine hardware and hull items · **4320** power and hand pumps · **4410** industrial boilers · **4420** heat exchangers and steam condensers · **4620** water distillation, marine and industrial · **4810/4820** valves powered and non-powered · **5845** underwater sound equipment · **6320** shipboard alarm and signal systems · **6605** navigational instruments · **6680/6685** flow, level, pressure and temperature measuring.

Authentic detail worth including: unit of issue **`SO` = Shot**, 15 fathoms or 90 feet, correct for anchor chain.

### 4.9 Drives which sub-application

| Element | Sub-application | Use |
|---|---|---|
| APL/AEL formats and categories | Registry, Supply | Equipment-to-parts identity |
| SNSL 14 fields, **Derivation Code** | **Supply** | The allowance table, and the field a predictive system writes into |
| `UR = POP × BRF / 4` and thresholds | **Supply** demand forecasting | The existing allowance computation the platform improves |
| Document number, DIC families, status codes | **Supply** | Requisition documentary lifecycle |
| Advice codes `2L`, `5G`/`5S`/`5R`/`5D` | Supply | Prediction-driven quantity; repairable carcass flow |
| Priority designators, F/AD × UND | Supply, Scheduling | Correct urgency for a *predicted* rather than actual failure |
| COG, MCC, SMR, ERC | Supply, PdM | Repairable-versus-consumable branching; demand-velocity segmentation |
| NSN/NICN/LICN heterogeneity | Registry, Supply | Catalogue realism |
| Supply condition codes, purpose codes | Supply | Stock partitioning; reservation and earmarking |
| Transportation control number (17 char) | Supply | In-transit visibility |

---

## 5. Maintenance and failure — Scheduling, PdM, PMA, Failure Intelligence

### 5.1 The composite key — DOCUMENTED, and stated explicitly by the Navy

NAVEDTRA 14326: *"Both the EIC and APL/AEL numbers are necessary to provide complete identification."* Worked example: two identical motors in a water cooler and a refrigerator share an APL but have different EICs; two different motors in one ventilation system share an EIC but have different APLs.

**That is the maintenance-to-parts composite key, asserted by the Navy rather than inferred.**

### 5.2 Job Control Number — DOCUMENTED, exact

JFMM Vol VI ¶19.2.3.2: thirteen characters — **UIC (5 numeric) + Work Center (4 alphanumeric, left justified) + Job Sequence Number (4)**. Work Center is 4 positions on ships, 3 at intermediate activities.

And the finding that matters most:

> *"**The first position of the JSN is used to identify the tool or organization that created the 2-Kilo.**… The specific value contained within the first position of the JSN **provides enhanced data mining capabilities and facilitates data aggregation and analysis.**"*

Originator values are controlled centrally. **A predictive system would legitimately carry its own originator alpha code**, and the field exists explicitly to support the analysis this platform performs. This should be in the demonstration.

The JCN shares its UIC with the requisition document number, which is the natural join between the maintenance and supply sub-applications.

### 5.3 The 2-Kilo record layout — PARTIALLY DOCUMENTED

An NPS thesis publishes an 80-character record layout with character positions, from a 448,258-record NAVSEALOGCEN extract of AEGIS TICONDEROGA unscheduled maintenance, July 1987 – September 1992:

| Record | Layout |
|---|---|
| `B1` deferred maintenance action | `1-5 UIC` · `6-9 WC` · `10-13 JSN` · (`1-13` = JCN) · `14-17 ACTN DATE` · `57-63 EIC` · `64 WND` · `65 STA` · `66 CAS` · `67 DFR` · `79-80 record type` |
| `C5` closure | `1-5 UIC` · `6-9 WC` · `10-13 JSN` · `14-17 ACTN DATE` · `45-46 SFAT` · `47-50 MHRS` · `58 TI` |
| `M1`/`M5` | Non-deferred action and closure |
| `BA`–`BT`, `CA`–`CT`, `MA`–`MT` | Narrative: `1-13 JCN` · `14-17 date` · `18-77 narrative` |
| `UN`/`UF`/`UP` | Parts records |

Positions 57–63 confirm the 7-character EIC independently, and the layout shows Blocks 6–9 (When Discovered, Status, Cause, Deferral) as single-character adjacent fields.

**Treat as structurally indicative but historical.** The current data element dictionary and the modern "120 Card Format" are NOT PUBLICLY FOUND. The forms themselves — OPNAV 4790/2K, /2L supplemental, /CK configuration change — are public and named.

### 5.4 Status codes — DOCUMENTED, and central to label quality

JFMM Vol VI Chapter 32: *"**Status 2 is defined by 3-M as inoperative and Status 3 is degraded performance.** Limiting 2-Kilo data to Status 2 and 3 eliminates approximately **75% of all 2-Kilos written** and provides the basis for measuring mission degrading performance."*

**This is the Navy's own severity filter, and it should be the platform's label filter.** It also supplies a realistic generation ratio: roughly 25% of maintenance actions are mission-degrading.

### 5.5 Reliability formulas — DOCUMENTED, verbatim

```
Ao      = Uptime / (Uptime + Downtime)
T(pf)   = MTBF / (MTBF + MDT)
MTBF    = 1 / (Failures / (30.44 × 0.667 × Population))     [days]
```

where 30.44 is days in an average month and **0.667 is the sea-going operating-tempo approximation** — *"the percentage of time that the system will be ready to perform satisfactorily in an operating environment. For sea-going systems this operating tempo is approximated as 2/3-calendar time."* Population is actual equipment count for large HM&E, or platform count for small HM&E such as pumps and valves.

MDT is *"the mean number of days from the opening of Status 2 or 3 2-Kilos until the… CASREPs are corrected and the 2-Kilos closed. MDT is all-inclusive."*

**Using these formulas rather than generic reliability mathematics is a cheap, high-credibility choice**, and it makes the platform's estimates directly comparable to the Navy's own.

### 5.6 TMA/TMI ranking — DOCUMENTED

The Navy's existing priority corrective-action process, over a two-year window, using six attributes: 2-Kilo volume, man-hours, parts cost, high-priority failures (Status 2/3 plus Priority 1–3 CASREPs), high-priority downtime, and CASREP volume. Attributes scaled so three sigma equals 1.0, combined by Pythagorean vector addition.

**Realistic cardinalities:** *"approximately 43,000 APL and 4,200 EIC systems/equipment"*; the fleetwide matrix *"contains data on over 60,000 APLs"* across six type commanders.

**This is the closest existing analogue to the platform's criticality scoring, and the tier assignment engine should be positioned as its successor** — same inputs, principled model, and a forward rather than retrospective view.

### 5.7 Named 3-M reports — DOCUMENTED with real field names

**Report `L0106` — SLICR**, *"intended to identify problem equipments within the fleet"*: `APL` · `EIC` · `FAILURES` (*"count of maintenance actions with Status_Code 2 or 3"*) · `SF_MNHRS` · `PART_ISSUES` · `REPLCMNT_COST` · `IMA_MNHRS` · `VISITS` · `ACTIONS` · `OWNSHP_COST` · `COSAL` · `NET_COSAL` · `GROSS_COSAL` · `LOG_TIME` · **`MAINT_EFFECT`**.

Three metric definitions worth adopting verbatim:

- `COSAL` — *"the probability a requested item is stocked onboard whether or not it is available when requested"*
- `NET_COSAL` — *"the probability that a stocked item is onboard when requested"*
- `GROSS_COSAL` — *"the product of COSAL × NET effectiveness"*
- **`MAINT_EFFECT`** — *"The probability of **all required repair parts** for a given maintenance action being onboard"*

**`MAINT_EFFECT` is the right headline KPI for this platform** — it is the Navy's own measure of whether the ship had everything it needed to fix the thing, and improving it is precisely the value proposition. It complements rather than replaces warning lead-time coverage (document 06 §2): lead time measures the prediction, `MAINT_EFFECT` measures the outcome.

**Report `L0201`** gives the ten highest-`TOTAL_PRICE` parts per system with NIIN, quantity, and total cost.

### 5.8 CASREP — DOCUMENTED at type level

Four types: **INITIAL** (*"identifies the status of the casualty and any parts or assistance needed. Operational and staff authorities use this information to set priorities for the use of resources"*), **UPDATE**, **CORRECT**, **CANCEL**. Categories 2–4 by severity.

CASREPs drive priority 01–03 requisitions and are the escalation path a prediction is intended to prevent. Per-set field lists (NWP 1-03.1) are NOT PUBLICLY FOUND.

A public CASREP-to-COSAL cross-reference layout exists — `CASREP RATING | NIIN | COSAL ALLOWED | CASREP DEMAND QTY | DEMAND LISTING` — with real C-2 and C-3 ratings.

### 5.9 The documented analytic chain — the program's thesis, in the Navy's own words

NAVEDTRA 14326, Chapter 11:

> *"By sorting MDS data by **EIC**, the maintenance cost for each system, subsystem, or component of equipment can be determined…*
> *By sorting MDS data by **APL/AEL number**, the maintenance cost and material usage can be determined for specific items of equipment. **This data can be used by inventory control points to adjust the Coordinated Shipboard Allowance List.***
> *By sorting material usage by **NSN**, the ICPs can **analyze past usage and more accurately predict future usage** thereby providing better COSAL support."*

A 2002 Navy training publication describes, as established doctrine, exactly the analytic chain this platform implements. **The program is not proposing a new idea; it is proposing to do a documented one properly.**

### 5.10 Policy authority — DOCUMENTED

**OPNAVINST 4790.16C, Condition-Based Maintenance Plus Policy, 13 May 2024**, CNO N83:

> ¶5.e.(2): *"Minimize equipment failures and improve operational availability by providing on- and off-platform real-time prognostic and diagnostic health monitoring capabilities, **leveraging enterprise LOG IT systems to provide automated repair scheduling, updating preventive maintenance schedules and automated parts acquisition processes**…"*
> ¶5.e.(3): *"…**accurately pre-positioning required assets for an effective logistics footprint**."*

The instruction names AI and machine-learning analytics among enabling technologies and requires data scientists among trained personnel. It also requires that need be *"objectively determined through analysis of the platform's health monitoring system, **supported by reliability-centered maintenance (RCM) analysis**"* — so the demonstration should show the RCM linkage, not a bare model score.

### 5.11 Drives which sub-application

| Element | Sub-application | Use |
|---|---|---|
| EIC + APL composite key | **All** | The universal equipment join |
| JCN, with originator-coded JSN first position | **Scheduling** | Maintenance action identity; the predictive system's own originator code |
| 2-Kilo layout, Blocks 6–9 | **Scheduling** | Maintenance action capture; When Discovered / Status / Cause / Deferral |
| Status 2 / 3 filter | **PdM**, Scheduling | Label filter and severity definition; ~25% generation ratio |
| MTBF / MDT / T(pf) / Ao formulas | **PdM** | Tier-0 and tier-1 baselines, in the Navy's own mathematics |
| TMA/TMI six attributes | **PdM** criticality scoring | The existing analogue the tier engine succeeds |
| SLICR field set, `MAINT_EFFECT` | **Fleet Status** | Outcome KPIs |
| CASREP types and categories | **PdM**, Fleet Status | Ground-truth failure label; risk-flag severity mapping |
| OPNAV 4790/CK | Registry, Scheduling | Configuration-change transaction |
| BRF from 3-M usage | **Supply**, PdM | The existing allowance feedback the platform improves |

---

## 6. Predicted demand — the four documented pathways

Every step below is a real code, form, job, or report name.

1. **Health-monitoring data** produces a prediction on equipment identified by **EIC + APL**.
2. **Authority:** OPNAVINST 4790.16C ¶5.e.(2)–(3) mandates automated parts acquisition and asset pre-positioning from health-monitoring data.
3. **Near-term need** → requisition `A0A` with advice code **`2L`**, UND `B` or `C`, forward RDD, linked by **JCN** with a distinct JSN originator alpha.
4. **Beyond-horizon need** → **Special Program Requirement `DYA`** → ICP status `DYK`/`PA`, or **`PB`** (held until procurement lead time from the support date) → **`PR`** (*"immediate requisition is needed"*). A fully documented closed loop for a forecasting activity.
5. **Protect specific assets** → reservation `BRR` or planned requirement `BPR` with **purpose code `S`**; `BFU` on drawdown-date lapse.
6. **Repairables** → advice `5G`/`5S`/`5R`, turn-in `BC1`, condition `F → M → A`, carcass tracking job `JSL326`, purpose code A→V/W with status `RV`.
7. **Structural change** → **OPNAV 4790/CK** → CDMD-OA → WSF → **ASI** (`JSS117`) → revised SNSL allowance quantity with an updated **Derivation Code**.
8. **Retail levels** → **RSUPPLY Level Setting (`JSI205`) in Trial Run mode**, showing revised AMD, RO, and RP, gated by the Recomputation Test percentage (suggested range 020–030) — the Navy's own mechanism for previewing a level change before committing it.
9. **Measured** in `MAINT_EFFECT`, `GROSS_COSAL`, `LOG_TIME`, `OWNSHP_COST`.
10. **Counterfactual:** absent prediction this becomes a **CASREP** and a priority 01–03 requisition.

**RSUPPLY Level Setting parameters** (NAVSUP P-732 ¶4.5, ¶5.13): AMD over a 6–24 month base period; Demand Based Item qualification and retention by period and frequency; order and shipping time; safety level factor; **Recomputation Test percentage** *"designed to prevent massive adjustments in RO resulting from insignificant changes in AMD"*; endurance levels (1.0 = 30 days, 1.5 = 45, 2.0 = 60, 2.5 = 75); Trial Run producing a Reorder Review listing.

**Two independent findings make this the strongest part of the program case:**

- RAND documents that *"forecasting and filtering demand data"* was a Naval Operational Supply System requirement that could not be satisfied. **Demand forecasting is an explicitly documented Navy afloat-supply capability gap.**
- RAND also documents that Navy ERP *"does not currently offer a detached capability and cannot support cross-domain solutions."* **Disconnected operation is the documented reason Navy ERP does not run the ships** — independent validation of the DDIL architecture seam in document 01 §12.

---

## 7. Synthetic data generation

### 7.1 Identifier policy

**Do not scrape a mirror for real NSNs.** Access was blocked throughout research, and provenance would be questionable. Instead:

- **Synthetic NIINs from a reserved block, explicitly labelled synthetic**, inside **real Federal Supply Classes**
- **Real code values throughout**: COG symbols, MCC, AAC, SMR, criticality codes, condition codes, purpose codes, unit of issue, DIC and status codes
- **APL/AEL-shaped identifiers** with correct lengths and category semantics per §4.1
- **Real UICs** from the Naval Vessel Register for the instantiated hulls
- **Real EIC-shaped values** with correct 7-character positional structure

This is indistinguishable in shape to a Navy logistician while being unambiguously fabricated — which is what a demonstration requires.

### 7.2 Realism rules that most synthetic datasets get wrong

| Rule | Source |
|---|---|
| Hull numbers use a **space**, never a hyphen | §3.5 |
| A catalogue is **heterogeneous** — NSN, permanent NICN, temporary NICN, LICN, CAGE+part number — and LICNs never appear in transactions | §4.8 |
| **~25% of maintenance actions** are Status 2 or 3 | §5.4 |
| Predicted requirements carry **UND C or B, never A** | §4.5 |
| `XA`-coded parts generate **next-higher-assembly** demand, not their own | §4.7 |
| Repairables (`7_` COG, recoverability `D`/`L`) follow a **carcass** flow, not consumption | §4.6, §4.7 |
| Unit price uses **implied two decimals**, with a `D` in the units position at or above $10M | DoD 4100.39-M Vol 12 |
| Fund codes and project codes are left **blank** — values NOT PUBLICLY FOUND, and they map to real appropriations | §4.5 |

### 7.3 Formal obligations

Synthetic data is not merely a convenience here. DoDI 5000.61 makes *"associated data"* a first-class object of verification, validation, and **accreditation for a specific intended use**, and requires recorded data sources, date stamps, and metadata. Existing data item descriptions exist for the plans and reports (DI-MSSM-81750 through 81753).

This converges with assumption **A1** in document 06 §8, the highest-consequence assumption in the program: the adversarial generator validation proposed there — **trivial baselines must perform poorly before the data is accepted** — is the V&V evidence these instruments require. It should therefore be structured as a formal V&V plan rather than an internal check.

Standards detail is pending the outstanding research in §10.

---

## 8. Revised capacity figures

These supersede the LOW-confidence estimates in document 06 §7.

| Quantity | Prior estimate | Revised | Basis |
|---|---|---|---|
| Fleetwide APL population | not estimated | **~43,000 APLs, ~4,200 EICs** in the TMA/TMI analysis population; **>60,000 APLs** fleetwide across six TYCOMs | JFMM Vol VI Ch. 32 — DOCUMENTED |
| Tracked installed items per surface asset | ~1,200 (LOW) | **Retain ~1,200 as a deliberate HM&E subset**, now defensible: the fleetwide APL population is ~43,000 across all ship types and all commodity areas, so a single-hull HM&E subset in the low thousands is proportionate | Derived |
| Distinct NIINs in the demo catalogue | ~2,500 (LOW) | **Raise to ~4,000–6,000.** A single hull's COSAL runs to tens of thousands of line items; a curated HM&E subset at this scale is credible | Derived |
| Maintenance actions over 24 months | ~14,000 (LOW) | **Retain, and constrain the mix:** ~25% Status 2 or 3 | §5.4 |
| CASREP-severity events | ~180 (LOW) | **Retain**, and tie add-backs to the documented rule: one hit for a Category 3 or 4 casualty in a class over two years | §4.3 |

Still LOW confidence and not resolvable from public sources: per-asset configuration item counts for a specific class (CDMD-OA content is CAC-gated), and per-hull COSAL line-item counts.

---

## 9. Corrections to earlier premises

Eight premises were wrong, three of them in ways that would have been built into schemas.

| Premise | Correction |
|---|---|
| "HSC = Hull, Ship, Class" | **Hierarchical Structure Code**, and the format **varies by ship**, selected by `HSCI`. There is no universal layout |
| "ASI number" | **ASI is the Automated Shore Interface batch process**, not an identifier |
| "SMR positions 5–6 = recoverability" | SMR is 6 positions; **recoverability is position 5 only** |
| "COSAL has five parts" | **Three parts** |
| Hull numbers as `DDG-51` | **Space, not hyphen** — SECNAVINST 5030.8D |
| "SPCCINST 4441.170 is the COSAL manual" | **NAVSUP P-488** |
| "RIN carries the APL number" | **RIC** carries it; RIN is an internal record address |
| "FSG 60 is unassigned; 33 is deleted" | **FSG 60 is assigned** (Fiber Optics); **FSG 33 is unassigned**. 78 groups, 645 classes |

---

## 10. Remaining gaps and highest-value follow-ups

**Confirmed CAC-gated or unpublished:** NAVSEA 9090-700D beyond Part A · SCLSIS field lengths and Record Type 3 · OPNAV 4790/CK code values · TYCOM code values · **NAVSUP P-488** and P-485 Vol II · the current 3-M data element dictionary and 120 Card Format · full ESWBS code list · CASREP per-set field lists · ICAS channel taxonomy · **Derivation Code values** · full Allowance Type Code and SMIC tables · Navy ERP SAP internals.

**Three follow-ups with the highest return:**

1. **GEIA-STD-0007 / MIL-STD-1388-2B LSAR reliability data elements** — MTBF, maintenance replacement rate, annual operating requirement, task frequency, attrition rate. The formal bridge from "this bearing will fail" to "therefore the allowance quantity should be N." Free on the DoD standards repository; unreachable from the research environment.
2. **NAVSUP P-485 Volume II** — closes fund codes, project codes, the full routing identifier and cognizance lists, SMIC, and Allowance Type Code in one document. Highest value per unit effort.
3. **NAVSUP P-488** — the COSAL code-set reference, and the only known location of **Derivation Code** values. Since that field records *why* an allowance is what it is, it is the single most demo-relevant table still missing.

**Standards research outstanding:** taxonomy anchoring (ISO 14224 failure-mode code sets) and synthetic-data V&V standards. Both requested and pending.
