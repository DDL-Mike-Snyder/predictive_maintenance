"""Mounts Michael's real `api/agent.py` router into a throwaway FastAPI
app for `test_agent_e2e.py` to run against over a real socket.

This stands in for the real `main.py`/`api/__init__.py` wiring Paul and
Amanda own (`main.py` isn't Michael's file, and `api/__init__.py` is
explicitly Amanda's to create at integration -- see both module
docstrings). Test-only; not one of Michael's owned files.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fastapi import FastAPI
from fathom_design_advisory.api.agent import router

app = FastAPI(title="agent-app-for-test (Michael's own harness, not the real main.py)")
app.include_router(router)


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}
