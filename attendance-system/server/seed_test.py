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

        classroom_id = str(uuid.uuid4())
        seat_ids = [str(uuid.uuid4()) for _ in range(4)]

        async with AsyncSessionLocal() as db:
            # Check if department already exists to avoid FK error
            res = await db.execute(text("SELECT id FROM departments WHERE name = 'Computer Science'"))
            row = res.fetchone()
            if row:
                dept_id = str(row[0])
            else:
                dept_id = str(uuid.uuid4())
                await db.execute(text(
                    "INSERT INTO departments (id, name) VALUES (:id, :name) ON CONFLICT DO NOTHING"
                ), {"id": dept_id, "name": "Computer Science"})

            # Check if classroom already exists
            res = await db.execute(text("SELECT id FROM classrooms WHERE name = 'Room 101'"))
            row = res.fetchone()
            if row:
                classroom_id = str(row[0])
                # Fetch existing seat IDs in alphabetical order of labels (A1, A2, B1, B2)
                res_seats = await db.execute(text(
                    "SELECT id FROM seats WHERE classroom_id = :cid ORDER BY label"
                ), {"cid": classroom_id})
                seat_ids = [str(r[0]) for r in res_seats.fetchall()]
            else:
                classroom_id = str(uuid.uuid4())
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
        # Helper to register or fetch existing user from DB
        async def register_or_get(email, password, full_name, role, student_id=None):
            req_data = {
                "email": email,
                "password": password,
                "full_name": full_name,
                "role": role,
                "department_id": dept_id,
            }
            if student_id:
                req_data["student_id"] = student_id
            
            resp = await client.post("/api/auth/register", json=req_data)
            if resp.status_code == 201:
                u = resp.json()
                print(f"✅ Registered user: {u['full_name']} ({u['id'][:8]}...)")
                return u
            elif resp.status_code == 400 or "already registered" in resp.text.lower():
                async with AsyncSessionLocal() as db:
                    res = await db.execute(text("SELECT id, full_name FROM users WHERE email = :email"), {"email": email})
                    user_row = res.fetchone()
                    if user_row:
                        print(f"⚠️ Reused existing user: {user_row[1]} ({str(user_row[0])[:8]}...)")
                        return {"id": str(user_row[0]), "full_name": user_row[1]}
            assert False, f"Register failed for {email}: {resp.text}"

        lecturer = await register_or_get("dr.smith@university.edu", "lecture123", "Dr. Sarah Smith", "lecturer")
        student1 = await register_or_get("alice@student.edu", "student123", "Alice Johnson", "student", "STU001")
        student2 = await register_or_get("bob@student.edu", "student123", "Bob Williams", "student", "STU002")
        hod = await register_or_get("hod@university.edu", "hod123", "Prof. Ahmed Hassan", "hod")

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
        async with AsyncSessionLocal() as db:
            # Check if course exists
            res = await db.execute(text("SELECT id FROM courses WHERE code = 'CS301'"))
            row = res.fetchone()
            if row:
                course_id = str(row[0])
            else:
                course_id = str(uuid.uuid4())
                await db.execute(text(
                    "INSERT INTO courses (id, code, name, department_id, lecturer_id) "
                    "VALUES (:id, :code, :name, :dept_id, :lec_id) ON CONFLICT DO NOTHING"
                ), {"id": course_id, "code": "CS301", "name": "Software Engineering",
                    "dept_id": dept_id, "lec_id": lecturer["id"]})

            # Enroll both students
            for sid in [student1["id"], student2["id"]]:
                res_enroll = await db.execute(text(
                    "SELECT id FROM enrollments WHERE student_id = :sid AND course_id = :cid"
                ), {"sid": sid, "cid": course_id})
                if not res_enroll.fetchone():
                    await db.execute(text(
                        "INSERT INTO enrollments (id, student_id, course_id) "
                        "VALUES (:id, :sid, :cid) ON CONFLICT DO NOTHING"
                    ), {"id": str(uuid.uuid4()), "sid": sid, "cid": course_id})

            await db.commit()

        print(f"✅ Created/reused course 'CS301' and enrolled 2 students")

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
