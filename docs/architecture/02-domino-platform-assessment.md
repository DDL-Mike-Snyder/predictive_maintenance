# Domino Platform Assessment

| | |
|---|---|
| **Purpose** | Establish, from primary sources, which components of the FATHOM architecture Domino can host today; document the specific basis for each platform-boundary decision; and specify the Domino capability changes that would permit Domino to serve as the foundation for the entire program |
| **Companion document** | [01 — Phase 1 System Architecture](01-system-architecture.md) |
| **Research date** | 4 August 2026 |
| **Domino versions assessed** | Self-managed 6.2.3 GA (June 2026), with 6.3.0 release material reviewed where it bears on findings; Domino Cloud Release 90 (July 2026) |
| **Classification** | **Internal only.** Cites unreleased roadmap material, unsigned product requirements documents, and candid internal engineering discussion. Not for external or customer distribution |

---

## 1. Purpose and method

The Phase 1 architecture allocates components between a Domino-hosted Intelligence Plane and a Helm-deployed Sustainment Plane. That allocation determines the program's engineering cost, its accreditation surface, and the credibility of its platform narrative. It should therefore rest on verified capability rather than assumption.

Four independent research passes were conducted against distinct source classes:

| Source class | Coverage |
|---|---|
| Public product documentation | Complete documentation sitemap (5,897 URLs) for versions 6.2 and Cloud; release notes 2023 through July 2026; product and press pages |
| Internal design documentation (Google Drive) | Approximately 30 queries; 25 documents read in full, including product requirements documents, technical design specifications, roadmap material, and public-sector submissions |
| Internal engineering discussion (Slack) | Approximately 40 searches across engineering, product, professional-services, field-engineering, and public-sector channels |
| Internal issue tracking and knowledge base (Confluence, Jira) | Epics, tickets, runbooks, and test plans relevant to Apps, Endpoints, governance, and Nexus |

Findings are classified throughout as generally available, preview, in design, discussed only, or not found. Where documentation is silent, that silence is reported as such rather than resolved by inference.

---

## 2. Bottom line

**Domino is the correct platform for the Intelligence Plane and is not, in its current form, a platform for the Sustainment Plane.** The distinction is not a matter of maturity or preference; it is a matter of what the product is documented and designed to host.

Domino's own product documentation states the position directly:

> "Apps are not intended for persistent workflows or large-scale back-end processing."
> — *Apps in Domino*, docs.dominodatalab.com, versions 6.2 and Cloud

The same documentation directs application persistence to external systems:

> "**Databases or External Data Sources**: Use standard client libraries to write to: SQL or NoSQL databases / Cloud object storage / Enterprise data warehouses (ensure your runtime environment has credentials and network access)"
> — *Persist data from Apps*

Internal platform-architecture documentation is more specific still:

> "As of today, Domino Apps are best suited to constrained stateless web applications with minimal dependencies — unlike a traditional web application that may have additional service dependencies like databases."
> "Apps should generally not be allowed to communicate with core Domino platform services within the cluster in any way."
> — *Domino Apps*, internal platform-architecture document

Against that, Domino's strengths in the Intelligence Plane are substantial and, for a Navy program, unusually well matched. The affirmative case appears in §3, and it is the reason the platform decision is sound notwithstanding the boundary.

The architecture therefore places both planes in the same Kubernetes cluster, in separate namespaces, on separate node pools. The program runs on Domino infrastructure in its entirety while confining Domino-managed workloads to those Domino is built to manage.

---

## 3. The affirmative case for Domino

The boundary analysis in §4 is extensive, and reading it in isolation would misrepresent the assessment. The capabilities below are genuinely differentiating for this program and are the basis for selecting Domino as the platform substrate.

### 3.1 Defense accreditation posture

Domino's April 2026 public-sector capability submission, an approved customer-facing document, records:

| Credential | Status |
|---|---|
| Facility clearance | Active Top Secret |
| IL5 | In production — Navy Project AMMO / Project Overmatch, AWS GovCloud |
| IL6 | Two operational Secret environments |
| IL7 | Accreditation in progress |
| Air-gapped Top Secret | Operational at a national intelligence agency, on premises |
| Compliance | ISO 27001:2022, SOC 2 Type II, FIPS, HIPAA, NIST 800-53 alignment |
| Foreign ownership | US-headquartered, no foreign ownership; US-only infrastructure for defense workloads |
| Contract vehicles | Navy Project Overmatch Production OTA, DIU Prototype OTA, CDAO Tradewinds OTA, NASA SEWP, GSA Schedule |

Few analytics platforms can present this posture. For a program targeting IL5 with a plausible path to IL6 and afloat deployment, it is the single strongest argument for the platform.

### 3.2 Navy precedent, and its architectural shape

