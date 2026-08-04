# Build Framework 10 — Shared Packages: Canonical Schemas, Contracts, and Agent Tooling

| | |
|---|---|
| **Status** | Build framework, rev 1 |
| **Scope** | `packages/canonical-schemas`, `packages/contracts`, `packages/agent-tooling` — the executable form of the binding contract in [03 — Integration Contracts](../architecture/03-integration-contracts.md) |
| **Binding source** | Document 03 rev 2. Where this document and document 03 disagree, **document 03 wins and this document is defective** |
| **Companion build documents** | [09 — Monorepo and Conventions](09-monorepo-and-conventions.md) (conventions, tooling versions, CI topology, shared Definition of Done template) |
| **Audience** | The coding agent building these three packages, and the nine sub-application coding agents that consume them |
| **Classification** | Internal |

---

## 1. Purpose and scope

### 1.1 Why this package exists

Nine sub-applications are implemented independently, by separate coding agents, from separate build-framework documents. They must nevertheless produce **byte-identical wire formats** for every shared type, because a substituting partner implementation is conformance-tested against a single specification and because a consumer's read model is built from a producer's events without negotiation.

Nine independent transcriptions of document 03 §7.1 will produce nine subtly different `FailurePrediction` shapes. One of them will spell the field `drivers` because that is what document 04 §4 still says (document 04 is remediation tranche 3 and has not yet been corrected — see §10.3). One will use `equipment_id` because document 04 §4's API surface still shows `GET /predictions?asset_id=&equipment_id=`. One will make `rul` unconditionally present. Each of those is a defect the architecture review already found, dispositioned, and fixed in document 03; each would be silently reintroduced by transcription.

Therefore: **the shared types are written exactly once, here, and imported.** A sub-application that declares its own `AssetRef` is in violation of this document regardless of whether its fields happen to match.

### 1.2 The three packages

| Package | Owns | Consumed by |
|---|---|---|
| `packages/canonical-schemas` | Every type that crosses a sub-application boundary: identity references (03 §3.3), the event envelope and clock (03 §5.4), `FailurePrediction` (03 §7.1), `Proposal` (03 §7.2), `ClassificationLabel` (03 §7.3), the sub-application slug vocabulary (03 §3.1), the domain-vocabulary lint rules (03 §3.2) | All nine sub-applications, all eight platform services, `agents/*`, `models/*`, `data/synthetic` |
| `packages/contracts` | The OpenAPI 3.1 generation and validation pipeline (03 §4, §4.1), the AsyncAPI generation pipeline (03 §5.5), the committed-specification CI gate, and the five-category conformance harness (03 §10) | All nine sub-applications; substituting partner implementations |
| `packages/agent-tooling` | The tool-manifest schema and MCP-descriptor generator (03 §8.2), the eligibility gate (03 §8.1), the manifest conformance test generator (03 §8.4) | `agents/*`, `platform/tool-server` |

Dependency direction is strict and enforced by an import-linter contract (§9.4):

```
canonical-schemas  ←  contracts  ←  agent-tooling
        ↑                 ↑              ↑
        └──────── services/*, platform/*, agents/* ────┘
```

`canonical-schemas` depends on nothing in the monorepo. It must remain importable in a Domino Job container, in the edge runtime, and in the synthetic-data generator, none of which have a web framework available. **No FastAPI, no Kafka client, no database driver in `canonical-schemas`.**

### 1.3 Dual publication is a requirement, not a convenience

Document 03 §5.5 states that payload schemas *"live in `packages/canonical-schemas`, publish as versioned **Python and TypeScript** libraries, and register in a schema registry enforcing compatibility on publish."*

TypeScript is required because `apps/web` (document 01 §11) renders `FailurePrediction`, adjudicates `Proposal`, and displays `ClassificationLabel` banner markings. A hand-written TypeScript interface for those types is a second transcription and therefore a defect by the argument of §1.1.

The dual-publication rule adopted here:

1. **Python is the single source of truth.** Pydantic v2 models are authored by hand.
2. **JSON Schema (draft 2020-12) is the intermediate artifact,** generated from the Python models and **committed** to the repository.
3. **TypeScript types and Zod validators are generated from the committed JSON Schema.** They are never hand-edited; a CI job regenerates and diffs.
4. **A golden-vector corpus is the cross-language equivalence proof** (§4.9). Every vector must accept-or-reject identically in Python and TypeScript. This is the only mechanism that actually catches divergence, because JSON Schema cannot express all of the conditional validators (§4.6) and the TypeScript side reimplements them.

> **Field naming does not change across languages.** TypeScript interfaces keep `snake_case` keys. There is no camelCase transformation layer anywhere in the system. Document 03 §4 fixes `snake_case` JSON fields; a transform at the TypeScript boundary would make the wire format depend on which language serialized it, which is exactly the property this package exists to prevent.

### 1.4 What this document does not cover

- Repository layout, Python/Node versions, formatter and linter baseline configuration, commit conventions, CI runner topology, and the shared Definition of Done template: **document 09**.
- Per-sub-application API surfaces, aggregates, and internal components: document 04, and each sub-application's own build-framework document.
- The synthetic reference dataset content: `data/synthetic` and its own build document. This document specifies only the *fixture interface* the conformance harness requires (§6.8).

---

## 2. Traceability

Every schema element in this package traces to an exact section of document 03. The table below is the index; each model's docstring repeats its own citation. A field with no citation in this table is a defect.

| Artifact | Document 03 source | Review findings enforced |
|---|---|---|
| `SubAppSlug`, `PlatformServiceSlug` | §3.1 | C27, C28 |
| Vocabulary lint rules `FTH0xx` | §3.2 | C29, C10, C2, D23 |
| `AssetRef` | §3.3 | — |
| `SystemRef` | §3.3 | C31 |
| `PositionRef` | §3.3 | C10, C29 |
| `InstalledItemRef` | §3.3 | C10, D9 |
| `PartRef` | §3.3 | D35 |
| Join-key rule (`eic` never a join key) | §3.3 rules 1–2 | C2, C10 |
| `ProvisionalIdentity` marker | §3.3 final paragraph | D8, D9 |
| `Operation` annotations `x-substitution`, `x-side-effects` | §4.1 | C1, D11, C24 |
| `EventSubject`, `EventScope` | §5.4 | C11 |
| `Clock`, `SyncQuality` | §5.4 | D29 |
| `EventEnvelope` | §5.4 | C11, C26, D3, D4, D29, D30 |
| Topic-name grammar | §5.1 | C26 |
| `FailurePrediction` | §7.1 | C2, D7, D19, D22, D23, D36 |
| `Rul`, `ReferenceClass`, `RulUnit` | §7.1 | D19 |
| `ContributingFactor` | §7.1 | D23 |
| `Proposal` | §7.2 | C30, C39, C12, D14, D16 |
| `Evidence`, `SourceTrust` | §7.2, §9 | D14 |
| `ClassificationLabel` | §7.3 | D13 |
| `DisseminationControl` (ten LDCs) | §7.3 | D13 |
| Manifest schema | §8.2 | C1, D11 |
| Eligibility gate | §8.1, §15 obligation 8 | C1, D11 |
| Conformance harness (five categories) | §10 | D24, D25 |
| Schema registry and compatibility | §5.5 | — |

---

## 3. Package skeleton

```
packages/canonical-schemas/
  pyproject.toml
  README.md
  src/fathom_schemas/
    __init__.py               # the public surface; re-exports every shared type
    _base.py                  # FathomModel, UtcDateTime, canonical_json, JCS hashing
    slugs.py                  # 03 §3.1
    identity.py               # 03 §3.3
    envelope.py               # 03 §5.4  (EventEnvelope, Clock, SyncQuality, EventSubject)
    topics.py                 # 03 §5.1  topic-name grammar and event-type grammar
    prediction.py             # 03 §7.1
    proposal.py               # 03 §7.2
    classification.py         # 03 §7.3
    annotations.py            # 03 §4.1  SideEffects / Substitution enums (no web dep)
    constants.py              # thresholds sourced from doc 06, each cited
    version.py                # __schema_major__, __version__
  lint/                       # flake8 plugin: the FTH rule set (03 §3.2)
    fathom_vocab/
      __init__.py
      checker.py
      rules.py
  schemas/                    # COMMITTED generated JSON Schema, draft 2020-12
    fathom.canonical/2/*.json
  vectors/                    # COMMITTED golden vectors, cross-language
    <type>/valid/*.json
    <type>/invalid/*.json     # each carries an `_expect` block naming the violated rule
  ts/                         # the TypeScript package (generated + thin hand-written index)
    package.json
    src/generated/*.ts        # DO NOT EDIT
    src/index.ts
    test/vectors.test.ts
  tests/
```

```
packages/contracts/
  pyproject.toml
  src/fathom_contracts/
    __init__.py
    operation.py              # the @operation decorator; attaches 03 §4.1 extensions
    events.py                 # the @event registry; source for AsyncAPI
    openapi/
      export.py               # FastAPI app  -> OpenAPI 3.1 document
      validate.py             # the 03 §4 / §4.1 / §8.1 rule set
      diff.py                 # committed-spec gate + compatibility differ
    asyncapi/
      export.py               # event registry -> AsyncAPI 3.0 document
    registry/
      publish.py              # subject registration against the schema registry
      compat.py               # the compatibility rules the registry cannot express
    cli.py                    # fathom-contracts
  conformance/
    harness/                  # the importable base classes and fixtures
      __init__.py
      contract.py             # ContractConformance
      events.py               # EventConformance
      faults.py               # FaultInjectionConformance
      consumers.py            # ConsumerDrivenConformance
      manifests.py            # ManifestConformance
      dataset.py              # ReferenceDataset protocol + loader
      drivers.py              # SystemUnderTest / FaultDriver / EventTap protocols
      plugin.py               # pytest11 entry point
    registry/apis/            # committed OpenAPI specs, one dir per slug
    registry/events/          # committed AsyncAPI docs, one dir per slug
    <slug>/                   # per-sub-application suites, 9 of these
      conftest.py
      test_contract.py
      test_events.py
      test_faults.py
      test_manifests.py
      consumers/<consumer-slug>/test_expectations.py
  tests/
```

```
packages/agent-tooling/
  pyproject.toml
  src/fathom_agent_tooling/
    __init__.py
    manifest.py               # the manifest schema (03 §8.2) as Pydantic models
    eligibility.py            # the 03 §8.1 gate, read from an OpenAPI document
    generate.py               # manifest + OpenAPI -> MCP descriptors
    descriptors.py            # MCP tool-descriptor models
    overlap.py                # the 03 §8.4 proliferation control
    conftest_gen.py           # emits the per-manifest conformance test (03 §8.4)
    cli.py                    # fathom-manifest
  manifests/
    <slug>/<manifest-name>.v<major>.yaml
  generated/
    <slug>/<manifest-name>.v<major>.mcp.json   # build output, committed
  tests/
```

---

## 4. `packages/canonical-schemas`

### 4.1 Base conventions

Byte-identical wire format requires the serialization rules to be fixed in one place, not left to each model.

```python
# src/fathom_schemas/_base.py
"""Shared base class and serialization discipline for every canonical type.

Wire-format rules are fixed here, once, because document 03's substitution
protocol (§10) conformance-tests nine independent implementations against one
specification.  A per-model serialization choice is a wire-format fork.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from typing import Annotated, Any

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    PlainSerializer,
    StringConstraints,
    field_validator,
)

# --- Time -------------------------------------------------------------------
# Document 03 §4 "Time": RFC 3339 with explicit offset, UTC on the wire.
# DoD Zero Trust Overlays v1.1 (cited in 03 §5.4) set audit time-stamp
# granularity at 1 millisecond.  Fixed 6-digit microsecond precision satisfies
# that and — critically — makes the serialized form of a given instant
# byte-stable, which a variable-precision serializer does not.


def _to_utc_z(value: _dt.datetime) -> str:
    if value.tzinfo is None:                       # pragma: no cover - validator blocks
        raise ValueError("naive datetime reached serialization")
    return (
        value.astimezone(_dt.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%S.%f")
        + "Z"
    )


UtcDateTime = Annotated[AwareDatetime, PlainSerializer(_to_utc_z, return_type=str)]
"""An RFC 3339 instant.  Rejects naive datetimes; always serializes as UTC 'Z'
with 6-digit microseconds.  Document 03 §4 (Time)."""

# --- Constrained scalars ----------------------------------------------------
# Document 03 §3.3.  Every one of these is a wire-format constraint, not a
# convenience: a substituting implementation is tested against them.

Niin = Annotated[str, StringConstraints(pattern=r"^(\d{9}|[A-Z]{2}[A-Z0-9]{7})$")]
"""Document 03 §3.3 PartRef — `niin` is *the* join key for a part type.

NOT restricted to a true 9-digit National Item Identification Number.
Document 07 §4.8 documents that a real shipboard catalogue is deliberately
heterogeneous — NSN, permanent NICN, temporary NICN, LICN, and CAGE+part-number
identifiers coexist, and "almost no synthetic dataset gets this right."
Document 13's generator (Block A) correctly mints `LL`-prefixed alphanumeric
NICN/LICN identifiers per that rule, and the original 9-digit-only pattern
here rejected every one of them — the first integration run would have failed
on the catalogue itself, caught when Supply's build document tried to
consume it.

The accepted shape is therefore: 9 digits (a true NIIN, the numeric tail of an
NSN), OR two letters followed by 7 alphanumeric characters (the NICN/LICN
item-portion documented in 07 §4.8 — e.g. `LL0000123`, matching the real
example `1710 LL 0000123` there).  `niin` remains the field name everywhere in
this package and in every build document that queries `?niin=`; only the
accepted alphabet widened, so no consumer needs a rename."""

Nsn = Annotated[str, StringConstraints(pattern=r"^\d{13}$")]
"""National Stock Number.  13 digits (4-digit FSC + 9-digit NIIN).  Human
reference and external federation only; NEVER a join key.  Document 03 §3.3
rule 1."""

Uic = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9]{5,6}$")]
"""Unit Identification Code.  Document 03 §3.3: "5 characters; a 6-character
form carries a leading Service identifier, and Navy ships use R (Pacific) or
V (Atlantic) in DoDAAC contexts."  """

Eswbs = Annotated[str, StringConstraints(pattern=r"^\d{3,6}$")]
"""Expanded Ship Work Breakdown Structure code.  Human reference and external
federation only.  Document 03 §3.3 SystemRef."""

NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


# --- Base model -------------------------------------------------------------
class FathomModel(BaseModel):
    """Base for every canonical type.

    `extra="forbid"` is load-bearing rather than tidy.  It is the runtime half
    of the vocabulary enforcement in §4.4 of build document 10: a payload
    carrying `eic`, `equipment_id`, or `drivers` is rejected at parse time by
    every one of the nine services, because none of those fields exists on any
    canonical model.  See document 05 C2, C10, D23.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,                # canonical payloads are values, not buffers
        validate_assignment=True,
        populate_by_name=False,     # no aliases: one name on the wire, always
        ser_json_timedelta="float",
        str_strip_whitespace=True,
    )

    def wire_dict(self) -> dict[str, Any]:
        """The exact dict that goes on the wire.

        `exclude_none=False`: document 03 models absence as an explicit `null`
        for `rul` (§7.1) and for unset adjudication fields (§7.2).  Dropping
        nulls would make "omitted" and "null" indistinguishable to a consumer,
        and §7.1's `rul { … } | null` distinguishes them deliberately.
        """
        return self.model_dump(mode="json", by_alias=False, exclude_none=False)

    def canonical_json(self) -> bytes:
        """RFC 8785 (JCS) canonical form, for hashing, signing, and dedup.

        Document 03 §5.2 permits idempotent consumer application "on that key
        or on a content hash", and §5.4 rule 1 permits deduplication on a
        content hash.  A content hash is only stable if the JSON is
        canonicalized: key order, number formatting, and Unicode escaping all
        vary between serializers, and Python's and JavaScript's float
        repr do not agree in every case.  Never hash `wire_dict()` output
        directly.
        """
        return _jcs(self.wire_dict())

    def content_hash(self) -> str:
        """Lowercase hex SHA-256 of the JCS form.  Stable across languages."""
        return hashlib.sha256(self.canonical_json()).hexdigest()


def _jcs(value: Any) -> bytes:
    """Minimal RFC 8785 JSON Canonicalization Scheme serializer.

    Sorted keys, no insignificant whitespace, ECMAScript `Number::toString`
    number formatting, UTF-8 output, and no NaN or Infinity.  Kept in-package
    rather than taken as a dependency because `canonical-schemas` must import
    in an air-gapped Domino Job container with no wheel fetch (document 05
    D26 records that the Domino application runtime installs packages at pod
    start; this package must not rely on that).
    """
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
        default=_jcs_default,
    ).encode("utf-8")


def _jcs_default(value: Any) -> Any:  # pragma: no cover - defensive
    raise TypeError(f"non-canonicalizable value on the wire: {type(value)!r}")
```

Two rules bind every model in this package:

- **`extra="forbid"` everywhere.** Document 03 principle 5 permits additive optional fields without a version change, which appears to argue for `extra="ignore"`. It does not: the *producer* may add an optional field, and a *consumer* built against the older schema must not silently accept a field it will then not project. Forbidding extras means the consumer's read-model gap becomes a loud parse failure at the version boundary rather than a silent data loss, and the schema-registry compatibility gate (§7) is what makes the additive change safe. This is the one place where this package is deliberately stricter than a naive reading of document 03, and it is called out here so no implementer relaxes it.
- **`frozen=True`.** Canonical payloads are values. A consumer that mutates a received `FailurePrediction` in place and re-publishes it has laundered provenance.

### 4.2 Sub-application slugs — document 03 §3.1

Document 03 §3.1 gives one canonical slug per sub-application, *"used without variation in topic names, event `producer` fields, `target_sub_app` values, API base paths, conformance directories, and manifest directories `[C27, C28]`."* Finding C27 is precisely that no canonical identifier existed while four schemes referenced one.

```python
# src/fathom_schemas/slugs.py
"""Canonical sub-application and platform-service slugs.

Document 03 §3.1.  Closes review finding C27 ("No canonical sub-application
identifier is ever defined, though four schemes reference one") and C28
(display names vary across and within documents).

The slug is the ONLY identifier for a sub-application on any wire.  Document
05 C9 records three mutually incompatible integer identities for these same
nine sub-applications; there is deliberately no integer here.
"""
from __future__ import annotations

from enum import StrEnum


class SubAppSlug(StrEnum):
    """The nine sub-applications.  Document 03 §3.1, table rows 1-9."""

    REGISTRY = "registry"                  # Asset & Configuration Registry
    TELEMETRY = "telemetry"                # Condition & Telemetry
    PDM = "pdm"                            # Predictive Maintenance
    FLEET_STATUS = "fleet-status"          # Fleet Status & Readiness
    MAINTENANCE = "maintenance"            # Maintenance Execution & Scheduling
    SUPPLY = "supply"                      # Supply Chain & Inventory
    PMA = "pma"                            # Post-Mission Analysis
    FAILURE_INTEL = "failure-intel"        # Failure Intelligence
    DESIGN_ADVISORY = "design-advisory"    # System Test & Design Advisory

    @property
    def canonical_name(self) -> str:
        """The canonical name from document 03 §3.1 column 1."""
        return _CANONICAL_NAME[self]

    @property
    def display_abbreviation(self) -> str:
        """The display abbreviation from document 03 §3.1 column 3.

        This is the ONLY string permitted in a user interface for this
        sub-application.  Document 05 C28: seven of nine had two or more
        spellings.
        """
        return _DISPLAY[self]

    @property
    def api_base_path_template(self) -> str:
        """Document 03 §4: `/api/v{major}/{sub-application-slug}/…`  [C25]."""
        return f"/api/v{{major}}/{self.value}/"

    def api_base_path(self, major: int) -> str:
        if major < 1:
            raise ValueError("API major version starts at 1")
        return f"/api/v{major}/{self.value}"


class PlatformServiceSlug(StrEnum):
    """Platform services.  Document 03 §3.1 final paragraph.

    Enumerated exactly as document 03 lists them.  Document 05 C14 records
    three mutually inconsistent platform-service inventories across documents
    01, 02, and 04; document 03 §3.1 is the reconciling authority for the
    *slug*, and this enum is its transcription.
    """

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
```

> **Directory-name deviation, flagged for reconciliation.** Document 01 §11's monorepo layout lists `services/asset-registry`, but document 03 §3.1's slug for that sub-application is `registry`. That is the residue of C27 in document 01 (remediation tranche 2, not yet applied). **This package treats `registry` as authoritative** because document 03 is binding, and `fathom-contracts validate-layout` (§9.4) fails the build if a directory under `services/` is not exactly a `SubAppSlug` value. Document 01's layout requires a tranche-2 correction to `services/registry`. Recorded as OQ-11 in §11.

### 4.3 Identity references — document 03 §3.3

```python
# src/fathom_schemas/identity.py
"""Canonical identity references.  Document 03 §3.3, transcribed exactly.

Four rules from §3.3 govern every type in this module:

1. `asset_id`, `system_id`, `position_id`, `installed_item_id`, and `niin` are
   THE join keys.  `hull_or_tail`, `eswbs`, `position_code`, and `nsn` are
   carried for human reference and for federation with external systems, and
   are never used as join keys internally, because external systems reissue
   and reformat them.
2. EIC is never a join key.  NAVSEAINST 4790.8 Appendix A defines it as a
   7-character code whose leading positions identify system, subsystem, and
   equipment category — a CLASS CODE OF VARIABLE SPECIFICITY, not an instance
   identifier.  See §4.4 of build document 10 for how this is enforced.  `eic`
   is declared on `SystemRef` and `InstalledItemRef` below, closing OQ-1 (§3.3
   now states the field rather than leaving it implicit in prose only).
3. A payload identifying a physical item identifies it as `installed_item_id`.
   A payload identifying a location identifies it as `position_id`.  The
   distinction is load-bearing: remaining useful life, usage accumulation, and
   failure history attach to the installed item.  Conflating the two produces
   the inherited-degradation failure document 04 §2 exists to prevent [C10].
4. A NIIN alone is a part type, not an installed item.

Review findings closed here: C10 (no canonical identifier existed for
InstalledItem), C31 (none existed for the System level), D9 (monotonic-max
counters reintroduced inherited degradation), D35 (equipment family defined
nowhere).
"""
from __future__ import annotations

import re
from enum import StrEnum
from uuid import UUID

from pydantic import Field, field_validator

from ._base import Eswbs, FathomModel, Niin, NonEmptyStr, Nsn, Uic, UtcDateTime


CANONICAL_JOIN_KEYS: frozenset[str] = frozenset(
    {"asset_id", "system_id", "position_id", "installed_item_id", "niin"}
)
"""Document 03 §3.3 rule 1, verbatim: "`asset_id`, `system_id`, `position_id`,
`installed_item_id`, and `niin` are the join keys."

Declared here, in the package every service imports, and MIRRORED by the lint
rule set in `lint/fathom_vocab/rules.py` (the plugin cannot import the runtime
package, because flake8 loads it outside the service's environment).  A test in
`tests/test_lint_rules.py` asserts the two definitions are identical, so the
mirror cannot drift."""

HUMAN_REFERENCE_ONLY: frozenset[str] = frozenset(
    {"hull_or_tail", "eswbs", "position_code", "nsn", "eic"}
)
"""Document 03 §3.3 rule 1: carried "for human reference and for federation with
external systems, and are never used as join keys internally, because external
systems reissue and reformat them."  `eic` is included per rule 2, now declared
on `SystemRef` and `InstalledItemRef` (OQ-1 resolved)."""


class AssetDomain(StrEnum):
    """Document 03 §3.3 AssetRef.domain: surface | subsurface | unmanned."""

    SURFACE = "surface"
    SUBSURFACE = "subsurface"
    UNMANNED = "unmanned"


_HULL_OR_TAIL = re.compile(r"^(T-)?[A-Z]{2,5} \d{1,4}[A-Z]?$")
"""SECNAVINST 5030.8D Enclosure 6, quoted in document 03 §3.3: "Hyphens will
not be used in the hull number of any ship or craft."  A SPACE separates the
type designation from the number.  The one sanctioned hyphen is the leading
`T-` denoting Military Sealift Command.  A trailing letter accommodates the
trailing N denoting nuclear propulsion (e.g. "CVN 68" is already covered by
the type designation; "SSN 796" likewise)."""


class AssetRef(FathomModel):
    """Document 03 §3.3 `AssetRef`.

    Transcribed field-for-field.  Every comment in §3.3 is preserved as a
    field description because those comments are normative: they carry the
    external authorities (SECNAVINST 5030.8D, DoDAAC conventions) that make
    the constraint non-negotiable.
    """

    asset_id: UUID = Field(
        description="Stable internal UUID; THE join key.  Document 03 §3.3."
    )
    hull_or_tail: NonEmptyStr = Field(
        description=(
            '"DDG 113", "SSN 796", "MQ-25 004" — human reference only.  SPACE, '
            "never a hyphen: SECNAVINST 5030.8D Enclosure 6 states \"Hyphens "
            "will not be used in the hull number of any ship or craft.\"  "
            "Trailing N denotes nuclear propulsion; a leading \"T-\" denotes "
            "Military Sealift Command.  NEVER a join key (§3.3 rule 1)."
        )
    )
    uic: Uic = Field(
        description=(
            "Unit Identification Code.  5 characters; a 6-character form "
            "carries a leading Service identifier, and Navy ships use R "
            "(Pacific) or V (Atlantic) in DoDAAC contexts."
        )
    )
    class_id: NonEmptyStr = Field(
        description=(
            "Class designation.  The Navy expresses ship class as the LEAD "
            "HULL NUMBER (68 for NIMITZ, 51 for ARLEIGH BURKE), so the "
            "internal identifier carries both that and the flight or block "
            '(e.g. "DDG-51-FLTIIA", "SSN-774-BLKIV").'
        )
    )
    domain: AssetDomain = Field(
        description="surface | subsurface | unmanned.  Document 03 §3.3."
    )

    @field_validator("hull_or_tail")
    @classmethod
    def _no_hyphen_in_hull(cls, value: str) -> str:
        body = value[2:] if value.startswith("T-") else value
        if "-" in body:
            raise ValueError(
                "hull_or_tail uses a SPACE, never a hyphen (SECNAVINST 5030.8D "
                "Encl 6, quoted in document 03 §3.3); the only sanctioned "
                f"hyphen is a leading 'T-' for Military Sealift Command: {value!r}"
            )
        if not _HULL_OR_TAIL.match(value):
            raise ValueError(
                "hull_or_tail must be '<TYPE> <NUMBER>', optionally prefixed "
                f"'T-': got {value!r}"
            )
        return value


class SystemRef(FathomModel):
    """Document 03 §3.3 `SystemRef`  [C31].

    Closes C31: "No canonical identifier exists for the System level, though
    readiness is scoped to it."  Fleet Status scopes readiness rollups to a
    system, so the system needs a join key of its own; `eswbs` is not it.
    """

    system_id: UUID = Field(
        description="Stable internal UUID; THE join key.  Document 03 §3.3."
    )
    eswbs: Eswbs = Field(
        description=(
            "ESWBS code — human reference and external federation ONLY.  Never "
            "a join key (§3.3 rule 1).  An ESWBS-aligned grouping within an "
            'asset is a "system"; "subsystem" and "group" are losing variants '
            "(§3.2)."
        )
    )
    eic: NonEmptyStr | None = Field(
        default=None,
        description=(
            "Equipment Identification Code of the system, WHERE IT HAS ONE.  "
            "Federation and human reference only — never a join key, and never "
            "of more than four-digit specificity per NAVSEAINST 4790.8 "
            "Appendix A: 'Where the EIC is known to more than four digits, it "
            "should be recorded at that level.'  Document 03 §3.3 (added same "
            "session as this package, after this field was first omitted)."
        ),
    )


class PositionRef(FathomModel):
    """Document 03 §3.3 `PositionRef`.

    A named PERSISTENT installation location.  Positions outlive the items
    installed in them (document 01 §6).  "slot" and "location" are losing
    variants (document 03 §3.2).
    """

    position_id: UUID = Field(
        description="Stable internal UUID; THE join key.  Document 03 §3.3."
    )
    position_code: NonEmptyStr = Field(
        description='"233-04-A" — human reference only.  Never a join key.'
    )
    system_id: UUID = Field(
        description="The parent system.  Document 03 §3.3 PositionRef.system_id."
    )


class InstalledItemRef(FathomModel):
    """Document 03 §3.3 `InstalledItemRef`  [C10, D9].

    Identifies the PHYSICAL ITEM occupying a position — not the position, and
    not the part type.  This type closes C10, the finding that "No canonical
    identifier exists for `InstalledItem`, defeating document 04's most
    consequential modeling decision", where "It is undefined whether
    `equipment_id` identifies the position-bound slot or the physical item."

    There is deliberately no field named `equipment_id` anywhere in this
    package.  See §10 of build document 10.
    """

    installed_item_id: UUID = Field(
        description=(
            "Stable internal UUID; THE join key.  Identifies the PHYSICAL "
            "ITEM.  Document 03 §3.3."
        )
    )
    eic: NonEmptyStr | None = Field(
        default=None,
        description=(
            "Equipment Identification Code of the CLASS this item instantiates, "
            "WHERE IT HAS ONE.  Federation and human reference only — never a "
            "join key.  Document 03 §3.3."
        ),
    )
    iuid: NonEmptyStr | None = Field(
        default=None,
        description=(
            "Item Unique Identification per DoDI 8320.04, WHERE ASSIGNED.  "
            "DoDI 4151.22 §1.2.d and §1.2.l require serialized item management "
            'and IUID "to optimize RCM and CBM+ data analytics", so this is '
            "the externally mandated instance identity — not the EIC.  "
            "Optional because §3.3 says 'where assigned'."
        ),
    )
    position_id: UUID = Field(description="Where it is installed.  Document 03 §3.3.")
    niin: Niin = Field(description="What it is.  Document 03 §3.3.")
    serial_or_lot: NonEmptyStr | None = Field(
        default=None,
        description="Where tracked.  Optional because §3.3 says 'where tracked'.",
    )
    installed_at: UtcDateTime = Field(description="Document 03 §3.3.")

    provisional: bool = Field(
        default=False,
        description=(
            "Provisional installed-item identity.  Document 03 §3.3 final "
            "paragraph: an edge deployment may mint an `installed_item_id` "
            "locally as a client-generated UUID with `provisional: true`; the "
            "Registry confirms or supersedes it on reconciliation.  Without "
            "this, a ship that replaces an item at sea cannot attribute usage "
            "or maintenance to the correct physical item  [D9, D8]."
        ),
    )


class PartRef(FathomModel):
    """Document 03 §3.3 `PartRef`.

    A part TYPE in the catalog.  "component" and "item" are losing variants
    (§3.2).  A NIIN alone is a part type, not an installed item (§3.3 rule 4).
    """

    niin: Niin = Field(
        description=(
            "National Item Identification Number; THE join key.  Document 03 "
            "§3.3."
        )
    )
    nsn: Nsn | None = Field(
        default=None,
        description=(
            "Full National Stock Number where known.  Human reference and "
            "federation only; never a join key (§3.3 rule 1)."
        ),
    )
    apl: NonEmptyStr | None = Field(
        default=None, description="Allowance Parts List reference.  Document 03 §3.3."
    )
    equipment_family: NonEmptyStr = Field(
        description=(
            "Canonical grouping for model binding and calibration  [D35].  "
            "Document 03 §3.3: `equipment_family` partitions model bindings, "
            "calibration records, and reference classes.  It is defined and "
            "served by Reference Data, is versioned, and is a REQUIRED "
            "attribute of every part.  Document 03 §14 repeats the ownership."
        )
    )
```

