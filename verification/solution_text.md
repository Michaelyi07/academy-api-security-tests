# Delivery — #2097 Academy privilege & data-scope tests (Rework round 1)

Public repo: https://github.com/Michaelyi07/academy-api-security-tests
Commit: this rework's HEAD on main (the exact SHA is stated in the submission
body and is verified by GET against the repository at submission time).
All files below are in that repo at that commit. README has run instructions
and S2-IAM integration points.

This is rework round 1. The 3 acceptance criteria were already met in the
first delivery (162 tests green in the reviewer sandbox); the changes below
address the three scope/quality gaps the poster listed, plus issues found by
an independent review of the rework.

## Changes in rework round 1
1. [major] Club isolation uses REAL club-B objects. `app/seed.py` now seeds a
   club-B roster (`ROSTER_B1`) and a club-B review (`REVIEW_B_PLAIN`) at SITE_B,
   with valid FK links to club-B session/contact/course. `test_club_isolation.py`
   uses those real ids (not made-up UUIDs) and first proves the object returns
   200 for its own club before asserting club-A employee gets 404. The
   DELETE-review forgery case in `test_dimension_coverage.py` also uses the real
   club-B review id.
2. [major] Phone scan extended to ALL non-reveal-mobile interface responses,
   including all 8 POST/PATCH/DELETE write endpoints
   (`tests/security/test_write_phone_scan.py`). Each write endpoint executes a
   real successful request and its response is scanned; for the DELETE (204,
   no body) the post-delete list response is scanned instead (a vacuous
   scan of "" would prove nothing). The coverage matrix now shows D7 PASS on
   all 8 write endpoints.
3. [minor] Phone regex and value handling. `app/serializers.py::PHONE_RE` now
   matches 11-digit mobiles with optional `+86`, `86` or `+` prefix; the
   recursive walkers (`has_phone`, `phone_hits`) scan numeric-typed JSON values
   as well as strings (and skip bool/negative ints). The README's "+86" claim
   now matches the code. Self-tests cover plain/+86/86/+ prefixed, numeric
   values, and documented negative boundaries (no false positives).

Independent-review fixes also included: A-club "employee" identity (not just
admin) used for the 404 assertions; accurate D7 statistics (31 endpoints
executed: 29 assert-absent + 2 reveal-mobile assert-present); full update of
this delivery note to rework data.

## Acceptance criteria mapping
C1 all tests pass OR failures listed with repro: **175 passed, 0 failed**;
reports/issue_list.md auto-generated (0 issues). A failing case is written into
the issue list by pytest hook with method/URL/headers/body/seed state/expected/actual.
C2 matrix lists all academy endpoints, each >=2 dimensions: reports/coverage_matrix.md —
31 endpoints, minimum 2 dims; tests/test_coverage_matrix_complete.py fails the suite
if any endpoint drops below 2.
C3 phone scan visible in test code: tests/security/test_phone_leak_scanner.py covers
all 23 GET endpoints x identity contexts; tests/security/test_write_phone_scan.py
covers all 8 write endpoints. Recursive scanner in app/serializers.py::phone_hits
checks every key/value/depth for 11-digit mainland mobiles incl. +86/86/+ prefixes
and numeric values; only the two reveal-mobile endpoints are plaintext outlets
(and are asserted to contain a mobile, so the scanner is proven non-blind).

