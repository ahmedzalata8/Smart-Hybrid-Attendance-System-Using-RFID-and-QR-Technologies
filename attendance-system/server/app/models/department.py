"""Department model."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKey, TimestampMixin


class Department(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "departments"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)

    # Relationships
    users = relationship("User", back_populates="department")
    courses = relationship("Course", back_populates="department")
    classrooms = relationship("Classroom", back_populates="department")
