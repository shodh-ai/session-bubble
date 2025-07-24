# Browser Automation Testing Guide (No LiveKit Required)

This guide explains how to test the complete browser automation system without requiring the full LiveKit service setup.

## 🎯 Overview

The browser automation system consists of 4 main components:
1. **VNC Listener** (Python) - Executes browser actions via Playwright
2. **Playwright Sensor** (Python) - Monitors browser interactions
3. **Browser Action Executor Hook** (TypeScript) - Frontend RPC handler
4. **Browser Interaction Sensor Hook** (TypeScript) - Frontend event listener

## 📋 Prerequisites

### Python Dependencies
```bash
# Install required Python packages
pip install playwright websockets asyncio

# Install Playwright browsers
playwright install chromium
```

### System Requirements
- Python 3.8+
- Node.js 16+ (for frontend testing)
- Chrome/Chromium browser
- WebSocket support

## 🧪 Testing Strategy

### Phase 1: Test Individual Python Components

#### 1.1 Test VNC Listener (Browser Action Executor)

**Terminal 1: Start VNC Listener**
```bash
cd /Users/drsudhanshu/Desktop/bidirectionalflow/session-bubble
python jupyter-docker/vnc_listener.py --host localhost --port 8765
```

**Terminal 2: Run VNC Listener Test**
```bash
python test_vnc_listener.py
```

**Expected Results:**
- ✅ WebSocket connection established
- ✅ Browser opens and navigates to test pages
- ✅ All browser actions execute successfully (click, type, scroll, etc.)
- ✅ Screenshots are captured
- ✅ Element information is retrieved

**Test Options:**
1. **Full Test Suite** - Automated test of all browser actions
2. **Individual Command** - Test specific actions with predefined scenarios
3. **Interactive Mode** - Manual testing with custom commands

#### 1.2 Test Playwright Sensor (Browser Interaction Monitor)

**Terminal 1: Start Playwright Sensor**
```bash
python jupyter-docker/playwright_sensor.py --host localhost --port 8766
```

**Terminal 2: Run Sensor Test**
```bash
python test_playwright_sensor.py
```

**Expected Results:**
- ✅ WebSocket connection established
- ✅ Browser opens and loads monitoring scripts
- ✅ User interactions are detected and reported
- ✅ Events are properly formatted and timestamped
- ✅ Event throttling works correctly

**Test Actions:**
- Click on various elements
- Type in input fields
- Hover over elements
- Navigate between pages
- Scroll the page
- Use keyboard shortcuts

### Phase 2: Test Frontend Hooks

#### 2.1 Test Browser Hooks with Mock LiveKit

**Open in Browser:**
```bash
# Navigate to the test page
open /Users/drsudhanshu/Desktop/bidirectionalflow/exsense/test_browser_hooks.html
```

**Test Scenarios:**

