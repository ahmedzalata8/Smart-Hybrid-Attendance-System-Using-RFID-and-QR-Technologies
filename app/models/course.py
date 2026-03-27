"""Course model."""
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDPrimaryKey, TimestampMixin


class Course(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    department_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False
    )
    lecturer_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    # Relationships
    department = relationship("Department", back_populates="courses")
    lecturer = relationship("User", foreign_keys=[lecturer_id])
    enrollments = relationship("Enrollment", back_populates="course")
    attendance_sessions = relationship("AttendanceSession", back_populates="course")
