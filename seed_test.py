"""
Seed script — inserts test data and exercises the full API flow.
Run: python seed_test.py
"""
import asyncio
import httpx
import json
from datetime import datetime, timedelta, timezone

BASE = "http://127.0.0.1:8000"


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=15) as client:
        print("=" * 60)
        print("  ATTENDANCE SYSTEM — FULL FLOW TEST")
        print("=" * 60)

        # ──────────────────────────────────────────────
        # 0. Health check
        # ──────────────────────────────────────────────
        r = await client.get("/health")
        assert r.status_code == 200
        print(f"\n✅ Health check: {r.json()}")

        # ──────────────────────────────────────────────
        # 1. Seed a Department directly in DB
        #    (no API endpoint for admin setup yet)
        # ──────────────────────────────────────────────
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal
        import uuid

        dept_id = str(uuid.uuid4())
        classroom_id = str(uuid.uuid4())
        seat_ids = [str(uuid.uuid4()) for _ in range(4)]

        async with AsyncSessionLocal() as db:
            # Department
            await db.execute(text(
                "INSERT INTO departments (id, name) VALUES (:id, :name) ON CONFLICT DO NOTHING"
            ), {"id": dept_id, "name": "Computer Science"})

            # Classroom (2x2 grid)
            await db.execute(text(
                "INSERT INTO classrooms (id, name, department_id, layout_rows, layout_cols) "
                "VALUES (:id, :name, :dept_id, 2, 2) ON CONFLICT DO NOTHING"
            ), {"id": classroom_id, "name": "Room 101", "dept_id": dept_id})

            # 4 Seats with RFID tags
            labels = ["A1", "A2", "B1", "B2"]
            for i, sid in enumerate(seat_ids):
                row, col = divmod(i, 2)
                await db.execute(text(
                    "INSERT INTO seats (id, classroom_id, label, row, col, tag_id) "
                    "VALUES (:id, :cid, :label, :row, :col, :tag) ON CONFLICT DO NOTHING"
                ), {"id": sid, "cid": classroom_id, "label": labels[i],
                    "row": row, "col": col, "tag": f"RFID-TAG-{i+1:03d}"})

            await db.commit()

        print(f"✅ Seeded department '{dept_id[:8]}...', classroom 'Room 101', 4 seats")

        # ──────────────────────────────────────────────
        # 2. Register users
        # ──────────────────────────────────────────────
        # Lecturer
        r = await client.post("/api/auth/register", json={
            "email": "dr.smith@university.edu",
            "password": "lecture123",
            "full_name": "Dr. Sarah Smith",
            "role": "lecturer",
            "department_id": dept_id,
        })
        assert r.status_code == 201, f"Lecturer register failed: {r.text}"
        lecturer = r.json()
        print(f"✅ Registered lecturer: {lecturer['full_name']} ({lecturer['id'][:8]}...)")

        # Student 1
        r = await client.post("/api/auth/register", json={
            "email": "alice@student.edu",
            "password": "student123",
            "full_name": "Alice Johnson",
            "role": "student",
            "student_id": "STU001",
            "department_id": dept_id,
        })
        assert r.status_code == 201, f"Student register failed: {r.text}"
        student1 = r.json()
        print(f"✅ Registered student: {student1['full_name']} ({student1['id'][:8]}...)")

        # Student 2
        r = await client.post("/api/auth/register", json={
            "email": "bob@student.edu",
            "password": "student123",
            "full_name": "Bob Williams",
            "role": "student",
            "student_id": "STU002",
            "department_id": dept_id,
        })
        assert r.status_code == 201, f"Student 2 register failed: {r.text}"
        student2 = r.json()
        print(f"✅ Registered student: {student2['full_name']} ({student2['id'][:8]}...)")

        # HoD
        r = await client.post("/api/auth/register", json={
            "email": "hod@university.edu",
            "password": "hod123",
            "full_name": "Prof. Ahmed Hassan",
            "role": "hod",
            "department_id": dept_id,
        })
        assert r.status_code == 201
        hod = r.json()
        print(f"✅ Registered HoD: {hod['full_name']} ({hod['id'][:8]}...)")

        # ──────────────────────────────────────────────
        # 3. Login as lecturer
        # ──────────────────────────────────────────────
        r = await client.post("/api/auth/login", json={
            "email": "dr.smith@university.edu",
            "password": "lecture123",
        })
        assert r.status_code == 200
        lecturer_token = r.json()["access_token"]
        lec_headers = {"Authorization": f"Bearer {lecturer_token}"}
        print(f"✅ Lecturer logged in — token: {lecturer_token[:20]}...")

        # ──────────────────────────────────────────────
        # 4. Seed a Course + Enrollment (directly in DB)
        # ──────────────────────────────────────────────
        course_id = str(uuid.uuid4())
        async with AsyncSessionLocal() as db:
            await db.execute(text(
                "INSERT INTO courses (id, code, name, department_id, lecturer_id) "
                "VALUES (:id, :code, :name, :dept_id, :lec_id) ON CONFLICT DO NOTHING"
            ), {"id": course_id, "code": "CS301", "name": "Software Engineering",
                "dept_id": dept_id, "lec_id": lecturer["id"]})

            # Enroll both students
            for sid in [student1["id"], student2["id"]]:
                await db.execute(text(
                    "INSERT INTO enrollments (id, student_id, course_id) "
                    "VALUES (:id, :sid, :cid) ON CONFLICT DO NOTHING"
                ), {"id": str(uuid.uuid4()), "sid": sid, "cid": course_id})

            await db.commit()

        print(f"✅ Created course 'CS301' and enrolled 2 students")

        # ──────────────────────────────────────────────
        # 5. Create attendance session (Lecturer)
        # ──────────────────────────────────────────────
        now = datetime.now(timezone.utc)
        r = await client.post("/api/sessions/", json={
            "course_id": course_id,
            "classroom_id": classroom_id,
            "t_start": now.isoformat(),
            "t_expiry": (now + timedelta(hours=1)).isoformat(),
            "freshness_delta_sec": 300,
            "min_presence_pct": 75,
        }, headers=lec_headers)
        assert r.status_code == 201, f"Session create failed: {r.text}"
        session = r.json()
        session_id = session["id"]
        print(f"✅ Session created: {session_id[:8]}... (status={session['status']})")
        print(f"   QR token: {session['qr_token'][:50]}...")

        # ──────────────────────────────────────────────
        # 6. Reader submits scan report (seats A1, A2 occupied)
        # ──────────────────────────────────────────────
        r = await client.post("/api/reader/scan", json={
            "session_id": session_id,
            "reader_device_id": "reader-room-101",
            "tags_detected": ["RFID-TAG-001", "RFID-TAG-002"],  # Seats A1, A2
            "scanned_at": now.isoformat(),
        }, headers={"X-Api-Key": "reader-key-room-101"})
        assert r.status_code == 201, f"Scan report failed: {r.text}"
        print(f"✅ Reader scan submitted: 2 tags detected (A1, A2 occupied)")

        # ──────────────────────────────────────────────
        # 7. Student 1 (Alice) submits attendance claim for seat A1
        # ──────────────────────────────────────────────
        r = await client.post("/api/auth/login", json={
            "email": "alice@student.edu", "password": "student123",
        })
        stu1_token = r.json()["access_token"]
        stu1_headers = {"Authorization": f"Bearer {stu1_token}"}

        r = await client.post("/api/attendance/claim", json={
            "session_id": session_id,
            "seat_id": seat_ids[0],  # A1
            "claimed_at": datetime.now(timezone.utc).isoformat(),
        }, headers=stu1_headers)
        assert r.status_code == 201, f"Claim failed: {r.text}"
        claim1 = r.json()
        print(f"✅ Alice claimed seat A1 → status: {claim1['status']}")

        # ──────────────────────────────────────────────
        # 8. Student 2 (Bob) claims seat B1 (NOT occupied → should be REJECTED)
        # ──────────────────────────────────────────────
        r = await client.post("/api/auth/login", json={
            "email": "bob@student.edu", "password": "student123",
        })
        stu2_token = r.json()["access_token"]
        stu2_headers = {"Authorization": f"Bearer {stu2_token}"}

        r = await client.post("/api/attendance/claim", json={
            "session_id": session_id,
            "seat_id": seat_ids[2],  # B1 — not in scan report → not occupied
            "claimed_at": datetime.now(timezone.utc).isoformat(),
        }, headers=stu2_headers)
        assert r.status_code == 201, f"Claim 2 failed: {r.text}"
        claim2 = r.json()
        print(f"✅ Bob claimed seat B1 (empty) → status: {claim2['status']} "
              f"(reason: {claim2.get('rejection_reason', 'N/A')})")

        # ──────────────────────────────────────────────
        # 9. Get attendance report (Lecturer)
        # ──────────────────────────────────────────────
        r = await client.get(f"/api/attendance/report/{session_id}", headers=lec_headers)
        assert r.status_code == 200
        report = r.json()
        print(f"\n📊 ATTENDANCE REPORT:")
        print(f"   Total claims: {report['total_claims']}")
        print(f"   Present:      {report['present_count']}")
        print(f"   Rejected:     {report['rejected_count']}")
        print(f"   Revoked:      {report['revoked_count']}")

        # ──────────────────────────────────────────────
        # 10. Digital Twin view (HoD)
        # ──────────────────────────────────────────────
        r = await client.post("/api/auth/login", json={
            "email": "hod@university.edu", "password": "hod123",
        })
        hod_token = r.json()["access_token"]
        hod_headers = {"Authorization": f"Bearer {hod_token}"}

        r = await client.get(f"/api/dashboard/twin/{session_id}", headers=hod_headers)
        assert r.status_code == 200
        twin = r.json()
        print(f"\n🏫 DIGITAL TWIN — {twin['classroom_name']}:")
        print(f"   Layout: {twin['layout_rows']}×{twin['layout_cols']}")
        for s in twin["seats"]:
            occ = "🟢 Occupied" if s["is_occupied"] else "⚪ Empty"
            att = f" | Attendance: {s['attendance_status']}" if s["attendance_status"] else ""
            print(f"   [{s['label']}] {occ}{att}")

        # ──────────────────────────────────────────────
        # 11. Close session (triggers finalization)
        # ──────────────────────────────────────────────
        r = await client.post(f"/api/sessions/{session_id}/close", headers=lec_headers)
        assert r.status_code == 200
        closed = r.json()
        print(f"\n🔒 Session closed: status={closed['status']}, hash={closed['integrity_hash'][:16]}...")

        print("\n" + "=" * 60)
        print("  ✅ ALL TESTS PASSED — FULL FLOW WORKING!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
