"""
Webhook Handler for Aurora Agent
Receives events from Google Apps Script and forwards to WebSocket clients
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import HTTPException
from .websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

class WebhookHandler:
    """Handles incoming webhook events from Google Apps Script"""
    
    def __init__(self):
        self.supported_events = {
            "SHEET_CHANGE",
            "CELL_UPDATE", 
            "ROW_INSERT",
            "ROW_DELETE",
            "FORMULA_UPDATE"
        }
    
    async def process_webhook_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming webhook event from Google Apps Script
        
        Expected payload format:
        {
            "event_type": "SHEET_CHANGE",
            "user_id": "default_teacher", 
            "sheet_id": "1ABC123...",
            "sheet_name": "Lesson Plan",
            "change_type": "CELL_UPDATE",
            "range": "A1:B2",
            "old_values": [["old1", "old2"]],
            "new_values": [["new1", "new2"]],
            "timestamp": "2025-07-21T23:30:00Z",
            "metadata": {...}
        }
        """
        try:
            # Validate required fields
            required_fields = ["event_type", "user_id", "sheet_id"]
            for field in required_fields:
                if field not in payload:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Missing required field: {field}"
                    )
            
            event_type = payload["event_type"]
            user_id = payload["user_id"]
            
            # Validate event type
            if event_type not in self.supported_events:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported event type: {event_type}. Supported: {self.supported_events}"
                )
            
            # Add processing timestamp
            payload["processed_at"] = datetime.utcnow().isoformat()
            
            # Log the event
            logger.info(f"Processing webhook event: {event_type} for user: {user_id}")
            logger.debug(f"Event payload: {payload}")
            
            # Forward to WebSocket client
            success = await websocket_manager.send_to_user(user_id, {
                "type": "webhook_event",
                "event": payload
            })
            
            if success:
                return {
                    "status": "success",
                    "message": f"Event {event_type} forwarded to user {user_id}",
                    "event_id": payload.get("event_id", "unknown"),
                    "processed_at": payload["processed_at"]
                }
            else:
                # User not connected, but event was valid
                logger.warning(f"User {user_id} not connected via WebSocket")
                return {
                    "status": "user_offline",
                    "message": f"User {user_id} not connected, event stored for later",
                    "event_id": payload.get("event_id", "unknown"),
                    "processed_at": payload["processed_at"]
                }
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing webhook event: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )
    
    def format_sheet_change_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Format sheet change event for frontend consumption"""
        return {
            "type": "SHEET_CHANGE",
            "sheet_id": payload.get("sheet_id"),
            "sheet_name": payload.get("sheet_name"),
            "change_type": payload.get("change_type"),
            "range": payload.get("range"),
            "old_values": payload.get("old_values", []),
            "new_values": payload.get("new_values", []),
            "timestamp": payload.get("timestamp"),
            "user_action": self._determine_user_action(payload),
            "metadata": payload.get("metadata", {})
        }
    
    def _determine_user_action(self, payload: Dict[str, Any]) -> str:
        """Determine what action the user likely took based on the change"""
        change_type = payload.get("change_type", "").upper()
        range_info = payload.get("range", "")
        
        if change_type == "ROW_INSERT":
            return "added_lesson_item"
        elif change_type == "ROW_DELETE":
            return "removed_lesson_item"
        elif change_type == "CELL_UPDATE":
            if "A" in range_info:  # Column A typically contains lesson titles
                return "updated_lesson_title"
            elif "B" in range_info:  # Column B might contain descriptions
                return "updated_lesson_description"
            else:
                return "updated_lesson_content"
        elif change_type == "FORMULA_UPDATE":
            return "updated_lesson_formula"
        else:
            return "modified_lesson_plan"

# Global webhook handler instance
webhook_handler = WebhookHandler()
