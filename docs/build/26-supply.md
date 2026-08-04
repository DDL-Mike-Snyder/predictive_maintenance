# Build 26 — Supply Chain & Inventory (`supply`)

| | |
|---|---|
| **Status** | Build specification. Prescriptive — an implementer follows it rather than interpreting it |
| **Slug** | `supply` · base path `/api/v1/supply/` · directory `services/supply/` · package `fathom_supply` |
| **Purpose** | Specify the Supply Chain & Inventory sub-application: stock and allowance position, the documentary lifecycle of materiel in motion, the **atomic multi-NIIN reservation set** that closes finding D6, the SMR-driven demand model, and predicted demand as a first-class published output |
| **Why this document is the reference case** | Document 03 §10 names Supply the **primary substitution candidate** and document 04 §7 makes "designed for substitution from the outset" its first key decision. Document 04 §7 further recommends that the demonstration exercise the **shadow-mode step** of the migration sequence against a mock partner adapter. If this document does not produce a required surface a partner could actually implement and pass conformance against, the platform's central modularity claim is untested rhetoric |
| **Findings closed here** | **D6** (no atomic reservation, no consistent snapshot, lead time absent from every operation) · **D24** (no partner can pass the conformance suite; the required Supply surface omitted lead time, condition codes, and interchangeability) · **D10/C7** (batch results enter through an API, never SQL) |
| **Binding inputs** | [03 Integration Contracts](../architecture/03-integration-contracts.md) §3.3, §4, §4.1, §5, §6 (Supply rows), §7.2, §7.2.1, §9, §10, §11, §15 · [04 Sub-Application Architectures](../architecture/04-subapplication-architectures.md) §7 · [05 Findings](../architecture/05-architecture-review-findings.md) D6, D24 · [07 Navy Data Systems](../architecture/07-navy-data-systems.md) §4 in full, §6 · [09 Monorepo & Conventions](09-monorepo-and-conventions.md) §4, §5, §8, §9 · [11 Outbox & Sync](11-outbox-sync-library.md) · [13 Synthetic Data Generator](13-synthetic-data-generator.md) §6, §12 |
| **Conventions** | The scaffold, layering, API middleware, CI, and the shared Definition of Done are document 09's. This document adds Supply-specific requirements only, and **removes nothing** |
| **Classification** | Internal |

**Every real MILSTRIP, COG, SMR, condition, purpose, advice, and status code value in this document traces to document 07.** Where document 07 records a value set as NOT PUBLICLY FOUND, this document says so and generates from a reserved range (13 §6) rather than inventing one. That discipline is document 07 §1's evidentiary rule, and it is not negotiable here: a fabricated code is recognised by a logistician on sight and costs more credibility than an acknowledged gap.

---

## 1. Purpose, scope, and the substitution objective

### 1.1 Purpose

Per document 04 §7: *represent parts availability, allowance position, and the documentary state of materiel in motion, at sufficient fidelity to constrain maintenance planning and to surface shortfalls.*

Three consequences of that sentence govern the whole build:

1. **"Constrain maintenance planning"** means Scheduling's optimizer is the primary consumer, and its needs — availability, lead time, condition, interchangeability, and an atomic reservation — are the required surface, not a convenience layer.
2. **"Documentary state"** means a part that is physically present but held behind an unfunded requisition is a *different* fact from a part that is absent, and the model must carry both. A planner needs the documentary fact.
3. **"Surface shortfalls"** means allowance position and availability are distinct axes, and conflating them produces unactionable output (§2.4).

### 1.2 Ownership boundary

**Owns** (04 §7): stock positions; allowance positions against COSAL and APL; requisitions and their documentary lifecycle; reservations and reservation sets; in-transit visibility; predicted demand; carcass obligations for depot-level repairables; and proposals targeting this sub-application.

**Does not own:** the parts catalogue or the allowance documents themselves (Registry), work orders (Scheduling), predictions (PdM), the failure-mode vocabulary or general code-set enumerations (Reference Data), or readiness rollups (Fleet Status).

**Does not own, specifically and importantly:** the authoritative SNSL allowance quantity and its Derivation Code. Those arrive on `allowance.updated` from the Registry. Supply stores them as received and may *propose* a revision (§6.5). It never overwrites them. The platform's improved allowance basis is a `Proposal`, adjudicated by a `supply_officer`, not a write.

### 1.3 Designed for substitution from the outset

Document 04 §7's key decision, restated as a build rule: **the `x-substitution: required` surface is confined to what Scheduling and Fleet Status genuinely need, and everything else is `internal`.** The design objective is that the substitution be uneventful, so a partner adapter is a small and testable artifact.

Three build rules follow, and they are what make the objective real rather than aspirational:

- **The required surface is enumerated once, in §7.6, and is closed.** Adding an operation to it is a contract change requiring an ADR and a change to this document. Every operation not in that table is `internal`, and an `internal` operation may not appear in any consumer's `depends_on_operations` (doc 10 §6.7 fails the build on a consumer depending on an `internal` operation — that is a C4-class undeclared dependency).
- **No required operation exposes an internal representation.** No stock ledger entry, no reservation row identifier other than `reservation_set_id`, no document sequence counter, no outbox artefact. The required surface is domain facts and canonical identity only.
- **A reference substitute is built and the suite runs against it in CI** (§9.2). The mock partner is the executable definition of "a partner could pass." Without it, D24's remedy is a claim.

### 1.4 What this document adds to document 04, and flags as an addition

Document 04 §7 is the architecture of record and this document does not silently diverge from it. Six additions to its API table are made here, each justified, each flagged, and each collected in **§7** so a reader can audit them in one place:

| Addition | Reason | Where |
|---|---|---|
| `condition_code` query parameter and a mandatory per-condition-code response breakdown on `GET /availability` | **The unclosed half of D24.** Lead time and interchangeability got operations; condition code did not | §7.2 |
| `POST /availability/query` — batch, consistent snapshot with epoch tokens | The other half of D6: *"neither a consistent snapshot nor atomic reservation."* An optimizer cannot fence a reservation against a snapshot it cannot obtain | §7.3 |
| `GET /reservation-sets/{id}` | Scheduling holds a `ReservationSet` aggregate (04 §6) and must be able to read its state without waiting for an event | §7.4 |
| `GET /reservation-sets?changed_since=` | Obligation 5 requires a change-feed read over **every** aggregate a declared consumer projects. Scheduling projects this one | §7.4 |
| `POST /reservation-sets/{id}/extend` | Without it, a work package awaiting adjudication must either hold an unbounded reservation — defeating the TTL — or release and re-reserve, reintroducing the race at the exact moment of approval | §7.4 |
| `POST /demand-forecast-runs` | Document 04 §7's own plane-placement paragraph requires the Domino Job to write "back through this sub-application's API," but its API table lists no write path. A `GET` with no ingest operation is unimplementable | §7.5 |

---

## 2. Data model

### 2.1 The aggregate map

| Aggregate | Root identity | Conflict policy (03 §11) | Notes |
|---|---|---|---|
| `StockKey` + `StockPosition` | `(niin, location_id)` + condition and purpose | Enterprise-authoritative, not edge-writable (§11 default) | The lock row and the fence token live on `StockKey`; quantities on `StockPosition` |
| `AllowancePosition` | `(asset_id, niin)` | Enterprise-authoritative | Authorized versus actual. **Distinct from availability** |
| `Requisition` | `document_number` (14 char) | **Server-authoritative; edge queues submissions** — 03 §11, external legal effect | The documentary lifecycle |
| `ReservationSet` + `ReservationSetLine` | `reservation_set_id` | Enterprise-authoritative | **The D6 fix.** No partial state exists |
| `InTransitItem` | `transportation_control_number` (17 char) | Enterprise-authoritative | 07 §4.9 |
| `DemandForecast` | `(niin, scope, horizon_days, run_id)` | Enterprise-authoritative | Predicted consumption, first-class published output |
| `CarcassObligation` | `(document_number, niin)` | Enterprise-authoritative | Repairables: recoverability `D`/`L`. Not a consumption record |
| `Proposal` | `proposal_id` | **Append-only; adjudication server-authoritative and claim-gated** — 03 §11 | Schema fixed by 03 §7.2. Closes C12 for this slug |

The README declares this table verbatim, satisfying obligation 16 and closing C20 for `supply`.

### 2.2 Location — a Phase 3 question, decided

Document 04 §7 leaves location granularity open. **[ESTABLISHED HERE]**, because the reservation protocol cannot be specified without it:

```sql
CREATE TYPE supply.location_type AS ENUM (
    'onboard_storeroom',   -- SNSL Part III Section A / B; asset_id required
    'ashore_activity',      -- NAVSUP FLC or RMC-held stock
    'depot',                -- ICP / wholesale
    'in_transit'            -- has a TCN; quantity is due-in, never on-hand
);

CREATE TABLE supply.location (
    location_id     uuid PRIMARY KEY,
    location_type   supply.location_type NOT NULL,
    asset_id        uuid NULL,          -- REQUIRED for onboard_storeroom, else NULL
    label           text NOT NULL,      -- "Storeroom 3-118-2-A"; human reference only
    CONSTRAINT location_asset_required
        CHECK ((location_type = 'onboard_storeroom') = (asset_id IS NOT NULL))
);
```

`in_transit` is a location rather than a flag because in-transit visibility is a documented Supply obligation (07 §4.9) and because materiel in motion has a position that is neither the shipper's nor the receiver's. **On-hand quantity at an `in_transit` location is always zero**; the quantity is `due_in_qty` at the destination, and the CHECK in §2.3 enforces it.

### 2.3 `StockKey` and `StockPosition`

Two tables, deliberately. The split is what makes the reservation lock both correct and unforgettable (§3.4).

```sql
-- The lock row and the optimistic-fence token. Exactly one row per (niin, location_id).
CREATE TABLE supply.stock_key (
    niin            text   NOT NULL,      -- 03 §3.3 join key. See §13 correction 1 on the pattern
    location_id     uuid   NOT NULL REFERENCES supply.location(location_id),
    stock_epoch     bigint NOT NULL DEFAULT 1,   -- monotonic; bumped by trigger on ANY child change
    lock_order_key  bytea  NOT NULL,      -- GENERATED: convert_to(niin,'UTF8') || '\x1f' || uuid_send(location_id)
    updated_at      timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (niin, location_id)
);

CREATE TABLE supply.stock_position (
    niin              text NOT NULL,
    location_id       uuid NOT NULL,
    condition_code    char(1) NOT NULL,   -- Reference Data validated. 07 documents A, F, M only (§2.9)
    purpose_code      char(1) NOT NULL,   -- 07 §4.9, §6: 'S' protect specific assets; A -> V/W carcass
    on_hand_qty       integer NOT NULL DEFAULT 0,
    reserved_qty      integer NOT NULL DEFAULT 0,   -- sum of live ReservationSetLine allocations
    due_in_qty        integer NOT NULL DEFAULT 0,
    unit_of_issue     text NOT NULL,      -- 07 §4.8; 'SO' = Shot (15 fathoms) is real. 'ST' is FORBIDDEN
    cog               char(2) NOT NULL,   -- 07 §4.6; funding source + ICP + (with SMR) carcass obligation
    unit_price_cents  bigint NOT NULL,    -- implied two decimals, 07 §7.2. NEVER a float
    apl               text NULL,          -- 07 §4.1 shapes; human reference and federation only
    updated_at        timestamptz NOT NULL DEFAULT clock_timestamp(),

    PRIMARY KEY (niin, location_id, condition_code, purpose_code),
    FOREIGN KEY (niin, location_id) REFERENCES supply.stock_key(niin, location_id),

    -- Oversell is UNWRITABLE, not merely discouraged. This is the D6 invariant at rest.
    CONSTRAINT stock_reserved_nonnegative CHECK (reserved_qty >= 0),
    CONSTRAINT stock_reserved_within_onhand CHECK (reserved_qty <= on_hand_qty),
    CONSTRAINT stock_onhand_nonnegative CHECK (on_hand_qty >= 0)
);

-- The trigger that makes the lock unforgettable (§3.4).
CREATE FUNCTION supply.bump_stock_epoch() RETURNS trigger AS $$
BEGIN
    UPDATE supply.stock_key
       SET stock_epoch = stock_epoch + 1, updated_at = clock_timestamp()
     WHERE niin = COALESCE(NEW.niin, OLD.niin)
       AND location_id = COALESCE(NEW.location_id, OLD.location_id);
    RETURN NULL;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER stock_position_epoch
    AFTER INSERT OR UPDATE OR DELETE ON supply.stock_position
    FOR EACH ROW EXECUTE FUNCTION supply.bump_stock_epoch();
```

Four properties are load-bearing:

- **`reserved_qty <= on_hand_qty` is a database CHECK.** No code path can oversell. Document 11 §2.2 uses the same move for the compaction key, for the same reason: a constraint makes a class of bug unwritable, where a convention makes it merely discouraged.
- **The CHECK has a consequence the implementer must handle, not discover.** A survey, loss, or inventory adjustment that reduces `on_hand_qty` below outstanding `reserved_qty` would violate it. The stock-adjustment path therefore **releases affected reservation sets in the same transaction** with cause `stock_shortfall`, emitting `reservation_set.released` and `part_availability.changed` together (§3.10). Discovering this in production, as a constraint violation on an operator's inventory correction, would be an outage.
- **The trigger means every writer takes the `stock_key` row lock whether it remembers to or not.** A concurrent stock receipt that never heard of the reservation protocol still serializes against it, because its `UPDATE` fires the trigger, which locks the parent row the reservation path holds.
- **`lock_order_key` is a byte sequence, not a collated string.** Ordering by `niin` under a database collation would silently change the lock order between environments — a collation change is a deadlock regression with no code diff. Ordering on bytes cannot drift.

`available_qty` is **derived, never stored**: `on_hand_qty - reserved_qty`, per `(niin, location_id, condition_code, purpose_code)`. It is exposed as a computed field and there is no column for it, because a stored copy is a second source of truth for the one number the whole protocol turns on.

### 2.4 `AllowancePosition` — distinguished from availability

Document 04 §7's key decision: *an item on hand but not authorized, and an item authorized but absent, are different conditions with different remedies, and conflating them produces unactionable output.* The model expresses that as **four states with two distinct remedies**, computed rather than stored:

```sql
CREATE TYPE supply.allowance_state AS ENUM (
    'authorized_and_held',        -- allowance_qty > 0, on_hand >= allowance. No action
    'authorized_shortfall',       -- allowance_qty > 0, on_hand < allowance. Remedy: REQUISITION
    'held_not_authorized',        -- allowance_qty = 0, on_hand > 0. Remedy: OFFLOAD or allowance revision
    'not_authorized_not_held'     -- neither. Remedy: allowance revision, if demand is real
);

CREATE TABLE supply.allowance_position (
    asset_id                 uuid NOT NULL,
    niin                     text NOT NULL,
    -- AS RECEIVED from the Registry on `allowance.updated`. NEVER written by this service.
    allowance_qty            integer NOT NULL,
    derivation_code          text NOT NULL,   -- SNSL. Value set NOT PUBLICLY FOUND except 'Y' (§6.5)
    sparing_model            text NULL,       -- 07 §4.3: '.5 Price Sensitive FLSIP Plus' | '.25 FLSIP'
                                              -- | '.10 MOD-FLSIP' | 'RBS' | 'TRIDENT'
    allowance_source         text NOT NULL,   -- 'SNSL_PART_III_A' | 'SNSL_PART_III_B' | 'AEL' | 'RSS' ...
    allowance_col_band       text NULL,       -- 07 §4.2 bands: 1|2|3|4|5-8|9-20|21-50 equipments
    cosal_revision           text NOT NULL,
    baseline_epoch           bigint NOT NULL, -- the configuration epoch this allowance was computed under
    -- THE PLATFORM'S CONTRIBUTION, held separately and never conflated with the above.
    proposed_allowance_qty   integer NULL,
    proposed_derivation_code text NULL,       -- from the reserved synthetic set, 13 §12.2
    proposal_id              uuid NULL,       -- the Proposal carrying it for adjudication
    proposal_basis_ref       text NULL,       -- demand_forecast run reference
    PRIMARY KEY (asset_id, niin)
);
```

**The separation of `allowance_qty` from `proposed_allowance_qty` is the whole design.** Document 07 §4.3 calls `UR = POP × BRF / 4` *"the loop the program exists to improve"* — the platform's contribution is a better-informed replacement factor and a defensible derivation basis. Writing that improvement into `allowance_qty` would make the platform an unaccountable allowance authority. Holding it in `proposed_allowance_qty` behind a `supply_officer` adjudication makes it a recommendation into a process the Navy already has, which is both correct and a materially better demonstration.

**`held_not_authorized` is not a defect to be normalised away.** It is a real and common shipboard condition, its remedy is an offload or an allowance revision rather than a requisition, and a system that reports it as "available" tells a planner a part is usable when its presence is unauthorized and unfunded.

### 2.5 `Requisition`

```sql
CREATE TABLE supply.requisition (
    document_number   char(14) PRIMARY KEY,   -- 07 §4.4, exact. Construction in §4.1
    niin              text NOT NULL,
    quantity          integer NOT NULL CHECK (quantity > 0),
    unit_of_issue     text NOT NULL,
    asset_id          uuid NOT NULL,          -- the requisitioner
    state             supply.requisition_state NOT NULL,
    current_dic       char(3) NULL,           -- the DIC of the most recent transaction (§4.2)
    advice_code       char(2) NULL,           -- 07 §4.5: '2L' predicted abnormal quantity; 5-series carcass
    priority_designator smallint NULL CHECK (priority_designator BETWEEN 1 AND 15),
    force_activity_designator smallint NULL,  -- F/AD; the PD matrix input (07 §4.5)
    urgency_of_need   char(1) NULL,           -- 'A' | 'B' | 'C'. See the CHECK below — this is the D-rule
    required_delivery_date date NULL,         -- forward-dated for a predicted requirement
    driver            supply.requisition_driver NOT NULL,  -- prediction | casualty | allowance | pms | manual
    triggering_prediction_id uuid NULL,       -- provenance for a prediction-driven document
    jcn               char(13) NULL,          -- 07 §5.2; the linkage to the maintenance job
    purpose_code      char(1) NULL,           -- 'S' where protecting a specific asset (07 §6)
    projected_availability date NULL,
    awaiting_parts_days integer NULL,         -- feeds MDT, 13 §11.3
    submitted_at      timestamptz NULL,
    baseline_epoch    bigint NOT NULL,
    classification    jsonb NOT NULL,

    -- 07 §4.5: "a predicted failure is not yet 'unable to perform'." UND 'A' for a
    -- prediction-driven requirement is logically wrong and a logistician will notice.
    CONSTRAINT und_a_forbidden_for_predicted
        CHECK (NOT (driver = 'prediction' AND urgency_of_need = 'A')),
    -- A predicted requirement's RDD is forward of submission, by construction.
    CONSTRAINT predicted_rdd_is_forward
        CHECK (driver <> 'prediction' OR submitted_at IS NULL
               OR required_delivery_date > submitted_at::date)
);
```

The two CHECKs are the same move as §2.3's: the most likely domain error in the entire service is a prediction-driven requisition that looks like a casualty, and a constraint prevents it where a code review might not.

### 2.6 `ReservationSet` and `ReservationSetLine` — the D6 aggregate

