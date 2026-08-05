"""`X-Correlation-Id` middleware. Document 03 §4, §5.4, §15 obligation 15.

Must be the OUTERMOST middleware (09 §5.7 rule 1) so every subsequent
layer, including the catch-all error handler, has a correlation ID.
Bound into a `contextvars` context so it survives `await` boundaries
without threading the ID through every function signature.
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "fathom_correlation_id", default=None
)


def current_correlation_id() -> str | None:
    return correlation_id_var.get()


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-Id") or str(uuid.uuid4())
        token = correlation_id_var.set(correlation_id)
        request.state.correlation_id = correlation_id
        try:
            response = await call_next(request)
        finally:
            correlation_id_var.reset(token)
        response.headers["X-Correlation-Id"] = correlation_id
        return response


def install_correlation_middleware(app: FastAPI) -> None:
    app.add_middleware(CorrelationMiddleware)
