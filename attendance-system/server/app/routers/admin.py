"""
Admin router — manage users, courses, classes, and enrollments.
Requires 'admin' role.
"""
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, String, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_role
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.course import Course
from app.models.course_class import CourseClass
from app.models.enrollment import Enrollment
from app.models.department import Department
from app.models.classroom import Classroom
from app.schemas.admin import (
    AdminUserCreate, AdminUserUpdate, AdminUserOut,
    AdminCourseCreate, AdminCourseUpdate, AdminCourseOut,
    AdminClassCreate, AdminClassUpdate, AdminClassOut,
    AdminEnrollmentCreate, AdminEnrollmentOut
)

router = APIRouter()

# ── Users ──

@router.get("/users", response_model=List[AdminUserOut])
async def list_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    query = select(User)
    if role:
        query = query.where(User.role == role)
    if search:
        search_term = f"%{search}%"
        query = query.where(or_(
            User.full_name.ilike(search_term),
            User.email.ilike(search_term),
            User.student_id.ilike(search_term)
        ))
    query = query.order_by(User.full_name)
    result = await db.execute(query)
    users = result.scalars().all()
    for u in users:
        u.role = u.role.value if hasattr(u.role, 'value') else u.role
    return users


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        student_id=data.student_id,
        department_id=data.department_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    user.role = user.role.value if hasattr(user.role, 'value') else user.role
    return user