Note what is **not** here, deliberately:

- **`eic` is declared on `SystemRef` and `InstalledItemRef`, not on `PartRef`.** OQ-1's original gap — document 03 §3.3's rule 2 prose named the two carrier types without either schema block declaring the field — is closed; both blocks now declare `eic: NonEmptyStr | None`. Its absence from `PartRef` is not a gap: EIC identifies equipment, not a part type, and the field simply does not apply here. The lint rule `FTH001` (§4.4) still catches `eic` as a join key wherever it appears.
- No `asset_id` on `SystemRef`, and no `asset_id` on `PositionRef`. Document 03 §3.3 does not denormalize the parent chain beyond `PositionRef.system_id`. Flagged as OQ-2.

### 4.4 Enforcing the domain vocabulary — document 03 §3.2

Document 03 §3.2 gives a canonical-term table and states: *"One term per concept. Losing variants are not to be used in any document or identifier `[C29]`."* Finding C29 records six labels for the component level, three for mission, three for position, and two unrelated meanings for "Endpoint".

The task brief asks for one enforcement mechanism, chosen and justified. **Chosen: a static AST lint rule set, shipped as a flake8 plugin inside `packages/canonical-schemas/lint/`, run in CI and pre-commit, backed by the runtime `extra="forbid"` property of §4.1.**

#### Why a static rule and not the alternatives

| Candidate | Rejected because |
|---|---|
| **Code-review checklist item** | The nine sub-applications are built by *separate coding agents from separate documents*. There is no shared reviewer with the vocabulary table in working memory across nine parallel workstreams. A checklist is exactly the control that C29 already defeated once — the losing variants are in the approved architecture documents, which were reviewed. |
| **Runtime assertion alone** | The defect C2/C10 describes lives in a **join**, not in a payload: `01 §7`'s use of `eic` as a join key. A join is written in SQL, in a SQLAlchemy `join()` clause, or in a pandas `merge(on=...)`. No runtime model validator can see it, because by then `eic` is a column in the producer's private database — which document 03 principle 1 explicitly permits ("Database schemas … are private to a sub-application"). The defect is in the *code*, and only a code checker sees it. |
| **A custom Ruff rule** | Ruff has no third-party plugin API. Vendoring a rule into Ruff is not available to this program. |
| **Naming-convention prose in document 09** | Necessary but not sufficient; it produces the same outcome as the checklist. Document 09 carries the table; this package carries the gate. |

Ruff remains the formatter and general linter for the monorepo per document 09. Flake8 is added **solely** to host the `FTH` rules and is invoked with `--select=FTH` only, so there is no overlapping or duplicated rule set and no second opinion about import order or line length.

#### The rule set

```python
# lint/fathom_vocab/rules.py
"""The FTH rule set: document 03 §3.2 vocabulary and §3.3 join-key discipline,
enforced statically.

Each rule cites the document 03 section it enforces and the review finding it
prevents from recurring.  A rule is only added here if a violation is a defect
in document 03's terms — this is not a style plugin.
"""
from __future__ import annotations

# --- FTH001: non-canonical join key ---------------------------------------
JOIN_FORBIDDEN = {
    "eic": "document 03 §3.3 rule 2 — EIC is a class code of variable "
           "specificity (NAVSEAINST 4790.8 App. A), never an instance "
           "identifier.  Review finding C2.",
    "hull_or_tail": "document 03 §3.3 rule 1 — human reference only.",
    "eswbs": "document 03 §3.3 rule 1 — human reference and federation only.",
    "position_code": "document 03 §3.3 rule 1 — human reference only.",
    "nsn": "document 03 §3.3 rule 1 — human reference only; join on `niin`.",
    "equipment_id": "document 03 §3.3 rule 3 — ambiguous between position and "
                    "physical item.  Use `installed_item_id` for the physical "
                    "item or `position_id` for the location.  Review finding C10.",
}
JOIN_CONTEXTS = (
    # SQLAlchemy / SQLModel
    "join", "outerjoin", "join_from", "relationship", "foreign", "ForeignKey",
    # pandas / polars
    "merge", "join_asof", "merge_asof", "set_index", "groupby", "group_by",
    # explicit dict/index keying
    "index_by", "key_by",
)
CANONICAL_JOIN_KEYS = frozenset(
    {"asset_id", "system_id", "position_id", "installed_item_id", "niin"}
)
"""Mirrors `fathom_schemas.identity.CANONICAL_JOIN_KEYS`.  The duplication is
deliberate — flake8 loads this plugin outside the service's environment, so it
cannot import the runtime package — and `tests/test_lint_rules.py` asserts the
two are identical."""

# --- FTH002: losing vocabulary term as an identifier ----------------------
# Document 03 §3.2, column "Not".  Checked against attribute names, class
# names, function names, Pydantic field names, and string literals used as
# dict keys — not against comments or docstrings, where the losing term may
# legitimately appear in an explanation of why it is losing.
LOSING_TERMS = {
    # concept: (losing variants, canonical term, note)
    "installed item": (
        ("equipment", "component", "part_instance", "partinstance"),
        "installed_item",
        "document 03 §3.2 row 1; review finding C29 (six labels for this level)",
    ),
    "position": (("slot", "location_code"), "position", "document 03 §3.2 row 2"),
    "system": (("subsystem", "equipment_group"), "system", "document 03 §3.2 row 3"),
    "part": (("component_type", "catalog_item"), "part", "document 03 §3.2 row 4"),
    "mission": (
        ("mission_event", "mission_record"),
        "mission",
        "document 03 §3.2 row 5",
    ),
    "sub-application": (
        ("sub_app", "subapp", "microservice"),
        "sub_application",
        "document 03 §3.2 row 6.  NOTE the sanctioned exception below.",
    ),
    "Domino Endpoint": (
        ("endpoint",),
        "domino_endpoint",
        "document 03 §3.2 rows 7-8.  'Endpoint' carries two unrelated meanings "
        "(review finding C29); an HTTP route is an OPERATION, and a Domino "
        "inference deployment is a Domino Endpoint, always qualified.",
    ),
    "operation": (
        ("route", "http_endpoint", "api_endpoint"),
        "operation",
        "document 03 §3.2 row 8",
    ),
}
# Sanctioned exception, enumerated rather than inferred:
# `target_sub_app` is the canonical Proposal field name in document 03 §7.2 and
# is therefore ALLOWED despite matching the `sub_app` losing variant.  The rule
# allowlists the exact identifier `target_sub_app` and nothing else.
FTH002_ALLOWLIST = frozenset({"target_sub_app"})

# --- FTH003: `drivers` as a field or attribute name ----------------------
FTH003_MESSAGE = (
    "`drivers` was renamed to `contributing_factors` (document 03 §7.1, review "
    "finding D23).  D23: at tier 2, attributions over correlated channels are "
    "unidentified and reorder run to run; at tier 3 the field reads as causal "
    "and delivers unadjudicated causal claims to the deckplate.  The rename is "
    "not cosmetic — `contributing_factors` additionally REQUIRES "
    "`attribution_method` and `stability`.  Do not rename it back."
)

# --- FTH004: wall-clock arbitration --------------------------------------
FTH004_TIME_FIELDS = frozenset(
    {"source_time", "occurred_at", "recorded_at", "ingest_time", "computed_at"}
)
FTH004_ORDERING_CONTEXTS = ("sort", "sorted", "max", "min", "order_by", "nlargest")
FTH004_MESSAGE = (
    "wall-clock arbitration of ordering or merge.  Document 03 §5.4: 'No wall "
    "clock ever arbitrates a merge.'  Ubuntu 22.04 STIG V-260520 mandates "
    "`makestep 1 -1` — unlimited backward steps — which fires precisely when a "
    "disconnected node reconnects and drains its outbox.  Order and deduplicate "
    "on `(producer.slug, clock.monotonic_seq)` or on `clock.hlc`.  Review "
    "finding D29."
)

# --- FTH005: retired CUI markings ----------------------------------------
FTH005_RETIRED = ("FOUO", "U//FOUO")
FTH005_MESSAGE = (
    '"FOUO" and "U//FOUO" are RETIRED markings (DoDI 5200.48 §3.4.b, cited in '
    "document 03 §7.3).  Minimum marking is `CUI` in both banner and footer.  "
    "Use `ClassificationLabel.level = CUI` with `cui_categories[]`, and a "
    "`DisseminationControl` from the ten authorized LDCs."
)

# --- FTH006: branching on `tier` -----------------------------------------
FTH006_MESSAGE = (
    "consumer branches on `tier`.  Document 03 §7.1: 'Tier invariance survives "
    "as SHAPE invariance: consumers must not branch on `tier`.  They may, and "
    "must, branch on `reference_class`.'  `tier` is present for transparency "
    "only.  Review findings D7, D19, D36.  If this module is inside "
    "`services/pdm/` — which OWNS tier assignment — add it to the "
    "`per-file-ignores` for FTH006 with a comment naming the operation."
)
```

```python
# lint/fathom_vocab/checker.py
"""flake8 plugin entry point for the FTH rule set.

Registered in packages/canonical-schemas/pyproject.toml:

    [project.entry-points."flake8.extension"]
    FTH = "fathom_vocab.checker:FathomVocabularyChecker"

Invoked in CI and pre-commit as:

    flake8 --select=FTH --extend-exclude=".venv,node_modules" .

Ruff continues to own every other lint concern (document 09).  Flake8 is
invoked with --select=FTH ONLY, so no rule is expressed twice and there is no
second opinion about formatting.
"""
from __future__ import annotations

import ast
from typing import Iterator

from . import rules

Violation = tuple[int, int, str, type]


class FathomVocabularyChecker:
    name = "fathom-vocab"
    version = "2.0.0"

    def __init__(self, tree: ast.AST, filename: str = "(none)") -> None:
        self._tree = tree
        self._filename = filename

    def run(self) -> Iterator[Violation]:
        visitor = _Visitor(self._filename)
        visitor.visit(self._tree)
        yield from visitor.violations


class _Visitor(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: list[Violation] = []

    # -- FTH001 / FTH004 : call-site rules ------------------------------
    def visit_Call(self, node: ast.Call) -> None:
        func = _dotted_name(node.func)
        leaf = func.rsplit(".", 1)[-1] if func else ""

        if leaf in rules.JOIN_CONTEXTS:
            for name in _identifiers_in(node):
                if name in rules.JOIN_FORBIDDEN:
                    self._add(
                        node,
                        "FTH001",
                        f"`{name}` used as a join key in `{leaf}(...)`: "
                        f"{rules.JOIN_FORBIDDEN[name]}  Join on one of "
                        f"{sorted(rules.CANONICAL_JOIN_KEYS)}.",
                    )

        if leaf in rules.FTH004_ORDERING_CONTEXTS:
            for name in _identifiers_in(node):
                if name in rules.FTH004_TIME_FIELDS:
                    self._add(node, "FTH004", f"`{name}` — {rules.FTH004_MESSAGE}")

        self.generic_visit(node)

    # -- FTH001 : raw SQL ----------------------------------------------
    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            text = node.value
            upper = text.upper()
            if " JOIN " in upper or upper.lstrip().startswith("SELECT"):
                lowered = text.lower()
                for name in rules.JOIN_FORBIDDEN:
                    if f"on {name}" in lowered or f".{name} =" in lowered:
                        self._add(
                            node,
                            "FTH001",
                            f"`{name}` used as a join key in embedded SQL: "
                            f"{rules.JOIN_FORBIDDEN[name]}",
                        )
            for retired in rules.FTH005_RETIRED:
                if retired in text:
                    self._add(node, "FTH005", rules.FTH005_MESSAGE)
        self.generic_visit(node)

    # -- FTH002 / FTH003 : declaration-site rules ----------------------
    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name):
            self._check_declared_name(node, node.target.id)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        self._check_declared_name(node, node.arg)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._check_declared_name(node, node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_declared_name(node, node.name)
        self.generic_visit(node)

    # -- FTH006 : branching on tier ------------------------------------
    def visit_If(self, node: ast.If) -> None:
        for name in _identifiers_in(node.test):
            if name == "tier":
                self._add(node, "FTH006", rules.FTH006_MESSAGE)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        for name in _identifiers_in(node.subject):
            if name == "tier":
                self._add(node, "FTH006", rules.FTH006_MESSAGE)
        self.generic_visit(node)

    # -- helpers --------------------------------------------------------
    def _check_declared_name(self, node: ast.AST, name: str) -> None:
        if name in rules.FTH002_ALLOWLIST:
            return
        lowered = name.lower()
        if lowered == "drivers" or lowered.endswith("_drivers"):
            self._add(node, "FTH003", rules.FTH003_MESSAGE)
        for concept, (losing, canonical, note) in rules.LOSING_TERMS.items():
            for variant in losing:
                if lowered == variant or lowered.startswith(f"{variant}_") \
                        or lowered.endswith(f"_{variant}"):
                    self._add(
                        node,
                        "FTH002",
                        f"`{name}` uses the losing variant `{variant}` for the "
                        f"concept '{concept}'.  Canonical term: `{canonical}`.  "
                        f"{note}.",
                    )

    def _add(self, node: ast.AST, code: str, message: str) -> None:
        self.violations.append(
            (
                getattr(node, "lineno", 1),
                getattr(node, "col_offset", 0),
                f"{code} {message}",
                FathomVocabularyChecker,
            )
        )


def _dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_dotted_name(node.value)}.{node.attr}"
    return ""


def _identifiers_in(node: ast.AST) -> set[str]:
    """Every bare name, attribute leaf, and string constant under `node`."""
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            found.add(child.id)
        elif isinstance(child, ast.Attribute):
            found.add(child.attr)
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            found.add(child.value)
        elif isinstance(child, ast.keyword) and child.arg:
            found.add(child.arg)
    return found
```

#### The three enforcement layers, and what each catches

| Layer | Mechanism | Catches | Cannot catch |
|---|---|---|---|
| **Static (primary)** | `flake8 --select=FTH` in pre-commit and CI, blocking | `eic` in a join clause, in embedded SQL, or in a `merge(on=…)`; `equipment_id` anywhere; `drivers` as a field name; wall-clock sort keys; `FOUO` literals; `if pred.tier == 3` | dynamically-constructed column names; a join expressed in a stored procedure or a dbt model |
| **Runtime (backstop)** | `FathomModel.model_config["extra"] = "forbid"` (§4.1) | any *payload* carrying `eic`, `equipment_id`, or `drivers` crossing a sub-application boundary — rejected at parse time in all nine services | anything inside a service's private database |
| **Conformance (external)** | `ContractConformance` asserts every identifier in a required response is a canonical join key (§6.4) | a substituting partner implementation exposing a non-canonical identifier — the case no in-repo lint can reach | — |

Document 09 carries the §3.2 table as prose for human readers; **this section is the gate.** A `# noqa: FTH001` is permitted only with an adjacent comment naming the document 03 section that sanctions the exception, and `tools/check_noqa_justified.py` (a sibling of the existing `tools/check_event_catalog.py`) fails CI on a bare `noqa` of any `FTH` code.

### 4.5 The event envelope and the clock — document 03 §5.4

Document 03 §5.4 presents the envelope as one code block and then introduces `clock` separately with *"Every event therefore carries:"*. **`clock` is a required top-level member of the envelope**, not a separate structure; the two blocks are merged here and the split is flagged as OQ-3 (§11) for an editorial correction to document 03.

```python
# src/fathom_schemas/envelope.py
"""The event envelope.  Document 03 §5.4, transcribed exactly.

Two document 03 blocks are merged here: the `EventEnvelope` block and the
`clock {}` block that §5.4 introduces immediately afterwards with "Every event
therefore carries:".  See OQ-3.

Review findings closed: C11 (the envelope made `asset_id` mandatory while ~nine
catalogued events have no asset scope), C26 (event names inconsistently
qualified and cased), D3/D4 (baseline fencing and the antecedent rule), D29 (no
time-synchronization design), D30 (replay through the bus fires live side
effects).
"""
from __future__ import annotations

import re
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from ._base import FathomModel, Niin, NonEmptyStr, UtcDateTime
from .classification import ClassificationLabel
from .slugs import AnySlug


class EventScope(StrEnum):
    """Document 03 §5.4 `scope`  [C11].

    "asset | system | installed_item | niin | class | mission | tycom | fleet"

    C11: the rev-1 envelope made `asset_id` mandatory, but roughly nine
    catalogued events have no asset scope — `part_availability.changed` is
    NIIN-and-location scoped, `criticality_tier.assigned` is NIIN-and-family
    scoped, `readiness.recomputed` may be fleet scoped.  Declaring the scope
    and requiring exactly one matching identifier is the fix.

    `MISSION` and the `FLEET` exception below were added to document 03 in
    the same session that closed OQ-4 (previously: `mission_id` existed in
    `subject` with no selecting scope value, and `fleet` had no identifier at
    all).  Both are resolved, not open, as of this revision of this package.

    `TYCOM` was added when Fleet Status's build framework (document 27) flagged
    that its `GET /readiness?scope=fleet|tycom|asset` and its `readiness.recomputed`
    event both need a middle echelon between `asset` and `fleet` — Type
    Commander, an administrative Navy rollup, not an equipment class, so
    `CLASS` does not fit it.
    """

    ASSET = "asset"
    SYSTEM = "system"
    INSTALLED_ITEM = "installed_item"
    NIIN = "niin"
    CLASS = "class"
    MISSION = "mission"
    TYCOM = "tycom"
    FLEET = "fleet"


class EventSubject(FathomModel):
    """Document 03 §5.4 `subject {}`.

    "exactly one scope identifier required, matching `scope`, EXCEPT
    scope=fleet, which requires none — fleet is the one singleton scope
    covering the entire fleet rather than one member of it."  Every field is
    optional individually; the cross-field rule is enforced on the envelope,
    because only the envelope knows the declared `scope`.
    """

    asset_id: UUID | None = None
    system_id: UUID | None = None
    installed_item_id: UUID | None = None
    niin: Niin | None = None
    class_id: NonEmptyStr | None = None
    mission_id: UUID | None = None
    tycom_id: NonEmptyStr | None = None


SCOPE_SUBJECT_FIELD: dict[EventScope, str | None] = {
    EventScope.ASSET: "asset_id",
    EventScope.SYSTEM: "system_id",
    EventScope.INSTALLED_ITEM: "installed_item_id",
    EventScope.NIIN: "niin",
    EventScope.CLASS: "class_id",
    EventScope.MISSION: "mission_id",
    EventScope.TYCOM: "tycom_id",
    EventScope.FLEET: None,   # the sole documented exception — see EventSubject's docstring
}
"""Maps each `EventScope` to the `subject` field that must be populated.

`FLEET` maps to None by design, not by gap: document 03 §5.4 states the
fleet-scope exception explicitly.  A fleet-scoped event carries an EMPTY
subject.

`MISSION` maps to `mission_id`, closing the OQ-4 gap in which `mission_id`
existed in `subject` with no scope value that selected it — `mission.completed`
and the `mission_review.*` events are scope=mission, not scope=asset with
`mission_id` merely carried in the payload.

`TYCOM` maps to `tycom_id`, closing Fleet Status's OD-2 — a real gap, not a
naming variant of `class`: TYCOM is where a ship's chain of command sits
administratively, orthogonal to what equipment class it operates.
"""


class TimeSource(StrEnum):
    """Document 03 §5.4 `clock.sync_quality.time_source`.

    "gnss | usno_authenticated | upstream_ntp | holdover | unsynced"
    """

    GNSS = "gnss"
    USNO_AUTHENTICATED = "usno_authenticated"
    UPSTREAM_NTP = "upstream_ntp"
    HOLDOVER = "holdover"
    UNSYNCED = "unsynced"


class SyncQuality(FathomModel):
    """Document 03 §5.4 `clock.sync_quality {}`.

    "the attestation that makes skew auditable rather than invisible".

    Document 03 §5.4 rule 4: `sync_quality` is RETAINED PERMANENTLY.  "It
    converts 'our timestamps drifted' from an audit finding into a bounded,
    documented condition, and it is the only way to re-derive true ordering
    after the fact.  Without it that information is gone.  Skew is
    indistinguishable from tampering to an assessor, and non-repudiation claims
    collapse if the time is contestable."
    """

    time_source: TimeSource = Field(description="Document 03 §5.4.")
    offset_ms: float = Field(description="Last measured offset.  Document 03 §5.4.")
    dispersion_ms: float = Field(
        ge=0.0,
        description=(
            "Accumulated uncertainty — THE PUBLISHED EPSILON.  Document 03 §5.4 "
            "rule 3: it grows while disconnected, and the application BRANCHES "
            "ON IT.  Small epsilon permits wall-clock-assisted presentation; "
            "epsilon exceeding the inter-write interval forces causal-only "
            "ordering and forbids any timestamp arbitration."
        ),
    )
    seconds_since_sync: float = Field(ge=0.0, description="Document 03 §5.4.")
    step_occurred: bool = Field(
        description=(
            "True if a backward step landed since the last record.  Ubuntu "
            "22.04 STIG V-260520 mandates `makestep 1 -1` — unlimited backward "
            "clock steps whenever the offset exceeds one second — and that step "
            "fires precisely when a disconnected node reconnects and begins "
            "draining its outbox.  Document 03 §5.4  [D29]."
        )
    )


class HybridLogicalClock(FathomModel):
    """Document 03 §5.4 `clock.hlc`: "hybrid logical clock: (physical, logical,
    node_id)".  Transcribed as a three-member structure."""

    physical: int = Field(
        ge=0, description="Physical component, milliseconds since epoch."
    )
    logical: int = Field(ge=0, description="Logical counter within `physical`.")
    node_id: NonEmptyStr = Field(description="Producing node identity.")

    def __lt__(self, other: "HybridLogicalClock") -> bool:
        """Lexicographic (physical, logical, node_id) — the HLC ordering.

        Provided so consumers can order on the HLC without reimplementing the
        comparison, which document 03 §5.4 rule 1 permits as an alternative to
        `(producer, monotonic_seq)`.
        """
        return (self.physical, self.logical, self.node_id) < (
            other.physical,
            other.logical,
            other.node_id,
        )


class Clock(FathomModel):
    """Document 03 §5.4 `clock {}`, transcribed exactly.

    §5.4: "Clock discipline.  NO WALL CLOCK EVER ARBITRATES A MERGE."  This is
    "stronger than a caution, and the reason is a mandated STIG behavior rather
    than a hypothetical" — Ubuntu 22.04 STIG V-260520.  "Compliance guarantees a
    non-monotonic clock at exactly the moment ordering matters most."

    The four rules that follow in §5.4:

    1. Ordering and deduplication use `(producer, monotonic_seq)` or the HLC.
       NEVER `source_time`.  Consumers apply idempotently on that key or on a
       content hash (see `FathomModel.content_hash`).
    2. Durations, timeouts, retry backoff, and lease expiry use a monotonic
       clock, never the wall clock.
    3. `dispersion_ms` is a published epsilon that grows while disconnected,
       and the application branches on it.
    4. `sync_quality` is retained permanently.
    """

    monotonic_seq: int = Field(
        ge=0,
        description=(
            "Per-producer monotonically increasing sequence.  THE ORDERING KEY.  "
            "Document 03 §5.4.  See OQ-5: §5.4 does not state whether 'per "
            "producer' means per slug or per process instance."
        ),
    )
    hlc: HybridLogicalClock = Field(description="Document 03 §5.4.")
    source_time: UtcDateTime = Field(
        description=(
            "Producing node's wall clock at the domain event.  NEVER an "
            "ordering or merge key (§5.4 rule 1; §11 'No policy below compares "
            "wall-clock timestamps across nodes')."
        )
    )
    ingest_time: UtcDateTime = Field(
        description="Receiving node's wall clock at acceptance.  Document 03 §5.4."
    )
    sync_quality: SyncQuality = Field(description="Document 03 §5.4.")


EVENT_TYPE_RE = re.compile(
    r"^fathom\.(?P<slug>[a-z][a-z0-9-]*)\.(?P<aggregate>[a-z][a-z0-9_]*)"
    r"\.(?P<verb>[a-z][a-z0-9_]*)$"
)
"""Document 03 §5.4: `event_type` is "fathom.<slug>.<aggregate>.<verb>" —
snake_case throughout  [C26].

The slug token permits a hyphen because §3.1's slugs include `fleet-status`,
`failure-intel`, and `design-advisory`; the aggregate and verb tokens are
snake_case per §5.1's topic-naming rule.  See OQ-6: document 03 §6's catalog
lists events in the SHORT form (`prediction.updated`), and it is not stated
whether the short form is shorthand for the document or a second wire value."""


class EventEnvelope(FathomModel):
    """Document 03 §5.4 `EventEnvelope`, with `clock` merged in.  See OQ-3.

    Every event on every topic carries exactly this envelope.  A substituting
    implementation must produce it (document 03 §10 requirement 2).
    """

    event_id: UUID = Field(
        description="UUID; THE CONSUMER IDEMPOTENCY KEY.  Document 03 §5.4, §5.2."
    )
    event_type: str = Field(
        pattern=EVENT_TYPE_RE.pattern,
        description=(
            '"fathom.<slug>.<aggregate>.<verb>" — snake_case throughout  [C26].  '
            "Document 03 §5.4."
        ),
    )
    event_version: int = Field(
        ge=1, description="Major version of the payload schema.  Document 03 §5.4."
    )
    occurred_at: UtcDateTime = Field(
        description=(
            "When the fact became true in the domain.  Document 03 §5.4: "
            "distinct from `recorded_at` because they diverge materially here — "
            "a mission anomaly occurred at sea and was recorded when the ship "
            "reconnected.  FEATURE COMPUTATION MUST NOT USE `occurred_at` FOR "
            "ANY VALUE AUTHORED WITH HINDSIGHT (§7.1, [D22])."
        )
    )
    recorded_at: UtcDateTime = Field(
        description=(
            "When the producer persisted it.  Document 03 §5.4: AUDIT USES "
            "`recorded_at`."
        )
    )
    producer: "ProducerRef" = Field(
        description="Slug from §3.1, plus version.  Document 03 §5.4."
    )
    producer_node: NonEmptyStr = Field(
        description=(
            '"enterprise" | "edge:<asset_id>" — WHICH DEPLOYMENT INSTANCE of '
            "`producer.slug` emitted this event.  Document 03 §5.4 (added same "
            "session as this package, after this field was first omitted): a "
            "sub-application with an edge profile runs as two independent "
            "instances of the same slug, each minting its own `monotonic_seq`; "
            "without this field their sequences collide and the dedup key "
            "silently drops an event.  Ordering and deduplication use "
            "`(producer, producer_node, monotonic_seq)` — NEVER `(producer, "
            "monotonic_seq)` alone."
        )
    )
    correlation_id: NonEmptyStr = Field(
        description=(
            "Document 03 §5.4 and §4 (Correlation): accepted, generated when "
            "absent, propagated to every log line, event, and downstream call."
        )
    )
    causation_id: UUID | None = Field(
        default=None,
        description=(
            "`event_id` of the immediately preceding event, where applicable.  "
            "Document 03 §5.4.  Used by the antecedent rule to resolve a "
            "blocked event  [D4]."
        ),
    )
    scope: EventScope = Field(description="Document 03 §5.4  [C11].")
    subject: EventSubject = Field(
        description=(
            "Exactly one scope identifier required, matching `scope`.  "
            "Document 03 §5.4."
        )
    )
    baseline_epoch: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Monotonic per-asset configuration epoch, where applicable  "
            "[D3, D4].  Document 03 §5.4: 'Any event whose correctness depends "
            "on configuration carries the epoch it was computed under.  A "
            "consumer that receives an event with an epoch ahead of its own "
            "configuration read model MUST BLOCK that event until the antecedent "
            "configuration event is applied, resolved via `causation_id` or by "
            "reading `changed_since` from the Registry.'"
        ),
    )
    classification: ClassificationLabel = Field(
        description=(
            "Document 03 §5.4 and principle 7: 'Every event envelope and every "
            "API response carries a classification label.'  Typed as the full "
            "§7.3 label, not a bare level string."
        )
    )
    replay: bool = Field(
        description=(
            "True for backfill-generated events.  Document 03 §5.3: consumers "
            "must ignore or handle `replay: true` events idempotently and MUST "
            "NOT raise operator-visible alerts from them  [D30]."
        )
    )
    clock: Clock = Field(
        description=(
            "Document 03 §5.4, 'Clock discipline' block.  Merged into the "
            "envelope here; see OQ-3."
        )
    )

    # --- cross-field rules from §5.4 -----------------------------------
    @model_validator(mode="after")
    def _exactly_one_scope_identifier(self) -> Self:
        """Document 03 §5.4: "exactly one scope identifier required, matching
        `scope`"  [C11]."""
        populated = {
            name
            for name, value in self.subject.wire_dict().items()
            if value is not None
        }
        expected = SCOPE_SUBJECT_FIELD[self.scope]

        if expected is None:                        # EventScope.FLEET — OQ-4
            if populated:
                raise ValueError(
                    "scope='fleet' carries an empty subject: document 03 §5.4's "
                    "`subject` block declares no fleet-scope identifier.  See "
                    f"OQ-4 in build document 10 §11.  Got: {sorted(populated)}"
                )
            return self

        if populated != {expected}:
            if populated == {"mission_id"}:
                raise ValueError(
                    "a mission-only subject is unrepresentable: no `scope` value "
                    "in document 03 §5.4 selects `mission_id`.  The catalog "
                    "carries `mission_id` in the PAYLOAD of `mission.completed` "
                    "and scopes the envelope to the asset.  See OQ-4."
                )
            raise ValueError(
                f"scope={self.scope.value!r} requires exactly `subject.{expected}` "
                f"and no other identifier (document 03 §5.4); got "
                f"{sorted(populated) or 'nothing'}"
            )
        return self

    @model_validator(mode="after")
    def _event_type_matches_producer(self) -> Self:
        """Document 03 §5.4 + §3.1: the slug token in `event_type` is the
        producer's canonical slug, "used without variation"  [C27]."""
        match = EVENT_TYPE_RE.match(self.event_type)
        assert match is not None                      # pattern= already enforced
        if match.group("slug") != str(self.producer.slug):
            raise ValueError(
                f"event_type slug {match.group('slug')!r} does not match "
                f"producer.slug {str(self.producer.slug)!r} (document 03 §3.1, "
                "§5.4  [C27])"
            )
        return self

    # --- ordering, per §5.4 rule 1 -------------------------------------
    @property
    def dedup_key(self) -> tuple[str, int]:
        """`(producer.slug, clock.monotonic_seq)` — document 03 §5.4 rule 1.

        `producer` carries "slug from §3.1, plus version", but the ORDERING key
        uses the slug alone: including the producer version would reset the
        sequence at every deployment and break deduplication across a rolling
        upgrade.  Flagged as OQ-5.
        """
        return (str(self.producer.slug), self.clock.monotonic_seq)

    def precedes(self, other: "EventEnvelope") -> bool:
        """Causal ordering per document 03 §5.4 rule 1.  Never `source_time`."""
        if self.producer.slug == other.producer.slug:
            return self.clock.monotonic_seq < other.clock.monotonic_seq
        return self.clock.hlc < other.clock.hlc

    @property
    def timestamp_arbitration_permitted(self) -> bool:
        """Document 03 §5.4 rule 3.

        False whenever a backward step has landed or the time source is
        untrusted.  The caller must additionally compare `dispersion_ms`
        against its own inter-write interval, which this package cannot know.
        """
        sq = self.clock.sync_quality
        return not sq.step_occurred and sq.time_source not in (
            TimeSource.HOLDOVER,
            TimeSource.UNSYNCED,
        )


