"""Shared fixtures, request instrumentation and report generation.

Real runtime: PostgreSQL (env ACADEMY_DATABASE_URL). No SQLite fallback.
Reports are regenerated on every run from actual test execution:
  reports/coverage_matrix.md - endpoint x dimension
  reports/issue_list.md      - failures with reproduction steps
"""
from __future__ import annotations

import json
import os
import sys
import traceback
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from _pytest.outcomes import Skipped
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import Base, SessionLocal, engine
from app.main import create_app
from app import models  # noqa: F401  register tables on metadata
from app import seed as S

from .endpoints import DIMENSIONS, ENDPOINTS, Endpoint

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# --- execution ledger ------------------------------------------------------
COVERAGE: dict[str, set[str]] = defaultdict(set)
REQUESTS: dict[str, list[dict[str, Any]]] = defaultdict(list)
ISSUES: list[dict[str, Any]] = []
NODE_ENDPOINT: dict[str, str] = {}


def record(endpoint: Endpoint | str, dimension: str, nodeid: str = "") -> None:
    key = endpoint.key if isinstance(endpoint, Endpoint) else endpoint
    COVERAGE[key].add(dimension)
    if nodeid:
        NODE_ENDPOINT[nodeid] = key


def note_request(
    nodeid: str,
    method: str,
    url: str,
    headers: dict[str, Any],
    body: Any,
    status: int,
    response: Any,
) -> None:
    REQUESTS[nodeid].append(
        {
            "method": method,
            "url": url,
            "headers": {k: v for k, v in headers.items()},
            "body": body,
            "status": status,
            "response": _shorten(response),
        }
    )