The Navy AMMO engagement (prototype HQ0845-22-9-0050, mine countermeasures) delivered a full machine-learning pipeline deployed to AWS IL2 and IL5 and passed Government Acceptance Testing for functionality, security, and automation. Reported outcomes: model deployment reduced from six months to six days; retraining reduced from twelve months to two weeks.

The architectural shape of that engagement is directly instructive. Domino functioned as the factory integrating four other commercial technologies across three contracted teams — that is, as the model factory within a larger system rather than as the entire system. The FATHOM two-plane architecture reproduces a pattern that has already been accredited and fielded for this customer.

### 3.3 Self-hosted, air-gappable language model serving

Generally available since January 2026: registration from Hugging Face or from MLflow-logged runs, deployment on a pre-built vLLM environment, OpenAI-compatible APIs, agent-framework tool-calling flags, and deployment within the customer VPC or on premises. For a program that must ultimately operate in an air-gapped enclave, governed in-enclave inference with centralized key custody and audit retention is a requirement that few platforms satisfy.

### 3.4 Agentic development lifecycle

Announced in the Winter Release 2026 (26 February 2026) and generally available in Domino Cloud. The capability is precisely characterized as tracing, evaluation, versioning, and governed deployment rather than as an agent runtime or orchestration framework:

> "Domino treats agentic systems as first-class objects in the ML lifecycle. The core abstraction is the trace."
> — *Agentic AI overview*

Concretely: a one-line `@add_tracing` decorator built on MLflow tracing, framework-agnostic across LangChain, Pydantic AI, OpenAI Agents SDK, LlamaIndex, and custom code; span-level capture of every model call, tool invocation, and decision point with token, latency, and cost accounting; heuristic and model-as-judge evaluation; trace diffs across versions; scheduled production evaluation; agent versions surfaced as first-class objects in Experiment Manager; and rollback to prior agent versions.

This maps almost exactly onto §8.8 of the architecture. The program's requirement to measure proposal precision against human adjudication outcomes, and to gate agent promotion on it, is directly serviceable.

### 3.5 Reproducibility and governance of the model estate

Governance bundles, policies, evidence, approval stages, and enforcement gates are generally available, with gates currently able to act on application and endpoint creation. Environments provide reproducible, vendorable images. Registry lineage connects production artifacts to source experiments. For a program whose predictions will inform maintenance decisions on operational platforms, an auditable path from a fielded prediction back to the training run that produced it is not a convenience.

### 3.6 Distribution and infrastructure flexibility

Validated on EKS, AKS, GKE, and OpenShift. OpenShift support materially eases on-premises and air-gapped Navy enclaves. Nexus permits workload placement across data planes for data-locality and residency requirements within connected environments.

---

## 4. Capability findings

### 4.1 Domino Apps

| Capability | Status | Detail and source |
|---|---|---|
| Supported frameworks | GA | Streamlit, Dash, Shiny, Flask documented. FastAPI appears in official agent-deployment code examples and is de facto supported |
| Compiled React SPA | Works with friction; not a documented app type | Never mentioned in product documentation. An internal blueprint repository demonstrates React deployment with continuous integration. The working internal consensus is a Vite-built React front end with a FastAPI backend |
| SPA base path | Constraint | The URL prefix is supplied at runtime through `DOMINO_RUN_HOST_PATH`, whereas standard build tooling bakes the base path at build time. Documentation warns that without correct base-path configuration "your app may fail to load resources or generate broken links." A customer ticket in February 2026 reported the proxy "not forwarding sub-path asset requests (`/assets/*.js`, `/assets/*.css`), preventing modern SPA/SSR apps from loading correctly." The thread received no product resolution |
| Server-side rendering (Next.js) | Not supported; question unanswered | Same customer ticket |
| Multi-container | Not supported | One image, one launch file, one pod. Internal engineering confirms the workaround is a single container running multiple processes behind a local nginx, characterized internally as "fairly gross" and "not super elegant" |
| Service-to-service | No first-class mechanism | Internal engineering: application-to-application communication has "no first-class way to do that"; application identity is recorded as a gap. HTTP with bearer tokens only; gRPC between applications is not configurable. Kubernetes service-link environment variables were disabled in the compute namespace in Cloud Release 86, removing service discovery |
| Programmatic invocation | **Blocking gap** | Internal analysis: "The options for an App-hosted endpoint are: PUBLIC (fully open), or Domino session auth (impractical for programmatic callers). There is no token-based middle ground in the current App auth model." Remediation estimated as "full overhaul." Personal access tokens shipped in 6.3.0; their applicability to application invocation is not documented |
| Identity propagation | GA, and strong | Three tiers: basic username header, enhanced JWT, and extended propagation permitting an application to act with the user's full permissions subject to explicit user consent, default eight hours and up to thirty days. Default execution identity is the publisher's, not the viewer's |
| Anonymous access | Being removed | Previously the only Domino asset intentionally reachable unauthenticated. Internal ratification in June 2026 to remove anonymous users platform-wide; an applications authorization overhaul is targeted for 6.4 |
| Autoscaling | GA since 6.2 | Kubernetes HPA v2, minimum one pod, no scale-to-zero, scale-up in approximately 20 seconds, optional session affinity. Practically, internal observation is that "most of the time people are only using a single pod app" |
| Concurrency safety | Customer responsibility | "Domino does not serialize or isolate access to shared resources across App users. You are responsible for implementing any necessary safeguards in your App code." Autoscaled applications share temporary storage |
| Per-framework concurrency | Documented limits | Flask and Dash run single-threaded by default, with Flask's own guidance against serving more than ten concurrent users unmodified. "Shiny Apps typically cannot scale to more than a handful of concurrent users" |
| Request timeout | 300s default | nginx connect and read timeouts default to 300s, admin-tunable. No per-application override |
| Custom domains | Not supported | Custom URL *paths* only. Applications are served from a single deployment-wide subdomain and iframed. Multiple open requests exist |
| Iframe rendering | Default | Iframe permissions were extended for microphone and clipboard in May 2026. An iframeless view exists for applications supporting deep linking. External content is subject to administrator-managed content-security-policy allowlisting |
| Idle shutdown | Documentation contradictory; effectively absent | Product documentation states "Apps run until you explicitly stop them." Marketing claims auto-suspend. No feature, configuration key, or timeout value appears in documentation or in any release note. A scale-to-zero product requirements document dated 24 July 2026 remains unsigned with technical design marked TODO. Customers have built their own idle detectors |
| Availability | Weak for always-on use | Domino Cloud service-level agreement is 99%. Platform maintenance restarts application pods. Node consolidation evicts them; one customer defect reported "most Apps get shutdown overnight" |
| Output persistence | Not supported | "File changes inside an App container are not saved to the project repository" |
| Per-project caps | GA | Ten applications per project and four active application runs per project, by default |
| **Extensions** | GA, **Domino Cloud only** | Surfaces an application natively inside the Domino interface at one of five mount points, passing page context. Admin-created only. Requires extended identity propagation on the backing application — "the only hard requirement." Absent from the self-managed 6.2 documentation tree, which matters because the program's production target is self-managed OpenShift and air-gapped enclaves. **Consequence for the architecture:** Extensions are the preferred practitioner-surface mechanism where available, and Domino Apps are the portable fallback that document 04 specifies |

