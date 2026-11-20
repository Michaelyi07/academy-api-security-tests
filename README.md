# Academy API — privilege-escalation & data-scope test suite

Automated pytest suite for the Academy module (`/api/admin/academy` and
`/api/mini/academy`). It runs against a **real PostgreSQL** database seeded with
**fictional** clubs/members/courses. No real personal or business data, no
customer name, no secrets in source, no overseas SDK.

## What is delivered

| Item | Location |
|---|---|
| Test code | `tests/` (7 dimension groups under `tests/security/`, plus gates/self-test) |
| Coverage matrix | `reports/coverage_matrix.md` (regenerated every run) |
| Issue list | `reports/issue_list.md` (failures + reproduction steps; auto-generated) |
| Run results | `reports/run_meta.json`, command/output in delivery text |
| Reference API target | `app/` — FastAPI/SQLAlchemy 2 stub used as the test database API |
| Run/test instructions | this README |

## Test-case dimensions

| # | Dimension | Assertion |
|---|---|---|
| D1 | 6 roles x 11 permission points | unauthorised role -> **403** |
| D2 | Club isolation | club A actor -> club B course/session/roster/review -> **404** (no existence leak) |
| D3 | Membership manager scope | only own rosters & learning records visible |
| D4 | Mini cross-user | user A token -> user B registration/application/review/learning record -> **404** |
| D5 | Forgery neutrality | URL id change, forged `contact_id`/`site_id`/`org_id` in body have no effect |
| D6 | Anonymous review privacy | no reviewer info in any mini endpoint |
| D7 | Phone scan | recursive mobile scan of **all endpoints except `reveal-mobile`** — 23 GET x identity contexts **and all 8 POST/PATCH/DELETE write responses**; detects plain 11-digit, `+86`/`86` prefixes and numeric-typed values; only `reveal-mobile` returns plaintext |

Every endpoint in the live router registry (`tests/endpoints.py`, derived from
`app.api` at import time) is asserted to have **>= 2** dimensions
(`tests/test_coverage_matrix_complete.py`). `tests/test_detector_selftest.py`
proves the scanner catches a deliberately seeded plaintext mobile, so an
all-green run is not a false negative.

## Run (PostgreSQL 16 — no SQLite fallback)

```bash
pip install -r requirements.txt
export ACADEMY_DATABASE_URL="postgresql+psycopg://postgres@127.0.0.1:5433/academy_scope_test"
pytest -q
# with docker compose instead:
docker compose up -d db && pytest -q
```

Verified environment: Python 3.13.14, pytest 9.2.0, FastAPI 0.165.0,
SQLAlchemy 2.1.8, psycopg 3.3.9, PostgreSQL **16.9**. CI workflow
`.github/workflows/tests.yml` runs the same suite on PostgreSQL 16.

## Integration points (S2-IAM dependency)

Per the work order, an API stub/mock is used first. The test target reads
identity from trusted gateway headers (`X-Org-Id`, `X-Site-Id`, `X-User-Id`,
`X-User-Roles`, `X-Contact-Id`), configured in `app/config.py`. To point the
suite at the real Academy API, replace the `client` fixture in
`tests/conftest.py` with an `httpx.Client` against `ACADEMY_BASE_URL` and keep
the same header injection; all test cases use `tests.endpoints.ENDPOINTS` and
`tests.conftest.probe()`, so no test body changes are needed. The 11 permission
points and 6 roles live in `app/iam.py`.

## Privacy

- Fictional mobile numbers only (`1390000xxxx` test range), seeded in `app/seed.py`.
- `app/serializers.py` is the single masking boundary: `mask_mobile()` and
  `review_json(mini=True)`; phone scanner in `app/serializers.py::phone_hits`.
- The scanner (`PHONE_RE`, `has_phone`, `phone_hits`) matches an 11-digit
  mainland mobile with optional `+86`/`86` prefix and scans numeric-typed
  field values as well as strings — so an echo of a raw contact mobile as a
  JSON int, or with a country prefix, is detected. `tests/test_detector_selftest.py`
  covers all three forms.
- Plaintext mobile is emitted only by the two `reveal-mobile` endpoints; every
  other response (GET **and** write) is scanned by D7.
