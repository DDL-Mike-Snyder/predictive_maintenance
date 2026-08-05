"""`generate_unique_id_function`. Document 09 §7.3: `operationId` is
`<slug_underscored>_<verb>_<resource>`, set explicitly rather than left to
FastAPI's default -- operation IDs must be unique in the gateway-merged
document and are the join key manifests select on.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.routing import APIRoute


def assert_operation_annotations(app: FastAPI) -> None:
    """Fails startup, in-process, if any non-health operation lacks
    `x-substitution`/`x-side-effects`. Document 09 §5.1: three layers of
    enforcement, deliberately redundant -- this is layer 2 (layer 1 is
    `operation()` raising at import time; layer 3 is CI's `tools/check_openapi.py`
    re-validating the committed spec).

    [AMENDMENT -- real bug, found while building services/pdm.] This
    originally walked `app.routes` directly with `isinstance(route,
    APIRoute)`. Some FastAPI versions resolve an `include_router()` call
    lazily -- `app.routes` holds an internal wrapper object, not expanded
    `APIRoute` instances, until something forces resolution (schema
    generation, or an actual request). The isinstance check then silently
    matched nothing and this function always "passed" without checking a
    single operation. Building on the generated OpenAPI schema instead of
    walking Route objects sidesteps that FastAPI-internals fragility
    entirely, and is arguably the more correct source of truth anyway: the
    committed `openapi.json` is what CI's own `tools/check_openapi.py`
    re-validates, so this in-process check should read the same artifact.
    """
    exempt_paths = {"/healthz", "/readyz", "/metrics"}
    schema = app.openapi()
    for path, path_item in schema.get("paths", {}).items():
        if path in exempt_paths:
            continue
        for method, operation in path_item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            if "x-substitution" not in operation or "x-side-effects" not in operation:
                raise RuntimeError(
                    f"operation {method.upper()} {path!r} is missing x-substitution "
                    "or x-side-effects -- every operation must declare both (03 §4.1)"
                )


def fathom_operation_id(slug: str) -> Callable[[APIRoute], str]:
    slug_underscored = slug.replace("-", "_")

    def _generate(route: APIRoute) -> str:
        # If the route already set an explicit operation_id (the normal
        # case -- every route declares one via `@operation`/`operation_extra`),
        # FastAPI uses it directly; this function is the fallback FastAPI
        # calls to derive one, so it still needs to produce the same shape.
        name = route.name.replace("-", "_")
        return f"{slug_underscored}_{name}"

    return _generate
