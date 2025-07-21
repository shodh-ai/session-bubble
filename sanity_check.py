# in /session-bubble/sanity_check_api.py
import asyncio
import os
import uuid
from dotenv import load_dotenv

# Set the python path to include your project
import sys
sys.path.insert(0, '.')

from aurora_agent.tools.sheets import get_sheets_tool_instance

async def main():
    """A simple test to verify the API tool works."""
    print("--- RUNNING API SANITY CHECK ---")
    
    # Load environment variables
    load_dotenv()
    if not os.getenv("TEST_SPREADSHEET_ID") or not os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_PATH"):
        print("ERROR: Missing .env variables. Please check your .env file.")
        return

    try:
        # Get an instance of our tested tool
        sheets_tool = get_sheets_tool_instance()
        print("Successfully initialized SheetsTool.")

        # Create a unique name for the sheet to avoid collisions
        sheet_name = f"Sanity_Check_{uuid.uuid4().hex[:8]}"

        # 1. Test Sheet Creation
        print(f"Attempting to create sheet: '{sheet_name}'...")
        create_result = await sheets_tool.create_sheet(sheet_name)
        print(f"API Response: {create_result}")
        assert "Success" in create_result, "Sheet creation failed!"
        print("✅ Sheet Creation: PASSED")

        # 2. Test Sheet Deletion (Cleanup)
        print(f"Attempting to delete sheet: '{sheet_name}'...")
        delete_result = await sheets_tool.delete_sheet(sheet_name)
        print(f"API Response: {delete_result}")
        assert "Success" in delete_result, "Sheet deletion failed!"
        print("✅ Sheet Deletion: PASSED")

        print("\n--- API SANITY CHECK: SUCCESS ---")

    except Exception as e:
        print(f"\n--- API SANITY CHECK: FAILED ---")
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())