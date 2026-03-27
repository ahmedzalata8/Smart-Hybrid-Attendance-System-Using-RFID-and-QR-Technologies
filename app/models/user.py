"""User model — Student, Lecturer, HoD."""
import enum

from sqlalchemy import String, Boolean, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, UUIDPrimaryKey, TimestampMixin


class UserRole(str, enum.Enum):
    student = "student"
    lecturer = "lecturer"
    hod = "hod"


class User(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    student_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    department_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    department = relationship("Department", back_populates="users")
    enrollments = relationship("Enrollment", back_populates="student")
    attendance_sessions = relationship("AttendanceSession", back_populates="lecturer")
    attendance_records = relationship("AttendanceRecord", back_populates="student")
