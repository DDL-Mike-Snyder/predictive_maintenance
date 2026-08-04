# Build Framework 20 — Asset & Configuration Registry (`registry`)

| | |
|---|---|
| **Status** | Wave 2 build framework. Binding on the Phase 3 implementation of `services/registry` |
| **Deliverable** | `services/registry` — the enterprise-authoritative record of what exists in the fleet, how it is configured, and what is presently installed in each position |
| **Position in the sequence** | **First.** Document 04 §12 order 1: *"Every other sub-application depends on it. The position-versus-installed-item and bitemporal decisions constrain all downstream modeling"* |
| **Source of truth** | [03 — Integration Contracts](../architecture/03-integration-contracts.md) §3.3, §4, §4.1, §5, §6, §7.2.1, §11, §14, §15 · [04 — Sub-Application Architectures](../architecture/04-subapplication-architectures.md) §1, §2, §12 · [05 — Review Findings](../architecture/05-architecture-review-findings.md) C10, C31, C39, D3, D4, D5, D9 · [07 — Navy Data Systems](../architecture/07-navy-data-systems.md) §3 in full, §4.1, §9 |
| **Siblings** | [09 — Monorepo & Conventions](09-monorepo-and-conventions.md) (scaffold, stack, DoD template, annotation mechanism) · [10 — Shared Packages](10-shared-packages.md) (the identity types this service serves) · [11 — Outbox & Sync Library](11-outbox-sync-library.md) (outbox/inbox, provisional-identity protocol §8) · [12 — Reference Data & Taxonomy](12-reference-data-taxonomy.md) (`equipment_family`, code sets) · [13 — Synthetic Data Generator](13-synthetic-data-generator.md) (§5 configuration fixtures) |
| **Precedence** | Document 03 prevails on any contract surface. Document 09 prevails on layout, stack, and conventions. Document 10 prevails on the public API of the shared packages. Document 11 prevails on outbox, inbox, clock, conflict policy, and provisional identity. This document prevails on Registry's aggregates, schema, operations, and events |
| **Classification** | Internal |

---

## 0. How to read this document

Three markers are used and they are load-bearing.

- **[03 §n]**, **[04 §2]**, **[07 §3.4]** — dictated by an architecture document. Not negotiable at implementation time.
- **`DECISION`** — the upstream documents do not settle this. This document decides it once so that eight downstream build documents do not each decide it differently. The reasoning is always stated.
- **`PLACEHOLDER`** — a Navy code value or vocabulary that document 07 records as **NOT PUBLICLY FOUND**. It is generated from a reserved synthetic range, flagged in the data card, and **never** presented as a real value. Document 07 §1: *"The prohibition on fabrication is operative, not aspirational."*

Defects found in upstream documents while writing this one are collected in §15 rather than silently worked around.

**Why this document is the tightest of the nine.** Every other sub-application projects a read model from this one's events and blocks on this one's `baseline_epoch`. If the bitemporal model, the position/installed-item distinction, or the identity types are wrong here, the error is not local — it propagates into eight downstream designs that will each encode it as an assumption. §5 therefore gives the exact SQL, not a description of bitemporality.

---

## 1. Purpose and scope

### 1.1 Purpose — document 04 §2, restated exactly

> **Purpose.** Serve as the authoritative record of what exists in the fleet, how it is configured, and what is presently installed in each position. Every other sub-application depends on this one, and no other sub-application may define asset or configuration identity.

### 1.2 Ownership boundary — document 04 §2, restated exactly

> **Owns:** class definitions, assets, the ESWBS system hierarchy, equipment and installed-item records, position definitions, part catalog entries, configuration baselines, allowance documents (COSAL, APL, AEL), and the class-to-hull deviation record.
>
> **Does not own:** telemetry, usage counter *values* (Condition & Telemetry), maintenance history (Scheduling), inventory positions (Supply), or predictions.

Three reading notes, each of which changes an implementation decision:

1. **"the ESWBS system hierarchy" is superseded in substance by document 07 §3.4.** ESWBS is *one* Hierarchical Structure Code scheme, selected per ship by `HSCI`; there is no universal layout. Document 07 §3.4 states the consequence in terms of this service: *"the ESWBS hierarchy in document 01 §6 must be modelled as one instance of a variant scheme selected by `HSCI`, not as the universal structure. This is a real change to the Phase 3 design of the Registry."* §4.3 implements that. The words "ESWBS system hierarchy" in document 04 §2 are read as "the system hierarchy, of which ESWBS is one scheme".
2. **"equipment and installed-item records" uses a losing term.** Document 03 §3.2 makes **installed item** canonical and lists *equipment* as a variant not to be used "in any document or identifier", and document 09 §7.2 extends that to class names, variables, tables, columns, topics, and log fields. There is exactly one aggregate here, `InstalledItem`. No table, column, class, or field in this service is named `equipment*`. Logged in §15 as a residual document 04 §2 defect.
3. **"usage counter *values*" are not owned, but a usage-at-installation snapshot is.** Document 01 §6 and document 13 §5.3 rule 5: Registry holds a **copy** of cumulative usage at the moment of installation, and it is explicitly not authoritative. It is carried so that a downstream model can compute usage-since-install without a synchronous call, and document 13 deliberately generates a small fraction of snapshots that disagree with the authoritative counter series. This service never corrects the counter and never serves the snapshot as a current value.

### 1.3 Plane placement and deployment shape

**Sustainment Plane in full. No Domino workloads.** [04 §2]

Registry has **no edge deployment profile.** Document 11 §1.2 states it: *"`registry` — Edge profile: No. Enterprise-authoritative. Participates ashore in provisional-identity resolution (§8)."* Document 01 §12's afloat resident subset is Condition & Telemetry, PMA tagging, the edge-authoritative maintenance-action-record path, edge-resident candidate generation, and cached predictions. Registry is not in it, and configuration baselines are enterprise-authoritative precisely because *"two divergent views of what is installed is the most damaging available conflict"* [03 §11].

The consequences are concrete and appear throughout: `producer_node` is always the literal `"enterprise"` (§7.2); no divergence budget is declared because no aggregate is edge-writable (§7.6); the edge reconciliation coordinator is absent, while the outbox relay is still always active per **C21** (§7.6).

### 1.4 What this document governs, and what it does not

| Concern | Governed by |
|---|---|
| Repository layout, stack pins, `src/` layering, Dockerfile, Helm skeleton, CI gates, the shared Definition of Done | [09](09-monorepo-and-conventions.md) |
| `AssetRef`, `SystemRef`, `PositionRef`, `InstalledItemRef`, `PartRef`, `EventEnvelope`, `ClassificationLabel`, `Proposal`, the conformance harness protocols, `operation_extra()` | [10](10-shared-packages.md) |
| `outbox.emit()`, the inbox, the clock module, `MonotonicSequencer`, conflict policies, `IdentityAliasResolver`, the fault-injection harness | [11](11-outbox-sync-library.md) |
| `equipment_family` definition and the NIIN→family assignment; ESWBS/EIC code *sets*; taxonomy | [12](12-reference-data-taxonomy.md); Registry is **not** the taxonomy owner [03 §14] |
| The synthetic fixtures this service loads, including the two `HSCI` schemes and the SCLSIS Record Type 2 field set | [13](13-synthetic-data-generator.md) §5, §6 |
| Capacity figures | [06 §7](../architecture/06-demo-decisions-and-assumptions.md). Do not invent numbers |
| Navy identifier formats and code values | [07](../architecture/07-navy-data-systems.md). Do not add on the basis of general knowledge [09 §9.5 item 32] |

### 1.5 Not the taxonomy owner

Document 03 §14: Reference Data is the **single owner** of the unified taxonomy — definition, versioning, publication — and *"Single ownership is an external obligation, not a preference"* under DoDI 8320.02. Registry owns identity and configuration. It owns neither the failure-mode vocabulary, nor `equipment_family`, nor the ESWBS/EIC code sets themselves.

Registry therefore holds a **read-through cache** of `equipment_family` refreshed on `equipment_family.updated` [12 §3.4], and validates `Part.equipment_family` against it. It never authors a family, never extends one, and never serves `GET /taxonomy`.

---

## 2. Traceability

Every design decision in this document traces to a row here. A decision with no row is a defect.

