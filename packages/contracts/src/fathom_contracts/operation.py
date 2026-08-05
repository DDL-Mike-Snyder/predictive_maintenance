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
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

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
) -> Callable[[F], F]:
    """Declare an operation's contract annotations. Document 03 §4.1, §8.1.

    `agent_eligible=True` with `side_effects=STATE_CHANGING` raises at import.
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
    return extra
