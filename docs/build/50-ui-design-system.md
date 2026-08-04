# Build Framework 50 — UI Design System, Routing, and Data Access

| | |
|---|---|
| **Status** | Build framework, rev 1. **Binding on `apps/web`, on `apps/practitioner`, and on the new shared package `packages/ui` this document establishes.** First document of Wave 4; the two sibling documents ([51 — Operator Console](51-operator-console.md), [52 — Practitioner Apps](52-practitioner-apps.md)) consume its decisions and do not re-decide them |
| **Scope** | The design-token set, the component layer and its headless-primitive basis, the router and route tree for `apps/web`, the data-fetching and freshness model, the `apps/web` / `apps/practitioner` operational boundary, the classification and advisory banner components, the accessibility baseline, and persona resolution at login |
| **This is the "look-and-feel wave"** | [09 §1.2](09-monorepo-and-conventions.md) defers *"[t]he operator UI's visual design, component library, styling system, and user flows"* to *"a later wave pending user input on look-and-feel."* [09 §2.6](09-monorepo-and-conventions.md) constraint 3 forbids any such choice before that wave. [09 §10 item 6](09-monorepo-and-conventions.md) — *"UI router, state, and data-fetching libraries"* — is **[OPEN]** and is closed here (§4, §5). [31 §1.3](31-auth.md) defers *"[n]etwork router, session storage, and login UI look-and-feel for `apps/web`"* here. [30 §1.3](30-gateway.md) defers *"[t]he operator UI's visual design, component library, routing, state management, user flows"* here. **This document is that wave.** |
| **Primary design source** | [`docs/design/operator-console-wireframes.html`](../design/operator-console-wireframes.html), **rev 3, as approved**. Fourteen sheets (H, 00, 01, 01B, 02–09, 10, 11). Every colour, type face, spacing value, and component pattern in §2 and §3 is transcribed from that file's stylesheet. Cited below as **WF** with the CSS selector or sheet number |
| **Binding sources** | [03 — Integration Contracts](../architecture/03-integration-contracts.md) principle 2, §4, §7.1, §7.2, **§7.2.1**, **§7.3**, §8.3, §12, §13, §15 · [02 — Domino Platform Assessment](../architecture/02-domino-platform-assessment.md) **§4.1**, §4.3, §4.6 · [04 — Sub-Application Architectures](../architecture/04-subapplication-architectures.md) §2, §5, **§9**, **§10**, §11 · [01 — System Architecture](../architecture/01-system-architecture.md) §4, §8.1, §14, §16 · [06 — Demonstration Decisions](../architecture/06-demo-decisions-and-assumptions.md) §2, §5, §6, §7 |
| **Binding build documents** | [09](09-monorepo-and-conventions.md) §2.6 (toolchain, unchanged), §3.1–§3.2 (layout), §8 (Definition of Done), §9 (DO-NOT) · [10](10-shared-packages.md) §4.8–§4.9 (`ClassificationLabel`, TypeScript + Zod publication) · [30](30-gateway.md) §2.3–§2.4, §3, §4, §5.1, §6.5, §7.3 (every operation this UI calls) · [31](31-auth.md) §2.2, §2.4, §3.1, §4.1, §8 (identity, roles, session) · [27](27-fleet-status.md) §3.7–§3.10, §7, §8 (readiness, disclosure, advisory framing) · [33](33-notification.md) §6.4 (delay presentation) |
| **Precedence** | Document 03 prevails on any contract surface. Document 09 prevails on layout, stack, and conventions. Documents 30 and 31 prevail on the operations and identity this UI consumes. Where this document appears to disagree with any of them, **this document is defective** and §13 is where the disagreement should already have been recorded |
| **Verification note** | Library selections were verified against the corpus as of a **May 2026 knowledge cutoff**, following [09 §2.2](09-monorepo-and-conventions.md)'s convention. Every version below is a **floor (`>=`), not a pin**: pin to the current stable minor at implementation time and record it in `pnpm-lock.yaml`. The specific package-name and primitive-coverage claims in §3.1 and §3.3 are marked **[VERIFY]** where they must be re-checked against the registry at implementation time. **No exact version in this document is a settled fact.** No web access was available during authoring |
| **Classification** | Internal. The demonstration operates single-level at `U` [03 §12, 06 §5], **by configuration and not by assumption** — §7 is the enforcement path that is exercised anyway |

---

## 0. How to read this document

Four markers, following [09 §1.3](09-monorepo-and-conventions.md) and [31 §0](31-auth.md):

- **`[03 §n]`**, **`[09 §n]`**, **`[30 §n]`**, **`[WF …]`** — the decision is dictated by that document or by the approved wireframe. Not negotiable at implementation time.
- **`[ESTABLISHED HERE]`** — no prior document fixes this. This document makes the call once, so that `apps/web`, `apps/practitioner`, and the shared package do not make three different ones. The reasoning is stated. A change is cheap here and expensive after two apps disagree.
- **`[VERIFY]`** — a factual claim about an external package that must be confirmed against the registry at implementation time. Proceed on the stated assumption; record the confirmation in the pull request.
- **`[OPEN]`** — genuinely undecided, listed in §14. Do not resolve one locally inside an app.

**Read §2 and §3 before writing any component; read §5 before writing any fetch; read §9 before writing the root route.**

Two decisions arrived with this document's assignment and are **not re-litigated** anywhere below:

1. **The production operator console keeps the wireframe's blueprint / drafting-sheet aesthetic.** The paper/ink/accent/annotation palette, the monospace-plus-serif pairing, the title block with a sheet number, hatch fills as chart placeholders, and italic serif annotation callouts distinct from UI chrome are the production visual language. §2 formalizes exactly that language into tokens. No alternative aesthetic is proposed and none is to be introduced by a later document.
2. **The component layer is built on headless, accessible primitives with fully custom styling.** Not a pre-styled component library. §3.1 names the specific package and justifies it; §3.3 names every place where no primitive exists and the component must be hand-built.

---

## 1. Purpose and scope

### 1.1 Why this document exists before its siblings

Two applications, drawn by two later documents, must produce one visual and behavioural system. `apps/web` renders twelve destination sheets for eight operator personas; `apps/practitioner` renders two Domino-hosted surfaces for engineers who also use `apps/web`. If each document chose its own tokens, its own primitives, and its own fetch idiom, the program would ship two consoles that look related and behave differently — and the behavioural differences would land precisely on the rules that are correctness rules rather than style rules: the advisory framing [27 §8], the contributor disclosure [06 §5 rule 3, 27 §3.7], the degraded-fragment rule [30 §3.4], the delay-presentation rule [33 §6.4], and the queue-freshness rule [30 §4.7].

Therefore: **the tokens, the primitives, the fetch idiom, and the banner components are written exactly once, here, and imported.** An app that declares its own colour value, its own `StatusChip`, or its own `queryFn` is in violation of this document regardless of whether the result happens to look right.

### 1.2 What this document governs

| Concern | Section |
|---|---|
| The exportable design-token set — colour (both themes), type, spacing, border, radius, hatch | §2 |
| The headless-primitive choice, the primitive-to-pattern map, and the components that must be hand-built | §3 |
| The router, the `apps/web` route tree, and the rule that no route is authorization-gated | §4 |
| The data-fetching library, the gateway view-model call pattern, and the freshness/polling model | §5 |
| The `apps/web` / `apps/practitioner` operational boundary — base path, assets, auth, iframe, theme | §6 |
| `ClassificationBanner`, `AdvisoryBanner`, `ContributorDisclosure` — concrete component specs | §7 |
| The accessibility baseline, with computed contrast figures and named tests | §8 |
| Persona resolution at login against the six realm roles of [31 §2.4] | §9 |

### 1.3 What this document does NOT govern

| Out of scope here | Governed by |
|---|---|
| The per-sheet layout, copy, empty states, and interaction detail of the twelve `apps/web` destination sheets | [51 — Operator Console](51-operator-console.md) |
| The two Domino-App surfaces — Failure Intelligence's practitioner causal exploration [04 §9] and Design Advisory's engineer case review [04 §10] — including their routes, their internal navigation, and their Domino deployment spec | [52 — Practitioner Apps](52-practitioner-apps.md). §4.3 states explicitly what is excluded and why |
| Every wire type. **The UI never hand-writes one** [09 §2.6 constraint 1]; all request and response types come from generated code | [10 §4.9](10-shared-packages.md) (canonical shared types + Zod), [09 §2.5](09-monorepo-and-conventions.md) (`openapi-typescript` per service) |
| The toolchain — React, TypeScript, Vite, pnpm, Vitest, Testing Library, ESLint, Prettier, `openapi-typescript`, `openapi-fetch`, and their floors | [09 §2.6](09-monorepo-and-conventions.md), unchanged and not restated except where a floor interacts with a §3–§5 choice |
| Which operations exist, what they return, and their freshness semantics | [30](30-gateway.md) for composed views and the queue; [20]–[28] for each sub-application |
| The OIDC flow's server side, realm layout, ABAC policy, CAC/PIV | [31](31-auth.md) |
| Any quantity — fleet size, item counts, latency budgets | [06 §7]. §5.4 derives a polling interval *from* those figures and invents none |
| Any Navy schema detail — hull rendering, ESWBS, NIIN format | [07](../architecture/07-navy-data-systems.md), consumed through the generated types |

### 1.4 Traceability

Every element of §2 and §3 traces to a wireframe selector; every element of §4–§9 traces to a build or architecture document. A token or component with no citation in this table is a defect.

| Artifact | Source | Section |
|---|---|---|
| Colour tokens, light theme | WF `:root` (lines 4–24) | §2.2 |
| Colour tokens, dark theme | WF `:root[data-theme="dark"]` (lines 25–45) and the `prefers-color-scheme` block (46–67) | §2.2, §2.6 |
| Type faces | WF `--font-mono`, `--font-annotation` (lines 80–81) | §2.3 |
| Type scale | WF, twelve distinct rule sizes; enumerated with their selectors | §2.3 |
| Spacing scale | WF, snapped to a 2 px grid; enumerated with their selectors | §2.4 |
| Border and radius conventions | WF `.sheet`, `.box`, `.chip`, `.btn`, `.tree`, `.placeholder-fig` | §2.5 |
| Hatch fill | WF `--hatch` (line 23) | §2.5 |
| Theme resolution | WF lines 25–67 | §2.6 |
| Headless primitive package | **[ESTABLISHED HERE]** | §3.1 |
| Primitive-to-pattern map | WF component classes | §3.2 |
| Hand-built components and the gaps that force them | **[ESTABLISHED HERE]** | §3.3 |
| Component inventory by sheet | WF sheets H, 00, 01, 01B, 02–07, 10, 11 | §3.5 |
| Router | **[ESTABLISHED HERE]**, closing [09 §10 item 6] | §4.1 |
| Route tree | WF sheet index; segments are the canonical slugs of [03 §3.1] | §4.2 |
| Data-fetching library | **[ESTABLISHED HERE]**, closing [09 §10 item 6] | §5.1 |
| Composed-view call pattern | [30 §3.2, §3.4] | §5.3 |
| Freshness / polling intervals | **[ESTABLISHED HERE]**, derived from [06 §7], [30 §4.7], [04 §5] | §5.4 |
| Base-path and asset handling | [02 §4.1], [09 §2.6 constraint 2] | §6.1, §6.2 |
| Session and token custody | [31 §4.1], [31 §2.2] | §6.3 |
| `ClassificationBanner` | [03 §7.3], [30 §7.3], [10 §4.8] | §7.2 |
| `AdvisoryBanner` | [27 §8.1–§8.4], [04 §5] | §7.3 |
| `ContributorDisclosure` | [06 §5], [27 §3.7–§3.9] | §7.4 |
| Accessibility baseline and contrast figures | WCAG 2.2 AA, computed against §2.2's values | §8 |
| Persona resolution | [31 §2.4, §3.1, §8], [01 §4], [03 §7.2.1], WF sheet H | §9 |

### 1.5 Which UI is which — confirmed against the current text

The assignment's summary was checked against [04](../architecture/04-subapplication-architectures.md) as it now stands rather than trusted. It is correct, and the confirmation matters because §4.3 excludes two sheets on this basis.

| Sub-application | Operator-facing surface | Basis, quoted |
|---|---|---|
| Asset & Configuration Registry [04 §2] | `apps/web` | *"Plane placement: Sustainment Plane in full. No Domino workloads."* |
| Condition & Telemetry [04 §3] | `apps/web` | *"ingest, storage, and serving on the Sustainment Plane"* |
| Predictive Maintenance [04 §4] | `apps/web` | *"the service, prediction store, and orchestration on the Sustainment Plane"* |
| Fleet Status & Readiness [04 §5] | `apps/web` | *"Sustainment Plane entirely."* |
| Maintenance Execution & Scheduling [04 §6] | `apps/web` | *"service and optimizer on the Sustainment Plane"* |
| Supply Chain & Inventory [04 §7] | `apps/web` | *"Sustainment Plane."* |
| Post-Mission Analysis [04 §8] | `apps/web` | *"service and workflow on the Sustainment Plane, including the afloat profile"* |
| **Failure Intelligence [04 §9]** | **`apps/practitioner` (Domino App)** | *"Practitioner-facing causal exploration is a Domino App, since its audience is reliability engineers who hold Domino accounts."* |
| **System Test & Design Advisory [04 §10]** | **`apps/practitioner` (Domino App)** | *"Engineer-facing case review is a Domino App, since the audience holds Domino accounts and the workflow benefits from proximity to the causal analysis."* |

**Exactly two, and no others.** A `grep` for *"Domino App"* across [04](../architecture/04-subapplication-architectures.md) returns those two plane-placement paragraphs and nothing else. [28 §2 / §16](28-design-advisory.md) and [42 §13.3](42-redesign-case-builder.md) both already place their review surfaces in `apps/practitioner` and both already cite [09 §2.6] constraint 2 and [02 §4.1] for the runtime base path, so the boundary is consistent across the corpus. [01 §4](../architecture/01-system-architecture.md)'s system-context diagram agrees: the Data Scientist / Reliability Engineer actor reaches `Practitioner Apps & Extensions — Domino` only, while the PEO / Design Engineer reaches both.

**Consequence for the Persona Hub, and it is the single most consequential structural fact in this document:** sheet H lives in `apps/web`, but two of its eight cards — Reliability Engineer → sheet 08, PEO / Design Engineer → sheet 09 — have primary landing views that are **not in `apps/web` at all**. Those two buttons are external launches into `apps/practitioner`, not routes. §4.3 and §9.5 specify them.

### 1.6 Sheet accounting

The wireframe's sheet index lists fourteen entries. Its own summary line under sheet H says *"[e]ight persona cards plus two cross-cutting utilities cover twelve sheets."* Both are right and they count different things:

| Class | Sheets | Count |
|---|---|---|
| Pre-landing | H (Persona Hub) | 1 |
| Frame | 00 (App Shell & Navigation) | 1 |
| **Destination sheets** | 01, 01B, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11 | **12** |
| — of which `apps/web` | 01, 01B, 02, 03, 04, 05, 06, 07, 10, 11 | 10 |
| — of which `apps/practitioner` | 08, 09 | 2 |

So `apps/web` routes **ten destination sheets plus the hub, inside one shell** — and covers seven of the nine sub-applications (§1.5). §4.2's route tree has exactly that shape.

---

## 2. Design tokens

### 2.1 Where they live, and the shape of the module

**[ESTABLISHED HERE]** A new workspace package, `packages/ui`.

```
packages/ui/
├── package.json                    # name "@fathom/ui"; react/react-dom as peerDependencies only
├── tokens.css                      # published entry: re-exports src/tokens/tokens.css
├── src/
│   ├── tokens/
│   │   ├── tokens.css              # AUTHORED. The single source of every token value
│   │   ├── tokens.ts               # GENERATED from tokens.css. Typed mirror, for TS consumers
│   │   └── contrast.fixture.ts     # GENERATED. The (fg, bg, ratio, requirement) rows of §8.4
│   ├── primitives/                 # §3.2: Button, StatusChip, Box, WfTable, Sparkline, …
│   ├── patterns/                   # §3.2: SheetFrame, TitleBlock, KpiTile, SheetNote, …
│   ├── disclosure/                 # §7: ClassificationBanner, AdvisoryBanner, ContributorDisclosure
│   ├── map/                        # §3.5: AorMap and its parts
│   ├── a11y/                       # §8: SkipLink, VisuallyHidden re-export, EquivalentTable
│   └── index.ts
└── tests/
```

Six rules, each load-bearing:

1. **`tokens.css` is authored; `tokens.ts` and `contrast.fixture.ts` are generated from it**, by `tools/gen_tokens.ts`, and CI fails on drift. This is [09 §2.5](09-monorepo-and-conventions.md)'s regenerate-and-diff convention applied to tokens: *"[b]oth generated documents are committed and CI fails on drift."* A hand-maintained TypeScript copy of a CSS variable is the same divergence risk [10 §4.9] mitigates with golden vectors.
2. **The token layer has no React dependency and no JavaScript dependency.** `tokens.css` is importable by a Vite build, by a Python-served Domino App template, and by a Storybook-less test harness. The reasoning is [10 §9.4](10-shared-packages.md)'s, transposed: `canonical-schemas` *"must import in a Domino Job container, in the edge runtime, and in the synthetic-data generator, none of which have a web framework"* — `tokens.css` must apply in a Domino-hosted page whose server is FastAPI, not Vite.
3. **`react` and `react-dom` are `peerDependencies`, never `dependencies`.** Two copies of React in one bundle break hooks and context, which would break every Radix primitive silently.
4. **No component in `packages/ui` imports from `apps/*`, and no component fetches.** Data arrives as props. This is what makes the package testable without a gateway and reusable by `apps/practitioner`, whose data path differs (§6.3).
5. **No component in `packages/ui` hard-codes a colour, a length, a font stack, or a duration.** Every visual value is `var(--…)`. Enforced by a Stylelint rule and by the `ui-no-literal-values` test (§10.2).
6. **`packages/ui` is not `packages/ts-common`.** [09 §2.5](09-monorepo-and-conventions.md) assigns `packages/ts-common/src/generated/` the `openapi-typescript` output; that package must remain importable by a non-React consumer for the same reason as rule 2. Mixing a React design system into it would make the generated wire types un-importable without React.

**This adds a directory to [09 §3.1](09-monorepo-and-conventions.md)'s tree and a row to [09 §3.2](09-monorepo-and-conventions.md)'s governance table, and a glob to `pnpm-workspace.yaml`** — [09 §2.6](09-monorepo-and-conventions.md) currently spans *"`apps/*` and `packages/ts-common`"* only. Filed as correction 1 in §13; the edit is upstream, not made here.

### 2.2 Colour — both themes, transcribed

Twenty-two custom properties, from `WF :root` (lines 4–24) and `WF :root[data-theme="dark"]` (lines 25–45). **These values are the source of truth. No colour is invented, adjusted, extended, or added below** — §8.4's conformance fix changes which token a rule *uses*, never a token's value.

| Token | Light | Dark | Role, from the wireframe's own usage |
|---|---|---|---|
| `--paper` | `#EDEFEA` | `#141917` | Page and sheet background (`body`, `.sheet`, `svg.aor .water`, `.box > .box-label` knock-out) |
| `--paper-2` | `#E3E6DF` | `#1B2220` | Recessed surface (`.titleblock`, `.nav-shell .side .item.active`, `.map-frame`, `svg.aor .land`) |
| `--ink` | `#1E2422` | `#DCE3DE` | Body text; the heavy rule (`.sheet` 1.5 px border, `.masthead` 2 px border, `.btn` border, `table.wf th` underline, `.p-glyph` border) |
| `--ink-soft` | `#4A5450` | `#9BA8A1` | Secondary text (`.k-label`, `.k-sub`, `.box-label`, `table.wf th`, `.tb-right`, `.persona`, `.tree .tag`, `.foot`); neutral **text**; neutral marker fill |
| `--line` | `#9CA79E` | `#4B5850` | Structural 1 px rule (`.box`, `.kpi`, `.topbar`, `.nav-shell`, `.toc`, `.classbar`, `.map-key` top, `svg.aor .land` stroke) |
| `--line-soft` | `#C4CBC2` | `#313C36` | Subordinate rule (`table.wf td` underline, `.tree` guide, `.topbar .search` border, `svg.spark .grid`, `svg.aor .grat`), and the hatch stripe |
| `--accent` | `#2F6E6A` | `#56ACA5` | The single interactive accent: links, `.sheet-no`, `.btn.primary` fill, `.chip.accent` fill, focus ring, `svg.spark .line`, map selection ring / leader / callout stroke |
| `--accent-ink` | `#FFFFFF` | `#0B1210` | Text on `--accent` |
| `--annotation` | `#8A5A2B` | `#D0A15F` | Design-rationale voice: `.callout b`, `.sheet-note` text and 3 px left border, `.p-card.is-new` border. **Not UI chrome** — WF legend: *"Design rationale or doc citation — not part of the UI itself"* |
| `--annotation-bg` | `#E9E1D3` | `#2A2419` | `.callout` / `.sheet-note` background |
| `--critical` | `#9C3F35` | `#D97D71` | Status: critical |
| `--critical-bg` | `#E9D8D3` | `#33201D` | Status: critical, tinted field |
| `--warning` | `#8A6A1E` | `#D3B15A` | Status: warning |
| `--warning-bg` | `#EBE1C3` | `#322C18` | Status: warning, tinted field |
| `--good` | `#4C6440` | `#93B481` | Status: good / nominal |
| `--good-bg` | `#DCE3D3` | `#202A1C` | Status: good, tinted field |
| `--neutral` | `#6B7570` | `#8B958E` | Status: neutral. **Non-text only** — see the rule below |
| `--neutral-bg` | `#DDE1DA` | `#232A26` | Status: neutral, tinted field |

Four rules the wireframe implies and this document makes explicit:

- **Semantic status is independent of the accent.** WF's own legend: *"Semantic status — **independent of the accent color**, used only for state (critical / warning / good / neutral)."* An accent-filled control means *"primary interactive control"* and never *"good."* A status colour never renders a control.
- **`--annotation` is the wireframe's own voice and appears in the production console only where the *product* is annotating itself** — the advisory banner (§7.3) and the contributor-disclosure statement (§7.4), both of which are the system telling the operator something about the limits of what it is showing. It is never used for ordinary UI chrome, and it is never used for status. `[ESTABLISHED HERE]`, and it is the one place where the drafting metaphor carries a production meaning rather than a drawing convention.
- **`--neutral` is a non-text token; `--ink-soft` is the neutral text colour.** This resolves what looks like an inconsistency in the wireframe — `--neutral` is defined in both themes and used by no rule, while `.chip.neutral`, `.map-key .mk-dot.neutral`, and `svg.aor .marker.neutral` all reach for `--ink-soft`. The reason is contrast: `--neutral` on `--paper` is **4.19 : 1** in the light theme, below WCAG 2.2's 4.5 : 1 for normal text but above the 3 : 1 required of a non-text indicator (§8.4). Assigning `--neutral` to marker fills, dots, and rule work, and `--ink-soft` to neutral text, makes the wireframe's usage correct rather than accidental and gives the unused token a role. `[ESTABLISHED HERE]`
- **`--hatch` is a token, not a colour.** `WF :root` line 23: `repeating-linear-gradient(135deg, var(--line-soft) 0 1px, transparent 1px 8px)`. It is redefined identically in the dark block because it resolves `--line-soft` at use time; the duplication in WF lines 23 and 44 is harmless and is retained verbatim so a diff against the wireframe is empty.

### 2.3 Typography

Two faces, both from `WF :root` lines 80–81, verbatim including fallback order:

```css
--font-mono: ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", "JetBrains Mono", Consolas, monospace;
--font-annotation: ui-serif, "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
```

**Monospace is the UI body face** (`WF body`, line 74) — not a code face used for code. **Serif italic is the annotation face** (`.kicker`, `.masthead .sub`, `.callout`, `.sheet-note`, `.persona`, `.p-func`, `.placeholder-fig`, `.foot`, `svg.aor .aor-label`). The pairing *is* the aesthetic: chrome and data are mono; the system's commentary on its own output is serif. Preserving that split is what makes §7.3's advisory banner read as the system speaking rather than as another data field.

**No web font is loaded.** Both stacks are system-resolved. This is not a style choice: [09 §9.5 item 26](09-monorepo-and-conventions.md) forbids calling a public-internet service at runtime, and a self-hosted font file would still add two subresources to a page that [02 §4.1] records the Domino proxy has failed to forward (*"not forwarding sub-path asset requests (`/assets/*.js`, `/assets/*.css`)"*). `ui-monospace` and `ui-serif` are the reason the wireframe's stacks work without one. `[ESTABLISHED HERE]`

**Type scale.** Twelve steps, each traced to the wireframe rules that produced it, expressed in `rem` against a 16 px root so that WCAG 2.2 SC 1.4.4 (resize to 200 %) holds without a media query.

| Token | rem | px | Wireframe rules at this size |
|---|---|---|---|
| `--fs-100` | `0.625rem` | 10 | `.box > .box-label` (10); `.nav-shell .side .group-label` (9.5, raised); `svg.aor .grat-label` (7.5, raised); `svg.aor .place-label` (7, raised); `svg.aor .sel-sub` (7, raised) |
| `--fs-150` | `0.656rem` | 10.5 | `.chip`; `.kpi .k-label`; `table.wf th`; `.map-key`; `.p-also`; `.hub-cross .hc-label`; `.titleblock .tb-right` |
| `--fs-200` | `0.688rem` | 11 | `.classbar`; `.titleblock .sheet-no`; `.btn`; `.kpi .k-sub`; `.placeholder-fig`; the 11 px inline notes on sheets 02, 04, 05, 06, 10, 11 |
| `--fs-250` | `0.719rem` | 11.5 | `.p-card .p-func`; `.sheet-note code` |
| `--fs-300` | `0.75rem` | 12 | `table.wf`; `.tree`; `.nav-shell .side .item`; `.legend-label`; the 12 px body text on sheets 07, 10, 11 |
| `--fs-350` | `0.781rem` | 12.5 | `.titleblock .persona`; `.foot`; `svg.aor .sel-label` (8.5, raised) |
| `--fs-400` | `0.844rem` | 13.5 | `body`; `.p-card h3`. **The base size** |
| `--fs-450` | `0.875rem` | 14 | `.callout`; `.masthead .kicker` (13, snapped); `.sheet-note` (13, snapped) |
| `--fs-500` | `0.938rem` | 15 | `.masthead .sub` |
| `--fs-600` | `1.063rem` | 17 | `.titleblock h2` |
| `--fs-700` | `1.375rem` | 22 | `.kpi .k-value` |
| `--fs-800` | `1.563rem` | 25 | `.masthead h1` |

Four rules:

- **`--fs-100` (10 px) is the floor. Nothing in the production console renders below it.** `[ESTABLISHED HERE]` The wireframe's 7 px, 7.5 px, 8.5 px, and 9.5 px rules are drafting-drawing scale and do not survive to a console an operator reads on a bridge. The affected rules are the four `svg.aor` label classes and `.nav-shell .side .group-label`; all move to `--fs-100`, and §13 correction 6 records it. The map's viewBox is widened by 51 if the raised labels no longer fit — a layout consequence, not a token one.
- **Two weights only: 400 and 700.** WF uses `font-weight: 600` on `.chip` and `.legend-label b` and `700` everywhere else (`.k-value`, `.sheet-no`, `.topbar .word`, `.nav-shell .item.active`, `.p-glyph`, `svg.aor .sel-label`). 600 collapses to 700 because a monospace system stack rarely ships a true semibold and a synthesized one is inconsistent across platforms. `[ESTABLISHED HERE]`
- **`--lh-body: 1.55`** (WF `body`), **`--lh-tight: 1.25`** (WF `.p-card h3`), **`--lh-dense: 1.6`** (WF `.titleblock .tb-right`). No other line height appears.
- **Letter-spacing is a token set, not ad hoc**: `--ls-0: 0`, `--ls-1: .01em` (`.masthead h1`, `.titleblock h2`), `--ls-2: .04em` (`table.wf th`, `.chip`, `.topbar .word`), `--ls-3: .05em` (`.btn`), `--ls-4: .06em` (`.box-label`, `.k-label`, `.group-label`, `.hc-label`, `.callout b`), `--ls-5: .08em` (`.classbar`, `.sheet-no`, `.toc-title`). Uppercase micro-labels without tracking are the single most common way this aesthetic reads as cheap.
- **`font-variant-numeric: tabular-nums`** is mandatory on `.kpi .k-value` and `table.wf td.num` (WF lines 200, 220) and on every numeric cell added later. Token: `--num-tabular`. A KPI that shifts width as it polls (§5.4) is a defect.

### 2.4 Spacing

The wireframe uses nineteen distinct lengths. Snapped to a 2 px grid, that is a fourteen-step scale; the `Snapped from` column is what makes the transcription auditable.

| Token | Value | Snapped from | Representative wireframe use |
|---|---|---|---|
| `--sp-1` | `2px` | 2 | `.chip` vertical padding; `.nav-shell .side` row gap; `svg.aor .grat` dash |
| `--sp-2` | `4px` | 3, 4 | `.btn` gap→6 no; `.tree li` margin (3); `.box-content` offset (6) no; `.legend-swatch` offset (2) |
| `--sp-3` | `6px` | 5, 6 | `.box-content` top margin; `.kpi` internal gap; `.chip` gap (5); `table.wf` cell y-padding |
| `--sp-4` | `8px` | 8 | `.chip` x-padding; `table.wf` cell x-padding; `.topbar` y-padding; `.sheet-note` y-padding; `.row` inner gaps |
| `--sp-5` | `10px` | 10 | `.box` y-padding; `.masthead` gap; `.classbar` x-padding; `.legend-item` gap |
| `--sp-6` | `12px` | 12 | `.box` x-padding; `.titleblock` y-padding; `.kpi` padding; `.map-key` x-padding; `.p-card` y-padding; `.btn` x-padding |
| `--sp-7` | `14px` | 14 | `.legend` gap; `.grid` gap; `.hub-grid` gap; `.row` gap; `.p-card` x-padding; `.placeholder-fig` padding; `.nav-shell .main` padding |
| `--sp-8` | `16px` | 16 | `.titleblock` x-padding and gap; `.sheet-body` gap and x-padding; `.callout` x-padding; `.toc` x-padding; `.foot` top padding |
| `--sp-9` | `18px` | 18 | `.callout` top/bottom margin; `.sheet-body` top padding; `.tree ul` left margin |
| `--sp-10` | `20px` | 20 | `.masthead` bottom padding; `.legend` top margin; `.sheet-body` bottom padding; `.wrap` x-padding |
| `--sp-12` | `24px` | 22, 24 | `.toc` top margin (22); `.toc ol` column gap (24) |
| `--sp-14` | `28px` | 26, 28 | `.masthead` bottom margin (28); `.wrap` top padding (28) |
| `--sp-20` | `40px` | 40 | `.sheet` vertical margin |
| `--sp-30` | `60px` | 60 | `.foot` top margin |

Layout tokens, also from the wireframe:

| Token | Value | Source |
|---|---|---|
| `--measure-page` | `1040px` | `.wrap { max-width: 1040px }` |
| `--measure-prose` | `640px` | `.masthead .sub { max-width: 640px }` |
| `--nav-width` | `190px` | `.nav-shell { grid-template-columns: 190px 1fr }` |
| `--search-width` | `320px` | `.topbar .search { max-width: 320px }` |
| `--card-min` | `230px` | `.hub-grid { minmax(230px, 1fr) }` |
| `--legend-min` | `210px` | `.legend { minmax(210px, 1fr) }` |
| `--bp-narrow` | `720px` | `@media (max-width: 720px)` — the single breakpoint. `.grid.cols-{2,3,4}` collapse to one column and `.row` wraps |

**One breakpoint, and it is the only one.** `[WF line 193]`. A console with three breakpoints and no drawn intermediate state invents layouts nobody approved. `.row.wrap-mobile` is the opt-in wrap marker and is retained as a prop (`wrap`) rather than a class.

### 2.5 Borders, radius, and the drafting motifs

| Token | Value | Source and meaning |
|---|---|---|
| `--bw-hair` | `0.75px` | `svg.aor .grat` — graticule only |
| `--bw-1` | `1px` | The structural rule: `.box`, `.kpi`, `.topbar`, `.nav-shell`, `.toc`, `.classbar`, `.map-key`, `table.wf td`, `.btn` |
| `--bw-2` | `1.5px` | The **sheet frame**: `.sheet` border, `.titleblock` bottom border, `.p-card .p-glyph` border |
| `--bw-3` | `2px` | `.masthead` bottom border; the focus ring; `svg.aor .marker.selected` stroke |
| `--bw-accent` | `3px` | The annotation left rule: `.callout`, `.sheet-note` |
| `--bw-spark` | `1.6px` | `svg.spark .line` |
| `--radius-chip` | `3px` | `.chip` — **the only non-zero rectangular radius in the system** |
| `--radius-round` | `50%` | `.chip .dot`, `.p-glyph`, `.map-key .mk-dot`, `svg.aor` circle markers |
| `--dash-guide` | `1px dashed` | `.tree ul` left guide, `.placeholder-fig`, `.hub-cross`, `.btn.ghost` |
| `--dash-lead` | `3 2` | `svg.aor .leader`, `.sel-ring` uses `2 2` → `--dash-ring: 2 2` |
| `--focus-ring` | `2px solid var(--accent)` | `WF .btn:focus-visible` |
| `--focus-offset` | `2px` | `WF .btn:focus-visible { outline-offset: 2px }` |

**Everything is square except chips and dots.** That single sentence is most of the aesthetic. There is no `--radius-sm`, no `--radius-md`, no `--radius-lg`; introducing one is a change to this document.

Four drafting motifs are promoted from CSS classes to named, mandatory components (§3.2), because each carries meaning a later author could mistake for decoration:

| Motif | Wireframe class | Meaning that must not be lost |
|---|---|---|
| **Title block with a sheet number** | `.titleblock`, `.sheet-no`, `.persona`, `.tb-right` | Every destination view states *what sheet it is*, *whose view it is*, and *which documents govern it*. The `tb-right` document references become, in production, the methodology and provenance links (§7.3's `methodology_ref`) — not a drawing artefact but the decomposability requirement of [04 §5] made visible |
| **Hatch fill as a chart placeholder** | `.hatch`, `.placeholder-fig` | A hatched or dashed box means *"a figure belongs here and is not rendered."* It is never a loading skeleton and never an empty state — those are distinct (§5.5). Conflating them would let a permanently-missing chart read as "still loading" |
| **Italic serif annotation** | `.callout`, `.sheet-note` | The system commenting on its own limits. In production this is exactly and only §7.3's advisory statement and §7.4's disclosure statement |
| **The floating box label** | `.box > .box-label` | A named region. Becomes `aria-labelledby` (§3.2), which is why the label may never be purely decorative |

### 2.6 Theme resolution

Transcribed from `WF` lines 25–67, unchanged in mechanism:

```css
:root { /* light values */ }
:root[data-theme="dark"] { /* dark values */ }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) { /* dark values */ }
}
```

Three rules on top:

1. **The dark values appear twice in the stylesheet and are generated from one source.** `tools/gen_tokens.ts` emits both blocks from a single table, and `ui-theme-blocks-agree` (§10.2) asserts they are byte-identical. The wireframe duplicates them by hand (lines 26–43 and 48–65); a divergence there is invisible until a user with a light OS preference toggles to dark.
2. **`data-theme` on `<html>` always wins, in both directions.** The `:not([data-theme="light"])` guard is what makes an explicit light choice survive a dark OS preference. Do not replace the media query with a class-only strategy.
3. **The explicit choice persists in `localStorage` under `fathom.theme`, values `light | dark | system`, default `system`.** `[ESTABLISHED HERE]` For `apps/practitioner` this is best-effort: [02 §4.1] serves Domino Apps *"from a single deployment-wide subdomain and iframed"*, and storage in a third-party iframe is partitioned in current browsers, so a practitioner surface may not remember the choice. §6.5 specifies the host-supplied override that mitigates it. A theme preference that silently fails is acceptable; a console that cannot be read is not.

### 2.7 What the token layer forbids

1. **No colour literal in any component.** Enforced by Stylelint `color-no-hex` plus `ui-no-literal-values` (§10.2).
2. **No token added, removed, or revalued** without a change to this section. The colour set is the wireframe's, complete.
3. **No second accent.** One `--accent`. A "secondary accent" is how a two-colour system becomes a five-colour system.
4. **No opacity-based status.** `svg.spark .area { opacity: .08 }` is the only opacity in the wireframe and it is a fill wash, not a state. A disabled or de-emphasized state is expressed with `--ink-soft` or `--line-soft`, not with alpha, because alpha over an unknown background has no computable contrast (§8.4).
5. **No transition longer than the wireframe's `.15s ease`, and every transition inside `@media (prefers-reduced-motion: no-preference)`** — `WF` lines 273–275 already establishes both. Token: `--dur-fast: .15s`, `--ease: ease`.

---

## 3. The component layer

### 3.1 The headless-primitive package

**[ESTABLISHED HERE]** **Radix Primitives**, floor `>=1.1` on the individual `@radix-ui/react-*` packages, **or** the consolidated `radix-ui` package where it is available at implementation time. **[VERIFY]** — Radix has published both a per-primitive package family (`@radix-ui/react-dialog` and siblings) and a single consolidated `radix-ui` package; confirm which is current, prefer the consolidated package if it is, and record the choice in the pull request. Either way the import surface below is the same and the decision does not change.

**Why this one:**

| Criterion | Radix Primitives | Alternative considered |
|---|---|---|
| Unstyled by construction | Ships behaviour, ARIA, and focus management with no visual opinion, which is the whole requirement: §2's palette is fully specified and a styled library would have to be fought | **Radix Themes** — rejected: it is the styled layer over the same primitives and would import a design system this document replaces. **MUI / Ant Design** — rejected for the same reason, harder |
| ARIA coverage of exactly what these sheets need | Dialog, AlertDialog, Tooltip, Collapsible, ToggleGroup, Popover, Select, Slot, VisuallyHidden, Portal, Direction — the map in §3.2 | **Headless UI** — narrower catalogue; no AlertDialog distinct from Dialog, no ToggleGroup, no Slot-style polymorphism. **Ariakit** — comparable and arguably broader, and a defensible substitute; Radix is chosen for the larger deployed base and because `Slot` solves §3.2's button-as-link problem cleanly. **[VERIFY]** that Ariakit remains the runner-up rather than the leader at pin time |
| React 18 compatibility | Required by [09 §2.6]'s `react >=18.3` floor. Radix Primitives supports React 18 and does not require React 19 features | — |
| Air-gap posture | Pure npm packages, no runtime network access, no CDN asset, no telemetry — which [09 §9.5 items 25–26] requires | A library shipping an icon font or a remote theme is disqualified outright |
| Composition over configuration | Every primitive is a set of parts (`Root`/`Trigger`/`Content`) styled individually, so the drafting motifs of §2.5 are expressible without overriding a vendor stylesheet | — |
| Bundle cost | Tree-shakeable per primitive; only the six families §3.2 uses are pulled in | — |

**No icon set is adopted.** `[ESTABLISHED HERE]` The wireframe contains no icons: status is a coloured dot plus a word (`.chip .dot` + label), domain is a geometric SVG marker, and the persona glyph is a two-letter monogram in a circle (`.p-glyph`). Adopting an icon library would introduce a second visual vocabulary and, in most cases, a webfont — see §2.3. Where a glyph is genuinely needed it is inline SVG in `packages/ui`, monochrome, `currentColor`, `aria-hidden`, sized in `em`.

### 3.2 Primitive-to-pattern map

Every row is a wireframe pattern. **"None"** in the primitive column is a decision, not an omission: it means plain semantic markup is correct and a primitive would add a dependency and a wrapper element for nothing.

| Wireframe pattern | Component in `packages/ui` | Primitive | Notes |
|---|---|---|---|
| `.sheet` + `.titleblock` + `.sheet-body` | `SheetFrame`, `TitleBlock` | **None** | `<section aria-labelledby>` wrapping `<header>` + `<h2>`. The `sheet-no`, `persona`, and `tb-right` slots are props, all optional except `sheetNo` and `title` |
| `.box` + `.box > .box-label` | `Box`, `BoxLabel` | **None** | `<section aria-labelledby={id}>` with the label absolutely positioned over the border. **Not `<fieldset>/<legend>`** — `fieldset` is for grouping form controls and would mis-announce a data region |
| `.chip` (`critical` `warning` `good` `neutral` `accent`) | `StatusChip` | **None** | `<span>`. Radix Primitives has no Badge primitive (Badge lives in Radix Themes, which §3.1 rejects). §8.4 fixes the label colour |
| `.btn` (`default` `primary` `ghost`) | `Button` | **`Slot`** (`asChild`) | Native `<button type="button">` by default. `asChild` renders the same styling on a router `<Link>`, which is what sheet H's `<a class="btn primary">` requires without producing a nested interactive element |
| `table.wf` + `.table-scroll` + `td.num` | `WfTable`, `WfTableScroll` | **None** — hand-built (§3.3) | Native `<table>` with `<caption>`, `scope` on headers, `aria-sort` on sortable headers. `WfTableScroll` is a `<div role="region" tabindex="0" aria-labelledby>` with `overflow-x:auto`, which is what makes a horizontally scrolling table keyboard-reachable |
| `.kpi` / `.k-label` / `.k-value` / `.k-sub` | `KpiTile`, `KpiGrid` | **None** | `<div>` with the label as a `<dt>`-equivalent; §8.3 fixes the reading order so the value is never announced before its label |
| `.sheet-note`, `.callout` | `SheetNote`, `Callout` | **None** | `role="note"`. Serif italic, `--annotation`. In production these render only §7.3 and §7.4 content |
| `.placeholder-fig`, `.hatch` | `FigurePlaceholder`, `HatchFill` | **None** | `<figure>` + `<figcaption>` carrying the required text alternative (§8.5). Distinct from a loading state and from an empty state (§5.5) |
| `.tree` (system / position / installed-item, sheet 02) | `ConfigTree` | **None** — hand-built (§3.3) | ARIA `tree` pattern. **Radix `Accordion` is deliberately not used** — see §3.3 |
| Bitemporal `as_of` / `as_known_at` toggle (sheet 02) | `BitemporalToggle` | **`ToggleGroup`** | WF sheet 02 calls it a *"[b]itemporal toggle — 'what was installed' vs. 'what we believed was installed' (doc 03 §4)."* Two exclusive options; `ToggleGroup type="single"` is exactly this control |
| Map marker hover/focus label (sheet 01) | `MapMarker` + `MarkerTooltip` | **`Tooltip`** (+ `Tooltip.Provider`) | `Tooltip.Trigger asChild` over the marker element. A tooltip is **supplementary only**: the marker's accessible name (§8.5) carries the same information, because a tooltip is unavailable to touch input and is not a substitute for a label |
| Adjudication confirm — approve / reject / execute purge (sheets 07, 10, 11) | `AdjudicationConfirm` | **`AlertDialog`** | `AlertDialog`, not `Dialog`: it requires an explicit action, does not dismiss on outside click, and takes `role="alertdialog"` with a required description. Mandatory for dual-control approval [03 §7.2.1] and for `purge`/`rewrap` [03 §7.2] |
| Adjudication panel body (sheets 07, 10, 11) | `AdjudicationPanel` | **None** | A `Box`, inline, as drawn. Not a modal — the wireframe shows the panel beside the queue and the evidence must remain readable while the queue is visible |
| Queue filter controls (required by [30 §4.5]; **not drawn**) | `QueueFilter` | **`Select`** | [30 §4.5] defines ~20 named query parameters and [30 OQ-9] makes client-side `authority_class` filtering the sanctioned mechanism. No filter control appears on WF sheet 10 — §13 correction 8, and the control's layout belongs to 51 |
| Topbar identifier lookup (sheet 00) | `IdentifierLookup` | **`Popover`** + native combobox — hand-built (§3.3) | Radix has no Combobox primitive. **And it is not a search box** — see §3.3 and §13 correction 9 |
| `.nav-shell .side` + `.item` + `.group-label` + badge | `SideNav`, `NavGroup`, `NavItem`, `NavBadge` | **None** | `<nav aria-label="Sub-applications">` + `<ul>`; the active item carries `aria-current="page"`, which is what the `.item.active` styling means |
| `.topbar` + `.word` + `.id` | `TopBar`, `IdentityBlock` | **None** | `IdentityBlock` renders name · organization · authority chips from §9's session data |
| `.classbar` | `ClassificationBanner` | **None** | §7.2. **Not `Toast`** — Radix Toast is transient and this marking is persistent [03 §7.3] |
| `.skip` | `SkipLink` | **None** | `WF .skip` / `.skip:focus` transcribed; targets `<main>` |
| `.hub-grid` + `.p-card` + `.p-glyph` + `.p-func` + `.p-also` | `PersonaHub`, `PersonaCard` | **None** | Plain markup, as the assignment anticipated. The card is a labelled region containing one primary `Button` and a list of secondary links — **the card itself is not clickable**, because a clickable card containing links is an unresolvable nesting |
| `.hub-cross` | `CrossCuttingBar` | **None** | Two `Button`s, dashed container |
| `svg.spark` | `Sparkline` | **None** — hand-built (§3.3) | §8.5 fixes its accessibility treatment |
| `svg.aor` (map, graticule, markers, selection callout, key) | `AorMap`, `MapMarker`, `MapGraticule`, `MapPlaceLabel`, `MapSelectionCallout`, `MapKey` | **`Tooltip`** on markers only | §3.5 and §8.5 |
| Reservation-set TTL chip (sheet 06, `TTL 03:58:02`) | `TtlCountdown` | **None** | Counts down from a server-supplied expiry; it is **not a poll** (§5.4). `aria-live="off"`; a per-second live region is unusable |
| Evidence-strength bar (sheet 08) | — | — | **Out of scope.** Sheet 08 is a Domino App [04 §9]; the component belongs to [52](52-practitioner-apps.md) |

**Primitives confirmed available and deliberately not adopted**, recorded so a later author does not read the omission as an oversight:

| Primitive | Why not |
|---|---|
| `Tabs` | **No sheet uses tabs.** Sheets 01B, 02, 04, 06, and 11 all use side-by-side `Box`es, not tabbed panes. Adopting `Tabs` would invite 51 to convert drawn two-column layouts into tabs and hide half of each sheet |
| `Toast` | Transient by design. The classification banner is persistent; the advisory banner is persistent; no drawn sheet has an ephemeral notification. Mutation feedback is specified inline in §5.6 |
| `Accordion` | See §3.3 — wrong ARIA for the tree, and no sheet has a standalone accordion |
| `ScrollArea` | `.table-scroll` uses native `overflow-x: auto`. Replacing native scrollbars costs keyboard and assistive-technology behaviour for a purely cosmetic gain |
| `DropdownMenu`, `ContextMenu`, `Menubar`, `NavigationMenu` | No sheet has a menu. The side nav is a list of links |
| `Checkbox`, `RadioGroup`, `Switch`, `Slider`, `Form` | No drawn sheet contains a form beyond the sheet-04 what-if inputs, which are inside a `FigurePlaceholder` (*"adjust usage / deferral inputs → recomputed RUL (Domino Endpoint)"*) and are therefore 51's to draw. When they are drawn, these are the primitives to use — adopting them now would be inventing components the wireframes do not have |
| `Progress`, `Avatar`, `AspectRatio`, `HoverCard`, `Toolbar`, `Separator`, `Label` | Not required. `Separator` and `Label` are replaced by a border token and a native `<label>` respectively |

### 3.3 Where no primitive exists, and what must be hand-built

Five gaps. Each is named so 51 and 52 do not each rediscover it, and each carries the ARIA pattern the hand-built component must implement.

1. **Data table.** Radix has no table primitive. `WfTable` is native `<table>` markup with: a `<caption>` (visually hidden where the surrounding `Box` label already names the region, per §8.3); `scope="col"` / `scope="row"`; `aria-sort` on the sorted column header with a `<button>` inside the `<th>` as the sort control; and no ARIA grid roles. **A `role="grid"` is deliberately avoided** — grid semantics impose two-dimensional cell navigation that none of these tables needs and that would break the expected reading behaviour of a static table. Sorting is server-side wherever the operation offers it ([30 §4.4]'s three sort orders for the queue) and client-side only over a fully-materialized page.

2. **Tree view.** `ConfigTree` (sheet 02's system → position → installed-item hierarchy) implements the ARIA `tree` pattern: `role="tree"` on the container, `role="treeitem"` with `aria-expanded` and `aria-level` on nodes, `role="group"` on child lists, roving `tabindex`, and Up/Down/Left/Right/Home/End key handling. **Radix `Accordion` and `Collapsible` are not used for it.** `Accordion` emits `button` + `region` semantics per item; nesting those three deep produces nested regions announced as headings and disclosures rather than as one navigable hierarchy, and it has no concept of `aria-level`. `Collapsible` supplies open/closed state but none of the tree keyboard model, so it would leave the hard 80 % unbuilt while adding a dependency. Typeahead within the tree is **[OPEN]** (§14 UI-OQ-6): the ARIA pattern permits it and no sheet requires it.

3. **Combobox / identifier lookup.** Radix Primitives has no Combobox. **[VERIFY]** — confirm at pin time that this remains true rather than assuming it. `IdentifierLookup` is a native `<input role="combobox" aria-expanded aria-controls aria-autocomplete="list">` with a Radix `Popover` supplying the positioned `role="listbox"`, implementing the ARIA 1.2 combobox pattern (Down/Up to move `aria-activedescendant`, Enter to select, Escape to dismiss and restore). Alternatives worth a look at implementation time are `downshift` or `cmdk`; either is acceptable **provided it ships unstyled**, and the choice is recorded in the pull request rather than in this document.

4. **Sparkline.** No primitive, and no charting library is adopted. `Sparkline` is ~30 lines of inline SVG generating a `<polyline>`, an area `<path>`, and an end `<circle>` from an array of numbers, exactly as `WF svg.spark` draws it. **No charting library is adopted anywhere in this document** `[ESTABLISHED HERE]`: every other figure on every sheet is a `FigurePlaceholder` (`.hatch` / `.placeholder-fig`), so the only chart the approved wireframe actually renders is this sparkline, and pulling in a charting dependency to draw one polyline would also pull in that library's own visual defaults against §2. When 51 replaces a placeholder with a real figure, the library choice is 51's and must satisfy §2.7 and §8.5.

5. **Persistent banner.** No primitive. `ClassificationBanner` and `AdvisoryBanner` are plain landmark markup (§7). This is listed as a gap only because `Toast` is the primitive an author reaches for and is wrong (§3.2).

### 3.4 Composition rules

1. **One component per pattern, in `packages/ui`, imported by both apps.** A component defined in `apps/web/src/components/` that duplicates a `packages/ui` export is a review rejection.
2. **Variants are props with closed unions, never free-form class names.** `<StatusChip tone="critical">`, where `tone: "critical" | "warning" | "good" | "neutral" | "accent"` — exactly the five wireframe classes. A sixth tone is a change to §2.2.
3. **Every component that renders operator-visible state accepts an explicit "unknown" representation** and renders it distinctly from zero. This is [30 §3.4]'s rule — *"[t]he UI must render the gap; it must not render zero"* — pushed into the type system: `KpiTile`'s `value` prop is `number | string | null`, `null` renders the wireframe's `—`, and there is no default that silently becomes `0`.
4. **No component owns server state.** Data in, callbacks out. §5 owns fetching.
5. **Styling is CSS Modules over the tokens.** `[ESTABLISHED HERE]` No CSS-in-JS runtime (a runtime style engine costs bundle and paint for a token system that is already static custom properties), and no utility framework (a utility framework *is* a design system, which [09 §2.6 constraint 3] excluded and §2 replaces). CSS Modules is chosen over plain global CSS for scoping, and over Tailwind/Panda/vanilla-extract for having no configuration surface that can drift from `tokens.css`.

### 3.5 Component inventory, by sheet

Everything the ten `apps/web` destination sheets plus the hub and the shell require, and nothing else. `*` marks a component required by a binding document rather than drawn on a sheet; each such row carries its citation.

| Sheet | Components |
|---|---|
| **00 — App Shell & Navigation** | `AppShell`, `TopBar`, `IdentityBlock`, `IdentifierLookup`, `SideNav`, `NavGroup`, `NavItem`, `NavBadge`, `SkipLink`, `ClassificationBanner`*, `ClassificationFooter`* [03 §7.3: *"[m]inimum marking is `CUI` in both banner and footer"*], `ProblemDetail`* [03 §4: RFC 9457 on every error path], `RateLimitNotice`* [30 §6.5] |
| **H — Persona Hub** | `PersonaHub`, `PersonaCard`, `PersonaGlyph`, `CrossCuttingBar`, `Button`, `ExternalLaunch`* [§1.5: two cards leave `apps/web`] |
| **01 — Fleet Overview** | `SheetFrame`, `TitleBlock`, `SheetNote`, `AdvisoryBanner`* [27 §8.1; and WF sheet 01's own note: *"a persistent banner, not a tooltip"*], `KpiGrid`, `KpiTile`, `ContributorDisclosure`* [06 §5, 27 §3.7], `AorMap`, `MapGraticule`, `MapPlaceLabel`, `MapMarker`, `MarkerTooltip`, `MapSelectionCallout`, `MapKey`, `EquivalentTable`* (§8.5), `Box`, `WfTable`, `WfTableScroll`, `StatusChip`, `FigurePlaceholder`, `DegradedFragmentNotice`* [30 §3.4] |
| **01B — Vehicle Detail** | `SheetFrame`, `SheetNote`, `ChipRow`, `StatusChip`, `KpiGrid`, `KpiTile`, `ContributorDisclosure`*, `AdvisoryBanner`*, `Box`, `WfTable`, `Button`, `BackLink` |
| **02 — Asset Browser** | `SheetFrame`, `Box`, `WfTable`, `StatusChip`, `ChipRow`, `ConfigTree`, `TreeNode`, `TreeTag`, `BitemporalToggle`, `EpochBadge` |
| **03 — Channel & Health** | `SheetFrame`, `SheetNote`, `Box`, `WfTable`, `WfTableScroll`, `Sparkline`, `HatchFill`, `StatusChip` (completeness) |
| **04 — Fleet-Risk Triage** | `SheetFrame`, `Box`, `WfTable`, `WfTableScroll`, `StatusChip` (`uncalibrated`), `UncalibratedCell`* [03 §7.1: a null `p_failure` *"renders as 'uncalibrated,' never as zero risk"*], `FigurePlaceholder`, `SheetNote` |
| **05 — Work Package Planner** | `SheetFrame`, `Box`, `WfTable`, `WfTableScroll`, `StatusChip`, `ReasonCell`* [04 §6: every included *and* excluded candidate carries a reason] |
| **06 — Stock & Requisition** | `SheetFrame`, `Box`, `WfTable`, `WfTableScroll`, `StatusChip`, `TtlCountdown`, `FigurePlaceholder` |
| **07 — Bounded Review Queue** | `SheetFrame`, `SheetNote`, `Box`, `FigurePlaceholder`, `Button`, `ButtonRow`, `AdjudicationConfirm`, `WfTable`, `StatusChip` |
| **10 — Unified Adjudication Queue** | `SheetFrame`, `Box`, `WfTable`, `WfTableScroll`, `StatusChip`, `DualControlBadge`, `AdjudicationPanel`, `EvidenceSummary`, `Button`, `ButtonRow`, `AdjudicationConfirm`, `QueueFreshnessNotice`* [30 §4.5, §4.7], `QueueFilter`*, `NonProgramEvidenceFlag`* [30 §2.4, 03 §7.2 rule 1, D14], `ApproximateTime`* [30 §4.4: `announced_recorded_at` never precise when dispersion is high] |
| **11 — Remediation & Purge Queue** | `SheetFrame`, `SheetNote`, `Box`, `WfTable`, `WfTableScroll`, `StatusChip`, `AdjudicationPanel`, `AdjudicationConfirm`, `Button`, `DisseminationLedgerTable`, `ReceiptTable` |
| **Cross-cutting** | `Box`, `StatusChip`, `Button`, `WfTable`, `SheetFrame`, `ProblemDetail`, `EmptyState`, `LoadingSkeleton` (§5.5 — three distinct states, one component each) |

**The map, specified.** `AorMap` is the one genuinely novel component and the wireframe fixes its conventions completely (`WF svg.aor`, lines 281–298, and sheet 01's key):

| Aspect | Rule | Source |
|---|---|---|
| Projection | **None. The map is schematic and not to scale.** The `aor-label` *"Simulated positions — CENTCOM AOR, not to scale"* is a **required, non-removable** element of the component, not a caption 51 may drop | `WF svg.aor .aor-label`, sheet 01 note |
| Coordinate space | The `viewBox` (`0 0 640 300`) as authored. Marker positions are viewBox coordinates, not latitude/longitude | `WF` line 514 |
| Position data | **`apps/web/src/features/fleet-status/demo-positions.ts`** — a build-time static map from `asset_id` to `{ x, y }`, covering all **twelve** assets of [06 §7]. `[ESTABLISHED HERE]` **No aggregate, event, or operation in the corpus carries a geographic position for an asset**: [04 §2]'s `Asset` carries *"UIC, domain, operational status, OFRP phase"* and [20 §Asset] adds `hull_or_tail`, `class_id`, `uic`, `operational_status`, `ofrp_phase` — and nothing else. [07] records no public source for real fleet disposition and none is used. §13 correction 3 |
| Marker shape | `Asset.domain` → `circle` (surface) · `polygon` triangle (subsurface) · `rect` (unmanned) | `WF` map key; [04 §2] domain |
| Marker colour | Highest severity among that asset's open risk flags, from the `open_casrep_risk` fragment: `critical` · `warning` · `good` (no open flag) | [30 §3.2]; `WF` map key |
| `neutral` marker | *"no recent contact"* — rendered when the `open_casrep_risk` fragment's outcome for that asset is `empty` or `unavailable`, i.e. **unknown rather than nominal**. This is [30 §3.4]'s rule applied per marker: render the gap, not zero. No field named "recent contact" exists and none is invented | [30 §3.4]; §13 correction 4 |
| Selection | `.sel-ring` + `.marker.selected` + `.leader` + `.sel-label-bg` + `.sel-label` + `.sel-sub`, transcribed. Selection navigates to `/fleet-status/assets/:assetId` | `WF` lines 546–551 |
| Accessibility | §8.5 — and the co-located Risk-flags table is **required, not optional**, as the non-colour equivalent | §8.5 |

---

## 4. Routing

This section closes half of [09 §10 item 6] — *"UI router, state, and data-fetching libraries … Blocks `apps/web` beyond a skeleton."*

### 4.1 The router

**[ESTABLISHED HERE]** **React Router**, floor `>=7.0`, in **declarative / data mode via `createBrowserRouter`** — **not framework mode**. **[VERIFY]** the current major and its React 18 support at pin time.

| Requirement | Why React Router satisfies it |
|---|---|
| React `>=18.3`, Vite `>=6.0` [09 §2.6] | React Router v7 is Vite-native and supports React 18; it does not require React 19 features |
| A **static** build behind program ingress | Declarative mode ships a client-only bundle. **Framework mode is rejected**: it introduces a server runtime and server-side rendering, which [02 §4.1] records as *"[n]ot supported; question unanswered"* on Domino, and which the Sustainment-Plane ingress — serving a Vite build's static output — has no place for. One router configured two ways across two apps is worth more than SSR neither app can use |
| Base-path portability | `createBrowserRouter(routes, { basename })`. `apps/web` passes the build-time `import.meta.env.BASE_URL`; `apps/practitioner` passes a value computed at runtime from `DOMINO_RUN_HOST_PATH` (§6.1). **This is the mechanism that makes [09 §2.6 constraint 2] implementable with one router** |
| Nested layout routes | The shell (sheet 00) is a layout route with an `<Outlet/>`; every destination sheet renders inside it, which is exactly what WF sheet 00 states |
| Parameterized routes | `:assetId`, `:installedItemId`, `:niin`, `:missionId`, `:proposalId` |

Rejected, with reasons recorded: **TanStack Router** — typed routes are genuinely attractive, but its file-based route generation would be a fifth code generator in a repository that already runs four ([09 §2.5]) and its typed-search-param model overlaps the query-key responsibility §5 gives TanStack Query; it is the credible runner-up and switching is a change to this document, not a local decision. **`wouter` / minimal routers** — no nested-layout model. **No router (state-machine navigation)** — unlinkable, and the console's whole drill-down story (sheet 01 → 01B) is a URL.

**Route loaders and actions are not used.** `[ESTABLISHED HERE]` All data fetching is TanStack Query inside components (§5). Using React Router's loaders alongside TanStack Query produces two caches with two invalidation models over the same gateway responses, and the one that loses a race is the one the operator is looking at. The router routes; the query client fetches.

### 4.2 The `apps/web` route tree

**URL segments are the canonical sub-application slugs of [03 §3.1] verbatim**, as reproduced in [09 §7.1]'s slug table. `[ESTABLISHED HERE]` One vocabulary for the API base path (`/api/v1/pdm/…`) and the console path (`/pdm`) removes an entire class of "which name is this" question, and it means a nav label can be changed without changing a URL. Collection segments are plural `kebab-case` and identifier segments are the canonical identifiers of [03 §3.3], following [03 §4]'s naming convention for paths.

```
/                                                    PersonaHub                       sheet H
│
└── (AppShell layout route)                          shell                            sheet 00
    │
    ├── /fleet-status                                FleetOverview                    sheet 01
    │   └── /fleet-status/assets/:assetId            VehicleDetail                    sheet 01B
    │
    ├── /registry                                    AssetBrowser                     sheet 02
    │   └── /registry/assets/:assetId                AssetBrowser (asset selected)    sheet 02
    │
    ├── /telemetry/installed-items/:installedItemId  ChannelHealthView                sheet 03
    │
    ├── /pdm                                         FleetRiskTriage                  sheet 04
    │   └── /pdm/installed-items/:installedItemId    FleetRiskTriage (deep-dive)      sheet 04
    │
    ├── /maintenance                                 WorkPackagePlanner               sheet 05
    │
    ├── /supply                                      StockAndRequisitionView          sheet 06
    │   └── /supply/parts/:niin                       StockAndRequisitionView (NIIN)   sheet 06
    │
    ├── /pma                                         BoundedReviewQueue               sheet 07
    │   └── /pma/missions/:missionId                 BoundedReviewQueue (scoped)      sheet 07
    │
    ├── /adjudication                                UnifiedAdjudicationQueue         sheet 10
    │   └── /adjudication/:proposalId                AdjudicationPanel (nested)       sheet 10
    │
    ├── /audit/remediations                          RemediationAndPurgeQueue         sheet 11
    │   └── /audit/remediations/:proposalId          RemediationPanel (nested)        sheet 11
    │
    └── *                                            NotFound
```

Notes, each load-bearing:

- **`/telemetry` has no index route.** WF sheet 03 is *"Channel & Health View — Maintainer — per-item condition monitoring"*, always scoped to one installed item; there is no drawn fleet-wide telemetry landing view. `/telemetry` redirects to `/registry`, which is the drawn entry point for selecting an item. Inventing a telemetry index would be inventing a sheet.
- **`/adjudication` is not a slug**, and that is deliberate. The unified queue is gateway-owned [30 §4, 04 §11] and `/gateway` means nothing to an operator. It is enumerated here as a carve-out, mirroring [03 §4]'s `x-naming-carve-outs` convention and [30 §8.3]'s own carve-out list. The other carve-out is `/audit/remediations`, where `audit` *is* the platform slug and `remediations` matches [03 §15 obligation 17]'s `POST /{slug}/remediations`.
- **The detail panel is a nested route, not a modal.** `/adjudication/:proposalId` renders `AdjudicationPanel` beside the queue, as drawn, and the URL is shareable — which matters for dual control, where a second adjudicator must reach the same proposal [03 §7.2.1].
- **Deep links always win.** `/` renders the hub; every other URL renders its sheet directly regardless of persona (§9.3).
- **No route is authorization-gated, in either direction.** `[ESTABLISHED HERE]` There is no `<RequireRole>`, no redirect on a missing role, and no hidden nav item that implies a permission. Three reasons, each sufficient: [03 §15 obligation 7] and [09 §8.1] put enforcement in the receiving sub-application and forbid relying on the gateway, let alone on a browser; [31 §8] frames the console's role knowledge as `advisory: true`, *"[n]ever the enforcement point"*; and [31 §6.5]'s predicate-obligation rule — *"[a] service that fetches rows and then drops them is in violation … even if the user never sees the dropped rows — the leak is in the count, the latency, and the cursor"* — is a general statement that client-side filtering is not a security control. A route the operator may not use returns an RFC 9457 problem body [03 §4] and renders `ProblemDetail`. Role knowledge is used only to *rank and mark* affordances (§9) and to filter the queue by `authority_class` as [30 OQ-9] specifies, which is presentation.

### 4.3 What is deliberately **not** routed here

**Sheet 08 (Hypothesis Adjudication, Failure Intelligence) and sheet 09 (Redesign Case Builder, System Test & Design Advisory) have no `apps/web` route, and this is a decision rather than an omission.** Both are Domino Apps [04 §9, 04 §10 — confirmed and quoted in §1.5], both live in `apps/practitioner` [28 §2, 42 §13.3], and both read their base path at runtime from `DOMINO_RUN_HOST_PATH` [02 §4.1, 09 §2.6 constraint 2]. Their routes, internal navigation, and deployment specification belong to [52 — Practitioner Apps](52-practitioner-apps.md).

What `apps/web` **does** own on their behalf is exactly one thing: **the two Persona Hub cards whose primary button launches them** (§1.5, §9.5). `ExternalLaunch` renders those buttons from a build-time configuration value, `VITE_PRACTITIONER_BASE_URL`, and never from a hard-coded URL — because [02 §4.1] records that Domino Apps are served *"from a single deployment-wide subdomain and iframed"* with *"[c]ustom URL paths only"* and *"[c]ustom domains: [n]ot supported"*, so the host is a per-deployment fact. `ExternalLaunch` opens in a new tab, states in its accessible name that it leaves the console, and is the only outbound link in the application.

### 4.4 Route-level concerns that are not authorization

| Concern | Rule |
|---|---|
| Title | Every route sets `document.title` to `FATHOM — <sheet title>`. A single-page application that never changes its title is unusable with a screen reader's window list |
| Focus on navigation | On every route change, focus moves to the destination's `<h2>` (the `TitleBlock` heading), which is announced, and the router's default scroll restoration applies. Implemented once in the shell, not per route |
| Announcement | A single polite live region in the shell announces `<sheet title> loaded`. `[ESTABLISHED HERE]` — SC 4.1.3 is not met by focus movement alone in every assistive technology |
| Not-found | `NotFound` renders inside the shell so the nav remains reachable |
| Query parameters | Filter and sort state lives in the URL query string, not in component state, so a filtered queue is linkable. Parameter names are the operation's own parameter names verbatim ([30 §4.5]'s list) — no client-side renaming |
| Redirects | Exactly two: `/telemetry` → `/registry`, and `/fleet` → `/fleet-status` (a courtesy alias for the label operators will type). No other alias |

---

## 5. Data fetching, freshness, and state

This closes the other half of [09 §10 item 6].

### 5.1 The library

**[ESTABLISHED HERE]** **TanStack Query** (`@tanstack/react-query`), floor `>=5.59`, React 18 compatible. **[VERIFY]** at pin time.

The decisive argument is a property of the gateway, not a preference. [30 §3.5] forbids the gateway from caching any domain response: *"[a] response cache would be a read model by the back door, and would reintroduce D32 at a larger scale than the queue ever did,"* and its cacheable set is exactly three non-domain entries (JWKS, versioned reference data, the committed OpenAPI documents), with `test_no_domain_response_is_cached` asserting that *"[t]wo identical view requests produce two full fan-outs."* **Therefore the only cache that exists anywhere between the sub-applications and the operator is the browser's.** That makes the client cache load-bearing rather than an optimization, and hand-rolling request deduplication, in-flight cancellation, staleness, and retry against a p95 budget of 1.5 s [06 §7] is not a reasonable thing to do by hand seventeen times.

Rejected: **SWR** — comparable, thinner mutation and invalidation story, and no equivalent of the query-key hierarchy §5.3 depends on. **Redux Toolkit Query** — pulls in a store this application does not need (§5.7). **Bare `useEffect` + `fetch`** — reintroduces every problem the gateway declined to solve, in eleven views.

**The fetcher is `openapi-fetch` over the generated types**, both already pinned by [09 §2.6]. TanStack Query supplies the cache; `openapi-fetch` supplies the typed call. A `queryFn` that calls `fetch` directly is a review rejection, because it bypasses [09 §2.6 constraint 1] — *"[t]he UI never hand-writes a wire type … A hand-written interface mirroring an API response is a review rejection."*

### 5.2 One client, in `packages/ui`? No — in each app

`packages/ui` contains no fetching (§2.1 rule 4). The query client, the `openapi-fetch` client, and the query-key factory live in each app, in `src/api/`, because their base URL and credential handling differ (§6). What is shared is the **shape**, specified here so the two do not diverge:

```
apps/web/src/api/
├── client.ts          # createClient<paths>({ baseUrl, credentials: "same-origin" })
├── queryClient.ts     # QueryClient with the §5.4 defaults
├── keys.ts            # the query-key factory — the ONLY place a key literal appears
├── problem.ts         # RFC 9457 parsing -> typed ProblemDetail [03 §4, 09 §5.2]
└── freshness.ts       # the §5.4 interval table, as data
```

**Every response is parsed through the Zod validators [10 §4.9] step 3 publishes** — *"JSON Schema → Zod validators, so the browser enforces the same rules"* — for the canonical shared types (`ClassificationLabel`, `Proposal`, `FailurePrediction`). A response that fails validation renders `ProblemDetail` with a client-side problem type rather than rendering a partially-typed object; `[ESTABLISHED HERE]`, because the alternative is a `TypeError` deep in a component, and because [10 §4.9] built the validators specifically so the browser could do this.

### 5.3 The gateway view-model pattern

Every read the console performs is one of five shapes, all defined by [30].

| Shape | Operation | Consumers |
|---|---|---|
| Composed view | `GET /api/v1/gateway/views/fleet` | sheet 01 |
| Composed view | `GET /api/v1/gateway/views/asset/{asset_id}` | sheets 01B, 02 |
| Composed view | `GET /api/v1/gateway/views/installed-item/{installed_item_id}` | sheets 03, 04 |
| Composed view | `GET /api/v1/gateway/views/explanation/{prediction_id}` | sheet 01's explanation graph, sheet 04's deep dive |
| Queue | `GET /api/v1/gateway/proposals`, `…/summary`, `…/{proposal_id}` | sheets 10, 11; the nav badge |
| Pass-through | `GET /api/v1/{slug}/…` | anything a composed view does not carry — [30 §8.1]: *"[t]he upstream's own contract, proxied"* |

**The composed-view envelope has exactly six top-level members** [30 §3.4]: `view`, `subject`, `as_of`, `fragments`, `degraded`, `data`. The mandatory client pattern:

1. **Read `data.<fragment>` only for fragments whose `fragments.<name>.outcome` is `ok`.** The six outcomes are `ok`, `empty`, `timeout`, `unavailable`, `forbidden`, `classification_fault` [30 §3.4].
2. **`degraded: true` renders `DegradedFragmentNotice` naming the affected fragment and its outcome — never a zero, never a dash that reads as "none."** [30 §3.4]: *"The UI must render the gap; it must not render zero."* This is the single most consequential rendering rule in this document, because the sheets it applies to are KPI tiles whose whole purpose is a number.
3. **`503 urn:fathom:problem:gateway:required-fragment-unavailable` has no partial body** [30 §3.4]. The whole sheet renders `ProblemDetail`, with a retry affordance. There is nothing partial to show.
4. **`502 urn:fathom:problem:gateway:classification-fault` is never rendered as a degraded view.** [30 §7.2] makes filtering and redacting *"[p]rohibited"* and refusing *"[r]equired"*, and `failClosed: true` is *"not overridable."* The sheet renders a distinct, non-retryable `ProblemDetail`.
5. **`as_of` is displayed as the view's currency** — with the caveat that [30] does not define its semantics (§13 correction 5), so it is labelled *"composed at"* rather than *"data as of"* until it is defined. `[ESTABLISHED HERE]`, and deliberately conservative: the wrong label on a timestamp is [33 §6.4]'s and D22's class of defect.
6. **No client-side join across two composed views to derive a third value.** [30 §2.3] property 4 forbids cross-domain derivation in the gateway and [30 §2.4] records that a composed priority score is *"[n]ot computed anywhere."* Computing it in the browser instead would relocate a prohibited derivation, not avoid it. `[ESTABLISHED HERE]`

**Query keys** mirror the operation and its parameters exactly, so invalidation is mechanical:

```
["views","fleet"]
["views","asset", assetId]
["views","installed-item", installedItemId]
["views","explanation", predictionId]
["proposals","list", normalizedFilterParams]
["proposals","summary"]
["proposals","detail", proposalId]
["passthrough", slug, path, normalizedParams]
```

### 5.4 Freshness — the polling decision

**No refresh interval, poll cadence, or push transport is specified anywhere in the corpus.** [30] states no client polling interval, no `Cache-Control` policy on gateway responses, and no streaming surface; a search across `docs/` for `WebSocket`, `Server-Sent`, `EventSource`, and `long-poll` returns nothing. The intervals below are therefore **[ESTABLISHED HERE]**, and the derivation is given so they can be argued with rather than merely accepted.

**No WebSocket, no Server-Sent Events, no `EventSource`, no long-poll, and no gateway push of any kind.** Five independent reasons:

1. [03 principle 2] permits synchronous reads *"only for user-facing composition, and that composition is performed by the API gateway."* A stream is a standing subscription to composition, which is a different thing than a read.
2. [30 §3.5] leaves the gateway holding *"no domain data across requests."* It has nothing to push from; a push transport would require it to hold a read model of the nine sub-applications, which is precisely finding D32 that [30 §2.3] resolves by forbidding it.
3. [01 §14]'s stack contains no such transport, and [02 §5] records that *"[f]leet risk does not change second to second."*
4. [02 §4.1] documents an unresolved Domino proxy defect on sub-path asset requests and no documented WebSocket support, so a push transport would work in `apps/web` and not in `apps/practitioner` — two behaviours for one design system.
5. The queue's own correctness mechanism is not freshness. [30 §4.6] forwards `If-Match` verbatim and returns `428` when it is absent, and [03 §7.2] requires a claim lease; a stale row therefore fails safe at adjudication with a `412`, which is [03 §4]'s mechanism and is unaffected by how often the list was refetched.

**The intervals, and what they are derived from.**

| Query | `staleTime` | `refetchInterval` | Derivation |
|---|---|---|---|
| `["views","fleet"]` | 30 s | **60 s** | Its content changes when scoring runs and when a flag transitions. [06 §7]: scoring cadence is *"[d]aily for tiers 0–1, per-mission-completion for tiers 2–3."* [04 §5] and [27 §6.2] apply hysteresis with *"a minimum dwell time … before either transition,"* so a flag cannot flicker. 60 s over-samples the fastest real change by orders of magnitude and exists for perceived liveness, not for correctness |
| `["views","asset", id]` | 30 s | **60 s** | Same inputs, narrower scope |
| `["views","installed-item", id]` | 30 s | **60 s** | Same |
| `["views","explanation", id]` | `Infinity` | **none** | An explanation decomposes one `prediction_id`. A new prediction is a new id; the old decomposition does not change. Polling it would burn the 4 s budget [06 §7] for nothing |
| `["proposals","list", …]` | 15 s | **30 s** | [06 §7]: *"[a]gent proposals per day | < 20."* 30 s is already ~2,900 polls per operator per working day against fewer than 20 changes, so it is not chosen for coverage — it is chosen because the queue is the one surface where a human is actively waiting, and because [30 §4.7] fixes the projector's staleness bound at `stalenessBoundSeconds: 300`, which means **no client can observe fresher data than 300 s of projection lag permits.** Polling faster than 300 s buys nothing; polling slower makes a claimed row look unclaimed for longer than a person will tolerate |
| `["proposals","summary"]` | 30 s | **60 s** | It drives the nav badge only (WF sheet 00 shows `Adjudication Queue [7]`). A badge is not worth the queue's cadence |
| `["proposals","detail", id]` | `Infinity` | **none** | Refetched on open, on a `412`, and after a successful mutation. [30 §4.6] passes the owner's `ETag` through verbatim and it is the concurrency mechanism; refetching under the operator would silently replace the `ETag` they are about to submit |
| Reference-data enumerations | `Infinity`, keyed by `taxonomy_version` | **none** | [30 §3.5]'s own precedent: *"[c]ached by version, so a cache entry is immutable and invalidation is a version change, not an expiry"* |

**Global query-client defaults**, and each is a decision:

| Setting | Value | Reason |
|---|---|---|
| `refetchOnWindowFocus` | `true` | Does more for perceived freshness than any interval: an operator returning to the tab gets current data immediately, which is the actual complaint intervals are usually chosen to answer |
| `refetchIntervalInBackground` | `false` | A hidden tab polling the gateway is load with no reader |
| `retry` | 2, with exponential backoff | Not on `4xx` other than `408`/`429` |
| `429` handling | **Respect `Retry-After` and pause the interval for that query for the stated seconds** | [30 §6.5] returns `429 urn:fathom:problem:gateway:rate-limit-exceeded` with `Retry-After: <integer seconds>`, *"[c]eiling, never zero"* [30 §6.3], and *"`429` is never `503`."* A poll loop that ignores `Retry-After` converts a rate limit into an outage. `RateLimitNotice` renders while paused |
| `503` handling | Retry with backoff; render `ProblemDetail` with retry | [30 §3.4], [30 §6.5] bulkhead/circuit |
| Time arithmetic | **Every interval, timeout, and backoff is measured with `performance.now()`, never `Date.now()`** | [09 §9.2 item 7] / D29: *"[d]o not let a wall clock arbitrate anything. Not merges, not conflict resolution, not last-writer-wins, not timeouts, not retry backoff, not lease expiry."* The STIG rule cited there permits unlimited backward clock steps, and a backward step with `Date.now()` backoff stalls a poll indefinitely. `TtlCountdown` (sheet 06) computes its remaining time from a monotonic delta against a server-supplied expiry captured once, not from repeated wall-clock subtraction |

**Two figures deliberately not invented.** The gateway states no `Cache-Control` policy, so the client sets none and sends no `If-None-Match` on gateway-owned reads — [30] issues no `ETag` on `/views/*`, `GET /proposals`, or `/proposals/summary`. And no operator-count or concurrency figure exists in [06 §7], so no aggregate request-rate claim is made here; the per-caller bucket of [30 §6.2] is the governing limit and `Retry-After` is the feedback channel.

### 5.5 Three states, three components, never conflated

| State | Component | Rendering |
|---|---|---|
| **Loading** | `LoadingSkeleton` | Structural placeholder at the final layout's dimensions. **Never the hatch fill** — `--hatch` means "a figure belongs here and is not rendered" (§2.5), and a hatched loading state would make a permanently-absent figure indistinguishable from a slow one |
| **Empty** | `EmptyState` | The query succeeded and there is genuinely nothing: `fragments.<name>.outcome === "empty"`, or a zero-length `items` array. States what is empty and over what scope |
| **Unknown / degraded** | `DegradedFragmentNotice` | The query could not determine the answer: `timeout`, `unavailable`, `forbidden`. Names the fragment and the outcome. **Never a zero and never a bare dash** [30 §3.4] |

`KpiTile` distinguishes all three, and `ui-kpi-never-renders-zero-for-unknown` (§10.2) asserts it.

### 5.6 Mutations — claim and adjudicate

Four operations mutate, all on the queue, all proxied by the gateway to the owning sub-application [30 §2.3, §4.6].

| Step | Requirement |
|---|---|
| Claim | `POST /api/v1/gateway/proposals/{proposal_id}/claim`. **`Idempotency-Key` required** [30 §4.5] — a client-generated UUIDv4, generated **once per user action** and reused across retries. Regenerating it on retry defeats the mechanism |
| Adjudicate | `POST /api/v1/gateway/proposals/{proposal_id}/adjudicate`. **`Idempotency-Key` and `If-Match` both required.** The `If-Match` value is the `ETag` from the `GET /proposals/{proposal_id}` the operator is looking at, forwarded unchanged. [30 §4.6]: *"`If-Match` is forwarded verbatim and never synthesized. If the client omits it, the gateway returns `428 Precondition Required`"* |
| `412` | The proposal moved under the operator. Refetch the detail, re-render, and **require the operator to re-confirm** — never auto-resubmit. [03 §7.2]: *"[w]ithout this the eventually-consistent queue permits two approvals and two work orders"* |
| `428` | A client defect, not an operator condition. Fails the `ui-adjudicate-sends-if-match` test (§10.2) rather than being handled at runtime |
| Confirmation | Every adjudication passes through `AdjudicationConfirm` (Radix `AlertDialog`). For `requires_dual_control` proposals the dialog states which signature this is [03 §7.2.1]; for `purge`/`rewrap` it states the act is irreversible [03 §13] |
| Invalidation | On success, invalidate `["proposals","list"]` and `["proposals","summary"]`; **do not optimistically update the row.** An optimistic queue row is a claim about another service's state that the gateway explicitly does not make |
| Evidence | The panel must render `non_program_evidence_only` prominently before the operator acts. [30 §2.4]: *"[t]he one thing an adjudicator must see before opening is whether the proposal rests solely on non-program content."* `NonProgramEvidenceFlag` is not collapsible |
| Agent-adjudication refusal | `403 urn:fathom:problem:auth:agent-may-not-adjudicate` [31 §3.5 step 6] renders as `ProblemDetail`. It cannot arise from a human console session and is handled so that it is never silently swallowed |

**Two presentation rules from [30 §4.4] are binding on the queue and are correctness rules, not preferences** — the section says so explicitly: *"[t]wo rules on presentation, which belong in a build document because getting them wrong is a correctness failure the UI cannot detect."*

1. **The `learned` sort order must not be labelled "oldest first."** [30 §12.4 DO-NOT 31]. It is projection order, which is arrival order at the gateway, which is not chronology.
2. **`announced_recorded_at` is rendered only alongside `announced_dispersion_ms`, and never as a precise time when dispersion exceeds the inter-arrival interval** [30 §4.4, §12.4 DO-NOT 32]. `ApproximateTime` renders *"recorded approximately"* with the uncertainty, which is also [33 §6.4] rule 5's mechanism — *"'on or about patrol day 21 (±6 h)' — and never with false precision."*

**And one from [33 §6.4], which states it is *"binding on the API, on every channel body, and on `apps/web`"*:** `occurred_at` is the headline timestamp, always; `recorded_at`, `delivered_at`, and `received_at` are secondary and separately labelled, *"in any channel body, in any list, in any sort default"*; and default sort is by `occurred_at`. No wireframe sheet renders a notification list, so no component here consumes it — but the rule binds the moment 51 draws one, and §14 UI-OQ-3 records that the surface is undrawn.

### 5.7 Client state that is not server state

**No global state library.** `[ESTABLISHED HERE]` No Redux, no Zustand, no Jotai, no MobX. The application's state is of four kinds and each has a home:

| Kind | Home |
|---|---|
| Server data | TanStack Query cache (§5.1) |
| Navigation and filter/sort state | The URL (§4.4) |
| Ephemeral UI state — an open dialog, an expanded tree node, a hovered marker | React `useState` in the owning component |
| Two durable preferences — theme (§2.6) and hub-skip (§9.3) | `localStorage`, under `fathom.theme` and `fathom.hub.skip`, read through one typed accessor in `src/prefs.ts` |

There is no fifth kind. Adding a store would create a fifth place for server data to live and a second invalidation model, which is §4.1's loader argument again.

---

## 6. The `apps/web` / `apps/practitioner` boundary, operationally

[09 §2.6 constraint 2] and [02 §4.1] establish the base-path difference. Six further differences follow from the same source and are specified here so that 51 and 52 do not each discover them.

### 6.1 Base path

| | `apps/web` | `apps/practitioner` |
|---|---|---|
| Where served | Program ingress, Sustainment Plane [01 §14, 09 §2.6] | Domino App, iframed under a deployment-wide subdomain [02 §4.1] |
| Vite `base` | **Baked at build.** `base: process.env.VITE_BASE_PATH ?? "/"` [09 §2.6 constraint 2: *"document 02 §4.1's runtime-base-path constraint does not apply to it"*] | **`base: "./"` — relative.** The prefix is unknown at build time: [02 §4.1] states *"[t]he URL prefix is supplied at runtime through `DOMINO_RUN_HOST_PATH`, whereas standard build tooling bakes the base path at build time"* |
| Router `basename` | `import.meta.env.BASE_URL` | Read at runtime from a `<meta name="fathom-base-path">` tag the serving process writes from `DOMINO_RUN_HOST_PATH`, with `"/"` as the fallback. The SPA never reads the environment variable itself — it has no access to it |

### 6.2 Assets, and the defect that forces the next line

[02 §4.1] records, on the SPA base-path row: *"[a] customer ticket in February 2026 reported the proxy 'not forwarding sub-path asset requests (`/assets/*.js`, `/assets/*.css`), preventing modern SPA/SSR apps from loading correctly.' The thread received no product resolution."*

**Therefore `apps/practitioner` sets `build.assetsDir: "static"`** and relies on relative URLs from `base: "./"`. `[ESTABLISHED HERE]` Two mitigations for one unresolved platform defect: relative URLs remove the dependence on a correct absolute prefix, and moving off the literal `/assets/` path avoids whatever the proxy rule was doing. `apps/web` keeps Vite's default `assets` directory, because it is served by program ingress and the defect does not apply. The divergence is recorded in both apps' `vite.config.ts` with this citation, so nobody "harmonizes" them later.

Two further consequences of the same finding: **`apps/practitioner` must be a single container** — [02 §4.1] *"Multi-container: [n]ot supported. One image, one launch file, one pod"* — so its SPA build output is served by the same FastAPI process that proxies its data calls (§6.3). And **it must tolerate being restarted without notice**: *"[p]latform maintenance restarts application pods,"* *"[n]ode consolidation evicts them,"* and *"[o]utput persistence: [n]ot supported — file changes inside an App container are not saved."* Nothing durable is written by the app, and no server-side session state is held (which [02 §4.1] also warns of directly: *"Domino does not serialize or isolate access to shared resources across App users … [a]utoscaled applications share temporary storage"*).

### 6.3 Authentication and token custody — the sharpest difference

**`apps/web` holds no token.** [31 §4.1] step 1, verbatim:

> `Human ──login──▶ apps/web ──▶ gateway ──authorization code + PKCE──▶ Keycloak`
> *Gateway is a BFF: the USER'S ACCESS TOKEN NEVER LEAVES THE SERVER. `apps/web` holds a session cookie. [ESTABLISHED HERE — a token in a browser is a token in every browser extension the browser has installed]*

Consequences, all binding:

| Rule | Basis |
|---|---|
| The console never reads, stores, decodes, or refreshes an access token. There is no `Authorization` header in `apps/web` | [31 §4.1]; [31 §13 item 5]: *"[d]o not write a token to disk, to a checkpoint, to a log line, to an event payload, or to an audit record"* |
| Every request is `credentials: "same-origin"` and carries the session cookie | [31 §4.1] |
| The console cannot read `fathom.identity.authority_classes[]` from a token, because it has no token. It must be told. **No operation returns it** — see §9.2 and §13 correction 7 | [31 §3.1]; [30 §8.1] |
| Cookie attributes, CSRF strategy, and the session store are the gateway's, not this document's — but they are **currently unspecified**, and [31 §1.3] deferred them here while [30] defines no session surface at all. §14 UI-OQ-1 | [31 §1.3]: *"[n]etwork router, session storage, and login UI look-and-feel for `apps/web` \| Deferred to the look-and-feel wave"* |
| **Logout is unspecified in the entire corpus.** No RP-initiated logout, no back-channel logout, no `end_session_endpoint` appears in [31] or [30]. The console renders a sign-out control that calls a gateway endpoint that does not yet exist; §14 UI-OQ-2 and §13 correction 7 | Absence in [31], [30] |
| CORS is not a factor for `apps/web` if it is served same-origin with `/api/`, which is the intended shape — [30 §11.1] sets `corsAllowedOrigins: []` with *"set per environment to the operator UI origin only,"* i.e. cross-origin is an environment-specific fallback, not the default | [30 §11.1] |

**`apps/practitioner` is a different problem, and it is not solved by the corpus.** [31 §2.2] federates in one direction — *"[t]he `fathom` realm is the authority. Domino's Keycloak is configured to broker to it as an external OIDC identity provider. Identity never flows the other way"* — and its own diagram separates *"`apps/web` · gateway · 17 services · agents"* (which hold `fathom`-realm tokens) from *"Workspaces · Jobs · Apps"* (which hold *"Domino session cookies"*). It then warns against exactly the reasoning that would paper over the gap: federation *"does not put caller identity on a Domino Endpoint invocation … [t]hat gap is what §5 exists to close, and it must not be reasoned away by pointing at federation."* And [31] defines **no client ID for a practitioner app** and no mechanism by which a Domino-hosted page obtains a `fathom`-realm access token.

**Resolved position** (§13 correction 10, §14 UI-OQ-4 — both closed): **[AMENDMENT]** This was originally recorded as an interim position, flagged as an amendment ask rather than presented as settled, describing the practitioner host reusing [31 §5.4]'s Endpoint-proxy shape (a workload token plus a second, caller-authority-bearing header). A security review found that reuse defective — one header name validating two structurally incompatible credentials — and [31 §5.8] was corrected instead to a settled token-exchange operation.

The practitioner SPA holds **no token either**, exactly like `apps/web`. Its co-resident FastAPI process (§6.2) is the credential holder, but it does not attach a second header to its own workload token: it presents the verified Domino identity assertion **once**, to `POST /api/v1/auth/practitioner-exchange` [31 §5.8], and receives back an ordinary short-lived delegated `fathom` token — never accepting a claimed subject from the browser [31 §13 item 15: *"[d]o not trust a caller's assertion of who its end user is"*], since the exchange, not the gateway, is where the Domino identity is verified. Every subsequent call to `gateway` carries that one exchanged token, identical in shape to any other delegated caller's, so `apps/practitioner` is a full read-and-write surface against every operation its authority permits — no narrowed workload envelope, no blocked adjudication actions, per [52 §4.4, §4.7].

The one thing that does **not** differ: **both apps hold a cookie and no token of their own construction — `apps/practitioner` holds a token only briefly, obtained by exchange, not one it mints or asserts.** That is what lets `packages/ui` be shared without an auth abstraction inside it.

### 6.4 How each build output reaches a URL

| | `apps/web` | `apps/practitioner` |
|---|---|---|
| Build | `vite build` → static bundle | `vite build` → static bundle, embedded in the app image |
| Serving | Sustainment-Plane ingress, same origin as `/api/v1/…`, so `/` and `/api/` share a host | The single Domino App container's FastAPI process serves the bundle and proxies `/api/` calls (§6.3) |
| Deep-link fallback | Ingress rewrites unknown paths to `index.html`; without it, a refresh on `/fleet-status/assets/…` 404s | The FastAPI catch-all returns `index.html`; the same failure mode with the same fix |
| Namespace | `fathom-sustainment` [09 §2.4] | Domino's `domino-compute`. **Never deployed into Domino's namespaces by us** [09 §9.5 item 28] — Domino deploys it |
| Timeout ceiling | Program ingress | [02 §4.1]: nginx connect/read default **300 s**, admin-tunable, *"[n]o per-application override."* A practitioner surface must therefore not initiate a request it expects to exceed 300 s |
| Scale | HPA [09 §2.4] | [02 §4.1]: HPA since 6.2, *"minimum one pod, no scale-to-zero, scale-up in approximately 20 seconds."* And practically, *"most of the time people are only using a single pod app"* — so a practitioner surface's client-side polling budget is smaller than the console's; §5.4's intervals are halved in frequency for `apps/practitioner` (i.e. 120 s / 60 s), `[ESTABLISHED HERE]` |

### 6.5 The iframe, and what it does to the theme

[02 §4.1]: *"Iframe rendering | Default … Applications are served from a single deployment-wide subdomain and iframed. An iframeless view exists for applications supporting deep linking. External content is subject to administrator-managed content-security-policy allowlisting."*

| Rule | Reason |
|---|---|
| No `window.top` access, no top-level navigation, no assumption of being a top-level document | Cross-origin framing makes both unavailable |
| Theme: `data-theme` is set from a `?theme=` query parameter or a `postMessage` from the host page when either is available; otherwise `prefers-color-scheme` (§2.6) | Inside an iframe `prefers-color-scheme` reflects the browser, not the Domino chrome, so a practitioner surface can render dark inside a light Domino page. The override is the mitigation; the mismatch is otherwise expected and acceptable |
| Theme persistence is best-effort | Third-party-iframe storage is partitioned (§2.6 rule 3) |
| No external subresource of any kind | The administrator-managed CSP allowlist, plus [09 §9.5 item 26]. §2.3's no-web-font rule is the concrete case |
| Deep linking is supported so the iframeless view is available | [02 §4.1] makes it conditional on the app supporting deep linking, and §4.1's router already does |

---

## 7. Classification, advisory framing, and exclusion disclosure

Three components. All three surface a rule that is a correctness or accreditation requirement rather than a presentation choice, and all three are therefore in `packages/ui/src/disclosure/` with their own tests.

### 7.1 Why these are components and not conventions

Each of the three rules has an explicit, cited statement in the corpus that it must not be buried, and each names the same failure mode: a consuming UI reads the fields it renders and drops the rest.

- [06 §5] rule 3: *"A low-side rollup never presents itself as complete. **The boolean is displayed, not buried in metadata.**"*
- [27 §8.1]: *"**Top-level, not nested in metadata, not a `_links` entry, not an envelope wrapper.** The same argument as 06 §5 rule 3 makes for the contributor disclosure: a consuming UI reads the fields it renders, and burying the label guarantees it is dropped."*
- [03 §7.3]: *"Minimum marking is `CUI` in both banner and footer."*

A convention would be dropped. A component with a test cannot be.

### 7.2 `ClassificationBanner` and `ClassificationFooter`

**Data source.** `ClassificationLabel` [03 §7.3], as implemented in [10 §4.8] and validated in the browser by the Zod publication of [10 §4.9]. Fields, verbatim from [03 §7.3]:

| Field | Rendering |
|---|---|
| `level` | `U \| CUI \| S \| TS`. Rendered as the banner's leading word, uppercase, expanded (`U` → `UNCLASSIFIED`, `CUI` → `CUI`). The expansion table is in `packages/ui` and is the only place it exists |
| `cui_categories[]` | Rendered verbatim, in the order received, comma-separated. [03 §7.3]: these are *"line 3 of the DoDI 5200.48 designation indicator"* — *"all types of CUI contained in the document"* — and are *"structured obligations, not annotations"* |
| `dissemination[]` | Rendered verbatim, **in [03 §7.3]'s declared order, never alphabetized**: `NOFORN`, `FED ONLY`, `FEDCON`, `NOCON`, `DL ONLY`, `RELIDO`, `REL TO`, `DISPLAY ONLY`, `AC`, `AWP`. Reordering a marking string is a marking change |
| `distribution_statement` | `A..F` or `REL TO`, per DoDI 5230.24 Table 1 — *"line 4 of the designation indicator"*. Rendered as `DISTRIBUTION <letter>` |
| `compartments[]` | Rendered verbatim |
| `derived_from` | Not in the banner. Available in the banner's expandable detail |
| `inherited_from[]` | **Rendered in the expandable detail as the list of contributing label references, and its presence is disclosed in the banner itself** as *"derived label"* — see below |

**Where the label comes from at runtime.** `X-Classification` on every response [03 §4; 09 §8.1: *"`X-Classification` on every response"*]. For a composed view the header is **the union of the contributing fragments' labels**, computed by the gateway with `ClassificationLabel.union(...)` and accumulating `inherited_from` [30 §7.3]. The banner therefore renders a *derived* label on every sheet backed by a composed view, and must say so — because [03 §7.3] makes aggregation itself a classification event: *"**Aggregation is a classification event.** A rollup whose value moves when a compartmented item degrades discloses that item's existence."* A banner that shows only the union level, with no indication that it is a union, silently drops the one fact `inherited_from` exists to carry [D13].

**Rules:**

1. **Banner and footer, both, on every page.** [03 §7.3]. `WF .classbar` is the banner; **the wireframe has no footer marking** — §13 correction 11. `ClassificationFooter` renders the same label, same rules, at the bottom of the shell.
2. **Always data-driven; never hard-coded, in any environment.** [03 §12]: the demonstration *"operates at a single level, and this is stated rather than implied to be multi-level capable"* — but the enforcement path is exercised, so a hard-coded `UNCLASSIFIED` string would remove the only place the console participates in it. `ui-classification-banner-is-data-driven` (§10.2) asserts that the component renders `S` when given `S`.
3. **Retired markings are never rendered, and never appear as a literal anywhere in either app.** [03 §7.3]: *"'FOUO' and 'U//FOUO' are RETIRED markings (DoDI 5200.48 §3.4.b)."* [10 §4.4]'s `FTH005` lint rejects them as string literals across the monorepo; **that rule is extended to `apps/web`, `apps/practitioner`, and `packages/ui`** `[ESTABLISHED HERE]`, following the precedent [27 §8.3] set when it extended `FS-TERM-001` to *"any `apps/web` module importing its types."* If a label arrives carrying one, the banner renders a distinct fault state rather than the marking; [31 §6.5]'s denial reason `retired_marking_present` is the server-side counterpart.
4. **Never rendered in a `Tooltip`, never collapsed, never behind a disclosure toggle, never removed on scroll.** The banner is persistent chrome in the shell, outside every route, so no route can fail to render it.
5. **A missing `X-Classification` is a fault, not a default.** The banner renders a fault state and the console does not substitute `U`. [30 §7.2] makes the analogous server-side posture *"[r]efuse, alarm, and fail closed."*
6. **`502 urn:fathom:problem:gateway:classification-fault`** [30 §7.2] renders a distinct, non-retryable `ProblemDetail`. [10 OQ-16] and [30 §7.3] record that a union containing incompatible statements *"raises rather than guessing"* — the console must not guess either.

### 7.3 `AdvisoryBanner`

[04 §5]'s key decision — *"[a]dvisory overlay, not a readiness system of record … It must not present itself as, or be mistaken for, authoritative readiness reporting … this is an **accreditation and acceptance concern rather than a stylistic one**"* — is carried in the contract by four redundant mechanisms [27 §8]. Two of them are the console's to honour.

**Data source: the required top-level `advisory` object** [27 §8.1], on *"[e]very 2xx response from every readiness, risk-flag, explanation, and status-summary operation"*:

| Field | Rendering |
|---|---|
| `statement` | **Rendered verbatim.** Not paraphrased, not shortened, not truncated with an ellipsis. It is the marking |
| `authoritative`, `system_of_record` | Both `false`; rendered as the banner's leading assertion |
| `character` | `predictive-advisory` |
| `methodology_version` | Rendered in the `TitleBlock`'s `tb-right` slot — which is what §2.5 identified as the production meaning of the wireframe's document-reference block |
| `methodology_ref` | A link, in the same slot. [27 §8.4] makes `GET /methodology/{version}` `x-substitution: required` because *"'advisory' is only meaningful if the advice's basis is inspectable"* |
| `display_requirement` | `must_be_surfaced`. **The component asserts this at runtime**: if the value is `must_be_surfaced` and the banner is not mounted in the rendered tree, the development build throws and the test `ui-advisory-must-be-surfaced` fails. [27 §8.1]: *"It is the hook that makes 'the UI must show this' checkable rather than aspirational"* — this is where it gets checked |

**Rules:**

1. **A persistent banner, not a tooltip.** WF sheet 01's own note: *"That label is a persistent banner, not a tooltip."*
2. **Rendered in `--annotation` serif italic** (§2.2's third rule): this is the system commenting on the limits of its own output, which is exactly the voice the annotation face carries.
3. **The header is a redundant source and is honoured.** [27 §8.2] sets `X-FATHOM-Advisory: predictive-advisory; authoritative=false; methodology=1.4.0` on every response *"including problem-details responses"*, *"because a proxy, a BFF view-model composition [04 §11], or a client SDK may drop either one, and the two failure modes are independent."* If the body block is absent but the header present, the banner still renders, from the header. **This matters concretely here**: [30 §3.2]'s `fleet_overview` composes a `readiness_rollup` fragment, and a BFF composition is one of the two droppers [27 §8.2] names.
4. **`FS-TERM-001` applies to console code.** [27 §8.3] runs its forbidden-term denylist over *"`services/fleet-status/**`, its OpenAPI description strings, and any `apps/web` module importing its types."* Every term in that table — `readiness_status`, `readiness_state`, `readiness_rating`, `mission_capable` and its family, authoritative rating ladders, `casrep` as an assertion, `certified`/`verified`/`official`/`authoritative`/`system_of_record` as positive assertions, `compliant`, `reportable` — is forbidden in a component name, a prop name, a label string, a route segment, and a test fixture. The positive vocabulary of [27 §8.5] is used instead: `advisory_readiness_score`, `degradation`, `risk_flag`, `predicted_casualty_category_candidate`, `degradation_contributor`. **WF sheet 01's KPI label *"Fleet Readiness"* and sheet 01B's *"Hull Readiness"* are display labels, not identifiers, and are permitted** — but the underlying prop and query field names are [27 §8.5]'s, and 51 should confirm the display labels with the subject-matter experts [27 §8.3] says must validate the list (its `OD-8`).

### 7.4 `ContributorDisclosure`

**Data source: the required, non-nullable `contributor_disclosure` block** [27 §3.7], carried by *"[e]very readiness and explanation response, in **every** view … a required, non-nullable member of the response body — never a metadata sidecar, never a header alone"*:

```json
"contributor_disclosure": {
  "restricted_contributors_present": true,
  "restricted_contributor_count": 1,
  "view": "default",
  "completeness": "partial",
  "statement": "This score is computed over the contributors visible at your access level. Contributors above that level are excluded from the computation and are not reflected in this figure."
}
```

This is the field WF sheet 01's fourth KPI already shows — `Restricted Contributors · present: no · doc 03 §7.3` — and WF sheet 01B repeats at hull scope.

| Field | Rendering |
|---|---|
| `restricted_contributors_present` | The KPI's headline. `false` renders as **`present: no`**, `true` as **`present: yes`** with the tile in the `warning` tone. **Never rendered as an absent tile when `false`** — a disclosure that appears only when something is hidden is itself the signal, and its absence would then mean "nothing hidden," which is a channel |
| `restricted_contributor_count` | The count, rendered as the KPI value. `WF`'s `—` is correct when the count is zero |
| `view` | `default` \| `high_side` — rendered as a chip, because [27 §3.7]'s three views produce three different figures and the operator must know which one they have |
| `completeness` | `partial` \| — rendered next to the score |
| `statement` | **Rendered verbatim**, in `--annotation` serif, as a `SheetNote` adjacent to the score. Not truncated, not tooltipped |

**Rules, and the first two are the reason this is a component:**

1. **Present on every sheet that renders a readiness figure, propagated upward.** [27 §3.10]: *"`restricted_contributors_present` propagates upward as a logical OR. If any descendant scope excluded a contributor, the ancestor's disclosure block says so. Silence at fleet level about an exclusion four levels down is rule 3 violated at the level operators actually look at."* So sheet 01 (fleet) shows it, sheet 01B (asset) shows it, and any system-scope rollup 51 draws shows it.
2. **Never buried, never collapsed, never a tooltip, never metadata.** [06 §5] rule 3 and [27 §3.7], both quoted in §7.1. And the reason, which is worth reproducing because it is what makes this a security control: [27 §3.7] — *"silent renormalization converts a partial view into something indistinguishable from a total view … With the boolean and count published, the discrepancy is expected and bounded: it discloses existence and a count, which is exactly what policy already sanctions, and nothing more. Publishing is therefore more protective than silence."*
3. **`score: null` is rendered from `suppression_reason`, and the two reasons are never conflated.** [27 §3.9]: `all_contributors_restricted` (with `restricted_contributors_present: true`) and `no_contributors` (with `false`) arrive as HTTP **200**, not 403, and *"[t]he two null-score cases are distinguishable by reason and are never conflated."* `KpiTile` renders each with its own text. **Never 0, never 100, never a blank tile.** [27 §3.9]: rendering `100` *"presents a fully compartmented, possibly failed asset as perfectly ready."* This case is **not drawn on any wireframe sheet** — §13 correction 12.
4. **A client-side forbidden-field denylist.** [27 §3.8] forbids `visible_weight_share`, `total_contributor_count`, `excluded_weight`, `coverage_fraction`, `score_full`, *"any `*_of_total` field, and any field whose value is a function of $C \setminus V$"*, enforced server-side by `fs-forbidden-fields`. **The same denylist runs over `apps/web` and `packages/ui`** `[ESTABLISHED HERE]`, as `ui-forbidden-disclosure-fields` (§10.2), covering component props, computed values, and label strings — because the field [27 §3.8] calls *"[t]he single most natural field an engineer adds in the name of transparency"* is exactly as natural for a UI engineer building a progress bar as for a service engineer building a response model. **And it must not be computed in the browser either**: the console never divides a released weight by anything whose denominator ranges over the full contributor set.
5. **Only renormalized weights are ever rendered.** [27 §3.8]: *"[r]elease renormalized weights only, always, in every view … Structural identity across views is the control."* The console renders what it is given and computes no weight of its own.
6. **The lead-time-coverage KPI is a separate and currently unsourceable figure** — see §13 correction 2. When it becomes available, [27 §7.5]'s presentation rules bind it: the lead-time distribution and the denominator, the chance reference and flag rate, the achievable ceiling, and *"[n]ever viewer-filtered."* WF sheets 01 and 01B currently draw it as a bare percentage, which those rules forbid.

### 7.5 One more rendering rule that is not a banner

[09 §9.3 item 20] / D23, binding on any surface that renders `FailurePrediction`: *"**Do not render `contributing_factors` in causal language,** and do not display factors below the stability threshold. A causal statement must cite an adjudicated Failure Intelligence hypothesis."* WF sheet 04's *"Top factor"* column and its *"Contributing factor / Stability"* table are the affected surfaces. `ContributingFactorRow` therefore: renders `factor` and `contribution` as association, never as cause; renders `attribution_method`; and **takes the stability floor as a required prop** rather than defaulting it — mirroring [10 §4.6]'s deliberate omission, where `CONTRIBUTING_FACTOR_STABILITY_FLOOR` is *"[d]eliberately ABSENT, because no document supplies a value"* and `is_displayable` *"takes it as an argument rather than defaulting it."* The console does not invent the threshold; it refuses to render without one. Also binding: [09 §9.3 item 21] / D7, D19 — the console **branches on `reference_class`, never on `tier`** (`FTH006` lints it), and `UncalibratedCell` renders a null `p_failure` as *"uncalibrated"* with `population_hazard_rate` where present, **never as zero** [03 §7.1; WF sheet 04's own note].

---

## 8. Accessibility baseline

Target: **WCAG 2.2 level AA**, plus the four specific obligations below that the wireframe's own conventions already imply. `[ESTABLISHED HERE]` — no accessibility standard is named anywhere in the corpus; AA is the defensible floor for a DoD-adjacent operator console and Section 508 incorporates WCAG 2.0 AA, which AA of 2.2 subsumes.

Every requirement below is testable and has a named test in §10.2. A generic statement that accessibility matters is not in this section.

### 8.1 Keyboard operation

| Requirement | Test |
|---|---|
| Every interactive element is reachable and operable by keyboard, in DOM order, with no positive `tabindex` anywhere | `a11y-no-positive-tabindex`, `a11y-tab-order` |
| No keyboard trap outside a `Dialog`/`AlertDialog`, where the trap is required and Radix supplies it | `a11y-no-trap` |
| `SkipLink` is the first focusable element and moves focus to `<main>` | `a11y-skip-link` |
| `ConfigTree` implements the full ARIA tree key model (§3.3 gap 2) | `a11y-tree-keys` |
| `IdentifierLookup` implements the ARIA 1.2 combobox key model (§3.3 gap 3) | `a11y-combobox-keys` |
| `WfTableScroll` is focusable (`role="region" tabindex="0"`), so a horizontally scrolling table can be scrolled without a pointer | `a11y-scroll-region-focusable` |
| Every map marker is reachable by keyboard and activatable with Enter and Space (§8.5) | `a11y-map-markers-focusable` |
| Sort controls are `<button>`s inside `<th>`, not click handlers on the `<th>` | `a11y-sortable-headers` |
| No action requires hover. A `Tooltip` is never the only carrier of information (§3.2) | `a11y-no-hover-only` |

### 8.2 Focus visibility

`WF .btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px }` is the wireframe's convention and it is **generalized to every focusable element**, not just buttons — §13 correction 13, because as drawn only `.btn` has it and every link, input, tree node, table sort control, and map marker would render the browser default or nothing.

```css
:where(a, button, input, select, textarea, summary, [tabindex]):focus-visible {
  outline: var(--focus-ring);
  outline-offset: var(--focus-offset);
}
```

| Requirement | Figure | Test |
|---|---|---|
| Focus indicator contrast against the adjacent background ≥ 3 : 1 (SC 1.4.11) | `--accent` on `--paper`: **5.11 : 1** light, **6.67 : 1** dark. `--accent` on `--paper-2`: **4.68 : 1** light, **6.08 : 1** dark | `a11y-focus-contrast` |
| The indicator is never removed, and `outline: none` appears nowhere in either app or `packages/ui` | — | `a11y-no-outline-none` |
| Focus is not obscured by sticky chrome (SC 2.4.11) — the classification banner and footer are in the scroll flow or `scroll-margin` compensates | — | `a11y-focus-not-obscured` |

### 8.3 Structure, labelling, and reading order

| Requirement | Rule |
|---|---|
| One `<h1>` per page (the masthead's product title in the shell), `<h2>` per sheet title (`TitleBlock`), `<h3>` per `Box` label. No level skipped | `a11y-heading-order` |
| Landmarks: `<header>`, `<nav aria-label>`, `<main>`, `<footer>`. One `<main>` |
| Every `Box` is `<section aria-labelledby>` pointing at its `BoxLabel`. A `BoxLabel` is therefore never decorative and never empty (§2.5) |
| Every `WfTable` has a `<caption>`; visually hidden where the enclosing `Box` label already names it, to avoid a duplicated visible title |
| **`KpiTile` reading order is label → value → sub.** The wireframe's DOM order already is (`WF` lines 198–203); the rule exists because the obvious CSS refactor — a large value with an absolutely positioned label — would reverse it and announce a bare number |
| `StatusChip` never conveys state by colour alone. The wireframe already pairs a `.dot` with a word; **the word is mandatory**, and `aria-hidden` is set on the dot |
| `IdentityBlock` uses a native `<label>` for the lookup input; no `placeholder`-as-label |
| `TtlCountdown` is `aria-live="off"` with the expiry time also present as static text; a per-second live region is unusable |
| One polite live region in the shell for route announcements (§4.4) and for mutation results (§5.6) |

### 8.4 Colour contrast — computed, with the one failure and its fix

Ratios below are computed against §2.2's exact values by the WCAG 2.x relative-luminance formula. `contrast.fixture.ts` (§2.1) carries these rows and `a11y-contrast` asserts them, so the table is executable rather than documentary.

**Text, as the wireframe draws it:**

| Foreground | Background | Light | Dark | Required | |
|---|---|---|---|---|---|
| `--ink` | `--paper` | **13.70** | **11.83** | 4.5 | pass |
| `--ink-soft` | `--paper` | **6.72** | **5.62** | 4.5 | pass |
| `--ink` | `--paper-2` | **12.53** | **11.36** | 4.5 | pass |
| `--accent` | `--paper` | **5.11** | **6.67** | 4.5 | pass |
| `--accent` | `--paper-2` | **4.68** | **6.08** | 4.5 | pass (tight — `.sheet-no` at `--fs-200`) |
| `--accent-ink` | `--accent` | **5.90** | **7.08** | 4.5 | pass (`.chip.accent`, `.btn.primary`) |
| `--annotation` | `--annotation-bg` | **4.52** | **6.56** | 4.5 | pass (tight — see the note below) |
| `--critical` | `--paper` | **5.73** | **6.06** | 3.0 (`--fs-700` bold) | pass |
| `--good` | `--paper` | **5.68** | **7.73** | 3.0 | pass |
| `--critical` | `--critical-bg` | **4.80** | **5.23** | 4.5 | pass |
| `--good` | `--good-bg` | **4.99** | **6.45** | 4.5 | pass |
| `--ink-soft` | `--neutral-bg` | **5.86** | **4.90** | 4.5 | pass |
| **`--warning`** | **`--warning-bg`** | **3.86** | 6.77 | 4.5 | **FAIL, light theme** |

**The one failure, and the fix that invents no colour.** `--warning` (`#8A6A1E`) on `--warning-bg` (`#EBE1C3`) is 3.86 : 1 against a 4.5 : 1 requirement, and `.chip` text is `--fs-150` uppercase — normal text by WCAG's definition, since large text requires 18.66 px bold or 24 px. `[ESTABLISHED HERE]`, the `.chip` rule changes so that **every chip renders its label in `--ink`, and the status colour is retained for the dot**:

```css
.chip { color: var(--ink); }
.chip .dot { background: var(--status); }   /* --status resolves per tone */
```

Recomputed, all eight combinations, with margin:

| `--ink` on | Light | Dark |
|---|---|---|
| `--critical-bg` | **11.47** | **11.80** |
| `--warning-bg` | **12.12** | **10.67** |
| `--good-bg` | **12.03** | **11.43** |
| `--neutral-bg` | **11.94** | **11.26** |

The status colour still reads through the tinted background and the dot, so the visual language is unchanged; only the label's colour moves, uniformly, in both themes. The surgical alternative — change only the `warning` chip and leave the other three coloured — is **rejected**: it makes one chip visually inconsistent with its siblings and leaves the rule un-generalizable, so the next tone added repeats the failure. §13 correction 14, and §14 UI-OQ-5 records the alternative in case the program prefers to accept the documented failure instead.

**`--annotation` on `--annotation-bg` at 4.52 : 1 passes by 0.02 and is flagged as at-risk** (§14 UI-OQ-5): it is serif italic at `--fs-450`, the least legible combination in the system at the tightest ratio. No change is made, because changing it means changing a token value and §2.7 forbids that here.

**Non-text contrast (SC 1.4.11, 3 : 1):**

| Element | Ratio | |
|---|---|---|
| `--line` on `--paper` | 2.15 light / 2.42 dark | **Below 3 : 1** |
| `--line-soft` on `--paper` | 1.45 light / 1.62 dark | **Below 3 : 1** |
| `--ink-soft` on `--paper` | 6.72 / 5.62 | pass |
| `--neutral` on `--paper` | 4.19 / 5.83 | pass |
| `--accent` on `--paper` | 5.11 / 6.67 | pass |

`[ESTABLISHED HERE]`, and it is a rule about which token a border uses, not a new token:

- **`--line` and `--line-soft` are decorative and structural only** — sheet frames, box outlines, table rules, graticules, hatch stripes. SC 1.4.11 does not apply to *"decorative"* boundaries or to the visual presentation of ordinary content, and these carry no state.
- **Every boundary that identifies an interactive component or its state uses `--ink-soft` at minimum** — the lookup input's border (`WF .topbar .search` currently uses `--line-soft` at 1.45 : 1), a control's outline, a selected state's edge. `--neutral` is available for non-text status indicators (§2.2's third rule) at 4.19 : 1.
- `.btn` already uses `--ink` (13.70 : 1) and `.btn.ghost` uses `--ink-soft` via `color` with a dashed `--ink` border, so both already comply.

§13 correction 15 records the `.topbar .search` border change.

### 8.5 The map, the sparkline, and the chart placeholders

**The map is the hardest surface in the console and the wireframe's current markup is not accessible.** `WF` line 514 sets `role="img"` with an `aria-label` on the whole `<svg>`. `role="img"` prunes the entire subtree from the accessibility tree — which is correct for a decorative diagram and **wrong the moment a marker is interactive**, and sheet 01 states plainly: *"Click any marker → sheet 01B, scoped to that hull."* As drawn, every marker is invisible and unreachable to assistive technology and to the keyboard. §13 correction 16.

The specified treatment, five parts:

1. **`<figure>` + `<figcaption>` wrapping the SVG.** The caption carries the wireframe's own `aor-label` text — *"Simulated positions — CENTCOM AOR, not to scale"* — which is required content (§3.5), not decoration.
2. **The `<svg>` takes `role="group"` with `aria-labelledby` pointing at the caption**, not `role="img"`, so the subtree remains available.
3. **Every marker is a real interactive element**: `<g role="button" tabindex="0">` with Enter/Space handlers, or preferably a `<button>` overlay positioned over the marker, which gets the correct semantics and focus ring for free. Its accessible name is composed and complete: **hull, domain, status, advisory readiness score** — e.g. `"DDG 113, surface, critical risk flag, advisory readiness 78 percent"`. Non-interactive scenery (land polygons, graticule, place labels) is `aria-hidden="true"`.
4. **A required equivalent table.** `EquivalentTable` renders the same rows the map encodes and is **not optional**. It serves two purposes at once: it is the SC 1.1.1 text alternative for a schematic that is explicitly *"not to scale"* and therefore conveys nothing a table cannot, and it is the SC 1.4.1 non-colour equivalent for marker status, which is encoded **by colour alone** (shape encodes domain, per the wireframe's own map key). On sheet 01 the co-located *"Risk flags"* `Box` already is this table — which is why §3.5 marks it **required, not optional**. Where a map appears without one, `EquivalentTable` renders it visually hidden.
5. **Text size.** The four `svg.aor` label classes move to `--fs-100` per §2.3's floor rule. 7 px map text is not readable and no exception is made for it.

**Sparkline** (`WF svg.spark`, sheet 03): rendered `aria-hidden="true"` — **and only because** the current value and the completeness chip are in adjacent `<td>`s of the same row, so the sparkline is genuinely redundant and announcing it would add noise. `Sparkline` therefore takes a required `redundant: true` prop with a comment naming this condition; a sparkline rendered without an adjacent numeric must pass `label` instead, and `a11y-sparkline-labelled` asserts one of the two is present.

**Chart placeholders** (`.hatch`, `.placeholder-fig`): each is a `<figure>` whose `<figcaption>` states what will be rendered there, using the wireframe's own text (*"RUL distribution — p10 / p50 / p90 range bar, unit: engine operating hours"*, *"score → contributing degradations → source predictions / casualties / shortfalls"*). **Never an empty `aria-hidden` box** — that would make a permanently-missing figure indistinguishable from nothing at all, to everyone.

**Dependency graph** (sheet 09) is out of scope (§4.3); the same rules will bind it in [52](52-practitioner-apps.md).

### 8.6 Motion, zoom, and input

| Requirement | Rule |
|---|---|
| Motion | Every transition inside `@media (prefers-reduced-motion: no-preference)`, as `WF` lines 273–275 already does. No animation on data change; a KPI that animates while polling (§5.4) is both a motion and a legibility defect |
| Zoom | Reflow at 320 px CSS width (SC 1.4.10) is met by the single `--bp-narrow` breakpoint's single-column collapse. Text resize to 200 % (SC 1.4.4) is met by §2.3's `rem` scale |
| Horizontal scroll | Only inside `WfTableScroll` and the map's own container. The page body never scrolls horizontally |
| Target size | Every control meets SC 2.5.8's 24 × 24 px minimum. `.btn` at `--sp-3`/`--sp-6` padding and `--fs-200` computes to ~26 px; **map markers at r ≈ 4.5 px do not** and are given a transparent hit area of at least 24 × 24 px, which is also what makes them usable with a pointer |
| Text spacing | SC 1.4.12 — no fixed-height text container. `.kpi`, `.chip`, and `.nav-shell .side .item` are the at-risk rules and use padding, not height |

---

## 9. Persona resolution at login

WF sheet H leaves this open in its own text — the persona line reads *"Every role — shown at login, or on demand from the app shell"* — and [01 §16] carries the underlying question as still open: *"**Personas.** Which of the four operator personas in §4 the demonstration targets."* This section resolves the console's behaviour concretely.

### 9.1 The eight cards against the six roles

[31 §2.4] fixes the vocabulary at **six realm roles, named exactly as the enum values**, and adds two rules that decide most of this section:

> **Realm representation.** The six values are **realm roles** named exactly as the enum values — not user attributes.

> **No implicit hierarchy. [ESTABLISHED HERE]** A `fleet_authority` does **not** automatically satisfy a requirement for `maintainer`.

And [31 §3.1] rule 3 is the constraint that shapes everything below: *"`fathom.identity.authority_classes` is populated from realm roles, filtered to the … values of §2.4. **A role that is not one of the [six] never appears in a token.**"*

| WF sheet H card | Glyph | Realm role [31 §2.4] | Primary view | Where |
|---|---|---|---|---|
| Executive / Commander (TYCOM Readiness Officer) | `EC` | **`fleet_authority`** | Fleet Overview | `/fleet-status` |
| Vehicle Readiness Officer | `VR` | **none** | Vehicle Detail | `/fleet-status/assets/:assetId` |
| Ship's Force Maintainer | `SF` | **`maintainer`** | Bounded Review Queue | `/pma` |
| RMC / Availability Planner | `AP` | **`planner`** | Work Package Planner | `/maintenance` |
| Supply Officer | `SO` | **`supply_officer`** | Stock & Requisition View | `/supply` |
| Reliability Engineer | `RE` | **none** | Hypothesis Adjudication | **`apps/practitioner`** (sheet 08) |
| PEO / Design Engineer | `DE` | **`design_authority`** | Redesign Case Builder | **`apps/practitioner`** (sheet 09) |
| Security Officer (ISSM / ISSO) | `SC` | **`security_officer`** | Remediation & Purge Queue | `/audit/remediations` |

**Six roles map to six cards. Two cards — `VR` and `RE` — have no realm role and can never be role-resolved.** WF sheet H's own footnote gets this accounting wrong: it states the roster is *"exactly document 03 §7.2.1's six adjudicating authority classes … plus two review-only roles (Ship's Force Maintainer-as-reviewer, Reliability Engineer)"* — but Ship's Force Maintainer **is** `maintainer`, one of the six, so the footnote double-counts it, and it omits Vehicle Readiness Officer, which is genuinely role-less. §13 correction 17.

**Neither `VR` nor `RE` gets a new realm role.** [31 §13 item 12] forbids adding an `AuthorityClass` *"beyond document 03 §7.2.1's enumerated set (six, as of amendment 03-1),"* and [31 §2.4]'s docstring is explicit that *"[a] seventh member is a change to document 03, not to this file."* And they do not need one: adjudication authority is not view authority. `VR` and `RE` are **self-selected personas**, held as a client-side preference (§9.4), and every view they reach is a read surface whose authorization is enforced server-side anyway [03 §15 obligation 7].

### 9.2 What the console actually knows, and the gap

`apps/web` **cannot read the token** — [31 §4.1] puts it entirely server-side (§6.3) — so it cannot read `fathom.identity.authority_classes[]` directly. And there is no operation that tells it:

- [30 §8.1]'s gateway-owned surface is *"[t]he queue (§4.5), the composed views (§3.2), the Domino Endpoint proxy (§5.6), health."* No session or `/me` operation.
- [31 §8] offers `GET /principals/{sub}` — *"[d]isplay attributes for audit rendering and the adjudication queue"* — but the console does not know its own `sub` without a token.
- [30 OQ-9] assumes the opposite of [31 §4.1]: it declines a server-side per-role queue projection on the grounds that *"[t]he UI filters by `authority_class` using the roles it already holds from its own token."* **The UI holds no token.** This is a direct contradiction between two binding build documents and it is §13 correction 7.

**Resolution, `[ESTABLISHED HERE]`.** **[AMENDMENT]** Originally filed as an amendment ask rather than asserted as existing; now closed — [30 §8.1.2](30-gateway.md) declares exactly this operation, and [30 OQ-9] is corrected to read from it rather than from a token the console never held. One operation was required —

```
GET /api/v1/gateway/session          x-substitution: internal
                                     x-side-effects: none
                                     x-agent-eligible: false
→ 200 { sub, display_name, unit_uic, billet, authority_classes[], clearance, classification }
→ 401 urn:fathom:problem:gateway:unauthenticated   (no session cookie)
```

Its fields are exactly [31 §3.1]'s identity block, minus everything [31 §3.6] says a token never contains, and it is `advisory` in the same sense [31 §8]'s `POST /authority-checks` is: *"[n]ever the enforcement point."* §13 correction 7 asks for it against [30 §8.1] and [31 §8].

**The interim, so 51 is not blocked:** until that operation exists, the console treats `authority_classes` as `[]` and `display_name` as unavailable. That degrades the hub to case 3 below — all eight cards, none marked — which is a working state, and it degrades the queue to unfiltered, which [30 §4.5]'s `authority_class` parameter still permits an operator to set by hand. Nothing is broken and nothing is faked.

### 9.3 The resolution algorithm

`[ESTABLISHED HERE]`, and this closes WF sheet H's *"shown at login, or on demand"*.

**`/` always renders the Persona Hub. There is no automatic redirect on the basis of a role.** Four reasons:

1. **A composed view can fail.** [30 §3.4] returns `503 required-fragment-unavailable` *"with no partial body"* when a required fragment is unavailable. Auto-redirecting a `fleet_authority` into `/fleet-status` on a day the `readiness_rollup` fragment is down lands them on a full-page error with no navigation context and no explanation of why they are there.
2. **Role knowledge is advice, not fact.** [31 §8] marks the authority surface `advisory: true`, *"[n]ever the enforcement point."* Auto-routing on advice makes wrong advice silently unrecoverable — the operator cannot tell that a routing decision was made at all.
3. **Two of eight primary views are not in this application** (§9.1). A redirect that sometimes leaves the console entirely, into an iframed Domino App on another host, is a worse first experience than a page with eight labelled choices.
4. **WF sheet H's own framing.** The hub is *"where a role is chosen or confirmed"* — confirmation is the point, and it costs one click.

**But an operator who wants the redirect can have it.** The hub carries a *"skip this next time"* checkbox that writes `fathom.hub.skip = <route>` (§5.7). When set, `/` redirects to that route. It is set by an explicit human action, is per-browser, and is cleared from the shell — never inferred.

**Cases:**

| Case | `authority_classes` | Behaviour |
|---|---|---|
| **1 — exactly one role, primary view in `apps/web`** | e.g. `["planner"]` | Hub renders all eight cards. That card is marked **"your authority"** and rendered first in DOM and visual order; initial focus is on its primary button. No redirect unless `fathom.hub.skip` is set. Pressing Enter immediately is therefore one keystroke to the right place |
| **2 — exactly one role, primary view in `apps/practitioner`** | `["design_authority"]` | Same, and the marked card's button is an `ExternalLaunch` (§4.3) whose accessible name states it leaves the console. Never auto-redirected, in any circumstance — an automatic cross-host navigation into an iframed app is not something a console does to a user |
| **3 — no role in the six** | `[]` | Hub renders **all eight cards, none marked**, plus the two cross-cutting utilities. This is the correct outcome for a pure operator or viewer login and for the interim of §9.2, and it is not an error state: [31 §3.1] guarantees a non-`AuthorityClass` role is filtered out of the token, so `[]` means *"holds no adjudication authority"* and says nothing about read access. No banner suggests the user is unauthorized, because they are not |
| **4 — more than one role** | `["maintainer","planner"]` | Every held role's card is marked **"your authority"**, in [31 §2.4]'s enum order. **No default is chosen and no ranking is applied**, because [31 §2.4]'s *"No implicit hierarchy"* rule means there is no basis on which to prefer one. Initial focus goes to the hub heading, not to a card |
| **5 — a role with no card** | impossible today | The six roles all have cards (§9.1). If a seventh is ever added to [03 §7.2.1], the hub renders an unmapped-authority notice naming it rather than silently ignoring it, and `ui-every-role-has-a-card` (§10.2) fails the build the moment the enum and the card set disagree |

**The hub is also reachable on demand from the shell**, at `/`, from a persistent control in the `TopBar` — the second half of WF sheet H's *"or on demand."*

### 9.4 What the persona selection does and does not do

| Does | Does not |
|---|---|
| Order and mark the hub's cards (§9.3) | Gate any route (§4.2 — no route is authorization-gated) |
| Pre-set the queue's `authority_class` filter, which is [30 OQ-9]'s intended mechanism and is presentation | Hide a nav item, a sheet, a table row, or a count. [31 §6.5]'s predicate rule makes client-side filtering not a control: *"the leak is in the count, the latency, and the cursor"* |
| Pre-set the `awaiting_second_signature` and `claimed=me` filters where the role implies dual-control work [03 §7.2.1] | Enable or disable an adjudication button on its own. Enablement comes from `POST /authority-checks` [31 §8] when available, and the server refuses regardless |
| Persist `VR` / `RE` self-selection and the hub-skip route locally (§5.7) | Write anything to Keycloak, or claim a role the token does not carry |

**On button enablement, precisely:** [31 §8] states `POST /authority-checks` exists *"so the gateway can render a queue without enabled-looking rows nobody may act on,"* with `advisory: true` in the response. The console therefore *may* dim an adjudication control on that advice, **and must still send the request if it is activated**, and must render the server's refusal ([31 §3.5]'s `urn:fathom:problem:auth:not-authorized` with its `reasons`) rather than pre-empting it. A control that is disabled and unexplained is worse than one that fails with a reason.

### 9.5 The two external cards

`ExternalLaunch`, used by the `RE` and `DE` cards only:

| Property | Rule |
|---|---|
| URL | `${VITE_PRACTITIONER_BASE_URL}/<surface>` — build-time configuration, never a literal (§4.3, [02 §4.1]: no custom domains, single deployment-wide subdomain) |
| Target | New tab, `rel="noopener noreferrer"` |
| Accessible name | States the destination **and** that it leaves the console: *"Open Hypothesis Adjudication — opens in Domino, in a new tab"* |
| Unconfigured | If `VITE_PRACTITIONER_BASE_URL` is unset, the card renders with its button disabled and a stated reason. It is never a dead link and never a `#` |
| Return path | None. There is no cross-app session hand-off (§6.3), and inventing one would be inventing the mechanism [31 §2.2] warns against reasoning away |

---

## 10. Testing

[09 §2.6] fixes **Vitest + Testing Library** and nothing is changed. Two additions and one lint extension.

### 10.1 Additions

| Concern | Selection | Floor | Why |
|---|---|---|---|
| Automated accessibility assertions | **`axe-core`**, driven from Testing Library render output by one helper in `packages/ui/tests/axe.ts` | `>=4.10` | §8's requirements are otherwise unenforced. **[VERIFY]**, and the image/package must be mirrored into the private index per [09 §2.2]'s air-gap rule for test infrastructure |
| Contrast assertions | Computed in-repo from `contrast.fixture.ts` (§2.1), no dependency | — | §8.4's table is executable. A colour-token change that breaks a ratio fails CI |
| End-to-end | **None adopted.** §14 UI-OQ-7 | — | No E2E tool is named anywhere in the corpus and [09 §10 item 8] already raises load and performance testing for assignment. Inventing a Playwright estate here would be inventing scope |

### 10.2 The named tests

Every rule in this document that could be silently violated has a test. These names are contractual: 51 and 52 add to the list and remove nothing.

**Tokens and theme**

| Test | Asserts |
|---|---|
| `ui-tokens-no-drift` | `tokens.ts` and `contrast.fixture.ts` regenerate from `tokens.css` with no diff (§2.1 rule 1) |
| `ui-theme-blocks-agree` | The `[data-theme="dark"]` and `prefers-color-scheme` blocks are byte-identical (§2.6 rule 1) |
| `ui-no-literal-values` | No hex colour, no `px` length outside `tokens.css`, no font-family literal, no duration literal in any component (§2.1 rule 5, §2.7) |
| `ui-token-set-complete` | Every token named in §2.2–§2.5 exists in both theme blocks; no extra token exists (§2.7 rule 2) |
| `ui-font-size-floor` | No computed font size below `--fs-100` (§2.3) |

**Rendering rules that are correctness rules**

| Test | Asserts |
|---|---|
| `ui-kpi-never-renders-zero-for-unknown` | `KpiTile` given `null`, `timeout`, `unavailable`, or `forbidden` renders none of `0`, `0%`, `—` alone, or an empty tile ([30 §3.4]) |
| `ui-degraded-view-renders-notice` | `degraded: true` renders `DegradedFragmentNotice` naming the fragment and outcome ([30 §3.4]) |
| `ui-classification-fault-is-not-degraded` | A `502 classification-fault` renders a distinct non-retryable `ProblemDetail`, not a partial sheet ([30 §7.2]) |
| `ui-classification-banner-is-data-driven` | Given `level: "S"` the banner renders `S`; given no `X-Classification` it renders a fault state, never `U` (§7.2 rules 2, 5) |
| `ui-classification-footer-present` | Banner **and** footer render on every route ([03 §7.3]) |
| `ui-no-retired-markings` | `FOUO` / `U//FOUO` appear as a literal nowhere in `apps/*` or `packages/ui`; a label carrying one renders a fault ([03 §7.3], [10 §4.4] `FTH005`) |
| `ui-advisory-must-be-surfaced` | `display_requirement: "must_be_surfaced"` with no mounted `AdvisoryBanner` fails ([27 §8.1]) |
| `ui-advisory-from-header-only` | With the body block absent and `X-FATHOM-Advisory` present, the banner still renders ([27 §8.2]) |
| `ui-fs-term-001` | [27 §8.3]'s denylist over `apps/web`, `apps/practitioner`, `packages/ui` identifiers and label strings |
| `ui-disclosure-always-rendered` | `ContributorDisclosure` renders for both `true` and `false`, never omitted, never inside a `Tooltip` or a collapsed region ([06 §5] rule 3) |
| `ui-forbidden-disclosure-fields` | [27 §3.8]'s denylist over props, computed values, and labels; and no client-side ratio whose denominator ranges over the full contributor set (§7.4 rule 4) |
| `ui-null-score-reasons-distinct` | `all_contributors_restricted` and `no_contributors` render distinctly; neither renders `0` or `100` ([27 §3.9]) |
| `ui-uncalibrated-never-zero` | A null `p_failure` renders *"uncalibrated"*, never `0` ([03 §7.1]) |
| `ui-no-tier-branch` | No component branches on `tier`; `reference_class` only ([09 §9.3 item 21], `FTH006`) |
| `ui-factors-not-causal` | `ContributingFactorRow` requires an explicit stability floor prop and emits no causal verb ([09 §9.3 item 20], [10 §4.6]) |
| `ui-learned-sort-label` | The `learned` sort is never labelled *"oldest first"* ([30 §12.4 DO-NOT 31]) |
| `ui-approximate-time` | `announced_recorded_at` renders through `ApproximateTime` whenever `announced_dispersion_ms` exceeds the threshold ([30 §4.4, DO-NOT 32]) |
| `ui-occurred-at-headline` | Any surface rendering a notification uses `occurred_at` as the headline and does not sort by arrival ([33 §6.4]) |
| `ui-queue-freshness-rendered` | `queue_freshness.stale === true` renders `QueueFreshnessNotice` ([30 §4.7]) |
| `ui-non-program-evidence-not-collapsible` | `NonProgramEvidenceFlag` is rendered outside any collapsed region ([30 §2.4], D14) |

**Data access**

| Test | Asserts |
|---|---|
| `ui-adjudicate-sends-if-match` | `POST …/adjudicate` always carries `If-Match` and `Idempotency-Key`; a `428` is a test failure, not a runtime path ([30 §4.6]) |
| `ui-idempotency-key-stable-across-retries` | One user action produces one key across all retries (§5.6) |
| `ui-412-requires-reconfirm` | A `412` refetches and requires re-confirmation; never auto-resubmits ([03 §7.2]) |
| `ui-retry-after-pauses-poll` | A `429` with `Retry-After: 30` pauses that query's interval for 30 s and renders `RateLimitNotice` ([30 §6.5]) |
| `ui-no-wall-clock-timers` | No `Date.now()` in interval, timeout, backoff, or countdown arithmetic ([09 §9.2 item 7], D29) |
| `ui-no-streaming-transport` | No `WebSocket`, `EventSource`, or long-poll construct anywhere in either app (§5.4) |
| `ui-no-hand-written-wire-type` | No interface or type alias mirrors an API response shape ([09 §2.6] constraint 1) |
| `ui-no-cross-view-derivation` | No component computes a value from two composed views ([30 §2.3] property 4) |
| `ui-zod-validated` | Canonical shared types are parsed through the Zod validators before render ([10 §4.9]) |

**Routing and persona**

| Test | Asserts |
|---|---|
| `ui-no-role-gated-route` | No route renders a redirect or a null on the basis of a role (§4.2) |
| `ui-every-role-has-a-card` | The six `AuthorityClass` values and the hub's role-mapped cards agree exactly ([31 §2.4], §9.3 case 5) |
| `ui-hub-no-auto-redirect` | With one role and no `fathom.hub.skip`, `/` renders the hub (§9.3) |
| `ui-empty-roles-renders-all-cards` | `authority_classes: []` renders eight cards and no unauthorized messaging (§9.3 case 3) |
| `ui-external-launch-configured` | An unset `VITE_PRACTITIONER_BASE_URL` disables the two external buttons with a stated reason; no `#` href (§9.5) |
| `ui-practitioner-basename-from-runtime` | `apps/practitioner`'s router `basename` comes from the injected meta tag, never from a build constant (§6.1) |

**Accessibility** — every test named in §8.1–§8.6, plus `a11y-axe-clean` (zero axe violations of impact `serious` or `critical`) on every component in `packages/ui` and every route in `apps/web`.

---

## 11. Explicit DO-NOT list

[09 §9]'s list applies in full — all thirty-two items. These are additional and UI-specific. Each carries the finding or citation that makes it a defect rather than a preference, so a reviewer may cite the number and stop reading.

### 11.1 Tokens and visual language

1. **Do not introduce a colour that is not in §2.2.** The palette is the approved wireframe's, complete, in both themes. *(§2.2, §2.7; WF `:root`)*
2. **Do not adopt a second accent, a colour ramp, or an opacity-based state.** One `--accent`; state is expressed with `--ink-soft` or `--line-soft`, because alpha over an unknown background has no computable contrast. *(§2.7 items 3–4, §8.4)*
3. **Do not use a status colour for a control, or the accent for a status.** WF's legend makes them orthogonal: *"Semantic status — independent of the accent color, used only for state."* *(§2.2)*
4. **Do not load a web font, an icon font, or any external subresource.** *(01 §12, 09 §9.5 items 25–26; 02 §4.1's CSP allowlist; §2.3, §3.1)*
5. **Do not adopt a CSS framework, a utility framework, or a CSS-in-JS runtime.** A utility framework *is* a design system, which [09 §2.6] constraint 3 excluded and §2 replaces. *(§3.4 rule 5)*
6. **Do not render the hatch fill as a loading state.** `--hatch` means *"a figure belongs here and is not rendered."* Conflating it with loading makes a permanently-absent chart look slow. *(§2.5, §5.5)*
7. **Do not add a border radius.** Everything is square except `.chip` (3 px) and dots (50 %). *(§2.5)*
8. **Do not use the annotation face or `--annotation` for ordinary UI chrome.** It is the wireframe's own voice and, in production, only §7.3's and §7.4's content. *(§2.2, §2.3)*

### 11.2 Components

9. **Do not adopt a pre-styled component library, including Radix Themes.** *(§3.1; the assignment's second fixed decision)*
10. **Do not build the configuration tree on `Accordion` or `Collapsible`.** Nested accordions produce nested regions, not a navigable tree, and neither has `aria-level`. *(§3.3 gap 2)*
11. **Do not render the classification banner or the advisory banner as a `Toast`, a tooltip, or a dismissible element.** Both are persistent markings. *(03 §7.3; 27 §8.1; §7.2 rule 4, §7.3 rule 1)*
12. **Do not invent a component the wireframes do not have.** Tabs, menus, avatars, progress bars, and toasts are all available primitives and none is used by any sheet. Adding one converts a drawn two-column layout into a hidden one. *(§3.2)*
13. **Do not build a component in an app that duplicates a `packages/ui` export.** *(§3.4 rule 1)*
14. **Do not put a fetch, a query, or a base URL inside `packages/ui`.** *(§2.1 rule 4, §5.2)*
15. **Do not make a persona card clickable.** A clickable card containing links is an unresolvable nesting. *(§3.2)*

### 11.3 Data access and freshness

16. **Do not open a WebSocket, an `EventSource`, or a long-poll, and do not ask the gateway for a push surface.** Five independent reasons, each sufficient. *(03 principle 2; 30 §3.5, §2.3; 01 §14; 02 §4.1, §5; §5.4)*
17. **Do not use React Router loaders or actions for data.** Two caches over the same responses; the one that loses the race is the one on screen. *(§4.1)*
18. **Do not add a global state library.** There is no fifth kind of state. *(§5.7)*
19. **Do not hand-write a wire type, and do not call `fetch` directly in a `queryFn`.** *(09 §2.6 constraint 1; §5.1)*
20. **Do not derive a cross-domain value in the browser.** [30 §2.4] records that a composed priority score is *"[n]ot computed anywhere"*; computing it client-side relocates a prohibited derivation rather than avoiding it. *(30 §2.3 property 4; §5.3 rule 6)*
21. **Do not arbitrate anything with a wall clock** — not a poll interval, not a retry backoff, not a TTL countdown. *(**D29**; 09 §9.2 item 7; §5.4)*
22. **Do not ignore `Retry-After`.** A poll loop that ignores it converts a rate limit into an outage. *(30 §6.5, §6.3; §5.4)*
23. **Do not synthesize an `If-Match`, regenerate an `ETag`, or auto-resubmit after a `412`.** *(30 §4.6, §12.3 DO-NOT 25; 03 §7.2; **D16**; §5.6)*
24. **Do not optimistically update a queue row.** It is a claim about another service's state that the gateway explicitly declines to make. *(30 §2.3; §5.6)*
25. **Do not regenerate an `Idempotency-Key` on retry.** *(03 §4; §5.6)*
26. **Do not render zero, a bare dash, or an empty state for an unknown value.** *(30 §3.4; §5.5, §3.4 rule 3)*

### 11.4 Authorization, classification, and disclosure

27. **Do not gate a route on a role, hide a nav item, or filter a list client-side for authorization.** *(03 §15 obligation 7; 09 §8.1; 31 §6.5, §8; §4.2)*
28. **Do not read, store, decode, or refresh an access token in either app.** Both hold a cookie and no token. *(31 §4.1, §13 item 5; §6.3)*
29. **Do not trust the browser's assertion of who the user is, and do not send a claimed subject.** *(31 §13 item 15, §5.4; §6.3)*
30. **Do not hard-code a classification level, and do not default a missing `X-Classification` to `U`.** The demonstration is single-level *"by configuration, not by assumption"*; a hard-coded string removes the only place the console exercises the path. *(03 §12; 30 §7.2; §7.2 rules 2, 5)*
31. **Do not reorder, abbreviate, or alphabetize a marking list.** Reordering a marking string is a marking change. *(03 §7.3; §7.2)*
32. **Do not render `FOUO` or `U//FOUO`, in any form, including a test fixture.** *(03 §7.3; 10 §4.4 `FTH005`; §7.2 rule 3)*
33. **Do not omit `ContributorDisclosure` when nothing is restricted.** A disclosure that appears only when something is hidden is itself the channel. *(06 §5 rule 3; 27 §3.7; §7.4)*
34. **Do not compute or display `visible_weight_share`, `total_contributor_count`, `excluded_weight`, `coverage_fraction`, `score_full`, or any `*_of_total` figure — in the browser or anywhere.** *(27 §3.8; §7.4 rule 4)*
35. **Do not paraphrase, shorten, or truncate the `advisory` statement or the `contributor_disclosure` statement.** They are the marking, not a description of it. *(27 §8.1; 27 §3.7)*
36. **Do not present the readiness view as authoritative, and do not name anything with a term on [27 §8.3]'s list.** This is an accreditation concern, not a stylistic one. *(04 §5; 27 §8; §7.3 rule 4)*
37. **Do not render `contributing_factors` in causal language, and do not display a factor without an explicit stability floor.** *(**D23**; 03 §7.1; 09 §9.3 item 20; §7.5)*
38. **Do not branch on `tier`.** Branch on `reference_class`. *(**D7**, **D19**; 09 §9.3 item 21; §7.5)*

### 11.5 Accessibility

39. **Do not write `outline: none`, anywhere.** *(§8.2)*
40. **Do not put `role="img"` on an SVG containing interactive elements.** It prunes the subtree, which is what makes every map marker unreachable as drawn. *(§8.5; §13 correction 16)*
41. **Do not convey status by colour alone**, and do not treat a `Tooltip` as a label. *(SC 1.4.1; §8.3, §8.5)*
42. **Do not ship a map without its equivalent table.** *(SC 1.1.1, 1.4.1; §8.5)*
43. **Do not use a positive `tabindex`, and do not attach an activation handler to a non-interactive element.** *(§8.1)*
44. **Do not render text below `--fs-100`.** *(§2.3; §8.5)*

---

## 12. Definition of Done

**The shared Definition of Done in [09 §8](09-monorepo-and-conventions.md) applies in full and nothing is removed from it.** Following its instruction — each build document *"reproduces this checklist for its own component, adds component-specific items, and **removes nothing**"* — the shared items that a browser application satisfies vacuously or by not needing them are dispositioned explicitly below, with the reason, rather than left ambiguous. Copy §12.2 into `packages/ui/README.md`, `apps/web/README.md`, and `apps/practitioner/README.md` and tick it there.

### 12.1 Shared items requiring an explicit disposition

| [09 §8] item | Disposition |
|---|---|
| 8.1 OpenAPI 3.1 generated from code and committed; `x-substitution`, `x-side-effects`, `x-agent-eligible`, base path, RFC 9457, `Idempotency-Key`, `ETag`/`If-Match`, `X-Correlation-Id`, `X-Classification`, `changed_since`, cursor pagination, bulk fenced writes, deprecation headers | **Not applicable as a producer; binding as a consumer.** These apps expose no HTTP API. Every one of them is consumed: RFC 9457 → `ProblemDetail`; `Idempotency-Key` and `If-Match` → §5.6; `X-Classification` → §7.2; cursor pagination → the queue's cursor with its generation token ([30 §4.4]); `X-Correlation-Id` → **the console originates one per user action and sends it on every request**, so an operator-reported problem is traceable ([03 §4]; `[ESTABLISHED HERE]`) |
| 8.1 Authorization enforced in this service, never relying on the gateway | **Not applicable, and asserting otherwise would be the defect.** A browser is not an enforcement point (§4.2, §11.4 item 27) |
| 8.1 Every timestamp RFC 3339, UTC, explicit offset; no naive datetime | **Binding on display.** The console renders server-supplied instants in the operator's local zone **with the zone named**, and never constructs a timestamp of its own except a monotonic delta (§5.4) |
| 8.2 Events — envelope, clock block, topics, schema registry, AsyncAPI, catalog equality, no wildcard subscriptions | **Not applicable.** Neither app publishes or consumes an event. Neither is a topic consumer; [09 §9.2 item 15]'s prohibition on non-service topic consumers applies with equal force to a browser |
| 8.3 Outbox, inbox, antecedent rule, `(producer, monotonic_seq)` ordering, read-model rebuild, read-model lag on `/readyz` | **Not applicable — no state, no store, no outbox.** But two of its obligations arrive as consumed data and are binding: the queue's projection lag is rendered from `queue_freshness` (§10.2 `ui-queue-freshness-rendered`, [30 §4.7]), and **monotonic-clock discipline binds every timer** (§5.4, §11.3 item 21) |
| 8.3 Conflict policy declared per aggregate | **Not applicable.** No aggregate is owned |
| 8.4 One logical database; Alembic migrations; provenance for derived values; classification labels with `inherited_from`; a declared purge path | **Database and migrations not applicable.** **Provenance and classification are binding**: every operator-visible figure links to its decomposition ([04 §5]) and its methodology ([27 §8.1]), and `inherited_from` is rendered rather than dropped (§7.2). **Purge:** neither app is a store. The two durable preferences (§5.7) are `localStorage` keys under one namespace, and a sign-out clears them — stated so that "the console has a store" is answered rather than assumed |
| 8.5 Conformance suite collected unmodified from `packages/contracts/conformance/<slug>/` | **Not applicable — no slug and no conformance suite exists for a UI.** §10.2's named tests are this document's equivalent, and they are named contractually for the same reason [09 §8.5] forbids editing a shared test: 51 and 52 add and remove nothing |
| 8.5 Consumer-driven tests contributed into every producer's suite | **Satisfied by not needing it, and the reason is [30 §1.3].** The console consumes the gateway's HTTP surface, not events; the gateway's own suite covers it |
| 8.5 Synthetic reference dataset for deterministic runs | **Adopted.** Component and route tests run against committed fixtures derived from the [06 §7] envelope — twelve assets, the three domains — so the map's twelve markers and the fleet rollup are exercised at the specified scale |
| 8.6 `check_event_catalog.py`, Helm lint/template/unittest, NetworkPolicy, non-root UID 65532, read-only root filesystem, no install at container start, digest pins, `/healthz` `/readyz` `/metrics`, `.env.example`, structured JSON logging, Argo CD Application | **Mixed.** `apps/web` ships as static assets behind program ingress and has no pod of its own, so the container items fall to whatever serves it. `apps/practitioner` **is** a container, but **Domino deploys it** and [09 §9.5 item 28] forbids deploying into Domino's namespaces; its image nonetheless honours *"no package or source installation at container start"* ([09 §9.5 item 25], **D26**, which [02 §4.1]'s own engineering called categorically incompatible with air gap) and pins by digest. `.env.example` is **binding on both** — every `VITE_*` variable is enumerated with no real value. Structured logging is **not applicable**: a browser writes no log line, and [31 §13 item 5] forbids a token ever reaching one |
| 8.7 README, ADR per deviation, `[OPEN]` items recorded, no silently varied `[ESTABLISHED HERE]` convention | **Binding in full.** Every `[ESTABLISHED HERE]` in this document is a convention two apps share; varying one breaks the sibling, not just the varier |

### 12.2 UI-specific items

**Tokens and the shared package (§2)**

- [ ] `packages/ui` exists, is in `pnpm-workspace.yaml`, and **[09 §3.1] and [09 §3.2] have been amended** to include it *(§2.1; §13 correction 1)*
- [ ] `tokens.css` carries every token of §2.2–§2.5 in **both** theme blocks, with values matching the wireframe byte for byte
- [ ] `ui-tokens-no-drift`, `ui-theme-blocks-agree`, `ui-token-set-complete`, `ui-no-literal-values`, `ui-font-size-floor` green
- [ ] `packages/ui` has **no** `react` dependency outside `peerDependencies`, and `tokens.css` imports nothing *(§2.1 rules 2–3)*
- [ ] No component fetches; no component imports from `apps/*` *(§2.1 rule 4)*

**Components (§3)**

- [ ] The headless-primitive package is pinned, the **[VERIFY]** of §3.1 is discharged, and the pull request records which packaging form was used
- [ ] Every component in §3.5's inventory exists; **no component outside it exists** *(§11.2 item 12)*
- [ ] The five §3.3 gaps are hand-built to the stated ARIA patterns, and each carries a comment naming the gap
- [ ] No charting library, no icon library, no component library *(§3.1, §3.3 gap 4, §11.1 item 5, §11.2 item 9)*

**Routing (§4)**

- [ ] The route tree matches §4.2 exactly; segments are the [03 §3.1] slugs verbatim; the two carve-outs are the only two
- [ ] `ui-no-role-gated-route` green. No `<RequireRole>` exists *(§11.4 item 27)*
- [ ] Sheets 08 and 09 have **no route**, and the two `ExternalLaunch` cards are the only outbound links *(§4.3)*
- [ ] Title, focus movement, and the polite announcement fire on every route change *(§4.4)*

**Data and freshness (§5)**

- [ ] Every read goes through `openapi-fetch` over generated types; `ui-no-hand-written-wire-type` green
- [ ] `freshness.ts` carries §5.4's table as data, each row citing its derivation
- [ ] `ui-no-streaming-transport`, `ui-no-wall-clock-timers`, `ui-retry-after-pauses-poll`, `ui-no-cross-view-derivation`, `ui-zod-validated` green
- [ ] `ui-adjudicate-sends-if-match`, `ui-idempotency-key-stable-across-retries`, `ui-412-requires-reconfirm` green
- [ ] All six `FragmentOutcome` values are handled explicitly; `ui-degraded-view-renders-notice`, `ui-kpi-never-renders-zero-for-unknown`, `ui-classification-fault-is-not-degraded` green *(30 §3.4, §7.2)*
- [ ] Loading, empty, and unknown are three components and are never conflated *(§5.5)*

**Boundary (§6)**

- [ ] `apps/web` bakes `base`; `apps/practitioner` uses `base: "./"`, `assetsDir: "static"`, and a runtime `basename`; both `vite.config.ts` files carry the [02 §4.1] citation for the divergence *(§6.1, §6.2)*
- [ ] `ui-practitioner-basename-from-runtime` green
- [ ] Neither app reads a token; every request is cookie-borne *(§6.3; §11.4 item 28)*
- [ ] The practitioner credential path of §6.3 is either implemented as amended or **explicitly recorded in the README as blocked**, with §13 correction 10 filed *(§6.3)*
- [ ] The iframe rules of §6.5 hold: no `window.top`, no external subresource, host-supplied theme honoured
- [ ] Deep-link fallback configured in both serving paths *(§6.4)*

**Disclosure (§7)**

- [ ] `ClassificationBanner` **and** `ClassificationFooter` render on every route, data-driven, with `inherited_from` disclosed *(03 §7.3; 30 §7.3)*
- [ ] `AdvisoryBanner` renders from body **or** header, verbatim, persistent, in the annotation voice, with `methodology_ref` reachable *(27 §8.1–§8.4)*
- [ ] `ContributorDisclosure` renders in both the `true` and `false` cases, with `statement` verbatim, and both null-score reasons distinct *(06 §5; 27 §3.7, §3.9)*
- [ ] `ui-classification-banner-is-data-driven`, `ui-classification-footer-present`, `ui-no-retired-markings`, `ui-advisory-must-be-surfaced`, `ui-advisory-from-header-only`, `ui-fs-term-001`, `ui-disclosure-always-rendered`, `ui-forbidden-disclosure-fields`, `ui-null-score-reasons-distinct`, `ui-uncalibrated-never-zero`, `ui-no-tier-branch`, `ui-factors-not-causal` green
- [ ] `ui-learned-sort-label`, `ui-approximate-time`, `ui-queue-freshness-rendered`, `ui-non-program-evidence-not-collapsible` green *(30 §4.4, §4.7, §2.4)*

**Accessibility (§8)**

- [ ] Every test named in §8.1–§8.6 green, and `a11y-axe-clean` reports zero `serious` or `critical` violations across `packages/ui` and every `apps/web` route
- [ ] §8.4's contrast table is executable from `contrast.fixture.ts` and green, **including the `.chip` label fix** *(§8.4; §13 correction 14)*
- [ ] The focus-visible rule is generalized to every focusable element *(§8.2; §13 correction 13)*
- [ ] The map ships with focusable, labelled markers, `role="group"`, a `<figcaption>`, a required `EquivalentTable`, and ≥ 24 × 24 px hit areas *(§8.5, §8.6)*

**Persona (§9)**

- [ ] `ui-every-role-has-a-card`, `ui-hub-no-auto-redirect`, `ui-empty-roles-renders-all-cards`, `ui-external-launch-configured` green
- [ ] All five cases of §9.3 implemented; `authority_classes: []` is a working state and not an error
- [ ] No realm role invented for `VR` or `RE` *(31 §2.4, §13 item 12; §9.1)*
- [ ] The session-operation gap of §9.2 is either satisfied by the amended operation or **recorded in the README as the interim**, with §13 correction 7 filed

**Governance**

- [ ] Corrections **1–18** of §13 each filed against their document with an owner. **Corrections 1, 2, 3, 7, and 10 block a complete `apps/web`** and are recorded as blocking
- [ ] Open questions **UI-OQ-1 … UI-OQ-10** recorded in each README as local resolutions where an app had to proceed *(§14; 09 §8.7)*
- [ ] Every deviation from this document carries an ADR under `docs/adr/` *(09 §8.7)*
- [ ] No `[ESTABLISHED HERE]` convention in this document has been silently varied by 51 or 52 *(09 §8.7)*

---

## 13. Corrections to source documents

Found while reconciling, following [09 §11](09-monorepo-and-conventions.md)'s convention: each is a **defect in the cited document or in the approved wireframe**, not a decision of this one. **None is applied here.** Corrections 1, 2, 3, and 7 block a complete `apps/web`. Correction 10 is now **resolved** — see its row below.

| # | Document | Defect | Correction | Status |
|---|---|---|---|---|
| 1 | **09 §3.1, §3.2, §2.6** | The monorepo tree, the per-directory governance table, and the pnpm workspace scope (*"spanning `apps/*` and `packages/ts-common`"*) have no place for a shared UI package, yet two apps must share tokens and components and `packages/ts-common` must stay React-free for the same reason [10 §9.4] keeps `canonical-schemas` framework-free | Add `packages/ui/` to §3.1's tree, a row to §3.2 governed by this document, and `packages/ui` to §2.6's workspace scope and to `pnpm-workspace.yaml` | **Blocking.** Not applied; flagged. §2.1 |
| 2 | **27 §7, and the [06 §2] metric generally** | [27 §7] determines that the definition and authoritative computation of **warning lead-time coverage** *"belong[s] to the cross-cutting effectiveness-analytics path, not here,"* and [27 §7.4] provides only the `GET /risk-flags/transitions` **ingest** feed. **No service, no build document, and no operation owns or serves the figure** — yet [06 §2] makes it the program's primary effectiveness metric and **WF sheets 01 and 01B both render it as a headline KPI** (*"Warning Lead-Time Coverage 64%"*, *"71%"*). The console has nothing to call | Assign the effectiveness-analytics path a build document and an operation, **or** remove the KPI from sheets 01 and 01B. Additionally, when it exists, [27 §7.5]'s presentation rules bind it — the lead-time distribution and denominator, the chance reference and flag rate, the achievable ceiling, and *"[n]ever viewer-filtered"* — and **a bare percentage as drawn violates all four** | **Blocking for sheets 01 and 01B.** Not applied; flagged. §7.4 rule 6 |
| 3 | **04 §2 / 20 (`Asset`), and WF sheet 01** | **No aggregate, event, or operation in the corpus carries a geographic position for an asset.** [04 §2]'s `Asset` carries *"UIC, domain, operational status, OFRP phase"*; [20]'s model adds `hull_or_tail`, `class_id`, `uic`, `operational_status`, `ofrp_phase`. WF sheet 01's fleet map plots nine markers with no data source, and [30 §3.2]'s `fleet_overview` has no position fragment | Either add a demonstration-only position to the synthetic dataset with an operation exposing it, or accept that the map is rendered from a build-time static table in `apps/web`. **§3.5 adopts the second as the interim** and it requires no contract change, consistent with WF's own note that *"[p]ositions are generated for this demonstration only — document 07 records no public source for real fleet disposition"* | **Blocking for the map.** Interim implemented in §3.5; flagged |
| 4 | **WF sheet 01 map key** | The key defines a `neutral` marker as *"no recent contact,"* but **no field in the corpus expresses recency of contact** for an asset | Either define the field, or read `neutral` as *unknown* — the `open_casrep_risk` fragment returning `empty`/`unavailable` for that asset, which is [30 §3.4]'s render-the-gap rule per marker. **§3.5 adopts the second** | Interim implemented in §3.5; flagged |
| 5 | **30 §3.4** | The composed-view envelope's `as_of` member appears in the §3.4 example and **its semantics are defined nowhere** — it could be the time the fan-out started, the time it completed, or the oldest contributing fragment's currency. A UI must label it, and the three readings warrant three different labels | Define `as_of` in §3.4 | Not applied; flagged. §5.3 rule 5 labels it conservatively as *"composed at"* meanwhile |
| 6 | **WF `svg.aor` label classes, `.nav-shell .side .group-label`** | Font sizes of 7 px, 7.5 px, 8.5 px, and 9.5 px. These are drafting-drawing scale and are not readable in a production console | Raise all five rules to the 10 px floor of §2.3. The map's `viewBox` may need widening as a consequence | Applied in §2.3 as a token rule; the wireframe needs the edit |
| 7 | **30 §8.1 and 30 OQ-9 versus 31 §4.1** | [30 OQ-9] declines a server-side per-role queue projection because *"[t]he UI filters by `authority_class` using the roles it already holds from its own token."* **[31 §4.1] establishes that `apps/web` holds no token** — *"the USER'S ACCESS TOKEN NEVER LEAVES THE SERVER. `apps/web` holds a session cookie."* No operation returns the session's identity: [30 §8.1]'s owned surface has none, and [31 §8]'s `GET /principals/{sub}` needs a `sub` the console cannot obtain. **Additionally, no logout mechanism appears anywhere** — no RP-initiated logout, no back-channel logout, no `end_session_endpoint` in [31] or [30] | Add `GET /api/v1/gateway/session` (§9.2's shape) and a sign-out operation to [30 §8.1]; correct [30 OQ-9]'s premise; state the cookie's attributes, CSRF strategy, and session store, which [31 §1.3] deferred to this wave but which are the gateway's to specify | **Blocking the Persona Hub and the queue's default filter.** Interim in §9.2; flagged |
| 8 | **WF sheet 10** | [30 §4.5] defines roughly twenty named query parameters and three sort orders for the queue, and [30 OQ-9] makes client-side `authority_class` filtering the sanctioned mechanism — **but sheet 10 draws no filter or sort control at all**, so the queue as drawn cannot be filtered | Draw the filter and sort controls on sheet 10. §3.2 names `Select` as the primitive; the layout is [51](51-operator-console.md)'s | Not applied; flagged |
| 9 | **WF sheet 00** | The topbar renders `search asset, NIIN, hull…`, implying free-text search. **No such operation exists and one is explicitly declined:** [30 OQ-7] — *"Does the operator UI need a cross-sub-application proposal search — free-text over rationale or payload? **Not offered.** Structured filters only"* — and [03 §4] forbids *"[a]ny general-purpose query language on the public surface"* | Relabel the affordance as a **typed identifier lookup** over the named filters that do exist (`GET /assets`, `GET /parts?niin=`), which is what §3.2's `IdentifierLookup` implements. A placeholder promising search the platform declines to offer is the kind of expectation that is expensive to withdraw | Not applied; flagged. §3.2, §3.3 gap 3 |
| 10 | **31 §2.2, §5, §8** | `apps/practitioner` had **no client ID, no token-acquisition path, and no specified credential** for calling the gateway. [31 §2.2] gives a Domino-hosted app a *"Domino session cookie"* traceable to a FATHOM `sub` by brokering, and then warns that federation *"does not put caller identity on a Domino Endpoint invocation … [t]hat gap … must not be reasoned away by pointing at federation."* [28 §2] and [42 §13.3] both place practitioner surfaces there regardless | **[AMENDMENT — resolved, not by extending [31 §5.4]'s two-credential shape as originally proposed.]** A security review found that extension defective (one header name validating two structurally incompatible credentials). [31 §5.8] was corrected instead to a token-exchange operation, `POST /api/v1/auth/practitioner-exchange` — a settled mechanism, not an interim | **Resolved.** `apps/practitioner`'s write path is authorized, not blocked — §6.3 |
| 11 | **WF, all sheets** | The classification marking appears only as the masthead `.classbar`. [03 §7.3] requires it in **banner and footer**: *"[m]inimum marking is `CUI` in both banner and footer."* No sheet shows a footer marking | Add a classification footer to the shell | Applied in §3.5 / §7.2 as a required component; the wireframe needs the edit |
| 12 | **WF sheets 01, 01B** | The suppressed-score case of [27 §3.9] — `score: null` with `suppression_reason` `all_contributors_restricted` or `no_contributors`, at HTTP 200 — **is not drawn**, and it is the case where rendering `100` *"presents a fully compartmented, possibly failed asset as perfectly ready"* | Draw both null-score states on sheets 01 and 01B | Specified in §7.4 rule 3; the wireframe needs the edit |
| 13 | **WF `.btn:focus-visible`** | The focus indicator is defined on `.btn` alone. Every link, input, tree node, sort control, and map marker would fall back to the browser default or to nothing | Generalize the rule to every focusable element | Applied in §8.2; the wireframe needs the edit |
| 14 | **WF `.chip.warning`** | `--warning` on `--warning-bg` is **3.86 : 1** in the light theme against WCAG 2.2 AA's 4.5 : 1 for normal text, and `.chip` is 10.5 px uppercase — normal text by definition | Render every chip's label in `--ink` and reserve the status colour for the dot. All eight combinations then exceed 10.6 : 1 using only existing tokens | Applied in §8.4; the wireframe needs the edit. The alternative is UI-OQ-5 |
| 15 | **WF `.topbar .search`** | The lookup input's border is `--line-soft`, **1.45 : 1** against `--paper`, far below SC 1.4.11's 3 : 1 for a boundary that identifies an interactive component | Interactive boundaries use `--ink-soft` (6.72 : 1) at minimum; `--line`/`--line-soft` remain decorative and structural | Applied in §8.4; the wireframe needs the edit |
| 16 | **WF sheet 01, `<svg class="aor" role="img">`** | `role="img"` prunes the SVG subtree from the accessibility tree, while the same sheet states *"[c]lick any marker → sheet 01B."* **Every marker is therefore unreachable to assistive technology and to the keyboard as drawn.** Marker status is additionally encoded by colour alone (shape encodes domain), against SC 1.4.1 | `role="group"` with `aria-labelledby`, a `<figure>`/`<figcaption>`, focusable and named markers, `aria-hidden` scenery, and a **required** equivalent table — which on sheet 01 is the already-drawn Risk-flags box | Applied in §8.5; the wireframe needs the edit |
| 17 | **WF sheet H footnote** | *"[T]he roster is exactly document 03 §7.2.1's six adjudicating authority classes … plus two review-only roles (Ship's Force Maintainer-as-reviewer, Reliability Engineer)."* **Ship's Force Maintainer *is* `maintainer`**, one of the six, so the footnote double-counts it — and it omits **Vehicle Readiness Officer**, which is the card that genuinely has no authority class. Six roles map to six cards; `VR` and `RE` map to none | Restate as: six authority classes → six cards; two cards (`VR`, `RE`) are self-selected personas with no realm role | Not applied; flagged. §9.1 |
| 18 | **31 §6.4** | The generated authority matrix covers `anomaly_tag`, `work_candidate`, `requisition`, `interval_change`, `redesign_case`, and `configuration_change`, and **`security_officer` appears in no cell** — yet [03 §7.2.1]'s minimum-authority table has `purge` / `rewrap` rows requiring `security_officer` + dual control at item/asset scope and a `fleet_authority` counter-signature at class/fleet. WF sheet 11 is built entirely on those rows. A console rendering enablement from that matrix would show the Security Officer as authorized for nothing | Add the `purge` / `rewrap` rows to §6.4's matrix. Related, and already noted by [31] itself: §2.4 says six while §2.5, §3.1 rule 3, and T-7 still say *"five"* | Not applied; flagged. §9.1 |

---

## 14. Open questions

Recorded rather than resolved locally, following [30 §15] and [31 §15]. Numbered `UI-OQ-n`. An app that must proceed records its local resolution in its README ([09 §8.7]) and does not treat it as settled.

| # | Question | Impact if unresolved | Interim position |
|---|---|---|---|
| **UI-OQ-1** | **Session cookie attributes, CSRF strategy, and session store** for the gateway BFF. [31 §1.3] deferred *"session storage … for `apps/web`"* to this wave, but the mechanism belongs to the gateway, which specifies none | The console cannot state its own security posture, and a reviewer cannot assess it | `HttpOnly`, `Secure`, `SameSite=Lax` with a double-submit CSRF token on unsafe methods, assumed. **Raise for [30] to specify.** §13 correction 7 |
| **UI-OQ-2** | **Logout.** No RP-initiated logout, back-channel logout, or `end_session_endpoint` appears in [31] or [30] | An operator cannot end a session on a shared bridge workstation, which is an accreditation question, not a convenience | The console renders a sign-out control that clears local preferences and calls a gateway endpoint to be defined. **Raise for [31] and [30].** §13 correction 7 |
| **UI-OQ-3** | **Notification surface.** [33 §6.4] states its presentation rule is *"binding on … `apps/web`,"* including the `delay` block, `dispersion_ms` qualifiers, and `occurred_at` sort — but **no wireframe sheet renders a notification list**, and [33] has no route here | The rule has no surface to bind, and the first author to draw one may not know it exists | The rule and its test (`ui-occurred-at-headline`) are specified in §5.6 so they are ready. **Raise with [51] whether a notification surface is in scope** |
| **UI-OQ-4** | ~~**The practitioner credential path** (§6.3, §13 correction 10)~~ **[RESOLVED.]** `apps/practitioner` can adjudicate — [31 §5.8]'s token-exchange mechanism (§6.3) landed, superseding the two-credential shape this question originally weighed | N/A — `apps/practitioner` is a full read-and-write surface, per its own authority | Closed. No interim position remains |
| **UI-OQ-5** | **The two tight contrast ratios.** `.chip` label colour (§8.4's fix, 3.86 : 1 as drawn) and `--annotation` on `--annotation-bg` (4.52 : 1, serif italic at the tightest ratio in the system) | Either a documented AA failure ships, or a token the user approved changes | §8.4's uniform `--ink` chip label is specified. The alternative — keep coloured chip labels and accept the documented failure — is recorded here for the program to choose. **No token value is changed either way** |
| **UI-OQ-6** | **Tree typeahead.** The ARIA tree pattern permits type-to-find; no sheet requires it, and an ~8,400-item configuration tree ([06 §7]) is where it would matter most | A large tree may be impractical to navigate by arrow key alone | Not implemented. Revisit with [51] once the tree's real depth and fan-out are known |
| **UI-OQ-7** | **End-to-end testing.** No E2E tool is named anywhere in the corpus; [09 §10 item 8] already raises load and performance testing for assignment | Cross-route flows — persona → sheet → drill-down → adjudication — are untested end to end | None adopted (§10.1). **Raise for assignment alongside [09 §10 item 8]** |
| **UI-OQ-8** | **Copilot surface.** [40 §1.5] shows *"maintainer types a question in `apps/web`"* and the answer rendered *"with every citation resolvable,"* and [40 §1157] records that **no agent-invocation operation exists anywhere in the corpus** — *"`apps/web` has nothing to call."* **And no wireframe sheet draws a Copilot panel** | An entire agent's user interface is unspecified and uncallable | No Copilot component is specified here, because the wireframes have none and §11.2 item 12 forbids inventing one. **Raise with [51] and [40]'s correction 13** |
| **UI-OQ-9** | **Sheet-04 what-if inputs.** WF sheet 04 shows *"adjust usage / deferral inputs → recomputed RUL (Domino Endpoint)"* inside a placeholder. The call is `POST /api/v1/gateway/inference/{domino_endpoint_name}` [30 §5.6], with a **10 MB payload ceiling and a 60 s recommended timeout** [02 §4.3], and [02 §4.3] also records that *"[a] timed-out request is not cancelled"* | The one interactive model surface in the console has no drawn form and a hostile latency profile | The primitives are named in §3.2's not-adopted table. **Raise with [51]**; whatever is drawn must show the request's own progress and must not retry a timeout |
| **UI-OQ-10** | **Print and export.** A drafting-sheet console invites printing, and a readiness figure that reaches paper without its advisory statement and classification markings is the exact failure [27 §8] and [03 §7.3] exist to prevent | A screenshot or print is the most likely way an advisory figure is mistaken for a report | Not specified. If print is in scope, `@media print` must retain the classification banner **and** footer, the advisory statement, and the contributor disclosure, and must state that the page is not a report. **Raise with [51]** |

---

## 15. Quick reference for an implementing agent

Read in this order before writing any UI code:

1. **This document** §2 (tokens), §3 (components), §4 (routes), §5 (data), §7 (the three disclosure components), §8 (accessibility), §11 (what not to do).
2. **[09](09-monorepo-and-conventions.md)** §2.6 (toolchain — unchanged), §3.1 (layout), §8 (Definition of Done), §9 (the thirty-two prohibitions, which apply in full).
3. **[30](30-gateway.md)** §3.2 (the four composed views and their fragments), §3.4 (the envelope and the six outcomes), §4.5 (the queue's fields, filters, and `queue_freshness`), §4.6 (claim and adjudicate), §6.5 (rate limiting).
4. **[31](31-auth.md)** §2.4 (the six roles), §4.1 (the BFF login — read step 1 twice), §8 (the two advisory operations).
5. **[03](../architecture/03-integration-contracts.md)** §4 (conventions), §7.1 (`FailurePrediction`), §7.2 / §7.2.1 (`Proposal`, authority), §7.3 (`ClassificationLabel`).
6. **[27](27-fleet-status.md)** §3.7–§3.9 (disclosure), §7 (the coverage metric's ownership), §8 (advisory framing) — before rendering any readiness figure.
7. **[02 §4.1](../architecture/02-domino-platform-assessment.md)** — before touching `apps/practitioner`.
8. **[06 §7](../architecture/06-demo-decisions-and-assumptions.md)** for any quantity. Invent none.
9. **The wireframe**, [`docs/design/operator-console-wireframes.html`](../design/operator-console-wireframes.html), for the sheet you are building.

Then: §12.2 is the checklist you copy into the README and tick, and §13 is the list of things you will discover are missing — they are already known, and they are not yours to resolve locally.