| Decision | Source |
|---|---|
| Purpose and ownership boundary, verbatim | 04 §2 |
| Seven core aggregates: `Class`, `Asset`, `SystemNode`, `Position`, `InstalledItem`, `ConfigurationBaseline`, `AllowanceDocument` | 04 §2 core aggregates table |
| Positions outlive installed items; RUL attaches to the item | 04 §2 key decision 1; 03 §3.3 rule 3; C10, D9 |
| Bitemporal configuration — valid time and record time tracked separately | 04 §2 key decision 2 |
| Exclusion constraints on overlapping validity | 04 §2 Data stores |
| Class template plus per-asset ordered deviation set | 04 §2 key decision 3 |
| Read-heavy, cacheable, `ETag`, consumers project from events | 04 §2 key decision 4; 03 principle 2 |
| The eight-row API surface, plus `x-substitution` values | 04 §2 API surface table |
| Six published events, three consumed events | 04 §2; 03 §6 Registry rows |
| `baseline_epoch` monotonic per asset; antecedent rule depends on it | 03 §5.4; D3, D4 |
| `producer_node` = `"enterprise"`, always | 03 §5.4; 11 §1.2, §4.2 |
| Provisional `installed_item_id` confirmed or superseded here | 03 §3.3 final paragraph, §11; **11 §8** in full |
| Published events under a provisional id are never rewritten; a mapping event is published | 11 §8.4 |
| `changed_since` snapshot reads over every projected aggregate | 03 §4, §15 obligation 5; D5, D25, D30 |
| `configuration_change` proposal kind, `maintainer` authority then Registry confirmation | 03 §7.2, §7.2.1; C39 |
| SCLSIS Record Types 1–2, 47 field names; `RIC` carries APL/AEL, `RIN` is a surrogate | 07 §3.1, §9 |
| EIC 7 characters, truncatable, never a join key | 07 §3.2; 03 §3.3 rule 2 |
| UIC 5 characters with optional Service prefix | 07 §3.3 |
| **HSC has no fixed layout; `HSCI` selects the scheme** | **07 §3.4, §9** |
| Hull number renders with a space, never a hyphen | 07 §3.5; SECNAVINST 5030.8D Encl 6 |
| OPNAV 4790/CK is the configuration-change transaction; ASI is a batch process, not an identifier | 07 §3.6, §9 |
| APL 8/9/11 characters, AEL 10–11 with the ambiguity stated | 07 §4.1 |
| PostgreSQL only; no time-series, no object storage | 04 §2 Data stores |
| SQLAlchemy 2.x async + asyncpg + Alembic; `TSTZRANGE` and `EXCLUDE` reachable from Core | 09 §2.2 (ORM row cites 04 §2's bitemporal requirement as decisive) |
| Enterprise-only; no edge profile; outbox still universal | 01 §12; 03 §15 obligation 11; 11 §1.2; C21 |

---

## 3. Names, paths, and the wire-name reconciliation

### 3.1 Mechanically derived forms [09 §7.1]

| Form | Value |
|---|---|
| Canonical name | Asset & Configuration Registry |
| Slug | **`registry`** |
| Display abbreviation | Registry |
| Service directory | `services/registry/` |
| Python distribution | `fathom-registry` |
| Python package | `fathom_registry` |
| API base path | `/api/v1/registry/` |
| Consumer group | `fathom-registry-v1` |
| Kubernetes label | `fathom.navy/service: registry` |
| Database cluster | `fathom-registry-pg`, database `registry` |
| Conformance directory | `packages/contracts/conformance/registry/` |
| Manifest directory | `packages/agent-tooling/manifests/registry/` |
| `operationId` prefix | `registry_` |
| Problem-detail `type` prefix | `urn:fathom:problem:registry:` |

The slug is **`registry`**, not `asset-registry`. Document 03 §3.1 fixes it; document 09 §11 item 1 and document 10 §4.3's directory-name note both record that document 01 §11 still carries the stale `asset-registry` and needs a tranche-2 edit. `fathom-contracts validate-layout` [10 §9.4] fails the build if the directory is anything else.

### 3.2 The catalog-label → wire-name reconciliation `DECISION`

Document 03 §5.4 gives one grammar for `event_type` — `fathom.<slug>.<aggregate>.<verb>` — and §5.1 gives one for topics — `fathom.<slug>.<aggregate>.v<major>`. **The `<aggregate>` token is the same token in both.** But document 03 §6's catalog rows use short labels (`configuration.baseline_changed`, `allowance.updated`) whose first segment is not the aggregate token in §5.1's own worked example, `fathom.registry.configuration_baseline.v1`. Document 10 §4.5 logs this as OQ-6 and declines to resolve it.

**It is resolved here, because Registry is the first service to publish and the aggregate token is not derivable from the catalog label.** The aggregate token governs; the catalog label is a cross-reference only and never appears on a wire.

| 03 §6 catalog label | Wire `event_type` | Topic | Aggregate token |
|---|---|---|---|
| `asset.registered` | `fathom.registry.asset.registered` | `fathom.registry.asset.v1` | `asset` |
| `asset.status_changed` | `fathom.registry.asset.status_changed` | `fathom.registry.asset.v1` | `asset` |
| `configuration.baseline_changed` | **`fathom.registry.configuration_baseline.changed`** | `fathom.registry.configuration_baseline.v1` | `configuration_baseline` |
| `installed_item.installed` | `fathom.registry.installed_item.installed` | `fathom.registry.installed_item.v1` | `installed_item` |
| `installed_item.removed` | `fathom.registry.installed_item.removed` | `fathom.registry.installed_item.v1` | `installed_item` |
| `installed_item.identity_resolved` **[AMENDMENT — closes OQ-5; row added to 03 §6]** | **`fathom.registry.installed_item.identity_resolved`** | `fathom.registry.installed_item.v1` | `installed_item` |
| `allowance.updated` | **`fathom.registry.allowance_document.updated`** | `fathom.registry.allowance_document.v1` | `allowance_document` |
| 03 §6 proposal convention | `fathom.registry.proposal.created` / `.adjudicated` / `.expired` | `fathom.registry.proposal.v1` | `proposal` |

`tools/check_event_catalog.py` must be taught this mapping rather than string-matching the catalog labels.

---

## 4. Data model — SQLAlchemy 2.x async

Stack per document 09 §2.2: **SQLAlchemy 2.x async (`AsyncEngine`/`AsyncSession`) + asyncpg**, migrations by **Alembic** with the async template, one history per service. Document 09's ORM row names this service's requirement as one of the three deciding factors: *"Document 04 §2's bitemporal configuration tables need `TSTZRANGE` columns and `EXCLUDE` constraints; SQLAlchemy 2.0 Core lets a repository drop to literal SQL for exactly those without abandoning typed models."*

All timestamps are `TIMESTAMPTZ` [09 §2.3]. `TIMESTAMP` without zone is a lint failure. All identifier columns carry exactly the names in document 03 §3.3 [09 §2.3].

### 4.0 Base, mixins, and the two temporal primitives

```python
# src/fathom_registry/models/__init__.py
"""SQLAlchemy 2.0 declarative base and the mixins every Registry table uses.

Private to this service.  Never serialized to the wire directly [03 principle 1].
"""
from __future__ import annotations

import datetime as dt
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Range,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint, JSONB, TSTZRANGE, UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class Base(DeclarativeBase):
    metadata = NAMING


TstzRange = Range[dt.datetime]
"""SQLAlchemy 2.0's typed range value.  Always constructed with '[)' bounds —
see `ClosedOpen` below."""


def ClosedOpen(lo: dt.datetime, hi: dt.datetime | None) -> TstzRange:
    """The ONLY sanctioned way to build a temporal period in this service.

    '[)' — lower inclusive, upper exclusive — is not a style choice.  The
    bitemporal exclusion constraints of §4.6 and §4.5 forbid OVERLAP, and two
    ADJACENT '[)' periods (`upper(a) == lower(b)`) do not overlap.  With '[]'
    bounds a correction that closes one record period exactly where its
    successor opens would be rejected by the constraint, and the only way an
    implementer could then make a correction land is to leave a one-microsecond
    hole in record-time coverage — which makes `as_known_at` return nothing for
    that instant.  Silent, and exactly the query the audit trail exists for.
    """
    return Range(lo, hi, bounds="[)")


class RecordSeqMixin:
    """The `changed_since` ordering column.  03 §4, §15 obligation 5, [D5].

    NOT a timestamp.  Ordering and pagination for every `changed_since` feed in
    this service are on `record_seq`, never on a wall clock [03 §5.4 rule 2,
    11 §4.7].  See §6.4 for why the allocator's row lock makes allocation order
    equal commit order, which is the property that makes the feed complete.
    """

    record_seq: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)


class ETagMixin:
    """Optimistic concurrency.  09 §5.4: the ETag is `W/"<version>"` derived
    from a monotonic integer column, and the repository compare-and-swap is
    `UPDATE ... SET version = version + 1 WHERE id = :id AND version = :expected`."""

    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class ClassifiedMixin:
    """03 principle 7 and §15 obligation 4: a classification label on every
    response and every event.  Stored as the full §7.3 `ClassificationLabel`,
    not a bare level string [10 §4.8]."""

    classification: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
```

#### 4.0.1 The record clock — a monotonic, non-regressing record time

Record time is a real timestamp, because `as_known_at` is a timestamp on the wire. It must never regress, and document 03 §5.4's clock discipline says a wall clock will regress: Ubuntu 22.04 STIG **V-260520** mandates `makestep 1 -1`.

```sql
-- One row.  The service's record-time high-water mark.
CREATE TABLE registry_record_clock (
  singleton  boolean     PRIMARY KEY DEFAULT true,
  last_time  timestamptz NOT NULL,
  CONSTRAINT rrc_singleton CHECK (singleton)
);
INSERT INTO registry_record_clock (singleton, last_time) VALUES (true, '-infinity');
```

```sql
-- Allocation, INSIDE the caller's transaction, before any bitemporal write.
UPDATE registry_record_clock
   SET last_time = GREATEST(clock_timestamp(), last_time + interval '1 microsecond')
 WHERE singleton
RETURNING last_time AS record_time;
```

Three properties, and each is required:

1. **Non-regressing.** A backward wall-clock step cannot produce a record time earlier than one already issued, so no `record_period` can invert and no exclusion constraint can be tripped by the STIG.
2. **Strictly increasing.** Every allocated record time is distinct, so a `record_period` is never empty and `[)` adjacency is exact.
3. **Serialized to commit.** The `UPDATE` holds a row lock until commit, so record times are issued in commit order.

> **This is not a violation of document 11 §4.7.** That rule prohibits *comparing wall-clock timestamps to decide precedence* — a merge, a last-writer-wins, a tie-break. Record time here is not an arbitration input. It is a **domain-visible interval boundary** that the caller supplies in `as_known_at` and the database tests with `@>` containment. Registry is enterprise-only and single-writer, so there is exactly one record clock and no cross-node comparison is ever performed. Every *ordering* decision in this service — the `changed_since` feed, the outbox, the deviation set — is on a gap-free sequence, never on this timestamp. Stated explicitly because an implementer reading document 11 first will otherwise either delete this table or, worse, order the `changed_since` feed on it.

#### 4.0.2 The gap-free sequence allocators

Two counters, both row-locked rather than Postgres `SEQUENCE`s, for the reason document 11 §4.3 gives: *"Native sequences are non-transactional: they leak values on rollback, so the stream has holes. A gap-free sequence gives consumers loss detection for free."*

```sql
CREATE TABLE registry_record_seq (
  aggregate text   PRIMARY KEY,
  next_seq  bigint NOT NULL DEFAULT 1
);

CREATE TABLE asset_baseline_epoch (
  asset_id   uuid   PRIMARY KEY REFERENCES assets(asset_id),
  next_epoch bigint NOT NULL DEFAULT 1,
  CONSTRAINT abe_next_positive CHECK (next_epoch >= 1)
);
```

```sql
-- record_seq, inside the caller's transaction:
UPDATE registry_record_seq SET next_seq = next_seq + 1
 WHERE aggregate = :aggregate RETURNING next_seq - 1 AS record_seq;

-- baseline_epoch, inside the caller's transaction:
UPDATE asset_baseline_epoch SET next_epoch = next_epoch + 1
 WHERE asset_id = :asset_id RETURNING next_epoch - 1 AS baseline_epoch;
```

**`baseline_epoch` rules — document 03 §5.4's antecedent rule depends on every one of them.**

| Rule | Why |
|---|---|
| Gap-free per asset | A consumer holding epoch 41 that receives 43 knows 42 exists and must block for it [03 §5.4, D4]. With gaps the block never releases, or worse, the consumer learns to ignore gaps and D4 returns |
| Strictly increasing, allocated in commit order | The row lock is held to commit, so epoch order equals visibility order. A `SEQUENCE` would let epoch 43 become visible before 42 |
| Starts at 1; epoch 0 is never allocated | `0` is the "no configuration read model yet" sentinel in `EpochFence.current_epoch` [11 §3.5]. A real epoch 0 makes an empty read model indistinguishable from a fresh asset |
| Never reset, never reused, not on redeploy, not on migration | Mirrors 11 §4.3's producer-sequence rule for the same reason: reuse is unrecoverable |
| A restored database backup requires operator confirmation that the epoch did not regress | A regressed epoch republishes a used epoch under different content, and every downstream fence silently accepts stale configuration |

Verified by `test_baseline_epoch_is_gap_free_per_asset` (§11.3) and by a startup invariant check that fails readiness if `max(baseline_epoch) <> next_epoch - 1` for any asset.

### 4.1 `HierarchyScheme` — the `HSCI` selector [07 §3.4]

Document 07 §3.4, and document 07 §9's first correction: *"HSC is Hierarchical Structure Code, and the format varies by ship, selected by `HSCI`. There is no universal layout."* Sibling schemes named in §3.4: AILSIN, CIN, FGC. ESWBS is one of them, and *"the code content is NOT PUBLICLY FOUND, and any nine-group summary table circulating informally should be treated as unusable."*

```python
# src/fathom_registry/models/hierarchy_scheme.py

class HierarchyScheme(Base, RecordSeqMixin, ETagMixin):
    """A Hierarchical Structure Code scheme, selected per asset by `HSCI`.

    07 §3.4: "Identifies the functional/hierarchical relationship of the ship,
    ship system and equipment... The numbering method MAY DIFFER IN TYPE."
    Record Type 1 carries `HSCI` to identify which scheme applies, so there is
    no fixed HSC column layout and an architecture that assumes one is wrong
    (07 §3.4, 07 §9).

    THERE IS NO `eswbs_group` COLUMN, NO `eswbs_subgroup` COLUMN, AND NO FIXED
    SEGMENT COLUMN ANYWHERE IN THIS SERVICE.  A scheme's shape is DATA, in
    `segment_spec`, and is validated per asset at write time (§4.3).
    """

    __tablename__ = "hierarchy_schemes"

    hsci: Mapped[str] = mapped_column(String(8), primary_key=True)
    scheme_name: Mapped[str] = mapped_column(Text, nullable=False)
    #  "eswbs" | "ailsin" | "cin" | "fgc" | a reserved synthetic name.
    #  07 §3.4 names ESWBS, AILSIN, CIN and FGC as sibling schemes.  The
    #  document number for ESWBS is S9040-AC-IDX-010 (07 §3.4: "Cite -AC- as
    #  current"); recorded in `authority_reference`, not in code.
    scheme_family: Mapped[str] = mapped_column(Text, nullable=False)
    authority_reference: Mapped[str | None] = mapped_column(Text)

    segment_spec: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    """Ordered segment definitions, one per hierarchy level.  Each entry:

        {"level": 1, "name": "group",    "length": 1, "charset": "0-9"}
        {"level": 2, "name": "subgroup", "length": 1, "charset": "0-9"}
        {"level": 3, "name": "unit",     "length": 1, "charset": "0-9A-Z"}

    `segment_spec` is the whole reason this table exists.  A scheme with three
    numeric segments and a scheme with two segments of different widths are both
    representable, and the hierarchy validator (§4.3) reads the spec rather than
    a hard-coded layout.  Document 13 §5.2 instantiates at least two schemes
    across the demonstration fleet — `ESWBS-like` on the five surface assets and
    `VARIANT-A` on the three subsurface and four unmanned — precisely "so that
    every consumer's scheme-awareness is exercised rather than asserted."
    """

    code_values_are_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    """PLACEHOLDER marker.  True for every scheme in the demonstration.

    07 §3.4: ESWBS "code content is NOT PUBLICLY FOUND", and 13 §5.2 requires
    generated ESWBS-like codes come from "a reserved synthetic band whose values
    are structurally shaped but are not presented as real ESWBS values."  This
    column is what makes the data card's divergence list mechanical rather than
    remembered, and `GET /assets/{id}/systems` echoes it on every response.
    """
```

### 4.2 `Class` and the as-designed template [04 §2]

`class_id` is a **string**, not a UUID. Document 03 §3.3: *"The Navy expresses ship class as the LEAD HULL NUMBER (68 for NIMITZ, 51 for ARLEIGH BURKE), so the internal identifier carries both that and the flight or block."* Document 10 §4.3 types `AssetRef.class_id` as `NonEmptyStr` and gives `"DDG-51-FLTIIA"`, `"SSN-774-BLKIV"` as the shape. Document 07 §3.1 confirms it from SCLSIS Record Type 1's `CLASS` field.

```python
# src/fathom_registry/models/klass.py
#  Module named `klass` because `class` is a Python keyword; the MAPPED CLASS is
#  `Class` and the table is `classes`, so the canonical aggregate name from
#  04 §2 survives everywhere it is externally visible.

class Class(Base, RecordSeqMixin, ETagMixin, ClassifiedMixin):
    """04 §2: "Ship, boat, or vehicle class with its as-designed configuration
    template." """

    __tablename__ = "classes"

    class_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    type_designation: Mapped[str] = mapped_column(String(8), nullable=False)   # "DDG"
    lead_hull_number: Mapped[int | None] = mapped_column(Integer)              # 51
    flight_or_block: Mapped[str | None] = mapped_column(String(16))            # "FLTIIA"
    domain: Mapped[str] = mapped_column(String(16), nullable=False)            # 03 §3.3 AssetDomain
    display_name: Mapped[str] = mapped_column(Text, nullable=False)            # "ARLEIGH BURKE"
    default_hsci: Mapped[str] = mapped_column(
        ForeignKey("hierarchy_schemes.hsci"), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "domain IN ('surface','subsurface','unmanned')",
            name="domain_vocabulary",   # 03 §3.3 AssetRef.domain
        ),
        CheckConstraint(
            "class_id ~ '^[A-Z0-9]+(-[A-Z0-9]+)*$'",
            name="class_id_shape",
            # Hyphens are legal HERE and illegal in `hull_or_tail`.  class_id is
            # an internal designation; hull_or_tail is a rendered hull number and
            # SECNAVINST 5030.8D Encl 6 forbids the hyphen there (07 §3.5).
            # Two different rules on two different columns, deliberately.
        ),
    )


class ClassTemplateVersion(Base, RecordSeqMixin, ETagMixin):
    """A versioned as-designed configuration template for a class.

    `DECISION` — the template is VERSIONED and valid-timed, not mutable in
    place.  04 §2: "Ships of one class diverge substantially over their service
    lives through modernization availabilities and field changes."  A class
    revision that changed the template in place would silently change what every
    hull's deviation set is a deviation FROM, and every historical effective
    configuration would move.  §9 resolves an effective configuration against
    the template version in force at `as_of`, which is only possible if the
    template is versioned.
    """

    __tablename__ = "class_template_versions"

    template_version_id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True)
    class_id: Mapped[str] = mapped_column(ForeignKey("classes.class_id"), nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_period: Mapped[TstzRange] = mapped_column(TSTZRANGE, nullable=False)
    record_period: Mapped[TstzRange] = mapped_column(TSTZRANGE, nullable=False)
    authority_reference: Mapped[str | None] = mapped_column(Text)
    node_count: Mapped[int] = mapped_column(Integer, nullable=False)
    position_count: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("class_id", "template_version", name="class_template_version"),
        ExcludeConstraint(
            ("class_id", "="),
            ("valid_period", "&&"),
            ("record_period", "&&"),
            using="gist",
            name="class_template_no_bitemporal_overlap",
        ),
    )


class ClassTemplateNode(Base):
    """A template system node.  Scheme-relative, per §4.1 — the code is
    validated against the class's `default_hsci` scheme's `segment_spec`."""

    __tablename__ = "class_template_nodes"

    template_node_id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True)
    template_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("class_template_versions.template_version_id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_template_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("class_template_nodes.template_node_id")
    )
    hsc_code: Mapped[str] = mapped_column(String(32), nullable=False)
    hsc_segments: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    eic: Mapped[str | None] = mapped_column(String(7))

    __table_args__ = (
        UniqueConstraint("template_version_id", "hsc_code", name="template_node_code"),
        CheckConstraint("eic IS NULL OR eic ~ '^[A-Z0-9]{2,7}$'", name="eic_shape"),
    )


class ClassTemplatePosition(Base):
    """A template installation location, with the part it is designed to hold.

    `expected_niin` is what the as-designed configuration calls for.  A hull
    whose position holds something else is a DEVIATION (§4.7), which is the
    whole point of 04 §2's third key decision: divergence becomes "a
    first-class, queryable fact rather than an inconsistency."
    """

    __tablename__ = "class_template_positions"

    template_position_id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True)
    template_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("class_template_versions.template_version_id", ondelete="CASCADE"),
        nullable=False,
    )
    template_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("class_template_nodes.template_node_id"), nullable=False
    )
    position_code: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_niin: Mapped[str | None] = mapped_column(String(9))
    expected_quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    ric: Mapped[str | None] = mapped_column(String(11))
    par_ric: Mapped[str | None] = mapped_column(String(11))

    __table_args__ = (
        UniqueConstraint("template_version_id", "position_code", name="template_position_code"),
    )
```

### 4.3 `Asset` and `SystemNode`

```python
# src/fathom_registry/models/asset.py

class Asset(Base, RecordSeqMixin, ETagMixin, ClassifiedMixin):
    """04 §2: "A specific hull, boat, or vehicle. Carries UIC, domain,
    operational status, OFRP phase."

    Projects onto 03 §3.3 `AssetRef` exactly: asset_id, hull_or_tail, uic,
    class_id, domain.  Everything else here is Registry-internal or is served on
    the fuller `AssetDetail` response (§6.2).
    """

    __tablename__ = "assets"

    asset_id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True)

    hull_or_tail: Mapped[str] = mapped_column(String(24), nullable=False, unique=True)
    """"DDG 113", "SSN 796", "MQ-25 004" — HUMAN REFERENCE ONLY, never a join key
    [03 §3.3 rule 1].  SPACE, never a hyphen, in the hull number itself:
    SECNAVINST 5030.8D Enclosure 6, "Hyphens will not be used in the hull number
    of any ship or craft" (07 §3.5).  Trailing N denotes nuclear propulsion; a
    leading "T-" denotes Military Sealift Command; F denotes foreign
    construction.  Unmanned assets carry a tail-style designator (13 §5.1) whose
    TYPE portion may itself contain a hyphen — "MQ-25 004" — see §15 item 5."""

    uic: Mapped[str] = mapped_column(String(6), nullable=False)
    """07 §3.3: SECNAVINST 5400.48 ¶2c, "A five or six-character alphanumeric
    code... In systems using a six-character UIC, the first character of the UIC
    is a Service identifier."  Navy ships use R (Pacific) or V (Atlantic) in
    DoDAAC contexts, so `R21313` is the six-character DoDAAC-prefixed form of the
    five-character UIC `21313`.  07 §3.3's instruction is explicit: "Model UIC as
    FIVE characters, with an optional leading Service prefix in DoDAAC and
    requisition contexts."  Stored canonically as the five-character form;
    `uic_service_prefix` carries the prefix separately so the six-character form
    is reconstructible without ever being the stored identity."""
    uic_service_prefix: Mapped[str | None] = mapped_column(String(1))

    class_id: Mapped[str] = mapped_column(ForeignKey("classes.class_id"), nullable=False)
    domain: Mapped[str] = mapped_column(String(16), nullable=False)

    hsci: Mapped[str] = mapped_column(ForeignKey("hierarchy_schemes.hsci"), nullable=False)
    """SCLSIS Record Type 1 field `HSCI` — "Identifies WHICH HSC scheme this ship
    uses" (07 §3.1, §3.4).  Per-asset and not derived from the class, because
    07 §3.4 states the format "may differ in type" and a modernized hull can
    legitimately carry a different scheme from its lead ship."""

    # --- SCLSIS Record Type 1, remaining fields (07 §3.1) -------------------
    sclsis_status: Mapped[str | None] = mapped_column(String(8))
    """Record Type 1 `STATUS` (Ship Status).  PLACEHOLDER — 07 §3.1 publishes the
    field name and not its value set.  Values are served by Reference Data from a
    reserved synthetic set and listed in the data card's divergence list."""
    tycom: Mapped[str | None] = mapped_column(String(8))
    """Record Type 1 `TYCOM` (Type Commander Code).  PLACEHOLDER — 07 §3.1:
    "Values NOT PUBLICLY FOUND."  Never populated with a guessed real value
    (13 §5.1)."""
    sthn: Mapped[str | None] = mapped_column(String(24))
    """Record Type 1 `STHN` — "Ship Type and Hull Number. A SINGLE FIELD with
    separate type and hull portions" (07 §3.1).  Retained as filed, alongside the
    rendered `hull_or_tail`, because the two are different artifacts."""

    # --- operational state ---------------------------------------------------
    operational_status: Mapped[str] = mapped_column(String(32), nullable=False)
    ofrp_phase: Mapped[str | None] = mapped_column(String(32))
    """PLACEHOLDER.  04 §2 requires the field; document 07 does not verify the
    OFRP phase vocabulary anywhere, so no value set is asserted here.  Served and
    versioned by Reference Data; Registry validates against the served
    enumeration and stores the code.  Inventing the phase names would be exactly
    the fabrication 07 §1 prohibits."""
    deployment_state: Mapped[str | None] = mapped_column(String(32))   # PLACEHOLDER, as above
    commissioned_on: Mapped[dt.date | None] = mapped_column()
    decommissioned_on: Mapped[dt.date | None] = mapped_column()

    __table_args__ = (
        CheckConstraint("uic ~ '^[A-Z0-9]{5}$'", name="uic_five_characters"),
        CheckConstraint(
            "uic_service_prefix IS NULL OR uic_service_prefix IN ('N','Q','R','V')",
            name="uic_service_prefix_navy",
            # 07 §3.3: "Navy DoDAAC first position is N, Q, R, or V, and ships
            # use R (Pacific) or V (Atlantic)."
        ),
        CheckConstraint("domain IN ('surface','subsurface','unmanned')", name="domain_vocabulary"),
        CheckConstraint(
            "position('-' in substring(hull_or_tail from position(' ' in hull_or_tail))) = 0",
            name="hull_number_has_no_hyphen",
            # The hull NUMBER — everything from the space onward — carries no
            # hyphen.  SECNAVINST 5030.8D Encl 6 via 07 §3.5.  The TYPE portion
            # before the space may (MQ-25), and the leading T- prefix is
            # sanctioned.  A regex over the whole string would reject document
            # 03 §3.3's own example; see §15 item 5.
        ),
    )


class SystemNode(Base, RecordSeqMixin, ETagMixin, ClassifiedMixin):
    """04 §2: "ESWBS-aligned hierarchy node within an asset" — read per §1.2
    note 1 as "hierarchy node within an asset, in the asset's own HSC scheme."

    Projects onto 03 §3.3 `SystemRef`: system_id (the join key), eswbs (human
    reference and federation only), eic (optional, where the system level has
    one, federation and human reference only).  Closes C31.

    ADJACENCY LIST plus a materialized path.  Traversal is a PostgreSQL
    recursive CTE, the same choice document 04 §10 makes for the design
    dependency graph: "Graph traversal is served from PostgreSQL recursive
    queries unless Phase 3 establishes depth requirements exceeding what that
    supports."  HSC schemes in 07 §3.4 are shallow — segment counts in the low
    single digits — so they do not.
    """

    __tablename__ = "system_nodes"

    system_id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.asset_id"), nullable=False)
    parent_system_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("system_nodes.system_id")
    )

    hsc_code: Mapped[str] = mapped_column(String(32), nullable=False)
    """The code AS FILED, in the asset's own scheme.  SCLSIS Record Type 2 field
    `HSC` (07 §3.1)."""
    hsc_segments: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    """The code decomposed per the asset's scheme's `segment_spec`.  Written by
    the hierarchy validator, never by hand.  Queries that need "all nodes in
    group 2" use a JSONB predicate against the SCHEME-NAMED segment, not a
    substring of a fixed layout."""
    hsc_path: Mapped[str] = mapped_column(Text, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)

    eswbs: Mapped[str | None] = mapped_column(String(6))
    """Populated ONLY where the asset's scheme family is `eswbs`.  NULL on an
    asset using AILSIN, CIN, FGC, or a variant scheme — which is the whole
    correction in 07 §3.4.  Human reference and external federation only; NEVER
    a join key [03 §3.3 rule 1].  Values are PLACEHOLDER: 07 §3.4 records ESWBS
    code content as NOT PUBLICLY FOUND, and 13 §5.2 forbids emitting the
    informally circulating nine-group table in any field."""

    eic: Mapped[str | None] = mapped_column(String(7))
    """03 §3.3 `SystemRef.eic`: "Equipment Identification Code, WHERE THE SYSTEM
    LEVEL HAS ONE.  Federation and human reference only — never a join key."

    07 §3.2: seven alphanumeric characters, positionally segmented, and
    "truncated EICs are LEGITIMATE — a two-character value such as `QD`
    identifies a subsystem only."  Hence `2..7`, not exactly 7.  NAVSEAINST
    4790.8 Appendix A via 03 §3.3 rule 2 is the authority for it being a CLASS
    CODE OF VARIABLE SPECIFICITY: there is no foreign key on this column, no
    index intended for joining, and lint rule FTH001 [10 §4.4] fails any join
    written against it."""

    __table_args__ = (
        UniqueConstraint("asset_id", "hsc_code", name="system_node_code_per_asset"),
        CheckConstraint("eic IS NULL OR eic ~ '^[A-Z0-9]{2,7}$'", name="eic_shape"),
        CheckConstraint("depth >= 1", name="depth_positive"),
        CheckConstraint(
            "(parent_system_id IS NULL) = (depth = 1)", name="root_has_no_parent"
        ),
        Index("ix_system_nodes_asset_path", "asset_id", "hsc_path"),
        Index("ix_system_nodes_segments", "hsc_segments", postgresql_using="gin"),
    )
```

**The hierarchy validator** [04 §2 internal components] reads the asset's `HierarchyScheme.segment_spec` and rejects a `hsc_code` that does not match it, rejects a child whose code does not extend its parent's under the scheme's segment order, and refuses to populate `eswbs` when `scheme_family <> 'eswbs'`. It is the mechanism that makes §1.2 note 1 enforced rather than documented.

### 4.4 `Position` — permanent, and the anchor of the C10 distinction

```python
# src/fathom_registry/models/position.py

class Position(Base, RecordSeqMixin, ETagMixin, ClassifiedMixin):
    """04 §2: "A named, persistent installation location within a system.
    POSITIONS OUTLIVE THE ITEMS INSTALLED IN THEM."

    Projects onto 03 §3.3 `PositionRef`: position_id (the join key),
    position_code ("233-04-A" — human reference only), system_id.

    THERE IS NO `installed_item_id` COLUMN ON THIS TABLE, AND THERE NEVER WILL
    BE.  Occupancy is a bitemporal fact with its own table (§4.5.2).  A
    `current_installed_item_id` column here would be the whole of C10 in one
    line: it has no valid time, so it cannot answer "what was installed on 14
    March", and the first correction entered three weeks late would overwrite the
    only record of what was believed.  Document 04 §2 calls the resulting failure
    mode — "a newly installed component inherits its predecessor's degradation" —
    "both wrong and confidence-destroying the first time an operator notices it."
    """

    __tablename__ = "positions"

    position_id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True)
    system_id: Mapped[UUID] = mapped_column(ForeignKey("system_nodes.system_id"), nullable=False)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.asset_id"), nullable=False)
    #  asset_id is denormalized here DELIBERATELY, for the resolver's benefit
    #  (§5): resolving an asset's configuration otherwise requires a recursive
    #  descent of system_nodes on every read, and this is the read-heaviest
    #  operation in the system [04 §2 key decision 4].  A trigger asserts it
    #  equals system_nodes.asset_id.  Note 03 §3.3's PositionRef carries only
    #  system_id, so the WIRE shape is unaffected — see 10 §4.3's OQ-2.

    position_code: Mapped[str] = mapped_column(String(32), nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)

    established_period: Mapped[TstzRange] = mapped_column(TSTZRANGE, nullable=False)
    """When the position itself exists, in VALID time.  A modernization
    availability that adds a position opens one here; one that removes a position
    closes it.  Distinct from occupancy: a position with no item installed is a
    real and important state — it is an empty foundation, and Supply's allowance
    position is computed against it."""

    template_position_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("class_template_positions.template_position_id")
    )
    """The template position this instantiates, where it is a template position
    at all.  NULL when the position exists only by deviation (§4.7)."""

    __table_args__ = (
        UniqueConstraint("asset_id", "position_code", name="position_code_per_asset"),
        CheckConstraint("NOT isempty(established_period)", name="established_nonempty"),
        Index("ix_positions_asset_system", "asset_id", "system_id"),
    )
```

### 4.5 `InstalledItem` — the physical item, and its bitemporal occupancy

`DECISION` — document 04 §2's single `InstalledItem` aggregate is implemented as **an aggregate root plus a bitemporal occupancy child.** The aggregate boundary, the `ETag`, and the `changed_since` feed remain `InstalledItem`; nothing on the contract surface changes.

Why the split is forced rather than preferred:

- A physical item **has an identity independent of where it is installed.** It can be removed to a storeroom, repaired, and reinstalled elsewhere. Document 03 §3.3 is explicit that `installed_item_id` *"identifies the PHYSICAL ITEM"*, and remaining useful life, usage accumulation, and failure history attach to it.
- The occupancy is what is **bitemporal.** "Which item was in position 233-04-A on 14 March, as we believed it on 1 April" is a question about occupancy, not about the item.
- With one table, `installed_item_id` cannot be the primary key and also carry a `record_period`, because a correction to an install date produces a second row for the same item. Either the identity or the correction has to go, and the correction is the thing document 04 §2's second key decision exists to preserve.

#### 4.5.1 `InstalledItem` — identity

```python
# src/fathom_registry/models/installed_item.py

class InstalledItem(Base, RecordSeqMixin, ETagMixin, ClassifiedMixin):
    """04 §2: "A physical item currently or formerly occupying a position."

    Projects onto 03 §3.3 `InstalledItemRef`, whose `position_id` and
    `installed_at` come from the CURRENTLY-BELIEVED occupancy (§4.5.2) — see
    §6.2 for the exact projection.

    Closes C10: "No canonical identifier exists for `InstalledItem`... It is
    undefined whether `equipment_id` identifies the position-bound slot or the
    physical item."  It identifies the physical item.  There is no column,
    attribute, or wire field named `equipment_id` in this service [10 §4.3].
    """

    __tablename__ = "installed_items"

    installed_item_id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True)

    niin: Mapped[str] = mapped_column(ForeignKey("parts.niin"), nullable=False)
    """[AMENDMENT] `NOT NULL` here, unlike `parts.niin`, is correct and stays —
    it is a residual gap, recorded rather than silently accepted: `parts.niin`
    is nullable for `identifier_form = 'cage_part_number'` (§4.7 above), and
    this FK requires a non-null value, so **no `cage_part_number` part can ever
    be installed** through this table as specified. Whether that is the
    intended scope of `identifier_form`'s fourth-and-fifth values or a genuine
    gap is a Phase 3 question this schema does not resolve.

    What it is.  A NIIN alone is a part TYPE, not an installed item
    [03 §3.3 rule 4]."""

    iuid: Mapped[str | None] = mapped_column(Text, unique=True)
    """Item Unique Identification per DoDI 8320.04, WHERE ASSIGNED.

    03 §3.3: "DoDI 4151.22 §1.2.d and §1.2.l require serialized item management
    and IUID 'to optimize RCM and CBM+ data analytics', so this is the
    externally mandated instance identity — NOT THE EIC."  13 §5.3 rule 4 says
    the same and adds that a replacement carries a NEW IUID.  Unique where
    present; NULL where the NIIN is lot-tracked rather than serialized (04 §2's
    first Phase 3 question is which NIINs warrant item-level serialization)."""

    serial_or_lot: Mapped[str | None] = mapped_column(Text)

    eic: Mapped[str | None] = mapped_column(String(7))
    """03 §3.3 `InstalledItemRef.eic`: "Equipment Identification Code OF THE
    CLASS THIS ITEM INSTANTIATES.  Federation and human reference only — never a
    join key."  2..7 characters per 07 §3.2's truncation rule.  No foreign key,
    no join."""

    # --- SCLSIS Record Type 2, the three fields that are commonly confused ---
    ric: Mapped[str | None] = mapped_column(String(11))
    """`RIC` — Repairable Identification Code.  07 §3.1, verbatim: "Uniquely
    identifies a particular commodity.  When the code is related to an Allowance
    Parts List or an Allowance Equipage List, it is known as an APL or AEL,
    respectively."  THIS IS THE FIELD THAT CARRIES THE APL/AEL NUMBER.  07 §9
    records "RIN carries the APL number" as a corrected premise."""
    par_ric: Mapped[str | None] = mapped_column(String(11))
    """`PAR RIC` — "the RIC of the equipment that carries supply support when an
    item has no APL or AEL of its own — a real parent-fallback mechanism worth
    modelling" (07 §3.1).  13 §5.4 exercises the fallback by giving a fraction of
    items no own RIC and a populated PAR RIC."""
    sclsis_record: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    """The remaining SCLSIS Record Type 2 fields as filed, keyed by the verbatim
    abbreviations 07 §3.1 publishes (`SEI`, `SN`, `QTY`, `CAGE`, `SC`, `EFD`,
    `ESD`, `MCC`, `SCAT`, ... `ISEA`).  JSONB rather than 41 columns because
    07 §3.1 records that field LENGTHS are NOT PUBLICLY FOUND and 13 §5.4 flags
    generated lengths as a known structural divergence; promoting a field to a
    typed column asserts a length this program cannot source.

    `RIN` — Record Identification Number — is stored here and IS NEVER A JOIN
    KEY.  07 §3.1: "an internal surrogate, not a domain identifier... basically
    an address used by these databases for automated retrieval."  It is not
    promoted to a column precisely so that nothing can join on it."""

    # --- provisional identity, per 03 §3.3 and 11 §8 ------------------------
    provisional: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    provisional_context: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    minting_node_id: Mapped[str | None] = mapped_column(Text)
    mint_monotonic_seq: Mapped[int | None] = mapped_column(BigInteger)
    identity_resolution: Mapped[str | None] = mapped_column(String(16))
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    canonical_installed_item_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("installed_items.installed_item_id")
    )
    resolution_evidence: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    #  See §8 for the full protocol and for what each value means.

    first_recorded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("eic IS NULL OR eic ~ '^[A-Z0-9]{2,7}$'", name="eic_shape"),
        # [AMENDMENT — corrected.] Previously `niin ~ '^[0-9]{9}$'`, which rejected
        # Block A of the canonical `Niin` type (10-shared-packages.md §4.1) and
        # every NICN-form part (07 §4.8, `parts.niin_shape_matches_identifier_form`
        # above) — this table's `niin` FKs to `parts.niin`, so it must accept
        # every shape that CHECK allows. `cage_part_number` needs no case here:
        # `parts.niin` is NULL for those rows, and this column is NOT NULL, so
        # the FK itself already excludes them (see the docstring above).
        CheckConstraint(
            "niin ~ '^([0-9]{9}|[A-Z]{2}[A-Z0-9]{7})$' OR niin ~ '^[0-9A-Z]{4}LL[0-9A-Z]{3}$'",
            name="niin_shape",
        ),
        CheckConstraint(
            "provisional = false OR provisional_context IS NOT NULL",
            name="provisional_carries_context",
            # 11 §8.2: "ProvisionalContext is retained forever, including after
            # resolution.  It is the audit record of why this id exists."
        ),
        CheckConstraint(
            "identity_resolution IS NULL "
            "OR identity_resolution IN ('confirmed','superseded','rejected')",
            name="identity_resolution_vocabulary",
        ),
        CheckConstraint(
            "(identity_resolution = 'superseded') = (canonical_installed_item_id IS NOT NULL)",
            name="only_superseded_has_canonical",
            # Confirmation-by-adoption means provisional_id == canonical_id and
            # NO alias row is needed (11 §8.4).  A self-alias would make the
            # resolver a lookup where it should be an identity.
        ),
        CheckConstraint(
            "canonical_installed_item_id IS NULL "
            "OR canonical_installed_item_id <> installed_item_id",
            name="no_self_alias",
        ),
    )
```

#### 4.5.2 `ItemOccupancy` — the bitemporal fact, with the C10 exclusion constraints

```python
class ItemOccupancy(Base, RecordSeqMixin):
    """WHICH physical item occupied WHICH position, over WHICH real-world
    interval, as believed over WHICH record-time interval.

    This is the table that makes 04 §2's most consequential modeling decision
    enforceable rather than aspirational.  "A pump at position 233-04-A may be
    replaced five times over a hull's life" — that is five rows here, one
    position row, and five installed_items rows.
    """

    __tablename__ = "item_occupancies"

    occupancy_id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True)
    installed_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("installed_items.installed_item_id"), nullable=False
    )
    position_id: Mapped[UUID] = mapped_column(ForeignKey("positions.position_id"), nullable=False)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.asset_id"), nullable=False)

    valid_period: Mapped[TstzRange] = mapped_column(TSTZRANGE, nullable=False)
    """VALID TIME.  Lower bound = installed_at; upper bound = removal, or
    unbounded while installed.  This is the axis that answers "what was
    installed on 14 March" [04 §2 key decision 2]."""

    record_period: Mapped[TstzRange] = mapped_column(TSTZRANGE, nullable=False)
    """RECORD TIME.  Lower bound = when Registry came to believe this; upper
    bound = when Registry stopped believing it, or unbounded for current belief.
    This is the axis that answers "what did we BELIEVE on 14 March was
    installed."  04 §2: "A configuration correction entered three weeks late
    changes valid time WITHOUT REWRITING RECORD TIME, so a prediction computed
    on stale information remains explicable rather than appearing to have been
    computed from data that contradicts it." """

    # --- installation facts -------------------------------------------------
    install_source: Mapped[str] = mapped_column(String(32), nullable=False)
    install_source_ref: Mapped[str | None] = mapped_column(Text)
    """Which work order / maintenance action / 4790/CK / allowance import /
    reconciliation caused this.  07 §3.6: OPNAV 4790/CK is the Configuration
    Change Form — "Whenever any system, equipment, component, or unit within the
    ship is installed, removed, modified, or relocated, the change must be
    reported."  Transaction and action CODE VALUES are NOT PUBLICLY FOUND and are
    PLACEHOLDER.  There is no "ASI number": ASI is the Automated Shore Interface
    BATCH PROCESS (07 §3.6, §9), modelled as a batch event and never as a field."""

    usage_at_install: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    """A COPY of cumulative usage at installation, per counter type.  NOT
    AUTHORITATIVE — 01 §6 and 13 §5.3 rule 5.  Condition & Telemetry owns
    counter values [04 §2 "Does not own"].  Registry never corrects this and
    never serves it as a current value; it carries `as_of` and `source` inside
    the JSONB so a consumer can see how stale the snapshot was."""

    baseline_epoch_installed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    baseline_epoch_removed: Mapped[int | None] = mapped_column(BigInteger)

    # --- removal facts ------------------------------------------------------
    removal_disposition: Mapped[str | None] = mapped_column(String(32))
    failure_indicator: Mapped[bool | None] = mapped_column(Boolean)
    """Carried on `installed_item.removed` per 03 §6.  Registry records what the
    removing action reported; it does not adjudicate corrective-versus-preventive
    — that determination is Scheduling's, on `maintenance_action.recorded`
    [04 §6 key decision 4], and it is "the determinative input" for censoring
    [04 §4]."""

    corrects_occupancy_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("item_occupancies.occupancy_id")
    )

    __table_args__ = (
        # ---- THE TWO C10/D9 EXCLUSION CONSTRAINTS -------------------------
        ExcludeConstraint(
            ("position_id", "="),
            ("valid_period", "&&"),
            ("record_period", "&&"),
            using="gist",
            name="one_item_per_position_per_belief",
        ),
        ExcludeConstraint(
            ("installed_item_id", "="),
            ("valid_period", "&&"),
            ("record_period", "&&"),
            using="gist",
            name="one_position_per_item_per_belief",
        ),
        CheckConstraint("lower_inc(valid_period) AND NOT upper_inc(valid_period)", name="valid_closed_open"),
        CheckConstraint("lower_inc(record_period) AND NOT upper_inc(record_period)", name="record_closed_open"),
        CheckConstraint("NOT isempty(valid_period)", name="valid_nonempty"),
        CheckConstraint("NOT isempty(record_period)", name="record_nonempty"),
        CheckConstraint(
            "install_source IN ('initial','work_order','maintenance_action','work_package',"
            "'configuration_change','allowance_import','edge_reconciliation','correction')",
            name="install_source_vocabulary",
        ),
        Index(
            "ix_item_occupancies_bitemporal",
            "asset_id", "valid_period", "record_period",
            postgresql_using="gist",
        ),
        Index(
            "ix_item_occupancies_current",
            "asset_id", "valid_period",
            postgresql_using="gist",
            postgresql_where=text("upper_inf(record_period)"),
        ),
        Index("ix_item_occupancies_item", "installed_item_id"),
    )
```

**Why the exclusion constraints carry three operands and not two.** This is the single most likely place for an implementation to go wrong, so it is spelled out.

| Constraint written | Behaviour |
|---|---|
| `EXCLUDE (position_id WITH =, valid_period WITH &&)` | **Wrong.** Forbids overlapping valid time outright, so a correction — which by definition asserts a *different* item over an *overlapping* real-world interval — cannot be recorded at all. The implementer's only escape is to `UPDATE` the existing row, which destroys record time and reduces the model to uni-temporal. This is document 04 §2's second key decision silently deleted |
| `EXCLUDE (position_id WITH =, record_period WITH &&)` | **Wrong.** Permits two simultaneously-believed items in one position at one instant, which is C10 |
| `EXCLUDE (position_id WITH =, valid_period WITH &&, record_period WITH &&)` | **Correct.** Two rows may overlap in valid time *or* in record time, never both. A correction closes the superseded row's `record_period` at record time *T* and opens the corrector's at exactly *T*; the record periods are adjacent, not overlapping, so the constraint permits it. Two rows believed at the same instant covering the same real instant are rejected by the database |

`asset_id WITH =`, `position_id WITH =`, and `installed_item_id WITH =` in a GiST exclusion constraint require the **`btree_gist`** extension. The first Alembic revision must create it:

```python
# src/fathom_registry/migrations/versions/20260804T000000_registry_initial.py
def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    ...
```

A conformance test asserts the extension is present and that both exclusion constraints reject their negative cases against a real PostgreSQL container — `mocks cannot exercise ... EXCLUDE-constraint behaviour` [09 §2.2].

### 4.6 `ConfigurationBaseline` — the bitemporal snapshot and the epoch

```python
# src/fathom_registry/models/configuration_baseline.py

class ConfigurationBaseline(Base, RecordSeqMixin, ETagMixin, ClassifiedMixin):
    """04 §2: "A bitemporal snapshot of an asset's installed configuration."

    One row per (asset, valid interval, record interval).  The row is the
    aggregate root; `ConfigurationBaselineItem` is the materialized snapshot
    (§4.6.1); `baseline_epoch` is the fence every other sub-application blocks
    on [03 §5.4, D3, D4].
    """

    __tablename__ = "configuration_baselines"

    baseline_id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.asset_id"), nullable=False)

    baseline_epoch: Mapped[int] = mapped_column(BigInteger, nullable=False)
    """MONOTONIC PER ASSET, GAP-FREE, allocated per §4.0.2.

    03 §5.4: "Each asset's configuration carries a monotonically increasing
    `baseline_epoch`.  Any event whose correctness depends on configuration
    carries the epoch it was computed under.  A consumer that receives an event
    with an epoch ahead of its own configuration read model MUST BLOCK that event
    until the antecedent configuration event is applied."

    The antecedent rule is only implementable if the sequence is genuinely
    monotonic AND gap-aware.  With a gap, a blocked consumer waits for an epoch
    that will never arrive; the operational response to that is to weaken the
    block, and D4 returns."""

    valid_period: Mapped[TstzRange] = mapped_column(TSTZRANGE, nullable=False)
    record_period: Mapped[TstzRange] = mapped_column(TSTZRANGE, nullable=False)

    template_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("class_template_versions.template_version_id"), nullable=False
    )
    """The class template version this baseline resolved against (§9).  Pinned on
    the row so a historical effective configuration is reproducible after the
    class template advances."""
    deviation_high_water: Mapped[int] = mapped_column(Integer, nullable=False)
    """The highest `AssetDeviation.sequence` included in this baseline.  With
    `template_version_id` this pair is the complete recipe: template version +
    ordered deviations up to N + occupancy at the bitemporal coordinates.  A
    reproducibility test re-derives the snapshot from the pair (§11.3)."""

    change_source: Mapped[str] = mapped_column(String(32), nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    source_ref: Mapped[str | None] = mapped_column(Text)
    changed_item_count: Mapped[int] = mapped_column(Integer, nullable=False)

    supersedes_baseline_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("configuration_baselines.baseline_id")
    )
    corrects_baseline_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("configuration_baselines.baseline_id")
    )
    """`supersedes` advances valid time (a real change happened).  `corrects`
    advances record time over the SAME valid time (we learned we were wrong).
    They are different facts and consumers respond differently: a supersession
    invalidates predictions for the changed items; a correction invalidates
    predictions computed under the corrected belief, which may be a different
    set.  Conflating them into one nullable `previous_baseline_id` makes that
    distinction unrecoverable."""

    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("asset_id", "baseline_epoch", name="epoch_unique_per_asset"),
        ExcludeConstraint(
            ("asset_id", "="),
            ("valid_period", "&&"),
            ("record_period", "&&"),
            using="gist",
            name="no_bitemporal_overlap",
        ),
        CheckConstraint("baseline_epoch >= 1", name="epoch_starts_at_one"),
        CheckConstraint("lower_inc(valid_period) AND NOT upper_inc(valid_period)", name="valid_closed_open"),
        CheckConstraint("lower_inc(record_period) AND NOT upper_inc(record_period)", name="record_closed_open"),
        CheckConstraint("NOT isempty(valid_period)", name="valid_nonempty"),
        CheckConstraint("NOT isempty(record_period)", name="record_nonempty"),
        CheckConstraint("recorded_at = lower(record_period)", name="recorded_at_is_record_lower"),
        CheckConstraint(
            "NOT (supersedes_baseline_id IS NOT NULL AND corrects_baseline_id IS NOT NULL)",
            name="supersede_xor_correct",
        ),
        Index(
            "ix_configuration_baselines_bitemporal",
            "asset_id", "valid_period", "record_period",
            postgresql_using="gist",
        ),
        Index(
            "ix_configuration_baselines_current",
            "asset_id", "valid_period",
            postgresql_using="gist",
            postgresql_where=text("upper_inf(record_period)"),
        ),
        Index("ix_configuration_baselines_epoch_feed", "asset_id", "baseline_epoch"),
    )
```

#### 4.6.1 `ConfigurationBaselineItem` — the materialized snapshot

```python
class ConfigurationBaselineItem(Base):
    """The materialized snapshot for one baseline.  Produced by the baseline
    snapshot generator [04 §2 internal components].

    `DECISION` — the snapshot is MATERIALIZED, and the derivation of §9 remains
    its authority.  04 §2 requires this service be "read-heavy, served
    aggressively", and deriving a 1,200-position configuration from a template,
    an ordered deviation fold, and a bitemporal occupancy join on every read is
    not that.  The safety property is a test, not a hope: §11.3's
    `test_snapshot_equals_derivation` re-derives every baseline in the reference
    dataset and asserts equality.  A materialized cache whose equality with its
    definition is untested is a second source of truth.
    """

    __tablename__ = "configuration_baseline_items"

    baseline_id: Mapped[UUID] = mapped_column(
        ForeignKey("configuration_baselines.baseline_id", ondelete="CASCADE"), primary_key=True
    )
    position_id: Mapped[UUID] = mapped_column(
        ForeignKey("positions.position_id"), primary_key=True
    )
    #  PK (baseline_id, position_id) is the C10 invariant restated at the
    #  snapshot level: one item per position per snapshot, enforced by the
    #  primary key rather than by the generator's care.

    installed_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("installed_items.installed_item_id"), nullable=False
    )
    occupancy_id: Mapped[UUID] = mapped_column(
        ForeignKey("item_occupancies.occupancy_id"), nullable=False
    )
    system_id: Mapped[UUID] = mapped_column(ForeignKey("system_nodes.system_id"), nullable=False)
    niin: Mapped[str] = mapped_column(String(9), nullable=False)
    deviation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("asset_deviations.deviation_id")
    )
    conforms_to_template: Mapped[bool] = mapped_column(Boolean, nullable=False)
    """False where the occupant's NIIN differs from the template's
    `expected_niin`, or where the position exists only by deviation.  This is
    04 §2's "makes divergence a first-class, QUERYABLE fact rather than an
    inconsistency", and it is what `GET /assets/{id}/configuration?
    conforms_to_template=false` filters on."""

    __table_args__ = (
        Index("ix_cfg_baseline_items_item", "installed_item_id"),
    )
```

### 4.7 `AssetDeviation` — the ordered per-asset deviation set

```python
# src/fathom_registry/models/deviation.py

class AssetDeviation(Base, RecordSeqMixin, ETagMixin, ClassifiedMixin):
    """04 §2 key decision 3: "Configuration is modeled as a class template plus
    an EXPLICIT ORDERED DEVIATION SET PER ASSET."

    04 §2's fourth Phase 3 question — "How field changes and modernization
    alterations are represented as deviations" — is answered by `kind` plus
    `authority_kind`/`authority_reference`.  Values for ALT and field-change
    identifiers are PLACEHOLDER: 07 §4.1 documents ORDALT and MACHALT only as
    APL-number prefixes (`0R`, an alpha in the 6th position), and no ALT
    numbering scheme is verified in document 07.
    """

    __tablename__ = "asset_deviations"

    deviation_id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.asset_id"), nullable=False)

    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    """THE ORDER.  Gap-free per asset, allocated from `asset_deviation_sequence`
    on the §4.0.2 row-lock pattern.

    Deviations are folded in `sequence` order and NEVER in timestamp order.
    Two deviations may share a valid-time instant — a modernization availability
    lands dozens at once — and the fold is not commutative: "remove position P"
    then "add position P with a different NIIN" is not the same configuration as
    the reverse.  Ordering on a wall clock here would be D29 wearing the
    configuration model as a hat [03 §5.4, 11 §4.7]."""

    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    target_template_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("class_template_nodes.template_node_id")
    )
    target_template_position_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("class_template_positions.template_position_id")
    )
    target_position_id: Mapped[UUID | None] = mapped_column(ForeignKey("positions.position_id"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    valid_period: Mapped[TstzRange] = mapped_column(TSTZRANGE, nullable=False)
    record_period: Mapped[TstzRange] = mapped_column(TSTZRANGE, nullable=False)
    """Deviations are bitemporal for the same reason baselines are: a
    modernization recorded three weeks after the availability ended must change
    valid time without rewriting what was believed during those three weeks."""

    authority_kind: Mapped[str | None] = mapped_column(String(32))
    authority_reference: Mapped[str | None] = mapped_column(Text)
    baseline_epoch_introduced: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("asset_id", "sequence", name="deviation_sequence_per_asset"),
        CheckConstraint(
            "kind IN ('add_system','remove_system','add_position','remove_position',"
            "'substitute_part','relocate_position','alter_attribute')",
            name="deviation_kind_vocabulary",
        ),
        CheckConstraint("sequence >= 1", name="sequence_starts_at_one"),
        ExcludeConstraint(
            ("deviation_id", "="),
            ("record_period", "&&"),
            using="gist",
            name="deviation_no_record_overlap",
        ),
        Index("ix_asset_deviations_fold", "asset_id", "sequence"),
    )
```

### 4.8 `AllowanceDocument` [04 §2, 07 §4.1]

```python
# src/fathom_registry/models/allowance.py

class AllowanceDocument(Base, RecordSeqMixin, ETagMixin, ClassifiedMixin):
    """04 §2: "COSAL, APL, or AEL revision applicable to an asset."

    Registry owns the DOCUMENTS.  Supply owns allowance POSITIONS, the SNSL, and
    the Derivation Code [04 §2 "Does not own: ... inventory positions (Supply)";
    04 §7 Owns; 07 §4.9 assigns "SNSL 14 fields, Derivation Code" to Supply].
    There is deliberately no `derivation_code` column here.
    """

    __tablename__ = "allowance_documents"

    allowance_document_id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True)
    asset_id: Mapped[UUID] = mapped_column(ForeignKey("assets.asset_id"), nullable=False)

    doc_type: Mapped[str] = mapped_column(String(8), nullable=False)   # cosal|apl|ael|acl|mrpl
    doc_number: Mapped[str] = mapped_column(String(11), nullable=False)
    revision: Mapped[str] = mapped_column(String(16), nullable=False)
    is_incomplete: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    """07 §4.1: "A `P` prefix indicates an INCOMPLETE APL." """
    ael_column: Mapped[int | None] = mapped_column(Integer)
    """SCLSIS Record Type 2 field `AEL COL` (07 §3.1).  "AELs use eight columns,
    selected by CDMD-OA's `AEL COL` field" (07 §4.2)."""
    length_is_ambiguous: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    valid_period: Mapped[TstzRange] = mapped_column(TSTZRANGE, nullable=False)
    record_period: Mapped[TstzRange] = mapped_column(TSTZRANGE, nullable=False)
    import_batch_ref: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint(
            "doc_type IN ('cosal','apl','ael','acl','mrpl')", name="doc_type_vocabulary"
        ),
        CheckConstraint(
            # 07 §4.1, DOCUMENTED from PAFOS Ch. 6 App. B: Ordnance Fire Control
            # and Electronics APLs have 8; HM&E have 9; prefixes and suffixes can
            # expand to 11; AELs have 10.  07 §4.1 also records the source as
            # INTERNALLY INCONSISTENT on AEL length — App. B says 10, App. D's
            # positional scheme implies 11, and real examples show both
            # (`A004230048` at 10, `2-260034096` at 11).  The instruction is
            # explicit: "Model 10–11 and STATE THE AMBIGUITY."  `length_is_
            # ambiguous` is where the statement lives, and it is echoed on every
            # response so a consumer sees it rather than inferring it.
            "(doc_type IN ('apl','mrpl') AND length(doc_number) BETWEEN 8 AND 11) "
            "OR (doc_type IN ('ael','acl') AND length(doc_number) BETWEEN 10 AND 11) "
            "OR (doc_type = 'cosal')",
            name="doc_number_length_per_type",
        ),
        ExcludeConstraint(
            ("asset_id", "="),
            ("doc_type", "="),
            ("doc_number", "="),
            ("valid_period", "&&"),
            ("record_period", "&&"),
            using="gist",
            name="allowance_no_bitemporal_overlap",
        ),
        Index("ix_allowance_documents_asset", "asset_id", "doc_type"),
    )
