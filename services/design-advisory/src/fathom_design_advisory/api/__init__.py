"""Wires reads + actions into one router. In the real 5-person plan this
is Amanda's integration file (the one file Paul/Marc/Michael were told not
to create, so their branches never collide) -- built here directly since
this pass builds Paul's skeleton + Marc's actions only, no agent.py yet."""

from __future__ import annotations

from fastapi import APIRouter

from fathom_design_advisory.api.actions import router as actions_router
from fathom_design_advisory.api.reads import router as reads_router


def build_router() -> APIRouter:
    router = APIRouter()
    router.include_router(reads_router)
    router.include_router(actions_router)
    return router
