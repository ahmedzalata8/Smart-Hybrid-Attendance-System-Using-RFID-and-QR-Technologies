"""
Scan processing service — updates seat states and logs transitions.
"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_session import AttendanceSession
from app.models.seat import Seat
from app.models.seat_state import SeatState
from app.models.seat_state_history import SeatStateHistory


async def process_scan_report(
    db: AsyncSession,
    session: AttendanceSession,
    tags_detected: list[str],
    scanned_at: datetime,
) -> None:
    """
    Process an RFID scan report:
    1. Map detected tag_ids → seat_ids
    2. Compare against current seat_states
    3. Update seat_states (live snapshot)
    4. Log transitions in seat_state_history
    """
    # Get all seats for this classroom
    seats_result = await db.execute(
        select(Seat).where(Seat.classroom_id == session.classroom_id)
    )
    seats = seats_result.scalars().all()
    tag_to_seat = {seat.tag_id: seat for seat in seats}

    # Get current seat states for this session
    states_result = await db.execute(
        select(SeatState).where(SeatState.session_id == session.id)
    )
    current_states = {ss.seat_id: ss for ss in states_result.scalars().all()}

    # Determine which seats are currently occupied
    detected_seat_ids = set()
    for tag_id in tags_detected:
        seat = tag_to_seat.get(tag_id)
        if seat:
            detected_seat_ids.add(seat.id)

    # Update each seat state and log transitions
    for seat in seats:
        now_occupied = seat.id in detected_seat_ids
        state = current_states.get(seat.id)

        if state is None:
            # Should have been pre-populated, but create if missing
            state = SeatState(
                session_id=session.id,
                seat_id=seat.id,
                is_occupied=now_occupied,
                last_seen_at=scanned_at if now_occupied else None,
            )
            db.add(state)
            if now_occupied:
                db.add(SeatStateHistory(
                    session_id=session.id,
                    seat_id=seat.id,
                    is_occupied=True,
                    detected_at=scanned_at,
                ))
        else:
            was_occupied = state.is_occupied

            # Update live state
            state.is_occupied = now_occupied
            if now_occupied:
                state.last_seen_at = scanned_at

            # Log transition only if state changed
            if was_occupied != now_occupied:
                db.add(SeatStateHistory(
                    session_id=session.id,
                    seat_id=seat.id,
                    is_occupied=now_occupied,
                    detected_at=scanned_at,
                ))

    await db.flush()