```

Notes that must survive into the code:

- **`RIC` is where an APL/AEL number lives on an installed item** (§4.5.1); `AllowanceDocument.doc_number` is where it lives on the document. The two are joined on the *number*, which is a human/federation identifier — so the join is a **federation** join done explicitly in the allowance importer, never treated as a canonical join key [03 §3.3 rule 1].
- **Category semantics are recorded, not asserted.** 07 §4.1's HM&E APL categories (first two digits), Ordnance `00`, ORDALT `0R`, MACHALT alpha in position 6, Miscellaneous Repair Parts List always `89`, ACL last two `CA`–`CZ` except `X`, and the AEL first-digit series `0-` through `9-` are all DOCUMENTED and belong in the importer's validation table, sourced from document 07 §4.1 rather than restated in code comments.
- **No allowance *computation*.** `UR = POP × BRF / 4` and its thresholds are Supply's [07 §4.3, §4.9].

### 4.9 `Part`

```python
# src/fathom_registry/models/part.py

class Part(Base, RecordSeqMixin, ETagMixin, ClassifiedMixin):
    """The part catalog entry.  04 §2 Owns: "part catalog entries."

    Projects onto 03 §3.3 `PartRef`: niin (THE join key), nsn, apl,
    equipment_family.
    """

    __tablename__ = "parts"

    part_id: Mapped[UUID] = mapped_column(PgUUID, primary_key=True)
    """[AMENDMENT] The surrogate key, replacing `niin` as primary key. `niin` is
    NULL for `identifier_form = 'cage_part_number'` (07 §4.8: a cage/part-number
    item "has no NIIN at all"), and a nullable column cannot be a primary key —
    the prior schema made every `cage_part_number` row unrepresentable."""
    niin: Mapped[str | None] = mapped_column(String(9), unique=True)
    nsn: Mapped[str | None] = mapped_column(String(13))
    fsc: Mapped[str | None] = mapped_column(String(4))
    ncb: Mapped[str | None] = mapped_column(String(2))
    """07 §4.8: "NSN = FSC (4) + NCB (2) + item number (7).  FLIS stores NCB and
    item number SEPARATELY, not as a monolithic NIIN."  Both forms are carried;
    `niin` remains the join key because 03 §3.3 makes it so, and `nsn` is human
    reference and federation only."""

    identifier_form: Mapped[str] = mapped_column(String(24), nullable=False)
    """07 §4.8: "A realistic shipboard catalogue is HETEROGENEOUS, and almost no
    synthetic dataset gets this right."  One of: `nsn`, `permanent_nicn`,
    `temporary_nicn`, `licn`, `cage_part_number`.  Rules from 07 §4.8:
    permanent NICN carries `LL` in positions 5-6 AND `C` in position 7;
    temporary NICN carries `LL` in 5-6 and any letter except `C` in 7;
    an LICN NEVER APPEARS IN SUPPLY TRANSACTIONS and is local use only."""

    apl: Mapped[str | None] = mapped_column(String(11))
    cage: Mapped[str | None] = mapped_column(String(5))
    part_number: Mapped[str | None] = mapped_column(String(32))
    noun_name: Mapped[str] = mapped_column(Text, nullable=False)
    unit_of_issue: Mapped[str | None] = mapped_column(String(2))

    equipment_family: Mapped[str] = mapped_column(Text, nullable=False)
    """03 §3.3: "canonical grouping for model binding and calibration [D35]...
    It is DEFINED AND SERVED BY REFERENCE DATA, is versioned, and is a REQUIRED
    attribute of every part."  Registry validates against the read-through cache
    of Reference Data's served family list [12 §2.7] and refuses a part whose
    family is not in it.  Registry never authors a family (§1.5)."""
    equipment_family_taxonomy_version: Mapped[str] = mapped_column(Text, nullable=False)
    """12 §2.7: `equipment_family` shares the taxonomy's version register.  The
    version is pinned on the part so a model binding pinned to a taxonomy
    version pins its reference class too."""

    serialization_scope: Mapped[str] = mapped_column(String(16), nullable=False)
    """`item` | `lot` | `none`.  04 §2's first Phase 3 question: "which NIINs
    warrant item-level serialization against lot-level tracking."  Registry
    enforces it: `serialization_scope = 'item'` requires `InstalledItem.iuid`."""

    __table_args__ = (
        # [AMENDMENT — corrected.] The prior CHECK, `niin ~ '^[0-9]{9}$'`, both
        # (a) rejected Block A of the canonical `Niin` type (10-shared-packages.md
        # §4.1: `^(\d{9}|[A-Z]{2}[A-Z0-9]{7})$`) — the exact shape the synthetic
        # generator (13 §6.2) mints for roughly half its catalogue — and
        # (b) was unsatisfiable by construction for three of `identifier_form`'s
        # five values: `permanent_nicn`/`temporary_nicn` carry `LL` at positions
        # 5-6 (07 §4.8), and `cage_part_number` items have no NIIN at all. `licn`
        # is local-use-only per 07 §4.8 and is not further distinguished here.
        CheckConstraint(
            "identifier_form = 'cage_part_number' AND niin IS NULL"
            " OR identifier_form = 'nsn' AND niin ~ '^([0-9]{9}|[A-Z]{2}[A-Z0-9]{7})$'"
            " OR identifier_form IN ('permanent_nicn','temporary_nicn','licn')"
            "    AND niin ~ '^[0-9A-Z]{4}LL[0-9A-Z]{3}$'",
            name="niin_shape_matches_identifier_form",
            # The NICN/LICN branch enforces only the one positional rule 07 §4.8
            # states precisely (LL at positions 5-6, 9 characters total) — it does
            # not distinguish permanent from temporary NICN (position 7: `C` versus
            # any other letter) or LICN from NICN, because 07 §4.8 gives no
            # complete positional grammar for those and a CHECK enforcing an
            # invented one would be worse than one that enforces what is actually
            # specified. A residual gap, recorded rather than guessed at.
        ),
        CheckConstraint("nsn IS NULL OR nsn ~ '^[0-9]{13}$'", name="nsn_thirteen_digits"),
        CheckConstraint(
            "identifier_form IN ('nsn','permanent_nicn','temporary_nicn','licn','cage_part_number')",
            name="identifier_form_vocabulary",
        ),
        CheckConstraint(
            "identifier_form <> 'cage_part_number' OR (cage IS NOT NULL AND part_number IS NOT NULL)",
            name="cage_part_number_requires_cage_and_part_number",
        ),
        CheckConstraint(
            "serialization_scope IN ('item','lot','none')", name="serialization_scope_vocabulary"
        ),
        Index("ix_parts_apl", "apl"),
        Index("ix_parts_family", "equipment_family"),
    )
```

`Niin` and `Nsn` on the wire are the constrained scalars from `packages/canonical-schemas` [10 §4.1]. **[AMENDMENT — corrected.]** This previously restated `Niin`'s pattern as `^\d{9}$`, predating 10 §4.1's actual fix (`^(\d{9}|[A-Z]{2}[A-Z0-9]{7})$`, accepting both blocks 13 §6.2 mints) and contradicting this section's own `niin_shape`/`niin_shape_matches_identifier_form` CHECKs above, which already implement the wider shape. `Nsn` remains `^\d{13}$`. The database CHECKs mirror the wire constraints so a bulk import cannot bypass them.

### 4.10 The complete owned-aggregate inventory

Document 11 §7.2 requires the conflict-policy registry to **enumerate every owned aggregate at startup and fail if one is neither declared nor explicitly defaulted** — the C20 fix. Registry's inventory is therefore normative:

| Aggregate | Table(s) | Conflict policy [03 §11] |
|---|---|---|
| `hierarchy_scheme` | `hierarchy_schemes` | `ENTERPRISE_AUTHORITATIVE_NOT_EDGE_WRITABLE` (explicit default) |
| `class` | `classes` | default, explicit |
| `class_template` | `class_template_versions`, `_nodes`, `_positions` | default, explicit |
| `asset` | `assets` | default, explicit |
| `system_node` | `system_nodes` | default, explicit |
| `position` | `positions` | default, explicit |
| `installed_item` | `installed_items`, `item_occupancies` | **`ENTERPRISE_AUTHORITATIVE_PROVISIONAL_EDGE`** |
| `configuration_baseline` | `configuration_baselines`, `configuration_baseline_items` | **`ENTERPRISE_AUTHORITATIVE_PROVISIONAL_EDGE`** |
| `asset_deviation` | `asset_deviations` | default, explicit |
| `allowance_document` | `allowance_documents` | default, explicit |
| `part` | `parts` | default, explicit |
| `configuration_change_proposal` | `configuration_change_proposals` | `APPEND_ONLY_SERVER_ADJUDICATED` |

Twelve aggregates, twelve declarations, none implicit.

---

## 5. The bitemporal resolver — the exact queries

This section is the reason this document exists. It gives the queries, not the concept.

### 5.1 The three questions, and the one predicate that answers all of them

| Question | `as_of` (valid time) | `as_known_at` (record time) |
|---|---|---|
| **A.** What is installed *now*, as we believe *now*? | `now()` | `now()` |
| **B.** What was installed on 14 March, as we believe *now*? | `2026-03-14T00:00:00Z` | `now()` |
| **C.** What did we *believe on 1 April* was installed on 14 March? | `2026-03-14T00:00:00Z` | `2026-04-01T00:00:00Z` |
| **D.** What did we believe on 1 April was installed *then*? | `2026-04-01T00:00:00Z` | `2026-04-01T00:00:00Z` |

There is **one** predicate and **one** query. A, B, C and D differ only in the binding of two parameters. Document 04 §2 names B and C as the two the system must answer; A is B with the default, and D is the audit question — *"Predictions are audited against the latter"* — and it is the one a naive implementation cannot express at all.

```sql
--  THE BITEMPORAL PREDICATE.  Every configuration read in this service uses it.
--    valid_period  @> :as_of         -- what was TRUE at as_of
--    record_period @> :as_known_at   -- ...according to what we BELIEVED at as_known_at
--
--  Both are '[)' containment tests, not comparisons.  Neither timestamp is ever
--  compared against another timestamp to decide precedence [03 §5.4, 11 §4.7].
```

`upper_inf(record_period)` is the equivalent of `record_period @> now()` for a current-belief row, and the partial indexes of §4.5.2 and §4.6 are built on it so question A and B take the cheap plan. The resolver uses `upper_inf()` when `as_known_at` is the request instant and `@>` otherwise; the results are identical by construction, and a test asserts it (§11.3).

### 5.2 REG-Q1 — resolve the governing baseline

```sql
-- REG-Q1.  Returns AT MOST ONE ROW.  Uniqueness is a database guarantee, not a
-- LIMIT 1: `no_bitemporal_overlap` (§4.6) forbids two rows for one asset
-- overlapping in both axes, so two rows satisfying both containments cannot
-- exist.  Writing LIMIT 1 here would mask a constraint failure as a silent
-- arbitrary pick, which is the class of defect this whole model exists to
-- prevent — so LIMIT 1 is PROHIBITED and the repository raises on >1 row.
SELECT b.baseline_id,
       b.baseline_epoch,
       b.asset_id,
       b.template_version_id,
       b.deviation_high_water,
       lower(b.valid_period)  AS effective_from,
       upper(b.valid_period)  AS effective_to,
       lower(b.record_period) AS recorded_from,
       upper(b.record_period) AS recorded_to,
       b.change_source,
       b.change_reason,
       b.changed_item_count,
       b.classification,
       b.version
  FROM configuration_baselines b
 WHERE b.asset_id      =  :asset_id
   AND b.valid_period  @> CAST(:as_of AS timestamptz)
   AND b.record_period @> CAST(:as_known_at AS timestamptz);
```

Three outcomes, and each maps to a distinct response:

| Rows | Meaning | Response |
|---|---|---|
| 1 | Resolved | `200` with the configuration |
| 0 | No configuration was believed at `as_known_at` to cover `as_of` — the asset was not yet commissioned, was decommissioned, or `as_known_at` precedes the asset's first record | `404` `urn:fathom:problem:registry:no-baseline-at-coordinates`, with `as_of` and `as_known_at` echoed as extension members and the asset's `earliest_recorded_from` so the caller can correct the coordinates without a second round trip |
| >1 | **A database invariant has failed.** | `500`, `urn:fathom:problem:registry:bitemporal-invariant-violated`, and an immediate page. This is not a recoverable condition and must never be papered over |

### 5.3 REG-Q2 — the snapshot read (the fast path)

```sql
-- REG-Q2.  Served from the materialized snapshot.  One index scan.
SELECT i.position_id,
       p.position_code,
       i.system_id,
       s.hsc_code,
       s.eswbs,                       -- NULL unless the asset's scheme family is eswbs
       s.eic          AS system_eic,  -- federation/human reference only
       i.installed_item_id,
       i.niin,
       ii.iuid,
       ii.serial_or_lot,
       ii.eic         AS item_eic,    -- federation/human reference only
       ii.provisional,
       ii.identity_resolution,
       lower(o.valid_period) AS installed_at,
       o.usage_at_install,
       i.conforms_to_template,
       i.deviation_id
  FROM configuration_baseline_items i
  JOIN positions       p  ON p.position_id       = i.position_id
  JOIN system_nodes    s  ON s.system_id         = i.system_id
  JOIN installed_items ii ON ii.installed_item_id = i.installed_item_id
  JOIN item_occupancies o ON o.occupancy_id      = i.occupancy_id
 WHERE i.baseline_id = :baseline_id
   AND (:system_id IS NULL OR i.system_id = :system_id)
   AND (:conforms_to_template IS NULL OR i.conforms_to_template = :conforms_to_template)
 ORDER BY p.position_code, i.position_id     -- stable sort key for the cursor
 LIMIT :limit OFFSET 0;                      -- keyset paging in the real query, see §6.3
```

### 5.4 REG-Q3 — the derivation (the authority, and the test oracle)

REG-Q3 answers the same question **without** the snapshot, straight from occupancy. It is the definition of what REG-Q2 caches, it is what the reconciliation and correction paths use, and it is the oracle for `test_snapshot_equals_derivation`.

```sql
-- REG-Q3.  The bitemporal occupancy join.  No snapshot, no cache.
SELECT o.position_id,
       p.position_code,
       p.system_id,
       o.installed_item_id,
       ii.niin,
       lower(o.valid_period)  AS installed_at,
       upper(o.valid_period)  AS removed_at,       -- NULL while installed
       lower(o.record_period) AS believed_from,
       o.usage_at_install,
       o.occupancy_id,
       ii.provisional
  FROM item_occupancies o
  JOIN positions p ON p.position_id = o.position_id
  JOIN installed_items ii ON ii.installed_item_id = o.installed_item_id
 WHERE o.asset_id      =  :asset_id
   AND o.valid_period  @> CAST(:as_of AS timestamptz)
   AND o.record_period @> CAST(:as_known_at AS timestamptz)
   -- The position must itself exist at as_of.  A position removed by a
   -- modernization cannot appear in a configuration after its removal even if a
   -- stale occupancy row overlaps, and this is the join that enforces it.
   AND p.established_period @> CAST(:as_of AS timestamptz)
 ORDER BY p.position_code, o.position_id;
```

**The `one_item_per_position_per_belief` exclusion constraint is what makes REG-Q3 correct.** Without it the query returns two occupants for one position at one bitemporal coordinate and the resolver has to pick — and every available tie-break is either a wall clock (D29) or arbitrary. The constraint is not a data-quality nicety; it is the resolver's proof of determinism.

### 5.5 The resolver, as code

```python
# src/fathom_registry/repositories/configuration.py
"""The bitemporal configuration resolver.  Document 04 §2, key decision 2.

The ONLY module in this service permitted to write a temporal predicate.  Every
other repository that needs configuration calls in here.  Nine hand-written
`valid_period @> ...` predicates would be nine chances to omit `record_period`,
and omitting `record_period` silently reduces the model to uni-temporal while
every test that only ever passes `as_known_at=now()` still passes.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from fathom_registry.errors import BitemporalInvariantViolated, NoBaselineAtCoordinates


@dataclass(frozen=True)
class BitemporalCoordinates:
    """The two axes, resolved once at the API boundary and threaded unchanged.

    Both fields are non-optional HERE even though both query parameters are
    optional on the wire: the API layer applies the defaults (§6.3) so that no
    code below the boundary can accidentally mean "now" by passing None.
    """

    as_of: dt.datetime
    as_known_at: dt.datetime

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_known_at.tzinfo is None:
            raise ValueError("bitemporal coordinates are timezone-aware [03 §4]")


@dataclass(frozen=True)
class ResolvedBaseline:
    baseline_id: UUID
    asset_id: UUID
    baseline_epoch: int
    template_version_id: UUID
    deviation_high_water: int
    effective_from: dt.datetime
    effective_to: dt.datetime | None
    recorded_from: dt.datetime
    recorded_to: dt.datetime | None
    change_source: str
    change_reason: str
    changed_item_count: int


_REG_Q1 = text(
    """
    SELECT b.baseline_id, b.asset_id, b.baseline_epoch, b.template_version_id,
           b.deviation_high_water,
           lower(b.valid_period)  AS effective_from,
           upper(b.valid_period)  AS effective_to,
           lower(b.record_period) AS recorded_from,
           upper(b.record_period) AS recorded_to,
           b.change_source, b.change_reason, b.changed_item_count
      FROM configuration_baselines b
     WHERE b.asset_id      =  :asset_id
       AND b.valid_period  @> CAST(:as_of AS timestamptz)
       AND b.record_period @> CAST(:as_known_at AS timestamptz)
    """
)


async def resolve_baseline(
    session: AsyncSession, asset_id: UUID, at: BitemporalCoordinates
) -> ResolvedBaseline:
    """REG-Q1.  Exactly one row, or a named failure.  Never a silent pick."""
    rows = (
        await session.execute(
            _REG_Q1,
            {"asset_id": asset_id, "as_of": at.as_of, "as_known_at": at.as_known_at},
        )
    ).mappings().all()

    if len(rows) == 1:
        return ResolvedBaseline(**rows[0])
    if not rows:
        raise NoBaselineAtCoordinates(asset_id=asset_id, at=at)
    #  Structurally unreachable: `no_bitemporal_overlap` forbids it.  Reached
    #  only if the constraint was dropped, if btree_gist is missing, or if a
    #  migration recreated the table without it.  All three are incidents.
    raise BitemporalInvariantViolated(
        asset_id=asset_id, at=at, baseline_ids=[r["baseline_id"] for r in rows]
    )


_REG_Q3 = text(
    """
    SELECT o.position_id, p.position_code, p.system_id, o.installed_item_id,
           ii.niin, ii.iuid, ii.serial_or_lot, ii.provisional,
           lower(o.valid_period)  AS installed_at,
           upper(o.valid_period)  AS removed_at,
           o.usage_at_install, o.occupancy_id
      FROM item_occupancies o
      JOIN positions p       ON p.position_id        = o.position_id
      JOIN installed_items ii ON ii.installed_item_id = o.installed_item_id
     WHERE o.asset_id      =  :asset_id
       AND o.valid_period  @> CAST(:as_of AS timestamptz)
       AND o.record_period @> CAST(:as_known_at AS timestamptz)
       AND p.established_period @> CAST(:as_of AS timestamptz)
     ORDER BY p.position_code, o.position_id
    """
)


async def derive_occupancy(
    session: AsyncSession, asset_id: UUID, at: BitemporalCoordinates
) -> list[dict[str, object]]:
    """REG-Q3.  The derivation.  Authority for REG-Q2's snapshot, and the
    oracle for `test_snapshot_equals_derivation` (§11.3)."""
    return [
        dict(r)
        for r in (
            await session.execute(
                _REG_Q3,
                {"asset_id": asset_id, "as_of": at.as_of, "as_known_at": at.as_known_at},
            )
        ).mappings()
    ]
```

An ORM-expression equivalent, for callers that need to compose further filters:

```python
from sqlalchemy import Select, and_, cast, func, literal_column, select
from sqlalchemy.dialects.postgresql import TSTZRANGE

from fathom_registry.models import ConfigurationBaseline, InstalledItem, ItemOccupancy, Position


def bitemporal(entity, at: BitemporalCoordinates):
    """The predicate, as a reusable SQLAlchemy clause.  `contains()` renders
    PostgreSQL's `@>`."""
    return and_(
        entity.valid_period.contains(at.as_of),
        entity.record_period.contains(at.as_known_at),
    )


