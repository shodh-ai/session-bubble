#!/usr/bin/env python3
# File: session-bubble/test_playwright_sensor.py
"""
Test Script for Playwright Sensor
=================================

This script tests the playwright_sensor.py without requiring LiveKit.
It acts as a mock frontend, connecting to the sensor via WebSocket and receiving browser interaction events.

Usage:
1. Start the Playwright sensor: python jupyter-docker/playwright_sensor.py
2. Run this test: python test_playwright_sensor.py
"""

import asyncio
import json
import websockets
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('sensor_test')

class PlaywrightSensorTester:
    """Test client for Playwright Sensor"""
    
    def __init__(self, sensor_url: str = 'ws://localhost:8766'):
        self.sensor_url = sensor_url
        self.websocket = None
        self.events_received = []
    
    async def connect(self):
        """Connect to Playwright sensor"""
        try:
            logger.info(f"Connecting to Playwright sensor at {self.sensor_url}")
            self.websocket = await websockets.connect(self.sensor_url)
            logger.info("Connected to Playwright sensor successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Playwright sensor: {e}")
            return False
    
    async def send_command(self, command: dict):
        """Send a command to Playwright sensor"""
        if not self.websocket:
            logger.error("Not connected to Playwright sensor")
            return None
        
        try:
            message = json.dumps(command)
            logger.info(f"Sending command: {command}")
            await self.websocket.send(message)
            
            # Wait for response
            response = await self.websocket.recv()
            response_data = json.loads(response)
            logger.info(f"Received response: {response_data}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return None
    
    async def listen_for_events(self, duration_seconds: int = 30):
        """Listen for browser interaction events"""
        if not self.websocket:
            logger.error("Not connected to Playwright sensor")
            return
        
        logger.info(f"🎧 Listening for browser events for {duration_seconds} seconds...")
        logger.info("👆 Interact with the browser to generate events!")
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            while (asyncio.get_event_loop().time() - start_time) < duration_seconds:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    event_data = json.loads(message)
                    
                    # Store and display event
                    self.events_received.append(event_data)
                    self._display_event(event_data)
                    
                except asyncio.TimeoutError:
                    # No message received, continue listening
                    continue
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                except Exception as e:
                    logger.error(f"Error receiving event: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Error during event listening: {e}")
        
        logger.info(f"📊 Listening completed. Received {len(self.events_received)} events.")
    
    def _display_event(self, event_data: dict):
        """Display a received event in a nice format"""
        action = event_data.get('action', 'unknown')
        timestamp = event_data.get('timestamp', 0)
        
        # Format timestamp
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000)
            time_str = dt.strftime('%H:%M:%S.%f')[:-3]
        else:
            time_str = 'unknown'
        
        print(f"\n🎯 [{time_str}] {action.upper()}")
        
        # Display specific details based on action type
        if action == 'click':
            selector = event_data.get('selector', 'unknown')
            coords = event_data.get('coordinates', {})
            element = event_data.get('element', {})
            print(f"   📍 Selector: {selector}")
            print(f"   🎯 Coordinates: ({coords.get('x', '?')}, {coords.get('y', '?')})")
            print(f"   🏷️  Element: {element.get('tagName', '?')} {element.get('textContent', '')[:50]}")
        
        elif action == 'type':
            selector = event_data.get('selector', 'unknown')
            element = event_data.get('element', {})
            value = element.get('value', '')
            print(f"   📍 Selector: {selector}")
            print(f"   ⌨️  Value: {value[:100]}")
        
        elif action == 'hover':
            selector = event_data.get('selector', 'unknown')
            coords = event_data.get('coordinates', {})
            print(f"   📍 Selector: {selector}")
            print(f"   🎯 Coordinates: ({coords.get('x', '?')}, {coords.get('y', '?')})")
        
        elif action == 'navigate':
            url = event_data.get('url', 'unknown')
            print(f"   🌐 URL: {url}")
        
        elif action == 'keypress':
            key = event_data.get('keyPressed', 'unknown')
            modifiers = event_data.get('modifiers', {})
            mod_str = ', '.join([k for k, v in modifiers.items() if v])
            print(f"   ⌨️  Key: {key}")
            if mod_str:
                print(f"   🔧 Modifiers: {mod_str}")
        
        elif action == 'scroll':
            coords = event_data.get('coordinates', {})
            print(f"   📜 Position: ({coords.get('x', '?')}, {coords.get('y', '?')})")
        
        elif action in ['focus', 'blur']:
            selector = event_data.get('selector', 'unknown')
            element = event_data.get('element', {})
            print(f"   📍 Selector: {selector}")
            print(f"   🏷️  Element: {element.get('tagName', '?')}")
    
    async def run_monitoring_test(self):
        """Run a test that monitors browser interactions"""
        if not await self.connect():
            return
        
        # Start monitoring
        start_command = {
            "command": "start_monitoring",
            "url": "https://httpbin.org/forms/post"  # Good test page
        }
        
        response = await self.send_command(start_command)
        if not response or not response.get('success'):
            logger.error("Failed to start monitoring")
            return
        
        logger.info("✅ Monitoring started successfully")
        logger.info("🌐 Browser should have navigated to the test page")
        
        # Listen for events
        await self.listen_for_events(duration_seconds=60)
        
        # Stop monitoring
        stop_command = {"command": "stop_monitoring"}
        await self.send_command(stop_command)
        
        await self.websocket.close()
        
        # Display summary
        self._display_summary()
    
    def _display_summary(self):
        """Display a summary of received events"""
        if not self.events_received:
            print("\n📊 No events received")
            return
        
        print(f"\n📊 Event Summary ({len(self.events_received)} total events)")
        print("=" * 50)
        
        # Count events by type
        event_counts = {}
        for event in self.events_received:
            action = event.get('action', 'unknown')
            event_counts[action] = event_counts.get(action, 0) + 1
        
        for action, count in sorted(event_counts.items()):
            print(f"   {action}: {count}")
        
        print("\n🎯 Recent Events:")
        for event in self.events_received[-5:]:  # Show last 5 events
            action = event.get('action', 'unknown')
            timestamp = event.get('timestamp', 0)
            if timestamp:
                dt = datetime.fromtimestamp(timestamp / 1000)
                time_str = dt.strftime('%H:%M:%S')
            else:
                time_str = 'unknown'
            print(f"   [{time_str}] {action}")

