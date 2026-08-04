# Build Framework 52 — Practitioner Apps (`apps/practitioner`)

| | |
|---|---|
| **Status** | Build framework, rev 1. **Binding on `apps/practitioner` — both Domino Apps and the co-resident FastAPI host process they share.** Third document of Wave 4; consumes [50 — UI Design System](50-ui-design-system.md) and re-decides nothing it decided |
| **Scope** | The single-container app shape and its FastAPI host; runtime base-path resolution; the credential and identity flow to the gateway; the two route trees; the data layer and its per-surface proxy allowlist; the full specification of **WF sheet 08 (Hypothesis Adjudication)** and **WF sheet 09 (Redesign Case Builder)**, including their adjudication actions; the iframe constraints; testing; and the Definition of Done for a component that is neither one of the seventeen services nor an agent runtime |
| **Out of scope** | The ten `apps/web` destination sheets, the shell, and the Persona Hub — [51 — Operator Console](51-operator-console.md). Tokens, primitives, the router choice, the fetch idiom, the disclosure components, and the accessibility baseline — [50](50-ui-design-system.md), imported verbatim. Session and logout operations — `apps/web`'s, and §4.7 states why they are not this app's problem either |
| **Primary design source** | [`docs/design/operator-console-wireframes.html`](../design/operator-console-wireframes.html), rev 3 as approved: **sheet 08** (`#s8`, lines 973–1013) and **sheet 09** (`#s9`, lines 1015–1066), plus sheet H's `RE` and `DE` persona cards (lines 426–437) and its footnote (line 450). Cited as **WF** |
| **Binding build documents** | [50](50-ui-design-system.md) **in full**, §6 in particular · [09](09-monorepo-and-conventions.md) §2.6, §3.1–§3.2, §4.4.2, §4.5, §8, §9 · [25](25-failure-intelligence.md) §2.1, §2.3–§2.4, §2.9, §4, §5, §7, §8, §12, §13 · [28](28-design-advisory.md) §1.2, §3.2, §3.3, §3.6, §3.7, §4.4, §4.5, §5, §6, §8, §9, §14–§16 · [30](30-gateway.md) §3.2, §3.4, §4.4–§4.7, §6.2, §8.1–§8.4 · [31](31-auth.md) §2.2, §2.4, §5.4, **§5.8**, §6.4, §8 · [42](42-redesign-case-builder.md) §13.3 |
| **Binding architecture** | [02 — Domino Platform Assessment](../architecture/02-domino-platform-assessment.md) **§4.1 in full**, §4.3 · [04](../architecture/04-subapplication-architectures.md) §9, §10, §11 · [03](../architecture/03-integration-contracts.md) §4, §4.1, §7.2, §7.2.1, §7.3, §12, §13, §15 · [06](../architecture/06-demo-decisions-and-assumptions.md) §5, §6, §7 |
| **Precedence** | [03] prevails on any contract surface. [09] prevails on layout, stack, and conventions. [02 §4.1] prevails on every platform capability claim. [50] prevails on tokens, components, routing, fetching, disclosure, and accessibility. [25] and [28] prevail on what their operations return. Where this document appears to disagree with any of them, **this document is defective** and §13 is where the disagreement should already have been recorded |
| **Verification note** | No new external library is selected here. Every library is [50]'s, at [50]'s floors, and every `[VERIFY]` in [50 §3.1], [50 §4.1], [50 §5.1], and [50 §10.1] is discharged once, for both apps, at pin time. Three new `[VERIFY]` items concern Domino console mechanics [02 §4.1] does not settle and are marked in place. No web access was available during authoring |
| **Classification** | Internal. The demonstration operates single-level at `U` [03 §12, 06 §5], by configuration and not by assumption. §8 is the enforcement path, and it matters **more** in a Domino App than in `apps/web`, for the reason [50 §7] gives and §8.1 restates |

---

## 0. How to read this document

### 0.1 What document 09 governs here, and what it does not

`apps/practitioner` is **not one of the seventeen services**. [09 §4]'s opening scopes the four-layer scaffold, the Dockerfile skeleton, the Helm chart skeleton, and the mandatory `values.yaml` shape to *"every one of the seventeen services"* — the nine under `services/` plus the eight under `platform/`. [09 §3.2]'s governance row for this directory reads *"`apps/practitioner` | Domino-hosted practitioner surfaces | This document §2.6 + 02 §4.1 constraints."* Following the precedent [40 §0.1](40-copilot.md) set for an agent runtime and [42 §19.1](42-redesign-case-builder.md) set for its Definition of Done, the consequences are enumerated rather than left to be discovered:

| Concern | Governed by | Note |
|---|---|---|
| Stack, lint, type-check, coverage floor, commits, ADRs | **[09 §2.2, §2.6, §7.4, §7.5] unchanged** | Nothing about them is service-specific. Varying one is a review rejection under [09 §8.7] |
| The four-layer service scaffold of [09 §4.1–§4.2] (`api/`, `services/`, `repositories/`, `domain/`) | **Not applicable** | The host process owns no aggregate, no repository, and no domain. §2.3 establishes its module set instead |
| The Helm chart skeleton and `values.yaml` keys of [09 §4.4] (`slug`, `apiMajor`, `database.clusterName`, `events.publishes/consumes`) | **Not applicable** | **Domino deploys this app**, and [09 §9.5 item 28] forbids deploying into Domino's namespaces. There is no chart, and four of the mandatory keys are meaningless for a component with no aggregate and no topic |
| The Dockerfile skeleton of [09 §4.3] | **Applies in substance, not in form** | §2.4. The multi-stage shape, the non-root UID, the digest pins, and [09 §9.5 item 25]'s no-install-at-start rule all bind. `readOnlyRootFilesystem` and the pod `securityContext` are **Domino's to set and we cannot assert them** — §2.4 and §13 correction 8 |
| `.env.example` and `Settings` reconciliation [09 §4.5] | **Applies in full**, to both the `VITE_*` build variables and the host's runtime variables | §2.3, §4.2. It is the only place the deployment contract with Domino is written down |
| `/healthz`, `/readyz`, `/metrics` [09 §5.6] | **Served; not necessarily observed** | §2.3. Whether anything scrapes them inside Domino's namespace is a deployment question outside this program's control |
| Structured JSON logging with `correlation_id` on every line [09 §8.6] | **Applies — and [50 §12.1] is too narrow** | [50 §12.1] disposes of this item as *"not applicable: a browser writes no log line."* True of the SPA, false of the host process, which is the first UI component in the corpus that writes log lines. §13 correction 1 |
| Events, outbox, inbox, read models, migrations, one logical database, conformance suite | **None applicable** | §12.1 dispositions each explicitly rather than dropping it, per [09 §8]'s *"removes nothing"* |

### 0.2 Markers

Following [09 §1.3], [50 §0], and [40 §0.2]:

- **`[50 §n]`**, **`[25 §n]`**, **`[28 §n]`**, **`[30 §n]`**, **`[31 §n]`**, **`[02 §n]`**, **`[WF …]`** — dictated by that document or the approved wireframe. Not negotiable at implementation time.
- **`[ESTABLISHED HERE]`** — no prior document fixes it. This document decides once, states the reasoning, and records it so that a Sonnet-tier implementing agent makes no architectural judgment call.
- **`[VERIFY]`** — a factual claim about Domino console mechanics or an external package that must be confirmed at implementation time. Proceed on the stated assumption; record the confirmation in the pull request.
- **`[OPEN]`** — genuinely undecided, listed in §14. Do not resolve one locally inside a surface.

**Read [50 §6] twice before writing a line of this app.** Then §2 and §4 of this document, then the section for the sheet you are building.

### 0.3 What landed after document 50 was authored

[50 §13] carries eighteen corrections. Four have moved, and an implementer trusting [50]'s own status column would build the wrong thing. This table is the current state; [50 §13]'s rows for these four are stale.

| [50 §13] # | Subject | Current state |
|---|---|---|
| **1** | `packages/ui` absent from [09 §3.1], §3.2, and the workspace scope | **RESOLVED.** [09 §2.6] now reads *"spanning `apps/*`, `packages/ts-common`, and `packages/ui`"*; [09 §3.1] carries the `packages/ui/` node and [09 §3.2] the governance row, both marked `[amendment 50-1]` |
| **7** | No session identity operation, no logout | **RESOLVED, for both apps.** [30 §8.1.2] now declares `GET /api/v1/gateway/session` and `POST /api/v1/gateway/session/logout`, and states the cookie and CSRF posture [31 §1.3] deferred. **[AMENDMENT]** Originally resolved for `apps/web` only, with `GET /session` unusable by `apps/practitioner`; `31 §5.8`'s correction (§4.4, a token-exchange operation rather than a caller-authority header) closed the gap — `GET /session` now works identically for this app too. `POST /session/logout` remains inapplicable here, for the unrelated reason that this app was never gateway-session-cookied — §4.7, §13 correction 3 |
| **10** | `apps/practitioner` has no client ID, no token path, no credential | **RESOLVED.** **[AMENDMENT]** `31 §5.8` originally extended `31 §5.4`'s two-credential shape to an app→gateway hop, *"recorded as an amendment ask rather than a settled mechanism."* A security review found that shape defective (one header name validating two incompatible credentials), and `31 §5.8` was corrected instead to a settled token-exchange operation, `POST /api/v1/auth/practitioner-exchange` — no longer an ask. §4 builds against the corrected mechanism; §4.6 records the alternatives considered and why this one was adopted |
| **18** | [31 §6.4]'s authority matrix omits `purge`/`rewrap`; `security_officer` in no cell | **RESOLVED for the matrix.** [31 §6.4] now carries both kinds with `counter_signature_class: fleet_authority` at class/fleet. **Also relevant here:** the same amendment pass annotated `redesign_case`'s **class** cell with dual control in both [31 §6.4] and [03 §7.2.1], closing [28 §16] correction 3. §7.7 is written against the corrected rule. The residual *"§2.5 … still say five"* half of [50]'s row is still open — [31 §2.5] reads *"03 §7.2.1's five values"* |

One further arrival, which is why §7 exists in the shape it does: **[30 §3.2] now declares a `redesign_case_detail` `ViewSpec`** at `/views/redesign-case/{case_id}`, closing [42 §18] item 13. [42 §13.3] recorded that *"30 §3.2 declares no view for a redesign case, so an adjudicator drilling into one has no composed view"* — that is no longer true, and Sheet 09 is built on the composed view rather than on a hand-rolled fan-out. **Sheet 08 has no equivalent**, and §6.1 and §13 correction 4 record the asymmetry.

**And [51 — Operator Console](51-operator-console.md) landed while this document was being written.** Three of its decisions touch this one, all compatible, and each is recorded as a reconciliation item in §14 rather than absorbed silently:

| [51]'s decision | Effect here |
|---|---|
| Its `EvidenceSummary` renders a cited strength *"verbatim and never re-banded or upgraded"* and defers the strength **meter** to this document, per [50 §3.2] | No `apps/web` component renders a band. `EvidenceStrengthMeter` (§6.3) is therefore practitioner-only, though it still lives in `packages/ui/src/evidence/` as the single home for the band vocabulary. **R-52-1** |
| **Sheet 10's adjudication panel also renders `redesign_case_detail`**, and [51] states the view *"is required by a screen this document owns, not by [52]"* | Both are true. Two surfaces over one proposal is what the claim lease and `If-Match` exist to make safe, and only Sheet 09 renders the dependency graph, the gate conditions, and the recommendation. **R-52-4**, and it is the one overlap worth reading before building §7.7 |
| It adopts [50 §9.5]'s single `VITE_PRACTITIONER_BASE_URL`, and finds that **WF sheet 00's side nav carries both surfaces too** — so there are four launch affordances, not [50 §4.3]'s two | §13 correction 23 now bears on [51] as well as on [50 §9.5]. **R-52-2** |

---

## 1. Purpose and scope

### 1.1 Two screens, two Domino Apps, and why that is a different problem

[04 §9], verbatim: *"Practitioner-facing causal exploration **is a Domino App**, since its audience is reliability engineers who hold Domino accounts."* [04 §10], verbatim: *"Engineer-facing case review **is a Domino App**, since the audience holds Domino accounts and the workflow benefits from proximity to the causal analysis."* A `grep` for *"Domino App"* across [04] returns those two paragraphs and nothing else [50 §1.5]. Exactly two, and no others.

| | Surface A | Surface B |
|---|---|---|
| Wireframe sheet | **08** — `WF #s8` | **09** — `WF #s9` |
| Title | Hypothesis Adjudication | Redesign Case Builder |
| Persona, as drawn | *"Reliability Engineer (practitioner)"* | *"PEO / Design Engineer"* |
| Owning sub-application | `failure-intel` [04 §9] | `design-advisory` [04 §10] |
| Data source | [25 §8.1]'s hypothesis operations, gateway pass-through | [30 §3.2]'s `redesign_case_detail` composed view + [28 §9.1] pass-through |
| Primary act | Adjudicate a causal hypothesis [25 §5.2] | Adjudicate a `redesign_case` `Proposal` [28 §6.4, 03 §7.2.1] |
| Adjudication path | **`failure-intel`'s own operations, direct** — §6.4 | **The gateway's unified queue** — §7.7 |
| Dual control | At S3/S4 only, per [25 §5.2]'s interim | At **class and fleet** scope, per the corrected [31 §6.4] / [03 §7.2.1] |
| Surface directory | `apps/practitioner/src/surfaces/failure-intel/` | `apps/practitioner/src/surfaces/design-advisory/` |

Six properties make this a different engineering problem from `apps/web`, all established by [50 §6] and none re-decided here:

1. **The base path is unknown at build time.** [02 §4.1]: *"The URL prefix is supplied at runtime through `DOMINO_RUN_HOST_PATH`, whereas standard build tooling bakes the base path at build time."* [50 §6.1] resolves it with `base: "./"` plus a runtime-read `<meta name="fathom-base-path">`. §3 implements that, and §3.3 fixes an interaction [50 §6.2] did not reach.
2. **One container, no separate backend.** [02 §4.1]: *"Multi-container: [n]ot supported. One image, one launch file, one pod."* So the SPA bundle and its data path are served by **one** FastAPI process [50 §6.2, §6.4]. §2 specifies it.
3. **No durable state, and no assumption of surviving a restart.** [02 §4.1]: *"Platform maintenance restarts application pods"*, *"[n]ode consolidation evicts them"*, *"[o]utput persistence: [n]ot supported — file changes inside an App container are not saved"*, and *"Domino does not serialize or isolate access to shared resources across App users … [a]utoscaled applications share temporary storage."* §2.6.
4. **The credential model is entirely different.** The SPA holds no token — same as `apps/web` — but for a different reason and by a different mechanism: the co-resident host holds a workload identity only long enough to obtain a real delegated `fathom` token by exchange, and forwards that token, never a workload credential, to `gateway` [50 §6.3, 31 §5.8]. §4.
5. **It runs in an iframe on a deployment-wide subdomain.** [02 §4.1]: *"Custom domains: [n]ot supported"*, *"Applications are served from a single deployment-wide subdomain and iframed. An iframeless view exists for applications supporting deep linking."* §3.4, §3.5, §5.1.
6. **Polling budget is halved.** [02 §4.1]: HPA *"minimum one pod, no scale-to-zero"*, and *"most of the time people are only using a single pod app."* [50 §6.4] therefore halves [50 §5.4]'s frequencies for this app. §5.4.

### 1.2 What this document does and does not govern

| Concern | Section |
|---|---|
| The image, the host process, the launch files, the restart posture | §2 |
| Runtime base path, assets, deep linking, the 404 discipline | §3 |
| The workload credential, the human identity, the outbound wire shape, the interim posture | §4 |
| Router, route trees, the `api/` layer, the per-surface proxy allowlist, freshness, mutations | §5 |
| Sheet 08 — every rendered field traced to an operation, components, the adjudication flow | §6 |
| Sheet 09 — the composed view, components, dual control, the passthrough rule in the UI | §7 |
| Classification marking, disclosure, and language discipline | §8 |
| Accessibility deltas from [50 §8] | §9 |
| Tests, named contractually | §10 |
| DO-NOT, Definition of Done, corrections, open questions | §11–§14 |

| Out of scope here | Governed by |
|---|---|
| Design tokens, the primitive package, the component inventory for `apps/web`, CSS Modules, the no-icon and no-charting-library rules | [50 §2, §3] |
| The router selection and the "no loaders" rule; the fetch library and the Zod-validate-every-response rule; the three-states rule | [50 §4.1, §5.1, §5.2, §5.5] |
| `ClassificationBanner`, `ClassificationFooter`, `AdvisoryBanner`, `ContributorDisclosure` component specs | [50 §7] |
| The accessibility baseline, the contrast table, the focus-visible generalization, the `--fs-100` floor | [50 §8] |
| The ten `apps/web` sheets, the shell, the Persona Hub, `ExternalLaunch`'s layout | [51](51-operator-console.md) |
| Session, logout, cookie attributes, CSRF for `apps/web` | [30 §8.1.2], [51] |
| Any wire type. **Never hand-written** [09 §2.6 constraint 1] | [10 §4.9](10-shared-packages.md), [09 §2.5] |
| Any quantity | [06 §7]. §5.4 derives from [50 §6.4] and invents none |
| The Failure Intelligence and Design Advisory services themselves | [25], [28] |

### 1.3 Traceability

Every element below traces to a wireframe element or a binding document. An element with no citation is a defect.

| Artifact | Source | Section |
|---|---|---|
| Two Domino Apps, one image | [02 §4.1], [04 §9], [04 §10] | §2.1 |
| Directory layout | [09 §3.1], [50 §2.1], [50 §5.2] | §2.2 |
| Host module set | **[ESTABLISHED HERE]**, from [02 §4.1] and [31 §5.8] | §2.3 |
| Dockerfile and launch files | [09 §4.3], [09 §9.5 items 25, 28], [02 §4.1] | §2.4 |
| `<base href>` + `<meta name="fathom-base-path">` | [50 §6.1], [50 §6.2]; the nested-path interaction **[ESTABLISHED HERE]** | §3.1–§3.3 |
| Domino identity assertion and the practitioner-exchange credential | [31 §5.4], [31 §5.8], [50 §6.3] | §4.2, §4.4 |
| Domino identity propagation, enhanced-JWT tier only | [02 §4.1] identity-propagation row | §4.3 |
| Per-surface proxy allowlist | **[ESTABLISHED HERE]**, on [30 §8.2] DECISION G-3's reasoning | §5.3 |
| Freshness intervals | [50 §6.4], derived from [50 §5.4] | §5.4 |
| Sheet 08 field map | [25 §2.9], [25 §4.2], [25 §8.1]; `WF #s8` | §6.1 |
| `EvidenceStrengthMeter` | [25 §4.3], [25 §4.4]; `WF #s8`'s three-segment bar; deferred to this document by [50 §3.2] | §6.3 |
| Approve ≠ admit | [25 §5.1] steps 7–8, [25 §5.3], [25 DO-NOT-6] | §6.5 |
| Sheet 09 fragment map | [30 §3.2], [28 §3.3], [28 §3.6], [28 §3.7], [28 §4.4]; `WF #s9` | §7.1 |
| Passthrough rendering rules | [28 §8], [28 DA-2], [28 DA-3] | §7.3 |
| Dependency-graph accessibility | [50 §8.5] (*"the same rules will bind it in 52"*) | §7.4, §9.2 |
| Dual control at class scope | [03 §7.2.1] as amended, [31 §6.4] as amended, [28 §16] correction 3 | §7.7 |

---

## 2. The single-container app shape

### 2.1 One image, two Domino Apps

**[ESTABLISHED HERE]** One workspace package, one Docker image, **two Domino App registrations** distinguished only by a launch-file argument.

| Decision | Reasoning |
|---|---|
| **Two Domino Apps, not one app with two routes** | [04 §9] and [04 §10] place them in two different sub-applications with two different audiences and two different owning services. [02 §4.1] gives each App *"[c]ustom URL paths only"* and *"a single deployment-wide subdomain"*, so each gets its own path and its own iframe. One App serving both would give a Reliability Engineer a URL that also serves a design authority's review surface, with no boundary between them except client-side routing — and §4.8's single rate-limit bucket would then be shared across two unrelated workloads |
| **One image** | [02 §4.1]: *"One image, one launch file, one pod."* Two images would double the CI surface, the digest-pin discipline, and the External-Secret-equivalent for zero benefit: the two surfaces share `packages/ui`, the `api/` layer, the base-path mechanism, the credential flow, and the proxy. The **only** difference is which SPA bundle is mounted and which operation allowlist is enforced (§5.3), and both are configuration |
| **Two launch files** | `app-failure-intel.sh` and `app-design-advisory.sh`, each invoking the same entrypoint with `--surface failure-intel` / `--surface design-advisory`. **[VERIFY]** that the pinned Domino version permits more than one launch file per project; [02 §4.1] establishes *"[t]en applications per project and four active application runs per project"* but does not state whether each App names its own launch file. **Fallback if it does not:** two Domino projects, one per surface, sharing the same environment image. Recorded as §14 P-OQ-1 |
| **Per-surface workload identity** | Each App registration carries its **own** client credentials (§4.2), so the two surfaces' authorization envelopes are independent. A single shared identity would give the hypothesis surface whatever the case-review surface may read |

### 2.2 Directory layout

Adds one subtree to [09 §3.1]. The `host/` subdirectory is a Python package inside `apps/`, which is new — §13 correction 2 asks [09 §3.1]/[§3.2] for the row.

```
apps/practitioner/
├── package.json                       # name "@fathom/practitioner"; depends on @fathom/ui, @fathom/ts-common
├── vite.config.ts                     # base: "./", build.assetsDir: "static", TWO rollup inputs.
│                                      #   Carries the [02 §4.1] citation for the divergence from apps/web
│                                      #   verbatim, per [50 §12.2]'s Boundary checklist
├── index.failure-intel.html           # surface A entry. Contains the placeholders §3.1 substitutes
├── index.design-advisory.html         # surface B entry. Same placeholders
├── src/
│   ├── surfaces/
│   │   ├── failure-intel/             # Sheet 08 — §6
│   │   │   ├── routes.tsx
│   │   │   ├── HypothesisList.tsx
│   │   │   ├── AdjudicationPanel.tsx
│   │   │   ├── FeatureAdmissionPanel.tsx
│   │   │   ├── TreatmentCensusDetail.tsx
│   │   │   └── main.tsx               # the surface's Vite entry
│   │   └── design-advisory/           # Sheet 09 — §7
│   │       ├── routes.tsx
│   │       ├── CaseSelector.tsx
│   │       ├── CaseReview.tsx
│   │       ├── DossierBox.tsx
│   │       ├── DependencyImpactBox.tsx
│   │       ├── CostEstimateBox.tsx
│   │       ├── RecommendationBox.tsx
│   │       └── main.tsx
│   ├── api/                           # [50 §5.2]'s five-file shape, mirrored. §5.2
│   │   ├── client.ts
│   │   ├── queryClient.ts
│   │   ├── keys.ts
│   │   ├── problem.ts
│   │   └── freshness.ts
│   ├── runtime/
│   │   ├── basePath.ts                # §3.2.  The ONLY reader of the meta tag
│   │   ├── theme.ts                   # §3.5
│   │   └── prefs.ts                   # storage, best-effort, never throws.  [50 §2.6 rule 3]
│   └── AppFrame.tsx                   # ClassificationBanner + SkipLink + <main> + ClassificationFooter
│
├── host/                              # THE CO-RESIDENT FASTAPI PROCESS.  §2.3
│   ├── pyproject.toml                 # package fathom_practitioner_host
│   └── src/fathom_practitioner_host/
│       ├── __main__.py                # argparse --surface, --port; uvicorn
│       ├── app.py                     # the single assembly point.  [09 §4.6]'s role, minus routers
│       ├── settings.py                # pydantic-settings, env_prefix FATHOM_, frozen. NO DEFAULTS (§4.2)
│       ├── basepath.py                # DOMINO_RUN_HOST_PATH -> validated, normalized prefix
│       ├── spa.py                      # static mount, head injection, catch-all
│       ├── identity.py                # Domino identity assertion: verify, never trust unverified
│       ├── credential.py              # client-credentials workload token; monotonic refresh
│       ├── allowlist.py               # the per-surface operation allowlist.  GENERATED — §5.3
│       ├── proxy.py                   # /api/ -> gateway, transparent per §4.5
│       ├── logging.py                 # structured JSON, correlation_id on every line [09 §8.6]
│       └── health.py                  # /healthz /readyz /metrics
│
├── Dockerfile
├── app-failure-intel.sh
├── app-design-advisory.sh
├── .env.example                       # BINDING [09 §4.5]. Every FATHOM_* and VITE_* variable, no real values
├── README.md                          # §12.2 copied and ticked here
└── tests/
    ├── ui/                            # Vitest + Testing Library + axe.  [50 §10.1]
    └── host/                          # pytest.  [09 §2.2]
```

`packages/ui` gains one directory for the components §6.3 and §7.4 establish:

```
packages/ui/src/evidence/              # EvidenceStrengthMeter, StrengthStatement, CitationCard,
                                       #   DependencyCompleteness, LowerBoundNotice
```

**Why `packages/ui` and not the app.** [50 §3.4] rule 1 forbids an app-local component that duplicates a `packages/ui` export, and [50 §11.2] item 13 makes it a review rejection. `EvidenceStrengthMeter` is not single-use: `WF #s10`'s adjudication panel renders *"1 causal finding (moderate strength)"* and [50 §3.5] gives sheet 10 an `EvidenceSummary`, so `apps/web` renders a strength band too. One component, one band vocabulary, one refusal to render a percentage. **[ESTABLISHED HERE]**, and flagged to [51] as reconciliation item **R-52-1** (§14).

**Where the boundary falls.** A component that presents a shared vocabulary goes in `packages/ui`; a component that composes one sheet's layout stays in `apps/practitioner/src/surfaces/`. `DossierBox` is app-local because it is Sheet 09's arrangement; `CitationCard` is shared because a citation is [28 §8.4]'s wire object and its rendering rules are correctness rules.

### 2.3 The FastAPI host process

**[ESTABLISHED HERE]** One process, four responsibilities, and **nothing else**. The module list is exhaustive; adding a fifth responsibility is a change to this document.

| Module | Responsibility | Rules |
|---|---|---|
| `basepath.py` | Read `DOMINO_RUN_HOST_PATH`, validate, normalize | Validated against `^/[A-Za-z0-9._~/-]*$`; leading `/` ensured, trailing `/` stripped, `"/"` when unset or empty. **A value failing the pattern fails startup** — it is an HTML-attribute injection sink (§3.1), and a rejected value must not be escaped-and-used |
| `spa.py` | Serve the surface's bundle; inject the head; catch-all `index.html` | The bundle is mounted at `<prefix>/static/` (`assetsDir: "static"`, [50 §6.2]). `index.html` is rendered **once at startup** into memory, because the base path cannot change without a restart and per-request templating buys nothing. §3.1, §3.4 |
| `identity.py` | Verify Domino's identity assertion on every request | §4.3. **Only** the enhanced-JWT tier is accepted. A request without a verifiable assertion is `401`, in every environment |
| `credential.py` | Obtain and hold the surface's workload token | §4.2. Client-credentials grant; refresh at 50 % of `expires_in`, measured on `time.monotonic()` [09 §9.2 item 7, **D29**]; never logged, never in a response, never in a problem detail |
| `allowlist.py` | The generated per-surface operation allowlist | §5.3. An unlisted path is `404` at the host, before any outbound call |
| `proxy.py` | Forward an allowlisted call to the gateway, transparently | §4.4, §4.5. Adds the two credentials and `X-Correlation-Id`; forwards everything else verbatim; caches nothing |
| `logging.py` | Structured JSON, `correlation_id` on every line | [09 §8.6], and see §0.1: this item binds here even though [50 §12.1] disposed of it as inapplicable to a browser. No token, no credential, and no request/response body is ever logged [31 §13 item 5] |
| `health.py` | `/healthz`, `/readyz`, `/metrics` | `/readyz` checks exactly two things: the base path validated at startup, and the workload token obtainable. It does **not** check the gateway's health — a practitioner surface that reports itself unready because the gateway is slow adds nothing and removes a diagnostic |

**Five things the host must never do**, each with the reasoning that makes it a defect rather than a preference:

1. **No response cache of any kind, for any duration.** [30 §3.5] forbids the gateway from caching a domain response — *"[a] response cache would be a read model by the back door"* — and [50 §5.1] concludes that *"the only cache that exists anywhere between the sub-applications and the operator is the browser's."* A cache in this process would be worse than the gateway's would have been: [02 §4.1] records that *"Domino does not serialize or isolate access to shared resources across App users"*, so one process's cache is a shared cache across viewers who may hold different clearances, and a cache hit would serve one viewer's authorized view to another. `host-no-response-cache` asserts it.
2. **No per-viewer server-side state, no session store, no sticky assumption.** [02 §4.1]: pods are restarted and evicted without notice; *"[a]utoscaled applications share temporary storage"*; session affinity is *optional*. Any state held between requests is state that vanishes or leaks. §2.6.
3. **No write to the filesystem beyond `/tmp` for the process's own lifetime.** [02 §4.1]: *"[f]ile changes inside an App container are not saved."* Nothing is written that anything later reads.
4. **No audit write.** [09 §4.4.2]'s sanctioned edge set gives `audit` an inbound edge from any service or agent runtime; it gives none to a Domino-hosted app, and the gateway already writes the audit record for every call it receives [30 §5.8]. A second, unreconciled record written by this app would be redundant, not merely worse-than-nothing. **[AMENDMENT]** An earlier revision of this rule worried the audit record might name the workload rather than the human, if the gateway merely recorded rather than authorized against a caller-authority credential — moot since `31 §5.8`'s correction (§4.4): the exchanged token *is* the human's own `fathom sub`, so the audit record the gateway writes already names the human, with no second mechanism needed.
5. **No event bus, no database, no direct call to any sub-application.** [09 §9.5 item 30] and [03 principle 2]. Every outbound call goes to the gateway; the host is a client, exactly as [42 §13.3] says of the same directory: *"[i]t does not host the agent, does not proxy tool calls, and holds no agent credential. It calls the gateway like any other client."*

### 2.4 The Dockerfile, the launch files, and what we cannot assert

```dockerfile
# apps/practitioner/Dockerfile — multi-stage, per [09 §4.3]'s shape.
# Bases pinned BY DIGEST, per [09 §8.6].  No install at container start [09 §9.5 item 25, D26].

FROM node:<ver>@sha256:<digest> AS spa
WORKDIR /w
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY packages/ui packages/ui
COPY packages/ts-common packages/ts-common
COPY apps/practitioner apps/practitioner
RUN --mount=type=cache,target=/pnpm corepack enable && pnpm install --frozen-lockfile \
 && pnpm --filter @fathom/practitioner build          # emits dist/failure-intel and dist/design-advisory

FROM python:<ver>@sha256:<digest> AS host
WORKDIR /w
COPY apps/practitioner/host ./host
RUN pip install --no-cache-dir ./host                  # BUILD time, never start time

FROM python:<ver>-slim@sha256:<digest> AS runtime
COPY --from=host /usr/local/lib/python*/site-packages /usr/local/lib/python*/site-packages
COPY --from=host /usr/local/bin /usr/local/bin
COPY --from=spa  /w/apps/practitioner/dist /srv/spa
USER 65532:65532
ENTRYPOINT ["python", "-m", "fathom_practitioner_host"]
```

```sh
# apps/practitioner/app-failure-intel.sh   — the Domino launch file
exec python -m fathom_practitioner_host --surface failure-intel --port "${DOMINO_APP_PORT:?}"
```

| [09 §8.6] item | Disposition |
|---|---|
| Multi-stage; non-root UID 65532 | **Honoured in the image.** `USER 65532:65532` in the runtime stage |
| `readOnlyRootFilesystem: true`, `capabilities: drop: [ALL]` | **Cannot be asserted.** Domino writes the pod spec; [09 §9.5 item 28] forbids us deploying into Domino's namespaces. The image is *compatible* with a read-only root — nothing is written outside `/tmp` (§2.3 rule 3) — and that compatibility is what the README records. §13 correction 8 asks [09 §8.6] for the disposition rule |
| No package or source installation at container start | **Honoured, and load-bearing.** [02 §4.1]'s own engineering called start-time installation *"categorically incompatible with air gap"* [**D26**]. The launch file contains one `exec` and no package manager. `host-launchfile-no-install` greps both launch files |
| Digest pins; image promoted by digest | **Honoured for our bases.** Whether Domino's environment mechanism preserves the digest through its own build is **[VERIFY]** |
| `/healthz`, `/readyz`, `/metrics` | Served (§2.3). Scraping is Domino's namespace, not ours |
| `.env.example` complete, no secret values | **Binding in full.** §4.2 enumerates every variable. It is the deployment contract with whoever registers the App in Domino |
| Structured JSON logging with `correlation_id` | **Binding.** §2.3 |
| Argo CD Application | **Not applicable.** Domino deploys this app |

The port comes from configuration, never a literal. **[VERIFY]** the environment-variable name Domino supplies for an App's listen port in the pinned version; [02 §4.1] does not state one, and inventing a number would violate [09 §9.5 item 31]. The launch file's `:?` makes a missing value a startup failure rather than a silent default.

### 2.5 What is emphatically *not* here

- **No nginx.** [02 §4.1] records the multi-container workaround as *"a single container running multiple processes behind a local nginx, characterized internally as 'fairly gross' and 'not super elegant.'"* One FastAPI process serves the static bundle and the proxy, so the second process and the reverse proxy in front of it are both unnecessary. **[ESTABLISHED HERE]** — this is the concrete reason [50 §6.4] could say *"[t]he single Domino App container's FastAPI process serves the bundle and proxies `/api/` calls"* without qualification.
- **No server-side rendering.** [02 §4.1]: *"Server-side rendering (Next.js) | Not supported; question unanswered."* [50 §4.1] already rejected React Router's framework mode on this basis.
- **No Domino Extension.** [02 §4.1] makes Extensions *"GA, **Domino Cloud only**"* and *"[a]bsent from the self-managed 6.2 documentation tree, which matters because the program's production target is self-managed OpenShift and air-gapped enclaves"*, with the explicit consequence that *"Domino Apps are the portable fallback that document 04 specifies."* [09 §9.5 item 27] forbids assuming a capability [02] rules out. **The App shape is built; the Extension is not.** If Extensions become available, the App mounts unchanged inside one — Extensions require *"extended identity propagation on the backing application — the only hard requirement"*, which §4.3 already provides for. §14 P-OQ-2.
- **No WebSocket, no `EventSource`, no long-poll.** [50 §5.4]'s five reasons, of which reason 4 names this app specifically.
- **No agent hosted here.** [42 §13.3]: *"[i]t does not host the agent."* The Redesign Case Builder runs under `agents/redesign-case-builder/` and is invoked through [30 §8.1.1]'s gateway-owned operations.

### 2.6 Restart, eviction, and the absence of durable state

[02 §4.1], four rows read together: availability is *"[w]eak for always-on use"* with a *"99%"* SLA; *"[p]latform maintenance restarts application pods"*; *"[n]ode consolidation evicts them; one customer defect reported 'most Apps get shutdown overnight'"*; and idle shutdown is *"[d]ocumentation contradictory; effectively absent."*

**[ESTABLISHED HERE]** The consequences, each an implementable rule:

| Rule | Consequence if broken |
|---|---|
| The host holds no state that a later request reads, except the workload token and the rendered `index.html`, both reconstructible at startup | A restart mid-adjudication would otherwise lose a claim or a half-built form with no way to recover it |
| The SPA treats every mutation as if the process could vanish immediately after it | This is why `Idempotency-Key` is generated **once per user action** and reused across retries [50 §5.6]: a retry after a restart must not create a second effect |
| A claim lease survives a restart because it is held by the **owning sub-application**, not here | [30 §4.6]: *"a lease held anywhere but the transactional store that performs the state change is not a lease."* The same argument, one hop further out |
| The SPA recovers from an abrupt reload by reading its state from the URL | [50 §4.4]'s query-parameter rule and [50 §5.7]'s four-kinds table are what make this work. There is no in-memory wizard |
| A restart is not an error state and is never reported as one | A `502`/`503` from the iframe during a pod restart renders Domino's own error page, not ours; there is nothing to catch. The SPA's own retry with backoff [50 §5.4] covers a restart that lands mid-poll |

### 2.7 Timeout and scaling consequences

| Property [02 §4.1] | Consequence here |
|---|---|
| nginx connect/read timeout **300 s** default, admin-tunable, *"[n]o per-application override"* | **No request this app initiates may be expected to exceed 300 s.** Every operation §5.3 allowlists is well inside it: [30 §3.2]'s `redesign_case_detail` budget is 4 000 ms, the queue operations are single-hop, and [25 §8.1]'s reads are single-slug. The host sets its own outbound deadline **well below** the ceiling and returns `504` with an RFC 9457 body rather than letting nginx return an HTML error page the SPA cannot parse. The deadline is required configuration with no default (§4.2) |
| HPA since 6.2, *"minimum one pod, no scale-to-zero, scale-up in approximately 20 seconds"*, and *"most of the time people are only using a single pod app"* | [50 §6.4]'s halved polling intervals. §5.4 |
| *"Domino does not serialize or isolate access to shared resources across App users"* | §2.3 rules 1–3 |
| Per-project caps: *"[t]en applications per project and four active application runs per project"* | Two Apps consume two of ten. Not a constraint at demonstration scale; recorded so a third practitioner surface is a capacity question rather than a surprise |
| Anonymous access *"[b]eing removed"*, with *"an applications authorization overhaul … targeted for 6.4"* | **The app never relies on anonymous access, in any environment.** §4.3's `401` on a missing identity assertion is unconditional, so the removal is a no-op for us |
| Endpoint payload ceiling 10 MB, timeout not cancelled [02 §4.3] | **Not reachable from here.** Neither surface calls a Domino Endpoint; [50 §14] UI-OQ-9's what-if surface is sheet 04's, in `apps/web` |

---

## 3. Runtime base path, assets, and deep linking

### 3.1 The injected head

[50 §6.1] fixes the mechanism: *"[r]ead at runtime from a `<meta name="fathom-base-path">` tag the serving process writes from `DOMINO_RUN_HOST_PATH`, with `"/"` as the fallback. The SPA never reads the environment variable itself — it has no access to it."*

Each `index.*.html` ships two placeholders as the **first two elements** of `<head>`:

```html
<head>
  <base href="__FATHOM_BASE_HREF__">
  <meta name="fathom-base-path" content="__FATHOM_BASE_PATH__">
  <meta charset="utf-8">
  ...
</head>
```

`spa.py` substitutes both once at startup, from `basepath.py`'s validated value, HTML-attribute-escaped:

| Placeholder | Value for `DOMINO_RUN_HOST_PATH=/apps/abc123` | Value when unset |
|---|---|---|
| `__FATHOM_BASE_PATH__` | `/apps/abc123` | `/` |
| `__FATHOM_BASE_HREF__` | `/apps/abc123/` | `/` |

Three rules:

1. **Substitution is a whole-token replacement of a placeholder that cannot occur elsewhere**, never a regex over the document. `host-head-injection-escapes` asserts that a base path containing `"`, `<`, or `&` is rejected at startup by `basepath.py`'s pattern (§2.3) and therefore never reaches the substitution at all — defence in depth, since the escape is applied anyway.
2. **The rendered document is produced once and served from memory.** `DOMINO_RUN_HOST_PATH` cannot change without a restart, and a restart re-renders it.
3. **No other runtime value is injected into the document.** No identity, no token, no `authority_classes`, no classification label. Everything else arrives through the data layer, where it is validated [50 §5.2]. An identity injected into HTML is an identity the browser could be persuaded to lie about, and [31 §13 item 15]'s rule — *"[d]o not trust a caller's assertion of who its end user is"* — applies to our own document as much as to a request body.

### 3.2 How the SPA reads it

```ts
// apps/practitioner/src/runtime/basePath.ts
// THE ONLY reader of the meta tag, anywhere in this app.  [50 §6.1]
// There is no import.meta.env.BASE_URL here: apps/web reads that, this app must not
// (Vite's base is "./" for this app, so BASE_URL is "./" and useless as a basename).

export const BASE_PATH: string =
  document.querySelector<HTMLMetaElement>('meta[name="fathom-base-path"]')?.content || "/";

export const API_PREFIX: string = BASE_PATH === "/" ? "/api" : `${BASE_PATH}/api`;
```

`createBrowserRouter(routes, { basename: BASE_PATH })` [50 §4.1]. `createClient({ baseUrl: API_PREFIX })` [50 §5.2]. **`API_PREFIX` is derived from `BASE_PATH`, in one place, so the router and the fetch client cannot disagree.** [50 §10.2]'s `ui-practitioner-basename-from-runtime` asserts the basename comes from the tag and never from a build constant; `pui-api-prefix-derived` extends it to the client's base URL.

### 3.3 The nested-deep-link asset problem, and why `<base href>` is required

[50 §6.2] sets `base: "./"` and `build.assetsDir: "static"` as *"[t]wo mitigations for one unresolved platform defect"* — the February 2026 ticket in which the proxy was *"not forwarding sub-path asset requests (`/assets/*.js`, `/assets/*.css`)."* That decision stands and is not re-litigated. **But `base: "./"` alone is broken by the router.**

The failure, concretely. With `base: "./"`, Vite emits `<script src="static/index-<hash>.js">`. `spa.py`'s catch-all serves the same document at `/<prefix>/hypotheses/9f2c…` (§3.4 — it must, or a refresh 404s). A relative URL resolves against the *document's* directory, so the browser requests `/<prefix>/hypotheses/static/index-<hash>.js`, which does not exist. **Every deep link loads a blank page** — and [02 §4.1] makes deep linking a requirement, not a nicety: *"[a]n iframeless view exists for applications supporting deep linking."*

**[ESTABLISHED HERE]** `<base href="<prefix>/">`, injected as the first element of `<head>` (§3.1). Relative URLs then resolve against the App's root regardless of the current route, and `base: "./"`'s whole purpose — never depending on a correct absolute prefix being baked at build time — is preserved. Two consequences, both testable:

- **Every in-app URL is router-generated or absolute.** `<base>` changes the resolution of *all* relative URLs, so a hand-written relative `href` or `src` anywhere in the app would silently resolve against the prefix rather than the current route. `pui-no-relative-url-literal` asserts no relative `href`/`src`/`action` literal exists in either surface's source outside the emitted asset tags.
- **A `<base>` with a wrong value breaks everything at once, visibly.** That is the desired failure mode: a misconfigured prefix produces an obviously blank app on first load rather than a subtly broken deep link discovered weeks later.

The rejected alternative was a build-time placeholder in Vite's `base` substituted by the host at startup. It works, and it is what some SPA-on-unknown-prefix setups do — but it re-introduces string surgery over the emitted JavaScript bundle, not only the HTML, and it contradicts [50 §6.2]'s explicit `base: "./"`. `<base href>` is additive to [50 §6.2] rather than a replacement for it, which is why it is recorded as **§13 correction 1** against [50 §6.2] (an omission to fill, not a decision to reverse) rather than taken as a licence to re-decide.

### 3.4 Catch-all, and the 404 discipline

`spa.py` mounts three things under the prefix, in this order:

| Path | Behaviour |
|---|---|
| `<prefix>/static/*` | The built bundle, from `/srv/spa/<surface>/static`. `404` for a miss — never the SPA document, because an HTML body returned for a `.js` request produces an unreadable MIME error instead of a legible 404 |
| `<prefix>/api/*` | `proxy.py` (§4.4), gated by `allowlist.py` (§5.3) |
| `<prefix>/*` and `<prefix>` | The rendered `index.html`. This is [50 §6.4]'s *"FastAPI catch-all returns `index.html`"*, and it is what makes a refresh on a nested route work |

Two rules:

1. **The catch-all returns `200` with `index.html`, and the SPA's own `NotFound` route decides.** A `404` status with an HTML body would be correct HTTP and would break the router, which is why [50 §6.4] specifies the catch-all rather than a status-aware handler.
2. **A path outside the prefix is `404` at the host.** The App is served under a prefix Domino chose; a request outside it is not ours to answer.

### 3.5 The iframe: theme, top-level navigation, and subresources

[02 §4.1]: *"Iframe rendering | Default … Applications are served from a single deployment-wide subdomain and iframed."* [50 §6.5]'s five rules bind, implemented as follows:

| [50 §6.5] rule | Implementation |
|---|---|
| No `window.top` access, no top-level navigation, no assumption of being a top-level document | `pui-no-window-top` asserts no `window.top`, `window.parent.location`, `top.location`, or `window.open` targeting `_top`/`_parent` appears in either surface. The only outbound affordance is `methodology_ref`-style content links, which open in a new tab with `rel="noopener noreferrer"` |
| Theme from `?theme=` or a host `postMessage`, else `prefers-color-scheme` | `runtime/theme.ts`, in that precedence order. `?theme=` accepts exactly `light \| dark \| system`; any other value is ignored, not defaulted. **`postMessage` is accepted only from an origin in `FATHOM_ALLOWED_THEME_ORIGINS`**, injected as configuration, never `"*"`; an unlisted origin's message is dropped silently. `pui-postmessage-origin-checked` asserts no `postMessage` listener without an origin check |
| Theme persistence is best-effort | `runtime/prefs.ts` wraps every `localStorage` access in `try/catch` and **returns a default rather than throwing**. Third-party-iframe storage is partitioned [50 §2.6 rule 3], so a `SecurityError` on read is an expected condition, not an exception path. `pui-prefs-never-throws` asserts it with storage stubbed to throw |
| No external subresource of any kind | [50 §2.3]'s no-web-font rule is the concrete case, and it already holds by construction: both type stacks are system-resolved. `pui-no-external-subresource` asserts no `http(s)://` URL appears in any emitted asset, any CSS `url()`, or any `<link>`/`<script>`/`<img>` in either `index.*.html`. The administrator-managed CSP allowlist [02 §4.1] is then never exercised, which is the point |
| Deep linking supported, so the iframeless view is available | §3.3, §3.4, and §5.1's route trees. Every rendered state has a URL |

**The theme's one honest gap, stated rather than papered over.** Nothing in Domino sends a `postMessage`, and [02 §4.1] describes no host-to-app channel. So in practice the theme comes from `?theme=` on the launch URL or from `prefers-color-scheme` — which, inside an iframe, *"reflects the browser, not the Domino chrome"* [50 §6.5], so a practitioner surface may render dark inside a light Domino page. [50 §6.5] already accepts that: *"[t]he override is the mitigation; the mismatch is otherwise expected and acceptable."* The `?theme=` path is only useful if the launching link supplies it, and **`apps/web`'s `ExternalLaunch` is the only launcher that knows the user's resolved theme** [50 §5.7]. Reconciliation item **R-52-2** asks [51] to have `ExternalLaunch` append `?theme=<resolved>`; until it does, `prefers-color-scheme` is the operative path and the app is fully legible either way (§9.1).

---

## 4. Credential and identity flow

### 4.1 What is settled, and what this document builds against

Three facts the implementer must hold:

1. **[31 §2.2] is settled.** *"The `fathom` realm is the authority. Domino's Keycloak is configured to broker to it as an external OIDC identity provider. Identity never flows the other way."* Its diagram puts *"Workspaces · Jobs · Apps"* on the Domino side, holding *"Domino session cookies"*, and separates them from *"`apps/web` · gateway · 17 services · agents"*, which hold `fathom`-realm tokens.
2. **[31 §2.2]'s warning is settled and must not be reasoned around.** Federation *"does not put caller identity on a Domino Endpoint invocation … [t]hat gap is what §5 exists to close, and it must not be reasoned away by pointing at federation."*
3. **[31 §5.8] is settled, not an amendment ask.** **[AMENDMENT]** It originally extended [31 §5.4]'s two-credential shape from an Endpoint-proxy call to an app→gateway hop, recorded then as *"an amendment ask rather than a settled mechanism."* A security review found that shape defective — one header name validating two structurally incompatible credentials — and [31 §5.8] was corrected instead to a token-exchange operation, `POST /api/v1/auth/practitioner-exchange` (§4.4). This is a settled mechanism, built against and buildable as stated, not an open ask.

**What this document builds against: [31 §5.8] exactly as corrected**, with one addition it leaves implicit and §4.3 makes explicit — *how* the app comes to hold a Domino-linked identity it can hand onward without asserting it. §4.6 records the alternatives considered and why the token-exchange mechanism was adopted, and §4.7 states that the write path is authorized, not blocked, now that the mechanism has landed.

### 4.2 The workload credential

**[ESTABLISHED HERE]**, implementing [31 §5.8]'s *"client-credentials **workload identity** over the sanctioned `domino-compute → gateway` NetworkPolicy edge [09 §4.4.2]."*

| Property | Rule |
|---|---|
| Grant | OAuth 2.0 client credentials against the `fathom` realm's token endpoint. One confidential client **per surface** (§2.1), so the two surfaces' authorization envelopes are independent |
| Audience | The token's `aud` must contain `gateway`, per [30 §5.1]'s claims-validated row. A token minted without it is rejected at the gateway, which is the correct failure |
| Custody | Injected as environment variables by **Domino's** project/environment mechanism. **This is not the program's External Secrets path** [09 §2.4, §4.5], because [09 §9.5 item 28] forbids us deploying the pod. §13 correction 5 raises it, and it is the single most accreditation-relevant consequence of hosting a program surface on Domino |
| Refresh | At 50 % of `expires_in`, measured with `time.monotonic()`. **Never a wall clock** [09 §9.2 item 7, **D29**] — the STIG rule cited there permits unlimited backward steps, and a backward step with wall-clock refresh arithmetic stalls the refresh indefinitely, at which point every viewer of the App sees `401`s with no explanation |
| Non-disclosure | Never logged, never in a response header or body, never in an RFC 9457 `detail`, never in the rendered `index.html`. [31 §13 item 5]. `host-no-credential-in-output` asserts the client secret and the access token appear in no log line, no response, and no problem body |
| Failure to obtain | `/readyz` fails; every `/api/` request returns `503` with a stable problem type. **Never a degraded read against no credential**, and never a fallback to an unauthenticated call [02 §4.1]'s soon-to-be-removed anonymous access might have permitted |

`.env.example`, complete — the deployment contract with whoever registers the App:

```
# ---- surface selection (also passed on the launch-file command line) ----
FATHOM_SURFACE=                       # failure-intel | design-advisory.  REQUIRED, no default
# ---- runtime base path (supplied by Domino) ----
DOMINO_RUN_HOST_PATH=                 # e.g. /apps/abc123.  Absent -> "/"  [02 §4.1]
# ---- the workload credential (§4.2).  Injected by Domino's environment mechanism ----
FATHOM_OIDC_TOKEN_ENDPOINT=           # REQUIRED
FATHOM_OIDC_CLIENT_ID=                # REQUIRED, per surface
FATHOM_OIDC_CLIENT_SECRET=            # REQUIRED, per surface.  NEVER a real value in this file
# ---- the human identity assertion (§4.3) ----
FATHOM_DOMINO_IDENTITY_ISSUER=        # REQUIRED.  Domino Keycloak's issuer
FATHOM_DOMINO_IDENTITY_JWKS_URL=      # REQUIRED
FATHOM_DOMINO_IDENTITY_HEADER=        # REQUIRED.  [VERIFY] the header Domino uses for the JWT tier
# ---- the gateway ----
FATHOM_GATEWAY_BASE_URL=              # REQUIRED
FATHOM_OUTBOUND_DEADLINE_MS=          # REQUIRED, no default.  Must be < 300 000 [02 §4.1]; §2.7
# ---- the iframe (§3.5) ----
FATHOM_ALLOWED_THEME_ORIGINS=         # comma-separated.  Empty means postMessage is not accepted
FATHOM_APP_ORIGIN=                    # REQUIRED.  The Origin check of §4.5
# ---- build-time (Vite).  No runtime value belongs here ----
# (none: every runtime value reaches the SPA through §3.1's head or the data layer)
```

**No setting has a default except the base-path fallback.** This is [28 §5.4]'s pattern, adopted for the same reason: *"[a] default here would be an invented number that ships, gets used, and is never revisited."*

### 4.3 The human identity — Domino identity propagation, enhanced-JWT tier only

[31 §5.8] says the caller's authority is *"the Domino-session-linked `fathom` `sub` from the broker's linked record."* It does not say how the app obtains it. **[ESTABLISHED HERE]**, from [02 §4.1]'s identity-propagation row, which is the only mechanism the corpus documents:

> *"Identity propagation | GA, and strong | Three tiers: **basic username header**, **enhanced JWT**, and **extended propagation** permitting an application to act with the user's full permissions subject to explicit user consent, default eight hours and up to thirty days. **Default execution identity is the publisher's, not the viewer's.**"*

| Rule | Reasoning |
|---|---|
| **Identity propagation must be enabled on both App registrations.** Without it the App executes as the *publisher*, and every viewer would be attributed to whoever published it | [02 §4.1]'s last sentence above. A README item and a `.env.example`-adjacent deployment note, because it is a Domino console setting we cannot assert from code — but the host **can** detect its absence, and does: no assertion means `401` |
| **Only the enhanced-JWT tier is accepted. Tier 1 — the basic username header — is refused** | A plain header can be set by anything that can reach the host. If the browser can set it, the identity binding is worthless and every viewer can impersonate every other. A signed JWT cannot be forged by the browser. `host-rejects-username-header-tier` asserts a request carrying only a username header is `401` |
| The assertion is **verified**: signature against `FATHOM_DOMINO_IDENTITY_JWKS_URL`, `iss` exact-match, `exp`, `nbf`, and `aud` | [30 §5.1]'s validation discipline, applied one hop out. Asymmetric algorithms only, allowlisted — `alg: none` and every HMAC family rejected, for [30 §5.1]'s stated reason |
| The host **does not decode, interpret, or map** the subject to a `fathom` `sub` itself | [31 §2.2]'s linking rule makes the broker's linked record the mapping, and it lives in Keycloak. An app that mapped names locally would be a second identity authority — reason 2 of [31 §2.2]'s four |
| **[AMENDMENT — corrected.]** The host **presents the verified assertion, once, to the exchange operation** (`POST /api/v1/auth/practitioner-exchange`, §4.4) — it is never forwarded to `gateway` itself | This is what makes it *not* a claimed subject. [31 §13 item 15]: *"[d]o not trust a caller's assertion of who its end user is."* `auth` verifies the signed assertion for itself at exchange and returns an ordinary delegated `fathom` token; every subsequent `gateway` call carries only that token, identical in shape to any other delegated call |
| No identity is ever accepted from the request body, from a query parameter, or from a client-settable header | `host-no-claimed-subject` asserts a body or query field named `sub`, `subject`, `user`, `principal`, or `on_behalf_of` is rejected with `400`, not ignored |

**A note on cookies, and a correction to the symmetry [50 §6.3] draws.** [50 §6.3] closes with *"[t]he one thing that does **not** differ: both apps hold a cookie and no token."* For `apps/web` the cookie is load-bearing — it *is* the session [31 §4.1]. For `apps/practitioner` it is not, and must not be relied on: the app runs in a **third-party iframe**, where cookies are partitioned or blocked in current browsers, so Domino's session cookie may simply not be sent. The identity therefore arrives on the **server-injected signed assertion**, which reaches the host regardless of the browser's cookie policy. §13 correction 1 records the refinement. The practical rule: `credentials: "same-origin"` on the fetch client [50 §5.2] because the request is same-origin and there is no reason to strip it — **and nothing in either surface depends on a cookie arriving.**

### 4.4 The outbound wire shape

**[AMENDMENT — corrected.]** This section originally implemented a two-credential shape reusing `31 §5.4`'s `X-Fathom-Caller-Authorization` header for a bearer value with none of that header's actual claims — a security review identified this as one header name validating two structurally incompatible credentials, with no document specifying which validator applied at the gateway. `31 §5.8` now adopts §4.6 alternative (a) below instead: a token-exchange operation on `auth`. The host exchanges the verified Domino identity JWT for a real, short-lived `fathom`-realm delegated access token (`POST /api/v1/auth/practitioner-exchange`, once per session and refreshed as it nears expiry — not per call), and every subsequent call to `gateway` carries **exactly one credential**, identical in shape to every other delegated call in this program:

```http
GET /api/v1/failure-intel/hypotheses?status=awaiting_adjudication&limit=50 HTTP/1.1
Host: <gateway>
Authorization: Bearer <the exchanged fathom-realm delegated token>   ◀── [31 §5.8, §3.2]
X-Correlation-Id: 0f2c8f5a-…                                        ◀── forwarded, or minted if absent
Accept: application/json
```

For a state-changing call, additionally:

```http
POST /api/v1/failure-intel/hypotheses/9f2c…/adjudicate HTTP/1.1
Authorization: Bearer <exchanged fathom-realm delegated token>
X-Correlation-Id: 0f2c8f5a-…
Idempotency-Key: 8fd1…                    ◀── from the SPA, one per user action  [50 §5.6]
If-Match: "…"                             ◀── from the SPA, the claimed ETag, verbatim  [25 §5.2]
Origin: https://<domino-subdomain>        ◀── checked at the host against FATHOM_APP_ORIGIN
Content-Type: application/json
```

Four properties, each of which a reviewer should be able to check in one place:

1. **One credential, verified once at exchange, never re-verified per call, never synthesized.** The host exchanges the Domino identity JWT for a `fathom` token (§4.2) and forwards that token unchanged on every call, exactly as `31 §5.3`'s "forwarded unchanged" rule already requires for every other delegated caller.
2. **No `X-Fathom-Caller-Authorization` is ever sent by this app.** That header remains exclusively `31 §5.4`'s Endpoint-proxy credential. The removal of the second header is the point of the correction — one name, one meaning, corpus-wide.
3. **The `Idempotency-Key` and `If-Match` originate in the SPA and are forwarded verbatim.** The host **never** generates an `If-Match` — [30 §4.6]: *"[a] gateway-generated ETag would defeat the entire concurrency mechanism while appearing to satisfy it."* The identical argument applies to a *host*-generated one, one hop further out. `host-never-synthesizes-if-match` asserts no outbound request carries an `If-Match` absent from the inbound one.
4. **Nothing else is added.** Explicitly not: any header a sub-application might authorize on [30 §8.4]. `host-adds-only-declared-headers` asserts the outbound header set is exactly the inbound set, minus the drops below, plus `Authorization` and `X-Correlation-Id`.

