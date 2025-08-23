"""
WebSocket manager for real-time consequence feedback
"""

from __future__ import annotations

import json
import asyncio
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect


class WebSocketManager:
    """Manages WebSocket connections and broadcasts events."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.player_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, player_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        if player_id:
            self.player_connections[player_id] = websocket
    
    def disconnect(self, websocket: WebSocket, player_id: Optional[str] = None):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        if player_id and player_id in self.player_connections:
            del self.player_connections[player_id]
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        message_json = json.dumps(message)
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except WebSocketDisconnect:
                disconnected.add(connection)
            except Exception:
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.active_connections.discard(connection)
    
    async def send_to_player(self, player_id: str, message: Dict[str, Any]):
        """Send a message to a specific player."""
        if player_id not in self.player_connections:
            return
        
        connection = self.player_connections[player_id]
        try:
            message_json = json.dumps(message)
            await connection.send_text(message_json)
        except WebSocketDisconnect:
            self.disconnect(connection, player_id)
        except Exception:
            self.disconnect(connection, player_id)
    
    async def emit_consequence_toast(
        self,
        kind: str,
        label: str,
        player_id: Optional[str] = None,
        delta: Optional[float] = None,
        npc_id: Optional[str] = None
    ):
        """Emit a consequence toast event."""
        message = {
            "type": "consequence_toast",
            "payload": {
                "kind": kind,
                "label": label,
                "delta": delta,
                "npc_id": npc_id
            }
        }
        
        if player_id:
            await self.send_to_player(player_id, message)
        else:
            await self.broadcast(message)


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
