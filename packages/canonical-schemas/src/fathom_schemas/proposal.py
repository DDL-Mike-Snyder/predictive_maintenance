"""`Proposal`. Document 03 §7.2, §7.2.1.

Not used by PdM's own service code -- PdM produces predictions, not
recommendations, and sets no `authority_class` (22-pdm.md: "No `POST
/proposals`. PdM produces no agent proposals... Do not create a proposal
surface in PdM."). Included here for the other eight sub-applications that
do create proposals, and for package completeness.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from ._base import FathomModel, NonEmptyStr, UtcDateTime
from .authority import AuthorityClass
from .classification import ClassificationLabel
from .envelope import EventSubject
from .slugs import PlatformServiceSlug, SubAppSlug

ProposalTargetSlug = SubAppSlug | Literal[PlatformServiceSlug.AUDIT]


class ProposalKind(StrEnum):
    """Eight values. `PURGE`/`REWRAP` added by amendment 03-2 for Audit's
    crypto-shred mechanism; neither may ever be created or adjudicated by an
    agent or an `accountable_autonomous` identity, with no exception."""

    ANOMALY_TAG = "anomaly_tag"
    WORK_CANDIDATE = "work_candidate"
    REQUISITION = "requisition"
    INTERVAL_CHANGE = "interval_change"
    REDESIGN_CASE = "redesign_case"
    CONFIGURATION_CHANGE = "configuration_change"
    PURGE = "purge"
    REWRAP = "rewrap"


class BlastRadius(StrEnum):
    ITEM = "item"
    ASSET = "asset"
    CLASS = "class"
    FLEET = "fleet"


class ProposalStatus(StrEnum):
    PROPOSED = "proposed"
    CLAIMED = "claimed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"


class EvidenceKind(StrEnum):
    RECORD = "record"
    DOCUMENT_CHUNK = "document_chunk"
    PREDICTION = "prediction"
    TRACE = "trace"


class SourceTrust(StrEnum):
    PROGRAM = "program"
    VENDOR = "vendor"
    EXTERNAL = "external"


class Evidence(FathomModel):
    kind: EvidenceKind
    ref: NonEmptyStr
    excerpt: str | None = Field(default=None)
    relevance: float | None = Field(default=None)
    source_trust: SourceTrust


EXTERNAL_LEGAL_EFFECT_KINDS: frozenset[ProposalKind] = frozenset({ProposalKind.REQUISITION})
ALWAYS_DUAL_CONTROL_KINDS: frozenset[ProposalKind] = frozenset(
    {ProposalKind.PURGE, ProposalKind.REWRAP}
)
COUNTER_SIGNATURE_REQUIRED_KINDS: frozenset[ProposalKind] = frozenset(
    {ProposalKind.PURGE, ProposalKind.REWRAP}
)


class Proposal(FathomModel):
    proposal_id: UUID
    kind: ProposalKind
    target_sub_app: ProposalTargetSlug
    subject: EventSubject
    baseline_id: UUID
    baseline_epoch: int = Field(ge=0)
    payload: dict[str, object]
    evidence: tuple[Evidence, ...] = Field(min_length=1)
    rationale: NonEmptyStr
    confidence: float = Field(ge=0.0, le=1.0)
    agent_id: NonEmptyStr | None = Field(default=None)
    agent_version: NonEmptyStr | None = Field(default=None)
    llm_version: NonEmptyStr | None = Field(default=None)
    trace_ref: NonEmptyStr | None = Field(default=None)
    authority_class: AuthorityClass
    blast_radius: BlastRadius
    requires_dual_control: bool
    valid_until: UtcDateTime
    status: ProposalStatus
    claimed_by: NonEmptyStr | None = Field(default=None)
    claimed_until: UtcDateTime | None = Field(default=None)
    adjudicated_by: NonEmptyStr | None = Field(default=None)
    adjudicated_at: UtcDateTime | None = Field(default=None)
    adjudication_note: str | None = Field(default=None)
    second_adjudicator: NonEmptyStr | None = Field(default=None)
    second_adjudicated_at: UtcDateTime | None = Field(default=None)
    counter_signature_by: NonEmptyStr | None = Field(default=None)
    counter_signature_at: UtcDateTime | None = Field(default=None)
    requires_counter_signature: bool
    classification: ClassificationLabel

    @model_validator(mode="after")
    def _dual_control_required_at_scope(self) -> Self:
        mandatory = (
            self.blast_radius in (BlastRadius.CLASS, BlastRadius.FLEET)
            or self.kind in EXTERNAL_LEGAL_EFFECT_KINDS
            or self.kind in ALWAYS_DUAL_CONTROL_KINDS
        )
        if mandatory and not self.requires_dual_control:
            raise ValueError(
                f"kind={self.kind.value!r} at blast_radius={self.blast_radius.value!r} "
                "requires dual control (03 §7.2)"
            )
        return self

    @model_validator(mode="after")
    def _counter_signature_required_at_scope(self) -> Self:
        mandatory = self.kind in COUNTER_SIGNATURE_REQUIRED_KINDS and self.blast_radius in (
            BlastRadius.CLASS,
            BlastRadius.FLEET,
        )
        if mandatory and not self.requires_counter_signature:
            raise ValueError(
                f"kind={self.kind.value!r} at blast_radius={self.blast_radius.value!r} "
                "requires a fleet_authority counter-signature"
            )
        if self.requires_counter_signature and not mandatory:
            raise ValueError("requires_counter_signature set where it is not mandated")
        return self

    @model_validator(mode="after")
    def _agent_provenance_consistent(self) -> Self:
        agent_fields = (self.agent_id, self.agent_version, self.llm_version)
        if any(agent_fields) and not all(agent_fields):
            raise ValueError("agent_id, agent_version, and llm_version are all-or-nothing")
        if self.agent_id is not None and self.trace_ref is None:
            raise ValueError("an agent-authored proposal requires trace_ref")
        if self.kind in ALWAYS_DUAL_CONTROL_KINDS and self.agent_id is not None:
            raise ValueError(f"kind={self.kind.value!r} may never be agent-authored")
        return self

    @model_validator(mode="after")
    def _claim_state_consistent(self) -> Self:
        if self.status is ProposalStatus.CLAIMED and not (self.claimed_by and self.claimed_until):
            raise ValueError("status='claimed' requires claimed_by and claimed_until")
        return self

    @model_validator(mode="after")
    def _adjudication_state_consistent(self) -> Self:
        if self.status is ProposalStatus.APPROVED:
            if self.adjudicated_by is None or self.adjudicated_at is None:
                raise ValueError("status='approved' requires adjudicated_by and adjudicated_at")
            if self.requires_dual_control and (
                self.second_adjudicator is None or self.second_adjudicated_at is None
            ):
                raise ValueError(
                    "status='approved' under dual control requires a second adjudicator"
                )
            if self.requires_dual_control and self.second_adjudicator == self.adjudicated_by:
                raise ValueError("the second adjudicator must differ from the first")
            if self.requires_counter_signature and (
                self.counter_signature_by is None or self.counter_signature_at is None
            ):
                raise ValueError("status='approved' requiring counter-signature has none recorded")
        return self

    @property
    def rests_solely_on_non_program_content(self) -> bool:
        return all(e.source_trust is not SourceTrust.PROGRAM for e in self.evidence)

    def is_expired_at(self, now: UtcDateTime) -> bool:
        return now >= self.valid_until

    def revalidation_required_against(self, current_baseline_epoch: int) -> bool:
        return self.baseline_epoch < current_baseline_epoch
