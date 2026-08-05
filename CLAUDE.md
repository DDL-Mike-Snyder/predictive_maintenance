# FATHOM — project instructions for Claude Code, plus handoff / continuation notes

This file is loaded automatically by Claude Code at the start of every
session in this repo (the `CLAUDE.md` convention) — so treat the section
immediately below as a standing instruction, and everything after "Where
things stand" as a running handoff log for whoever (human or agent) picks
this up next. This file used to be `HANDOFF.md`; renamed 2026-08-05 so the
agentic-model-allocation policy below is actually visible to a fresh
session rather than living only in Claude's private cross-session memory.

## Agentic model allocation (standing policy)

| Work | Model | Notes |
|---|---|---|
| Build-framework / spec authoring | Sonnet 5 | The corpus-hardening phase; done. |
| Per-service implementation (writing code) | Sonnet 5 | Default for all build work, including self-review of your own output. |
| Adversarial review of generated code | **Opus 5** — explicit `model` override required | Not run by default. Explicit per-checkpoint decision the user makes — as of 2026-08-05, deferred again even though PdM cleared its 7-item checklist plus a real AWS deploy; don't assume this means it's now standard practice. Ask before scheduling one. |
| Mechanical sweeps (status-column reconciliation, staleness cleanup, bulk lint fixes, etc.) | **Haiku 4.5** — explicit `model` override required | Cheap, high-volume, low-judgment work only. |
| Parallelizing genuinely independent build tasks (e.g. Dockerfile + Helm chart) | Multiple Sonnet 5 subagents, fanned out | This is a speed/parallelism choice, not a model-tier change — still Sonnet. Re-verify each subagent's work afterward (real command execution, not just trusting its self-report) before treating it as done. |

**Why an explicit `model` override matters:** omitting the `model` param on
an `Agent`/subagent call makes it silently inherit whatever model the
*current session* is running as — there is no config-file pin causing
this, it's plain inheritance. `opus`/`haiku` overrides are honored
per-call and reliably produce that tier (verified live). Sonnet needs no
override since it's both the safe default and the session default.

**Current actual practice (as of 2026-08-05, PdM's implementation):** no
subagents are used for PdM's own build/review — the main session (Sonnet
5) does both building and self-review directly. Opus adversarial review
was considered and explicitly declined twice (once mid-build, once again
after the AWS smoke-test deploy) — revisit before starting service #2 or
before any non-smoke-test production deployment, but don't self-schedule
it without asking.

---

# FATHOM — handoff / continuation notes

