#!/usr/bin/env python3
"""
Local test script to test Jupyter upload functionality with company-sales.csv
This runs locally without Docker dependencies.
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aurora_agent.browser_manager import browser_manager
from aurora_agent.tools.jupyter.upload_tool import upload_file_to_jupyter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_local_jupyter_upload():
    """
    Test Jupyter upload functionality locally
    """
    logger.info("=== Testing Local Jupyter Upload ===")
    
    try:
        # Step 1: Check if CSV file exists
        csv_file_path = "/Users/drsudhanshu/Desktop/bidirectionalflow/session-bubble/company-sales.csv"
        if not os.path.exists(csv_file_path):
            logger.error(f"CSV file not found at: {csv_file_path}")
            return False
        
        logger.info(f"✓ Found CSV file: {csv_file_path}")
        
        # Step 2: Initialize browser (non-headless for testing)
        logger.info("Step 2: Starting browser...")
        await browser_manager.start_browser(headless=False)
        
        # Step 3: Navigate to Jupyter Try Lab online
        jupyter_url = "https://jupyter.org/try-jupyter/lab/"
        logger.info(f"Step 3: Navigating to Jupyter Try Lab at {jupyter_url}")
        
        try:
            await browser_manager.navigate(jupyter_url, headless=False)
            logger.info("✓ Successfully navigated to Jupyter Try Lab")
        except Exception as e:
            logger.warning(f"Could not navigate to Jupyter Try Lab: {e}")
            return False
        
        # Wait for Jupyter Try Lab to load (online takes longer)
        await asyncio.sleep(8)
        
        # Step 4: Test the upload functionality
        logger.info("Step 4: Testing file upload...")
        
        upload_result = await upload_file_to_jupyter(csv_file_path)
        logger.info(f"Upload result: {upload_result}")
        
        # Wait for upload to complete
        await asyncio.sleep(3)
        
        # Step 5: Take a screenshot for verification
        screenshot_path = "/Users/drsudhanshu/Desktop/bidirectionalflow/session-bubble/jupyter_test_screenshot.png"
        await browser_manager.page.screenshot(path=screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")
        
        # Step 6: Try to create a simple notebook to work with the data
        logger.info("Step 6: Creating new notebook for data analysis...")
        
        try:
            # Look for "New" button or similar
            new_button = browser_manager.page.locator('button:has-text("New")')
            if await new_button.count() > 0:
                await new_button.click()
                await asyncio.sleep(1)
                
                # Look for Python notebook option
                python_option = browser_manager.page.locator('a:has-text("Python")')
                if await python_option.count() > 0:
                    await python_option.click()
                    logger.info("✓ Created new Python notebook")
                    await asyncio.sleep(2)
                    
                    # Add some basic data analysis code
                    basic_code = '''import pandas as pd
import matplotlib.pyplot as plt

# Load the uploaded CSV file
df = pd.read_csv('company-sales.csv')

# Display basic info
print("Company Sales Data Analysis")
print("=" * 30)
print(f"Dataset shape: {df.shape}")
print("\\nFirst 5 rows:")
print(df.head())

# Basic statistics
print("\\nBasic Statistics:")
print(df.describe())'''
                    
                    # Find code cell and input the code
                    code_cell = browser_manager.page.locator('.CodeMirror-code').first
                    if await code_cell.count() > 0:
                        await code_cell.click()
                        await browser_manager.page.keyboard.type(basic_code)
                        logger.info("✓ Added data analysis code to notebook")
                        
                        # Execute the cell
                        await browser_manager.page.keyboard.press('Shift+Enter')
                        logger.info("✓ Executed data analysis code")
                        
                        await asyncio.sleep(3)
                        
                        # Take final screenshot
                        final_screenshot = "/Users/drsudhanshu/Desktop/bidirectionalflow/session-bubble/jupyter_analysis_screenshot.png"
                        await browser_manager.page.screenshot(path=final_screenshot)
                        logger.info(f"Final screenshot saved: {final_screenshot}")
        
        except Exception as e:
            logger.warning(f"Could not create notebook: {e}")
        
        logger.info("✓ Local Jupyter test completed successfully!")
        
        # Keep browser open for manual inspection
        logger.info("Browser will stay open for 30 seconds for inspection...")
        await asyncio.sleep(30)
        
        return True
        
    except Exception as e:
        logger.error(f"Error during local Jupyter test: {e}", exc_info=True)
        return False
    
    finally:
        # Close browser
        try:
            await browser_manager.close_browser()
        except:
            pass
    
    return False

async def main():
    print("Starting local Jupyter upload test...")
    print("Make sure Jupyter is running with: jupyter lab --port=8888")
    print("Press Ctrl+C to cancel, or wait 5 seconds to continue...")
    
    try:
        await asyncio.sleep(5)
        result = await test_local_jupyter_upload()
        if result:
            print("✓ Test completed successfully!")
        else:
            print("✗ Test failed!")
    except KeyboardInterrupt:
        print("Test cancelled by user.")
    except Exception as e:
        print(f"Test error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
