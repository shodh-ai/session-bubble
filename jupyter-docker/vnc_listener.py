#!/usr/bin/env python3
"""
VNC Listener for Browser Automation
===================================

This script runs inside the Jupyter Docker container and listens for incoming
messages on the VNC data channel. It receives JSON messages from the Frontend
Mediator and executes browser actions using Playwright.

Message Format:
{
    "action": "click|type|navigate|scroll|hover|keypress|wait|screenshot|get_element|execute_script",
    "selector": "#element-id or .class-name",
    "text": "text to type",
    "url": "https://example.com",
    "x": 100,
    "y": 200,
    "key": "Enter",
    "waitTime": 1000,
    "timestamp": 1234567890
}
"""

import asyncio
import json
import logging
import sys
import websockets
import websockets.server
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, Playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/vnc_listener.log')
    ]
)
logger = logging.getLogger('vnc_listener')

class BrowserAutomationHandler:
    """Handles browser automation using Playwright"""
    
    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.is_initialized = False
    
    async def initialize(self):
        """Initialize Playwright and browser"""
        try:
            logger.info("Initializing Playwright browser...")
            self.playwright = await async_playwright().start()
            
            # Launch browser with options suitable for Docker/VNC environment
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
            
            # Create a new page
            self.page = await self.browser.new_page()
            
            # Set viewport size
            await self.page.set_viewport_size({"width": 1280, "height": 720})
            
            self.is_initialized = True
            logger.info("Playwright browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def cleanup(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Browser cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def execute_action(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a browser action based on the message"""
        if not self.is_initialized:
            await self.initialize()
        
        action = message.get('action', '').lower()
        logger.info(f"Executing action: {action} with params: {message}")
        
        try:
            result = None
            
            if action == 'navigate':
                result = await self._navigate(message)
            elif action == 'click':
                result = await self._click(message)
            elif action == 'type':
                result = await self._type(message)
            elif action == 'scroll':
                result = await self._scroll(message)
            elif action == 'hover':
                result = await self._hover(message)
            elif action == 'keypress':
                result = await self._keypress(message)
            elif action == 'wait':
                result = await self._wait(message)
            elif action == 'screenshot':
                result = await self._screenshot(message)
            elif action == 'get_element':
                result = await self._get_element(message)
            elif action == 'execute_script':
                result = await self._execute_script(message)
            else:
                raise ValueError(f"Unknown action: {action}")
            
            return {
                'success': True,
                'action': action,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'action': action,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _navigate(self, message: Dict[str, Any]) -> str:
        """Navigate to a URL"""
        url = message.get('url')
        if not url:
            raise ValueError("URL is required for navigate action")
        
        await self.page.goto(url, wait_until='domcontentloaded')
        return f"Navigated to {url}"
    
    async def _click(self, message: Dict[str, Any]) -> str:
        """Click on an element"""
        selector = message.get('selector')
        x = message.get('x')
        y = message.get('y')
        
        if selector:
            # Click by selector
            await self.page.wait_for_selector(selector, timeout=5000)
            await self.page.click(selector)
            return f"Clicked element: {selector}"
        elif x is not None and y is not None:
            # Click by coordinates
            await self.page.mouse.click(x, y)
            return f"Clicked at coordinates: ({x}, {y})"
        else:
            raise ValueError("Either selector or coordinates (x, y) are required for click action")
    
    async def _type(self, message: Dict[str, Any]) -> str:
        """Type text into an element"""
        selector = message.get('selector')
        text = message.get('text', '')
        
        if not selector:
            raise ValueError("Selector is required for type action")
        
        await self.page.wait_for_selector(selector, timeout=5000)
        await self.page.fill(selector, text)
        return f"Typed '{text}' into {selector}"
    
    async def _scroll(self, message: Dict[str, Any]) -> str:
        """Scroll the page or an element"""
        x = message.get('x', 0)
        y = message.get('y', 0)
        selector = message.get('selector')
        
        if selector:
            # Scroll specific element
            await self.page.wait_for_selector(selector, timeout=5000)
            await self.page.evaluate(f"""
                document.querySelector('{selector}').scrollBy({x}, {y})
            """)
            return f"Scrolled element {selector} by ({x}, {y})"
        else:
            # Scroll page
            await self.page.evaluate(f"window.scrollBy({x}, {y})")
            return f"Scrolled page by ({x}, {y})"
    
    async def _hover(self, message: Dict[str, Any]) -> str:
        """Hover over an element"""
        selector = message.get('selector')
        if not selector:
            raise ValueError("Selector is required for hover action")
        
        await self.page.wait_for_selector(selector, timeout=5000)
        await self.page.hover(selector)
        return f"Hovered over element: {selector}"
    
    async def _keypress(self, message: Dict[str, Any]) -> str:
        """Press a key"""
        key = message.get('key')
        if not key:
            raise ValueError("Key is required for keypress action")
        
        await self.page.keyboard.press(key)
        return f"Pressed key: {key}"
    
    async def _wait(self, message: Dict[str, Any]) -> str:
        """Wait for a specified time or element"""
        wait_time = message.get('waitTime', 1000)
        selector = message.get('selector')
        
        if selector:
            # Wait for element
            await self.page.wait_for_selector(selector, timeout=wait_time)
            return f"Waited for element: {selector}"
        else:
            # Wait for time
            await asyncio.sleep(wait_time / 1000)  # Convert ms to seconds
            return f"Waited for {wait_time}ms"
    
    async def _screenshot(self, message: Dict[str, Any]) -> str:
        """Take a screenshot"""
        selector = message.get('selector')
        
        if selector:
            # Screenshot of specific element
            element = await self.page.wait_for_selector(selector, timeout=5000)
            screenshot_bytes = await element.screenshot()
        else:
            # Full page screenshot
            screenshot_bytes = await self.page.screenshot(full_page=True)
        
        # Save screenshot to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/tmp/screenshot_{timestamp}.png"
        
        with open(filename, 'wb') as f:
            f.write(screenshot_bytes)
        
        return f"Screenshot saved to {filename}"
    
    async def _get_element(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Get element information"""
        selector = message.get('selector')
        if not selector:
            raise ValueError("Selector is required for get_element action")
        
        await self.page.wait_for_selector(selector, timeout=5000)
        
        # Get element properties
        element_info = await self.page.evaluate(f"""
            (() => {{
                const element = document.querySelector('{selector}');
                if (!element) return null;
                
                const rect = element.getBoundingClientRect();
                return {{
                    tagName: element.tagName,
                    id: element.id,
                    className: element.className,
                    textContent: element.textContent?.trim(),
                    value: element.value,
                    href: element.href,
                    src: element.src,
                    bounds: {{
                        x: rect.x,
                        y: rect.y,
                        width: rect.width,
                        height: rect.height
                    }}
                }};
            }})()
        """)
        
        return element_info or {}
    
    async def _execute_script(self, message: Dict[str, Any]) -> Any:
        """Execute JavaScript code"""
        script = message.get('text')  # Using 'text' field for script content
        if not script:
            raise ValueError("Script content is required for execute_script action")
        
        result = await self.page.evaluate(script)
        return result

class VNCListener:
    """Main VNC listener class"""
    
    def __init__(self, host: str = 'localhost', port: int = 8765):
        self.host = host
        self.port = port
        self.browser_handler = BrowserAutomationHandler()
        self.running = False
    
    async def start(self):
        """Start the VNC listener server"""
        logger.info(f"Starting VNC listener on {self.host}:{self.port}")
        self.running = True
        
        try:
            # Initialize browser
            await self.browser_handler.initialize()
            
            # Start WebSocket server
            async with websockets.serve(self.handle_client, self.host, self.port):
                logger.info("VNC listener server started successfully")
                await self.wait_for_shutdown()
                
        except Exception as e:
            logger.error(f"Failed to start VNC listener: {e}")
            logger.error(traceback.format_exc())
        finally:
            await self.cleanup()
    
    async def handle_client(self, websocket: websockets.server.WebSocketServerProtocol, path: str):
        """Handle incoming WebSocket connections"""
        client_addr = websocket.remote_address
        logger.info(f"New client connected: {client_addr}")
        
        try:
            async for message in websocket:
                try:
                    # Parse JSON message
                    data = json.loads(message)
                    logger.info(f"Received message from {client_addr}: {data}")
                    
                    # Execute browser action
                    response = await self.browser_handler.execute_action(data)
                    
                    # Send response back
                    await websocket.send(json.dumps(response))
                    logger.info(f"Sent response to {client_addr}: {response}")
                    
                except json.JSONDecodeError as e:
                    error_response = {
                        'success': False,
                        'error': f'Invalid JSON: {str(e)}',
                        'timestamp': datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(error_response))
                    logger.error(f"JSON decode error from {client_addr}: {e}")
                
                except Exception as e:
                    error_response = {
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                    await websocket.send(json.dumps(error_response))
                    logger.error(f"Error handling message from {client_addr}: {e}")
                    logger.error(traceback.format_exc())
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_addr} disconnected")
        except Exception as e:
            logger.error(f"Error with client {client_addr}: {e}")
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            self.running = False
    
    async def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up VNC listener...")
        await self.browser_handler.cleanup()
        logger.info("VNC listener cleanup completed")

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='VNC Listener for Browser Automation')
    parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--port', type=int, default=8765, help='Port to bind to (default: 8765)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Log level (default: INFO)')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create and start listener
    listener = VNCListener(args.host, args.port)
    
    try:
        await listener.start()
    except KeyboardInterrupt:
        logger.info("VNC listener stopped by user")
    except Exception as e:
        logger.error(f"VNC listener failed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
