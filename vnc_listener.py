#!/usr/bin/env python3
# File: session-bubble/jupyter-docker/vnc_listener.py
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
from typing import Dict, Any, Optional, List
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
        self.pages: List[Page] = []  # Track all open pages/tabs
        self.current_page_index: int = 0  # Track active page
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
                    '--start-maximized',
                    '--disable-popup-blocking',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-default-apps',
                    '--no-first-run',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows'
                ]
            )
            
            # Create the first page and track it
            self.page = await self.browser.new_page()
            self.pages = [self.page]  # Track all pages
            self.current_page_index = 0  # First page is active
            
            # Set viewport size to fill most of the VNC desktop (1024x768)
            await self.page.set_viewport_size({"width": 1200, "height": 800})
            
            self.is_initialized = True
            logger.info("Playwright browser initialized successfully with tab management")
            
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
    
    async def open_new_tab(self) -> str:
        """Open a new tab within the same browser window using JavaScript"""
        try:
            # Use JavaScript to open a new tab in the same browser window
            await self.page.evaluate("window.open('about:blank', '_blank')")
            
            # Wait a moment for the new tab to be created
            await asyncio.sleep(1)
            
            # Get all pages in the browser context
            context = self.page.context
            all_pages = context.pages
            
            # Find the new page (should be the last one)
            if len(all_pages) > len(self.pages):
                new_page = all_pages[-1]
                await new_page.set_viewport_size({"width": 1200, "height": 800})
                self.pages.append(new_page)
                self.current_page_index = len(self.pages) - 1
                self.page = new_page  # Switch to the new tab
                
                logger.info(f"Opened new tab {self.current_page_index + 1}. Total tabs: {len(self.pages)}")
                return f"Successfully opened new tab {self.current_page_index + 1}"
            else:
                return "Error: New tab was not created"
                
        except Exception as e:
            logger.error(f"Failed to open new tab: {e}")
            return f"Error opening new tab: {str(e)}"
    
    async def switch_to_tab(self, tab_index: int) -> str:
        """Switch to a specific tab by index (1-based)"""
        try:
            # Convert to 0-based index
            zero_based_index = tab_index - 1
            
            if zero_based_index < 0 or zero_based_index >= len(self.pages):
                return f"Error: Tab {tab_index} does not exist. Available tabs: 1-{len(self.pages)}"
            
            # Switch to the specified page
            self.current_page_index = zero_based_index
            self.page = self.pages[zero_based_index]
            await self.page.bring_to_front()
            
            logger.info(f"Switched to tab {tab_index}")
            return f"Successfully switched to tab {tab_index}"
        except Exception as e:
            logger.error(f"Failed to switch to tab {tab_index}: {e}")
            return f"Error switching to tab {tab_index}: {str(e)}"
    
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
            elif action == 'execute_jupyter_command':
                result = await self._execute_jupyter_command(message)
            elif action == 'jupyter_click_pyodide':
                result = await self._jupyter_click_pyodide(message)
            elif action == 'open_new_tab':
                result = await self.open_new_tab()
            elif action == 'switch_to_tab':
                tab_index = message.get('tab_index', 1)
                result = await self.switch_to_tab(tab_index)
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
        """Navigate to a URL using the current active page"""
        url = message.get('url')
        if not url:
            raise ValueError("URL is required for navigate action")
        
        # Use the current active page (supports multi-tab navigation)
        current_page = self.page
        if not current_page:
            raise ValueError("No active page available for navigation")
        
        # Navigate to the URL in the current active page
        await current_page.goto(url, wait_until='domcontentloaded')
        
        # Bring the page to front for visibility
        try:
            await self.page.bring_to_front()
        except Exception as e:
            logger.warning(f"Could not bring page to front: {e}")
        
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
    
    async def _execute_jupyter_command(self, message: Dict[str, Any]) -> str:
        """Execute individual Jupyter commands using the individual command executor"""
        # Support both direct parameters and nested parameters format
        tool_name = message.get('tool_name')
        parameters = message.get('parameters', {})
        
        # If tool_name is not at top level, check if it's in parameters
        if not tool_name and 'tool_name' in parameters:
            tool_name = parameters.get('tool_name')
            # Remove tool_name from parameters to avoid duplication
            parameters = {k: v for k, v in parameters.items() if k != 'tool_name'}
        
        # Support flattened parameter format (parameters directly in message)
        if not tool_name:
            # Check for common Jupyter parameter patterns
            if 'cell_index' in message or 'code' in message:
                # This looks like a flattened Jupyter command
                tool_name = message.get('action', '').replace('execute_jupyter_command', 'jupyter_type_in_cell')
                parameters = {k: v for k, v in message.items() 
                             if k not in ['action', 'timestamp']}
        
        if not tool_name:
            raise ValueError("tool_name is required for execute_jupyter_command action")
        
        # Import the individual command executor
        try:
            from aurora_agent.tools.jupyter.individual_command_executor import execute_jupyter_command
            result = await execute_jupyter_command(tool_name, parameters, self.page)
            return result
        except ImportError as e:
            raise ValueError(f"Could not import Jupyter command executor: {e}")
        except Exception as e:
            raise ValueError(f"Error executing Jupyter command {tool_name}: {e}")
    
    async def _jupyter_click_pyodide(self, message: Dict[str, Any]) -> str:
        """Click on the Python (Pyodide) kernel option"""
        logger.info("Clicking Python (Pyodide) kernel option")
        
        try:
            # Use the exact selector from the recorded script
            await self.page.get_by_title("Python (Pyodide)").first.click()
            return "Successfully clicked Python (Pyodide) kernel"
        except Exception as e:
            return f"Error clicking Python (Pyodide): {str(e)}"

