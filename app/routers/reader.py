"""
Reader router — receive scan reports, process seat state updates.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.scan_report import ScanReport
from app.schemas.reader import ScanReportCreate, ScanReportOut, ReaderCommand
from app.services.scan_service import process_scan_report

router = APIRouter()
settings = get_settings()


def verify_reader_api_key(x_api_key: str = Header(...)):
    """Authenticate reader devices via API key."""
    if x_api_key not in settings.reader_api_key_list:
        raise HTTPException(status_code=401, detail="Invalid reader API key")
    return x_api_key


@router.post("/scan", response_model=ScanReportOut, status_code=201)
async def submit_scan(
    data: ScanReportCreate,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_reader_api_key),
):
    """Reader submits a scan report (FR-S06, FR-R03)."""
    # Verify session exists and is active
    result = await db.execute(
        select(AttendanceSession).where(AttendanceSession.id == data.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.active:
        raise HTTPException(status_code=400, detail="Session not active")

    # Save raw report
    report = ScanReport(
        session_id=data.session_id,
        reader_device_id=data.reader_device_id,
        tags_detected=data.tags_detected,
        scanned_at=data.scanned_at,
    )
    db.add(report)
    await db.flush()

    # Process: update seat states + log transitions (FR-S07)
    await process_scan_report(db, session, data.tags_detected, data.scanned_at)

    await db.refresh(report)
    return report


@router.get("/command/{session_id}", response_model=ReaderCommand)
async def get_reader_command(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    api_key: str = Depends(verify_reader_api_key),
):
    """Reader polls for commands (FR-R04). Returns stop_scanning if session closed."""
    result = await db.execute(
        select(AttendanceSession).where(AttendanceSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == SessionStatus.closed:
        return ReaderCommand(command="stop_scanning", session_id=session.id)
    return ReaderCommand(command="continue", session_id=session.id)
