#!/usr/bin/env python3
"""
Test script to launch a browser with Jupyter and display it in the VNC session.
This script will open a browser in non-headless mode so it's visible through VNC.
"""

import asyncio
import os
import sys
import logging
from aurora_agent.browser_manager import browser_manager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_jupyter_browser():
    """
    Test function that:
    1. Starts a browser in non-headless mode (visible in X session)
    2. Navigates to Jupyter (assuming it's running on localhost:8888)
    3. Performs some basic interactions
    """
    try:
        logger.info("Starting browser in non-headless mode for VNC visibility...")
        
        # Start browser in non-headless mode so it appears in the X session
        await browser_manager.start_browser(headless=False)
        
        # Navigate to a test page first
        logger.info("Navigating to Google to test browser visibility...")
        page = await browser_manager.navigate("https://www.google.com", headless=False)
        
        # Wait a bit to see the page
        await asyncio.sleep(3)
        
        # Try to navigate to local Jupyter (if running)
        logger.info("Attempting to navigate to local Jupyter...")
        try:
            await page.goto("http://localhost:8888", wait_until="domcontentloaded", timeout=10000)
            logger.info("Successfully connected to Jupyter!")
        except Exception as e:
            logger.warning(f"Could not connect to Jupyter: {e}")
            logger.info("Staying on Google page for testing...")
        
        # Perform some basic interactions to test
        logger.info("Performing test interactions...")
        
        # If we're on Google, search for something
        try:
            search_box = await page.wait_for_selector('textarea[name="q"]', timeout=5000)
            await search_box.fill("VNC browser test")
            await search_box.press("Enter")
            await asyncio.sleep(2)
            logger.info("Successfully performed search interaction!")
        except Exception as e:
            logger.info(f"Search interaction failed (expected if not on Google): {e}")
        
        # Keep the browser open for testing
        logger.info("Browser is now running and should be visible in VNC!")
        logger.info("Press Ctrl+C to close the browser and exit.")
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, closing browser...")
            
    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        await browser_manager.close_browser()
        logger.info("Browser closed.")

if __name__ == "__main__":
    # Ensure we're using the correct display for X11
    if "DISPLAY" not in os.environ:
        os.environ["DISPLAY"] = ":99"
        logger.info("Set DISPLAY to :99 for X11")
    
    logger.info(f"Using DISPLAY: {os.environ.get('DISPLAY')}")
    logger.info("Starting Jupyter browser test...")
    
    # Run the test
    asyncio.run(test_jupyter_browser())