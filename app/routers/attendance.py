"""
Attendance router — student claims and reports.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.attendance_record import AttendanceRecord, AttendanceStatus
from app.models.seat_state import SeatState
from app.models.enrollment import Enrollment
from app.schemas.session import AttendanceClaim, AttendanceRecordOut, SessionReport

router = APIRouter()


@router.post("/claim", response_model=AttendanceRecordOut, status_code=status.HTTP_201_CREATED)
async def submit_claim(
    data: AttendanceClaim,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.student)),
):
    """Student submits an attendance claim."""

    # 1. Session validity check (FR-S11)
    result = await db.execute(
        select(AttendanceSession).where(AttendanceSession.id == data.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.active:
        return _reject(db, data, current_user.id, "Session not active")

    # 2. Freshness check (FR-S09)
    now = datetime.now(timezone.utc)
    delta = abs((now - data.claimed_at).total_seconds())
    if delta > session.freshness_delta_sec:
        return await _reject(db, data, current_user.id, "Stale/replayed claim")

    # 3. Session expiry check
    if now > session.t_expiry:
        return await _reject(db, data, current_user.id, "Session expired")

    # 4. Enrollment check (FR-S10)
    enrollment = await db.execute(
        select(Enrollment).where(
            Enrollment.student_id == current_user.id,
            Enrollment.course_id == session.course_id,
        )
    )
    if not enrollment.scalar_one_or_none():
        return await _reject(db, data, current_user.id, "Not enrolled in this course")

    # 5. Duplicate check
    existing = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == data.session_id,
            AttendanceRecord.student_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Claim already submitted for this session")

    # 6. Dual-factor seat check (FR-S12)
    seat_state = await db.execute(
        select(SeatState).where(
            SeatState.session_id == data.session_id,
            SeatState.seat_id == data.seat_id,
        )
    )
    seat_state_row = seat_state.scalar_one_or_none()
    if not seat_state_row or not seat_state_row.is_occupied:
        return await _reject(db, data, current_user.id, "Seat not occupied (dual-factor mismatch)")

    # ✅ All checks pass → mark present
    record = AttendanceRecord(
        session_id=data.session_id,
        student_id=current_user.id,
        seat_id=data.seat_id,
        status=AttendanceStatus.present,
        claimed_at=data.claimed_at,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def _reject(
    db: AsyncSession,
    data: AttendanceClaim,
    student_id,
    reason: str,
) -> AttendanceRecord:
    """Create a rejected attendance record."""
    record = AttendanceRecord(
        session_id=data.session_id,
        student_id=student_id,
        seat_id=data.seat_id,
        status=AttendanceStatus.rejected,
        rejection_reason=reason,
        claimed_at=data.claimed_at,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


@router.get("/report/{session_id}", response_model=SessionReport)
async def session_report(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.lecturer, UserRole.hod)),
):
    """Get attendance report for a session (FR-S17)."""
    result = await db.execute(
        select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
    )
    records = result.scalars().all()

    session_result = await db.execute(
        select(AttendanceSession).where(AttendanceSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    present = sum(1 for r in records if r.status == AttendanceStatus.present)
    rejected = sum(1 for r in records if r.status == AttendanceStatus.rejected)
    revoked = sum(1 for r in records if r.status == AttendanceStatus.revoked)

    return SessionReport(
        session_id=session.id,
        course_id=session.course_id,
        total_claims=len(records),
        present_count=present,
        rejected_count=rejected,
        revoked_count=revoked,
        records=records,
    )
