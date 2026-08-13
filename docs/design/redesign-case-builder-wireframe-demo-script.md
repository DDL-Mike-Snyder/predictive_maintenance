# Demo script — "Redesign Case Builder" wireframe (Sheet 09)

**Correction on source:** the wireframe lives in
`docs/design/operator-console-wireframes.html`, section `id="s9"`
("SHEET 09 / SYSTEM TEST & DESIGN ADVISORY") — not in
`docs/architecture/01-system-architecture.md`, which only lists
"Redesign Case Builder" as one row in the §8.1 agent-inventory table
(no wireframe there). This script walks the actual HTML mockup.

**What this is, and isn't.** This is a **static wireframe walkthrough**
for a design review — there is no running software behind these buttons,
and clicking "Approve" or "Draft" does nothing. That's deliberate:
`docs/build/51-operator-console.md` explicitly designs **no** `apps/web`
route or component for this sheet — it's specified as an `ExternalLaunch`
stub that hands off to `apps/practitioner` (a separate, not-yet-built
surface), never as a screen `apps/web` implements itself. So this HTML
mockup is the complete, correct artifact to demo for *this exact screen*
— there's nothing further along to show instead. (If you're looking for
the separate, simplified *working* demo built earlier for a redesign-
case-builder-flavored screen, that lives in `apps/web` per
`docs/demo/redesign-case-builder-demo-plan.md` — a different, in-repo
stand-in built for a different purpose. Don't conflate the two in front
of an audience; say so if asked.)