```sql
-- THERE IS NO 'pending' AND NO 'partial' STATE. See §3.2 — this is the fix, in the type system.
CREATE TYPE supply.reservation_set_state AS ENUM ('confirmed', 'consumed', 'released', 'expired');

CREATE TYPE supply.release_cause AS ENUM (
    'released_by_caller',   -- DELETE /reservation-sets/{id}
    'expired',              -- TTL lapse. Navy analogue: drawdown-date lapse -> 'BFU' (07 §6 item 5)
    'consumed',             -- material issued against a work order; terminal happy path
    'stock_shortfall',      -- an inventory adjustment made the set unhonourable (§3.10)
    'superseded'            -- replaced by a re-planned set for the same work package
);

CREATE TABLE supply.reservation_set (
    reservation_set_id  uuid PRIMARY KEY,
    asset_id            uuid NOT NULL,          -- partition key; a set serves one asset's work
    for_work_package_id uuid NULL,              -- Scheduling's reference, opaque here
    requested_by        text NOT NULL,          -- workload or user identity
    state               supply.reservation_set_state NOT NULL,
    granted_at          timestamptz NOT NULL,   -- database clock; see §3.8
    ttl_seconds         integer NOT NULL CHECK (ttl_seconds BETWEEN 60 AND 604800),
    expires_at          timestamptz NOT NULL,   -- granted_at + ttl_seconds, computed SERVER-SIDE
    extend_count        smallint NOT NULL DEFAULT 0 CHECK (extend_count <= 8),
    released_at         timestamptz NULL,
    release_cause       supply.release_cause NULL,
    idempotency_key     text NOT NULL,
    request_digest      bytea NOT NULL,         -- sha256 of the canonical request body
    etag                text NOT NULL,
    baseline_epoch      bigint NOT NULL,
    classification      jsonb NOT NULL,

    CONSTRAINT released_iff_cause
        CHECK ((state IN ('released','expired','consumed')) = (release_cause IS NOT NULL)),
    CONSTRAINT idempotency_unique UNIQUE (idempotency_key)
);

CREATE TABLE supply.reservation_set_line (
    reservation_set_id  uuid NOT NULL REFERENCES supply.reservation_set(reservation_set_id),
    line_ref            text NOT NULL,          -- caller-supplied; opaque, echoed back
    niin                text NOT NULL,
    location_id         uuid NOT NULL,
    condition_code      char(1) NOT NULL,       -- the code actually allocated from
    purpose_code        char(1) NOT NULL,
    quantity            integer NOT NULL CHECK (quantity > 0),
    for_work_order_id   uuid NULL,
    PRIMARY KEY (reservation_set_id, line_ref),
    FOREIGN KEY (niin, location_id) REFERENCES supply.stock_key(niin, location_id)
);

-- Live allocations are exactly the lines of sets in a holding state. The index that
-- makes the reaper and the availability read cheap.
CREATE INDEX reservation_set_expiring
    ON supply.reservation_set (expires_at) WHERE state = 'confirmed';
```

### 2.7 `InTransitItem`

```sql
CREATE TABLE supply.in_transit_item (
    transportation_control_number char(17) PRIMARY KEY,  -- 07 §4.9, 17 characters
    document_number   char(14) NULL REFERENCES supply.requisition(document_number),
    niin              text NOT NULL,
    quantity          integer NOT NULL CHECK (quantity > 0),
    condition_code    char(1) NOT NULL,
    from_location_id  uuid NULL,
    to_location_id    uuid NOT NULL,
    shipped_at        timestamptz NULL,
    estimated_arrival date NULL,
    last_status_dic   char(3) NULL,      -- 'AS_' shipment status family (07 §4.5)
    last_status_at    timestamptz NULL
);
```

In-transit quantity contributes to `due_in_qty` at `to_location_id` and to **nothing else**. It is never `on_hand`, is never reservable, and never contributes to `available_qty` — a reservation against materiel in a container is the documentary-versus-physical confusion document 04 §7 exists to prevent.

### 2.8 `DemandForecast` and `CarcassObligation`

```sql
CREATE TABLE supply.demand_forecast (
    run_id            uuid NOT NULL,
    niin              text NOT NULL,
    scope             text NOT NULL,          -- 'niin_fleet' | 'asset'
    asset_id          uuid NULL,              -- required when scope = 'asset'
    horizon_days      integer NOT NULL,       -- 30 | 90 | 180 (13 §2.3)

    -- THE DOCUMENTED BASELINE the platform improves upon. Always populated, always returned.
    baseline_ur       numeric(12,4) NOT NULL, -- UR = POP x BRF / 4  (07 §4.3)
    baseline_pop      integer NOT NULL,       -- installed population, from the Registry read model
    baseline_brf      numeric(12,4) NOT NULL, -- Best Replacement Factor: fleet-reported 3-M usage
    baseline_brf_as_of date NOT NULL,         -- BRF is updated annually (07 §4.3)
    baseline_disposition text NOT NULL,       -- 'carry' (UR>=0.50) | 'may_exclude' (UR<0.125) | 'between'

    -- THE MODEL FIGURE.
    expected_demand_p50 numeric(12,4) NULL,
    expected_demand_p90 numeric(12,4) NULL,
    forecast_basis      supply.forecast_basis NOT NULL,   -- the SMR branch, §5.2
    smr_source_code     char(2) NOT NULL,
    smr_recoverability  char(1) NOT NULL,
    prediction_value_class text NOT NULL,     -- 'high' for PB/PG (§5.4) | 'standard' | 'not_applicable'
    sharp_estimate_permitted boolean NOT NULL,-- false where the underlying reference class forbids it
    reference_class     text NOT NULL,        -- carried through from FailurePrediction (03 §7.1)
    calibration_population integer NULL,
    redirected_from_niin text NULL,           -- XA -> NHA redirect provenance (§5.3)
    redirect_path       jsonb NULL,
    carcass_adjusted    boolean NOT NULL DEFAULT false,  -- recoverability D/L (§5.5)

    -- Provenance, per obligation 9.
    model_version     text NOT NULL,
    computed_at       timestamptz NOT NULL,
    baseline_epoch    bigint NOT NULL,
    classification    jsonb NOT NULL,         -- inherited_from = union of input labels

    PRIMARY KEY (run_id, niin, scope, horizon_days),
    CONSTRAINT asset_scope_requires_asset
        CHECK ((scope = 'asset') = (asset_id IS NOT NULL)),
    -- 03 §7.1's gate, carried forward: no sharp number where calibration does not support one.
    CONSTRAINT no_sharp_estimate_without_permission
        CHECK (sharp_estimate_permitted OR expected_demand_p50 IS NULL)
);

CREATE TABLE supply.carcass_obligation (
    document_number   char(14) NOT NULL REFERENCES supply.requisition(document_number),
    niin              text NOT NULL,
    advice_code       char(2) NOT NULL,   -- 07 §4.5 5-series: 5G | 5S | 5R | 5D | 5A
    turn_in_dic       char(3) NULL,       -- 'BC1' (07 §6 item 6)
    condition_progression text NULL,      -- documented: 'F' -> 'M' -> 'A'
    purpose_code_from char(1) NULL,       -- documented flow: A -> V/W
    purpose_code_to   char(1) NULL,
    tracking_status   char(2) NULL,       -- 'RV' (07 §6 item 6)
    tracking_job      text NULL,          -- 'JSL326', the documented carcass tracking job
    PRIMARY KEY (document_number, niin)
);
```

`no_sharp_estimate_without_permission` is document 03 §7.1's `p_failure` gate propagated into demand. Below n=50 in the calibration cell, PdM publishes no calibrated probability at all — so a demand forecast that renders a sharp expected quantity from it is manufacturing precision that does not exist. The honest output for that cell is the baseline `UR` plus a qualitative flag, and the CHECK guarantees it.

### 2.9 Code sets are read, never owned

Document 12 §1.3 places *"unit hierarchy, ESWBS/EIC code sets, and general enumerations"* with Reference Data but explicitly out of that document's scope. Supply therefore has a dependency with no server yet. **Decision, and it is a decision rather than a deferral:**

