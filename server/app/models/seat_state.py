"""SeatState model — live occupancy snapshot per seat per session."""
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDPrimaryKey


class SeatState(Base, UUIDPrimaryKey):
    __tablename__ = "seat_states"
    __table_args__ = (
        UniqueConstraint("session_id", "seat_id", name="uq_seat_state_session_seat"),
        Index("ix_seat_states_session", "session_id"),
    )

    session_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attendance_sessions.id"), nullable=False
    )
    seat_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seats.id"), nullable=False
    )
    is_occupied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    session = relationship("AttendanceSession", back_populates="seat_states")
    seat = relationship("Seat", back_populates="seat_states")