### 4.2 Agents

Agent hosting is architecturally identical to application hosting. The determinative sentence:

> "Agents use the same hosting infrastructure as Domino Apps. Deploying as an agent mainly affects the dashboard and how traces and evaluations are associated."
> — *Deploy agentic systems*

Internal governance documentation concurs, treating agents and extensions as inheriting application governance "by nature of being apps under the hood."

Consequently every constraint in §4.1 applies to agents without modification, including the programmatic-invocation gap. This is the origin of the dependency recorded in architecture §8.7.

**Model Context Protocol is not a Domino capability.** Zero pages in the documentation sitemap; zero occurrences across three years of release notes; absent from the Winter Release 2026 announcement and the agentic product page. A community MCP server exposing Domino's own APIs to external coding assistants exists on GitHub with two stars and no support statement. Internal evaluation of an MCP-capable third-party gateway concluded its "real strengths (MCP, A2A, LLM routing) are not needed for the internal service routing scope" and deferred it. A single demonstration artifact integrates a Domino-hosted agent with AWS Bedrock AgentCore.

The program should therefore expect to host MCP tool servers itself, without platform-provided registry, discovery, or governance for them.

### 4.3 Endpoints

| Property | State |
|---|---|
| Deployment | Always-on, replica-based, fixed integer replica count |
| Autoscaling | **None.** An investigation ticket has remained open since August 2022, most recently updated March 2026. The same HPA mechanism shipped for Apps in 6.2.0 |
| Scale-to-zero | None; internally assessed as high-effort with "no existing pattern in Domino for this" |
| Concurrency | Serial by default. A partial fix shipped in 4.6 permitting worker and thread configuration; internal benchmarking shows one worker with two threads materially flattens latency. The setting is **deployment-global**, not per-endpoint; a per-endpoint override was formally declined |
| Payload ceiling | 10 MB, fixed. Two requests to raise it were declined and closed as will-not-do |
| Request timeout | Per-endpoint override exists, with an effective ceiling near 560s and a requirement to adjust health-check parameters in tandem. Internal engineering recommended documenting a conservative 60s maximum |
| Timeout cancellation | **A timed-out request is not cancelled** and continues to occupy its worker. Closed as will-not-do. Combined with a default single worker, one slow request stalls a replica for its full duration |
| Traffic splitting | Supported — concurrent versions with canary and A/B routing. A capability Apps lack |
| Authentication | Static per-model tokens with no expiry, rotation policy, or per-caller audit trail. Remediation assessed as "full overhaul"; an identity-based invoke-authentication technical design was dated 3 August 2026 |
| Runtimes | Python uWSGI harness, R, or MLServer. Intentional, and precludes custom web servers or protocols |
| Data access | No Datasets, no external volume mounts, no imported repositories, default branch only |
| Async endpoints | At risk of sunset — dependent on Seldon, with an unresolved licensing issue |
| Serving SLO | **None exists.** Service-level objectives cover model build and deploy, not serving latency or availability |
| Remote data planes | Endpoints supported; asynchronous requests and integrated model monitoring are not. Generative-AI and LLM endpoints on remote data planes were postponed from 6.2, with the final solution dependent on Kubernetes features not yet available |

