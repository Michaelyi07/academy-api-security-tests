"""D1: 6 role types x 11 academy permission points -> 403 when unauthorized.

For each admin endpoint we enumerate all 6 roles. Expected result is derived
from the IAM grant matrix in app.iam (the same matrix the API enforces).
Roles without the permission must receive 403; roles with it must not receive
403 (200/201/204, or 404 when the object is out of that role's data scope).
"""
from __future__ import annotations

import pytest

from app import seed as S
from app.iam import PERMISSION_POINTS, ROLES, grants_for
from tests import conftest as C
from tests.endpoints import ADMIN_ENDPOINTS, Endpoint

CASES = [
    (ep, role)
    for ep in ADMIN_ENDPOINTS
    for role in ROLES
]

_IDENTITY = {
    "platform_admin": C.PLATFORM,
    "org_admin": C.ORG_ADMIN,
    "club_admin": C.CLUB_A_ADMIN,
    "club_employee": C.EMPLOYEE_A,
    "membership_manager": C.MANAGER_A,
    "member": C.admin_headers(S.U_MEMBER_A1, ["member"]),
}


def _body_for(ep: Endpoint) -> dict | None:
    """Minimal valid body for write endpoints so permission is the variable."""
    if ep.method == "GET" or ep.method == "DELETE":
        return None
    if ep.path.endswith("/courses"):
        return {"title": "Permission Probe Course"}
    if ep.path.endswith("/courses/{course_id}"):
        return {"title": "Permission Probe Course"}
    if ep.path.endswith("/sessions"):
        return {"course_id": str(S.COURSE_A), "title": "Permission Probe Session"}
    if ep.path.endswith("/rosters"):
        return {"session_id": str(S.SESSION_A), "contact_id": str(S.C_A1), "note": "probe"}
    return None


@pytest.mark.parametrize("ep,role", CASES, ids=[f"{e.key}|{r}" for e, r in CASES])
def test_role_permission(client, request, ep: Endpoint, role: str) -> None:
    C.record(ep, "D1_role_permission", request.node.nodeid)
    assert ep.perm in PERMISSION_POINTS, f"endpoint {ep.key} has no mapped permission point"

    body = _body_for(ep)
    resp = C.probe(client, request.node.nodeid, ep, headers=_IDENTITY[role], json_body=body)
    allowed = ep.perm in grants_for(role)
    if allowed:
        assert resp.status_code != 403, (
            f"role={role} should hold {ep.perm} but got 403: {resp.text}"
        )
        assert resp.status_code in (200, 201, 204), (
            f"role={role} permitted but returned {resp.status_code}: {resp.text}"
        )
    else:
        assert resp.status_code == 403, (
            f"role={role} lacks {ep.perm}, expected 403, got {resp.status_code}: {resp.text}"
        )


def test_matrix_is_complete() -> None:
    """Every one of the 11 permission points is exercised by at least one case."""
    covered = {ep.perm for ep in ADMIN_ENDPOINTS if ep.perm}
    assert set(PERMISSION_POINTS) == covered, (
        f"uncovered permission points: {set(PERMISSION_POINTS) - covered}"
    )
    assert len(ROLES) == 6
    assert len(PERMISSION_POINTS) == 11
