import pytest
import yaml
import os
import sys
import json
import asyncio

# --- Core Components We Are Testing ---
from aurora_agent.ui_tools.interaction_tool import interact_agent, execute_interaction
from aurora_agent.tools.sheets.api_client import SheetsAPIClient
from aurora_agent.tools.sheets.tool import SheetsTool
from playwright.async_api import async_playwright

# --- Test Scenarios --- 
SCENARIOS_FILE = os.path.join(os.path.dirname(__file__), 'ui_scenarios.yaml')
with open(SCENARIOS_FILE, 'r') as f:
    scenarios = yaml.safe_load(f)

@pytest.mark.parametrize("scenario", scenarios)
@pytest.mark.asyncio
async def test_ui_agent_end_to_end_scenario(scenario):
    """
    This test orchestrates the full Perception -> Reasoning -> Action -> Verification loop
    for the UI agent, proving all components work together.
    """
    print(f"\n--- RUNNING SCENARIO: {scenario['name']} ---")

    # 1. SETUP: Prepare environment variables and clients
    from dotenv import load_dotenv
    dotenv_path = os.path.join(os.path.dirname(__file__), '../.env')
    load_dotenv(dotenv_path=dotenv_path)

    spreadsheet_id = os.getenv("TEST_SPREADSHEET_ID")
    key_file_path = os.path.join(os.path.dirname(__file__), '../service-account-key.json')
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    assert spreadsheet_id and os.path.exists(key_file_path), "Setup failed: ENV vars not configured."

    api_verifier = SheetsAPIClient(key_file_path=key_file_path, spreadsheet_id=spreadsheet_id)
    sheets_tool = SheetsTool(client=api_verifier)

    # --- LAUNCH AUTHENTICATED BROWSER ---
    auth_file_path = os.path.join(os.path.dirname(__file__), '../auth.json')
    assert os.path.exists(auth_file_path), f"Auth file not found at {auth_file_path}. Please run setup_auth.py first."

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Run in headed mode for debugging
        context = await browser.new_context(storage_state=auth_file_path)
        page = await context.new_page()
        # For complex apps like Google Sheets, 'networkidle' is unreliable.
        # We wait for the DOM to load, then specifically for the grid element later.
        await page.goto(spreadsheet_url, wait_until="domcontentloaded", timeout=60000)

        # Ensure a clean state for the test
        verification_details = scenario['verification']
        cell_to_check = verification_details['verification_step']['args'][0]
        await sheets_tool.clear_range(cell_to_check)
        print(f"SETUP: Cleared cell {cell_to_check}.")

        # Execute the setup step from the scenario
        if 'setup_step' in verification_details:
            setup = verification_details['setup_step']
            setup_func = getattr(sheets_tool, setup['function_to_call'])
            await setup_func(*setup['args'])
            print(f"SETUP: Executed setup step: {setup['function_to_call']}.")

        # 1. PERCEPTION ("Eyes")
        # CRITICAL: Wait for the main grid to be visible before parsing.
        # This ensures the page is fully loaded and interactive.
        print("Step 1: Waiting for sheet grid to load...")
        await page.locator("div#docs-editor-container").wait_for(timeout=15000)
        
        print("Step 1: Running Perception to gather element info...")
        from aurora_agent.parsers import get_parser_for_url
        parser = get_parser_for_url(page.url)
        element_info_list = await parser.get_interactive_elements(page)
        element_info_json = json.dumps(element_info_list, default=str, indent=2)
        print(f"Perception found {len(element_info_list)} interactive elements.")

        # 2. REASONING ("Brain") - Placeholder Agent
        print("Step 2: Running Reasoning to generate action...")
        # 'interact_agent' is an instance, not a class, so we use it directly.
        # The placeholder agent expects a single 'new_message' argument.
        # The agent returns a response object; we need to extract the code text.
        agent_response = await interact_agent.run_async(
            user_prompt=scenario['prompt'],
            element_info_list=element_info_list # Pass the actual list of dicts
        )
        generated_code = agent_response.content.parts[0].text
        print(f"Reasoning generated the following code:\n{generated_code}")

        # 3. ACTION ("Hands")
        print("Step 3: Executing the generated code...")
        execution_result = await execute_interaction(page, generated_code)
        assert execution_result["success"], f"Action execution failed: {execution_result['error']}"
        print("Action executed successfully.")

        # Add a delay to allow the backend to process the format change
        print("Waiting for 3 seconds for backend to sync...")
        await asyncio.sleep(3)

        # 4. VERIFICATION
        print("Step 4: Verifying the result via API...")
        # Dynamically get the verification function from the tool (e.g., 'get_cell_value')
        verify_step_details = verification_details["verification_step"]
        verification_func_name = verify_step_details["function_to_call"]
        verification_args = verify_step_details.get("args", [])
        expected_result_contains = verify_step_details.get("expected_result_contains", {})
        verification_func = getattr(sheets_tool, verification_func_name)
        actual_result_json = await verification_func(*verification_args)
        actual_result_data = json.loads(actual_result_json) # The tool returns JSON

        print(f"Verification - Expected to contain: '{expected_result_contains}', Got: '{actual_result_data}'")

        # The format data is deeply nested. We need to parse it carefully.
        try:
            # This is the path to the 'bold' property in the API response
            is_bold = actual_result_data['sheets'][0]['data'][0]['rowData'][0]['values'][0]['effectiveFormat']['textFormat']['bold']
        except (KeyError, IndexError):
            is_bold = False # If any key is missing, it's not bold

        # Check if the expected key-value pair is in the actual result
        for key, expected_value in expected_result_contains.items():
            if key == 'bold':
                assert is_bold == expected_value, f"Verification for '{key}' failed. Expected: {expected_value}, Got: {is_bold}"
            else:
                # Add other key checks here if needed for future tests
                pass

        print("--- SCENARIO PASSED ---")
