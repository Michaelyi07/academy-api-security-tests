"""D7: Response-body phone-number scanning against ALL GET endpoints.

The scanner walks every JSON key and value at every depth (strings included)
looking for an 11-digit mainland mobile pattern. It is executed for every GET
endpoint in the registry, under multiple identity contexts (anonymous, admin,
club A, club B, and two mini users). Only the two reveal-mobile endpoints are
exempt. Plaintext mobiles in the seed are fabricated test numbers.
"""
from __future__ import annotations

import pytest

from app.serializers import phone_hits
from tests import conftest as C
from tests.endpoints import GET_ENDPOINTS, Endpoint

REVEAL_MOBILE = "/reveal-mobile"

CONTEXTS = {
    "anonymous": C.ANON,
    "platform_admin": C.PLATFORM,
    "club_a_admin": C.CLUB_A_ADMIN,
    "club_b_employee": C.EMPLOYEE_B,
    "mini_user_a1": C.MEMBER_A1,
    "mini_user_a2": C.MEMBER_A2,
}


@pytest.mark.parametrize("ep", GET_ENDPOINTS, ids=[e.key for e in GET_ENDPOINTS])
def test_phone_scan_all_get_endpoints(client, request, ep: Endpoint) -> None:
    C.record(ep, "D7_phone_scan", request.node.nodeid)
    exempt = REVEAL_MOBILE in ep.path
    contexts = CONTEXTS
    if ep.side == "admin":
        contexts = {k: v for k, v in CONTEXTS.items() if k != "anonymous"}
    for name, headers in contexts.items():
        resp = C.probe(client, request.node.nodeid + "::" + name, ep, headers=headers)
        assert resp.status_code in (200, 400, 401, 403, 404), (
            f"unexpected status {resp.status_code} for {ep.key} as {name}: {resp.text}"
        )
        hits = phone_hits(resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text)
        if exempt:
            # reveal-mobile is the only designed plaintext outlet; assert it
            # actually returns the fabricated number (scanner must not be blind).
            if resp.status_code == 200:
                assert hits, f"{ep.key} is the exempt reveal-mobile endpoint but no mobile was found"
        else:
            assert not hits, (
                f"phone leak on {ep.key} as {name}: {hits}; response={resp.text[:600]}"
            )
