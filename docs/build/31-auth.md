# Build Framework 31 — Identity & Authorization (`auth`)

| | |
|---|---|
| **Status** | Build framework, rev 1. Binding on `platform/auth`, on `packages/py-common`'s authorization surface, and on every service that enforces authorization (which is all seventeen) |
| **Scope** | The OpenID Provider deployment and realm configuration, federation with Domino's Keycloak, the ABAC attribute model, **the two agent-authority-class token shapes**, the RFC 8693 token-exchange flow for agent delegation, mid-run authority-lapse handling, **the Domino Endpoint call proxy and its audit binding**, the OPA policy structure for authority-versus-blast-radius and classification checks, and the CAC/PIV integration path |
| **Binding sources** | [03 — Integration Contracts](../architecture/03-integration-contracts.md) §4, **§7.2.1**, §7.3, **§8.3**, §12, §15 · [01 — System Architecture](../architecture/01-system-architecture.md) §5, **§8.5**, §8.7 · [04 — Sub-Application Architectures](../architecture/04-subapplication-architectures.md) §11 · [05 — Review Findings](../architecture/05-architecture-review-findings.md) **D12**, **D16**, D13, D14 · [08 — Standards Alignment](../architecture/08-standards-alignment.md) §3.2, §3.3, §3.5, §3.6 |
| **Companion build documents** | [09 — Monorepo and Conventions](09-monorepo-and-conventions.md) (layout, stack, the shared Definition of Done) · [10 — Shared Packages](10-shared-packages.md) (`Proposal`, `ClassificationLabel`, `SideEffects`) |
| **Precedence** | Document 03 prevails over this document on any contract surface. Document 09 prevails on layout, stack, and conventions. Where this document appears to disagree with either, **this document is defective** and §14 is where the disagreement should already have been recorded |
| **Classification** | Internal |

---

## 0. How to read this document, and why it exists before its siblings

Every other sub-application document in this wave will contain the sentence *"enforced by ABAC"* or *"checked against the caller's authority."* Those sentences are unimplementable until this document exists, because nothing else in the corpus states what a token contains, who issues it, what an authority class is at the wire level, or how a receiving service turns a bearer token into an allow-or-deny decision. Document 04 §11 says only *"substantial Phase 3 design required."* This is that design.

Two markers are used, following document 09 §1.3:

- **[03 §n]**, **[01 §n]**, **[08 §n]** — dictated by an architecture document. Not negotiable at implementation time.
- **[ESTABLISHED HERE]** — the architecture documents do not specify it. This document decides, states the reasoning, and records the decision so seventeen services do not make seventeen different calls.
- **[VERIFY]** — a factual claim about an external product, standard, or credential profile that this document does **not** assert as verified. It must be confirmed against primary documentation at implementation time. Document 08 §8's discipline ("unverified — do not present as fact") applies to this document too, and the CAC/PIV section in particular is where the temptation to invent detail is strongest.

Read §3 and §5 before writing any code. They are the two sections whose absence would make the rest of the program's safety claims false rather than merely undocumented.

---

## 1. Purpose and scope

### 1.1 What this service is

`auth` is the Sustainment Plane platform service listed in document 01 §5: *"OIDC, CAC/PIV-ready, ABAC over classification, caveats, compartments, unit, billet, and qualification. Federated with Domino's Keycloak so agent activity carries the requesting user's authority (§8.5)."*

It is **two deployed things under one slug**, and conflating them is the first mistake available:

| Component | What it is | Where it lives |
|---|---|---|
| **The OpenID Provider** | A Keycloak instance. Issues every token in the system. Owns the realm, the identity providers, the authentication flows, the protocol mappers, and the signing keys | `platform/auth/keycloak/`, deployed by the `auth` chart as a StatefulSet |
| **The `auth` service** | A FastAPI service following document 09 §4's scaffold exactly. Mediates and audits token exchange, owns delegation and agent-run records, serves signed OPA policy bundles, and answers advisory authority queries | `platform/auth/`, deployed by the same chart as a Deployment |

The OpenID Provider is the *issuer*. The `auth` service is the *authority over issuance policy and over the lifecycle of a delegation*. Neither is the *enforcement point*: enforcement happens in the receiving sub-application, in-pod, and that is a contract term, not a preference [03 §4, §15 obligation 7 — *"Enforced by the receiving sub-application against ABAC attributes… Never delegated to the gateway alone"*].

### 1.2 What this document governs

1. Keycloak realm configuration, federation direction with Domino's Keycloak, and the attribute model (§2).
2. **The exact JWT claim set for three token kinds: the interactive human token, the `delegated` agent token, and the `accountable_autonomous` agent token** (§3).
3. **The exact RFC 8693 token-exchange flow, and the exact mid-run-lapse termination and checkpoint protocol** (§4).
4. **The exact Domino Endpoint call proxy mechanism and its audit binding** (§5).
5. The OPA policy bundle structure, the decision input document, the authority-versus-blast-radius policy generated from document 03 §7.2.1, and the classification policy (§6).
6. The CAC/PIV integration path, expressed as a diff to identity-provider configuration and nothing else, with a test that makes the claim verifiable (§7).
7. The `auth` service's own API surface, events, tests, deployment, prohibitions, and Definition of Done (§8–§13, §16).

### 1.3 What this document does NOT govern

| Out of scope here | Governed by |
|---|---|
| The `Proposal`, `ClassificationLabel`, and `Evidence` wire schemas | [10 — Shared Packages](10-shared-packages.md); schemas themselves 03 §7 |
| Which operations exist on each sub-application, and their `x-side-effects` values | Document 04, then each sub-application's build document. This document consumes those annotations; it does not assign them |
| The unified proposal adjudication queue, view-model composition, rate limiting | `gateway`'s own build document. **Exception:** the Domino Endpoint proxy operation is specified here (§5) because its correctness is an authority property, and it is implemented on `gateway` |
| Audit record storage, retention, immutability, and purge | `audit`'s own build document. This document specifies the *content and timing* of two audit records it is the sole author of (§4.6, §5.5) |
| Outbox, inbox, clock discipline, `sync_quality` | [11 — Outbox & Sync Library](11-outbox-sync-library.md) |
| Unit hierarchy, billet code sets, qualification code sets as *data* | `reference-data` [12], seeded per [13]. **Do not invent Navy billet or TYCOM code values here** — document 07 records them as CAC-gated, and document 09 §9.5 item 32 makes inventing them a defect |
| Which impact level applies, and therefore which control baseline | **Nobody yet.** It requires a written authorizing-official determination of NSS status [08 §3.3]. §12 states what changes under each outcome and asserts neither |
| Network router, session storage, and login UI look-and-feel for `apps/web` | Deferred to the look-and-feel wave [09 §2.6] |

---

## 2. Identity model

### 2.1 Deployment shape

| Concern | Decision | Basis |
|---|---|---|
| OpenID Provider | **Keycloak**, one realm `fathom` | 01 §14, 09 §2.1 — not open |
| Placement | `fathom-sustainment` namespace, StatefulSet, part of the `auth` chart | 09 §2.4 |
| Provider database | CloudNativePG cluster **`fathom-auth-pg`**, **two schemas**: `keycloak` (the OP) and `auth` (the service) | 03 §15 obligation 13 permits *"separate schemas of one owned cluster"*; **[ESTABLISHED HERE]** that this is the sanctioned form for `auth`, and it is the justification the Definition of Done asks for |
| Signing | Asymmetric only. `RS256` or `ES256` realm keys, rotated on a realm key-rotation schedule; JWKS at the realm's standard path | **[ESTABLISHED HERE]**. Symmetric signing (`HS256`) is prohibited: it would require every one of seventeen services to hold a secret capable of *minting* tokens, which converts any single service compromise into full impersonation |
| Discovery | Services read `FATHOM_AUTH__ISSUER` and `FATHOM_AUTH__JWKS_URL`, already in document 09 §4.5's `.env.example` | 09 §4.5 |
| Image | The program's hardened Keycloak image, pinned by digest, mirrored into the private registry | 09 §2.4. **No authorization or STIG inheritance is claimed from a hardened base image** — Iron Bank *"[h]ardened containers do not have a Certificate to Field (CtF) or an Authority to Operate (ATO)"*, and it is IL2-only [08 §3.6] |
| Realm as code | `platform/auth/keycloak/realm-fathom.json`, committed, applied by a Helm hook Job. **No configuration is made through the admin console in any environment** | **[ESTABLISHED HERE]**. An accreditor asks what the realm is configured to do; the answer must be a reviewed file in git, not a live query. This is the same argument document 09 §6.3 makes for Argo CD as the deployment record |

### 2.2 Federation with Domino's Keycloak — direction, and why

Document 01 §5 and document 04 §11 both require that *"one identity spans both planes,"* and document 04 §11 calls it *"the prerequisite for delegated agent authority."* Neither states which realm is authoritative. **[ESTABLISHED HERE]:**

> **The `fathom` realm is the authority. Domino's Keycloak is configured to broker to it as an external OIDC identity provider. Identity never flows the other way.**

```
        CAC/PIV or password                 OIDC identity brokering
 Human ──────────────────────▶ fathom realm ◀──────────────────────── Domino Keycloak
                               (authoritative)                        (broker only)
                                     │                                      │
                                     │ issues every token in the system     │ issues Domino
                                     ▼                                      ▼ session cookies
                    apps/web · gateway · 17 services · agents        Workspaces · Jobs · Apps
```

Four reasons, each of which would independently decide it:

1. **The CAC/PIV claim depends on it.** Document 01 §5 and document 04 §11 both assert that CAC/PIV substitution is *"an identity-provider change, not an application change."* That is only true if there is exactly one place where the authenticator changes. If Domino's realm were authoritative, the program would have to change an authenticator inside a vendor-managed component, and §7's verifiable claim would collapse into a hope.
2. **The program owns attributes Domino has no schema for.** Clearance level, caveats, compartments, unit, billet, and qualification are the ABAC inputs [01 §5, 03 §4]. They are program data governed by program policy. A vendor realm is not the authoritative source for a clearance attribute, and an accreditor should not be asked to accept that it is.
3. **Domino is a substitutable platform component.** Document 01 §9's port abstractions exist so that *"a partner-operated or air-gapped environment can substitute implementations."* Identity cannot be the one dependency that makes the platform irreplaceable.
4. **The M2M dependency in document 01 §8.7 is unresolved.** Domino's *"application authorization model currently offers public access or interactive session authentication, with no documented token-based intermediate suitable for programmatic callers."* If the program's identity depended on Domino's realm, the contingency in 01 §8.7 — relocating the agent orchestration runtime to the Sustainment Plane — would also require an identity migration. Brokering keeps the contingency cheap.

**Linking rule.** Domino's broker configuration links on the `fathom` realm's stable `sub`, with automatic first-broker-login linking and **no** account creation on the Domino side beyond the linked record. A user who exists in Domino but not in the `fathom` realm has no FATHOM identity and no FATHOM authority; that is the intended outcome, not a gap.

**What federation does *not* buy.** Federation gives a Domino Workspace or App a *user session* traceable to a FATHOM identity. It does **not** put caller identity on a Domino Endpoint invocation: an Endpoint authenticates with *"[s]tatic per-model tokens with no expiry, rotation policy, or per-caller audit trail"* [02 §4.3], and no amount of realm federation changes that. That gap is what §5 exists to close, and it must not be reasoned away by pointing at federation.

### 2.3 User attributes

Stored as Keycloak user attributes, populated from the program's authoritative personnel source (out of scope here; seeded from `data/synthetic` in the demonstration per [13]).

| Attribute | Type | Source of values | Notes |
|---|---|---|---|
| `unit_uic` | string, 5 characters | `reference-data` unit hierarchy [01 §5] | The `uic` form of 03 §3.3's `AssetRef.uic`. A 6-character form carries a leading Service identifier [03 §3.3] |
| `unit_path` | string | `reference-data` | Materialized ancestry `fleet/tycom/isic/unit`, so a `class`- or `fleet`-scoped policy check needs no runtime tree walk |
| `billet` | string | `reference-data` | **Code values are not invented here.** Document 07 records TYCOM and billet code values as CAC-gated or unpublished |
| `qualifications` | list of strings | `reference-data` | Feeds 03 §6's `anomaly_tag.confirmed` *"reviewer, qualification"* field and 01 §8.8's *"[r]eviewer qualification weights labels"* |
| `authority_classes` | list, closed vocabulary | **03 §7.2.1** | See §2.4. Realm roles, not free-text attributes |
| `clearance_level` | enum `U` \| `CUI` \| `S` \| `TS` | Program personnel security | Same vocabulary as `ClassificationLabel.level` [03 §7.3] so the dominance comparison is on one scale |
| `caveats` | list, closed vocabulary | 03 §7.3's ten authorized Limited Dissemination Controls | `NOFORN`, `FED ONLY`, `FEDCON`, `NOCON`, `DL ONLY`, `RELIDO`, `REL TO`, `DISPLAY ONLY`, `AC`, `AWP`. **`FOUO` and `U//FOUO` are retired markings** [03 §7.3, DoDI 5200.48 §3.4.b] and are rejected at attribute validation, not merely discouraged |
| `compartments` | list of strings | Program | Matched by containment, never by post-filtering [03 §7.3, D13] |
| `cui_categories_authorized` | list | CUI Registry categories | Mirrors `ClassificationLabel.cui_categories` |

Attribute validation is enforced at the realm boundary by a Keycloak declarative user profile [VERIFY: declarative user profile availability and schema in the pinned Keycloak version], and again by `packages/py-common` when a token is parsed. Both are required: the first prevents a bad attribute being stored, the second prevents a bad attribute being *trusted* if a future realm change loosens the first.

### 2.4 `AuthorityClass` — the enum, and where it now lives

Document 03 §7.2.1 (added in the correction landed today) fixes the vocabulary:

```
AuthorityClass = maintainer | planner | supply_officer | design_authority | fleet_authority |
                  security_officer
```

`security_officer` was added by amendment 03-1, after this section was first drafted — the ISSM/ISSO role holding the crypto-shred purge/rewrap authority (03 §7.2.1), under mandatory dual control with a `fleet_authority` counter-signature at class/fleet scope. Every occurrence below is written against the current, six-member enum.

Document 10 currently types `Proposal.authority_class` as `NonEmptyStr` and records **OQ-13** as *"the most consequential gap in the package"* precisely because the vocabulary was undefined at the time it was written. **OQ-13 is now closed by 03 §7.2.1**, and the consequence is a required edit to document 10:

```python
# packages/canonical-schemas/src/fathom_schemas/authority.py          NEW MODULE
from enum import StrEnum

class AuthorityClass(StrEnum):
    """Document 03 §7.2.1.  The organizational role permitted to ADJUDICATE a
    proposal, given its `kind` and `blast_radius`.

    DISTINCT from the agent authority classes of 03 §8.3, which govern which
    CREDENTIAL an agent calls with.  03 §7.2.1 opens with that distinction
    because conflating them is the available mistake: "An agent's delegated
    token still carries a human's identity and roles, and it is that identity's
    roles that are checked here."

    Closed vocabulary.  Phase 3 "may add finer-grained roles WITHIN a class
    (e.g. splitting `planner` by RMC), but may not remove the minimum this
    table establishes."  A seventh member is a change to document 03, not to
    this file — `security_officer` (amendment 03-1) is already the sixth.
    """

    MAINTAINER = "maintainer"                 # Ship's Force Maintainer
    PLANNER = "planner"                       # RMC / Availability Planner
    SUPPLY_OFFICER = "supply_officer"         # Supply role, ship or RMC
    DESIGN_AUTHORITY = "design_authority"     # PEO / Design Engineer
    FLEET_AUTHORITY = "fleet_authority"       # TYCOM Readiness Officer
    SECURITY_OFFICER = "security_officer"     # ISSM / ISSO
```

`Proposal.authority_class` is retyped from `NonEmptyStr` to `AuthorityClass`. Recorded as amendment **A-1** in §14.

**Realm representation.** The six values are **realm roles** named exactly as the enum values — not user attributes. Reason: roles are what Keycloak's role-scope mapper puts into a token, they are assignable through groups, and they are visible to an auditor as a role assignment rather than as a string in a bag of attributes. Group membership derives roles from billet through a program-owned mapping (`platform/auth/keycloak/billet-authority-map.json`), which is data, versioned in git, and reviewed as a change to authority.

