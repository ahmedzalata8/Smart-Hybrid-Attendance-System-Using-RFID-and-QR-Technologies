from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# Users
class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str # student, lecturer, hod, admin
    student_id: Optional[str] = None
    department_id: UUID

class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    student_id: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class AdminUserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    student_id: Optional[str] = None
    department_id: UUID
    is_active: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}

# Courses
class AdminCourseCreate(BaseModel):
    code: str
    name: str
    department_id: UUID
    lecturer_id: UUID

class AdminCourseUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    lecturer_id: Optional[UUID] = None

class AdminCourseOut(BaseModel):
    id: UUID
    code: str
    name: str
    department_id: UUID
    lecturer_id: UUID
    lecturer_name: Optional[str] = None
    
    model_config = {"from_attributes": True}

# Classes
class AdminClassCreate(BaseModel):
    course_id: UUID
    classroom_id: UUID
    lecturer_id: UUID
    day_of_week: int
    start_time: str
    end_time: str
    group_name: Optional[str] = None

class AdminClassUpdate(BaseModel):
    classroom_id: Optional[UUID] = None
    lecturer_id: Optional[UUID] = None
    day_of_week: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    group_name: Optional[str] = None

class AdminClassOut(BaseModel):
    id: UUID
    course_id: UUID
    course_code: Optional[str] = None
    classroom_id: UUID
    classroom_name: Optional[str] = None
    lecturer_id: UUID
    lecturer_name: Optional[str] = None
    day_of_week: int
    start_time: str
    end_time: str
    group_name: Optional[str] = None
    
    model_config = {"from_attributes": True}

# Enrollments
class AdminEnrollmentCreate(BaseModel):
    student_id: UUID
    course_id: UUID
    class_id: Optional[UUID] = None

class AdminEnrollmentOut(BaseModel):
    id: UUID
    student_id: UUID
    student_name: Optional[str] = None
    student_identifier: Optional[str] = None
    course_id: UUID
    course_code: Optional[str] = None
    class_id: Optional[UUID] = None
    class_group: Optional[str] = None
    enrolled_at: datetime
    
    model_config = {"from_attributes": True}
