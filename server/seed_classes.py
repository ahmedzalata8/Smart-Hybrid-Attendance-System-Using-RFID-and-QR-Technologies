"""
Seed script — adds CourseClass (scheduled classes) and updates enrollments.
Links existing courses to scheduled time slots and assigns students to classes.
Run: python seed_classes.py
"""
import sys
import asyncio
import uuid
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models.course import Course
from app.models.course_class import CourseClass
from app.models.classroom import Classroom
from app.models.user import User, UserRole
from app.models.enrollment import Enrollment


async def main():
    async with AsyncSessionLocal() as db:
        print("=" * 60)
        print("  SEEDING COURSE CLASSES (SCHEDULED TIME SLOTS)")
        print("=" * 60)

        # Get all courses
        courses_result = await db.execute(select(Course))
        courses = courses_result.scalars().all()
        if not courses:
            print("❌ No courses found. Run main seed script first.")
            return

        # Get classrooms
        classrooms_result = await db.execute(select(Classroom))
        classrooms = classrooms_result.scalars().all()
        if not classrooms:
            print("❌ No classrooms found.")
            return

        # Check if classes already exist
        existing = await db.execute(select(CourseClass).limit(1))
        if existing.scalar_one_or_none():
            print("⚠️  Course classes already exist. Skipping.")
            await db.close()
            return

        classroom = classrooms[0]  # Use first available classroom
        created_classes = []

        for course in courses:
            # Create 2 classes per course: one Sun/Tue, one Mon/Wed
            class1 = CourseClass(
                id=uuid.uuid4(),
                course_id=course.id,
                lecturer_id=course.lecturer_id,
                classroom_id=classroom.id,
                day_of_week=0,  # Sunday
                start_time="10:00",
                end_time="12:00",
                group_name="Group A",
            )
            class2 = CourseClass(
                id=uuid.uuid4(),
                course_id=course.id,
                lecturer_id=course.lecturer_id,
                classroom_id=classroom.id,
                day_of_week=2,  # Tuesday
                start_time="14:00",
                end_time="16:00",
                group_name="Group B",
            )
            db.add(class1)
            db.add(class2)
            created_classes.append((course, class1, class2))
            print(f"✅ Created classes for {course.code} - {course.name}:")
            print(f"   📅 Group A: Sunday 10:00-12:00")
            print(f"   📅 Group B: Tuesday 14:00-16:00")

        await db.flush()

        # Update existing enrollments to link to classes
        # Assign students alternately to Group A and Group B
        for course, class1, class2 in created_classes:
            enrollments_result = await db.execute(
                select(Enrollment).where(Enrollment.course_id == course.id)
            )
            enrollments = enrollments_result.scalars().all()

            for i, enrollment in enumerate(enrollments):
                target_class = class1 if i % 2 == 0 else class2
                enrollment.class_id = target_class.id

            # Also create duplicate enrollments for the other class
            # so all students appear in both groups (common in small courses)
            for enrollment in enrollments:
                other_class = class2 if enrollment.class_id == class1.id else class1
                # Check if already exists
                existing_check = await db.execute(
                    select(Enrollment).where(
                        Enrollment.student_id == enrollment.student_id,
                        Enrollment.course_id == enrollment.course_id,
                        Enrollment.class_id == other_class.id,
                    )
                )
                if not existing_check.scalar_one_or_none():
                    db.add(Enrollment(
                        id=uuid.uuid4(),
                        student_id=enrollment.student_id,
                        course_id=enrollment.course_id,
                        class_id=other_class.id,
                    ))

            print(f"✅ Linked {len(enrollments)} students to {course.code} classes")

        # Link existing sessions to class1 (Group A) for each course
        from app.models.attendance_session import AttendanceSession
        for course, class1, class2 in created_classes:
            sessions_result = await db.execute(
                select(AttendanceSession).where(AttendanceSession.course_id == course.id)
            )
            sessions = sessions_result.scalars().all()
            for session in sessions:
                session.class_id = class1.id
            if sessions:
                print(f"✅ Linked {len(sessions)} existing sessions to {course.code} Group A")

        await db.commit()

        print("\n" + "=" * 60)
        print("  ✅ COURSE CLASSES SEEDED SUCCESSFULLY!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
