"""
Scan processing service — updates seat states and logs transitions.

Also hosts the shared 360°-scan helpers (tag radar positioning and the
"update scan" diff) so both the lecturer's manual Update Scan endpoint and the
automated scan triggered by a student claim apply the exact same logic.
"""
import hashlib
import math
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_session import AttendanceSession
from app.models.classroom import Classroom
from app.models.seat import Seat
from app.models.seat_state import SeatState
from app.models.seat_state_history import SeatStateHistory


# Centre angle (degrees, 0° = up) of each radar quadrant.
QUAD_CENTER = {"Q1": 45, "Q2": 135, "Q3": 225, "Q4": 315}


def _hash_frac(seed: str) -> float:
    """Deterministic 0..1 value from a string (stable across processes)."""
    h = int(hashlib.md5(seed.encode()).hexdigest()[:8], 16)
    return (h % 10000) / 10000.0


def radar_position(quadrant: str, label: str) -> tuple[float, float]:
    """
    Compute a stable radar position (x_pct, y_pct in 0..100, centre = 50,50)
    for a tag, scattered within its detected quadrant. Deterministic per
    (quadrant, label) so a tag keeps the same spot across scans/reloads.
    """
    center = QUAD_CENTER.get(quadrant, 45)
    angle = center - 35 + _hash_frac(label + "a") * 70   # within ±35° of centre
    frac = 0.45 + _hash_frac(label + "r") * 0.4          # 0.45..0.85 of radius
    rad = math.radians(angle - 90)
    x = 50 + frac * 50 * math.cos(rad)
    y = 50 + frac * 50 * math.sin(rad)
    return round(x, 2), round(y, 2)


# Boundary angle (0°=up, clockwise) separating two ADJACENT quadrants.
_ADJ_BOUNDARY = {
    frozenset({"Q1", "Q2"}): 90,    # right
    frozenset({"Q2", "Q3"}): 180,   # bottom
    frozenset({"Q3", "Q4"}): 270,   # left
    frozenset({"Q4", "Q1"}): 0,     # top
}
# For a tie across two OPPOSITE quadrants, the quadrant between them by index
# ((a+b)/2): Q1&Q3 -> Q2, Q2&Q4 -> Q3.
_OPP_MIDDLE = {
    frozenset({"Q1", "Q3"}): "Q2",
    frozenset({"Q2", "Q4"}): "Q3",
}
# Opposite quadrant — the middle of a 3-quadrant arc is opposite the one missing.
_OPPOSITE = {"Q1": "Q3", "Q2": "Q4", "Q3": "Q1", "Q4": "Q2"}


def _angle_to_xy(angle_deg: float, frac: float = 0.65) -> tuple[float, float]:
    """Convert a radar angle (0°=up, clockwise) to an (x_pct, y_pct) point."""
    rad = math.radians(angle_deg - 90)
    x = 50 + frac * 50 * math.cos(rad)
    y = 50 + frac * 50 * math.sin(rad)
    return round(x, 2), round(y, 2)


def resolve_tag_placement(quadrant_hits: dict, label: str) -> tuple[float, float] | None:
    """
    Decide a tag's radar position from its per-quadrant hit counts, breaking
    ties between quadrants that share the SAME maximum number of hits:

      1 quadrant  -> scattered within that quadrant (radar_position)
      2 adjacent  -> the boundary angle between them   (Q1&Q2 -> 90°)
      2 opposite  -> the middle quadrant between them   (Q1&Q3 -> Q2 centre)
      3 quadrants -> the middle of the contiguous arc   (Q1,Q2,Q3 -> Q2)
      4 quadrants -> None  (cannot determine — caller marks it "failed")
    """
    qh = {q: int(quadrant_hits.get(q, 0) or 0) for q in ("Q1", "Q2", "Q3", "Q4")}
    top = max(qh.values())
    if top <= 0:
        return radar_position("Q1", label)
    winners = sorted(q for q, n in qh.items() if n == top)

    if len(winners) == 1:
        return radar_position(winners[0], label)
    if len(winners) == 2:
        pair = frozenset(winners)
        if pair in _ADJ_BOUNDARY:                      # adjacent → separating angle
            return _angle_to_xy(_ADJ_BOUNDARY[pair])
        return _angle_to_xy(QUAD_CENTER[_OPP_MIDDLE[pair]])  # opposite → middle quadrant
    if len(winners) == 3:
        missing = ({"Q1", "Q2", "Q3", "Q4"} - set(winners)).pop()
        return _angle_to_xy(QUAD_CENTER[_OPPOSITE[missing]])
    return None  # 4-way tie — undeterminable


