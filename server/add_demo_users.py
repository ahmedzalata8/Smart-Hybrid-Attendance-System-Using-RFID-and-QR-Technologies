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
            print("Creating default department...")
            dept = Department(
                id=str(uuid.uuid4()),
                name="Computer Science",
                code="CS"
            )
            db.add(dept)
            await db.flush()

        users_to_add = [
            ("dr.shawky@aast.edu", "lecture123", "Dr. Shawky", UserRole.lecturer),
            ("dr.smith@university.edu", "lecture123", "Dr. Smith", UserRole.lecturer),
            ("hod@aast.edu", "hod123", "AAST Head of Department", UserRole.hod),
            ("hod@university.edu", "hod123", "University Head of Department", UserRole.hod),
            ("admin@aast.edu", "admin123", "System Administrator", UserRole.admin),
        ]

        for email, password, full_name, role in users_to_add:
            existing = await db.execute(select(User).where(User.email == email))
            if not existing.scalar_one_or_none():
                new_user = User(
                    id=str(uuid.uuid4()),
                    email=email,
                    hashed_password=hash_password(password),
                    full_name=full_name,
                    role=role,
                    department_id=dept.id
                )
                db.add(new_user)
                print(f"✅ Added {email} ({role.name})")
            else:
                print(f"⚠️ {email} already exists")

        await db.commit()
        print("Database seeded successfully.")

if __name__ == "__main__":
    asyncio.run(main())