@router.put("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: str,
    data: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.email:
        user.email = data.email
    if data.full_name:
        user.full_name = data.full_name
    if data.role:
        user.role = data.role
    if data.student_id is not None:
        user.student_id = data.student_id
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.password:
        user.hashed_password = hash_password(data.password)

    await db.commit()
    await db.refresh(user)
    user.role = user.role.value if hasattr(user.role, 'value') else user.role
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.delete(user)
    await db.commit()
    return None


# ── Courses ──

@router.get("/courses", response_model=List[AdminCourseOut])
async def list_courses(
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    query = select(Course).options(selectinload(Course.lecturer))
    if search:
        search_term = f"%{search}%"
        query = query.where(or_(
            Course.name.ilike(search_term),
            Course.code.ilike(search_term)
        ))
    query = query.order_by(Course.code)
    result = await db.execute(query)
    courses = result.scalars().all()
    
    for c in courses:
        c.lecturer_name = c.lecturer.full_name if c.lecturer else None
    return courses


@router.post("/courses", response_model=AdminCourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(
    data: AdminCourseCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    course = Course(
        id=str(uuid.uuid4()),
        code=data.code,
        name=data.name,
        department_id=data.department_id,
        lecturer_id=data.lecturer_id,
    )
    db.add(course)
    await db.commit()
    
    # Reload to get lecturer
    result = await db.execute(select(Course).options(selectinload(Course.lecturer)).where(Course.id == course.id))
    loaded_course = result.scalar_one()
    loaded_course.lecturer_name = loaded_course.lecturer.full_name if loaded_course.lecturer else None
    return loaded_course


@router.put("/courses/{course_id}", response_model=AdminCourseOut)
async def update_course(
    course_id: str,
    data: AdminCourseUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(Course).options(selectinload(Course.lecturer)).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if data.code:
        course.code = data.code
    if data.name:
        course.name = data.name
    if data.lecturer_id:
        course.lecturer_id = data.lecturer_id

    await db.commit()
    
    # Reload
    result = await db.execute(select(Course).options(selectinload(Course.lecturer)).where(Course.id == course.id))
    loaded = result.scalar_one()
    loaded.lecturer_name = loaded.lecturer.full_name if loaded.lecturer else None
    return loaded


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    await db.delete(course)
    await db.commit()
    return None


# ── Classes ──

@router.get("/classes", response_model=List[AdminClassOut])
async def list_classes(
    course_id: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    query = select(CourseClass).options(
        selectinload(CourseClass.course),
        selectinload(CourseClass.lecturer),
        selectinload(CourseClass.classroom)
    )
    if course_id:
        query = query.where(CourseClass.course_id == course_id)
    if search:
        search_term = f"%{search}%"
        query = query.join(CourseClass.course).where(
            or_(Course.code.ilike(search_term), Course.name.ilike(search_term))
        )
        
    query = query.order_by(CourseClass.day_of_week)
    result = await db.execute(query)
    classes = result.scalars().all()
    
    for c in classes:
        c.course_code = c.course.code if c.course else None
        c.classroom_name = c.classroom.name if c.classroom else None
        c.lecturer_name = c.lecturer.full_name if c.lecturer else None
        
    return classes

@router.post("/classes", response_model=AdminClassOut, status_code=status.HTTP_201_CREATED)
async def create_class(
    data: AdminClassCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    c = CourseClass(
        id=str(uuid.uuid4()),
        course_id=data.course_id,
        classroom_id=data.classroom_id,
        lecturer_id=data.lecturer_id,
        day_of_week=data.day_of_week,
        start_time=data.start_time,
        end_time=data.end_time,
        group_name=data.group_name,
    )
    db.add(c)
    await db.commit()
    
    result = await db.execute(select(CourseClass).options(
        selectinload(CourseClass.course),
        selectinload(CourseClass.lecturer),
        selectinload(CourseClass.classroom)
    ).where(CourseClass.id == c.id))
    loaded = result.scalar_one()
    loaded.course_code = loaded.course.code if loaded.course else None
    loaded.classroom_name = loaded.classroom.name if loaded.classroom else None
    loaded.lecturer_name = loaded.lecturer.full_name if loaded.lecturer else None
    
    return loaded

@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(
    class_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(CourseClass).where(CourseClass.id == class_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Class not found")
    
    await db.delete(c)
    await db.commit()
    return None

# ── Enrollments ──

@router.get("/enrollments", response_model=List[AdminEnrollmentOut])
async def list_enrollments(
    student_id: Optional[str] = None,
    course_id: Optional[str] = None,
    class_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    query = select(Enrollment).options(
        selectinload(Enrollment.student),
        selectinload(Enrollment.course),
        selectinload(Enrollment.course_class)
    )
    if student_id:
        query = query.where(Enrollment.student_id == student_id)
    if course_id:
        query = query.where(Enrollment.course_id == course_id)
    if class_id:
        query = query.where(Enrollment.class_id == class_id)
    
    result = await db.execute(query)
    enrollments = result.scalars().all()
    
    for e in enrollments:
        e.student_name = e.student.full_name if e.student else None
        e.student_identifier = e.student.student_id if e.student else None
        e.course_code = e.course.code if e.course else None
        e.class_group = e.course_class.group_name if e.course_class else None
        
    return enrollments

@router.post("/enrollments", response_model=AdminEnrollmentOut, status_code=status.HTTP_201_CREATED)
async def create_enrollment(
    data: AdminEnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    e = Enrollment(
        id=str(uuid.uuid4()),
        student_id=data.student_id,
        course_id=data.course_id,
        class_id=data.class_id,
    )
    db.add(e)
    await db.commit()
    
    result = await db.execute(select(Enrollment).options(
        selectinload(Enrollment.student),
        selectinload(Enrollment.course),
        selectinload(Enrollment.course_class)
    ).where(Enrollment.id == e.id))
    loaded = result.scalar_one()
    loaded.student_name = loaded.student.full_name if loaded.student else None
    loaded.student_identifier = loaded.student.student_id if loaded.student else None
    loaded.course_code = loaded.course.code if loaded.course else None
    loaded.class_group = loaded.course_class.group_name if loaded.course_class else None
    
    return loaded

@router.delete("/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enrollment(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
    e = result.scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    await db.delete(e)
    await db.commit()
    return None

# ── Reference Data (Departments, Classrooms) ──
@router.get("/departments")
async def list_departments(db: AsyncSession = Depends(get_db), admin: User = Depends(require_role(UserRole.admin))):
    result = await db.execute(select(Department))
    depts = result.scalars().all()
    return [{"id": str(d.id), "name": d.name} for d in depts]

@router.get("/classrooms")
async def list_classrooms(db: AsyncSession = Depends(get_db), admin: User = Depends(require_role(UserRole.admin))):
    result = await db.execute(select(Classroom))
    rooms = result.scalars().all()
    return [{"id": str(r.id), "name": r.name} for r in rooms]
