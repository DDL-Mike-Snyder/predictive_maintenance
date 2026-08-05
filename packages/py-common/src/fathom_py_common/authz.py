"""Authorization dependency. Document 03 §4, obligation 7: enforced in the
receiving service against ABAC attributes, never delegated to the gateway
alone.

[PLACEHOLDER] The full ABAC/OPA decision-input shape belongs to
`31-auth.md`, which this vertical slice does not yet implement end to end
-- this is a minimal, honestly-scoped principal extractor sufficient for
PdM's own routes, not a claim that OPA integration is complete.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, Request

from .problems import ProblemException


@dataclass(frozen=True)
class Principal:
    principal_id: str
    agent_authority: str | None  # "delegated" | "accountable_autonomous" | None (human)
    clearance_level: str
    compartments: tuple[str, ...]


def current_principal(
    request: Request,
    x_fathom_principal: str | None = Header(default=None, alias="X-Fathom-Principal"),
) -> Principal:
    """[PLACEHOLDER] Stand-in for real OIDC-bearer-token validation +
    JWKS + ABAC-attribute extraction (31-auth.md). Reads a test/dev header
    so the rest of the service (idempotency, ETag, business logic) can be
    built and tested against a real `Principal` shape now, without blocking
    on the full auth integration."""
    if x_fathom_principal is None:
        raise ProblemException(
            type="urn:fathom:problem:common:unauthenticated",
            title="Missing principal",
            status=401,
        )
    principal = Principal(
        principal_id=x_fathom_principal,
        agent_authority=None,
        clearance_level="U",
        compartments=(),
    )
    request.state.principal_id = principal.principal_id
    return principal


def require_clearance(
    principal: Principal, label_level: str, label_compartments: tuple[str, ...]
) -> None:
    """[PLACEHOLDER] A minimal ABAC check a service calls explicitly from
    its own service-layer code (03 §4, obligation 7: enforced in THIS
    service, never the gateway). A full implementation belongs to
    `31-auth.md`'s OPA policy bundle, not this stand-in level-rank check."""
    _rank = {"U": 0, "CUI": 1, "S": 2, "TS": 3}
    if _rank.get(label_level, 99) > _rank.get(principal.clearance_level, -1):
        raise ProblemException(
            type="urn:fathom:problem:common:forbidden",
            title="Insufficient clearance",
            status=403,
        )
    missing = set(label_compartments) - set(principal.compartments)
    if missing:
        raise ProblemException(
            type="urn:fathom:problem:common:forbidden",
            title="Missing compartment",
            status=403,
            # Never name the missing compartment(s) in the body -- 31-auth.md
            # §6.5's amendment: that would disclose a compartment's existence
            # to a principal not cleared to know it.
        )
