# Build 30 — API Gateway / BFF

| | |
|---|---|
| **Status** | Build specification. Prescriptive — an implementer follows it rather than interpreting it |
| **Slug** | `gateway` (document 03 §3.1). Directory `platform/gateway/`, package `fathom_gateway`, base path `/api/v1/gateway/`, consumer group `fathom-gateway-v1`, database cluster `fathom-gateway-pg` |
| **Purpose** | Build specification for the single ingress fronting the operator interface, the practitioner surfaces, the agent tool calls, and the batch scoring write path: authentication and delegated-authority token exchange, per-caller rate limiting, view-model composition across sub-applications, and the unified proposal adjudication queue |
| **Resolves** | Finding **D32** (document 05 §2.2) — *"the gateway becomes a stateful all-domain, all-classification consumer to build the unified adjudication queue, contradicting its stated stateless-composition role."* Disposition FIX. §2 of this document is that fix |
| **Binding contracts** | [03 §4](../architecture/03-integration-contracts.md) (REST conventions — the gateway sits in front of every one of them), [03 §5](../architecture/03-integration-contracts.md) (event backbone), [03 §6](../architecture/03-integration-contracts.md) ("Proposals — a convention"), [03 §7.2 / §7.2.1](../architecture/03-integration-contracts.md) (Proposal and the adjudication authority table), [03 §7.3](../architecture/03-integration-contracts.md) (ClassificationLabel), [03 §8](../architecture/03-integration-contracts.md) (agent authority and tool surfaces), [03 §12](../architecture/03-integration-contracts.md) (classification posture), [03 §13](../architecture/03-integration-contracts.md) (data remediation — names gateway-held read models explicitly), [03 §15](../architecture/03-integration-contracts.md) (obligations) |
| **Assigned by** | [04 §11](../architecture/04-subapplication-architectures.md) "API Gateway / BFF"; [01 §3](../architecture/01-system-architecture.md) (Sustainment Plane), [01 §4](../architecture/01-system-architecture.md) (system context), [01 §5](../architecture/01-system-architecture.md) (platform inventory), [01 §8.4](../architecture/01-system-architecture.md), [01 §8.5](../architecture/01-system-architecture.md) |
| **Conventions** | [09 — Monorepo and Conventions](09-monorepo-and-conventions.md) in full: scaffold §4, API rules §5, DoD §8, DO-NOT §9. [10 — Shared Packages](10-shared-packages.md) for `Proposal`, `ClassificationLabel`, `EventEnvelope`, `topics`. [11 — Outbox & Sync Library](11-outbox-sync-library.md) for the inbox, clock discipline, and provisional-identity resolution |
| **Quantities** | Every figure is cited from [06 §6](../architecture/06-demo-decisions-and-assumptions.md) or [06 §7](../architecture/06-demo-decisions-and-assumptions.md). None is invented (09 §9.5 item 31) |
| **Classification** | Internal. The service operates single-level at `U` for the synthetic demonstration (03 §12, 06 §5), by **configuration**, not by assumption — see §7 |
| **Verification note** | Following 09's convention: library and protocol selections were verified against documents 01/03 as of a **January 2026 knowledge cutoff**. RFC 8693 support in the chosen identity provider (§5.3) is a **dependency to confirm at implementation time**, not a settled fact |

---

## 1. Purpose and scope

### 1.1 What document 04 §11 assigns

Document 04 §11 states the assignment in five clauses:

> *"Single ingress for the operator interface and for agent tool calls. Responsibilities: authentication, token exchange for delegated authority, rate limiting per caller identity, view-model composition across sub-applications, and construction of the unified proposal adjudication queue by consuming the `fathom.*.proposal.v1` topic pattern. Composition happens here, which is what keeps sub-applications from calling one another synchronously."*

Document 01 §5's platform inventory says the same in one line, and document 01 §4's system context places the gateway on every path into the system: the four operator personas reach it through the Operator Web UI, the Domino-hosted agent runtimes reach it for tool calls, the practitioner Apps reach it, and — per 09 §4.4.2's sanctioned edge set — the Domino scoring Jobs reach it to write predictions through PdM's bulk ingest operation.

The gateway is therefore the one component whose failure is indistinguishable from the failure of the whole system. Two consequences run through every section below: it must hold as little state as the job permits, and it must never become the place where a correctness or security property is *decided* rather than *carried*.

### 1.2 The five responsibilities, and where each is specified

| # | Responsibility (04 §11) | Section | The hard part |
|---|---|---|---|
| 1 | Authentication | §5.1–§5.2 | Authentication only. Authorization is the receiving sub-application's, per 03 §4 and obligation 7 |
| 2 | Token exchange for delegated authority | §5.3–§5.6 | Carrying a *human's* authority through an agent to a sub-application, when 03 §8.3 defines two authority classes and one of them has no human requester |
| 3 | Rate limiting per caller identity | §6 | A per-identity token bucket with no shared cache in the 01 §11 inventory |
| 4 | View-model composition | §3 | Fan-out-and-gather without chained upstream calls, inside 06 §7's latency budget, with honest partial failure |
| 5 | The unified proposal adjudication queue | §2, §4 | **Finding D32.** This is the whole of §2 |

### 1.3 What this document does not govern

| Out of scope here | Governed by |
|---|---|
| The operator UI's visual design, component library, routing, state management, user flows | Deferred to the look-and-feel wave (09 §1.2, 09 §2.6, 09 OQ-6). This document specifies the API the UI consumes and nothing about how it renders |
| OIDC provider configuration, realm layout, ABAC policy authoring, CAC/PIV federation, the token-exchange grant's server side | `platform/auth/` and its build document (04 §11 "Identity & Authorization"). The gateway is a **client** of `auth`, never a policy decision point |
| Audit record schema, retention, immutability, object-store spillover thresholds | `platform/audit/` and its build document. §5.8 states what the gateway sends, not how it is stored |
| Each sub-application's own `/proposals` operations, payload validation, claim lease implementation, re-validation at adjudication | Documents `20`–`28`, per 03 §7.2. The gateway **proxies** these; it does not implement them (§4.6) |
| Tool manifest content and generation | 03 §8.2, `packages/agent-tooling`, 10 §7 |
| Outbox, inbox, clock discipline, provisional-identity resolution mechanics | [11](11-outbox-sync-library.md). This document declares which of them the gateway uses (§4.3) and which it correctly does not (§9) |
| Any quantity | 06 §6, 06 §7 |

### 1.4 Traceability

| Requirement | Source | Where discharged |
|---|---|---|
| Single ingress; slug-namespaced base paths prevent collision | 03 §4, C25 | §8.1 |
| No synchronous cross-sub-application calls on a compute path; composition is the gateway's | 03 principle 2 | §2.3, §3.1, §3.6, §12 |
| Unified queue from the `fathom.*.proposal.v1` pattern, without sub-applications knowing it exists | 03 §6 | §4.1 |
| Queue presents `authority_class` and `blast_radius` for routing and filtering | 03 §7.2, §7.2.1, D16 | §2.4, §4.5 |
| Adjudication requires a claim and `If-Match`; re-validation at approval | 03 §7.2, D16 | §4.6 |
| Two agent authority classes; delegated token carries the user's authority | 03 §8.3, 01 §8.5, D12 | §5.3, §5.4 |
| Domino Endpoint calls proxied so caller identity reaches audit | 03 §8.3, D12, 02 §4.3 | §5.6 |
| Per-caller-identity token bucket; per-sub-application limits declared in charts | 03 §4 | §6 |
| `X-Classification` read and propagated; enforcement at the receiver, never the gateway alone | 03 §4, §7.3, obligation 7, D13 | §7 |
| Single-level demonstration posture, stated rather than implied | 03 §12, 06 §5 | §7.4 |
| A declared purge protocol covering **gateway-held read models** | 03 §13 item 2, D15 | §4.7 |
| No wildcard subscriptions | C38, 09 §8.2 | §4.2 |
| The gateway becomes a stateful all-domain all-classification consumer | **D32** | **§2** |

---

## 2. Resolution of finding D32

### 2.1 The finding, and why it is not editorial

Document 05 §2.2 records:

> **D32** | MED-HIGH | *The gateway becomes a stateful all-domain, all-classification consumer to build the unified adjudication queue, contradicting its stated stateless-composition role* | **FIX**

The contradiction is real and it is between two documents that are both binding. Document 04 §11 describes the gateway as the place composition happens — a *composition* layer, which implies it derives its responses from upstream calls and holds nothing. The same paragraph instructs it to build the unified queue by consuming a topic pattern across nine sub-applications. Consuming a topic pattern means holding a projection. A projection is state. Nine sub-applications means all domains. Topics segregated by classification (03 §5.1) means, if the subscription is genuinely `fathom.*.proposal.v1`, all classification levels present.

The finding's disposition is FIX rather than DECIDE, which means the review judged it reconcilable by design rather than requiring a program decision. But nothing in documents 01, 03, or 04 says *how*, and `packages/canonical-schemas` — which already ships the pattern constant — records the tension and explicitly declines to resolve it:

> `PROPOSAL_TOPIC_PATTERN` … *"Note document 05 D32: the gateway becoming a stateful all-domain consumer contradicts its stateless-composition role — that tension is document 04's to resolve, not this package's."* (10 §4.5)

Document 04 did not resolve it. **This document resolves it, and §2.7 records that as a decision this document makes rather than one the architecture dictated.**

Three failure modes make it worth resolving precisely rather than plausibly:

1. **A store with no purge path is an accreditation blocker.** Document 03 §13 item 2 names *"gateway-held read models"* by hand in the list of stores a purge protocol must cover, because D15 is an accreditation blocker. A queue holding nine domains' proposal payloads and evidence excerpts is a tenth copy of nine domains' content, with a remediation problem proportional to its size.
2. **An all-classification consumer makes labels decorative.** D13's argument applies unchanged: a consumer subscribed to a mixed-classification topic set must be accredited at the highest level present and must materialize that content into its own database. That is system-high by construction, at the single component every user reaches.
3. **A queue that is the least available surface in the system defeats D16.** The adjudication queue is the human-in-the-loop control the entire propose-and-adjudicate boundary rests on (01 §8.4, 03 §7.2). Whatever architecture it has, it must not make the control less reliable than the thing it controls.

### 2.2 The two candidate resolutions

**Option (a) — a genuinely minimal read model.** The gateway consumes the proposal topics and projects *metadata only*: identity, kind, owner, authority class, blast radius, status, lifecycle, and the scalars and booleans a queue must sort, filter, route, and warn on. The `payload`, the `evidence[]` array, and the free-text `rationale` are **not projected**; they stay in the owning sub-application and are fetched synchronously, for one proposal, at the moment a human opens it to adjudicate.

**Option (b) — no queue at the gateway at all.** The gateway holds nothing and, on each queue-view request, fans out to each of the nine sub-applications' own `GET /api/v1/{slug}/proposals` operations, merges, sorts, and paginates the results in memory.

Option (b) is superficially attractive because it makes the "stateless composition layer" description literally true. It is rejected, on five grounds.

**First — it does not actually violate principle 2, and that is the problem with the argument for it.** Document 03 principle 2 reads:

> *"No synchronous cross-sub-application calls on a compute path. … Synchronous reads are permitted only for user-facing composition, and that composition is performed by the API gateway rather than by sub-applications calling one another in chains."*

A queue view is user-facing composition. So principle 2 does not forbid option (b) — which means principle 2 cannot be used to decide between them, and the decision has to rest on properties principle 2 does not address. The task framing anticipated that principle 2 would rule (b) out; on the text, it does not. **This is recorded as a correction to the framing rather than glossed over.** What rules (b) out is the following four items.

**Second — cross-source pagination is not composable, and the amplification is unbounded.** A unified queue needs a total order across nine independently-paginated collections. To return page *k* of a merged, globally ordered result, a fan-out merger must read enough of each source to guarantee no unseen item belongs on the page — which for a deep cursor means reading, from every one of the nine, everything ahead of the cursor. The request amplification is not 9×; it is 9 × (offset + limit) rows for a design whose whole pagination convention is cursor-based specifically to avoid offsets (03 §4). Filtering makes it worse: `?authority_class=fleet_authority&status=proposed` must be pushed into nine independent filter implementations and trusted to be identical, or applied after the fact over an over-fetch.

**Third — availability multiplies at exactly the wrong component.** Under (b) the queue view is available only when all nine owners are. Partial failure has no honest rendering: a queue missing one sub-application's proposals is not a degraded queue, it is a *wrong* queue, and the failure mode is silent — an adjudicator sees a shorter list and adjudicates it. D16 exists because two people adjudicating one proposal produces two work orders; a proposal nobody can see produces none, and nothing alarms.

**Fourth — the state does not actually go away; it goes undeclared.** Document 06 §6 sets admission control: *"If unadjudicated candidates exceed 3× monthly throughput, candidate generation halts and an alarm raises."* That is a continuously-maintained global count across nine owners. Under (b) it becomes nine periodic count queries feeding a cached aggregate — a read model with no schema, no rebuild path, no purge path, and no declaration. Option (a)'s state is small, typed, versioned, and testable; option (b)'s state is the same information with none of those properties.

**Fifth — it contradicts the contract that makes the convention work.** Document 03 §6's proposal convention states its own purpose: publication to `fathom.<slug>.proposal.v1` exists *"permitting the gateway to build a unified adjudication queue from a topic pattern **without any sub-application knowing the queue exists**."* Under (b), every sub-application must expose, document, version, filter, sort, and conformance-test a `/proposals` **collection** operation shaped for a cross-domain queue it is not allowed to know about. The convention's decoupling property is inverted: nine services acquire a shared, implicit, untestable contract about queue semantics. Under (a), each sub-application publishes a fact about its own domain and exposes a single-resource read — which it needs anyway, for the detail fetch and for adjudication.

### 2.3 The decision

> **DECISION D32-R1. Option (a).** The gateway maintains a **metadata-only, non-authoritative, classification-partitioned, rebuildable projection** of proposals — the `proposal_queue` read model of §2.4 — populated from an **explicitly enumerated** set of `fathom.<slug>.proposal.v1` topics at the deployment's declared classification level. Proposal `payload`, `evidence[]`, and `rationale` are never projected, never stored, and never cached; they are fetched from the owning sub-application, one proposal at a time, when a human opens it (§4.6). Every proposal state transition — claim, adjudicate — is **proxied** to the owning sub-application; the gateway never mutates a proposal in its own store on an operator's behalf.

The description in 04 §11 is therefore amended, not abandoned. The gateway is not stateless. It is **stateless with respect to domain content, and stateful only with respect to a queue index it can throw away.** That distinction is what makes D32 reconcilable, and it is only meaningful if it is enforced rather than intended. Four properties enforce it, each with a test named in §10.

**Property 1 — content exclusion is a schema-level allowlist, not a code convention.** The projection's column set is a frozen allowlist asserted against SQLAlchemy metadata, so adding a column fails CI (§10, `test_d32_read_model_column_allowlist`). Separately, a canary test writes a `Proposal` whose `payload` and whose `evidence[].excerpt` each contain a unique string, runs it through the real consumer into a real PostgreSQL, then scans every text and JSONB column in the gateway database and asserts neither string appears (`test_d32_projection_discards_payload_from_the_wire`). The second test constrains the *store*, not the code path, so a future refactor cannot reintroduce the defect quietly.

There is a second, independent payoff. Because the projection holds no `rationale`, no `evidence[].excerpt`, and no `payload`, **the gateway's own database contains no free text authored outside the program.** Document 03 §9 and D14 make retrieved and user-supplied content untrusted input; the gateway is the component that assembles responses for both operators and agents, and a queue response that carried agent-authored prose and corpus excerpts would be a broad, structurally-unavoidable injection surface at the single ingress. Under D32-R1 a queue response is entirely structured fields — enumerations, UUIDs, booleans, and two floats. The untrusted text exists only in the single-proposal detail response, which is streamed from the owner, not persisted, and not logged (09 §4.8 forbids logging retrieved corpus text).

**Property 2 — the projection is non-authoritative, and nothing depends on it being correct.** No decision is taken from the read model. Authority-versus-blast-radius (03 §7.2.1) is checked by the owning sub-application at adjudication; the read model carries `authority_class` and `blast_radius` so a UI can *route and filter*, which is presentation. Staleness (`valid_until`, `baseline_epoch`) is re-validated by the owner at adjudication, per 03 §7.2's mandatory re-validation rule; the read model carries them so the queue can *warn*, not so it can *reject*. The claim lease is the owner's; the read model reflects it. If the projection is stale, wrong, or empty, no proposal is mis-adjudicated — the queue is merely a worse index. This is the property that makes the state safe, and §10's `test_d32_stale_projection_cannot_cause_a_wrong_adjudication` asserts it by adjudicating against a deliberately-poisoned row and confirming the owner's re-validation rejects it.

**Property 3 — the projection is rebuildable from `changed_since` reads, so deleting it loses nothing.** Document 03 §4 requires every sub-application to expose `GET /{collection}?changed_since=&cursor=` over every aggregate a consumer projects, and D5 makes that the rebuild path because the event bus is not one. The gateway's rebuild is a per-owner `changed_since` sweep over `/api/v1/{slug}/proposals` (§4.7). `test_d32_read_model_rebuild_with_bus_down` truncates the table, rebuilds with Redpanda stopped, and asserts the result is identical — the same property 11's DoD item 16 requires of every consumer, here doing double duty as the D32 guard and the D15 purge path.

**Property 4 — the gateway derives and publishes nothing.** The gateway computes no derived domain value from the projection beyond counts and orderings, performs no join between proposals and predictions, readiness, or configuration, and **publishes no events at all** (§9.2). This closes the mechanism by which an "all-domain consumer" becomes a cross-domain authority: under 03 §7.3 and principle 7, a derived value carries the union of its inputs' labels, and a component that derives across nine domains manufactures union-classified facts. The gateway does not derive across domains. It concatenates fragments for presentation and sets `X-Classification` to the union for that one response (§7.3), and persists neither.

### 2.4 The read model — exact schema

One table, in the gateway's own single logical database `fathom-gateway-pg` (03 §15 obligation 13, 09 §2.3). Alongside it: `inbox` (11 §3.3, verbatim), `idempotency_keys` (09 §5.3, verbatim), and `queue_rebuild_watermark` (§4.7). There is **no `outbox` table** — see §9.2.

```sql
-- platform/gateway/src/fathom_gateway/migrations/versions/…_gateway_proposal_queue.py
--
-- THE D32 READ MODEL.  Document 05 D32; resolution DECISION D32-R1 (build 30 §2.3).
--
-- WHAT THIS TABLE IS: a metadata-only, non-authoritative, rebuildable INDEX over
-- proposals owned by the nine sub-applications, at THIS DEPLOYMENT'S declared
-- classification level only (build 30 §7.1).
--
-- WHAT IT IS NOT, AND MUST NEVER BECOME:
--   * a copy of `Proposal.payload`            — stays with the owner (03 §7.2)
--   * a copy of `Proposal.evidence[]`         — stays with the owner (03 §7.2, D14)
--   * a copy of `Proposal.rationale`          — stays with the owner
--   * a copy of `adjudication_note`, `llm_version`
--   * a store of ANY free text authored outside the program (03 §9, D14)
--   * a system of record for anything (build 30 §2.3 property 2)
--   * a cross-classification aggregate (03 §7.3, §12, D13; build 30 §7)
--
-- Adding a column to this table fails `test_d32_read_model_column_allowlist`.
-- That is deliberate.  If the queue genuinely needs a new field, the allowlist in
-- src/fathom_gateway/readmodels/proposal_queue.py is amended IN THE SAME COMMIT,
-- with the D32 justification in the commit message (09 §7.5).
CREATE TABLE proposal_queue (
  -- ── identity and ownership ────────────────────────────────────────────────
  proposal_id                uuid        PRIMARY KEY,              -- 03 §7.2 [C30]; never `id`
  target_sub_app             text        NOT NULL,                 -- slug, 03 §3.1
  detail_fetch_path          text        NOT NULL,                 -- the owner's single-resource path (§4.6)

  -- ── routing and authority: the reason this row exists at all ──────────────
  kind                       text        NOT NULL,                 -- ProposalKind, 03 §7.2 [C39]
  authority_class            text        NOT NULL,                 -- 03 §7.2.1 vocabulary [D16]
  blast_radius               text        NOT NULL,                 -- item|asset|class|fleet [D16]
  requires_dual_control      boolean     NOT NULL,                 -- 03 §7.2 rule 4 [D16]

  -- ── scope, for filtering a queue to a hull, a system, or an item ──────────
  scope                      text        NOT NULL,                 -- 03 §5.4 `scope` [C11]
  asset_id                   uuid        NULL,
  system_id                  uuid        NULL,
  installed_item_id          uuid        NULL,                     -- the PHYSICAL item, 03 §3.3 [C10]
  niin                       text        NULL,
  class_id                   text        NULL,
  mission_id                 uuid        NULL,
  subject_provisional        boolean     NOT NULL DEFAULT false,   -- edge-minted id, 11 §8; resolved on read

  -- ── lifecycle, for warning and filtering.  NOT for deciding ──────────────
  status                     text        NOT NULL,                 -- ProposalStatus, 03 §7.2
  valid_until                timestamptz NOT NULL,                 -- 03 §7.2; re-validated BY THE OWNER [D16]
  baseline_id                uuid        NOT NULL,
  baseline_epoch             bigint      NOT NULL,                 -- staleness warning only [D16]
  claimed_by                 text        NULL,                     -- lease is the OWNER'S [D16]
  claimed_until              timestamptz NULL,
  adjudicated_by             text        NULL,
  second_adjudicator         text        NULL,                     -- dual control [D16]
  counter_signature_by       text        NULL,                     -- [AMENDMENT] a THIRD,
  counter_signature_at       timestamptz NULL,                     --   additional signatory (03 §7.2);
                                                                    --   see PROJECTED_COLUMNS below

  -- ── ranking and adjudicator warnings: scalars and booleans, never prose ──
  confidence                 double precision NOT NULL,            -- 03 §7.2
  evidence_count             integer     NOT NULL,                 -- a COUNT of evidence[], not evidence[]
  non_program_evidence_only  boolean     NOT NULL,                 -- Proposal.rests_solely_on_non_program_content
                                                                   --   (10 §4.7) — the D14 flag, as a BOOLEAN.
                                                                   --   The flag travels; the text does not.

  -- ── provenance pointers, not provenance content ──────────────────────────
  agent_id                   text        NOT NULL,
  agent_version              text        NOT NULL,
  trace_ref                  text        NOT NULL,                 -- 03 §8.5 Domino trace correlation

  -- ── classification (03 §7.3).  Always at this deployment's level (§7.1) ──
  classification             jsonb       NOT NULL,                 -- serialized ClassificationLabel

  -- ── projection bookkeeping ───────────────────────────────────────────────
  projection_seq             bigint      GENERATED ALWAYS AS IDENTITY,  -- gateway-local total order (§4.4)
  source_topic               text        NOT NULL,
  producer_slug              text        NOT NULL,
  producer_node_id           text        NOT NULL,                 -- 11 §4.2; "enterprise" | "edge:<asset_id>"
  last_monotonic_seq         bigint      NOT NULL,                 -- THE precedence key (03 §5.4, D29)
  announced_recorded_at      timestamptz NOT NULL,                 -- DISPLAY ONLY.  Never a sort or merge key
  announced_dispersion_ms    integer     NOT NULL,                 -- clock.sync_quality.dispersion_ms (03 §5.4)

  -- The owner of a proposal is the publisher of the event announcing it.
  -- 03 §6: "Every sub-application accepting agent proposals publishes to
  -- fathom.<slug>.proposal.v1"; 03 §7.2: target_sub_app is the executing
  -- sub-application.  They are the same service.  A violation is a producer
  -- publishing a fact about ANOTHER domain — 03 principle 3, [C32] — and is
  -- quarantined and alarmed, never projected (§4.3).
  CONSTRAINT proposal_queue_owner_is_producer
    CHECK (producer_slug = target_sub_app
           AND source_topic = 'fathom.' || producer_slug || '.proposal.v1'),

  -- 03 §7.2 rule 4, mirrored so a malformed upstream row cannot enter the queue
  -- looking adjudicable-by-one-signature. [AMENDMENT] Originally omitted
  -- purge/rewrap: 31-auth.md §6.4's generated authority_matrix.json sets
  -- dual_control:true on those kinds' item AND asset cells, not only
  -- class/fleet — the same gap 10-shared-packages.md's
  -- _dual_control_required_at_scope validator independently had, fixed there
  -- in the same pass.
  CONSTRAINT proposal_queue_dual_control_at_scope
    CHECK (requires_dual_control OR (blast_radius NOT IN ('class', 'fleet')
                                     AND kind NOT IN ('requisition', 'purge', 'rewrap'))),

  -- 03 §5.4: exactly one scope identifier, matching `scope`; scope='fleet'
  -- requires none — the one singleton scope [C11].
  CONSTRAINT proposal_queue_subject_matches_scope CHECK (
    (scope = 'asset'          AND asset_id          IS NOT NULL) OR
    (scope = 'system'         AND system_id         IS NOT NULL) OR
    (scope = 'installed_item' AND installed_item_id IS NOT NULL) OR
    (scope = 'niin'           AND niin              IS NOT NULL) OR
    (scope = 'class'          AND class_id          IS NOT NULL) OR
    (scope = 'mission'        AND mission_id        IS NOT NULL) OR
    (scope = 'fleet')
  )
);

CREATE UNIQUE INDEX proposal_queue_projection_seq ON proposal_queue (projection_seq);

-- The queue's default view: open proposals, most urgent first (§4.4).
CREATE INDEX proposal_queue_open
  ON proposal_queue (valid_until, projection_seq)
  WHERE status IN ('proposed', 'claimed');

-- The authority-routed view a UI filters on (03 §7.2.1).
CREATE INDEX proposal_queue_authority
  ON proposal_queue (authority_class, blast_radius, valid_until, projection_seq)
  WHERE status IN ('proposed', 'claimed');

CREATE INDEX proposal_queue_asset
  ON proposal_queue (asset_id, valid_until) WHERE asset_id IS NOT NULL;

CREATE INDEX proposal_queue_target ON proposal_queue (target_sub_app, status);

-- Admission-control depth (06 §6) and the dual-control worklist.
CREATE INDEX proposal_queue_dual_control
  ON proposal_queue (requires_dual_control, status) WHERE requires_dual_control;
```