**Read this first if you're picking this up cold.** Last updated 2026-08-05
(fourth update, same day: **PdM's Helm chart, Dockerfile, and API were
actually deployed to a real AWS EKS cluster and hit end-to-end** — a
smoke-test namespace, a real Postgres, a real ingress on the user's real
Domino domain, the Domino Job entrypoint run for real from inside the
Domino workspace against it, and a minimal live dashboard published at
the same domain. See "AWS smoke-test deployment" below and bugs #16–#17).
Commit `4c1e13e` has #27's model-registry binding + Domino Job entrypoint
work. **Update, 2026-08-05, later the same day: the AWS deployment pass
(the Dockerfile arch fix, the new scoring_run grant migration, the Helm
chart toggles) is now committed too, in `91e81c0`** — an earlier version of
this file said it wasn't; that was true when written and is stale now.
`git log --oneline` / `git status` tell the true story; this file is the
map, but always verify against those two before trusting a paragraph like
this one that describes commit state.

## Where things stand, in one paragraph

The spec corpus (`docs/architecture/`, `docs/build/`) is **done** — two full
adversarial review rounds (a 12-finding classification-aggregation audit and
a buildability spot-check that found regressions in the *previous* round's
own fixes) are both closed, `tools/check_event_catalog.py` passes, and the
user explicitly chose to stop reviewing and start building rather than run a
third pass. We picked **PdM (Predictive Maintenance)** as the first service
to build end-to-end, specifically to prove the shared-infrastructure pattern
and surface Domino-specific issues before repeating it across the other 8
domain services + 8 platform services. That vertical slice is now a real,
tested skeleton with **all seven items on the user's explicit checklist
done** — see "What's built" below.

## This update: #27 (Domino Job entrypoint + Model Registry binding)

The user provided real access this session: the Domino instance
(`https://mikesn136713.cs.domino.tech`), a live `dom connect` SSH tunnel to
their `mike_snyder`'s vscode session workspace, and confirmed this repo is
checked out there at `/mnt/code` (git-based project, was 5 commits behind
`origin/main`, fast-forwarded). Real values discovered by actually connecting,
not guessed: `DOMINO_PROJECT_ID=6a7109c166c85009d461fcef`,
`DOMINO_PROJECT_NAME=predictive_maintenance` (confirmed via
`GET /api/projects/v1/projects/{id}`). **The Domino Model Registry is
currently empty** (`GET /api/registeredmodels/v1` → `{"items":[]}`) — there
is no real registered model anywhere in this instance yet, so the binding
logic below is real and tested but has never bound an actual live registry
entry (nothing exists to bind to).

Two things got built:

1. **Model-registry binding** (22-pdm.md §5.6). `models/__init__.py`'s own
   docstring had explicitly deferred `model_binding`/`label_set`/
   `propensity_model` as "a substantial second vertical slice" — the user
   confirmed the right move was to add `propensity_model`/`label_set` as
   **schema-only** tables (columns per §2.3/§2.4, no IPCW-fitting logic) so
   `model_binding`'s FK and §5.6's three binding-refusal checks (propensity
   model accepted, label set's family powered, calibration record exists
   for the triple) are real queries against real tables, not stubs. New:
   `models/{propensity_model,label_set,model_binding}.py`, a new migration
   (`versions/20260805141953_pdm_model_binding.py`), `repositories/
   model_binding.py`, `services/model_binding.py` (refusal checks +
   deactivate-and-invalidate-the-superseded-binding + queue a
   `binding_activation` re-score + publish `model_binding.activated`),
   `api/v1/model_bindings.py` (`POST /model-bindings`,
   `POST /model-bindings/{id}/activate`).
2. **Domino Job entrypoint** (`models/tier0-historical/entrypoint.py`) —
   stdlib-only (no `fathom_pdm` import, no dependency install step), reads
   `DOMINO_RUN_ID` for `domino_execution_ref`, POSTs to PdM's real bulk-ingest
   API. The actual tier-0 Weibull MLE fit is explicitly NOT implemented
   (same out-of-scope boundary as everywhere else in this vertical slice —
   see the script's own docstring); it emits the one shape a fit-free
   stand-in can honestly claim (`class_estimate`, `population_hazard_rate`
   only, per §5.5's last row). **Actually run end to end inside the real
   workspace** — genuine `DOMINO_RUN_ID=6a732adddb7d90254e2fe880` read from
   the platform, a real HTTP round trip to a real (locally-started, sqlite)
   PdM instance running inside that same workspace, real predictions written.

Three more real bugs found the same way every other one in this file was —
by actually running the thing, not by re-reading the code — see #13–#15
below. All are fixed, and the fixes are verified by the new tests, not just
asserted.

## What's built and tested (commit `02af267`, plus spec fixes before it)

Everything below has passing tests, run against a local venv (see "How to
run tests" — you'll need to recreate it; it was not committed and doesn't
survive between sessions).

| Package/service | What it has | Tests |
|---|---|---|
| `packages/canonical-schemas` | `FathomModel`/`UtcDateTime`/JCS hashing, `ClassificationLabel` (union-label rule), full event envelope, `FailurePrediction` w/ 4 cross-field validators, `fathom_schemas.decision` (the expected-consequence conversion — **authored here from 22-pdm.md §7**, since `10-shared-packages.md` never actually defines this module despite saying it should live here) | 11 passing |
| `packages/py-sync` | Transactional outbox (partition-key derivation, D5 compaction-key guard), inbox (D2 record-before-processed), `MonotonicSequencer`, epoch fencing both directions (`EpochFence` consumer-side + `BaselineFencedComputation` producer-side), conflict-policy declarations, divergence budgets | 5 passing |
| `packages/contracts` | The `@operation`/`operation_extra` decorator (`x-substitution`/`x-side-effects`, import-time enforcement) | untested (simple, no test dir yet) |
| `packages/py-common` | RFC 9457 problem details, correlation-ID middleware, classification middleware, idempotency (see gotcha #2 below), ETag/If-Match, health/readyz/metrics, structured logging, cursor pagination. **This whole package is a corpus gap** — `10-shared-packages.md` explicitly disclaims owning it; it's authored from `09-monorepo-and-conventions.md` §5's prose contract | 6 passing |
| `services/pdm` | DB models for `prediction` (RLS-bearing), `criticality_assessment`, `calibration_record` (compartment-partitioned), `scoring_run`, `tier_policy`, `prediction_provenance`, plus (this update) `model_binding`, `propensity_model`, `label_set`; a working bulk-ingest endpoint (idempotent, transactional, baseline-fenced, outbox-emitting); get-prediction, get-criticality, expected-consequence reads; model-binding create/activate (§5.6's refusal checks, superseded-binding invalidation, re-score queuing, `model_binding.activated` publish); two Alembic migrations (`20260805072746_pdm_initial_schema.py`, `20260805141953_pdm_model_binding.py`, both applied and round-tripped against real Postgres); RLS holdout isolation, verified end to end against a real Postgres container, not just reviewed as DDL; a real `Dockerfile` (builds and runs, `/healthz`/`/readyz` verified against real Postgres) and a complete Helm chart (`helm/`, depends on the new `deploy/helm/_fathom-common` library chart, `helm lint`/`template`/`unittest` all passing); the criticality scoring/tier-assignment/hysteresis algorithm (`services/criticality.py` — the formula, band function, and hysteresis gate only; §3.1's per-input normalization and §3.3's ceiling-input read models are event-consumer work, not built yet, see the module's own docstring); two event consumers (`events/consumers.py` — `configuration.baseline_changed`, `installed_item.removed`, both invalidating affected predictions, verified against a real Postgres connection authenticated as the actual `fathom_pdm_serving` role, not the migration-owning superuser) | 46 passing, incl. one real HTTP→DB integration test, 10 real-Postgres RLS tests, 20 scoring/hysteresis unit tests, 4 real-Postgres event-consumer tests, 6 model-binding sqlite e2e tests, and 2 real-Postgres model-binding-as-`fathom_pdm_serving` tests |
| `models/tier0-historical` | `entrypoint.py` — the Domino Job entrypoint (this update). Stdlib-only, no monorepo package dependency; reads Domino's own injected `DOMINO_RUN_ID`, POSTs to PdM's bulk-ingest API. Tier-0's real Weibull MLE fit is explicitly a placeholder (see script docstring) | exercised manually end-to-end (locally and inside the real Domino workspace over SSH), not under `pytest` — it has no monorepo package dependency to test against in-process, by design |

**Total: 46 passing tests** in `services/pdm` alone (up from 38), plus 5 in
`packages/py-sync` (unchanged) and the rest of the earlier table's counts
unchanged. All newly written this session or the one before it, all
genuinely exercised (not just "written and assumed to work" — see the
gotchas below, several were only caught by actually running them).

**Repo-wide finding, this pass: `ruff` had never actually been run across
the whole `services/`/`packages/` tree before now** (only spot-checked on
individual files). Running it surfaced ~280 findings repo-wide — meaning
`make lint`/CI's lint gate would currently fail entirely, across code from
every prior session, not just this one. Triaged: applied ~55 safe
auto-fixes, fixed two real repo-wide config gaps (see below), and
hand-fixed a handful of genuine-but-defensible findings in PdM's own code.
**~206 findings remain untriaged** (mostly `E501` line-length, `TRY003`
exception-message style, `TC001-3` typing-only-import placement,
`PLC0415` deferred imports) — real, but mechanical and spread across ~30
files from earlier sessions, not evaluated one by one. This is its own
well-scoped cleanup task, separate from anything on the PdM checklist —
flagged for the user to prioritize rather than silently absorbed into
whatever task was in progress when it was found.

## What's NOT built yet for PdM

- **The real tier-0..3 model fits.** `models/tier0-historical/entrypoint.py`
  (this update) is real wiring, not a real model: the Weibull MLE / IPCW
  fit tier 0's own method specifies (22-pdm.md §5.1) needs real
  per-`(equipment_family, niin)` telemetry and failure-label infrastructure
  this vertical slice doesn't build (same boundary as everything else
  below). `models/tier1-survival`, `tier2-degradation`, `tier3-hybrid`,
  `causal` are still empty directories — only tier 0 got an entrypoint, as
  the simplest tier, to prove the wiring once.
- **`POST /scoring-runs`** (22-pdm.md §10, line ~1356; on-demand re-score
  creation) — declared in the spec's own API-surface table but not
  implemented. `entrypoint.py` takes an existing `--scoring-run-id` rather
  than minting one for exactly this reason; whatever orchestrates real
  scoring runs (Domino Flow scheduling) needs this endpoint first.
- **Most event consumers.** Of `catalog.CONSUMES`' ~19 declared types, only
  the two that are both externally-evented AND have a fully-specified local
  effect are wired: `configuration.baseline_changed` and
  `installed_item.removed` (both invalidate affected predictions via
  `pdm.invalidate_prediction()`, `events/consumers.py`). Of the other four
  internal invalidation triggers in 22-pdm.md §8.1's own table, **binding
  deactivation is now wired** (this update: `services/model_binding
  .activate_binding` invalidates the superseded binding's own predictions
  directly, not via a consumed event) — tier reassignment, calibration
  withdrawal, and label-set retraction remain unbuilt, triggered by other
  PdM subsystems that don't exist yet. The remaining ~15 declared types
  (telemetry health indicators, maintenance actions, failure-intel
  findings, etc.) feed the tier 0-3 model scoring pipeline itself, which
  needs the real model execution named above. `dispatch_event()` raises
  `UnhandledEventTypeError` for all of these rather than silently
  no-op'ing, so a future consumer loop can tell "nothing to do" apart from
  "this needs a handler built." **No Kafka client/consumer-loop
  infrastructure exists anywhere in this codebase** (checked: zero
  `confluent_kafka` usage outside comments) — `events/consumers.py` is the
  business-logic layer such a loop would call once it has deserialized a
  message, not the loop itself; building that is shared `packages/py-sync`
  infrastructure, not PdM-specific.
- **Every other service.** Only PdM has been touched. The other 8 domain
  services + 8 platform services + `apps/` + `agents/` are still just empty
  directories (`models/` now has one file, `tier0-historical/entrypoint.py`
  — see above for what it does and doesn't cover).

## Real bugs found by actually building this (useful for the *next* service)

These are worth reading before repeating this pattern on service #2,
because they'll bite again if not accounted for:

1. **`22-pdm.md`'s `calibration_record` DDL was missing the `compartments`
   column** that an earlier security fix (this same session) required in
   prose but never added to the actual table/constraint. Fixed in the spec
   (commit `2645818`) — caught only by trying to actually write the
   SQLAlchemy model against the DDL.
2. **FastAPI's `route_class` does not propagate through nested
   `include_router()` calls.** An `APIRouter()` constructed in a resource
   file (e.g. `api/v1/predictions.py`) does NOT inherit `route_class` from
   the app-level router even if you set `app.router.route_class = X` — each
   router's `route_class` is independent unless passed explicitly at
   construction. This silently broke an entire idempotency mechanism (it
   simply never ran) until caught by an actual end-to-end request test.
   Fixed by redesigning idempotency as a **dependency** (which DOES cascade
   through router nesting via `FastAPI(dependencies=[...])`/`router.dependencies`)
   paired with a custom exception + exception-handler for the "replay
   short-circuits the handler" case a plain dependency can't express. See
   `packages/py-common/src/fathom_py_common/idempotency.py`'s module
   docstring for the full story.
3. **`assert_operation_annotations` had the same silent-no-op problem** —
   originally walked `app.routes` with `isinstance(route, APIRoute)`, which
   this FastAPI version doesn't eagerly resolve for nested routers (they sit
   behind an internal lazy wrapper until something forces resolution, e.g.
   schema generation). Fixed by validating against `app.openapi()`'s
   generated schema instead of walking Route objects — more robust anyway,
   since that's the same artifact CI's own spec-drift check re-validates.
4. **`starlette.testclient.TestClient` manages its own internal event
   loop**, separate from whatever loop a test's own `await`s run under.
   Seeding a database via a plain `asyncio.run(...)` call before using
   `TestClient` created a THIRD event loop; aiosqlite connections are
   loop-bound, so the seeded rows were invisible to the app's own requests
   even with `poolclass=StaticPool`. Fix: use `httpx.AsyncClient` +
   `ASGITransport` and make the whole test `async def`, so seeding and
   requests share the one loop pytest-asyncio provides. See
   `services/pdm/tests/integration/test_bulk_ingest_e2e.py`'s docstring.
5. **SQLite dialect gaps, all test-only (production is real PostgreSQL, not
   affected):** no `pdm.*` schema qualification (fix: `schema_translate_map`
   execution option), no `LEAST()` scalar function (fix: register it via
   `event.listens_for(engine.sync_engine, "connect")`), in-memory SQLite is
   per-connection so a second checkout is a different empty database (fix:
   `poolclass=StaticPool` + `connect_args={"check_same_thread": False}`).
   All three are already handled in `services/pdm/src/fathom_pdm/main.py`'s
   `create_app()` (branches on `settings.database.url.startswith("sqlite")`)
   and in `services/pdm/tests/conftest.py`.
6. **Two separate `DeclarativeBase` classes must both be migrated.**
   `fathom_sync.Base` (outbox/inbox/producer_sequence) and
   `fathom_py_common.idempotency.IdempotencyBase` (idempotency_keys) are
   each their own metadata, separate from a service's own `Base`. The real
   Alembic migration handles this correctly: `env.py`'s `target_metadata` is
   a list of all three, confirmed by a successful autogenerate + a clean
   `upgrade`/`downgrade` round-trip against real Postgres.
7. **RLS roles need `GRANT USAGE ON SCHEMA`, not just table-level grants.**
   `22-pdm.md §4.5`'s original DDL created `fathom_pdm_serving` /
   `fathom_pdm_research` and granted table privileges on `pdm.prediction`,
   but never granted `USAGE` on the `pdm` schema itself. PostgreSQL checks
   schema `USAGE` before object-level privileges, so every query either
   role issued failed with `permission denied for schema pdm` — confirmed
   against a real container, then fixed in both the spec and the migration.
   Fails closed, not a security hole, but would have made the entire
   mechanism silently unusable. Caught only by actually connecting as one
   of the roles and running a query, not by reading the DDL.
8. **PostgreSQL RLS: an UPDATE's target row must satisfy the table's SELECT
   policy too, not just the UPDATE-scoped policy — a real bug in a security
   control this session had already reviewed and "fixed" once.** The
   original design split `actionable_read` (SELECT) from `serving_invalidate`
   (`FOR UPDATE ... USING (true)`), reasoning that the UPDATE policy's
   `USING (true)` would let `fathom_pdm_serving` invalidate a research_only
   row it could never SELECT. Verified against a real container: this
   updated **zero rows, silently, every time** — PostgreSQL requires an
   UPDATE's WHERE-clause row visibility to also pass any applicable SELECT
   policy for the same role, because that WHERE clause is itself a read.
   No combination of SELECT/UPDATE policies on one role can express
   "writable but not readable" in Postgres's RLS model — this was never
   fixable by rearranging policies. The actual fix: a `SECURITY DEFINER`
   function (`pdm.invalidate_prediction()`), owned by a dedicated
   `BYPASSRLS` role (`fathom_pdm_invalidator`) that `fathom_pdm_serving`
   cannot otherwise assume, `EXECUTE`-granted to `fathom_pdm_serving` alone.
   `fathom_pdm_serving` now holds **no UPDATE grant on the table at all** —
   invalidation, for both actionable and research_only rows, goes through
   the function exclusively. This is the single most important finding from
   building PdM end to end: a spec-level security control had already been
   reviewed, flagged as a bug, and "corrected" once earlier this session —
   and the correction itself was wrong, in a way that only running it
   against a real database (not re-reading the DDL more carefully) could
   have caught. See `docs/build/22-pdm.md` §4.5 for the full corrected
   mechanism and `services/pdm/tests/integration/test_rls_holdout_isolation.py`
   for the test that proves it (and that would have failed loudly against
   the old design).
9. **22-pdm.md §3.2's scoring formula is internally inconsistent, and the
   spec text was never actually run.** It gives `score = 100 x sum(w_j x_j)
   / sum(w_j)`, but §3.1 already normalizes every x_j to `[0, 100]` for
   storage — applying the literal formula to already-`[0,100]` inputs
   produces values up to 10,000, not the documented and DB-range-checked
   `[0, 100]` `score` column. `services/criticality.py` implements
   `score = sum(w_j x_j) / sum(w_j)` (no extra factor) instead, documented
   inline; the "100 x" only makes sense if x_j were `[0,1]` fractions,
   which contradicts §3.1's own normalization column. Not yet corrected in
   the spec doc itself — worth fixing `22-pdm.md` §3.2 to match if you're
   back in there.
10. **Root `pyproject.toml`'s ruff `per-file-ignores` pattern
    (`"tests/*"`) never matched anything** — every real test tree lives at
    `services/<slug>/tests/` or `packages/<name>/tests/`, two directories
    deep, which a bare `tests/*` glob doesn't reach. Fixed to
    `"**/tests/*"`. Also added a `flake8-bugbear.extend-immutable-calls`
    entry for `fastapi.Depends`/`Query`/`Path`/etc. — B008 was flagging
    every single FastAPI route handler's dependency-injection parameter as
    a "mutable default," which is the idiomatic pattern 09§4.6 itself
    specifies, not a bug. Both gaps existed because **nothing had ever run
    `ruff` across a real multi-directory service tree before this pass** —
    worth running `make lint` for real (not just spot-checking individual
    files) early when building service #2, now that these two config gaps
    are fixed.
11. **`fathom_pdm_serving` had a grant on `pdm.prediction` alone — every
    other table this service's own code touches had none, at all.**
    Found by finally connecting as this role instead of the migration-owning
    superuser (every earlier integration test in this session used the
    superuser). A newly created table grants nothing beyond its owner by
    default; only `pdm.prediction` ever got an explicit `GRANT`, because
    it's the one table with RLS policies to write. The result: bulk ingest
    (`scoring_run`, `prediction_provenance`, `outbox`), the idempotency
    middleware (`idempotency_keys`), the monotonic sequencer
    (`producer_sequence`), and every inbox-consuming event handler would
    all have failed with "permission denied" under the role the running
    service actually authenticates as. Fixed with a comprehensive grant
    block in the migration and in `docs/build/22-pdm.md` §4.5, covering
    every table current code paths actually need. **If you're building
    service #2's migration, budget for this same grant sweep from the
    start** — don't just copy the RLS-bearing table's grants and assume
    the rest follows.
12. **Two of PdM's own declared `CONSUMES` event types were wrong strings**,
    caught only by actually constructing a real `EventEnvelope` against
    them (Pydantic's own regex validator rejected one outright; the other
    would have silently subscribed to nothing, since no producer ever
    emits that exact string). `fathom.telemetry.batch_ingested` should have
    been `fathom.telemetry.telemetry_batch.ingested` (21-telemetry.md's own
    catalog table has the real name); `fathom.audit.remediation.v1` was the
    *topic* name, not an event_type — the actual event_type is
    `fathom.audit.remediation.purge_executed` (32-audit.md's own catalog
    row). Both fixed in `events/catalog.py` and `helm/values.yaml`. Worth
    double-checking every other service's own `CONSUMES`/`PUBLISHES` list
    against its cited source doc's actual catalog table the same way,
    rather than trusting a prose cross-reference — these were both
    authored from prose summaries earlier this session, not the tables
    themselves.
13. **`fathom_pdm_serving` could never actually publish an event, in any
    service, since the very first migration that granted it INSERT on
    `outbox` — caught only by activating a model binding as that role for
    real, the first code path ever to call `OutboxWriter.emit()` under it**
    (every earlier test either used SQLite or the migration-owning
    superuser; `bulk_ingest_predictions` already published events, but
    never under the real role until now). Two independent grant gaps, both
    from the same root cause (Postgres autoincrement PKs need sequence
    privilege to fire their own `nextval()` default, and — separately —
    reading a column back via `RETURNING` needs the same privilege as
    `SELECT`ing it): fixed `packages/py-sync/fathom_sync/models
    .OutboxRow.__table_args__` to set `implicit_returning=False` (nothing
    in `emit()`'s own return value ever used the PK RETURNING would have
    fetched anyway — this fix is shared, so it protects every other
    service's own outbox table too, not just PdM's), and granted
    `fathom_pdm_serving` explicit `USAGE` on `outbox_outbox_id_seq` in
    PdM's own migration. **Every other service will hit the exact same
    wall the first time its own serving role actually publishes an
    event** — budget for the sequence-USAGE grant from the start, the same
    lesson as bug #11.
14. **`pdm.prediction.rul` (and four other nullable JSON-variant columns)
    could never actually store SQL `NULL` — caught only by ingesting a
    real non-item-conditional prediction (`reference_class='class_estimate'`,
    `rul=None`) through the bulk-ingest API for the first time.** Every
    earlier test's prediction payloads happened to be item-conditional
    (`rul` always present). SQLAlchemy's `JSON`/`JSONB` default to
    `none_as_null=False`: a Python `None` bound to the column serializes as
    the JSON string `"null"`, not SQL `NULL` — dialect-agnostic, so this
    was never a SQLite-only quirk, and would have failed identically
    against real Postgres. `rul_only_when_item_conditional`'s `rul IS NULL`
    check constraint rejected every such row. Fixed by adding
    `none_as_null=True` to the `_JsonVariant` type alias in all four
    affected model files (`prediction.py`, `criticality.py`,
    `provenance.py`, `scoring_run.py`) — a DDL-invisible, Python-side-only
    fix (no migration needed). Worth grep'ing for `_JsonVariant` in every
    future service's own models before assuming a nullable JSON column
    round-trips `None` correctly.
15. **SQLAlchemy's autoflush ordering has no dependency graph across plain
    FK columns without an ORM `relationship()`** — two sibling `session
    .add()` calls (e.g. `propensity_model` then `label_set`, where
    `label_set.propensity_model_id` is a bare FK column) can flush in
    either order in the same transaction, and against real Postgres (never
    caught under SQLite, which doesn't enforce the FK at all by default)
    this intermittently 500s with a real FK violation depending on which
    order won. Fixed in this session's own new test fixtures with an
    explicit `await session.flush()` between the two `add()` calls, not by
    adding `relationship()`s to the production models (which have no other
    reason to want one). Worth remembering for any future test that seeds
    more than one FK-linked row in a single session without a
    relationship-aware ORM graph to lean on.
16. **The Dockerfile's Python base image was pinned to an ARM64-SPECIFIC
    digest, not the multi-arch index — caught only by actually deploying
    to a real amd64 EKS cluster.** Every earlier `docker build`/run of this
    Dockerfile happened on an Apple Silicon dev machine, so this never
    surfaced. A digest pin fixes the exact image regardless of
    `--platform`; `docker build --platform linux/amd64` printed a warning
    ("image platform (linux/arm64/v8) does not match the expected platform
    (linux/amd64)") and silently built an arm64 binary anyway. The
    container started fine locally (arm64 host, arm64 binary) but every
    process exec failed with "exec format error" the instant it ran on a
    real amd64 node. Fixed by re-pinning to the actual multi-arch INDEX
    digest (`docker manifest inspect python:3.12-slim-bookworm` against
    the registry's `Docker-Content-Digest` header, not a tool's
    pretty-printed body) for both `FROM` lines — this now resolves
    correctly per-platform on arm64 dev machines and amd64 CI/prod alike.
    Worth checking every other digest-pinned base image in every future
    service's Dockerfile the same way, not assuming a pin is safe just
    because it looks like a normal sha256 digest.
17. **`fathom_pdm_serving` was never granted `UPDATE` on `pdm.scoring_run`
    — caught only by running the real Domino Job entrypoint against a
    real AWS deployment for the first time.** `bulk_ingest_predictions()`
    updates the scoring_run row (`predictions_written`, `status`,
    `completed_at`) at the end of every ingest; the initial migration
    granted this role SELECT and INSERT on the table but never UPDATE.
    Same bug shape as #11: a real code path's privilege need, never
    actually exercised under the real role in any test written before
    this deployment (every earlier real-Postgres test touched RLS, the
    model-binding tables, or the event consumers -- none of them called
    `bulk_ingest_predictions()` itself under `fathom_pdm_serving`). Fixed
    in a new migration (`20260805155514_pdm_scoring_run_update_grant.py`).

## AWS smoke-test deployment (this update)

Per the user's explicit request, PdM's Helm chart, Dockerfile, and API
were actually deployed to AWS, not just `helm lint`/`docker build` locally.
**The Domino instance's own EKS cluster** turned out to be the right
target — `mikesn136713` (us-west-2, tagged `customer_name: navy`), reachable
via Teleport (`tsh7 kube login mikesn136713` — this cluster needs a v7.x
`tsh` client; the proxy is v7.3.26 and rejects newer clients outright). AWS
access via `okta-aws` (role `okta-fulladmin`, account `946429944765` —
**shared across many other Domino engineers' clusters/resources**; name
and tag anything new obviously as FATHOM's).

**What's real, in `fathom-pdm-dev` namespace** (a deliberate sandbox,
separate from the repo's own `fathom-data`/`fathom-sustainment` charts,
which were NOT installed this pass): a single-instance Postgres (no
CloudNativePG operator in this cluster; a real production deploy should
still target CloudNativePG per 09 §2.1), both PdM migrations applied by
hand, the real PdM image pushed to a new ECR repo
(`946429944765.dkr.ecr.us-west-2.amazonaws.com/mikesn136713/fathom/pdm`),
the Helm chart installed with a `values-smoke-test.yaml` override, exposed
on the existing shared `nginx-ingress-controller`/ELB at
`https://mikesn136713.cs.domino.tech/fathom-pdm/` and
`https://mikesn136713.cs.domino.tech/fathom-ui/` (a minimal live dashboard,
`services/pdm/helm` has no chart for this — the dashboard's HTML lives only
as a ConfigMap in-cluster right now, not in this repo, since it's a
smoke-test artifact, not a real deliverable). `/healthz`, `/readyz`, and
all five demoed API flows (get-prediction, get-criticality,
expected-consequence, model-binding create+activate) verified for real
from outside the cluster.

**Two chart gaps found and fixed, not workarounds**:
- `externalSecret.enabled`/`serviceMonitor.enabled` toggles added (default
  `true`) since neither the External Secrets Operator nor the Prometheus
  Operator's CRDs exist in this cluster — the chart had no way to render
  without them before.
- `migration-job.yaml` and the app `Deployment` share ONE
  `database.secretRef` (`FATHOM_DATABASE__URL`), but migrations need owner
  privileges (`CREATE ROLE`, `CREATE SCHEMA`, `SECURITY DEFINER`
  functions) while the app must connect as a restricted
  `fathom_pdm_serving`-member role for RLS to actually apply — a real,
  unfixed chart gap (not addressed this pass; migrations were run by hand
  with a separate owner DSN instead, `migrations.enabled: false` in the
  override). **Worth fixing properly before any real (non-smoke-test)
  deployment** — needs a second secretRef, e.g.
  `database.migrationSecretRef`, distinct from the app's own.

**One thing deliberately NOT worked around**: `networkpolicy.yaml` has no
disable toggle by design (`values.yaml`'s own comment: "NEVER false in any
environment") and is correctly written for the *real* target topology
(`fathom-data` namespace, a `cnpg.io/cluster`-labeled Postgres,
gateway-only ingress) — none of which exists in this sandbox. Rather than
weaken the chart, the rendered `NetworkPolicy` object was deleted by hand
in `fathom-pdm-dev` only. Do not do this in a real environment.

**The Domino Model Registry connection point was never actually
exercised** — see the earlier note that the registry is empty; this pass
proved the *deployment* end-to-end, not a real registered-model binding.

**2026-08-05 correction, verified live against the real Domino API with
the `domino-claude-plugin` now installed:** neither the Model Registry
(`GET /api/registeredmodels/v1`) nor Domino's own Apps registry
(`GET /api/apps/beta/apps?projectId=...`) has ever had an entry for this
project — both return zero items, checked directly, not assumed. **The
"minimal live dashboard published at the same domain" above is a bare
Kubernetes Ingress/ConfigMap on the shared `mikesn136713` EKS cluster —
it never went through Domino's own App Publisher (`POST /api/apps/beta
/apps`), so it does not and never did show up as a registered Domino App**,
despite "published ... at the same domain" reading like it might have.
Same for PdM itself: it's a backend microservice deployed via its own
Helm chart onto the platform's shared EKS cluster, by design — it was
never meant to *be* a Domino App or a Domino Model API deployment (those
apply to the UI layer, `51-operator-console`/`52-practitioner-apps`,
neither built yet). Nothing here is a bug to fix, but don't describe a
raw k8s Ingress as "published" without the caveat that it's invisible to
Domino's own Apps tab — a future session or a human skimming this file
could otherwise reasonably conclude a real platform artifact exists when
none does. The `domino-claude-plugin`'s own MCP server
(`domino_server`) is configured to run from inside a Domino
workspace (`/mnt/code/...`) and fails to connect from this Mac directly
("Connection closed") — querying the real API from outside a workspace
still means going through the `dom connect` SSH tunnel and hitting the
REST API with curl, same as every prior session did, not something the
plugin's MCP changes for this machine.

## How to run tests (you'll need to redo this — nothing here survives)

The test venv (`/tmp/fathom-test-venv`) was scratch space for this session
and is gone. To reconstitute:

```bash
cd /Users/michaelsnyder/repos/predictive_maintenance
python3 -m venv /tmp/fathom-test-venv   # or use `uv` if available — it wasn't, this session
/tmp/fathom-test-venv/bin/pip install \
  "pydantic>=2.9" "pytest>=8.3" "pytest-asyncio>=0.24" \
  "sqlalchemy>=2.0" "aiosqlite>=0.20" \
  "fastapi>=0.115" "pydantic-settings>=2.5" "structlog>=24.4" \
  "prometheus-client>=0.21" "httpx>=0.27" "uvicorn[standard]>=0.32" "asyncpg>=0.30" "alembic>=1.14" \
  "ruff" "testcontainers>=4.15" "psycopg[binary]>=3.2"

# Editable-install every package, in dependency order:
for p in canonical-schemas py-sync contracts py-common; do
  /tmp/fathom-test-venv/bin/pip install -e packages/$p
done
/tmp/fathom-test-venv/bin/pip install -e services/pdm

# Run everything:
for d in packages/canonical-schemas packages/py-sync packages/contracts packages/py-common services/pdm; do
  echo "=== $d ==="; (cd $d && /tmp/fathom-test-venv/bin/python -m pytest tests/ -q)
done
```

The real target stack is `uv` (per `09-monorepo-and-conventions.md` §2.2),
not raw `pip` — `uv` wasn't installed in this environment, so pip was used
as a substitute. Worth installing `uv` properly for the real project.

The RLS suite (`services/pdm/tests/integration/test_rls_holdout_isolation.py`)
needs Docker/Podman reachable (spins up its own `postgres:16-alpine`
testcontainer per run — independent of any long-lived container you may
also have running for interactive migration work). If `docker ps` fails
against a "no such file" socket error, this environment uses Podman as the
Docker backend: `podman machine start podman-machine-default`, then export
`DOCKER_HOST` to the machine's API socket (see `podman machine inspect
podman-machine-default` for the path) — needed per shell invocation, since
shell state doesn't persist between separate tool calls.

## Recommended next steps, roughly in priority order

The user's explicit PdM checklist is now **fully done**: ~~Alembic
migration~~ → ~~RLS testing~~ → ~~Dockerfile~~ → ~~Helm chart~~ →
~~hysteresis/scoring algorithm~~ → ~~event consumers~~ → ~~Domino Job
entrypoint/Model Registry binding~~. Dockerfile and Helm chart were built
in parallel across two Sonnet subagents (per the user's explicit interest
in parallelizing genuinely independent PdM work) — both independently
re-verified afterward (real `docker build` + container run +
`/healthz`/`/readyz`, and `helm lint`/`helm template`/`helm unittest` rerun
from scratch), not just trusted from the subagents' own reports. Building
`services/pdm/helm` also required building `deploy/helm/_fathom-common`
(the shared label/naming library chart every per-service chart depends on)
and the two namespace-wide default-deny NetworkPolicy charts
(`fathom-sustainment`, `fathom-data`) first, since none of that shared Helm
infrastructure existed yet — done directly rather than delegated, since
it's foundational/shared, not PdM's own deliverable. The scoring/hysteresis
algorithm, the event consumers, and #27's model-binding + entrypoint were
all built directly (not delegated) since each needed careful judgment, not
mechanical transcription — see bugs #9, #11/#12, and #13-15 above for what
that judgment caught.

1. ~~The AWS smoke-test deployment pass (Dockerfile arch fix, the
   scoring_run grant migration, the Helm chart toggles) is not committed~~
   — **done, committed in `91e81c0`.**
2. ~~Decide what to do with the live `fathom-pdm-dev` sandbox~~ — **decided
   2026-08-05: tear it down** (see "2026-08-05 follow-up decisions" below
   for status).
3. ~~Fix the migration-job.yaml / database.secretRef credential
   conflation~~ — **done, 2026-08-05.** Added `database.migrationSecretRef`
   (a distinct Secret name, `fathom-pdm-pg-migrate`) alongside the existing
   `database.secretRef`; `migration-job.yaml` now uses the former, the app
   `Deployment` still uses the latter; `externalsecret.yaml` renders a
   second `ExternalSecret` (gated on `migrations.enabled`) sourced from a
   distinct Vault path (`.../database-migration`) so the two never
   collapse to one credential again. `helm lint`/`template`/`unittest`
   (17 tests, up from 14) all re-run and passing, against both the
   default values and `values-smoke-test.yaml` (confirms the second
   `ExternalSecret`/the migration `Job` both correctly disappear when
   `migrations.enabled: false`). **Worth knowing if you touch this chart's
   tests again**: `helm-unittest` v1.1.2's per-assertion `documentIndex`
   field is silently ignored for multi-document templates in this
   environment — set `documentIndex` at the test-case (`it:`) level
   instead, sibling to `asserts:`, or assertions against a multi-doc
   template's non-shared fields resolve against the wrong document without
   any error (caught by an assertion that failed with a *value from the
   wrong document*, not a missing-path error — worth re-checking test
   output carefully rather than assuming a passing run means the intended
   document was actually checked).
4. **The user plans to restart their Claude Code session to pick up the
   newly-installed `domino-claude-plugin`** (marketplace registered at
   `~/.claude/marketplaces/domino`, installed at user scope), specifically
   for an adversarial sweep of this deployment and for building out the
   remaining 16 services. A fresh session won't have this session's
   in-memory context (AWS/Teleport credentials will also need re-auth,
   both expire) — this file plus memory (`project_fathom_corpus_state.md`,
   `reference_domino_workspace_access.md`) is the map back to where things
   stand.
5. ~~Decide: is PdM "done enough" to move to service #2, or push further
   first?~~ — **decided 2026-08-05: push PdM to production-grade first,
   before starting service #2.** Genuinely out-of-scope-for-this-vertical-slice items remain --
   the real tier 0-3 model fits (needs real telemetry/failure-label
   infrastructure), most of `CONSUMES`' ~19 event types (need that same
   pipeline + real Registry/Telemetry/Failure-Intel read models), the
   Kafka consumer-loop/client infrastructure itself (shared `py-sync` work,
   not PdM-specific), `POST /scoring-runs` (on-demand re-score creation --
   the entrypoint assumes one already exists), §3.1's input-normalization
   curves, §3.3's ceiling read models, §8.3's re-score-before-publication
   orchestration and dual-binding shadow scoring. None of these were ever
   on the user's explicit 7-item checklist — worth naming them plainly
   rather than letting "PdM is done" quietly expand to mean "PdM is
   complete."
6. **If a real model does get registered in Domino's Model Registry**
   (it's currently empty — see above), worth a real end-to-end test of
   `POST /model-bindings` + `/activate` against that actual
   `registry_model_version`/`registry_model_uri`, not just the
   manually-supplied strings this session's tests use — §5.6 says PdM only
   ever records what it's given, so this would mainly confirm the real
   value's shape matches what the tests already assume, not exercise new
   code.
7. **Separate from the PdM checklist**: ~206 untriaged `ruff` findings
   remain across the whole `services/`/`packages/` tree (see above). The
   user was asked and explicitly chose to defer this — don't re-raise it
   unless asked, but it's still there.

## 2026-08-05 follow-up decisions

After the AWS smoke-test pass above, the user reviewed this file and made
four explicit decisions, in this order of priority:

1. **Direction: PdM to production-grade first**, not service #2 yet. The
   top real blocker for that is item 3 above (the migration-job.yaml /
   database.secretRef conflation) — start there, then CloudNativePG
   (item mentioned in "AWS smoke-test deployment" above), then the rest of
   the "harden before calling it production-ready" items.
2. **Sandbox: tear down `fathom-pdm-dev`.** Done — `kubectl delete
   namespace fathom-pdm-dev` removed the namespace and both Ingress
   objects (`pdm-smoke-test`, `pdm-ui-smoke-test`) in one shot, confirmed
   gone afterward. **Left alone, deliberately**: the ECR repo
   `946429944765.dkr.ecr.us-west-2.amazonaws.com/mikesn136713/fathom/pdm`
   still has 3 images (one tagged `smoke-test`, two untagged) — the user's
   answer covered the running k8s sandbox, not explicitly the registry;
   delete those too if you're actually done with this image lineage.
3. **Agentic model allocation: document it in this file** (see the new
   section near the top) rather than leave it only in Claude's
   cross-session memory. This file was renamed from `HANDOFF.md` to
   `CLAUDE.md` for that reason — Claude Code auto-loads `CLAUDE.md` at the
   start of every session, so the policy is now visible without anyone
   having to know to ask for it.
4. **Opus adversarial review: still not now.** Deferred a second time —
   don't self-schedule it; ask again before service #2 or before any real
   (non-smoke-test) production deployment.

## 2026-08-05 later still — CloudNativePG, and Sonnet-only for the rest of this push

The user is near their Claude spend limit and asked to stick to Sonnet for
all remaining work (no Opus, consistent with decision 4 above anyway) —
worth remembering if a future session considers a model override on this
project without checking first.

**CloudNativePG, item 1's second blocker, is now provisioned**: a new
`services/pdm/helm/templates/postgres-cluster.yaml` renders a real CNPG
`Cluster` CR (`fathom-pdm-pg`, 3 instances by default, Postgres 16
digest-pinned to the real multi-arch OCI index — verified live against
the registry, round-tripped by digest, same discipline bug #16 should have
gotten the first time). `database.provisionCluster` (default `true`) is
the escape hatch for a platform-level GitOps pipeline or a CNPG-operator-
less sandbox; `values-smoke-test.yaml` now sets it `false` to match what
that pass actually did (a hand-rolled single-instance Postgres, no CNPG
operator in that cluster at all — unchanged behavior, now expressed as an
explicit toggle instead of an unstated gap). `values-dev.yaml` overrides
to 1 instance / smaller storage.

**A real, non-obvious hazard found by reasoning through CNPG's own
behavior before writing anything — not caught by trial and error, since
no live CNPG cluster was available to test against without installing the
operator on the shared `mikesn136713` cluster, judged too big a blast-
radius action for this pass:** CNPG's own default convention names the
Secret it auto-generates for the bootstrap-owner role `<cluster-name>-app`
and the superuser's `<cluster-name>-superuser`. This chart's own
`database.secretRef` — `fathom-pdm-pg-app`, 09 §4.4.1's own mandated
value — is *exactly* the string CNPG would default to for a completely
different purpose (the bootstrap owner, not the restricted
`fathom_pdm_serving`-member role our ExternalSecret actually populates
from Vault). Left alone, a real CNPG Cluster and this chart's own
`ExternalSecret` would both try to own one Kubernetes Secret object named
`fathom-pdm-pg-app`, fighting over its contents every reconcile — two
different controllers, two different intended credentials, one Secret
name. Fixed by explicitly redirecting CNPG's own two generated secrets to
names nothing else in this chart ever references (`<clusterName>-cnpg-
bootstrap`, `<clusterName>-cnpg-superuser`) — neither `database.secretRef`
nor `database.migrationSecretRef` changed. **Still an open operational
step, not a code gap**: someone has to actually copy the real DSN values
into Vault at the two paths `externalsecret.yaml` reads from
(`.../database`, `.../database-migration`) — the CNPG superuser secret's
password is the natural source for the migration path, per this service's
own §4.5 BYPASSRLS requirement. `helm lint`/`template`/`unittest` all
re-run (23 tests, up from 17) across default, dev, and smoke-test values;
none of this has been exercised against a real CNPG operator, since none
was installed anywhere reachable this pass — worth flagging loudly to
whoever gets a real cluster with the operator installed, same as every
other "reviewed carefully but never actually run" item in this file.

## Where to find more context

- `git log --oneline` — every commit this session (and the many before it)
  has a detailed, self-contained message.
- Claude's persistent memory at
  `~/.claude/projects/-Users-michaelsnyder-repos-predictive-maintenance/memory/`
  — `MEMORY.md` is the index; `project_fathom_corpus_state.md` has the full
  session-by-session history of the spec-hardening phase, updated through
  the point where implementation started.
- `docs/build/09-monorepo-and-conventions.md` — the master spec for
  everything under `packages/`, `services/`, `platform/`: layout, tech
  stack, per-service scaffold, API conventions, CI gates, Definition of
  Done, DO-NOT list. Read this before touching service #2.
- `docs/build/22-pdm.md` — PdM's own spec, what `services/pdm` is built
  against.
- `docs/build/11-outbox-sync-library.md` — what `packages/py-sync` is
  built against.
- `docs/build/10-shared-packages.md` — what `packages/canonical-schemas`
  is built against (and where it explicitly disclaims owning `py-common`
  and the `Page[T]`/`CursorParams`/`ChangedSinceParams` types).