These properties are compatible with governed, moderate-volume, interactive inference. They are incompatible with a telemetry ingest path or with serving the request path of an operational interface — hence the batch-first correction in architecture §3.

### 4.4 Governance

Shipped: bundles, policies, evidence notebooks, approval stages, and gates enforced as infrastructure proxies, with current gate actions covering application and endpoint creation, parameterized by hardware tier or data plane.

Targeted for 6.3.0 per an unsigned product requirements document, with status unconfirmed against the 6.3 release retrospective: a governance tab on application, agent, and extension detail views; a unified `Deploy` gate replacing per-asset gates. The document carries an explicit fallback to the current bundle model should the transition prove too large for the release.

Four limitations are recorded in Domino's own governance vision refresh and are material to a Navy authorization-to-operate narrative:

> "gates must be expressed in terms of infrastructure proxies (hardware tiers, data planes) rather than the lifecycle concept the admin actually cares about (e.g., 'block promotion to production until validated')"
> "gates are not configurable from the UI — they live as YAML inside a specific policy"
> "there is no way to programmatically compute whether a gate should be open or closed… gate state is solely a function of static approval status"
> "gates only enforce on already-governed assets — nothing in the platform prevents a user from building and shipping a model, app, or agent without ever attaching a policy in the first place, leaving governance fundamentally opt-in at the asset level"

The final item is the most consequential. A governance regime that can be bypassed by declining to attach a policy will not, without compensating controls, satisfy an accreditor. Governance of prompts as first-class assets was not found.

### 4.5 Nexus, and the DDIL finding

This is the most consequential finding in the assessment and the basis for redesigning the afloat off-ramp.

**A Nexus data plane requires continuous control-plane connectivity.** From Domino's control-plane security guidance:

> "Domino Nexus control planes host several important services which must be accessible from data plane clusters:
> **Domino API** — … This endpoint should be routable from data plane clusters.
> **Vault** — Data plane clusters use Hashicorp's Vault to authenticate with the control plane… over HTTPS on port 8200.
> **RabbitMQ** — **The primary communication channel between the Domino control plane and the data plane is based on RPC over RabbitMQ.** Additionally, data planes publish execution state back to the control plane over RabbitMQ… on ports 5672 and 5552.
> **Docker Registry** — … data plane Kubelets must be able to access the registry over HTTPS on port 443."

Remote procedure call over persistent messaging is a continuous-connection pattern. A data plane cannot dispatch, execute, or report workloads without it.

**Loss of connectivity is a fault, not a mode.** From the data-plane monitoring documentation:

> "Data planes are marked Healthy if they are available for use. If a data plane indicates Error, Disconnected, or Degraded, there may be an issue with communication between the data plane services and the control plane. Please reach out to Domino for assistance in troubleshooting."

No documentation of disconnected operation, offline data planes, store-and-forward behavior, lease-based authorization, or conflict-resolution semantics exists in the public documentation, in internal design documentation, or in internal engineering discussion. Searches for DDIL and for disconnected operation returned nothing in the internal corpus.

Remote data-plane feature parity is additionally incomplete: Starburst-backed data sources, Datasets, asynchronous endpoint requests, integrated model monitoring, generative-AI model caching, and generative-AI endpoints are each unsupported or postponed on remote planes, and shared-storage provisioning differs mechanism by mechanism.

What Domino does support for edge operation is **model artifact export**, with documented targets including SageMaker and NVIDIA Fleet Command, and a public-sector claim of demonstrated compression — quantization, pruning, distillation — for size, weight, and power-constrained hardware on Navy unmanned vehicles and Army ground vehicles. This is the supported pattern and it is what architecture §12 now specifies.

### 4.6 Kubernetes coexistence

