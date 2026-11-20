"""Response serialisers: central privacy boundary.

Rules enforced here (mirrored/verified by the test suite):
- Plaintext mobile appears ONLY via reveal-mobile endpoints. Every other
  serialiser emits a masked value that cannot match an 11-digit phone pattern.
- Anonymous reviews never expose reviewer identity in any mini endpoint.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

from .models import (
    Application,
    Contact,
    Course,
    CourseSession,
    LearningRecord,
    Registration,
    Review,
    Roster,
)

PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")


def mask_mobile(plain: str) -> str:
    """13900000001 -> 139****0001 (no 11-digit run remains)."""
    if not re.fullmatch(r"1[3-9]\d{9}", plain or ""):
        return "[redacted]"
    return f"{plain[:3]}****{plain[-4:]}"


def has_phone(value: Any) -> bool:
    """Recursive scan of any JSON-like structure for an 11-digit mobile pattern."""
    if isinstance(value, str):
        return bool(PHONE_RE.search(value))
    if isinstance(value, dict):
        return any(has_phone(k) or has_phone(v) for k, v in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(has_phone(v) for v in value)
    return False


def phone_hits(value: Any) -> list[str]:
    """Return the matching 11-digit strings found anywhere in a JSON structure."""
    out: list[str] = []

    def walk(v: Any) -> None:
        if isinstance(v, str):
            out.extend(PHONE_RE.findall(v))
        elif isinstance(v, dict):
            for k, item in v.items():
                walk(k)
                walk(item)
        elif isinstance(v, (list, tuple, set)):
            for item in v:
                walk(item)

    walk(value)
    return out


def _base(obj: Any) -> dict[str, Any]:
    return {
        "id": str(obj.id),
        "org_id": str(obj.org_id),
        "site_id": str(obj.site_id),
        "created_at": obj.created_at.isoformat() if obj.created_at else None,
        "created_by": str(obj.created_by) if obj.created_by else None,
        "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        "deleted_at": obj.deleted_at.isoformat() if obj.deleted_at else None,
    }


def course_json(c: Course) -> dict[str, Any]:
    return {
        **_base(c),
        "title": c.title,
        "summary": c.summary,
        "price_cents": c.price_cents,
        "published": c.published,
    }


def session_json(s: CourseSession) -> dict[str, Any]:
    return {**_base(s), "course_id": str(s.course_id), "title": s.title, "capacity": s.capacity}


def roster_json(r: Roster, *, include_contact: bool = True) -> dict[str, Any]:
    data: dict[str, Any] = {
        **_base(r),
        "session_id": str(r.session_id),
        "contact_id": str(r.contact_id),
        "note": r.note,
    }
    if include_contact:
        data["owner_manager_id"] = str(r.owner_manager_id) if r.owner_manager_id else None
    return data


def contact_json(c: Contact) -> dict[str, Any]:
    """Default contact serialiser: NEVER includes plaintext mobile."""
    return {
        **_base(c),
        "display_name": c.display_name,
        "mobile": mask_mobile(c.mobile),
        "mobile_masked": mask_mobile(c.mobile),
        "owner_manager_id": str(c.owner_manager_id) if c.owner_manager_id else None,
    }


def review_json(r: Review, *, mini: bool) -> dict[str, Any]:
    data: dict[str, Any] = {
        **_base(r),
        "course_id": str(r.course_id),
        "is_anonymous": r.is_anonymous,
        "rating": r.rating,
        "comment": r.comment,
    }
    # Anonymous reviews: no reviewer identity in ANY mini endpoint.
    if not (mini and r.is_anonymous):
        data["contact_id"] = str(r.contact_id)
        data["reviewer_name"] = r.reviewer_name
    return data


def registration_json(r: Registration) -> dict[str, Any]:
    return {**_base(r), "session_id": str(r.session_id), "contact_id": str(r.contact_id), "status": r.status}


def application_json(a: Application) -> dict[str, Any]:
    return {**_base(a), "course_id": str(a.course_id), "contact_id": str(a.contact_id), "status": a.status}


def learning_json(l: LearningRecord) -> dict[str, Any]:
    return {
        **_base(l),
        "session_id": str(l.session_id),
        "contact_id": str(l.contact_id),
        "owner_manager_id": str(l.owner_manager_id) if l.owner_manager_id else None,
        "progress_pct": l.progress_pct,
    }
