#!/usr/bin/env python3
"""
Quick Test Script
================

This script quickly tests if the WebSocket servers start correctly.
"""

import asyncio
import websockets
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('quick_test')

async def test_vnc_connection():
    """Test VNC Listener connection"""
    try:
        logger.info("Testing VNC Listener connection...")
        websocket = await websockets.connect('ws://localhost:8765')
        logger.info("✅ VNC Listener connection successful")
        
        # Send a simple test command
        test_command = {
            "action": "wait",
            "waitTime": 1000,
            "timestamp": 1234567890
        }
        
        await websocket.send(json.dumps(test_command))
        logger.info("📤 Sent test command")
        
        response = await websocket.recv()
        response_data = json.loads(response)
        logger.info(f"📥 Received response: {response_data}")
        
        await websocket.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ VNC Listener test failed: {e}")
        return False

async def test_sensor_connection():
    """Test Playwright Sensor connection"""
    try:
        logger.info("Testing Playwright Sensor connection...")
        websocket = await websockets.connect('ws://localhost:8766')
        logger.info("✅ Playwright Sensor connection successful")
        
        # Send a simple test command
        test_command = {
            "command": "start_monitoring",
            "url": "about:blank"
        }
        
        await websocket.send(json.dumps(test_command))
        logger.info("📤 Sent test command")
        
        response = await websocket.recv()
        response_data = json.loads(response)
        logger.info(f"📥 Received response: {response_data}")
        
        await websocket.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Playwright Sensor test failed: {e}")
        return False

async def main():
    """Run quick tests"""
    print("🧪 Quick WebSocket Server Test")
    print("=" * 40)
    
    print("\n1. Testing VNC Listener (port 8765)...")
    vnc_result = await test_vnc_connection()
    
    print("\n2. Testing Playwright Sensor (port 8766)...")
    sensor_result = await test_sensor_connection()
    
    print("\n📊 Test Results:")
    print(f"   VNC Listener: {'✅ PASS' if vnc_result else '❌ FAIL'}")
    print(f"   Playwright Sensor: {'✅ PASS' if sensor_result else '❌ FAIL'}")
    
    if vnc_result and sensor_result:
        print("\n🎉 All tests passed! The servers are working correctly.")
    else:
        print("\n⚠️  Some tests failed. Make sure both servers are running:")
        print("   Terminal 1: python jupyter-docker/vnc_listener.py")
        print("   Terminal 2: python jupyter-docker/playwright_sensor.py")

if __name__ == "__main__":
    asyncio.run(main())
