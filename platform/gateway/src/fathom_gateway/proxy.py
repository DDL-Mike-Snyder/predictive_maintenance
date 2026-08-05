"""DECISION G-3 (30-gateway.md §8.2): pass-through routes are GENERATED AT
STARTUP from a committed `openapi.json`, never a catch-all proxy. §8.2's
own four reasons: (1) a catch-all can't declare `x-substitution`/
`x-side-effects`/`x-agent-eligible` per operation, so agent tooling and
the idempotency gate would have nothing to inspect; (2) it would forward
routes the upstream service never declared, silently widening the attack
surface every time the upstream adds an internal-only endpoint; (3) path
parameters and methods the upstream doesn't have would 404 from the
upstream instead of failing at the gateway's own routing layer; (4) the
generated routes show up in the gateway's OWN `app.openapi()` output,
which is what `assert_operation_annotations` (installed in every service's
`main.py`) validates against.

This builds one real FastAPI route per (path, method) declared in the
upstream's own OpenAPI document, copying every `x-*` extension key
verbatim onto the generated route's `openapi_extra` -- so
`idempotency_guard` (already installed globally by `main.py`) enforces
the exact same Idempotency-Key contract at the gateway boundary that the
upstream service itself declared for that operation, not a laxer or
stricter one invented here.

[SCOPE, this vertical slice] Path/query parameters are forwarded via
Starlette's own `{param}` template matching and `request.query_params`
passthrough -- they are NOT individually declared as FastAPI `Parameter`
objects, so the gateway's own generated OpenAPI schema for these routes
lacks per-parameter type/required metadata (functionally irrelevant here
since `docs_url`/`redoc_url` are both disabled, per every service's own
`main.py`). Worth building properly if the gateway's own OpenAPI document
ever needs to be consumed by a codegen step, the same way PdM's is.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Request, Response

from fathom_gateway.config import PdmUpstreamSettings
from fathom_gateway.deps import current_gateway_session
from fathom_gateway.models import GatewaySessionRow
from fathom_gateway.oidc import principal_id_from_access_token

_METHODS = ("get", "post", "put", "patch", "delete")

# Never forwarded in either direction: hop-by-hop (RFC 9110 §7.6.1) plus
# `host`/`content-length` (recomputed by httpx for the new destination) and
# `authorization`/`cookie` (the caller's own cookie is never forwarded --
# the whole point of the BFF pattern, 30-gateway.md §8.1.2 -- and PdM, the
# only real upstream in this vertical slice, never checks an
# `Authorization` header at all; see `oidc.py::principal_id_from_access_token`'s
# own docstring for what IS forwarded instead: `X-Fathom-Principal`, matching
# `fathom_py_common.authz.current_principal`'s own placeholder contract).
_STRIPPED_REQUEST_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "authorization",
    "cookie",
    "x-fathom-principal",
}
_STRIPPED_RESPONSE_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
}


def _load_openapi(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def _make_handler(
    *, base_url: str, upstream_path: str, method: str, http_client: httpx.AsyncClient
) -> Callable[..., Awaitable[Response]]:
    async def _handler(
        request: Request,
        session: GatewaySessionRow = Depends(current_gateway_session),
    ) -> Response:
        real_path = upstream_path
        for key, value in request.path_params.items():
            real_path = real_path.replace(f"{{{key}}}", str(value))

        forward_headers = {
            k: v for k, v in request.headers.items() if k.lower() not in _STRIPPED_REQUEST_HEADERS
        }
        forward_headers["x-fathom-principal"] = principal_id_from_access_token(session.access_token)

        upstream_response = await http_client.request(
            method.upper(),
            f"{base_url}{real_path}",
            params=request.query_params.multi_items(),
            content=await request.body(),
            headers=forward_headers,
        )
        response_headers = {
            k: v
            for k, v in upstream_response.headers.items()
            if k.lower() not in _STRIPPED_RESPONSE_HEADERS
        }
        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers=response_headers,
        )

    return _handler


def build_passthrough_router(
    *, upstream: PdmUpstreamSettings, http_client: httpx.AsyncClient
) -> APIRouter:
    router = APIRouter()
    spec = _load_openapi(upstream.openapi_path)

    for path, path_item in spec.get("paths", {}).items():
        for method in _METHODS:
            operation = path_item.get(method)
            if operation is None:
                continue
            extra = {k: v for k, v in operation.items() if k.startswith("x-")}
            router.add_api_route(
                path,
                _make_handler(
                    base_url=upstream.base_url,
                    upstream_path=path,
                    method=method,
                    http_client=http_client,
                ),
                methods=[method.upper()],
                operation_id=operation.get("operationId"),
                summary=operation.get("summary"),
                openapi_extra=extra,
            )
    return router
