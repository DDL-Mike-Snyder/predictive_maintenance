# Build Framework 11 — The Outbox & Sync Library

| | |
|---|---|
| **Status** | Wave 1 build framework. Binding on every program-built service |
| **Deliverable** | `fathom-sync` — one library, written once, consumed by all nine sub-applications and every platform service that produces or consumes events |
| **Source of truth** | [03 — Integration Contracts](../architecture/03-integration-contracts.md) §5.2, §5.3, §5.4, §11, §15.11–16 · [01 — System Architecture](../architecture/01-system-architecture.md) §5, §12 · [05 — Review Findings](../architecture/05-architecture-review-findings.md) D2, D3, D4, D5, D8, D9, D18, D25, D28, D29, D30, C21 · [08 — Standards Alignment](../architecture/08-standards-alignment.md) §3 |
| **Siblings** | [09 — Monorepo & Conventions](09-monorepo-and-conventions.md) (ORM selection, Definition of Done template, lint gates) |
| **Classification** | Internal |

---

## 0. How to read this document, and why it exists at all

Nine sub-applications and at least six platform services must each implement the transactional outbox (document 03 §15.11), the consumer inbox (§15.12), and — for those with an edge deployment profile (document 01 §12) — edge reconciliation against the per-aggregate conflict policy table (document 03 §11).

The architecture review found **more correctness defects in this one mechanism than in any other part of the system**: D2 (the inbox protocol as originally written silently drops events), D3 and D4 (baseline epoch races and cross-topic ordering), D5 (unrebuildable read models, wrong compaction key), D9 (monotonic merge on the wrong key), D28 (unbounded edge outbox growth), D29 (no time-synchronization design at all, while two merge policies depended on trusted clocks), D30 (replay firing live side effects), and C21 (the universal outbox implemented inside a component declared inert).

Nine independent implementations of this mechanism would produce nine subtly different, subtly wrong versions of exactly the code the review found most defective. So it is written once, here.

**Every implementation rule below carries a "why this matters" note restating the failure scenario in plain terms.** Those notes are not commentary. They are there because the shortest path from correct code to broken code is an implementer who does not know why a line is load-bearing and "simplifies" it. If you are tempted to remove something, read its note first; if the note does not explain the removal away, the removal is a regression.

Rules trace to a document 03 section or a document 05 finding. Where this document decides something the architecture does not dictate, the decision is flagged **`DECISION`** with its justification.

---

## 1. Purpose and scope

### 1.1 What the library provides

| Component | Applies to | Active in the cloud-only demonstration? |
|---|---|---|
| **Outbox writer** — enlists an event in the caller's own database transaction | Every program-built service that publishes any event (03 §15.11, "without exception, including sub-applications with no current edge profile") | **Always active** |
| **Outbox relay** — drains the outbox to Redpanda | Same | **Always active** — see §1.3 |
| **Inbox** — record-and-apply-atomically consumption, epoch fencing, replay handling | Every program-built service that consumes any event (03 §15.12) | **Always active** |
| **Clock discipline module** — monotonic sequencing, HLC, `sync_quality` attestation, step detection | Every service. The outbox writer cannot construct an envelope without it | **Always active** |
| **Conflict policy registry** — per-aggregate policy declarations and merge strategies | Every service declares its policies or accepts the §11 default (03 §15.16) | Declarations always active; merge paths exercised only where an edge profile exists |
| **Divergence budget tracker & write gate** | Services with an edge profile | Declarations always active; breach path exercised at the edge |
| **Provisional identity minting & alias resolution** | Edge-profile services (mint) and every read model (resolve) | Resolver always active; minting only at the edge |
| **Edge reconciliation coordinator** | Edge-profile deployments only | **Legitimately inert / absent** — see §1.3 and §9 |
| **Fault-injection & clock-skew test harness** | Every service's conformance suite | **Always active in CI** |

### 1.2 Deployment profiles per service

Derived from document 01 §12 (afloat resident subset) and document 06 §4 (the resolved edge-scope decision).

| Service | Edge profile | What it does at the edge |
|---|---|---|
| `telemetry` — Condition & Telemetry | **Yes** | Edge-authoritative ingest of samples/batches; edge-resident detector ensemble producing anomaly candidates `[D18]`; usage counters |
| `pma` — Post-Mission Analysis | **Yes** | Afloat mission review and anomaly tagging; small edge pre-screener `[D18]` |
| `maintenance` — Maintenance Execution & Scheduling | **Yes, one path only** | Edge-authoritative, append-only **maintenance action records** `[D8]`. Work orders, authorizations and work packages remain server-authoritative and are *not* edge-writable |
| `pdm` — Predictive Maintenance | Read-only cache | Holds cached predictions with an explicit staleness horizon, presented as degraded (03 §11). Inbox-only; mints no edge writes |
| `registry` | No | Enterprise-authoritative. Participates ashore in provisional-identity resolution (§8) |
| `fleet-status`, `supply`, `failure-intel`, `design-advisory` | No | Enterprise only. Still implement outbox + inbox + clock discipline (03 §15.11) |
| Platform: `sync`, `audit`, `notification`, `reference-data`, `knowledge-retrieval`, `gateway`, `auth`, `tool-server` | `sync` hosts the coordinator; others no | `audit` receives `sync_quality` for permanent retention (§10.5) |

> **Why this matters.** Document 03 §15.11 makes the outbox universal *deliberately* — "including sub-applications with no current edge profile." A service that skips the outbox because it has no ship deployment today cannot acquire one later without a rewrite, and document 01 §12 names the outbox/inbox pair as "the load-bearing seam; absent it, offline synchronization becomes a rewrite rather than a feature."

### 1.3 The C21 correction — what is inert and what is emphatically not

Document 01 §5 defines the Sync Gateway (`sync`) as **two components**: "an **always-active** outbox and inbox relay library consumed by every sub-application and platform consumer, and an **edge reconciliation coordinator** that is inert in the demonstration."

Finding **C21** was raised because an earlier revision placed the universal outbox inside a component described as inert — and "if outbox drain is inert, no event reaches the broker." The whole event backbone would be dead in the demonstration.

The corrected split, which this library implements structurally:

- **The outbox relay is always active, in every deployment, cloud-only included.** It publishes to Redpanda. It is in-process with the owning service, not a separately schedulable deployment, precisely so that nobody can turn it off by scaling something to zero.
- **The edge reconciliation coordinator is the ONE component legitimately inert or absent in the cloud-only demonstration.** It is a distinct deployable with its own feature flag.

**Mandatory CI gate.** A test asserts that the relay's enablement is not reachable from the coordinator's feature flag — that is, that `SYNC_EDGE_COORDINATOR_ENABLED=false` leaves the relay running and events flowing. Name the test `test_c21_relay_not_gated_by_coordinator_flag` so that anyone who breaks it finds the finding.

### 1.4 Library location and packaging

**`DECISION`.** Library source lives at `platform/sync/lib/`, published into the monorepo's internal index as the `fathom-sync` distribution; the coordinator deployable lives at `platform/sync/coordinator/`. Justification: document 01 §5 names `sync` as the owner of *both* components, and co-locating them keeps the wire protocol and the record format versioned together. The alternative — `packages/py-common/sync/` — matches the monorepo's convention that shared libraries live under `packages/`, and is flagged in §13 as a convention question for document 09 to settle. Whichever wins, the import path must be `fathom_sync`, and nothing in this document changes.

---

## 2. The outbox pattern, exactly

### 2.1 Placement: colocated in the service's own database

The outbox table lives **in the service's own database, in the same logical database as the aggregate tables it accompanies**. Never a shared outbox database. Never a second cluster.

> **Why this matters.** Document 03 §15.13 requires each sub-application to own exactly one logical database and reach no other; document 01 §11 enforces it with default-deny NetworkPolicy — "each service may reach only its own database and the event bus." A separate outbox database would place the state change and its event in different transactional domains, which destroys the entire guarantee the outbox exists to provide (there is no atomic two-database commit here, and there will not be one). Finding **D33** is the precedent: Condition & Telemetry's two databases were a defect requiring separate schemas of one owned cluster or explicit Phase 3 justification. Telemetry's TimescaleDB is the one place this bites — see §2.7.

### 2.2 Table schema

```sql
CREATE TABLE outbox (
  -- Relay ordering and identity
  outbox_id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  event_id             uuid        NOT NULL UNIQUE,       -- 03 §5.4; consumer idempotency key

  -- Producer identity and THE ordering key (03 §5.4 clock discipline)
  producer_slug        text        NOT NULL,              -- §3.1 slug, no variation
  producer_version     text        NOT NULL,
  producer_node_id     text        NOT NULL,              -- see §4.2: enterprise vs edge instance
  monotonic_seq        bigint      NOT NULL,              -- gap-free per (producer_slug, producer_node_id)
  hlc_physical_ms      bigint      NOT NULL,
  hlc_logical          integer     NOT NULL,
  hlc_node_id          text        NOT NULL,

  -- Event typing and routing
  event_type           text        NOT NULL,              -- fathom.<slug>.<aggregate>.<verb>
  event_version         integer    NOT NULL,
  topic                text        NOT NULL,              -- fathom.<slug>.<aggregate>.v<major>
  partition_key        text        NOT NULL,              -- asset_id, or the event's own scope id
  compaction_key       text        NULL,                  -- MUST differ from partition_key [D5]
  aggregate            text        NOT NULL,              -- selects the conflict policy (§7)
  aggregate_id         text        NOT NULL,

  -- Envelope fields (03 §5.4)
  scope                text        NOT NULL,              -- asset|system|installed_item|niin|class|mission|tycom|fleet
  subject              jsonb       NOT NULL,              -- exactly one scope identifier
  baseline_epoch       bigint      NULL,                  -- [D3, D4]
  classification       jsonb       NOT NULL,              -- ClassificationLabel, 03 §7.3
  correlation_id       uuid        NOT NULL,
  causation_id         uuid        NULL,
  replay               boolean     NOT NULL DEFAULT false, -- 03 §5.3 [D30]
  occurred_at          timestamptz NOT NULL,
  recorded_at          timestamptz NOT NULL,              -- audit basis; ms precision (AU-12(1))

  -- Clock attestation (03 §5.4). Retained permanently; see §10.5
  source_time          timestamptz NOT NULL,              -- NEVER an ordering input
  ingest_time          timestamptz NULL,                  -- set by the receiver, not here
  sync_quality         jsonb       NOT NULL,

  -- Payload. Encrypted at rest (08 §3.5, SC-28); large results by reference [D27]
  payload_ciphertext   bytea       NULL,
  payload_ref          text        NULL,                  -- s3:// URI when payload exceeds inline_max
  payload_sha256       bytea       NOT NULL,              -- over plaintext canonical form
  payload_kek_id       text        NOT NULL,              -- per-classification key (03 §13.1)

  -- Signature (AU-10, 08 §3.5)
  record_signature     bytea       NOT NULL,
  signing_key_id       text        NOT NULL,

  -- Relay state
  shard                smallint    NOT NULL,              -- hash(partition_key) % shard_count
  claimed_by           text        NULL,
  claimed_until_mono   bigint      NULL,                  -- MONOTONIC deadline, never wall clock
  attempt_count        integer     NOT NULL DEFAULT 0,
  published_at         timestamptz NULL,                  -- broker-accepted
  acked_by_shore_at    timestamptz NULL,                   -- edge only; gates pruning [D28]

  CONSTRAINT outbox_seq_unique UNIQUE (producer_slug, producer_node_id, monotonic_seq),
  CONSTRAINT outbox_payload_present CHECK (payload_ciphertext IS NOT NULL OR payload_ref IS NOT NULL),
  CONSTRAINT outbox_compaction_key_distinct CHECK (compaction_key IS NULL
                                                   OR compaction_key <> partition_key)
);

CREATE INDEX outbox_unpublished ON outbox (shard, outbox_id) WHERE published_at IS NULL;
CREATE INDEX outbox_prunable    ON outbox (published_at) WHERE published_at IS NOT NULL;
```

Two constraints are doing real work:

- **`outbox_compaction_key_distinct`.** Finding **D5**: compaction key equalled partition key equalled `asset_id`, so compacting the prediction topic "collapses to one event per hull and discards every other item's predictions." Document 03 §5.1 fixes it — the compaction key is the *aggregate* key (`installed_item_id`, `(niin, location)`, `baseline_id`). This CHECK makes the bug unwritable rather than merely discouraged.
- **`outbox_seq_unique`** over `(producer_slug, producer_node_id, monotonic_seq)`. See §4.2 for why `producer_node_id` must be in the key.

### 2.3 The transactional guarantee, concretely

