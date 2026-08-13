#!/bin/bash
# Redesign Case Builder -- local integrated run (B-4 integration fix).
#
# This is the demo plan's ACTUAL deliverable
# (docs/demo/redesign-case-builder-demo-plan.md, Amanda Part 2): the whole
# stack running on localhost -- design-advisory + gateway (both upstreams,
# agent endpoints included, demo_auto_login) -- so the real backend is
# reachable end-to-end through the gateway exactly as a browser hits it.
# The `apps/web` operator UI is started separately with `pnpm dev` (it
# proxies /api to the gateway via vite.config.ts) -- printed at the end.
#
# Idempotent: rebuilds either venv only if missing; reseeds a fresh
# design-advisory DB each run. Ctrl-C stops both background services.
#
# Verified end-to-end (health + the full qualify->create->draft->propose
# flow through the gateway) on 2026-08-13.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA_DIR="${RCB_DATA_DIR:-$REPO_ROOT/.rcb-demo-data}"
mkdir -p "$DATA_DIR"
DA_DB="$DATA_DIR/design_advisory.db"
GW_DB="$DATA_DIR/gateway.db"

DA_DIR="$REPO_ROOT/services/design-advisory"
GW_DIR="$REPO_ROOT/platform/gateway"

ensure_venv() {
  local dir="$1"
  if [ ! -x "$dir/.venv/bin/python" ]; then
    echo "=== RCB: building venv for $dir ==="
    (cd "$dir" && uv venv --python 3.12 .venv && uv pip install -e . --python .venv/bin/python \
       && uv pip install aiosqlite --python .venv/bin/python)
  fi
}

ensure_venv "$DA_DIR"
ensure_venv "$GW_DIR"

echo "=== RCB: seeding design-advisory (creates tables + 5 candidates) ==="
rm -f "$DA_DB"
(cd "$DA_DIR" && DESIGN_ADVISORY_DATABASE_URL="sqlite+aiosqlite:///$DA_DB" \
   .venv/bin/python scripts/seed_demo_data.py)

echo "=== RCB: starting design-advisory (port 8002) ==="
(cd "$DA_DIR" && \
   DESIGN_ADVISORY_DATABASE_URL="sqlite+aiosqlite:///$DA_DB" \
   DESIGN_ADVISORY_BASE_URL="http://127.0.0.1:8002" \
   exec .venv/bin/uvicorn fathom_design_advisory.main:app --host 127.0.0.1 --port 8002) &
DA_PID=$!

echo "=== RCB: initializing gateway schema ==="
GATEWAY_DB_PATH="$GW_DB" "$GW_DIR/.venv/bin/python" "$REPO_ROOT/deploy/domino-demo/init_gateway_schema.py"

echo "=== RCB: starting gateway (port 8000, both upstreams, demo_auto_login) ==="
(cd "$GW_DIR" && \
   FATHOM_DATABASE__URL="sqlite+aiosqlite:///$GW_DB" \
   FATHOM_OIDC__ISSUER="https://demo-issuer/realms/fathom" \
   FATHOM_OIDC__CLIENT_ID="demo" FATHOM_OIDC__CLIENT_SECRET="demo" \
   FATHOM_OIDC__REDIRECT_URI="https://demo.invalid/api/v1/gateway/session/callback" \
   FATHOM_SESSION__COOKIE_SIGNING_KEY="demo-signing-key" \
   FATHOM_SESSION__DEMO_AUTO_LOGIN="true" FATHOM_SESSION__LANDING_URL="/design-advisory" \
   FATHOM_PDM__BASE_URL="http://localhost:8001" \
   FATHOM_PDM__OPENAPI_PATH="$REPO_ROOT/services/pdm/openapi.json" \
   FATHOM_DESIGN_ADVISORY__BASE_URL="http://127.0.0.1:8002" \
   FATHOM_DESIGN_ADVISORY__OPENAPI_PATH="$REPO_ROOT/services/design-advisory/openapi.json" \
   exec .venv/bin/uvicorn fathom_gateway.main:app --host 127.0.0.1 --port 8000) &
GW_PID=$!

cleanup() { echo; echo "=== RCB: stopping services ==="; kill "$DA_PID" "$GW_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Wait for both to answer /healthz.
for svc in "design-advisory http://127.0.0.1:8002/healthz" "gateway http://127.0.0.1:8000/healthz"; do
  name="${svc% *}"; url="${svc#* }"
  for _ in $(seq 1 30); do
    if curl -sf -o /dev/null "$url"; then echo "  $name is up"; break; fi
    sleep 0.5
  done
done

cat <<EOF

=== RCB stack is up ===
  design-advisory : http://127.0.0.1:8002   (FastAPI /docs for raw API)
  gateway         : http://127.0.0.1:8000   (the real demo path, /api/v1/design-advisory/...)

Start the operator UI in another terminal:
  cd $REPO_ROOT/apps/web && pnpm install && pnpm dev
  then open http://localhost:5173/  ("Design Advisory" in the left nav)

Note: the gateway requires FATHOM_PDM__OPENAPI_PATH to exist (it generates
routes from it at startup) but PdM itself need not be running for the RCB
demo -- only design-advisory calls hit a live backend.

Press Ctrl-C to stop both services.
EOF

wait
