# Build Framework 34 — Tool Server: MCP Hosting, Discovery, and Invocation-Time Enforcement

| | |
|---|---|
| **Status** | Draft rev 1 |
| **Slug** | `tool-server` (document 03 §3.1, platform services line) |
| **Deliverable** | `platform/tool-server` — the Sustainment Plane platform service that **serves** the MCP descriptors `packages/agent-tooling` generates, **scopes** discovery to a calling agent's pinned manifests, and **re-validates authority and eligibility at the moment of invocation** |
| **Why it exists** | [02 §4.2](../architecture/02-domino-platform-assessment.md): *"Model Context Protocol is not a Domino capability. Zero pages in the documentation sitemap; zero occurrences across three years of release notes."* There is no platform-provided registry, discovery, or governance to inherit. This service is the whole of it |
| **Binding contracts** | [03 §8](../architecture/03-integration-contracts.md) in full (§8.1 eligibility/selection, §8.2 manifests, §8.3 agent authority classes, §8.4 versioning and pins, §8.5 invocation properties) · [03 §4](../architecture/03-integration-contracts.md) and §4.1 (REST conventions, operation annotations) · [01 §8.0](../architecture/01-system-architecture.md), §8.5, §8.7 |
| **Consumed tooling — do not redesign** | [`10-shared-packages.md` §7](10-shared-packages.md) — the manifest schema, the eligibility reader, the `McpToolDescriptor` model, the generator and its exit codes, the proliferation controls. This service **imports and hosts** that package's output. It generates nothing |
| **Conventions** | [`09-monorepo-and-conventions.md`](09-monorepo-and-conventions.md) — stack, scaffold, API rules, CI gates, Definition of Done template |
| **Resolves** | Finding **C17** (*"MCP tool servers are mandated on the Sustainment Plane but appear in no component inventory or monorepo path"*) at the build-framework level |
| **Classification** | Internal. The service operates at U for the synthetic demonstration (03 §12) |

---

## 0. How to read this document

### 0.1 The one distinction everything else depends on

`packages/agent-tooling` and this service are frequently conflated, and the conflation is exactly the defect that lets an agent call something it should not. They are separated as follows, and no row moves.

| | `packages/agent-tooling` (document 10 §7) | `platform/tool-server` (this document) |
|---|---|---|
| **When it runs** | Build and CI time | Request time |
| **Input** | A manifest YAML plus the **committed** OpenAPI document for the pinned API major | The **live** OpenAPI document the target is serving right now, plus the descriptor bundle |
| **Output** | Static MCP descriptor JSON, committed at `packages/agent-tooling/generated/<slug>/<name>.v<major>.mcp.json` | HTTP responses: a scoped tool list, and proxied tool-call results |
| **Failure mode** | An exit code. *"Every row is an exit code, not a warning"* (10 §7.5) | An RFC 9457 rejection. Never a warning, never a degraded success |
| **Authority over eligibility** | Decides whether a manifest **may be generated** | Decides whether a call **may proceed now** |
| **What it may never do** | Assert its own eligibility (10 §10.3) | Generate, mutate, or repair a descriptor |

The generator's verdict is a statement about the world **at generation time**. This service exists because the world moves: a specification can change, a service can be redeployed, and a manifest pin can be superseded, all between the commit that produced a descriptor and the next call an agent makes against it. **A cached eligibility claim is a claim about the past.** §4 is the whole of the response to that, and it is the reason this service is not a static file server behind an nginx.

### 0.2 What this document may not do

It may not restate document 10 §7. Where this document needs the manifest schema, the eligibility rule, the descriptor field set, or the exit-code discipline, it **cites and imports**. A second implementation of the §8.1 gate inside this service would drift, and — as §4.3 argues — the drift would be in the direction of permissiveness at exactly the point where permissiveness is most expensive.

Decisions this document makes that no architecture document dictates are marked **`DECISION`**, with the reasoning stated, per document 09 §1.3's `[ESTABLISHED HERE]` convention.

---

## 1. Purpose and scope

### 1.1 The verified negative this service answers

Document 02 §4.2 does not say MCP support in Domino is immature. It says it is absent, and says so from primary sources: zero documentation pages, zero release-note occurrences across three years, absent from the Winter Release 2026 announcement and the agentic product page, with the only artifact a two-star community repository carrying no support statement. The conclusion drawn there is quoted verbatim because it is this service's charter:

> *"The program should therefore expect to host MCP tool servers itself, without platform-provided registry, discovery, or governance for them."*

Document 03 §8.5 turns that into a component:

> *"Tool servers run on the Sustainment Plane as the `tool-server` platform service, since Domino provides no MCP registry, discovery, or governance (document 02 §4.2) `[C17]`."*

The consequence for sequencing is worth stating plainly: **Wave 5's agent runtimes have nothing to connect to until this service exists.** Document 01 §8.3 forbids an agent from answering a state question from parametric memory or the vector store; structured state arrives only through tools; tools arrive only through here.

### 1.2 In scope

1. **Hosting** the descriptor bundle — the committed MCP descriptors from `packages/agent-tooling/generated/`, plus the compiled agent→manifest binding table (§2).
2. **Discovery** — an MCP-compatible listing scoped to the calling agent's pinned manifests, plus the governed REST equivalent (§3).
3. **Invocation-time enforcement** — pin verification, live re-validation of the target operation's declared side-effect class and eligibility, authority-class enforcement, and token attachment (§4). **This is the service.**
4. **Proxying** an MCP tool call into the actual REST call against the target sub-application, per the descriptor's recorded operation mapping (§5).
5. **Recording** every invocation, with full request and response, to Audit & Provenance with `trace_ref` correlation (§4.6), per 03 §8.5.
6. **Publication mechanics** — how a newly generated descriptor becomes callable (§6).
7. **The third-party boundary** — what is published, and what is program infrastructure (§7).

### 1.3 Out of scope

| Not here | Where |
|---|---|
| Manifest authoring, the manifest schema, the generator, exit codes, overlap and orphan reports | Document 10 §7. **Not restated** |
| Whether an operation is `x-agent-eligible` in the first place | The owning sub-application's OpenAPI document, gated by `OAS004` (10 §5.3). Eligibility is *asserted* there; this service only *checks* it |
| Agent prompts, model pins, evaluation sets, golden question sets, the promotion pipeline | `agents/*`, per 01 §8.6 and §8.8, and the Wave 5 agent build documents |
| The two token classes' issuance, lifetime, exchange, and revocation | `platform/auth`. Not yet written: this document states the **requirement** generically against 01 §8.5 and 03 §8.3 and does not invent an issuance protocol (§4.5) |
| The immutable invocation ledger's storage, retention, and integrity | `platform/audit` (04 §11). This service is a **client** of it |
| View-model composition, per-caller rate limiting, delegated-token exchange | `platform/gateway` (01 §5, 04 §11) |
| Knowledge retrieval | `platform/knowledge-retrieval`. 04 §11: *"Structured facts are never served from this component… the distinction is enforced in the tool manifests"* |

### 1.4 Traceability

Every rule below traces to a line of an architecture document. A rule with no citation is a defect in this document.

| Mechanism | Source | Findings enforced |
|---|---|---|
| Service exists at all, on the Sustainment Plane | 03 §8.5; 02 §4.2; 01 §5 platform inventory | **C17** |
| Two-level exposure: eligibility gate vs. manifest selection | 03 §8.1; 01 §8.0 | **C1**, **D11** |
| Descriptors served, not generated | 03 §8.2; 10 §7.4, §7.5 | — |
| Discovery scoped to the pinned manifest | 03 §8.4; 03 §8.2 `owner` | — |
| Pin checked at call time (manifest version **and** API major) | 03 §8.4 | — |
| Live `x-side-effects` re-check; reject on mismatch | 03 §8.1, §4.1; 10 §7.4 `x_fathom_side_effects` | **C1**, **D11** |
| Eligibility never gated on HTTP method | 03 §4.1, §8.1 | **C1**, **D11** |
| Two agent authority classes; accountable_autonomous capped | 03 §8.3; 01 §8.5 | **D12** |
| Mid-run authority lapse is a defined condition, not a retry | 03 §8.3; 02 §4.1 (8-hour default propagation) | **D12** |
| Every invocation recorded with full request/response and `trace_ref` | 03 §8.5; 01 §8.5; 04 §11 | — |
| Domino Endpoint calls are proxied with caller identity attached | 03 §8.3; 02 §4.3 | **D12** |
| Agents are never direct topic consumers; this service consumes none either | 03 §6; 09 §9.2 item 15 | **C19** |
| Third parties may build tool surfaces from published contracts | 01 §8.0; 03 §8.5 | — |
| Bundle activation by deployment, never by runtime fetch | 01 §11 (Argo CD as the deployment record), 01 §12 | **D26** |
| No wall clock arbitrates a timeout, deadline, or cache age | 03 §5.4 | **D29** |

---

## 2. What the service holds

### 2.1 The descriptor bundle

The service serves exactly one immutable artifact set per running pod, called the **bundle**. It is assembled at image build time and has a digest.

```
platform/tool-server/bundle/
  bundle.v1.json          # GENERATED, COMMITTED. The compiled bundle
  bundle.sha256           # GENERATED, COMMITTED. Digest of the above, byte-exact
```

`bundle.v1.json` contains, and contains nothing else:

| Member | Source | Notes |
|---|---|---|
| `descriptors[]` | Every file matching `packages/agent-tooling/generated/<slug>/<name>.v<major>.mcp.json`, parsed as `list[McpToolDescriptor]` (10 §7.4) | Copied verbatim. **The compiler may not edit a descriptor field.** If a descriptor is unfit to serve, the fix is in the manifest and a regeneration, not here |
| `bindings[]` | Compiled from `agents/<name>/tool-pins.yaml` | §2.2 |
| `provenance` | Generation commit SHA, `generated_at`, the `bundle.sha256` value, and the per-target `(slug, api_major)` set the descriptors were generated against | This is the accreditation-visible answer to *"what could an agent have called at time T"* |

`make tool-bundle` builds it; `make check-bundle` regenerates and diffs, and **fails** on drift. This mirrors document 10's `check-generated` gate and document 09 §2.5's rule that generated documents are committed and CI fails on drift. **`DECISION`** — the bundle is a committed artifact rather than a build-time-only product, because an accreditor asking what an agent could call on a given date must be able to answer it from the repository at that commit, without reproducing a build.

### 2.2 The agent binding table

Document 03 §8.4 fixes what an agent pins:

> *"Manifest version and API major version are independent. An agent artifact pins **both**, plus its prompt and model version, promoted together as one registered unit."*

Document 01 §11 already places the pin with the agent: each `agents/<name>/` holds *"prompt, manifest pin, API version pin, evaluation set, deployment spec."* This service therefore does not own the pin; it owns the **compiled, enforceable projection** of the pins.

