# FATHOM monorepo — the single entrypoint. CI calls these targets, never inline scripts.
# 09-monorepo-and-conventions.md §6.1: "All pipeline logic lives in make targets and
# tools/ scripts. Workflow YAML does nothing but check out, set up, and call make <target>."
#
# SLUG selects a single service where a target is per-service (e.g. `make test SLUG=pdm`).
# Targets with no SLUG argument are repository-wide reconciliations (09 §6.2 jobs 4, 6, 7, 9).

SHELL := /usr/bin/env bash
SLUG ?=
PY := uv run

.PHONY: help lint typecheck test contract conformance check-event-catalog \
        check-service-events schema-check charts manifests image scaffold

help:
	@echo "make lint | typecheck | test | contract | conformance SLUG=<slug>"
	@echo "make check-event-catalog | check-service-events | schema-check   (repo-wide)"
	@echo "make charts | manifests | image SLUG=<slug>"
	@echo "make scaffold SLUG=<slug>   (produces 09 §4.2's per-service tree)"

# --- job 1: lint & format (09 §6.2) -----------------------------------------
lint:
	uvx ruff check .
	uvx ruff format --check .

# --- job 2: type check --------------------------------------------------------
typecheck:
	uvx mypy --config-file pyproject.toml services/$(SLUG)/src packages

# --- job 3: unit + integration tests -----------------------------------------
test:
	cd services/$(SLUG) && $(PY) pytest tests/unit tests/integration --cov

# --- job 4: contract checks (repo-wide when SLUG unset, else scoped) --------
contract:
	cd services/$(SLUG) && $(PY) python -m $(subst -,_,fathom_$(SLUG)).main --emit-openapi > openapi.json.new
	diff services/$(SLUG)/openapi.json services/$(SLUG)/openapi.json.new
	rm -f services/$(SLUG)/openapi.json.new
	$(PY) python tools/check_openapi.py services/$(SLUG)/openapi.json

# --- job 5: conformance suite -------------------------------------------------
conformance:
	cd services/$(SLUG) && $(PY) pytest tests/conformance

# --- job 6: event-catalog reconciliation (repo-wide, EXISTS) -----------------
check-event-catalog:
	python3 tools/check_event_catalog.py

check-service-events:
	python3 tools/check_service_events.py

# --- job 7: schema compatibility ---------------------------------------------
schema-check:
	cd packages/canonical-schemas && $(PY) python -m fathom_schemas.emit_json_schema --check

# --- job 8: chart & container checks ------------------------------------------
charts:
	helm lint services/$(SLUG)/helm
	helm template services/$(SLUG)/helm | kubeconform --strict
	helm unittest services/$(SLUG)/helm
	hadolint services/$(SLUG)/Dockerfile

# --- job 9: manifest generation ------------------------------------------------
manifests:
	$(PY) python -m fathom_agent_tooling.generator services/$(SLUG)/openapi.json

# --- job 10: build (no push) --------------------------------------------------
image:
	docker build -t fathom-$(SLUG):local services/$(SLUG)

# --- scaffold a new service from the 09 §4.2 skeleton -------------------------
scaffold:
	tools/scaffold_service.sh $(SLUG)
