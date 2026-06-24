import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("select * from classrooms"))
        print("Classrooms:", res.all())
        res = await db.execute(text("select * from seats"))
        print("Seats count:", len(res.all()))

if __name__ == "__main__":
    asyncio.run(main())