```yaml
# agents/pma-prescreener/tool-pins.yaml
# The filename is a DECISION of this document; agents/* is governed by 01 §8 and 03 §8,
# so Wave 5's agent build document may rename it.  Nothing here depends on the name —
# only on the compiled binding — so a rename costs a compiler constant.
agent_id: pma-prescreener
agent_authority: accountable_autonomous        # 03 §8.3; snake_case per 31 §2.5 amendment A-2.
                                                # Named agent_authority, not authority_class, to
                                                # avoid colliding with 03 §7.2.1's Proposal field
                                                # of the same bare name (31 §2.5's finding)
accountable_owner: <named human, resolvable in auth>   # 03 §8.3, required for this class
manifests:
  - name: pma-mission-review
    version: 1
    target: { slug: pma, api_major: 1 }
  - name: telemetry-window-read
    version: 2
    target: { slug: telemetry, api_major: 1 }
```

The compiler enforces four rules and **fails the build** on each. Every one is derived, not invented:

| # | Rule | Source |
|---|---|---|
| B1 | Every `(name, version, slug, api_major)` resolves to a committed descriptor file. A pin naming a manifest that was never generated is a build failure | 03 §8.4 — a pin that cannot be resolved is not a pin |
| B2 | For each bound manifest, `x_fathom_manifest.owner` is either this `agent_id` or `curated` | 03 §8.2 (`owner` is *"consuming agent, or `curated`"*), §8.4 (*"an unowned manifest is deleted rather than inherited"*) |
| B3 | **No duplicate tool `name` within one binding.** Two manifests bound to the same agent may not both select the same operation, because `name` is `<slug>__<operation_id>` (10 §7.4) and MCP tool names must be unique in a session | Derived. See below |
| B4 | `agent_authority` is exactly one of `delegated` or `accountable_autonomous`; `accountable_autonomous` requires a non-empty `accountable_owner` | 03 §8.3; naming per 31 §2.5 amendment A-2 |

**Why B3 is a hard failure and not a runtime disambiguation.** Document 01 §8.0 makes overlapping manifests over one API the *intended* design, and document 10 §7.6 is explicit that overlap is therefore *reviewed, not gated*. That reasoning holds **across** agents and does not hold **within** one agent's tool list: two descriptions for one tool name in one session is an ambiguous tool surface, which is the precise failure 01 §8.0 says degrades agent performance measurably. Runtime suffixing was rejected because it would make a tool's name depend on which manifests happen to be bound, and the tool name appears in the agent's prompt, its evaluation set, and its audit records — all three of which 03 §8.4 requires to be pinned and promoted as one unit. The remedy for a B3 failure is a manifest change, reviewed with the overlap report document 10 §7.6 already emits.

### 2.3 Caller identity is never self-asserted

The binding is keyed on `agent_id`, and `agent_id` is derived **only** from the validated token presented on the call — its subject or client identifier, mapped through a compiled table. A caller-supplied `X-Agent-Id` header, a JSON-RPC parameter, or a query string naming the agent is ignored where it agrees and rejected where it disagrees. An agent that could name itself could name another agent's binding, which would make every rule in §4 decorative.

Two hosting cases, and the service is indifferent to which one applies:

- **Domino-hosted runtime (the design position, 01 §8).** Delegated authority arrives through Domino's identity propagation, which document 02 §4.1 records as *"GA, and strong"* — including *"extended propagation permitting an application to act with the user's full permissions subject to explicit user consent, default eight hours and up to thirty days."* That eight-hour default is why 03 §8.3's mid-run expiry condition is an operational certainty rather than an edge case (§4.5).
- **Sustainment-Plane-hosted runtime (the 01 §8.7 contingency).** The caller is an ordinary in-cluster workload holding a Keycloak identity federated with Domino (01 §5). Same binding key, different issuer path, **no change to this service.** That indifference is a substantive part of why 01 §8.7 calls the contingency *"architecturally acceptable"*: relocating the runtime does not relocate tool governance, because tool governance was never in Domino to begin with.

### 2.4 Statelessness, and the obligations it switches off

**`DECISION` — the tool server owns no database.** Document 03 §15 obligation 13 requires a service to own exactly one logical database and reach no other; it does not require owning one. Every artifact this service serves is a build output baked into the image (§2.1), and every record it must retain durably belongs to Audit & Provenance, which document 04 §11 designates the immutable record of *"agent tool invocations with full request and response"* and treats as an accreditation artifact. A local store would create a second, weaker copy of that record, with its own purge obligation under 03 §13 and its own divergence risk against the system of record.

Consequences, each stated so no implementer restores it by reflex:

| Ordinarily mandatory (09 §4.2, §5.6, §8) | Here | Justification |
|---|---|---|
| Owned CloudNativePG cluster, Alembic, `migrations` readiness check | **Absent** | No aggregate, no state (§2.4) |
| Transactional outbox (03 §15 obligation 11) | **Not wired** | Document 11 §1.1 scopes the outbox writer to *"every program-built service that publishes any event."* This service publishes none (§9). Recorded as a deviation with an ADR, and as **OQ-4** |
| Consumer inbox, read models, `read_model_lag` check | **Absent** | Consumes no topic (§9) |
| `changed_since` snapshot reads (obligation 5) | **Absent** | The obligation is scoped to *"every aggregate a declared consumer projects."* There are none |
| Local `Idempotency-Key` deduplication | **Deliberately not implemented** | The key is forwarded to the target, which owns idempotency for its own operation (§5.4) |

Every row above is a deviation from document 09's per-service scaffold and therefore requires an ADR under `docs/adr/` per 09 §8.7. The ADR is a Definition-of-Done item (§16).

### 2.5 The live specification cache

The one piece of mutable in-process state, and the mechanism §4.3 rests on.

Per `(slug, api_major)` reachable through a bound descriptor, the service holds the target's **currently served** OpenAPI 3.1 document. Document 03 §15 obligation 1 makes that document exist and be true: *"Publishes an OpenAPI 3.1 specification, generated from code, verified in CI, with `x-substitution` and `x-side-effects` on every operation."* Because it is generated from code, the document a running service serves is a statement about that running service — which is the only authority that can answer "is this operation still `none`?"

| Property | Rule |
|---|---|
| Fetch path | Through `gateway` in pass-through mode (§5.1), never a direct sub-application edge |
| Refresh | Background poller per target, `If-None-Match` against the stored `ETag`. A `304` refreshes the age and nothing else |
| Age measurement | **Monotonic clock only.** A wall-clock age is a lie the instant STIG rule V-260520 steps the clock backward at reconnection — 03 §5.4, finding **D29** |
| Freshness bound | `FATHOM_TOOL_SERVER__SPEC_MAX_AGE_SECONDS`, no default (09 §4.5). The **value** is a program decision — **OQ-1**. The **behavior at expiry** is fixed here and is not configurable |
| Behavior at expiry | **Fail closed.** Every invocation against that target is rejected `503` `spec-cache-stale`. The cached descriptor's recorded class is **never** used as a fallback |
| Behavior on fetch failure | The last good document is retained and continues to age. It does not become authoritative-because-nothing-newer-arrived |
| Startup | The service is not ready until every target reachable through a binding has been fetched once. A pod that has never seen a target's spec cannot enforce anything about it |

The last row is the one an implementer under deadline pressure will want to relax into "serve discovery, enforce lazily." Do not: an agent that discovers a tool it cannot call has been handed a broken surface, and 01 §8.2's whole argument for the pre-screener is that a bounded, reliable candidate set is what makes human review tractable.

---

## 3. Discovery

### 3.1 Two surfaces, one enforcement path

**`DECISION`.** The service exposes both:

1. A **governed REST surface** under `/api/v1/tool-server/…`, conforming to document 03 §4 in full — OpenAPI 3.1 generated from code and committed, RFC 9457 problem details, `X-Correlation-Id`, `ETag`, cursor pagination, `X-Classification`. This is the contract surface: what CI validates, what the gateway proxies, what an operator reads.
2. An **MCP-compatible protocol endpoint** at `/mcp`, speaking JSON-RPC 2.0 with the methods `initialize`, `tools/list`, and `tools/call`.

Both are required. Only REST would abandon the single benefit of the descriptors being MCP-style — every agent runtime would hand-roll a client, and "MCP-style" would be a naming convention rather than an interoperability property. Only MCP would put the program's tool surface outside document 03 §4, which states its conventions are *"applicable to all sub-applications and platform services."*

**The adapter contains no logic.** `tools/list` and `tools/call` translate their arguments into the same internal use case the corresponding REST operation invokes, and translate the result back — including translating an RFC 9457 problem document into a JSON-RPC error whose `data` member carries the problem `type` verbatim. Enforcement lives in the use case, never in either adapter. §11 makes this structural by parametrizing the entire enforcement test suite across both surfaces: a second copy of the checks inside the JSON-RPC handler is the single likeliest way this service acquires a hole, because it is the surface no contract test naturally covers.

The MCP protocol revision is **pinned in configuration** (`FATHOM_MCP__PROTOCOL_REVISION`), asserted during `initialize`, and recorded in the README. No program document fixes a revision, so this document does not invent one — **OQ-2**.

### 3.2 Scoping: an agent discovers only what it pinned

Resolution order, on every discovery call:

1. Validate the bearer token against `auth` (JWKS). An unvalidatable token is `401`.
2. Derive `agent_id` from the token (§2.3). Never from the request body.
3. Look up the binding. **No binding is `403` `no-manifest-binding`, not an empty list.**
4. Union the descriptors of the bound `(name, version)` manifests. Emit them with the descriptor's own task-scoped `description` and `inputSchema` — the manifest's, not the API summary's (10 §7.4).
5. Filter nothing else. There is no "hidden tool" concept: if a descriptor is in the binding, it is discoverable, and if it is discoverable it is callable subject to §4.

**Why step 3 is a rejection and not an empty result.** An empty tool list is indistinguishable, from inside an agent, from "this deployment has no tools configured," and the documented behavior of a model with no tools is to answer from parametric memory — which document 01 §8.3 forbids outright for state questions. A `403` naming the missing binding is a condition the runtime can surface and an operator can fix. An empty `200` is a silent downgrade to the exact failure mode the grounding rule exists to prevent.

**Discovery is not authorization.** A descriptor appearing in `tools/list` asserts only that the agent's binding includes it. Every check in §4 runs again at call time, on the same call, with no reliance on the discovery response the agent received — which may be minutes or hours old, and may have been served by a pod running a different bundle during a rolling deployment. The discovery response therefore carries the serving pod's `bundle_digest`, so an agent or an investigator can tell which bundle answered.

---

## 4. Invocation-time enforcement

**This is the service.** Everything else is plumbing around it.

### 4.1 Why the checks are here and not only in CI

Document 10 §7.5's generator already fails on an absent operation, an ineligible operation, a missing description, an invalid parameter default, and an unresolvable projection. All five verdicts are true of the committed specification at the commit that generated the descriptor. Between that commit and an agent's next call, four things can change independently:

| Drift | How it happens | What a purely generation-time gate does |
|---|---|---|
| The target's spec changes `x-side-effects` from `none` to `state-changing` | An ordinary sub-application release. `OAS004` (10 §5.3) blocks `x-agent-eligible` **with** `state-changing`, so the release drops eligibility — but the committed descriptor still says `none` | Nothing. The agent calls a state-changing operation with a cached claim that it has no side effects |
| The operation is renamed or removed at the same API major | A spec change that the compatibility differ should have caught as breaking (10 §12.3) but that reached a deployment anyway | Nothing |
| The agent's manifest pin is superseded, or the agent runs an older artifact than the deployed bundle | Rolling deployments, a rolled-back agent, a long-lived agent session | Nothing |
| The deployed service and its committed spec disagree | `check-committed` bypassed, an emergency patch, a substituted implementation mid-migration (03 §10) | Nothing |

