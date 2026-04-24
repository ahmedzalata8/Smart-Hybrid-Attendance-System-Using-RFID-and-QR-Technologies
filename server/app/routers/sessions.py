"""
Sessions router — create, list, and close attendance sessions.
Also handles CourseClass CRUD and student roster queries.
"""
import json
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.attendance_record import AttendanceRecord, AttendanceStatus
from app.models.seat_state import SeatState
from app.models.classroom import Classroom
from app.models.seat import Seat
from app.models.course import Course
from app.models.course_class import CourseClass
from app.models.enrollment import Enrollment
from app.schemas.session import (
    SessionCreate, SessionOut, SessionBrief,
    CourseClassOut, CourseClassBrief, StudentOut, ClassSessionOut,
)
from app.services.qr_service import generate_qr_token

router = APIRouter()

DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


# ── Courses ──

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


@router.get("/courses/{course_id}/students", response_model=list[StudentOut])
async def list_course_students(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.lecturer, UserRole.hod)),
):
    """Get all students enrolled in a course (across all classes)."""
    result = await db.execute(
        select(Enrollment, User)
        .join(User, Enrollment.student_id == User.id)
        .where(Enrollment.course_id == course_id)
        .order_by(User.full_name)
    )
    rows = result.all()
    # Deduplicate by student (a student may be in multiple classes)
    seen = set()
    students = []
    for enrollment, user in rows:
        if user.id not in seen:
            seen.add(user.id)
            students.append(StudentOut(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                student_id=user.student_id,
                enrolled_at=enrollment.enrolled_at,
            ))
    return students


# ── CourseClass (Scheduled Classes) ──

@router.get("/classes", response_model=list[CourseClassOut])
async def list_my_classes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return scheduled classes for the current lecturer (or all dept classes for HoD)."""
    query = select(CourseClass).options(
        selectinload(CourseClass.course),
        selectinload(CourseClass.lecturer),
        selectinload(CourseClass.classroom),
    )
    if current_user.role == UserRole.lecturer:
        query = query.where(CourseClass.lecturer_id == current_user.id)
    elif current_user.role == UserRole.hod:
        query = query.join(Course).where(Course.department_id == current_user.department_id)

    query = query.order_by(CourseClass.day_of_week, CourseClass.start_time)
    result = await db.execute(query)
    classes = result.scalars().all()

    return [
        CourseClassOut(
            id=c.id,
            course_id=c.course_id,
            course_code=c.course.code if c.course else None,
            course_name=c.course.name if c.course else None,
            lecturer_id=c.lecturer_id,
            lecturer_name=c.lecturer.full_name if c.lecturer else None,
            classroom_id=c.classroom_id,
            classroom_name=c.classroom.name if c.classroom else None,
            day_of_week=c.day_of_week,
            start_time=c.start_time,
            end_time=c.end_time,
            group_name=c.group_name,
        )
        for c in classes
    ]


@router.get("/classes/{class_id}/students", response_model=list[StudentOut])
async def list_class_students(
    class_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.lecturer, UserRole.hod)),
):
    """Get students enrolled in a specific class (section)."""
    result = await db.execute(
        select(Enrollment, User)
        .join(User, Enrollment.student_id == User.id)
        .where(Enrollment.class_id == class_id)
        .order_by(User.full_name)
    )
    rows = result.all()
    return [
        StudentOut(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            student_id=user.student_id,
            enrolled_at=enrollment.enrolled_at,
        )
        for enrollment, user in rows
    ]


@router.get("/classes/{class_id}/sessions", response_model=list[ClassSessionOut])
async def list_class_sessions(
    class_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.lecturer, UserRole.hod)),
):
    """Get all past/current sessions for a specific class, with attendance summary."""
    # Get sessions for this class
    sessions_result = await db.execute(
        select(AttendanceSession)
        .where(AttendanceSession.class_id == class_id)
        .order_by(AttendanceSession.t_start.desc())
    )
    sessions = sessions_result.scalars().all()

    # Get total enrolled in this class
    enrolled_count_result = await db.execute(
        select(func.count()).select_from(Enrollment).where(Enrollment.class_id == class_id)
    )
    total_enrolled = enrolled_count_result.scalar() or 0

    output = []
    for s in sessions:
        # Get attendance records for this session
        att_result = await db.execute(
            select(AttendanceRecord, User)
            .join(User, AttendanceRecord.student_id == User.id)
            .where(
                AttendanceRecord.session_id == s.id,
                AttendanceRecord.status == AttendanceStatus.present,
            )
        )
        present_rows = att_result.all()
        present_names = [user.full_name for _, user in present_rows]

        output.append(ClassSessionOut(
            id=s.id,
            t_start=s.t_start,
            t_expiry=s.t_expiry,
            status=s.status.value,
            present_count=len(present_names),
            total_enrolled=total_enrolled,
            students_present=present_names,
        ))

    return output


# ── Session CRUD ──

@router.post("/", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.lecturer)),
):
    """Lecturer creates a new attendance session."""
    # If class_id provided, derive course/classroom from the class
    course_id = data.course_id
    classroom_id = data.classroom_id
    class_id = data.class_id

    if class_id:
        cc_result = await db.execute(
            select(CourseClass).where(CourseClass.id == class_id)
        )
        cc = cc_result.scalar_one_or_none()
        if not cc:
            raise HTTPException(status_code=404, detail="Class not found")
        course_id = cc.course_id
        classroom_id = cc.classroom_id

    # Generate QR token
    qr_token = generate_qr_token(
        session_data={
            "course_id": str(course_id),
            "classroom_id": str(classroom_id),
            "t_start": data.t_start.isoformat(),
            "t_expiry": data.t_expiry.isoformat(),
        }
    )

    session = AttendanceSession(
        course_id=course_id,
        classroom_id=classroom_id,
        lecturer_id=current_user.id,
        class_id=class_id,
        t_start=data.t_start,
        t_expiry=data.t_expiry,
        qr_token=qr_token,
        freshness_delta_sec=data.freshness_delta_sec,
        min_presence_pct=data.min_presence_pct,
    )
    db.add(session)
    await db.flush()

    # Pre-populate seat_states for this session (all empty)
    seats_result = await db.execute(select(Seat).where(Seat.classroom_id == classroom_id))
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
    query = select(AttendanceSession).options(
        selectinload(AttendanceSession.course).selectinload(Course.lecturer),
        selectinload(AttendanceSession.course_class),
    )

    if current_user.role == UserRole.lecturer:
        query = query.where(AttendanceSession.lecturer_id == current_user.id)
    elif current_user.role == UserRole.hod:
        # HoD sees sessions for courses in their department
        query = query.join(Course).where(Course.department_id == current_user.department_id)

    query = query.order_by(AttendanceSession.created_at.desc())
    result = await db.execute(query)
    sessions = result.scalars().all()

    return [
        SessionBrief(
            id=s.id,
            course_id=s.course_id,
            class_id=s.class_id,
            status=s.status,
            t_start=s.t_start,
            t_expiry=s.t_expiry,
            course_name=s.course.name if s.course else None,
            course_code=s.course.code if s.course else None,
            lecturer_name=s.course.lecturer.full_name if s.course and s.course.lecturer else None,
            class_group=s.course_class.group_name if s.course_class else None,
            class_day=s.course_class.day_of_week if s.course_class else None,
            class_time=f"{s.course_class.start_time}-{s.course_class.end_time}" if s.course_class else None,
        )
        for s in sessions
    ]


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
