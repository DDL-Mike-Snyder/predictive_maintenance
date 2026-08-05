"""FATHOM outbox/inbox library. Document 11.

Every program-built service wires the transactional outbox (`OutboxWriter`)
without exception, including services with no current edge profile (03 §15
obligation 11). The inbox (`Inbox`, `evaluate_fence`) is wired by every
consumer of at least one event type.
"""

from .baseline_fence import BaselineFencedComputation, BaselineSuperseded
from .clock import HybridLogicalClock, MonotonicDeadline, MonotonicSequencer, monotonic_backoff
from .conflict_policy import (
    BreachAction,
    ConflictPolicy,
    ConflictPolicyRegistry,
    DivergenceBudgetDeclaration,
    MergeContext,
    MergeDecision,
    PolicyId,
)
from .inbox import EpochFence, FenceDecision, Inbox, evaluate_fence
from .models import Base, InboxRow, OutboxRow, ProducerSequenceRow, RemediatedSelectorRow
from .outbox import EventId, OutboxWriter, SigningPort, UnitOfWork
from .readmodel import ReadinessCheckResult, ReadModelLag, StalenessBoundExceeded

__all__ = [
    "Base",
    "BaselineFencedComputation",
    "BaselineSuperseded",
    "BreachAction",
    "ConflictPolicy",
    "ConflictPolicyRegistry",
    "DivergenceBudgetDeclaration",
    "EpochFence",
    "EventId",
    "FenceDecision",
    "HybridLogicalClock",
    "Inbox",
    "InboxRow",
    "MergeContext",
    "MergeDecision",
    "MonotonicDeadline",
    "MonotonicSequencer",
    "OutboxRow",
    "OutboxWriter",
    "PolicyId",
    "ProducerSequenceRow",
    "ReadModelLag",
    "ReadinessCheckResult",
    "RemediatedSelectorRow",
    "SigningPort",
    "StalenessBoundExceeded",
    "UnitOfWork",
    "evaluate_fence",
    "monotonic_backoff",
]
