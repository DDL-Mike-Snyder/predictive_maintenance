#!/bin/bash
# Domino App entrypoint for the Redesign Case Builder demo
# (docs/demo/redesign-case-builder-demo-plan.md). A SEPARATE App/entryPoint
# from the existing `app.sh` (fathom-pdm-demo) -- this script only starts
# `services/design-advisory` (Paul's skeleton + Marc's action endpoints),
# on its own port, in its own App, so it never touches or conflicts with
# the already-deployed fathom-pdm-demo App.
#
# Same discipline as the root `app.sh`'s own header comment: a Domino App
# gets its OWN fresh `git clone` in its own container, so this script
# builds design-advisory's venv from scratch every start.
#
# No UI/gateway/agent is deployed here (Bella/Amanda/Michael's sections of
# the demo plan aren't built) -- FastAPI's own interactive docs at `/docs`
# are the click-through surface for this pass: every one of Marc's five
# action endpoints, plus Paul's reads, are real, callable, and backed by
# the real seeded data from scripts/seed_demo_data.py.
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA_DIR="$REPO_ROOT/.demo-data"
mkdir -p "$DATA_DIR"

echo "=== RCB demo: installing Python 3.12 ==="
uv python install 3.12

echo "=== RCB demo: setting up design-advisory's venv ==="
cd "$REPO_ROOT/services/design-advisory"
uv venv --python 3.12 .venv
uv pip install -e . --python .venv/bin/python

export DESIGN_ADVISORY_DATABASE_URL="sqlite+aiosqlite:///$DATA_DIR/design_advisory.db"

echo "=== RCB demo: seeding the five demo candidates (idempotent) ==="
.venv/bin/python scripts/seed_demo_data.py

echo "=== RCB demo: starting design-advisory (foreground, port 8888) ==="
exec .venv/bin/uvicorn fathom_design_advisory.main:app --host 0.0.0.0 --port 8888
