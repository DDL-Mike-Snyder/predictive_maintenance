# Build Framework 51 — Operator Console (`apps/web`)

| | |
|---|---|
| **Status** | Build framework, rev 1. **Binding on `apps/web`.** Second document of Wave 4. Consumes [50 — UI Design System](50-ui-design-system.md) entirely and re-decides nothing it decided; its sibling [52 — Practitioner Apps](52-practitioner-apps.md) owns the two Domino-hosted surfaces excluded in §18 |
| **Scope** | The twelve `apps/web` surfaces of the approved wireframe — sheet H (Persona Hub), sheet 00 (App Shell), and the ten destination sheets 01, 01B, 02, 03, 04, 05, 06, 07, 10, 11 — wired end to end: route path, component composition, gateway operation, response field, query key, polling interval, degraded rendering, loading/empty/unknown state, and test |
| **What this document is** | The field-by-field wiring layer. [50](50-ui-design-system.md) fixed *what components exist*; [30](30-gateway.md) and [20]–[28] fix *what operations exist*. This document is the join, and it is the first document in the program to perform that join for every screen. Where the join fails — a drawn column with no field, a route with no operation — §22 records it as a correction and the screen renders the gap rather than a fabricated value |
| **Primary design source** | [`docs/design/operator-console-wireframes.html`](../design/operator-console-wireframes.html), **rev 3, as approved**, read in full. Cited as **WF** with a sheet number and, where the claim is structural, the element. Every box, table column, chip, KPI, and button below is transcribed from that file; **no UI element is added and none is dropped** [50 §11.2 item 12] |
| **Binding build documents** | [50](50-ui-design-system.md) **in full** — §2 (tokens), §3 (components), §4 (routes), §5 (data), §7 (disclosure), §8 (accessibility), §11 (DO-NOT), §13 (corrections), §14 (open questions) · [30](30-gateway.md) §3.2, §3.4, §4.4–§4.8, §5.3, §6, §7.3, §8.1–§8.4 · [31](31-auth.md) §2.4, §3.1, §4.1, §5.8, §8 · [09](09-monorepo-and-conventions.md) §2.5, §2.6, §3.1–§3.2, §7.1, §8, §9 · [32](32-audit.md) §4.6, §6.1–§6.7, §10.4, §10.5, §10.7 · [20](20-registry.md) §4, §6 · [21](21-telemetry.md) §3, §5, §9 · [22](22-pdm.md) §2, §6, §9, §10 · [23](23-pma.md) §2, §3 · [24](24-scheduling.md) §3, §4, §9 · [26](26-supply.md) §2, §3, §7 · [27](27-fleet-status.md) §2, §3, §5, §6, §7, §8, §10 |
| **Binding architecture documents** | [03](../architecture/03-integration-contracts.md) §4, §7.1, §7.2, **§7.2.1**, §7.3, §13, §15 · [04](../architecture/04-subapplication-architectures.md) §2, §3, §5, §6, §7, §8, §11 · [06](../architecture/06-demo-decisions-and-assumptions.md) §2, §5, §6, §7 · [02](../architecture/02-domino-platform-assessment.md) §4.1, §4.3 |
| **Precedence** | [03](../architecture/03-integration-contracts.md) prevails on any contract surface. [09](09-monorepo-and-conventions.md) prevails on layout, stack, and conventions. [30](30-gateway.md) and [31](31-auth.md) prevail on operations and identity. **[50](50-ui-design-system.md) prevails on every token, component, router, fetch idiom, and accessibility rule.** WF prevails on *what is drawn*. Where this document appears to disagree with any of them, **this document is defective** and §22 is where the disagreement should already have been recorded |
| **Quantities** | Every figure traces to [06 §7](../architecture/06-demo-decisions-and-assumptions.md) or to a named field in a build document. **No count, cadence, threshold, or interval is invented here.** §3.4's polling table maps every query onto one of [50 §5.4]'s three existing settings and introduces no fourth |
| **Classification** | Internal. The demonstration operates single-level at `U` [03 §12, 06 §5], by configuration and not by assumption; §17.2 is the enforcement path the console exercises anyway |

---

## 0. How to read this document

Five markers, following [50 §0](50-ui-design-system.md) and [09 §1.3](09-monorepo-and-conventions.md):

- **`[50 §n]`**, **`[30 §n]`**, **`[03 §n]`**, **`[WF sheet nn]`** — dictated by that document or by the approved wireframe. Not negotiable at implementation time.
- **`[ESTABLISHED HERE]`** — no prior document fixes this, and [50](50-ui-design-system.md) did not either. This document makes the call once so that eleven screens do not make eleven different ones. The reasoning is always stated.
- **`[EXTENDS 50 §n]`** — [50](50-ui-design-system.md) decided the general rule and this document adds the case it did not have in front of it, **without contradicting it**. Every occurrence is also filed in §22 as an amendment ask against [50](50-ui-design-system.md), because [50 §12.2] makes its route tree and component inventory exact and an addition is therefore an edit to that document rather than a local liberty.
- **`[GAP]`** — a drawn element with no field, or a route with no operation. Rendered as an honest absence per §17, never as a fabricated value, and filed in §22.
- **`[OPEN]`** — genuinely undecided, listed in §23.

**Read [50](50-ui-design-system.md) in full before this document.** Nothing here is comprehensible without it and nothing here replaces it. Then read §1.3, then §3, then the section for the sheet you are building, then §17, then §19.

### 0.1 The three things this document assumes and does not re-argue

1. **The wireframe's blueprint aesthetic and its token set** are production, per [50 §0] decision 1 and [50 §2]. No screen below proposes a visual change; where a drawn element is inaccessible or unwired, the fix is a token *choice* or a data *source*, never a new colour, radius, or face.
2. **The component layer is [50 §3.5]'s inventory and nothing else.** Every screen section below names components from that inventory. Where a screen needs a behaviour the inventory has no component for, that is a `[GAP]` and a §22 row — **not a new component invented in a feature directory** [50 §11.2 items 12–13].
3. **No route is authorization-gated, in either direction** [50 §4.2]. Every screen below is reachable by URL by any authenticated operator; the server refuses what it must and the console renders `ProblemDetail` [50 §11.4 item 27].

---

## 1. Purpose, scope, and the reconciliation that happened after 50 was authored

### 1.1 What this document governs

| Concern | Section |
|---|---|
| The `apps/web` source layout, and where each screen's code lives | §2 |
| The route tree with, per route, its component, its operations, and its polling | §3 |
| Sheet 00 — the shell: topbar, identity, lookup, side nav, badge, banner, footer | §4 |
| Sheet H — the Persona Hub, and the real `authority_classes` → route mapping | §5 |
| Sheet 01 — Fleet Overview, its four KPIs, its map, and its two rollup boxes | §6 |
| The AOR map's static position table — its shape, its location, its rules | §7 |
| Sheet 01B — Vehicle Detail | §8 |
| Sheet 02 — Asset Browser, the configuration tree, the bitemporal toggle | §9 |
| Sheet 03 — Channel & Health View, the sparkline, completeness | §10 |
| Sheet 04 — Fleet-Risk Triage, the uncalibrated cell, the what-if surface | §11 |
| Sheet 05 — Work Package Planner, dispositions, deferrals | §12 |
| Sheet 06 — Stock & Requisition View, the reservation-set TTL | §13 |
| Sheet 07 — Bounded Review Queue, and the canary rule the console must not break | §14 |
| Sheet 10 — Unified Adjudication Queue: the filter controls WF omits, sort, claim, adjudicate, dual control | §15 |
| Sheet 11 — Remediation & Purge Queue: purge/rewrap, three signatures, the ledger | §16 |
| Error, loading, empty, degraded, and suppressed states, for every screen | §17 |
| What is *not* in this document — sheets 08 and 09 — and the outbound affordances | §18 |
| Testing: component, route, contract | §19 |
| DO-NOT list, additional to [09 §9] and [50 §11] | §20 |
| Definition of Done | §21 |
| Corrections to source documents | §22 |
| Open questions | §23 |

### 1.2 What this document does NOT govern

| Out of scope here | Governed by |
|---|---|
| Tokens, components, router, fetch library, disclosure components, accessibility baseline, persona-resolution *rule* | [50](50-ui-design-system.md). This document applies them; it does not restate their reasoning |
| Sheets 08 (Hypothesis Adjudication) and 09 (Redesign Case Builder) — routes, components, data, deployment | [52](52-practitioner-apps.md). §18 states the exclusion and specifies only the two launch affordances `apps/web` owns |
| Any wire type. The console hand-writes none [09 §2.6 constraint 1] | [10 §4.9](10-shared-packages.md), [09 §2.5](09-monorepo-and-conventions.md) |
| The gateway's composition, the queue's projection, rate limiting, classification enforcement | [30](30-gateway.md) |
| Every operation's semantics, DDL, and events | [20]–[28], [32](32-audit.md) |
| `apps/practitioner`'s base path, credential, iframe, and theme handling | [50 §6](50-ui-design-system.md), [52](52-practitioner-apps.md) |
| Print and export | **[OPEN]** — [50 UI-OQ-10], carried forward as §23 UI-OQ-10 unchanged |

### 1.3 Three of [50 §13]'s corrections landed before this document — verified against current text, not trusted

[50 §13](50-ui-design-system.md) was written before a reconciliation pass. Its corrections table is therefore **stale in three rows**, and this document verified each against the *current* text of the cited document rather than accepting [50](50-ui-design-system.md)'s own status column. The results change what is buildable.

| [50 §13] row | [50](50-ui-design-system.md)'s status | Current state, verified | Consequence here |
|---|---|---|---|
| **1** — `packages/ui` has no place in the monorepo tree, governance table, or workspace scope | **Blocking** | **CLOSED.** [09 §2.6](09-monorepo-and-conventions.md) now reads *"pnpm workspaces spanning `apps/*`, `packages/ts-common`, and `packages/ui`"*, and [09 §3.2](09-monorepo-and-conventions.md) carries the row *"`packages/ui` — Design tokens, Radix-based component library — `50-ui-design-system.md` [amendment 50-1]"* | `packages/ui` is a governed workspace package. §2's layout imports from it without qualification |
| **2** — warning lead-time coverage is a headline KPI on WF sheets 01 and 01B with **nothing to call** | **Blocking for sheets 01 and 01B** | **CLOSED.** [32 §10.7](32-audit.md) adds `GET /effectiveness/warning-lead-time-coverage?scope=&id=&horizon_days=&stratum=` on `audit`, marked *"[AMENDMENT — closes a BLOCKING gap for the operator console]"*, computing [27 §7.5]'s formula and carrying *"the lead-time distribution (p10/p50/p90), the covered and uncovered counts, the chance reference and flag rate, and the achievable-ceiling fraction"* plus `"source": "audit"`, `"computed_at"`, `"definition_ref"` | §6.3 and §8.2 wire the KPI. **But [27 §7.5]'s four presentation rules bind it, and a bare percentage as drawn violates all four** — §6.3 specifies the compliant rendering and §22 row 1 keeps the wireframe edit filed |
| **7** — no session identity operation, no logout, and [30 OQ-9] assumed a token the console does not hold | **Blocking the Persona Hub and the queue's default filter** | **CLOSED.** [30 §8.1.2](30-gateway.md) adds `GET /api/v1/gateway/session` (identity block, *"byte-identical to §3.2's token shape"*, with *"its six `authority_classes`"*) and `POST /api/v1/gateway/session/logout` (server-side RP-initiated logout, no client `end_session_endpoint` redirect). [30 §8.1.1](30-gateway.md) additionally adds the agent-invocation surface. [30 OQ-9](30-gateway.md) is now marked **[CORRECTED]** and reads *"The UI filters by `authority_class` using the roles from the session identity §8.1.2 returns — **not** 'its own token'"* | §4.3 and §5.2 wire real identity. **[50 §9.2]'s speculative field list is superseded**: the operation returns `fathom.identity`, whose subject field is **`subject_id`**, not `sub`, and which additionally carries `unit_path` and `qualifications` — §22 row 2. Cookie attributes and CSRF mechanism are now stated ([30 §8.1.2]: `HttpOnly`, `Secure`, `SameSite=Lax`, opaque identifier, Redis-backed, double-submit token on state-changing gateway-owned operations), so [50 UI-OQ-1] is **partially** closed — **the cookie's name and the CSRF token's cookie and header names are still unspecified**, and the console cannot send a double-submit token whose name it does not know (§23 UI-OQ-1) |

Two further rows changed state and matter to this document:

- **[50 §13] row 10** (`apps/practitioner` has no credential path) is **CLOSED** by [31 §5.8](31-auth.md). **[AMENDMENT]** Originally closed by extending [31 §5.4]'s two-credential shape to an app→gateway hop; a security review found that extension defective (one header name validating two structurally incompatible credentials), so [31 §5.8] was corrected instead to a token-exchange operation, `POST /api/v1/auth/practitioner-exchange` — a settled mechanism, not an interim. It changes nothing in `apps/web`, which holds a cookie and no token either way [50 §6.3], and it is [52](52-practitioner-apps.md)'s to consume.
- **[50 §13] row 5** (the composed-view envelope's `as_of` has no defined semantics) is **STILL OPEN**. [30 §3.4](30-gateway.md) still shows `as_of` in the envelope example and defines it nowhere. Every screen below therefore labels it **"composed at"**, per [50 §5.3] rule 5, and §22 row 3 carries the correction forward.

### 1.4 Sheet-to-route accounting, reconciled

[50 §1.6](50-ui-design-system.md) fixed the counts: fourteen sheets, twelve destinations, ten of them in `apps/web`, plus the hub and the shell. This document adds the third column — the operations behind each — and the fourth, which is the honest verdict.

| Sheet | Route | Fully wired from a real operation? |
|---|---|---|
| H — Persona Hub | `/` | **Yes.** `GET /api/v1/gateway/session` [30 §8.1.2] |
| 00 — App Shell | layout route | **Partially.** Identity and badge yes; the topbar lookup has **no operation** — `GET /assets` declares no query parameter anywhere in [20](20-registry.md) (§4.4, §22 row 4) |
| 01 — Fleet Overview | `/fleet-status` | **Partially.** Three of four KPIs, the map, and the risk-flag table yes; the 30-day delta, the flag total, and the per-class rollup are `[GAP]`s (§6, §22 rows 5–8) |
| 01B — Vehicle Detail | `/fleet-status/assets/:assetId` | **Partially.** Score, flags, system rollup, coverage yes; `rank 6 of 12 in class` is a `[GAP]` (§8, §22 row 9) |
| 02 — Asset Browser | `/registry`, `/registry/assets/:assetId` | **Partially.** Tree, baseline, chips, allowances yes; the asset-search filter is the §4.4 `[GAP]` |
| 03 — Channel & Health | `/telemetry/installed-items/:installedItemId` | **Yes**, with two rendering constraints [21](21-telemetry.md) imposes that WF does not draw (§10) |
| 04 — Fleet-Risk Triage | `/pdm`, `/pdm/installed-items/:installedItemId` | **Partially.** Every column yes; **the drawn ranking has no server-side sort and no console-available weight source** (§11.2, §22 row 10) |
| 05 — Work Package Planner | `/maintenance` **+ two child routes [EXTENDS 50 §4.2]** | **Partially.** Candidates, dispositions, deferrals yes; `Priority` has no field (§12, §22 row 11) |
| 06 — Stock & Requisition | `/supply`, `/supply/parts/:niin` **+ one child route [EXTENDS 50 §4.2]** | **Partially.** Stock, allowance, lead time, reservation set yes; `requisition.state`'s enum is **undefined in the corpus** (§13, §22 row 12) |
| 07 — Bounded Review Queue | `/pma` **+ `/pma/reviews/:reviewId` replacing [50 §4.2]'s `/pma/missions/:missionId`** | **Partially.** Candidate, evidence, actions, history yes; `Tags confirmed` and the mission-scoped route are `[GAP]`s (§14, §22 rows 13–14) |
| 10 — Unified Adjudication Queue | `/adjudication`, `/adjudication/:proposalId` | **Mostly.** List, filters, sort, claim yes; **`adjudicate` has no specified request body** (§15, §22 row 16). **[AMENDMENT]** The `authority_class` filter enum omitting `security_officer` (§22 row 15) is now resolved — `30-gateway.md` §4.5 added it |
| 11 — Remediation & Purge Queue | `/audit/remediations`, `/audit/remediations/:proposalId` | **Partially.** Queue, panel, receipt yes; **the queue row cannot represent a three-signature purge**, `Store` has no field, and the dissemination ledger has no read operation (§16, §22 rows 17–19) |

**Nine of twelve screens are partially wired, and that is the finding this document exists to produce.** Every partial is a named `[GAP]` with a §17 rendering and a §22 row. None is papered over with a plausible-looking number, because [30 §3.4](30-gateway.md) states the governing rule for all of them: *"The UI must render the gap; it must not render zero."*

### 1.5 Traceability

| Artifact | Source | Section |
|---|---|---|
| Source layout | [09 §3.1](09-monorepo-and-conventions.md), [50 §2.1], [50 §5.2] | §2 |
| Route tree | [50 §4.2], extended per §0's `[EXTENDS]` marker | §3.1 |
| Query-key factory | [50 §5.3] | §3.3 |
| Polling assignments | [50 §5.4], no new interval | §3.4 |
| Per-screen component composition | [50 §3.5] inventory × WF sheet elements | §4–§16 |
| Per-screen operations and fields | [30 §3.2], [30 §4.5], [20]–[28], [32](32-audit.md) | §4–§16 |
| Map position table | [50 §3.5], [50 §13] row 3's adopted interim | §7 |
| Persona → route mapping | [50 §9.1], [31 §2.4], [30 §8.1.2] | §5.2 |
| Queue filter controls | [30 §4.5]'s 22 parameters, [50 §13] row 8 | §15.3 |
| Dual control | [03 §7.2.1], [32 §6.1], [30 §4.5] | §15.6, §16.4 |
| State rendering | [30 §3.4], [27 §3.9], [50 §5.5], [50 §7] | §17 |
| Tests | [09 §2.6], [50 §10.2] | §19 |

---

## 2. `apps/web` source layout

**[ESTABLISHED HERE]**, and the shape is [50 §5.2](50-ui-design-system.md)'s `src/api/` directory extended by one rule: **one directory per canonical slug** [09 §7.1], plus `shell/`, `hub/`, and `adjudication/` for the three surfaces that are not a sub-application.

```
apps/web/
├── .env.example                       # every VITE_* variable, no real value  [09 §8.6]
├── index.html
├── vite.config.ts                     # base baked at build  [50 §6.1]
├── src/
│   ├── main.tsx                       # createBrowserRouter(routes, { basename: import.meta.env.BASE_URL })
│   ├── routes.tsx                     # §3.1's tree, ONE file, no per-feature route registration
│   ├── prefs.ts                       # fathom.theme, fathom.hub.skip  [50 §5.7]
│   ├── api/
│   │   ├── client.ts                  # createClient<paths>({ baseUrl: "/api/v1", credentials: "same-origin" })
│   │   ├── queryClient.ts             # §3.4 defaults
│   │   ├── keys.ts                    # §3.3 — the ONLY place a key literal appears
│   │   ├── problem.ts                 # RFC 9457 -> typed ProblemDetail  [03 §4, 09 §5.2]
│   │   ├── freshness.ts               # §3.4's table, as data, each row citing its derivation
│   │   ├── correlation.ts             # one X-Correlation-Id per user action  [09 §8.1, 50 §12.1]
│   │   ├── csrf.ts                    # double-submit token  [30 §8.1.2] — BLOCKED, §23 UI-OQ-1
│   │   └── outcomes.ts                # FragmentOutcome handling  [30 §3.4], §17.1
│   ├── shell/                         # sheet 00 — §4
│   ├── hub/                           # sheet H — §5
│   ├── features/
│   │   ├── fleet-status/              # sheets 01, 01B — §6, §7, §8
│   │   │   └── demo-positions.ts      # §7's table
│   │   ├── registry/                  # sheet 02 — §9
│   │   ├── telemetry/                 # sheet 03 — §10
│   │   ├── pdm/                       # sheet 04 — §11
│   │   ├── maintenance/               # sheet 05 — §12
│   │   ├── supply/                    # sheet 06 — §13
│   │   ├── pma/                       # sheet 07 — §14
│   │   ├── adjudication/              # sheet 10 — §15
│   │   └── audit/                     # sheet 11 — §16
│   └── display/                       # slug -> display abbreviation  [09 §7.1], §4.2
└── tests/
    ├── routes/                        # one file per route, §19.2
    └── contract/                      # §19.3, against the committed OpenAPI
```

Five rules, each load-bearing:

1. **A feature directory contains hooks, screen components, and screen-local layout — and no reusable component.** A component that another feature would want belongs in `packages/ui` [50 §3.4 rule 1, §11.2 item 13]. The test is mechanical: if two feature directories would each need it, it is a `packages/ui` export or it is a defect.
2. **A feature directory never imports from another feature directory.** Cross-screen navigation is a route path, not an import. `ui-no-cross-feature-import` (§19.1) asserts it. Without this rule §6 and §8 — the same four KPIs at two scopes — silently fuse into one component with a `scope` prop that neither sheet's data model supports (§8.1).
3. **`src/api/keys.ts` is the only file containing a query-key literal** [50 §5.2]. A `useQuery({ queryKey: ["views","fleet"] })` written inline is a review rejection, because invalidation after a mutation (§15.7) is then unprovable.
4. **`src/display/` holds the slug→abbreviation map and the classification-level expansion map, and nothing else.** [09 §7.1]'s display abbreviations (`Registry`, `Telemetry`, `PdM`, `Fleet Status`, `Scheduling`, `Supply`, `PMA`, `Failure Intelligence`, `Design Advisory`) are the only permitted rendering of a slug in operator-facing text; the level expansion (`U` → `UNCLASSIFIED`) lives in `packages/ui` per [50 §7.2] and is imported, not duplicated.
5. **No feature directory contains a `types.ts`.** [09 §2.6] constraint 1 and `ui-no-hand-written-wire-type` [50 §10.2]. Every response shape is `components["schemas"][…]` from the generated document.

---

## 3. Routing and data access, concretely

### 3.1 The route tree

[50 §4.2](50-ui-design-system.md)'s tree is reproduced verbatim and **three segments are added**, each marked and each filed in §22 as an amendment ask against [50 §4.2] rather than taken as a local liberty — because [50 §12.2] makes the tree exact (*"The route tree matches §4.2 exactly"*) and an addition is therefore an edit to that document.

```
/                                                    PersonaHub                        H
│
└── (AppShell layout route)                          shell                             00
    │
    ├── /fleet-status                                FleetOverview                     01
    │   └── /fleet-status/assets/:assetId            VehicleDetail                     01B
    │
    ├── /registry                                    AssetBrowser                      02
    │   └── /registry/assets/:assetId                AssetBrowser (asset selected)     02
    │
    ├── /telemetry/installed-items/:installedItemId  ChannelHealthView                 03
    │
    ├── /pdm                                         FleetRiskTriage                   04
    │   └── /pdm/installed-items/:installedItemId    FleetRiskTriage (deep-dive)       04
    │
    ├── /maintenance                                 WorkPackagePlanner                05
    │   ├── /maintenance/availabilities/:availabilityId          [EXTENDS 50 §4.2]     05
    │   │                                            WorkPackagePlanner (availability)
    │   └── /maintenance/assets/:assetId             [EXTENDS 50 §4.2]                 05
    │                                                WorkPackagePlanner (asset scope)
    │
    ├── /supply                                      StockAndRequisitionView           06
    │   ├── /supply/parts/:niin                      StockAndRequisitionView (NIIN)    06
    │   └── /supply/reservation-sets/:reservationSetId   [EXTENDS 50 §4.2]             06
    │                                                StockAndRequisitionView (set)
    │
    ├── /pma                                         BoundedReviewQueue                07
    │   └── /pma/reviews/:reviewId                   [REPLACES 50 §4.2's               07
    │                                                 /pma/missions/:missionId]
    │                                                BoundedReviewQueue (review)
    │
    ├── /adjudication                                UnifiedAdjudicationQueue          10
    │   └── /adjudication/:proposalId                AdjudicationPanel (nested)        10
    │
    ├── /audit/remediations                          RemediationAndPurgeQueue          11
    │   └── /audit/remediations/:proposalId          RemediationPanel (nested)         11
    │
    └── *                                            NotFound
```

**Why each addition exists, and why none of them is a new sheet:**

| Addition | Why the drawn sheet cannot render without it | Why it is not a new sheet |
|---|---|---|
| `/maintenance/availabilities/:availabilityId` | WF sheet 05's second box is *"Availability: DSRA 26-1 — candidate assignment"*. The disposition list is served by `GET /work-packages/{id}/explanation` [24 §9.1], reached from `GET /availabilities/{id}/work-package` [24 §9.1]. **Neither is reachable without an availability identifier**, and `/maintenance` alone carries none | It renders **the same three boxes** of sheet 05, with the second and third populated instead of empty. `/maintenance` renders sheet 05 with the availability boxes in `EmptyState` and a selector; the child renders it scoped. One screen, two URLs — the identical pattern [50 §4.2] already uses for `/registry` → `/registry/assets/:assetId` |
| `/maintenance/assets/:assetId` | `GET /work-candidates?asset_id=` [24 §9.1] has no unscoped form that is bounded. Sheet 05's first box is a candidate list, and a fleet-wide unscoped candidate list is not a drawn view | Same three boxes, first box scoped |
| `/supply/reservation-sets/:reservationSetId` | WF sheet 06's second box is *"Reservation set — RS-00219"* with a live TTL. It is served by `GET /reservation-sets/{id}` [26 §7.6, added by that document's §7.4] — **a set identifier, never a NIIN**. `/supply/parts/:niin` cannot address it | Same four boxes of sheet 06 |
| `/pma/reviews/:reviewId` **replacing** `/pma/missions/:missionId` | **[50 §4.2]'s segment has no operation behind it.** [23 §3.7]'s review queue is `GET /reviews?asset_id=&status=&reviewer=&changed_since=&limit=&cursor=` — **there is no `mission_id` filter on `/reviews`**, and `mission_id` is a *column* on `pma.mission_review` [23 §2.1], not a query key. Every reviewer-facing operation is keyed on `{id}` = `review_id`: `GET /reviews/{id}`, `GET /reviews/{id}/candidates`, `POST /reviews/{id}/claim`, `POST /reviews/{id}/candidates/{cid}/confirm`, `POST /reviews/{id}/complete` | It is the same sheet 07, reached by the identifier the operations actually take. §22 row 13 |

**Notes carried unchanged from [50 §4.2], restated because a reader of this document must not have to hold two tables in mind:**

- `/telemetry` has no index route and redirects to `/registry`; `/fleet` redirects to `/fleet-status`. Those two are the only redirects.
- `/adjudication` and `/audit/remediations` are the only two slug carve-outs.
- The detail panel at `/adjudication/:proposalId` is a **nested route beside the queue**, not a modal — which is what makes a dual-control second signature reachable by URL [03 §7.2.1].
- Deep links always win; `/` renders the hub and never auto-redirects except on an explicit `fathom.hub.skip` [50 §9.3].
- **No route is authorization-gated** [50 §4.2].

### 3.2 Route-level obligations, per route

Implemented once in `AppShell` (§4.6), never per screen, per [50 §4.4]:

| Obligation | Rule |
|---|---|
| `document.title` | `FATHOM — <sheet title>`. The sheet titles are WF's `<h2>` text verbatim: `Persona Hub`, `App Shell & Navigation`, `Fleet Overview`, `Vehicle Detail`, `Asset Browser`, `Channel & Health View`, `Fleet-Risk Triage`, `Work Package Planner`, `Stock & Requisition View`, `Bounded Review Queue`, `Unified Adjudication Queue`, `Remediation & Purge Queue` |
| Focus | Moves to the `TitleBlock` `<h2>` on every route change |
| Announcement | One polite live region announces `<sheet title> loaded` |
| Scroll | Router default restoration; `scroll-margin` compensates for the classification banner [50 §8.2] |
| Query state | Filter and sort state lives in the URL, **parameter names verbatim from the operation** [50 §4.4]. §15.3 is the case where this matters most: 22 names, unrenamed |
| `X-Correlation-Id` | **One per user action**, minted client-side, sent on every request that action produces, including retries [09 §8.1; 50 §12.1] |

### 3.3 The query-key factory

[50 §5.3](50-ui-design-system.md)'s eight keys, plus the four this document's screens require. `[EXTENDS 50 §5.3]`, §22 row 20.

```ts
// apps/web/src/api/keys.ts — the ONLY file containing a key literal
export const keys = {
  session:            ()                       => ["session"] as const,

  views: {
    fleet:            ()                       => ["views","fleet"] as const,
    asset:            (id: string)             => ["views","asset", id] as const,
    installedItem:    (id: string)             => ["views","installed-item", id] as const,
    explanation:      (id: string)             => ["views","explanation", id] as const,
    redesignCase:     (id: string)             => ["views","redesign-case", id] as const,   // [EXTENDS]
  },

  proposals: {
    list:             (p: NormalizedQueueParams) => ["proposals","list", p] as const,
    summary:          ()                       => ["proposals","summary"] as const,
    detail:           (id: string)             => ["proposals","detail", id] as const,
  },

  // Pass-through. `slug` is a canonical slug [09 §7.1]; `path` is the upstream path
  // template; `params` is the normalized query object. One shape, so invalidation and
  // the §19.3 contract test are mechanical.
  passthrough:        (slug: Slug, path: string, params?: object) =>
                        ["passthrough", slug, path, params ?? null] as const,

  // Bitemporally pinned reads. SEPARATE from `passthrough` because their staleTime is
  // Infinity by construction (§3.4) and mixing them into one key family would make that
  // property invisible at the call site.
  pinned:             (slug: Slug, path: string, params: BitemporalParams) =>
                        ["pinned", slug, path, params] as const,

  refdata:            (kind: string, version: string) => ["refdata", kind, version] as const,
} as const;
```

**`["views","redesign-case", id]` is new and is required by a screen this document owns**, not by [52](52-practitioner-apps.md): [30 §3.2](30-gateway.md)'s `redesign_case_detail` view was added by amendment *"[to close] `42-redesign-case-builder.md` §18 item 13: An adjudicator opening a `redesign_case` from the queue has no composed drill-down."* That adjudicator is on **WF sheet 10**, in `apps/web`. [50 §5.3]'s shape table predates the amendment and lists four composed views; there are five. §15.5 wires it.

**`["pinned", …]` is the second addition and it encodes a correctness property in the key family.** A read that supplies both `as_of` and `as_known_at` explicitly is **immutable by construction**: [20 §6.3](20-registry.md) makes `as_of` *"VALID TIME … 'What was installed at this instant'"* and `as_known_at` *"RECORD TIME … 'As Registry believed it at this instant'"*, and [21 §5.1](21-telemetry.md) makes both **required with no default** on `GET /features`, with `latest` as an explicit literal. Two explicit instants name one answer that cannot change. Polling it is waste; `staleTime: Infinity` is not an optimization but a statement of fact. Keeping those reads in a distinct key family is what makes §3.4's assignment auditable rather than a per-call-site judgement.

### 3.4 Freshness — every query mapped onto [50 §5.4]'s existing settings

**This document introduces no new interval.** [50 §5.4](50-ui-design-system.md) derived three distinct settings from real figures; every query below is assigned one of them, and the assignment carries its derivation.

| Setting | `staleTime` | `refetchInterval` | [50 §5.4]'s derivation |
|---|---|---|---|
| **A — view cadence** | 30 s | 60 s | Scoring is *"[d]aily for tiers 0–1, per-mission-completion for tiers 2–3"* [06 §7] with hysteresis dwell [27 §6.2]; 60 s over-samples the fastest real change by orders of magnitude and exists for perceived liveness |
| **B — queue cadence** | 15 s | 30 s | *"[a]gent proposals per day \| < 20"* [06 §7], and `stalenessBoundSeconds: 300` [30 §4.7] means **no client can observe fresher data than 300 s of projection lag permits**; 30 s is chosen because the queue is the one surface where a human is actively waiting |
| **C — immutable** | `Infinity` | none | A new identity is a new id; the old answer does not change |

| Query | Setting | Why this setting |
|---|---|---|
| `session()` | **C**, invalidated on any `401`/`404` | The identity block changes only at login and logout. `refetchOnWindowFocus: true` [50 §5.4] already re-reads it when an operator returns to the tab, which is the case that matters on a shared bridge workstation. **No interval is invented for it**, and a `404` from `GET /api/v1/gateway/session` [30 §8.1.2] is the session's end |
| `views.fleet()` | **A** | [50 §5.4] assigns it directly |
| `views.asset(id)` | **A** | [50 §5.4] |
| `views.installedItem(id)` | **A** | [50 §5.4] |
| `views.explanation(id)` | **C** | [50 §5.4]: *"An explanation decomposes one `prediction_id`. A new prediction is a new id"* |
| `views.redesignCase(id)` | **C** | Same argument, same 4000 ms budget class [30 §3.2]. A case's composed dossier changes on a new case revision, which is a new fetch triggered by the queue's invalidation (§15.7), not by a timer |
| `proposals.list(p)` | **B** | [50 §5.4] |
| `proposals.summary()` | **A** | [50 §5.4]: *"It drives the nav badge only … A badge is not worth the queue's cadence"* |
| `proposals.detail(id)` | **C** | [50 §5.4]: refetching under the operator *"would silently replace the `ETag` they are about to submit"* |
| `pinned(…)` — every bitemporal read (§9, §10) | **C** | §3.3's immutability argument. `ui-pinned-queries-never-poll` (§19.1) asserts no `pinned` key carries a `refetchInterval` |
| `passthrough("fleet-status", "/risk-flags", …)` | **A** | Same inputs as the composed view it accompanies; a flag transition is dwell-gated [27 §6.2] |
| `passthrough("fleet-status", "/readiness", …)` | **A** | Same |
| `passthrough("audit", "/effectiveness/warning-lead-time-coverage", …)` | **A** | It sits in the same KPI row as the readiness figure (§6.3) and polling it on a different cadence would make two tiles in one row disagree about their own currency. The response carries `computed_at` [32 §10.7], so its real staleness is displayed regardless of the poll |
| `passthrough("registry", …)` — unpinned reads (§9) | **A** | A configuration change is an epoch bump [20 §4.0.2]; `epoch_is_current: false` must appear promptly (§9.5) |
| `passthrough("pdm", "/predictions", …)` | **A** | Predictions are written by a scoring run [22 §10]; the cadence is [06 §7]'s |
| `passthrough("pdm", "/attribution-policy")` | **C** | A singleton policy document [22 §10]. §11.4 reads the stability floor from it once |
| `passthrough("maintenance", …)` (§12) | **A** | Candidate generation is event-driven off the same prediction cadence [24 §3.2.1] |
| `passthrough("supply", "/reservation-sets/{id}")` | **B** | **The one place a real figure argues for the faster setting rather than the slower.** The expiry reaper runs at a 15 s interval [26 §7.4], so a confirmed set can transition to `expired` within 15 s of `expires_at`. Setting **A** would leave a released set looking confirmed for up to 60 s, and the operator would be looking at a reservation they no longer hold. **The `TtlCountdown` is not this poll** [50 §3.2] — it is a monotonic delta from a server-supplied `expires_at` captured once, and it is what gives the operator a second-resolution number without a second-resolution request |
| `passthrough("supply", …)` — all other reads | **A** | — |
| `passthrough("pma", "/reviews", …)` | **A** | — |
| `pinned("pma", "/reviews/{id}/candidates", …)` | **C** | The bounded set is fixed at review open: `candidate_cap`, `taxonomy_version_pin` *"set at creation, never re-pinned"*, and `presentation_ordinal` `1..cap` [23 §2.1]. Refetching it could reorder the operator's queue mid-review |
| `passthrough("audit", "/purges/{id}", …)` | **B** | A purge in `executing`/`verifying` is the one surface where a human is actively waiting on a multi-store protocol [32 §6.2], and §16.6 renders per-store receipts arriving one at a time |
| `refdata(kind, version)` | **C** | [50 §5.4]: *"[c]ached by version, so a cache entry is immutable and invalidation is a version change, not an expiry"* |

**Global defaults are [50 §5.4]'s, unchanged and not restated except for the two that bind every screen below:**

- **`429` pauses that query's interval for `Retry-After` seconds and renders `RateLimitNotice`** [30 §6.5]. `Retry-After` is *"[c]eiling, never zero"* [30 §6.3] and is the **only** rate-limit header the gateway sets — [30 §6.5] declares no `X-RateLimit-Limit`, `-Remaining`, or `-Reset`, so the console must not read one and must not render a quota gauge. `[ESTABLISHED HERE]`
- **Every interval, timeout, backoff, and countdown is measured with `performance.now()`** [09 §9.2 item 7, D29; 50 §5.4]. This binds `TtlCountdown` (§13.4) and the purge elapsed-duration display (§16.6), which are the two screens where a wall clock is the obvious implementation.

### 3.5 The six-outcome contract, as code every screen calls

[30 §3.4](30-gateway.md)'s outcomes are `ok`, `empty`, `timeout`, `unavailable`, `forbidden`, `classification_fault`. **Every screen backed by a composed view routes every fragment through one function**, so that no screen can handle five of six.

```ts
// apps/web/src/api/outcomes.ts
type FragmentView<T> =
  | { kind: "ok";        data: T }
  | { kind: "empty" }                                   // -> EmptyState        [50 §5.5]
  | { kind: "unknown";   outcome: "timeout" | "unavailable" | "forbidden";
                         upstream?: string; retryable?: boolean };  // -> DegradedFragmentNotice

export function fragment<K extends string, T>(
  envelope: ComposedView, name: K
): FragmentView<T>;
```

Four rules, all from [30 §3.4] and [50 §5.3]:

1. **`data.<name>` is read only when `fragments.<name>.outcome === "ok"`.** `outcomes.ts` is the only place `envelope.data` is indexed; a screen that reads `data.readiness_rollup` directly fails `ui-no-direct-fragment-read` (§19.1).
2. **`empty` and `unknown` are different renderings, never merged** — [30 §3.4]: *"`EMPTY` and `UNAVAILABLE` are different facts and are presented as different facts."*
3. **`degraded: true` renders `DegradedFragmentNotice` naming the fragment and its outcome** [50 §5.5], at the top of the affected `Box`, never as a page-level banner — a page banner cannot say *which* box is wrong, and on sheet 01 five fragments feed six boxes.
4. **A whole-view `503 required-fragment-unavailable` has no partial body** [30 §3.4] and renders `ProblemDetail` for the entire sheet; a `502 classification-fault` renders a **distinct, non-retryable** `ProblemDetail` [30 §7.2, 50 §7.2 rule 6]. `ui-classification-fault-is-not-degraded` [50 §10.2] already asserts the second.

**One thing [30 §3.2](30-gateway.md) does not give, and it affects every composed view on every screen below:** `Fragment.operation_id` exists as a field, described as *"the upstream `operationId` (09 §7.3); resolved against its committed spec"* — but **no fragment's `operation_id` value is stated anywhere in [30](30-gateway.md)**. The console therefore cannot know which upstream operation produced a fragment, which means it cannot know a fragment's response *shape* from [30](30-gateway.md) alone; §6–§11 below derive each shape from the upstream document's own schema and state the derivation. This is §22 row 21 and it is the single largest wiring gap in the corpus.

---

## 4. Sheet 00 — the App Shell

### 4.1 What the wireframe draws, element by element

`WF sheet 00` contains exactly three regions and nothing else. Transcribed:

| WF element | Content as drawn | Component [50 §3.5] |
|---|---|---|
| `.classbar` (in the masthead) | `● Unclassified — demonstration data — internal working draft` | `ClassificationBanner` |
| `.topbar .word` | `FATHOM` | `TopBar` |
| `.topbar .search` | `search asset, NIIN, hull…` | `IdentifierLookup` — **and it is not a search box**, §4.4 |
| `.topbar .id` | `CDR J. RIVERA · Ship's Force · [chip neutral] delegated` | `IdentityBlock` — **and `delegated` is wrong**, §4.3 |
| `.nav-shell .side` | `Fleet Status` (active) · group `Asset & Condition` → `Registry`, `Telemetry` · group `Maintenance` → `Predictions`, `Scheduling`, `Supply` · group `Analysis` → `Post-Mission Review`, `Failure Intelligence`, `Design Advisory` · group `Cross-cutting` → `Adjudication Queue` + `[chip warning] 7` | `SideNav`, `NavGroup`, `NavItem`, `NavBadge` |
| `.nav-shell .main` | `→ selected sub-application's landing sheet renders here` | React Router `<Outlet/>` inside `<main>` |
| `.skip` | `Skip to first wireframe` | `SkipLink`, retargeted to `<main>` [50 §3.2] |
| *(absent)* | — | `ClassificationFooter` — **required by [03 §7.3] and drawn on no sheet** [50 §13 row 11] |

### 4.2 The side nav, and the two items that are not routes

Eleven `NavItem`s in four groups. The mapping is exact, and **two items leave the application**:

| WF nav item | Target | Kind |
|---|---|---|
| `Fleet Status` | `/fleet-status` | Route |
| `Registry` | `/registry` | Route |
| `Telemetry` | `/registry` — **redirect target** | Route. `/telemetry` has no index [50 §4.2]; the item's `href` is `/registry` directly rather than a link that bounces, so the address bar never shows a URL the operator did not ask for. `[ESTABLISHED HERE]` |
| `Predictions` | `/pdm` | Route |
| `Scheduling` | `/maintenance` | Route |
| `Supply` | `/supply` | Route |
| `Post-Mission Review` | `/pma` | Route |
| **`Failure Intelligence`** | `${VITE_PRACTITIONER_BASE_URL}` + the Failure Intelligence surface | **`ExternalLaunch`** — §18.2 |
| **`Design Advisory`** | `${VITE_PRACTITIONER_BASE_URL}` + the Design Advisory surface | **`ExternalLaunch`** — §18.2 |
| `Adjudication Queue` + badge | `/adjudication` | Route |
| *(absent from WF)* | `/audit/remediations` | **Route with no nav item.** §4.5 |

**[50 §4.3](50-ui-design-system.md) says `apps/web` owns *"exactly one thing"* on sheets 08 and 09's behalf — the two Persona Hub cards.** That is one element short: **WF sheet 00's side nav lists `Failure Intelligence` and `Design Advisory` as nav items**, and they have no `apps/web` route. §22 row 22 files the correction; §18.2 specifies the treatment, which is the same `ExternalLaunch` [50 §9.5] already specified for the cards, with two consequences the nav position adds:

1. **An `ExternalLaunch` inside `<nav>` must not carry `aria-current`**, ever. It is not a page in this application, and `aria-current="page"` on it would announce the operator as being somewhere they are not. `a11y-external-nav-no-current` (§19.1).
2. **The two items are visually distinguished as leaving the console**, using `--ink-soft` text and the `--dash-guide` border [50 §2.5] — the existing "this is not solid chrome" motif — plus the accessible name [50 §9.5] mandates. **No icon** [50 §3.1]. `[ESTABLISHED HERE]`

**`NavItem` labels are [09 §7.1]'s display abbreviations except for three**, and the three exceptions are WF's own words: `Predictions` (abbreviation: `PdM`), `Post-Mission Review` (abbreviation: `PMA`), and `Scheduling` (abbreviation matches). WF's words win — they are operator-facing labels, not identifiers, and [50 §4.2]'s rule that *"a nav label can be changed without changing a URL"* is exactly this case. The URL segments remain the slugs verbatim.

**`aria-current="page"` marks the active item** [50 §3.2], derived from the router's match, and it is what `.item.active` means. The nav is `<nav aria-label="Sub-applications">` + `<ul>`; `NavGroup` renders `.group-label` at `--fs-100` per [50 §2.3]'s floor rule, **not** WF's 9.5 px [50 §13 row 6].

### 4.3 `IdentityBlock` — real identity, and the chip the wireframe gets wrong

**Source:** `GET /api/v1/gateway/session` [30 §8.1.2], returning *"the session's identity block (`fathom.identity`, byte-identical to §3.2's token shape) and its six `authority_classes`"*. [31 §3.1](31-auth.md) fixes that block's members exactly:

| Field [31 §3.1] | Rendered as |
|---|---|
| `display_name` | The leading text. WF draws `CDR J. RIVERA` |
| `billet` | The second segment. WF draws `Ship's Force` |
| `unit_uic` | In the block's title attribute and in the accessible name, not in the visible line — WF has room for two segments and `billet` is the operationally meaningful one. `[ESTABLISHED HERE]` |
| `unit_path` | Not rendered. It is a hierarchy path (`fleet/tycom-01/isic-04/N12345`) and has no drawn slot |
| `authority_classes[]` | **One `StatusChip tone="neutral"` per held class**, in [31 §2.4]'s enum order, label = the enum value verbatim. Zero classes renders **no chips and no text** — §5.3 case 3 makes `[]` a working state, and a "no authority" chip would make it read as an error |
| `qualifications[]` | Not rendered here. §14.5 renders it in the one place it is operationally meaningful |
| `clearance` | **Never rendered.** It is not a display attribute, and rendering a clearance level next to a classification banner invites the reading that the banner is scoped to the viewer. `[ESTABLISHED HERE]`, and it is why `ClassificationBanner` is data-driven from `X-Classification` [50 §7.2 rule 2] and not from the session |
| `subject_id` | Not rendered. Used only as the `claimed=me` comparison basis (§15.4) |
| `edipi` | Not rendered. `null` until the CAC/PIV path is enabled [31 §3.1] |

**WF sheet 00's `[chip neutral] delegated` is a defect.** `delegated` is not a human property: [31 §3.2](31-auth.md) makes `delegated` a **token shape for an agent**, and [30 §5.3](30-gateway.md) sets `fathom.agent.authority = "delegated"` on a delegation minted for an agent turn. A human interactive session has no such value, and `fathom.identity` [31 §3.1] contains no field it could come from. Rendering it would tell an operator their own session is an agent delegation. **The chips are `authority_classes[]`**, and §22 row 23 files the wireframe edit.

**Two additional controls live in the `IdentityBlock`**, both required by documents rather than drawn:

| Control | Basis |
|---|---|
| **Sign out** | `POST /api/v1/gateway/session/logout` [30 §8.1.2]. On success: clear `fathom.hub.skip` and `fathom.theme` [50 §12.1's purge disposition], clear the entire query cache, and navigate to `/`. **No client-side `end_session_endpoint` redirect** — [30 §8.1.2] is explicit that RP-initiated logout is triggered server-side *"because the browser holds no `id_token` to present to one."* This closes [50 UI-OQ-2] |
| **Return to Persona Hub** | [50 §9.3]: *"The hub is also reachable on demand from the shell, at `/`, from a persistent control in the `TopBar`"* — the second half of WF sheet H's *"or on demand"* |

### 4.4 `IdentifierLookup` — and the operation it needs does not exist

[50 §13 row 9](50-ui-design-system.md) already established that WF's `search asset, NIIN, hull…` promises a capability the platform declines: [30 OQ-7] says a free-text proposal search is *"[n]ot offered. Structured filters only"* and [03 §4] forbids *"[a]ny general-purpose query language on the public surface."* [50 §3.2] therefore specified `IdentifierLookup`, a typed identifier lookup over *"the named filters that do exist (`GET /assets`, `GET /parts?niin=`)."*

**One of those two named filters does not exist.** Verified against [20 §6.1](20-registry.md)'s 33-row operation table:

| Wanted | Reality |
|---|---|
| A NIIN lookup | **Exists.** `GET /parts/{niin}` [20 §6.1 row 9], and `GET /parts?apl=&equipment_family=&changed_since=` [20 §6.1 row 10] |
| An installed-item lookup | **Exists.** `GET /installed-items?asset_id=&position_id=&niin=&provisional=&changed_since=&cursor=` [20 §6.1 row 16], and `GET /installed-items/{installed_item_id}` [row 17] |
| A hull lookup | **`[GAP]`.** `GET /assets` [20 §6.1 row 1] and `GET /assets/{asset_id}` [row 2] declare **no query parameter anywhere in [20](20-registry.md)** — not `hull_or_tail=`, not `uic=`, not `domain=`, not `class_id=`, not even `changed_since=`, unlike rows 10, 13, 16, and 19–22 which spell theirs out. There is no operation that answers *"which asset is hull DDG 113"* |

**Consequence, and it is the honest one:** `IdentifierLookup` ships with **two working modes and one declared-absent mode**.

| Mode | Trigger | Operation | Behaviour |
|---|---|---|---|
| NIIN | Input matches `^([0-9]{9}\|[A-Z]{2}[A-Z0-9]{7})$` | `GET /api/v1/registry/parts/{niin}` | Navigate to `/supply/parts/{niin}`. **[AMENDMENT]** Previously `^[0-9A-Z]{9}$` per [26 §13 row 1]'s *proposed* form — broader than what `10-shared-packages.md` §4.1 actually adopted, which constrains letters to positions 1–2 rather than accepting one anywhere in the 9 characters. The wider pattern let the console accept input the API's canonical `Niin` type would `422` on |
| Installed item | Input is a UUID | `GET /api/v1/registry/installed-items/{installed_item_id}` | Navigate to `/telemetry/installed-items/{id}` |
| **Hull / asset** | Anything else | **None** | The listbox renders one non-selectable `EmptyState` option: *"Hull lookup is unavailable — no operation accepts a hull number. Open the Asset Browser to select an asset."* with a link to `/registry`. **Never a spinner, never a silent empty list.** `[ESTABLISHED HERE]`, §22 row 4 |

**The placeholder text changes**, because [50 §13 row 9] is right that *"[a] placeholder promising search the platform declines to offer is the kind of expectation that is expensive to withdraw"*: `NIIN or installed-item ID`. And [50 §8.3] forbids placeholder-as-label, so the native `<label>` reads `Identifier lookup` and the placeholder is a format hint only.

**Twelve assets** [06 §7] is the whole fleet. `/registry`'s asset list (§9.2) is therefore a complete, unpaginated list, which is why the fallback above is a real answer and not a deflection: an operator who cannot type a hull number can *see all twelve*.

### 4.5 `NavBadge`, and the queue with no nav item

**The badge.** WF draws `Adjudication Queue [chip warning] 7`. Source: `GET /api/v1/gateway/proposals/summary` [30 §4.5], setting **A** (§3.4). [30 §4.5] describes it as *"[c]ounts grouped by `status × authority_class × blast_radius × target_sub_app`, plus a total for the deployment's level"* — **and states no field names**, so the badge's number has no named source. `[GAP]`, §22 row 24. The interim, `[ESTABLISHED HERE]`: the badge renders the count of `status: proposed` from whatever grouping shape the generated type exposes, and **renders nothing at all** — no chip, no zero — when the query has not resolved or has failed. A badge is the one place where absence is legitimately silent, because a *missing* badge claims nothing while a `0` badge claims the queue is empty [30 §3.4].

The badge tone is `warning` as drawn. It is **not** conditional on the count: a tone that changes with depth would be a client-side threshold the corpus does not define, and [06 §6]'s admission-control threshold (*"3× monthly throughput"*) is about **PMA review candidates, not `Proposal`s** — [30 §4.8] warns explicitly that conflating them *"would report a number that means nothing."*

**The queue with no nav item.** WF sheet 00's nav has no `Remediation & Purge Queue`, but WF sheet 11 exists and [50 §4.2] routes it at `/audit/remediations`. Two options were considered and one is adopted:

- **Adopted:** a twelfth `NavItem`, `Remediation Queue`, in the `Cross-cutting` group, immediately after `Adjudication Queue`, **with no badge**. `[ESTABLISHED HERE]`, §22 row 25 files the wireframe edit. It carries no badge because `GET /proposals/summary`'s grouping is by `authority_class`, and filtering that grouping to `security_officer` client-side to produce a second badge would be exactly the presentation-versus-control confusion [50 §9.4] warns about — and worse, [30 §4.5]'s `authority_class` filter **does not accept `security_officer`** (§15.3, §22 row 15), so the number could not be obtained even by asking.
- **Rejected:** reaching sheet 11 only from the hub's `SC` card. It would make a routed, deep-linkable screen invisible to an operator who has already landed, and [50 §4.2]'s *"no hidden nav item that implies a permission"* rule cuts both ways — hiding a nav item because most operators lack the authority is the same defect as showing one because they have it.

### 4.6 Shell composition, and what is outside every route

```
<ClassificationBanner …/>            <!-- outside <main>, persistent, undismissable  [50 §7.2 rule 4] -->
<SkipLink target="main"/>
<header>
  <h1>FATHOM</h1>                    <!-- the ONE <h1>  [50 §8.3] -->
  <TopBar>
    <IdentifierLookup/>              <!-- §4.4 -->
    <IdentityBlock/>                 <!-- §4.3, incl. sign-out and hub return -->
  </TopBar>
</header>
<div class="nav-shell">
  <SideNav aria-label="Sub-applications">…</SideNav>   <!-- §4.2 -->
  <main id="main">
    <Outlet/>                        <!-- every sheet 01–11 -->
  </main>
</div>
<footer>
  <ClassificationFooter …/>          <!-- [03 §7.3]; NOT drawn on any sheet  [50 §13 row 11] -->
</footer>
<div aria-live="polite" …/>          <!-- route announcements (§3.2) and mutation results (§15.7) -->
```

Four rules:

1. **`ClassificationBanner` and `ClassificationFooter` are outside `<Outlet/>`**, so no route can fail to render them and `ui-classification-footer-present` [50 §10.2] passes structurally rather than by eleven separate assertions.
2. **Both are fed by the classification label of the *most recently completed* request on the active route.** `[ESTABLISHED HERE]` — a composed view's `X-Classification` is *"the union of the contributing fragments' labels"* with `inherited_from` accumulated [30 §7.3], so the banner on sheet 01 renders a **derived** label and must say so [50 §7.2]. Where a route makes several requests (§6 makes three), the label is the union the *composed view* returned, not a client-computed union — [30 §7.3] makes `ClassificationLabel.union` the shared implementation and [50 §11.3 item 20] forbids the browser deriving a cross-domain value. A route whose several requests return *differing* labels renders the banner's fault state and a `ProblemDetail`, because a client that picked one would be choosing a marking. §22 row 26 asks [30](30-gateway.md) whether a multi-request route is expected to see one label.
3. **A missing `X-Classification` is a fault, never a default to `U`** [50 §7.2 rule 5, §11.4 item 30].
4. **The shell renders `RateLimitNotice`** [50 §3.5] when any query is paused on a `429` `Retry-After` (§3.4), because a rate limit is a session-wide condition and a per-box notice would appear six times on sheet 01.

### 4.7 Shell states

| Condition | Rendering |
|---|---|
| `session()` loading | Nav and banner render; `IdentityBlock` renders `LoadingSkeleton` at final dimensions. **Routes render.** The shell never blocks a route on identity, because no route is authorization-gated [50 §4.2] and a deep link must work before identity resolves |
| `session()` → `404` | No session [30 §8.1.2]. Render the login affordance and nothing else; clear the cache. **This is the only full-shell interception in the application** |
| `session()` → `401 urn:fathom:problem:gateway:unauthenticated` | Same as `404`. [30 §5.1] sets `WWW-Authenticate: Bearer`, which the console does not act on — it holds no token [50 §6.3] |
| `session()` → other error | `IdentityBlock` renders `ProblemDetail` inline, compactly. Nav and routes render: an operator who cannot see their own name can still read a fleet view |
| `authority_classes: []` | No chips, no messaging. **Not an error** [50 §9.3 case 3] |
| Any query paused on `429` | `RateLimitNotice` in the shell, stating the remaining seconds from `Retry-After` [30 §6.5] |

---

## 5. Sheet H — the Persona Hub

### 5.1 What the wireframe draws

`WF sheet H` contains a `sheet-note`, a `.hub-grid` of **eight** `.p-card`s, a `.hub-cross` bar with **two** `.btn`s, and a footnote. Each card has a two-letter `.p-glyph`, an `<h3>`, a `.p-func` line, one `.btn.primary.p-primary`, and a `.p-also` line. Two cards carry `.is-new` (`VR`, `SC`) and are *"outlined rather than filled"*.

| Glyph | `<h3>` | `.p-func` | Primary button | `.p-also` |
|---|---|---|---|---|
| `EC` | Executive / Commander | TYCOM Readiness Officer — fleet-wide rollup and risk posture | `Open Fleet Overview` | Vehicle Detail · Adjudication Queue |
| `VR` | Vehicle Readiness Officer | Owns one hull's readiness and open risk in depth | `Open Vehicle Detail` | Fleet Overview · Asset Browser |
| `SF` | Ship's Force Maintainer | Confirms anomaly tags; deckplate condition monitoring | `Open Bounded Review Queue` | Channel & Health · Risk Triage · Asset Browser |
| `AP` | RMC / Availability Planner | Assembles work packages from predictions and parts | `Open Work Package Planner` | Risk Triage · Stock & Requisition |
| `SO` | Supply Officer | Requisitions, expedites, stock and allowance position | `Open Stock & Requisition View` | Work Package Planner |
| `RE` | Reliability Engineer | Adjudicates causal failure-mode hypotheses | `Open Hypothesis Adjudication` | Redesign Case Builder |
| `DE` | PEO / Design Engineer | Reviews redesign business cases and dependency impact | `Open Redesign Case Builder` | Hypothesis Adjudication · Adjudication Queue |
| `SC` | Security Officer (ISSM / ISSO) | Dual-control crypto-shred purge and rewrap adjudication | `Open Remediation & Purge Queue` | *"no secondary view — scope is deliberately narrow"* |

`.hub-cross`: label *"Cross-cutting — reachable from every role above, owned by none of them"*, then `Asset Browser` and `Unified Adjudication Queue`.

Components [50 §3.5]: `PersonaHub`, `PersonaCard`, `PersonaGlyph`, `CrossCuttingBar`, `Button`, `ExternalLaunch`. **The card is not clickable** [50 §11.2 item 15]; it is a labelled region containing one primary `Button` and a list of secondary links.

### 5.2 The role-to-route mapping, wired to real `authority_classes`

**Source:** `GET /api/v1/gateway/session` [30 §8.1.2] → `authority_classes[]`, populated from realm roles *"filtered to the six values of §2.4"* [31 §3.1 rule 3]. Setting **C** (§3.4). [50 §9.1](50-ui-design-system.md) fixed the mapping; this table is that mapping with the concrete route, target, and the queue pre-filter §15.3 applies.

| Card | `authority_classes` value [31 §2.4] | Primary target | Kind | Queue pre-filter set on `.p-also` → Adjudication Queue [50 §9.4] |
|---|---|---|---|---|
| `EC` | `fleet_authority` | `/fleet-status` | Route | `?authority_class=fleet_authority&status=proposed&sort=expiry` |
| `VR` | **none** | `/fleet-status/assets/:assetId` | Route — **and it needs an id it does not have**, §5.4 | — |
| `SF` | `maintainer` | `/pma` | Route | `?authority_class=maintainer&status=proposed&sort=expiry` |
| `AP` | `planner` | `/maintenance` | Route | `?authority_class=planner&status=proposed&sort=expiry` |
| `SO` | `supply_officer` | `/supply` | Route | `?authority_class=supply_officer&status=proposed&sort=expiry` |
| `RE` | **none** | Hypothesis Adjudication | **`ExternalLaunch`** — §18 | — |
| `DE` | `design_authority` | Redesign Case Builder | **`ExternalLaunch`** — §18 | `?authority_class=design_authority&status=proposed&sort=expiry` |
| `SC` | `security_officer` | `/audit/remediations` | Route | **`?kind=purge&kind=rewrap&status=proposed&sort=expiry` — not `authority_class`**, §5.5 |

**Six roles, six cards; `VR` and `RE` are self-selected personas with no realm role** [50 §9.1]. **Neither gets a new one** — [31 §13 item 12] forbids adding an `AuthorityClass` *"beyond document 03 §7.2.1's enumerated set (six, as of amendment 03-1),"* and [31 §2.4]'s docstring is explicit that *"[a] seventh member is a change to document 03, not to this file."* WF sheet H's footnote miscounts and is [50 §13 row 17]'s correction, carried forward unchanged as §22 row 27.

### 5.3 The five cases, implemented

[50 §9.3](50-ui-design-system.md)'s algorithm, with the concrete behaviour:

| Case | `authority_classes` | Behaviour |
|---|---|---|
| **1** — one role, target in `apps/web` | e.g. `["planner"]` | All eight cards render. The `AP` card is marked **"your authority"** — a `StatusChip tone="accent"` [50 §2.2] since it marks a *primary affordance*, not a status — and is first in **DOM and visual order**. Initial focus is on its primary `Button`. **No redirect** unless `fathom.hub.skip` is set |
| **2** — one role, target in `apps/practitioner` | `["design_authority"]` | Same, and the marked card's button is an `ExternalLaunch`. **Never auto-redirected, in any circumstance** [50 §9.3] |
| **3** — no role in the six | `[]` | All eight cards, **none marked**, plus the cross-cutting bar. **Not an error state, and no banner suggests the operator is unauthorized** [50 §9.3 case 3]. Initial focus on the hub `<h2>` |
| **4** — more than one role | `["maintainer","planner"]` | Every held role's card marked, in [31 §2.4]'s enum order. **No default and no ranking** — [31 §2.4]'s *"No implicit hierarchy"* rule means there is no basis to prefer one. Focus on the `<h2>` |
| **5** — a role with no card | impossible today | An unmapped-authority notice **naming the value**, rather than silent omission. `ui-every-role-has-a-card` [50 §10.2] fails the build the moment [03 §7.2.1]'s enum and the card set disagree |

**Card ordering is a stable sort, and this matters for case 4.** The base order is WF's DOM order (`EC`, `VR`, `SF`, `AP`, `SO`, `RE`, `DE`, `SC`); marked cards move ahead of unmarked ones preserving relative order. A comparator that reorders unmarked cards would make the hub's layout vary between two operators who hold no roles at all, which is the case-3 majority.

**`fathom.hub.skip`** [50 §5.7] holds a **route string, not a card id**, and the hub renders a *"skip this next time"* checkbox that writes it on an explicit human action. Two guards, `[ESTABLISHED HERE]`:

1. **A stored value that is not one of §3.1's route paths is discarded**, not navigated to. `localStorage` is operator-writable and a stale value from a previous build must not become a redirect to `*`.
2. **The skip never applies to an `ExternalLaunch` target.** Setting it on the `RE` or `DE` card is refused with a stated reason, because *"an automatic cross-host navigation into an iframed app is not something a console does to a user"* [50 §9.3 case 2]. `ui-hub-skip-never-external` (§19.1).

### 5.4 The `VR` card needs an asset id, and the hub does not have one

WF sheet H's `VR` card links to sheet 01B, whose route is `/fleet-status/assets/:assetId` [50 §4.2] — but **the hub makes exactly one request, `GET /api/v1/gateway/session`, and that response carries no asset**. [31 §3.1] gives `unit_uic` and `unit_path`, which are organizational, and [20 §6.1] has no operation mapping a UIC to an asset (§4.4's same gap: `GET /assets` declares no parameter, and `uic` is an `assets` column [20 §4.3] with no filter).

**Resolution, `[ESTABLISHED HERE]`, and it invents nothing:** the `VR` card's primary button targets **`/fleet-status`**, labelled `Open Fleet Overview — select your hull`, and the card's `.p-func` line is unchanged. Sheet 01's map and risk-flag table are the hull selector [WF sheet 01: *"Click any marker → sheet 01B, scoped to that hull"*], so one extra click reaches the drawn destination. Three alternatives were rejected:

- **A `?vr=1` hint that auto-selects the first asset** — it would present an arbitrary hull as "yours."
- **Persisting a chosen hull in `localStorage`** — a per-browser guess about an organizational fact, and the `VR` persona is itself already self-selected [50 §9.1]; two layers of guessing is one too many.
- **Asking for a `unit_uic` → `asset_id` operation** — filed as §22 row 4's second clause rather than assumed, since it is the same missing `GET /assets` filter set.

### 5.5 The `SC` card's queue pre-filter — `authority_class`, like every other role

Every other role's `.p-also` link to the Adjudication Queue pre-sets `authority_class` — [30 OQ-9] (as corrected) makes exactly that *"the roles from the session identity §8.1.2 returns"* filtering the sanctioned mechanism, and [50 §9.4] confirms it is presentation.

**[AMENDMENT — resolved.]** This section previously stated `security_officer` was not an accepted value of that parameter, because [30 §4.5](30-gateway.md) declared `authority_class` over only five values while [03 §7.2.1] has six, and [30 §8.1.2] in the same document contradicted its own §4.5. `30-gateway.md` §4.5 now declares all six, explicitly closing this row. The `SC` card pre-sets `?authority_class=security_officer` exactly as every other role's card does — no special-cased filter is needed.

**A narrower alternative remains available, and is worth keeping for one case `authority_class` cannot express.** The `kind` parameter (`ProposalKind`, [03 §7.2] extended with `purge | rewrap`) supports `?kind=purge&kind=rewrap`, which selects exactly the security officer's proposal work by a different axis. `authority_class=security_officer` is the right default pre-filter because it is what every other role's card does and it also surfaces `awaiting_second_signature` counter-signature work that `kind` alone would still show correctly — but `?kind=purge&kind=rewrap` remains a useful narrower query for a screen that wants to filter by proposal kind rather than by adjudicator role.

### 5.6 Hub states

| Condition | Rendering |
|---|---|
| `session()` loading | **All eight cards render, unmarked, and are usable.** No skeleton over the grid: the hub's whole content is static and only the *marking* depends on identity. A hub that blocks on a request is a slower first screen than a hub that marks itself 200 ms late |
| `session()` → `404`/`401` | The shell intercepts (§4.7); the hub does not render |
| `session()` → other error | Eight cards, unmarked, plus one `SheetNote` stating that authority could not be read and the cards are therefore unmarked. **Never a claim that the operator holds no authority** — that is case 3's meaning and this is not case 3 |
| `authority_classes: []` | Case 3. Eight cards, no marking, no messaging |
| `VITE_PRACTITIONER_BASE_URL` unset | The `RE` and `DE` buttons are **disabled with a stated reason**, never a `#` [50 §9.5]. `ui-external-launch-configured` [50 §10.2] |

---

## 6. Sheet 01 — Fleet Overview

**Route:** `/fleet-status`. **Component:** `FleetOverview` in `src/features/fleet-status/`.

### 6.1 What the wireframe draws

`WF sheet 01`, in DOM order — and the order is load-bearing, because the map is **inserted between** two KPI pairs rather than following four:

| # | WF element | Content as drawn |
|---|---|---|
| 1 | `.sheet-note` | *"**Advisory — not an authoritative readiness report.** … That label is a persistent banner, not a tooltip."* |
| 2 | `.grid.cols-2` → `.kpi` | `Fleet Readiness` · `78%` (`good`) · `▲ 2pt / 30d` |
| 3 | `.grid.cols-2` → `.kpi` | `Warning Lead-Time Coverage` · `64%` · *"primary effectiveness metric — doc 06 §2"* |
| 4 | `.box.map-box` | label `Fleet map — CENTCOM AOR (scope=fleet)`; `svg.aor` viewBox `0 0 640 300`; four land polygons; four graticule lines + labels `20°N`, `10°N`, `50°E`, `60°E`; six place labels; **nine markers**; a selection ring + leader + callout `DDG 113 · 78%` / `selected → sheet 01B`; `aor-label` *"Simulated positions — CENTCOM AOR, not to scale"*; a `.map-key` with three shapes and four dots |
| 5 | `.sheet-note` | *"Click any marker → sheet 01B, scoped to that hull … Positions are generated for this demonstration only"* |
| 6 | `.grid.cols-2` → `.kpi` | `Open Risk Flags` · `11` (`critical`) · `4 critical · 7 warning` |
| 7 | `.grid.cols-2` → `.kpi` | `Restricted Contributors` · `—` · `present: **no** — doc 03 §7.3` |
| 8 | `.box` + `.table-scroll` | label `Risk flags`; columns `Hull` · `Installed item` · `Predicted category` · `Horizon` · `State` |
| 9 | `.row` → `.col.box` | label `Rollup by TYCOM / class`; columns `Class` · `Hulls` · `Readiness` (num) |
| 10 | `.row` → `.col.box` | label `Explanation graph — click any score`; `.placeholder-fig` *"score → contributing degradations → source predictions / casualties / shortfalls (doc 04 §5 decomposability)"* |

Components [50 §3.5], all of them and no others: `SheetFrame`, `TitleBlock`, `SheetNote`, `AdvisoryBanner`, `KpiGrid`, `KpiTile`, `ContributorDisclosure`, `AorMap`, `MapGraticule`, `MapPlaceLabel`, `MapMarker`, `MarkerTooltip`, `MapSelectionCallout`, `MapKey`, `EquivalentTable`, `Box`, `WfTable`, `WfTableScroll`, `StatusChip`, `FigurePlaceholder`, `DegradedFragmentNotice`.

`TitleBlock`: `sheetNo` = `SHEET 01 / FLEET STATUS & READINESS`, `title` = `Fleet Overview`, `persona` = *"Executive / Commander (TYCOM Readiness Officer) — confirmed default landing"*. Its `tb-right` slot carries WF's `Doc 04 §5 / Doc 06 §2` in the wireframe and, **in production, `advisory.methodology_version` and a link to `advisory.methodology_ref`** [50 §2.5, §7.3] — which is what makes the advisory framing inspectable [27 §8.4: `GET /methodology/{version}` is `x-substitution: required` because *"'advisory' is only meaningful if the advice's basis is inspectable"*].

### 6.2 Data wiring

Three queries. **One composed view plus two pass-throughs**, and the reason there are three rather than one is that [30 §3.2](30-gateway.md)'s `fleet_overview` fragment list does not cover the drawn content.

| # | Query | Operation | Setting | Feeds |
|---|---|---|---|---|
| 1 | `keys.views.fleet()` | `GET /api/v1/gateway/views/fleet` [30 §3.2] | **A** | KPIs 1 and 4; the map; the risk-flag table; the class rollup |
| 2 | `keys.passthrough("audit","/effectiveness/warning-lead-time-coverage",{scope:"fleet"})` | `GET /api/v1/audit/effectiveness/warning-lead-time-coverage?scope=fleet` [32 §10.7] | **A** | KPI 2 |
| 3 | `keys.passthrough("fleet-status","/risk-flags",{state:"raised"})` | `GET /api/v1/fleet-status/risk-flags?state=raised&changed_since=&limit=&cursor=` [27 §10.1 row 4] | **A** | The risk-flag table's **rows**, if the composed view's `open_casrep_risk` fragment does not carry them — §6.5 |

`fleet_overview`'s five fragments [30 §3.2] and what each is for:

| Fragment | Upstream | Required | Feeds |
|---|---|---|---|
| `readiness_rollup` | `fleet-status` | **required** | KPI 1's score; the `advisory` block; the `contributor_disclosure` block; the class rollup (§6.6) |
| `asset_status` | `registry` | **required** | The map's twelve markers — `hull_or_tail`, `domain` [20 §4.3]; the risk-flag table's `Hull` column |
| `open_casrep_risk` | `fleet-status` | optional | KPI 4; marker colour; the risk-flag table |
| `availability_windows` | `maintenance` | optional | **Nothing on this sheet.** §6.7 |
| `proposal_counts` | gateway local read model | optional | **Nothing on this sheet.** §6.7 |

**A required fragment failing fails the whole view** — `503 urn:fathom:problem:gateway:required-fragment-unavailable` with *"no partial body"* [30 §3.4] — so the sheet renders `ProblemDetail` with a retry affordance. **`readiness_rollup` and `asset_status` are both required**, which means sheet 01 is all-or-nothing on readiness and on the asset roster, and degrades gracefully only on flags. §17.1's table states it per fragment.

### 6.3 The four KPIs, one by one

`KpiTile`'s reading order is **label → value → sub** [50 §8.3], its `value` prop is `number | string | null` with `null` rendering `—` [50 §3.4 rule 3], and it distinguishes loading, empty, and unknown as three states [50 §5.5].

**KPI 1 — `Fleet Readiness`, drawn `78%` with sub `▲ 2pt / 30d`.**

| Element | Source | Notes |
|---|---|---|
| Value | `data.readiness_rollup` → **`advisory_readiness_score`** [27 §5.3, §8.5] | The field is `advisory_readiness_score`, **never `readiness_score`, `readiness`, `score`, or `rating`** — [27 §8.3]'s `FS-TERM-001` denylist runs over *"any `apps/web` module importing its types"* and `ui-fs-term-001` [50 §10.2] asserts it. **The display label `Fleet Readiness` is permitted** [50 §7.3 rule 4] because it is a label, not an identifier |
| Tone | `good` as drawn | **`[GAP]`.** No threshold anywhere in the corpus maps a score to a tone. §6.8 |
| `null` value | `score: null` + `suppression_reason` [27 §3.9] | Two reasons, **never conflated**: `all_contributors_restricted` and `no_contributors`, both at HTTP **200**. §17.3. **Never `0`, never `100`, never a blank tile** — [27 §3.9] and [27 §13 DO-NOT 4]: rendering `100` *"presents a fully compartmented, possibly failed asset as perfectly ready"* |
| Sub `▲ 2pt / 30d` | **`[GAP]`** | The only delta the contract publishes is **`delta_attribution`** [27 §3.11], which is **assessment-to-assessment**, not 30-day: `previous_assessment_id`, `previous_score`, `score`, `delta`, and four components that sum to `delta` (`from_degradation_change`, `from_weight_change`, `from_contributor_set_change`, `from_methodology_change`), plus `contributor_set_changed` and **`exclusion_set_changed`**. There is no 30-day window field on any operation. §22 row 5 |

**The `▲ 2pt` rendering is replaced, and the replacement is a correctness requirement rather than a substitution.** `[ESTABLISHED HERE]` The sub-line renders `delta` against the previous assessment, **labelled as such** (*"−2.9 vs. previous assessment"*), and **when `exclusion_set_changed` is `true` it says so on the same line**. A bare `▲ 2pt` hides the one thing [27 §3.11] built the block to expose: a score that moved because the *exclusion set* changed moved for a clearance reason, not an engineering one, and presenting that as a readiness improvement is precisely the channel [27 §3.7] describes when it says *"silent renormalization converts a partial view into something indistinguishable from a total view."* Where `delta_attribution` is absent (a first assessment), the sub-line renders *"no previous assessment"* — not `—`, which would read as a zero delta.

**KPI 2 — `Warning Lead-Time Coverage`, drawn `64%`.**

Source: query 2, `GET /api/v1/audit/effectiveness/warning-lead-time-coverage?scope=fleet` [32 §10.7]. `scope`/`id` use [03 §5.4]'s vocabulary (`asset`, `tycom`, `fleet`); `horizon_days` is one of **30, 90, 180** [06 §7, via 27 §7.5]; `stratum` selects `reference_class` and methodology version.

**A bare percentage violates all four of [27 §7.5]'s presentation rules, and [50 §7.4 rule 6] already said so.** The compliant rendering, and every element traces to a field [32 §10.7] states the response carries:

| Required by [27 §7.5] | Rendered as |
|---|---|
| *"Report the lead-time distribution, not only the proportion … p10 / p50 / p90 … plus the count of $A(W,S)$, plus the uncovered count. A coverage figure without its denominator is not interpretable"* | `KpiTile` value = the coverage fraction; **`k-sub` = the covered and uncovered counts**; a two-row `WfTable` beneath the KPI row carrying p10 / p50 / p90 |
| *"Stratify by `reference_class` and by methodology version, always"* | A `StatusChip tone="neutral"` per stratum dimension, from `stratum`. **The horizon is explicit in the label**: `Warning Lead-Time Coverage (30 d)`, never an unlabelled percentage, because the same population yields three different figures at 30, 90, and 180 days |
| *"Report against the chance reference … Coverage reported without the flag rate cannot be distinguished from coverage bought by flagging everything"* | The chance reference and flag rate render **adjacent to the value**, not in a tooltip |
| *"The achievable ceiling is below 1.0 and must be shown … Omitting it invites a demonstration that reports 0.94 against an achievable 0.95 as though the remaining 0.06 were an engineering shortfall"* | The achievable-ceiling fraction renders as a second figure on the same tile |
| [27 §7.6] rule 1 — *"Read-only and attributed"* | `"source": "audit"`, `"computed_at"`, and a link to `"definition_ref"` render in the tile's disclosure detail. `computed_at` is the tile's real currency and is **not** the view's `as_of` |
| [27 §7.6] rule 2 — *"**Never viewer-filtered** … If it cannot be released, the field is `null` with `suppression_reason`, exactly as in §3.9"* | A `null` coverage renders from `suppression_reason` exactly as KPI 1 does (§17.3). **The console never recomputes it over a visible subset** and never divides one returned count by another |
| [27 §7.6] rule 3 | The `AdvisoryBanner` covers it (§6.4) |

**This exceeds a `.kpi` box's drawn capacity, and that is the wireframe's defect rather than this document's over-reach.** The KPI tile renders the fraction, the horizon, and the counts; **the distribution, chance reference, and ceiling render in a `Box` labelled `Lead-time coverage — distribution and reference` placed immediately after the KPI row.** `[ESTABLISHED HERE]`, §22 row 1 files the wireframe edit. Two boxes are not two mechanisms: the KPI is the headline the operator scans and the box is the denominator [27 §7.5] says the headline is uninterpretable without.

**KPI 3 — `Open Risk Flags`, drawn `11` with sub `4 critical · 7 warning`.**

| Element | Source | Notes |
|---|---|---|
| Value `11` | **`[GAP]`.** `data.open_casrep_risk` is a fragment whose shape [30 §3.2] does not state (§3.5). `GET /risk-flags` [27 §10.1] is **cursor-paginated with no total count** — [03 §4] forbids a total count on an unbounded collection, and [32 §10.6] adds that *"here a count is also an aggregation channel"* | §22 row 6 |
| Sub `4 critical · 7 warning` | **`[GAP]`, twice over.** The counts are the same missing total, **and `critical`/`warning` are not the severity vocabulary**: [27 §6.2] fixes it as `advisory_watch`, `casualty_risk_moderate`, `casualty_risk_high` for item classes and `advisory_watch_population`, `casualty_risk_moderate_population` for uncalibrated classes — with *"**no `_high` severity exists**"* for the population classes | §22 row 7 |

**Resolution, `[ESTABLISHED HERE]`, and it renders a real number rather than a guess.** The tile's value is **the count of rows the console actually holds**, labelled as such: `11 shown`, with the `k-sub` reading `of an unbounded set — no total is published`. The rows come from query 3, `GET /risk-flags?state=raised`, whose `limit` is set to the fleet's own scale — **twelve assets** [06 §7] — so a first page is in practice the whole set, and the label is honest when it is not. The severity breakdown renders **by [27 §6.2]'s five values, using their own names**, mapped to chip tones per §6.5's table, with the *word* mandatory beside the dot [50 §8.3].

Three alternatives rejected: paginating to exhaustion to compute a total (a client-side count over an unbounded collection, which is the thing [03 §4] forbids and which would also be the aggregation channel [32 §10.6] warns of); rendering `—` (it reads as *no flags*, and [30 §3.4] forbids exactly that); asking [27](27-fleet-status.md) for a count operation (filed as §22 row 6 rather than assumed).

**KPI 4 — `Restricted Contributors`, drawn `—` with sub `present: **no** — doc 03 §7.3`.**

This is the `ContributorDisclosure` component [50 §7.4], and it is the one KPI whose rendering is fully specified upstream. Source: `data.readiness_rollup.contributor_disclosure` — *"a required, non-nullable member of the response body — never a metadata sidecar, never a header alone"* [27 §3.7], carried *"in **every** view."*

| Field [27 §3.7] | Rendering |
|---|---|
| `restricted_contributors_present` | The headline. `false` → **`present: no`**; `true` → **`present: yes`** with the tile in `warning` tone. **Never an absent tile when `false`** [50 §7.4, §11.4 item 33]: *"a disclosure that appears only when something is hidden is itself the signal"* |
| `restricted_contributor_count` | The tile value. WF's `—` is correct at zero [50 §7.4] |
| `view` | `default` \| `high_side`, as a `StatusChip tone="neutral"`. [27 §10.2]: *"**Every response states which view produced it**, in `contributor_disclosure.view`. Always, including `high_side`"* |
| `completeness` | `partial` \| otherwise, beside the score |
| `statement` | **Verbatim**, as a `SheetNote` adjacent to the score, in `--annotation` serif [50 §2.2]. Not truncated, not tooltipped, not paraphrased [50 §11.4 item 35] |

**The console renders no derived disclosure figure of any kind.** [27 §3.8]'s denylist — `visible_weight_share`, `total_contributor_count`, `excluded_weight`, `coverage_fraction`, `score_full`, *"any `*_of_total` field, and any field whose value is a function of $C \setminus V$"* — runs over props, computed values, and label strings as `ui-forbidden-disclosure-fields` [50 §10.2], **and no ratio is computed in the browser whose denominator ranges over the full contributor set** [50 §7.4 rule 4]. The mechanical test [27 §3.8] gives is the one to apply: *"a ratio whose denominator ranges over $V$ is releasable; a ratio whose denominator ranges over $C$ is not."*

`score_integrity` [27 §4.4] arrives on the same response and is **not** the same block: `unassessed_contributor_count`, `assessed_contributor_count`, `uncalibrated_share`, and its own `statement`. [27 §12.5]'s `fs-disclosure-present` makes **both** required top-level members. `[ESTABLISHED HERE]`: it renders as a second `SheetNote` beneath the disclosure, with its `statement` verbatim — because *"3 contributors could not be assessed at any reference class"* is a different fact from *"1 contributor is above your clearance,"* and a screen that renders one and drops the other tells the operator the score is complete in the dimension it is not. **[50 §3.5]'s inventory has no `ScoreIntegrity` component**; it is a `SheetNote` with a `statement` prop, so no component is invented. §22 row 28 notes the omission for [50 §3.5]'s inventory.

### 6.4 `AdvisoryBanner`, and the header a composed view drops

[27 §8.1](27-fleet-status.md) makes `advisory` a *"required, non-nullable"* top-level member of *"[e]very 2xx response from every readiness, risk-flag, explanation, and status-summary operation."* [27 §8.2] adds the header `X-FATHOM-Advisory: predictive-advisory; authoritative=false; methodology=1.4.0`, *"on every response from this service, **including problem-details responses**"* — **and states why both exist**: *"because a proxy, a **BFF view-model composition [04 §11]**, or a client SDK may drop either one, and the two failure modes are independent."*

**Sheet 01 is a BFF view-model composition, and both mechanisms are at risk on it.**

| Mechanism | On `GET /views/fleet` | Verdict |
|---|---|---|
| Body block | Arrives inside `data.readiness_rollup.advisory` when that fragment's outcome is `ok` | **Available, conditionally.** `readiness_rollup` is a *required* fragment [30 §3.2], so if it is not `ok` the whole view is a `503` and there is no sheet to banner. The conditionality is therefore benign |
| Header | **`[GAP]`.** [30 §8.4](30-gateway.md) enumerates the response headers the gateway forwards — `ETag`, `Location`, `Retry-After`, `Deprecation`, `Sunset`, `X-Classification`, `Idempotency-Replayed` — and that list governs **pass-through**. For a composed view the gateway *computes* `X-Classification` [30 §7.3] and **nothing in [30](30-gateway.md) requires it to emit `X-FATHOM-Advisory`** | §22 row 29 |

**Consequence for `ui-advisory-from-header-only` [50 §10.2]**, which asserts that with the body block absent and the header present the banner still renders: on a composed view **neither** may be present, and the test's premise does not hold. `[ESTABLISHED HERE]`, the three-tier resolution:

1. **Body block present** → render every field from it: `statement` verbatim, `authoritative`/`system_of_record` as the leading assertion, `character`, and `methodology_version`/`methodology_ref` into the `TitleBlock`'s `tb-right` slot [50 §7.3].
2. **Header present, body absent** → render from the header [50 §7.3 rule 3]. This is the pass-through case (§6.2 query 3, and every sheet in §10–§14).
3. **Neither present, and the sheet renders a readiness figure** → the banner renders in a **degraded form**: the assertion that the view is advisory and not a system of record, and an explicit statement that the methodology reference is unavailable, with a retry. It does **not** synthesize a `statement` — [50 §11.4 item 35] forbids paraphrasing it and a locally-held copy would be a hard-coded marking. The methodology reference is recoverable by a separate pass-through, `GET /api/v1/fleet-status/methodology` [27 §10.1 row 9], and the degraded banner offers it as a link rather than a value.

`display_requirement: "must_be_surfaced"` [27 §8.1] is asserted at runtime: *"if the value is `must_be_surfaced` and the banner is not mounted in the rendered tree, the development build throws"* [50 §7.3]. **Tier 3 satisfies the assertion**, because the banner *is* mounted; what is missing is a field, not the component. That distinction is the whole reason tier 3 exists rather than a silent omission.

### 6.5 The risk-flag table

WF columns → fields, from `risk_flag` [27 §2.4]:

| WF column | Field | Notes |
|---|---|---|
| `Hull` | `data.asset_status` → **`hull_or_tail`** [20 §4.3], joined on `asset_id` | **This is a within-view join across two fragments of one envelope, and it is permitted.** [50 §5.3] rule 6 forbids a join *"across two composed views"*; both fragments are in one. [20 §7 / WF sheet 02] requires the hull *"rendered with a space, never a hyphen — SECNAVINST 5030.8D"*, so the value is rendered verbatim and never reformatted |
| `Installed item` | `installed_item_id` [27 §2.4] | **Rendered as a link to `/telemetry/installed-items/{id}`**, which is the drilldown WF sheet 03 exists for. **A human-readable item name (`SSDG No. 2`) is a `[GAP]`**: `installed_items` [20 §4.5.1] carries `niin`, `iuid`, `serial_or_lot`, `eic`, and an `sclsis_record` JSONB — no `label` or `name` column, and *"[t]here is no column, attribute, or wire field named `equipment_id` in this service."* §22 row 30. Interim: render `niin` + `serial_or_lot` where the `asset_detail`-class fragments supply them, and the bare identifier otherwise — **never a fabricated nomenclature** |
| `Predicted category` | **`predicted_casualty_category_candidate`** [27 §2.4, §8.5] | The field name is mandatory; `casrep_category` and `casualty_category` are on [27 §8.3]'s denylist. WF draws `CAT 3` and `class_estimate` in the same column, which conflates a category with a **reference class** — §22 row 31. This document renders the category here and `reference_class` [27 §2.4] as a separate `StatusChip tone="neutral"`, because [03 §7.1] makes reference class the thing consumers *must* branch on and burying it in a category column hides it |
| `Horizon` | `horizon_days` [27 §2.4] | Rendered with its unit. `—` where absent, and WF's `—` on a `cleared` row is correct |
| `State` | `state` [27 §2.4] — `candidate \| raised \| evidence_invalidated \| mitigation_in_progress \| clearing \| cleared \| suppressed` | `StatusChip`, **word mandatory** [50 §8.3]. **`candidate` never appears**: [27 §6.1] makes it not operator-visible and [27 §7.5] warns it *"warned nobody"* — the query filters `state=raised` and the console never requests `candidate`. `suppressed` renders distinctly with `clear_cause: methodology_suppression` [27 §2.4] and its named approver, because an operator must not read an audited suppression as a cleared flag |

**Severity → chip tone.** [27 §6.2]'s five values collapse onto [50 §2.2]'s four tones, and the collapse is lossy, so **the severity word renders beside the dot in every case**:

| `severity` [27 §6.2] | Tone | Word rendered |
|---|---|---|
| `casualty_risk_high` | `critical` | `casualty_risk_high` |
| `casualty_risk_moderate` | `warning` | `casualty_risk_moderate` |
| `casualty_risk_moderate_population` | `warning` | `casualty_risk_moderate_population` |
| `advisory_watch` | `warning` | `advisory_watch` |
| `advisory_watch_population` | `warning` | `advisory_watch_population` |
| *(no open flag for that asset)* | `good` | `no open flag` |
| *(fragment not `ok`)* | `neutral` | `unknown` — §7.4 |

`uncalibrated: true` [27 §2.4] renders as an additional `StatusChip tone="neutral"` reading `uncalibrated`, on every row that carries it. It is the same fact `UncalibratedCell` renders on sheet 04 (§11.3) and the two must not disagree.

**Where the rows come from.** [30 §3.2]'s `open_casrep_risk` fragment has no stated shape (§3.5), so the table's row source is **query 3's pass-through**, `GET /api/v1/fleet-status/risk-flags?state=raised`, whose response *is* schema'd. The fragment is used for **the presence and severity signal the map needs** (§7.4) and for KPI 3's degraded case. `[ESTABLISHED HERE]`, and it is deliberately redundant: if the fragment's shape is later documented, the pass-through collapses into it and the table's rendering does not change.

### 6.6 The class rollup, and the scope value it needs

WF box 9: `Class` · `Hulls` · `Readiness`, drawn with `DDG 51 Flt IIA / 5 / 81%`.

| WF column | Source | Verdict |
|---|---|---|
| `Class` | `assets.class_id` [20 §4.3], *"a **string** not a UUID"*, e.g. `"DDG-51-FLTIIA"`; label from `GET /classes/{class_id}` [20 §6.1 row 7] | Available |
| `Hulls` | A count of assets in the class | **Available and legitimate**, uniquely on this sheet: the denominator is `data.asset_status`, a **required fragment** covering the whole fleet of twelve [06 §7]. Counting rows of a fully-materialized required fragment is presentation, not an unbounded count [50 §3.3 gap 1's *"client-side only over a fully-materialized page"*] |
| `Readiness` | **`[GAP]`.** `GET /readiness`'s `scope` accepts `asset \| system \| fleet \| fleet_grouping` [27 §10.1 row 1] — **`class` is not a scope value**. `fleet_grouping` is *"TYCOM or other fleet grouping"* addressed by `grouping_id`, and [27 §3.10] leaves the grouping's intrinsic weight — *"hull tasking"* — **`[OPEN]` per its own OD-2** | §22 row 8 |

**Resolution, `[ESTABLISHED HERE]`:** the box's label is WF's own `Rollup by TYCOM / class` and it renders **`scope=fleet_grouping`** rows — `GET /api/v1/fleet-status/readiness?scope=fleet_grouping` — with the `Class` column reading whatever grouping identifier the response carries in `subject_grouping_id` [27 §2.2]. **The console does not group by `class_id` and compute a per-class score**: a power mean over per-asset scores with an unspecified weight [27 §3.2, §3.10] is a rollup formula, and computing one in the browser would be manufacturing a readiness figure — the exact thing [04 §5]'s *"advisory overlay, not a readiness system of record"* decision forbids, and a client-side derivation [50 §11.3 item 20] besides. Where no `fleet_grouping` assessment exists, the box renders `EmptyState` naming the scope, and the `Hulls` column still renders from `asset_status` grouped by `class_id` **without a score column** — a class roster is a registry fact and is useful on its own.

Every row's `Readiness` value is subject to §17.3's suppressed-score rendering, and each row carries its **own** `contributor_disclosure` — [27 §3.10]: *"`restricted_contributors_present` propagates upward as a logical OR … Silence at fleet level about an exclusion four levels down is rule 3 violated at the level operators actually look at."* A grouping row whose disclosure differs from the fleet KPI's renders its own chip.

### 6.7 The explanation-graph placeholder, and two fragments this sheet does not use

**Box 10 is a `FigurePlaceholder`, and it stays one.** [50 §3.3 gap 4]: *"[n]o charting library is adopted anywhere in this document … When 51 replaces a placeholder with a real figure, the library choice is 51's."* **This document does not replace it**, for a reason that is not deferral: the figure is *"score → contributing degradations → source predictions / casualties / shortfalls"*, which is `GET /readiness/{assessment_id}/explanation` [27 §10.1 row 3] — a **cursor-paginated tree ordered by `attribution_share DESC` with both disclosure blocks repeated on every page** [27 §5.3]. A graph rendered from a partial page would misstate the decomposition, and a graph rendered after exhausting the cursor is an unbounded fetch on a 1.5 s view. So:

- The `<figcaption>` carries WF's own text verbatim [50 §8.5], **never an empty `aria-hidden` box**.
- The box additionally renders a **`WfTable` of the first page** of `GET /readiness/{assessment_id}/explanation`, ordered as served, with `contributor_id`, `path`, `kind`, `attribution_share`, `deduction_points`, `basis`, `uncalibrated`, `reference_class`, and `render_hint` [27 §5.3] — a table is not a chart and needs no library, it paginates honestly, and it is the SC 1.1.1 alternative the figure would need anyway.
- `deduction_points` sums to `100 − R(V)` exactly [27 §5.3, tests `fs-decomp`/`fs-decomp-exact`]. **The console renders them and sums nothing**, so a page that does not sum is a server defect the console makes visible rather than hides.
- Each row's `basis` value [27 §2.3] — `calibrated_item`, `population_hazard`, `observed_indicator`, `observed_anomaly`, `accepted_risk`, `supply_constrained`, `adjudicated_finding`, `child_rollup`, `unassessed` — renders as a `StatusChip tone="neutral"` with the value verbatim, and **`render_hint`** (`point_estimate | population_band | observed | qualitative`) governs whether a numeric is shown at all.
- **No causal language, anywhere in this box.** [09 §9.3 item 20] / D23 and [50 §7.5]. A `basis: adjudicated_finding` row is the only row that may cite a finding, and it cites it — it does not paraphrase it as a cause.

**`availability_windows` and `proposal_counts` feed nothing on sheet 01.** Both are optional fragments [30 §3.2] and WF sheet 01 draws neither an availability window nor a proposal count. `[ESTABLISHED HERE]`: the console **requests the view as specified and ignores those two members**, and does *not* invent a box for them [50 §11.2 item 12]. Two consequences worth stating so nobody "fixes" it: their outcomes are excluded from the sheet's `DegradedFragmentNotice` set (a notice about a fragment no box renders is noise an operator cannot act on), and `proposal_counts` is **not** the nav badge's source — §4.5 uses `GET /proposals/summary`, because the badge is shell chrome present on every route while `fleet_overview` is fetched on one.

### 6.8 The `[GAP]` that recurs on every screen: score-to-tone thresholds

WF colours KPI values (`78%` `good`, `11` `critical`, `2` `warning`) and chips. **No document in the corpus maps a readiness score, a flag count, or a probability to a tone.** [27 §6.2] gives *severity* classes for flags — which §6.5 uses — but nothing for a score.

`[ESTABLISHED HERE]`, and it is the conservative call: **a score-bearing `KpiTile` renders with no tone.** `--ink` value on `--paper`, 13.70 : 1 [50 §8.4]. A tone is applied only where a **field** carries the classification:

| Value | Tone from | Basis |
|---|---|---|
| A risk-flag row or count | `severity` | [27 §6.2] |
| A proposal row | `status` | [03 §7.2] |
| A candidate disposition | `disposition` | [24 §4.4] |
| A stock condition | `condition_code` | [26 §2.3] |
| A readiness score, a coverage fraction, a flag count, a probability | **nothing** | No source. §22 row 32 asks [27](27-fleet-status.md) for banding, noting that any banding it supplies is *"labelled advisory like everything else"* [27 §7.6 rule 3] |

Inventing a threshold would be worse than uncoloured: a green `78%` is an assertion that 78 is acceptable, made by a UI engineer, on a view [04 §5] says *"must not present itself as, or be mistaken for, authoritative readiness reporting."* `ui-no-invented-banding` (§19.1) asserts no component maps a numeric to a tone without a field.

---

## 7. The AOR map

### 7.1 What the wireframe fixes, and what [50](50-ui-design-system.md) already decided

[50 §3.5](50-ui-design-system.md) specified `AorMap` completely: no projection (*"schematic and not to scale"*, the `aor-label` **required and non-removable**), the `0 0 640 300` viewBox as authored, marker shape from `Asset.domain`, marker colour from severity, selection navigating to `/fleet-status/assets/:assetId`, and the accessibility treatment of [50 §8.5] — `<figure>`/`<figcaption>`, `role="group"` not `role="img"`, focusable named markers, `aria-hidden` scenery, a **required** `EquivalentTable`, ≥ 24 × 24 px hit areas, and labels at the `--fs-100` floor.

**None of that is re-decided.** This section specifies the two things [50](50-ui-design-system.md) left to this document: the position table's concrete shape and location, and the per-marker wiring — including two places where [50 §3.5]'s own wiring cannot work as written.

### 7.2 The position table

[50 §13 row 3](50-ui-design-system.md) established the interim: *"[n]o aggregate, event, or operation in the corpus carries a geographic position for an asset,"* and the map is *"rendered from a build-time static table in `apps/web`."* This document verified the premise independently against [27](27-fleet-status.md) — an exhaustive search for `lat`, `lon`, `latitude`, `longitude`, `geo*`, `coordinates`, `position`, `homeport`, and `AOR` returns **zero** hits; the only location-adjacent members are `subject_grouping_id` (an opaque grouping identifier, [27 §2.2]) and `rm_supply`'s internal `(NIIN, location)` read-model key ([27 §9.3], not on any response schema). The premise holds.

**Location:** `apps/web/src/features/fleet-status/demo-positions.ts` [50 §3.5].

```ts
// apps/web/src/features/fleet-status/demo-positions.ts
//
// DEMONSTRATION ONLY. Document 07 records no public source for real fleet disposition
// and none is used here [WF sheet 01]. No aggregate, event, or operation in the corpus
// carries a geographic position for an asset [50 §13 row 3, verified against 27 in 51 §7.2].
// This file is a DRAWING AID, not a registry. It is deliberately minimal so that it
// cannot become one.

/** viewBox units, NOT latitude/longitude. Must match svg.aor's authored viewBox. */
export const AOR_VIEWBOX = { minX: 0, minY: 0, width: 640, height: 300 } as const;

/** [06 §7]: twelve assets. Asserted, not assumed. */
export const DEMO_POSITION_COUNT = 12;

/** asset_id -> viewBox coordinate. NOTHING ELSE. */
export const DEMO_POSITIONS: Readonly<Record<string, { readonly x: number; readonly y: number }>> = {
  // twelve entries, keyed by the asset_id values of the committed synthetic fixture
};
```

Six rules, `[ESTABLISHED HERE]`, and rules 2 and 3 are the ones that keep the file honest:

1. **Keyed by `asset_id`** [03 §3.3], never by `hull_or_tail`. A hull number is a display string [20 §7]; an `asset_id` is the identifier every operation takes.
2. **The record's value is `{x, y}` and nothing else.** No `hull_or_tail`, no `domain`, no `class_id`, no label. Every rendered attribute comes from `data.asset_status` at request time, so the file **cannot** drift into a shadow registry — which is the failure mode of every static table that starts by adding "just the hull number for readability."
3. **Twelve entries, and the count is asserted.** `DEMO_POSITION_COUNT` is checked against `Object.keys(DEMO_POSITIONS).length` at module load in development and by `ui-map-position-count` (§19.1). WF draws **nine** markers plus one selected — ten — against [06 §7]'s twelve; the table covers twelve, per [50 §3.5]'s own *"covering all **twelve** assets of [06 §7]."*
4. **An asset in `asset_status` with no entry is rendered off-map, never at the origin.** An `UnplottedAssets` list — a `WfTable` inside the map `Box`, below the `MapKey` — names them. `(0,0)` would place a hull in the north-west corner of the Red Sea and look like data.
5. **An entry with no matching asset fails the build**, not the render. `ui-map-positions-match-fixture` (§19.1) asserts key-set equality against the committed synthetic reference dataset [09 §8.5, 50 §12.1] — the same fixture [50 §12.1] adopts so that *"the map's twelve markers and the fleet rollup are exercised at the specified scale."* A stale key is a dead marker nobody notices.
6. **Coordinates are clamped to `AOR_VIEWBOX` at module load.** An out-of-range value is a build failure, because an SVG renders it silently outside the frame.

**Where the marker sits in the SVG**, wired to WF's authored structure: the scenery — `rect.water`, four `polygon.land`, four `line.grat` with their four `text.grat-label`, six `text.place-label` — is transcribed verbatim into `AorMap`, `MapGraticule`, and `MapPlaceLabel`, all `aria-hidden="true"` [50 §8.5]. Markers render **after** the scenery so they paint above it, each at `DEMO_POSITIONS[asset_id]`, with the shape from `domain` [50 §3.5]: `circle r=4.5` (surface), `polygon` triangle (subsurface), `rect 8×8` (unmanned) — WF's own geometry. The four label classes render at `--fs-100` [50 §2.3, §13 row 6], and **if the raised labels no longer fit, the viewBox widens** — [50 §2.3] anticipated exactly this and made it *"a layout consequence, not a token one."*

### 7.3 Selection, and the callout

WF draws a selection state: `circle.sel-ring` (r = 10, `--dash-ring: 2 2`), `.marker.selected` (`--bw-3` stroke), `line.leader` (`--dash-lead: 3 2`), `rect.sel-label-bg`, `text.sel-label` (`DDG 113 · 78%`), `text.sel-sub` (`selected → sheet 01B`).

`[ESTABLISHED HERE]`: **selection is hover-or-focus, and it is ephemeral UI state** [50 §5.7] — `useState` in `FleetOverview`, not a URL parameter. Activation (click, Enter, or Space) **navigates** to `/fleet-status/assets/:assetId`. Two rules follow:

1. **The callout is not the marker's accessible name.** [50 §3.2] is explicit that a `Tooltip` is *"supplementary only … because a tooltip is unavailable to touch input and is not a substitute for a label."* The accessible name is composed on the marker itself, per [50 §8.5]: hull, domain, severity word, advisory readiness score — e.g. `"DDG 113, surface, casualty_risk_high, advisory readiness 78 percent"`.
2. **`text.sel-label`'s `DDG 113 · 78%` renders the per-asset score, and sheet 01's composed view may not have it.** `fleet_overview`'s `readiness_rollup` fragment is a *fleet* rollup [30 §3.2]; there is no per-asset score fragment in that view. **The callout therefore renders `hull_or_tail` and the severity word, and omits the percentage** unless the score is present. `[ESTABLISHED HERE]` — fetching twelve per-asset views to populate a hover label would be a twelve-way fan-out for a tooltip, which is the thing [30 §3.2] built `proposal_counts` as a local read model to avoid. §22 row 33 notes the wireframe shows a value the view does not carry.

### 7.4 Marker colour: [50 §3.5]'s rule cannot work as written

[50 §3.5](50-ui-design-system.md) specifies the `neutral` marker as rendered *"when the `open_casrep_risk` fragment's outcome **for that asset** is `empty` or `unavailable`."*

**There is no per-asset fragment outcome.** [30 §3.4](30-gateway.md)'s envelope keys `fragments` by **fragment name**, one entry per fragment, one `outcome` each: `"open_casrep_risk": { "outcome": "unavailable", "upstream": "fleet-status", "retryable": true }`. The fragment either resolved for the whole fleet or did not resolve at all.

**Corrected rule, `[ESTABLISHED HERE]`, and it preserves [50](50-ui-design-system.md)'s intent — render the gap, not zero — at the granularity the contract actually offers:**

| `open_casrep_risk` outcome | Every marker's colour |
|---|---|
| `ok` | Per asset: the **highest severity among that asset's open flags**, mapped by §6.5's table; `good` where the asset appears in `asset_status` and has no open flag |
| `empty` | **`good`** on every marker. `empty` is *"upstream answered authoritatively: there is none"* [30 §3.4] — a fleet with no open flags is a fact, not an absence |
| `timeout` \| `unavailable` \| `forbidden` | **`neutral` on every marker**, and the map renders `DegradedFragmentNotice` naming the fragment and the outcome. Not one marker is coloured, because the console does not know any asset's flag state |

WF's map key reads `neutral` as *"no recent contact"* — [50 §13 row 4] already established that **no field in the corpus expresses recency of contact** and adopted *unknown* as the reading. This document keeps that reading and **changes the key's label to `flag state unknown`**, because a key that says "no recent contact" beside a dot that means "the flag service timed out" is a false statement about the fleet. §22 row 34.

`MapKey` renders WF's seven items: three shapes (`● surface`, `▲ subsurface`, `■ unmanned`) and four dots — and the four dots become **six**, one per §6.5 severity plus `no open flag` and `flag state unknown`, because the key must enumerate what the map can actually draw. `[ESTABLISHED HERE]`, §22 row 34's second clause.

### 7.5 `EquivalentTable`: [50 §8.5] identifies the wrong table

[50 §8.5](50-ui-design-system.md) part 4 requires a **non-optional** equivalent table and states: *"On sheet 01 the co-located 'Risk flags' `Box` already is this table — which is why §3.5 marks it required, not optional."*

**It is not that table, and the difference is not cosmetic.** The map encodes **assets** — twelve markers, one per hull, shape = domain, colour = flag state. The Risk-flags box enumerates **flags** — [27 §10.1 row 4]'s cursor-paginated `GET /risk-flags`, of which WF draws three rows, one of them `cleared`. The two have different row sets, different cardinality, and different subjects:

- An asset with **no** open flag has a marker and **no row** in the flags table. WF draws exactly this: eight `good`/`neutral` markers and three flag rows.
- A single asset with **three** open flags has one marker and three rows.
- A `cleared` flag has a row and colours no marker.

So the flags table is not an equivalent of the map: an assistive-technology user reading it would conclude the fleet is three hulls. SC 1.1.1's text alternative and SC 1.4.1's non-colour equivalent both fail.

**Corrected, `[ESTABLISHED HERE]`:** `EquivalentTable` renders **one row per asset**, from `data.asset_status` (required, so it is always present when the sheet renders) joined with `data.open_casrep_risk` (§6.5's within-envelope join), with columns `Hull` · `Domain` · `Flag state` · `Plotted`. It sits **inside the map `Box`, visually hidden** [50 §8.5], because the Risk-flags box already occupies the visible slot and two visible tables of overlapping content is its own defect. The `Plotted` column is what makes rule 4 of §7.2 checkable by a user rather than only by a test. §22 row 35 corrects [50 §8.5] and [50 §3.5].

### 7.6 Map states

| Condition | Rendering |
|---|---|
| View loading | `LoadingSkeleton` at the map's final dimensions [50 §5.5]. **Never the hatch fill** — `--hatch` means *"a figure belongs here and is not rendered"* [50 §2.5, §11.1 item 6] |
| View `503` | The whole sheet is `ProblemDetail` (§6.2); no map |
| `asset_status` `ok`, `open_casrep_risk` not `ok` | Scenery, twelve markers, all `neutral`, `DegradedFragmentNotice` inside the box (§7.4) |
| `asset_status` `ok` with zero assets | `EmptyState` naming the scope, **inside the map frame**, with the scenery and the `aor-label` still rendered — the label is required content [50 §3.5] and an empty fleet is a legitimate answer for a fresh deployment |
| An asset with no `DEMO_POSITIONS` entry | Rendered in the `UnplottedAssets` list, named (§7.2 rule 4) |
| `prefers-reduced-motion` | No transition on selection [50 §2.7 item 5, §8.6] |

---

## 8. Sheet 01B — Vehicle Detail

**Route:** `/fleet-status/assets/:assetId`. **Component:** `VehicleDetail` in `src/features/fleet-status/`.

### 8.1 What the wireframe draws, and the one thing it says that is not true

`WF sheet 01B`, in DOM order:

| # | WF element | Content as drawn |
|---|---|---|
| 1 | `.sheet-note` | *"Same four-metric shape as the Fleet Overview, re-scoped to one hull … `GET /readiness?scope=asset&id=` … Nothing here is a second mechanism."* |
| 2 | `.row` → chips + `.btn.ghost` | `DDG 113 · UIC 21487` · `Class DDG 51 Flt IIA` · `OFRP: Sustainment` (`good`) · `← back to fleet map` |
| 3 | `.grid.cols-4` → four `.kpi` | `Hull Readiness` `78%` (`good`) *"rank 6 of 12 in class"* · `Warning Lead-Time Coverage` `71%` *"this hull vs. 64% fleet-wide"* · `Open Risk Flags` `2` (`warning`) *"0 critical · 2 warning"* · `Restricted Contributors` `—` *"present: **no**"* |
| 4 | `.row` → `.col.box` | label `This hull's risk flags`; columns `Installed item` · `Predicted category` · `Horizon` · `State` |
| 5 | `.row` → `.col.box` | label `Rollup by system (ESWBS)`; columns `System` · `Readiness` (num) |
| 6 | `.row` → three `.btn` | `Open full asset browser →` (primary) · `View maintenance history` · `View predictions` |

Components [50 §3.5]: `SheetFrame`, `SheetNote`, `ChipRow`, `StatusChip`, `KpiGrid`, `KpiTile`, `ContributorDisclosure`, `AdvisoryBanner`, `Box`, `WfTable`, `Button`, `BackLink`.

**The sheet-note's `GET /readiness?scope=asset&id=` is not the operation.** [27 §10.1 row 1] declares `GET /readiness?scope=&asset_id=&system_id=&grouping_id=&view=&as_of=&changed_since=&limit=&cursor=` — the parameter is **`asset_id`**, not `id`. Trivial, and worth stating because a sheet-note is where an implementer looks first. §22 row 36.

**And the note's *"[s]ame four-metric shape … Nothing here is a second mechanism"* is true of the formula and false of the wiring**, which is why §2 rule 2 forbids fusing §6 and §8 into one component: sheet 01's four KPIs come from `GET /views/fleet` + `audit`; sheet 01B's come from `GET /views/asset/{asset_id}` + `audit` at a different scope, over a *different fragment set* (`readiness`, optional, not `readiness_rollup`, required). The tiles look identical and their degradation behaviour is opposite — §8.5.

### 8.2 Data wiring

| # | Query | Operation | Setting | Feeds |
|---|---|---|---|---|
| 1 | `keys.views.asset(assetId)` | `GET /api/v1/gateway/views/asset/{asset_id}` [30 §3.2] | **A** | Chips; KPIs 1, 3, 4; the flags box |
| 2 | `keys.passthrough("audit","/effectiveness/warning-lead-time-coverage",{scope:"asset",id:assetId})` | `GET /api/v1/audit/effectiveness/warning-lead-time-coverage?scope=asset&id={assetId}` [32 §10.7] | **A** | KPI 2 |
| 3 | `keys.passthrough("fleet-status","/readiness",{scope:"system",asset_id:assetId})` | `GET /api/v1/fleet-status/readiness?scope=system&asset_id={assetId}` [27 §10.1 row 1] | **A** | The ESWBS rollup box |
| 4 | `keys.passthrough("fleet-status","/risk-flags",{asset_id:assetId,state:"raised"})` | `GET /api/v1/fleet-status/risk-flags?asset_id={assetId}&state=raised` [27 §10.1 row 4] | **A** | The flags box's rows, on the same basis as §6.5 |

`asset_detail`'s eight fragments [30 §3.2]:

| Fragment | Upstream | Required | Feeds on this sheet |
|---|---|---|---|
| `asset` | `registry` | **required** | The three chips: `hull_or_tail`, `uic`, `class_id`, `domain`, `ofrp_phase` [20 §4.3] |
| `configuration_baseline` | `registry` | **required** | Nothing here — §9 uses it |
| `readiness` | `fleet-status` | optional | KPI 1; the `advisory` block; `contributor_disclosure`; `score_integrity` |
| `predictions` | `pdm` | optional | The `View predictions` button's enablement (§8.4) |
| `open_work` | `maintenance` | optional | The `View maintenance history` button's enablement |
| `parts_position` | `supply` | optional | Nothing here |
| `open_proposals` | gateway local | optional | Nothing here |
| `installed_items` | `registry` | optional, **phase 1** | The flags box's item rendering (§6.5's `[GAP]` on item nomenclature) |

**`readiness` is optional on this view and `readiness_rollup` is required on sheet 01's.** That is the single most important difference between the two sheets and it inverts their failure modes: sheet 01 with a dead fleet-status returns `503` and renders nothing; **sheet 01B with a dead fleet-status returns `200` with `degraded: true`** and renders the hull's identity, its configuration, and its work — with the readiness KPIs as `DegradedFragmentNotice`. That is the better behaviour and it is [30 §3.2]'s own reasoning: *"An asset view without a readiness score is useful; an asset view that cannot confirm the asset exists is a lie."*

### 8.3 The four KPIs

**KPI 1 — `Hull Readiness`, drawn `78%` with sub `rank 6 of 12 in class`.**

Value: `data.readiness.advisory_readiness_score` [27 §5.3, §8.5]. Suppression, tone, and disclosure exactly as §6.3 — the same components, the same `null` handling, the same absence of banding (§6.8).

**`rank 6 of 12 in class` is a `[GAP]` and the console does not compute it.** No rank field exists on `readiness_assessment` [27 §2.2] or in the explanation response [27 §5.3], and [27 §3.6] discusses *"cross-hull comparison"* only inside a **ruled-out** formulation. Computing it client-side would require twelve per-asset scores — twelve composed views — and then a comparison **across** them, which is a cross-view derivation [50 §5.3 rule 6, §11.3 item 20] and, worse, a comparison of figures each renormalized over a *different visible contributor set* [27 §3.7]. Two hulls' scores are not comparable when one excluded a compartmented contributor and the other did not; a rank computed over them is a number with no meaning that changes with the viewer's clearance. **The sub-line renders `delta_attribution` instead**, exactly as §6.3's KPI 1 does. §22 row 9.

**KPI 2 — `Warning Lead-Time Coverage`, drawn `71%` with sub `this hull vs. 64% fleet-wide`.**

Source: query 2 at `scope=asset&id={assetId}` [32 §10.7], with §6.3's full compliant rendering — the same distribution box, the same chance reference, the same ceiling, the same `computed_at`/`definition_ref` attribution.

**The sub-line's comparison to a fleet figure requires two calls and is permitted, narrowly.** `[ESTABLISHED HERE]`: rendering both figures side by side is *presentation of two independently attributed values*, not a derivation — the console shows `71%` and `64%` and **computes no difference**, no ratio, and no ranking. It also renders both `computed_at` values, because two coverage figures computed at different instants are not comparable and the operator must be able to see that. A single-figure fallback applies when the fleet call fails: the hull figure renders alone, with the comparison line absent rather than partial.

**KPI 3 — `Open Risk Flags`, drawn `2` with sub `0 critical · 2 warning`.**

Same `[GAP]`s as §6.3's KPI 3 and the same resolution — `n shown`, the severity breakdown by [27 §6.2]'s own five names — **except** that the denominator here is genuinely bounded in practice: one hull's open flags. The label still says `shown`, because [03 §4] publishes no total at any scope and the console does not invent one at the scope where it would probably be right.

**KPI 4 — `Restricted Contributors`, drawn `—` with sub `present: no`.**

`data.readiness.contributor_disclosure` and `score_integrity`, rendered exactly as §6.3's KPI 4. [27 §3.10]'s propagation rules mean this tile and sheet 01's can legitimately differ: `restricted_contributors_present` ORs upward and `restricted_contributor_count` sums over descendants, so a fleet `count: 3` and a hull `count: 1` are consistent. **Neither figure is derived from the other**, in either direction.

### 8.4 The chips, the system rollup, and the three buttons

**Chips** (`ChipRow`, all `tone="neutral"` except the third):

| WF chip | Fields [20 §4.3] |
|---|---|
| `DDG 113 · UIC 21487` | `hull_or_tail` + `uic`. Hull rendered verbatim, with a space, never a hyphen [20 §7 / WF sheet 02, SECNAVINST 5030.8D]. `uic_service_prefix` is a separate column and renders where present |
| `Class DDG 51 Flt IIA` | `class_id`, with its label from `GET /classes/{class_id}` [20 §6.1 row 7] where fetched; the identifier verbatim otherwise |
| `OFRP: Sustainment` (`good`) | `ofrp_phase`. **Rendered `tone="neutral"`, not `good`** — §6.8: no field maps an OFRP phase to a tone, and [27 §9.3 row 2] / [27 DO-NOT 22] explicitly **forbid treating an OFRP phase change as degradation**, which is exactly what a `good` chip asserts. §22 row 37 |
| *(absent)* | `operational_status` and `deployment_state` [20 §4.3] are drawn nowhere and are **not added** [50 §11.2 item 12] |

**System rollup (ESWBS).** Query 3, `GET /readiness?scope=system&asset_id={assetId}`. Rows: `subject_system_id` → `advisory_readiness_score` [27 §2.2, §5.3]. The `System` column's `233 — Propulsion` needs `eswbs` and `label`, which are `SystemNode` fields [20 §4.3] — **`eswbs` is *"populated only where `scheme_family = 'eswbs'`"***, so the column renders `eswbs — label` where the scheme is ESWBS and `hsc_code — label` otherwise, from `GET /assets/{asset_id}/systems` [20 §6.1 row 4]. WF's box label says `(ESWBS)` unconditionally; **the label is conditioned on `scheme_family`** [20 §4.1: *"`GET /assets/{id}/systems` **echoes it on every response**"*], because a hull under a non-ESWBS hierarchy scheme would carry a false header. `[ESTABLISHED HERE]`, §22 row 38.

**[27 §10.1] does not explicitly state that `scope=system` accepts `asset_id`** — the parameter list is flat (`scope=&asset_id=&system_id=&grouping_id=`) and the pairing is unstated. §22 row 39 asks for the clarification. The interim is the pairing above; the fallback, if it is rejected, is one call per system from `GET /assets/{asset_id}/systems`, which is a browser-side fan-out this document does not want and would file as a further correction.

Every rollup row carries its own suppression (§17.3) and its own `contributor_disclosure` chip, per [27 §3.10].

**The three buttons** are `Button`s with `asChild` over router `Link`s [50 §3.2]:

| WF button | Target | Enablement |
|---|---|---|
| `Open full asset browser →` (primary) | `/registry/assets/{assetId}` | Always. §9 renders it |
| `View maintenance history` | `/maintenance/assets/{assetId}` (§3.1) | Always enabled. **Not conditioned on `open_work`'s outcome** — a fragment timeout on *this* view says nothing about whether the *next* screen will load, and a control disabled by another screen's failure is unexplainable |
| `View predictions` | `/pdm/installed-items/…` — **`[GAP]`** | [50 §4.2]'s pdm routes are `/pdm` and `/pdm/installed-items/:installedItemId`; **there is no asset-scoped pdm route**, and `GET /predictions` [22 §10] does accept `asset_id=`. The button targets **`/pdm?asset_id={assetId}`** — a query parameter on the index route, using the operation's own parameter name verbatim [50 §4.4] — rather than a new segment, because §11 renders the same sheet 04 filtered. §22 row 40 notes it for [50 §4.2] |

`BackLink` renders WF's `← back to fleet map` as `Button variant="ghost"` targeting `/fleet-status`, and it is a **link, not `history.back()`**: a deep link into 01B has no fleet view behind it.

### 8.5 Sheet 01B states

| Condition | Rendering |
|---|---|
| `asset` or `configuration_baseline` not `ok` | `503` for the whole view [30 §3.4]; the sheet is `ProblemDetail`. *"An asset view that cannot confirm the asset exists is a lie"* [30 §3.2] |
| `readiness` not `ok` | `200 degraded: true`. **KPIs 1 and 4 render `DegradedFragmentNotice`; the chips, the flags box, and the buttons all render.** `ui-kpi-never-renders-zero-for-unknown` [50 §10.2] covers the tiles. **`AdvisoryBanner` renders in §6.4's tier-3 degraded form**, because the sheet still shows a readiness *view* even when the score is unavailable |
| `readiness` `ok` with `score: null` | §17.3 — the two suppression reasons, distinctly, at HTTP 200 |
| `installed_items` (phase 1) not `ok` | The flags box renders identifiers without item nomenclature, and says so. **Not an empty table** |
| Unknown `:assetId` | The gateway returns the owner's `404` [30 §8.4: upstream problem bodies *"never rewritten"*]; `ProblemDetail` with a link to `/registry` |
| Query 2 or 3 fails | That box or tile alone renders `ProblemDetail` inline. A pass-through failure never takes the sheet down |

---

## 9. Sheet 02 — Asset Browser

**Routes:** `/registry` and `/registry/assets/:assetId`. **Component:** `AssetBrowser` in `src/features/registry/`. One component, two URLs — the second populates the right-hand boxes [50 §4.2].

### 9.1 What the wireframe draws

| # | WF element | Content as drawn |
|---|---|---|
| 1 | `.col.box` (flex 0 0 260px) | label `Asset search`; columns `Hull` · `Domain`; three rows, the selected one bold |
| 2 | `.col.box` | label `Selected asset — DDG 113 · UIC 21487`; three chips `Class DDG 51 Flt IIA` · `Domain: surface` · `OFRP: Sustainment` (`good`); note *"Hull rendered with a space, never a hyphen — SECNAVINST 5030.8D. (doc 07 §3.5)"* |
| 3 | `.col.box` | label `System / position / installed-item tree`; a `.tree` — `233 — Propulsion` [tag `ESWBS, HSC-variant per HSCI`] → `Position 233-04-A` [tag `outlives items`] → `Installed item: Feed pump #A19381` [tag `IUID`]; and `300 — Electrical` → `Position 300-11-B` |
| 4 | `.col.box` | label `Configuration baseline`; chips `as_of: 2026-08-01` · `as_known_at: today`; note *"Bitemporal toggle … Baseline epoch: **17**."*; chip `Allowance docs: COSAL · APL · AEL` |

Components [50 §3.5]: `SheetFrame`, `Box`, `WfTable`, `StatusChip`, `ChipRow`, `ConfigTree`, `TreeNode`, `TreeTag`, `BitemporalToggle`, `EpochBadge`. `TitleBlock`: `SHEET 02 / ASSET & CONFIGURATION REGISTRY`, `Asset Browser`, persona *"Maintainer, Planner, Vehicle Readiness Officer — entry point to a specific hull"*.

### 9.2 Data wiring

| # | Query | Operation | Setting | Feeds |
|---|---|---|---|---|
| 1 | `keys.passthrough("registry","/assets")` | `GET /api/v1/registry/assets` [20 §6.1 row 1] | **A** | Box 1 |
| 2 | `keys.views.asset(assetId)` | `GET /api/v1/gateway/views/asset/{asset_id}` [30 §3.2] | **A** | Boxes 2 and 4 |
| 3 | `keys.pinned("registry","/assets/{id}/configuration",{as_of,as_known_at})` | `GET /api/v1/registry/assets/{asset_id}/configuration?as_of=&as_known_at=&system_id=&limit=&cursor=` [20 §6.1 row 3, §6.3] | **C** | Box 3's positions and installed items |
| 4 | `keys.passthrough("registry","/assets/{id}/systems")` | `GET /api/v1/registry/assets/{asset_id}/systems` [20 §6.1 row 4] | **A** | Box 3's system hierarchy and `hsci` echo |
| 5 | `keys.passthrough("registry","/assets/{id}/current-baseline-epoch")` | `GET /api/v1/registry/assets/{asset_id}/current-baseline-epoch` [20 §6.1 row 15] | **A** | `EpochBadge` |
| 6 | `keys.passthrough("registry","/assets/{id}/allowances")` | `GET /api/v1/registry/assets/{asset_id}/allowances` [20 §6.1 row 11] | **A** | Box 4's allowance chip |

**Box 1 has no filter, and that is §4.4's gap again.** `GET /assets` declares **no query parameter anywhere in [20](20-registry.md)** — not `domain=`, not `class_id=`, not `changed_since=`. With twelve assets [06 §7] the unfiltered list is the whole fleet and the box is a complete selector, so the sheet works; **but a client-side text filter over it is deliberately not added**, because it would make the box look like the search affordance §4.4 had to withdraw and would stop working the moment the fleet is not twelve. `WfTable` renders `hull_or_tail` and `domain`, sorted by `hull_or_tail`, with `aria-sort` on the sorted header and the sort control as a `<button>` inside the `<th>` [50 §3.3 gap 1] — **client-side sorting is permitted here precisely because the page is fully materialized**. §22 row 4.

**Box 2's chips.** `data.asset` → `class_id` (+ label from `GET /classes/{class_id}`), `domain`, `ofrp_phase`. `ofrp_phase` renders `tone="neutral"` for §8.4's reason. **[20 §4.3] references *"a fuller `AssetDetail` response (§6.2)"* and [20 §6.2] defines no such schema** — it defines `ConfigurationLine`, `AssetConfiguration`, and `BaselineEpochState` only. The chips are therefore wired to the `assets` table's own column names, which is what the generated type will expose. §22 row 41.

### 9.3 `ConfigTree` — three levels from two operations

The drawn tree is **system → position → installed item**. No single operation returns it; two do, and the composition is within one domain and therefore not a prohibited derivation [50 §5.3 rule 6].

| Level | Source | Fields |
|---|---|---|
| System | Query 4, `GET /assets/{id}/systems` → `SystemNode` [20 §4.3] | `system_id`, `parent_system_id`, `hsc_code`, `hsc_path`, `depth`, `label`, `eswbs`, `eic`. It is *"an **adjacency list plus materialized path**, traversed by a PostgreSQL recursive CTE"* — so `hsc_path` and `depth` give the tree its shape without the client inferring one |
| Position | Query 3, `AssetConfiguration.lines[]` → `ConfigurationLine` [20 §6.2] | `position_id`, `position_code`, `system_id`, `eswbs`, `hsc_code`, `system_eic` |
| Installed item | Same `ConfigurationLine` | `installed_item_id`, `niin`, `iuid`, `serial_or_lot`, `installed_at`, `provisional`, `identity_resolution`, `conforms_to_template`, `deviation_id`, `item_eic` |

Grouping `lines[]` by `system_id` and nesting under query 4's hierarchy is presentation over one service's rows, not a cross-domain join.

**`ConfigurationLine.installed_item_id` is nullable on the wire**, because [20 §9.3] makes the underlying join a **LEFT** join: a vacant position is a real row with no item. `[ESTABLISHED HERE]`: a vacant position renders as a leaf `TreeNode` reading `Position <code> — vacant`, with `aria-expanded` **absent** (not `false` — the ARIA tree pattern reserves `false` for a collapsed node that has children [50 §3.3 gap 2]). **Never an empty child list**, which would announce as an expandable node with nothing in it.

**`TreeTag` renders real fields, not WF's annotations.** WF's tags (`ESWBS, HSC-variant per HSCI`, `outlives items`, `IUID`) are drawing rationale in the `--annotation` voice, and [50 §2.2] confines that voice to §7's disclosure content. The production tags:

| Node | `TreeTag` content |
|---|---|
| System | `eswbs` where `scheme_family = 'eswbs'`, else `hsc_code`; plus `eic` where present |
| Position | `position_code`. **No `outlives items` tag** — it is a design fact, and [20 §4.4] states it structurally: *"**THERE IS NO `installed_item_id` COLUMN ON THIS TABLE, AND THERE NEVER WILL BE**"* |
| Installed item | `iuid` where present, else `serial_or_lot`, else `niin`. Plus a `StatusChip tone="warning"` reading `provisional` where `provisional` is `true`, and `identity_resolution` (`confirmed \| superseded \| rejected`) where it is not `confirmed` |

**`provisional` and `identity_resolution` are rendered, not hidden.** [20 §4.5.1] mints provisional identities afloat, and an item whose `identity_resolution` is `superseded` has a `canonical_installed_item_id` pointing elsewhere — an operator acting on the superseded id would act on the wrong record. `[ESTABLISHED HERE]`, and a superseded node renders a link to its canonical node.

`ConfigTree` implements the full ARIA `tree` pattern [50 §3.3 gap 2]: `role="tree"`, `role="treeitem"` with `aria-expanded` and `aria-level`, `role="group"` on child lists, roving `tabindex`, Up/Down/Left/Right/Home/End. **Typeahead is not implemented** — [50 UI-OQ-6] left it open and no sheet requires it; §23 carries it forward with one new data point: a hull's configuration is bounded by `MAX_LIMIT = 500` per page [20 §6.4], so the tree paginates rather than materializing [06 §7]'s ~8,400-item fleet-wide configuration, and arrow-key navigation over one page of 500 is unpleasant but not impractical.

### 9.4 `BitemporalToggle` — and it is not a toggle

WF draws two chips, `as_of: 2026-08-01` and `as_known_at: today`, with the note *"Bitemporal toggle — 'what was installed' vs. 'what we believed was installed' (doc 03 §4)."* [50 §3.2] maps it to Radix `ToggleGroup type="single"` — *"[t]wo exclusive options."*

**They are not exclusive options; they are two independent instants**, and [20 §6.3](20-registry.md) is explicit about it in six numbered rules: both are optional, both default to *"a **single** request instant,"* **and *"[t]he two are never compared."*** `as_of` is valid time (*"what was installed at this instant"*); `as_known_at` is record time (*"as Registry believed it at this instant"*). Setting one does not unset the other. A single-select toggle cannot express `(2026-08-01, today)`, which is WF's own drawn state.

**Corrected, `[ESTABLISHED HERE]`, §22 row 42:** `BitemporalToggle` renders **two independent controls**, each a `ToggleGroup type="single"` with two options — `now` and `explicit` — plus a datetime input revealed when `explicit` is chosen. That keeps [50 §3.2]'s primitive (a `ToggleGroup` is still the control; there are two of them) and does not invent a component. Both values live in the URL as `as_of` and `as_known_at`, parameter names verbatim [50 §4.4], which is what makes a historical configuration linkable.

Four rules from [20 §6.3], all enforced client-side **before** the request so the operator gets an immediate answer rather than a 422:

1. **A naive datetime is rejected** — the input always produces an explicit offset [20 §6.3: `RegistryProblem.NAIVE_TIMESTAMP`].
2. **A future `as_known_at` is refused, and is not clamped** — [20 §6.3] returns **422**, *"not a clamp"* (`AS_KNOWN_AT_IN_FUTURE`). The control disables future record-time selection and states why. Clamping silently would answer a different question than the one asked.
3. **A future `as_of` is allowed** [20 §6.3] — a planned configuration is a legitimate query.
4. **`OAS-REG-1`'s spirit binds the client**: [20 §6.3] fails the build if an operation accepts `as_of` without `as_known_at`. The console never sends one without the other; `ui-bitemporal-pairs` (§19.1).

**Both explicit ⇒ the read is immutable**, which is why query 3 is a `pinned` key at setting **C** (§3.3, §3.4). When either control is `now`, the key falls back to `passthrough` at setting **A**. `ui-pinned-queries-never-poll` (§19.1) is what keeps that distinction from decaying.

The accepted-on list matters and is transcribed: `as_of`/`as_known_at` are accepted on operations **3, 4, 5, 6, 11, 16, 20, 22, 23** [20 §6.3]. The console sends them on queries 3, 4, and 6 and **not** on query 5 (`current-baseline-epoch`), which is a current-state singleton.

### 9.5 `EpochBadge`

WF draws `Baseline epoch: **17**` inside a `--annotation`-voice note. In production it is a first-class badge, because an epoch is the fence every write in the system is validated against [03 §5.4, D3/D4].

Source: query 5, `BaselineEpochState` [20 §6.2] → `asset_id`, `current_epoch`, `current_baseline_id`, `allocated_high_water`, `recorded_from`. [20 §5.7] states the rule: *"`current_epoch` and `allocated_high_water` returned separately and both; `allocated_high_water > current_epoch` means a change is in flight."*

`[ESTABLISHED HERE]`, `EpochBadge` renders three states:

| Condition | Rendering |
|---|---|
| `allocated_high_water === current_epoch` | `StatusChip tone="neutral"` reading `baseline epoch 17` |
| `allocated_high_water > current_epoch` | `StatusChip tone="warning"` reading `baseline epoch 17 · change in flight (18 allocated)`. **This is the one fact an operator needs before believing a configuration tree**, and WF's static `17` cannot express it |
| Query 5 failed | `StatusChip tone="neutral"` reading `baseline epoch unknown`. **Never the epoch from `AssetConfiguration.baseline_epoch`** — that is the epoch of the *returned configuration*, not the asset's current one, and substituting it would silently claim the view is current |

`AssetConfiguration` additionally carries **`epoch_is_current`** [20 §6.2, §5.7: *"Every configuration response carries `baseline_epoch`, `baseline_id`, and `epoch_is_current: bool`"*]. When it is `false`, box 3 renders a `SheetNote` stating the tree is a historical baseline and naming its epoch. `ui-epoch-not-current-disclosed` (§19.1).

**Allowance chip.** Query 6 → `allowance_document` [20 §6.1 row 11]. WF's `Allowance docs: COSAL · APL · AEL` renders one `StatusChip tone="neutral"` per document actually returned, with its own type. **A hull with no allowance documents renders no chip and an `EmptyState`** in box 4, not the drawn three-name string — which would assert three documents exist.

### 9.6 Sheet 02 states

| Condition | Rendering |
|---|---|
| No `:assetId` (route `/registry`) | Box 1 renders the list; boxes 2, 3, 4 render `EmptyState` reading *"Select an asset."* **Not skeletons** — nothing is loading |
| Query 1 loading | Box 1 `LoadingSkeleton` |
| Query 1 empty | `EmptyState` naming the scope. A registry with no assets is a legitimate fresh-deployment state |
| `asset` fragment not `ok` | `503` for the view (required) → `ProblemDetail` for boxes 2 and 4; **box 1 still renders** from query 1, so the operator can pick a different hull |
| Query 3 `403` | `ProblemDetail` in box 3 with the owner's problem body verbatim [30 §8.4]. **Not an empty tree** |
| Query 3 `422` (bitemporal) | Rendered at the control, naming which of the two rules was violated (§9.4) |
| A vacant position | A leaf node reading `vacant`, `aria-expanded` absent (§9.3) |
| `epoch_is_current: false` | Box 3's historical-baseline `SheetNote` (§9.5) |

---

## 10. Sheet 03 — Channel & Health View

**Route:** `/telemetry/installed-items/:installedItemId`. **Component:** `ChannelHealthView` in `src/features/telemetry/`. There is no index route [50 §4.2]; `/telemetry` redirects to `/registry`.

### 10.1 What the wireframe draws

| # | WF element | Content as drawn |
|---|---|---|
| 1 | `.sheet-note` | *"Domain note: submarine channels arrive burst-on-reconnect (gaps expected); unmanned channels exist only within sortie windows. **Completeness is shown, not hidden.**"* |
| 2 | `.box` + `.table-scroll` | label `Channels — Feed pump #A19381`; columns `Health indicator` · `Current` (num) · `Trend` · `Completeness`. Row 1: `Bearing vibration RMS` · `3.4 mm/s` · an `svg.spark` · `[chip good] 98%`. Row 2: `Lube-oil temperature` · `61°C` · **a `.hatch` block** · `[chip warning] 71%` |
| 3 | `.box` | label `Recent missions`; columns `Mission` · `Type` · `Period` · `Completeness`. Rows: `Patrol 26-3` · `underway` · `14d` · `100%`; `Sortie 0442` · `UUV sortie` · `6h` · `100%` |

Components [50 §3.5]: `SheetFrame`, `SheetNote`, `Box`, `WfTable`, `WfTableScroll`, `Sparkline`, `HatchFill`, `StatusChip`.

### 10.2 Data wiring

| # | Query | Operation | Setting | Feeds |
|---|---|---|---|---|
| 1 | `keys.views.installedItem(id)` | `GET /api/v1/gateway/views/installed-item/{installed_item_id}` [30 §3.2] | **A** | The box labels; the indicator roster |
| 2 | `keys.pinned("telemetry","/health-indicators",{installed_item_id,from,to,as_of,as_known_at})` | `GET /api/v1/telemetry/health-indicators?installed_item_id=&from=&to=&as_of=&as_known_at=` [21 §9.1, §5.8] | **C** | `Current`, `Trend`, `Completeness` |
| 3 | `keys.passthrough("telemetry","/missions",{asset_id,from,to})` | `GET /api/v1/telemetry/missions?asset_id=&from=&to=` [21 §9.1] | **A** | Box 3 |
| 4 | `keys.passthrough("telemetry","/installed-items/{id}/channels")` | `GET /api/v1/telemetry/installed-items/{id}/channels` [21 §9.1] | **A** | §10.5's attribution disclosure |

`installed_item_detail`'s six fragments [30 §3.2]: `installed_item` (registry, **required**), `prediction` (pdm), `health_indicators` (telemetry), `usage_counters` (telemetry), `maintenance_history` (maintenance), `failure_modes` (failure-intel). **Only `installed_item` and `health_indicators` feed this sheet**; the other four feed sheet 04's deep dive (§11) and are not rendered here [50 §11.2 item 12].

**Query 2 exists because [21 §5.8](21-telemetry.md) requires two parameters the composed view cannot supply.** `GET /health-indicators` takes `as_of` **and** `as_known_at`, both *"required with no default"* [21 §5.1, extended to `/health-indicators` by §5.8] — and [30 §3.2] declares no query parameters on any view. The console must therefore choose both instants, and the choice is a decision:

`[ESTABLISHED HERE]`: **the console sends `as_of=latest&as_known_at=latest`** by default, using the explicit `latest` literal [21 §5.1 DECISION], and the `Trend` window is `from`/`to` over the drawn horizon. When `as_known_at=latest` the response carries **`definition_time_unconstrained: true`** and the header **`X-Feature-Definition-Time: unconstrained`** [21 §5.1]. **Both are rendered**: the box gets a `SheetNote` stating that indicator definitions are unpinned, because [D22]'s whole concern is a value computed under a definition authored with hindsight, and a screen that silently uses `latest` hides which definition produced the number. A `BitemporalToggle` (§9.4's two-control form) is offered on this box as well, so an operator can pin both instants — at which point the query becomes a true `pinned` key at setting **C**.

### 10.3 The four columns

| WF column | Field | Notes |
|---|---|---|
| `Health indicator` | `indicator_key` + `definition_version` [21 §3.4.2] | The **version renders**, as a `StatusChip tone="neutral"`. Two values of the same `indicator_key` under different definitions are not the same series |
| `Current` (num) | `value` + **`unit_code`** [21 §3.4.2] | `unit_code` *"resolves against Reference Data, never free text"* [21 §3.1.1] and is rendered from `refdata(…)` at setting **C**. `tabular-nums` mandatory [50 §2.3]. **A value with no resolvable unit renders the code verbatim**, never a bare number |
| `Trend` | `Sparkline` over the window — §10.4 | |
| `Completeness` | `completeness`, `sample_count`, `expected_sample_count` [21 §3.4.2] | §10.5 |

Every row additionally renders `quality_flags` [21 §3.4.2] as `StatusChip`s from the vocabulary `ABSENT | CLIPPED | STUCK | IMPLAUSIBLE | IMPUTED | DUPLICATE | IMPULSE | TIMEBASE` [21 §5.3], plus `missing_policy_applied` and `outlier_policy_applied`. `[ESTABLISHED HERE]`, and it is not an added UI element in the sense [50 §11.2 item 12] forbids — it is the `Completeness` column rendering the fields that make completeness interpretable, in the column WF drew for it. A `98%` completeness whose `STUCK` flag is set is a transducer holding a value, and [21 §3.8] names the operator's actual question: *"which channels on this hull are lying to me."*

### 10.4 The sparkline, and the hatch block that is not a placeholder

**`Sparkline` is [50 §3.3 gap 4]'s hand-built component** — inline SVG, a `<polyline>`, an area `<path>`, and an end `<circle>`, transcribed from `WF svg.spark`, `--bw-spark: 1.6px`, `--accent` line, `opacity: .08` area wash [50 §2.5, §2.7 item 4]. **No charting library** [50 §3.3 gap 4].

Its data is `value` over `window_end` from query 2's series. **[21](21-telemetry.md) publishes no downsampled or aggregate series read** — the word *sparkline* appears nowhere in it, and there is no summary operation — so the polyline is built from the returned rows directly. That is safe at this scale because the window is bounded by `from`/`to` and cursor-paginated, and `[ESTABLISHED HERE]` **the console renders only the first page and states the window it drew**, rather than paginating to exhaustion for a 90 × 26 px figure. §22 row 43 notes the absent summary read.

`aria-hidden="true"` with the required `redundant: true` prop [50 §8.5] — legitimate here **and only here**, because `Current` and `Completeness` are in adjacent `<td>`s of the same row, which is exactly the condition [50 §8.5] attaches to it.

**WF row 2's `.hatch` block in the `Trend` cell is a defect.** [50 §2.5] fixes `--hatch` to mean *"a figure belongs here and is **not rendered**"* and [50 §11.1 item 6] forbids it as a loading state. Row 2 is not a missing figure; it is a series with `71%` completeness — **too sparse to trend, not absent**. Rendering it hatched makes an insufficient-data condition indistinguishable from an unimplemented chart. `[ESTABLISHED HERE]`, §22 row 44:

| Condition | `Trend` cell renders |
|---|---|
| Enough points to draw, and `completeness >= min_completeness` [21 §3.4.1] | `Sparkline` |
| `completeness < min_completeness` | **`EmptyState`, inline and compact**: `insufficient completeness to trend`. Not a hatch, not a spinner, not a flat line — a flat line asserts a stable value |
| Zero points in the window | `EmptyState`: `no values in window`. **And `completeness = 0` is never rendered as "not observed"** — [21 §12.2 DO-NOT 21] forbids treating them as equivalent |
| Query 2 not resolved | `LoadingSkeleton` at 90 × 26 px |
| Query 2 failed | `DegradedFragmentNotice` / `ProblemDetail`, inline |

`min_completeness` is a field on `indicator_definition` [21 §3.4.1] and is **read, never assumed** — the same discipline [50 §7.5] applies to the contributing-factor stability floor. [21 OQ-8] concerns that field and is carried forward as §23.

### 10.5 Completeness, gaps, and the scalar that is not allowed to stand alone

`Completeness` renders `completeness` as a `StatusChip` — **and the tone is a `[GAP]` of the §6.8 family**: WF draws `98%` `good` and `71%` `warning`, and no document bands completeness. **The only banding that exists is `min_completeness` per definition** [21 §3.4.1], which is a *sufficiency* threshold, not a three-tone scale. `[ESTABLISHED HERE]`: two tones, both field-derived — `good` where `completeness >= min_completeness`, `warning` where it is below. That is a real distinction the operator can act on, and it needs no invented threshold. §22 row 45.

**A completeness scalar may not stand alone**, and [21 §3.6] says so directly: `gap_intervals` are *"`[{from,to,cause}]` — **enumerated, never summarized**."* So:

- Each channel row is expandable — `Collapsible` [50 §3.2's available primitives] — to a `WfTable` of `data_time_gaps[] { from, to, cause, observation_state }` [21 §5.3] and `coverage.missing_indicators[] { indicator_key, reason }` with `reason` from `not_defined_at_as_known_at | no_data | no_value_within_fences | insufficient_completeness`.
- **`mnar_indicator`** [21 §5.3, §3.8] renders as a `StatusChip tone="warning"` where set. Missing-not-at-random is the fact that makes a completeness figure misleading rather than merely incomplete, and it is exactly what WF's own sheet-note is about: *"submarine channels arrive burst-on-reconnect (gaps expected)."*
- **`observation_state`** (`observed | partially_observed | not_observed` [21 §3.6]) renders as its own chip on the mission rows (§10.6).
- **`attribution_weight`** [21 §3.1.4], from query 4, renders where a channel is `sharing: shared`: it is *"NULL where genuinely unresolvable; never defaulted to 1."* A shared channel whose attribution to this item is unresolvable renders `attribution unresolved` and **the value is still shown** — with the disclosure, because the reading is real and only its allocation is uncertain.

**No "last sample time" is rendered, because no such field exists.** [21](21-telemetry.md) has no `last_sample`, `last_seen`, or `latest_sample` under any name. The available currency facts are `window_end` on the latest value [21 §3.4.2] and `mission_record.ended_at` [21 §3.6], and the console renders `window_end` labelled as *"latest window ends"* — never as *"last seen."* §22 row 46.

### 10.6 The missions box

| WF column | Field [21 §3.6] | Notes |
|---|---|---|
| `Mission` | `mission_id` | Rendered with its identifier; no name field exists |
| `Type` | `mission_type` — `underway_period \| patrol \| sortie` | WF draws `underway` and `UUV sortie`; the enum values render verbatim. WF's `UUV sortie` conflates the type with the platform — `sortie` is the type and the platform is the asset's `domain`. §22 row 47 |
| `Period` | `started_at` → `ended_at` | Rendered as both instants **in the operator's local zone with the zone named** [50 §12.1], plus the elapsed duration. WF's bare `14d` drops the boundary, and `boundary_source` (`reported \| inferred \| reconciled`) renders beside it — an *inferred* mission boundary is a computed guess and a 14-day period built on one is not the same claim as a reported one |
| `Completeness` | `completeness`, plus `observation_state`, plus `expected_channel_set`/`observed_channel_set` counts | §10.5's two-tone rule. `100%` with `observation_state: partially_observed` is possible and both render |
| *(added)* | `gap_intervals` | Expandable, enumerated [21 §3.6] |

Box 3's query needs an `asset_id`, which this route does not carry. It comes from `data.installed_item` (the required fragment) [30 §3.2] — a within-envelope read, not a second lookup.

---

## 11. Sheet 04 — Fleet-Risk Triage

**Routes:** `/pdm` and `/pdm/installed-items/:installedItemId`. **Component:** `FleetRiskTriage` in `src/features/pdm/`.

### 11.1 What the wireframe draws

| # | WF element | Content as drawn |
|---|---|---|
| 1 | `.box` + `.table-scroll` | label `Triage — ranked by expected consequence`; columns `NIIN` · `Installed item` · `Tier` · `Reference class` · `P(failure) / rate` · `Horizon` · `Top factor`. Three rows, the third with `[chip neutral] uncalibrated / pop. hazard only` and `Top factor` `—` |
| 2 | `.sheet-note` (`--annotation`) | *"A null `p_failure` (calibration population < 50) renders as 'uncalibrated,' never as zero risk — doc 03 §7.1."* |
| 3 | `.col.box` | label `Item deep-dive — SSDG No. 2`; `.placeholder-fig` *"RUL distribution — p10 / p50 / p90 range bar, unit: engine operating hours"*; then a `WfTable` `Contributing factor` · `Stability` (num) |
| 4 | `.col.box` | label `What-if scenario` + `[chip accent] tier-3 · interactive`; `.placeholder-fig` *"adjust usage / deferral inputs → recomputed RUL (Domino Endpoint)"* |

Components [50 §3.5]: `SheetFrame`, `Box`, `WfTable`, `WfTableScroll`, `StatusChip`, `UncalibratedCell`, `FigurePlaceholder`, `SheetNote`, and `ContributingFactorRow` [50 §7.5].

### 11.2 The drawn ranking cannot be obtained, and the console does not fake it

WF box 1's label is `Triage — ranked by expected consequence`. Three facts make that unobtainable as drawn:

1. **`GET /predictions` has no sort parameter.** [22 §10](22-pdm.md) declares `GET /predictions?asset_id=&installed_item_id=&niin=&equipment_family=&min_probability=&horizon_days=&reference_class=&status=&changed_since=&cursor=&limit=` — **no `sort`, no `order_by`** anywhere in the document.
2. **Expected consequence is not a field on a prediction.** It is the output of `POST /api/v1/pdm/expected-consequence` [22 §10, §7.2], which *"[a]ccepts predictions + consequence weights + operating fraction + posture"* — signature `expected_consequence(pred, *, consequence: ConsequenceWeights, operating_fraction: float, risk_posture: RiskPosture)`. **The console has no source for `ConsequenceWeights` or `RiskPosture`**; no operation publishes them, and [24 §4.4] flags optimizer dispositions with **`weights_are_illustrative`** for the same reason.
3. **The fleet triage agent that would do this ranking is not built.** [22 §10.1] describes the `pdm-fleet-triage` manifest as *"Fleet-wide ranked triage, named in 03 §8.2, **not detailed here** — this agent is not built in this wave … (Phase 3, when the Work-Package Planner is in scope)."*

**Resolution, `[ESTABLISHED HERE]`, §22 row 10.** The box's label becomes **`Triage — active predictions`** and the table is sorted by a **field the response carries**, with the sort control declaring which: `horizon_days` ascending as the default (soonest horizon first, which is an act-before-this ordering in the same spirit as [30 §4.4]'s `expiry` default), and `p_failure` descending and `computed_at` descending as alternatives. All three are **client-side over the fetched page** [50 §3.3 gap 1] and the `<caption>` states the page bound, because a client-side sort over a paginated collection is a sort of the page and must not be presented as a fleet ranking.

**Three things the console does not do**, each of which would be the tempting fix:

- **It does not call `POST /expected-consequence` with invented weights.** A ranking produced from weights a UI engineer chose is a priority claim the program did not make, and [30 §2.4] records that a composed priority score is *"[n]ot computed anywhere"* — [50 §11.3 item 20] forbids relocating that derivation into the browser.
- **It does not sort by `confidence`.** [22 §2.5] and [03 §7.1] make `confidence` *"sharpness-and-fit confidence only"*, separate from `fallback_level` by construction, because *"[o]ne scalar cannot carry both sharpness and epistemic reference-class depth and remain orderable"* [D7].
- **It does not compare `p_failure` across reference classes.** [03 §7.1]: *"[a] tier-0 population rate and a tier-3 item-conditional probability can each be perfectly calibrated and remain incomparable. Consumers do not compare `p_failure` across reference classes."* The `p_failure` sort therefore **groups by `reference_class` first** and sorts within each group, with the group boundary visible as a `<tbody>` per class and a row-group header naming it. `ui-no-cross-reference-class-sort` (§19.1).

**And one mandatory negative wiring rule.** [22 §10] documents it on the operation itself: `min_probability` *"filters on `p_failure` and therefore **excludes** below-gate predictions when set — documented on the operation, because a caller filtering on probability silently drops the uncalibrated population otherwise."* **The console never sends `min_probability`**, and offers no control that would. `ui-never-sends-min-probability` (§19.1). Dropping the uncalibrated population from a triage view is dropping precisely the items nobody has enough data about, which is the opposite of triage.

### 11.3 The seven columns

| WF column | Field | Rendering |
|---|---|---|
| `NIIN` | `niin` [22 §2.5] | Linked to `/supply/parts/{niin}`. Pattern `^([0-9]{9}\|[A-Z]{2}[A-Z0-9]{7})$`, canonical `Niin` [10-shared-packages.md §4.1] — **not** [26 §13 row 1]'s broader proposed form |
| `Installed item` | `installed_item_id` [22 §2.5] | Linked to `/telemetry/installed-items/{id}`. Nomenclature is §6.5's `[GAP]` |
| `Tier` | `tier` [22 §2.5] | **Displayed, never branched on.** [03 §7.1]: `tier` is *"0..3, transparency only"* and *"consumers must not branch on `tier`. They may, and must, branch on `reference_class`."* `ui-no-tier-branch` / `FTH006` [50 §10.2, §11.4 item 38]. Rendered as a plain numeral with **no tone** |
| `Reference class` | `reference_class` — `item \| niin_fleet \| equipment_family \| class_estimate` [22 §2.5] | `StatusChip tone="neutral"`, value verbatim. **This is the branch column**, and it governs both the `P(failure)` cell and whether `rul` exists at all |
| `P(failure) / rate` | `p_failure`, or `population_hazard_rate` | §11.4 |
| `Horizon` | `horizon_days` [22 §2.5] | With its unit; the default sort key (§11.2) |
| `Top factor` | `contributing_factors[0]` | §11.5. WF's `—` on the uncalibrated row is correct: [22 §9.3] emits *"[t]ier 0 … an empty tuple always"* |

Additional fields rendered because they change what the row means, `[ESTABLISHED HERE]` and all within the drawn columns:

- **`fallback_level`** (0–4) [22 §2.5] as a chip where > 0. [03 §7.1] separates it from `confidence` deliberately; a level-4 cold-start prediction beside a level-0 one in the same table, undifferentiated, is the comparability defect the field exists to prevent.
- **`calibration_population`** in the `P(failure)` cell's disclosure — [22 §2.5] notes it is *"the small number, published rather than nulled."*
- **`model_version` and `computed_at`** in the row's expandable detail. `computed_at` is the row's currency and is not the sheet's `as_of`.
- **`status`** is **not** rendered and **not** requested as anything but `active`: `invalidated` and `superseded` predictions [22 §2.5] are not triage rows, and the console sends `status=active`.
- **`serving_class` is never rendered and `research_only` never reaches this screen.** [22 §4.5.2] puts research predictions behind `GET /research/predictions`, `internal`, not agent-eligible, gated on the `research_analyst` ABAC role and the header `X-Fathom-Prediction-Use: research-only`, with `GET /predictions/{id}` returning **404 `urn:fathom:problem:pdm:prediction-not-actionable`** for one. The console calls only the actionable surface. `ui-no-research-predictions` (§19.1).

### 11.4 `UncalibratedCell` — the one cell whose wrongness is silent

[03 §7.1](../architecture/03-integration-contracts.md): `p_failure` is *"NULL when `calibration_population < 50` … A predicted probability that cannot be calibrated must not be emitted merely because the field exists; omission is the honest signal,"* and *"[a] consumer that treats a missing `p_failure` as zero, rather than as 'uncalibrated,' reintroduces the comparability defect this field exists to prevent."* [22 §6.3] makes all four consequences DB-enforced below the gate: `p_failure` **NULL**, `reference_class` forced to **`class_estimate`**, `population_hazard_rate` **required**, `rul` NULL with `fallback_level ≥ 3`.

**There is no field named `uncalibrated` on a prediction.** [22](22-pdm.md) uses the token twice, both times quoting the consumer obligation, never as a field or enum value. The machine-readable signal is the conjunction: `p_failure === null` **and** `reference_class === "class_estimate"`. `[ESTABLISHED HERE]`, `UncalibratedCell` branches on exactly that and on nothing else:

| Condition | Cell renders |
|---|---|
| `p_failure` present | The probability, `tabular-nums`, with `reference_class` beside it and `sharpness` in the disclosure. **No tone** (§6.8) |
| `p_failure === null`, `population_hazard_rate` present | `StatusChip tone="neutral"` reading **`uncalibrated`**, with a second line `pop. hazard <rate>` and `calibration_population n=<n>`. WF's own two-line chip, wired. **Never `0`, never `0.00`, never `—` alone, never an empty cell** — `ui-uncalibrated-never-zero` [50 §10.2] |
| `p_failure === null`, `population_hazard_rate` absent | `StatusChip tone="neutral"` reading `no rate available`. This is [22 §7.3]'s Case C, which *"raises `UncalibratedAndUnrated` only if `p_failure` and `population_hazard_rate` are both absent"* and *"**never treats a null `p_failure` as zero**"* |

**The sheet-note (WF element 2) renders verbatim as a `SheetNote`**, in the `--annotation` voice — it is one of the two production uses [50 §2.2] permits that voice for: the system stating a limit of its own output.

**The gate is not the console's to restate as a number.** WF's note says *"calibration population < 50"*, and 50 is [06 §3]'s figure via [22 §6.2]. The note renders WF's wording because it is approved copy, and the console **does not implement the comparison** — it reads `p_failure === null`, which is where the gate already landed. A client-side `n < 50` check would be a second gate that could disagree with the server's.

### 11.5 The deep dive, the contributing factors, and the stability floor's real source

**Box 3's `FigurePlaceholder` stays a placeholder** [50 §3.3 gap 4], `<figcaption>` carrying WF's text verbatim [50 §8.5]. The `rul` object it describes — `{p10, p50, p90, unit}` with unit from `days | steaming_hours | eoh | cycles | sorties | dives` [03 §7.1] — is instead rendered as a three-row `WfTable` beneath the caption, `[ESTABLISHED HERE]`, because a range bar needs a chart library and three labelled numbers with a unit need nothing.

**`rul` is `null` wherever `reference_class` is not item-conditional** [03 §7.1, 22 §2.5's `rul_only_when_item_conditional` constraint], *"because a memoryless population fit cannot produce a per-item residual-life distribution, and rendering one indistinguishably from a tier-3 distribution misleads the operator [D19]."* The box therefore renders `EmptyState` reading `no residual-life distribution at reference class <class>` — **naming the reason**, never an empty range or a zero.

**`ContributingFactorRow`** [50 §7.5], from `contributing_factors[]` [03 §7.1]: `factor`, `contribution`, `attribution_method` (**required**), `stability`, `observation_ref`.

| Rule | Basis |
|---|---|
| Rendered as **association, never cause** | [09 §9.3 item 20] / D23: *"**Do not render `contributing_factors` in causal language** … A causal statement must cite an adjudicated Failure Intelligence hypothesis."* No verb in any label implies causation; the column header is WF's own `Contributing factor`. `ui-factors-not-causal` [50 §10.2] |
| `attribution_method` **always rendered** | [03 §7.1] makes it required. Vocabulary [22 §9.1]: `weibull_covariate_coefficient`, `aft_time_ratio`, `cox_partial_effect`, `degradation_channel_contribution`, `shap_treeexplainer`, `shap_kernel`, `permutation_importance`, `physics_residual_decomposition`, `rule_trigger`. **`fallback_reason` is deliberately not in it** and must never appear as one |
| `observation_ref` is a link | [22 §9.4]'s form `fathom://telemetry/health-indicator/{indicator_id}?installed_item_id=&data_time=&definition_time=&definition_version=` resolves to `/telemetry/installed-items/{id}` with the two instants as the `pinned` query's `as_of`/`as_known_at` (§10.2). **This is the point-in-time provenance chain [03 §7.1] built the field for**, and it is what makes [09 §8.4]'s *"sufficient to trace any operator-visible figure to its sources"* true from the browser |
| The stability floor is a **required prop with a real source** | [50 §7.5] specified the prop and said *"[t]he console does not invent the threshold; it refuses to render without one"* — and left the source open. **[22 §9.3] is the source**: suppression happens at emission with a threshold of `stability >= 0.6` [P-20], at most **5** factors are emitted [P-21], and *"[t]he applied threshold [is] published on **`GET /pdm/attribution-policy`**"* [22 §10, a singleton in `x-naming-carve-outs`]. The console reads it — `keys.passthrough("pdm","/attribution-policy")`, setting **C** — and passes it. **Until it resolves, the table does not render**; it shows a `LoadingSkeleton`, then `ProblemDetail` if the policy is unobtainable. This closes a [50 §7.5] gap rather than correcting it (§22 row 48 records the closure so [50](50-ui-design-system.md) can cite it) |
| `suppressed_factor_count` is **disclosed** | [22 §2.6]'s provenance block carries `suppressed_factor_count` and `suppressed_factors`, from `GET /predictions/{id}/provenance` [22 §10]. The box renders *"n factors below the stability floor are not shown"* — because a table of two factors that is silently a table of two out of nine is a completeness claim it should not make. `[ESTABLISHED HERE]` |
| `stability` is rendered, uncoloured | §6.8. WF draws `0.86` and `0.52` — and **`0.52` is below [22 §9.3]'s 0.6 floor and should not have been emitted at all.** §22 row 49 notes the wireframe's illustrative value is inconsistent with the policy |

Deep-dive data: on `/pdm/installed-items/:installedItemId`, the box is fed by `keys.views.installedItem(id)` [30 §3.2]'s `prediction` fragment and by `keys.passthrough("pdm","/predictions/{id}/provenance")` at setting **C** — a provenance record for one prediction id does not change. `views.explanation(predictionId)` [30 §3.2] is the fuller decomposition and is fetched **on demand**, when the operator opens the factor's provenance, because it carries a 4000 ms budget [30 §3.2, 06 §7] and prefetching it on every row selection would burn that budget for nothing [50 §5.4].

### 11.6 The what-if surface, and the operation [50 UI-OQ-9] named wrongly

WF box 4: `What-if scenario` with `[chip accent] tier-3 · interactive` and a placeholder for *"adjust usage / deferral inputs → recomputed RUL (Domino Endpoint)."*

**[50 UI-OQ-9](50-ui-design-system.md) states the call is `POST /api/v1/gateway/inference/{domino_endpoint_name}` [30 §5.6]. It is not.** [22 §10](22-pdm.md) declares **`POST /api/v1/pdm/what-if`**, `x-substitution: required`, `x-side-effects: none`, **agent-eligible**, held in its own manifest `pdm-whatif` *"deliberately kept out of `pdm-equipment-deepdive`"* [22 §10.1]. The console calls that operation through the gateway's **pass-through** surface [30 §8.1]; **PdM** calls the Domino Endpoint [22 §13.1: *"Egress | Domino Endpoint (tier-3 what-if) | The only synchronous model call in the service"*]. The console never addresses the Endpoint proxy. §22 row 50 corrects [50 UI-OQ-9], and the correction matters because the two paths have different limits, different problem types, and different owners.

The operation's real constraints, transcribed from [22 §10] and [22 §5.4]:

| Constraint | Console behaviour |
|---|---|
| **One item, ≤ 3 horizons** [22 §10] | The form takes one `installed_item_id` — the route's — and **at most three** horizon values, enforced client-side with a stated limit |
| **45 s monotonic deadline** [22 §10] | The request's own progress is rendered from a monotonic elapsed counter [50 §5.4, D29] — never a wall clock, never an indeterminate spinner with no elapsed time |
| **`503 urn:fathom:problem:pdm:whatif-capacity`** — *"rather than queueing"* [22 §5.4] | `ProblemDetail` with a **manual** retry affordance and **no automatic retry**. [02 §4.3] records that *"[a] timed-out request is not cancelled"*, so an automatic retry stacks a second Endpoint call behind a first that is still running on a surface with *"no autoscaling"* |
| **`422 urn:fathom:problem:pdm:policy-frozen-item`** [22 §4.5.2] | `ProblemDetail`, non-retryable, stating the item is policy-frozen |
| **10 MB payload ceiling, ~60 s practical timeout, no serving SLO** [22 §5.4, §13.2] | The console sends a bounded form and **declares in the box that the surface has no latency guarantee** — a `SheetNote`, because an operator waiting 45 s at a console needs to know that is expected |

**The `[chip accent] tier-3 · interactive` chip does not render as drawn.** `--accent` means *"primary interactive control"* [50 §2.2] and this is a label, not a control; and the label says `tier-3`, which would be branching a UI affordance on `tier` — [50 §11.4 item 38]'s prohibition. `[ESTABLISHED HERE]`: the chip renders `tone="neutral"` reading `interactive · no latency guarantee`, and the box's **availability** is conditioned on `reference_class === "item"` (the branch [03 §7.1] mandates), not on `tier`. Where the reference class is not item-conditional, the box renders `EmptyState` naming the reason. §22 row 51.

**The form's fields are `[OPEN]`.** [22 §10] names the operation but this document has verified no request-body schema for it, and [50 UI-OQ-9] already recorded that *"[t]he one interactive model surface in the console has no drawn form."* §23 UI-OQ-9 carries it forward with the corrected operation. Until the schema is known the box renders the `FigurePlaceholder` with WF's caption and a stated reason — which is exactly what `--hatch` legitimately means [50 §2.5].

---

## 12. Sheet 05 — Work Package Planner

**Routes:** `/maintenance`, `/maintenance/assets/:assetId`, `/maintenance/availabilities/:availabilityId` (§3.1). **Component:** `WorkPackagePlanner` in `src/features/maintenance/`.

### 12.1 What the wireframe draws

| # | WF element | Content as drawn |
|---|---|---|
| 1 | `.box` + `.table-scroll` | label `Work candidates`; columns `Item` · `Driver` · `Priority`. Rows: `SSDG No. 2 bearing` · `[chip accent] prediction` · `high`; `Feed pump PMS` · `[chip neutral] PMS` · `routine`; `Trim pump A` · `[chip critical] casualty` · `urgent` |
| 2 | `.box` + `.table-scroll` | label `Availability: DSRA 26-1 — candidate assignment`; columns `Item` · `Status` · `Reason`. Rows: `[chip good] included` · *"within window, parts on hand"*; `[chip critical] excluded` · *"merged into bearing job — same position"*. Note *"Every included **and** excluded candidate carries a reason — doc 04 §6."* |
| 3 | `.box` | label `Deferral log`; columns `Item` · `Reason class`. Row: `Aux seawater valve` · `[chip neutral] capacity` |

Components [50 §3.5]: `SheetFrame`, `Box`, `WfTable`, `WfTableScroll`, `StatusChip`, `ReasonCell`.

### 12.2 Data wiring

| # | Query | Operation | Setting | Feeds |
|---|---|---|---|---|
| 1 | `keys.passthrough("maintenance","/work-candidates",{asset_id,status:"open"})` | `GET /api/v1/maintenance/work-candidates?asset_id=&installed_item_id=&driver=&status=&changed_since=&limit=&cursor=` [24 §9.1] | **A** | Box 1 |
| 2 | `keys.passthrough("maintenance","/availabilities",{asset_id})` | `GET /api/v1/maintenance/availabilities?asset_id=&changed_since=&cursor=` [24 §9.1] | **A** | The availability selector |
| 3 | `keys.passthrough("maintenance","/availabilities/{id}/work-package")` | `GET /api/v1/maintenance/availabilities/{id}/work-package` [24 §9.1, a singleton carve-out] | **A** | Box 2's package identity |
| 4 | `keys.passthrough("maintenance","/work-packages/{id}/explanation")` | `GET /api/v1/maintenance/work-packages/{id}/explanation` [24 §9.1, §4.4] | **A** | Box 2's rows |
| 5 | `keys.passthrough("maintenance","/deferrals",{asset_id})` | `GET /api/v1/maintenance/deferrals?asset_id=&deferral_reason_class=&changed_since=&cursor=` [24 §9.1] | **A** | Box 3 |

**Box 2 is a three-hop chain — availability → package → explanation — and that is why `/maintenance/availabilities/:availabilityId` exists** (§3.1). On `/maintenance` with no scope, boxes 2 and 3 render `EmptyState` and box 2 shows the availability selector from query 2, listing `availability_type` (`CMAV | SRA | DSRA | EDSRA | ROH | continuous_maintenance`), `window`, `executing_activity`, `ofrp_phase`, and `status` (`planned | committed | executing | closed`) [24 §3.6]. WF's `DSRA 26-1` is an `availability_type` plus an identifier; there is no name field, so the selector renders `availability_type` + `window` + the identifier.

### 12.3 Box 1: the `Priority` column has no field

| WF column | Field | Verdict |
|---|---|---|
| `Item` | `installed_item_id` + `position_id` + `niin` [24 §3.2] | Nomenclature is §6.5's `[GAP]`. **`position_id` renders beside the item**, because [24 §3.2] carries both and [20 §4.4] makes the position *"the LOCATION, never interchangeable"* — a bearing job at position 233-04-A is a different job from the same NIIN elsewhere |
| `Driver` | `driver` — `prediction \| pms \| casualty` [24 §3.2], **IMMUTABLE, trigger-enforced** | `StatusChip`. WF's tones: `accent` for `prediction`, `neutral` for `PMS`, `critical` for `casualty`. **`accent` is wrong** — [50 §2.2] and WF's own legend make status *"independent of the accent color"* and `--accent` mean *"primary interactive control"*; a driver is a status. Corrected to `tone="neutral"` for `prediction` and `pms`, `tone="critical"` for `casualty` (a reported casualty is a real severity, from `casrep_category` 2–4 [24 §3.2]). §22 row 52. **The label renders the enum value verbatim** (`prediction`, `pms`, `casualty`), not WF's `PMS` |
| `Priority` | **`[GAP]`.** `WorkCandidate` [24 §3.2] has **no priority field**. It has `expected_consequence?`, and [24 §3.2] annotates it *"§4.2. **Optimizer-populated, never client-set**"* — so it is `null` until an optimizer run touches the candidate. `consequence_rank` exists only on `CandidateDisposition` [24 §4.4], which is box 2's data, not box 1's | §22 row 11 |

**Resolution, `[ESTABLISHED HERE]`:** the column header becomes **`Expected consequence`** and renders `expected_consequence` where the optimizer has populated it and **`not yet ranked`** where it has not — which is the honest state of an unplanned candidate. Three additional fields render in the same column's disclosure because they change how the figure should be read:

- **`weights_are_illustrative`** [24 §4.4] as a `StatusChip tone="warning"` where true. A consequence figure computed from illustrative weights is not a priority.
- **`fallback_level`** [24 §3.2] where > 0, for §11.3's reason.
- **`driver_disagreement`** [24 §3.2] — `{pms_due_at, prediction_horizon_days, delta_days, retained: true}` — rendered as a `StatusChip tone="warning"` reading `driver disagreement · Δ<n> d`, expandable. It is *"carried through from the merge"* [24 §4.4] and `retained: true` is the contract's way of saying it must not be dropped; a candidate where PMS and the prediction disagree by 40 days is the most decision-relevant row in the table.

**Additional rows the console must not hide.** [24 §3.2]'s `status` enum is `open | packaged | authorized | deferred | superseded | withdrawn | closed`; the query sends `status=open` for box 1 as drawn, and `withdrawn_reason` (`baseline_superseded | prediction_invalidated | item_removed | duplicate | operator`) renders wherever a withdrawn candidate is shown. `merged_candidate_ids[]` — *"the superseded sources, retained forever"* [24 §3.2] — renders as an expandable list on a merge product, which is what makes box 2's *"merged into bearing job"* traceable.

### 12.4 Box 2: `ReasonCell` renders a code, not prose

`GET /work-packages/{id}/explanation` [24 §4.4] returns `CandidateDisposition` records:

| WF column | Field [24 §4.4] | Rendering |
|---|---|---|
| `Item` | `candidate_id` → joined to query 1's candidate | Within-service join; presentation |
| `Status` | **`disposition`** — `included \| excluded \| deferred \| unscorable \| withdrawn` | `StatusChip`. Tones: `good` for `included`, `warning` for `excluded` and `deferred`, `neutral` for `unscorable` and `withdrawn`. **WF's `critical` for `excluded` is wrong** — an exclusion is a planning outcome, not a casualty, and `critical` is the tone the casualty driver uses two boxes away. §22 row 53 |
| `Reason` | **`reason_code`** | §12.4's rule below |

**WF renders free text in the `Reason` column (*"within window, parts on hand"*, *"merged into bearing job — same position"*) and the field is not free text.** [24 §4.4] declares `reason_code` as `enum # CONTROLLED VOCABULARY. Never free text`, with the complete vocabulary: `capacity_exhausted`, `parts_lead_time`, `parts_unavailable`, `prerequisite_unmet`, `ofrp_phase_conflict`, `deployment_blackout`, `availability_full`, `item_down_conflict`, `lower_expected_consequence`, `criticality_floor_deferred`, `baseline_superseded`, `prediction_invalidated`, `item_removed`, `unscorable_no_calibrated_rate`, `holdout_excluded`, `duplicate_of_merged_candidate`.

`[ESTABLISHED HERE]`, `ReasonCell` renders **three things, in this order**, and §22 row 54 files the wireframe edit:

1. **`reason_code`, verbatim**, as the primary text. Sixteen values; the console holds no translation table, because a translation is a paraphrase and the vocabulary is the contract.
2. **`binding_constraint`** [24 §4.4] — *"which constraint bound, from the CP-SAT core"* — plus **`slack`**, as a chip. This is the answer to *"why not"* at the level a planner can act on, and [24 §4.4] notes `excluded` reasons come from CP-SAT's **infeasibility core** for the pinned-inclusion sub-problem, which is a stronger claim than a category.
3. **`counterfactual`** [24 §4.4], which **is** `text` — the one free-text member — rendered verbatim beneath, where present. WF's prose belongs here.

**The totality invariant renders as a check the operator can see.** [24 §4.4]: *"a run is invalid unless `count(dispositions) == count(candidates_in_scope)`, asserted in the same transaction that persists the run."* Box 2's `<caption>` states `n dispositions over n candidates in scope`, and where they disagree the box renders a `ProblemDetail`-class notice — **the console does not silently show a short list.** `[ESTABLISHED HERE]`, and it is the cheapest possible surfacing of an invariant [24](24-scheduling.md) enforces server-side.

**The optimizer's own inputs render in an expandable header**, from `GET /optimizer-runs/{id}` [24 §9.1] (`internal`, `x-side-effects: none`) → `InputWatermark` [24 §4.1]: `snapshot_txid`, `solved_at_monotonic`, `sources[] {source, last_applied_event_id, last_applied_seq, lag_seconds, bound_seconds}`, `baseline_epoch_per_asset`, `stock_epoch`, `conversion_version`, `solver_version`, `seed`. `[ESTABLISHED HERE]`: a disposition list is a claim about a world state, and `sources[].lag_seconds` against `bound_seconds` is what tells a planner whether the solve saw current parts data. **`replan_generation` and `superseded_by_package_id`** [24 §3.7] render as a `StatusChip tone="warning"` where the package has been superseded — a planner reading a superseded assignment is the D16-class failure this program keeps closing.

**Five `409` refusals render as `ProblemDetail` with their own text** [24 §4.1, §9.3]: `staleness-bound-exceeded`, `antecedent-unresolved`, `prediction-invalidated-in-scope`, `lead-time-unavailable`, `clock-dispersion-exceeded`. None is retried automatically; each names a precondition a human resolves.

### 12.5 Box 3: the deferral log

`GET /deferrals?asset_id=` [24 §9.1] → `Deferral` [24 §3.5]:

| WF column | Field | Rendering |
|---|---|---|
| `Item` | `installed_item_id` + `position_id` | As box 1 |
| `Reason class` | **`deferral_reason_class`** — `capacity \| tempo \| parts_unavailable \| risk_disagreement`, *"REQUIRED. NO DEFAULT. NOT NULLABLE. [D34]"* | `StatusChip tone="neutral"`, value verbatim. WF's `capacity` is one of the four |

Three fields are added to the drawn table, `[ESTABLISHED HERE]`, because a deferral log without them records that risk was accepted and not by whom:

- **`risk_accepted_by`** and **`risk_acceptance_authority`** [24 §3.5] — the latter an `AuthorityClass` [03 §7.2.1]. A deferral is an accepted risk and the accountable name is the point of logging it.
- **`revised_window`** `{earliest, latest}` [24 §3.5].
- **`disagreement`** `{asserted_rul_days?, asserted_probability_band?, basis}` and **`prediction_ref`** [24 §3.5], rendered **only** on `deferral_reason_class: risk_disagreement`. [24 §3.5] makes both mandatory at that class with three `422` validations — `deferral.risk_disagreement_requires_prediction_ref`, `deferral.risk_disagreement_requires_basis`, `deferral.non_disagreement_must_not_assert_disagreement` — and the console mirrors the third by **never rendering a disagreement block on a non-disagreement row**, even if one arrives.

**`reason_narrative`** [24 §3.5] is *"untrusted free text; never the classification."* Rendered as text, escaped, in a disclosure — **never as the reason class**, and never in a position where it could be mistaken for one. `ui-narrative-not-classification` (§19.1).

### 12.6 Sheet 05 states

| Condition | Rendering |
|---|---|
| `/maintenance` with no scope | Box 1 `EmptyState` reading *"Select an asset"*; box 2 renders the availability selector; box 3 `EmptyState`. **Not skeletons** |
| No availability selected | Box 2 shows the selector and an `EmptyState`; queries 3 and 4 are not issued |
| Query 3 `404` | The availability has no work package. `EmptyState` reading *"No work package for this availability"* — a real and common planning state, not an error |
| Query 4 `409` | `ProblemDetail` naming which of [24 §4.1]'s five refusals, with the precondition stated |
| Disposition count ≠ candidate count | The invariant notice (§12.4) |
| Package superseded | The `replan_generation` warning chip (§12.4) |
| Empty deferral log | `EmptyState`. A hull with no deferrals is good news and is stated as *"no deferrals recorded"* |

---

## 13. Sheet 06 — Stock & Requisition View

**Routes:** `/supply`, `/supply/parts/:niin`, `/supply/reservation-sets/:reservationSetId` (§3.1). **Component:** `StockAndRequisitionView` in `src/features/supply/`.

### 13.1 What the wireframe draws

| # | WF element | Content as drawn |
|---|---|---|
| 1 | `.col.box` | label `Stock / allowance — NIIN 013479201`; a headerless `WfTable`: `On-hand` `2` · `Allowance` `3` · `Condition` `[chip good] A` · `Lead time` `14d` |
| 2 | `.col.box` | label `Reservation set — RS-00219` + `[chip warning] TTL 03:58:02`; columns `NIIN` · `Qty`; note *"Atomic confirm — all lines succeed or the set rolls back."* |
| 3 | `.box` + `.table-scroll` | label `Requisition tracker`; columns `Doc no.` · `NIIN` · `Status` · `Priority`. Row: `N0021826058A102` · `013479201` · `[chip warning] BB — backordered` · `02` |
| 4 | `.box` | label `Demand forecast`; `.placeholder-fig` *"predicted consumption, 90-day horizon — feeds allowance review"* |

Components [50 §3.5]: `SheetFrame`, `Box`, `WfTable`, `WfTableScroll`, `StatusChip`, `TtlCountdown`, `FigurePlaceholder`.

### 13.2 Data wiring

| # | Query | Operation | Setting | Feeds |
|---|---|---|---|---|
| 1 | `keys.passthrough("supply","/availability",{niin,asset_id})` | `GET /api/v1/supply/availability?niin=&location=&asset_id=&condition_code=&purpose_code=&changed_since=&cursor=` [26 §7.6] | **A** | Box 1 |
| 2 | `keys.passthrough("supply","/lead-times",{niin,location})` | `GET /api/v1/supply/lead-times?niin=&location=` [26 §7.6] | **A** | Box 1's lead time, where the availability response omits it |
| 3 | `keys.passthrough("supply","/reservation-sets/{id}")` | `GET /api/v1/supply/reservation-sets/{id}` [26 §7.6, added by 26 §7.4] | **B** | Box 2 |
| 4 | `keys.passthrough("supply","/requisitions",{niin,asset_id})` | `GET /api/v1/supply/requisitions?asset_id=&niin=&status=&changed_since=&cursor=` [26 §7.6] | **A** | Box 3 |
| 5 | `keys.passthrough("supply","/demand-forecast",{niin,horizon_days:90})` | `GET /api/v1/supply/demand-forecast?niin=&horizon_days=&form=` [26 §7.6] | **A** | Box 4 |
| 6 | `keys.passthrough("supply","/interchangeable-groups",{niin})` | `GET /api/v1/supply/interchangeable-groups?niin=` [26 §7.6] | **A** | Box 1's substitutes disclosure |

**There is no `/parts/{niin}` on `supply`.** [26 §7.6] is *"[t]he complete required surface — closed"* and every NIIN-scoped read is a **query parameter**, never a path segment. The console's route `/supply/parts/:niin` [50 §4.2] is a **console** path, not an API path, and §19.3's contract test asserts that no request is constructed from the route path by concatenation. `[ESTABLISHED HERE]`, and worth stating because the two look alike enough to be confused once.

### 13.3 Box 1: the flat `On-hand` / `Condition` pair is not what the schema publishes

[26 §7.2](26-supply.md)'s `GET /availability` response gives, per position: `niin`, `location_id`, `location_type`, `asset_id`, `stock_epoch`, and **`by_condition[]`** — declared **`(MANDATORY, non-empty; a bare `on_hand_qty` at position level does not exist in the schema)`** — with members `condition_code`, `purpose_code`, `on_hand_qty`, `reserved_qty`, `available_qty`, `due_in_qty`; plus `lead_time {…}`, `interchangeable_group_id`, `allowance_position {allowance_qty, allowance_state, derivation_code, sparing_model}`, `smr {source_code, recoverability}`, `cog`.

**WF's four flat rows cannot represent this.** A NIIN at a location can hold condition-A and condition-F stock simultaneously under different purpose codes, and *"`available_qty` is derived, never stored"* [26 §2.3] as `on_hand_qty − reserved_qty` per `(niin, location_id, condition_code, purpose_code)`. A single `On-hand 2` with a single `Condition A` chip asserts a homogeneous holding.

`[ESTABLISHED HERE]`, §22 row 55: box 1 renders **two tables**, both inside the drawn box.

**Table 1 — one row per `by_condition[]` entry**, columns `Condition` · `Purpose` · `On-hand` · `Reserved` · `Available` · `Due-in`:

| Column | Field | Rendering |
|---|---|---|
| `Condition` | `condition_code` (`char(1)`) | `StatusChip`. WF's `good` for `A` is the one status tone here that has a real basis — a serviceable condition code is a materiel-condition classification, not an invented band. `A` → `good`; every other code → `neutral`, because the console holds no condition-code severity table and inventing one would grade materiel |
| `Purpose` | `purpose_code` (`char(1)`) | Verbatim. `'S'` marks stock protected for a specific asset [26 §2.5] |
| `On-hand` / `Reserved` / `Available` / `Due-in` | `on_hand_qty`, `reserved_qty`, `available_qty`, `due_in_qty` | `tabular-nums`. **`available_qty` is rendered as served and never recomputed** — the console does not subtract, because the server's definition is per-`(condition, purpose)` and a browser subtraction across rows would be wrong |
| *(caption)* | `stock_epoch` | Rendered in the caption. It is the fence a reservation is made against (§13.4) and *"[e]very `stock_epoch` returned is directly usable as `expected_stock_epoch`"* [26 §7.3] |

**Table 2 — allowance**, from `allowance_position`: `allowance_qty` (WF's `Allowance 3`), **`allowance_state`** — `authorized_and_held \| authorized_shortfall \| held_not_authorized \| not_authorized_not_held` [26 §2.4] — `derivation_code`, and `sparing_model`.

**`allowance_state` is rendered prominently and `held_not_authorized` is never normalized away.** [26 §2.4] is explicit: it *"is not a defect to be normalised away. It is a real and common shipboard condition, its remedy is an offload or an allowance revision rather than a requisition, and a system that reports it as 'available' tells a planner a part is usable when its presence is unauthorized and unfunded."* `StatusChip tone="warning"` on `held_not_authorized` and `authorized_shortfall`; `good` on `authorized_and_held`; `neutral` on `not_authorized_not_held`.

**`proposed_allowance_qty` renders separately and never in the `Allowance` row.** [26 §2.4]: *"The separation of `allowance_qty` from `proposed_allowance_qty` is the whole design … Writing that improvement into `allowance_qty` would make the platform an unaccountable allowance authority."* Where present it renders as `proposed <n> — pending supply_officer adjudication`, with a link to `/adjudication/{proposal_id}` from `proposal_id` [26 §2.4].

**`Lead time 14d` is ambiguous as drawn, and the ambiguity selects a procurement instrument.** [26 §7.2]'s `lead_time` object carries **`order_and_ship_time_days`**, **`procurement_lead_time_days`**, `basis`, `observed_n`, `as_of` — and [26 §5.4] makes the second *"a distinct field … because it selects the instrument (`need_date − now > procurement_lead_time` → Special Program Requirement, `DYA` → `DYK`/`PA`, or `PB` → `PR`)."* `[ESTABLISHED HERE]`, §22 row 56: **both render, each labelled**, with `basis` (e.g. `observed`) and `observed_n` beside them, and `as_of` as the pair's currency. A single unlabelled `14d` is the field that makes a planner order the wrong instrument.

**`interchangeable_group_id`** and query 6 render as a disclosure: a NIIN with substitutes has a materially different availability picture, and [26 §3.6] returns `interchangeable_group_id` on a failed reservation line for exactly that reason.

### 13.4 Box 2: the reservation set and its TTL

`GET /reservation-sets/{id}` [26 §7.6] → `reservation_set_id`, `asset_id`, `for_work_package_id`, `state`, **`granted_at`**, **`ttl_seconds`**, **`expires_at`**, **`extend_count`**, `lines[] {line_ref, niin, location_id, quantity, condition_code, purpose_code, for_work_order_id, stock_epoch_after}`, `classification` [26 §3.5].

| WF element | Field | Rendering |
|---|---|---|
| Label `Reservation set — RS-00219` | `reservation_set_id` | Verbatim |
| `[chip warning] TTL 03:58:02` | **`expires_at`** | `TtlCountdown` — §13.4's rules below |
| Columns `NIIN` · `Qty` | `lines[].niin`, `lines[].quantity` | Plus `condition_code`, `purpose_code`, and `for_work_order_id`, because a line reserved in condition F against a specific work order is not the same reservation as a bare quantity |
| Note *"Atomic confirm"* | — | Renders verbatim as a `SheetNote`. `state` has **no `pending` and no `partial`** [26 §3.2], which is what makes the note true |

**`TtlCountdown` rules**, `[ESTABLISHED HERE]` and every one of them from a cited constraint:

1. **`expires_at` is captured once and the countdown is a monotonic delta from it** [50 §3.2, §5.4]: *"it is **not** a poll"*, and [09 §9.2 item 7] / D29 forbid wall-clock arithmetic in a countdown. `expires_at` is computed server-side as `clock_timestamp() + (ttl_seconds || ' seconds')::interval` [26 §2.6], so it is the server's instant and the client measures elapsed time against it with `performance.now()`.
2. **`aria-live="off"`, with the expiry instant also present as static text** [50 §8.3]. A per-second live region is unusable.
3. **The chip's tone is `state`-derived, not time-derived**: `state: confirmed` → `warning` (a holding that will expire is a warning by nature, which is WF's drawn tone and the one status tone on this sheet with an obvious basis); `consumed` → `good`; `released`/`expired` → `neutral`. **No countdown threshold changes the tone** — that would be an invented band (§6.8).
4. **At zero the countdown does not assert expiry.** It renders `expired at <instant> — awaiting confirmation` until query 3 (setting **B**, chosen in §3.4 precisely for this) returns a `state` change. The reaper runs on a 15 s interval [26 §7.4], so the server's transition trails the clock by up to 15 s, and a client that flips to `expired` on its own would be asserting a state change it did not observe.
5. **`extend_count` and `extends_remaining` render.** [26 §7.4] caps extensions at **8**; a set on its eighth extension is about to become unextendable and the operator needs to know before the planner's saga does [24 §4.5.6: at the cap the package goes to `EXPIRED_UNAPPROVED`].
6. **`release_cause`** [26 §2.6] — `released_by_caller \| expired \| consumed \| stock_shortfall \| superseded` — renders on a released set. `stock_shortfall` is materially different from `expired` and a single "released" label loses it.

**The console issues no reservation mutation.** `POST /reservation-sets`, `POST /reservation-sets/{id}/extend`, and `DELETE /reservation-sets/{id}` are all `x-agent-eligible: false`, `state-changing` [26 §7.6] — and, more to the point, WF sheet 06 draws **no button**. Reservation is the scheduling saga's act [24 §4.5.1], not an operator's on this sheet, and adding a button would be inventing an affordance [50 §11.2 item 12] that would also enter a saga the console cannot compensate.

### 13.5 Box 3: the requisition `Status` column, whose enum does not exist

| WF column | Field [26 §2.5] | Verdict |
|---|---|---|
| `Doc no.` | `document_number` (`char(14)`, PK) | Verbatim. Construction is [26 §4.1]'s and the console never parses it |
| `NIIN` | `niin` | Linked |
| `Status` | **`state supply.requisition_state`** | **`[GAP]`. `supply.requisition_state` is referenced in the DDL and defined nowhere in [26](26-supply.md) or in any other document** — a repository-wide search for the type name returns exactly one hit, its own column declaration. The console cannot enumerate a value set that does not exist, and cannot map it to a tone. §22 row 12 |
| `Priority` | `priority_designator` (`smallint`, 1–15) | Verbatim, as two digits. WF's `02` matches |

**And WF's cell content is not `state`.** `BB — backordered` is a MILSTRIP supply status code; the fields available are `state` (undefined), **`current_dic`** (`char(3)`, *"the DIC of the most recent transaction"* [26 §2.5, §4.2]), and **`advice_code`** (`char(2)`, e.g. `'2L'` for a predicted abnormal quantity). No field is a two-character supply status code. §22 row 57.

`[ESTABLISHED HERE]`, the interim: the column renders **`state` verbatim, uncoloured** (`tone="neutral"`, always — a tone over an unknown enum would be a guess), with **`current_dic`** as a second chip and **`advice_code`** where present. When the enum lands, tones follow the same discipline as every other status column: from the field, never from a threshold.

Four further fields render, `[ESTABLISHED HERE]`, because they carry the two invariants [26 §2.5] enforces and an operator must be able to see them satisfied:

- **`driver`** — `prediction \| casualty \| allowance \| pms \| manual`. `supply.requisition_driver` is *also* undefined as a type in the document, though its values are enumerated inline; §22 row 12's second clause.
- **`urgency_of_need`** (`A|B|C`) and **`required_delivery_date`**. The two CHECKs are `und_a_forbidden_for_predicted` — [07 §4.5] via [26 §2.5]: *"a predicted failure is not yet 'unable to perform.' UND 'A' for a prediction-driven requirement is logically wrong and a logistician will notice"* — and `predicted_rdd_is_forward`. Rendering both makes the constraint visible.
- **`triggering_prediction_id`** where the driver is `prediction`, linked to the prediction's provenance (§11.5). This is [09 §8.4]'s provenance obligation reaching a supply document.
- **`awaiting_parts_days`** and **`projected_availability`**, which are the two figures a planner is actually waiting on.

**In-transit** [26 §2.7] renders as an expandable row detail where a `transportation_control_number` is available: `from_location_id`, `to_location_id`, `shipped_at`, `estimated_arrival`, `last_status_dic`, `last_status_at`. [26 §2.7] notes in-transit *"contributes to `due_in_qty` at `to_location_id` and to nothing else"*, so it is a detail of the due-in figure and is rendered as one, never as a second stock quantity.

### 13.6 Box 4 and sheet 06 states

Box 4 stays a `FigurePlaceholder` [50 §3.3 gap 4] with WF's caption verbatim, and renders `GET /demand-forecast?niin=&horizon_days=90&form=` [26 §7.6] as a `WfTable` beneath it. `horizon_days=90` is WF's own drawn horizon and it is sent explicitly; `form` selects the response form and the console sends the tabular form. **The console issues no `POST /demand-forecast-runs`** [26 §7.6] — it is `state-changing` and no button is drawn.

| Condition | Rendering |
|---|---|
| `/supply` with no NIIN | All four boxes `EmptyState`, plus the `IdentifierLookup` hint (§4.4). A fleet-wide stock view is not a drawn sheet |
| Query 1 empty | `EmptyState` reading *"no stock position for this NIIN at any location"*. **Not `On-hand 0`** — [30 §3.4]'s rule, and a zero here would say the part is out of stock when the truth is that no position record exists |
| `by_condition[]` present but all quantities zero | Rendered as zeros. **This is the one place a zero is correct**, because the row asserts a real position with no stock. The distinction from the empty case is exactly [30 §3.4]'s `empty`-versus-`unavailable` distinction, at the row level |
| `missing_keys[]` returned by `POST /availability/query` | Rendered explicitly [26 §7.3: *"never silently dropped"*]. The console uses the batch form only where it needs several keys at once |
| Query 3 `404` | `EmptyState`. A released set is deleted from view, not an error |
| Query 3 `409 reservation-set-expired` | `ProblemDetail`. [24 §4.5.6]: an expired set *"[is] not resurrected"* — no retry affordance |
| Reservation `409 reservation-set-infeasible` | Not reachable from this screen (no mutation, §13.4). Where the console *displays* one from a saga, `failed_lines[]` renders with `reason` from the closed enum [26 §3.6] and `reservation_set_id: null` is honoured as null, never as a missing set |
| Query 4 empty | `EmptyState` reading *"no open requisitions"* |

---

## 14. Sheet 07 — Bounded Review Queue

**Routes:** `/pma` and `/pma/reviews/:reviewId` (§3.1, replacing [50 §4.2]'s `/pma/missions/:missionId`). **Component:** `BoundedReviewQueue` in `src/features/pma/`.

### 14.1 What the wireframe draws

| # | WF element | Content as drawn |
|---|---|---|
| 1 | `.sheet-note` | *"15% of candidates are seeded canaries with planted ground truth, presented **indistinguishably** from real candidates — this is how recall is measured. (doc 06 §6)"* |
| 2 | `.box` | label `Mission: Patrol 26-3 — candidate 3 of 9`; a `.row` with a `.placeholder-fig` *"evidence — telemetry window snippet"* (flex 0 0 220px) and a column containing *"Window 04:12–04:19 · Feed pump #A19381 · vibration + temperature co-excursion"* and three buttons: `Confirm` (primary) · `Reject` · `Escalate` (ghost) |
| 3 | `.box` | label `Review history`; columns `Mission` · `Tags confirmed` (num) · `Duration` (num) · `Reviewer`. Row: `Sortie 0441` · `4` · `8m 20s` · `PO2 Alvarez [chip neutral] qualified` |

`TitleBlock`'s `tb-right` in WF reads `Doc 06 §6` / `Cap: 12 · ~45s/candidate`. Components [50 §3.5]: `SheetFrame`, `SheetNote`, `Box`, `FigurePlaceholder`, `Button`, `ButtonRow`, `AdjudicationConfirm`, `WfTable`, `StatusChip`.

### 14.2 The canary rule, and it is the most important sentence in this section

**WF element 1 is drawing rationale and must not become UI content, and the console must be structurally incapable of rendering canary status.** [23 §2.2](23-pma.md) makes `origin` (`detector | agent | canary`) **WITHHELD (I3)**, *"never selected by any reviewer-facing repository method"*, and the wire model is explicit: *"`AnomalyCandidateView` in `schemas/candidates.py` has **no `origin`, no `canary_*`, and no `plant_*` member**"* — so *"no `include=` expansion can surface one."*

Consequences, all `[ESTABLISHED HERE]` and all testable:

1. **The console never requests, renders, infers, logs, or sorts on canary status.** `ui-no-canary-signal` (§19.1) asserts no identifier matching `canary`, `plant`, `origin`, or `ground_truth` appears in `src/features/pma/`.
2. **WF's 15 % note does not render.** It is [06 §6]'s measurement design explained to a wireframe reviewer; rendering it to a reviewer at a console tells them a seeded population exists, which is the first half of distinguishing it. The `SheetNote` slot instead carries the domain guidance from [21](21-telemetry.md) that *is* operator-relevant (gaps expected on burst-on-reconnect channels), which is the same note sheet 03 carries. §22 row 58.
3. **No candidate is visually distinguished from another on any axis the console could correlate with origin** — not ordering (`presentation_ordinal` is server-assigned, `1..cap` [23 §2.2], and rendered in that order), not `detector_score`, not `rank_stratum`. `rank_stratum` is *"0..2 tercile; **injection-matching key**"* [23 §2.2] and is therefore **never rendered**, because it is the field the matching is done on.
4. **`detector_score` and `rank_components` are not rendered either.** `[ESTABLISHED HERE]` — they are ranking internals, and a reviewer who learns which candidates score unusually has learned something about the population's composition. `rank_score` is likewise withheld from display.

This is the one screen where the console's correctness requirement is to show *less* than it is given.

### 14.3 Data wiring

| # | Query | Operation | Setting | Feeds |
|---|---|---|---|---|
| 1 | `keys.passthrough("pma","/reviews",{status:"open",reviewer})` | `GET /api/v1/pma/reviews?asset_id=&status=&reviewer=&changed_since=&limit=&cursor=` [23 §3.7] | **A** | The review selector on `/pma`; box 3's history at `status=completed` |
| 2 | `keys.passthrough("pma","/reviews/{id}")` | `GET /api/v1/pma/reviews/{id}` [23 §3.7] — **returns an `ETag`** | **A** | Box 2's header |
| 3 | `keys.pinned("pma","/reviews/{id}/candidates",{include:"evidence_manifest"})` | `GET /api/v1/pma/reviews/{id}/candidates?include=&limit=&cursor=` [23 §3.7] | **C** | Box 2's candidate |
| 4 | `keys.passthrough("pma","/tags",{mission_id})` | `GET /api/v1/pma/tags?installed_item_id=&mission_id=&taxonomy=&changed_since=&cursor=` [23 §3.7] | **A** | Box 3's confirmed count — §14.5 |

**Query 3 is one round trip for the whole review, by contract.** [23 §3.6] obliges PMA to serve *"all `cap` candidates with manifests and pre-signed object URLs"* in one call, with *"default page size **equals `candidate_cap`**"* and *"no cross-service fetch during review."* The console therefore fetches once, at setting **C**, and paginates never — and `GET /reviews/next?reviewer=` [23 §3.7] is used to **prefetch the next review** while the operator works, which is what that operation exists for.

**Query 3 is `pinned` because refetching it would reorder the operator's queue.** [23 §2.1] pins `taxonomy_version_pin` at creation, *"never re-pinned"*, and `presentation_ordinal` is `1..cap` within the review [23 §2.2]. A refetch mid-review that returned a different order would move the candidate under the reviewer's cursor.

**`GET /reviews/{id}/candidates` is `x-agent-eligible: no`, and [23 §3.7] marks that *"deliberate, `[ESTABLISHED HERE]`"* in its own document.** The console is a human surface and calls it; nothing here changes.

### 14.4 Box 2: the candidate, the evidence, and the three buttons

**The header.** WF's `Mission: Patrol 26-3 — candidate 3 of 9`:

| Element | Field | Notes |
|---|---|---|
| `Mission: Patrol 26-3` | `mission_id` [23 §2.1] | No mission name field exists (§10.6); the identifier renders |
| `candidate 3 of 9` | `presentation_ordinal` of `candidate_cap` [23 §2.1, §2.2] | **`candidate_cap` is a column, not a constant** — [23 §3.6]: *"12 for the demonstration (06 §6)"* and *"a Helm value, not a constant."* The console reads it from the review and **never hard-codes 12**. WF's `9` is a real page of admitted candidates, which may be fewer than the cap; the denominator rendered is the count of admitted candidates actually returned, and the cap renders separately in the `tb-right` slot |
| *(added)* | `state` [23 §2.1] — `pending_evidence \| deferred_admission_control \| open \| completed \| abandoned` | **`deferred_admission_control` is a first-class state, not an error** [23 §3.6]. It renders as an explanatory `EmptyState` naming admission control, and box 2 shows no candidate — there is none to show |
| *(added)* | `review_kind` (`primary \| re_review`) and `blinded_from_review_id` [23 §2.1] | `re_review` renders as a chip. **`blinded_from_review_id` is never rendered** — it is the blinding link, and showing it unblinds the re-review |
| *(added)* | `taxonomy_version_pin` [23 §2.1] | A chip. A tag's `taxonomy_version` is mandatory with no default [23 §2.4]; the reviewer should see which version their confirmation will be recorded under |

**The candidate line.** WF's *"Window 04:12–04:19 · Feed pump #A19381 · vibration + temperature co-excursion"*:

- `window_start` → `window_end` [23 §2.2], rendered with the zone named [50 §12.1].
- `installed_item_id` and **`position_id`** — [23 §2.2] labels them *"the PHYSICAL item"* and *"the LOCATION, never interchangeable"*, and both render.
- **`channels_implicated`** (`text[]`) [23 §2.2] renders as chips. WF's *"vibration + temperature co-excursion"* is prose; the field is a channel-key array and it renders as one, each linked to `/telemetry/installed-items/{id}` with the window as the `from`/`to` (§10.2).
- **`detection_origin`** (`enterprise | edge`) [23 §2.2] renders as a chip. It is not `origin` — §14.2's withheld field — and it is a legitimate operational fact: an edge-detected candidate was found on a hull.
- `baseline_id` / `baseline_epoch` [23 §2.2] in the disclosure, because a confirmation is fenced on the epoch [23 §3.7: `baseline-superseded` 409 carries `baseline_epoch_submitted` / `_current`].

**The evidence placeholder, and the object-store question nobody has answered.** WF's `.placeholder-fig` is *"evidence — telemetry window snippet."* [23 §2.6] materializes evidence into bucket `fathom-pma-evidence` with an `object_manifest` of `{key, bytes, sha256, media_type, role}` and a `content_hash` Merkle root, and [23 §3.6] serves **pre-signed object URLs** that *"outlive the review budget."*

**`[GAP]`: no document states whether those pre-signed URLs are reachable from an operator's browser.** [09 §9.5 item 26] forbids a runtime call to a public-internet service — the object store is internal, so that is not the objection — but nothing declares an ingress path from the operator's network to the object store, and the gateway's surface [30 §8.1] is `/api/v1/{slug}/…` and `/api/v1/gateway/…` only, with no object-store proxy. §22 row 59, and it is **blocking for sheet 07's evidence pane**.

Interim, `[ESTABLISHED HERE]`: the pane renders the `object_manifest` as a `WfTable` — `role`, `media_type`, `bytes`, and the `sha256` prefix — plus **`telemetry_completeness`** and the `content_hash` [23 §2.6], with the `FigurePlaceholder` caption stating that the artifacts are not rendered inline. A reviewer can see *what* evidence exists and its integrity hash without fetching it. That is a materially worse review than the drawn one, and it is a stated limitation rather than a silent blank. **`state: materialising | failed | superseded`** [23 §2.6] renders distinctly, and `409 urn:fathom:problem:pma:evidence-not-materialised` [23 §3.7] renders as `ProblemDetail` — [23 §3.6] requires evidence materialized *"at stage 9, before review open"*, so an unmaterialized package on an open review is a real fault.

**The three buttons.**

| WF button | Operation | Rules |
|---|---|---|
| `Confirm` (primary) | `POST /api/v1/pma/reviews/{id}/candidates/{cid}/confirm` [23 §3.7] → creates an `AnomalyTag` | `Idempotency-Key` per user action [03 §4, 50 §5.6]. Requires a claim first — §14.6 |
| `Reject` | `POST /api/v1/pma/reviews/{id}/candidates/{cid}/reject` [23 §3.7] → creates a `TagRejection` | **Requires a `reason_class`**, and the console must collect it: [23 §2.5]'s enum is `normal_for_this_equipment`, `normal_for_this_condition`, `already_known_and_repaired`, `sensor_artifact`, `wrong_installed_item`, `duplicate_of_candidate`, `insufficient_evidence`, `other` — nine values, one of which (`duplicate_of_candidate`) additionally needs `duplicate_of_candidate_id`. **WF draws a bare button**, so the reject flow opens an `AdjudicationConfirm` (`AlertDialog` [50 §3.2]) carrying a `Select` of the nine reasons and an optional `reason_text`. §22 row 60 |
| `Escalate` (ghost) | **`[GAP]`.** [23 §3.7]'s reviewer-facing actions are `confirm`, `reject`, the batch `POST /reviews/{id}/adjudications`, `POST /reviews/{id}/claim`, and `POST /reviews/{id}/complete`. **There is no escalate operation** | §22 row 61. The button renders **disabled with a stated reason**, never as a no-op click — a review action that silently does nothing is worse than one that is visibly unavailable |

**`is_negative_label` is derived from `reason_class`, server-side** [23 §2.5], and the console **never computes it and never displays it as a reviewer-facing consequence**. `NEGATIVE_LABEL_CLASSES` is declared once in `services/pma/.../labels.py` [23 §2.5]; a console-side copy would be a second definition of the label stream's semantics. `[ESTABLISHED HERE]`

**Every confirmation passes through `AdjudicationConfirm`** [50 §5.6], and it states two things the reviewer must see before acting: the tag will be recorded under `taxonomy_version_pin`, and `dwell_seconds` is being measured. [23 §3.6] has the client report per-candidate dwell (*"clamped to the review's monotonic duration"*, `fathom_pma_candidate_dwell_seconds`), so the console measures it — **monotonically** [50 §5.4] — and `low_dwell` [23 §2.4] is a server-derived flag the console does not compute.

### 14.5 Box 3: `Tags confirmed` has no field, and the count is legitimate anyway

| WF column | Field [23 §2.1] | Verdict |
|---|---|---|
| `Mission` | `mission_id` | Identifier |
| `Tags confirmed` | **`[GAP]`.** `pma.mission_review` has no confirmed-count column, and [03 §4] forbids a total count on an unbounded collection | §22 row 14 |
| `Duration` | **`duration_seconds`** [23 §2.1] — *"MONOTONIC-measured, not a timestamp difference"* | Rendered as `8m 20s`. **The console does not compute it** from `opened_at`/`completed_at`; the field exists precisely because that subtraction is wrong |
| `Reviewer` | `assigned_reviewer_id` | §14.5's name resolution below |
| `[chip neutral] qualified` | `qualification_snapshot_id` on the tag [23 §2.4], or `GET /reviewers/{id}/qualifications` [23 §3.7] | A chip reading `qualified` where a snapshot exists. **Never absent-means-unqualified** — where the snapshot is unknown the chip reads `qualification unknown` |

**`Tags confirmed` renders a real count, and this is the one screen where a client-side count is unambiguously sound.** A review is bounded: `candidate_cap` is 12 for the demonstration [23 §3.6] and is a column [23 §2.1], so `GET /tags?mission_id={id}` returns **at most `candidate_cap` rows** — a single, fully-materialized page. [50 §3.3 gap 1] permits a client-side operation *"only over a fully-materialized page"*, and this is one by contract. `[ESTABLISHED HERE]`: the cell renders the count of returned tags **with the cap as its stated bound** (`4 of cap 12`), and where the response carries a `next_cursor` the cell renders `4+` and says the page was not the whole set — which cannot happen at the specified cap but is what makes the rendering honest if the cap moves. §22 row 14 still asks [23](23-pma.md) for the field, because a per-review count belongs on the review.

**Reviewer name resolution.** `assigned_reviewer_id` is an identifier; WF draws `PO2 Alvarez`. [31 §8](31-auth.md) offers `GET /principals/{sub}` — *"[d]isplay attributes for audit rendering and the adjudication queue"* — which is exactly this case and is reachable because the console has the `sub` from the review row (unlike [50 §9.2]'s original problem, where it had no `sub` for *itself*). Fetched at setting **C** per identifier, and where it fails the identifier renders verbatim. `[ESTABLISHED HERE]`

**`GET /quality-metrics` is never called.** [23 §3.7] marks it `internal`, `x-agent-eligible: no`, *"precision and canary recall jointly, ABAC-restricted"*, with `403 urn:fathom:problem:pma:quality-metrics-forbidden`. It is the measurement surface §14.2 exists to keep away from a reviewer, and the console holds no code that references it. `ui-no-quality-metrics-call` (§19.1).

### 14.6 The claim, and sheet 07's states

**A review must be claimed before any candidate action.** [23 §3.7]: `POST /reviews/{id}/claim` is the *"reviewer lease"*, monotonic-evaluated, writing `claimed_by` and `claimed_until` [23 §2.1]; `409 urn:fathom:problem:pma:review-not-claimed` is the refusal. `[ESTABLISHED HERE]`: the console claims on **explicit operator action** — a `Claim review` button, not an implicit claim on page load — because a claim is a lease other reviewers are blocked by and opening a URL is not an intention to work. Until claimed, the three action buttons are disabled with the reason stated.

| Condition | Rendering |
|---|---|
| `/pma` with no review | Box 2 `EmptyState`; box 3 renders completed reviews from query 1; a review selector lists `status=open` reviews with their `mission_id`, `asset_id`, and admitted-candidate count |
| `state: pending_evidence` | `EmptyState` naming the state; no candidate, no buttons |
| `state: deferred_admission_control` | `EmptyState` explaining admission control [23 §3.6]: no `mission_review.opened` was published and there is nothing to review yet. **Not an error** |
| Not claimed | Candidate renders; buttons disabled with the reason |
| Claimed by another reviewer | `claimed_by` rendered (name-resolved), buttons disabled, `claimed_until` shown as an instant |
| `429 admission-control-engaged` | `RateLimitNotice`-class rendering with `Retry-After` [23 §3.7] |
| `409 candidate-already-adjudicated` | Refetch query 3 and advance; **never resubmit** |
| `409 tag-immutable` | `ProblemDetail`, non-retryable |
| `409 baseline-superseded` | `ProblemDetail` naming `baseline_epoch_submitted` and `_current` [23 §3.7], with a refetch affordance |
| `422 signature-unknown-at-version` | `ProblemDetail` rendering `resolved_alternatives[]` [23 §3.7] as selectable options — the server offered them and dropping them would make the error unrecoverable |
| `423 divergence-budget-exceeded` | `ProblemDetail`, non-retryable, naming the budget |
| `403 quality-metrics-forbidden` | Unreachable (§14.5); handled so it is never silently swallowed |
| Evidence not browser-reachable | The manifest table and the stated limitation (§14.4) |

---

## 15. Sheet 10 — Unified Adjudication Queue

**Routes:** `/adjudication` and `/adjudication/:proposalId`. **Component:** `UnifiedAdjudicationQueue` in `src/features/adjudication/`. The detail is a **nested route beside the queue, not a modal** [50 §4.2] — the URL must be shareable so a second adjudicator can reach the same proposal [03 §7.2.1].

### 15.1 What the wireframe draws, and what it omits

| # | WF element | Content as drawn |
|---|---|---|
| 1 | `.box` + `.table-scroll` | label `Pending proposals — 7`; columns `Kind` · `Target` · `Authority required` · `Blast radius` · `Status`. Three rows; row 2's authority cell reads `fleet_authority [chip critical] dual control` |
| 2 | `.box` | label `Adjudication panel — interval_change (class scope)`; text *"Evidence: 3 records · 1 causal finding (moderate strength) · source_trust: program"*; two buttons `Approve — signature 1 of 2` (primary) and `Reject`; note *"Dual control required at class/fleet scope — doc 03 §7.2.1."* |
| — | **absent** | **Any filter or sort control.** [50 §13 row 8]: [30 §4.5] defines *"roughly twenty named query parameters and three sort orders … but sheet 10 draws no filter or sort control at all, so the queue as drawn cannot be filtered."* **§15.3 draws and wires them, which is what [50 §13 row 8] assigned to this document** |

Components [50 §3.5]: `SheetFrame`, `Box`, `WfTable`, `WfTableScroll`, `StatusChip`, `DualControlBadge`, `AdjudicationPanel`, `EvidenceSummary`, `Button`, `ButtonRow`, `AdjudicationConfirm`, `QueueFreshnessNotice`, `QueueFilter`, `NonProgramEvidenceFlag`, `ApproximateTime`.

### 15.2 Data wiring

| # | Query | Operation | Setting | Feeds |
|---|---|---|---|---|
| 1 | `keys.proposals.list(params)` | `GET /api/v1/gateway/proposals?…` [30 §4.5] | **B** | Box 1; `QueueFreshnessNotice` |
| 2 | `keys.proposals.detail(proposalId)` | `GET /api/v1/gateway/proposals/{proposal_id}` [30 §4.5, §4.6] | **C** | Box 2. Carries **the owner's `ETag` verbatim** |
| 3 | `keys.views.redesignCase(caseId)` | `GET /api/v1/gateway/views/redesign-case/{case_id}` [30 §3.2] | **C** | Box 2, **only** where `kind === "redesign_case"` — §15.5 |
| 4 | `keys.passthrough("auth","/principals/{sub}")` | `GET /api/v1/auth/principals/{sub}` [31 §8] | **C** | Name resolution for `claimed_by`, `adjudicated_by`, `second_adjudicator` |

**Query 2 is setting C and is refetched only on open, on a `412`, and after a successful mutation** [50 §5.4]: *"[30 §4.6] passes the owner's `ETag` through verbatim and it is the concurrency mechanism; refetching under the operator would silently replace the `ETag` they are about to submit."* This is the single most important freshness decision on the screen.

### 15.3 `QueueFilter` — twenty-two parameters, drawn and wired

[30 §4.5](30-gateway.md) declares twenty-two named parameters on `GET /proposals`. All of them are exposed, **all of them live in the URL under the operation's own names** [50 §4.4], and none is renamed. `QueueFilter` uses Radix `Select` [50 §3.2] for closed vocabularies, native checkboxes for booleans, and a native `datetime-local` producing an explicit offset for the one instant.

| Parameter [30 §4.5] | Control | Values |
|---|---|---|
| `status` | Multi-select, repeatable | `ProposalStatus` [03 §7.2]: `proposed \| claimed \| approved \| rejected \| superseded \| expired`. **Default `proposed`** — WF's box label is `Pending proposals` |
| `kind` | Multi-select, repeatable | `ProposalKind` [03 §7.2]: `anomaly_tag \| work_candidate \| requisition \| interval_change \| redesign_case \| configuration_change \| purge \| rewrap` |
| `target_sub_app` | Multi-select, repeatable | The nine slugs [09 §7.1], labelled with display abbreviations (§4.1's `src/display/`) |
| `authority_class` | Multi-select, repeatable | **Five values as [30 §4.5] declares them, not six** — §15.3's defect below |
| `blast_radius` | Multi-select, repeatable | `item \| asset \| class \| fleet` |
| `requires_dual_control` | Tri-state (unset / true / false) | Boolean |
| `awaiting_second_signature` | Tri-state | Boolean. *"`requires_dual_control` and one signature present"* — the second-signature worklist |
| `asset_id` | Identifier input | Canonical identifiers only [03 §3.3] |
| `system_id` | Identifier input | |
| `installed_item_id` | Identifier input | |
| `niin` | Identifier input | Pattern `^([0-9]{9}\|[A-Z]{2}[A-Z0-9]{7})$`, canonical `Niin` [10-shared-packages.md §4.1] |
| `class_id` | Identifier input | A string, not a UUID [20 §4.2] |
| `mission_id` | Identifier input | |
| `expires_before` | `datetime-local` + offset | RFC 3339 |
| `epoch_superseded` | Tri-state | **Labelled as a warning flag, not a filter** — [30 §4.5]: *"the staleness **warning** flag, not a filter the owner honours"*. The control's label says so, because an adjudicator who filters it out is hiding stale proposals rather than excluding them from the owner's consideration |
| `claimed` | Single-select | `any \| none \| me \| other`. `me` is resolved server-side; the console sends the literal and **does not substitute its own `subject_id`** |
| `flagged_non_program_evidence` | Tri-state | Boolean [03 §7.2 rule 1, D14] |
| `agent_id` | Text input, exact | |
| `agent_version` | Text input, exact | |
| `sort` | Single-select | §15.4 |
| `limit` | Numeric | Cursor pagination |
| `cursor` | **Not a control** | Held by the pager, never typed. Opaque [30 §4.4] |

**Two rules on the filter set as a whole:**

1. **Filtering is presentation, never a control.** [50 §9.4] and [31 §6.5]: *"[a] service that fetches rows and then drops them is in violation … the leak is in the count, the latency, and the cursor."* Every filter is sent to the server; **the console filters no row locally**, ever. `ui-no-client-side-queue-filter` (§19.1).
2. **No general-purpose text search.** [30 §4.5]: *"Filtering is by explicit named parameters only — no general-purpose query language on the public surface."* [30 OQ-7] declines free-text proposal search outright. `QueueFilter` has no free-text box and §4.4's lookup does not reach the queue.

**[AMENDMENT — resolved.]** The `authority_class` enum previously omitted `security_officer` here — [30 §4.5] declared five values against [03 §7.2.1]'s six, and [30 §8.1.2] in the same document already returned six, an internal contradiction. `30-gateway.md` §4.5 now declares all six. The control lists all six values the parameter accepts, `security_officer` included, exactly like every other role's filter — no stated exclusion, no `422` risk, and no need for the `?kind=purge&kind=rewrap` (§5.5) substitute, which remains available as a narrower alternative but is no longer the only way to select this work.

**Filter state is the URL**, so a filtered queue is linkable [50 §4.4]. `NormalizedQueueParams` (§3.3) sorts repeatable values and drops empty ones so that two orderings of the same filter produce **one** cache entry — otherwise setting **B**'s 30 s poll runs twice against one screen.

### 15.4 Sort, and the label that must not be written

[30 §4.4](30-gateway.md)'s three orders, and the reason there are only three is the clock discipline, not an omission: [03 §5.4] permits ordering only on `(producer, producer_node, monotonic_seq)` or the HLC, and [11 §11.5] gate 4 forbids sorting on `recorded_at`, `occurred_at`, or `source_time` at all.

| `sort` | Key | Label rendered | Default |
|---|---|---|---|
| `expiry` | `(valid_until ASC, projection_seq ASC)` | **`Act before — soonest expiry first`** | **Yes** |
| `confidence` | `(confidence DESC, projection_seq ASC)` | **`Agent-asserted confidence`** — [30 §4.4]: *"Presented as the agent's claim, never as a priority"* | No |
| `learned` | `(projection_seq ASC)` | **`Order the queue learned of them`** | No |

**`learned` must never be labelled "oldest first,"** and this is a correctness rule, not a wording preference. [30 §4.4] and [30 §12.4 DO-NOT 31]: under the scripted six-week single-SSN disconnection [06 §4, 13 §15], *"a proposal created afloat in week 1 arrives at the gateway in week 7 and takes a `projection_seq` after everything created ashore in the interval. Labelling that 'oldest first' would systematically bury exactly the afloat proposals the edge-scope decision exists to capture (D8)."* `ui-learned-sort-label` [50 §10.2] asserts it, and the label above carries the fact in the words the operator reads.

**`ApproximateTime`** [50 §3.5] governs every rendering of `announced_recorded_at`, which [30 §4.4] permits *"**only** alongside `announced_dispersion_ms`"* and forbids as a precise time *"when dispersion exceeds the inter-arrival interval."* `[ESTABLISHED HERE]`: the component takes both fields as required props — so it is structurally impossible to render one without the other — and renders *"recorded approximately <instant> (±<dispersion>)"*, which is also [33 §6.4] rule 5's mechanism (*"'on or about patrol day 21 (±6 h)' — and never with false precision"*). `ui-approximate-time` [50 §10.2].

**Cursor pagination**, per [30 §4.4]: opaque base64url over `(sort, sort_key_value, projection_seq)` **plus a projection-generation token**. A pre-rebuild cursor is rejected with `400 urn:fathom:problem:gateway:cursor-generation-stale`, and `[ESTABLISHED HERE]` the console handles it by **discarding the cursor and refetching page one with a stated notice**, never by retrying the stale cursor and never silently — [30 §4.4] built the token *"so a cursor issued before a rebuild is rejected … rather than silently skipping or repeating rows,"* and a console that swallowed the 400 would restore the silence. **No total count is requested or rendered** [30 §4.4, 03 §4]; WF's `Pending proposals — 7` renders as `n shown`, on §6.3's KPI-3 reasoning.

**`QueueFreshnessNotice`** renders whenever `queue_freshness.stale === true` [30 §4.5, §4.7], from `{classification_level, lag_seconds, stale, staleness_bound_seconds, completeness}`. Three of its members are rendered for specific reasons [30 §4.5]:

- `lag_seconds` against `staleness_bound_seconds` (300 [30 §4.7]) makes [03 §5.2]'s *"consumer staleness is observable"* visible to the human. [30 §4.7] is explicit that the API deployment *"must not fail readiness on projection lag"* and instead *"reports lag in the response … The operator sees 'this queue may be incomplete'; the fleet view still loads."* The notice is that sentence, rendered.
- `completeness: "level_scoped"` and `classification_level` implement [06 §5] rule 3's *"a low-side rollup never presents itself as complete"* for the queue. **The notice states the level the queue is scoped to, always — not only when stale.** `ui-queue-freshness-rendered` [50 §10.2] covers the stale case; `[ESTABLISHED HERE]` extends the level disclosure to every render, because a queue that says nothing about its scope is claiming completeness it does not have.

### 15.5 Box 1's five columns, and box 2's panel

**Box 1**, from `items[]` [30 §4.5]:

| WF column | Field | Rendering |
|---|---|---|
| `Kind` | `kind` | `StatusChip tone="neutral"`, value verbatim. WF renders bare text; a chip is [50 §3.2]'s component for a closed vocabulary |
| `Target` | `target_sub_app` | Display abbreviation [09 §7.1] — WF's `PMA`, `Scheduling`, `Design Advisory` are exactly those. **`subject` renders beside it**, and §15.5's defect below |
| `Authority required` | `authority_class` + `requires_dual_control` | §15.6 |
| `Blast radius` | `blast_radius` | `StatusChip tone="neutral"`, verbatim |
| `Status` | `status` | `StatusChip`. Tones: `proposed` → `warning`, `claimed` → `neutral`, `approved` → `good`, `rejected` → `neutral`, `superseded`/`expired` → `neutral`. **Word mandatory** [50 §8.3]. **PMA contributes a value the enum does not have**: [23 §3.7] states *"[t]he gateway renders an admitted agent proposal as **`claimed_by_review`**, not `proposed`"* — so the console handles that value and renders it distinctly, and §22 row 62 asks [03 §7.2] whether it belongs in `ProposalStatus` |

Additional row content, all from `items[]` [30 §4.5] and all rendered because a row without them is not adjudicable:

- **`NonProgramEvidenceFlag`** on `non_program_evidence_only: true`, **outside any collapsed region** [50 §11.2, `ui-non-program-evidence-not-collapsible`]. [30 §2.4]: *"[t]he one thing an adjudicator must see before opening is whether the proposal rests solely on non-program content"* [D14].
- **`valid_until` and `expires_within_hours`**, the latter a computed presentation flag [30 §4.5]. It is the default sort key and the operational urgency.
- **`baseline_id` / `baseline_epoch`**, and `epoch_superseded` as a `StatusChip tone="warning"` where set — [03 §7.2]'s re-validation rule means a superseded epoch will be rejected at adjudication, and an adjudicator should know before claiming.
- **`evidence_count`**, `confidence` (labelled as the agent's claim, §15.4), `agent_id`, `agent_version`, `trace_ref`.
- **`subject_provisional`** as a chip — an identity minted afloat [20 §4.5.1] that has not resolved.
- **`classification`** — `{level, cui_categories, dissemination}` [30 §4.5] — rendered per row where it differs from the banner's, with `dissemination` **in [03 §7.3]'s declared order, never alphabetized** [50 §11.4 item 31].

**`subject`'s members are not enumerated anywhere.** [30 §4.5] shows `"subject": {}`; [30 §3.4] shows `{ "asset_id": "…" }`; [30 §4.3] rule 4 says *"the queue response carries both the provisional and the confirmed identifier when they differ"* **without naming either field**. WF's `Target` column shows only the sub-app, so the drawn sheet does not expose the defect — but an adjudicator needs to know *which item*, and §15.5's `redesign_case` drill-down needs a `case_id` from somewhere. §22 row 16, **blocking**. Interim: the `Target` cell renders the display abbreviation plus **every key/value pair present in `subject`**, generically, labelled by key. It is ugly and it is honest, and it degrades gracefully whichever members turn out to exist.

**Box 2 — `AdjudicationPanel`**, from query 2. [30 §4.6] returns *"the owner's `Proposal` — the full 03 §7.2 object with `payload`, `evidence[]`, and `rationale` — merged with the queue row's presentation flags, and **the owner's `ETag` passed through verbatim**."* It is **inline beside the queue, not a modal** [50 §3.2]: *"the evidence must remain readable while the queue is visible."*

`EvidenceSummary` renders WF's *"Evidence: 3 records · 1 causal finding (moderate strength) · source_trust: program"* from `evidence[] {kind, ref, excerpt?, relevance?, source_trust}` [03 §7.2]: a count per `kind` (`record | document_chunk | prediction | trace`), and **`source_trust` per item** (`program | vendor | external` [D14]), never aggregated into one label. WF's *"(moderate strength)"* is an evidence-strength band belonging to Failure Intelligence and **sheet 08's `EvidenceStrengthBar` is explicitly out of scope** [50 §3.2]; where a `causal_finding` citation carries a strength, the console renders it **verbatim and never re-banded or upgraded** [WF sheet 09: *"Causal findings are cited at their original evidence strength — never upgraded"*]. `[ESTABLISHED HERE]`

**`rationale` renders verbatim as untrusted text, escaped, and never as a system statement.** An agent-authored rationale in a panel that also renders program facts must be visually attributed to the agent — `agent_id`, `agent_version`, `llm_version`, `trace_ref` [03 §7.2] adjacent to it. `[ESTABLISHED HERE]`

**The `redesign_case` drill-down.** Where `kind === "redesign_case"`, the panel additionally renders query 3, `GET /api/v1/gateway/views/redesign-case/{case_id}` [30 §3.2] — the view added *"[to close] `42-redesign-case-builder.md` §18 item 13: An adjudicator opening a `redesign_case` from the queue has no composed drill-down."* Its five fragments are `redesign_case` (**required**), `dossier` (**required**), `impact_snapshot`, `cost_estimate`, `causal_findings` (phase 1). The panel renders the two required fragments as a summary and the three optional ones through §3.5's outcome contract, with **`DegradedFragmentNotice` where a fragment is unavailable — never an empty impact section**, because an adjudicator reading a blank impact panel would conclude there is no impact. **Its 4000 ms budget is marked `[NOT SOURCED]`** in [30 §3.2] (*"borrowed by analogy"*), so the panel renders its own elapsed-time indicator monotonically and does not retry a timeout automatically.

### 15.6 Dual control, and the two signatures

**Authority display.** WF's `fleet_authority [chip critical] dual control` maps to `authority_class` + `DualControlBadge` on `requires_dual_control`. Two rules:

1. **`authority_class` is *a* representative required authority, not *the* required authority, and the label says so.** [03 §7.2.1]: *"Some cells accept more than one class … `Proposal.authority_class` itself records one representative value from the cell — for display, audit, and queue filtering — and is re-validated against the full allow-set, not against that single recorded value, at adjudication time."* The cell renders `authority_class` with the header `Authority (representative)`. `[ESTABLISHED HERE]`, and it matters because `work_candidate` at item scope accepts `maintainer` **or** `planner` and a `maintainer` reading `planner` in that cell would wrongly conclude they cannot act.
2. **`DualControlBadge` is `tone="critical"` as drawn and that is correct here** — it is not a severity band but a marking that an irreversible-class control applies, and [03 §7.2] makes dual control *"mandatory at class and fleet scope and for any kind with external legal effect,"* that set being `{requisition}`.

**The signature state, from three fields plus one computed flag** [30 §4.5]: `adjudicated_by`, `second_adjudicator`, `requires_dual_control`, `second_signature_outstanding`.

| State | Rendering | Button |
|---|---|---|
| `requires_dual_control: false` | No badge | `Approve` |
| `true`, `adjudicated_by: null` | `DualControlBadge` reading `dual control · 0 of 2` | **`Approve — signature 1 of 2`**, which is WF's own label |
| `true`, `adjudicated_by` set, `second_signature_outstanding: true` | Badge `dual control · 1 of 2`, with `adjudicated_by` name-resolved (query 4) and `adjudicated_at` | **`Approve — signature 2 of 2`**, and it is **disabled with a stated reason when `adjudicated_by === session.subject_id`** — [30 §4.6] makes *"whether dual control is satisfied by two **distinct** adjudicators … the owner's determination"*, so the console **still sends the request if activated** and renders the owner's refusal [50 §9.4]. The dimming is advice; the refusal is the control |
| `true`, both set | Badge `dual control · 2 of 2 — complete` | No approve button |

**`AdjudicationConfirm`** (Radix `AlertDialog` [50 §3.2]) wraps every adjudication [50 §5.6] and states **which signature this is** for dual-control proposals [03 §7.2.1]. `AlertDialog`, not `Dialog`: it requires an explicit action, does not dismiss on outside click, and takes `role="alertdialog"` with a required description.

**Enablement comes from advice and never from a local rule.** [31 §8]'s `POST /authority-checks` exists *"so the gateway can render a queue without enabled-looking rows nobody may act on,"* with `advisory: true`. The console **may** dim on that advice, **must still send** if activated, and **must render the server's refusal** — [31 §3.5]'s `urn:fathom:problem:auth:not-authorized` with its `reasons` — rather than pre-empting it [50 §9.4]. **The console never evaluates [03 §7.2.1]'s minimum-authority table itself**: [31 §6.4] generates `authority_matrix.json` server-side from that table and [50 §13 row 18] records that `security_officer` *"appears in no cell"* of it, so a console-side copy would be both a duplicate policy and a wrong one. `ui-no-local-authority-matrix` (§19.1). §22 row 63 carries [50 §13 row 18] forward — it is **still open**.

### 15.7 The two mutations

**Claim.** `POST /api/v1/gateway/proposals/{proposal_id}/claim` [30 §4.5].

| Requirement | Rule |
|---|---|
| `Idempotency-Key` | **Required** [30 §4.5], a client-generated UUIDv4 **generated once per user action and reused across every retry** [50 §5.6]. `ui-idempotency-key-stable-across-retries` [50 §10.2]. Regenerating it on retry defeats the mechanism |
| Body | **`[GAP]`** — [30 §4.5]/§4.6 describe no request body for claim. The console sends none, and §19.3's contract test asserts the committed OpenAPI agrees. §22 row 64 |
| Lease semantics | The gateway *"does not implement the lease"* [30 §4.6]; claim state reaches the queue only through projection and the detail fetch. **The console does not optimistically mark the row claimed** [50 §11.3 item 24] |
| On success | Invalidate `keys.proposals.list` and `keys.proposals.summary`; refetch `keys.proposals.detail` |

**Adjudicate.** `POST /api/v1/gateway/proposals/{proposal_id}/adjudicate` [30 §4.5].

| Requirement | Rule |
|---|---|
| `If-Match` | **Required**, the `ETag` from the `GET /proposals/{proposal_id}` the operator is looking at, **forwarded unchanged**. [30 §4.6]: *"`If-Match` is forwarded verbatim and never synthesized … the gateway must never supply an `If-Match` value of its own."* The console never synthesizes one and never regenerates an `ETag` [50 §11.3 item 23] |
| `Idempotency-Key` | **Required**, same rule as claim |
| **Request body** | **`[GAP]`, and it blocks the buttons.** [30 §4.5] and [30 §4.6] give the path, the two headers, and the three inviolable proxy rules — **and no body field names.** There is no `decision`, no `disposition`, no `adjudication_note` on the gateway's operation; [30 §2.4] mentions `adjudication_note` only as a `FORBIDDEN_FIELD` for the gateway's own *store*. [03 §7.2] has `adjudication_note` on the `Proposal` aggregate, and the owners' operations vary ([23 §3.7] uses `POST /proposals/{id}/adjudicate`; [32 §10.5] uses `PATCH /proposals/{id}`). **The console cannot construct the request.** §22 row 17, **blocking sheets 07, 10, and 11's approve and reject actions** |
| `412` | The proposal moved. **Refetch the detail, re-render, and require the operator to re-confirm — never auto-resubmit** [50 §5.6, §11.3 item 23]. [03 §7.2]: *"[w]ithout this the eventually-consistent queue permits two approvals and two work orders."* `ui-412-requires-reconfirm` [50 §10.2] |
| `428` | **A client defect, not a runtime path.** `ui-adjudicate-sends-if-match` [50 §10.2] fails the build; the console does not handle it at runtime |
| `403 not-authorized` | Rendered with its `reasons` [31 §3.5]. Not pre-empted (§15.6) |
| `403 agent-may-not-adjudicate` | [31 §3.5 step 6] — cannot arise from a human session, handled so it is never silently swallowed [50 §5.6] |
| `409` / `429` | `409` renders `ProblemDetail`; a `429` **is never stored as an idempotent outcome** and a retry with the same key executes normally [30 §6.5], so the console retries after `Retry-After` **with the same `Idempotency-Key`** |
| On success | Invalidate `keys.proposals.list` and `keys.proposals.summary`; **do not optimistically update the row** [50 §5.6]. Announce the outcome in the shell's polite live region (§4.6) |

**The interim while §22 row 17 is open, `[ESTABLISHED HERE]`:** the approve and reject buttons **render, disabled, with the reason stated** — *"adjudication request body is unspecified; see 51 §22 row 17."* They are not hidden (a hidden control is an unexplainable absence) and they do not send a guessed body (a guessed field name on an irreversible action is the worst available outcome). The claim button works, so containment (§16.3) and the read path are fully exercised.

---

## 16. Sheet 11 — Remediation & Purge Queue

**Routes:** `/audit/remediations` and `/audit/remediations/:proposalId`. **Component:** `RemediationAndPurgeQueue` in `src/features/audit/`. `audit` is the platform slug and `remediations` matches [03 §15 obligation 17]'s `POST /{slug}/remediations` [50 §4.2].

### 16.1 What the wireframe draws

| # | WF element | Content as drawn |
|---|---|---|
| 1 | `.sheet-note` | *"**No agent may ever create or adjudicate a `purge` or `rewrap` proposal — no exception.** … because the act is classification-adjacent and irreversible, not operational (doc 03 §7.2.1, §7.2)."* |
| 2 | `.box` + `.table-scroll` | label `Pending remediations — 2`; columns `Kind` · `Store` · `Blast radius` · `Signatures` · `Status`. Row 1: `purge` · `telemetry read model` · `item` · `security_officer — 1 of 1` · `[chip warning] proposed`. Row 2: `rewrap` · `audit + 4 read models` · `class` · `security_officer + [chip critical] fleet_authority ctr-sig` · `[chip neutral] claimed` |
| 3 | `.col.box` | label `Adjudication panel — purge, item scope`; text *"Selector: installed_item_id = A19381 · classification: spillage remediation · reason: mislabeled payload"*; buttons `Approve — execute purge` (primary) and `Reject`; note *"Item/asset scope: `security_officer` + dual control. Class/fleet scope adds a `fleet_authority` counter-signature."* |
| 4 | `.col.box` | label `Dissemination ledger — who holds a copy`; columns `Holder store` · `Node` · `Materialized`. Three rows, the third `edge:SSN-796` · `[chip neutral] pending ack`. Note *"Populated from every inbox apply and every `changed_since` rebuild — **not omniscient, and the receipt says so**"* |
| 5 | `.box` | label `Signed receipt — purge PRG-00441`; columns `Store` · `Legally immutable / append-only` · `Mechanism`. Three rows. Note *"Vector embeddings are the one documented exception to crypto-shred …"* |

Components [50 §3.5]: `SheetFrame`, `SheetNote`, `Box`, `WfTable`, `WfTableScroll`, `StatusChip`, `AdjudicationPanel`, `AdjudicationConfirm`, `Button`, `DisseminationLedgerTable`, `ReceiptTable`.

### 16.2 Data wiring

| # | Query | Operation | Setting | Feeds |
|---|---|---|---|---|
| 1 | `keys.proposals.list({kind:["purge","rewrap"],status:["proposed","claimed"]})` | `GET /api/v1/gateway/proposals?kind=purge&kind=rewrap&…` [30 §4.5] | **B** | Box 2 |
| 2 | `keys.proposals.detail(proposalId)` | `GET /api/v1/gateway/proposals/{proposal_id}` [30 §4.6] | **C** | Box 3 |
| 3 | `keys.passthrough("audit","/purges/{id}")` | `GET /api/v1/audit/purges/{id}` [32 §10.5] — *"State machine, sealed closure, per-store receipts, pending nodes"* | **B** | Boxes 2, 4, 5 |
| 4 | `keys.passthrough("audit","/purges/{id}/certificate")` | `GET /api/v1/audit/purges/{id}/certificate` [32 §10.5] — the §6.6 certificate with §5.9's four proofs, a **query-projection carve-out** | **C** | Box 5 |
| 5 | `keys.passthrough("auth","/principals/{sub}")` | `GET /api/v1/auth/principals/{sub}` [31 §8] | **C** | Signature name resolution |

**The queue filter is `kind`, not `authority_class`** — §5.5 and §15.3's defect. `?kind=purge&kind=rewrap` selects exactly [03 §7.2.1]'s two `security_officer` rows.

**Boxes 4 and 5 exist only once a purge record exists.** [32 §6.2]'s seven phases put closure sealing at **phase 3 (ENUMERATE)**, which follows **phase 2 (CONTAIN)**, which is triggered *"[o]n CLAIM of the proposal (before adjudication)."* So a `proposed` purge has no `purge_id`, no sealed closure, and no receipts — boxes 4 and 5 render `EmptyState` naming the phase. §16.5 and §16.6.

### 16.3 The purge protocol, made visible

The console renders `purge.state` [32 §6.7] because a security officer's screen must show where in an irreversible protocol a purge stands:

```
proposed → claimed → adjudicated → executing → verifying
                                       ├─▶ certified          (all holders complete)
                                       ├─▶ certified-partial  (≥1 pending-at-node)
                                       └─▶ aborted            (closure grew; §6.2 ph.4)
```

Three renderings are mandatory, `[ESTABLISHED HERE]` and each from an explicit obligation:

1. **`certified-partial` is never rendered as "complete."** [32 §6.7]: *"`certified-partial` is never displayed, logged, or reported as 'complete.'"* `StatusChip tone="warning"` reading `certified-partial`, never `certified`, and never a checkmark. `ui-certified-partial-not-complete` (§19.1).
2. **[32 §6.7] states a direct UI obligation and the console discharges it**: *"the operator interface shows the pending set with the node identity and the elapsed duration."* Box 4 renders `holder_node` per pending row **and its elapsed duration**, measured monotonically [50 §5.4] from the instant the console first observed the pending state, with the server-side `applied_at`/`purged_at` [32 §4.6] shown as instants. **WF draws the node identity and not the elapsed duration**; §22 row 18.
3. **`aborted` renders with its reason.** [32 §6.2] phase 4: *"recompute the closure and compare to the sealed set. Growth → ABORT"* and a growth beyond the adjudicated scope *"requires a new proposal"* [32 §6.1]. An aborted purge that reads as merely "failed" invites a retry of an act that must be re-proposed.

**The claim button is prominent and its consequence is stated, because a claim is not a neutral act here.** [32 §6.2] phase 2: on claim, *"the coordinator issues `POST /{slug}/remediations {action: quarantine}` to every holder in the provisional closure. Quarantine **DENIES READS and BLOCKS FURTHER DERIVATION**; it destroys nothing and is fully reversible."* `AdjudicationConfirm` on the **claim** — not only on the adjudication — states exactly that: reads will be denied across the closure, nothing is destroyed, and the action is reversible. `[ESTABLISHED HERE]`, and it is the one place in the console where a *claim* needs a confirmation dialog. [32 §6.2] explains why the ordering is right: *"[a] protocol that waits for full authority before doing anything lets the closure grow while the paperwork moves."*

### 16.4 The `Signatures` column, and the three-signature purge the queue cannot represent

[03 §7.2.1]'s minimum-authority table, purge/rewrap rows, and [32 §6.1]'s expansion of them:

| Blast radius of the closure | Required authority [32 §6.1] |
|---|---|
| `item` / `asset` | `security_officer` **+ a second, distinct `security_officer`** (two-person integrity) |
| `class` / `fleet` | The above **+ `fleet_authority` counter-signature** |
| Closure includes a `legally-immutable` record | The above **+** automatic conversion to a **re-wrap** [32 §5.10]. *"Destruction of a legally-immutable record is not an available action at any authority level"* |
| Closure includes a record under `legal_hold` | **Refused.** The hold is released first, by the authority that set it, as its own adjudicated act |

**[AMENDMENT — resolved.]** This row previously found the queue row modeled only two signatures where a class/fleet purge needs three — `items[]` carried `adjudicated_by`, `second_adjudicator`, and the computed `second_signature_outstanding`, with nothing to hold a counter-signature distinct from the second signature. `03-integration-contracts.md` §7.2's `Proposal` now carries `counter_signature_by`/`counter_signature_at`, propagated to `10-shared-packages.md`'s model and to `30-gateway.md` §2.4's `proposal_queue` columns and §4.5's response (both already rendered `counter_signature_by`/`counter_signature_at` as of that fix — the schema behind them was the missing half). A `rewrap` at class scope requiring `security_officer` + a second `security_officer` + a `fleet_authority` counter-signature now has three signatories and three fields.

**And WF row 1's `security_officer — 1 of 1` contradicts [03 §7.2.1] directly**: item/asset scope requires `security_officer` **+ dual control**, which is two of two, not one of one. §22 row 65.

`[ESTABLISHED HERE]`, the honest interim rendering:

| Condition | `Signatures` cell |
|---|---|
| `blast_radius` `item` or `asset` | `security_officer · <n> of 2` from `adjudicated_by`/`second_adjudicator`, both name-resolved |
| `blast_radius` `class` or `fleet` | `security_officer · <n> of 2` **plus a `StatusChip tone="critical"` reading `fleet_authority counter-signature required — state not represented in the queue`**, with the §22 row 19 reference in its title. The console **does not infer** the counter-signature's presence from `second_adjudicator`, because a second `security_officer` and a `fleet_authority` counter-signer are different people discharging different obligations and conflating them would report a two-signature purge as fully authorized |
| The proposal's detail (query 2) carries the owner's own signature record | Rendered from the owner's `Proposal` in preference to the queue row's projection — [30 §4.6] returns the owner's full object, and the owner is the authority [30 §4.6: *"whether dual control is satisfied by two **distinct** adjudicators … [is] the owner's determination"*] |

**The agent prohibition renders, verbatim.** WF element 1's `sheet-note` is production content on this sheet — it is the system stating a limit of its own authority, which is [50 §2.2]'s sanctioned use of the annotation voice. [03 §7.2] and [32 §6.1] make it absolute: *"[a] purge or rewrap proposal may never be created or adjudicated by an agent principal or an `accountable-autonomous` identity, with no exception … because the act is irreversible (§13) and classification-adjacent rather than operational."* And [32 §6.1] adds the concrete refusal: the coordinator *"rejects any proposal whose principal's `fathom.agent.authority` claim is `accountable_autonomous` … and any proposal carrying an `agent_id`."* `[ESTABLISHED HERE]`: **a row on this sheet carrying a non-null `agent_id` renders a `ProblemDetail`-class fault notice, not a normal row** — its presence means a prohibition was violated upstream, and the console makes it visible rather than rendering it as ordinary work. `ui-purge-row-with-agent-id-is-a-fault` (§19.1).

### 16.5 Box 3's panel, and the `Store` column with no field

**Box 3.** WF's *"Selector: installed_item_id = A19381 · classification: spillage remediation · reason: mislabeled payload"* comes from the `Proposal` (query 2) [03 §7.2]: `subject` (the selectors), `payload`, `evidence[]`, `rationale`, `classification`.

Three rules specific to a purge proposal, from [32 §6.1]:

1. **`evidence[]` must include the spillage report** — *"the incident reference, the mislabeling determination, and its authority — with `source_trust: program`. A purge proposal resting on non-program evidence is refused, not merely flagged."* `EvidenceSummary` renders each item's `source_trust`, and a non-`program` item on this sheet renders as a fault, not a `NonProgramEvidenceFlag` — the flag means "an adjudicator should know"; here it means the proposal should not exist.
2. **`valid_until` is mandatory and short** (default 72 hours). Rendered prominently with `expires_within_hours`, because *"[t]he closure is recomputed and re-sealed at adjudication, and a growth beyond the adjudicated scope aborts the purge."*
3. **The classification label of what was purged is retained and rendered**, including `inherited_from[]` and **the mislabeling correction** — [32 §6.6]: *"[t]he label is metadata and is the evidence of the spillage. Destroying it destroys the reason for the purge."* And **no excerpt, quotation, field value, or paraphrase of the purged content is ever rendered**: [32 §6.6] permits only *"[a] **category** description"* because *"[a] quotation would recreate the spillage inside the record of its remediation."* `ui-no-purged-content-excerpt` (§19.1) asserts the panel renders no `excerpt` member for a `purge`/`rewrap` proposal — which is a real risk, because `evidence[].excerpt` exists on the shared `Proposal` shape [03 §7.2] and every other sheet renders it.

**Box 2's `Store` column has no field, at the state the row is in.** WF draws `telemetry read model` and `audit + 4 read models`. The store set is the **sealed closure**, written as `purge_target` rows at phase 3 [32 §6.2] and served by `GET /purges/{id}` [32 §10.5] — which does not exist for a `proposed` proposal (§16.2). `Proposal` [03 §7.2] carries `target_sub_app` (always `audit` for a purge [32 §6.1]) and `subject`, whose members are unnamed (§15.5). §22 row 66.

`[ESTABLISHED HERE]`: the column header becomes **`Closure`** and renders three states — `not yet enumerated (claim to compute)` for `proposed`; the sealed store list from query 3 for `claimed` and later; and `aborted — closure grew` where applicable. WF's drawn value is the phase-3-and-later state, and labelling the column `Closure` makes the empty case legible instead of looking like missing data.

### 16.6 Box 4 — the dissemination ledger, which has no read operation

[32 §4.6](32-audit.md) defines the `dissemination` table — `source_event_id`, `holder_slug`, `holder_node` (`'enterprise' | 'edge:<asset_id>'`), `holder_store`, `applied_at`, **`materialized`**, `purge_receipt_id`, `purged_at` — and calls it *"the single most important addition this document makes to the platform."*

**No operation exposes it.** [32 §10.4]'s provenance surface is `GET /lineage/{record_id}`, `GET /lineage/{record_id}/dependents`, and `POST /lineage/closures` — the last *"[c]ompute-only. A closure over a selector set, with per-store holder resolution from the dissemination ledger."* There is **no `GET /dissemination`**, and a compute-only `POST` is a poor fit for a screen box: it is a mutation-shaped read that TanStack Query would treat as a mutation and that has no cache key of its own. §22 row 67.

`[ESTABLISHED HERE]`, the interim, and it is the correct source for this box anyway: **box 4 renders from query 3, `GET /purges/{id}`**, which [32 §10.5] states carries *"State machine, sealed closure, per-store receipts, **pending nodes**."* That is exactly WF's three columns plus the pending state:

| WF column | Field | Rendering |
|---|---|---|
| `Holder store` | `holder_store` [32 §4.6] | Verbatim, with `holder_slug` beside it — a `telemetry read model` and a `pdm read model` are different holders and the slug is what distinguishes them |
| `Node` | `holder_node` | Verbatim. `enterprise` or `edge:<asset_id>`; the edge form renders the hull where resolvable |
| `Materialized` | **`materialized`** | `StatusChip`: `yes` → `good`, `no` → `neutral`. **The `no` case is rendered with its meaning**, because [32 §4.6] is emphatic: *"`materialized` is the field that makes the ledger honest … A consumer that stored only the reference has no content to purge, and its purge is a no-op receipt — but the object store holding the artifact does have content, and it appears as its own ledger row. Conflating those two produces a certificate that purges nine read models and leaves the payload sitting in MinIO."* The chip's label reads `reference only` rather than `no` |
| *(added)* | pending nodes + elapsed duration | §16.3 rule 2's obligation |

**WF element 4's note renders verbatim** — *"not omniscient, and the receipt says so"* — because [32 §6.5] makes the limitation structural: *"[t]he dissemination ledger (§4.6) is good, not omniscient — a store commissioned yesterday, a cache nobody declared."* A ledger box that presented itself as complete would be the exact claim the note exists to refuse.

**On `/audit/remediations` with no proposal selected, box 4 renders `EmptyState`.** It is never rendered speculatively for a selector, because computing a closure is `POST /lineage/closures` and issuing a compute call on hover is not something this screen does.

### 16.7 Box 5 — the signed receipt and the four proofs

Query 4, `GET /purges/{id}/certificate` [32 §10.5], *"with §5.9's four proofs"*, and [32 §6.6] enumerates exactly what the certificate retains and what it does not.

| WF column | Field | Rendering |
|---|---|---|
| `Store` | `holder_store` per receipt | Verbatim |
| `Legally immutable / append-only` | The store's declared class [03 §13.3, 32 §6.3] | `StatusChip`: `legally immutable` → `warning` (WF's tone, and correct: it means destruction was **not available** and the record was re-wrapped instead), `append-only` → `neutral` |
| `Mechanism` | Per [32 §6.3]'s order table | Verbatim: `crypto-shred (KEK destroyed)`, `physical row delete + partition rebuild`, `re-wrapped upward, never shredded`. **WF's three rows are transcribed from that table and are rendered from the receipt, not from a client-side lookup** |

**`refused` is a legitimate outcome exactly once and renders as such.** [32 §6.6]: *"a selector resolving to a record the holder classifies `legally-immutable`. The holder names the records and the coordinator converts to `rewrap`."* A `refused` receipt renders `tone="warning"` with the conversion stated — **never `tone="critical"`**, which would read as a failure when it is the protocol working.

**The four proofs render as a list, not a badge.** [32 §5.9] via [32 §6.6], including the **HSM destruction receipt** — *"signed by the module: key handle, group id, destruction timestamp, operator identities under dual control, and the module's serial and firmware version"* — verifiable *"[b]y verifying the HSM's signature with the module's public key. No audit-service involvement."* `[ESTABLISHED HERE]`: **the console does not verify any signature.** It renders `receipt_signature` and `receipt_key_id` [32 §6.4] as present-or-absent facts and states who signed — [32 §6.4]: *"[t]he receipt is signed by the **holder**, so the certificate aggregates independently-attributable statements rather than audit's assertions about other services."* A browser-side signature check would be a verification claim made by unsigned JavaScript, which is worth nothing.

**WF element 5's `--annotation` note renders verbatim** — the vector-embedding exception, *"encryption would defeat the nearest-neighbor search it exists to serve, so purge here is physical deletion, never a key destroyed (doc 03 §13 item 5)"* — because it is the system stating a limit of its own remediation guarantee, which is the sanctioned annotation voice [50 §2.2].

**The certificate is append-only and never amended** [32 §6.6]; a **supplemental** certificate chained to the first is how a late-reconciling holder is recorded [32 §6.7]. `[ESTABLISHED HERE]`: box 5 renders **each certificate in the chain as its own table with its own seal instant**, never merged into one — merging them would present a six-weeks-later reconciliation as though it had been part of the original act.

### 16.8 Sheet 11 states

| Condition | Rendering |
|---|---|
| No proposal selected | Box 2 renders; boxes 3, 4, 5 `EmptyState` |
| `status: proposed` | Box 3 renders the proposal; boxes 4 and 5 `EmptyState` naming phase 3 (§16.2) |
| Query 3 `404` | No purge record yet. `EmptyState`, not an error |
| `purge.state: executing` / `verifying` | Boxes 4 and 5 poll at setting **B**; per-store receipts render as they arrive, with the pending set and elapsed durations (§16.3) |
| `certified-partial` | The `warning` chip, the pending set, and **never a completion indication** (§16.3) |
| `aborted` | The reason and the requirement to re-propose (§16.3) |
| A row with a non-null `agent_id` | A fault notice, not a normal row (§16.4) |
| A class/fleet row | The counter-signature-unrepresented chip (§16.4) |
| Adjudication buttons | **Disabled with the §15.7 reason** until §22 row 17 lands. On this sheet the disabling is least costly and most defensible: the act is irreversible and a guessed field name is not an acceptable risk |
| `403` on any audit read | `ProblemDetail` with the owner's body verbatim. `audit`'s own reads are ABAC-restricted and a security officer's screen showing a bare empty table would be worse than a refusal |

---

## 17. Loading, empty, unknown, suppressed, and error — the five renderings

[50 §5.5](50-ui-design-system.md) fixed three states and three components. This section adds the two that are not fetch states — a **suppressed** value and a **problem** — and gives the per-screen table.

| State | Component | Meaning | Never |
|---|---|---|---|
| **Loading** | `LoadingSkeleton` | The request is in flight | Never the hatch fill [50 §11.1 item 6] |
| **Empty** | `EmptyState` | The query succeeded and there is genuinely nothing: `outcome: "empty"`, or a zero-length collection | Never a zero |
| **Unknown / degraded** | `DegradedFragmentNotice` | The answer could not be determined: `timeout`, `unavailable`, `forbidden` | **Never a zero and never a bare dash** [30 §3.4] |
| **Suppressed** | `KpiTile` + `SheetNote`, from the reason field | The server determined the value must not be released, at HTTP **200** | Never `0`, never `100`, never blank [27 §3.9] |
| **Problem** | `ProblemDetail` | RFC 9457 [03 §4] | Never a generic message; never a swallowed error |

### 17.1 Fragment outcomes, per screen

Read through §3.5's `fragment()` function, never inline. `R` = required (its failure is a whole-view `503`).

| Screen | View | Fragments and their effect |
|---|---|---|
| 01 | `fleet_overview` | `readiness_rollup` **R** · `asset_status` **R** · `open_casrep_risk` → KPI 3 + every marker `neutral` (§7.4) · `availability_windows`, `proposal_counts` → unused (§6.7) |
| 01B, 02 | `asset_detail` | `asset` **R** · `configuration_baseline` **R** · `readiness` → KPIs 1, 4 degrade; chips, flags, buttons render · `predictions`, `open_work`, `parts_position`, `open_proposals` → unused here · `installed_items` (phase 1) → identifiers without nomenclature |
| 03, 04 | `installed_item_detail` | `installed_item` **R** · `prediction`, `health_indicators`, `usage_counters`, `maintenance_history`, `failure_modes` → per-box notice |
| 04 deep dive | `explanation_decomposition` | `prediction` **R** · `contributing_factors` **R** · `feature_observations` (phase 1), `causal_findings` (phase 1), `procedure_references` (phase 1) → per-box notice |
| 10 | `redesign_case_detail` | `redesign_case` **R** · `dossier` **R** · `impact_snapshot`, `cost_estimate` → notice, **never a blank impact section** · `causal_findings` (phase 1) → notice |

**`forbidden` is never escalated to a whole-view 403** [30 §3.4]; it renders as a per-fragment notice reading *"not available at your access level"* — which is a different statement from *"unavailable"* and must not be merged with it.

### 17.2 Classification and advisory faults

| Condition | Rendering |
|---|---|
| `502 urn:fathom:problem:gateway:classification-fault` | A **distinct, non-retryable** `ProblemDetail` for the whole sheet. Never a degraded view [30 §7.2: filtering and redacting *"[p]rohibited"*, refusing *"[r]equired"*, `failClosed` *"not overridable"*]. `ui-classification-fault-is-not-degraded` [50 §10.2] |
| A fragment's outcome is `classification_fault` | Same — the gateway returns `502` for the view [30 §3.4] |
| Missing `X-Classification` | Banner fault state. **Never a default to `U`** [50 §11.4 item 30] |
| A retired marking in a label | Banner fault state, and the marking is not rendered [50 §7.2 rule 3, §11.4 item 32]. `FOUO`/`U//FOUO` appear as a literal nowhere, including in a test fixture |
| Incomparable distribution statements in a union | `502 classification-fault` [30 §7.3]. The console does not guess [10 OQ-16] |
| `display_requirement: "must_be_surfaced"` with no `AdvisoryBanner` mounted | Development build throws; `ui-advisory-must-be-surfaced` fails [27 §8.1, 50 §7.3] |
| Advisory body and header both absent on a readiness sheet | §6.4's tier-3 degraded banner |

### 17.3 The suppressed-score rendering, which is drawn on no sheet

[27 §3.9](27-fleet-status.md) publishes two null-score cases, both at HTTP **200** and *"never conflated"*, and [50 §13 row 12] records that **neither is drawn on WF sheets 01 or 01B.** §22 row 68 keeps the wireframe edit filed.

| Condition | `KpiTile` renders | `SheetNote` renders |
|---|---|---|
| `score: null`, `suppression_reason: "all_contributors_restricted"`, `restricted_contributors_present: true` | **`not released`** as the value, `warning` tone | *"Every contributor to this score is above your access level. No score is computed for this scope at your level."* Plus the `contributor_disclosure.statement` verbatim |
| `score: null`, `suppression_reason: "no_contributors"`, `restricted_contributors_present: false` | **`not assessed`** as the value, `neutral` tone | *"No contributors have been assessed for this scope."* Plus `score_integrity.statement` verbatim |
| Coverage metric `null` with `suppression_reason` | Same two renderings [27 §7.6 rule 2: *"exactly as in §3.9"*] | Same |

**Never `0`, never `100`, never blank, and never the same text for both reasons.** `ui-null-score-reasons-distinct` [50 §10.2]. [27 §3.9] and [27 DO-NOT 4] state the stake: rendering `100` *"presents a fully compartmented, possibly failed asset as perfectly ready."* And [27 §10.4] adds the reciprocal rule the console must honour on the error path too: *"[n]o problem `detail` may name a compartment, a restricted contributor, a system, or a count beyond what `contributor_disclosure` already discloses"* — so `ProblemDetail` renders the server's `detail` verbatim and **never augments it** with anything the console inferred.

A `403 urn:fathom:problem:fleet-status:view-not-authorized` [27 §10.4] on `view=high_side` renders as `ProblemDetail` and **does not silently retry at `view=default`** — [27 §10.2] is explicit that the parameter *"does not silently downgrade"*, and a console that downgraded for the operator would answer a different question than the one asked.

### 17.4 Screen-by-screen state matrix

| Screen | Loading | Empty | Unknown | Problem |
|---|---|---|---|---|
| 00 shell | Identity skeleton; nav and routes render | — | Identity `ProblemDetail` inline | `404`/`401` → login affordance (the only full interception) |
| H hub | **Cards render unmarked** | `[]` roles = case 3, not empty | Unmarked + a stated reason | Shell intercepts |
| 01 | Per-box skeletons | `EmptyState` per box | Per-box notices; all markers `neutral` | `503`/`502` → whole sheet |
| 01B | Per-box skeletons | Per box | KPIs 1, 4 degrade; rest renders | `asset` fails → whole sheet |
| 02 | Box 1 skeleton | *"Select an asset"*, per box | Tree box notice | `422` at the bitemporal control |
| 03 | Sparkline skeleton at 90×26 | *"no values in window"* | Per-row | `403` per box |
| 04 | Table skeleton | *"no active predictions"* | Per-box | `whatif-capacity` → manual retry only |
| 05 | Per-box skeletons | *"Select an asset"* / *"No work package"* | Per-box | Five `409`s, each named |
| 06 | Per-box skeletons | *"no stock position"* ≠ `On-hand 0` | Per-box | `reservation-set-expired` → no retry |
| 07 | Candidate skeleton | `deferred_admission_control` explained | Per-box | Nine problem types, each named |
| 10 | Row skeletons | *"no proposals matching these filters"*, naming the filters | `QueueFreshnessNotice`; degraded `redesign_case_detail` fragments | `412` → re-confirm; `428` → build failure |
| 11 | Row skeletons | Phase-3 `EmptyState` for boxes 4, 5 | Pending set + elapsed | `403` → refusal, never a blank table |

**Two universal rules.** An `EmptyState` **always names what is empty and over what scope** [50 §5.5] — *"no proposals"* is not an acceptable string; *"no proposals matching status=proposed, kind=purge"* is. And **every error path renders the server's RFC 9457 body**: `type` (always a URN, never a dereferenceable URL [30 §8.5]), `title`, `status`, `detail`, `instance`, plus any extension members, with upstream problem bodies **never rewritten** [30 §8.4].

---

## 18. What this document does not build: sheets 08 and 09

### 18.1 The exclusion, stated

**WF sheet 08 (Hypothesis Adjudication, Failure Intelligence) and WF sheet 09 (Redesign Case Builder, System Test & Design Advisory) have no route, no component, and no query in `apps/web`, and this document designs none.** The basis is settled in four places and is not reopened here:

- [04 §9](../architecture/04-subapplication-architectures.md): *"Practitioner-facing causal exploration is a Domino App, since its audience is reliability engineers who hold Domino accounts."*
- [04 §10](../architecture/04-subapplication-architectures.md): *"Engineer-facing case review is a Domino App, since the audience holds Domino accounts and the workflow benefits from proximity to the causal analysis."*
- [28 §2 / §16](28-design-advisory.md) and [42 §13.3](42-redesign-case-builder.md) both already place their review surfaces in `apps/practitioner`, both citing [09 §2.6] constraint 2 and [02 §4.1].
- [50 §1.5](50-ui-design-system.md) confirmed the boundary by `grep` and [50 §4.3](50-ui-design-system.md) declared the exclusion *"a decision rather than an omission."*

**Their routes, internal navigation, components, data wiring, and Domino deployment specification belong to [52 — Practitioner Apps](52-practitioner-apps.md).** Two elements they contain are therefore **not** specified anywhere in this document and must not be built into `packages/ui` on this document's authority: the **evidence-strength bar** of sheet 08 [50 §3.2: *"**Out of scope.** Sheet 08 is a Domino App [04 §9]; the component belongs to 52"*] and the **dependency graph** of sheet 09 [50 §8.5: *"out of scope (§4.3); the same rules will bind it in 52"*].

**One thing this document does own that touches sheet 09's domain, and it is not that sheet:** the `redesign_case_detail` composed view (§15.5). [30 §3.2](30-gateway.md) added it *"[to close] `42-redesign-case-builder.md` §18 item 13: **An adjudicator opening a `redesign_case` from the queue** has no composed drill-down"* — and that adjudicator is on **sheet 10, in `apps/web`**. Rendering a `redesign_case` proposal's dossier inside the adjudication panel is not rendering sheet 09; it is rendering the queue's detail for one proposal kind. The two must not be conflated, and §22 row 20 records the view's addition to [50 §5.3]'s four-shape table so that [52](52-practitioner-apps.md) does not read it as its own.

### 18.2 The three outbound affordances `apps/web` does own

[50 §4.3](50-ui-design-system.md) named one: *"the two Persona Hub cards whose primary button launches them."* §4.2 found the third and fourth — **WF sheet 00's side nav lists `Failure Intelligence` and `Design Advisory` as nav items** — so there are four affordances across two surfaces, all using the one component.

| Affordance | Location | Component |
|---|---|---|
| `RE` card → Hypothesis Adjudication | Sheet H | `ExternalLaunch` |
| `DE` card → Redesign Case Builder | Sheet H | `ExternalLaunch` |
| Nav item `Failure Intelligence` | Sheet 00 side nav | `ExternalLaunch`, `NavItem`-styled (§4.2) |
| Nav item `Design Advisory` | Sheet 00 side nav | `ExternalLaunch`, `NavItem`-styled (§4.2) |

`ExternalLaunch`'s rules are [50 §9.5]'s, unchanged: the URL is `${VITE_PRACTITIONER_BASE_URL}/<surface>` — **build-time configuration, never a literal**, because [02 §4.1] records that Domino Apps are served *"from a single deployment-wide subdomain and iframed"* with *"[c]ustom URL paths only"* and *"[c]ustom domains: [n]ot supported"*, so the host is a per-deployment fact; a new tab with `rel="noopener noreferrer"`; an accessible name stating the destination **and** that it leaves the console (*"Open Hypothesis Adjudication — opens in Domino, in a new tab"*); **disabled with a stated reason** when the variable is unset, *never* a dead link and never a `#`; and **no return path**, because there is no cross-app session hand-off [50 §6.3] and inventing one would invent the mechanism [31 §2.2] warns against reasoning away.

**The `<surface>` path segments are `[OPEN]`.** [50 §9.5] specifies the shape and no document fixes the two values. `[ESTABLISHED HERE]`: they are **[52](52-practitioner-apps.md)'s to fix**, and until it does, `ExternalLaunch` targets `VITE_PRACTITIONER_BASE_URL` alone with the surface named in the accessible name and in the visible label. That reaches the practitioner application's own landing page rather than a wrong path, which is recoverable; a guessed segment is a 404 in a different application. §23 UI-OQ-51-1. The console holds **exactly one** practitioner-related environment variable and does not add a second per surface — two variables would be two places for a deployment to be half-configured.

**`ExternalLaunch` is the only outbound link in `apps/web`** [50 §4.3]. `ui-only-external-launch-leaves` (§19.1) asserts that no `<a>` with an off-origin `href` exists outside that component.

---

## 19. Testing

[09 §2.6](09-monorepo-and-conventions.md) fixes **Vitest + Testing Library** and [50 §10.1] adds `axe-core` (floor `>=4.10`, mirrored into the private index per [09 §2.2]'s air-gap rule) and an in-repo contrast assertion. **Nothing is changed.** [50 §10.2]'s named tests are contractual: *"51 and 52 add to the list and remove nothing."* This section adds.

### 19.1 New named tests

Grouped by what they protect. Each protects a rule this document states and each is named so a reviewer can cite it.

**Layout and imports**

| Test | Asserts |
|---|---|
| `ui-no-cross-feature-import` | No module under `src/features/<a>/` imports from `src/features/<b>/` (§2 rule 2) |
| `ui-no-feature-types-file` | No `types.ts` in any feature directory; no interface or type alias mirrors a response shape (§2 rule 5, [09 §2.6] constraint 1) |
| `ui-keys-are-central` | Every `queryKey` traces to `src/api/keys.ts`; no key literal appears at a call site (§3.3) |
| `ui-only-external-launch-leaves` | No off-origin `href` outside `ExternalLaunch` (§18.2) |

**Data access**

| Test | Asserts |
|---|---|
| `ui-no-direct-fragment-read` | `envelope.data` is indexed only inside `src/api/outcomes.ts` (§3.5 rule 1) |
| `ui-all-six-outcomes-handled` | Every screen backed by a composed view handles all six `FragmentOutcome` values; a missing case fails at type-check and at runtime (§3.5, §17.1) |
| `ui-pinned-queries-never-poll` | No `pinned(…)` key carries a `refetchInterval` (§3.3, §3.4) |
| `ui-bitemporal-pairs` | No request sends `as_of` without `as_known_at`, or vice versa (§9.4, [20 §6.3] `OAS-REG-1`) |
| `ui-never-sends-min-probability` | No request to `GET /predictions` carries `min_probability` (§11.2, [22 §10]) |
| `ui-no-research-predictions` | No reference to `/research/predictions`, `serving_class`, or `X-Fathom-Prediction-Use` (§11.3, [22 §4.5.2]) |
| `ui-no-quality-metrics-call` | No reference to `/quality-metrics` (§14.5, [23 §3.7]) |
| `ui-no-client-side-queue-filter` | No queue row is filtered, hidden, or dropped locally (§15.3 rule 1, [31 §6.5]) |
| `ui-no-cross-reference-class-sort` | A `p_failure` sort groups by `reference_class` first (§11.2, [03 §7.1]) |
| `ui-no-rate-limit-headers-read` | No reference to `X-RateLimit-*`; `Retry-After` is the only rate-limit signal read (§3.4, [30 §6.5]) |

**Rendering rules that are correctness rules**

| Test | Asserts |
|---|---|
| `ui-no-invented-banding` | No component maps a numeric to a status tone without a field carrying the classification (§6.8) |
| `ui-map-position-count` | `DEMO_POSITIONS` has `DEMO_POSITION_COUNT` entries, all within `AOR_VIEWBOX` (§7.2 rules 3, 6) |
| `ui-map-positions-match-fixture` | `DEMO_POSITIONS`' key set equals the committed synthetic fixture's `asset_id` set (§7.2 rule 5) |
| `ui-map-equivalent-table-is-per-asset` | `EquivalentTable` renders one row per asset in `asset_status`, not one per risk flag (§7.5) |
| `ui-map-neutral-is-fragment-wide` | A non-`ok` `open_casrep_risk` renders **every** marker `neutral` and a `DegradedFragmentNotice` (§7.4) |
| `ui-epoch-not-current-disclosed` | `epoch_is_current: false` renders the historical-baseline note; `allocated_high_water > current_epoch` renders the in-flight chip (§9.5) |
| `ui-hatch-not-insufficient-data` | An insufficient-completeness trend renders `EmptyState`, never `HatchFill` (§10.4) |
| `ui-completeness-zero-not-unobserved` | `completeness === 0` never renders as `not_observed` (§10.5, [21 §12.2 DO-NOT 21]) |
| `ui-gaps-enumerated` | `gap_intervals` render as rows, never as a scalar summary (§10.5, [21 §3.6]) |
| `ui-narrative-not-classification` | `reason_narrative` never renders in a reason-class position (§12.5, [24 §3.5]) |
| `ui-reason-code-verbatim` | `ReasonCell` renders `reason_code` verbatim from the sixteen-value vocabulary and never a paraphrase (§12.4, [24 §4.4]) |
| `ui-disposition-totality-surfaced` | A disposition count ≠ candidate count renders a fault notice (§12.4, [24 §4.4]) |
| `ui-by-condition-not-flattened` | Box 1 renders one row per `by_condition[]` entry; no position-level `on_hand_qty` is synthesized (§13.3, [26 §7.2]) |
| `ui-available-qty-not-recomputed` | `available_qty` is rendered as served; no subtraction anywhere (§13.3, [26 §2.3]) |
| `ui-lead-time-labelled` | Both `order_and_ship_time_days` and `procurement_lead_time_days` render, each labelled (§13.3, [26 §5.4]) |
| `ui-ttl-from-monotonic-delta` | `TtlCountdown` computes from `performance.now()` against a once-captured `expires_at`; no `Date.now()` (§13.4, D29) |
| `ui-ttl-does-not-assert-expiry` | At zero the countdown awaits a server `state` change (§13.4 rule 4) |
| `ui-no-canary-signal` | No identifier matching `canary`, `plant`, `origin`, `ground_truth`, `rank_stratum`, `rank_score`, `rank_components`, or `detector_score` appears in `src/features/pma/` (§14.2) |
| `ui-hub-skip-never-external` | `fathom.hub.skip` never holds an `ExternalLaunch` target, and an unrecognized value is discarded (§5.3) |
| `a11y-external-nav-no-current` | An `ExternalLaunch` inside `<nav>` never carries `aria-current` (§4.2) |
| `ui-certified-partial-not-complete` | `certified-partial` never renders as `certified` and never shows a completion indication (§16.3) |
| `ui-purge-row-with-agent-id-is-a-fault` | A `purge`/`rewrap` row with a non-null `agent_id` renders a fault notice (§16.4, [32 §6.1]) |
| `ui-no-purged-content-excerpt` | No `evidence[].excerpt` renders on a `purge`/`rewrap` proposal (§16.5, [32 §6.6]) |
| `ui-no-local-authority-matrix` | No component evaluates [03 §7.2.1]'s minimum-authority table locally (§15.6) |
| `ui-empty-state-names-its-scope` | Every `EmptyState` receives a non-generic scope description (§17.4) |

### 19.2 Route tests

One file per route in `tests/routes/`, each rendering the route inside a real `AppShell` and a real `QueryClient` against MSW handlers built from the **committed OpenAPI documents**, not hand-written fixtures. Each asserts, at minimum:

1. The route renders its sheet, with `document.title`, focus on the `<h2>`, and the polite announcement (§3.2).
2. `ClassificationBanner` **and** `ClassificationFooter` are present [50 §10.2 `ui-classification-footer-present`].
3. Every column, KPI, chip, and button the sheet's §-table lists is present, and **nothing else is** — the inverse assertion is what enforces [50 §11.2 item 12].
4. Each of §17.4's five states renders its own component, driven by an MSW handler per state.
5. `axe-core` reports zero violations of impact `serious` or `critical` [50 §10.1].
6. The route is reachable with `authority_classes: []` and renders no unauthorized messaging [50 §10.2 `ui-no-role-gated-route`, `ui-empty-roles-renders-all-cards`].

**Fixtures come from the committed synthetic reference dataset** [09 §8.5], at [06 §7]'s envelope — twelve assets, the three domains — so *"the map's twelve markers and the fleet rollup are exercised at the specified scale"* [50 §12.1].

### 19.3 Contract tests — how an SPA verifies wiring against a real contract

`apps/web` publishes no OpenAPI document, so [09 §8.5]'s conformance-suite item has no producer form here (§21.1). **The consumer form does exist and is the substance of this section:** every service document's pattern is a contract test against the committed specification, and the console runs the mirror image of it.

`tests/contract/` asserts, **against `packages/contracts/openapi/<slug>/openapi.json` and `platform/gateway/openapi.json` as committed** [09 §2.5, 30 §8.2 property 4: *"`platform/gateway/openapi.json` is generated and committed like every other service's … and CI fails on drift"*]:

| # | Assertion | Why it catches a real defect |
|---|---|---|
| 1 | **Every operation the console calls exists** in the committed document, at the exact path and method | A renamed upstream path is otherwise a runtime 404 in one screen |
| 2 | **Every query parameter the console sends is declared**, with the console's value inside the declared enum | This is the test that catches §15.3's `security_officer` case at build time rather than as a `422` in front of a security officer |
| 3 | **Every response field the console reads is declared** in the operation's response schema, walking the generated types | This is the join §1.4 performs, made continuous. A `[GAP]` becomes a failing test the moment the field lands, which is how §22's rows get closed rather than forgotten |
| 4 | **Every header the console sends or reads is declared**: `Idempotency-Key` and `If-Match` on the two mutations, `X-Correlation-Id` on everything, `X-Classification` and `Retry-After` on responses | `ui-adjudicate-sends-if-match` [50 §10.2] asserts the send; this asserts the contract accepts it |
| 5 | **No operation the console calls is `x-agent-eligible`-dependent or `internal`-only in a way the console violates** | The console is a human surface; calling an `internal` operation it has no business on is a boundary defect |
| 6 | **Every fragment name the console reads exists in [30 §3.2]'s registry** | §3.5's `operation_id` gap means fragment *shapes* are underivable; fragment *names* are not, and a renamed fragment is otherwise a silently empty box |
| 7 | **Every `urn:fathom:problem:*` type the console branches on is declared** in some committed document's `responses` | A problem type the console handles and the server never sends is dead code; one the server sends and the console does not handle renders a generic error |
| 8 | **No request URL is built by concatenating a route path** | §13.2's `/supply/parts/:niin` is a console path and not an API path; this asserts the two never fuse |

**Assertion 3 is the one that makes this document maintainable.** Its output is a report of every field the console reads that the contract does not declare — which is exactly §22's `[GAP]` list, regenerated on every CI run. `[ESTABLISHED HERE]`: the test emits that report as a committed artifact, `apps/web/contract-gaps.json`, and **CI fails when a gap is added and warns when one is closed**, so a landed amendment shows up as a diff rather than as a document nobody re-read.

**No end-to-end tool is adopted.** [50 UI-OQ-7] left it open, [09 §10 item 8] already raises load and performance testing for assignment, and inventing a Playwright estate here would be inventing scope. §23 carries it forward.

---

## 20. Explicit DO-NOT list

[09 §9](09-monorepo-and-conventions.md)'s thirty-two items and [50 §11](50-ui-design-system.md)'s forty-four apply **in full**. These are additional and screen-specific. Each carries the citation that makes it a defect rather than a preference.

### 20.1 Data and derivation

1. **Do not compute a readiness score, a rollup, a rank, or a coverage fraction in the browser.** Not per class (§6.6), not per hull (§8.3), not over a visible subset (§17.3). *(04 §5; 27 §3.2, §3.8, §7.6 rule 2; 50 §11.3 item 20)*
2. **Do not count an unbounded collection, and do not paginate to exhaustion to obtain a total.** Render `n shown` with its bound. *(03 §4; 32 §10.6; §6.3, §8.3)*
3. **Do not send `min_probability` to `GET /predictions`.** It silently drops the uncalibrated population, which is the population triage exists for. *(22 §10; §11.2)*
4. **Do not rank predictions by expected consequence with locally chosen weights**, and do not call `POST /expected-consequence` with invented `ConsequenceWeights` or `RiskPosture`. *(30 §2.4; 22 §7.2; 24 §4.4's `weights_are_illustrative`; §11.2)*
5. **Do not compare or sort `p_failure` across reference classes.** *(03 §7.1, D7; §11.2)*
6. **Do not recompute `available_qty`, or subtract across `by_condition[]` rows.** *(26 §2.3; §13.3)*
7. **Do not compute `duration_seconds` from `opened_at` and `completed_at`.** The field is monotonically measured and the subtraction is wrong. *(23 §2.1; §14.5)*
8. **Do not join across two composed views.** Joining two fragments of one envelope is permitted and is not this. *(30 §2.3 property 4; 50 §5.3 rule 6; §6.5)*
9. **Do not poll a bitemporally pinned read.** Two explicit instants name one immutable answer. *(20 §6.3; 21 §5.1; §3.3, §3.4)*
10. **Do not invent a polling interval.** Every query maps to one of [50 §5.4]'s three settings. *(§3.4)*
11. **Do not read an `X-RateLimit-*` header or render a quota gauge.** `Retry-After` is the only signal the gateway sets. *(30 §6.5; §3.4)*

### 20.2 Rendering

12. **Do not map a numeric to a status tone without a field that carries the classification.** No readiness band, no completeness band, no probability band, no TTL band, no queue-depth band. *(§6.8, §10.5, §13.4)*
13. **Do not render `--hatch` for insufficient data.** It means *"a figure belongs here and is not rendered."* *(50 §2.5, §11.1 item 6; §10.4)*
14. **Do not render a bare `▲ 2pt / 30d`-style delta.** Render `delta_attribution` with `exclusion_set_changed` disclosed; a score that moved for a clearance reason must not read as an engineering improvement. *(27 §3.11, §3.7; §6.3)*
15. **Do not render a coverage fraction without its denominator, distribution, chance reference, and achievable ceiling.** *(27 §7.5; §6.3)*
16. **Do not render `tier` as a branch, a tone, or an affordance condition.** Display it; branch on `reference_class`. *(03 §7.1; 09 §9.3 item 21; 50 §11.4 item 38; §11.3, §11.6)*
17. **Do not render `--accent` for a status, or a status colour for a control.** WF's `[chip accent] prediction` and `[chip accent] tier-3` are both defects. *(50 §2.2, §11.1 item 3; §11.6, §12.3)*
18. **Do not render a severity, disposition, state, or reason enum by paraphrase.** Sixteen `reason_code`s, nine rejection classes, five severities, four allowance states — all verbatim. *(24 §4.4; 23 §2.5; 27 §6.2; 26 §2.4; §12.4)*
19. **Do not summarize `gap_intervals`, and do not treat `completeness = 0` as `not_observed`.** *(21 §3.6, §12.2 DO-NOT 21; §10.5)*
20. **Do not render `held_not_authorized` as available stock.** *(26 §2.4; §13.3)*
21. **Do not render `proposed_allowance_qty` in the `Allowance` position.** *(26 §2.4; §13.3)*
22. **Do not render an unlabelled lead time.** The two fields select different procurement instruments. *(26 §5.4; §13.3)*
23. **Do not render `certified-partial` as complete, or an `aborted` purge as merely failed.** *(32 §6.7, §6.2; §16.3)*
24. **Do not render a `purge` proposal's `evidence[].excerpt`, or any quotation, field value, or paraphrase of purged content.** A category description only. *(32 §6.6; §16.5)*
25. **Do not merge a supplemental purge certificate into the original.** *(32 §6.6; §16.7)*
26. **Do not verify a signature in the browser.** Render presence and signatory; claim nothing. *(32 §5.9, §6.4; §16.7)*
27. **Do not render `EquivalentTable` from the risk-flag rows.** One row per asset. *(SC 1.1.1, 1.4.1; §7.5)*
28. **Do not render a marker at the origin for an unpositioned asset.** *(§7.2 rule 4)*

### 20.3 Disclosure, authority, and the two prohibitions that are absolute

29. **Do not render, request, infer, log, or sort on canary status, `origin`, `rank_stratum`, `rank_score`, `rank_components`, or `detector_score` on sheet 07.** The withholding is the recall measurement. *(23 §2.2 I3; 06 §6; §14.2)*
30. **Do not render WF sheet 07's 15 % canary note.** It is drawing rationale; rendering it to a reviewer is the first half of distinguishing the population. *(§14.2)*
31. **Do not render `blinded_from_review_id`.** *(23 §2.1; §14.4)*
32. **Do not treat a `purge` or `rewrap` row carrying an `agent_id` as ordinary work.** A prohibition was violated upstream and the console makes it visible. *(03 §7.2; 32 §6.1; §16.4)*
33. **Do not evaluate [03 §7.2.1]'s minimum-authority table in the console**, and do not disable an adjudication control on a locally computed authority decision. Send, and render the refusal. *(31 §6.4, §8; 50 §9.4; §15.6)*
34. **Do not render `authority_class` as *the* required authority.** It is one representative value from a cell that may accept several. *(03 §7.2.1; §15.6)*
35. **Do not label the `learned` sort "oldest first."** *(30 §4.4, §12.4 DO-NOT 31; §15.4)*
36. **Do not render `announced_recorded_at` without `announced_dispersion_ms`.** *(30 §4.4, DO-NOT 32; 33 §6.4 rule 5; §15.4)*
37. **Do not retry a stale cursor, or swallow a `cursor-generation-stale` 400.** Refetch page one and say so. *(30 §4.4; §15.4)*
38. **Do not present the queue as complete.** `completeness: "level_scoped"` and the level render on every response, not only when stale. *(06 §5 rule 3; 30 §4.5; §15.4)*
39. **Do not send a guessed adjudication request body.** The buttons are disabled with the reason stated until §22 row 17 lands. *(§15.7)*
40. **Do not silently downgrade `view=high_side` to `view=default` on a 403.** *(27 §10.2; §17.3)*
41. **Do not augment a problem `detail`.** It may not name a compartment, a restricted contributor, a system, or a count beyond what `contributor_disclosure` discloses — and the console adds nothing to it. *(27 §10.4; 30 §8.4; §17.3)*
42. **Do not render a human session's identity chip as `delegated`.** That is an agent token shape. *(31 §3.2; 30 §5.3; §4.3)*
43. **Do not render `clearance` in the identity block.** *(§4.3)*
44. **Do not claim a PMA review or a purge proposal implicitly on page load.** A claim is a lease others are blocked by, and a purge claim quarantines a closure. *(23 §3.7; 32 §6.2 phase 2; §14.6, §16.3)*
45. **Do not add a mutation to a screen the wireframe draws no button for.** Sheet 06 has no reservation control, sheet 06 has no forecast-run control, and adding one would enter a saga the console cannot compensate. *(50 §11.2 item 12; 24 §4.5.1; §13.4, §13.6)*
46. **Do not build a component, route, or query for sheet 08 or sheet 09.** *(04 §9, §10; 50 §4.3; §18)*

---

## 21. Definition of Done

**The shared Definition of Done in [09 §8](09-monorepo-and-conventions.md) applies in full and nothing is removed from it**, and **[50 §12](50-ui-design-system.md)'s reconciliation of it for a browser application is adopted verbatim and not repeated**. §21.1 reconciles only the items [50 §12.1] left ambiguous for a *screen-bearing* application, following the pattern [42 §19.1](42-redesign-case-builder.md) established for a component that is not a conventional service. §21.2 is the checklist to copy into `apps/web/README.md` and tick there.

### 21.1 [09 §8] reconciliation, extending [50 §12.1]

| [09 §8] subsection | Applies to `apps/web` | Note |
|---|---|---|
| **§8.1 Contract and specification** | **As a consumer, in full; as a producer, not at all.** [50 §12.1] disposed of this and §19.3 is where it becomes executable. The console publishes no OpenAPI document, so `make contract` has no producer form — **and the consumer form is stricter than a service's**, because §19.3 assertion 3 walks every field the console reads against every committed document. `X-Correlation-Id` is **originated** per user action (§3.2), which is an obligation a pure consumer would not have. Timestamps: the console renders server instants in the operator's local zone **with the zone named** and constructs none except a monotonic delta (§13.4, §16.3) |
| **§8.2 Events** | **None.** [50 §12.1]: neither app publishes or consumes an event, and [09 §9.2 item 15]'s prohibition on non-service topic consumers *"applies with equal force to a browser."* **Asserted, not assumed** — `ui-no-streaming-transport` [50 §10.2] covers the transport and `ui-no-event-consumption` extends it to any broker client |
| **§8.3 Outbox, inbox, read models** | **Two obligations only, both consumed.** No store, no outbox, no read model. But: the queue's projection lag is **rendered** from `queue_freshness` (§15.4, `ui-queue-freshness-rendered`), and **monotonic-clock discipline binds every timer** — and this document adds three concrete ones [50 §12.1] did not have: `TtlCountdown` (§13.4), the purge elapsed duration (§16.6), and the what-if request's own progress (§11.6) |
| **§8.4 Data and storage** | **Items 4 and 5 in full; 1, 2, 3, 6 not applicable.** No database, no migrations. **Provenance (item 4) is binding and is the substance of §11.5**: `observation_ref` resolves to a bitemporally pinned telemetry read, which is [09 §8.4]'s *"sufficient to trace any operator-visible figure to its sources"* made true from the browser. **Classification with `inherited_from` (item 5) is binding** and §4.6 rule 2 is where it lands. **Purge (item 6):** the console is not a store; the two `localStorage` keys are cleared on sign-out (§4.3) |
| **§8.5 Conformance and tests** | **Items 1–5 and 8 have no producer form; items 6–7 adapted.** There is no `packages/contracts/conformance/apps-web/` and no slug — **and this is the item [42 §19.1] taught how to reconcile**: §19.1's named tests are this component's equivalent and are *"named contractually for the same reason [09 §8.5] forbids editing a shared test"* [50 §12.1]. **Consumer-driven tests are satisfied by not needing them**: the console consumes HTTP, not events, and the gateway's own suite covers it [50 §12.1]. **The synthetic reference dataset is adopted** and §19.2 fixes it as the fixture source at [06 §7]'s scale. `pytest` has no analogue; `vitest run` green with the [09 §7.4] coverage floor is the gate |
| **§8.6 Deployment and boundary** | **Mixed, as [50 §12.1] disposed.** `apps/web` ships as static assets behind program ingress and has no pod of its own; the container items fall to whatever serves it. **`.env.example` is binding** and §21.2 enumerates every `VITE_*` variable with no real value. **Structured logging is not applicable** — a browser writes no log line and [31 §13 item 5] forbids a token ever reaching one. **`ui-deep-link-fallback-configured` is added**: [50 §6.4] requires ingress to rewrite unknown paths to `index.html`, *"without it, a refresh on `/fleet-status/assets/…` 404s"*, and with fourteen deep-linkable routes (§3.1) that is not a theoretical failure |
| **§8.7 Documentation and governance** | **All four items, in full.** Item 3 in particular: every `[OPEN]` in §23 and every `[GAP]` in §22 is recorded in the README as a local resolution and raised for a program decision. Item 4: **no `[ESTABLISHED HERE]` convention of [50](50-ui-design-system.md) has been silently varied** — every departure in this document is marked `[EXTENDS 50 §n]` or filed in §22 |

### 21.2 The checklist

**Routing (§3)**

- [ ] `src/routes.tsx` matches §3.1 exactly, including the three `[EXTENDS]` additions and the `/pma/reviews/:reviewId` replacement, and §22 rows 13 and 20 are filed against [50 §4.2]
- [ ] Twelve screens render; sheets 08 and 09 have **no** route, component, or query *(§18)*
- [ ] `ui-no-role-gated-route` green; no `<RequireRole>` exists
- [ ] Title, focus, and the polite announcement fire on every route change *(§3.2)*
- [ ] Filter and sort state is in the URL under the operation's own parameter names, unrenamed *(§3.2, §15.3)*
- [ ] Deep-link fallback configured at ingress; `ui-deep-link-fallback-configured` green *(§21.1)*

**Data access (§3.3–§3.5)**

- [ ] `src/api/keys.ts` is the only source of key literals; `ui-keys-are-central` green
- [ ] `src/api/freshness.ts` carries §3.4's assignments as data, each row citing its setting **and** its derivation; **no fourth interval exists**
- [ ] `ui-pinned-queries-never-poll`, `ui-bitemporal-pairs`, `ui-no-direct-fragment-read`, `ui-all-six-outcomes-handled` green
- [ ] `ui-no-rate-limit-headers-read` green; `429` pauses the query and renders `RateLimitNotice`
- [ ] `ui-no-wall-clock-timers` green, including `TtlCountdown`, the purge elapsed duration, and the what-if progress *(§21.1)*
- [ ] Every response is parsed through the Zod validators for the canonical shared types; `ui-zod-validated` green *(50 §5.2)*

**Per-screen (§4–§16)**

- [ ] Every screen's component list matches its section's table, **and no component outside it exists**; §19.2 assertion 3's inverse check green
- [ ] Sheet 00: `ClassificationBanner` **and** `ClassificationFooter` outside every route; two `ExternalLaunch` nav items with no `aria-current`; `IdentifierLookup` in its two working modes with the hull mode declared absent
- [ ] Sheet H: all five cases of §5.3; `authority_classes: []` is a working state; `ui-hub-skip-never-external` green
- [ ] Sheet 01: the coverage KPI renders all four of [27 §7.5]'s required disclosures; the map ships with a per-asset `EquivalentTable`, focusable named markers, `role="group"`, a `<figcaption>`, and ≥ 24 × 24 px hit areas
- [ ] `demo-positions.ts` holds `asset_id → {x,y}` and **nothing else**; `ui-map-position-count` and `ui-map-positions-match-fixture` green
- [ ] Sheet 01B: no rank is computed; `delta_attribution` renders with `exclusion_set_changed`
- [ ] Sheet 02: `BitemporalToggle` is two independent controls; `EpochBadge` renders the in-flight state; `ui-epoch-not-current-disclosed` green
- [ ] Sheet 03: `ui-hatch-not-insufficient-data`, `ui-completeness-zero-not-unobserved`, `ui-gaps-enumerated` green
- [ ] Sheet 04: `ui-never-sends-min-probability`, `ui-no-research-predictions`, `ui-no-cross-reference-class-sort`, `ui-uncalibrated-never-zero`, `ui-no-tier-branch`, `ui-factors-not-causal` green; the stability floor comes from `GET /pdm/attribution-policy` and is never defaulted
- [ ] Sheet 05: `ui-reason-code-verbatim`, `ui-disposition-totality-surfaced`, `ui-narrative-not-classification` green
- [ ] Sheet 06: `ui-by-condition-not-flattened`, `ui-available-qty-not-recomputed`, `ui-lead-time-labelled`, `ui-ttl-from-monotonic-delta`, `ui-ttl-does-not-assert-expiry` green
- [ ] Sheet 07: `ui-no-canary-signal` and `ui-no-quality-metrics-call` green; the 15 % note does not render; `Escalate` is disabled with a stated reason
- [ ] Sheet 10: all twenty-two parameters exposed under their own names; `ui-no-client-side-queue-filter`, `ui-learned-sort-label`, `ui-approximate-time`, `ui-queue-freshness-rendered`, `ui-non-program-evidence-not-collapsible`, `ui-no-local-authority-matrix` green
- [ ] Sheet 11: `ui-certified-partial-not-complete`, `ui-purge-row-with-agent-id-is-a-fault`, `ui-no-purged-content-excerpt` green; the counter-signature chip renders on class and fleet rows
- [ ] Adjudication: `ui-adjudicate-sends-if-match`, `ui-idempotency-key-stable-across-retries`, `ui-412-requires-reconfirm` green — **or** the buttons are disabled with §15.7's stated reason and §22 row 17 is filed as blocking

**States (§17)**

- [ ] Five renderings, five components, never conflated; `ui-empty-state-names-its-scope` green
- [ ] `ui-kpi-never-renders-zero-for-unknown`, `ui-degraded-view-renders-notice`, `ui-classification-fault-is-not-degraded`, `ui-null-score-reasons-distinct` green
- [ ] Both suppression reasons render distinctly, at HTTP 200, and neither renders `0` or `100`
- [ ] `ui-no-invented-banding` green *(§6.8)*

**Disclosure (§17.2, §6.3–§6.4)**

- [ ] `AdvisoryBanner` renders on sheets 01 and 01B in all three tiers of §6.4, with `statement` verbatim and `methodology_ref` reachable
- [ ] `ContributorDisclosure` renders for both `true` and `false`, with `statement` verbatim; `score_integrity` renders as its own note
- [ ] `ui-disclosure-always-rendered`, `ui-forbidden-disclosure-fields`, `ui-advisory-must-be-surfaced`, `ui-advisory-from-header-only`, `ui-fs-term-001`, `ui-no-retired-markings` green

**Accessibility (§19.2)**

- [ ] Every test named in [50 §8.1–§8.6] green, plus `a11y-external-nav-no-current`
- [ ] `a11y-axe-clean` reports zero `serious` or `critical` violations on **every one of the fourteen routes**
- [ ] `ConfigTree` implements the full ARIA tree key model; a vacant position has no `aria-expanded` *(§9.3)*
- [ ] `IdentifierLookup` implements the ARIA 1.2 combobox key model, with a `<label>` and no placeholder-as-label *(§4.4)*

**Environment**

- [ ] `.env.example` enumerates every variable with no real value: `VITE_BASE_PATH`, `VITE_PRACTITIONER_BASE_URL`, and nothing else this document introduces *(§21.1)*
- [ ] `ui-external-launch-configured` green; an unset `VITE_PRACTITIONER_BASE_URL` disables all four affordances of §18.2 with a stated reason

**Contract (§19.3)**

- [ ] `tests/contract/` runs all eight assertions against the committed documents
- [ ] `apps/web/contract-gaps.json` is committed, and CI fails on an added gap and warns on a closed one

**Governance**

- [ ] Corrections **1–68** of §22 each filed against their document with an owner. **Rows 4, 16, 17, 21, 59, and 67 block a complete `apps/web`** and are recorded as blocking. **Rows 15 and 19 are resolved.**
- [ ] Open questions **UI-OQ-51-1 … UI-OQ-51-6** and the five inherited from [50 §14] recorded in the README as local resolutions where a screen had to proceed *(09 §8.7)*
- [ ] Every deviation from [50](50-ui-design-system.md) carries an ADR under `docs/adr/` and appears in §22 *(09 §8.7)*
- [ ] No `[ESTABLISHED HERE]` convention of [50](50-ui-design-system.md) has been silently varied *(09 §8.7)*

---

## 22. Corrections to source documents

Found while wiring every screen field by field, following [09 §11](09-monorepo-and-conventions.md)'s convention and [26 §13](26-supply.md)'s table shape. Each is a **defect in the cited document or in the approved wireframe**, not a decision of this one. **None is applied here.** **Rows 4, 16, 17, 21, 59, and 67 block a complete `apps/web`. Rows 15 and 19 are resolved** — see their rows below.

| # | Document | Defect | Correction | Status |
|---|---|---|---|---|
| 1 | **WF sheets 01, 01B** | The warning-lead-time-coverage KPI is drawn as a bare percentage. [32 §10.7] now supplies the operation, closing [50 §13 row 2] — but [27 §7.5] requires the lead-time distribution and denominator, the chance reference and flag rate, the achievable ceiling, and stratification, and *"a bare percentage as drawn violates all four"* [50 §7.4 rule 6]. A `.kpi` box cannot hold them | Draw a `Lead-time coverage — distribution and reference` box after the KPI row, carrying the p10/p50/p90 distribution, covered/uncovered counts, chance reference and flag rate, achievable ceiling, and `computed_at` / `definition_ref` | **Applied in §6.3 / §8.3.** The wireframe needs the edit |
| 2 | **50 §9.2** | Its asked-for session shape was `{ sub, display_name, unit_uic, billet, authority_classes[], clearance, classification }`. [30 §8.1.2] landed a different one: the identity block *"byte-identical to §3.2's token shape"*, whose subject member is **`subject_id`** not `sub`, which additionally carries `unit_path` and `qualifications`, and which carries no `classification` | Amend [50 §9.2] to [31 §3.1]'s actual member names | Not applied; flagged. §4.3 wires the real block |
| 3 | **30 §3.4** | The composed-view envelope's **`as_of`** appears in the example and **its semantics are defined nowhere** — the fan-out's start, its completion, or the oldest contributing fragment's currency. [50 §13 row 5] filed this and it is **still open** | Define `as_of` in §3.4 | Not applied; **still open**. Every screen labels it *"composed at"* per [50 §5.3] rule 5 |
| 4 | **20 §6.1 rows 1–2** | `GET /assets` and `GET /assets/{asset_id}` declare **no query parameter anywhere in [20](20-registry.md)** — no `hull_or_tail=`, `uic=`, `domain=`, `class_id=`, or `changed_since=`, unlike rows 10, 13, 16, 19–22 which spell theirs out. **There is no operation that answers "which asset is hull DDG 113," and no operation mapping a `unit_uic` to an asset** | Declare `GET /assets?hull_or_tail=&uic=&domain=&class_id=&changed_since=&cursor=`. Obligation 5 arguably requires `changed_since` already, since consumers project `Asset` | **Blocking** the sheet-00 lookup (§4.4), sheet 02's search (§9.2), and the hub's `VR` card (§5.4). Not applied; flagged |
| 5 | **WF sheet 01, KPI 1 sub-line** | `▲ 2pt / 30d`. **No 30-day-window delta field exists on any operation.** The only published delta is `delta_attribution` [27 §3.11], which is assessment-to-assessment | Redraw as the previous-assessment delta with `exclusion_set_changed` disclosed | **Applied in §6.3.** The wireframe needs the edit |
| 6 | **27 §10.1 row 4; WF sheets 01, 01B** | `Open Risk Flags` is drawn as a total (`11`, `2`). `GET /risk-flags` is cursor-paginated with **no count**, [03 §4] forbids a total on an unbounded collection, and [32 §10.6] adds that a count is an aggregation channel | Either publish a bounded flag count per scope with the exclusion policy applied, or redraw as `n shown` | Interim in §6.3 (`n shown` with its bound). Flagged |
| 7 | **WF sheets 01, 01B** | The severity breakdown reads `4 critical · 7 warning`. **`critical`/`warning` are chip tones, not the severity vocabulary**: [27 §6.2] fixes it as `advisory_watch`, `casualty_risk_moderate`, `casualty_risk_high`, `advisory_watch_population`, `casualty_risk_moderate_population`, with *"no `_high` severity"* for population classes | Redraw using [27 §6.2]'s five names | **Applied in §6.5.** The wireframe needs the edit |
| 8 | **WF sheet 01; 27 §10.1 row 1** | `Rollup by TYCOM / class` needs a per-class readiness score. `scope` accepts `asset \| system \| fleet \| fleet_grouping` — **`class` is not a scope value**, and `fleet_grouping`'s intrinsic weight (*"hull tasking"*) is **`[OPEN]` per [27 OD-2]** | Either add a `class` scope, or resolve OD-2 and state that a class is a `fleet_grouping` | Interim in §6.6 (`fleet_grouping` rows; no client-side rollup). Flagged |
| 9 | **WF sheet 01B, KPI 1 sub-line** | `rank 6 of 12 in class`. **No rank field exists**, and [27 §3.6] discusses cross-hull comparison only in a ruled-out formulation. Computing it needs twelve views and a comparison across figures each renormalized over a different visible contributor set — a cross-view derivation over incomparable values | Either publish a rank with its comparability basis, or remove it | **Applied in §8.3** (`delta_attribution` instead). The wireframe needs the edit |
| 10 | **WF sheet 04 box label; 22 §10** | `Triage — ranked by expected consequence`. `GET /predictions` has **no `sort` parameter**; expected consequence is `POST /expected-consequence`'s output requiring `ConsequenceWeights`, `operating_fraction`, and `RiskPosture` **that no operation publishes**; and the `pdm-fleet-triage` agent that would rank is *"not built in this wave"* [22 §10.1] | Either publish a `sort` parameter, or publish the consequence weights and posture, or relabel the box | **Applied in §11.2** (`Triage — active predictions`, sorted on a served field). The wireframe needs the edit |
| 11 | **WF sheet 05; 24 §3.2** | The `Priority` column (`high`/`routine`/`urgent`). **`WorkCandidate` has no priority field.** `expected_consequence` is *"[o]ptimizer-populated, never client-set"* and null before a run; `consequence_rank` is on `CandidateDisposition`, not the candidate | Redraw as `Expected consequence` with a `not yet ranked` state, plus `weights_are_illustrative` | **Applied in §12.3.** The wireframe needs the edit |
| 12 | **26 §2.5** | **`supply.requisition_state` is referenced in the DDL and defined nowhere** — a repository-wide search returns exactly one hit, its own column declaration. `supply.requisition_driver` is likewise undeclared as a type, though its values appear inline. Sheet 06's `Status` column has an enum with no values | Declare both `CREATE TYPE` statements | **Blocking** sheet 06's status rendering and any tone mapping. Interim in §13.5 (verbatim, uncoloured). Flagged |
| 13 | **50 §4.2** | The route `/pma/missions/:missionId` **has no operation behind it.** [23 §3.7]'s `GET /reviews` has no `mission_id` filter; `mission_id` is a column, and every reviewer-facing operation is keyed on `review_id` | Replace with `/pma/reviews/:reviewId` | **Applied in §3.1.** [50 §4.2] needs the edit |
| 14 | **23 §2.1; WF sheet 07** | The `Tags confirmed` column has **no field.** `pma.mission_review` carries no confirmed count, and [03 §4] forbids a total on an unbounded collection | Add a per-review confirmed/rejected count to `GET /reviews/{id}` — it is bounded by `candidate_cap` and is not an unbounded aggregation | Interim in §14.5 (count over the materialized page, cap stated). Flagged |
| 15 | ~~**30 §4.5 vs. 30 §8.1.2 vs. 03 §7.2.1** | `GET /proposals`'s `authority_class` parameter declares **five** values...~~ **[RESOLVED.]** `30-gateway.md` §4.5 now declares all six values including `security_officer`, explicitly closing this row | Closed — no correction needed | **Resolved.** Sheet 11's filters and the hub's `SC` pre-filter use `authority_class=security_officer` directly (§5.5, §15.3); the `?kind=purge&kind=rewrap` substitute remains available as a narrower alternative, not a required interim |
| 16 | **30 §4.5, §4.3 rule 4** | The queue row's **`subject` members are not enumerated.** §4.5 shows `"subject": {}`; §3.4 shows `{ "asset_id": "…" }`; §4.3 rule 4 says the response *"carries both the provisional and the confirmed identifier when they differ"* **and names neither field**. Sheet 10's target rendering, sheet 11's closure selector, and the `redesign_case` → `views/redesign-case/{case_id}` drill-down all need a named member | Enumerate `subject`'s members per `scope`, and name the provisional/confirmed pair | **Blocking** §15.5's target cell and §15.5's drill-down key. Interim: generic key/value rendering. Flagged |
| 17 | **30 §4.5, §4.6** | **`POST /proposals/{proposal_id}/adjudicate` has no specified request body.** The path, `Idempotency-Key`, `If-Match`, and three proxy rules are given; **no field names** — no `decision`, no `disposition`, no `adjudication_note`. [30 §2.4] mentions `adjudication_note` only as a gateway-store forbidden field, and owners differ ([23 §3.7] `POST …/adjudicate`; [32 §10.5] `PATCH /proposals/{id}`) | Specify the body, or declare it a verbatim pass-through of the owner's and enumerate the owners' shapes | **Blocking sheets 07, 10, and 11's approve and reject actions.** Interim in §15.7: buttons disabled with the reason stated. Flagged |
| 18 | **WF sheet 11 box 4** | [32 §6.7] states a direct UI obligation — *"the operator interface shows the pending set with **the node identity and the elapsed duration**"* — and the drawn ledger shows the node identity only | Draw the elapsed duration per pending node | **Applied in §16.3 / §16.6.** The wireframe needs the edit |
| 19 | **30 §4.5, §2.4; 03 §7.2.1; 32 §6.1** | **The queue row cannot represent a three-signature purge.** `items[]` carries `adjudicated_by`, `second_adjudicator`, and `second_signature_outstanding` — two signatories. [03 §7.2.1] and [32 §6.1] require, at class/fleet scope, `security_officer` **+ a second distinct `security_officer`** **+ a `fleet_authority` counter-signature` — three | Add a counter-signature field to `PROJECTED_COLUMNS` and the wire row, distinct from `second_adjudicator` | **Blocking** sheet 11's class and fleet rows. Interim in §16.4 (an explicit "state not represented" chip). Flagged |
| 20 | **50 §5.3, §4.2, §5.4** | [50 §5.3]'s shape table lists **four** composed views; [30 §3.2] now has **five** — `redesign_case_detail` was added by amendment expressly for *"[a]n adjudicator opening a `redesign_case` **from the queue**"*, which is sheet 10, in `apps/web`. And [50 §4.2]'s route tree has no segment for sheet 05's availability scope, sheet 06's reservation set, or an asset-scoped pdm view | Add the fifth view, its query key, and its freshness row to [50 §5.3]/§5.4; add §3.1's three route segments to [50 §4.2] | **Applied in §3.1 / §3.3 / §3.4 / §15.5** as `[EXTENDS 50]`. [50](50-ui-design-system.md) needs the edits |
| 21 | **30 §3.2** | **No fragment's `operation_id` value is stated.** The field exists — *"the upstream `operationId` (09 §7.3); resolved against its committed spec"* — and not one of the twenty-nine fragments across five views has its value given. **A consumer therefore cannot derive any fragment's response shape from [30](30-gateway.md)**, which is what every composed-view screen renders | Enumerate `operation_id` per fragment in §3.2's table | **Blocking, in the sense that every composed-view field in §6–§11 is derived from the upstream document rather than from the gateway's contract.** Not applied; flagged |
| 22 | **50 §4.3** | It states `apps/web` owns *"exactly one thing"* on sheets 08 and 09's behalf — the two hub cards. **WF sheet 00's side nav also lists `Failure Intelligence` and `Design Advisory`**, which have no `apps/web` route | Restate as four affordances across two surfaces, all `ExternalLaunch` | **Applied in §4.2 / §18.2.** [50 §4.3] needs the edit |
| 23 | **WF sheet 00 `.topbar .id`** | The identity chip reads `delegated`. **`delegated` is an agent token shape** [31 §3.2] and [30 §5.3]'s `fathom.agent.authority` value; `fathom.identity` [31 §3.1] has no field it could come from. It would tell an operator their own session is an agent delegation | Redraw as one chip per `authority_classes[]` value | **Applied in §4.3.** The wireframe needs the edit |
| 24 | **30 §4.5** | `GET /proposals/summary` is described as *"[c]ounts grouped by `status × authority_class × blast_radius × target_sub_app`, plus a total for the deployment's level"* and **states no field names**. The nav badge has no named source | Specify the response schema | Interim in §4.5 (no badge rather than a zero badge). Flagged |
| 25 | **WF sheet 00 side nav** | No nav item reaches `/audit/remediations`, though sheet 11 exists and is routed. Reaching a routed, deep-linkable screen only from the hub makes it invisible to an operator who has already landed | Add a `Remediation Queue` item to the `Cross-cutting` group, without a badge | **Applied in §4.5.** The wireframe needs the edit |
| 26 | **30 §7.3** | Composed-view `X-Classification` is *"the union of the contributing fragments' labels."* A route that makes several requests (sheets 01, 01B, 02, 06, 07 each make three to six) may receive **differing** labels, and no document says what the banner should then show | State whether a multi-request route is expected to observe one label, or specify the console's obligation | Interim in §4.6 rule 2 (banner fault state; the console picks none). Flagged |
| 27 | **WF sheet H footnote** | *"the roster is exactly document 03 §7.2.1's six adjudicating authority classes … plus two review-only roles (Ship's Force Maintainer-as-reviewer, Reliability Engineer)."* **Ship's Force Maintainer *is* `maintainer`**, one of the six, so the footnote double-counts it, and it omits **Vehicle Readiness Officer**, the card that genuinely has no class. [50 §13 row 17] filed this and it is **still open** | Restate: six classes → six cards; `VR` and `RE` are self-selected personas with no realm role | Not applied; **still open**. §5.2 |
| 28 | **50 §3.5** | The component inventory has no entry for `score_integrity` [27 §4.4], which [27 §12.5]'s `fs-disclosure-present` makes a **required** top-level member of every readiness, explanation, and status-summary 200 alongside `contributor_disclosure` | Note in §3.5 that `score_integrity` renders through `SheetNote` with a `statement` prop; no new component | **Applied in §6.3.** [50 §3.5] needs the note |
| 29 | **30 §8.4, §3.4; 27 §8.2** | [30 §8.4] enumerates the response headers the gateway forwards on **pass-through** and does not require `X-FATHOM-Advisory` on a **composed view** — while [27 §8.2] sets that header on every fleet-status response precisely because *"a **BFF view-model composition [04 §11]** … may drop"* the body block. On `GET /views/fleet` **both mechanisms can be absent**, and `ui-advisory-from-header-only`'s premise fails | Require the gateway to emit `X-FATHOM-Advisory` on any composed view containing a fleet-status fragment, or add an envelope-level advisory member to §3.4 | Interim in §6.4 (a three-tier resolution, tier 3 degraded). Flagged |
| 30 | **20 §4.5.1** | `installed_items` carries `niin`, `iuid`, `serial_or_lot`, `eic`, `ric`, and an `sclsis_record` JSONB — **and no `label` or `name` column.** WF renders human nomenclature (`SSDG No. 2`, `Feed pump #A19381`) on sheets 01, 01B, 03, 04, 05, 07, 10 | Add a nomenclature field, or state that `niin` + `serial_or_lot` is the operator-facing rendering | Interim: identifiers plus `niin`/`serial_or_lot`, never a fabricated name. Flagged |
| 31 | **WF sheets 01, 01B** | The `Predicted category` column shows `CAT 3` **and** `class_estimate` in the same cells. Those are two different things: `predicted_casualty_category_candidate` [27 §2.4] and `reference_class` [03 §7.1] — and reference class is the field [03 §7.1] makes consumers *must* branch on | Separate them into a category column and a reference-class chip | **Applied in §6.5.** The wireframe needs the edit |
| 32 | **27 §6.2, §7.5** | **No document bands a readiness score, a coverage fraction, a flag count, a completeness ratio, or a probability into a status tone**, yet WF colours all of them. A UI-chosen threshold is an acceptability assertion on a view [04 §5] says must not be mistaken for authoritative reporting | Publish banding with its basis, subject to [27 §7.6] rule 3's advisory labelling — or accept uncoloured values | **Applied in §6.8** (no tone without a field). Flagged |
| 33 | **WF sheet 01 map callout** | `text.sel-label` reads `DDG 113 · 78%`. `fleet_overview` [30 §3.2] has **no per-asset readiness fragment**; the score is not on the view | Redraw the callout without the percentage, or add a per-asset fragment | **Applied in §7.3** (hull + severity word). The wireframe needs the edit |
| 34 | **WF sheet 01 map key** | The `neutral` dot is labelled *"no recent contact."* **No field expresses recency of contact** [50 §13 row 4], and §7.4 establishes that `neutral` means the flag fragment did not resolve. Also the key lists four dots where the map can draw six states | Relabel as `flag state unknown` and enumerate all six | **Applied in §7.4.** The wireframe needs the edit |
| 35 | **50 §8.5 part 4, §3.5** | It identifies sheet 01's Risk-flags box as the map's `EquivalentTable`. **It is not**: the map encodes one row per **asset**; the flags box enumerates **flags**. An asset with no flag has a marker and no row; an asset with three flags has one marker and three rows; a `cleared` flag has a row and colours no marker. SC 1.1.1 and SC 1.4.1 both fail | Specify a per-asset `EquivalentTable` from `asset_status` + `open_casrep_risk`, visually hidden inside the map box | **Applied in §7.5.** [50 §8.5] and [50 §3.5] need the edit |
| 36 | **WF sheet 01B `.sheet-note`** | Cites `GET /readiness?scope=asset&id=`. The parameter is **`asset_id`** [27 §10.1 row 1], not `id` | Correct the note | Not applied; flagged. §8.1 |
| 37 | **WF sheets 01B, 02** | The `OFRP: Sustainment` chip is `tone="good"`. **[27 §9.3] row 2 and [27 DO-NOT 22] forbid treating an OFRP phase change as degradation**, which is what a `good` tone asserts | Render `tone="neutral"` | **Applied in §8.4.** The wireframe needs the edit |
| 38 | **WF sheet 01B box 5** | The label reads `Rollup by system (ESWBS)` unconditionally. `SystemNode.eswbs` is *"populated only where `scheme_family = 'eswbs'`"* [20 §4.3], and `GET /assets/{id}/systems` *"echoes [the `hsci`] on every response"* [20 §4.1] | Condition the label on `scheme_family` | **Applied in §8.4.** The wireframe needs the edit |
| 39 | **27 §10.1 row 1** | The parameter list `scope=&asset_id=&system_id=&grouping_id=` is flat and **the valid pairings are unstated.** Sheet 01B's system rollup needs `scope=system` **with** `asset_id` to return all of one hull's system assessments in one call; the alternative is a per-system browser fan-out | State the valid `(scope, identifier)` pairings | Interim in §8.4 (the pairing above). Flagged |
| 40 | **50 §4.2** | The pdm routes are `/pdm` and `/pdm/installed-items/:installedItemId` — **no asset-scoped route**, although `GET /predictions` accepts `asset_id=` and WF sheet 01B's `View predictions` button is asset-scoped | Note that `/pdm?asset_id=` is the asset-scoped form; no new segment | **Applied in §8.4.** [50 §4.2] needs the note |
| 41 | **20 §4.3, §6.2** | [20 §4.3] references *"a fuller `AssetDetail` response (§6.2)"* and **§6.2 defines no `AssetDetail`** (only `ConfigurationLine`, `AssetConfiguration`, `BaselineEpochState`). [20 §4.5.1] likewise says the `InstalledItem` → `InstalledItemRef` projection is *"see §6.2 for the exact projection"* and §6.2 has no installed-item schema | Define both schemas in §6.2 | Interim: wired to the table column names. Flagged |
| 42 | **50 §3.2; WF sheet 02** | `BitemporalToggle` is mapped to `ToggleGroup type="single"` — *"[t]wo exclusive options."* **They are not exclusive**: [20 §6.3] makes `as_of` and `as_known_at` two independent instants and states *"[t]he two are never compared."* A single-select control cannot express WF's own drawn `(2026-08-01, today)` | Specify two independent controls, each a `ToggleGroup` with `now`/`explicit` plus a datetime input | **Applied in §9.4.** [50 §3.2] needs the edit |
| 43 | **21 §9.1** | **No downsampled, aggregate, or summary series read exists**, and the word *sparkline* appears nowhere in [21](21-telemetry.md). Sheet 03's `Trend` column is built from the raw paginated series | Either publish a bounded summary read, or state that the first page is the drawn window | Interim in §10.4 (first page, window stated). Flagged |
| 44 | **WF sheet 03 row 2** | The `Trend` cell renders `.hatch`. **`--hatch` means *"a figure belongs here and is not rendered"*** [50 §2.5] and is forbidden as a loading state [50 §11.1 item 6]. Row 2 is a series with 71 % completeness — **too sparse to trend, not absent** | Redraw as an inline `EmptyState` reading `insufficient completeness to trend` | **Applied in §10.4.** The wireframe needs the edit |
| 45 | **WF sheet 03** | Completeness chips are drawn `good` at 98 % and `warning` at 71 %, with no threshold in any document. The only threshold that exists is per-definition `min_completeness` [21 §3.4.1] | Render two tones from `completeness` vs. `min_completeness` | **Applied in §10.5.** The wireframe needs the edit |
| 46 | **21 §3, §5** | **No "last sample time" field exists** under any name (`last_sample`, `last_seen`, `latest_sample`). The available currency facts are `indicator_value.window_end` and `mission_record.ended_at` | Either publish a last-observation instant, or state that `window_end` is the rendering | Interim in §10.5 (`window_end`, labelled *"latest window ends"*). Flagged |
| 47 | **WF sheet 03 missions box** | The `Type` column renders `UUV sortie`, conflating `mission_type` (`sortie`) with the platform (the asset's `domain`) | Render `mission_type` verbatim; the domain is the asset's | **Applied in §10.6.** The wireframe needs the edit |
| 48 | **50 §7.5** | It makes the contributing-factor stability floor *"a required prop rather than defaulting it"* and leaves the source open. **[22 §9.3] is the source**: threshold `stability >= 0.6` [P-20], at most 5 factors [P-21], *"[t]he applied threshold [is] published on `GET /pdm/attribution-policy`"* | Cite [22 §9.3] and the operation in [50 §7.5] | **Closed by §11.5** rather than corrected; recorded so [50](50-ui-design-system.md) can cite it |
| 49 | **WF sheet 04 box 3** | The `Stability` column shows `0.52`, **below [22 §9.3]'s 0.6 suppression floor** — a factor at that stability is not emitted at all | Change the illustrative value to one above the floor | Not applied; flagged |
| 50 | **50 UI-OQ-9** | It states the sheet-04 what-if call is `POST /api/v1/gateway/inference/{domino_endpoint_name}` [30 §5.6]. **It is not.** [22 §10] declares `POST /api/v1/pdm/what-if` (`x-substitution: required`, `x-side-effects: none`, agent-eligible, manifest `pdm-whatif`); **PdM** calls the Endpoint [22 §13.1]. The two paths have different limits, problem types, and owners | Correct UI-OQ-9 to the pdm operation | **Applied in §11.6.** [50 UI-OQ-9] needs the edit |
| 51 | **WF sheet 04 box 4** | The chip reads `[chip accent] tier-3 · interactive`. `--accent` means *"primary interactive control"* [50 §2.2] and this is a label; and conditioning an affordance on `tier` violates [50 §11.4 item 38] — the branch must be on `reference_class` | Redraw `tone="neutral"` reading `interactive · no latency guarantee`; condition availability on `reference_class === "item"` | **Applied in §11.6.** The wireframe needs the edit |
| 52 | **WF sheet 05 box 1** | The `prediction` driver chip is `[chip accent]`. WF's own legend makes status *"independent of the accent color"*, and a driver is a status | Render `tone="neutral"` for `prediction` and `pms`, `critical` for `casualty` | **Applied in §12.3.** The wireframe needs the edit |
| 53 | **WF sheet 05 box 2** | `excluded` is drawn `[chip critical]`. An exclusion is a planning outcome, not a casualty — and `critical` is the tone the casualty driver uses two boxes away | Render `tone="warning"` | **Applied in §12.4.** The wireframe needs the edit |
| 54 | **WF sheet 05 box 2; 24 §4.4** | The `Reason` column renders free prose (*"within window, parts on hand"*). **`reason_code` is `enum # CONTROLLED VOCABULARY. Never free text`** with sixteen values; the free-text member is `counterfactual` | Redraw as `reason_code` + `binding_constraint`/`slack` + `counterfactual` | **Applied in §12.4.** The wireframe needs the edit |
| 55 | **WF sheet 06 box 1; 26 §7.2** | The flat `On-hand 2` / `Condition A` pair. **[26 §7.2] makes `by_condition[]` MANDATORY and non-empty and states *"a bare `on_hand_qty` at position level does not exist in the schema"***; `available_qty` is derived per `(niin, location, condition, purpose)` | Redraw as one row per `by_condition[]` entry, plus a separate allowance table | **Applied in §13.3.** The wireframe needs the edit |
| 56 | **WF sheet 06 box 1** | `Lead time 14d` is unlabelled between `order_and_ship_time_days` and `procurement_lead_time_days` — and [26 §5.4] makes the second **select the procurement instrument** (`DYA` → `DYK`/`PA`, or `PB` → `PR`) | Draw both, each labelled, with `basis`, `observed_n`, `as_of` | **Applied in §13.3.** The wireframe needs the edit |
| 57 | **WF sheet 06 box 3** | The `Status` cell reads `BB — backordered`, a MILSTRIP supply status code. **No field is a two-character supply status code**: the available fields are `state` (undefined, row 12), `current_dic` (`char(3)`), and `advice_code` (`char(2)`) | Either publish a supply-status-code field, or redraw as `state` + `current_dic` | Interim in §13.5. Flagged, together with row 12 |
| 58 | **WF sheet 07 `.sheet-note`** | *"15% of candidates are seeded canaries with planted ground truth, presented indistinguishably from real candidates."* **Rendering this to a reviewer at a console tells them a seeded population exists**, which is the first half of distinguishing it. [23 §2.2] withholds `origin` (I3) and the wire model has no `canary_*` member precisely so it cannot be surfaced | Move the note to a drawing-rationale callout, not a `sheet-note` that reads as UI copy | **Applied in §14.2** (the note does not render). The wireframe needs the edit |
| 59 | **23 §2.6, §3.6; 30 §8.1** | Evidence is served as **pre-signed object URLs** into bucket `fathom-pma-evidence`, and **no document states whether those URLs are reachable from an operator's browser.** The gateway's surface is `/api/v1/{slug}/…` and `/api/v1/gateway/…` only, with no object-store proxy, and no ingress path from the operator network to the object store is declared anywhere | Declare the ingress path, or add an evidence-object proxy to a service's surface | **Blocking** sheet 07's evidence pane. Interim in §14.4 (the `object_manifest` as a table, artifacts not rendered inline, limitation stated). Flagged |
| 60 | **WF sheet 07** | `Reject` is a bare button. [23 §2.5] requires a **`reason_class`** from a nine-value enum, one of which (`duplicate_of_candidate`) additionally requires `duplicate_of_candidate_id` | Draw the reject dialog with its reason `Select` | **Applied in §14.4.** The wireframe needs the edit |
| 61 | **WF sheet 07; 23 §3.7** | The `Escalate` button. **There is no escalate operation**: [23 §3.7]'s reviewer actions are `confirm`, `reject`, the batch `adjudications`, `claim`, and `complete` | Either add an escalation operation, or remove the button | **Applied in §14.4** (disabled with a stated reason). Flagged |
| 62 | **03 §7.2; 23 §3.7** | [23 §3.7] states *"[t]he gateway renders an admitted agent proposal as **`claimed_by_review`**, not `proposed`"* — a value **not in [03 §7.2]'s `ProposalStatus` enum** (`proposed \| claimed \| approved \| rejected \| superseded \| expired`) | Add `claimed_by_review` to `ProposalStatus`, or state that it is a presentation flag rather than a status | Handled in §15.5 (rendered distinctly). Flagged |
| 63 | **31 §6.4** | The generated authority matrix covers `anomaly_tag`, `work_candidate`, `requisition`, `interval_change`, `redesign_case`, `configuration_change` — and **`security_officer` appears in no cell**, yet [03 §7.2.1] has `purge`/`rewrap` rows requiring it. A console rendering enablement from that matrix would show the Security Officer authorized for nothing. [50 §13 row 18] filed this and it is **still open** | Add the `purge`/`rewrap` rows. Related: [31 §2.4] says six while §2.5, §3.1 rule 3, and T-7 still say *"five"* | Not applied; **still open**. §15.6 |
| 64 | **30 §4.5, §4.6** | `POST /proposals/{proposal_id}/claim` has **no described request body** — not even an explicit statement that it takes none | State that the body is empty, or specify it | Interim in §15.7 (none sent). Flagged |
| 65 | **WF sheet 11 box 2 row 1** | `security_officer — 1 of 1` for an item-scope purge. **[03 §7.2.1] and [32 §6.1] require `security_officer` + dual control at item/asset scope — two of two, not one of one** | Redraw as `1 of 2` | **Applied in §16.4.** The wireframe needs the edit |
| 66 | **WF sheet 11 box 2; 32 §6.2** | The `Store` column shows a store list for a `proposed` purge. **The store set is the sealed closure, written at phase 3 (ENUMERATE), which follows phase 2 (CONTAIN) on claim** — a `proposed` purge has no `purge_id` and no closure | Relabel the column `Closure` with a `not yet enumerated` state | **Applied in §16.5.** The wireframe needs the edit |
| 67 | **32 §4.6, §10.4** | The **dissemination ledger has no read operation.** §4.6 defines the table and calls it *"the single most important addition this document makes to the platform"*; §10.4's only exposure is `POST /lineage/closures`, **compute-only**, which is a mutation-shaped read with no cache key. WF sheet 11 box 4 is titled `Dissemination ledger — who holds a copy` | Add `GET /dissemination?…` cursor-paginated, or state that `GET /purges/{id}`'s holder list is the operator-facing surface | **Blocking** sheet 11 box 4 as drawn. Interim in §16.6 (`GET /purges/{id}`, which carries holders, receipts, and pending nodes). Flagged |
| 68 | **WF sheets 01, 01B** | The suppressed-score case of [27 §3.9] — `score: null` with `suppression_reason` `all_contributors_restricted` or `no_contributors`, at HTTP **200** — **is drawn on neither sheet**, and it is the case where rendering `100` *"presents a fully compartmented, possibly failed asset as perfectly ready."* [50 §13 row 12] filed this and it is **still open** | Draw both null-score states on both sheets | Specified in §17.3; the wireframe needs the edit |

---

## 23. Open questions

Recorded rather than resolved locally, following [30 §15], [31 §15], and [50 §14]. **[50 §14]'s ten are carried forward**; four are wholly or partly closed by this document's research and are marked, and six new ones are added. An app that must proceed records its local resolution in its README ([09 §8.7]) and does not treat it as settled.

| # | Question | Impact if unresolved | Interim position |
|---|---|---|---|
| **UI-OQ-1** *(inherited, partly closed)* | **The session cookie's name and the CSRF token's cookie and header names.** [30 §8.1.2] now specifies the attributes and the mechanism — *"an opaque session identifier in an `HttpOnly`, `Secure`, `SameSite=Lax` cookie, keyed against a server-side store (Redis, TTL-bound…)"* and *"`SameSite=Lax` plus a **double-submit token** on every state-changing gateway-owned operation"* — **and names neither the cookie nor the token** | **The console cannot send a double-submit token whose header and cookie names it does not know**, so every state-changing gateway-owned request (claim, adjudicate, logout, agent-session) would be rejected by the middleware | `src/api/csrf.ts` exists as a stub reading a conventionally-named pair. **Raise for [30 §8.1.2] to name both.** The attributes half of [50 UI-OQ-1] is closed |
| **UI-OQ-2** *(inherited, closed)* | **Logout.** — | — | **Closed** by [30 §8.1.2]'s `POST /api/v1/gateway/session/logout`, with server-side RP-initiated logout and no client `end_session_endpoint` redirect. Wired in §4.3 |
| **UI-OQ-3** *(inherited)* | **Notification surface.** [33 §6.4] states its presentation rule is *"binding on … `apps/web`"* — `occurred_at` as the headline always, `recorded_at`/`delivered_at`/`received_at` secondary and separately labelled, default sort by `occurred_at`, the `delay` block and `dispersion_ms` qualifiers — but **no wireframe sheet renders a notification list** | The rule has no surface to bind, and the first author to draw one may not know it exists | **No notification surface is built**, because none is drawn and [50 §11.2 item 12] forbids inventing one. `ui-occurred-at-headline` [50 §10.2] stands ready. **Raise whether a notification surface is in scope for a later revision** |
| **UI-OQ-4** *(inherited, closed)* | **The practitioner credential path.** — | — | **Closed** by [31 §5.8], *"[AMENDMENT — closes a BLOCKING gap, `50-ui-design-system.md` §13 correction 10]"*. It changes nothing in `apps/web` and is [52](52-practitioner-apps.md)'s to consume |
| **UI-OQ-5** *(inherited)* | **The two tight contrast ratios**: the `.chip` label (3.86 : 1 as drawn) and `--annotation` on `--annotation-bg` (4.52 : 1, serif italic) | Either a documented AA failure ships, or an approved token changes | [50 §8.4]'s uniform `--ink` chip label is implemented, and this document's chips inherit it. **The annotation ratio is unchanged and is at-risk** — and this document renders more annotation-voice text than [50](50-ui-design-system.md) anticipated (§6.3, §11.4, §16.4, §16.7 all render verbatim statements in it). **Raise with the program** |
| **UI-OQ-6** *(inherited, with new data)* | **Tree typeahead** in `ConfigTree` | A large tree may be impractical by arrow key alone | Not implemented (§9.3). **New data point**: a hull's configuration paginates at `MAX_LIMIT = 500` [20 §6.4], so the tree never materializes [06 §7]'s ~8,400-item fleet configuration; arrow-key navigation over 500 nodes is unpleasant, not impractical. **Revisit once real fan-out is measured** |
| **UI-OQ-7** *(inherited)* | **End-to-end testing.** No E2E tool is named anywhere in the corpus | Cross-route flows — persona → sheet → drill-down → claim → adjudicate — are untested end to end, and this document now has fourteen routes and two mutation paths | None adopted (§19.3). **Raise for assignment alongside [09 §10 item 8]** |
| **UI-OQ-8** *(inherited, partly closed)* | **Copilot surface.** [50 UI-OQ-8] recorded that *"no agent-invocation operation exists anywhere in the corpus — `apps/web` has nothing to call"*, and that no sheet draws a Copilot panel | An entire agent's user interface is unspecified | **The operation half is closed**: [30 §8.1.1] adds the shape-1 interactive surface — `POST /agent-sessions`, `POST /agent-sessions/{id}/turns` (body `{question}`, returning a `GroundedAnswer` or a refusal), `GET`, `DELETE`, all `Idempotency-Key`-required and `x-agent-eligible: false`. **The drawing half is not**: WF sheet 00's topbar has `FATHOM`, the lookup, and the identity block; its side nav has eleven items; **no sheet draws a Copilot affordance anywhere.** This document therefore builds none [50 §11.2 item 12], and `GroundedAnswer`'s schema is additionally undefined in [30](30-gateway.md). **Raise with [40](40-copilot.md) for a drawn surface** |
| **UI-OQ-9** *(inherited, operation corrected)* | **Sheet-04 what-if inputs.** The request body of `POST /api/v1/pdm/what-if` is unspecified | The one interactive model surface in the console has no drawn form and no schema | The operation is corrected to the pdm path (§11.6, §22 row 50) and its five real constraints are wired — one item, ≤ 3 horizons, 45 s monotonic deadline, `whatif-capacity` 503 with no auto-retry, `policy-frozen-item` 422. **The form's fields remain `[OPEN]`**; the box renders the placeholder with a stated reason. **Raise with [22](22-pdm.md)** |
| **UI-OQ-10** *(inherited)* | **Print and export.** A drafting-sheet console invites printing, and a readiness figure that reaches paper without its advisory statement, classification markings, and contributor disclosure is the exact failure [27 §8] and [03 §7.3] exist to prevent | A screenshot or print is the most likely way an advisory figure is mistaken for a report | Not specified. If print is in scope, `@media print` must retain the classification **banner and footer**, the advisory statement, the contributor disclosure **and** `score_integrity`, every `n shown` bound (§6.3), and every `[GAP]` disclosure — and must state that the page is not a report. **Raise with the program** |
| **UI-OQ-51-1** | **The two `apps/practitioner` surface path segments** for `ExternalLaunch`'s `${VITE_PRACTITIONER_BASE_URL}/<surface>` | Four affordances (§18.2) cannot address their destinations precisely | Target the base URL alone with the surface named in the label and the accessible name (§18.2). **Raise with [52](52-practitioner-apps.md)**, which owns them |
| **UI-OQ-51-2** | **Is a fleet-wide index view in scope for `/pdm`, `/maintenance`, `/supply`, and `/pma`?** Every one of those routes' sheets is drawn scoped — to an item, an availability, a NIIN, a review — and [50 §4.2] routes an unscoped index for each. §12.6, §13.6, §14.6 render selectors and `EmptyState`s there | Four routes render a selector rather than a view, which may or may not be the intent | Selectors and `EmptyState`s, on the reasoning of [50 §4.2]'s `/telemetry` note (*"[i]nventing a telemetry index would be inventing a sheet"*). **Raise whether the four index views should be drawn** |
| **UI-OQ-51-3** | **How does an operator reach sheet 03?** Its only route is `/telemetry/installed-items/:installedItemId`, reachable from an item link on sheets 01, 01B, 04, 05, 07, and 10 — **and the nav item `Telemetry` redirects to `/registry`** (§4.2). An operator who knows an item's identifier can use the lookup (§4.4); one who does not must traverse the configuration tree | The most-linked screen in the console has no direct entry point | The redirect and the item links, as drawn. **Raise whether a telemetry index is wanted** — it is the same question as UI-OQ-51-2 for a fifth slug |
| **UI-OQ-51-4** | **Should the console honour `POST /authority-checks`** [31 §8] to dim adjudication controls? It is marked `advisory: true`, *"[n]ever the enforcement point"*, and exists *"so the gateway can render a queue without enabled-looking rows nobody may act on"* — but [50 §9.4] requires the console to send anyway and render the refusal, so the check buys presentation only, at one extra request per queue page | Either an extra request per page for a cosmetic dimming, or rows that look actionable and are not | **Not called.** §15.6 renders every row enabled and renders the server's refusal with its `reasons`. **Raise whether the dimming is worth the request**, noting [31 §6.4]'s matrix is separately defective (§22 row 63) |
| **UI-OQ-51-5** | **What does the console render for a multi-request route whose responses carry differing `X-Classification` labels?** Sheets 01, 01B, 02, 06, and 07 each make three to six requests (§22 row 26) | The banner is the one piece of chrome that must never be wrong, and no document says what it shows | Banner fault state and a `ProblemDetail`; the console picks no label (§4.6 rule 2). **Raise for [30 §7.3]** |
| **UI-OQ-51-6** | **Is `n shown` the right rendering for an uncountable collection**, or should the corpus publish bounded counts per scope? It affects sheet 01's `Open Risk Flags`, sheet 01B's, sheet 10's `Pending proposals — 7`, and sheet 11's `Pending remediations — 2` — **four drawn headline numbers, none of which has a source** (§22 rows 6, 24) | Four drawn figures render differently from the way they were approved | `n shown` with its stated bound, and no total. **Raise with the program**: the alternative is a bounded-count operation per scope with [06 §5]'s exclusion policy applied, which [32 §10.6] warns is itself an aggregation channel |

---

## 24. Quick reference for an implementing agent

**Read in this order. Do not start a screen before finishing step 4.**

1. **[50 — UI Design System](50-ui-design-system.md), in full.** §2 tokens, §3 components, §4 routes, §5 data, §7 disclosure, §8 accessibility, §11 the forty-four prohibitions. Nothing in this document is comprehensible without it.
2. **This document** §1.3 (what changed after [50](50-ui-design-system.md) was written — three corrections closed, one still open), §2 (layout), §3 (routes, keys, freshness, the six-outcome contract), §17 (the five states), §20 (the forty-six additional prohibitions).
3. **[30 — Gateway](30-gateway.md)** §3.2 (the **five** composed views and their fragments), §3.4 (the envelope and the six outcomes — **read the rendering rule twice**), §4.4–§4.7 (the queue's sort orders, its twenty-two filters, claim, adjudicate, freshness), §6.5 (rate limiting: `Retry-After` and nothing else), §8.1.1–§8.1.2 (agent invocation, session, logout), §8.4 (what the gateway forwards).
4. **[03 — Integration Contracts](../architecture/03-integration-contracts.md)** §4 (conventions), §7.1 (`FailurePrediction` — the null `p_failure` rule), §7.2/§7.2.1 (`Proposal`, the six authority classes, the minimum-authority table), §7.3 (`ClassificationLabel`).
5. **The screen's own section** in this document, then the sub-application document it cites, then the wireframe sheet.
6. **Before rendering any readiness figure**: [27 §3.7–§3.9](27-fleet-status.md) (disclosure, the two suppression reasons), §7.5–§7.6 (the coverage metric's four presentation rules), §8 (advisory framing and `FS-TERM-001`).
7. **Before rendering any prediction**: [22 §6.3, §9.1–§9.4](22-pdm.md) and [03 §7.1]. Branch on `reference_class`, never `tier`; never send `min_probability`.
8. **Before touching sheet 07**: §14.2 of this document, then [23 §2.2](23-pma.md). The correctness requirement on that screen is to render *less* than you are given.
9. **Before touching sheet 11**: [32 §6.1–§6.7](32-audit.md) and [03 §7.2.1]. The act is irreversible and three of its wiring facts are `[GAP]`s.
10. **[06 §7](../architecture/06-demo-decisions-and-assumptions.md)** for any quantity. **Invent none.**

**The three rules that catch the most defects, restated because they are the ones most easily lost in a screen's detail:**

- **Render the gap; do not render zero** [30 §3.4]. A `0`, a bare `—`, an absent tile, or an empty table where the answer is *unknown* is the single most damaging thing this console can do, and §17 gives every case its own component.
- **Compute nothing the server did not send.** No rollup, no rank, no ratio, no count over an unbounded set, no threshold, no banding, no signature verification. §20.1 and §20.2 enumerate every temptation, and each one has a citation.
- **When a drawn element has no field, say so.** §22 has sixty-eight rows because eleven screens were wired field by field and eleven screens' worth of gaps were found. A screen that renders a plausible value in place of a missing one converts a documented gap into an undetectable defect — and §19.3's `contract-gaps.json` is what keeps the list honest after this document stops being read.

**§21.2 is the checklist you copy into `apps/web/README.md` and tick. §22 is the list of things you will discover are missing — they are already known, and they are not yours to resolve locally.**
