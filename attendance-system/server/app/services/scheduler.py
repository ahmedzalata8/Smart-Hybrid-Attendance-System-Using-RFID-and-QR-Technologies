"""
Background scheduler — auto-finalize expired sessions.
"""
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.services.finalization_service import finalize_session

scheduler = AsyncIOScheduler()


async def auto_finalize_expired_sessions():
    """Check for active sessions past their expiry and finalize them (FR-S14)."""
    async with AsyncSessionLocal() as db:
        try:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(AttendanceSession).where(
                    AttendanceSession.status == SessionStatus.active,
                    AttendanceSession.t_expiry < now,
                )
            )
            expired_sessions = result.scalars().all()

            for session in expired_sessions:
                await finalize_session(db, session)

            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"[Scheduler] Error finalizing sessions: {e}")


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        auto_finalize_expired_sessions,
        "interval",
        seconds=30,  # check every 30 seconds
        id="auto_finalize",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler():
    """Shut down the scheduler."""
    scheduler.shutdown(wait=False)