class ProducerRef(FathomModel):
    """Document 03 §5.4 `producer`: "slug from §3.1, plus version".

    Modelled as a two-member structure rather than a delimited string so the
    slug is machine-comparable without parsing.  See OQ-5 on the ordering-key
    consequence.
    """

    slug: AnySlug = Field(description="Slug from document 03 §3.1.")
    version: NonEmptyStr = Field(
        description="Producing implementation version, e.g. '2.4.1'."
    )


EventEnvelope.model_rebuild()
```

The topic and event-name grammar from §5.1 lives beside it:

```python
# src/fathom_schemas/topics.py
"""Topic and event-name grammar.  Document 03 §5.1 and §5.4  [C26].

C26: "Event names are inconsistently qualified and cased between the envelope
example, the topic scheme, and the catalog."  One grammar, one function.
"""
from __future__ import annotations

import re

from .slugs import AnySlug

TOPIC_RE = re.compile(
    r"^fathom\.(?P<slug>[a-z][a-z0-9-]*)\.(?P<aggregate>[a-z][a-z0-9_]*)"
    r"\.v(?P<major>[1-9]\d*)$"
)
"""Document 03 §5.1: `fathom.<slug>.<aggregate>.v<major>`, snake_case for the
aggregate token.  Examples given: `fathom.registry.configuration_baseline.v1`,
`fathom.pdm.prediction.v1`, `fathom.pma.anomaly_tag.v1`  [C26]."""


def topic_name(slug: AnySlug, aggregate: str, major: int) -> str:
    """Build a topic name.  The ONLY sanctioned way to construct one.

    Document 03 §5.1: "One topic per aggregate type per producing
    sub-application; topics are never shared between producers."
    """
    name = f"fathom.{slug}.{aggregate}.v{major}"
    if not TOPIC_RE.match(name):
        raise ValueError(f"not a valid document 03 §5.1 topic name: {name!r}")
    return name


def proposal_topic(slug: AnySlug) -> str:
    """Document 03 §6, "Proposals — a convention".

    "Every sub-application accepting agent proposals publishes to
    `fathom.<slug>.proposal.v1` using the §8.2 schema, permitting the gateway
    to build a unified adjudication queue from a topic pattern without any
    sub-application knowing the queue exists."

    (Document 03 §6 cites "the §8.2 schema"; the Proposal schema is at §7.2.
    §8.2 is the manifest structure.  Recorded as OQ-7.)
    """
    return topic_name(slug, "proposal", 1)


PROPOSAL_TOPIC_PATTERN = r"^fathom\.[a-z][a-z0-9-]*\.proposal\.v1$"
"""The pattern subscription the gateway uses to assemble the unified
adjudication queue.  Document 03 §6.  Note document 05 D32: the gateway
becoming a stateful all-domain consumer contradicts its stateless-composition
role — that tension is document 04's to resolve, not this package's."""


def event_type(slug: AnySlug, aggregate: str, verb: str) -> str:
    """Document 03 §5.4: `fathom.<slug>.<aggregate>.<verb>`  [C26]."""
    return f"fathom.{slug}.{aggregate}.{verb}"
```

### 4.6 `FailurePrediction` — document 03 §7.1

Document 03 §7.1 opens: ***"This supersedes the illustrative shape in document 01 §7"*** `[C2]`. C2 is the finding that document 03 §7.1 *"claims to 'reproduce' document 01 §7's `FailurePrediction` but materially changes it; and 01 §7's use of `eic` as a join key violates 03 §4's own identity rule. The **approved artifact is the non-conformant one**."* Document 01 §7 has since been corrected to defer: *"The wire contract is **document 03 §7.1, which is authoritative.** It is not reproduced here, because two divergent copies existed in rev 3 and the approved copy was the non-conformant one."*

**This model is the third and final copy, and it is executable.** There are now exactly two normative statements of this schema: document 03 §7.1, and this Pydantic model generated into JSON Schema. Any third copy is a defect.

```python
# src/fathom_schemas/prediction.py
"""FailurePrediction.  Document 03 §7.1, transcribed exactly.

Document 03 §7.1 states four embedded corrections, "each [closing] a defect
that would otherwise be silent":

- `reference_class` REPLACES cross-tier probability comparability.  A tier-0
  population rate and a tier-3 item-conditional probability can each be
  perfectly calibrated and remain incomparable.  Consumers do not compare
  `p_failure` across reference classes; the scheduling optimizer applies a
  per-class decision-theoretic conversion to expected consequence  [D7].
- `rul` is OMITTED where the reference class is not item-conditional.  A
  memoryless population fit cannot produce a per-item residual-life
  distribution, and rendering one indistinguishably from a tier-3 distribution
  misleads the operator  [D19].
- `fallback_level` is SEPARATE from `confidence`.  One scalar cannot carry both
  sharpness and epistemic reference-class depth and remain orderable  [D7].
- `contributing_factors` requires `attribution_method` and `stability`, and
  `observation_ref` points at a feature observation rather than at itself.
  Factors below a stability threshold are suppressed from display, and agents
  MUST NOT render them in causal language — a causal statement must cite an
  adjudicated Failure Intelligence hypothesis  [D23].

And the invariance rule: "Tier invariance survives as SHAPE invariance:
consumers must not branch on `tier`.  They may, and must, branch on
`reference_class`."  Enforced statically by lint rule FTH006 (§4.4).
"""
from __future__ import annotations

from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from ._base import FathomModel, Niin, NonEmptyStr, UtcDateTime
from .constants import CALIBRATION_POPULATION_FLOOR


class ReferenceClass(StrEnum):
    """Document 03 §7.1 `reference_class`.

    "item | niin_fleet | equipment_family | class_estimate"

    Document 06 §3 records the decision: `reference_class` is REQUIRED on every
    prediction; consumers may branch on reference class; they still must not
    branch on tier.
    """

    ITEM = "item"
    NIIN_FLEET = "niin_fleet"
    EQUIPMENT_FAMILY = "equipment_family"
    CLASS_ESTIMATE = "class_estimate"

    @property
    def is_item_conditional(self) -> bool:
        """Document 03 §7.1: `rul` is "OMITTED where reference_class is not
        item-conditional".  Only `item` is item-conditional — the other three
        are population reference classes  [D19]."""
        return self is ReferenceClass.ITEM


class RulUnit(StrEnum):
    """Document 03 §7.1 `rul.unit`.

    "days | steaming_hours | eoh | cycles | sorties | dives"

    Domain-specific units under a common shape (document 01 §6, UsageCounter).
    `eoh` is engine operating hours.
    """

    DAYS = "days"
    STEAMING_HOURS = "steaming_hours"
    EOH = "eoh"
    CYCLES = "cycles"
    SORTIES = "sorties"
    DIVES = "dives"


class Rul(FathomModel):
    """Document 03 §7.1 `rul {}`: "p10, p50, p90, unit".

    OMITTED (null) where `reference_class` is not item-conditional  [D19].
    """

    p10: float = Field(ge=0.0, description="10th percentile residual life.")
    p50: float = Field(ge=0.0, description="Median residual life.")
    p90: float = Field(ge=0.0, description="90th percentile residual life.")
    unit: RulUnit = Field(description="Document 03 §7.1.")

    @model_validator(mode="after")
    def _quantiles_ordered(self) -> Self:
        """p10 <= p50 <= p90.  Not stated in §7.1, but a violation is a
        malformed distribution rather than a contract variation; the ordering is
        implied by the quantile names themselves."""
        if not (self.p10 <= self.p50 <= self.p90):
            raise ValueError(
                f"RUL quantiles must be ordered p10<=p50<=p90; got "
                f"{self.p10}, {self.p50}, {self.p90}"
            )
        return self


class ContributingFactor(FathomModel):
    """Document 03 §7.1 `contributing_factors[]`.

    "renamed from `drivers`"  [D23].

    D23 in full: "`drivers[]` cannot be produced honestly.  At tier 2,
    attributions over correlated channels are unidentified and will reorder run
    to run on unchanged data.  At tier 3 the field reads as causal and the
    Maintainer Copilot renders it as a reason — an unadjudicated back channel
    delivering causal claims to the deckplate, bypassing the constraint Failure
    Intelligence is deliberately built around.  `evidence_ref` is unsatisfiable
    for a model-internal attribution."

    The rename is therefore NOT cosmetic.  Three fields were added to make the
    attribution honest, and `evidence_ref` became `observation_ref` pointing at
    a feature observation rather than at itself.  See lint rule FTH003 (§4.4)
    and the DO-NOT list (§10.1).
    """

    factor: NonEmptyStr = Field(description="Document 03 §7.1.")
    contribution: float = Field(description="Document 03 §7.1.  Signed; see OQ-8.")
    attribution_method: NonEmptyStr = Field(
        description=(
            "REQUIRED.  Document 03 §7.1.  The method by which the contribution "
            "was attributed, so a consumer can judge whether the attribution is "
            "identified at all  [D23].  Typed as a free string: document 03 §7.1 "
            "enumerates no vocabulary.  See OQ-8."
        )
    )
    stability: float = Field(
        description=(
            "REQUIRED.  Rank stability across runs or bootstrap.  Document 03 "
            "§7.1.  Factors below a stability threshold are SUPPRESSED FROM "
            "DISPLAY  [D23].  Document 03 §7.1 does not set the threshold — see "
            "OQ-8 and `is_displayable`."
        )
    )
    observation_ref: NonEmptyStr = Field(
        description=(
            "The feature observation, with point-in-time provenance.  Document "
            "03 §7.1.  Points at a feature observation rather than at itself — "
            "D23 records that the former `evidence_ref` was unsatisfiable for a "
            "model-internal attribution.  Point-in-time provenance is what makes "
            "definition-time leakage detectable  [D22]."
        )
    )

    def is_displayable(self, stability_threshold: float) -> bool:
        """Document 03 §7.1: "Factors below a stability threshold are suppressed
        from display".

        The threshold is a REQUIRED ARGUMENT rather than a package constant
        because document 03 §7.1 does not set a value and this package does not
        invent one (OQ-8).  A caller that has no threshold has no licence to
        display the factor.
        """
        return self.stability >= stability_threshold
```

```python
class FailurePrediction(FathomModel):
    """Document 03 §7.1 `FailurePrediction`.

    THE authoritative wire contract, superseding the illustrative shape in
    document 01 §7  [C2].  Document 01 §7 now defers to §7.1 explicitly.
    """

    # --- identity: document 03 §7.1 line 1, §3.3 -----------------------
    asset_id: UUID = Field(description="Document 03 §7.1; join key per §3.3.")
    installed_item_id: UUID = Field(
        description=(
            "Document 03 §7.1; join key per §3.3.  Identifies the PHYSICAL "
            "ITEM: remaining useful life, usage accumulation, and failure "
            "history attach to the installed item  [C10].  There is no field "
            "named `equipment_id`, and `eic` is not an identifier here  [C2]."
        )
    )
    position_id: UUID = Field(
        description="Document 03 §7.1; join key per §3.3.  Where it is installed."
    )
    niin: Niin = Field(description="Document 03 §7.1; join key per §3.3.")
    equipment_family: NonEmptyStr = Field(
        description=(
            "Document 03 §7.1.  Partitions model bindings, calibration records, "
            "and reference classes; owned and versioned by Reference Data  "
            "[D35, §3.3, §14]."
        )
    )

    # --- configuration fencing: document 03 §7.1 line 2, §5.4 ----------
    baseline_id: UUID = Field(
        description=(
            "Document 03 §7.1, §3.3 rule 5: "
            "'A prediction computed against a superseded baseline is invalid, "
            "and consumers must be able to detect that without inference.'"
        )
    )
    baseline_epoch: int = Field(
        ge=0,
        description=(
            "Monotonic per-asset configuration epoch the prediction was "
            "computed under  [D3, D4].  Document 03 §7.1, §5.4.  D3: 'A long "
            "scoring job reads baseline B1, the baseline becomes B2 mid-run, and "
            "the job's stale result lands after the invalidation and wins — and "
            "looks fresher by `computed_at`.'  The epoch, not `computed_at`, is "
            "what fences that."
        ),
    )

    # --- the prediction: document 03 §7.1 -------------------------------
    horizon_days: int = Field(
        gt=0,
        description=(
            "Document 03 §7.1.  Document 06 §7 sets the demonstration horizon "
            "set at 3 horizons per item: 30, 90, 180 days."
        ),
    )
    p_failure: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Calibrated WITHIN ITS DECLARED REFERENCE CLASS.  Document 03 §7.1 "
            "(rev 2, corrected same session as this package): NULL when "
            "`calibration_population < 50` (document 06 §3's gate) — below the "
            "gate `reference_class` is forced to `class_estimate` and only "
            "`population_hazard_rate` is populated.  A consumer treating a null "
            "`p_failure` as zero risk reintroduces the comparability defect this "
            "field exists to prevent.  Consumers MUST NOT compare `p_failure` "
            "across reference classes even when non-null; the scheduling "
            "optimizer applies a per-class decision-theoretic conversion to "
            "expected consequence  [D7]."
        ),
    )
    reference_class: ReferenceClass = Field(
        description=(
            "item | niin_fleet | equipment_family | class_estimate.  Document 03 "
            "§7.1.  REPLACES cross-tier probability comparability  [D7]."
        )
    )
    sharpness: float = Field(
        description=(
            "Dispersion relative to the reference-class base rate.  Document 03 "
            "§7.1.  No scale or range is specified there; see OQ-9."
        )
    )
    calibration_population: int | None = Field(
        default=None,
        ge=0,
        description=(
            "n backing the calibration cell; NULL IF UNGATED.  Document 03 §7.1.  "
            "Document 06 §3 sets the gate: n >= 50 item-horizons in the "
            "calibration cell to publish a calibrated `p_failure`; below that, "
            "the prediction publishes at `reference_class = class_estimate` with "
            "a population hazard rate and no calibrated probability.  See OQ-10 "
            "on the tension between 'no calibrated probability' and §7.1's "
            "unconditional `p_failure`."
        ),
    )
    rul: Rul | None = Field(
        default=None,
        description=(
            "OMITTED where `reference_class` is not item-conditional.  Document "
            "03 §7.1  [D19].  Explicit `null` rather than an absent key, so "
            "'not applicable' is distinguishable from 'not populated'."
        ),
    )
    population_hazard_rate: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Emitted INSTEAD OF `rul` for non-item reference classes.  Document "
            "03 §7.1  [D19]."
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "SHARPNESS-AND-FIT CONFIDENCE ONLY.  Document 03 §7.1.  Cold-start "
            "depth is NOT encoded here — see `fallback_level`.  D7: 'one scalar "
            "cannot carry both and stay orderable.'"
        ),
    )
    fallback_level: int = Field(
        ge=0,
        le=4,
        description=(
            "0..4; cold-start depth, NOT encoded in `confidence`.  Document 03 "
            "§7.1  [D7].  The fallback hierarchy is item history, then NIIN "
            "fleet history, then equipment-family history, then class-level "
            "engineering estimate (document 04 §4)."
        ),
    )
    tier: int = Field(
        ge=0,
        le=3,
        description=(
            "0..3, TRANSPARENCY ONLY.  Document 03 §7.1.  Consumers MUST NOT "
            "branch on this field; branch on `reference_class`.  Enforced by "
            "lint rule FTH006 (§4.4 of build document 10)."
        ),
    )
    contributing_factors: tuple[ContributingFactor, ...] = Field(
        default=(),
        description=(
            "Renamed from `drivers`  [D23].  Document 03 §7.1.  Never rendered "
            "in causal language: 'a causal statement must cite an adjudicated "
            "Failure Intelligence hypothesis.'"
        ),
    )

    # --- provenance: document 03 §7.1 final line ------------------------
    model_version: NonEmptyStr = Field(
        description=(
            "Document 03 §7.1.  The Domino registry model version bound to this "
            "tier and family; the BINDING is PdM's domain, the artifact is "
            "Domino's  [C32, §14]."
        )
    )
    scoring_run_id: UUID = Field(
        description=(
            "Document 03 §7.1.  `prediction.updated` references the run artifact "
            "rather than inlining result sets  [D27]."
        )
    )
    computed_at: UtcDateTime = Field(
        description=(
            "Document 03 §7.1.  NOT a freshness arbiter: D3 records that a "
            "stale result 'looks fresher by `computed_at`'.  Use "
            "`baseline_epoch` to detect staleness, per §3.3 rule 5."
        )
    )

    # --- cross-field rules, all four from §7.1 --------------------------
    @model_validator(mode="after")
    def _rul_only_when_item_conditional(self) -> Self:
        """Document 03 §7.1: `rul` is "OMITTED where reference_class is not
        item-conditional"; `population_hazard_rate` is "emitted instead of `rul`
        for non-item reference classes"  [D19].

        D19: "Tier 0 is defined as the random-failure population, i.e. Weibull
        beta ~= 1, i.e. memoryless — so conditional residual life is identical
        for a new and a nine-year-old item.  The UI renders it indistinguishably
        from a tier-3 distribution."
        """
        if self.reference_class.is_item_conditional:
            if self.rul is None:
                raise ValueError(
                    "reference_class='item' is item-conditional and REQUIRES "
                    "`rul` (document 03 §7.1)"
                )
            if self.population_hazard_rate is not None:
                raise ValueError(
                    "`population_hazard_rate` is emitted INSTEAD OF `rul`, for "
                    "non-item reference classes only (document 03 §7.1  [D19])"
                )
        else:
            if self.rul is not None:
                raise ValueError(
                    f"reference_class={self.reference_class.value!r} is not "
                    "item-conditional, so `rul` must be omitted: a memoryless "
                    "population fit cannot produce a per-item residual-life "
                    "distribution (document 03 §7.1  [D19])"
                )
            if self.population_hazard_rate is None:
                raise ValueError(
                    f"reference_class={self.reference_class.value!r} REQUIRES "
                    "`population_hazard_rate` (document 03 §7.1  [D19])"
                )
        return self

    @model_validator(mode="after")
    def _calibration_gate(self) -> Self:
        """Document 06 §3, Decision 2: "Calibration population gate: n >= 50
        item-horizons in the calibration cell to publish a calibrated
        `p_failure`.  Below that, the prediction publishes at
        `reference_class = class_estimate` with a population hazard rate and no
        calibrated probability."

        Sourced from document 06, NOT document 03 — document 03 §7.1 says only
        "null if ungated".  The threshold lives in `constants.py` with its
        citation so it is revisable as one edit.  See OQ-10.
        """
        n = self.calibration_population
        if n is None:
            return self                     # ungated, per §7.1
        if (
            n < CALIBRATION_POPULATION_FLOOR
            and self.reference_class is not ReferenceClass.CLASS_ESTIMATE
        ):
            raise ValueError(
                f"calibration_population={n} is below the document 06 §3 gate of "
                f"{CALIBRATION_POPULATION_FLOOR} item-horizons; such a prediction "
                "publishes at reference_class='class_estimate' with a population "
                f"hazard rate, not at {self.reference_class.value!r}"
            )
        return self

    # --- consumer helpers ----------------------------------------------
    def comparable_with(self, other: "FailurePrediction") -> bool:
        """Document 03 §7.1: "Consumers do not compare `p_failure` across
        reference classes."

        Provided so a consumer never has to write the reference-class check
        itself — and so the wrong form of the check (`self.tier == other.tier`)
        never appears in a consumer, which FTH006 would flag anyway.
        """
        return self.reference_class is other.reference_class

    def is_stale_against(self, current_baseline_epoch: int) -> bool:
        """Document 03 §3.3 rule 5 and §5.4.  Epoch comparison, never
        `computed_at`  [D3]."""
        return self.baseline_epoch < current_baseline_epoch
```

```python
# src/fathom_schemas/constants.py
"""Numeric thresholds referenced by validators, each with its source citation.

Document 03 states no numbers; document 06 records the demonstration's design
envelope.  Every constant here cites document 06, and a constant with no
citation is a defect — see the "do not invent" rule in §11.
"""

CALIBRATION_POPULATION_FLOOR: int = 50
"""Document 06 §3, Decision 2: "Calibration population gate: n >= 50
item-horizons in the calibration cell to publish a calibrated `p_failure`."
Document 06 marks the value MEDIUM confidence, "chosen as a practical floor,
not derived", and notes it should be raised for high-consequence families."""

PREDICTION_HORIZONS_DAYS: tuple[int, ...] = (30, 90, 180)
"""Document 06 §7, "Prediction and scoring": 3 horizons per item, MEDIUM
confidence.  Used by the reference dataset and the conformance harness; NOT
enforced on `FailurePrediction.horizon_days`, because document 03 §7.1 places
no enumeration on the field."""

# Deliberately ABSENT, because no document supplies a value.  See OQ-8, OQ-9.
# CONTRIBUTING_FACTOR_STABILITY_FLOOR — the display-suppression threshold of
# document 03 §7.1.  `ContributingFactor.is_displayable` takes it as an
# argument rather than defaulting it.
```

### 4.7 `Proposal` — document 03 §7.2

```python
# src/fathom_schemas/proposal.py
"""Proposal.  Document 03 §7.2, transcribed exactly.

The field is `proposal_id`, not `id`  [C30].  C30: "`Proposal` field names
diverge between 01 §8.4 (`id`) and 03 §7.2 (`proposal_id`)."  Document 03 is
binding; `id` is the losing spelling and must not be reintroduced (§10.1).

Document 03 §7.2's four rules, which "make this safe rather than merely
descriptive":

- `evidence` is REQUIRED AND NON-EMPTY, rejected at the API boundary if absent.
  But a non-empty evidence list is not sufficient: evidence carries
  `source_trust`, and a proposal resting solely on non-program content is
  flagged to the adjudicator  [D14].
- Re-validation at approval is MANDATORY.  The owning sub-application
  re-validates `payload` against current configuration at adjudication time and
  rejects if `baseline_epoch` is superseded or `valid_until` has passed.
  Validation at creation is insufficient  [D16].
- Adjudication requires a CLAIM.  `POST /proposals/{id}/claim` obtains a lease;
  adjudication requires `If-Match` on the claimed ETag.  Without this the
  eventually-consistent queue permits two approvals and two work orders  [D16].
- Authority is checked against BLAST RADIUS.  Dual control is mandatory at
  class and fleet scope and for any kind with external legal effect  [D16].
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Self
from uuid import UUID

from pydantic import Field, model_validator

from ._base import FathomModel, NonEmptyStr, UtcDateTime
from .classification import ClassificationLabel
from .envelope import EventSubject
from .slugs import SubAppSlug


class ProposalKind(StrEnum):
    """Document 03 §7.2 `kind`  [C39].

    "anomaly_tag | work_candidate | requisition | interval_change |
    redesign_case | configuration_change"

    C39: "The conflict policy requires 'proposed' configuration changes with no
    matching proposal kind and no endpoint" — `configuration_change` is the
    sixth kind added by that fix.  Document 05 §3.4's note that "all five
    `Proposal` kinds have exactly one executing sub-application" predates it.
    """

    ANOMALY_TAG = "anomaly_tag"
    WORK_CANDIDATE = "work_candidate"
    REQUISITION = "requisition"
    INTERVAL_CHANGE = "interval_change"
    REDESIGN_CASE = "redesign_case"
    CONFIGURATION_CHANGE = "configuration_change"


class BlastRadius(StrEnum):
    """Document 03 §7.2 `blast_radius`: "item | asset | class | fleet"  [D16]."""

    ITEM = "item"
    ASSET = "asset"
    CLASS = "class"
    FLEET = "fleet"


class ProposalStatus(StrEnum):
    """Document 03 §7.2 `status`.

    "proposed | claimed | approved | rejected | superseded | expired"
    """

    PROPOSED = "proposed"
    CLAIMED = "claimed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"


class EvidenceKind(StrEnum):
    """Document 03 §7.2 `evidence[].kind`.

    "record | document_chunk | prediction | trace"
    """

    RECORD = "record"
    DOCUMENT_CHUNK = "document_chunk"
    PREDICTION = "prediction"
    TRACE = "trace"


class SourceTrust(StrEnum):
    """Document 03 §7.2 `evidence[].source_trust`: "program | vendor | external"
    [D14].

    Document 03 §9 item 5: "Corpus ingest records authorship and provenance,
    and content from outside the program is marked AT INGEST rather than
    inferred later."  This field is that marking, carried forward.
    """

    PROGRAM = "program"
    VENDOR = "vendor"
    EXTERNAL = "external"


class Evidence(FathomModel):
    """Document 03 §7.2 `evidence[]`: "required, non-empty"."""

    kind: EvidenceKind = Field(description="Document 03 §7.2.")
    ref: NonEmptyStr = Field(description="Document 03 §7.2.")
    excerpt: str | None = Field(
        default=None,
        description=(
            "Document 03 §7.2, optional.  UNTRUSTED DATA, NEVER INSTRUCTION "
            "(§9 item 1): tool results and retrieved passages are structurally "
            "separated from instructions in every agent prompt  [D14]."
        ),
    )
    relevance: float | None = Field(
        default=None, description="Document 03 §7.2, optional."
    )
    source_trust: SourceTrust = Field(
        description="program | vendor | external.  Document 03 §7.2  [D14]."
    )


EXTERNAL_LEGAL_EFFECT_KINDS: frozenset[ProposalKind] = frozenset(
    {ProposalKind.REQUISITION}
)
"""Kinds with external legal effect, for which document 03 §7.2 makes dual
control mandatory.