The library exposes one port and one rule.

```python
class OutboxWriter(Protocol):
    def emit(
        self,
        uow: UnitOfWork,               # the caller's ambient transaction — REQUIRED, never optional
        *,
        event_type: str,
        aggregate: str,
        aggregate_id: str,
        scope: Scope,
        subject: Subject,
        payload: CanonicalSchema,       # from packages/canonical-schemas
        classification: ClassificationLabel,
        baseline_epoch: int | None = None,
        causation_id: UUID | None = None,
        compaction_key: str | None = None,
        replay: bool = False,
    ) -> EventId: ...
```

**`partition_key` is not a parameter — it is derived, never supplied.** Registry's build-framework agent flagged its absence against §2.2's `NOT NULL` column as a contradiction; it is not one, but the derivation belongs here rather than left implicit. `emit()` computes it from `scope`/`subject` per document 03 §5.1's partition rule before the row is written: `asset_id` when `scope=asset`, and otherwise the event's own scope identifier (`niin`, `class_id`, `mission_id`, `tycom_id`; `subject` is empty for `scope=fleet`, whose partition key is the literal string `"fleet"`, a singleton partition). A caller cannot pass a different partition key than the one `scope`/`subject` implies — that is the property that makes "per-asset ordering within a topic" (03 §5.1) hold without every call site re-deriving it correctly.

Three invariants, enforced mechanically:

1. **`emit()` writes through the caller's transaction and never opens a connection.** It takes the ambient `UnitOfWork`; it has no session factory, no engine, no connection pool of its own. It cannot commit — `UnitOfWork` exposes no `commit()` to `emit()`'s type.
2. **`emit()` never publishes.** Nothing in the write path touches Redpanda. Publication is exclusively the relay's job.
3. **A service commits a state change and its event together, or neither.**

The reference adapter targets the session/`begin()` idiom of the ORM selected in [09 — Monorepo & Conventions](09-monorepo-and-conventions.md); if 09 selects a different ORM, only the adapter changes and nothing else in this document moves. The canonical shape:

```python
# The ONLY sanctioned write shape. Copy it.
async with uow.begin():                          # one transaction, opened by the service
    item = await repo.record_maintenance_action(cmd)      # (1) domain state change
    outbox.emit(                                          # (2) event, SAME transaction
        uow,
        event_type="fathom.maintenance.maintenance_action.recorded",
        aggregate="maintenance_action_record",
        aggregate_id=str(item.record_id),
        scope=Scope.INSTALLED_ITEM,
        subject=Subject(installed_item_id=item.installed_item_id),
        payload=MaintenanceActionRecorded.from_domain(item),
        classification=item.classification,
        baseline_epoch=item.baseline_epoch,
    )
# commit here. (1) and (2) are atomic. Nothing was published yet.
```

**Prohibited shapes, each rejected by a CI lint (§11):**

- `emit()` called outside an open transaction.
- `emit()` called after `commit()` (the "commit then announce" bug the outbox exists to eliminate — 03 §5.2).
- Any `producer.send(...)` / Kafka client call inside a service module other than the relay.
- Any direct `INSERT INTO outbox` bypassing `emit()` — it would skip sequencing, signing, and encryption.
- Any write to another service's database. Finding **C7/D10**: Domino Jobs writing directly into PdM's datastore "bypasses the outbox." Batch results enter through the bulk, idempotent, fenced HTTP operation of 03 §4 — never through SQL.

> **Why this matters.** Without one transaction, the failure is: the service commits a maintenance action, then dies before publishing. The action exists; no consumer ever hears about it; the label stream that "is the label stream for every model in the system" (03 §6) silently loses a record with no error anywhere. This is also exactly the observable property a substituting implementation must satisfy (03 §10: "no state change without a corresponding event, verified by a fault-injection driver"), which is why the harness in §10 is part of this library rather than each team's improvisation.

### 2.4 The relay: polling, not CDC

**`DECISION` — the relay is a transactional claim-based poller, not a logical-replication/CDC consumer.** The architecture says only "a relay publishes from the outbox" (03 §5.2). The choice is mine; here is the justification.

| Criterion | Claim-based polling | Logical replication / CDC (Debezium-style) |
|---|---|---|
| **Always-active, never inert (C21)** | Runs in-process with the service. There is no separate deployment to scale to zero, and no scenario where "the outbox is inert" | A separate connector deployment — precisely the shape C21 warns about, and the shape somebody will disable in a constrained demo |
| **Disconnected edge safety** | Backlog is ordinary table rows. Weeks of backlog costs disk in a table you can measure and prune | **An inactive replication slot pins WAL indefinitely.** A submarine dark six weeks with a stalled connector fills the data directory and takes the whole database down — a self-inflicted outage at the worst possible moment |
| **Edge footprint** | Zero extra pods. Document 01 §12 constrains the afloat deployment to "a subset of Sustainment Plane services" | Adds a connector plus its own runtime to every hull |
| **Air-gap / STIG** | No extra images, no extra STIG surface | Another image to vendor, harden, and patch on Iron Bank's 5/15-day clocks against a hull offline for weeks (08 §3.6) |
| **Signing and encryption** | The signed, encrypted record *is* the row; the relay ships bytes it did not author | CDC ships post-images of columns; envelope construction drifts from the write path |
| **Latency** | ~50–200 ms with adaptive interval; `LISTEN/NOTIFY` wake-up as a pure optimization | Lower, and irrelevant: 03 §2 forbids synchronous cross-service calls on a compute path, so no correctness property depends on sub-100 ms event latency |
| **Ordering control** | Explicit and inspectable (§2.5) | Inherited from WAL order, harder to reason about across shards |

Polling loses on raw latency and wins on every property this program actually needs. The decision is recorded here so no Phase 3 team re-litigates it per service.

### 2.5 Relay algorithm, and how per-partition ordering survives

Document 03 §5.1: per-asset ordering within a topic "is the only ordering guarantee the design relies on." A relay with N concurrent workers over one unordered claim query breaks it — two workers can publish two events for the same `asset_id` out of order. So claiming is **sharded by partition key with one lease per shard**.

```
shard_count: fixed at deploy time, per service, power of two (default 8). Changing it
             requires a drain-to-empty; the value is recorded in the service's Helm chart.

for shard in shards_leased_by_this_worker:            # exactly one worker per shard at a time
    rows = SELECT * FROM outbox
             WHERE published_at IS NULL AND shard = :shard
             ORDER BY outbox_id                        -- == (producer, monotonic_seq) order
             LIMIT :batch_size
             FOR UPDATE SKIP LOCKED
    for row in rows:                                   # STRICTLY sequential within a shard
        verify_signature(row)                          # detect at-rest tampering before publish
        publish(topic=row.topic, key=row.partition_key, envelope=row)   # synchronous ack
        UPDATE outbox SET published_at = now(), attempt_count = attempt_count + 1
          WHERE outbox_id = row.outbox_id
    commit
```

Rules:

- **One in-flight publish per shard.** Batch for throughput by claiming many rows; publish them one at a time, in `outbox_id` order, awaiting broker acknowledgement each time. Pipelining within a shard reintroduces reordering under partial failure.
- **Shard leases are held in the same database** (`outbox_relay_lease` table) with a **monotonic-clock** deadline. `claimed_until_mono` is monotonic-derived, never `now()`.
  > **Why this matters.** Document 03 §5.4: "Durations, timeouts, retry backoff, and lease expiry use a monotonic clock, never the wall clock. A wall-clock backoff loop storms or hangs the instant a step lands — again, at reconnection." A wall-clock lease deadline plus a mandated `makestep 1 -1` backward step equals two workers believing they hold the same shard, publishing the same partition out of order, at the exact moment the outbox is draining after reconnect `[D29]`.
- **Duplicates are expected and correct.** If the publish succeeds and the `UPDATE` fails, the row republishes. At-least-once is the contract (03 §5.2, "Exactly-once is assumed nowhere"); consumers dedup on `event_id` / `(producer, node, monotonic_seq)`.
- **Poison rows quarantine, never block.** After `max_attempts` (default 12) the row is moved to `outbox_quarantine`, a metric fires, and the shard proceeds. A permanently stuck row must not stall an entire asset's stream — but quarantining is an **incident**, not routine: it means a state change exists without its event, violating obligation 03 §15.2, and it pages.
- **Backoff is monotonic and jittered**, per §4.6.

### 2.6 Pruning — closing D28

Finding **D28**: "the edge outbox doubles telemetry storage with no pruning rule," dispositioned PHASE 3. That phase is now, and the rule is:

```python
class OutboxRetentionPolicy:
    inline_payload_max_bytes: int = 65_536     # above this, payload_ref to object storage
    min_retention: timedelta                    # per service; >= the longest consumer replay need
    prune_requires_shore_ack: bool               # True on every edge deployment
```

A row is prunable only when **all** hold:

1. `published_at IS NOT NULL`.
2. At the edge: `acked_by_shore_at IS NOT NULL` (the shore high-water mark advanced past it — §9.3).
3. `age(published_at) > min_retention`.
4. `sync_quality` has been exported to Audit (§10.5) — it is retained permanently even though the row is not.

Additional rules for high-volume streams:

- **Telemetry never stores sample payloads inline in the outbox.** `telemetry.batch_ingested` carries a `payload_ref` into object storage; the outbox row carries the envelope plus the reference. This is the same discipline document 03 §6 applies to `prediction.updated` — "references to the run artifact rather than inline result sets" `[D27]` — and it is what prevents the doubling D28 describes.
- **Disk headroom is a readiness signal.** `/readyz` degrades when the unpublished-and-unacked backlog exceeds a declared fraction of provisioned storage, so a hull discovers the problem before the database stops accepting writes.

### 2.7 One database, two engines (Telemetry's exception)

Condition & Telemetry owns a TimescaleDB cluster (01 §14, and `[D33]`). Its outbox lives **in that same cluster**, alongside the hypertables, so `emit()` remains transactional with the ingest write. It does not live in a second Postgres. If any service genuinely cannot colocate, the escalation path is 03 §15.13 — separate schemas of one owned cluster, or explicit Phase 3 justification — not a cross-database "transaction."

### 2.8 The bulk / backfill write path

Per 03 §5.3, "historical load and replay never traverse the live event bus, because replay would fire live side effects — notifications, work candidates, requisitions" `[D30]`.

The library's backfill mode:

```python
with outbox.backfill_mode(reason="24-month synthetic history load", ticket="FATHOM-1234"):
    async with uow.begin():
        await repo.bulk_upsert(batch)
        outbox.emit(uow, ..., replay=True)     # forced True inside backfill_mode
```

| Rule | Detail |
|---|---|
| **Inbound** | Bulk writes arrive at the receiving service's bulk, idempotent, fenced operation (03 §4, `[D10, C7]`) carrying `X-Backfill: true` and `Idempotency-Key`. Never SQL, never the live single-record path |
| **`X-Backfill: true` suppresses live side effects** | The library exposes `SideEffectGate.suppressed_for_backfill()`. Notification dispatch, work-candidate generation, requisition creation, and operator alerting consult it and no-op. Suppression is at the *side-effect* site, not the event site — the event is still produced |
| **Events are still produced, marked `replay: true`** | 03 §5.3. The read models must still converge; only the side effects are suppressed |
| **Consumers must handle `replay: true` idempotently and raise no operator-visible alert** | 03 §5.3. The library's inbox does this by default: `replay=True` events bypass the notification hooks. A consumer that overrides this must justify it in its Phase 3 design |
| **Replay for read-model rebuild does not use the bus at all** | It uses `GET /{collection}?changed_since=&cursor=` (03 §4, §5.3) `[D5, D25, D30]`. The library ships `ChangedSinceRebuilder` so nine teams do not write nine cursor loops |
| **Backfill uses its own monotonic sequence space** | Backfill events are sequenced by the same `(producer, node)` counter — they are real events in the producer's stream. `replay: true` is the only distinguishing flag; ordering discipline is unchanged |

> **Why this matters.** D30's scenario: someone replays 24 months of history through Kafka to rebuild a read model. Every `casrep_risk.raised` re-fires notifications; every `prediction.updated` re-generates work candidates; Supply issues requisitions against two-year-old shortfalls. Real-world effect from a maintenance operation. The fix is structural — backfill and rebuild have their own paths — and it only holds if `X-Backfill` and `replay` are honored by *every* consumer, which is why the default lives in the library.

---

## 3. The inbox pattern, exactly, with the corrected semantics

### 3.1 The rule

> **`event_id` is recorded and the resulting state change is applied IN ONE TRANSACTION. Recording receipt before processing is prohibited.** (03 §5.2, `[D2]`)

