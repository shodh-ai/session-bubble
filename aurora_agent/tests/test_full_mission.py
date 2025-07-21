# in tests/test_full_mission.py
import pytest
import os
import uuid
from dotenv import load_dotenv

# Import the main entry point and the verification tool
from aurora_agent.adk_service import execute_browser_mission
from aurora_agent.tools.sheets import get_sheets_tool_instance

# Load environment variables
load_dotenv()

@pytest.mark.asyncio
async def test_full_mission_e2e_create_sheet():
    """
    This is a full end-to-end test. It runs the entire agent stack with
    real tools and a real browser to verify a complete mission.
    """
    # --- ARRANGE ---
    # Create a unique sheet name for this test run to prevent collisions
    unique_sheet_name = f"E2E_Test_{uuid.uuid4().hex[:8]}"
    
    mission_payload = {
      "application": "google_sheets",
      "mission_prompt": f"Please create a new sheet named '{unique_sheet_name}'.",
      "session_context": {
        "user_id": "e2e_test_user",
        "current_url": os.getenv("TEST_SPREADSHEET_URL")
      }
    }
    
    sheets_verifier = get_sheets_tool_instance()

    # --- ACT ---
    print(f"\n--- RUNNING FULL E2E MISSION: Create Sheet '{unique_sheet_name}' ---")
    result = await execute_browser_mission(mission_payload)
    print(f"--- MISSION COMPLETE ---")
    print(f"Final Result: {result}")

    # --- ASSERT ---
    # 1. Assert that the mission itself reported success
    assert result["status"] == "SUCCESS"

    # 2. Verify the "ground truth" using the API tool
    sheet_list_response = await sheets_verifier.list_sheets()
    import json
    try:
        sheet_data = json.loads(sheet_list_response)
        assert sheet_data["status"] == "SUCCESS", f"Failed to list sheets for verification: {sheet_list_response}"
        sheet_names = sheet_data.get("sheets", [])
        assert unique_sheet_name in sheet_names, f"Verification failed: Sheet '{unique_sheet_name}' was not found in {sheet_names}"
    except json.JSONDecodeError:
        # Fallback to string-based check if not JSON
        assert "Success" in sheet_list_response, f"Failed to list sheets for verification: {sheet_list_response}"
        assert unique_sheet_name in sheet_list_response, f"Verification failed: Sheet '{unique_sheet_name}' was not found."

    # Cleanup
    await sheets_verifier.delete_sheet(unique_sheet_name)
    print(f"--- CLEANUP COMPLETE ---")
