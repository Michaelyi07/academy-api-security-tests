"""D3: Membership manager sees only roster rows and learning records for
members they are responsible for."""
from __future__ import annotations

import pytest

from app import seed as S
from tests import conftest as C
from tests.endpoints import BY_KEY

MANAGER_ENDPOINTS = [
    "GET /api/admin/academy/rosters",
    "GET /api/admin/academy/rosters/{roster_id}",
    "GET /api/admin/academy/learning-records",
]


@pytest.mark.parametrize("key", MANAGER_ENDPOINTS)
def test_manager_sees_only_owned_rows(client, request, key: str) -> None:
    ep = BY_KEY[key]
    C.record(ep, "D3_manager_scope", request.node.nodeid)
    resp = C.probe(client, request.node.nodeid, ep, headers=C.MANAGER_A)
    assert resp.status_code == 200, resp.text

    if "{roster_id}" in key:
        rows = [resp.json()]
    else:
        rows = resp.json()
    assert rows, "seed must contain manager-owned rows"
    for row in rows:
        assert row["owner_manager_id"] == str(S.U_MANAGER_A), (
            f"manager saw a row owned by another manager: {row}"
        )
        assert row["contact_id"] == str(S.C_A1), f"manager saw a foreign member row: {row}"


def test_manager_cannot_read_foreign_roster_by_id(client, request) -> None:
    ep = BY_KEY["GET /api/admin/academy/rosters/{roster_id}"]
    C.record(ep, "D3_manager_scope", request.node.nodeid)
    path = ep.path.replace("{roster_id}", str(S.ROSTER_A2))  # owned by employee A
    resp = C.probe(client, request.node.nodeid, ep, headers=C.MANAGER_A, path=path)
    assert resp.status_code == 404, f"foreign roster must be 404, got {resp.status_code}: {resp.text}"


def test_club_admin_sees_all_site_rows(client, request) -> None:
    """Control case: a club admin is not manager-scoped and sees both rows."""
    ep = BY_KEY["GET /api/admin/academy/rosters"]
    C.record(ep, "D3_manager_scope", request.node.nodeid)
    resp = C.probe(client, request.node.nodeid, ep, headers=C.CLUB_A_ADMIN)
    assert resp.status_code == 200, resp.text
    assert {r["contact_id"] for r in resp.json()} == {str(S.C_A1), str(S.C_A2)}