**The allowlist, as code.** The schema comment is not the enforcement; this is:

```python
# platform/gateway/src/fathom_gateway/readmodels/proposal_queue.py

PROJECTED_COLUMNS: frozenset[str] = frozenset({
    "proposal_id", "target_sub_app", "detail_fetch_path",
    "kind", "authority_class", "blast_radius", "requires_dual_control",
    "scope", "asset_id", "system_id", "installed_item_id", "niin",
    "class_id", "mission_id", "subject_provisional",
    "status", "valid_until", "baseline_id", "baseline_epoch",
    "claimed_by", "claimed_until", "adjudicated_by", "second_adjudicator",
    "counter_signature_by", "counter_signature_at",   # [AMENDMENT] 03 §7.2
    "confidence", "evidence_count", "non_program_evidence_only",
    "agent_id", "agent_version", "trace_ref",
    "classification",
    "projection_seq", "source_topic", "producer_slug", "producer_node_id",
    "last_monotonic_seq", "announced_recorded_at", "announced_dispersion_ms",
})
"""The complete set of Proposal-derived fields the gateway is permitted to hold.

DECISION D32-R1 (build 30 §2.3).  `test_d32_read_model_column_allowlist` asserts
this equals the table's actual column set, in BOTH directions.
"""

FORBIDDEN_FIELDS: frozenset[str] = frozenset({
    "payload",            # 03 §7.2 — the domain object.  Stays with the owner.
    "evidence",           # 03 §7.2 — required, non-empty, and NOT the gateway's [D14]
    "excerpt",            # 03 §7.2 — untrusted corpus text [D14, 03 §9]
    "rationale",          # 03 §7.2 — agent-authored free text
    "adjudication_note",  # 03 §7.2 — human free text; audit holds it
    "llm_version",        # 03 §7.2 — belongs on the detail record and in audit
})
"""Fields whose presence anywhere in the gateway's ORM metadata is a D32
regression.  Asserted by `test_d32_forbidden_fields_absent_from_all_models`,
which walks `Base.metadata` rather than this one table — so the guard also
catches a future table that reintroduces them by another name's back door.
"""
```

**Fields deliberately absent, and why each absence is safe rather than an oversight:**

| Absent field | Why the queue does not need it | Where it is obtained |
|---|---|---|
| `payload` | The queue routes and filters; it does not render or validate the domain object. Validation is the owner's at creation and again at adjudication (03 §7.2) | Detail fetch, §4.6 |
| `evidence[]` | The one thing an adjudicator must see *before* opening is whether the proposal rests solely on non-program content (03 §7.2 rule 1, D14). That is one boolean, and the boolean is projected | Detail fetch, §4.6 |
| `rationale` | A row is structured facts. Prose is read when the proposal is opened — which 06 §6's 45 s per candidate assumes anyway | Detail fetch, §4.6 |
| `llm_version`, `adjudication_note` | Neither is a queue filter. Both are audit and detail concerns | Detail fetch; `audit` |
| A composed "priority score" | A derived cross-domain value, which property 4 forbids. Ranking is by declared, contractual fields only (§4.4) | Not computed anywhere |
| `p_failure` or any prediction field | Joining proposals to predictions is a cross-domain derivation. Forbidden by property 4, and it would attach PdM's `reference_class` semantics (03 §7.1, D7) to a queue that cannot honour them | The asset/item view, composed at request time (§3) |

### 2.5 Classification: segregation by deployment, not by filter

D32's second clause — *all-classification* — is not solved by making the read model small. A small projection of every level is still a projection of every level. It is solved by making the read model **partitioned**, and by making the partition a property of the deployment topology rather than of a runtime decision.

Document 03 §5.1 is the lever:

> *"Topics are segregated by classification level and compartment. A topic carries exactly one classification, declared in its registration; cross-level flow occurs only through an accredited guard."*

So `fathom.<slug>.proposal.v1` is not one topic per slug in production; it is one topic per (slug, level, compartment). The gateway's subscription is therefore never "the pattern"; it is **the pattern intersected with the topics at the deployment's own declared level**.

> **DECISION D32-R2.** One `gateway` deployment per classification level and compartment set. Each deployment carries a single declared level in configuration (`FATHOM_CLASSIFICATION__DEPLOYMENT_LEVEL`), owns its **own** database, its **own** consumer group, its **own** Kafka ACL grant, and its **own** ingress hostname. A deployment subscribes only to proposal topics at its declared level, and its read model therefore contains only proposals at that level — not by filtering them, but by never receiving them.

Five consequences, and each is the answer to a specific objection:

1. **The gateway cannot become system-high, because it is not subscribed.** Accreditation scope for a gateway deployment is its own level. There is no code path that reads above it, so there is nothing to review for one.
2. **No post-filtering, ever.** Document 03 §7.3 and DO-NOT 22 (09 §9.4) prohibit post-filtering because *"removing results afterward leaks the existence of records."* Under D32-R2 the gateway never holds a result it must remove. This is the same argument the vector store's query-time filtering rests on (04 §11 "Knowledge & Retrieval"), applied to a projection instead of an index.
3. **Topic-name enumeration is itself a leak, and this is why §4.1 rejects a broker-side regex subscription.** A librdkafka pattern subscription fetches cluster metadata and matches topic names locally, so a low-side consumer would learn the *names* of high-side topics. Topic names encode slug and, in production, level and compartment. Learning that `fathom.pdm.proposal.v1.s-compartment-x` exists is learning that a compartment exists — the same disclosure D13 describes one level up. The subscription must therefore be an explicit list, and the ACL must deny metadata describe on topics above the deployment's level.
4. **No cross-level aggregate is computed anywhere, including queue depth.** Document 03 §7.3: *"Aggregation is a classification event. A rollup whose value moves when a compartmented item degrades discloses that item's existence."* A "total proposals pending, all levels" figure is exactly such a rollup. It is not computed, not exposed, and not obtainable — because obtaining it would require a cross-level read, which only an accredited guard may perform and the gateway is not one. Admission-control depth (06 §6) is therefore **per level**, and §4.8 says so in the operation contract. The queue response carries no completeness claim across levels, which follows 06 §5's rule 3: *"A low-side rollup never presents itself as complete."*
5. **The demonstration is the degenerate case, by configuration.** Document 03 §12 and 06 §5 fix the demonstration at a single unclassified level. Under D32-R2 that is `n = 1`: one gateway deployment, `DEPLOYMENT_LEVEL=U`, one enumerated topic list of nine entries. **The multi-level shape is the same code with more deployments** — no branch, no feature flag, no filtering layer to add later. That is what "designed not to become system-high in production" means concretely, and §10's `test_d32_subscription_confined_to_declared_level` proves it by running the real consumer against a broker holding topics at two levels and asserting the above-level proposal is neither projected nor visible in any queue response.

An honest cost, recorded rather than buried: a user cleared for two levels sees two queues at two hostnames, and there is no single pane of glass across levels. That is not an implementation shortcut; it is the accreditable outcome. A single pane across levels *is* a cross-level flow and would require an accredited guard, which is a program and accreditation undertaking, not a gateway feature. Recorded as OQ-4.

### 2.6 The resolution, restated as five testable properties

D32 is closed when all five hold. Each maps to a named test in §10.

| # | Property | Test |
|---|---|---|
| 1 | The projection's column set equals the declared allowlist, and no forbidden field appears anywhere in the gateway's ORM metadata | `test_d32_read_model_column_allowlist`, `test_d32_forbidden_fields_absent_from_all_models` |
| 2 | A proposal's `payload` and `evidence[].excerpt` do not appear anywhere in the gateway's database after real end-to-end projection | `test_d32_projection_discards_payload_from_the_wire` |
| 3 | The subscription is an explicit list confined to the deployment's declared level; nothing above it is received, projected, or served; no `^`-prefixed pattern is passed to the broker client | `test_d32_subscription_confined_to_declared_level`, `test_d32_no_broker_pattern_subscription` |
| 4 | The projection is rebuildable from `changed_since` reads with the event bus down, and the rebuild is identical to the projected state | `test_d32_read_model_rebuild_with_bus_down` |
| 5 | The gateway publishes no events, owns no outbox, and takes no decision from the projection — a poisoned row cannot cause a wrong adjudication | `test_d32_gateway_publishes_nothing`, `test_d32_stale_projection_cannot_cause_a_wrong_adjudication` |

### 2.7 What this document decides that the architecture did not

Following 09 §1.3's convention, marked so a reader can tell a derivation from a decision.

| ID | Decision | Status | If it is overturned |
|---|---|---|---|
| **D32-R1** | Metadata-only projection; payload fetched on demand from the owner | **[ESTABLISHED HERE]** — 04 §11 says "consume the topic pattern" and says nothing about what is projected. 03 §6 says the queue is built from the pattern. Neither bounds the projection | The alternative is option (b) (§2.2), which changes §4 entirely and requires nine sub-applications to expose a queue-shaped `/proposals` collection. It does not change §3, §5, §6, or §7 |
| **D32-R2** | One gateway deployment per classification level; segregation by topology, not by filter | **[ESTABLISHED HERE]** — 03 §5.1 requires topic segregation and 03 §12 requires a stated single-level posture, but no document says how a consumer of a *pattern* across levels is structured | The alternative is one deployment filtering by label, which is post-filtering (D13, DO-NOT 22) and makes the gateway the classification enforcement point. Rejected |
| **G-1** | Explicit enumerated topic list; the pattern is used only as a CI-verified assertion | **[ESTABLISHED HERE]**, and it is what reconciles 03 §6's pattern with C38's prohibition on wildcard subscriptions. §4.2 | Reverting to a broker-side regex reintroduces C38 and the metadata-enumeration leak of §2.5 item 3 |
| **G-2** | Two Deployments from one chart — API (HPA on request rate) and projector (KEDA on consumer lag) | **[ESTABLISHED HERE]** — 09 §2.4 assigns the gateway HPA-on-request-rate and event workers KEDA-on-lag; the gateway is both, and 09 §4.4.1 permits one `autoscaling.mode` per chart. §11.2 | A single Deployment means either the wrong scaling signal or one consumer instance per HTTP replica, rebalancing the group on request load |
| **G-3** | Pass-through routes are generated at startup from the nine committed `openapi.json` documents, delivered as a ConfigMap | **[ESTABLISHED HERE]** — no document specifies how the ingress surface is constructed, and 09 §5.3's idempotency middleware requires a statically-known `x-side-effects` per route. §8.2 | A dynamic catch-all proxy makes the ingress surface unknowable at review time and breaks the shared middleware |
| **G-4** | RFC 8693 token exchange with `act` and `may_act`; signed gateway assertion recorded as the fallback | **[ESTABLISHED HERE]** — 04 §11 assigns "token exchange for delegated authority" to the gateway and names no mechanism. §5.3 | The fallback makes the gateway a token issuer, i.e. an authority root, which §5.7 argues against |
| **G-5** | In-process token bucket sized against `minReplicas`; no shared limiter store | **[ESTABLISHED HERE]** — 03 §4 requires the bucket and names no storage; there is no Redis in the 01 §11 inventory. §6.3 | A shared limiter store is a new infrastructure component and a change to 09 §2 |

**A correction to the framing of this work, recorded per 09 §11's convention.** The task framing asserted that option (b) *"would violate [03's no-synchronous-cross-sub-application-calls principle] on every queue-view request."* On the text of 03 principle 2 it would not: the principle's second sentence explicitly permits synchronous reads for user-facing composition performed by the gateway. Option (b) is rejected on the four grounds in §2.2, not on principle 2. The distinction matters because a reviewer citing principle 2 against option (b) would be citing it incorrectly, and the real objections — pagination non-composability, multiplied availability, undeclared state, and the inversion of 03 §6's decoupling property — are the ones that survive scrutiny.

---

## 3. View composition — fan-out and gather

### 3.1 The shape, and the one thing it must never be

Document 03 principle 2's closing sentence names the stake: composition in the gateway *"is the principal defense against a distributed system that fails like a monolith."* The defense only works if the fan-out is **flat**.

```
                     PERMITTED — flat fan-out, gathered in the gateway
  UI ──▶ gateway ──┬──▶ registry      GET /assets/{id}
                   ├──▶ registry      GET /assets/{id}/installed-items
                   ├──▶ pdm           GET /predictions?asset_id=…
                   ├──▶ fleet-status  GET /readiness?asset_id=…
                   └──▶ maintenance   GET /work-orders?asset_id=…
                        (all five in flight simultaneously; joined in the gateway)

                     FORBIDDEN — a chain, regardless of who starts it
  UI ──▶ gateway ──▶ pdm ──▶ registry ──▶ …
```

The forbidden shape is forbidden by 03 principle 2 and made **structurally impossible** by 09 §4.4.2's NetworkPolicy: the sanctioned edge table lists `sub-application → sub-application` as **NO**, with the annotation *"this is the whole point of the policy."* The gateway may therefore *rely* on the property rather than merely hope for it: every fragment it requests is served by the owner from the owner's own database, so a fragment's latency is one service's latency and the composed view's latency is the maximum of the fragments, not their sum.

Two rules follow, and they are the rules that keep it that way:

- **Rule C1 — a join across two sub-applications happens in the gateway, never upstream.** If a view needs Registry configuration joined to PdM predictions, the gateway requests both and joins. A view that would require an upstream to fetch a peer's data is a view that must be redesigned, and the fragment registry (§3.2) is where that redesign is forced, because a fragment declares exactly one upstream.
- **Rule C2 — a fragment's request never depends on another fragment's response.** All fragments for a view are dispatched in one batch. Where a view genuinely needs an identifier from a first call to make a second — the item list for an asset, for example — that is **two declared phases**, each internally flat, and the phase count is a declared property of the view that CI bounds at two. A third phase is a rejected design, not a configuration value: three serial phases inside a 1.5 s budget (06 §7) leaves ~500 ms per phase, and the tail behaviour of three chained maxima is not something a p95 target survives.

### 3.2 The fragment registry

Views are declared, not assembled ad hoc, so the fan-out shape of the whole ingress is reviewable in one file.

```python
# platform/gateway/src/fathom_gateway/composition/registry.py
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fathom_schemas.slugs import AnySlug


@dataclass(frozen=True, slots=True)
class Fragment:
    name: str                      # stable, snake_case; appears in the response envelope and metrics
    upstream: AnySlug              # EXACTLY ONE.  This is Rule C1, expressed as a type.
    operation_id: str              # the upstream operationId (09 §7.3); resolved against its committed spec
    required: bool                 # False => a failure degrades the view; True => a failure fails it
    budget_ms: int                 # per-fragment monotonic deadline (§3.3)
    phase: int                     # 0 or 1 only.  Rule C2.
    fetch: Callable[["FragmentContext"], Awaitable["FragmentResult"]]


@dataclass(frozen=True, slots=True)
class ViewSpec:
    name: str                      # "asset_detail", "fleet_overview", "explanation_decomposition"
    route: str                     # "/api/v1/gateway/views/asset/{asset_id}"
    budget_ms: int                 # from 06 §7.  NOT invented here.
    fragments: tuple[Fragment, ...]
```

The registry, with every budget cited:

| View | Route | Budget | Basis | Fragments (upstream · required · phase) |
|---|---|---|---|---|
| `fleet_overview` | `/views/fleet` | 1500 ms | 06 §7 *"p95 < 1.5 s for fleet and asset views"* | `readiness_rollup` (fleet-status · **required** · 0); `asset_status` (registry · **required** · 0); `open_casrep_risk` (fleet-status · optional · 0); `availability_windows` (maintenance · optional · 0); `proposal_counts` (**local read model** · optional · 0) |
| `asset_detail` | `/views/asset/{asset_id}` | 1500 ms | 06 §7 | `asset` (registry · **required** · 0); `configuration_baseline` (registry · **required** · 0); `readiness` (fleet-status · optional · 0); `predictions` (pdm · optional · 0); `open_work` (maintenance · optional · 0); `parts_position` (supply · optional · 0); `open_proposals` (**local read model** · optional · 0); `installed_items` (registry · optional · **1**) |
| `installed_item_detail` | `/views/installed-item/{installed_item_id}` | 1500 ms | 06 §7 | `installed_item` (registry · **required** · 0); `prediction` (pdm · optional · 0); `health_indicators` (telemetry · optional · 0); `usage_counters` (telemetry · optional · 0); `maintenance_history` (maintenance · optional · 0); `failure_modes` (failure-intel · optional · 0) |
| `explanation_decomposition` | `/views/explanation/{prediction_id}` | 4000 ms | 06 §7 *"< 4 s for explanation decomposition"* | `prediction` (pdm · **required** · 0); `contributing_factors` (pdm · **required** · 0); `feature_observations` (telemetry · optional · **1**); `causal_findings` (failure-intel · optional · 1); `procedure_references` (knowledge-retrieval · optional · 1) |
| `redesign_case_detail` **[AMENDMENT]** | `/views/redesign-case/{case_id}` | 4000 ms, **[NOT SOURCED — see note]** | No figure exists in 06 §7 for this view; `explanation_decomposition`'s budget is borrowed by analogy (same order of composition: a multi-hop dependency/causal chain, not a single-slug lookup) | `redesign_case` (design-advisory · **required** · 0); `dossier` (design-advisory · **required** · 0); `impact_snapshot` (design-advisory · optional · 0); `cost_estimate` (design-advisory · optional · 0); `gate_decision` (design-advisory · optional · 0); `causal_findings` (failure-intel · optional · **1**) |

**`redesign_case_detail` closes `42-redesign-case-builder.md` §18 item 13**: *"An adjudicator opening a `redesign_case` from the queue has no composed drill-down, though the case's value is entirely in its evidence chain."* `28-design-advisory.md` §2's claim that this composition *"is composed by the gateway"* had no implementation until this row. The budget is flagged rather than asserted as settled — `42`'s own §18 item 20 separately records that 06 §6 has no adjudication-effort figure for a `redesign_case` at all, so this view's timing budget shares that same open dependency rather than resolving it. **Phase 1's `causal_findings` fragment is the drill-down into Failure Intelligence** the same document's §18 item 13 describes as absent from every existing `ViewSpec` fragment list.

**The `gate_decision` fragment was added by a later amendment** `[closes 52-practitioner-apps.md §13 correction 7, blocking]` — the wireframe's cost box draws the two-stage gate, and `28-design-advisory.md` §5.5's `failed_conditions`/`remedy` are the actionable part of a gate failure; without this fragment, rendering the gate region required a second client call this view exists to avoid.

**Every fragment's `operation_id`, enumerated — `[amendment, closes 51-operator-console.md §22 row 21, blocking]`.** The field has existed in `Fragment`'s definition (§3.2) since this document's original authoring — *"the upstream `operationId` (09 §7.3); resolved against its committed spec"* — and no fragment's value was ever given, so no consumer of this table could derive a response shape from this document alone. Cross-checked against each cited sub-application's own API-surface table:

| View | Fragment | `operation_id` |
|---|---|---|
| `fleet_overview` | `readiness_rollup` | `GET /readiness?scope=fleet` (`27-fleet-status.md` §10.1) |
| | `asset_status` | `GET /assets?...` (`20-registry.md` §9.1, list form) |
| | `open_casrep_risk` | `GET /risk-flags?severity=&horizon_days=` (`27-fleet-status.md`) |
| | `availability_windows` | `GET /availabilities?asset_id=` (`24-scheduling.md` §9.1) |
| | `proposal_counts` | none — the local `proposal_queue` read model (§9.3), not an upstream call |
| `asset_detail` | `asset` | `GET /assets/{asset_id}` (`20-registry.md` §9.1) |
| | `configuration_baseline` | `GET /assets/{asset_id}/configuration` (`20-registry.md` §9.1) |
| | `readiness` | `GET /readiness?scope=asset&asset_id=` (`27-fleet-status.md` §10.1) |
| | `predictions` | `GET /predictions?asset_id=` (`22-pdm.md` §10) |
| | `open_work` | `GET /work-orders?asset_id=&status=open` (`24-scheduling.md` §9.1) |
| | `parts_position` | `GET /availability?asset_id=` (`26-supply.md` §7) |
| | `open_proposals` | none — the local read model, same as `proposal_counts` above |
| | `installed_items` | `GET /assets/{asset_id}/installed-items` (`20-registry.md` §9.1) |
| `installed_item_detail` | `installed_item` | `GET /installed-items/{installed_item_id}` (`20-registry.md` §9.1) |
| | `prediction` | `GET /predictions?installed_item_id=` (`22-pdm.md` §10) |
| | `health_indicators` | `GET /health-indicators?installed_item_id=&from=&to=&as_of=&as_known_at=` (`21-telemetry.md` §9.1) |
| | `usage_counters` | `GET /usage-counters?installed_item_id=&as_of=` (`21-telemetry.md` §9.1) |
| | `maintenance_history` | `GET /maintenance-history?installed_item_id=&niin=` (`24-scheduling.md` §9.1, amended) |
| | `failure_modes` | `GET /failure-modes?equipment_class=&taxonomy_version=` (`25-failure-intelligence.md` §8.1) — resolved from the installed item's `equipment_family`, itself read off its `PartRef`. **[VERIFY]**: this fragment may be better served by `GET /attributions?installed_item_id=` (attributed findings, item-scoped) than by the class-level annotation surface; the two answer different questions and the wireframe's box (04 §3's per-item view) reads as the latter |
| `explanation_decomposition` | `prediction` | `GET /predictions/{id}` (`22-pdm.md` §10) |
| | `contributing_factors` | `GET /predictions/{id}/provenance` (`22-pdm.md` §10) |
| | `feature_observations` | `GET /health-indicators?installed_item_id=&from=&to=` (`21-telemetry.md` §9.1), windowed to the prediction's observation window |
| | `causal_findings` | `GET /attributions?installed_item_id=&mode_lineage_id=` (`25-failure-intelligence.md` §8.1) |
| | `procedure_references` | `POST /retrievals` (`35-knowledge-retrieval.md` §8, `mode=asset_scoped`) |
| `redesign_case_detail` | `redesign_case` | `GET /redesign-cases/{id}` (`28-design-advisory.md` §9.1) |
| | `dossier` | `GET /dossiers/{id}` (`28-design-advisory.md` §9.1) |
| | `impact_snapshot` | `GET /impact-snapshots/{id}` (`28-design-advisory.md` §9.1) |
| | `cost_estimate` | `GET /cost-estimates/{id}` (`28-design-advisory.md` §9.1, added by amendment alongside this row — no such operation existed until this reconciliation pass) |
| | `gate_decision` | `GET /redesign-candidates/{id}/gate-decisions` (`28-design-advisory.md` §9.1, full append-only history — the fragment takes the most recent row) |
| | `causal_findings` | `GET /attributions?niin=` (`25-failure-intelligence.md` §8.1) |

One row above is itself a new, smaller correction rather than a clean answer — `failure_modes`'s `[VERIFY]` — recorded here rather than papered over with a confident-sounding wrong answer. `cost_estimate`'s missing read operation was found and closed in the same pass (`28-design-advisory.md` §9.1, `GET /cost-estimates/{id}`).

Four properties of the table are load-bearing:

- **`proposal_counts` and `open_proposals` read the local `proposal_queue`**, not an upstream. This is the *only* place a composed view reads gateway-held state, and it is why the read model earns its existence: an asset view showing "3 proposals awaiting your adjudication for this hull" under option (b) would require a nine-way fan-out inside a 1.5 s asset-view budget, for a badge.
- **`required` is sparse and deliberate.** A view fails only when the fragment that identifies its subject is unobtainable. Everything else degrades. An asset view without a readiness score is useful; an asset view that cannot confirm the asset exists is a lie.
- **Every `phase: 1` fragment is optional.** A second phase is already the slow path; making a required fragment depend on a prior response would put a serial two-hop chain on the critical path of a required field.
- **`explanation_decomposition` is the only view over 1.5 s, and 06 §7 is the only reason.** No budget in this table is chosen; each is transcribed.

### 3.3 Deadlines and timeouts — monotonic, per D29

Every deadline, timeout, and backoff in the gateway is measured on `time.monotonic()`. This is not stylistic: 09 §9.2 item 7 and 11 §12 item 3 forbid wall-clock arithmetic in any deadline, and 11 §11.5's static gate 5 fails CI on `time.time()` or `datetime.now()` in a timeout. The mandated STIG behaviour (Ubuntu 22.04 V-260520, `makestep 1 -1`) means a backward step of arbitrary size can land at any moment; a wall-clock request deadline would then either fire immediately on every in-flight request or never fire at all.

```python
# platform/gateway/src/fathom_gateway/composition/deadline.py
import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MonotonicDeadline:
    """The ONLY deadline type in this service.  [D29 · 03 §5.4 · 09 §9.2.7 · 11 §12.3]

    There is no wall-clock deadline anywhere in the gateway.  The single sanctioned
    wall-clock read in the whole service is JWT `exp`/`nbf` validation (§5.2), which
    RFC 7519 defines in wall-clock terms and which is therefore unavoidable — and it
    is deliberately NOT reachable from this module.
    """

    at: float                                   # a time.monotonic() value

    @classmethod
    def after_ms(cls, ms: int) -> "MonotonicDeadline":
        return cls(at=time.monotonic() + ms / 1000.0)

    @property
    def remaining_ms(self) -> float:
        return max(0.0, (self.at - time.monotonic()) * 1000.0)

    def clamp_ms(self, budget_ms: int) -> float:
        """A fragment gets the lesser of its own budget and what the view has left.
        This is what stops phase 1 from spending a budget phase 0 already consumed."""
        return min(float(budget_ms), self.remaining_ms)
```

Timeout layering, from outermost in. Each layer is strictly inside the one above, so no layer can be starved by a layer below it:

| Layer | Value | Rule |
|---|---|---|
| View deadline | `ViewSpec.budget_ms` (06 §7) | Set once per request from the matched route |
| Fragment deadline | `deadline.clamp_ms(Fragment.budget_ms)` | Never exceeds the view's remaining time |
| httpx read timeout | fragment deadline | Set per request on the shared client factory (09 §2.2) |
| httpx connect timeout | 250 ms | **[ESTABLISHED HERE]** — an in-cluster connect that has not completed in 250 ms is a pod that is gone, not a pod that is slow; and the value must be small enough that the one sanctioned retry fits |
| Retry | **connect failures only, once** | A read timeout is **never** retried: retrying a timeout doubles load on a dependency that is already failing, which is the monolith-failure mode principle 2 names. A connect failure is retried once, inside the fragment deadline, because it is the ordinary signal of a rolling deployment |

### 3.4 Gathering, and honest partial failure

```python
# platform/gateway/src/fathom_gateway/composition/gather.py
import asyncio
from enum import StrEnum


class FragmentOutcome(StrEnum):
    OK = "ok"                        # data obtained
    EMPTY = "empty"                  # upstream answered authoritatively: there is none
    TIMEOUT = "timeout"              # deadline expired
    UNAVAILABLE = "unavailable"      # connect failure, 5xx, or circuit open
    FORBIDDEN = "forbidden"          # upstream 403 — the CALLER may not see this fragment
    CLASSIFICATION_FAULT = "classification_fault"   # over-level fragment; §7.2. Fails closed.


async def gather_phase(
    fragments: tuple[Fragment, ...], ctx: FragmentContext, deadline: MonotonicDeadline
) -> dict[str, FragmentResult]:
    """All fragments of a phase are dispatched simultaneously and none can cancel
    another.  `asyncio.TaskGroup` is deliberately NOT used: it cancels siblings on
    the first exception, which would turn one slow upstream into a blank view — the
    opposite of the required behaviour.
    """
    results = await asyncio.gather(
        *(_run_one(f, ctx, deadline) for f in fragments),
        return_exceptions=False,      # _run_one never raises; see below
    )
    return {r.name: r for r in results}


async def _run_one(f, ctx, deadline) -> FragmentResult:
    """Converts every failure into a typed FragmentResult.  This function does not
    raise, which is what makes the gather total."""
    ...
```

**The rendering rule, which is the whole point of the typed outcome:**

> **A fragment failure is rendered, never dropped.** `EMPTY` and `UNAVAILABLE` are different facts and are presented as different facts. A view that silently omits a failed prediction fragment tells the operator there is no predicted risk, which is the single most damaging thing this system can say.

Response envelope on every composed view:

```json
{
  "view": "asset_detail",
  "subject": { "asset_id": "…" },
  "as_of": "2026-08-04T13:02:11.480000+00:00",
  "fragments": {
    "asset":                 { "outcome": "ok" },
    "configuration_baseline":{ "outcome": "ok" },
    "readiness":             { "outcome": "ok" },
    "predictions":           { "outcome": "unavailable",
                               "upstream": "pdm",
                               "detail": "upstream unavailable",
                               "retryable": true },
    "open_work":             { "outcome": "empty" },
    "parts_position":        { "outcome": "timeout", "upstream": "supply", "retryable": true },
    "open_proposals":        { "outcome": "ok" },
    "installed_items":       { "outcome": "ok" }
  },
  "degraded": true,
  "data": { "…": "one key per fragment whose outcome is ok" }
}
```

| Situation | Gateway response |
|---|---|
| All fragments `ok` or `empty` | `200`, `degraded: false` |
| Any optional fragment not `ok`/`empty` | `200`, `degraded: true`, per-fragment outcome stated. The UI must render the gap; it must not render zero |
| Any **required** fragment not `ok`/`empty` | `503` RFC 9457, `type: urn:fathom:problem:gateway:required-fragment-unavailable`, with the failed fragment names and their upstreams in an extension member. **No partial body** — a view whose subject could not be confirmed is not a degraded view |
| Any fragment `forbidden` | `200`, `degraded: true`, outcome `forbidden`. The gateway does not convert an upstream `403` into a `403` for the whole view: the caller may legitimately see four of five fragments, and the upstream is the authority on each (03 obligation 7) |
| Any fragment `classification_fault` | `502` RFC 9457, `urn:fathom:problem:gateway:classification-fault`. Fails closed; §7.2 |

**Circuit breaker and bulkhead, per upstream.** A slow upstream must not exhaust the gateway's connection pool and take down every view — the exact "fails like a monolith" outcome principle 2 exists to prevent. Two independent mechanisms, both per `(upstream, operation_id)`:

- **Bulkhead** — a bounded `asyncio.Semaphore` per upstream. Saturation returns `UNAVAILABLE` immediately rather than queueing, because a queued request that will miss the view deadline is worse than a rendered gap.
- **Circuit breaker** — closed → open after a declared consecutive-failure count within a monotonic window; open returns `UNAVAILABLE` without a call; half-open admits one probe. Breaker state per upstream is exported as `fathom_gateway_circuit_state{upstream}`, so a partially-degraded ingress is visible rather than inferred from latency.

Both are sized from `values.yaml` (§11.1). Neither threshold is invented here: they are declared per environment, and the demonstration values are set alongside the rate limits from each sub-application's own chart (§6.2), which is the only place in the system that owns a per-sub-application capacity figure.

### 3.5 What the gateway may cache, and what it may never cache

A response cache would be a read model by the back door, and would reintroduce D32 at a larger scale than the queue ever did.

| Cacheable | TTL | Why it is not domain state |
|---|---|---|
| JWKS from `auth` | bounded, plus forced refresh on an unknown `kid` | Key material, not data. §5.1 |
| Reference Data enumerations, code sets, `equipment_family` | per the `taxonomy_version` published by `reference-data` (12 §6.2) | 09 §4.4.2: reference-data *"must be cached; it is not a compute-path dependency."* Cached **by version**, so a cache entry is immutable and invalidation is a version change, not an expiry |
| The nine committed `openapi.json` documents | process lifetime; delivered by ConfigMap (§8.2) | Contract metadata, loaded at startup |

| Never cacheable | Why |
|---|---|
| Any fragment response from the nine sub-applications | It is domain state owned elsewhere. Caching it makes the gateway a read model of nine domains — D32, at full payload size, with no schema and no purge path |
| A composed view | Same, one layer up, plus it would freeze a classification union (§7.3) |
| A proposal detail response | It carries `payload`, `evidence[]`, and `rationale`. Caching it is a direct violation of D32-R1 (§2.3) |
| An exchanged delegation token | §5.3. Bearer credentials for a specific `(user, agent, audience)` at a specific instant |

Consequence, stated so nobody reintroduces a cache to fix it: the gateway holds no domain data across requests, so the p95 budget in 06 §7 must be met by the fan-out itself, at a fleet of 12 assets and ~8,400 installed items (06 §7). If it is not met, the answer is upstream indexing or a narrower fragment, **not** a gateway cache. Recorded as OQ-3 together with the load-testing gap 09 OQ-8 already carries.

### 3.6 Why upstream fan-out is not this document's problem

Rule C1 assumes each fragment is served from the owner's own database. That assumption is not this document's to enforce, and it is already enforced twice elsewhere: by 03 principle 2 (contract), and by 09 §4.4.2's NetworkPolicy egress set, where the nine sub-applications' permitted in-namespace egress is exactly `[auth, audit, reference-data]` and `toNamespaces` is empty. A sub-application physically cannot call a peer.

The gateway therefore treats an anomalous fragment latency as an upstream defect worth surfacing rather than a condition to accommodate: `fathom_gateway_fragment_duration_seconds{view,fragment,upstream}` is a per-fragment histogram, and a fragment whose latency profile implies its own fan-out is a finding against that sub-application's build document, not a reason to raise a budget here.

---

## 4. The unified proposal adjudication queue

### 4.1 The subscription — exactly how

Nine topics, named explicitly, at the deployment's declared classification level (§2.5, D32-R2).

```python
# platform/gateway/src/fathom_gateway/events/catalog.py
"""The gateway's event catalog.  09 §8.2 requires PUBLISHES/CONSUMES here to equal
helm/values.yaml `events.publishes`/`events.consumes` to document 03 §6's catalog
rows for this slug, reconciled by tools/check_service_events.py in CI job 6.
"""
from fathom_schemas.slugs import SubAppSlug            # the NINE domain slugs, 03 §3.1 (10 §4.2)
from fathom_schemas.topics import proposal_topic       # 10 §4.5

PUBLISHES: frozenset[str] = frozenset()
"""EMPTY, and correct.  The gateway owns no aggregate and effects no state change
through its own contract, so 03 §15 obligation 2 ("emit an event for every state
change reachable through its contract") is satisfied vacuously.  See build 30 §9.2.
"""

AUDIT_PROPOSAL_TOPIC: str = "fathom.audit.proposal.v1"
"""[AMENDMENT] `audit` is a PLATFORM slug, not a member of `SubAppSlug` (the nine
DOMAIN slugs) — but 03 §6 line "Audit's purge/rewrap-kind proposals follow the
generic [proposal] convention... exactly as any other proposal-accepting
sub-application's topic does" makes `audit` a tenth, explicitly-named producer
under that same convention, and 03 §6's convention table names `gateway` as a
consumer regardless of which slug publishes.  `CONSUMES` below previously
enumerated only the nine `SubAppSlug` topics, silently excluding this one — the
consequence was that `purge`/`rewrap` proposals, the only kind whose
`authority_class` is `security_officer`, could never reach the queue at all
(§9.1's Security Officer card and 51-operator-console.md's Sheet 11 are built
against a topic the gateway never subscribed to). Named as a constant, not
folded into a loop, because it is a single fixed exception, not a pattern."""

CONSUMES: frozenset[str] = frozenset(
    proposal_topic(slug) for slug in SubAppSlug
) | {AUDIT_PROPOSAL_TOPIC}
"""The nine domain proposal topics plus `audit`'s — TEN, ENUMERATED, not a
pattern.  See build 30 §4.2 for why this is an explicit list and not the
librdkafka regex form, and §7.1 for how the enumeration is confined to this
deployment's classification level.
"""

CONSUMED_EVENT_TYPES: frozenset[str] = frozenset({
    f"fathom.{slug}.proposal.{verb}"
    for slug in SubAppSlug
    for verb in ("created", "adjudicated", "expired")
} | {
    f"fathom.audit.proposal.{verb}"
    for verb in ("created", "adjudicated", "expired")
})
"""03 §6 "Proposals — a convention" lists three events on the proposal aggregate,
for every producer under the convention — the nine sub-applications AND `audit`
(see `AUDIT_PROPOSAL_TOPIC` above). NOTE the catalog defect at §14 item 1: 03 §6
names `gateway` as a consumer of `proposal.created` and `proposal.expired` but
NOT of `proposal.adjudicated` — which would leave every approved proposal in the
queue as pending forever.  The gateway consumes all three; document 03 §6's
consumer column needs the correction.
"""
```

Consumer configuration, `confluent-kafka-python` against Redpanda (09 §2.2):

```python
# platform/gateway/src/fathom_gateway/events/consumer.py
CONSUMER_CONFIG = {
    "bootstrap.servers":            settings.events.brokers,
    "group.id":                     settings.events.consumer_group,   # fathom-gateway-v1 (09 §7.1)
    "enable.auto.commit":           False,   # 11 §3.4: the offset commits AFTER the DB transaction
    "auto.offset.reset":            "earliest",
    "isolation.level":              "read_committed",
    "partition.assignment.strategy": "cooperative-sticky",
    "enable.partition.eof":         False,
    # Deliberately absent: `topic.metadata.refresh.sparse` tuning for pattern
    # matching, and any `allow.auto.create.topics`.  The gateway neither discovers
    # topics nor creates them.
}

consumer.subscribe(sorted(CONSUMES))     # an explicit LIST of ten topic names
```

### 4.2 The pattern, C38, and why the list is explicit

Two constraints appear to conflict, and reconciling them is a required piece of this document.

- **03 §6 and 04 §11** say the queue is built *"by consuming the `fathom.*.proposal.v1` topic pattern"*, and `packages/canonical-schemas` ships `PROPOSAL_TOPIC_PATTERN` for exactly that (10 §4.5).
- **C38** is a FIX finding against wildcard subscriptions — *"which cannot be conformance-tested and auto-subscribe to future events"* — and 09 §8.2 makes it a Definition-of-Done item: *"No wildcard subscriptions. Every consumed event type is named explicitly."* 09 §9.2 item 14 repeats it as a DO-NOT.

> **DECISION G-1.** The gateway subscribes to an **explicitly enumerated list of ten topic names**. `PROPOSAL_TOPIC_PATTERN` is used in **exactly one place**: a CI assertion that the enumerated list equals the pattern's expansion over the canonical slug table, plus the one named platform-service exception. The broker client is never handed a `^`-prefixed pattern.

This satisfies both, and the reason it is not a fudge is that the "pattern" here is closed on every axis but one:

| Axis | Varies? | Consequence |
|---|---|---|
| Aggregate token | No — fixed at `proposal` | Not a wildcard over aggregates |
| Major version | No — fixed at `v1` | A `v2` proposal topic is a deliberate, reviewed subscription change, not an auto-subscription |
| Slug | Yes — but over a **closed, enumerated table** of nine (03 §3.1) **plus one named platform-service exception, `audit`** (`AUDIT_PROPOSAL_TOPIC` above — 03 §6 makes `audit` a tenth producer under the same proposal convention, for `purge`/`rewrap`) | Expansion is a ten-element list, knowable at build time |

C38's two named defects therefore cannot occur. *"Cannot be conformance-tested"*: the gateway contributes a consumer-driven conformance test to each of the ten producers' suites (§10.4), which is possible only because all ten are named. *"Auto-subscribe to future events"*: an eleventh producer requires either a row in 03 §3.1 (changing `SubAppSlug`, `CONSUMES`, and `helm/values.yaml` together) or an explicit second named exception alongside `AUDIT_PROPOSAL_TOPIC` — either way CI job 6 fails until all four agree.

The CI assertion:

```python
# platform/gateway/tests/contract/test_subscription_matches_pattern.py
import re

from fathom_schemas.slugs import SubAppSlug
from fathom_schemas.topics import PROPOSAL_TOPIC_PATTERN

from fathom_gateway.events.catalog import AUDIT_PROPOSAL_TOPIC, CONSUMES


def test_g1_enumerated_list_equals_pattern_expansion() -> None:
    """DECISION G-1 (build 30 §4.2).  Reconciles 03 §6's "topic pattern" with
    C38's prohibition on wildcard subscriptions: the pattern is the SPECIFICATION
    and the list is the IMPLEMENTATION, and CI holds them equal.

    [AMENDMENT] Previously asserted CONSUMES == the nine-slug expansion exactly,
    len == 9 — silently correct-looking while excluding fathom.audit.proposal.v1,
    the only topic carrying purge/rewrap proposals. audit is a PlatformServiceSlug,
    not a SubAppSlug, so it is added as a named exception rather than folded into
    the slug expansion, which stays a pattern match over a closed enumeration."""
    expansion = {f"fathom.{slug}.proposal.v1" for slug in SubAppSlug} | {AUDIT_PROPOSAL_TOPIC}
    assert CONSUMES == expansion
    assert len(CONSUMES) == 10

    pattern = re.compile(PROPOSAL_TOPIC_PATTERN)
    for topic in CONSUMES:
        assert pattern.match(topic), topic


def test_d32_no_broker_pattern_subscription(subscribed_topics: list[str]) -> None:
    """§2.5 item 3: a librdkafka regex subscription fetches cluster metadata and
    matches topic names locally, so a low-side consumer would learn the NAMES of
    high-side topics — and in production a topic name encodes level and
    compartment.  Learning that a compartmented topic exists is the D13
    existence disclosure, one level up.  No argument may begin with '^'."""
    assert subscribed_topics, "the projector must subscribe to something"
    assert not any(t.startswith("^") for t in subscribed_topics)
```

A third reason for the explicit list, which is operational rather than architectural: a librdkafka pattern subscription requires cluster-wide metadata describe rights. Under D32-R2 the gateway's Kafka ACL grant is exactly ten topics at one level, and `describe` is denied above it — so a pattern subscription would not merely leak, it would fail. The ACL is the enforcement; the code matches it.

### 4.3 The projector

The projector is the `gateway-projector` Deployment (§11.2). It uses `packages/py-sync`'s inbox verbatim — the gateway is a consumer, so 03 §15 obligation 12 and 11 §1.1 bind it in full.

```python
# platform/gateway/src/fathom_gateway/events/consumers.py

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
# WHY IT IS SEVERE HERE: a permanently-suppressed `proposal.created` is a
# proposal that exists, is adjudicable, expires unadjudicated, and NEVER APPEARS
# IN THE QUEUE. Nothing alarms, because the queue's depth metric counts what the
# queue holds. D16's defect is two people adjudicating one proposal; this is
# nobody adjudicating it, and it is quieter.
#
# THE ONLY LEGAL SUPPRESSION PREDICATE IS:
#     event_id present AND processed_at IS NOT NULL
# A row with processed_at NULL means "seen, not applied" and MUST NOT suppress.
# ---------------------------------------------------------------------------

EVENT_HANDLERS: dict[str, Handler] = {
    **{f"fathom.{s}.proposal.created":     project_created     for s in SubAppSlug},
    **{f"fathom.{s}.proposal.adjudicated": project_adjudicated for s in SubAppSlug},
    **{f"fathom.{s}.proposal.expired":     project_expired     for s in SubAppSlug},
    # [AMENDMENT] audit's purge/rewrap proposals, on AUDIT_PROPOSAL_TOPIC above —
    # the same three handlers, keyed on the platform-service exception.
    "fathom.audit.proposal.created":     project_created,
    "fathom.audit.proposal.adjudicated": project_adjudicated,
    "fathom.audit.proposal.expired":     project_expired,
}
```

Five projector rules, each with its finding:

1. **Precedence is `(producer_slug, producer_node_id, monotonic_seq)`, never a timestamp.** A `proposal.adjudicated` arriving before the `proposal.created` it follows — possible across a partition, and certain when a hull reconnects and drains a six-week outbox (06 §4) — must not be overwritten by the later-arriving `created`. The upsert therefore applies only when `excluded.last_monotonic_seq > proposal_queue.last_monotonic_seq` for the same `(producer_slug, producer_node_id)`. Where the pair differs, the row is not comparable and the event is projected as a distinct fact only if it strictly advances `status` along the 03 §7.2 lifecycle. `announced_recorded_at` is stored and **never compared**, per 11 §11.5's static gate 4, which forbids any sort or comparison key over `recorded_at`.

2. **Epoch fencing does not apply, and this is a deliberate exception with a reason.** 11 §3.5 fences any event whose `baseline_epoch` exceeds the consumer's configuration read model. The gateway holds no configuration read model — by D32-R1, it holds no domain read model at all — so there is nothing to fence against, and fetching Registry `changed_since` to build one would be exactly the D32 defect. Instead, `baseline_epoch` is stored verbatim and surfaced as a warning; the authoritative staleness check is the owner's mandatory re-validation at adjudication (03 §7.2, D16). **Recorded explicitly** because 09 §8.3's checklist item ("antecedent rule implemented") would otherwise read as unmet: it is met by not needing it, and §13 says so.

3. **`replay: true` events project idempotently and raise no operator-visible alert** (03 §5.3, D30). A backfilled proposal appears in the queue as a historical row; it does not notify, and it does not count toward admission-control depth for the current period.

4. **Provisional identity is resolved on read, not rewritten on projection.** A `configuration_change` proposal submitted at the edge (03 §7.2.1) may carry a provisionally-minted `installed_item_id` (03 §3.3, 11 §8). 11 §1.1 makes the alias resolver active in *"every read model"*, and 11 §12 item 13 forbids rewriting records published under a provisional identity. So: `subject_provisional` is stored, the alias resolver runs at query time, and the queue response carries both the provisional and the confirmed identifier when they differ.

5. **A malformed or cross-domain event is quarantined and alarmed, never projected.** A row failing `proposal_queue_owner_is_producer` means a sub-application published a proposal targeted at a neighbour — a 03 principle 3 / C32 violation. A row failing `proposal_queue_dual_control_at_scope` means an upstream constructed a class- or fleet-scoped proposal (or a `purge`/`rewrap` proposal at any scope) without dual control, which is 03 §7.2 rule 4. Both are upstream contract violations. The projector writes the inbox row with `processed_at` NULL and `last_error` set, increments `fathom_gateway_projection_rejections_total{reason,producer}`, logs at ERROR, and **does not** advance to a state where the event is suppressed — so remediating the upstream and redelivering works.

### 4.4 Ordering, cursors, and why there is no global "oldest first"

The queue cannot offer a globally correct "oldest first" across nine independent producers, and this is a consequence of the clock discipline rather than an omission. Document 03 §5.4 permits ordering only on `(producer, producer_node, monotonic_seq)` — which is per-producer and therefore not comparable across nine — or on the HLC; and 11 §11.5's gate 4 forbids sorting on `recorded_at`, `occurred_at`, or `source_time` at all. A cross-producer domain-time ordering would require a trusted global clock, which D29 establishes the system does not have.

Three sort orders are offered, and each is honest about what it claims:

| Sort | Key | What it means | Default |
|---|---|---|---|
| `expiry` | `(valid_until ASC, projection_seq ASC)` | **Act-before-this order.** `valid_until` is a contractual domain field the owner authored (03 §7.2), so this is the operationally correct urgency ordering and the one an adjudicator wants | **Yes** |
| `confidence` | `(confidence DESC, projection_seq ASC)` | Agent-asserted confidence. Presented as the agent's claim, never as a priority | No |
| `learned` | `(projection_seq ASC)` | **The order the gateway learned of them.** Not a claim about when they were created | No |

`projection_seq` is a PostgreSQL identity column: a gateway-local, monotonically increasing integer that is not a clock and asserts nothing about domain time. It exists for two reasons — it is the stable tie-breaker every cursor needs for a total order, and it is the only honest "arrival order" available.

**Two rules on presentation, which belong in a build document because getting them wrong is a correctness failure the UI cannot detect:**

- `learned` **must not be labelled "oldest first."** Under the scripted six-week single-SSN disconnection (06 §4, 13 §15), a proposal created afloat in week 1 arrives at the gateway in week 7 and takes a `projection_seq` after everything created ashore in the interval. Labelling that "oldest first" would systematically bury exactly the afloat proposals the edge-scope decision exists to capture (D8).
- `announced_recorded_at` is exposed **only** alongside `announced_dispersion_ms`, and a UI must not render it as a precise time when dispersion exceeds the inter-arrival interval. This is 03 §5.4's dispersion rule applied to the queue: *"epsilon exceeding the inter-write interval forces causal-only ordering and forbids any timestamp arbitration."* A hull disconnected for weeks reports a large `dispersion_ms`, and the queue says "recorded approximately" rather than a false timestamp.

**Cursor format.** Opaque base64url over `(sort, sort_key_value, projection_seq)` plus a projection-generation token that changes on rebuild, so a cursor issued before a rebuild is rejected with `400 urn:fathom:problem:gateway:cursor-generation-stale` rather than silently skipping or repeating rows. No total count on the unbounded collection (03 §4).

### 4.5 The queue API

Base path `/api/v1/gateway/`. All operations `x-substitution: internal` (§8.3).

#### `GET /proposals` — list and filter · `x-side-effects: none` · `x-agent-eligible: false`

| Parameter | Values | Source |
|---|---|---|
| `status` | repeatable; `ProposalStatus` | 03 §7.2 |
| `kind` | repeatable; `ProposalKind` | 03 §7.2 [C39] |
| `target_sub_app` | repeatable; slug | 03 §3.1 |
| `authority_class` | repeatable; `maintainer\|planner\|supply_officer\|design_authority\|fleet_authority\|security_officer` | **03 §7.2.1**, six classes as of amendment 03-1 — **[amendment]** closes `51-operator-console.md` §22 row 15 (blocking sheet 11's filters and the hub's Security Officer card): this row was still the pre-amendment five |
| `blast_radius` | repeatable; `item\|asset\|class\|fleet` | 03 §7.2 [D16] |
| `requires_dual_control` | boolean | 03 §7.2 rule 4 |
| `awaiting_second_signature` | boolean — `requires_dual_control` and one signature present | 03 §7.2 |
| `asset_id`, `system_id`, `installed_item_id`, `niin`, `class_id`, `mission_id` | canonical identifiers only | 03 §3.3 |
| `expires_before` | RFC 3339 | 03 §7.2 |
| `epoch_superseded` | boolean — the staleness **warning** flag, not a filter the owner honours | 03 §7.2 [D16] |
| `claimed` | `any\|none\|me\|other` | 03 §7.2 [D16] |
| `flagged_non_program_evidence` | boolean | 03 §7.2 rule 1 [D14] |
| `agent_id`, `agent_version` | exact | 03 §7.2 |
| `sort` | `expiry\|confidence\|learned` (default `expiry`) | §4.4 |
| `limit`, `cursor` | cursor pagination; no total count | 03 §4 |

Filtering is by explicit named parameters only — no general-purpose query language on the public surface (03 §4).

Response, per row, is exactly the `PROJECTED_COLUMNS` allowlist rendered as wire fields, plus three computed presentation flags and no domain content:

```json
{
  "items": [
    {
      "proposal_id": "…",
      "kind": "redesign_case",
      "target_sub_app": "design-advisory",
      "authority_class": "design_authority",
      "blast_radius": "fleet",
      "requires_dual_control": true,
      "status": "proposed",
      "scope": "fleet",
      "subject": {},
      "subject_provisional": false,
      "valid_until": "2026-08-18T00:00:00+00:00",
      "baseline_id": "…",
      "baseline_epoch": 412,
      "claimed_by": null,
      "claimed_until": null,
      "adjudicated_by": null,
      "second_adjudicator": null,
      "counter_signature_by": null,
      "counter_signature_at": null,
      "confidence": 0.71,
      "evidence_count": 4,
      "non_program_evidence_only": false,
      "agent_id": "redesign-case-builder",
      "agent_version": "2.1.0",
      "trace_ref": "…",
      "classification": { "level": "U", "cui_categories": [], "dissemination": [] },
      "announced_recorded_at": "2026-08-03T09:14:02.110000+00:00",
      "announced_dispersion_ms": 12,
      "expires_within_hours": 336,
      "second_signature_outstanding": false,
      "detail": { "href": "/api/v1/gateway/proposals/…" }
    }
  ],
  "next_cursor": "…",
  "queue_freshness": {
    "classification_level": "U",
    "lag_seconds": 3.2,
    "stale": false,
    "staleness_bound_seconds": 300,
    "completeness": "level_scoped"
  }
}
```

`queue_freshness` is mandatory on every list and summary response. Three of its members exist for specific findings: `lag_seconds`/`stale` make 03 §5.2's *"consumer staleness is observable"* visible to the human rather than only to `/metrics` (§4.7); `classification_level` and `completeness: "level_scoped"` implement 06 §5 rule 3's *"a low-side rollup never presents itself as complete"* for the queue.

**`subject`'s members, enumerated by `scope` — `[amendment, closes 51-operator-console.md §22 row 16, blocking]`.** The row above showed `subject: {}` only because its example is `scope: fleet` (03 §3.3's singleton exception). For every other scope, `subject` carries exactly the one canonical identifier 03 §5.4's envelope rule names for that scope — the same mapping `10-shared-packages.md` §4's `SCOPE_SUBJECT_FIELD` fixes for events, reused here rather than re-derived: `asset_id` (asset), `system_id` (system), `installed_item_id` (installed_item), `niin` (niin), `class_id` (class), `mission_id` (mission), `tycom_id` (tycom), none (fleet). **The provisional/confirmed pair** §4.3 rule 4 requires — *"carries both the provisional and the confirmed identifier when they differ"* — is named explicitly: `subject.provisional_id` and `subject.confirmed_id`, both present only when `subject_provisional: true` and they differ; otherwise `subject` carries the single confirmed identifier under its scope's field name as shown above.

