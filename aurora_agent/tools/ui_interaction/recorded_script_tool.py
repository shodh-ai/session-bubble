import logging
import os
import json

# Import the shared browser_manager and the executor
from aurora_agent.browser_manager import browser_manager, execute_interaction_on_page

logger = logging.getLogger(__name__)

async def run_recorded_ui_script(script_name: str) -> str:
    """
    Executes a complex, multi-step, pre-recorded visual demonstration from a file.
    The `script_name` should be the name of the file without the .py extension.
    """
    logger.info(f"SCRIPT-RUNNER TOOL: Executing recorded script: '{script_name}'")
    page = browser_manager.page
    if not page:
        return "Error: Browser page not available."

    try:
        # Construct the full, correct path to the script file
        script_path = os.path.join(
            # Start from the directory of *this* file
            os.path.dirname(__file__), 
            # Go up two levels (from tools/ui_interaction to aurora_agent)
            '..', '..', 
            # Go into the recorded_scripts directory
            'recorded_scripts', 
            f"{script_name}.py"
        )
        
        if not os.path.exists(script_path):
            error_msg = f"Script '{script_name}' not found at path '{os.path.abspath(script_path)}'."
            logger.error(error_msg)
            return f"Error: {error_msg}"

        with open(script_path, 'r') as f:
            interaction_code = f.read()
        
        # Reuse our existing, robust executor to run the script from the file
        # Note: The executor needs the page object.
        result_dict = await execute_interaction_on_page(page, interaction_code)
        
        # Return the final message
        return result_dict.get("message", "Script executed.") if result_dict.get("success") else result_dict.get("error", "Unknown error during script execution.")

    except Exception as e:
        logger.error(f"Error in run_recorded_script: {e}", exc_info=True)
        return f"Error: An unexpected exception occurred while running the script: {e}"