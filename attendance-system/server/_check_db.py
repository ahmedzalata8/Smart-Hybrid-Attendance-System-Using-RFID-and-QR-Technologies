import asyncio
import traceback
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as s:
        r = await s.execute(text("SELECT id FROM attendance_sessions"))
        print("Sessions:", r.scalars().all())
        r = await s.execute(text("SELECT classroom_id, COUNT(*) FROM seats GROUP BY classroom_id"))
        print("Seats per classroom:", r.fetchall())

asyncio.run(check())
