"""`X-Classification` middleware. Document 03 §4, §7.3.

Per-field redaction where a response mixes levels is a
`packages/canonical-schemas` serializer concern (the handler chooses what to
put on the wire), not a middleware one -- this middleware only sets the
response header from whatever classification the handler recorded.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class ClassificationMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        level = getattr(request.state, "response_classification_level", None)
        if level is not None:
            response.headers["X-Classification"] = level
        return response


def set_response_classification(request: Request, level: str) -> None:
    """Called by a handler (or a repository-level helper) once it knows the
    classification of what it's about to return."""
    request.state.response_classification_level = level


def install_classification_middleware(app: FastAPI) -> None:
    app.add_middleware(ClassificationMiddleware)
