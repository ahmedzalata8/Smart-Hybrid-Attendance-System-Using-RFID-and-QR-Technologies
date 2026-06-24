"""
WebSocket manager for real-time seat map updates.
"""
import json
from fastapi import WebSocket
from typing import Dict, Set


class ConnectionManager:
    """Manages WebSocket connections per session for live seat-map pushes."""

    def __init__(self):
        # session_id -> set of active WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
        self.active_connections[session_id].add(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast_seat_update(self, session_id: str, data: dict):
        """Broadcast seat state update to all clients watching this session."""
        if session_id not in self.active_connections:
            return
        message = json.dumps(data)
        dead = []
        for ws in self.active_connections[session_id]:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_connections[session_id].discard(ws)


# Singleton
ws_manager = ConnectionManager()
