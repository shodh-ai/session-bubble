# File: session-bubble/aurora_agent/tools/jupyter/individual_command_executor.py

import logging
from typing import Dict, Any
from .screenshot_feedback import send_action_feedback

# Remove browser_manager dependency to prevent multiple browser instances
# All page objects should be passed from the VNC listener's global browser handler
# when running in VNC listener context
browser_manager = None

logger = logging.getLogger(__name__)

async def execute_jupyter_command(tool_name: str, parameters: Dict[str, Any], page=None) -> str:
    """
    Execute individual Jupyter commands sent from the backend.
    This replaces the old recorded script approach with individual command execution.
    
    Args:
        tool_name: The name of the Jupyter tool (e.g., 'jupyter_type_in_cell', 'jupyter_run_cell')
        parameters: Dictionary containing the parameters for the command
        page: Optional page object (for VNC listener context)
    
    Returns:
        String result of the command execution
    """
    logger.info(f"--- INDIVIDUAL COMMAND EXECUTOR: Executing {tool_name} ---")
    
    # Page must be provided by the VNC listener's global browser handler
    if page is None:
        return "Error: No page provided. Page must be passed from VNC listener."

    try:
        # Execute the command
        result = None
        if tool_name == "jupyter_type_in_cell":
            result = await _jupyter_type_in_cell(page, parameters)
        elif tool_name == "jupyter_run_cell":
            result = await _jupyter_run_cell(page, parameters)
        elif tool_name == "jupyter_create_new_cell":
            result = await _jupyter_create_new_cell(page, parameters)
        elif tool_name == "jupyter_scroll_to_cell":
            result = await _jupyter_scroll_to_cell(page, parameters)
        elif tool_name == "jupyter_click_pyodide":
            result = await _jupyter_click_pyodide(page, parameters)
        else:
            result = f"Error: Unknown Jupyter command '{tool_name}'"
        
        # Send screenshot feedback to LangGraph after the action
        try:
            await send_action_feedback(page, tool_name, result, parameters)
        except Exception as feedback_error:
            logger.warning(f"Failed to send screenshot feedback: {feedback_error}")
            # Don't fail the main command if feedback fails
        
        return result
            
    except Exception as e:
        error_msg = f"Error executing {tool_name}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Send screenshot feedback even for errors
        try:
            await send_action_feedback(page, tool_name, error_msg, parameters)
        except Exception:
            pass  # Ignore feedback errors during error handling
            
        return error_msg

async def _jupyter_type_in_cell(page, parameters: Dict[str, Any]) -> str:
    """Type code into a specific Jupyter cell using the correct CodeMirror approach"""
    # Convert cell_index to integer to handle string inputs from frontend
    cell_index_raw = parameters.get('cell_index', 0)
    try:
        cell_index = int(cell_index_raw) if cell_index_raw is not None else 0
    except (ValueError, TypeError):
        cell_index = 0
    
    code = parameters.get('code', '')
    
    if not code:
        return "Error: No code provided to type"
    
    logger.info(f"Typing code into cell {cell_index}: {code[:50]}...")
    
    try:
        # Always use explicit cell selection for better reliability
        # Convert cell_index to 1-based for nth-of-type selector
        # Handle case where cell_index might be 0 or negative
        if cell_index is None or cell_index < 0:
            cell_number = 1  # Default to first cell
        else:
            cell_number = cell_index + 1  # Convert 0-based to 1-based
        
        # First, ensure the cell exists and click on it to make it active
        cell_click_selector = f".jp-Notebook-cell:nth-of-type({cell_number})"
        logger.info(f"Looking for cell with selector: {cell_click_selector}")
        
        # Wait for the cell to exist
        await page.locator(cell_click_selector).wait_for(state="visible", timeout=15000)
        
        # Click on the cell to make it active
        await page.locator(cell_click_selector).click()
        logger.info(f"Clicked on cell {cell_number}")
        
        # Wait for the cell to become active
        await page.wait_for_timeout(1500)
        
        # Now target the CodeMirror content area within the active cell
        cell_selector = "div.jp-Notebook-cell.jp-mod-active .cm-content"
        
        # Wait for the cell to be ready and click it to ensure focus
        await page.locator(cell_selector).wait_for(state="visible", timeout=10000)
        await page.locator(cell_selector).click()
        
        # Clear existing content using keyboard shortcuts
        await page.keyboard.press("Control+a")  # Select all
        await page.keyboard.press("Delete")     # Delete selected content
        
        # Type the new code using keyboard (like code_generator.py does)
        await page.keyboard.type(code, delay=50)  # 50ms delay makes it visible
        
        return f"Successfully typed code into cell {cell_index}"
        
    except Exception as e:
        logger.error(f"Error typing into cell {cell_index}: {e}")
        return f"Error typing into cell {cell_index}: {str(e)}"