async def test_sensor_commands():
    """Test sensor control commands"""
    tester = PlaywrightSensorTester()
    
    if not await tester.connect():
        return
    
    print("🧪 Testing sensor control commands...")
    
    # Test start monitoring
    print("\n1. Testing start monitoring...")
    response = await tester.send_command({
        "command": "start_monitoring",
        "url": "https://example.com"
    })
    print(f"Start monitoring response: {response}")
    
    await asyncio.sleep(2)
    
    # Test navigation
    print("\n2. Testing navigation...")
    response = await tester.send_command({
        "command": "navigate",
        "url": "https://httpbin.org/forms/post"
    })
    print(f"Navigation response: {response}")
    
    await asyncio.sleep(3)
    
    # Test stop monitoring
    print("\n3. Testing stop monitoring...")
    response = await tester.send_command({
        "command": "stop_monitoring"
    })
    print(f"Stop monitoring response: {response}")
    
    await tester.websocket.close()

async def interactive_event_listener():
    """Interactive mode to listen for events"""
    tester = PlaywrightSensorTester()
    
    if not await tester.connect():
        return
    
    print("\n🎮 Interactive Event Listener Mode")
    
    # Ask user for test URL
    test_url = input("Enter URL to monitor (default: https://httpbin.org/forms/post): ").strip()
    if not test_url:
        test_url = "https://httpbin.org/forms/post"
    
    # Start monitoring
    response = await tester.send_command({
        "command": "start_monitoring",
        "url": test_url
    })
    
    if not response or not response.get('success'):
        print("❌ Failed to start monitoring")
        return
    
    print(f"✅ Started monitoring: {test_url}")
    print("👆 Interact with the browser window to generate events")
    print("Press Ctrl+C to stop listening")
    
    try:
        await tester.listen_for_events(duration_seconds=300)  # 5 minutes
    except KeyboardInterrupt:
        print("\n⏹️  Stopping event listener...")
    
    # Stop monitoring
    await tester.send_command({"command": "stop_monitoring"})
    await tester.websocket.close()
    
    tester._display_summary()

async def main():
    """Main test function"""
    print("Playwright Sensor Test Options:")
    print("1. Run monitoring test (automated)")
    print("2. Test sensor commands")
    print("3. Interactive event listener")
    
    choice = input("Choose option (1-3): ").strip()
    
    if choice == "1":
        tester = PlaywrightSensorTester()
        await tester.run_monitoring_test()
    
    elif choice == "2":
        await test_sensor_commands()
    
    elif choice == "3":
        await interactive_event_listener()
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    print("🧪 Playwright Sensor Test Script")
    print("Make sure playwright_sensor.py is running on localhost:8766")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
