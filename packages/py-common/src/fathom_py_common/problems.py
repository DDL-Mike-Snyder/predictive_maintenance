"""RFC 9457 problem details. Document 03 §4 (Errors), 09-monorepo-and-conventions.md §5.2.

Installed by one call; no service writes its own handler. Registers four
handlers, all returning `application/problem+json`.

`type` is a URN, not an HTTPS URL [ESTABLISHED HERE, 09 §5.2] -- an
`https://` type invites a runtime dereference, and 01 principle 5 forbids
runtime dependence on public-internet services and external DNS.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_MEDIA_TYPE = "application/problem+json"

_HTTP_STATUS_PROBLEM_TYPE = {
    400: "urn:fathom:problem:common:bad-request",
    401: "urn:fathom:problem:common:unauthenticated",
    403: "urn:fathom:problem:common:forbidden",
    404: "urn:fathom:problem:common:not-found",
    409: "urn:fathom:problem:common:conflict",
    412: "urn:fathom:problem:common:precondition-failed",
    422: "urn:fathom:problem:common:validation-error",
    423: "urn:fathom:problem:common:locked",
    428: "urn:fathom:problem:common:precondition-required",
    429: "urn:fathom:problem:common:rate-limit-exceeded",
}


class ProblemException(Exception):
    """Raise this for any declared, service-specific problem type.

    `type` must be one already declared in the service's own
    `schemas/problems.py` enum and present in the OpenAPI `responses` of
    every operation that can raise it -- a `type` string constructed inline
    is a review rejection (09 §5.2).
    """

    def __init__(
        self,
        *,
        type: str,
        title: str,
        status: int,
        detail: str | None = None,
        instance: str | None = None,
        **extensions: Any,
    ) -> None:
        super().__init__(detail or title)
        self.type = type
        self.title = title
        self.status = status
        self.detail = detail
        self.instance = instance
        self.extensions = extensions


def _problem_response(
    request: Request,
    *,
    type: str,
    title: str,
    status_code: int,
    detail: str | None = None,
    **extensions: Any,
) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    body: dict[str, Any] = {
        "type": type,
        "title": title,
        "status": status_code,
        "instance": f"urn:fathom:request:{correlation_id}" if correlation_id else None,
        "correlation_id": correlation_id,
    }
    if detail is not None:
        body["detail"] = detail
    body.update(extensions)
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type=_MEDIA_TYPE,
        headers={"X-Correlation-Id": correlation_id} if correlation_id else {},
    )


def install_problem_handlers(app: FastAPI, *, slug: str) -> None:
    """Registers the four handlers. No service writes its own."""

    @app.exception_handler(ProblemException)
    async def _handle_problem(request: Request, exc: ProblemException) -> JSONResponse:
        return _problem_response(
            request,
            type=exc.type,
            title=exc.title,
            status_code=exc.status,
            detail=exc.detail,
            **exc.extensions,
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem_response(
            request,
            type="urn:fathom:problem:common:validation-error",
            title="Request validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            errors=[{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()],
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        problem_type = _HTTP_STATUS_PROBLEM_TYPE.get(
            exc.status_code, f"urn:fathom:problem:{slug}:http-{exc.status_code}"
        )
        return _problem_response(
            request,
            type=problem_type,
            title=exc.detail if isinstance(exc.detail, str) else "HTTP error",
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def _handle_uncaught(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("uncaught exception in %s", slug, exc_info=exc)
        return _problem_response(
            request,
            type="urn:fathom:problem:common:internal-error",
            title="Internal error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            # No detail leaked -- correlation ID is the only thing the caller gets.
        )
