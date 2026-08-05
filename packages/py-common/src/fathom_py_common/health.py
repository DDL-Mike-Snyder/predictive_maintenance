"""`/healthz`, `/readyz`, `/metrics`. Document 03 §4, §5.2, obligation 14.
Identical in all seventeen services.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


class ReadinessCheck(Protocol):
    name: str

    async def __call__(self) -> tuple[bool, str | None]: ...
    """Returns (healthy, detail)."""


def install_health_routes(app: FastAPI, *, checks: list[ReadinessCheck]) -> None:
    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        """Liveness. Process-local only -- NEVER consults a dependency; a
        database blip must not trigger a restart storm."""
        return {"status": "ok"}

    @app.get("/readyz", include_in_schema=False)
    async def readyz(response: Response) -> dict[str, object]:
        """Readiness. Aggregates registered `ReadinessCheck` callables."""
        results: dict[str, object] = {}
        all_healthy = True
        for check in checks:
            healthy, detail = await check()
            results[check.name] = {"healthy": healthy, "detail": detail}
            all_healthy = all_healthy and healthy
        if not all_healthy:
            response.status_code = 503
        return {"status": "ready" if all_healthy else "degraded", "checks": results}

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def make_check(name: str, fn: Callable[[], Awaitable[tuple[bool, str | None]]]) -> ReadinessCheck:
    class _Check:
        def __init__(self) -> None:
            self.name = name

        async def __call__(self) -> tuple[bool, str | None]:
            return await fn()

    return _Check()  # type: ignore[return-value]
