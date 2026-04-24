"""
QR token generation service.
"""
import json
import hashlib
from datetime import datetime, timezone

from app.core.config import get_settings

settings = get_settings()


def generate_qr_token(session_data: dict) -> str:
    """
    Generate a QR token that encodes session info.
    In production this could be a signed JWT; for now it's a JSON + HMAC.
    """
    payload = json.dumps(session_data, sort_keys=True)
    signature = hashlib.sha256(
        (payload + settings.SECRET_KEY).encode()
    ).hexdigest()[:16]

    token_data = {
        "data": session_data,
        "sig": signature,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(token_data)
