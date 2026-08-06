# Domino demo deployment (`app.sh`)

Runs PdM + the gateway (which also serves `apps/web`) as one Domino App,
using SQLite and `demo_auto_login` instead of the real CloudNativePG
Postgres + Keycloak/OIDC every other deployment in this repo uses. See
`app.sh`'s own header comment for the full reasoning.

## `web-dist/` — a committed, demo-only exception to the real `dist/` gitignore rule

A Domino App gets its own fresh `git clone` in its own container, with no
Node.js in the environment used here (`Domino Core Environment`) — so
`apps/web` can't be built inside the App's own container the way every
other deployment builds it. This directory is a **committed snapshot** of
`apps/web/dist` for `app.sh` to serve directly.

**Regenerate it whenever `apps/web`'s source changes, or the registered
App's own ID changes** (found the hard way — a blank page, nothing
rendering, after the 502 fix above): Domino's own App URL is a real path
prefix (`/apps-internal/<appId>/`), and Vite's default build emits
root-absolute asset paths (`/assets/...`) that silently resolve to the
wrong URL once loaded from under that prefix — the JS bundle never
loads, so React never mounts, and the page is blank with no console
error obviously pointing at "wrong path" unless you check the Network
tab. `VITE_BASE_URL` must be set to the App's real, absolute mount path
at build time — this also fixes `createBrowserRouter`'s own `basename`
(`main.tsx` already wires `import.meta.env.BASE_URL` into it), which
needs a real absolute path for route matching, not a relative `./`:

```bash
cd apps/web
VITE_BASE_URL="/apps-internal/6a74924c664e0f706e462d33/" pnpm build
rm -rf ../../deploy/domino-demo/web-dist/*
cp -r dist/* ../../deploy/domino-demo/web-dist/
```

**The appId above (`6a74924c664e0f706e462d33`) is specific to the
`fathom-pdm-demo` App currently registered in the `predictive_maintenance`
project — if that App is ever deleted and recreated, it gets a new ID,
and this build (plus this README) needs updating to match.**

This is a real, intentional gap for a demo pipeline, not a production
CI/CD story — a real deployment would build `apps/web` in CI, publish the
artifact, and serve it from the real target's own stable base path (per
`02-domino-platform-assessment.md`'s own documented reasoning for why
that real target is the Sustainment Plane, not Domino) — not commit a
build pinned to one Domino App's own generated ID.