Every row is a live hole in a design where enforcement happens only at generation. Document 10 anticipated this and left the hook: `McpToolDescriptor.x_fathom_side_effects` exists, in its own words, *"so the tool server can refuse a call whose declared class changed since generation."* §4.3 is that refusal.

### 4.2 The ordered gate

Every invocation passes all nine gates, in this order, and any failure ends the call. **No gate is skippable, samplable, or configurable off.** Order matters: nothing reaches the target, and nothing is proxied, until every check has passed.

| # | Gate | Rejects with | Source |
|---|---|---|---|
| 1 | Token validates against `auth`; `fathom.agent.authority` claim present (31 §2.5 amendment A-2 — not `authority_class`, which is document 03 §7.2.1's distinct Proposal field) | `401` `invalid-token` / `422` `agent-authority-missing` | 03 §4 Authentication, §8.3 |
| 2 | Token is not expired and not inside the refusal margin | `401` `delegated-authority-lapsed` | 03 §8.3 |
| 3 | `agent_id` derived from the token resolves to a binding | `403` `no-manifest-binding` | §2.3 |
| 4 | The requested tool `name` is present in **this agent's** binding, and the binding's `(manifest name, version)` and `(slug, api_major)` match the descriptor's `x_fathom_manifest` and `x_fathom_target` | `403` `tool-not-in-pinned-manifest`, `409` `manifest-pin-superseded`, `409` `api-major-pin-unsatisfiable` | 03 §8.4 |
| 5 | The live spec cache for `(slug, api_major)` is present and within its freshness bound | `503` `spec-cache-stale` | §2.5 |
| 6 | **`assess(live_spec, operation_id)` returns eligible**, and the live declared class **equals** `x_fathom_side_effects` | `409` `side-effects-mismatch`, `403` `operation-not-agent-eligible`, `409` `operation-absent-from-live-spec`, `403` `side-effects-forbids-invocation` | 03 §8.1, §4.1; 10 §7.3 |
| 7 | The caller's `fathom.agent.authority` permits the live class; `accountable_autonomous` requires a resolvable accountable owner | `403` `agent-authority-insufficient`, `403` `accountable-owner-missing` | 03 §8.3 |
| 8 | Arguments validate against the **live** operation's parameter and request-body schemas, not only against the descriptor's `inputSchema`; `Idempotency-Key` present where the live class is `proposal-only` | `422` `input-schema-drift`, `400` `idempotency-key-required` | 03 §4, §4.1; 09 §8.1 |
| 9 | The pre-invocation audit record is durably accepted by `audit` | `503` `audit-record-incomplete` | 03 §8.5 |

### 4.3 Gate 6 in full — the live re-validation

This is the gate that a stale cached claim would otherwise defeat, so it is specified exhaustively.

**The rule is called with the same function the generator calls.** `fathom_agent_tooling.eligibility.assess(spec, operation_id)` (document 10 §7.3) is imported and invoked against the **live** document. It returns an `EligibilityVerdict` whose `reason` is one of `ABSENT`, `NOT_ELIGIBLE`, `STATE_CHANGING`, `NO_DESCRIPTION`, and the service maps those four onto problem types one-to-one. Document 10 §7.3 calls that module *"the ONLY place in the package that decides whether an operation may be selected"*; this service does not become a second place. A locally written re-check would be a copy that must be kept in step with a module owned by another package and another wave, and the observable direction of that drift is permissive — a local copy silently keeps allowing what an updated rule has started to forbid.

Note what `assess` gives for free by construction: it **never looks at the HTTP method**. Findings C1 and D11 are that a method check makes `pdm-whatif` unbuildable, since every operation it needs is a `POST`. Reusing `assess` means the call-time gate cannot reintroduce that defect even by accident.

**The comparison `assess` cannot make.** `assess` answers *"may this operation be selected at all, against this document?"* It knows nothing about the descriptor. The tool server adds exactly one comparison:

```
live_class = live_spec.operations[operation_id]["x-side-effects"]
if live_class != descriptor.x_fathom_side_effects:
    reject 409 urn:fathom:problem:tool-server:side-effects-mismatch
```

**Mismatch in either direction is a rejection.** Escalation (`none` → `state-changing`, `none` → `proposal-only`) is obviously fatal. Relaxation (`proposal-only` → `none`) is also fatal, and the reasoning is not symmetry for its own sake:

- The descriptor's task-scoped description and `x_fathom_result_projection` were written against the recorded semantics. Document 03 §8.4 requires each manifest's conformance test to assert *"descriptions accurately characterize returns"*; a class change is a semantic change, and 03 principle 5 puts semantic changes behind a major version. A descriptor whose recorded class no longer matches is, by that principle, a descriptor written against a version that no longer exists.
- More importantly, a mismatch is evidence about the **whole descriptor**, not about one field. It can only mean that the committed descriptors were not regenerated after a spec change (so `check-generated` was bypassed), or that the deployed service is not serving its committed spec (so `check-committed` was bypassed), or that a substituting implementation mid-migration declares the operation differently from the incumbent (03 §10). In all three conditions, no other field of that descriptor — its `inputSchema`, its projection, its authority annotation — has any better standing than the field that was caught. Proceeding on the rest of a descriptor that has been demonstrated wrong in one place is the reasoning error, not the strictness.

**What must not happen on mismatch.** No silent proceed. No downgrade-and-continue. No "reject only if the live class is `state-changing`." No serving the call from the cached descriptor because the live document "looks wrong." No auto-regeneration of the descriptor from the live spec — that would let a sub-application widen an agent's reach by editing its own annotation, which inverts document 03 §8.1's two-level model, where selection is the *consuming agent's* decision and eligibility is the *sub-application's* assertion, and neither may perform the other's act.

**What must happen on mismatch, besides the rejection.** `fathom_tool_side_effects_mismatch_total{slug,operation_id,recorded,live}` increments, and any nonzero value is an alerting condition, not a dashboard curiosity: it means a specification and a committed descriptor are out of step in production. The rejection is recorded to Audit as a completed invocation with outcome `rejected` and the reason code, because a blocked attempt to call a state-changing operation with a stale eligibility claim is precisely the event an accreditor will ask whether the system can detect (03 §8.5, 04 §11).

### 4.4 Gate 8 — argument validation against the live schema

The descriptor's `inputSchema` is a generation-time derivative (10 §7.4: derived from the operation's parameters and request body, with `parameter_defaults` applied as schema `default` keywords and defaulted parameters removed from `required`). It is what the agent was shown. It is not authority.

Arguments are validated against the live document's parameter and request-body schemas. A divergence between the two — a parameter that no longer exists, a narrowed type, a newly required field — is `422` `input-schema-drift` and is **not** repaired by dropping the offending argument. Silently discarding an argument an agent supplied changes the meaning of the call the agent made, and document 03 §9 item 1 requires that no retrieved or supplied content alter tool behavior implicitly.

Manifest `parameter_defaults` are applied as recorded in the descriptor, then validated the same way. Document 03 §8.4 already requires the manifest conformance test to assert defaults *"are valid"* against the live operation; this gate is that assertion moved to the call site, where it also catches the case of a default that satisfies the schema and is rejected at runtime — which document 10 §6.8 names as the actual failure mode.

### 4.5 Gate 7 and token attachment

Document 03 §8.3's two classes bind here without modification.

| Class | Token attached to the proxied call | Cap enforced here |
|---|---|---|
| **Delegated** | The caller's own delegated token, forwarded unchanged | Reach is bounded by the user's authorization, evaluated by the **receiving** sub-application (03 §4 Authorization, obligation 7). This service narrows; it never widens |
| **Accountable autonomous** | The caller's scoped short-lived workload identity, forwarded unchanged, with the named accountable owner carried into the audit record | Live class must be `none` or `proposal-only`. Cannot reach outside the binding's declared scope |

Three prohibitions, each with its failure scenario:

1. **Never mint, exchange, elevate, or substitute a credential.** The proxied call carries the caller's identity, full stop. A service identity substituted for an expired delegated token would make every downstream ABAC decision (obligation 7) evaluate the wrong subject, and would produce an audit record naming a workload where a human belongs.
2. **An expired or near-expired delegated token is a distinct, non-retryable condition.** Document 03 §8.3: an agent whose token expires *"terminates and records a resumable checkpoint. It does not silently continue under a service identity, and it does not create a proposal after its authority has lapsed."* The service therefore rejects with `401` `delegated-authority-lapsed` — a problem type deliberately distinct from a generic `401` so the runtime can checkpoint rather than back off and retry. A refusal margin (`FATHOM_TOOL_SERVER__TOKEN_REFUSAL_MARGIN_SECONDS`, measured monotonically) rejects a token that would expire mid-call rather than starting work that cannot legitimately finish. Document 02 §4.1 records Domino's extended identity propagation as defaulting to eight hours, so for a Domino-hosted interactive agent this is a routine daily event, not a corner case.
3. **`accountable_autonomous` with no resolvable accountable owner is a rejection, not a warning.** Document 03 §8.3 requires *"a named accountable human owner"* and *"every run recorded to Audit with the accountable owner."* An unattributable autonomous run is exactly the artifact the class exists to prevent.

**Do not confuse these classes with document 03 §7.2.1's.** §7.2.1 (`maintainer`, `planner`, `supply_officer`, `design_authority`, `fleet_authority`) governs which **human organizational role** may adjudicate a proposal given its `kind` and `blast_radius`, and its own opening line makes the separation explicit: *"This is distinct from the agent authority classes in §8.3."* This service enforces §8.3 and has no opinion about §7.2.1 — the `authority_class` on a `Proposal` is set and re-validated by the owning sub-application (03 §7.2.1), reached through a `proposal-only` tool call like any other write. Note that document 10's **OQ-13** recorded the §7.2.1 vocabulary as undefined and called it *"the most consequential gap in the package"*; §7.2.1 now defines it, so OQ-13 is closed against document 03 and document 10's open-question table is stale on that row. Nothing in this service changes as a result, which is the point of keeping the two vocabularies apart.

### 4.6 Gate 9 and completion — recording to Audit

Document 03 §8.5: *"Tool invocations, with full request and response, are recorded to Audit & Provenance and correlated to the Domino trace by `trace_ref`."*

**`DECISION` — two-phase, and the first phase is a gate.** An invocation that cannot be recorded does not occur.

1. **Before proxying**, the service writes an `attempted` record: `agent_id`, `agent_version`, `authority_class`, `accountable_owner` where applicable, `trace_ref`, `X-Correlation-Id`, `bundle_digest`, the tool `name`, `x_fathom_manifest` (name/version/owner), `x_fathom_target` (slug/api_major), the resolved operation, the live spec `ETag` and its measured age, the full arguments, and the outcome of every gate. If `audit` does not accept it, the call is rejected `503` `audit-record-incomplete` and **the target is never contacted.**
2. **After the proxied call returns** — or times out, or is rejected — a completion record carries the full response body, the status, and the outcome (`succeeded` | `rejected` | `target_error` | `timed_out`). If the completion write fails, it retries with bounded monotonic backoff; on exhaustion, the agent receives `502` `audit-record-incomplete` and the `attempted` record remains in the append-only store visibly incomplete. An observable gap is the correct outcome; a discarded record is not.

