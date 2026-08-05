"""FATHOM shared FastAPI middleware, problem details, idempotency, ETag,
health, logging (09-monorepo-and-conventions.md §5).

[NOTE] `10-shared-packages.md` explicitly disclaims owning this package's
content ("this document's own §1 scope covers canonical-schemas, contracts,
and agent-tooling... the broader py-common gap is recorded in document 05
rather than silently implied closed"). This is a genuine corpus gap, not an
oversight -- this package is authored from 09-monorepo-and-conventions.md
§5's prose contract, the same way any other [ESTABLISHED HERE] decision in
this corpus is made once, here, rather than nine times locally.
"""

from .authz import Principal, current_principal, require_clearance
from .classification import install_classification_middleware, set_response_classification
from .concurrency import VersionConflict, etag_for, require_if_match
from .correlation import current_correlation_id, install_correlation_middleware
from .health import ReadinessCheck, install_health_routes, make_check
from .httpclient import make_client
from .idempotency import (
    IdempotencyKeyRow,
    IdempotentReplay,
    idempotency_guard,
    install_idempotency_middleware,
    persist_idempotent_response,
)
from .logging import configure_logging
from .openapi import assert_operation_annotations, fathom_operation_id
from .pagination import ChangedSinceParams, CursorParams, Page, decode_cursor, encode_cursor
from .problems import ProblemException, install_problem_handlers

__all__ = [
    "ChangedSinceParams",
    "CursorParams",
    "IdempotencyKeyRow",
    "IdempotentReplay",
    "Page",
    "Principal",
    "ProblemException",
    "ReadinessCheck",
    "VersionConflict",
    "assert_operation_annotations",
    "configure_logging",
    "current_correlation_id",
    "current_principal",
    "decode_cursor",
    "encode_cursor",
    "etag_for",
    "fathom_operation_id",
    "idempotency_guard",
    "install_classification_middleware",
    "install_correlation_middleware",
    "install_health_routes",
    "install_idempotency_middleware",
    "install_problem_handlers",
    "make_check",
    "make_client",
    "persist_idempotent_response",
    "require_clearance",
    "require_if_match",
    "set_response_classification",
]
