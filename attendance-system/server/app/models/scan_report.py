"""ScanReport — raw RFID scan reports from Reader devices."""
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, UUIDPrimaryKey


class ScanReport(Base, UUIDPrimaryKey):
    __tablename__ = "scan_reports"
    __table_args__ = (
        Index("ix_scan_reports_session_time", "session_id", "scanned_at"),
    )

    session_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attendance_sessions.id"), nullable=False
    )
    reader_device_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tags_detected: Mapped[dict] = mapped_column(JSONB, nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    session = relationship("AttendanceSession", back_populates="scan_reports")
