# Redesign Case Builder — 2.5-hour demo build plan

**Goal:** a live, click-through demo of the Redesign Case Builder pipeline
(`docs/build/42-redesign-case-builder.md`, backed by
`docs/build/28-design-advisory.md`) — candidate list → qualify → dependency
impact + parametric cost + gate decision → (if the gate passes) draft a
case with an LLM-composed narrative → submit a proposal — running inside
this repo, in **2.5 hours**, split across **five builders, each running
their own Claude Code instance on their own computer, plus one Executive
Review role that adversarially checks the integrated result before it's
called demo-ready.**

This is a demo, not a production build. It deliberately does not attempt
most of what 42/28 actually require (see "What we are explicitly NOT
building" below) — those documents describe a real system with dual
control, an agent runtime with a session store and checkpointing, a
tool-server MCP surface, real auth delegation, and event publishing. None
of that fits in 2.5 hours across five people who've never worked in this
codebase together before. What we *are* building is real, working code
against the real data model and the real API shapes those documents
define — just a thin, honestly-labeled slice of them, in the same spirit
as the PdM "Fleet-Risk Triage" demo pass already in this repo (see
`CLAUDE.md`'s "Fleet-Risk Triage demo screen" section for the precedent:
time-boxed, named simplifications, verified end-to-end for real).

**If you are one of the five people building this: read this entire file
before writing code.** You do not have access to the conversation that
produced this plan — this file is the only context you get. Read your own
named section fully, and read "§1 Shared contract" before you write a
single line, because everyone is building against it in parallel with no
other synchronization until integration.

**If you are doing Executive Review: skip straight to that section once
you've read §0–§2**, and read it well before integration lands — its
checklist takes real prep, and you have almost no slack if you start
reading it cold at 2:00.

---

## 0. Ground rules

**Repo:** `https://github.com/DDL-Mike-Snyder/predictive_maintenance`
(branch `main`). Clone it fresh. Read the repo's own `CLAUDE.md` at the
root first — it has the project's conventions and recent history; you do
not need to read the full session history in it, just skim it for
orientation (2 minutes, not more).

**Branching.** Each of you works on your own branch, named
`demo/rcb-<yourname>` (e.g. `demo/rcb-paul`), off `main`. Commit early and
often and **push to `origin` at least every 20 minutes** — Amanda cannot
integrate work she cannot see. Do not push directly to `main`. Do not
force-push. Do not touch files outside the ones your section names as
yours — that's what keeps five parallel branches mergeable in 30 minutes
instead of not-mergeable at all.

**Communication.** Whatever channel the group is already using (Slack,
etc.) — post when you: start, hit a blocker, finish your section, push a
commit worth others knowing about. If you discover the shared contract in
§1 is wrong or ambiguous in a way that blocks you, **post it immediately
and pick the more-demoable interpretation yourself rather than
blocking** — do not wait for a reply you might not get in time. Note what
you assumed in your commit message.

**What "done" means for your section:** your own service/component starts
up cleanly and does the thing your section describes, verified by
actually running it (curl it, or open it in a browser) — not just "the
code compiles." Every prior pass in this repo's history that skipped this
step shipped a real bug (see `CLAUDE.md`'s "Real bugs found" sections —
that pattern is not hypothetical, it happened repeatedly). You have very
little slack in 2.5 hours to find those bugs late.

### 0.1 What we are explicitly NOT building (name it, don't silently drop it)

If you find yourself about to build one of these, stop — it's out of
scope by design, not an oversight:

- **No tool-server / MCP surface** (34-tool-server.md). The "agent" calls
  the design-advisory HTTP API directly. This collapses 42 §2.1's
  "exclusively through tool-server" rule for demo speed only.
- **No auth delegation, no dual control, no adjudication workflow**
  (31-auth.md, 03 §7.2). Nobody logs in as a design authority and
  countersigns anything. "Submit Proposal" in the UI just flips a status
  flag — it is not wired to the gateway's real proposal/adjudication
  queue.
- **No agent runtime session store / checkpointing / run authority**
  (42 §3.4). The two "invocations" are plain synchronous HTTP calls.
- **No events published or consumed, no outbox, no Kafka** (28 §10).
- **No taxonomy resolution, no Failure Intelligence preflight call, no
  Knowledge & Retrieval corpus search** (42 §4.1 steps 4, 5; §4.1's
  retrieval step). All of that data is pre-seeded directly instead of
  fetched live from those (unbuilt, for this slice) services.
- **No real dependency-graph traversal.** `dependency_completeness` and
  the impact snapshot are seeded, realistic-looking numbers, not computed
  from an actual graph.
- **No RLS, no classification/compartment enforcement, no idempotency-key
  enforcement, no ETag/If-Match concurrency control.** Everything in this
  demo is effectively unclassified and single-user.
- **No production deploy pipeline.** See Amanda's section for the
  actual target (a local run first, a Domino demo App only as a stretch
  goal).

Everything else — the actual field names, the actual enum values, the
actual gate logic, the actual boundary rule that the agent never chooses
the recommendation — is real, taken from the two build documents, not
invented. That boundary rule in particular (04 §10, quoted in 42 §1.2) is
the one thing worth preserving even under this much time pressure: **the
agent composes a package for a human to evaluate; it does not decide.**
Keep the UI honest about that (see Bella's section).

---

## 1. Shared contract — read this before writing any code

This is the one thing every one of you builds against. It is fixed for
the duration of the build. If Paul's actual implementation drifts from
it, Paul fixes the implementation, not the contract (everyone else is
already coding against this document, not against Paul's code).

### 1.1 Services and ports (local dev)

| Service | Port | Owner |
|---|---|---|
| `services/design-advisory` (new) | `8002` | Paul (skeleton, models, reads), Marc (actions), Michael (agent endpoints) — one process, three contributors |
| `services/pdm` (already exists, not touched) | `8001` | — |
| `platform/gateway` (already exists) | `8000` (dev) | Amanda adds a second upstream |
| `apps/web` (already exists) | `5173` (`vite dev`) | Bella |

### 1.2 Vocabularies (verbatim from `docs/build/28-design-advisory.md` §3)

```
candidate_status:      identified | qualifying | gate_passed | gate_failed | case_drafted | withdrawn
case_status:            draft | assembled | published | superseded | withdrawn
recommendation_stance:  redesign_warranted_for_evaluation | insufficient_evidence
                         | monitor_and_reassess | no_action_indicated
cost_method:            parametric | dependency_rollup
citation_posture:       supporting | contra
test_record_status:     present | present_unparsed | absent_not_performed
                         | absent_not_located | absent_not_required | absent_unknown
gate_verdict:           proceed | proceed_corrected | restricted | refused   (from Failure Intelligence, carried verbatim)
strength_band (demo):   strong | moderate | weak | insufficient
```

For this demo, `case_status` only ever reaches `draft` → `assembled` →
`proposed` (the last one is a demo-only value, not in the real enum —
label it as such in the UI; it stands in for "a Proposal now exists,"
since we build no real proposal/adjudication queue).

### 1.3 Data model (simplified from 28 §3 — SQLite, no schema qualification, JSON columns for nested structures)

Build these as SQLAlchemy models (async, same pattern as
`services/pdm/src/fathom_pdm/models/*.py` or the simpler
`platform/gateway/src/fathom_gateway/models.py` — no `schema=` argument,
this demo's SQLite DB has one flat namespace). All IDs are string UUIDs
(`str(uuid.uuid4())`), all timestamps are ISO-8601 UTC strings.

**`redesign_candidate`**
| Column | Type | Notes |
|---|---|---|
| `candidate_id` | str, PK | |
| `niin` | str | |
| `nomenclature` | str | human-readable part name, demo-only convenience field, not in the real schema but harmless |
| `equipment_family` | str | |
| `status` | str | `candidate_status` |
| `driver_kinds` | JSON list[str] | e.g. `["causal_finding"]` |
| `driver_evidence` | JSON object | free-form summary, demo can keep it to `{"summary": "..."}` |
| `priority_score` | float | **[SIMPLIFIED]** real spec (28 §3.5.2) is a Pythagorean vector magnitude over 6+1 scaled attributes; demo uses a plain `0.0–1.0` score instead, seeded directly |
| `pdm_criticality_tier` | int | 1–5 |
| `affected_population` | JSON object | `{"item_count": int, "hull_count": int}` |
| `created_from` | str | `'causal_finding'` for every seed row |
| `dossier_id` | str, nullable FK | set once a dossier is assembled |
| `created_at` | str | |

**`failure_dossier`** (28 §3.3, flattened: citations/field-failures/test-coverage as JSON arrays on the row instead of child tables — real spec normalizes these, we don't, for speed)
| Column | Type | Notes |
|---|---|---|
| `dossier_id` | str, PK | |
| `candidate_id` | str, FK | |
| `niin` | str | |
| `dossier_version` | int | always `1` for the demo |
| `assembled_at` | str | |
| `inputs_digest` | str | any stable-looking hex string is fine — demo-only, never actually verified |
| `taxonomy_version` | str | e.g. `"v3-demo"` |
| `affected_population` | JSON object | copy of the candidate's |
| `causal_citations` | JSON list of objects | see shape below |
| `field_failure_count` | int | how many `failure_indicator=true` rows this dossier represents (we don't model individual rows) |
| `test_coverage` | JSON list of objects | see shape below |

`causal_citations[]` item shape (28 §3.3.1, field names kept, values
carried verbatim once seeded — nobody recomputes them):
```json
{
  "citation_id": "uuid",
  "posture": "supporting",
  "hypothesis_id": "uuid",
  "adjudication_state": "published",
  "strength_band": "moderate",
  "band_limiting_axis": "confound_control",
  "treatment_handling": "as_treated",
  "gate_verdict": "proceed",
  "confounders_unaddressed": ["duty-cycle variation not controlled"],
  "failure_mode_code": "FM-CORROSION-04",
  "narrative_summary": "One line, human-readable, for the UI and the narrative composer to draw on."
}
```

`test_coverage[]` item shape (28 §3.2/§3.3.2):
```json
{
  "test_kind_code": "environmental-salt-fog",
  "record_status": "absent_not_performed",
  "outcome": null,
  "qualification_credit": false,
  "absence_basis": "Legacy component, predates current qualification regime."
}
```

**`impact_snapshot`** (28 §4.4's `dependency_completeness` shape, verbatim field names — this is the one JSON object every downstream artifact carries by reference, so get the field names exactly right)
| Column | Type |
|---|---|
| `impact_snapshot_id` | str, PK |
| `candidate_id` | str, FK |
| `computed_at` | str |
| `max_depth_requested` | int |
| `edges_touched` | int |
| `edges_verified` | int |
| `completeness_ratio` | float |
| `nodes_expanded` | int |
| `nodes_truncated_at_depth` | int |
| `artifact_leaves_reached` | int |
| `unverified_by_relation` | JSON object, e.g. `{"interfaces_with": 4, "supports": 9}` |
| `unverified_by_source_kind` | JSON object, e.g. `{"inferred_cooccurrence": 11}` |
| `is_bounded_below` | bool | `true` whenever `completeness_ratio < 1.0` **or** `nodes_truncated_at_depth > 0` — always true in our seed data |
| `impacted_parts` | JSON list[str] | other NIINs |
| `impacted_artifacts` | JSON list[str] | e.g. `["TM-4410-15/2", "APL-991-04"]` |

**`cost_estimate`** (28 §3.7)
| Column | Type |
|---|---|
| `estimate_id` | str, PK |
| `candidate_id` | str, FK |
| `case_id` | str, nullable FK |
| `method` | str | `parametric` \| `dependency_rollup` |
| `cost_model_version` | str | `"v0-demo"` |
| `point_estimate_usd` | float |
| `low_usd` / `high_usd` | float, nullable together |
| `interval_basis` | str, nullable | e.g. `"±35%, demo heuristic band"` |
| `confidence` | float, nullable | 0–1 |
| `assumptions` | JSON list[str], non-empty |
| `impact_snapshot_id` | str, nullable | required if `method='dependency_rollup'` |
| `coverage_ratio` | float, nullable | copied from the snapshot, rollup only |
| `is_lower_bound` | bool | **must equal `coverage_ratio < 1.0`** when method is `dependency_rollup` — this is 28 §3.7's load-bearing constraint, keep it real even in the demo |

**`gate_decision`** (28 §5.2/§5.3)
| Column | Type |
|---|---|
| `gate_decision_id` | str, PK |
| `candidate_id` | str, FK |
| `dossier_id` / `impact_snapshot_id` | str, FK |
| `decision` | str | `pass` \| `fail` |
| `condition_results` | JSON object | `{"G1_cost_floor": true, "G2_priority_floor": true, "G3_completeness_floor": false, "G4_test_coverage_assessed": true, "G5_evidentiary_floor": true, "G6_state_consistency": true}` |
| `failed_conditions` | JSON list[str] | e.g. `["G3_completeness_floor"]` |
| `thresholds_in_force` | JSON object | see §1.4 below |
| `gate_policy_version` | str | `"v0-demo-placeholder"` |
| `computed_at` | str | |

**`redesign_case`** (28 §3.6)
| Column | Type |
|---|---|
| `case_id` | str, PK |
| `candidate_id` | str, FK |
| `niin` | str, nullable until assembled |
| `dossier_id` | str, FK |
| `case_version` | int | `1` |
| `case_status` | str | `draft` → `assembled` → `proposed` (demo value) |
| `scope_description` | str, nullable until assembled |
| `dependency_completeness` | JSON object, nullable until assembled | copy of the impact snapshot's fields |
| `impact_snapshot_id` | str, nullable until assembled |
| `test_coverage_summary` | JSON object, nullable until assembled | `{"by_record_status": {...}, "absent_unknown_count": int}` |
| `cost_estimate_id` | str, nullable until assembled |
| `recommendation_stance` | str, nullable until assembled | one of §1.2's four values |
| `recommendation_basis_refs` | JSON list, nullable until assembled |
| `recommendation_limitations` | JSON list[str], non-empty once assembled |
| `recommendation_evidence_gaps` | JSON list[str], non-empty once assembled |
| `narrative_sections` | JSON list of `{heading, body}`, nullable until assembled | **[demo addition]** not a column in the real 28 schema (the real `CaseDraftPackage` is unpersisted, per 42 §1.3) — we persist it here purely so the UI has something to re-fetch. Label it in code as demo-only |
| `assembled_at` | str, nullable |
| `proposal_id` | str, nullable | demo: just a random string once "proposed" |

### 1.4 Gate thresholds (28 §5.4 — real spec has *no default*; this demo picks concrete placeholder numbers, labeled `v0-demo-placeholder`)

```
GATE_COST_FLOOR_USD        = 250_000
GATE_PRIORITY_FLOOR        = 0.55
GATE_COMPLETENESS_FLOOR    = 0.60
GATE_FIELD_FAILURE_FLOOR   = 8
```

Gate logic (28 §5.3, G1–G6 — condition names match `condition_results` keys above):
```
G1  point_estimate_usd            >= GATE_COST_FLOOR_USD
G2  priority_score                >= GATE_PRIORITY_FLOOR
G3  completeness_ratio            >= GATE_COMPLETENESS_FLOOR
G4  no test_coverage row has record_status == 'absent_unknown'
G5  field_failure_count >= GATE_FIELD_FAILURE_FLOOR
      OR any causal_citation has posture=='supporting' AND adjudication_state=='published'
G6  candidate.status in {identified, qualifying, gate_passed, gate_failed}   (always true in demo — seed data never sets case_drafted/withdrawn before gating)
decision = 'pass' iff all six are true
```

### 1.5 Seed data — exactly five candidates (Paul builds this; everyone else can rely on these exact outcomes when building their own UI/demo script)

| # | NIIN / nomenclature | priority_score | completeness_ratio | field_failure_count | citations | point_estimate_usd | Gate outcome | Why (for the demo narrator) |
|---|---|---|---|---|---|---|---|---|
| 1 | `013456789` — Hydraulic Actuator, Primary Flight Control | 0.82 | 0.78 | 14 | 1 supporting, published, `strong` | 1,450,000 | **PASS** (all G1–G6) | Clean happy path. Draft this one fully; suggested stance should land on `redesign_warranted_for_evaluation` |
| 2 | `013456790` — Auxiliary Seawater Pump Impeller | 0.71 | **0.42** | 11 | 1 supporting, published, `moderate` | 610,000 | **FAIL — G3 only** | "Populate the dependency graph before costing this" — the honest-refusal story (28 §5.3 G3 rationale) |
| 3 | `013456791` — Digital Multiplexer Card, Combat System | **0.31** | 0.75 | 10 | 1 supporting, published, `strong` | 900,000 | **FAIL — G2 only** | Expensive and well-evidenced but nothing depends on it enough to matter — "not worth detailed estimation" |
| 4 | `013456792` — Shipboard HVAC Compressor Unit | 0.63 | 0.71 | **3** | 1 `contra` only (rejected hypothesis) | 480,000 | **FAIL — G5 only** | No evidentiary floor met — a contra citation never counts (28 §3.3.1) |
| 5 | `013456793` — Gas Turbine Module Bearing Assembly | 0.61 | 0.68 | 9 | 1 supporting, published, `weak`, non-empty `confounders_unaddressed` | 610,000 | **PASS** (all G1–G6) | Gate passing is not the same as evidence being strong — draft this one too; suggested stance should land on `monitor_and_reassess`, demonstrating that the agent doesn't just say yes because the gate passed |

Give each of these 2–3 `test_coverage` rows (mix of `present`/`pass` and one
deliberate `absent_not_performed` with a real `absence_basis` string) —
**none of the five should have an `absent_unknown` row**, or G4 fails for
all of them and you lose the G2/G3/G5 story above. `impacted_parts`/
`impacted_artifacts` can be 2–4 plausible-looking strings each.

---

## 2. Timeline (2.5 hours = 150 minutes)

| Time | What |
|---|---|
| 0:00–0:10 | Everyone clones, reads this file, reads their own section, creates their branch |
| 0:10–1:40 (90 min) | **Parallel build**, each against §1's contract. Push often. Executive Review spends this window preparing (see that section) — not idle, but not blocking anyone either |
| 1:40–2:00 (20 min) | **Amanda integrates**: merges branches in order (Paul → Marc → Michael → Bella), wires the gateway, runs the whole stack, does her own smoke test |
| 2:00–2:20 (20 min) | **Executive Review runs its adversarial checklist** against the integrated stack, live. Reports findings to Amanda (and whoever owns the affected section) as it finds them — don't batch everything to the end, a fix landing at 2:18 is still useful |
| 2:20–2:30 (10 min) | Fix anything blocking from Executive Review's findings, then rehearse the demo script (Appendix A). Executive Review gives an explicit go/no-go before rehearsal starts |

If you finish your own section early, don't scope-creep — go re-read the
relevant section of `42-redesign-case-builder.md` or `28-design-advisory.md`
(cited in your section below) and tighten your implementation against it,
or help whoever's running behind.

This is a tight schedule for six people who've never worked together in
this codebase — if Amanda's integration runs long, that time comes out of
Executive Review's window, not out of the rehearsal. A rushed adversarial
check that only spot-checks one candidate is still much better than none;
see that section's own "if you're short on time" note.

---

## Paul

**You own:** the `services/design-advisory` skeleton, its data model, and
every read-only (`GET`) endpoint. You are the foundation everyone else
builds on, so prioritize getting something that *starts and returns data*
over completeness — Marc and Michael need your models importable and your
service running on port 8002 as early as possible.

**Read first:** §1 of this file (the whole contract — you're implementing
most of it). Then skim `docs/build/28-design-advisory.md` §3 (lines
98–908, the full data model this is simplified from) if you want the
real-spec reasoning behind any field; you don't need to read it end to
end.

**Reference implementation to copy the shape of, not the content of:**
`platform/gateway/src/fathom_gateway/` — it's the smallest existing
service in this repo (no outbox, no broker, no events — same as this
one). Specifically: `main.py` (the assembly pattern), `config.py` (the
`Settings`/`BaseSettings` pattern), `models.py` (SQLAlchemy models with no
schema qualification, exactly what you need since this is SQLite).
`services/pdm/src/fathom_pdm/db.py` (or wherever PdM wires its
`async_sessionmaker`) is the pattern for the session dependency.

**Files you own:**
```
services/design-advisory/pyproject.toml
services/design-advisory/src/fathom_design_advisory/__init__.py
services/design-advisory/src/fathom_design_advisory/config.py
services/design-advisory/src/fathom_design_advisory/main.py
services/design-advisory/src/fathom_design_advisory/db.py
services/design-advisory/src/fathom_design_advisory/models.py
services/design-advisory/src/fathom_design_advisory/api/reads.py
services/design-advisory/scripts/seed_demo_data.py
```

**Do not touch** `api/actions.py`, `api/agent.py` — those are Marc's and
Michael's files (they don't exist yet; don't create empty placeholders,
just leave them out of `api/__init__.py`'s router wiring — Amanda wires
the final `build_router()` at integration, see her section. This is
deliberate: it means your branch, Marc's, and Michael's never touch the
same line of the same file).

**Tasks, in order:**

1. `pyproject.toml` — copy `platform/gateway/pyproject.toml`'s shape.
   Package name `fathom-design-advisory`, package dir
   `src/fathom_design_advisory`. Dependencies: `fastapi`, `uvicorn[standard]`,
   `pydantic`, `pydantic-settings`, `sqlalchemy[asyncio]`, `aiosqlite`
   (put it in main deps, not just dev — this demo runs SQLite always, no
   Postgres branch needed). **Skip** `fathom-canonical-schemas`,
   `fathom-contracts`, `fathom-py-common` — for demo speed, don't take a
   dependency on the shared packages' stricter conventions (problem-detail
   middleware, `operation_extra` annotations, etc.); plain FastAPI
   `HTTPException` and plain Pydantic models are fine here. This is a
   deliberate scope cut — see §0.1.
2. `config.py` — one `Settings(BaseSettings)` with `database_url: str`
   (env var `DESIGN_ADVISORY_DATABASE_URL`, default
   `sqlite+aiosqlite:///./design_advisory.db`) and the four gate thresholds
   from §1.4 as fields with those exact defaults (still overridable by
   env, but don't leave them unset — this demo needs the service to just
   start).
3. `models.py` — implement every table in §1.3 as a SQLAlchemy 2.0
   declarative model (`Mapped[...]`, `mapped_column(...)`), JSON columns
   via `sqlalchemy.JSON`. No `schema=` kwarg anywhere.
4. `db.py` — `create_async_engine`, `async_sessionmaker`, a
   `get_session()` FastAPI dependency, and a `create_all()` helper called
   at startup (`Base.metadata.create_all` via `run_sync` — no Alembic for
   this demo, straight `create_all` is fine).
5. `main.py` — `create_app()` returning a `FastAPI` instance, CORS
   middleware open (`allow_origins=["*"]` — this is a demo, not a security
   review), a `/healthz` returning `{"status": "ok"}`, and
   `app.include_router(reads_router)` from `api/reads.py`. Module-level
   `app = create_app()` so `uvicorn fathom_design_advisory.main:app` works
   directly on port 8002 (`--port 8002` on the command line, not hardcoded).
6. `api/reads.py` — an `APIRouter` with, at minimum:
   - `GET /api/v1/design-advisory/redesign-candidates` — list all, support
     an optional `?status=` filter
   - `GET /api/v1/design-advisory/redesign-candidates/{candidate_id}`
   - `GET /api/v1/design-advisory/dossiers/{dossier_id}`
   - `GET /api/v1/design-advisory/impact-snapshots/{impact_snapshot_id}`
   - `GET /api/v1/design-advisory/cost-estimates/{estimate_id}`
   - `GET /api/v1/design-advisory/redesign-cases` — list, optional
     `?candidate_id=`
   - `GET /api/v1/design-advisory/redesign-cases/{case_id}`

   Return plain dicts (`row.__dict__`-ish, or a quick Pydantic
   `model_validate`) — don't over-engineer response schemas under this
   time pressure, just make sure every field named in §1.3 is present in
   the JSON with the exact same key name.
7. `scripts/seed_demo_data.py` — a standalone script
   (`python scripts/seed_demo_data.py`) that connects to the configured DB
   and inserts exactly the five candidates from §1.5, each with its
   dossier (citations + test_coverage per the shapes in §1.3), its impact
   snapshot, and its parametric `cost_estimate` (`method='parametric'`).
   **Do not create `gate_decision` or `redesign_case` rows in the seed
   script** — those are written by Marc's/Michael's endpoints when the
   demo actually runs the qualify/draft flow live, which is the point of
   the demo. Make the script idempotent (safe to re-run: check if
   candidate NIINs already exist, skip if so) — you will run it more than
   once while debugging.
8. **Verify it for real**: `uvicorn fathom_design_advisory.main:app --port
   8002`, run the seed script, `curl http://localhost:8002/api/v1/design-advisory/redesign-candidates`
   and confirm all 5 come back with every field in §1.3 populated
   correctly. Push.

**Definition of done:** `curl` against every endpoint in step 6 returns
real seeded data matching §1.3's shapes exactly (field names matter — Marc,
Michael, and Bella are all typing these field names from this document
without seeing your code).

---

## Marc

**You own:** the "action" endpoints that run the actual gate/costing
logic — the pieces of the pipeline a human would trigger by hand even in
the real spec (28 §5.1, §5.2, §6.1 steps 7–9). You are turning the seeded
data Paul provides into a live pass/fail decision and a drafted case, on
demand.

**Read first:** §1 of this file, especially §1.3's `gate_decision`/
`redesign_case`/`cost_estimate` tables and §1.4's gate logic — that's the
whole of what you're implementing. For the real reasoning behind the gate
(worth 5 minutes even under time pressure, because it'll help you write
believable `condition_results` and not accidentally invert a comparison):
`docs/build/28-design-advisory.md` §5.2–§5.4 (lines 1239–1338, "The gate —
a persisted, reproducible decision" through "the thresholds are
placeholders").

**You do not need Paul's code to start.** You need Paul's *schema*, which
is fully specified in §1.3 above. Start against a local SQLite file with
your own quick `create_all()` call using copy-pasted model definitions if
Paul hasn't pushed yet; when Paul's `models.py` lands, switch your imports
to `from fathom_design_advisory.models import ...` and delete your copies.
Coordinate in chat if this handoff is awkward — worst case, Amanda
resolves it at integration.

**Files you own:**
```
services/design-advisory/src/fathom_design_advisory/api/actions.py
```
That's it — one file, importing `fathom_design_advisory.models` and
`fathom_design_advisory.db` (Paul's). Do not edit `models.py`,
`main.py`, `config.py`, or `api/reads.py`.

**Tasks, in order:**

1. `POST /api/v1/design-advisory/redesign-candidates/{candidate_id}/parametric-estimate`
   — **[SIMPLIFIED]** the real spec (28 §5.1) computes this from real
   inputs; here, since Paul's seed script already created a `parametric`
   `cost_estimate` row per candidate, this endpoint can just **look it up
   and return it** (idempotent re-run, no-op if it already exists). This
   keeps the "two-stage costing" *shape* real (there's a real API call in
   the pipeline) without requiring you to invent a costing formula.
2. `POST /api/v1/design-advisory/redesign-candidates/{candidate_id}/evaluate-gate`
   — the real logic. Look up the candidate, its dossier (via
   `candidate.dossier_id` once Paul's seed sets it — if it's still null,
   404 with a clear message so whoever's testing knows the seed data isn't
   linked yet), its impact snapshot, and its parametric cost estimate.
   Compute G1–G6 exactly per §1.4. Write a new `gate_decision` row (every
   call writes a fresh row — 28 §5.2's "re-evaluation writes a new row,"
   never update in place). Return the full row. Update
   `candidate.status` to `gate_passed` or `gate_failed` to match.
3. `POST /api/v1/design-advisory/redesign-cases` — body
   `{"candidate_id": "..."}`. Look up the candidate's `dossier_id`, create
   a `redesign_case` row with `case_status='draft'`, `case_version=1`, and
   nothing else populated yet (28 §3.6's own "draft rows have almost
   everything null" shape — matches the real spec's `POST /redesign-cases`
   fix, 28 §9.1). Return the new row. **Refuse (409 or 422) if a
   non-`withdrawn` case already exists for this candidate** — one draft at
   a time is enough for a demo.
4. `POST /api/v1/design-advisory/redesign-cases/{case_id}/assemble` — body
   `{"recommendation_stance": "...", "recommendation_limitations": [...],
   "recommendation_evidence_gaps": [...], "narrative_sections": [...]}`
   (Michael's agent endpoint computes these values and calls this
   endpoint to actually persist them — see Michael's section; you're
   building the persistence side of that handoff). Validate: gate for this
   candidate must have `decision='pass'` (404/409 with a clear message if
   not — this is 28 §5.5's real precondition, worth keeping). Populate
   every field the real `assembled_is_complete`/`assembly_inputs_complete`
   constraints require (28 §3.6): `niin`, `scope_description` (can be a
   generic templated string, e.g. `f"Redesign evaluation for {niin}"`),
   `dependency_completeness` (copy from the impact snapshot),
   `impact_snapshot_id`, `test_coverage_summary` (derive
   `{"by_record_status": {...counts...}, "absent_unknown_count": 0}` from
   the dossier's `test_coverage` list), `cost_estimate_id` (create a
   **`dependency_rollup`** `cost_estimate` row here — reuse the parametric
   estimate's `point_estimate_usd` scaled by, say, `1.4` as a stand-in
   "detailed roll-up," with `coverage_ratio` = the impact snapshot's
   `completeness_ratio` and `is_lower_bound = coverage_ratio < 1.0` per
   §1.3's constraint — do the arithmetic for real, don't hardcode
   `is_lower_bound`), `recommendation_*` fields (from the request body),
   `narrative_sections`, `assembled_at`. Set `case_status='assembled'`.
   Return the full row.
5. `POST /api/v1/design-advisory/redesign-cases/{case_id}/propose` —
   **[demo-only endpoint, not in the real 28 API surface]** — sets
   `case_status='proposed'` and `proposal_id` to a random UUID string.
   That's the entire "adjudication" story this demo tells; label it as
   such in a one-line comment.
6. **Verify it for real**: with Paul's service running and seeded, `curl
   -X POST` each of your five endpoints against at least candidate #1
   (Hydraulic Actuator — should gate-pass) and candidate #2 (Seawater Pump
   — should gate-fail on G3 only) from §1.5, and confirm the responses
   match what you'd expect by hand-checking the numbers. Push.

**Definition of done:** running the full sequence
(parametric-estimate → evaluate-gate → [if pass] redesign-cases →
assemble → propose) by hand with `curl` against candidate #1 produces a
`case_status='proposed'` row with a real, constraint-satisfying
`dependency_rollup` cost estimate; the same sequence against candidate #2
correctly refuses at `assemble` (or you never call it, since evaluate-gate
already reports `fail`).

---

## Michael

**You own:** the "agent" — the orchestration that runs 42's two
invocations (`qualify`, `draft`) by calling Paul's and Marc's endpoints in
sequence, deriving the honest limitations/evidence-gaps by rule (not by
LLM — 42 §1.3 is explicit that this part is deterministic code, never the
language model), and composing the human-readable narrative (which *is*
the LLM's job, per 42 §1.3's "Composed" row).

**Read first:** §1 of this file. Then
`docs/build/42-redesign-case-builder.md` §1.3 (lines 92–109, "What
'drafts the business case' means, exactly" — the Carried/Derived/Composed
table is the single most important thing in this whole plan for your
section) and §4.1 (lines 383–406, the ordered tool-call sequence — you're
implementing a simplified version of steps 1–3, 6–8 for `qualify` and
steps 10–12 for `draft`; steps 4, 5, and the retrieval call are skipped
per §0.1 above).

**You do not need Paul's or Marc's code to start.** Build against a tiny
local stub server that returns the exact JSON shapes from §1.3/§1.5 (a
20-line FastAPI app or even a `responses`-mocked `httpx` client is fine)
so you can develop and test your orchestration logic in isolation. Switch
the base URL to `http://localhost:8002` (the real service) once Paul's is
up, or at integration.

**Files you own:**
```
services/design-advisory/src/fathom_design_advisory/api/agent.py
services/design-advisory/src/fathom_design_advisory/agent/derive.py
services/design-advisory/src/fathom_design_advisory/agent/narrative.py
```

**Tasks, in order:**

1. `agent/derive.py` — two pure functions, no I/O:
   - `derive_evidence_gaps(dossier: dict, impact_snapshot: dict) -> list[str]`.
     Rules (deterministic, demo-scoped standins for 42 §4.5's real logic):
     for each `test_coverage` row whose `record_status` starts with
     `"absent"`, add a gap string naming the test kind and its
     `absence_basis`; for each citation with `posture == "contra"`, add
     `"A contradicting causal hypothesis was also examined for this
     failure mode and is not counted as supporting evidence."`; if
     `impact_snapshot["is_bounded_below"]`, add a gap stating the
     `completeness_ratio` and that the traversal was truncated or
     incomplete.
   - `derive_limitations(cost_estimate: dict, dossier: dict) -> list[str]`.
     Rules: if any citation has a non-empty `confounders_unaddressed`,
     add a limitation listing them verbatim (**never summarize or soften
     them** — that's 42's core non-negotiable rule, §1.2 B4/§1.3); if
     `cost_estimate["is_lower_bound"]`, add
     `"This cost estimate is a lower bound — it reflects only the
     {coverage_ratio:.0%} of the dependency graph that has been
     verified."`; always add one generic limitation naming the
     `strength_band` of the weakest supporting citation (so a reader
     never mistakes "gate passed" for "evidence is strong" — this is the
     point of candidate #5 in §1.5).

   **Both functions must return a non-empty list, always** — 28 §3.6's
   real constraint requires it, and it's also the whole ethical point of
   this agent (42 §1.2 B4): it must never have nothing to say.

2. `agent/narrative.py` — one function,
   `compose_narrative(candidate, dossier, impact_snapshot, cost_estimate,
   gate_decision, limitations, evidence_gaps) -> dict` returning
   `{"narrative_sections": [{"heading": str, "body": str}, ...],
   "suggested_stance": str, "suggested_stance_basis": str}`.
   - **Try the Domino AI Gateway first** (skill: `dominodatalab:ai-gateway`
     — load it and follow its setup instructions if you have Domino
     credentials in your environment). Prompt it with the carried figures
     only — every number in the narrative must come from the function's
     own arguments, never be invented (42 §5.6's rule, and it's the
     easiest way to embarrass this demo if violated: don't let the model
     make up a dollar figure or a percentage that isn't in the carried
     data). Ask for 2–3 short sections (e.g. "Evidence Summary," "Cost and
     Impact," "Limitations") and a `suggested_stance` — **but you choose
     `suggested_stance` yourself, in code, from simple rules below; do not
     let the model pick it** (this is 42 §1.3's single most important
     rule: *"A model selecting `redesign_warranted_for_evaluation` is a
     model making a recommendation"* — which 04 §10 places outside this
     system entirely). Only ask the model to write the *basis* prose
     explaining a stance you already picked.
   - **`suggested_stance` rule (deterministic, your code, not the LLM):**
     if gate `decision == 'fail'`, this function is never called (no case
     to draft). If it passed: `no_action_indicated` if
     `field_failure_count < GATE_FIELD_FAILURE_FLOOR` and the only support
     is a single `weak` citation with confounders; `monitor_and_reassess`
     if the strongest supporting citation's `strength_band` is `weak` or
     it has non-empty `confounders_unaddressed`; otherwise
     `redesign_warranted_for_evaluation`. (Sanity check against §1.5:
     candidate #1 → `redesign_warranted_for_evaluation`; candidate #5 →
     `monitor_and_reassess`.) `insufficient_evidence` is available for a
     case with zero supporting citations, which shouldn't happen for any
     gate-passing candidate in our seed data but write the branch anyway.
   - **Fallback, and do not burn more than 15 minutes chasing AI Gateway
     auth issues:** if the AI Gateway call fails or you don't have
     credentials, compose the narrative from an f-string template instead
     — plug the real carried numbers into fixed prose. Label this
     fallback clearly in a comment and log a line saying which path was
     used. **A templated-but-numerically-honest narrative is a fine demo
     outcome; a broken pipeline because an LLM call hung is not.**
3. `api/agent.py` — two endpoints:
   - `POST /api/v1/design-advisory/agent/candidates/{candidate_id}/qualify`
     — calls, via `httpx.AsyncClient` against `http://localhost:8002`
     (configurable via an env var `DESIGN_ADVISORY_BASE_URL`): get the
     candidate, get its dossier, get its impact snapshot (candidate's
     `dossier_id` → dossier → you'll need a way to find the snapshot; Paul
     seeds one snapshot per candidate, so `GET
     /redesign-candidates/{id}` should be enough context — coordinate
     with Paul/chat if the snapshot isn't reachable by candidate id, and
     add a `GET /impact-snapshots?candidate_id=` filter to Paul's
     `reads.py` if needed, or just have your seed step note the mapping),
     call Marc's `parametric-estimate`, then Marc's `evaluate-gate`. Call
     `derive_evidence_gaps` for the gap list. Return a `QualificationReport`
     -shaped JSON (42 §3.2.1, trimmed to what we actually have): `run_id`
     (`uuid4`), `candidate_id`, `niin`, `dossier_id`, `impact_snapshot_id`,
     `dependency_completeness`, `parametric_estimate`, `gate_decision_id`,
     `gate_decision` (the `decision` string), `condition_results`,
     `failed_conditions`, `causal_citation_refs` (the dossier's citations,
     verbatim), `derived_evidence_gaps`, `outcome`
     (`"gate_pass"`/`"gate_fail"`).
   - `POST /api/v1/design-advisory/agent/cases/{case_id}/draft` — calls
     `GET /redesign-cases/{id}` (must be `status='draft'` — 404 if not, or
     if none exists call Marc's `POST /redesign-cases` first with the
     `candidate_id` from the query/body), pulls the dossier/snapshot/cost
     estimate it needs, runs `derive_limitations`/`derive_evidence_gaps`,
     runs `compose_narrative`, then **calls Marc's own
     `POST /redesign-cases/{id}/assemble`** with the results (so
     persistence happens exactly once, in Marc's endpoint — you don't
     write to the DB directly from this file). Return the assembled case.
4. **Verify it for real**: with Paul's and Marc's services running and
   seeded, `curl -X POST` your `qualify` endpoint for all five candidates
   from §1.5 and confirm each one's `outcome`/`failed_conditions` matches
   the table exactly. Then `curl -X POST` your `draft` endpoint for
   candidates #1 and #5 and read the actual narrative text that comes
   back — if it reads like nonsense or invents a number, fix it before
   moving on. Push.

**Definition of done:** `qualify` against all five seed candidates
reproduces §1.5's outcomes exactly; `draft` against candidate #1 produces
a narrative that only cites the real seeded figures and lands on
`redesign_warranted_for_evaluation`; `draft` against candidate #5 lands on
`monitor_and_reassess` and its limitations mention the weak/confounded
evidence explicitly.

---

## Bella

**You own:** the UI screen. This is what the audience actually watches —
prioritize it looking clean and telling the right story over covering
every field in the contract.

**Read first:** §1 of this file (you mostly need §1.5's seed data table
and the shapes in §1.3, so you know what to render). Skim
`docs/build/42-redesign-case-builder.md` §1.2 (lines 75–90, the four
boundary statements B1–B4) — this is why your UI must never present
`suggested_stance` as a decision the system made; frame it visibly as a
draft recommendation for a human to accept or reject, matching 04 §10's
own framing (*"a decision package for a human authority, not a
decision"*).

**Reference implementation to copy the shape of:**
`apps/web/src/features/pdm/FleetRiskTriage.tsx` — same three-box
layout idea (a list/triage table, a detail/deep-dive panel, an
action area) applies here: candidate list → qualification report →
draft package.

**You do not need Paul/Marc/Michael's services running to build this.**
Build against hardcoded fixture objects matching §1.3's shapes (literally
copy the JSON examples in this file into a `fixtures.ts` in your own
feature folder) so your whole component tree and interaction flow works
before any backend exists. Isolate your data-fetching into a small number
of functions (e.g. `fetchCandidates()`, `runQualify(candidateId)`,
`runDraft(caseId)`, `submitProposal(caseId)`) so swapping fixtures for
real `fetch`/`client.GET` calls at integration is a five-line diff, not a
rewrite.

**Files you own:**
```
apps/web/src/features/design-advisory/RedesignCaseBuilder.tsx
apps/web/src/features/design-advisory/fixtures.ts
apps/web/src/features/design-advisory/api.ts
```
Plus two **one-line** edits to files Amanda will also touch — coordinate
timing with her, or just make the edit, commit, and let her merge it (it's
a two-line diff, low risk):
- `apps/web/src/routes.tsx` — replace the `NotBuilt` you're not using...
  actually: **add a new route**, don't reuse `/registry` etc. Add
  `{ path: "design-advisory", element: <RedesignCaseBuilder /> }` to the
  children array.
- `apps/web/src/shell/SideNav.tsx` — change the existing `{ kind:
  "external", label: "Design Advisory" }` entry (in the `"Analysis"`
  group) to `{ kind: "route", label: "Design Advisory", to:
  "/design-advisory" }`. This is the one nav item in the whole app
  that's currently a dead placeholder specifically waiting for this —
  see that file's own header comment.

**Tasks, in order:**

1. `fixtures.ts` — hand-write the five candidates from §1.5 as objects
   matching §1.3's shapes (you don't need every field, but include enough
   to render everything in step 3 below), plus one fully-worked
   `QualificationReport` and one fully-worked `CaseDraftPackage`-shaped
   response (candidate #1's) for the detail views.
2. `api.ts` — the four functions named above. For now they read from
   `fixtures.ts` and `return Promise.resolve(...)` (simulate a qualify/
   draft call with a `setTimeout` of ~800ms so the loading state is
   visible and real). Structure each function so that swapping its body
   for a real `fetch("/api/v1/design-advisory/...")` call doesn't change
   its signature or callers.
3. `RedesignCaseBuilder.tsx` — three panels:
   - **Candidate list** (left or top): all five, showing NIIN,
     nomenclature, `status`, `priority_score`. Clicking one selects it.
   - **Qualification panel** (once a candidate is selected): a "Run
     Qualification" button that calls `runQualify`; while pending, show a
     loading state; once resolved, render the `QualificationReport`:
     dependency-completeness figures (`completeness_ratio`,
     `is_bounded_below` — **make `is_bounded_below` visually prominent
     when true**, this is 42 §4.3's whole point, don't bury it), the
     parametric cost estimate, the gate `decision` with `condition_results`
     shown as a pass/fail checklist (not just the aggregate), and the
     dossier's causal citations (show `strength_band`,
     `confounders_unaddressed`, `posture`).
   - **Draft panel** (visible once the gate has passed): a "Draft Case"
     button calling `runDraft`; once resolved, render the
     `narrative_sections`, then **separately and visually distinctly**,
     `recommendation_limitations` and `recommendation_evidence_gaps`
     (non-empty lists, styled to draw attention — e.g. a warning-toned
     box, not buried in small print) and the `suggested_stance` **labeled
     explicitly as "Suggested — pending human review," never as a
     decision**. End with a "Submit Proposal" button calling
     `submitProposal`, which on success shows something like "Proposal
     submitted — awaiting design-authority adjudication (not implemented
     in this demo)."
   - If the gate failed, show the failed condition(s) and a short, honest
     message instead of a draft button — e.g. for candidate #2:
     "Dependency completeness is 42% (floor: 60%) — populate the
     dependency graph for this NIIN before a detailed cost estimate can
     be justified." Pull the message from `failed_conditions`, don't
     hardcode per-candidate text.
4. **Verify it for real**: `pnpm dev` (or however this repo's `apps/web`
   is started — check its `package.json` scripts), open it in a browser,
   click through all five candidates, confirm the fixture data renders
   correctly and the two buttons produce the fixture qualification/draft
   results. Push.

**Definition of done:** clicking through all five candidates in a real
browser tells the correct story for each (per §1.5's "why" column)
without touching any real backend yet — you're validating your own UI
logic and copy, independent of integration.

---

## Amanda

**You own:** gateway wiring and final integration. You are the last
critical path before the demo is real — budget your time accordingly (see
§2's timeline: you get the 1:40–2:10 block as your primary window, but
start your gateway changes during the parallel build window since they
don't depend on anyone else's work landing first).

**Read first:** §1 and §2 of this file in full — you need the whole
picture. `platform/gateway/src/fathom_gateway/proxy.py`'s module
docstring (already in this repo) explains DECISION G-3 (openapi.json-
driven pass-through, no catch-all) — you're replicating that pattern for
a second upstream, not inventing a new one.

### Part 1 (do this during the parallel build window, 0:10–1:40 — it doesn't depend on Paul/Marc/Michael/Bella)

**Files you touch:**
```
platform/gateway/src/fathom_gateway/config.py   (add a class + a field)
platform/gateway/src/fathom_gateway/main.py     (add one include_router call)
```

1. In `config.py`, add a `DesignAdvisoryUpstreamSettings(BaseModel)` class
   — identical shape to the existing `PdmUpstreamSettings` right above it
   (`base_url: str`, `openapi_path: str`). Add
   `design_advisory: DesignAdvisoryUpstreamSettings` to `Settings`, right
   after the existing `pdm: PdmUpstreamSettings` field.
2. In `main.py`, right after the existing
   ```python
   app.include_router(
       build_passthrough_router(app=app, upstream=settings.pdm, http_client=app.state.http_client)
   )
   ```
   add a second, identical call with `upstream=settings.design_advisory`.
   `build_passthrough_router`'s parameter is type-hinted as
   `PdmUpstreamSettings` in `proxy.py` — that's just a hint, Python won't
   enforce it, and `DesignAdvisoryUpstreamSettings` has the same two
   fields, so this works without touching `proxy.py` at all. (If you have
   a spare five minutes near the end, genericize the type hint properly —
   not required for the demo to work.)
3. You'll need a `platform/gateway/.env`-equivalent or exported env vars
   for local runs: `FATHOM_DESIGN_ADVISORY__BASE_URL=http://localhost:8002`
   and `FATHOM_DESIGN_ADVISORY__OPENAPI_PATH=<path to design-advisory's
   generated openapi.json>` (see Part 2, step 1 — you generate this file
   yourself once Paul's service exists, it isn't something Paul commits
   ahead of time necessarily, but ask him to if he has a spare minute).
4. Push this early — it's independent of everyone else and de-risks your
   own critical-path work later.

### Part 2 — integration (1:40–2:10, or as soon as Paul+Marc+Michael+Bella have each pushed something working)

1. Merge order matters, do it in this sequence, resolving conflicts as
   you go (there should be almost none — everyone was told to touch
   disjoint files):
   `demo/rcb-paul` → `demo/rcb-marc` → `demo/rcb-michael` → `demo/rcb-bella`
   → your own gateway branch, all into one integration branch (e.g.
   `demo/rcb-integration`).
2. After merging Paul+Marc+Michael, you now have three files
   (`api/reads.py`, `api/actions.py`, `api/agent.py`) that nobody has
   wired together. Edit `services/design-advisory/src/fathom_design_advisory/api/__init__.py`
   (create it if Paul didn't) to build one `APIRouter` including all
   three, and make sure `main.py` includes it. **This is the one file
   Paul/Marc/Michael were all told not to create for exactly this
   reason** — you're the one who wires it, once, with all three files
   in front of you.
3. Generate design-advisory's `openapi.json`: add a small
   `--emit-openapi` flag to its `main.py` if nobody already did (copy the
   pattern from `services/pdm/src/fathom_pdm/main.py` or
   `platform/gateway/src/fathom_gateway/main.py` — both already support
   this), run it, commit the file at
   `services/design-advisory/openapi.json`.
4. Start everything locally:
   - `services/design-advisory` on `8002`, run
     `scripts/seed_demo_data.py` once against it
   - `services/pdm` on `8001` (existing — not part of this demo's story,
     but the gateway proxies it too and its absence would 500 on
     unrelated routes; start it anyway, or comment out its
     `include_router` call temporarily if it's more trouble than it's
     worth — your call, it's not this demo's focus)
   - `platform/gateway` on `8000`, pointed at both upstreams
   - `apps/web` via `pnpm dev` (port `5173`), talking to the gateway via
     its existing Vite proxy
5. **Swap Bella's `api.ts` from fixtures to real calls** — either you or
   Bella does this together, whoever has more time left; it's the one
   place her branch and the real backend actually meet. The real paths
   are `/api/v1/design-advisory/...` exactly as documented in Paul's/
   Marc's/Michael's sections above.
6. **Smoke-test the whole thing yourself, in a real browser, following
   Appendix A below, before declaring integration done.**

### Part 3 — stretch goal only, if ≥20 minutes remain after Part 2 is solid

A real Domino demo App already exists for this project (`fathom-pdm-demo`,
see the repo's `CLAUDE.md` "RESUME HERE" section for its App ID and how to
restart it) — **do not overwrite or redeploy it** without confirming with
the project's coordinator first; it's a real, currently-working shared
resource. If there's real time left and the coordinator agrees, the
lowest-risk path is a **new**, separate Domino App (e.g.
`fathom-rcb-demo`) following `app.sh`'s existing pattern (it already shows
exactly how to run multiple Python services + a static `apps/web` build
in one container — you'd be adding a third `uvicorn` process block for
design-advisory on port `8002`, alongside the existing PdM-on-8001 and
gateway-on-8888 blocks, plus a new `deploy/domino-demo/init_design_advisory_schema.py`
mirroring the existing `init_pdm_schema.py`). **A working `localhost` demo
is the actual deliverable for this 2.5-hour window — treat any Domino
deployment as optional polish, not the goal**, given this repo's own
documented history of real, time-consuming bugs the first time anything
gets actually deployed there (see `CLAUDE.md`'s "Real bugs found" list —
SDK bugs, path-prefix bugs, port conventions that only apply inside a real
App container). Don't gamble your last 20 minutes on it if Part 2 isn't
rock solid yet.

**Definition of done:** Appendix A's script runs cleanly, live, in a
browser, against the real integrated stack.

---

## Executive Review

**You own:** an adversarial check of the *integrated* system — after
Amanda has merged everyone's work and declared it running, not before.
You are not a sixth builder and you do not write feature code. Your job is
to find the ways this demo is lying, broken, or fragile before an
audience does, in the roughly 20 minutes between Amanda's integration
landing and the final rehearsal.

**Mindset, stated plainly: assume every "done" above is wrong until you
personally verify it.** This is not a comment on the other five — it's
this project's own established discipline. `CLAUDE.md`'s "Real bugs found
by actually building this" section (and its "AWS smoke-test deployment"
section, and its "Kafka consumer-loop infrastructure" section...) is nine
separate entries long, and the common thread in every one of them is *"a
prior pass reviewed this and believed it worked; running it for real
found otherwise."* Grant statements 1–5 (candidates match §1.5's table),
1–4 (Marc's endpoints), etc. below zero credit from anyone's self-report,
including Amanda's own "smoke-tested" claim — re-run it yourself. If
something can't be checked in the time available, say so explicitly
("NOT VERIFIED — ran out of time") rather than letting it pass silently as
if it had been.

**Read first:** §0.1 (what was deliberately cut — you are not filing bugs
against those, they're known and named), §1 (the contract — this is your
ground truth; anywhere the running system disagrees with §1 is a finding),
§1.5's seed-data table (memorize the five expected outcomes — you'll be
checking against them directly, repeatedly), and 42's four boundary
statements B1–B4 (`docs/build/42-redesign-case-builder.md` lines 83–90) —
those are the thing most worth protecting even in a 2.5-hour demo, and the
thing most likely to have quietly eroded under time pressure without
anyone deciding to erode it.

**You need:** the integrated stack running (from Amanda), a terminal with
`curl` and `jq`, and a real browser. You do not need write access to
anyone's branch — file findings by talking to the relevant owner (or
Amanda, if the owner isn't reachable) rather than fixing code yourself;
your value here is the independent check, not becoming a seventh
implementer under time pressure.

### During the parallel-build window (0:10–1:40) — prepare, don't wait idle

You have nothing to test yet, but plenty to do:

1. Write out the exact `curl` commands you'll run against all five
   endpoints for all five candidates, from §1.3/§1.5, so you're not
   composing them live under time pressure at 2:00. A shell script
   (`check_candidate.sh <candidate_id> <expected_outcome>`) that hits
   `qualify`, checks `outcome`/`failed_conditions` against an expected
   value, and prints PASS/FAIL is worth the ten minutes.
2. Skim each of the five people's sections above and note, in your own
   scratch file, the specific claims you'll need to verify — not just
   "does it work" but the sharpest version of each: *does `is_lower_bound`
   actually equal `coverage_ratio < 1.0` in Marc's assemble response, or
   is it hardcoded? Does Michael's narrative cite a dollar figure that
   isn't in the carried cost estimate? Does Bella's UI ever render
   `suggested_stance` without the "pending human review" label?* Specific,
   falsifiable predictions beat a vague "seems fine."
3. If Paul/Marc/Michael push working branches early, you're allowed to
   poke at their individual services *before* full integration — this
   surfaces problems earlier and is strictly better than waiting. Just
   don't block them or demand fixes before their own section's own
   "definition of done" — that's their call to make until integration.

### Once the integrated stack is up — the adversarial checklist

Work through these in order; stop and report immediately if you hit
anything in the first three (they're the ones most likely to make the
live demo visibly fail or visibly lie, as opposed to being merely
untidy):

1. **Reproduce §1.5's table exactly, candidate by candidate, via `curl`
   against the real running gateway** (not against `localhost:8002`
   directly — going through the gateway is the actual demo path and is
   where a proxy-wiring bug would show up, per this project's own history
   of gateway pass-through bugs). For each of the five: run `qualify`,
   confirm `outcome` and `failed_conditions` match the table's "Gate
   outcome"/"Why" columns precisely — not "close enough." A single flipped
   comparison operator in Marc's gate logic (`>` vs `>=`, or a threshold
   read from the wrong field) is exactly the kind of bug this repo's own
   history shows surviving a first pass (see `22-pdm.md`'s own scoring-
   formula bug, bug #9 in `CLAUDE.md`) — verify the actual numbers, don't
   just check that *a* decision came back.
2. **Try to make the system lie.** Draft candidate #1 and #5 (both gate
   passes) and, for every number that appears in the narrative prose,
   grep for that exact figure in the `QualificationReport`/cost-estimate
   JSON that fed it. If the LLM (or the template) states a percentage,
   dollar figure, or count that doesn't trace to a carried field, **that
   is the single most serious class of finding this review can surface**
   — 42 §5.6's whole rule is that a narrative may never carry a figure
   the carried set doesn't have, and an LLM under a vague prompt is
   exactly the kind of thing that invents a plausible-sounding number.
3. **Try to make the system make a decision it isn't allowed to make.**
   Check: is `suggested_stance` ever selected by the LLM/template rather
   than by Michael's rule-based code (ask to see the code if the JSON
   alone doesn't make it obvious — a stance that varies across identical
   inputs on repeated calls is a tell)? Does the UI present it anywhere
   without an explicit "suggested / pending human review" framing? Does
   `recommendation_limitations` or `recommendation_evidence_gaps` ever
   come back empty on an assembled case (28's own constraint requires
   non-empty; an empty list here is both a spec violation and the exact
   failure mode 42 §1.2 B4 exists to prevent)?
4. **Break the unhappy paths on purpose**, not just the five scripted
   candidates: call `draft` on a candidate whose gate failed (should
   refuse, not silently draft anyway); call `assemble` twice on the same
   case (should the second call fail cleanly, or does it corrupt state?);
   call `qualify` on a candidate id that doesn't exist (should 404, not
   500); reload Bella's UI mid-flow and confirm it doesn't crash on a
   candidate with no case yet.
5. **Check the two structural invariants a demo audience won't notice but
   a domain expert would ask about within thirty seconds:** the
   `dependency_rollup` cost estimate Marc creates at `assemble` — does its
   `is_lower_bound` really equal `coverage_ratio < 1.0`, computed live, or
   is it a copy-pasted `true`? And candidate #4 (the `contra`-only
   citation) — confirm it actually fails G5 for the reason claimed
   (no supporting, published citation) and not by accident (e.g., because
   `field_failure_count` happens to also be low, masking a bug where
   `contra` citations are incorrectly being counted toward the floor).
6. **Skim the UI copy for anything that oversells.** Any phrase that
   reads like the system decided something, recommended an action without
   a hedge, or presented a lower-bound cost as a total — flag it. This is
   a fast, cheap pass and it's the one most likely to embarrass the demo
   in front of exactly the audience (design engineers, PEO staff) who'd
   catch it fastest.

### Reporting findings

For each finding, give the owner: what you did (exact command/click),
what you expected (cite the section/table this plan gave), what actually
happened, and a severity:

- **Blocking** — demo will visibly break or visibly misrepresent data.
  Must be fixed before rehearsal, even if it eats into rehearsal time.
- **Notable** — real bug, doesn't break the demo script in Appendix A
  specifically. Fix if time allows; otherwise the presenter should know
  about it so they don't get surprised live.
- **Cosmetic** — worth a follow-up, not worth anyone's remaining minutes
  tonight.

End with an explicit **go/no-go** for rehearsal, and if no-go, name the
specific blocking items left. A silent shrug is not a verdict — say the
word.

**If you're short on time:** do not water down the checklist by skimming
all six items shallowly. Do items 1–3 properly (they're the ones that
protect the demo's honesty, which is the whole point of this role) and
explicitly mark 4–6 as "not checked" rather than rushing them and
reporting false confidence. An honest "we didn't get to X" is strictly
more useful to the presenter than a rushed pass that missed something.

---

## Appendix A — end-to-end demo script (rehearse this in the last 20 minutes)

1. Open the app, click **Design Advisory** in the left nav (it's real now
   — it used to be a greyed-out placeholder).
2. Point out the five candidates. Click **Digital Multiplexer Card**
   (#3). Run qualification. Point out: cost estimate is high, evidence is
   solid, but the priority score is too low relative to what's actually
   at stake — **gate fails on G2 only**, and the UI says so honestly
   instead of drafting a case nobody asked for.
3. Click **Auxiliary Seawater Pump Impeller** (#2). Run qualification.
   Point out the dependency-completeness figure and `is_bounded_below` —
   **gate fails on G3**: the system is refusing to cost a redesign against
   a dependency graph it knows is only 42% verified, and says exactly what
   to do about it (populate the graph), rather than producing a
   false-precision number.
4. Click **Hydraulic Actuator, Primary Flight Control** (#1). Run
   qualification — gate passes on every condition. Click **Draft Case**.
   Walk through the narrative, then **stop on the limitations and
   evidence-gaps box** — point out that even on the strongest candidate in
   the seed set, the system is still surfacing what it doesn't know. Point
   out `suggested_stance` is labeled "pending human review," not a
   decision. Click **Submit Proposal**.
5. Click **Gas Turbine Module Bearing Assembly** (#5). Run qualification
   — gate passes. Click **Draft Case** — but this time the suggested
   stance is **"monitor and reassess,"** not "redesign warranted," even
   though the gate passed, because the underlying evidence is weak and
   confounded. **This is the single most important beat in the whole
   demo**: passing the cost/priority/completeness gate is not the same as
   the evidence justifying a redesign, and the system never conflates the
   two — that distinction is 04 §10's entire reason for existing, and it's
   real in this build, not just asserted in a slide.

## Appendix B — where to go for more depth, if time allows

- `docs/build/42-redesign-case-builder.md` §1 (lines 65–144) — the
  authority boundary this whole demo tries to honor even in miniature.
- `docs/build/28-design-advisory.md` §5 (lines 1220–1393) — the real
  two-stage costing/gate design this demo simplifies.
- `docs/build/28-design-advisory.md` §8 (lines 1674–1787) — why a citation's
  `strength_band`/`confounders_unaddressed` must never be summarized away;
  the reason Michael's `derive_limitations` carries them verbatim.
- `CLAUDE.md` (repo root) — this project's own conventions and the
  precedent for the PdM demo pass this plan is modeled on.
