# in /session-bubble/sanity_check_2.py
import asyncio
import os
import json
import time
import traceback
from dotenv import load_dotenv

import sys
sys.path.insert(0, '.')

# FIX: Import the necessary functions and modules
from aurora_agent.browser_manager import browser_manager
from aurora_agent.agent_brains.experts.sheets_expert_agent import perform_visual_ui_action
from aurora_agent.tools.sheets import get_sheets_tool_instance
from aurora_agent.setup_auth import main as run_auth_setup

async def main():
    """A simple, visual test to verify the entire UI pipeline works."""
    print("--- RUNNING UI SANITY CHECK ---")
    
    load_dotenv()
    test_spreadsheet_id = os.getenv("TEST_SPREADSHEET_ID")
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{test_spreadsheet_id}/edit"
    auth_file_path = 'aurora_agent/auth.json'

    if not os.path.exists(auth_file_path):
        print("\nWARNING: auth.json not found. Running auth setup...")
        await run_auth_setup()
        # Verify creation
        if not os.path.exists(auth_file_path):
            print("ERROR: auth.json could not be created. Exiting.")
            return

    sheets_tool = get_sheets_tool_instance()
    
    try:
        # --- SETUP ---
        print("SETUP: Starting browser (it should be visible)...")
        await browser_manager.start_browser(headless=False)
        
        # Use a new context with our saved authentication state
        context = await browser_manager.browser_instance.new_context(storage_state=auth_file_path)
        page = await context.new_page()
        
        # IMPORTANT: Make the created page accessible to the tool via the singleton
        browser_manager.page = page

        print(f"SETUP: Navigating to test sheet...")
        await page.goto(spreadsheet_url, wait_until="domcontentloaded", timeout=60000)

        print("SETUP: Preparing the sheet using the API tool...")
        await sheets_tool.write_cell("TestSheet!A1", "Hello, World!")
        # FIX: We don't have a remove_bold_format, so we just write the cell again
        # to ensure it's in a known, un-bolded state.
        await sheets_tool.write_cell("TestSheet!A1", "Hello, World!") 
        print("✅ SETUP: Complete.")

        # --- REASONING & ACTION ---
        prompt = "Select cell A1 and click the 'Bold' button in the toolbar."
        print(f"\nREASONING & ACTION: Calling the real 'perform_visual_ui_action' with prompt: '{prompt}'")
        
        result_json = await perform_visual_ui_action(prompt=prompt)
        result = json.loads(result_json)

        print(f"ACTION: Execution result: {result}")
        assert result["success"], f"Action execution failed: {result.get('error')}"
        print("✅ ACTION: Tool executed successfully.")

        print("\nPausing for 5 seconds for visual confirmation...")
        time.sleep(5)

        # --- VERIFICATION ---
        print("\nVERIFICATION: Using API to check if cell A1 is now bold...")
        format_json = await sheets_tool.get_cell_format("TestSheet!A1")
        is_bold = '"bold": true' in format_json
        assert is_bold is True, f"Verification failed: Cell is not bold! Format was: {format_json}"
        print("✅ VERIFICATION: Cell A1 is confirmed to be bold.")

        print("\n\n--- UI SANITY CHECK: SUCCESS ---")

    except Exception as e:
        print(f"\n--- UI SANITY CHECK: FAILED ---")
        traceback.print_exc()
    finally:
        print("Cleaning up: Closing browser...")
        if browser_manager.browser_instance:
            await browser_manager.close_browser()

if __name__ == "__main__":
    asyncio.run(main())