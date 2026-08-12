"""Wires reads + actions + agent into one router. In the real 5-person plan
this is Amanda's integration file (the one file Paul/Marc/Michael were told
not to create, so their branches never collide) -- originally built ahead
of that step (Marc's own commit, before Michael's api/agent.py landed);
agent_router added at integration once Michael's branch merged in."""

from __future__ import annotations

from fastapi import APIRouter

from fathom_design_advisory.api.actions import router as actions_router
from fathom_design_advisory.api.agent import router as agent_router
from fathom_design_advisory.api.reads import router as reads_router


def build_router() -> APIRouter:
    router = APIRouter()
    router.include_router(reads_router)
    router.include_router(actions_router)
    router.include_router(agent_router)
    return router