Rejections at gates 1–8 also produce a completed record. A design in which only successful calls are recorded cannot answer the question that matters most — *did an agent try to call something it should not have?*

The volume argument for accepting two audit writes per invocation is document 06 §7's, not an assumption: three agents in the demonstration, fewer than twenty agent proposals per day. No tool-call rate is published there, so no rate is invented here — the two-write cost is recorded as a scaling item at production fleet size (**OQ-5**).

### 4.7 Result handling and projection

The target's response is returned to the agent after `x_fathom_result_projection` is applied — the RFC 6901 pointers document 10 §7.4 records. Two cases that look alike and are not:

| Case | Behavior | Why |
|---|---|---|
| A pointer does not resolve **in the response instance** | The field is **omitted**. Not an error | This is the normal, correct case. `pdm-whatif` projects both `/rul` and `/population_hazard_rate`, and document 03 §7.1 requires `rul` to be **absent** where `reference_class` is not item-conditional (**D19**). Treating an absent optional field as an error would break the manifest document 03 §8.2 names |
| A pointer does not resolve **against the live response schema** | `409` `result-projection-schema-drift` | The response shape has changed under a descriptor that claims otherwise. Document 03 §8.4 requires *"result projections match response schemas"*; this is that requirement at the call site |

The service does not reshape, summarize, rank, or annotate a result beyond the recorded projection. It does not add a natural-language wrapper. Document 03 §9 item 1 requires that tool results reach an agent as data that is structurally separated from instruction; a proxy that editorializes is inserting instruction into a result channel.

`X-Classification` from the target is propagated to the agent unchanged, and never widened. Redaction is the target's act (03 §4, §7.3).

### 4.8 The enforcement path, as code

Ordering and failure semantics only. The types come from `packages/agent-tooling`; nothing here reimplements them.

```python
# platform/tool-server/src/fathom_tool_server/services/invoke.py
#
# THE ORDER OF THESE CHECKS IS LOAD-BEARING.  DO NOT REORDER, MERGE, OR
# SHORT-CIRCUIT.  [03 §8.1, §8.3, §8.4, §8.5]
#
# Nothing is proxied, and no audit record is completed, until every gate passes.
# The most important line in this function is the `!=` in gate 6: the descriptor
# was generated against a specification that may no longer be the specification
# the target is serving, and a cached `x-side-effects: none` on an operation that
# has since become state-changing is the one way this service could let an agent
# change domain state.  A mismatch is a REJECTION, in either direction.

from fathom_agent_tooling.eligibility import Ineligibility, assess

async def invoke(req: ToolCall, principal: Principal) -> ToolResult:
    principal.assert_valid_and_unexpired()                       # gates 1-2
    binding = bundle.binding_for(principal.agent_id)              # gate 3
    descriptor = binding.descriptor_for(req.tool_name)            # gate 4  (pin: name+version+slug+api_major)

    live = await spec_cache.get_fresh(descriptor.x_fathom_target) # gate 5  (raises SpecCacheStale)

    verdict = assess(live.document, descriptor.x_fathom_operation_id)   # gate 6a — THE SAME FUNCTION CI USES
    if not verdict.eligible:
        raise Rejected(_PROBLEM_FOR[verdict.reason], verdict.detail)

    live_class = live.side_effects_of(descriptor.x_fathom_operation_id)
    if live_class != descriptor.x_fathom_side_effects:            # gate 6b — the comparison assess() cannot make
        raise Rejected(
            "side-effects-mismatch",
            f"descriptor recorded {descriptor.x_fathom_side_effects!r}; "
            f"{descriptor.x_fathom_target['slug']} v{descriptor.x_fathom_target['api_major']} "
            f"now declares {live_class!r} for {descriptor.x_fathom_operation_id!r}.  "
            "Document 03 §8.1: the descriptor was generated against a specification "
            "that is no longer the one being served.  Regenerate; do not proceed.",
        )

    principal.assert_may_invoke(live_class)                       # gate 7  (03 §8.3 cap + accountable owner)
    args = live.validate_arguments(descriptor, req.arguments)     # gate 8  (live schema, not inputSchema)

    record = await audit.attempted(...)                           # gate 9  — fails closed
    try:
        response = await proxy.call(live.operation(descriptor), args, principal)  # §5
    finally:
        await audit.complete(record, ...)                         # always, including on rejection
    return project(response, descriptor.x_fathom_result_projection)              # §4.7
```

---

## 5. Proxying to the target sub-application

### 5.1 Through the gateway, in pass-through mode

**`DECISION`.** The tool server does not hold a direct network edge to any of the nine sub-applications. It calls `gateway`, which forwards to the target.

The reasoning is document 09 §4.4.2's own, applied consistently. That table sanctions `gateway → any of the nine, plus tool-server, knowledge-retrieval, notification`, and sanctions `domino-compute → gateway` with the stated rationale that scoring jobs *"route through the gateway so PdM keeps a single ingress and the caller's workload identity is attached at one place. The alternative — a direct `domino-compute` → `pdm` rule — is rejected because it would need repeating for every future batch producer."* A tool server holding nine direct edges is that rejected shape with nine rules instead of one, and it would make the tool server a second ingress to every sub-application. Routing through the gateway also inherits what the gateway already owns per 04 §11: token exchange for delegated authority, and rate limiting per caller identity — both of which a tool call needs and neither of which should be built twice.

Two consequences that must be honored:

- **Document 09 §4.4.2's sanctioned-edge table needs one new row, `tool-server → gateway`.** It is absent today. Per document 09 §9 item 30 that requires a change to document 09 plus an ADR. Recorded in §15.
- **The gateway must serve `/api/v1/<slug>/…` in pass-through mode, not BFF composition mode.** The tool server needs the target operation's own response, unmodified, because §4.7's projection pointers are RFC 6901 pointers into *that* schema. A composed view model would break every projection in every manifest. This is a requirement on the gateway's own build document, flagged in §15.

The live-spec fetches of §2.5 take the same path, for the same reason.

### 5.2 The operation mapping

The descriptor records `x_fathom_target` (slug, api_major) and `x_fathom_operation_id`. The concrete method and path come from the **live** document by `operationId` lookup — never from a path recorded in the descriptor.

This is deliberate and document 10 §7.2 supplies the reason for using `operationId` at all: *"an operationId survives a path change."* Under document 03 §4 the base path is `/api/v1/{slug}/…` and the major version is in the path, so a within-major path change is legal and additive. Recording a resolved path in the bundle would make the bundle wrong the first time that happened; resolving through the live document makes a path change invisible to the manifest and a *removal* a gate-6 rejection.

### 5.3 Headers on the proxied call

| Header | Value |
|---|---|
| `Authorization` | The caller's own token, forwarded unchanged (§4.5) |
| `X-Correlation-Id` | The correlation ID of the tool call, propagated per 03 §4 so the target's log lines, events, and downstream calls all join up |
| `Idempotency-Key` | The agent's key, forwarded verbatim (§5.4) |
| `If-Match` | Forwarded where the agent supplied it. The tool server never synthesizes one: a synthesized `If-Match` would defeat the lost-update protection of 03 §4 and finding **D16** |
| `X-Backfill` | **Never set.** 03 §5.3 reserves it for bulk historical load; an agent-originated call is not a backfill |

### 5.4 Idempotency is forwarded, never consumed

**`DECISION`.** The tool server implements no local idempotency cache, and this is a deliberate departure from document 09 §5.3's shared middleware for this one service.

Document 09 §8.1 requires `Idempotency-Key` on every `state-changing` and `proposal-only` operation. Since the eligibility gate caps a tool call at `proposal-only`, an agent's tool call can create a proposal — and document 03 §7.2's whole safety argument depends on the *owning sub-application* deciding whether a retry is the same act. If the tool server answered a retry from its own cache, the target would never see the second attempt, and the target's claim-and-`If-Match` fencing (D16) would be reasoning about a call history it cannot see. So: the key is required (gate 8) and forwarded (§5.3), and the target decides.

The tool server also never **mints** a key on the agent's behalf. A freshly minted key per attempt defeats idempotency outright; a deterministically derived key silently defines equivalence semantics for someone else's operation. Absence on a `proposal-only` call is `400` `idempotency-key-required`.

### 5.5 The tool server never calls a Domino Endpoint

Document 03 §8.3 and 01 §8.5 require that Domino Endpoint calls be proxied by a Sustainment Plane service that attaches caller identity, *"because a Domino Endpoint authenticates with a static token carrying no caller identity and no per-caller audit trail"* (02 §4.3). That obligation is satisfied here for **tool calls**, and it does not make the tool server a Domino client.

The interaction that tempts otherwise is `pdm-whatif`, whose interactive tier-3 analysis is Endpoint-backed per 01 §7. But document 01 §7 also fixes the boundary: predictions are read *from PdM, never from Domino*, and `pdm_what_if` is a PdM operation carrying `x-side-effects: none`. The Endpoint hop is PdM's private business, inside PdM's own trust boundary, and PdM attaches caller identity to the audit record on that hop. Every descriptor's operation mapping therefore resolves to a sub-application REST operation, always. A descriptor mapping to a Domino Endpoint URL is malformed and the bundle compiler rejects it.

### 5.6 Deadlines

Per-target deadline from configuration, measured on a **monotonic** clock (03 §5.4, **D29** — a wall-clock deadline storms or hangs the instant a STIG-mandated backward step lands). On expiry: `504` `target-timeout`, audit outcome `timed_out`, never reported to the agent as an empty success.

The deadline must be set **above** the target's own declared timeout budget. Document 02 §4.3 records that a timed-out Domino Endpoint request *"is not cancelled and continues to occupy its worker"*, so abandoning an Endpoint-backed call early consumes the target's capacity while returning nothing. Document 06 §7 publishes operator-view latency budgets (p95 < 1.5 s for fleet and asset views, < 4 s for explanation decomposition) but no tool-call budget, so no value is invented here — **OQ-3**.

---

## 6. How a newly generated manifest becomes callable

### 6.1 The decision

**`DECISION` — activation is a deployment. There is no hot reload, no polling of a manifest registry, and no runtime fetch of a descriptor.** A pod serves exactly one bundle for its entire life, identified by `bundle_digest`, and a new bundle reaches production only as a new image digest synced by Argo CD.

The pipeline, entirely within document 09 §6's existing jobs:

1. A manifest changes under `packages/agent-tooling/manifests/<slug>/`, or a pin changes under `agents/<name>/tool-pins.yaml`.
2. Document 09 §6.2 job 9 (`make manifests`) regenerates descriptors and **fails, never warns** (03 §8.2; 10 §7.5).
3. `make check-bundle` recompiles `bundle.v1.json` and diffs against the committed copy; the four B-rules of §2.2 are hard failures.
4. On merge, document 09 §6.3 builds and pushes the image with the bundle baked in, records the digest, and a bot commit writes it into `deploy/argocd/environments/dev/values.yaml`.
5. Argo CD syncs `dev` automatically; staging and production are manual sync inside a sync window (09 §6.3 item 5).