**No implicit hierarchy. [ESTABLISHED HERE]** A `fleet_authority` does **not** automatically satisfy a requirement for `maintainer`. The classes are organizational roles, not levels: 03 §7.2.1 maps `maintainer` to *"Ship's Force Maintainer"* who *"[c]onfirms anomaly tags"*, and a TYCOM Readiness Officer holds no deckplate qualification to confirm what a sensor signature was. The policy therefore evaluates set membership against an explicit allow-set per table cell, never a rank comparison. Document 03 §7.2.1's word *"[m]inimum"* is ambiguous on this point and the ambiguity is recorded as **OQ-31-3** in §15; the safe reading is implemented.

### 2.5 One name, two meanings — resolved

Document 09 §5.5 says: *"The principal carries an `authority_class` of `delegated` or `accountable-autonomous`."* Document 03 §7.2.1 says `authority_class` is one of six organizational roles (§2.4 — five plus `security_officer`, amendment 03-1). **These are two different fields with one name**, and a service that reads `principal.authority_class` expecting one will silently get the other.

**[ESTABLISHED HERE] — the resolution, binding on `packages/py-common`:**

| Concept | Claim / field name | Vocabulary | Governs |
|---|---|---|---|
| Which credential an agent calls with | `fathom.agent.authority` | `delegated` \| `accountable_autonomous` | 03 §8.3 |
| Which organizational role may adjudicate | `fathom.identity.authority_classes[]` (principal) and `Proposal.authority_class` (resource) | 03 §7.2.1's six values (§2.4) | 03 §7.2.1, D16 |

Note also the spelling correction: 03 §8.3 renders the second agent class as *"Accountable autonomous"* in prose; document 09 §5.5 writes `accountable-autonomous` with a hyphen. The wire value is **`accountable_autonomous`**, `snake_case`, because 03 §4 fixes `snake_case` for JSON field *and* enumeration values elsewhere and a mixed convention here would be its own defect. Recorded as amendment **A-2** in §14.

---

## 3. The token shapes

Three kinds of token exist. Every one is a signed JWT issued by the `fathom` realm; none is opaque; none is symmetric.

### 3.1 The common identity block

Present, byte-identical, on the interactive human token and on the `delegated` agent token. Produced by Keycloak protocol mappers with dotted claim names (Keycloak nests on `.`), so the claim structure is realm configuration rather than service code.

```json
{
  "iss": "https://keycloak.internal/realms/fathom",
  "sub": "b31f…",
  "aud": ["pdm", "registry"],
  "azp": "fathom-web",
  "exp": 1770000900, "iat": 1770000600, "auth_time": 1770000000,
  "jti": "5c1a…",
  "acr": "1", "amr": ["pwd"],
  "scope": "openid fathom.user sfx:none sfx:proposal-only sfx:state-changing",

  "fathom": {
    "identity": {
      "subject_id": "b31f…",
      "edipi": null,
      "display_name": "…",
      "unit_uic": "N12345",
      "unit_path": "fleet/tycom-01/isic-04/N12345",
      "billet": "…",
      "qualifications": ["…"],
      "authority_classes": ["maintainer"],
      "clearance": {
        "level": "CUI",
        "caveats": ["FEDCON"],
        "compartments": [],
        "cui_categories_authorized": ["SP-CTI"]
      }
    }
  }
}
```

Rules on this block:

- **`aud` is a list of canonical slugs** [03 §3.1]. A receiving service requires its own slug in `aud` and rejects otherwise. This is what stops a token minted for `pdm`'s what-if surface being replayed against `maintenance`.
- **`scope` carries `sfx:` values** — the side-effect classes this token may authorize. A human interactive token may carry all three. See §3.4.
- **`fathom.identity.authority_classes` is populated from realm roles**, filtered to the six values of §2.4 (five plus `security_officer`, amendment 03-1). A role that is not one of the six never appears in a token.
- `edipi` is `null` until the CAC/PIV path is enabled (§7). Its presence or absence changes nothing else in the token.

### 3.2 Token shape 1 — `delegated`

For interactive agents invoked by a user. Document 03 §8.3: *"The user's delegated token… [r]each bounded by the user's own authorization, evaluated by the receiving sub-application."* Document 01 §8.5: *"A maintainer's copilot cannot read what the maintainer cannot read."*

```json
{
  "iss": "https://keycloak.internal/realms/fathom",
  "sub": "b31f…",                                  ◀── THE HUMAN. Unchanged from §3.1.
  "aud": ["pdm", "registry", "telemetry"],
  "azp": "fathom-agent-copilot",
  "exp": 1770000900, "iat": 1770000600,
  "jti": "9ae0…",
  "scope": "fathom.agent.delegated sfx:none sfx:proposal-only",

  "act": {                                         ◀── RFC 8693 actor claim.
    "sub": "svc:agents/copilot",
    "fathom": { "agent_id": "copilot", "agent_version": "3.2.0", "llm_version": "…" }
  },

  "fathom": {
    "identity": { "…": "BYTE-IDENTICAL to the user token's identity block" },
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

| Property | Value | Why exactly this |
|---|---|---|
| `sub` | **The human's subject.** Never the agent's | This single choice is what makes 01 §8.5's *"cannot read what the maintainer cannot read"* true by construction rather than by policy authoring. A receiving service evaluating ABAC on `fathom.identity` is evaluating *the user's* reach, using the same code path as the user's own request |
| `act` | The agent as actor, per RFC 8693 §4.1 | **Delegation, not impersonation.** Audit must be able to answer "who acted, on whose behalf" — an impersonation token (no `act`) makes an agent action indistinguishable from the human's own, which is exactly the non-repudiation failure an accreditor probes |
| `scope` | `sfx:none sfx:proposal-only`. **Never** `sfx:state-changing` | 03 §8.1/§15 obligation 8 permit agent eligibility only where side effects are `none` or `proposal-only`; 01 principle 7 and 09 §9.3 item 17 say an agent never writes domain state. Both agent classes are bound by this — the two classes differ in *whose authority* they carry, not in *whether they may write* |
| `authority_classes` | The user's own | Present because a delegated token's identity block is the user's. **But it can never be used to adjudicate**: see §3.5 rule 6 |
| Lifetime | Short, and **never longer than the parent session's remaining lifetime**. Default TTL 300 s, `FATHOM_AUTH__DELEGATED_TTL_SECONDS` | **[ESTABLISHED HERE]** as a configuration value, not a capacity figure — document 09 §9.5 item 31 forbids inventing quantities, and this is not one of the quantities document 06 §7 owns. The binding rule is the relationship, not the number: `exp ≤ min(iat + TTL, parent_session_exp)` |
| Refresh | **None issued.** `offline_access` is not in the client's scope set | An agent that can refresh its own authority has authority independent of the user, which is the defect D12 describes from the other direction. Continuation requires a fresh exchange against a live user session (§4) |

### 3.3 Token shape 2 — `accountable_autonomous`

For event-triggered and scheduled agents. Document 03 §8.3: *"A scoped short-lived workload identity with a **named accountable human owner**… [r]estricted to `x-side-effects: none` and `proposal-only`. Cannot read outside its declared scope. Every run recorded to Audit with the accountable owner."* This class exists because of **D12**: *"Delegated user authority is unsatisfiable for autonomous work. Three of the design's own paths have no requesting user."*

```json
{
  "iss": "https://keycloak.internal/realms/fathom",
  "sub": "svc:agents/pma-prescreener",             ◀── THE WORKLOAD. Not a human.
  "aud": ["pma", "telemetry"],
  "azp": "fathom-agent-pma-prescreener",
  "exp": 1770003600, "iat": 1770000000,
  "jti": "1d44…",
  "scope": "fathom.agent.autonomous sfx:none sfx:proposal-only",

  "fathom": {
    "identity": {
      "subject_id": "svc:agents/pma-prescreener",
      "authority_classes": [],                     ◀── EMPTY. ALWAYS. See rule 6.
      "clearance": {
        "level": "CUI",                            ◀── min(owner clearance, declared ceiling)
        "caveats": ["FEDCON"],
        "compartments": [],
        "cui_categories_authorized": ["SP-CTI"]
      }
    },
    "agent": {
      "authority": "accountable_autonomous",
      "run_id": "77c1a2e4-…",
      "grant_id": "g-4180…",
      "manifest": "pma-prescreen",
      "manifest_version": 1,
      "api_major": 1,
      "trigger": { "kind": "event", "event_type": "fathom.telemetry.mission.completed",
                   "event_id": "…", "correlation_id": "…" },
      "trace_ref": "mlflow://…"
    },
    "accountable_owner": {                         ◀── REQUIRED. Issuance fails without it.
      "subject_id": "b31f…",
      "display_name": "…",
      "billet": "…",
      "unit_uic": "N12345",
      "authority_classes": ["planner"]             ◀── ACCOUNTABILITY ONLY, never authorization
    },
    "declared_scope": {                            ◀── REQUIRED, non-empty. The read ceiling.
      "assets": ["a1b2…"],
      "class_ids": [],
      "fleet": false,
      "aggregates": ["mission", "telemetry_batch", "anomaly_candidate"],
      "clearance_ceiling": { "level": "CUI", "compartments": [] }
    }
  }
}
```

Six properties, each carrying a specific failure it prevents:

1. **`accountable_owner` is required and validated non-empty at issuance.** `POST /autonomous-grants` returns `422` with `urn:fathom:problem:auth:accountable-owner-required` if absent, if the named subject does not exist in the realm, or if that subject is disabled. 03 §8.3's *"named accountable human owner"* is the whole content of the word *accountable*; a nullable field would make it decorative on the first Friday afternoon someone needed a scheduled job to run.
2. **`declared_scope` is required and non-empty.** 03 §8.3: *"Cannot read outside its declared scope."* An absent scope is not "unscoped", it is a rejected grant. `fleet: true` requires an explicit dual-signature grant (§8) because it is the one value that makes the scope restriction vacuous.
3. **`fathom.identity.clearance` is the *floor* of the owner's clearance and the declared ceiling.** An autonomous agent never reads above the human accountable for it. Computed at issuance by `auth` and re-derivable by any receiver from `accountable_owner` and `declared_scope`, so the derivation is auditable rather than asserted.
4. **`authority_classes` is always empty**, even though the owner has classes. An autonomous agent proposes; it never adjudicates. Encoding the owner's roles into the agent's identity block would make an autonomous agent capable of approving its own proposals through a policy path nobody intended, which is D16 arriving by the back door.
5. **`scope` never contains `sfx:state-changing`**, and the realm makes it unmintable rather than merely unrequested (§3.4).
6. **Adjudication requires the absence of `fathom.agent` entirely.** Both agent classes are denied on any adjudication action, regardless of `authority_classes`. This is the token-level expression of 01 principle 7 and 03 §7.2's adjudication model, and it is asserted by a test (§10, T-6).

Lifetime is bounded by the run, `FATHOM_AUTH__AUTONOMOUS_TTL_SECONDS`, with no refresh token, for the same reason as §3.2. A run needing longer than one token lifetime terminates and checkpoints (§4.4) — it does not renew.

### 3.4 How the side-effect restriction is actually encoded and enforced

This is the mechanism document 03 §8.3's sentence *"[r]estricted to `x-side-effects: none` and `proposal-only`"* reduces to. It is a **positive allow-list in the OAuth `scope` claim, matched by the receiving sub-application against the matched route's own `x-side-effects` annotation.** Three independent layers, deliberately redundant, in the same spirit as document 09 §5.1's three-layer eligibility gate.

```
                        ┌──────────────────────────────────────────────────────┐
 Layer 1  ISSUER        │ The Keycloak client for an agent has an optional/     │
 (Keycloak realm)       │ default client-scope set that DOES NOT CONTAIN        │
                        │ `sfx:state-changing`. The scope is therefore          │
                        │ UNMINTABLE for that client, not merely unrequested.   │
                        └──────────────────────────────────────────────────────┘
                        ┌──────────────────────────────────────────────────────┐
 Layer 2  RECEIVER      │ `require_authz` reads the MATCHED ROUTE's             │
 (every sub-application)│ `x-side-effects` from `request.scope["route"]`        │
                        │ .openapi_extra and requires `sfx:<class>` to be       │
                        │ PRESENT in the token's `scope`. Deny by default.      │
                        └──────────────────────────────────────────────────────┘
                        ┌──────────────────────────────────────────────────────┐
 Layer 3  POLICY        │ OPA `side_effects.rego` denies on the same input,     │
 (in-pod OPA sidecar)   │ so a service that mis-wires layer 2 still fails       │
                        │ closed rather than open.                              │
                        └──────────────────────────────────────────────────────┘
```

```python
# packages/py-common/src/fathom_py_common/authz.py                    (excerpt)
SFX_SCOPE = {
    SideEffects.NONE: "sfx:none",
    SideEffects.PROPOSAL_ONLY: "sfx:proposal-only",
    SideEffects.STATE_CHANGING: "sfx:state-changing",
}

def _check_side_effects(principal: Principal, route_side_effects: SideEffects) -> None:
    """03 §8.3 · §8.1 · §15 obligation 8.

    POSITIVE matching. The ABSENCE of `sfx:state-changing` is NOT the test —
    the PRESENCE of the scope matching this route's declared class is. A token
    with no `sfx:` scopes at all authorizes nothing, which is the correct
    reading of a malformed or downgraded token.
    """
    required = SFX_SCOPE[route_side_effects]
    if required not in principal.scopes:
        raise ProblemException(
            type="urn:fathom:problem:auth:side-effects-not-permitted",
            title="Token does not authorize this operation's side-effect class",
            status=403,
            side_effects_required=route_side_effects.value,
            side_effects_authorized=sorted(
                s for s in principal.scopes if s.startswith("sfx:")
            ),
            agent_authority=principal.agent_authority,
        )
