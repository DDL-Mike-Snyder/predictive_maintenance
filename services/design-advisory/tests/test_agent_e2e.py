#!/usr/bin/env python3
"""Michael's own "verify it for real" harness
(`docs/demo/redesign-case-builder-demo-plan.md`, "Michael" section, task 4
/ Definition of Done). Not part of the real design-advisory service --
starts `stub_upstream.py` (a test double for Paul's/Marc's contract,
seeded with §1.5's five candidates) and `agent_app_for_test.py` (Michael's
real `api/agent.py` router, mounted standalone) as two real subprocesses
talking over real sockets, then drives `qualify`/`draft` against all five
seed candidates and checks the results against §1.5's table exactly --
the same discipline this repo's own `CLAUDE.md` insists on ("verified by
actually running it... not just 'the code compiles'").

Run: `python3 services/design-advisory/tests/test_agent_e2e.py`
(needs `fastapi`, `httpx`, `uvicorn`, `pydantic` importable -- Paul's real
`pyproject.toml` will provide these; this script has no other dependency
on Paul's or Marc's actual code, only on the stub above).

This is a standalone CLI verification script, not a `pytest` suite run in
CI (09 §4.8's "all output is structlog" convention governs *service*
code, not a one-off runner meant to be read on a terminal the way `curl`
output would be) -- `print()` and a boolean-flagged subprocess launch are
both the right tool here, not a lint violation to work around.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
STUB_PORT = 8002
AGENT_PORT = 8102
STUB_URL = f"http://127.0.0.1:{STUB_PORT}"
AGENT_URL = f"http://127.0.0.1:{AGENT_PORT}"

# candidate NIIN -> expected outcome, per §1.5 exactly
EXPECTED = {
    "013456789": {
        "outcome": "gate_pass",
        "failed": [],
        "stance": "redesign_warranted_for_evaluation",
    },
    "013456790": {"outcome": "gate_fail", "failed": ["G3_completeness_floor"], "stance": None},
    "013456791": {"outcome": "gate_fail", "failed": ["G2_priority_floor"], "stance": None},
    "013456792": {"outcome": "gate_fail", "failed": ["G5_evidentiary_floor"], "stance": None},
    "013456793": {"outcome": "gate_pass", "failed": [], "stance": "monitor_and_reassess"},
}

failures: list[str] = []


def check(label: str, *, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    suffix = f" -- {detail}" if detail and not condition else ""
    print(f"[{status}] {label}{suffix}")  # noqa: T201 -- this IS the tool's output, not debug noise
    if not condition:
        failures.append(f"{label} -- {detail}")


def wait_for(url: str, timeout_s: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_exc: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=1.0)
            if response.status_code == httpx.codes.OK:
                return
        except httpx.HTTPError as exc:
            last_exc = exc
        time.sleep(0.25)
    raise RuntimeError(f"{url} never became healthy") from last_exc


def _start_uvicorn(module_app: str, port: int) -> subprocess.Popen:
    # Fixed, in-repo argv only (module name, port, log level) -- never
    # request/user input, same discipline as this repo's own
    # tests/integration S603 per-file-ignore for subprocess argv.
    argv = [
        sys.executable,
        "-m",
        "uvicorn",
        module_app,
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    return subprocess.Popen(argv, cwd=HERE)  # noqa: S603


def _run_qualify(candidate_id: str) -> dict:
    url = f"{AGENT_URL}/api/v1/design-advisory/agent/candidates/{candidate_id}/qualify"
    response = httpx.post(url, timeout=10.0)
    detail = response.text
    check("qualify returns 200", condition=response.status_code == httpx.codes.OK, detail=detail)
    return response.json()


def _run_draft(candidate_id: str) -> dict:
    create = httpx.post(
        f"{STUB_URL}/api/v1/design-advisory/redesign-cases",
        json={"candidate_id": candidate_id},
        timeout=10.0,
    )
    check("draft case created", condition=create.status_code == httpx.codes.OK, detail=create.text)
    case_id = create.json()["case_id"]

    url = f"{AGENT_URL}/api/v1/design-advisory/agent/cases/{case_id}/draft"
    draft_resp = httpx.post(url, timeout=10.0)
    detail = draft_resp.text
    check("draft returns 200", condition=draft_resp.status_code == httpx.codes.OK, detail=detail)
    return draft_resp.json()


def _check_no_invented_dollar_figures(candidate_id: str, case: dict) -> None:
    # 42 §5.6: the narrative must never state a dollar figure that isn't a
    # carried one. `compose_narrative` only ever sees the *parametric*
    # estimate (the dependency_rollup cost_estimate doesn't exist until
    # Marc's `assemble` creates it, one step after the narrative is
    # composed) -- so the parametric estimate is the figure to check the
    # narrative against, not the rollup the assembled case ends up
    # pointing at.
    parametric_rows = httpx.get(
        f"{STUB_URL}/api/v1/design-advisory/cost-estimates",
        params={"candidate_id": candidate_id, "method": "parametric"},
    ).json()
    expected_dollar = f"${parametric_rows[0]['point_estimate_usd']:,.0f}"
    body_text = " ".join(section.get("body", "") for section in case.get("narrative_sections", []))
    dollar_figures = set(re.findall(r"\$[\d,]+", body_text))
    check(
        "every dollar figure in narrative matches the carried parametric estimate",
        condition=dollar_figures <= {expected_dollar},
        detail=f"narrative contains {dollar_figures}, carried figure is {expected_dollar!r}",
    )


def main() -> int:
    procs = [
        _start_uvicorn("stub_upstream:app", STUB_PORT),
        _start_uvicorn("agent_app_for_test:app", AGENT_PORT),
    ]
    try:
        wait_for(f"{STUB_URL}/healthz")
        wait_for(f"{AGENT_URL}/healthz")

        candidates = httpx.get(f"{STUB_URL}/api/v1/design-advisory/redesign-candidates").json()
        by_niin = {c["niin"]: c for c in candidates}
        check(
            "stub seeded exactly five candidates",
            condition=len(candidates) == 5,
            detail=f"got {len(candidates)}",
        )

        drafted: dict[str, str] = {}
        for niin, expected in EXPECTED.items():
            candidate = by_niin.get(niin)
            check(f"candidate {niin} exists in stub", condition=candidate is not None)
            if candidate is None:
                continue
            candidate_id = candidate["candidate_id"]

            body = _run_qualify(candidate_id)
            check(
                f"{niin} outcome == {expected['outcome']!r}",
                condition=body.get("outcome") == expected["outcome"],
                detail=f"got {body.get('outcome')!r}",
            )
            check(
                f"{niin} failed_conditions == {expected['failed']!r}",
                condition=body.get("failed_conditions") == expected["failed"],
                detail=f"got {body.get('failed_conditions')!r}",
            )
            check(
                f"{niin} derived_evidence_gaps is non-empty",
                condition=bool(body.get("derived_evidence_gaps")),
                detail="must never be empty (28 §3.6 / 42 §1.2 B4)",
            )

            if expected["outcome"] == "gate_pass":
                drafted[niin] = candidate_id

        for niin, candidate_id in drafted.items():
            case = _run_draft(candidate_id)
            expected_stance = EXPECTED[niin]["stance"]
            check(
                f"{niin} suggested stance == {expected_stance!r}",
                condition=case.get("recommendation_stance") == expected_stance,
                detail=f"got {case.get('recommendation_stance')!r}",
            )
            check(
                f"{niin} case_status == 'assembled'",
                condition=case.get("case_status") == "assembled",
            )
            check(
                f"{niin} recommendation_limitations non-empty",
                condition=bool(case.get("recommendation_limitations")),
            )
            check(
                f"{niin} recommendation_evidence_gaps non-empty",
                condition=bool(case.get("recommendation_evidence_gaps")),
            )
            check(
                f"{niin} narrative_sections non-empty",
                condition=bool(case.get("narrative_sections")),
            )
            _check_no_invented_dollar_figures(candidate_id, case)

        if failures:
            print("\n=== FAILURES ===")  # noqa: T201
            for failure in failures:
                print(f" - {failure}")  # noqa: T201
            return 1
        print("\nAll checks passed.")  # noqa: T201
        return 0
    finally:
        for proc in procs:
            proc.terminate()
        for proc in procs:
            proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