async def _jupyter_run_cell(page, parameters: Dict[str, Any]) -> str:
    """Execute a specific Jupyter cell using the execution_tool.py approach"""
    # Convert cell_index to integer to handle string inputs from frontend
    cell_index_raw = parameters.get('cell_index', 0)
    try:
        cell_index = int(cell_index_raw) if cell_index_raw is not None else 0
    except (ValueError, TypeError):
        cell_index = 0
        
    wait_for_completion = parameters.get('wait_for_completion', True)
    timeout = parameters.get('timeout', 3600000)  # 1 hour default like execution_tool.py
    
    logger.info(f"Running cell {cell_index}, wait_for_completion={wait_for_completion}")
    
    try:
        # Always use explicit cell selection for consistency with _jupyter_type_in_cell
        # Convert cell_index to 1-based for nth-of-type selector
        cell_number = cell_index + 1 if cell_index >= 0 else 1
        
        # First, ensure the correct cell is active by clicking on it
        cell_click_selector = f".jp-Notebook-cell:nth-of-type({cell_number})"
        logger.info(f"Selecting cell with selector: {cell_click_selector}")
        
        await page.locator(cell_click_selector).wait_for(state="visible", timeout=10000)
        await page.locator(cell_click_selector).click()
        logger.info(f"Clicked on cell {cell_number} (index {cell_index})")
        await page.wait_for_timeout(1500)  # Wait longer for cell to become active
        
        # Use the approach from the recorded script (jupyter_full_lesson.py)
        active_cell_selector = "div.jp-Notebook-cell.jp-mod-active"
        busy_indicator_selector = f"{active_cell_selector}.jp-mod-busy"
        
        # Use the selector from the recorded script that works
        run_button = page.get_by_role("button", name="Run this cell and advance")
        
        # Click the Run button to start execution
        await run_button.click()
        logger.info(f"Run command sent for cell {cell_index}. Monitoring for completion...")
        
        if wait_for_completion:
            # The "Smart Wait" from execution_tool.py
            try:
                # Short wait for it to become busy
                await page.locator(busy_indicator_selector).wait_for(state="visible", timeout=5000)
                logger.info(f"Cell {cell_index} is busy (execution started).")
            except Exception:
                # This is okay, it might have run too fast to catch the busy state
                logger.warning(f"Cell {cell_index} did not appear busy. Proceeding to wait for idle.")
            
            # The main, long wait
            await page.locator(busy_indicator_selector).wait_for(state="hidden", timeout=timeout)
            
            logger.info(f"Cell {cell_index} is no longer busy (execution finished).")
            return f"Successfully executed cell {cell_index} and waited for completion"
        else:
            return f"Successfully triggered execution of cell {cell_index}"
            
    except Exception as e:
        logger.error(f"Error running cell {cell_index}: {e}")
        return f"Error running cell {cell_index}: {str(e)}"

async def _jupyter_create_new_cell(page, parameters: Dict[str, Any]) -> str:
    """Create a new Jupyter cell"""
    cell_type = parameters.get('cell_type', 'code')  # 'code' or 'markdown'
    position = parameters.get('position', 'below')   # 'above' or 'below'
    
    logger.info(f"Creating new {cell_type} cell {position} current cell")
    
    # Use keyboard shortcuts to create new cell
    if position == 'above':
        await page.keyboard.press("a")  # Insert cell above
    else:
        await page.keyboard.press("b")  # Insert cell below
    
    # Change cell type if needed
    if cell_type == 'markdown':
        await page.keyboard.press("m")  # Change to markdown
    elif cell_type == 'code':
        await page.keyboard.press("y")  # Change to code (default)
    
    return f"Successfully created new {cell_type} cell {position} current cell"

async def _jupyter_scroll_to_cell(page, parameters: Dict[str, Any]) -> str:
    """Scroll to a specific cell in the Jupyter notebook"""
    cell_index = parameters.get('cell_index', 1)
    
    logger.info(f"Scrolling to cell {cell_index}")
    
    # Find the specific cell and scroll it into view
    cell_selector = f".jp-Notebook-cell:nth-child({cell_index})"
    
    try:
        await page.locator(cell_selector).scroll_into_view_if_needed()
        await page.locator(cell_selector).click()
        return f"Successfully scrolled to and focused cell {cell_index}"
    except:
        return f"Error: Could not find or scroll to cell {cell_index}"

async def _jupyter_click_pyodide(page, parameters: Dict[str, Any]) -> str:
    """Click on the Python (Pyodide) kernel option"""
    logger.info("Clicking Python (Pyodide) kernel option")
    
    try:
        # Use the exact selector from the recorded script
        await page.get_by_title("Python (Pyodide)").first.click()
        return "Successfully clicked Python (Pyodide) kernel"
    except Exception as e:
        return f"Error clicking Python (Pyodide): {str(e)}"
