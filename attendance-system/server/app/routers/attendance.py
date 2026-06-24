"""
Attendance router — student claims and reports.
"""
import asyncio
from datetime import datetime, timedelta, timezone

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
from app.models.seat import Seat
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from app.schemas.session import AttendanceClaim, AttendanceRecordOut, SessionReport
from app.services.rfid_scanner import scanner_service, ScanStatus
from app.services.scan_service import apply_update_scan

router = APIRouter()

# How long a claim will wait for its automated verification scan to finish.
SCAN_WAIT_SECONDS = 180


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
    if not enrollment.scalars().first():
        return await _reject(db, data, current_user.id, "Not enrolled in this course")

    # 5. Duplicate check
    existing = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == data.session_id,
            AttendanceRecord.student_id == current_user.id,
        )
    )
    if existing.scalars().first():
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

    # Enrich each record with the student's name and human student_id so the
    # report shows the same identifiers as the admin panel (not the UUID).
    student_ids = {r.student_id for r in records}
    if student_ids:
        users_result = await db.execute(select(User).where(User.id.in_(student_ids)))
        users = {u.id: u for u in users_result.scalars().all()}
        for r in records:
            u = users.get(r.student_id)
            r.student_name = u.full_name if u else None
            r.student_number = u.student_id if u else None

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


class RevokeRequest(BaseModel):
    reason: str | None = None


