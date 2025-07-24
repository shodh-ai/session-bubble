#!/usr/bin/env python3
"""
Playwright Browser Sensor
=========================

This script runs inside the Jupyter Docker container and continuously monitors
the browser's state using Playwright. When it detects user interactions or
state changes, it sends messages out over the VNC data channel to the Frontend.

The frontend's useBrowserInteractionSensor hook listens for these messages
and makes student_spoke_or_acted RPC calls back to the LiveKit Conductor.

Event Types Monitored:
- Click events
- Keyboard input (typing)
- Mouse hover
- Page navigation
- Element focus/blur
- Form submissions
- Scroll events
"""

import asyncio
import json
import logging
import sys
import websockets
import websockets.server
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Set
from playwright.async_api import async_playwright, Browser, Page, Playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/playwright_sensor.log')
    ]
)
logger = logging.getLogger('playwright_sensor')

class BrowserInteractionSensor:
    """Monitors browser interactions using Playwright"""
    
    def __init__(self, websocket_url: str = 'ws://localhost:8766'):
        self.websocket_url = websocket_url
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_monitoring = False
        self.last_interaction_time = 0
        self.interaction_throttle_ms = 100  # Throttle rapid events
        
        # Track monitored elements to avoid duplicate events
        self.monitored_elements: Set[str] = set()
    
    async def initialize(self):
        """Initialize Playwright and browser for monitoring"""
        try:
            logger.info("Initializing Playwright for browser monitoring...")
            self.playwright = await async_playwright().start()
            
            # Launch browser with monitoring capabilities
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # We want to see the browser in VNC
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--start-maximized'
                ]
            )
            
            # Create a new page for monitoring
            self.page = await self.browser.new_page()
            
            # Set viewport size
            await self.page.set_viewport_size({"width": 1280, "height": 720})
            
            # Set up event listeners
            await self._setup_event_listeners()
            
            logger.info("Browser monitoring initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser monitoring: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def _setup_event_listeners(self):
        """Set up event listeners for browser interactions"""
        if not self.page:
            return
        
        # Add JavaScript to monitor interactions
        await self.page.add_init_script("""
            // Track interactions and send to Python
            window.interactionSensor = {
                sendEvent: (eventData) => {
                    // This will be intercepted by our console message handler
                    console.log('INTERACTION_EVENT:', JSON.stringify(eventData));
                }
            };
            
            // Click events
            document.addEventListener('click', (e) => {
                const element = e.target;
                const rect = element.getBoundingClientRect();
                
                window.interactionSensor.sendEvent({
                    action: 'click',
                    selector: getElementSelector(element),
                    element: {
                        tagName: element.tagName,
                        id: element.id,
                        className: element.className,
                        textContent: element.textContent?.trim().substring(0, 100),
                        value: element.value
                    },
                    coordinates: {
                        x: e.clientX,
                        y: e.clientY
                    },
                    timestamp: Date.now()
                });
            });
            
            // Input events (typing)
            document.addEventListener('input', (e) => {
                const element = e.target;
                
                window.interactionSensor.sendEvent({
                    action: 'type',
                    selector: getElementSelector(element),
                    element: {
                        tagName: element.tagName,
                        id: element.id,
                        className: element.className,
                        value: element.value
                    },
                    timestamp: Date.now()
                });
            });
            
            // Keypress events
            document.addEventListener('keydown', (e) => {
                // Only report special keys and combinations
                if (e.key === 'Enter' || e.key === 'Tab' || e.key === 'Escape' || 
                    e.ctrlKey || e.altKey || e.metaKey) {
                    
                    window.interactionSensor.sendEvent({
                        action: 'keypress',
                        keyPressed: e.key,
                        modifiers: {
                            ctrl: e.ctrlKey,
                            alt: e.altKey,
                            shift: e.shiftKey,
                            meta: e.metaKey
                        },
                        timestamp: Date.now()
                    });
                }
            });
            
            // Hover events (throttled)
            let hoverTimeout;
            document.addEventListener('mouseover', (e) => {
                clearTimeout(hoverTimeout);
                hoverTimeout = setTimeout(() => {
                    const element = e.target;
                    
                    window.interactionSensor.sendEvent({
                        action: 'hover',
                        selector: getElementSelector(element),
                        element: {
                            tagName: element.tagName,
                            id: element.id,
                            className: element.className,
                            textContent: element.textContent?.trim().substring(0, 50)
                        },
                        coordinates: {
                            x: e.clientX,
                            y: e.clientY
                        },
                        timestamp: Date.now()
                    });
                }, 200); // Throttle hover events
            });
            
            // Focus events
            document.addEventListener('focus', (e) => {
                const element = e.target;
                
                window.interactionSensor.sendEvent({
                    action: 'focus',
                    selector: getElementSelector(element),
                    element: {
                        tagName: element.tagName,
                        id: element.id,
                        className: element.className,
                        value: element.value
                    },
                    timestamp: Date.now()
                });
            }, true);
            
            // Blur events
            document.addEventListener('blur', (e) => {
                const element = e.target;
                
                window.interactionSensor.sendEvent({
                    action: 'blur',
                    selector: getElementSelector(element),
                    element: {
                        tagName: element.tagName,
                        id: element.id,
                        className: element.className,
                        value: element.value
                    },
                    timestamp: Date.now()
                });
            }, true);
            
            // Form submission events
            document.addEventListener('submit', (e) => {
                const form = e.target;
                
                window.interactionSensor.sendEvent({
                    action: 'submit',
                    selector: getElementSelector(form),
                    element: {
                        tagName: form.tagName,
                        id: form.id,
                        className: form.className,
                        action: form.action,
                        method: form.method
                    },
                    timestamp: Date.now()
                });
            });
            
            // Scroll events (throttled)
            let scrollTimeout;
            document.addEventListener('scroll', (e) => {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(() => {
                    window.interactionSensor.sendEvent({
                        action: 'scroll',
                        coordinates: {
                            x: window.scrollX,
                            y: window.scrollY
                        },
                        timestamp: Date.now()
                    });
                }, 300); // Throttle scroll events
            });
            
            // Helper function to generate CSS selector for element
            function getElementSelector(element) {
                if (element.id) {
                    return '#' + element.id;
                }
                
                if (element.className && typeof element.className === 'string') {
                    const classes = element.className.trim().split(/\\s+/);
                    if (classes.length > 0 && classes[0]) {
                        return '.' + classes[0];
                    }
                }
                
                // Fallback to tag name with nth-child
                const parent = element.parentElement;
                if (parent) {
                    const siblings = Array.from(parent.children);
                    const index = siblings.indexOf(element) + 1;
                    return `${element.tagName.toLowerCase()}:nth-child(${index})`;
                }
                
                return element.tagName.toLowerCase();
            }
        """)
        
        # Listen for console messages to capture interaction events
        self.page.on('console', self._handle_console_message)
        
        # Listen for page navigation
        self.page.on('framenavigated', self._handle_navigation)
    
    async def _handle_console_message(self, msg):
        """Handle console messages from the browser"""
        try:
            message_text = msg.text
            if message_text.startswith('INTERACTION_EVENT:'):
                # Extract the JSON data
                json_data = message_text[len('INTERACTION_EVENT:'):].strip()
                event_data = json.loads(json_data)
                
                # Throttle rapid events
                current_time = datetime.now().timestamp() * 1000
                if current_time - self.last_interaction_time < self.interaction_throttle_ms:
                    return
                
                self.last_interaction_time = current_time
                
                # Send event to frontend
                await self._send_interaction_event(event_data)
                
        except Exception as e:
            logger.error(f"Error handling console message: {e}")
    
    async def _handle_navigation(self, frame):
        """Handle page navigation events"""
        try:
            if frame == self.page.main_frame:
                event_data = {
                    'action': 'navigate',
                    'url': frame.url,
                    'timestamp': datetime.now().timestamp() * 1000
                }
                
                await self._send_interaction_event(event_data)
                
        except Exception as e:
            logger.error(f"Error handling navigation: {e}")
    
    async def _send_interaction_event(self, event_data: Dict[str, Any]):
        """Send interaction event to frontend via WebSocket"""
        if not self.websocket or self.websocket.closed:
            logger.debug("No WebSocket connection available to send event")
            return
        
        try:
            message = json.dumps(event_data)
            await self.websocket.send(message)
            logger.debug(f"Sent interaction event: {event_data['action']}")
            
        except Exception as e:
            logger.error(f"Error sending interaction event: {e}")
    
    async def start_monitoring(self, target_url: str = 'about:blank'):
        """Start monitoring browser interactions"""
        if not self.page:
            await self.initialize()
        
        try:
            logger.info(f"Starting browser monitoring on: {target_url}")
            self.is_monitoring = True
            
            # Navigate to target URL
            if target_url != 'about:blank':
                await self.page.goto(target_url, wait_until='domcontentloaded')
            
            logger.info("Browser monitoring started successfully")
            
        except Exception as e:
            logger.error(f"Error starting browser monitoring: {e}")
            raise
    
    async def stop_monitoring(self):
        """Stop monitoring browser interactions"""
        self.is_monitoring = False
        logger.info("Browser monitoring stopped")
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser sensor cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

class SensorWebSocketServer:
    """WebSocket server for sending sensor events to frontend"""
    
    def __init__(self, host: str = 'localhost', port: int = 8766):
        self.host = host
        self.port = port
        self.sensor = BrowserInteractionSensor()
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
    
    async def start(self):
        """Start the sensor WebSocket server"""
        logger.info(f"Starting sensor WebSocket server on {self.host}:{self.port}")
        
        try:
            # Initialize browser sensor
            await self.sensor.initialize()
            
            # Start WebSocket server
            async with websockets.serve(self.handle_client, self.host, self.port):
                logger.info("Sensor WebSocket server started successfully")
                
                # Start monitoring
                await self.sensor.start_monitoring()
                
                # Keep server running
                await self.wait_for_shutdown()
                
        except Exception as e:
            logger.error(f"Failed to start sensor server: {e}")
            logger.error(traceback.format_exc())
        finally:
            await self.cleanup()
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle incoming WebSocket connections from frontend"""
        client_addr = websocket.remote_address
        logger.info(f"Frontend client connected: {client_addr}")
        
        self.clients.add(websocket)
        self.sensor.websocket = websocket  # Set current websocket for sensor
        
        try:
            # Handle incoming messages from frontend
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_frontend_command(data, websocket)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON from frontend {client_addr}: {e}")
                except Exception as e:
                    logger.error(f"Error handling frontend message: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Frontend client {client_addr} disconnected")
        except Exception as e:
            logger.error(f"Error with frontend client {client_addr}: {e}")
        finally:
            self.clients.discard(websocket)
            if self.sensor.websocket == websocket:
                self.sensor.websocket = None
    
    async def handle_frontend_command(self, data: Dict[str, Any], websocket):
        """Handle commands from frontend"""
        command = data.get('command')
        
        try:
            if command == 'start_monitoring':
                url = data.get('url', 'about:blank')
                logger.info(f"Frontend requested start monitoring: {url}")
                
                # Temporarily disable event sending to avoid duplicate navigation events
                old_websocket = self.sensor.websocket
                self.sensor.websocket = None
                
                await self.sensor.start_monitoring(url)
                
                # Re-enable event sending
                self.sensor.websocket = old_websocket
                
                # Send success response
                await websocket.send(json.dumps({
                    'success': True,
                    'message': f'Started monitoring {url}',
                    'url': url,
                    'timestamp': datetime.now().isoformat()
                }))
                logger.info(f"Successfully started monitoring {url}")
            
            elif command == 'stop_monitoring':
                logger.info("Frontend requested stop monitoring")
                await self.sensor.stop_monitoring()
                await websocket.send(json.dumps({
                    'success': True,
                    'message': 'Stopped monitoring',
                    'timestamp': datetime.now().isoformat()
                }))
                logger.info("Successfully stopped monitoring")
            
            elif command == 'navigate':
                url = data.get('url')
                if url and self.sensor.page:
                    logger.info(f"Frontend requested navigation to: {url}")
                    await self.sensor.page.goto(url, wait_until='domcontentloaded')
                    await websocket.send(json.dumps({
                        'success': True,
                        'message': f'Navigated to {url}',
                        'url': url,
                        'timestamp': datetime.now().isoformat()
                    }))
                    logger.info(f"Successfully navigated to {url}")
                else:
                    await websocket.send(json.dumps({
                        'success': False,
                        'error': 'No URL provided or page not available',
                        'timestamp': datetime.now().isoformat()
                    }))
            
            else:
                await websocket.send(json.dumps({
                    'success': False,
                    'error': f'Unknown command: {command}',
                    'timestamp': datetime.now().isoformat()
                }))
                
        except Exception as e:
            logger.error(f"Error handling frontend command {command}: {e}")
            await websocket.send(json.dumps({
                'success': False,
                'error': str(e),
                'command': command,
                'timestamp': datetime.now().isoformat()
            }))
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
    
    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up sensor server...")
        await self.sensor.cleanup()
        logger.info("Sensor server cleanup completed")

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Playwright Browser Interaction Sensor')
    parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--port', type=int, default=8766, help='Port to bind to (default: 8766)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Log level (default: INFO)')
    parser.add_argument('--target-url', default='about:blank', help='Initial URL to monitor (default: about:blank)')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create and start sensor server
    server = SensorWebSocketServer(args.host, args.port)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Sensor server stopped by user")
    except Exception as e:
        logger.error(f"Sensor server failed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
