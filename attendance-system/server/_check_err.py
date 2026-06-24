import asyncio
import traceback
from app.routers.rfid_scan import apply_scan_results
from app.core.database import AsyncSessionLocal
from fastapi import Request
from app.models.user import User

async def run_apply():
    async with AsyncSessionLocal() as s:
        user = User(role="hod")
        try:
            # We mock the dependencies
            # We just need to call the apply-results directly, but we need to mock scanner_service.results
            pass
        except Exception as e:
            pass

asyncio.run(run_apply())
