"""Pydantic schemas for Auth endpoints."""
from uuid import UUID
from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


# ── Requests ──

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole
    student_id: str | None = None
    department_id: UUID


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Responses ──

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    student_id: str | None
    department_id: UUID
    is_active: bool

    model_config = {"from_attributes": True}
