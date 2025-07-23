"""
Layer 2: TRIAGE - Event Triage Engine
Triple-Verified Architecture Implementation

This module implements the second layer of the Triple-Verified Architecture:
- Receives raw events from Layer 1 (Capture)
- Intelligently decides verification method (Playwright, API, or VLM)
- Takes "after" snapshots when needed
- Bundles all evidence for Layer 3 (Analysis)
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from playwright.async_api import Page
from fastapi import WebSocket
import json
import time
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class VerificationMethod(Enum):
    """Types of verification methods available."""
    PLAYWRIGHT_ONLY = "playwright"  # Fast DOM-based verification
    API_ONLY = "api"                # Google Sheets API verification
    VLM_ASSISTED = "vlm"            # VLM + API verification
    HYBRID = "hybrid"               # Multiple methods combined

@dataclass
class TriageDecision:
    """Decision made by the triage engine."""
    primary_method: VerificationMethod
    secondary_methods: List[VerificationMethod]
    requires_screenshot: bool
    requires_api_snapshot: bool
    confidence_threshold: float
    reasoning: str

class EventTriageEngine:
    """
    Layer 2: TRIAGE
    
    Receives raw events from Layer 1 and intelligently decides how to verify them.
    Takes snapshots and bundles evidence for Layer 3 analysis.
    """
    
    def __init__(self, page: Page, websocket: WebSocket, sheets_tool=None):
        self.page = page
        self.websocket = websocket
        self.sheets_tool = sheets_tool
        self.triage_active = False
        
        # State tracking for smart decisions
        self.last_screenshot = None
        self.last_api_state = None
        self.recent_events = []
        self.event_patterns = {}
        
    async def start_triage(self):
        """Start the triage engine."""
        logger.info("Starting Layer 2: TRIAGE - Event Triage Engine")
        self.triage_active = True
        
        # Take initial baseline snapshots
        await self._take_baseline_snapshots()
        
        logger.info("✅ Layer 2 TRIAGE engine active - ready to process events")
    
    async def process_raw_event(self, raw_event_data: Dict[str, Any]):
        """
        Main triage processing function.
        
        Receives raw event from Layer 1 and decides how to verify it.
        """
        try:
            event = raw_event_data.get("rawEvent", {})
            event_type = event.get("type")
            
            logger.info(f"🔍 Triaging event: {event_type} on {event.get('target', {}).get('tagName')}")
            
            # Make triage decision
            decision = await self._make_triage_decision(event)
            
            # Collect evidence based on decision
            evidence_bundle = await self._collect_evidence(event, decision)
            
            # Send to Layer 3 (Analysis)
            await self._send_to_analysis(evidence_bundle)
            
        except Exception as e:
            logger.error(f"Error in triage processing: {e}", exc_info=True)
    
    async def _make_triage_decision(self, event: Dict[str, Any]) -> TriageDecision:
        """
        Intelligent triage decision making.
        
        Decides the best verification method based on event context.
        """
        event_type = event.get("type")
        target = event.get("target", {})
        sheets_context = event.get("sheetsContext")
        
        # Rule-based triage logic
        
        # 1. FAST PLAYWRIGHT-ONLY VERIFICATION
        if self._is_simple_ui_interaction(event):
            return TriageDecision(
                primary_method=VerificationMethod.PLAYWRIGHT_ONLY,
                secondary_methods=[],
                requires_screenshot=False,
                requires_api_snapshot=False,
                confidence_threshold=0.9,
                reasoning="Simple UI interaction - DOM verification sufficient"
            )
        
        # 2. API-ONLY VERIFICATION (Google Sheets data changes)
        if self._is_data_modification(event):
            return TriageDecision(
                primary_method=VerificationMethod.API_ONLY,
                secondary_methods=[VerificationMethod.PLAYWRIGHT_ONLY],
                requires_screenshot=False,
                requires_api_snapshot=True,
                confidence_threshold=0.95,
                reasoning="Data modification - API verification most reliable"
            )
        
        # 3. VLM-ASSISTED VERIFICATION (Complex visual changes)
        if self._requires_visual_analysis(event):
            return TriageDecision(
                primary_method=VerificationMethod.VLM_ASSISTED,
                secondary_methods=[VerificationMethod.API_ONLY],
                requires_screenshot=True,
                requires_api_snapshot=True,
                confidence_threshold=0.8,
                reasoning="Complex visual change - VLM analysis needed"
            )
        
        # 4. HYBRID VERIFICATION (Uncertain cases)
        return TriageDecision(
            primary_method=VerificationMethod.HYBRID,
            secondary_methods=[VerificationMethod.PLAYWRIGHT_ONLY, VerificationMethod.API_ONLY],
            requires_screenshot=True,
            requires_api_snapshot=True,
            confidence_threshold=0.85,
            reasoning="Uncertain case - multiple verification methods"
        )
    
    def _is_simple_ui_interaction(self, event: Dict[str, Any]) -> bool:
        """Check if this is a simple UI interaction that doesn't change data."""
        event_type = event.get("type")
        target = event.get("target", {})
        
        # Focus/blur events
        if event_type in ["focus", "blur"]:
            return True
        
        # Hover events
        if event_type in ["mousemove", "mouseover"]:
            return True
        
        # Clicks on UI elements (not data cells)
        if event_type == "click":
            aria_label = target.get("ariaLabel", "")
            tag_name = target.get("tagName", "")
            
            # Toolbar/menu clicks
            if any(keyword in aria_label.lower() for keyword in ["menu", "toolbar", "button"]):
                return True
            
            # Non-data elements
            if tag_name.lower() in ["button", "div", "span"] and "cell" not in aria_label.lower():
                return True
        
        return False
    
    def _is_data_modification(self, event: Dict[str, Any]) -> bool:
        """Check if this event modifies spreadsheet data."""
        event_type = event.get("type")
        sheets_context = event.get("sheetsContext")
        target = event.get("target", {})
        
        # Input in cells
        if event_type == "input" and sheets_context and sheets_context.get("type") == "cell":
            return True
        
        # Key events in cells (Enter, Tab, etc.)
        if event_type in ["keydown", "keyup"] and sheets_context and sheets_context.get("type") == "cell":
            key = event.get("key", "")
            if key in ["Enter", "Tab", "Escape"]:
                return True
        
        # Paste operations
        if event_type == "keydown" and event.get("ctrlKey") and event.get("key") == "v":
            return True
        
        return False
    
    def _requires_visual_analysis(self, event: Dict[str, Any]) -> bool:
        """Check if this event requires VLM visual analysis."""
        event_type = event.get("type")
        target = event.get("target", {})
        
        # Formatting operations
        if event_type == "click":
            aria_label = target.get("ariaLabel", "").lower()
            
            # Formatting toolbar clicks
            if any(keyword in aria_label for keyword in ["bold", "italic", "color", "format", "border"]):
                return True
            
            # Chart/image operations
            if any(keyword in aria_label for keyword in ["chart", "image", "drawing"]):
                return True
        
        # Right-click context menus
        if event_type == "contextmenu":
            return True
        
        # Drag and drop operations
        if event_type in ["dragstart", "dragend", "drop"]:
            return True
        
        return False
    
    async def _collect_evidence(self, event: Dict[str, Any], decision: TriageDecision) -> Dict[str, Any]:
        """
        Collect evidence based on triage decision.
        
        This is where we take snapshots and gather data for Layer 3.
        """
        evidence = {
            "layer": "TRIAGE",
            "triageTimestamp": time.time(),
            "rawEvent": event,
            "triageDecision": {
                "primaryMethod": decision.primary_method.value,
                "secondaryMethods": [m.value for m in decision.secondary_methods],
                "requiresScreenshot": decision.requires_screenshot,
                "requiresApiSnapshot": decision.requires_api_snapshot,
                "confidenceThreshold": decision.confidence_threshold,
                "reasoning": decision.reasoning
            },
            "evidence": {}
        }
        
        # Collect Playwright evidence (always available)
        evidence["evidence"]["playwright"] = await self._collect_playwright_evidence(event)
        
        # Collect screenshot if needed
        if decision.requires_screenshot:
            evidence["evidence"]["screenshot"] = await self._collect_screenshot_evidence()
        
        # Collect API snapshot if needed
        if decision.requires_api_snapshot:
            evidence["evidence"]["api"] = await self._collect_api_evidence()
        
        return evidence
    
    async def _collect_playwright_evidence(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Collect Playwright-based evidence (DOM state, element info)."""
        try:
            # Get current page state
            page_info = {
                "url": self.page.url,
                "title": await self.page.title(),
                "timestamp": time.time()
            }
            
            # Get element-specific info if we have coordinates
            element_info = {}
            if event.get("coordinates"):
                coords = event["coordinates"]
                try:
                    # Get element at click position
                    element = await self.page.locator(f"*").element_at(coords["clientX"], coords["clientY"])
                    if element:
                        element_info = {
                            "tagName": await element.tag_name(),
                            "textContent": await element.text_content(),
                            "attributes": await element.get_attributes()
                        }
                except:
                    pass  # Element might not be accessible
            
            return {
                "pageInfo": page_info,
                "elementInfo": element_info,
                "domPath": event.get("domPath", ""),
                "sheetsContext": event.get("sheetsContext")
            }
            
        except Exception as e:
            logger.error(f"Error collecting Playwright evidence: {e}")
            return {"error": str(e)}
    
    async def _collect_screenshot_evidence(self) -> Dict[str, Any]:
        """Collect screenshot evidence for VLM analysis."""
        try:
            # Take current screenshot
            current_screenshot = await self.page.screenshot()
            
            evidence = {
                "currentScreenshot": current_screenshot.hex(),  # Convert to hex for JSON
                "timestamp": time.time()
            }
            
            # Include before screenshot if available
            if self.last_screenshot:
                evidence["beforeScreenshot"] = self.last_screenshot.hex()
            
            # Update last screenshot
            self.last_screenshot = current_screenshot
            
            return evidence
            
        except Exception as e:
            logger.error(f"Error collecting screenshot evidence: {e}")
            return {"error": str(e)}
    
    async def _collect_api_evidence(self) -> Dict[str, Any]:
        """Collect Google Sheets API evidence."""
        try:
            if not self.sheets_tool:
                return {"error": "No sheets tool available"}
            
            # Get current spreadsheet state
            current_state = await self._get_sheets_state()
            
            evidence = {
                "currentState": current_state,
                "timestamp": time.time()
            }
            
            # Include before state if available
            if self.last_api_state:
                evidence["beforeState"] = self.last_api_state
            
            # Update last state
            self.last_api_state = current_state
            
            return evidence
            
        except Exception as e:
            logger.error(f"Error collecting API evidence: {e}")
            return {"error": str(e)}
    
    async def _get_sheets_state(self) -> Dict[str, Any]:
        """Get current Google Sheets state via API."""
        try:
            # This would use the sheets tool to get current state
            # Implementation depends on sheets tool interface
            return {
                "placeholder": "sheets_state",
                "timestamp": time.time()
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _take_baseline_snapshots(self):
        """Take initial baseline snapshots."""
        try:
            # Take initial screenshot
            self.last_screenshot = await self.page.screenshot()
            
            # Take initial API state
            if self.sheets_tool:
                self.last_api_state = await self._get_sheets_state()
            
            logger.info("📸 Baseline snapshots taken")
            
        except Exception as e:
            logger.error(f"Error taking baseline snapshots: {e}")
    
    async def _send_to_analysis(self, evidence_bundle: Dict[str, Any]):
        """Send evidence bundle to Layer 3 (Analysis)."""
        try:
            message = {
                "type": "EVIDENCE_BUNDLE",
                "data": evidence_bundle
            }
            
            await self.websocket.send_json(message)
            
            logger.debug(f"📦 Sent evidence bundle to Layer 3: {evidence_bundle['triageDecision']['primaryMethod']}")
            
        except Exception as e:
            logger.error(f"Failed to send evidence to analysis: {e}")
    
    async def stop_triage(self):
        """Stop the triage engine."""
        self.triage_active = False
        logger.info("🛑 Layer 2 TRIAGE engine stopped")

class TriageManager:
    """Manages multiple triage sessions."""
    
    def __init__(self):
        self.active_triages: Dict[str, EventTriageEngine] = {}
    
    async def create_triage_session(self, user_id: str, page: Page, websocket: WebSocket, sheets_tool=None) -> EventTriageEngine:
        """Create a new triage session."""
        
        # Stop existing triage if any
        if user_id in self.active_triages:
            await self.active_triages[user_id].stop_triage()
        
        # Create new triage session
        triage = EventTriageEngine(page, websocket, sheets_tool)
        self.active_triages[user_id] = triage
        
        await triage.start_triage()
        
        logger.info(f"✅ Created Layer 2 TRIAGE session for user {user_id}")
        return triage
    
    async def stop_triage_session(self, user_id: str):
        """Stop triage session for a user."""
        if user_id in self.active_triages:
            await self.active_triages[user_id].stop_triage()
            del self.active_triages[user_id]
            logger.info(f"🛑 Stopped Layer 2 TRIAGE session for user {user_id}")

# Global triage manager instance
triage_manager = TriageManager()
