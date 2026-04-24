"""
Session finalization service — computes presence, revokes, creates audit log.
"""
import json
import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.attendance_record import AttendanceRecord, AttendanceStatus
from app.models.seat_state_history import SeatStateHistory
from app.models.audit_log import AuditLog


async def finalize_session(db: AsyncSession, session: AttendanceSession) -> None:
    """
    Finalize an attendance session:
    1. Compute presence_pct for each 'present' student using seat_state_history
    2. Revoke attendance for students below min_presence_pct
    3. Compute integrity hash
    4. Create audit log entry
    5. Mark session as closed
    """
    now = datetime.now(timezone.utc)
    session_duration = (session.t_expiry - session.t_start).total_seconds()

    if session_duration <= 0:
        session_duration = 1  # avoid division by zero

    # Get all 'present' attendance records
    att_result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session.id,
            AttendanceRecord.status == AttendanceStatus.present,
        )
    )
    present_records = att_result.scalars().all()

    for record in present_records:
        # Get occupancy history for this student's seat
        history_result = await db.execute(
            select(SeatStateHistory)
            .where(
                SeatStateHistory.session_id == session.id,
                SeatStateHistory.seat_id == record.seat_id,
            )
            .order_by(SeatStateHistory.detected_at.asc())
        )
        transitions = history_result.scalars().all()

        # Compute occupied time from transitions
        occupied_seconds = _compute_occupied_time(
            transitions, session.t_start, session.t_expiry
        )
        presence_pct = int((occupied_seconds / session_duration) * 100)
        presence_pct = min(presence_pct, 100)

        record.presence_pct = presence_pct
        record.finalized_at = now

        if presence_pct < session.min_presence_pct:
            record.status = AttendanceStatus.revoked
            record.revocation_reason = (
                f"Presence {presence_pct}% < required {session.min_presence_pct}%"
            )

    # Compute integrity hash of all records
    all_records_result = await db.execute(
        select(AttendanceRecord)
        .where(AttendanceRecord.session_id == session.id)
        .order_by(AttendanceRecord.claimed_at)
    )
    all_records = all_records_result.scalars().all()

    hash_input = json.dumps([
        {
            "student_id": str(r.student_id),
            "seat_id": str(r.seat_id),
            "status": r.status.value,
            "claimed_at": r.claimed_at.isoformat(),
            "presence_pct": r.presence_pct,
        }
        for r in all_records
    ], sort_keys=True)
    integrity_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    session.integrity_hash = integrity_hash
    session.finalized_at = now
    session.status = SessionStatus.closed

    # Get previous audit log hash for chain
    prev_log_result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    prev_log = prev_log_result.scalar_one_or_none()
    prev_hash = prev_log.integrity_hash if prev_log else None

    # Create audit log
    audit_payload = {
        "session_id": str(session.id),
        "course_id": str(session.course_id),
        "total_records": len(all_records),
        "present": sum(1 for r in all_records if r.status == AttendanceStatus.present),
        "rejected": sum(1 for r in all_records if r.status == AttendanceStatus.rejected),
        "revoked": sum(1 for r in all_records if r.status == AttendanceStatus.revoked),
        "integrity_hash": integrity_hash,
    }
    audit_hash_input = json.dumps(audit_payload, sort_keys=True)
    if prev_hash:
        audit_hash_input = prev_hash + audit_hash_input
    audit_hash = hashlib.sha256(audit_hash_input.encode()).hexdigest()

    audit_log = AuditLog(
        session_id=session.id,
        event_type="session_finalized",
        payload=audit_payload,
        integrity_hash=audit_hash,
        prev_hash=prev_hash,
    )
    db.add(audit_log)
    await db.flush()


def _compute_occupied_time(
    transitions: list[SeatStateHistory],
    t_start: datetime,
    t_expiry: datetime,
) -> float:
    """
    Compute total seconds a seat was occupied during the session window,
    using the occupancy transition log.
    """
    if not transitions:
        return 0.0

    occupied_seconds = 0.0
    last_occupied_start = None

    for t in transitions:
        # Clamp transition time to session window
        ts = max(t.detected_at, t_start)
        ts = min(ts, t_expiry)

        if t.is_occupied:
            last_occupied_start = ts
        else:
            if last_occupied_start is not None:
                occupied_seconds += (ts - last_occupied_start).total_seconds()
                last_occupied_start = None

    # If still occupied at session end
    if last_occupied_start is not None:
        end = min(t_expiry, datetime.now(timezone.utc))
        occupied_seconds += (end - last_occupied_start).total_seconds()

    return occupied_seconds
