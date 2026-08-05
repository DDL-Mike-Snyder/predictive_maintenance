"""Document 03 §4.1 `x-substitution` / `x-side-effects` vocabulary.

Pure enums, no web-framework dependency -- so this module can be imported by
any consumer of the wire contract (a Domino Job, a conformance-suite fixture,
a TypeScript-generation step) without pulling in FastAPI.

The `@operation` decorator that actually attaches these to a FastAPI route's
OpenAPI extension keys lives in `packages/contracts/src/fathom_contracts/operation.py`,
which imports the two enums below rather than redefining them -- one value-type
authority, one decorator implementation.
"""

from __future__ import annotations

from enum import StrEnum


class Substitution(StrEnum):
    """Document 03 §4.1 `x-substitution`.

    `required`: a substituting implementation MUST provide this operation
    (document 03 §10 requirement 1).
    `internal`: it need not.
    """

    REQUIRED = "required"
    INTERNAL = "internal"


class SideEffects(StrEnum):
    """Document 03 §4.1 `x-side-effects`.

    Agent eligibility is determined by declared side-effect class, NOT by
    HTTP method -- a method check wrongly excludes the compute-only `POST`
    operations several agents require [C1, D11].
    """

    NONE = "none"
    PROPOSAL_ONLY = "proposal-only"
    STATE_CHANGING = "state-changing"

    @property
    def agent_eligible_permitted(self) -> bool:
        """Document 03 §8.1 and §15 obligation 8: `x-agent-eligible` may be
        asserted only where `x-side-effects` is `none` or `proposal-only`."""
        return self in (SideEffects.NONE, SideEffects.PROPOSAL_ONLY)