| Question | Finding |
|---|---|
| What Domino owns | Namespaces `domino-platform`, `domino-compute`, `domino-system`, and an Istio namespace. The installer "requires that these namespaces do not exist at installation" |
| Customer Helm charts, databases, or brokers as Domino-managed workloads | **No documented mechanism, and no documented prohibition.** No custom-workload, sidecar, bring-your-own-service, or extension-chart concept exists. The installer configuration exposes namespace annotations and labels but no facility for additional releases |
| Service mesh | "A Domino-deployed Istio is for Domino use only." Domino's mesh cannot serve as the application mesh |
| Ingress | Domino installs nginx by default and will yield ownership via `ingress_controller.install = false`, requiring a network policy admitting ingress from the nginx namespace. **This is the one documented coexistence seam** |
| Node pools | Labeled platform and compute pools, with separate pools recommended |
| Network policy | Required. The cluster must use a NetworkPolicy-capable plugin such as Calico |
| Event bus for customers | **None.** RabbitMQ is internal platform infrastructure, and security guidance states Vault and RabbitMQ "should not be generally available." No customer-facing publish-subscribe, topic, stream, or queue API exists, shipped or planned |
| Managed database | Not shipped. A product requirements document dated 31 July 2026 remains in Phase-1 design, unsigned, with technical design and all milestones marked TODO. The provisional envelope is "<20 tables, <5GB total storage, <10 concurrent connections, low 100s of QPS," with high availability deferred, backup and restore deferred to a second milestone, single-writer in the first milestone, and row- and table-level security explicitly out of scope. Workload identity for Apps is recorded as "a critical prerequisite for this work" |
| Multi-tenancy guidance | Domino 4.x published guidance that Domino "does not interfere with other applications or other cluster-wide services" in a shared cluster. That page returns 404 and has no successor in the 6.x or Cloud documentation |

The correct reading of current documentation is that Domino can **coexist** in a cluster alongside separately managed workloads — bring your own ingress controller; Domino confines itself to its own namespaces and labeled node pools — but does not provide, document, or support a means of running always-on transactional services, databases, or event brokers as Domino-managed workloads. Anything co-located sits outside Domino's governance, audit trail, role-based access control, upgrade path, Nexus placement, and support boundary.

Notably, Domino's own internal exploration of persistence architecture names the microservice pattern the program requires, and records that the requirement went the other direction:

> "Microservices Architecture ('MA'): Databases and Apps have a 1:1 relationship. The one App defines the data schema and mediates all access to the data. All other clients (including other Apps, Workspaces, etc) must talk to the owner App via API, typically HTTP."
> — *Persistence Auth Architecture*, internal, July 2026

The same document notes that in working-group discussion "many people seem to want" the shared-database alternative instead, and characterizes the status quo as "the 'Wild West': App authors may code the authorization logic themselves."

### 4.7 Compliance claim requiring verification

The April 2026 public-sector submission claims **NIST 800-53 alignment**, not FedRAMP authorization. A July 2024 blog post refers to "Domino's plans to achieve FedRAMP High Authorization." The only FedRAMP documents located internally date from 2023 and 2024 and are inconclusive. No current internal documentation asserting FedRAMP Moderate or High authorization was found.

This distinction should be verified with Domino's compliance function before any FedRAMP representation appears in program material.

---

## 5. Basis for each boundary decision

| Component | Plane | Specific documented basis |
|---|---|---|
| Model training, feature pipelines, retraining | Intelligence | Jobs and Flows are purpose-built for this and execute on remote data planes by default. No alternative offers comparable reproducibility |
| Model registry, lineage, promotion governance | Intelligence | GA for registry and lineage. **Tier-weighted promotion gating is not expressible today** (§4.4, request D12); approximated through hardware-tier and data-plane proxies |
| Tier 0–3 fleet scoring | Intelligence, batch | Scheduled Jobs and Flows carry none of the Endpoint serving constraints. Fleet risk does not change second to second |
| Interactive tier-3 inference | Intelligence, Endpoint | Acceptable at low volume with bounded payloads. Traffic splitting is an Endpoint-only capability of genuine value for model rollout |
| Self-hosted language models | Intelligence | GA, in-VPC or on-premises, OpenAI-compatible, air-gappable. A principal argument for the platform |
| Agent runtimes | Intelligence, subject to §8.7 | Tracing, evaluation, versioning, and rollback are GA and directly serve the program's evaluation requirements. Contingent on resolving programmatic invocation |
| Practitioner analytical applications | Intelligence | Audience already holds Domino accounts; governance integration is valuable; Extensions provide native placement in the Domino interface |
| **Operator web interface** | **Sustainment** | Anonymous access is being removed platform-wide and every viewer is expected to hold a licensed account, which is inconsistent with fleet-scale maintainer access. Sub-path proxy rewriting has documented SPA asset failures. Iframe rendering by default. Base path supplied at runtime rather than build time. Applications are restarted by maintenance and evicted by node consolidation against a 99% SLA |
| **Nine domain sub-applications** | **Sustainment** | Documentation states Apps "are not intended for persistent workflows or large-scale back-end processing." No first-class application-to-application communication. No service discovery. No gRPC. No multi-container support. Single container per application, and internal guidance against communicating with in-cluster services |
| **Per-service databases** | **Sustainment** | No managed database exists. The provisional design envelope — under 5 GB, under 10 connections, low hundreds of queries per second, no high availability, no first-milestone backup, no row-level security — is a developer-convenience store rather than a transactional tier, and it is unbuilt and unsigned. Product documentation directs persistence to external databases |
| **Event bus** | **Sustainment** | No customer-facing event, stream, topic, or queue primitive exists in Domino, shipped or planned. Internal RabbitMQ is explicitly restricted |
| **Telemetry ingest** | **Sustainment** | Endpoint payload ceiling of 10 MB is fixed and formally declined for increase; practical request timeout near 60s; timed-out requests are not cancelled; no autoscaling; no serving SLO |
| **API gateway and ingress** | **Sustainment** | Domino owns its ingress by default and yields it only wholesale. Custom hostnames per application are unsupported. Applications are iframed |
| **Service mesh, if required** | **Sustainment** | "A Domino-deployed Istio is for Domino use only" |
| **Afloat and forward-deployed nodes** | **Program-operated Kubernetes** | Nexus data planes require continuous control-plane connectivity; `Disconnected` is an error state. Model export is the supported edge mechanism and has Navy precedent |

