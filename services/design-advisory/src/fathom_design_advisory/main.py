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

    _install_operation_annotations(app)

    return app


def _install_operation_annotations(app: FastAPI) -> None:
    """B-4 integration fix. Every operation in the gateway-merged OpenAPI
    document must declare `x-substitution`/`x-side-effects` (03 §4.1); the
    gateway's pass-through generator copies these verbatim and its startup
    guard (`assert_operation_annotations`) refuses to boot without them.

    The real services use `fathom_contracts.operation_extra` per route, but
    this standalone demo service deliberately has no dependency on that
    package. Instead we inject the two keys by HTTP method, which is exact
    for this service: every `GET` here is a pure read (`side-effects: none`)
    and every `POST` persists a row (`side-effects: state-changing`). All
    operations are `substitution: required` (a substituting implementation
    must provide them). Wraps `app.openapi()` so the injection lands in the
    same cached schema `--emit-openapi` prints and the gateway proxies."""
    exempt = {"/healthz", "/readyz", "/metrics"}
    base_openapi = app.openapi

    def _openapi() -> dict:
        schema = base_openapi()
        for path, path_item in schema.get("paths", {}).items():
            if path in exempt:
                continue
            for method, operation in path_item.items():
                if method not in ("get", "post", "put", "patch", "delete"):
                    continue
                operation.setdefault("x-substitution", "required")
                operation.setdefault(
                    "x-side-effects",
                    "none" if method == "get" else "state-changing",
                )
        return schema

    app.openapi = _openapi  # type: ignore[method-assign]


app = create_app()

if __name__ == "__main__":
    import json
    import sys

    if "--emit-openapi" in sys.argv:
        print(json.dumps(app.openapi(), indent=2))  # noqa: T201
    else:
        print("usage: python -m fathom_design_advisory.main --emit-openapi", file=sys.stderr)  # noqa: T201
        sys.exit(1)
