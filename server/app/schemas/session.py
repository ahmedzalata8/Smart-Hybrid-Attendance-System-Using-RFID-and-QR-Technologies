"""Pydantic schemas for Session, CourseClass, and Attendance endpoints."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

from app.models.attendance_session import SessionStatus
from app.models.attendance_record import AttendanceStatus


# ── CourseClass (Scheduled Class / Section) ──

class CourseClassOut(BaseModel):
    """Output schema for a scheduled class."""
    id: UUID
    course_id: UUID
    course_code: str | None = None
    course_name: str | None = None
    lecturer_id: UUID
    lecturer_name: str | None = None
    classroom_id: UUID
    classroom_name: str | None = None
    day_of_week: int
    start_time: str
    end_time: str
    group_name: str | None = None

    model_config = {"from_attributes": True}


class CourseClassBrief(BaseModel):
    """Minimal class info for dropdowns."""
    id: UUID
    course_code: str
    course_name: str
    day_of_week: int
    start_time: str
    end_time: str
    group_name: str | None = None
    classroom_name: str | None = None


# ── Student ──

class StudentOut(BaseModel):
    """Student info for enrollment rosters."""
    id: UUID
    full_name: str
    email: str
    student_id: str | None = None
    enrolled_at: datetime | None = None


# ── Class Session Schedule ──

class ClassSessionOut(BaseModel):
    """A past session for a class, with attendance summary."""
    id: UUID
    t_start: datetime
    t_expiry: datetime
    status: str
    present_count: int = 0
    total_enrolled: int = 0
    students_present: list[str] = []  # list of student names


# ── Session ──

class SessionCreate(BaseModel):
    course_id: UUID
    classroom_id: UUID
    class_id: UUID | None = None
    t_start: datetime
    t_expiry: datetime
    freshness_delta_sec: int = 120
    min_presence_pct: int = 75


class SessionOut(BaseModel):
    id: UUID
    course_id: UUID
    classroom_id: UUID
    lecturer_id: UUID
    class_id: UUID | None = None
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
    class_id: UUID | None = None
    status: SessionStatus
    t_start: datetime
    t_expiry: datetime
    course_name: str | None = None
    course_code: str | None = None
    lecturer_name: str | None = None
    class_group: str | None = None
    class_day: int | None = None
    class_time: str | None = None

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
