"""Classification labels. Document 03 §7.3.

Two distinct disciplines, both load-bearing:

1. **Union-label rule.** Every derived value carries the union of its inputs'
   labels, recorded in `inherited_from`. `ClassificationLabel.union()` is the
   ONLY sanctioned way to label a derived value.
2. **Aggregation-discipline rule [D13].** Aggregation is itself a
   classification event: a rollup whose value moves when a compartmented
   item degrades discloses that item's existence. This is a property of the
   *formula* that computes a rollup, not something this module can enforce --
   see 27-fleet-status.md §3 and 22-pdm.md §6.1 for the discharge pattern
   (compartment-partitioned aggregation, never a live cross-compartment pool).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from ._base import FathomModel, NonEmptyStr


class ClassificationLevel(StrEnum):
    """Document 03 §7.3 `level`: U | CUI | S | TS."""

    U = "U"
    CUI = "CUI"
    S = "S"
    TS = "TS"

    @property
    def rank(self) -> int:
        return _LEVEL_RANK[self]


_LEVEL_RANK: dict[ClassificationLevel, int] = {
    ClassificationLevel.U: 0,
    ClassificationLevel.CUI: 1,
    ClassificationLevel.S: 2,
    ClassificationLevel.TS: 3,
}


class DisseminationControl(StrEnum):
    """The TEN authorized Limited Dissemination Controls. CLOSED enum.

    'FOUO'/'U//FOUO' are RETIRED (DoDI 5200.48 §3.4.b) and deliberately
    absent -- lint rule FTH005 rejects them as literals wherever they appear.
    """

    NOFORN = "NOFORN"
    FED_ONLY = "FED ONLY"
    FEDCON = "FEDCON"
    NOCON = "NOCON"
    DL_ONLY = "DL ONLY"
    RELIDO = "RELIDO"
    REL_TO = "REL TO"
    DISPLAY_ONLY = "DISPLAY ONLY"
    AC = "AC"
    AWP = "AWP"


class DistributionStatement(StrEnum):
    """DoDI 5230.24 Table 1."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    REL_TO = "REL TO"


_STATEMENT_ORDER = "ABCDEF"


class ClassificationLabel(FathomModel):
    level: ClassificationLevel = Field(description="U | CUI | S | TS.")
    cui_categories: tuple[NonEmptyStr, ...] = Field(
        default=(), description="CUI Registry categories present, e.g. SP-CTI, SP-NNPI."
    )
    dissemination: tuple[DisseminationControl, ...] = Field(default=())
    distribution_statement: DistributionStatement | None = Field(default=None)
    compartments: tuple[NonEmptyStr, ...] = Field(default=())
    derived_from: NonEmptyStr | None = Field(
        default=None, description="Classification authority reference."
    )
    inherited_from: tuple[NonEmptyStr, ...] = Field(
        default=(), description="Input label references, for derived values [D13]."
    )

    @model_validator(mode="after")
    def _cui_categories_only_at_cui(self) -> Self:
        if self.cui_categories and self.level is ClassificationLevel.U:
            raise ValueError("level='U' cannot carry `cui_categories` (DoDI 5200.48)")
        return self

    @classmethod
    def union(cls, *inputs: "ClassificationLabel", derived_from: str) -> Self:
        """THE only sanctioned way to label a derived value. Document 03 §7.3,
        §15 obligation 4: 'classification labels on every response and event,
        with `inherited_from` set as the union of inputs on every derived value.'
        """
        if not inputs:
            raise ValueError("a derived value has at least one input label")
        return cls(
            level=max((i.level for i in inputs), key=lambda lv: lv.rank),
            cui_categories=tuple(sorted({c for i in inputs for c in i.cui_categories})),
            dissemination=tuple(sorted({d for i in inputs for d in i.dissemination})),
            distribution_statement=_most_restrictive_statement(inputs),
            compartments=tuple(sorted({c for i in inputs for c in i.compartments})),
            derived_from=derived_from,
            inherited_from=tuple(
                sorted({r for i in inputs for r in ([i.derived_from] if i.derived_from else [])})
            ),
        )


def _most_restrictive_statement(
    inputs: tuple[ClassificationLabel, ...],
) -> DistributionStatement | None:
    present = {i.distribution_statement for i in inputs if i.distribution_statement}
    if not present:
        return None
    if DistributionStatement.REL_TO in present and len(present) > 1:
        raise ValueError(
            "cannot mechanically union `REL TO` with a lettered distribution statement (OQ-16)"
        )
    lettered = [s for s in present if s.value in _STATEMENT_ORDER]
    if not lettered:
        return DistributionStatement.REL_TO
    return max(lettered, key=lambda s: _STATEMENT_ORDER.index(s.value))