```

**Why the receiver and not the issuer is the enforcement point.** Layer 1 alone would be a single point of failure: one realm misconfiguration, one client-scope added to fix an unrelated problem, and every service in the system silently accepts state-changing autonomous calls. Layer 2 is where 03 §15 obligation 7 puts authorization (*"Enforces authorization locally… never relying solely on the gateway"*), and it is the layer test **T-1** in §10 exercises with a **validly signed** token that carries `sfx:state-changing` — proving the receiver refuses it rather than proving the issuer never sent it.

### 3.5 The receiving-service validation algorithm

Implemented once in `packages/py-common`, exposed as `Depends(require_authz(...))` per document 09 §5.5 — never reimplemented in a service. Order matters; each step is cheap-before-expensive and fail-closed.

| # | Step | Failure |
|---|---|---|
| 1 | Signature verified against cached JWKS; `alg` must be in the realm's asymmetric allow-list. `alg: none` and any symmetric `alg` are rejected before parsing claims | `401 urn:fathom:problem:auth:token-invalid` |
| 2 | `iss` equals `FATHOM_AUTH__ISSUER` exactly | `401 …:token-invalid` |
| 3 | `exp`/`iat`/`nbf` validated — **the one sanctioned wall-clock comparison in the system** (§6.7) | `401 …:token-expired` |
| 4 | **`aud` contains this service's canonical slug** | `403 …:audience-mismatch` |
| 5 | `sfx:` scope matches the matched route's `x-side-effects` (§3.4) | `403 …:side-effects-not-permitted` |
| 6 | If the action is adjudication, **`fathom.agent` must be absent** | `403 …:agent-may-not-adjudicate` |
| 7 | If `fathom.agent.authority == "accountable_autonomous"`: `accountable_owner` and `declared_scope` present and well-formed; the request's subject identifiers are contained by `declared_scope` | `403 …:outside-declared-scope` |
| 8 | If `x-side-effects` is `proposal-only` or `state-changing` **and** `fathom.agent` is present: the delegation or grant is confirmed active by `auth` introspection within `introspection_max_age` (§4.6) | `401 …:authority-lapsed` |
| 9 | OPA decision requested with the §6.3 input document; `allow` must be `true` | `403 …:not-authorized`, with `reasons` |
| 10 | Obligations from the decision applied — dual-control requirement, query predicates, field redaction | — |

Steps 1–4 and 6 are pure token checks and are performed even when OPA is unreachable; **an unreachable OPA sidecar is a `503`, never an allow.**

### 3.6 What a token never contains

- **A refresh token, for either agent class.** §3.2.
- **A password, certificate, or Domino Endpoint credential.** §5.7.
- **A classification label above the deployment's declared level**, and no compartment string that is itself compartmented. Document 09 §4.8 already forbids logging bearer tokens; this extends it to token *content* review.
- **A `fathom.agent` block on a human interactive token.** The blocks are mutually exclusive, and a token carrying both is rejected at step 1 as malformed.

---

## 4. Token exchange for agent delegation, and mid-run authority lapse

### 4.1 The flow

```
 1  Human ──login──▶ apps/web ──▶ gateway ──authorization code + PKCE──▶ Keycloak
                                   │
                                   └─ Gateway is a BFF: the USER'S ACCESS TOKEN NEVER
                                      LEAVES THE SERVER. apps/web holds a session cookie.
                                      [ESTABLISHED HERE — a token in a browser is a token
                                      in every browser extension the browser has installed]

 2  Human starts an agent turn
        │
        ▼
 3  gateway ── POST /api/v1/auth/delegations ──▶ auth        (user access token as bearer)
                                                  │
                                                  ├─ 4a validate agent client is registered
                                                  ├─ 4b load the manifest from
                                                  │     packages/agent-tooling/manifests/…
                                                  ├─ 4c RE-RUN THE ELIGIBILITY GATE against the
                                                  │     committed openapi.json: every selected
                                                  │     operation must be x-side-effects
                                                  │     none|proposal-only  [03 §8.1]
                                                  ├─ 4d derive `aud` from the manifest's targets,
                                                  │     plus `gateway` iff any selected operation
                                                  │     declares x-domino-endpoint  (§5.3)
                                                  └─ 4e RFC 8693 exchange ──▶ Keycloak
                                                        ◀── delegated access token
                                                  ├─ 4f persist the delegation record
                                                  └─ 4g write the audit record  (§4.6)
        ◀── delegated token + delegation_id ──────┘
 5  gateway ──invoke agent, passing the delegated token──▶ agent runtime
 6  agent ──tool call, Authorization: Bearer <delegated token>──▶ gateway ──▶ sub-application
                                                                              │
                                                    THE TOKEN IS FORWARDED UNCHANGED.
                                                    The gateway never swaps it for its own
                                                    workload identity. [03 §15 obligation 7]
```

**Why `auth` mediates rather than the gateway calling Keycloak directly.** Document 04 §11 assigns *"token exchange for delegated authority"* to the gateway, and step 3 keeps the gateway as the caller. But steps 4b–4d are *issuance policy*: they re-run the manifest eligibility gate at issuance time, against the committed specification, in the one service whose job is authority. Putting that in the gateway would place the safety gate in the component whose other responsibilities are composition and rate limiting, and would mean a second implementation of document 03 §8.1's rule. **[ESTABLISHED HERE]:** the gateway is the *caller* of exchange; `auth` is the *authority over* exchange. This does not contradict 04 §11 — it refines who holds which half.

**Why the eligibility gate runs three times.** Import time and CI already check it [09 §5.1]. Issuance is the third check because the manifest, the OpenAPI document, and the deployed service version can drift between a CI run and a token issuance — a manifest pinned to `api_major: 1` can select an operation whose side-effect class changed in a redeploy. The gate that matters is the one closest to the credential.

### 4.2 The exchange call

```http
POST /realms/fathom/protocol/openid-connect/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=urn:ietf:params:oauth:grant-type:token-exchange
&subject_token=<the user's access token>
&subject_token_type=urn:ietf:params:oauth:token-type:access_token
&actor_token=<the agent client's own client-credentials access token>
&actor_token_type=urn:ietf:params:oauth:token-type:access_token
&requested_token_type=urn:ietf:params:oauth:token-type:access_token
&audience=pdm
&scope=fathom.agent.delegated%20sfx:none%20sfx:proposal-only
&client_id=fathom-auth-exchanger
&client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer
&client_assertion=<private_key_jwt>
```

| Element | Rule |
|---|---|
| `subject_token` | The user's access token. Never a refresh token, never a password grant |
| `actor_token` | Present, and it is what produces the `act` claim of §3.2. **Delegation semantics, not impersonation** — an exchange that omits `actor_token` and yields a token without `act` is rejected by `auth` before it is returned to the gateway |
| `audience` | One or more canonical slugs, derived from the manifest (step 4d), never client-supplied |
| `scope` | Exactly the two `sfx:` values plus `fathom.agent.delegated`. `auth` asserts the returned token's `scope` matches what it requested and discards the token if not |
| Client authentication | `private_key_jwt`. No client secret is held by `auth` for the exchanger client |

**[VERIFY]** Keycloak's standard token exchange, the `actor_token` parameter, and emission of the `act` claim are version-gated (feature flag `token-exchange` and its v2 form) [VERIFY against the pinned Keycloak version at implementation time]. **Named fallback, adopted if verification fails:** `auth` mints the delegated token itself as an RFC 8693-*shaped* assertion — same claim set including `act` — signed with a dedicated realm client key, and the realm's token-exchange feature is not used. The claim shapes in §3 are unchanged under the fallback, which is the property that matters: **no service's validation code depends on which mechanism minted the token.** Recorded as **OQ-31-1** in §15.

### 4.3 The agent-run record

`auth` owns it, because authority lapse is the terminating condition and `auth` is the only component that knows when authority ends.

```
agent_runs
  run_id                  UUID, PK
  delegation_id           FK, nullable          -- delegated runs
  grant_id                FK, nullable          -- accountable_autonomous runs
  agent_id, agent_version, manifest, manifest_version, api_major
  llm_version
  trace_ref
  principal_sub           -- the human (delegated) or the workload (autonomous)
  accountable_owner_sub   -- NOT NULL for autonomous runs
  status                  running | completed | terminated_authority_lapsed
                          | terminated_pod_restart | terminated_revoked
                          | terminated_target_refused
                          # terminated_target_refused: a routine target refusal
                          # with a valid, unexpired token (a 429 admission-control
                          # engagement, a 503 tool-surface-unavailable) -- NOT an
                          # authority event.  Closes 41-pma-prescreener.md §20
                          # item 6, which found no status value for the "designed,
                          # routine condition" its own §5.6.2 requires; conflating
                          # it with terminated_authority_lapsed would send an
                          # implementer looking for authority-lapse causes a
                          # target refusal never had. [amendment]
  authority_expires_at    TIMESTAMPTZ           -- the token's exp
  checkpoint_ref          TEXT, nullable        -- s3://… An OBJECT REFERENCE, never content
  checkpoint_hash         TEXT, nullable        -- JCS-canonical SHA-256, so a resumed
                                                --   checkpoint is provably the one written
  resumable_until         TIMESTAMPTZ, nullable
  resumed_from_run_id     UUID, nullable
  terminated_at, terminated_reason
  version                 INTEGER               -- ETag source [09 §5.4]
```

Exactly one of `delegation_id` and `grant_id` is non-null, enforced by a `CHECK`.

### 4.4 Mid-run authority lapse

Document 01 §8.5: *"An agent whose token expires, or whose pod is restarted by platform maintenance, terminates with a resumable checkpoint. It does not continue under a service identity and does not create a proposal after its authority has lapsed."* Document 03 §8.3 repeats it. D12 names the unaddressed case: *"consent-gated tokens expiring mid-run when platform maintenance restarts the agent pod."* Document 01 §9 confirms the trigger is routine, not hypothetical: Domino app hosting carries *"300 s timeout; restart by maintenance; eviction by consolidation."*

**Detection — three independent triggers.**

| Trigger | Mechanism |
|---|---|
| **Proactive deadline** | At run start the runtime computes `run_deadline_monotonic = time.monotonic() + (exp - now)` **once**, and thereafter compares only monotonic values. Before every tool call it checks `run_deadline_monotonic - time.monotonic() > guard_band`. **No wall-clock arithmetic**: document 09 §9.2 item 7 and D29 — the Ubuntu 22.04 STIG rule **V-260520** mandates unlimited backward clock steps on any offset over one second, and a wall-clock countdown either storms or hangs the instant one lands |
| **Reactive `401`** | A tool call returning `401 urn:fathom:problem:auth:token-expired` or `…:authority-lapsed` terminates the run. The runtime does **not** retry, and does **not** attempt to obtain any other credential |
| **Restart** | The runtime finds a checkpoint for a `running` run with no token in memory. See below |

**Termination sequence**, in this order, because the order is what makes the guarantee hold:

1. Stop issuing tool calls immediately. No "just finish this one."
2. Serialize agent state to object storage; record `checkpoint_ref` and `checkpoint_hash`.
3. `POST /api/v1/auth/agent-runs/{run_id}/terminate` with the reason. `auth` sets `status`, `terminated_at`, `resumable_until`, and **revokes the delegation** (§4.6).
4. Write the audit record.
5. Exit non-zero, so the platform records a failed run rather than a successful one.

**The pod-restart case, exactly.** A restarted pod has lost the token, because **a delegated or autonomous token is never written to disk, never written into a checkpoint, and never written to a log** [09 §4.8 already forbids logging bearer tokens; this extends it to persistence]. On restart the runtime therefore finds a `running` run it cannot continue and has exactly one legal action: terminate it per the sequence above. It must **not**:

- re-authenticate with its own client credentials and continue (that is *"continu[ing] under a service identity"*, prohibited verbatim by 01 §8.5);
- exchange its own workload token into a delegation (`POST /delegations` requires a live user session and refuses a workload-only subject token — `403 urn:fathom:problem:auth:no-delegating-subject`);
- resume from the checkpoint under any credential it can mint for itself.

**Resume is a new run under new authority.** `POST /agent-runs/{run_id}/resume`, called with a **human interactive token**, creates a *new* `run_id` with `resumed_from_run_id` set and a freshly exchanged delegation. `auth` refuses when `resumable_until` has passed, when `checkpoint_hash` does not match the stored object, when the manifest or `api_major` pins have changed since the terminated run, or when the resuming human is not the original delegating subject. The last condition matters: resuming someone else's run under your authority is a quiet authority transfer.

**Autonomous runs resume too**, under a fresh grant from the same accountable owner. If that owner is no longer a valid principal, the run is not resumable — which is the intended consequence of accountability being attached to a person.

### 4.5 No proposal after lapse

The strong case is automatic: an expired token fails step 3 of §3.5. The subtle case is a token that is still within `exp` but whose *run* was terminated — a revoked delegation. That is closed by §4.6, and it is why `proposal-only` operations pay for introspection while `none` operations do not.

### 4.6 Revocation, introspection, and the deny-list

| Rule | Detail |
|---|---|
| **Introspection is authoritative** | On any `proposal-only` or `state-changing` operation presented with an agent token, the receiving service calls `auth` (a sanctioned NetworkPolicy edge — 09 §4.4.2 *"any service → `auth`"*) and requires an `active: true` response for the `delegation_id` or `grant_id`. RFC 7662-shaped |
| **`introspection_max_age` bounds the cache** | Default 10 s, `FATHOM_AUTH__INTROSPECTION_MAX_AGE_SECONDS`. Measured on a monotonic clock. An in-process **positive** cache older than the bound is not usable for an allow |
| **The event-fed deny-list may only deny** | Services consume `fathom.auth.delegation.v1` (§9) into a small revoked-`jti` read model. It makes revocation propagate fast; **it is never the sole basis for an allow**, because a consumer with lag would otherwise fail open |
| **`none` operations skip introspection** | A read under a valid, unexpired, correctly-audienced token is authorized by the token itself. This keeps the agent read path free of a synchronous dependency on `auth`, which matters because 03 principle 2's spirit is that compute paths do not fan out |
| **Revocation triggers** | Run termination; explicit `POST /delegations/{id}/terminate`; the delegating user's session ending; the accountable owner being disabled; a policy-bundle revision that removes an authority the grant depended on |

**The audit record `auth` authors** (written to `audit` over its API; `auth` holds no domain events of another service's):

```
DelegationAuditRecord {
  record_type            # delegation.issued | delegation.terminated | delegation.revoked
                         # | agent_run.started | agent_run.terminated_authority_lapsed
                         # | agent_run.resumed | autonomous_grant.issued
  delegation_id | grant_id, run_id, jti
  agent_authority        # delegated | accountable_autonomous
  subject_sub, act_sub, agent_id, agent_version, llm_version
  accountable_owner_sub  # REQUIRED for accountable_autonomous  [03 §8.3]
  declared_scope         # REQUIRED for accountable_autonomous
  audience[], scopes[], authority_classes[]
  manifest, manifest_version, api_major
  issued_at, expires_at, terminated_at, terminated_reason
  checkpoint_ref, checkpoint_hash
  correlation_id, trace_ref
  classification
}
```

Timestamps carry **1 ms granularity**, because DoD Zero Trust Overlays v1.1 set audit time-stamp granularity at 1 ms and select SC-45/SC-45(1) as tailoring additions [08 §3.3]. The record is written with the `sync_quality` attestation of 03 §5.4 attached, so that a skewed node produces a *bounded documented condition* rather than a contestable timestamp — 08 §3.3's point that *"skew is indistinguishable from tampering to an assessor and non-repudiation claims collapse if the time is contestable"* applies with full force to authority records.

---

## 5. The Domino Endpoint call proxy

### 5.1 The problem, stated exactly

Document 02 §4.3 records Domino Endpoint authentication as: *"Static per-model tokens with no expiry, rotation policy, or per-caller audit trail. Remediation assessed as 'full overhaul'."* Document 03 §8.3 draws the consequence: *"A Domino Endpoint authenticates with a static token carrying no caller identity and no per-caller audit trail (document 02 §4.3). Every Endpoint call is therefore made through a Sustainment Plane service that attaches caller identity to the audit record `[D12]`."* Document 01 §8.5 repeats it as a constraint on this design.

The consequence is sharper than "we should log it." **Domino cannot tell anyone, ever, who made a given Endpoint call.** There is no per-caller audit trail to reconcile against, no request-scoped identity to correlate with, and a timed-out request *"is not cancelled and continues to occupy its worker"* [02 §4.3] — so even the fact of execution is not reliably observable from the caller's side. If the program does not write the binding at the moment of invocation, the binding **does not exist anywhere and cannot be reconstructed later.** That is what makes this an accreditation exposure rather than an observability gap.

The interactive tier-3 what-if operation is the concrete path: document 01 §7 puts *"a dedicated Domino Endpoint for interactive what-if analysis"* behind PdM's `POST /scoring-runs/{id}/what-if`, which document 09 §5.1 shows as `x-side-effects: none, agent_eligible=True` — reachable by an agent, under a delegated token, on behalf of a named human. D12 lists it explicitly: *"`POST /what-if` via a Domino Endpoint whose auth is a static token with no per-caller audit."*

### 5.2 Decision: the proxy is an operation on `gateway`

**[ESTABLISHED HERE].** Document 03 §8.3 requires *"a Sustainment Plane service"* without naming it. It is the **`gateway`**, exposing one operation:

```
POST /api/v1/gateway/domino/endpoint-invocations        x-side-effects: none
                                                        x-substitution: internal
                                                        x-agent-eligible: false
