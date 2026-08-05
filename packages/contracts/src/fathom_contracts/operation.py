"""The operation annotation decorator. Document 03 §4.1 and §8.1.

Every operation on every sub-application and platform service is declared
through this decorator. It does three things a raw `openapi_extra=` dict
does not:

1. Enforces the §8.1 gate AT IMPORT TIME, so a state-changing operation
   marked agent-eligible fails the service's own unit tests rather than
   waiting for CI spec validation.
2. Registers the operation in a process-local registry, so a layout
   validator can assert COMPLETENESS -- that no operation was declared
   without the decorator.
3. Records the source location, so a validation failure names the file and
   line rather than only the path and method.

`Substitution`/`SideEffects` are pure enums, defined once in
`fathom_schemas.annotations` (no web-framework dependency); this module
imports them rather than redefining them.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from fathom_schemas import SideEffects, Substitution

__all__ = [
    "REGISTRY",
    "OperationDeclaration",
    "SideEffects",
    "Substitution",
    "operation",
    "operation_extra",
]


@dataclass(frozen=True)
class OperationDeclaration:
    operation_id: str
    substitution: Substitution
    side_effects: SideEffects
    agent_eligible: bool
    summary: str
    source: str  # "file.py:lineno", for error messages
    aggregate: str | None = None  # for the §4 changed_since completeness check
    singleton_carveout: str | None = None  # §4 naming carve-out justification
    idempotency_required: bool = False  # see `operation()`'s own docstring


REGISTRY: dict[str, OperationDeclaration] = {}
F = TypeVar("F", bound=Callable[..., Any])


def operation(
    *,
    operation_id: str,
    substitution: Substitution,
    side_effects: SideEffects,
    summary: str,
    agent_eligible: bool = False,
    aggregate: str | None = None,
    singleton_carveout: str | None = None,
    idempotency_required: bool = False,
) -> Callable[[F], F]:
    """Declare an operation's contract annotations. Document 03 §4.1, §8.1.

    `agent_eligible=True` with `side_effects=STATE_CHANGING` raises at import.

    `idempotency_required` is the escape hatch for 09 §8.1's own general
    rule ("required on every `state-changing` and `proposal-only`
    operation") -- `packages/py-common`'s `idempotency_guard` enforces that
    rule automatically from `x-side-effects` alone, so this flag only needs
    setting on the rare `side_effects=none` operation whose own spec calls
    for an Idempotency-Key anyway (22-pdm.md §10's `POST /scoring-runs`:
    `none` because it computes and does not alter *domain* state, but it
    still mints a real row, so blind retries are not safe). Do not set this
    on a normal `none` operation -- that would silently make retries of an
    ordinary read-only-ish endpoint require a header no caller expects.
    """
    if agent_eligible and not side_effects.agent_eligible_permitted:
        raise ValueError(
            f"operation {operation_id!r}: `x-agent-eligible` may be asserted only "
            f"where `x-side-effects` is `none` or `proposal-only`; got "
            f"{side_effects.value!r}. Document 03 §8.1 and §15 obligation 8."
        )
    if operation_id in REGISTRY:
        raise ValueError(
            f"duplicate operationId {operation_id!r} (first declared at "
            f"{REGISTRY[operation_id].source})"
        )

    frame = inspect.stack()[1]
    declaration = OperationDeclaration(
        operation_id=operation_id,
        substitution=substitution,
        side_effects=side_effects,
        agent_eligible=agent_eligible,
        summary=summary,
        source=f"{frame.filename}:{frame.lineno}",
        aggregate=aggregate,
        singleton_carveout=singleton_carveout,
        idempotency_required=idempotency_required,
    )
    REGISTRY[operation_id] = declaration

    def decorate(func: F) -> F:
        func.__fathom_operation__ = declaration  # type: ignore[attr-defined]
        return func

    return decorate


def operation_extra(**kwargs: Any) -> dict[str, Any]:
    """The `openapi_extra=` payload. Registers, gates, and returns the
    extension keys in one call, so the two cannot drift apart."""
    operation(**kwargs)
    declaration = REGISTRY[kwargs["operation_id"]]
    extra: dict[str, Any] = {
        "x-substitution": declaration.substitution.value,
        "x-side-effects": declaration.side_effects.value,
    }
    if declaration.agent_eligible:
        extra["x-agent-eligible"] = True
    if declaration.aggregate:
        extra["x-fathom-aggregate"] = declaration.aggregate
    if declaration.singleton_carveout:
        extra["x-fathom-singleton-carveout"] = declaration.singleton_carveout
    if declaration.idempotency_required:
        extra["x-fathom-idempotency-required"] = True
    return extra