- Supply validates `condition_code`, `purpose_code`, `advice_code`, `cog`, `unit_of_issue`, `dic`, and `smr` against Reference Data's general-enumeration surface, cached, never on a compute path (09 §4.4.2 sanctions the `reference-data` egress edge for exactly this).
- Until that surface exists, the seed set lives in `packages/canonical-schemas` as typed enums generated from document 07's verified values, each carrying `set_is_complete` — the honest-partial pattern document 12 §2.6 establishes for the 3-M `ACTION_TAKEN` set.
- **Document 07 verifies exactly three Supply condition codes: `A`, `F`, `M`** (§6 item 6's `F → M → A` progression). The full Supply Condition Code table is not in document 07 (**OQ-S8**). The enum therefore carries those three with `set_is_complete = false`, and **no fourth value is invented.** A dataset containing condition code `B` that document 07 never verified is precisely the fabrication document 07 §1 forbids.
- Recorded as open question **OQ-S1** (§14): the general-enumeration surface needs an owner and a document.

---

## 3. The reservation-set transactional protocol

This section is the reason the document exists. It is specified to a level at which D6 is demonstrably closed rather than asserted closed.

### 3.1 What D6 actually says

> *"The optimizer has neither a consistent snapshot nor atomic reservation. It solves over a stale non-atomic mixture, then reserves per-NIIN with no batch, no TTL, no two-phase confirm and no compensating release. 37 of 40 reservations succeed, the 38th fails, orphans persist and 37 spurious availability events degrade every other asset's planning. `lead time` is named as a hard constraint but exists in no Supply event or operation."*

Five distinct defects, and each needs its own mechanism:

| Defect | Mechanism | Section |
|---|---|---|
| No consistent snapshot | `POST /availability/query` returning one `as_of` and a per-key `stock_epoch` | §3.7, §7.3 |
| Per-NIIN, non-atomic | One request, one transaction, deterministic lock order | §3.3, §3.4 |
| No TTL | Server-computed `expires_at`, single-clock evaluation, reaper | §3.8 |
| No two-phase confirm | Two phases **inside** one transaction — feasibility over all lines, then commit | §3.4 |
| No compensating release | `DELETE`, TTL expiry, and adjustment-driven release, each emitting `reservation_set.released` | §3.9, §3.10 |
| Lead time in no operation | `GET /lead-times`, plus `lead_time` in the snapshot response and the availability event | §7.1 |

### 3.2 The modeling decision: no partial state exists

**`ReservationSet` has no `pending` state and no `partial` state, and this is the fix expressed in the type system rather than in the code.**

A set is `confirmed` at creation or it does not exist. The enum in §2.6 contains no state that could represent 37 of 40 lines. Consequently:

- There is no operation that adds a line to an existing set. A changed plan creates a new set and releases the old one with cause `superseded`.
- There is no per-line state. A line has no independent lifecycle to get stuck in.
- There is no route by which a caller, a retry, a crash, or a partial network failure produces a half-set, because the representation cannot hold one.

D6's failure scenario is not defended against. **It is unrepresentable.** A conformance test can assert the absence of orphans (§9.3), and a reviewer can verify the absence of the state that would permit them by reading one `CREATE TYPE`.

### 3.3 `POST /reservation-sets` — exact request and semantics

```
POST /api/v1/supply/reservation-sets
Authorization: Bearer <token>
Idempotency-Key: 6f1c9d84-6c2b-4a1e-9c8e-2a7f0b3d5e11      # REQUIRED (state-changing)
X-Correlation-Id: <uuid>
Content-Type: application/json

{
  "asset_id": "8f2b1e40-1c33-4e5a-9d21-7b6a0c4f8e19",
  "for_work_package_id": "b1d4e7a2-55c9-4f80-8a3e-1c2d9f4b6e70",
  "ttl_seconds": 3600,
  "fence": "strict",                                  # "strict" | "none"; default "strict"
  "lines": [
    {
      "line_ref": "wo-4412-l1",                       # caller-supplied, unique within the request
      "niin": "LLC004821",
      "location_id": "d7c1a9e3-2b44-4f16-8e05-3a9b1c7d2f88",
      "quantity": 2,
      "acceptable_condition_codes": ["A"],            # default ["A"]; validated against Reference Data
      "purpose_code": null,                           # null = any; "S" to draw earmarked stock
      "for_work_order_id": "3c9e2b17-8d54-4a2f-b6c1-0e7a5d3f9b42",
      "expected_stock_epoch": 41                      # REQUIRED when fence = "strict"
    }
    /* ... up to max_lines (default 250, declared in the chart and in the spec) ... */
  ]
}
```

Request rules, all enforced at the API boundary and all conformance-tested:

| Rule | Behavior on violation |
|---|---|
| `lines` non-empty, `<= max_lines` | `422` `urn:fathom:problem:supply:reservation-set-too-large` with the declared maximum |
| `line_ref` unique within the request | `422` `duplicate-line-ref`. **Not** silently merged — a caller that duplicated a ref has a bug and hiding it produces a set whose accounting the caller cannot reconcile |
| Two lines may share `(niin, location_id)` with distinct `line_ref` | **Permitted.** Two work orders legitimately need the same part. The lines are preserved for accounting; locking and feasibility aggregate them per `(niin, location_id)` |
| `fence = "strict"` requires `expected_stock_epoch` on every line | `422` `fence-requires-epoch` |
| `asset_id` must exist in the configuration read model at a non-superseded `baseline_epoch` | `409` `superseded-baseline` |
| Every `niin` must be transactionable | `422` `niin-not-transactionable` — a **LICN never appears in a supply transaction** (07 §4.8) |
| `ttl_seconds` within `[60, 604800]` | `422` `ttl-out-of-range` |
| `Idempotency-Key` absent | `400` per the shared middleware (09 §5.3) |
| Same `Idempotency-Key`, same body | Returns the **original** `201` with the original `reservation_set_id`. No second set, no second event |
| Same `Idempotency-Key`, different body | `422` `idempotency-key-reuse` |

### 3.4 The isolation mechanism, exactly

This is the operative specification. An implementer follows it literally.

```python
# services/supply/src/fathom_supply/services/reservations.py
#
# THE RESERVATION-SET TRANSACTION.  DO NOT RESTRUCTURE.   [05 D6 · 03 §6 · 04 §7]
#
# The bug this prevents, in the reviewer's words: "37 of 40 reservations succeed,
# the 38th fails, orphans persist and 37 spurious availability events degrade every
# other asset's planning."  Every element below exists because removing it
# reintroduces one specific half of that sentence.

async def create_reservation_set(cmd: CreateReservationSet, uow: UnitOfWork) -> ReservationSet:

    # ---- Phase 0: normalise, OUTSIDE any lock. Pure computation. ------------
    # Aggregate the caller's lines into distinct lock keys, and sort those keys
    # into the CANONICAL BYTE ORDER.  The sort is what makes the protocol
    # deadlock-free: two concurrent sets over overlapping NIINs acquire in the
    # same order, so one waits.  Without it, {A,B} versus {B,A} deadlocks, Postgres
    # aborts one after deadlock_timeout, and the optimizer reads a spurious
    # "unavailable" a full second late.
    demand: dict[LockKey, int] = aggregate_quantity_by_lock_key(cmd.lines)
    keys: list[LockKey] = sorted(demand, key=lambda k: k.lock_order_key)   # bytes, never collation

    async with uow.begin():                        # ONE transaction. READ COMMITTED suffices.

        # ---- Phase 1: acquire, in canonical order, ONE KEY AT A TIME. -------
        # A single set-based `SELECT ... FOR UPDATE ... ORDER BY` is NOT sufficient:
        # Postgres does not guarantee lock-acquisition order matches the ORDER BY
        # under every plan (a bitmap heap scan will not).  The loop is the guarantee.
        stock_keys = []
        for key in keys:
            stock_keys.append(await repo.lock_stock_key(uow, key))   # SELECT ... FOR UPDATE, 1 row

        # ---- Phase 2: feasibility over ALL lines, before ANY write. ---------
        # This is the "reserve" half of reserve-then-confirm.  It writes nothing.
        infeasible: list[LineFailure] = []
        allocation: list[Allocation] = []
        for line in cmd.lines:
            if cmd.fence == "strict":
                observed = stock_keys_by_key[line.lock_key].stock_epoch
                if observed != line.expected_stock_epoch:
                    infeasible.append(LineFailure(line, "stock_epoch_stale",
                                                  observed_stock_epoch=observed))
                    continue
            alloc = allocate_from_conditions(line, positions_by_key[line.lock_key])
            if alloc is None:
                infeasible.append(LineFailure(line, "insufficient_stock",
                                              available_qty=..., shortfall=...))
            else:
                allocation.append(alloc)

        if infeasible:
            # ---- ALL-OR-NOTHING.  Raise; the transaction rolls back. --------
            # Nothing was written, so there is nothing to compensate.  No set row,
            # no line rows, no reserved_qty increment, NO OUTBOX ROW — therefore no
            # `part_availability.changed`, which is the "37 spurious availability
            # events" half of D6.  The 409 body carries EVERY failing line so the
            # optimizer re-solves once instead of probing 40 times.
            raise ReservationSetInfeasible(infeasible)

        # ---- Phase 3: confirm. Writes, still inside the same transaction. ---
        rset = await repo.insert_reservation_set(uow, cmd, state="confirmed")
        await repo.insert_lines(uow, rset, allocation)
        await repo.increment_reserved(uow, allocation)        # CHECK enforces no oversell

        # ---- Phase 4: events, SAME transaction, via the outbox (11 §2.3). ---
        outbox.emit(uow, event_type="fathom.supply.reservation_set.confirmed",
                    aggregate="reservation_set", aggregate_id=str(rset.reservation_set_id),
                    scope=Scope.ASSET, subject=Subject(asset_id=rset.asset_id),
                    payload=ReservationSetConfirmed.from_domain(rset),
                    classification=rset.classification, baseline_epoch=rset.baseline_epoch)
        for key in keys:                                      # one per AFFECTED key, not per line
            outbox.emit(uow, event_type="fathom.supply.part_availability.changed",
                        aggregate="part_availability", aggregate_id=f"{key.niin}:{key.location_id}",
                        scope=Scope.NIIN, subject=Subject(niin=key.niin),
                        compaction_key=f"{key.niin}:{key.location_id}",      # 03 §5.1, [D5]
                        payload=PartAvailabilityChanged.from_key(key), ...)
    # commit. The set, its lines, the reserved quantities, and ALL of the events
    # became true together, or none of them did.
    return rset
```

Six properties, each with the failure it prevents:

| Property | Prevents |
|---|---|
| **One HTTP request, one database transaction** | The 40-call sequence in which call 38 fails. There is no call 38 |
| **Deterministic byte-order lock acquisition, one key at a time** | Deadlock between overlapping concurrent sets, and the spurious "unavailable" a deadlock abort produces |
| **The `stock_key` row lock, made unforgettable by the epoch trigger (§2.3)** | A concurrent receipt, issue, or adjustment interleaving between feasibility and confirm. Any writer of `stock_position` fires the trigger, which needs the same row lock |
| **Feasibility over all lines before any write** | Partial commitment. Phase 2 is read-only, so a failure in it has nothing to undo |
| **`reserved_qty <= on_hand_qty` as a CHECK** | Oversell by any path, including a future one this document did not anticipate |
| **Every event emitted through the outbox in the same transaction** | The 37 spurious availability events, and their inverse — a committed reservation no consumer hears about |

**Rejected alternatives, recorded so they are not re-litigated per team:**

| Alternative | Why rejected |
|---|---|
| `SERIALIZABLE` isolation with retry | Correct, but converts contention into `40001` serialization failures the caller must retry, and the retry is a fresh solve. Explicit row locks give the same guarantee with waiting rather than aborting, which is what a batch optimizer wants |
| `pg_advisory_xact_lock` per key instead of the row lock | Works, and was the first design. Rejected because a hash collision serialises unrelated keys, and — decisively — because an advisory lock protects nothing against a writer that does not take it. The row lock is enforced by a trigger; an advisory lock is enforced by memory |
| A saga with per-NIIN compensation | **Strictly worse, and it is the D6 shape.** A saga's intermediate states are exactly the orphans. See §3.12 |
| Application-level mutex or a distributed lock service | A second source of truth for the invariant the database already enforces, plus a new liveness dependency, plus a lease that expires on a wall clock (03 §5.4 forbids it) |
| Optimistic retry without locks | Under 250 lines the probability that no key changed during a solve approaches zero, so it degenerates into a retry storm at the moment of highest contention |

**Two operational constraints the implementer must not discover the hard way:**

- **`ttl_seconds` and `expires_at` are computed by the database, never by the caller's process** (§3.8). A caller-supplied `expires_at` is ignored if present and the field is absent from the request schema.
- **Connection pooling.** The protocol holds row locks for the duration of one transaction only, so a transaction-pooling proxy is safe. **A session-scoped lock of any kind would not be**, which is the second reason the row lock beats a session advisory lock.

### 3.5 Exact response — success

```
HTTP/1.1 201 Created
Location: /api/v1/supply/reservation-sets/9d3f1a76-4e28-4b90-8c15-6a2e7f0d3b41
ETag: "3"
X-Classification: CUI
X-Correlation-Id: <echoed>
Content-Type: application/json

{
  "reservation_set_id": "9d3f1a76-4e28-4b90-8c15-6a2e7f0d3b41",
  "asset_id": "8f2b1e40-1c33-4e5a-9d21-7b6a0c4f8e19",
  "for_work_package_id": "b1d4e7a2-55c9-4f80-8a3e-1c2d9f4b6e70",
  "state": "confirmed",
  "granted_at": "2026-08-04T14:12:03.418627Z",
  "ttl_seconds": 3600,
  "expires_at": "2026-08-04T15:12:03.418627Z",
  "extend_count": 0,
  "lines": [
    {
      "line_ref": "wo-4412-l1",
      "niin": "LLC004821",
      "location_id": "d7c1a9e3-2b44-4f16-8e05-3a9b1c7d2f88",
      "quantity": 2,
      "condition_code": "A",
      "purpose_code": "A",
      "for_work_order_id": "3c9e2b17-8d54-4a2f-b6c1-0e7a5d3f9b42",
      "stock_epoch_after": 42
    }
  ],
  "classification": { "level": "CUI", "cui_categories": ["SP-CTI"], "...": "..." }
}
```

`state` is `confirmed` and can be nothing else on a `201`. There is no other creation outcome.

### 3.6 Exact response — partial failure

**No line succeeds. The response is a single `409` carrying every failure, and the database is byte-identical to its pre-request state.**

```
HTTP/1.1 409 Conflict
Content-Type: application/problem+json
X-Correlation-Id: <echoed>

{
  "type": "urn:fathom:problem:supply:reservation-set-infeasible",
  "title": "The reservation set could not be confirmed in full and was not created",
  "status": 409,
  "detail": "3 of 40 lines are infeasible. No reservation was created and no stock is held.",
  "instance": "/api/v1/supply/reservation-sets",
  "reservation_set_id": null,
  "failed_lines": [
    { "line_ref": "wo-4412-l7",  "niin": "LLC009117", "location_id": "d7c1...",
      "reason": "insufficient_stock", "requested_qty": 4, "available_qty": 1, "shortfall": 3,
      "lead_time_days": 21, "interchangeable_group_id": "ig-0f24" },
    { "line_ref": "wo-4412-l19", "niin": "LLC004821", "location_id": "a3b8...",
      "reason": "stock_epoch_stale", "expected_stock_epoch": 41, "observed_stock_epoch": 44 },
    { "line_ref": "wo-4412-l33", "niin": "LLA772C41", "location_id": "d7c1...",
      "reason": "condition_code_ineligible", "requested_condition_codes": ["A"],
      "available_by_condition": { "F": 6 } }
  ]
}
```

`reason` is a closed enum: `insufficient_stock` · `stock_epoch_stale` · `unknown_niin` · `niin_not_transactionable` · `location_not_found` · `condition_code_ineligible` · `purpose_code_ineligible` · `not_apl_authorized`.

Three response properties are contract terms, and §9.3 tests each:

- **`reservation_set_id` is explicitly `null`.** A caller must not be able to read a set identifier out of a failure and then attempt to release it.
- **Every failing line is reported, not the first.** The optimizer re-solves once. Returning the first failure recreates the 40-probe loop with extra steps.
- **`lead_time_days` and `interchangeable_group_id` accompany an `insufficient_stock` failure.** These are the two facts that let the optimizer immediately consider a substitute or a schedule slip instead of issuing a second query, and their presence here is part of D24's remedy.

### 3.7 The optimistic stock fence — the consistent-snapshot half of D6

Atomicity alone does not close D6. The reviewer's first clause is *"neither a consistent snapshot."* An optimizer that solves over stock it read at different instants and then reserves atomically has still solved the wrong problem — it merely fails atomically.

The mechanism is a **monotonic per-key epoch plus an optimistic fence**:

1. The optimizer calls `POST /availability/query` (§7.3) with its candidate key set. The response carries **one `as_of`** and a `stock_epoch` per key, read in a single read-only transaction — a genuine consistent snapshot, not a merge of per-key reads.
2. It solves against that snapshot.
3. It submits the reservation set with `fence: "strict"` and each line's `expected_stock_epoch`.
4. Any key whose epoch moved fails the line with `stock_epoch_stale`, and therefore fails the set. The optimizer re-queries and re-solves.

`fence: "none"` is available and is the correct choice for an interactive single-line reservation by a supply officer, where a stale-epoch rejection would be user-hostile noise. **The optimizer must use `strict`, and this is a consumer-driven conformance expectation contributed by `maintenance` (§9.4), not a suggestion.**

The complementary obligation sits on Scheduling's side and is already contracted: document 03 §5.2 requires that *"any computation with a correctness dependency on freshness declares a staleness bound and refuses to run outside it — the scheduling optimizer in particular `[D6]`."* Supply supplies the epoch; Scheduling refuses to solve on a stale read model. Both halves are needed.

### 3.8 TTL, expiry, and the reaper

**One clock, and it is the database's.** A TTL is a lease, and document 03 §5.4 forbids wall-clock lease arithmetic — but a per-process monotonic clock cannot be compared across processes or survive a restart. The resolution is that expiry is never *compared* across nodes at all:

- `expires_at` is computed server-side as `clock_timestamp() + (ttl_seconds || ' seconds')::interval` in the same transaction that creates the set. No application process computes it.
- Expiry is evaluated only by `WHERE expires_at <= clock_timestamp()` in that same database. There is exactly one clock in the comparison, so there is no cross-node skew to arbitrate.
- **Direction of error under a mandated backward step.** STIG rule V-260520 permits unlimited backward steps. A backward step on the database host can only *extend* an unexpired lease; it cannot expire an active one early. Extension holds stock slightly too long, which is recoverable by an explicit `DELETE`; premature expiry would release stock a planner believes is held, which is not. The safe direction is the one that occurs, and the reaper records the `sync_quality` attestation (11 §4.6) on every expiry so the extension is auditable rather than invisible.
- **All retry, backoff, and reaper scheduling remain monotonic**, per 03 §5.4 and doc 11. The database clock authorises *expiry*, not *timers*.

The reaper is an in-process scheduled task in the Supply service — not a CronJob, for document 11 §1.3's reason: a separately schedulable component is one somebody scales to zero.

```
every reaper_interval (default 15s, monotonic):
    for each batch:
        SELECT reservation_set_id FROM supply.reservation_set
          WHERE state = 'confirmed' AND expires_at <= clock_timestamp()
          ORDER BY expires_at LIMIT :batch FOR UPDATE SKIP LOCKED
        for each set:                       # ONE TRANSACTION PER SET
            lock its distinct stock_keys in canonical byte order      # §3.4's order, always
            UPDATE state='expired', released_at=clock_timestamp(), release_cause='expired'
            decrement reserved_qty for each line
            emit reservation_set.released (cause='expired')
            emit part_availability.changed per affected key
        commit
```

**A lagging reaper understates availability, and that is deliberate.** `available_qty` derives from `reserved_qty`, which only the reaper decrements. An unreaped expired set therefore continues to hide its stock. The error direction is: a part appears unavailable when it is in fact free. The inverse — appearing available when it is held — would oversell. Reaper lag is exposed as `fathom_supply_reservation_reaper_lag_seconds`, and `/readyz` degrades past a declared bound (09 §5.6). The lag is bounded, monitored, and errs safe; that is the whole of the argument, and it is stated rather than left for someone to reason out during an incident.

**The Navy analogue is documented, and worth stating because it means the TTL is not a software invention.** Document 07 §6 item 5 records that a reservation protecting a specific asset (`BRR`, or planned requirement `BPR` with purpose code `S`) lapses at a drawdown date, generating **`BFU`**. A `reservation_set.released` with cause `expired` is the platform's expression of that documented mechanism, and §4.2 records the correspondence in the requisition state machine.

### 3.9 `DELETE /reservation-sets/{id}` — explicit release

```
DELETE /api/v1/supply/reservation-sets/9d3f1a76-4e28-4b90-8c15-6a2e7f0d3b41
If-Match: "3"                # accepted and honoured; optional (03 §4 requires it on PUT/PATCH)
Idempotency-Key: <uuid>      # required

HTTP/1.1 204 No Content
```

| Case | Behavior |
|---|---|
| Set is `confirmed` | State → `released`, cause `released_by_caller`, `reserved_qty` decremented, `reservation_set.released` and `part_availability.changed` emitted in one transaction. `204` |
| Set is already `released`, `expired`, or `consumed` | **`204`, and no second event.** The caller's intent is satisfied; release is idempotent by intent, not merely by key |
| Set does not exist | `404` `urn:fathom:problem:supply:reservation-set-not-found` |
| `If-Match` supplied and stale | `412` |

Emitting `reservation_set.released` twice for one set would be worse than an error: Scheduling's read model would restore availability twice.

### 3.10 Consumption, and the stock-adjustment interaction

**Consumption.** When material is issued against a work order, the set (or the affected lines' quantities) transitions to `consumed`: `on_hand_qty` and `reserved_qty` decrement together — which is precisely why the CHECK survives — and `part_availability.changed` publishes. `consumed` is the terminal happy path and is reached through the internal issue operation, driven by `maintenance_action.recorded` carrying parts consumed. It is not a caller-facing state transition on the required surface.

**Stock adjustment — the path that makes the CHECK safe rather than an outage.** An inventory correction, survey, or loss that would drop `on_hand_qty` below outstanding `reserved_qty` must, **in the same transaction**:

1. Lock the `stock_key` in canonical order.
2. Select the affected `confirmed` sets, **oldest `granted_at` last** — newest sets are released first, so the longest-standing plan is disturbed least.
3. Release exactly as many as required, with cause `stock_shortfall`, emitting `reservation_set.released` per set.
4. Apply the adjustment.
5. Emit `part_availability.changed` once per affected key.

An implementation that instead relaxes the CHECK has converted a loud, transactional, event-emitting reconciliation into a silent negative-availability condition that every consumer's read model inherits.

### 3.11 Events, and their exact emission points

| Event | Emitted when | Scope / partition | Compaction key |
|---|---|---|---|
| `reservation_set.confirmed` | Set creation, same transaction | `asset` / `asset_id` | `reservation_set_id` |
| `reservation_set.released` | `DELETE`, TTL expiry, `stock_shortfall`, `superseded`, `consumed` | `asset` / `asset_id` | `reservation_set_id` |
| `part_availability.changed` | Once per affected `(niin, location)` in the same transaction as any change to on-hand, due-in, reserved, condition, or allowance position | `niin` / `niin` | `(niin, location)` |

Payloads carry exactly what document 03 §6 specifies. `reservation_set.confirmed`: *reservation set, NIIN quantities, expiry.* `reservation_set.released`: *reservation set, cause.* `part_availability.changed`: *NIIN, location, on-hand, due-in, allowance position, `lead_time`, `condition_code`, interchangeable group, `unit_price_cents`* **[AMENDMENT]**.

Two rules follow from document 03 §5.1 and are tested:

- **The compaction key is `(niin, location)` for availability and `reservation_set_id` for reservation sets — never the partition key.** Compacting availability on `niin` alone would collapse every storeroom, depot, and ashore position for a part into one record. Document 11 §2.2's `outbox_compaction_key_distinct` CHECK makes the error unwritable, and document 03 §5.1 names `(niin, location)` explicitly as the example.
- **One availability event per affected key, not per line.** Forty lines across twelve keys produce twelve availability events. Per-line emission would produce the event storm D6 describes even on the success path.

### 3.12 Why there is no saga, and what document 11 does and does not supply

Document 11 specifies the outbox, the inbox, clock discipline, conflict policy, provisional identity, and the divergence budget. **It specifies no saga or compensation framework, and this document deliberately does not add one.** The reasoning, recorded so a Phase 3 team does not add one later:

- **Inside Supply, atomicity is a local ACID property, not a distributed one.** Every reservation line, every stock position, and the outbox row all live in Supply's single owned logical database (03 §15.13, 11 §2.1). A saga would decompose a transaction the database already performs, and its intermediate states — reserved-but-unconfirmed lines — are *exactly* the orphans D6 describes. A saga here would be a faithful reimplementation of the finding.
- **Across the Scheduling↔Supply boundary, the protocol is a lease, not a transaction.** Scheduling holds a `ReservationSet` aggregate (04 §6) referencing an identifier Supply owns. The compensating action for a Scheduling crash after confirmation is **TTL expiry** — automatic, requiring no coordinator, no orchestrator state, and no liveness assumption about the crashed party. This is the correct pattern for a cross-service hold whose failure mode is "the requester went away," and it is why the TTL is mandatory rather than a convenience.
- **The one genuinely distributed obligation is already contracted.** Document 03 §6 requires that `work_package.approved` be *"published only after reservation confirmation `[D6]`."* That ordering is Scheduling's obligation, asserted by Scheduling's conformance suite and by the consumer-driven expectations Supply contributes to it. Supply's obligation is to make confirmation atomic and its events truthful.

**No cross-service two-phase commit, no distributed lock manager, and no orchestrator is introduced by this document.** Any proposal to add one must first explain what property the TTL lease fails to provide.

### 3.13 The reservation-set state machine

```
                        POST /reservation-sets  (201, all-or-nothing)
                                    │
                                    ▼
                             ┌─────────────┐
        POST …/extend ──────▶│  confirmed  │
        (expires_at moves)   └─────────────┘
                              │    │    │  │
       DELETE …/{id}          │    │    │  └────── material issued ──▶ ┌──────────┐
       cause=released_by_caller    │    │                              │ consumed │
                    ┌─────────┘    │    └── stock adjustment ──┐       └──────────┘
                    ▼              ▼        cause=stock_shortfall│
             ┌────────────┐  ┌──────────┐                       │
             │  released  │  │ expired  │◀── TTL lapse ─────────┘
             └────────────┘  └──────────┘     (Navy analogue: drawdown lapse -> BFU)
                    ▲
                    └── re-plan, cause=superseded

Terminal states: released · expired · consumed.  There is NO initial state other than
`confirmed`, and no state that can represent a subset of the requested lines.
```

---

## 4. The documentary lifecycle state machine

Document 04 §7's second key decision: *documentary state is modeled as an explicit lifecycle, at two levels… A planner needs to know that a part is theoretically available but held behind an unfunded requisition, which is a documentary fact rather than a physical one.*

### 4.1 The document number — 14 characters, exact

Per document 07 §4.4 (NAVSUP P-409):

| Positions | Element | Rule | Example |
|---|---|---|---|
| 1 | Service code | `N` other than fleet · `R` Pacific Fleet · `V` Atlantic Fleet | `R` |
| 2–6 | Requisitioner UIC | 5 characters. **The same UIC that opens the JCN** (13 §6.4) — generated from one source, never re-derived | `21487` |
| 7–10 | Julian date | `YDDD` | `6058` |
| 11–14 | Serial | 4 characters, **excluding the letters `I` and `O`** | `2101` |

Three build rules:

- Construction lives in exactly one module, `services/supply/src/fathom_supply/services/document_number.py`. A document number assembled inline anywhere else fails review, for the reason document 13 §6 gives about identifier minting.
- The serial alphabet excludes `I` and `O` in a constant, with the citation in a comment. A generator that emits `I` or `O` is a defect a logistician spots immediately.
- The UIC is drawn from the asset's `AssetRef.uic`, and **the six-character DoDAAC form is derived at the boundary, never stored as a second identifier** (13 §6.4). For unmanned assets, which have no vessel UIC, the **parent unit's** UIC is used — which is also operationally correct.

### 4.2 States and DIC transitions

DIC families are document 07 §4.5's, with its documented third-character semantics (`A` domestic NSN · `B` domestic part number · `1` overseas NSN; `_1` requisitioner · `_2` supplementary addressee · `_6` ICP-to-storage · `_8` to DAAS · `_9` from DAAS).

| State | Entered by | DIC / code | Notes |
|---|---|---|---|
| `queued` | Edge submission held for reconnect | **none** | Deliberate: no DIC exists before submission. Requisitions are *server-authoritative; edge queues submissions* (03 §11) because of external legal effect. A document number is not minted at the edge |
| `submitted` | Submission | **`A0A`** domestic NSN · **`A0B`** domestic part number → escalates to **DD 1348-6** where the part number exceeds 10 characters, or for a permanent NICN (07 §4.8) | The `A0_` requisition family |
| `status_received` | Supply status returned | **`AE_`** family | May recur. Carries `projected_availability` |
| `shipped` | Shipment status | **`AS_`** family | Creates or updates an `InTransitItem` with a 17-character TCN |
| `received` | Receipt posted | — | Increments `on_hand_qty` at the destination in the condition code received; decrements `due_in_qty` |
| `cancellation_requested` | Cancellation initiated | **`AC_`** / **`AK_`** families | |
| `cancelled` | Cancellation confirmed | | Terminal |
| `planned_requirement` | Protecting a specific asset ahead of need | **`BPR`** with **purpose code `S`**, then the `BPA`/`BPC`/`BPD` lifecycle; **`BFU`** on drawdown-date lapse | 07 §6 item 5. The documented analogue of a reservation-set TTL (§3.8) |
| `special_program_requirement` | Need beyond the requisition horizon | **`DYA`** → ICP status **`DYK`**/**`PA`**, or **`PB`** (held until procurement lead time from the support date) → **`PR`** (*"immediate requisition is needed"*) | 07 §6 item 4. **A fully documented closed loop for a forecasting activity** — which is exactly what this platform is |
| `reserved` | Reservation transaction | **`BRR`** | See the note below on the rest of the family |
| carcass path | Repairable turn-in | advice **`5G`** / **`5S`** / **`5R`** / **`5D`** / **`5A`**; turn-in **`BC1`**; condition **`F → M → A`**; purpose code **A → V/W** with status **`RV`**; tracking job **`JSL326`** | §5.5 |
| `converted` | Temporary NICN became an NSN | status code **`BG`** | 07 §4.8 |

**A deliberate gap, stated rather than filled.** Document 07 §4.5 names the reservation lifecycle family as **`BRR/BRA/BRC/BRF/BRS/BRX`** and document 07 §6 item 5 confirms `BRR` as the reservation transaction. **It does not document the individual meanings of `BRA`, `BRC`, `BRF`, `BRS`, or `BRX`.** This service therefore stores the family membership and assigns per-code semantics to `BRR` only; the other five are accepted on inbound status and recorded without interpretation. Assigning them meanings from general knowledge is exactly what document 09 DO-NOT 32 and document 07 §1 forbid, and it is the kind of error that survives review because it looks knowledgeable. Recorded as **OQ-S2** (§14).

### 4.3 Priority designator, UND, and RDD — the predicted-requirement rule

Document 07 §4.5, verbatim in its force: **"a predicted failure is not yet 'unable to perform.'"**

| Element | Rule | Enforcement |
|---|---|---|
| Urgency of Need | **`C`**, or **`B`** where degradation is already impairing performance. **Never `A`** for a prediction-driven requirement | CHECK `und_a_forbidden_for_predicted` (§2.5) **and** a `422` at the API boundary, `urn:fathom:problem:supply:und-a-for-predicted-requirement` |
| Priority designator | From the **Force/Activity Designator × Urgency of Need** matrix. Never assigned directly | Computed from `(force_activity_designator, urgency_of_need)`; a caller-supplied `priority_designator` is rejected `422` |
| Required delivery date | **Forward-dated**, consistent with the prediction horizon | CHECK `predicted_rdd_is_forward` |
| Priority 01–03 | Reachable by a **casualty**-driven document only. A predicted requisition does not reach it | Validated against `driver` |
| RDD codes | **`444`, `N__`, `E__` are never emitted** — NOT FOUND or affirmatively wrong (07 §4.5) | Rejected-value CHECK |
| Unit of issue | **`ST` is never emitted.** `SO` = Shot (15 fathoms) is real and correct for anchor chain | Rejected-value CHECK |
| Routing identifier | **`S9M`, `S9T`, `SMS`, `NRP` are never emitted** (07 §4.5) | Rejected-value CHECK |

The UND rule is the single most visible domain-fidelity test in the whole sub-application. A demonstration that generates UND `A` for a not-yet-failed pump loses a logistician in the first minute, and no amount of model quality recovers it.

### 4.4 Advice codes

| Code | Documented meaning (07 §4.5) | Use here |
|---|---|---|
| **`2L`** | *"Quantity reflected in the quantity field exceeds normal demands; however, this is a confirmed valid requirement"* | **The officially sanctioned encoding for a prediction-driven abnormal quantity.** Every requisition with `driver = 'prediction'` and a quantity above the demand-based level carries `2L`. This is the field the Navy already has for exactly what the platform does |
| **`5G`** | Exchange certification | Repairable carcass flow |
| **`5S`** | Remain-in-place | Repairable, where the failed item cannot be landed before the replacement arrives |
| **`5R`** | Release of planned requirement with turn-in | The bridge from `planned_requirement` to a carcass turn-in |
| **`5D`** | Initial requirement, or **increased allowance/stockage objective** | The code a platform-proposed allowance increase carries |
| **`5A`** | Surveyed as missing or damaged beyond repair | |

`5D` deserves emphasis: it is the documented instrument for an *increased allowance or stockage objective*, which is precisely the outcome an improved Best Replacement Factor produces (§6.5). The platform's recommendation therefore lands as a real transaction type rather than as a report.

### 4.5 Enforcement — domain policy in the operation, not in agent behavior

Document 03 §9 item 2 is explicit and names this sub-application: *"a requisition proposal's NIIN must be APL-authorized for that position… These are validation rules on the receiving operation, and they hold regardless of what an agent proposes or why."* D14's attack is a crafted corpus passage producing a requisition proposal with a substituted NIIN, a fluent rationale, and genuine citations that satisfy the non-empty-evidence gate mechanically.

Validation on `POST /proposals` (kind `requisition`) and on requisition creation, in order:

1. **APL authorization.** The NIIN must be APL-authorized for the position implied by the subject, resolved against the allowance and configuration read models. Not authorized → `422` `not-apl-authorized`. **This is the control that stops D14's attack**, and it holds whether the requester is an agent, a user, or a partner adapter.
2. **Transactionability.** A **LICN never appears in a supply transaction** (07 §4.8) → `422`.
3. **SMR source code.** A requisition for an **`XA`** NIIN is rejected → `422` `xa-has-no-independent-demand`, with the resolved next-higher-assembly NIIN in the problem body so the caller can resubmit correctly (§5.3).
4. **Baseline currency.** A superseded `baseline_epoch` → `409`. Re-validated **at adjudication**, not only at creation (03 §7.2, D16).
5. **Rejected-value sets.** §4.3's CHECK lists.

### 4.6 Authority — requisitions are dual-control, always

From document 03 §7.2.1's minimum-authority table:

| `kind` | `item`/`asset` | `class` | `fleet` |
|---|---|---|---|
| `requisition` | `supply_officer` | `supply_officer` | `fleet_authority` |

And from document 03 §7.2: `requires_dual_control` is *"true for class or fleet scope, **and for any kind with external legal effect**."* Document 03 §11 classifies requisitions as server-authoritative precisely *because of* external legal effect, and document 10 §—'s `EXTERNAL_LEGAL_EFFECT_KINDS` is `{requisition}`.

**Therefore: every `requisition` proposal carries `requires_dual_control = true`, at every blast radius, including `item`.** This is stronger than the blast-radius rule alone would give, and it is the correct reading of the two clauses together. Build rules:

- Supply sets `authority_class` at creation from the §7.2.1 table — `supply_officer` at item/asset/class, `fleet_authority` at fleet — and **re-validates it at adjudication** in case the scope was corrected in between (03 §7.2's re-validation rule).
- Adjudication requires a claim (`POST /proposals/{id}/claim`) and `If-Match` on the claimed ETag. Without the lease, the eventually-consistent queue permits two approvals and two requisitions — and a requisition is a document with external effect, so a duplicate is not merely a data defect.
- `second_adjudicator` is mandatory before a requisition proposal can transition to `approved`. An approval with one signature is rejected `422`, not warned about.
- Document 10's OQ-12 notes that document 03 §7.2 does not enumerate the external-legal-effect set. This document's position is recorded here as **OQ-S3** (§14): the set should be enumerated in document 03 §7.2, and until it is, `{requisition}` is the operative value for this slug.

---

## 5. The SMR-driven demand model branch

Document 07 §4.7: *"SMR is the most important table for demand modelling, because the source code partitions the demand model itself."* The branch is not an optimisation. A service that forecasts uniformly across source codes is wrong on a majority of its catalogue.

### 5.1 Parsing SMR — six positions, and one correction already applied

Current authority: AR 700-82 / SECNAVINST 4410.23A / AFMAN 21-106, 29 August 2020.

```
position:  1  2  |  3  |  4  |  5  |  6
           source  │     │      │     └─ Service option
                   │     │      └─────── RECOVERABILITY — ONE character (07 §9 correction)
                   │     └────────────── maintenance repair
                   └──────────────────── maintenance use
```

- **Recoverability is position 5 only.** Document 07 §9 records "SMR positions 5–6 = recoverability" as a **wrong premise already corrected**. A parser that slices `[4:6]` reproduces a defect the program has already found and fixed, and it would silently mis-class every repairable.
- Navy-specific: positions 3–5 map onto **Afloat (`F`) / Ashore (`H`) / both (`G`, Navy only) / Depot (`D`)** rather than the Army's crew-field-sustainment ladder. **`Z` in position 3 is Navy-only.** Numeric ship-class sub-codes **`2`–`6`** are Navy-only.
- The parser lives in one module, returns a typed `SmrCode`, and **refuses a code of length other than 6**. A silently truncated SMR is worse than a rejected one.

### 5.2 The source-code branch

Per document 07 §4.7, and mirrored by document 13 §12.3 which asserts each branch non-empty in the generated corpus:

| Source | `forecast_basis` | Demand behavior | API consequence |
|---|---|---|---|
| **`P*`** | `forecastable_stocked` | Stocked and forecastable — ordinary demand | Baseline `UR` and a model figure both published |
| **`XA`** | `nha_redirect` | **No independent demand.** The requirement is met by replacing the next higher assembly | Demand is published **against the NHA NIIN**, with redirect provenance. A requisition for the XA NIIN is rejected (§4.5) |
| **`K*`** | `kit_driven` | Demand arises from the kit | Forecast is against the kit, not the member |
| **`M*` / `A*`** | `material_or_component` | Demand is for raw material or components | Baseline `UR` published; model figure suppressed unless a bill-of-material expansion exists |
| **`PB`** insurance, **`PG`** sustained life support | `low_history_high_value` | **Little or no demand history. Exactly where prediction has the highest value** | `prediction_value_class = "high"`, and the response is shaped differently (§5.4) |

`forecast_basis` is a **required field on every `DemandForecast`** and appears in the `GET /demand-forecast` response. A consumer must be able to tell, without inference, whether the number it received is an ordinary forecast, a redirect, or a low-history estimate. This is the same discipline document 03 §7.1 applies with `reference_class`: the honest signal is a declared class, not a confidence scalar carrying two meanings.

### 5.3 `XA` → next-higher-assembly redirect: exact logic

```python
# services/supply/src/fathom_supply/services/nha_redirect.py
#
# 07 §4.7: XA = "No independent demand — requirement is met by replacing the next
# higher assembly. A prediction on an XA part must be translated into next-higher-
# assembly demand."  13 §7.2 makes this a required realism rule and asserts that a
# requisition for an XA part is ABSENT from the corpus.

MAX_REDIRECT_DEPTH = 5

def resolve_forecast_target(niin: str, installed_item_id: UUID | None) -> RedirectResult:
    """Resolve the NIIN against which demand for `niin` should be forecast.

    Lookup, in order — each step reads a LOCAL READ MODEL, never a synchronous
    call to the Registry (03 principle 2):

      1. Read the SMR source code for `niin` from the catalogue read model.
         Not `XA` -> return (niin, redirect_path=[]).  The common case is one read.

      2. Resolve the ASSEMBLY CONTEXT. Two cases, and they are not the same:
         a. `installed_item_id` known (the prediction-driven case): read the item's
            `position_id`, then that position's PARENT position from the
            configuration read model, then the installed item at the parent, then
            ITS niin.  Position hierarchy, not APL similarity: the physical parent
            is what gets replaced.
         b. `installed_item_id` unknown (a fleet-scope forecast): read the parent
            APL for `niin` from the COSAL read model — SNSL Part III Section A
            carries the MANY-TO-MANY part-to-equipment linkage (07 §4.2), so this
            can yield several candidate assemblies.  Redirect to EACH, apportioning
            demand by installed population, and record the fan-out in
            `redirect_path`.  Collapsing a many-to-many linkage to one arbitrary
            parent is the silent-corruption failure 03 §14 warns about in the
            taxonomy crosswalk, and the same rule applies here: CARRY THE
            AMBIGUITY AS DATA.

      3. If the resolved NHA is ITSELF `XA`, recurse. Depth is capped at
         MAX_REDIRECT_DEPTH.

      4. If no non-XA ancestor exists within the cap, or the hierarchy is
         incomplete, DO NOT silently forecast against the XA NIIN.  Emit
         `urn:fathom:problem:supply:no-forecastable-nha` on the query path, record a
         data-quality finding for the remediation path (03 §13), and publish NO
         forecast for that NIIN.  A forecast against an XA part is the defect 13
         §12.3 asserts absent; publishing one to avoid a gap is worse than the gap.
    """
```

**Quantity conversion, flagged as an engineering rule rather than a documented Navy one.** One predicted XA failure yields demand for **one** next-higher assembly, **deduplicated per (NHA installed item, forecast window)**: two XA failures on the same assembly within one window produce one assembly demand, because the assembly is replaced once. Document 07 documents the *redirect*; it does not document the arithmetic. The rule is recorded in the data card and as **OQ-S4** (§14), and it is marked in the response as `redirect_quantity_rule: "one_per_assembly_per_window"` so a consumer is never guessing.

Every redirected forecast carries `redirected_from_niin` and `redirect_path[]`. A planner who sees demand appear against a gearbox must be able to see that it originated from a bearing prediction, or the number is unexplainable and will be discarded — the same failure mode document 04 §6 records for unexplained optimizer output.

### 5.4 `PB` and `PG` — where the documented formula gives the wrong answer

This is the strongest single point in the platform's supply value story, and it is worth stating precisely because it is a place where the Navy's own documented computation and the platform's contribution visibly diverge.

Document 07 §4.7: **`PB` insurance and `PG` sustained life support** have *"little or no demand history. Exactly where prediction has the highest value."*

Now apply document 07 §4.3's documented allowance computation to such an item:

```
BRF  = fleet-reported 3-M usage           ->  ~0 for an insurance item, by definition
UR   = POP x BRF / 4                      ->  ~0
Rule:  "May be excluded" where UR < 0.125 ->  the item is a candidate for EXCLUSION
```

**The documented formula, applied faithfully, recommends excluding precisely the items whose absence is least tolerable.** That is not a criticism of the formula — it is a demand-history estimator and it is reporting, correctly, that there is no demand history. It is the exact gap a condition-based prediction fills, and the platform's contribution is to supply a demand signal where fleet-reported usage cannot.

API consequences, and they are why `PB`/`PG` items are **flagged differently** rather than merely forecast differently:

| Field | Value for `PB`/`PG` | Why |
|---|---|---|
| `forecast_basis` | `low_history_high_value` | Declared, not inferred |
| `prediction_value_class` | `"high"` | The consumer-visible statement that this is where the platform earns its place |
| `baseline_disposition` | `"may_exclude"` where `UR < 0.125`, **always returned** | The comparison is the point. Suppressing the baseline because it looks wrong hides the argument |
| `baseline_conflict` | `"baseline_excludes_item"` | An explicit flag that baseline and model disagree in direction, not degree |
| `sharp_estimate_permitted` | **`false` unless the underlying `FailurePrediction` supports it** | See below |
| `reference_class`, `calibration_population` | Carried through from the prediction | 03 §7.1 |

**The discipline that keeps this honest.** A `PB` item has little history, so its calibration cell is thin, so document 03 §7.1's gate applies: below `calibration_population = 50` PdM publishes no calibrated `p_failure` at all, `reference_class` is forced to `class_estimate`, and only `population_hazard_rate` is available. A demand forecast that renders a sharp expected quantity from that input has manufactured precision. So `sharp_estimate_permitted` is `false`, `expected_demand_p50` is `NULL` (the CHECK in §2.8 enforces it), and the response carries the population rate, the baseline, and the conflict flag.

That is a *less* impressive-looking number and a *more* defensible product. The alternative — a confident quantity for an insurance item with no history — is the demonstration failure mode document 06 §8's assumption A1 warns about, arriving through the supply door instead of the telemetry door.

### 5.5 Recoverability `D`/`L` — carcass flow, not consumption

Document 07 §4.7: *"Recoverability `D` or `L` means a depot-level repairable — a carcass and rotable-pool problem, not a consumption problem. `Z` means a true consumable. **The demand model must branch here.**"* Document 13 §7.2 makes it a required realism rule: *"a repairable that is generated as a consumption is the error a logistician spots first."*

| Recoverability | Tracking | Demand arithmetic |
|---|---|---|
| **`D`** or **`L`** — depot-level repairable | `CarcassObligation` (§2.8), **not** a consumption record. Advice `5G`/`5S`/`5R`/`5D`/`5A`; turn-in **`BC1`**; condition **`F → M → A`**; purpose code **A → V/W** with status **`RV`**; tracking job **`JSL326`** | **Net demand = predicted removals − expected carcass returns × repair yield.** A rotable pool's requirement is the *net* of the loop, not the gross removal count. `carcass_adjusted = true` |
| **`Z`** — true consumable | Ordinary consumption against `on_hand_qty` | Gross predicted removals |

Two supporting rules:

- **`5S` remain-in-place is a scheduling fact, not only a supply one.** A remain-in-place repairable cannot be landed until its replacement is on hand, so the reservation for the replacement gates the work window. This is one of the reasons lead time must be *queryable* rather than merely broadcast (§7).
- **The repair yield and turn-in rate are parameters, not constants in code.** They come from the generated corpus (13 §12) or from ingested history, and a hard-coded yield is the kind of invented quantity document 09 DO-NOT 31 forbids.

### 5.6 COG as the cross-check

Document 07 §4.6: *"COG is the single most important Navy-specific field in the supply model. It simultaneously encodes funding source, responsible inventory control point, and — with SMR recoverability — whether a carcass obligation exists."*

| First character | Funding | Effect here |
|---|---|---|
| `1, 3, 5, 7` | Navy Stock Account — requisitioner pays | Requisition carries a charge |
| `9` | Defense Stock Fund purchase held in NSA — pays | Requisition carries a charge |
| `2, 4, 6, 8` | Appropriations Purchase Account — issued without charge | No charge |
| `0` | Not carried in the stores account | Not a stock position |

Shipboard HM&E symbols used: **`2S`** major shipboard HM&E (NAVSEA, APA) · **`7H`** depot-level repairable shipboard and base equipment (NAVSUP WSS, NWCF) · **`3H`** field-level repairables · **`1H`** general consumables · `9N`/`9C`/`9G`/`9Z` Navy-owned DLA material · `0S` reactor plant technical manuals. Ninety-four symbols are in use; the demonstration distribution is weighted toward `2S`, `7H`, `3H`, `1H`, `9N`, which document 07 §4.6 calls defensible for shipboard HM&E.

**The cross-check, and it is a real control.** A `7_` COG indicates a depot-level repairable and SMR recoverability `D`/`L` indicates the same thing, from two independent fields. **A disagreement between them is a data-quality finding, never a silent choice.** The service records it to the remediation path (03 §13) with both values, and continues using the SMR recoverability as the operative value — because document 07 §4.7 names SMR as the authority for the demand branch. Picking one silently would mean a repairable is tracked as a consumable on some rows and not others, with nothing to indicate which.

`0S` reactor plant material is **excluded from the demonstration configuration entirely** — document 13 DO-NOT 14: NNPI is a materially more restrictive regime that *attaches the moment carrier or submarine propulsion-plant equipment is in scope*.

---

## 6. Predicted demand publication

Document 04 §7's third key decision: *the forward-looking demand signal derived from predictions and planned work is one of the more valuable products of the whole system and is exposed as a first-class resource rather than remaining an optimizer input. It is what connects predictive maintenance to provisioning.*

Document 07 §6 independently corroborates it with two findings that make this the strongest part of the program case: RAND documents that *"forecasting and filtering demand data"* was a Naval Operational Supply System requirement that **could not be satisfied** — demand forecasting is an explicitly documented Navy afloat-supply capability gap — and OPNAVINST 4790.16C ¶5.e.(2)–(3) **mandates** automated parts acquisition and asset pre-positioning from health-monitoring data. The capability is required by instruction and documented as unmet.

### 6.1 The baseline the platform improves upon

```
UR = POP × BRF / 4                                            [07 §4.3]
```

`UR` is the usage rate, `POP` the installed population, and **`BRF` the Best Replacement Factor — "the actual Fleet reported usage… as reported by fleet users and recorded in the 3-M system", updated annually.**

| Rule | Value | Where it appears |
|---|---|---|
| Carried as an on-board repair part | `UR ≥ 0.50` | `baseline_disposition = "carry"` |
| May be excluded | `UR < 0.125` | `baseline_disposition = "may_exclude"` |
| Price-sensitive sparing | Items ≥ **$2,000** spared at **4.0** | Applied where `unit_price_cents >= 200000` |
| CASREP add-back | One hit for a **Category 3 or 4** casualty in a class over **two years**, items **< $10K**, flagged **Allowance Derivation Code `Y`** | The one documented Derivation Code value |

Sparing models named on the allowance record: `.5 Price Sensitive FLSIP Plus` · `.25 FLSIP` · `.10 MOD-FLSIP` · `RBS` · `TRIDENT`.

**Three build rules:**

- **The baseline is computed by the service, deterministically, with no model.** It is arithmetic over the Registry population read model and the BRF derived from `maintenance_action.recorded` parts consumption. It is not the Domino Job's output and does not depend on it. If the Job never runs, `GET /demand-forecast` still returns the baseline.
- **`POP` comes from the configuration read model, not from a constant.** Document 07 §5.5 notes that population is *"actual equipment count for large HM&E, or platform count for small HM&E such as pumps and valves"* — the choice is per-family and is carried on the equipment family from Reference Data, not decided in Supply's code.
- **`BRF` carries `baseline_brf_as_of` because it is updated annually.** A forecast that compares a current model figure against a two-year-old BRF and does not say so is not a comparison. Document 13 §12.1 generates a BRF revision precisely so the effect of a revision is visible.

### 6.2 The forecast resource and the endpoint

`GET /demand-forecast?niin=&horizon_days=` — **confirmed still present in document 04 §7's API table, `x-substitution: required`.** Verified against the current file, not assumed.

```
GET /api/v1/supply/demand-forecast?niin=LLC004821&horizon_days=90

200 OK
X-Classification: CUI
{
  "niin": "LLC004821",
  "scope": "niin_fleet",
  "horizon_days": 90,
  "as_of": "2026-08-04T06:00:00Z",

  "baseline": {
    "formula": "UR = POP * BRF / 4",
    "authority": "07 §4.3 (NAVSUP allowance computation)",
    "pop": 34, "brf": 0.21, "brf_as_of": "2026-01-01",
    "ur": 1.785,
    "disposition": "carry",
    "sparing_model": ".25 FLSIP",
    "price_sensitive": false
  },

  "forecast": {
    "expected_demand_p50": 2.4,
    "expected_demand_p90": 5.0,
    "forecast_basis": "forecastable_stocked",
    "smr": { "source_code": "PA", "recoverability": "Z" },
    "prediction_value_class": "standard",
    "sharp_estimate_permitted": true,
    "reference_class": "niin_fleet",
    "calibration_population": 118,
    "carcass_adjusted": false,
    "redirected_from_niin": null,
    "baseline_conflict": null
  },

  "pathway": {
    "recommended_instrument": "requisition",
    "codes": { "dic": "A0A", "advice_code": "2L", "urgency_of_need": "C" },
    "rationale": "need_date_within_procurement_lead_time",
    "authority": "07 §6 items 3-4"
  },

  "provenance": {
    "run_id": "…", "model_version": "…", "computed_at": "…",
    "baseline_epoch": 77, "prediction_refs": ["…"]
  },
  "classification": { "level": "CUI", "inherited_from": ["…"], "...": "..." }
}
```

**The `pathway` block is the operationally important part**, and it is computable from document 07 §6's four documented pathways rather than invented:

| Condition | Recommended instrument | Codes | Authority |
|---|---|---|---|
| Need within the procurement lead time; stock insufficient | Requisition | **`A0A`**, advice **`2L`**, UND **`B`**/**`C`**, forward RDD, linked by **JCN** | 07 §6 item 3 |
| `need_date − now > procurement_lead_time` | **Special Program Requirement** | **`DYA`** → **`DYK`**/**`PA`**, or **`PB`** held until procurement lead time from the support date → **`PR`** | 07 §6 item 4 |
| Protect stock for a specific asset or work package | Reservation or planned requirement | **`BRR`** or **`BPR`** with purpose code **`S`**; **`BFU`** on drawdown-date lapse | 07 §6 item 5 |
| Repairable | Carcass flow | **`5G`**/**`5S`**/**`5R`**, turn-in **`BC1`**, condition **`F→M→A`**, purpose A→V/W with status **`RV`**, job **`JSL326`** | 07 §6 item 6 |
| The allowance quantity should change structurally | Allowance revision proposal | OPNAV **4790/CK** → CDMD-OA → WSF → ASI (**`JSS117`**) → revised SNSL quantity with an updated **Derivation Code** | 07 §6 item 7 |
| The retail level should change | Level-setting preview | **`JSI205`** Trial Run (§6.3) | 07 §6 item 8 |

The decision rule for the first two rows is exact and mechanical: compare the need date against the procurement lead time from `GET /lead-times`. That is the whole reason `procurement_lead_time_days` is a distinct field from order-and-ship time (§7.1) — it selects the instrument.

Document 07 §6 item 10 records the counterfactual that makes the comparison meaningful: *absent prediction this becomes a **CASREP** and a priority 01–03 requisition.* The `pathway` block is therefore the difference between a planned `DYA` and an emergency.

### 6.3 The Trial Run form — landing in a shape the Navy already accepts

`GET /demand-forecast?niin=&horizon_days=&form=trial_run` returns the same forecast in the presentation form of **RSUPPLY Level Setting (`JSI205`) in Trial Run mode**, producing a **Reorder Review** shape (07 §6 item 8, NAVSUP P-732 ¶4.5, ¶5.13):

| Parameter | Documented value or rule |
|---|---|
| AMD base period | **6–24 months** |
| Demand Based Item qualification and retention | By period and frequency |
| Order and shipping time | From `GET /lead-times` |
| Safety level factor | Parameter |
| **Recomputation Test percentage** | **Suggested range 020–030** — *"designed to prevent massive adjustments in RO resulting from insignificant changes in AMD"* |
| Endurance levels | **1.0 = 30 days · 1.5 = 45 · 2.0 = 60 · 2.5 = 75** |
| Output | Revised **AMD**, **RO**, **RP**, as a Reorder Review listing |

**Trial Run mode is the Navy's own mechanism for previewing a level change before committing it**, which makes it the natural shape for a model-derived recommendation. `form=trial_run` is enumerated in the specification's `x-naming-carve-outs` as a projection of a singleton resource (03 §4's carve-out), not a second endpoint.

Note the Recomputation Test percentage does real work here: a model that jitters AMD slightly from run to run produces no RO change at all under a 020–030 test, which is a built-in stability filter the platform inherits for free rather than having to invent.

### 6.4 The write path — a scheduled Domino Job, through the API

Document 04 §7: *"Demand forecasting executes as a scheduled Domino Job, since it is a modeling activity, writing results back through this sub-application's API."* Document 09 DO-NOT 1 and finding **D10/C7** make the rest of it non-negotiable: *a Domino Job is an API client, never a database client.*

**`POST /demand-forecast-runs`** — bulk, idempotent, fenced. **This operation is added by this document; document 04 §7 specifies the `GET` and mandates the write-back but lists no write operation** (§7.5).

```
POST /api/v1/supply/demand-forecast-runs
Idempotency-Key: <uuid>                 # REQUIRED
X-Correlation-Id: <uuid>
X-Backfill: true                        # optional; suppresses live side effects (11 §2.8)

{
  "run_id": "…",
  "model_version": "…",
  "computed_at": "…",
  "baseline_epoch": 77,                 # FENCE: rejected 409 if superseded  [D3 pattern]
  "horizon_days": [30, 90, 180],
  "forecasts": [ { …DemandForecast…}, … ]      # batched; max_batch declared in the chart
}

201 Created  { "run_id": "…", "accepted": 4182, "rejected": 0, "state": "published" }
```

| Rule | Detail |
|---|---|
| **Bulk, idempotent, fenced** | 03 §4's bulk-write convention. Replay with the same `Idempotency-Key` produces one run |
| **Baseline fenced** | A run computed under a superseded `baseline_epoch` is rejected `409`, not stored. This is D3's defect — *"a long scoring job reads baseline B1, the baseline becomes B2 mid-run, and the job's stale result lands after the invalidation and wins"* — applied to forecasting rather than scoring |
| **Route** | `domino-compute` → **`gateway`** → `supply`. One sanctioned cross-namespace edge (09 §4.4.2), so caller identity is attached in one place |
| **Never SQL** | The Job holds no database credential. NetworkPolicy makes this an invariant, not a policy |
| **`X-Backfill: true` suppresses live side effects, not events** | Requisition creation and shortfall notification consult `SideEffectGate.suppressed_for_backfill()` and no-op; forecasts are still stored and events still publish with `replay: true` (11 §2.8, 03 §5.3, D30) |
| **Atomic per run** | A run is stored whole or not at all, in one transaction with its events. A half-published forecast run is the same class of defect as a half-committed reservation set |
| **No event is published for a forecast** | Document 03 §6 has no `demand_forecast.*` row for `supply`. Adding one is a document 03 change; this document does not make it silently. Consumers read the forecast; they do not subscribe to it. Recorded as **OQ-S5** (§14) |

### 6.5 The Derivation Code, and what the platform is allowed to write

Document 07 §4.2 calls the SNSL **Derivation Code** *"the single most demo-relevant field located in the entire study"* — *"a code used to reflect what determined the computed SNSL allowance"* — because *"a predictive system that writes a new derivation basis is filling a field the Navy already has."*

Its **value set is NOT PUBLICLY FOUND** (NAVSUP P-488, itself unlocated). Therefore, exactly as document 13 §12.2 specifies:

- Values come from the **reserved synthetic set**, with **one documented exception: `Y` for the CASREP add-back**, which document 07 §4.3 does publish.
- The reserved set is declared in the data card. Closing the gap is a named follow-up (**OQ-S7**; 07 §10 ranks NAVSUP P-488 among the three highest-return retrievals).
- **No value is invented outside the reserved set.** Document 13 DO-NOT 11 and document 07 §1 both forbid it, and a fabricated Derivation Code is recognised by a supply officer immediately.

**The write path is a proposal, and this is the design's centre of gravity for the supply value story.** A model-derived replacement factor produces a `proposed_allowance_qty` and a `proposed_derivation_code`.

A note on which proposal kind carries it. Document 03 §7.2's `kind` enum is closed — `anomaly_tag | work_candidate | requisition | interval_change | redesign_case | configuration_change | purge | rewrap` **[AMENDMENT — was restated as six, omitting the two added by amendment 03-2]** — and **none of them is an allowance revision.** An allowance-quantity change is a *structural* change, and document 07 §6 item 7 documents its path precisely: OPNAV **4790/CK** → CDMD-OA → WSF → ASI (**`JSS117`**) → revised SNSL allowance quantity with an updated Derivation Code. That path terminates in the Registry's allowance document, not in a Supply document. This document therefore does **not** invent a ninth proposal kind (which would be a document 03 §7.2 change, and C39's neighbourhood). Instead: where the revision yields an immediate materiel requirement it is expressed as a `requisition` proposal carrying advice code **`5D`** — *initial requirement or **increased allowance/stockage objective*** — and where it yields only a structural revision it is surfaced to the allowance authority through the documented 4790/CK path with no proposal at all. Recorded as **OQ-S12** (§14): document 03 §7.2's kind enum has no allowance-revision member, and the platform's single most demo-relevant output (§6.5's Derivation Code) therefore has no adjudication kind of its own.

Supply therefore:

1. Computes and stores `proposed_allowance_qty` and `proposed_derivation_code` on the `AllowancePosition`, with `proposal_basis_ref` pointing at the forecast run.
2. Raises a `requisition` `Proposal` for `supply_officer` adjudication — dual-control per §4.6 — carrying the proposed change, its basis, and the baseline comparison, wherever the revision yields an immediate materiel requirement.
3. On approval, expresses the increase as advice code **`5D`** — *initial requirement or increased allowance/stockage objective* — and surfaces the structural revision through the documented 4790/CK path to the allowance authority. **It does not write `allowance_qty`.** That field's authority is the Registry's `allowance.updated`, and Supply does not own allowance documents (§1.2).

The demonstration value is precise and worth naming: the platform's output lands as *a revised Derivation Code and a `5D` advice code inside a process the Navy already operates*, rather than as a dashboard figure requiring a new process to consume it.

---

## 7. The substitution-required surface, verified against the corrected catalog

Finding **D24**, second clause: *"the required Supply surface omits lead time, condition codes, and interchangeability, all of which the optimizer already depends on."* Document 03 §6's catalog has since been corrected — `part_availability.changed` now carries **`lead_time`, `condition_code`, interchangeable group** `[D6, D24]`.

**An event payload is not a query surface.** Document 03 principle 2 forbids synchronous cross-sub-application calls on a compute path, so Scheduling maintains a read model from events — but a read model can only project what it can also *rebuild*, and obligation 5 requires a `changed_since` read for exactly that reason. More directly: the optimizer must be able to **ask** about lead time and condition when re-solving after a rejected reservation set (§3.6), and an event it received three days ago is not an answer. So this section verifies, row by row, that every field the corrected catalog promises is reachable through an API **operation**.

### 7.1 Row-by-row verification against document 03 §6's Supply rows

| Catalog row and field | Event carries it | Query operation | Status |
|---|---|---|---|
| `part_availability.changed` — NIIN, location, on-hand | ✓ | `GET /availability?niin=&location=&asset_id=` (04 §7) | **OK** |
| — due-in | ✓ | `GET /availability` response; in-transit detail via `internal` | **OK** |
| — allowance position | ✓ | `GET /allowance-position?asset_id=&niin=` (04 §7) | **OK** |
| — **`lead_time`** `[D6, D24]` | ✓ | **`GET /lead-times?niin=&location=` (04 §7)** | **OK — present in document 04, verified against the current file.** D6's *"lead time is named as a hard constraint but exists in no Supply event or operation"* is closed on both sides |
| — **interchangeable group** `[D24]` | ✓ | **`GET /interchangeable-groups?niin=` (04 §7)** | **OK — present in document 04, verified** |
| — **`condition_code`** `[D24]` | ✓ | **NONE** | **GAP. Closed in §7.2** |
| `requisition.status_changed` — document number, NIIN, status, projected availability | ✓ | `GET /requisitions?asset_id=&niin=&status=`, `GET /requisitions/{id}` (04 §7) | **OK** |
| `allowance_shortfall.detected` — asset, NIIN, allowance vs on-hand, driver | ✓ | `GET /shortfalls?asset_id=` (04 §7) | **OK** |
| `reservation_set.confirmed` — set, NIIN quantities, expiry | ✓ | **NONE** | **GAP. Closed in §7.4** |
| `reservation_set.released` — set, cause | ✓ | **NONE** | **GAP. Closed in §7.4** |

**Result: two of D24's three named omissions were closed by document 04 §7's API table; the third — condition codes — was not.** Document 04 §7's aggregate table does say `StockPosition` is *"On-hand quantity by NIIN and location, **with condition code**"*, so the attribute is on the aggregate; but no operation filters on it, and document 04 specifies no response shape that exposes it. The attribute existed and the query did not, which is precisely the D24 pattern in miniature.

`GET /lead-times` and `GET /interchangeable-groups` needed no addition, and that is worth recording explicitly: the corrected catalog and the corrected API table agree on two of three, and this document's job on those rows was verification, not invention.

### 7.2 The condition-code gap — closed here

**Addition to document 04 §7, flagged.** `GET /availability` gains a `condition_code` filter and a **mandatory** per-condition-code breakdown in its response.

```
GET /api/v1/supply/availability?niin=LLC004821&asset_id=8f2b…&condition_code=A

200 OK
{
  "as_of": "2026-08-04T14:11:58.204Z",
  "positions": [
    {
      "niin": "LLC004821",
      "location_id": "d7c1…", "location_type": "onboard_storeroom", "asset_id": "8f2b…",
      "stock_epoch": 42,
      "by_condition": [                                   /* MANDATORY. Never an aggregate alone */
        { "condition_code": "A", "purpose_code": "A", "on_hand_qty": 6,
          "reserved_qty": 2, "available_qty": 4, "due_in_qty": 0 },
        { "condition_code": "F", "purpose_code": "V", "on_hand_qty": 3,
          "reserved_qty": 0, "available_qty": 3, "due_in_qty": 0 }
      ],
      "lead_time": { "order_and_ship_time_days": 12, "procurement_lead_time_days": 96,
                     "basis": "observed", "observed_n": 41, "as_of": "2026-07-31" },
      "unit_price_cents": 214900,          /* [AMENDMENT] 03 §6; the stock_item column (§2.1),
                                              never previously exposed on this event, though
                                              design-advisory's cost estimators have always cited it */
      "interchangeable_group_id": "ig-0f24",
      "allowance_position": { "allowance_qty": 4, "allowance_state": "authorized_and_held",
                              "derivation_code": "…", "sparing_model": ".25 FLSIP" },
      "smr": { "source_code": "PA", "recoverability": "Z" },
      "cog": "1H"
    }
  ],
  "next_cursor": null
}
```

**Why the breakdown is mandatory rather than optional.** An aggregate on-hand figure that silently sums condition **`A`** (serviceable) with condition **`F`** (the first state of the documented `F → M → A` carcass progression, 07 §6 item 6) tells the optimizer a part is available when it is a carcass awaiting induction. Three of six on hand and none of them serviceable is not "three available." That is exactly the class of error D24 names when it says the optimizer *already depends on* condition codes — and a response contract that permits the aggregate-only shape lets a conformant substitute make the mistake without failing a test.

So the contract term is: **`by_condition[]` is required and non-empty on every position; a bare `on_hand_qty` at the position level does not exist in the schema.** A consumer cannot accidentally read a condition-blind figure because there is none to read. The conformance suite asserts the field's presence and asserts that the sum of `by_condition[].available_qty` is the only availability figure the response contains (§9.3).

`condition_code` and `purpose_code` are both accepted as repeatable filters, because purpose code partitions stock and earmarking (07 §4.9) and an optimizer drawing against purpose code `S` earmarked stock is doing something different from drawing general stock.

### 7.3 The consistent-snapshot batch query — added

**Addition to document 04 §7, flagged.** `POST /availability/query`, `x-side-effects: none`, `x-substitution: required`, `x-agent-eligible: true`.

Two independent reasons, either sufficient:

1. **D6's first clause.** *"Neither a consistent snapshot nor atomic reservation."* The atomic reservation is §3; the consistent snapshot is this operation. Per-key `GET` calls read at different instants and cannot produce the one `as_of` and the epoch set the fence in §3.7 requires.
2. **Scale.** An availability read over 250 candidate keys as 250 `GET` requests is not a query surface, and the sanctioned computational-`POST` pattern exists in document 03 §4 and §4.1 for exactly this shape. It is `x-side-effects: none`, so it is agent-eligible — which is what lets the Supply Expediter and Work-Package Planner agents ask the question at all (C1/D11: eligibility follows the declared side-effect class, not the HTTP method).

```
POST /api/v1/supply/availability/query
{
  "keys": [ { "niin": "LLC004821", "location_id": "d7c1…" }, … ],   /* max_keys, declared */
  "include": ["lead_time", "interchangeable_group", "allowance_position", "smr"]
}

