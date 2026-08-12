"""The single assembly point. Document 09 §4.6. Differs from
`services/pdm`'s own `main.py` in owning no outbox/broker (this service
publishes no domain events and consumes none -- see `observability
/readiness.py`'s docstring) and in constructing an `OidcClient` + `httpx
.AsyncClient` instead of an `EnvelopeSigner`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from fathom_gateway.api import build_router
from fathom_gateway.config import Settings
from fathom_gateway.observability.readiness import register_checks
from fathom_gateway.oidc import OidcClient
from fathom_gateway.proxy import build_passthrough_router

SLUG = "gateway"  # canonical slug, 03 §3.1
API_MAJOR = 1


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]
    configure_logging(settings.app.log_level, service=SLUG)

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        await app.state.http_client.aclose()

    app = FastAPI(
        title="FATHOM -- Gateway",
        version=f"{API_MAJOR}.0",
        openapi_version="3.1.0",
        generate_unique_id_function=fathom_operation_id(SLUG),
        docs_url=None,
        redoc_url=None,  # no interactive docs in cluster
        lifespan=_lifespan,
    )

    # Same three-branch SQLite-vs-Postgres shape as services/pdm/main.py --
    # see that module's own comment for the full rationale; this service's
    # own models (`GatewaySessionRow`) carry no schema qualification, so
    # there is no `schema_translate_map` branch needed here.
    engine_kwargs: dict[str, object] = {}
    if settings.database.url.startswith("sqlite"):
        engine_kwargs["poolclass"] = StaticPool
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["pool_size"] = settings.database.pool_size
        engine_kwargs["max_overflow"] = settings.database.max_overflow
    engine = create_async_engine(settings.database.url, **engine_kwargs)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    app.state.engine = engine
    app.state.settings = settings
    app.state.http_client = httpx.AsyncClient()
    app.state.oidc_client = OidcClient(
        issuer=settings.oidc.issuer,
        client_id=settings.oidc.client_id,
        client_secret=settings.oidc.client_secret,
        redirect_uri=settings.oidc.redirect_uri,
        http_client=app.state.http_client,
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
        async with session_maker() as session:
            request.state.db_session = session
            response = await call_next(request)
            await session.commit()
            return response

    app.include_router(build_router(settings))
    # DECISION G-3 (30-gateway.md §8.2): generated from PdM's own committed
    # openapi.json, not a catch-all -- see proxy.py's own module docstring.
    app.include_router(
        build_passthrough_router(app=app, upstream=settings.pdm, http_client=app.state.http_client)
    )
    install_health_routes(app, checks=register_checks(engine))

    assert_operation_annotations(app)  # 5. fail fast, in-process, not only in CI

    # [ADDITIVE, opt-in -- see config.py's own AppSettings.static_dir
    # docstring] Registered LAST, deliberately: Starlette tries routes in
    # registration order, so every API route/health route above still
    # wins on an exact match; this only catches what nothing else claimed.
    # Mounting apps/web's build here (rather than a separate reverse
    # proxy in front of it) makes gateway + UI one same-origin Domino App
    # -- no CORS, no cross-origin cookie story to solve.
    if settings.app.static_dir:
        static_dir = Path(settings.app.static_dir)
        index_html = static_dir / "index.html"
        assets_dir = static_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="web-assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def _serve_web_spa(full_path: str) -> Response:  # noqa: ARG001 -- SPA fallback, path unused
            return FileResponse(index_html)

    return app


app = create_app()

if __name__ == "__main__":
    # 09-monorepo-and-conventions.md: `make contract` runs
    # `python -m fathom_gateway.main --emit-openapi > openapi.json` and diffs
    # against the committed copy.
    import json
    import sys

    if "--emit-openapi" in sys.argv:
        print(json.dumps(app.openapi(), indent=2))  # noqa: T201 -- this print IS `make contract`'s output
    else:
        print("usage: python -m fathom_gateway.main --emit-openapi", file=sys.stderr)  # noqa: T201
        sys.exit(1)
