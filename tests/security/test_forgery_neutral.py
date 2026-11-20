"""D5: Changing the id in the URL or forging contact_id/site_id in the body
has no effect. Server-side scope comes from the trusted identity headers."""
from __future__ import annotations

import uuid

import pytest

from app import seed as S
from tests import conftest as C
from tests.endpoints import BY_KEY

FORGED_SITE = str(S.SITE_B)
FORGED_CONTACT = str(S.C_B1)
FORGED_ORG = str(uuid.UUID("10000000-0000-4000-8000-000000000099"))


def test_url_id_change_cannot_escalate(client, request) -> None:
    ep = BY_KEY["GET /api/mini/academy/registrations/{registration_id}"]
    C.record(ep, "D5_forgery_neutral", request.node.nodeid)
    # Guess a valid-format UUID that belongs to another user: must stay 404.
    path = ep.path.replace("{registration_id}", str(S.REG_A2))
    resp = C.probe(client, request.node.nodeid, ep, headers=C.MEMBER_A1, path=path)
    assert resp.status_code == 404, resp.text


@pytest.mark.parametrize(
    "key,body",
    [
        (
            "POST /api/admin/academy/courses",
            {"title": "Forged Course", "contact_id": FORGED_CONTACT, "site_id": FORGED_SITE, "org_id": FORGED_ORG},
        ),
        (
            "POST /api/admin/academy/sessions",
            {"course_id": str(S.COURSE_A), "title": "Forged Session", "contact_id": FORGED_CONTACT, "site_id": FORGED_SITE},
        ),
    ],
)
def test_admin_body_forgery_ignored(client, request, key: str, body: dict) -> None:
    ep = BY_KEY[key]
    C.record(ep, "D5_forgery_neutral", request.node.nodeid)
    baseline = dict(body)
    # contact_id is a legitimate required field for rosters (the manager
    # assigns a member); site_id/org_id are always forged-only and removed.
    if "session_id" not in baseline and "title" not in baseline:
        pass  # roster body keeps its contact_id
    else:
        baseline.pop("contact_id", None)
    baseline.pop("site_id", None)
    baseline.pop("org_id", None)
    clean = C.probe(client, request.node.nodeid + "::clean", ep, headers=C.CLUB_A_ADMIN, json_body=baseline)
    forged = C.probe(client, request.node.nodeid + "::forged", ep, headers=C.CLUB_A_ADMIN, json_body=body)
    assert clean.status_code == forged.status_code in (200, 201), (clean.text, forged.text)
    assert forged.json()["site_id"] == str(S.SITE_A), "forged site_id took effect"
    assert forged.json()["org_id"] == str(S.ORG), "forged org_id took effect"
    assert {k: v for k, v in forged.json().items() if k in ("title", "note")} == {
        k: v for k, v in clean.json().items() if k in ("title", "note")
    }


@pytest.mark.parametrize(
    "key,body",
    [
        (
            "POST /api/mini/academy/registrations",
            {"session_id": str(S.SESSION_A), "contact_id": FORGED_CONTACT, "site_id": FORGED_SITE, "org_id": FORGED_ORG},
        ),
        (
            "POST /api/mini/academy/applications",
            {"course_id": str(S.COURSE_A), "contact_id": FORGED_CONTACT, "site_id": FORGED_SITE},
        ),
        (
            "POST /api/mini/academy/reviews",
            {"course_id": str(S.COURSE_A), "rating": 5, "comment": "forged", "contact_id": FORGED_CONTACT, "site_id": FORGED_SITE},
        ),
    ],
)
def test_mini_body_forgery_ignored(client, request, key: str, body: dict) -> None:
    ep = BY_KEY[key]
    C.record(ep, "D5_forgery_neutral", request.node.nodeid)
    resp = C.probe(client, request.node.nodeid, ep, headers=C.MEMBER_A1, json_body=body)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["contact_id"] == str(S.C_A1), "forged contact_id took effect"
    assert data["site_id"] == str(S.SITE_A), "forged site_id took effect"
    assert data["org_id"] == str(S.ORG), "forged org_id took effect"
