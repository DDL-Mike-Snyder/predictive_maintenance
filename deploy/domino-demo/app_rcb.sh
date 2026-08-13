#!/bin/bash
# Domino App entrypoint for the Redesign Case Builder demo
# (docs/demo/redesign-case-builder-demo-plan.md). A SEPARATE App/entryPoint
# from the existing `app.sh` (fathom-pdm-demo) -- runs the RCB stack in its
# own App/container so it never touches the already-deployed fathom-pdm-demo
# App (do NOT overwrite that one -- see the demo plan, Amanda Part 3).
#
# [B-4 integration fix] This now runs the FULL integrated stack, not just
# the design-advisory API: design-advisory (background, 8002) + the gateway
# (foreground on 8888, Domino's real App-ingress port), which proxies BOTH
# upstreams, mounts the agent qualify/draft endpoints, uses demo_auto_login
# instead of real OIDC, and serves apps/web's pre-built static UI at the
# same origin -- exactly the pattern the root app.sh already uses for PdM.
#
# Same discipline as root app.sh: a Domino App gets its OWN fresh `git
# clone` in its own container, so this script builds both venvs from
# scratch every start.
#
# [STRETCH / UNTESTED ON DOMINO] The integrated backend+gateway wiring here
# is verified locally (see deploy/domino-demo/run_rcb_local.sh, which is the
# same wiring on ports 8002/8000 and is the demo's actual deliverable). What
# is NOT verifiable outside a real Domino App container is the static UI
# step: apps/web must be built with VITE_BASE_URL set to THIS App's own
# absolute mount path (`/apps-internal/<appId>/`) and that build committed to
# RCB_WEB_DIST below, exactly as deploy/domino-demo/web-dist/ was baked for
# the PdM App. There is no Node.js in the App container, so the build cannot
# happen here -- it is a committed snapshot, App-ID-specific, regenerated
# whenever the App is recreated. If RCB_WEB_DIST is absent the gateway still
# serves the real API (raw /docs is the fallback click-through surface).
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA_DIR="$REPO_ROOT/.demo-data"
mkdir -p "$DATA_DIR"
RCB_WEB_DIST="${RCB_WEB_DIST:-$REPO_ROOT/deploy/domino-demo/web-dist-rcb}"

echo "=== RCB demo: installing Python 3.12 ==="
uv python install 3.12

echo "=== RCB demo: setting up design-advisory's venv ==="
cd "$REPO_ROOT/services/design-advisory"
uv venv --python 3.12 .venv
uv pip install -e . --python .venv/bin/python
uv pip install aiosqlite --python .venv/bin/python

echo "=== RCB demo: setting up gateway's venv ==="
cd "$REPO_ROOT/platform/gateway"
uv venv --python 3.12 .venv
uv pip install -e . --python .venv/bin/python
uv pip install aiosqlite --python .venv/bin/python

echo "=== RCB demo: seeding design-advisory (creates tables + 5 candidates) ==="
cd "$REPO_ROOT/services/design-advisory"
export DESIGN_ADVISORY_DATABASE_URL="sqlite+aiosqlite:///$DATA_DIR/design_advisory.db"
.venv/bin/python scripts/seed_demo_data.py

echo "=== RCB demo: regenerating design-advisory openapi.json (gateway reads it) ==="
.venv/bin/python -m fathom_design_advisory.main --emit-openapi > "$REPO_ROOT/services/design-advisory/openapi.json"

echo "=== RCB demo: initializing gateway schema ==="
GATEWAY_DB_PATH="$DATA_DIR/gateway_rcb.db" "$REPO_ROOT/platform/gateway/.venv/bin/python" \
  "$REPO_ROOT/deploy/domino-demo/init_gateway_schema.py"

echo "=== RCB demo: starting design-advisory (background, port 8002) ==="
(
  cd "$REPO_ROOT/services/design-advisory"
  export DESIGN_ADVISORY_DATABASE_URL="sqlite+aiosqlite:///$DATA_DIR/design_advisory.db"
  export DESIGN_ADVISORY_BASE_URL="http://127.0.0.1:8002"
  exec .venv/bin/uvicorn fathom_design_advisory.main:app --host 127.0.0.1 --port 8002
) &

echo "=== RCB demo: starting gateway (foreground, port 8888) ==="
cd "$REPO_ROOT/platform/gateway"
export FATHOM_DATABASE__URL="sqlite+aiosqlite:///$DATA_DIR/gateway_rcb.db"
export FATHOM_OIDC__ISSUER="https://demo-issuer/realms/fathom"
export FATHOM_OIDC__CLIENT_ID="demo"
export FATHOM_OIDC__CLIENT_SECRET="demo"
export FATHOM_OIDC__REDIRECT_URI="https://demo.invalid/api/v1/gateway/session/callback"
export FATHOM_SESSION__COOKIE_SIGNING_KEY="demo-signing-key-not-a-real-secret"
export FATHOM_SESSION__DEMO_AUTO_LOGIN="true"
export FATHOM_SESSION__LANDING_URL="/design-advisory"
export FATHOM_PDM__BASE_URL="http://localhost:8001"
export FATHOM_PDM__OPENAPI_PATH="$REPO_ROOT/services/pdm/openapi.json"
export FATHOM_DESIGN_ADVISORY__BASE_URL="http://127.0.0.1:8002"
export FATHOM_DESIGN_ADVISORY__OPENAPI_PATH="$REPO_ROOT/services/design-advisory/openapi.json"
[ -d "$RCB_WEB_DIST" ] && export FATHOM_APP__STATIC_DIR="$RCB_WEB_DIST"
exec .venv/bin/uvicorn fathom_gateway.main:app --host 0.0.0.0 --port 8888
