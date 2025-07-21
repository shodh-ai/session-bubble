import os
from .api_client import SheetsAPIClient
from .api_tool import SheetsTool

# This is a factory function. It ensures that the SheetsTool is created
# only when this function is called, giving time for .env to be loaded.
from dotenv import load_dotenv

def get_sheets_tool_instance():
    """Factory function to create and return an instance of SheetsTool."""
    spreadsheet_id = os.getenv('TEST_SPREADSHEET_ID')
    key_file_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_KEY_PATH')

    if not spreadsheet_id or not key_file_path:
        print("Error: SPREADSHEET_ID or GOOGLE_SERVICE_ACCOUNT_KEY_PATH not found in environment variables.")
        return None

    try:
        # Construct the full path if key_file_path is relative to the project root
        if not os.path.isabs(key_file_path):
            # Assuming the test is run from the project root
            project_root = os.getcwd()
            key_file_path = os.path.join(project_root, key_file_path)

        api_client = SheetsAPIClient(key_file_path=key_file_path, spreadsheet_id=spreadsheet_id)
        return SheetsTool(client=api_client)
    except Exception as e:
        print(f"Error initializing SheetsTool: {e}")
        return None

# We also need to expose the interaction tool from this module if the agent uses it
from ...ui_tools.interaction_tool import execute_interaction

__all__ = ['get_sheets_tool_instance', 'execute_interaction']
