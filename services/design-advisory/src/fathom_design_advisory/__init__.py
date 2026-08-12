"""FATHOM Design Advisory service — Redesign Case Builder demo slice.

See docs/demo/redesign-case-builder-demo-plan.md for the whole build plan.
This package holds Paul's foundation: config, the SQLAlchemy data model
(plan §1.3), the async DB wiring, and every read-only (GET) endpoint. The
action endpoints (api/actions.py) and agent endpoints (api/agent.py) are
owned by other contributors and are wired together at integration.
"""