**Path filters must include `packages/agent-tooling/generated/**` and `agents/*/tool-pins.yaml` in the tool-server image job.** Document 09 §6.2 scopes jobs by changed service, so without this a manifest-only change would regenerate descriptors and never ship them — the pipeline would be green and the deployment stale. This is the single most likely wiring error in the whole document.

### 6.2 Why, against the stack in document 09

| Alternative | Rejected because |
|---|---|
| **Hot reload from a mutable manifest registry** | It makes the set of callable tools mutable without a deployment record. Document 01 §11 keeps Argo CD partly because it *"supplies the record of what was deployed and when, which is relevant to accreditation"*, and document 01 §9 already had to adopt the fallback that *"pin enforcement is implemented in the program's own promotion pipeline"* because Domino's governance *"gates act on creation only"* and is *"opt-in per asset"* (02 §4.4). A hot-reload path would hand back exactly the property that fallback was adopted to recover |
| **Polling the internal package index at startup or on an interval** | Document 01 §12 and finding **D26**: nothing is fetched or installed at container start. Document 02 §4.1 records Domino's own runtime package installation as *"categorically incompatible with air gap, with no workaround"*, and document 09 §9 item 25 generalizes it. A registry poll is the same defect wearing different clothes, and it makes a running pod's tool surface depend on network reachability at an arbitrary moment |
| **A ConfigMap of descriptors with a file watcher** | Decouples the descriptor set from the image digest, so promotion by digest (09 §6.3 item 1) no longer promotes the thing being served. It also puts the whole bundle under the 1 MiB ConfigMap ceiling, which nine slugs' descriptors will not respect for long |
| **Generating descriptors in-process from the live spec** | Directly forbidden. Document 03 §8.1's two levels: selection is the consuming agent's decision recorded in a reviewed, owned, versioned manifest; runtime generation would let a spec change silently alter an agent's tool set without a manifest version, a review, or a promotion. It would also invert §4.3's entire argument — there would be no independent recorded claim left to compare the live spec against |

### 6.3 What this costs, stated honestly

A manifest-only fix requires a tool-server image build and an Argo CD sync. In exchange, three properties hold that no reload mechanism preserves: the callable tool set at any instant is derivable from a git commit and an image digest; a rollback is a digest change with no separate manifest state to unwind; and an air-gapped enclave needs no additional distribution channel beyond the image it already receives. Given three agents in the demonstration (06 §7), the change rate does not justify trading those away.

**During a rolling deployment two bundles serve concurrently.** This is safe and requires no coordination, because §4.2 gate 4 checks the agent's pin against the bundle the *serving pod* holds: an agent whose pin exists only in the new bundle is rejected by an old pod with `manifest-pin-superseded` rather than served something adjacent. Both the discovery response and every audit record carry `bundle_digest`, so which pod answered is always recoverable. `DECISION` — a rejection during a rollout is preferable to a best-effort match, and agent runtimes should treat `manifest-pin-superseded` as retryable-once rather than fatal.

---

## 7. Third-party tool development

Document 01 §8.0 makes an explicit claim: *"third parties can develop tools against these sub-applications without program involvement"*, and document 03 §8.5 restates it: *"Because manifests generate from published contracts, third parties may develop tool surfaces against these sub-applications without program involvement."* Document 01 §8.0 also draws the line: *"this readiness is program intellectual property rather than platform-provided function."*

This service must therefore support the claim without becoming the mechanism a third party calls.

| Artifact | Disposition | Reasoning |
|---|---|---|
| The OpenAPI 3.1 documents, with `x-substitution`, `x-side-effects`, and `x-agent-eligible` | **Publishable** | 03 §15 obligation 1. These are the *only* input a third-party manifest needs. Everything else follows |
| The manifest schema — the five fields of 03 §8.2 | **Publishable, and stable** | Document 10 §7.2 states the reason: a sixth field *"would be a private extension to a published artifact"*, and third-party generation *"requires the manifest format to be as published and as stable as the OpenAPI document"* |
| The `McpToolDescriptor` shape, including the `x_fathom_*` extension vocabulary | **Publishable** | A third party generating descriptors that a program tool server could serve needs the field set. Publishing it also makes the governance extensions legible rather than proprietary |
| The generator's failure semantics — exit codes 10–21 | **Publishable** | A third party should fail on the same conditions. Publishing the table is cheaper than answering the question repeatedly |
| The conformance suite (03 §10, 10 §6) | **Publishable** | Already required for substitution. Document 01 §8.0: *"substitution-safety and tool-safety are the same property"*, and the manifest tests of 10 §6.8 run inside it |
| **This service's discovery and invocation endpoints** | **Program-internal** | Not part of any published contract. `x-substitution: internal` on every operation |
| **The binding table** — which agent holds which pin, and each accountable owner | **Program-internal** | It is the authority model. Publishing it publishes the reach of every agent |
| **Audit correlation, `trace_ref` linkage, the invocation ledger** | **Program-internal** | An accreditation artifact (04 §11) |
| **The `/mcp` endpoint** | **Program-internal** | Reachable only by a bound caller |

Three rules follow, and they are what keep the claim honest:

1. **A third party generates its own descriptors and, if it wants one, runs its own tool server.** Nothing in the program is required, and nothing in the program is exposed. This is exactly the readiness 01 §8.0 describes.
2. **A third party is not a caller of this tool server unless bound.** There is no anonymous discovery, no public `tools/list`, and no self-service registration. Discovery is scoped by binding (§3.2), a binding is a reviewed GitOps change to `agents/*`, and a third party holding one is by definition program-authorized. Note also that document 02 §4.1 records Domino removing anonymous access platform-wide; an anonymously discoverable program tool surface would be a stranger posture than the platform's own.
3. **Third-party tooling is safe because authority does not come from the tool server.** A third party's agent authenticates as an ordinary OIDC client and is bounded by the receiving sub-application's ABAC evaluation (03 §4, obligation 7: *"Never delegated to the gateway alone"*). Its manifest can select only operations the sub-application itself marked eligible (03 §8.1), and it can reach only what its subject is authorized to reach. That is the property that makes publishing the contracts an acceptable act.

Whether the OpenAPI documents are *actually* released outside the program is a program decision this document does not make. The annotations describe Navy sustainment operations, document 03 §12 states the demonstration is single-level unclassified while production is not, and document 03 §7.3 puts distribution statements and dissemination controls on the artifacts themselves. Recorded as **OQ-6**.

---

## 8. API surface

### 8.1 Operations

Base path `/api/v1/tool-server/` per document 03 §4 and finding C25. Every operation is generated from FastAPI into a committed `openapi.json` (09 §2.5).

| Operation | `operationId` | `x-side-effects` | `x-substitution` | Notes |
|---|---|---|---|---|
| `GET /tools` | `tool_server_list_tools` | `none` | `internal` | Discovery, scoped by binding (§3.2). Cursor-paginated, `ETag` over `bundle_digest` + `agent_id` |
| `GET /tools/{tool_name}` | `tool_server_get_tool` | `none` | `internal` | One descriptor, as served to this caller |
| `POST /tools/{tool_name}/invoke` | `tool_server_invoke_tool` | `proposal-only` | `internal` | The proxy (§4, §5). `Idempotency-Key` required |
| `GET /bindings/{agent_id}` | `tool_server_get_binding` | `none` | `internal` | The effective binding, for operator and audit visibility. **Read-only: there is no write operation** |
| `GET /descriptor-bundle` | `tool_server_get_descriptor_bundle` | `none` | `internal` | `bundle_digest`, image digest, generation commit, per-manifest versions, per-target `api_major` |
| `GET /target-specs` | `tool_server_list_target_specs` | `none` | `internal` | Per-target live-spec cache state: `ETag`, monotonic age, verdict (`fresh` \| `stale`) |
| `POST /mcp` | `tool_server_mcp_jsonrpc` | `proposal-only` | `internal` | The JSON-RPC adapter (§3.1). Carries `x-fathom-protocol: mcp-jsonrpc` and a naming carve-out note |
| `/healthz`, `/readyz`, `/metrics` | — | — | — | From `py_common` (09 §5.6), with §10's check set |

**No operation on this service ever declares `x-agent-eligible`.** The tool server is not itself a tool. There is a pleasing existing guard: `ToolManifest.target.slug` is typed `ToolTargetSlug` (10 §7.2) — **[AMENDMENT]** widened from `SubAppSlug` alone to also admit `knowledge-retrieval` and `reference-data`, but `tool-server` (along with `auth`, `audit`, `gateway`, `sync`, and `notification`) remains deliberately excluded from that wider union — so the manifest schema still makes a manifest targeting this service unrepresentable. `invoke` declares `proposal-only` rather than `none` because that is the maximal class it can reach — the eligibility gate caps targets there — and understating it would be exactly the mis-declaration `OAS004` exists to catch.

`x-substitution: internal` on all of them, per 03 §10: a substituting partner assumes a *discipline* and its contract, and this service is program infrastructure, not a discipline.

### 8.2 Problem types

`urn:fathom:problem:tool-server:<code>`, RFC 9457, declared in `schemas/problems.py` and present in the spec's `responses` (09 §8.1). `detail` is never used for control flow (03 §4).

| Code | Status | Raised by |
|---|---|---|
| `invalid-token` | 401 | Gate 1 |
| `authority-class-missing` | 422 | Gate 1 |
| `delegated-authority-lapsed` | 401 | Gate 2 — **distinct so the runtime checkpoints instead of retrying** (03 §8.3) |
| `no-manifest-binding` | 403 | Gate 3 (§3.2) |
| `tool-not-in-pinned-manifest` | 403 | Gate 4 |
| `manifest-pin-superseded` | 409 | Gate 4 — retryable once during a rollout (§6.3) |
| `api-major-pin-unsatisfiable` | 409 | Gate 4 |
| `spec-cache-stale` | 503 | Gate 5 (§2.5) |
| `operation-absent-from-live-spec` | 409 | Gate 6a — `Ineligibility.ABSENT` |
| `operation-not-agent-eligible` | 403 | Gate 6a — `Ineligibility.NOT_ELIGIBLE` |
| `side-effects-forbids-invocation` | 403 | Gate 6a — `Ineligibility.STATE_CHANGING` |
| `operation-lacks-description` | 409 | Gate 6a — `Ineligibility.NO_DESCRIPTION` |
| `side-effects-mismatch` | 409 | **Gate 6b — §4.3** |
| `authority-class-insufficient` | 403 | Gate 7 |
| `accountable-owner-missing` | 403 | Gate 7 |
| `input-schema-drift` | 422 | Gate 8 (§4.4) |
| `idempotency-key-required` | 400 | Gate 8 (§5.4) |
| `audit-record-incomplete` | 503 / 502 | Gate 9 / completion (§4.6) |
| `result-projection-schema-drift` | 409 | §4.7 |
| `target-timeout` | 504 | §5.6 |
| `target-unavailable` | 502 | §5 |
| `descriptor-bundle-unavailable` | 503 | Bundle failed to load — the service is also not ready |

Problem `type` URIs are `urn:`, never `https:`, per document 09 §9 item 26 — a dereferenceable type would be a public-internet call at runtime.

---

## 9. Events