200 OK
{
  "as_of": "2026-08-04T14:11:58.204Z",     /* ONE instant, one read-only transaction */
  "snapshot_consistency": "single_transaction",
  "positions": [ /* the §7.2 shape, per key, each with its stock_epoch */ ],
  "missing_keys": [ /* keys with no stock_key row — reported, never silently dropped */ ]
}
```

Three contract terms:

- **The read executes in one read-only transaction.** `snapshot_consistency: "single_transaction"` is an assertion a substitute must be able to make truthfully, and the conformance suite verifies it behaviourally: a driver mutates stock mid-query and asserts the response is internally consistent (§9.3).
- **`missing_keys` is explicit.** A key silently absent from `positions` is indistinguishable from zero stock, and those are different facts with different remedies.
- **Every `stock_epoch` in the response is directly usable as `expected_stock_epoch`** in a subsequent reservation set. The fence is only usable if the tokens come from a snapshot; this is the operation that supplies them.

### 7.4 Reservation-set read and extend operations — added

**Additions to document 04 §7, flagged.** Document 04 lists only `POST /reservation-sets` and `DELETE /reservation-sets/{id}`.

| Operation | Substitution | Reason |
|---|---|---|
| `GET /reservation-sets/{id}` | Required | Scheduling holds a `ReservationSet` aggregate (04 §6) and must read its state — expiry in particular — without waiting for an event. A consumer that can only learn a set expired by receiving `reservation_set.released` cannot answer "is my hold still good?" at plan time |
| `GET /reservation-sets?asset_id=&state=&changed_since=&cursor=` | Required | **Obligation 5 is unconditional:** a `changed_since` read over *every* aggregate a declared consumer projects. `maintenance` is a declared consumer of both reservation-set events (03 §6), so it projects the aggregate, so the read is mandatory. Its absence would mean Scheduling's read model has no rebuild path — D5, reintroduced through the one aggregate D6 exists to fix |
| `POST /reservation-sets/{id}/extend` | Required | Without it, a work package awaiting adjudication must hold an unbounded reservation, defeating the TTL that bounds orphan lifetime, **or** release and re-reserve — reintroducing the race at the exact moment of approval, when `work_package.approved` must be *"published only after reservation confirmation"* (03 §6). One trivially implementable operation removes a designed-in failure |

```
POST /api/v1/supply/reservation-sets/{id}/extend
If-Match: "3"                    # required: extension is a state transition
Idempotency-Key: <uuid>
{ "ttl_seconds": 3600 }

