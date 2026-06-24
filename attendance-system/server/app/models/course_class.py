"""CourseClass model — a scheduled class (section) within a course."""
from sqlalchemy import String, Integer, ForeignKey, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDPrimaryKey, TimestampMixin


class CourseClass(Base, UUIDPrimaryKey, TimestampMixin):
    """
    Represents a specific scheduled class/section for a course.

    A Course (e.g. CS401 Artificial Intelligence) can have multiple classes:
      - Sunday 10:00-12:00 in Room 101 (Group A)
      - Tuesday 14:00-16:00 in Room 203 (Group B)

    Students enroll in specific classes (not just courses).
    Attendance sessions are started for a specific class.
    """
    __tablename__ = "course_classes"

    course_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False
    )
    lecturer_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    classroom_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classrooms.id"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="0=Sunday, 1=Monday, 2=Tuesday, 3=Wednesday, 4=Thursday, 5=Friday, 6=Saturday"
    )
    start_time: Mapped[str] = mapped_column(
        String(5), nullable=False,
        comment="HH:MM format, e.g. 10:00"
    )
    end_time: Mapped[str] = mapped_column(
        String(5), nullable=False,
        comment="HH:MM format, e.g. 12:00"
    )
    group_name: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="Optional section/group label, e.g. Group A, Section 1"
    )

    # Relationships
    course = relationship("Course", back_populates="classes")
    lecturer = relationship("User", foreign_keys=[lecturer_id], back_populates="teaching_classes")
    classroom = relationship("Classroom", back_populates="classes")
    enrollments = relationship("Enrollment", back_populates="course_class")
    attendance_sessions = relationship("AttendanceSession", back_populates="course_class")