---

## 6. Domino changes required for Domino to host the entire program

The following changes would move the boundary in §5. They are ordered by whether they are blocking — that is, whether their absence alone prevents a component from moving into Domino — and annotated with evidence of feasibility, since several are already in motion. Where a change is already in flight, the program is well positioned to influence its shape rather than merely await it.

### 6.1 Blocking changes

Each of the six below is individually sufficient to prevent the Sustainment Plane from running inside Domino. All six would be required.

**D1 — Workload identity and machine-to-machine authentication for Apps and Endpoints.**
*Current state:* application authorization offers public access or interactive session authentication with no token-based intermediate; internal assessment characterizes remediation as a full overhaul. Endpoint authentication uses static tokens with no expiry, rotation, or per-caller audit. Application workload identity is recorded as a gap.
*Required change:* OAuth client-credentials or equivalent service-principal flow, scoped per workload, with rotation and per-caller audit, valid for invoking both Apps and Endpoints.
*Feasibility:* highest of the six. An authentication overhaul product requirements document is dated 3 August 2026; an identity-based invoke-authentication technical design for Endpoints is dated the same day; personal access tokens shipped in 6.3.0; an applications authorization overhaul is targeted for 6.4. This is the program's most tractable ask and also its most urgent, because architecture §8.7 depends on it.
*Program impact if delivered:* agent hosting confirmed in Domino; the §8.7 contingency retired.

**D2 — First-class service-to-service networking and discovery between Domino workloads.**
*Current state:* no first-class mechanism; internal guidance discourages in-cluster communication; service-link environment variables were disabled in the compute namespace; gRPC is not configurable; internal service DNS exists but is undocumented and, per internal discussion, effectively unreachable without administrator assistance.
*Required change:* stable internal DNS names for Apps and Endpoints; a declared dependency graph per workload; generated NetworkPolicy from those declarations; support for gRPC alongside HTTP.
*Feasibility:* no product requirements document located. Internal engineering identifies the gap explicitly, which is a starting point rather than a commitment.
*Program impact if delivered:* domain sub-applications could communicate, which is prerequisite to hosting more than one of them.

**D3 — Production-grade managed databases with per-workload ownership.**
*Current state:* unshipped Phase-1 design; provisional envelope under 5 GB, under 10 connections, low hundreds of queries per second; high availability, backup and restore, connection pooling, and row-level security absent or deferred; single writer in the first milestone; the microservice one-database-per-service pattern explicitly identified and not selected.
*Required change:* PostgreSQL with high availability, automated backup and point-in-time restore, connection pooling, migration hooks, and a capacity envelope appropriate to a transactional system; database-per-service ownership as a first-class pattern.
*Feasibility:* a product requirements document dated 31 July 2026 exists but is unsigned with all milestones marked TODO, and internal engineering has recorded unresolved objections including concern about over-engineering and a recommendation to narrow scope to Apps only. The program constitutes a concrete forcing case for a larger envelope.
*Program impact if delivered:* the largest single element of the Sustainment Plane could move, contingent on D1 and D2.

**D4 — A customer-facing event or stream primitive.**
*Current state:* none exists, shipped or planned. Internal RabbitMQ is restricted platform infrastructure. The Seldon-based asynchronous endpoint path is a sunset candidate.
*Required change:* durable topics with consumer groups, at-least-once delivery, and retention configuration, exposed to customer workloads with Domino-governed access control.
*Feasibility:* lowest of the six. No design work located in any source.
*Program impact if delivered:* the event backbone and the transactional-outbox pattern underpinning the afloat off-ramp could move into Domino.

**D5 — Multi-container workloads.**
*Current state:* one image, one launch file, one pod. The documented workaround is multiple processes behind a local nginx within a single container, characterized internally as inelegant.
*Required change:* declarative sidecar or multi-container support for migration jobs, outbox relays, proxies, and local caches.
*Feasibility:* an internal roadmap question was raised in October 2025 and received workarounds rather than a product answer.
*Program impact if delivered:* the transactional-outbox relay and per-service migration pattern become expressible.

