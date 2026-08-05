"""Conflict policy declaration and enforcement. Document 11 §7.

Declaration is complete-or-fail: a service enumerates EVERY aggregate it
owns at startup, or the registry refuses to start (C20 -- an implicit
default is not permitted, only an explicit one)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import final


class PolicyId(StrEnum):
    APPEND_ONLY_DEDUP = "append-only-dedup"
    RECOMPUTABLE_SUPERSEDE = "recomputable-supersede"
    EDGE_GENERATABLE = "edge-generatable"
    APPEND_ONLY_IMMUTABLE = "append-only-immutable"
    APPEND_ONLY_SERVER_ADJUDICATED = "append-only-server-adjudicated"
    EDGE_AUTHORITATIVE_APPEND_ONLY = "edge-authoritative-append-only"
    SERVER_AUTHORITATIVE_EDGE_SUBMITS = "server-authoritative-edge-submits"
    EDGE_AUTHORITATIVE_THEN_ENTERPRISE = "edge-authoritative-then-enterprise"
    ENTERPRISE_AUTHORITATIVE_CACHED_DEGRADED = "enterprise-authoritative-cached-degraded"
    SERVER_AUTHORITATIVE_QUEUED = "server-authoritative-queued"
    ENTERPRISE_AUTHORITATIVE_PROVISIONAL_EDGE = "enterprise-authoritative-provisional-edge"
    MONOTONIC_MERGE_KEYED = "monotonic-merge-keyed"
    ENTERPRISE_AUTHORITATIVE_NOT_EDGE_WRITABLE = "enterprise-authoritative-not-edge-writable"  # default


class MergeDecision(StrEnum):
    APPLY = "apply"
    IGNORE = "ignore"
    SUPERSEDE = "supersede"
    REJECT = "reject"
    QUARANTINE = "quarantine"
    EMIT_CORRECTION = "emit_correction"


class BreachAction(StrEnum):
    EXPLICIT_READ_ONLY = "explicit_read_only"
    ALERT_AND_DEGRADE = "alert_and_degrade"  # audit store ONLY [amendment 11-3]


@dataclass(frozen=True)
class DivergenceBudgetDeclaration:
    aggregate: str
    max_disconnection: timedelta
    max_unreconciled_records: int | None = None
    max_unreconciled_bytes: int | None = None
    on_breach: BreachAction = BreachAction.EXPLICIT_READ_ONLY

    def __post_init__(self) -> None:
        if self.on_breach is BreachAction.ALERT_AND_DEGRADE and self.aggregate != "audit_record":
            raise ValueError(
                "BreachAction.ALERT_AND_DEGRADE is permitted only for the audit "
                "store [amendment 11-3] -- refusing audit writes stops the "
                "accountability record for every service on the hull"
            )


@dataclass(frozen=True)
class MergeContext:
    """Whatever context a `ConflictPolicy.merge()` needs, beyond the two
    records themselves -- deliberately does not carry a liveliness signal
    (see `_forbid_liveliness_binding`)."""

    now_monotonic: float


class ConflictPolicy(ABC):
    aggregate: str
    policy_id: PolicyId
    edge_writable: bool
    divergence_budget: DivergenceBudgetDeclaration | None

    @abstractmethod
    def merge(self, ctx: MergeContext, local: object | None, incoming: object) -> MergeDecision: ...

    @final
    def _precedence(self, a_key: tuple[str, str, int], b_key: tuple[str, str, int]) -> int:
        """(producer_slug, producer_node_id, monotonic_seq) within one
        producer-node; total order across producer-nodes uses the HLC
        instead, supplied by the caller. Wall time is never consulted."""
        if a_key < b_key:
            return -1
        if a_key > b_key:
            return 1
        return 0

    @final
    def _forbid_liveliness_binding(self) -> None:
        """Authority is a function of the AGGREGATE, never of connectivity.
        There is no `is_connected()` input to any merge decision -- CI gate
        (11 §11.5) forbids a liveliness predicate reachable from `merge()`."""
        return None


class ConflictPolicyRegistry:
    """Enumerates every aggregate a service owns at startup. Fails to
    construct if the enumeration is incomplete (C20)."""

    def __init__(self, service: str, policies: list[ConflictPolicy]) -> None:
        self.service = service
        self._by_aggregate: dict[str, ConflictPolicy] = {p.aggregate: p for p in policies}

    @classmethod
    def declare(cls, *, service: str, policies: list[ConflictPolicy]) -> "ConflictPolicyRegistry":
        return cls(service, policies)

    def policy_for(self, aggregate: str) -> ConflictPolicy:
        try:
            return self._by_aggregate[aggregate]
        except KeyError:
            raise ValueError(
                f"aggregate {aggregate!r} has no declared conflict policy for service "
                f"{self.service!r} -- an implicit default is not permitted (C20)"
            ) from None
