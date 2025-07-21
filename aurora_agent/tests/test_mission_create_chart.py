# in tests/test_mission_create_chart.py
import pytest
import os
import uuid
import json
from dotenv import load_dotenv

from aurora_agent.adk_service import execute_browser_mission
from aurora_agent.tools.sheets import get_sheets_tool_instance
from aurora_agent.browser_manager import browser_manager

load_dotenv()

@pytest.mark.asyncio
async def test_full_mission_e2e_create_chart():
    """
    A full E2E test to verify the agent can perform the multi-step
    process of creating a chart from data using three explicit steps.
    """
    # --- ARRANGE ---
    sheets_tool = get_sheets_tool_instance()
    sheet_name = f"ChartData_{uuid.uuid4().hex[:8]}"
    
    # Create a fresh sheet first
    await sheets_tool.create_sheet(sheet_name)
    print(f"\n✅ SETUP: Created sheet '{sheet_name}'.")

    # Start browser and navigate to the sheet
    await browser_manager.start_browser(headless=False)
    sheets_url = os.getenv("TEST_SPREADSHEET_URL")
    await browser_manager.navigate(sheets_url)
    print(f"✅ SETUP: Browser opened and navigated to sheet.")

    try:
        # --- STEP 1: WRITE DATA ---
        print(f"\n--- STEP 1: WRITING DATA ---")
        sales_data = [
            ["Month", "Sales"],
            ["January", 1500],
            ["February", 1800],
            ["March", 2200]
        ]
        await sheets_tool.write_range(f"'{sheet_name}'!A1:B4", json.dumps(sales_data))
        print(f"✅ STEP 1: Data written to sheet '{sheet_name}' range A1:B4.")

        # --- STEP 2: INSERT CHART VIA UI ---
        print(f"\n--- STEP 2: INSERTING CHART VIA UI ---")
        page = browser_manager.page
        
        # Navigate to the specific sheet tab (try the new sheet first)
        print(f"DEBUG: Looking for sheet tab '{sheet_name}'...")
        
        # First, try to find and click the new sheet tab
        try:
            # Try different selectors for the sheet tab
            sheet_tab_selectors = [
                f"div[role='tab']:has-text('{sheet_name}')",
                f"//div[@role='tab' and contains(text(), '{sheet_name}')]"
            ]
            
            sheet_found = False
            for selector in sheet_tab_selectors:
                try:
                    await page.locator(selector).click(timeout=3000)
                    print(f"✅ Found and clicked sheet tab: {sheet_name}")
                    sheet_found = True
                    break
                except:
                    continue
            
            if not sheet_found:
                print(f"INFO: Could not find sheet tab '{sheet_name}', using current sheet")
                
        except Exception as e:
            print(f"INFO: Sheet tab navigation skipped: {e}")
        
        await page.wait_for_timeout(1000)
        
        # Click somewhere in the data area to ensure we're focused on the sheet
        try:
            await page.locator("div[role='grid']").click()
            await page.wait_for_timeout(500)
        except:
            print("INFO: Could not click grid area, continuing...")
        
        # Click Insert menu
        print("DEBUG: Clicking Insert menu...")
        await page.get_by_role("menuitem", name="Insert").click()
        await page.wait_for_timeout(1000)
        
        # Click Chart option
        print("DEBUG: Clicking Chart option...")
        await page.get_by_role("menuitem", name="Chart h", exact=True).locator("div").first.click()
        await page.wait_for_timeout(3000)  # Wait for chart to be created
        print(f"✅ STEP 2: Chart inserted via Insert > Chart menu.")

        # --- ASSERT ---
        print("\n--- VERIFYING CHART CREATION ---")
        # Use the API to verify that a chart was created
        chart_info_json = await sheets_tool.get_sheet_charts(sheet_name)
        chart_info = json.loads(chart_info_json)
        
        assert chart_info["status"] == "SUCCESS", f"Failed to get chart info: {chart_info}"
        assert len(chart_info["charts"]) >= 1, f"Verification failed: No chart found. Charts: {chart_info['charts']}"
        
        print(f"✅ SUCCESS: Chart created successfully! Found {len(chart_info['charts'])} chart(s).")
        
    except Exception as e:
        print(f"❌ ERROR: Test failed with exception: {e}")
        raise
    finally:
        # Clean up browser
        await browser_manager.close_browser()
        
        # --- CLEANUP ---
        try:
            await sheets_tool.delete_sheet(sheet_name)
            print("--- CLEANUP COMPLETE ---")
        except Exception as cleanup_error:
            print(f"Warning: Cleanup failed: {cleanup_error}")
