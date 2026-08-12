# Michael's own verification harness -- not Paul's or Marc's real code

This directory exists purely to verify `api/agent.py` /
`agent/derive.py` / `agent/narrative.py` (Michael's owned files per
`docs/demo/redesign-case-builder-demo-plan.md`) against something real
and running, per the demo build plan's own instruction:

> You do not need Paul's or Marc's code to start. Build against a tiny
> local stub server that returns the exact JSON shapes from §1.3/§1.5...
> so you can develop and test your orchestration logic in isolation.

- `stub_upstream.py` -- a small, real (in-memory, no SQLite)
  implementation of Paul's `api/reads.py` + Marc's `api/actions.py`
  contract, seeded with exactly the five candidates from §1.5, including
  real G1-G6 gate logic (§1.4) and real assemble/create-case logic
  (Marc's spec). **Not the real service** -- delete this whole directory
  once Paul's and Marc's actual `reads.py`/`actions.py` exist, and
  re-point `test_agent_e2e.py` (or a real integration test) at those
  instead.
- `agent_app_for_test.py` -- mounts the real `api/agent.py` router into a
  throwaway `FastAPI()` app, standing in for the `main.py`/
  `api/__init__.py` wiring that Paul and Amanda own.
- `test_agent_e2e.py` -- starts both of the above as real subprocesses on
  real sockets (ports 8002 / 8102) and drives `qualify`/`draft` against
  all five seed candidates, checking outcomes against §1.5's table
  exactly, plus a handful of unhappy paths (nonexistent candidate, draft
  against a failed gate, a repeat draft on an already-assembled case).

Run it directly:

```bash
python3 services/design-advisory/tests/test_agent_e2e.py
```

Needs `fastapi`, `httpx`, `uvicorn`, `pydantic` importable (Paul's real
`pyproject.toml` will provide these once it exists; in the meantime,
`pip install fastapi httpx "uvicorn[standard]" pydantic` is enough).

**Result of the last run**: all 32 checks pass, run under a real Python
3.12 virtualenv (`uv venv --python 3.12`) to match this repo's actual
`requires-python = ">=3.12"` convention (every other service's
`pyproject.toml` pins the same) -- not the ambient Python 3.10 this
sandbox happened to default to. Plus three unhappy-path spot checks run
separately by hand: 404 on an unknown candidate, 409 refusing to draft a
gate-failed candidate, and 409 -- not a 500 or a silent overwrite -- on a
repeat draft call against an already-assembled case.

Also `ruff check`/`ruff format --check` clean (repo root config) across
`api/agent.py`, `agent/derive.py`, `agent/narrative.py`, and this whole
`tests/` directory, matching this repo's own established discipline
(`CLAUDE.md`'s ruff-cleanup entries) of not letting lint debt silently
accumulate on new code.

**[ASSUMPTION, demo-only]** `stub_upstream.py` implements three
list-by-`candidate_id` read filters that §1.3/§1.6 of the build plan
don't explicitly give Paul's `reads.py` (`GET /impact-snapshots
?candidate_id=`, `GET /cost-estimates?candidate_id=&method=`,
`GET /gate-decisions?candidate_id=`) -- see `api/agent.py`'s own module
docstring for why `qualify`/`draft` need them. If Paul's real service
doesn't grow these, add them there; this stub existing is not a
substitute for that.
