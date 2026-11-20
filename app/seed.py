"""Fictional seed data for Academy scope tests.

Every entity is fabricated. Club A / Club B are two fictional venues of one
fictional organisation. Phone numbers are made-up test numbers (no real person).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

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

ORG = uuid.UUID("10000000-0000-4000-8000-000000000001")
SITE_A = uuid.UUID("20000000-0000-4000-8000-000000000001")  # fictional club A
SITE_B = uuid.UUID("20000000-0000-4000-8000-000000000002")  # fictional club B
CREATOR = uuid.UUID("30000000-0000-4000-8000-000000000001")

# --- Actors (identity headers in tests) -----------------------------------
U_PLATFORM_ADMIN = uuid.UUID("40000000-0000-4000-8000-000000000001")
U_ORG_ADMIN = uuid.UUID("40000000-0000-4000-8000-000000000002")
U_CLUB_ADMIN_A = uuid.UUID("40000000-0000-4000-8000-000000000003")
U_EMPLOYEE_A = uuid.UUID("40000000-0000-4000-8000-000000000004")
U_MANAGER_A = uuid.UUID("40000000-0000-4000-8000-000000000005")
U_EMPLOYEE_B = uuid.UUID("40000000-0000-4000-8000-000000000006")
U_MEMBER_A1 = uuid.UUID("50000000-0000-4000-8000-000000000001")
U_MEMBER_A2 = uuid.UUID("50000000-0000-4000-8000-000000000002")
U_MEMBER_B1 = uuid.UUID("50000000-0000-4000-8000-000000000003")

# --- Contacts (mini users) -------------------------------------------------
C_A1 = uuid.UUID("60000000-0000-4000-8000-000000000001")  # owned by U_MANAGER_A
C_A2 = uuid.UUID("60000000-0000-4000-8000-000000000002")  # not manager-owned
C_B1 = uuid.UUID("60000000-0000-4000-8000-000000000003")

# --- Content ---------------------------------------------------------------
COURSE_A = uuid.UUID("70000000-0000-4000-8000-000000000001")
COURSE_A2 = uuid.UUID("70000000-0000-4000-8000-000000000002")
COURSE_B = uuid.UUID("70000000-0000-4000-8000-000000000003")
SESSION_A = uuid.UUID("71000000-0000-4000-8000-000000000001")
SESSION_B = uuid.UUID("71000000-0000-4000-8000-000000000002")
ROSTER_A1 = uuid.UUID("72000000-0000-4000-8000-000000000001")
ROSTER_A2 = uuid.UUID("72000000-0000-4000-8000-000000000002")
ROSTER_B1 = uuid.UUID("72000000-0000-4000-8000-000000000003")  # real club-B roster
REVIEW_A_PLAIN = uuid.UUID("73000000-0000-4000-8000-000000000001")
REVIEW_A_ANON = uuid.UUID("73000000-0000-4000-8000-000000000002")
REVIEW_B_PLAIN = uuid.UUID("73000000-0000-4000-8000-000000000003")  # real club-B review
REG_A1 = uuid.UUID("74000000-0000-4000-8000-000000000001")
REG_A2 = uuid.UUID("74000000-0000-4000-8000-000000000002")
APP_A1 = uuid.UUID("75000000-0000-4000-8000-000000000001")
APP_A2 = uuid.UUID("75000000-0000-4000-8000-000000000002")
LEARN_A1 = uuid.UUID("76000000-0000-4000-8000-000000000001")
LEARN_A2 = uuid.UUID("76000000-0000-4000-8000-000000000002")

# Fictional mobile numbers: deliberately obvious test ranges, 11-digit format.
MOBILE_A1 = "13900000001"
MOBILE_A2 = "13900000002"
MOBILE_B1 = "13900000003"


def _common(site_id: uuid.UUID, entity_id: uuid.UUID, **extra: Any) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "id": entity_id,
        "org_id": ORG,
        "site_id": site_id,
        "created_at": now,
        "created_by": CREATOR,
        "updated_at": now,
        "deleted_at": None,
        **extra,
    }


def reset_and_seed(db: Session) -> None:
    """Idempotent: clear academy tables then insert one stable fictional dataset."""
    for model in (
        LearningRecord,
        Registration,
        Application,
        Review,
        Roster,
        CourseSession,
        Course,
        Contact,
    ):
        db.execute(delete(model))
    db.commit()

    contacts = [
        Contact(
            **_common(
                SITE_A,
                C_A1,
                display_name="Fictional Member One",
                mobile=MOBILE_A1,
                owner_manager_id=U_MANAGER_A,
            )
        ),
        Contact(
            **_common(
                SITE_A,
                C_A2,
                display_name="Fictional Member Two",
                mobile=MOBILE_A2,
                owner_manager_id=U_EMPLOYEE_A,
            )
        ),
        Contact(
            **_common(SITE_B, C_B1, display_name="Fictional Member Three", mobile=MOBILE_B1)
        ),
    ]
    courses = [
        Course(**_common(SITE_A, COURSE_A, title="Fictional Course A", summary="seed", price_cents=19900)),
        Course(**_common(SITE_A, COURSE_A2, title="Fictional Course A2", summary="seed")),
        Course(**_common(SITE_B, COURSE_B, title="Fictional Course B", summary="seed")),
    ]
    sessions = [
        CourseSession(**_common(SITE_A, SESSION_A, course_id=COURSE_A, title="Session A", capacity=30)),
        CourseSession(**_common(SITE_B, SESSION_B, course_id=COURSE_B, title="Session B", capacity=30)),
    ]
    rosters = [
        Roster(
            **_common(
                SITE_A,
                ROSTER_A1,
                session_id=SESSION_A,
                contact_id=C_A1,
                owner_manager_id=U_MANAGER_A,
            )
        ),
        Roster(
            **_common(
                SITE_A,
                ROSTER_A2,
                session_id=SESSION_A,
                contact_id=C_A2,
                owner_manager_id=U_EMPLOYEE_A,
            )
        ),
        # Real club-B roster: used to prove A-club staff get 404 on an object
        # that genuinely exists in club B (not a made-up id).
        Roster(
            **_common(
                SITE_B,
                ROSTER_B1,
                session_id=SESSION_B,
                contact_id=C_B1,
                owner_manager_id=U_EMPLOYEE_B,
            )
        ),
    ]
    reviews = [
        Review(
            **_common(
                SITE_A,
                REVIEW_A_PLAIN,
                course_id=COURSE_A,
                contact_id=C_A1,
                reviewer_name="Fictional Reviewer One",
                is_anonymous=False,
                rating=5,
                comment="fine",
            )
        ),
        Review(
            **_common(
                SITE_A,
                REVIEW_A_ANON,
                course_id=COURSE_A,
                contact_id=C_A2,
                reviewer_name="Fictional Reviewer Two",
                is_anonymous=True,
                rating=4,
                comment="anonymous note",
            )
        ),
        # Real club-B review: proof of cross-club 404 / DELETE isolation.
        Review(
            **_common(
                SITE_B,
                REVIEW_B_PLAIN,
                course_id=COURSE_B,
                contact_id=C_B1,
                reviewer_name="Fictional Reviewer B",
                is_anonymous=False,
                rating=5,
                comment="club B note",
            )
        ),
    ]
    registrations = [
        Registration(**_common(SITE_A, REG_A1, session_id=SESSION_A, contact_id=C_A1)),
        Registration(**_common(SITE_A, REG_A2, session_id=SESSION_A, contact_id=C_A2)),
    ]
    applications = [
        Application(**_common(SITE_A, APP_A1, course_id=COURSE_A, contact_id=C_A1)),
        Application(**_common(SITE_A, APP_A2, course_id=COURSE_A2, contact_id=C_A2)),
    ]
    learnings = [
        LearningRecord(
            **_common(
                SITE_A,
                LEARN_A1,
                session_id=SESSION_A,
                contact_id=C_A1,
                owner_manager_id=U_MANAGER_A,
                progress_pct=60,
            )
        ),
        LearningRecord(
            **_common(
                SITE_A,
                LEARN_A2,
                session_id=SESSION_A,
                contact_id=C_A2,
                owner_manager_id=U_EMPLOYEE_A,
                progress_pct=30,
            )
        ),
    ]
    # Insert in FK order with explicit flushes: contacts/courses first, then
    # sessions, then every dependent table. Avoids flush-order surprises when
    # the session has pending objects from a previous test in it.
    db.add_all(contacts)
    db.add_all(courses)
    db.flush()
    db.add_all(sessions)
    db.flush()
    db.add_all(rosters)
    db.add_all(reviews)
    db.add_all(registrations)
    db.add_all(applications)
    db.add_all(learnings)
    db.commit()


def all_ids() -> dict[str, str]:
    """Stable id map for test parameterisation."""
    names = [
        "ORG", "SITE_A", "SITE_B", "U_PLATFORM_ADMIN", "U_ORG_ADMIN", "U_CLUB_ADMIN_A",
        "U_EMPLOYEE_A", "U_MANAGER_A", "U_EMPLOYEE_B", "U_MEMBER_A1", "U_MEMBER_A2",
        "U_MEMBER_B1", "C_A1", "C_A2", "C_B1", "COURSE_A", "COURSE_A2", "COURSE_B",
        "SESSION_A", "SESSION_B", "ROSTER_A1", "ROSTER_A2", "ROSTER_B1", "REVIEW_A_PLAIN",
        "REVIEW_A_ANON", "REVIEW_B_PLAIN", "REG_A1", "REG_A2", "APP_A1", "LEARN_A1", "LEARN_A2",
    ]
    return {n: str(globals()[n]) for n in names}
