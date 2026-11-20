"""Academy tables. Every business table carries the platform-common columns:
id(UUID), org_id, site_id, created_at, created_by, updated_at, deleted_at(soft delete).

All data in this module is fictional. Monetary values, if any, are integer cents.
Phone numbers are stored as plaintext only in contact.mobile so the test suite can
verify that no other endpoint leaks an 11-digit mobile pattern.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Common(Base):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    org_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    site_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Contact(Common):
    """Mini-program identity. `mobile` is plaintext by design (reveal-mobile only)."""

    __tablename__ = "academy_contact"
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    mobile: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_manager_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)


class Course(Common):
    __tablename__ = "academy_course"
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CourseSession(Common):
    __tablename__ = "academy_session"
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academy_course.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=30, nullable=False)


class Roster(Common):
    __tablename__ = "academy_roster"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academy_session.id"), index=True, nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academy_contact.id"), index=True, nullable=False)
    owner_manager_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Review(Common):
    __tablename__ = "academy_review"
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academy_course.id"), index=True, nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academy_contact.id"), index=True, nullable=False)
    reviewer_name: Mapped[str] = mapped_column(String(80), nullable=False)
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    comment: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Registration(Common):
    __tablename__ = "academy_registration"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academy_session.id"), index=True, nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academy_contact.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="registered", nullable=False)


class Application(Common):
    __tablename__ = "academy_application"
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academy_course.id"), index=True, nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academy_contact.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)


class LearningRecord(Common):
    __tablename__ = "academy_learning_record"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academy_session.id"), index=True, nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("academy_contact.id"), index=True, nullable=False)
    owner_manager_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
