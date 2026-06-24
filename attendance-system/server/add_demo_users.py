import sys
import asyncio
import uuid
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.department import Department

async def main():
    async with AsyncSessionLocal() as db:
        # Get existing department
        result = await db.execute(select(Department).limit(1))
        dept = result.scalar_one_or_none()
        
        if not dept:
            print("❌ No department found. Need to create one first.")
            return

        # 1. Add Dr. Shawky
        shawky_email = "dr.shawky@aast.edu"
        existing = await db.execute(select(User).where(User.email == shawky_email))
        if not existing.scalar_one_or_none():
            dr_shawky = User(
                id=str(uuid.uuid4()),
                email=shawky_email,
                hashed_password=hash_password("lecture123"),
                full_name="Dr. Shawky",
                role=UserRole.lecturer,
                department_id=dept.id
            )
            db.add(dr_shawky)
            print(f"✅ Added {shawky_email} (Lecturer)")
        else:
            print(f"⚠️ {shawky_email} already exists")

        # 2. Add HoD
        hod_email = "hod@aast.edu"
        existing = await db.execute(select(User).where(User.email == hod_email))
        if not existing.scalar_one_or_none():
            hod = User(
                id=str(uuid.uuid4()),
                email=hod_email,
                hashed_password=hash_password("hod123"),
                full_name="AAST Head of Department",
                role=UserRole.hod,
                department_id=dept.id
            )
            db.add(hod)
            print(f"✅ Added {hod_email} (HoD)")
        else:
            print(f"⚠️ {hod_email} already exists")

        # 3. Add Admin
        admin_email = "admin@aast.edu"
        existing = await db.execute(select(User).where(User.email == admin_email))
        if not existing.scalar_one_or_none():
            admin_user = User(
                id=str(uuid.uuid4()),
                email=admin_email,
                hashed_password=hash_password("admin123"),
                full_name="System Administrator",
                role=UserRole.admin,
                department_id=dept.id
            )
            db.add(admin_user)
            print(f"✅ Added {admin_email} (Admin)")
        else:
            print(f"⚠️ {admin_email} already exists")

        await db.commit()
        print("Database seeded successfully.")

if __name__ == "__main__":
    asyncio.run(main())
