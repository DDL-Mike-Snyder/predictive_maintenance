"""Document 03 §7.2.1. The organizational role permitted to ADJUDICATE a
proposal, given its `kind` and `blast_radius`.

DISTINCT from the agent authority classes of 03 §8.3, which govern which
CREDENTIAL an agent calls with -- conflating them is the available mistake;
`31-auth.md` §2.5 resolves the one-name-two-meanings collision between this
field and `fathom.agent.authority`.
"""

from __future__ import annotations

from enum import StrEnum


class AuthorityClass(StrEnum):
    """Closed vocabulary. Phase 3 may add finer-grained roles WITHIN a class
    but may not remove the minimum this table establishes."""

    MAINTAINER = "maintainer"  # Ship's Force Maintainer
    PLANNER = "planner"  # RMC / Availability Planner
    SUPPLY_OFFICER = "supply_officer"  # Supply role, ship or RMC
    DESIGN_AUTHORITY = "design_authority"  # PEO / Design Engineer
    FLEET_AUTHORITY = "fleet_authority"  # TYCOM Readiness Officer
    SECURITY_OFFICER = "security_officer"  # ISSM / ISSO