**Dropped:** the inbound Domino identity header itself (consumed at exchange, never forwarded past it), any inbound `Authorization` (the browser has no business sending one), `Host`, and hop-by-hop headers.

### 4.5 Pass-through transparency, and the Origin check

The host is a proxy, and [30 §8.4]'s framing applies verbatim: *"a proxy that changes things is a source of defects nobody can locate."* Its transparency rules are adopted as contract terms for the host, tested in §10.

| Direction | Rule |
|---|---|
| Request → gateway | Query parameters, `Content-Type`, `Accept`, `Idempotency-Key`, `If-Match`, `If-None-Match` forwarded **verbatim**. Body forwarded byte-identically |
| Gateway → response | Status code, `Content-Type`, and body **byte-identical**. `ETag`, `Retry-After`, `X-Classification`, `Deprecation`, `Sunset`, `Idempotency-Replayed`, `Location` forwarded **verbatim** |
| Gateway → response | **RFC 9457 problem bodies are never re-wrapped.** An upstream `urn:fathom:problem:failure-intel:…` reaches the SPA unchanged. [30 §8.4]: *"[a] re-wrapped problem detail destroys the stable-`type` contract."* The host's own problem types cover only conditions the host detected: `unauthenticated` (no verifiable assertion), `operation-not-allowlisted`, `credential-unavailable`, `upstream-deadline-exceeded`, `origin-rejected` |
| Gateway → response | `ETag` forwarding is load-bearing for [**D16**] and for [25 §5.2]: adjudication carries `If-Match` on the claimed ETag, and a host that regenerated ETags would break the claim mechanism while appearing to work |
| Unsafe methods | **`Origin` must equal `FATHOM_APP_ORIGIN`; a request with no `Origin` on an unsafe method is rejected `403`.** Reasoning: the host authenticates on a **server-injected** assertion rather than a cookie (§4.3), so classic CSRF token machinery has nothing to protect — but a cross-site `POST` from another page in the same browser would still arrive carrying Domino's injected identity. The `Origin` check is the mechanism that stops it, and it is the direct analogue of [30 §8.1.2]'s double-submit token for a cookie-borne session. `host-origin-required-on-unsafe` asserts it |
| Everything | **Nothing is cached, at any layer, for any duration** (§2.3 rule 1) |

### 4.6 The alternatives considered, and why (a) was adopted

Three alternatives were weighed for closing `31 §5.8`'s gap. (a) is now `31 §5.8`'s actual resolution (§4.4 above); (b) and (c) are recorded so neither is re-proposed.

| Alternative | Assessment | Status |
|---|---|---|
| **(a) A token-exchange operation on `auth`** — RFC 8693, taking the verified Domino identity JWT and returning a short-lived `fathom` access token for that human | Reuses [31 §4.2]'s exchange machinery, produces a token the gateway already validates unchanged [30 §5.1], removes the need for the gateway to understand a second credential shape, and makes the ABAC decision unambiguously about the human. Gives the audit record the human's `sub` with no new mechanism | **Adopted.** `31 §5.8`, `POST /api/v1/auth/practitioner-exchange`. §4.4 implements it |
| **(b) Domino's extended identity-propagation tier** — [02 §4.1]: *"permitting an application to act with the user's full permissions subject to explicit user consent, default eight hours and up to thirty days"* | Gives the host a **Domino-side** credential acting as the user. It is still not a `fathom`-realm token, so the gateway must still broker or exchange — (a) by another route, with a consent prompt and a 30-day grant attached | **Rejected** in favor of (a), which needs no Domino consent flow |
| **(c) A practitioner OIDC public client**, authorization-code + PKCE, in the iframe | Puts a token in the browser, which [31 §4.1] and [50 §6.3] both forbid — *"a token in a browser is a token in every browser extension the browser has installed."* Also depends on storage for `state`/`nonce`, partitioned in a third-party iframe | **Rejected.** Not built against |

**The invariant (a) preserves:** the SPA holds no credential, and the host adds nothing to a request that a sub-application might authorize on.

### 4.7 The write path is authorized, not blocked