def _shorten(value: Any, limit: int = 1200) -> Any:
    text = json.dumps(value, default=str, ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "...(truncated)"


# --- pytest hooks ----------------------------------------------------------
def pytest_runtest_setup(item: pytest.Item) -> None:
    REQUESTS[item.nodeid].clear()


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    # pytest 9: CallInfo.result raises when the test failed; read excinfo instead.
    if call.when != "call" or call.excinfo is None:
        return
    if call.excinfo.errisinstance(Skipped):
        return
    nodeid = item.nodeid
    endpoint_key = NODE_ENDPOINT.get(nodeid, "")
    ep = (
        __import__("tests.endpoints", fromlist=["BY_KEY"]).BY_KEY.get(endpoint_key)
        if endpoint_key
        else None
    )
    exc = str(call.excinfo.getrepr(style="short"))
    ISSUES.append(
        {
            "nodeid": nodeid,
            "endpoint": endpoint_key,
            "dimension": ", ".join(sorted(COVERAGE.get(endpoint_key, set()))) or "unknown",
            "error": str(exc)[-1500:],
            "requests": REQUESTS.get(nodeid, []),
            "seed_state": "reset_and_seed() applied at test start (fictional dataset)",
            "expected": "see test assertion; brief acceptance criteria",
            "actual": "see request/response rows above",
        }
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    write_coverage_matrix()
    write_issue_list()
    write_run_meta(exitstatus)


# --- fixtures --------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _schema() -> None:
    Base.metadata.create_all(engine)


@pytest.fixture()
def db() -> Session:
    s = SessionLocal()
    try:
        S.reset_and_seed(s)
        yield s
    finally:
        s.close()


@pytest.fixture()
def client(db: Session) -> TestClient:
    app = create_app()

    # Use the same session as tests so forged-body assertions see committed rows.
    from app.db import get_db

    def _override() -> Any:
        yield db

    app.dependency_overrides[get_db] = _override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# --- identity helpers ------------------------------------------------------
def admin_headers(
    user_id: uuid.UUID,
    roles: list[str],
    *,
    site_id: uuid.UUID = S.SITE_A,
    org_id: uuid.UUID = S.ORG,
    contact_id: uuid.UUID | None = None,
) -> dict[str, str]:
    h = {
        "X-Org-Id": str(org_id),
        "X-Site-Id": str(site_id),
        "X-User-Id": str(user_id),
        "X-User-Roles": ",".join(roles),
    }
    if contact_id:
        h["X-Contact-Id"] = str(contact_id)
    return h


PLATFORM = admin_headers(S.U_PLATFORM_ADMIN, ["platform_admin"])
ORG_ADMIN = admin_headers(S.U_ORG_ADMIN, ["org_admin"])
CLUB_A_ADMIN = admin_headers(S.U_CLUB_ADMIN_A, ["club_admin"])
EMPLOYEE_A = admin_headers(S.U_EMPLOYEE_A, ["club_employee"])
MANAGER_A = admin_headers(S.U_MANAGER_A, ["membership_manager"])
EMPLOYEE_B = admin_headers(S.U_EMPLOYEE_B, ["club_employee"], site_id=S.SITE_B)

# Mini users always carry exactly one role: member; contact_id identifies the user.
MEMBER_A1 = admin_headers(
    S.U_MEMBER_A1, ["member"], contact_id=S.C_A1
)
MEMBER_A2 = admin_headers(
    S.U_MEMBER_A2, ["member"], contact_id=S.C_A2
)
MEMBER_B1 = admin_headers(
    S.U_MEMBER_B1, ["member"], site_id=S.SITE_B, contact_id=S.C_B1
)
ANON: dict[str, str] = {}


def probe(
    client: TestClient,
    nodeid: str,
    endpoint: Endpoint,
    *,
    headers: dict[str, str] | None = None,
    json_body: Any = None,
    path: str | None = None,
    method: str | None = None,
) -> Any:
    """Execute one HTTP request and instrument it for reproduction steps."""
    url = path or endpoint.sample
    verb = method or endpoint.method
    kw: dict[str, Any] = {"headers": headers or {}}
    if json_body is not None:
        kw["json"] = json_body
    resp = client.request(verb, url, **kw)
    try:
        payload = resp.json()
    except Exception:
        payload = resp.text
    note_request(nodeid, verb, url, kw["headers"], json_body, resp.status_code, payload)
    return resp


# --- report writers --------------------------------------------------------
def write_coverage_matrix() -> Path:
    lines = [
        "# Academy API coverage matrix (endpoint x test-case dimension)",
        "",
        "Generated from live pytest execution. `PASS` = at least one executed test case",
        "for that endpoint x dimension; `-` = not applicable / not executed.",
        "",
        "| Endpoint | Side | " + " | ".join(DIMENSIONS) + " | Dims |",
        "|---|---|" + "|".join(["---"] * len(DIMENSIONS)) + "|---|",
    ]
    total_min = 99
    for e in ENDPOINTS:
        dims = COVERAGE.get(e.key, set())
        total_min = min(total_min, len(dims))
        cells = ["PASS" if d in dims else "-" for d in DIMENSIONS]
        lines.append(f"| `{e.method} {e.path}` | {e.side} | " + " | ".join(cells) + f" | {len(dims)} |")
    lines += [
        "",
        f"- Total academy endpoints: **{len(ENDPOINTS)}** "
        f"(admin {sum(1 for e in ENDPOINTS if e.side == 'admin')}, "
        f"mini {sum(1 for e in ENDPOINTS if e.side == 'mini')})",
        f"- Minimum dimensions per endpoint: **{total_min if total_min != 99 else 0}** "
        "(acceptance requires >= 2)",
        f"- GET endpoints (phone-scan applicable): **{sum(1 for e in ENDPOINTS if e.method == 'GET')}**",
        f"- Write endpoints (POST/PATCH/DELETE, phone-scan applicable): "
        f"**{sum(1 for e in ENDPOINTS if e.method != 'GET')}**",
        f"- Endpoints D7 executes on: **{len(ENDPOINTS)}** "
        f"({sum(1 for e in ENDPOINTS if '/reveal-mobile' not in e.path)} "
        f"assert no mobile; {sum(1 for e in ENDPOINTS if '/reveal-mobile' in e.path)} "
        f"reveal-mobile assert a mobile IS present)",
        "",
    ]
    path = REPORTS / "coverage_matrix.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_issue_list() -> Path:
    lines = [
        "# Issues found",
        "",
        f"Run at {datetime.now(timezone.utc).isoformat()}. "
        f"Total failed cases: **{len(ISSUES)}**.",
        "",
    ]
    if not ISSUES:
        lines += [
            "No failing cases in this run. The suite is regression-checked:",
            "the seeded-leak detector self-test (`tests/test_detector_selftest.py`)",
            "proves the phone scanner detects a deliberately injected plaintext",
            "mobile, so a green run is not a false negative.",
            "",
        ]
    for i, issue in enumerate(ISSUES, 1):
        lines += [
            f"## ISSUE-{i:03d} — {issue['endpoint'] or issue['nodeid']}",
            "",
            f"- Test: `{issue['nodeid']}`",
            f"- Dimension: {issue['dimension']}",
            f"- Seed state: {issue['seed_state']}",
            f"- Expected: {issue['expected']}",
            f"- Actual: {issue['actual']}",
            "- Error:",
            "```text",
            issue["error"],
            "```",
            "- Reproduction steps (executed requests, in order):",
        ]
        for j, r in enumerate(issue["requests"], 1):
            lines += [
                f"  {j}. `{r['method']} {r['url']}`",
                f"     headers={r['headers']} body={r['body']} -> {r['status']} {r['response']}",
            ]
        lines.append("")
    path = REPORTS / "issue_list.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_run_meta(exitstatus: int) -> None:
    import platform

    data = {
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "exit_status": int(exitstatus),
        "python": sys.version,
        "platform": platform.platform(),
        "database_url_env": os.environ.get("ACADEMY_DATABASE_URL", "(default: local PG16)"),
        "endpoints": len(ENDPOINTS),
        "get_endpoints": sum(1 for e in ENDPOINTS if e.method == "GET"),
        "write_endpoints": sum(1 for e in ENDPOINTS if e.method != "GET"),
        "d7_dimension_endpoints": len(ENDPOINTS),
        "d7_assert_absent": sum(1 for e in ENDPOINTS if "/reveal-mobile" not in e.path),
        "d7_reveal_assert_present": sum(1 for e in ENDPOINTS if "/reveal-mobile" in e.path),
        "issue_count": len(ISSUES),
    }
    (REPORTS / "run_meta.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
