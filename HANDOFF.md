# FATHOM — handoff / continuation notes

**Read this first if you're picking this up cold.** Last updated 2026-08-05,
end of a long session that (a) closed out the spec-hardening phase and
(b) started real implementation. Everything below is committed on `main`
unless stated otherwise. `git log --oneline` tells the true story in detail;
this file is the map.

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
| `services/pdm` | DB models for `prediction` (RLS-bearing), `criticality_assessment`, `calibration_record` (compartment-partitioned), `scoring_run`, `tier_policy`, `prediction_provenance`; a working bulk-ingest endpoint (idempotent, transactional, baseline-fenced, outbox-emitting); get-prediction, get-criticality, expected-consequence reads | 4 passing, incl. one real HTTP→DB integration test |

**Total: 26 passing tests**, all newly written this session, all genuinely
exercised (not just "written and assumed to work" — see the gotchas below,
several were only caught by actually running them).

## What's NOT built yet for PdM

- **Alembic migration files.** Models exist; no `alembic revision` /
  `upgrade()`/`downgrade()` has been written. `services/pdm/src/fathom_pdm/migrations/`
  has empty `env.py`/`versions/` directories only.
- **Dockerfile.** Not written at all yet for `services/pdm`.
- **Helm chart.** `services/pdm/helm/` directories exist (empty) — no
  `values.yaml`, no templates.
- **The actual criticality-scoring / hysteresis algorithm.** We modeled the
  *data* (the `criticality_assessment` table, `tier_is_capped`,
  `migration_requires_rescore` constraints) but not the *computation* —
  22-pdm.md §3.3/§3.4's `raw_band`/`proposed_tier` hysteresis logic, the
  five-input scoring formula, none of that is implemented as code yet.
- **RLS enforcement testing.** The `CREATE POLICY` statements are
  documented in 22-pdm.md §4.5 but have not been transcribed into the
  Alembic migration, and — more importantly — **SQLite cannot test row-level
  security at all**. This needs a real PostgreSQL instance (testcontainers,
  per `09-monorepo-and-conventions.md` §2.2) to actually verify. This is
  arguably the single highest-priority remaining item, since RLS is PdM's
  most security-critical mechanism.
- **The Domino Job entrypoint script** and the Domino Model Registry
  binding logic (22-pdm.md §5.6) — nothing Domino-specific has been
  exercised against a live workspace at all. The `.env.example` has
  placeholder `FATHOM_DOMINO__*` vars with no real values.
- **Event consumers.** Only the *publisher* side (`prediction.updated`) is
  wired. None of PdM's ~15 consumed event types (`configuration.baseline_changed`,
  `maintenance_action.recorded`, etc.) have a handler.
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
   each their own metadata, separate from a service's own `Base`. Any
   migration or test schema setup needs `create_all()` (or the real Alembic
   equivalent) against **all three** metadatas, not just the service's own
   models. This is currently handled ad hoc in test fixtures; the *real*
   Alembic migration (not yet written) needs to do the same thing properly.

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
  "prometheus-client>=0.21" "httpx>=0.27" "uvicorn[standard]>=0.32" "asyncpg>=0.30" "alembic>=1.14"

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

## Recommended next steps, roughly in priority order

1. **Decide: finish PdM to full completion, or move to service #2 now?**
   The user hadn't decided this before signing off — worth asking first
   thing. Arguments for finishing PdM: Alembic/Docker/Helm/RLS-testing are
   exactly the pieces most likely to surface *more* Domino-specific issues,
   which was the whole point of picking one service first. Arguments for
   moving on: the shared-infrastructure pattern (packages/*) is now
   validated and is the part that was genuinely uncertain; Docker/Helm/Alembic
   are comparatively mechanical and low-risk to defer.
2. **If finishing PdM:** Alembic migration first (needed for literally
   everything else — Docker's migration hook, Helm's migration Job, RLS
   testing all depend on a real migration existing), then RLS testing
   against a real Postgres (testcontainers), then Dockerfile, then Helm
   chart, then the actual hysteresis/scoring algorithm, then event
   consumers, then the Domino-specific pieces (which need the user's actual
   Domino project/workspace details — was mid-outage when this session
   started, should be back up by now).
3. **Either way:** get the user's Domino project/workspace details, since
   several remaining PdM pieces (Domino Job entrypoint, Model Registry
   binding) are blocked on it, and it's needed for every other service too.

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
