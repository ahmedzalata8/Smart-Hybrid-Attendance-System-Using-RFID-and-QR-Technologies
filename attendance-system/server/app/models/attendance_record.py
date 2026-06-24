"""AttendanceRecord — one row per student claim attempt."""
import enum
from datetime import datetime

from sqlalchemy import String, Integer, Enum, ForeignKey, DateTime, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDPrimaryKey


class AttendanceStatus(str, enum.Enum):
    present = "present"
    rejected = "rejected"
    revoked = "revoked"


class AttendanceRecord(Base, UUIDPrimaryKey):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_attendance_session_student"),
        Index("ix_attendance_records_session_status", "session_id", "status"),
    )

    session_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attendance_sessions.id"), nullable=False
    )
    student_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    seat_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seats.id"), nullable=False
    )
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status"), nullable=False
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    presence_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    session = relationship("AttendanceSession", back_populates="attendance_records")
    student = relationship("User", back_populates="attendance_records")
    seat = relationship("Seat", back_populates="attendance_records")
