# Academy API coverage matrix (endpoint x test-case dimension)

Generated from live pytest execution. `PASS` = at least one executed test case
for that endpoint x dimension; `-` = not applicable / not executed.

| Endpoint | Side | D1_role_permission | D2_club_isolation_404 | D3_manager_scope | D4_mini_cross_user_404 | D5_forgery_neutral | D6_anonymous_reviewer_privacy | D7_phone_scan | Dims |
|---|---|---|---|---|---|---|---|---|---|
| `GET /api/admin/academy/contacts/{contact_id}/reveal-mobile` | admin | PASS | - | - | - | - | - | PASS | 2 |
| `GET /api/admin/academy/courses` | admin | PASS | PASS | - | - | - | - | PASS | 3 |
| `POST /api/admin/academy/courses` | admin | PASS | - | - | - | PASS | - | PASS | 3 |
| `GET /api/admin/academy/courses/{course_id}` | admin | PASS | PASS | - | - | - | - | PASS | 3 |
| `PATCH /api/admin/academy/courses/{course_id}` | admin | PASS | - | - | - | PASS | - | PASS | 3 |
| `GET /api/admin/academy/learning-records` | admin | PASS | - | PASS | - | - | - | PASS | 3 |
| `GET /api/admin/academy/registrations` | admin | PASS | - | - | - | - | - | PASS | 2 |
| `GET /api/admin/academy/reviews` | admin | PASS | PASS | - | - | - | - | PASS | 3 |
| `DELETE /api/admin/academy/reviews/{review_id}` | admin | PASS | - | - | - | PASS | - | PASS | 3 |
| `GET /api/admin/academy/rosters` | admin | PASS | PASS | PASS | - | - | - | PASS | 4 |
| `POST /api/admin/academy/rosters` | admin | PASS | - | - | - | PASS | - | PASS | 3 |
| `GET /api/admin/academy/rosters/{roster_id}` | admin | PASS | PASS | PASS | - | - | - | PASS | 4 |
| `GET /api/admin/academy/sessions` | admin | PASS | PASS | - | - | - | - | PASS | 3 |
| `POST /api/admin/academy/sessions` | admin | PASS | - | - | - | PASS | - | PASS | 3 |
| `GET /api/admin/academy/sessions/{session_id}` | admin | PASS | PASS | - | - | - | - | PASS | 3 |
| `GET /api/mini/academy/applications` | mini | - | - | - | PASS | - | - | PASS | 2 |
| `POST /api/mini/academy/applications` | mini | - | - | - | PASS | PASS | - | PASS | 3 |
| `GET /api/mini/academy/applications/{application_id}` | mini | - | - | - | PASS | - | - | PASS | 2 |
| `GET /api/mini/academy/contacts/{contact_id}/reveal-mobile` | mini | - | - | - | PASS | - | - | PASS | 2 |
| `GET /api/mini/academy/courses` | mini | - | PASS | - | - | - | - | PASS | 2 |
| `GET /api/mini/academy/courses/{course_id}` | mini | - | PASS | - | - | - | - | PASS | 2 |
| `GET /api/mini/academy/learning-records` | mini | - | - | - | PASS | - | - | PASS | 2 |
| `GET /api/mini/academy/learning-records/{record_id}` | mini | - | - | - | PASS | - | - | PASS | 2 |
| `GET /api/mini/academy/registrations` | mini | - | - | - | PASS | - | - | PASS | 2 |
| `POST /api/mini/academy/registrations` | mini | - | - | - | PASS | PASS | - | PASS | 3 |
| `GET /api/mini/academy/registrations/{registration_id}` | mini | - | - | - | PASS | PASS | - | PASS | 3 |
| `GET /api/mini/academy/reviews` | mini | - | - | - | - | - | PASS | PASS | 2 |
| `POST /api/mini/academy/reviews` | mini | - | - | - | - | PASS | PASS | PASS | 3 |
| `GET /api/mini/academy/reviews/{review_id}` | mini | - | PASS | - | PASS | - | PASS | PASS | 4 |
| `GET /api/mini/academy/sessions` | mini | - | PASS | - | - | - | - | PASS | 2 |
| `GET /api/mini/academy/sessions/{session_id}` | mini | - | PASS | - | - | - | - | PASS | 2 |

- Total academy endpoints: **31** (admin 15, mini 16)
- Minimum dimensions per endpoint: **2** (acceptance requires >= 2)
- GET endpoints (phone-scan applicable): **23**
- Write endpoints (POST/PATCH/DELETE, phone-scan applicable): **8**
- Endpoints D7 executes on: **31** (29 assert no mobile; 2 reveal-mobile assert a mobile IS present)