@router.post("/records/{record_id}/revoke")
async def revoke_record(
    record_id: str,
    data: RevokeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.lecturer, UserRole.hod)),
):
    """Lecturer/HoD manually revokes a student's attendance claim."""
    result = await db.execute(
        select(AttendanceRecord).where(AttendanceRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if record.status == AttendanceStatus.revoked:
        raise HTTPException(status_code=409, detail="Claim is already revoked")

    record.status = AttendanceStatus.revoked
    record.revocation_reason = (data.reason or "Revoked by lecturer")[:100]
    await db.flush()
    await db.refresh(record)
    return {
        "success": True,
        "record_id": str(record.id),
        "status": record.status.value,
        "revocation_reason": record.revocation_reason,
    }


class PublicAttendanceClaim(BaseModel):
    session_id: str
    student_name: str
    tag_number: str


@router.get("/public/session-info/{session_id}")
async def public_session_info(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get public session information including classroom name and available seats."""
    # 1. Find session and classroom
    result = await db.execute(
        select(AttendanceSession)
        .options(selectinload(AttendanceSession.classroom))
        .where(AttendanceSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # 2. Find seats and their states
    seats_result = await db.execute(
        select(Seat, SeatState)
        .join(SeatState, SeatState.seat_id == Seat.id)
        .where(SeatState.session_id == session_id)
    )
    rows = seats_result.all()
    
    seats_out = [
        {
            "seat_id": str(seat.id),
            "label": seat.label,
            "is_occupied": state.is_occupied,
        }
        for seat, state in rows
    ]
    
    return {
        "classroom_name": session.classroom.name if session.classroom else "Unknown Classroom",
        "expires_at": session.t_expiry.isoformat(),
        "seats": seats_out
    }


@router.post("/public/claim")
async def public_submit_claim(
    data: PublicAttendanceClaim,
    db: AsyncSession = Depends(get_db),
):
    """Student submits an attendance claim from the public page."""
    # 1. Find session
    session_result = await db.execute(
        select(AttendanceSession).where(AttendanceSession.id == data.session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if session.status != SessionStatus.active:
        raise HTTPException(status_code=400, detail="Session not active")
        
    now = datetime.now(timezone.utc)
    if now > session.t_expiry:
        raise HTTPException(status_code=400, detail="Session expired")

    # 2. Find User by full_name
    # Case-insensitive match on full_name
    user_result = await db.execute(
        select(User).where(
            User.role == UserRole.student,
            func.lower(User.full_name) == data.student_name.lower()
        )
    )
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Student not found. Please enter your exact registered name.")
        
    # 3. Find seat by tag_number (label)
    seat_result = await db.execute(
        select(Seat).where(
            Seat.classroom_id == session.classroom_id,
            func.lower(Seat.label) == data.tag_number.lower()
        )
    )
    seat = seat_result.scalar_one_or_none()
    if not seat:
        raise HTTPException(status_code=404, detail="Seat tag not found")
        
    # 4. Check enrollment
    enrollment = await db.execute(
        select(Enrollment).where(
            Enrollment.student_id == user.id,
            Enrollment.course_id == session.course_id,
        )
    )
    if not enrollment.scalars().first():
        raise HTTPException(status_code=403, detail="Not enrolled in this course")

    # 5. Look up any existing claim. A previous PRESENT or REVOKED claim is
    #    final; a previous REJECTED claim may be retried (student sat down).
    existing_res = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session.id,
            AttendanceRecord.student_id == user.id,
        )
    )
    existing = existing_res.scalars().first()
    if existing and existing.status != AttendanceStatus.rejected:
        raise HTTPException(status_code=409, detail="Claim already submitted for this session")

    # 6. Run an automated UPDATE scan to confirm the seat is really occupied.
    #    Tags sit on the chairs; a tag the scan can NO LONGER find is being
    #    blocked by a person sitting there → that seat counts as occupied and
    #    the student may be marked present.
    all_seats_result = await db.execute(
        select(Seat).where(Seat.classroom_id == session.classroom_id)
    )
    all_seats = all_seats_result.scalars().all()
    scanner_tag_map = {s.tag_id: s.label for s in all_seats if s.tag_id}  # {card_id: label}
    tag_map_fwd = {s.label: s.tag_id for s in all_seats if s.tag_id}      # {label: card_id}

    started = scanner_service.start_scan(
        session_id=str(session.id),
        tag_map=scanner_tag_map,
    )
    if "error" in started:
        # Another scan is already running (e.g. the lecturer's manual scan).
        raise HTTPException(
            status_code=409,
            detail=f"Could not start the verification scan: {started['error']}. Please try again in a moment.",
        )

    # Wait (bounded) for the background scan thread to finish.
    deadline = datetime.now(timezone.utc) + timedelta(seconds=SCAN_WAIT_SECONDS)
    while scanner_service.status["status"] == ScanStatus.SCANNING:
        if datetime.now(timezone.utc) > deadline:
            raise HTTPException(status_code=504, detail="The verification scan timed out. Please try again.")
        await asyncio.sleep(0.5)

    scan_state = scanner_service.status
    if scan_state["status"] == ScanStatus.ERROR:
        raise HTTPException(
            status_code=502,
            detail=f"The verification scan failed: {scan_state.get('error') or 'reader/stepper error'}",
        )

    results = scanner_service.results or {}

    # Apply the scan to the digital twin (marks every seat occupied/empty), then
    # commit so the refreshed twin is saved even if this claim ends up rejected.
    try:
        await apply_update_scan(db, session, results, tag_map_fwd)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()

    # The claimed seat is "occupied" iff its tag was NOT found by this scan.
    detected_labels = set((results.get("tags_summary") or {}).keys())
    seat_empty = seat.label in detected_labels

    # Upsert the student's record for this session (reuse a prior rejected row).
    if existing is not None:
        record = existing
        record.seat_id = seat.id
        record.claimed_at = now
    else:
        record = AttendanceRecord(
            session_id=session.id,
            student_id=user.id,
            seat_id=seat.id,
            status=AttendanceStatus.present,  # overwritten below
            claimed_at=now,
        )
        db.add(record)

    if seat_empty:
        # Scan still sees the tag → nobody is blocking it → record as REJECTED.
        record.status = AttendanceStatus.rejected
        record.rejection_reason = "Seat empty - tag still detected by scan"
        record.revocation_reason = None
        await db.commit()  # persist the rejected record before returning the error
        raise HTTPException(
            status_code=400,
            detail=(
                f"Tag {seat.label} was still detected, so the seat reads as empty. "
                "Your claim was recorded as rejected — sit so the tag is blocked and try again."
            ),
        )

    # Seat occupied → mark PRESENT.
    record.status = AttendanceStatus.present
    record.rejection_reason = None
    record.revocation_reason = None
    await db.flush()

    return {"success": True, "message": f"Attendance recorded for {user.full_name}!"}
