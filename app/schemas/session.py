"""Pydantic schemas for Session and Attendance endpoints."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from app.models.attendance_session import SessionStatus
from app.models.attendance_record import AttendanceStatus


# ── Session ──

class SessionCreate(BaseModel):
    course_id: UUID
    classroom_id: UUID
    t_start: datetime
    t_expiry: datetime
    freshness_delta_sec: int = 120
    min_presence_pct: int = 75


class SessionOut(BaseModel):
    id: UUID
    course_id: UUID
    classroom_id: UUID
    lecturer_id: UUID
    status: SessionStatus
    t_start: datetime
    t_expiry: datetime
    qr_token: str
    freshness_delta_sec: int
    min_presence_pct: int
    integrity_hash: str | None
    created_at: datetime
    finalized_at: datetime | None

    model_config = {"from_attributes": True}


class SessionBrief(BaseModel):
    """Lightweight session info for lists."""
    id: UUID
    course_id: UUID
    status: SessionStatus
    t_start: datetime
    t_expiry: datetime

    model_config = {"from_attributes": True}


# ── Attendance Claim ──

class AttendanceClaim(BaseModel):
    session_id: UUID
    seat_id: UUID
    claimed_at: datetime


class AttendanceRecordOut(BaseModel):
    id: UUID
    session_id: UUID
    student_id: UUID
    seat_id: UUID
    status: AttendanceStatus
    rejection_reason: str | None
    revocation_reason: str | None
    presence_pct: int | None
    claimed_at: datetime
    processed_at: datetime
    finalized_at: datetime | None

    model_config = {"from_attributes": True}


# ── Attendance Report ──

class SessionReport(BaseModel):
    session_id: UUID
    course_id: UUID
    total_claims: int
    present_count: int
    rejected_count: int
    revoked_count: int
    records: list[AttendanceRecordOut]
