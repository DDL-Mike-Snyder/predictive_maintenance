"""FATHOM canonical schemas -- the shared kernel and shared payload schemas.

Document 03 §7, §5.5. This is the public surface; import from here, not from
individual modules, so a future internal reshuffle doesn't break consumers.
"""

from ._base import Eswbs, FathomModel, Niin, NonEmptyStr, Nsn, Uic, UtcDateTime
from .annotations import SideEffects, Substitution
from .authority import AuthorityClass
from .classification import (
    ClassificationLabel,
    ClassificationLevel,
    DisseminationControl,
    DistributionStatement,
)
from .constants import CALIBRATION_POPULATION_FLOOR, PREDICTION_HORIZONS_DAYS
from .decision import (
    Basis,
    ConsequenceWeights,
    ExpectedConsequence,
    RiskPosture,
    TimingBasis,
    UncalibratedAndUnratedError,
    expected_consequence,
)
from .envelope import (
    Clock,
    EventEnvelope,
    EventScope,
    EventSubject,
    HybridLogicalClock,
    ProducerRef,
    SyncQuality,
    TimeSource,
)
from .identity import (
    CANONICAL_JOIN_KEYS,
    HUMAN_REFERENCE_ONLY,
    AssetRef,
    Domain,
    InstalledItemRef,
    PartRef,
    PositionRef,
    SystemRef,
)
from .prediction import ContributingFactor, FailurePrediction, ReferenceClass, Rul, RulUnit
from .proposal import (
    ALWAYS_DUAL_CONTROL_KINDS,
    COUNTER_SIGNATURE_REQUIRED_KINDS,
    EXTERNAL_LEGAL_EFFECT_KINDS,
    BlastRadius,
    Evidence,
    EvidenceKind,
    Proposal,
    ProposalKind,
    ProposalStatus,
    ProposalTargetSlug,
    SourceTrust,
)
from .slugs import AnySlug, PlatformServiceSlug, SubAppSlug
from .topics import EVENT_TYPE_RE, TOPIC_RE, event_type, proposal_topic, topic_name
from .version import __schema_major__, __version__

__all__ = [
    "ALWAYS_DUAL_CONTROL_KINDS",
    "CALIBRATION_POPULATION_FLOOR",
    "CANONICAL_JOIN_KEYS",
    "COUNTER_SIGNATURE_REQUIRED_KINDS",
    "EVENT_TYPE_RE",
    "EXTERNAL_LEGAL_EFFECT_KINDS",
    "HUMAN_REFERENCE_ONLY",
    "PREDICTION_HORIZONS_DAYS",
    "TOPIC_RE",
    "AnySlug",
    "AssetRef",
    "AuthorityClass",
    "Basis",
    "BlastRadius",
    "ClassificationLabel",
    "ClassificationLevel",
    "Clock",
    "ConsequenceWeights",
    "ContributingFactor",
    "DisseminationControl",
    "DistributionStatement",
    "Domain",
    "Eswbs",
    "EventEnvelope",
    "EventScope",
    "EventSubject",
    "Evidence",
    "EvidenceKind",
    "ExpectedConsequence",
    "FailurePrediction",
    "FathomModel",
    "HybridLogicalClock",
    "InstalledItemRef",
    "Niin",
    "NonEmptyStr",
    "Nsn",
    "PartRef",
    "PlatformServiceSlug",
    "PositionRef",
    "ProducerRef",
    "Proposal",
    "ProposalKind",
    "ProposalStatus",
    "ProposalTargetSlug",
    "ReferenceClass",
    "RiskPosture",
    "Rul",
    "RulUnit",
    "SideEffects",
    "SourceTrust",
    "SubAppSlug",
    "Substitution",
    "SyncQuality",
    "SystemRef",
    "TimeSource",
    "TimingBasis",
    "Uic",
    "UncalibratedAndUnratedError",
    "UtcDateTime",
    "__schema_major__",
    "__version__",
    "event_type",
    "expected_consequence",
    "proposal_topic",
    "topic_name",
]
