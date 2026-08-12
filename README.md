# FATHOM

A Navy fleet-sustainment platform: a polyglot monorepo of domain services, platform
services, and operator/practitioner UIs. The full system is specified up front in
`docs/` and implemented one vertical slice at a time.

> **Status:** early implementation. Only a fraction of the specified system exists today —
> `services/pdm` (Predictive Maintenance), `platform/gateway`, `apps/web`, the four shared
> `packages/`, and one Domino Job entrypoint under `models/`. Every other directory named
> in the specs is still a placeholder. The specs are the source of truth for what code
> *should* do; the code is the source of truth for what exists.

## Repository layout

| Path | What it holds |
|---|---|
| `packages/` | Shared Python libraries (`canonical-schemas`, `py-sync`, `contracts`, `py-common`) |
| `services/<slug>/` | Domain services (e.g. `pdm`) — independent `uv` projects |
| `platform/<slug>/` | Platform services (e.g. `gateway` — the BFF) |
| `apps/web` | Operator console (Vite + React + TypeScript SPA) |
| `models/` | Domino Job entrypoints (model scoring) |
| `deploy/` | Helm charts and Domino demo assets |
| `tools/` | CI reconciliation scripts |
| `docs/architecture/` | Architecture specs (`01`–`08`) |
| `docs/build/` | Build specs (`09`+), the binding contract for each service |

## Getting started

The `Makefile` is the single entrypoint; CI calls only these targets. `SLUG` selects a
service (e.g. `pdm`); repo-wide targets take no `SLUG`. Python runs through `uv`.

```bash
make lint                    # ruff check + format check (repo-wide)
make typecheck SLUG=pdm      # mypy --strict
make test SLUG=pdm           # pytest unit + integration, with coverage
make contract SLUG=pdm       # regenerate openapi.json and diff against the committed copy
make check-event-catalog     # reconcile event catalogs against the specs (repo-wide)
make charts SLUG=pdm         # helm lint / template / unittest + hadolint
make scaffold SLUG=<new>     # generate a new service from the standard skeleton
```

Integration tests spin up **real** Postgres/Redpanda via testcontainers, so a working
Docker/Podman socket is required.

Frontend (`apps/web`):

```bash
pnpm install                 # from repo root (pnpm workspace)
cd apps/web && pnpm dev      # Vite dev server
cd apps/web && pnpm build    # tsc -b && vite build
cd apps/web && pnpm test     # vitest
```

## Documentation

- **`CLAUDE.md`** (repo root) — project conventions, architecture notes, and a running
  handoff log of implementation history.
- **`docs/build/09-monorepo-and-conventions.md`** — the master spec: layout, tech-stack
  pins, per-service scaffold, API conventions, CI gates, and Definition of Done. Read this
  before starting any new service.
- **`docs/build/`** — per-service build specs (e.g. `22-pdm.md`, `30-gateway.md`), the
  binding contract each service is implemented against.
- **`docs/architecture/`** — the higher-level system architecture the build specs derive
  from.