Document 03 §7.2 does not enumerate the set.  `requisition` is derived from
§11's conflict-policy table, which states "Requisitions | Server-authoritative;
edge queues submissions | External legal effect", and from §10's migration
sequence, which names "requisition creation and reservation confirmation" as
having "real-world effect".  Recorded as OQ-12: the set should be enumerated in
document 03 §7.2 rather than inferred here."""


class Proposal(FathomModel):
    """Document 03 §7.2 `Proposal`.

    Published by every sub-application accepting agent proposals to
    `fathom.<slug>.proposal.v1` (§6, "Proposals — a convention").

    Note C12, unresolved in document 04: "`Proposal` is owned by 'the executing
    sub-application', but no sub-application in 04 lists it in its Owns boundary
    or aggregate table."  That is document 04's tranche-3 fix; this package
    supplies the shape either way.
    """

    proposal_id: UUID = Field(
        description=(
            "Document 03 §7.2  [C30].  NOT `id` — document 01 §8.4's `id` is the "
            "losing spelling."
        )
    )
    kind: ProposalKind = Field(description="Document 03 §7.2  [C39].")
    target_sub_app: SubAppSlug = Field(
        description=(
            "Slug from §3.1.  Document 03 §7.2.  One of the four schemes C27 "
            "records as referencing a canonical identifier that did not exist."
        )
    )
    subject: EventSubject = Field(
        description="Scope identifiers per §5.4.  Document 03 §7.2."
    )
    baseline_id: UUID = Field(description="Document 03 §7.2  [D16].")
    baseline_epoch: int = Field(
        ge=0,
        description=(
            "Document 03 §7.2  [D16].  Re-validated at adjudication: the owning "
            "sub-application rejects if `baseline_epoch` is superseded.  D16: "
            "'A `work_candidate` sits five weeks, the equipment is replaced, "
            "validation happened at creation, and approval executes against a "
            "configuration that no longer exists.'"
        ),
    )
    payload: dict[str, Any] = Field(
        description=(
            "The domain object, VALIDATED BY THE OWNING SUB-APPLICATION.  "
            "Document 03 §7.2.  Deliberately opaque here: §9 item 2 places "
            "domain policy enforcement in the sub-application, not in this "
            "package — 'a requisition proposal's NIIN must be APL-authorized "
            "for that position; an `interval_change` must fall within a bounded "
            "delta and route to PMS authority; a `work_candidate` must reference "
            "an installed item present in the current baseline.'  Those are "
            "validation rules on the receiving operation."
        )
    )
    evidence: tuple[Evidence, ...] = Field(
        min_length=1,
        description=(
            "REQUIRED, NON-EMPTY.  Document 03 §7.2, rejected at the API "
            "boundary if absent  [D14]."
        ),
    )
    rationale: NonEmptyStr = Field(description="Document 03 §7.2.")
    confidence: float = Field(ge=0.0, le=1.0, description="Document 03 §7.2.")
    agent_id: NonEmptyStr = Field(description="Document 03 §7.2.")
    agent_version: NonEmptyStr = Field(description="Document 03 §7.2.")
    llm_version: NonEmptyStr = Field(description="Document 03 §7.2.")
    trace_ref: NonEmptyStr = Field(
        description=(
            "Document 03 §7.2 and §8.5: tool invocations are recorded to Audit & "
            "Provenance and correlated to the Domino trace by `trace_ref`."
        )
    )
    authority_class: NonEmptyStr = Field(
        description=(
            "Required authority to adjudicate  [D16].  Document 03 §7.2 cites "
            '"§9.3" for the vocabulary, but document 03 §9 is "Untrusted '
            'content" and has no §9.3; the agent authority classes are at §8.3 '
            "and are AGENT authority classes (Delegated / Accountable "
            "autonomous), not ADJUDICATION authority classes.  The vocabulary "
            "is therefore undefined in document 03 and this field is typed as an "
            "opaque string, validated by the owning sub-application.  See OQ-13 "
            "— this is the most consequential open question in this package."
        )
    )
    blast_radius: BlastRadius = Field(
        description="item | asset | class | fleet.  Document 03 §7.2  [D16]."
    )
    requires_dual_control: bool = Field(
        description=(
            "True for class or fleet scope, and for any kind with external legal "
            "effect.  Document 03 §7.2  [D16].  Enforced by "
            "`_dual_control_required_at_scope` below."
        )
    )
    valid_until: UtcDateTime = Field(
        description=(
            "Expiry.  Document 03 §7.2: 'absent means no expiry is permitted' — "
            "read as 'the field is mandatory', hence non-optional here.  See "
            "OQ-14 on the alternative reading.  Re-validated at adjudication: "
            "the owning sub-application rejects if `valid_until` has passed."
        )
    )
    status: ProposalStatus = Field(description="Document 03 §7.2.")
    claimed_by: NonEmptyStr | None = Field(default=None, description="Document 03 §7.2  [D16].")
    claimed_until: UtcDateTime | None = Field(
        default=None,
        description=(
            "Lease expiry from `POST /proposals/{id}/claim`.  Document 03 §7.2  "
            "[D16].  Lease expiry is evaluated on a MONOTONIC CLOCK, never the "
            "wall clock (§5.4 rule 2)."
        ),
    )
    adjudicated_by: NonEmptyStr | None = Field(default=None, description="Document 03 §7.2.")
    adjudicated_at: UtcDateTime | None = Field(default=None, description="Document 03 §7.2.")
    adjudication_note: str | None = Field(default=None, description="Document 03 §7.2.")
    second_adjudicator: NonEmptyStr | None = Field(
        default=None, description="Dual control.  Document 03 §7.2  [D16]."
    )
    second_adjudicated_at: UtcDateTime | None = Field(
        default=None, description="Dual control.  Document 03 §7.2  [D16]."
    )
    classification: ClassificationLabel = Field(
        description="Document 03 §7.2 and principle 7."
    )

    # --- cross-field rules from §7.2 ------------------------------------
    @model_validator(mode="after")
    def _dual_control_required_at_scope(self) -> Self:
        """Document 03 §7.2: "requires_dual_control  # boolean; true for class or
        fleet scope, and for any kind with external legal effect", and rule 4:
        "Dual control is MANDATORY at class and fleet scope and for any kind
        with external legal effect"  [D16]."""
        mandatory = (
            self.blast_radius in (BlastRadius.CLASS, BlastRadius.FLEET)
            or self.kind in EXTERNAL_LEGAL_EFFECT_KINDS
        )
        if mandatory and not self.requires_dual_control:
            raise ValueError(
                f"blast_radius={self.blast_radius.value!r}, kind="
                f"{self.kind.value!r}: dual control is mandatory at class and "
                "fleet scope and for any kind with external legal effect "
                "(document 03 §7.2 rule 4  [D16])"
            )
        return self

    @model_validator(mode="after")
    def _claim_state_consistent(self) -> Self:
        """Document 03 §7.2 rule 3: "Adjudication requires a claim."  """
        if self.status is ProposalStatus.CLAIMED and not (
            self.claimed_by and self.claimed_until
        ):
            raise ValueError(
                "status='claimed' requires `claimed_by` and `claimed_until` "
                "(document 03 §7.2 rule 3  [D16])"
            )
        return self

    @model_validator(mode="after")
    def _adjudication_state_consistent(self) -> Self:
        """Document 03 §7.2: an adjudicated proposal records who and when; a
        dual-control proposal records a SECOND, DIFFERENT adjudicator  [D16].

        D16: "one `adjudicated_by` field spans a maintainer's anomaly tag and an
        `interval_change` that suppresses a preventive task across an entire
        class — no dual control, no authority-versus-blast-radius check."
        """
        terminal = (ProposalStatus.APPROVED, ProposalStatus.REJECTED)
        if self.status in terminal:
            if not (self.adjudicated_by and self.adjudicated_at):
                raise ValueError(
                    f"status={self.status.value!r} requires `adjudicated_by` and "
                    "`adjudicated_at` (document 03 §7.2)"
                )
            if self.requires_dual_control:
                if not (self.second_adjudicator and self.second_adjudicated_at):
                    raise ValueError(
                        f"status={self.status.value!r} with "
                        "requires_dual_control=True requires `second_adjudicator` "
                        "and `second_adjudicated_at` (document 03 §7.2 rule 4)"
                    )
                if self.second_adjudicator == self.adjudicated_by:
                    raise ValueError(
                        "dual control requires TWO DISTINCT adjudicators; "
                        f"{self.adjudicated_by!r} appears as both (document 03 "
                        "§7.2 rule 4  [D16])"
                    )
        else:
            if self.second_adjudicator or self.second_adjudicated_at:
                raise ValueError(
                    f"status={self.status.value!r} is not adjudicated, so no "
                    "second-adjudicator fields may be set (document 03 §7.2)"
                )
        return self

    # --- adjudicator-facing helpers -------------------------------------
    @property
    def rests_solely_on_non_program_content(self) -> bool:
        """Document 03 §7.2 rule 1 and §9 item 3: "a proposal resting solely on
        non-program content is FLAGGED TO THE ADJUDICATOR"  [D14].

        D14 is the reason: "A crafted or careless passage produces a requisition
        proposal with a substituted NIIN, a fluent rationale, and GENUINE
        citations that satisfy the non-empty-evidence gate mechanically."
        """
        return all(e.source_trust is not SourceTrust.PROGRAM for e in self.evidence)

    def is_expired_at(self, now: UtcDateTime) -> bool:
        """Document 03 §7.2 rule 2.  The caller supplies `now`; this package
        does not read a clock, because §5.4 rule 2 requires lease and expiry
        evaluation on a monotonic source the caller owns."""
        return now >= self.valid_until

    def revalidation_required_against(self, current_baseline_epoch: int) -> bool:
        """Document 03 §7.2 rule 2: re-validation at approval is MANDATORY, and
        the proposal is rejected if `baseline_epoch` is superseded.  Validation
        at creation is insufficient  [D16]."""
        return self.baseline_epoch < current_baseline_epoch
```

### 4.8 `ClassificationLabel` — document 03 §7.3

Document 03 §7.3 has been corrected since the review: `dissemination[]` is now *"constrained to the ten authorized Limited Dissemination Controls"* and the schema comment states explicitly that ***"'FOUO' and 'U//FOUO' are RETIRED markings (DoDI 5200.48 §3.4.b)"***, with the closing prose repeating *"the older `U//FOUO` form is retired."* The retired markings therefore appear in this package **only** as the forbidden-literal list of lint rule `FTH005` (§4.4). Note that document 05 C42 still lists "NOFORN/FOUO" among acronyms lacking glossary entries — that is a stale glossary item, not a licence to use the marking.

```python
# src/fathom_schemas/classification.py
"""ClassificationLabel.  Document 03 §7.3, transcribed exactly.

Document 03 §7.3: "The category and dissemination lists are TYPED RATHER THAN
FREE TEXT because DoDI 5200.48 requires a five-line CUI designation indicator
whose third and fourth lines are 'all types of CUI contained in the document'
and 'the distribution statement or the dissemination controls applicable' —
STRUCTURED OBLIGATIONS, NOT ANNOTATIONS.  Minimum marking is `CUI` in both
banner and footer; the older `U//FOUO` form is retired."

Document 03 principle 7 and §7.3: "Every derived value carries the UNION of its
inputs' labels", recorded in `inherited_from`  [D13].
"""
from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from ._base import FathomModel, NonEmptyStr


class ClassificationLevel(StrEnum):
    """Document 03 §7.3 `level`: "U | CUI | S | TS"."""

    U = "U"
    CUI = "CUI"
    S = "S"
    TS = "TS"

    @property
    def rank(self) -> int:
        """Ordering for the union rule of §7.3.  U < CUI < S < TS."""
        return _LEVEL_RANK[self]


_LEVEL_RANK: dict[ClassificationLevel, int] = {
    ClassificationLevel.U: 0,
    ClassificationLevel.CUI: 1,
    ClassificationLevel.S: 2,
    ClassificationLevel.TS: 3,
}


class DisseminationControl(StrEnum):
    """The TEN authorized Limited Dissemination Controls.  Document 03 §7.3.

    "NOFORN | FED ONLY | FEDCON | NOCON | DL ONLY | RELIDO | REL TO |
    DISPLAY ONLY | AC | AWP"

    This enum is CLOSED.  "FOUO" and "U//FOUO" are RETIRED markings (DoDI
    5200.48 §3.4.b) and are absent deliberately; lint rule FTH005 (§4.4 of
    build document 10) rejects them as string literals anywhere in the
    monorepo.
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
    """Document 03 §7.3 `distribution_statement`: "A..F or REL TO, per DoDI
    5230.24 Table 1.  Corresponds to line 4 of the designation indicator."

    Transcribed as the six statements A-F plus the `REL TO` form.  Note that
    `REL TO` appears in both this field and `dissemination[]`; document 03 §7.3
    lists it in both and this package follows.
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    REL_TO = "REL TO"


class ClassificationLabel(FathomModel):
    """Document 03 §7.3 `ClassificationLabel`.

    Carried on every event envelope (§5.4) and every API response (§4,
    `X-Classification`), per principle 7.
    """

    level: ClassificationLevel = Field(
        description="U | CUI | S | TS.  Document 03 §7.3."
    )
    cui_categories: tuple[NonEmptyStr, ...] = Field(
        default=(),
        description=(
            "CUI Registry categories present, e.g. SP-CTI, SP-NNPI, SP-EXPT.  "
            "Corresponds to LINE 3 of the DoDI 5200.48 designation indicator: "
            "'all types of CUI contained in the document'.  Document 03 §7.3.  "
            "Typed as strings rather than an enum because the CUI Registry is "
            "externally maintained and versioned outside this program; the "
            "authoritative list is served by Reference Data (§14).  See OQ-15."
        ),
    )
    dissemination: tuple[DisseminationControl, ...] = Field(
        default=(),
        description=(
            "Constrained to the TEN authorized Limited Dissemination Controls.  "
            "Document 03 §7.3.  Corresponds to LINE 4 of the designation "
            "indicator.  'FOUO' and 'U//FOUO' are RETIRED (DoDI 5200.48 §3.4.b)."
        ),
    )
    distribution_statement: DistributionStatement | None = Field(
        default=None,
        description=(
            "A..F or REL TO, per DoDI 5230.24 Table 1.  Corresponds to LINE 4 of "
            "the designation indicator.  Document 03 §7.3."
        ),
    )
    compartments: tuple[NonEmptyStr, ...] = Field(
        default=(),
        description=(
            "Document 03 §7.3.  §5.1: topics are segregated by classification "
            "level AND COMPARTMENT.  §7.3: 'Aggregation is a classification "
            "event' — a rollup whose value moves when a compartmented item "
            "degrades discloses that item's existence  [D13]."
        ),
    )
    derived_from: NonEmptyStr | None = Field(
        default=None, description="Classification authority reference.  Document 03 §7.3."
    )
    inherited_from: tuple[NonEmptyStr, ...] = Field(
        default=(),
        description=(
            "Input label references, for derived values  [D13].  Document 03 "
            "§7.3: 'Every derived value carries the UNION of its inputs' labels, "
            "recorded in `inherited_from` and enforced by the provenance "
            "obligation in §15.'"
        ),
    )

    @model_validator(mode="after")
    def _cui_categories_only_at_cui(self) -> Self:
        """DoDI 5200.48's designation indicator applies to CUI.  Document 03 §7.3
        ties `cui_categories[]` to the CUI marking regime and states the minimum
        marking is `CUI`; a level of `U` with CUI categories present is
        self-contradictory."""
        if self.cui_categories and self.level is ClassificationLevel.U:
            raise ValueError(
                "level='U' cannot carry `cui_categories`: the minimum marking "
                "for CUI is `CUI` in both banner and footer (document 03 §7.3, "
                "DoDI 5200.48)"
            )
        return self

    @classmethod
    def union(cls, *inputs: "ClassificationLabel", derived_from: str) -> Self:
        """The label of a derived value: the UNION of its inputs' labels.

        Document 03 principle 7 and §7.3  [D13].  This is the ONLY sanctioned
        way to label a derived value, and it exists here rather than in nine
        services so the union rule cannot be implemented nine ways.

        `inherited_from` accumulates the input references, which is what makes
        the inheritance auditable per §15 obligation 9.

        NOTE what this does NOT do: it does not implement the aggregation policy
        of §7.3 / document 06 §5.  Excluding compartmented contributors from a
        rollup, or computing a separate high-side view, is Fleet Status's
        scoring methodology and "is not a presentation concern".  This method
        computes a label; it does not decide what to aggregate.
        """
        if not inputs:
            raise ValueError("a derived value has at least one input label")
        return cls(
            level=max((i.level for i in inputs), key=lambda lv: lv.rank),
            cui_categories=tuple(
                sorted({c for i in inputs for c in i.cui_categories})
            ),
            dissemination=tuple(
                sorted({d for i in inputs for d in i.dissemination})
            ),
            distribution_statement=_most_restrictive_statement(inputs),
            compartments=tuple(sorted({c for i in inputs for c in i.compartments})),
            derived_from=derived_from,
            inherited_from=tuple(
                sorted({r for i in inputs for r in ([i.derived_from] if i.derived_from else [])})
            ),
        )


def _most_restrictive_statement(
    inputs: tuple["ClassificationLabel", ...],
) -> DistributionStatement | None:
    """DoDI 5230.24 Table 1 orders statements A (least restrictive) to F.

    `REL TO` is not ordinally comparable with A..F, so a union containing it
    raises rather than guessing.  See OQ-16.
    """
    present = {i.distribution_statement for i in inputs if i.distribution_statement}
    if not present:
        return None
    if DistributionStatement.REL_TO in present and len(present) > 1:
        raise ValueError(
            "cannot mechanically union `REL TO` with a lettered distribution "
            "statement: DoDI 5230.24 Table 1 does not order them.  The derived "
            "value requires an explicit determination by the classification "
            "authority.  See OQ-16."
        )
    order = "ABCDEF"
    lettered = [s for s in present if s.value in order]
    if not lettered:
        return DistributionStatement.REL_TO
    return max(lettered, key=lambda s: order.index(s.value))
```

> **Stray empty code fence in document 03 §7.3.** Immediately after the `ClassificationLabel` block and its explanatory paragraph, document 03 lines 503–504 contain an empty fenced block. It may be the residue of a removed `FOUO` example, or content lost in an edit. Recorded as OQ-17; **this package assumes nothing was intended to be there.**

### 4.9 TypeScript publication and the golden-vector corpus

The generation chain, all four steps in CI, all outputs committed:

```bash
# 1. Python models -> JSON Schema (draft 2020-12), committed
fathom-schemas emit-json-schema \
    --out packages/canonical-schemas/schemas/fathom.canonical/2/

# 2. JSON Schema -> TypeScript types (snake_case keys preserved)
npx json-schema-to-typescript \
    --input  'packages/canonical-schemas/schemas/fathom.canonical/2/*.json' \
    --output packages/canonical-schemas/ts/src/generated/ \
    --no-additionalProperties --style.singleQuote

# 3. JSON Schema -> Zod validators, so the browser enforces the same rules
npx json-schema-to-zod \
    --input  'packages/canonical-schemas/schemas/fathom.canonical/2/*.json' \
    --output packages/canonical-schemas/ts/src/generated/zod/

# 4. Both languages run the golden vectors; any disagreement fails the build
pytest packages/canonical-schemas/tests/test_vectors.py
npm --prefix packages/canonical-schemas/ts test
```

`emit-json-schema` uses `model_json_schema(mode="serialization")` and then attaches, from a hand-written table, the conditional constraints Pydantic cannot derive from a `model_validator`:

```python
# excerpt from src/fathom_schemas/_json_schema.py
CONDITIONAL_CONSTRAINTS = {
    "FailurePrediction": {
        # Document 03 §7.1  [D19].  Pydantic's `_rul_only_when_item_conditional`
        # validator is imperative; JSON Schema needs it declaratively so the
        # TypeScript side and the schema registry enforce the same rule.
        "allOf": [
            {
                "if": {"properties": {"reference_class": {"const": "item"}},
                       "required": ["reference_class"]},
                "then": {
                    "properties": {"rul": {"type": "object"},
                                   "population_hazard_rate": {"type": "null"}},
                    "required": ["rul"],
                },
                "else": {
                    "properties": {"rul": {"type": "null"},
                                   "population_hazard_rate": {"type": "number"}},
                    "required": ["population_hazard_rate"],
                },
            }
        ]
    },
    "EventEnvelope": {
        # Document 03 §5.4  [C11]: exactly one scope identifier, matching `scope`.
        "allOf": [
            {"if": {"properties": {"scope": {"const": scope}}, "required": ["scope"]},
             "then": {"properties": {"subject": {
                 "required": [field],
                 "properties": {other: {"type": "null"}
                                for other in _SUBJECT_FIELDS if other != field},
             }}}}
            for scope, field in _SCOPE_FIELD_PAIRS
        ]
    },
    "Proposal": {
        # Document 03 §7.2 rule 4  [D16].
        "allOf": [
            {"if": {"properties": {"blast_radius": {"enum": ["class", "fleet"]}}},
             "then": {"properties": {"requires_dual_control": {"const": True}}}},
            {"if": {"properties": {"kind": {"enum": ["requisition"]}}},
             "then": {"properties": {"requires_dual_control": {"const": True}}}},
        ]
    },
}
```

**A hand-maintained table is a divergence risk, and the golden-vector corpus is the mitigation.** Every conditional constraint must have at least one `invalid/` vector that trips it; `tests/test_conditional_coverage.py` fails if a key in `CONDITIONAL_CONSTRAINTS` has no vector exercising it.

Vector format:

```jsonc
// packages/canonical-schemas/vectors/FailurePrediction/invalid/rul_on_niin_fleet.json
{
  "_expect": {
    "rule": "FailurePrediction._rul_only_when_item_conditional",
    "source": "document 03 §7.1",
    "finding": "D19",
    "message_contains": "not item-conditional"
  },
  "instance": {
    "asset_id": "0f3d…", "installed_item_id": "…", "position_id": "…",
    "niin": "014567890", "equipment_family": "GTG-501K",
    "baseline_id": "…", "baseline_epoch": 7,
    "horizon_days": 90, "p_failure": 0.12,
    "reference_class": "niin_fleet", "sharpness": 0.4,
    "calibration_population": 220,
    "rul": {"p10": 30.0, "p50": 90.0, "p90": 210.0, "unit": "days"},
    "population_hazard_rate": 0.0011,
    "confidence": 0.6, "fallback_level": 1, "tier": 1,
    "contributing_factors": [],
    "model_version": "tier1-survival@3.2.0",
    "scoring_run_id": "…", "computed_at": "2026-07-01T04:00:00.000000Z"
  }
}
```

Both test suites read the same directory:

| Vector class | Python assertion | TypeScript assertion |
|---|---|---|
| `valid/*.json` | `Model.model_validate(instance)` succeeds **and** `wire_dict()` round-trips to a byte-identical `canonical_json()` | Zod `.parse()` succeeds and `JSON.stringify` of the parsed value, JCS-canonicalized, equals the Python `content_hash` recorded in a committed `hashes.json` |
| `invalid/*.json` | raises `ValidationError` whose message contains `_expect.message_contains` | Zod `.safeParse()` returns `success: false` |

The committed `hashes.json` — one SHA-256 per valid vector, produced by Python — is the actual byte-identity proof. If a TypeScript serializer formats a float differently, the hash differs and CI fails. This is the only test in the repository that can detect a cross-language wire-format fork.

---

## 5. `packages/contracts` — specification generation

### 5.1 The annotation decorator

Document 03 §4 requires OpenAPI 3.1 *"generated from code, published to the contracts package, validated in CI against the committed specification"*, and §4.1 requires *two* annotations on **every** operation, *"validated in CI"*:

| Annotation | Values | Purpose (document 03 §4.1) |
|---|---|---|
| `x-substitution` | `required` \| `internal` | Whether a substituting implementation must provide it (§10) |
| `x-side-effects` | `none` \| `proposal-only` \| `state-changing` | The basis for agent eligibility (§9.1 — see OQ-18 on that cross-reference) |

A third, optional annotation comes from §8.1: `x-agent-eligible`, which *"may be asserted only where `x-side-effects` is `none` or `proposal-only`"*.

> **Annotation model, confirmed against the current document 03.** The task brief asks whether `x-agent-eligible` still exists or has been superseded by the `x-side-effects` model. **It still exists, and both are required.** Document 03 §8.1 (current text) reads: *"Eligibility — a safety gate in the OpenAPI specification. `x-agent-eligible` may be asserted only where `x-side-effects` is `none` or `proposal-only` (§4.1). Validated in CI, so no manifest author can select a state-changing operation."* Obligation 8 in §15 repeats it: *"Declares `x-agent-eligible` only where `x-side-effects` is `none` or `proposal-only`."*
>
> What was superseded is **the basis for the gate**, not the annotation. Rev 1 gated agent eligibility on the **HTTP method**; C1/D11 found that this *"makes the `pdm-whatif` manifest listed in the same section impossible to build"* and *"Same defect blocks `POST /work-packages/plan` and `POST /scoring-runs`."* Rev 2 replaced the method check with the declared side-effect class. So: `x-side-effects` is the **gate condition**, `x-agent-eligible` is the **assertion the gate constrains**, and the two are not redundant — the gate says what *may* be eligible, the assertion says what *is*. A generator that treats `x-side-effects: none` as implying agent eligibility is wrong, because §8.1's two-level model deliberately separates eligibility from selection.

```python
# src/fathom_contracts/operation.py
"""The operation annotation decorator.  Document 03 §4.1 and §8.1.

Every operation on every sub-application and platform service is declared
through this decorator.  It does three things a raw `openapi_extra=` dict does
not:

1. Enforces the §8.1 gate AT IMPORT TIME, so a state-changing operation marked
   agent-eligible fails the service's own unit tests rather than waiting for the
   CI spec validation.
2. Registers the operation in a process-local registry, so `validate-openapi`
   can assert COMPLETENESS — that no operation was declared without the
   decorator.  A missing annotation is invisible to a checker that only reads
   the emitted document, because an un-annotated route simply has no extension
   key to find.
3. Records the source location, so a validation failure names the file and line
   rather than only the path and method.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable, TypeVar


class Substitution(StrEnum):
    """Document 03 §4.1 `x-substitution`.

    `required`: a substituting implementation MUST provide this operation
    (document 03 §10 requirement 1, "The `x-substitution: required` subset …
    including the `changed_since` snapshot reads of §4").
    `internal`: it need not.

    Document 05 C49: "04's substitution column values do not use 03's marker
    names."  These two values are the marker names.
    """

    REQUIRED = "required"
    INTERNAL = "internal"


class SideEffects(StrEnum):
    """Document 03 §4.1 `x-side-effects`.

    `none` "asserts the operation does not alter domain state.  It is permitted
    on `GET` and on computational `POST` operations such as scenario analysis
    and planning."

    "Agent eligibility is determined by declared side-effect class, NOT BY HTTP
    METHOD — a method check wrongly excludes the compute-only `POST` operations
    that three of the seven agents require  [C1, D11]."
    """

    NONE = "none"
    PROPOSAL_ONLY = "proposal-only"
    STATE_CHANGING = "state-changing"

    @property
    def agent_eligible_permitted(self) -> bool:
        """Document 03 §8.1 and §15 obligation 8: `x-agent-eligible` may be
        asserted only where `x-side-effects` is `none` or `proposal-only`."""
        return self in (SideEffects.NONE, SideEffects.PROPOSAL_ONLY)


@dataclass(frozen=True)
class OperationDeclaration:
    operation_id: str
    substitution: Substitution
    side_effects: SideEffects
    agent_eligible: bool
    summary: str
    source: str                      # "file.py:lineno", for error messages
    aggregate: str | None = None     # for the §4 changed_since completeness check
    singleton_carveout: str | None = None   # §4 Naming carve-out justification


REGISTRY: dict[str, OperationDeclaration] = {}
F = TypeVar("F", bound=Callable[..., Any])


def operation(
    *,
    operation_id: str,
    substitution: Substitution,
    side_effects: SideEffects,
    summary: str,
    agent_eligible: bool = False,
    aggregate: str | None = None,
    singleton_carveout: str | None = None,
) -> Callable[[F], F]:
    """Declare an operation's contract annotations.  Document 03 §4.1, §8.1.

    Usage on a FastAPI route:

        @router.post(
            "/what-if",
            operation_id="pdm_what_if",
            openapi_extra=operation_extra(
                operation_id="pdm_what_if",
                substitution=Substitution.REQUIRED,
                side_effects=SideEffects.NONE,      # computational POST  [C1]
                agent_eligible=True,                # pdm-whatif manifest, §8.2
                summary="Interactive tier-3 scenario analysis.",
            ),
        )
        async def what_if(...): ...

    `agent_eligible=True` with `side_effects=STATE_CHANGING` raises at import.
    """
    if agent_eligible and not side_effects.agent_eligible_permitted:
        raise ValueError(
            f"operation {operation_id!r}: `x-agent-eligible` may be asserted only "
            f"where `x-side-effects` is `none` or `proposal-only`; got "
            f"{side_effects.value!r}.  Document 03 §8.1 and §15 obligation 8.  "
            "This gate exists so 'no manifest author can select a state-changing "
            "operation'."
        )
    if operation_id in REGISTRY:
        raise ValueError(
            f"duplicate operationId {operation_id!r} (first declared at "
            f"{REGISTRY[operation_id].source})"
        )

    frame = inspect.stack()[1]
    declaration = OperationDeclaration(
        operation_id=operation_id,
        substitution=substitution,
        side_effects=side_effects,
        agent_eligible=agent_eligible,
        summary=summary,
        source=f"{frame.filename}:{frame.lineno}",
        aggregate=aggregate,
        singleton_carveout=singleton_carveout,
    )
    REGISTRY[operation_id] = declaration

    def decorate(func: F) -> F:
        func.__fathom_operation__ = declaration  # type: ignore[attr-defined]
        return func

    return decorate