```

Four reasons:

1. **Credential custody collapses to one service.** The Endpoint credential is a *static token with no expiry and no rotation policy* [02 §4.3] — the worst credential in the system. Putting it in `gateway` alone means one External Secret, one rotation runbook, one NetworkPolicy egress into `domino-compute`, and one place an assessor inspects. Letting each sub-application call its own Endpoint would distribute the worst credential in the system across nine services.
2. **The Domino edge already exists there, in the other direction.** Document 09 §4.4.2 sanctions `domino-compute → gateway` as *"one rule"*, for exactly this reason: *"they route through the gateway so PdM keeps a single ingress and the caller's workload identity is attached at one place. The alternative — a direct `domino-compute` → `pdm` rule — is rejected because it would need repeating for every future batch producer."* The identical argument applies outbound. One audited seam between the planes, not two.
3. **The gateway already validates the caller's token.** It is the ingress that received the agent's tool call; it has the delegated token in hand and has already verified it. Binding identity to invocation there requires no new trust relationship.
4. **The proxy is stateless composition plus an audit write, which is what the gateway is for.** D32's finding — *"the gateway becomes a stateful all-domain, all-classification consumer"* — is about consuming domain topics to build the adjudication queue. An endpoint-invocation intent row alongside the idempotency table that document 09 §5.3 already puts in every service's own database is not a domain read model and does not reopen D32.

**Alternatives considered and rejected:**

| Alternative | Rejected because |
|---|---|
| The owning sub-application (e.g. `pdm`) calls the Endpoint directly | Distributes a non-rotating static credential into nine services; requires nine cross-namespace NetworkPolicy edges into `domino-compute`, each separately justified at accreditation; and nine implementations of the two-phase audit binding in §5.5 |
| `auth` proxies | Puts `auth` on a compute path. `auth` is a dependency of all seventeen services; an inference-latency-bound operation there makes an authority outage an inference outage and vice versa |
| `tool-server` proxies | `tool-server` hosts MCP-style manifests [03 §8.5]; it is a manifest surface, not an egress. It also is not the component that validated the caller's token |
| A new dedicated `domino-proxy` platform service | An eighteenth service to hold one operation, one credential, and one audit write. Document 01 §5's platform inventory is canonical and adding to it is an architecture change, not a build decision. Revisit only if Endpoint traffic grows a second, non-inference use |

### 5.3 The contract annotation that scopes the audience

An operation whose implementation requires a Domino Endpoint declares it, so that §4.1 step 4d can add `gateway` to the delegated token's `aud` **only** for manifests that actually need it. **[ESTABLISHED HERE]** — a fourth operation annotation, validated in CI alongside document 03 §4.1's two:

```python
@router.post(
    "/scoring-runs/{scoring_run_id}/what-if",
    operation_id="pdm_what_if",
    **operation(
        substitution=Substitution.INTERNAL,
        side_effects=SideEffects.NONE,          # computational POST  [C1, D11]
        agent_eligible=True,                    # pdm-whatif manifest  [03 §8.2]
        domino_endpoint="pdm-tier3-whatif",     # ◀── x-domino-endpoint
    ),
)
async def what_if(...): ...
```

`x-domino-endpoint` names a logical Endpoint id resolved by `gateway` to a Domino Endpoint URL plus credential reference through chart configuration. The service never holds either. Two CI consequences: `tools/check_openapi.py` fails if a logical id is not declared in the gateway's chart, and it fails if `x-domino-endpoint` appears on an operation whose `x-side-effects` is `state-changing` — an Endpoint call is inference, and inference is not a domain state change.

### 5.4 The wire shape

```http
POST /api/v1/gateway/domino/endpoint-invocations HTTP/1.1
Authorization: Bearer <the CALLING SERVICE's workload token>       ◀── who is calling the proxy
X-Fathom-Caller-Authorization: Bearer <the delegated/autonomous token>
                                                                   ◀── on whose authority
X-Correlation-Id: 0f2c8f5a-…
Idempotency-Key: 8fd1…
Content-Type: application/json

{
  "domino_endpoint": "pdm-tier3-whatif",
  "operation_id": "pdm_what_if",
  "payload": { … },
  "deadline_ms": 55000,
  "classification": { "level": "CUI", "…": "…" }
}
```

**Why two credentials, and why the caller's token is not merely asserted.** The proxy must know *who is calling it* (a service, authorized to use the proxy at all) and *on whose authority* (the human or the accountable-owner-backed workload whose identity must appear in the audit record). It **verifies both**: it validates `X-Fathom-Caller-Authorization` fully — signature, `iss`, `exp`, `aud` containing `gateway`, `sfx:none` present, and delegation active via `auth` introspection. It does **not** accept a claimed subject id in the body. A proxy that trusted its caller's assertion of who the end user was would make the whole binding a statement by `pdm` about `pdm`, which is worth nothing to an assessor.

The `aud` requirement is what makes this tight: a delegated token only carries `gateway` in `aud` when its manifest selected an operation declaring `x-domino-endpoint` (§4.1 step 4d, §5.3). A token minted for a manifest with no inference operation **cannot** be used to reach the proxy, and the restriction is derived from the contract rather than configured by hand.

Response: `200` with the Endpoint's response body plus `X-Fathom-Invocation-Id`, or an RFC 9457 problem per §5.6.

### 5.5 The audit binding — two-phase, and why

```
 ┌ TXN 1 ────────────────────────────────────────────────────────────────────┐
 │ INSERT domino_endpoint_invocations (invocation_id, …, outcome='pending')   │
 │ INSERT outbox  → fathom.gateway.domino_endpoint_invocation.v1 (intent)    │
 └───────────────────────────────────────────────────────────────────────────┘   commit
                                     │
                                     ▼
              call the Domino Endpoint with the STATIC credential
                                     │
 ┌ TXN 2 ────────────────────────────┴──────────────────────────────────────┐
 │ UPDATE … SET outcome=…, http_status=…, response_hash=…, duration_ms=…    │
 │ INSERT outbox  → …domino_endpoint_invocation.v1 (result)                  │
 └───────────────────────────────────────────────────────────────────────────┘   commit
