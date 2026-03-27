"""Classroom model — physical rooms with a seat grid layout."""
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDPrimaryKey, TimestampMixin


class Classroom(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "classrooms"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    department_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False
    )
    building: Mapped[str | None] = mapped_column(String(100), nullable=True)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    layout_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    layout_cols: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    department = relationship("Department", back_populates="classrooms")
    seats = relationship("Seat", back_populates="classroom")
    attendance_sessions = relationship("AttendanceSession", back_populates="classroom")