def operation_extra(**kwargs: Any) -> dict[str, Any]:
    """The `openapi_extra=` payload.  Registers, gates, and returns the
    extension keys in one call, so the two cannot drift apart."""
    operation(**kwargs)
    declaration = REGISTRY[kwargs["operation_id"]]
    extra: dict[str, Any] = {
        "x-substitution": declaration.substitution.value,
        "x-side-effects": declaration.side_effects.value,
    }
    if declaration.agent_eligible:
        extra["x-agent-eligible"] = True
    if declaration.aggregate:
        extra["x-fathom-aggregate"] = declaration.aggregate
    if declaration.singleton_carveout:
        # Document 03 §4 Naming carve-out  [C23]: "singleton and query-projection
        # resources may be singular where no collection semantics exist, and MUST
        # BE ENUMERATED in the sub-application's specification."  Enumerating it
        # in the document itself, rather than in a side file, is what makes the
        # carve-out externally checkable.
        extra["x-fathom-singleton-carveout"] = declaration.singleton_carveout
    return extra
```

### 5.2 OpenAPI export

```python
# src/fathom_contracts/openapi/export.py
"""FastAPI app -> OpenAPI 3.1 document.  Document 03 §4.

FastAPI emits OpenAPI 3.1 natively and carries `openapi_extra` through to the
operation object, so the extensions of §4.1 need no post-processing.  What this
module adds is the DOCUMENT-LEVEL material document 03 requires and FastAPI does
not know about: the §4 base path, the RFC 9457 problem-details response shared
by every operation, and the deprecation headers of §4's deprecation policy.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fathom_schemas.slugs import AnySlug


def export(app: FastAPI, *, slug: AnySlug, major: int) -> dict[str, Any]:
    document = app.openapi()

    if document.get("openapi", "").split(".")[0] != "3" or not document[
        "openapi"
    ].startswith("3.1"):
        raise ValueError(
            f"document 03 §4 requires OpenAPI 3.1; app emitted "
            f"{document.get('openapi')!r}"
        )

    document["info"]["x-fathom-slug"] = str(slug)
    document["info"]["x-fathom-api-major"] = major
    document["servers"] = [{"url": f"/api/v{major}/{slug}"}]

    # Document 03 §4 Errors: "RFC 9457 problem details.  `type` is a stable URI;
    # `detail` is never used for control flow."  Declared once at the document
    # level and referenced by every operation, so nine services cannot each
    # invent an error shape.
    document.setdefault("components", {}).setdefault("schemas", {})[
        "ProblemDetails"
    ] = _PROBLEM_DETAILS_SCHEMA
    for path_item in document["paths"].values():
        for method, op in path_item.items():
            if method not in _HTTP_METHODS:
                continue
            op.setdefault("responses", {}).setdefault(
                "default",
                {
                    "description": "RFC 9457 problem details.  Document 03 §4.",
                    "content": {
                        "application/problem+json": {
                            "schema": {"$ref": "#/components/schemas/ProblemDetails"}
                        }
                    },
                },
            )
    return document


def write(document: dict[str, Any], path: str) -> None:
    """Deterministic serialization, so `git diff` on the committed spec shows
    only real contract changes.  Sorted keys and a trailing newline: an
    unstable serializer makes the §5.4 committed-spec gate produce noise, and a
    noisy gate is a disabled gate."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(document, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


_HTTP_METHODS = frozenset(
    {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
)
_PROBLEM_DETAILS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["type", "title", "status"],
    "properties": {
        "type": {"type": "string", "format": "uri",
                 "description": "A stable URI.  Document 03 §4."},
        "title": {"type": "string"},
        "status": {"type": "integer"},
        "detail": {"type": "string",
                   "description": "NEVER used for control flow.  Document 03 §4."},
        "instance": {"type": "string", "format": "uri"},
        "correlation_id": {"type": "string"},
    },
}
```

### 5.3 OpenAPI validation — the CI rule set

`fathom-contracts validate-openapi` implements every mechanically checkable convention in document 03 §4, §4.1, and §8.1. Each rule cites its source; each is a hard failure.

| Rule | Source | Check |
|---|---|---|
| `OAS001` | §4 Specification | Document is OpenAPI **3.1**, not 3.0 |
| `OAS002` | §4.1 | Every operation has `x-substitution` ∈ {`required`, `internal`} |
| `OAS003` | §4.1 | Every operation has `x-side-effects` ∈ {`none`, `proposal-only`, `state-changing`} |
| `OAS004` | §8.1, §15 obl. 8 | `x-agent-eligible: true` only where `x-side-effects` ∈ {`none`, `proposal-only`} |
| `OAS005` | §4.1 | Every operation was declared through `@operation` — the emitted set equals `REGISTRY` |
| `OAS006` | §4 Base path | Server URL is exactly `/api/v{major}/{slug}` with the slug a `SubAppSlug`/`PlatformServiceSlug` `[C25]` |
| `OAS007` | §4 Naming | Path segments are `kebab-case`; no `camelCase`, no underscores in paths |
| `OAS008` | §4 Naming | Resource collections are **plural**, unless the operation carries `x-fathom-singleton-carveout` `[C23]` |
| `OAS009` | §4 Naming | Every JSON property in every request/response schema is `snake_case` |
| `OAS010` | §4 Identity | Path parameters are canonical identifiers only; no `eic`, `equipment_id`, `hull_or_tail`, `nsn`, `eswbs`, `position_code` as a path identifier `[C2, C10]` |
| `OAS011` | §4 Identity | Version selectors are **query** parameters, never path identifiers `[C24]` |
| `OAS012` | §4 Sub-resource actions | `POST /{collection}/{id}/{action}` — action is a `kebab-case` verb; every such operation declares `x-side-effects` `[C24]` |
| `OAS013` | §4 Snapshot reads | For every `x-fathom-aggregate` a declared consumer projects (read from the AsyncAPI catalog), a `GET` exists accepting **both** `changed_since` and `cursor` `[D5, D25, D30]` |
| `OAS014` | §4 Pagination | Any collection `GET` accepts `limit` and `cursor` and returns `next_cursor`; no `total` on an unbounded collection |
| `OAS015` | §4 Idempotency | Every unsafe method accepts `Idempotency-Key` |
| `OAS016` | §4 Concurrency | `PUT`/`PATCH` require `If-Match`; updatable resources return `ETag` |
| `OAS017` | §4 Correlation | Every operation accepts `X-Correlation-Id` |
| `OAS018` | §4 Classification | Every response declares `X-Classification` |
| `OAS019` | §4 Errors | Every operation declares an `application/problem+json` response |
| `OAS020` | §4 Time | Every `date-time` property is documented as RFC 3339 with explicit offset |
| `OAS021` | §8.2 | Every `x-agent-eligible` operation has a non-empty `description` — manifest generation *fails* without one |
| `OAS022` | §4 Deprecation | A `deprecated: true` operation declares `Deprecation` and `Sunset` response headers |

```python
# src/fathom_contracts/openapi/validate.py  (excerpt: OAS004 and OAS013)
def check_oas004(document: dict) -> list[Finding]:
    """Document 03 §8.1: "`x-agent-eligible` may be asserted only where
    `x-side-effects` is `none` or `proposal-only` (§4.1).  Validated in CI, so no
    manifest author can select a state-changing operation."

    This is the single most important rule in the file.  C1/D11 record what
    happens when the gate is expressed as an HTTP-method check instead: the
    `pdm-whatif` manifest becomes unbuildable, along with
    `POST /work-packages/plan` and `POST /scoring-runs`.  The gate is on the
    DECLARED SIDE-EFFECT CLASS.  Never re-derive it from the method.
    """
    findings = []
    for path, item in document["paths"].items():
        for method, op in item.items():
            if method not in _HTTP_METHODS:
                continue
            if not op.get("x-agent-eligible"):
                continue
            side_effects = op.get("x-side-effects")
            if side_effects not in ("none", "proposal-only"):
                findings.append(
                    Finding(
                        code="OAS004",
                        location=f"{method.upper()} {path}",
                        message=(
                            f"x-agent-eligible asserted with "
                            f"x-side-effects={side_effects!r}.  Document 03 §8.1 "
                            "and §15 obligation 8 permit it only for 'none' or "
                            "'proposal-only'."
                        ),
                    )
                )
    return findings


def check_oas013(document: dict, consumed_aggregates: set[str]) -> list[Finding]:
    """Document 03 §4: "EVERY sub-application exposes
    `GET /{collection}?changed_since=&cursor=` over each aggregate a consumer
    maintains a read model of.  This is the REBUILD PATH; the event bus is not
    [D5, D25, D30]."

    `consumed_aggregates` comes from the committed AsyncAPI documents of the
    declared consumers in document 03 §6 — not from a hand-maintained list —
    because D5's defect was precisely that no sub-application exposed one and
    nobody noticed.
    """
    findings = []
    served = {
        op.get("x-fathom-aggregate")
        for item in document["paths"].values()
        for method, op in item.items()
        if method == "get"
        and {"changed_since", "cursor"} <= _param_names(op)
    }
    for aggregate in sorted(consumed_aggregates - served):
        findings.append(
            Finding(
                code="OAS013",
                location=f"aggregate:{aggregate}",
                message=(
                    f"aggregate {aggregate!r} is projected by a declared consumer "
                    "(document 03 §6) but no operation exposes "
                    "`?changed_since=&cursor=` over it.  Document 03 §4 makes this "
                    "the read-model rebuild path; retention is bounded and the "
                    "event bus is NOT a rebuild source (§5.1)  [D5, D25, D30]."
                ),
            )
        )
    return findings
```

### 5.4 The committed-specification gate and the compatibility differ

Document 03 §4 requires the specification be *"validated in CI against the committed specification"*. Two distinct checks, both in `openapi/diff.py`:

```
$ fathom-contracts check-committed --slug pdm --major 1
  reads:    services/pdm/  (imports the app, exports the spec)
  compares: packages/contracts/registry/apis/pdm/v1/openapi.json
  fails if: the exported document differs from the committed one at all

$ fathom-contracts check-compat --slug pdm --major 1 --base origin/main
  compares: the committed spec on this branch against the base ref
  fails if: a BREAKING change appears without a major-version bump
```

`check-committed` is a pure byte comparison and its failure message is *"run `make contracts` and commit the result"*. It exists so the committed spec cannot rot: the committed artifact is what conformance suites and manifest generation read, and a stale one silently tests the wrong contract.

`check-compat` implements document 03 principle 5 — *"Backward-compatible evolution by default; major versions for anything else. Additive optional fields require no version change. Removals, renames, type changes, and semantic changes require a new major version served alongside the prior one."*

| Change | Verdict | Rationale |
|---|---|---|
| New optional request field, new response field, new operation | **compatible** | Principle 5 |
| New required request field, removed operation, removed response field, narrowed type, narrowed enum, removed enum value from a *response* | **breaking** | Principle 5 |
| Added enum value to a *response* | **breaking** | The consumer's `extra="forbid"`-equivalent enum parse fails. Requires a major bump or a documented `unknown` fallback |
| Added enum value to a *request* | compatible | |
| `x-substitution` changed `internal` → `required` | **breaking for substitutes** | Widens §10's required subset; reported separately as `COMPAT-SUB` and requires an explicit `--allow-substitution-widening` flag plus a note in the sub-application's substitution posture |
| `x-side-effects` changed to `state-changing` | **breaking** | Revokes agent eligibility; any manifest selecting it must be re-versioned (§8.4) |
| `x-side-effects` changed *from* `state-changing` | flagged for review, not failed | Widening eligibility is a safety decision, not a compatibility one |

### 5.5 AsyncAPI export

Document 03 §5.5: *"AsyncAPI documents generate from the same source."* The same source is the event registry, declared in code beside the outbox publisher:

```python
# src/fathom_contracts/events.py
"""The event declaration registry.  Source for AsyncAPI generation and for the
schema-registry subject registration of §7.

Every field on `@event` corresponds to a document 03 requirement that is
otherwise unwritten anywhere machine-readable:
`partition_key` (§5.1), `compaction_key` (§5.1, [D5]), `retention` (§5.1),
`classification` (§5.1), `consumers` (§6), `scope` (§5.4).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Type

from fathom_schemas.envelope import EventScope
from fathom_schemas.slugs import AnySlug


class Retention(StrEnum):
    """Document 03 §5.1 Retention: "Seven days for high-volume derived streams;
    thirty days for domain events; compacted indefinite retention for
    state-carrying topics.  Retention is bounded DELIBERATELY, and THE EVENT BUS
    IS NOT A REBUILD SOURCE"  [D5]."""

    DERIVED_7D = "derived-7d"
    DOMAIN_30D = "domain-30d"
    COMPACTED_INDEFINITE = "compacted-indefinite"


@dataclass(frozen=True)
class EventDeclaration:
    event_type: str            # fathom.<slug>.<aggregate>.<verb>   §5.4
    aggregate: str             # the topic's aggregate token        §5.1
    major: int
    producer: AnySlug
    payload: Type[Any]         # a FathomModel subclass
    scope: EventScope          # §5.4
    partition_key: str         # §5.1
    compaction_key: str | None # §5.1  — MUST NOT equal partition_key  [D5]
    retention: Retention
    consumers: tuple[AnySlug, ...]   # §6; drives consumer-driven tests (§6.7)
    summary: str


REGISTRY: dict[str, EventDeclaration] = {}


def event(**kwargs: Any) -> EventDeclaration:
    """Declare a published event.

    Enforces the §5.1 rule that the compaction key is the AGGREGATE key, not the
    partition key: "Compacting on `asset_id` would collapse a hull's entire
    prediction history to a single record  [D5]."
    """
    declaration = EventDeclaration(**kwargs)
    if (
        declaration.compaction_key is not None
        and declaration.compaction_key == declaration.partition_key
    ):
        raise ValueError(
            f"{declaration.event_type}: compaction key equals partition key "
            f"({declaration.partition_key!r}).  Document 03 §5.1: the compaction "
            "key is the AGGREGATE key — `installed_item_id`, `(niin, location)`, "
            "or `baseline_id` — not the partition key.  D5: compacting the "
            "prediction topic on `asset_id` collapses it to one event per hull "
            "and discards every other item's predictions."
        )
    if (
        declaration.retention is Retention.COMPACTED_INDEFINITE
        and declaration.compaction_key is None
    ):
        raise ValueError(
            f"{declaration.event_type}: compacted retention requires a "
            "compaction key (document 03 §5.1)"
        )
    REGISTRY[declaration.event_type] = declaration
    return declaration
```

Declaration site, in the producing service:

```python
# services/pdm/events.py
from fathom_contracts.events import Retention, event
from fathom_schemas.envelope import EventScope
from fathom_schemas.slugs import SubAppSlug

PREDICTION_UPDATED = event(
    event_type="fathom.pdm.prediction.updated",
    aggregate="prediction",
    major=1,
    producer=SubAppSlug.PDM,
    payload=PredictionUpdatedPayload,   # references the run artifact  [D27]
    scope=EventScope.ASSET,
    partition_key="asset_id",           # §5.1: per-asset ordering within a topic
    compaction_key="installed_item_id", # §5.1: the AGGREGATE key  [D5]
    retention=Retention.COMPACTED_INDEFINITE,
    consumers=(
        SubAppSlug.FLEET_STATUS, SubAppSlug.MAINTENANCE, SubAppSlug.SUPPLY,
        SubAppSlug.DESIGN_ADVISORY, SubAppSlug.FAILURE_INTEL,
    ),                                   # document 03 §6, PdM table row 1
    summary="Scoring run reference and affected scope.  Document 03 §6.",
)
```

Export produces **AsyncAPI 3.0**, one document per producing service, with the envelope as a shared message trait so the §5.4 envelope cannot be restated per event:

```python
# src/fathom_contracts/asyncapi/export.py  (excerpt)
def export(slug: AnySlug) -> dict[str, Any]:
    """Event registry -> AsyncAPI 3.0.  Document 03 §5.5.

    Channel per topic (§5.1), message per event, envelope as a shared component
    (§5.4).  The Fathom-specific operational properties that document 03 fixes
    and AsyncAPI has no standard field for are carried as `x-fathom-*`
    extensions, so a substituting implementation reads them from the document
    rather than from prose.
    """
    declarations = [d for d in REGISTRY.values() if d.producer == slug]
    channels = {}
    for d in declarations:
        topic = topic_name(d.producer, d.aggregate, d.major)
        channels[topic] = {
            "address": topic,
            "messages": {d.event_type: {"$ref": f"#/components/messages/{_msg(d)}"}},
            "x-fathom-partition-key": d.partition_key,
            "x-fathom-compaction-key": d.compaction_key,
            "x-fathom-retention": d.retention.value,
            "x-fathom-scope": d.scope.value,
            # §5.1 Classification segregation: "A topic carries EXACTLY ONE
            # classification, declared in its registration."  For the
            # unclassified synthetic demonstration a single level is used and
            # this is STATED EXPLICITLY rather than implied to be multi-level
            # capable (§5.1, §12; document 06 §5)  [D13].
            "x-fathom-classification": "U",
            "x-fathom-declared-consumers": [str(c) for c in d.consumers],
        }
    ...
```

`fathom-contracts validate-asyncapi` adds four rules beyond schema validity:

| Rule | Source | Check |
|---|---|---|
| `ASY001` | §5.1 | Topic name matches `fathom.<slug>.<aggregate>.v<major>`; the slug is the producing service's own `[C26]` |
| `ASY002` | §5.1 | Compaction key ≠ partition key; compacted topics have a compaction key `[D5]` |
| `ASY003` | §5.1 | No topic appears in two services' documents — *"topics are never shared between producers"* |
| `ASY004` | §6 | Every declared consumer is a real `SubAppSlug`/`PlatformServiceSlug`, and **no consumer is an agent** — *"Agents are never direct topic consumers"* `[C19]` |

`ASY004` is the mechanical form of C19, which found the catalog listing *"consumers that exist nowhere ('governance reporting', 'PEO reporting', 'the originating agent's training corpus')"* and *"agents as direct event consumers, contradicting the rule that agents obtain state only through tools."* The existing `tools/check_event_catalog.py` reconciles the *documents*; `ASY004` reconciles the *code*.

---

## 6. `packages/contracts/conformance` — the test harness

### 6.1 What the harness is for

Document 03 §10 specifies `packages/contracts/conformance/<slug>/` containing five test categories plus a reference dataset. Document 03 principle 6: *"Every contract has an executable conformance suite, and every obligation in a contract is externally observable."*

D24 is the finding this structure exists to satisfy: *"No partner can pass the conformance suite. Several obligations — transactional outbox, inbox, per-log-line correlation IDs, owning exactly one database — are internal implementation properties unobservable from outside a black box and therefore unconformable by an executable suite. Either the obligation is unenforceable, or it is enforceable and no partner qualifies."*

The harness therefore tests **only** the §15 *contract terms* (obligations 1–10). It never tests obligations 11–16, the *program implementation standards*. Where an internal obligation exists to guarantee an observable property, the harness tests the property:

> Document 03 §10: *"For a substitute, the outbox obligation is replaced by the observable property it exists to guarantee: **no state change without a corresponding event**, verified by a fault-injection driver that interrupts the substitute mid-operation and asserts convergence. A partner platform emitting from an ontology or a change-feed can satisfy that; it will not implement our outbox, and no test could tell whether it had."*

That sentence is the specification for `FaultInjectionConformance` (§6.6).

### 6.2 The three protocols an implementation supplies

The harness is implementation-agnostic. It reaches the system under test through three protocols, which a program-built sub-application and a substituting partner implement differently and the tests cannot distinguish.

```python
# conformance/harness/drivers.py
"""The seams between the harness and any implementation.

A program-built sub-application implements these against its own Helm release;
a substituting partner implements them against its own deployment.  NOTHING in
the harness may import a service module, because a substitute has none.
"""
from __future__ import annotations

from typing import Iterator, Protocol, runtime_checkable

import httpx
from fathom_schemas.envelope import EventEnvelope


@runtime_checkable
class SystemUnderTest(Protocol):
    """The HTTP surface.  Document 03 §10 requirement 1."""

    slug: str
    api_major: int

    def client(self, *, identity: str = "conformance-operator") -> httpx.Client:
        """An authenticated client.

        `identity` selects a principal from the reference dataset's identity
        fixture, so authorization tests (§15 obligation 7 — "Enforces
        authorization LOCALLY against ABAC attributes, never relying solely on
        the gateway") can assert a 403 for an under-privileged caller.  The
        client MUST bypass the gateway: obligation 7 is about the
        sub-application's own enforcement.
        """
        ...

    def reset_to(self, dataset_name: str) -> None:
        """Load the named reference dataset.  Document 03 §10, "A reference
        dataset — synthetic Navy data sufficient for DETERMINISTIC runs."  """
        ...


@runtime_checkable
class EventTap(Protocol):
    """Read access to what the implementation published.  Document 03 §10
    requirement 2."""

    def consume(
        self, topic: str, *, since: int = 0, timeout_s: float = 30.0
    ) -> Iterator[tuple[int, int, EventEnvelope, dict]]:
        """Yield `(partition, offset, envelope, payload)`.

        Returning the partition is essential: document 03 §10's event tests
        assert "correct ordering WITHIN A PARTITION", and §5.1 states per-asset
        ordering "within a topic — which is the only ordering guarantee the
        design relies on"  [D4].  A tap that hides partitions cannot express the
        only guarantee there is.
        """
        ...

    def partition_for(self, topic: str, key: str) -> int: ...


@runtime_checkable
class FaultDriver(Protocol):
    """Mid-operation interruption.  Document 03 §10, fault-injection tests.

    The implementation chooses HOW it is interrupted — a pod kill, a broker
    partition, a proxy fault.  The harness only requires that the interruption
    land at the named point and that the implementation be restartable.
    """

    def interrupt_after_commit_before_publish(self) -> "FaultScope": ...
    def partition_from_broker(self) -> "FaultScope": ...
    def kill_and_restart(self) -> "FaultScope": ...


class FaultScope(Protocol):
    def __enter__(self) -> "FaultScope": ...
    def __exit__(self, *exc: object) -> bool: ...
    def await_convergence(self, timeout_s: float = 120.0) -> None:
        """Block until the implementation has finished recovering.  Convergence
        is what the fault tests assert, not the absence of the fault."""
        ...
```

### 6.3 The reference dataset

```python
# conformance/harness/dataset.py
"""Reference dataset loader.  Document 03 §10: "synthetic Navy data sufficient
for deterministic runs."

Content comes from `data/synthetic` and its own build document.  This module
defines only the INTERFACE, and the two properties conformance depends on:
determinism and canonical identity.

Scale per document 06 §7: 12 assets (5 surface, 3 subsurface, 4 unmanned),
~8,400 installed items, ~2,500 distinct NIINs, 6 spotlight equipment families,
~25,000 predictions per scoring run.  The conformance datasets are SUBSETS of
that corpus, named and pinned by content hash so a run is reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from uuid import UUID

from fathom_schemas.identity import AssetRef, InstalledItemRef, PartRef, PositionRef, SystemRef


@dataclass(frozen=True)
class ReferenceDataset:
    name: str
    content_hash: str        # pinned; a changed dataset is a changed test

    @cached_property
    def assets(self) -> tuple[AssetRef, ...]: ...
    @cached_property
    def installed_items(self) -> tuple[InstalledItemRef, ...]: ...

    def any_asset(self, *, domain: str | None = None) -> AssetRef:
        """A deterministic pick, not a random one.  Ordered by `asset_id`."""
        ...

    def installed_item_with_history(self) -> InstalledItemRef:
        """An item with at least one prior installation at the same position.

        Required by the C10 regression test: an implementation that conflates
        position and installed item passes every other test and fails only
        where a position has been occupied twice.
        """
        ...

    def provisional_installed_item(self) -> InstalledItemRef:
        """An edge-minted identity with `provisional: true`.  Document 03 §3.3
        final paragraph  [D8, D9]."""
        ...


DATASETS = {
    "minimal":  ReferenceDataset("minimal",  "sha256:…"),   # 1 asset, smoke
    "standard": ReferenceDataset("standard", "sha256:…"),   # 12 assets, doc 06 §7
    "edge":     ReferenceDataset("edge",     "sha256:…"),   # 1 SSN, doc 06 §4
}
```

### 6.4 Category 1 — contract tests

> Document 03 §10: *"**Contract tests** — every `x-substitution: required` operation against the specification, including errors, pagination, idempotency, and concurrency."*

```python
# conformance/harness/contract.py
"""Contract conformance.  Document 03 §10, category 1.

Tests §15 CONTRACT TERMS 1, 3, 4, 5, 6, 7 — the externally observable ones.
Never obligations 11-16  [D24].

Design: the required-operation sweep is GENERATED from the committed OpenAPI
document, not hand-written.  A hand-written sweep silently omits an operation
added later, and an omitted operation is exactly the substitution that "conforms
and still breaks a neighbor".
"""
from __future__ import annotations

import pytest
from fathom_schemas.classification import ClassificationLabel
from fathom_schemas.identity import CANONICAL_JOIN_KEYS

from .dataset import ReferenceDataset
from .drivers import SystemUnderTest


class ContractConformance:
    """Base class for `conformance/<slug>/test_contract.py`.

    A sub-application's suite subclasses it and supplies the two fixtures:

        class TestPdmContract(ContractConformance):
            slug = "pdm"
            api_major = 1

            @pytest.fixture(scope="session")
            def sut(self) -> SystemUnderTest:
                return PdmUnderTest(base_url=os.environ["PDM_URL"])

    Everything else is inherited.  Sub-applications add operation-specific
    tests as additional methods; they never re-implement the sweeps below.
    """

    slug: str
    api_major: int
    dataset_name: str = "standard"

    # -- fixtures -------------------------------------------------------
    @pytest.fixture(scope="session")
    def spec(self) -> dict:
        """The COMMITTED specification, from
        `packages/contracts/registry/apis/<slug>/v<major>/openapi.json`.

        Deliberately not the live `/openapi.json`: testing an implementation
        against its own emitted spec is a tautology.  §5.4's `check-committed`
        gate is what keeps the committed copy honest.
        """
        return load_committed_spec(self.slug, self.api_major)

    @pytest.fixture(scope="session")
    def required_operations(self, spec: dict) -> list[Operation]:
        """Document 03 §10 requirement 1: the `x-substitution: required`
        subset."""
        return [op for op in iter_operations(spec)
                if op.extensions["x-substitution"] == "required"]

    @pytest.fixture(scope="session")
    def dataset(self, sut: SystemUnderTest) -> ReferenceDataset:
        ds = DATASETS[self.dataset_name]
        sut.reset_to(ds.name)
        return ds

    # -- generated sweeps -----------------------------------------------
    def test_every_required_operation_is_reachable(self, sut, required_operations):
        """§10 req. 1.  A required operation that 404s is not a substitution."""

    def test_response_schemas_conform(self, sut, required_operations, spec):
        """Every 2xx response validates against its declared schema.  §15 obl. 1."""

    def test_canonical_identity_only(self, sut, required_operations, spec):
        """§15 obligation 3: "Accepts and returns canonical identifiers per §3.3."

        Asserts that every identifier-shaped property in a required response is
        a canonical join key, or is one of the human-reference fields §3.3
        permits — and that no response exposes `eic` or `equipment_id` as an
        identifier  [C2, C10].  This is the check no in-repo lint can perform
        against a partner implementation (§4.4, layer 3).
        """

    def test_classification_label_on_every_response(self, sut, required_operations):
        """§15 obligation 4 and §4: `X-Classification` on responses, and a
        parseable `ClassificationLabel` where a body carries one."""

    def test_correlation_id_propagates(self, sut, required_operations):
        """§15 obligation 6 and §4: `X-Correlation-Id` accepted, generated when
        absent, returned on the response.

        NOT tested: "Emits `X-Correlation-Id` on every log line" — that is §15
        obligation 15, a PROGRAM IMPLEMENTATION STANDARD, unobservable from
        outside a black box  [D24].
        """

    def test_problem_details_on_errors(self, sut, required_operations):
        """§4 Errors: RFC 9457, `type` a stable URI.  Asserts the media type is
        `application/problem+json` and that `type` is absolute."""

    def test_cursor_pagination(self, sut, required_operations):
        """§4 Pagination: `?limit=&cursor=`, `next_cursor` in the response, no
        total count on an unbounded collection.  Walks a full collection and
        asserts no duplicates and no gaps across pages."""

    def test_idempotency_key_honoured(self, sut, required_operations):
        """§4 Idempotency and §15 obl. 6: replaying an unsafe request with the
        same `Idempotency-Key` produces the same result and no second effect.

        Required "for any operation reachable from an agent proposal, a bulk
        write, or an edge sync" — which the harness identifies from
        `x-agent-eligible`, `x-fathom-bulk`, and the edge policy table.
        """

    def test_optimistic_concurrency(self, sut, required_operations):
        """§4 Concurrency and §15 obl. 6: `ETag` on updatable resources;
        `If-Match` required on PUT/PATCH; LOST UPDATES RETURN 412.

        Also covers §7.2 rule 3: adjudication requires `If-Match` on the claimed
        ETag  [D16].  The two-planner double-approval scenario is tested here
        rather than in the proposal-specific tests, because it is the generic
        concurrency property.
        """

    def test_changed_since_snapshot_read(self, sut, spec, dataset):
        """§15 obligation 5 and §4: "Exposes `changed_since` snapshot reads over
        every aggregate a declared consumer projects."

        THE REBUILD PATH  [D5, D25, D30].  Asserts three properties:
        completeness (a full walk with no `changed_since` returns every record in
        the dataset), monotonicity (a walk with `changed_since=T` returns exactly
        the records changed at or after T), and stability under concurrent write
        (a cursor walk does not skip a record modified mid-walk).

        Document 03 §10 requirement 5 makes this the write-cutover gate: "the
        substitute must be able to serve history through `changed_since`, or the
        program must retain the incumbent's event archive in object storage
        indefinitely.  Without one of these, write cutover leaves every consumer
        unable to rebuild"  [D25].
        """

    def test_local_authorization_enforcement(self, sut, required_operations):
        """§15 obligation 7: "Enforces authorization LOCALLY against ABAC
        attributes, NEVER RELYING SOLELY ON THE GATEWAY."

        Calls the sub-application directly, bypassing the gateway, with an
        under-privileged identity, and asserts 403.  Observable, therefore a
        contract term.
        """

    def test_singleton_carveouts_are_enumerated(self, spec):
        """§4 Naming carve-out  [C23]: singular resources "must be enumerated in
        the sub-application's specification."  Asserts every singular collection
        segment carries `x-fathom-singleton-carveout` with a non-empty
        justification."""
```

### 6.5 Category 2 — event tests

> Document 03 §10: *"**Event tests** — a driver asserting specified domain actions produce specified events with correct envelopes and keys, and correct ordering *within a partition*."*

```python
# conformance/harness/events.py
"""Event conformance.  Document 03 §10, category 2.

