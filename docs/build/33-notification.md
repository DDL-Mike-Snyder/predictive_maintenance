# Notification — Routing, Escalation, and the Delivery-Channel Abstraction

| | |
|---|---|
| **Status** | Draft |
| **Slug** | `notification` (document 03 §3.1, used without variation) |
| **Directory** | `platform/notification/` (document 09 §3.1) |
| **Purpose** | Build specification for the platform service that routes, escalates, delivers, and records acknowledgement of every operator-directed notification in FATHOM — across an ashore posture and a genuinely disconnected afloat posture that are **not** the same abstraction with a different transport |
| **Carries** | The delivery half of finding **D17**'s remedy (document 06 §6 admission control). An admission-control breach that fires into a black hole is indistinguishable from no admission control at all |
| **Primary sources** | [03 §6](../architecture/03-integration-contracts.md) (the catalog, read in full — §2 below), [04 §11](../architecture/04-subapplication-architectures.md) "Notification", [01 §12](../architecture/01-system-architecture.md) (off-ramp seams), [06 §6](../architecture/06-demo-decisions-and-assumptions.md) and [06 §4](../architecture/06-demo-decisions-and-assumptions.md) |
| **Binding contracts** | 03 §3 (identity), §4 (API conventions), §5 (event backbone, envelope, clock), §7.2/§7.2.1 (Proposal, authority classes), §7.3 (classification), §11 (edge reconciliation), §15 (obligations) |
| **Conventions** | [09 — Monorepo & Conventions](09-monorepo-and-conventions.md) (§8 Definition of Done applies in full, nothing removed), [10 — Shared Packages](10-shared-packages.md), [11 — Outbox & Sync Library](11-outbox-sync-library.md) |
| **Classification** | Internal. The service operates at U for the synthetic demonstration (03 §12) |

---

## 1. Purpose and scope

Document 04 §11 specifies this service in two sentences:

> *"Routing and escalation for raised risk flags, opened reviews, shortfalls, and adjudication requests. Delivery-channel abstraction, since afloat notification will not resemble shore notification."*

Document 01 §5 adds nothing beyond a one-line restatement. Everything else in this document is derived — from the live document 03 §6 catalog, from the DDIL posture in 01 §12, and from the two demonstration decisions that make notification load-bearing rather than decorative (06 §4 and 06 §6). Where a derivation required a choice that no architecture document makes, the choice is marked **`DECISION`** and, where it needs program confirmation, **`PLACEHOLDER`** with an entry in §11.

### 1.1 Why this service is on the critical path

Two reasons, and neither is about convenience.

1. **Document 06 §6's admission control is a delivery obligation.** *"If unadjudicated candidates exceed 3× monthly throughput, candidate generation halts and an alarm raises."* At 06 §6's demonstration figures — 840 candidates per month — the trigger is **2,520 unadjudicated candidates**. Halting generation is Post-Mission Analysis's job. *Raising the alarm to a named human who can act on it* is this service's job, and it is the only part of the mechanism that can fail silently. §4.5, §8.2, and §9's test `test_d17_admission_control_alarm_reaches_a_human` exist for exactly this.
2. **Afloat and ashore notification are different abstractions, not one abstraction with two transports.** An ashore notification assumes a mailbox, a chat client, a browser session, and a network. An afloat notification during the six-week disconnect of 06 §4 assumes none of those and has a hull-local watch organisation instead. A design that models the afloat case as "the same email, sent later" converts a raised CASREP risk on patrol day 3 into an email on patrol day 42, which is not a late notification — it is a lost one. §5 and §6 are the response.

### 1.2 In scope

1. **Trigger intake** — the six declared consumer rows in document 03 §6 (§2), plus the command-invoked triggers of §2.3.
2. **Recipient resolution** — role and identity to deliverable recipient, with posture and connectivity context.
3. **Urgency classification** — `routine` | `urgent` | `critical`, and its consequences for channel selection, retry, and escalation (§4).
4. **The delivery-channel abstraction** — one interface, several implementations, split explicitly by *connectivity dependence* rather than by transport family (§5).
5. **Afloat queuing and reconciliation** — hold, drain, order, dedup, and the presentation of delay (§6).
6. **Acknowledgement and escalation** (§7).
7. **Delivery observability** — the service is a producer of `delivery.*` and `notification.*` events and holds its own outbox (§8.3).
8. **Suppression, coalescing, and storm control** — with critical exempted absolutely (§4.6).

### 1.3 Out of scope

- **Deciding that a condition exists.** Notification never computes readiness, risk, or capacity. It carries facts authored elsewhere. It has no domain model of an installed item beyond the identifiers it renders.
- **The unified adjudication queue.** That is the gateway's, built from the `fathom.*.proposal.v1` topic pattern (03 §6, 04 §11). Notification tells a human that a proposal awaits them; it does not hold the queue.
- **Operator UI rendering.** Notification serves notification records and their delay metadata; `apps/web` renders them. The **presentation rule** of §6.4 is nonetheless binding on the UI, because it is a correctness property, not a style preference.
- **The divergence-budget read-only banner.** Owned by `packages/py-sync` (document 11 §9.1) in each service's own UI surface. Notification additionally delivers a breach *notification* (§2.3).
- **Identity storage.** Recipient identities, roles, billets, and qualifications belong to `auth`. Notification holds a cache, never a directory (§3.2).

---

## 2. The complete notification-triggering event enumeration

### 2.1 What the live catalog actually declares

Document 03 §6 was read in full. **Six event rows declare `notification` as a consumer.** They are the complete set, transcribed verbatim from the current catalog, in catalog order:

| # | Event | Producer | Catalog consumers (verbatim) | Payload fields Notification uses for routing |
|---|---|---|---|---|
| 1 | `readiness.recomputed` | `fleet-status` | `notification` | `scope`, score components, contributing degradations, **`classification union`** |
| 2 | `casrep_risk.raised` | `fleet-status` | `notification`, `maintenance`, `supply` | `installed item`, **`predicted category`**, `horizon`, evidence references |
| 3 | `casrep_risk.cleared` | `fleet-status` | `notification`, `maintenance` | `installed item`, cause of clearance |
| 4 | `mission_review.opened` | `pma` | `notification` | `mission_id`, `asset`, candidate set, **`assigned reviewer`**, candidate origin |
| 5 | `redesign_candidate.created` | `design-advisory` | `fleet-status`, `notification` | `NIIN`, driver evidence, affected population, **`preliminary priority`** |
| 6 | `proposal.created` | every sub-application, per 03 §6's proposal convention on `fathom.<slug>.proposal.v1` — **and `audit`**, on `fathom.audit.proposal.v1`, for `purge`/`rewrap` (03 §6: *"exactly as any other proposal-accepting sub-application's topic does"*) | `gateway`, `notification` | `authority_class`, `blast_radius`, `requires_dual_control`, `valid_until`, `target_sub_app`, `kind` |

**Nothing else in document 03 §6 names `notification` as a consumer.** In particular, and contrary to what a reader working from an earlier revision or from document 04 §11's prose might expect:

| Event | Live consumers | Consequence |
|---|---|---|
| `proposal.expired` | `gateway`, `audit` — **not** `notification` | Notification **must not** subscribe to it. An expired unadjudicated proposal is arguably the most notification-worthy proposal event there is, so this looks like an omission rather than a decision — but the catalog is binding and wildcard subscriptions are prohibited (09 DO-NOT-14, C38). Raised as **OD-2**. |
| `proposal.adjudicated` | `audit`, and the owning sub-application | Not a Notification trigger. The acknowledgement loop for an adjudication request is closed by §7.4's *withdrawal* path, not by a second notification. |
| `allowance_shortfall.detected` | `maintenance`, `fleet-status` — **not** `notification` | Document 04 §11 and document 01 §5 both promise Notification covers **"shortfalls."** The catalog does not deliver a shortfall event to it. This is a genuine contract gap, not a reading error. Raised as **OD-1**; the build ships the handler behind a flag so the amendment is a catalog edit, not a code change (§2.4). |
| `prediction.invalidated`, `deferral.recorded`, `work_package.approved`, `requisition.status_changed`, everything else in §6 | Various; never `notification` | Not Notification triggers. Do not add them speculatively. |

> **Why the enumeration is stated this precisely.** Finding **C14** records that *"Notification is a declared consumer in five catalog rows but appears in no 01 inventory."* The 01 inventory has since been repaired (01 §5 now lists the service). The row count is now six — the five sub-application catalog rows plus the proposal-convention row — and document 09 §8.2's Definition of Done requires that `src/fathom_notification/events/catalog.py` `CONSUMES`, `helm/values.yaml` `events.consumes`, and document 03 §6's rows for this slug be **equal**, verified by `tools/check_event_catalog.py`. That gate is what keeps this table honest as the catalog evolves. If a future catalog revision adds a seventh row, CI fails until this document and the code agree.

### 2.2 Urgency and routing implication, per declared event

Urgency classes are defined in §4. Routing roles are document 03 §7.2.1's `AuthorityClass` vocabulary verbatim — `maintainer` | `planner` | `supply_officer` | `design_authority` | `fleet_authority` | `security_officer` — plus exactly one non-adjudicating addition, `watch_station`, which §5.4 justifies and **OD-3** asks to have confirmed. **[AMENDMENT]** `security_officer` (amendment 03-1) was missing here and from every restatement of this vocabulary below — the omission meant `purge`/`rewrap` proposals, whose `authority_class` is `security_officer` exclusively (03 §7.2.1), had no representable recipient role at all.

