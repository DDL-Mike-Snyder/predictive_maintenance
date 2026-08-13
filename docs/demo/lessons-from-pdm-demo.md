# Lessons from the PdM demo — trade-offs made vs. the documented spec

**Who this is for:** whoever is building the Redesign Case Builder demo
(see `docs/demo/redesign-case-builder-demo-plan.md`). That plan's own
§0.1 ("What we are explicitly NOT building") already applies the same
discipline described here — this file is the precedent and the reasoning
behind it, drawn from actually shipping the earlier PdM demo, not a new
set of shortcuts invented for this task. If your own demo needs to cut a
corner not already named in your plan, use the same test this file
applies throughout: **name the cut explicitly, in a comment or doc, and
verify the result by actually running it — never assume a paper design
survives contact with a real deployment.**

`services/pdm`, `platform/gateway`, and `app.sh` are real, full
implementations of the corpus's own build docs (`docs/build/22-pdm.md`,
`30-gateway.md`) for local/Kubernetes/production use — RLS, real
Postgres, real OIDC, real Helm charts, all of it exists and is tested.
**The trade-offs below are specifically what changed for the
demo-hosting path** (`app.sh`, `deploy/domino-demo/`), not the real
implementation underneath it. Same code, different runtime mode.

---

## Trade-off table: documented vs. what we actually ran

| Area | What `docs/build/*` specifies | What the demo actually runs | Why this was safe to cut |
|---|---|---|---|
| **Auth** | Real OIDC/Keycloak, delegated tokens, dual-control adjudication (31-auth.md) | `demo_auto_login` — an opt-in gateway mode that mints a session with no login step at all | A Domino-hosted demo has no Keycloak reachable from both the gateway and an arbitrary browser; a real login flow was proven separately (Keycloak in a container, real redirect/callback) and works — it's just not what the *Domino-hosted* path uses |
| **Database** | CloudNativePG-managed Postgres, RLS-enforced compartment isolation (22-pdm.md §4.5) | SQLite, no RLS | RLS was built and tested for real against Postgres elsewhere in this repo (10 passing RLS tests) — the demo just doesn't need compartment isolation to tell its story, and a Domino App's own container has no persistent Postgres to point at anyway |
| **Events / messaging** | Kafka outbox + consumer loop, real event catalog (11-outbox-sync-library.md) | Not run at all — `FATHOM_EVENTS__BROKERS="demo"` is a stub, nothing drains the outbox | The demo's own narrative doesn't depend on cross-service event propagation; the outbox still gets written to (harmless), just never drained |
| **Deployment topology** | Per-service Helm chart, its own pod, its own NetworkPolicy, on a real K8s cluster (09 §4) | Every process (PdM, gateway, the built UI) runs **in one container**, started by one script | A Domino App gets its **own fresh `git clone`**, isolated from any interactive workspace's filesystem, with no persistent volume across restarts — one self-sufficient script that builds everything from scratch on every start is simpler and more robust than trying to reuse per-service Helm/K8s machinery inside that constraint |
| **Frontend build** | `apps/web` built in CI, published, served from its own stable path (02-domino-platform-assessment.md §5) | A **committed, pre-built static snapshot** (`deploy/domino-demo/web-dist/`) | No Node.js exists in the Domino App's own container/environment — the build has to happen beforehand, on a machine that has Node, and get committed |
| **Agent runtime / tool-server** | Agents call domain services exclusively through `platform/tool-server`'s MCP surface (34-tool-server.md) | N/A for PdM (PdM has no agent runtime yet) — but see your own plan's §0.1, same call was made there: the agent calls the domain service's HTTP API directly | Building a real MCP tool-server is a multi-hour investment on its own; skipping it doesn't change the demo's actual narrative, it changes an internal wiring detail nobody in the audience sees |
| **UI scope** | Eleven wireframe sheets (51-operator-console.md §4.2) | One real screen (Fleet-Risk Triage / `/pdm`), the other ten are `NotBuilt`/`ExternalLaunch` placeholders | Building one real, fully-wired screen well beats ten shallow ones — same principle your own plan applies to Design Advisory |
| **Model fidelity** | Real Weibull MLE / IPCW fits per tier (22-pdm.md §5.1) | A stand-in entrypoint that emits only the one shape a fit-free implementation can honestly claim (`class_estimate`, `population_hazard_rate`) | No real per-NIIN telemetry/failure-label infrastructure exists yet to fit against — the demo's seeded predictions are realistic-looking, not derived from a real model, and this is stated plainly rather than implied |

---

## Bugs this caused — the same *shapes* will bite a Domino-hosted demo again

These aren't PdM-specific bugs; they're consequences of the trade-offs
above, so expect the same **classes** of bug if the redesign-case-builder
demo ever gets deployed as a real Domino App (currently scoped as an
optional stretch goal in your plan — this is exactly why):

1. **Root-relative asset paths break under a real path prefix.** Domino
   serves an App at `/apps-internal/<appId>/`, not `/`. Vite's default
   build emits root-absolute asset paths; any API client with a
   hardcoded `baseUrl` makes the same mistake. Both must derive from
   `import.meta.env.BASE_URL` / `VITE_BASE_URL` set at build time — this
   bit PdM's demo twice (once for the blank page, once for "couldn't
   load predictions") because it's really one bug, hit in two places.
2. **A Domino App's container is not an interactive workspace's
   filesystem.** No shared venvs, no shared Node install, no assumption
   that "it already works in the workspace" carries over. Whatever
   starts the App has to be self-sufficient from a bare clone.
3. **Port conventions differ by execution context.** 8888 looking
   "occupied" was a false alarm from testing inside an interactive
   workspace (Jupyter sits there) — it's Domino's real ingress port
   inside an App's own dedicated container.
4. **The App-registration API surface itself has real bugs** (the
   SDK's own `app_publish()` references an undefined variable; its docs
   point at the wrong REST shape — the working one is the legacy
   `/v4/modelProducts` surface). Budget time to find this the same way
   we did: by reading the SDK's own source, not trusting its docs.
5. **The committed static build is pinned to one App's ID.** If the App
   is ever deleted and recreated, it gets a new ID, and `VITE_BASE_URL`
   (and the committed build) needs regenerating to match — see
   `deploy/domino-demo/README.md`'s own worked example.

---

## What did NOT get cut — the boundary rules that survived every trade-off

The infrastructure got thin; the **domain honesty rules did not**, and
your plan should hold the same line:

- A `redesign_case`'s recommendation is a **suggestion for a human**,
  never a decision the system makes (04 §10) — this stayed true even
  though almost everything else around it was simplified.
- Non-empty limitations/evidence-gaps, evidence-strength cited verbatim
  (never re-banded or upgraded), and cost figures that say plainly when
  they're a lower bound — none of these got relaxed for demo speed,
  because they're cheap to keep and they're the whole point of the
  system, unlike the infrastructure around them.
- Every simplification was **named in a comment or doc**, not silently
  absorbed. If you cut something new, do the same — the next person (or
  the next Claude) reading this repo should never have to discover a cut
  corner by finding a bug.

---

## One-line summary, if you only read one paragraph

**We kept the full-fidelity implementation of every domain rule, and cut
almost everything about how it's wired up and deployed** — auth, storage,
events, tool invocation, deployment topology, model fitting. Every cut
was made because it was invisible to the audience and expensive to build
for real, never because it was hard to get right. Apply the same test:
cut wiring, keep honesty, name every cut, verify by running it for real.
