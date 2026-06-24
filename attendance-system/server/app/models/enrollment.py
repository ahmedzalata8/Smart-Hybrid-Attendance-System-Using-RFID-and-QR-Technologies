"""Enrollment model — student ↔ course/class many-to-many."""
from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDPrimaryKey


class Enrollment(Base, UUIDPrimaryKey):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "class_id", name="uq_enrollment_student_course_class"),
    )

    student_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    course_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False
    )
    class_id: Mapped["UUID | None"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_classes.id"), nullable=True
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    course_class = relationship("CourseClass", back_populates="enrollments")