Tests §15 contract term 2 ("Emits an event for every state change reachable
through its contract") and §10 requirement 2 (envelope, catalog payload schemas,
declared partition key, at-least-once semantics).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest
from fathom_schemas.envelope import EventEnvelope

from .drivers import EventTap, SystemUnderTest


@dataclass(frozen=True)
class ActionEventExpectation:
    """One row of a sub-application's event-emission table.

    A sub-application's suite declares these; the harness executes them.  The
    declaration is the machine-readable form of document 03 §6's catalog, and
    `tools/check_event_catalog.py` already reconciles the catalog against
    document 04 — this reconciles it against RUNNING CODE.
    """

    name: str
    action: Callable[[SystemUnderTest], None]
    expected_event_type: str
    expected_topic: str
    expected_partition_key_field: str
    expected_payload_fields: frozenset[str]


class EventConformance:
    """Base class for `conformance/<slug>/test_events.py`.

        class TestPdmEvents(EventConformance):
            slug = "pdm"
            expectations = (
                ActionEventExpectation(
                    name="bulk prediction write publishes prediction.updated",
                    action=lambda sut: post_bulk_predictions(sut),
                    expected_event_type="fathom.pdm.prediction.updated",
                    expected_topic="fathom.pdm.prediction.v1",
                    expected_partition_key_field="asset_id",
                    expected_payload_fields=frozenset(
                        {"scoring_run_id", "affected_scope"}   # [D27]
                    ),
                ),
                …
            )
    """

    slug: str
    expectations: tuple[ActionEventExpectation, ...] = ()

    @pytest.fixture(scope="session")
    def tap(self) -> EventTap: ...

    # -- parametrized over `expectations` -------------------------------
    def test_action_produces_event(self, sut, tap, expectation):
        """§15 contract term 2.  The action runs; the event appears."""

    def test_envelope_validates(self, sut, tap, expectation):
        """Every published envelope parses as `EventEnvelope`.

        Because `FathomModel` forbids extra fields, this also asserts the
        producer added no undeclared envelope member — which is how a
        second dialect of the envelope would otherwise enter the system.
        """

    def test_partition_key_as_declared(self, sut, tap, expectation):
        """§5.1: `asset_id` for asset-scoped events, guaranteeing per-asset
        ordering WITHIN A TOPIC — "the only ordering guarantee the design relies
        on"  [D4].  Fleet-, NIIN-, and class-scoped events partition on their own
        scope identifier."""

    def test_ordering_within_partition(self, sut, tap, expectation):
        """§10: "correct ordering WITHIN A PARTITION."

        Drives N sequential actions against ONE scope identifier and asserts the
        consumed order matches, and that `clock.monotonic_seq` increases
        monotonically.  Deliberately does NOT assert cross-partition or
        cross-topic order: §5.1 forbids depending on it, so a test that asserted
        it would fail a conformant implementation  [D4].
        """

    def test_clock_block_present_and_disciplined(self, sut, tap, expectation):
        """§5.4.  Asserts `clock.monotonic_seq` is present and increasing,
        `clock.hlc` is well-formed, and `clock.sync_quality` is fully populated
        including `step_occurred` and `dispersion_ms`  [D29].

        Additionally asserts that `source_time` is NOT the ordering key, by
        publishing two events whose `source_time` is inverted (the driver steps
        the producing node's clock backwards, reproducing STIG V-260520's
        `makestep 1 -1`) and asserting the consumer-visible order still follows
        `monotonic_seq`.  This is the only test in the suite that reproduces the
        actual STIG behavior document 03 §5.4 cites.
        """

    def test_at_least_once_idempotent_on_event_id(self, sut, tap, expectation):
        """§5.2: "At-least-once delivery.  Every consumer is idempotent on
        `event_id`.  Exactly-once is assumed nowhere."

        Redelivers a consumed event and asserts the implementation's state is
        unchanged.  Tests the CONSUMER half of the contract, so it runs against
        sub-applications in their consumer role.
        """

    def test_baseline_epoch_carried_where_configuration_dependent(self, sut, tap):
        """§5.4 and §3.3 rule 5: "Every payload referencing configuration carries
        `baseline_id` and `baseline_epoch`"  [D3, D4]."""

    def test_antecedent_rule(self, sut, tap):
        """§5.4: "A consumer that receives an event with an epoch AHEAD OF its
        own configuration read model MUST BLOCK that event until the antecedent
        configuration event is applied."

        Delivers a prediction at epoch N+1 while withholding the
        `configuration.baseline_changed` at epoch N+1, and asserts the consumer
        neither applies it nor drops it — it blocks, and applies on arrival of
        the antecedent.  This closes D4: "`causation_id` exists but no consumer
        rule uses it and no consumer can block on an unseen antecedent."
        """

    def test_replay_events_marked_and_side_effect_free(self, sut, tap):
        """§5.3: backfill produces events marked `replay: true`; consumers "must
        ignore or handle `replay: true` events idempotently and MUST NOT raise
        operator-visible alerts from them"  [D30].

        Drives a backfill with `X-Backfill: true` and asserts (a) every resulting
        event carries `replay: true`, and (b) no notification, work candidate, or
        requisition is generated — the three side effects §5.3 names.
        """
```

### 6.6 Category 3 — fault-injection tests

> Document 03 §10: *"**Fault-injection tests** — interruption mid-operation, asserting no state change without its event."*

This is the category that makes the substitution protocol usable at all, per D24. The outbox (§15 obligation 11) is a program implementation standard; **the property it guarantees is the contract term.**

```python
# conformance/harness/faults.py
"""Fault-injection conformance.  Document 03 §10, category 3.

Document 03 §10: "For a substitute, the outbox obligation is replaced by the
observable property it exists to guarantee: NO STATE CHANGE WITHOUT A
CORRESPONDING EVENT, verified by a fault-injection driver that interrupts the
substitute mid-operation and asserts convergence.  A partner platform emitting
from an ontology or a change-feed can satisfy that; it will not implement our
outbox, and no test could tell whether it had."

Every test here is written in terms of CONVERGENCE, never in terms of a
mechanism.  A test that asserted "an outbox row exists" would be D24's defect
reintroduced.
"""
from __future__ import annotations

import pytest

from .drivers import EventTap, FaultDriver, SystemUnderTest


class FaultInjectionConformance:
    """Base class for `conformance/<slug>/test_faults.py`.

        class TestPdmFaults(FaultInjectionConformance):
            slug = "pdm"
            state_changing_operations = ("pdm_bulk_write_predictions", …)

            @pytest.fixture(scope="session")
            def faults(self) -> FaultDriver:
                return HelmPodFaultDriver(release="fathom-pdm")
    """

    slug: str
    state_changing_operations: tuple[str, ...] = ()

    @pytest.fixture(scope="session")
    def faults(self) -> FaultDriver: ...

    def test_no_state_change_without_its_event(self, sut, tap, faults, operation_id):
        """§15 contract term 2, verified by fault injection.

        Parametrized over `state_changing_operations`.  For each:

        1. Read the pre-state through the contract.
        2. Enter `interrupt_after_commit_before_publish()`.
        3. Invoke the operation.
        4. Await convergence.
        5. Assert: EITHER the state change is absent AND no event was published,
           OR the state change is present AND its event was published.

        The forbidden outcome — state changed, no event — is the one that leaves
        every consumer's read model permanently wrong with no rebuild trigger.
        The permitted outcomes are both fine; the implementation chooses.
        """

    def test_convergence_after_broker_partition(self, sut, tap, faults, operation_id):
        """The same property under a broker partition rather than a process kill.

        Document 03 §5.2's outbox exists to survive exactly this; a substitute's
        change-feed must too.  Asserts the event appears after the partition
        heals, with its ORIGINAL `event_id` — a re-minted `event_id` breaks every
        consumer's idempotency (§5.2).
        """

    def test_inbox_semantics_survive_a_crash(self, sut, tap, faults):
        """§5.2: "Inbox: record and apply in one transaction.  The `event_id`
        record and the resulting state change commit TOGETHER.  Where that is
        impossible, the inbox row carries `processed_at` and ONLY ROWS WITH
        `processed_at` SET SUPPRESS REDELIVERY.  Recording receipt BEFORE
        processing is PROHIBITED."

        D2 in full: "a crash between recording and committing the state change
        makes the event permanently suppressed on redelivery.  Applied to
        `configuration.baseline_changed`, predictions for a replaced item are
        never invalidated — precisely the outcome document 04 calls the failure
        most likely to destroy operator trust, INTRODUCED BY THE INBOX RULE
        ITSELF."

        Test: deliver `configuration.baseline_changed`; kill the consumer between
        receipt and application; restart; REDELIVER the same event; assert the
        state change is applied.  An implementation that recorded receipt first
        will suppress the redelivery and fail.

        Observable, therefore a contract term — even though the inbox mechanism
        (§15 obligation 12) is not.
        """

    def test_idempotent_retry_after_interruption(self, sut, faults, operation_id):
        """§4 Idempotency.  Replay with the same `Idempotency-Key` after an
        interruption produces one effect, not two."""

    def test_no_orphaned_reservation_after_partial_failure(self, sut, faults):
        """D6, for `supply` and `maintenance` only.

        D6: "37 of 40 reservations succeed, the 38th fails, orphans persist and
        37 spurious availability events degrade every other asset's planning."
        Asserts a failed reservation set leaves no partial reservation and emits
        no availability change.  Declared here rather than in the sub-application
        suite because the compensating-release property is a contract term of
        §6's `reservation_set.released`.
        """
```

### 6.7 Category 4 — consumer-driven tests

> Document 03 §10: *"**Consumer-driven tests** — contributed by each declared consumer in §6, asserting the guarantees that consumer depends upon. These catch the substitution that conforms and still breaks a neighbor."*

C3 is why this category is structurally hard: *"**21 consumers declared in the 03 event catalog are not shown consuming in 04.** Each is an unbuildable consumer-driven conformance test."* The harness therefore makes the *absence* of a contributed expectation a failure, not a silent pass.

```python
# conformance/harness/consumers.py
"""Consumer-driven conformance.  Document 03 §10, category 4.

Layout — the consumer OWNS the file, inside the producer's suite directory:

    packages/contracts/conformance/pdm/consumers/
        fleet-status/test_expectations.py     # owned by services/fleet-status
        maintenance/test_expectations.py      # owned by services/maintenance
        supply/test_expectations.py
        design-advisory/test_expectations.py
        failure-intel/test_expectations.py

CODEOWNERS assigns each directory to the consuming service's team, so a producer
cannot weaken a neighbor's expectation without that neighbor's review.  This is
the only mechanism in the framework that gives a consumer a veto.
"""
from __future__ import annotations

import pytest
from fathom_contracts.events import REGISTRY as EVENT_REGISTRY

from .drivers import EventTap, SystemUnderTest


class ConsumerDrivenConformance:
    """Base class for `conformance/<producer>/consumers/<consumer>/test_expectations.py`.

        class TestFleetStatusExpectationsOfPdm(ConsumerDrivenConformance):
            producer = "pdm"
            consumer = "fleet-status"

            depends_on_events = (
                "fathom.pdm.prediction.updated",
                "fathom.pdm.prediction.invalidated",
                "fathom.pdm.criticality_tier.assigned",
                "fathom.pdm.model_binding.activated",
            )
            depends_on_operations = ("pdm_list_predictions", "pdm_get_provenance")

            def test_invalidation_carries_epoch(self, tap):
                '''Fleet Status displays invalidated predictions as such
                (document 04 §4) and needs the epoch to decide whether its own
                read model is behind.  Document 03 §6:
                `prediction.invalidated` carries "affected scope, cause,
                `baseline_epoch`".'''
                ...
    """

    producer: str
    consumer: str
    depends_on_events: tuple[str, ...] = ()
    depends_on_operations: tuple[str, ...] = ()

    # -- automatic, from the declarations ------------------------------
    def test_declared_dependencies_exist(self, spec):
        """Every event in `depends_on_events` is in the producer's AsyncAPI
        document, and every operation in `depends_on_operations` is in the
        producer's committed OpenAPI document AND is `x-substitution: required`.

        A consumer depending on an `internal` operation is a C4-class
        undeclared dependency: "Four events consumed in 04 by sub-applications
        the catalog does not declare as consumers — undeclared dependencies that
        a conformant substitution would break."
        """

    def test_consumer_is_declared_in_the_catalog(self):
        """The inverse direction: this consumer appears in the producer's
        `event.consumers` tuple for every event in `depends_on_events`.

        Closes the C4 direction that `tools/check_event_catalog.py` checks
        between documents, here between code and code.
        """


def collect_missing_consumer_suites() -> list[tuple[str, str]]:
    """Every (producer, consumer) pair declared in document 03 §6 — via the
    `@event(consumers=…)` registry — that has NO suite directory.

    `test_no_declared_consumer_lacks_a_suite` fails on a non-empty result.  This
    is the mechanical guard on C3's 21 unbuildable tests: a declared consumer
    with no contributed expectations is a declared dependency nobody has
    written down, and it will be discovered at substitution time instead.

    Platform services that bridge to agents (`notification`, `audit`, `gateway`)
    are in scope: C19 established that where "a downstream capability is realized
    by an agent, the consumer named here is the PLATFORM COMPONENT that bridges
    to it."  Their expectations are thinner but they are not exempt.
    """
    missing = []
    for declaration in EVENT_REGISTRY.values():
        for consumer in declaration.consumers:
            path = (
                f"packages/contracts/conformance/{declaration.producer}"
                f"/consumers/{consumer}/test_expectations.py"
            )
            if not exists(path):
                missing.append((str(declaration.producer), str(consumer)))
    return sorted(set(missing))
```

### 6.8 Category 5 — manifest tests

> Document 03 §10: *"**Manifest tests** — per §8.4."*
> Document 03 §8.4: *"Each manifest ships a conformance test asserting its declared behavior matches actual API behavior — every selected operation exists and is eligible, descriptions accurately characterize returns, parameter defaults are valid, result projections match response schemas. Manifest tests run inside the sub-application conformance suite (§10), so a conformant substitution is automatically a conformant tool surface."*

```python
# conformance/harness/manifests.py
"""Manifest conformance.  Document 03 §10 category 5, specified by §8.4.

The tests live in the SUB-APPLICATION's suite, not in `agent-tooling`, because
§8.4's payoff is "a conformant substitution is automatically a conformant tool
surface" — which requires the manifest assertions to run against the substitute.
"""
from __future__ import annotations

import pytest
from fathom_agent_tooling.manifest import ToolManifest, load_manifests_for


class ManifestConformance:
    """Base class for `conformance/<slug>/test_manifests.py`.

        class TestPdmManifests(ManifestConformance):
            slug = "pdm"
            api_major = 1
            # Document 03 §8.2: "Predictive Maintenance backs AT LEAST THREE
            # manifests over one unchanged API."
            expected_minimum_manifests = 3
    """

    slug: str
    api_major: int
    expected_minimum_manifests: int = 0

    @pytest.fixture(scope="session")
    def manifests(self) -> tuple[ToolManifest, ...]:
        """Every manifest under `packages/agent-tooling/manifests/<slug>/`
        pinned to `api_major`."""
        return load_manifests_for(self.slug, self.api_major)

    def test_selected_operations_exist(self, manifests, spec):
        """§8.4: "every selected operation exists".  §8.2: generation FAILS —
        rather than warns — when a selected operation is absent from the pinned
        API version."""

    def test_selected_operations_are_agent_eligible(self, manifests, spec):
        """§8.4 and §8.1: every selected operation carries
        `x-agent-eligible: true`, and therefore `x-side-effects` ∈ {`none`,
        `proposal-only`}.

        This is the substitution-safety property: a substitute that marks an
        operation `state-changing` where the incumbent marked it `none` fails
        HERE, before any agent can call it  [C1, D11].
        """

    def test_descriptions_accurately_characterize_returns(self, manifests, spec, sut):
        """§8.4: "descriptions accurately characterize returns."

        Mechanically checkable part only: every field named in a task-scoped
        description exists in the operation's response schema, and every
        REQUIRED response field is either described or explicitly projected
        away.  Semantic accuracy is an agent-evaluation concern (document 01
        §8.8), not a conformance one, and this test does not claim to check it.
        """

    def test_parameter_defaults_are_valid(self, manifests, spec, sut):
        """§8.4: "parameter defaults are valid."  Every default validates against
        the parameter's schema AND is accepted by the live operation — a default
        that satisfies the schema and 422s at runtime is the failure mode."""

    def test_result_projections_match_response_schemas(self, manifests, spec):
        """§8.4: "result projections match response schemas."  Every JSON pointer
        in a projection resolves against the declared response schema."""

    def test_no_state_changing_operation_reachable(self, manifests, spec):
        """The negative form of the §8.1 gate, asserted from the manifest side.

        Together with `OAS004` (§5.3) this is defense in depth: OAS004 stops a
        service from mis-declaring, this stops a manifest from mis-selecting.
        """

    def test_expected_manifest_count(self, manifests):
        """§8.2 names three PdM manifests explicitly: `pdm-fleet-triage`
        (broad, ranked, read-heavy), `pdm-equipment-deepdive` (narrow,
        provenance-rich), and `pdm-whatif` (interactive scenario, using the
        `x-side-effects: none` computational operation)."""
```

### 6.9 Registration and invocation

```python
# conformance/harness/plugin.py
"""pytest plugin.  Registered in packages/contracts/pyproject.toml:

    [project.entry-points.pytest11]
    fathom_conformance = "fathom_contracts.conformance.harness.plugin"

Supplies the parametrization for the generated sweeps, the `--fathom-*` options,
and the JUnit + markdown conformance report a substituting partner submits as
evidence of a "conformance run" (document 03 §10 requirement 6).
"""
```

```bash
# A program-built sub-application, in its own CI:
pytest packages/contracts/conformance/pdm \
       --fathom-base-url=http://fathom-pdm.fathom-sustainment.svc:8080 \
       --fathom-broker=redpanda.fathom-data.svc:9092 \
       --fathom-dataset=standard \
       --fathom-report=out/conformance-pdm.md

# A substituting partner, against their own deployment:
fathom-conformance run --slug supply \
       --sut-plugin partner_supply_driver \
       --dataset standard \
       --categories contract,events,faults,consumers,manifests \
       --report out/conformance-supply.md
```

The report enumerates all five categories with per-test results and, critically, **lists any category that did not run**. A partner submitting a run with `faults` skipped has not submitted a conformance run: §10's fault-injection category is the one that replaces the unconformable outbox obligation, so skipping it removes the only evidence that "no state change without its event" holds.

### 6.10 What the harness deliberately does not test

| §15 obligation | Category | Why not |
|---|---|---|
| 11 — transactional outbox | Program implementation standard | Unobservable from outside a black box. The **property** is tested by §6.6 `test_no_state_change_without_its_event` `[D24]` |
| 12 — consumer inbox | Program implementation standard | Mechanism unobservable; the **redelivery-suppression property** is tested by §6.6 `test_inbox_semantics_survive_a_crash` `[D2]` |
| 13 — one logical database | Program implementation standard | Unobservable. Enforced instead by NetworkPolicy default-deny (document 01 §11) and an in-repo check, not by conformance `[D33]` |
| 14 — read-model lag exposure | **Partly a contract term** | `/readyz` and `/metrics` are HTTP surfaces, so lag exposure *is* observable and *is* tested in §6.4. The internal refusal-to-compute behavior is not `[D6]` |
| 15 — `X-Correlation-Id` on every log line | Program implementation standard | Log format is not a contract surface |
| 16 — declared conflict policy | Program implementation standard | Declaration is a document, not an operation |

---

## 7. `packages/agent-tooling` — manifest generation

### 7.1 The two-level model, restated precisely

Document 03 §8.1 defines two levels, and conflating them is the defect this package prevents:

| Level | Where it lives | Who decides | Changing it |
|---|---|---|---|
| **Eligibility** — a safety gate | The OpenAPI specification: `x-agent-eligible`, permitted only where `x-side-effects` ∈ {`none`, `proposal-only`} | The sub-application, validated in CI (`OAS004`, §5.3) | Requires an API change |
| **Selection** — a tuning decision | A manifest: a subset of eligible operations, with task-scoped descriptions, parameter defaults, result shaping | *"the consuming agent's decision and requires no API change"* | Requires only a manifest version |

Document 01 §8.0 supplies the reason the relationship is one-to-many: *"tool descriptions occupy prompt space. A manifest tuned to a task outperforms a generic one, and the one-to-many relationship means agent tuning never requires an API change. That decoupling is the substantive benefit."*

### 7.2 The manifest schema

Document 03 §8.2 fixes the path and the field set:

```
packages/agent-tooling/manifests/<slug>/<manifest-name>.v<major>.yaml
```

| Field | Purpose (document 03 §8.2, verbatim) |
|---|---|
| `name`, `version` | Manifest identity, versioned independently of the API |
| `target` | Sub-application slug and the API major version written against |
| `owner` | Consuming agent, or `curated` for shared manifests |
| `purpose` | Task or persona served; reviewed for overlap |
| `operations[]` | Selected operation identifiers with task-scoped description, parameter defaults, optional result projection |

```python
# src/fathom_agent_tooling/manifest.py
"""The tool-manifest schema.  Document 03 §8.2, transcribed exactly.

Five fields, no more.  A sixth field would be a private extension to a
published artifact, and §8.5 records that "because manifests generate from
published contracts, THIRD PARTIES may develop tool surfaces against these
sub-applications without program involvement" — which requires the manifest
format to be as published and as stable as the OpenAPI document.
"""
from __future__ import annotations

import re
from typing import Any, Self

from fathom_schemas._base import FathomModel, NonEmptyStr
from fathom_schemas.slugs import SubAppSlug
from pydantic import Field, model_validator

MANIFEST_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
"""kebab-case, matching the names document 03 §8.2 gives: `pdm-fleet-triage`,
`pdm-equipment-deepdive`, `pdm-whatif`.  The filename is
`<manifest-name>.v<major>.yaml`, so the name must not contain a dot."""

CURATED = "curated"
"""Document 03 §8.2 `owner`: "Consuming agent, or `curated` for shared
manifests."  §8.4: "shared manifests are marked `curated` and maintained
centrally", and "an UNOWNED manifest is DELETED rather than inherited."  """


class ManifestTarget(FathomModel):
    """Document 03 §8.2 `target`: "Sub-application slug and the API major
    version written against."

    §8.4: "Manifest version and API major version are INDEPENDENT.  An agent
    artifact pins BOTH, plus its prompt and model version, promoted together as
    one registered unit."
    """

    slug: SubAppSlug = Field(description="Slug from document 03 §3.1  [C27].")
    api_major: int = Field(
        ge=1,
        description=(
            "The API major version this manifest is written against.  Document "
            "03 §8.2, §8.4.  Generation FAILS if a selected operation is absent "
            "from THIS version — not from the latest version."
        ),
    )


class ManifestOperation(FathomModel):
    """Document 03 §8.2 `operations[]`: "Selected operation identifiers with
    task-scoped description, parameter defaults, optional result projection."  """

    operation_id: NonEmptyStr = Field(
        description=(
            "The `operationId` from the target's committed OpenAPI document.  "
            "Not a path and method: an operationId survives a path change, and "
            "§8.2 requires generation to fail when the operation is ABSENT, "
            "which requires a stable identifier to be absent."
        )
    )
    description: NonEmptyStr = Field(
        description=(
            "TASK-SCOPED description.  Document 03 §8.2.  Generation FAILS when "
            "an operation 'lacks a description' — including when it inherits the "
            "API's own summary, because document 01 §8.0's argument is that a "
            "generic description underperforms: 'tool descriptions occupy prompt "
            "space.  A manifest tuned to a task outperforms a generic one.'"
        )
    )
    parameter_defaults: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Document 03 §8.2.  Validated against the parameter schemas at "
            "generation time and against the live operation by the §6.8 manifest "
            "conformance test."
        ),
    )
    result_projection: tuple[NonEmptyStr, ...] = Field(
        default=(),
        description=(
            "OPTIONAL result shaping, as RFC 6901 JSON pointers into the "
            "operation's response schema.  Document 03 §8.2.  Every pointer must "
            "resolve, per §8.4's 'result projections match response schemas'."
        ),
    )


class ToolManifest(FathomModel):
    """Document 03 §8.2 manifest.  The complete field set."""

    name: NonEmptyStr = Field(
        pattern=MANIFEST_NAME_RE.pattern,
        description="Manifest identity.  Document 03 §8.2.",
    )
    version: int = Field(
        ge=1,
        description=(
            "Manifest MAJOR version, versioned INDEPENDENTLY of the API.  "
            "Document 03 §8.2, §8.4.  Must equal the `v<major>` token in the "
            "filename."
        ),
    )
    target: ManifestTarget = Field(description="Document 03 §8.2.")
    owner: NonEmptyStr = Field(
        description=(
            "Consuming agent, or `curated` for shared manifests.  Document 03 "
            "§8.2.  §8.4: 'manifests are owned, and an unowned manifest is "
            "DELETED rather than inherited.'  A non-curated owner must name a "
            "directory under `agents/` (document 01 §11)."
        )
    )
    purpose: NonEmptyStr = Field(
        min_length=40,
        description=(
            "Task or persona served; REVIEWED FOR OVERLAP.  Document 03 §8.2, "
            "§8.4 proliferation controls.  The minimum length is a deliberate "
            "friction: a one-word purpose cannot be reviewed for overlap, which "
            "is the control's whole function."
        ),
    )
    operations: tuple[ManifestOperation, ...] = Field(
        min_length=1, description="Document 03 §8.2."
    )

    @model_validator(mode="after")
    def _no_duplicate_operations(self) -> Self:
        ids = [o.operation_id for o in self.operations]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            raise ValueError(
                f"operation selected more than once: {sorted(duplicates)}"
            )
        return self

    @property
    def descriptor_path(self) -> str:
        """`packages/agent-tooling/generated/<slug>/<name>.v<major>.mcp.json`."""
        return (
            f"packages/agent-tooling/generated/{self.target.slug}/"
            f"{self.name}.v{self.version}.mcp.json"
        )

    @property
    def manifest_path(self) -> str:
        """Document 03 §8.2:
        `packages/agent-tooling/manifests/<slug>/<manifest-name>.v<major>.yaml`."""
        return (
            f"packages/agent-tooling/manifests/{self.target.slug}/"
            f"{self.name}.v{self.version}.yaml"
        )
```

Example manifest, transcribing the third of the three PdM manifests document 03 §8.2 names:

```yaml
# packages/agent-tooling/manifests/pdm/pdm-whatif.v1.yaml
# Document 03 §8.2: "`pdm-whatif` (interactive scenario, using the
# `x-side-effects: none` computational operation)".  This manifest is the
# concrete artifact C1/D11 found unbuildable under the rev-1 HTTP-method gate:
# every operation it needs is a POST.
name: pdm-whatif
version: 1
target:
  slug: pdm
  api_major: 1
owner: diagnostic          # agents/diagnostic (document 01 §11)
purpose: >
  Interactive tier-3 what-if scenario analysis for a single installed item
  during a diagnostic conversation with a maintainer. Narrow and interactive:
  the operator names a hypothetical usage or configuration change and the agent
  reports the resulting prediction shape. Distinct from pdm-equipment-deepdive,
  which is retrospective and provenance-rich rather than hypothetical.
operations:
  - operation_id: pdm_what_if
    description: >
      Compute a hypothetical failure prediction for one installed item under a
      stated usage or configuration scenario. Returns p_failure with its
      reference_class, and rul ONLY when reference_class is "item"; otherwise
      returns population_hazard_rate. Never present rul for a non-item
      reference class, and never compare p_failure across reference classes.
    parameter_defaults:
      horizon_days: 90
    result_projection:
      - /p_failure
      - /reference_class
      - /sharpness
      - /rul
      - /population_hazard_rate
      - /confidence
      - /fallback_level
      - /contributing_factors
  - operation_id: pdm_get_prediction
    description: >
      Retrieve the current operational prediction for an installed item, to
      contrast against a what-if result. Read-only.