async def apply_update_scan(
    db: AsyncSession,
    session: AttendanceSession,
    results: dict | None,
    tag_map_fwd: dict[str, str] | None = None,
) -> dict:
    """
    Apply an UPDATE scan against the existing seats (presence detection).

    - A previously-known tag that is NO LONGER detected -> seat becomes OCCUPIED
      (a student sitting on the chair blocks its tag).
    - A previously-known tag that IS still detected -> seat stays EMPTY
      (un-occupied again if the student left).
    - A brand-new tag the Initial Scan never saw -> added as a new EMPTY seat at
      its scanned position.

    Existing seats are NEVER repositioned — the Initial Scan owns the placement
    of tags it already saw; the update only changes their occupancy. New tags
    are the only thing an update may place.

    Raises ValueError if there are no baseline seats yet (run an Initial Scan
    first). Callers translate that into the appropriate HTTP error.
    """
    tag_map_fwd = tag_map_fwd or {}
    tags_summary = (results or {}).get("tags_summary", {}) or {}
    detected_labels = set(tags_summary.keys())
    now = datetime.now(timezone.utc)

    # ── Load existing seats for this classroom ──
    seats_result = await db.execute(
        select(Seat).where(Seat.classroom_id == session.classroom_id)
    )
    existing_seats = list(seats_result.scalars().all())
    if not existing_seats:
        raise ValueError("No baseline seats — run an Initial Scan before updating")

    # Index existing seat_states for this session by seat_id
    states_result = await db.execute(
        select(SeatState).where(SeatState.session_id == session.id)
    )
    states_by_seat = {s.seat_id: s for s in states_result.scalars().all()}

    known_labels = {s.label for s in existing_seats}
    occupied_count = 0
    freed_count = 0

    # ── Step 1: Update existing seats based on whether their tag was detected ──
    for seat in existing_seats:
        is_detected = seat.label in detected_labels
        new_occupied = not is_detected  # tag gone -> someone is sitting there

        state = states_by_seat.get(seat.id)
        if state is None:
            state = SeatState(
                session_id=session.id,
                seat_id=seat.id,
                is_occupied=new_occupied,
                last_seen_at=now if is_detected else None,
            )
            db.add(state)
        else:
            changed = state.is_occupied != new_occupied
            state.is_occupied = new_occupied
            if is_detected:
                state.last_seen_at = now
            if changed:
                db.add(SeatStateHistory(
                    session_id=session.id,
                    seat_id=seat.id,
                    is_occupied=new_occupied,
                    detected_at=now,
                ))

        if new_occupied:
            occupied_count += 1
        elif state is not None:
            freed_count += 1

    # ── Add brand-new tags (unseen by the Initial Scan) as new EMPTY seats ──
    # Existing seats above keep their position; only these new tags are placed.
    new_labels = sorted(detected_labels - known_labels)

    classroom_result = await db.execute(
        select(Classroom).where(Classroom.id == session.classroom_id)
    )
    classroom = classroom_result.scalar_one_or_none()
    cols = max(classroom.layout_cols if classroom else 1, 1)
    next_index = len(existing_seats)

    added_seats = []
    failed_to_place = []
    for tag_label in new_labels:
        info = tags_summary.get(tag_label, {})
        placement = resolve_tag_placement(info.get("quadrant_hits", {}), tag_label)
        if placement is None:
            # 4-way tie — cannot determine a position, so don't place it.
            failed_to_place.append(tag_label)
            continue
        x_pct, y_pct = placement
        tag_hex = tag_map_fwd.get(tag_label, info.get("canonical_tag_id", tag_label))
        linear = next_index + len(added_seats)
        seat = Seat(
            classroom_id=session.classroom_id,
            label=tag_label,
            row=linear // cols,
            col=linear % cols,
            tag_id=tag_hex,
            x_pct=x_pct,
            y_pct=y_pct,
        )
        db.add(seat)
        added_seats.append(seat)

    await db.flush()  # get IDs for the new seats

    for seat in added_seats:
        db.add(SeatState(
            session_id=session.id,
            seat_id=seat.id,
            is_occupied=False,  # newly discovered tag = empty chair
            last_seen_at=now,
        ))

    total_seats = len(existing_seats) + len(added_seats)
    if classroom and added_seats:
        classroom.layout_rows = math.ceil(total_seats / cols)

    await db.flush()

    return {
        "total_seats": total_seats,
        "seats_occupied": occupied_count,
        "seats_freed": freed_count,
        "seats_added": len(added_seats),
        "new_seat_labels": [s.label for s in added_seats],
        "failed_to_place": failed_to_place,
        "detected_labels": sorted(detected_labels),
    }


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
