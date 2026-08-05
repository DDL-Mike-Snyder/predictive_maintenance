"""Shared httpx client factory. Document 03 §4, 09-monorepo-and-conventions.md §2.2.

`X-Correlation-Id` propagation "to every log line, event, and downstream
call" is a property of a *configured client* -- a bare `httpx.AsyncClient()`
is a lint failure. Note the constraint this serves: 03 principle 2 forbids
synchronous cross-sub-application calls on compute paths, so in the nine
domain services the only sanctioned outbound HTTP is to `auth`, `audit`,
and `reference-data`.
"""

from __future__ import annotations

import httpx

from .correlation import current_correlation_id


def _attach_correlation_id(request: httpx.Request) -> None:
    correlation_id = current_correlation_id()
    if correlation_id:
        request.headers["X-Correlation-Id"] = correlation_id


def make_client(*, base_url: str, workload_token: str | None = None, timeout: float = 10.0) -> httpx.AsyncClient:
    headers = {}
    if workload_token:
        headers["Authorization"] = f"Bearer {workload_token}"
    return httpx.AsyncClient(
        base_url=base_url,
        headers=headers,
        timeout=timeout,
        event_hooks={"request": [_attach_correlation_id]},
    )