200 OK  { "reservation_set_id": "…", "state": "confirmed", "expires_at": "…",
          "extend_count": 1, "extends_remaining": 7 }
```

Extension rules: permitted only from `confirmed`; `extend_count` capped at 8 (the CHECK in §2.6) so an extension loop cannot become an unbounded hold by another route; a set already `expired` returns `409` `reservation-set-expired` and **is not resurrected** — resurrection would require re-verifying every line's availability, which is a new reservation set by definition; `expires_at` recomputed server-side from `clock_timestamp()`; and `reservation_set.confirmed` is **not** re-emitted — an extension changes expiry, not confirmation. A superseding event type would need a document 03 §6 catalog row, and this document does not add one silently (**OQ-S6**, §14).

### 7.5 The forecast write path — added

**Addition to document 04 §7, flagged.** `POST /demand-forecast-runs`, specified in §6.4.

Document 04 §7's API table lists `GET /demand-forecast` as required and its plane-placement paragraph mandates that the Domino Job write *"back through this sub-application's API"* — but names no operation. The two statements are jointly unimplementable: there is a mandated write with no write surface. Marked `required` rather than `internal`, deliberately: a substitute that cannot accept the program's forecast writes breaks the capability document 04 §7 calls *"one of the more valuable products of the whole system,"* and the program's forecasting Job is a declared client. A partner assuming Supply must be able to receive our forecasts even if it also produces its own.

### 7.6 The complete required surface — closed

**This table is the substitution contract.** Adding a row requires an ADR and a change to this document (§1.3).

| Operation | `x-substitution` | `x-side-effects` | Agent-eligible | Source |
|---|---|---|---|---|
| `GET /availability?niin=&location=&asset_id=&condition_code=&purpose_code=&changed_since=&cursor=` | required | none | yes | 04 §7; `condition_code`/`purpose_code` **added §7.2** |
| `POST /availability/query` | required | none | yes | **Added §7.3** |
| `GET /allowance-position?asset_id=&niin=&changed_since=&cursor=` | required | none | yes | 04 §7 |
| `GET /requisitions?asset_id=&niin=&status=&changed_since=&cursor=` | required | none | yes | 04 §7 |
| `GET /requisitions/{id}` | required | none | yes | 04 §7 |
| `POST /reservation-sets` | required | state-changing | **no** | 04 §7 |
| `GET /reservation-sets/{id}` | required | none | yes | **Added §7.4** |
| `GET /reservation-sets?asset_id=&state=&changed_since=&cursor=` | required | none | yes | **Added §7.4** |
| `POST /reservation-sets/{id}/extend` | required | state-changing | **no** | **Added §7.4** |
| `DELETE /reservation-sets/{id}` | required | state-changing | **no** | 04 §7 |
| `GET /lead-times?niin=&location=` | required | none | yes | 04 §7 — **D6/D24 verified present** |
| `GET /interchangeable-groups?niin=` | required | none | yes | 04 §7 — **D24 verified present** |
| `GET /shortfalls?asset_id=&changed_since=&cursor=` | required | none | yes | 04 §7 |
| `GET /demand-forecast?niin=&horizon_days=&form=` | required | none | yes | 04 §7 — **verified present** |
| `POST /demand-forecast-runs` | required | state-changing | **no** | **Added §7.5** |
| `POST /proposals` (requisitions, expedites) | required | proposal-only | **yes** | 04 §7 |
| `POST /proposals/{id}/claim`, adjudication | required | state-changing | no | 03 §7.2 |
| Stock adjustment, receipt, issue, document creation, catalogue synchronisation, requisition status ingest, supply-effectiveness metrics, reaper administration | internal | state-changing / none | no | 04 §7 |

`x-agent-eligible` appears **only** where `x-side-effects` is `none` or `proposal-only` (03 §8.1), verified by `tools/check_openapi.py` and by `assert_operation_annotations` at startup. Note that `POST /reservation-sets` is state-changing and therefore **not agent-eligible**: an agent may query availability and propose a requisition, but it cannot hold fleet stock. The Supply Expediter agent's surface is the read operations plus `POST /proposals`.

**Naming carve-outs**, enumerated per document 03 §4 and C23: `availability` and `allowance-position` and `demand-forecast` are query-projection singletons; `POST /availability/query` and `POST /reservation-sets/{id}/extend` are sanctioned sub-resource actions with `x-side-effects` declared.

### 7.7 `changed_since` coverage — obligation 5, completely

| Aggregate | Declared consumer projecting it (03 §6) | `changed_since` read |
|---|---|---|
| `StockPosition` / availability | `maintenance`, `fleet-status`, `design-advisory` | `GET /availability?changed_since=` |
| `AllowancePosition` | `maintenance`, `fleet-status` | `GET /allowance-position?changed_since=` |
| `Requisition` | `maintenance`, `fleet-status` | `GET /requisitions?changed_since=` |
| Shortfalls | `maintenance`, `fleet-status` | `GET /shortfalls?changed_since=` |
| `ReservationSet` | `maintenance` | `GET /reservation-sets?changed_since=` **(added §7.4)** |
| `DemandForecast` | none declared in 03 §6 | `GET /demand-forecast` serves current state; no consumer projects it |

Cursor-paginated, no total count, and **the event bus is never a rebuild source** (03 §5.1, D5). This table is the rebuild path, and document 03 §10 item 5 makes a substitute's ability to serve history through `changed_since` a condition of write cutover: without it, cutover leaves every consumer unable to rebuild.

---

## 8. Events published and consumed

### 8.1 Published

| Event | Topic | Scope / partition key | Compaction key |
|---|---|---|---|
| `part_availability.changed` | `fathom.supply.part_availability.v1` | `niin` / `niin` | **`(niin, location)`** — named explicitly by 03 §5.1 |
| `requisition.status_changed` | `fathom.supply.requisition.v1` | `asset` / `asset_id` | `document_number` |
| `allowance_shortfall.detected` | `fathom.supply.allowance_shortfall.v1` | `asset` / `asset_id` | `(asset_id, niin)` |
| `reservation_set.confirmed` | `fathom.supply.reservation_set.v1` | `asset` / `asset_id` | `reservation_set_id` |
| `reservation_set.released` | `fathom.supply.reservation_set.v1` | `asset` / `asset_id` | `reservation_set_id` |
| `proposal.created`, `proposal.adjudicated`, `proposal.expired` | `fathom.supply.proposal.v1` | per 03 §7.2 | `proposal_id` |

`part_availability.changed` is **NIIN-scoped, not asset-scoped** — which is exactly the case C11 was raised about and document 10's `EventScope` docstring cites by name. `subject.niin` carries the one required identifier; `location` is in the payload, not the subject, because the envelope's `scope` enum has no location member.

`allowance_shortfall.detected` carries a typed `driver`: `allowance_revision` · `stock_depletion` · `predicted_demand` · `casrep_risk`. A shortfall raised because a prediction created forward demand is a different fact from one raised because the COSAL revision increased the allowance, and Fleet Status renders them differently.

### 8.2 Consumed

Exactly document 04 §7's list, every type named explicitly — **no wildcard subscriptions** (C38):

`work_candidate.created` · `work_order.opened` · `work_package.proposed` · `work_package.approved` · `maintenance_action.recorded` · `prediction.updated` · `prediction.invalidated` · `casrep_risk.raised` · `installed_item.installed` · `installed_item.removed` · `installed_item.identity_resolved` **[AMENDMENT — this service is a declared 03 §6 consumer (04 §7) but the list previously omitted it]** · `allowance.updated` · `configuration.baseline_changed`

| Event | What Supply does with it |
|---|---|
| `configuration.baseline_changed` | **The most consequential event in the system** (03 §6). **[AMENDMENT]** Resolves `changed_items` vs `changed_items_ref` first (20 §6.2 — exactly one is set; a bulk allowance import is always the ref form, never inline). Re-evaluates APL authorization and allowance position for affected items; bumps the local `baseline_epoch`; invalidates forecasts computed under the superseded epoch. Inbox semantics are D2-critical here |
| `allowance.updated` | Replaces `allowance_qty`, `derivation_code`, `sparing_model`, `cosal_revision` **as received**. Recomputes `allowance_state`; emits `allowance_shortfall.detected` where the revision creates one, with driver `allowance_revision` |
| `installed_item.installed` / `.removed` | Updates the installed population feeding `POP`. **`removed` with a failure indicator and a repairable SMR opens a `CarcassObligation`** |
| `installed_item.identity_resolved` | `resolution: superseded` — re-key the installed population and any open `CarcassObligation` from `provisional_id` to `canonical_id`; `confirmed` — no-op |
| `maintenance_action.recorded` | Parts consumed → stock issue, reservation-set `consumed` transition, and the **BRF** input. This is where the documented loop closes: 3-M usage → BRF → allowance |
| `prediction.updated` / `.invalidated` | Forecast inputs. `invalidated` withdraws the affected forecast rather than leaving a stale one; the withdrawal is visible in the next `GET /demand-forecast` |
| `casrep_risk.raised` | Raises forecast urgency. **Does not create a requisition** — the counterfactual in 07 §6 item 10 is that absent prediction this *becomes* a CASREP; a risk flag is not a casualty and does not earn priority 01–03 |
| `work_package.proposed` / `.approved` | Reservation-set correlation and shortfall context |
| `work_candidate.created` / `work_order.opened` | Forward demand signal ahead of a work package |

**Consumer discipline, per document 11:**

- **Inbox records receipt and applies state in one transaction.** Only rows with `processed_at` set suppress redelivery. Applied to `configuration.baseline_changed`, the wrong order silently prevents allowance and APL-authorization re-evaluation (D2).
- **Antecedent rule.** An event whose `baseline_epoch` is ahead of the local configuration read model is **blocked** until the antecedent is applied (D3/D4).
- **Ordering and dedup on `(producer, producer_node, monotonic_seq)` or the HLC — never `source_time`** (D29).
- **`replay: true` events are handled idempotently and raise no operator-visible alert**, and generate **no requisition** — document 03 §5.3 names requisitions among the live side effects replay must not fire (D30).

### 8.3 Catalog reconciliation — verified

`src/fathom_supply/events/catalog.py`'s `PUBLISHES` and `CONSUMES` frozensets **equal** `helm/values.yaml`'s `events.publishes`/`events.consumes` **equal** document 03 §6's rows for `supply`, in both directions. `python tools/check_event_catalog.py` exits 0.

Verified while writing this document: **document 03 §6 and document 04 §7 agree exactly for `supply`, in both directions.** Five published events, twelve consumed, no undeclared dependency, no declared consumer absent. Given that C3 found 21 declared consumers not shown consuming and C4 found four undeclared dependencies elsewhere, the agreement here is worth asserting rather than assuming — it means Supply's consumer-driven suites (§9.4) are all buildable.

---

## 9. Testing and the conformance suite

Document 04 §7: *"The primary substitution candidate and the reference case for the protocol in document 03 §8"* — read §10, per document 09 correction 7.

### 9.1 The obligation split — D24's remedy, applied

Finding **D24**, first clause: *"No partner can pass the conformance suite. Several obligations — transactional outbox, inbox, per-log-line correlation IDs, owning exactly one database — are internal implementation properties unobservable from outside a black box and therefore unconformable by an executable suite. Either the obligation is unenforceable, or it is enforceable and no partner qualifies."*

Document 03 §10 and §15 supply the split. Applied to Supply, exhaustively:

**Contract terms — in `packages/contracts/conformance/supply/`, binding on every implementation including a substitute:**

| # | Obligation | How it is observed |
|---|---|---|
| 1 | OpenAPI 3.1 published, `x-substitution` and `x-side-effects` on every operation | Spec fetch and validation |
| 2 | **No state change without its event** | Fault injection (§9.3) — **not** "implements an outbox" |
| 3 | Canonical identifiers accepted and returned; no local surrogate exposed | Request/response inspection |
| 4 | Classification labels on every response and event; `inherited_from` on derived values | Response and envelope inspection |
| 5 | `changed_since` reads over the six aggregates in §7.7 | Cursor walk with concurrent mutation |
| 6 | `Idempotency-Key`, `ETag`/`If-Match`, `X-Correlation-Id` echo | Direct exercise |
| 7 | Authorization enforced locally against ABAC attributes | Call with a token lacking the attribute; expect 403 from the service, not the gateway |
| 8 | `x-agent-eligible` only where side effects are `none`/`proposal-only` | Spec inspection |
| 9 | Provenance on every derived value published | `GET /demand-forecast` provenance block; allowance proposal basis |
| 10 | **Reservation-set atomicity, TTL, and release semantics** | §9.3 — the Supply-specific core |
| 11 | **`by_condition[]` present and non-empty; no condition-blind aggregate exists** | Schema and response assertion (§7.2) |
| 12 | **`lead_time` and `interchangeable_group` reachable by operation** | Direct call — D24's remedy, tested |
| 13 | **Snapshot internal consistency** under concurrent mutation | §9.3 |
| 14 | Inbox crash semantics — redelivery still applies the state change | Observable, therefore a contract term even though the inbox mechanism is not (doc 10 §6.6) |

**Program implementation standards — asserted in `services/supply/tests/`, never in the conformance suite:**

| # | Obligation | Why it cannot bind a substitute |
|---|---|---|
| 11 | Transactional outbox via `packages/py-sync` | Unobservable from outside. Replaced by contract term 2's observable property |
| 12 | Consumer inbox mechanism | Unobservable. Its *effect* is contract term 14 |
| 13 | Exactly one logical database | Unobservable. A partner ontology has no notion of it |
| 15 | `X-Correlation-Id` on every log line | Logs are not a contract surface |
| — | Deterministic byte-order lock acquisition (§3.4) | **Unobservable, and deliberately so.** The *outcome* — no orphans, no deadlock-induced spurious failures under concurrency — is contract term 10. A partner using serializable transactions, an ontology transaction, or a single-writer log satisfies it without our locks, and no test could tell |
| — | The `stock_key` epoch trigger | Same. The *epoch's monotonicity and fence behaviour* are observable; the trigger is not |
| — | The in-process reaper | Same. *That expiry happens, emits exactly one release event, and restores availability* is observable; how it is scheduled is not |

That last group is the discipline D24 demands, applied to this document's own most prescriptive content. §3.4 is written as a mandate for the program-built service and as a **worked example** for a substitute — and none of its mechanism appears in the conformance suite. Document 09 DO-NOT 28 states the rule; this table is what honouring it looks like when the mechanism is genuinely load-bearing and the temptation to test it is real.

### 9.2 The reference substitute — the conformance self-test

**A suite that no partner can pass is indistinguishable, from the inside, from a suite that any partner can pass.** The only way to know which one exists is to run it against something that is not the program's implementation.

```
packages/contracts/conformance/supply/
├── test_contract.py            # categories 1-2, from the harness (10 §6)
├── test_events.py
├── test_faults.py              # includes test_no_orphaned_reservation_after_partial_failure (10 §6.6)
├── test_reservation_sets.py    # §9.3 — Supply's core
├── test_required_fields.py     # D24: condition, lead time, interchangeability, BY OPERATION
├── consumers/
│   ├── maintenance/test_expectations.py       # owned by services/maintenance via CODEOWNERS
│   ├── fleet-status/test_expectations.py
│   └── design-advisory/test_expectations.py
├── reference-dataset/          # from data/synthetic (13); deterministic
└── reference-substitute/       # THE SELF-TEST
    ├── README.md               # "This is deliberately not our implementation."
    ├── adapter.py              # in-memory store; SERIALIZABLE-style single-writer;
    │                           # emits from a change feed, NOT an outbox;
    │                           # internal ids translated to canonical identity at the boundary
    └── conftest.py             # provides the same four fixtures as the real service
