"""
Sessions router — create, list, and close attendance sessions.
"""
import json
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.seat_state import SeatState
from app.models.classroom import Classroom
from app.models.seat import Seat
from app.schemas.session import SessionCreate, SessionOut, SessionBrief
from app.services.qr_service import generate_qr_token
from app.models.course import Course

router = APIRouter()


@router.get("/courses")
async def list_my_courses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return courses for the current lecturer (or all dept courses for HoD)."""
    query = select(Course)
    if current_user.role == UserRole.lecturer:
        query = query.where(Course.lecturer_id == current_user.id)
    elif current_user.role == UserRole.hod:
        query = query.where(Course.department_id == current_user.department_id)
    result = await db.execute(query)
    courses = result.scalars().all()
    return [{"id": str(c.id), "code": c.code, "name": c.name} for c in courses]


@router.post("/", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.lecturer)),
):
    """Lecturer creates a new attendance session."""
    # Generate QR token
    qr_token = generate_qr_token(
        session_data={
            "course_id": str(data.course_id),
            "classroom_id": str(data.classroom_id),
            "t_start": data.t_start.isoformat(),
            "t_expiry": data.t_expiry.isoformat(),
        }
    )

    session = AttendanceSession(
        course_id=data.course_id,
        classroom_id=data.classroom_id,
        lecturer_id=current_user.id,
        t_start=data.t_start,
        t_expiry=data.t_expiry,
        qr_token=qr_token,
        freshness_delta_sec=data.freshness_delta_sec,
        min_presence_pct=data.min_presence_pct,
    )
    db.add(session)
    await db.flush()

    # Pre-populate seat_states for this session (all empty)
    seats_result = await db.execute(select(Seat).where(Seat.classroom_id == data.classroom_id))
    seats = seats_result.scalars().all()
    for seat in seats:
        db.add(SeatState(session_id=session.id, seat_id=seat.id, is_occupied=False))

    await db.flush()
    await db.refresh(session)
    return session


@router.get("/", response_model=list[SessionBrief])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List sessions — lecturers see own, HoD sees department's."""
    query = select(AttendanceSession)

    if current_user.role == UserRole.lecturer:
        query = query.where(AttendanceSession.lecturer_id == current_user.id)
    elif current_user.role == UserRole.hod:
        # HoD sees sessions for courses in their department
        from app.models.course import Course
        query = query.join(Course).where(Course.department_id == current_user.department_id)

    query = query.order_by(AttendanceSession.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AttendanceSession).where(AttendanceSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/close", response_model=SessionOut)
async def close_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.lecturer)),
):
    """Manually close a session and finalize attendance."""
    from app.services.finalization_service import finalize_session

    result = await db.execute(
        select(AttendanceSession).where(AttendanceSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.lecturer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session")
    if session.status == SessionStatus.closed:
        raise HTTPException(status_code=400, detail="Session already closed")

    await finalize_session(db, session)
    await db.refresh(session)
    return session
