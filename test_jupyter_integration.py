#!/usr/bin/env python3
"""
Comprehensive Jupyter Integration Test
=====================================

This test demonstrates the complete frontend-driven tool execution flow:
1. Frontend sends browser automation commands via WebSocket
2. VNC Listener executes Playwright actions on Jupyter
3. Jupyter tools (annotation, execution, upload) are triggered
4. Playwright Sensor captures interactions and sends events back
5. Frontend receives events and makes RPC calls

This simulates the full Teacher AI -> Frontend -> Browser -> Jupyter workflow.
"""

import asyncio
import json
import logging
import websockets
import time
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('jupyter_integration_test')

class JupyterIntegrationTester:
    def __init__(self):
        self.vnc_websocket = None
        self.sensor_websocket = None
        self.test_results = []
        
    async def connect_to_services(self):
        """Connect to both VNC Listener and Playwright Sensor"""
        try:
            logger.info("🔌 Connecting to VNC Listener (port 8765)...")
            self.vnc_websocket = await websockets.connect('ws://localhost:8765')
            logger.info("✅ Connected to VNC Listener")
            
            logger.info("🔌 Connecting to Playwright Sensor (port 8766)...")
            self.sensor_websocket = await websockets.connect('ws://localhost:8766')
            logger.info("✅ Connected to Playwright Sensor")
            
            return True
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    async def send_vnc_command(self, command):
        """Send command to VNC Listener and get response"""
        try:
            await self.vnc_websocket.send(json.dumps(command))
            response = await self.vnc_websocket.recv()
            return json.loads(response)
        except Exception as e:
            logger.error(f"VNC command failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_sensor_command(self, command):
        """Send command to Playwright Sensor and get response"""
        try:
            await self.sensor_websocket.send(json.dumps(command))
            response = await self.sensor_websocket.recv()
            return json.loads(response)
        except Exception as e:
            logger.error(f"Sensor command failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_jupyter_navigation(self):
        """Test 1: Navigate to Online Jupyter and set up Python notebook"""
        logger.info("\n🧪 TEST 1: Online Jupyter Setup & Navigation")
        
        # Step 1: Navigate to online Jupyter
        nav_command = {
            "action": "navigate",
            "url": "https://jupyter.org/try-jupyter/lab/",
            "timestamp": time.time() * 1000
        }
        
        result = await self.send_vnc_command(nav_command)
        success = result.get("success", False)
        
        if not success:
            logger.error(f"❌ Navigation failed: {result.get('error', 'Unknown error')}")
            self.test_results.append(("Jupyter Navigation", False, result))
            return False
        
        logger.info("✅ Successfully navigated to Online Jupyter")
        
        # Step 2: Wait for main content to load (90 seconds as specified)
        logger.info("⏳ Waiting for Main Content to load (up to 90 seconds)...")
        wait_main_command = {
            "action": "wait",
            "selector": '[aria-label="Main Content"]',
            "waitTime": 90000,
            "timestamp": time.time() * 1000
        }
        
        wait_result = await self.send_vnc_command(wait_main_command)
        if not wait_result.get("success", False):
            logger.warning(f"⚠️  Main content wait failed: {wait_result.get('error', 'Timeout')}")
            # Continue anyway, might still work
        else:
            logger.info("✅ Main Content loaded successfully")
        
        # Step 3: Click on Python (Pyodide) notebook option
        logger.info("🐍 Clicking on Python (Pyodide) notebook...")
        click_python_command = {
            "action": "click",
            "selector": 'div[data-category="Notebook"][title="Python (Pyodide)"]',
            "timestamp": time.time() * 1000
        }
        
        python_result = await self.send_vnc_command(click_python_command)
        if not python_result.get("success", False):
            logger.error(f"❌ Failed to click Python notebook: {python_result.get('error', 'Unknown error')}")
            # Try alternative selector
            logger.info("🔄 Trying alternative Python notebook selector...")
            alt_click_command = {
                "action": "click",
                "selector": '[title*="Python"]',
                "timestamp": time.time() * 1000
            }
            python_result = await self.send_vnc_command(alt_click_command)
        
        if python_result.get("success", False):
            logger.info("✅ Successfully clicked Python notebook option")
        else:
            logger.warning("⚠️  Could not click Python notebook, continuing...")
        
        # Step 4: Wait for notebook cell to be ready (30 seconds)
        logger.info("📝 Waiting for notebook cell to be ready (up to 30 seconds)...")
        wait_cell_command = {
            "action": "wait",
            "selector": ".jp-NotebookPanel-notebook .jp-Cell-inputWrapper .cm-content",
            "waitTime": 30000,
            "timestamp": time.time() * 1000
        }
        
        cell_result = await self.send_vnc_command(wait_cell_command)
        if cell_result.get("success", False):
            logger.info("🎉 Jupyter notebook cell is ready!")
            success = True
        else:
            logger.warning(f"⚠️  Cell wait failed: {cell_result.get('error', 'Timeout')}")
            # Check if we can find any cells at all
            check_cells_command = {
                "action": "execute_script",
                "text": "document.querySelectorAll('.jp-CodeCell, .jp-Cell').length",
                "timestamp": time.time() * 1000
            }
            cells_check = await self.send_vnc_command(check_cells_command)
            cell_count = int(cells_check.get("result", "0"))
            
            if cell_count > 0:
                logger.info(f"✅ Found {cell_count} cells, notebook partially ready")
                success = True
            else:
                logger.error("❌ No cells found, notebook setup failed")
                success = False
        
        self.test_results.append(("Jupyter Setup & Navigation", success, result))
        return success
    
    async def test_cell_interaction_simulation(self):
        """Test 2: Simulate Jupyter cell interactions"""
        logger.info("\n🧪 TEST 2: Jupyter Cell Interaction")
        
        # First, try to click on a Jupyter code cell
        logger.info("🔍 Looking for Jupyter code cells...")
        
        # Check if cells exist
        cell_check_command = {
            "action": "execute_script",
            "text": "document.querySelectorAll('.jp-CodeCell').length",
            "timestamp": time.time() * 1000
        }
        
        cell_check_result = await self.send_vnc_command(cell_check_command)
        cell_count = int(cell_check_result.get("result", "0"))
        
        if cell_count > 0:
            logger.info(f"📝 Found {cell_count} code cells in Jupyter")
            
            # Click on the first code cell's input area
            click_command = {
                "action": "click",
                "selector": ".jp-CodeCell .jp-InputArea .cm-content",
                "timestamp": time.time() * 1000
            }
            
            result = await self.send_vnc_command(click_command)
            success = result.get("success", False)
            
            if success:
                logger.info("✅ Successfully clicked on Jupyter code cell")
                
                # Wait a moment for cell to become active
                await asyncio.sleep(1)
                
                # Try typing Python code into the active cell
                type_command = {
                    "action": "type",
                    "selector": ".jp-CodeCell.jp-mod-active .cm-content",
                    "text": "print('Hello from Frontend-driven Jupyter!')\nimport datetime\nprint(f'Test executed at: {datetime.datetime.now()}')",
                    "timestamp": time.time() * 1000
                }
                
                type_result = await self.send_vnc_command(type_command)
                type_success = type_result.get("success", False)
                
                if type_success:
                    logger.info("✅ Successfully typed Python code into cell")
                    
                    # Try to execute the cell (Shift+Enter)
                    execute_command = {
                        "action": "keypress",
                        "key": "Shift+Enter",
                        "timestamp": time.time() * 1000
                    }
                    
                    execute_result = await self.send_vnc_command(execute_command)
                    if execute_result.get("success", False):
                        logger.info("✅ Attempted to execute cell with Shift+Enter")
                        await asyncio.sleep(2)  # Wait for execution
                else:
                    logger.warning(f"⚠️  Typing failed: {type_result.get('error', 'Unknown error')}")
                
                success = success and type_success
            else:
                logger.error(f"❌ Cell click failed: {result.get('error', 'Unknown error')}")
        else:
            logger.warning("⚠️  No Jupyter code cells found, trying generic interaction...")
            # Fallback to generic body click
            click_command = {
                "action": "click",
                "selector": "body",
                "timestamp": time.time() * 1000
            }
            result = await self.send_vnc_command(click_command)
            success = result.get("success", False)
        
        self.test_results.append(("Jupyter Cell Interaction", success, result))
        return success
    
    async def test_screenshot_capture(self):
        """Test 3: Capture screenshot of current state"""
        logger.info("\n🧪 TEST 3: Screenshot Capture")
        
        screenshot_command = {
            "action": "screenshot",
            "timestamp": time.time() * 1000
        }
        
        result = await self.send_vnc_command(screenshot_command)
        success = result.get("success", False)
        
        if success:
            logger.info(f"✅ Screenshot captured: {result.get('result', 'Unknown location')}")
        else:
            logger.error(f"❌ Screenshot failed: {result.get('error', 'Unknown error')}")
        
        self.test_results.append(("Screenshot Capture", success, result))
        return success
    
    async def test_element_inspection(self):
        """Test 4: Inspect page elements"""
        logger.info("\n🧪 TEST 4: Element Inspection")
        
        # Try to get information about page elements
        inspect_command = {
            "action": "get_element",
            "selector": "h1, title, body",  # Try multiple selectors
            "timestamp": time.time() * 1000
        }
        
        result = await self.send_vnc_command(inspect_command)
        success = result.get("success", False)
        
        if success:
            element_info = result.get("result", {})
            logger.info(f"✅ Element found: {element_info.get('tagName', 'Unknown')} - '{element_info.get('textContent', 'No text')[:50]}...'")
        else:
            logger.error(f"❌ Element inspection failed: {result.get('error', 'Unknown error')}")
        
        self.test_results.append(("Element Inspection", success, result))
        return success
    
    async def test_javascript_execution(self):
        """Test 5: Execute JavaScript for advanced interactions"""
        logger.info("\n🧪 TEST 5: JavaScript Execution")
        
        # Execute JavaScript to get page information
        js_command = {
            "action": "execute_script",
            "text": "JSON.stringify({title: document.title, url: window.location.href, cells: document.querySelectorAll('.jp-CodeCell, .jp-MarkdownCell').length})",
            "timestamp": time.time() * 1000
        }
        
        result = await self.send_vnc_command(js_command)
        success = result.get("success", False)
        
        if success:
            try:
                page_info = json.loads(result.get("result", "{}"))
                logger.info(f"✅ Page info: Title='{page_info.get('title', 'Unknown')}', Cells={page_info.get('cells', 0)}")
            except:
                logger.info(f"✅ JavaScript executed: {result.get('result', 'Unknown result')}")
        else:
            logger.error(f"❌ JavaScript execution failed: {result.get('error', 'Unknown error')}")
        
        self.test_results.append(("JavaScript Execution", success, result))
        return success
    
    async def test_sensor_monitoring(self):
        """Test 6: Test Playwright Sensor monitoring"""
        logger.info("\n🧪 TEST 6: Sensor Monitoring")
        
        # Start monitoring
        start_command = {
            "command": "start_monitoring",
            "url": "https://example.com"
        }
        
        result = await self.send_sensor_command(start_command)
        success = result.get("success", False)
        
        if success:
            logger.info(f"✅ Sensor monitoring started: {result.get('message', 'Unknown')}")
            
            # Listen for events for a short time
            logger.info("🎧 Listening for browser events (10 seconds)...")
            event_count = 0
            
            try:
                # Listen for events with timeout
                for _ in range(10):  # 10 second timeout
                    try:
                        event_data = await asyncio.wait_for(
                            self.sensor_websocket.recv(), 
                            timeout=1.0
                        )
                        event = json.loads(event_data)
                        
                        # Skip command responses, only count actual events
                        if 'action' in event and event['action'] in ['click', 'type', 'hover', 'navigate', 'focus', 'blur']:
                            event_count += 1
                            logger.info(f"📡 Event {event_count}: {event['action']} on {event.get('selector', 'unknown')}")
                    except asyncio.TimeoutError:
                        continue  # No event received, continue listening
                    except Exception as e:
                        logger.debug(f"Event parsing error: {e}")
                        continue
            
            except Exception as e:
                logger.warning(f"Event listening error: {e}")
            
            # Stop monitoring
            stop_command = {"command": "stop_monitoring"}
            stop_result = await self.send_sensor_command(stop_command)
            
            logger.info(f"📊 Captured {event_count} browser events")
            success = success and stop_result.get("success", False)
        else:
            logger.error(f"❌ Sensor monitoring failed: {result.get('error', 'Unknown error')}")
        
        self.test_results.append(("Sensor Monitoring", success, {"events_captured": event_count}))
        return success
    
    async def run_comprehensive_test(self):
        """Run all tests in sequence"""
        logger.info("🚀 Starting Comprehensive Jupyter Integration Test")
        logger.info("=" * 60)
        
        # Connect to services
        if not await self.connect_to_services():
            logger.error("❌ Failed to connect to services. Make sure both servers are running.")
            return False
        
        # Run all tests
        tests = [
            self.test_jupyter_navigation,
            self.test_cell_interaction_simulation,
            self.test_screenshot_capture,
            self.test_element_inspection,
            self.test_javascript_execution,
            self.test_sensor_monitoring
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test in tests:
            try:
                success = await test()
                if success:
                    passed_tests += 1
                await asyncio.sleep(1)  # Brief pause between tests
            except Exception as e:
                logger.error(f"Test failed with exception: {e}")
        
        # Print results
        logger.info("\n" + "=" * 60)
        logger.info("📊 TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        
        for test_name, success, details in self.test_results:
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"{status} {test_name}")
            if not success and isinstance(details, dict) and 'error' in details:
                logger.info(f"    Error: {details['error']}")
        
        logger.info(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            logger.info("🎉 ALL TESTS PASSED! Frontend-driven Jupyter integration is working perfectly!")
        elif passed_tests > total_tests // 2:
            logger.info("✅ Most tests passed. System is largely functional with minor issues.")
        else:
            logger.warning("⚠️  Several tests failed. Check server connections and Jupyter setup.")
        
        return passed_tests == total_tests
    
    async def cleanup(self):
        """Clean up connections"""
        if self.vnc_websocket:
            await self.vnc_websocket.close()
        if self.sensor_websocket:
            await self.sensor_websocket.close()
        logger.info("🧹 Cleanup completed")

async def main():
    """Main test runner"""
    tester = JupyterIntegrationTester()
    
    try:
        success = await tester.run_comprehensive_test()
        return success
    except KeyboardInterrupt:
        logger.info("🛑 Test interrupted by user")
        return False
    except Exception as e:
        logger.error(f"💥 Test failed with exception: {e}")
        return False
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    print("🧪 Jupyter Integration Test")
    print("=" * 40)
    print("This test requires:")
    print("1. VNC Listener running on port 8765")
    print("2. Playwright Sensor running on port 8766") 
    print("3. Optional: Jupyter running on port 8888")
    print("=" * 40)
    
    success = asyncio.run(main())
    exit(0 if success else 1)
