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

**Regenerate it whenever `apps/web`'s source changes:**

```bash
cd apps/web && pnpm build
rm -rf ../../deploy/domino-demo/web-dist/*
cp -r dist/* ../../deploy/domino-demo/web-dist/
```

This is a real, intentional gap for a demo pipeline, not a production
CI/CD story — a real deployment would build `apps/web` in CI and publish
the artifact, not commit it.
