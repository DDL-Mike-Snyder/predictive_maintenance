#!/bin/bash
# Redesign Case Builder -- DOMINO WORKSPACE entrypoint.
#
# Runs the whole RCB stack behind ONE gateway process on the workspace app
# port (9888 by default -- 8888 is the notebookSession itself), bound to
# 0.0.0.0, reachable through the Domino workspace proxy. The gateway serves
# apps/web's built UI at the same origin AND proxies /api to both upstreams,
# using demo_auto_login instead of real OIDC.
#
# Distinct from:
#   - app.sh            -- the PdM demo (fathom-pdm-demo App), untouched
#   - deploy/domino-demo/app_rcb.sh -- the RCB *Domino App* deploy (port 8888)
#
# The one thing that MUST be right for a proxied sub-path (this is the
# blank-page/404 class of bug this repo has hit before): apps/web is built
# with VITE_BASE_URL = the proxy path, so both its assets and its API calls
# carry the `/.../proxy/<port>/` prefix. Domino's proxy strips that prefix
# before the gateway sees the request, so the gateway itself still serves at
# "/", "/assets/...", "/api/...".
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PORT="${APP_PORT:-9888}"
DATA_DIR="${RCB_DATA_DIR:-$REPO_ROOT/.rcb-demo-data}"
mkdir -p "$DATA_DIR"
export PATH="/opt/nodejs/bin:$PATH"

# Proxy path this app is reached at. DOMINO_RUN_HOST_PATH is the EXTERNAL
# form /owner/project/r/notebookSession/<runId>/ -- note the `/r/`. That `/r/`
# is a Domino-edge redirect marker that only works for the top-level document
# navigation; Jupyter's real base_url (JUPYTER_SERVER_URL) has NO `/r/`, and
# sub-resource requests (assets, /api) carrying `/r/` 404 at Jupyter. So we
# bake the CANONICAL no-`/r/` path as the base -- assets and API then resolve.
# Open the app at the no-`/r/` URL this prints, so the document, assets, API,
# and the React-Router basename are all consistent.
RAW_PATH="${DOMINO_RUN_HOST_PATH:-/}"
CANON_PATH="${RAW_PATH/\/r\/notebookSession\//\/notebookSession\/}"
BASE_PATH="${CANON_PATH}proxy/${APP_PORT}/"

ensure_venv() {
  local dir="$1"
  if [ ! -x "$dir/.venv/bin/python" ]; then
    echo "=== RCB: building venv for $dir ==="
    (cd "$dir" && uv venv --python 3.12 .venv \
       && uv pip install -e . --python .venv/bin/python \
       && uv pip install aiosqlite --python .venv/bin/python)
  fi
}
ensure_venv "$REPO_ROOT/services/design-advisory"
ensure_venv "$REPO_ROOT/platform/gateway"

echo "=== RCB: seeding design-advisory (creates tables + 5 candidates) ==="
rm -f "$DATA_DIR/design_advisory.db"
(cd "$REPO_ROOT/services/design-advisory" \
   && DESIGN_ADVISORY_DATABASE_URL="sqlite+aiosqlite:///$DATA_DIR/design_advisory.db" \
      .venv/bin/python scripts/seed_demo_data.py)

echo "=== RCB: regenerating design-advisory openapi.json (gateway reads it) ==="
(cd "$REPO_ROOT/services/design-advisory" \
   && DESIGN_ADVISORY_DATABASE_URL="sqlite+aiosqlite:///$DATA_DIR/design_advisory.db" \
      .venv/bin/python -m fathom_design_advisory.main --emit-openapi \
      > "$REPO_ROOT/services/design-advisory/openapi.json")

echo "=== RCB: building apps/web with base path $BASE_PATH ==="
command -v pnpm >/dev/null 2>&1 || npm install -g pnpm@9
(cd "$REPO_ROOT" && pnpm install --frozen-lockfile)
# VITE_ASSETS_DIR: emit the bundle under a non-"/assets/" dir -- Domino's
# workspace edge reserves the /assets/ path segment for its own frontend and
# won't forward it to this app (see apps/web/vite.config.ts).
(cd "$REPO_ROOT/apps/web" && VITE_BASE_URL="$BASE_PATH" VITE_ASSETS_DIR="app-assets" pnpm build)

echo "=== RCB: initializing gateway schema ==="
GATEWAY_DB_PATH="$DATA_DIR/gateway_rcb.db" "$REPO_ROOT/platform/gateway/.venv/bin/python" \
  "$REPO_ROOT/deploy/domino-demo/init_gateway_schema.py"

echo "=== RCB: starting design-advisory (background, port 8002) ==="
(cd "$REPO_ROOT/services/design-advisory" \
   && DESIGN_ADVISORY_DATABASE_URL="sqlite+aiosqlite:///$DATA_DIR/design_advisory.db" \
      DESIGN_ADVISORY_BASE_URL="http://127.0.0.1:8002" \
      exec .venv/bin/uvicorn fathom_design_advisory.main:app --host 127.0.0.1 --port 8002) &
DA_PID=$!
trap 'kill "$DA_PID" 2>/dev/null || true' EXIT INT TERM

cat <<EOF

==================================================================
INFO: Redesign Case Builder is starting on port ${APP_PORT}
INFO: Open it in your browser at (NOTE: no '/r/' in this path -- that is
INFO: required for assets/API to load; see the header comment):
INFO:   https://<your-domino-host>${BASE_PATH}
INFO: Prepend the same host you use to reach this workspace. Then click
INFO: "Design Advisory" in the left nav.
==================================================================

EOF

echo "=== RCB: starting gateway (foreground, port ${APP_PORT}, serves UI + both upstreams) ==="
cd "$REPO_ROOT/platform/gateway"
export FATHOM_DATABASE__URL="sqlite+aiosqlite:///$DATA_DIR/gateway_rcb.db"
export FATHOM_OIDC__ISSUER="https://demo-issuer/realms/fathom"
export FATHOM_OIDC__CLIENT_ID="demo"
export FATHOM_OIDC__CLIENT_SECRET="demo"
export FATHOM_OIDC__REDIRECT_URI="https://demo.invalid/api/v1/gateway/session/callback"
export FATHOM_SESSION__COOKIE_SIGNING_KEY="demo-signing-key-not-a-real-secret"
export FATHOM_SESSION__DEMO_AUTO_LOGIN="true"
export FATHOM_SESSION__LANDING_URL="${BASE_PATH}"
export FATHOM_PDM__BASE_URL="http://localhost:8001"
export FATHOM_PDM__OPENAPI_PATH="$REPO_ROOT/services/pdm/openapi.json"
export FATHOM_DESIGN_ADVISORY__BASE_URL="http://127.0.0.1:8002"
export FATHOM_DESIGN_ADVISORY__OPENAPI_PATH="$REPO_ROOT/services/design-advisory/openapi.json"
export FATHOM_APP__STATIC_DIR="$REPO_ROOT/apps/web/dist"
exec .venv/bin/uvicorn fathom_gateway.main:app --host 0.0.0.0 --port "${APP_PORT}"