**`POST /proposals/{proposal_id}/adjudicate`'s request body — `[amendment, closes 51-operator-console.md §22 row 17, blocking]`.** `{decision: "approve" | "reject", note}`. `note` is required on `reject` and optional on `approve`, matching every owning sub-application's own adjudication rule (03 §7.2's re-validation notwithstanding — this is the human's stated reason, not a re-validation input). The gateway does not invent a richer body: it is a **verbatim pass-through** to the owner's own `PATCH`/`POST .../adjudicate` operation (03 §10's substitution discipline — the gateway must not diverge from what a substituted owner actually accepts), and every owner's adjudication operation accepts exactly this shape, `decision` and `note`, regardless of `kind`. A `second_adjudicate` action (the second signature at class/fleet scope) uses the identical body on the identical path — the owner distinguishes first from second signature by whether `adjudicated_by` is already set, not by a different request shape.

**`POST /proposals/{proposal_id}/claim`'s request body is empty** — `[amendment, closes 51-operator-console.md §22 row 64]`. No fields; the lease is minted from the authenticated caller and the operation's own `Idempotency-Key`.

#### `GET /proposals/summary` — depth by bucket · `x-side-effects: none`

Counts grouped by `status × authority_class × blast_radius × target_sub_app`, plus a total for the deployment's level. A query-projection singleton under 03 §4's carve-out; enumerated in `x-naming-carve-outs` with this reason (09 §8.1). See §4.8.

#### `GET /proposals/{proposal_id}` — the detail fetch · `x-side-effects: none`

The queue row **plus** the full proposal, fetched synchronously from the owner. §4.6.

#### `POST /proposals/{proposal_id}/claim` — proxied · `x-side-effects: state-changing`

#### `POST /proposals/{proposal_id}/adjudicate` — proxied · `x-side-effects: state-changing`

Both in §4.6. Both require `Idempotency-Key` (09 §5.3); `adjudicate` additionally requires `If-Match` (03 §4, 03 §7.2, 09 §5.4).

**No `x-agent-eligible` operation exists on the gateway's own surface.** Adjudication is a human act (03 §7.2.1: *"which human organizational role is permitted to adjudicate"*), and 03 §8.1 permits eligibility only where side effects are `none` or `proposal-only`. The read operations qualify on side effects but are marked ineligible anyway, deliberately: an agent that could read the adjudication queue could observe which of its own proposals were rejected and by whom, which is an unadjudicated feedback channel of the kind D23 objects to. Agents obtain state through sub-application tools (03 §6, C19), and the queue is not a domain.

### 4.6 Detail, claim, and adjudicate — all proxied

This is where D32-R1's "fetch on demand" becomes concrete, and where the gateway's non-authority becomes concrete.

**Detail.** `GET /api/v1/gateway/proposals/{id}` performs one upstream call: `GET /api/v1/{target_sub_app}/proposals/{id}`, resolved from the row's `detail_fetch_path`. The response is the owner's `Proposal` — the full 03 §7.2 object with `payload`, `evidence[]`, and `rationale` — merged with the queue row's presentation flags, and **the owner's `ETag` passed through verbatim**.

| Situation | Response |
|---|---|
| Owner returns `200` | `200`, owner's `ETag`, owner's `X-Classification`, full proposal |
| Owner unreachable, times out, or `5xx` | `503` `urn:fathom:problem:gateway:owner-unavailable`. **Never a partial proposal.** Adjudicating a proposal whose payload and evidence could not be read is precisely D16's defect wearing a friendlier face |
| Owner returns `404` | `404`, and the queue row is marked for re-projection: the projection is stale or the proposal was purged upstream. The gateway does not delete the row on a single `404` — a `404` from one replica during a rolling deploy is not authority |
| Owner returns `403` | `403`, passed through. The owner is the authority on who may read it (03 obligation 7) |
| Row absent from the projection but the owner has it | Served anyway if `{target_sub_app}` can be resolved from the request, with `queue_freshness.stale: true`. **The projection is an index, not a gate** — property 2 (§2.3). A proposal the queue has not yet learned of is still adjudicable |

The last row matters and is easy to get wrong: making the projection a precondition for the detail fetch would convert the index into an authority and re-break property 2. Volume makes it costless — 06 §7 gives **fewer than 20 agent proposals per day**, so the detail fetch happens at most a few tens of times a day, against a per-adjudication budget of ~45 s (06 §6). One synchronous upstream call is not a scaling question at this volume, and the design does not depend on it being one at any volume, because it is one call per *opened* proposal, not per queue view.

**Claim.** Proxied to `POST /api/v1/{target_sub_app}/proposals/{id}/claim` (03 §7.2 rule 3). The gateway **does not implement the lease**: no `claimed_by` write to its own store, no lease timer, no expiry sweep. Claim state reaches the queue only through `proposal.adjudicated`/`proposal.created` projections and through the detail fetch. Rationale, stated because a gateway-side lease is a tempting optimisation: D16's failure is *"two planners approve the same proposal and two work orders result,"* and a lease held anywhere but the transactional store that performs the state change is not a lease. Two gateway deployments, or one gateway and one direct API caller, would each hold their own.

**Adjudicate.** Proxied to the owner's adjudication operation, with three inviolable rules:

- **`If-Match` is forwarded verbatim and never synthesized.** If the client omits it, the gateway returns `428 Precondition Required` (09 §5.4 makes this stricter than 03 §4's letter, deliberately, for D16). The gateway must never supply an `If-Match` value of its own — a gateway-generated ETag would defeat the entire concurrency mechanism while appearing to satisfy it. `test_gateway_never_synthesizes_if_match` asserts no outbound request carries an `If-Match` absent from the inbound one.
- **The gateway performs no authority check.** Whether this principal's roles satisfy the proposal's `authority_class` at its `blast_radius` (03 §7.2.1), and whether dual control is satisfied by two *distinct* adjudicators, are the owner's determinations, re-validated at adjudication time. The gateway carries `authority_class` in the queue so a UI can *route work to the right person*; routing is not authorization. `test_gateway_forwards_an_authority_violation` asserts a proposal the caller lacks authority for is **forwarded** and rejected by the owner, not pre-rejected by the gateway — because a gateway that pre-rejects becomes the policy decision point, and 03 obligation 7 forbids relying on it.
- **The `Idempotency-Key` is forwarded verbatim**, so the owner's replay semantics (09 §5.3) are the authoritative ones. The gateway records its own idempotency entry for its own route as well, so a client retry does not produce two upstream calls — but the outcome stored is whatever the owner returned, including a `409` or `412`, and a `429` is never stored (§6.5).

### 4.7 Staleness, rebuild, and purge

**Staleness.** `stalenessBoundSeconds: 300`, adopted from 09 §4.4.1's declared shared default rather than invented (09 DO-NOT 31). The bound is not a correctness constraint here — no computation depends on queue freshness, by property 2 — so the shared default is the honest choice, and the operational requirement it must satisfy is loose: a proposal must appear within one adjudication cycle, and 06 §6's cycle is monthly.

The consequence of 09 §5.6 ("exceeding the bound makes the service **not ready**") needs care, and §11.2's two-Deployment split is what makes it safe:

- The **projector** registers the `read_model_lag` readiness check. Exceeding the bound makes the projector not-ready, which is the correct signal and which KEDA and alerting act on.
- The **API** Deployment consumes nothing and therefore has no read-model lag of its own. It must not fail readiness on projection lag: taking the entire operator interface out of rotation because the proposal projection is behind would be a self-inflicted outage in which every view, every agent tool call, and every batch scoring write fails because a badge is stale.
- Instead the API reports lag **in the response**, via `queue_freshness.stale`. The operator sees "this queue may be incomplete"; the fleet view still loads. This is 03 §5.2's observability requirement met without converting it into an availability hazard.

**Rebuild.** Per-owner `changed_since` sweep, never the event bus (03 §4, 03 §5.1, D5).

```sql
CREATE TABLE queue_rebuild_watermark (
  target_sub_app   text        PRIMARY KEY,
  changed_since    timestamptz NOT NULL,   -- the owner's own watermark semantics
  cursor           text        NULL,
  completed_at     timestamptz NULL,
  generation       bigint      NOT NULL    -- bumped on every full rebuild; see the cursor rule in §4.4
);
```

```
for slug in (*SubAppSlug, "audit"):            # the nine, 03 §3.1 / 10 §4.2, plus
                                                # the AUDIT_PROPOSAL_TOPIC exception (§4.1)
    GET /api/v1/{slug}/proposals?changed_since=<watermark>&cursor=<cursor>
    upsert each row into proposal_queue, projecting ONLY PROJECTED_COLUMNS
    advance the watermark and cursor in the same transaction as the upserts
```

The projection function is the **same** function the event path uses — one `project(proposal) -> ProposalQueueRow` — so the two paths cannot diverge and the allowlist is enforced once. This is what makes `test_d32_read_model_rebuild_with_bus_down` a meaningful equality assertion rather than a comparison of two implementations.

Note the reciprocal obligation this places on the nine, **and on `audit`**: each must expose `GET /proposals?changed_since=&cursor=` because the gateway is a declared consumer that projects the aggregate (03 §4, obligation 5). **[AMENDMENT]** `audit`'s own build document (`32-audit.md`) declared `GET /records?changed_since=&cursor=` for its audit-record aggregate but no equivalent for the `Proposal` aggregate its `POST /proposals` operation creates — closed there by adding `GET /proposals?changed_since=&cursor=` alongside it. The gateway contributes the consumer-driven conformance test that proves it for all ten (§10.4), which is how the obligation becomes enforceable rather than aspirational.

**Purge.** Document 03 §13 item 2 requires *"a declared purge protocol covering every store, including Domino-side traces and gateway-held read models, with an owner and a tested procedure."* This document declares it:

| Store | Immutability | Purge mechanism | Owner |
|---|---|---|---|
| `proposal_queue` | **Operationally derived.** Not a record of anything; an index | **Truncate and rebuild.** `DELETE` the affected rows (or `TRUNCATE` the table), bump `generation`, re-sweep `changed_since` | Gateway service owner |
| `inbox` | Operationally append-only | Row delete plus re-projection; `sync_quality` already exported to `audit` for permanent retention (11 §10.5), so deletion here loses no attestation | Gateway service owner |
| `idempotency_keys` | Operationally append-only, 24 h retention (09 §5.3) | Row delete; expiry does the rest | Gateway service owner |
| Composed views, detail responses, exchanged tokens | **Not stored** (§3.5, §5.3) | Nothing to purge | — |

This is the strongest single argument for D32-R1 over any payload-carrying design, and it is worth stating plainly: **a classification spillage reaching the gateway is remediated by deleting rows and re-projecting.** No crypto-shredding, no compacted-topic tombstones, no coordinated multi-store mutation — because there is no content in the store to shred. D15 is an accreditation blocker; option (a) makes the gateway's contribution to it trivial. A queue holding nine domains' payloads and evidence excerpts would have made the single most-reached component in the system one of the hardest to remediate.

### 4.8 Queue depth, admission control, and the boundary the gateway does not cross

Document 06 §6 sets admission control: *"If unadjudicated candidates exceed 3× monthly throughput, candidate generation halts and an alarm raises."*

The gateway **measures**; it does not **halt**.

- **Measures:** `GET /proposals/summary` and the metric `fathom_gateway_proposal_queue_depth{status,target_sub_app,authority_class,blast_radius}`, both scoped to the deployment's classification level (§2.5 item 4 — there is no cross-level total, and none is obtainable).
- **Does not halt:** the gateway has no authority to stop anything. Halting candidate generation is Post-Mission Analysis's decision on its own pipeline; halting agent proposal generation is the agent runtime's. The gateway is an unauthenticated-to-authenticated ingress and a composition layer; giving it a throttle over another sub-application's pipeline would make it a control plane, and there is no contract in which it holds that authority.

One distinction must not be blurred, because conflating the two would misreport the metric that D17 exists to protect: **06 §6's "candidates" are PMA review candidates, not `Proposal`s.** The candidate cap of 12 per review, the ~840 candidates per month, and the 3× admission threshold are PMA's review pipeline. The pre-screener's confirmed outputs become `anomaly_tag` proposals, which is a strictly smaller flow — 06 §7 puts *all* agent proposals under 20 per day. The gateway supplies the proposal half of the picture and labels it as such; PMA's own build document owns the candidate half. A dashboard that added them would report a number that means nothing.

---

## 5. Authentication and token exchange

### 5.1 Bearer token validation

Document 03 §4: *"Authentication — OIDC bearer tokens. Service-to-service calls carry the calling workload's identity."* The gateway validates; `auth` issues.

| Concern | Rule |
|---|---|
| Algorithms | Asymmetric only — `RS256`, `RS512`, `ES256`, `ES384`. An **allowlist**, not a denylist: `alg: none` and every HMAC family are rejected because the key material is asymmetric and an HMAC-accepting validator can be attacked with the public key |
| Key material | JWKS from `auth` (Keycloak, federated with Domino's Keycloak per 04 §11). Cached; **forced refresh on an unknown `kid`**, rate-limited so an attacker cannot drive JWKS fetches with fabricated `kid` values. A validation failure after a forced refresh is terminal |
| Claims validated | `iss` (exact match against configured issuer), `aud` (must contain `gateway`), `exp`, `nbf`, `sub` present and non-empty, `typ` is an access token |
| Claims **not** interpreted | Roles, groups, clearance, caveats, compartments, unit, billet, qualification. The gateway reads none of them. §5.7 |
| Transport | TLS terminated at program ingress; in-cluster hops over the cluster's transport security. The token is never logged, never placed in a URL, never in a problem-detail body (09 §4.8) |
| Failure | `401` RFC 9457 `urn:fathom:problem:gateway:unauthenticated`, with `WWW-Authenticate: Bearer`. The `detail` member states the *class* of failure and never which claim failed or what value was expected — 03 §4 makes `detail` non-control-flow, and a validator that reports why it rejected a token is an oracle |
| Unauthenticated surface | Exactly `/healthz`, `/readyz`, `/metrics`. Nothing else, in any environment. `docs_url` and `redoc_url` are `None` (09 §4.6) |

### 5.2 The one sanctioned wall-clock read, declared

`exp` and `nbf` are wall-clock values by RFC 7519. There is no monotonic formulation of token expiry, so this is the single place in the gateway where a wall clock decides something — and D29 makes that worth declaring rather than leaving as an unexamined exception.

```python
# platform/gateway/src/fathom_gateway/auth/clock.py
"""THE ONLY WALL-CLOCK READ IN THIS SERVICE.  [D29 · 03 §5.4 · 11 §11.5 gate 5]

JWT `exp`/`nbf` are wall-clock instants by RFC 7519 §4.1.4/§4.1.5.  A monotonic
clock cannot express them, because the issuer and the validator are different
processes on different hosts.  So this function exists, in one module, and:

  * It is used ONLY for `exp`/`nbf`.  Nothing else in the gateway may import it —
    enforced by an import-linter contract (see 10 §9.4 for the pattern).
  * Leeway is 60 s, FIXED.  Not configurable: a deployment that widens it to
    paper over host skew is a deployment that has stopped enforcing expiry.
  * The mitigation for a backward STIG clock step (V-260520, `makestep 1 -1`) is
    NOT a wider leeway.  It is 03 §5.4's time-service requirement: SC-45/SC-45(1),
    1 ms audit granularity, 1 s resync threshold, and a local stratum-1 reference.
    A gateway host outside that discipline mis-validates tokens, and there is no
    application-level fix.  §11.4 makes host time sync a deployment prerequisite.
  * `step_occurred` on the host's clock attestation is exported as
    `fathom_gateway_clock_step_total`, so a step is visible rather than inferred
    from a burst of 401s.

EVERY OTHER TIME DECISION — request deadlines, fragment timeouts, retry backoff,
circuit-breaker windows, rate-limit refill, lease evaluation — uses
time.monotonic() via composition/deadline.py.  See §3.3 and §6.3.
"""
JWT_LEEWAY_SECONDS: int = 60
```

### 5.3 Delegated authority — one exchange, forwarded unchanged

**[AMENDED — reconciled against `31-auth.md` §4.1, §3.2, which is authoritative.]** This section originally specified a two-hop model in which the gateway itself called Keycloak's token-exchange endpoint twice, re-narrowing `audience` and `scope` at each tool call and carrying a second credential (`X-Fathom-Delegation`) alongside the caller's own workload token. **That model is superseded.** All three Wave-5 agent-runtime build documents (`40-copilot.md` §16 item 1, `41-pma-prescreener.md` §20 items 7–9, `42-redesign-case-builder.md` §18 items 7 and 14) independently reconciled against `31-auth.md`'s flow instead and flagged this section as the one needing the edit — three of three runtimes converging on the same reading is the signal that this document, not the runtime documents, was carrying the defect.

This is the mechanism 04 §11 assigns to the gateway and names only as *"token exchange for delegated authority."* Document 03 §8.3 states the requirement it must satisfy: for the **Delegated** class, *"the user's delegated token"* with *"reach bounded by the user's own authorization, evaluated by the receiving sub-application."* Document 01 §8.5 puts it operationally: *"A maintainer's copilot cannot read what the maintainer cannot read."*

> **DECISION G-4, revised.** **One RFC 8693 exchange per agent turn, mediated by `auth`, not by the gateway calling Keycloak directly.** The resulting token carries `aud` as the **union** of the pinned manifest's target slugs (not narrowed per call) and is **forwarded unchanged** on every subsequent tool call for the life of the turn. There is no second exchange and no second credential.

**The flow, exactly `31-auth.md` §4.1's:**

```http
POST /api/v1/auth/delegations HTTP/1.1
Host: auth.fathom-sustainment.svc.cluster.local
Authorization: Bearer <the user's own access token, verbatim as received>
Content-Type: application/json

{ "agent_id": "copilot", "manifest": "pdm-equipment-deepdive", "manifest_version": 2 }
```

`auth` — not the gateway — re-runs the manifest eligibility gate against the committed OpenAPI document (31 §4.1 steps 4a–4c), derives `aud` from the manifest's targets (step 4d), performs the RFC 8693 exchange against Keycloak internally, persists the delegation record, and writes the audit record. The gateway's role is to be the **caller** of `POST /api/v1/auth/delegations`, holding the user's access token as a BFF (*"the user's access token never leaves the server"*) and never touching Keycloak's token endpoint itself. Resulting token (31 §3.2's exact shape, transcribed):

```json
{
  "iss": "https://keycloak.internal/realms/fathom",
  "sub": "b31f…",
  "aud": ["pdm", "registry", "telemetry"],
  "azp": "fathom-agent-copilot",
  "exp": 1770000900, "iat": 1770000600,
  "scope": "fathom.agent.delegated sfx:none sfx:proposal-only",
  "act": {
    "sub": "svc:agents/copilot",
    "fathom": { "agent_id": "copilot", "agent_version": "3.2.0", "llm_version": "…" }
  },
  "fathom": {
    "identity": { "…": "byte-identical to the user token's identity block" },
    "agent": {
      "authority": "delegated",
      "run_id": "0f2c8f5a-…",
      "delegation_id": "d-7731…",
      "manifest": "pdm-equipment-deepdive",
      "manifest_version": 2,
      "api_major": 1,
      "trace_ref": "mlflow://…"
    }
  }
}
```

**The gateway invokes the agent, passing this one token** (31 §4.1 step 5). Every subsequent tool call the agent makes — through the tool server, back through the gateway to the target sub-application — presents `Authorization: Bearer <this same token>`, unmodified. **There is no `X-Fathom-Delegation` header, no second `Authorization`, and no re-exchange.** 31 §4.1: *"THE TOKEN IS FORWARDED UNCHANGED. The gateway never swaps it for its own workload identity"* [03 §15 obligation 7].

**How the user's authority actually reaches the receiving sub-application.** The sub-application authorizes on `sub` — the human — against its own ABAC attributes, exactly as it would for a direct human call (03 §4, obligation 7). Nothing about the request tells it to relax anything. It audits on `act`, which names the agent, its version, and (nested one level deeper) the gateway. That is the whole mechanism, and its virtue is that **the receiving sub-application needs no agent-specific authorization logic at all**: an agent call is a user call with an actor annotation. This is the runtime expression of 01 §8.0's claim that sub-application APIs are the tool surface by construction.

**Why `aud` is a list rather than narrowed per call.** The rejected two-hop design narrowed `audience` to one slug at tool-call time on the theory that a token minted for a PdM what-if call should not be replayable against Scheduling. 31 §3.1's rule achieves the same property without a second exchange: *"A receiving service requires its own slug in `aud` and rejects otherwise"* — the token is already useless outside the manifest's declared target set, and narrowing further at each call adds a second exchange (with its own failure mode, `[VERIFY]`-gated Keycloak behavior twice instead of once) for no additional safety.

**Constraints on the delegation token, enforced by `auth` at issuance (31 §3.2) and asserted at the gateway on every forward (§10):**

| Constraint | Value | Reason |
|---|---|---|
| Audience | The manifest's target slugs, as a list | A slug not in `aud` is rejected by the receiving service; no broader reach exists |
| TTL | Default 300 s, `FATHOM_AUTH__DELEGATED_TTL_SECONDS`, **never exceeding the parent session's remaining life** | `exp ≤ min(iat + TTL, parent_session_exp)` (31 §3.2). One exchange, one lifetime — there is no second exchange to extend it |
| Scope | `fathom.agent.delegated` plus the `sfx:` classes the manifest's operations require — **never** `sfx:state-changing` | 03 §8.1/§15 obligation 8; 31 §3.2 |
| `fathom.agent.authority` | `delegated` | 31 §2.5 amendment A-2. Not `fathom:authority_class` — that bare name collides with 03 §7.2.1's distinct `Proposal` field |
| Caching | **None**, at the gateway or anywhere else. The token is forwarded, not reconstructed | A cached delegation token is a bearer credential for a specific principal at a specific instant |
| Storage | **None.** Held in the request scope, never persisted, never logged (09 §4.8) | |

**The rejected alternative, recorded.** A **signed gateway assertion** — the gateway mints a short-lived JWT with its own key, carrying `sub`/`act`/`aud`/`scope`, validated by sub-applications against the gateway's JWKS — is a working mechanism and is the documented fallback if `auth` cannot supply RFC 8693 token exchange with `act` and the `fathom` claim namespace. It is not the primary choice because it makes the gateway a **token issuer**, which makes it a second root of trust for authorization decisions and a component whose key compromise mints authority for any user. §5.7's whole argument is that the gateway must not become the place authority is decided; issuing the credentials that carry authority is a short step from deciding it. Adopting the fallback requires an ADR (09 §7.5) and a note in the SSP that the gateway's signing key is an authorization root.

**Dependency, flagged rather than assumed.** `auth` must implement the exchange grant, including `act` nesting. Keycloak documents token exchange, but exact conformance on this claim is a **verification item at implementation time**, per 31's own **OQ-31-1** and 09's verification convention. It is downstream of 01 §8.7's machine-to-machine authentication dependency — *"the single open dependency capable of altering the agentic design."* Note that 01 §8.7's contingency (relocating agent orchestration to the Sustainment Plane) does **not** change any of the above: the exchange, the claims, and the forwarding rule are identical whether the agent runtime is a Domino application or a Sustainment Plane workload. Only the network path changes.

### 5.4 Accountable autonomous — no exchange, because there is no subject

Document 03 §8.3's second class covers *"event-triggered and scheduled agents — PMA Pre-Screener, Readiness Narrative, scheduled evaluation."* D12's finding is that delegated authority is *unsatisfiable* here: there is no requesting user, so there is no subject token, so there is nothing to exchange.

The gateway therefore performs **no exchange** on this path. The agent runtime holds a client-credentials workload identity issued by `auth` (31 §3.3), and the gateway validates it like any other bearer token, with three additional assertions:

| Assertion | Failure | Reason |
|---|---|---|
| `fathom.agent.authority == "accountable_autonomous"` | `403 urn:fathom:problem:gateway:authority-unknown` | An unrecognised class is not a default-allow. Naming per 31 §2.5 amendment A-2 — not `fathom:authority_class` |
| `fathom.agent.accountable_owner` present and non-empty | `403 urn:fathom:problem:gateway:accountable-owner-absent` | 03 §8.3 requires *"a named accountable human owner."* A run with no owner is a run nobody answers for, and the gateway is where that becomes unrepresentable |
| The matched route's `x-side-effects` is `none` or `proposal-only` | `403 urn:fathom:problem:gateway:autonomous-state-change-refused` | 03 §8.3: *"Restricted to `x-side-effects: none` and `proposal-only`"* |

The third is **defense in depth and is declared as such.** 09 §5.5 already places this check in every sub-application's `require_authz` dependency, and 03 obligation 7 makes the sub-application's check the authoritative one. The gateway's copy exists because it is cheap, because the route's side-effect class is statically known at the gateway (§8.2, decision G-3), and because a state-changing call from an autonomous agent is a class of request that should not traverse the network at all. §5.7 enumerates it as one of exactly two authorization-adjacent decisions the gateway makes, so that "the gateway does not authorize" remains a checkable statement.

Every `accountable_autonomous` request is recorded to `audit` with the accountable owner, per 03 §8.3's *"Every run recorded to Audit with the accountable owner."*

### 5.5 Mid-run authority lapse

Document 03 §8.3 and D12: *"An agent run whose delegated token expires, or whose pod is restarted by platform maintenance, terminates and records a resumable checkpoint. It does not silently continue under a service identity, and it does not create a proposal after its authority has lapsed."*

The gateway is where "silently continue under a service identity" would happen, because it is the component holding both the user's delegation and its own workload identity. One rule closes it:

> **The gateway has no code path in which a request that arrived bearing a delegation token is retried, re-sent, or forwarded under the gateway's own workload identity — or under any identity other than the one derived from that delegation.** Not on `401`, not on `403`, not on a connect failure, not on a circuit-breaker probe.

An expired or invalid delegation token yields `401 urn:fathom:problem:gateway:delegated-authority-lapsed`, with `Retry-After` absent — there is nothing to retry, because the authority is gone and only a fresh user interaction can restore it. The agent runtime terminates with a resumable checkpoint; that behaviour is the agent's, and the gateway's contribution is refusing to make it unnecessary.

The gateway also does **not** refresh a delegation token on the agent's behalf. It holds no refresh token for any user, ever. A refresh capability at the gateway would be a standing ability to act as any user who has ever used the system, which is the same objection as §5.3's rejected fallback in a different form.

`test_d12_no_service_identity_fallback` asserts it structurally: it drives every upstream failure mode against a delegated request and asserts that every outbound `Authorization` header in the resulting trace derives from the inbound delegation, and that the gateway's own workload token appears in no upstream request on that path.

### 5.6 Domino Endpoint proxying

Document 03 §8.3 and D12, from 02 §4.3: *"A Domino Endpoint authenticates with a static token carrying no caller identity and no per-caller audit trail. Every Endpoint call is therefore made through a Sustainment Plane service that attaches caller identity to the audit record."*

The gateway is that service.

```
POST /api/v1/gateway/inference/{domino_endpoint_name}
    x-substitution: internal
    x-side-effects: none          # interactive inference: tier-3 what-if (01 §3 correction 2)
    x-agent-eligible: false       # an agent reaches inference through a sub-application's
                                  # x-side-effects:none computational operation (03 §8.2's
                                  # pdm-whatif manifest), not through this route
    Idempotency-Key: required     # 09 §5.3
```

| Rule | Reason |
|---|---|
| The static Endpoint token is a gateway-held secret, projected as an env var by External Secrets (01 §11, 09 §4.5), and **exists nowhere else in the system** | It carries no caller identity, so anywhere it exists is a place calls become anonymous |
| The caller's token — user, delegation, or workload — is **never** forwarded to Domino | Domino cannot validate it, and forwarding a bearer credential to a system that ignores it is a credential leak with no benefit |
| An audit record is written **before** the response returns, carrying `principal_id`, the full `act` chain, `correlation_id`, `trace_ref`, the Endpoint name, and request/response digests | This route exists *for* the audit record. Writing it after the response would make a crash lose exactly the record the route was built to produce |
| A `503` from the audit write fails the request | If the identity attribution cannot be recorded, the anonymous call must not be made |
| The declared timeout is below Domino's documented practical request ceiling near 60 s (01 §3 correction 2), and a timeout returns `504` with the audit record already written | 01 §3 correction 2 also records that Domino Endpoints have *"no cancellation of timed-out requests"* — so a gateway timeout does not mean the inference stopped, and the audit record must reflect that a call was made |
| Egress to Domino namespaces is a declared NetworkPolicy edge — see §11.3 and §14 item 3 | 09 §4.4.2's sanctioned edge table does not currently name `gateway → domino-*`; this document requires it and flags the gap |

Note the boundary: this route is a **proxy**, not an agent host and not a model server. It attaches identity and audits. Batch scoring does not use it — scoring Jobs write predictions through PdM's bulk ingest operation on the pass-through surface (01 §3 correction 2, 09 §4.4.2), which is a write path, not an inference path.

### 5.7 What the gateway does not decide

This section exists because 03 §4 and obligation 7 state the constraint negatively — *"Never delegated to the gateway alone"*, *"Enforces authorization locally against ABAC attributes, never relying solely on the gateway"* — and a negative constraint is unfalsifiable unless the exceptions are enumerated.

**The gateway makes exactly two authorization-adjacent decisions, both enumerated, both defense-in-depth, and neither authoritative:**

1. The accountable-autonomous refusal on `state-changing` routes (§5.4).
2. The classification-level fault refusal (§7.2), which is fault detection rather than a policy decision — it refuses to *carry* an over-level fragment; it does not decide who may see what.

**Everything else is forwarded.** Specifically, the gateway does not:

- Read or interpret roles, groups, clearance, caveats, compartments, unit, billet, or qualification claims.
- Hold, evaluate, or ship an OPA or Cedar policy. `test_gateway_has_no_policy_engine` asserts neither is a dependency of `platform/gateway/pyproject.toml`.
- Check a principal's `authority_class` against a proposal's `authority_class` or `blast_radius` (§4.6).
- Pre-reject a request the upstream will reject. `test_gateway_forwards_an_authority_violation` asserts the forwarding.
- **Assert any header a sub-application might trust for an authorization decision.** This is the subtlest way a gateway becomes the enforcement point, and the rule is absolute: the gateway adds no `X-Fathom-Clearance`, no `X-Fathom-Roles`, no `X-Fathom-Level`, no `X-Forwarded-User`. Everything a sub-application authorizes on arrives in the validated token, signed by `auth`. `test_gateway_asserts_no_authorization_header` enumerates the headers the gateway adds and asserts the set is exactly `{X-Correlation-Id}` when absent inbound, and nothing else.

The consequence is the property the architecture wants: **the gateway is not a single point of authorization failure, because it is not a point of authorization at all.** If it were bypassed entirely — a direct in-cluster call to a sub-application — nothing about authorization would change. That is the test of whether obligation 7 is really satisfied, and it is satisfied here.

### 5.8 Audit

Document 03 §8.5: *"Tool invocations, with full request and response, are recorded to Audit & Provenance and correlated to the Domino trace by `trace_ref`."* Document 04 §11 makes `audit` the immutable record of *"agent tool invocations with full request and response."*

| Recorded | Content |
|---|---|
| Every agent tool call through the pass-through surface | `principal_id` (`sub`), the full nested `act` chain, `fathom.agent.agent_version` (carried on `act.fathom.agent_version`), `fathom.agent.llm_version`, `fathom.agent.manifest`, `trace_ref`, `correlation_id`, method, resolved upstream operation, request and response bodies, status, `X-Classification`, duration (`time.monotonic()`, per 09 §4.8) |
| Every Domino Endpoint proxy call | §5.6 |
| Every `accountable_autonomous` request | Plus `fathom.accountable_owner` (03 §8.3; 31 §3.3) |
| Every proposal claim and adjudication proxied | Plus `proposal_id`, `target_sub_app`, `If-Match` presence, and the outcome. The owning sub-application also records its own; the gateway's record is the *invocation*, the owner's is the *decision* |
| Human view requests | **Not** recorded to `audit`. They are logged (09 §4.8) with `correlation_id` and `principal_id`. A `GET` of a fleet view is not a tool invocation, and recording every read into the immutable accreditation store at operator-interface volume would flood the artifact 04 §11 describes |

Two mechanics:

- **Delivery is asynchronous with a bounded buffer, except where §5.6 requires it synchronously.** A slow `audit` must not add latency to every tool call; a *full* buffer must not silently drop records. On buffer exhaustion the gateway fails the request (`503 urn:fathom:problem:gateway:audit-unavailable`) rather than proceeding unaudited — the audit trail is an accreditation artifact (04 §11), and an unaudited tool invocation is worse than a failed one.
- **Large bodies are referenced, not inlined**, following D27's pattern for the same reason. The threshold and the object-store destination are **`audit`'s to set**; this document does not invent a number (09 DO-NOT 31) and records the dependency as OQ-2, alongside 11 OQ-10's related question about `audit` accepting a per-event `sync_quality` attestation at full event volume.

---

## 6. Rate limiting

Document 03 §4: *"Rate limiting — Per-caller-identity token bucket at the gateway; per-sub-application limits declared in its chart."* Both halves are required, and they protect different things.

### 6.1 Two tiers, and what each is for

| Tier | Keyed on | Protects against |
|---|---|---|
| **Per caller identity** | The principal, per §6.2 | One caller — overwhelmingly, one looping agent — consuming the ingress |
| **Per target sub-application** | `target_sub_app` | A sub-application being overwhelmed by the *aggregate* of many callers, which no per-caller bucket can bound |

Neither is a billing meter. Both are availability guards, and that framing settles the accuracy question in §6.3.

### 6.2 The per-caller bucket key

The key is not simply `sub`, and the reason is 03 §8.3's two authority classes:

| Caller | Bucket key | Why |
|---|---|---|
| Human, direct | `("user", sub)` | |
| Agent, delegated (§5.3) | `("delegated", sub, act.sub)` — **the user *and* the agent** | A looping agent acting for a maintainer must not consume the maintainer's own interactive budget. Separate buckets mean the human's fleet view still loads while their copilot is being throttled |
| Agent, accountable autonomous (§5.4) | `("autonomous", sub, accountable_owner)` | The owner is in the key so a per-owner budget is expressible, per 03 §8.3's accountability requirement |
| Workload — Domino scoring Jobs, practitioner Apps | `("workload", sub)` | 09 §4.4.2's `domino-compute → gateway` edge. Batch ingest is bursty by design and gets its own declared limit |

Unauthenticated requests are rejected at §5.1 before any bucket is consulted, so there is no anonymous bucket and no anonymous-flood surface. `/healthz`, `/readyz`, and `/metrics` are exempt — a rate-limited readiness probe produces a restart storm.

### 6.3 The algorithm and where the state lives

```python
# platform/gateway/src/fathom_gateway/ratelimit/bucket.py
import time
from dataclasses import dataclass


@dataclass(slots=True)
class TokenBucket:
    """Token bucket with MONOTONIC refill.  [D29 · 03 §5.4 · 11 §11.5 gate 5]

    A wall-clock refill is a defect, not a style choice.  Ubuntu 22.04 STIG rule
    V-260520 mandates `makestep 1 -1` — unlimited backward steps whenever the
    offset exceeds one second.  With a wall-clock refill:
      * a BACKWARD step makes `now - last` negative, so the bucket never refills
        and every caller is throttled until the clock catches up;
      * a FORWARD step grants every bucket a windfall proportional to the step,
        which is a rate-limit bypass triggered by NTP.
    Neither is theoretical: the step fires precisely when a node resynchronizes.
    """

    rate_per_second: float
    burst: float
    tokens: float
    last_mono: float

    def take(self, n: float = 1.0) -> bool:
        now = time.monotonic()
        self.tokens = min(self.burst, self.tokens + (now - self.last_mono) * self.rate_per_second)
        self.last_mono = now
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    def retry_after_seconds(self, n: float = 1.0) -> int:
        """Integer seconds for the Retry-After header, derived from the monotonic
        refill rate.  Ceiling, never zero — a Retry-After of 0 invites an
        immediate retry that will also fail."""
        deficit = max(0.0, n - self.tokens)
        return max(1, int(deficit / self.rate_per_second) + 1)
```

> **DECISION G-5.** Buckets are held **in-process, per replica**, with the effective per-replica rate computed as `declared_rate / autoscaling.minReplicas`. There is no shared limiter store.

The reasoning, stated with its cost:

- **There is no shared cache in the 01 §11 inventory.** 09 §5.3 makes exactly this argument when placing idempotency records in the service's own database rather than in Redis. Adding Redis for rate limiting is a new infrastructure component, a change to 09 §2, an addition to the air-gap mirroring surface, and a new dependency on the request path of every call into the system.
- **The gateway's own database is the wrong store.** A per-request read-modify-write against PostgreSQL on the hottest path in the system, to enforce an availability guard, trades the thing being protected for the protection.
- **Sizing against `minReplicas` fails safe.** At `minReplicas` the aggregate limit is exact. Scaled to `maxReplicas` it is over-permissive by at most `maxReplicas / minReplicas` — 3× at 09 §4.4.1's default 2/6. Over-permissive when scaled up is the correct direction: the gateway scales up because load is high, and throttling more aggressively at that moment is how a load spike becomes an outage. The inverse error — under-permissive when scaled down — cannot occur.
- **Approximate is sufficient because the target is protection, not accounting.** 06 §7's envelope is 12 assets, fewer than 20 agent proposals per day, and a p95 budget of 1.5 s. The failure this guard exists for is an agent loop issuing thousands of calls a minute, and a 3× uncertainty in the threshold does not change whether that is caught.

The alternative — a shared limiter store for exactness — is recorded as OQ-5 rather than dismissed, because it becomes the right answer at production scale.

**Per-sub-application limits come from each sub-application's own chart**, per 03 §4, and reach the gateway declaratively:

```yaml
# each sub-application's helm/values.yaml — an addition to 09 §4.4.1's mandatory shape,
# flagged at §14 item 4 because 09 §4.4.1 does not currently carry these keys
rateLimit:
  requestsPerSecond: 50
  burst: 100
  maxConcurrent: 32          # the §3.4 bulkhead for this upstream
```

The `fathom-sustainment` umbrella chart renders these into one ConfigMap, `gateway-upstream-limits`, mounted by the gateway. There is exactly one source of truth — the sub-application's own chart — and **no runtime discovery call**: a gateway that queried each sub-application for its limit would have a startup dependency on all nine. CI asserts the ConfigMap's slug set equals the nine plus the reachable platform services, so a new sub-application without a declared limit fails the release rather than defaulting to unlimited.

### 6.4 Concurrency, which matters more than rate

A rate limit bounds requests per second; it does not bound *in-flight work*. Ten slow requests per second against a 5 s upstream is 50 concurrent connections from a limit of 10/s. The `maxConcurrent` bulkhead of §3.4 is therefore the primary protection and the rate limit is secondary, and both are declared per upstream in the same block above.

### 6.5 Responses and metrics

| Situation | Response |
|---|---|
| Per-caller bucket exhausted | `429` RFC 9457 `urn:fathom:problem:gateway:rate-limit-exceeded`, `Retry-After: <integer seconds>` |
| Per-sub-application bucket exhausted | `429` `urn:fathom:problem:gateway:upstream-rate-limit-exceeded`, naming the upstream slug |
| Bulkhead saturated or circuit open | `503`/`UNAVAILABLE` per §3.4 — a capacity condition on the upstream, not a limit on the caller |

Two rules that are easy to get wrong:

- **`429` is never `503`.** They are different facts: `429` says *you* are asking too fast, `503` says the *system* cannot serve you. Conflating them makes a client's retry strategy wrong in both directions.
- **A `429` is never recorded as an idempotent outcome.** 09 §5.3's middleware persists `(key, request_hash, status, body)` on execution; a rate-limited request did not execute, and storing the `429` would make the key permanently replay a `429` and the caller's legitimate retry impossible. The limiter therefore runs **before** the idempotency middleware writes anything, and `test_ratelimit_does_not_poison_idempotency_key` asserts a throttled request followed by a retry with the same key executes normally.

Metrics, following 09 §5.6's naming:

```
fathom_gateway_ratelimit_rejections_total{tier,principal_class,target_sub_app}
fathom_gateway_bucket_tokens{tier,principal_class}             # gauge, sampled
fathom_gateway_inflight{upstream}                              # gauge, the bulkhead
fathom_gateway_circuit_state{upstream}                         # 0 closed, 1 half-open, 2 open
fathom_gateway_clock_step_total                                # §5.2
```

---

## 7. Classification handling

The requirement is precise and easy to over-satisfy into a defect. Document 03 §4 requires `X-Classification` on responses; 03 §7.3 and principle 7 require labels to travel and derived values to carry the union of inputs; obligation 7 and 03 §4 require **enforcement at the receiving sub-application, never the gateway alone**; D13 establishes that consumer-side enforcement alone yields system-high or a leak; and DO-NOT 22 (09 §9.4) prohibits post-filtering because *"removing results afterward leaks the existence of records."*

The gateway therefore does four things and refuses a fifth.

### 7.1 Segregation is topology (what the gateway *is*)

Per D32-R2 (§2.5): one deployment per classification level and compartment set, each with its own declared level, database, consumer group, Kafka ACL grant, and ingress hostname.

```yaml
# platform/gateway/helm/values.yaml — the gateway-specific block
classification:
  deploymentLevel: U          # 03 §7.3 ClassificationLevel. The DEMONSTRATION value, 03 §12 / 06 §5.
                              # Production renders one release per level; see build 30 §2.5.
  compartments: []            # empty for the demonstration
  failClosed: true            # NEVER false, in any environment. §7.2
```

This is the whole of the gateway's classification *architecture*: a property of the deployment graph, not a runtime decision, so there is no code path to bypass and no policy to misconfigure. The Kafka ACL denies even `describe` above the declared level (§4.2), so the leak of §2.5 item 3 is closed by the broker rather than by the application.

The demonstration's posture is **stated, not implied** (03 §12, 06 §5): one deployment, level `U`, single-level unclassified synthetic data. `test_demo_posture_is_single_level_by_configuration` asserts the value is read from configuration and that no default exists — a missing `deploymentLevel` fails startup (09 §4.5: no defaults for anything environment-specific).

### 7.2 Fault detection, not filtering (what the gateway *does*)

An over-level fragment or event is an **upstream defect**, and the gateway's response to it is the crux of not becoming the enforcement point.

| Response | Assessment |
|---|---|
| Filter it out and return the rest | **Prohibited.** This is post-filtering (D13, DO-NOT 22), and it makes the gateway the classification enforcement point — the exact single-point-of-failure the requirement forbids |
| Redact fields and return the rest | **Prohibited.** Per-field redaction is a `canonical-schemas` serializer concern in the *owning* service (09 §5.5), not a gateway transformation |
| Refuse, alarm, and fail closed | **Required** |

Concretely:

- A fragment response whose `X-Classification` union exceeds `deploymentLevel`, or names a compartment outside `compartments`, yields `FragmentOutcome.CLASSIFICATION_FAULT` → `502 urn:fathom:problem:gateway:classification-fault` for the whole view (§3.4). Not a degraded view: an upstream that returned over-level content is an upstream whose *other* fields cannot be trusted either.
- A projected event above `deploymentLevel` — which should be impossible, since the ACL denies the topic — is quarantined in the inbox with `processed_at` NULL, never projected, and alarmed.
- Both increment `fathom_gateway_classification_faults_total{source,upstream,level}` and log at ERROR with the source, the observed level, and the deployment level. A classification fault is a security event and is alertable, not a metric someone might notice.

The distinction to hold onto: **filtering is enforcement; refusing and alarming is fault detection.** The first makes the gateway responsible for a decision it must not own. The second detects that someone else's decision failed, which is what a component in the path should do.

`failClosed: true` is not overridable. There is no configuration in which an over-level response is returned with a warning.

### 7.3 Propagation (what the gateway *carries*)

- **Pass-through:** the upstream's `X-Classification` is forwarded verbatim. Unmodified, unmerged, unaugmented.
- **Composed views:** `X-Classification` is the union of the contributing fragments' labels, computed with `ClassificationLabel.union(*labels, derived_from=…)` from `packages/canonical-schemas` (10 §4.8) — the shared implementation, so the union rule cannot be implemented differently here than in the nine. `inherited_from` accumulates the fragment label references, per 03 §7.3 and obligation 4.
- **The union is never persisted and never published.** It is a response header on one response. This is property 4 of §2.3: the gateway does not manufacture union-classified facts, because it stores none and emits none.
- **Queue responses:** labelled at `deploymentLevel`, with `queue_freshness.completeness: "level_scoped"` (§4.5) so the response declares what it is scoped to. This implements 06 §5 rule 3 — *"A low-side rollup never presents itself as complete"* — for the queue.
- **`_most_restrictive_statement` may raise.** 10 §4.8 records that `REL TO` is not ordinally comparable with the lettered DoDI 5230.24 statements, so a union containing both raises rather than guessing. In the gateway that surfaces as a `502 classification-fault` with a distinct `detail`: a view whose fragments carry incomparable distribution statements requires an explicit determination by the classification authority (10 OQ-16) and is not something a composition layer may resolve.

### 7.4 The refusal: no cross-level anything

The gateway is **not** an accredited guard, and 03 §5.1 and §12 permit cross-level flow only through one. Therefore:

- No cross-level view, no cross-level queue, no cross-level count, no cross-level token, no cross-level correlation.
- No aggregate spanning levels — including admission-control depth (§4.8, §2.5 item 4). Document 03 §7.3: *"Aggregation is a classification event."*
- No "show me everything I'm cleared for across levels" surface. A user cleared for two levels uses two hostnames (§2.5, and its recorded cost at OQ-4).

`test_no_cross_level_read_path` asserts the gateway holds credentials for exactly one database, one consumer group, and one ACL grant, and that no configuration key accepts more than one level.

### 7.5 Production, and what changes

| Property | Demonstration (03 §12, 06 §5) | Production (03 §12, 06 §5) | Change required |
|---|---|---|---|
| Levels | One, `U` | One deployment per level and compartment set | **Helm values only.** No code |
| Topics subscribed | Ten, at `U` | Ten per level, enumerated per deployment | `SubAppSlug` × the deployment's level, plus `audit`'s exception topic; the enumeration mechanism is unchanged |
| Read-model content | Metadata at `U` | Metadata at one level per store | Unchanged |
| Cross-level flow | None | None — an accredited guard, which is not the gateway | Unchanged |
| Aggregation | `level_scoped` | `level_scoped` | Unchanged |

That the "change required" column is almost empty is the point of §2.5, and it is the specific sense in which the gateway is *designed* not to become system-high rather than merely *not yet* system-high.

---

## 8. API surface

### 8.1 Two surfaces at one ingress

| Surface | Paths | Nature |
|---|---|---|
| **Pass-through** | `/api/v1/{slug}/…` for the nine sub-applications plus `tool-server`, `knowledge-retrieval`, `notification`, `reference-data`, and `auth`'s two advisory-only operations (`POST /authority-checks`, `GET /principals/{sub}`) | The upstream's own contract, proxied. The gateway adds authentication, rate limiting, correlation, and audit; it changes nothing else. **[amendment, closes `52-practitioner-apps.md` §13 correction 6, blocking]** `auth` was previously entirely absent from the pass-through set, so `31-auth.md` §8's two browser-facing advisory operations were unreachable from any browser client — `apps/web` included. Both remain non-authoritative (§8.1.2's identity operation is the one that matters for presentation logic); this addition only lets a client *ask* before it acts, per `31-auth.md` §8's own stated purpose |
| **Gateway-owned** | `/api/v1/gateway/…` | The queue (§4.5), the composed views (§3.2), the Domino Endpoint proxy (§5.6), the agent-invocation surface (§8.1.1, **[AMENDMENT]**), session identity and sign-out (§8.1.2, **[AMENDMENT]**), health |

The pass-through surface is why 03 §4 requires slug-namespaced base paths: *"This prevents collision at the single gateway ingress `[C25]`."* C25 records three sub-applications defining operations under `/assets/{id}` with no namespacing; the convention is what makes one ingress possible, and the gateway is the component that would break without it.

**There is no separate "agent API" for *tool calls*.** Agents call the same pass-through paths as humans, differing only in the credential (§5.3). This is 01 §8.0's *"the sub-application APIs **are** the tool surface"* made true at runtime rather than asserted: had the gateway exposed an agent-specific surface for reaching a sub-application, tool manifests would be written against the gateway rather than against sub-application contracts, and 01 §8.0's substitution-safety-equals-tool-safety property would be lost. **This does not extend to *starting* an agent turn or run** — that act has no sub-application to be a pass-through to, and §8.1.1 is where it lives.

#### 8.1.1 Agent invocation — the operation this document was missing

**[AMENDMENT — closes a BLOCKING gap.]** `31-auth.md` §4.1 step 2 is *"Human starts an agent turn"* and step 5 is *"gateway ── invoke agent, passing the delegated token ──▶ agent runtime"*; §5.3 above (as amended) has the gateway calling `POST /api/v1/auth/delegations` and then invoking the runtime. Until this amendment, nothing in this document — not §8.1's surface table, not a problem type, not an operation — gave that act a route. `apps/web` had nothing to call. Flagged independently by `40-copilot.md` §16 correction 16 (marked **R10**, "blocks the demonstration end-to-end") and `42-redesign-case-builder.md` §18 item 9(b); the two agents converged on different SHAPES of the same missing surface, because they are invoked differently, and both are specified below.

**Shape 1 — interactive, turn-based** (the Maintainer Copilot's shape; `40-copilot.md` §9.2's proposal, adopted verbatim):

| Operation | `x-side-effects` | `x-substitution` | `x-agent-eligible` | Notes |
|---|---|---|---|---|
| `POST /api/v1/gateway/agent-sessions` | `state-changing` | `internal` | **false** | Body `{agent_id, subject_hint?}`. Opens a session; returns `session_id`. `Idempotency-Key` required |
| `POST /api/v1/gateway/agent-sessions/{session_id}/turns` | `state-changing` | `internal` | **false** | Body `{question}`. Issues the delegation (§5.3 step 3), invokes the runtime, returns the `GroundedAnswer` or a refusal. `Idempotency-Key` required |
| `GET /api/v1/gateway/agent-sessions/{session_id}` | `none` | `internal` | **false** | Session and turn history for the calling human **only** |
| `DELETE /api/v1/gateway/agent-sessions/{session_id}` | `state-changing` | `internal` | **false** | Explicit close; terminates any live delegation |

**Shape 2 — asynchronous, job-based** (the Redesign Case Builder's shape; `42-redesign-case-builder.md` §13.4's interim surface, promoted from that document's runtime-owned dispatcher to a gateway-owned contract, since a gateway-owned surface is what both correction sets actually asked for):

| Operation | `x-side-effects` | `x-substitution` | `x-agent-eligible` | Notes |
|---|---|---|---|---|
| `POST /api/v1/gateway/agent-invocations` | `state-changing` | `internal` | **false** | Body `{agent_id, invocation, candidate_id?, session_id?, case_id?}`. `Idempotency-Key` required. `202 Accepted`, `Location: /api/v1/gateway/agent-runs/{run_id}` |
| `GET /api/v1/gateway/agent-runs/{run_id}` | `none` | `internal` | **false** | Polled result |

**Three annotations are load-bearing on every row above, in both shapes, and are the reason this cannot be waved through as "the UI will figure it out":**

- **`x-agent-eligible: false` on every row.** Per §8.3's existing rule that it is *"`false` everywhere on the gateway's own surface."* An agent able to invoke an agent is a recursion with no authority boundary — worse, a *delegated* agent invoking another delegated agent would pass a human's authority through a component that never saw the human.
- **`x-side-effects: state-changing` on every `POST`.** A turn or a run is not a computational `POST` — it mints a delegation or a grant, writes runtime-store rows, and produces audit records. Declaring it `none` to make it agent-eligible would be exactly the "correct in form and false in substance" mis-declaration `24-scheduling.md` §9.2 rejects.
- **`Idempotency-Key` required on every `POST`**, per 01 §9's *"agent invocation is idempotency-keyed"* and 09 §5.3.

**Which agent uses which shape is not a free choice per runtime** — it follows from whether the interaction is a bounded conversational exchange (shape 1) or a long-running assembly with no single human waiting synchronously (shape 2). `41-pma-prescreener.md`'s enterprise path uses **neither**: it is `accountable_autonomous` and event-triggered through its own run-initiator (§5.4 below; that document's §2.2), never invoked by the gateway on a human's behalf, so it has no row here.

#### 8.1.2 Session identity and sign-out — the operations `apps/web` needs and none of this document declared

**[AMENDMENT — closes a BLOCKING gap.]** `31-auth.md` §4.1 step 1 establishes the BFF shape (*"the user's access token never leaves the server. `apps/web` holds a session cookie"*), which means `apps/web` cannot read the user's roles from a token it never has — yet §8.1.1's shape-1 flow, the Persona Hub, and the queue's client-side `authority_class` filter (OQ-9, corrected above) all need those roles somewhere in the browser. Nothing in this document exposed them, and nothing anywhere specifies a sign-out. Flagged by `50-ui-design-system.md` §13 correction 7.

| Operation | `x-side-effects` | `x-substitution` | `x-agent-eligible` | Notes |
|---|---|---|---|---|
| `GET /api/v1/gateway/session` | `none` | `internal` | **false** | Returns the session's identity block (`fathom.identity`, byte-identical to §3.2's token shape) and its six `authority_classes`, read from the session cookie's server-side session store — never from a token the browser holds, because it holds none. `404` if no session. **[amendment, closes `52-practitioner-apps.md` §13 correction 3]** `apps/practitioner`'s co-resident host calls this operation exactly as `apps/web` does, with its own `fathom`-realm delegated token obtained from `31-auth.md` §5.8's `POST /api/v1/auth/practitioner-exchange` — **no caller-authority-borne variant is needed**; §5.8 was corrected to eliminate the second credential shape rather than add a second code path here |
| `POST /api/v1/gateway/session/logout` | `state-changing` | `internal` | **false** | Destroys the server-side session and its cookie. **RP-initiated logout** at the identity provider is triggered server-side in the same call, per `31-auth.md` §2's Keycloak binding — there is no client-side `end_session_endpoint` redirect, because the browser holds no `id_token` to present to one. Not applicable to `apps/practitioner`, which has no session cookie to destroy (§4.7 of `52-practitioner-apps.md`) |