def occupancy_query(asset_id: UUID, at: BitemporalCoordinates) -> Select:
    return (
        select(
            ItemOccupancy.position_id,
            Position.position_code,
            Position.system_id,
            ItemOccupancy.installed_item_id,
            InstalledItem.niin,
            func.lower(ItemOccupancy.valid_period).label("installed_at"),
            func.upper(ItemOccupancy.valid_period).label("removed_at"),
        )
        .join(Position, Position.position_id == ItemOccupancy.position_id)
        .join(InstalledItem, InstalledItem.installed_item_id == ItemOccupancy.installed_item_id)
        .where(ItemOccupancy.asset_id == asset_id)
        .where(bitemporal(ItemOccupancy, at))
        .where(Position.established_period.contains(at.as_of))
        .order_by(Position.position_code, ItemOccupancy.position_id)
    )
```

### 5.6 The mutation procedures — how a period is closed

Reads are the easy half. These three procedures are where a bitemporal table is actually got wrong, so each is given exactly.

**Notation:** `T` is the record time allocated by §4.0.1 in this transaction; `V` is the domain-supplied effective instant.

#### 5.6.1 Supersession — a real-world change (advance valid time)

```sql
-- 1. Close the outgoing occupancy in VALID time at V.  Record time is untouched:
--    we did not stop believing the old row, the world moved.
UPDATE item_occupancies
   SET valid_period = tstzrange(lower(valid_period), CAST(:V AS timestamptz), '[)'),
       baseline_epoch_removed = :new_epoch,
       removal_disposition = :disposition,
       failure_indicator = :failure_indicator,
       record_seq = :next_record_seq
 WHERE position_id = :position_id
   AND upper_inf(record_period)
   AND valid_period @> CAST(:V AS timestamptz);

-- 2. Open the incoming occupancy at V, unbounded above in valid time.
INSERT INTO item_occupancies (occupancy_id, installed_item_id, position_id, asset_id,
                              valid_period, record_period, install_source,
                              install_source_ref, usage_at_install,
                              baseline_epoch_installed, record_seq)
VALUES (:occupancy_id, :installed_item_id, :position_id, :asset_id,
        tstzrange(CAST(:V AS timestamptz), NULL, '[)'),
        tstzrange(CAST(:T AS timestamptz), NULL, '[)'),
        :install_source, :install_source_ref, :usage_at_install,
        :new_epoch, :next_record_seq);
```

Note what step 1 does **not** do: it does not close `record_period`. The outgoing row remains the currently-believed record of an occupancy that has now ended. Closing record time here would be the single most common bitemporal error — it would make the removal look like a retraction, and question C would report that we never believed the item was there.

#### 5.6.2 Correction — we learned we were wrong (advance record time)

```sql
-- 1. Close the incorrect row in RECORD time at T.  Valid time is untouched:
--    the claim it made about the world is preserved exactly as made.
UPDATE item_occupancies
   SET record_period = tstzrange(lower(record_period), CAST(:T AS timestamptz), '[)'),
       record_seq = :next_record_seq
 WHERE occupancy_id = :wrong_occupancy_id
   AND upper_inf(record_period);

-- 2. Insert the corrected row.  Its valid_period MAY overlap the row just
--    closed — that is what a correction IS — and the exclusion constraint
--    permits it because the record periods are now adjacent, not overlapping.
INSERT INTO item_occupancies (occupancy_id, installed_item_id, position_id, asset_id,
                              valid_period, record_period, install_source,
                              install_source_ref, usage_at_install,
                              baseline_epoch_installed, corrects_occupancy_id, record_seq)
VALUES (:occupancy_id, :installed_item_id, :position_id, :asset_id,
        tstzrange(CAST(:corrected_from AS timestamptz), CAST(:corrected_to AS timestamptz), '[)'),
        tstzrange(CAST(:T AS timestamptz), NULL, '[)'),
        'correction', :source_ref, :usage_at_install,
        :new_epoch, :wrong_occupancy_id, :next_record_seq);
```

Four rules on corrections, all mandatory:

1. **The closed row is never deleted and never updated again.** It is the audit record of what was believed, and document 03 §13 requires every store declare whether it is legally immutable or operationally append-only. Registry's declaration is in §12.5.
2. **`record_period` upper bound and the successor's lower bound are the same instant `T`.** No gap. A gap makes `as_known_at` inside it return zero rows, which surfaces as a spurious `404` on an audit query — the exact query the bitemporal model was built to serve.
3. **A correction allocates a new `baseline_epoch`.** It changes what consumers should believe, so it is a `configuration.baseline_changed` with `corrects_baseline_id` set, and PdM must invalidate predictions computed under the corrected belief [04 §4 "Configuration change invalidates predictions, loudly"].
4. **A correction is never applied by rewriting a published event** — §8.4's rule generalizes: Registry's outbox rows are signed [11 §10.2], and a rewrite is indistinguishable from tampering.

#### 5.6.3 Retraction — it never happened (close record time, open nothing)

Used when an occupancy was recorded entirely in error. Step 1 of §5.6.2 alone, with no step 2. The baseline recomputes without that position occupied, a new epoch is allocated, and `changed_item_count` includes the vacated position. There is no physical delete and no `is_deleted` flag: the closed `record_period` *is* the tombstone, and it carries when we stopped believing it, which a boolean cannot.

### 5.7 Detecting a stale epoch — the D3/D4 read

Document 03 §3.3's last rule: *"A prediction computed against a superseded baseline is invalid, and consumers must be able to detect that **without inference**."* Registry supplies the detection in one read.

```sql
-- REG-Q4.  The fence read.  Served by GET /assets/{id}/current-baseline-epoch.
SELECT b.baseline_epoch      AS current_epoch,
       b.baseline_id         AS current_baseline_id,
       lower(b.record_period) AS recorded_from,
       (SELECT next_epoch - 1 FROM asset_baseline_epoch WHERE asset_id = :asset_id)
                             AS allocated_high_water
  FROM configuration_baselines b
 WHERE b.asset_id = :asset_id
   AND upper_inf(b.record_period)
   AND upper_inf(b.valid_period);
```

`current_epoch` and `allocated_high_water` are returned **separately and both**. They are equal in steady state. They differ for exactly the interval between an epoch allocation and its baseline row becoming visible, and a consumer that sees `allocated_high_water > current_epoch` knows a configuration change is in flight and must not treat `current_epoch` as final. A single-value response would force the consumer to infer that condition, which is what document 03 §3.3 forbids.

Every configuration response carries `baseline_epoch`, `baseline_id`, and `epoch_is_current: bool`. `epoch_is_current` is `false` whenever the resolved epoch is not the asset's current one — which is *always* true for a historical `as_of` or `as_known_at`, and that is the point: a scoring run that resolved configuration at `as_known_at = T0` and publishes after `T1` reads `epoch_is_current: false` on its own input and its `BaselineFencedComputation` [11 §3.5] refuses to publish. Tested by `test_d3_stale_epoch_is_detectable_in_one_read` (§11.3).

---

## 6. API surface

Base path `/api/v1/registry/`. Every operation is declared through `operation_extra()` from `fathom_contracts.operation` [10 §5.1], which registers the declaration for the `OAS005` completeness check and emits `x-substitution`, `x-side-effects`, optionally `x-agent-eligible`, `x-fathom-aggregate` (which `OAS013` uses to prove a `changed_since` read exists), and `x-fathom-singleton-carveout`.

> **`DECISION` on the annotation helper.** Document 09 §5.1 shows `fathom_py_common.openapi.operation()` returning `{"openapi_extra": ...}` and document 10 §5.1 shows `fathom_contracts.operation.operation_extra()` used as `openapi_extra=`. These are two helpers for one job. This service uses **document 10's `operation_extra()`**, because document 09 §1.2 assigns the public API of `packages/contracts` to document 10, and because only document 10's version registers the declaration (needed for `OAS005`) and carries `x-fathom-aggregate` (needed for `OAS013`, which is Registry's most load-bearing spec rule). Logged in §15 item 6 as a duplication for document 09 to resolve.

### 6.1 The complete operation table

Document 04 §2's eight rows, expanded to every operation the contract actually requires. Rows marked **[04 §2]** are named there; rows marked **[03]** are required by document 03 §4/§15 and not enumerated in document 04 §2; the row marked **[11 §8.3]** is required verbatim by the provisional-identity protocol.

| # | Operation | `x-substitution` | `x-side-effects` | agent | Aggregate | Source |
|---|---|---|---|---|---|---|
| 1 | `GET /assets?hull_or_tail=&uic=&domain=&class_id=&changed_since=&cursor=` | required | none | ✓ | `asset` | [04 §2]. **[amendment]** No query parameter was declared here — closes `51-operator-console.md` §22 row 4 (blocking): with no filter, no operation answers "which asset is hull DDG 113" or maps a `unit_uic` to an asset, and `changed_since` is obligation 5's rebuild path for every consumer that projects `Asset` |
| 2 | `GET /assets/{asset_id}` | required | none | ✓ | `asset` | [04 §2] |
| 3 | `GET /assets/{asset_id}/configuration` | required | none | ✓ | `configuration_baseline` | [04 §2] |
| 4 | `GET /assets/{asset_id}/systems` | required | none | ✓ | `system_node` | [04 §2] |
| 5 | `GET /assets/{asset_id}/positions` | required | none | ✓ | `position` | [04 §2] |
| 6 | `GET /assets/{asset_id}/installed-items` | required | none | ✓ | `installed_item` | [04 §2] |
| 7 | `GET /classes/{class_id}` | required | none | ✓ | `class` | [04 §2] |
| 8 | `GET /classes/{class_id}/template` | required | none | ✓ | `class_template` | [04 §2] · singleton carve-out |
| 9 | `GET /parts/{niin}` | required | none | ✓ | `part` | [04 §2] |
| 10 | `GET /parts` (`?apl=&equipment_family=&changed_since=`) | required | none | ✓ | `part` | [04 §2] |
| 11 | `GET /assets/{asset_id}/allowances` | required | none | ✓ | `allowance_document` | [04 §2] |
| 12 | `POST /assets/{asset_id}/configuration-changes` | required | state-changing | ✗ | `configuration_baseline` | [04 §2] |
| 13 | `GET /configuration-baselines` (`?asset_id=&changed_since=&cursor=`) | required | none | ✓ | `configuration_baseline` | [03 §4, D5] |
| 14 | `GET /configuration-baselines/{baseline_id}` | required | none | ✓ | `configuration_baseline` | [03 §4] |
| 15 | `GET /assets/{asset_id}/current-baseline-epoch` | required | none | ✓ | `configuration_baseline` | [03 §5.4, D3/D4] · singleton carve-out |
| 16 | `GET /installed-items` (`?asset_id=&position_id=&niin=&provisional=&changed_since=&cursor=`) | required | none | ✓ | `installed_item` | [03 §4, D5] |
| 17 | `GET /installed-items/{installed_item_id}` | required | none | ✓ | `installed_item` | [03 §4] |
| 18 | `POST /installed-items` | required | state-changing | ✗ | `installed_item` | **[11 §8.3]** |
| 19 | `GET /systems` (`?asset_id=&changed_since=&cursor=`) | required | none | ✓ | `system_node` | [03 §4, D5] |
| 20 | `GET /positions` (`?asset_id=&system_id=&changed_since=&cursor=`) | required | none | ✓ | `position` | [03 §4, D5] |
| 21 | `GET /classes` (`?changed_since=&cursor=`) | required | none | ✓ | `class` | [03 §4, D5] |
| 22 | `GET /allowance-documents` (`?asset_id=&changed_since=&cursor=`) | required | none | ✓ | `allowance_document` | [03 §4, D5] |
| 23 | `GET /assets/{asset_id}/deviations` | required | none | ✓ | `asset_deviation` | [04 §2 key decision 3] |
| 24 | `GET /configuration-changes` (`?asset_id=&status=`) | required | none | ✓ | `configuration_change_proposal` | [03 §7.2, C39] |
| 25 | `POST /configuration-changes/{proposal_id}/claim` | required | state-changing | ✗ | `configuration_change_proposal` | [03 §7.2, D16] |
| 26 | `POST /configuration-changes/{proposal_id}/adjudicate` | required | state-changing | ✗ | `configuration_change_proposal` | [03 §7.2, D16] |
| 27 | `POST /configuration-changes/bulk` (`X-Backfill`) | required | state-changing | ✗ | `configuration_baseline` | [03 §4 bulk writes, D10/C7] |
| 28 | `POST /allowance-documents/bulk` (`X-Backfill`) | required | state-changing | ✗ | `allowance_document` | [03 §4 bulk writes] |
| 29 | `POST /assets` | internal | state-changing | ✗ | `asset` | [04 §2] |
| 30 | `PATCH /assets/{asset_id}` | internal | state-changing | ✗ | `asset` | [04 §2] |
| 31 | `POST /classes`, `PUT /classes/{class_id}/template` | internal | state-changing | ✗ | `class`, `class_template` | [04 §2] |
| 32 | `POST /parts`, `PATCH /parts/{niin}` | internal | state-changing | ✗ | `part` | [04 §2 Owns] |
| 33 | `POST /hierarchy-schemes` | internal | state-changing | ✗ | `hierarchy_scheme` | [07 §3.4] |

**No operation in this service is `proposal-only`.** Registry receives proposals (rows 24–26) but does not *create* them on an agent's behalf; row 12 with `mode: proposed` creates one as a side effect of a state-changing submission, and it is annotated `state-changing` because it also writes an `AssetDeviation` candidate. Agent eligibility is therefore confined to the read surface, which is correct for a service whose entire agent value is configuration lookup.

**Every read operation is `x-agent-eligible`.** Permitted because `x-side-effects: none` [03 §8.1], and required in practice: the Maintainer Copilot and the Diagnostic agent both need "what is installed at this position" and "what does this hull's configuration diverge from", and configuration-aware retrieval [04 §11] filters on the baseline. Registry ships `registry-configuration-lookup.v1` in `packages/agent-tooling/manifests/registry/`.

### 6.2 Wire schemas

Canonical types are **imported** from `packages/canonical-schemas`, never redefined [09 §4.1]. New payload schemas live in `fathom_schemas.registry` — in the shared package, not in this service — because they are event payloads and document 03 §5.5 requires payload schemas live there and register with the schema registry.

```python
# packages/canonical-schemas/src/fathom_schemas/registry.py  (excerpt)
"""Registry wire schemas and event payloads.  Document 03 §6 Registry rows."""
from __future__ import annotations

import datetime as dt
from enum import StrEnum
from uuid import UUID

from pydantic import Field, model_validator

from ._base import FathomModel, Niin, NonEmptyStr, UtcDateTime
from .classification import ClassificationLabel
from .identity import AssetRef, InstalledItemRef, PartRef, PositionRef, SystemRef


class ConfigurationLine(FathomModel):
    """One position and its occupant, at a resolved bitemporal coordinate.

    Carries `position_id` AND `installed_item_id` as separate, both-required
    fields.  03 §3.3 rule 3 and [C10, D9]: "A payload identifying a physical item
    identifies it as `installed_item_id`.  A payload identifying a location
    identifies it as `position_id`."  A consumer that needs one and receives the
    other has been given the inherited-degradation defect.
    """

    position_id: UUID
    position_code: NonEmptyStr = Field(description="Human reference only [03 §3.3].")
    system_id: UUID
    installed_item_id: UUID
    niin: Niin
    iuid: NonEmptyStr | None = None
    serial_or_lot: NonEmptyStr | None = None
    installed_at: UtcDateTime
    removed_at: UtcDateTime | None = None
    usage_at_install: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "A COPY of cumulative usage at installation, per counter type.  NOT "
            "AUTHORITATIVE — Condition & Telemetry owns counter values [04 §2]."
        ),
    )
    provisional: bool = False
    identity_resolution: str | None = None
    conforms_to_template: bool
    deviation_id: UUID | None = None
    eswbs: NonEmptyStr | None = Field(
        default=None,
        description=(
            "Present ONLY where the asset's HSC scheme family is ESWBS [07 §3.4].  "
            "Human reference and external federation only; never a join key."
        ),
    )
    hsc_code: NonEmptyStr
    system_eic: NonEmptyStr | None = None
    item_eic: NonEmptyStr | None = None


class AssetConfiguration(FathomModel):
    """The response of `GET /assets/{asset_id}/configuration`.

    The four temporal fields are the whole contract.  A consumer that stores
    `lines` without `recorded_at_resolved` cannot answer 04 §2's second question
    and cannot audit a prediction.
    """

    asset_id: UUID
    baseline_id: UUID
    baseline_epoch: int = Field(ge=1, description="03 §5.4 [D3, D4].")
    epoch_is_current: bool = Field(
        description=(
            "False whenever the resolved epoch is not the asset's current epoch — "
            "always false for a historical `as_of` or `as_known_at`.  03 §3.3: "
            "consumers must detect a superseded baseline WITHOUT INFERENCE."
        )
    )

    as_of_resolved: UtcDateTime = Field(description="The valid-time coordinate used.")
    as_known_at_resolved: UtcDateTime = Field(description="The record-time coordinate used.")
    effective_from: UtcDateTime
    effective_to: UtcDateTime | None = Field(description="Null while in force.")
    recorded_from: UtcDateTime
    recorded_to: UtcDateTime | None = Field(
        description="Null while this is the currently-believed baseline."
    )

    hsci: NonEmptyStr = Field(
        description=(
            "The asset's Hierarchical Structure Code scheme selector [07 §3.1, §3.4].  "
            "A consumer MUST NOT assume ESWBS: there is no universal HSC layout."
        )
    )
    scheme_family: NonEmptyStr
    scheme_code_values_are_synthetic: bool

    lines: list[ConfigurationLine]
    next_cursor: str | None = None
    classification: ClassificationLabel


class BaselineEpochState(FathomModel):
    """`GET /assets/{asset_id}/current-baseline-epoch` — the D3/D4 fence read."""

    asset_id: UUID
    current_epoch: int = Field(ge=1)
    current_baseline_id: UUID
    allocated_high_water: int = Field(
        ge=1,
        description=(
            "The highest epoch ALLOCATED for this asset.  Equals `current_epoch` in "
            "steady state; exceeds it while a configuration change is in flight.  "
            "Returned separately so a consumer need not infer the condition (§5.7)."
        ),
    )
    recorded_from: UtcDateTime
    classification: ClassificationLabel


# ---- event payloads, document 03 §6 Registry rows -------------------------

class AssetRegistered(FathomModel):
    """`fathom.registry.asset.registered`.  03 §6: "AssetRef, class,
    commissioning data"."""

    asset: AssetRef
    class_id: NonEmptyStr
    class_display_name: NonEmptyStr
    hsci: NonEmptyStr
    commissioned_on: dt.date | None = None
    initial_baseline_id: UUID
    baseline_epoch: int = Field(ge=1)


class AssetStatusChanged(FathomModel):
    """`fathom.registry.asset.status_changed`.  03 §6: "operational status, OFRP
    phase, deployment state".  All three vocabularies are served by Reference
    Data and are PLACEHOLDER in the demonstration (§4.3)."""

    asset_id: UUID
    operational_status: NonEmptyStr
    previous_operational_status: NonEmptyStr | None = None
    ofrp_phase: NonEmptyStr | None = None
    deployment_state: NonEmptyStr | None = None
    effective_at: UtcDateTime


class BaselineChangeKind(StrEnum):
    INITIAL = "initial"
    SUPERSESSION = "supersession"
    CORRECTION = "correction"
    RETRACTION = "retraction"


class ChangedConfigurationItem(FathomModel):
    position_id: UUID
    installed_item_id_before: UUID | None = None
    installed_item_id_after: UUID | None = None
    niin_before: Niin | None = None
    niin_after: Niin | None = None


CHANGED_ITEM_INLINE_MAX = 200
"""Above this, the changed set moves to `changed_items_ref`.

03 §6 and [D27]: "references to the run artifact rather than inline result
sets", and 09 §8.2's DoD item "No event carries a result set that could exceed
the broker message limit."  An initial baseline or an allowance import touches
every position on a hull — ~1,200 on a surface asset [06 §7] — which inlined
would be a multi-megabyte event against a 1 MB default broker limit.

**[AMENDMENT]** Unlike every other D27 reference in this corpus
(`prediction.updated`, `telemetry.batch_ingested`), which are reference-ONLY,
this field is a union: EXACTLY one of `changed_items` / `changed_items_ref` is
set (`_exactly_one_changed_set_representation` above), never both, never
neither. A consumer that reads `changed_items` unconditionally works on every
routine change and breaks on exactly the two cases that matter most — an
initial baseline (~1,200 positions) and a bulk allowance import — either
raising on `None` or, worse, silently iterating zero items and treating a
full-hull change as a no-op. Every consumer of `configuration.baseline_changed`
(21, 22, 26, 27) MUST branch on which field is set and fetch `changed_items_ref`
before applying, not assume the inline shape."""


class ConfigurationBaselineChanged(FathomModel):
    """`fathom.registry.configuration_baseline.changed`.  03 §6: "`baseline_id`,
    `baseline_epoch`, changed installed-item set, effective date".

    03 §6: "the MOST CONSEQUENTIAL EVENT IN THE SYSTEM.  It invalidates every
    prediction attached to affected installed items, carries the new epoch, and
    is A CORRECTNESS SIGNAL RATHER THAN AN INFORMATIONAL ONE."
    """

    asset_id: UUID
    baseline_id: UUID
    baseline_epoch: int = Field(ge=1)
    previous_baseline_id: UUID | None = None
    previous_baseline_epoch: int | None = Field(default=None, ge=1)
    change_kind: BaselineChangeKind
    effective_from: UtcDateTime = Field(description="Valid-time lower bound.")
    recorded_from: UtcDateTime = Field(description="Record-time lower bound.")
    changed_item_count: int = Field(ge=0)
    changed_items: list[ChangedConfigurationItem] | None = Field(
        default=None, description=f"Inline when count <= {CHANGED_ITEM_INLINE_MAX}."
    )
    changed_items_ref: NonEmptyStr | None = Field(
        default=None, description="s3:// URI when the set exceeds the inline cap [D27]."
    )
    change_source: NonEmptyStr
    source_ref: NonEmptyStr | None = None

    @model_validator(mode="after")
    def _exactly_one_changed_set_representation(self) -> "ConfigurationBaselineChanged":
        inline, ref = self.changed_items is not None, self.changed_items_ref is not None
        if inline == ref:
            raise ValueError("exactly one of `changed_items` / `changed_items_ref` [D27]")
        if inline and len(self.changed_items or []) > CHANGED_ITEM_INLINE_MAX:
            raise ValueError(f"inline changed set exceeds {CHANGED_ITEM_INLINE_MAX} [D27]")
        return self


class InstalledItemInstalled(FathomModel):
    """`fathom.registry.installed_item.installed`.  03 §6: "InstalledItemRef,
    position, install date, source work order, usage-at-install"."""

    installed_item: InstalledItemRef
    asset_id: UUID
    position: PositionRef
    installed_at: UtcDateTime
    source_work_order_id: UUID | None = None
    source_maintenance_action_id: UUID | None = None
    usage_at_install: dict[str, float] = Field(default_factory=dict)
    replaced_installed_item_id: UUID | None = Field(
        default=None,
        description=(
            "What came out, where anything did.  Consumed by Condition & "
            "Telemetry to OPEN A NEW COUNTER EPOCH rather than continue the prior "
            "item's accumulation [04 §3 Events consumed; 03 §11 usage counters; D9]."
        ),
    )
    baseline_id: UUID
    baseline_epoch: int = Field(ge=1)


class InstalledItemRemoved(FathomModel):
    """`fathom.registry.installed_item.removed`.  03 §6: "InstalledItemRef,
    removal date, disposition, failure indicator"."""

    installed_item: InstalledItemRef
    asset_id: UUID
    position: PositionRef
    removed_at: UtcDateTime
    disposition: NonEmptyStr
    failure_indicator: bool | None = Field(
        default=None,
        description=(
            "As reported by the removing action.  Registry does NOT adjudicate "
            "corrective-versus-preventive; that determination is Scheduling's on "
            "`maintenance_action.recorded` [04 §6], and it is the determinative "
            "censoring input [04 §4]."
        ),
    )
    baseline_id: UUID
    baseline_epoch: int = Field(ge=1)


class IdentityResolution(StrEnum):
    CONFIRMED = "confirmed"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class InstalledItemIdentityResolved(FathomModel):
    """`fathom.registry.installed_item.identity_resolved`.

    Mandated by 11 §8.4 verbatim: "Registry publishes
    `installed_item.identity_resolved` carrying `{provisional_id, canonical_id,
    resolution: confirmed|superseded, evidence, baseline_epoch}` on
    `fathom.registry.installed_item.v1`."

    ABSENT FROM DOCUMENT 03 §6's CATALOG.  Logged in §15 item 2 as a required
    document 03 edit; the event is published regardless, because 11 §8.4 makes it
    the ONLY mechanism by which a consumer can interpret an event already
    published under a provisional id.
    """

    provisional_id: UUID
    canonical_id: UUID
    resolution: IdentityResolution
    asset_id: UUID
    position_id: UUID
    evidence: dict[str, object]
    baseline_epoch: int = Field(ge=1)
    resolved_at: UtcDateTime


class AllowanceUpdated(FathomModel):
    """`fathom.registry.allowance_document.updated`.  03 §6: "COSAL/APL/AEL
    revision for an asset"."""

    asset_id: UUID
    allowance_document_id: UUID
    doc_type: NonEmptyStr
    doc_number: NonEmptyStr
    revision: NonEmptyStr
    previous_revision: NonEmptyStr | None = None
    effective_from: UtcDateTime
    is_incomplete: bool = Field(
        description="A `P` prefix indicates an incomplete APL [07 §4.1]."
    )
    length_is_ambiguous: bool = Field(
        description=(
            "True for AEL/ACL numbers: 07 §4.1 records the source as internally "
            "inconsistent on AEL length (10 per App. B, 11 per App. D) and "
            "instructs 'Model 10–11 and STATE THE AMBIGUITY'.  This field is the "
            "statement, carried to consumers rather than left in a comment."
        )
    )
    affected_niins: list[Niin] | None = None
    affected_niins_ref: NonEmptyStr | None = None
