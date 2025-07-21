"""
WebSocket Manager for Aurora Agent
Handles real-time communication between backend and frontend
"""
import json
import logging
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages active WebSocket connections for real-time communication"""
    
    def __init__(self):
        # Map user_id to their active WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        
    async def connect(self, user_id: str, websocket: WebSocket):
        """Accept a new WebSocket connection and store it"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected for user: {user_id}")
        
        # Send connection confirmation
        await self.send_to_user(user_id, {
            "type": "connection_established",
            "message": "WebSocket connection established",
            "user_id": user_id
        })
    
    def disconnect(self, user_id: str):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            logger.info(f"WebSocket disconnected for user: {user_id}")
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to a specific user's WebSocket"""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.send_text(json.dumps(message))
                logger.debug(f"Message sent to user {user_id}: {message.get('type', 'unknown')}")
                return True
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                # Remove the broken connection
                self.disconnect(user_id)
                return False
        else:
            logger.warning(f"No active WebSocket connection for user: {user_id}")
            return False
    
    async def broadcast(self, message: dict):
        """Send a message to all connected users"""
        disconnected_users = []
        
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected_users.append(user_id)
        
        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)
    
    def get_active_users(self) -> list:
        """Get list of currently connected user IDs"""
        return list(self.active_connections.keys())
    
    def is_user_connected(self, user_id: str) -> bool:
        """Check if a user has an active WebSocket connection"""
        return user_id in self.active_connections

# Global WebSocket manager instance
websocket_manager = WebSocketManager()