```

Two things about that description are load-bearing and are checked (§7.5): it states the `rul` conditionality of §7.1 `[D19]`, and it forbids cross-reference-class comparison `[D7]`. `contributing_factors` is projected but the description does not license causal phrasing — document 03 §7.1: *"agents must not render them in causal language — a causal statement must cite an adjudicated Failure Intelligence hypothesis"* `[D23]`.

### 7.3 The eligibility reader

```python
# src/fathom_agent_tooling/eligibility.py
"""The §8.1 eligibility gate, read from a committed OpenAPI document.

This module is the ONLY place in the package that decides whether an operation
may be selected.  It reads `x-agent-eligible` and re-checks it against
`x-side-effects`, rather than trusting the flag alone: a spec that passed an
older `validate-openapi` could carry an inconsistent pair, and generation is the
last gate before an agent can call the operation.

IT NEVER LOOKS AT THE HTTP METHOD.  C1/D11: "Agent eligibility is determined by
declared side-effect class, NOT BY HTTP METHOD — a method check wrongly excludes
the compute-only `POST` operations that three of the seven agents require."
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Ineligibility(StrEnum):
    ABSENT = "operation-absent-from-pinned-api-version"
    NOT_ELIGIBLE = "not-marked-x-agent-eligible"
    STATE_CHANGING = "x-side-effects-forbids-eligibility"
    NO_DESCRIPTION = "operation-lacks-a-description"


@dataclass(frozen=True)
class EligibilityVerdict:
    operation_id: str
    eligible: bool
    reason: Ineligibility | None
    detail: str


def assess(spec: dict, operation_id: str) -> EligibilityVerdict:
    """Document 03 §8.1, §8.2, and §15 obligation 8."""
    op = find_operation(spec, operation_id)
    if op is None:
        return EligibilityVerdict(
            operation_id, False, Ineligibility.ABSENT,
            f"{operation_id!r} is not in the pinned API version.  Document 03 "
            "§8.2: generation FAILS — rather than warns — when a selected "
            "operation is absent from the pinned API version.",
        )
    side_effects = op.get("x-side-effects")
    if side_effects not in ("none", "proposal-only", "state-changing"):
        return EligibilityVerdict(
            operation_id, False, Ineligibility.STATE_CHANGING,
            f"{operation_id!r} declares x-side-effects={side_effects!r}, which is "
            "not one of the three values in document 03 §4.1.  Every operation "
            "declares this annotation, validated in CI.",
        )
    if not op.get("x-agent-eligible"):
        return EligibilityVerdict(
            operation_id, False, Ineligibility.NOT_ELIGIBLE,
            f"{operation_id!r} is not marked `x-agent-eligible`.  Document 03 "
            "§8.1 separates ELIGIBILITY (a safety gate in the specification, the "
            "sub-application's decision) from SELECTION (a tuning decision in a "
            "manifest).  A manifest cannot assert its own eligibility; "
            f"x-side-effects={side_effects!r} may make the operation ELIGIBLE-ABLE "
            "but the sub-application must assert it.",
        )
    if side_effects == "state-changing":
        return EligibilityVerdict(
            operation_id, False, Ineligibility.STATE_CHANGING,
            f"{operation_id!r} asserts `x-agent-eligible` with "
            "x-side-effects='state-changing'.  Document 03 §8.1 and §15 "
            "obligation 8 permit the assertion only for 'none' or "
            "'proposal-only'.  The specification is defective; fix it there, not "
            "here.  (`validate-openapi` OAS004 should have caught this.)",
        )
    if not (op.get("description") or "").strip():
        return EligibilityVerdict(
            operation_id, False, Ineligibility.NO_DESCRIPTION,
            f"{operation_id!r} lacks a description.  Document 03 §8.2: generation "
            "FAILS when a selected operation lacks a description.",
        )
    return EligibilityVerdict(operation_id, True, None, "")
```

### 7.4 MCP descriptor emission

```python
# src/fathom_agent_tooling/descriptors.py
"""MCP-style tool descriptors.  Document 03 §8.2: "Generation emits MCP-style
descriptors".

Served by `platform/tool-server`, the Sustainment Plane platform service that
exists because "Domino provides no MCP registry, discovery, or governance
(document 02 §4.2)"  [C17].
"""
from __future__ import annotations

from typing import Any

from fathom_schemas._base import FathomModel, NonEmptyStr
from pydantic import Field


class McpToolDescriptor(FathomModel):
    """One MCP tool.  Name, description, JSON Schema input, plus the Fathom
    provenance an ungoverned MCP descriptor would omit."""

    name: NonEmptyStr = Field(
        description=(
            "`<slug>__<operation_id>` — the slug prefix prevents collision when "
            "one agent loads manifests from several sub-applications, which the "
            "one-to-many model in document 01 §8.0 makes normal."
        )
    )
    description: NonEmptyStr = Field(
        description="The manifest's TASK-SCOPED description, not the API summary."
    )
    inputSchema: dict[str, Any] = Field(
        description=(
            "JSON Schema derived from the operation's parameters and request "
            "body, with the manifest's `parameter_defaults` applied as schema "
            "`default` keywords and the defaulted parameters removed from "
            "`required`."
        )
    )
    # -- Fathom governance extensions -----------------------------------
    x_fathom_target: dict[str, Any] = Field(
        description="Slug and API major version.  Document 03 §8.2 `target`."
    )
    x_fathom_operation_id: NonEmptyStr
    x_fathom_side_effects: NonEmptyStr = Field(
        description=(
            "Copied from the specification so the tool server can refuse a call "
            "whose declared class changed since generation.  Document 03 §8.1."
        )
    )
    x_fathom_manifest: dict[str, Any] = Field(
        description=(
            "Manifest name, version, and owner.  Document 03 §8.4: an agent "
            "artifact pins BOTH manifest version and API major version, plus its "
            "prompt and model version, 'promoted together as one registered "
            "unit'."
        )
    )
    x_fathom_result_projection: tuple[str, ...] = ()
    x_fathom_authority: dict[str, Any] = Field(
        description=(
            "The §8.3 constraint carried to the call site.  For `proposal-only` "
            "and `none` operations an ACCOUNTABLE AUTONOMOUS agent may call; "
            "anything else requires DELEGATED authority.  §8.3 also requires "
            "that Domino Endpoint calls be PROXIED through a Sustainment Plane "
            "service that attaches caller identity, because 'a Domino Endpoint "
            "authenticates with a static token carrying no caller identity and "
            "no per-caller audit trail'  [D12]."
        )
    )
```

### 7.5 The generator and its failure modes

Document 03 §8.2: *"Generation emits MCP-style descriptors and **fails** — rather than warns — when a selected operation is absent from the pinned API version, is not `x-agent-eligible`, or lacks a description."*

```
$ fathom-manifest --help

  validate  <manifest.yaml>...        Schema + eligibility, no output written
  generate  <manifest.yaml>...        Emit MCP descriptors to generated/
  generate --all                      Every manifest under manifests/
  check-generated                     Committed descriptors match a fresh run
  emit-conformance <manifest.yaml>    Write the §8.4 per-manifest test
  overlap [--slug SLUG]               §8.4 proliferation report
  orphans                             Manifests whose `owner` is not an agent dir
```

Failure modes. **Every row is an exit code, not a warning.** There is no `--warn-only` flag and adding one is a violation of this document.

| Exit | Condition | Source |
|---|---|---|
| `0` | Success | |
| `10` | Manifest fails its own schema (missing field, bad `name`, `purpose` under 40 chars, empty `operations[]`) | §8.2 |
| `11` | Filename disagrees with `name`/`version`, or the directory disagrees with `target.slug` | §8.2 path form |
| `12` | **Selected operation absent from the pinned API version** | §8.2, verbatim |
| `13` | **Selected operation is not `x-agent-eligible`** | §8.2, verbatim |
| `14` | **Selected operation lacks a description** | §8.2, verbatim |
| `15` | `x-agent-eligible` asserted with `x-side-effects: state-changing` — the *specification* is defective | §8.1, §15 obl. 8 |
| `16` | A `parameter_defaults` key is not a parameter of the operation, or its value fails the parameter schema | §8.4 |
| `17` | A `result_projection` pointer does not resolve against the response schema | §8.4 |
| `18` | Committed OpenAPI document for `target` is missing, or is not the pinned major version | §4, §8.2 |
| `19` | `owner` is neither `curated` nor a directory under `agents/` — *"an unowned manifest is deleted rather than inherited"* | §8.4 |
| `20` | Duplicate `operation_id` within one manifest | §8.2 |
| `21` | `check-generated`: committed descriptor differs from a fresh generation | §4 pattern, applied to manifests |

```python
# src/fathom_agent_tooling/generate.py  (excerpt: the failure discipline)
def generate(manifest_path: str, *, write: bool = True) -> int:
    """Document 03 §8.2.  Returns an exit code; raises nothing on contract
    failure, so the CLI can report every failure in one run rather than
    stopping at the first.

    There is deliberately no `strict=False` parameter.  §8.2 says generation
    FAILS rather than warns, and the reason is in §8.1: the gate exists "so no
    manifest author can select a state-changing operation."  A warning is a gate
    that a hurried author steps over.
    """
    manifest = ToolManifest.model_validate(read_yaml(manifest_path))
    _assert_path_agrees(manifest, manifest_path)          # exit 11

    spec = load_committed_spec(manifest.target.slug, manifest.target.api_major)
    if spec is None:
        return report(18, f"no committed OpenAPI document for "
                          f"{manifest.target.slug} v{manifest.target.api_major}")

    failures: list[tuple[int, str]] = []
    descriptors = []
    for selected in manifest.operations:
        verdict = assess(spec, selected.operation_id)
        if not verdict.eligible:
            failures.append((_EXIT_FOR[verdict.reason], verdict.detail))
            continue
        failures.extend(_check_parameter_defaults(spec, selected))   # 16
        failures.extend(_check_result_projection(spec, selected))    # 17
        descriptors.append(build_descriptor(spec, manifest, selected))

    if failures:
        for code, detail in failures:
            report(code, detail)
        return max(code for code, _ in failures)

    if write:
        write_json(manifest.descriptor_path, descriptors)
        emit_conformance_test(manifest)                   # §8.4, into §6.8's suite
    return 0
```

### 7.6 Proliferation controls

Document 03 §8.4: *"Proliferation controls: every manifest declares a `purpose` reviewed for overlap; manifests are owned, and an unowned manifest is deleted rather than inherited; shared manifests are marked `curated` and maintained centrally."*

```python
# src/fathom_agent_tooling/overlap.py
"""The §8.4 proliferation report.

Overlap is REVIEWED, not gated: document 03 §8.4 says purposes are "reviewed for
overlap", and document 01 §8.0 establishes that overlapping manifests over one
API are the INTENDED design — "One API, one contract, three manifests differing
in operation subset, descriptions, and parameter defaults."  A gate on operation
overlap would forbid the design.  So `overlap` reports; only `orphans` fails.
"""

def overlap_report(slug: str | None = None) -> OverlapReport:
    """For each pair of manifests on the same target, report:

    - Jaccard similarity of their selected operation sets.
    - Whether their `purpose` statements share a distinguishing clause.
    - A HIGH-OVERLAP flag at >= 0.8 operation similarity, which is the
      threshold at which two manifests are plausibly one manifest with two
      parameter-default sets.

    Emitted as a markdown table into the PR that adds a manifest, so the
    "reviewed for overlap" obligation has an artifact.
    """


def orphans() -> list[str]:
    """Manifests whose `owner` is neither `curated` nor a directory under
    `agents/`.

    Document 03 §8.4: "an UNOWNED MANIFEST IS DELETED RATHER THAN INHERITED."
    This function is a HARD FAILURE in CI (exit 19), because inheritance by
    default is how a manifest outlives the agent that justified it and then
    constrains an API change nobody can trace to a consumer.
    """
```

---

## 8. Schema registry and compatibility enforcement

### 8.1 What document 03 requires

Document 03 §5.5, in full: *"Payload schemas live in `packages/canonical-schemas`, publish as versioned Python and TypeScript libraries, and **register in a schema registry enforcing compatibility on publish**. AsyncAPI documents generate from the same source. **A producer cannot publish an event whose payload fails registry validation.**"*

Two distinct obligations, and they need two mechanisms:

1. **Compatibility enforced on publish** — a *schema-evolution* gate. Belongs in CI, where a human can read the failure and decide whether to bump a major version.
2. **A producer cannot publish an event whose payload fails registry validation** — a *runtime* gate. Belongs at the serializer, in the producing process.

### 8.2 Chosen technology

**Runtime gate: Redpanda's built-in Schema Registry, with JSON Schema subjects.**

Document 01 §11 already deploys *"Redpanda operator, Kafka API. Single-binary operation suits the demonstration and remains air-gap-friendly."* Redpanda embeds a Confluent-API-compatible Schema Registry in the broker itself. Choosing it means:

- **Zero new components.** No Confluent Platform, no separate Karapace deployment, no additional Helm release, no additional NetworkPolicy, no additional database. At the demonstration scale of document 06 §7 — 12 assets, ~5M telemetry samples/day, ~25,000 predictions per scoring run, <20 agent proposals/day — a standalone registry deployment would be pure operational overhead.
- **Air-gap compatible,** which document 01 §12 makes a structural seam and document 05 D26 identifies as an area where platform assumptions have already failed once.
- **The subject-per-topic model matches §5.1's topic-per-aggregate-per-producer rule** one-to-one. Subject naming: `<topic>-value`, e.g. `fathom.pdm.prediction.v1-value`, with `fathom.pdm.prediction.v1-key` registered as a plain string.
- **JSON Schema rather than Avro or Protobuf.** Document 03 §4 fixes JSON bodies and `snake_case` fields on the API, §7.x expresses every shared schema as JSON-shaped, and the TypeScript half of §5.5's dual publication consumes JSON Schema. Introducing Avro would mean a second schema language, a second code generator, and a second wire encoding — three new divergence surfaces to solve a problem this system does not have.
- Compatibility level set to **`BACKWARD_TRANSITIVE`** per subject, which matches document 03 principle 5's "backward-compatible evolution by default" and the §4 deprecation policy's requirement that a superseded major be served *"for a minimum of two release cycles"* — transitive, not merely pairwise, because a consumer two versions behind is explicitly in scope.

**Compatibility gate: `fathom-contracts check-compat`, in CI, over the committed JSON Schema artifacts.**

The registry's own compatibility checker is necessary but not sufficient, for three specific reasons:

| Rule the registry cannot enforce | Why |
|---|---|
| `rul` present iff `reference_class == "item"` (§7.1 `[D19]`) | JSON Schema `if/then/else` compatibility is not part of any registry's subset-comparison algorithm; a registry will accept a change that inverts the condition |
| Exactly one `subject` identifier matching `scope` (§5.4 `[C11]`) | Same reason |
| `requires_dual_control` forced true at class/fleet blast radius (§7.2 `[D16]`) | Same reason |
| `dissemination[]` closed to the ten LDCs (§7.3) | A registry treats adding an enum value to a *response* as backward-compatible; for a closed authorized list it is a policy change requiring review |
| `x-substitution: internal` → `required` (§10) | Not a payload change at all; it widens the substitution obligation |

So the CI differ is where the real enforcement lives, and the registry is the runtime fail-closed. Both read **the same committed JSON Schema artifacts** under `packages/canonical-schemas/schemas/`, so there is one source and no possibility of the two disagreeing.

```python
# packages/contracts/src/fathom_contracts/registry/publish.py
"""Subject registration.  Document 03 §5.5.

Run as a CI step after `check-compat` passes, and as a Helm pre-upgrade hook for
the producing service — the same discipline document 01 §11 applies to database
migrations, and for the same reason: a service must not start able to publish a
schema the registry has not accepted.
"""
from __future__ import annotations

COMPATIBILITY_LEVEL = "BACKWARD_TRANSITIVE"
"""Document 03 principle 5 plus the §4 deprecation policy: a superseded major is
served for at least two release cycles, so a consumer two versions behind is in
scope and pairwise BACKWARD is insufficient."""


def register_all(registry_url: str, *, dry_run: bool = False) -> list[Registration]:
    """Register one subject per declared event, from the §5.5 event registry.

    Subject name: `<topic>-value`, where the topic is built by
    `fathom_schemas.topics.topic_name` — never by string concatenation at the
    call site, so C26's inconsistent qualification cannot recur.

    Fails closed: a registration rejected by the registry aborts the deployment.
    """
```

```python
# packages/contracts/src/fathom_contracts/registry/compat.py
"""The compatibility rules the registry cannot express.

Run by `fathom-contracts check-compat` against the base ref's committed
schemas.  Every rule cites the document 03 section whose invariant it protects.
"""

CONDITIONAL_INVARIANTS = {
    # (schema, jsonpath-ish description, document 03 section, finding)
    ("FailurePrediction", "if reference_class==item then rul required and "
     "population_hazard_rate null", "§7.1", "D19"),
    ("FailurePrediction", "if reference_class!=item then rul null and "
     "population_hazard_rate required", "§7.1", "D19"),
    ("EventEnvelope", "exactly one subject identifier matching scope",
     "§5.4", "C11"),
    ("Proposal", "blast_radius in {class,fleet} implies requires_dual_control",
     "§7.2", "D16"),
    ("Proposal", "kind==requisition implies requires_dual_control",
     "§7.2/§11", "D16"),
    ("ClassificationLabel", "dissemination closed to the ten authorized LDCs",
     "§7.3", "D13"),
}
"""Each entry must have a corresponding golden vector in
`packages/canonical-schemas/vectors/`, and `check-compat` fails if the
conditional block that expresses it was REMOVED or WEAKENED between refs.

The check is structural, not semantic: it asserts the `allOf`/`if`/`then` block
is still present with the same branch conditions.  A weakened branch is the
change that silently reintroduces D19 while every ordinary compatibility check
passes, because relaxing a conditional requirement IS backward-compatible in
JSON Schema terms and is a contract violation in document 03's terms."""
```

### 8.3 Where the runtime gate sits

```
producing service
  └── domain transaction ─── outbox row (§5.2, program-built only)
        └── outbox relay
              ├── 1. serialize payload via fathom_schemas  (extra="forbid")
              ├── 2. JSON-Schema-validate against the registered subject
              │        ← FAIL CLOSED: "A producer cannot publish an event whose
              │          payload fails registry validation" (§5.5).  A failure
              │          leaves the outbox row unpublished and alerts; it does
              │          NOT drop the row, because the state change already
              │          committed and §15 term 2 requires the event.
              └── 3. produce to fathom.<slug>.<aggregate>.v<major>
