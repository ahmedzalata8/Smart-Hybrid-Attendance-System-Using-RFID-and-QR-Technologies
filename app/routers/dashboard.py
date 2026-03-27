"""
Dashboard router — Digital Twin and classroom management.
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.attendance_session import AttendanceSession
from app.models.classroom import Classroom
from app.models.seat import Seat
from app.models.seat_state import SeatState
from app.models.attendance_record import AttendanceRecord
from app.schemas.dashboard import DigitalTwinView, SeatStateOut, ClassroomOut

router = APIRouter()


@router.get("/twin/{session_id}", response_model=DigitalTwinView)
async def get_digital_twin(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.hod, UserRole.lecturer)),
):
    """Construct Digital Twin View — merged seat occupancy + attendance (FR-S18, FR-S19)."""
    # Fetch session
    result = await db.execute(
        select(AttendanceSession).where(AttendanceSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # HoD can only view department sessions
    if current_user.role == UserRole.hod:
        from app.models.course import Course
        course_result = await db.execute(
            select(Course).where(Course.id == session.course_id)
        )
        course = course_result.scalar_one_or_none()
        if course and course.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Not in your department")

    # Fetch classroom
    classroom_result = await db.execute(
        select(Classroom).where(Classroom.id == session.classroom_id)
    )
    classroom = classroom_result.scalar_one_or_none()

    # Fetch seat states with seat info
    seat_states_result = await db.execute(
        select(SeatState, Seat)
        .join(Seat, SeatState.seat_id == Seat.id)
        .where(SeatState.session_id == session_id)
    )
    seat_state_rows = seat_states_result.all()

    # Fetch attendance records for this session
    att_result = await db.execute(
        select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
    )
    att_records = {r.seat_id: r for r in att_result.scalars().all()}

    # Build seat list
    seats_out = []
    for seat_state, seat in seat_state_rows:
        att_record = att_records.get(seat.id)
        seats_out.append(SeatStateOut(
            seat_id=seat.id,
            label=seat.label,
            row=seat.row,
            col=seat.col,
            is_occupied=seat_state.is_occupied,
            last_seen_at=seat_state.last_seen_at,
            student_name=None,  # Could be populated by joining User
            attendance_status=att_record.status.value if att_record else None,
        ))

    return DigitalTwinView(
        session_id=session.id,
        classroom_name=classroom.name if classroom else "Unknown",
        layout_rows=classroom.layout_rows if classroom else 0,
        layout_cols=classroom.layout_cols if classroom else 0,
        session_status=session.status.value,
        seats=seats_out,
    )


@router.get("/classrooms", response_model=list[ClassroomOut])
async def list_classrooms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Classroom))
    return result.scalars().all()
