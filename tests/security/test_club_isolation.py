"""D2: Club A identity accessing Club B courses/sessions/rosters/reviews -> 404.

404 (not 403) is asserted to avoid existence leaks: a cross-club actor must not
be able to distinguish 'object exists in another club' from 'object missing'.
Both admin-side and mini-side object endpoints are covered.
"""
from __future__ import annotations

import pytest

from app import seed as S
from tests import conftest as C
from tests.endpoints import BY_KEY, Endpoint

CASES = [
    ("GET /api/admin/academy/courses/{course_id}", str(S.COURSE_B), "course"),
    ("GET /api/admin/academy/sessions/{session_id}", str(S.SESSION_B), "session"),
    ("GET /api/admin/academy/rosters/{roster_id}", str(S.ROSTER_B1), "roster"),
    ("GET /api/mini/academy/reviews/{review_id}", str(S.REVIEW_B_PLAIN), "review"),
    ("GET /api/mini/academy/courses/{course_id}", str(S.COURSE_B), "course"),
    ("GET /api/mini/academy/sessions/{session_id}", str(S.SESSION_B), "session"),
]


@pytest.mark.parametrize(
    "key,object_id,owner_headers",
    [
        ("GET /api/admin/academy/rosters/{roster_id}", str(S.ROSTER_B1), C.EMPLOYEE_B),
        ("GET /api/mini/academy/reviews/{review_id}", str(S.REVIEW_B_PLAIN), C.MEMBER_B1),
    ],
    ids=["roster", "review"],
)
def test_foreign_roster_and_review_exist_for_club_b(client, request, key: str,
                                                    object_id: str, owner_headers: dict) -> None:
    """Precondition: the foreign ids are REAL club-B objects, not random UUIDs.
    A 404 for club A therefore proves isolation, not a missing object."""
    ep: Endpoint = BY_KEY[key]
    path = ep.path.replace("{" + ep.params[0] + "}", object_id)
    resp = C.probe(client, request.node.nodeid, ep, headers=owner_headers, path=path)
    assert resp.status_code == 200, f"seed object must exist for its own club: {resp.text}"
    assert resp.json()["site_id"] == str(S.SITE_B)
    assert resp.json()["id"] == object_id


@pytest.mark.parametrize("key,foreign_id,resource", CASES, ids=[c[0].split("/")[-2] + c[2] for c in CASES])
def test_cross_club_object_returns_404(client, request, key: str, foreign_id: str, resource: str) -> None:
    ep: Endpoint = BY_KEY[key]
    C.record(ep, "D2_club_isolation_404", request.node.nodeid)
    path = ep.path.replace("{" + ep.params[0] + "}", foreign_id)

    # Club A EMPLOYEE (admin endpoints) and Club A member (mini endpoints) —
    # the brief says "A-club employee accessing B-club objects -> 404".
    headers = C.EMPLOYEE_A if ep.side == "admin" else C.MEMBER_A1
    resp = C.probe(client, request.node.nodeid, ep, headers=headers, path=path)
    assert resp.status_code == 404, (
        f"cross-club {resource} access must be 404, got {resp.status_code}: {resp.text}"
    )
    assert "not_found" in resp.text, "404 must not reveal why the object was denied"


@pytest.mark.parametrize(
    "key",
    [
        "GET /api/admin/academy/courses",
        "GET /api/admin/academy/sessions",
        "GET /api/admin/academy/rosters",
        "GET /api/admin/academy/reviews",
    ],
)
def test_cross_club_list_excludes_foreign_site(client, request, key: str) -> None:
    ep = BY_KEY[key]
    C.record(ep, "D2_club_isolation_404", request.node.nodeid)
    own = C.probe(client, request.node.nodeid, ep, headers=C.CLUB_A_ADMIN)
    foreign = C.probe(client, request.node.nodeid, ep, headers=C.EMPLOYEE_B)
    assert own.status_code == 200 and foreign.status_code == 200
    assert all(x["site_id"] == str(S.SITE_A) for x in own.json())
    assert all(x["site_id"] == str(S.SITE_B) for x in foreign.json())
    own_ids = {x["id"] for x in own.json()}
    foreign_ids = {x["id"] for x in foreign.json()}
    assert not (own_ids & foreign_ids), "club A list leaked club B objects"