Where a single transaction is genuinely impossible, the inbox row carries `processed_at`, and **only rows with `processed_at` set suppress redelivery.**

### 3.2 The mandatory comment template

Every service's inbox integration includes this comment, verbatim, immediately above its handler dispatch. Its presence is checked by CI (§11).

```python
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
```

### 3.3 Table schema

```sql
CREATE TABLE inbox (
  event_id          uuid        PRIMARY KEY,
  producer_slug     text        NOT NULL,
  producer_node_id  text        NOT NULL,
  monotonic_seq     bigint      NOT NULL,
  event_type        text        NOT NULL,
  aggregate         text        NOT NULL,

  topic             text        NOT NULL,
  kafka_partition   integer     NULL,
  kafka_offset      bigint      NULL,

  received_at       timestamptz NOT NULL DEFAULT clock_timestamp(),
  ingest_time       timestamptz NOT NULL,        -- envelope clock.ingest_time
  sync_quality      jsonb       NOT NULL,        -- copied from the envelope; exported to Audit

  -- THE suppression column. NULL => seen but NOT applied => MUST be reprocessed.
  processed_at      timestamptz NULL,

  -- Antecedent / epoch fencing (03 §5.4) [D3, D4]
  blocked_on_epoch  bigint      NULL,
  blocked_since_mono bigint     NULL,

  attempt_count     integer     NOT NULL DEFAULT 0,
  last_error        text        NULL,
  replay            boolean     NOT NULL DEFAULT false,

  CONSTRAINT inbox_seq_unique UNIQUE (producer_slug, producer_node_id, monotonic_seq)
);

CREATE INDEX inbox_unprocessed ON inbox (received_at) WHERE processed_at IS NULL;
CREATE INDEX inbox_blocked     ON inbox (blocked_on_epoch) WHERE blocked_on_epoch IS NOT NULL;
```

The suppression query, and the only one permitted:

```sql
SELECT 1 FROM inbox WHERE event_id = $1 AND processed_at IS NOT NULL;
```

A lint forbids any `SELECT ... FROM inbox WHERE event_id = ?` that does not constrain `processed_at`.

### 3.4 The consume loop

```python
async def handle(envelope: EventEnvelope) -> None:
    async with uow.begin():                                  # ONE transaction
        if await inbox.already_applied(uow, envelope.event_id):   # processed_at IS NOT NULL
            return                                            # true duplicate; offset commits

        # Epoch fencing BEFORE any state change [D3, D4]
        gate = await epoch_fence.evaluate(uow, envelope)
        if gate.blocked:
            await inbox.record_blocked(uow, envelope, on_epoch=gate.required_epoch)
            return                                            # retried by the blocked-row sweeper

        await inbox.record(uow, envelope)                      # processed_at LEFT NULL here
        await dispatch(uow, envelope)                          # the state change
        await inbox.mark_processed(uow, envelope.event_id)     # processed_at = clock_timestamp()
    # commit: record + state change + processed_at, atomically.
    # Kafka offset is committed only AFTER this transaction commits.
```

Notes that are not optional:

- **`record()` sets `processed_at` NULL; `mark_processed()` sets it.** Both are inside the transaction, so on commit the row is complete and on crash the row either does not exist or exists with `processed_at` NULL. Both states are safe. This is why the two-step exists at all: it makes the "impossible" case of 03 §5.2 representable without ever being unsafe.
- **The Kafka offset commits after the database transaction, never before.** Offset-then-apply is D2 wearing a different hat.
- **Handlers receive the `UnitOfWork` and must not open their own.** Enforced by signature.
- **Handlers that emit events use `outbox.emit(uow, ...)` in the same transaction** — consume, apply, and announce become one atomic step, and this is the chain that makes a nine-service graph converge.

### 3.5 Epoch fencing and the antecedent rule

Per 03 §5.4: "A consumer that receives an event with an epoch ahead of its own configuration read model **must block that event until the antecedent configuration event is applied**, resolved via `causation_id` or by reading `changed_since` from the Registry."

```python
class EpochFence:
    def current_epoch(self, uow, asset_id: AssetId) -> int: ...
    async def evaluate(self, uow, envelope) -> FenceDecision:
        """BLOCK when envelope.baseline_epoch > current_epoch(asset).
        Resolution order:
          1. If causation_id names an unapplied event, wait for it.
          2. After `antecedent_wait` (monotonic, default 30 s), actively pull
             GET /api/v1/registry/configuration-baselines?changed_since=<epoch>
             and apply, then re-evaluate.
          3. After `antecedent_deadline` (monotonic, default 15 min), page.
             NEVER apply out of order, and never silently drop.
        """
```

And the producer-side half of the same fence, which belongs here because both halves are the same defect:

```python
class BaselineFencedComputation:
    """Guards any long-running computation whose result depends on configuration.
    Reads baseline_epoch at start; re-reads at publish; REFUSES to publish a
    result computed under a superseded epoch. [D3]"""
```

> **Why this matters.** Two failure scenarios the review found, which are one bug seen from two sides.
> **D3:** a long scoring job reads baseline B1; the baseline becomes B2 mid-run; the job's stale result lands *after* the invalidation and wins — "and looks fresher by `computed_at`." A stale prediction for a replaced pump outlives its own invalidation, and appears to be the newest information available.
> **D4:** per-asset ordering is per-*topic*. Configuration, prediction, and invalidation live on different topics, so a consumer can legitimately see a prediction computed under B2 before it has processed B1→B2. `causation_id` existed but "no consumer rule uses it and no consumer can block on an unseen antecedent." The blocking rule *is* the cross-topic causal ordering; per-asset partitioning does not supply it and never will.

### 3.6 Read-model lag and staleness refusal (03 §15.14)

The library provides it so nobody omits it:

```python
class ReadModelLag:
    def observe(self, topic: str, envelope) -> None: ...
    def lag(self, topic: str) -> timedelta: ...            # monotonic-derived
    def blocked_events(self) -> int: ...
    def readyz(self) -> ReadinessReport: ...               # 03 §4 /readyz, §5.2
    def require_fresh(self, bound: timedelta, *, computation: str) -> None:
        """Raise StalenessBoundExceeded if lag > bound. The scheduling optimizer
        in particular MUST call this before solving. [D6]"""
```

> **Why this matters.** D6: the optimizer "solves over a stale non-atomic mixture," then reserves per-NIIN — 37 of 40 reservations succeed, the 38th fails, orphans persist, and 37 spurious availability events degrade every other asset's planning. A computation with a correctness dependency on freshness that does not refuse to run when stale will produce confidently wrong plans forever, silently.

---

## 4. The clock discipline module

**This is the single most important code in the library.** Read document 03 §5.4 and document 08 §3.3 before touching it.

### 4.1 The threat, stated once

The Ubuntu 22.04 STIG rule **V-260520** mandates `makestep 1 -1`: unlimited backward clock steps whenever the offset exceeds one second. That step fires **precisely when a disconnected node reconnects and begins draining its outbox.** Two writes from one process can therefore carry inverted wall-clock timestamps. The Kubernetes STIG contains **zero** time-synchronization rules, so correctness is inherited entirely from the host OS STIG, and one skewed node silently poisons every pod on it `[D29]`.

Compliance *guarantees* a non-monotonic clock at exactly the moment ordering matters most. This is not a hypothetical to be handled defensively; it is a scheduled event to be designed around.

### 4.2 Producer identity — a correction this library makes explicit

Document 03 §5.4 says ordering and deduplication use `(producer, monotonic_seq)`, where `producer` is "slug from §3.1, plus version." But an edge instance and the enterprise instance of the same slug are **two nodes each minting its own monotonic sequence**, so `(telemetry, 41)` is ambiguous — two different events collide on the dedup key, and one is silently dropped.

**`DECISION` — the library's dedup and ordering key is `(producer_slug, producer_node_id, monotonic_seq)`.** `producer_node_id` is a stable, configured, non-reused identifier for the producing deployment (e.g. `telemetry@ashore-1`, `telemetry@ssn796`), carried in the envelope as `clock.hlc.node_id` and, redundantly and deliberately, as `producer_node`. Flagged in §13 for document 03 to make explicit in the envelope. Every implementation uses the three-part key; nothing keys on two parts.

### 4.3 The monotonic sequence generator

```python
class MonotonicSequencer:
    """Gap-free, strictly increasing sequence per (producer_slug, producer_node_id).
    Allocated INSIDE the caller's transaction so the sequence and the outbox row
    commit together."""

    def next(self, uow: UnitOfWork, count: int = 1) -> Sequence[int]: ...
```

Backed by a row, not a Postgres `SEQUENCE`:

```sql
CREATE TABLE producer_sequence (
  producer_slug    text   NOT NULL,
  producer_node_id text   NOT NULL,
  next_seq         bigint NOT NULL,
  PRIMARY KEY (producer_slug, producer_node_id)
);
-- allocation, inside the caller's transaction:
UPDATE producer_sequence SET next_seq = next_seq + :count
 WHERE producer_slug = :slug AND producer_node_id = :node
 RETURNING next_seq - :count AS first_allocated;
```

**`DECISION` — a row-lock counter rather than a native sequence, accepting the serialization cost.** Native sequences are non-transactional: they leak values on rollback, so the stream has holes. A gap-free sequence gives consumers **loss detection** for free — a receiver that has seen 41 and 43 knows 42 exists and can demand it, which is exactly the property a ship-to-shore link with resume-from-offset needs (§9.3). Ordering alone would tolerate gaps; loss detection does not. The cost is that writers for one producer serialize on one row; at the demonstration's scale (~5M telemetry samples/day arriving as *batch* events, document 06 §7) this is nowhere near binding, and the batch-level event granularity of 03 §6 is what keeps it that way. If a service ever needs more, the escape hatch is `next(count=n)` to allocate a block in one statement — not a second sequence.

Additional rules:

- `producer_node_id` is **never reused** for a different deployment, and a restored database backup requires a new node id. Reuse means two live nodes minting the same sequence numbers, which is unrecoverable.
- The sequence never resets. Ever. Not on redeploy, not on migration.

### 4.4 The hybrid logical clock

```python
@dataclass(frozen=True, order=False)
class HLC:
    physical_ms: int       # NOT a wall-clock reading; see step_guard below
    logical: int
    node_id: str

    def __lt__(self, other: "HLC") -> bool:
        return (self.physical_ms, self.logical, self.node_id) < \
               (other.physical_ms, other.logical, other.node_id)
    # total order: lexicographic on (physical_ms, logical, node_id).
    # node_id is the deterministic tie-break, not a semantic input.


class HybridLogicalClock:
    """State (physical_ms, logical) is PERSISTED in the service's own database and
    restored on start, so a restart cannot regress the clock."""

    def send(self) -> HLC:
        pt = self._guarded_physical_ms()
        if pt > self._l:
            self._l, self._c = pt, 0
        else:
            self._c += 1                      # physical stalled or went backwards
        self._persist()
        return HLC(self._l, self._c, self._node_id)

    def receive(self, remote: HLC) -> HLC:
        pt = self._guarded_physical_ms()
        l_new = max(self._l, remote.physical_ms, pt)
        if l_new == self._l == remote.physical_ms:
            self._c = max(self._c, remote.logical) + 1
        elif l_new == self._l:
            self._c += 1
        elif l_new == remote.physical_ms:
            self._c = remote.logical + 1
        else:
            self._c = 0
        self._l = l_new
        self._persist()
        return HLC(self._l, self._c, self._node_id)

    def _guarded_physical_ms(self) -> int:
        """A monotonic-anchored wall-clock ESTIMATE, never a raw CLOCK_REALTIME read.

            estimate = anchor_wall_ms + (mono_now_ms - anchor_mono_ms)

        The anchor is re-established ONLY on a resync the StepDetector classifies as
        forward-consistent. A mandated backward step (makestep 1 -1) therefore does
        NOT drag the HLC's physical component backwards; the clock keeps advancing
        on the monotonic delta, records step_occurred, and the logical counter
        absorbs any stall. [03 §5.4, 08 §3.3]
        """
```

**The `_guarded_physical_ms` guard is the whole point.** A textbook HLC calls `time.time()` for `pt`. Under `makestep 1 -1` that reading jumps backward by seconds; `l` stalls; the logical counter carries ordering (which is *correct* but degenerate), and worse, on the next forward correction `l` leaps, compressing ordering across the discontinuity. Anchoring on `CLOCK_MONOTONIC` keeps the physical component well-behaved through the step. Comparison remains total and correct regardless.

### 4.5 Step detection — how `step_occurred` is actually determined

`sync_quality.step_occurred` is not a guess and not a chrony log scrape. It is measured.

