"""RFIDReading — raw audit log of every RFID tag detection during 360° scans."""
from datetime import datetime

from sqlalchemy import String, Float, Integer, ForeignKey, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDPrimaryKey


class RFIDReading(Base, UUIDPrimaryKey):
    __tablename__ = "rfid_readings"
    __table_args__ = (
        Index("ix_rfid_readings_session", "session_id"),
        Index("ix_rfid_readings_tag", "tag_hex_id"),
        Index("ix_rfid_readings_timestamp", "detected_at"),
    )

    session_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attendance_sessions.id"), nullable=False
    )
    tag_hex_id: Mapped[str] = mapped_column(String(200), nullable=False)
    tag_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    seat_label: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Spatial / motor data
    angle_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    step_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    direction: Mapped[str | None] = mapped_column(String(10), nullable=True)  # 'CW' or 'CCW'
    quadrant: Mapped[str | None] = mapped_column(String(10), nullable=True)  # 'Q1','Q2','Q3','Q4'

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    session = relationship("AttendanceSession", back_populates="rfid_readings")
