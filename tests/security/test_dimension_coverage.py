"""Extra cases to guarantee every academy endpoint has >= 2 executed dimensions
(acceptance criterion 2). Each case exercises a real security property, not a
matrix-filling no-op:

- write endpoints: forged URL id / forged body has no effect (D5)
- mini GET endpoints without a natural scope case: cross-club isolation (D2)
  or reveal-mobile ownership (D4)
- mini POST endpoints: cross-user forgery is neutralised (D4)
"""
from __future__ import annotations

from app import seed as S
from tests import conftest as C
from tests.endpoints import BY_KEY


def test_patch_course_forged_fields(client, request) -> None:
    ep = BY_KEY["PATCH /api/admin/academy/courses/{course_id}"]
    C.record(ep, "D5_forgery_neutral", request.node.nodeid)
    body = {"title": "Forged Edit", "site_id": str(S.SITE_B), "org_id": "10000000-0000-4000-8000-000000000099"}
    resp = C.probe(client, request.node.nodeid, ep, headers=C.CLUB_A_ADMIN, json_body=body)
    assert resp.status_code == 200, resp.text
    assert resp.json()["site_id"] == str(S.SITE_A)


def test_delete_review_forged_id(client, request) -> None:
    ep = BY_KEY["DELETE /api/admin/academy/reviews/{review_id}"]
    C.record(ep, "D5_forgery_neutral", request.node.nodeid)
    # Forged foreign-site id -> 404; own-site id -> 204.
    # Use a REAL club-B review (seeded), so 404 proves scope isolation rather
    # than merely "id does not exist".
    foreign = ep.path.replace("{review_id}", str(S.REVIEW_B_PLAIN))
    r1 = C.probe(client, request.node.nodeid + "::forged", ep, headers=C.CLUB_A_ADMIN, path=foreign)
    assert r1.status_code == 404, r1.text
    r2 = C.probe(client, request.node.nodeid + "::own", ep, headers=C.CLUB_A_ADMIN)
    assert r2.status_code == 204, r2.text


def test_mini_courses_cross_club(client, request) -> None:
    ep = BY_KEY["GET /api/mini/academy/courses"]
    C.record(ep, "D2_club_isolation_404", request.node.nodeid)
    mine = C.probe(client, request.node.nodeid + "::A", ep, headers=C.MEMBER_A1)
    theirs = C.probe(client, request.node.nodeid + "::B", ep, headers=C.MEMBER_B1)
    assert mine.status_code == theirs.status_code == 200
    assert all(r["site_id"] == str(S.SITE_A) for r in mine.json())
    assert all(r["site_id"] == str(S.SITE_B) for r in theirs.json())


def test_mini_sessions_cross_club(client, request) -> None:
    ep = BY_KEY["GET /api/mini/academy/sessions"]
    C.record(ep, "D2_club_isolation_404", request.node.nodeid)
    mine = C.probe(client, request.node.nodeid + "::A", ep, headers=C.MEMBER_A1)
    theirs = C.probe(client, request.node.nodeid + "::B", ep, headers=C.MEMBER_B1)
    assert mine.status_code == theirs.status_code == 200
    assert all(r["site_id"] == str(S.SITE_A) for r in mine.json())
    assert all(r["site_id"] == str(S.SITE_B) for r in theirs.json())


def test_mini_registrations_user_scope(client, request) -> None:
    ep = BY_KEY["GET /api/mini/academy/registrations"]
    C.record(ep, "D4_mini_cross_user_404", request.node.nodeid)
    a = C.probe(client, request.node.nodeid + "::A", ep, headers=C.MEMBER_A1)
    b = C.probe(client, request.node.nodeid + "::B", ep, headers=C.MEMBER_A2)
    assert all(r["contact_id"] == str(S.C_A1) for r in a.json())
    assert all(r["contact_id"] == str(S.C_A2) for r in b.json())


def test_mini_learning_user_scope(client, request) -> None:
    ep = BY_KEY["GET /api/mini/academy/learning-records"]
    C.record(ep, "D4_mini_cross_user_404", request.node.nodeid)
    a = C.probe(client, request.node.nodeid + "::A", ep, headers=C.MEMBER_A1)
    b = C.probe(client, request.node.nodeid + "::B", ep, headers=C.MEMBER_A2)
    assert all(r["contact_id"] == str(S.C_A1) for r in a.json())
    assert all(r["contact_id"] == str(S.C_A2) for r in b.json())


def test_mini_reveal_mobile_ownership(client, request) -> None:
    ep = BY_KEY["GET /api/mini/academy/contacts/{contact_id}/reveal-mobile"]
    C.record(ep, "D4_mini_cross_user_404", request.node.nodeid)
    other = ep.path.replace("{contact_id}", str(S.C_A2))
    r1 = C.probe(client, request.node.nodeid + "::other", ep, headers=C.MEMBER_A1, path=other)
    assert r1.status_code == 404, r1.text
    r2 = C.probe(client, request.node.nodeid + "::own", ep, headers=C.MEMBER_A1)
    assert r2.status_code == 200 and r2.json()["mobile"] == S.MOBILE_A1


def test_mini_post_registration_forged_contact(client, request) -> None:
    ep = BY_KEY["POST /api/mini/academy/registrations"]
    C.record(ep, "D4_mini_cross_user_404", request.node.nodeid)
    body = {"session_id": str(S.SESSION_A), "contact_id": str(S.C_A2)}
    resp = C.probe(client, request.node.nodeid, ep, headers=C.MEMBER_A1, json_body=body)
    assert resp.status_code == 201 and resp.json()["contact_id"] == str(S.C_A1)


def test_mini_post_application_forged_contact(client, request) -> None:
    ep = BY_KEY["POST /api/mini/academy/applications"]
    C.record(ep, "D4_mini_cross_user_404", request.node.nodeid)
    body = {"course_id": str(S.COURSE_A), "contact_id": str(S.C_A2)}
    resp = C.probe(client, request.node.nodeid, ep, headers=C.MEMBER_A1, json_body=body)
    assert resp.status_code == 201 and resp.json()["contact_id"] == str(S.C_A1)


def test_admin_create_roster_forged_site(client, request) -> None:
    ep = BY_KEY["POST /api/admin/academy/rosters"]
    C.record(ep, "D5_forgery_neutral", request.node.nodeid)
    body = {"session_id": str(S.SESSION_A), "contact_id": str(S.C_A1), "site_id": str(S.SITE_B)}
    resp = C.probe(client, request.node.nodeid, ep, headers=C.CLUB_A_ADMIN, json_body=body)
    assert resp.status_code == 201 and resp.json()["site_id"] == str(S.SITE_A), resp.text