1. **Browser Action Executor Test:**
   - Connect to VNC Listener (ws://localhost:8765)
   - Send various browser commands
   - Simulate RPC calls from mock LiveKit
   - Verify commands are translated to VNC messages

2. **Browser Interaction Sensor Test:**
   - Connect to Playwright Sensor (ws://localhost:8766)
   - Start listening for events
   - Simulate browser interactions
   - Verify events trigger mock RPC calls

**Expected Results:**
- ✅ WebSocket connections established
- ✅ Mock RPC handlers registered
- ✅ Commands sent and responses received
- ✅ Events captured and processed
- ✅ UI updates reflect connection status

### Phase 3: End-to-End Integration Test

#### 3.1 Full System Test

**Setup (4 terminals):**

**Terminal 1: VNC Listener**
```bash
python jupyter-docker/vnc_listener.py
```

**Terminal 2: Playwright Sensor**
```bash
python jupyter-docker/playwright_sensor.py
```

**Terminal 3: VNC Listener Test**
```bash
python test_vnc_listener.py
# Choose option 3 (Interactive mode)
```

**Terminal 4: Sensor Test**
```bash
python test_playwright_sensor.py
# Choose option 3 (Interactive event listener)
```

**Browser: Frontend Test**
```
Open test_browser_hooks.html
Connect both executor and sensor
```

#### 3.2 Integration Test Flow

1. **Start all components**
2. **Send navigation command** via frontend → VNC Listener
3. **Interact with the browser** manually
4. **Verify events** are captured by Playwright Sensor
5. **Check logs** in all terminals for proper message flow

## 🔧 Troubleshooting

### Common Issues

#### WebSocket Connection Failures
```bash
# Check if ports are available
netstat -an | grep 8765
netstat -an | grep 8766

# Kill processes using the ports if needed
lsof -ti:8765 | xargs kill -9
lsof -ti:8766 | xargs kill -9
```

#### Playwright Browser Issues
```bash
# Reinstall Playwright browsers
playwright install --force chromium

# Check Playwright installation
playwright --version
```

#### JavaScript Console Errors
- Open browser DevTools (F12)
- Check Console tab for WebSocket errors
- Verify correct WebSocket URLs

### Debug Mode

**Enable verbose logging:**
```bash
# Python components
python vnc_listener.py --log-level DEBUG
python playwright_sensor.py --log-level DEBUG

# Test scripts
python test_vnc_listener.py  # Already has detailed logging
```

## 📊 Test Validation Checklist

### VNC Listener Tests
- [ ] WebSocket server starts successfully
- [ ] Browser launches and is visible
- [ ] Navigation commands work
- [ ] Click commands execute on correct elements
- [ ] Type commands fill form fields
- [ ] Scroll commands move the page
- [ ] Screenshot commands create image files
- [ ] Element info retrieval returns correct data
- [ ] Error handling works for invalid commands

### Playwright Sensor Tests
- [ ] WebSocket server starts successfully
- [ ] Browser monitoring initializes
- [ ] Click events are detected
- [ ] Type events capture input values
- [ ] Hover events track mouse movement
- [ ] Navigation events capture URL changes
- [ ] Keyboard events detect special keys
- [ ] Event throttling prevents spam
- [ ] Events are properly formatted JSON

### Frontend Hook Tests
- [ ] Mock LiveKit room initializes
- [ ] RPC methods register successfully
- [ ] WebSocket connections establish
- [ ] Commands translate correctly to VNC format
- [ ] Events trigger mock RPC calls
- [ ] UI status updates reflect connection state
- [ ] Error states are handled gracefully
- [ ] Logs provide useful debugging information

### Integration Tests
- [ ] All components start without conflicts
- [ ] Commands flow: Frontend → VNC Listener → Browser
- [ ] Events flow: Browser → Sensor → Frontend → Mock RPC
- [ ] Multiple simultaneous connections work
- [ ] System handles disconnections gracefully
- [ ] Performance is acceptable under load

## 🚀 Next Steps

After successful testing:

1. **Docker Integration**: Test within actual Docker container
2. **LiveKit Integration**: Replace mocks with real LiveKit connections
3. **Production Deployment**: Configure for production environment
4. **Performance Optimization**: Optimize for scale and reliability

## 📝 Test Results Template

```markdown
## Test Results - [Date]

### Environment
- OS: [macOS/Linux/Windows]
- Python Version: [3.x.x]
- Playwright Version: [x.x.x]
- Browser: [Chromium x.x.x]

### VNC Listener Tests
- Connection: [✅/❌]
- Navigation: [✅/❌]
- Clicking: [✅/❌]
- Typing: [✅/❌]
- Screenshots: [✅/❌]
- Error Handling: [✅/❌]

### Playwright Sensor Tests
- Connection: [✅/❌]
- Event Detection: [✅/❌]
- Event Formatting: [✅/❌]
- Throttling: [✅/❌]
- WebSocket Communication: [✅/❌]

### Frontend Hook Tests
- Mock LiveKit: [✅/❌]
- RPC Registration: [✅/❌]
- WebSocket Connections: [✅/❌]
- Command Translation: [✅/❌]
- Event Processing: [✅/❌]

### Integration Tests
- End-to-End Flow: [✅/❌]
- Multiple Components: [✅/❌]
- Error Recovery: [✅/❌]
- Performance: [✅/❌]

### Issues Found
[List any issues encountered]

### Notes
[Additional observations]
```

## 🎯 Success Criteria

The system is ready for LiveKit integration when:
- All individual component tests pass
- End-to-end message flow works correctly
- Error handling is robust
- Performance meets requirements
- No memory leaks or resource issues
- Logs provide clear debugging information
