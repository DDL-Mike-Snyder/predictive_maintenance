"""Assembly point for the Redesign Case Builder demo service.
docs/demo/redesign-case-builder-demo-plan.md, Paul's task 5 -- plain
FastAPI, no `fathom-py-common` middleware stack (this demo's own §0.1
scope cut). CORS is wide open (`allow_origins=["*"]`) -- this is a demo,
not a security review."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fathom_design_advisory.api import build_router
from fathom_design_advisory.config import Settings
from fathom_design_advisory.db import create_all, make_engine, make_session_maker


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        await create_all(app.state.engine)
        yield

    app = FastAPI(
        title="FATHOM -- Design Advisory (Redesign Case Builder demo)",
        version="0.1",
        lifespan=_lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    engine = make_engine(settings.database_url)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_maker = make_session_maker(engine)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(build_router())

    return app


app = create_app()

if __name__ == "__main__":
    import json
    import sys

    if "--emit-openapi" in sys.argv:
        print(json.dumps(app.openapi(), indent=2))  # noqa: T201
    else:
        print("usage: python -m fathom_design_advisory.main --emit-openapi", file=sys.stderr)  # noqa: T201
        sys.exit(1)
