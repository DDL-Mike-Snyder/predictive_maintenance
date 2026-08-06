#!/bin/bash
# Domino App entrypoint. [SCOPE, demo-only] Runs PdM + the gateway (which
# also serves apps/web's pre-built static files, see platform/gateway
# /src/fathom_gateway/main.py's own AppSettings.static_dir docstring) as
# two processes in ONE container -- same-origin, no separate reverse
# proxy, no CORS. Uses gateway's demo_auto_login mode instead of real
# OIDC/Keycloak (see deps.py's own docstring for why: a Domino-hosted demo
# has no Keycloak reachable from both the gateway and an arbitrary
# browser). SQLite, not the real CloudNativePG Postgres every other
# deployment in this repo uses -- a demo doesn't need RLS.
#
# [REAL, FOUND BY ACTUALLY RUNNING THIS AS A REGISTERED APP, not just in
# an interactive workspace] A Domino App gets its OWN fresh `git clone`
# of the repo in its own container -- NOT the same filesystem as any
# interactive workspace, even one that already has venvs/build output
# sitting in the identical-looking /mnt/code path. This script is
# self-sufficient because of that: it builds both services' venvs from
# scratch every start (no Node.js in this environment either, which is
# why apps/web's static build is a COMMITTED snapshot -- see
# deploy/domino-demo/web-dist/'s own note -- rather than built here).
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$REPO_ROOT/.demo-data"
mkdir -p "$DATA_DIR"

echo "=== FATHOM demo: installing Python 3.12 ==="
uv python install 3.12

echo "=== FATHOM demo: setting up PdM's venv ==="
cd "$REPO_ROOT/services/pdm"
uv venv --python 3.12 .venv
uv pip install -e . --python .venv/bin/python
uv pip install aiosqlite --python .venv/bin/python

echo "=== FATHOM demo: setting up gateway's venv ==="
cd "$REPO_ROOT/platform/gateway"
uv venv --python 3.12 .venv
uv pip install -e . --python .venv/bin/python
uv pip install aiosqlite --python .venv/bin/python

echo "=== FATHOM demo: initializing schemas ==="
PDM_DB_PATH="$DATA_DIR/pdm.db" "$REPO_ROOT/services/pdm/.venv/bin/python" \
  "$REPO_ROOT/deploy/domino-demo/init_pdm_schema.py"
GATEWAY_DB_PATH="$DATA_DIR/gateway.db" "$REPO_ROOT/platform/gateway/.venv/bin/python" \
  "$REPO_ROOT/deploy/domino-demo/init_gateway_schema.py"

echo "=== FATHOM demo: starting PdM (background, port 8001) ==="
(
  cd "$REPO_ROOT/services/pdm"
  export FATHOM_DATABASE__URL="sqlite+aiosqlite:///$DATA_DIR/pdm.db"
  export FATHOM_EVENTS__BROKERS="demo"
  export FATHOM_EVENTS__SCHEMA_REGISTRY="http://demo"
  export FATHOM_EVENTS__CONSUMER_GROUP="fathom-pdm-demo"
  export FATHOM_AUTH__ISSUER="https://demo-issuer"
  export FATHOM_AUTH__JWKS_URL="https://demo-issuer/jwks"
  export FATHOM_AUDIT__BASE_URL="http://demo-audit"
  export FATHOM_REFERENCE_DATA__BASE_URL="http://demo-reference-data"
  export FATHOM_OTEL__ENABLED="false"
  exec .venv/bin/uvicorn fathom_pdm.main:app --host 127.0.0.1 --port 8001
) &

echo "=== FATHOM demo: waiting for PdM health ==="
for _ in $(seq 1 30); do
  curl -sf http://localhost:8001/healthz > /dev/null && break
  sleep 1
done

echo "=== FATHOM demo: seeding demo predictions if none exist ==="
EXISTING=$(curl -s "http://localhost:8001/api/v1/pdm/predictions" -H "X-Fathom-Principal: demo-seed-check" \
  | python3 -c "import json,sys; print(len(json.load(sys.stdin).get('predictions', [])))" 2>/dev/null || echo 0)
if [ "$EXISTING" = "0" ]; then
  PDM_BASE_URL="http://localhost:8001" "$REPO_ROOT/services/pdm/.venv/bin/python" \
    "$REPO_ROOT/services/pdm/scripts/seed_demo_predictions.py"
fi

echo "=== FATHOM demo: starting gateway (foreground, port 8888) ==="
cd "$REPO_ROOT/platform/gateway"
export FATHOM_DATABASE__URL="sqlite+aiosqlite:///$DATA_DIR/gateway.db"
export FATHOM_OIDC__ISSUER="https://demo-issuer/realms/fathom"
export FATHOM_OIDC__CLIENT_ID="demo"
export FATHOM_OIDC__CLIENT_SECRET="demo"
export FATHOM_OIDC__REDIRECT_URI="https://demo.invalid/api/v1/gateway/session/callback"
export FATHOM_SESSION__COOKIE_SIGNING_KEY="demo-signing-key-not-a-real-secret"
export FATHOM_SESSION__DEMO_AUTO_LOGIN="true"
export FATHOM_SESSION__LANDING_URL="/pdm"
export FATHOM_PDM__BASE_URL="http://localhost:8001"
export FATHOM_PDM__OPENAPI_PATH="$REPO_ROOT/services/pdm/openapi.json"
export FATHOM_APP__STATIC_DIR="$REPO_ROOT/deploy/domino-demo/web-dist"
exec .venv/bin/uvicorn fathom_gateway.main:app --host 0.0.0.0 --port 8888