```python
class StepDetector:
    """Samples (CLOCK_REALTIME, CLOCK_BOOTTIME) pairs at a fixed cadence and
    compares the two deltas. Monotonic time cannot jump; realtime can. Any
    divergence between them IS a step.

    sample cadence:  <= 1 s  (the Zero Trust Overlays' 1 s resync threshold,
                              08 §3.3 / 03 §5.4)
    threshold:       250 ms  (well above scheduler jitter, well below the STIG's
                              1 s step trigger)
    """

    BACKWARD_THRESHOLD_MS = -250
    FORWARD_THRESHOLD_MS  = +250

    def sample(self) -> StepObservation:
        r1 = time.clock_gettime_ns(time.CLOCK_REALTIME)  // 1_000_000
        m1 = time.clock_gettime_ns(time.CLOCK_BOOTTIME)  // 1_000_000
        d_real = r1 - self._r0
        d_mono = m1 - self._m0
        skew_ms = d_real - d_mono                 # 0 if the wall clock behaved
        self._r0, self._m0 = r1, m1

        if skew_ms <= self.BACKWARD_THRESHOLD_MS:
            self._latch_backward_step(skew_ms)    # PERSISTED latch
            return StepObservation(kind=StepKind.BACKWARD, skew_ms=skew_ms)
        if skew_ms >= self.FORWARD_THRESHOLD_MS:
            self._latch_forward_step(skew_ms)
            return StepObservation(kind=StepKind.FORWARD, skew_ms=skew_ms)
        return StepObservation(kind=StepKind.NONE, skew_ms=skew_ms)
```

Latch semantics, which matter as much as the detection:

- **The latch is persisted, in the service's own database.** A backward step immediately followed by a pod restart must still be reported. An in-memory flag loses exactly the event you most need.
- **The latch clears only after at least one record carrying `step_occurred = true` has been durably written and published.** "True if a backward step landed **since the last record**" (03 §5.4) is a per-record claim, so the latch cannot be cleared by the mere passage of time.
- **`CLOCK_BOOTTIME`, not `CLOCK_MONOTONIC`, for step detection.** On Linux `CLOCK_MONOTONIC` does not advance across suspend, so a suspended node would report a spurious forward step on resume. `CLOCK_MONOTONIC` remains correct for durations (§4.6) because there we *want* suspend excluded.
- **A backward step is an audit event**, emitted to Audit with the measured `skew_ms`. Skew is indistinguishable from tampering to an assessor (08 §3.3); a measured, timestamped, signed record of "the STIG-mandated step fired here, by this much" is the difference between a bounded documented condition and a finding.

### 4.6 The `sync_quality` attestation

```python
@dataclass(frozen=True)
class SyncQuality:                                   # 03 §5.4, retained permanently
    time_source: TimeSource       # gnss | usno_authenticated | upstream_ntp | holdover | unsynced
    offset_ms: float             # last measured offset
    dispersion_ms: float         # accumulated uncertainty — THE published epsilon
    seconds_since_sync: int
    step_occurred: bool          # from StepDetector's persisted latch
```

Populated by a sampler daemon, never by a synchronous shell-out on the write path:

| Field | Source |
|---|---|
| `time_source` | The selected reference from `chronyc -c tracking` / `sourcestats`. A GNSS refclock → `gnss`; an NTS-authenticated authoritative upstream → `usno_authenticated`; plain NTP → `upstream_ntp`; no reachable source but within the declared holdover spec → `holdover`; otherwise → `unsynced` |
| `offset_ms` | Last measured offset from tracking |
| `dispersion_ms` | `root_dispersion + skew_ppm × seconds_since_sync + sampler_cache_age`. **It grows monotonically while disconnected.** The cache-age term is included so a stale sampler reading inflates rather than understates uncertainty |
| `seconds_since_sync` | Monotonic-derived time since the last successful clock update |
| `step_occurred` | The persisted latch from §4.5 |

**Write-path rule.** `SyncQualitySampler` refreshes a cached snapshot every ≤1 s; `emit()` reads the cache. Never invoke `chronyc` inside a database transaction — it is a subprocess on a possibly-degraded node, and a hung `chronyc` would hold a transaction open on a ship.

**Honesty rule.** If no sampler reading exists, `time_source = unsynced` and `dispersion_ms = +inf`. Never fabricate a plausible value. "A time service that declares itself untrusted is far safer than one confidently serving wrong time" (03 §5.4).

**Epsilon branching** (03 §5.4, third rule):

```python
class EpsilonPolicy:
    def ordering_mode(self, sq: SyncQuality, inter_write_interval_ms: float) -> OrderingMode:
        """WALL_ASSISTED_PRESENTATION when dispersion_ms < inter_write_interval_ms / 2:
             a wall-clock hint may be shown to the operator.
           CAUSAL_ONLY otherwise:
             presentation is causal/sequence-based; NO timestamp arbitration; the
             operator interface displays a degraded-time indicator.
        Either way this affects PRESENTATION ONLY. Merge precedence is never a
        function of dispersion, because merge precedence is never a function of
        wall time at all."""
```

**Monotonic durations** (03 §5.4, second rule). The library owns every duration in the sync path so no team hand-rolls one:

```python
class MonotonicDeadline:
    @classmethod
    def after(cls, d: timedelta) -> "MonotonicDeadline": ...   # CLOCK_MONOTONIC
    def expired(self) -> bool: ...

def monotonic_backoff(attempt: int, *, base_ms=100, cap_ms=60_000, jitter=0.2) -> float: ...
```

Every lease, timeout, retry, TTL, staleness measurement, and divergence-budget clock in this library uses these. A wall-clock backoff loop "storms or hangs the instant a step lands — again, at reconnection" (03 §5.4).

### 4.7 The prohibition, and its mechanical enforcement

> **NO function in this library ever compares two `source_time` values to decide precedence.** Not for merge, not for last-writer-wins, not for tie-breaks, not "just as a fallback."

Enforcement is not a code-review convention. `source_time` is a distinct type whose comparison operators raise:

```python
@dataclass(frozen=True)
class SourceTime:
    """A producing node's wall clock at the domain event. NOT ORDERABLE.

    Comparison raises because a mandated STIG backward step (makestep 1 -1) fires
    at reconnection, so two writes from ONE process can carry inverted source_time
    values. Any code that orders on this is wrong at exactly the moment it matters.
    Order on (producer_slug, producer_node_id, monotonic_seq) or on the HLC.
    [03 §5.4 · findings D29, D9]
    """
    value: datetime

    def __lt__(self, other): raise ClockDisciplineError(self.__doc__)
    __gt__ = __le__ = __ge__ = __lt__
    def __sub__(self, other): raise ClockDisciplineError(self.__doc__)   # no durations either
    def for_display(self) -> str: ...        # the ONLY sanctioned use
    def for_audit(self) -> datetime: ...     # recording, not comparing
```

Plus a CI check (§11) that greps for `source_time`/`occurred_at`/`recorded_at` in any comparison, `max()`, `min()`, or `sort(key=...)` position across all services.

> **Why this matters.** D29 was dispositioned FIX because "last-writer-wins and monotonic-max both depend on trusted clocks across disconnected nodes" and no time-synchronization design existed. Document 03 §11 now states flatly: "Where an earlier revision said 'last-writer-wins,' the winner is determined by `(producer, monotonic_seq)` or hybrid logical clock per §5.4, never by `source_time`. A mandated STIG clock step fires at reconnection, so timestamp arbitration would invert exactly when the outbox drains." A type that refuses to be compared is the only version of this rule that survives nine teams and a deadline.

### 4.8 Ordering and deduplication — the exact signature

```python
DedupKey = tuple[str, str, int]     # (producer_slug, producer_node_id, monotonic_seq)

def dedup_key(record: SyncRecord) -> DedupKey:
    return (record.producer_slug, record.producer_node_id, record.monotonic_seq)

def content_hash(record: SyncRecord) -> bytes:
    """SHA-256 over the canonical serialization of the payload. The permitted
    ALTERNATIVE dedup basis per 03 §5.2 ('idempotently on that key or on a
    content hash') for producers that cannot supply a sequence — external
    federation feeds only. Never used for program-built producers."""

def order_and_dedup(
    records: Iterable[SyncRecord],
    *,
    mode: OrderingMode = OrderingMode.CAUSAL_ONLY,
) -> OrderedBatch:
    """Deduplicate on dedup_key(); order:
         - within one (producer_slug, producer_node_id): by monotonic_seq
         - across producers/nodes: by HLC total order (physical_ms, logical, node_id)
       Returns OrderedBatch(records=[...], gaps=[SequenceGap(...)]) where a gap is a
       missing monotonic_seq within a producer-node run — i.e. detected loss.

       source_time and occurred_at are NOT INPUTS to this function. They are not
       read. Passing a record whose SourceTime is compared anywhere in the call
       tree raises ClockDisciplineError.
    """
```

`mode` affects nothing about precedence; it is threaded through only so presentation layers downstream can render a degraded-time indicator without re-deriving epsilon.

---

## 5. Envelope construction

`emit()` builds the full 03 §5.4 envelope so no service hand-rolls one:

```
EventEnvelope {
  event_id, event_type, event_version
  occurred_at            # when the fact became true in the domain
  recorded_at            # when the producer persisted it
  producer               # slug + version
  producer_node          # library addition; see §4.2 and §13
  correlation_id, causation_id
  scope, subject { exactly one scope identifier matching `scope` }
  baseline_epoch?
  classification
  replay
  clock {
    monotonic_seq        # THE ordering key
    hlc { physical, logical, node_id }
    source_time          # SourceTime — display and audit only
    ingest_time          # set by the receiver at acceptance, not by the producer
    sync_quality { time_source, offset_ms, dispersion_ms, seconds_since_sync, step_occurred }
  }
}
```

Validation at `emit()`, all fatal:

- `subject` carries **exactly one** identifier and it matches `scope` (03 §5.4, `[C11]`).
- `event_type` matches `fathom.<slug>.<aggregate>.<verb>`, `snake_case`, slug from 03 §3.1 (`[C26, C27]`).
- Payload validates against the registered schema in `packages/canonical-schemas` — "a producer cannot publish an event whose payload fails registry validation" (03 §5.5).
- `classification` is a well-formed `ClassificationLabel` (03 §7.3), and derived values carry `inherited_from` (§10.4).
- `compaction_key != partition_key` on compacted topics (`[D5]`).
- **`occurred_at` is not usable as a feature timestamp.** `emit()` stamps a `hindsight: bool` marker on aggregates declared hindsight-authored (confirmed anomaly tags, in particular) so feature pipelines cannot silently use it. Document 03 §5.4: "Feature computation must not use `occurred_at` for any value authored with hindsight" `[D22]`.

---

## 6. Consumer-side envelope handling

| Envelope field | Consumer obligation |
|---|---|
| `event_id` | Dedup, via the inbox's `processed_at` predicate only (§3.3) |
| `clock.monotonic_seq` + `producer_node` | Ordering and loss detection (§4.8) |
| `clock.source_time` | Display and audit only. Not orderable (§4.7) |
| `clock.ingest_time` | Stamped by the receiver on acceptance |
| `clock.sync_quality` | Copied into the inbox row and exported to Audit for permanent retention (§10.5) |
| `baseline_epoch` | Epoch fence (§3.5) before any state change |
| `causation_id` | Antecedent resolution (§3.5) |
| `replay` | Idempotent apply, **no operator-visible alert**, side effects suppressed (03 §5.3, `[D30]`) |
| `classification` | Enforce locally; never trust the topic alone (03 §7.3, §12, `[D13]`) |
| `scope`/`subject` | Route to the right aggregate; `installed_item_id` identifies the physical item and `position_id` the location — never interchangeably (03 §3.3, `[C10, D9]`) |

---

## 7. Per-aggregate conflict policy enforcement

### 7.1 The policy table, transcribed from document 03 §11

Declared centrally "so behavior cannot diverge between ships."

**Default rule.** Any aggregate not listed is **enterprise-authoritative and not edge-writable.** Phase 3 enumerates exceptions per sub-application; it does not re-derive defaults `[C20]`.

**No policy below compares wall-clock timestamps across nodes.** Where an earlier revision said "last-writer-wins," the winner is determined by `(producer, monotonic_seq)` or hybrid logical clock per §5.4, never by `source_time`. A mandated STIG clock step fires at reconnection, so timestamp arbitration would invert exactly when the outbox drains `[D29]`.

