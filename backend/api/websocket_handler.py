import json
from typing import Dict
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"WebSocket connected: {session_id}")
        await self.send(session_id, {
            "type": "connected",
            "session_id": session_id,
            "message": "MAESTRO agent online"
        })
    
    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"WebSocket disconnected: {session_id}")
    
    async def send(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            ws = self.active_connections[session_id]
            try:
                await ws.send_json(data)
            except Exception as e:
                print(f"WS send error for {session_id}: {e}")
                await self.disconnect(session_id)
    
    async def broadcast(self, data: dict):
        for session_id in list(self.active_connections.keys()):
            await self.send(session_id, data)
    
    def active_count(self) -> int:
        return len(self.active_connections)
