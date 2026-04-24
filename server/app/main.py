"""
Attendance System — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all models so relationships are registered
import app.models  # noqa: F401

from app.routers import auth, sessions, attendance, dashboard, reader, admin
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Start/stop background scheduler on app startup/shutdown."""
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Attendance System API",
    version="0.1.0",
    description="University attendance system",
    lifespan=lifespan,
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


# ── Routers ──
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(attendance.router, prefix="/api/attendance", tags=["Attendance"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(reader.router, prefix="/api/reader", tags=["Reader"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
