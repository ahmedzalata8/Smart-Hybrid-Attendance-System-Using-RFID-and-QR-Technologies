import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def check():
    async with AsyncSessionLocal() as s:
        for table in ['attendance_records', 'seat_state_history', 'seat_states']:
            r = await s.execute(text(f"SELECT COUNT(*) FROM {table}"))
            print(f"{table}: {r.scalar()}")

asyncio.run(check())
