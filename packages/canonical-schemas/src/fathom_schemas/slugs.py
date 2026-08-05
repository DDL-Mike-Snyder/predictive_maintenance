"""Canonical sub-application and platform-service slugs.

Document 03 §3.1. The slug is the ONLY identifier for a sub-application on
any wire -- used without variation in topic names, event `producer` fields,
`target_sub_app` values, API base paths, conformance directories, and
manifest directories.
"""

from __future__ import annotations

from enum import StrEnum


class SubAppSlug(StrEnum):
    """The nine domain sub-applications. Document 03 §3.1, table rows 1-9."""

    REGISTRY = "registry"  # Asset & Configuration Registry
    TELEMETRY = "telemetry"  # Condition & Telemetry
    PDM = "pdm"  # Predictive Maintenance
    FLEET_STATUS = "fleet-status"  # Fleet Status & Readiness
    MAINTENANCE = "maintenance"  # Maintenance Execution & Scheduling
    SUPPLY = "supply"  # Supply Chain & Inventory
    PMA = "pma"  # Post-Mission Analysis
    FAILURE_INTEL = "failure-intel"  # Failure Intelligence
    DESIGN_ADVISORY = "design-advisory"  # System Test & Design Advisory

    @property
    def canonical_name(self) -> str:
        return _CANONICAL_NAME[self]

    @property
    def display_abbreviation(self) -> str:
        """The ONLY string permitted in a user interface for this sub-application."""
        return _DISPLAY[self]

    def api_base_path(self, major: int) -> str:
        if major < 1:
            raise ValueError("API major version starts at 1")
        return f"/api/v{major}/{self.value}"


class PlatformServiceSlug(StrEnum):
    """Platform services. Document 03 §3.1 final paragraph."""

    GATEWAY = "gateway"
    AUTH = "auth"
    REFERENCE_DATA = "reference-data"
    KNOWLEDGE_RETRIEVAL = "knowledge-retrieval"
    AUDIT = "audit"
    NOTIFICATION = "notification"
    SYNC = "sync"
    TOOL_SERVER = "tool-server"


_CANONICAL_NAME: dict[SubAppSlug, str] = {
    SubAppSlug.REGISTRY: "Asset & Configuration Registry",
    SubAppSlug.TELEMETRY: "Condition & Telemetry",
    SubAppSlug.PDM: "Predictive Maintenance",
    SubAppSlug.FLEET_STATUS: "Fleet Status & Readiness",
    SubAppSlug.MAINTENANCE: "Maintenance Execution & Scheduling",
    SubAppSlug.SUPPLY: "Supply Chain & Inventory",
    SubAppSlug.PMA: "Post-Mission Analysis",
    SubAppSlug.FAILURE_INTEL: "Failure Intelligence",
    SubAppSlug.DESIGN_ADVISORY: "System Test & Design Advisory",
}

_DISPLAY: dict[SubAppSlug, str] = {
    SubAppSlug.REGISTRY: "Registry",
    SubAppSlug.TELEMETRY: "Telemetry",
    SubAppSlug.PDM: "PdM",
    SubAppSlug.FLEET_STATUS: "Fleet Status",
    SubAppSlug.MAINTENANCE: "Scheduling",
    SubAppSlug.SUPPLY: "Supply",
    SubAppSlug.PMA: "PMA",
    SubAppSlug.FAILURE_INTEL: "Failure Intelligence",
    SubAppSlug.DESIGN_ADVISORY: "Design Advisory",
}

AnySlug = SubAppSlug | PlatformServiceSlug
