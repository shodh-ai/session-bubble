"""
Triple-Verified Architecture Integration Layer
Connects the new 4-layer architecture with existing Aurora Agent system

This module provides a clean interface to start/stop Triple-Verified sessions
and integrates with the existing SessionCore, WebSocket, and authentication systems.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page
from fastapi import WebSocket

from capture_layer import capture_manager, EventCapture
from triage_layer import triage_manager, EventTriageEngine
from browser_manager import browser_manager

logger = logging.getLogger(__name__)

class TripleVerifiedSession:
    """
    Integration layer for the Triple-Verified Architecture.
    
    Manages all 4 layers:
    - Layer 1: CAPTURE (Real-time event streaming)
    - Layer 2: TRIAGE (Intelligent verification routing)
    - Layer 3: ANALYSIS (AI synthesis - to be implemented)
    - Layer 4: PRESENTATION (WebSocket to frontend)
    """
    
    def __init__(self, user_id: str, websocket: WebSocket):
        self.user_id = user_id
        self.websocket = websocket
        self.session_active = False
        
        # Layer components
        self.capture: Optional[EventCapture] = None
        self.triage: Optional[EventTriageEngine] = None
        self.page: Optional[Page] = None
        
        # Message routing
        self.message_handlers = {
            "RAW_EVENT_STREAM": self._handle_raw_event,
            "EVIDENCE_BUNDLE": self._handle_evidence_bundle
        }
    
    async def start_session(self, spreadsheet_url: str) -> Dict[str, Any]:
        """
        Start a Triple-Verified session.
        
        This replaces the old SessionCore.start_session method.
        """
        try:
            logger.info(f"🚀 Starting Triple-Verified session for user {self.user_id}")
            
            # Step 1: Launch browser and navigate to spreadsheet
            self.page = await browser_manager.get_page()
            await self.page.goto(spreadsheet_url)
            
            # Step 2: Start Layer 1 (CAPTURE)
            self.capture = await capture_manager.create_capture_session(
                self.user_id, self.page, self.websocket
            )
            
            # Step 3: Start Layer 2 (TRIAGE)
            # Note: sheets_tool integration will be added when Layer 3 is implemented
            self.triage = await triage_manager.create_triage_session(
                self.user_id, self.page, self.websocket, sheets_tool=None
            )
            
            # Step 4: Start message routing
            self.session_active = True
            asyncio.create_task(self._message_router())
            
            # Notify frontend
            await self._send_websocket_message({
                "type": "SESSION_STARTED",
                "message": "Triple-Verified Architecture session started - real-time event streaming active",
                "architecture": "triple_verified",
                "layers": {
                    "capture": "✅ Active - Real-time event streaming",
                    "triage": "✅ Active - Intelligent verification routing", 
                    "analysis": "🔄 Coming next - AI synthesis layer",
                    "presentation": "✅ Active - WebSocket communication"
                }
            })
            
            logger.info("✅ Triple-Verified session fully active")
            return {"success": True, "message": "Triple-Verified session started successfully"}
            
        except Exception as e:
            logger.error(f"Failed to start Triple-Verified session: {e}", exc_info=True)
            await self.stop_session()
            return {"success": False, "error": str(e)}
    
    async def _message_router(self):
        """
        Route messages between layers.
        
        This handles the flow:
        Layer 1 → Layer 2 → Layer 3 → Layer 4
        """
        logger.info("📡 Message router started for Triple-Verified Architecture")
        
        # Note: In a full implementation, this would listen to a message queue
        # For now, we'll handle messages via the WebSocket message handlers
        
        while self.session_active:
            try:
                # This is a placeholder for the message routing logic
                # In practice, messages flow through the WebSocket handlers
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in message router: {e}")
                break
        
        logger.info("📡 Message router stopped")
    
    async def _handle_raw_event(self, message_data: Dict[str, Any]):
        """
        Handle RAW_EVENT_STREAM messages from Layer 1 (CAPTURE).
        
        Route to Layer 2 (TRIAGE) for processing.
        """
        try:
            if self.triage:
                await self.triage.process_raw_event(message_data)
            else:
                logger.warning("Received raw event but triage engine not available")
                
        except Exception as e:
            logger.error(f"Error handling raw event: {e}", exc_info=True)
    
    async def _handle_evidence_bundle(self, message_data: Dict[str, Any]):
        """
        Handle EVIDENCE_BUNDLE messages from Layer 2 (TRIAGE).
        
        This will route to Layer 3 (ANALYSIS) when implemented.
        For now, we'll create a simple verified action.
        """
        try:
            evidence = message_data.get("data", {})
            raw_event = evidence.get("rawEvent", {})
            decision = evidence.get("triageDecision", {})
            
            # Temporary: Create a simple verified action
            # This will be replaced by Layer 3 (AI Synthesis)
            verified_action = {
                "type": "VERIFIED_ACTION",
                "interpretation": f"Triple-Verified: {raw_event.get('type')} on {raw_event.get('target', {}).get('tagName')}",
                "verification": f"Verified via {decision.get('primaryMethod', 'unknown')} method",
                "status": "SUCCESS",
                "tool_name": "triple_verified_triage",
                "parameters": {
                    "event_type": raw_event.get("type"),
                    "target": raw_event.get("target", {}),
                    "verification_method": decision.get("primaryMethod"),
                    "confidence": decision.get("confidenceThreshold", 0.8)
                },
                "confidence": decision.get("confidenceThreshold", 0.8),
                "timestamp": evidence.get("triageTimestamp", ""),
                "architecture": "triple_verified",
                "triage_reasoning": decision.get("reasoning", "")
            }
            
            # Send to Layer 4 (PRESENTATION)
            await self._send_websocket_message(verified_action)
            
            logger.info(f"📦 Processed evidence bundle: {decision.get('primaryMethod')} → {raw_event.get('type')}")
            
        except Exception as e:
            logger.error(f"Error handling evidence bundle: {e}", exc_info=True)
    
    async def handle_websocket_message(self, message: Dict[str, Any]):
        """
        Handle incoming WebSocket messages and route to appropriate layer.
        
        This is called by the FastAPI WebSocket endpoint.
        """
        try:
            message_type = message.get("type")
            
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](message.get("data", {}))
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
    
    async def _send_websocket_message(self, message: Dict[str, Any]):
        """Send message to frontend via WebSocket."""
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")
            self.session_active = False
    
    async def stop_session(self):
        """Stop the Triple-Verified session and clean up all layers."""
        logger.info(f"🛑 Stopping Triple-Verified session for user {self.user_id}")
        
        self.session_active = False
        
        # Stop Layer 1 (CAPTURE)
        if self.capture:
            await capture_manager.stop_capture_session(self.user_id)
        
        # Stop Layer 2 (TRIAGE)  
        if self.triage:
            await triage_manager.stop_triage_session(self.user_id)
        
        # Close browser
        await browser_manager.close_browser()
        
        logger.info("✅ Triple-Verified session stopped and cleaned up")

# Global session management
active_triple_verified_sessions: Dict[str, TripleVerifiedSession] = {}

async def get_or_create_triple_verified_session(user_id: str, websocket: WebSocket) -> TripleVerifiedSession:
    """Get or create a Triple-Verified session for a user."""
    if user_id not in active_triple_verified_sessions:
        active_triple_verified_sessions[user_id] = TripleVerifiedSession(user_id, websocket)
    else:
        # Update WebSocket for reconnecting user
        active_triple_verified_sessions[user_id].websocket = websocket
    
    return active_triple_verified_sessions[user_id]

async def cleanup_triple_verified_session(user_id: str):
    """Clean up a Triple-Verified session."""
    if user_id in active_triple_verified_sessions:
        await active_triple_verified_sessions[user_id].stop_session()
        del active_triple_verified_sessions[user_id]
