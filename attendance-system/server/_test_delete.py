import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.seat import Seat
from app.models.attendance_record import AttendanceRecord
from app.models.seat_state_history import SeatStateHistory
from app.models.seat_state import SeatState

async def test_delete():
    async with AsyncSessionLocal() as db:
        old_seats_result = await db.execute(select(Seat))
        old_seats = old_seats_result.scalars().all()
        old_seat_ids = [s.id for s in old_seats]
        
        if old_seat_ids:
            recs = await db.execute(select(AttendanceRecord).where(AttendanceRecord.seat_id.in_(old_seat_ids)))
            for r in recs.scalars().all(): await db.delete(r)
            
            hist = await db.execute(select(SeatStateHistory).where(SeatStateHistory.seat_id.in_(old_seat_ids)))
            for h in hist.scalars().all(): await db.delete(h)
            
            states = await db.execute(select(SeatState).where(SeatState.seat_id.in_(old_seat_ids)))
            for s in states.scalars().all(): await db.delete(s)
            
            for s in old_seats: await db.delete(s)
            
        await db.commit()
        print("Delete OK")

asyncio.run(test_delete())
