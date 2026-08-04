# Build Framework 09 — Monorepo, Stack, and Engineering Conventions

| | |
|---|---|
| **Status** | Draft rev 1. Binding on every subsequent build-framework document and every Phase 3 implementation |
| **Scope** | The repository layout, technology pins, per-service scaffold, code-level API rules, CI/CD skeleton, coding standards, and the shared Definition of Done |
| **Derived from** | [01 — System Architecture](../architecture/01-system-architecture.md) §11, §14 · [02 — Domino Platform Assessment](../architecture/02-domino-platform-assessment.md) §4 · [03 — Integration Contracts](../architecture/03-integration-contracts.md) §3, §4, §5, §15 · [04 — Sub-Application Architectures](../architecture/04-subapplication-architectures.md) §1, §11, §12 · [05 — Review Findings](../architecture/05-architecture-review-findings.md) |
| **Precedence** | Document 03 prevails over this document on any contract surface. This document prevails over the eight sibling build-framework documents on layout, stack, and conventions |
| **Verification note** | Library and tool selections were verified against documents 01/03 as of a **January 2026 knowledge cutoff**. Where a version is stated as a floor (`>=`), **pin to the current stable minor release at implementation time** and record the pin in the lockfile. No exact version in this document is to be treated as a settled fact |
| **Classification** | Internal |

---

## 1. Purpose and scope

### 1.1 What this document governs

Nine domain sub-applications and eight platform services are to be implemented independently, largely by separate agents working from separate documents. Every decision that must be *identical* across all seventeen services is made here, once:

- The monorepo directory layout and the exact path of every artifact (§3).
- The technology stack and the specific library chosen for each concern (§2).
- The per-service skeleton — `src/` layering, `tests/` layering, Dockerfile, Helm chart, config loading, logging (§4).
- The FastAPI-level implementation of document 03 §4's REST conventions, including which pieces are shared-library components rather than per-service code (§5).
- The CI/CD pipeline and the gates every pull request must pass (§6).
- Naming, formatting, linting, typing, commit, and branch conventions (§7).
- **The Definition of Done every service must satisfy before being called complete (§8).**
- The prohibitions that carry a cited review finding behind them (§9).

### 1.2 What this document does NOT govern

| Out of scope here | Governed by |
|---|---|
| The contents and public API of `packages/py-common`, `packages/ts-common`, `packages/canonical-schemas`, `packages/contracts` | The **shared-packages** build-framework document |
| Outbox and inbox implementation, the relay, event publication and consumption APIs, conflict-policy enforcement, divergence budgets | [`docs/build/11-outbox-sync-library.md`](11-outbox-sync-library.md) |
| Taxonomy structure, versioning, crosswalks, enumeration serving, the Reference Data service's own design | The **Reference Data & taxonomy** build-framework document |
| Synthetic data generation, fixture corpora, the reference dataset shipped with each conformance suite | The **synthetic-data** build-framework document |
| Any Navy schema detail — 3-M code sets, CDMD-OA fields, COSAL structure, NIIN/NSN formats, IUID | [07 — Navy Data Systems](../architecture/07-navy-data-systems.md), consumed by the relevant sub-application document |
| Per-sub-application aggregates, operations, events, read models | Document 04, then each sub-application's Phase 3 document |
| **The operator UI's visual design, component library, styling system, and user flows** | **Deferred to a later wave pending user input on look-and-feel.** §2.6 pins *only* the build toolchain |
| Capacity figures, rates, volumes, latency budgets | [06 — Demonstration Decisions](../architecture/06-demo-decisions-and-assumptions.md) §7. Do not invent numbers; cite that table |

> **Sibling-document filenames.** Only `docs/build/11-outbox-sync-library.md` is fixed by assignment. The other three sibling documents are referenced descriptively above because their filenames are assigned by the build-framework index, not by this document. Replace the descriptive references with paths once the index is published; do not guess numbers.

### 1.3 How to read a decision in this document

Three markers are used, and they are load-bearing:

- **[03 §n]** or **[01 §n]** — the decision is dictated by an architecture document. Not negotiable at implementation time.
- **[ESTABLISHED HERE]** — the architecture documents do not specify this. This document makes the call so that seventeen services do not make seventeen different calls. The reasoning is stated. A change is cheap *if made once, here*; it is expensive after nine implementations disagree.
- **[OPEN]** — genuinely undecided, listed in §10, and blocking or near-blocking. Do not resolve one of these locally inside a service.

---

## 2. Technology stack

### 2.1 Pins fixed by document 01 §14

These are not open. They are reproduced so that no service re-litigates them.

| Layer | Selection | Source |
|---|---|---|
| Domain and platform services | **Python 3.12** with **FastAPI** | 01 §14 |
| Operator interface | **React + TypeScript, Vite-built**, served from the Sustainment Plane | 01 §14, 01 §3 correction 1 |
| Practitioner interfaces | Domino Apps; Extensions only where the deployment supports them | 01 §9, 01 §14 |
| Relational storage | **PostgreSQL via CloudNativePG**, database-per-service | 01 §11, 01 §14 |
| Time series | **TimescaleDB**, a distinct operator-managed cluster owned by Condition & Telemetry | 01 §14 (and finding D33) |
| Vector | **pgvector**, on Knowledge & Retrieval's own cluster | 01 §14 |
| Object storage | S3 API; MinIO in the demonstration | 01 §14 |
| Events | **Kafka API via Redpanda** | 01 §14, 03 §5.1 |
| Identity | OIDC via Keycloak federated with Domino; OPA or Cedar for ABAC | 01 §14 |
| Contracts | **OpenAPI 3.1** per service, **AsyncAPI** for events, MCP-style manifests generated from OpenAPI | 01 §14, 03 §4, 03 §8.2 |
| Orchestration | **Kubernetes, Helm, Argo CD** | 01 §11, 01 §14 |

### 2.2 Python service libraries

Version numbers below are **floors, not pins**. Pin to the current stable minor release at implementation time; verified against documents 01/03 as of Jan 2026 knowledge cutoff.

| Concern | Selection | Floor | Why this one, against what document 03 requires |
|---|---|---|---|
| Web framework | **FastAPI** | `>=0.115` | Fixed by 01 §14. Chosen floor is the first line that emits **OpenAPI 3.1.0** rather than 3.0.x, which 03 §4 requires; a 3.0.x emitter cannot express the JSON Schema 2020-12 that `packages/canonical-schemas` produces. |
| Data validation / wire schemas | **Pydantic v2** | `>=2.9` | 03 §5.5 requires payload schemas published as versioned Python **and** TypeScript libraries; Pydantic v2 exports JSON Schema 2020-12, which is the single source both the OpenAPI document and the TypeScript generator read. v1 is prohibited. |
| Settings | **pydantic-settings** | `>=2.5` | One typed `Settings` class per service, populated from environment only (§4.5). Keeps 01 §11's External-Secrets model workable: secrets arrive as env vars, never as files in the chart. |
| ASGI server | **uvicorn** with `uvloop` + `httptools` extras | `>=0.32` | **One worker per container, replica-scaled by HPA/KEDA** [01 §11]. No gunicorn: a process manager inside the pod duplicates what Kubernetes already does and obscures per-replica readiness, which 03 §5.2 requires to reflect read-model lag. |
| ORM / data access | **SQLAlchemy 2.x async** (`AsyncEngine`/`AsyncSession`) + **asyncpg** | `>=2.0`, `asyncpg>=0.30` | Three requirements decide this. (a) 03 §5.2's transactional outbox needs a state change and an outbox row in **one** transaction — an explicit session/transaction boundary, which SQLAlchemy 2.0 gives and an active-record ORM does not. (b) Document 04 §2's **bitemporal** configuration tables need `TSTZRANGE` columns and `EXCLUDE` constraints; SQLAlchemy 2.0 Core lets a repository drop to literal SQL for exactly those without abandoning typed models. (c) Async throughout, because outbox relays and inbox consumers are I/O-bound and colocated with the request path. Rejected: Tortoise/SQLModel (thin over the same, adds a layer), Django ORM (not async-first, no `EXCLUDE` support), raw asyncpg only (no migration story, no typed mapping). |
| Migrations | **Alembic**, async template, one history per service | `>=1.14` | 01 §11: migrations are **per-service, executed as pre-upgrade Helm hooks**; "no shared migration path exists, by construction." Alembic's per-service `versions/` directory is exactly that. TimescaleDB hypertable DDL and pgvector index DDL are `op.execute()` raw SQL inside ordinary revisions. |
| Kafka client | **confluent-kafka-python** (librdkafka) | `>=2.6` | Redpanda's tested client family, and the only one shipping a Schema Registry client compatible with 03 §5.5's "producer cannot publish an event whose payload fails registry validation." Ships as a manylinux wheel, so it vendors into a private index without a compiler at build time [01 §12]. It is synchronous; **bridging it to asyncio is `docs/build/11-outbox-sync-library.md`'s responsibility, not each service's.** |
| Schema registry mode | **JSON Schema** (Redpanda Schema Registry, Confluent-compatible API) | — | **[ESTABLISHED HERE]** 03 §5.5 mandates a registry enforcing compatibility on publish but does not name a serialization. JSON Schema is chosen because `packages/canonical-schemas` is Pydantic v2, whose native export *is* JSON Schema — Avro or Protobuf would require a second, hand-maintained schema definition per payload and a divergence check between them. Cost: larger payloads. Accepted, because 03 §6 events are batch-level and reference-carrying, not sample-level. |
| HTTP client | **httpx** async, via a shared factory in `packages/py-common` | `>=0.27` | 03 §4 requires `X-Correlation-Id` propagation "to every log line, event, and **downstream call**", plus workload identity on service-to-service calls. Those are properties of a *configured client*, so the factory is shared and a bare `httpx.AsyncClient()` is a lint failure. **Note the constraint this serves:** 03 principle 2 forbids synchronous cross-sub-application calls on compute paths, so in the nine domain services the only sanctioned outbound HTTP is to `auth`, `audit`, and `reference-data`. The gateway is the exception. |
| Structured logging | **structlog** with JSON renderer, correlation ID in a `contextvars` binding | `>=24.4` | 03 §15 obligation 15: `X-Correlation-Id` on **every** log line. `contextvars` is the only mechanism that survives `await` boundaries without threading the ID through every function signature. |
| Metrics | **prometheus-client**, `/metrics` text exposition | `>=0.21` | 03 §4 requires `/metrics`; 03 §5.2 requires read-model lag on `/metrics`. |
| Tracing | **OpenTelemetry SDK**, OTLP exporter, **disabled by default** | `>=1.28` | **[ESTABLISHED HERE]** No collector is in the 01 §11 inventory, so tracing is instrumented-but-off: the SDK is wired and the exporter is config-gated. `X-Correlation-Id` remains the primary correlation mechanism because 03 §4 makes it contractual and OTLP is not. |
| Test framework | **pytest** + **pytest-asyncio** (`asyncio_mode = "strict"`) | `pytest>=8.3` | Fixed by convention here; no alternative is discussed in the architecture. Strict mode so that a forgotten `await` fails rather than silently passing. |
| Integration test infra | **testcontainers-python** (PostgreSQL, Redpanda modules) | `>=4.8` | Every service owns a real database and a real broker; mocks cannot exercise the outbox's single-transaction property or `EXCLUDE`-constraint behaviour. **Air-gap constraint:** container images used by tests must be mirrored into the private registry and referenced by digest — the same rule as runtime images [01 §12]. |
| API property testing | **schemathesis** | `>=3.38` | Drives the committed `openapi.json` against the running service, which is the cheapest available check on 03 §15 obligation 1 (spec generated from code and *true*). |
| HTTP mocking | **respx** | `>=0.21` | Pairs with httpx; used only for `auth`/`audit`/`reference-data` edges. |
| Lint + format | **ruff** (`ruff check` and `ruff format`) | `>=0.8` | One tool for lint, import sorting, and formatting. **black, isort, and flake8 are prohibited** — running two formatters produces a reformat war across seventeen services. |
| Type checking | **mypy**, `strict = true` | `>=1.13` | §7.4 states the strictness contract and its two narrow escapes. |
| Dependency management | **uv** with `pyproject.toml` + committed `uv.lock` per service | `>=0.5` | **[ESTABLISHED HERE]** No tool is named in the architecture. `uv` is chosen for two reasons that matter to this program specifically: `uv sync --locked` fails rather than resolving, which is what "all dependencies baked at build time" [01 §12] requires of a Dockerfile; and the lockfile carries hashes, which is the vendoring manifest for a private index. Alternative if `uv` proves unsuitable: Poetry with `poetry install --sync --no-root` and `poetry.lock`. Whichever is used, **it must be the same one in all seventeen services**, and switching is a change to this document. |
| Pre-commit | **pre-commit** running ruff, ruff-format, and a secrets scan | `>=4.0` | Identical checks to CI job 1, so the fast feedback loop and the gate agree. |

### 2.3 Data-layer specifics