**The tool server publishes no events and consumes no topic.** Document 03 §6's catalog assigns it no aggregate, and document 03 principle 1 defines the contract as *"the API plus the published events plus the conformance suite"* — inventing a topic for a platform service would add a contract term to a catalog document 03 owns.

It is also not a topic consumer, and that is the same rule finding **C19** produced: *agents are never direct event consumers; agents obtain state through tools* (03 §6; 09 §9 item 15). This service is the component that bridges agents to state, and it bridges by proxying tool calls. A tool server that consumed topics would be a read model in the one place the architecture forbids one, and would give an agent an event-shaped back channel around the eligibility gate.

The durable record of what happened is Audit's (§4.6), which is stronger than an event for this purpose: append-only, integrity-controlled, and already the designated accreditation artifact.

Whether `tool_invocation` should nonetheless become a catalogued event — for `notification` escalation on repeated `side-effects-mismatch`, say — is **OQ-4**. The position taken here is against it: it would create a second, weaker copy of an accreditation artifact, carrying full request and response payloads through a broker with its own classification and retention posture (03 §5.1, §12). Escalation is better served by the alert on `fathom_tool_side_effects_mismatch_total` (§10).

---

## 10. Observability

### 10.1 Metrics

Following document 09 §5.6's fixed naming.

```
fathom_tool_discovery_requests_total{agent_id,outcome}
fathom_tool_invocations_total{agent_id,tool_name,outcome}          # outcome=succeeded|rejected|target_error|timed_out
fathom_tool_invocation_duration_seconds{tool_name}                 # histogram, monotonic-clock measured
fathom_tool_rejections_total{agent_id,tool_name,reason}            # reason == the §8.2 problem code
fathom_tool_side_effects_mismatch_total{slug,operation_id,recorded,live}
fathom_tool_spec_cache_age_seconds{slug,api_major}                 # gauge, monotonic
fathom_tool_spec_fetch_total{slug,api_major,outcome}               # outcome=fresh|not_modified|failed
fathom_tool_audit_write_failures_total{phase}                      # phase=attempted|completed
fathom_tool_bundle_info{bundle_digest,image_digest}                # gauge, always 1
```

**`fathom_tool_side_effects_mismatch_total` alerts on any nonzero increase.** It is not a rate to watch; a single occurrence means a deployed specification and a committed descriptor disagree in production, which is one of the three conditions §4.3 enumerates, all of which are release-process failures. `fathom_tool_rejections_total{reason="tool-not-in-pinned-manifest"}` alerts on a sustained rate: an agent repeatedly asking for a tool outside its pin is either a stale agent artifact or a prompt that has drifted from its manifest.

### 10.2 Readiness

`/healthz` is process-local and consults nothing (09 §5.6). `/readyz` aggregates:

| Check | Fails readiness when |
|---|---|
| `bundle` | `bundle.v1.json` absent, digest mismatched against `bundle.sha256`, or any descriptor failing to parse as `McpToolDescriptor` |
| `bindings` | Any B1–B4 violation detectable at load (§2.2) |
| `auth` | JWKS unreachable — no token can be validated, so no call can be authorized |
| `audit` | Unreachable — gate 9 fails closed, so invocation is unavailable. This is a genuine outage of the primary function |
| `gateway` | Unreachable — no target is reachable |
| `spec_freshness` | **Only when every target is stale.** Per-target staleness is reported `degraded` in the breakdown and fails closed at the call site |

The `spec_freshness` row is a **deliberate deviation** from document 09 §5.6's read-model-lag rule, which makes a single stale projection fail the whole service. The argument for the deviation: this service has nine independent targets rather than one read model, and removing the pod from service would not repair a stale target — it would only remove the enforcement point that is at that moment correctly rejecting calls against it, while also taking down the other eight targets and all discovery. Per-target fail-closed preserves the safety property with a smaller blast radius. Recorded as an ADR item (§16) and as **OQ-1**'s companion.

---

## 11. Testing

Document 09 §4.7's layering applies. Beyond it, the tests below exist because each catches a specific way this service could let an agent call something it should not. **Each is a positive test that a defect is detected**, in the manner of document 10 §12.5's exemplar variants — a suite that only ever passes against a correct target has never been shown to discriminate.

### 11.1 The fake-target harness

`platform/tool-server/tests/fixtures/target/` is a minimal FastAPI service serving a real OpenAPI 3.1 document, with variants that mutate it **after** the descriptor was generated against it. This is the only way to test §4.3 honestly.

| Variant | Mutation | Test asserts |
|---|---|---|
| `target-good` | none | Every gate passes; the call proxies; both audit records written |
| `target-escalated` | `x-side-effects` flips `none` → `state-changing`; `x-agent-eligible` dropped | `409 side-effects-mismatch`; **and no outbound request to the target** |
| `target-relaxed` | `proposal-only` → `none` | `409 side-effects-mismatch`. Relaxation is a rejection too (§4.3) |
| `target-eligibility-dropped` | class unchanged, `x-agent-eligible` removed | `403 operation-not-agent-eligible` |
| `target-operation-removed` | `operationId` removed at the same major | `409 operation-absent-from-live-spec` |
| `target-path-moved` | path changes, `operationId` unchanged | **Succeeds.** `operationId` resolution survives a path change (§5.2) |
| `target-param-narrowed` | a parameter type narrows | `422 input-schema-drift`; the argument is not silently dropped |
| `target-response-reshaped` | a projected field removed from the response **schema** | `409 result-projection-schema-drift` |
| `target-optional-absent` | projected optional field absent from the **instance** (`/rul` on a non-item `reference_class`) | **Succeeds**, field omitted. The **D19** case (§4.7) |
| `target-slow` | exceeds the deadline | `504 target-timeout`; audit outcome `timed_out`, never `succeeded` |

### 11.2 The two mandated tests, named

```python
# platform/tool-server/tests/enforcement/test_call_time_gates.py
#
# Every test in this module is parametrized over BOTH surfaces — the REST
# operation and the /mcp JSON-RPC method — because §3.1 requires one
# enforcement path and the JSON-RPC adapter is the surface no contract test
# naturally covers.  A hole introduced there would be invisible otherwise.

@pytest.mark.parametrize("surface", ["rest", "mcp"])
def test_superseded_manifest_pin_is_rejected_at_call_time(surface):
    """03 §8.4.  An agent artifact pins BOTH manifest version and API major.

    The generator checked the pin at generation time.  That is a statement about
    the past.  Here the agent presents a valid token, a well-formed call, and a
    pin whose (name, version) is not in the SERVING pod's bundle — a rolled-back
    agent, or an old pod mid-rollout.  Asserts 409 manifest-pin-superseded, and
    asserts respx recorded NO outbound call: the target must never be contacted
    on a failed pin check.
    """


@pytest.mark.parametrize("surface", ["rest", "mcp"])
def test_side_effects_changed_since_generation_is_rejected(surface):
    """THE CENTRAL TEST OF THIS SERVICE.  03 §8.1, §4.1  [C1, D11].

    The cached descriptor records x_fathom_side_effects == "none".  The target
    now serves x-side-effects == "state-changing" for the same operationId.
    The descriptor is otherwise perfectly valid and was generated by a clean CI
    run.  Asserts:

      1. 409 urn:fathom:problem:tool-server:side-effects-mismatch
      2. NO outbound request to the target  (the state change must not occur)
      3. fathom_tool_side_effects_mismatch_total incremented with
         recorded="none", live="state-changing"
      4. an audit record exists with outcome "rejected" and the reason code —
         a blocked call is exactly what an accreditor asks whether we detect
      5. the descriptor on disk is UNCHANGED: the service does not "repair"
         a descriptor from the live spec (§4.3, §6.2)
    """
```

### 11.3 The rest of the enforcement suite

| Test | Asserts |
|---|---|
| `test_discovery_excludes_tools_outside_the_pin` | Two agents bound to different manifests over the same slug see disjoint tool sets |
| `test_unbound_caller_is_403_not_empty_list` | §3.2's argument, mechanically |
| `test_agent_id_is_never_taken_from_the_request` | A caller-supplied `X-Agent-Id` naming another agent is rejected, not honored (§2.3) |
| `test_stale_spec_cache_fails_closed` | Age past the bound ⇒ `503 spec-cache-stale`; the cached descriptor's class is not used as a fallback |
| `test_startup_without_a_target_spec_is_not_ready` | §2.5's last row |
| `test_audit_attempt_precedes_proxy` | With `audit` unreachable: `503`, and respx recorded no outbound call to the target |
| `test_audit_completion_failure_is_visible_not_discarded` | `502 audit-record-incomplete`; the `attempted` record remains, marked incomplete |
| `test_accountable_autonomous_cannot_reach_a_non_eligible_class` | 03 §8.3's cap, as defense in depth behind gate 6 |
| `test_accountable_autonomous_without_owner_is_rejected` | 03 §8.3's *"named accountable human owner"* |
| `test_expired_delegated_token_yields_its_own_problem_type` | `delegated-authority-lapsed`, distinct from a generic `401`, **and** the call is not retried under a workload identity (03 §8.3) |
| `test_idempotency_key_is_forwarded_not_consumed` | The target sees the agent's key; a retry reaches the target (§5.4) |
| `test_no_key_on_proposal_only_is_rejected` | `400 idempotency-key-required` |
| `test_if_match_is_never_synthesized` | **D16** |
| `test_x_backfill_is_never_set` | 03 §5.3, **D30** |
| `test_duplicate_tool_name_in_one_binding_fails_the_compiler` | B3 (§2.2) |
| `test_binding_owner_must_match_or_be_curated` | B2 — 03 §8.2, §8.4 |
| `test_bundle_digest_matches_committed_descriptors` | `make check-bundle`, as a test as well as a CI job |
| `test_no_generation_code_is_importable_at_runtime` | An `import-linter` contract: the service may import `fathom_agent_tooling.{manifest,eligibility,descriptors}` and **may not** import `{generate,overlap,cli,conftest_gen}`. §6.2's last row, made mechanical |
| `test_eligibility_is_not_reimplemented` | Static check: no module in this service reads the string `x-side-effects` or `x-agent-eligible` for a *verdict* except through `assess()`; gate 6b's `!=` comparison is the sole sanctioned direct read |
| `test_mcp_and_rest_produce_identical_verdicts` | The parametrized suite, plus a property test over random gate-failure permutations asserting the two surfaces reject identically with the same problem `type` |
| `test_no_wall_clock_arithmetic` | Ruff `DTZ` clean plus a targeted check that spec age, deadlines, and the token refusal margin use `time.monotonic()`. **D29** |

Schemathesis runs against the committed `openapi.json` per document 09 §2.2. Note what it cannot cover: the JSON-RPC surface is one POST operation to a property-based HTTP fuzzer, which is precisely why §11.2 parametrizes over both surfaces by hand.

---

## 12. Deployment

Document 09 §4's scaffold, minus §2.4's absent pieces.

