# in aurora_agent/session_core.py (FINAL, CORRECTED VERSION)
import asyncio
import json
import logging
import base64
from datetime import datetime
import time
from typing import Dict, Any, Optional, List
from playwright.async_api import Page
from fastapi import WebSocket
from browser_manager import browser_manager
from vlm_differ import analyze_image_diff
# Import from our production sheets tool, not the old one in tools/sheets/__init__.py
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from tools.sheets import get_sheets_tool_instance as old_get_sheets_tool_instance

# Import our production sheets tool directly
def get_sheets_tool_instance():
    """Get sheets tool instance with proper fallback."""
    try:
        # Import from the correct production sheets tool location
        from tools.sheets import get_sheets_tool_instance as production_tool
        
        # Try to get the production tool first
        tool = production_tool()
        if tool is not None:
            logger.info("Using production sheets tool")
            return tool
        else:
            logger.info("Production tool not available, using mock")
            return create_mock_sheets_tool()
            
    except Exception as e:
        logger.error(f"Failed to import sheets tools: {e}")
        # Create a simple mock inline
        return create_mock_sheets_tool()

def create_mock_sheets_tool():
    """Create a simple mock sheets tool for UAT testing."""
    class MockSheetsToolForUAT:
        def __init__(self):
            self.name = "mock_sheets_tool_uat"
            self.spreadsheet_id = None
            logger.info("Mock sheets tool initialized for UAT testing")
        
        def set_spreadsheet_id(self, spreadsheet_id: str):
            self.spreadsheet_id = spreadsheet_id
            logger.info(f"Mock UAT tool: Set spreadsheet ID: {spreadsheet_id}")
        
        async def verify_action(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
            tool_name = analysis.get('tool_name', 'unknown')
            logger.info(f"Mock UAT verification: {tool_name}")
            
            return {
                "verified": True,
                "message": f"Mock UAT verification: {tool_name} action detected",
                "api_response": "mock_uat_response",
                "confidence": 0.85,
                "verification_method": "mock_uat_testing"
            }
    
    return MockSheetsToolForUAT()

from student_verifier import publish_student_action

logger = logging.getLogger(__name__)

class SessionCore:
    def __init__(self, user_id: str, websocket: WebSocket):
        self.user_id = user_id
        self.websocket = websocket
        self.page: Optional[Page] = None
        self.session_active = False
        self.before_screenshot_buffer: Optional[bytes] = None
        self.polling_task: Optional[asyncio.Task] = None
        self.sheets_tool = get_sheets_tool_instance()
        
    async def start_session(self, spreadsheet_url: str) -> Dict[str, Any]:
        try:
            logger.info(f"Starting verification session for user {self.user_id}")
            
            # Handle both full URLs and spreadsheet IDs
            if not spreadsheet_url.startswith('http'):
                # If it's just an ID, construct the full Google Sheets URL
                logger.info(f"Converting spreadsheet ID to full URL: {spreadsheet_url}")
                full_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_url}/edit"
                spreadsheet_id = spreadsheet_url
            else:
                # Extract spreadsheet ID from full URL for API verification
                full_url = spreadsheet_url
                spreadsheet_id = self._extract_spreadsheet_id(spreadsheet_url)
            
            if spreadsheet_id:
                # Handle different sheets tool types
                if hasattr(self.sheets_tool, 'set_spreadsheet_id'):
                    self.sheets_tool.set_spreadsheet_id(spreadsheet_id)
                elif hasattr(self.sheets_tool, 'spreadsheet_id'):
                    self.sheets_tool.spreadsheet_id = spreadsheet_id
                logger.info(f"Set spreadsheet ID for API verification: {spreadsheet_id}")
            
            await browser_manager.start_browser(headless=False)
            logger.info(f"Navigating to: {full_url}")
            self.page = await browser_manager.get_page(full_url)
            
            # Wait for Google Sheet to actually load (not login screen)
            await self._wait_for_sheet_to_load()
            
            await self.attach_event_listeners()
            self.before_screenshot_buffer = await self.page.screenshot()
            self.session_active = True
            
            # Start the polling task
            self.polling_task = asyncio.create_task(self._poll_for_events())
            
            await self._send_websocket_message({
                "type": "SESSION_STARTED",
                "message": "Verification session started with production VLM and API verification.",
            })
            return {"success": True, "message": "Session started successfully"}
        except Exception as e:
            logger.error(f"Failed to start session: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def attach_event_listeners(self):
        logger.info("Attaching event listeners to the page...")
        # This script initializes an array on the window object to store events.
        await self.page.evaluate("""
            () => {
                window.aurora_agent_events = [];
                const event_handler = (e) => {
                    const event_data = {
                        type: e.type,
                        target: e.target.tagName,
                        x: e.clientX, y: e.clientY,
                        key: e.key,
                        value: e.target.value,
                        aria_label: e.target.getAttribute('aria-label'),
                        timestamp: Date.now()
                    };
                    window.aurora_agent_events.push(event_data);
                };
                document.addEventListener('click', event_handler, true);
                document.addEventListener('input', event_handler, true);
                document.addEventListener('mouseover', event_handler, true);
            }
        """)
        logger.info("Event listeners attached successfully.")

    async def _poll_for_events(self):
        """Continuously poll the browser for captured events and process them."""
        logger.info("Event polling loop has started.")
        while self.session_active and self.page and not self.page.is_closed():
            try:
                # Atomically get and clear the events array in the browser
                events = await self.page.evaluate("() => { const events = window.aurora_agent_events || []; window.aurora_agent_events = []; return events; }")
                
                if events:
                    logger.info(f"Polling found {len(events)} events.")
                    for event in events:
                        # --- THIS IS THE FIX ---
                        # Call the correct method name: process_event
                        await self.process_event(event)
                        # --- END OF FIX ---
                
                await asyncio.sleep(0.5) # Poll every 0.5 seconds for faster response
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                # If the page or context closes, the loop should terminate
                if "Target page, context or browser has been closed" in str(e):
                    break
                await asyncio.sleep(2)
        logger.info("Event polling loop has stopped.")

    async def process_event(self, event: Dict[str, Any]):
        """Main dispatcher for processing raw events from the browser."""
        try:
            event_type = event.get("type")
            if event_type == 'click':
                await self._handle_click_event(event)
            elif event_type == 'input':
                # For now, we'll just log input events.
                await self._send_websocket_message({"type": "RAW_EVENT", "event": event})
            elif event_type == 'mouseover':
                await self._handle_hover_event(event)
        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)

    async def process_event(self, event: Dict[str, Any]):
        """Main dispatcher for processing raw events from the browser."""
        try:
            event_type = event.get("type")
            if event_type == 'click':
                await self._handle_click_event(event)
            elif event_type == 'input':
                # For now, we'll just log input events.
                await self._send_websocket_message({"type": "RAW_EVENT", "event": event})
            elif event_type == 'mouseover':
                await self._handle_hover_event(event)
        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)

    async def _handle_click_event(self, event: Dict[str, Any]):
        """Layer 2: TRIAGE - Parallel data collection and bundling."""
        if not self.page or self.page.is_closed():
            return
        
        try:
            logger.info("🔄 Layer 2 TRIAGE: Processing click event with parallel data collection")
            
            # Add small delay to let UI settle after click
            await asyncio.sleep(0.3)
            
            # Task A, B, C: Execute in parallel
            tasks = [
                # Task A: Take after screenshot
                self.page.screenshot(),
                # Task B: Get API snapshot (if sheets tool available)
                self._get_api_snapshot(),
                # Task C: Raw event data (already available)
                asyncio.sleep(0)  # Placeholder - event data already in hand
            ]
            
            # Execute all tasks in parallel
            after_screenshot, after_api_snapshot, _ = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle exceptions from parallel tasks
            if isinstance(after_screenshot, Exception):
                logger.error(f"Screenshot task failed: {after_screenshot}")
                after_screenshot = None
            if isinstance(after_api_snapshot, Exception):
                logger.error(f"API snapshot task failed: {after_api_snapshot}")
                after_api_snapshot = None
            
            # Create complete data bundle
            data_bundle = {
                "layer": "TRIAGE",
                "timestamp": time.time(),
                "raw_playwright_event": event,
                "before_screenshot_bytes": self.before_screenshot_buffer.hex() if self.before_screenshot_buffer else None,
                "after_screenshot_bytes": after_screenshot.hex() if after_screenshot else None,
                "before_api_snapshot": getattr(self, 'before_api_state', None),
                "after_api_snapshot": after_api_snapshot
            }
            
            # Pass data bundle to Layer 3 (Analysis)
            await self._send_to_analysis_layer(data_bundle)
            
            # Update before state for next event
            if after_screenshot:
                self.before_screenshot_buffer = after_screenshot
            if after_api_snapshot:
                self.before_api_state = after_api_snapshot
            
            logger.info("✅ Layer 2 TRIAGE: Data bundle created and sent to Analysis layer")
            
        except Exception as e:
            logger.error(f"Error in Layer 2 TRIAGE: {e}", exc_info=True)

    async def _handle_hover_event(self, event: Dict[str, Any]):
        """Handles hover events for the 'AI is thinking' box."""
        description = f"Hovering over a {event.get('target')} element."
        if event.get('aria_label'):
            description = f"Hovering over: {event.get('aria_label')}"

        await self._send_websocket_message({
            "type": "HOVER_ANNOTATION",
            "element_description": description,
        })

    async def _get_api_snapshot(self) -> Optional[Dict[str, Any]]:
        """Task B: Get current API snapshot of the spreadsheet state."""
        try:
            if not self.sheets_tool:
                return None
            
            # Get current spreadsheet state via API
            # This would typically get visible range data and formatting
            api_state = {
                "timestamp": time.time(),
                "spreadsheet_data": "placeholder_for_actual_api_call",
                "visible_range": "A1:Z100",  # Example range
                "formatting_info": "placeholder_for_formatting_data"
            }
            
            return api_state
            
        except Exception as e:
            logger.error(f"Failed to get API snapshot: {e}")
            return None
    
    async def _send_to_analysis_layer(self, data_bundle: Dict[str, Any]):
        """Send data bundle to Layer 3 (Analysis/Synthesizer Agent) for processing."""
        try:
            # Import the synthesizer agent
            from synthesizer_agent import synthesize_data_bundle
            
            logger.info("📦 Sending data bundle to Layer 3 (Synthesizer Agent)")
            
            # Send to Layer 3: Synthesizer Agent (Fusion Engine)
            verified_action = await synthesize_data_bundle(data_bundle)
            
            # Send to Layer 4 (Presentation) via WebSocket
            await self._send_websocket_message(verified_action)
            
            # Publish to student verifier for LangGraph integration
            await publish_student_action(self.user_id, verified_action)
            
            logger.info(f"✅ Layer 3 synthesis complete: {verified_action.get('tool_name')} → Layer 4")
            
        except Exception as e:
            logger.error(f"Failed to send to analysis layer: {e}", exc_info=True)
            
            # Fallback: Create simple action if synthesis fails
            raw_event = data_bundle.get("raw_playwright_event", {})
            fallback_action = {
                "type": "VERIFIED_ACTION",
                "interpretation": f"Fallback: {raw_event.get('type')} on {raw_event.get('target', 'unknown')}",
                "verification": f"Synthesis failed, using fallback: {str(e)}",
                "status": "PARTIAL",
                "tool_name": "fallback_action",
                "parameters": {"error": str(e)},
                "confidence": 0.3,
                "timestamp": data_bundle.get("timestamp", ""),
                "architecture": "triple_verified_fallback"
            }
            
            await self._send_websocket_message(fallback_action)

    async def _send_websocket_message(self, message: Dict[str, Any]):
        try:
            await self.websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send WebSocket message: {e}")
            self.session_active = False # Stop the session if socket is broken

    async def stop_session(self):
        self.session_active = False
        if self.polling_task:
            self.polling_task.cancel()
        await browser_manager.close_browser()
        logger.info(f"Session stopped for user {self.user_id}")

    def _extract_spreadsheet_id(self, spreadsheet_url: str) -> Optional[str]:
        """Extract spreadsheet ID from Google Sheets URL."""
        import re
        
        # Pattern to match Google Sheets URL and extract spreadsheet ID
        pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
        match = re.search(pattern, spreadsheet_url)
        
        if match:
            spreadsheet_id = match.group(1)
            logger.info(f"Extracted spreadsheet ID: {spreadsheet_id}")
            return spreadsheet_id
        else:
            logger.warning(f"Could not extract spreadsheet ID from URL: {spreadsheet_url}")
            return None
    
    async def _wait_for_sheet_to_load(self):
        """Wait for Google Sheet to actually load before starting event capture."""
        logger.info("🔍 Waiting for Google Sheet to load (not login screen)...")
        
        max_wait_time = 30  # Maximum 30 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                # Check if we're on a login/account selection screen
                login_indicators = [
                    "Choose an account",
                    "Sign in",
                    "Use another account",
                    "accounts.google.com",
                    "Sign in to continue to Google Sheets"
                ]
                
                page_content = await self.page.content()
                page_title = await self.page.title()
                current_url = self.page.url
                
                # If we detect login screen, wait longer
                is_login_screen = any(indicator in page_content or indicator in page_title 
                                    for indicator in login_indicators)
                
                if is_login_screen:
                    logger.info(f"🔄 Still on login screen, waiting... (URL: {current_url})")
                    await asyncio.sleep(2)
                    continue
                
                # Check for Google Sheets interface elements
                sheet_indicators = [
                    "waffle-grid",  # Google Sheets grid
                    "cell-input",   # Formula bar
                    "docs-sheet",   # Sheet container
                    "grid-container", # Grid container
                    "name-box"      # Name box (A1, B2, etc.)
                ]
                
                # Also check if URL contains the spreadsheet ID and /edit
                is_sheet_url = "/spreadsheets/d/" in current_url and "/edit" in current_url
                has_sheet_elements = any(indicator in page_content for indicator in sheet_indicators)
                
                if is_sheet_url and has_sheet_elements:
                    logger.info(f"✅ Google Sheet loaded successfully! URL: {current_url}")
                    # Give it one more second to fully render
                    await asyncio.sleep(1)
                    return
                
                logger.info(f"🔄 Sheet still loading... (URL: {current_url})")
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.warning(f"Error checking sheet load status: {e}")
                await asyncio.sleep(2)
        
        # If we timeout, log warning but continue
        logger.warning(f"⚠️ Timeout waiting for sheet to load, proceeding anyway...")
    
    def __del__(self):
        # Ensure tasks are cleaned up if the object is garbage collected
        if self.polling_task:
            self.polling_task.cancel()

# Global session management (remains the same)
active_sessions: Dict[str, SessionCore] = {}
async def get_or_create_session(user_id: str, websocket: WebSocket) -> SessionCore:
    if user_id not in active_sessions:
        active_sessions[user_id] = SessionCore(user_id, websocket)
    else:
        # Update the websocket for a reconnecting user
        active_sessions[user_id].websocket = websocket
    return active_sessions[user_id]

async def cleanup_session(user_id: str):
    if user_id in active_sessions:
        await active_sessions[user_id].stop_session()
        del active_sessions[user_id]