| Concern | Rule |
|---|---|
| Database per service | **Exactly one logical database per service** [03 §15 obligation 13]. Provisioned as a CloudNativePG `Cluster` in `fathom-data`, named `fathom-<slug>-pg`. A service holds credentials for its own cluster and no other; NetworkPolicy enforces this rather than trusting it [01 §11]. |
| TimescaleDB | Condition & Telemetry only. A **separate operator-managed cluster**, `fathom-telemetry-ts`, not a flag on a shared cluster — Timescale is a Postgres extension requiring its own image [01 §14, finding D33]. Where a service needs both relational and time-series storage, they are separate schemas of one owned cluster or are separately justified [03 §15 obligation 13]. |
| pgvector | Knowledge & Retrieval only, on its own cluster [01 §14]. |
| Connection pooling | SQLAlchemy `AsyncEngine` pool sized from config; **no PgBouncer in the demonstration** — **[ESTABLISHED HERE]**, because prepared-statement handling in transaction-pooling mode interacts badly with asyncpg and nothing in document 06 §7 implies the connection counts that would justify it. |
| Timestamps | `TIMESTAMPTZ` always. `TIMESTAMP` without zone is a lint failure. RFC 3339 with explicit offset on the wire, UTC [03 §4]. |
| Identifier columns | Exactly the names in 03 §3.3: `asset_id`, `system_id`, `position_id`, `installed_item_id`, `niin`. No local surrogate is ever exposed [03 principle 4]. |

### 2.4 Kubernetes and delivery

| Concern | Selection | Source |
|---|---|---|
| Chart tooling | **Helm 3**, one chart per service, umbrella chart per plane | 01 §11 |
| Chart testing | `helm lint`, `helm template \| kubeconform`, **helm-unittest** for template assertions | **[ESTABLISHED HERE]** — 01 §11 makes boundary enforcement "an invariant testable in continuous integration", which requires a template-level assertion tool |
| GitOps | **Argo CD**, declarative from `deploy/argocd/`, app-of-apps | 01 §11 |
| Secrets | **External Secrets Operator**. No secrets in charts, no secrets in `values.yaml` | 01 §11 |
| Namespaces | `fathom-sustainment`, `fathom-data`. Never Domino's `domino-platform`, `domino-compute`, `domino-system` | 01 §11 |
| Network plugin | NetworkPolicy-capable (Calico or equivalent) — a cluster prerequisite | 01 §11, 02 §4.6 |
| Scaling | HPA on request rate for gateway and read-heavy services; **KEDA on consumer lag** for event workers | 01 §11 |
| Base images | Builder `python:3.12-slim-bookworm`; runtime the same slim image, **pinned by digest** | **[ESTABLISHED HERE]** — see §4.3 for why not distroless |
| Image scanning / SBOM | **Trivy** (or Grype) scan and **Syft** SBOM per image, both artifacts retained | **[ESTABLISHED HERE]** — an air-gapped accreditation needs a per-image bill of materials, and it is nearly free at build time |

### 2.5 Contract tooling

| Artifact | Producer | Committed at |
|---|---|---|
| OpenAPI 3.1 document | Generated from FastAPI at build time by `tools/gen_openapi.py` | `services/<slug>/openapi.json` |
| AsyncAPI document | Generated from the service's declared event catalog + `packages/canonical-schemas` | `services/<slug>/asyncapi.yaml` |
| MCP-style tool manifests | Generated from the pinned OpenAPI document [03 §8.2] | `packages/agent-tooling/manifests/<slug>/<name>.v<major>.yaml` |
| TypeScript wire types | `openapi-typescript` over each committed `openapi.json` | `packages/ts-common/src/generated/` |

**Both generated documents are committed and CI fails on drift.** 03 §4 requires the specification be "validated in CI against the committed specification"; a regenerate-and-diff check is the mechanism.

### 2.6 Operator UI toolchain — framework only

Document 01 §14 fixes React + TypeScript + Vite. This section pins the toolchain and **nothing else**.

| Concern | Selection | Floor |
|---|---|---|
| Framework | React | `>=18.3` |
| Language | TypeScript, `strict: true`, `noUncheckedIndexedAccess: true` | `>=5.6` |
| Build | Vite | `>=6.0` |
| Package manager / workspace | **pnpm** workspaces spanning `apps/*` and `packages/ts-common` | `pnpm>=9` |
| Tests | **Vitest** + Testing Library | `vitest>=2.1` |
| Lint / format | **ESLint** (flat config) + **Prettier** | — |
| API types | **openapi-typescript** + **openapi-fetch**, generated from committed `openapi.json` | — |
| Router / state / data fetching | **[OPEN]** — see §10 | — |

Three constraints that *are* in scope:

1. **The UI never hand-writes a wire type.** All request and response types come from generated code. A hand-written interface mirroring an API response is a review rejection.
2. **`apps/web` bakes its base path at build time.** It is served from program ingress on the Sustainment Plane, so document 02 §4.1's runtime-base-path constraint does **not** apply to it. `apps/practitioner` is Domino-hosted and **must** read its base path at runtime from `DOMINO_RUN_HOST_PATH` [02 §4.1] — the two apps therefore differ in Vite `base` configuration and this is deliberate.
3. **No look-and-feel decisions.** No component library, design system, theme, CSS framework, icon set, or layout is selected here. Any such choice made inside a service or app PR before the look-and-feel wave is out of scope and should be rejected.

---

## 3. Monorepo layout

### 3.1 The reconciled tree

Reconciled against document 01 §11's layout, document 03's package paths, and the canonical slugs in 03 §3.1. **Two corrections to 01 §11 are applied and flagged in §11.**

```
/
├── apps/
│   ├── web/                          # React SPA, Sustainment Plane. Base path baked at build. [09, then the look-and-feel wave]
│   └── practitioner/                 # Domino Apps (and Extensions where supported). Runtime base path. [09 + 02 §4.1]
│
├── services/                         # The nine domain sub-applications. Directory name == canonical slug (03 §3.1)
│   ├── registry/                     # Asset & Configuration Registry
│   ├── telemetry/                    # Condition & Telemetry
│   ├── pdm/                          # Predictive Maintenance
│   ├── fleet-status/                 # Fleet Status & Readiness
│   ├── maintenance/                  # Maintenance Execution & Scheduling
│   ├── supply/                       # Supply Chain & Inventory
│   ├── pma/                          # Post-Mission Analysis
│   ├── failure-intel/                # Failure Intelligence
│   └── design-advisory/              # System Test & Design Advisory
│
├── platform/                         # The eight platform services (01 §5, 04 §11). Directory name == canonical slug
│   ├── gateway/                      # API Gateway / BFF; unified adjudication queue
│   ├── auth/                         # OIDC, ABAC
│   ├── reference-data/               # Enumerations, code sets, sole taxonomy owner [Reference Data doc]
│   ├── knowledge-retrieval/          # Chunking, embedding, configuration-aware retrieval; pgvector
│   ├── audit/                        # Immutable lineage and provenance
│   ├── notification/                 # Routing and escalation
│   ├── tool-server/                  # Hosts MCP-style manifests (03 §8.5)
│   └── sync/                         # Edge reconciliation coordinator service [11-outbox-sync-library.md]
│
├── agents/                           # Versioned agent artifacts: prompt, manifest pin, API version pin,
│   ├── copilot/                      #   evaluation set, deployment spec (01 §11). Demo builds three
│   ├── pma-prescreener/              #   (06 §7): copilot, pma-prescreener, redesign-case-builder
│   ├── diagnostic/
│   ├── work-package-planner/
│   ├── supply-expediter/
│   ├── redesign-case-builder/
│   └── readiness-narrative/
│
├── models/                           # Model source, training entrypoints, evaluation. Domino-executed
│   ├── tier0-historical/
│   ├── tier1-survival/
│   ├── tier2-degradation/
│   ├── tier3-hybrid/
│   └── causal/
│
├── packages/                         # Shared, versioned libraries. Path shapes are fixed by 03
│   ├── canonical-schemas/            # Shared kernel + shared payload schemas (01 §6, 03 §5.5, 03 §7) [shared-packages doc]
│   ├── contracts/
│   │   ├── openapi/<slug>/           # Published specs, one directory per slug
│   │   ├── asyncapi/<slug>/
│   │   └── conformance/<slug>/       # Executable conformance suites — path fixed by 03 §10 [shared-packages doc]
│   ├── agent-tooling/
│   │   ├── manifests/<slug>/         # Path fixed by 03 §8.2
│   │   └── generator/                # OpenAPI → MCP-style descriptor generation; fails, never warns
│   ├── py-common/                    # Shared FastAPI middleware, problem details, idempotency, ETag,
│   │                                 #   logging, health, OpenAPI annotations (§5) [shared-packages doc]
│   ├── py-sync/                      # Outbox/inbox library consumed by every service [11-outbox-sync-library.md]
│   └── ts-common/                    # Generated wire types and shared TS utilities [shared-packages doc]
│
├── data/
│   └── synthetic/                    # Generator + generated fixtures; reference datasets for conformance
│                                     #   [synthetic-data doc]
├── deploy/
│   ├── helm/                         # Umbrella charts per plane; shared chart library (_fathom-common)
│   ├── argocd/                       # Argo CD Applications, app-of-apps, project definitions
│   └── terraform/                    # Cluster-adjacent infrastructure (registry, object store, DNS)
│
├── tools/                            # Repository-level checks and generators. Invoked by CI and by make
│   └── check_event_catalog.py        # EXISTS. Reconciles 03 §6 catalog against 04 declarations, both directions
│
├── docs/
│   ├── architecture/                 # Phase 1–2 architecture of record (01–08)
│   ├── build/                        # Build framework, this document included (09–…)
│   └── adr/                          # Architecture Decision Records for post-Phase-3 changes
│
├── Makefile                          # The single entrypoint. CI calls make targets, never inline scripts
├── pyproject.toml                    # Workspace root: shared ruff/mypy/pytest configuration only
├── pnpm-workspace.yaml
└── .github/workflows/                # [OPEN] CI provider — see §6.1 and §10
```

### 3.2 Per-directory governance

| Directory | Contains | Governed by |
|---|---|---|
| `apps/web` | Operator SPA. Toolchain only until the look-and-feel wave | This document §2.6, then the look-and-feel document |
| `apps/practitioner` | Domino-hosted practitioner surfaces | This document §2.6 + 02 §4.1 constraints |
| `services/<slug>` | The nine domain sub-applications, one directory per canonical slug | Scaffold: this document §4. Content: document 04 §2–§10, then each Phase 3 document |
| `platform/<slug>` | The eight platform services | Scaffold: this document §4. Content: 04 §11; `reference-data` additionally the Reference Data document; `sync` additionally document 11 |
| `agents/<name>` | Prompt, manifest pin, API version pin, evaluation set, deployment spec | 01 §8, 03 §8. Not this document |
| `models/<tier>` | Training and scoring source executed as Domino Jobs and Flows | 01 §7. Not this document, except §9's prohibition on direct datastore writes |
| `packages/canonical-schemas` | Shared kernel and shared payload schemas | Shared-packages document; schemas themselves 03 §7 |
| `packages/contracts` | Published specs and executable conformance suites | Shared-packages document; suite content 03 §10 |
| `packages/agent-tooling` | Manifests and their generator | 03 §8.2, §8.4 |
| `packages/py-common` | The shared middleware and dependency library §5 mandates | Shared-packages document; the required surface is enumerated in §5 |
| `packages/py-sync` | Outbox, inbox, relay, conflict policy | `docs/build/11-outbox-sync-library.md` |
| `packages/ts-common` | Generated TypeScript wire types | Shared-packages document |
| `data/synthetic` | Generator and fixtures | Synthetic-data document |
| `deploy/helm` | Umbrella charts and the shared chart library | This document §4.4 |
| `deploy/argocd` | Argo CD Applications and sync policy | This document §6.3 |
| `deploy/terraform` | Cluster-adjacent infrastructure | Not covered by any build-framework document yet — **[OPEN]** |
| `tools` | Repository-level validators and generators | This document §6 |
| `docs/adr` | ADRs for decisions taken after Phase 3 begins | This document §7.6 |

---

## 4. Per-service scaffold

**Every one of the seventeen services starts from this skeleton.** Domain services and platform services use the *same* skeleton; there is no second shape.

### 4.1 Layering — one structure, chosen

**[ESTABLISHED HERE]** Document 03 §1 explicitly permits any internal structure ("A sub-application may choose any internal structure; it may not vary its contract surface"). That permission would produce nine different structures written by nine agents, so this document removes it: **the layering below is mandatory.** Four layers, dependencies pointing strictly inward-to-outward in one direction only.

```
api  →  services  →  repositories  →  models
 ↑         ↑                            ↑
schemas   events                     (SQLAlchemy)
```

| Layer | Directory | Responsibility | Hard rules |
|---|---|---|---|
| **api** | `api/v1/` | HTTP shape only: routing, annotations, dependency wiring, status codes | Never touches a session or emits SQL. Never imports from `models/`. One module per resource collection |
| **schemas** | `schemas/` | Pydantic v2 **wire** models — requests, responses, problem details | Canonical kernel types are **imported** from `packages/canonical-schemas`, never redefined. A wire schema is never a SQLAlchemy model |
| **services** | `services/` | Domain and application logic. **Owns the transaction boundary** | The only layer that opens a transaction. The only layer that calls the outbox. Never sees a `Request` or `Response` |
| **repositories** | `repositories/` | Data access. **The only place SQL is written** | Accepts and returns domain/model objects, never Pydantic wire schemas. Never commits — the caller owns the transaction |
| **models** | `models/` | SQLAlchemy 2.0 `DeclarativeBase` mapped classes | Private to the service. Never serialized to the wire directly [03 principle 1] |
| **events** | `events/` | Outbox publication, inbox handlers, and the machine-readable event catalog | Publishers are called **from `services/`, inside the caller's transaction** [03 §5.2] |
| **readmodels** | `readmodels/` | Projections built from consumed events | Rebuilt from `changed_since` reads, **never** from the event bus [03 §5.1, finding D5] |

