"""Pydantic schemas for Reader device endpoints."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ScanReportCreate(BaseModel):
    session_id: UUID
    reader_device_id: str
    tags_detected: list[str]
    scanned_at: datetime


class ScanReportOut(BaseModel):
    id: UUID
    session_id: UUID
    reader_device_id: str
    tags_detected: list[str]
    scanned_at: datetime
    received_at: datetime

    model_config = {"from_attributes": True}


class ReaderCommand(BaseModel):
    command: str  # "stop_scanning"
    session_id: UUID
