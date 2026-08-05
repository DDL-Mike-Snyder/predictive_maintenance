"""Structured JSON logging. Document 03 §4, §15 obligation 15.

JSON to stdout only. `correlation_id` on every line, bound via the
correlation middleware's contextvar. `duration_ms` is measured with
`time.monotonic()`, never a wall clock (03 §5.4, D29) -- that discipline is
the caller's, this module only fixes the processor chain and redaction.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from .correlation import current_correlation_id

_NEVER_LOG_KEYS = {
    "authorization",
    "bearer_token",
    "idempotency_key",
    "request_body",
}


def _redact(_logger: object, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key in list(event_dict):
        if key.lower() in _NEVER_LOG_KEYS:
            event_dict[key] = "[redacted]"
    return event_dict


def _bind_correlation_id(
    _logger: object, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    event_dict.setdefault("correlation_id", current_correlation_id())
    return event_dict


def configure_logging(log_level: str, *, service: str) -> None:
    logging.basicConfig(stream=sys.stdout, level=log_level, format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _bind_correlation_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            _redact,
            structlog.processors.EventRenamer("event"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level.upper())),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    structlog.contextvars.bind_contextvars(service=service)