Why this layering and not hexagonal/ports-and-adapters: the transaction boundary is the single most consequential correctness surface in this system (03 §5.2's outbox, 03 §5.4's epoch fencing, finding D2's inbox rule). Putting it in a named layer with one rule — *`services/` opens transactions, nobody else* — is checkable by a reviewer and by a lint rule. A port/adapter split distributes that boundary across interfaces and makes the rule unstateable.

### 4.2 Directory skeleton

`<pkg>` below is the slug with hyphens replaced by underscores, prefixed `fathom_`: `registry` → `fathom_registry`, `fleet-status` → `fathom_fleet_status`, `failure-intel` → `fathom_failure_intel`, `reference-data` → `fathom_reference_data`.

```
services/<slug>/                       # or platform/<slug>/
├── pyproject.toml                     # name = "fathom-<slug>"; deps; tool config inherits workspace root
├── uv.lock                            # committed. Docker installs with --locked
├── Dockerfile                         # §4.3
├── .dockerignore
├── .env.example                       # §4.5 — every variable, no real values
├── alembic.ini
├── Makefile                           # thin: delegates to root make targets
├── README.md                          # purpose, owned aggregates, published/consumed events, run instructions
├── openapi.json                       # GENERATED, COMMITTED. CI fails on drift
├── asyncapi.yaml                      # GENERATED, COMMITTED. CI fails on drift
│
├── src/<pkg>/
│   ├── __init__.py
│   ├── main.py                        # create_app(): the ONLY assembly point. §4.6
│   ├── config.py                      # class Settings(BaseSettings) — the only reader of os.environ
│   ├── deps.py                         # FastAPI dependencies: session, principal, if_match, idempotency
│   ├── api/
│   │   ├── __init__.py                 # build_router() -> APIRouter(prefix=f"/api/v1/{SLUG}")
│   │   └── v1/
│   │       ├── __init__.py             # aggregates resource routers; one place lists them all
│   │       ├── <resource>.py           # one module per plural collection
│   │       └── health.py               # /healthz /readyz /metrics — wired from py_common, not written here
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── <resource>.py
│   ├── models/
│   │   ├── __init__.py                 # Base = DeclarativeBase subclass
│   │   └── <aggregate>.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── <aggregate>.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── <capability>.py
│   ├── events/
│   │   ├── __init__.py
│   │   ├── catalog.py                  # PUBLISHES: frozenset[str], CONSUMES: frozenset[str] — machine-readable
│   │   ├── publishers.py               # domain fact -> outbox row, via packages/py-sync
│   │   └── consumers.py                # EVENT_HANDLERS: dict[str, Handler], keyed by event_type
│   ├── readmodels/
│   │   ├── __init__.py
│   │   └── <projection>.py
│   ├── observability/
│   │   ├── __init__.py
│   │   ├── logging.py                  # calls py_common.logging.configure(); no local formatter
│   │   └── readiness.py                # registers this service's ReadinessCheck callables
│   └── migrations/
│       ├── env.py                      # async Alembic env
│       └── versions/
│
├── tests/
│   ├── conftest.py                     # app fixture, db container, broker container, principal factory
│   ├── unit/                           # no I/O. services/ and repositories/ logic against fakes
│   ├── integration/                    # real Postgres + real Redpanda via testcontainers
│   ├── contract/                       # this service's own contract obligations. §4.7
│   │   ├── test_openapi_committed.py    # regenerate == committed
│   │   ├── test_annotations.py           # every operation has x-substitution + x-side-effects
│   │   ├── test_problem_details.py       # RFC 9457 on every error path
│   │   ├── test_idempotency.py
│   │   ├── test_etag_if_match.py
│   │   └── test_changed_since.py          # 03 §4 snapshot/change-feed reads
│   └── conformance/
│       ├── conftest.py                  # provides the four fixtures the shared suite requires. §4.7
│       └── test_suite.py                # 8 lines. Collects packages/contracts/conformance/<slug>/
│
└── helm/
    ├── Chart.yaml                       # depends on the _fathom-common library chart
    ├── values.yaml                      # §4.4 — the mandatory shape
    ├── values-dev.yaml
    ├── templates/
    │   ├── _helpers.tpl
    │   ├── deployment.yaml
    │   ├── service.yaml
    │   ├── configmap.yaml
    │   ├── externalsecret.yaml
    │   ├── networkpolicy.yaml            # §4.4.2 — default-deny plus explicit allow
    │   ├── hpa.yaml                      # or scaledobject.yaml for event workers
    │   ├── servicemonitor.yaml
    │   ├── migration-job.yaml            # helm.sh/hook: pre-upgrade,pre-install
    │   └── poddisruptionbudget.yaml
    └── tests/                            # helm-unittest specs, including the NetworkPolicy assertion
```

The `helm/tests/` NetworkPolicy assertion is mandatory and specific: the rendered policy's egress peer set must **equal** `values.networkPolicy.egress` exactly and contain nothing else. That is the CI-testable invariant document 01 §11 promises.

### 4.3 Dockerfile skeleton

Two constraints dominate, both from document 01 §12 and document 02: **nothing is installed at container start** — Domino's own engineering documented runtime package installation as "categorically incompatible with air gap" [02 §4.1, finding D26] — and the container runs **non-root** with a read-only root filesystem.

```dockerfile
# syntax=docker/dockerfile:1.10
# ---------- stage 1: build ----------
FROM python:3.12-slim-bookworm@sha256:<PINNED_DIGEST> AS builder

ARG PIP_INDEX_URL                      # private index; no public PyPI at build time in air-gapped builds
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=ghcr.io/astral-sh/uv:0.5@sha256:<PINNED_DIGEST> /uv /usr/local/bin/uv

WORKDIR /build

# Dependencies first, from the lockfile only, so the layer caches independently of source.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Then the shared packages, then the service source.
COPY packages/py-common     /build/packages/py-common
COPY packages/py-sync       /build/packages/py-sync
COPY packages/canonical-schemas /build/packages/canonical-schemas
COPY services/<slug>/src    /build/src
COPY services/<slug>/alembic.ini /build/alembic.ini

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---------- stage 2: runtime ----------
FROM python:3.12-slim-bookworm@sha256:<PINNED_DIGEST> AS runtime

# Non-root, fixed numeric UID so the PodSecurityContext can assert it.
RUN groupadd --gid 65532 nonroot && \
    useradd  --uid 65532 --gid 65532 --no-create-home --shell /usr/sbin/nologin nonroot

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_INDEX=1 \
    UV_NO_INDEX=1

WORKDIR /app
COPY --from=builder --chown=root:root /build/.venv     /app/.venv
COPY --from=builder --chown=root:root /build/src       /app/src
COPY --from=builder --chown=root:root /build/alembic.ini /app/alembic.ini

USER 65532:65532
EXPOSE 8000

# No HEALTHCHECK: Kubernetes probes own liveness and readiness (§5.6).
# No ENTRYPOINT shell wrapper: exec form so SIGTERM reaches uvicorn for graceful drain.
CMD ["uvicorn", "<pkg>.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--loop", "uvloop", "--http", "httptools", \
     "--no-server-header", "--timeout-graceful-shutdown", "25"]
```

Hard rules on this file:

1. **No `apt-get`, `pip install`, `uv pip install`, `curl`, or `wget` in the runtime stage.** Ever. If the runtime stage needs a system library, it is installed in a *third* stage and copied, or the base image is changed. Detected in CI by a Dockerfile lint rule (§6.2 job 8).
2. `PIP_NO_INDEX=1` and `UV_NO_INDEX=1` in the runtime environment so an accidental install fails loudly rather than reaching a network.
3. Both base images and `uv` are **pinned by digest**, not by tag. A tag is mutable and defeats the reproducibility 01 §11 requires ("containers built once and promoted across environments").
4. **Not distroless** — **[ESTABLISHED HERE]**. `confluent-kafka` links librdkafka against glibc and OpenSSL, and asyncpg/psycopg wheels expect a glibc userland; a slim Debian base with a pinned digest keeps the dependency surface predictable and keeps a shell available for accreditation-time inspection. Revisit if image-surface scanning findings force it.
5. `--workers 1`. Scale with replicas [01 §11], not with in-pod processes.
6. `--timeout-graceful-shutdown 25` against a `terminationGracePeriodSeconds: 30` so in-flight requests drain before SIGKILL.

### 4.4 Helm chart skeleton

#### 4.4.1 `values.yaml` — the mandatory shape

Every service's `values.yaml` has these keys with these names. A sub-application may add keys under `app.config`; it may not rename or omit anything below.

```yaml
# ---- identity -------------------------------------------------------------
slug: pdm                              # canonical slug, 03 §3.1. Used for labels, base path, topic prefix
apiMajor: 1                            # the /api/v{major}/ segment

image:
  repository: registry.internal/fathom/pdm
  digest: ""                           # sha256:… — set by CI on merge. tag is for local dev only
  tag: ""
  pullPolicy: IfNotPresent
  pullSecrets: [fathom-registry]

replicaCount: 2

# ---- workload -------------------------------------------------------------
resources:
  requests: { cpu: 100m, memory: 256Mi }
  limits:   { cpu: "1",  memory: 512Mi }

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
  fathom.navy/pool: program            # program workloads on their own pool, 01 §11
tolerations: []
terminationGracePeriodSeconds: 30

# ---- probes ---------------------------------------------------------------
probes:
  liveness:  { path: /healthz, initialDelaySeconds: 5,  periodSeconds: 10, failureThreshold: 3 }
  readiness: { path: /readyz,  initialDelaySeconds: 3,  periodSeconds: 5,  failureThreshold: 3 }

# ---- application config (becomes FATHOM_* env vars; see §4.5) ------------
app:
  logLevel: INFO
  config:
    stalenessBoundSeconds: 300         # 03 §5.2 / obligation 14. REQUIRED for every consumer
    corsAllowedOrigins: []

# ---- owned datastore ------------------------------------------------------
database:
  clusterName: fathom-pdm-pg           # CloudNativePG Cluster in fathom-data. Exactly one
  name: pdm
  secretRef: fathom-pdm-pg-app         # created by External Secrets, never in the chart
  poolSize: 10
  maxOverflow: 5

migrations:
  enabled: true                        # rendered as a pre-install,pre-upgrade Helm hook Job, 01 §11
  backoffLimit: 0                      # fail the release rather than retry a partial migration

# ---- event bus ------------------------------------------------------------
events:
  brokers: redpanda.fathom-data.svc.cluster.local:9093
  schemaRegistry: http://redpanda.fathom-data.svc.cluster.local:8081
  consumerGroup: fathom-pdm-v1
  publishes:                           # MUST equal src/<pkg>/events/catalog.py PUBLISHES
    - fathom.pdm.prediction.v1
    - fathom.pdm.criticality_tier.v1
    - fathom.pdm.model_binding.v1
    - fathom.pdm.proposal.v1
  consumes:                            # MUST equal src/<pkg>/events/catalog.py CONSUMES
    - fathom.registry.configuration_baseline.v1
    # …

# ---- scaling --------------------------------------------------------------
autoscaling:
  mode: hpa                            # hpa | keda | none.  keda for event workers, 01 §11
  minReplicas: 2
  maxReplicas: 6
  targetRequestsPerSecond: 50
  kedaLagThreshold: 1000

# ---- network boundary (see §4.4.2) ---------------------------------------
networkPolicy:
  enabled: true                        # NEVER false in any environment
  ingress:
    fromServices: [gateway]            # in-namespace peers permitted to call this service
    fromNamespaces: []                 # cross-namespace ingress. Empty except gateway (see §4.4.2)
    allowPrometheusScrape: true
  egress:
    toOwnDatabase: true                # -> fathom-data, this service's cluster only
    toEventBus: true                   # -> fathom-data, Redpanda brokers + schema registry
    toServices: [auth, audit, reference-data]   # the ONLY permitted in-namespace egress
    toNamespaces: []                   # cross-namespace egress. Empty for all nine sub-applications
    allowDNS: true
```

#### 4.4.2 NetworkPolicy — default-deny plus explicit allow

Document 01 §11: "NetworkPolicy default-deny. Each service may reach only its own database and the event bus. This converts principle 1 from convention into an invariant testable in continuous integration." Two pieces implement that:

**A namespace-wide default-deny**, shipped once in `deploy/helm/fathom-sustainment/templates/default-deny.yaml` and again for `fathom-data`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: fathom-sustainment
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
```

**A per-service allow policy**, rendered from `values.networkPolicy` and from nothing else — the template must not contain a hard-coded peer:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "fathom.fullname" . }}
  labels: {{- include "fathom.labels" . | nindent 4 }}
spec:
  podSelector:
    matchLabels: {{- include "fathom.selectorLabels" . | nindent 6 }}
  policyTypes: [Ingress, Egress]
  ingress:
    {{- range .Values.networkPolicy.ingress.fromServices }}
    - from:
        - podSelector:
            matchLabels: { fathom.navy/service: {{ . }} }
      ports: [{ protocol: TCP, port: 8000 }]
    {{- end }}
    {{- if .Values.networkPolicy.ingress.allowPrometheusScrape }}
    - from:
        - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: monitoring } }
      ports: [{ protocol: TCP, port: 8000 }]
    {{- end }}
  egress:
    {{- if .Values.networkPolicy.egress.allowDNS }}
    - to:
        - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } }
          podSelector: { matchLabels: { k8s-app: kube-dns } }
      ports: [{ protocol: UDP, port: 53 }, { protocol: TCP, port: 53 }]
    {{- end }}
    {{- if .Values.networkPolicy.egress.toOwnDatabase }}
    - to:
        - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: fathom-data } }
          podSelector:
            matchLabels: { cnpg.io/cluster: {{ .Values.database.clusterName }} }
      ports: [{ protocol: TCP, port: 5432 }]
    {{- end }}
    {{- if .Values.networkPolicy.egress.toEventBus }}
    - to:
        - namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: fathom-data } }
          podSelector: { matchLabels: { app.kubernetes.io/name: redpanda } }
      ports: [{ protocol: TCP, port: 9093 }, { protocol: TCP, port: 8081 }]
    {{- end }}
    {{- range .Values.networkPolicy.egress.toServices }}
    - to:
        - podSelector:
            matchLabels: { fathom.navy/service: {{ . }} }
      ports: [{ protocol: TCP, port: 8000 }]
    {{- end }}
```

**The sanctioned edge set.** **[ESTABLISHED HERE]** — document 01 §11 states the principle and document 03 §6 states the event dependencies, but no document enumerates the allowed HTTP edges. These are they, and anything not listed requires a change to this document plus an ADR:

| Edge | Permitted | Reason |
|---|---|---|
| any service → own CloudNativePG cluster | yes | 01 §11 |
| any service → Redpanda brokers + schema registry | yes | 01 §11, 03 §5.5 |
| any service → `kube-dns` | yes | 01 §11 service discovery |
| any service → `auth` | yes | 03 §4: authorization is enforced by the receiving service, which requires JWKS/introspection |
| any service → `audit` | yes | 03 §15 obligation 9: provenance recording |
| any service → `reference-data` | yes | 04 §11: runtime enumeration and taxonomy resolution. Must be cached; it is not a compute-path dependency |
| `gateway` → any of the nine, plus `tool-server`, `knowledge-retrieval`, `notification` | yes | 01 §5: the gateway performs all view-model composition |
| `tool-server` → `gateway` | yes, **one rule**, pass-through only | `docs/build/34-tool-server.md` §4.4: an agent tool call is proxied through the gateway rather than the tool server calling a target sub-application directly, so the gateway's existing composition/auth path is reused rather than duplicated. The gateway must serve a pass-through mode for this edge — a requirement on the gateway's own build document, not established here |
| `pma` → `gateway` | yes, **one rule**, evidence materialisation only | `docs/build/23-pma.md` §10.3: PMA materialises an immutable evidence package from Telemetry's replay API rather than reading Telemetry's own object store (C36). Not a compute path in principle 2's sense — asynchronous, retried, out-of-band, and gating a workflow state transition rather than a request/response latency. Routes through the gateway for the same single-ingress-plus-caller-identity reason as the two rows above, rejecting a direct `pma → telemetry` rule for the same reason: it would need repeating for every future evidence consumer |
| any sub-application → **its own declared producers**, `changed_since` reads only | yes, **`GET` only, one path** | **[ESTABLISHED HERE]** — Registry's build-framework agent flagged that this row was missing: 03 §4 obligation 5 requires every declared consumer to rebuild its read model from `GET /{collection}?changed_since=` on the producer it consumes events from, and that is unavoidably a direct sub-application → sub-application call, not a gateway-composed one (the gateway does not sit on this path; rebuild must work even if the gateway is down). The row below still holds for everything else: only the exact `x-substitution: required` snapshot-read path, restricted to the producer/consumer pairs 03 §6's catalog already declares (so the peer set is closed and auditable, not "any service, any reason"), egress-allowed for `GET` only, and never used for a synchronous compute-path call — a service reading beyond that path from another sub-application's API is the violation this table's next row still forbids |
| **sub-application → sub-application, for anything other than the `changed_since` row above** | **NO** | 03 principle 2. This is the whole point of the policy |
| `domino-compute` namespace → `gateway` | yes, **one rule** | 01 §3 correction 2: scoring Jobs write predictions through PdM's bulk ingest API. **[ESTABLISHED HERE]** they route through the gateway so PdM keeps a single ingress and the caller's workload identity is attached at one place. The alternative — a direct `domino-compute` → `pdm` rule — is rejected because it would need repeating for every future batch producer |
| program ingress namespace → `domino-*` namespaces | yes | 01 §11, the documented coexistence seam |
| any service → public internet | **NO** | 01 principle 5, 01 §12 |

A helm-unittest spec asserts, per service, that the rendered egress peer set is exactly the values-declared set. That is the CI-testable invariant 01 §11 promises.

**The through-gateway exception is now a pattern, not three coincidences.** Domino scoring writes, tool-server proxying, and PMA evidence materialisation each independently arrived at the same shape: an asynchronous, non-compute-path transfer routed through the gateway rather than a direct sub-application edge, specifically to avoid a point-to-point rule that would need repeating for every future instance of the same need. A fourth sub-application requiring an equivalent transfer should default to this pattern rather than re-deriving it, and cite this paragraph rather than opening a fourth ADR.

### 4.5 Configuration and `.env.example`

**[ESTABLISHED HERE]** — no convention exists in the architecture documents.

- **`config.py` is the only module in the service that reads the environment.** Everything else takes `Settings` by dependency injection. A direct `os.environ` or `os.getenv` outside `config.py` is a lint failure.
- Prefix `FATHOM_`; nested delimiter `__`. `FATHOM_DATABASE__URL`, `FATHOM_EVENTS__BROKERS`, `FATHOM_APP__STALENESS_BOUND_SECONDS`.
- **No defaults for anything environment-specific.** A missing `FATHOM_DATABASE__URL` must fail at startup, not silently connect to localhost. Defaults are permitted only for genuinely universal values (log level, port, pool size).
- Secrets arrive **as environment variables projected from an External Secrets–managed Secret**. Never a file path in the chart, never a value in `values.yaml` [01 §11].
- `.env.example` lists **every** variable the service reads, with a comment and a non-secret placeholder. CI asserts `.env.example` and `Settings` agree in both directions (job 4). A variable in one and not the other is a failure.

```dotenv
# services/pdm/.env.example — every variable this service reads. No real values.
FATHOM_APP__LOG_LEVEL=INFO
FATHOM_APP__STALENESS_BOUND_SECONDS=300      # 03 §5.2: refuse freshness-dependent computation beyond this
FATHOM_DATABASE__URL=postgresql+asyncpg://pdm@localhost:5432/pdm
FATHOM_DATABASE__POOL_SIZE=10
FATHOM_EVENTS__BROKERS=localhost:9093
FATHOM_EVENTS__SCHEMA_REGISTRY=http://localhost:8081
FATHOM_EVENTS__CONSUMER_GROUP=fathom-pdm-v1
FATHOM_AUTH__ISSUER=https://keycloak.internal/realms/fathom
FATHOM_AUTH__JWKS_URL=https://keycloak.internal/realms/fathom/protocol/openid-connect/certs
FATHOM_AUDIT__BASE_URL=http://audit.fathom-sustainment.svc.cluster.local:8000
FATHOM_REFERENCE_DATA__BASE_URL=http://reference-data.fathom-sustainment.svc.cluster.local:8000
FATHOM_OTEL__ENABLED=false
```

### 4.6 `main.py` — the single assembly point

The app factory is the same in all seventeen services, differing only in the routers registered and the readiness checks added. It is the place the shared library is wired, and it must not contain re-implementations of anything in §5.

```python
from fastapi import FastAPI
from fathom_py_common import (
    assert_operation_annotations,      # fails startup if any operation lacks x-substitution/x-side-effects
    install_correlation_middleware,
    install_problem_handlers,          # RFC 9457
    install_idempotency_middleware,
    install_classification_middleware,
    install_health_routes,
    configure_logging,
    fathom_operation_id,
)
from .api import build_router
from .config import Settings
from .observability.readiness import register_checks

SLUG = "pdm"          # canonical slug, 03 §3.1
API_MAJOR = 1


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.app.log_level, service=SLUG)

    app = FastAPI(
        title="FATHOM — Predictive Maintenance",
        version=f"{API_MAJOR}.0",
        openapi_version="3.1.0",
        generate_unique_id_function=fathom_operation_id(SLUG),   # §7.3
        docs_url=None, redoc_url=None,                            # no interactive docs in cluster
    )

    # Middleware order is fixed and load-bearing. §5.7.
    install_correlation_middleware(app)          # 1. X-Correlation-Id in/out, bound to contextvars
    install_problem_handlers(app, slug=SLUG)     # 2. RFC 9457 for every raised error
    install_classification_middleware(app)       # 3. X-Classification on responses
    install_idempotency_middleware(app)          # 4. reads x-side-effects off the matched route

    app.include_router(build_router(settings))
    install_health_routes(app, checks=register_checks(settings))

    assert_operation_annotations(app)            # 5. fail fast, in-process, not only in CI
    return app


app = create_app()
```

### 4.7 Tests, and how the conformance suite gets wired in

Four test tiers, and they are not interchangeable.

| Tier | Directory | Runs against | Gate |
|---|---|---|---|
| **unit** | `tests/unit/` | No I/O. `services/` logic against fake repositories | Every PR. Fast |
| **integration** | `tests/integration/` | Real Postgres + real Redpanda via testcontainers | Every PR |
| **contract** | `tests/contract/` | **This service's own** obligations: spec drift, annotations, problem details, idempotency, ETag, `changed_since` | Every PR |
| **conformance** | `tests/conformance/` | **The shared suite from `packages/contracts/conformance/<slug>/`**, unmodified | Every PR, and before any release |

**The wiring mechanism.** `packages/contracts` is an installable package (`fathom-contracts`) whose conformance suites are ordinary pytest modules parameterized by fixtures. A service collects them by re-exporting, and supplies exactly four fixtures. Nothing else. **A service may not edit, skip, xfail, or subclass a shared conformance test** — if a test is wrong, it is fixed in `packages/contracts` for everyone.

```python
# services/pdm/tests/conformance/test_suite.py
"""Collects the shared conformance suite for this slug into this service's test run.

The suite lives in packages/contracts/conformance/pdm/ (path fixed by document 03 §10).
Do not add, skip, or modify tests here. Fixtures are in conftest.py.
"""
from fathom_contracts.conformance.pdm import *          # noqa: F401,F403
```

```python
# services/pdm/tests/conformance/conftest.py
import pytest
from fathom_contracts.conformance import ConformanceTarget, EventTap, FaultInjector

@pytest.fixture
async def conformance_target(app_client, principal_factory) -> ConformanceTarget:
    """Base URL + auth for a live instance of THIS service, plus its committed spec."""
    ...

@pytest.fixture
async def event_tap(redpanda) -> EventTap:
    """Reads published envelopes so event tests can assert envelope, partition key,
    and within-partition ordering (03 §10 'Event tests')."""
    ...

@pytest.fixture
async def fault_injector(app_client) -> FaultInjector:
    """Interrupts the service mid-operation so fault-injection tests can assert
    'no state change without its event' (03 §10, obligation 2)."""
    ...

@pytest.fixture
async def reference_dataset(db) -> None:
    """Loads the synthetic Navy reference dataset for deterministic runs
    (03 §10; content owned by the synthetic-data document)."""
    ...
```

Two consequences worth stating explicitly:

- **Consumer-driven tests** [03 §10] are contributed by each declared consumer *into* `packages/contracts/conformance/<producer-slug>/consumers/<consumer-slug>/`. A consumer that declares a dependency in document 03 §6 and contributes no test has an unmet Definition-of-Done item — and `tools/check_event_catalog.py` is what proves the declaration exists in the first place.
- **Manifest tests** [03 §8.4] run inside the same suite, so a conformant substitution is automatically a conformant tool surface. They read `packages/agent-tooling/manifests/<slug>/`.

### 4.8 Structured logging

**[ESTABLISHED HERE]** in mechanism; the requirement is 03 §4 and 03 §15 obligation 15.

- JSON to stdout only. No files, no rotation, no sidecar shipper in the service.
- `X-Correlation-Id` is read (or minted) by the correlation middleware, bound into a `contextvars` context, and emitted as `correlation_id` on **every** log line. Propagated onto every outbound httpx request by the shared client factory, and onto every event envelope's `correlation_id` field [03 §5.4].
- Mandatory fields on every line: `timestamp` (RFC 3339, UTC, explicit offset), `level`, `service` (canonical slug), `event` (a stable short string, **not** an interpolated sentence), `correlation_id`. Present when in scope: `causation_id`, `principal_id`, `asset_id`, `installed_item_id`, `baseline_epoch`, `event_type`, `http_status`, `duration_ms`.
- **`duration_ms` is measured with `time.monotonic()`, never a wall clock** [03 §5.4, finding D29].
- **Never logged:** bearer tokens, `Idempotency-Key` values, request bodies of state-changing operations, retrieved corpus text, or any field carrying a classification above the deployment's declared level. Redaction is a shared processor in `packages/py-common`, not a per-service habit.
- `event` values are snake_case and stable, because they are queried: `prediction_invalidated`, `inbox_event_applied`, `outbox_relay_lagging`.

---

## 5. API conventions as code-level rules

This section does **not** restate document 03 §4. It translates it into FastAPI mechanisms. Where it says "shared", the component lives in `packages/py-common` and **is not reimplemented in any service** — nine hand-rolled idempotency middlewares would be nine subtly different concurrency semantics.

### 5.1 `x-substitution` and `x-side-effects` on every operation

Document 03 §4.1 requires both annotations on every operation, validated in CI. Document 03 §8.1 adds `x-agent-eligible`, permitted only where side effects are `none` or `proposal-only`.

**Mechanism: a keyword-expanding helper returning FastAPI route kwargs.** Chosen over a decorator because FastAPI's route decorator already owns the callable, and over a dependency because dependencies cannot write into the OpenAPI operation object.

```python
# packages/py-common/src/fathom_py_common/openapi.py
from enum import StrEnum
from typing import Any

class Substitution(StrEnum):
    REQUIRED = "required"
    INTERNAL = "internal"

class SideEffects(StrEnum):
    NONE = "none"
    PROPOSAL_ONLY = "proposal-only"
    STATE_CHANGING = "state-changing"

def operation(
    *,
    substitution: Substitution,
    side_effects: SideEffects,
    agent_eligible: bool = False,
    idempotency: str | None = None,     # "required" | "optional" | None -> derived from side_effects
) -> dict[str, Any]:
    """Return route kwargs carrying the document 03 §4.1 / §8.1 annotations.

    Raises at import time — not at request time, not in CI — if the operation
    asserts agent eligibility while declaring state-changing side effects
    (03 §8.1, findings C1/D11).
    """
    if agent_eligible and side_effects is SideEffects.STATE_CHANGING:
        raise ValueError(
            "x-agent-eligible is permitted only where x-side-effects is "
            "'none' or 'proposal-only' (document 03 §8.1)"
        )
    extra = {
        "x-substitution": substitution.value,
        "x-side-effects": side_effects.value,
    }
    if agent_eligible:
        extra["x-agent-eligible"] = True
    if idempotency is not None:
        extra["x-idempotency"] = idempotency
    return {"openapi_extra": extra}
```

Usage — this is the shape every route in every service takes:

```python
@router.get(
    "/predictions",
    response_model=Page[FailurePrediction],
    **operation(substitution=Substitution.REQUIRED, side_effects=SideEffects.NONE,
                agent_eligible=True),
)
async def list_predictions(...): ...


@router.post(
    "/scoring-runs/{scoring_run_id}/what-if",          # compute-only POST: agent-eligible by design
    response_model=WhatIfResult,
    **operation(substitution=Substitution.INTERNAL, side_effects=SideEffects.NONE,
                agent_eligible=True),
)
async def what_if(...): ...


@router.post(
    "/predictions/bulk",                               # the 03 §4 bulk, idempotent, fenced write path
    status_code=202,
    **operation(substitution=Substitution.REQUIRED, side_effects=SideEffects.STATE_CHANGING),
)
async def bulk_ingest(...): ...
```

**Three layers of enforcement, deliberately redundant:**

1. **Import time** — `operation()` raises on the eligibility violation, so the illegal combination cannot be written.
2. **Startup** — `assert_operation_annotations(app)` walks `app.routes` and raises if any non-health route lacks either annotation. A service with a missing annotation fails its own unit tests.
3. **CI** — `tools/check_openapi.py` re-validates over the committed `openapi.json`, which is what a substituting partner and the manifest generator actually read.

**Side-effect class drives runtime behaviour.** The idempotency middleware reads the matched route's annotations at request time — `request.scope["route"].openapi_extra` — so declaration and enforcement cannot diverge:

| `x-side-effects` | Runtime consequence |
|---|---|
| `none` | No `Idempotency-Key` required. Eligible for agent selection. Must not open a write transaction (asserted in tests) |
| `proposal-only` | `Idempotency-Key` **required**. May write only proposal aggregates. Eligible for agent selection |
| `state-changing` | `Idempotency-Key` **required** on all unsafe methods. **Never** agent-eligible |

**Naming carve-outs** [03 §4, finding C23]: singleton and query-projection operations that are legitimately singular are enumerated in the spec, not merely tolerated. Mechanism: a root-level extension the service supplies to `FastAPI(openapi_extra=...)`, listing operation IDs.

```json
"x-naming-carve-outs": [
  { "operationId": "pdm_get_calibration_summary", "reason": "query projection; no collection semantics" }
]
```
`tools/check_openapi.py` fails on any singular path segment whose operation is not listed.

### 5.2 RFC 9457 problem details

Shared, in `packages/py-common`. Installed by one call; no service writes its own handler.

```python
install_problem_handlers(app, slug=SLUG)
```

It registers four handlers and returns `application/problem+json` from all of them:

| Handler | Produces |
|---|---|
| `ProblemException` (the library's own) | The declared `type`, `title`, `status`, `detail`, plus extension members |
| `RequestValidationError` | `type=urn:fathom:problem:common:validation-error`, `status=422`, `errors[]` with the field pointers |
| `HTTPException` | Mapped to a common `type` per status code |
| `Exception` (catch-all) | `type=urn:fathom:problem:common:internal-error`, `status=500`, **no detail leaked**, correlation ID echoed |

```json
{
  "type": "urn:fathom:problem:pdm:baseline-superseded",
  "title": "Prediction baseline is superseded",
  "status": 409,
  "detail": "Scoring run was computed against baseline_epoch 41; current epoch is 43.",
  "instance": "urn:fathom:request:0f2c8f5a-...",
  "correlation_id": "0f2c8f5a-...",
  "baseline_epoch_submitted": 41,
  "baseline_epoch_current": 43
}
```

Rules:

- **`type` is a URN, not an HTTPS URL.** **[ESTABLISHED HERE]** — 03 §4 requires "a stable URI" without naming a scheme. `urn:fathom:problem:<slug>:<kebab-case-code>` is chosen because an `https://` type invites a runtime dereference, and 01 principle 5 forbids runtime dependence on public-internet services and external DNS. URNs are stable identifiers with no resolution implied.
- **Every `type` a service can emit is declared once**, as an enum in `schemas/problems.py`, and appears in the OpenAPI `responses` of every operation that can raise it. A `type` string constructed inline is a review rejection.
- **`detail` is never used for control flow** [03 §4]. Machine-readable facts go in extension members (`baseline_epoch_current` above), never parsed out of prose.
- A problem response still carries `X-Correlation-Id` and `X-Classification`.

### 5.3 `Idempotency-Key` — shared middleware

Document 03 §4 requires all unsafe methods to accept `Idempotency-Key`, and require it for anything reachable from an agent proposal, a bulk write, or an edge sync. **This is one shared middleware.** Nine implementations would give nine different answers to "same key, different body."

- **Storage: the service's own database**, table `idempotency_keys`. **[ESTABLISHED HERE]** — there is no Redis or shared cache in the 01 §11 inventory, and using the owned database keeps the record in the same transaction as the effect, which is the only way replay can be exactly faithful.
- Columns: `key`, `route_id`, `principal_id`, `request_hash`, `response_status`, `response_body`, `created_at`, `expires_at`. Primary key `(key, route_id, principal_id)` — scoping by route and principal prevents one caller's key colliding with another's.
- Behaviour:

| Situation | Response |
|---|---|
| Key absent on a `state-changing` or `proposal-only` operation | `400`, `urn:fathom:problem:common:idempotency-key-required` |
| Key unseen | Execute. Persist `(key, request_hash, status, body)` **in the same transaction as the effect** |
| Key seen, `request_hash` matches | Replay the stored status and body. Do **not** re-execute. `Idempotency-Replayed: true` |
| Key seen, `request_hash` differs | `409`, `urn:fathom:problem:common:idempotency-key-reuse` |
| Key seen, original still in flight | `409`, `urn:fathom:problem:common:request-in-progress`, `Retry-After` |

- Retention 24 hours by default; longer for edge-sync-reachable operations, because a disconnected hull's retry window is measured in weeks — **[OPEN]**: the exact edge retention is set by document 11 alongside the divergence budget [03 §11].
- `request_hash` is over the canonicalized body plus the path and query, **excluding** `X-Correlation-Id` — the same logical retry from a different request has a different correlation ID and must still replay.

### 5.4 `ETag` / `If-Match` — shared dependency

- **ETag is derived from a monotonic `version` integer column on the aggregate root**, rendered `W/"<version>"`. **[ESTABLISHED HERE]** — a content hash would change when an unrelated denormalized field changed and would produce spurious 412s; a version column makes the concurrency check a single `WHERE version = :expected` predicate.
- Shared dependency:

```python
from fathom_py_common.concurrency import require_if_match, ETagged

@router.patch(
    "/proposals/{proposal_id}",
    **operation(substitution=Substitution.REQUIRED, side_effects=SideEffects.STATE_CHANGING),
)
async def adjudicate(
    proposal_id: UUID,
    body: AdjudicationRequest,
    expected_version: int = Depends(require_if_match),   # 428 if header absent, 400 if malformed
    ...
): ...
```

- `require_if_match` returns `428 Precondition Required` when the header is absent on `PUT`/`PATCH` and on proposal adjudication [03 §4, 03 §7.2]. **This is stricter than 03 §4's letter and is deliberate**: finding D16 is that a missing claim/`If-Match` produces two approvals and two work orders, so the failure mode of "header optional" is exactly the defect. Flagged as **[ESTABLISHED HERE]**.
- Repositories implement the compare-and-swap as `UPDATE … SET version = version + 1 WHERE id = :id AND version = :expected`; zero rows affected raises `PreconditionFailed` → `412` with `urn:fathom:problem:common:version-conflict`.
- Every response for an updatable resource sets `ETag`. A `GET` that returns an aggregate without an `ETag` is a contract-test failure.

### 5.5 Correlation, classification, and authorization

| Concern | Mechanism | Source |
|---|---|---|
| `X-Correlation-Id` | Shared middleware: accept, else mint a UUIDv4; bind to `contextvars`; echo on the response; propagate on every httpx call and into every event envelope | 03 §4, 03 §5.4, obligation 15 |
| `X-Classification` | Shared middleware sets it from the response's classification label; per-field redaction is a `packages/canonical-schemas` serializer concern, not a middleware one | 03 §4, 03 §7.3 |
| Authorization | A **dependency**, `Depends(require_authz(...))`, evaluated **in the receiving service** against ABAC attributes. **Never delegated to the gateway alone** | 03 §4, obligation 7 |
| Agent authority | The principal carries a **`fathom.agent.authority`** claim of `delegated` \| `accountable_autonomous`; `accountable_autonomous` principals are rejected by the dependency on any `state-changing` operation. **Not named `authority_class`** — document 03 §7.2.1 independently defines `Proposal.authority_class` as a five-value organizational-role field with a different vocabulary and a different owner (the resource, not the principal), and the two must never share a name or a service reading one gets the other's value silently. A principal's own held organizational roles, compared against `Proposal.authority_class` at adjudication, are carried separately as `fathom.identity.authority_classes[]` (plural, deliberately sharing §7.2.1's vocabulary — that sharing is what makes the comparison meaningful) | 03 §7.2.1, §8.3; naming fixed by `docs/build/31-auth.md` §2.5, binding on `packages/py-common` |
| Cursor pagination | Shared `Page[T]` and `CursorParams`; opaque base64url cursor over a stable sort key; `next_cursor` in the body; **no total count** on unbounded collections | 03 §4 |
| `changed_since` reads | Shared `ChangedSinceParams` plus a repository mixin. **Every aggregate a declared consumer projects must expose one** — this is the rebuild path, and the event bus is not | 03 §4, obligation 5, finding D5 |
| Backfill | `X-Backfill: true` accepted on bulk writes; suppresses downstream notification and command generation while still producing events marked `replay: true` | 03 §5.3 |

### 5.6 `/healthz`, `/readyz`, `/metrics`

Installed by `install_health_routes(app, checks=...)`. Identical in all seventeen services.

| Route | Semantics | Fails when |
|---|---|---|
| `/healthz` | Liveness. Process-local only | The event loop is wedged. **Never** consults a dependency — a database blip must not trigger a restart storm |
| `/readyz` | Readiness. Aggregates registered `ReadinessCheck` callables | Any check fails. Returns a per-check JSON breakdown |
| `/metrics` | Prometheus text exposition | — |

**Mandatory readiness checks in every service** [03 §4, §5.2, obligation 14]:

1. `database` — a `SELECT 1` on the owned cluster within a short timeout.
2. `migrations` — Alembic head in the database equals the head baked into the image. A pod running against an unmigrated schema must not receive traffic.
3. `broker` — producer metadata reachable.
4. `read_model_lag` — **for every consumed event type**, `now - last_applied_recorded_at` compared against the declared `stalenessBoundSeconds`. Exceeding it makes the service **not ready**, which is how 03 §5.2's "consumer staleness is observable" becomes operative rather than decorative.
5. `outbox_drain` — pending outbox depth and oldest-pending age within bounds. Semantics owned by document 11; the check name is fixed here so dashboards and alerts are uniform.

**Metric names are fixed here** so that seventeen services do not invent seventeen names:

```
fathom_http_requests_total{service,method,route,status}
fathom_http_request_duration_seconds{service,method,route}      # histogram, monotonic-clock measured
fathom_readmodel_lag_seconds{service,event_type}                # gauge
fathom_inbox_events_total{service,event_type,outcome}           # outcome=applied|duplicate|blocked_on_antecedent
fathom_outbox_pending{service}                                  # gauge
fathom_outbox_oldest_pending_seconds{service}                    # gauge
fathom_outbox_published_total{service,event_type}
fathom_idempotency_replays_total{service,route}
fathom_staleness_refusals_total{service,computation}            # 03 §5.2 refusal-to-run counter
fathom_problem_responses_total{service,type}
```

### 5.7 Middleware order

Fixed, and load-bearing. Registered in `create_app` in this order (FastAPI executes registered middleware outermost-first):

1. **Correlation** — must be outermost so every subsequent layer, including the catch-all error handler, has a correlation ID.
2. **Problem handlers** — exception handlers, so anything raised deeper is rendered as RFC 9457.
3. **Classification** — sets `X-Classification` on the way out.
4. **Idempotency** — must run *after* routing has matched (so it can read the route's `x-side-effects`) and *before* the handler executes.
5. Authorization is a **dependency**, not middleware, so it runs per-operation with typed access to path parameters. Do not convert it to middleware.

---

## 6. CI/CD pipeline skeleton

### 6.1 Provider

**[OPEN — flagged in §10].** No architecture document expresses a preference; the only near-signal is document 02 §4.1's mention of an internal blueprint repository with continuous integration, which is not a program decision. This document therefore establishes:

- **Default: GitHub Actions with self-hosted runners.** Self-hosted because the production target is self-managed OpenShift and air-gapped enclaves [01 §12], and a cloud-hosted runner cannot reach a private registry.
- **All pipeline logic lives in `make` targets and `tools/` scripts.** Workflow YAML does nothing but check out, set up, and call `make <target>`. A migration to GitLab CI or Tekton then rewrites only the thin invocation layer. **No pipeline step may exist only as inline YAML.**

### 6.2 On every pull request

Jobs run in parallel where possible. Every one is blocking. Path filters scope jobs to the changed services; jobs 4, 6, 7, and 9 run repository-wide because they are cross-service reconciliations.

| # | Job | Command | Enforces |
|---|---|---|---|
| 1 | **Lint & format** | `make lint` → `ruff check .`, `ruff format --check .`, `pnpm eslint`, `pnpm prettier --check` | §7.4 |
| 2 | **Type check** | `make typecheck` → `mypy --strict`, `tsc --noEmit` | §7.4 |
| 3 | **Unit + integration tests** | `make test` → `pytest tests/unit tests/integration --cov` | §4.7 |
| 4 | **Contract checks** | `make contract` → regenerate `openapi.json` and `asyncapi.yaml` and diff against committed; `tools/check_openapi.py`; `schemathesis run`; `.env.example` ↔ `Settings` reconciliation | 03 §4, §4.1, §15 obligation 1 |
| 5 | **Conformance suite** | `make conformance` → `pytest tests/conformance` against an ephemeral instance | 03 §10, obligation 10 |
| 6 | **Event-catalog reconciliation** | `python tools/check_event_catalog.py` **(exists)**; plus `tools/check_service_events.py` (new) reconciling `events/catalog.py` ↔ `helm/values.yaml` `events.publishes/consumes` ↔ document 03 §6 | 03 §6, findings C3–C5, C37, C38 |
| 7 | **Schema compatibility** | `make schema-check` → every `packages/canonical-schemas` payload checked against the registry's compatibility rules | 03 §5.5 |
| 8 | **Chart & container checks** | `make charts` → `helm lint`, `helm template \| kubeconform --strict`, `helm unittest` (including the NetworkPolicy egress-equality assertion); `hadolint` plus a rule rejecting `apt-get`/`pip install`/`curl` in any runtime stage | 01 §11, 01 §12 |
| 9 | **Manifest generation** | `make manifests` → regenerate MCP-style descriptors from committed specs. **Fails, never warns**, when a selected operation is missing, not `x-agent-eligible`, or undescribed | 03 §8.2 |
| 10 | **Build (no push)** | `make image` → multi-stage build, Trivy scan, Syft SBOM, both uploaded as artifacts | 01 §12, §2.4 |

**Merge requires all ten green.** No `continue-on-error`, no soft-fail job. A check that is allowed to fail is not a check; and the specific defects these guard — a consumer declared but not implemented (C3), an agent-eligible state-changing operation (C1/D11), a NetworkPolicy admitting an undeclared peer (01 §11) — are precisely the class that survives a warning.

### 6.3 On merge to `main`

1. **Build and push.** Image tagged `sha-<short>` **and pushed with its digest recorded**. Promotion across environments moves the digest, never rebuilds [01 §11].
2. **Publish contracts.** `openapi.json`, `asyncapi.yaml`, and `packages/canonical-schemas` versions published to the internal package index; register payload schemas with the schema registry.
3. **Regenerate TypeScript types** into `packages/ts-common/src/generated/` and fail if the working tree is dirty afterward (types must have been committed).
4. **Update GitOps.** A bot commit writes the new digest into `deploy/argocd/environments/dev/values.yaml`.
5. **Argo CD syncs `dev` automatically.** Staging and production are **manual sync with an Argo CD sync window**. **[ESTABLISHED HERE]** — 01 §11 notes Argo CD "supplies the record of what was deployed and when, which is relevant to accreditation", and an auto-syncing production deprives an accreditor of a change-approval point.
6. **Migrations** run as the chart's `pre-upgrade,pre-install` hook Job with `backoffLimit: 0`, so a failed migration fails the release rather than leaving a half-migrated schema serving traffic [01 §11].
7. **Post-sync verification.** A `PostSync` Argo CD hook Job calls `/readyz` on every replica and asserts the Alembic head matches; a failure triggers rollback to the previous digest.

### 6.4 What CI does not do

- It does not run agent evaluation gates — those are Domino Experiment Manager's, per 01 §8.8.
- It does not deploy Domino artifacts. Models and agents are promoted through Domino's registry; **pin enforcement is the program's own pipeline** because Domino gates act on infrastructure proxies only [01 §9, 02 §4.4].
- It does not reach the public internet from a runner in an air-gapped configuration; all actions, images, and packages come from the private mirror [01 §12].

---

## 7. Coding standards

### 7.1 The canonical sub-application slug table

Reproduced **exactly** from document 03 §3.1. Used without variation in topic names, event `producer` fields, `target_sub_app` values, API base paths, conformance directories, manifest directories, service directory names, Helm release names, Kubernetes labels, and consumer group names.

| Sub-application (canonical name) | Slug | Display abbreviation |
|---|---|---|
| Asset & Configuration Registry | `registry` | Registry |
| Condition & Telemetry | `telemetry` | Telemetry |
| Predictive Maintenance | `pdm` | PdM |
| Fleet Status & Readiness | `fleet-status` | Fleet Status |
| Maintenance Execution & Scheduling | `maintenance` | Scheduling |
| Supply Chain & Inventory | `supply` | Supply |
| Post-Mission Analysis | `pma` | PMA |
| Failure Intelligence | `failure-intel` | Failure Intelligence |
| System Test & Design Advisory | `design-advisory` | Design Advisory |

Platform services use `gateway`, `auth`, `reference-data`, `knowledge-retrieval`, `audit`, `notification`, `sync`, `tool-server`.

Derived forms, mechanically:

| Form | Rule | Example (`fleet-status`) |
|---|---|---|
| Directory | slug verbatim | `services/fleet-status/` |
| Python distribution | `fathom-<slug>` | `fathom-fleet-status` |
| Python package | `fathom_` + slug with `-`→`_` | `fathom_fleet_status` |
| API base path | `/api/v{major}/<slug>/` | `/api/v1/fleet-status/` |
| Topic | `fathom.<slug>.<aggregate>.v<major>`, aggregate `snake_case` | `fathom.fleet-status.casrep_risk.v1` |
| Consumer group | `fathom-<slug>-v<major>` | `fathom-fleet-status-v1` |
| Kubernetes label | `fathom.navy/service: <slug>` | `fathom.navy/service: fleet-status` |
| Database cluster | `fathom-<slug>-pg` | `fathom-fleet-status-pg` |
| Conformance directory | `packages/contracts/conformance/<slug>/` | fixed by 03 §10 |
| Manifest directory | `packages/agent-tooling/manifests/<slug>/` | fixed by 03 §8.2 |

### 7.2 Domain vocabulary

Document 03 §3.2 is binding on **identifiers as well as prose**. The losing variants are not to appear in a class name, a variable, a table, a column, a topic, a log field, or a comment.

| Use | Never |
|---|---|
| **installed item** / `installed_item_id` | equipment, component, part instance, `equipment_id` |
| **position** / `position_id` | slot, location |
| **system** / `system_id` | subsystem, group |
| **part** / `niin` | component, item |
| **mission** / `mission_id` | mission event, mission record |
| **sub-application** | sub-app, service, microservice |
| **Domino Endpoint** (always qualified) | endpoint |
| **operation** (an HTTP route) | endpoint |

Note the last two: `endpoint` is ambiguous in this program and is therefore banned as a bare noun. A ruff `flake8-forbidden-words`-style rule or a `tools/check_vocabulary.py` grep gate enforces the identifier half of this.

### 7.3 Naming

| Surface | Convention | Source |
|---|---|---|
| JSON fields | `snake_case` | 03 §4 |
| URL paths | `kebab-case`, plural collections; singleton and query-projection carve-outs enumerated in the spec | 03 §4, finding C23 |
| Sub-resource actions | `POST /{collection}/{id}/{action}`, action a `kebab-case` verb | 03 §4, finding C24 |
| Version selectors | Query parameters, never path identifiers | 03 §4 |
| Event types | `fathom.<slug>.<aggregate>.<verb>`, `snake_case` throughout | 03 §5.4, finding C26 |
| OpenAPI `operationId` | `<slug_underscored>_<verb>_<resource>` — set via `generate_unique_id_function`, never left to FastAPI's default | **[ESTABLISHED HERE]**: operation IDs must be unique in the gateway-merged document and are the join key manifests select on [03 §8.2] |
| Python modules | `snake_case`; classes `PascalCase`; constants `UPPER_SNAKE` | PEP 8 |
| SQL tables | `snake_case`, plural | **[ESTABLISHED HERE]** |
| SQL identifier columns | Exactly 03 §3.3's names | 03 §3.3 |
| Alembic revisions | `<utc_timestamp>_<slug>_<short_description>.py` | **[ESTABLISHED HERE]** — sortable, and greppable per service |
| Env vars | `FATHOM_<SECTION>__<KEY>` | §4.5 |
| Metrics | `fathom_<subsystem>_<unit>` per §5.6's fixed list | **[ESTABLISHED HERE]** |
| TypeScript | `PascalCase` components and types, `camelCase` values; **wire-shaped objects keep their `snake_case` field names** because they are generated | **[ESTABLISHED HERE]** — renaming at the boundary produces a mapping layer that drifts |

### 7.4 Linting, formatting, typing

Configured **once** in the workspace-root `pyproject.toml`. A service does not carry its own `[tool.ruff]` or `[tool.mypy]` section, and adding one is a review rejection.

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E","W","F","I","N","UP","B","A","C4","DTZ","T20","SIM","TCH","PTH","RUF",
          "ASYNC","S","BLE","FBT","ANN","ARG","PL","TRY","ERA"]
ignore = ["ANN401", "PLR0913"]
# DTZ is mandatory and not to be relaxed: it is what forbids naive datetimes,
# which document 03 §4 (RFC 3339 with explicit offset) requires.
# T20 forbids print(); all output is structlog (§4.8).

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101", "ANN", "PLR2004"]           # asserts and magic numbers are fine in tests
"**/migrations/versions/*" = ["ANN", "ERA", "E501"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_unreachable = true
disallow_any_explicit = false                      # Pydantic and SQLAlchemy internals need Any
plugins = ["pydantic.mypy"]

[[tool.mypy.overrides]]
module = ["confluent_kafka.*", "testcontainers.*"]
ignore_missing_imports = true                      # the ONLY sanctioned override category
```

- **`mypy --strict` with no per-service relaxation.** The only sanctioned overrides are `ignore_missing_imports` for third-party packages that ship no stubs. `# type: ignore` requires a specific error code and a comment naming the reason.
- **`ruff format` is the formatter.** black, isort, and flake8 are prohibited (§2.2).
- Coverage floor **[ESTABLISHED HERE]**: 80% on `services/` and `repositories/`; no floor on `api/` (thin) or `models/` (declarative). Coverage is a smoke alarm, not a goal — the conformance suite is the real gate.

### 7.5 Commits and branches

**[ESTABLISHED HERE]** — nothing in the architecture documents addresses this.

- **Trunk-based.** `main` is always deployable. Branches are short-lived: `feat/<slug>-<short-description>`, `fix/<slug>-<short-description>`, `docs/<short-description>`, `chore/<short-description>`.
- **Conventional Commits, with the canonical slug as scope**: `feat(pdm): add bulk prediction ingest with baseline fencing`. Permitted types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`. Scope is a canonical slug from §7.1, a package name (`py-common`, `canonical-schemas`), or `repo`.
- A commit touching a contract surface **must** cite the governing section: `feat(registry): add changed_since reads (03 §4, D5)`.
- **Squash merge.** One commit per PR on `main`, so the Argo CD deployment record maps one-to-one to a reviewed change — which is the accreditation-relevant property in 01 §11.
- A PR that changes an architecture document and code together is split: the document change lands first, so document 03 remains binding rather than retro-fitted.
- **ADRs** (`docs/adr/NNNN-title.md`) are required for any decision that contradicts or extends this document, any new sanctioned NetworkPolicy edge, and any deviation from document 03. An ADR is not a substitute for changing document 03 when document 03 is wrong.

---

## 8. The shared Definition of Done

**This is the section every other build-framework document references and instantiates.** A service is not done when it works; it is done when every box below is ticked, with the verifying command run and its output green. Each subsequent build-framework document reproduces this checklist for its own component, adds component-specific items, and **removes nothing**.

Copy this into the service's `README.md` and tick it there.

### 8.1 Contract and specification

- [ ] **OpenAPI 3.1 document generated from code and committed** at `services/<slug>/openapi.json`. `make contract` shows no drift. *(03 §4, obligation 1)*
- [ ] **Every operation declares `x-substitution`** (`required` | `internal`). *(03 §4.1)*
- [ ] **Every operation declares `x-side-effects`** (`none` | `proposal-only` | `state-changing`). *(03 §4.1)*
- [ ] **`x-agent-eligible` appears only where `x-side-effects` is `none` or `proposal-only`.** Verified by `tools/check_openapi.py` **and** by `assert_operation_annotations` at startup. *(03 §8.1, C1/D11)*
- [ ] **Base path is `/api/v1/<canonical-slug>/`** with the slug from §7.1 verbatim. *(03 §4, C25)*
- [ ] Paths are `kebab-case`, collections plural; **every singular path is enumerated in `x-naming-carve-outs`** with a reason. *(03 §4, C23)*
- [ ] All JSON fields `snake_case`; all identifiers exactly 03 §3.3's names; **no local surrogate identifier is exposed**. *(03 principle 4, §3.3)*
- [ ] **`changed_since` snapshot/change-feed read exists for every aggregate a declared consumer projects**, cursor-paginated. *(03 §4, obligation 5, D5)*
- [ ] Cursor pagination on every unbounded collection; no total count. *(03 §4)*
- [ ] Every error path returns **RFC 9457 `application/problem+json`** with a `urn:fathom:problem:<slug>:<code>` type declared in `schemas/problems.py` and present in the spec's `responses`. *(03 §4, §5.2)*
- [ ] **`Idempotency-Key` accepted on all unsafe methods and required on every `state-changing` and `proposal-only` operation**, via the shared middleware — not a local implementation. *(03 §4, §5.3)*
- [ ] **`ETag` on every updatable resource; `If-Match` required on `PUT`, `PATCH`, and proposal adjudication**, via the shared dependency. Lost updates return `412`. *(03 §4, §7.2, D16)*
- [ ] **`X-Correlation-Id` accepted, minted when absent, echoed on the response, propagated to every downstream call and every event.** *(03 §4)*
- [ ] `X-Classification` on every response; per-field redaction where levels mix. *(03 §4, §7.3)*
- [ ] Authorization enforced **in this service** against ABAC attributes, never relying on the gateway. *(03 §4, obligation 7)*
- [ ] Every timestamp RFC 3339, UTC, explicit offset. No naive datetime anywhere (ruff `DTZ` clean). *(03 §4)*
- [ ] **A bulk, idempotent, fenced write operation exists** for every path by which a batch process delivers results. *(03 §4, D10/C7)*
- [ ] Deprecation policy honoured: any superseded major version still served, with `Deprecation` and `Sunset` headers. *(03 §4)*

### 8.2 Events

- [ ] **Every state change reachable through the contract emits an event.** Asserted by fault-injection tests, not by inspection. *(obligation 2)*
- [ ] **Every published event carries the full 03 §5.4 envelope**: `event_id`, `event_type`, `event_version`, `occurred_at`, `recorded_at`, `producer`, `correlation_id`, `causation_id`, `scope`, `subject` (exactly one identifier matching `scope`), `baseline_epoch` where applicable, `classification`, `replay`, and the full `clock` block. *(03 §5.4)*
- [ ] **The `clock` block is complete**: `monotonic_seq`, `hlc`, `source_time`, `ingest_time`, and `sync_quality` with all six sub-fields. *(03 §5.4, D29)*
- [ ] Topics named `fathom.<slug>.<aggregate>.v<major>`; partition key per 03 §5.1; **compaction key is the aggregate key, not the partition key**. *(03 §5.1, D5)*
- [ ] **Every payload schema lives in `packages/canonical-schemas` and is registered in the schema registry.** The service cannot publish an unregistered payload. *(03 §5.5)*
- [ ] **AsyncAPI document generated and committed**, with no drift. *(03 §5.5)*
- [ ] `src/<pkg>/events/catalog.py` `PUBLISHES`/`CONSUMES` **equal** `helm/values.yaml` `events.publishes`/`events.consumes` **equal** document 03 §6's catalog rows for this slug. *(C3–C5, C37, C38)*
- [ ] **No wildcard subscriptions.** Every consumed event type is named explicitly. *(C38)*
- [ ] Events carry **facts from this service's own domain only** — no instructions, no other domain's facts. *(03 principle 3, C32)*
- [ ] **Large results are referenced, not inlined.** No event carries a result set that could exceed the broker message limit. *(D27)*
- [ ] `replay: true` events are handled idempotently and raise **no** operator-visible alert. *(03 §5.3, D30)*

### 8.3 Outbox, inbox, and read models

*Mechanism owned by [`docs/build/11-outbox-sync-library.md`](11-outbox-sync-library.md); the obligations are asserted here.*

- [ ] **Transactional outbox wired via `packages/py-sync`** — state change and event in one database transaction. No exception, including for a sub-application with no current edge profile. *(03 §5.2, obligation 11)*
- [ ] **Inbox records receipt and applies state in one transaction.** Where impossible, only rows with `processed_at` **set** suppress redelivery. **Recording receipt before processing is prohibited.** *(03 §5.2, D2)*
- [ ] Every consumer is **idempotent on `event_id`**. *(03 §5.2)*
- [ ] **Antecedent rule implemented**: an event whose `baseline_epoch` is ahead of the local configuration read model is **blocked** until the antecedent configuration event is applied. *(03 §5.4, D3/D4)*
- [ ] **Ordering and deduplication use `(producer, monotonic_seq)` or the HLC — never `source_time`.** *(03 §5.4, D29)*
- [ ] **Durations, timeouts, retry backoff, and lease expiry use a monotonic clock.** No wall-clock arithmetic anywhere in the service. *(03 §5.4, D29)*
- [ ] Read models are rebuilt from **`changed_since` reads**, never from the event bus. A documented, tested rebuild procedure exists. *(03 §5.1, D5)*
- [ ] **Read-model lag exposed on `/readyz` and `/metrics`**, and any freshness-dependent computation **declares a staleness bound and refuses to run outside it**, incrementing `fathom_staleness_refusals_total`. *(03 §5.2, obligation 14, D6)*
- [ ] Conflict policy declared per aggregate, or the 03 §11 default (**enterprise-authoritative, not edge-writable**) explicitly accepted in the README. *(obligation 16, C20)*

### 8.4 Data and storage

- [ ] **Exactly one logical database, and the service reaches no other.** Two storage engines, where genuinely required, are separate schemas of one owned cluster or separately justified. *(obligation 13, D33)*
- [ ] Alembic migrations complete, forward-only, and executed as a `pre-upgrade,pre-install` Helm hook with `backoffLimit: 0`. *(01 §11)*
- [ ] The `migrations` readiness check passes: image Alembic head equals database head.
- [ ] **Provenance recorded for every derived value published** — inputs, versions, computation reference — sufficient to trace any operator-visible figure to its sources. *(obligation 9)*
- [ ] **Classification labels on every response and event, with `inherited_from` set as the union of inputs on every derived value.** *(03 §7.3, obligation 4, D13)*
- [ ] A **declared purge path** for every store this service owns, stating whether it is legally immutable or operationally append-only. *(03 §13, D15)*

### 8.5 Conformance and tests

- [ ] **`packages/contracts/conformance/<slug>/` exists and the service's `tests/conformance/` collects it unmodified.** No shared test skipped, xfailed, or edited. *(03 §10, obligation 10)*
- [ ] Contract tests cover every `x-substitution: required` operation, including errors, pagination, idempotency, and concurrency. *(03 §10)*
- [ ] **Event tests** assert specified actions produce specified events with correct envelopes, keys, and within-partition ordering. *(03 §10)*
- [ ] **Fault-injection tests** interrupt mid-operation and assert no state change without its event. *(03 §10, obligation 2)*
- [ ] **Consumer-driven tests contributed** by this service into every producer's suite for every event it consumes. *(03 §10)*
- [ ] **Manifest tests** pass for every manifest in `packages/agent-tooling/manifests/<slug>/`. *(03 §8.4)*
- [ ] A synthetic reference dataset gives deterministic runs. *(03 §10; content per the synthetic-data document)*
- [ ] `pytest tests/unit tests/integration tests/contract tests/conformance` green. Coverage floor met (§7.4).

### 8.6 Deployment and boundary

- [ ] **`python tools/check_event_catalog.py` exits 0.** *(README, tranche 3)*
- [ ] `helm lint` clean; `helm template | kubeconform --strict` clean; `helm unittest` green.
- [ ] **NetworkPolicy allows only declared dependencies.** The helm-unittest assertion shows the rendered egress peer set **equals** `values.networkPolicy.egress` — no extra peer, no wildcard, no `enabled: false` in any environment. Every peer maps to a sanctioned edge in §4.4.2. *(01 §11, principle 1)*
- [ ] **No direct database access from outside the owning service.** No other service, Domino Job, notebook, or tool holds this database's credentials; the only inbound path is the REST API. *(01 principle 1, 03 §4, D10/C7)*
- [ ] Dockerfile is multi-stage; runtime stage is **non-root (UID 65532)** with `readOnlyRootFilesystem: true` and `capabilities: drop: [ALL]`.
- [ ] **No package or source installation at container start.** No `apt-get`, `pip install`, `curl`, or `wget` in the runtime stage. All dependencies baked at build time. *(01 §12, 01 principle 5, D26)*
- [ ] Base images and build tools pinned **by digest**. Image promoted by digest, never rebuilt per environment. *(01 §11)*
- [ ] `/healthz`, `/readyz` (with database, migrations, broker, read-model lag, and outbox checks), and `/metrics` all present and behaving per §5.6. *(03 §4)*
- [ ] `.env.example` complete and reconciled with `Settings`; no secret value in any chart or repository file. *(01 §11)*
- [ ] Structured JSON logging with `correlation_id` on **every** line. *(obligation 15)*
- [ ] Argo CD Application committed under `deploy/argocd/`, with `dev` auto-sync and staging/production manual sync.

### 8.7 Documentation and governance

- [ ] `README.md` states purpose, owned aggregates, published and consumed events, conflict policy per aggregate, staleness bound, and sanctioned NetworkPolicy peers.
- [ ] Every deviation from this document carries an ADR under `docs/adr/`.
- [ ] Every decision this document marked **[OPEN]** and the service had to resolve locally is recorded in the README as a local resolution, and raised for a program decision.
- [ ] **No **[ESTABLISHED HERE]** convention has been silently varied.** Varying one breaks a sibling service, not just this one.

---

## 9. Explicit DO-NOT list

Each item carries the finding that makes it a defect rather than a preference. A reviewer may cite the ID and stop reading.

### 9.1 Boundaries and data ownership

1. **Do not write to any datastore you do not own, and do not let any Domino Job write to one.** Scoring results arrive through PdM's **bulk ingest API** with a workload identity. A Domino Job is an API client, never a database client. Direct access bypasses invalidation, calibration, provenance, and the outbox, and violates the one-database-per-service invariant NetworkPolicy enforces. *(**D10 / C7**; 01 §3 correction 2, 01 §7, 03 §4 bulk writes)*
2. **Do not call another sub-application synchronously on a compute path.** Maintain a local read model fed by events. Synchronous reads exist only for user-facing composition, and that composition happens in the gateway. *(03 principle 2)*
3. **Do not own two databases.** Where two storage engines are genuinely needed, they are separate schemas of one owned cluster or separately justified in Phase 3. *(**D33**; obligation 13)*
4. **Do not re-mint canonical identity.** No local surrogate for asset, system, position, installed item, or part is ever exposed. *(03 principle 4)*
5. **Do not use `eic`, `hull_or_tail`, `eswbs`, `position_code`, or `nsn` as a join key.** EIC in particular is a class code of variable specificity, not an instance identifier. *(03 §3.3; **C2**, **C10**)*
6. **Do not conflate `position_id` with `installed_item_id`.** That is the inherited-degradation defect the whole model exists to prevent. *(03 §3.3; **C10**, **D9**)*

### 9.2 Time, ordering, and the event bus

7. **Do not let a wall clock arbitrate anything.** Not merges, not conflict resolution, not last-writer-wins, not timeouts, not retry backoff, not lease expiry. The Ubuntu 22.04 STIG rule **V-260520** mandates unlimited backward clock steps whenever offset exceeds one second — which fires precisely when a disconnected node reconnects and drains its outbox. Order on `(producer, monotonic_seq)` or the HLC; measure durations with a monotonic clock. *(**D29**; 03 §5.4)*
8. **Do not record inbox receipt before processing.** Only rows with `processed_at` set suppress redelivery. Applied to `configuration.baseline_changed`, the wrong order silently prevents prediction invalidation — the outcome document 04 identifies as most likely to destroy operator trust, introduced by the inbox rule itself. *(**D2**; 03 §5.2)*
9. **Do not treat the event bus as a rebuild source.** Retention is bounded deliberately. Rebuild uses `changed_since` reads. *(**D5**; 03 §5.1)*
10. **Do not set the compaction key equal to the partition key.** Compacting the prediction topic on `asset_id` collapses a hull's entire prediction history to one record. *(**D5**; 03 §5.1)*
11. **Do not replay history through the live event bus.** Replay fires live notifications, work candidates, and requisitions. Backfill uses bulk writes with `X-Backfill: true`. *(**D30**; 03 §5.3)*
12. **Do not depend on cross-topic or cross-asset ordering** except through the antecedent rule; and **do not accept an event whose `baseline_epoch` is ahead of your configuration read model** — block it. *(**D3**, **D4**; 03 §5.4)*
13. **Do not inline large result sets in events.** Publish a reference to the run artifact. *(**D27**; 03 §6)*
14. **Do not use wildcard subscriptions.** They cannot be conformance-tested and auto-subscribe to future events. *(**C38**)*
15. **Do not make an agent a direct topic consumer.** Agents obtain state through tools. Where a downstream capability is an agent's, the named consumer is the platform component that bridges to it. *(**C19**; 03 §6)*

### 9.3 Agents, proposals, and untrusted content

16. **Do not gate agent eligibility on HTTP method.** Eligibility follows the declared `x-side-effects` class; a method check wrongly excludes the compute-only `POST` operations three agents require. *(**C1 / D11**; 03 §4.1, §8.1)*
17. **Do not let an agent write domain state.** Every state-changing agent output is a `Proposal`. *(01 principle 7, 03 §7.2)*
18. **Do not adjudicate without a claim and `If-Match`.** The queue is eventually consistent; without a lease two planners approve the same proposal and two work orders result. **Do not validate only at creation** — re-validate against current configuration at adjudication and reject on a superseded `baseline_epoch` or an elapsed `valid_until`. **Do not use one authority for every blast radius** — dual control is mandatory at class and fleet scope and for any kind with external legal effect. *(**D16**; 03 §7.2)*
19. **Do not treat retrieved or user-supplied content as instruction.** Enforce domain policy in the receiving operation — APL authorization, bounded interval deltas, baseline presence — regardless of what an agent proposed or why. A non-empty `evidence` list is necessary, never sufficient. *(**D14**; 03 §9)*
20. **Do not render `contributing_factors` in causal language,** and do not display factors below the stability threshold. A causal statement must cite an adjudicated Failure Intelligence hypothesis. *(**D23**; 03 §7.1)*
21. **Do not branch on `tier`.** Branch on `reference_class`. Do not emit a per-item `rul` where the reference class is not item-conditional; publish a population hazard rate. Do not fold cold-start depth into `confidence`. *(**D7**, **D19**; 03 §7.1)*

### 9.4 Classification and remediation

22. **Do not post-filter for classification.** Filtering happens inside the query; removing results afterward leaks the existence of records. *(**D13**; 03 §7.3)*
23. **Do not publish a derived value without the union of its inputs' labels** in `inherited_from`. Aggregation is itself a classification event. *(**D13**; 03 §7.3)*
24. **Do not create a store with no purge path.** Append-only is an integrity property, not a licence for unrecoverable data. *(**D15**; 03 §13)*

### 9.5 Platform and build

25. **Do not install anything at container start.** No package installation, no source retrieval, no dependency resolution. Domino's own engineering documented this as categorically incompatible with air gap, with no workaround. *(01 §12, 01 principle 5; **D26**)*
26. **Do not call a public-internet service at runtime.** No external DNS, telemetry, or licence callouts. This includes an `https://` problem-detail `type` that anyone might dereference. *(01 principle 5, 01 §12)*
27. **Do not assume a Domino capability document 02 rules out** — Extensions outside Domino Cloud, platform-side drift detection, platform-side prompt or manifest governance, air-gapped agent hosting, or agent hosting beyond the per-project caps. Each has a named fallback in 01 §9; use it. *(**D26**; 01 §9)*
28. **Do not deploy into Domino's namespaces**, and do not treat a Domino-deployed Istio as the application mesh. *(01 §11, 02 §4.6)*
29. **Do not put a program implementation standard into the conformance suite.** The outbox, the inbox, per-log-line correlation IDs, and one-database-per-service are unobservable from outside a black box; a suite asserting them is one no partner can pass. Assert the observable property instead — for the outbox, *no state change without its event*, by fault injection. *(**D24**; 03 §10, §15)*
30. **Do not disable `networkPolicy.enabled`, add a wildcard peer, or add a peer not in §4.4.2** without an ADR and a change to this document. The policy is the mechanism converting principle 1 from convention into an invariant. *(01 §11, principle 1)*
31. **Do not invent quantities.** Fleet size, item counts, telemetry rates, prediction volumes, proposal rates, and latency budgets come from document 06 §7. Inventing a number reintroduces the gap finding **D37** exists to close. *(**D37**; 06 §7)*
32. **Do not add Navy schema detail here or in a shared package** on the basis of general knowledge. 3-M code sets, COSAL structure, FLIS, MILSTRIP, and identifier formats come from document 07, and the code sets themselves need re-baselining against the current NAVSEAINST 4790.8 revision. *(07; README standards posture)*

---

## 10. Open questions

Listed so they are resolved once, centrally, rather than nine times locally. A service that must proceed before one is resolved records its local resolution in its README (§8.7) and does not treat it as settled.

| # | Question | Impact if unresolved | Interim position |
|---|---|---|---|
| 1 | **CI provider** — GitHub Actions, GitLab CI, or something else | Low, by construction: all logic is in `make` targets, so the invocation layer is thin and replaceable | GitHub Actions with self-hosted runners (§6.1) |
| 2 | **Private package index and container registry** — which product, and the mirroring procedure for air-gapped builds | Blocks the first real Docker build. Every image pin depends on it | Assume an OCI registry plus a PEP 503 index; `PIP_INDEX_URL` is a build arg |
| 3 | **Domino → program network path** for batch scoring writes | Two viable shapes with different NetworkPolicy consequences | Route through `gateway`; one declared cross-namespace ingress rule (§4.4.2) |
| 4 | **Schema registry serialization** — JSON Schema versus Avro | Changes payload size and the `canonical-schemas` build | JSON Schema (§2.2) |
| 5 | **Idempotency retention for edge-sync-reachable operations** | A disconnected hull's retry window is weeks, not 24 hours | Set by document 11 alongside the divergence budget [03 §11] |
| 6 | **UI router, state, and data-fetching libraries** | Blocks `apps/web` beyond a skeleton | Deferred to the look-and-feel wave. Toolchain only (§2.6) |
| 7 | **`deploy/terraform` ownership** — no build-framework document covers it | Cluster-adjacent infrastructure has no design owner | Raise for assignment |
| 8 | **Load and performance testing** — tool, thresholds, where it runs | Document 06 §7 states a p95 budget (1.5 s fleet/asset views, 4 s explanation decomposition) that nothing currently verifies | Raise for assignment; do not invent thresholds |

---

## 11. Corrections to the source architecture documents

Found while reconciling. Each is a **defect in the cited document**, not a decision of this one. Items 1 and 2 are corrected in this document's §3.1 and must be corrected upstream.

| # | Document | Defect | Correction | Status |
|---|---|---|---|---|
| 1 | **01 §11 monorepo layout** | Lists `services/{fleet-status,**asset-registry**,telemetry,pdm,…}`. The canonical slug for Asset & Configuration Registry is **`registry`** [03 §3.1], which is also what `tools/check_event_catalog.py` enforces and what `packages/contracts/conformance/<slug>/` and `packages/agent-tooling/manifests/<slug>/` require | Directory is **`services/registry`** | **Applied in §3.1.** 01 §11 needs the edit. This is exactly the drift finding **C27** describes ("the monorepo uses different slugs"); C27's disposition is FIX but the fix did not reach 01 §11 in rev 5 |
| 2 | **01 §11 monorepo layout** | Omits `tools/`, which exists in the repository and holds `check_event_catalog.py` — a component the README makes a standing gate. Also omits `docs/build/` | Add `tools/` and extend `docs/{architecture,adr}` to `docs/{architecture,build,adr}` | **Applied in §3.1.** 01 §11 needs the edit |
| 3 | **05 §3.4 "Verified sound"** | Asserts "all package paths in 03 match the 01 §11 monorepo layout." The `packages/*` paths do match; the **service** paths do not, per item 1. The assertion is too broad and masks C27 | Narrow the claim to `packages/*` | Not applied; flagged |
| 4 | **04 §11 Sync Gateway** | Says "**Inert in the demonstration**." Document 01 §5 explicitly corrects this: "The outbox relay is never inert. Document 03 §5.2 makes the outbox universal, so a component that drained it only at the edge would prevent any event reaching the broker." This is finding **C21**, fixed in 01 rev 5 but not in 04 | Only the **edge reconciliation coordinator** is inert; the outbox/inbox relay library is always active | Not applied; flagged. **Implementers must follow 01 §5, not 04 §11** |
| 5 | **04 §11 Sync Gateway** | Cites "document 03 §9" for the edge seam. 03 §9 is *Untrusted content*; edge reconciliation is **03 §11** | Read §11 | Not applied; flagged |
| 6 | **04 §11** | Contains **two** `### Identity & Authorization` headings (lines 711 and 730) with different content, and delivers three "substantial Phase 3 design required" markers against a promise of two — finding **C33**'s neighbourhood | Merge into one section | Not applied; flagged |
| 7 | **04 §12 / §13** | Cite "document 03 §10" for the tool manifest model, "§8" for the substitution protocol, and "§9" for edge reconciliation. Actual: manifests **§8**, substitution **§10**, edge **§11**. Document **01 §8.0** carries the same inversion ("specified in document 03 §10" for the manifest model) | Manifests §8; substitution §10; edge §11 | Not applied; flagged. Affects any agent following cross-references literally |
| 8 | **03 internal cross-references** | Several point at the wrong section: §4 "Agent authority — Per §9.2" (→ **§8.3**); §4.1 "agent eligibility (§9.1)" (→ **§8.1**); §4 concurrency "proposal adjudication (§8.2)" (→ **§7.2**); §7.2 "authority to adjudicate (§9.3)" (→ **§8.3**); principle 6 "recorded separately (§11)" (→ **§15**); principle 7 "provenance machinery that §11 requires" (→ **§15**); principle 8 "(§13)" (→ **§9**); principle 9 "(§14)" (→ **§13**) | As shown | Not applied; flagged. Document 03 is binding, so its cross-references are followed literally by implementers |
| 9 | **05 §2 findings tables** | Cite **D10** and **D11** as duplicated by C7 and C1, but neither D10 nor D11 has a row in §2.1–§2.7. Worse, **document 02 §6 uses D10 and D11 for entirely different things** (Domino application hosting fidelity; a consumer licensing tier), so the same identifiers mean two things across documents | Add the missing D10/D11 rows to 05 §2, or renumber 02 §6's platform requests to a distinct prefix (e.g. `PR-10`) | Not applied; flagged. **This document cites "D10/C7" and "C1/D11" as document 03 does, meaning the review findings, not the platform requests** |
| 10 | **03 §11 conflict-policy table** | The table header is emitted, then a bolded clock-discipline paragraph is interleaved **between** the header and the rows, so the table does not render as one table | Move the paragraph above the header | Cosmetic; flagged because the table is contractual |
| 11 | **03 §7.3** | Contains an empty fenced code block after `ClassificationLabel` | Remove | Cosmetic; flagged |

---

## 12. Quick reference for an implementing agent

Read in this order before writing code for a service:

1. **This document** §3 (where things go), §4 (the skeleton), §5 (the API rules), §8 (what done means), §9 (what not to do).
2. **Document 03** §3 (identity), §4 (conventions), §5 (events), §6 (your slug's catalog rows), §7 (shared payloads), §15 (obligations).
3. **Document 04** — the section for your sub-application.
4. **`docs/build/11-outbox-sync-library.md`** before writing anything in `events/`.
5. The **shared-packages** document before writing anything you suspect belongs in `packages/py-common`. If §5 names it, it is already shared: do not reimplement it.
6. **Document 06 §7** for any quantity.
7. **Document 07** for any Navy schema detail.

Then: `make scaffold SLUG=<slug>` produces §4.2's tree, and §8 is the checklist you copy into the README and tick.