**D6 — A declarative multi-service deployment unit.**
*Current state:* discussed only. An internal spike identified the direction and named candidate technologies — KubeVela, Score, Radius, CNAB, Knative, Porter — as "Future Investigation post MS1," observing that "at the time Domino apps were built, the idea of hosting a k8s PaaS was fairly nascent."
*Required change:* an application manifest describing a set of related services, their datastores, their event topics, and their dependency graph, deployed and versioned and governed as one unit.
*Feasibility:* recognized internally as the modern pattern; no product requirements document, owner, or date.
*Program impact if delivered:* the nine sub-applications become one governed Domino artifact rather than nine unmanaged ones, which is the condition under which "the whole system runs in Domino" becomes accurate rather than aspirational.

### 6.2 Enabling changes

Not individually blocking, but each removes a real constraint or risk from the current architecture.

| Ref | Change | Current state | Program benefit |
|---|---|---|---|
| **D7** | Endpoint horizontal autoscaling and scale-to-zero | Investigation ticket open since August 2022; the same mechanism shipped for Apps in 6.2.0 | Permits real-time inference on the operator request path; reduces idle GPU cost for tier-3 models |
| **D8** | Raise the payload ceiling; per-endpoint timeout with request cancellation | 10 MB fixed, increase declined; timed-out requests not cancelled, closed as will-not-do | Permits mission-scale telemetry payloads to be scored through Endpoints; removes the single-slow-request replica stall |
| **D9** | A serving-path service-level objective | None exists; SLOs cover build and deploy only | Required for any operational availability commitment to the Navy |
| **D10** | Application hosting fidelity: per-application hostnames, non-iframe full-window hosting, base-path rewriting at the ingress rather than in application code | Custom paths only; iframe default; runtime environment variable; documented SPA asset failures | Would permit the operator interface to move into Domino, subject to D11 |
| **D11** | A consumer or read-only licensing tier for application viewers at fleet scale | Anonymous access being removed; every viewer expected to hold a licensed account | Commercial rather than technical, but architecturally determinative for a maintainer-facing interface across a fleet |
| **D12** | Governance gates on lifecycle stages rather than infrastructure proxies; mandatory policy attachment | Gates are infrastructure proxies, YAML-only, statically evaluated, and enforce only on already-governed assets | Closes the opt-in governance gap, which is likely to be examined during accreditation |
| **D13** | Image-based distribution with no dependency retrieval at container start | Application runtime performs source retrieval and package installation at pod start. Internal engineering states this "is categorically incompatible with these environments. There is no workaround." Remediation is a March 2026 draft proposal scoped to Extensions | Removes the principal air-gap obstacle for Domino-hosted workloads |
| **D14** | An offline-capable data plane: lease-based authorization, store-and-forward execution state, declared conflict resolution | Continuous control-plane connectivity required; `Disconnected` is an error state; nothing in any source contemplates offline operation | The only change that would permit a Domino data plane afloat. Largest ask in the assessment and the one with least existing groundwork |

### 6.3 Assessment of the ask

D1 is close, actively in flight, and should be pursued immediately because it gates the agentic design. D3 and D6 are in motion but unsigned, and the program is a credible forcing case for both — particularly D3, where the current envelope is being scoped downward at precisely the moment a concrete large-envelope requirement exists. D2 and D5 are recognized gaps without owners. D4 and D14 have no groundwork whatsoever and should be treated as multi-release efforts if pursued at all.

The realistic near-term position is therefore the two-plane architecture, with D1 pursued as an immediate dependency and D3, D6, D9, D11, D12, and D13 pursued as a design-partner agenda.

---

## 7. Questions for Domino product management

Ordered by consequence to the architecture.

1. **Can personal access tokens, or any token mechanism, invoke Apps and Endpoints programmatically?** This determines whether agent runtimes can be Domino-hosted (architecture §8.7). If not, what is the 6.4 authorization overhaul's intended answer for machine-to-machine callers?
2. **Is there intent to give Endpoints the horizontal autoscaling that Apps received in 6.2.0?** The investigation ticket has been open four years.
3. **What is the timeline for generative-AI and LLM endpoints on remote data planes?** Required for any forward-deployed or afloat inference within a connected enclave.
4. **Is any offline or intermittently-connected data-plane capability contemplated?** Nothing in the documentary record addresses it, and it is the single hardest blocker to a DDIL design.
5. **What is the intended capacity envelope for managed databases, and is a transactional envelope contemplated?** The current provisional figures preclude domain-service use.
6. **Is there a supported pattern for customer-managed workloads coexisting in a Domino cluster?** The 4.x multi-tenancy guidance has been withdrawn without a successor, and the program requires a defensible statement of the coexistence posture for accreditation documentation.
7. **What is the current FedRAMP authorization status?** The 2026 public-sector submission claims NIST 800-53 alignment; a 2024 post refers to plans for FedRAMP High.
8. **Is auto-suspend for Apps a shipped capability?** Product documentation, marketing, and the administrative interface disagree.
9. **What licensing model applies to fleet-scale read-only application viewers** following removal of anonymous access?
10. **Will governance gates become expressible as lifecycle stages, and will policy attachment become mandatory?** Both bear on the accreditation narrative.

