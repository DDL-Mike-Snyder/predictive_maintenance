"""The single assembly point (plan §Paul task 5). Deliberately minimal:
this demo slice takes no dependency on the shared fathom-* middleware
(problem details, correlation, idempotency, classification) — plain
FastAPI, open CORS, one health route, and the read router.

`app = create_app()` is exposed at module level so
`uvicorn fathom_design_advisory.main:app --port 8002` works directly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fathom_design_advisory.api.reads import router as reads_router
from fathom_design_advisory.config import Settings
from fathom_design_advisory.db import build_engine, build_sessionmaker, create_all

SLUG = "design-advisory"
API_MAJOR = 1


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = build_engine(settings)

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        # No Alembic for this demo — create the schema on startup.
        await create_all(engine)
        yield
        await engine.dispose()

    app = FastAPI(
        title="FATHOM — Design Advisory (Redesign Case Builder demo)",
        version=f"{API_MAJOR}.0",
        openapi_version="3.1.0",
        lifespan=_lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_maker = build_sessionmaker(engine)

    # Open CORS — this is a demo, not a security review (plan §Paul task 5).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(reads_router)
    # NOTE: api/actions.py (Marc) and api/agent.py (Michael) are wired at
    # integration by Amanda via api/__init__.py::build_router — deliberately
    # NOT included here, so this branch never touches those files.
    return app


app = create_app()