## Coverage matrix (from reports/coverage_matrix.md)
| Endpoint | D1 | D2 | D3 | D4 | D5 | D6 | D7 | Dims |
|---|---|---|---|---|---|---|---|---|
| GET /api/admin/academy/contacts/{contact_id}/reveal-mobile | PASS | - | - | - | - | - | PASS | 2 |
| GET /api/admin/academy/courses | PASS | PASS | - | - | - | - | PASS | 3 |
| POST /api/admin/academy/courses | PASS | - | - | - | PASS | - | PASS | 3 |
| GET /api/admin/academy/courses/{course_id} | PASS | PASS | - | - | - | - | PASS | 3 |
| PATCH /api/admin/academy/courses/{course_id} | PASS | - | - | - | PASS | - | PASS | 3 |
| GET /api/admin/academy/learning-records | PASS | - | PASS | - | - | - | PASS | 3 |
| GET /api/admin/academy/registrations | PASS | - | - | - | - | - | PASS | 2 |
| GET /api/admin/academy/reviews | PASS | PASS | - | - | - | - | PASS | 3 |
| DELETE /api/admin/academy/reviews/{review_id} | PASS | - | - | - | PASS | - | PASS* | 3 |
| GET /api/admin/academy/rosters | PASS | PASS | PASS | - | - | - | PASS | 4 |
| POST /api/admin/academy/rosters | PASS | - | - | - | PASS | - | PASS | 3 |
| GET /api/admin/academy/rosters/{roster_id} | PASS | PASS | PASS | - | - | - | PASS | 4 |
| GET /api/admin/academy/sessions | PASS | PASS | - | - | - | - | PASS | 3 |
| POST /api/admin/academy/sessions | PASS | - | - | - | PASS | - | PASS | 3 |
| GET /api/admin/academy/sessions/{session_id} | PASS | PASS | - | - | - | - | PASS | 3 |
| GET /api/mini/academy/applications | - | - | - | PASS | - | - | PASS | 2 |
| POST /api/mini/academy/applications | - | - | - | PASS | PASS | - | PASS | 3 |
| GET /api/mini/academy/applications/{application_id} | - | - | - | PASS | - | - | PASS | 2 |
| GET /api/mini/academy/contacts/{contact_id}/reveal-mobile | - | - | - | PASS | - | - | PASS | 2 |
| GET /api/mini/academy/courses | - | PASS | - | - | - | - | PASS | 2 |
| GET /api/mini/academy/courses/{course_id} | - | PASS | - | - | - | - | PASS | 2 |
| GET /api/mini/academy/learning-records | - | - | - | PASS | - | - | PASS | 2 |
| GET /api/mini/academy/learning-records/{record_id} | - | - | - | PASS | - | - | PASS | 2 |
| GET /api/mini/academy/registrations | - | - | - | PASS | - | - | PASS | 2 |
| POST /api/mini/academy/registrations | - | - | - | PASS | PASS | - | PASS | 3 |
| GET /api/mini/academy/registrations/{registration_id} | - | - | - | PASS | PASS | - | PASS | 3 |
| GET /api/mini/academy/reviews | - | - | - | - | - | PASS | PASS | 2 |
| POST /api/mini/academy/reviews | - | - | - | - | PASS | PASS | PASS | 3 |
| GET /api/mini/academy/reviews/{review_id} | - | PASS | - | PASS | - | PASS | PASS | 4 |
| GET /api/mini/academy/sessions | - | PASS | - | - | - | - | PASS | 2 |
| GET /api/mini/academy/sessions/{session_id} | - | PASS | - | - | - | - | PASS | 2 |
Total 31 endpoints; min dims 2; D7 executes on 31 endpoints (29 assert no mobile,
2 reveal-mobile assert a mobile is present). 23 GET + 8 write endpoints.
(*) DELETE returns 204 (no body); D7 scans the post-delete list response.

## Verified environment & real output
Command: python -m pytest -v (full raw output: verification/pytest_run_rework1.txt in repo)
Environment: Windows-10-10.0.19045-SP0; Python 3.13.14; pytest 9.2.0; pluggy 1.7.0;
FastAPI 0.165.0; SQLAlchemy 2.1.8; psycopg 3.3.9; pydantic 2.14.4; httpx 0.28.1;
PostgreSQL 16.9 (select version()).
Raw excerpts (unmodified):
platform win32 -- Python 3.13.14, pytest-9.2.0, pluggy-1.7.0
tests/security/test_club_isolation.py::test_foreign_roster_and_review_exist_for_club_b PASSED
tests/security/test_write_phone_scan.py::test_phone_scan_all_write_endpoints[DELETE /api/admin/academy/reviews/{review_id}] PASSED
tests/test_detector_selftest.py::test_scanner_detects_prefixed_and_numeric_mobiles PASSED
tests/test_detector_selftest.py::test_scanner_boundaries_no_false_positives PASSED
tests/test_coverage_matrix_complete.py::test_coverage_matrix_complete PASSED
============================ 175 passed in 20.49s =============================
EXIT=0

## Confidentiality
Fictional data only; made-up test phone numbers; no customer name, no real personal/enterprise
info, no secrets in source. Dependency S2-IAM uses header-driven stubs; integration point
documented in README. Bug fixing excluded per scope; found issues (none here) would be
listed with repro steps, not silently patched.
