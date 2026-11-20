"""All /api/admin/academy and /api/mini/academy endpoints (fictional reference target).

Scope rules:
- Admin: require() permission point -> 403; object/list queries filtered by
  org_id and (for club roles) site_id; missing/out-of-scope object -> 404.
- membership_manager: roster rows and learning records further restricted to
  owner_manager_id == identity.user_id.
- Mini: identity.contact_id from trusted header; any object not owned by that
  contact -> 404. Forged body contact_id/site_id are ignored.
- Mobile plaintext: only the two reveal-mobile endpoints return it.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .iam import Identity, admin_scope, get_identity, not_found, require
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
from .serializers import (
    application_json,
    contact_json,
    course_json,
    learning_json,
    registration_json,
    review_json,
    roster_json,
    session_json,
)

admin = APIRouter(prefix="/api/admin/academy", tags=["admin-academy"])
mini = APIRouter(prefix="/api/mini/academy", tags=["mini-academy"])


# --- request bodies (forgery fields are accepted then ignored) --------------
class CourseIn(BaseModel):
    title: str
    summary: str = ""
    price_cents: int = 0
    # forgeable fields: deliberately accepted, never trusted
    contact_id: str | None = None
    site_id: str | None = None
    org_id: str | None = None


class SessionIn(BaseModel):
    course_id: str
    title: str
    capacity: int = 30
    contact_id: str | None = None
    site_id: str | None = None


class RosterIn(BaseModel):
    session_id: str
    contact_id: str
    note: str = ""
    site_id: str | None = None


class RegistrationIn(BaseModel):
    session_id: str
    contact_id: str | None = None
    site_id: str | None = None
    org_id: str | None = None


class ApplicationIn(BaseModel):
    course_id: str
    contact_id: str | None = None
    site_id: str | None = None


class ReviewIn(BaseModel):
    course_id: str
    rating: int = 5
    comment: str = ""
    is_anonymous: bool = False
    contact_id: str | None = None
    site_id: str | None = None


# --- helpers ---------------------------------------------------------------
def _scoped_one(
    db: Session,
    model: Any,
    obj_id: uuid.UUID,
    identity: Identity,
    *,
    site_scoped: bool = True,
    contact_field: str | None = None,
) -> Any:
    org_id, site_id = admin_scope(identity)
    stmt = select(model).where(
        model.id == obj_id,
        model.org_id == org_id,
        model.deleted_at.is_(None),
    )
    if site_scoped and site_id is not None:
        stmt = stmt.where(model.site_id == site_id)
    if contact_field:
        stmt = stmt.where(getattr(model, contact_field) == identity.contact_id)
    obj = db.scalar(stmt)
    if obj is None:
        raise not_found()
    return obj


def _mini_identity(identity: Identity) -> Identity:
    """Mini endpoints require a contact identity (trusted X-Contact-Id header)."""
    if identity.contact_id is None:
        raise HTTPException(status_code=401, detail={"code": "contact_required"})
    return identity


def _manager_filter(stmt: Any, model: Any, identity: Identity) -> Any:
    if "membership_manager" in identity.roles and not (identity.roles & {"platform_admin", "org_admin", "club_admin"}):
        return stmt.where(model.owner_manager_id == identity.user_id)
    return stmt


# ============================ ADMIN ENDPOINTS ==============================
@admin.get("/courses")
def admin_list_courses(
    identity: Identity = Depends(require("academy.course.view")), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    org_id, site_id = admin_scope(identity)
    stmt = select(Course).where(Course.org_id == org_id, Course.deleted_at.is_(None))
    if site_id is not None:
        stmt = stmt.where(Course.site_id == site_id)
    return [course_json(c) for c in db.scalars(stmt)]


@admin.post("/courses", status_code=201)
def admin_create_course(
    body: CourseIn,
    identity: Identity = Depends(require("academy.course.manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    obj = Course(
        id=uuid.uuid4(),
        org_id=identity.org_id,
        site_id=identity.site_id,  # forged body.site_id ignored
        created_by=identity.user_id,
        title=body.title,
        summary=body.summary,
        price_cents=body.price_cents,
    )
    db.add(obj)
    db.commit()
    return course_json(obj)


@admin.get("/courses/{course_id}")
def admin_get_course(
    course_id: uuid.UUID,
    identity: Identity = Depends(require("academy.course.view")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return course_json(_scoped_one(db, Course, course_id, identity))


@admin.patch("/courses/{course_id}")
def admin_edit_course(
    course_id: uuid.UUID,
    body: CourseIn,
    identity: Identity = Depends(require("academy.course.manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    obj = _scoped_one(db, Course, course_id, identity)
    obj.title = body.title
    obj.summary = body.summary
    obj.price_cents = body.price_cents
    db.commit()
    return course_json(obj)


@admin.get("/sessions")
def admin_list_sessions(
    identity: Identity = Depends(require("academy.session.view")), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    org_id, site_id = admin_scope(identity)
    stmt = select(CourseSession).where(CourseSession.org_id == org_id, CourseSession.deleted_at.is_(None))
    if site_id is not None:
        stmt = stmt.where(CourseSession.site_id == site_id)
    return [session_json(s) for s in db.scalars(stmt)]


@admin.post("/sessions", status_code=201)
def admin_create_session(
    body: SessionIn,
    identity: Identity = Depends(require("academy.session.manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _scoped_one(db, Course, uuid.UUID(body.course_id), identity)
    obj = CourseSession(
        id=uuid.uuid4(),
        org_id=identity.org_id,
        site_id=identity.site_id,
        created_by=identity.user_id,
        course_id=uuid.UUID(body.course_id),
        title=body.title,
        capacity=body.capacity,
    )
    db.add(obj)
    db.commit()
    return session_json(obj)


@admin.get("/sessions/{session_id}")
def admin_get_session(
    session_id: uuid.UUID,
    identity: Identity = Depends(require("academy.session.view")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return session_json(_scoped_one(db, CourseSession, session_id, identity))


@admin.get("/rosters")
def admin_list_rosters(
    identity: Identity = Depends(require("academy.roster.view")), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    org_id, site_id = admin_scope(identity)
    stmt = select(Roster).where(Roster.org_id == org_id, Roster.deleted_at.is_(None))
    if site_id is not None:
        stmt = stmt.where(Roster.site_id == site_id)
    stmt = _manager_filter(stmt, Roster, identity)
    return [roster_json(r) for r in db.scalars(stmt)]


@admin.post("/rosters", status_code=201)
def admin_create_roster(
    body: RosterIn,
    identity: Identity = Depends(require("academy.roster.manage")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _scoped_one(db, CourseSession, uuid.UUID(body.session_id), identity)
    contact = _scoped_one(db, Contact, uuid.UUID(body.contact_id), identity)
    obj = Roster(
        id=uuid.uuid4(),
        org_id=identity.org_id,
        site_id=identity.site_id,
        created_by=identity.user_id,
        session_id=uuid.UUID(body.session_id),
        contact_id=contact.id,
        owner_manager_id=contact.owner_manager_id,
        note=body.note,
    )
    db.add(obj)
    db.commit()
    return roster_json(obj)


@admin.get("/rosters/{roster_id}")
def admin_get_roster(
    roster_id: uuid.UUID,
    identity: Identity = Depends(require("academy.roster.view")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    obj = _scoped_one(db, Roster, roster_id, identity)
    if "membership_manager" in identity.roles and not (identity.roles & {"platform_admin", "org_admin", "club_admin"}):
        if obj.owner_manager_id != identity.user_id:
            raise not_found()
    return roster_json(obj)


@admin.get("/reviews")
def admin_list_reviews(
    identity: Identity = Depends(require("academy.review.view")), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    org_id, site_id = admin_scope(identity)
    stmt = select(Review).where(Review.org_id == org_id, Review.deleted_at.is_(None))
    if site_id is not None:
        stmt = stmt.where(Review.site_id == site_id)
    return [review_json(r, mini=False) for r in db.scalars(stmt)]


@admin.delete("/reviews/{review_id}", status_code=204)
def admin_delete_review(
    review_id: uuid.UUID,
    identity: Identity = Depends(require("academy.review.moderate")),
    db: Session = Depends(get_db),
) -> None:
    obj = _scoped_one(db, Review, review_id, identity)
    from datetime import datetime, timezone

    obj.deleted_at = datetime.now(timezone.utc)
    db.commit()


@admin.get("/learning-records")
def admin_list_learning(
    identity: Identity = Depends(require("academy.learning.view")), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    org_id, site_id = admin_scope(identity)
    stmt = select(LearningRecord).where(LearningRecord.org_id == org_id, LearningRecord.deleted_at.is_(None))
    if site_id is not None:
        stmt = stmt.where(LearningRecord.site_id == site_id)
    stmt = _manager_filter(stmt, LearningRecord, identity)
    return [learning_json(r) for r in db.scalars(stmt)]


@admin.get("/registrations")
def admin_list_registrations(
    identity: Identity = Depends(require("academy.registration.view")), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    org_id, site_id = admin_scope(identity)
    stmt = select(Registration).where(Registration.org_id == org_id, Registration.deleted_at.is_(None))
    if site_id is not None:
        stmt = stmt.where(Registration.site_id == site_id)
    return [registration_json(r) for r in db.scalars(stmt)]


@admin.get("/contacts/{contact_id}/reveal-mobile")
def admin_reveal_mobile(
    contact_id: uuid.UUID,
    identity: Identity = Depends(require("academy.mobile.reveal")),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    obj = _scoped_one(db, Contact, contact_id, identity)
    return {"id": str(obj.id), "mobile": obj.mobile, "purpose": "reveal-mobile"}  # only plaintext outlet


# ============================= MINI ENDPOINTS ==============================
@mini.get("/courses")
def mini_list_courses(
    identity: Identity = Depends(get_identity), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    _mini_identity(identity)
    stmt = select(Course).where(
        Course.org_id == identity.org_id,
        Course.site_id == identity.site_id,
        Course.published.is_(True),
        Course.deleted_at.is_(None),
    )
    return [course_json(c) for c in db.scalars(stmt)]


@mini.get("/courses/{course_id}")
def mini_get_course(
    course_id: uuid.UUID, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)
) -> dict[str, Any]:
    _mini_identity(identity)
    return course_json(_scoped_one(db, Course, course_id, identity))


@mini.get("/sessions")
def mini_list_sessions(
    identity: Identity = Depends(get_identity), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    _mini_identity(identity)
    stmt = select(CourseSession).where(
        CourseSession.org_id == identity.org_id,
        CourseSession.site_id == identity.site_id,
        CourseSession.deleted_at.is_(None),
    )
    return [session_json(s) for s in db.scalars(stmt)]


@mini.get("/sessions/{session_id}")
def mini_get_session(
    session_id: uuid.UUID, identity: Identity = Depends(get_identity), db: Session = Depends(get_db)
) -> dict[str, Any]:
    _mini_identity(identity)
    return session_json(_scoped_one(db, CourseSession, session_id, identity))


@mini.get("/registrations")
def mini_list_registrations(
    identity: Identity = Depends(get_identity), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    ident = _mini_identity(identity)
    stmt = select(Registration).where(
        Registration.org_id == ident.org_id,
        Registration.site_id == ident.site_id,
        Registration.contact_id == ident.contact_id,
        Registration.deleted_at.is_(None),
    )
    return [registration_json(r) for r in db.scalars(stmt)]


@mini.post("/registrations", status_code=201)
def mini_create_registration(
    body: RegistrationIn,
    identity: Identity = Depends(get_identity),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ident = _mini_identity(identity)
    _scoped_one(db, CourseSession, uuid.UUID(body.session_id), ident)
    obj = Registration(
        id=uuid.uuid4(),
        org_id=ident.org_id,
        site_id=ident.site_id,  # forged body.site_id ignored
        created_by=ident.user_id,
        session_id=uuid.UUID(body.session_id),
        contact_id=ident.contact_id,  # forged body.contact_id ignored
        status="registered",
    )
    db.add(obj)
    db.commit()
    return registration_json(obj)


@mini.get("/registrations/{registration_id}")
def mini_get_registration(
    registration_id: uuid.UUID,
    identity: Identity = Depends(get_identity),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ident = _mini_identity(identity)
    return registration_json(
        _scoped_one(db, Registration, registration_id, ident, contact_field="contact_id")
    )


@mini.get("/applications")
def mini_list_applications(
    identity: Identity = Depends(get_identity), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    ident = _mini_identity(identity)
    stmt = select(Application).where(
        Application.org_id == ident.org_id,
        Application.site_id == ident.site_id,
        Application.contact_id == ident.contact_id,
        Application.deleted_at.is_(None),
    )
    return [application_json(a) for a in db.scalars(stmt)]


@mini.post("/applications", status_code=201)
def mini_create_application(
    body: ApplicationIn,
    identity: Identity = Depends(get_identity),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ident = _mini_identity(identity)
    _scoped_one(db, Course, uuid.UUID(body.course_id), ident)
    obj = Application(
        id=uuid.uuid4(),
        org_id=ident.org_id,
        site_id=ident.site_id,
        created_by=ident.user_id,
        course_id=uuid.UUID(body.course_id),
        contact_id=ident.contact_id,
    )
    db.add(obj)
    db.commit()
    return application_json(obj)


@mini.get("/applications/{application_id}")
def mini_get_application(
    application_id: uuid.UUID,
    identity: Identity = Depends(get_identity),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ident = _mini_identity(identity)
    return application_json(_scoped_one(db, Application, application_id, ident, contact_field="contact_id"))


@mini.get("/reviews")
def mini_list_reviews(
    identity: Identity = Depends(get_identity), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    ident = _mini_identity(identity)
    stmt = select(Review).where(
        Review.org_id == ident.org_id,
        Review.site_id == ident.site_id,
        Review.deleted_at.is_(None),
    )
    return [review_json(r, mini=True) for r in db.scalars(stmt)]


@mini.post("/reviews", status_code=201)
def mini_create_review(
    body: ReviewIn,
    identity: Identity = Depends(get_identity),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ident = _mini_identity(identity)
    _scoped_one(db, Course, uuid.UUID(body.course_id), ident)
    obj = Review(
        id=uuid.uuid4(),
        org_id=ident.org_id,
        site_id=ident.site_id,
        created_by=ident.user_id,
        course_id=uuid.UUID(body.course_id),
        contact_id=ident.contact_id,  # forged body.contact_id ignored
        reviewer_name="Fictional Reviewer",
        is_anonymous=body.is_anonymous,
        rating=body.rating,
        comment=body.comment,
    )
    db.add(obj)
    db.commit()
    return review_json(obj, mini=True)


@mini.get("/reviews/{review_id}")
def mini_get_review(
    review_id: uuid.UUID,
    identity: Identity = Depends(get_identity),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ident = _mini_identity(identity)
    return review_json(
        _scoped_one(db, Review, review_id, ident, contact_field="contact_id"), mini=True
    )


@mini.get("/learning-records")
def mini_list_learning(
    identity: Identity = Depends(get_identity), db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    ident = _mini_identity(identity)
    stmt = select(LearningRecord).where(
        LearningRecord.org_id == ident.org_id,
        LearningRecord.site_id == ident.site_id,
        LearningRecord.contact_id == ident.contact_id,
        LearningRecord.deleted_at.is_(None),
    )
    return [learning_json(r) for r in db.scalars(stmt)]


@mini.get("/learning-records/{record_id}")
def mini_get_learning(
    record_id: uuid.UUID,
    identity: Identity = Depends(get_identity),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ident = _mini_identity(identity)
    return learning_json(
        _scoped_one(db, LearningRecord, record_id, ident, contact_field="contact_id")
    )


@mini.get("/contacts/{contact_id}/reveal-mobile")
def mini_reveal_mobile(
    contact_id: uuid.UUID,
    identity: Identity = Depends(get_identity),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    ident = _mini_identity(identity)
    if contact_id != ident.contact_id:
        raise not_found()
    obj = _scoped_one(db, Contact, contact_id, ident)
    return {"id": str(obj.id), "mobile": obj.mobile, "purpose": "reveal-mobile"}