```

### 6.3 The bitemporal query parameters — exact handling

```python
# src/fathom_registry/api/v1/configuration.py
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from fathom_contracts.operation import SideEffects, Substitution, operation_extra
from fathom_py_common.pagination import CursorParams
from fathom_schemas.registry import AssetConfiguration, BaselineEpochState

router = APIRouter(tags=["configuration"])


@router.get(
    "/assets/{asset_id}/configuration",
    response_model=AssetConfiguration,
    openapi_extra=operation_extra(
        operation_id="registry_get_asset_configuration",
        substitution=Substitution.REQUIRED,
        side_effects=SideEffects.NONE,
        agent_eligible=True,
        aggregate="configuration_baseline",
        summary=(
            "Resolve an asset's installed configuration at a valid-time instant, "
            "as it was believed at a record-time instant."
        ),
    ),
)
async def get_asset_configuration(
    asset_id: UUID,
    response: Response,
    as_of: Annotated[
        dt.datetime | None,
        Query(
            description=(
                "VALID TIME.  'What was installed at this instant.'  RFC 3339 with "
                "an explicit offset [03 §4].  Defaults to the request instant."
            )
        ),
    ] = None,
    as_known_at: Annotated[
        dt.datetime | None,
        Query(
            description=(
                "RECORD TIME.  'As Registry believed it at this instant.'  RFC 3339 "
                "with an explicit offset.  Defaults to the request instant, which "
                "yields current belief.  Supply a past instant to reproduce what a "
                "consumer would have read then — this is the axis predictions are "
                "audited against [04 §2]."
            )
        ),
    ] = None,
    system_id: Annotated[UUID | None, Query()] = None,
    conforms_to_template: Annotated[bool | None, Query()] = None,
    page: Annotated[CursorParams, Depends()] = ...,
    svc: Annotated[ConfigurationService, Depends(get_configuration_service)] = ...,
) -> AssetConfiguration:
    at = resolve_coordinates(as_of, as_known_at)
    result = await svc.resolve(asset_id, at, system_id, conforms_to_template, page)
    #  ETag is derived from (baseline_id, version) — a historical bitemporal
    #  coordinate resolves to an immutable row, so its representation is
    #  indefinitely cacheable and a conditional GET is a cheap 304 [04 §2 key
    #  decision 4].  A CURRENT-belief read is not: recorded_to is null and the
    #  row can be closed by a correction at any moment.
    response.headers["ETag"] = etag_for(result)
    response.headers["Cache-Control"] = (
        "private, max-age=86400, immutable"
        if result.recorded_to is not None
        else "private, no-cache"
    )
    return result
```

```python
# src/fathom_registry/api/coordinates.py
"""Bitemporal query-parameter resolution.  ONE implementation, used by every
operation that accepts `as_of`/`as_known_at`.

Six rules, all of them load-bearing:

1. Both parameters are OPTIONAL on the wire and BOTH DEFAULT TO THE REQUEST
   INSTANT, captured ONCE.  Two separate `now()` calls would let `as_of` and
   `as_known_at` differ by microseconds on a default request, so a "current"
   read could resolve a baseline whose record period opened between the two
   reads.  Rare, non-reproducible, and it presents as a phantom 404.

2. The request instant is captured from the request scope, not from the
   database and not per-parameter.  It is a REQUEST timestamp, never an
   ordering input — 11 §4.7's prohibition is on precedence, and this is
   parameter defaulting.

3. A naive datetime is a 422.  03 §4 requires RFC 3339 with an explicit
   offset; ruff's DTZ rules forbid naive datetimes in the service [09 §7.4].

4. `as_known_at` in the FUTURE is a 422, not a clamp.  A future record time
   asks what Registry will believe, which is not a question with an answer.
   Clamping silently returns current belief and the caller never learns its
   parameter was ignored — which is exactly how a consumer comes to believe it
   audited a historical read when it did not.

5. `as_of` in the future is ALLOWED.  A scheduled modernization has a future
   valid-time lower bound, and "what will be installed after this availability"
   is a real planning question [04 §6's availability framing].

6. Neither value is ever compared to the other.  There is no rule that
   `as_known_at >= as_of` and asserting one would be wrong: "what did we believe
   in January about what would be installed in June" is legitimate and is how a
   planned configuration is audited.
"""
from __future__ import annotations

import datetime as dt

from fathom_py_common.problems import ProblemException

from fathom_registry.repositories.configuration import BitemporalCoordinates
from fathom_registry.schemas.problems import RegistryProblem


def resolve_coordinates(
    as_of: dt.datetime | None,
    as_known_at: dt.datetime | None,
    *,
    request_instant: dt.datetime,
) -> BitemporalCoordinates:
    for name, value in (("as_of", as_of), ("as_known_at", as_known_at)):
        if value is not None and value.tzinfo is None:
            raise ProblemException(
                type=RegistryProblem.NAIVE_TIMESTAMP,
                status=422,
                detail=f"{name} requires an explicit UTC offset (RFC 3339) [03 §4].",
                parameter=name,
            )

    resolved_as_known_at = as_known_at or request_instant
    if resolved_as_known_at > request_instant:
        raise ProblemException(
            type=RegistryProblem.AS_KNOWN_AT_IN_FUTURE,
            status=422,
            detail=(
                "as_known_at is a record-time instant and cannot be in the future; "
                "Registry cannot report what it will believe.  Omit the parameter "
                "for current belief."
            ),
            as_known_at=resolved_as_known_at.isoformat(),
            request_instant=request_instant.isoformat(),
        )

    return BitemporalCoordinates(
        as_of=as_of or request_instant,
        as_known_at=resolved_as_known_at,
    )
```

`as_of` and `as_known_at` are accepted, with identical semantics, on: operation 3 (`/configuration`), 4 (`/systems`), 5 (`/positions`), 6 (`/installed-items`), 11 (`/allowances`), 16 (`/installed-items`), 20 (`/positions`), 22 (`/allowance-documents`), and 23 (`/deviations`). Every one of them threads a single `BitemporalCoordinates` into the repository. `OAS-REG-1`, a Registry-specific spec rule added to `tools/check_openapi.py`, fails the build if an operation accepts `as_of` without also accepting `as_known_at` — a half-bitemporal operation is a uni-temporal operation wearing the parameter name.

### 6.4 `changed_since` — the exact snapshot-read implementation

Document 03 §4 makes this mandatory over every projected aggregate and states why: *"This is the rebuild path; the event bus is not"* `[D5, D25, D30]`. Document 03 §15 obligation 5 makes it a **contract term** binding a substitute. Document 11 §3.5's epoch fence and §2.8's `ChangedSinceRebuilder` both call it.

**`DECISION` — `changed_since` accepts an opaque watermark token or an RFC 3339 instant, and pagination is always on `record_seq`.**

Document 03 §4 names the parameter and not its type. Both forms are needed and they are needed for different callers:

- **`rt:<record_seq>`** — what a rebuilder uses. Exact, gap-free, and free of any wall clock. `next_changed_since` in every response returns this form, so a correct rebuild loop never constructs a timestamp.
- **RFC 3339 instant** — what a human, an operator tool, or a substituting partner that only has timestamps uses. Translated to a watermark on entry and never used for ordering.

```python
# src/fathom_registry/repositories/changed_since.py
"""The `changed_since` change-feed reader.  03 §4, §15 obligation 5, [D5].

WHY `record_seq` AND NOT A TIMESTAMP — the property that makes the feed
COMPLETE rather than merely ordered.

`record_seq` is allocated by `UPDATE registry_record_seq ... RETURNING`
(§4.0.2) INSIDE the writing transaction.  That UPDATE takes a row lock which is
held until commit, so a second writer for the same aggregate BLOCKS ON
ALLOCATION until the first commits.  Allocation order therefore EQUALS commit
order, and there is never a row with a lower `record_seq` that becomes visible
after a higher one.

That is the whole safety argument.  With a Postgres SEQUENCE, or with a
timestamp assigned at statement time, two concurrent writers can allocate 41 and
42 and commit in the order 42, 41 — so a reader that pages to the end, sees 42,
and stores watermark 42 PERMANENTLY MISSES 41.  The read model is then silently
short one row, forever, with no error.  Applied to a configuration baseline, the
missing row is a component replacement that never invalidates a prediction: D2's
outcome reached by a different route.

Consequences, all mandatory:
  * ORDER BY is `record_seq` alone.  Never `recorded_at`, never `updated_at`.
  * The feed returns FULL CURRENT ROW STATE, not a diff.  A rebuilder replays
    upserts, which is what makes the feed idempotent and restartable.
  * Rows whose `record_period` has been CLOSED are included.  A correction and a
    retraction are exactly the facts a rebuilder must not miss, and a filter on
    `upper_inf(record_period)` would hide both.
  * NOTHING is ever physically deleted, so the feed needs no tombstone channel:
    a closed `record_period` IS the tombstone and carries its own record time.
"""
from __future__ import annotations

import base64
import datetime as dt
from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

MAX_LIMIT = 500
DEFAULT_LIMIT = 100


@dataclass(frozen=True)
class ChangedSincePage:
    rows: Sequence[dict[str, Any]]
    next_cursor: str | None
    next_changed_since: str
    high_water: int


def _encode_cursor(record_seq: int) -> str:
    """Opaque base64url over the stable sort key [03 §4 pagination]."""
    return base64.urlsafe_b64encode(f"rs:{record_seq}".encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> int:
    pad = "=" * (-len(cursor) % 4)
    raw = base64.urlsafe_b64decode(cursor + pad).decode()
    if not raw.startswith("rs:"):
        raise ValueError("malformed cursor")
    return int(raw[3:])


async def resolve_watermark(
    session: AsyncSession, table: str, changed_since: str | None, cursor: str | None
) -> int:
    """Cursor wins over `changed_since`: a caller mid-page is resuming, and
    re-applying the original watermark would replay the whole page."""
    if cursor is not None:
        return _decode_cursor(cursor)
    if changed_since is None:
        return 0
    if changed_since.startswith("rt:"):
        return int(changed_since[3:])

    #  RFC 3339 form.  Translated ONCE, here, to the largest record_seq whose
    #  row was recorded strictly before the instant.  `recorded_at` is read
    #  exactly once, in this translation, and never again — in particular it is
    #  never an ORDER BY and never a page boundary.
    instant = dt.datetime.fromisoformat(changed_since)
    if instant.tzinfo is None:
        raise ValueError("changed_since requires an explicit offset (RFC 3339) [03 §4]")
    row = await session.execute(
        text(
            f"SELECT coalesce(max(record_seq), 0) AS wm "  # noqa: S608 - table from a fixed allowlist
            f"FROM {table} WHERE recorded_at < CAST(:instant AS timestamptz)"
        ),
        {"instant": instant},
    )
    return int(row.scalar_one())


async def read_page(
    session: AsyncSession,
    *,
    table: str,
    columns: str,
    watermark: int,
    limit: int,
    extra_where: str = "",
    params: dict[str, Any] | None = None,
) -> ChangedSincePage:
    limit = min(max(limit, 1), MAX_LIMIT)
    sql = text(
        f"""
        SELECT {columns}, record_seq
          FROM {table}
         WHERE record_seq > :watermark
           {extra_where}
         ORDER BY record_seq
         LIMIT :fetch
        """  # noqa: S608 - `table`/`columns` come from a per-aggregate fixed allowlist
    )
    rows = (
        await session.execute(sql, {"watermark": watermark, "fetch": limit + 1, **(params or {})})
    ).mappings().all()

    has_more = len(rows) > limit
    page = [dict(r) for r in rows[:limit]]
    last = page[-1]["record_seq"] if page else watermark
    return ChangedSincePage(
        rows=page,
        next_cursor=_encode_cursor(last) if has_more else None,
        next_changed_since=f"rt:{last}",
        high_water=last,
    )
```

Response envelope for every `changed_since` feed:

```json
{
  "items": [ ... full current row state ... ],
  "next_cursor": "cnM6NDIxNw",
  "next_changed_since": "rt:4217",
  "feed_complete": true
}
```

`feed_complete` is `true` when `next_cursor` is null — the rebuilder has reached the end and may store `next_changed_since` as its watermark. **No total count** on an unbounded collection [03 §4].

**The rebuild contract Registry offers, stated for the eight consumers that depend on it:**

1. Start at `changed_since` absent. Page to `feed_complete: true`. Store `next_changed_since`.
2. Resume with the stored token at any later time. Rows are full state; apply as upserts, keyed on the aggregate's own identifier.
3. The feed is **complete at the moment `feed_complete` is returned** — see the allocation argument above. There is no "wait for in-flight writes" step and no clock-skew window.
4. `installed_item` and `configuration_baseline` feeds carry `baseline_epoch`, so a rebuilder ends with a correct `EpochFence.current_epoch` [11 §3.5] and does not have to derive one.
5. Registry retains all rows for the life of the system — nothing is pruned and nothing is physically deleted — so requirement 5 of document 03 §10's substitution protocol (*"A historical backfill capability... the substitute must be able to serve history through `changed_since`"*) is satisfied by construction rather than by a retention setting. `test_d5_read_model_rebuild_from_changed_since_only` [11 §11.3] is run against this service with the broker down.

### 6.5 The configuration-change submission

`POST /assets/{asset_id}/configuration-changes` is the one state-changing operation document 04 §2 marks `required`, and it carries two modes.

```python
class ConfigurationChangeMode(StrEnum):
    DIRECT = "direct"
    PROPOSED = "proposed"


class ConfigurationChangeRequest(FathomModel):
    """`POST /assets/{asset_id}/configuration-changes`.

    Shaped on OPNAV 4790/CK, the Configuration Change Form [07 §3.6]:
    "Whenever any system, equipment, component, or unit within the ship is
    installed, removed, modified, or relocated, the change must be reported."
    Transaction and action CODE VALUES are NOT PUBLICLY FOUND (07 §3.6) and are
    PLACEHOLDER, generated from a reserved set and recorded in the divergence
    list [13 §5.3 rule 7].

    There is no `asi_number` field.  ASI is the Automated Shore Interface BATCH
    PROCESS — job `JSS117` (Unit) or `JSS135` (Force) — not an identifier
    (07 §3.6, 07 §9).  Batch provenance goes in `import_batch_ref`.
    """

    mode: ConfigurationChangeMode
    effective_at: UtcDateTime = Field(
        description="The VALID-TIME instant of the change.  May be in the past."
    )
    change_kind: BaselineChangeKind
    installations: list[InstallationRequest] = Field(default_factory=list)
    removals: list[RemovalRequest] = Field(default_factory=list)
    deviations: list[DeviationRequest] = Field(default_factory=list)
    corrects_baseline_id: UUID | None = None

    expected_baseline_epoch: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Optional optimistic fence.  When supplied and not equal to the "
            "asset's current epoch, the submission is rejected 409 "
            "`urn:fathom:problem:registry:baseline-epoch-conflict` with both epochs "
            "as extension members.  This is how a caller that read configuration, "
            "computed a change, and submits it avoids writing against a "
            "configuration that moved underneath it — the write-side counterpart of "
            "11 §3.5's `BaselineFencedComputation` [D3]."
        ),
    )

    submitting_authority: NonEmptyStr
    source_ref: NonEmptyStr | None = None
    import_batch_ref: NonEmptyStr | None = None
    transaction_code: NonEmptyStr | None = Field(
        default=None, description="OPNAV 4790/CK transaction code.  PLACEHOLDER [07 §3.6]."
    )
    action_code: NonEmptyStr | None = Field(
        default=None, description="OPNAV 4790/CK action code.  PLACEHOLDER [07 §3.6]."
    )
```

`mode: direct` writes the change and allocates an epoch. `mode: proposed` writes a `configuration_change_proposal` and nothing else. Which mode a caller may use is an authorization decision, not a client choice: the `require_authz` dependency [09 §5.5] rejects `direct` from a principal without enterprise configuration-management authority and rejects `proposed` from nobody.

**Why `proposed` exists here.** Document 03 §11: *"Configuration baselines — Enterprise-authoritative; edge submits configuration-change proposals."* Document 03 §7.2's `kind` vocabulary includes `configuration_change`, and §7.2.1's authority table gives it `maintainer` (edge-submitted) then **Registry confirmation**, at `item`/`asset` blast radius only. Finding **C39** was that the conflict policy required proposed configuration changes *"with no matching proposal kind and no endpoint"* — the kind was added to document 03 §7.2 and this is the endpoint.

Document 04 §2 lists neither a `Proposal` aggregate nor a proposal operation for Registry, so this is an extension of document 04 §2 and is logged in §15 item 1. The adjudication path follows document 03 §7.2's four rules without variation:

| Rule [03 §7.2] | Implementation |
|---|---|
| `evidence` required and non-empty, rejected at the API boundary | `ConfigurationChangeProposal.evidence: list[Evidence] = Field(min_length=1)`; `source_trust` on each item, and a proposal resting solely on non-program content is flagged to the adjudicator |
| **Re-validation at approval is mandatory** | `POST /configuration-changes/{id}/adjudicate` re-resolves the asset's *current* configuration and rejects if `baseline_epoch` has advanced past the proposal's, or if `valid_until` has passed. Validation at creation is insufficient [D16] |
| **Adjudication requires a claim** | `POST /configuration-changes/{id}/claim` takes a lease; adjudication requires `If-Match` on the claimed ETag, and `require_if_match` returns `428` when the header is absent [09 §5.4] |
| **Authority checked against blast radius** | `authority_class` is set by Registry at creation from §7.2.1's table — `maintainer` — and re-validated at adjudication. `blast_radius` is `item` or `asset`; a submission computing `class` or `fleet` is rejected, because §7.2.1's table declares those scopes not applicable for this kind |

Domain policy is enforced **in the operation, not by agent behaviour** [03 §9 item 2]: a submission's `position_id` must be present in the asset's current baseline; the installed NIIN must be APL-authorized for that position (via `ClassTemplatePosition.expected_niin` and `AllowanceDocument`, with a deviation required where it is not); and `installed_item_id` must not already be occupying another position. These hold regardless of what an agent proposed or why.

---

## 7. Events

### 7.1 Topics, keys, and compaction

| Topic | Aggregate | Partition key | Compaction key | Compacted? | Retention |
|---|---|---|---|---|---|
| `fathom.registry.asset.v1` | `asset` | `asset_id` | **`NULL`** | **No** | 30 days (domain events) |
| `fathom.registry.configuration_baseline.v1` | `configuration_baseline` | `asset_id` | `baseline_id` | Yes | Indefinite (state-carrying) |
| `fathom.registry.installed_item.v1` | `installed_item` | `asset_id` | `installed_item_id` | Yes | Indefinite |
| `fathom.registry.allowance_document.v1` | `allowance_document` | `asset_id` | `allowance_document_id` | Yes | Indefinite |
| `fathom.registry.proposal.v1` | `proposal` | `asset_id` | `proposal_id` | Yes | Indefinite |

**Why the asset topic is deliberately not compacted.** Document 11 §2.2's `outbox_compaction_key_distinct` CHECK makes `compaction_key = partition_key` unwritable, and for the asset aggregate the aggregate key *is* `asset_id` — the two coincide. The resolution is not to weaken the CHECK but to recognize that a compacted asset topic would collapse a hull's status history to one record, which is exactly the D5 failure the CHECK exists to prevent. `asset.status_changed` is a history, not a state snapshot, and the state snapshot is served by `GET /assets/{id}` and rebuilt by `changed_since`. `compaction_key` is left `NULL`, which the CHECK permits, and the topic carries the 30-day domain-event retention of document 03 §5.1.

**Why installed-item-scoped events partition on `asset_id`.** `DECISION`. Document 03 §5.1 specifies `asset_id` for asset-scoped events and the own scope identifier for fleet-, NIIN-, and class-scoped events; installed-item scope is not enumerated. Partitioning on `installed_item_id` would place `installed_item.removed` for the outgoing pump and `installed_item.installed` for its replacement in **different partitions**, and document 03 §5.1 is explicit that per-asset ordering within a topic *"is the only ordering guarantee the design relies on"* and that *"no design may depend on cross-asset or cross-topic ordering."* A consumer would then legitimately apply the install before the removal, briefly hold two items in one position, and — for Condition & Telemetry, which opens a new counter epoch on install [04 §3] — attribute the interval to the wrong item. That is D9. `asset_id` it is, and the compaction key remains `installed_item_id` so compaction still preserves per-item state.

**[AMENDMENT]** This appeared to expose a gap in the library — `document 11 §2.3`'s `OutboxWriter.emit()` signature has no `partition_key` parameter, while §2.2's outbox table has a `partition_key` column that is `NOT NULL` — but 11 §2.3 answers it differently than proposed: `partition_key` is derived internally from `scope`/`subject`, never supplied by the caller, so no signature change was needed. Logged in §15 item 4, resolved.

### 7.2 Envelope construction — exact

Every event is written through `outbox.emit()` inside the caller's transaction [11 §2.3]. `emit()` builds the full document 03 §5.4 envelope; the service supplies only the fields below.

```python
# src/fathom_registry/events/publishers.py
"""Outbox publication.  Called FROM `services/`, INSIDE the caller's
transaction [09 §4.1, 11 §2.3].  Never opens a transaction, never publishes.
"""
from __future__ import annotations

from uuid import UUID

from fathom_schemas.envelope import EventScope, EventSubject
from fathom_schemas.registry import (
    ConfigurationBaselineChanged,
    InstalledItemInstalled,
    InstalledItemIdentityResolved,
)
from fathom_sync import OutboxWriter, UnitOfWork

PRODUCER_NODE = "enterprise"
"""03 §5.4 `producer_node`: "which DEPLOYMENT INSTANCE of that slug emitted this
event: "enterprise" | "edge:<asset_id>"."

REGISTRY IS ENTERPRISE-ONLY, SO THIS VALUE IS ALWAYS THE LITERAL "enterprise",
IN EVERY DEPLOYMENT, WITHOUT EXCEPTION.

Registry has no edge deployment profile [11 §1.2: "`registry` — Edge profile:
No"], because configuration baselines are enterprise-authoritative and "two
divergent views of what is installed is the most damaging available conflict"
[03 §11].  There is exactly one instance of this slug minting exactly one
monotonic sequence, so the dedup key
`(producer_slug, producer_node_id, monotonic_seq)` [11 §4.2] can never collide
for Registry.

This is asserted at startup and in the conformance suite rather than trusted:
`test_registry_producer_node_is_always_enterprise` (§11.2) drains every event a
full reference-dataset run produces and asserts the field.  If Registry ever
acquires an edge profile, that test fails first — which is the correct order of
events, because acquiring one would mean two nodes minting configuration
baselines, and every downstream epoch fence would be reading a sequence that is
no longer a total order for the asset.

Note the two distinct grammars, which must not be conflated: the ENVELOPE field
`producer_node` uses 03 §5.4's vocabulary ("enterprise" | "edge:<asset_id>"),
while `clock.hlc.node_id` uses 11 §4.2's deployment-instance form
("registry@ashore-1").  See §15 item 7.
"""


async def publish_baseline_changed(
    uow: UnitOfWork,
    outbox: OutboxWriter,
    *,
    payload: ConfigurationBaselineChanged,
    classification: dict,
    causation_id: UUID | None,
) -> None:
    """`fathom.registry.configuration_baseline.changed`.

    03 §6: "the most consequential event in the system... a CORRECTNESS SIGNAL
    rather than an informational one."  Eight declared consumers: pdm, pma,
    knowledge-retrieval, failure-intel, fleet-status, maintenance, supply,
    telemetry.
    """
    outbox.emit(
        uow,
        event_type="fathom.registry.configuration_baseline.changed",
        aggregate="configuration_baseline",
        aggregate_id=str(payload.baseline_id),
        scope=EventScope.ASSET,
        subject=EventSubject(asset_id=payload.asset_id),
        partition_key=str(payload.asset_id),
        compaction_key=str(payload.baseline_id),      # MUST differ from partition_key [D5]
        payload=payload,
        classification=classification,
        baseline_epoch=payload.baseline_epoch,        # ALWAYS set on this event
        causation_id=causation_id,
    )


async def publish_installed_item_installed(
    uow: UnitOfWork,
    outbox: OutboxWriter,
    *,
    payload: InstalledItemInstalled,
    classification: dict,
    causation_id: UUID | None,
) -> None:
    """`fathom.registry.installed_item.installed`.

    `causation_id` is the `event_id` of the `configuration_baseline.changed`
    that carries the same epoch, ALWAYS.  03 §5.4's antecedent rule resolves a
    blocked event "via `causation_id` or by reading `changed_since` from the
    Registry" — so Registry supplies BOTH resolution paths, and a consumer that
    blocks on an unseen epoch can follow the causation chain without a network
    call [D4].  Setting it to None here would leave `changed_since` as the only
    path, which works but costs a round trip per blocked event on a topic that
    can burst.
    """
    outbox.emit(
        uow,
        event_type="fathom.registry.installed_item.installed",
        aggregate="installed_item",
        aggregate_id=str(payload.installed_item.installed_item_id),
        scope=EventScope.INSTALLED_ITEM,
        subject=EventSubject(installed_item_id=payload.installed_item.installed_item_id),
        partition_key=str(payload.asset_id),          # §7.1, DECISION
        compaction_key=str(payload.installed_item.installed_item_id),
        payload=payload,
        classification=classification,
        baseline_epoch=payload.baseline_epoch,
        causation_id=causation_id,
    )
```

**Emission ordering within one transaction.** A configuration change emits several events. They are emitted in this order, which fixes their `monotonic_seq` order and therefore their delivery order within the partition:

1. `configuration_baseline.changed` — **first, always.** It carries the new epoch, and every subsequent event in the transaction cites it as `causation_id`. A consumer that receives the removal or install first would see an epoch ahead of its read model and block [11 §3.5] — correct, but needlessly, since the antecedent was in the same transaction.
2. `installed_item.removed` for each outgoing item.
3. `installed_item.installed` for each incoming item.
4. `installed_item.identity_resolved`, where a provisional identity was adjudicated (§8).
5. `allowance_document.updated`, where the change altered allowance applicability.

Removals before installs, so a consumer applying in order never holds two items in one position — the C10 invariant preserved across the wire, not only in the database.

### 7.3 Published events — the full declaration

```python
# src/fathom_registry/events/catalog.py
"""Machine-readable event catalog.  MUST equal helm/values.yaml
`events.publishes`/`events.consumes` and document 03 §6's Registry rows
[09 §8.2; C3-C5, C37, C38].  Reconciled by `tools/check_service_events.py`.
"""
from __future__ import annotations

PUBLISHES: frozenset[str] = frozenset(
    {
        "fathom.registry.asset.registered",
        "fathom.registry.asset.status_changed",
        "fathom.registry.configuration_baseline.changed",
        "fathom.registry.installed_item.installed",
        "fathom.registry.installed_item.removed",
        "fathom.registry.installed_item.identity_resolved",   # 11 §8.4; see §15 item 2
        "fathom.registry.allowance_document.updated",
        "fathom.registry.proposal.created",
        "fathom.registry.proposal.adjudicated",
        "fathom.registry.proposal.expired",
    }
)

CONSUMES: frozenset[str] = frozenset(
    {
        "fathom.maintenance.work_order.opened",
        "fathom.maintenance.maintenance_action.recorded",
        "fathom.maintenance.work_package.approved",
        "fathom.reference-data.equipment_family.updated",     # 12 §3.4; see §15 item 8
    }
)

#  NO WILDCARDS.  Every consumed type is named explicitly [C38, 09 §8.2].
```

| Event | Declared consumers [03 §6] | `baseline_epoch` | Scope |
|---|---|---|---|
| `asset.registered` | `fleet-status`, `pdm`, `telemetry` | set (initial epoch) | `asset` |
| `asset.status_changed` | `fleet-status`, `maintenance`, `pdm` | not set | `asset` |
| `configuration_baseline.changed` | `pdm`, `pma`, `knowledge-retrieval`, `failure-intel`, `fleet-status`, `maintenance`, `supply`, `telemetry` | **always set** | `asset` |
| `installed_item.installed` | `pdm`, `telemetry`, `supply` | always set | `installed_item` |
| `installed_item.removed` | `pdm`, `failure-intel`, `supply`, `design-advisory`, `telemetry` | always set | `installed_item` |
| `installed_item.identity_resolved` | same as `installed_item.*` [11 §8.4] | always set | `installed_item` |
| `allowance_document.updated` | `supply`, `maintenance` | not set | `asset` |
| `proposal.*` | `gateway`, `notification`, `audit` [03 §6 convention] | set on `created` | `asset` |

Eight consumers of `configuration_baseline.changed` means **eight consumer-driven conformance tests** contributed into `packages/contracts/conformance/registry/consumers/<slug>/` [03 §10, 09 §4.7]. A declared consumer contributing no test is an unmet Definition-of-Done item — for the *consumer*, but Registry's suite is where the gap is visible, so §11.5 tracks it.

### 7.4 Consumed events — configuration change is caused by executed maintenance

Document 04 §2: *"Executed maintenance is what causes configuration change, so the Registry consumes rather than polls it."*

```python
# src/fathom_registry/events/consumers.py

