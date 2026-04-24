"""AttendanceSession model — a single lecture session."""
import enum
from datetime import datetime

from sqlalchemy import String, Integer, Text, Enum, ForeignKey, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDPrimaryKey, TimestampMixin


class SessionStatus(str, enum.Enum):
    active = "active"
    closed = "closed"


class AttendanceSession(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "attendance_sessions"
    __table_args__ = (
        Index("ix_session_course_status", "course_id", "status"),
    )

    course_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False
    )
    classroom_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classrooms.id"), nullable=False
    )
    lecturer_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    class_id: Mapped["UUID | None"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("course_classes.id"), nullable=True
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"), default=SessionStatus.active, nullable=False
    )
    t_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    t_expiry: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    qr_token: Mapped[str] = mapped_column(Text, nullable=False)
    freshness_delta_sec: Mapped[int] = mapped_column(Integer, default=120, nullable=False)
    min_presence_pct: Mapped[int] = mapped_column(Integer, default=75, nullable=False)
    integrity_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    course = relationship("Course", back_populates="attendance_sessions")
    classroom = relationship("Classroom", back_populates="attendance_sessions")
    lecturer = relationship("User", back_populates="attendance_sessions")
    course_class = relationship("CourseClass", back_populates="attendance_sessions")
    seat_states = relationship("SeatState", back_populates="session")
    seat_state_history = relationship("SeatStateHistory", back_populates="session")
    attendance_records = relationship("AttendanceRecord", back_populates="session")
    audit_logs = relationship("AuditLog", back_populates="session")
    scan_reports = relationship("ScanReport", back_populates="session")
