"""Aggregates resource routers; one place lists them all. Document 09 §4.2."""

from __future__ import annotations

from fastapi import APIRouter

from . import session


def build_v1_router() -> APIRouter:
    router = APIRouter()
    router.include_router(session.router, tags=["session"])
    return router