```

**The rules that give it teeth:**

1. **CI runs the suite twice** — once against `services/supply`, once against `reference-substitute`. Both must be green. `make conformance-supply` runs both; a green run against only the real service is not a passing build.
2. **The substitute shares no code with the service.** An import-contract test asserts `reference-substitute` imports nothing from `fathom_supply` and nothing from `fathom_sync`. It may import `packages/canonical-schemas` — the wire contract is shared by definition — and nothing else. Without this rule the substitute drifts into a thin wrapper and the test becomes theatre.
3. **It is deliberately differently built**, along the axes D24 names: no outbox (a change feed, so the fault-injection driver exercises document 03 §10's *"partner platform emitting from an ontology or a change-feed"* path); no inbox table; internal surrogate identifiers translated at the boundary, exercising document 03 §10 item 3's *"identity translation is the substitute's responsibility, not its consumers'"*; a single in-memory store, so one-database-per-service is meaningless to it.
4. **The D24 regression guard.** If the suite passes against the real service and fails against the substitute, the build fails with a message naming D24 and requiring one of two resolutions: the failing assertion is a genuine contract obligation and the substitute must implement it, **or** it is a program implementation standard that leaked into the suite and must move to `services/supply/tests/`. The second case is the regression D24 describes, and this is the only mechanism in the framework that catches it.
5. **It is not a mock of Supply's behaviour.** It implements the required surface against its own store, well enough to satisfy the contract. Its reservation atomicity comes from a single-writer lock over the whole store — a legitimate implementation at its scale and a completely different mechanism from §3.4. That difference is the evidence that §3.4 is not in the contract.

Test naming: `test_d24_reference_substitute_passes_the_same_suite`, so anyone who breaks it finds the finding — document 11 §1.3's convention.

### 9.3 Supply-specific conformance tests

`test_reservation_sets.py`. Each test names the half of D6 it closes.

| Test | Asserts |
|---|---|
| `test_partial_failure_creates_nothing` | A 40-line set with one infeasible line returns `409`; **zero** `reservation_set` rows; **zero** `reserved_qty` change on all 40 keys; **zero** events of any type. *"37 of 40 succeed"* is unreachable |
| `test_failure_response_reports_every_failing_line` | Three infeasible lines produce three `failed_lines` entries, not one, each with its reason and — for `insufficient_stock` — `lead_time_days` and `interchangeable_group_id` |
| `test_failure_response_carries_no_set_id` | `reservation_set_id` is `null` on `409` |
| `test_concurrent_overlapping_sets_exactly_one_wins` | Two 40-line sets sharing 20 keys with stock for one: exactly one `201`, one `409`, no orphan lines, and availability afterwards equals on-hand minus the winner's holdings exactly |
| `test_reverse_order_concurrency_does_not_deadlock` | Two sets over the same keys submitted in opposite caller order: no `40P01` deadlock surfaces as a `5xx`, and no `409` cites a database error. **This is the test that fails if the canonical ordering is dropped** |
| `test_strict_fence_rejects_stale_epoch` | A key mutated between snapshot and submission fails the line `stock_epoch_stale`, fails the set, and changes nothing |
| `test_fence_none_ignores_epoch` | `fence: "none"` succeeds against a moved epoch |
| `test_ttl_expiry_releases_once` | After `ttl_seconds`, state is `expired`; **exactly one** `reservation_set.released` with cause `expired`; availability restored; one `part_availability.changed` per affected key |
| `test_expiry_restores_exact_quantities` | Availability after expiry equals availability before creation, key by key |
| `test_delete_is_idempotent_and_emits_once` | Two `DELETE`s: `204`, `204`, and exactly one `reservation_set.released` |
| `test_delete_after_expiry_is_204_not_404` | A caller releasing an already-expired set gets `204`, no second event |
| `test_extend_moves_expiry_without_reconfirming` | `expires_at` advances; `extend_count` increments; **no** `reservation_set.confirmed` re-emitted |
| `test_extend_on_expired_set_is_409` | An expired set is not resurrected |
| `test_extend_cap_enforced` | The ninth extension is rejected |
| `test_stock_adjustment_releases_rather_than_violating_the_invariant` | An adjustment below outstanding reservations releases the necessary sets with cause `stock_shortfall`, newest first, emitting one release per set — and never produces negative availability |
| `test_availability_events_are_one_per_key_not_per_line` | 40 lines over 12 keys produce 12 `part_availability.changed` events |
| `test_oversell_is_impossible` | A direct attempt to reserve beyond on-hand fails; property-based over random interleavings |
| `test_snapshot_is_internally_consistent_under_mutation` | Stock mutated during `POST /availability/query`; the response reflects one instant |
| `test_missing_keys_are_reported_not_dropped` | An unknown key appears in `missing_keys`, never silently in neither list |
| `test_by_condition_is_mandatory_and_no_blind_aggregate_exists` | Every position carries non-empty `by_condition[]`, and the response contains no position-level `on_hand_qty`. **D24's condition-code remedy** |
| `test_lead_time_and_interchangeability_are_queryable` | `GET /lead-times` and `GET /interchangeable-groups` return the same values the event carries. **D24, both halves** |
| `test_und_a_rejected_for_predicted_requirement` | A prediction-driven requisition with UND `A` is `422` |
| `test_xa_requisition_rejected_with_nha_in_the_problem_body` | 07 §4.7 / 13 §12.3 |
| `test_licn_never_transacts` | 07 §4.8 |
| `test_requisition_proposal_requires_dual_control` | Single-signature approval is `422` at every blast radius (§4.6) |
| `test_not_apl_authorized_rejected` | D14's control (§4.5) |

Plus, from document 10 §6.6, already declared in the shared harness: `test_no_orphaned_reservation_after_partial_failure`, `test_no_state_change_without_its_event`, `test_convergence_after_broker_partition` (original `event_id` preserved), `test_inbox_semantics_survive_a_crash`, `test_idempotent_retry_after_interruption`.

**The reservation tests run against both implementations** (§9.2). That is what makes them evidence rather than self-assessment.

### 9.4 Consumer-driven suites

Three, one per declared consumer, owned by the consuming team via CODEOWNERS (10 §6.7). Document 10's `collect_missing_consumer_suites` fails the build on a declared consumer with no contributed expectations, so C3's unbuildable-test class cannot recur here.

**`consumers/maintenance/test_expectations.py`** — the important one, because Scheduling is why Supply exists:

| Expectation | Rationale |
|---|---|
| The optimizer uses `fence: "strict"` and Supply honours it | D6's snapshot half is only closed if the consumer actually fences |
| `reservation_set.confirmed` carries `expiry`, so the optimizer can bound its plan | 03 §6's payload summary |
| `reservation_set.released` carries `cause`, and `expired` is distinguishable from `released_by_caller` | A hold lost to a lapse and one released deliberately require different planner responses |
| `part_availability.changed` carries `lead_time` **and** it matches `GET /lead-times` | Lead time is a hard optimizer constraint (04 §6); a disagreement between event and query means the optimizer and the interface disagree about the same NIIN — the condition 03 §10's read-cutover step exists to prevent |
| `by_condition[]` is present, so condition `F` stock is never counted as available | §7.2 |
| `interchangeable_group_id` is present on availability and resolvable by operation | The optimizer's substitution path |
| A `409` reservation failure reports all failing lines with lead time | So one re-solve suffices |
| `GET /reservation-sets?changed_since=` rebuilds the projection | D5 |

**`consumers/fleet-status/`**: requisition status and shortfall driver classification reach readiness rollups with classification labels intact and `inherited_from` populated (D13 — a rollup that moves when a compartmented item's supply position changes is an aggregation event).

**`consumers/design-advisory/`**: `part_availability.changed` supports the parts-cost and availability inputs to a redesign case.

### 9.5 The shadow-migration exercise

Document 04 §7 recommends the demonstration exercise the shadow step *"against a mock partner adapter, which validates the substitution machinery at low cost and materially strengthens the platform narrative."* The `reference-substitute` **is** that adapter, so the exercise costs one scenario script rather than a new artifact.

Per document 03 §10's migration sequence:

1. **Shadow.** The substitute receives the same inputs. **Externally-effective commands are intercepted and suppressed: requisition creation and reservation confirmation must not be double-issued** (D25). The interception is asserted, not assumed: `test_shadow_suppresses_externally_effective_commands` fails if a shadow run produces a document number or a confirmed set. Document 10's `EXTERNAL_LEGAL_EFFECT_KINDS` and document 11 §7.1's `SERVER_AUTHORITATIVE_QUEUED` policy both name the same two operations, from opposite directions — the agreement is the sign the boundary is drawn in the right place.
2. **Dual publish.** Both implementations publish to `fathom.supply.*` under distinct `producer` and `producer_node` identities, with a declared cutover fence. `producer_node` is what keeps their `monotonic_seq` spaces from colliding (03 §5.4) — the field added in document 03's correction, load-bearing here for the first time.
3. **Read cutover.** Gateway reads move only once consumer read models are fed by the substitute's events, *"so the interface and the optimizer cannot disagree about the same NIIN."*
4. **Write cutover.** Gated on the substitute serving history through `changed_since` (§7.7), or on the incumbent's archive being retained in object storage indefinitely.
5. **Decommission.** Archive retained indefinitely, not for the topic retention period.

The demonstration exercises steps 1 and 2 and **stops there deliberately**: steps 3–5 require a partner that exists. What is validated is the machinery — interception, dual identity, fence, and the conformance certificate — which is what the narrative claims.

### 9.6 The rest of the pyramid

Per document 09 §4.2:

- **`tests/unit/`** — no I/O. SMR parsing (including the position-5 recoverability correction, §5.1), document-number construction, the F/AD × UND priority matrix, `UR = POP × BRF / 4` and its four thresholds, `allowance_state` derivation, NHA redirect including the many-to-many fan-out and the depth cap, canonical lock-key byte ordering.
- **`tests/integration/`** — real Postgres and Redpanda via testcontainers. The reservation transaction under genuine concurrency (the deadlock and interleaving tests are only meaningful here), the reaper, the epoch trigger, inbox antecedent blocking, migrations forward-only.
- **`tests/contract/`** — the six document 09 §4.2 files, unmodified.
- **`tests/conformance/`** — eight lines, collecting `packages/contracts/conformance/supply/` unmodified. **No shared test skipped, xfailed, or edited.**
- **Property-based tests** (Hypothesis) over random reservation/adjustment/expiry interleavings, asserting the two invariants that cannot be enumerated by example: `0 <= reserved_qty <= on_hand_qty` always, and every reservation-set row is in exactly one of the four states with a cause iff terminal.

---

## 10. Deployment

Per document 04 §7 and documents 09 and 11.

| Concern | Decision |
|---|---|
| Plane | **Sustainment Plane.** `services/supply/`, chart `helm/`, Argo CD Application under `deploy/argocd/` |
| **Edge profile** | **None. Enterprise only** (11 §1.2). Supply still implements outbox, inbox, and clock discipline without exception (03 §15.11) |
| `producer_node` | Always `enterprise`. There is no second instance of this slug, so the sequence space is single (03 §5.4) |
| Edge-originated requisitions | Queued by the **edge `sync` outbox** and submitted against Supply's API on reconnect with an `Idempotency-Key`, per 11 §7.1's `SERVER_AUTHORITATIVE_QUEUED`. **Never issued from the edge** — external legal effect. No edge Supply instance exists to queue them locally |
| Database | One CloudNativePG PostgreSQL cluster. Outbox and inbox colocated (11 §2.1). Alembic forward-only, `pre-upgrade,pre-install` hook, `backoffLimit: 0` |
| NetworkPolicy egress | `kube-dns`, own database, Redpanda brokers + schema registry, `auth`, `audit`, `reference-data`. **Nothing else.** No sub-application peer — 03 principle 2 |
| NetworkPolicy ingress | `gateway` only, plus the Prometheus scrape |
| Domino path | `domino-compute` → **`gateway`** → `supply` for `POST /demand-forecast-runs`. The one sanctioned cross-namespace edge (09 §4.4.2) |
| Container | Multi-stage; runtime non-root UID 65532, `readOnlyRootFilesystem: true`, `capabilities: drop: [ALL]`, digest-pinned bases, **nothing installed at container start** (D26) |
| Scaling | HPA on request rate. **The reaper runs in every replica** and is safe to: `FOR UPDATE SKIP LOCKED` makes concurrent reapers correct rather than merely tolerable |
| `/readyz` | Database, Alembic head match, broker, **read-model lag** (configuration, allowance, prediction), **outbox backlog**, and **reaper lag**. Degrades past the declared bounds |
| Metrics | `fathom_supply_reservation_sets_confirmed_total`, `..._rejected_total{reason}`, `..._expired_total`, `..._released_total{cause}`, `fathom_supply_reservation_reaper_lag_seconds`, `fathom_supply_lock_wait_seconds`, `fathom_supply_stock_epoch_conflicts_total`, `fathom_staleness_refusals_total` |
| Staleness bound | Declared in the README. Availability reads refuse to serve — `503`, incrementing `fathom_staleness_refusals_total` — when the configuration read model exceeds it, because an availability figure computed against a superseded baseline may reference items no longer installed (03 §15.14, D6) |
| Purge path | Declared per store (03 §13, D15). Stock ledger and requisitions are **operationally append-only** with envelope-level encryption and per-classification keys; crypto-shredding is the purge mechanism. Reservation sets are prunable after terminal state plus the declared retention |

---

## 11. Explicit DO-NOT list

Document 09 §9's thirty-two items apply in full. These are additional and Supply-specific; each carries the finding that makes it a defect rather than a preference.

| # | Do not | Why, and authority |
|---|---|---|
| **S1** | **Do not add a `pending`, `partial`, `reserving`, or `draft` state to `ReservationSet`.** | **D6.** The absence of that state is the fix. A state that can hold 37 of 40 lines is a state something will eventually leave a set in (§3.2) |
| **S2** | **Do not implement reservation as per-NIIN calls, a loop over single reservations, or a client-side batch.** | **D6** verbatim: *"reserves per-NIIN with no batch, no TTL, no two-phase confirm and no compensating release"* |
| **S3** | **Do not acquire `stock_key` locks in any order but canonical byte order, and do not replace the one-key-at-a-time loop with a single set-based `SELECT … FOR UPDATE … ORDER BY`.** | Postgres does not guarantee lock-acquisition order matches `ORDER BY` under every plan. The loop is the deadlock-freedom guarantee (§3.4) |
| **S4** | **Do not sort lock keys by a collated string.** | A collation difference between environments is a deadlock regression with no code diff (§2.3) |
| **S5** | **Do not relax `reserved_qty <= on_hand_qty`.** Handle the adjustment case by releasing sets, in the same transaction. | Relaxing it converts a loud transactional reconciliation into silent negative availability every consumer inherits (§3.10) |
| **S6** | **Do not emit `part_availability.changed` per line.** One per affected `(niin, location)`. | The event storm half of D6, on the success path |
| **S7** | **Do not emit `reservation_set.released` twice for one set.** | Scheduling would restore availability twice (§3.9) |
| **S8** | **Do not introduce a saga, orchestrator, distributed lock service, or cross-service two-phase commit for reservations.** | Its intermediate states *are* D6's orphans. Atomicity is local; the cross-service hold is a lease whose compensation is TTL expiry (§3.12) |
| **S9** | **Do not compute `expires_at` in application code, and do not accept it from the caller.** | One clock, the database's. A caller-supplied expiry is a lease with no authority (§3.8) |
| **S10** | **Do not use a wall clock for reaper scheduling, backoff, or any timer.** Expiry is a database predicate; timers are monotonic. | 03 §5.4, D29. STIG V-260520 mandates backward steps |
| **S11** | **Do not return a condition-blind `on_hand_qty`.** `by_condition[]` is mandatory and there is no position-level aggregate in the schema. | **D24.** Summing condition `F` with `A` reports a carcass as available (§7.2) |
| **S12** | **Do not treat an event payload as satisfying a query obligation.** Lead time, condition, and interchangeability must each be reachable by an operation. | **D24**: *"the required Supply surface omits lead time, condition codes, and interchangeability, all of which the optimizer already depends on"* |
| **S13** | **Do not generate UND `A`, or a priority designator of 01–03, for a prediction-driven requirement.** | **07 §4.5**: *a predicted failure is not yet "unable to perform."* A logistician notices immediately |
| **S14** | **Do not requisition an `XA` part.** Redirect to the next higher assembly, or publish nothing and record a data-quality finding. | 07 §4.7, 13 §12.3 asserts its absence (§5.3) |
| **S15** | **Do not collapse a many-to-many part-to-equipment linkage to one arbitrary parent during NHA redirect.** Carry the fan-out as data. | 07 §4.2's SNSL linkage is many-to-many. Same failure as flattening the taxonomy crosswalk (03 §14) |
| **S16** | **Do not slice SMR recoverability as positions 5–6.** It is position **5 only**. | 07 §9 records the two-position reading as a **wrong premise already corrected**. Reproducing it mis-classes every repairable |
| **S17** | **Do not model a repairable as a consumption.** Recoverability `D`/`L` opens a carcass obligation. | 07 §4.7; 13 §7.2: *the error a logistician spots first* |
| **S18** | **Do not silently resolve a COG-versus-SMR repairable disagreement.** Record it to the remediation path; use SMR as operative. | Otherwise the same NIIN is a repairable on some rows and a consumable on others, with nothing to say which (§5.6) |
| **S19** | **Do not write `allowance_qty` or the authoritative `derivation_code`.** The platform's figure is `proposed_*` behind a `supply_officer` adjudication. | §1.2, §6.5. Supply does not own allowance documents |
| **S20** | **Do not invent a Derivation Code, a condition code, or any code value document 07 records as NOT PUBLICLY FOUND.** Generate from the reserved set; `Y` is the one documented Derivation Code. | 07 §1, 07 §4.2, 13 §12.2, 09 DO-NOT 32. *Fabricated schema detail is worse than an acknowledged gap* |
| **S21** | **Do not assign per-code semantics to `BRA`, `BRC`, `BRF`, `BRS`, or `BRX`.** Store the family; interpret `BRR` only. | 07 §4.5 names the family and documents only `BRR`. OQ-S2 |
| **S22** | **Do not emit RDD `444`, `N__`, `E__`, unit of issue `ST`, or RIC `S9M`/`S9T`/`SMS`/`NRP`.** | 07 §4.5: NOT FOUND or affirmatively wrong |
| **S23** | **Do not let a LICN appear in any supply transaction.** | 07 §4.8, verbatim |
| **S24** | **Do not publish a sharp expected demand where the underlying reference class forbids one.** | 03 §7.1's calibration gate. For `PB`/`PG` items the thin cell is the norm, and a confident quantity there is manufactured precision (§5.4) |
| **S25** | **Do not suppress the `UR = POP × BRF / 4` baseline because it disagrees with the model.** The disagreement is the product. | 07 §4.3. For an insurance item the formula recommends exclusion, and showing that is the value story (§5.4, §6.1) |
| **S26** | **Do not let a Domino Job hold a database credential or write SQL.** Forecasts arrive at `POST /demand-forecast-runs`. | **D10/C7**, 09 DO-NOT 1 |
| **S27** | **Do not accept a forecast run computed under a superseded `baseline_epoch`.** | D3's defect, applied to forecasting (§6.4) |
| **S28** | **Do not create a requisition from a `replay: true` event, or from a `casrep_risk.raised`.** | 03 §5.3 names requisitions among the side effects replay must not fire (D30). A risk flag is not a casualty (§8.2) |
| **S29** | **Do not approve a `requisition` proposal on one signature, at any blast radius.** | 03 §7.2 — dual control for any kind with external legal effect (§4.6) |
| **S30** | **Do not skip APL authorization on a requisition proposal.** | **D14**. This is the control that stops a crafted corpus passage from producing a substituted NIIN with genuine citations (§4.5) |
| **S31** | **Do not put §3.4's lock protocol, the epoch trigger, or the reaper into the conformance suite.** Assert their observable outcomes. | **D24**, 09 DO-NOT 28. This document's own mechanism is the test case for the rule (§9.1) |
| **S32** | **Do not ship a green conformance run that only ran against `services/supply`.** Both targets, always. | **D24.** A suite never run against a non-program implementation carries no information about whether a partner could pass it (§9.2) |
| **S33** | **Do not add an operation to §7.6's required surface without an ADR and a change to this document.** | 04 §7's *"the required surface is deliberately minimal"* is a design property that erodes one convenience at a time |
| **S34** | **Do not generate reactor-plant or nuclear-propulsion material (`0S` COG) into the demonstration.** | 13 DO-NOT 14, 08 §5.6. NNPI attaches the moment propulsion-plant equipment is in scope |

---

## 12. Definition of Done

**Document 09 §8 applies in full — all seven subsections, every box, nothing removed.** Copy it into `services/supply/README.md` and tick it there. The gates below are **additional** and all CI-enforced.

### 12.1 The reservation-set protocol — D6

- [ ] `supply.reservation_set_state` contains **exactly** `confirmed`, `consumed`, `released`, `expired`. No `pending`, no `partial`. *(§3.2, S1)*
- [ ] `POST /reservation-sets` completes in **one** database transaction; no code path opens a second. Asserted by a static gate over `services/reservations.py`. *(§3.4)*
- [ ] Lock keys acquired **one at a time, in canonical byte order**, by the single sanctioned repository helper `lock_stock_keys()`. No other module issues `FOR UPDATE` against `stock_key`. *(§3.4, S3, S4)*
- [ ] Feasibility evaluated over **all** lines before any write. *(§3.4)*
- [ ] `reserved_qty <= on_hand_qty` present as a database CHECK and **not** relaxed. *(§2.3, S5)*
- [ ] Every event emitted through `packages/py-sync`'s `emit()` **in the same transaction**; **one** `part_availability.changed` per affected key. *(§3.11, S6)*
- [ ] `expires_at` computed server-side from the database clock; absent from the request schema. *(§3.8, S9)*
- [ ] Reaper in-process, `FOR UPDATE SKIP LOCKED`, one transaction per set, monotonic scheduling, lag on `/readyz` and `/metrics`. *(§3.8, S10)*
- [ ] `DELETE` idempotent and emits at most one release event per set. *(§3.9, S7)*
- [ ] Stock adjustment releases sets in the same transaction rather than violating the invariant. *(§3.10, S5)*
- [ ] Every test in §9.3 green **against both** `services/supply` and `reference-substitute`.

### 12.2 The required surface and D24

- [ ] §7.6's table is the OpenAPI document's `x-substitution: required` set, exactly — no more, no fewer. Asserted by `tools/check_openapi.py`.
- [ ] `by_condition[]` required and non-empty; **no position-level `on_hand_qty` exists in the schema**. *(§7.2, S11)*
- [ ] `GET /lead-times` and `GET /interchangeable-groups` return values consistent with `part_availability.changed`, asserted by test. *(§7.1, S12)*
- [ ] `POST /availability/query` returns one `as_of`, per-key `stock_epoch`, and explicit `missing_keys`; internally consistent under concurrent mutation. *(§7.3)*
- [ ] `changed_since` present for all six aggregates in §7.7.
- [ ] Every addition to document 04 §7 is listed in §1.4 and in the README's "extensions to document 04" section. **No silent divergence.**

### 12.3 Navy fidelity

- [ ] Document numbers are 14 characters per 07 §4.4, serial excluding `I` and `O`, built in one module. *(§4.1)*
- [ ] UND `A` and priority 01–03 unreachable for `driver = 'prediction'`, by CHECK **and** by API validation. *(§4.3, S13)*
- [ ] Advice code `2L` applied to prediction-driven abnormal quantity; the 5-series applied to the carcass path. *(§4.4)*
- [ ] SMR parsed as six positions with **recoverability at position 5 only**. *(§5.1, S16)*
- [ ] All five source-code branches implemented and exercised by the reference dataset. *(§5.2)*
- [ ] `XA` redirect implemented with the many-to-many fan-out, the depth cap, and the loud failure; no requisition for an `XA` NIIN is constructible. *(§5.3, S14, S15)*
- [ ] `PB`/`PG` flagged `prediction_value_class: "high"` with the baseline conflict surfaced and `sharp_estimate_permitted` honoured. *(§5.4, S24, S25)*
- [ ] Recoverability `D`/`L` opens a `CarcassObligation` with net-of-loop demand; `Z` consumes. *(§5.5, S17)*
- [ ] COG-versus-SMR disagreement recorded to the remediation path, never silently resolved. *(§5.6, S18)*
- [ ] `UR = POP × BRF / 4` computed with all four documented thresholds and the named sparing models, always returned. *(§6.1)*
- [ ] Trial Run form emits AMD/RO/RP with the Recomputation Test percentage and the documented endurance levels. *(§6.3)*
- [ ] Rejected-value sets enforced: RDD `444`/`N__`/`E__`, UI `ST`, RIC `S9M`/`S9T`/`SMS`/`NRP`, and LICN in any transaction. *(§4.3, S22, S23)*
- [ ] **No code value appears that document 07 does not verify.** Condition codes are `A`, `F`, `M` with `set_is_complete = false`; Derivation Codes come from the reserved set with `Y` the sole documented value; `BRA`/`BRC`/`BRF`/`BRS`/`BRX` carry no assigned semantics. *(§2.9, §4.2, §6.5, S20, S21)*

### 12.4 Substitution and conformance

- [ ] `packages/contracts/conformance/supply/` complete, with all five categories plus `test_reservation_sets.py` and `test_required_fields.py`.
- [ ] **`reference-substitute/` exists, shares no code with `fathom_supply` or `fathom_sync`, and passes the same suite.** `test_d24_reference_substitute_passes_the_same_suite` green. *(§9.2, S32)*
- [ ] `make conformance-supply` runs **both** targets; a single-target run is not a pass.
- [ ] §9.1's obligation split holds: no program implementation standard in the conformance suite; every contract term observable from outside a black box. *(S31)*
- [ ] All three consumer-driven suites contributed and green; `collect_missing_consumer_suites()` empty for `supply`.
- [ ] Shadow-mode exercise scripted, with `test_shadow_suppresses_externally_effective_commands` proving requisition creation and reservation confirmation are intercepted. *(§9.5)*
- [ ] Manifest tests green for the Supply Expediter manifest; every selected operation exists, is `x-substitution: required`, and is `x-agent-eligible`.

### 12.5 Governance

- [ ] `python tools/check_event_catalog.py` exits 0; `catalog.py` ≡ `values.yaml` ≡ document 03 §6's `supply` rows.
- [ ] README states purpose, the §2.1 aggregate table with conflict policy per aggregate, the staleness bound, sanctioned NetworkPolicy peers, the six extensions to document 04 §7, and every open question in §14 recorded as a local resolution.
- [ ] Every `[OPEN]` and `OQ-Sn` this document raises is recorded, not silently defaulted.

---

## 13. Corrections to source documents

Found while reconciling. Each is a **defect in the cited document**, not a decision of this one.

| # | Document | Defect | Correction | Status |
|---|---|---|---|---|
| 1 | **10 §—, `packages/canonical-schemas`** | `Niin = Annotated[str, StringConstraints(pattern=r"^\d{9}$")]` — all-numeric, nine digits. But document 13 §6.2's Block A mints **every** catalogue item as `FSC(4) ‖ "LL"(5–6) ‖ 7 alphanumeric`, so the 9-character item-identifier portion contains letters by construction, and document 07 §4.8 documents NICNs and LICNs as legitimate shipboard catalogue forms. **The canonical type rejects the entire synthetic catalogue.** Supply is where this surfaces first and worst: `stock_position`, `reservation_set_line`, and every requisition are NIIN-keyed | Relax to `^[0-9A-Z]{9}$` with the documented note that an all-numeric NIIN is an NSN and an alphabetic character in the NCB positions marks a Navy local item (07 §4.8); keep `Nsn` at `^\d{13}$`; and add a separate `transaction_eligible` attribute so **LICNs are excluded from transactions by data, not by regex** | **[AMENDMENT] Applied, differently.** `10-shared-packages.md` §4.1 resolved this to `^(\d{9}|[A-Z]{2}[A-Z0-9]{7})$` — narrower than this row's `^[0-9A-Z]{9}$` ask, constraining the letters to Block A's actual positions (1–2) rather than accepting a letter anywhere in the 9 characters — and `20-registry.md` §4.7/§4.9's CHECK constraints were reconciled to it in the same pass this row's own gap surfaced in. This document's DDL types `niin` as `text` with the constraint applied at the Pydantic boundary, unaffected by which exact pattern canonical settled on |
| 2 | **04 §7 API surface** | The corrected event catalog (03 §6) gives `part_availability.changed` **`lead_time`, `condition_code`, interchangeable group** `[D6, D24]`, and document 04 §7 added `GET /lead-times` and `GET /interchangeable-groups` — but **no operation exposes condition code**, and the aggregate table's *"with condition code"* is not a query surface. One third of D24's second clause is unclosed | Add `condition_code` and `purpose_code` filters and a mandatory `by_condition[]` response breakdown | **Applied in §7.2.** Document 04 §7 needs the edit |
| 3 | **04 §7 API surface** | Lists `POST /reservation-sets` and `DELETE /reservation-sets/{id}` but no `GET`. `maintenance` is a declared consumer of both reservation-set events and holds a `ReservationSet` aggregate (04 §6), so it projects the aggregate — and obligation 5 requires a `changed_since` read over **every** aggregate a declared consumer projects. As written, Scheduling's projection of the one aggregate D6 exists to fix has no rebuild path | Add `GET /reservation-sets/{id}` and `GET /reservation-sets?changed_since=` | **Applied in §7.4.** Document 04 §7 needs the edit |
| 4 | **04 §7** | The plane-placement paragraph requires demand forecasting to write *"back through this sub-application's API,"* but the API table contains no write operation. The two statements are jointly unimplementable | Add `POST /demand-forecast-runs`, bulk, idempotent, fenced | **Applied in §7.5.** Document 04 §7 needs the edit |
| 5 | **04 §7 Substitution posture** | *"The reference case for the protocol in document 03 §8."* Document 03 §8 is *Agent authority and tool surfaces*; the substitution protocol is **§10** | Read §10 | Not applied; flagged. Same inversion document 09 correction 7 records for 04 §12/§13 and 01 §8.0 |
| 6 | **03 §6, Supply rows** | `reservation_set.confirmed` and `reservation_set.released` are declared with `maintenance` as sole consumer, but **no catalog row covers a TTL extension**. An extension changes expiry, which Scheduling's projection holds. Either extension re-emits `confirmed` (semantically wrong — nothing was re-confirmed) or the projection goes stale until release | Add a `reservation_set.extended` row, or state that consumers re-read `GET /reservation-sets/{id}`. This document takes the second position and does not invent an event | Not applied; flagged as **OQ-S6** |
| 7 | **03 §7.2** | Does not enumerate the kinds with external legal effect, though `requires_dual_control` depends on the set. Document 10 derives `{requisition}` from §11 and §10 and records it as OQ-12 | Enumerate the set in §7.2 | Not applied; flagged as **OQ-S3**. `{requisition}` is operative for this slug |
| 8 | **07 §4.5** | Gives two overlapping third-character schemes for DIC values — positional semantics (`_1` requisitioner, `_2` supplementary addressee, `_6` ICP-to-storage, `_8` to DAAS, `_9` from DAAS) and media/type semantics (`A` domestic NSN, `B` domestic part number, `1` overseas NSN) — without stating which applies to which family. §6 item 3's `A0A` is consistent with the second reading for the `A0_` family | State the applicable scheme per family | Not applied; flagged. This document uses `A0A`/`A0B` on document 07 §6's own worked example and asserts nothing further |
| 9 | **03 §7.2 `kind` enum** | The closed enum — `anomaly_tag \| work_candidate \| requisition \| interval_change \| redesign_case \| configuration_change \| purge \| rewrap` **[AMENDMENT — restated as six here; the enum has had eight members since amendment 03-2]** — has **no allowance-revision member**, yet document 07 §4.2 calls the SNSL Derivation Code *"the single most demo-relevant field located in the entire study"* precisely because *"a predictive system that writes a new derivation basis is filling a field the Navy already has."* The platform's most demo-relevant supply output therefore has no adjudication kind of its own, and document 07 §6 item 7's documented 4790/CK → CDMD-OA → WSF → ASI path terminates in a Registry document rather than a Supply one | Either add an `allowance_revision` kind to §7.2 with a `supply_officer` minimum in §7.2.1, or state that allowance revisions route through the Registry's `configuration_change` kind | Not applied; flagged as **OQ-S12**. **No ninth kind is invented here** — that would be C39's neighbourhood. Interim: a `requisition` proposal with advice `5D` where there is a materiel requirement, and the 4790/CK path with no proposal where the change is purely structural |
| 10 | **12 §1.3** | Places *"general enumerations"* with Reference Data but out of scope, leaving condition codes, purpose codes, advice codes, COG, DIC, SMR, and unit of issue with an owner and no server. Supply cannot validate against a surface that does not exist | Assign the general-enumeration surface a build document | Not applied; flagged as **OQ-S1**. Interim: typed enums in `packages/canonical-schemas` from document 07's verified values, each with `set_is_complete` |

---

## 14. Open questions

Recorded rather than resolved with an invented value. Each blocks something specific.

| ID | Question | Blocks | Interim position | Owner |
|---|---|---|---|---|
| **OQ-S1** | Which document owns the **general code-set surface** on Reference Data — condition, purpose, advice, COG, DIC, SMR, unit of issue? | Validation against an authoritative source; nothing in the demonstration | Typed enums in `packages/canonical-schemas` generated from document 07's verified values, each carrying `set_is_complete = false` where document 07 records the set as partial. Supply reads Reference Data when the surface exists | Program / architecture |
| **OQ-S2** | The individual meanings of **`BRA`, `BRC`, `BRF`, `BRS`, `BRX`** in the MILSTRIP reservation lifecycle. Document 07 names the family and documents only `BRR` | Full documentary fidelity of the reservation lifecycle | Family membership stored; per-code semantics assigned to `BRR` only; the other five recorded without interpretation. **No meaning invented** | Engineering research (NAVSUP P-485 Vol II, ranked second in 07 §10) |
| **OQ-S3** | Enumeration of the **external-legal-effect proposal kinds** in document 03 §7.2 | Nothing; `{requisition}` is unambiguous for this slug | Every `requisition` proposal is dual-control at every blast radius | Program, per document 10's OQ-12 |
| **OQ-S4** | The **quantity rule for an XA→NHA redirect**. Document 07 documents the redirect, not the arithmetic | Nothing hard; the rule is declared in the response | One NHA per predicted XA failure, deduplicated per assembly per window, marked `redirect_quantity_rule` and recorded in the data card | Program, with engineering recommendation |
| **OQ-S5** | Whether **predicted demand should be a published event**. Document 03 §6 has no `demand_forecast.*` row for `supply`, yet document 04 §7 calls predicted demand one of the system's more valuable products | Push-based consumption of the forecast. Pull works today | No event. Consumers read `GET /demand-forecast`. Adding a row is a document 03 change and is not made here | Program / architecture |
| **OQ-S6** | Whether a **`reservation_set.extended`** event is needed, or consumers re-read | Freshness of Scheduling's expiry projection between extension and release | No event; `GET /reservation-sets/{id}` is `required` partly for this reason | Program / architecture |
| **OQ-S7** | **Derivation Code values** (NAVSUP P-488, unlocated) | Full fidelity of the field document 07 §4.2 calls *the single most demo-relevant field located in the entire study* | Reserved synthetic set with `Y` the sole documented value, declared in the data card | Engineering research (ranked third in 07 §10) |
| **OQ-S8** | The **full Supply Condition Code table**. Document 07 verifies `A`, `F`, `M` only | Realistic condition partitioning beyond the documented `F → M → A` progression | Three values, `set_is_complete = false`. **No fourth value invented** | Engineering research |
| **OQ-S9** | **`max_lines` on a reservation set** and `max_keys` on the snapshot query | Nothing; both are declared in the chart and the specification | 250 lines, 500 keys. Derived from document 07 §8's cardinalities and document 13 §2.1's ~4,000–6,000 catalogue NIINs, **not invented** — a fleet availability work package plausibly spans a few hundred NIINs. Revisit against the capacity model (05 §4.6) | Engineering, reviewed by program |
| **OQ-S10** | Default **`ttl_seconds`** and the reaper interval | Nothing; both configurable | 3600 s TTL, 15 s reaper interval, 8 extensions. The TTL must exceed an optimizer solve plus an adjudication round-trip and must not exceed a planner's tolerance for a stale hold; both figures depend on the human-capacity model document 05 §4.5 defers | Program, informed by 05 §4.5 |
| **OQ-S11** | Whether **`MAINT_EFFECT`, `COSAL`, `NET_COSAL`, `GROSS_COSAL`** (07 §5.7's verbatim definitions) should be published to Fleet Status | Nothing; computed and served on an `internal` operation | Computed per document 07 §5.7 and exposed internally. **No event**, because document 03 §6 has no row for it, and `MAINT_EFFECT` — *"the probability of all required repair parts for a given maintenance action being onboard"* — is the single best supply-effectiveness figure the platform could show a TYCOM, so the routing deserves a decision rather than a default | Program / architecture |
| **OQ-S12** | Which **`Proposal` kind** carries an allowance-quantity revision and a new Derivation Code. Document 03 §7.2's enum has no allowance-revision member | Adjudication of the platform's most demo-relevant supply output (07 §4.2) as a first-class proposal | A `requisition` proposal with advice code **`5D`** where the revision yields a materiel requirement; the documented 4790/CK → CDMD-OA → WSF → ASI (`JSS117`) path with no proposal where it is purely structural. **No seventh kind invented** | Program / architecture, per correction 9 |

---

## 15. Quick reference for an implementing agent

Read in this order before writing code in `services/supply/`:

1. **Document 09** §3 (layout), §4 (skeleton), §5 (API rules), §8 (Definition of Done), §9 (DO-NOT).
2. **Document 03** §3.3 (identity), §4/§4.1 (conventions and annotations), §5 (events and envelope), **§6's Supply rows**, §7.2 and **§7.2.1** (proposals and adjudication authority), §9 (untrusted content), §10 (substitution), §11 (edge policy), §15 (the obligation split).
3. **Document 04 §7** — and §1.4 of this document for the six places it is extended.
4. **Document 05 D6 and D24** in full. Everything distinctive here exists to close one of them.
5. **Document 07 §4 in full and §6** before writing a single code value. Then **§3 of this document** before writing anything in `services/reservations.py`.
6. **Document 11** before writing anything in `events/`. Note that it specifies no saga, and §3.12 explains why none is needed.
7. **Document 13 §6 and §12** for the reference dataset's identifiers, allowance generation, and SMR branch coverage.
8. **Document 06 §7 and 07 §8** for any quantity. Do not invent one (09 DO-NOT 31).

Then: `make scaffold SLUG=supply`, copy document 09 §8 plus §12 of this document into the README, and tick.

**If you read only one thing:** `ReservationSet` has four states and none of them can hold a subset of the requested lines. Everything else in §3 protects that property.
