#!/usr/bin/env python3
"""
Simple test script to upload company-sales.csv to Jupyter.
This tests just the upload functionality.
"""

import asyncio
import os
import sys
import logging
from aurora_agent.browser_manager import browser_manager
from aurora_agent.tools.jupyter.upload_tool import upload_file_to_jupyter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_simple_upload():
    """
    Simple test to upload the CSV file to Jupyter
    """
    logger.info("=== Testing Simple Jupyter Upload ===")
    
    # Set display for X11
    os.environ['DISPLAY'] = ':99'
    
    try:
        # Step 1: Initialize browser and navigate to Jupyter
        logger.info("Step 1: Starting browser and navigating to Jupyter...")
        await browser_manager.start_browser(headless=False)
        
        # Navigate to Jupyter (assuming it's running on localhost:8888)
        await browser_manager.navigate_to("http://localhost:8888")
        
        # Wait for Jupyter to load
        await asyncio.sleep(5)
        
        # Step 2: Upload the CSV file
        logger.info("Step 2: Uploading company-sales.csv...")
        csv_file_path = "/app/company-sales.csv"  # Path inside Docker container
        
        upload_result = await upload_file_to_jupyter(csv_file_path)
        logger.info(f"Upload result: {upload_result}")
        
        # Wait for upload to complete and verify
        await asyncio.sleep(3)
        
        # Take a screenshot to verify upload
        await browser_manager.page.screenshot(path="/app/jupyter_upload_test.png")
        logger.info("Screenshot saved: jupyter_upload_test.png")
        
        logger.info("✓ Simple upload test completed!")
        
    except Exception as e:
        logger.error(f"Error during upload test: {e}", exc_info=True)
        return False
    
    finally:
        # Keep browser open for manual inspection
        logger.info("Browser will stay open for 20 seconds for inspection...")
        await asyncio.sleep(20)
        
        # Close browser
        await browser_manager.close_browser()
    
    return True

if __name__ == "__main__":
    asyncio.run(test_simple_upload())
