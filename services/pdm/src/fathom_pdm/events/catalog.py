"""Machine-readable event catalog. Document 09 §4.2, §8.2: `PUBLISHES`/
`CONSUMES` here MUST equal `helm/values.yaml`'s `events.publishes`/
`events.consumes` MUST equal document 03 §6's catalog rows for `pdm`.

This vertical slice implements `prediction.updated` end to end and declares
the rest of the catalog for completeness/CI-reconciliation, without yet
wiring every consumer handler (out of scope for proving the pattern; see
services/pdm/README.md's Definition of Done for what remains).
"""

from __future__ import annotations

PUBLISHES: frozenset[str] = frozenset(
    {
        "fathom.pdm.prediction.updated",
        "fathom.pdm.prediction.invalidated",
        "fathom.pdm.criticality_tier.assigned",
        "fathom.pdm.model_binding.activated",
    }
)

CONSUMES: frozenset[str] = frozenset(
    {
        "fathom.registry.asset.registered",
        "fathom.registry.asset.status_changed",
        "fathom.registry.configuration_baseline.changed",
        "fathom.registry.installed_item.installed",
        "fathom.registry.installed_item.removed",
        "fathom.registry.installed_item.identity_resolved",
        "fathom.telemetry.telemetry_batch.ingested",
        "fathom.telemetry.health_indicator.computed",
        "fathom.telemetry.usage_counter.updated",
        "fathom.telemetry.usage_counter.reset",
        "fathom.telemetry.channel_mapping.version_published",
        "fathom.maintenance.maintenance_action.recorded",
        "fathom.maintenance.deferral.recorded",
        "fathom.pma.anomaly_tag.confirmed",
        "fathom.failure-intel.causal_finding.published",
        "fathom.failure-intel.failure_mode.attributed",
        "fathom.failure-intel.causal_feature_set.updated",
        "fathom.design-advisory.design_change.projected",
        # 11 §3.7: every domain sub-application subscribes to remediation,
        # regardless of whether it currently caches D13-classified content.
        # 32-audit.md line ~1450: the EVENT_TYPE is remediation.purge_executed,
        # published on TOPIC fathom.audit.remediation.v1 -- an earlier version
        # of this entry used the topic name here by mistake, which would never
        # have matched EVENT_TYPE_RE (no trailing "vN" segment is a valid verb).
        "fathom.audit.remediation.purge_executed",
    }
)