**The session store and cookie, stated because §1.3 of `31-auth.md` deferred them to this wave:** an opaque session identifier in a cookie named **`fathom_session`** — `HttpOnly`, `Secure`, `SameSite=Lax` — keyed against a server-side store (Redis, TTL-bound to the underlying token's remaining life) holding the actual tokens. CSRF: `SameSite=Lax` plus a double-submit token, cookie **`fathom_csrf`** (readable by JavaScript, unlike the session cookie) echoed on header **`X-Fathom-CSRF`**, required and matched on every state-changing gateway-owned operation, checked in the middleware order of §8.6 immediately after authentication. **[amendment, closes `51-operator-console.md` UI-OQ-1]** Neither name was previously stated; both are needed before a console can construct the header.

### 8.2 How pass-through routes are constructed

> **DECISION G-3.** Pass-through routes are **generated at startup** from the nine committed `openapi.json` documents (plus the reachable platform services'), delivered as a ConfigMap rendered by the umbrella chart from `packages/contracts/openapi/<slug>/`. Each generated route **inherits `x-side-effects`, `x-substitution`, and `x-agent-eligible` verbatim** from the upstream operation. There is no catch-all proxy route.

Four things depend on this, and a dynamic catch-all breaks all four:

1. **09 §5.3's idempotency middleware "reads `x-side-effects` off the matched route."** A catch-all has no side-effect class, so the middleware cannot decide whether `Idempotency-Key` is required, and 03 §4's requirement — mandatory *"for any operation reachable from an agent proposal, a bulk write, or an edge sync"* — becomes unenforceable at the ingress.
2. **§5.4's accountable-autonomous refusal needs the class statically.** Deciding it from the upstream's response is deciding it after the state change.
3. **An undeclared operation is unreachable.** An unknown path `404`s at the gateway rather than being blindly forwarded. The ingress surface is exactly the union of nine reviewed, committed contracts — a security property, not only a tidiness one.
4. **The merged document is a reviewable artifact.** `platform/gateway/openapi.json` is generated and committed like every other service's (09 §2.5), and CI fails on drift — so a change to any sub-application's surface shows up as a diff in the ingress.

The cost, stated: a new upstream operation is not reachable until the ConfigMap is updated and the gateway restarts. Because the specs come from the already-published `packages/contracts/openapi/<slug>/` and Argo CD already syncs the umbrella chart (09 §6.3), that is a chart value bump, **not an image rebuild** — which is why the ConfigMap is preferred over baking the specs into the image. The rejected alternative (runtime spec fetch from each upstream) adds a startup dependency on all nine and makes the ingress surface vary by fetch timing.

### 8.3 Annotations on gateway-owned operations

| Annotation | Value | Reason |
|---|---|---|
| `x-substitution` | `internal` on **every** gateway operation | 03 §4.1's annotation governs whether a *substituting sub-application implementation* must provide the operation (03 §10). The substitution protocol covers the nine disciplines; no partner assumes the gateway. Declared rather than omitted, because 09 §8.1 requires the annotation on every operation |
| `x-side-effects` | `none` on reads and views; `state-changing` on `claim`, `adjudicate`, and the pass-through of upstream state-changing operations; `none` on the Domino Endpoint proxy | 03 §4.1 |
| `x-agent-eligible` | **`false` everywhere on the gateway's own surface** | §4.5's closing paragraph. Agents obtain state through sub-application tools (03 §6, C19); the queue is not a domain, and an agent reading adjudication outcomes is an unadjudicated feedback channel (D23) |
| `x-naming-carve-outs` | `/proposals/summary`, `/views/*`, `/inference/{name}` | 03 §4's singleton and query-projection carve-out, which must be *enumerated in the specification* (C23, 09 §8.1) |

### 8.4 Pass-through transparency, as a contract

The gateway is a proxy, and a proxy that changes things is a source of defects nobody can locate. The transparency rules are contract terms, tested in §10.2.

| Direction | Rule |
|---|---|
| Request → upstream | `Authorization` **never replaced on the agent path** (§5.3) — the delegation token forwards unchanged from invocation to every tool call. `Idempotency-Key`, `If-Match`, `If-None-Match`, `X-Backfill`, `Content-Type`, `Accept`, and query parameters forwarded verbatim. `X-Correlation-Id` forwarded, or minted if absent (09 §5.5) |
| Request → upstream | **Added:** nothing except `X-Correlation-Id` when absent. Explicitly **not** added: any header a sub-application might authorize on (§5.7) |
| Request → upstream | **Dropped:** the human's original browser-session cookie (never forwarded past the BFF boundary, §5.1), `Host`/hop-by-hop headers. There is no `X-Fathom-Delegation` header to drop — §5.3's amendment removed it along with the second exchange it existed to carry |
| Upstream → response | Status code, `Content-Type`, body **byte-identical**. `ETag`, `Location`, `Retry-After`, `Deprecation`, `Sunset`, `X-Classification`, `Idempotency-Replayed` forwarded verbatim |
| Upstream → response | **Never rewritten:** RFC 9457 problem bodies. An upstream's `urn:fathom:problem:pdm:…` reaches the client unchanged; the gateway does not re-wrap it as a gateway problem. A re-wrapped problem detail destroys the stable-`type` contract 03 §4 establishes |
| Upstream → response | The gateway's **own** problem types are used only for conditions the gateway itself detected — `unauthenticated`, `rate-limit-exceeded`, `owner-unavailable`, `classification-fault`, `required-fragment-unavailable`, `authority-unknown`, `accountable-owner-absent`, `delegated-authority-lapsed`, `autonomous-state-change-refused`, `cursor-generation-stale`, `audit-unavailable`, and the two `Idempotency-Key` conditions of 09 §5.3. **`delegation-actor-mismatch` is retired** — it existed only to catch a mismatch between the two credentials §5.3's superseded two-hop model presented; with one forwarded token there is nothing to compare |

`ETag` forwarding is load-bearing for D16: 03 §7.2 rule 3 requires adjudication to carry `If-Match` on the *claimed* ETag. A gateway that regenerated ETags would break the claim mechanism while appearing to work — the same defect as synthesizing `If-Match` (§4.6), from the other end.

### 8.5 Problem types

All under `urn:fathom:problem:gateway:<code>`, declared in `schemas/problems.py` and present in the spec's `responses` (09 §8.1). The `type` URI is a URN, never an `https://` URL — 09 DO-NOT 26 prohibits a dereferenceable problem type, because someone will dereference it and the gateway may not reach the public internet.

### 8.6 Middleware order

Fixed by 09 §5.7 and extended here. Registered in `create_app` in this order:

| # | Middleware | From | Note |
|---|---|---|---|
| 1 | Correlation | 09 §5.5 | Outermost, so every layer including the error handler has a correlation ID |
| 2 | Problem handlers | 09 §5.2 | RFC 9457 for anything raised deeper |
| 3 | Classification | 09 §5.5, §7.3 | Sets `X-Classification` on the way out |
| 4 | **Authentication** | §5.1 — **gateway-specific** | After correlation so a `401` is correlated; before rate limiting so the bucket key exists |
| 5 | **Rate limiting** | §6 — **gateway-specific** | After authentication (needs the principal), **before** idempotency (§6.5's poisoning rule) |
| 6 | Idempotency | 09 §5.3 | After routing has matched, so it can read `x-side-effects` (decision G-3) |
| — | Authorization | — | **Absent.** 09 §5.5 makes it a per-operation dependency in the *receiving* service. The gateway has none. §5.7 |

Positions 4 and 5 are additions to 09 §5.7's list, which does not contemplate a service that authenticates on behalf of an ingress. Flagged at §14 item 5.

---

## 9. Events

### 9.1 Consumed

| Topic | Event types | Payload | Source |
|---|---|---|---|
| `fathom.registry.proposal.v1` | `proposal.created`, `proposal.adjudicated`, `proposal.expired` | `Proposal` (03 §7.2) | 03 §6 |
| `fathom.telemetry.proposal.v1` | " | " | " |
| `fathom.pdm.proposal.v1` | " | " | " |
| `fathom.fleet-status.proposal.v1` | " | " | " |
| `fathom.maintenance.proposal.v1` | " | " | " |
| `fathom.supply.proposal.v1` | " | " | " |
| `fathom.pma.proposal.v1` | " | " | " |
| `fathom.failure-intel.proposal.v1` | " | " | " |
| `fathom.design-advisory.proposal.v1` | " | " | " |

Nine topics, enumerated (§4.1), confined to the deployment's classification level (§7.1). Consumer group `fathom-gateway-v1` (09 §7.1).

**Two notes on the catalog, both flagged at §14:** 03 §6 does not list `gateway` as a consumer of `proposal.adjudicated`, which the queue requires or approved proposals remain pending forever (§14 item 1). And a sub-application that accepts no agent proposals publishes no proposal topic; 03 §6's convention says *"every sub-application accepting agent proposals"*, and 03 §7.2's six `kind` values map to fewer than nine owners. The gateway subscribes to all nine anyway — a subscription to a topic with no messages is inert, whereas an enumeration that varies by which sub-applications happen to accept proposals would need maintaining in two places and would silently miss a sub-application that started accepting them. `test_subscription_tolerates_empty_topic` covers it.

### 9.2 Published: none

```
PUBLISHES: frozenset()
```

The gateway owns no aggregate and effects no state change through its own contract. Claim and adjudicate are the owning sub-application's state changes, announced on the owner's own proposal topic. So:

- **03 §15 obligation 2** — *"emits an event for every state change reachable through its contract"* — is satisfied **vacuously**, and §13 records it as such rather than as unmet.
- **There is no `outbox` table.** 11 §1.1 scopes the outbox writer and relay to *"every program-built service that **publishes any event**."* The gateway publishes none. This is consistent with 03 §15 obligation 11's *"without exception, including sub-applications with no current edge profile"*, because that clause closes the gap of a service that *will* publish later; a service that publishes nothing has no state change to make atomic with a publication.
- **The clock discipline module is still required** — 11 §1.1 marks it *"Every service"* — because the projector reads `clock.monotonic_seq`, `producer_node`, and `sync_quality` off consumed envelopes (§4.3).
- **The inbox is required in full** (03 §15 obligation 12, 11 §3).

If the gateway ever needs to publish, it acquires the outbox first and this section changes. `test_d32_gateway_publishes_nothing` asserts `PUBLISHES` is empty, that no `outbox` table exists in the migration head, and that no Kafka *producer* is constructed anywhere in the service — the last being 11 §11.5's static gate 2 applied to a service that has no relay to exempt.

### 9.3 Read models

One: `proposal_queue` (§2.4). Rebuilt from `changed_since` reads, never from the event bus (03 §5.1, D5, §4.7).

The gateway holds **no other read model of any kind**. That sentence is the operative half of the D32 resolution, and §10.1's tests are what keep it true.

---

## 10. Testing

Four tiers per 09 §4.7 — unit, integration, contract, conformance — plus the D32 suite, which is the reason this document exists and is therefore listed first.

### 10.1 The D32 suite

`platform/gateway/tests/contract/test_d32_resolution.py` and `tests/integration/test_d32_projection.py`. Every test name begins `test_d32_` so a reviewer can run the finding.

| Test | Asserts | Property (§2.6) |
|---|---|---|
| `test_d32_read_model_column_allowlist` | `proposal_queue`'s actual column set **equals** `PROJECTED_COLUMNS`, in both directions. Reads `Base.metadata`, so adding a column fails | 1 |
| `test_d32_forbidden_fields_absent_from_all_models` | Walks **every** table in `Base.metadata` and asserts no column name matches `FORBIDDEN_FIELDS`. Catches a future table reintroducing payload storage by another route | 1 |
| `test_d32_projection_discards_payload_from_the_wire` | **The strong test.** Publishes a real `Proposal` whose `payload` contains `CANARY-PAYLOAD-<uuid>` and whose `evidence[0].excerpt` contains `CANARY-EXCERPT-<uuid>`, through a real Redpanda into a real PostgreSQL via testcontainers (09 §2.2); then scans **every** `text`, `varchar`, `jsonb`, and `json` column in **every** table of the gateway database and asserts neither canary appears. Constrains the store, not the code path | 2 |
| `test_d32_queue_response_contains_no_free_text` | The `GET /proposals` response body, for a proposal with a long rationale and excerpts, contains no field whose value is unbounded free text — the injection-surface half of property 1 (§2.3, D14) | 1, 2 |
| `test_d32_subscription_confined_to_declared_level` | With proposal topics registered at two levels, `deploymentLevel=U`: the subscription set equals the enumerated `U` list; a proposal published on an above-level topic is **never** projected and appears in **no** queue response | 3 |
| `test_d32_no_broker_pattern_subscription` | No argument passed to `Consumer.subscribe()` begins with `^` (§4.2) | 3 |
| `test_g1_enumerated_list_equals_pattern_expansion` | `CONSUMES` equals `PROPOSAL_TOPIC_PATTERN` expanded over `SubAppSlug` plus `AUDIT_PROPOSAL_TOPIC`, and has ten members (§4.2) | 3 |
| `test_d32_read_model_rebuild_with_bus_down` | Project N proposals; snapshot; `TRUNCATE proposal_queue`; **stop Redpanda**; rebuild from `changed_since` against stub owners; assert the result is identical to the snapshot modulo `projection_seq` | 4 |
| `test_d32_purge_is_truncate_and_rebuild` | The declared purge procedure of §4.7 executes end to end and leaves no trace of the purged `proposal_id` in any column of any table | 4 |
| `test_d32_gateway_publishes_nothing` | `PUBLISHES == frozenset()`; no `outbox` table at migration head; no Kafka producer constructed anywhere in the service | 5 |
| `test_d32_stale_projection_cannot_cause_a_wrong_adjudication` | Poison a row (`baseline_epoch` low, `status='proposed'`, `authority_class` wrong, `valid_until` future), then adjudicate through the gateway against a stub owner enforcing 03 §7.2's re-validation; assert the owner rejects and the gateway forwards the rejection unaltered | 5 |
| `test_d32_no_domain_readmodel_other_than_the_queue` | The migration head's table set equals exactly `{proposal_queue, inbox, idempotency_keys, queue_rebuild_watermark, alembic_version}` | 5 |
| `test_no_cross_level_read_path` | Exactly one database credential, one consumer group, one ACL grant; no configuration key accepts more than one level (§7.4) | 3 |

The last of these is the guard with the longest reach: it makes "the gateway holds no other read model" a CI failure rather than a code-review judgement, so a future agent adding an innocuous-looking `asset_cache` table to fix a latency problem trips D32 immediately.

### 10.2 The no-chained-calls and composition suite

| Test | Asserts |
|---|---|
| `test_fanout_is_concurrent_not_sequential` | Instruments the shared httpx factory; for each view, records each upstream call's monotonic start and end; asserts that within a phase **every** call starts before the **earliest** completion of any other. A sequential chain fails this deterministically |
| `test_view_phase_count_bounded_at_two` | Every `ViewSpec` in the registry has `max(f.phase) <= 1` (Rule C2, §3.1) |
| `test_fragment_has_exactly_one_upstream` | Every `Fragment.upstream` is a single slug — Rule C1 as a type invariant |
| `test_partial_failure_is_rendered_not_dropped` | With one upstream stopped: `200`, `degraded: true`, the failed fragment present in `fragments` with outcome `unavailable`, and its key **absent** from `data`. Asserts `empty` and `unavailable` produce different envelopes |
| `test_required_fragment_failure_returns_503_with_no_partial_body` | Stopping `registry` on `asset_detail` yields `503` with the problem type and **no** `data` member |
| `test_forbidden_fragment_does_not_fail_the_view` | An upstream `403` on an optional fragment yields `200 degraded` with outcome `forbidden`, not a `403` for the view |
| `test_read_timeout_is_not_retried` | A slow upstream produces exactly **one** outbound request; a connect failure produces exactly two (§3.3) |
| `test_fragment_deadline_clamped_to_view_deadline` | A phase-1 fragment whose own budget exceeds the view's remaining time is given the remainder, not its budget |
| `test_bulkhead_returns_unavailable_rather_than_queueing` | Saturating `maxConcurrent` returns immediately; latency does not grow past the deadline |
| `test_circuit_opens_and_probes` | Closed → open on the declared failure count within a monotonic window; open short-circuits without a call; half-open admits one probe |
| `test_no_domain_response_is_cached` | Two identical view requests produce two full fan-outs (§3.5) |
| `test_passthrough_is_byte_identical` | Status, `Content-Type`, and body bytes identical for `2xx`, `4xx`, and `5xx`, including an RFC 9457 problem body, which must **not** be re-wrapped (§8.4) |
| `test_passthrough_forwards_etag_and_conditional_headers` | `ETag` out and `If-Match`/`If-None-Match` in survive verbatim |
| `test_gateway_asserts_no_authorization_header` | The set of headers the gateway adds to an upstream request is exactly `{X-Correlation-Id}` when absent inbound (§5.7) |

### 10.3 Authority, rate limiting, and classification

| Test | Asserts |
|---|---|
| `test_delegation_claims` | The single exchange (§5.3) produces `sub = <user>`, `aud` = the manifest's target-slug list, nested `act.sub = svc:agents/<name>`, `scope ⊆ manifest scopes`, `exp ≤ min(300 s, subject remaining)` |
| `test_delegation_forwarded_unchanged` | The same token's byte value reaches every tool-call upstream for the life of the turn; the gateway never re-exchanges, never substitutes, and never adds a second `Authorization`-bearing header |
| `test_delegation_token_never_cached_or_persisted` | No token value appears in the database or in any log line, across the whole turn |
| `test_d12_no_service_identity_fallback` | Across every upstream failure mode on a delegated request, every outbound `Authorization` derives from the inbound delegation, and the gateway's own workload token appears in no upstream request on that path (§5.5) |
| `test_d12_delegated_expiry_terminates` | An expired delegation yields `401 delegated-authority-lapsed`, no `Retry-After`, and no upstream call |
| `test_d12_autonomous_state_change_refused` | `accountable_autonomous` against a `state-changing` route yields `403`, with no upstream call (§5.4) |
| `test_d12_accountable_owner_required` | An autonomous token without `fathom.accountable_owner` yields `403` |
| `test_d12_domino_endpoint_audit_written_before_response` | Killing the process between the Domino call and the response leaves the audit record present; the caller's token never reaches Domino (§5.6) |
| `test_gateway_has_no_policy_engine` | Neither OPA nor Cedar is a dependency of `platform/gateway/pyproject.toml` (§5.7) |
| `test_gateway_forwards_an_authority_violation` | A proposal whose `authority_class` the caller does not hold is **forwarded** and rejected by the owner; the gateway does not pre-reject (§4.6, §5.7) |
| `test_gateway_never_synthesizes_if_match` | Adjudication without `If-Match` yields `428`; no outbound request carries an `If-Match` absent inbound (§4.6, D16) |
| `test_ratelimit_refill_is_monotonic` | Injects a **backward** wall-clock step of an hour mid-test: no windfall, no stall, bucket behaviour unchanged (§6.3, D29) |
| `test_ratelimit_bucket_keys_separate_user_and_agent` | Exhausting a delegated agent's bucket leaves the same user's direct bucket unaffected (§6.2) |
| `test_ratelimit_does_not_poison_idempotency_key` | A throttled request followed by a retry with the same `Idempotency-Key` executes normally (§6.5) |
| `test_upstream_limits_come_from_configmap_not_discovery` | Startup makes no HTTP call to any sub-application; limits load from the mounted ConfigMap (§6.3) |
| `test_classification_fault_fails_closed` | An over-level fragment yields `502 classification-fault`, an ERROR log, and a metric increment — **never** a filtered `200` (§7.2) |
| `test_classification_union_uses_shared_implementation` | A composed view's `X-Classification` equals `ClassificationLabel.union(...)` of its fragments' labels, with `inherited_from` populated; the union is not persisted (§7.3) |
| `test_incomparable_distribution_statements_fault` | Fragments carrying `REL TO` and a lettered statement yield `502 classification-fault`, not a guessed union (§7.3, 10 OQ-16) |
| `test_demo_posture_is_single_level_by_configuration` | `deploymentLevel` has no default; a missing value fails startup (§7.1, 03 §12) |
| `test_queue_response_declares_level_scoped_completeness` | Every list and summary response carries `queue_freshness.classification_level` and `completeness: "level_scoped"` (§4.5, 06 §5 rule 3) |

### 10.4 Conformance

**The gateway's own suite** at `packages/contracts/conformance/gateway/`, collected unmodified per 09 §4.7. It covers the queue contract, the pass-through transparency properties of §8.4, and cursor stability across a rebuild.

**Ten consumer-driven contributions**, at `packages/contracts/conformance/<slug>/consumers/gateway/`. This is a Definition-of-Done obligation, not an optional extra: 09 §4.7 states that *"a consumer that declares a dependency in document 03 §6 and contributes no test has an unmet Definition-of-Done item."* The gateway declares ten — the nine sub-applications plus `audit` (§4.1). Each contribution asserts, against that sub-application's implementation or a substituting partner's:

1. `fathom.<slug>.proposal.v1` exists, carries the full 03 §5.4 envelope with `producer_node` and the complete `clock` block, and partitions per 03 §5.1.
2. A created proposal validates against `packages/canonical-schemas`' `Proposal`, with `authority_class` drawn from 03 §7.2.1's vocabulary and `blast_radius` from 03 §7.2's.
3. `target_sub_app` equals the producing slug — the `proposal_queue_owner_is_producer` invariant (§2.4), which is 03 principle 3 stated as a testable property.
4. `requires_dual_control` is true wherever 03 §7.2 rule 4 mandates it (class or fleet scope, or a kind with external legal effect).
5. `proposal.adjudicated` and `proposal.expired` are published on the same topic, so a projection built from `proposal.created` alone cannot go permanently stale.
6. `GET /proposals?changed_since=&cursor=` exists, is cursor-paginated, and returns the same fields the events carry — the §4.7 rebuild path, and 03 obligation 5 for this aggregate.
7. `POST /proposals/{id}/claim` returns a lease and an `ETag`; adjudication without `If-Match` returns `428`; adjudication on a superseded `baseline_epoch` or an elapsed `valid_until` is **rejected** (03 §7.2 rule 2, D16).

Item 7 deserves emphasis: it is the gateway, as the consumer that serves the queue, that makes D16's re-validation rule externally observable across all ten owners. Without it, "re-validation at approval is mandatory" is an obligation with no test anywhere in the system.

### 10.5 Standard tiers

| Tier | Content |
|---|---|
| **unit** | Bucket refill arithmetic; cursor encode/decode; the projection function's field mapping and allowlist enforcement; precedence comparison on `(producer_slug, producer_node_id, monotonic_seq)`; fragment-outcome classification; deadline clamping |
| **integration** | Real PostgreSQL and real Redpanda via testcontainers (09 §2.2), images mirrored and referenced by digest (09 §2.2's air-gap constraint). The projector end to end; rebuild with the bus down; inbox crash-recovery at each of 11 §11.1's injection points |
| **contract** | 09 §4.7's six files, plus §10.1's schema-level D32 guards and §4.2's subscription assertion. `schemathesis` against the committed merged `openapi.json` |
| **conformance** | §10.4 |
| **load** | The p95 targets of 06 §7 — 1.5 s for fleet and asset views, 4 s for explanation decomposition — asserted against stub upstreams with injected latency distributions. **The tool and thresholds are 09 OQ-8**, which records that 06 §7 *"states a p95 budget … that nothing currently verifies"*; this document inherits that gap rather than inventing a tool (OQ-3) |

---

## 11. Deployment

### 11.1 `values.yaml`

09 §4.4.1's mandatory shape in full, with the gateway-specific additions.

```yaml
slug: gateway
apiMajor: 1

image:
  repository: registry.internal/fathom/gateway
  digest: ""
  tag: ""
  pullPolicy: IfNotPresent
  pullSecrets: [fathom-registry]

# ---- workload: TWO deployments from one chart.  DECISION G-2, §11.2 ---------
api:
  replicaCount: 2
  resources:
    requests: { cpu: 200m, memory: 256Mi }
    limits:   { cpu: "2",  memory: 512Mi }
  autoscaling:
    mode: hpa                      # 09 §2.4: "HPA on request rate for gateway"
    minReplicas: 2                 # the rate-limit divisor, DECISION G-5 (§6.3)
    maxReplicas: 6
    targetRequestsPerSecond: 50

projector:
  replicaCount: 1
  resources:
    requests: { cpu: 100m, memory: 256Mi }
    limits:   { cpu: "1",  memory: 512Mi }
  autoscaling:
    mode: keda                     # 09 §2.4: "KEDA on consumer lag for event workers"
    minReplicas: 1
    maxReplicas: 3                 # never exceeds total partitions across the ten topics
    kedaLagThreshold: 1000

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 65532
  runAsGroup: 65532
  fsGroup: 65532
  seccompProfile: { type: RuntimeDefault }

containerSecurityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities: { drop: ["ALL"] }

nodeSelector:
  fathom.navy/pool: program
tolerations: []
terminationGracePeriodSeconds: 30

probes:
  liveness:  { path: /healthz, initialDelaySeconds: 5, periodSeconds: 10, failureThreshold: 3 }
  readiness: { path: /readyz,  initialDelaySeconds: 3, periodSeconds: 5,  failureThreshold: 3 }

app:
  logLevel: INFO
  config:
    stalenessBoundSeconds: 300      # 09 §4.4.1's declared default, adopted not invented (§4.7)
    corsAllowedOrigins: []          # set per environment to the operator UI origin only

# ---- gateway-specific -------------------------------------------------------
classification:
  deploymentLevel: U                # 03 §7.3 level. DECISION D32-R2 / §7.1. No default in code.
  compartments: []
  failClosed: true                  # NEVER false, in any environment

composition:
  views:                            # budgets from 06 §7 ONLY (§3.2)
    fleet_overview:            { budgetMs: 1500 }
    asset_detail:              { budgetMs: 1500 }
    installed_item_detail:     { budgetMs: 1500 }
    explanation_decomposition: { budgetMs: 4000 }
  connectTimeoutMs: 250
  connectRetries: 1                 # connect failures only; read timeouts are never retried

upstreamLimits:
  configMap: gateway-upstream-limits   # rendered by the umbrella chart from each
                                       # sub-application's own rateLimit block (§6.3)

openapiSpecs:
  configMap: gateway-upstream-specs    # the nine committed openapi.json, DECISION G-3 (§8.2)

auth:
  issuer: ""                        # required; startup fails if absent (09 §4.5)
  jwksUrl: ""
  tokenExchangeUrl: ""              # RFC 8693 grant on auth's token operation (§5.3)
  jwtLeewaySeconds: 60              # FIXED. Not tunable per environment. §5.2

domino:
  inferenceProxyEnabled: true
  endpointTokenSecretRef: fathom-gateway-domino-endpoint   # External Secrets. §5.6

# ---- owned datastore --------------------------------------------------------
database:
  clusterName: fathom-gateway-pg    # exactly one. 03 §15.13
  name: gateway
  secretRef: fathom-gateway-pg-app
  poolSize: 20
  maxOverflow: 10

migrations:
  enabled: true
  backoffLimit: 0

# ---- event bus --------------------------------------------------------------
events:
  brokers: redpanda.fathom-data.svc.cluster.local:9093
  schemaRegistry: http://redpanda.fathom-data.svc.cluster.local:8081
  consumerGroup: fathom-gateway-v1
  publishes: []                     # EMPTY, and correct. §9.2
  consumes:                         # MUST equal events/catalog.py CONSUMES. CI job 6
    - fathom.registry.proposal.v1
    - fathom.telemetry.proposal.v1
    - fathom.pdm.proposal.v1
    - fathom.fleet-status.proposal.v1
    - fathom.maintenance.proposal.v1
    - fathom.supply.proposal.v1
    - fathom.pma.proposal.v1
    - fathom.failure-intel.proposal.v1
    - fathom.design-advisory.proposal.v1
    - fathom.audit.proposal.v1         # [AMENDMENT] the AUDIT_PROPOSAL_TOPIC exception, §4.1 — purge/rewrap

# ---- network boundary (§11.3) ----------------------------------------------
networkPolicy:
  enabled: true                     # NEVER false
  ingress:
    fromServices: []
    fromNamespaces: [ingress-nginx, domino-compute]   # program ingress; batch scoring writes
    allowPrometheusScrape: true
  egress:
    toOwnDatabase: true
    toEventBus: true
    toServices:                     # the gateway's edge set is the broad one, by design
      - registry
      - telemetry
      - pdm
      - fleet-status
      - maintenance
      - supply
      - pma
      - failure-intel
      - design-advisory
      - auth
      - audit
      - reference-data
      - tool-server
      - knowledge-retrieval
      - notification
    toNamespaces: [domino-platform, domino-compute]   # Domino Endpoint proxy, §5.6, §14 item 3
    allowDNS: true
```

### 11.2 Two Deployments, one chart

> **DECISION G-2.** The chart renders two Deployments from one image: `gateway` (HTTP, HPA on request rate) and `gateway-projector` (the proposal consumer, KEDA on consumer lag).

Three reasons, and the third is the one that makes it necessary rather than tidy:

1. **The scaling signals differ and are mutually exclusive in one chart.** 09 §2.4 assigns HPA-on-request-rate to the gateway and KEDA-on-lag to event workers; 09 §4.4.1 carries one `autoscaling.mode` per chart. The gateway is both kinds of workload.
2. **Load isolation.** A request-load spike must not stall queue projection, and a projection backlog must not consume the CPU serving the fleet view.
3. **Consumer group correctness.** If the consumer ran in the API replicas, HPA would add and remove consumer group members in response to *HTTP* load, triggering a partition rebalance on every scale event. Cooperative-sticky assignment reduces the cost but does not remove it, and rebalancing a proposal projection because someone opened a lot of dashboards is a defect. The projector's replica count is bounded by total partitions, and its scaling signal is lag.

Both share one image, one slug, one database, one Alembic history, and one `Settings` class; they differ in an entrypoint flag and in which readiness checks register. §4.7 records the readiness consequence, which is the fourth benefit: projection lag makes the **projector** not-ready without taking the operator interface out of rotation.

Migrations run once, as the chart's `pre-upgrade,pre-install` hook Job with `backoffLimit: 0` (09 §6.3), not from either Deployment.

### 11.3 NetworkPolicy

The gateway's egress set is the widest in the system, and that is the design: 09 §4.4.2's sanctioned edge table lists `gateway → any of the nine, plus tool-server, knowledge-retrieval, notification, and audit` as permitted precisely because *"the gateway performs all view-model composition."* **[AMENDMENT]** `audit` was added to that row — the detail-fetch/adjudicate mechanism (§4.6) needs it for `purge`/`rewrap` rows exactly as it needs the nine for every other kind. The breadth is what buys the nine sub-applications their narrowness — their permitted egress is `[auth, audit, reference-data]` and nothing more.

The helm-unittest assertion mandated by 09 §4.4.2 and 09 §8.6 applies unchanged and is not relaxed for the gateway: the rendered egress peer set must **equal** `values.networkPolicy.egress` exactly, with nothing extra and no wildcard.

Two edges need attention:

- **`domino-compute → gateway` ingress**, for batch scoring writes to PdM's bulk ingest operation. Already sanctioned by 09 §4.4.2 as *"yes, **one rule**"*, with the recorded rationale that routing through the gateway keeps PdM's single ingress and attaches the caller's workload identity in one place. Nothing new.
- **`gateway → domino-platform` / `domino-compute` egress**, for the Domino Endpoint proxy (§5.6) and for invoking Domino-hosted agent runtimes (01 §8.7). **09 §4.4.2's table does not name this edge.** It lists *"program ingress namespace → `domino-*` namespaces"*, which is a different peer. Per 09 §4.4.2's own rule — *"anything not listed requires a change to this document plus an ADR"* — this document requires the edge, requires an ADR, and flags the 09 update at §14 item 3. It must not be added silently: 09 §9.5 item 30 makes an undeclared peer a defect with a finding behind it.

### 11.4 Deployment prerequisites

| Prerequisite | Why | Source |
|---|---|---|
| **Host time synchronization per 03 §5.4** — SC-45/SC-45(1), 1 ms audit granularity, comparison at least daily, 1 s resync threshold | §5.2: JWT `exp`/`nbf` validation is wall-clock by RFC 7519 and has no application-level mitigation for host skew. A gateway on a skewed host mis-validates every token | 03 §5.4, D29 |
| Kafka ACL granting the gateway's principal `read` and `describe` on exactly the ten topics at its declared level, and **denying `describe` above it** | §4.2, §7.1. The ACL, not the application, is what closes the topic-name enumeration leak | 03 §5.1, D13 |
| One CloudNativePG `Cluster` per gateway deployment | 03 §15.13; and under D32-R2 a per-level store means a per-level cluster | 03 §15.13, §2.5 |
| `gateway-upstream-specs` and `gateway-upstream-limits` ConfigMaps rendered by the umbrella chart | Decisions G-3 and G-5 | §6.3, §8.2 |
| `auth` implementing the RFC 8693 grant with `act` nesting and `may_act` | §5.3; OQ-1 | 03 §8.3 |
| PodDisruptionBudget on the API Deployment | It is the single ingress; a node drain must not take all replicas | 09 §4.2 |

---

## 12. Explicit DO-NOT list

09 §9's list applies in full — all thirty-two items. These are additional, and gateway-specific. Each carries the finding that makes it a defect rather than a preference, so a reviewer may cite the number and stop reading.

### 12.1 The D32 prohibitions

1. **Do not project a proposal's `payload`, `evidence[]`, `rationale`, `adjudication_note`, or `llm_version` into the gateway's store.** Not "temporarily", not "just the first evidence ref", not "just a truncated rationale for the list view". The whole of D32-R1 is that the gateway holds routing metadata and the owner holds content. *(**D32**; §2.3, §2.4)*
2. **Do not add a column to `proposal_queue` without amending `PROJECTED_COLUMNS` in the same commit, with the D32 justification in the commit message.** The allowlist test failing is the design working. *(**D32**; §2.4)*
3. **Do not build a read model of any other domain aggregate.** No asset cache, no prediction cache, no configuration mirror, no readiness snapshot. The migration head's table set is asserted in CI, and a tenth table is a D32 regression whatever it is called. *(**D32**; §9.3, §10.1)*
4. **Do not cache a fragment response, a composed view, or a proposal detail response.** A response cache is a read model with no schema, no rebuild path, and no purge path — D32 and D15 at once. *(**D32**, **D15**; §3.5)*
5. **Do not subscribe the broker client to a pattern.** Not `^fathom\..*\.proposal\.v1$`, not any other regex. The list is explicit; the pattern is a CI assertion. A pattern subscription reintroduces C38 *and* discloses the names of topics above the deployment's classification level, which is D13's existence leak one level up. *(**C38**, **D13**; §4.2, §2.5)*
6. **Do not subscribe to a topic above the deployment's declared classification level, and do not add a second level to a deployment.** Segregation is one deployment per level. A single deployment filtering by label is post-filtering, which D13 and 09 DO-NOT 22 prohibit, and it makes the gateway the classification enforcement point. *(**D13**, **D32**; §2.5, §7.1)*
7. **Do not compute an aggregate spanning classification levels** — including total queue depth for admission control. *"Aggregation is a classification event."* A cross-level total is obtainable only through an accredited guard, and the gateway is not one. *(**D13**; 03 §7.3, §7.4, §4.8)*
8. **Do not make the projection a precondition for anything.** A proposal absent from the queue is still adjudicable; a row present in the queue confers no authority. The index is not a gate. *(**D32** property 2, **D16**; §2.3, §4.6)*
9. **Do not give the gateway an outbox or a Kafka producer.** It publishes nothing. If that changes, the outbox is acquired first and §9.2 is rewritten — not worked around. *(03 §15.11 read with 11 §1.1; §9.2)*

### 12.2 Composition and the no-chained-calls principle

10. **Do not chain upstream calls, and do not design a view that requires an upstream to fetch a peer's data.** A cross-sub-application join happens in the gateway. This is 03 principle 2 — *"the principal defense against a distributed system that fails like a monolith"* — and 09 §4.4.2's NetworkPolicy makes the forbidden shape structurally impossible, so a view that needs it is a view that must be redesigned. *(03 principle 2; 09 §9.1 item 2; §3.1, §3.6)*
11. **Do not exceed two phases in a view.** Three serial phases inside 06 §7's 1.5 s p95 leaves ~500 ms each, and three chained maxima do not survive a p95 target. *(06 §7; §3.1 Rule C2)*
12. **Do not drop a failed fragment from the response.** `empty` and `unavailable` are different facts and are rendered differently. A view that silently omits a failed prediction fragment tells the operator there is no predicted risk, which is the most damaging thing this system can say. *(§3.4)*
13. **Do not return a partial body when a required fragment failed.** A view whose subject could not be confirmed is not a degraded view. *(§3.4)*
14. **Do not retry a read timeout.** Retrying a timeout doubles load on a dependency that is already failing — the monolith-failure mode itself. One retry on connect failure only. *(03 principle 2; §3.3)*
15. **Do not use `asyncio.TaskGroup` for the fan-out.** It cancels siblings on the first exception, turning one slow upstream into a blank view. *(§3.4)*
16. **Do not raise a view's latency budget to accommodate a slow upstream.** The budgets are transcribed from 06 §7. An anomalous fragment latency is a finding against that sub-application, not a configuration change here. *(06 §7; 09 §9.5 item 31; §3.6)*

### 12.3 Authority, and not becoming the enforcement point

17. **Do not authorize.** Do not read roles, clearance, caveats, compartments, unit, billet, or qualification. Do not hold an OPA or Cedar policy. Do not check a principal against a proposal's `authority_class` or `blast_radius`. Do not pre-reject a request the upstream will reject. The two enumerated defense-in-depth exceptions are §5.4's autonomous refusal and §7.2's classification fault, and adding a third requires an ADR. *(03 §4, obligation 7; §5.7)*
18. **Do not assert any header a sub-application might authorize on.** No `X-Fathom-Clearance`, no `X-Fathom-Roles`, no `X-Forwarded-User`. Everything a sub-application authorizes on arrives in a token signed by `auth`. This is the subtlest route to becoming the enforcement point. *(03 obligation 7; §5.7, §8.4)*
19. **Do not retry a delegated request under the gateway's own workload identity**, on any failure, at any layer. An expired delegation is terminal. *(**D12**; 03 §8.3, §5.5)*
20. **Do not hold a refresh token for any user, and do not refresh a delegation token.** That is a standing ability to act as any user who has ever used the system. *(**D12**; §5.5)*
21. **Do not cache, persist, or log an exchanged delegation token.** *(§5.3)*
22. **Do not mint a token with the gateway's own key** unless the §5.3 fallback has been adopted by ADR, with the SSP noting that the gateway's signing key becomes an authorization root. *(§5.3, §5.7)*
23. **Do not issue a delegation token whose TTL, scope, or audience exceeds the subject's.** An exchange narrows authority; it never extends it. *(03 §8.3; §5.3)*
24. **Do not forward the caller's token to a Domino Endpoint**, and do not let the static Endpoint token exist anywhere but the gateway's projected secret. *(**D12**; 02 §4.3, §5.6)*
25. **Do not synthesize an `If-Match`, and do not regenerate an `ETag` on pass-through.** Either defeats D16's claim mechanism while appearing to satisfy it. *(**D16**; 03 §7.2, §4.6, §8.4)*
26. **Do not implement the claim lease in the gateway.** A lease held anywhere but the store that performs the state change is not a lease, and two gateway deployments would each hold their own. *(**D16**; §4.6)*
27. **Do not expose an `x-agent-eligible` operation on the gateway's own surface.** An agent that can read the adjudication queue can observe which of its own proposals were rejected and by whom — an unadjudicated feedback channel of the kind D23 objects to. Agents obtain state through sub-application tools. *(**D23**, **C19**; §4.5, §8.3)*
28. **Do not halt anything.** Queue depth is measured here; candidate generation and proposal generation are halted by their owners. A gateway with a throttle over another sub-application's pipeline is a control plane, and holds no contract making it one. *(06 §6; §4.8)*

### 12.4 Time, ordering, and the queue

29. **Do not use a wall clock for any deadline, timeout, backoff, circuit-breaker window, rate-limit refill, or lease evaluation.** The single sanctioned wall-clock read is JWT `exp`/`nbf` (§5.2), confined to one module by an import-linter contract. A wall-clock rate-limit refill is a bypass triggered by NTP. *(**D29**; 03 §5.4, 11 §11.5 gate 5; §3.3, §6.3)*
30. **Do not sort, compare, or merge on `announced_recorded_at`, `occurred_at`, or `source_time`.** Precedence is `(producer_slug, producer_node_id, monotonic_seq)`. *(**D29**; 11 §11.5 gate 4; §4.3, §4.4)*
31. **Do not label the `learned` sort order "oldest first."** A proposal created afloat in week 1 of a six-week disconnection arrives in week 7 and takes a later `projection_seq`. Mislabelling it systematically buries exactly the afloat proposals the edge-scope decision exists to capture. *(**D8**, **D29**; 06 §4, §4.4)*
32. **Do not render `announced_recorded_at` as a precise time when `announced_dispersion_ms` exceeds the inter-arrival interval.** 03 §5.4: a large epsilon *"forces causal-only ordering and forbids any timestamp arbitration."* *(**D29**; §4.4)*
33. **Do not record inbox receipt before processing.** A permanently-suppressed `proposal.created` is a proposal that exists, is adjudicable, expires unadjudicated, and never appears in the queue — quieter than D16's double adjudication and no less serious. *(**D2**; 03 §5.2, 11 §3.2, §4.3)*
34. **Do not rebuild the projection from the event bus.** Retention is bounded by design. Rebuild is `changed_since`. *(**D5**; §4.7)*
35. **Do not rewrite a projected row minted under a provisional identity.** Resolve aliases on read. *(11 §12 item 13; §4.3)*
36. **Do not project a malformed or cross-domain proposal event.** A `target_sub_app` differing from the producing slug is a sub-application publishing a fact about another domain. Quarantine and alarm. *(03 principle 3, **C32**; §2.4, §4.3)*

### 12.5 Classification and the ingress

37. **Do not filter or redact for classification.** Removing results afterward leaks the existence of records. Refuse, alarm, fail closed. *(**D13**; 09 §9.4 item 22, §7.2)*
38. **Do not set `failClosed: false` in any environment.** There is no configuration in which an over-level response is returned with a warning. *(**D13**; §7.2)*
39. **Do not persist or publish a composed view's classification union.** It is a header on one response. Persisting it manufactures a union-classified fact. *(**D13**; 03 §7.3, §7.3)*
40. **Do not guess a union of incomparable distribution statements.** `REL TO` is not ordinally comparable with the lettered DoDI 5230.24 statements; the derived value requires an explicit determination by the classification authority. *(10 §4.8, 10 OQ-16; §7.3)*
41. **Do not add a catch-all proxy route.** Routes are generated from committed specs so the ingress surface is exactly the union of nine reviewed contracts, and so `x-side-effects` is statically known to the shared middleware. *(§8.2)*
42. **Do not re-wrap an upstream RFC 9457 problem body as a gateway problem.** It destroys the stable-`type` contract. *(03 §4; §8.4)*
43. **Do not store a `429` as an idempotent outcome.** The request did not execute, and storing it makes the caller's legitimate retry permanently impossible. *(09 §5.3; §6.5)*
44. **Do not add a NetworkPolicy peer not declared in `values.networkPolicy`, and do not disable the policy.** The `gateway → domino-*` egress this document requires is added by ADR plus an amendment to 09 §4.4.2, not silently. *(09 §9.5 item 30, 01 §11; §11.3, §14 item 3)*

---

## 13. Definition of Done

**The shared Definition of Done in [09 §8](09-monorepo-and-conventions.md) applies in full and nothing is removed from it.** Where an item is satisfied vacuously or by not needing it, that is recorded below with the reason rather than left ambiguous — 09 §8's instruction is that each build document *"reproduces this checklist for its own component, adds component-specific items, and removes nothing."*

### 13.1 Shared items requiring an explicit disposition

| 09 §8 item | Disposition |
|---|---|
| 8.1 `changed_since` read for every aggregate a declared consumer projects | **Not applicable — no consumer projects a gateway aggregate**, because the gateway owns none. The reciprocal obligation binds instead: the gateway **consumes** all ten producers' (the nine sub-applications plus `audit`) `changed_since` reads for rebuild, and contributes the conformance test proving each exists (§4.7, §10.4) |
| 8.1 A bulk, idempotent, fenced write operation | **Not applicable** — the gateway receives no batch results. Batch scoring results are written **through** it to PdM's bulk ingest operation, which is PdM's operation (01 §3 correction 2, 09 §4.4.2) |
| 8.2 Every state change reachable through the contract emits an event | **Satisfied vacuously.** The gateway effects no state change of its own; claim and adjudicate are the owner's, announced on the owner's topic (§9.2) |
| 8.2 Envelope, `clock` block, topic naming, compaction key, schema registration, AsyncAPI | **Not applicable to publication** — `PUBLISHES` is empty, so `asyncapi.yaml` documents consumption only. All of it applies to **consumption**: the projector rejects any envelope missing `producer_node` or the full `clock` block (§4.3) |
| 8.2 No wildcard subscriptions | **Satisfied by the enumerated ten-topic list** (the nine `SubAppSlug` plus `audit`'s exception), with `PROPOSAL_TOPIC_PATTERN` used only as a CI assertion (§4.2, decision G-1, C38) |
| 8.3 Transactional outbox via `packages/py-sync` | **Not applicable — the gateway publishes no event.** 11 §1.1 scopes the outbox to *"every program-built service that publishes any event."* No `outbox` table exists, and `test_d32_gateway_publishes_nothing` asserts it (§9.2) |
| 8.3 Antecedent / epoch-fencing rule | **Satisfied by not needing it, and the reason is D32.** Fencing requires a local configuration read model; the gateway holds none, and building one to fence with would be the D32 defect. `baseline_epoch` is projected as a **warning** and the authoritative staleness check is the owner's mandatory re-validation at adjudication (§4.3 rule 2, 03 §7.2, D16) |
| 8.3 Conflict policy declared per aggregate | **Default accepted explicitly:** enterprise-authoritative, not edge-writable (03 §11). The gateway owns no aggregate; the proposal conflict policy — *"append-only; adjudication server-authoritative and claim-gated"* — is the **owner's**, and the gateway's projection is derived from it. Recorded in the README per 09 §8.3 |
| 8.4 Provenance for every derived value published | **Satisfied vacuously** — nothing is published. The composed view's classification union is a response header computed with the shared `ClassificationLabel.union()` and carries `inherited_from` (§7.3) |
| 8.5 Conformance suite | `packages/contracts/conformance/gateway/` **plus ten consumer-driven contributions** (§10.4) — the latter being a hard requirement under 09 §4.7, since the gateway declares ten dependencies in 03 §6 (the nine sub-applications plus `audit`) |

### 13.2 Gateway-specific items

**D32 — the resolution holds (§2.6). All thirteen tests of §10.1 green.**

- [ ] `test_d32_read_model_column_allowlist` and `test_d32_forbidden_fields_absent_from_all_models` green; `PROJECTED_COLUMNS` and `FORBIDDEN_FIELDS` present with their D32 comments.
- [ ] `test_d32_projection_discards_payload_from_the_wire` green — the canary scan finds neither canary in **any** text or JSONB column of the gateway database, after real end-to-end projection through Redpanda and PostgreSQL.
- [ ] `test_d32_queue_response_contains_no_free_text` green.
- [ ] `test_d32_subscription_confined_to_declared_level` green against a broker holding proposal topics at two levels; `test_d32_no_broker_pattern_subscription` and `test_g1_enumerated_list_equals_pattern_expansion` green.
- [ ] `test_d32_read_model_rebuild_with_bus_down` green — rebuild identical to projection, with Redpanda stopped.
- [ ] `test_d32_purge_is_truncate_and_rebuild` green; the §4.7 purge protocol documented in the README with a named owner *(03 §13 item 2, D15)*.
- [ ] `test_d32_gateway_publishes_nothing`, `test_d32_no_domain_readmodel_other_than_the_queue`, `test_d32_stale_projection_cannot_cause_a_wrong_adjudication`, `test_no_cross_level_read_path` green.
- [ ] The `proposal_queue` DDL carries all four CHECK constraints of §2.4, including `proposal_queue_owner_is_producer`.

**Composition (§3)**

- [ ] Every view in the registry declares its budget from **06 §7** and cites it. No invented budget *(09 DO-NOT 31)*.
- [ ] `test_fanout_is_concurrent_not_sequential`, `test_view_phase_count_bounded_at_two`, `test_fragment_has_exactly_one_upstream` green.
- [ ] Partial-failure suite green: `test_partial_failure_is_rendered_not_dropped`, `test_required_fragment_failure_returns_503_with_no_partial_body`, `test_forbidden_fragment_does_not_fail_the_view`.
- [ ] `test_read_timeout_is_not_retried`, `test_fragment_deadline_clamped_to_view_deadline` green.
- [ ] Bulkhead and circuit breaker per upstream, sized from the ConfigMap; `test_bulkhead_returns_unavailable_rather_than_queueing` and `test_circuit_opens_and_probes` green.
- [ ] `test_no_domain_response_is_cached` green. The cacheable set is exactly §3.5's three entries.
- [ ] Every deadline via `MonotonicDeadline`; 11 §11.5 gate 5 clean across the whole service.

**Queue (§4)**

- [ ] `events/catalog.py` `CONSUMES` equals `helm/values.yaml` `events.consumes` equals the ten proposal topics (the nine `SubAppSlug` plus `audit`'s exception, §4.1); CI job 6 green *(09 §8.2)*.
- [ ] The 11 §3.2 inbox comment template present **verbatim**, with the gateway-specific severity paragraph (§4.3).
- [ ] Precedence on `(producer_slug, producer_node_id, monotonic_seq)`; `announced_recorded_at` stored and never compared.
- [ ] Provisional-identity alias resolution active on read *(11 §1.1, §8)*.
- [ ] Malformed and cross-domain events quarantined with `processed_at` NULL and alarmed, never projected.
- [ ] All filters of §4.5 implemented, including `authority_class` and `blast_radius` *(03 §7.2.1, D16)*.
- [ ] `queue_freshness` on every list and summary response, with `classification_level` and `completeness: "level_scoped"`.
- [ ] Cursor carries the projection generation; a stale cursor returns `400`, never silently skips or repeats.
- [ ] Claim and adjudicate **proxied**; `test_gateway_never_synthesizes_if_match` and `test_gateway_forwards_an_authority_violation` green.
- [ ] Detail fetch returns `503` rather than a partial proposal when the owner is unreachable; a proposal absent from the projection is still servable (§4.6).

**Authority (§5)**

- [ ] JWKS validation with an algorithm **allowlist**; `alg: none` and all HMAC families rejected.
- [ ] `auth/clock.py` is the only wall-clock reader; the import-linter contract confining it is in place and CI-enforced.
- [ ] Two-hop RFC 8693 exchange with `act` nesting and `may_act`; the full §10.3 authority suite green.
- [ ] `test_d12_no_service_identity_fallback` green — no upstream request on a delegated path carries the gateway's own workload token.
- [ ] `test_d12_accountable_owner_required` and `test_d12_autonomous_state_change_refused` green *(03 §8.3, D12)*.
- [ ] Domino Endpoint proxy: audit written **before** the response; caller's token never forwarded; static token exists only as the gateway's projected secret *(D12, 02 §4.3)*.
- [ ] `test_gateway_has_no_policy_engine` and `test_gateway_asserts_no_authorization_header` green — the two checkable forms of "the gateway does not authorize" *(obligation 7)*.

**Rate limiting (§6)**

- [ ] Two tiers implemented, keyed per §6.2, with `(sub, act.sub)` separating a delegated agent's budget from its user's.
- [ ] `test_ratelimit_refill_is_monotonic` green under an injected backward clock step *(D29)*.
- [ ] `test_ratelimit_does_not_poison_idempotency_key` green; the limiter runs before the idempotency middleware writes.
- [ ] Per-sub-application limits from the ConfigMap; `test_upstream_limits_come_from_configmap_not_discovery` green; CI asserts the ConfigMap's slug coverage.
- [ ] `429` never rendered as `503`; `Retry-After` an integer ≥ 1 derived from monotonic refill.

**Classification (§7)**

- [ ] `deploymentLevel` required with no default; `test_demo_posture_is_single_level_by_configuration` green. The single-level demonstration posture is **stated** in the README *(03 §12, 06 §5)*.
- [ ] `failClosed` not overridable; `test_classification_fault_fails_closed` green. **No filtering, no redaction, anywhere.**
- [ ] Union via the shared `ClassificationLabel.union()`, never a local implementation; never persisted; `test_classification_union_uses_shared_implementation` green.
- [ ] `test_incomparable_distribution_statements_fault` green.
- [ ] Kafka ACL granting exactly ten topics at one level, denying `describe` above it — verified against the deployed cluster, not only in the chart.

**Surface and deployment (§8, §11)**

- [ ] Pass-through routes generated from the ConfigMap-delivered specs; no catch-all; unknown path `404`s. Merged `openapi.json` generated and committed, CI green on drift *(09 §2.5)*.
- [ ] Every gateway operation declares `x-substitution: internal`, an `x-side-effects` class, and `x-agent-eligible: false`; carve-outs enumerated in `x-naming-carve-outs` *(09 §8.1, C23)*.
- [ ] `test_passthrough_is_byte_identical` and `test_passthrough_forwards_etag_and_conditional_headers` green; upstream problem bodies never re-wrapped.
- [ ] Middleware order per §8.6, with authentication at 4 and rate limiting at 5.
- [ ] Two Deployments from one chart; the `read_model_lag` readiness check registered on the **projector** only, with API responses carrying `queue_freshness.stale` instead (§4.7, §11.2).
- [ ] helm-unittest egress-equality assertion green; the `gateway → domino-*` edge carries an ADR and an amendment to 09 §4.4.2 *(§11.3, §14 item 3)*.
- [ ] Host time synchronization per 03 §5.4 verified as a deployment prerequisite (§11.4).
- [ ] Load suite asserts 06 §7's p95 budgets; the tooling gap recorded as inherited from 09 OQ-8, not resolved locally *(09 §8.7)*.

**Documentation and governance (09 §8.7)**

- [ ] README states purpose, the D32 resolution in one paragraph with a pointer to §2, consumed events, the accepted conflict-policy default, the staleness bound, the declared purge protocol and its owner, the sanctioned NetworkPolicy peers, and the single-level classification posture.
- [ ] Every decision marked **[ESTABLISHED HERE]** in §2.7 that a reviewer overturns carries an ADR.
- [ ] Every 09 **[OPEN]** item this document had to resolve locally is recorded in the README as a local resolution and raised for a program decision.

---

## 14. Corrections to the source documents

Found while reconciling, and following 09 §11's convention: each is a **defect in the cited document**, not a decision of this one. Items 1 and 3 are blocking — the gateway cannot pass CI or deploy without them.

| # | Document | Defect | Correction | Status |
|---|---|---|---|---|
| 1 | **03 §6, "Proposals — a convention"** | The consumer column lists `proposal.created` → `gateway, notification` and `proposal.expired` → `gateway, audit`, but `proposal.adjudicated` → `audit, and the owning sub-application` — **omitting `gateway`**. The gateway's queue must observe adjudication or every approved proposal remains `proposed` in the queue forever, which is a stale-queue defect adjacent to D16. Because 09 §8.2 and CI job 6 reconcile a service's `CONSUMES` against 03 §6's catalog rows in **both** directions, the gateway literally cannot pass CI until this is corrected | Add `gateway` to `proposal.adjudicated`'s consumers | **Blocking.** Not applied; flagged. §9.1 |
| 2 | **03 §6, same table** | `proposal.adjudicated`'s consumers include *"the owning sub-application"* — the producer of the event. A sub-application consuming its own published event is either a no-op or an inbox loop, and it is the only such entry in the whole catalog. It appears to mean *"the owning sub-application acts on the adjudication"*, which is an internal state transition, not a consumption | Remove, or restate as prose outside the consumer column | Not applied; flagged |
| 3 | **09 §4.4.2 sanctioned edge set** | The table lists *"program ingress namespace → `domino-*` namespaces"* but does not list **`gateway` → `domino-platform` / `domino-compute`**, which is required by 03 §8.3's proxied-Endpoint rule (D12) and by 01 §8.7's agent invocation. Per 09 §4.4.2's own rule, an unlisted edge *"requires a change to this document plus an ADR"* | Add the edge, with the D12 rationale | **Blocking deployment.** ADR required; 09 amendment required. §11.3 |
| 4 | **09 §4.4.1 mandatory `values.yaml` shape** | 03 §4 requires *"per-sub-application limits declared in its chart"*, but 09 §4.4.1's mandatory shape carries no `rateLimit` block. Nine services will therefore not declare one, and the gateway's `gateway-upstream-limits` ConfigMap has nothing to render from | Add `rateLimit: {requestsPerSecond, burst, maxConcurrent}` to 09 §4.4.1's mandatory keys | Not applied; flagged. §6.3 |
| 5 | **09 §5.7 middleware order** | The fixed order has four positions and no authentication or rate-limiting step, because it was written for a sub-application that is authenticated *by* the ingress. The gateway *is* the ingress and needs both, in a specific relative position (rate limiting before idempotency, per §6.5) | Note that the gateway extends the order with authentication at 4 and rate limiting at 5 | Not applied; flagged. §8.6 |
| 6 | **04 §11 "API Gateway / BFF"** | Describes the gateway such that *"composition happens here"* implies a stateless layer, while the same sentence assigns it a topic-pattern-consuming queue. This is finding **D32** as a textual matter, and the paragraph should record the resolution rather than leaving the contradiction in the architecture of record | Amend to state that the gateway maintains a metadata-only, non-authoritative, level-partitioned projection, per this document §2 | Not applied; flagged. **This is the document 04 amendment D32's FIX disposition implies** |
| 7 | **03 §7.2 / §7.2.1 interaction with 03 §6** | 03 §6's convention says *"every sub-application accepting agent proposals"* publishes a proposal topic, but 03 §7.2's six `kind` values map to fewer than nine owners, and no document states which of the nine accept proposals. C12 records the adjacent defect (*"no sub-application in 04 lists `Proposal` in its Owns boundary"*). The gateway subscribes to all nine as the safe reading (§9.1) | Enumerate, per sub-application in 04 §2–§10, whether it accepts proposals and of which kinds | Not applied; flagged. Compounds **C12** |
| 8 | **10 §4.7 `Proposal.authority_class`** | Typed as an opaque `NonEmptyStr`, with the docstring recording that *"the vocabulary is therefore undefined in document 03"* and calling it *"the most consequential open question in this package"* (10 OQ-13). **Document 03 §7.2.1 now defines it** — six classes (five plus `security_officer`, amendment 03-1) and a minimum-authority table — so the field can and should be a `StrEnum` | Replace with `AuthorityClass = maintainer \| planner \| supply_officer \| design_authority \| fleet_authority \| security_officer` in `packages/canonical-schemas`, and close OQ-13 | **Resolved.** `31-auth.md` §2.4 defines the six-member `AuthorityClass` enum in `packages/canonical-schemas` (its own new module), closing OQ-13; this row's premise is now stale and is left here only as history |
| 9 | **10 §4.5 `PROPOSAL_TOPIC_PATTERN`** | The docstring says the D32 tension *"is document 04's to resolve, not this package's."* Document 04 did not resolve it; this document does, as decisions D32-R1/R2/G-1 | Update the docstring to cite `docs/build/30-gateway.md §2` and note that the constant's sanctioned use is the CI assertion of §4.2, **not** a broker subscription | Not applied; flagged |
| 10 | **03 §7.2 `valid_until`** | *"absent means no expiry is permitted"* is ambiguous, and 10 §4.7 records the two readings at OQ-14, resolving it as mandatory. The gateway's queue depends on the mandatory reading — `expiry` is the default sort (§4.4) and a NULL `valid_until` would make the default ordering undefined | State the mandatory reading explicitly in 03 §7.2 | Not applied; flagged. The gateway assumes mandatory, per 10 §4.7 |
| 11 | **Task framing for this document** | Asserted that resolution option (b) *"would violate [03's no-synchronous-calls principle] on every queue-view request."* On the text of 03 principle 2 it would not: the second sentence explicitly permits synchronous reads for user-facing composition performed by the gateway | Option (b) is rejected on the four grounds in §2.2, not on principle 2 | Recorded in §2.7 |

---

## 15. Open questions

Recorded rather than resolved locally, because each affects a document this one is downstream of. Numbered `OQ-n` per this document.

| # | Question | Impact if unresolved | Interim position |
|---|---|---|---|
| **OQ-1** | **Does `auth` implement RFC 8693 with `act` nesting and `may_act`?** Keycloak documents token exchange; conformance on these two claims is unverified | Blocks the delegated-agent path (§5.3). It is downstream of 01 §8.7, *"the single open dependency capable of altering the agentic design"* | Build against RFC 8693. The signed-assertion fallback is specified (§5.3) and requires an ADR plus an SSP note. Raise with `auth`'s build document |
| **OQ-2** | **The `audit` payload-size threshold and object-store spillover destination** for full request/response recording (03 §8.5) | The gateway must reference rather than inline large bodies (D27's pattern), and cannot pick a threshold without inventing a number (09 DO-NOT 31) | Reference above a threshold `audit` sets. Raise with `audit`'s build document, alongside 11 OQ-10 |
| **OQ-3** | **Can 06 §7's p95 budgets be met by fan-out with no gateway cache?** 1.5 s for fleet and asset views, 4 s for explanation decomposition, over 12 assets and ~8,400 installed items | If not, the answer is upstream indexing or narrower fragments — **not** a gateway cache, which would reintroduce D32 (§3.5) | Assume yes at demonstration scale. The verification tooling is 09 OQ-8's unresolved load-testing gap, inherited not resolved |
| **OQ-4** | **How does a user cleared for two levels work?** Under D32-R2 they use two hostnames and there is no single pane across levels | A cross-level pane is a cross-level flow requiring an accredited guard, which is a program and accreditation undertaking | Two hostnames. Cost recorded in §2.5. Raise as a program question, not an engineering one |
| **OQ-5** | **A shared rate-limiter store at production scale.** Decision G-5's per-replica buckets are over-permissive by at most `maxReplicas/minReplicas` | Sufficient for the demonstration's envelope; becomes the wrong answer at fleet scale | In-process buckets sized against `minReplicas` (§6.3). Revisit with the production capacity model (05 §4.6) |
| **OQ-6** | **Which of the nine sub-applications actually accept proposals, and of which kinds?** §14 item 7 | The gateway subscribes to all nine, which is safe but leaves the conformance contribution set partly notional for a sub-application that accepts none | Subscribe to all nine; a topic with no messages is inert. Resolved by the 04 §2–§10 amendment |
| **OQ-7** | **Does the operator UI need a cross-sub-application proposal search** — free-text over rationale or payload? | Would require either projecting free text (a D32 violation) or a nine-way fan-out search (option (b)'s problems, scoped to search) | **Not offered.** Structured filters only (§4.5). If the requirement is real, the honest answer is a search capability in `knowledge-retrieval` over an owner-published index, not a gateway projection. Raise at the look-and-feel wave |
| **OQ-8** | **Notification's relationship to the queue.** 03 §6 makes `notification` a co-consumer of `proposal.created`; 04 §11 gives it *"escalation … for adjudication requests"* | Two components consume the same event for adjacent purposes. Duplicated escalation logic, or a gap, is possible | The gateway serves the queue; `notification` routes and escalates. Neither reads the other's store. Confirm the boundary with `notification`'s build document |
| **OQ-9** | **Whether the gateway should surface a per-authority-class "my queue" projection** keyed to the caller's roles | Requires the gateway to read role claims, which §5.7 forbids | **Not offered.** **[CORRECTED — the premise below was wrong; flagged by `50-ui-design-system.md` §13 correction 7.]** The UI filters by `authority_class` using the roles from the session identity §8.1.2 returns — **not** "its own token," since `apps/web` is a BFF that never holds one (§5.1: *"the user's access token never leaves the server"*). Recorded so nobody adds a role-aware server-side filter and calls it presentation |
