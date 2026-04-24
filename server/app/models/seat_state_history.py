"""SeatStateHistory — occupancy transition log for continuous presence verification."""
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDPrimaryKey, TimestampMixin


class SeatStateHistory(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "seat_state_history"
    __table_args__ = (
        Index(
            "ix_seat_state_history_session_seat_time",
            "session_id", "seat_id", "detected_at",
        ),
    )

    session_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attendance_sessions.id"), nullable=False
    )
    seat_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seats.id"), nullable=False
    )
    is_occupied: Mapped[bool] = mapped_column(Boolean, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    session = relationship("AttendanceSession", back_populates="seat_state_history")
    seat = relationship("Seat", back_populates="seat_state_history")