# ---------------------------------------------------------------------------
# INBOX SEMANTICS — DO NOT "SIMPLIFY" THIS.  [doc 03 §5.2 · finding D2]
#
# The event_id record and the state change it causes COMMIT TOGETHER, in one
# transaction. We do NOT record receipt and then process.
#
# THE BUG THIS PREVENTS:
#   1. Handler records event_id in `inbox` and commits.
#   2. Process crashes (OOM, node drain, pod eviction) before the state change.
#   3. Kafka redelivers the event (at-least-once — 03 §5.2).
#   4. The dedup check sees event_id already present and SKIPS it.
#   5. The state change never happens. There is no error, no alert, no retry.
#      The event is permanently suppressed.
#
# WHY IT IS SEVERE: applied to `configuration.baseline_changed`, predictions
# for a replaced installed item are never invalidated. Document 04 calls that
# the failure most likely to destroy operator trust — and the naive inbox rule
# introduces it by itself. An operator sees a confident remaining-useful-life
# figure for a pump that was landed three weeks ago.
#
# THE ONLY LEGAL SUPPRESSION PREDICATE IS:
#     event_id present AND processed_at IS NOT NULL
# A row with processed_at NULL means "seen, not applied" and MUST NOT suppress.
# ---------------------------------------------------------------------------

EVENT_HANDLERS: dict[str, Handler] = {
    "fathom.maintenance.work_order.opened": on_work_order_opened,
    "fathom.maintenance.maintenance_action.recorded": on_maintenance_action_recorded,
    "fathom.maintenance.work_package.approved": on_work_package_approved,
    "fathom.reference-data.equipment_family.updated": on_equipment_family_updated,
}
```

The §3.2 comment template from document 11 is reproduced **verbatim**, and its presence is a CI gate [11 §11.5 item 7]. Registry is the service where the template's own worked example applies to Registry's own output, which is the strongest possible reason not to paraphrase it.

| Consumed event | What Registry does | What Registry does **not** do |
|---|---|---|
| `work_order.opened` | Records an **anticipated** configuration change against the target position — the work order is authorization to change configuration, not a change. Held as a pending expectation so the subsequent action can be reconciled against it, and so `GET /assets/{id}/configuration` can surface "a change is authorized for this position" | Does not write a baseline, does not allocate an epoch. Authorization is not a fact about configuration |
| `maintenance_action.recorded` | **The configuration-change trigger.** Where the action reports parts consumed or an item replaced, Registry writes the occupancy supersession (§5.6.1), allocates an epoch, regenerates the snapshot, and publishes `configuration_baseline.changed` + `installed_item.removed` + `installed_item.installed` | Does not re-interpret `failure_indicator`, `triggering_driver`, `triggering_prediction_id`, or `policy_version`. Those are Scheduling's facts [03 §6, D1/D21] and Registry carries the reference, not a copy |
| `work_package.approved` | Records the availability window against which a batch of anticipated changes will land, so a modernization's deviations can be grouped and their `sequence` allocated contiguously | Does not create deviations speculatively. A deviation is written when the change is executed or explicitly authorized as a configuration change |
| `equipment_family.updated` | Refreshes the read-through cache and re-validates every `Part.equipment_family` against the new version. A part whose family was removed is flagged, not silently rewritten | Does not author or extend a family. Reference Data is the sole owner [03 §14, 12 §1] |

**Epoch fencing on the consume side.** All three maintenance events carry `baseline_epoch` — document 03 §6 shows `maintenance_action.recorded` in an epoch-carrying position and the antecedent rule is universal. Registry is the *producer* of configuration epochs, so an incoming epoch ahead of Registry's own current epoch for that asset is not a "wait for the antecedent" condition; it is **impossible** and indicates either a replayed event from a future state (after a bad restore) or a rogue producer. `EpochFence.evaluate` is still called, and Registry's handler additionally rejects `incoming_epoch > current_epoch` to `inbox` quarantine with a page rather than blocking, because blocking would wait forever for an antecedent Registry itself would have had to produce.

### 7.5 Staleness bound and read-model lag

`stalenessBoundSeconds: 300` [09 §4.4.1]. Registry declares **no** freshness-dependent computation and therefore never calls `require_fresh()` [11 §3.6]: it owns all of its source-of-truth data, and configuration resolution reads only its own tables. `read_model_lag` on `/readyz` still applies to all four consumed types [09 §5.6 check 4], because a Registry that has fallen 20 minutes behind `maintenance_action.recorded` is serving a configuration that omits a completed replacement — which no downstream fence can detect, since the epoch has not advanced. **That is the one staleness condition in this service that is invisible from outside, so it must fail readiness.**

### 7.6 Outbox, inbox, and conflict policy wiring

| Obligation | Registry |
|---|---|
| Transactional outbox | **Always active.** No exception for a service with no edge profile [03 §15 obligation 11; 11 §1.2] |
| Outbox relay | **Always active, in-process.** `test_c21_relay_not_gated_by_coordinator_flag` runs in Registry's suite [11 §1.3] |
| Edge reconciliation coordinator | **Absent.** No `SYNC_EDGE_COORDINATOR_ENABLED` in Registry's chart and no coordinator sidecar. This is the one legitimately inert component [11 §9.2] and here it is not merely inert, it is not deployed |
| Relay shard count | **4.** `DECISION`, per 11 §13 item 8 which assigns the value to each service's build document with a default of 8. Registry's write rate is ~14,000 configuration changes over 24 months across 12 assets [06 §7] — under 20 per day fleet-wide. Four shards over 12 assets keeps each asset's stream in exactly one shard with fewer lease rows to contend, and changing it requires a drain-to-empty [11 §2.5] |
| Divergence budget | **None declared.** No aggregate is edge-writable, so there is no accumulation to bound [11 §9.1]. The tracker is still constructed, with an empty declaration set, so the registry's complete-or-fail enumeration passes |
| Provisional identity | **Resolver active, minter absent.** Registry never mints a provisional identity — it adjudicates them (§8). `ProvisionalIdentityMinter` is not constructed [11 §1.2: "Resolver always active; minting only at the edge"] |
| Outbox retention | `min_retention` = **90 days**; `prune_requires_shore_ack` = **false** (no edge). `inline_payload_max_bytes` = 65,536 with `changed_items_ref` above the inline cap (§6.2) |
| Idempotency-key retention | **24 hours**, the default [09 §5.3]. Document 09's open question 5 — longer retention for edge-sync-reachable operations — **does** apply to `POST /installed-items`, which is reached from a hull that may have been disconnected for six weeks [06 §4]. Set to **90 days** for that one operation, matching the outbox retention, so a retried provisional submission replays rather than double-writing |

---

## 8. Provisional-identity reconciliation

Registry is the service that confirms or supersedes an edge-minted provisional `installed_item_id`. The protocol is **document 11 §8** in full; this section states Registry's half exactly and adds nothing to the protocol.

### 8.1 Why Registry is the adjudicator

Document 03 §3.3, final paragraph: *"An edge deployment may mint an `installed_item_id` locally as a client-generated UUID with `provisional: true`. **The Registry confirms or supersedes it on reconciliation.** Without this, a ship that replaces an item at sea cannot attribute usage or maintenance to the correct physical item `[D9, D8]`."* Document 03 §11 assigns configuration baselines the policy *"Enterprise-authoritative; edge submits configuration-change proposals and may mint **provisional** installed-item identities."* Document 11 §1.2 places Registry's role precisely: *"Enterprise-authoritative. Participates ashore in provisional-identity resolution (§8)."*

Document 11 §8.1 is the argument for why a provisional identity is not a prohibited local surrogate: *"it is a **candidate canonical identifier** in the canonical namespace, awaiting adoption."* Registry's job is the adoption decision.

### 8.2 The reconciliation operation

Document 11 §8.3 specifies the call verbatim. Registry implements exactly it.

```python
@router.post(
    "/installed-items",
    response_model=IdentityReconciliationResult,
    status_code=200,
    openapi_extra=operation_extra(
        operation_id="registry_reconcile_installed_item",
        substitution=Substitution.REQUIRED,
        side_effects=SideEffects.STATE_CHANGING,
        aggregate="installed_item",
        summary=(
            "Submit an edge-minted provisional installed-item identity for "
            "confirmation or supersession.  Document 11 §8.3."
        ),
    ),
)
async def reconcile_installed_item(
    body: ProvisionalInstalledItemSubmission,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    svc: Annotated[IdentityService, Depends(get_identity_service)],
) -> IdentityReconciliationResult:
    """`Idempotency-Key` is REQUIRED (state-changing [09 §5.3]) and the
    coordinator sets it to the provisional id itself [11 §8.3 step 4].  That
    makes the submission naturally idempotent across a link that drops
    mid-request: the same provisional id resubmitted replays the stored
    response, and `request_hash` mismatch on a DIFFERENT body for the same
    provisional id is a 409 `idempotency-key-reuse` — which is exactly right,
    because two different physical items claiming one provisional id is a real
    conflict and must not be silently merged."""
    return await svc.reconcile(body, idempotency_key)
```

```python
class ProvisionalInstalledItemSubmission(FathomModel):
    """The body of 11 §8.3 step 4, field for field."""

    installed_item_id: UUID = Field(description="The edge-minted uuid4.")
    provisional: bool = Field(description="Always true on this operation.")
    position_id: UUID
    niin: Niin
    serial_or_lot: NonEmptyStr | None = None
    iuid: NonEmptyStr | None = None
    installed_at: UtcDateTime
    removed_item_id: UUID | None = Field(
        default=None, description="What came out, if anything [11 §8.2]."
    )
    usage_at_install: dict[str, float] = Field(default_factory=dict)
    provisional_context: ProvisionalContext


class ProvisionalContext(FathomModel):
    """11 §8.2: "ProvisionalContext recording minting_node_id,
    mint_monotonic_seq, and the physical facts needed for the Registry to
    adjudicate."  Retained FOREVER, including after resolution."""

    minting_node_id: NonEmptyStr
    mint_monotonic_seq: int = Field(ge=0)
    source_work_reference: NonEmptyStr | None = None
    minted_by_principal: NonEmptyStr | None = None
    physical_facts: dict[str, object] = Field(default_factory=dict)
```

### 8.3 The adjudication algorithm

```python
# src/fathom_registry/services/identity.py

async def reconcile(self, sub: ProvisionalInstalledItemSubmission, key: str) -> IdentityReconciliationResult:
    """11 §8.3 step 5: "adjudicate against current baseline."

    ONE transaction.  Identity resolution, the occupancy write, the epoch
    allocation, and every event emitted commit together or not at all
    [11 §2.3].
    """
    async with self.uow.begin():
        position = await self.positions.get(sub.position_id)

        # ---- 6c. REJECTED — physically impossible ------------------------
        #  11 §8.3: "REJECTED: physically impossible (e.g. position not in
        #  baseline).  Quarantined for human adjudication.  NEVER DISCARDED."
        reject_reason = await self._impossible(sub, position)
        if reject_reason is not None:
            await self.quarantine.record(sub, reason=reject_reason)   # NEVER discarded
            return IdentityReconciliationResult(
                resolution=IdentityResolution.REJECTED,
                provisional_id=sub.installed_item_id,
                canonical_id=None,
                reason=reject_reason,
                quarantine_id=...,
            )

        # ---- is there already an enterprise identity for this item? -------
        existing = await self.items.find_same_physical_item(
            position_id=sub.position_id,
            niin=sub.niin,
            iuid=sub.iuid,
            serial_or_lot=sub.serial_or_lot,
            installed_at=sub.installed_at,
        )

        if existing is None:
            # ---- 6a. CONFIRMED — adoption, the designed common case -------
            #  11 §8.4: "Confirmation-by-adoption is the designed common case...
            #  it adopts the ship's UUID.  Then provisional_id == canonical_id,
            #  no alias is needed, and the resolver is a no-op."
            item = await self.items.adopt(sub)          # provisional stays TRUE on the row;
                                                       # identity_resolution = 'confirmed'
            canonical_id = sub.installed_item_id
            resolution = IdentityResolution.CONFIRMED
        else:
            # ---- 6b. SUPERSEDED — a genuine collision ---------------------
            #  11 §8.4: "Supersession is reserved for genuine collisions (the
            #  shore already recorded the replacement from another source, e.g.
            #  a 4790/CK submitted through a separate channel)."
            item = await self.items.record_superseded_alias(
                provisional_id=sub.installed_item_id,
                canonical_id=existing.installed_item_id,
                evidence=self._collision_evidence(sub, existing),
            )
            canonical_id = existing.installed_item_id
            resolution = IdentityResolution.SUPERSEDED

        # ---- the configuration change itself -----------------------------
        epoch = await self.epochs.allocate(position.asset_id)
        record_time = await self.record_clock.allocate()

        if sub.removed_item_id is not None:
            await self.occupancies.close_valid(
                position_id=sub.position_id, at=sub.installed_at, epoch=epoch
            )
        await self.occupancies.open(
            installed_item_id=canonical_id,
            position_id=sub.position_id,
            valid_from=sub.installed_at,
            record_from=record_time,
            install_source="edge_reconciliation",
            usage_at_install=sub.usage_at_install,
            epoch=epoch,
        )
        baseline = await self.baselines.create(
            asset_id=position.asset_id, epoch=epoch, valid_from=sub.installed_at,
            record_from=record_time, change_kind=BaselineChangeKind.SUPERSESSION,
            change_source="edge_reconciliation",
        )
        await self.snapshots.regenerate(baseline)

        # ---- events, in the §7.2 order -----------------------------------
        cid = await publish_baseline_changed(...)                    # 1, carries the new epoch
        if sub.removed_item_id is not None:
            await publish_installed_item_removed(..., causation_id=cid)   # 2
        await publish_installed_item_installed(..., causation_id=cid)      # 3
        await publish_identity_resolved(                                    # 4
            provisional_id=sub.installed_item_id,
            canonical_id=canonical_id,
            resolution=resolution,
            baseline_epoch=epoch,
            causation_id=cid,
        )
    return IdentityReconciliationResult(...)
```

**Confirmation keeps `provisional = true` on the row and sets `identity_resolution = 'confirmed'`.** The flag records *how the identity came to exist*, not whether it is trustworthy, and the `ProvisionalContext` is retained forever [11 §8.2]. Clearing the flag on confirmation would destroy the audit answer to "which identities in this hull's configuration were minted at sea", which is a question a reliability engineer will ask the first time an at-sea replacement correlates with an anomaly.

**`_impossible()` — the rejection predicate.** Rejection is for physical impossibility, not for disagreement:

| Condition | Outcome |
|---|---|
| `position_id` is not in the asset's baseline at `installed_at` | REJECTED |
| `position_id` did not exist at `installed_at` (`established_period` excludes it) | REJECTED |
| `installed_item_id` already exists ashore as a *different* physical item (different `iuid`) | REJECTED — a UUID collision, which must be adjudicated by a human, never resolved by a rule |
| `niin` is not in the part catalog | REJECTED, and the quarantine record carries the NIIN so the catalog gap is actionable |
| `removed_item_id` was not the occupant at `installed_at` | REJECTED — the ship and shore disagree about what came out, which is exactly the divergence that must not be auto-merged |
| The NIIN is not APL-authorized for the position | **Not rejected.** Written, and flagged `conforms_to_template: false`. A cannibalization or an emergency substitution at sea is a real event, and refusing to record it would reintroduce D8 |

Quarantined submissions are surfaced by `GET /installed-items?provisional=true&status=quarantined` and never discarded [11 §8.3 step 6c, §12 item 15].

### 8.4 What happens to events already published under a provisional id

**Document 11 §8.4's decision is binding and is not re-litigated here: published events are NEVER rewritten.** Its three reasons are Registry's reasons too:

1. Records are signed (AU-10, 08 §3.5). Rewriting the subject invalidates the signature, so a rewrite is indistinguishable from tampering.
2. Several aggregates are append-only by contract — anomaly tags *"never overwritten or deleted"*, maintenance action records append-only [03 §11].
3. Events may already have been consumed by nine read models plus Audit; a rewrite is the coordinated global mutation D15 identifies as an accreditation blocker.

Registry's obligations under the mapping-event approach:

| Obligation | Implementation |
|---|---|
| Publish the mapping event | `fathom.registry.installed_item.identity_resolved` on `fathom.registry.installed_item.v1`, carrying `{provisional_id, canonical_id, resolution, evidence, baseline_epoch}` exactly as 11 §8.4 specifies. Emitted in the same transaction as the resolution |
| Publish it on **confirmation as well as supersession** | 11 §8.4 says the resolver is a no-op when `provisional_id == canonical_id`, but a consumer cannot know a provisional id was *confirmed* rather than still pending unless the event fires. It fires for `confirmed`, `superseded`, and `rejected`. A consumer holding a provisional id that never resolves must be able to tell that from one that resolved to itself |
| Retain aliases **permanently** | `installed_items.canonical_installed_item_id` is never deleted and never nulled. 11 §8.4: aliases *"are how a two-year-old event's subject is still interpretable"* |
| Answer a query posed with the **provisional** id | `GET /installed-items/{id}` accepts either a provisional or a canonical id. Given a superseded provisional id it returns `303 See Other` with `Location` pointing at the canonical resource **and** an `X-Fathom-Identity-Resolution: superseded` header, so a machine client follows and a human client sees why. 11 §8.4: *"a maintainer who wrote the provisional id on a form six weeks ago must still find the item."* A `404` here is a defect |
| Never rewrite Registry's own outbox rows | Registry's outbox is signed [11 §10.2]. A resolution never touches a prior row; it appends |
| Never emit an `installed_item.installed` for the canonical id that duplicates one already emitted for the provisional id | Supersession emits the mapping event **only** for the identity change; the occupancy write reuses the canonical id and the install event fires once, for the id that will persist. A second install event under the canonical id would make a consumer count two installations of one physical item |

`IdentityAliasResolver` from `fathom_sync` [11 §8.4] is used **inside Registry too**, not only by consumers: any Registry read that accepts an externally-supplied `installed_item_id` resolves it first. Registry authoring its own resolution and then not applying it is the most obvious way for the alias table to be correct and unused.

---

## 9. The class-template-plus-deviation model

Document 04 §2, key decision 3: *"Ships of one class diverge substantially over their service lives through modernization availabilities and field changes. Configuration is modeled as a class template plus an explicit ordered deviation set per asset, which keeps the common case compact and makes divergence a first-class, queryable fact rather than an inconsistency."*

### 9.1 The three artifacts

| Artifact | What it is | Temporality |
|---|---|---|
| `ClassTemplateVersion` + `Nodes` + `Positions` (§4.2) | The **as-designed** configuration for a class, at a version | Bitemporal, versioned |
| `AssetDeviation` (§4.7) | An **ordered** set of departures from the template, per asset | Bitemporal, ordered by `sequence` |
| `SystemNode` + `Position` (§4.3, §4.4) | The **as-built** hierarchy, materialized | `established_period` in valid time |

The template and the deviation set are the *definition*; the system nodes and positions are the *materialization*. Both are stored, and the resolver's reproducibility test (§11.3) asserts the second is derivable from the first.

### 9.2 Resolving an effective configuration

```python
# src/fathom_registry/services/effective_configuration.py
"""Template + ordered deviations -> effective configuration.  04 §2 key
decision 3.

The fold is the whole algorithm and its order is not negotiable: deviations
apply in ascending `sequence`, never in timestamp order (§4.7).  "remove
position P" then "add position P holding NIIN X" is a different configuration
from the reverse, and a modernization availability lands dozens of deviations
sharing one valid-time instant.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID


@dataclass(frozen=True)
class EffectivePosition:
    position_code: str
    template_position_id: UUID | None
    system_hsc_code: str
    expected_niin: str | None
    ric: str | None
    par_ric: str | None
    origin: str          # "template" | "deviation"
    deviation_id: UUID | None


async def resolve_effective_positions(
    self, asset_id: UUID, at: BitemporalCoordinates
) -> dict[str, EffectivePosition]:
    """Step 1 of the resolution.  Returns position_code -> EffectivePosition."""

    # (a) Which template version was in force, at these coordinates?
    #     Bitemporal on the CLASS, so a template revision recorded late does not
    #     retroactively change what a historical effective configuration was.
    asset = await self.assets.get(asset_id)
    template = await self.templates.resolve(asset.class_id, at)
    if template is None:
        raise NoTemplateAtCoordinates(class_id=asset.class_id, at=at)

    # (b) Start from the as-designed set.
    effective: dict[str, EffectivePosition] = {
        tp.position_code: EffectivePosition(
            position_code=tp.position_code,
            template_position_id=tp.template_position_id,
            system_hsc_code=tp.node_hsc_code,
            expected_niin=tp.expected_niin,
            ric=tp.ric,
            par_ric=tp.par_ric,
            origin="template",
            deviation_id=None,
        )
        for tp in await self.templates.positions(template.template_version_id)
    }

    # (c) Fold the deviations, IN SEQUENCE ORDER, filtered bitemporally.
    #     ORDER BY sequence.  Not by valid_period, not by record_period, not by
    #     any timestamp.  [§4.7, 03 §5.4, 11 §4.7]
    deviations = await self.deviations.list_ordered(asset_id, at)
    for dv in deviations:
        effective = _apply(effective, dv)

    return effective


def _apply(
    effective: dict[str, EffectivePosition], dv: AssetDeviation
) -> dict[str, EffectivePosition]:
    """The seven deviation kinds.  Each is total: a kind whose target is absent
    is a HARD ERROR, not a no-op.

    A tolerant fold is the wrong choice here and the reason is specific.  If
    'remove_position P' silently no-ops because a prior deviation already removed
    P, the effective configuration is still correct — but the deviation set is
    now internally inconsistent and NOTHING WILL EVER SAY SO.  The next
    modernization builds on a set nobody can trust, and 04 §2's promise that
    divergence is 'a first-class, queryable fact rather than an inconsistency'
    is quietly void.  Failing loudly at fold time makes the inconsistency
    visible while there is still one deviation to fix.
    """
    out = dict(effective)
    match dv.kind:
        case "add_position":
            code = dv.payload["position_code"]
            if code in out:
                raise DeviationFoldConflict(dv, f"position {code} already effective")
            out[code] = EffectivePosition(
                position_code=code,
                template_position_id=None,
                system_hsc_code=dv.payload["system_hsc_code"],
                expected_niin=dv.payload.get("expected_niin"),
                ric=dv.payload.get("ric"),
                par_ric=dv.payload.get("par_ric"),
                origin="deviation",
                deviation_id=dv.deviation_id,
            )
        case "remove_position":
            code = dv.payload["position_code"]
            if code not in out:
                raise DeviationFoldConflict(dv, f"position {code} not effective")
            del out[code]
        case "substitute_part":
            code = dv.payload["position_code"]
            if code not in out:
                raise DeviationFoldConflict(dv, f"position {code} not effective")
            out[code] = replace(
                out[code],
                expected_niin=dv.payload["expected_niin"],
                ric=dv.payload.get("ric", out[code].ric),
                origin="deviation",
                deviation_id=dv.deviation_id,
            )
        case "relocate_position":
            code = dv.payload["position_code"]
            if code not in out:
                raise DeviationFoldConflict(dv, f"position {code} not effective")
            out[code] = replace(
                out[code],
                system_hsc_code=dv.payload["system_hsc_code"],
                origin="deviation",
                deviation_id=dv.deviation_id,
            )
        case "add_system" | "remove_system":
            #  Handled in the hierarchy fold, which runs before the position
            #  fold; a `remove_system` cascades to the positions beneath it and
            #  those cascaded removals are MATERIALIZED as explicit
            #  `remove_position` deviations at fold time so the effective set is
            #  never a function of an implicit cascade.
            out = _apply_system(out, dv)
        case "alter_attribute":
            out = _apply_attribute(out, dv)
        case _:  # pragma: no cover - CHECK constraint forbids
            raise DeviationFoldConflict(dv, f"unknown deviation kind {dv.kind!r}")
    return out
```

### 9.3 Joining the effective positions to occupancy

```
effective_configuration(asset, as_of, as_known_at) =
    LET template   = template version in force at (as_of, as_known_at)
    LET positions  = fold(template.positions, deviations ORDER BY sequence)
    LET occupancy  = REG-Q3(asset, as_of, as_known_at)          -- §5.4
    RETURN LEFT JOIN positions ON occupancy BY position_code
           WITH conforms_to_template =
                  (position.origin = 'template'
                   AND occupancy.niin = position.expected_niin)
```

A **LEFT** join, deliberately. A position with no occupant is a real and reportable state — an empty foundation awaiting a part — and an inner join would silently drop it, which would make `GET /assets/{id}/configuration` under-report the hull and would make Supply's allowance-position computation short. `ConfigurationLine.installed_item_id` is therefore nullable on the wire for the vacant case, and a consumer must handle it; a conformance test asserts the reference dataset contains at least one vacant position so the case is exercised rather than asserted.

`conforms_to_template: false` arises from three distinct conditions, and the response distinguishes them because the remedies differ: the position exists only by deviation (`origin = 'deviation'`); the occupant's NIIN differs from `expected_niin` (a substitution); or the position is vacant against a template that expects an occupant (a shortfall). `divergence_reason` carries which.

### 9.4 Why the baseline pins `template_version_id` and `deviation_high_water`

Together they are the complete recipe for a historical resolution: template version + deviations up to sequence N + occupancy at the bitemporal coordinates. Without them, a class template revision or a late-recorded deviation silently changes what a two-year-old baseline meant, and the audit answer to *"what did we believe on 1 April"* becomes a function of what has been recorded since. `test_baseline_recipe_is_reproducible` (§11.3) re-derives each baseline from its own recipe and asserts the snapshot is unchanged.

---

## 10. Internal components, mapped onto the scaffold

Document 04 §2 names five internal components. Document 09 §4.1 fixes the layering — `api → services → repositories → models`, with `services/` owning the transaction boundary and `repositories/` the only place SQL is written. The mapping is one-to-one and there is no sixth component.

| Document 04 §2 component | Module | Layer | Notes |
|---|---|---|---|
| **configuration resolver** (template + deviations + bitemporal query) | `repositories/configuration.py` (§5.5), `services/effective_configuration.py` (§9.2) | repositories + services | Split deliberately: the bitemporal predicate is SQL and belongs in `repositories/`; the deviation fold is domain logic and belongs in `services/`. The predicate exists in exactly one module |
| **baseline snapshot generator** | `services/snapshots.py` | services | Regenerates `configuration_baseline_items` from REG-Q3 within the writing transaction. Never a background job: a snapshot that lags its baseline is a second source of truth [§4.6.1] |
| **allowance importer** | `services/allowance_import.py` | services | Consumes `POST /allowance-documents/bulk` with `X-Backfill`. 04 §2's third Phase 3 question — import format, cadence, and reconciliation against observed configuration — is **open**; the importer's interface is fixed here and its source adapters are not |
| **hierarchy validator** | `services/hierarchy.py` | services | Validates `hsc_code` against the asset's `HierarchyScheme.segment_spec`, validates parent/child code extension under the scheme's segment order, and refuses to populate `eswbs` when `scheme_family <> 'eswbs'` (§4.3). This is the component that makes 07 §3.4 enforced |
| **read-model publisher** | `events/publishers.py` (§7.2) | events | Called from `services/`, inside the caller's transaction [09 §4.1, 11 §2.3] |

`readmodels/` holds exactly one projection: the `equipment_family` read-through cache fed by `equipment_family.updated` [12 §3.4]. It is the only read model Registry owns, because Registry is the source of truth for everything else it serves — which is why it is the one service in the nine whose `/readyz` read-model-lag check covers a single event type.

---

## 11. Testing

### 11.1 Conformance suite wiring

Exactly document 09 §4.7's mechanism, with document 10 §6.2's three protocols. Nothing is varied; a shared conformance test may not be edited, skipped, xfailed, or subclassed [09 §4.7].

```python
# services/registry/tests/conformance/test_suite.py
"""Collects the shared conformance suite for this slug into this service's test run.