| Event | Urgency | Routed to | Basis and routing logic |
|---|---|---|---|
| `readiness.recomputed` | **`routine`**, and **coalesced by default** | `planner` for the asset's RMC; `fleet_authority` for fleet-scope recomputes | This event fires on every contributing change and is the highest-volume Notification trigger by an order of magnitude. One notification per event is a storm that trains recipients to ignore the channel. **Rule:** notify only on a **readiness band transition** for the scope, or on entry into the lowest band; otherwise record the notification as `suppressed_coalesced` and fold it into the daily digest. The event's own `classification union` field selects the channel accreditation floor (§5.5). |
| `casrep_risk.raised` | **`urgent`**, promoted to **`critical`** when `predicted category` is CASREP **category 3 or 4** | `maintainer` for the owning hull (ship's force) **and** `planner` for the availability that would absorb the work | Document 01 §13 grounds CASREP categories 2–4 as the catastrophic-failure ground truth. Category 3 (major degradation) and 4 (loss of primary mission capability) are the two that must reach a hull that may be disconnected, which is why they are the promotion boundary. `horizon` modulates the escalation window (§7.3), not the class: a 7-day horizon and a 90-day horizon are both urgent, but the 7-day one escalates sooner. `PLACEHOLDER` — the category→class boundary is a program judgement; **OD-4**. |
| `casrep_risk.cleared` | **`routine`** | The recipient set of the original `casrep_risk.raised`, resolved by `installed_item_id` | This is a **closing** notification, and its primary job is not to inform but to **withdraw** the open one: it cancels any pending escalation timer on the matching raise, marks the raise `closed_by_clearance`, and — critically for §6 — collapses with it when both arrive together after a disconnect (§6.5). A clearance that arrives with no matching open raise is delivered as an ordinary routine item and recorded, never dropped. |
| `mission_review.opened` | **`routine`** | The `assigned reviewer` **identity** carried in the payload; falls back to the `maintainer` (ship's force persona) or shore-analyst cohort for the asset's unit when the field is absent | The only trigger that names its recipient in the payload, so it is identity-routed rather than role-routed. Routine because review is scheduled work within 06 §6's ~10-minute bounded-review budget, not an interrupt. **Afloat exception:** two of the demonstration's mission reviews occur *while dark* (06 §4), so this notification is generated by the **edge** instance for a **same-hull** recipient and never touches the ship-to-shore link at all (§6.2). |
| `redesign_candidate.created` | **`routine`** | `design_authority` (PEO / Design Engineer) | Priority-driven, not time-driven; a redesign candidate has no operational deadline. `preliminary priority` selects digest placement, and a top-decile priority may be delivered individually rather than in digest. Never promoted above routine: 04 §10 frames Design Advisory as producing decision packages rather than decisions. |
| `proposal.created` | **`routine`** by default; **`urgent`** when `requires_dual_control` is true, or `blast_radius` is `class` or `fleet`, or `valid_until` is within the urgent window | The proposal's own **`authority_class`** field, per 03 §7.2.1's minimum-authority-by-blast-radius table | The proposal schema already carries everything routing needs, which is the whole point of 03 §7.2's design — Notification performs **no** authority derivation of its own and **never** recomputes `authority_class` from `kind` and `blast_radius`. It reads the field the owning sub-application set. Where `requires_dual_control` is true, **both** signatures are notified, and the second is notified again on first-signature completion. `valid_until` is a real deadline: a proposal expiring inside the urgent window is urgent regardless of blast radius, because 03 §7.2 permits no un-expiring proposal and an expiry that nobody was told about is an adjudication silently declined. |

### 2.3 Required triggers that the live catalog does not yet carry

These are not in document 03 §6. They are enumerated separately, and deliberately, so that no reader mistakes them for declared contract. Each is either mandatory for a mechanism another document already commits to, or a promise document 04 §11 makes that the catalog does not keep.

| # | Trigger | Urgency | Routed to | Status and intake path |
|---|---|---|---|---|
| A | **Admission-control breach** — 06 §6: unadjudicated candidates exceed 3× monthly throughput (2,520 at demonstration figures); candidate generation halts | **`critical`** | **`fleet_authority`** (TYCOM Readiness Officer) as primary, **plus** the *named accountable human owner* of the PMA Pre-Screener's accountable-autonomous workload identity (03 §8.3) as co-primary. See §2.5 | **MANDATORY.** Intake is **dual-path** by design (§2.5): a synchronous command to `POST /notifications` *and* a durable event. Neither path alone is sufficient. |
| B | **Admission control cleared** — the queue drains back below the threshold and generation resumes | `routine` | The recipient set of trigger A | Mandatory companion. Withdraws A's escalation and records the outage duration. Without it, A escalates forever after the condition resolves. |
| C | **Divergence-budget breached / cleared** — `sync.divergence_budget_breached` on `fathom.sync.divergence.v1`, declared by document 11 §9.1 | **`urgent`** | `planner` and `fleet_authority` ashore; `watch_station` on the affected hull | Document 11 §9.1 declares the event and its purpose — *"so shore sees the hull's history after reconnect"* — but 03 §6 declares no consumers for `fathom.sync.*`. Handler built, subscription flagged. **OD-5.** |
| D | **Allowance shortfall** — `allowance_shortfall.detected` (`supply`) | `urgent` | `supply_officer`, and `maintainer` where the shortfall blocks an open work order | Promised by 04 §11 and 01 §5 ("shortfalls"); **not delivered by 03 §6**. Handler built behind `triggers.allowance_shortfall.enabled=false`. **OD-1.** |
| E | **Proposal expired** — `proposal.expired` | `routine` | The `authority_class` that failed to adjudicate it | Catalog declares `gateway`, `audit` only. Handler built, disabled. **OD-2.** |

**Handlers for C, D, and E ship complete, tested, and disabled by Helm value.** The reason is stated once: enabling one of them is then a catalog amendment plus a values change reviewed against `tools/check_event_catalog.py`, not a code change written months later by someone who no longer remembers why the gap existed. Trigger A is **never** flag-gated.

### 2.4 The subscription set is closed

No wildcard subscriptions (09 DO-NOT-14, C38). Notification's `events/catalog.py` names six consumed event types and no more until an amendment lands. Two additional read-model subscriptions are required for routing and are **also** absent from the catalog as Notification-consumed rows:

| Read model | Fed by | Needed for | Status |
|---|---|---|---|
| **Recipient posture** — is this recipient's unit currently on a deployed hull, and in what deployment state | `asset.status_changed` (`registry`) — "operational status, OFRP phase, deployment state" | §5.4's channel selection cannot distinguish an ashore recipient from an afloat one without it | Catalog consumers are `fleet-status`, `maintenance`, `pdm`. **OD-6.** |
| **Identity and role cache** | `auth`, by `changed_since` read (03 §4), not by event | Role→identity expansion (§3.2) | `auth` publishes no catalog events. Read-through cache with a declared staleness bound. |

Until OD-6 resolves, the enterprise instance treats an unresolved posture as **afloat** and requires a connectivity-independent channel (§5.4). Failing safe means over-provisioning a watch-log entry; failing the other way means a critical notification queued behind a satellite link nobody is holding open.

### 2.5 The admission-control alarm: recipient, and why intake is dual-path

**The recipient decision.** No architecture document names an owner for this alarm. Document 04 §11 does not mention it; document 06 §6 says only that *"an alarm raises."* The available role vocabularies are document 01 §4's four operator personas and document 03 §7.2.1's six `AuthorityClass` values. Neither contains a "PMA program lead," an "on-duty supervisor," or anything resembling a queue owner.

**`DECISION`, with the reasoning shown, because inventing a sixth role vocabulary would be worse than either alternative:**

1. **Primary: `fleet_authority` (TYCOM Readiness Officer).** The breach halts candidate generation across the fleet. Its blast radius is `fleet`, and `fleet_authority` is the only class document 03 §7.2.1 admits at fleet scope. Routing a fleet-scope capability outage to an item-scope role would be the same category error 03 §7.2.1 exists to prevent.
2. **Co-primary: the named accountable human owner of the PMA Pre-Screener's workload identity.** Document 03 §8.3 *already requires* every accountable-autonomous agent to carry *"a scoped short-lived workload identity with a **named accountable human owner**."* The pre-screener is named there explicitly. That owner is therefore an identity the system is contractually obliged to know, and it is the person whose agent's output is filling the queue. This requires **no new role** and no new registry — it reads a field 03 §8.3 mandates.
3. **Escalation hop 1 (§7.3): a second `fleet_authority` holder.** Not a new role.
4. **Escalation hop 2: terminal `unacknowledged_critical`** — a permanent red banner on the gateway's fleet view for every `fleet_authority` holder, a `fathom_notification_unacknowledged_critical` gauge at 1, and an Audit record. Not a third recipient, because a third silent hop is just a longer black hole.

**`PLACEHOLDER` — requires confirmation.** The task framing proposed a PMA program lead or an on-duty supervisor, and either may be organisationally correct. The above is the construction that uses only vocabulary the architecture already binds. Raised as **OD-7**, and the mapping lives in `escalation_policy` data (§7.3), so confirming a different owner is a configuration change and not a rebuild.

**Why intake is dual-path.** Document 03 principle 3 is unambiguous: *"Events carry facts, not instructions… A producer that needs a specific action taken elsewhere issues a command against that sub-application's API and accepts the response."* An admission-control breach is precisely a producer needing a specific action taken elsewhere. So:

- **Path 1 — synchronous command.** PMA calls `POST /api/v1/notification/notifications` with `Idempotency-Key` and receives a **receipt** carrying the resolved recipient identities and the accepted channel set. This is the anti-black-hole property in its strongest available form: PMA learns *in-band* whether the alarm landed, and a non-2xx is itself an operator-visible failure in PMA rather than a silence in Notification.
- **Path 2 — durable event.** PMA also emits `adjudication_capacity.breached` through its own transactional outbox in the same transaction as the halt. If Notification is down when path 1 is attempted, the event is still durable and is delivered when Notification returns.
- **Deduplicated** on `Idempotency-Key` / `event_id`, so both paths landing produces one notification.

Belt and braces is justified here and nowhere else in this document: this is the one notification whose loss invalidates a review finding's remedy. It also means the new event `adjudication_capacity.breached` must be added to PMA's rows in document 03 §6 — **OD-8**.

---

## 3. Data model and recipient resolution

### 3.1 Aggregates

One logical database (03 §15.13, 09 §8.4). Six owned aggregates, each with a declared conflict policy (§6.6).

| Aggregate | Holds | Notes |
|---|---|---|
| `notification` | The notification record: trigger reference, urgency, subject identifiers, classification label, `occurred_at`, `recorded_at`, body reference, recipient set, status | **Operationally append-only**; status transitions are separate rows in `notification_transition`, never in-place mutation. Purge by crypto-shred (03 §13.1). |
| `delivery_attempt` | One row per channel per recipient per attempt: channel id, node, monotonic attempt deadline, outcome, provider reference | The evidence that the system tried. Never pruned before its notification. |
| `acknowledgement` | Identity, channel, node, `acknowledged_at`, free-text note | Append-only. A human judgement, and therefore the same class of record as an anomaly tag under 03 §11. |
| `escalation` | Hop index, policy version, from/to recipient, monotonic deadline, trigger reason | Append-only. Bounded at two hops (§7.3). |
| `channel_registration` | Channel id, `reach`, `requires_connectivity`, `max_urgency_served`, `max_classification`, `supports_acknowledgement`, health | Declared in Helm values, loaded and validated at startup (§5.6). |
| `suppression_state` | Coalescing windows, digest membership, dedup keys | Never reachable from a `critical` notification (§4.6). |

Plus the `outbox` and `inbox` tables from document 11 §2.2 and §3.3, unmodified.

### 3.2 Recipient resolution

```python
class RecipientResolver(Protocol):
    def resolve(
        self,
        *,
        role: RoutingRole | None,          # AuthorityClass (03 §7.2.1) + watch_station
        identity: IdentityRef | None,      # when the trigger names a person
        subject: Subject,                  # 03 §5.4 scope identifiers — bounds the role cohort
        classification: ClassificationLabel,
    ) -> list[RecipientContext]: ...


@dataclass(frozen=True)
class RecipientContext:
    identity: IdentityRef
    roles: frozenset[RoutingRole]
    uic: str                       # 03 §3.3 AssetRef.uic — the unit, from auth ABAC attributes
    asset_id: UUID | None          # the hull, where the recipient is attached to one
    posture: Posture               # ASHORE | AFLOAT | UNKNOWN
    connectivity: Connectivity     # CONNECTED | INTERMITTENT | DARK
    clearance: ClassificationLabel # the ceiling the router must not exceed
```

Four rules:

1. **A role never resolves to "everyone with the role."** It resolves to holders of that role scoped by `subject` — the hull's ship's force for an `installed_item`-scoped item, the owning RMC's planners for an `asset`-scoped one. An unscoped role expansion is how a per-item risk flag becomes a fleet-wide mailing.
2. **`posture` and `connectivity` are inputs to channel selection only.** They are never inputs to *whether* a notification exists, and never inputs to authority. Document 11 DO-NOT-5 forbids binding write authority to liveliness; the same reasoning forbids binding notification *existence* to reachability. A notification for a dark hull is created, recorded, and queued — it is not skipped.
3. **`clearance` is a ceiling, enforced in the query.** Recipient resolution filters by clearance *inside* the query, never by removing recipients afterwards (03 §7.3, 09 DO-NOT-22).
4. **Empty resolution is a failure, not a no-op.** A trigger that resolves to zero recipients increments `fathom_notification_unroutable_total`, writes an Audit record, and — for `urgent` and `critical` — raises its own `critical` notification to `fleet_authority`. A notification with nobody to send it to is the black hole in its purest form.

### 3.3 Classification of the notification body

A notification is a derived value. Per 03 §7.3 and obligation 4 it carries the **union** of its inputs' labels in `inherited_from`, and per 06 §5 it inherits the aggregation constraint: a notification whose body would disclose the existence of a compartmented contributor is not sendable merely because its recipient holds the role.

Two mechanical consequences, both in §5.5:

- Every channel declares `max_classification`. The router refuses a channel below the notification's level; it does not redact and send.
- Where the notification's level exceeds what any available channel for that recipient can carry, the router delivers a **pointer with no domain content** — "a FATHOM item requires your attention; open the operator interface" — on the highest-accredited available channel, and records `body_withheld_classification`. A truncated body on a low-side channel is a spillage under 03 §13, which is an incident with a remediation cost, not a delivery.

---

## 4. Urgency classes

### 4.1 The enum

```python
class Urgency(StrEnum):
    ROUTINE  = "routine"    # scheduled work. May be coalesced, digested, and deferred to reconnect.
    URGENT   = "urgent"     # acts on this shift. Individually delivered. Never digested.
    CRITICAL = "critical"   # acts now. Requires a connectivity-independent channel where the
                            # recipient may be disconnected. Escalates if unacknowledged.
                            # Exempt from every suppression, rate-limit, and preference path.
```

Three values, deliberately. A four- or five-level scale invites recipients to negotiate the middle of it, and every level that is not mechanically distinguishable in *behaviour* is decoration. Each of these three changes what the code does:

| Property | `routine` | `urgent` | `critical` |
|---|---|---|---|
| Coalescing / digest eligible | Yes, by default | No | **Never** |
| Rate-limit eligible | Yes | Yes, per-recipient floor of 1/hour guaranteed | **Never** (§4.6) |
| Recipient preference may suppress | Yes | Channel choice only, not suppression | **Never** |
| Requires a connectivity-independent channel when recipient posture is AFLOAT or UNKNOWN | No | **Yes** | **Yes**, and refusal is a hard error (§5.4) |
| Acknowledgement expected | No | Yes, untimed | **Yes, timed** |
| Escalates if unacknowledged | No | No | **Yes**, two hops (§7.3) |
| Default acknowledgement window | — | 8 h (recorded, not enforced) | **15 min** (§7.3) |
| Retry policy | 3 attempts, monotonic backoff to 1 h | 5 attempts, monotonic backoff to 15 min | Every channel with reach, in parallel, immediately (§5.4) |
| Delivered during afloat disconnect | Queued for reconnect | Queued **and** same-hull channel if the recipient is same-hull | **Same-hull channel unconditionally where one exists** (§6.2) |

### 4.2 Class assignment is data, not code

Assignment lives in `urgency_policy` rows, versioned, loaded at startup, exported on `GET /urgency-policies`. Every notification records the `urgency_policy_version` that classified it, for the same reason every taxonomy label records `taxonomy_version` (document 12 §2.1): a class boundary retuned in month four must not silently reinterpret month two's escalation history.

### 4.3 The full mapping

| Trigger | Class | Promotion condition |
|---|---|---|
| `readiness.recomputed` | `routine` | None. Never promoted — the readiness signal that matters operationally arrives as `casrep_risk.raised`, which has its own row |
| `casrep_risk.raised` | `urgent` | → `critical` when `predicted category` ∈ {3, 4} (`PLACEHOLDER`, OD-4) |
| `casrep_risk.cleared` | `routine` | None |
| `mission_review.opened` | `routine` | None |
| `redesign_candidate.created` | `routine` | None |
| `proposal.created` | `routine` | → `urgent` when `requires_dual_control` is true, or `blast_radius` ∈ {`class`, `fleet`}, or `valid_until` − now < 24 h (tunable) |
| **A** Admission-control breach | **`critical`** | Fixed. Not tunable, not demotable, not flag-gated |
| **B** Admission control cleared | `routine` | None |
| **C** Divergence-budget breached | `urgent` | → `critical` when the breached aggregate is `maintenance_action_record` or `anomaly_tag` — document 11 §9.1 warns these budgets must exceed patrol length or "D8 returns wearing a compliance badge" |
| **D** Allowance shortfall | `urgent` | → `critical` when it blocks a category 3/4 CASREP-risk work order (`PLACEHOLDER`, OD-4) |
| **E** Proposal expired | `routine` | None |
| Unroutable-trigger self-alarm (§3.2 rule 4) | **`critical`** | Fixed |
| Channel-total-failure self-alarm (§5.6) | **`critical`** | Fixed |

### 4.4 Every window is a monotonic duration

Acknowledgement windows, retry backoff, coalescing windows, digest boundaries, and escalation deadlines are **all** measured on a monotonic clock and stored as monotonic deadlines (`escalate_after_mono`), never as wall-clock timestamps. Document 03 §5.4 and document 11 DO-NOT-3: Ubuntu STIG **V-260520** mandates `makestep 1 -1`, and the backward step fires precisely when a disconnected node reconnects and drains its outbox — which is exactly when a reconnecting hull's escalation timers would otherwise all fire at once or never.

### 4.5 Critical is the class that carries D17

`critical` exists as a distinct class for one reason: the admission-control alarm must survive every mechanism that legitimately protects recipients from the other two classes. Coalescing, digesting, rate limiting, quiet hours, per-recipient channel preferences, and channel health degradation are all real requirements, and every one of them is a plausible route to swallowing the alarm. Making them structurally unreachable from `critical` is cheaper and more auditable than remembering to exempt it in six places.

### 4.6 The suppression exemption, mechanically

```python
def apply_suppression(n: Notification, state: SuppressionState) -> SuppressionOutcome:
    if n.urgency is Urgency.CRITICAL:
        # Not a branch that returns "no suppression" — a branch that never reaches the
        # suppression engine at all. See test_rate_limit_never_suppresses_critical and
        # the static gate ntf-critical-not-suppressible (§9.5).
        return SuppressionOutcome.deliver_now(reason="critical_exempt")
    ...
```

Enforced three ways, because one is not enough for a property this consequential: the guard above; an import-linter contract forbidding `suppression` from being reachable with a `CRITICAL` argument in any path; and a property test that generates arbitrary suppression states and asserts no `critical` notification is ever withheld.

---

## 5. The delivery-channel abstraction

### 5.1 The interface

**One interface. Multiple implementations. The axis of variation is connectivity dependence, not transport family.**

```python
class ChannelReach(StrEnum):
    ASHORE = "ashore"          # reachable only from the enterprise deployment
    AFLOAT = "afloat"          # reachable only from an edge deployment, on its own hull
    BOTH   = "both"            # reachable from either, with node-local semantics


@dataclass(frozen=True)
class DeliveryResult:
    outcome: DeliveryOutcome          # DELIVERED | REJECTED | UNAVAILABLE | DEFERRED
    channel_id: str
    node: ProducerNode                # "enterprise" | "edge:<asset_id>" — 03 §5.4 producer_node
    attempted_at: datetime            # recorded_at semantics; never an ordering input
    provider_ref: str | None          # message id, watch-log entry number, alarm annunciation id
    acknowledgeable: bool             # whether an ack can arrive back through this channel
    detail: str | None                # human diagnostic. Never used for control flow (03 §4)


class NotificationChannel(Protocol):
    channel_id: str
    reach: ChannelReach
    requires_connectivity: bool       # THE load-bearing attribute. See §5.2.
    max_urgency_served: Urgency
    max_classification: ClassificationLabel
    supports_acknowledgement: bool

    def deliver(self, notification: Notification, recipient: RecipientContext) -> DeliveryResult: ...
    def health(self) -> ChannelHealth: ...
```

`deliver()` is synchronous, has no retry loop of its own, and never queues. Retry is the router's (§5.6); queuing is the outbox's (§6). A channel that queues internally makes `DELIVERED` a lie, and `DELIVERED` is the only evidence this service produces that it did its job.

### 5.2 `requires_connectivity` is the design's centre of gravity

The temptation is to model channels by transport — email, chat, dashboard, alarm — and treat afloat as "the same channels, over a worse link." Document 04 §11 warns against exactly this: *"afloat notification will not resemble shore notification."* Document 01 §12 explains why: ships, submarines in particular, *"are genuinely DDIL,"* and the demonstration's SSN is dark for six weeks (06 §4).

So the classification that matters is: **can this channel complete a delivery with no network path off the node it runs on?**

- If **yes**, it can serve a `critical` notification during a disconnect.
- If **no**, it cannot, regardless of how urgent the content is or how good the transport usually is.

Everything else — SMTP versus chat versus a watch log — is an implementation detail beneath that one bit.

### 5.3 The implementations

| Channel | `reach` | `requires_connectivity` | `max_urgency_served` | Acknowledgeable | Notes |
|---|---|---|---|---|---|
| `email` | `ashore` | **true** | `urgent` | No (link-back only) | In-enclave SMTP relay. Cannot serve `critical` alone, because a mailbox is not an alarm. |
| `chat` | `ashore` | **true** | `urgent` | Yes, via callback | **In-enclave chat only** (Mattermost/Matrix class). An internet-hosted Slack is **prohibited** by 01 §12 and 09 DO-NOT-26 — no runtime calls to public-internet services, no external DNS. If no in-enclave chat is procured, this channel is simply absent; nothing else changes. **OD-9.** |
| `dashboard_badge` | `both` | **false** | `urgent` | Yes | Writes to Notification's **own** store; the gateway composes it into the operator UI. Connectivity-independent *for a recipient with a session against the same node* — the edge instance's badge serves afloat users with no shore path. It is not connectivity-independent for a recipient who has no session, which is why it cannot carry `critical` alone either. |
| `watch_log` | **`afloat`** | **false** | **`critical`** | Yes, by watch-stander entry | Appends an entry to the hull's watch log / deck-log queue over the ship LAN. **This is the primary afloat channel and it is genuinely a different abstraction** — its delivery unit is a log entry against a *watch station*, not a message to a person; its acknowledgement is a watch-stander's initials; its retention is the ship's, not ours. It completes with no shore path whatsoever. |
| `bridge_alarm` | **`afloat`** | **false** | **`critical`** | Yes, by alarm acknowledgement | Audible/visual annunciation at a manned station, for `critical` only. **`PLACEHOLDER`** — integration with a hull's alarm annunciation is a hardware and accreditation seam that no architecture document scopes. The demonstration implements `LoopbackAlarmChannel`, which writes a distinguishable high-priority watch-log entry and records `annunciation: simulated`. **OD-10.** |
| `outbox_queue` | — | — | — | — | **NOT A CHANNEL.** Listed only to say so. Queuing for reconnect is document 11's outbox, is not a delivery, and never produces `DELIVERED`. §6.1. |

> **Why `watch_log` and `email` are not the same abstraction.** They differ in delivery unit (log entry against a station versus message to a mailbox), in addressing (billet-on-watch versus identity), in acknowledgement semantics (initials in a log versus a click), in retention authority (the ship's versus ours), and in bandwidth posture (zero external bytes versus a satellite round trip). A design that treats `watch_log` as "email with a different backend" gets the addressing wrong first — it sends to the person who happens to hold the role, who at 0300 on patrol day 21 is asleep, rather than to the station that is by definition manned.

### 5.4 The routing logic

```python
def select_channels(n: Notification, r: RecipientContext) -> ChannelPlan:
    candidates = [
        c for c in registry.for_reach(node_reach_for(r))
        if c.max_urgency_served >= n.urgency
        and c.max_classification.dominates(n.classification)
        and c.health().usable
    ]

    needs_offline = (
        n.urgency in (Urgency.URGENT, Urgency.CRITICAL)
        and r.posture in (Posture.AFLOAT, Posture.UNKNOWN)   # UNKNOWN fails safe — §2.4
    )
    offline_capable = [c for c in candidates if not c.requires_connectivity]

    if needs_offline and not offline_capable:
        # HARD FAILURE. Never a silent queue-and-hope. See DO-NOT-1.
        raise NoConnectivityIndependentChannel(n, r)

    if n.urgency is Urgency.CRITICAL:
        # Every channel with reach, in parallel, immediately. Not a primary/fallback
        # cascade: a cascade's first hop is a place for a critical alarm to sit.
        return ChannelPlan(parallel=candidates, sequential=[])

    if n.urgency is Urgency.URGENT:
        return ChannelPlan(parallel=offline_capable or candidates[:1],
                           sequential=[c for c in candidates if c not in offline_capable])

    return ChannelPlan(parallel=[], sequential=candidates[:1])   # routine: one channel, best-effort
```

Five rules the code above encodes, stated in prose because they are the contract:

1. **Urgency selects the channel *class*; posture selects the *instance*.** Urgency asks "may this wait for a network?" Posture answers "is there one?"
2. **`critical` fans out in parallel, not in a cascade.** A cascade has a first hop, and a first hop is somewhere a critical alarm can sit for the length of a timeout.
3. **`UNKNOWN` posture is treated as `AFLOAT`.** Over-provisioning a watch-log entry costs a line in a log. Under-provisioning costs the alarm.
4. **No connectivity-independent channel for an urgent-or-critical afloat recipient is a hard error**, surfaced as an RFC 9457 `409` on the command path (`urn:fathom:problem:notification:no-offline-channel`), as a `critical` self-alarm on the event path, and on `/readyz` as degraded. It is never a queue.
5. **A recipient may be resolved on more than one node.** A shore analyst assigned as a mission reviewer for a deployed hull is ashore; the hull's ship's force is afloat. The same trigger therefore produces different channel plans per recipient, on different nodes, and both are recorded against the one `notification` record.

### 5.5 Classification gating in the router, not in the channel

`c.max_classification.dominates(n.classification)` runs during *candidate selection* — the channel is never handed a notification it may not carry. Per 03 §7.3 the filter is inside the selection, not a post-hoc removal, and per §3.3 the fallback is a content-free pointer rather than a redacted body.

### 5.6 Channel health, retry, and total failure

- **Health** is per channel, exposed as `fathom_notification_channel_usable{channel}` and on `/readyz`. An unusable channel is removed from candidacy — which is precisely why rule 4 exists: degrading the last offline-capable channel must fail loudly rather than silently reclassifying the recipient as reachable.
- **Retry** is the router's, with monotonic backoff (§4.4), attempt counts per §4.1, and every attempt recorded as a `delivery_attempt` row plus a `delivery.attempted` event.
- **Total failure** — every channel in the plan returning non-`DELIVERED` — raises a `critical` self-alarm to `fleet_authority` through a **statically declared minimal channel set** that does not consult the registry, so that a registry-wide misconfiguration cannot suppress the alarm about itself. Recursion is bounded: a self-alarm that itself totally fails writes to Audit and sets `fathom_notification_channel_total_failure` to 1, and does not raise a third.
- **Channel registrations are validated at startup** against the invariant that, for every routing role with any afloat holder, at least one registered channel has `reach ∈ {afloat, both}`, `requires_connectivity == false`, and `max_urgency_served == critical`. The service **refuses to start** otherwise. That is the one configuration error that would turn every afloat critical notification into rule 4's hard error at runtime, and it is cheaper to catch at boot.

---

## 6. Afloat queuing and reconciliation

### 6.1 What is held, and where

Notification runs the **same outbox discipline as every other service** (03 §15.11, document 11 §2) for its own published events, and additionally holds undelivered notifications as domain state. The two are distinct and must not be conflated:

| | Undelivered notification | Outbox row |
|---|---|---|
| What it is | Domain state: a fact that a human has not yet been told something | Transport state: an event this service published that the broker has not yet accepted |
| Lives in | `notification` + `delivery_attempt` | `outbox` (document 11 §2.2) |
| Drains when | A channel with reach becomes available | The relay runs (always active — C21) |
| Survives a six-week disconnect | Yes, in full | Yes, in full, encrypted at rest (document 11 §10.1) |

**Queuing for reconnect is never reported as a delivery.** `DeliveryOutcome.DEFERRED` is its own outcome, distinct from `DELIVERED`, and `fathom_notification_deferred` is a separate gauge. Collapsing them is how a delivery-rate dashboard reads green while nobody has been told anything.

### 6.2 The two afloat cases are genuinely different

This is the question the task poses, and it has a two-part answer.

**Case 1 — a same-hull recipient, notification generated afloat.** No link is involved at all. The edge instance of Notification resolves a same-hull recipient, selects `watch_log` (and `bridge_alarm` for `critical`), and **delivers immediately, at sea, on patrol day 3**. The notification is complete before the ship reconnects. Its `delivery.confirmed` event queues in the outbox and reaches shore on reconnect as an *audit fact about a delivery that already happened*, not as the delivery.

This is the case that matters most and it is the one a naive design gets wrong. The demonstration's scenario (06 §4) contains it explicitly: one at-sea corrective repair and two mission reviews conducted while dark. Both `mission_review.opened` notifications are same-hull and both are delivered at sea. If a CASREP category-4 risk is raised by the edge detector ensemble on patrol day 21, the maintainer on that hull is told on patrol day 21.

**Case 2 — an ashore recipient, notification generated afloat (or vice versa).** No connectivity-independent channel exists for that recipient from that node, by definition. The notification is created, recorded, and **deferred**, and drains per document 11 §9.3's priority classes on reconnect. It is delivered late, and §6.4 governs how it is then presented.

**The consequence, stated as a rule:** a `critical` notification with any same-hull recipient is **never** dependent on reconnect. It takes the same-hull path immediately, and the shore-bound copy for its ashore co-recipients defers independently. One notification, two recipients, two nodes, two very different delivery timelines, one record. This is DO-NOT-1.

### 6.3 Drain order, priority, and deduplication

- **Order** is `(producer, producer_node, monotonic_seq)` or the HLC — never `source_time`, never `occurred_at` (03 §5.4, document 11 DO-NOT-2).
- **Deduplication** is on `event_id` for consumed events and on `Idempotency-Key` for commanded ones. Notification is idempotent on both. Idempotency-key retention must exceed the divergence budget, not the ashore default of 24 hours — a hull's retry window is weeks (09 open question 5). Set to **8 weeks** for the demonstration's six-week scenario, with margin. **OD-11.**
- **Priority class.** Document 11 §9.3 defines drain classes 0–4 and does not place notification records in any of them. `DECISION`: `delivery.confirmed` and `notification.acknowledged` records for `critical` and `urgent` notifications drain in **class 1** alongside the label stream, because an acknowledgement is a human judgement of the same kind and shore needs to know the hull was told; `routine` records drain in **class 3**. Requires an amendment to document 11 §9.3's table — **OD-12**.
- **Not a replay.** A six-week-old notification draining from the edge is a **first emission of a real fact**, not history. `replay` stays false; `X-Backfill` is never used for edge drain (document 11 §9.3a). It fires its normal side effects ashore, deliberately.

### 6.4 The presentation rule — delay is visible, and occurrence is not overwritten

**This is binding on the API, on every channel body, and on `apps/web`.**

A notification that occurred at sea and was delivered on reconnect is presented as **having occurred when it occurred**, with the delay explicit:

1. **`occurred_at` is the headline timestamp.** Always. It is the time the fact became true in the producer's domain (03 §5.4).
2. **`recorded_at`, `delivered_at`, and `received_at` are secondary and separately labelled.** None of them is ever rendered as the occurrence time, in any channel body, in any list, in any sort default.
3. **Every notification carries a computed `delay` block**, served by the API and rendered by every surface:

```python
@dataclass(frozen=True)
class DelayDisclosure:
    occurred_at: datetime
    delivered_at: datetime | None
    delay: timedelta | None                # delivered_at - occurred_at
    delay_is_material: bool                # delay > materiality threshold (default 1 h, tunable)
    delay_cause: DelayCause                # DISCONNECTED_EDGE | CHANNEL_UNAVAILABLE |
                                           # SUPPRESSED_COALESCED | NONE
    disconnection_context: str | None       # "generated at sea; hull reconnected after 42 days"
    dispersion_ms: int                      # 03 §5.4's published epsilon at generation
```

4. **Sort order is by `occurred_at` by default.** A reconnect that dumps six weeks of notifications sorted by arrival puts patrol day 3 above patrol day 40 and reads as a live burst.
5. **`dispersion_ms` gates the presentation of the timestamp itself.** Document 03 §5.4: *"Small epsilon permits wall-clock-assisted presentation; epsilon exceeding the inter-write interval forces causal-only ordering and forbids any timestamp arbitration."* A notification generated on a hull in `holdover` or `unsynced` time for weeks is rendered with an explicit uncertainty qualifier — "on or about patrol day 21 (±6 h)" — and never with false precision. `sync_quality` travels with the notification and is retained permanently (03 §5.4, document 11 §10.5).

> **Why this is a correctness rule and not a UI preference.** A CASREP risk raised on patrol day 21 and presented on patrol day 42 as "raised just now" produces a planner who believes a 21-day-old horizon is fresh. Every downstream judgement — whether the window has already closed, whether the item has since been replaced, whether the clearance already arrived — is made against a wrong premise. This is the same class of defect as finding **D22** (using `occurred_at` for hindsight-authored features): a timestamp used for something it does not mean.

### 6.5 Raised-and-cleared while dark

The case that makes §6.4 more than bookkeeping. Suppose `casrep_risk.raised` on patrol day 21 and `casrep_risk.cleared` on patrol day 28, and reconnect on day 42. On drain, both arrive, in order.

**Rule:** the pair **collapses into one historical record**, marked `raised_and_cleared_while_disconnected`, delivered as **`routine`** ashore, and rendered with both original timestamps and the resolution. The raise's escalation timer is cancelled without ever having started (§7.3), and no ashore alarm sounds for a condition that resolved fourteen days ago.

Two things this rule does **not** do:

- **It does not delete anything.** Both events, both notification rows, and the collapse decision are retained. The hull's watch log holds the day-21 entry that was correctly delivered at sea, and the ashore record must not contradict it.
- **It does not apply afloat.** Same-hull delivery already happened on day 21, correctly and urgently. Collapse is a *presentation* of a late-arriving pair to a recipient who could not have been told earlier — never a suppression of the timely delivery.

### 6.6 Conflict policy per aggregate

Declared per 03 §11 and document 11 §7. Notification is enterprise-authoritative by default (03 §11's default rule) with two deliberate exceptions.

| Aggregate | Policy | Rationale |
|---|---|---|
| `notification` | Enterprise-authoritative for enterprise-generated; **edge-generatable** for edge-generated, append-only | The edge must be able to raise a notification about its own hull with no shore path, exactly as it must be able to generate anomaly candidates (03 §11, `[D18]`) |
| `delivery_attempt` | **Edge-authoritative, append-only** | The node that attempted delivery is the only node that knows whether it succeeded. Same reasoning as maintenance action records `[D8]`: the node records what it *did* |
| `acknowledgement` | **Edge-authoritative, append-only; never overwritten or deleted; supersession recorded** | A human judgement, and therefore the same class as an anomaly tag under 03 §11 |
| `escalation` | Enterprise-authoritative; edge escalates locally within its own hull and reports | An afloat escalation to the on-watch station cannot wait for shore adjudication of the escalation policy |
| `channel_registration` | Enterprise-authoritative; not edge-writable | Configuration |
| `suppression_state` | Node-local, not reconciled | Coalescing is a per-node presentation concern with no cross-node meaning |

**Divergence budgets** (03 §11, document 11 §9.1) must exceed the scripted six-week patrol for `notification`, `delivery_attempt`, and `acknowledgement`. Document 11 §9.1's warning applies verbatim: a budget shorter than the patrol takes the hull read-only for the aggregate halfway through the scenario the budget exists to satisfy. **Declared value: 10 weeks** for all three, with the breach path exercised in test.

---

## 7. Acknowledgement and escalation

### 7.1 How a recipient acknowledges

`POST /api/v1/notification/notifications/{notification_id}/acknowledge`

- Requires `If-Match` on the notification's ETag (03 §4) and `Idempotency-Key`.
- Body: `{ acknowledged_by (from the token, never the body), channel_id, note? }`.
- Records an append-only `acknowledgement` row with the acknowledging **node** (`producer_node`, 03 §5.4) and the channel through which it arrived.
- Publishes `notification.acknowledged`.
- Idempotent: a second acknowledgement by the same identity returns the first. A *different* identity acknowledging is recorded as an additional row, not a replacement — for a dual-control proposal notification, two acknowledgements are the expected shape.

**Per channel:** `dashboard_badge` and `chat` acknowledge by user action; `email` carries a link back to the operator interface and cannot itself acknowledge (`supports_acknowledgement: false`); `watch_log` acknowledges by watch-stander entry, submitted through the edge instance's local surface; `bridge_alarm` acknowledges by alarm acknowledgement at the station.

**Acknowledgement is a human act.** `x-agent-eligible` is **false** on this operation and will never be true. An agent acknowledging a critical notification on a human's behalf defeats the entire escalation mechanism while leaving every dashboard green. This is DO-NOT-4.

### 7.2 What acknowledgement means, and does not

Acknowledgement means *a human received and saw this*. It does not mean the condition is handled, the proposal is adjudicated, or the work is scheduled. Notification never infers a domain outcome from an acknowledgement, and never writes one. The domain outcome arrives as its own event — `proposal.adjudicated`, `casrep_risk.cleared` — and closes the notification through §7.4's withdrawal path.

### 7.3 Escalation

Only `critical` escalates. Two hops, then terminal.

```python
@dataclass(frozen=True)
class EscalationPolicy:
    policy_id: str
    policy_version: int
    urgency: Urgency                       # CRITICAL only
    window: timedelta                      # monotonic. Default 15 min. TUNABLE.
    hops: tuple[EscalationHop, ...]        # max 2, enforced by constraint
    terminal: TerminalAction               # UNACKNOWLEDGED_CRITICAL — the only permitted value
```

| Hop | Ashore | Afloat |
|---|---|---|
| 0 (initial) | `email` + `chat` + `dashboard_badge`, in parallel | `watch_log` + `bridge_alarm`, in parallel |
| 1, after `window` unacknowledged | A **second holder** of the same routing role, all channels | `watch_station` — the on-watch billet, which is manned by definition |
| 2, after `2 × window` unacknowledged | `fleet_authority` cohort, all channels | `bridge_alarm` at elevated annunciation |
| Terminal, after `3 × window` | `unacknowledged_critical`: persistent red banner on the gateway fleet view for every `fleet_authority` holder, `fathom_notification_unacknowledged_critical` gauge at 1, Audit record, and the notification **stays open forever** | Same, plus a permanent watch-log entry |

**Default window: 15 minutes for `critical`. Explicitly tunable** per policy, per urgency, and per trigger, in Helm values. `PLACEHOLDER` — no architecture document supplies a value, and 15 minutes is a defensible engineering default for an alarm that halts a fleet-wide capability, not a researched figure. **OD-13.**

Four rules:

1. **The escalation clock starts at the first *deliverable* attempt on a channel with reach for that recipient** — not at notification creation. A notification deferred for six weeks because its ashore recipient was unreachable has **not** burned its window; on reconnect it starts at hop 0 with a full window. Otherwise every deferred critical notification arrives already terminal, and the terminal state means nothing. Tested by `test_escalation_timer_does_not_burn_while_undeliverable`.
2. **All deadlines are monotonic** (§4.4). A wall-clock deadline fires all at once or never at reconnection, per V-260520.
3. **Hops are bounded at two, and the terminal state is loud and permanent.** An unbounded escalation chain is a black hole with more steps.
4. **Escalation does not re-derive authority.** Hop targets are role cohorts resolved by §3.2 against ABAC, exactly as hop 0 is. Notification never widens a recipient's clearance to complete an escalation; if no cleared holder exists at a hop, that hop records `no_cleared_holder` and escalation advances.

### 7.4 Withdrawal

A notification is closed without acknowledgement when its condition resolves: `casrep_risk.cleared` closes the matching raise; `proposal.adjudicated` closes the matching adjudication request (consumed via the owning sub-application's declared row, or via the gateway — **OD-14**, since Notification is not a declared consumer of `proposal.adjudicated`); trigger B closes trigger A. Withdrawal cancels pending escalation, records `closed_by: withdrawal`, and — for `critical` — delivers a routine closing notification so the recipient learns the alarm they were escalating is resolved.

---

## 8. API surface, events, and deployment

### 8.1 API surface

Base path `/api/v1/notification/…` (03 §4, C25). Every operation declares `x-substitution` and `x-side-effects`; `x-agent-eligible` only where `x-side-effects` is `none` or `proposal-only` (03 §8.1, C1/D11).

| Operation | Purpose | `x-substitution` | `x-side-effects` | `x-agent-eligible` |
|---|---|---|---|---|
| `POST /notifications` | **The command path.** Create a notification directly. This is 03 principle 3's sanctioned mechanism for a producer that needs a specific action taken elsewhere. Returns a **receipt** with resolved recipients and accepted channels. The admission-control alarm's primary path (§2.5) | `required` | `state-changing` | no |
| `GET /notifications?recipient=&role=&urgency=&status=&subject_id=&changed_since=&limit=&cursor=` | List. `changed_since` is the read-model rebuild path (03 §4, obligation 5) | `required` | `none` | yes |
| `GET /notifications/{id}` | One notification, with its `delay` block (§6.4), delivery attempts, acknowledgements, and escalations | `required` | `none` | yes |
| `POST /notifications/{id}/acknowledge` | Acknowledge. `If-Match` + `Idempotency-Key` required. **Never agent-eligible** (§7.1) | `required` | `state-changing` | **no** |
| `GET /notifications/undelivered?older_than=&urgency=` | **The anti-black-hole read.** Every notification with no `DELIVERED` attempt, by age and urgency. The one operation an auditor uses to ask "what has this system failed to tell anyone?" | `required` | `none` | yes |
| `GET /notifications/{id}/deliveries` | Delivery-attempt history, per channel, per node | `required` | `none` | yes |
| `GET /channels` | The registered channel set with `reach`, `requires_connectivity`, `max_urgency_served`, `max_classification`, and health. The substitution-critical introspection surface | `required` | `none` | yes |
| `GET /urgency-policies?version=` | The §4.3 mapping as served data, with `urgency_policy_version` | `required` | `none` | yes |
| `GET /escalation-policies?version=` | The §7.3 policies | `required` | `none` | yes |
| `GET /recipient-preferences/{identity}` | Channel preferences. Read | `internal` | `none` | no |
| `PUT /recipient-preferences/{identity}` | Set preferences. **Rejects any attempt to suppress `critical`** with `urn:fathom:problem:notification:critical-not-suppressible` | `internal` | `state-changing` | no |
| `POST /notifications/{id}/escalate` | Force a hop. Operator/administrative | `internal` | `state-changing` | no |
| `PUT /channels/{channel_id}` | Register or update a channel. Startup-validated invariant of §5.6 re-checked | `internal` | `state-changing` | no |
| `POST /notifications:bulk` | Bulk, idempotent, fenced create — the 03 §4 bulk-write path, and the `X-Backfill: true` intake that **suppresses delivery entirely** while still recording (03 §5.3, `[D30]`) | `required` | `state-changing` | no |
| `GET /healthz`, `GET /readyz`, `GET /metrics` | Per 03 §4. `/readyz` includes read-model lag, outbox depth, per-channel health, and **the §5.6 offline-channel invariant** | `internal` | `none` | no |

**Substitution posture.** The `required` subset is deliberately narrow and deliberately includes `GET /channels` and `GET /notifications/undelivered`. A partner notification platform may be substituted, and the contract terms it must satisfy are observable ones (03 §10): a notification created is a notification recorded; a delivery attempted produces a `delivery.attempted` event; an undelivered critical notification is discoverable through the API. The **connectivity-independent-channel invariant of §5.4 rule 4 is a contract term**, tested by the conformance suite against a substitute's own declared channel set — it is externally observable and must be, because it is the property that keeps D17's remedy alive.

### 8.2 Events consumed

The complete set, equal to §2.1 and to `events/catalog.py` and `helm/values.yaml`, verified by `tools/check_event_catalog.py` (09 §8.2, §8.6):

| Event | Topic | Partition key | State |
|---|---|---|---|
| `readiness.recomputed` | `fathom.fleet-status.readiness.v1` | scope identifier | **Active** |
| `casrep_risk.raised` | `fathom.fleet-status.casrep_risk.v1` | `asset_id` | **Active** |
| `casrep_risk.cleared` | `fathom.fleet-status.casrep_risk.v1` | `asset_id` | **Active** |
| `mission_review.opened` | `fathom.pma.mission_review.v1` | `asset_id` | **Active** |
| `redesign_candidate.created` | `fathom.design-advisory.redesign_candidate.v1` | `niin` | **Active** |
| `proposal.created` | `fathom.*.proposal.v1` (**explicitly enumerated per slug**, never a wildcard — C38) | per producer | **Active** |
| `asset.status_changed` | `fathom.registry.asset.v1` | `asset_id` | **Required for routing; not a declared row — OD-6** |
| `adjudication_capacity.breached` / `.cleared` | `fathom.pma.adjudication_capacity.v1` | fleet (no subject id — 03 §5.4) | **Required; event does not exist — OD-8** |
| `sync.divergence_budget_breached` / `.cleared` | `fathom.sync.divergence.v1` | `asset_id` | Handler built, **disabled — OD-5** |
| `allowance_shortfall.detected` | `fathom.supply.allowance.v1` | `asset_id` | Handler built, **disabled — OD-1** |
| `proposal.expired` | `fathom.*.proposal.v1` | per producer | Handler built, **disabled — OD-2** |
| `proposal.adjudicated` | `fathom.*.proposal.v1` | per producer | Needed for withdrawal (§7.4) — **OD-14** |

Every consumer is idempotent on `event_id`; the inbox records receipt and applies state in **one** transaction with the `processed_at` suppression predicate and document 11 §3.2's comment template verbatim (`[D2]`). `replay: true` events are recorded and **never delivered** and never raise an operator-visible alert (03 §5.3, `[D30]`) — for this service that prohibition is unusually literal, since Notification is the component D30 names first.

### 8.3 Events published

Notification is a producer, with the full outbox discipline (03 §15.11, document 11).

| Event | Topic | Payload | Consumers |
|---|---|---|---|
| `notification.created` | `fathom.notification.notification.v1` | notification id, trigger ref, urgency, urgency_policy_version, recipient roles/identities, classification with `inherited_from`, `occurred_at` | `audit` |
| `delivery.attempted` | `fathom.notification.delivery.v1` | notification id, channel, node, outcome, attempt index, provider ref | `audit` |
| `delivery.confirmed` | `fathom.notification.delivery.v1` | notification id, channel, node, `delay` block | `audit`, `gateway` |
| `delivery.failed` | `fathom.notification.delivery.v1` | notification id, channel set attempted, terminal reason | `audit`, `fleet-status` |
| `notification.acknowledged` | `fathom.notification.notification.v1` | notification id, identity, channel, node | `audit` |
| `notification.escalated` | `fathom.notification.notification.v1` | notification id, hop, policy version, from/to | `audit` |
| `notification.unacknowledged_critical` | `fathom.notification.notification.v1` | notification id, elapsed, hops exhausted | `audit`, `gateway`, `fleet-status` |

⚠️ **Document 03 §6's catalog covers the nine sub-applications and does not enumerate platform-service topics.** These topics and their consumers must be added before the consumer-driven conformance tests of 03 §10 can be written against them. This is the same gap document 12 §3.4 logs as its OD-7; recorded here as **OD-15** so the two are resolved together rather than twice.

Partition key is `asset_id` for asset-scoped notifications and the notification's own scope identifier otherwise (03 §5.1). **Compaction key, where a topic is compacted, is `notification_id` — never the partition key** (`[D5]`, document 11 §2.2's CHECK constraint).

### 8.4 Deployment

Scaffold per document 09 §4, unmodified. Package `fathom_notification`; layering `api → services → repositories → models` with `events/` and `readmodels/` per 09 §4.1.

**Two deployment profiles, and this is a correction to two documents.**

| Profile | Runs | `producer_node` |
|---|---|---|
| **Enterprise** | The full service; ashore channels; escalation for ashore recipients; the shore end of reconciliation | `enterprise` |
| **Edge (per hull)** | Trigger intake from edge-resident producers; same-hull recipient resolution; `watch_log` and `bridge_alarm`; local escalation to `watch_station`; local acknowledgement capture; outbox for shore-bound records | `edge:<asset_id>` |

> **Correction.** Document 11 §1.2's deployment-profile table places `notification` among the platform services with **no** edge profile. Document 01 §12's afloat-resident subset does not list it either. Both are inconsistent with document 04 §11's own requirement that *"afloat notification will not resemble shore notification"* — a statement that is vacuous if no notification component runs afloat — and with 06 §4's six-week dark patrol during which two mission reviews and one corrective repair occur. **Notification requires an edge profile.** Without it, every afloat notification is Case 2 of §6.2, §5.4 rule 4 fails for every afloat recipient, and a category-4 CASREP risk raised on patrol day 21 reaches the maintainer standing next to the pump on patrol day 42. Raised as **OD-16**; this document proceeds on the corrected basis.

**NetworkPolicy** — default-deny, declared peers only (01 §11, 09 §8.6). Enterprise: own PostgreSQL, Redpanda, `auth` (identity/role cache, `changed_since`), the in-enclave SMTP relay, the in-enclave chat service (if OD-9 resolves to procuring one), `gateway` ingress. Edge: own PostgreSQL, local broker, the ship-LAN watch-log endpoint, the alarm annunciator (OD-10), the sync coordinator. **No public-internet peer on either profile** (01 §12, 09 DO-NOT-26) — which is why `chat` is in-enclave-only and why a hosted Slack cannot be a channel.

**Relay shard count: 8** (document 11 §2.5 default; no capacity figure in 06 §7 justifies deviating).

---

## 9. Testing

Document 09 §8.5 applies in full. The following are additions, and the first two are gates rather than tests.

### 9.1 `test_d17_admission_control_alarm_reaches_a_human` — the gate

The test document 06 §6's remedy depends on. Named for the finding so that whoever breaks it finds the reasoning.

```
GIVEN the demonstration capacity model of 06 §6 (840 candidates/month, 3× threshold = 2,520)
  AND an unadjudicated candidate queue driven to 2,521
WHEN PMA halts candidate generation and raises the alarm
THEN both intake paths of §2.5 are exercised, and:
  1. POST /notifications returns 2xx with a receipt naming >= 1 resolved recipient identity
     and >= 1 accepted channel with outcome DELIVERED
  2. the durable event path alone, with the command path failing, also produces delivery
  3. both paths together produce exactly ONE notification (idempotency)
  4. the notification's urgency is CRITICAL and its urgency_policy_version is recorded
  5. delivery is NOT suppressible by: an exhausted per-recipient rate limit; an active
     coalescing window on the same dedup key; recipient preferences set to suppress
     everything; quiet hours; a degraded primary channel
  6. with EVERY registered channel unusable, the §5.6 statically-declared minimal set
     still delivers, and fathom_notification_channel_total_failure is set
  7. unacknowledged for 3 x window, the notification reaches UNACKNOWLEDGED_CRITICAL,
     the gauge is 1, and the Audit record exists
  8. at no point does any code path return success without a DeliveryResult whose
     outcome is DELIVERED
```

Assertion 8 is the one that matters. Every other assertion checks a specific way the alarm could be swallowed; assertion 8 checks that no *unenumerated* way exists.

### 9.2 `test_six_week_disconnect_queue_then_reconnect` — the 06 §4 scenario, literally

Runs against a physically separate edge deployment where available, and a network-partitioned co-located one otherwise (06 §4's stated fallback).

```
GIVEN one SSN edge deployment, disconnected for a simulated six weeks (06 §4)
  AND the scripted scenario: one at-sea corrective repair, two mission reviews while dark
WHEN the following are generated during the disconnect:
     day  3: mission_review.opened, same-hull reviewer          (routine, afloat)
     day 12: casrep_risk.raised, predicted category 4, same-hull maintainer  (CRITICAL, afloat)
     day 21: mission_review.opened, SHORE analyst reviewer       (routine, ashore recipient)
     day 28: casrep_risk.raised category 3 + casrep_risk.cleared day 35     (the §6.5 pair)
     day 40: readiness.recomputed, band transition, ashore planner (routine, ashore recipient)
AND the hull reconnects on day 42
THEN:
  1. day 3 and day 12 were DELIVERED AT SEA, on watch_log (+ bridge_alarm for day 12),
     with delivered_at inside the disconnect and NOT on day 42
  2. day 12's escalation ran ITS FULL COURSE AT SEA against the watch_station, on the
     edge node, with no shore dependency
  3. day 21 and day 40 were DEFERRED, never reported DELIVERED, and counted in
     fathom_notification_deferred throughout
  4. on reconnect, deferred records drain in (producer, producer_node, monotonic_seq)
     order — day 21 before day 40 — and are deduplicated on event_id under a forced
     double-drain
  5. every drained record renders occurred_at as its headline, delay populated,
     delay_is_material true, and disconnection_context naming the 42-day disconnect
  6. the day-28/35 pair COLLAPSES per §6.5, is delivered ashore as ROUTINE, raises no
     ashore alarm, and BOTH original timestamps plus the at-sea day-28 watch-log
     delivery survive in the record
  7. deferred day-21 and day-40 escalation clocks are UNSTARTED at drain (§7.3 rule 1)
  8. nothing is lost: created count == delivered + deferred-then-delivered + collapsed,
     with zero unaccounted
  9. the divergence budget for notification, delivery_attempt, and acknowledgement was
     never breached (10-week declared value vs 6-week patrol)
 10. a mid-drain backward clock step of -90 s (V-260520, makestep 1 -1) changes neither
     the drain order nor any rendered occurrence time
```

### 9.3 Other required tests

| Test | Asserts |
|---|---|
| `test_delayed_notification_never_presents_delivery_time_as_occurrence_time` | Across the API response, every channel body template, and the served list default sort: `occurred_at` is the headline and `delivered_at` never substitutes for it. Property-based over arbitrary delays |
| `test_rate_limit_never_suppresses_critical` | Property test over arbitrary suppression states; no `critical` is ever withheld |
| `test_no_offline_channel_is_a_hard_error_not_a_queue` | An urgent/critical notification for an afloat recipient with no connectivity-independent channel raises, returns `409`, degrades `/readyz`, and produces **no** `DEFERRED` row |
| `test_service_refuses_to_start_without_offline_critical_channel` | The §5.6 startup invariant |
| `test_unknown_posture_fails_safe_to_afloat` | §2.4 / §5.4 rule 3 |
| `test_escalation_timer_does_not_burn_while_undeliverable` | §7.3 rule 1 |
| `test_agent_cannot_acknowledge` | `x-agent-eligible` false on acknowledge, asserted from the generated OpenAPI **and** rejected at runtime under an accountable-autonomous workload identity |
| `test_unroutable_trigger_self_alarms` | §3.2 rule 4 |
| `test_channel_below_classification_is_not_selected` | Filtering inside candidate selection; content-free pointer fallback; no redact-and-send path (`[D13]`) |
| `test_readiness_recomputed_storm_is_coalesced` | 1,000 `readiness.recomputed` events across one asset produce notifications only on band transitions |
| `test_replay_events_never_deliver` | `replay: true` records and delivers nothing and raises no operator-visible alert (`[D30]`) |
| `test_backfill_suppresses_delivery` | `X-Backfill: true` on `POST /notifications:bulk` records without delivering (03 §5.3) |
| Fault injection (document 11 §11.1) | Every state-changing operation × every injection point: no state change without its event |
| Conformance suite `packages/contracts/conformance/notification/` | Contract, event, fault-injection, consumer-driven, and manifest categories (03 §10). Includes the §5.4 rule 4 invariant as a contract term testable against a substitute |
| Consumer-driven tests contributed | Into `fleet-status`, `pma`, `design-advisory`, and every proposal producer's suites, asserting what Notification depends on: `predicted category` present on raise, `assigned reviewer` present on review open, `authority_class` and `valid_until` present on proposal creation |

### 9.4 Reference dataset

Deterministic runs from `data/synthetic` (document 13), extended with: the 06 §6 capacity trajectory that crosses 2,520; the 06 §4 six-week scenario timeline of §9.2; a recipient fixture set spanning all six `AuthorityClass` values plus `watch_station`, ashore and afloat, with distinct clearances; and a channel fixture set exercising every combination of `reach` × `requires_connectivity` × `max_classification`.

### 9.5 Static gates (CI `lint` stage, per 09 §6.2)

| Gate | Enforces |
|---|---|
| `ntf-critical-not-suppressible` | No call path from a `CRITICAL` notification into the suppression, rate-limit, or preference engines (import-linter contract + AST check) |
| `ntf-no-wallclock-deadline` | No wall-clock arithmetic in escalation, retry, coalescing, or lease code. Extends document 11's `FTH004` |
| `ntf-occurred-at-headline` | No channel body template or serializer places `delivered_at`/`recorded_at` where `occurred_at` belongs |
| `ntf-no-public-egress` | No channel implementation references a public-internet host or an external DNS name (01 §12, 09 DO-NOT-26) |
| `ntf-ack-not-agent-eligible` | `x-agent-eligible` is absent on the acknowledge operation |
| `ntf-catalog-parity` | `tools/check_event_catalog.py` exit 0: `events/catalog.py` == `helm/values.yaml` == 03 §6's rows for this slug |
| `ntf-no-queue-as-delivery` | No code path maps `DEFERRED` to `DELIVERED`, and no metric sums them |

---

## 10. Explicit DO-NOT list

**DO-NOT-1 — Never let a critical or afloat-relevant notification depend on reconnect when a same-ship alarm path exists.**
If the recipient is on the hull, the notification is delivered on the hull, at sea, immediately, through a channel with `requires_connectivity: false`. Queuing it for the ship-to-shore link is not a late delivery; it is a lost one — a category-4 CASREP risk raised on patrol day 12 and emailed on patrol day 42 was never delivered to the maintainer who was standing next to the equipment. Where no connectivity-independent channel exists for an urgent-or-critical afloat recipient, **fail hard and loudly** (§5.4 rule 4); do not queue and hope. *(04 §11, 01 §12, 06 §4)*

**DO-NOT-2 — Never present a delayed notification's delivery time as its occurrence time.**
`occurred_at` is the headline, always, in every channel body, every list, every default sort. `recorded_at`, `delivered_at`, and `received_at` are secondary and separately labelled. The `delay` block is populated and rendered whenever the delay is material, and `dispersion_ms` qualifies the timestamp's own precision when the generating node's clock was in holdover. A three-week-old risk flag presented as "raised just now" makes every downstream judgement against a false premise — the same class of defect as `[D22]`. *(03 §5.4, §6.4 here)*

**DO-NOT-3 — Do not let any suppression, coalescing, rate-limit, preference, quiet-hours, or channel-health mechanism be reachable from a `critical` notification.**
Every one of those is a legitimate requirement for the other two classes and a plausible route to swallowing the admission-control alarm. Structural unreachability, not a remembered exemption. *(06 §6, §4.6 here)*

**DO-NOT-4 — Do not let an agent acknowledge a notification.**
Acknowledgement is the assertion that a human saw this. An agent acknowledging on a human's behalf disables escalation while leaving every dashboard green — a strictly worse outcome than no acknowledgement mechanism at all. `x-agent-eligible` is false on that operation permanently. *(03 §8.1, §8.3)*

**DO-NOT-5 — Do not report a queued notification as delivered.**
`DEFERRED` and `DELIVERED` are distinct outcomes with distinct metrics, and no code path or dashboard sums them. A delivery-rate panel that counts queued items reads green while nobody has been told anything. *(§6.1)*

**DO-NOT-6 — Do not subscribe to an event document 03 §6 does not declare `notification` a consumer of, and do not use a wildcard subscription.**
Six declared rows (§2.1). Handlers for undeclared triggers ship disabled and are enabled by catalog amendment plus a values change, reviewed against `tools/check_event_catalog.py`. `fathom.*.proposal.v1` is expanded to an explicit per-slug list — the nine `SubAppSlug` topics **plus `fathom.audit.proposal.v1`**, the same named platform-service exception `30-gateway.md` §4.1 makes, added here because `purge`/`rewrap` proposals are otherwise silently unrouted to any recipient. *(C38, 09 DO-NOT-14)*

**DO-NOT-7 — Do not deliver a `replay: true` event, and do not let backfill notify.**
Document 03 §5.3 names notifications first among the live side effects replay must not fire, and document 01 §12 repeats it. Record and suppress. Conversely, **do not treat an edge drain as a replay**: a six-week-old maintenance action is a first emission of a real fact and must fire its normal effects ashore. *(`[D30]`, document 11 §9.3a)*

**DO-NOT-8 — Do not compare wall clocks for anything: ordering, deduplication, escalation deadlines, retry backoff, coalescing windows, or lease expiry.**
Order on `(producer, producer_node, monotonic_seq)` or the HLC; measure durations monotonically. STIG V-260520's mandated backward step fires exactly when a reconnecting hull drains its outbox — which for this service is exactly when six weeks of escalation timers would otherwise fire at once or never. *(`[D29]`, 03 §5.4, document 11 DO-NOT-2/3)*

**DO-NOT-9 — Do not send domain content on a channel not accredited to the notification's classification level, and do not redact-and-send.**
Filter inside candidate selection. Where no adequately accredited channel exists, send a content-free pointer and record `body_withheld_classification`. Do not let a notification body disclose a compartmented contributor that 06 §5's aggregation policy excludes from the rollup it came from. *(`[D13]`, 03 §7.3, 06 §5)*

**DO-NOT-10 — Do not treat a notification as skippable because the recipient is unreachable.**
Existence is never conditioned on reachability. Create, record, and route it; defer the *delivery* if you must. Binding notification existence to liveliness is the same error document 11 DO-NOT-5 forbids for write authority, and it fails in the same direction: the dark hull loses the thing only it needs. *(03 §11, document 11 DO-NOT-5)*

**DO-NOT-11 — Do not infer or write a domain outcome from an acknowledgement.**
Acknowledgement means seen, not handled. Notification never adjudicates a proposal, clears a risk, or resolves a shortfall. *(03 principle 3, §7.2 here)*

**DO-NOT-12 — Do not recompute `authority_class`, widen a clearance, or expand a role cohort beyond the trigger's subject scope.**
Read the `authority_class` the owning sub-application set (03 §7.2.1). Never widen clearance to complete an escalation. Never expand a role to "everyone who holds it" — an item-scoped risk flag mailed fleet-wide is how a channel becomes noise, and a noisy channel is a swallowed alarm with extra steps. *(03 §7.2.1, §3.2 here)*

**DO-NOT-13 — Do not add a fourth urgency class, or a class whose behaviour is not mechanically distinct.**
Three classes, each changing what the code does (§4.1). A level that only changes a label is decoration, and recipients negotiate the middle of any scale longer than three.

**DO-NOT-14 — Do not make `critical` delivery a sequential cascade.**
Parallel fan-out across every channel with reach. A cascade's first hop is a place for a critical alarm to sit for the length of a timeout. *(§5.4 rule 2)*

---

## 11. Open decisions

| ID | Decision | Owner | Consequence if unresolved |
|---|---|---|---|
| **OD-1** | **`allowance_shortfall.detected` does not list `notification` as a consumer**, yet 04 §11 and 01 §5 both promise Notification covers "shortfalls." Add the row, or strike "shortfalls" from both | Architecture + Supply | A documented capability does not exist. Supply officers are never told about shortfalls by the service whose charter names them |
| **OD-2** | **`proposal.expired` declares `gateway`, `audit` only.** Should `notification` consume it? An expired unadjudicated proposal is arguably the most notification-worthy proposal event | Architecture + Gateway | Proposals silently expire. The adjudicator who missed the window is never told they missed it |
| **OD-3** | Confirm `watch_station` as a **non-adjudicating routing role** alongside 03 §7.2.1's six `AuthorityClass` values | Architecture | No canonical role names the on-watch billet, so afloat escalation hop 1 has no target and afloat `critical` cannot escalate at all |
| **OD-4** | Confirm the promotion boundaries: CASREP **category 3/4** → `critical`; shortfall blocking a category-3/4 work order → `critical` | Fleet Status + TYCOM SME | Either alarm fatigue (boundary too low) or a category-4 risk that never reaches a dark hull (too high) |
| **OD-5** | Declare consumers for `fathom.sync.divergence.v1` in 03 §6 (document 11 §9.1 declares the event; the catalog declares no consumer) | Architecture + Sync | A breached divergence budget produces a UI banner on the affected node and reaches nobody ashore, which is the opposite of 11 §9.1's stated purpose |
| **OD-6** | Add `notification` as a consumer of `asset.status_changed`, or supply another posture source | Architecture + Registry | Channel selection cannot distinguish ashore from afloat. Interim: unresolved posture fails safe to AFLOAT (§2.4) |
| **OD-7** | **Confirm the admission-control alarm's owning role.** This document routes to `fleet_authority` + the pre-screener's named accountable owner (§2.5). The alternative proposed in framing is a PMA program lead or on-duty supervisor | PMA + TYCOM + program management | `PLACEHOLDER` in production. The mechanism works; the alarm may reach the wrong desk. Configuration-only to change |
| **OD-8** | Add `adjudication_capacity.breached` / `.cleared` to PMA's rows in 03 §6 | Architecture + PMA | The durable half of §2.5's dual-path intake has no declared event, leaving only the synchronous command — and a single-path critical alarm |
| **OD-9** | **Is there an in-enclave chat service?** A hosted Slack is prohibited by 01 §12 and 09 DO-NOT-26 | Program IT | The `chat` channel is simply absent. Ashore recipients fall back to `email` + `dashboard_badge`; neither alone carries `critical`, so ashore critical delivery becomes thinner than intended |
| **OD-10** | **Afloat alarm annunciation integration** — is `bridge_alarm` a real hull integration or does `watch_log` carry `critical` alone? | Program + ship systems | Demonstration uses `LoopbackAlarmChannel` with `annunciation: simulated`. The afloat critical path is demonstrated but not proven against hardware |
| **OD-11** | Idempotency-key retention for edge-sync-reachable operations — 09 open question 5, unresolved. This document sets **8 weeks** | Architecture (centrally, per 09 OQ 5) | A hull's retry window is weeks; a 24-hour default duplicates every acknowledgement replayed after reconnect |
| **OD-12** | Add notification delivery and acknowledgement records to document 11 §9.3's drain priority table (proposed: class 1 for critical/urgent, class 3 for routine) | Sync | Notification records drain behind bulk telemetry, so shore learns hours or days late that a hull was told, and a burst-telemetry drain starves the acknowledgement stream |
| **OD-13** | Confirm the escalation windows: **15 min** critical, 8 h urgent acknowledgement target, and the `3 × window` terminal | TYCOM + PMA | `PLACEHOLDER`. Too short escalates every alarm to the fleet; too long makes escalation ceremonial |
| **OD-14** | Notification needs `proposal.adjudicated` (or a gateway-mediated equivalent) to withdraw an adjudication-request notification | Architecture + Gateway | Adjudicated proposals keep escalating. A `critical` dual-control request could reach terminal `unacknowledged_critical` after being approved |
| **OD-15** | **Add platform-service topics and their consumers to 03 §6.** Same gap document 12 §3.4 logs as its OD-7 | Architecture | `fathom.notification.*` has no declared consumers, so 03 §10's consumer-driven conformance tests cannot be written and the delivery-evidence stream is unverifiable by contract |
| **OD-16** | **Notification requires an edge profile.** Correct document 11 §1.2's profile table and document 01 §12's afloat-resident subset | Architecture | Without it there is no afloat notification at all, §5.4 rule 4 fails for every afloat recipient, 04 §11's "afloat notification will not resemble shore notification" is unimplementable, and DO-NOT-1 is unsatisfiable. **This is the most consequential item in this table** |

---

## 12. Definition of Done

The shared Definition of Done in [09 §8](09-monorepo-and-conventions.md) applies **in full, with nothing removed** — OpenAPI generated from code and CI-validated, annotation coverage, canonical identity, `changed_since` reads, RFC 9457, idempotency, ETag/If-Match, correlation, classification labelling with `inherited_from`, outbox and inbox with the document 11 §3.2 template verbatim, one logical database, migrations, NetworkPolicy parity, non-root image with nothing installed at container start, `/healthz` `/readyz` `/metrics`, conformance suite green, README, ADRs for deviations.

Service-specific additions, all of which must hold:

1. **`test_d17_admission_control_alarm_reaches_a_human` green**, all eight assertions, including assertion 8. This is a release gate, not a test. Document 06 §6's admission control is not delivered until it passes.
2. **`test_six_week_disconnect_queue_then_reconnect` green**, all ten assertions, run against a physically separate edge deployment where 06 §4's primary option holds and a network-partitioned one otherwise.
3. **All six declared triggers of §2.1 implemented**, and `ntf-catalog-parity` green: `events/catalog.py` == `helm/values.yaml` == document 03 §6's rows for this slug, in both directions.
4. **Handlers for triggers C, D, E of §2.3 implemented, tested, and shipped disabled**, each with its OD reference in the values comment.
5. **The channel abstraction is one interface with at least five registered implementations**, spanning both `reach` values and both `requires_connectivity` values, and `GET /channels` serves their declared capabilities.
6. **The §5.6 startup invariant is live** — the service refuses to start when no `afloat`-or-`both`, `requires_connectivity: false`, `critical`-capable channel is registered while any afloat holder exists for any routed role.
7. **`§5.4` rule 4 is a hard error everywhere** — `409` on the command path, `critical` self-alarm on the event path, `/readyz` degraded, zero `DEFERRED` rows. `test_no_offline_channel_is_a_hard_error_not_a_queue` green.
8. **All three enforcement layers of §4.6 in place** and `ntf-critical-not-suppressible` green.
9. **The §6.4 presentation rule holds end to end**, including in `apps/web`, and `ntf-occurred-at-headline` green. `test_delayed_notification_never_presents_delivery_time_as_occurrence_time` green.
10. **The §6.5 collapse implemented and tested**, with both original timestamps and the at-sea delivery preserved.
11. **Escalation bounded at two hops with a loud permanent terminal state**, timers monotonic, clock starting at first deliverable attempt. `test_escalation_timer_does_not_burn_while_undeliverable` green.
12. **`GET /notifications/undelivered` served**, and wired to an alert on any `critical` undelivered for more than one escalation window.
13. **Conflict policies declared for all six aggregates** (§6.6), divergence budgets declared at 10 weeks for the three edge-writable ones, with the write gate wired and the breach path exercised.
14. **All seven static gates of §9.5 green in CI.**
15. **Consumer-driven tests contributed** into `fleet-status`, `pma`, `design-advisory`, and every proposal producer's conformance suite.
16. **Both deployment profiles build, deploy, and pass the suite**, and the edge profile is exercised in the 06 §4 scenario.
17. **A declared purge path** for all six aggregates plus outbox and inbox, by crypto-shred per 03 §13.1, stating for each whether it is legally immutable or operationally append-only.
18. **Every open decision in §11 is either resolved and this document updated, or explicitly accepted as a demonstration-scope risk with a named owner.** **OD-16 cannot be closed by silence** — without an edge profile this service does not do the thing document 04 §11 says it exists to do, and **OD-7** must be answered before the admission-control alarm is claimed as delivered to the right desk rather than merely to a desk.