---

## 8. Strategic context

Domino's internal roadmap is explicitly repositioning the product toward application delivery. The February 2026 roadmap summary is titled "Product Roadmap: From MLOps Platform to AI Application Partner" and states:

> "We're transforming Domino from an MLOps tool that data scientists use into a platform where enterprises depend on us to build and distribute AI-powered applications used by stakeholders across their business."

Four pillars are named — Model Factory, Application Hub, Governance Center, and Platform Services with multi- and hybrid-cloud orchestration — with Production Apps SDLC, an authentication and authorization overhaul, and Extensions in the first half of FY27, and unified governed products plus a new API serving stack in the second half. The stated delivery model is co-building with forward-deployed engineers. An internal applications initiative carries the working name "Domino App Factory," and its problem statement is directly aligned: "In order to position Domino as an app development and hosting platform, we must minimize friction in the App SDLC."

Two calibrations are warranted. First, the term "PaaS" appears in internal engineering documentation once, and as something Domino is not. The roadmap's application ambition concerns AI-powered applications and dashboards that front models, not arbitrary transactional microservices. Nothing in the FY27 roadmap addresses event buses, service meshes for customer workloads, custom ingress, or declarative multi-service deployment. Second, the leadership signal is nonetheless real: the chief executive has stated internally that what resonates with customers is "showing what we can do with Apps to deliver entire use cases," and separately that Domino needs to become "a great platform for developing solutions on top of."

This program is therefore well aligned with Domino's stated direction and constitutes a credible forcing function for the six blocking capabilities in §6.1 — most immediately D1, which is already in flight, and D3, whose envelope is being decided now. Pursuing formal design-partner status on that agenda is recommended.

No Domino predictive-maintenance or CBM+ accelerator, reference architecture, or reusable asset exists. Existing defense accelerators address automatic target recognition, document intelligence, geospatial analysis, and requirements triage. This program would establish the predictive-maintenance accelerator rather than adapt one.

---

## 9. Caveats on this assessment

- **Several decisive documents are days old and unsigned.** The structured-data, authentication-overhaul, applications SDLC, and governance product requirements documents were all modified between 21 July and 3 August 2026, and none carries executive sign-off. Items characterized here as in design may move within one release cycle — though several have also remained in Phase-1 status for months.
- **Internal documentation quality is uneven.** No consolidated limits or quotas table exists for Endpoints; figures in this assessment were assembled from runbooks and individual tickets, several drawn from sections self-labeled as stale. Three internal configuration-key naming inconsistencies were identified and left unresolved. Public documentation contains at least two internal contradictions: on **idle suspension**, where the product documentation states applications run until explicitly stopped while marketing claims auto-suspend and the interface exposes a Suspended state; and on **application autoscaling**, where the autoscaling page documents HPA v2 with multiple replicas while a separate performance-tuning page in the same documentation tree states that applications do not scale horizontally. The autoscaling page is the current one.
- **Absence of documentation is reported as absence of documentation.** Where this assessment states that no mechanism was found, that is a statement about the documentary record, not a proof of impossibility. The §7 questions exist to convert those gaps into answers.
- **Capability changes rapidly.** All findings are as of 4 August 2026 against self-managed 6.2.3 and Cloud Release 90, and should be re-verified before any commitment rests on them.

---

## 10. Recommended follow-on reading

| Document | Relevance |
|---|---|
| *PRD — Auth Overhaul* (internal, 3 Aug 2026) | Where D1 is likely resolved; the gating dependency for both databases and machine-to-machine access |
| *PRD — API Gateway* (internal, 31 Jul 2026) | Internal service routing direction; bears on D2 |
| *PRD Structured Data (Databases)* (internal, 31 Jul 2026) | The D3 envelope, currently being decided |
| *Persistence Auth Architecture* (internal, Jul 2026) | Domino's own framing of the microservice-versus-shared-database choice |
| *Apps Refresh: Initial SPIKE* (internal, Feb 2025) | The D6 direction and candidate technologies |
| *Container-Based Extension Distribution* (internal, Mar 2026) | The D13 air-gap remediation proposal |
| *AI Effects at the Edge* (internal, Apr 2026) | Accreditation posture and the model-export edge pattern with Navy precedent |
| *Navy AMMO Use Case* | The accredited precedent architecture and its hybrid shape |
| *6.3.0 Release Retrospective* (internal, 31 Jul 2026) | What shipped in 6.3 against what slipped |
| Internal RFI response library | Reusable DoD compliance and past-performance language for program submissions |
