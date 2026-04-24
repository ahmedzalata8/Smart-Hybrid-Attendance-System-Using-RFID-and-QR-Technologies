"""Seat model — individual seat with RFID tag mapping."""
from sqlalchemy import String, Integer, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDPrimaryKey


class Seat(Base, UUIDPrimaryKey):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("classroom_id", "row", "col", name="uq_seat_position"),
        UniqueConstraint("classroom_id", "label", name="uq_seat_label"),
    )

    classroom_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classrooms.id"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(20), nullable=False)
    row: Mapped[int] = mapped_column(Integer, nullable=False)
    col: Mapped[int] = mapped_column(Integer, nullable=False)
    tag_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Dynamic spatial position (percentage 0–100) from RFID calibration scan.
    # When set, these override the static row/col grid for rendering.
    x_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    y_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    classroom = relationship("Classroom", back_populates="seats")
    seat_states = relationship("SeatState", back_populates="seat")
    seat_state_history = relationship("SeatStateHistory", back_populates="seat")
    attendance_records = relationship("AttendanceRecord", back_populates="seat")