| Aggregate | Policy | Rationale |
|---|---|---|
| Telemetry samples and batches | Append-only; deduplicated on `(producer, monotonic_seq)` | Immutable observations; duplication is a transport artifact |
| Health indicators | Recomputable; enterprise recomputation supersedes | Derived data |
| Anomaly candidates | **Edge-generatable**; enterprise adds further candidates on reconnect | Afloat review requires a local candidate source `[D18]` |
| Anomaly tags | Append-only; never overwritten or deleted; supersession recorded | Human judgments are evidence |
| Proposals | Append-only; adjudication server-authoritative and claim-gated | Two adjudications is a real conflict |
| **Maintenance action records** | **Edge-authoritative, append-only** | The ship records what it *did*; the server retains authority over what was *authorized*. Separating them is what permits label capture afloat `[D8]` |
| Work orders and authorizations | Server-authoritative; edge submits requests | Maintenance authority does not fork |
| Mission records | Edge-authoritative on creation; enterprise-authoritative thereafter | The ship knows the mission occurred |
| Predictions | Enterprise-authoritative; edge holds a cache with an explicit staleness horizon, presented as degraded | Edge inference is a degraded mode and must display as such |
| — | **Write authority is never bound to liveliness.** A disconnected hull retains authority over its own records | This is where the DDS ownership model is actively wrong for this design: DDS binds OWNERSHIP to LIVELINESS, so a dark ship would *lose* authority over the mission records it alone can produce. The opposite of what is required |
| Requisitions | Server-authoritative; edge queues submissions | External legal effect |
| Configuration baselines | Enterprise-authoritative; edge submits configuration-change proposals and may mint **provisional** installed-item identities | Two divergent views of what is installed is the most damaging available conflict |
| Usage counters | Monotonic merge keyed on `(installed_item_id, counter_epoch)`; `usage_counter.reset` opens a new epoch; authoritative correction permitted with provenance and exempt from monotonicity | Keying on position rather than item would credit a new item with its predecessor's hours. Unqualified max-merge makes one sensor glitch permanent `[D9]` |

> Transcription note: in document 03 the "no wall-clock timestamps" paragraph and the liveliness row are interleaved with the table body. Both are reproduced above with the paragraph lifted above the table so the table parses; no wording is changed. Flagged in §13.

### 7.2 The strategy interface

```python
class PolicyId(StrEnum):
    APPEND_ONLY_DEDUP                        = "append-only-dedup"
    RECOMPUTABLE_SUPERSEDE                   = "recomputable-supersede"
    EDGE_GENERATABLE                         = "edge-generatable"
    APPEND_ONLY_IMMUTABLE                    = "append-only-immutable"
    APPEND_ONLY_SERVER_ADJUDICATED           = "append-only-server-adjudicated"
    EDGE_AUTHORITATIVE_APPEND_ONLY           = "edge-authoritative-append-only"
    SERVER_AUTHORITATIVE_EDGE_SUBMITS        = "server-authoritative-edge-submits"
    EDGE_AUTHORITATIVE_THEN_ENTERPRISE       = "edge-authoritative-then-enterprise"
    ENTERPRISE_AUTHORITATIVE_CACHED_DEGRADED = "enterprise-authoritative-cached-degraded"
    SERVER_AUTHORITATIVE_QUEUED              = "server-authoritative-queued"
    ENTERPRISE_AUTHORITATIVE_PROVISIONAL_EDGE = "enterprise-authoritative-provisional-edge"
    MONOTONIC_MERGE_KEYED                    = "monotonic-merge-keyed"
    ENTERPRISE_AUTHORITATIVE_NOT_EDGE_WRITABLE = "enterprise-authoritative-not-edge-writable"  # DEFAULT


class MergeDecision:
    Apply       : "apply the incoming record as new state"
    Ignore      : "duplicate or subsumed; no state change; reason recorded"
    Supersede   : "apply, and mark prior_record_id superseded (never deleted)"
    Reject      : "the write was not permitted here; return to submitter as a request"
    Quarantine  : "cannot be decided safely; hold, alert, do not drop"
    EmitCorrection : "apply, and emit a correction event carrying provenance"


class ConflictPolicy(ABC):
    aggregate: str
    policy_id: PolicyId
    edge_writable: bool
    divergence_budget: DivergenceBudgetDeclaration

    @abstractmethod
    def merge(self, ctx: MergeContext, local: AggregateState | None,
              incoming: SyncRecord) -> MergeDecision: ...

    # Provided by the base class; overriding either is a lint error.
    @final
    def _precedence(self, a: SyncRecord, b: SyncRecord) -> int:
        """(producer_slug, producer_node_id, monotonic_seq) within a producer-node;
        HLC total order across them. Wall time is not consulted."""

    @final
    def _forbid_liveliness_binding(self) -> None:
        """Authority is a function of the AGGREGATE, never of connectivity.
        There is no is_connected() input to any merge decision. [03 §11 · 08 §3.4]"""
```

Registration is declarative and complete-or-fail:

```python
policies = ConflictPolicyRegistry.declare(
    service="maintenance",
    policies=[
        EdgeAuthoritativeAppendOnly(
            aggregate="maintenance_action_record",
            divergence_budget=DivergenceBudget(max_disconnection=timedelta(days=60)),
        ),
        ServerAuthoritativeEdgeSubmits(aggregate="work_order"),
        ServerAuthoritativeEdgeSubmits(aggregate="work_package"),
        AppendOnlyServerAdjudicated(aggregate="proposal"),
    ],
    # every other aggregate this service owns falls to the §11 default; the
    # registry ENUMERATES them at startup and fails if an owned aggregate is
    # neither declared nor explicitly defaulted. [03 §15.16, C20]
)
```

> **Why complete-or-fail.** Finding **C20**: "The conflict-policy table covers ten aggregates; document 04 defines roughly fifty." A registry that silently defaults leaves forty aggregates with an *implicit* policy nobody reviewed. Startup enumeration forces each of the fifty to be either declared or explicitly written `default=True`, which makes the review possible.

### 7.3 Concrete implementations

| Policy | Merge behavior |
|---|---|
| **`APPEND_ONLY_DEDUP`** — telemetry samples/batches | Insert if `dedup_key` unseen, else `Ignore(duplicate)`. Never update, never delete. Out-of-order arrival is fine: observations are immutable and carry their own window. Dedup on the three-part key, or on `content_hash` for external federation feeds only |
| **`RECOMPUTABLE_SUPERSEDE`** — health indicators | Enterprise recomputation supersedes edge computation for the same `(installed_item_id, indicator, window, definition_version)`. Precedence is `origin == enterprise` **first**, then HLC — origin, not recency, is the discriminator. Edge values are retained and marked superseded so the disagreement remains inspectable. `definition_version` and definition-time are part of the key: recomputation under a *newer definition* is a new value, not a supersession `[D22]` |
| **`EDGE_GENERATABLE`** — anomaly candidates | Both sides may create. Enterprise **adds** on reconnect; it never replaces or prunes the edge set. Near-duplicate candidates over the same `(installed_item_id, window)` are linked as a candidate group with both origins preserved, never merged away. `origin` (`enterprise`\|`edge`, per 03 §6) is mandatory. **Why:** `[D18]` — "a returning submarine's reviews had empty candidate sets and review degraded to the open-ended authoring the design declares unreliable." An enterprise pass that overwrote the edge set would restore that failure |
| **`APPEND_ONLY_IMMUTABLE`** — anomaly tags | Insert only. Never overwrite, never delete. A changed judgment is a **new** tag with `supersedes: <prior_tag_id>`; both are retained with both reviewers and both timestamps. `taxonomy_version` is mandatory on every tag (03 §14) `[D31]`. **Why:** human judgments are evidence, and a training set assembled across an unversioned taxonomy revision "is silently corrupt and undetectably so" |
| **`APPEND_ONLY_SERVER_ADJUDICATED`** — proposals | Edge may create; adjudication is server-only and requires the claim/lease of 03 §7.2 (`POST /proposals/{id}/claim`, then `If-Match` on the claimed ETag). An edge-originated adjudication is `Reject`ed and returned as a request. Re-validation against current configuration at approval time is mandatory `[D16]`. **Why:** "two planners approve the same proposal and two work orders result" |
| **`EDGE_AUTHORITATIVE_APPEND_ONLY`** — maintenance action records | The edge is the authority. The shore **applies** the record; it may not modify, reject, or reorder it. Corrections are new append-only records with provenance and a non-observer flag. **Why:** `[D8]` — a submarine dark six weeks "repairs a pump at sea and cannot record the corrective/preventive determination, findings coding, parts consumed, or failure timing — the four highest-value fields — until weeks later, reconstructed by someone who was not there." This is *the* label stream (03 §6). Note the deliberate split: the ship owns what was **done**; the server owns what was **authorized** |
| **`SERVER_AUTHORITATIVE_EDGE_SUBMITS`** — work orders, authorizations | Edge writes are converted to *requests* at the boundary and stored in a local request queue with local visibility. On reconnect they are submitted to the server API with `Idempotency-Key`. Server response is authoritative, including rejection. The edge never fabricates an authorization. **Why:** "maintenance authority does not fork" |
| **`EDGE_AUTHORITATIVE_THEN_ENTERPRISE`** — mission records | Creation is edge-authoritative (the ship knows the mission occurred and may be the only witness). After the first successful reconciliation the record transitions to enterprise-authoritative; subsequent edge writes become submissions. The transition is recorded on the record itself so authority is never ambiguous mid-flight |
| **`ENTERPRISE_AUTHORITATIVE_CACHED_DEGRADED`** — predictions | Inbox-only at the edge. The cache carries an explicit staleness horizon; **beyond it the value is not shown as a prediction** — it is shown as expired, with the reason. Every edge-served prediction carries a degraded-mode marker the UI must render. The edge never publishes a prediction upstream. **Why:** "edge inference is a degraded mode and must display as such"; and per 03 §7.1 a cached tier-0 population rate rendered like a tier-3 item-conditional distribution misleads the operator `[D19]` |
| **`SERVER_AUTHORITATIVE_QUEUED`** — requisitions | Queued locally, submitted on reconnect with `Idempotency-Key`, never issued from the edge. **Why:** external legal effect. Compare 03 §10's shadow-mode rule — "externally-effective commands intercepted and suppressed: requisition creation and reservation confirmation have real-world effect and must not be double-issued" `[D25]` |
| **`ENTERPRISE_AUTHORITATIVE_PROVISIONAL_EDGE`** — configuration baselines | Enterprise-authoritative. The edge may (a) submit `configuration_change` proposals and (b) mint **provisional** installed-item identities (§8). Nothing else. **Why:** "two divergent views of what is installed is the most damaging available conflict" |
| **`MONOTONIC_MERGE_KEYED`** — usage counters | See §7.4 — the most defect-prone policy in the table |
| **`ENTERPRISE_AUTHORITATIVE_NOT_EDGE_WRITABLE`** — default | Edge writes `Reject`ed at the API boundary with a 423 problem detail. Reads are served from cache with a staleness marker |

### 7.4 `MONOTONIC_MERGE_KEYED` in full, because D9 is three bugs

```python
class MonotonicMergeKeyed(ConflictPolicy):
    policy_id = PolicyId.MONOTONIC_MERGE_KEYED
    KEY = ("installed_item_id", "counter_type", "counter_epoch")

    def merge(self, ctx, local, incoming) -> MergeDecision:
        # 1. KEY ON THE ITEM, NOT THE POSITION.
        #    A new pump in an old position starts at its own hours. Keying on
        #    position credits the new item with its predecessor's age — the
        #    inherited-degradation failure document 04 §2 exists to prevent.
        # 2. EPOCH-SCOPED. usage_counter.reset opens a NEW counter_epoch. Values
        #    never merge across epochs, because a replaced hour meter legitimately
        #    reads lower than the one it replaced.
        # 3. AUTHORITATIVE CORRECTION IS EXEMPT FROM MONOTONICITY.
        #    A correction carrying provenance (authority, reason, evidence ref) may
        #    LOWER a counter. Without this, one sensor glitch pins the counter at a
        #    wrong high value permanently — max-merge is irreversible.
        # 4. Within an epoch, absent a correction: value = max(local, incoming).
        #    max() over the counter VALUE (a domain quantity), never over a clock.
        if incoming.is_authoritative_correction:
            return MergeDecision.EmitCorrection(value=incoming.value,
                                                provenance=incoming.provenance)
        if local is None or incoming.value > local.value:
            return MergeDecision.Apply(value=incoming.value)
        return MergeDecision.Ignore(reason="subsumed by higher value in same epoch")
```

