"""
Layer 1: CAPTURE - Real-Time Playwright Event Streaming
Triple-Verified Architecture Implementation

This module implements the first layer of the Triple-Verified Architecture:
- Real-time event capture from Playwright browser
- Rich event context extraction
- WebSocket streaming to backend triage
- Canvas-aware coordinate mapping
- Multiple event type support
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from playwright.async_api import Page, WebSocket as PlaywrightWebSocket
from fastapi import WebSocket
import json
import time

logger = logging.getLogger(__name__)

class EventCapture:
    """
    Layer 1: CAPTURE
    
    Captures raw browser events with rich context and streams them
    in real-time to the backend triage system via WebSocket.
    """
    
    def __init__(self, page: Page, backend_websocket: WebSocket):
        self.page = page
        self.backend_websocket = backend_websocket
        self.capture_active = False
        self.event_counter = 0
        
    async def start_capture(self):
        """Initialize real-time event capture with comprehensive listeners."""
        logger.info("Starting Layer 1: CAPTURE - Real-time event streaming")
        
        # Inject the event capture system into the browser
        await self._inject_capture_system()
        
        # Set up Playwright event listeners
        await self._setup_playwright_listeners()
        
        self.capture_active = True
        logger.info("✅ Layer 1 CAPTURE system active - streaming events to triage")
        
    async def _inject_capture_system(self):
        """Inject comprehensive event capture JavaScript into the browser."""
        
        capture_script = """
        () => {
            // Initialize Aurora Agent capture system
            window.auroraCapture = {
                eventBuffer: [],
                sessionId: Date.now(),
                
                // Enhanced event context extraction
                extractEventContext: function(event) {
                    const target = event.target;
                    const rect = target.getBoundingClientRect();
                    
                    return {
                        // Basic event info
                        type: event.type,
                        timestamp: Date.now(),
                        
                        // Target element context
                        target: {
                            tagName: target.tagName,
                            id: target.id,
                            className: target.className,
                            ariaLabel: target.getAttribute('aria-label'),
                            placeholder: target.placeholder,
                            value: target.value,
                            textContent: target.textContent?.slice(0, 100), // First 100 chars
                            
                            // Element positioning
                            rect: {
                                x: rect.x,
                                y: rect.y,
                                width: rect.width,
                                height: rect.height
                            }
                        },
                        
                        // Event-specific data
                        coordinates: {
                            clientX: event.clientX,
                            clientY: event.clientY,
                            pageX: event.pageX,
                            pageY: event.pageY,
                            offsetX: event.offsetX,
                            offsetY: event.offsetY
                        },
                        
                        // Keyboard events
                        key: event.key,
                        code: event.code,
                        ctrlKey: event.ctrlKey,
                        shiftKey: event.shiftKey,
                        altKey: event.altKey,
                        metaKey: event.metaKey,
                        
                        // Google Sheets specific context
                        sheetsContext: this.extractSheetsContext(target),
                        
                        // DOM path for precise targeting
                        domPath: this.getDOMPath(target)
                    };
                },
                
                // Extract Google Sheets specific context
                extractSheetsContext: function(target) {
                    // Check if we're in Google Sheets
                    if (!window.location.hostname.includes('docs.google.com')) {
                        return null;
                    }
                    
                    // Try to extract cell information
                    const cellElement = target.closest('[role="gridcell"]');
                    if (cellElement) {
                        return {
                            type: 'cell',
                            cellId: cellElement.getAttribute('id'),
                            ariaLabel: cellElement.getAttribute('aria-label'),
                            row: cellElement.getAttribute('aria-rowindex'),
                            col: cellElement.getAttribute('aria-colindex')
                        };
                    }
                    
                    // Check for toolbar/menu elements
                    const toolbarElement = target.closest('[role="toolbar"], [role="menubar"]');
                    if (toolbarElement) {
                        return {
                            type: 'toolbar',
                            toolbarId: toolbarElement.getAttribute('id'),
                            ariaLabel: toolbarElement.getAttribute('aria-label')
                        };
                    }
                    
                    return {
                        type: 'other',
                        context: 'sheets_interface'
                    };
                },
                
                // Get DOM path for element
                getDOMPath: function(element) {
                    const path = [];
                    let current = element;
                    
                    while (current && current !== document.body) {
                        let selector = current.tagName.toLowerCase();
                        
                        if (current.id) {
                            selector += '#' + current.id;
                        } else if (current.className) {
                            selector += '.' + current.className.split(' ')[0];
                        }
                        
                        path.unshift(selector);
                        current = current.parentElement;
                    }
                    
                    return path.join(' > ');
                },
                
                // Stream event to backend
                streamEvent: function(eventData) {
                    // Send via custom event that Playwright can listen to
                    const customEvent = new CustomEvent('auroraAgentEvent', {
                        detail: eventData
                    });
                    document.dispatchEvent(customEvent);
                }
            };
            
            // Set up comprehensive event listeners
            const eventTypes = [
                'click', 'dblclick', 'contextmenu',
                'keydown', 'keyup', 'input',
                'focus', 'blur', 'change',
                'mousedown', 'mouseup', 'mousemove',
                'dragstart', 'dragend', 'drop'
            ];
            
            eventTypes.forEach(eventType => {
                document.addEventListener(eventType, (event) => {
                    const eventData = window.auroraCapture.extractEventContext(event);
                    eventData.eventId = ++window.auroraCapture.eventCounter;
                    
                    // Stream immediately to backend
                    window.auroraCapture.streamEvent(eventData);
                }, true); // Use capture phase for better event catching
            });
            
            console.log('🎯 Aurora Agent Layer 1 CAPTURE system initialized');
        }
        """
        
        await self.page.evaluate(capture_script)
        
    async def _setup_playwright_listeners(self):
        """Set up Playwright listeners for the custom events from browser."""
        
        # Listen for our custom events
        await self.page.expose_function("auroraStreamEvent", self._handle_streamed_event)
        
        # Alternative: Listen for custom events via page evaluation
        await self.page.evaluate("""
            () => {
                document.addEventListener('auroraAgentEvent', (event) => {
                    // Call the exposed function
                    window.auroraStreamEvent(event.detail);
                });
            }
        """)
        
    async def _handle_streamed_event(self, event_data: Dict[str, Any]):
        """Handle events streamed from the browser in real-time."""
        try:
            self.event_counter += 1
            
            # Enrich event with capture metadata
            enriched_event = {
                "layer": "CAPTURE",
                "captureId": self.event_counter,
                "captureTimestamp": time.time(),
                "rawEvent": event_data
            }
            
            # Stream to backend triage immediately
            await self._stream_to_triage(enriched_event)
            
            logger.debug(f"📡 Streamed event {self.event_counter}: {event_data.get('type')} on {event_data.get('target', {}).get('tagName')}")
            
        except Exception as e:
            logger.error(f"Error handling streamed event: {e}", exc_info=True)
    
    async def _stream_to_triage(self, event_data: Dict[str, Any]):
        """Stream captured event to Layer 2 (Triage) via WebSocket."""
        try:
            message = {
                "type": "RAW_EVENT_STREAM",
                "data": event_data
            }
            
            await self.backend_websocket.send_json(message)
            
        except Exception as e:
            logger.error(f"Failed to stream event to triage: {e}")
            # Don't stop capture on WebSocket errors
    
    async def stop_capture(self):
        """Stop the event capture system."""
        self.capture_active = False
        
        # Clean up browser-side capture system
        await self.page.evaluate("""
            () => {
                if (window.auroraCapture) {
                    delete window.auroraCapture;
                    console.log('🛑 Aurora Agent Layer 1 CAPTURE system stopped');
                }
            }
        """)
        
        logger.info("🛑 Layer 1 CAPTURE system stopped")

class CaptureManager:
    """
    Manages multiple capture sessions and provides factory methods.
    """
    
    def __init__(self):
        self.active_captures: Dict[str, EventCapture] = {}
    
    async def create_capture_session(self, user_id: str, page: Page, websocket: WebSocket) -> EventCapture:
        """Create a new capture session for a user."""
        
        # Stop existing capture if any
        if user_id in self.active_captures:
            await self.active_captures[user_id].stop_capture()
        
        # Create new capture session
        capture = EventCapture(page, websocket)
        self.active_captures[user_id] = capture
        
        await capture.start_capture()
        
        logger.info(f"✅ Created Layer 1 CAPTURE session for user {user_id}")
        return capture
    
    async def stop_capture_session(self, user_id: str):
        """Stop capture session for a user."""
        if user_id in self.active_captures:
            await self.active_captures[user_id].stop_capture()
            del self.active_captures[user_id]
            logger.info(f"🛑 Stopped Layer 1 CAPTURE session for user {user_id}")

# Global capture manager instance
capture_manager = CaptureManager()
