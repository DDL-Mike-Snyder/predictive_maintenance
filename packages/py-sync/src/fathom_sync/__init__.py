"""FATHOM outbox/inbox library. Document 11.

Every program-built service wires the transactional outbox (`OutboxWriter`)
without exception, including services with no current edge profile (03 §15
obligation 11). The inbox (`Inbox`, `evaluate_fence`) is wired by every
consumer of at least one event type.
"""

from .baseline_fence import BaselineFencedComputation, BaselineSupersededError
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
from .consumer import InboundConsumer, PollResult
from .inbox import EpochFence, FenceDecision, Inbox, evaluate_fence
from .models import (
    Base,
    InboxRow,
    OutboxQuarantineRow,
    OutboxRow,
    ProducerSequenceRow,
    RemediatedSelectorRow,
)
from .outbox import EventId, OutboxWriter, SigningPort, UnitOfWork
from .readmodel import ReadinessCheckResult, ReadModelLag, StalenessBoundExceededError
from .relay import OutboxRelay, ShardRunStats, SignatureVerificationError

__all__ = [
    "Base",
    "BaselineFencedComputation",
    "BaselineSupersededError",
    "BreachAction",
    "ConflictPolicy",
    "ConflictPolicyRegistry",
    "DivergenceBudgetDeclaration",
    "EpochFence",
    "EventId",
    "FenceDecision",
    "HybridLogicalClock",
    "InboundConsumer",
    "Inbox",
    "InboxRow",
    "MergeContext",
    "MergeDecision",
    "MonotonicDeadline",
    "MonotonicSequencer",
    "OutboxQuarantineRow",
    "OutboxRelay",
    "OutboxRow",
    "OutboxWriter",
    "PolicyId",
    "PollResult",
    "ProducerSequenceRow",
    "ReadModelLag",
    "ReadinessCheckResult",
    "RemediatedSelectorRow",
    "ShardRunStats",
    "SignatureVerificationError",
    "SigningPort",
    "StalenessBoundExceededError",
    "UnitOfWork",
    "evaluate_fence",
    "monotonic_backoff",
]
