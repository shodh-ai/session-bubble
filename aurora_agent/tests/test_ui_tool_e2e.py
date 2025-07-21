# in tests/test_ui_tool_e2e.py
import pytest
import yaml
import os
import json
from dotenv import load_dotenv

# --- Import the components we are testing and using ---
from aurora_agent.browser_manager import browser_manager
from aurora_agent.agent_brains.experts.sheets_expert_agent import perform_visual_ui_action
from aurora_agent.tools.sheets import get_sheets_tool_instance

# Load scenarios
with open(os.path.join(os.path.dirname(__file__), 'ui_tool_scenarios.yaml'), 'r') as f:
    scenarios = yaml.safe_load(f)

@pytest.mark.parametrize("scenario", scenarios)
@pytest.mark.asyncio
async def test_perform_visual_ui_action_end_to_end(scenario):
    """
    This is an end-to-end integration test for the 'perform_visual_ui_action' tool ONLY.
    It proves the Perception -> Reasoning -> Action loop for the UI tool is working.
    """
    print(f"\n--- RUNNING SCENARIO: {scenario['name']} ---")
    load_dotenv()
    
    # --- ARRANGE (Setup) ---
    sheets_tool = get_sheets_tool_instance()
    spreadsheet_id = os.getenv("TEST_SPREADSHEET_ID")
    spreadsheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    
    # Execute all setup steps from the YAML file
    for step in scenario['verification']['setup']:
        setup_func = getattr(sheets_tool, step['function'])
        await setup_func(*step['args'])
    print("✅ SETUP: Sheet is in a clean, known state.")

    # We need the browser to be visible to debug
    is_headed = os.getenv("HEADED_TEST", "true").lower() == "true"
    
    try:
        await browser_manager.start_browser(headless=not is_headed)
        page = await browser_manager.get_page(spreadsheet_url)
        browser_manager.page = page # Make page accessible to the tool

        # --- ACT ---
        prompt = scenario['prompt']
        print(f"\nACTION: Calling 'perform_visual_ui_action' with prompt: '{prompt}'")
        result_json = await perform_visual_ui_action(prompt=prompt)
        result = json.loads(result_json)
        
        print(f"ACTION: Tool returned: {result}")
        assert result["success"], f"The UI tool failed: {result.get('error')}"
        print("✅ ACTION: UI tool executed successfully.")

        # --- ASSERT (Verification) ---
        print("\nVERIFICATION: Checking ground truth with API tool...")
        for step in scenario['verification']['verify']:
            verify_func = getattr(sheets_tool, step['function'])
            actual_result = await verify_func(*step['args'])
            
            expected_substring = step['expected_result_contains']
            assert expected_substring in actual_result, \
                f"Verification Failed! Expected to find '{expected_substring}' in '{actual_result}'"
        print("✅ VERIFICATION: Ground truth matches expected state.")

    finally:
        await browser_manager.close_browser()