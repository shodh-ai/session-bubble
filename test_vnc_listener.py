#!/usr/bin/env python3
"""
Test Script for VNC Listener
============================

This script tests the vnc_listener.py without requiring LiveKit.
It connects to the VNC listener via WebSocket and sends mock browser automation commands.

Usage:
1. Start the VNC listener: python jupyter-docker/vnc_listener.py
2. Run this test: python test_vnc_listener.py
"""

import asyncio
import json
import websockets
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('vnc_test')

class VNCListenerTester:
    """Test client for VNC Listener"""
    
    def __init__(self, vnc_url: str = 'ws://localhost:8765'):
        self.vnc_url = vnc_url
        self.websocket = None
    
    async def connect(self):
        """Connect to VNC listener"""
        try:
            logger.info(f"Connecting to VNC listener at {self.vnc_url}")
            self.websocket = await websockets.connect(self.vnc_url)
            logger.info("Connected to VNC listener successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to VNC listener: {e}")
            return False
    
    async def send_command(self, command: dict):
        """Send a command to VNC listener"""
        if not self.websocket:
            logger.error("Not connected to VNC listener")
            return None
        
        try:
            message = json.dumps(command)
            logger.info(f"Sending command: {command['action']}")
            await self.websocket.send(message)
            
            # Wait for response
            response = await self.websocket.recv()
            response_data = json.loads(response)
            logger.info(f"Received response: {response_data}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return None
    
    async def run_test_suite(self):
        """Run a comprehensive test suite"""
        if not await self.connect():
            return
        
        test_commands = [
            # Test navigation
            {
                "action": "navigate",
                "url": "https://example.com",
                "timestamp": datetime.now().timestamp() * 1000
            },
            
            # Test waiting
            {
                "action": "wait",
                "waitTime": 2000,
                "timestamp": datetime.now().timestamp() * 1000
            },
            
            # Test clicking by selector (if element exists)
            {
                "action": "click",
                "selector": "h1",
                "timestamp": datetime.now().timestamp() * 1000
            },
            
            # Test typing (if input exists)
            {
                "action": "type",
                "selector": "input",
                "text": "Hello World Test",
                "timestamp": datetime.now().timestamp() * 1000
            },
            
            # Test scrolling
            {
                "action": "scroll",
                "x": 0,
                "y": 100,
                "timestamp": datetime.now().timestamp() * 1000
            },
            
            # Test screenshot
            {
                "action": "screenshot",
                "timestamp": datetime.now().timestamp() * 1000
            },
            
            # Test getting element info
            {
                "action": "get_element",
                "selector": "h1",
                "timestamp": datetime.now().timestamp() * 1000
            },
            
            # Test JavaScript execution
            {
                "action": "execute_script",
                "text": "document.title",
                "timestamp": datetime.now().timestamp() * 1000
            }
        ]
        
        logger.info("Starting VNC Listener test suite...")
        
        for i, command in enumerate(test_commands, 1):
            logger.info(f"\n--- Test {i}/{len(test_commands)}: {command['action']} ---")
            
            response = await self.send_command(command)
            
            if response:
                if response.get('success'):
                    logger.info(f"✅ Test {i} PASSED: {command['action']}")
                else:
                    logger.error(f"❌ Test {i} FAILED: {response.get('error', 'Unknown error')}")
            else:
                logger.error(f"❌ Test {i} FAILED: No response received")
            
            # Wait between tests
            await asyncio.sleep(1)
        
        logger.info("\n🎯 VNC Listener test suite completed!")
        await self.websocket.close()

async def test_individual_command():
    """Test a single command interactively"""
    tester = VNCListenerTester()
    
    if not await tester.connect():
        return
    
    # Example: Navigate to a test page
    command = {
        "action": "navigate",
        "url": "https://httpbin.org/forms/post",  # Good test page with forms
        "timestamp": datetime.now().timestamp() * 1000
    }
    
    response = await tester.send_command(command)
    print(f"Navigation response: {response}")
    
    # Wait a bit for page to load
    await asyncio.sleep(3)
    
    # Try to interact with the form
    fill_command = {
        "action": "type",
        "selector": "input[name='custname']",
        "text": "Test User",
        "timestamp": datetime.now().timestamp() * 1000
    }
    
    response = await tester.send_command(fill_command)
    print(f"Fill response: {response}")
    
    await tester.websocket.close()

async def main():
    """Main test function"""
    print("VNC Listener Test Options:")
    print("1. Run full test suite")
    print("2. Test individual command")
    print("3. Interactive mode")
    
    choice = input("Choose option (1-3): ").strip()
    
    if choice == "1":
        tester = VNCListenerTester()
        await tester.run_test_suite()
    
    elif choice == "2":
        await test_individual_command()
    
    elif choice == "3":
        await interactive_mode()
    
    else:
        print("Invalid choice")

async def interactive_mode():
    """Interactive testing mode"""
    tester = VNCListenerTester()
    
    if not await tester.connect():
        return
    
    print("\n🎮 Interactive VNC Listener Test Mode")
    print("Available actions: navigate, click, type, scroll, hover, keypress, wait, screenshot, get_element, execute_script")
    print("Type 'quit' to exit")
    
    while True:
        try:
            action = input("\nEnter action: ").strip().lower()
            
            if action == 'quit':
                break
            
            command = {"action": action, "timestamp": datetime.now().timestamp() * 1000}
            
            if action == "navigate":
                url = input("Enter URL: ").strip()
                command["url"] = url
            
            elif action in ["click", "type", "hover", "get_element"]:
                selector = input("Enter CSS selector: ").strip()
                command["selector"] = selector
                
                if action == "type":
                    text = input("Enter text to type: ").strip()
                    command["text"] = text
            
            elif action == "scroll":
                x = int(input("Enter X offset (default 0): ").strip() or "0")
                y = int(input("Enter Y offset (default 100): ").strip() or "100")
                command["x"] = x
                command["y"] = y
            
            elif action == "keypress":
                key = input("Enter key to press: ").strip()
                command["key"] = key
            
            elif action == "wait":
                wait_time = int(input("Enter wait time in ms (default 1000): ").strip() or "1000")
                command["waitTime"] = wait_time
            
            elif action == "execute_script":
                script = input("Enter JavaScript code: ").strip()
                command["text"] = script
            
            response = await tester.send_command(command)
            
            if response:
                if response.get('success'):
                    print(f"✅ Success: {response.get('result', 'Command executed')}")
                else:
                    print(f"❌ Error: {response.get('error', 'Unknown error')}")
            else:
                print("❌ No response received")
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
    
    await tester.websocket.close()
    print("👋 Goodbye!")

if __name__ == "__main__":
    print("🧪 VNC Listener Test Script")
    print("Make sure vnc_listener.py is running on localhost:8765")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
