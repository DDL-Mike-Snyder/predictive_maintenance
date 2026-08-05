"""`build_router() -> APIRouter(prefix=f"/api/v1/{SLUG}")`. Document 09 §4.2."""

from __future__ import annotations

from fastapi import APIRouter

from fathom_pdm.config import Settings

from .v1 import build_v1_router


def build_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/v1/pdm")
    router.include_router(build_v1_router())
    return router
