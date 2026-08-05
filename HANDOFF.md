# FATHOM — handoff / continuation notes

**Read this first if you're picking this up cold.** Last updated 2026-08-05
(second update, same day: Alembic migration + real-Postgres RLS testing now
done — see the updated tables below). Everything below is committed on
`main` unless stated otherwise. `git log --oneline` tells the true story in
detail; this file is the map.

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
tested, committed skeleton — see "What's built" below.

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
| `services/pdm` | DB models for `prediction` (RLS-bearing), `criticality_assessment`, `calibration_record` (compartment-partitioned), `scoring_run`, `tier_policy`, `prediction_provenance`; a working bulk-ingest endpoint (idempotent, transactional, baseline-fenced, outbox-emitting); get-prediction, get-criticality, expected-consequence reads; a real Alembic migration (`versions/20260805072746_pdm_initial_schema.py`, applied and round-tripped against real Postgres); RLS holdout isolation, verified end to end against a real Postgres container, not just reviewed as DDL; a real `Dockerfile` (builds and runs, `/healthz`/`/readyz` verified against real Postgres) and a complete Helm chart (`helm/`, depends on the new `deploy/helm/_fathom-common` library chart, `helm lint`/`template`/`unittest` all passing); the criticality scoring/tier-assignment/hysteresis algorithm (`services/criticality.py` — the formula, band function, and hysteresis gate only; §3.1's per-input normalization and §3.3's ceiling-input read models are event-consumer work, not built yet, see the module's own docstring); two event consumers (`events/consumers.py` — `configuration.baseline_changed`, `installed_item.removed`, both invalidating affected predictions, verified against a real Postgres connection authenticated as the actual `fathom_pdm_serving` role, not the migration-owning superuser) | 38 passing, incl. one real HTTP→DB integration test, 10 real-Postgres RLS tests, 20 scoring/hysteresis unit tests, and 4 real-Postgres event-consumer tests |

**Total: 60 passing tests**, all newly written this session, all genuinely
exercised (not just "written and assumed to work" — see the gotchas below,
several were only caught by actually running them).

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

- **The Domino Job entrypoint script** and the Domino Model Registry
  binding logic (22-pdm.md §5.6) — nothing Domino-specific has been
  exercised against a live workspace at all. The `.env.example` has
  placeholder `FATHOM_DOMINO__*` vars with no real values.
- **Most event consumers.** Of `catalog.CONSUMES`' ~19 declared types, only
  the two that are both externally-evented AND have a fully-specified local
  effect are wired: `configuration.baseline_changed` and
  `installed_item.removed` (both invalidate affected predictions via
  `pdm.invalidate_prediction()`, `events/consumers.py`). The other four
  invalidation triggers in 22-pdm.md §8.1's own table are internal (tier
  reassignment, binding deactivation, calibration withdrawal, label-set
  retraction) — triggered by other PdM subsystems that don't exist yet, not
  by consuming an event at all. The remaining ~15 declared types (telemetry
  health indicators, maintenance actions, failure-intel findings, etc.) feed
  the tier 0-3 model scoring pipeline itself, which needs real model
  execution (Domino Jobs) this vertical slice doesn't build. `dispatch_event()`
  raises `UnhandledEventTypeError` for all of these rather than silently
  no-op'ing, so a future consumer loop can tell "nothing to do" apart from
  "this needs a handler built." **No Kafka client/consumer-loop
  infrastructure exists anywhere in this codebase** (checked: zero
  `confluent_kafka` usage outside comments) — `events/consumers.py` is the
  business-logic layer such a loop would call once it has deserialized a
  message, not the loop itself; building that is shared `packages/py-sync`
  infrastructure, not PdM-specific.
- **Every other service.** Only PdM has been touched. The other 8 domain
  services + 8 platform services + `apps/` + `agents/` + `models/` are
  still just empty directories.

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

The user has explicitly chosen to finish PdM before moving to service #2,
in this order: ~~Alembic migration~~ → ~~RLS testing~~ → ~~Dockerfile~~ →
~~Helm chart~~ → ~~hysteresis/scoring algorithm~~ → ~~event consumers~~ →
Domino Job entrypoint/Model Registry binding. All six are done — **only
#27 remains** on the user's explicit checklist. Dockerfile and Helm chart
were built in parallel across two Sonnet subagents (per the user's explicit
interest in parallelizing genuinely independent PdM work) — both
independently re-verified afterward (real `docker build` + container run +
`/healthz`/`/readyz`, and `helm lint`/`helm template`/`helm unittest` rerun
from scratch), not just trusted from the subagents' own reports. Building
`services/pdm/helm` also required building `deploy/helm/_fathom-common`
(the shared label/naming library chart every per-service chart depends on)
and the two namespace-wide default-deny NetworkPolicy charts
(`fathom-sustainment`, `fathom-data`) first, since none of that shared Helm
infrastructure existed yet — done directly rather than delegated, since
it's foundational/shared, not PdM's own deliverable. The scoring/hysteresis
algorithm and the event consumers were both built directly (not delegated)
since each needed careful judgment, not mechanical transcription — see
bugs #9 and #11/#12 above for what that judgment caught.

1. **Domino Job entrypoint + Model Registry binding** (#27) needs the
   user's real Domino project/workspace details — the only remaining item
   on the explicit PdM checklist, and the only one blocked on something
   only the user can provide. Get these regardless of what happens next,
   since every other service will need them too.
2. **Decide: is PdM "done enough" to move to service #2, or push further
   first?** Genuinely out-of-scope-for-this-vertical-slice items remain --
   most of `CONSUMES`' ~19 event types (need the tier 0-3 model scoring
   pipeline + real Registry/Telemetry/Failure-Intel read models), the
   Kafka consumer-loop/client infrastructure itself (shared `py-sync` work,
   not PdM-specific), §3.1's input-normalization curves, §3.3's ceiling
   read models, §8.3's re-score-before-publication orchestration and
   dual-binding shadow scoring. None of these were ever on the user's
   explicit 7-item checklist — worth naming them plainly rather than
   letting "PdM is done" quietly expand to mean "PdM is complete."
3. **Separate from the PdM checklist**: ~206 untriaged `ruff` findings
   remain across the whole `services/`/`packages/` tree (see above). The
   user was asked and explicitly chose to defer this — don't re-raise it
   unless asked, but it's still there.

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
