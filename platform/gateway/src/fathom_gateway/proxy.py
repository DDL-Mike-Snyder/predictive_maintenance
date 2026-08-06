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

Path/query parameters are still forwarded functionally via Starlette's own
`{param}` template matching and `request.query_params` passthrough (the
handler signature declares neither) -- but each operation's `path`/`query`
`parameters` entries are copied verbatim from the upstream's own openapi.json
into the generated route's `openapi_extra["parameters"]`, so the gateway's
OWN generated schema carries real per-parameter type/required metadata too
-- confirmed load-bearing, not cosmetic: `apps/web`'s `openapi-typescript`
codegen against this document is a real consumer (found the first time this
gap was hit, generating a typed client against a route with no declared path
parameter -- see `apps/web/src/features/pdm/PredictionLookup.tsx`'s own
history). `header` parameters (`Idempotency-Key`, `X-Fathom-Principal`) are
deliberately excluded from this copy -- both are handled generically by the
handler's own header-forwarding logic below, and `X-Fathom-Principal`
specifically is a header the GATEWAY substitutes, never one a caller
supplies, so declaring it as a caller-facing parameter would be actively
misleading.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends, FastAPI, Request, Response

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


def _install_upstream_components(app: FastAPI, spec: dict[str, Any]) -> None:
    """Some upstream `parameters`/`schemas` reference sibling component
    definitions via `$ref` (e.g. PdM's `expected-consequence` operation's
    `risk_posture` query param: `{"$ref": "#/components/schemas
    /RiskPosture"}`) -- copying `parameters` alone (as `build_passthrough
    _router` does, above) produces a dangling ref in the GATEWAY's own
    document, since that component only exists in the upstream's. Found
    only by actually running a real OpenAPI consumer (`openapi-typescript`,
    from `apps/web`) against the gateway's generated document -- it failed
    to resolve the ref; FastAPI itself never validates this at startup.
    Fixed by merging the upstream's own `components.schemas` into the
    gateway's, wrapping `app.openapi()` so the merge applies to the SAME
    cached schema dict every service's own `main.py` calls at `--emit-
    openapi` time and `assert_operation_annotations` inspects.
    `setdefault` deliberately never overwrites an existing gateway-native
    component of the same name (there are no known collisions today, but a
    silent overwrite would be a worse failure mode than a merge no-op)."""
    original_openapi = app.openapi

    def _patched_openapi() -> dict[str, Any]:
        schema = original_openapi()
        upstream_schemas = spec.get("components", {}).get("schemas", {})
        target = schema.setdefault("components", {}).setdefault("schemas", {})
        for name, definition in upstream_schemas.items():
            target.setdefault(name, definition)
        return schema

    app.openapi = _patched_openapi  # type: ignore[method-assign]


def build_passthrough_router(
    *, app: FastAPI, upstream: PdmUpstreamSettings, http_client: httpx.AsyncClient
) -> APIRouter:
    router = APIRouter()
    spec = _load_openapi(upstream.openapi_path)
    _install_upstream_components(app, spec)

    for path, path_item in spec.get("paths", {}).items():
        for method in _METHODS:
            operation = path_item.get(method)
            if operation is None:
                continue
            extra = {k: v for k, v in operation.items() if k.startswith("x-")}
            path_and_query_params = [
                param
                for param in operation.get("parameters", [])
                if param.get("in") in ("path", "query")
            ]
            if path_and_query_params:
                extra["parameters"] = path_and_query_params
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
