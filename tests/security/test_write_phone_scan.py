"""D7 (write side): response-body phone scanning for all POST/PATCH/DELETE
academy endpoints — the 8 write interfaces, not just GET.

The brief says: plaintext mobile is returned only by reveal-mobile, and NO
other interface response may contain an 11-digit mobile pattern. Write
responses are part of "all other interfaces" and are scanned here under a
realistic successful request for each write endpoint. Only reveal-mobile is
exempt (there are no write reveal-mobile endpoints).

Every successful write response is produced by the same central serialisers,
so a regression that starts echoing a raw contact.mobile would be caught.
"""
from __future__ import annotations

import pytest

from app import seed as S
from app.serializers import phone_hits
from tests import conftest as C
from tests.endpoints import BY_KEY, WRITE_ENDPOINTS, Endpoint

# A successful request (headers + body + optional path) per write endpoint.
# Bodies use only fictional seed ids; forged site/contact fields would be
# ignored by the API, but we keep them out so the happy path is unambiguous.
def _request_spec(key: str) -> tuple[dict, dict | None, str | None]:
    if key == "POST /api/admin/academy/courses":
        return C.CLUB_A_ADMIN, {"title": "Scan Course", "summary": "write scan", "price_cents": 100}, None
    if key == "PATCH /api/admin/academy/courses/{course_id}":
        return C.CLUB_A_ADMIN, {"title": "Scan Edit", "summary": "write scan", "price_cents": 200}, None
    if key == "DELETE /api/admin/academy/reviews/{review_id}":
        return C.CLUB_A_ADMIN, None, None  # sample = own-site REVIEW_A_PLAIN
    if key == "POST /api/admin/academy/rosters":
        return C.CLUB_A_ADMIN, {"session_id": str(S.SESSION_A), "contact_id": str(S.C_A1), "note": "scan"}, None
    if key == "POST /api/admin/academy/sessions":
        return C.CLUB_A_ADMIN, {"course_id": str(S.COURSE_A), "title": "Scan Session", "capacity": 10}, None
    if key == "POST /api/mini/academy/applications":
        return C.MEMBER_A1, {"course_id": str(S.COURSE_A)}, None
    if key == "POST /api/mini/academy/registrations":
        return C.MEMBER_A1, {"session_id": str(S.SESSION_A)}, None
    if key == "POST /api/mini/academy/reviews":
        return C.MEMBER_A1, {"course_id": str(S.COURSE_A), "rating": 5, "comment": "scan"}, None
    raise AssertionError(f"no request spec for write endpoint {key}")


@pytest.mark.parametrize("ep", WRITE_ENDPOINTS, ids=[e.key for e in WRITE_ENDPOINTS])
def test_phone_scan_all_write_endpoints(client, request, ep: Endpoint) -> None:
    C.record(ep, "D7_phone_scan", request.node.nodeid)
    headers, body, path = _request_spec(ep.key)
    resp = C.probe(client, request.node.nodeid, ep, headers=headers,
                   json_body=body, path=path)
    # A real successful write must have happened; scanning an error body would
    # prove nothing about the response serialiser.
    assert resp.status_code in (200, 201, 204), (
        f"write endpoint {ep.key} did not succeed: {resp.status_code} {resp.text}"
    )
    if resp.status_code == 204:
        # DELETE returns 204 No Content — there is no response body to scan.
        # Scanning "" would be a vacuous assertion. Instead scan the resulting
        # admin reviews LIST response: that is the observable response state
        # after this delete, and it is produced by the same serialiser boundary.
        list_ep = BY_KEY["GET /api/admin/academy/reviews"]
        after = C.probe(client, request.node.nodeid + "::after-delete-list",
                        list_ep, headers=headers)
        assert after.status_code == 200, after.text
        payload = after.json()
        scanned_via = "post-delete list response (204 has no body)"
    else:
        payload = resp.json()
        scanned_via = "write response body"

    hits = phone_hits(payload)
    assert not hits, (
        f"phone leak on WRITE {ep.key} via {scanned_via}: {hits}; "
        f"response={resp.text[:600]}"
    )


def test_write_endpoints_covered_by_scanner() -> None:
    """Guard: all 8 write endpoints are actually enumerated for D7 scanning."""
    assert len(WRITE_ENDPOINTS) == 8
    keys = {e.key for e in WRITE_ENDPOINTS}
    assert all("/reveal-mobile" not in k for k in keys)  # no write reveal outlet
    # Per-endpoint execution is proven by the parametrized scan test above.