The suite lives in packages/contracts/conformance/registry/ (path fixed by
document 03 §10).  Do not add, skip, or modify tests here.  Fixtures are in
conftest.py.
"""
from fathom_contracts.conformance.registry import *          # noqa: F401,F403
from fathom_sync.testing import *                            # noqa: F401,F403  — 11 §11
```

```python
# services/registry/tests/conformance/conftest.py
import pytest
from fathom_contracts.conformance import ConformanceTarget, EventTap, FaultInjector

@pytest.fixture
async def conformance_target(app_client, principal_factory) -> ConformanceTarget:
    """Base URL + auth for a live Registry instance, plus its committed spec.

    `principal_factory` supplies FOUR principals, not one, because Registry has
    three distinct authority levels on one operation (§6.5): an enterprise
    configuration manager (may use `mode: direct`), a maintainer (may use
    `mode: proposed` only), an edge sync identity (may call `POST
    /installed-items`), and an under-privileged reader (asserts the 403 that
    proves 03 §15 obligation 7 — local ABAC enforcement, never the gateway's).
    """

@pytest.fixture
async def event_tap(redpanda) -> EventTap:
    """Reads published envelopes.  Must expose the PARTITION: 10 §6.2 —
    "a tap that hides partitions cannot express the only guarantee there is."
    Registry's event tests assert `installed_item.removed` precedes
    `installed_item.installed` WITHIN the asset's partition (§7.2)."""

@pytest.fixture
async def fault_injector(app_client) -> FaultInjector:
    """11 §11.1's ten injection points, parameterized over every state-changing
    operation.  `AFTER_INBOX_INSERT_BEFORE_APPLY` is mandatory and is D2's
    regression test."""

@pytest.fixture
async def reference_dataset(db) -> None:
    """Loads the `standard` dataset [10 §6.3]: 12 assets, ~8,400 installed
    items, two HSCI schemes [13 §5.2], at least one position with an install
    HISTORY (`installed_item_with_history`, the C10 regression fixture), at
    least one vacant position (§9.3), and at least one provisional identity
    (`provisional_installed_item`)."""
```

Registry additionally contributes the reference dataset's **configuration** partition, since document 13 §2 assigns `configuration/` to Registry and Supply. The dataset is pinned by content hash: *"a changed dataset is a changed test"* [10 §6.3].

### 11.2 Contract and event tests

The generated required-operation sweep from document 10 §6.4 covers rows 1–28 of §6.1. Registry-specific additions:

| Test | Asserts |
|---|---|
| `test_registry_producer_node_is_always_enterprise` | Drain every event a full reference-dataset run produces; assert `producer_node == "enterprise"` on all of them, and that no `edge:` value appears anywhere. §7.2's rationale |
| `test_installed_item_events_partition_on_asset_id` | Given a replacement at one position, `installed_item.removed` and `installed_item.installed` land in the **same** partition, and in that order. §7.1's `DECISION` |
| `test_compaction_key_differs_from_partition_key` | For each compacted Registry topic. Enforced by 11 §2.2's CHECK **and** by this test [11 §11.3] |
| `test_asset_topic_is_not_compacted` | The asset topic's `compaction_key` is NULL on every row, and the topic's broker config is retention-based. §7.1 |
| `test_baseline_changed_precedes_item_events_in_transaction` | `monotonic_seq` ordering within one configuration change matches §7.2's five-step order, and every item event's `causation_id` is the baseline event's `event_id` |
| `test_changed_items_reference_above_inline_cap` | An initial baseline for a surface asset (~1,200 positions [06 §7]) publishes `changed_items_ref`, not an inline list, and the event is under the broker limit [D27] |
| `test_no_equipment_named_identifier_anywhere` | Grep the OpenAPI document, the AsyncAPI document, the migration DDL, and the model modules for `equipment_id`, `equipment_record`, and any `equipment*` identifier other than `equipment_family`. §1.2 note 2, [03 §3.2, C29, 09 §7.2] |
| `test_eic_is_never_a_join_key` | No foreign key, index-for-join, or SQL `JOIN ... ON` references `eic` in any Registry module. Backs lint rule FTH001 [10 §4.4] with a schema-level assertion |
| `test_rin_is_not_promoted_to_a_column` | `RIN` appears only inside `installed_items.sclsis_record` JSONB and in no column, index, or constraint. 07 §3.1, 07 §9 |
| `test_hull_number_has_no_hyphen` | A regex over every emitted `hull_or_tail`, in responses and events, not only at mint time [13 §5.1]. **And** that `"MQ-25 004"` — document 03 §3.3's own example — is accepted (§15 item 5) |
| `test_eswbs_null_on_non_eswbs_scheme` | Every `SystemNode` on a `VARIANT-A` asset has `eswbs = NULL`, and the response carries `scheme_family` so no consumer can assume ESWBS. 07 §3.4 |
| `test_no_informal_eswbs_group_table` | No fixture, seed, enum, or constant maps an ESWBS group number to a name. 13 §5.2: *"A reviewer who recognizes a fabricated ESWBS group table stops believing the rest of the dataset"* |

Fault injection [11 §11.1] runs every state-changing operation × every injection point, asserting `(domain state changed) ⟺ (an outbox row exists for it)`. For Registry the highest-value case is `AFTER_EMIT_BEFORE_COMMIT` on a configuration change: an epoch must not be consumed without its baseline, because a consumed-but-unused epoch is a **gap**, and §4.0.2 depends on gap-freedom. The row-lock allocator makes this safe — the rollback releases the increment — and the test proves it: `test_rolled_back_configuration_change_leaves_no_epoch_gap`.

### 11.3 The bitemporal resolver — specific test cases

These are the tests that would not be written by an implementer who understood bitemporality only as a concept.

| Test | Setup | Assertion |
|---|---|---|
| `test_valid_time_query_returns_historical_occupant` | Pump A installed 1 Feb, replaced by pump B on 1 Apr | `as_of=2026-03-01` returns A; `as_of=2026-05-01` returns B; **both with `as_known_at` defaulted** |
| `test_record_time_query_returns_prior_belief` | Same, but B's installation is recorded on 22 Apr (three weeks late) | `as_of=2026-04-05, as_known_at=2026-04-10` returns **A** — what we believed then. `as_of=2026-04-05, as_known_at=now()` returns **B**. This single pair is document 04 §2's second key decision, and an implementation that answers both identically has silently dropped record time |
| `test_correction_changes_valid_time_without_rewriting_record_time` | B's install date corrected from 1 Apr to 28 Mar, recorded 5 May | The pre-correction row is still readable at `as_known_at=2026-04-30` with its original valid period; the corrected row is readable at `as_known_at=now()`. Neither row was `UPDATE`d in valid time |
| `test_retraction_leaves_a_readable_prior_belief` | An occupancy recorded in error, retracted | `as_known_at` before the retraction returns the occupant; after it returns the position vacant. No physical delete, no `is_deleted` flag |
| `test_exactly_one_row_per_bitemporal_coordinate` | Property test over a generated history of installs, replacements, corrections and retractions | For every `(asset, as_of, as_known_at)` sampled, REG-Q1 returns ≤1 row and REG-Q3 returns ≤1 occupant per position. **Written as a property test, not examples**, because the failure mode is a coordinate nobody thought to enumerate |
| `test_overlapping_validity_is_rejected_by_the_database` | Attempt two currently-believed occupancies for one position over overlapping valid periods | `IntegrityError` naming `one_item_per_position_per_belief`. Run against a real PostgreSQL container — a mock cannot exercise an `EXCLUDE` constraint [09 §2.2] |
| `test_correction_is_accepted_by_the_same_constraint` | The negative control for the test above: overlapping *valid* periods with adjacent *record* periods | **Accepted.** This test is what proves the constraint has three operands and not two (§4.5.2); without it, a two-operand constraint passes the rejection test and looks correct |
| `test_adjacent_periods_do_not_overlap` | Close a record period at exactly `T` and open the successor at exactly `T` | Accepted, and `as_known_at=T` resolves to the successor. Proves the `'[)'` bound choice (§4.0) |
| `test_no_gap_in_record_time_coverage` | After a correction and a retraction | For every valid instant with any coverage, record-time coverage is contiguous from the first record to `now()`. A gap presents as a spurious `404` on an audit query |
| `test_snapshot_equals_derivation` | Every baseline in the reference dataset | REG-Q2's snapshot equals REG-Q3's derivation, position for position. §4.6.1's safety property |
| `test_baseline_recipe_is_reproducible` | Every baseline | Re-deriving from `(template_version_id, deviation_high_water, coordinates)` reproduces the snapshot. §9.4 |
| `test_baseline_epoch_is_gap_free_per_asset` | After the full 24-month history load | `SELECT baseline_epoch ORDER BY baseline_epoch` equals `generate_series(1, max)` for every asset, and `max = next_epoch - 1` |
| `test_epoch_never_regresses_across_restart` | Restart the service mid-history-load | No epoch is reissued and none regresses. §4.0.2 |
| `test_record_clock_survives_backward_step` | `SkewableClock.step_backward(1h)` [11 §11.2] between two configuration changes | The second change's `recorded_at` is strictly greater than the first's; no exclusion constraint is tripped; **and** the test asserts that a naive `clock_timestamp()` would have inverted them — *"the test must prove the inversion exists, or it is not testing anything"* [11 §11.2] |
| `test_as_known_at_in_future_is_422_not_clamped` | `as_known_at = now() + 1h` | `422` with the named problem type. A clamp would silently return current belief and the caller would believe it had audited a historical read (§6.3 rule 4) |
| `test_as_of_in_future_is_allowed` | A scheduled modernization with a future valid-time lower bound | `200`. §6.3 rule 5 |
| `test_upper_inf_and_containment_agree` | Both index paths | `record_period @> now()` and `upper_inf(record_period)` return identical result sets. §5.1 |

#### The D3/D4 scenario, in full

Findings **D3** (*"A long scoring job reads baseline B1, the baseline becomes B2 mid-run, and the job's stale result lands after the invalidation and wins — and looks fresher by `computed_at`"*) and **D4** (*"a consumer can see a prediction computed under B2 before it has processed B1→B2"*) are one bug from two sides. Registry cannot fix either alone — the producer-side fence is PdM's `BaselineFencedComputation` and the consumer-side block is the library's `EpochFence` — but **Registry must make the condition detectable, and that is testable here.**

| Test | Assertion |
|---|---|
| `test_d3_stale_epoch_is_detectable_in_one_read` | Resolve configuration at `as_known_at=T0` (epoch N). Record a configuration change (epoch N+1). Re-read the *same* coordinates: the response still returns epoch N — the historical read is stable — **and** `epoch_is_current` is now `false`. One read, no inference, no second call. 03 §3.3: *"consumers must be able to detect that without inference"* |
| `test_d3_fence_read_exposes_allocation_in_flight` | Hold a transaction open between epoch allocation and commit; call `GET /assets/{id}/current-baseline-epoch` from another connection | `allocated_high_water > current_epoch`. A consumer sees a change is in flight and does not treat `current_epoch` as final (§5.7) |
| `test_d3_write_side_epoch_fence_rejects_stale_submission` | Submit a configuration change with `expected_baseline_epoch = N` after the asset has advanced to N+1 | `409 urn:fathom:problem:registry:baseline-epoch-conflict`, with both epochs as extension members and never parsed from `detail` [03 §4] |
| `test_d4_causation_chain_resolves_the_antecedent` | Consume a Registry `installed_item.installed` in isolation, with the baseline event withheld | The consumer's `EpochFence` blocks, follows `causation_id` to the withheld baseline event, applies it, then applies the install — **in order**. Proves Registry populates `causation_id` on every epoch-carrying event (§7.2) |
| `test_d4_changed_since_resolves_the_antecedent_without_the_bus` | Same, with the broker unavailable after the block | The consumer resolves via `GET /configuration-baselines?changed_since=` and converges. Proves Registry supplies **both** of document 03 §5.4's resolution paths |
| `test_d3_scoring_run_reading_a_stale_epoch_is_detectable_end_to_end` | The integration case, contributed as a **consumer-driven test by PdM** into `conformance/registry/consumers/pdm/`: a simulated long scoring run resolves configuration at epoch N, a replacement advances to N+1 mid-run, and the run attempts to publish | The run's own re-read of `GET /assets/{id}/current-baseline-epoch` returns N+1, `epoch_is_current` on its cached configuration is `false`, and `BaselineFencedComputation` refuses publication. **The assertion that matters is that refusal is possible from Registry's contract alone** — that no PdM-internal state is needed to detect it |

### 11.4 Provisional-identity reconciliation — specific tests

Document 11 §11.4 names two; Registry's suite runs those plus the cases only the adjudicator can reach.

| Test | Assertion |
|---|---|
| `test_provisional_identity_confirmed_by_adoption` [11 §11.4] | Shore has no competing record. Registry adopts the ship's UUID; `provisional_id == canonical_id`; **no alias row is created**; `IdentityAliasResolver.resolve()` is the identity function |
| `test_provisional_identity_superseded_publishes_mapping` [11 §11.4] | Shore already recorded the replacement from a separate 4790/CK channel. A mapping event is published; **no event is rewritten**; every prior signature still verifies; a query by the provisional id still resolves |
| `test_identity_resolved_published_on_confirmation_too` | Confirmation publishes `installed_item.identity_resolved` with `resolution: confirmed`, so a consumer can distinguish "confirmed to itself" from "still pending" (§8.4) |
| `test_query_by_superseded_provisional_id_returns_303` | `GET /installed-items/{provisional_id}` after supersession returns `303` with `Location` and `X-Fathom-Identity-Resolution: superseded`. **A `404` fails this test**, and 11 §8.4's maintainer-with-a-six-week-old-form is the reason |
| `test_provisional_flag_survives_confirmation` | `provisional` remains `true` with `identity_resolution = 'confirmed'`, and `ProvisionalContext` is intact (§8.3) |
| `test_provisional_context_retained_after_resolution` | Including `minting_node_id` and `mint_monotonic_seq`. 11 §8.2: *"retained forever, including after resolution"* |
| `test_rejected_submission_is_quarantined_never_discarded` | Each `_impossible()` condition of §8.3 produces a quarantine record surfaced by `GET /installed-items?provisional=true&status=quarantined`, and **nothing is dropped** [11 §8.3 step 6c, §12 item 15] |
| `test_unauthorized_niin_is_recorded_not_rejected` | An at-sea substitution with a NIIN not APL-authorized for the position is **written**, flagged `conforms_to_template: false` with `divergence_reason`. Refusing it would reintroduce D8 (§8.3) |
| `test_resubmission_replays_via_idempotency_key` | The coordinator resubmits after a dropped link, with `Idempotency-Key = provisional_id`. The stored response replays; `Idempotency-Replayed: true`; **no second occupancy, no second epoch** |
| `test_different_body_same_provisional_id_is_409` | Two different physical items claiming one provisional id → `409 idempotency-key-reuse`. Silently merging them is a real conflict resolved by a rule, which §8.3 forbids |
| `test_identity_resolution_precedes_aggregate_drain` | Contributed by the `sync` coordinator's suite: identity submissions are priority class 0 and complete before any aggregate referencing them drains [11 §8.3 step 4, §9.3]. Registry asserts its half — that a reconciliation accepted at *T* is visible to `changed_since` before the coordinator's class-1 drain begins |
| `test_no_duplicate_install_event_on_supersession` | Supersession emits one install event, under the canonical id (§8.4) |
| `test_usage_counter_keyed_on_item_not_position` [11 §11.4, D9] | Contributed by Telemetry as a consumer-driven test: after an at-sea replacement reconciled here, the new item's counter starts at its own hours. Registry's half is that `installed_item.installed` carries `replaced_installed_item_id` so Telemetry can open a new counter epoch (§6.2) |

### 11.5 Consumer-driven tests Registry must receive

Document 03 §10: consumer-driven tests are *"contributed by each declared consumer in §6, asserting the guarantees that consumer depends upon. These catch the substitution that conforms and still breaks a neighbor."* Registry has **more declared consumers than any other producer** — eight on one event — so its suite is where C3 (*"21 consumers declared in the 03 event catalog are not shown consuming in 04. Each is an unbuildable consumer-driven conformance test"*) is most likely to resurface.

`packages/contracts/conformance/registry/consumers/` must contain a directory per slug: `pdm`, `pma`, `knowledge-retrieval`, `failure-intel`, `fleet-status`, `maintenance`, `supply`, `telemetry`, `design-advisory`, `gateway`, `notification`, `audit`. A directory that is absent or empty is a **Definition-of-Done failure for that consumer**, and Registry's suite reports it as a named skip with the owning slug rather than silently collecting nothing — an empty consumer directory that produces a green run is C3 with a passing build.

Registry cannot write these tests. It can and does make their absence loud.

### 11.6 Test tiers

Per document 09 §4.7, four tiers, not interchangeable. Coverage floor 80% on `services/` and `repositories/` [09 §7.4] — and for this service the floor is beside the point: `repositories/configuration.py` and `services/effective_configuration.py` are covered by the property tests of §11.3, and a percentage on either is not evidence.

`testcontainers` PostgreSQL is **mandatory** for every test in §11.3. `btree_gist`, `EXCLUDE USING gist`, `tstzrange` containment, and the row-lock allocator's commit-order property are none of them mockable, and every one of them is load-bearing.

---

## 12. Deployment

Chart shape, `values.yaml` keys, Dockerfile, and CI are document 09 §4.3–§4.4 without variation. This section states only what is Registry-specific.

### 12.1 `values.yaml` — the Registry-specific values

```yaml
# services/registry/helm/values.yaml
slug: registry                         # 03 §3.1.  NOT asset-registry
apiMajor: 1

image:
  repository: registry.internal/fathom/registry
  digest: ""                           # set by CI on merge; promoted by digest [01 §11]

replicaCount: 3
# THREE, not the scaffold's two.  DECISION.  04 §2: "Every sub-application reads
# this one" and the surface is "read-dominated".  Registry is the only service in
# the nine whose unavailability is a fleet-wide outage: every consumer's
# `changed_since` rebuild path and every blocked consumer's antecedent pull
# terminate here [03 §5.4, D4, D5].  A rolling upgrade at replicaCount 2 leaves
# one replica, and a PodDisruptionBudget of minAvailable 1 then blocks the drain.

resources:
  requests: { cpu: 200m, memory: 512Mi }
  limits:   { cpu: "2",  memory: 1Gi }
# Above the scaffold default because the GiST index scans of §5 and the snapshot
# regeneration of §4.6.1 are the memory-hungriest reads in the Sustainment Plane.
# Capacity basis: 12 assets, ~8,400 installed items, ~1,200 positions on a
# surface asset [06 §7].  No figure here is invented [09 §9.5 item 31].

app:
  logLevel: INFO
  config:
    stalenessBoundSeconds: 300         # 03 §5.2 / obligation 14.  §7.5
    relayShardCount: 4                 # 11 §13 item 8.  §7.6
    outboxMinRetentionDays: 90
    changedItemInlineMax: 200          # §6.2, [D27]
    idempotencyRetentionHours: 24
    idempotencyRetentionHoursEdgeReachable: 2160   # 90 days, POST /installed-items only.  §7.6

database:
  clusterName: fathom-registry-pg      # exactly one, in fathom-data [03 §15 obl. 13]
  name: registry
  secretRef: fathom-registry-pg-app
  poolSize: 20                         # read-heavy; above the scaffold's 10
  maxOverflow: 10

migrations:
  enabled: true
  backoffLimit: 0                      # a failed migration fails the release [01 §11]

events:
  brokers: redpanda.fathom-data.svc.cluster.local:9093
  schemaRegistry: http://redpanda.fathom-data.svc.cluster.local:8081
  consumerGroup: fathom-registry-v1
  publishes:                           # MUST equal events/catalog.py PUBLISHES
    - fathom.registry.asset.v1
    - fathom.registry.configuration_baseline.v1
    - fathom.registry.installed_item.v1
    - fathom.registry.allowance_document.v1
    - fathom.registry.proposal.v1
  consumes:                            # MUST equal events/catalog.py CONSUMES
    - fathom.maintenance.work_order.v1
    - fathom.maintenance.maintenance_action.v1
    - fathom.maintenance.work_package.v1
    - fathom.reference-data.taxonomy.v1        # equipment_family.updated [12 §3.4]

autoscaling:
  mode: hpa                            # read-heavy request-driven, not a lag-driven worker
  minReplicas: 3
  maxReplicas: 8
  targetRequestsPerSecond: 50
```

**No `values-edge.yaml`, no coordinator, no `SYNC_EDGE_COORDINATOR_ENABLED`.** Registry has no edge profile [11 §1.2]. A chart file for an edge deployment must not exist, because its existence is the first step toward a second instance of this slug minting configuration baselines — and §7.2 explains why that breaks every downstream epoch fence.

### 12.2 NetworkPolicy — who may call Registry, and whom Registry may call

```yaml
networkPolicy:
  enabled: true                        # NEVER false in any environment [09 §9.5 item 30]
  ingress:
    fromServices:
      # The gateway, for all user-facing composition [09 §4.4.2, 01 §5]
      - gateway
      # The nine consumers' `changed_since` rebuild and antecedent-pull path.
      # See the ADR requirement below — this is NOT a sanctioned edge in 09 §4.4.2
      # as written, and it must be added there before this chart merges.
      - pdm
      - telemetry
      - maintenance
      - supply
      - fleet-status
      - pma
      - failure-intel
      - design-advisory
      # Platform consumers that project configuration
      - knowledge-retrieval            # configuration-aware retrieval [04 §11]
      - sync                           # shore-side coordinator, provisional identity [11 §9.3]
    fromNamespaces: []                 # no cross-namespace ingress.  Domino never calls Registry
    allowPrometheusScrape: true
  egress:
    toOwnDatabase: true                # fathom-registry-pg only
    toEventBus: true                   # Redpanda brokers + schema registry
    toServices: [auth, audit, reference-data]
    toNamespaces: []                   # empty
    allowDNS: true
```

**Whom Registry may call: nothing but its own database, the event bus, DNS, and three platform services.**

Document 04 §2 gives Registry no outbound dependency at all — *"Plane placement: Sustainment Plane in full. No Domino workloads"* — and its ownership boundary makes it the source of truth for everything it serves. The three platform edges are the universal ones document 09 §4.4.2 sanctions for every service, and each is genuinely needed here: `auth` for JWKS and introspection, since document 03 §4 requires authorization be enforced by the receiving sub-application; `audit` for the provenance obligation [03 §15 obligation 9]; and `reference-data` for `equipment_family` resolution, which document 03 §3.3 requires on every part and document 12 §2.7 places in Reference Data's ownership. The `reference-data` call is a cached read-through, never a compute-path dependency [09 §4.4.2].

**Registry calls no sub-application, ever.** Not for a read, not for composition, not for validation. Document 03 principle 2 forbids it, and Registry has no reason to want it: it is the root of the dependency graph [04 §1].

**Who may call Registry: everyone.** And this requires an ADR, because document 09 §4.4.2 as written forbids it.

> **`DECISION` and required ADR.** Document 09 §4.4.2's sanctioned edge set marks **sub-application → sub-application** as **NO**, citing document 03 principle 2, and lists no exception. But document 03 §4 and §15 obligation 5 require `changed_since` reads *"over each aggregate a consumer maintains a read model of"* and state flatly that *"This is the rebuild path; the event bus is not"* `[D5, D25, D30]`; document 11 §3.5's epoch fence resolves a blocked antecedent by calling `GET /api/v1/registry/configuration-baselines?changed_since=<epoch>` **from the consumer**; and document 11 §2.8 ships a `ChangedSinceRebuilder` for exactly that call. As written, document 09 §4.4.2 makes both mechanisms unreachable.
>
> The resolution is a **narrow named edge, not a general relaxation**: `<any sub-application or platform consumer> → registry`, restricted to `x-substitution: required` **GET** operations. It is consistent with document 03 principle 2, which prohibits synchronous calls *"on a compute path"* — a read-model rebuild and an antecedent pull are by construction not compute paths; they are the mechanism D5 and D4 mandate. Routing them through the `gateway` was considered and rejected: document 09 §4.4.2 sanctions `gateway → the nine` but not `the nine → gateway`, so it needs an ADR either way, and it would put a stateless composition layer on a bulk-paging rebuild path that document 05 D32 already flags as the wrong shape for the gateway.
>
> Required before this chart merges: an ADR under `docs/adr/`, plus the edge added to document 09 §4.4.2 [09 §7.5, §9.5 item 30]. Logged in §15 item 9. The same edge is needed for **every** producer with declared consumers, so it should be added generically rather than for Registry alone.

The helm-unittest assertion is unchanged and mandatory: the rendered egress peer set must **equal** `values.networkPolicy.egress` exactly and contain nothing else [09 §4.2, §8.6].

### 12.3 Migrations

One Alembic history, executed as a `pre-install,pre-upgrade` Helm hook Job with `backoffLimit: 0` [01 §11, 09 §8.4]. Registry-specific:

- The **first** revision creates `btree_gist` before any table, because both exclusion constraints depend on it (§4.5.2).
- Exclusion constraints, `tstzrange` columns, and the partial GiST indexes are `op.execute()` raw SQL inside ordinary revisions where SQLAlchemy's DDL does not reach them, exactly as document 09 §2.2 anticipates.
- **A migration may never drop an exclusion constraint to make a data load succeed.** If a load violates one, the data is wrong. A DoD gate asserts every migration head leaves both constraints present, and `test_overlapping_validity_is_rejected_by_the_database` runs against the migrated schema rather than against `metadata.create_all()`.
- Migrations are **forward-only** [09 §8.4]. There is no down-migration that drops a bitemporal column, because dropping `record_period` is not reversible in data.

### 12.4 Readiness

The five mandatory checks [09 §5.6], with Registry's specifics:

| Check | Registry |
|---|---|
| `database` | `SELECT 1` on `fathom-registry-pg` |
| `migrations` | Image Alembic head equals database head |
| `broker` | Producer metadata reachable |
| `read_model_lag` | All four consumed types against `stalenessBoundSeconds: 300`. §7.5 explains why this must fail readiness and not merely warn |
| `outbox_drain` | Pending depth and oldest-pending age within bounds [11 §2.6] |

Plus two Registry-only checks, both of which assert an invariant no consumer can verify:

| Check | Fails when |
|---|---|
| `bitemporal_constraints` | Either exclusion constraint, or `btree_gist`, is absent from the live schema. A Registry serving reads without them is returning arbitrary picks from a set it believes is a singleton (§5.2) |
| `epoch_continuity` | For any asset, `max(baseline_epoch) <> next_epoch - 1`. A gap means every downstream fence is waiting for an epoch that will never arrive (§4.0.2) |

### 12.5 Purge path and store classification [03 §13, D15]

Document 03 §13 requires *"An explicit statement per store of whether it is legally immutable or operationally append-only. The two require different remediation."* Registry's declaration:

| Store | Classification | Purge mechanism |
|---|---|---|
| `configuration_baselines`, `configuration_baseline_items` | **Operationally append-only.** Not legally immutable | Envelope-level encryption with per-classification keys; crypto-shredding the KEK is the purge mechanism where row deletion would break the bitemporal record [03 §13.1] |
| `item_occupancies` | Operationally append-only | As above |
| `installed_items`, incl. `provisional_context` | Operationally append-only | As above. `provisional_context` is retained forever [11 §8.2] and is purged only by crypto-shredding |
| `asset_deviations` | Operationally append-only | As above |
| `outbox`, `inbox`, `outbox_quarantine`, identity quarantine | Operationally append-only | `fathom_sync.purge_by_selector(...)` covers all four [11 §10.1] |
| `idempotency_keys` | Operationally transient | Time-based expiry (§12.1) |
| `registry_record_clock`, `registry_record_seq`, `asset_baseline_epoch` | **Never purged, never reset** | Resetting any of the three is unrecoverable (§4.0.2) |

A spillage remediation therefore has a declared owner and a tested procedure for every Registry store, which document 03 §13 makes an accreditation prerequisite rather than a refinement.

---

## 13. Explicit DO-NOT list

Each item carries the finding that makes it a defect rather than a preference. A reviewer may cite the number and stop reading. Document 09 §9's thirty-two items apply in full and are not repeated; these are Registry's.

### 13.1 Identity

1. **Do not conflate `position_id` with `installed_item_id`.** Not in a column, not in a payload, not in a variable, not in a log field. A `position` row never carries a `current_installed_item_id`; occupancy is a bitemporal fact with its own table. *(**C10**, **D9**; 03 §3.3 rule 3; 04 §2 key decision 1 — "a newly installed component inherits its predecessor's degradation, which is both wrong and confidence-destroying the first time an operator notices it")*
2. **Do not name anything `equipment_id`, `equipment_record`, or `equipment_*`** — the sole exception being `equipment_family`, which is a canonical term in its own right [03 §3.3, D35]. *(**C10**, **C29**; 03 §3.2; 09 §7.2; 10 §4.3 — "There is deliberately no field named `equipment_id` anywhere in this package")*
3. **Do not use `eic` as a join key.** No foreign key, no `JOIN ... ON eic`, no index built for joining on it, no dictionary keyed on it. EIC is a class code of variable specificity, 2–7 characters, and truncated values are legitimate. *(03 §3.3 rule 2; 07 §3.2; **C2**, **C10**; lint FTH001)*
4. **Do not use `hull_or_tail`, `eswbs`, `position_code`, `nsn`, `hsc_code`, or `sthn` as a join key.** External systems reissue and reformat all of them. *(03 §3.3 rule 1)*
5. **Do not promote `RIN` to a column, and never join on it.** It is *"an internal surrogate, not a domain identifier... basically an address used by these databases for automated retrieval."* It lives inside the `sclsis_record` JSONB precisely so nothing can. *(07 §3.1, 07 §9 — "RIN carries the APL number" is a corrected premise; **RIC** carries it)*
6. **Do not mint any identifier at the edge other than `installed_item_id`,** and do not accept one. Registry rejects a submission carrying an edge-minted `asset_id`, `system_id`, `position_id`, or `baseline_id`. *(03 principle 4; 11 §8.2, §12 item 14)*
7. **Do not render a hull number with a hyphen,** and do not reject `"MQ-25 004"`. The rule constrains the hull *number*, not the type designation. *(SECNAVINST 5030.8D Encl 6 via 07 §3.5; §15 item 5)*
8. **Do not model UIC as six characters.** Five, with an optional leading Service prefix carried separately. *(07 §3.3 — "Model UIC as five characters, with an optional leading Service prefix in DoDAAC and requisition contexts")*

### 13.2 Bitemporality and the epoch

9. **Do not write a temporal predicate outside `repositories/configuration.py`.** One module, one predicate. A predicate that tests `valid_period` and omits `record_period` reduces the model to uni-temporal, and every test that only ever passes `as_known_at=now()` still passes. *(04 §2 key decision 2; §5.5)*
10. **Do not write an exclusion constraint with two operands.** `(id, valid_period)` forbids corrections outright; `(id, record_period)` permits two simultaneously-believed occupants. Three operands, always. *(04 §2 Data stores; **C10**; §4.5.2)*
11. **Do not drop an exclusion constraint to make a data load succeed.** If a load violates one, the data is wrong. *(§12.3)*
12. **Do not `UPDATE` a closed `record_period`, and do not physically delete a superseded row.** A closed record period *is* the tombstone and carries when belief ended, which a boolean cannot. *(03 §13; 04 §2 key decision 2; §5.6)*
13. **Do not close `record_period` when recording a removal.** A removal advances valid time. Closing record time makes the removal look like a retraction, and question C then reports that we never believed the item was there. *(§5.6.1)*
14. **Do not leave a gap in record-time coverage.** A correction closes the predecessor at exactly the instant the successor opens. A gap presents as a spurious `404` on the audit query the model exists to serve. *(§5.6.2 rule 2)*
15. **Do not write `LIMIT 1` on REG-Q1.** Uniqueness is a database guarantee; `LIMIT 1` converts a constraint failure into a silent arbitrary pick. *(§5.2)*
16. **Do not allocate `baseline_epoch` from a Postgres `SEQUENCE`.** Sequences leak values on rollback, so the stream has holes, and they do not serialize allocation with commit, so epoch 43 can become visible before 42. Both properties are required. *(11 §4.3's identical argument; **D4**; §4.0.2)*
17. **Do not allow a `baseline_epoch` gap to go undetected.** With a gap, every consumer blocked on the antecedent rule waits for an epoch that will never arrive, and the operational response is to weaken the block — at which point **D4** returns. `epoch_continuity` fails readiness. *(03 §5.4; **D3**, **D4**; §12.4)*
18. **Do not reset, reuse, or regress `baseline_epoch`, `record_seq`, or the record clock** — not on redeploy, not on migration, not on a database restore without operator confirmation. *(11 §4.3; §4.0.2)*
19. **Do not order the `changed_since` feed on a timestamp.** Ordering on `recorded_at` permits a lower-sequence row to become visible after a higher one, and a rebuilder that reached the end permanently misses it. *(**D5**; §6.4)*
20. **Do not filter the `changed_since` feed to currently-believed rows.** A correction and a retraction are exactly the facts a rebuilder must not miss, and `WHERE upper_inf(record_period)` hides both. *(**D5**; §6.4)*
21. **Do not clamp `as_known_at` into the past.** A future record time is a `422`. Clamping silently returns current belief and the caller comes to believe it audited a historical read. *(§6.3 rule 4)*
22. **Do not assert `as_known_at >= as_of`.** "What did we believe in January about what would be installed in June" is legitimate. *(§6.3 rule 6)*
23. **Do not order deviations by any timestamp.** The fold is not commutative and a modernization lands dozens of deviations sharing one valid-time instant. `ORDER BY sequence`, always. *(04 §2 key decision 3; 03 §5.4; §4.7)*
24. **Do not make the deviation fold tolerant.** A `remove_position` whose target is absent is a hard error. A tolerant fold yields a correct configuration over an inconsistent deviation set that nothing will ever report. *(§9.2)*

### 13.3 The hierarchy

25. **Do not assume a fixed HSC layout, and do not add an `eswbs_group` or `eswbs_subgroup` column.** HSC is the Hierarchical Structure Code; *"the format varies by ship"*; Record Type 1 carries `HSCI` to say which scheme applies; *"There is therefore no single fixed HSC layout, and an architecture that assumes one is wrong."* A scheme's shape is data, in `segment_spec`. *(**07 §3.4**, 07 §9 — a corrected premise; 13 §5.2)*
26. **Do not populate `eswbs` on an asset whose scheme family is not ESWBS.** *(07 §3.4)*
27. **Do not emit, seed, enumerate, or hard-code the informal ESWBS nine-group mapping.** ESWBS *"code content is NOT PUBLICLY FOUND"* and the circulating summary table is *"unusable — ESWBS `843` = ballast contradicts it."* *(07 §3.4, §10; 13 §5.2 — "A reviewer who recognizes a fabricated ESWBS group table stops believing the rest of the dataset")*
28. **Do not cite `S9040-AA-IDX-010`.** Cite `-AC-` as current. *(07 §3.4)*

### 13.4 Navy values and fabrication

29. **Do not invent a Navy code value.** `TYCOM`, Ship `STATUS`, OFRP phase, deployment state, OPNAV 4790/CK transaction and action codes, and ESWBS content are all **NOT PUBLICLY FOUND**. Generate from a reserved synthetic range, mark it, and list it in the data card's divergence list. *(07 §1 — "The prohibition on fabrication is operative, not aspirational"; 07 §3.1, §3.6, §10; 09 §9.5 item 32)*
30. **Do not model an "ASI number".** ASI is the Automated Shore Interface **batch process** — `JSS117` (Unit) or `JSS135` (Force) — not an identifier. *(07 §3.6, 07 §9 — a corrected premise)*
31. **Do not assert a single AEL length.** Model 10–11 and **state the ambiguity** on the wire, because the source is internally inconsistent and real examples show both. *(07 §4.1)*
32. **Do not add a `derivation_code` column, an SNSL table, or `UR = POP × BRF / 4`.** The SNSL, the fourteen fields, and the Derivation Code are Supply's. *(04 §2 "Does not own"; 04 §7; 07 §4.9)*
33. **Do not author, extend, or version `equipment_family`, the failure-mode taxonomy, or any code set.** Reference Data is the single owner, and single ownership is an external obligation under DoDI 8320.02. *(03 §14; **C8**, **D31**; 12 §1)*
34. **Do not treat `usage_at_install` as authoritative or serve it as a current value.** It is a copy; Condition & Telemetry owns counter values, and the reference dataset deliberately contains snapshots that disagree with the authoritative series. *(01 §6; 04 §2 "Does not own"; 13 §5.3 rule 5)*
35. **Do not adjudicate corrective-versus-preventive.** Registry records `failure_indicator` as reported and carries the reference. The determination is Scheduling's, and it is the determinative censoring input. *(03 §6; 04 §4, §6)*

### 13.5 Events and boundaries

36. **Do not set `producer_node` to anything but `"enterprise"`.** Registry is enterprise-only. Two instances of this slug minting configuration baselines would make every downstream epoch fence read a sequence that is no longer a total order for the asset. *(03 §5.4; 11 §1.2, §4.2; §7.2)*
37. **Do not partition installed-item events on `installed_item_id`.** The removal and its replacement's install would land in different partitions, a consumer would legitimately apply them out of order, and Telemetry would attribute the interval to the wrong item. *(03 §5.1; **D9**; §7.1)*
38. **Do not compact the asset topic.** Its aggregate key equals its partition key, and compacting would collapse a hull's status history to one record. *(**D5**; 11 §2.2's CHECK; §7.1)*
39. **Do not emit an item event before its `configuration_baseline.changed`,** and do not omit `causation_id`. Both resolution paths of the antecedent rule must be available. *(03 §5.4; **D4**; §7.2)*
40. **Do not inline a changed-item set above the cap.** An initial baseline touches ~1,200 positions and would exceed the broker limit. *(**D27**; 03 §6; 09 §8.2; §6.2)*
41. **Do not rewrite an event published under a provisional identity.** Signatures break, append-only policies are violated, and the fix requires a coordinated global mutation across every store. Publish the mapping event. *(11 §8.4, §12 item 13; **D15**)*
42. **Do not return `404` for a query posed with a superseded provisional id.** `303` with `Location`. A maintainer who wrote the provisional id on a form six weeks ago must still find the item. *(11 §8.4; §8.4)*
43. **Do not discard a rejected provisional submission.** Quarantine and surface it. *(11 §8.3 step 6c, §12 item 15)*
44. **Do not reject an at-sea substitution because the NIIN is not APL-authorized.** Record it and flag the divergence. Refusing it reintroduces **D8**. *(§8.3)*
45. **Do not clear `provisional` on confirmation.** The flag records how the identity came to exist, not whether it is trustworthy. *(§8.3)*
46. **Do not call any sub-application, synchronously or otherwise.** Registry is the root of the dependency graph and has no outbound domain dependency. *(03 principle 2; 04 §1, §2)*
47. **Do not skip the outbox because Registry has no edge profile.** *"Without exception, including sub-applications with no current edge profile."* *(03 §15 obligation 11; 11 §12 item 17)*
48. **Do not create a `values-edge.yaml`, an edge coordinator deployment, or a `SYNC_EDGE_COORDINATOR_ENABLED` flag for Registry** — while never gating the outbox relay on anything. *(**C21**; 11 §1.3, §9.2; §12.1)*

---

## 14. Definition of Done

**The shared Definition of Done in [09 §8](09-monorepo-and-conventions.md) applies in full.** All of §8.1 through §8.7, every box, with the verifying command run and its output green. **Nothing is removed** [09 §8].

Document 09 §8 instructs each subsequent build-framework document to *"reproduce this checklist"*; document 11 §14 set the precedent of referencing it and adding to it, which avoids a second copy drifting from the first. That precedent is followed here. `services/registry/README.md` carries the full expansion, copied from document 09 §8 and ticked there.

Registry adds the following, and the service is not done until every one holds.

### 14.1 Bitemporal correctness

- [ ] **`btree_gist` is created in the first Alembic revision**, before any table.
- [ ] **`configuration_baselines` carries `EXCLUDE USING gist (asset_id =, valid_period &&, record_period &&)`**, with all three operands, verified against the migrated schema and not against `metadata.create_all()`. *(04 §2 Data stores)*
- [ ] **`item_occupancies` carries both three-operand exclusion constraints** — `one_item_per_position_per_belief` and `one_position_per_item_per_belief`. *(**C10**, **D9**)*
- [ ] `class_template_versions`, `asset_deviations`, and `allowance_documents` carry their bitemporal exclusion constraints.
- [ ] **`test_overlapping_validity_is_rejected_by_the_database` is green, AND `test_correction_is_accepted_by_the_same_constraint` is green.** The second is what proves the constraint has three operands and not two; the first passes with a two-operand constraint. *Both, or neither counts.*
- [ ] All temporal periods are `'[)'`; `test_adjacent_periods_do_not_overlap` is green.
- [ ] **`test_record_time_query_returns_prior_belief` is green** — the single test that proves record time is real. An implementation answering `as_known_at=then` and `as_known_at=now` identically fails here and passes everything else.
- [ ] `test_exactly_one_row_per_bitemporal_coordinate` runs as a **property test**, not as examples.
- [ ] `test_no_gap_in_record_time_coverage` is green after a correction and a retraction.
- [ ] `test_snapshot_equals_derivation` and `test_baseline_recipe_is_reproducible` are green over every baseline in the reference dataset.
- [ ] No temporal predicate exists outside `repositories/configuration.py`, asserted by a grep gate in `make lint`.
- [ ] `test_record_clock_survives_backward_step` is green **and includes the inversion assertion** — it proves a naive `clock_timestamp()` would have inverted the two writes. *(11 §11.2)*

### 14.2 The epoch

- [ ] **`baseline_epoch` is allocated by the row-lock counter of §4.0.2**, never a Postgres `SEQUENCE`.
- [ ] `test_baseline_epoch_is_gap_free_per_asset` is green after the full 24-month history load.
- [ ] `test_rolled_back_configuration_change_leaves_no_epoch_gap` is green at the `AFTER_EMIT_BEFORE_COMMIT` injection point.
- [ ] `test_epoch_never_regresses_across_restart` is green.
- [ ] **The `epoch_continuity` readiness check is wired and fails readiness on a gap.** *(§12.4)*
- [ ] **The `bitemporal_constraints` readiness check is wired** and fails if either exclusion constraint or `btree_gist` is absent.
- [ ] `GET /assets/{id}/current-baseline-epoch` returns `current_epoch` **and** `allocated_high_water` separately. *(03 §3.3 — detection without inference)*
- [ ] Every configuration response carries `baseline_epoch`, `baseline_id`, and `epoch_is_current`.
- [ ] **`test_d3_stale_epoch_is_detectable_in_one_read` is green.** *(**D3**, **D4**)*
- [ ] `test_d4_causation_chain_resolves_the_antecedent` and `test_d4_changed_since_resolves_the_antecedent_without_the_bus` are both green — Registry supplies **both** of document 03 §5.4's resolution paths.
- [ ] PdM's contributed `test_d3_scoring_run_reading_a_stale_epoch_is_detectable_end_to_end` is present in `conformance/registry/consumers/pdm/` and green.

### 14.3 Provisional identity

- [ ] `POST /installed-items` implements document 11 §8.3 step 4 field for field, with `Idempotency-Key` **required** and 90-day retention.
- [ ] All three resolutions are implemented — `confirmed` (adoption), `superseded` (mapping event), `rejected` (quarantine, never discarded).
- [ ] **`installed_item.identity_resolved` is published for all three**, including confirmation. *(§8.4)*
- [ ] **No published event is ever rewritten**, asserted by `test_provisional_identity_superseded_publishes_mapping` including signature re-verification. *(11 §8.4)*
- [ ] Aliases are retained permanently; `test_query_by_superseded_provisional_id_returns_303` is green and a `404` fails it.
- [ ] `ProvisionalContext` survives resolution intact, `provisional` stays `true`, `identity_resolution` is set.
- [ ] `test_resubmission_replays_via_idempotency_key` and `test_different_body_same_provisional_id_is_409` are both green.
- [ ] `test_unauthorized_niin_is_recorded_not_rejected` is green. *(**D8**)*
- [ ] `IdentityAliasResolver` is applied to every Registry read that accepts an externally-supplied `installed_item_id`.
- [ ] Telemetry's contributed `test_usage_counter_keyed_on_item_not_position` is present and green; `installed_item.installed` carries `replaced_installed_item_id`. *(**D9**)*

### 14.4 `changed_since` — every aggregate a consumer projects

- [ ] **A `changed_since` read exists for every one of the twelve owned aggregates in §4.10**, cursor-paginated, `x-fathom-aggregate` declared so `OAS013` can prove it. *(03 §4, §15 obligation 5, **D5**)*
- [ ] Ordering and pagination are on `record_seq`; no feed orders on a timestamp. *(§6.4)*
- [ ] Feeds return **full current row state**, and include rows whose `record_period` is closed.
- [ ] `next_changed_since` is returned in `rt:<seq>` form on every response, and the RFC 3339 input form is accepted and translated once.
- [ ] `feed_complete` is returned, and the completeness argument of §6.4 holds — allocation is serialized to commit.
- [ ] **`test_d5_read_model_rebuild_from_changed_since_only` is green with the broker unavailable.** *(11 §11.3)*
- [ ] Nothing is pruned and nothing is physically deleted, so document 03 §10 requirement 5's historical-backfill capability holds by construction.

### 14.5 Registry-specific contract and event gates

- [ ] Every read operation is `x-agent-eligible`; no operation is `proposal-only`; agent eligibility is asserted only where `x-side-effects` is `none`. *(**C1/D11**)*
- [ ] `as_of` and `as_known_at` are accepted together on all nine operations of §6.3, asserted by spec rule `OAS-REG-1`.
- [ ] `GET /classes/{id}/template` and `GET /assets/{id}/current-baseline-epoch` are enumerated in `x-naming-carve-outs` with reasons. *(**C23**)*
- [ ] `producer_node == "enterprise"` on every event; `test_registry_producer_node_is_always_enterprise` green.
- [ ] The catalog-label → wire-name mapping of §3.2 is implemented, and `tools/check_event_catalog.py` exits 0 against it.
- [ ] `events/catalog.py` `PUBLISHES`/`CONSUMES` equal `helm/values.yaml` and document 03 §6's Registry rows, with the two documented additions (§15 items 2 and 8). No wildcards. *(**C3–C5**, **C37**, **C38**)*
- [ ] Compaction key differs from partition key on every compacted topic; the asset topic is uncompacted. *(**D5**)*
- [ ] Event emission order within a transaction matches §7.2, asserted by `test_baseline_changed_precedes_item_events_in_transaction`.
- [ ] The inbox comment template of document 11 §3.2 is present **verbatim**, and the CI gate for it passes.
- [ ] All twelve owned aggregates are declared in the conflict-policy registry, none implicit; the startup enumeration passes. *(**C20**; 11 §7.2)*
- [ ] Divergence-budget tracker constructed with an empty declaration set; no edge-writable aggregate exists.
- [ ] `test_c21_relay_not_gated_by_coordinator_flag` is green. *(**C21**)*

### 14.6 Navy fidelity

- [ ] No `equipment*` identifier anywhere except `equipment_family`; `test_no_equipment_named_identifier_anywhere` green. *(**C29**)*
- [ ] `test_eic_is_never_a_join_key` and `test_rin_is_not_promoted_to_a_column` green.
- [ ] `test_hull_number_has_no_hyphen` green, **including acceptance of `"MQ-25 004"`**.
- [ ] `test_eswbs_null_on_non_eswbs_scheme` and `test_no_informal_eswbs_group_table` green; at least two `HSCI` schemes present in the reference dataset. *(**07 §3.4**; 13 §5.2)*
- [ ] Every PLACEHOLDER value is marked in the schema, echoed on the response where a consumer could otherwise mistake it for real, and listed in the data card's divergence list. *(07 §1)*
- [ ] `AllowanceDocument.length_is_ambiguous` is carried to consumers on `allowance.updated`. *(07 §4.1)*
- [ ] No SNSL table, no `derivation_code`, no allowance computation. *(04 §7; 07 §4.9)*

### 14.7 Consumers

- [ ] **`packages/contracts/conformance/registry/consumers/<slug>/` exists for all twelve declared consumers**, and Registry's suite reports an absent or empty directory as a **named skip with the owning slug** rather than collecting nothing silently. *(**C3**; §11.5)*

---

## 15. Defects found in upstream documents

Found while writing this document. Each is a defect in the cited document, not a decision of this one. Items 1–5 affect implementation directly.

| # | Document | Defect | Correction | Status here |
|---|---|---|---|---|
| **1** | **04 §2** | Registry is given neither a `Proposal` aggregate nor any proposal operation, while **03 §7.2** includes `configuration_change` in the `kind` vocabulary, **03 §7.2.1** gives it `maintainer` authority *"then Registry confirmation"*, and **03 §11** states *"edge submits configuration-change proposals."* Finding **C39** was raised for exactly this gap and its fix reached 03 but not 04 | Add a `Proposal` aggregate and the claim/adjudicate operations to 04 §2, or state that `POST /assets/{id}/configuration-changes` subsumes them | **Implemented** as §6.5's two-mode submission plus rows 24–26. Flagged for a 04 tranche-3 edit |
| **2** | **03 §6** | ~~**11 §8.4 mandates `installed_item.identity_resolved`** — and it appears in **no** row of 03 §6's Registry catalog. Without a catalog row it has no declared consumers, so no consumer-driven conformance test can be written for the only mechanism by which an event published under a provisional id remains interpretable~~ **[RESOLVED — closes OQ-5.]** | Add the row to 03 §6 with consumers `pdm`, `telemetry`, `supply`, `failure-intel`, `design-advisory` | **Resolved.** 03 §6 now carries the row (§6, consumers `pdm`, `telemetry`, `supply`, `failure-intel`, `design-advisory`, `audit`); `tools/check_event_catalog.py` PASSes |
| **3** | **03 §6 vs §5.1/§5.4** | The catalog's short labels are not the `<aggregate>` token: `configuration.baseline_changed` and `allowance.updated` cannot be suffixes of an `event_type` consistent with **03 §5.1's own example topic** `fathom.registry.configuration_baseline.v1`, because §5.4's `event_type` grammar and §5.1's topic grammar share the aggregate token. **10 §4.5 logs this as OQ-6 and declines to resolve it** | State in 03 §6 that the labels are cross-references and give the wire `event_type` per row | **Resolved** in §3.2's mapping table, which `tools/check_event_catalog.py` must be taught |
| **4** | **11 §2.3 vs §2.2** | ~~`OutboxWriter.emit()` exposes no `partition_key` parameter, while the outbox table's `partition_key` column is `NOT NULL`.~~ **[ADDRESSED DIFFERENTLY, not the literal ask.]** `11-outbox-sync-library.md` §2.3: *"`partition_key` is not a parameter — it is derived, never supplied."* `emit()` computes it internally from `scope`/`subject` per 03 §5.1's partition rule (`asset_id` when `scope=asset`, otherwise the event's own scope identifier — `niin`, `class_id`, `mission_id`, `tycom_id` — and the literal `"fleet"` singleton for `scope=fleet`), rather than accepting a caller-supplied override | Closed — 11's own counter-decision, not this row's proposed signature change | **Resolved.** A caller cannot pass a different partition key than `scope`/`subject` implies, which 11 §2.3 argues is the property that makes per-asset ordering hold without every call site re-deriving it correctly |
| **5** | **10 §4.3 vs 03 §3.3** | `_HULL_OR_TAIL = ^(T-)?[A-Z]{2,5} \d{1,4}[A-Z]?$` and `_no_hyphen_in_hull` reject **`"MQ-25 004"` — document 03 §3.3's own worked example** — because the validator strips only a leading `T-` and the type-designation group admits no hyphen. Unmanned assets carry tail-style designators [13 §5.1], so this rejects a real class of asset the demonstration instantiates | Constrain the hull *number* (the portion after the space), not the whole string | **Worked around** by §4.3's CHECK, which constrains only the portion after the space. `packages/canonical-schemas` needs the same fix or Registry cannot serve an `AssetRef` for an unmanned asset |
| **6** | **09 §5.1 vs 10 §5.1** | Two annotation helpers for one job: `fathom_py_common.openapi.operation()` returning `{"openapi_extra": ...}`, and `fathom_contracts.operation.operation_extra()` used as `openapi_extra=`. Only the second registers the declaration (needed for `OAS005`) and carries `x-fathom-aggregate` (needed for `OAS013`) | Delete the `py-common` copy; 09 §1.2 already assigns `packages/contracts`' public API to 10 | Registry uses **10's `operation_extra()`** (§6) |
| **7** | **11 §4.2 vs 03 §5.4** | Two grammars for the producing node. 03 §5.4's envelope field `producer_node` is `"enterprise" \| "edge:<asset_id>"`; 11 §4.2's `producer_node_id` is `telemetry@ashore-1` / `telemetry@ssn796`, and 11 §4.2 says it is carried *"as `clock.hlc.node_id` and, redundantly and deliberately, as `producer_node`"* — which cannot be true of both grammars at once | State that `producer_node` carries 03 §5.4's vocabulary and `clock.hlc.node_id` carries the deployment-instance id, and that the dedup key uses the latter | **Both**, as distinct fields with distinct grammars (§7.2) |
| **8** | **03 §6** | 03 §6's catalog *"covers the nine sub-applications and does not enumerate platform services"*, so **12 §3.4's `equipment_family.updated` → `registry`** is an undeclared dependency. 12 logs it as OD-7. Registry consuming an event with no catalog row is finding **C4** in a new instance | Add Reference Data's topics and consumers to 03 §6 | **Consumed** and declared in `CONSUMES` (§7.3). Beyond 04 §2's three-event list, traceable to 12 §3.4 |
| **9** | **09 §4.4.2** | The sanctioned edge set marks **sub-application → sub-application** as **NO** with no exception, which makes 03 §4/§15 obligation 5's `changed_since` rebuild path and 11 §3.5's antecedent pull unreachable — both of which are mandated mechanisms, and 11 §2.8 ships a client for one of them | Add a narrow edge — `<any consumer> → <any producer>`, restricted to `x-substitution: required` GET operations — generically, not per service | **ADR required before Registry's chart merges** (§12.2) |
| **10** | **10 §4.3** | Declines to declare `eic` on `SystemRef`/`InstalledItemRef`, logging OQ-1 on the grounds that *"neither schema block in §3.3 declares the field."* **03 §3.3 now declares `eic?` on both**, so OQ-1 is resolved and 10 §4.3's omission is stale | Add `eic: str \| None` to both, 2–7 characters per 07 §3.2's truncation rule, with no join permitted | Registry serves `eic` on both refs and **cannot** until `canonical-schemas` adds the field, since `extra="forbid"` will reject it |
| **11** | **10 §4.5** | ~~`EventEnvelope` has **no `producer_node` field**, and `dedup_key` is the two-part `(producer.slug, monotonic_seq)` under OQ-5.~~ **[RESOLVED — half-applied, now fully.]** `producer_node` was added to `EventEnvelope`, but `dedup_key` (and `precedes`) were left returning/comparing the two-part key — a live contradiction against `producer_node`'s own docstring. Both are now three-part, matching `11-outbox-sync-library.md`'s `DedupKey = tuple[str, str, int]` | Closed — no correction needed | **Resolved.** Registry's own events are unaffected in value (always `"enterprise"`), and the field now both exists and is actually used |
| **12** | **10 §6.3** | The reference-dataset docstring states *"~2,500 distinct NIINs"* from 06 §7, but **07 §8 supersedes it to ~4,000–6,000** and 07's status line says it *"Supersedes the LOW-confidence configuration estimates in 06 §7"* | Cite 07 §8 | Registry's fixtures follow **07 §8** |
| **13** | **04 §2** | Ownership boundary reads *"equipment and installed-item records"*, using a term 03 §3.2 lists as a losing variant and 09 §7.2 bans from identifiers | *"installed-item records"* | §1.2 note 2. No `equipment*` identifier exists in this service |
| **14** | **04 §2** | *"the ESWBS system hierarchy"* is contradicted by **07 §3.4**, which names the correction as *"a real change to the Phase 3 design of the Registry"* | *"the system hierarchy, of which ESWBS is one scheme selected by `HSCI`"* | §1.2 note 1; implemented in §4.1, §4.3 |
| **15** | **03 §11** | The conflict-policy table is still structurally malformed — the header row, then the clock-discipline paragraph, then the body rows, plus one row with `—` as its aggregate. Already flagged by **09 §11 item 10** and **11 §13 item 2**; **the table is contractual** | Move the paragraph above the header | Transcribed correctly in §4.10 |
| **16** | **03 §2 principle 4** | *"Every payload referencing an asset, system, installed item, or part uses the identifiers defined in **§4**"* — identity references are **§3.3**; §4 is REST conventions. In the same family as the eight stale cross-references 09 §11 item 8 already lists | Read §3.3 | Followed as §3.3 |
| **17** | **03 §5.4** | The `producer_node` comment cites *"the dedup key in §5.4"* from inside §5.4 — a self-reference that gives an implementer nothing to follow | Cite the four rules that follow, or §5.2 | Cosmetic |
| **18** | **05 §3.4 "Verified sound"** | Asserts *"every event published in 04 is present in the 03 catalog"*, which item 2 above contradicts once 11 §8.4's event is accounted for, and *"all package paths in 03 match the 01 §11 monorepo layout"*, which 09 §11 item 3 already narrows | Narrow both claims | Flagged |




