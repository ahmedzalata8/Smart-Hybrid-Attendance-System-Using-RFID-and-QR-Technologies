"""Pydantic schemas for the RFID 360° scan endpoints."""
from pydantic import BaseModel


class ScanStartRequest(BaseModel):
    session_id: str
    stepper_port: str | None = None
    rfid_port: str | None = None


class ScanStartResponse(BaseModel):
    scan_id: str | None = None
    status: str
    error: str | None = None


class ScanStatusResponse(BaseModel):
    status: str
    scan_id: str | None = None
    session_id: str | None = None
    progress: float = 0.0
    detections_count: int = 0
    error: str | None = None


class TagSummary(BaseModel):
    canonical_tag_id: str
    matched_known_hex: str | None = None
    detection_count: int
    raw_variant_count: int
    angles_detected: list[float]
    quadrant_hits: dict[str, int]
    best_quadrant: str
    # Radar position (0..100, centre 50,50) — matches the applied seat position.
    # Null + undetermined=True when a 4-way quadrant tie makes placement impossible.
    x_pct: float | None = None
    y_pct: float | None = None
    undetermined: bool = False
    first_seen: str | None = None
    last_seen: str | None = None


class ScanResultsResponse(BaseModel):
    scan_id: str | None = None
    session_id: str | None = None
    tags_found: int = 0
    scan_info: dict | None = None
    tags_summary: dict[str, TagSummary] | None = None
    clustered_detections: list[dict] | None = None
    status: str = "idle"
    error: str | None = None
