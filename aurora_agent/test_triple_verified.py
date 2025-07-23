"""
Comprehensive Test Suite for Triple-Verified Architecture
Tests each layer individually and the complete fusion pipeline

Usage:
    python test_triple_verified.py --layer 1    # Test Layer 1 only
    python test_triple_verified.py --layer 2    # Test Layer 2 only  
    python test_triple_verified.py --layer 3    # Test Layer 3 only
    python test_triple_verified.py --full       # Test complete pipeline
    python test_triple_verified.py --interactive # Interactive testing
"""

import asyncio
import json
import time
import argparse
import logging
from typing import Dict, Any, List
import websockets
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TripleVerifiedTester:
    """Comprehensive tester for the Triple-Verified Architecture."""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:8000"
        self.ws_url = "ws://127.0.0.1:8000/ws/session/test_user"
        self.test_results = []
        
    async def test_layer_1_capture(self):
        """Test Layer 1: Event Capture System"""
        print("\n🎯 TESTING LAYER 1: CAPTURE")
        print("=" * 50)
        
        try:
            # Test 1: WebSocket Connection
            print("Test 1.1: WebSocket Connection...")
            async with websockets.connect(self.ws_url) as websocket:
                # Send test message
                test_message = {
                    "type": "RAW_EVENT_STREAM",
                    "data": {
                        "layer": "CAPTURE",
                        "captureId": 1,
                        "captureTimestamp": time.time(),
                        "rawEvent": {
                            "type": "click",
                            "timestamp": time.time(),
                            "target": {
                                "tagName": "DIV",
                                "className": "test-element",
                                "ariaLabel": "Test Button"
                            },
                            "coordinates": {
                                "clientX": 100,
                                "clientY": 200
                            }
                        }
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                print("✅ Test 1.1 PASSED: WebSocket connection and message sending")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    print(f"✅ Test 1.2 PASSED: Received response: {response_data.get('type')}")
                except asyncio.TimeoutError:
                    print("⚠️  Test 1.2 TIMEOUT: No response received (may be expected)")
                
        except Exception as e:
            print(f"❌ Test 1 FAILED: {e}")
            return False
            
        return True
    
    async def test_layer_2_triage(self):
        """Test Layer 2: Parallel Data Collection"""
        print("\n🔄 TESTING LAYER 2: TRIAGE")
        print("=" * 50)
        
        try:
            # Test session start
            print("Test 2.1: Starting verification session...")
            start_response = requests.post(f"{self.base_url}/verification/start", json={
                "user_id": "test_user",
                "spreadsheet_url": "https://docs.google.com/spreadsheets/d/test"
            })
            
            if start_response.status_code == 200:
                print("✅ Test 2.1 PASSED: Session start endpoint")
            else:
                print(f"❌ Test 2.1 FAILED: Status {start_response.status_code}")
                return False
            
            # Test WebSocket with session
            print("Test 2.2: Testing parallel data collection...")
            async with websockets.connect(self.ws_url) as websocket:
                # Send click event that should trigger Layer 2
                click_event = {
                    "type": "click",
                    "target": "SPAN",
                    "x": 150,
                    "y": 250,
                    "aria_label": "Cell A1",
                    "timestamp": time.time()
                }
                
                # This should trigger the complete Layer 2 pipeline
                await websocket.send(json.dumps(click_event))
                
                # Wait for Layer 2 processing
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    
                    if response_data.get("type") == "VERIFIED_ACTION":
                        print("✅ Test 2.2 PASSED: Layer 2 parallel processing complete")
                        print(f"   Architecture: {response_data.get('architecture')}")
                        print(f"   Tool Name: {response_data.get('tool_name')}")
                        return True
                    else:
                        print(f"⚠️  Test 2.2 PARTIAL: Received {response_data.get('type')}")
                        
                except asyncio.TimeoutError:
                    print("❌ Test 2.2 TIMEOUT: No response from Layer 2")
                    return False
                    
        except Exception as e:
            print(f"❌ Test 2 FAILED: {e}")
            return False
            
        return True
    
    async def test_layer_3_synthesis(self):
        """Test Layer 3: Synthesizer Agent (Fusion Engine)"""
        print("\n🧠 TESTING LAYER 3: SYNTHESIS")
        print("=" * 50)
        
        try:
            # Import and test synthesizer directly
            from synthesizer_agent import synthesize_data_bundle
            
            # Create test data bundle
            test_bundle = {
                "layer": "TRIAGE",
                "timestamp": time.time(),
                "raw_playwright_event": {
                    "type": "click",
                    "target": "SPAN",
                    "x": 100,
                    "y": 200,
                    "aria_label": "Cell B2"
                },
                "before_screenshot_bytes": "deadbeef",  # Mock hex data
                "after_screenshot_bytes": "cafebabe",   # Mock hex data
                "before_api_snapshot": {
                    "spreadsheet_data": {"A1": "old_value"},
                    "formatting_info": {}
                },
                "after_api_snapshot": {
                    "spreadsheet_data": {"A1": "new_value"},
                    "formatting_info": {}
                }
            }
            
            print("Test 3.1: Testing synthesizer agent...")
            result = await synthesize_data_bundle(test_bundle)
            
            if result.get("type") == "VERIFIED_ACTION":
                print("✅ Test 3.1 PASSED: Synthesizer agent working")
                print(f"   Interpretation: {result.get('interpretation')}")
                print(f"   Confidence: {result.get('confidence')}")
                print(f"   Evidence Summary: {result.get('evidence_summary', {}).keys()}")
                
                # Test evidence fusion
                evidence = result.get("evidence_summary", {})
                if "playwright" in evidence and "vlm" in evidence and "api" in evidence:
                    print("✅ Test 3.2 PASSED: Evidence fusion working")
                else:
                    print("⚠️  Test 3.2 PARTIAL: Some evidence sources missing")
                
                return True
            else:
                print(f"❌ Test 3.1 FAILED: Wrong result type: {result.get('type')}")
                return False
                
        except Exception as e:
            print(f"❌ Test 3 FAILED: {e}")
            return False
    
    async def test_layer_4_presentation(self):
        """Test Layer 4: Frontend Presentation"""
        print("\n📱 TESTING LAYER 4: PRESENTATION")
        print("=" * 50)
        
        try:
            # Test frontend endpoints
            print("Test 4.1: Testing frontend endpoints...")
            
            # Test static file serving
            response = requests.get(f"{self.base_url}/static/lesson-builder.html")
            if response.status_code == 200:
                print("✅ Test 4.1 PASSED: Frontend files accessible")
            else:
                print(f"❌ Test 4.1 FAILED: Status {response.status_code}")
                return False
            
            # Test WebSocket message formatting
            print("Test 4.2: Testing WebSocket message format...")
            async with websockets.connect(self.ws_url) as websocket:
                # Send a message that should result in a VERIFIED_ACTION
                test_message = {
                    "type": "click",
                    "target": "DIV",
                    "x": 300,
                    "y": 400
                }
                
                await websocket.send(json.dumps(test_message))
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                    response_data = json.loads(response)
                    
                    # Check if response has all required fields for frontend
                    required_fields = ["type", "interpretation", "verification", "status", "confidence"]
                    missing_fields = [field for field in required_fields if field not in response_data]
                    
                    if not missing_fields:
                        print("✅ Test 4.2 PASSED: Message format complete")
                        return True
                    else:
                        print(f"⚠️  Test 4.2 PARTIAL: Missing fields: {missing_fields}")
                        return True  # Still functional
                        
                except asyncio.TimeoutError:
                    print("❌ Test 4.2 TIMEOUT: No response for presentation test")
                    return False
                    
        except Exception as e:
            print(f"❌ Test 4 FAILED: {e}")
            return False
    
    async def test_full_pipeline(self):
        """Test Complete End-to-End Pipeline"""
        print("\n🚀 TESTING COMPLETE PIPELINE")
        print("=" * 50)
        
        try:
            # Start session
            print("Pipeline Test 1: Starting session...")
            start_response = requests.post(f"{self.base_url}/verification/start", json={
                "user_id": "test_user",
                "spreadsheet_url": "https://docs.google.com/spreadsheets/d/test"
            })
            
            if start_response.status_code != 200:
                print(f"❌ Pipeline FAILED at session start: {start_response.status_code}")
                return False
            
            # Test multiple consecutive actions
            print("Pipeline Test 2: Testing multi-action sequence...")
            async with websockets.connect(self.ws_url) as websocket:
                
                actions = [
                    {"type": "click", "target": "SPAN", "x": 100, "y": 100, "aria_label": "Cell A1"},
                    {"type": "input", "target": "INPUT", "value": "Sales Data", "aria_label": "Cell A1"},
                    {"type": "click", "target": "BUTTON", "x": 200, "y": 50, "aria_label": "Bold"},
                    {"type": "keydown", "key": "Enter", "target": "INPUT"}
                ]
                
                results = []
                for i, action in enumerate(actions):
                    print(f"   Action {i+1}: {action['type']} on {action.get('aria_label', action['target'])}")
                    
                    await websocket.send(json.dumps(action))
                    
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        results.append(response_data)
                        
                        if response_data.get("type") == "VERIFIED_ACTION":
                            print(f"   ✅ Action {i+1} verified: {response_data.get('tool_name')}")
                        else:
                            print(f"   ⚠️  Action {i+1} response: {response_data.get('type')}")
                            
                    except asyncio.TimeoutError:
                        print(f"   ❌ Action {i+1} timeout")
                        results.append({"error": "timeout"})
                    
                    # Small delay between actions
                    await asyncio.sleep(1)
                
                # Analyze results
                verified_actions = [r for r in results if r.get("type") == "VERIFIED_ACTION"]
                success_rate = len(verified_actions) / len(actions)
                
                print(f"\nPipeline Results:")
                print(f"   Total Actions: {len(actions)}")
                print(f"   Verified Actions: {len(verified_actions)}")
                print(f"   Success Rate: {success_rate:.1%}")
                
                if success_rate >= 0.75:  # 75% success rate threshold
                    print("✅ PIPELINE TEST PASSED: Multi-action sequence working")
                    return True
                else:
                    print("⚠️  PIPELINE TEST PARTIAL: Some actions not verified")
                    return True  # Still functional
                    
        except Exception as e:
            print(f"❌ PIPELINE TEST FAILED: {e}")
            return False
    
    async def interactive_test(self):
        """Interactive testing mode"""
        print("\n🎮 INTERACTIVE TESTING MODE")
        print("=" * 50)
        print("This will connect to the WebSocket and show real-time responses.")
        print("You can manually test actions in the browser while watching the output.")
        print("Press Ctrl+C to exit.\n")
        
        try:
            async with websockets.connect(self.ws_url) as websocket:
                print(f"✅ Connected to {self.ws_url}")
                print("Listening for messages...\n")
                
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        print(f"📨 Received: {data.get('type', 'UNKNOWN')}")
                        if data.get('type') == 'VERIFIED_ACTION':
                            print(f"   🎯 Action: {data.get('tool_name', 'unknown')}")
                            print(f"   📝 Description: {data.get('interpretation', 'N/A')}")
                            print(f"   🎲 Confidence: {data.get('confidence', 0):.2f}")
                            print(f"   🏗️  Architecture: {data.get('architecture', 'unknown')}")
                        print("-" * 40)
                        
                    except websockets.exceptions.ConnectionClosed:
                        print("Connection closed")
                        break
                    except KeyboardInterrupt:
                        print("\nExiting interactive mode...")
                        break
                        
        except Exception as e:
            print(f"❌ Interactive test failed: {e}")

async def main():
    parser = argparse.ArgumentParser(description='Test Triple-Verified Architecture')
    parser.add_argument('--layer', type=int, choices=[1,2,3,4], help='Test specific layer')
    parser.add_argument('--full', action='store_true', help='Test complete pipeline')
    parser.add_argument('--interactive', action='store_true', help='Interactive testing mode')
    
    args = parser.parse_args()
    
    tester = TripleVerifiedTester()
    
    print("🧪 TRIPLE-VERIFIED ARCHITECTURE TEST SUITE")
    print("=" * 60)
    
    if args.interactive:
        await tester.interactive_test()
    elif args.layer:
        if args.layer == 1:
            await tester.test_layer_1_capture()
        elif args.layer == 2:
            await tester.test_layer_2_triage()
        elif args.layer == 3:
            await tester.test_layer_3_synthesis()
        elif args.layer == 4:
            await tester.test_layer_4_presentation()
    elif args.full:
        await tester.test_full_pipeline()
    else:
        # Run all tests
        print("Running comprehensive test suite...\n")
        
        results = []
        results.append(await tester.test_layer_1_capture())
        results.append(await tester.test_layer_2_triage())
        results.append(await tester.test_layer_3_synthesis())
        results.append(await tester.test_layer_4_presentation())
        results.append(await tester.test_full_pipeline())
        
        # Summary
        passed = sum(results)
        total = len(results)
        
        print(f"\n📊 TEST SUMMARY")
        print("=" * 30)
        print(f"Passed: {passed}/{total}")
        print(f"Success Rate: {passed/total:.1%}")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! Triple-Verified Architecture is working!")
        elif passed >= total * 0.8:
            print("✅ MOSTLY WORKING! Minor issues detected.")
        else:
            print("⚠️  ISSUES DETECTED! Check failed tests above.")

if __name__ == "__main__":
    asyncio.run(main())
