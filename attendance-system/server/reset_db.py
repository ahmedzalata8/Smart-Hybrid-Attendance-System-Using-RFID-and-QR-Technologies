import asyncio
from sqlalchemy import text
from app.core.database import engine

async def main():
    print("Resetting database schema...")
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
    print("Database reset successfully.")

if __name__ == "__main__":
    asyncio.run(main())
