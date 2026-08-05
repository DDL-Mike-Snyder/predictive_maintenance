"""Shared base class and serialization discipline for every canonical type.

Wire-format rules are fixed here, once, because document 03's substitution
protocol (§10) conformance-tests nine independent implementations against one
specification. A per-model serialization choice is a wire-format fork.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from typing import Annotated, Any

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    PlainSerializer,
    StringConstraints,
)

# --- Time --------------------------------------------------------------------
# Document 03 §4 "Time": RFC 3339 with explicit offset, UTC on the wire.
# DoD Zero Trust Overlays v1.1 (cited in 03 §5.4) set audit time-stamp
# granularity at 1 millisecond. Fixed 6-digit microsecond precision satisfies
# that and — critically — makes the serialized form of a given instant
# byte-stable, which a variable-precision serializer does not.


def _to_utc_z(value: _dt.datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("naive datetime reached serialization")
    return value.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


UtcDateTime = Annotated[AwareDatetime, PlainSerializer(_to_utc_z, return_type=str)]
"""An RFC 3339 instant. Rejects naive datetimes; always serializes as UTC 'Z'
with 6-digit microseconds. Document 03 §4 (Time)."""

# --- Constrained scalars -------------------------------------------------------
# Document 03 §3.3. Every one of these is a wire-format constraint, not a
# convenience: a substituting implementation is tested against them.

Niin = Annotated[str, StringConstraints(pattern=r"^(\d{9}|[A-Z]{2}[A-Z0-9]{7})$")]
"""Document 03 §3.3 PartRef -- `niin` is *the* join key for a part type.

NOT restricted to a true 9-digit National Item Identification Number.
Document 07 §4.8 documents that a real shipboard catalogue is deliberately
heterogeneous -- NSN, permanent NICN, temporary NICN, LICN, and CAGE+part-number
identifiers coexist. The accepted shape is therefore: 9 digits (a true NIIN),
OR two letters followed by 7 alphanumeric characters (the NICN/LICN
item-portion documented in 07 §4.8, e.g. `LL0000123`)."""

Nsn = Annotated[str, StringConstraints(pattern=r"^\d{13}$")]
"""National Stock Number. 13 digits (4-digit FSC + 9-digit NIIN). Human
reference and external federation only; NEVER a join key. Document 03 §3.3 rule 1."""

Uic = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{5,6}$")]
"""Unit Identification Code. Document 03 §3.3."""

Eswbs = Annotated[str, StringConstraints(pattern=r"^\d{3,6}$")]
"""Expanded Ship Work Breakdown Structure code. Human reference and external
federation only. Document 03 §3.3 SystemRef."""

NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


# --- Base model ----------------------------------------------------------------
class FathomModel(BaseModel):
    """Base for every canonical type.

    `extra="forbid"` is load-bearing rather than tidy: a payload carrying
    `eic`, `equipment_id`, or `drivers` is rejected at parse time by every
    service, because none of those fields exists on any canonical model.
    See document 05 C2, C10, D23.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,  # canonical payloads are values, not buffers
        validate_assignment=True,
        populate_by_name=False,  # no aliases: one name on the wire, always
        ser_json_timedelta="float",
        str_strip_whitespace=True,
    )

    def wire_dict(self) -> dict[str, Any]:
        """The exact dict that goes on the wire.

        `exclude_none=False`: document 03 models absence as an explicit `null`
        for `rul` (§7.1) and for unset adjudication fields (§7.2). Dropping
        nulls would make "omitted" and "null" indistinguishable to a consumer.
        """
        return self.model_dump(mode="json", by_alias=False, exclude_none=False)

    def canonical_json(self) -> bytes:
        """RFC 8785 (JCS) canonical form, for hashing, signing, and dedup.

        Never hash `wire_dict()` output directly -- key order, number
        formatting, and Unicode escaping vary between serializers.
        """
        return _jcs(self.wire_dict())

    def content_hash(self) -> str:
        """Lowercase hex SHA-256 of the JCS form. Stable across languages."""
        return hashlib.sha256(self.canonical_json()).hexdigest()


def _jcs(value: Any) -> bytes:
    """Minimal RFC 8785 JSON Canonicalization Scheme serializer.

    Sorted keys, no insignificant whitespace, UTF-8 output, no NaN/Infinity.
    Kept in-package rather than taken as a dependency because
    `canonical-schemas` must import in an air-gapped Domino Job container
    with no wheel fetch at pod start (01 §12, finding D26).
    """
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
        default=_jcs_default,
    ).encode("utf-8")


def _jcs_default(value: Any) -> Any:
    raise TypeError(f"non-canonicalizable value on the wire: {type(value)!r}")