# Global shared browser handler to prevent multiple browser instances
_global_browser_handler = None

async def get_global_browser_handler():
    """Get or create the global browser handler instance"""
    global _global_browser_handler
    if _global_browser_handler is None:
        _global_browser_handler = BrowserAutomationHandler()
        await _global_browser_handler.initialize()
    return _global_browser_handler

class VNCListener:
    """Main VNC listener class"""
    
    def __init__(self, port: int = 8765):
        self.port = port
        self.running = False
    
    async def start(self):
        """Start the VNC listener server"""
        # --- CHANGE HERE: Remove self.host from the log message ---
        logger.info(f"Starting VNC listener on 0.0.0.0:{self.port}")
        self.running = True
        
        try:
            # Initialize global browser handler (shared across all connections)
            await get_global_browser_handler()
            
            # This line is already correct from your previous fix
            async with websockets.serve(self.handle_client, '0.0.0.0', self.port):
                logger.info("VNC listener server started successfully on 0.0.0.0")
                await self.wait_for_shutdown()
                
        except Exception as e:
            logger.error(f"Failed to start VNC listener: {e}")
            logger.error(traceback.format_exc())
        finally:
            await self.cleanup()
    
    async def handle_client(self, websocket, path='/'):
        """Handle incoming WebSocket connections"""
        client_addr = websocket.remote_address
        # path is now provided as a parameter by websockets library
        logger.info(f"New client connected: {client_addr} on path: {path}")
        
        try:
            async for message in websocket:
                try:
                    # Parse JSON message
                    data = json.loads(message)
                    logger.info(f"Received message from {client_addr}: {data}")
                    
                    # Execute browser action using global browser handler
                    browser_handler = await get_global_browser_handler()
                    response = await browser_handler.execute_action(data)
                    
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
    # --- CHANGE HERE: Remove the '--host' argument ---
    # parser.add_argument('--host', default='localhost', help='Host to bind to (default: localhost)')
    parser.add_argument('--port', type=int, default=8765, help='Port to bind to (default: 8765)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Log level (default: INFO)')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # --- CHANGE HERE: Do not pass the host to the VNCListener constructor ---
    listener = VNCListener(args.port)
    
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