**Setup:** open `docs/design/operator-console-wireframes.html` directly
in a browser (no server needed, it's a self-contained static file).

---

## The story this script tells

The wireframes let you show a causal finding travel from adjudication
(Sheet 08, Reliability Engineer) into a costed business case (Sheet 09,
PEO/Design Engineer) into the cross-cutting adjudication queue (Sheet 10)
— the same evidence, cited verbatim, at every stop, with the system
refusing at every step to quietly turn "evaluate this" into "do this."
That refusal is the actual point of the whole sub-application (doc 04
§10), and it's visible directly in the mockup's own copy, not just in the
architecture doc's prose — this script is built to make sure you land on
those exact lines.

---

## Step-by-step

### 1. Open at the Persona Hub (Sheet 00) — set up who's who

Scroll to the top of the file (Sheet 00, the Persona Hub). Find two
cards:

- **Reliability Engineer** — *"Adjudicates causal failure-mode
  hypotheses"* — primary button **Open Hypothesis Adjudication**, with a
  secondary link to **Redesign Case Builder**.
- **PEO / Design Engineer** — *"Reviews redesign business cases and
  dependency impact"* — primary button **Open Redesign Case Builder**,
  with secondary links to **Hypothesis Adjudication** and **Adjudication
  Queue**.

**Say:** "Two different people, two different jobs, on the same causal
finding. One decides whether a hypothesis about *why* something is
failing is well-supported enough to act on. The other decides whether
acting on it is worth a detailed cost estimate — and neither of them is
the same as *approving a redesign*. That distinction is the whole reason
this sub-application exists, and it's enforced by which buttons the
mockup gives each of them, not just by a policy someone wrote down."

Click **Open Hypothesis Adjudication** to go to Sheet 08 first — the
finding needs to exist before Sheet 09 can cite it.

### 2. Sheet 08 — Hypothesis Adjudication (Reliability Engineer)

Point at the sheet note: *"Outputs are **adjudicated hypotheses**, never
automated conclusions — a strength scale is shown, not a bare 'confidence'
number."*

Point at the open-hypotheses table: **ELP — external leakage, process**,
method *survival + covariates*, evidence strength shown as a **2-of-3
filled bar** (not a number like "67%"), state **pending adjudication**.

**Say:** "Notice there's no single confidence percentage anywhere on this
row — evidence strength is a small, discrete scale, because a bare number
invites treating a statistical association as more certain than it is.
This bar is exactly what gets carried forward, unchanged, to the next
sheet — watch for it."

Point at the adjudication panel below: chip **"confounding check:
propensity modeled"**, then the two buttons — **Approve → admit as causal
feature** / **Reject — retain as negative finding**.

**Say:** "Even rejection is a first-class outcome here, not a deletion —
'retain as negative finding' means a hypothesis that didn't hold up stays
in the record, so nobody re-investigates the same dead end next year."

Click through (or just narrate) the Reliability Engineer approving it —
this is the finding Sheet 09 will cite.

### 3. Sheet 09 — Redesign Case Builder (PEO / Design Engineer)

Navigate to `#s9` (or click **Redesign Case Builder** from the Persona
Hub / Sheet 08's own cross-link). Read the sheet note aloud first, it's
the thesis statement for the whole screen:

> *"This sub-application assembles a decision package, never a decision.
> Causal findings are cited at their original evidence strength — never
> upgraded."*

Walk the five boxes in order:

**a. Dossier — NIIN 013479201**
- 6 field failures over 24 months
- Causal finding: **ELP hypothesis**, chip **"S2 — plausible,
  unreplicated"** — *"cited verbatim from Failure Intelligence — never
  re-banded"*
- Test data: chip **"no qualification record found"** (styled critical —
  a gap, not a soft note)

**Say:** "That 'S2 — plausible, unreplicated' label is the exact same
2-of-3 evidence bar you just saw the Reliability Engineer adjudicate on
Sheet 08 — carried here word for word. This system could not re-describe
that finding as 'strong' or 'confirmed' even if doing so made a cleaner
slide, and the mockup is written to make that visible, not just true in
the backend."

**b. Dependency impact — 72% graph completeness**
- Point at the small node/edge diagram (one dashed node/edge — an
  unverified link).

**Say:** "72%, not 100 — and the dashed line is a real design choice:
whatever's still unverified in the blast radius is shown as unverified,
not silently rounded up to complete. A redesign case built on an
incomplete graph says so, visibly, right where the number lives."

**c. Cost estimate — two-stage**
- Chips: **parametric: qualified** → **gate: priority ≥ threshold** →
  **detailed: pending**

**Say:** "Three stages, left to right, and the third one hasn't run yet.
A cheap estimate qualifies the case first; only a case that clears a
priority gate gets the expensive, detailed roll-up. You're looking at a
case that's cleared the cheap check and is waiting on the gate — not one
that's been fully costed yet."

**d. Recommendation — required, never optional (case v3)**
- Chip: **redesign_warranted_for_evaluation**, with the line right next
  to it: *"— warrants an evaluation, not a redesign. Never rendered as
  'recommended' or 'approved.'"*
- **Limitations**: dependency graph bounded below (28% of the
  neighbourhood unresolved), no qualification record for this NIIN's
  current configuration.
- **Evidence gaps**: no unstructured engineering evidence available
  (cites finding D38), detailed cost roll-up not yet run.
- Closing note: *"Publication releases this package to a design authority
  for evaluation. **It is not itself a redesign decision.**"*

**Say — this is the single most important beat in the whole demo:**
"Look at the label again: `redesign_warranted_for_evaluation`. Not
'redesign recommended.' Not 'approved.' And right beside the headline
chip, in the exact same box, is a list of everything this case doesn't
yet know — an incomplete dependency graph, no qualification record, no
engineering-narrative corroboration, no detailed cost yet. The system
is never allowed to present a confident recommendation without also
showing you, in the same breath, what it doesn't know. That pairing is
mandatory in the underlying data model — the wireframe is showing you a
UI that literally cannot omit it."

**e. Adjudicate — class scope, dual control**
- Warning chip: **"⚠ non-program evidence present"** — *"review the
  retrieved-content citations before signing"*
- Buttons: **Approve — signature 1 of 2** / **Reject**
- Footnote: *"Adjudicated through the unified queue's proposal detail
  (sheet 10) — this panel and sheet 10's are the same call, and either
  may carry the second signature."*

**Say:** "Two things stacked here. First, this is flagged 'class scope' —
meaning if this redesign gets approved, it doesn't just affect one ship,
it potentially applies fleet-wide — and that's exactly the blast radius
where the system requires a **second, independent signature**, not one
person's approval. Second: the design engineer isn't the one who signs
alone even once — clicking Approve here is signature 1 of 2, and the
second signature can come from this exact panel or from the cross-cutting
queue on the next sheet. It's the same adjudication either way, not two
separate approvals."

### 4. Sheet 10 — Unified Adjudication Queue (close the loop)

Navigate to `#s10`. Point at the pending-proposals table's third row:

`redesign_case | Design Advisory | design_authority | asset | proposed`

**Say:** "This is the same case you just walked through on Sheet 09,
now sitting in the one queue every adjudicator across the whole platform
checks — proposed, waiting for a `design_authority` to act. Whether that
person works from this queue or from Sheet 09 directly, it's the same
underlying decision, in the same state, with the same evidence behind
it. There's exactly one place this case can be, not two conflicting
copies of it."

---

## Anticipated questions (have an answer ready)

- **"Why can't the design engineer just approve this themselves?"** —
  Because at class/fleet blast radius, one signature isn't enough by
  design (dual control) — and separately, an agent that assembled this
  package (if one had) is barred from ever being the one who adjudicates
  it, on either end, no exceptions.
- **"Why show a confidence bar instead of a percentage?"** — A discrete
  strength scale is harder to over-read as false precision than a number
  like "67% confidence," and it's the same scale used consistently from
  the moment a hypothesis is first adjudicated (Sheet 08) through to the
  business case that cites it (Sheet 09).
- **"What happens after the second signature?"** — Publication releases
  the package to a design authority for evaluation — it is explicitly
  **not**, itself, a redesign decision. The actual redesign action (a
  contract, a configuration change) happens through acquisition and
  configuration-management processes entirely outside this system.
- **"Is this screen actually built anywhere?"** — No, and that's
  intentional: `51-operator-console.md` scopes this sheet as an external
  hand-off to a not-yet-built practitioner surface, not something the
  operator console (`apps/web`) implements. This wireframe is the design
  intent; a separate, simplified working stand-in exists elsewhere in the
  repo for a different, demo-speed purpose (see the note at the top of
  this file) — don't present that as "this screen, built."