```
platform/tool-server/
├── bundle/                      # §2.1 — GENERATED, COMMITTED, digest-gated
│   ├── bundle.v1.json
│   └── bundle.sha256
├── openapi.json                 # GENERATED, COMMITTED. CI fails on drift
├── src/fathom_tool_server/
│   ├── main.py                  # create_app(); no local middleware reimplementation (09 §4.6)
│   ├── config.py                # the only reader of the environment (09 §4.5)
│   ├── api/v1/{tools,bindings,bundle,target_specs,health}.py
│   ├── mcp/jsonrpc.py           # adapter ONLY. No enforcement logic (§3.1)
│   ├── bundle/{load,compile}.py # compile runs at build time; load at startup
│   ├── services/
│   │   ├── discover.py          # §3.2
│   │   ├── invoke.py            # §4.8 — the ordered gate
│   │   ├── spec_cache.py        # §2.5
│   │   └── proxy.py             # §5
│   ├── clients/{audit,auth,gateway}.py    # shared httpx factory (09 §2.2)
│   └── observability/{logging,readiness}.py
├── tests/{unit,integration,contract,enforcement,fixtures/target}/
└── helm/…                       # no migration-job.yaml; no database values block
```

No `models/`, `repositories/`, `migrations/`, `events/`, or `readmodels/` directories: each corresponds to a capability §2.4 and §9 remove. Their absence is asserted by a test, so a later contributor adding one has to argue for it.

### 12.1 Chart and boundary

`values.networkPolicy.egress` is exactly:

| Peer | Reason | Sanctioned by |
|---|---|---|
| `kube-dns` | Service discovery | 09 §4.4.2 |
| `auth` | Token validation, JWKS | 09 §4.4.2 (*any service → auth*) |
| `audit` | §4.6 | 09 §4.4.2 (*any service → audit*) |
| `gateway` | §5.1 target proxying and §2.5 spec fetching | **New row required in 09 §4.4.2** — §15 |

Ingress: `gateway` only (09 §4.4.2 already sanctions `gateway → tool-server`), plus the Prometheus scrape. **No database peer. No Redpanda peer.** The helm-unittest assertion that the rendered egress set *equals* the declared set (09 §4.2, §8.6) is therefore also the assertion that this service reaches no broker and no database — a stronger statement than usual, and worth making deliberately.

Otherwise standard: non-root UID 65532, `readOnlyRootFilesystem: true`, `capabilities: drop: [ALL]`, one uvicorn worker per container, HPA on request rate (stateless, so replica scaling is free), base image pinned by digest, nothing installed at container start (09 §4.3, **D26**), Argo CD with `dev` auto-sync and staging/production manual sync.

### 12.2 Configuration

```dotenv
# platform/tool-server/.env.example — every variable, no real values (09 §4.5)
FATHOM_APP__LOG_LEVEL=INFO
FATHOM_AUTH__ISSUER=https://keycloak.internal/realms/fathom
FATHOM_AUTH__JWKS_URL=https://keycloak.internal/realms/fathom/protocol/openid-connect/certs
FATHOM_AUDIT__BASE_URL=http://audit.fathom-sustainment.svc.cluster.local:8000
FATHOM_GATEWAY__BASE_URL=http://gateway.fathom-sustainment.svc.cluster.local:8000
FATHOM_TOOL_SERVER__BUNDLE_PATH=/app/bundle/bundle.v1.json
FATHOM_TOOL_SERVER__SPEC_MAX_AGE_SECONDS=            # NO DEFAULT. Program decision — OQ-1
FATHOM_TOOL_SERVER__SPEC_POLL_INTERVAL_SECONDS=
FATHOM_TOOL_SERVER__TARGET_DEADLINE_SECONDS=         # must exceed the target's own budget — OQ-3
FATHOM_TOOL_SERVER__TOKEN_REFUSAL_MARGIN_SECONDS=
FATHOM_MCP__PROTOCOL_REVISION=                       # pinned, asserted at initialize — OQ-2
FATHOM_OTEL__ENABLED=false
```

Per document 09 §4.5, the four freshness and deadline variables have **no defaults**: a missing value fails at startup. A defaulted freshness bound is the mechanism by which §4.3's fail-closed rule would quietly become fail-open in one environment.

---

## 13. Explicit DO-NOT list

Each row is a way this service could let an agent do something the architecture forbids.

| Do not | Because | Guard |
|---|---|---|
| **Trust a generated descriptor's `x_fathom_side_effects` without a live check against the current specification** | The descriptor is a claim about the specification at generation time. A sub-application release can change the class, and `OAS004` will correctly drop `x-agent-eligible` in that release while the committed descriptor still says `none`. This is the single path by which an agent calls a state-changing operation under a stale eligibility claim (03 §8.1; 10 §7.4 records the field's purpose as *"so the tool server can refuse a call whose declared class changed since generation"*) | Gate 6 (§4.3); `test_side_effects_changed_since_generation_is_rejected`; `target-escalated` fixture |
| **Let an agent discover or call a tool outside its pinned manifest** | 03 §8.4 pins manifest version **and** API major as one promoted unit. A tool reachable outside the pin makes the pin decorative and makes the agent's evaluation gate (01 §8.8) a statement about a different tool set than the one in production | Gates 3–4; `test_discovery_excludes_tools_outside_the_pin`; `test_superseded_manifest_pin_is_rejected_at_call_time` |
| Treat a `side-effects` **relaxation** as benign | A mismatch in either direction proves the descriptor and the served spec are out of step, which means no other field of that descriptor has better standing (§4.3) | Gate 6b's `!=`; `target-relaxed` fixture |
| Reimplement the §8.1 eligibility rule locally | Document 10 §7.3 is *"the ONLY place that decides whether an operation may be selected."* A second copy must track a module owned by another package, and the observable direction of that drift is permissive at the call site | `assess()` import; `test_eligibility_is_not_reimplemented` |
| Gate anything on the HTTP method | **C1, D11.** A method check makes `pdm-whatif` unbuildable — every operation it needs is a `POST` — and wrongly excludes the compute-only operations three of seven agents require | Inherited from `assess`, which *"NEVER LOOKS AT THE HTTP METHOD"* (10 §7.3) |
| Generate, edit, regenerate, or "repair" a descriptor at runtime | Inverts 03 §8.1's two levels: selection is the consuming agent's reviewed decision, eligibility is the sub-application's assertion, and neither may perform the other's act. It would also destroy the independent recorded claim §4.3 compares against | `import-linter` contract; `test_no_generation_code_is_importable_at_runtime` |
| Serve an empty tool list to an unbound caller | Indistinguishable, from inside an agent, from "no tools configured", and a model with no tools answers from parametric memory — forbidden for state questions by 01 §8.3 | `test_unbound_caller_is_403_not_empty_list` |
| Derive `agent_id` from anything a caller can set | An agent that can name itself can name another agent's binding, and every rule in §4 becomes decorative | `test_agent_id_is_never_taken_from_the_request` |
| Mint, exchange, elevate, or substitute a credential — especially for an expired delegated token | 03 §8.3: an agent whose token expires *"does not silently continue under a service identity, and it does not create a proposal after its authority has lapsed."* Substitution also makes every downstream ABAC decision evaluate the wrong subject (obligation 7) | Gates 2, 7; `test_expired_delegated_token_yields_its_own_problem_type` |
| Proxy before the audit record is accepted, or discard a failed completion write | 03 §8.5 requires full request and response recorded. An unrecordable invocation must not occur, and an incomplete record must be visible rather than absent (04 §11 treats this as an accreditation artifact) | Gate 9; `test_audit_attempt_precedes_proxy`; `test_audit_completion_failure_is_visible_not_discarded` |
| Record only successful invocations | The question an accreditor asks is whether a blocked attempt is detectable. Rejections are the interesting records | §4.6; assertion 4 of the central test |
| Deduplicate on `Idempotency-Key` locally, or mint one | A retry answered from the proxy's cache never reaches the target, whose claim-and-`If-Match` fencing then reasons about a call history it cannot see (**D16**). A minted key either defeats idempotency or silently defines equivalence for someone else's operation | §5.4; `test_idempotency_key_is_forwarded_not_consumed` |
| Synthesize `If-Match`, or set `X-Backfill` | **D16** lost-update protection; 03 §5.3 reserves backfill for bulk historical load (**D30**) | `test_if_match_is_never_synthesized`; `test_x_backfill_is_never_set` |
| Hot-reload descriptors, poll a manifest registry, or fetch a bundle at container start | Makes the callable tool set mutable without a deployment record, which is the property 01 §9's pin-enforcement fallback exists to recover; and **D26** forbids fetching at container start with no workaround | §6; bundle path is read-only in the image; `readOnlyRootFilesystem` |
| Call a Domino Endpoint | Every descriptor maps to a sub-application REST operation. The Endpoint hop is inside the owning sub-application, which attaches caller identity there (03 §8.3; 02 §4.3) | §5.5; the compiler rejects a non-REST operation mapping |
| Hold a direct network edge to a sub-application, or to a database, or to Redpanda | 09 §4.4.2's sanctioned-edge set, and the reasoning that rejected a direct `domino-compute → pdm` rule. A second ingress to every sub-application is the shape being avoided | NetworkPolicy egress-equality helm-unittest assertion |
| Consume an event topic or build a read model | **C19.** Agents obtain state through tools; a topic-fed read model here is an event-shaped back channel around the eligibility gate | §9; no `events/` or `readmodels/` directory, asserted by test |
| Reshape, summarize, rank, or annotate a tool result beyond the recorded projection | 03 §9 item 1 requires tool results to reach the agent as data structurally separated from instruction. A proxy that editorializes inserts instruction into a result channel | §4.7 |
| Treat a projection pointer absent from a response **instance** as an error | That is the normal case, and it is exactly **D19**: `rul` is absent where `reference_class` is not item-conditional, and `pdm-whatif` projects it | `target-optional-absent` fixture |
| Add a `--warn-only`, `--force`, or sampling flag to any gate | Document 10 §7.5's discipline, applied at the call site: *"A warning is a gate that a hurried author steps over"* | Mirror of `test_no_warn_only_escape_hatch_exists`, over this service's configuration surface |
| Let a wall clock measure a spec age, a deadline, or a token margin | **D29.** STIG V-260520 mandates unlimited backward steps; a wall-clock age would declare a stale cache fresh at precisely the wrong moment | `test_no_wall_clock_arithmetic` |
| Expose discovery, `/mcp`, or the binding table to an unbound or anonymous caller | §7 rule 2. Also stranger than the platform's own posture: 02 §4.1 records Domino removing anonymous access platform-wide | Gate 3; no anonymous route exists |
| Declare `x-agent-eligible` on any operation of this service | The tool server is not a tool. Reachability into the proxy from a manifest would make the eligibility gate self-referential | `assert_operation_annotations` at startup; `ToolManifest.target.slug` is a `SubAppSlug`, so the manifest schema cannot name `tool-server` |

---

## 14. Open questions

Per the rule that nothing is invented, each of these is a gap this document refused to fill. Each names the reading adopted so behavior is deterministic in the meantime.