**[AMENDMENT — this section previously described an interim, narrowest-workload-envelope posture that blocked every adjudication attempt pending `31 §5.8`'s confirmation. That confirmation has landed (§4.4), so the interim no longer applies.]** With the exchanged token carrying the human's real `sub` and real `authority_classes` (§3.2's identity block, byte-identical to `apps/web`'s), the owning sub-application's ABAC check runs against the actual adjudicator, exactly as it does for `apps/web`. No narrowed workload envelope, no blanket refusal, no `IdentityBlock` gap — `GET /api/v1/gateway/session` (`30 §8.1.2`) returns the same identity block for this app that it returns for `apps/web`, and the console-parity concerns §4.7 previously raised (a cross-viewer, cross-clearance read behind a shared workload identity) do not arise, because there is no shared workload identity on the read path — every read and every write carries the individual human's own exchanged token.

Historical note, retained because it states the property correctly even though the mechanism changed: the risk was never about which operations are *reachable*, but about **on whose authority** they execute once reached, and:

1. **~~The workload identity is provisioned at the narrowest possible envelope~~** — superseded. The exchanged token is now what carries authority, not the workload identity, so there is no envelope to narrow.
2. **~~Both surfaces render a persistent, non-dismissible level-scoping notice while the interim holds~~** — superseded along with item 1. There is no shared-identity read to scope-narrow, so the notice has nothing true left to say; `pui-interim-scoping-notice` and `FATHOM_INTERIM_LEVEL_SCOPED` are removed, not merely disabled — a notice warning of a leak that can no longer occur would itself be the [50 §11.3 item 26] violation (rendering a value for a condition that isn't true).
3. **~~The README records the interim as a local resolution~~** — superseded. There is no interim left to record; the README instead notes that [50 §13] correction 10, [50 §14] UI-OQ-4, and §14 P-OQ-3 are closed by this resolution, per [09 §8.7]'s convention for recording how a flagged gap was actually closed.

**One operation `apps/web` has and this app still does not — and it is no longer about identity.** `GET /api/v1/gateway/session` (`30 §8.1.2`) now returns the same identity block to this app that it returns to `apps/web`, fed by the exchanged token exactly as §4.7 above states. `POST /api/v1/gateway/session/logout` remains inapplicable, for an unrelated reason that the credential fix does not touch: this app was never cookie-sessioned at the gateway — it holds a bearer token it exchanges and refreshes itself — so there is no gateway session for that operation to destroy, regardless of which credential shape feeds it. **Consequences:**

- **`IdentityBlock` is available**, superseding [50 §13] correction 3 and this document's own earlier P-OQ-3. [50 §3.2]'s `IdentityBlock`, fed here from `GET /api/v1/gateway/session`'s response, renders the viewer's name, organization, and authority chips exactly as it does in `apps/web` — no invented data, because the identity block is the gateway's own, not read off the Domino assertion locally.
- **No sign-out control**, for the reason above: logout is Domino's problem, not this app's. A sign-out button that ended only a nonexistent gateway session would be a lie about what it did. `pui-no-signout-control` asserts neither surface renders one.
- **No pre-marking, no dimming, no `POST /authority-checks`.** [31 §8]'s advisory operation lives on `auth`, and [30 §8.1]'s pass-through surface covers *"the nine sub-applications plus `tool-server`, `knowledge-retrieval`, `notification`, `reference-data`"* — **not `auth`**. So neither `POST /authority-checks` nor `GET /principals/{sub}` is reachable from this app at all. §13 correction 6. The practical effect is the correct one: no control is disabled on advice this app cannot obtain, and every refusal is the server's, rendered with its `reasons`.

### 4.8 Rate limiting: one bucket for every viewer

[30 §6.2]'s per-caller bucket table has been amended and now names this app explicitly:

> *"Workload — Domino scoring Jobs, **practitioner Apps** | `("workload", sub)` | 09 §4.4.2's `domino-compute → gateway` edge."*

**The consequence is that all viewers of one App share one token bucket**, because the bucket key is the workload `sub` and there is one workload identity per surface (§2.1). Four rules follow:

| Rule | Reasoning |
|---|---|
| [50 §6.4]'s halved polling frequencies are not a nicety here; they are the mechanism that keeps a shared bucket viable | Two viewers polling a 60 s list consume the budget two viewers polling a 30 s list would consume at four times the rate |
| `Retry-After` is honoured, and the pause is per query, exactly as [50 §5.4] specifies | [30 §6.5] returns `429 urn:fathom:problem:gateway:rate-limit-exceeded` with `Retry-After: <integer seconds>`, *"[c]eiling, never zero."* A poll loop that ignores it converts a rate limit into an outage [50 §11.3 item 22] |
| **`RateLimitNotice` states that the limit is shared.** *"The application's request budget is shared by everyone using it; retrying in N seconds."* | An operator who reads "you are being rate limited" when they made one request will conclude the system is broken. The shared bucket is a fact about the deployment and the notice says so |
| The host does not retry a `429` itself, and does not queue | A retry inside the host multiplies the very load the bucket is bounding, and the SPA is the layer with the query-level pause [50 §5.4] |

---

## 5. Routing, data fetching, and freshness

### 5.1 Router and the two route trees

[50 §4.1]'s React Router selection, mode, and *"[r]oute loaders and actions are not used"* rule bind unchanged. `basename` comes from §3.2. Two trees, one per surface, each its own `createBrowserRouter` call in its own entry.

**Surface A — `failure-intel` (Sheet 08):**

```
/                                       HypothesisList                    WF #s8, "Open hypotheses"
└── /hypotheses/:hypothesisId            HypothesisList + AdjudicationPanel (nested, beside)
    └── /hypotheses/:hypothesisId/census TreatmentCensusDetail             (nested, beside)
*                                        NotFound
```

**Surface B — `design-advisory` (Sheet 09):**

```
/                                       CaseSelector                      entry list — see below
└── /cases/:caseId                       CaseReview                        WF #s9 in full
*                                        NotFound
```

Six rules, each load-bearing:

1. **The adjudication panel is a nested route, not a modal**, exactly as [50 §4.2] rules for `apps/web`'s queue: *"the URL is shareable — which matters for dual control, where a second adjudicator must reach the same proposal."* `WF #s8` draws the panel as a second `Box` below the list, and `WF #s9` is a whole-sheet review; neither is a modal. [50 §3.2]: `AdjudicationPanel` is *"[n]ot a modal — the wireframe shows the panel beside the queue and the evidence must remain readable."*
2. **Every rendered state has a URL**, because [02 §4.1] makes the iframeless view conditional on *"applications supporting deep linking."*
3. **No route is authorization-gated, in either direction.** [50 §4.2]'s rule, and every reason it gives applies with more force here: this app cannot even obtain the viewer's roles (§4.7). There is no `<RequireRole>`, no redirect on a missing role, and no hidden affordance implying a permission. A route the viewer may not use renders the server's RFC 9457 refusal. `pui-no-role-gated-route` extends [50 §10.2]'s `ui-no-role-gated-route`.
4. **`/` on Surface B renders `CaseSelector`, and that is a judgment call with a stated basis.** `WF #s9` draws no entry list — an engineer arrives from `apps/web`'s sheet 10 or from a notification. But a Domino App is reached by *its own URL*, so `/` must render something, and a blank page is worse than a list. `CaseSelector` therefore uses **only existing components** — a `Box` containing a `WfTable` of open `redesign_case` proposals plus a `SheetNote` stating it is an entry list — so [50 §11.2] item 12's prohibition on *"invent[ing] a component the wireframes do not have"* is honoured: no new pattern is introduced, only an arrangement of drawn ones. §13 correction 9 records that sheet 09 draws no entry point for its own App.
5. **Title, focus, and announcement** on every route change, per [50 §4.4]: `document.title` is `FATHOM — <sheet title>`; focus moves to the destination's `<h2>`; one polite live region in `AppFrame` announces `<sheet title> loaded`. The title matters more here than in `apps/web` — inside an iframe the browser tab shows *Domino's* title, so the `<h2>` and the live region are the only announcements a screen-reader user gets.
6. **Redirects: none.** [50 §4.4] permits exactly two for `apps/web`; this app has no label an operator would type and no legacy path to alias.

### 5.2 The `api/` layer

[50 §5.2]'s five-file shape, mirrored exactly, with three surface-specific differences and no others:

| File | Difference from `apps/web` |
|---|---|
| `client.ts` | `createClient<paths>({ baseUrl: API_PREFIX, credentials: "same-origin" })` where `API_PREFIX` is §3.2's derived value. Nothing depends on the cookie arriving (§4.3) |
| `queryClient.ts` | [50 §5.4]'s global defaults **unchanged**, including `refetchOnWindowFocus: true`, `refetchIntervalInBackground: false`, `retry: 2` with backoff, `Retry-After` honoured, and `performance.now()` for every interval and backoff |
| `keys.ts` | §5.4's key set. **The only place a key literal appears** |
| `problem.ts` | [50]'s parser, plus the five host-originated problem types of §4.5 so a host failure is distinguishable from an upstream one |
| `freshness.ts` | §5.4's table as data, each row citing its derivation |

Unchanged and binding: every read goes through `openapi-fetch` over generated types, and *"[a] `queryFn` that calls `fetch` directly is a review rejection"* [50 §5.1]; every canonical shared type is parsed through the Zod validators [50 §5.2, 10 §4.9]; no component in `packages/ui` fetches [50 §2.1 rule 4].

### 5.3 The per-surface proxy allowlist

**[ESTABLISHED HERE]**, on [30 §8.2] DECISION G-3's reasoning applied one hop out. The host proxies an **explicit, per-surface, generated allowlist** and `404`s anything else. There is no catch-all proxy route.

Four properties depend on it, and a catch-all breaks all four:

1. **The reachable surface is exactly what this document enumerates.** A path the app does not need is unreachable through the app, so a compromised or mis-coded SPA cannot use the workload credential to reach an operation nobody reviewed. This is the security property [30 §8.2]'s property 3 names: *"[a]n undeclared operation is unreachable."*
2. **The `Origin` check and the `Idempotency-Key` requirement can be decided statically**, from the matched entry's method and side-effect class, rather than from the upstream's response — which would be after the state change.
3. **The two surfaces have genuinely different envelopes**, which is what makes §2.1's per-surface workload identities meaningful rather than decorative.
4. **CI can prove the allowlist and the query-key factory agree.** `pui-allowlist-matches-keys` asserts every entry is reached by some query or mutation in that surface, and every query or mutation in that surface resolves to an entry — so a dead entry and an unreachable call are both build failures.

`allowlist.py` is **generated** from `apps/practitioner/src/api/keys.ts`'s declared operation set by `tools/gen_practitioner_allowlist.ts`, committed, and CI fails on drift — [09 §2.5]'s regenerate-and-diff convention, the same one [50 §2.1] rule 1 applies to tokens.

**Surface A — `failure-intel`. Ten entries.**

| # | Method and path | Source | Side effects | Used by |
|---|---|---|---|---|
| A1 | `GET /api/v1/failure-intel/hypotheses` | [25 §8.1] | `none` | §6.1 list |
| A2 | `GET /api/v1/failure-intel/hypotheses/{id}` | [25 §8.1] | `none` | §6.1 panel; the ETag source (§6.4) |
| A3 | `GET /api/v1/failure-intel/hypotheses/{id}/evidence` | [25 §8.1] | `none` | §6.1 evidence list |
| A4 | `GET /api/v1/failure-intel/hypotheses/{id}/treatment-census` | [25 §8.1] | `none` | §6.1, §6.2 census detail |
| A5 | `GET /api/v1/failure-intel/failure-modes/{mode_lineage_id}` | [25 §8.1] | `none` | §6.1 mode label + `code_authority` |
| A6 | `POST /api/v1/failure-intel/hypotheses/prior-examination-check` | [25 §8.1], [25 §7.3] | `none` | §6.2 supersession panel |
| A7 | `POST /api/v1/failure-intel/hypotheses/{id}/claim` | [25 §8.1] | `state-changing` | §6.4 step 2 |
| A8 | `POST /api/v1/failure-intel/hypotheses/{id}/adjudicate` | [25 §8.1] | `state-changing` | §6.4 step 5 |
| A9 | `POST /api/v1/failure-intel/causal-feature-set-admissions` | [25 §8.1] | `state-changing` | §6.5 |
| A10 | `GET /api/v1/failure-intel/causal-feature-sets/entries` | [25 §8.1] | `none` | §6.5, to show whether an entry already exists |

**Surface B — `design-advisory`. Seven entries.**

| # | Method and path | Source | Side effects | Used by |
|---|---|---|---|---|
| B1 | `GET /api/v1/gateway/views/redesign-case/{case_id}` | [30 §3.2] | `none` | §7.1 the whole sheet |
| B2 | `GET /api/v1/design-advisory/proposals` | [28 §9.1] | `none` | §5.1 `CaseSelector`; §7.7's case→proposal resolution |
| B3 | `GET /api/v1/gateway/proposals/{proposal_id}` | [30 §4.5] | `none` | §7.7. **The ETag source** [30 §4.6] |
| B4 | `POST /api/v1/gateway/proposals/{proposal_id}/claim` | [30 §4.5] | `state-changing` | §7.7 step 2 |
| B5 | `POST /api/v1/gateway/proposals/{proposal_id}/adjudicate` | [30 §4.5] | `state-changing` | §7.7 step 5 |
| B6 | `GET /api/v1/design-advisory/redesign-candidates/{candidate_id}/gate-decisions` | [28 §9.1] | `none` | §7.5. **Required because `redesign_case_detail` carries no gate fragment** — §13 correction 7 |
| B7 | `GET /api/v1/design-advisory/impact-snapshots/{snapshot_id}` | [28 §9.1], [28 §4.5] | `none` | §7.4's *"reproduce this traversal"* link |

**Not allowlisted, deliberately**, each with the reason so a later author does not read the omission as an oversight:

| Operation | Why not |
|---|---|
| `POST /api/v1/design-advisory/dossiers/assemble`, `.../parametric-estimate`, `.../evaluate-gate` | Compute-only and agent-eligible [28 §6.1 steps 2, 7, 8], and **they belong to the Redesign Case Builder agent's run**, not to a review surface. A reviewer who could re-assemble the dossier under themselves would change the artefact they are reviewing |
| `POST /api/v1/design-advisory/redesign-cases`, `.../assemble`, `.../estimate` | [28 §6.1] steps 9–10 and [42 §13.3]: *"[i]t is where a human commits `POST /redesign-cases/{id}/assemble`."* **That human is on a *drafting* surface, and `WF #s9` draws a *review* surface** — it has no stance selector, no limitations editor, and no estimate control. Adding them would be inventing three sheets. §13 correction 10 records the gap between [42 §13.3]'s claim and what sheet 09 draws |
| `POST /api/v1/failure-intel/discovery-runs` and every discovery-management operation | `x-substitution: internal`, not agent-eligible, and `WF #s8` draws no run-request control. [25 §5.1] step 1 puts run requests with *"[a] reliability engineer, or a scheduled Flow"* — the surface for that is undrawn. §13 correction 11 |
| `GET /api/v1/gateway/session`, `POST /api/v1/gateway/session/logout` | §4.7. No gateway session exists for this app |
| `POST /api/v1/auth/authority-checks`, `GET /api/v1/auth/principals/{sub}` | **Not reachable at all**: [30 §8.1]'s pass-through does not include `auth`. §4.7, §13 correction 6 |
| Anything on `/api/v1/gateway/domino/endpoint-invocations` | §2.7. Neither surface calls an Endpoint |

### 5.4 Query keys and freshness

Keys mirror the operation and its parameters exactly, so invalidation is mechanical [50 §5.3]:

```
["hypotheses","list",   normalizedParams]          // A1
["hypotheses","detail", hypothesisId]              // A2
["hypotheses","evidence", hypothesisId]            // A3
["hypotheses","census", hypothesisId]              // A4
["failure-modes","detail", modeLineageId, taxonomyVersion]   // A5
["feature-set-entries", normalizedParams]          // A10
["views","redesign-case", caseId]                  // B1
["proposals","list", normalizedParams]             // B2
["proposals","detail", proposalId]                 // B3
["gate-decisions", candidateId]                    // B6
["impact-snapshots","detail", snapshotId]          // B7
```

**Intervals.** [50 §6.4] establishes the rule — *"a practitioner surface's client-side polling budget is smaller than the console's; §5.4's intervals are halved in frequency for `apps/practitioner` (i.e. 120 s / 60 s)"* — and [50 §5.4]'s derivations are the basis. No new figure is invented; each row states which [50 §5.4] row it halves.

| Query | `staleTime` | `refetchInterval` | Derivation |
|---|---|---|---|
| `["hypotheses","list", …]` | 30 s | **60 s** | Halved from [50 §5.4]'s `["proposals","list"]` row (15 s / 30 s), which is the nearest analogue: a work queue a human is actively waiting at. It over-samples the real rate of change by orders of magnitude — a hypothesis appears when a discovery run completes, and [25 §5.1] step 1 makes runs a scheduled Flow — and exists for perceived liveness, **not for correctness**. Correctness is [25 §5.2]'s claim-then-`If-Match`, which fails safe with a `412` regardless of how often the list refetched |
| `["hypotheses","detail", id]` | `Infinity` | **none** | [50 §5.4]'s `["proposals","detail"]` reasoning, unchanged and not halved because it is already none: *"[r]efetched on open, on a `412`, and after a successful mutation … refetching under the operator would silently replace the `ETag` they are about to submit."* Identical here, and §6.4 makes it the ETag source |
| `["hypotheses","evidence", id]`, `["hypotheses","census", id]` | `Infinity` | **none** | Both decompose one hypothesis version. [50 §5.4]'s explanation-view reasoning: *"[a] new prediction is a new id; the old decomposition does not change."* A recomputed strength [25 §4.6] is a new strength document on the same hypothesis, so both are invalidated together with the detail after a mutation, not polled |
| `["failure-modes","detail", …]` | `Infinity` | **none** | [50 §5.4]'s reference-data row: keyed by `taxonomy_version`, so *"a cache entry is immutable and invalidation is a version change, not an expiry"* |
| `["views","redesign-case", caseId]` | `Infinity` | **none** | The detail-fetch reasoning above, applied to a composed view the reviewer is reading while they decide. Refetched on open, after a mutation, and on a `412` from B5. Polling a 4 000 ms five-fragment fan-out [30 §3.2] under a reading human would burn the budget and could swap the evidence mid-review |
| `["proposals","list", …]` | 30 s | **60 s** | Halved from [50 §5.4]'s `["proposals","list"]` row. Drives `CaseSelector` only |
| `["proposals","detail", proposalId]` | `Infinity` | **none** | [50 §5.4] verbatim. The `ETag` source for B5 |
| `["gate-decisions", candidateId]` | `Infinity` | **none** | [28 §5.2]: the table is *"[a]ppend-only, superseded never overwritten."* The live decision changes only when the gate is re-evaluated, which is not something this surface can cause |
| `["impact-snapshots","detail", …]` | `Infinity` | **none** | An `impact_snapshot` is immutable by construction [28 §4.5] — it exists to make a traversal reproducible |

**No `Cache-Control`, no `If-None-Match` on gateway-owned reads**, per [50 §5.4]'s closing paragraph: [30] issues no `ETag` on `/views/*` or `GET /proposals`. And **every interval, timeout, and backoff is measured with `performance.now()`** [50 §5.4, **D29**]; `ui-no-wall-clock-timers` [50 §10.2] runs over this app too.

### 5.5 Mutations

[50 §5.6]'s table binds unchanged; five rows apply here and two are added. Both surfaces' mutation flows are detailed in §6.4 and §7.7; the shared rules are here so they are stated once.

| Rule | Basis |
|---|---|
| **`Idempotency-Key` on every state-changing call**, a client-generated UUIDv4 generated **once per user action** and reused across every retry | [09 §5.3], [50 §5.6]. *"[r]egenerating it on retry defeats the mechanism."* `ui-idempotency-key-stable-across-retries` [50 §10.2] |
| **`If-Match` on every adjudication**, carrying the ETag the operator is looking at, forwarded unchanged | [25 §5.2] for A8; [30 §4.6] for B5. Neither the SPA nor the host ever synthesizes one (§4.4 property 3) |
| **`412` refetches, re-renders, and requires the operator to re-confirm. Never auto-resubmit** | [03 §7.2]: *"[w]ithout this the eventually-consistent queue permits two approvals and two work orders."* [25 §5.2] applies the identical rule to hypotheses |
| **`428` is a client defect, not a runtime path** | [50 §5.6]. `pui-adjudicate-sends-if-match` fails the build rather than handling it at runtime |
| **Every adjudication passes through `AdjudicationConfirm`** (Radix `AlertDialog`) [50 §3.2] | It *"requires an explicit action, does not dismiss on outside click, and takes `role="alertdialog"` with a required description"* |
| **[ADDED] The confirm dialog enumerates the evidence it is about to attest was reviewed, and refuses to submit if any item is unavailable** | [25 §5.2] makes `adjudication_record.evidence_reviewed` a record of *"what was actually in front of the adjudicator"*; [30 §4.6] refuses a partial proposal because *"[a]djudicating a proposal whose payload and evidence could not be read is precisely D16's defect wearing a friendlier face."* The refusal **states which item is unavailable and offers a retry** — it is never a greyed control with no explanation [50 §9.4] |
| **[ADDED] The decision note is required, and the form will not submit an empty one** | [25 §5.2]: `note text NOT NULL` — *"[a] decision with no reason is not one."* For a `redesign_case`, `adjudication_note` [03 §7.2] |
| **On success, invalidate; never optimistically update the row** | [50 §5.6]. *"[a]n optimistic queue row is a claim about another service's state that the gateway explicitly does not make"* |

### 5.6 Loading, empty, and unknown

[50 §5.5]'s three components, never conflated, bind unchanged: `LoadingSkeleton`, `EmptyState`, `DegradedFragmentNotice`. Two surface-specific applications, both of which are the load-bearing case:

- **A degraded `causal_findings` fragment is not "no causal findings."** §7.3.
- **An unavailable strength band is not S0.** §6.3. `S0` means *"[c]ontradicted, or the gate refused. Not a finding"* [25 §4.4] — an assertion about the evidence, not about our ability to fetch it.

`--hatch` is never a loading state [50 §2.5, §5.5, §11.1 item 6]: it means *"a figure belongs here and is not rendered."* Sheet 09's dependency graph is a real figure (§7.4), not a `FigurePlaceholder`.

---

## 6. Sheet 08 — Hypothesis Adjudication

`WF #s8`. Title block: `SHEET 08 / FAILURE INTELLIGENCE`, `Hypothesis Adjudication`, persona *"Reliability Engineer (practitioner)"*, `tb-right` *"Doc 04 §9"*. One `SheetNote`, two `Box`es.

The sheet's own note is the framing rule for everything below and is **rendered verbatim**, not paraphrased:

> *"Outputs are **adjudicated hypotheses**, never automated conclusions — a strength scale is shown, not a bare 'confidence' number. (doc 04 §9)"*

### 6.1 Every rendered field, traced to an operation

`WF #s8`'s "Open hypotheses" table draws four columns. Each maps to real fields, and each carries at least one rule the wireframe does not show.

| WF column | Fields | Operation | Rules |
|---|---|---|---|
| **Failure mode** | `subject_mode.code`, `subject_mode.lineage_id`, `subject_mode.taxonomy_version`, `subject_mode.code_authority` | A1 [25 §2.9]; label from A5 | **The code is human reference; `lineage_id` resolves** [25 DO-NOT-9, 12 §2.3]. `code_authority = 'fathom-extension'` renders a **placeholder marker** and the row carries no ISO 14224 claim [25 DO-NOT-14, 25 §6.5]. `taxonomy_version` is always visible — [25 §2.3] carries `subject_taxonomy_version` as `NOT NULL` for invariant I2 |
| **Method** | `primary_method_id`, `primary_method_version`; `strength.method_agreement.methods_run[].placeholder_pending_sme` | A1, A2 [25 §2.3, §4.2] | **A method flagged `placeholder_pending_sme` renders that flag inline**, because [25 §3] says a placeholder *"surfaces in every published finding's provenance"* and *"[n]othing in the strength scale treats a placeholder method's output as if the choice were settled."* `WF`'s *"survival + covariates"* is `M2.survival`; the identifier and version are shown, not a prose gloss |
| **Evidence strength** | `strength_band`, `band_limiting_axis`, `strength_rule_version`, `axis_levels{}` | A1, A2 [25 §4.2] | §6.3. **Five bands, never three segments; never a percentage; never a confidence** [25 §4.1] |
| **State** | `adjudication_state` | A1 [25 §2.1] | Eight values, each rendered distinctly: `draft`, `under_analysis`, `awaiting_adjudication`, `published`, `unsupported`, `refuted`, `withdrawn`, `superseded`. `WF` draws *"pending adjudication"* — the enum value is `awaiting_adjudication` and **the enum value governs**; the display label may differ but the underlying field name and value are [25 §2.1]'s |

Six columns the wireframe does **not** draw and this document **adds**, each because omitting it would hide a fact a binding document makes non-optional:

| Added column / element | Fields | Why it cannot be omitted |
|---|---|---|
| **Gate verdict** | `gate_verdict` ∈ `proceed \| proceed_corrected \| restricted \| refused` | [25 §2.3]'s `refused_is_never_published` and axis A4 level 0. `WF` shows the confounding state only inside the panel, as one chip; a list in which a `restricted` finding is indistinguishable from a `proceed` one at a glance invites the reader to compare incomparable rows |
| **Treatment handling** | `treatment_handling` (six values, **no default** [25 §2.1]) | [25 DO-NOT-1] is the sub-application's first prohibition, and the whole of [**D21**]. `WF`'s *"confounding check: propensity modeled"* chip is this field |
| **Admissibility** | `admissible_as_causal_feature`, `admissible_as_primary_redesign_driver` | [25 §2.9]: *"served explicitly, so that PdM and Design Advisory do not each re-derive the policy from the band and drift apart."* **The UI does not re-derive them from the band either** |
| **Supersession** | `supersedes_hypothesis_id`, `novelty_basis` | [25 §7.2]: on a fingerprint collision the prior finding *"its census, and its adjudication note are attached to the new draft and **shown to the adjudicator**."* §6.2 |
| **Dual-control state** | `adjudication.dual_control`, and — where present — the second adjudicator | [25 §5.2]'s table requires dual control to publish at S3/S4. §6.4 |
| **Claim state** | **NO FIELD EXISTS.** See §13 correction 12 | [25 §5.2] requires a claim lease, but [25 §2.9]'s wire model carries no `claimed_by`/`claimed_until` and [25 §8.1] declares no filter for them. **A second adjudicator cannot see that a hypothesis is already claimed** — the exact condition [03 §7.2] rule 3 exists to prevent, made invisible. **The interim is honest, not synthetic**: the list renders a `neutral` *"claim state unknown"* marker rather than *"unclaimed"*, and the first `409`/`412` at claim time is the only signal available. Inventing an unclaimed default would be [50 §11.3 item 26]'s violation — rendering a value for an unknown |

**Filtering.** [25 §8.1]'s parameters are `niin`, `installed_item_id`, `mode_lineage_id`, `status`, `min_strength`, `changed_since`, `limit`, `cursor`. `QueueFilter` (Radix `Select`, [50 §3.2]) is rendered for `status`, `min_strength`, and `mode_lineage_id`; the identifier filters are rendered as an `IdentifierLookup` [50 §3.3 gap 3]. **Filter state lives in the URL** [50 §4.4], and parameter names are the operation's own, verbatim, with no client-side renaming. `min_strength` takes a **band** (`S2`), never a number [25 §8.1].

**Sort and pagination.** [25 §8.1] declares no `sort` parameter, so the list is rendered in the order served and **is not labelled with any ordering claim**. This is [30 §12.4 DO-NOT 31]'s rule generalized: a list whose order the contract does not define must not be captioned *"newest first"* or *"oldest first."* Cursor pagination, no total count [03 §4]. `pui-no-unsourced-sort-label` asserts it.

### 6.2 Components

All from `packages/ui` unless marked. Nothing outside this list exists in this surface.

| Region | Components |
|---|---|
| **Frame** | `AppFrame` (app-local composition), `ClassificationBanner`*, `ClassificationFooter`*, `SkipLink`, `SheetFrame`, `TitleBlock`, `SheetNote` |
| **List** (`WF` "Open hypotheses") | `Box`, `BoxLabel`, `WfTableScroll`, `WfTable`, `StatusChip`, **`EvidenceStrengthMeter`** (§6.3), `PlaceholderCodeMarker`* (new — §8.3), `QueueFilter`, `IdentifierLookup`, `EmptyState`, `LoadingSkeleton`, `DegradedFragmentNotice`, `ProblemDetail`, `RateLimitNotice` |
| **Adjudication panel** (`WF` "Adjudication panel — ELP hypothesis") | `Box`, `AdjudicationPanel`, **`StrengthStatement`** (new — §6.3), `StatusChip`, `ChipRow`, `ButtonRow`, `Button`, `AdjudicationConfirm`, `DualControlBadge`, **`ResidualConfounderList`** (new), **`SupersessionNotice`** (new), `ApproximateTime` |
| **Evidence** | `WfTable`, `StatusChip` (`source_trust`), **`DefinitionTimeFlag`** (new), `EmptyState` |
| **Census detail** (nested route) | `Box`, `WfTable`, `WfTableScroll`, **`GateVerdictBadge`** (new), `ResidualConfounderList`, `BackLink` |
| **Admission** (§6.5) | `Box`, `Button`, `AdjudicationConfirm`, native `<label>` + `<input type="date">` for `review_due`, `ProblemDetail` |

`*` = required by a binding document rather than drawn: `ClassificationBanner`/`ClassificationFooter` by [03 §7.3], `PlaceholderCodeMarker` by [25 DO-NOT-14].

**The six new components, and why each is a component rather than a convention** — the same argument [50 §7.1] makes for the disclosure trio: *"[a] convention would be dropped. A component with a test cannot be."*

| Component | Rule it carries | Enforcing test |
|---|---|---|
| `EvidenceStrengthMeter` | Five bands; band + plain-English name + limiting axis together; never a percentage | `pui-strength-five-bands`, `pui-strength-not-a-percentage` |
| `StrengthStatement` | The generated `statement` rendered **verbatim**, never re-worded, never truncated | `pui-statement-verbatim` |
| `ResidualConfounderList` | `residual_confounders[]` rendered in full with `direction_of_bias`, `could_reverse_sign`, and `why_unaddressed`; **never collapsed, never elided** | `pui-residuals-not-collapsible` |
| `DefinitionTimeFlag` | `definition_time_integrity ∈ {fail, unknown}` and cap `C-DT` rendered together with the band | `pui-definition-time-flagged` |
| `GateVerdictBadge` | The four `gate_verdict` values rendered distinctly; `refused` never as a neutral or absent state | `pui-gate-verdict-distinct` |
| `SupersessionNotice` | `supersedes_hypothesis_id` + `novelty_basis` + the prior finding's state, band, and adjudication note | `pui-supersession-shown` |

**The supersession panel, concretely.** When `supersedes_hypothesis_id` is set, `SupersessionNotice` fetches the prior hypothesis (A2 on that id) and renders its `adjudication_state`, `strength_band`, and the adjudication note, alongside `novelty_basis`. [25 §7.2] enumerates the six permitted grounds — more observations, a new method, a different arm or population, a new `taxonomy_version`, a corrected gate posture, a new falsification result — and the notice renders which one was claimed. Where the operator wants the full prior-examination register, A6 (`POST /hypotheses/prior-examination-check`, compute-only, `x-side-effects: none`) returns *"the fingerprint and every prior examination with its state, band, adjudication note, and census"* [25 §7.3]. It is a read: no state changes, and it is the operation [25 §7.3] calls *"the difference between a retained negative finding and a findable one."*

### 6.3 `EvidenceStrengthMeter` and `StrengthStatement`

[50 §3.2]'s inventory table closes with: *"Evidence-strength bar (sheet 08) | — | — | **Out of scope.** Sheet 08 is a Domino App [04 §9]; the component belongs to [52]."* This is that specification.

**What the wireframe draws, and why it cannot ship as drawn.** `WF #s8` lines 992–996 draw three 14 × 8 px segments, two filled with `--accent` and one with `--line-soft`. [25 §4] defines **five** bands, `S0`–`S4`. A three-segment bar cannot express five states, and two-of-three reads as a fraction — which is precisely what [25 §4.1] forbids: *"[i]t is not a confidence, a probability, or a score. Nothing sums, nothing averages, and nothing trades off."* §13 correction 13.

**The specification.** `[ESTABLISHED HERE]`

| Aspect | Rule |
|---|---|
| Segments | **Five**, one per band, `S0`–`S4`. Filled up to and including the current band, using `--ink-soft` for filled and `--line-soft` for unfilled — **not `--accent`**, because [50 §2.2]'s first rule makes the accent mean *"primary interactive control"* and a strength band is neither interactive nor a status |
| Accessible name | The band identifier **and** its plain-English meaning from [25 §4.4], verbatim: `"S2 — corroborated hypothesis"`. Never a ratio, never *"2 of 3"*, never a percentage |
| Adjacent, mandatory text | The band, its [25 §4.4] name, and **`band_limiting_axis`** — *"the actionable field"* [25 §2.3], and the answer to [25 §4]'s own framing question *"why is this only S2?"*. The meter is never rendered without it; `pui-strength-has-limiting-axis` asserts it |
| Caps | `caps_applied[]` rendered when non-empty. `C-DT` (definition-time integrity, cap at S1) and `C-TAX` (`fathom-extension` subject, cap at S2) [25 §4.3] each render their reason, because a band capped at S1 for hindsight contamination is a different fact from a band computed at S1 |
| Unknown | An unavailable band renders `DegradedFragmentNotice`-equivalent text, **never `S0`**. `S0` is an assertion about the evidence [25 §4.4]; unavailability is an assertion about the fetch. `pui-strength-unknown-is-not-s0` |
| Never | No aggregation across hypotheses, no ranking, no local score, no threshold boolean. [25 DO-NOT-8] and [28 §8.2] property 4 — *"[t]hree weak hypotheses pointing the same way do not become one moderate hypothesis"* — bind the *renderer* as much as the service |
| Colour is never the only encoding | Position (which segments are filled) plus the adjacent text. SC 1.4.1 [50 §8.3] |

**`StrengthStatement`.** [25 §4.5] generates a published finding's operator- and engineer-facing text *"from a band-keyed template, from the structured fields, and … never authored free-hand."* The component therefore:

1. **Renders `statement` verbatim** — not paraphrased, not shortened, not truncated with an ellipsis, not tooltipped. It is the same rule [50 §7.3] applies to the advisory statement and [50 §11.4 item 35] generalizes: *"[t]hey are the marking, not a description of it."*
2. **Emits no causal verb of its own.** [25 §4.5]'s forbidden vocabulary — *causes, caused by, root cause, because, due to, drives, results in* — is unlocked at S4 only, and even then only inside the generated statement. [28 DA-3]'s permitted vocabulary is *"hypothesis, adjudicated `<state>` by Failure Intelligence."* [50 §7.5] and [09 §9.3 item 20] / [**D23**] bind. `pui-no-causal-verb` runs [25 §4.5]'s denylist over every label string, prop name, and component name in both surfaces.
3. **Never renders the statement without `residual_confounders[]`** where the list is non-empty. [25 §4.5]: *"`{confounding_clause}` and `{residual_clause}` are … **not omittable**: a template render with a non-empty residual list and an empty clause fails."* If the statement arrives without them — a service defect — the component renders the residual list itself, adjacent, rather than hiding the discrepancy.
4. **Renders `strength_rule_version`.** [25 §4.6] makes a band recomputable and falls permitted; a statement whose derivation rule set is unnamed cannot be compared to one from a later version.

### 6.4 The adjudication flow, in full

Six steps. Steps 1–5 are `WF #s8`'s two buttons made implementable; step 6 is §6.5's separate act.

| # | Step | Call | Rules |
|---|---|---|---|
| 1 | **Open** | A2, A3, A4; A5 for the mode label; A2-on-prior where superseding | `["hypotheses","detail"]` is `staleTime: Infinity` (§5.4) so nothing refetches under the operator. **The `ETag` from this response is captured once** and is what step 5 sends |
| 2 | **Claim** | A7 `POST /hypotheses/{id}/claim`, `Idempotency-Key` required, `If-Match` per [25 §8.1] | [25 §5.2]: *"`POST /hypotheses/{id}/claim` obtains a lease; adjudication requires `If-Match` on the claimed ETag and returns 412 otherwise."* A `409` means someone else holds it: render the refusal, do not retry, do not offer a force |
| 3 | **Review** | — | The panel must render, before any button is reachable: the `StrengthStatement`, `EvidenceStrengthMeter` with its limiting axis and caps, `GateVerdictBadge`, `treatment_handling`, `ResidualConfounderList`, the evidence table with `source_trust` per row, `negative_control.status`, and `SupersessionNotice` where present. **`negative_control.status ∈ {fail, unavailable}` is rendered prominently** — it caps A4 at level 1 [25 §4.3] and is the falsification result [25 §3.8] |
| 4 | **Confirm** | `AdjudicationConfirm` (`AlertDialog`) | The dialog states: the decision, the band before and after, whether this is signature 1 of 2, and **an enumeration of the evidence being attested as reviewed** (§5.5's added rule) — which becomes `adjudication_record.evidence_reviewed`, *"what was actually in front of the adjudicator"* [25 §5.2]. **The note is required and the dialog will not submit an empty one.** If any evidence item's fetch is not `ok`, the dialog **refuses with a stated reason and a retry** |
| 5 | **Adjudicate** | A8 `POST /hypotheses/{id}/adjudicate`, `Idempotency-Key` + `If-Match` on the step-1 ETag | On `200`: invalidate `["hypotheses","list"]`, `["hypotheses","detail", id]`, `["hypotheses","evidence", id]`, `["hypotheses","census", id]`. On `412`: refetch, re-render, **require re-confirmation**, never auto-resubmit. On `409`: [25 §5.2]'s mandatory re-validation failed — render the reason (a superseded census, a superseded `baseline_epoch`, a superseded `taxonomy_version` after a `split` or `narrowed` relation, or a stale `strength_rule_version`) and offer refresh, **never a retry of the same body**. On `403`: [31 §3.5]'s `not-authorized` with its `reasons`, rendered as `ProblemDetail` (§6.7) |
| 6 | **Admit** — separate | A9, §6.5 | **Not part of step 5, and not offered from the same button** |

**The decision vocabulary, and its one gap.** [25 §5.2]'s `adjudication_record.decision` is `approve \| reject \| downgrade \| defer \| retire`. Each renders as its own control with its own confirm text:

| Decision | Control | Rules |
|---|---|---|
| `approve` | `WF`'s primary button, **relabelled** — §6.5 | Publishes at the computed band. `published_band ≤ strength_band` [25 §2.3]'s `override_lowers_only` |
| `reject` | `WF`'s second button, *"Reject — retain as negative finding"* — the label is correct and is kept | [25 §7.1]: the row is **retained in full**, with its evidence, census, strength document, method versions, and adjudication record. The confirm dialog says so, because "reject" reads as "discard" to anyone who has not read [25 §7] |
| `downgrade` | Secondary button + a band selector limited to bands **below** `strength_band` | [25 §2.3]'s `downgrade_lowers` CHECK and [25 DO-NOT-8]: *"[a]n adjudicator may lower. Nothing raises."* The selector **cannot offer a higher band** — the control makes the prohibited thing unreachable rather than relying on the server's refusal |
| `defer` | Secondary button | Note required |
| `retire` | Secondary button, shown only for a `published` hypothesis | [25 §5.5]: retirement cascades to `causal_feature_entry` retirement in the next feature-set version, **a major bump**. The confirm dialog states that consequence |
| `withdraw` | **NO DECISION VALUE EXISTS.** §13 correction 14 | [25 §7.1] makes `withdrawn` a state reached by *"[a]djudicator judgment, with the reason required"* — but no `decision` value produces it. **The UI does not invent one**: no withdraw control is rendered, and the README records the gap |

**Dual control.** [25 §5.2]'s interim table requires it to publish at S3/S4, and for every vocabulary change. So:

| Rule | Basis |
|---|---|
| When `strength_band ∈ {S3, S4}` and the decision is `approve`, `DualControlBadge` renders and the confirm dialog states **which signature this is** | [25 §5.2]; [50 §5.6]: *"[f]or `requires_dual_control` proposals the dialog states which signature this is"* |
| The second signature must be a **different identity** | [25 DO-NOT-11]: *"dual control means two distinct identities."* Enforced by the service; the dialog states it so a single operator does not expect to click twice |
| The second adjudicator reaches the same hypothesis by **URL** | §5.1 rule 1. `/hypotheses/:hypothesisId` is shareable, which is the whole reason the panel is a nested route |
| **There is no way to find hypotheses awaiting a second signature.** §13 correction 15 | [25 §8.1] declares no `awaiting_second_signature` filter — [30 §4.5] has one for proposals and [25] has no equivalent. The interim: the second adjudicator arrives by link. **No client-side derivation is attempted**, because the list response carries no second-signature field to derive from |

### 6.5 Approve is not admit, and the wireframe's button label is a defect

`WF #s8` line 1007: `<button class="btn primary">Approve → admit as causal feature</button>`.

**That button collapses two acts [25 §5.1] separates deliberately**, and its own words say why:

> *"**Step 7 and step 8 are deliberately separate.** Publishing a finding is an epistemic act; admitting a feature into operational scoring is an operational one, with a different blast radius. Collapsing them would mean every published finding automatically reaches tier-3 models, which is precisely the silent propagation 04 §9 forbids."*

`[ESTABLISHED HERE]` The sheet renders **two controls, in two regions, with two confirmations**:

| | Publish (step 7) | Admit (step 8) |
|---|---|---|
| Control | `Approve — publish at S<n>` | `Admit as causal feature` |
| Operation | A8 `POST /hypotheses/{id}/adjudicate` | A9 `POST /causal-feature-set-admissions` |
| Precondition rendered by the UI | A claim (step 2) | `adjudication_state = 'published'` **and** `admissible_as_causal_feature = true` [25 §2.9] |
| Gate | [25 §5.2]'s authority table | [25 §5.3]'s three layers: `admission_floor` ≥ S2, `s2_is_monitored_only`, definition-time integrity |
| Standing | — | **S2 → `monitored` only; S3+ → `standing`** [25 §5.4], and the control does not offer `standing` for an S2 hypothesis |
| Required input | `note` | **`review_due`, with no default.** [25 §5.4]: the interval is **OD-6**, unresolved, *"[s]et per admission by the adjudicator until a standing interval exists"*, and the field is `NOT NULL` *"so it cannot be silently omitted."* The form requires it and offers no suggested value — inventing one would be [09 §9.5 item 31] |
| Separation of duties | — | [25 §5.3]: the API *"rejects with 422 … where the adjudicating identity equals the proposing identity for a `standing` admission."* **The UI cannot know the identities (§4.7), so it does not pre-judge**: it renders the `422` with its reason |
| Ablation | — | For `monitored`, the panel states that ablation is **mandatory** and that *"[a] feature that does not improve the ablation comparison is retired at its review date"* [25 §5.4] |

`pui-approve-is-not-admit` asserts that no single control issues both A8 and A9, and that the string `admit as causal feature` never appears in the same control as an adjudication decision.

**One gap blocks the admission form and is not filled here.** [25 §8.1] declares `POST /causal-feature-set-admissions` but **specifies no request body**, while [25 §2.6]'s `causal_feature_entry` requires `feature_key`, `definition_ref`, `definition_version`, `definition_time`, `equipment_family`, `standing`, and `review_due`. The form cannot be built without the shape. §13 correction 16 — the same class of gap [42 §18] items 1 and 3 found in [28], and the same remedy: specify the body. **Interim:** the admission control renders a stated-reason refusal (*"the admission request shape is not yet specified — see 25 OD-6 and 52 §13 correction 16"*) rather than posting a guessed body, and A9 remains allowlisted so the form lands as a one-file change.

### 6.6 Error, loading, and empty states

| Condition | Rendering |
|---|---|
| List loading | `LoadingSkeleton` at the table's final dimensions [50 §5.5]. **Never `--hatch`** |
| List empty (`items: []`) | `EmptyState` naming the filter scope: *"No hypotheses match status = awaiting_adjudication."* Distinct from a failed fetch |
| List fetch failed | `ProblemDetail` with retry. `503` from the host means the workload credential is unavailable (§4.2) and says so |
| `429` | `RateLimitNotice`, pausing that query for `Retry-After` seconds, **stating that the budget is shared** (§4.8) |
| Detail `404` | The hypothesis was purged or the id is wrong. `ProblemDetail`; the list stays reachable |
| Evidence empty | **`EmptyState`, and it is a meaningful state**: [25 §2.4]'s `evidence_record` is per-hypothesis and a draft may legitimately have none. It is never rendered as *"no evidence found"* in a way that implies the hypothesis is unsupported — `unsupported` is an `adjudication_state`, not an evidence count |
| Census unavailable | `DegradedFragmentNotice`. **Never rendered as "no confounding"** — [25 §2.3]'s invariant I3 makes `treatment_census_id` `NOT NULL`, so an absent census is a fetch failure or a service defect, never a fact about the population. This is [50 §11.3 item 26] at its sharpest: rendering "no confounding" for an unfetchable census is the defaults-to-benign failure [25 §2.1] says *"is how a confounded population passes a gate silently"* |
| `X-Classification` missing | `ClassificationBanner` renders a **fault state**, never `U` [50 §7.2 rule 5] |
| `502 classification-fault` | A distinct, **non-retryable** `ProblemDetail` [50 §5.3 rule 4, 30 §7.2] |

### 6.7 The persona problem: the Reliability Engineer cannot adjudicate

This is the most consequential finding in this document about Sheet 08, and it is a contradiction between the approved wireframe and [25], not a decision this document can make.

**What the wireframe says.** `WF #s8`'s title block names the persona *"Reliability Engineer (practitioner)"*. `WF` sheet H's `RE` card reads *"Adjudicates causal failure-mode hypotheses"* with a primary button *"Open Hypothesis Adjudication"*. Sheet H's footnote calls the roster *"exactly document 03 §7.2.1's six adjudicating authority classes … plus two review-only roles (Ship's Force Maintainer-as-reviewer, **Reliability Engineer**) document 04 names without granting them adjudication authority."*

**What the corpus says.** [50 §9.1] establishes, and this document confirms against [31 §2.4]'s current text, that **`RE` maps to no realm role**: the six `AuthorityClass` values are `maintainer`, `planner`, `supply_officer`, `design_authority`, `fleet_authority`, `security_officer`, and *"[a] role that is not one of the [six] never appears in a token"* [31 §3.1 rule 3]. [31 §13 item 12] forbids adding a seventh, and [31 §2.4]'s docstring is explicit that *"[a] seventh member is a change to document 03, not to this file."*

**And [25 §5.2]'s interim authority for the act this sheet performs is `design_authority`:**

> *"Publish a hypothesis at S1/S2 | class | `design_authority` | No"* · *"Publish at S3/S4 | class | `design_authority` | **Yes**"* · *"Arbitrate an `Attribution` | item | `design_authority`. **Explicitly not `maintainer`** — arbitrating a PMA/Scheduling disagreement is a reliability-engineering judgment, not a deckplate confirmation."*

[25 §5.2] then records the gap itself: *"[03 §7.2.1] has no row for a causal finding, a feature admission, or a taxonomy extension. That is a genuine gap, and this document does not invent a class to fill it,"* with **OD-5** naming *"[a] `reliability_engineer` role within `design_authority`"* as *"the likely refinement."*

**So, as the corpus stands: the persona the sheet names cannot perform the sheet's primary action.** Sheet H's own footnote is internally consistent with that — it calls `RE` *"review-only"* — while its card copy (*"Adjudicates causal failure-mode hypotheses"*) is not. §13 correction 17.

**[ESTABLISHED HERE]** — what this surface does about it, and it invents nothing:

1. **No route, control, or affordance is gated on a role.** §5.1 rule 3. The adjudication controls render for everyone who reaches the sheet.
2. **Every refusal is the server's, rendered with its `reasons`.** [31 §3.5]'s `urn:fathom:problem:auth:not-authorized`. A Reliability Engineer without `design_authority` gets a legible refusal naming the required class — which is [50 §9.4]'s rule and is strictly better than a disabled button.
3. **The sheet renders no claim about who may adjudicate.** No *"you may adjudicate this"* badge, no *"your authority"* marking. This app cannot obtain the viewer's roles (§4.7) and must not guess.
4. **The README states the open decision by name** — [25 OD-5], [50 §13] correction 17, §13 correction 17 — so an implementer who finds every adjudication refused knows this is the known state and not a bug in the surface.

The same reasoning applies, with the same shape, to `POST /attributions/{id}/arbitrate` [25 §8.1] — which is **not allowlisted** (§5.3), because `WF #s8` draws no arbitration surface and drawing one would be inventing a sheet.


---

## 7. Sheet 09 — Redesign Case Builder

`WF #s9`. Title block: `SHEET 09 / SYSTEM TEST & DESIGN ADVISORY`, `Redesign Case Builder`, persona *"PEO / Design Engineer"*, `tb-right` *"Doc 04 §10"*. One `SheetNote`, a two-column `row`, one full-width `Box`.

The sheet's note is the framing rule and is **rendered verbatim**:

> *"This sub-application assembles a **decision package**, never a decision. Causal findings are cited at their original evidence strength — never upgraded."*

Both halves are correctness rules with enforcement behind them: the first is [28 §1.1]'s framing and [28 §1.2]'s four structural enforcements E1–E4; the second is **R-PASSTHROUGH** [28 §8.1], which [28] calls *"the highest-stakes rule in the document."* §7.3 is how the UI honours it.

### 7.1 The composed view and its five fragments

Sheet 09 is built on **one** call: B1, `GET /api/v1/gateway/views/redesign-case/{case_id}` [30 §3.2]. This is the view [42 §18] item 13 asked for and [30 §3.2] added, and [28 §2]'s claim that the citation drill-down *"is **composed by the gateway**"* now has an implementation.

**The envelope has exactly six top-level members** [30 §3.4]: `view`, `subject`, `as_of`, `fragments`, `degraded`, `data`. [50 §5.3]'s six mandatory client rules bind unchanged, including rule 5 — `as_of` is labelled *"composed at"*, not *"data as of"*, because [30] does not define its semantics ([50 §13] correction 5, still open).

| Fragment | Upstream | Required | Phase | Renders | Rules |
|---|---|---|---|---|---|
| `redesign_case` | design-advisory | **Yes** | 0 | `case_status`, `case_version`, `scope_description`, `dependency_completeness`, `test_coverage_summary`, `test_attribution_ambiguity`, `recommendation_stance`, `recommendation_basis_refs`, `recommendation_limitations`, `recommendation_evidence_gaps` [28 §3.6] | §7.6. `case_status` has **no `approved` value** [28 §1.2 E1]; `published` means *"released to a design authority as a decision package"* and the UI says exactly that |
| `dossier` | design-advisory | **Yes** | 0 | Field failures, causal citations, test-coverage rows, `affected_population`, `read_model_watermarks`, `taxonomy_version`, `inputs_digest` [28 §3.3] | §7.3. `read_model_watermarks` is rendered, because [28 §3.3] says a dossier assembled while a read model was hours stale *"is a different artefact"* and *"a design authority reviewing a case six weeks later has no other way to know"* |
| `impact_snapshot` | design-advisory | No | 0 | `impacted_parts[]`, `impacted_artifacts[]`, `truncated_at_depth[]`, `dependency_completeness`, `policy_version`, `edges_digest` [28 §4.2] | §7.4 |
| `cost_estimate` | design-advisory | No | 0 | `method`, `point_estimate_usd`, `low_usd`/`high_usd`/`interval_basis`, `confidence`, `assumptions[]`, `cost_lines`, `coverage_ratio`, `is_lower_bound`, `cost_model_version`, `model_ref` [28 §3.7] | §7.5 |
| `causal_findings` | failure-intel | No | **1** | The drill-down into the cited hypotheses [30 §3.2] | §7.3. Phase 1, so it is on the slow path and **optional by construction** [30 §3.2] |

**Two required, three optional, and the consequences are not symmetric:**

- **`redesign_case` or `dossier` unobtainable → `503 urn:fathom:problem:gateway:required-fragment-unavailable`, with no partial body** [30 §3.4]. The whole sheet renders `ProblemDetail` with retry [50 §5.3 rule 3]. There is nothing partial to show, and that is correct: a case without its dossier is not a decision package.
- **An optional fragment not `ok` → `degraded: true` and `DegradedFragmentNotice` naming the fragment and its outcome** [50 §5.3 rule 2]. §7.8 states what each degraded fragment must **not** render.
- **`502 urn:fathom:problem:gateway:classification-fault` is never a degraded view** [50 §5.3 rule 4, 30 §7.2]. Distinct, non-retryable `ProblemDetail`.

**The gate decision is not in the view.** [30 §3.2]'s fragment list has no `gate_decision`, yet `WF #s9`'s cost box draws the gate (*"gate: priority ≥ threshold"*) and [28 §5.5]'s `409` carries `failed_conditions` and `remedy` — the actionable part. B6 (`GET /redesign-candidates/{candidate_id}/gate-decisions`) is therefore a **second call**, keyed on `candidate_id` from the `redesign_case` fragment. §13 correction 7 asks [30 §3.2] for a `gate_decision` fragment; until then the second call is a `phase: 1`-equivalent the client sequences itself, and its failure degrades the cost box rather than the sheet.

**Resolving `case_id` to `proposal_id`.** The adjudication action (§7.7) operates on a `Proposal`, not on the case. Nothing maps one to the other: [28 §9.1]'s `GET /proposals` has no `case_id` filter, and [30 §4.5]'s queue row carries *"no domain content"* — so `payload.case_id` is not in the projection. The route therefore accepts the proposal id when the caller has it, and resolves it otherwise:

```
/cases/:caseId?proposal=<proposal_id>      preferred — the id travels on the link
/cases/:caseId                             resolves via B2, matching payload.case_id
```

Three rules on the fallback: it filters `GET /api/v1/design-advisory/proposals?status=proposed`, matches on `payload.case_id` [28 §6.4]'s `RedesignCaseProposalPayload`; **zero matches renders a stated "no open proposal for this case" state and the review remains fully readable** (a case with no live proposal is a legitimate state — `draft`, `assembled`, `superseded`, `withdrawn`); **more than one match renders a stated ambiguity and no adjudication control**, because guessing which proposal an approval applies to is exactly the class of error [**D16**] exists to prevent. §13 correction 18 asks for `GET /proposals?case_id=` or for `GET /redesign-cases/{id}` to carry the live `proposal_id`.

### 7.2 Components

| Region | Components |
|---|---|
| **Frame** | `AppFrame`, `ClassificationBanner`*, `ClassificationFooter`*, `SkipLink`, `SheetFrame`, `TitleBlock`, `SheetNote` |
| **Entry** (`/`, §5.1 rule 4) | `Box`, `WfTable`, `WfTableScroll`, `StatusChip`, `SheetNote`, `EmptyState` |
| **Dossier** (`WF` "Dossier — NIIN …") | `Box`, `WfTable`, **`CitationCard`** (new), **`StrengthStatement`**, **`EvidenceStrengthMeter`**, **`ResidualConfounderList`**, **`TestCoverageTable`** (new), `StatusChip`, **`AbsenceStatusChip`** (new), **`WatermarkNotice`** (new) |
| **Dependency impact** (`WF` "Dependency impact") | `Box`, **`DependencyGraph`** (new), `EquivalentTable`, **`DependencyCompleteness`** (new), **`LowerBoundNotice`** (new), `WfTable`, `WfTableScroll` |
| **Cost** (`WF` "Cost estimate — two-stage") | `Box`, `ChipRow`, `StatusChip`, **`TwoStageCostBar`** (new), **`GateConditionTable`** (new), **`PlaceholderFactorNotice`** (new), `LowerBoundNotice`, `WfTable` |
| **Recommendation** (**not drawn** — §7.6) | `Box`, **`RecommendationStance`** (new), `WfTable`, `SheetNote` |
| **Adjudication** (**not drawn** — §7.7) | `Box`, `AdjudicationPanel`, `ButtonRow`, `Button`, `AdjudicationConfirm`, `DualControlBadge`, `NonProgramEvidenceFlag`, `ApproximateTime`, `QueueFreshnessNotice` |
| **Cross-cutting** | `EmptyState`, `LoadingSkeleton`, `DegradedFragmentNotice`, `ProblemDetail`, `RateLimitNotice` |

The eleven new components, and the rule each one carries — again, [50 §7.1]'s argument: a convention would be dropped.

| Component | Rule | Test |
|---|---|---|
| `CitationCard` | Renders `strength_carry` **structured object** and `rendered_strength` **side by side**, with `posture`, `adjudication_state`, `confounders_unaddressed`, `treatment_handling`, `attribution_agreement`, and `strength_carry_digest` | `pui-citation-carries-structured-strength` |
| `TestCoverageTable` | One row per **expected** test kind, present or absent [28 §3.2.2]; `qualification_credit` never true for an absence | `pui-test-coverage-one-row-per-expected` |
| `AbsenceStatusChip` | Four absence statuses rendered **distinctly**, never collapsed to "missing" | `pui-absence-statuses-distinct` |
| `WatermarkNotice` | `read_model_watermarks` rendered | `pui-watermarks-rendered` |
| `DependencyGraph` | §7.4's accessibility treatment; unverified edges encoded by dash, not colour alone | `a11y-depgraph-*` (§9.2) |
| `DependencyCompleteness` | Ratio **plus** `is_bounded_below`, `nodes_truncated_at_depth`, `unverified_by_relation`, `unverified_by_source_kind` | `pui-completeness-not-aggregate-only` |
| `LowerBoundNotice` | `is_lower_bound` / `is_bounded_below` rendered as *"this number can only go up"* | `pui-lower-bound-stated` |
| `TwoStageCostBar` | Stage 1 → gate → stage 2, with each stage's real state | `pui-two-stage-states-real` |
| `GateConditionTable` | `condition_results` per condition **by identifier** (`G1`…`G6`), with `thresholds_in_force` and `remedy` | `pui-gate-conditions-by-id` |
| `PlaceholderFactorNotice` | `cost_model_version` / `gate_policy_version` carrying `PLACEHOLDER` rendered as such | `pui-placeholder-factors-marked` |
| `RecommendationStance` | Stance from the closed non-directive vocabulary; `limitations[]` and `evidence_gaps[]` **never collapsed** | `pui-limitations-not-collapsible` |

### 7.3 The dossier, the citations, and R-PASSTHROUGH in the UI

`WF #s9`'s dossier box draws three lines. All three carry a defect, and all three are load-bearing.

**Line 1 — *"Field failures: 6 over 24mo."*** From `dossier_field_failure` [28 §3.3.2]. Rendered with `failure_indicator` distinguished, because [28 §3.3.2] marks it *"04 §4's determinative input"* — a corrective failure and a preventive replacement are different facts, and a count that mixes them is the number a reviewer will challenge first. `occurred_at` is the headline timestamp and `recorded_at` is secondary and separately labelled [33 §6.4, 50 §5.6]. `m3_status_code`, `findings_code`, `triggering_driver`, and `triggering_prediction_id` are all rendered — the last two because they are [**D21**]'s treatment-assignment fields, and a reviewer assessing a causal claim needs to see whether the failures behind it were themselves model-assigned.

**Line 2 — *"Causal finding: ELP hypothesis [strength: moderate] (cited, not restated)."*** The parenthetical is exactly right and the chip is a defect.

| Issue | Rule |
|---|---|
| **`strength: moderate` is not in the vocabulary.** [25 §4] defines `S0`–`S4` with plain-English names — *"Examined, not established"*, *"Corroborated hypothesis"*, *"Adjudicated finding, strong evidence"*, *"Confirmed by intervention or test."* `moderate` is a synonym nobody authored | `CitationCard` renders the **band identifier and its [25 §4.4] name**, and no synonym. §13 correction 19 |
| **The structured object must be present, not only a rendering.** [28 §8.2] property 3: *"[e]very API response and every export containing a citation **contains the structured object**. The renderer's output is an *additional* field, never a replacement. A response schema in which `strength_carry` is optional is a contract-test failure"* | `CitationCard` renders `rendered_strength` as the readable line **and** exposes the structured `strength_carry` in an adjacent, expandable region that is **not** the only path to `confounders_unaddressed` — those render unconditionally, at the top level. `pui-citation-carries-structured-strength` |
| **`confounders_unaddressed` can never be elided.** [28 §8.2] property 3: the renderer *"has no code path that omits `confounders_unaddressed`"* — the UI inherits the obligation | `ResidualConfounderList`, never collapsed, never tooltipped |
| **No local strength, rank, score, threshold, or aggregation.** [28 §8.2] property 2 enumerates the forbidden columns — `local_strength`, `strength_rank`, `strength_score`, `strength_summary`, `strength_prose`, `combined_strength`, `consolidated_strength`, `is_strong`, `meets_threshold` — and property 4 forbids combining across citations | **The same denylist runs over this app's props, computed values, and label strings**, `[ESTABLISHED HERE]` on the precedent [50 §7.4] rule 4 set when it extended [27 §3.8]'s server-side denylist to the console. `pui-no-local-strength` |
| **Sorting citations is permitted; persisting or displaying a rank is not.** [28 §8.3]: the ordering is *"one pure function in `packages/canonical-schemas`"*; this app *"may **call** it — to sort citations for display"* and *"may **never** persist its output as a citation field"* | The sort control exists; **no rank number, position badge, or "top finding" label is rendered.** `pui-no-rank-displayed` |
| **`posture` separates supporting from contra, and a `contra` citation is never counted as support** | [28 §3.3.1]: *"[w]ithout the split, 'we examined this and it wasn't supported' and 'this supports redesign' occupy the same list."* Two labelled groups, never one list. `contra` citations also never satisfy G5 (§7.5) |
| **`attribution_agreement` is rendered as received, and never resolved** | [28 §8.4]: *"[a] design authority reading that the observable signature and the maintainer's physical finding pointed **different directions** is receiving exactly the signal doc 12 §9.3 exists to preserve — and a business case that quietly resolved the disagreement would have destroyed it at the last possible moment."* `pma_only`, `maintenance_only`, and `both` render distinctly |
| **`strength_carry_digest` is rendered** | It is [28 §8.2] property 1's whole enforcement mechanism, and a reviewer who can see the digest can ask whether it matches. Rendered as a short prefix with the full value available, alongside `rendered_by` — [28 §8.4]: *"names its renderer version so a rendering can be reproduced or repudiated"* |
| **No causal verb** | [28 DA-3]'s permitted vocabulary; [25 §4.5]'s denylist; [**D23**]. `pui-no-causal-verb` runs over this surface too |

**Line 3 — *"Test data: [no qualification record found]."*** This collapses four distinct claims into one, and [28 §3.2.3] says why that is indefensible:

> *"`absent_not_located` asserts that someone looked; `absent_unknown` asserts that nobody has. A `RedesignCase` reports the counts separately (§3.6), because 'we searched and the 1987 qualification file is gone' and 'we have not searched' carry different weight to a reviewer, and collapsing them into a single 'missing' count is the kind of loss that makes a business case indefensible on its first challenge."*

`TestCoverageTable` therefore renders **one row per expected test kind** from `dossier_test_coverage` [28 §3.3.2] — which [28 §3.3.2] guarantees is complete: *"a dossier always carries one row per expected test kind, present or absent. There is no code path by which a dossier's test section is silently empty."* Each row shows `test_kind_code`, `record_status` (six values, six distinct renderings), `outcome` (only where `record_status = 'present'` [28 §3.2.1]'s `outcome_only_when_present`), `qualification_credit`, `materialised_absence`, and `absence_basis`.

Three rules the UI must not get wrong:

1. **`qualification_credit` is `false` for every absence status, including `absent_not_required`.** [28 §3.2.2]: *"**Not required** is a statement about the qualification regime, not evidence about the component. It suppresses a finding of concern; it never creates a finding of confidence."* The UI renders `absent_not_required` in a **neutral** tone, never `good`. `pui-not-required-is-not-credit`.
2. **`materialised_absence = true` is rendered**, because it distinguishes *"the profile expected this and no record exists at all"* from *"a record exists and says the test was not performed."*
3. **`absent_unknown` is rendered as the most serious of the four**, in the `warning` tone with its own label — because it is the one condition G4 refuses (§7.5) and it means *nobody has checked*.

`test_attribution_ambiguity` [28 §3.6] is rendered alongside, from [28 §3.2.4]'s `eic_resolution`: a test artefact filed by EIC whose NIIN derivation was ambiguous is an ambiguity in the evidence, and hiding it would be [28 DA-13].

### 7.4 Dependency impact, and the accessibility treatment [50 §8.5] deferred

`WF #s9` draws a small node-link SVG (lines 1041–1049) with `role="img" aria-label="dependency graph placeholder"` and a box label carrying `72% graph completeness`. [50 §8.5] closes with: *"**Dependency graph** (sheet 09) is out of scope (§4.3); the same rules will bind it in [52]."* This is those rules.

**What it renders**, from the `impact_snapshot` fragment [28 §4.2]:

| Element | Source | Encoding |
|---|---|---|
| Root node | `root_niin` | Heavier stroke (`--bw-2`), as drawn |
| Part nodes | `impacted_parts[]`, positioned by `min_depth` | `--bw-1` stroke |
| Artifact leaves | `impacted_artifacts[]` with `artifact_kind` | Terminal, never expanded — [28 §4.3] property 4: *"[a]rtifacts are terminal, enforced by a CHECK constraint"* |
| Unverified edges | per-node `verified_edge_count` vs `edge_count` | **Dashed** (`--dash-guide`), as drawn. Not a colour difference |
| Truncation | `truncated_at_depth[]` | Nodes at the cap render an explicit truncation marker, because [28 §4.3] property 8 makes `nodes_truncated_at_depth` the difference between a ratio and a claim of totality |

**Six accessibility rules**, mirroring [50 §8.5]'s five-part map treatment and adapted for a graph that is **not interactive**:

1. **`<figure>` + `<figcaption>`.** The caption states what the figure shows and its completeness in words: *"Dependency blast radius for NIIN 013479201 to depth 3. 12 parts and 8 artifacts touched. 61.7 % of touched edges have a verified source. Bounded below: 3 nodes remained expandable at the depth cap."*
2. **`role="img"` is permissible here, and only because nothing inside is interactive.** [50 §8.5] rejects `role="img"` for the AOR map because *"`role="img"` prunes the entire subtree … and **wrong the moment a marker is interactive**"* — sheet 01 states *"[c]lick any marker → sheet 01B."* `WF #s9` states no such thing, and **no operation exists to drill into a graph node**: [28 §9.1]'s neighbourhood read `GET /dependencies?niin=&depth=` is not allowlisted (§5.3) because navigating to another NIIN's blast radius is not this sheet's job. So the graph is a static diagram, `role="img"` is correct, non-scenery is `aria-hidden`, and **the moment a later author makes a node interactive, rule 2 flips to [50 §8.5]'s `role="group"` treatment.** `a11y-depgraph-no-interactive-under-role-img` asserts the invariant rather than the current state, so the flip cannot be forgotten.
3. **`EquivalentTable` is required, not optional.** It renders `impacted_parts[]` (NIIN, `min_depth`, `relations[]`, `verified_edge_count` / `edge_count`) and `impacted_artifacts[]` (`artifact_kind`, `external_ref`, `via_relation`, `min_depth`) as real table rows. Two reasons, both from [50 §8.5]: it is the SC 1.1.1 text alternative for a schematic, and it is the SC 1.4.1 non-colour equivalent. A third reason is specific to this figure: the graph cannot show `unverified_by_relation` or `unverified_by_source_kind` at all, and [28 §3.6] says the aggregate *"hides which one you have."*
4. **No text below `--fs-100`** [50 §2.3, §8.5]. Node labels are NIINs — nine characters — so the `viewBox` is sized for `--fs-100` labels rather than the labels being shrunk to fit. Where they still do not fit, **the label is omitted from the figure and carried only in the equivalent table**, never rendered at 7 px.
5. **`DependencyCompleteness` renders the full object, not the ratio.** `completeness_ratio`, `edges_touched`, `edges_verified`, `nodes_expanded`, `nodes_truncated_at_depth`, `artifact_leaves_reached`, `unverified_by_relation{}`, `unverified_by_source_kind{}`, and `is_bounded_below` [28 §3.6]. `WF #s9`'s single `72% graph completeness` chip is a defect against [28 §3.6]'s own reasoning — §13 correction 20. And [28 DA-7] is unambiguous: *"[d]o not report dependency completeness as total, and do not omit it."*
6. **`is_bounded_below` renders as a sentence, not a boolean.** [28 §4.4]'s worked example is the model: *"38 % of the dependency edges in this blast radius have no verified source, and the radius is bounded below because the traversal was capped at depth 3 with three expandable nodes remaining."* `LowerBoundNotice` renders exactly that shape from the fields.

**Two further rules on the graph's honesty**, both from [28]:

- **An unverified edge is never presented as verified, whatever it carries.** [28 DA-8]: *"`inferred_cooccurrence` and `unverified_import` can never count as verified, whatever `verified_by` says. A statistical co-replacement pattern is a hypothesis about a dependency, not a dependency."* The UI computes no verification of its own; it renders `edge_verified` as the snapshot reports it.
- **`policy_version` and `is_placeholder` are rendered.** [28 §15] OD-3 leaves traversal direction and weights unresolved with *"`is_placeholder = true`, `policy_version` on every snapshot"*, and [28 DA-12] forbids shipping a traversal weight as a plain default. A blast radius computed under a placeholder policy says so. `B7` (`GET /impact-snapshots/{snapshot_id}`) backs a *"reproduce this traversal"* link — [28 §9.1]: *"[r]eproducibility of a cited traversal."*

### 7.5 The two-stage cost estimate and the gate

`WF #s9` draws three chips and two arrows: `parametric: qualified` → `gate: priority ≥ threshold` → `detailed: pending`. That is the right shape and it is under-specified in four ways.

`TwoStageCostBar` renders three stages from real state:

| Stage | State from | Renderings |
|---|---|---|
| **Stage 1 — parametric** | `cost_estimate` fragment with `method = 'parametric'` [28 §5.1] | `point_estimate_usd`; `low_usd`/`high_usd` **only with `interval_basis`** [28 §3.7]'s `interval_paired` — *"[a] ±30% band with no basis is a decoration that reads as rigour"*, so the UI renders no interval without its basis; `assumptions[]` in full, non-empty by constraint; `cost_model_version` and `model_ref`, the latter distinguishing `inservice:<fn>@<ver>` from `domino-endpoint:<name>@<ver>` [28 §2] so a reader knows whether the deterministic fallback produced the figure |
| **Gate** | B6's live `gate_decision` [28 §5.2] | `decision`, `gate_policy_version`, `thresholds_in_force`, and **`condition_results` per condition by identifier** — `G1` cost floor, `G2` priority floor, `G3` completeness floor, `G4` zero `absent_unknown`, `G5` the disjunctive evidentiary floor, `G6` state and dossier consistency [28 §5.3]. On a `fail`, the `remedy` string is rendered verbatim: [28 §5.5]: *"`failed_conditions` names the conditions by identifier, so the response is actionable and the gate is debuggable"* |
| **Stage 2 — detailed** | `cost_estimate` with `method = 'dependency_rollup'`, or its absence | `cost_lines` per class [28 §5.6]; `coverage_ratio`; **`is_lower_bound`** |

Four rules, each of which the wireframe's three chips do not carry:

1. **A `dependency_rollup` over an incomplete graph is a lower bound and says so.** [28 §3.7]'s `rollup_incomplete_is_lower_bound` CHECK makes `is_lower_bound = (coverage_ratio < 1.0)` structural, and [28 §3.7] states the payoff: *"[t]hat single fact — **this number can only go up** — is what a design authority most needs and what an unqualified total silently destroys."* `LowerBoundNotice` renders it adjacent to the figure, never in a tooltip, never below a fold. `pui-rollup-lower-bound-adjacent`.
2. **Every cost factor is a placeholder and is marked.** [28 §5.6]: *"[e]very factor is `PLACEHOLDER` in `cost_model_version` and enumerated in `assumptions[]` … so no reader of a demonstration case can mistake the factors for validated rates"* [28 §15 OD-2, DA-12]. `PlaceholderFactorNotice` renders it once, prominently, for the whole box.
3. **`detailed: pending` is three distinct states and the UI distinguishes them.** *No gate decision yet*; *gate failed, so a roll-up is refused* [28 §5.5]'s `409 gate-not-passed`; *gate passed and no roll-up has been produced*. Collapsing them to "pending" tells a reviewer nothing about what to do next, which is the opposite of what `remedy` exists for. `pui-detailed-pending-disambiguated`.
4. **The gate is never presented as an evidentiary judgment.** [28 DA-10] and [28 §5.3]'s note on G5: *"[t]he gate exists to decide where to spend estimation effort. Smuggling an evidentiary sufficiency test into it would move a decision that belongs to a human into a configuration constant."* So `GateConditionTable`'s caption states that the gate decides estimation effort, not merit — and the UI never renders "gate passed" in a way that reads as "the case is justified." A `503 gate-thresholds-unconfigured` [28 §9.2] renders as a `ProblemDetail` naming [28 OD-1], not as a failed gate: an unconfigured threshold is a deployment state, not a verdict.

### 7.6 Recommendation, limitations, and evidence gaps — required by the schema, absent from the sheet

`WF #s9` draws no recommendation region. [28 §3.6]'s `assembled_is_complete` CHECK makes all four fields mandatory on an assembled or published case, and requires `recommendation_limitations` and `recommendation_evidence_gaps` to be **non-empty arrays**. [28 §1.2] E3 states the reason:

> *"`limitations[]` and `evidence_gaps[]` are **required and non-empty** — a recommendation that claims no limitations cannot be persisted. This is what makes 'to a standard a design engineer can evaluate and defend' checkable: **the case states what it does not know.**"*

**A review surface that renders the cost and the graph but not the limitations shows a reviewer the confident half of the package.** §13 correction 21. `RecommendationBox` is therefore specified here and is **required, not optional**:

| Field | Rendering |
|---|---|
| `recommendation_stance` | The closed, non-directive vocabulary [28 §1.2 E3]: `redesign_warranted_for_evaluation`, `insufficient_evidence`, `monitor_and_reassess`, `no_action_indicated`. **Rendered as the enum's own words.** No paraphrase, and in particular **never** *"recommended"* or *"approved"* — `redesign_warranted_for_evaluation` warrants an *evaluation*, and the difference is the whole of [28 DA-1] |
| `recommendation_basis_refs` | Resolvable references, rendered as links into the dossier, the snapshot, and the citations they name |
| `recommendation_limitations[]` | **In full, never collapsed, never truncated, never behind a disclosure toggle.** The same treatment [50 §7.4] rule 2 gives the contributor disclosure, for the same reason |
| `recommendation_evidence_gaps[]` | Likewise |
| `case_status` | With its meaning stated: `published` means *"released to a design authority as a decision package"* [28 §1.2 E1], and [28 §6.5] is explicit that *"publication is still not a redesign decision … The distinction is stated in the aggregate's description, in the event's AsyncAPI description, and **in the practitioner UI**, because it is the one a reader is most likely to collapse."* **That sentence names this surface, and this is where the obligation is discharged**: a persistent `SheetNote` in the annotation voice states it, and `pui-published-is-not-approved` asserts the string is present whenever `case_status = 'published'` |
| `case_version` | Rendered. [28 §3.6]'s `case_version_unique` makes versions real, and [28 §6.4]'s payload carries `case_version` as *"[t]he version the agent read at its step 10"* — a reviewer looking at a different version than the proposal was raised against needs to see it |

**This surface renders the recommendation; it does not author it.** The stance, limitations, and gaps are written by the human at `POST /redesign-cases/{id}/assemble` [28 §6.1 step 9], and that operation is **not allowlisted** (§5.3) because the drafting surface is undrawn. §13 correction 10 records the gap between [42 §13.3]'s claim that `apps/practitioner` *"is where a human commits `POST /redesign-cases/{id}/assemble`"* and the fact that `WF #s9` draws no control for it.

### 7.7 Adjudication with dual control

`WF #s9` draws **no adjudication controls at all** — the sheet ends at the cost estimate. But the sheet is the review surface for a `redesign_case` proposal, `redesign_case` is one of [03 §7.2]'s eight `ProposalKind` values, and [28 §6.5] makes human adjudication the **only** route to `published`. §13 correction 22.

**Determination: Sheet 09 adjudicates through the gateway's unified queue, not through Design Advisory's own operations.** `[ESTABLISHED HERE]`, with four reasons:

1. **[42 §13.3] says so.** *"**Adjudication is elsewhere.** The unified queue is the gateway's (04 §11, 30 §4), with dual-control surfacing through `awaiting_second_signature` and the `flagged_non_program_evidence` filter (30 §4.5)."*
2. **The `ETag` mechanism is specified there and only there.** [30 §4.6] states three inviolable rules — `If-Match` forwarded verbatim and never synthesized, no authority check at the gateway, `Idempotency-Key` forwarded verbatim — and [30 §4.6]'s detail fetch is *"[t]he queue row **plus** the full proposal, fetched synchronously from the owner … and **the owner's `ETag` passed through verbatim**."* [28 §9.1]'s own `POST /proposals/{id}/adjudicate` says only *"`If-Match` required; `design_authority`"* and specifies no equivalent detail contract.
3. **The drill-down and the action then live on one ingress surface.** `redesign_case_detail` is gateway-owned [30 §3.2]; adjudicating through a different surface would mean the evidence and the act arrive by two paths with two failure modes.
4. **`non_program_evidence_only` is a queue-row field.** [30 §4.5]'s projection carries it; [30 §2.4] calls it *"[t]he one thing an adjudicator must see before opening."* Reaching the proposal any other way loses it.

**This means two surfaces can adjudicate the same proposal, and that is correct.** [51 §15] renders the same composed view inside `apps/web`'s sheet-10 panel. Both paths send `If-Match` on the owner's `ETag` and neither synthesizes one, so a race fails safe with a `412` [30 §4.6, **D16**] — and at class or fleet scope the second of two signatures may legitimately arrive from the other surface. **Neither document removes its path.** §0.3 and §14 **R-52-4**.

**The flow.** Five steps.

| # | Step | Call | Rules |
|---|---|---|---|
| 1 | **Open the proposal** | B3 `GET /api/v1/gateway/proposals/{proposal_id}` | Returns the queue row's presentation flags merged with the owner's full `Proposal` — `payload`, `evidence[]`, `rationale` — and the owner's `ETag`. `staleTime: Infinity` (§5.4). **The `ETag` is captured once** and is what step 5 sends. On `503 owner-unavailable`: [30 §4.6] returns *"[n]ever a partial proposal"*, and neither does this surface — `ProblemDetail` with retry, and **no adjudication control** |
| 2 | **Claim** | B4 `POST /api/v1/gateway/proposals/{proposal_id}/claim`, `Idempotency-Key` required | Proxied to the owner [30 §4.6]. The gateway *"**does not implement the lease**"* — and neither does this app |
| 3 | **Review** | — | The panel renders, before any control is reachable: `NonProgramEvidenceFlag` (see below), `evidence[]` with `source_trust` per item, `blast_radius`, `authority_class`, `requires_dual_control`, `second_signature_outstanding`, `valid_until` with `expires_within_hours`, `baseline_id`/`baseline_epoch`, `epoch_superseded`, `confidence` **labelled as the agent's claim** [30 §4.4], `agent_id`/`agent_version`, and `QueueFreshnessNotice` where `queue_freshness.stale` [30 §4.5, 50 §10.2] |
| 4 | **Confirm** | `AdjudicationConfirm` (`AlertDialog`) | States the decision, the blast radius, **which signature this is**, and the required second class where applicable; enumerates the evidence being attested (§5.5); requires `adjudication_note`. **Refuses with a stated reason if `dossier` or `causal_findings` was not `ok`** (§5.5's added rule, and [30 §4.6]'s reasoning) |
| 5 | **Adjudicate** | B5 `POST /api/v1/gateway/proposals/{proposal_id}/adjudicate`, `Idempotency-Key` + `If-Match` on the step-1 ETag | On `200`: invalidate `["proposals","detail"]`, `["proposals","list"]`, and `["views","redesign-case", caseId]` — the last because approval transitions the case to `published` [28 §6.5]. **Do not optimistically update** [50 §5.6]. On `412`: refetch, re-render, require re-confirmation. On `409 baseline-superseded` [28 §9.2]: [03 §7.2]'s re-validation rejected it — render the reason and offer refresh, never a retry of the same body. On `403 authority-insufficient` [28 §9.2] or [31 §3.5]'s `not-authorized`: render with `reasons` |

**Dual control, per the corrected rule.** [03 §7.2.1] as amended and [31 §6.4] as amended both now require dual control for `redesign_case` at **class and fleet** scope, closing [28 §16] correction 3. [28 §6.4] already implemented the stricter reading, deriving `blast_radius` from the dossier's `affected_population` and never from the caller:

| `blast_radius` | Authority | Dual control | Rendered |
|---|---|---|---|
| `item`, `asset` | `design_authority` | No | `DualControlBadge` absent |
| **`class`** | `design_authority` | **Yes** | `DualControlBadge`, *"signature 1 of 2"* / *"signature 2 of 2"* |
| **`fleet`** | `design_authority` | **Yes** | Likewise |

Five rules on the rendering:

1. **`requires_dual_control` from the row is what governs, not a client-side derivation from `blast_radius`.** [28 §6.4] sets it at creation and [03 §7.2] re-validates it at adjudication; a UI that recomputed it would be a third implementation of a rule two documents already disagreed about once.
2. **The second signature must be a different human**, and at class/fleet scope [31 §6.4]'s generalized rule additionally checks that signer's authority — the defect [42 §18] item 17 found, where a second signature *"[was] satisfiable by any authenticated human distinct from the first adjudicator."* The dialog states both requirements.
3. **The second adjudicator reaches the same case by URL** (§5.1 rule 1, §7.1's route). This is why the proposal id travels on the link.
4. **`second_signature_outstanding` and [30 §4.5]'s `awaiting_second_signature` filter are the discovery path** — and they live on `apps/web`'s sheet 10, not here, because `CaseSelector` (§5.1 rule 4) filters `design-advisory`'s own `GET /proposals`, which declares no such parameter [28 §9.1]. Reconciliation item **R-52-3**: sheet 10's `redesign_case` rows should offer a launch into this surface. §13 correction 23 notes that doing so requires `case_id`, which the queue row does not carry.
5. **No control is enabled or disabled on an authority guess.** §4.7. Every refusal is the server's, with `reasons`.

**`NonProgramEvidenceFlag` is stricter here than anywhere else in the corpus.** [30 §2.4] makes it *"[t]he one thing an adjudicator must see before opening"*; [50 §5.6] makes it non-collapsible. [28 §6.4] goes further **for this proposal kind specifically**:

> *"[A] proposal resting solely on non-program content is flagged to the adjudicator — **for this proposal kind that flag is close to disqualifying**, and the adjudication UI surfaces it prominently."*

So: `non_program_evidence_only = true` renders the flag in the `critical` tone, outside every collapsed region, **above** the decision controls, carrying [28 §6.4]'s own framing that for a `redesign_case` it is close to disqualifying. And [28 §6.4]'s minimum evidence composition — `case_id`, `dossier_id`, `impact_snapshot_id`, `gate_decision_id`, `cost_estimate_id`, each `source_trust: program` — is rendered as a checklist, so a proposal missing one is visible before the operator acts. `pui-non-program-flag-critical`.

**What the payload is, and what it is deliberately not.** [28 §6.4]'s `RedesignCaseProposalPayload` carries `case_id`, `case_version`, `candidate_id`, `dossier_id`/`dossier_version`, `impact_snapshot_id`, `gate_decision_id`, `cost_estimate_id`, optional `scenario_id`, `carried_digests`, `narrative_sections[]`, `evidence_gaps[]`, `limitations[]`, `prompt_digest`, `manifest_pins[]`, `renderer_versions[]`. It **deliberately omits** `recommendation_stance`, `recommendation_limitations`, `recommendation_evidence_gaps`, any strength band, any cost figure, and `blast_radius`/`authority_class`.

**Two rendering rules follow, and both are easy to get wrong:**

- **The committed case's fields are what the panel renders, never the payload's derived lists.** [28 §6.4]: duplicating the recommendation into the payload *"would create a second, agent-authored version an adjudicator could act on instead of the committed one."* The payload's `limitations[]` and `evidence_gaps[]` are the **agent's derivation**; [42 §13.3] describes rendering *"the divergence between the agent's derived lists and the case's committed fields."* This surface renders the **committed** fields as the case (§7.6) and, where they differ, a labelled divergence — never the agent's list in place of the case's.
- **`carried_digests` are attestations, not assertions.** [28 §6.4]: *"this service re-validates against current state at adjudication regardless."* The panel renders them as what the agent read, with the label; it computes no digest of its own and asserts no match.

### 7.8 Degraded fragments: what each one must not render

The single most consequential rendering table in this section. [30 §3.4]: *"The UI must render the gap; it must not render zero."*

| Fragment not `ok` | Must render | Must **never** render |
|---|---|---|
| `impact_snapshot` | `DegradedFragmentNotice` naming the fragment and outcome; the graph region replaced by the notice | A completeness ratio, `is_bounded_below: false`, an empty graph, or a graph of the parts the dossier happens to mention. **An unfetchable blast radius is not a small blast radius**, and [28 DA-7] forbids reporting completeness as total |
| `cost_estimate` | `DegradedFragmentNotice`; the two-stage bar shows stage states as unknown | `$0`, a dash that reads as "no cost", `is_lower_bound: false`, or *"detailed: pending"* — which is a claim about the gate, not about the fetch (§7.5 rule 3) |
| `causal_findings` | `DegradedFragmentNotice`, **and the dossier's own citations remain rendered** — they are carried verbatim in the `dossier` fragment [28 §3.3.1] and do not depend on the drill-down | *"No causal findings"*, an empty citation list, or a case that reads as resting on field failures alone. This is the sharpest case: a reviewer who cannot see the citations would assess the case as **weaker** than it is, and a reviewer who sees an empty list would assess it as **unsupported** — two opposite errors from one silent empty array |
| `dossier` or `redesign_case` | The whole sheet renders `ProblemDetail` [30 §3.4] | Any partial sheet. `503 required-fragment-unavailable` *"has no partial body"* |
| Any | `degraded: true` renders the notice even when the sheet otherwise looks complete | A complete-looking sheet with no notice. `ui-degraded-view-renders-notice` [50 §10.2] |

**And the adjudication rule that follows:** if `dossier` or `causal_findings` is not `ok`, the confirm dialog refuses with a stated reason (§5.5, §7.7 step 4). [30 §4.6]'s words are the authority: adjudicating on evidence that *"could not be read is precisely D16's defect wearing a friendlier face."*


---

## 8. Classification, disclosure, and language discipline

### 8.1 Why the marking matters more inside a Domino App

[50 §7] establishes `ClassificationBanner`, `ClassificationFooter`, `AdvisoryBanner`, and `ContributorDisclosure`. Their specifications are not restated. What changes here is the **weight** of the marking, and the reason is structural:

**In `apps/web`, the program's chrome surrounds the sheet.** The masthead, the classification bar, the side nav, and the footer are all program-authored, so a sheet inherits a marked frame. **In `apps/practitioner`, the surrounding chrome is Domino's** — a vendor interface with its own branding, its own navigation, and no knowledge of the program's marking obligations. [02 §4.1]: applications are *"served from a single deployment-wide subdomain and iframed."* A practitioner sheet that omitted its banner would render **unmarked program content inside a vendor frame**, and a screenshot of it would carry no marking at all.

Four consequences, all `[ESTABLISHED HERE]`:

1. **`ClassificationBanner` and `ClassificationFooter` are rendered by `AppFrame`, outside every route**, so no route can fail to render them [50 §7.2 rule 4]. `pui-classification-on-every-route` asserts both render on every route of both surfaces.
2. **Both are rendered inside the app's own document**, never delegated to a host page, and never suppressed on the grounds that the app is embedded. There is no `?embedded=1` mode that drops them.
3. **The banner states that this is a program surface**, not a Domino one. `[ESTABLISHED HERE]` A one-line identity element in the title block area — *"FATHOM — <sheet title>"* — because inside Domino's chrome nothing else tells a reader which system authored the content they are about to screenshot. It is not branding; it is attribution of the marking.
4. **[50 §14] UI-OQ-10 (print and export) binds here first.** A drafting-sheet review surface inside an iframe is the most likely thing in the whole console to be printed or screenshotted into a slide, and a dossier that reaches paper without its marking, its limitations, and its lower-bound qualification is the exact failure [03 §7.3] and [28 §3.7] exist to prevent. `@media print` retains the banner, the footer, `LowerBoundNotice`, `DependencyCompleteness`, `RecommendationBox`'s limitations and gaps, and the *"decision package, not a decision"* note. **[AMENDMENT]** No longer prints §4.7's level-scoping notice — that notice was removed once `31 §5.8` landed, since there is no interim condition left for it to describe. §14 P-OQ-4 carries the residual question of whether print is in scope at all.

### 8.2 Which disclosure components apply, and which do not

| Component | Applies here | Basis |
|---|---|---|
| `ClassificationBanner`, `ClassificationFooter` | **Yes, both, on every route** | [03 §7.3]: *"[m]inimum marking is `CUI` in both banner and footer."* §8.1 |
| `AdvisoryBanner` | **No** | [27 §8.1] requires the `advisory` block on *"[e]very 2xx response from every readiness, risk-flag, explanation, and status-summary operation."* Neither `failure-intel` nor `design-advisory` serves one, and neither sheet renders a readiness figure. **Rendering an advisory banner over a causal finding would be a category error** — a hypothesis is not an advisory readiness score, and the two framings are different rules. If a later surface here renders a readiness figure, [27 §8]'s four mechanisms bind immediately |
| `ContributorDisclosure` | **No — but its logic recurred once** | [27 §3.7]'s block is carried by readiness and explanation responses, which these surfaces do not call. §4.7 briefly carried an interim level-scoping notice built on exactly [27 §3.7]'s reasoning — *"silent renormalization converts a partial view into something indistinguishable from a total view … Publishing is therefore more protective than silence"* — but that notice was removed along with the interim it belonged to once `31 §5.8` landed (§4.7). [30 §4.5]'s `queue_freshness.completeness: "level_scoped"` is the queue's own, still-live instance of the same rule and **is rendered** on Sheet 09 |
| `DegradedFragmentNotice` | **Yes** | §7.8 |
| `QueueFreshnessNotice` | **Yes, Sheet 09** | [30 §4.5], [30 §4.7]. `ui-queue-freshness-rendered` [50 §10.2] |
| `NonProgramEvidenceFlag` | **Yes, Sheet 09, in the `critical` tone** | §7.7 |

### 8.3 The classification label itself

| Rule | Basis |
|---|---|
| Data-driven, never hard-coded, in any environment | [50 §7.2 rule 2]. `ui-classification-banner-is-data-driven` |
| Derived labels are disclosed as derived | Sheet 09 is backed by a composed view, so its `X-Classification` is *"the union of the contributing fragments' labels … accumulating `inherited_from`"* [30 §7.3]. The banner renders *"derived label"* and `inherited_from[]` in its expandable detail [50 §7.2]. [03 §7.3]: *"**Aggregation is a classification event**"* |
| A missing `X-Classification` is a fault, not a default | [50 §7.2 rule 5]. Never substitute `U` |
| Markings are never reordered, abbreviated, or alphabetized | [03 §7.3], [50 §7.2]. `dissemination[]` in [03 §7.3]'s declared order |
| Retired markings never rendered, never a literal anywhere | `FOUO`, `U//FOUO` [03 §7.3, DoDI 5200.48 §3.4.b]. [10 §4.4]'s `FTH005` extends to this app [50 §7.2 rule 3]. `ui-no-retired-markings` |
| Every citation, dossier, snapshot, and estimate carries its own `classification` | [28 §3.3], [28 §3.7], [25 §2.3] all carry `classification jsonb NOT NULL`. Where a rendered region's label differs from the view's union, the region's label is rendered on the region |
| **`PlaceholderCodeMarker`** | [25 DO-NOT-14]: no ISO 14224 conformance claim for a `FATHOM-EXT-nnn` subject mode; *"the marker travels with every rendering."* [28 §3.2.1]'s `FATHOM-TK-###` test kinds carry the same discipline via `code_authority`. `pui-placeholder-code-marked` |

### 8.4 Language discipline — the one rule these two sheets exist to protect

Three documents converge on the same prohibition, and this app is where all three land at once:

- [09 §9.3 item 20] / [**D23**]: *"**Do not render `contributing_factors` in causal language** … A causal statement must cite an adjudicated Failure Intelligence hypothesis."*
- [25 DO-NOT-3]: *"**Do not present a hypothesis as an established cause.** … Presenting algorithmically derived causes as established fact to a design authority would be both wrong and, on first contradiction, fatal to the program's credibility."*
- [28 DA-3]: *"**Do not use causal language for a causal finding beyond calling it a hypothesis.** The permitted vocabulary is *'hypothesis, adjudicated `<state>` by Failure Intelligence'*. Not *cause*, *root cause*, *caused by*, *determined*, *proves*, *confirms*, or *establishes* — in a rendered strength, a case narrative, an agent response, **or a UI label**."*

That last clause names this document's output. So:

| Rule | Enforcement |
|---|---|
| [25 §4.5]'s forbidden vocabulary runs as a **denylist over component names, prop names, label strings, ARIA labels, and test fixtures** in both surfaces and in `packages/ui/src/evidence/` | `pui-no-causal-verb`. Modelled on [50 §7.3 rule 4]'s extension of `FS-TERM-001` to console code, and on [10 §4.4]'s `FTH005` |
| The generated `statement` is rendered **verbatim** and is the only place a causal verb may appear — and only at S4 | §6.3. `pui-statement-verbatim` |
| No rendered text asserts that a case, a finding, or a redesign is approved, authorized, directed, funded, or scheduled | [28 DA-1], [28 §1.2] E1–E4. `pui-no-decision-verb` runs a decision-verb denylist over both surfaces, mirroring [28 §13.5]'s `T-NODECISION-1` route scan |
| `published` never renders as *"approved"* | §7.6. `pui-published-is-not-approved` |
| [27 §8.3]'s `FS-TERM-001` denylist runs over this app | [50 §7.3 rule 4] extends it to `apps/practitioner`. Neither sheet renders readiness, so the list should never fire — which is exactly why it is cheap to run |
| No component branches on `tier`; `reference_class` only | [09 §9.3 item 21] / [**D7**, **D19**], `FTH006`. `ui-no-tier-branch` [50 §10.2] |

---

## 9. Accessibility

[50 §8]'s baseline — WCAG 2.2 AA, every named test in [50 §8.1]–[50 §8.6], plus `a11y-axe-clean` at zero `serious` or `critical` violations — binds **in full** and is not restated. Three deltas.

### 9.1 What the iframe changes

| Concern | Rule |
|---|---|
| **The document title is not the tab title.** Inside an iframe the browser tab shows Domino's title | [50 §4.4]'s `document.title` rule still applies (a screen reader's document list and the iframeless view both use it), **and** the `<h1>`/`<h2>` heading structure plus the polite live region carry the announcement. §5.1 rule 5 |
| **The skip link's target is inside the frame** | `SkipLink` targets this document's `<main>`, never `window.top`. It is still the first focusable element [50 §8.1] |
| **Focus must not be moved on load** beyond what [50 §4.4] specifies | An iframe that steals focus on load moves the user out of the host page's reading order. Focus moves to the `<h2>` on **route change**, not on initial mount |
| **Theme mismatch is expected and must not reduce legibility** | [50 §6.5]: a practitioner surface may render dark inside a light Domino page. **Both themes independently meet [50 §8.4]'s contrast table**, including the `.chip` label fix, so a mismatch is an aesthetic discontinuity and never a legibility failure. `a11y-contrast` [50 §10.2] covers both themes and both surfaces |
| **Zoom and reflow** | [50 §8.6]: reflow at 320 px CSS width via the single `--bp-narrow` breakpoint. **An iframe's viewport is the frame's, not the window's**, so a narrow Domino panel triggers the same collapse a narrow window would — which is the desired behaviour and is what makes one breakpoint sufficient. `WF #s9`'s `row wrap-mobile` is the drawn opt-in [50 §2.4] |
| **Target size** | SC 2.5.8's 24 × 24 px minimum [50 §8.6]. **The dependency graph has no interactive targets** (§7.4 rule 2), so the map's hit-area problem does not recur; if a node becomes interactive, both the hit area and `role="group"` become required together |

### 9.2 The dependency graph

Named tests, from §7.4:

| Test | Asserts |
|---|---|
| `a11y-depgraph-figure` | `DependencyGraph` renders inside `<figure>` with a `<figcaption>` stating scope, counts, completeness, and bounded-below state |
| `a11y-depgraph-no-interactive-under-role-img` | No focusable element, no click handler, and no `role="button"` exists inside an SVG carrying `role="img"`. **Asserts the invariant, not the current state** — so making a node interactive fails the build until the treatment is changed to [50 §8.5]'s `role="group"` shape |
| `a11y-depgraph-equivalent-table` | `EquivalentTable` renders for every `DependencyGraph`, with a row per impacted part and per impacted artifact. Not optional [50 §8.5, item 42] |
| `a11y-depgraph-scenery-hidden` | Edges, guides, and decorative geometry are `aria-hidden` |
| `ui-font-size-floor` | No label below `--fs-100`, including inside the SVG [50 §2.3, §8.5] |

### 9.3 Tables, states, and the panel

| Requirement | Rule |
|---|---|
| Every `WfTable` has a `<caption>`, visually hidden where the enclosing `Box` label already names the region [50 §8.3] | The evidence table, the test-coverage table, and both equivalent tables |
| `WfTableScroll` is `role="region" tabindex="0" aria-labelledby` [50 §3.2, §8.1] | The hypothesis list and the impacted-parts table both scroll horizontally at narrow widths |
| Sort controls are `<button>`s inside `<th>` with `aria-sort` [50 §3.3 gap 1] | Citation sort (§7.3) and any column sort. `a11y-sortable-headers` |
| `StatusChip` never conveys state by colour alone; the word is mandatory and the dot is `aria-hidden` [50 §8.3] | Every `record_status`, `gate_verdict`, `posture`, `adjudication_state`, and `source_trust` chip |
| `EvidenceStrengthMeter` is not colour-only | §6.3: position plus mandatory adjacent text |
| `AdjudicationConfirm` is `role="alertdialog"` with a required description, focus-trapped, and does not dismiss on outside click [50 §3.2] | Radix `AlertDialog` supplies it; the description is the confirm text of §6.4 step 4 / §7.7 step 4 |
| One polite live region per surface, in `AppFrame` [50 §4.4, §8.3] | Route announcements and mutation results |
| No `outline: none`, anywhere [50 §8.2, item 39] | `a11y-no-outline-none` |

---

## 10. Testing

[09 §2.6] fixes **Vitest + Testing Library** for the SPA and [09 §2.2] fixes **pytest** for Python. [50 §10.1] adds `axe-core` (`>=4.10`, mirrored into the private index per [09 §2.2]'s air-gap rule) and in-repo contrast assertions. Nothing new is adopted. [50 §10.1]'s third row stands: **no E2E tool** — [50 §14] UI-OQ-7.

### 10.1 What runs where

| Suite | Location | Runs against |
|---|---|---|
| SPA component and route tests | `apps/practitioner/tests/ui/` | MSW-style handlers over the **committed OpenAPI documents** of `failure-intel`, `design-advisory`, and `gateway`, so a contract change breaks a UI test rather than a deployment |
| SPA fixtures | `apps/practitioner/tests/ui/fixtures/` | The conformance datasets of `packages/contracts/conformance/failure-intel/` and `.../design-advisory/dataset/` [28 §16] correction 5, **not hand-authored JSON**. [50 §12.1]'s adopted item — *"[c]omponent and route tests run against committed fixtures"* — applied here |
| Host tests | `apps/practitioner/tests/host/` | pytest, with the gateway stubbed. Every rule of §2.3, §3.1, §3.4, §4.2–§4.5, §5.3 |
| Accessibility | Both surfaces, every route, every `packages/ui/src/evidence/` component | `a11y-axe-clean` at zero `serious`/`critical` |
| Contrast | `packages/ui`'s `contrast.fixture.ts` [50 §2.1] | Unchanged; both themes |

**Two fixture requirements that are not optional**, because without them the sheets cannot be exercised at all:

1. **`failure-intel` must supply hypotheses at every band `S0`–`S4`**, with at least one carrying a non-empty `residual_confounders[]`, one with `caps_applied` containing `C-DT`, one with `C-TAX` and a `fathom-extension` subject, one `gate_verdict: 'restricted'`, one superseding a prior with a `novelty_basis`, and one in each of `unsupported`/`refuted`/`withdrawn`. [25 §10.1]'s reference dataset is the source; §13 correction 24 asks whether it covers all of them.
2. **`design-advisory` must supply a case with `completeness_ratio < 1.0` and `nodes_truncated_at_depth > 0`, a `dependency_rollup` estimate with `is_lower_bound = true`, at least one row of each `test_record_status`, one `contra` citation, one `attribution_agreement: 'pma_only'`, and one proposal at `class` blast radius.** [28 §16] correction 5 already records that document 13 *"[g]enerates no test records, coverage profiles, or dependency edges"* and that the dataset is authored in the conformance directory. **Without those rows Sheet 09's honesty machinery is untestable**, which is the same argument [28 §16] correction 5 makes for the service.

### 10.2 The named tests

Contractual, in [50 §10.2]'s sense: a later document adds and removes nothing.

**Host — the process (`host-*`)**

| Test | Asserts |
|---|---|
| `host-base-path-validated` | A `DOMINO_RUN_HOST_PATH` failing `^/[A-Za-z0-9._~/-]*$` fails startup; unset yields `/` (§2.3) |
| `host-head-injection-escapes` | The rendered `index.html` HTML-escapes the base path, and a value containing `"`, `<`, or `&` never reaches substitution (§3.1) |
| `host-base-href-present` | Both `<base href>` and `<meta name="fathom-base-path">` are present and agree (§3.1, §3.3) |
| `host-catchall-returns-index` | A nested unknown path under the prefix returns `200` + `index.html`; a `static/` miss returns `404`, never HTML (§3.4) |
| `host-rejects-username-header-tier` | A request carrying only a Domino username header is `401` (§4.3) |
| `host-verifies-identity-assertion` | A JWT with a bad signature, wrong `iss`, expired `exp`, or `alg: none`/HMAC is `401` (§4.3) |
| `host-no-claimed-subject` | A body or query field named `sub`/`subject`/`user`/`principal`/`on_behalf_of` is rejected `400` (§4.3) |
| `host-sends-one-credential` | **[AMENDMENT — corrected; superseded a `host-sends-two-credentials` test for the two-credential shape §4.4 no longer implements.]** Every outbound call carries exactly one `Authorization` header, the exchanged `fathom` token — never a workload token, never both (§4.4) |
| `host-never-sends-caller-authorization` | No outbound request ever carries `X-Fathom-Caller-Authorization`; that header is exclusively `31 §5.4`'s Endpoint-proxy credential (§4.4 property 2) |
| `host-never-synthesizes-if-match` | No outbound `If-Match` absent from the inbound request (§4.4) |
| `host-adds-only-declared-headers` | The outbound header set is exactly the declared transform of the inbound set (§4.4) |
| `host-passthrough-byte-identical` | Status, `Content-Type`, and body byte-identical; `ETag`, `Retry-After`, `X-Classification`, `Deprecation`, `Sunset`, `Idempotency-Replayed`, `Location` verbatim (§4.5) |
| `host-never-rewraps-problem` | An upstream `urn:fathom:problem:<slug>:…` reaches the client unchanged (§4.5) |
| `host-origin-required-on-unsafe` | An unsafe method with a wrong or absent `Origin` is `403` (§4.5) |
| `host-allowlist-enforced` | A path outside the surface's allowlist is `404` **before** any outbound call (§5.3) |
| `host-allowlist-no-drift` | `allowlist.py` regenerates from `keys.ts` with no diff (§5.3) |
| `host-no-response-cache` | Two identical inbound reads produce two outbound calls (§2.3 rule 1) |
| `host-no-viewer-state` | No module holds state keyed by viewer identity (§2.3 rule 2) |
| `host-token-refresh-monotonic` | Refresh arithmetic uses `time.monotonic()`; no `time.time()`/`datetime.now()` in the refresh path (§4.2, **D29**) |
| `host-no-credential-in-output` | The client secret and the access token appear in no log line, response, or problem body (§4.2) |
| `host-deadline-below-ceiling` | `FATHOM_OUTBOUND_DEADLINE_MS` is required and rejected at or above 300 000 (§2.7) |
| `host-no-settings-defaults` | Every `Settings` field except the base path is required (§4.2) |
| `host-launchfile-no-install` | Neither launch file contains a package manager or a source fetch (§2.4, **D26**) |
| `host-logs-are-json-with-correlation` | Every log line is JSON and carries `correlation_id` (§2.3, [09 §8.6]) |

**Practitioner SPA — shared (`pui-*`)**

| Test | Asserts |
|---|---|
| `ui-practitioner-basename-from-runtime` | [50 §10.2]'s existing test; the basename comes from the meta tag, never a build constant |
| `pui-api-prefix-derived` | The fetch client's base URL derives from `BASE_PATH` in one place (§3.2) |
| `pui-no-relative-url-literal` | No relative `href`/`src`/`action` literal outside emitted asset tags (§3.3) |
| `pui-no-window-top` | No `window.top`, `window.parent.location`, `top.location`, or `_top`/`_parent` target (§3.5) |
| `pui-postmessage-origin-checked` | No `postMessage` listener without an origin allowlist check; `"*"` never appears (§3.5) |
| `pui-prefs-never-throws` | With storage stubbed to throw, every preference read returns a default (§3.5) |
| `pui-no-external-subresource` | No `http(s)://` URL in any emitted asset, CSS `url()`, or entry HTML (§3.5) |
| `pui-no-role-gated-route` | No route redirects or renders null on a role (§5.1) |
| `pui-allowlist-matches-keys` | Every allowlist entry is reached by a query or mutation, and every query resolves to an entry (§5.3) |
| `pui-adjudicate-sends-if-match` | Every adjudication carries `If-Match` and `Idempotency-Key`; a `428` is a build failure (§5.5) |
| `pui-confirm-enumerates-evidence` | The confirm dialog lists the evidence being attested, and refuses when an item is unavailable (§5.5) |
| `pui-note-required` | An empty decision note does not submit (§5.5) |
| ~~`pui-interim-scoping-notice`~~ | **[AMENDMENT — removed.]** Asserted the `FATHOM_INTERIM_LEVEL_SCOPED` notice rendered outside every collapsed region; the notice and its flag no longer exist, superseded along with the interim they described once `31 §5.8` landed (§4.7) |
| `pui-no-signout-control` | Neither surface renders a sign-out control (§4.7) |
| `pui-classification-on-every-route` | Banner **and** footer render on every route of both surfaces (§8.1) |
| `pui-placeholder-code-marked` | A `fathom-extension` / `FATHOM-TK-###` code renders its marker (§8.3) |
| `pui-no-causal-verb` | [25 §4.5]'s denylist over component names, prop names, labels, ARIA labels, and fixtures (§8.4) |
| `pui-no-decision-verb` | No rendered text asserts approved / authorized / directed / funded / scheduled (§8.4) |
| `pui-shared-rate-limit-notice` | A `429` renders `RateLimitNotice` stating the budget is shared, and pauses that query for `Retry-After` (§4.8) |
| `pui-no-unsourced-sort-label` | No ordering claim is captioned where the contract declares no `sort` (§6.1) |

**Sheet 08 (`pui-*`)**

| Test | Asserts |
|---|---|
| `pui-strength-five-bands` | `EvidenceStrengthMeter` renders five segments and the band's [25 §4.4] name |
| `pui-strength-not-a-percentage` | No percentage, ratio, or "n of m" in the meter's text or accessible name |
| `pui-strength-has-limiting-axis` | The meter never renders without `band_limiting_axis` |
| `pui-strength-unknown-is-not-s0` | An unavailable band renders a degraded state, never `S0` |
| `pui-strength-caps-rendered` | `caps_applied` renders `C-DT` / `C-TAX` with their reasons |
| `pui-statement-verbatim` | `statement` renders unmodified; truncation, ellipsis, and re-wording all fail |
| `pui-residuals-not-collapsible` | `residual_confounders[]` renders in full, outside any collapsed region, with `direction_of_bias`, `could_reverse_sign`, and `why_unaddressed` |
| `pui-definition-time-flagged` | `definition_time_integrity ∈ {fail, unknown}` renders with the band |
| `pui-gate-verdict-distinct` | Four `gate_verdict` values render distinctly; `refused` is never neutral or absent |
| `pui-census-unavailable-is-not-clean` | An unavailable census renders a degraded notice, never "no confounding" (§6.6) |
| `pui-supersession-shown` | `supersedes_hypothesis_id` renders the prior finding's state, band, note, and the claimed `novelty_basis` |
| `pui-downgrade-offers-lower-only` | The downgrade selector offers no band at or above `strength_band` |
| `pui-approve-is-not-admit` | No control issues both A8 and A9; the admit label never appears on an adjudication control |
| `pui-review-due-no-default` | The admission form requires `review_due` and suggests no value |
| `pui-claim-state-not-synthesized` | With no claim fields in the response, the list renders "claim state unknown", never "unclaimed" |
| `pui-no-withdraw-control` | No withdraw control is rendered (§6.4) |

**Sheet 09 (`pui-*`)**

| Test | Asserts |
|---|---|
| `pui-required-fragment-fails-whole-sheet` | `503 required-fragment-unavailable` renders `ProblemDetail`, never a partial sheet |
| `pui-degraded-causal-findings-not-empty` | A degraded `causal_findings` never renders "no causal findings" and never an empty citation list; the dossier's citations still render (§7.8) |
| `pui-degraded-impact-not-complete` | A degraded `impact_snapshot` renders no ratio and no `is_bounded_below: false` |
| `pui-degraded-cost-not-zero` | A degraded `cost_estimate` renders no `$0`, no bare dash, and no "detailed: pending" |
| `pui-citation-carries-structured-strength` | The structured `strength_carry` renders alongside `rendered_strength`, never instead of it; `confounders_unaddressed` renders unconditionally |
| `pui-no-local-strength` | [28 §8.2] property 2's denylist over props, computed values, and labels |
| `pui-no-rank-displayed` | Sorting is permitted; no rank number, position badge, or "top finding" label renders |
| `pui-no-strength-aggregation` | No component combines two citations' strengths into one figure |
| `pui-posture-groups-separate` | `supporting` and `contra` citations render as two labelled groups |
| `pui-agreement-rendered-as-received` | `pma_only` / `maintenance_only` / `both` render distinctly and unresolved |
| `pui-test-coverage-one-row-per-expected` | One row per expected test kind, present or absent |
| `pui-absence-statuses-distinct` | The four absence statuses render distinctly, never collapsed to "missing" |
| `pui-not-required-is-not-credit` | `absent_not_required` renders neutral, never `good`, and never as qualification credit |
| `pui-watermarks-rendered` | `read_model_watermarks` renders |
| `pui-completeness-not-aggregate-only` | `unverified_by_relation`, `unverified_by_source_kind`, `nodes_truncated_at_depth`, and `is_bounded_below` all render |
| `pui-lower-bound-stated` | `is_lower_bound` / `is_bounded_below` render adjacent to the figure, never in a tooltip |
| `pui-rollup-lower-bound-adjacent` | A `dependency_rollup` with `coverage_ratio < 1.0` renders `LowerBoundNotice` beside the total |
| `pui-gate-conditions-by-id` | `condition_results` render per condition by identifier, with `thresholds_in_force` and `remedy` |
| `pui-placeholder-factors-marked` | A `PLACEHOLDER` `cost_model_version` or `gate_policy_version` renders its marker |
| `pui-two-stage-states-real` | The bar renders real stage state, not the wireframe's fixed chips |
| `pui-detailed-pending-disambiguated` | The three "pending" causes render distinctly |
| `pui-interval-requires-basis` | `low_usd`/`high_usd` render only with `interval_basis` |
| `pui-limitations-not-collapsible` | `recommendation_limitations[]` and `recommendation_evidence_gaps[]` render in full, outside any collapsed region |
| `pui-published-is-not-approved` | `case_status = 'published'` renders the decision-package statement and never "approved" |
| `pui-non-program-flag-critical` | `non_program_evidence_only` renders in the `critical` tone, above the controls, outside any collapsed region |
| `pui-dual-control-from-field` | `DualControlBadge` renders from `requires_dual_control`, never from a client derivation of `blast_radius` |
| `pui-ambiguous-proposal-blocks-action` | Two matching proposals for one case render an ambiguity state and no adjudication control (§7.1) |
| `pui-committed-fields-not-payload` | The panel renders the case's committed recommendation, and any payload divergence is labelled as the agent's derivation (§7.7) |

**Accessibility** — every test in [50 §8.1]–[50 §8.6] plus §9.2's five, plus `a11y-axe-clean` across both surfaces' routes and `packages/ui/src/evidence/`.


---

## 11. Explicit DO-NOT list

[09 §9]'s thirty-two items apply in full. [50 §11]'s forty-four apply in full. These are additional and specific to a Domino-hosted practitioner surface. Each carries the citation that makes it a defect rather than a preference, so a reviewer may cite the number and stop reading.

### 11.1 The container and the host

1. **Do not add a second process, and do not add nginx.** [02 §4.1]: *"One image, one launch file, one pod"*, and the multi-process workaround is recorded as *"fairly gross"* and *"not super elegant."* One FastAPI process serves the bundle and proxies. *(§2.1, §2.5)*
2. **Do not cache a domain response in the host, at any layer, for any duration.** [02 §4.1]: *"Domino does not serialize or isolate access to shared resources across App users."* One process's cache is a shared cache across viewers of different clearances, and a cache hit serves one viewer's authorized view to another. *(§2.3 rule 1; 30 §3.5; 50 §5.1)*
3. **Do not hold per-viewer state in the host, and do not build a session.** Pods restart and are evicted without notice; *"[a]utoscaled applications share temporary storage."* *(§2.3 rule 2, §2.6; 02 §4.1)*
4. **Do not write anything durable.** [02 §4.1]: *"[f]ile changes inside an App container are not saved."* *(§2.3 rule 3)*
5. **Do not install anything at container start.** [02 §4.1]'s own engineering called it categorically incompatible with air gap. *(**D26**; 09 §9.5 item 25; §2.4)*
6. **Do not deploy this app into Domino's namespaces, and do not write a Helm chart for it.** Domino deploys it. *(09 §9.5 item 28; §0.1, §2.4)*
7. **Do not assume a Domino capability [02] rules out** — Extensions outside Domino Cloud, server-side rendering, multi-container, a WebSocket surface, or anonymous access. Each has a stated fallback. *(09 §9.5 item 27; §2.5, §2.7)*
8. **Do not initiate a request expected to exceed the 300 s nginx ceiling**, and do not tune it: [02 §4.1] records *"[n]o per-application override."* *(§2.7)*
9. **Do not open a WebSocket, an `EventSource`, or a long-poll.** *(50 §5.4's five reasons, of which reason 4 is this app; 50 §11.3 item 16)*
10. **Do not write an audit record from this app.** The gateway writes it, and a second unreconciled record from a component whose identity binding is the open question is worse than none. *(§2.3 rule 4; 30 §5.8; 09 §4.4.2)*
11. **Do not subscribe to a topic, own a database, or call a sub-application directly.** Every outbound call goes to the gateway. *(03 principle 2; 09 §9.5 item 30; §2.3 rule 5)*

### 11.2 Base path, assets, and the iframe

12. **Do not read `DOMINO_RUN_HOST_PATH` from the SPA, and do not bake a base path at build time.** The SPA has no access to the environment and one meta tag is the only source. *(50 §6.1; §3.1, §3.2)*
13. **Do not ship `base: "./"` without `<base href>`.** Every nested deep link loads a blank page, and deep linking is what makes the iframeless view available. *(50 §6.2; 02 §4.1; §3.3)*
14. **Do not write a relative `href`, `src`, or `action` literal anywhere.** With `<base href>` set, a relative URL resolves against the prefix rather than the route. *(§3.3)*
15. **Do not move Vite's `assetsDir` back to `assets`.** [02 §4.1]'s February 2026 proxy defect is unresolved and `assetsDir: "static"` is one of the two mitigations. *(50 §6.2)*
16. **Do not touch `window.top`, `window.parent.location`, or navigate the top-level document.** *(50 §6.5; §3.5)*
17. **Do not accept a `postMessage` without an origin allowlist check, and never listen with `"*"`.** *(§3.5)*
18. **Do not let a storage failure throw.** Third-party-iframe storage is partitioned; a `SecurityError` on read is an expected condition. *(50 §2.6 rule 3; §3.5)*
19. **Do not load an external subresource of any kind** — font, script, stylesheet, image, or fetch. *(01 §12; 09 §9.5 item 26; 02 §4.1's CSP allowlist; 50 §2.3)*
20. **Do not inject an identity, a token, a role, or a classification label into the served HTML.** Only the base path and its `<base href>`. *(§3.1 rule 3; 31 §13 item 15)*

### 11.3 Credentials and identity

21. **Do not put a token in the browser.** Neither app does, and the reason is [50 §6.3]'s: *"a token in a browser is a token in every browser extension the browser has installed."* *(31 §4.1; 50 §11.4 item 28; §4.6 alternative (c))*
22. **Do not accept Domino's basic username-header tier.** A header the browser can set makes the identity binding worthless. Only the signed-JWT tier. *(02 §4.1; §4.3)*
23. **Do not accept a claimed subject from the request body, a query parameter, or a client-settable header.** *(31 §13 item 15; 50 §11.4 item 29; §4.3)*
24. **Do not map a Domino identity to a `fathom` `sub` in this app.** The broker's linked record is the mapping and it lives in Keycloak. A second mapping is a second identity authority. *(31 §2.2; §4.3)*
25. **Do not synthesize an `If-Match` or regenerate an `ETag` in the host.** [30 §4.6]'s argument, one hop out: it *"would defeat the entire concurrency mechanism while appearing to satisfy it."* *(§4.4)*
26. **Do not add a header a sub-application might authorize on.** *(30 §8.4; §4.4, §4.5)*
27. **Do not re-wrap an RFC 9457 problem body.** *(30 §8.4; §4.5)*
28. **Do not refresh a credential on wall-clock arithmetic.** *(**D29**; 09 §9.2 item 7; §4.2)*
29. **Do not accept an unsafe method without an `Origin` check.** The host authenticates on a server-injected assertion, so a cross-site `POST` would otherwise arrive carrying it. *(§4.5)*
30. ~~**Do not reason past [31 §5.8]'s status.** It is an amendment ask.~~ **[AMENDMENT — superseded.]** [31 §5.8] is now settled (§4.1), the adjudication path is live, and §4.7's level-scoping notice and workload-envelope narrowing were removed along with the interim they belonged to — there is no longer a status to reason past. *(31 §2.2's warning; 31 §5.8; 50 §13 correction 10; §4.7)*
31. **Do not retry a `429` in the host, and do not queue.** The bucket is shared across every viewer; a host retry multiplies the load it is bounding. *(30 §6.2, §6.5; §4.8)*
32. **Do not add a catch-all proxy route.** An operation nobody reviewed must be unreachable through the app's credential. *(30 §8.2 DECISION G-3; §5.3)*
33. ~~**Do not render a sign-out control, an identity block, or an authority marking.** No gateway session exists here and the viewer's roles are unobtainable.~~ **[AMENDMENT — the identity-block half is superseded, same status change as rule 30.]** `GET /api/v1/gateway/session` now returns a real identity block to this app (§4.7), so the viewer's name, organization, and authority chips render exactly as in `apps/web`. The sign-out half stands unchanged: no gateway session exists for this app to end, so no sign-out control renders. *(§4.7)*
34. **Do not disable or dim a control on an authority guess.** Every refusal is the server's, with `reasons`. *(31 §8; 50 §9.4; §4.7, §6.7)*

### 11.4 The two sheets

35. **Do not render an evidence-strength band as a percentage, a ratio, a confidence, an "n of m", or a three-segment bar.** [25 §4.1]: *"[n]othing sums, nothing averages, and nothing trades off."* Five bands, plus the limiting axis. *(§6.3)*
36. **Do not render a strength band without `band_limiting_axis`.** It is *"the actionable field"* and the answer to *"why is this only S2?"* *(25 §2.3, §4; §6.3)*
37. **Do not render an unavailable band as `S0`.** `S0` asserts the evidence is contradicted or the gate refused; unavailability asserts nothing about the evidence. *(25 §4.4; 30 §3.4; §6.3)*
38. **Do not re-word, shorten, truncate, or tooltip the generated `statement`.** *(25 §4.5; 50 §11.4 item 35; §6.3)*
39. **Do not omit, collapse, or tooltip `residual_confounders[]` / `confounders_unaddressed`.** [28 §8.2]: the renderer *"has no code path that omits `confounders_unaddressed`."* *(§6.3, §7.3)*
40. **Do not render an unavailable treatment census as "no confounding."** Invariant I3 makes the census mandatory, so an absent one is a fetch failure, and the benign default is exactly *"how a confounded population passes a gate silently."* *(25 §2.1, §2.3; §6.6)*
41. **Do not collapse publishing a finding into admitting a causal feature.** Two acts, two operations, two blast radii. *(25 §5.1 steps 7–8, DO-NOT-6; §6.5)*
42. **Do not offer a band at or above the current one in a downgrade control, and do not offer any upgrade path.** *(25 DO-NOT-8, §2.3's `downgrade_lowers`; §6.4)*
43. **Do not default `review_due`.** [25 §5.4]'s interval is **OD-6**, unresolved. *(09 §9.5 item 31; §6.5)*
44. **Do not render "unclaimed" for a hypothesis.** No claim field exists; unknown is the honest rendering. *(§6.1, §13 correction 12)*
45. **Do not author, derive, persist, or display a local strength — score, rank, threshold, summary, prose-in-place-of-the-object, or a combination across citations.** [28 §8.2]'s denylist runs over this app's props, computed values, and labels. *(§7.3)*
46. **Do not aggregate across citations.** [28 §8.2] property 4: *"[t]hree weak hypotheses pointing the same way do not become one moderate hypothesis in a dossier."* *(§7.3)*
47. **Do not resolve a `pma_only` / `maintenance_only` disagreement, and do not render it as resolved.** *(28 §8.4, DA-15; 12 §9.2; §7.3)*
48. **Do not collapse the four absence statuses, and do not credit `absent_not_required`.** *"**Not required** is a statement about the qualification regime, not evidence about the component."* *(28 §3.2.2, §3.2.3, DA-5; §7.3)*
49. **Do not report dependency completeness as an aggregate ratio alone, and do not omit it.** *(28 §3.6, DA-7; §7.4)*
50. **Do not render a `dependency_rollup` total without its lower-bound qualification.** *"[T]his number can only go up."* *(28 §3.7, DA-7; §7.5)*
51. **Do not render a cost interval without `interval_basis`.** *"[A] ±30% band with no basis is a decoration that reads as rigour."* *(28 §3.7; §7.5)*
52. **Do not present the costing gate as an evidentiary or merit judgment.** It decides where to spend estimation effort. *(28 §5.3's G5 note, DA-10; §7.5)*
53. **Do not omit `recommendation_limitations[]` or `recommendation_evidence_gaps[]`, and do not collapse them.** They are what makes the package defensible. *(28 §1.2 E3, §3.6; §7.6)*
54. **Do not render `published` as approved, authorized, directed, funded, or scheduled — anywhere, in any label.** [28 §6.5] names the practitioner UI as one of the three places the distinction must be stated. *(28 DA-1, §1.2 E1; §7.6, §8.4)*
55. **Do not use a causal verb in any component name, prop name, label, ARIA label, or fixture.** The permitted vocabulary is one word wide: *hypothesis*. *(**D23**; 09 §9.3 item 20; 25 DO-NOT-3, §4.5; 28 DA-3; §8.4)*
56. **Do not put `role="img"` on an SVG and then make something inside it interactive.** The invariant is asserted, not the current state. *(50 §8.5, item 40; §7.4, §9.2)*
57. **Do not ship the dependency graph without its equivalent table.** *(50 §8.5, item 42; §7.4)*
58. **Do not adjudicate on evidence that could not be read.** [30 §4.6]: it *"is precisely D16's defect wearing a friendlier face."* *(§5.5, §7.7, §7.8)*
59. **Do not derive `requires_dual_control` client-side from `blast_radius`.** Two documents already disagreed about that rule once. *(03 §7.2.1 as amended; 31 §6.4 as amended; 28 §16 correction 3; §7.7)*
60. **Do not offer an adjudication control when a case resolves to more than one open proposal.** *(**D16**; §7.1)*
61. **Do not add a control the wireframes do not draw and this document does not specify.** `CaseSelector` (§5.1 rule 4) and the two additions of §7.6 and §7.7 are argued individually and are the complete set; anything further is a change to this document. *(50 §11.2 item 12)*
62. **Do not suppress the classification banner or footer because the app is embedded.** Domino's chrome is not the program's chrome. *(03 §7.3; 50 §7.2 rule 4; §8.1)*

---

## 12. Definition of Done

**The shared Definition of Done in [09 §8] applies in full and nothing is removed from it.** Following its instruction that each document *"reproduces this checklist for its own component, adds component-specific items, and **removes nothing**"*, and following [42 §19.1]'s method for a component that publishes no OpenAPI document, owns no aggregate, and consumes no topic, §12.1 dispositions every subsection explicitly. [50 §12] already did this for a browser application; this section differs from it in exactly one way, and the difference is the host process. Copy §12.2 into `apps/practitioner/README.md` and tick it there.

### 12.1 [09 §8] reconciliation

| [09 §8] subsection | Applies | Note |
|---|---|---|
| **§8.1 Contract and specification** | **Items 10, 12, 13, 14, 16 only, and as a *consumer*, not a producer** | Neither the SPA nor the host publishes an `x-substitution: required` surface, so items 1–9, 11, 15, 17, 18 have no subject. **Item 10** (RFC 9457) binds: the host has five problem types of its own (§4.5) and never re-wraps an upstream's. **Item 12** (`ETag`/`If-Match`) binds as a consumer: §4.4 and §5.5. **Item 13** (`X-Correlation-Id` accepted, minted when absent, echoed, propagated) binds on the host **and** on the SPA, which originates one per user action [50 §12.1]. **Item 14** (`X-Classification` on every response) binds as a consumer: §8.3. **Item 16** (RFC 3339 UTC, `DTZ` clean) binds on display and on the host. **Item 11** (`Idempotency-Key` required on state-changing) binds in the direction of *sending*: §5.5. Authorization enforced in this service (item 15) is **not applicable, and asserting otherwise would be the defect** — a browser and its proxy are not enforcement points *(§5.1 rule 3, §11.3 item 34)* |
| **§8.2 Events** | **None** | Neither component publishes or consumes an event. [09 §9.2 item 15] / **C19** forbids a non-service topic consumer and the prohibition binds a browser and a Domino App with equal force. **Asserted rather than assumed** — `host-no-event-client` asserts no broker client library is importable from `fathom_practitioner_host` |
| **§8.3 Outbox, inbox, read models** | **Items 6 and 8 only** | Item 6: **monotonic clocks for every duration, timeout, backoff, and refresh** — `performance.now()` in the SPA [50 §5.4] and `time.monotonic()` in the host (§4.2). Item 8: a **staleness bound rendered rather than hidden** — `queue_freshness.stale` on Sheet 09 [30 §4.5, §4.7]. Items 1–5, 7, 9 concern an outbox, an inbox, and event-fed read models; there are none, and §2.3 rule 1 forbids the nearest thing to one |
| **§8.4 Data and storage** | **Items 4 and 5 only** | One logical database, Alembic, and the `migrations` readiness check are **not applicable** — no store. Item 4 (**provenance for every derived value**): binding, and substantively so — every operator-visible figure on both sheets links to its basis (`treatment_census_ref`, `impact_snapshot_id`, `inputs_digest`, `read_model_watermarks`, `strength_carry_digest`, `gate_decision_id`, `cost_model_version`), per [03 §15] obligation 9 and [04 §5]'s decomposability requirement. Item 5 (**classification labels with `inherited_from`**): binding, §8.3. **Purge:** neither component is a store; the only persisted client state is `runtime/prefs.ts`'s best-effort theme key, which is stated in the README so *"the app has a store"* is answered rather than assumed |
| **§8.5 Conformance and tests** | **Item 7 fully; §10 is the equivalent of the rest** | Items 1–6 and 8 concern a service's own conformance suite, contract tests over its published operations, event and fault-injection tests, consumer-driven contributions, and manifest tests. **There is no slug and no conformance suite for a UI** [50 §12.1]. Item 7 (**a deterministic synthetic reference dataset**) is **adopted and is load-bearing**: §10.1's two fixture requirements, drawn from `packages/contracts/conformance/{failure-intel,design-advisory}/`. §10.2's names are contractual in [50 §10.2]'s sense |
| **§8.6 Deployment and boundary** | **Mixed — §2.4's table is the disposition** | `check_event_catalog.py`, `helm lint`, `helm template`, `helm unittest`, NetworkPolicy assertions, and the Argo CD Application are **not applicable: Domino deploys this app** and [09 §9.5 item 28] forbids us deploying into its namespaces. **Applies:** multi-stage Dockerfile, non-root UID 65532, digest pins, no install at container start, `/healthz` `/readyz` `/metrics` served, `.env.example` complete with no secret value, and **structured JSON logging with `correlation_id` on every line** — which binds on the host and is where [50 §12.1] was too narrow (§0.1, §13 correction 1). **Cannot be asserted:** `readOnlyRootFilesystem`, `capabilities: drop: [ALL]`, and the pod `securityContext`, all of which Domino sets (§2.4, §13 correction 8). **No direct database access** holds vacuously and is asserted anyway |
| **§8.7 Documentation and governance** | **All four items** | Every `[ESTABLISHED HERE]` here is a convention two surfaces share; varying one breaks the sibling. Every `[OPEN]` the app resolved locally is in the README, and §4.7's interim is the substantive one |

### 12.2 Component-specific items

**Container and host (§2)**

- [ ] One image; two Domino App registrations; two launch files, each one `exec` with no package manager *(§2.1, §2.4; `host-launchfile-no-install`)*
- [ ] `[VERIFY]` discharged on: multiple launch files per Domino project, the App listen-port variable, and digest preservation through Domino's environment build; each recorded in the pull request *(§2.1, §2.4)*
- [ ] No second process, no nginx, no SSR, no Extension assumption *(§2.5; §11.1 items 1, 7)*
- [ ] `host-no-response-cache`, `host-no-viewer-state`, `host-no-event-client` green *(§2.3)*
- [ ] `host-no-settings-defaults`, `host-deadline-below-ceiling`, `host-token-refresh-monotonic`, `host-no-credential-in-output` green *(§2.7, §4.2)*
- [ ] `host-logs-are-json-with-correlation` green; no token, credential, or body in any log line *(§2.3; 31 §13 item 5)*
- [ ] `.env.example` complete, reconciled with `Settings`, no real value *(§4.2; 09 §4.5)*
- [ ] The README records that `readOnlyRootFilesystem` and the `securityContext` are Domino's, and that the image is compatible with both *(§2.4)*

**Base path and assets (§3)**

- [ ] `vite.config.ts` sets `base: "./"` and `build.assetsDir: "static"`, and carries the [02 §4.1] citation verbatim *(50 §6.1, §6.2; 50 §12.2)*
- [ ] `<base href>` **and** `<meta name="fathom-base-path">` injected, agreeing, escaped *(§3.1, §3.3)*
- [ ] `host-base-path-validated`, `host-head-injection-escapes`, `host-base-href-present`, `host-catchall-returns-index` green
- [ ] `ui-practitioner-basename-from-runtime`, `pui-api-prefix-derived`, `pui-no-relative-url-literal` green
- [ ] A deep link to a nested route loads correctly after a hard refresh, in both surfaces *(§3.3, §3.4)*
- [ ] `pui-no-window-top`, `pui-postmessage-origin-checked`, `pui-prefs-never-throws`, `pui-no-external-subresource` green *(§3.5)*

**Credentials and identity (§4)**

- [ ] Per-surface confidential client; `aud` contains `gateway`; refresh monotonic *(§4.2)*
- [ ] Only the Domino enhanced-JWT identity tier accepted; `host-rejects-username-header-tier`, `host-verifies-identity-assertion`, `host-no-claimed-subject` green *(§4.3)*
- [ ] `host-sends-one-credential`, `host-never-sends-caller-authorization`, `host-never-synthesizes-if-match`, `host-adds-only-declared-headers`, `host-passthrough-byte-identical`, `host-never-rewraps-problem`, `host-origin-required-on-unsafe` green *(§4.4, §4.5)*
- [ ] **[31 §5.8] has landed as the token-exchange mechanism, and the write path is authorized rather than blocked.** No narrowed workload envelope, no interim level-scoping notice (removed, not merely disabled); `pui-no-signout-control` green; [50 §13] correction 10, [50 §14] UI-OQ-4, and §14 P-OQ-3 all named as closed *(§4.7)*
- [ ] §4.6's three alternatives recorded, so a revision is a one-module change and not a redesign *(§4.6)*
- [ ] `pui-shared-rate-limit-notice` green *(§4.8)*

**Routing and data (§5)**

- [ ] Two route trees exactly as §5.1; every rendered state has a URL; `pui-no-role-gated-route` green
- [ ] `api/` mirrors [50 §5.2]'s five-file shape; every read through `openapi-fetch` over generated types; `ui-no-hand-written-wire-type`, `ui-zod-validated` green
- [ ] The allowlist matches §5.3 exactly; `host-allowlist-enforced`, `host-allowlist-no-drift`, `pui-allowlist-matches-keys` green
- [ ] `freshness.ts` carries §5.4's table as data, each row citing its derivation from [50 §5.4] and [50 §6.4]
- [ ] `ui-no-wall-clock-timers`, `ui-no-streaming-transport`, `ui-retry-after-pauses-poll` green *(50 §10.2)*
- [ ] `pui-adjudicate-sends-if-match`, `ui-idempotency-key-stable-across-retries`, `ui-412-requires-reconfirm`, `pui-confirm-enumerates-evidence`, `pui-note-required` green
- [ ] Loading, empty, and unknown are three components and never conflated *(50 §5.5; §5.6)*

**Sheet 08 (§6)**

- [ ] Every rendered field traces to §6.1's table; the six added columns present; the claim-state column renders "unknown" and never "unclaimed"
- [ ] `EvidenceStrengthMeter` and `StrengthStatement` in `packages/ui/src/evidence/`; **not duplicated in the app** *(50 §3.4 rule 1, §11.2 item 13)*
- [ ] `pui-strength-five-bands`, `pui-strength-not-a-percentage`, `pui-strength-has-limiting-axis`, `pui-strength-unknown-is-not-s0`, `pui-strength-caps-rendered`, `pui-statement-verbatim`, `pui-residuals-not-collapsible`, `pui-definition-time-flagged`, `pui-gate-verdict-distinct`, `pui-census-unavailable-is-not-clean`, `pui-supersession-shown` green
- [ ] `pui-approve-is-not-admit`, `pui-downgrade-offers-lower-only`, `pui-review-due-no-default`, `pui-claim-state-not-synthesized`, `pui-no-withdraw-control` green
- [ ] The admission control renders a stated-reason refusal until [25 §8.1] specifies the request body *(§6.5; §13 correction 16)*
- [ ] §6.7's persona finding recorded in the README by name: [25 OD-5], [50 §13] correction 17, §13 correction 17

**Sheet 09 (§7)**

- [ ] Built on B1's composed view; all six envelope members handled; all six `FragmentOutcome` values handled explicitly *(30 §3.4; 50 §5.3)*
- [ ] `pui-required-fragment-fails-whole-sheet`, `pui-degraded-causal-findings-not-empty`, `pui-degraded-impact-not-complete`, `pui-degraded-cost-not-zero`, `ui-degraded-view-renders-notice`, `ui-classification-fault-is-not-degraded` green *(§7.8)*
- [ ] `pui-citation-carries-structured-strength`, `pui-no-local-strength`, `pui-no-rank-displayed`, `pui-no-strength-aggregation`, `pui-posture-groups-separate`, `pui-agreement-rendered-as-received` green *(§7.3)*
- [ ] `pui-test-coverage-one-row-per-expected`, `pui-absence-statuses-distinct`, `pui-not-required-is-not-credit`, `pui-watermarks-rendered` green *(§7.3)*
- [ ] `pui-completeness-not-aggregate-only`, `pui-lower-bound-stated`, `a11y-depgraph-*` (five), `ui-font-size-floor` green *(§7.4, §9.2)*
- [ ] `pui-gate-conditions-by-id`, `pui-placeholder-factors-marked`, `pui-two-stage-states-real`, `pui-detailed-pending-disambiguated`, `pui-interval-requires-basis`, `pui-rollup-lower-bound-adjacent` green *(§7.5)*
- [ ] `RecommendationBox` present and required; `pui-limitations-not-collapsible`, `pui-published-is-not-approved` green *(§7.6)*
- [ ] `pui-non-program-flag-critical`, `pui-dual-control-from-field`, `pui-ambiguous-proposal-blocks-action`, `pui-committed-fields-not-payload`, `ui-queue-freshness-rendered`, `ui-non-program-evidence-not-collapsible`, `ui-approximate-time`, `ui-learned-sort-label` green *(§7.7)*

**Classification, language, accessibility (§8, §9)**

- [ ] `pui-classification-on-every-route`, `ui-classification-banner-is-data-driven`, `ui-classification-footer-present`, `ui-no-retired-markings`, `pui-placeholder-code-marked` green
- [ ] `pui-no-causal-verb`, `pui-no-decision-verb`, `ui-fs-term-001`, `ui-no-tier-branch`, `ui-factors-not-causal` green
- [ ] `AdvisoryBanner` and `ContributorDisclosure` are **absent, and §8.2 records why** — an absence with a reason, not an omission
- [ ] Every test named in [50 §8.1]–[50 §8.6] green; `a11y-axe-clean` at zero `serious`/`critical` on every route of both surfaces and every `packages/ui/src/evidence/` component
- [ ] [50 §8.4]'s contrast table green in **both** themes *(§9.1)*
- [ ] `@media print` retains the banner, footer, limitations, gaps, lower-bound notice, completeness object, and the decision-package statement *(§8.1 item 4)*

**Testing and fixtures (§10)**

- [ ] Tests run against the **committed OpenAPI documents**, not hand-written handlers *(§10.1)*
- [ ] §10.1's two fixture requirements satisfied from the conformance datasets, or the gap recorded against [25 §10.1] and [28 §16] correction 5 *(§13 correction 24)*
- [ ] Every test in §10.2 exists and is green, and none has been renamed *(50 §10.2's contractual-names rule)*

**Governance**

- [ ] Corrections **1–24** of §13 filed against their documents with an owner. **Corrections 2, 3, 5, 6, 7, 10, 12, 14, 15, 16, 17, 18, 21, and 22 block a complete `apps/practitioner`** and are recorded as blocking
- [ ] Open questions **P-OQ-1 … P-OQ-8** recorded in the README as local resolutions where the app had to proceed *(§14; 09 §8.7)*
- [ ] Reconciliation items **R-52-1 … R-52-4** raised with [51], and §0.3's three landed-decision rows confirmed against [51]'s final text *(§0.3, §14)*
- [ ] Every deviation from this document or from [50] carries an ADR under `docs/adr/` *(09 §8.7)*
- [ ] No `[ESTABLISHED HERE]` convention in [50] has been silently varied here *(09 §8.7; 50 §12.2)*

---

## 13. Corrections to source documents

Found while reconciling, following [09 §11] and [26 §13]'s convention: each is a **defect or gap in the cited document or in the approved wireframe**, not a decision of this one. **None is applied upstream here.** The **thirteen** marked blocking prevent a complete `apps/practitioner`: **2, 5, 6, 7, 10, 12, 14, 15, 16, 17, 18, 21, and 22**. Correction 3 is **resolved, not by the fix it originally asked for** — see its row below.

| # | Document | Defect | Correction | Status |
|---|---|---|---|---|
| **1** | **50 §6.2, §6.3, §12.1** | Three omissions, all discovered by implementing §6. (a) **`base: "./"` alone breaks every nested deep link**: a relative asset URL resolves against the document's directory, and the catch-all serves `index.html` at `/prefix/hypotheses/:id`, so the browser requests `/prefix/hypotheses/static/…`. [02 §4.1] makes deep linking the condition for the iframeless view, so this is not cosmetic. (b) **§6.3's *"both apps hold a cookie and no token"* symmetry is not load-bearing for this app**: in a third-party iframe cookies are partitioned or blocked, so Domino's session cookie may never reach the host, and identity must arrive on a server-injected assertion instead. (c) **§12.1 disposes of structured JSON logging as *"not applicable: a browser writes no log line"*** — true of the SPA, false of the co-resident host, which is the first UI component in the corpus that logs | (a) Add `<base href="<prefix>/">` to §6.1's injected head alongside the meta tag, with the nested-path reasoning. (b) Restate §6.3's closing symmetry as *"neither app holds a token"*, and record that `apps/practitioner` must not depend on a cookie arriving. (c) Split §12.1's logging row: not applicable to the SPA, **binding on the host** | **Not applied; flagged.** (a) implemented in §3.3, (b) in §4.3, (c) in §0.1 and §12.1 |
| **2** | **09 §3.1, §3.2** | `apps/practitioner/` in the tree is a JS/TS node, and [09 §3.2]'s row reads *"Domino-hosted practitioner surfaces \| This document §2.6 + 02 §4.1 constraints."* This document adds a **Python package** at `apps/practitioner/host/` (the co-resident FastAPI process [02 §4.1]'s single-container rule requires) and the governance row names no document for the surfaces' content | Annotate the `apps/practitioner/` node with the `host/` subtree and its Python package name; change [09 §3.2]'s `Governed by` cell to *"This document §2.6 + 02 §4.1; content 50 and 52"*; confirm the root `pyproject.toml`'s shared ruff/mypy/pytest configuration reaches `apps/*/host/` | **Blocking** — CI does not lint or type-check the host until the config reaches it. Not applied; flagged |
| **3** | **30 §8.1.2** | The amendment declared `GET /api/v1/gateway/session` reading *"the session cookie's server-side session store"* and `POST /api/v1/gateway/session/logout`. **Neither was usable by `apps/practitioner`**, which holds no gateway session — so this app could not learn the viewer's `display_name`, `unit_uic`, `billet`, or `authority_classes` by any route. [50 §13] correction 7 was therefore resolved for `apps/web` and **open for this app** | **[RESOLVED — not by the caller-authority-borne variant originally asked for.]** `31 §5.8` was corrected to a token-exchange operation instead (`POST /api/v1/auth/practitioner-exchange`, §4.4), which gives this app an ordinary delegated `fathom` token — so `GET /api/v1/gateway/session` (`30 §8.1.2`) now works for `apps/practitioner` exactly as it does for `apps/web`, with no second code path at the gateway. The originally-proposed variant is superseded, not built | **Resolved.** Identity block, sign-out, and authority-aware presentation are all available — §4.7 |
| **4** | **30 §3.2** | The fragment registry now declares `redesign_case_detail` for Sheet 09, and declares **no composed view for a hypothesis**. Sheet 08 has the same shape of problem [42 §18] item 13 raised for Sheet 09 — an adjudicator opening a hypothesis needs its evidence, its treatment census, its failure-mode label, and its prior examination, which is four calls the client sequences itself. `installed_item_detail`'s `failure_modes` fragment is not it: it carries failure modes, not hypotheses | Either add a `hypothesis_detail` `ViewSpec` at `/views/hypothesis/{hypothesis_id}` with fragments `hypothesis` (failure-intel, required), `evidence` (failure-intel, required), `treatment_census` (failure-intel, optional), `failure_mode` (reference-data, optional), `prior_examinations` (failure-intel, optional, phase 1) — **or** state that Sheet 08 composes client-side and record the asymmetry deliberately. **The budget would be unsourced either way**, as `redesign_case_detail`'s already is | Not applied; flagged. **§5.3 and §6 build the client-side composition**, which works and is four round trips inside a shared rate-limit bucket (§4.8) |
| **5** | **09 §2.4, §4.5, §4.4.2** | **The workload client secret for a Domino-hosted app cannot use the program's External Secrets path**, because [09 §9.5 item 28] forbids us deploying the pod — so the credential is injected by **Domino's** project/environment mechanism, outside the program's secret custody, rotation runbook, and NetworkPolicy. [09 §4.4.2] also justifies the `domino-compute → gateway` edge solely by *"scoring Jobs write predictions through PdM's bulk ingest API"*, while [31 §5.8] and [30 §6.2] both now route a practitioner App over it. And the gateway's ingress allow-list is rendered from `fathom.navy/service` pod labels [09 §4.4.2], which a Domino-deployed App does not carry | (a) State the credential-custody exception explicitly, with the rotation owner, since it is an accreditation-relevant divergence rather than an implementation detail. (b) Widen the `domino-compute → gateway` row's reason to include practitioner Apps, matching [30 §6.2]'s amended bucket table. (c) Specify the gateway's ingress rule for a namespace-selected, unlabelled peer | **Blocking** deployment and the accreditation narrative. Not applied; flagged |
| **6** | **30 §8.1** | The pass-through surface covers *"the nine sub-applications plus `tool-server`, `knowledge-retrieval`, `notification`, `reference-data`"* — **not `auth`**. So [31 §8]'s `POST /authority-checks` (*"so the gateway can render a queue without enabled-looking rows nobody may act on"*) and `GET /principals/{sub}` are **unreachable from any browser client**, `apps/web` included. [50 §9.4] relies on the first to dim a control on advice | Either add `auth`'s two advisory operations to the pass-through set, or declare gateway-owned equivalents alongside [30 §8.1.2]'s session operations. **[AMENDMENT]** `GET /principals/{sub}` needed a `sub` a browser could not obtain without correction 3 — correction 3 is now resolved (§4.4, §4.7), so the `sub` is obtainable for both apps; this correction's own gap (the pass-through surface excluding `auth` entirely) is independent and remains open | **Blocking** any authority-aware presentation in either app. Interim in §4.7: no dimming, server refusals only. Not applied; flagged — and it is [51]'s problem as much as this document's |
| **7** | **30 §3.2** | `redesign_case_detail`'s fragments are `redesign_case`, `dossier`, `impact_snapshot`, `cost_estimate`, `causal_findings`. **No gate-decision fragment** — yet `WF #s9`'s cost box draws the gate, and [28 §5.5]'s `failed_conditions`/`remedy` are the actionable part of a gate failure | Add a `gate_decision` fragment (design-advisory, optional, phase 0) resolving the live `gate_decision` for the case's candidate | **Blocking** the cost box's gate region as a single-call sheet. Interim: B6 as a second call (§5.3, §7.5). Not applied; flagged |
| **8** | **09 §8.6** | Three items — `readOnlyRootFilesystem: true`, `capabilities: drop: [ALL]`, and the pod `securityContext` — are stated as unconditional obligations, but **a component deployed by a third-party platform cannot assert them**, and [09 §9.5 item 28] forbids us deploying it. The checklist has no disposition for that case | Add the disposition rule: where a component's pod spec is written by a platform the program does not control, the image records *compatibility* with the requirement and the README states who sets it | Not applied; flagged. §2.4 states the compatibility claim |
| **9** | **WF sheet 09** | The sheet draws no entry point, yet it **is its own Domino App reached by its own URL** [02 §4.1], so `/` must render something. As drawn, an engineer arriving at the App's root sees nothing | Draw an entry list — open `redesign_case` proposals — or state that the App is deep-link-only, in which case the launch path from `apps/web`'s sheet 10 becomes mandatory rather than convenient | Interim implemented in §5.1 rule 4 using drawn components only; flagged |
| **10** | **42 §13.3 vs WF sheet 09** | [42 §13.3] states that `apps/practitioner` *"renders the `QualificationReport`, the `CaseDraftPackage` with `suggested_stance` marked as suggested, the derived gaps and limitations in full, and the divergence between the agent's derived lists and the case's committed fields"* and that *"[i]t is where a human commits `POST /redesign-cases/{id}/assemble`."* **`WF #s9` draws none of that** — no stance selector, no limitations editor, no estimate control, no qualification report. A drafting surface and a review surface are two sheets, and one is drawn | Either draw the drafting surface as a further sheet, or correct [42 §13.3] to describe review only and assign the drafting act elsewhere. This document builds the **review** surface, because that is what is drawn | **Blocking** the `assemble` step's user interface. Not applied; flagged. §5.3 excludes the three drafting operations with this reason |
| **11** | **WF sheet 08 / 25 §5.1** | [25 §5.1] step 1 puts a discovery-run request with *"[a] reliability engineer, or a scheduled Flow"*, and [25 §7.3] makes `POST /hypotheses/prior-examination-check` *"the operation a reliability engineer … calls **before** requesting a discovery run."* **No sheet draws either surface.** The engineer's workflow begins one step before sheet 08 and that step has no interface | Draw a run-request surface, or state that runs are Flow-triggered only in the demonstration | Not applied; flagged. §5.3 excludes discovery management; §6.2's `SupersessionNotice` uses the prior-examination check only in the adjudication context, where [25 §7.2] requires it |
| **12** | **25 §2.9, §8.1** | [25 §5.2] requires a claim lease and returns `412` without one, but **the `CausalHypothesis` wire model carries no `claimed_by`/`claimed_until`** and [25 §8.1] declares no claim filter. **A second adjudicator cannot see that a hypothesis is already claimed** — the eventually-consistent double-adjudication condition [03 §7.2] rule 3 exists to prevent, made invisible. [30 §4.5] carries `claimed_by`, `claimed_until`, and a `claimed=any\|none\|me\|other` filter for proposals; hypotheses have no equivalent | Add `claimed_by` and `claimed_until` to the wire model and a `claimed=` filter to `GET /hypotheses`, mirroring [30 §4.5] | **Blocking** any honest claim-state rendering. Interim in §6.1: an explicit *"claim state unknown"* marker, never *"unclaimed"*. Not applied; flagged |
| **13** | **WF sheet 08** | The evidence-strength bar draws **three** segments (two filled). [25 §4] defines **five** bands, and two-of-three reads as a fraction — which [25 §4.1] forbids outright: *"[i]t is not a confidence, a probability, or a score."* | Redraw as five segments with the band identifier and its [25 §4.4] plain-English name adjacent, plus `band_limiting_axis` | Applied in §6.3 as a component specification; the wireframe needs the edit |
| **14** | **25 §5.2, §7.1** | `adjudication_record.decision` is `approve \| reject \| downgrade \| defer \| retire`. `adjudication_state` includes **`withdrawn`**, reached per [25 §7.1] by *"[a]djudicator judgment, with the reason required"* — **but no `decision` value produces it.** The state is reachable by no adjudication path the contract describes | Add `withdraw` to the `decision` CHECK, or state which existing decision produces `withdrawn`. Related: the mapping from `reject` to `unsupported` versus `refuted` is also unstated, and [25 §7.1] implies `refuted` is evidence-derived rather than adjudicator-chosen | **Blocking** the withdraw control. Interim in §6.4: no withdraw control is rendered. Not applied; flagged |
| **15** | **25 §8.1** | [25 §5.2] requires dual control to publish at S3/S4, but `GET /hypotheses` declares **no `awaiting_second_signature` filter** and the response carries no second-signature field. [30 §4.5] has one for proposals. **A second adjudicator has no way to find the hypotheses awaiting their signature** | Add `awaiting_second_signature` and the second-adjudicator fields, mirroring [30 §4.5] | **Blocking** dual-control discovery on Sheet 08. Interim in §6.4: the second adjudicator arrives by link. Not applied; flagged |
| **16** | **25 §8.1** | `POST /causal-feature-set-admissions` is declared with **no request body**, while [25 §2.6]'s `causal_feature_entry` requires `feature_key`, `definition_ref`, `definition_version`, `definition_time`, `equipment_family`, `standing`, and `review_due`. The admission form of [25 §5.1] step 8 cannot be built | Specify the request body, as [28] did for three operations under [42 §18] item 3 | **Blocking** §6.5's admission control. Interim: a stated-reason refusal rather than a guessed body. Not applied; flagged |
| **17** | **WF sheet H's `RE` card / 25 §5.2** | Sheet H's `RE` card reads *"Adjudicates causal failure-mode hypotheses"*, and sheet 08's title block names the persona *"Reliability Engineer (practitioner)."* **[25 §5.2]'s interim authority for publishing a hypothesis is `design_authority`**, [31 §2.4]'s six-member enum has no reliability-engineer role, [31 §13 item 12] forbids a seventh, and sheet H's own footnote calls `RE` *"review-only."* **The persona named on the sheet cannot perform the sheet's primary action**, and the card copy and the footnote contradict each other | Resolve [25 OD-5] — most likely by the finer-grained `reliability_engineer` role within `design_authority` [25 §5.2] permits and [03 §7.2.1] sanctions (*"may add finer-grained roles within a class"*) — **and** correct the `RE` card's copy to match whichever answer lands | **Blocking** Sheet 08's purpose, not its construction. §6.7 states the position; every adjudication is refused server-side with reasons in the meantime. Not applied; flagged. Compounds [50 §13] correction 17 |
| **18** | **28 §9.1 / 30 §4.5** | **Nothing maps a `case_id` to its live `proposal_id`.** [28 §9.1]'s `GET /proposals` has no `case_id` filter; [30 §4.5]'s queue row carries *"no domain content"*, so `payload.case_id` is not projected; and `redesign_case.published_via_proposal_id` [28 §3.6] is set only **after** publication — i.e. never at the moment adjudication needs it. A review surface reached by `case_id` cannot find the proposal it must adjudicate | Add `case_id` to [28 §9.1]'s `GET /proposals` filters, **or** carry the live `proposal_id` on `GET /redesign-cases/{id}` and in `redesign_case_detail`'s `redesign_case` fragment | **Blocking** Sheet 09's adjudication when the caller arrives without the proposal id. Interim in §7.1: the id travels on the link; the fallback scan renders explicit zero-match and ambiguity states. Not applied; flagged |
| **19** | **WF sheet 09** | The dossier line renders `strength: moderate`. **`moderate` is in no vocabulary in the corpus** — [25 §4.4]'s bands are `S0`–`S4` with authored plain-English names — and [28 DA-2] forbids re-stating a strength *"as anything other than what Failure Intelligence adjudicated"* | Render the band identifier and its [25 §4.4] name. Also correct the chip's tone: a strength band is not a status *(50 §2.2's first rule)* | Applied in §7.3; the wireframe needs the edit |
| **20** | **WF sheet 09** | Three under-renderings of honesty machinery the schemas make mandatory. (a) *"Test data: no qualification record found"* collapses four distinct `record_status` values [28 §3.2.3] whose distinction *"survives into the case."* (b) *"72% graph completeness"* renders the aggregate ratio alone, which [28 §3.6] says *"hides which one you have"*, and omits `is_bounded_below` and `nodes_truncated_at_depth` — [28 DA-7] forbids both omissions. (c) The cost box's three fixed chips carry no `is_lower_bound`, no `assumptions[]`, no `PLACEHOLDER` marker, and no `failed_conditions`/`remedy` | Redraw all three: one row per expected test kind with its status; the full completeness object with the bounded-below sentence; and a cost region carrying the lower-bound qualification, the assumptions, the placeholder marker, and the gate's per-condition results | Applied in §7.3–§7.5 as component specifications; the wireframe needs the edits |
| **21** | **WF sheet 09** | The sheet renders no `recommendation_stance`, `recommendation_limitations`, or `recommendation_evidence_gaps` — yet [28 §3.6]'s `assembled_is_complete` CHECK makes all three mandatory and non-empty on an assembled or published case, and [28 §1.2] E3 says why: *"[t]his is what makes 'to a standard a design engineer can evaluate and defend' checkable: the case states what it does not know."* **The sheet as drawn shows the confident half of the decision package** | Draw the recommendation region with the stance, the basis references, and the full limitations and evidence-gaps lists | **Blocking** the sheet's stated purpose. `RecommendationBox` specified as required in §7.6; the wireframe needs the edit |
| **22** | **WF sheet 09** | The sheet draws **no adjudication controls**, no dual-control affordance, and no non-program-evidence flag — yet it is the review surface for a `redesign_case` proposal, [28 §6.5] makes human adjudication the only route to `published`, [03 §7.2.1] as amended requires dual control at class **and** fleet scope, and [28 §6.4] says *"the adjudication UI surfaces [the non-program-evidence flag] prominently"* | Draw the adjudication panel: approve / reject, the signature-of-two state, the required note, and the non-program-evidence flag above the controls | **Blocking** the sheet's primary act. Specified in §7.7; the wireframe needs the edit |
| **23** | **50 §9.5, 50 §4.3, and 51's launch affordances** | Three gaps in the launch path into this app. (a) [50 §9.5] builds both launch URLs as `${VITE_PRACTITIONER_BASE_URL}/<surface>`, and [51] has adopted that shape — **but it presumes a shared prefix Domino does not guarantee**: [02 §4.1] gives each App *"[c]ustom URL paths only"* on *"a single deployment-wide subdomain"*, and the two App paths are independent per-App configuration. (b) [50 §4.3] states `apps/web` owns *"exactly one thing"* on these sheets' behalf — the two hub cards — while [51] found **WF sheet 00's side nav also lists both surfaces**, so there are four launch affordances and [50 §4.3]'s count is short. (c) A launch into Surface B needs `case_id`, which the queue row does not carry (correction 18) | (a) Replace with two values, `VITE_PRACTITIONER_FAILURE_INTEL_URL` and `VITE_PRACTITIONER_DESIGN_ADVISORY_URL`, each independently unconfigurable-to-disabled per [50 §9.5]'s own rule. (b) Correct [50 §4.3]'s count to four. (c) Specify the launch from sheet 10's panel in [51], appending `?theme=` and the resolved `case_id` | Not applied; flagged. Raised with [51] as **R-52-2** and **R-52-3** |
| **24** | **25 §10.1 / 28 §16 correction 5 / 13** | Neither sheet can be tested without fixtures the corpus does not confirm exist: hypotheses at every band with residuals, caps, a `restricted` verdict, a supersession, and each negative state; and a case with an incomplete truncated traversal, a lower-bound roll-up, every `test_record_status`, a `contra` citation, a `pma_only` agreement, and a class-scoped proposal. [28 §16] correction 5 already records that document 13 *"[g]enerates no test records, coverage profiles, or dependency edges"* | Confirm [25 §10.1]'s reference dataset covers the strength and state matrix, and land [28 §16] correction 5's Design Advisory dataset. Both are `packages/contracts/conformance/<slug>/dataset/` additions, not document-13 changes | Not applied; flagged. §10.1 states both requirements so the gap is visible before the tests are written |

---

## 14. Open questions

Recorded rather than resolved locally, following [30 §15], [31 §15], and [50 §14]. Numbered `P-OQ-n`. A surface that must proceed records its local resolution in the README ([09 §8.7]) and does not treat it as settled.

| # | Question | Impact if unresolved | Interim position |
|---|---|---|---|
| **P-OQ-1** | **Can one Domino project register two Apps with two launch files?** [02 §4.1] establishes *"[t]en applications per project"* but names no per-App launch file | If not, the two surfaces need two Domino projects sharing one environment image, which doubles the registration and credential surface | Two launch files assumed, marked **[VERIFY]** (§2.1). Fallback stated: two projects. **Raise with whoever administers the Domino deployment** |
| **P-OQ-2** | **Do Extensions become available on the program's self-managed target?** [02 §4.1]: *"GA, **Domino Cloud only**"*, absent from the self-managed 6.2 tree, and *"Domino Apps are the portable fallback that document 04 specifies"* | The practitioner surfaces would mount natively at one of five Domino mount points with page context passed, which is a materially better workflow for *"proximity to the causal analysis"* [04 §10] | App shape built; Extension not. §4.3's identity-propagation requirement already satisfies the *"only hard requirement"* [02 §4.1] names, so the migration would be a registration change. **Raise with Domino product management alongside [02 §7]** |
| **P-OQ-3** | ~~**[31 §5.8]'s confirmation** — does the gateway *authorize* against the caller-authority credential, or merely record it?~~ **[RESOLVED — question is moot.]** `31 §5.8` adopted the token-exchange mechanism (§4.4/§4.6 alternative (a)), so there is no caller-authority credential at the gateway to authorize against or merely record — every call carries one ordinary delegated `fathom` token, authorized exactly as any other delegated caller's is | N/A — the leak this question guarded against (a cross-viewer read behind a shared workload identity) cannot occur under the adopted mechanism, since there is no shared workload identity on the read path | Closed by §4.4/§4.7. No interim rules remain in force |
| **P-OQ-4** | **Print and export.** [50 §14] UI-OQ-10 is unresolved and binds here first: a dossier inside an iframe is the most screenshot-prone artefact in the console | A cost figure, a completeness ratio, or a strength band reaching a slide without its lower-bound qualification, its limitations, and its marking is the exact failure [28 §3.7] and [03 §7.3] exist to prevent | §8.1 item 4 specifies the `@media print` retention set. Whether print is in scope at all is still [50 §14] UI-OQ-10. **Raise with [51] jointly** |
| **P-OQ-5** | **Does a hypothesis need a composed view?** §13 correction 4 | Sheet 08 makes four sequenced calls where Sheet 09 makes one, inside a rate-limit bucket shared by every viewer (§4.8) | Client-side composition (§5.3, §6). It works; whether it should is a [30 §3.2] decision. **Raise with [30]** |
| **P-OQ-6** | **Which persona actually adjudicates a hypothesis?** [25 OD-5], §6.7, §13 correction 17 | Sheet 08's primary action is refused for the persona the sheet names, and no wireframe change fixes that — it is an authority decision | No role invented, no route gated, server refusals rendered with reasons. **Raise with [25]'s owners and the program** — it is [25 OD-5], and it now has a user interface waiting on it |
| **P-OQ-7** | **Is a drafting surface in scope?** §13 correction 10 — [42 §13.3] describes one and no sheet draws it | The `assemble` step [28 §6.1 step 9], the `suggested_stance` divergence view, and the `QualificationReport` have no interface, so the Redesign Case Builder agent's output has nowhere to land for a human to commit | Not built. §5.3 excludes the three drafting operations with the reason. **Raise with [42]'s owners and whoever owns the wireframe** |
| **P-OQ-8** | **Who rotates the workload client secret, and on what cadence?** §13 correction 5 — the credential is injected by Domino's environment mechanism, outside the program's External Secrets path and rotation runbook | An unrotated, unowned credential on a program surface is an accreditation finding, and [31 §5.7] already records the analogous problem for the Endpoint token: *"[r]otation is a **program runbook item**, because Domino provides no rotation policy"* | Named as a runbook item in the README, with no owner assigned by this document. **Raise with the program and with whoever owns the Domino deployment** |

**Reconciliation items with [51 — Operator Console](51-operator-console.md)**, authored in parallel. Each is a shared decision, not a local one; a divergence is a defect in one of the two.

| # | Item | This document's position |
|---|---|---|
| **R-52-1** | **`StrengthStatement` is shared in `packages/ui/src/evidence/`; `EvidenceStrengthMeter` lives there too but is used only by Surface A** | [51 §15] has landed and takes a compatible position: its `EvidenceSummary` renders a cited strength *"**verbatim** and never re-banded or upgraded"* and defers *"sheet 08's `EvidenceStrengthBar`"* to this document [50 §3.2]. **So no `apps/web` component renders a band, and the meter is practitioner-only.** It still belongs in `packages/ui/src/evidence/` rather than in the app, because that is the single home for the band vocabulary and for the never-re-band rule, and verbatim rendering (`StrengthStatement`) is genuinely shared. §2.2, §6.3. **Nothing to reconcile beyond the file location; confirm it at pin time** |
| **R-52-2** | **The launch affordances need two independent URLs, and should append the resolved theme** | [51] has landed with `${VITE_PRACTITIONER_BASE_URL}` + a surface suffix, adopting [50 §9.5] unchanged — and [51] additionally found that **WF sheet 00's side nav carries `Failure Intelligence` and `Design Advisory` as nav items**, so there are **four** launch affordances (two hub cards, two nav items), not two as [50 §4.3] states. Both consequences: (a) [02 §4.1]'s *"[c]ustom URL paths only"* on *"a single deployment-wide subdomain"* makes the two App paths independent per-App configuration, so one base plus a suffix is not guaranteed to resolve — §13 correction 23; (b) `?theme=<light\|dark>` from `fathom.theme` [50 §5.7] is the only mechanism that gives a practitioner surface the operator's theme (§3.5), and it should be appended by all four affordances |
| **R-52-3** | **The launch into Surface B needs `case_id`, which the queue row does not carry** | The unified queue is where an adjudicator finds the proposal [42 §13.3]; [51 §15] renders its drill-down from `redesign_case_detail` and therefore already holds the case. So the launch is `?case_id=` from the panel, not from the row — and the row alone cannot produce it (§13 corrections 18, 23). [51] should specify the panel-to-launch sequence rather than leaving it to be discovered |
| **R-52-4** | **Two surfaces may adjudicate the same `redesign_case` proposal, and that is safe rather than a duplication to remove** | [51 §15] renders `GET /api/v1/gateway/views/redesign-case/{case_id}` inside **sheet 10's** adjudication panel and states the view *"is required by a screen this document owns, not by [52]."* Both are true and both are legitimate: sheet 10 is the console adjudicator's drill-down; Sheet 09 is the engineer's review surface, and only Sheet 09 renders the dependency graph, the two-stage cost estimate with its gate conditions, and the recommendation with its limitations and evidence gaps (§7.4–§7.6). **Two surfaces over one proposal is exactly what the claim lease plus `If-Match` exist to make safe** [03 §7.2 rule 3, 30 §4.6], and at class or fleet scope the second signature may legitimately arrive from the other surface. Neither document should remove its path; both must send `If-Match` and neither may synthesize one |

---

## 15. Quick reference for an implementing agent

Read in this order before writing a line of this app:

1. **[50 — UI Design System](50-ui-design-system.md)** — **§6 twice**, then §2 (tokens), §3 (components and the five hand-built gaps), §4.1 (router), §5 (fetching, freshness, the three states, mutations), §7 (the disclosure components), §8 (accessibility), §11 (the forty-four prohibitions). Nothing in it is re-decided here.
2. **This document** §0.3 (four of [50]'s corrections have moved), §2 (the container and the host), §3 (base path — including §3.3, which [50] did not reach), §4 (credentials, and §4.7 before you believe the write path works), §5.3 (the allowlist), then §6 or §7 for the sheet you are building, then §11.
3. **[02 §4.1](../architecture/02-domino-platform-assessment.md)** in full — every platform claim in §2, §3, and §4 is transcribed from it, and it is binding on all of them.
4. **[25 §2.1, §2.3, §2.4, §2.9, §4, §5, §7, §8.1, §12](25-failure-intelligence.md)** before Sheet 08. §4 and §5 are the ones that decide what the sheet may say.
5. **[28 §1.2, §3.2, §3.3, §3.6, §3.7, §4.4, §5, §6.4, §6.5, §8, §14](28-design-advisory.md)** before Sheet 09. §8 is the highest-stakes rule in that document and §7.3 is how the UI honours it.
6. **[30 §3.2, §3.4, §4.4–§4.7, §6.2, §8.1–§8.4](30-gateway.md)** — the composed view, the six fragment outcomes, the queue, the pass-through discipline the host mirrors.
7. **[31 §2.2, §2.4, §5.4, §5.8, §6.4](31-auth.md)** — the federation direction, the six authority classes, the Endpoint-proxy's own two-credential shape (§5.4, unrelated to this app), and the practitioner token-exchange operation (§5.8) this app actually uses. **Read §5.8 in full before building anything on it.**
8. **[03 §4, §7.2, §7.2.1, §7.3](../architecture/03-integration-contracts.md)** — conventions, `Proposal`, the amended authority table, `ClassificationLabel`.
9. **[09 §8, §9](09-monorepo-and-conventions.md)** — the Definition of Done and the thirty-two prohibitions, both of which apply in full.
10. **The wireframe**, [`docs/design/operator-console-wireframes.html`](../design/operator-console-wireframes.html), `#s8` and `#s9`, and sheet H's `RE` and `DE` cards.

Then: **§12.2 is the checklist you copy into the README and tick**, **§13 is the list of things you will discover are missing** — twenty-four of them, fourteen blocking, all already known and none yours to resolve locally — and **§14 is what to raise rather than decide.**

Two things to expect, so they are not mistaken for bugs in your work: **every adjudication will be refused** until [31 §5.8] is confirmed and [25 OD-5] is resolved (§4.7, §6.7), and **the admission control will refuse with a stated reason** until [25 §8.1] specifies a request body (§6.5). Both are the honest state.
