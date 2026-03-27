"""Pydantic schemas for Dashboard and Digital Twin endpoints."""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


# ── Seat Map ──

class SeatStateOut(BaseModel):
    seat_id: UUID
    label: str
    row: int
    col: int
    is_occupied: bool
    last_seen_at: datetime | None
    student_name: str | None = None
    attendance_status: str | None = None

    model_config = {"from_attributes": True}


class DigitalTwinView(BaseModel):
    session_id: UUID
    classroom_name: str
    layout_rows: int
    layout_cols: int
    session_status: str
    seats: list[SeatStateOut]


# ── Classroom / Seat admin ──

class ClassroomOut(BaseModel):
    id: UUID
    name: str
    building: str | None
    floor: int | None
    layout_rows: int
    layout_cols: int
    department_id: UUID

    model_config = {"from_attributes": True}


class SeatOut(BaseModel):
    id: UUID
    classroom_id: UUID
    label: str
    row: int
    col: int
    tag_id: str

    model_config = {"from_attributes": True}