| ID | Question | Reading adopted |
|---|---|---|
| **OQ-1** | **The live-spec freshness bound.** No document publishes a value. It directly governs how long a stale eligibility claim could survive, so it is a safety parameter rather than a tuning knob | No default; startup fails without it (§12.2). The *behavior* at expiry — fail closed, per target — is fixed here and is not configurable. Companion question: whether per-target degradation should fail `/readyz` (§10.2 argues no) |
| **OQ-2** | **MCP protocol revision.** No program document names one, and inventing a revision string would be a fabricated fact | Pinned in configuration, asserted at `initialize`, recorded in the README. Needs a program decision before Wave 5's runtimes are written against it |
| **OQ-3** | **Tool-call latency budget and per-target deadline.** Document 06 §7 publishes operator-view budgets only. Two hops (tool server → gateway → target) plus two audit writes are added to whatever the target costs | No value invented. The deadline must exceed the target's own budget, because an abandoned Endpoint-backed call still occupies the target's worker (02 §4.3). Document 09 §10 open question 8 (load testing unassigned) is the same gap |
| **OQ-4** | **Should `tool_invocation` be a catalogued event?** Document 03 §6 assigns this service no aggregate, and a platform-service topic would be a new contract term in a document 03-owned catalog | No events (§9). Escalation runs on the `side-effects-mismatch` alert. If the answer changes, 03 §6 gains rows and the outbox obligation (§2.4) turns back on |
| **OQ-5** | **Audit write volume at production scale.** Two writes per invocation is trivial at document 06 §7's demonstration figures; at ~300 hulls it is not obviously so | Two-phase writing retained — an unrecordable invocation must not occur. Batching the *completion* write is the available relief; batching the *attempt* write is not, because it is a gate |
| **OQ-6** | **Are the OpenAPI documents actually releasable outside the program?** §7's third-party claim depends on it. The annotations describe Navy sustainment operations, and 03 §12 states the demonstration is single-level while production is not | This document specifies what *may* be published and does not decide whether it *is*. Distribution statements and dissemination controls per 03 §7.3 govern; a program release decision is required |
| **OQ-7** | **The pin file's name and shape.** `agents/*` is governed by 01 §8 and 03 §8, not by this document, and Wave 5's agent build document owns it | `agents/<name>/tool-pins.yaml` as in §2.2. Nothing here depends on the filename — only on the compiled binding — so a rename costs a compiler constant |
| **OQ-8** | **Document 03 §4's REST conventions versus a JSON-RPC surface.** §4 is *"applicable to all sub-applications and platform services"* and cannot describe a JSON-RPC method set | Both surfaces served, JSON-RPC as a logic-free adapter documented as one operation with a naming carve-out (§3.1, §8.1). A 03 §4 carve-out sentence would make this clean rather than merely justified |

---

## 15. Corrections and requirements against other documents

Found while reconciling. Items 1 and 2 **block** this service's deployment.

| # | Document | Issue | Required change |
|---|---|---|---|
| 1 | **09 §4.4.2 sanctioned-edge table** | No `tool-server → gateway` edge exists, so the egress-equality assertion cannot pass for a service that must reach its targets (§5.1) | Add the row, with the same rationale the table already gives for `domino-compute → gateway`. Per 09 §9 item 30 this needs a document 09 change plus an ADR |
| 2 | **The gateway's build document** (not yet written) | The gateway must serve `/api/v1/<slug>/…` in **pass-through** mode for this caller. A composed view model breaks every `x_fathom_result_projection` pointer (§4.7), and would break the live-spec fetch of §2.5 | State pass-through as a gateway requirement |
| 3 | **04 §11 Platform layer** | Has no **Tool Servers** subsection, though 01 §5 lists the service and 03 §8.5 mandates it. This is the unfixed remainder of finding **C17** (*"appear in no component inventory"*) — 01 §5 was corrected; 04 §11 was not | Add a Tool Servers subsection to 04 §11 |
| 4 | **01 §3 plane diagram** | The Mermaid graph declares node id `TS` twice — `TS[Tool Servers<br/>MCP manifests]` in the Sustainment Plane subgraph and `TS[(TimescaleDB)]` in the Data & Infrastructure Plane. The second declaration re-labels the first node, so TimescaleDB does not render in the Data Plane at all | Rename one node id (e.g. `TSRV` and `TSDB`). Cosmetic in prose, materially wrong in the rendered diagram that most readers actually look at |
| 5 | **10 §11 open questions** | **OQ-13** records the `authority_class` vocabulary as undefined and calls it *"the most consequential gap in the package."* Document 03 now defines it at **§7.2.1** | Close OQ-13 against 03 §7.2.1, and adopt the `AuthorityClass` enum in `packages/canonical-schemas`. Nothing in this service changes — §7.2.1 is *adjudication* authority, distinct from the *agent* authority classes of §8.3 that this service enforces (§4.5) |
| 6 | **03 §8.5** | Says *"Tool servers"* plural while 03 §3.1 and 01 §5 give one singular slug, `tool-server`. Read as one service hosting many manifests, which is what 01 §8.0's one-to-many model implies | Editorial |
| 7 | **09 §6.2 path filters** | Job scoping by changed service would let a manifest-only change regenerate descriptors without rebuilding the tool-server image, producing a green pipeline and a stale deployment (§6.1) | Include `packages/agent-tooling/generated/**` and `agents/*/tool-pins.yaml` in the tool-server image job's filter |

---

## 16. Definition of Done

This **extends** the shared Definition of Done in [`09-monorepo-and-conventions.md` §8](09-monorepo-and-conventions.md). Every applicable item there applies and none is removed. The items §2.4 makes inapplicable are enumerated below with justification, because document 09 §8 permits additions but not silent removals.

### 16.1 Bundle and bindings

- [ ] `bundle.v1.json` and `bundle.sha256` committed; `make check-bundle` shows no drift against a fresh compile.
- [ ] The compiler copies descriptors **verbatim** — a test asserts byte-equality between each bundled descriptor and its `packages/agent-tooling/generated/` source.
- [ ] Rules **B1–B4** (§2.2) each fail the build, each with a test.
- [ ] `provenance` records the generation commit, `generated_at`, the bundle digest, and every `(slug, api_major)` the descriptors were generated against.
- [ ] `GET /descriptor-bundle` returns the active bundle digest and image digest; `fathom_tool_bundle_info` carries both.

### 16.2 Discovery

- [ ] Discovery is scoped by binding; two agents over one slug see disjoint sets where their manifests differ.
- [ ] An unbound caller receives `403 no-manifest-binding` — **never** an empty `200`.
- [ ] `agent_id` derives only from the validated token; a caller-supplied override is rejected.
- [ ] REST and `/mcp` produce identical verdicts across the whole enforcement suite; the JSON-RPC handler contains no enforcement logic (asserted by the shared-use-case test and by review).
- [ ] The MCP protocol revision is pinned in configuration and asserted at `initialize`.

### 16.3 Invocation-time enforcement

- [ ] All nine gates of §4.2 implemented **in order**, each with a positive and a negative test.
- [ ] Gate 6a calls `fathom_agent_tooling.eligibility.assess` against the **live** document; `import-linter` forbids importing the generator, and `test_eligibility_is_not_reimplemented` passes.
- [ ] Gate 6b rejects a class mismatch **in either direction**, with `409 side-effects-mismatch`, and the target is not contacted.
- [ ] `test_superseded_manifest_pin_is_rejected_at_call_time` and `test_side_effects_changed_since_generation_is_rejected` pass, on both surfaces, with all five assertions of the latter.
- [ ] All ten fake-target variants of §11.1 exist and produce their stated outcome — including `target-optional-absent` **succeeding** (the **D19** case) and `target-path-moved` **succeeding**.
- [ ] The live-spec cache measures age monotonically, fetches through the gateway with `If-None-Match`, fails closed past its bound, and never falls back to the descriptor's recorded class.
- [ ] The service is not ready until every bound target's spec has been fetched once.
- [ ] Authority: delegated tokens forwarded unchanged; accountable_autonomous capped at `none`/`proposal-only` with a resolvable accountable owner; expired delegated authority yields `delegated-authority-lapsed` and is never substituted.
- [ ] Audit: `attempted` before proxying and fails closed; completion always written, including on rejection; an incomplete record is visible, never discarded; `trace_ref` and `X-Correlation-Id` on every record.
- [ ] `Idempotency-Key` required on `proposal-only` and forwarded, never consumed or minted. `If-Match` never synthesized. `X-Backfill` never set.
- [ ] No configuration or flag can disable, sample, or soften any gate.

### 16.4 Proxying and boundary

- [ ] Every call routes through `gateway`; no direct sub-application edge exists in the rendered NetworkPolicy.
- [ ] The concrete method and path resolve from the **live** document by `operationId`; no path is recorded in the bundle.
- [ ] No Domino Endpoint is ever called; the compiler rejects a non-REST operation mapping.
- [ ] Deadlines, retry backoff, and the token refusal margin are monotonic. `test_no_wall_clock_arithmetic` passes.
- [ ] The helm-unittest egress-equality assertion passes over exactly `{kube-dns, auth, audit, gateway}` — **no database peer, no broker peer**.
- [ ] `deploy/argocd/` Application committed; `dev` auto-sync, staging and production manual sync.
- [ ] CI path filters include `packages/agent-tooling/generated/**` and `agents/*/tool-pins.yaml` (§15 item 7).

### 16.5 Explicitly not applicable, with justification

Each row requires an ADR under `docs/adr/` per document 09 §8.7. An implementer who restores one without an ADR has diverged from this document.

| 09 §8 item | Status | Justification |
|---|---|---|
| Owned CloudNativePG database; Alembic; `migrations` readiness check | **N/A** | No aggregate, no state (§2.4). Everything served is a build artifact; everything retained belongs to `audit` |
| Transactional outbox (obligation 11) | **N/A** | Document 11 §1.1 scopes it to services that publish events. This service publishes none (§9). Tracked as **OQ-4** |
| Consumer inbox, read models, `read_model_lag` check, antecedent rule | **N/A** | Consumes no topic (§9), by the same rule that forbids agents from consuming topics (**C19**) |
| `changed_since` snapshot reads (obligation 5) | **N/A** | Scoped to aggregates a declared consumer projects; there are none |
| Local `Idempotency-Key` middleware | **Deliberately absent** | §5.4 — the key is forwarded so the target's fencing sees the retry |
| Event-catalog reconciliation (09 §6.2 job 6) | **N/A** | Empty `PUBLISHES`/`CONSUMES`, asserted as empty rather than absent |
| Conflict policy per aggregate (obligation 16) | **N/A** | No aggregate. The 03 §11 default is accepted vacuously and stated in the README |
| Purge path per owned store (03 §13) | **N/A for owned stores; declared for the bundle** | The bundle is a read-only image artifact removed by image lifecycle. Invocation records are purged under `audit`'s protocol |
| `spec_freshness` failing `/readyz` on a single stale target | **Deviated** | §10.2 — nine independent targets, and removing the pod would remove the enforcement point that is correctly rejecting calls while breaking the other eight |

### 16.6 Documentation

- [ ] `README.md` carries the copied document 09 §8 checklist, this section's additions, the sanctioned NetworkPolicy peers, the empty event catalog stated explicitly, the pinned MCP revision, and every **N/A** above with its ADR reference.
- [ ] Every **`DECISION`** in this document is either unchanged or superseded by an ADR — never silently varied.
- [ ] **OQ-1 through OQ-8** are filed with owners. **OQ-1** (freshness bound) and **OQ-2** (MCP revision) are **blockers for Wave 5**: the first sets how long a stale eligibility claim can survive, and the second is the wire contract every agent runtime is written against.
- [ ] §15 items 1 and 2 are landed before this service deploys. Without item 1 it cannot reach a target; without item 2 every result projection breaks.
