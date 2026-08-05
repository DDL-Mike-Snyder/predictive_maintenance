"""Canonical identity references. Document 03 §3.3, transcribed exactly.

Four rules from §3.3 govern every type in this module:

1. `asset_id`, `system_id`, `position_id`, `installed_item_id`, and `niin` are
   THE join keys. `hull_or_tail`, `eswbs`, `position_code`, and `nsn` are
   carried for human reference and for federation with external systems, and
   are never used as join keys internally, because external systems reissue
   and reformat them.
2. EIC is never a join key. NAVSEAINST 4790.8 Appendix A defines it as a
   7-character code whose leading positions identify system, subsystem, and
   equipment category -- a CLASS CODE OF VARIABLE SPECIFICITY, not an
   instance identifier.
3. A payload identifying a physical item identifies it as `installed_item_id`.
   A payload identifying a location identifies it as `position_id`. The
   distinction is load-bearing: remaining useful life, usage accumulation,
   and failure history attach to the installed item. Conflating the two
   produces the inherited-degradation failure document 04 §2 exists to
   prevent [C10].
4. A NIIN alone is a part type, not an installed item.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import Field

from ._base import Eswbs, FathomModel, Niin, NonEmptyStr, Nsn, Uic, UtcDateTime

CANONICAL_JOIN_KEYS: frozenset[str] = frozenset(
    {"asset_id", "system_id", "position_id", "installed_item_id", "niin"}
)
"""The ONLY fields ever used as a join key internally. Document 03 §3.3 rule 1."""

HUMAN_REFERENCE_ONLY: frozenset[str] = frozenset(
    {"hull_or_tail", "eswbs", "position_code", "nsn", "eic"}
)
"""Carried for human reference and external federation only. Never a join key.
Lint rule FTH001 (build doc 10 §4.4) fails any join written against one of these."""


class Domain(StrEnum):
    SURFACE = "surface"
    SUBSURFACE = "subsurface"
    UNMANNED = "unmanned"


class AssetRef(FathomModel):
    asset_id: UUID = Field(description="Stable internal UUID; the join key.")
    hull_or_tail: NonEmptyStr = Field(
        description=(
            "'DDG 113', 'SSN 796', 'MQ-25 004' -- human reference only. SPACE, "
            "never a hyphen (SECNAVINST 5030.8D Enclosure 6). Trailing N denotes "
            "nuclear propulsion; a leading 'T-' denotes Military Sealift Command."
        )
    )
    uic: Uic = Field(description="Unit Identification Code.")
    class_id: NonEmptyStr = Field(
        description=(
            "Class designation, expressed as the LEAD HULL NUMBER "
            "(68 for NIMITZ, 51 for ARLEIGH BURKE), plus flight/block."
        )
    )
    domain: Domain


class SystemRef(FathomModel):
    """Document 03 §3.3 [C31]."""

    system_id: UUID = Field(description="Stable internal UUID; the join key.")
    eswbs: Eswbs = Field(description="Human reference and external federation only.")
    eic: NonEmptyStr | None = Field(
        default=None,
        description=(
            "Equipment Identification Code, where the system level has one. Never a join key."
        ),
    )


class PositionRef(FathomModel):
    position_id: UUID = Field(description="Stable internal UUID; the join key.")
    position_code: NonEmptyStr = Field(description="'233-04-A' -- human reference only.")
    system_id: UUID


class InstalledItemRef(FathomModel):
    """Document 03 §3.3 [C10, D9]."""

    installed_item_id: UUID = Field(
        description="Stable internal UUID; the join key. Identifies the PHYSICAL ITEM."
    )
    iuid: NonEmptyStr | None = Field(
        default=None,
        description=(
            "Item Unique Identification per DoDI 8320.04, where assigned. "
            "DoDI 4151.22 §1.2.d/§1.2.l require serialized item management and "
            "IUID to optimize RCM/CBM+ data analytics -- the externally mandated "
            "instance identity, not the EIC."
        ),
    )
    eic: NonEmptyStr | None = Field(
        default=None,
        description="EIC of the class this item instantiates. Federation/human reference only.",
    )
    position_id: UUID = Field(description="Where it is installed.")
    niin: Niin = Field(description="What it is.")
    serial_or_lot: NonEmptyStr | None = Field(default=None, description="Where tracked.")
    installed_at: UtcDateTime


class PartRef(FathomModel):
    niin: Niin = Field(description="National Item Identification Number; the join key.")
    nsn: Nsn | None = Field(default=None, description="Full NSN where known.")
    apl: NonEmptyStr | None = Field(default=None, description="Allowance Parts List reference.")
    equipment_family: NonEmptyStr = Field(
        description=(
            "Canonical grouping for model binding and calibration [D35]. "
            "Defined and served by Reference Data, versioned, required on every part."
        )
    )
