"""Endpoint registry derived from the live FastAPI routers.

The registry is the single source of truth for 'all academy interfaces'.
It is read from the routers at import time, so a newly added endpoint that a
test does not cover will automatically appear in the generated coverage matrix.

Each record:
  key       stable id (METHOD path)
  method    HTTP method
  path      full path as mounted
  side      admin | mini
  params    ordered list of path parameter names
  perm      required admin permission point (None for mini)
  resource  logical resource for scope tests (course/session/roster/review/...)
  sample    concrete path built from fictional seed ids, for executable probes
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.api import admin, mini
from app import seed

ADMIN_PREFIX = "/api/admin/academy"
MINI_PREFIX = "/api/mini/academy"

# Concrete fictional ids used to fill path templates in executable probes.
_PARAM_SAMPLE_IDS = {
    "course_id": seed.COURSE_A,
    "session_id": seed.SESSION_A,
    "roster_id": seed.ROSTER_A1,
    "review_id": seed.REVIEW_A_PLAIN,
    "registration_id": seed.REG_A1,
    "application_id": seed.APP_A1,
    "learning_id": seed.LEARN_A1,
    "record_id": seed.LEARN_A1,
    "contact_id": seed.C_A1,
}


@dataclass(frozen=True)
class Endpoint:
    key: str
    method: str
    path: str
    side: str
    params: tuple[str, ...]
    perm: str | None
    resource: str
    sample: str


_SAMPLES: dict[str, tuple[str, str]] = {
    # template suffix -> (resource, sample id)
    "/courses": ("course", seed.COURSE_A),
    "/courses/{course_id}": ("course", seed.COURSE_A),
    "/sessions": ("session", seed.SESSION_A),
    "/sessions/{session_id}": ("session", seed.SESSION_A),
    "/rosters": ("roster", seed.ROSTER_A1),  # GET; POST sample overridden below
    "/rosters/{roster_id}": ("roster", seed.ROSTER_A1),
    "/reviews": ("review", seed.REVIEW_A_PLAIN),
    "/reviews/{review_id}": ("review", seed.REVIEW_A_PLAIN),
    "/learning-records": ("learning", seed.LEARN_A1),
    "/registrations": ("registration", seed.REG_A1),
    "/registrations/{registration_id}": ("registration", seed.REG_A1),
    "/applications": ("application", seed.APP_A1),
    "/applications/{application_id}": ("application", seed.APP_A1),
    "/contacts/{contact_id}/reveal-mobile": ("contact", seed.C_A1),
}

# (method, suffix) -> permission point. Read from the same decorators the API
# enforces; GET=view, POST/PATCH=manage, DELETE=moderate.
_PERM_BY_METHOD_SUFFIX: dict[tuple[str, str], str] = {
    ("GET", "/courses"): "academy.course.view",
    ("POST", "/courses"): "academy.course.manage",
    ("GET", "/courses/{course_id}"): "academy.course.view",
    ("PATCH", "/courses/{course_id}"): "academy.course.manage",
    ("GET", "/sessions"): "academy.session.view",
    ("POST", "/sessions"): "academy.session.manage",
    ("GET", "/sessions/{session_id}"): "academy.session.view",
    ("GET", "/rosters"): "academy.roster.view",
    ("POST", "/rosters"): "academy.roster.manage",
    ("GET", "/rosters/{roster_id}"): "academy.roster.view",
    ("GET", "/reviews"): "academy.review.view",
    ("DELETE", "/reviews/{review_id}"): "academy.review.moderate",
    ("GET", "/learning-records"): "academy.learning.view",
    ("GET", "/registrations"): "academy.registration.view",
    ("GET", "/contacts/{contact_id}/reveal-mobile"): "academy.mobile.reveal",
}


def _build(side: str, prefix: str, router: Any) -> list[Endpoint]:
    out: list[Endpoint] = []
    for route in router.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}
        if not path or not methods:
            continue
        # route.path already includes its APIRouter prefix in this FastAPI build.
        suffix = path[len(prefix):] if path.startswith(prefix) else path
        params = tuple(
            p for p in (getattr(route, "param_convertors", {}) or {}).keys()
        )
        resource, sample_id = _SAMPLES.get(suffix, ("unknown", ""))
        sample = path
        for p in params:
            sample = sample.replace("{" + p + "}", str(_PARAM_SAMPLE_IDS.get(p, sample_id)))
        for method in sorted(methods):
            perm = _PERM_BY_METHOD_SUFFIX.get((method, suffix)) if side == "admin" else None
            out.append(
                Endpoint(
                    key=f"{method} {path}",
                    method=method,
                    path=path,
                    side=side,
                    params=params,
                    perm=perm,
                    resource=resource,
                    sample=sample,
                )
            )
    return out


ENDPOINTS: tuple[Endpoint, ...] = tuple(
    sorted(
        _build("admin", ADMIN_PREFIX, admin) + _build("mini", MINI_PREFIX, mini),
        key=lambda e: (e.path, e.method),
    )
)
BY_KEY = {e.key: e for e in ENDPOINTS}
GET_ENDPOINTS = tuple(e for e in ENDPOINTS if e.method == "GET")
ADMIN_ENDPOINTS = tuple(e for e in ENDPOINTS if e.side == "admin")
MINI_ENDPOINTS = tuple(e for e in ENDPOINTS if e.side == "mini")

DIMENSIONS: tuple[str, ...] = (
    "D1_role_permission",
    "D2_club_isolation_404",
    "D3_manager_scope",
    "D4_mini_cross_user_404",
    "D5_forgery_neutral",
    "D6_anonymous_reviewer_privacy",
    "D7_phone_scan",
)
