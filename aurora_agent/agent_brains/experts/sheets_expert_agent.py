# in aurora_agent/agent_brains/experts/sheets_expert_agent.py (FINAL, UNAMBIGUOUS VERSION)
import logging
import json
from google.adk.agents import Agent

from ...tools.sheets import get_sheets_tool_instance
from ...ui_tools.interaction_tool import generate_playwright_code, execute_interaction
from ...browser_manager import browser_manager

logger = logging.getLogger(__name__)

# Maintained for backward compatibility with adk_service.py
def set_extracted_sheet_name(name: str):
    """No-op function maintained for backward compatibility.
    
    This function is called by adk_service.py but is no longer needed in the refactored agent.
    The parameter extraction is now handled directly in the agent's instruction.
    """
    logger.debug(f"set_extracted_sheet_name called with: {name} (no-op in refactored agent)")

# --- We define our HIGH-LEVEL "SKILL" FUNCTIONS ---

async def create_chart_using_ui(sheet_name: str, data_range: str) -> str:
    """
    Use this precise tool for any mission that involves creating a chart from data in a specific sheet and range. This tool visually demonstrates the process.
    """
    logger.info("\n=== CHART CREATION TOOL INVOKED ===")
    logger.info(f"Sheet name: {sheet_name}")
    logger.info(f"Data range: {data_range}")
    logger.info("---")
    
    page = browser_manager.page
    if not page: 
        error_msg = "Browser page not available. Cannot create chart."
        logger.error(error_msg)
        return json.dumps({"success": False, "error": error_msg})

    try:
        # Step 1: Reliably select the data range using the most robust Playwright methods.
        await page.locator(f"//div[contains(@class, 'goog-inline-block') and text()='{sheet_name}']").click()
        await page.locator("#name-box").click()
        await page.keyboard.type(data_range)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(500)
        logger.info(f"Step 1/3: Selected data range '{data_range}'.")

        # Step 2 & 3: Use the code-generating agent for the menu clicks.
        chart_creation_prompt = "Click the 'Insert' menu, then click the 'Chart' option from the dropdown."
        generated_code = await generate_playwright_code(page, chart_creation_prompt, [])
        result = await execute_interaction(page, generated_code)
        
        if not result["success"]: return json.dumps(result)
        logger.info("Steps 2 & 3: Successfully navigated menus to create chart.")
        return json.dumps({"success": True, "message": "Chart creation workflow completed."})
    except Exception as e:
        logger.error(f"Error in create_chart_using_ui: {e}", exc_info=True)
        return json.dumps({"success": False, "error": str(e)})

async def create_new_sheet_using_api(title: str) -> str:
    """
    Use this precise tool when the mission is specifically to create a new, empty sheet (tab). This action is non-visual and uses the API for efficiency.
    """
    sheets_api = get_sheets_tool_instance()
    logger.info(f"Expert Agent is calling API to create sheet with title='{title}'")
    return await sheets_api.create_sheet(title)

async def run_recorded_ui_script(script_name: str) -> str:
    """
    Use this tool to execute complex, multi-step, pre-recorded visual demonstrations. This is the most reliable tool for critical workflows like 'create a chart'. The `script_name` should be the name of the file without the .py extension.
    """
    logger.info(f"--- SHEETS EXPERT is calling the Script Runner for: '{script_name}' ---")
    page = browser_manager.page
    if not page: return json.dumps({"success": False, "error": "Browser page not available."})

    try:
        script_path = os.path.join(
            os.path.dirname(__file__), 
            '../../../recorded_scripts', # Navigate to the scripts directory
            f"{script_name}.py"
        )
        if not os.path.exists(script_path):
            return json.dumps({"success": False, "error": f"Script '{script_name}' not found."})

        with open(script_path, 'r') as f:
            interaction_code = f.read()
        
        # We reuse our existing, robust executor to run the script from the file
        result = await execute_interaction(page, interaction_code)
        return json.dumps(result)

    except Exception as e:
        logger.error(f"Error in run_recorded_script: {e}", exc_info=True)
        return json.dumps({"success": False, "error": str(e)})

# --- THE FINAL, UNAMBIGUOUS AGENT INSTRUCTION ---
EXPERT_AGENT_INSTRUCTION = """
You are a tool-calling agent. Your response MUST be a tool call, never text.

FOR THE REQUEST "Show me the full process of creating a chart":
Call: run_recorded_ui_script(script_name="create_chart")

FOR OTHER REQUESTS:
- Chart creation with details: create_chart_using_ui(sheet_name, data_range)
- New sheet creation: create_new_sheet_using_api(title)

IMPORTANT:
- NO text responses
- NO explanations
- NO thoughts
- ONLY tool calls
- Call exactly ONE tool per request
"""

def get_expert_agent():
    """Factory function that provides the agent with a clean, unambiguous toolkit."""
    # The agent's toolkit is now very small and clear. There is no overlap.
    all_tools = [
        create_chart_using_ui,
        create_new_sheet_using_api,
        run_recorded_ui_script,
    ]
    
    logger.info("\n=== CREATING SHEETS EXPERT AGENT ===")
    logger.info(f"Tools available: {[tool.__name__ for tool in all_tools]}")
    logger.info(f"Instruction length: {len(EXPERT_AGENT_INSTRUCTION)} chars")
    
    # Create the agent with our tools and instruction
    agent = Agent(
        name="expert_agent",
        model="gemini-2.5-flash",
        instruction=EXPERT_AGENT_INSTRUCTION,
        tools=all_tools,
    )
    
    logger.info("Sheets expert agent created successfully")
    return agent