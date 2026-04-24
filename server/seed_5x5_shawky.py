import sys
import asyncio
import uuid
import httpx
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.department import Department
from app.models.classroom import Classroom
from app.models.seat import Seat
from app.models.course import Course
from app.models.course_class import CourseClass
from app.models.enrollment import Enrollment

BASE = "http://127.0.0.1:8000"

async def main():
    print("Seeding 5x5 session for Dr. Shawky...")
    
    async with AsyncSessionLocal() as db:
        # Get Dr. Shawky
        shawky_email = "dr.shawky@aast.edu"
        existing = await db.execute(select(User).where(User.email == shawky_email))
        dr_shawky = existing.scalar_one_or_none()
        
        if not dr_shawky:
            print("[X] Dr. Shawky not found. Run main seed script first.")
            return
            
        dept_id = dr_shawky.department_id
        
        import random
        # Create a 5x5 classroom
        classroom_id = str(uuid.uuid4())
        room_name = f"Room 5x5-{random.randint(1000, 9999)}"
        await db.execute(text(
            "INSERT INTO classrooms (id, name, department_id, layout_rows, layout_cols) "
            "VALUES (:id, :name, :dept_id, 5, 5) ON CONFLICT DO NOTHING"
        ), {"id": classroom_id, "name": room_name, "dept_id": dept_id})
        
        # 25 Seats with RFID tags
        seat_ids = []
        tags = []
        for r in range(5):
            for c in range(5):
                sid = str(uuid.uuid4())
                tag = f"RFID-5x5-{r}-{c}-{random.randint(1000,9999)}"
                seat_ids.append(sid)
                tags.append(tag)
                label = f"{chr(65+r)}{c+1}"
                await db.execute(text(
                    "INSERT INTO seats (id, classroom_id, label, row, col, tag_id) "
                    "VALUES (:id, :cid, :label, :row, :col, :tag) ON CONFLICT DO NOTHING"
                ), {"id": sid, "cid": classroom_id, "label": label,
                    "row": r, "col": c, "tag": tag})
        
        # Create course
        course_id = str(uuid.uuid4())
        await db.execute(text(
            "INSERT INTO courses (id, code, name, department_id, lecturer_id) "
            "VALUES (:id, :code, :name, :dept_id, :lec_id) ON CONFLICT DO NOTHING"
        ), {"id": course_id, "code": f"CS5X5-{random.randint(100, 999)}", "name": f"Advanced Grid Computing {random.randint(100, 999)}",
            "dept_id": dept_id, "lec_id": dr_shawky.id})
            
        # Create class
        class_id = str(uuid.uuid4())
        await db.execute(text(
            "INSERT INTO course_classes (id, course_id, lecturer_id, classroom_id, day_of_week, start_time, end_time, group_name) "
            "VALUES (:id, :course_id, :lec_id, :class_id, 0, '10:00', '12:00', 'Group 5x5') ON CONFLICT DO NOTHING"
        ), {"id": class_id, "course_id": course_id, "lec_id": dr_shawky.id, "class_id": classroom_id})
        
        await db.commit()
        
    print("[OK] Classroom, seats, course, and class created in DB.")
    
    # Use API to register students, enroll them, and simulate attendance
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as client:
        student_tokens = []
        student_ids = []
        
        for i in range(15): # 15 students for 25 seats
            # Student register
            email = f"student5x5_{i}@student.edu"
            r = await client.post("/api/auth/register", json={
                "email": email,
                "password": "student123",
                "full_name": f"Dummy Student {i}",
                "role": "student",
                "student_id": f"STU5X5_{i}",
                "department_id": str(dept_id),
            })
            if r.status_code == 201:
                student = r.json()
                student_ids.append(student["id"])
                
                # Login
                rl = await client.post("/api/auth/login", json={
                    "email": email,
                    "password": "student123",
                })
                student_tokens.append(rl.json()["access_token"])
                
                # Enroll directly in DB
                async with AsyncSessionLocal() as db:
                    await db.execute(text(
                        "INSERT INTO enrollments (id, student_id, course_id, class_id) "
                        "VALUES (:id, :sid, :cid, :clsid) ON CONFLICT DO NOTHING"
                    ), {"id": str(uuid.uuid4()), "sid": student["id"], "cid": course_id, "clsid": class_id})
                    await db.commit()
            elif r.status_code == 400: # Already exists
                rl = await client.post("/api/auth/login", json={
                    "email": email,
                    "password": "student123",
                })
                student_tokens.append(rl.json()["access_token"])
                
                # Get student ID from DB
                async with AsyncSessionLocal() as db:
                    existing = await db.execute(select(User).where(User.email == email))
                    student_user = existing.scalar_one_or_none()
                    student_ids.append(student_user.id)
                    
                    await db.execute(text(
                        "INSERT INTO enrollments (id, student_id, course_id, class_id) "
                        "VALUES (:id, :sid, :cid, :clsid) ON CONFLICT DO NOTHING"
                    ), {"id": str(uuid.uuid4()), "sid": student_user.id, "cid": course_id, "clsid": class_id})
                    await db.commit()
                
        print("[OK] Registered and enrolled 15 dummy students.")

        # Login Lecturer
        r = await client.post("/api/auth/login", json={
            "email": "dr.shawky@aast.edu",
            "password": "lecture123",
        })
        lecturer_token = r.json()["access_token"]
        lec_headers = {"Authorization": f"Bearer {lecturer_token}"}
        
        # Create attendance session
        now = datetime.now(timezone.utc)
        r = await client.post("/api/sessions/", json={
            "course_id": course_id,
            "classroom_id": classroom_id,
            "class_id": class_id,
            "t_start": now.isoformat(),
            "t_expiry": (now + timedelta(hours=2)).isoformat(),
            "freshness_delta_sec": 300,
            "min_presence_pct": 75,
        }, headers=lec_headers)
        
        if r.status_code != 201:
            print("Session creation failed:", r.text)
            return
            
        session = r.json()
        session_id = session["id"]
        print(f"[OK] Session created: {session_id}")
        
        import random
        
        # Indices: A3=2, C1=10, D4=18
        rejected_indices = [2, 10, 18]
        
        all_other_indices = [i for i in range(25) if i not in rejected_indices]
        random.shuffle(all_other_indices)
        
        # Pick 6 seats to be present (claimed and occupied)
        present_indices = all_other_indices[:6]
        
        # Pick 5 seats to be unknown (occupied but not claimed)
        unknown_indices = all_other_indices[6:11]
        
        # Occupied tags = present + unknown
        occupied_indices = present_indices + unknown_indices
        occupied_tags = [tags[i] for i in occupied_indices]
        
        # Submit reader scan
        r = await client.post("/api/reader/scan", json={
            "session_id": session_id,
            "reader_device_id": "reader-room-5x5",
            "tags_detected": occupied_tags,
            "scanned_at": now.isoformat(),
        }, headers={"X-Api-Key": "reader-key-room-101"})
        
        if r.status_code != 201:
            print("Reader scan failed:", r.text)
            return
            
        print("[OK] Reader scan submitted.")
        
        # Claimed indices = present + rejected
        claimed_indices = present_indices + rejected_indices
        random.shuffle(claimed_indices)
        
        # Assign claims to the first N students
        for i, seat_idx in enumerate(claimed_indices):
            if i >= len(student_tokens):
                break
            r = await client.post("/api/attendance/claim", json={
                "session_id": session_id,
                "seat_id": seat_ids[seat_idx],
                "claimed_at": datetime.now(timezone.utc).isoformat(),
            }, headers={"Authorization": f"Bearer {student_tokens[i]}"})
            
            status_text = "PRESENT" if seat_idx in present_indices else "REJECTED"
            print(f"Student {i} claimed seat index {seat_idx} ({status_text}) -> API returned: {r.status_code}")
            
        print("[OK] Claims submitted.")
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())
