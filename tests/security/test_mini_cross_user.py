"""D4: User A's token accessing User B's registrations/applications/reviews/
learning records -> 404 (no existence leak)."""
from __future__ import annotations

import pytest

from app import seed as S
from tests import conftest as C
from tests.endpoints import BY_KEY

CASES = [
    ("GET /api/mini/academy/registrations/{registration_id}", str(S.REG_A2), "registration"),
    ("GET /api/mini/academy/applications/{application_id}", str(S.APP_A2), "application"),
    ("GET /api/mini/academy/reviews/{review_id}", str(S.REVIEW_A_ANON), "review"),
    ("GET /api/mini/academy/learning-records/{record_id}", str(S.LEARN_A2), "learning record"),
]


@pytest.mark.parametrize("key,foreign_id,label", CASES, ids=[c[2] for c in CASES])
def test_user_a_cannot_read_user_b_object(client, request, key: str, foreign_id: str, label: str) -> None:
    ep = BY_KEY[key]
    C.record(ep, "D4_mini_cross_user_404", request.node.nodeid)
    path = ep.path.replace("{" + ep.params[0] + "}", foreign_id)
    resp = C.probe(client, request.node.nodeid, ep, headers=C.MEMBER_A1, path=path)
    assert resp.status_code == 404, (
        f"cross-user {label} must be 404, got {resp.status_code}: {resp.text}"
    )


@pytest.mark.parametrize(
    "key,owned_id",
    [
        ("GET /api/mini/academy/registrations/{registration_id}", str(S.REG_A1)),
        ("GET /api/mini/academy/learning-records/{record_id}", str(S.LEARN_A1)),
    ],
)
def test_user_can_read_own_object(client, request, key: str, owned_id: str) -> None:
    """Positive control: the same endpoint returns 200 for the owner."""
    ep = BY_KEY[key]
    C.record(ep, "D4_mini_cross_user_404", request.node.nodeid)
    path = ep.path.replace("{" + ep.params[0] + "}", owned_id)
    resp = C.probe(client, request.node.nodeid, ep, headers=C.MEMBER_A1, path=path)
    assert resp.status_code == 200, f"owner read failed: {resp.text}"
    assert resp.json()["contact_id"] == str(S.C_A1)


@pytest.mark.parametrize(
    "key",
    [
        "GET /api/mini/academy/registrations",
        "GET /api/mini/academy/applications",
        "GET /api/mini/academy/learning-records",
    ],
)
def test_mini_lists_are_user_scoped(client, request, key: str) -> None:
    ep = BY_KEY[key]
    C.record(ep, "D4_mini_cross_user_404", request.node.nodeid)
    a = C.probe(client, request.node.nodeid + "::A", ep, headers=C.MEMBER_A1)
    b = C.probe(client, request.node.nodeid + "::B", ep, headers=C.MEMBER_A2)
    assert a.status_code == b.status_code == 200
    assert all(row["contact_id"] == str(S.C_A1) for row in a.json())
    assert all(row["contact_id"] == str(S.C_A2) for row in b.json())