```

A validation failure at step 2 is a **deployment defect**, not a data error: the schema was registered from the same source that serialized the payload. Its correct handling is to halt publication for that subject and alert, which is why the relay treats it as a poison-message condition with an operator-visible metric rather than a retry loop.

### 8.4 Rejected alternative, recorded

A full Confluent Schema Registry or a standalone Karapace deployment was considered and rejected: it adds a Helm release, a NetworkPolicy, a leader-election dependency, and an air-gap image-mirroring obligation, in exchange for compatibility checking that §8.2 shows is insufficient for this contract anyway. If the program later moves off Redpanda, the seam is `registry/publish.py` and the Confluent-compatible REST API, which both Redpanda and Karapace implement — so the substitution is a URL change.

---

## 9. Versioning and publication mechanics

### 9.1 The requirement

Nine services, plus eight platform services, plus `agents/*`, `models/*`, and `apps/web`, consume `packages/canonical-schemas`. **They must be able to upgrade at different times.** A purely path-based workspace import makes every consumer upgrade atomically at the moment the package changes, which means:

- A change to `FailurePrediction` cannot be merged until all nine services are ready, so the change never merges.
- Or it merges and breaks nine services at once, so nobody dares change it, and the schemas fossilize while the services accumulate local workarounds — which is the drift this package exists to prevent, arriving by the opposite route.

### 9.2 Chosen mechanism: versioned artifacts from an internal package registry

**Not** path-based workspace imports. `packages/canonical-schemas` is built into a wheel and an npm tarball, published to the monorepo's Git-forge package registry, and consumed by version range.

The registry is **whatever package registry the forge hosting this monorepo provides** (GitHub Packages, GitLab Package Registry, or a self-hosted Forgejo/Gitea — all three speak both the PyPI simple-index and npm protocols). Justification:

- **No new component.** Argo CD already reconciles from this monorepo (document 01 §11), so a Git forge exists.
- **Auth is inherited** from the forge, so no additional secret class in External Secrets Operator.
- **Mirrorable for air gap** — the seam is an index URL, and document 01 §12 makes air-gap a structural requirement.

Fallback if no forge registry is available: a PEP 503 static index in the MinIO bucket document 01 §11 already deploys, plus npm tarball URLs pinned by `integrity` hash. Recorded so the choice is not a blocker.

### 9.3 Exact consumer configuration

Python consumer — `services/pdm/pyproject.toml`:

```toml
[project]
name = "fathom-pdm"
requires-python = ">=3.12"
dependencies = [
  # Caret-equivalent range.  Document 03 principle 5: additive optional fields
  # require no version change, so a minor bump is always safe to accept; a MAJOR
  # bump is a contract change that this service must adopt deliberately.
  "fathom-canonical-schemas>=2.3,<3",
  "fathom-contracts>=2.1,<3",
]

[[tool.uv.index]]
name = "fathom"
url = "https://forge.internal/api/packages/fathom/pypi/simple"
explicit = true          # only the packages routed below come from here

[tool.uv.sources]
fathom-canonical-schemas = { index = "fathom" }
fathom-contracts = { index = "fathom" }
```

`uv.lock` is committed per service, so the *resolved* version is exact and reproducible while the *declared* range permits independent upgrade. A service upgrades by running `uv lock --upgrade-package fathom-canonical-schemas` — one file changes, one service is affected.

TypeScript consumer — `apps/web/package.json`:

```json
{
  "dependencies": {
    "@fathom/canonical-schemas": "^2.3.0"
  }
}
```

with `.npmrc` at the repo root:

```
@fathom:registry=https://forge.internal/api/packages/fathom/npm/
```

Package version — `packages/canonical-schemas/pyproject.toml`:

```toml
[project]
name = "fathom-canonical-schemas"
version = "2.3.0"

[tool.fathom]
# The SCHEMA major version, which is the wire contract's major version.  It is
# the same integer as the package major version, deliberately: document 03
# principle 5 ties a wire-breaking change to a major version, and having two
# different majors (package vs schema) would make "which schema does 2.3.0 ship"
# a question requiring a lookup table.
schema_major = 2
```

### 9.4 The rules that keep independence from becoming drift

Independent upgrade without a bound is just drift with extra steps. Four gates:

| Gate | Rule | Enforced by |
|---|---|---|
| **Range shape** | Every consumer declares `>=X.Y,<X+1` (Python) / `^X.Y.Z` (npm). A pinned exact version (`==2.3.0`) or an unbounded range (`>=2.3`) both fail | `tools/check_dependency_ranges.py`, CI |
| **Minor-lag bound** | No service may be more than **one minor version** behind the latest published minor for more than **14 days**. A weekly automated bump PR per service is opened by the dependency bot; the gate fails the *package* repo's CI, not the service's, so the pressure lands on whoever is publishing | CI job `schema-lag`, running against the registry index |
| **Major adoption** | A new **major** is published alongside the prior one and the prior major is not unpublished until all nine services have adopted. This mirrors document 03 §4's deprecation policy — *"served for a minimum of two release cycles after its successor reaches general availability"* — and the same rule applies to the topic major version: `fathom.pdm.prediction.v1` and `.v2` coexist | `tools/check_major_adoption.py`, plus per-version call metrics per §4 |
| **Import direction** | `canonical-schemas` imports nothing from the monorepo; `contracts` imports only `canonical-schemas`; no service is importable by another service | `import-linter` contracts in `pyproject.toml`, CI |

```ini
# packages/canonical-schemas/pyproject.toml  — import-linter contracts
[tool.importlinter]
root_packages = ["fathom_schemas", "fathom_contracts", "fathom_agent_tooling"]

[[tool.importlinter.contracts]]
name = "canonical-schemas depends on nothing in the monorepo"
type = "forbidden"
source_modules = ["fathom_schemas"]
forbidden_modules = ["fathom_contracts", "fathom_agent_tooling", "fastapi",
                    "sqlalchemy", "confluent_kafka", "httpx"]
# Rationale: `canonical-schemas` must import in a Domino Job container, in the
# edge runtime, and in the synthetic-data generator, none of which have a web
# framework, a database driver, or a Kafka client.  D26 records that the Domino
# application runtime installs packages at pod start, so a heavy dependency tree
# is a platform blocker rather than an inconvenience.

[[tool.importlinter.contracts]]
name = "layered packages"
type = "layers"
layers = ["fathom_agent_tooling", "fathom_contracts", "fathom_schemas"]
```

### 9.5 Release process

```
1.  Edit the Pydantic model.  Add or extend a golden vector.
2.  make schemas          # regenerate JSON Schema, TypeScript, Zod, hashes.json
3.  make check-compat     # against origin/main; classifies the change
4.  Bump version in pyproject.toml + ts/package.json:
      patch  — docstrings, validators made STRICTER only where the stricter rule
               was always implied by document 03 (rare; requires a citation)
      minor  — additive optional field, new type, new helper
      major  — anything document 03 principle 5 calls breaking
5.  PR.  CI runs: vectors (both languages), check-compat, import-linter,
    flake8 --select=FTH, the nine services' conformance suites against the
    NEW package (a cross-repo canary, not a merge gate)
6.  Merge -> tag `canonical-schemas/v2.4.0` -> publish wheel + tarball
7.  Dependency bot opens nine bump PRs.  The `schema-lag` gate tracks them.
```

Step 5's cross-service canary is advisory rather than blocking, deliberately: making it blocking recreates the atomic-upgrade problem §9.1 rejects. Its value is that a breaking change is *visible* at authoring time, with named failing services, rather than discovered by each service separately two weeks later.

---

## 10. Explicit DO-NOT list

Every item here is a defect that was found, dispositioned, and fixed. This package's shape *is* the fix. An implementer who "corrects" the shape back reintroduces the defect, and the review findings are cited so the reasoning is recoverable without re-litigating it.

### 10.1 Identity and naming

| Do not | Because | Guard |
|---|---|---|
| Use `eic` as a join key, a dictionary key, a merge key, or a foreign key | **C2.** Document 01 §7's use of `eic` as a join key *"violates 03 §4's own identity rule"*, and *"the approved artifact is the non-conformant one."* NAVSEAINST 4790.8 App. A makes EIC *"a 7-character code"* whose leading characters identify system, subsystem, and equipment category — **a class code of variable specificity**, explicitly *"Where the EIC is known to more than four digits, it should be recorded at that level."* Two different physical pumps share an EIC | `FTH001`; `ContractConformance.test_canonical_identity_only` |
| Introduce a field named `equipment_id` | **C10.** *"No canonical identifier exists for `InstalledItem` … It is undefined whether `equipment_id` identifies the position-bound slot or the physical item."* The ambiguity *is* the defect. Use `installed_item_id` for the physical item, `position_id` for the location. Note that document 04 §4's API surface still shows `GET /predictions?asset_id=&equipment_id=` — **document 04 is remediation tranche 3 and is not yet corrected; do not copy it** | `FTH001`; `OAS010` |
| Attach RUL, usage accumulation, or failure history to a position | **C10, D9.** *"A pump at position 233-04-A may be replaced five times over a hull's life; conflating the two makes a new component inherit its predecessor's degradation"* (document 01 §6). D9: max-merge on position *"would credit a new item with its predecessor's hours"* | `FTH001`; `ReferenceDataset.installed_item_with_history` |
| Use `hull_or_tail`, `eswbs`, `position_code`, or `nsn` as a join key | **§3.3 rule 1**: *"external systems reissue and reformat them"* | `FTH001`; `OAS010` |
| Write a hull number with a hyphen | **§3.3**, quoting SECNAVINST 5030.8D Encl 6: *"Hyphens will not be used in the hull number of any ship or craft."* The sole exception is a leading `T-` for Military Sealift Command | `AssetRef._no_hyphen_in_hull` |
| Invent an integer identifier for a sub-application | **C9.** *"Three incompatible integer identities exist for the same nine sub-applications."* The slug is the only identifier | `SubAppSlug` has no integer |
| Spell a sub-application any way but §3.1 | **C27, C28.** Seven of nine had two or more spellings; four schemes referenced a canonical identifier that did not exist | `SubAppSlug`; `OAS006`; `ASY001` |
| Use `equipment`, `component`, `subsystem`, `slot`, `sub_app`, or a bare `endpoint` in an identifier | **C29.** Six labels for the component level; *"'Endpoint' carries two unrelated meanings with no disambiguation."* An HTTP route is an **operation**; a Domino inference deployment is a **Domino Endpoint**, always qualified | `FTH002` |

### 10.2 Schemas

| Do not | Because | Guard |
|---|---|---|
| Rename `contributing_factors` back to `drivers` | **D23.** *"`drivers[]` cannot be produced honestly. At tier 2, attributions over correlated channels are unidentified and will reorder run to run on unchanged data. At tier 3 the field reads as causal and the Maintainer Copilot renders it as a reason — an unadjudicated back channel delivering causal claims to the deckplate."* The rename came with three new required fields; a rename back drops them. Document 04 §4 still says *"the fallback level exposed in `confidence` and in `drivers`"* — **stale, tranche 3** | `FTH003`; `extra="forbid"` |
| Drop `attribution_method`, `stability`, or `observation_ref` | **D23.** They are what make the attribution honest. `observation_ref` replaced `evidence_ref` because *"`evidence_ref` is unsatisfiable for a model-internal attribution"* | required fields on `ContributingFactor` |
| Render a contributing factor in causal language | **§7.1, D23.** *"a causal statement must cite an adjudicated Failure Intelligence hypothesis"* | manifest description review (§7.5); agent evaluation gate |
| Fold `fallback_level` back into `confidence` | **D7.** *"`confidence` is overloaded to carry both sharpness and cold-start fallback depth — one scalar cannot carry both and stay orderable"* | separate fields; `extra="forbid"` |
| Emit `rul` for a non-item reference class | **D19.** *"Tier 0 is defined as the random-failure population, i.e. Weibull β≈1, i.e. memoryless — so conditional residual life is identical for a new and a nine-year-old item. The UI renders it indistinguishably from a tier-3 distribution"* | `_rul_only_when_item_conditional`; JSON Schema `if/then/else`; `check-compat` |
| Compare `p_failure` across reference classes | **D7.** *"A tier-0 marginal population rate and a tier-3 item-conditional probability can both be perfectly calibrated in their own reference classes and remain incomparable. The optimizer will systematically starve high-hazard tier-0 items and over-serve tier-3 tails"* | `comparable_with()`; document 04 §4's claim that they *are* comparable is **stale, tranche 3** |
| Branch on `tier` in a consumer | **§7.1.** *"Tier invariance survives as shape invariance: consumers must not branch on `tier`. They may, and must, branch on `reference_class`"* | `FTH006` |
| Use `computed_at` to decide which prediction is fresher | **D3.** *"the job's stale result lands after the invalidation and wins — and looks fresher by `computed_at`."* Use `baseline_epoch` | `is_stale_against()`; `FTH004` |
| Rename `proposal_id` to `id` | **C30.** *"`Proposal` field names diverge between 01 §8.4 (`id`) and 03 §7.2 (`proposal_id`)."* Document 03 wins | `extra="forbid"` |
| Accept a proposal with an empty `evidence[]` | **§7.2 rule 1, D14.** *"rejected at the API boundary if absent"* | `min_length=1` |
| Treat a non-empty `evidence[]` as sufficient | **D14.** *"A crafted or careless passage produces a requisition proposal with a substituted NIIN, a fluent rationale, and genuine citations that satisfy the non-empty-evidence gate mechanically"* | `rests_solely_on_non_program_content`; §9 item 2's domain policy in the receiving operation |
| Validate a proposal only at creation | **§7.2 rule 2, D16.** *"A `work_candidate` sits five weeks, the equipment is replaced, validation happened at creation, and approval executes against a configuration that no longer exists"* | `revalidation_required_against`; `is_expired_at` |
| Adjudicate without a claim, or with one adjudicator at class/fleet scope | **§7.2 rules 3–4, D16.** *"two planners approve the same proposal and two work orders result"*; *"no dual control, no authority-versus-blast-radius check"* | `_claim_state_consistent`; `_adjudication_state_consistent`; `test_optimistic_concurrency` |
| Use `FOUO` or `U//FOUO` anywhere | **§7.3**, DoDI 5200.48 §3.4.b — **retired markings**. Minimum marking is `CUI`. Document 05 C42's mention of "NOFORN/FOUO" is a stale glossary item, not a licence | `FTH005`; closed `DisseminationControl` enum |
| Add an eleventh dissemination control | **§7.3.** *"constrained to the ten authorized Limited Dissemination Controls"* | closed enum; `check-compat` |
| Label a derived value with anything less than the union of its inputs | **§7.3, principle 7, D13.** *"a readiness rollup that moves when a compartmented fitting degrades leaks its existence, and the explanation graph hands over the pointer"* | `ClassificationLabel.union` |
| Make `asset_id` mandatory on the envelope | **C11.** *"~nine catalogued events have no asset scope"* | `EventScope` + `_exactly_one_scope_identifier` |
| Order or deduplicate on `source_time`, `occurred_at`, or any wall clock | **§5.4, D29.** Ubuntu 22.04 STIG **V-260520** mandates `makestep 1 -1` — unlimited backward steps — *"and that step fires precisely when a disconnected node reconnects and begins draining its outbox. Two writes from one process can therefore carry inverted wall-clock timestamps. Compliance guarantees a non-monotonic clock at exactly the moment ordering matters most"* | `FTH004`; `dedup_key`; `precedes`; `test_clock_block_present_and_disciplined` |
| Drop `sync_quality`, or retain it for less than forever | **§5.4 rule 4.** *"Skew is indistinguishable from tampering to an assessor, and non-repudiation claims collapse if the time is contestable"* | required on `Clock` |
| Use `occurred_at` for a feature value authored with hindsight | **D22.** *"confirmed anomaly tags carry mission `occurred_at` but were authored with hindsight"* | `FTH004`; field docstring; `observation_ref` point-in-time provenance |
| Set the compaction key equal to the partition key | **D5.** *"Compaction key = partition key = `asset_id`, so compacting the prediction topic collapses to one event per hull and discards every other item's predictions"* | `event()` validator; `ASY002` |
| Treat the event bus as a rebuild source | **§5.1, D5.** *"Retention is bounded deliberately, and the event bus is not a rebuild source."* Rebuild uses `changed_since` | `OAS013`; `test_changed_since_snapshot_read` |
| Replay history through the live bus | **D30.** *"replaying history through the event bus fires live side effects (notifications, work candidates, requisitions)"* | `replay` flag; `test_replay_events_marked_and_side_effect_free` |
| Record inbox receipt before applying the state change | **D2.** *"a crash between recording and committing the state change makes the event permanently suppressed on redelivery. Applied to `configuration.baseline_changed`, predictions for a replaced item are never invalidated — precisely the outcome document 04 calls the failure most likely to destroy operator trust, introduced by the inbox rule itself"* | `test_inbox_semantics_survive_a_crash` |

### 10.3 Contracts, agents, and conformance

| Do not | Because | Guard |
|---|---|---|
| Gate agent eligibility on the HTTP method | **C1, D11.** *"The `x-agent-eligible` rule introduced at rev 4 makes the `pdm-whatif` manifest listed in the same section impossible to build. Same defect blocks `POST /work-packages/plan` and `POST /scoring-runs`."* Gate on the declared `x-side-effects` class | `operation()`; `OAS004`; `eligibility.assess` |
| Treat `x-side-effects: none` as implying `x-agent-eligible` | **§8.1's two-level model.** Eligibility is the sub-application's safety assertion; selection is the agent's tuning decision. Collapsing them removes the safety gate | `eligibility.assess` returns `NOT_ELIGIBLE`, not eligible |
| Make manifest generation warn instead of fail | **§8.2.** *"Generation emits MCP-style descriptors and **fails** — rather than warns"* | exit codes 12–14; no `--warn-only` flag exists |
| Test the transactional outbox, the inbox mechanism, one-database-per-service, or log-line correlation IDs in the conformance suite | **D24.** *"Several obligations … are internal implementation properties unobservable from outside a black box and therefore unconformable by an executable suite. Either the obligation is unenforceable, or it is enforceable and no partner qualifies"* | §6.10; harness imports no service module |
| Assert cross-topic or cross-asset event ordering | **§5.1, D4.** Per-asset ordering is **per-topic**. Cross-topic causal order comes only from the antecedent rule | `test_ordering_within_partition` is partition-scoped |
| Let a sub-application define its own copy of a shared type | §1.1 of this document; C2's two-divergent-copies failure | `extra="forbid"`; import-linter; code review |
| Add a field to a canonical model that document 03 does not define | §11's "do not invent" rule. Flag it as an open question instead | this document's review; `check-compat` |
| Make an agent a direct topic consumer | **C19.** *"Agents are never direct topic consumers. Agents obtain state through tools"* | `ASY004` |
| Copy document 04's API surface, event lists, or prediction prose verbatim | **Document 04 is remediation tranche 3 and is not yet corrected.** It still contains `equipment_id`, `drivers`, and the claim that `p_failure` and `confidence` *"are comparable across tiers"* — all three superseded by document 03 rev 2. Document 05 §5 sequences the tranches; document 03 is binding on 04, *"so it must be correct first"* | this row; `FTH001`–`FTH003` |

---

## 11. Open questions — where document 03 is silent, ambiguous, or internally inconsistent

Per the rule that nothing may be invented, each item below is a gap this package refused to fill. Each names the exact reading adopted so behavior is deterministic in the meantime, and each needs a document 03 editorial correction or a program decision.

| ID | Question | Reading adopted here |
|---|---|---|
| **OQ-1** | **RESOLVED.** §3.3's prose said EIC *"is carried on `SystemRef` and `InstalledItemRef` for federation and human reference only"*, but neither schema block declared an `eic` field. | Both blocks now declare `eic: NonEmptyStr | None`, in document 03 §3.3 and here. `FTH001` continues to catch `eic` as a join key. |
| **OQ-2** | §3.3 denormalizes the parent chain only as far as `PositionRef.system_id`. Does `SystemRef` carry `asset_id`? Does `PositionRef`? Fleet Status scopes readiness to a system and needs the asset. | **No parent fields added.** Consumers resolve the chain through the Registry's `changed_since` reads. |
| **OQ-3** | §5.4 presents `EventEnvelope` as one block and then introduces `clock {}` separately. Is `clock` a top-level envelope member? | **Yes** — *"Every event therefore carries"* is unambiguous about the obligation, only about placement. Merge the blocks in document 03. |
| **OQ-4** | §5.4 requires *"exactly one scope identifier … matching `scope`"*, but (a) `EventScope.FLEET` has no corresponding `subject` field, and (b) `subject.mission_id` exists while no `scope` value selects it. | **`fleet` ⇒ empty subject; `mission_id` unusable as a sole subject.** Needs either a `mission` scope value or removal of `mission_id` from `subject`. Non-trivial: `mission_review.opened` and `mission_review.completed` are mission-scoped facts. |
| **OQ-5** | §5.4 says `producer` is *"slug from §3.1, plus version"* and that ordering uses `(producer, monotonic_seq)`. If the version is in the key, the sequence resets on every deploy. Separately, *"per-producer monotonically increasing"* does not say whether "producer" is a slug or a process instance — a multi-replica producer cannot maintain one sequence without coordination. | **Ordering key is `(producer.slug, monotonic_seq)`.** The multi-replica question is unresolved and material: it constrains whether a producing service may scale horizontally at all. Recommend `(producer.slug, hlc.node_id, monotonic_seq)` with HLC as the cross-node comparator, but that is a contract change. |
| **OQ-6** | §5.4 fixes `event_type` as `fathom.<slug>.<aggregate>.<verb>`, while §6's catalog lists `prediction.updated`. Is the short form shorthand, or a second wire value? | **Fully qualified on the wire.** The catalog is read as shorthand. C26 is the finding that these were inconsistent; the qualified form is the one §5.4 states normatively. |
| **OQ-7** | §6 says proposals are published *"using the §8.2 schema"*, but the Proposal schema is §7.2; §8.2 is the manifest structure. | Read as §7.2. Editorial. |
| **OQ-8** | §7.1's `contributing_factors` gives no vocabulary for `attribution_method`, no scale for `stability`, no sign convention for `contribution`, and **no value for the stability threshold below which factors are suppressed from display**. | `attribution_method` typed as a string; `is_displayable(threshold)` requires the caller to supply the threshold. **The threshold is a program decision**, and it directly governs what a maintainer sees. |
| **OQ-9** | §7.1's `sharpness` — *"dispersion relative to the reference-class base rate"* — has no range, direction, or units. Higher is presumably sharper, but that is an inference. | Unbounded float, no validator. Needs a definition before any consumer can threshold it. |
| **OQ-10** | §7.1 lists `p_failure` unconditionally, but document 06 §3 says that below the n≥50 calibration gate the prediction publishes *"with a population hazard rate and **no calibrated probability**."* Those cannot both hold. | **`p_failure` required** (03 is binding); the gate validator rejects a sub-floor prediction that is not `class_estimate`. If document 06's reading is correct, `p_failure` must become nullable — a **major** schema change. Reconcile before Phase 3. |
| **OQ-11** | Document 01 §11's monorepo layout says `services/asset-registry`; §3.1's slug is `registry`. | **`registry`.** Document 01 tranche-2 fix. |
| **OQ-12** | §7.2 makes dual control mandatory for *"any kind with external legal effect"* without enumerating which kinds those are. | `{requisition}`, derived from §11's conflict table and §10's shadow-mode text. Should be enumerated in §7.2. |
| **OQ-13** | §7.2's `authority_class` cites *"§9.3"* for its vocabulary. **Document 03 §9 is "Untrusted content" and has no §9.3.** §8.3's authority classes are *agent* classes (Delegated / Accountable autonomous), not *adjudication* authority classes. **The vocabulary of `authority_class` is undefined.** | Typed as an opaque string, validated by the owning sub-application. **This is the most consequential gap in the package**: D16's *"authority-versus-blast-radius check"* cannot be implemented against an undefined vocabulary, and it is the control that stops an anomaly-tag adjudicator from suppressing a preventive task across a class. |
| **OQ-14** | §7.2's `valid_until` comment reads *"expiry; absent means no expiry is permitted"* — ambiguous between "the field is mandatory" and "absence means never expires, which is forbidden". | **Field is mandatory.** Both readings forbid a non-expiring proposal; making it required is the enforceable one. |
| **OQ-15** | §7.3's `cui_categories[]` gives three examples (SP-CTI, SP-NNPI, SP-EXPT) but the CUI Registry is externally maintained. Closed enum or open list? | **Open list of strings**, with the authoritative set served by Reference Data (§14). A closed enum would require a package release each time the CUI Registry changes. |
| **OQ-16** | §7.3's `distribution_statement` is *"A..F or REL TO"*. Unioning `REL TO` with a lettered statement is not ordered by DoDI 5230.24 Table 1, so `ClassificationLabel.union` cannot mechanically resolve it. Also, `REL TO`, `DISPLAY ONLY`, and `FED ONLY` normally take an argument list (`REL TO USA, FVEY`) which §7.3 does not model. | `union` **raises** on that combination rather than guessing. The LDC-argument gap is a real modelling omission; it does not bind the unclassified demonstration but blocks any CUI handling. |
| **OQ-17** | §7.3 contains a **stray empty code fence** (lines 503–504) immediately after the `ClassificationLabel` explanation. Possibly content lost in an edit. | Assumed empty by intent. Worth confirming against the pre-edit revision. |
| **OQ-18** | §4.1 cites *"§9.1"* as the home of agent eligibility and §4's table cites *"§9.2"* for agent authority; the actual sections are §8.1 and §8.3. §7.2 cites *"§9.3"* (see OQ-13). All three appear to predate a section renumbering. | Read as §8.1 / §8.3. Editorial, but OQ-13 shows one of the three is a substantive gap rather than a typo. |
| **OQ-19** | Document 04 §4 declares `POST /scoring-runs` as `x-side-effects: none`, and §4's own table marks it `Required`. A scoring run creates a run record and consumes fleet-scale compute; `none` asserts *"the operation does not alter domain state."* Under §8.1 that makes it agent-eligible-able, so an agent could trigger a full fleet scoring run. | **Not resolved here** — this package only enforces the declaration's internal consistency. Flagged because C1 lists `POST /scoring-runs` among the operations the old gate blocked, and the fix may have over-corrected: `proposal-only` or a bounded `state-changing` may be the honest class. Needs a document 04 tranche-3 decision. |
| **OQ-20** | §4.1 says *"Every operation declares **two** annotations"*, while §8.1 and §15 obligation 8 add `x-agent-eligible` as a third. Is it required-with-default-false, or genuinely optional? | **Optional; absence means false.** `validate-openapi` does not require the key. If it should be mandatory-and-explicit, `OAS002`/`OAS003` gain a third rule. |
| **OQ-21** | §5.1 requires each topic's classification be *"declared in its registration"*, but no field in §5.4 or §5.5 carries a topic's declared classification. | Carried as the `x-fathom-classification` AsyncAPI extension (§5.5 of this document), set to `U` for the demonstration per §12 and document 06 §5. Should be normative in document 03. |

---

## 12. Testing this package

The three packages are infrastructure, so their own test suite is the only thing standing behind nine services' correctness. Four layers.

### 12.1 Schema round-trip and byte-identity

```python
# packages/canonical-schemas/tests/test_roundtrip.py
"""Round-trip and byte-identity.  The property §1.1 exists to guarantee."""

@pytest.mark.parametrize("vector", all_valid_vectors())
def test_python_roundtrip_is_byte_identical(vector):
    """parse -> wire_dict -> parse -> wire_dict produces identical bytes.

    Catches a serializer that normalizes on the way out but not on the way in —
    which makes a content hash depend on how many times the payload has been
    handled, and breaks §5.2's content-hash idempotency.
    """
    model = MODELS[vector.type].model_validate(vector.instance)
    once = model.canonical_json()
    twice = MODELS[vector.type].model_validate(json.loads(once)).canonical_json()
    assert once == twice


@pytest.mark.parametrize("vector", all_valid_vectors())
def test_content_hash_matches_committed(vector):
    """The committed `hashes.json` is the cross-language contract (§4.9)."""
    model = MODELS[vector.type].model_validate(vector.instance)
    assert model.content_hash() == COMMITTED_HASHES[vector.path]


@pytest.mark.parametrize("vector", all_invalid_vectors())
def test_invalid_vector_is_rejected_for_the_stated_reason(vector):
    """Not merely that it fails — that it fails for the RIGHT rule.

    A vector that starts failing for an unrelated reason silently stops testing
    the rule it was written for, which is how a regression guard rots.
    """
    with pytest.raises(ValidationError) as exc:
        MODELS[vector.type].model_validate(vector.instance)
    assert vector.expect.message_contains in str(exc.value)


def test_every_document_03_field_is_present():
    """Traceability, mechanically.

    Parses the pseudo-schema code blocks out of
    `docs/architecture/03-integration-contracts.md` §3.3, §5.4, §7.1, §7.2, §7.3
    and asserts a one-to-one correspondence with the Pydantic model fields.
    A field in the document with no model field fails; a model field with no
    document field fails as an INVENTED FIELD (§11's rule).

    This is the same technique as the existing `tools/check_event_catalog.py`,
    which reconciles the document 03 catalog against document 04.  Coupling a
    test to a Markdown document is unusual, and justified here: document 03 is
    the binding contract, and the alternative is that the two drift and nobody
    notices — which is C2 exactly.
    """


def test_no_model_declares_a_forbidden_field():
    """No canonical model has a field named `eic`, `equipment_id`, `drivers`,
    or `id`.  [C2, C10, C30, D23]"""


def test_utc_serialization_is_fixed_precision():
    """Six-digit microseconds and a `Z` suffix, always.  Document 03 §4 (Time)
    and the 1 ms audit granularity of DoD Zero Trust Overlays v1.1 (§5.4).
    Variable precision makes the wire form of one instant non-unique."""
```

### 12.2 Cross-language equivalence

```
packages/canonical-schemas/ts/test/vectors.test.ts
```

Runs the same vector directory through the generated Zod validators. Three assertions per vector, per §4.9. The suite fails if a vector exists that TypeScript does not cover — a missing test is a silent divergence licence.

Additionally `test_conditional_coverage.py`: every entry in `CONDITIONAL_CONSTRAINTS` (§4.9) and every entry in `CONDITIONAL_INVARIANTS` (§8.2) must have at least one `invalid/` vector that trips it, in both languages.

### 12.3 Compatibility-check tests

```python
# packages/contracts/tests/test_compat.py
"""Tests of the differ itself, using committed schema-pair fixtures.

The differ is the thing that decides whether a breaking change reaches nine
services.  A false negative is a fleet-wide outage; a false positive is a
blocked release.  Both are tested with explicit pairs rather than generated
mutations, so each verdict is traceable to a document 03 rule.
"""

CASES = [
    # (before, after, expected verdict, document 03 basis)
    ("add_optional_response_field",  "compatible",  "principle 5"),
    ("add_required_request_field",   "breaking",    "principle 5"),
    ("remove_response_field",        "breaking",    "principle 5"),
    ("narrow_integer_to_enum",       "breaking",    "principle 5"),
    ("add_response_enum_value",      "breaking",    "consumer enum parse"),
    ("add_request_enum_value",       "compatible",  "principle 5"),
    ("weaken_rul_conditional",       "breaking",    "§7.1  [D19]"),
    ("remove_scope_subject_if_then", "breaking",    "§5.4  [C11]"),
    ("relax_dual_control_condition", "breaking",    "§7.2  [D16]"),
    ("add_eleventh_ldc",             "breaking",    "§7.3"),
    ("substitution_internal_to_required", "breaking-for-substitutes", "§10"),
    ("side_effects_to_state_changing",    "breaking", "§8.1  [C1]"),
]


def test_registry_and_differ_agree_on_the_simple_cases():
    """For the cases a schema registry CAN evaluate, run both the registry's
    compatibility endpoint (against an ephemeral Redpanda) and our differ, and
    assert the same verdict.

    A disagreement means either the differ is wrong or the registry's
    compatibility level is misconfigured — and §8.2's whole argument is that the
    two are complementary, which requires them not to contradict.
    """
```

### 12.4 Generation-tool tests

```python
# packages/contracts/tests/test_openapi_validate.py
"""One test per OAS rule, each with a minimal failing document.

Rules are only useful if they fire.  A validation rule with no negative test is
indistinguishable from a rule that always passes, which is how `OAS004` — the
rule standing between an agent and a state-changing operation — would silently
stop working.
"""

@pytest.mark.parametrize("rule", ALL_OAS_RULES)
def test_rule_has_a_failing_fixture(rule):
    """Coverage guard: every rule in the table of §5.3 has a fixture that
    triggers it and a fixture that does not."""


def test_oas004_blocks_state_changing_agent_eligible():
    """§8.1, §15 obligation 8.  The C1/D11 regression test."""


def test_oas013_requires_changed_since_for_projected_aggregates():
    """§4, [D5, D25, D30].  Builds a spec with an event whose declared consumer
    projects an aggregate, and no `changed_since` read, and asserts failure."""
```

```python
# packages/agent-tooling/tests/test_generate.py
"""One test per exit code in the §7.5 table.

    @pytest.mark.parametrize("fixture,expected_exit", [
        ("bad_purpose_too_short",          10),
        ("filename_disagrees_with_name",   11),
        ("operation_absent",               12),   # §8.2, verbatim
        ("operation_not_agent_eligible",   13),   # §8.2, verbatim
        ("operation_lacks_description",    14),   # §8.2, verbatim
        ("eligible_but_state_changing",    15),   # §8.1 / §15 obl. 8
        ("bad_parameter_default",          16),
        ("unresolvable_projection",        17),
        ("missing_committed_spec",         18),
        ("orphan_owner",                   19),
        ("duplicate_operation",            20),
        ("stale_generated_descriptor",     21),
    ])

Plus the positive case: the three PdM manifests document 03 §8.2 names generate
cleanly against the committed `pdm` v1 specification, and `pdm-whatif` in
particular generates — it is the artifact C1 found unbuildable.
"""


def test_no_warn_only_escape_hatch_exists():
    """§8.2 requires generation to FAIL rather than warn.

    Asserts the CLI exposes no flag whose name contains 'warn', 'force',
    'ignore', or 'skip'.  A crude test, deliberately: the failure mode is
    someone adding a convenience flag under deadline pressure, and this test is
    what makes that a visible decision.
    """
```

### 12.5 Harness self-tests

The conformance harness needs a reference implementation to test against, or its tests are vacuous. `packages/contracts/tests/fixtures/exemplar/` contains a **deliberately minimal, deliberately non-compliant-in-known-ways** FastAPI service:

| Exemplar variant | Injected defect | Test asserts |
|---|---|---|
| `exemplar-good` | none | all five categories pass |
| `exemplar-no-etag` | omits `ETag`/`If-Match` | `test_optimistic_concurrency` fails |
| `exemplar-lost-event` | commits state, never publishes | `test_no_state_change_without_its_event` fails |
| `exemplar-receipt-first` | records inbox receipt before applying | `test_inbox_semantics_survive_a_crash` fails |
| `exemplar-walltime-order` | orders on `source_time` | `test_clock_block_present_and_disciplined` fails |
| `exemplar-no-changed-since` | omits the snapshot read | `test_changed_since_snapshot_read` fails |
| `exemplar-eic-join` | exposes `eic` as a response identifier | `test_canonical_identity_only` fails |

Each variant is a **positive test that the harness detects a real defect.** A harness whose tests only ever pass against a compliant implementation has never been shown to detect anything, and D24's whole concern is a conformance suite that cannot actually discriminate.

---

## 13. Definition of Done

This section **extends** the shared Definition of Done template in [`docs/build/09-monorepo-and-conventions.md`](09-monorepo-and-conventions.md). Every item in that template applies — repository conventions, formatting, type checking, commit hygiene, CI green, documentation, and whatever release and review gates it defines. The items below are **additional and specific to these three packages**, and none of them substitutes for a template item.

### 13.1 `packages/canonical-schemas`

- [ ] Every type in the §2 traceability table exists as a Pydantic v2 model, with a docstring citing its document 03 section, and every field carries a `description` traceable to a document 03 line.
- [ ] `test_every_document_03_field_is_present` passes: no document 03 field is missing, **and no model field is invented** (§11's rule).
- [ ] `test_no_model_declares_a_forbidden_field` passes: no `eic`, `equipment_id`, `drivers`, or `id`.
- [ ] All four §7.1 conditional rules, all three §7.2 state rules, the §5.4 exactly-one-subject rule, and the §7.3 CUI rule are implemented as `model_validator`s **and** as JSON Schema `if/then/else` blocks, with at least one `invalid/` vector each.
- [ ] `dissemination` is a closed enum of exactly ten LDCs; `FOUO` and `U//FOUO` appear nowhere except `FTH005`'s forbidden list.
- [ ] `clock` is a required member of `EventEnvelope`, with `sync_quality` fully populated.
- [ ] JSON Schema, TypeScript types, Zod validators, and `hashes.json` are generated, committed, and byte-identical to a fresh `make schemas` run.
- [ ] Both language test suites pass over the same vector corpus; `test_conditional_coverage` passes.
- [ ] The `FTH` flake8 plugin is registered, runs in pre-commit and CI, and has a positive and negative test per rule.
- [ ] `tools/check_noqa_justified.py` passes: no bare `noqa` of an `FTH` code.
- [ ] `import-linter` passes: `fathom_schemas` imports no web framework, database driver, or Kafka client.
- [ ] The package imports successfully in the Domino Job base image and the edge runtime image.

### 13.2 `packages/contracts`

- [ ] `@operation` / `operation_extra` gate `x-agent-eligible` at import time, with a test.
- [ ] All 22 `OAS` rules implemented, each with a passing and a failing fixture; `test_rule_has_a_failing_fixture` covers the whole table.
- [ ] `check-committed` and `check-compat` wired into CI for all nine slugs; every case in §12.3's `CASES` table passes.
- [ ] `@event` rejects compaction-key-equals-partition-key and compacted-without-compaction-key, with tests.
- [ ] AsyncAPI 3.0 export produces a valid document per producing service; `ASY001`–`ASY004` implemented and tested; `ASY004` rejects an agent as a declared consumer.
- [ ] Registry publication (§8.3) fails closed, with an ephemeral-Redpanda integration test.
- [ ] All five conformance base classes exist with the methods enumerated in §6.4–§6.8, and none imports a service module.
- [ ] All seven exemplar variants exist and produce the expected pass/fail outcome (§12.5).
- [ ] `collect_missing_consumer_suites()` returns empty, or every entry has a tracked exception with an owner — the mechanical closure of C3's 21 unbuildable tests.
- [ ] The conformance report enumerates all five categories and explicitly lists any that did not run.

### 13.3 `packages/agent-tooling`

- [ ] `ToolManifest` implements exactly the five §8.2 fields and no sixth.
- [ ] All twelve failure modes in §7.5 return their documented exit code, each with a test.
- [ ] `test_no_warn_only_escape_hatch_exists` passes.
- [ ] The three manifests document 03 §8.2 names — `pdm-fleet-triage`, `pdm-equipment-deepdive`, `pdm-whatif` — exist and generate cleanly.
- [ ] `emit-conformance` writes a §8.4 test into the sub-application's suite, and that test runs inside the §6.8 category.
- [ ] `orphans` returns empty (hard gate); `overlap` emits a report artifact on every manifest PR (advisory).
- [ ] Generated descriptors are committed and match a fresh run (`check-generated`).

### 13.4 Cross-cutting

- [ ] Every open question OQ-1 … OQ-21 is filed as a tracked item against document 03 or document 04, with an owner. **OQ-13 (undefined `authority_class` vocabulary) and OQ-10 (`p_failure` nullability) are blockers for Phase 3 detailed design**, because the first prevents implementing D16's authority check and the second is a potential major schema change.
- [ ] The nine sub-application build-framework documents reference this document for shared types and do not restate any schema.
- [ ] `packages/canonical-schemas` is published to the internal registry with a semver tag; the nine services reference it by range per §9.3, with committed lockfiles.
- [ ] The `schema-lag`, `check_dependency_ranges`, and `check_major_adoption` gates are live in CI.
- [ ] Documents 01 §11 (`services/asset-registry` → `services/registry`) and 04 (`equipment_id`, `drivers`, cross-tier comparability) have tranche-2/3 corrections filed — this package's lint rules will otherwise fail against code written from those documents, and the failure will look like a package defect rather than a stale-source defect.
