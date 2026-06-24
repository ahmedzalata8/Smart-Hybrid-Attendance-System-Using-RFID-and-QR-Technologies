"""
RFID Scan router — start/status/results for 360° scans.

These endpoints control the physical RFID reader + stepper motor
to perform a full rotational scan of the room.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.core.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.seat import Seat
from app.models.rfid_reading import RFIDReading
from app.models.seat_state import SeatState
from app.schemas.rfid_scan import (
    ScanStartRequest,
    ScanStartResponse,
    ScanStatusResponse,
    ScanResultsResponse,
)
from app.services.rfid_scanner import scanner_service
from app.services.scan_service import resolve_tag_placement, apply_update_scan

router = APIRouter()
logger = logging.getLogger(__name__)

# Known-tag map, stored as {label: card_id} (e.g. {"Tag-1": "4187573767"}).
# Lives inside the attendance-system project (server/tag_map.json) so tag
# recognition no longer depends on the external rfid/ prototype folder.
# Set TAG_MAP_PATH in the environment to override.
_settings = get_settings()
TAG_MAP_FILE = (
    Path(_settings.TAG_MAP_PATH)
    if _settings.TAG_MAP_PATH
    else Path(__file__).resolve().parents[2] / "tag_map.json"
)


def load_tag_map() -> dict[str, str]:
    """
    Load tag_map.json as {hex_id: label}.
    The file is stored as {label: hex_id}, so we invert it.
    """
    if TAG_MAP_FILE.exists():
        try:
            with open(TAG_MAP_FILE, "r") as f:
                data = json.load(f)
            # Invert: {label: hex} → {hex: label}
            return {v: k for k, v in data.items()}
        except Exception as e:
            logger.warning("Could not load tag_map.json: %s", e)
    return {}


@router.post("/start", response_model=ScanStartResponse)
async def start_scan(
    data: ScanStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.hod, UserRole.lecturer)),
):
    """Trigger a 360° RFID scan for the given session."""
    # Verify session
    result = await db.execute(
        select(AttendanceSession).where(AttendanceSession.id == data.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status != SessionStatus.active:
        raise HTTPException(400, "Session is not active")

    # Build tag_map from tag_map.json: {hex_id: label}
    # This contains the actual RFID hex IDs for each tag (Tag-1 through Tag-20)
    tag_map = load_tag_map()
    logger.info("Loaded %d known tags from tag_map.json", len(tag_map))

    resp = scanner_service.start_scan(
        session_id=str(session.id),
        tag_map=tag_map,
        stepper_port=data.stepper_port,
        rfid_port=data.rfid_port,
    )
    if "error" in resp:
        raise HTTPException(409, resp["error"])

    return ScanStartResponse(scan_id=resp["scan_id"], status=resp["status"])


@router.get("/status", response_model=ScanStatusResponse)
async def scan_status(
    current_user: User = Depends(require_role(UserRole.hod, UserRole.lecturer)),
):
    """Poll live scan progress."""
    return ScanStatusResponse(**scanner_service.status)


@router.get("/results", response_model=ScanResultsResponse)
async def scan_results(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.hod, UserRole.lecturer)),
):
    """Get the results of the most recent completed scan."""
    st = scanner_service.status
    res = scanner_service.results

    if not res:
        return ScanResultsResponse(status=st["status"], error=st.get("error"))

    # Enrich each tag with its radar position so the live preview lands exactly
    # where the seat will be drawn once applied. Quadrant ties are resolved here;
    # a 4-way tie can't be placed → flagged undetermined (no position).
    tags_summary = res.get("tags_summary") or {}
    for label, info in tags_summary.items():
        placement = resolve_tag_placement(info.get("quadrant_hits", {}), label)
        if placement is None:
            info["x_pct"] = None
            info["y_pct"] = None
            info["undetermined"] = True
        else:
            info["x_pct"], info["y_pct"] = placement
            info["undetermined"] = False

    return ScanResultsResponse(
        scan_id=res.get("scan_id"),
        session_id=res.get("session_id"),
        tags_found=res.get("tags_found", 0),
        scan_info=res.get("scan_info"),
        tags_summary=tags_summary,
        clustered_detections=res.get("clustered_detections"),
        status=st["status"],
    )


@router.post("/apply-results")
async def apply_scan_results(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.hod, UserRole.lecturer)),
):
    """
    Apply initial scan results to the session.

    INITIAL SCAN LOGIC:
    - Each detected tag represents a SEAT in the room.
    - The total number of seats = number of tags detected (dynamic).
    - All detected seats are NON-OCCUPIED (empty chairs with tags, no students yet).
    - This creates/updates seat records in the DB to match the scan results.
    """
    import math
    from app.models.classroom import Classroom
    from app.models.seat_state_history import SeatStateHistory

    res = scanner_service.results
    if not res:
        raise HTTPException(400, "No scan results to apply")

    session_id = res.get("session_id")
    if not session_id:
        raise HTTPException(400, "No session_id in results")

    # Verify session
    sess_result = await db.execute(
        select(AttendanceSession).where(AttendanceSession.id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    tags_summary = res.get("tags_summary", {})
    num_tags = len(tags_summary)

    if num_tags == 0:
        raise HTTPException(400, "No tags detected — nothing to apply")

    # Load the forward tag map {label: hex} for setting proper tag_ids
    tag_map_fwd = {}
    if TAG_MAP_FILE.exists():
        try:
            with open(TAG_MAP_FILE, "r") as f:
                tag_map_fwd = json.load(f)
        except Exception:
            pass

    # Resolve each tag's placement, handling quadrant ties. A 4-way tie can't be
    # positioned → recorded as "failed to determine" and given no seat.
    tag_entries = sorted(tags_summary.items(), key=lambda x: x[0])  # by label
    placeable = []        # (label, info, x_pct, y_pct)
    failed_to_place = []  # labels we couldn't position
    for tag_label, info in tag_entries:
        placement = resolve_tag_placement(info.get("quadrant_hits", {}), tag_label)
        if placement is None:
            failed_to_place.append(tag_label)
        else:
            placeable.append((tag_label, info, placement[0], placement[1]))

    num_placed = len(placeable)
    if num_placed == 0:
        raise HTTPException(400, "No tags could be placed (all had ambiguous quadrants)")

    # ── Step 1: Update classroom layout to fit the placed tags ──
    classroom_result = await db.execute(
        select(Classroom).where(Classroom.id == session.classroom_id)
    )
    classroom = classroom_result.scalar_one_or_none()

    cols = math.ceil(math.sqrt(num_placed))
    rows = math.ceil(num_placed / cols)

    if classroom:
        classroom.layout_rows = rows
        classroom.layout_cols = cols
        logger.info("Updated classroom %s layout to %dx%d for %d seats",
                     classroom.name, rows, cols, num_placed)

    # ── Step 2 & 3: Remove old seats and their dependent records to avoid FK constraints ──
    from app.models.attendance_record import AttendanceRecord
    
    old_seats_result = await db.execute(
        select(Seat).where(Seat.classroom_id == session.classroom_id)
    )
    old_seats = old_seats_result.scalars().all()
    
    if old_seats:
        old_seat_ids = [s.id for s in old_seats]
        
        # Remove attendance_records
        recs = await db.execute(select(AttendanceRecord).where(AttendanceRecord.seat_id.in_(old_seat_ids)))
        for r in recs.scalars().all(): await db.delete(r)
        
        # Remove seat_state_history
        hist = await db.execute(select(SeatStateHistory).where(SeatStateHistory.seat_id.in_(old_seat_ids)))
        for h in hist.scalars().all(): await db.delete(h)
        
        # Remove seat_states
        states = await db.execute(select(SeatState).where(SeatState.seat_id.in_(old_seat_ids)))
        for s in states.scalars().all(): await db.delete(s)
        
        # Remove seats
        for s in old_seats: await db.delete(s)

    await db.flush()

    # ── Step 4: Create new seats — one per PLACEABLE tag ──
    now = datetime.now(timezone.utc)
    new_seats = []

    for idx, (tag_label, info, x_pct, y_pct) in enumerate(placeable):
        row = idx // cols
        col = idx % cols
        # Use the canonical hex from tag_map.json if available
        tag_hex = tag_map_fwd.get(tag_label, info.get("canonical_tag_id", tag_label))
        seat = Seat(
            classroom_id=session.classroom_id,
            label=tag_label,
            row=row,
            col=col,
            tag_id=tag_hex,
            x_pct=x_pct,   # tie-resolved radar position
            y_pct=y_pct,
        )
        db.add(seat)
        new_seats.append(seat)

    await db.flush()  # Get seat IDs

    # ── Step 5: Create seat_states — ALL non-occupied (empty chairs) ──
    for seat in new_seats:
        state = SeatState(
            session_id=session.id,
            seat_id=seat.id,
            is_occupied=False,  # Initial scan = all seats are EMPTY
            last_seen_at=now,   # We've seen them, they're just empty
        )
        db.add(state)

    # ── Step 6: Persist raw RFID readings (audit trail) ──
    clustered_detections = res.get("clustered_detections", [])
    for d in clustered_detections:
        angle = d.get("angle_deg", 0) % 360
        if angle < 90:
            quadrant = "Q1"
        elif angle < 180:
            quadrant = "Q2"
        elif angle < 270:
            quadrant = "Q3"
        else:
            quadrant = "Q4"

        tag_label = d.get("label", "")

        reading = RFIDReading(
            session_id=session.id,
            tag_hex_id=d.get("tag_id", ""),
            tag_label=tag_label,
            seat_label=tag_label,
            angle_deg=d.get("angle_deg"),
            step_position=d.get("step"),
            direction="CW",
            quadrant=quadrant,
            detected_at=datetime.fromisoformat(d["timestamp"]) if d.get("timestamp") else now,
        )
        db.add(reading)

    await db.flush()

    logger.info("Initial scan applied: %d seats created (all empty), %d failed to place, %d readings saved",
                num_placed, len(failed_to_place), len(clustered_detections))

    return {
        "success": True,
        "total_seats": num_placed,
        "seats_occupied": 0,  # Initial scan = all empty
        "readings_saved": len(clustered_detections),
        "tags_detected": num_tags,
        "failed_to_place": failed_to_place,
        "seat_labels": [s.label for s in new_seats],
    }


@router.post("/apply-update")
async def apply_scan_update(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.hod, UserRole.lecturer)),
):
    """
    Apply an UPDATE scan against the existing seats (presence detection).

    UPDATE SCAN LOGIC (diff against the current digital twin):
    - Tags are mounted on chairs. A student sitting down blocks the tag.
    - A previously-known tag that is NO LONGER detected -> seat becomes OCCUPIED
      (the seat is kept, just marked occupied — never removed).
    - A previously-known tag that IS still detected -> seat stays EMPTY
      (and is un-occupied again if the student left).
    - A NEW tag never seen before -> added to the twin as a new EMPTY seat.

    The diff itself lives in scan_service.apply_update_scan so the automated
    scan triggered by a student claim applies identical logic.
    """
    res = scanner_service.results
    if not res:
        raise HTTPException(400, "No scan results to apply")

    session_id = res.get("session_id")
    if not session_id:
        raise HTTPException(400, "No session_id in results")

    # Verify session
    sess_result = await db.execute(
        select(AttendanceSession).where(AttendanceSession.id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    # Forward tag map {label: hex} for assigning tag_ids to brand-new seats
    tag_map_fwd = {}
    if TAG_MAP_FILE.exists():
        try:
            with open(TAG_MAP_FILE, "r") as f:
                tag_map_fwd = json.load(f)
        except Exception:
            pass

    try:
        summary = await apply_update_scan(db, session, res, tag_map_fwd)
    except ValueError as e:
        raise HTTPException(400, str(e))

    logger.info(
        "Update scan applied: %d occupied, %d empty, %d new seats added",
        summary["seats_occupied"], summary["seats_freed"], summary["seats_added"],
    )

    return {"success": True, **summary}

