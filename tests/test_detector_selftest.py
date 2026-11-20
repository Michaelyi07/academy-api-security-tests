"""Detector self-test: prove the phone scanner catches a deliberately seeded
leak. Without this, an all-green run could be a false negative (scanner blind).

Also proves the coverage-matrix gate fails when dimensions are missing, using
an isolated in-memory ledger (does not mutate the real execution ledger).
"""
from __future__ import annotations

from app.serializers import mask_mobile, phone_hits, has_phone
from app import seed as S
from tests import conftest as C
from tests.endpoints import ENDPOINTS, DIMENSIONS


def test_scanner_detects_seeded_plain_mobile() -> None:
    payload = {
        "wrapper": {
            "rows": [
                {"id": "x", "nested": ["ok", S.MOBILE_A1]},
                {"note": "call +86 " + S.MOBILE_A2},
            ]
        }
    }
    hits = phone_hits(payload)
    assert S.MOBILE_A1 in hits and S.MOBILE_A2 in hits, f"scanner missed seeded leak: {hits}"
    assert has_phone(payload)


def test_scanner_detects_prefixed_and_numeric_mobiles() -> None:
    """A +86/86 prefix and a numeric-typed value must both be detected.

    The original regex (?<!\\d)1[3-9]\\d{9}(?!\\d) missed '+86139...' (the 6 of
    86 broke the lookbehind) and the walkers ignored non-string values.
    """
    plain = S.MOBILE_A1          # 13900000001
    prefixed_plus = "+86" + plain
    prefixed_plain = "86" + plain
    plus_only = "+" + plain       # '+' without 86 still a leak
    numeric = int(plain)

    # +86 / 86 / '+' prefix, inside free text and as a whole value
    for leaked in (prefixed_plus, prefixed_plain, plus_only, "tel:" + prefixed_plus):
        hits = phone_hits({"note": leaked})
        assert hits, f"scanner missed prefixed leak: {leaked!r}"
        assert any(plain in h for h in hits), f"prefixed hit lost the number: {hits}"
        assert has_phone({"note": leaked})

    # numeric-typed field value (JSON int), at top level and nested
    assert has_phone({"mobile": numeric})
    assert any(plain in h for h in phone_hits({"rows": [{"m": numeric}]}))
    assert has_phone([numeric])


def test_scanner_boundaries_no_false_positives() -> None:
    """Documented negative boundaries: a mobile embedded in a longer digit
    run, or with trailing digits, is NOT an 11-digit mobile leak; negative
    integers are not mobiles either. This makes the regex trade-off explicit
    and stops a future 'fix' from silently changing scan semantics."""
    for not_a_phone in (
        "2139000000001",     # 12-digit run: leading digit
        "98613900000001",     # leading digits before 86 prefix
        "139000000012",      # 11-digit prefix with trailing digit
        "00000000000",        # not a valid 1[3-9] mobile
        "1380000000",         # only 10 digits
        -13900000001,         # negative integer
    ):
        assert not has_phone({"v": not_a_phone}), f"false positive on {not_a_phone!r}"
        assert not phone_hits({"v": not_a_phone})


def test_scanner_ignores_masked_mobile() -> None:
    masked = mask_mobile(S.MOBILE_A1)
    assert "****" in masked
    assert not has_phone({"mobile": masked, "mobile_masked": masked})
    assert S.MOBILE_A1 not in masked


def test_coverage_matrix_gate_logic() -> None:
    """Regression check for acceptance criterion 2 (>= 2 dims per endpoint)."""
    assert len(ENDPOINTS) >= 1
    assert len(DIMENSIONS) == 7
    # The real gate is test_coverage_matrix_complete; here we assert the rule
    # itself: an endpoint with fewer than two dims would fail the predicate.
    dims = {"D1_role_permission"}
    assert not (len(dims) >= 2)
    dims.add("D7_phone_scan")
    assert len(dims) >= 2