> **Why this matters — all three of D9's bugs.** (a) The edge could not mint a new `InstalledItem` identity because configuration is enterprise-authoritative, "so it accumulates hours against the *replaced* item. Max-merge then either credits the old item with hours it never ran or gives the new pump its predecessor's age." Provisional identity (§8) is what makes item-keying possible afloat. (b) "Max-merge is irreversible, so one sensor glitch permanently pins a counter" — hence the correction exemption. (c) "Real hour meters get replaced and reset, with no representation for a reset" — hence `counter_epoch` and `usage_counter.reset`. Note also that `max()` here is over a *domain quantity*; if you ever find yourself writing `max()` over a timestamp in this class, you have written D29.

---

## 8. Provisional identity

### 8.1 Why it exists

Document 01 §12: "the edge may mint an `installed_item_id` locally, marked provisional, confirmed or superseded by the Registry on reconciliation. Without it, a ship that replaces an item at sea accumulates usage against the item it removed." Document 03 §3.3 states the same and cites `[D9, D8]`. Document 06 §4 fixes the mechanism: "Client-minted UUID with `provisional: true`, confirmed or superseded by the Registry on reconciliation."

A ship replacing a pump at sea cannot mint a *confirmed* identity — configuration is enterprise-authoritative, and the Registry is unreachable. Without a provisional identity the ship has three bad options: attribute the new pump's hours to the removed item (D9's inherited degradation), record nothing (D8's excluded label capture), or invent a local surrogate that 03 §2.4 prohibits outright ("Canonical identity is never re-minted... No sub-application invents a local surrogate and exposes it").

Provisional identity is the fourth option, and it is not a surrogate: it is a **candidate canonical identifier** in the canonical namespace, awaiting adoption.

### 8.2 Minting

```python
class ProvisionalIdentityMinter:
    def mint_installed_item(
        self, uow, *,
        position_id: PositionId,
        niin: str,
        serial_or_lot: str | None,
        installed_at: SourceTime,
        removed_item_id: InstalledItemId | None,   # what came out, if anything
        source_work_reference: str | None,
    ) -> ProvisionalInstalledItem:
        """Returns a uuid4 installed_item_id with provisional=True plus a
        ProvisionalContext recording minting_node_id, mint_monotonic_seq, and the
        physical facts needed for the Registry to adjudicate."""
```

Rules:

- `installed_item_id` is a **uuid4 in the canonical namespace** — the same shape a Registry-minted id takes. This is what permits confirmation-by-adoption in the common case (§8.4).
- **Every event referencing a provisional id carries `identity_provisional: true`** in the envelope's subject block. A consumer must be able to tell without inference.
- `ProvisionalContext` is retained forever, including after resolution. It is the audit record of why this id exists.
- Only the aggregates whose policy is `ENTERPRISE_AUTHORITATIVE_PROVISIONAL_EDGE` may mint, and only for `installed_item_id`. **No other identifier is ever minted at the edge** — not `asset_id`, not `system_id`, not `position_id`, not `baseline_id`.

### 8.3 The reconciliation protocol

```
EDGE                                    SHORE (Registry)
────                                    ────────────────
1. mint uuid4, provisional=true
2. record usage, maintenance actions,
   anomaly tags against it
   (all events: identity_provisional=true)
3. reconnect
4. coordinator submits, BEFORE draining
   any aggregate that references it:
     POST /api/v1/registry/installed-items
     Idempotency-Key: <provisional_id>
     { installed_item_id: <provisional_id>,
       provisional: true,
       position_id, niin, serial_or_lot,
       installed_at, removed_item_id,
       provisional_context: {...} }
                                    ──▶  5. adjudicate against current baseline
                                    ◀──  6a. CONFIRMED:  adopts the provisional UUID
                                              as the permanent installed_item_id.
                                              Publishes installed_item.installed.
                                         6b. SUPERSEDED: an enterprise identity
                                              already covers this physical item.
                                              Publishes installed_item.identity_resolved
                                              { provisional_id, canonical_id,
                                                resolution: superseded, evidence }
                                         6c. REJECTED: physically impossible (e.g.
                                              position not in baseline). Quarantined
                                              for human adjudication. NEVER discarded.
7. drain the remaining aggregates
```

**Identity resolution precedes aggregate drain.** The coordinator orders reconciliation so identity is settled before the events that depend on it. It is a topological order, not a timestamp order.

### 8.4 What happens to events already published under a provisional id

**`DECISION` — published events are NEVER rewritten. The Registry publishes a mapping event, and consumers resolve at read time.**

Justification, three independent reasons:

1. **Records are signed (AU-10, 08 §3.5).** Rewriting the subject invalidates the signature, so a rewrite is indistinguishable from tampering. The non-repudiation claim collapses.
2. **Several aggregates are append-only by contract** (03 §11: anomaly tags "never overwritten or deleted"; maintenance action records append-only). A rewrite violates the policy table directly.
3. **Events may already have been consumed** by any of nine read models plus Audit. A rewrite would require a coordinated global mutation across every store — the exact unrecoverability D15 identifies as an accreditation blocker.

The mechanism instead:

- Registry publishes **`installed_item.identity_resolved`** carrying `{provisional_id, canonical_id, resolution: confirmed|superseded, evidence, baseline_epoch}` on `fathom.registry.installed_item.v1`. Consumers of `installed_item.*` already exist per 03 §6 (`pdm`, `telemetry`, `supply`, `failure-intel`, `design-advisory`).
- The library ships **`IdentityAliasResolver`**, and every read model that keys on `installed_item_id` uses it:

```python
class IdentityAliasResolver:
    """Alias table maintained from installed_item.identity_resolved.
       resolve(id) -> canonical id (identity when confirmed-by-adoption).
       Aliases are retained PERMANENTLY; they are how a two-year-old event's
       subject is still interpretable."""
    def resolve(self, provisional_or_canonical: InstalledItemId) -> InstalledItemId: ...
    def aliases_of(self, canonical: InstalledItemId) -> set[InstalledItemId]: ...
```

- A read model **may** materialize the canonical id into its own rows as a background canonicalization pass, for query efficiency. It may not delete the alias record, and it must remain able to answer a query posed with the provisional id — a maintainer who wrote the provisional id on a form six weeks ago must still find the item.
- **Confirmation-by-adoption is the designed common case.** Where the Registry has no pre-existing identity for the physical item — a ship replacing a pump at sea with no shore-side record — it adopts the ship's UUID. Then `provisional_id == canonical_id`, no alias is needed, and the resolver is a no-op. Supersession is reserved for genuine collisions (the shore already recorded the replacement from another source, e.g. a 4790/CK submitted through a separate channel).

> **Why this matters.** D9 plus D8 together: without provisional identity the ship either mis-attributes usage (corrupting the RUL model's most important covariate) or records nothing (removing labels from "exactly the operating mode where the most informative failures occur"). And the *rewrite* temptation is strong, because rewriting looks tidier — which is precisely how a signed append-only store becomes an unverifiable one.

---

## 9. The divergence budget and the edge reconciliation coordinator

### 9.1 The divergence budget mechanism

Document 03 §11: "Each edge deployment declares a maximum tolerable disconnection per aggregate, beyond which the operator interface degrades to explicitly read-only for that aggregate rather than accumulating unbounded unreconciled state."

```python
@dataclass(frozen=True)
class DivergenceBudgetDeclaration:
    aggregate: str
    max_disconnection: timedelta          # measured on a MONOTONIC clock
    max_unreconciled_records: int | None = None
    max_unreconciled_bytes: int | None = None
    on_breach: BreachAction = BreachAction.EXPLICIT_READ_ONLY
    # EXPLICIT_READ_ONLY is the only permitted value for every aggregate except one.
    # ALERT_AND_DEGRADE is permitted ONLY for the audit store `[amendment 11-3]`:
    # refusing audit writes stops the accountability record for every service on
    # the hull, and no document 08 control requires that a breached audit budget
    # go read-only rather than degrade with an alert. No other aggregate may set
    # this value — enforced at declaration time, not left to service discretion.


class DivergenceBudgetTracker:
    def declare(self, *decls: DivergenceBudgetDeclaration) -> None: ...
    def status(self, aggregate: str) -> DivergenceStatus:
        """DivergenceStatus(disconnected_for, unreconciled_records,
        unreconciled_bytes, fraction_of_budget, breached: bool)"""
    def gate(self, aggregate: str) -> WriteGate:
        """The API layer calls gate(aggregate).require_writable() on every
        state-changing operation for that aggregate."""
```

Breach behavior — all four required, none optional:

1. **Writes to that aggregate are refused** with RFC 9457 problem details, `423 Locked`, `type: https://fathom.navy.mil/problems/divergence-budget-exceeded`, and a `detail` naming the aggregate and the elapsed disconnection. `detail` is never used for control flow (03 §4); the `type` is.
2. **The operator interface degrades to explicitly read-only for that aggregate** — a persistent, visible banner naming the aggregate and the reason. Never a silent failure, never a generic error, never a disabled button with no explanation.
3. **Other aggregates are unaffected.** The budget is per aggregate. A telemetry breach must not stop maintenance action recording — that would reintroduce D8 by a different route.
4. **Nothing already recorded is discarded.** The unreconciled state is preserved in full and reconciles when the link returns. The budget bounds *accumulation of new* state, not the survival of existing state.

Surfacing:

| Channel | Signal |
|---|---|
| `/metrics` | `fathom_sync_divergence_seconds{service,aggregate}`, `fathom_sync_divergence_budget_seconds{...}`, `fathom_sync_divergence_breached{...}` (0/1), `fathom_sync_unreconciled_records{...}` |
| `/readyz` | Degraded (not failed — the service is functioning in a defined mode), enumerating breached aggregates. 03 §4 requires read-model-staleness checks on `/readyz` |
| Events | `sync.divergence_budget_breached` / `...cleared` on `fathom.sync.divergence.v1`, so shore sees the hull's history after reconnect |
| Audit | Every breach and clearance, with the measured duration |
| Operator UI | Per-aggregate read-only banner |

**Demonstration values.** Document 06 §4 scripts a six-week disconnect for one SSN, and notes "the divergence budget is a declared value per aggregate, so the period is configuration rather than design." Each service sets its own in its Helm chart. The one binding constraint: **the maintenance-action-record and anomaly-tag budgets must exceed the planned patrol length**, or the demonstration's own scenario breaches the budget it is meant to satisfy — the ship goes read-only for maintenance recording halfway through the patrol, and D8 returns wearing a compliance badge.

### 9.2 The coordinator — the one legitimately inert component

Per 01 §5 and §12, and the **C21** correction of §1.3: the edge reconciliation coordinator is inert in the cloud-only demonstration; **the outbox relay is not.**

| | Outbox relay | Edge reconciliation coordinator |
|---|---|---|
| Where it runs | In-process in every service, every deployment | A distinct deployable, edge and shore ends |
| Cloud-only demo | **Active.** Without it no event reaches the broker (C21) | **Inert / absent.** Correct and intended |
| Talks to | Redpanda | The ship-to-shore link |
| Feature flag | None. Not disableable | `SYNC_EDGE_COORDINATOR_ENABLED` |

For the demonstration's one SSN (document 06 §4: "a physically separate deployment rather than a simulated queue") the coordinator is active on that hull and its shore counterpart, and nowhere else.

### 9.3 Coordinator responsibilities when active

**a. Outbox drain over the ship-to-shore link.** Per 08 §3.4's recommended split: "a durable transactional outbox drained over authenticated, idempotent HTTPS or gRPC with resume-from-offset for ship-to-shore." Not DDS (§11).

- Transport: mutually authenticated TLS (SC-8/SC-8(1)); idempotent submission keyed on `event_id`; resume-from-offset on the shore-returned high-water mark per `(producer_slug, producer_node_id)`.
- **Resume-from-offset is a per-producer-node sequence position, not a byte offset and not a timestamp.** The shore returns `{producer_node: last_contiguous_seq}`; the ship resumes at `+1`. Because the sequence is gap-free (§4.3), a gap is unambiguous loss and is re-requested rather than assumed benign.
- **Acknowledgement gates pruning** (`acked_by_shore_at`, §2.6) `[D28]`.
- **Priority classes, and this is a correctness matter, not a nicety.** Six weeks of burst telemetry (document 06 §7: subsurface channels "transmitted in burst on reconnect") would otherwise saturate a narrow link and starve the label stream for hours or days.

  | Class | Contents | Order |
  |---|---|---|
  | 0-R | Remediation commands and purge receipts | **First, ahead of class 0** `[amendment 11-2]` — a spillage remediation outranks a data-quality concern, and a purge receipt awaiting drain is exactly the kind of unreconciled state the divergence budget (§9.1) exists to bound |
  | 0 | Provisional identity submissions | Next, always (§8.3) |
  | 1 | Maintenance action records, anomaly tags, mission records | Next — the label stream `[D8, D18]` |
  | 2 | Requisition and work-order request queues | Next — operationally time-critical |
  | 3 | Usage counters, health indicators, anomaly candidates | Next |
  | 4 | Bulk telemetry (by `payload_ref`, resumable object transfer) | Last, and interruptible |

  Ordering *within* a `(producer_node, partition_key)` is never violated by prioritization: classes partition by aggregate, and one aggregate never spans two classes.
- **Never uses `X-Backfill` for edge drain.** Edge records are live facts arriving late, not replay. They must fire their normal side effects ashore. The distinction: `replay: true` means "this event is a re-emission of history"; a six-week-old maintenance action from a submarine is a first emission of a real fact, and 03 §5.4 already accounts for it — "`occurred_at` and `recorded_at` are distinct because they diverge materially here: a mission anomaly occurred at sea and was recorded when the ship reconnected."

**b. Inbox apply on the shore side.** Standard inbox semantics (§3) — record-and-apply atomically, epoch fencing, `processed_at` suppression. The shore ingress additionally: verifies the record signature before admitting (failure → quarantine and audit, never silent drop); stamps `clock.ingest_time`; checks the classification label against the target topic's declared level (03 §5.1, `[D13]`); and records `sync_quality` for permanent retention.

**c. Conflict resolution per §7.** The coordinator dispatches each record to its aggregate's `ConflictPolicy.merge()`. It has no merge logic of its own, and — critically — **no `is_connected()` input to any decision** (§11, the DDS anti-pattern).

**d. Divergence budget tracking per §9.1**, on both ends: the ship tracks its own accumulation; the shore tracks per-hull last-reconciliation so a hull overdue for contact is visible ashore.

**e. Shore-to-ship direction.** Cached predictions with staleness horizons, configuration baseline updates (which advance `baseline_epoch` and therefore fence edge computations), reference data and taxonomy versions, model artifacts, and enterprise-added anomaly candidates (03 §11: enterprise "adds further candidates on reconnect").

---

## 10. Security properties — library-provided, not per-service discipline

Every property below is **provided by the library by default**. None is something a service team must remember to add. Control citations from 08 §3.5.

### 10.1 Encryption at rest — SC-28, SC-28(1)

"**Encrypt the outbox at rest on the ship** — it is a persistent CUI or NSI store" (08 §3.5). The outbox holds domain payloads indefinitely on a hull that may be boarded, salvaged, or lost.

- Payloads are stored as `payload_ciphertext` under a **per-classification KEK** (03 §13.1: "Envelope-level encryption with per-classification keys"), with mission-owner sole key control (08 §3.5).
- `emit()` encrypts. There is no plaintext-payload code path. A service cannot write an unencrypted payload because `emit()` is the only way in (§2.3).
- **Crypto-shredding a KEK is the purge mechanism** where physical deletion is impossible (03 §13.1, `[D15]`). The library exposes `purge_by_selector(...)` covering the outbox, the inbox, the quarantine tables, and the object-store payload references — four of the stores D15 enumerates, so a spillage remediation does not have to reverse-engineer them. `purge_by_selector(...)` accepts a coordinator-issued `remediation_id` — the identifier document 03 §15 obligation 17's `POST /{slug}/remediations` operation mints — and returns a receipt **signed by this library**, per §10.2's key material, stating which of the four stores it touched and by which mechanism `[amendment 11-4]`.
- `payload_ref` objects are encrypted with the same KEK class. A reference is not an exemption.

### 10.2 Signed records — AU-10

"**AU-10** sign outbox records at the ship" (08 §3.5).

- `emit()` signs, at insert, over the canonical serialization of: `event_id, event_type, event_version, producer_slug, producer_version, producer_node_id, monotonic_seq, hlc, scope, subject, baseline_epoch, classification, payload_sha256, source_time, sync_quality, replay`. Key id recorded in `signing_key_id`. **The signed set is exactly this list — the signature covers `payload_sha256`, never the payload itself, and excludes `wrapped_dek` and all key-wrapping metadata** `[amendment 11-5]`. Both exclusions are load-bearing, not oversights: a rewrap (§10.1) changes `wrapped_dek` without changing the fact being attested, and a purge shreds the key the payload was encrypted under while the hash and signature remain valid evidence that the (now unrecoverable) content once existed with that provenance. An implementer who "completes" the field set by including the payload or the wrap metadata breaks purge and reclassification simultaneously — every rewrap or purge would invalidate every affected record's signature.
- The relay verifies before publishing (detects at-rest tampering or corruption before it propagates).
- The shore ingress verifies before admitting. **Verification failure quarantines and audits; it never silently drops** — a dropped record is a lost maintenance action, and a lost maintenance action is a lost label.
- Signature covers `sync_quality`, so a clock attestation cannot be edited after the fact. This is what makes "skew is indistinguishable from tampering to an assessor" (08 §3.3) a solved problem rather than a finding.

### 10.3 Transaction recovery — CP-10(2)

"**CP-10(2) Transaction Recovery** — *'Implement transaction recovery for systems that are transaction-based'* — is in **both** the Moderate and High baselines, and it is the control the outbox directly satisfies" (08 §3.5).

The library ships the control-mapping evidence — the fault-injection suite of §10 is CP-10(2) assessment evidence, not merely a test suite. Say so in the SSP.

### 10.4 Classification and provenance binding — SC-16

"**SC-16** bind classification and provenance to synced records" (08 §3.5).

- `classification` is mandatory on `emit()` and is inside the signature. It cannot be added, changed, or stripped in transit.
- **Derived values carry the union of their inputs' labels** in `inherited_from` (03 §7.3, `[D13]`). The library provides `ClassificationLabel.union(*inputs)` and refuses to emit a derived event whose `inherited_from` is empty when the service declares the aggregate derived. This is obligation 03 §15.4 and §15.9 made mechanical.
- **The shore ingress enforces the target topic's declared level** — one classification per topic (03 §5.1), cross-level flow only through an accredited guard. Consumer-side enforcement alone "yields either system-high operation — in which labels are decorative — or a leak" (03 §12).
- For the demonstration a single unclassified level is used, stated explicitly rather than implied to be multi-level capable (03 §12, document 06 §5). The enforcement code path is still exercised, against one level.

### 10.5 Audit and clock-attestation retention — AU-4(1), AU-6(3), AU-9(3), AU-12(1)

- **`sync_quality` is retained permanently** (03 §5.4). It is exported to Audit before its outbox row becomes prunable (§2.6). "It converts 'our timestamps drifted' from an audit finding into a bounded, documented condition, and it is the only way to re-derive true ordering after the fact. Without it that information is gone."
- **The inbox exports a dissemination record on every apply** — `(source_event_id, holder_slug, holder_node, holder_store, applied_at, materialized)` — to Audit's dissemination ledger (`32-audit.md` §4.6), alongside the `sync_quality` export above. **`ChangedSinceRebuilder` (§2.8) does the same for every rebuild it performs** `[amendment 11-1]`. This is the half of the ledger this library owns: Audit's coordinator can only know a store holds a copy if every path that materializes one — a live apply or a rebuild from `changed_since` — reports it. A rebuild that skips this export is exactly the gap §4.6 describes as "the rebuild path is the one that resurrects purged content" — a purge can shred the key everywhere the ledger knows about and still leave a live copy in a store that rebuilt without reporting.
- **1 ms granularity** on `recorded_at` and `ingest_time` (AU-12(1), the stated correlation parameter — 08 §3.5, and the Zero Trust Overlays' audit time-stamp granularity per 03 §5.4).
- **AU-4(1)** transfer to alternate storage: the edge outbox is itself the alternate store during disconnection; the drain is the transfer.
- **AU-6(3)** correlate ship and shore repositories: `(producer_node_id, monotonic_seq)` plus `correlation_id` is the correlation key. Wall time is not, and cannot be, that key.
- **AU-9(3)** protection: signatures per §10.2.

---

## 11. Testing — the harness this library ships

Every service consumes this harness; nobody writes their own. Fixtures live at `packages/contracts/conformance/_shared/sync/`.

### 11.1 Fault injection — the core property

This is what makes 03 §10's substitution conformance suite possible: "**Fault-injection tests** — interruption mid-operation, asserting no state change without its event," and it is the observable property that replaces the unconformable outbox obligation for a substitute `[D24]`.

```python
class InjectionPoint(StrEnum):
    BEFORE_DOMAIN_WRITE              = "before-domain-write"
    AFTER_DOMAIN_WRITE_BEFORE_EMIT   = "after-domain-write-before-emit"
    AFTER_EMIT_BEFORE_COMMIT         = "after-emit-before-commit"
    AFTER_COMMIT_BEFORE_PUBLISH      = "after-commit-before-publish"
    AFTER_PUBLISH_BEFORE_MARK        = "after-publish-before-mark"
    AFTER_INBOX_INSERT_BEFORE_APPLY  = "after-inbox-insert-before-apply"   # THE D2 POINT
    AFTER_APPLY_BEFORE_MARK_PROCESSED = "after-apply-before-mark-processed"
    AFTER_MARK_BEFORE_OFFSET_COMMIT  = "after-mark-before-offset-commit"
    MID_RELAY_BATCH                  = "mid-relay-batch"
    MID_COORDINATOR_DRAIN            = "mid-coordinator-drain"


@parametrize_over_all_injection_points
async def test_no_state_change_without_its_event(service, command, injection_point):
    """For EVERY state-changing operation × EVERY injection point:
       crash, recover, converge, then assert
             (domain state changed)  <=>  (an outbox row exists for it)
       and that the published event set is a superset of nothing missing and
       contains no event for a state change that did not happen."""
```

The **`AFTER_INBOX_INSERT_BEFORE_APPLY`** case is mandatory in every consumer's suite and is D2's regression test:

```python
async def test_d2_crash_between_inbox_record_and_apply_does_not_suppress(consumer):
    """Crash after the inbox row is written and before the state change.
    On redelivery the event MUST be applied. If it is suppressed, the
    implementation has reverted to record-then-process. Canonical instance:
    configuration.baseline_changed must still invalidate predictions."""
```

### 11.2 Clock-skew simulation

```python
class SkewableClock:
    def step_backward(self, delta: timedelta) -> None:
        """Simulate the STIG-mandated makestep 1 -1 backward step. Moves the
        REALTIME source only; the MONOTONIC source is untouched, which is exactly
        what the kernel does."""
    def step_forward(self, delta: timedelta) -> None: ...
    def freeze(self) -> None: ...
```

Required tests, each named for the finding it guards:

| Test | Assertion |
|---|---|
| `test_d29_backward_step_does_not_reorder` | Write A, `step_backward(1 h)`, write B. Assert `order_and_dedup` yields A before B; **and assert that ordering by `source_time` would yield B before A** — the test must prove the inversion exists, or it is not testing anything |
| `test_d29_step_occurred_latched_and_reported` | After a backward step, the next emitted record carries `step_occurred=true`; the latch survives a process restart; the latch clears only after that record is durable |
| `test_d29_hlc_never_regresses_across_step` | HLC physical component is non-decreasing across a backward step, and across a restart |
| `test_d29_backoff_unaffected_by_step` | A retry loop mid-backoff neither storms nor hangs when a step lands. Monotonic deadlines only |
| `test_d29_lease_not_extended_by_step` | A relay shard lease does not expire early or late across a step; no two workers ever hold one shard |
| `test_d29_dispersion_grows_while_disconnected` | `dispersion_ms` increases monotonically with `seconds_since_sync`, and `CAUSAL_ONLY` engages once epsilon exceeds the inter-write interval |
| `test_d29_source_time_comparison_raises` | Any attempt to compare two `SourceTime` values raises `ClockDisciplineError` |

### 11.3 Distributed-correctness tests

| Test | Guards |
|---|---|
| `test_d3_superseded_baseline_result_refused` | A computation started under epoch N cannot publish after N+1 lands |
| `test_d4_event_ahead_of_epoch_blocks_then_applies` | An event with `baseline_epoch` ahead of the read model blocks, resolves via `causation_id` or `changed_since`, then applies — in order |
| `test_d5_compaction_key_differs_from_partition_key` | Every compacted topic; enforced by CHECK constraint *and* test |
| `test_d5_read_model_rebuild_from_changed_since_only` | A read model rebuilds with the event bus unavailable |
| `test_d30_replay_fires_no_side_effects` | `replay: true` produces no notification, no work candidate, no requisition, no operator alert |
| `test_d28_outbox_pruning_respects_shore_ack` | No row is pruned before its shore acknowledgement; backlog metrics and `/readyz` degrade before disk exhaustion |
| `test_partition_ordering_preserved_under_relay_concurrency` | N relay workers, one partition key, asserted publish order |
| `test_gap_free_sequence_detects_loss` | A deliberately dropped record produces a `SequenceGap` and a re-request |
| `test_at_least_once_duplicates_are_idempotent` | Every event delivered twice; state identical |

### 11.4 Edge and policy tests

| Test | Guards |
|---|---|
| `test_d8_edge_maintenance_action_survives_six_week_disconnect` | Record afloat, reconcile, assert shore applied it unmodified with all fields |
| `test_d9_usage_counter_keyed_on_item_not_position` | Replace an item at a position; assert the new item does not inherit hours |
| `test_d9_authoritative_correction_can_lower_counter` | A glitch-inflated counter is correctable with provenance |
| `test_d9_reset_opens_new_epoch` | Values never merge across `counter_epoch` |
| `test_d18_enterprise_adds_candidates_never_replaces` | Edge candidate set intact after enterprise reconciliation |
| `test_provisional_identity_confirmed_by_adoption` | No alias needed; `provisional_id == canonical_id` |
| `test_provisional_identity_superseded_publishes_mapping` | Mapping event published; **no event rewritten**; signatures still verify; a query by provisional id still resolves |
| `test_divergence_budget_breach_is_explicit_read_only` | Writes 423 with the right problem type; other aggregates unaffected; nothing discarded |
| `test_write_authority_independent_of_connectivity` | The same merge decision with the link up and down. No `is_connected()` anywhere in the call tree (asserted by call-graph inspection) |
| `test_c21_relay_not_gated_by_coordinator_flag` | §1.3 |

### 11.5 Static gates (CI, in the `lint` stage per document 09)

1. No `emit()` outside an open transaction; none after commit.
2. No Kafka producer call in any module but the relay.
3. No `INSERT INTO outbox` outside the library.
4. No comparison, `max`, `min`, or `sort` key over `source_time`, `occurred_at`, or `recorded_at`.
5. No `time.time()`, `datetime.now()`, or wall-clock arithmetic in any deadline, timeout, backoff, TTL, or lease.
6. No `SELECT ... FROM inbox WHERE event_id = ?` that does not constrain `processed_at`.
7. The §3.2 comment template is present in every inbox integration.
8. Every owned aggregate appears in the conflict policy registry, declared or explicitly defaulted.
9. No `is_connected` / `is_live` / liveliness predicate reachable from any `ConflictPolicy.merge()`.

---

## 12. Explicit DO-NOT list

| # | Do not | Because |
|---|---|---|
| 1 | **Record `event_id` before processing.** Do not "optimize" the inbox into a dedup-then-handle sequence | `[D2]` — a crash between the two permanently suppresses the event, with no error. Applied to `configuration.baseline_changed`, predictions for a replaced item are never invalidated: the failure document 04 calls the most likely to destroy operator trust, introduced by the inbox rule itself |
| 2 | **Compare wall-clock timestamps to decide precedence** — `source_time`, `occurred_at`, `recorded_at`, `computed_at`, `now()`. Not for last-writer-wins, not as a tie-break, not "as a fallback when sequences match" | `[D29]`, 03 §5.4/§11 — Ubuntu STIG V-260520 mandates `makestep 1 -1`, and the step fires exactly when a reconnected node drains its outbox. Two writes from one process can carry inverted timestamps. Timestamp arbitration inverts precisely when it matters most |
| 3 | **Use a wall clock for durations, timeouts, backoff, TTLs, or lease expiry** | 03 §5.4 — "a wall-clock backoff loop storms or hangs the instant a step lands." A wall-clock lease means two relay workers on one shard, reordering one asset's stream, at reconnection |
| 4 | **Monotonic-max on the wrong key.** Do not key usage counters on `position_id`; do not merge across `counter_epoch`; do not make max-merge unconditional | `[D9]` — position-keying credits a new pump with its predecessor's hours (the inherited-degradation failure); cross-epoch merge breaks on a replaced hour meter; unconditional max means one sensor glitch pins a counter permanently, irreversibly |
| 5 | **Bind write authority to liveliness.** No `is_connected()`, no lease-based ownership, no "the shore takes over when the ship is unreachable" | 08 §3.4, 03 §11 — "DDS binds OWNERSHIP to LIVELINESS, so a dark ship would *lose* authority over the mission records it alone can produce. The opposite of what is required." **Do not copy that binding.** Authority is a function of the aggregate, forever |
| 6 | **Use DDS/RTPS as the ship-to-shore wire** | 08 §3.4 — RTPS discovery is BEST_EFFORT under a `leaseDuration` after which participant resources "can be freed"; RELIABLE is footnoted "subject to timeouts that indicate loss of communication"; multicast is not routed over satellite. After an outage exceeding the lease the reliable match tears down. Also: `DURABILITY_SERVICE history_depth` defaults to **1**, and `DESTINATION_ORDER BY_SOURCE_TIMESTAMP` "converges deterministically *on the wrong value*" under skew. DDS intra-ship is fine; ship-to-shore is a durable outbox over authenticated idempotent HTTPS/gRPC |
| 7 | **Commit a state change and publish afterwards** | 03 §5.2 — the exact failure the outbox exists to eliminate |
| 8 | **Put the outbox in a separate or shared database** | 03 §15.13, `[D33]` — there is no atomic two-database commit, so this silently discards the entire guarantee |
| 9 | **Write to another service's database, including from a batch job** | `[D10, C7]` — bypasses the outbox and principle 03 §2.1. Batch results enter through the bulk, idempotent, fenced HTTP operation |
| 10 | **Replay history through the live event bus** | `[D30]` — re-fires notifications, work candidates, and requisitions. Real-world effect from a maintenance action |
| 11 | **Rebuild a read model from the event bus** | `[D5]` — retention is 7/30 days by design; "the event bus is not a rebuild source." Use `changed_since` |
| 12 | **Set the compaction key equal to the partition key** | `[D5]` — collapses a hull's entire prediction history to one record |
| 13 | **Rewrite events published under a provisional identity** | §8.4 — breaks AU-10 signatures, violates append-only policies, and requires a coordinated global mutation across every store (`[D15]`) |
| 14 | **Mint any identifier other than `installed_item_id` at the edge** | 03 §2.4 — "canonical identity is never re-minted... no sub-application invents a local surrogate" |
| 15 | **Discard unreconciled state when a divergence budget is breached** | 03 §11 — the budget bounds accumulation of *new* state; it never authorizes destroying recorded facts |
| 16 | **Let a divergence breach fail silently, or take the whole service read-only** | 03 §11 — degradation is per aggregate and **explicit**. A service-wide read-only mode would stop maintenance action recording and reintroduce `[D8]` |
| 17 | **Skip the outbox because the service has no edge profile** | 03 §15.11 — "without exception, including sub-applications with no current edge profile." Retrofitting is a rewrite (01 §12) |
| 18 | **Gate the relay on the edge coordinator's feature flag, or make it separately schedulable** | `[C21]` — "if outbox drain is inert, no event reaches the broker" |
| 19 | **Fabricate a `sync_quality` value when the sampler has no reading** | 03 §5.4 — "a time service that declares itself untrusted is far safer than one confidently serving wrong time." Report `unsynced` and infinite dispersion |
| 20 | **Prune `sync_quality`** | 03 §5.4 — retained permanently; "it is the only way to re-derive true ordering after the fact. Without it that information is gone," and non-repudiation claims collapse if the time is contestable |
| 21 | **Drop a record that fails signature verification** | §10.2 — quarantine and audit. A dropped record is a lost label, and silent loss is indistinguishable from an attack |
| 22 | **Use `occurred_at` as a feature timestamp for hindsight-authored values** | `[D22]` — a confirmed anomaly tag carries the mission's `occurred_at` but was authored with hindsight. Using it leaks the future into training data |

---

## 13. Open questions for the orchestrating process

Recorded here rather than resolved locally, because each affects a document this one is downstream of.

1. **`producer_node` is missing from the document 03 §5.4 envelope.** §5.4 keys dedup on `(producer, monotonic_seq)` where `producer` is "slug plus version," but an edge and an enterprise instance of the same slug each mint their own sequence, so the key collides and one event is silently dropped. This library uses `(producer_slug, producer_node_id, monotonic_seq)` and adds `producer_node` to the envelope (§4.2). Document 03 should adopt it explicitly; `clock.hlc.node_id` carrying it implicitly is too easy to miss.
2. **Document 03 §11's table is structurally malformed.** The header row is followed by the "no wall-clock timestamps" paragraph and then the body rows, and one row has `—` as its aggregate (the liveliness rule). Transcribed faithfully in §7.1 with the paragraph lifted above the table; document 03 should be repaired so the table renders.
3. **Stale cross-references in document 03.** §2.6 cites "(§11)" for program implementation standards (they are in §15); §2.8 cites "(§13)" for untrusted content (§9); §2.9 cites "(§14)" for remediation (§13); §7.3 cites "the provenance machinery that §11 requires" (§15.9). Sections appear to have been renumbered without updating the references.
4. **Empty fenced code block in document 03 §7.3**, immediately after `ClassificationLabel`. Possibly a dropped example.
5. **ORM not named in any architecture document.** The stack is Python 3.12/FastAPI/PostgreSQL (01 §14) but no ORM is selected. §2.3's `UnitOfWork` port is ORM-agnostic and its reference adapter assumes a session/`begin()` idiom; document 09 must name the ORM and the migration tool.
6. **Library location convention.** §1.4 places the library at `platform/sync/lib/` per 01 §5's ownership statement, but the monorepo layout (01 §11) puts shared libraries under `packages/`. Document 09 should settle it; the import path `fathom_sync` is unaffected either way.
7. **Divergence budget values are unset.** Document 03 §11 defers them to Phase 3; document 06 §4 makes the period configuration. Each service must set them, and the maintenance-action-record and anomaly-tag budgets must exceed the demonstration's scripted six-week patrol (§9.1) or the scenario breaches its own budget.
8. **Relay shard count is a per-service capacity decision** (§2.5) with a drain-to-empty migration path. Values belong in each service's build document; the default is 8.
9. **D28's telemetry storage question is only half closed.** §2.6 gives the pruning rule and moves payloads out of line, but the *absolute* edge storage envelope for a six-week subsurface burst (document 06 §7: 150 channels at 1/minute) needs a number in the capacity model before hull provisioning.
10. **`sync_quality` retention has no declared destination store cost.** §10.5 exports it to Audit permanently; Audit's build document should confirm it accepts a per-event attestation record at full event volume.

---

## 14. Definition of Done

The shared Definition of Done template in [09 — Monorepo & Conventions](09-monorepo-and-conventions.md) applies in full. This library adds the following, and a consuming service is not done until all of them hold:

**For the library itself**

1. All static gates of §11.5 implemented and enforced in CI.
2. Full fault-injection matrix (§11.1) green: every state-changing operation × every injection point.
3. All clock-skew tests of §11.2 green, including `test_d29_source_time_comparison_raises` and the inversion assertion in `test_d29_backward_step_does_not_reorder`.
4. All distributed-correctness (§11.3) and edge/policy (§11.4) tests green.
5. `test_c21_relay_not_gated_by_coordinator_flag` green.
6. Control-mapping evidence produced for CP-10(2), AU-4(1), AU-6(3), AU-9(3), AU-10, AU-12(1), SC-8/SC-8(1), SC-16, SC-28/SC-28(1), and referenced from the SSP.
7. Twelve conflict policies plus the default implemented, each with the tests of §11.4.
8. Reference test vectors published at `packages/contracts/conformance/_shared/sync/`.

**For each consuming service**

9. Outbox table created in the service's own database, with both CHECK constraints (§2.2).
10. Every state change emits through `outbox.emit()` in the same transaction. Zero direct publishes.
11. Inbox implemented with the §3.2 comment template present verbatim, and the `processed_at`-constrained suppression predicate.
12. Epoch fence active on every consumer of an epoch-carrying event; `BaselineFencedComputation` wrapping every configuration-dependent computation.
13. Conflict policies declared for **every** owned aggregate, or explicitly defaulted, with the registry's startup enumeration passing.
14. Divergence budgets declared for every edge-writable aggregate, with the write gate wired into the API layer and the read-only banner in the UI.
15. Read-model lag on `/readyz` and `/metrics`; `require_fresh()` called by every freshness-dependent computation (03 §15.14).
16. `changed_since` snapshot reads exposed over every aggregate a declared consumer projects (03 §15.5), and a rebuild test that passes with the event bus down.
17. Outbox retention policy declared, with pruning tested and backlog alerting wired.
18. The service's conformance suite includes the fault-injection driver, so 03 §10's substitution protocol is satisfiable for it.
