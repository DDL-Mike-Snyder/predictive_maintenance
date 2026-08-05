"""The single assembly point. Document 09 §4.6. Differs from every other
service's `main.py` only in the routers registered and the readiness
checks added -- must not contain re-implementations of anything in
`packages/py-common`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fathom_py_common import (
    assert_operation_annotations,
    configure_logging,
    fathom_operation_id,
    install_classification_middleware,
    install_correlation_middleware,
    install_health_routes,
    install_idempotency_middleware,
    install_problem_handlers,
)
from fathom_sync.outbox import OutboxWriter
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from fathom_pdm.api import build_router
from fathom_pdm.config import Settings
from fathom_pdm.observability.readiness import register_checks
from fathom_pdm.signer import EnvelopeSigner

SLUG = "pdm"  # canonical slug, 03 §3.1
API_MAJOR = 1


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]
    configure_logging(settings.app.log_level, service=SLUG)

    # 22-pdm.md: "PdM has no edge profile. Every event it publishes carries
    # `producer_node = 'enterprise'`... asserted at startup, not assumed: a
    # PdM instance that finds an edge profile configured refuses to start."
    # [PLACEHOLDER] There is no FATHOM_EDGE__* settings section defined
    # anywhere in this vertical slice's Settings model, so this check is
    # currently vacuous -- it exists as the documented guard, ready for the
    # day an edge-profile config surface is added to this service by mistake.

    app = FastAPI(
        title="FATHOM -- Predictive Maintenance",
        version=f"{API_MAJOR}.0",
        openapi_version="3.1.0",
        generate_unique_id_function=fathom_operation_id(SLUG),
        docs_url=None,
        redoc_url=None,  # no interactive docs in cluster
    )

    # `pool_size`/`max_overflow` are QueuePool options (asyncpg/Postgres, the
    # production target per 09 §2.1). SQLite's async driver uses a StaticPool
    # by default and rejects them; SQLite also has no notion of the `pdm`
    # schema every model is declared under, so `schema_translate_map` remaps
    # it away for that dialect only. `poolclass=StaticPool` is additionally
    # required for an in-memory SQLite URL specifically: each new physical
    # connection to `sqlite+aiosqlite://` (no file path) is otherwise its
    # OWN separate, empty database -- a schema seeded through one checked-out
    # connection is invisible to a request handled through another. StaticPool
    # forces every checkout to share the one connection the engine opened.
    # All three branches exist purely so the SAME main.py can be exercised in
    # tests against SQLite; production always takes the Postgres branch,
    # unmodified.
    engine_kwargs: dict[str, object] = {}
    if settings.database.url.startswith("sqlite"):
        engine_kwargs["execution_options"] = {"schema_translate_map": {"pdm": None}}
        engine_kwargs["poolclass"] = StaticPool
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["pool_size"] = settings.database.pool_size
        engine_kwargs["max_overflow"] = settings.database.max_overflow
    engine = create_async_engine(settings.database.url, **engine_kwargs)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    app.state.engine = engine
    app.state.outbox_writer = OutboxWriter(
        producer_slug=SLUG,
        producer_version=f"{API_MAJOR}.0",
        producer_node_id="enterprise",  # ALWAYS -- no edge profile, per above
        signer=EnvelopeSigner(),
    )

    # Middleware order is fixed and load-bearing. §5.7.
    install_correlation_middleware(app)  # 1. X-Correlation-Id in/out, bound to contextvars
    install_problem_handlers(app, slug=SLUG)  # 2. RFC 9457 for every raised error
    install_classification_middleware(app)  # 3. X-Classification on responses
    install_idempotency_middleware(app)  # 4. reads x-side-effects off the matched route

    @app.middleware("http")
    async def _attach_db_session(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # services/ owns the transaction boundary (09 §4.1) -- this
        # middleware only makes ONE session available per request; whether
        # (and where) a transaction opens is a services/ decision, not this
        # middleware's.
        async with session_maker() as session:
            request.state.db_session = session
            response = await call_next(request)
            await session.commit()
            return response

    app.include_router(build_router(settings))
    install_health_routes(app, checks=register_checks(settings, engine))

    assert_operation_annotations(app)  # 5. fail fast, in-process, not only in CI
    return app


app = create_app()

if __name__ == "__main__":
    # 09-monorepo-and-conventions.md: `make contract` runs
    # `python -m fathom_pdm.main --emit-openapi > openapi.json` and diffs
    # against the committed copy. `create_app()` (module level, above) has
    # already run by the time this executes, so this just prints its result.
    import json
    import sys

    if "--emit-openapi" in sys.argv:
        print(json.dumps(app.openapi(), indent=2))  # noqa: T201 -- this print IS `make contract`'s output
    else:
        print("usage: python -m fathom_pdm.main --emit-openapi", file=sys.stderr)  # noqa: T201
        sys.exit(1)
