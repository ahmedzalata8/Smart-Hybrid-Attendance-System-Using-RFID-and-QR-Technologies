"""Check which users exist in the database."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

EMAILS_TO_CHECK = [
    "dr.smith@university.edu",
    "dr.shawky@aast.edu",
    "admin@aast.edu",
    "hod@aast.edu",
    "hod@university.edu",
]

async def main():
    engine = create_async_engine("postgresql+asyncpg://postgres:attend@localhost:5432/attendance_db")
    async with engine.connect() as conn:
        # List ALL users
        result = await conn.execute(text("SELECT email, full_name, role, is_active FROM users ORDER BY role, email"))
        rows = result.fetchall()
        print(f"=== ALL USERS IN DATABASE ({len(rows)} total) ===")
        for row in rows:
            print(f"  {row[0]:40s} | {row[1]:30s} | {row[2]:10s} | active={row[3]}")

        print("\n=== CHECKING REQUESTED EMAILS ===")
        for email in EMAILS_TO_CHECK:
            result = await conn.execute(text("SELECT email, full_name, role FROM users WHERE email = :email"), {"email": email})
            row = result.fetchone()
            if row:
                print(f"  FOUND:     {email:40s} -> {row[1]} ({row[2]})")
            else:
                print(f"  NOT FOUND: {email}")

    await engine.dispose()

asyncio.run(main())
