"""Aggregates resource routers; one place lists them all. Document 09 §4.2."""

from __future__ import annotations

from fastapi import APIRouter

from . import criticality, decisions, predictions


def build_v1_router() -> APIRouter:
    router = APIRouter()
    router.include_router(predictions.router, tags=["predictions"])
    router.include_router(criticality.router, tags=["criticality"])
    router.include_router(decisions.router, tags=["decisions"])
    return router
