#!/usr/bin/env python3
"""
Simple test script to verify browser launches and is visible in VNC.
This can be run inside the Docker container to test the setup.
"""

import asyncio
import os
import sys
import logging
import subprocess
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_x11_setup():
    """Test if X11 is properly configured"""
    logger.info("Testing X11 setup...")
    
    display = os.environ.get('DISPLAY', ':99')
    logger.info(f"Using DISPLAY: {display}")
    
    try:
        # Test if X server is running
        result = subprocess.run(['xdpyinfo', '-display', display], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info("✓ X server is running and accessible")
            return True
        else:
            logger.error(f"✗ X server test failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"✗ X server test error: {e}")
        return False

def test_window_manager():
    """Test if window manager is running"""
    logger.info("Testing window manager...")
    
    try:
        # Check if openbox is running
        result = subprocess.run(['pgrep', 'openbox'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info("✓ Window manager (openbox) is running")
            return True
        else:
            logger.info("! Window manager not found, but browser might still work")
            return True  # Not critical
    except Exception as e:
        logger.warning(f"Window manager test error: {e}")
        return True  # Not critical

async def test_browser_launch():
    """Test launching browser with Playwright"""
    logger.info("Testing browser launch...")
    
    try:
        from aurora_agent.browser_manager import browser_manager
        
        # Start browser in non-headless mode
        logger.info("Starting browser in non-headless mode...")
        await browser_manager.start_browser(headless=False)
        
        # Navigate to a simple page
        logger.info("Navigating to example.com...")
        page = await browser_manager.navigate("https://example.com", headless=False)
        
        # Wait a bit for the page to load and be visible
        await asyncio.sleep(5)
        
        # Take a screenshot to verify it's working
        logger.info("Taking screenshot...")
        screenshot = await page.screenshot()
        logger.info(f"Screenshot taken, size: {len(screenshot)} bytes")
        
        logger.info("✓ Browser launched successfully and should be visible in VNC!")
        
        # Keep browser open for manual testing
        logger.info("Browser will stay open for 30 seconds for VNC testing...")
        await asyncio.sleep(30)
        
        # Clean up
        await browser_manager.close_browser()
        logger.info("Browser closed.")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Browser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    logger.info("=== VNC Browser Test ===")
    
    # Test X11 setup
    if not test_x11_setup():
        logger.error("X11 setup failed, cannot continue")
        return False
    
    # Test window manager
    test_window_manager()
    
    # Test browser launch
    success = await test_browser_launch()
    
    if success:
        logger.info("=== All tests passed! Browser should be visible in VNC ===")
    else:
        logger.error("=== Tests failed ===")
    
    return success

if __name__ == "__main__":
    # Ensure DISPLAY is set
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":99"
        logger.info("Set DISPLAY to :99")
    
    # Run the test
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