```

**The pre-write is the entire point.** If the record were written only after the call returned, a gateway crash mid-call would leave an Endpoint invocation that occurred and is attributable to nobody — permanently, because Domino has no per-caller audit trail to reconcile against [02 §4.3]. With the intent row, the worst case is an invocation whose *outcome* is unknown, which is a bounded documented condition. This is the same reasoning document 03 §5.2 applies to the transactional outbox and document 11 applies to the inbox: **the ordering of the write and the effect is the correctness property.**

Both writes go through the outbox [03 §5.2, 11], so the audit record reaches `audit` durably rather than by a best-effort HTTP call that a crash discards.

```
DominoEndpointInvocation {
  invocation_id
  # --- caller identity: THE BINDING. This is the record's reason for existing. ---
  caller {
    subject_sub                 # the HUMAN for delegated; the workload for autonomous
    agent_authority             # delegated | accountable_autonomous
    act_sub, agent_id, agent_version, llm_version
    delegation_id | grant_id
    jti                         # the specific token, so a specific credential is bound
    accountable_owner_sub       # REQUIRED when agent_authority is accountable_autonomous
    authority_classes[]         # the caller's, for context; never used to authorize here
  }
  immediate_caller_workload     # "pdm" — the service that invoked the proxy
  # --- what was invoked ---
  endpoint {
    domino_endpoint             # logical id from x-domino-endpoint
    domino_endpoint_url
    model_name, model_version, deployment_version
    traffic_split_variant       # Endpoints support canary/A-B routing [02 §4.3]; which
                                #   variant served a given call is otherwise unrecoverable
  }
  credential_ref                # External Secret name + rotation generation.
                                # NEVER the credential value.  §5.7
  # --- the call ---
  operation_id, correlation_id, trace_ref
  request_hash, response_hash   # JCS-canonical SHA-256. BODIES ARE NOT STORED [09 §4.8]
  request_bytes, response_bytes
  duration_ms                   # MONOTONIC-measured [09 §4.8, D29]
  http_status
  outcome                       # pending | ok | endpoint_error | payload_too_large
                                # | timeout_result_unknown | proxy_error
  domino_request_id?            # if Domino returns one. MAY BE ABSENT — see §5.6
  # --- envelope discipline ---
  occurred_at, recorded_at, clock{ monotonic_seq, hlc, sync_quality{…} }
  classification
}
```

Controls this record supports, each already established by document 08 §3.5 rather than invented here: **AU-10** (sign the record — non-repudiation), **AU-12(1)** (time-correlated audit trail, with 1 ms as the stated parameter), **AU-9(3)** (cryptographic protection of audit information), **SC-16** (bind classification and provenance to the record). Document 08 §3.5 names these for the outbox; they apply unchanged to a record that binds an identity to an act.

### 5.6 Domino's constraints are enforced in the proxy, not discovered in production

Every limit below is from document 02 §4.3, and each is enforced locally so a platform limit surfaces as a program error with a stable problem type rather than as a stalled worker.

| Domino property [02 §4.3] | Proxy behaviour |
|---|---|
| Payload ceiling **10 MB, fixed**; two requests to raise it declined | Reject **before** calling: `413 urn:fathom:problem:gateway:endpoint-payload-too-large`, `outcome=payload_too_large`, no invocation attempted. The intent row records the rejection |
| Effective timeout ceiling ~560 s; internal engineering recommends documenting **60 s** | Default deadline 55 s, configurable below the recommended maximum. Enforced with a monotonic deadline |
| **A timed-out request is not cancelled** and continues to occupy its worker | `outcome=timeout_result_unknown` — **never** an outcome implying the model did not run. This distinction is load-bearing: the invocation may have executed, and the audit record must not assert otherwise |
| No autoscaling; **serial by default**; no serving SLO | The proxy applies a bounded concurrency limit per logical Endpoint and sheds with `503 …:endpoint-capacity` rather than queueing unboundedly. **No latency or throughput figure is invented here** — document 09 §9.5 item 31 |
| No per-caller audit trail | §5.5 is the compensating control, and it is the only one |

`domino_request_id` is recorded when present and left null otherwise. It is **not** treated as a required correlation key, because nothing in document 02 establishes that Endpoints return one.

### 5.7 Credential custody

- The static Endpoint token arrives as an environment variable projected from an External Secrets–managed Secret [09 §2.4, §4.5]. It is never in a chart, a `values.yaml`, a log line, an audit record, or a problem detail.
- `credential_ref` records the Secret name and a rotation generation counter, so a rotation is visible in the audit trail without the value ever being.
- Rotation is a **program runbook item**, because Domino provides no rotation policy [02 §4.3]. The runbook lives with the `gateway` chart; this document records that the absence of platform rotation is a Domino property and not a program choice.
- A test asserts the credential value appears in no audit record and no log line (§10, T-3d).

### 5.8 Extending this shape to `apps/practitioner` — the credential gap §2.2 warned about

**[AMENDMENT — closes a BLOCKING gap, `50-ui-design-system.md` §13 correction 10.]** §2.2 establishes that federation gives a Domino Workspace or App only a Domino-realm session, and warns explicitly against reasoning past the resulting gap: *"[f]ederation does not put caller identity on a Domino Endpoint invocation… that gap must not be reasoned away by pointing at federation."* The same gap exists one level up: `apps/practitioner` (`28-design-advisory.md` §2's case review, `25-failure-intel.md`'s causal exploration) has **no client ID, no token-acquisition path, and no specified credential** for calling `gateway` at all, because it holds a Domino session and a Domino session is not a `fathom`-realm credential.

**Resolution, corrected: a token-exchange operation, not a second credential shape reusing the Endpoint proxy's header name.** `[AMENDMENT — this section originally proposed reusing X-Fathom-Caller-Authorization for a bearer shape with none of §5.4's actual claims (no fathom `iss`, no aud: gateway, no sfx: scope, no delegation) — the same header name validated two structurally incompatible credentials, which a security review correctly identified as two mechanisms wearing one name, with no document specifying which validator applies. 52-practitioner-apps.md §4.4 rule 5 independently proposed the fix below as "the cleanest, and what this document would ask for" — adopted here rather than left as an ask.]`

`POST /api/v1/auth/practitioner-exchange` — a new, narrow token-exchange operation. The practitioner app's co-resident single-container FastAPI process (`50-ui-design-system.md` §6.2's `02 §4.1`-mandated single-container shape) presents its own client-credentials **workload identity** plus the verified Domino identity JWT (the Domino-session-linked `fathom` `sub` from §2.2's broker-linked record) to this operation, over the sanctioned `domino-compute → gateway` NetworkPolicy edge (09 §4.4.2) — `auth`, not `gateway`, is the target, matching this document's own "gateway is the caller, `auth` is the authority over exchange" split (§4.1). `auth` returns a short-lived, ordinary `fathom`-realm **delegated** access token (§3.2's exact shape, `sub` = the linked human, `aud` = the practitioner surface's own manifest targets), reusing §4.2's RFC 8693 exchange machinery with the Domino identity JWT as `subject_token` and the host's workload token as `actor_token`.

**This removes the second credential shape entirely.** The practitioner host's every subsequent call to `gateway` carries exactly one credential — `Authorization: Bearer <the exchanged fathom token>` — identical in shape to every other delegated call in this document, which the gateway already validates unchanged (§5.3) with no second header, no second validator, and no ambiguity about which mechanism applies. `X-Fathom-Caller-Authorization` remains exclusively §5.4's Endpoint-proxy credential; it is never sent by `apps/practitioner`. The gateway never accepts a claimed subject from the practitioner app (§13 item 15's rule, applied identically) — the exchange, not the gateway, is where the Domino identity is verified.

**Consequence for `52-practitioner-apps.md`:** its two-credential wire shape (§4.4), its `host-sends-two-credentials` test, and its §4.7 interim (no `IdentityBlock`, no sign-out, the narrowest-workload-envelope posture) are all superseded by this resolution — the exchanged token carries a real identity block and real `authority_classes`, so `GET /api/v1/gateway/session` (§8.1.2) works for `apps/practitioner` exactly as it does for `apps/web`, with no caller-authority-borne variant needed. `52`'s own P-OQ-3 (*"does the gateway authorize against the caller-authority credential, or merely record it"*) is moot under this resolution — there is no caller-authority credential at the gateway to ask that question about.

---

## 6. ABAC policy evaluation

### 6.1 Decision: OPA, as an in-pod sidecar, with centrally signed bundles

Document 09 §2.1 records the choice as *"OPA or Cedar for ABAC"* from document 01 §14 and leaves it open. **[ESTABLISHED HERE]: OPA, Rego policies, evaluated by a sidecar in every service pod, from a signed bundle built in CI and served by `auth`.**

| Requirement | Why this shape satisfies it |
|---|---|
| *"Enforced by the receiving sub-application… Never delegated to the gateway alone"* [03 §4, obligation 7] | The decision point is **inside the pod**. The claim is literally true and survives a compromised or bypassed gateway. A central PDP service would make every authorization decision a network call to a component the obligation says must not be the sole enforcer |
| One policy, seventeen services | Rego lives once, in `platform/auth/policy/`. No service authors policy; a service that writes `if role == …` in Python is in violation (§13) |
| Auditable authority | A bundle has a revision, is signed, and is built from reviewed files. "What was the authorization policy on that date" is answerable from git plus the bundle revision recorded on each decision |
| **The DDIL constraint** | Document 08 §3.6: the Zero Trust Overlays' DDIL grant is hedged — *"DDIL environments may be able to support disconnected functions but will be managed by centralized ICAM solutions."* That authorizes **a centrally-governed cached policy decision point, not an autonomous shipboard one.** A signed bundle pulled from `auth`, evaluated locally, and expiring against a declared staleness bound is exactly that shape. An edge deployment can decide; it cannot *author* |

**Cedar rejected**, and the rejection is cheap to revisit: the policy *language* matters less here than the *distribution* model, and OPA's signed-bundle mechanism is what makes the DDIL argument above expressible. If Cedar is later preferred, the input document of §6.3 and the decision output of §6.4 are the stable interface, and only the policy files change. Recorded as reversible.

**Sidecar over in-process evaluation:** no mature in-process Rego evaluator exists for Python 3.12 that this document is willing to assert [VERIFY if revisited], and a WASM-compiled bundle inside the service process would put policy compilation into seventeen build pipelines. The sidecar costs one container per pod and keeps policy out of application dependency trees.

### 6.2 Bundle build, distribution, and staleness

```
platform/auth/policy/
├── fathom/
│   ├── authz/entry.rego            # THE single entrypoint: data.fathom.authz.decision
│   ├── authz/side_effects.rego     # §3.4 layer 3          [03 §8.1, §8.3]
│   ├── authz/authority.rego        # §6.4                  [03 §7.2.1, D16]
│   ├── authz/classification.rego   # §6.5                  [03 §7.3, §12, D13]
│   ├── authz/scope.rego            # §6.6                  [03 §8.3]
│   └── authz/dual_control.rego     # §6.4                  [03 §7.2, D16]
├── data/
│   ├── authority_matrix.json       # GENERATED from 03 §7.2.1. Never hand-typed
│   └── classification_lattice.json # GENERATED from 03 §7.3's enums
└── tests/                          # `opa test` — a Rego unit test per table cell
```

| Concern | Rule |
|---|---|
| Generation | `tools/gen_authority_matrix.py` emits `authority_matrix.json` from `packages/canonical-schemas`. CI regenerates and **fails on drift**, the same mechanism document 09 §2.5 uses for OpenAPI. Document 03 §7.2.1's table therefore exists exactly once in executable form |
| Build | `opa build --bundle --signing-key …` in CI; bundle and signature published as artifacts and to the internal index |
| Distribution | `GET /api/v1/auth/policy-bundles/{name}` with `ETag`. Sidecars poll; **signature verification is mandatory and an unverifiable bundle is not loaded** |
| Staleness | The bundle revision and its age are a **mandatory readiness check** named `policy_bundle` (extending document 09 §5.6's five), bounded by `FATHOM_AUTHZ__BUNDLE_MAX_AGE_SECONDS`. Exceeding it makes the service **not ready**. This is the same pattern as read-model lag: a stale policy is a correctness problem, so it must be observable rather than silent |
| Air gap | The bundle is an ordinary OCI/HTTP artifact from the private registry. No sidecar reaches a public network [09 §9.5 item 26] |
| Metrics | `fathom_authz_decisions_total{service,operation_id,allow}`, `fathom_authz_decision_duration_seconds{service}`, `fathom_authz_bundle_revision_info{service,revision}`, `fathom_authz_denials_total{service,reason}` — added to document 09 §5.6's fixed list |

### 6.3 The decision input document

Built by `packages/py-common` from the validated token, the matched route's annotations, and the resource. Fixed here so seventeen services produce one shape.

```json
{
  "principal": {
    "sub": "b31f…",
    "agent_authority": null,
    "act": null,
    "delegation_id": null,
    "authority_classes": ["planner"],
    "unit_uic": "N12345",
    "unit_path": "fleet/tycom-01/isic-04/N12345",
    "billet": "…",
    "qualifications": ["…"],
    "clearance": { "level": "CUI", "caveats": ["FEDCON"], "compartments": [],
                   "cui_categories_authorized": ["SP-CTI"] },
    "scopes": ["sfx:none", "sfx:proposal-only", "sfx:state-changing"],
    "accountable_owner": null,
    "declared_scope": null
  },
  "operation": {
    "sub_app": "maintenance", "operation_id": "maintenance_adjudicate_proposal",
    "method": "PATCH", "side_effects": "state-changing", "agent_eligible": false,
    "domino_endpoint": null
  },
  "action": "adjudicate",
  "resource": {
    "type": "proposal",
    "kind": "interval_change",
    "blast_radius": "class",
    "authority_class": "fleet_authority",
    "requires_dual_control": true,
    "adjudicated_by": null,
    "subject": { "class_id": "51-IIA" },
    "baseline_epoch": 43,
    "classification": { "level": "CUI", "cui_categories": ["SP-CTI"],
                        "dissemination": ["FEDCON"], "compartments": [] }
  },
  "context": {
    "deployment_classification": "CUI",
    "deployment_node": "enterprise",
    "bundle_revision": "…"
  }
}
```

`action` is a closed vocabulary: `read`, `create_proposal`, `claim`, `adjudicate`, `second_adjudicate`, **`counter_sign`**, `write`, `invoke_endpoint`, `retrieve`. **[AMENDMENT]** `counter_sign` is new — added below alongside the corrected `purge`/`rewrap` matrix cells, because a class/fleet-scope purge needs a *third*, distinct action from a *third* distinct person, and reusing `second_adjudicate` for it was the defect this amendment fixes.

### 6.4 Authority versus blast radius — document 03 §7.2.1, executable

`authority_matrix.json`, generated, is document 03 §7.2.1's table verbatim. Note that three cells carry an **alternative set** rather than a single class, one carries a two-stage requirement, and two (`purge`, `rewrap`) carry an **additional** counter-signature by a different class **on top of**, not instead of, same-role dual control:

```json
{
  "anomaly_tag":          { "item": {"any_of": ["maintainer"]},
                            "asset": {"any_of": ["maintainer"]},
                            "class": {"not_applicable": true},
                            "fleet": {"not_applicable": true} },
  "work_candidate":       { "item": {"any_of": ["maintainer", "planner"]},
                            "asset": {"any_of": ["maintainer", "planner"]},
                            "class": {"any_of": ["planner"]},
                            "fleet": {"any_of": ["fleet_authority"]} },
  "requisition":          { "item": {"any_of": ["supply_officer"]},
                            "asset": {"any_of": ["supply_officer"]},
                            "class": {"any_of": ["supply_officer"]},
                            "fleet": {"any_of": ["fleet_authority"]} },
  "interval_change":      { "item": {"any_of": ["planner"]},
                            "asset": {"any_of": ["planner"]},
                            "class": {"any_of": ["fleet_authority"], "dual_control": true},
                            "fleet": {"any_of": ["fleet_authority"], "dual_control": true} },
  "redesign_case":        { "item": {"any_of": ["design_authority"]},
                            "asset": {"any_of": ["design_authority"]},
                            "class": {"any_of": ["design_authority"], "dual_control": true},
                            "fleet": {"any_of": ["design_authority"], "dual_control": true} },
  "configuration_change": { "item": {"any_of": ["maintainer"],
                                     "then_confirmed_by": "registry"},
                            "asset": {"any_of": ["maintainer"],
                                      "then_confirmed_by": "registry"},
                            "class": {"not_applicable": true},
                            "fleet": {"not_applicable": true} },
  "purge":                { "item": {"any_of": ["security_officer"], "dual_control": true},
                            "asset": {"any_of": ["security_officer"], "dual_control": true},
                            "class": {"any_of": ["security_officer"], "dual_control": true,
                                      "requires_counter_signature": true,
                                      "counter_signature_class": "fleet_authority"},
                            "fleet": {"any_of": ["security_officer"], "dual_control": true,
                                      "requires_counter_signature": true,
                                      "counter_signature_class": "fleet_authority"} },
  "rewrap":               { "item": {"any_of": ["security_officer"], "dual_control": true},
                            "asset": {"any_of": ["security_officer"], "dual_control": true},
                            "class": {"any_of": ["security_officer"], "dual_control": true,
                                      "requires_counter_signature": true,
                                      "counter_signature_class": "fleet_authority"},
                            "fleet": {"any_of": ["security_officer"], "dual_control": true,
                                      "requires_counter_signature": true,
                                      "counter_signature_class": "fleet_authority"} }
}
```

**`purge` and `rewrap` were missing from this matrix** — they postdate this document's original authoring (amendments 03-1/03-2). Their item/asset cells are **same-role** dual control, like `interval_change`'s and `redesign_case`'s class/fleet cells: a second `security_officer`, not a different class. **[AMENDMENT — corrected.]** An earlier revision of this matrix had the class/fleet cells' `counter_signature_class` *replace* the second `security_officer` signature, yielding two signatures total (one `security_officer`, one `fleet_authority`) where `32-audit.md` §6.1 and `51-operator-console.md` §16.4/§22 row 19 both independently specify **three**: dual control (two `security_officer`s) **plus** a `fleet_authority` counter-signature, on top. Two independently-authored documents converging on the stricter reading, against this document's own single earlier interpretation of admittedly ambiguous source text, is the signal that the stricter reading is correct. `requires_counter_signature` is now a separate boolean from `dual_control` — both are `true` at class/fleet scope for `purge`/`rewrap`, and the two are checked by two different Rego rules below, guarding two different actions (`second_adjudicate` and the new `counter_sign`).

```rego
package fathom.authz

import rego.v1

# --------------------------------------------------------------------------
# Deny by default. `decision.allow` is true only when some allow rule fires
# AND no deny rule fires.  [03 §15 obligation 7]
# --------------------------------------------------------------------------
default decision := {"allow": false, "reasons": ["no_rule_matched"], "obligations": {}}

decision := {
    "allow": count(deny) == 0,
    "reasons": [r | some r in deny],
    "obligations": obligations,
} if {
    allow_base
}

# --------------------------------------------------------------------------
# allow_base: the POSITIVE gate. [AMENDMENT — this was referenced above and
# defined nowhere in the corpus, a critical omission a security review
# caught: without it, a naive "token validated" placeholder would make every
# action unconditionally allowed except where a deny rule happens to exist —
# and no deny rule below fires on create_proposal, claim, write, or
# invoke_endpoint, so those four actions would have been allow-anything.]
#
# allow_base is intentionally NARROW: it only asserts the request is
# well-formed enough for the deny rules below to evaluate meaningfully. It is
# NOT where authorization decisions are made — every substantive restriction
# is a deny rule, per this file's own "deny by default" comment above. Token
# validity itself is checked upstream (09 §5.5's require_authz dependency,
# evaluated before OPA is ever called); allow_base assumes a validated
# principal and checks only that (a) the action is in the closed vocabulary,
# and (b) the resource type matches what that action operates on.
# --------------------------------------------------------------------------
allow_base if {
    input.action in {"read", "create_proposal", "claim", "adjudicate",
                      "second_adjudicate", "counter_sign", "write",
                      "invoke_endpoint", "retrieve"}
    resource_type_matches_action
}

resource_type_matches_action if {
    input.action in {"create_proposal", "claim", "adjudicate",
                      "second_adjudicate", "counter_sign"}
    input.resource.type == "proposal"
}
resource_type_matches_action if {
    input.action in {"read", "write", "retrieve"}
    input.resource.type in {"domain_record", "tool_call"}
}
resource_type_matches_action if {
    input.action == "invoke_endpoint"
    input.resource.type == "domino_endpoint"
}

# --- ADJUDICATION: 03 §7.2.1 + D16 ---------------------------------------

# An AGENT never adjudicates, of either class. 01 principle 7; §3.3 rule 6.
# [AMENDMENT] Extended to `counter_sign` (new action, above) and to
# `create_proposal` for purge/rewrap specifically — 03 §7.2's standing rule
# that "a purge proposal may never be created or adjudicated by an agent
# principal or an accountable_autonomous identity" binds creation too, and
# this is the Rego-level backing for that rule, not merely 32-audit.md's
# own coordinator-level check (defense in depth, per this policy's own
# convention of checking things a receiving service also checks).
deny contains "agent_may_not_adjudicate" if {
    input.action in {"adjudicate", "second_adjudicate", "counter_sign"}
    is_agent_principal
}

deny contains "agent_may_not_create_purge_or_rewrap" if {
    input.action == "create_proposal"
    input.resource.kind in {"purge", "rewrap"}
    is_agent_principal
}

# [AMENDMENT] `object.get` with a default makes this safe against an ABSENT
# key, not only a null one — `input.principal.agent_authority != null` is
# UNDEFINED (not false) when the key is missing entirely, which would make
# the two deny rules above silently not fire for a request that omitted the
# field rather than setting it to null. This is the same shape of bug the
# hardcoded second-signature check was (31 §6.4, above): a check written
# against one representation that a different-but-equally-valid input shape
# defeats silently.
is_agent_principal if object.get(input.principal, "agent_authority", null) != null

cell := data.fathom.authority_matrix[input.resource.kind][input.resource.blast_radius]

deny contains "authority_class_not_applicable_at_scope" if {
    input.action == "adjudicate"
    cell.not_applicable
}

# NO IMPLICIT HIERARCHY (§2.4): explicit set membership, never a rank compare.
deny contains sprintf(
    "authority_class_insufficient: need any_of %v, principal holds %v",
    [cell.any_of, input.principal.authority_classes],
) if {
    input.action == "adjudicate"
    not cell.not_applicable
    count({c | some c in cell.any_of
                 some p in input.principal.authority_classes
                 c == p}) == 0
}

# 03 §7.2's re-validation rule: the stored field must still agree with the
# table, "in case the scope was corrected between proposal and adjudication".
deny contains "authority_class_field_stale" if {
    input.action == "adjudicate"
    not cell.not_applicable
    not input.resource.authority_class in cell.any_of
}

# --- DUAL CONTROL: mandatory at class and fleet scope, and for any kind with
#     external legal effect.  03 §7.2 rule 4, D16 -------------------------
dual_required if input.resource.blast_radius in {"class", "fleet"}
dual_required if cell.dual_control
dual_required if input.resource.kind in {"requisition"}      # external legal effect

deny contains "dual_control_required_but_not_declared" if {
    input.action == "adjudicate"
    dual_required
    not input.resource.requires_dual_control
}

# The second signature is a DIFFERENT human, and at class/fleet scope on an
# interval_change it is fleet_authority's.  03 §7.2.1.
deny contains "second_adjudicator_must_differ" if {
    input.action == "second_adjudicate"
    input.principal.sub == input.resource.adjudicated_by
}

# The class(es) the SECOND signature must hold. ALWAYS same-role dual control
# (a second member of cell.any_of) — this is the "dual" in dual control, and
# it is never satisfied by the counter-signature below, which is a THIRD,
# additional party at class/fleet-scope purge/rewrap, not a substitute for
# the second same-role signer.
# [AMENDMENT — this rule previously redirected to counter_signature_class
# when present, which silently reduced a required THREE-signature control
# (32-audit.md §6.1; 51-operator-console.md §16.4, §22 row 19) to two. Two
# independently-authored documents specified three; this rule now enforces
# exactly the same-role second signature for every kind, always, and the
# counter-signature is a separate, additional deny rule below.]
second_signature_any_of := cell.any_of

# GENERALIZED to every kind, not just interval_change. The prior rule checked
# only input.resource.kind == "interval_change", which meant a class- or
# fleet-scoped redesign_case (or purge/rewrap) required a SECOND SIGNER, but
# checked NOTHING about that signer's authority — satisfiable by any
# authenticated human distinct from the first adjudicator. This is the
# defect Redesign Case Builder's build-framework agent found (42 §18 item
# 17): "nothing in this runtime can compensate: the agent cannot adjudicate,
# so it cannot detect or refuse an under-authorized second signature."
deny contains sprintf(
    "second_adjudicator_authority_insufficient: need any_of %v, principal holds %v",
    [second_signature_any_of, input.principal.authority_classes],
) if {
    input.action == "second_adjudicate"
    dual_required
    count({c | some c in second_signature_any_of
                 some p in input.principal.authority_classes
                 c == p}) == 0
}

# --- COUNTER-SIGNATURE: a THIRD, additional party, distinct from both
#     adjudicators, required only where the cell says so (purge/rewrap at
#     class/fleet scope: 03 §7.2.1's `fleet_authority` counter-signature).
#     [AMENDMENT — new action, new rules, closing the 2-vs-3-signature defect
#     the second_signature_any_of fix above also closes from the other side.]
counter_signature_required if cell.requires_counter_signature

deny contains "counter_signature_required_but_not_declared" if {
    input.action == "adjudicate"
    counter_signature_required
    not input.resource.requires_counter_signature
}

deny contains "counter_signer_must_differ" if {
    input.action == "counter_sign"
    input.principal.sub in {input.resource.adjudicated_by, input.resource.second_adjudicator}
}

deny contains sprintf(
    "counter_signer_authority_insufficient: need %v, principal holds %v",
    [cell.counter_signature_class, input.principal.authority_classes],
) if {
    input.action == "counter_sign"
    counter_signature_required
    not cell.counter_signature_class in input.principal.authority_classes
}

obligations := {
    "dual_control_required": dual_required,
    "counter_signature_required": counter_signature_required,
    "classification_predicate": classification_predicate,
    "redact_fields": redact_fields,
}
```

**The `any_of` finding.** Document 03 §7.2 gives `Proposal` a **singular** `authority_class` field, while §7.2.1's table has cells with two acceptable classes (`work_candidate` at item/asset scope is *"`maintainer` or `planner`"*). A single field cannot carry an alternative set. **Resolution [ESTABLISHED HERE]:** the *policy* is authoritative and evaluates `any_of` from the generated matrix; `Proposal.authority_class` records the cell's *first* value for display, audit, and queue filtering, and is re-validated at adjudication against membership in `any_of` — which is what the `authority_class_field_stale` rule above does. Recorded as amendment **A-3** in §14, proposing `authority_class_any_of[]` on the schema.

**The two-stage cell.** `configuration_change` is *"`maintainer` (edge-submitted) then Registry confirmation"* [03 §7.2.1]. The policy authorizes the maintainer's submission; **Registry confirmation is a domain state transition in `registry`, not an authorization decision**, and is specified by `registry`'s own document. The matrix carries `then_confirmed_by` so the obligation is visible at the decision point rather than assumed.

### 6.5 Classification and compartment access

```rego
# 03 §7.3, §12.  Level dominance on ONE scale, because principal clearance and
# ClassificationLabel.level share the U|CUI|S|TS vocabulary (§2.3).
level_rank := {"U": 0, "CUI": 1, "S": 2, "TS": 3}

deny contains "clearance_level_insufficient" if {
    level_rank[input.resource.classification.level] >
        level_rank[input.principal.clearance.level]
}

deny contains sprintf("compartment_not_held: %v", [missing]) if {
    missing := {c | some c in input.resource.classification.compartments
                    not c in input.principal.clearance.compartments}
    count(missing) > 0
}

deny contains sprintf("dissemination_control_unsatisfied: %v", [unmet]) if {
    unmet := {d | some d in input.resource.classification.dissemination
                  not d in input.principal.clearance.caveats}
    count(unmet) > 0
}

deny contains sprintf("cui_category_not_authorized: %v", [unmet]) if {
    unmet := {k | some k in input.resource.classification.cui_categories
                  not k in input.principal.clearance.cui_categories_authorized}
    count(unmet) > 0
}

# Retired markings are a hard failure, not a warning. DoDI 5200.48 §3.4.b via
# 03 §7.3: "'FOUO' and 'U//FOUO' are RETIRED markings".
deny contains "retired_marking_present" if {
    some d in input.resource.classification.dissemination
    d in {"FOUO", "U//FOUO"}
}

# The demonstration operates at a SINGLE level and says so, rather than
# implying multi-level capability.  03 §12, 06 §5.
deny contains "above_deployment_declared_level" if {
    level_rank[input.resource.classification.level] >
        level_rank[input.context.deployment_classification]
}

# --- THE PREDICATE OBLIGATION: no post-filtering, ever.  D13, 09 §9.4 item 22
classification_predicate := {
    "max_level": input.principal.clearance.level,
    "compartments_held": input.principal.clearance.compartments,
    "caveats_held": input.principal.clearance.caveats,
    "cui_categories_authorized": input.principal.clearance.cui_categories_authorized,
} if input.action in {"read", "retrieve"}
```

**The predicate obligation is the mechanism, not a convenience.** For `read` and `retrieve` actions the decision returns a predicate the service pushes **into** its SQL `WHERE` clause or its pgvector query, because *"[t]he vector store enforces at query time rather than post-filtering, because post-filtering leaks the existence of records"* [03 §7.3, 04 §11, D13]. A service that fetches rows and then drops them is in violation of document 09 §9.4 item 22 even if the user never sees the dropped rows — the leak is in the count, the latency, and the cursor.

**Aggregation** remains Fleet Status's design constraint, not this policy's: *"[a] rollup whose value moves when a compartmented item degrades discloses that item's existence"* [03 §7.3, D13]. The policy supplies the predicate; it cannot make a rollup safe, and this document does not claim it does.

### 6.6 Declared-scope containment for autonomous agents

```rego
# 03 §8.3: an accountable-autonomous agent "[c]annot read outside its declared
# scope."  Containment is checked on the REQUEST's subject identifiers.
deny contains "outside_declared_scope" if {
    input.principal.agent_authority == "accountable_autonomous"
    not scope_contains_subject
}

scope_contains_subject if input.principal.declared_scope.fleet == true
scope_contains_subject if input.resource.subject.asset_id in
                          input.principal.declared_scope.assets
scope_contains_subject if input.resource.subject.class_id in
                          input.principal.declared_scope.class_ids

deny contains "aggregate_not_in_declared_scope" if {
    input.principal.agent_authority == "accountable_autonomous"
    not input.resource.type in input.principal.declared_scope.aggregates
}

# An autonomous agent's clearance never exceeds its accountable owner's (§3.3
# rule 3). Re-derived here rather than trusted, so a mis-minted token fails.
deny contains "clearance_exceeds_accountable_owner" if {
    input.principal.agent_authority == "accountable_autonomous"
    level_rank[input.principal.clearance.level] >
        level_rank[input.principal.declared_scope.clearance_ceiling.level]
}
```

### 6.7 The one sanctioned wall-clock comparison

Document 03 §5.4 and document 09 §9.2 item 7 forbid a wall clock arbitrating *anything* — merges, ordering, last-writer-wins, timeouts, retry backoff, lease expiry. **Token `exp` validation is nevertheless a wall-clock comparison, and it is the single sanctioned one.** The distinction and the compensating rule, both **[ESTABLISHED HERE]**:

- `exp` is not *arbitration between two writers*; it is a comparison against an externally-issued absolute instant, which is what JWT is. There is no monotonic alternative available across processes.
- Because it is unavoidable, it is made *observable*: the service reads its own `sync_quality` block [03 §5.4, 11 §4] and **refuses agent traffic when `dispersion_ms` exceeds the shortest configured agent-token TTL** — `503 urn:fathom:problem:auth:time-uncertain`, counted in `fathom_authz_denials_total{reason="time_uncertain"}`. Rationale, direct from 08 §3.3 and 03 §5.4: a node whose published epsilon is larger than a credential's lifetime cannot tell an expired token from a valid one, and *"[a] time service that declares itself untrusted is far safer than one confidently serving wrong time."*
- Every other duration in this service — delegation lease, `introspection_max_age`, bundle age, proxy deadline, `resumable_until` evaluation — uses `time.monotonic()`.

### 6.8 Decision caching

| Action class | Caching |
|---|---|
| `read` / `retrieve` under a human token | Decision cacheable in-process, keyed on `(sub, operation_id, resource classification, bundle_revision)`, bounded by a monotonic TTL |
| Anything under an agent token, `proposal-only` or `state-changing` | **Not cacheable.** Introspection freshness (§4.6) is part of the decision |
| `adjudicate` / `second_adjudicate` | **Never cached.** Evaluated per request against the live proposal, because 03 §7.2's re-validation rule is a per-adjudication obligation |
| Any bundle revision change | Invalidates the entire cache |

---

## 7. CAC/PIV integration path

### 7.1 The claim, and what would make it false

Document 01 §5 calls this service *"CAC/PIV-ready"*; document 04 §11 states *"CAC and PIV substitution is an identity-provider change, not an application change."* Asserted, that is a hope. This section makes it a **testable property** by naming the exact configuration surface that changes and adding a test that fails if anything outside that surface has to change.

**What would make the claim false:** any service reading a claim that only the password flow produces; any policy branching on `amr`; any code deriving authority from an email address or username; a `sub` that changes when the authenticator changes.

### 7.2 The exact change surface

**Three files, all under `platform/auth/keycloak/`, plus one ingress setting. Nothing else.**

| # | Artifact | Change |
|---|---|---|
| 1 | `realm-fathom.json` → `identityProviders` / `authenticationFlows` | Add a `browser-x509` authentication flow whose first execution is Keycloak's **X.509/Validate Username Form** authenticator, and bind it as the realm's browser flow. The existing `browser` flow is retained, disabled, for rollback |
| 2 | `realm-fathom.json` → the x509 authenticator config | Certificate-to-user mapping: which certificate field is extracted, which user attribute it matches, whether CRL/OCSP checking is enabled, and the trust store reference. **[VERIFY]** — see §7.4 |
| 3 | `realm-fathom.json` → `components` (truststore / SPI) | The DoD PKI trust anchors and the certificate-lookup provider appropriate to how TLS terminates |
| 4 | Ingress (`deploy/helm/…/gateway` and the Keycloak Service) | Request or require a client certificate on the Keycloak login path and pass it to Keycloak by the configured lookup mechanism. This is an ingress annotation, not application code |

**What does not change, and this is the substance of the claim:**

- No FastAPI service code, in any of the seventeen.
- No claim name, no claim structure, no `fathom.identity` field (§3.1). `edipi` goes from `null` to populated, which is additive.
- No OPA policy file and no `authority_matrix.json` entry.
- No `AuthorityClass` derivation: authority still comes from realm roles derived from billet (§2.4), and a certificate carries no billet.
- No token lifetime, audience, or `sfx:` scope rule.
- No change to the token-exchange flow (§4): a delegated token derives from whatever the user authenticated with, and the exchange does not inspect `amr`.

**The one honest exception.** Step-up assurance becomes *expressible* once a hardware credential exists: a dual-control second signature may be required to carry an `acr` at or above a configured value. That is a **value in policy data**, added to `authority_matrix.json` generation, not application code — and it is optional. It is called out because a section claiming "nothing else changes" that quietly needed a policy edit would be the kind of claim this document exists to stop.

### 7.3 The test that makes it verifiable

`packages/contracts/conformance/auth/test_idp_swap_claim_parity.py`:

> Provision one user record. Obtain a token through the password flow. Reconfigure the realm to `browser-x509` from the committed realm file and obtain a token for the same user through a client certificate presented against a test CA. **Assert the two decoded token bodies are equal after removing `jti`, `iat`, `exp`, `auth_time`, `amr`, `acr`, `sid`, and `fathom.identity.edipi`.** Then replay a fixed corpus of authorization decisions with both tokens against the OPA bundle and assert identical decisions, including obligations.

If a future change makes a service depend on the authenticator, this test fails, and document 04 §11's sentence stops being true in CI rather than at an accreditation review.

### 7.4 What this document does not assert

**[VERIFY]** — each of the following is a program action against primary documentation, and document 08 §8's *"do not present as fact"* discipline applies:

- The exact certificate field carrying the EDIPI in a current DoD CAC or PIV authentication certificate, and the corresponding Keycloak certificate-identity-source setting. Document 08 establishes **no** verified DoD PKI certificate-profile reference, and this document does not invent one.
- DoD PKI trust-anchor distribution, CRL/OCSP availability inside an air-gapped enclave, and the revocation-checking posture the authorizing official requires.
- Whether Keycloak's x509 browser authenticator, the declarative user profile, and standard token exchange are all available and mutually compatible in the pinned Keycloak version.
- Whether CAC/PIV authentication satisfies the multifactor control selection for the applicable baseline. **Control selection follows the authorizing official's baseline determination** [08 §3.2, §3.3]; this document selects no controls it did not find in document 08.

---

## 8. API surface

Base path `/api/v1/auth/` [03 §4]. Scaffold, layering, middleware order, problem details, idempotency, ETag, pagination, and health routes are document 09 §4–§5 verbatim and are not restated. Every operation declares `x-substitution` and `x-side-effects` [03 §4.1]; **no operation on `auth` is ever `x-agent-eligible`** — an agent has no business minting or inspecting authority.

| Operation | `x-side-effects` | `x-substitution` | Purpose |
|---|---|---|---|
| `POST /delegations` | `state-changing` | `internal` | Issue a delegated token (§4.1–§4.2). Requires a **human** subject token; `403 …:no-delegating-subject` for a workload-only subject. `Idempotency-Key` required |
| `GET /delegations/{delegation_id}` | `none` | `internal` | Status: `active` \| `terminated` \| `expired`, with `terminated_reason` |
| `GET /delegations?changed_since=&cursor=` | `none` | `internal` | The change feed backing consumers' revoked-`jti` read model [03 §4, obligation 5]. Returns identifiers and status only — never a token |
| `POST /delegations/{delegation_id}/terminate` | `state-changing` | `internal` | Revoke. `If-Match` required |
| `POST /delegations/{delegation_id}/introspections` | `none` | `internal` | RFC 7662-shaped active check (§4.6). `none` because it alters nothing; it is the hottest operation in the service |
| `POST /autonomous-grants` | `state-changing` | `internal` | Issue an `accountable_autonomous` token (§3.3). Rejects without `accountable_owner` and a non-empty `declared_scope`. `declared_scope.fleet: true` additionally requires a second, distinct `fleet_authority` signature |
| `GET /autonomous-grants/{grant_id}` | `none` | `internal` | Grant detail, including the owner and declared scope |
| `POST /autonomous-grants/{grant_id}/terminate` | `state-changing` | `internal` | Revoke |
| `POST /agent-runs` | `state-changing` | `internal` | Open a run record (§4.3) |
| `GET /agent-runs/{run_id}` | `none` | `internal` | Run status, checkpoint reference, termination reason |
| `POST /agent-runs/{run_id}/checkpoint` | `state-changing` | `internal` | Record `checkpoint_ref` + `checkpoint_hash`. **Rejects a body containing anything token-shaped** |
| `POST /agent-runs/{run_id}/terminate` | `state-changing` | `internal` | Terminate and revoke, atomically (§4.4) |
| `POST /agent-runs/{run_id}/resume` | `state-changing` | `internal` | New run from a checkpoint. Human token required; all §4.4 refusal conditions apply |
| `POST /authority-checks` | `none` | `internal` | **Advisory only.** Answers "may this principal adjudicate this proposal" so the gateway can render a queue without enabled-looking rows nobody may act on. **Never the enforcement point** — enforcement is the owning sub-application's, per 03 §15 obligation 7, and the response says so in a `advisory: true` field |
| `GET /policy-bundles/{name}` | `none` | `required` | Signed OPA bundle (§6.2). `ETag` on revision. `x-substitution: required` because a substituting identity implementation must still serve policy to seventeen sidecars |
| `GET /principals/{sub}` | `none` | `internal` | Display attributes for audit rendering and the adjudication queue. Redacted per the caller's own clearance — a principal record is itself subject to §6.5 |
| `GET /healthz` `GET /readyz` `GET /metrics` | — | — | Document 09 §5.6, plus the `policy_bundle` check of §6.2 and a `keycloak` reachability check |

**Naming carve-outs** [03 §4, C23]: none. Every path above is a plural collection or a sub-resource action on one.

**`auth` calls nothing but Keycloak, `audit`, and its own database.** It does not call `reference-data` on the request path — attribute values are provisioned into the realm, not resolved per request, because an authorization decision must not depend on a second service being up.

---

## 9. Events

`auth` is bound by 03 §15 obligation 2 like every other implementation: *"[e]mits an event for every state change reachable through its contract; no state change without its event."* Two topics, both through the transactional outbox [03 §5.2, 11].

| Topic | Events | Declared consumers |
|---|---|---|
| `fathom.auth.delegation.v1` | `delegation.issued`, `delegation.terminated`, `delegation.expired`, `autonomous_grant.issued`, `autonomous_grant.terminated` | `audit`; `gateway` and the nine sub-applications for the deny-list read model (§4.6) |
| `fathom.auth.agent_run.v1` | `agent_run.started`, `agent_run.terminated_authority_lapsed`, `agent_run.terminated_pod_restart`, `agent_run.resumed`, `agent_run.completed` | `audit` |

| Rule | Detail |
|---|---|
| **No token, ever, in a payload** | Payloads carry `jti`, `delegation_id`, `grant_id`, subjects, and status. A payload carrying a credential would put it in a broker with 30-day retention |
| Partition key | `subject_sub` [03 §5.1 — *"[f]leet-scoped, NIIN-scoped, and class-scoped events partition on their own scope identifier"*; a principal is its own scope]. Per-principal ordering is the only ordering any consumer needs |
| Envelope `scope` | **`fleet`** — the singleton scope requiring no subject identifier [03 §5.4]. Document 03 §5.4's `scope` enumeration has no `principal` value, and `fleet` is the only member that does not force an inapplicable identifier. Recorded as amendment **A-5** in §14 |
| Compaction | `fathom.auth.delegation.v1` is compacted on `delegation_id`/`grant_id` — **the aggregate key, never the partition key** [03 §5.1, D5] |
| Retention | Domain-event tier, 30 days. The **authoritative** long-term record is `audit`, not the topic — the bus is not a rebuild source [03 §5.1, D5], and `GET /delegations?changed_since=` is the rebuild path |
| Consumer rule | The read model may **deny** only (§4.6). A consumer that allows on the strength of a possibly-lagging read model has reintroduced the lapse defect |

---

## 10. Testing

Four tiers per document 09 §4.7, plus the shared conformance suite at `packages/contracts/conformance/auth/` collected unmodified. **The three tests the design turns on are T-1, T-2, and T-3; a review that finds them missing should stop there.**

### 10.1 The mandated tests

| ID | Test | Asserts |
|---|---|---|
| **T-1a** | **An `accountable_autonomous` token cannot call a `state-changing` operation even when presented.** Mint a **validly signed** token from the test realm with `fathom.agent.authority = accountable_autonomous` **and** `sfx:state-changing` injected into `scope` — i.e. deliberately forge the issuer-side failure — then call a real `state-changing` operation on a real sub-application instance | `403 urn:fathom:problem:auth:side-effects-not-permitted`; no state change; no event emitted; a denial counted with `reason="side_effects_not_permitted"`. **The point is that the RECEIVER refuses.** A test that only shows the issuer never mints the scope proves nothing about the enforcement point 03 §15 obligation 7 names |
| **T-1b** | The realm **refuses to mint** `sfx:state-changing` for an autonomous client | Layer 1 of §3.4 independently. Both layers are tested because either alone is a single point of failure |
| **T-1c** | Same forged token against a `proposal-only` and a `none` operation | Allowed (given scope and audience) — the restriction is exactly 03 §8.3's, not a blanket ban |
| **T-2a** | **Mid-run lapse — expiry.** Issue a delegated token with a very short TTL, start a run, let it lapse, make a tool call | `401 …:authority-lapsed`; run `status = terminated_authority_lapsed`; `checkpoint_ref` and `checkpoint_hash` set; delegation revoked; **no proposal exists created after `exp`**; the runtime made no retry and requested no other credential |
| **T-2b** | **Mid-run lapse — pod restart.** SIGKILL the runtime container mid-run and let it restart | The restarted process terminates the run; **the checkpoint contains no token** (asserted by scanning the serialized object for anything JWT-shaped); `POST /delegations` presented with only the workload's own client-credentials token returns `403 …:no-delegating-subject`; no proposal was created after the restart |
| **T-2c** | **Resume.** Resume with the original human's token; then attempt resume with a different human's token, after `resumable_until`, and with a mutated checkpoint object | First succeeds with a new `run_id` and `resumed_from_run_id` set; the other three are refused with distinct problem types |
| **T-3a** | **Domino Endpoint proxy audit binding.** A stub Domino Endpoint (testcontainer) that requires a static token and logs nothing about callers. Invoke `pdm_what_if` under a delegated token, through PdM, through the proxy | An audit record exists binding `caller.subject_sub`, `caller.act_sub`, `agent_id`, `agent_version`, `delegation_id`, and `jti` to that `invocation_id`, `domino_endpoint`, and `model_version`; `immediate_caller_workload == "pdm"`; `correlation_id` matches end to end |
| **T-3b** | **Attribution survives a crash.** Fault-inject a proxy kill between the pre-write and the Endpoint call, and again mid-call | An intent record with `outcome=pending` exists in both cases. **No Endpoint invocation is ever unattributable** — the property that cannot be recovered later, because Domino keeps no per-caller trail [02 §4.3] |
| **T-3c** | Timeout semantics | `outcome=timeout_result_unknown`, never an outcome implying non-execution [02 §4.3: a timed-out request is not cancelled] |
| **T-3d** | Credential hygiene | The static Endpoint credential appears in no audit record, no problem detail, and no log line across the whole test run |
| **T-3e** | Audience gating | A delegated token whose manifest selected no operation declaring `x-domino-endpoint` is refused by the proxy with `403 …:audience-mismatch` |

### 10.2 The rest

| ID | Test | Asserts |
|---|---|---|
| T-4 | **Federation identity parity.** The same human authenticating directly and through Domino's brokered flow | Identical `sub` and identical `fathom.identity` block. This is document 01 §5's *"one identity spans both planes"*, made checkable |
| T-5 | **Delegated reach equals user reach.** Replay a decision corpus with a user token and with a delegated token derived from it | Identical decisions and obligations. 01 §8.5's *"cannot read what the maintainer cannot read"* |
| T-6 | **No agent adjudicates.** Both agent classes, against `adjudicate` and `second_adjudicate` | `403 …:agent-may-not-adjudicate`, regardless of `authority_classes` |
| T-7 | **Authority matrix exhaustiveness.** Property test over the full cross-product of 03 §7.2.1's `kind` × `blast_radius` × **the six classes** (`security_officer` included — **[AMENDMENT]** this test previously iterated only the pre-amendment-03-1 five, which meant every `purge`/`rewrap` cell, the only cells `security_officer` appears in, was untested by the corpus's own exhaustiveness check) | Every cell's allow/deny matches the table exactly; an uncovered cell **fails**; `not_applicable` cells deny; `any_of` cells accept either class; **no implicit hierarchy** — `fleet_authority` is denied on `anomaly_tag`; `purge`/`rewrap`'s dual-control and counter-signature cells (§6.4) are exercised, not merely present |
| T-8 | **Dual control.** Class and fleet scope, and external-legal-effect kinds | Required; second adjudicator must differ from the first; the second signature is checked against the matrix's `second_signature_any_of` (same-role `any_of` by default, `counter_signature_class` for `purge`/`rewrap`) for **every** kind requiring dual control, not `interval_change` alone |
| T-9 | **Re-validation.** Adjudicate a proposal whose `blast_radius` was corrected after creation | `authority_class_field_stale` denial — 03 §7.2's *"[r]e-validation at approval is mandatory"* |
| T-10 | **Classification.** Level dominance, missing compartment, unmet dissemination control, unauthorized CUI category, retired `FOUO` marking, above-deployment-level | Each denied with its own reason string |
| T-11 | **No post-filtering.** For `read`/`retrieve` the decision returns a `classification_predicate` and the service's emitted SQL / vector query contains it | D13, 09 §9.4 item 22. Asserted on the emitted query, not on the result set — a passing result-set assertion is exactly what a post-filter would produce |
| T-12 | **Declared-scope containment.** An autonomous token reading outside its assets, outside its aggregates, or above its clearance ceiling | `403 …:outside-declared-scope` / `clearance_exceeds_accountable_owner` |
| T-13 | **Grant validation.** `POST /autonomous-grants` without `accountable_owner`, with a disabled owner, with an empty `declared_scope`, and with `fleet: true` and one signature | Each refused with its own problem type |
| T-14 | **Token hardening.** `alg: none`; symmetric `alg`; wrong `iss`; wrong `aud`; a token carrying both `fathom.agent` and a human interactive scope; a delegated token with no `act` | All rejected at §3.5 steps 1–4 |
| T-15 | **Time uncertainty.** `sync_quality.dispersion_ms` exceeding the shortest agent TTL | `503 …:time-uncertain`; no agent request authorized (§6.7) |
| T-16 | **Bundle integrity and staleness.** Unsigned bundle; bundle signed by the wrong key; bundle older than the bound | Not loaded; service **not ready**; never an allow |
| T-17 | **OPA unreachable** | `503`, never an allow (§3.5) |
| T-18 | **CAC/PIV claim parity** | §7.3 |
| T-19 | **Revocation propagation.** Terminate a delegation, then present the still-unexpired token to a `proposal-only` operation | Refused via introspection even before the deny-list event arrives; and refused when introspection is unreachable (fail closed) |
| T-20 | **Realm as code.** The running realm's exported configuration equals `realm-fathom.json` | Prevents console drift (§2.1) |

Fixtures follow document 09 §4.7's four-fixture contract; the `principal_factory` fixture referenced there is **provided by this service's build** into `packages/py-common.testing` so that seventeen services do not each hand-roll a token minter — and so that no service's tests can construct a principal shape the realm cannot actually issue.

---

## 11. Deployment

| Concern | Value |
|---|---|
| Chart | `platform/auth/helm/`, one chart, document 09 §4.4's mandatory `values.yaml` shape, `slug: auth`, `apiMajor: 1` |
| Workloads | Keycloak StatefulSet; `auth` Deployment; a realm-import Job as a `pre-install,pre-upgrade` hook with `backoffLimit: 0` [09 §6.3 item 6] |
| Database | `fathom-auth-pg`, schemas `keycloak` and `auth` (§2.1) |
| Secrets | External Secrets Operator only. Realm admin credential, the exchanger client's private key, and the bundle signing key. **The Domino Endpoint static credential belongs to `gateway`, not here** (§5.7) |
| Scaling | HPA on request rate. The `introspections` operation is the hot path |
| OPA sidecar | Injected by the `_fathom-common` library chart when `authz.opa.enabled: true` — **which is the default and is never `false` in any environment**, exactly as `networkPolicy.enabled` is never `false` [09 §4.4.2] |
| NetworkPolicy | Unchanged for the nine: `any service → auth` is already a sanctioned edge [09 §4.4.2]. `auth` egress: own database, event bus, `audit`, Keycloak. The OPA sidecar is in-pod and needs **no** policy change beyond egress to `auth` for bundle polling |
| **One amendment required** | The Endpoint proxy needs `<sub-application> → gateway` for the single proxy operation. Not in document 09 §4.4.2's sanctioned set. **Requires an ADR plus an edit to document 09** — amendment **A-4** in §14. Do not add the peer without both |
| Edge profile | `auth` is enterprise-only. An edge deployment caches a **signed bundle** and a **short-lived token set**; it does not run an authority. Document 08 §3.6: the Zero Trust Overlays authorize DDIL operation *"managed by centralized ICAM solutions"* — a cached PDP, never an autonomous shipboard PDP. The divergence budget for authority caching is set with document 11's budgets [03 §11]; **no interval is invented here** |

---

## 12. Accreditation posture

Every claim here traces to document 08. Nothing beyond it is asserted.

| Item | Position |
|---|---|
| RMF authority | **DoDI 8510.01, reissued 19 Jul 2022** and retitled — *"Risk Management Framework for DoD Systems."* Document 08 §7 flags the widely-mirrored 2014 citation as stale; cite the 2022 reissue [08 §3.2, §7] |
| Cybersecurity policy | **DoDI 8500.01**, 14 Mar 2014, Change 1 effective 7 Oct 2019 [08 §3.2] |
| Control catalog | **NIST SP 800-53 Rev 5**, release 5.2.0 [08 §3.2] |
| **Impact level — undetermined, and this service does not assume one** | IL5 no longer covers CUI: *"Redefined 2 July 2025: IL4 expanded to cover both Moderate and High confidentiality and integrity and is now the CUI level; IL5 became 'Unclassified National Security System / National Security Information.'"* **This requires a written authorizing-official determination of NSS status**, which also settles federal AI-policy applicability — *"[o]ne memo, two questions"* [08 §3.3, §6, §9]. Consequence for this service: **if NSS, CNSSI 1253 applies and uses separate C/I/A levels rather than a high-water mark, and CNSSP 32 requires FedRAMP High plus CNSSI 1253 Appendix D overlays at HHx** [08 §3.2]. The ABAC attribute model in §2.3 is unaffected either way; the *control selection* over it is not, and this document selects none |
| Application security | **ASD STIG V6R4**, 1 Oct 2025 [08 §3.2] |
| Cloud | **CSP SRG V1R7**, 30 Jun 2026. **Do not cite the superseded Cloud Computing SRG** — replaced 14 Jun 2024 [08 §3.2, §6] |
| Zero Trust | **DoD Zero Trust Overlays v1.1, Jun 2024**, as a tailoring source — the only document that both accommodates DDIL and supplies the SC-45/AU-8 parameters. **Do not cite the Zero Trust Reference Architecture v2.0 as DDIL authority; it does not address DDIL at all** [08 §3.2] |
| Audit timestamps | 1 ms granularity, comparison at least daily, 1 s resync threshold, per the Overlays' SC-45/SC-45(1) selection [08 §3.3]. Applied to §4.6's and §5.5's records |
| Controls this service's audit records support | **AU-10** (sign records — non-repudiation), **AU-12(1)** (time-correlated trail, 1 ms), **AU-9(3)**, **AU-6(3)** (correlate repositories), **SC-16** (bind classification and provenance), **SC-8/8(1)** and **SC-28/28(1)** — all named by document 08 §3.5. No IA-family selection is made here |
| Cross-domain | **DoDI 8540.01 does not apply to same-level replication** — it scopes itself to *"the interconnection of information systems of different security domains,"* and *"Impact Levels are a DoW construct only"* [08 §3.3]. Two same-level enclaves are one security domain. Crossing **classification** levels is genuinely cross-domain and is a different design [03 §12] |
| Demonstration classification | Single level, stated rather than implied to be multi-level capable [03 §12, 06 §5]. The policy of §6.5 is written multi-level-capable and **tested** at more than one level, which is the honest version of "ready" |
| Base images | Iron Bank confers no CtF and no ATO, inherits only evidence, and is IL2-only [08 §3.6]. No inheritance is claimed for the Keycloak or OPA image |
| Markings | `FOUO` and `U//FOUO` are retired [03 §7.3, DoDI 5200.48 §3.4.b] and are rejected by policy (§6.5), not merely avoided in prose |

---

## 13. Explicit DO-NOT list

Each item carries the finding or citation that makes it a defect rather than a preference. A reviewer may cite the number and stop reading.

### 13.1 The two findings this service exists to close

1. **Do not let delegated authority be assumed available for autonomous work.** Event-triggered and scheduled work has no requesting user — the PMA Pre-Screener fires on mission completion, the Readiness Narrative and scheduled evaluation run on a schedule, and `POST /what-if` reaches a Domino Endpoint whose auth is a static token with no per-caller audit. Use `accountable_autonomous` with a **named accountable human owner** and a **declared scope**, and record every run to Audit with that owner. A scheduled job running under a plain workload identity with no named owner is the defect, not a shortcut. *(**D12**; 03 §8.3, 01 §8.5)*
2. **Do not let a proposal be adjudicated without an authority-class check against blast radius.** One `adjudicated_by` field spanning a maintainer's anomaly tag and an `interval_change` that suppresses a preventive task across an entire class is exactly the finding. The check is the generated matrix of §6.4, evaluated per adjudication, with dual control mandatory at class and fleet scope and for any kind with external legal effect — and the second signature from a **different** human. *(**D16**; 03 §7.2, §7.2.1)*

### 13.2 Tokens and authority

3. **Do not continue an agent run under a service identity after a token expires or a pod restarts.** Terminate with a resumable checkpoint. Do not retry, do not re-authenticate as the workload, do not create a proposal after authority has lapsed. *(**D12**; 01 §8.5, 03 §8.3; §4.4)*
4. **Do not issue a refresh token to an agent of either class**, and do not grant `offline_access` to an agent client. An agent that can renew its own authority has authority independent of its user. *(§3.2)*
5. **Do not write a token to disk, to a checkpoint, to a log line, to an event payload, or to an audit record.** *(09 §4.8; §3.6, §4.4, §9)*
6. **Do not put a human's authority classes into an `accountable_autonomous` token's identity block.** They belong in `accountable_owner`, for accountability, and they authorize nothing. *(§3.3 rule 4)*
7. **Do not let an agent token of either class adjudicate anything.** Adjudication requires the absence of `fathom.agent`. *(01 principle 7; §3.3 rule 6, T-6)*
8. **Do not test the side-effect restriction only at the issuer.** The receiver is the enforcement point; test it with a validly signed token that carries the forbidden scope. *(03 §15 obligation 7; §3.4, T-1a)*
9. **Do not use symmetric token signing, and do not accept `alg: none`.** Symmetric signing gives every service the power to mint. *(§2.1, T-14)*
10. **Do not gate agent eligibility on HTTP method.** Eligibility follows declared `x-side-effects`; a method check wrongly excludes the compute-only `POST` operations three agents require. *(**C1 / D11**; 03 §4.1, §8.1)*
11. **Do not treat `authority_class` as one field with one meaning.** `fathom.agent.authority` is the agent credential class (03 §8.3); `authority_classes` and `Proposal.authority_class` are organizational roles (03 §7.2.1). *(§2.5)*
12. **Do not add an `AuthorityClass` beyond document 03 §7.2.1's enumerated set (six, as of amendment 03-1), and do not compare classes by rank.** Finer-grained roles *within* a class are permitted; removing the minimum, or inventing a hierarchy, is not. *(03 §7.2.1; §2.4)*

### 13.3 The Domino Endpoint path

13. **Do not call a Domino Endpoint from a sub-application directly.** It distributes a static, non-rotating, non-expiring credential across nine services and multiplies cross-namespace edges into `domino-compute`. Route through the `gateway` proxy. *(02 §4.3, 03 §8.3; §5.2)*
14. **Do not write the audit binding only after the call returns.** A crash mid-call then leaves an invocation attributable to nobody, permanently, because Domino keeps no per-caller trail. Pre-write the intent. *(**D12**; 02 §4.3; §5.5)*
15. **Do not trust a caller's assertion of who its end user is.** The proxy validates the actual delegated token, including `aud`. *(§5.4)*
16. **Do not record a timed-out Endpoint call as not executed.** A timed-out Domino request is not cancelled. *(02 §4.3; §5.6)*
17. **Do not assume federation gives Endpoint calls caller identity.** It gives Domino a user session; the Endpoint credential still carries nothing. *(02 §4.3; §2.2)*

### 13.4 Policy and classification

18. **Do not write authorization logic in a service.** No `if role == …` in Python, no per-service policy file, no local authority table. Policy is Rego in `platform/auth/policy/`, and the decision point is the in-pod sidecar. *(03 §15 obligation 7; §6.1)*
19. **Do not hand-type the authority matrix.** It is generated from the canonical enum and CI fails on drift, so document 03 §7.2.1's table exists once. *(§6.2)*
20. **Do not post-filter for classification.** The decision returns a predicate to push into the query; removing rows afterward leaks their existence through counts, latency, and cursors. *(**D13**; 03 §7.3, 09 §9.4 item 22; §6.5)*
21. **Do not fail open.** An unreachable OPA sidecar, an unverifiable bundle, a stale bundle, an unreachable introspection on a side-effecting operation, and excessive clock dispersion are each a refusal. *(§3.5, §6.2, §6.7, T-15–T-17, T-19)*
22. **Do not let the event-fed deny-list authorize anything.** It may only deny faster. *(§4.6)*
23. **Do not let a wall clock arbitrate anything except JWT `exp`**, and make that one comparison observable through `sync_quality`. *(**D29**; 03 §5.4, 09 §9.2 item 7; §6.7)*

### 13.5 Accreditation and data

24. **Do not assert an impact level, an NSS determination, or a control baseline.** IL4-versus-IL5 requires a written AO determination. *(08 §3.3, §9)*
25. **Do not cite the superseded Cloud Computing SRG, the 2014 DoDI 8510.01, or the Zero Trust Reference Architecture as DDIL authority.** *(08 §3.2, §7)*
26. **Do not claim STIG inheritance or an ATO from a hardened base image.** *(08 §3.6)*
27. **Do not invent DoD PKI certificate-profile detail, CAC field mappings, or revocation posture.** Mark them **[VERIFY]** and route them to the program. *(08 §8; §7.4)*
28. **Do not invent Navy billet, TYCOM, or qualification code values.** They are CAC-gated or unpublished; they come from documents 07 and 12. *(09 §9.5 item 32; §2.3)*
29. **Do not accept `FOUO` or `U//FOUO` as a dissemination control.** Retired markings fail policy. *(03 §7.3; §6.5)*
30. **Do not reach a public-internet service at runtime**, including for JWKS, OCSP, CRL, or a policy bundle. *(01 principle 5, 09 §9.5 item 26)*

---

## 14. Amendments required to binding documents

Each is a **defect or gap in the cited document**, not a decision of this one. Items A-1 through A-3 block clean implementation; A-4 and A-5 are required before merge of the code they govern.

| # | Document | Issue | Required change | Status |
|---|---|---|---|---|
| **A-1** | **10 §7.2 / `packages/canonical-schemas`** | `Proposal.authority_class` is typed `NonEmptyStr` with **OQ-13** recorded as *"the most consequential gap in the package"* because the vocabulary was undefined. Document 03 §7.2.1 now defines it | Add `fathom_schemas/authority.py` with the `AuthorityClass` enum (§2.4); retype the field; **close OQ-13** and remove it from document 10 §11's blocker list | **Applied.** `10-shared-packages.md` §4.6b adds the module, §4.7 retypes the field, and OQ-13 is closed |
| **A-2** | **09 §5.5** | Says the principal carries *"an `authority_class` of `delegated` or `accountable-autonomous`"* — collides by name with 03 §7.2.1's vocabulary, and hyphenates a value that must be `snake_case` on the wire | Rename to `fathom.agent.authority`; wire value `accountable_autonomous` | **Applied in §2.5.** Document 09 needs the edit |
| **A-3** | **03 §7.2 / §7.2.1** | `Proposal.authority_class` is **singular**, but three §7.2.1 cells accept **two** classes (*"`maintainer` or `planner`"*) and one is two-stage (*"then Registry confirmation"*). A single value cannot express an alternative set | Either rename to `authority_class_any_of[]`, or state explicitly that the field records the cell's first value and that the policy is authoritative | **Interim implemented** in §6.4 (`authority_class_field_stale` validates membership in `any_of`). Flagged |
| **A-4** | **09 §4.4.2** | The sanctioned-edge table has no `<sub-application> → gateway` edge. The Domino Endpoint proxy (§5) requires it, for one operation | Add the edge, scoped to `POST /api/v1/gateway/domino/endpoint-invocations`, with the §5.2 justification. **ADR required** | Not applied. **Blocks the proxy's NetworkPolicy** |
| **A-5** | **03 §5.4 / §6** | The `scope` enumeration has no `principal` member, so `auth`'s events must use `fleet`. And 03 §6's producer-owned catalog has no `auth` rows, while obligation 2 requires `auth` to emit events | Add a `principal` scope, or ratify `fleet`; add the two §9 topics to the 03 §6 catalog with their declared consumers | Interim `fleet` implemented (§9). Flagged |
| **A-6** | **04 §11** | Two `### Identity & Authorization` headings with different content (document 09 §11 item 6 already flags this as finding **C33**'s neighbourhood). Also assigns *"token exchange for delegated authority"* to the gateway without splitting caller from authority | Merge the headings; record the §4.1 split | Not applied. Flagged; document 09 §11 item 6 already carries it |
| **A-7** | **09 §5.6** | The five mandatory readiness checks and the fixed metric list predate this service | Add the `policy_bundle` readiness check and the four `fathom_authz_*` metrics (§6.2) | **Specified in §6.2.** Document 09 needs the edit |
| **A-8** | **03 §4.1 / 09 §5.1** | Two operation annotations are specified; the audience-scoping mechanism of §5.3 needs a third declared surface | Add `x-domino-endpoint` as an optional annotation, with the CI rule that it may not appear on a `state-changing` operation | **Specified in §5.3.** Both documents need the edit |

---

## 15. Open questions

Resolved once, centrally. A local resolution is recorded in the service README and is not treated as settled [09 §8.7].

| # | Question | Impact if unresolved | Interim position |
|---|---|---|---|
| **OQ-31-1** | Does the pinned Keycloak version support standard token exchange with `actor_token` and emit the `act` claim? | Decides whether §4.2 uses the realm's exchange or the signed-assertion fallback | Fallback is named and claim-shape-identical (§4.2). No service's validation code changes either way |
| **OQ-31-2** | **Sender-constrained tokens** — DPoP (RFC 9449) or mTLS binding (RFC 8705) via `cnf`? | A bearer token exfiltrated from an agent runtime is replayable within its TTL | **Not adopted.** Domino's agent runtime cannot be assumed to present a client certificate or a DPoP proof [01 §8.7, 02 §4.1–§4.2]. Compensating controls: short TTL, `aud` restriction, `jti` in audit, introspection on side-effecting operations. **Revisit when 01 §8.7's M2M dependency resolves** |
| **OQ-31-3** | Does 03 §7.2.1's *"[m]inimum authority"* imply escalation — may a `fleet_authority` adjudicate an item-scoped `anomaly_tag`? | Changes T-7's expected results for 20 of 24 cells | **No implicit hierarchy** (§2.4). The safe reading is implemented and tested |
| **OQ-31-4** | Agent-token TTLs, `introspection_max_age`, bundle max age, and the guard band | Too short churns exchanges; too long widens the lapse window | Defaults in §3.2/§4.6/§6.2 as configuration, **not** as capacity figures [09 §9.5 item 31]. Tune against document 06 §7's agent-proposal volume once measured |
| **OQ-31-5** | Authoritative personnel source for clearance, caveats, compartments, unit, billet, qualification, and its provisioning cadence | The attribute model is specified; its *feed* is not | Synthetic seed for the demonstration [13]. Raise for program assignment |
| **OQ-31-6** | Edge authority caching interval and the divergence budget for a disconnected hull's cached bundle and token set | A dark hull with an expired bundle is either unusable or unsafely permissive | Set with document 11's divergence budgets [03 §11]. **Do not invent an interval.** The Overlays' hedge (centralized ICAM governs the cached PDP) bounds the design space [08 §3.6] |
| **OQ-31-7** | Does the accountable owner of an autonomous grant require re-attestation on a cadence? | An owner who transfers billet leaves grants attributed to a person no longer in the role | Grants are revoked when the owner is disabled (§4.6). A periodic re-attestation is likely an accreditation expectation; raise with the AO |

---

## 16. Definition of Done

Document 09 §8's shared checklist applies **in full and unmodified** — it is not reproduced here, and nothing in it is removed. Copy it into `platform/auth/README.md` and tick it there. The items below are **additional** and specific to this service.

### 16.1 Identity and tokens

- [ ] Keycloak deployed from `realm-fathom.json`; **the running realm's export equals the committed file** (T-20). No console configuration in any environment. *(§2.1)*
- [ ] Asymmetric signing only; `alg: none` and symmetric algorithms rejected before claim parsing. *(§2.1, T-14)*
- [ ] Domino's Keycloak brokers **to** the `fathom` realm; identity parity asserted (T-4). *(§2.2)*
- [ ] Every §2.3 attribute present, closed-vocabulary-validated at the realm **and** at token parse. Retired markings rejected. *(§2.3)*
- [ ] `AuthorityClass` exists in `packages/canonical-schemas`; `Proposal.authority_class` retyped; **document 10's OQ-13 closed**. *(§2.4, A-1)*
- [ ] `fathom.agent.authority` is the agent-class claim; **no field named `authority_class` carries an agent class anywhere in the codebase**. *(§2.5, A-2)*
- [ ] The three token shapes match §3.1–§3.3 exactly, asserted against committed golden token vectors in the conformance suite.
- [ ] A delegated token's `fathom.identity` block is **byte-identical** to the originating user token's (T-5). *(§3.2)*
- [ ] No refresh token, and no `offline_access`, for any agent client. *(§3.2, §3.3)*
- [ ] `accountable_autonomous` issuance refuses without `accountable_owner` and a non-empty `declared_scope`; `fleet: true` requires a second distinct `fleet_authority` signature (T-13). *(§3.3)*
- [ ] An autonomous token's `authority_classes` is empty and its clearance is the floor of owner and ceiling (T-12). *(§3.3)*
- [ ] `sfx:` scope matching is **positive** and enforced in the receiver; both layers tested independently (T-1a, T-1b). *(§3.4)*
- [ ] §3.5's ten validation steps implemented **once** in `packages/py-common` and reimplemented in no service.

### 16.2 Exchange and lapse

- [ ] Exchange carries `subject_token` **and** `actor_token`; a returned token without `act` is discarded. *(§4.2)*
- [ ] The manifest eligibility gate re-runs at issuance against the committed `openapi.json`. *(§4.1 step 4c)*
- [ ] `aud` is derived from the manifest, never client-supplied, and includes `gateway` only when an `x-domino-endpoint` operation is selected (T-3e). *(§4.1, §5.3)*
- [ ] Agent-run records per §4.3, with the `CHECK` that exactly one of `delegation_id`/`grant_id` is set.
- [ ] Lapse detection on a **monotonic** deadline; all three triggers implemented; termination sequence in the specified order (T-2a). *(§4.4)*
- [ ] A checkpoint contains **no token**, asserted by scanning the serialized object (T-2b). *(§4.4)*
- [ ] A workload-only subject token cannot obtain a delegation (T-2b). *(§4.4)*
- [ ] Resume creates a new `run_id`, requires the original human, and refuses on expiry, hash mismatch, or changed pins (T-2c). *(§4.4)*
- [ ] Introspection is authoritative on `proposal-only` and `state-changing`; the event-fed deny-list can only deny; fail closed when introspection is unreachable (T-19). *(§4.6)*
- [ ] Audit records at 1 ms granularity with `sync_quality` attached. *(§4.6, 08 §3.3)*

### 16.3 The Domino Endpoint proxy

- [ ] The proxy exists **only** on `gateway`; no sub-application holds an Endpoint credential (grep-asserted in CI). *(§5.2, §5.7)*
- [ ] `x-domino-endpoint` declared on every operation requiring inference; CI fails on an undeclared logical id and on `state-changing` + `x-domino-endpoint`. *(§5.3, A-8)*
- [ ] Both credentials verified; no body-asserted caller identity accepted. *(§5.4)*
- [ ] **Two-phase audit binding**, intent row committed with its outbox row **before** the call (T-3a, T-3b). *(§5.5)*
- [ ] 10 MB rejected pre-call; deadline below the recommended 60 s maximum; `timeout_result_unknown` never reported as non-execution (T-3c). *(§5.6)*
- [ ] The static credential appears in no record, problem detail, or log line (T-3d). *(§5.7)*
- [ ] Rotation runbook committed alongside the `gateway` chart. *(§5.7)*

### 16.4 Policy

- [ ] OPA sidecar in **every** service pod; `authz.opa.enabled` never `false`. *(§6.1, §11)*
- [ ] `authority_matrix.json` **generated**, CI drift-checked, and covering every 03 §7.2.1 cell (T-7). *(§6.2, §6.4)*
- [ ] Bundle signed; signature verification mandatory; `policy_bundle` readiness check wired and bounded (T-16). *(§6.2, A-7)*
- [ ] The §6.3 input document built once in `packages/py-common`.
- [ ] No implicit authority hierarchy; `any_of` sets honoured; `not_applicable` cells deny; `authority_class` re-validated at adjudication (T-7, T-9). *(§6.4)*
- [ ] Dual control mandatory at class and fleet scope and for external-legal-effect kinds; second adjudicator distinct; the second signature's authority is checked against the matrix for **every** kind requiring dual control — `interval_change`, `redesign_case`, `purge`, `rewrap`, and any future kind — never hardcoded to one (T-8). *(§6.4)*
- [ ] No agent adjudicates, of either class (T-6). *(§6.4)*
- [ ] Classification checks complete, and **the predicate obligation is asserted on the emitted query, not the result set** (T-10, T-11). *(§6.5)*
- [ ] Declared-scope containment enforced (T-12). *(§6.6)*
- [ ] JWT `exp` is the only wall-clock comparison; dispersion refusal implemented (T-15). *(§6.7)*
- [ ] Adjudication decisions never cached. *(§6.8)*
- [ ] Fail-closed on unreachable OPA (T-17). *(§3.5)*

### 16.5 Surface, accreditation, and governance

- [ ] Every §8 operation present with its annotations; **no operation on `auth` is `x-agent-eligible`**.
- [ ] `POST /authority-checks` returns `advisory: true` and is documented as never the enforcement point. *(§8)*
- [ ] `GET /delegations?changed_since=` serves the rebuild path; the bus is not a rebuild source. *(§9, D5)*
- [ ] Two topics published through the outbox; no credential in any payload; compaction key is the aggregate key. *(§9)*
- [ ] T-1 through T-20 present and green, in `packages/contracts/conformance/auth/` where shared. *(§10)*
- [ ] `principal_factory` provided from `packages/py-common.testing`; no service mints its own principal shape. *(§10)*
- [ ] One owned database cluster, two schemas, **justified in the README** per obligation 13. *(§2.1)*
- [ ] §12's accreditation table reproduced in the README, with the **NSS determination named as an open program action** and no impact level asserted. *(§12, 08 §3.3)*
- [ ] Every **[VERIFY]** item in §7.4 filed as a tracked program action with an owner.
- [ ] Amendments **A-1 … A-8** each filed against their document with an owner. **A-4 additionally requires a merged ADR before the proxy's NetworkPolicy peer is added.** *(§14)*
- [ ] Open questions **OQ-31-1 … OQ-31-7** recorded in the README as local resolutions where the service had to proceed. *(§15, 09 §8.7)*
