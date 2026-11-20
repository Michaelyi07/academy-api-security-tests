"""D6: Anonymous reviews must not expose reviewer information in any mini
endpoint (list, detail, or newly created response)."""
from __future__ import annotations

import pytest

from app import seed as S
from tests import conftest as C
from tests.endpoints import BY_KEY

IDENTITY_KEYS = ("contact_id", "reviewer_name", "reviewer_mobile", "mobile", "reviewer")


def _assert_no_reviewer(data: object, *, must_be_anonymous: bool = False) -> None:
    import json

    blob = json.dumps(data, ensure_ascii=False)
    for key in IDENTITY_KEYS:
        assert f'"{key}"' not in blob, f"anonymous review leaked reviewer field {key}: {blob[:400]}"
    if must_be_anonymous:
        if isinstance(data, dict):
            assert data["is_anonymous"] is True
        else:
            assert any(r["is_anonymous"] for r in data)


@pytest.mark.parametrize(
    "key",
    ["GET /api/mini/academy/reviews", "GET /api/mini/academy/reviews/{review_id}"],
)
def test_anonymous_review_has_no_reviewer(client, request, key: str) -> None:
    ep = BY_KEY[key]
    C.record(ep, "D6_anonymous_reviewer_privacy", request.node.nodeid)
    is_detail = "{review_id}" in key
    path = ep.path.replace("{review_id}", str(S.REVIEW_A_ANON)) if is_detail else None
    # The anonymous review belongs to member A2; detail is owner-scoped, so use A2.
    headers = C.MEMBER_A2 if is_detail else C.MEMBER_A1
    resp = C.probe(client, request.node.nodeid, ep, headers=headers, path=path)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    rows = data if isinstance(data, list) else [data]
    anon = [r for r in rows if r["id"] == str(S.REVIEW_A_ANON)]
    assert len(anon) == 1, "seeded anonymous review missing from response"
    _assert_no_reviewer(anon[0], must_be_anonymous=True)


def test_named_review_still_has_reviewer(client, request) -> None:
    """Control: non-anonymous reviews are unaffected by the privacy rule."""
    ep = BY_KEY["GET /api/mini/academy/reviews"]
    C.record(ep, "D6_anonymous_reviewer_privacy", request.node.nodeid)
    resp = C.probe(client, request.node.nodeid, ep, headers=C.MEMBER_A1)
    rows = resp.json()
    named = [r for r in rows if r["id"] == str(S.REVIEW_A_PLAIN)]
    assert named and "reviewer_name" in named[0], "named review must keep reviewer info"


def test_created_anonymous_review_hides_reviewer(client, request) -> None:
    ep = BY_KEY["POST /api/mini/academy/reviews"]
    C.record(ep, "D6_anonymous_reviewer_privacy", request.node.nodeid)
    body = {"course_id": str(S.COURSE_A), "rating": 5, "comment": "anon", "is_anonymous": True}
    resp = C.probe(client, request.node.nodeid, ep, headers=C.MEMBER_A1, json_body=body)
    assert resp.status_code == 201, resp.text
    _assert_no_reviewer(resp.json(), must_be_anonymous=True)
