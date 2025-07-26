# File: session-bubble/aurora_agent/tools/jupyter/reader_tool.py
import logging
from ...browser_manager import browser_manager

logger = logging.getLogger(__name__)


async def read_output_of_cell_n(cell_execution_count: int) -> str:
    """A resilient tool that finds a cell by its execution number and reads its output using precise locators."""
    logger.info(f"--- PRECISE READER: Reading Output of Cell {cell_execution_count} ---")
    page = browser_manager.page
    if not page: return "Error: Browser not available."
    
    try:
        # Step 1: Find the unique input prompt, which is our stable anchor.
        prompt_locator = page.locator(f"div.jp-InputPrompt:has-text('[{cell_execution_count}]')")
        await prompt_locator.wait_for(state="visible", timeout=15000)
        
        # Step 2: From that unique prompt, find the parent cell container.
        cell_container = prompt_locator.locator("xpath=ancestor::div[contains(@class, 'jp-Cell')]")

        # Step 3: From the container, find the output area.
        output_area = cell_container.locator(".jp-Cell-outputArea")
        
        try:
            await output_area.wait_for(state="visible", timeout=2000)
            output_text = await output_area.inner_text()
            logger.info(f"PRECISE READER: Successfully read output: {output_text}")
            return f"Success: Output of cell {cell_execution_count} is:\n---\n{output_text}\n---"
        except Exception:
            logger.warning(f"PRECISE READER: Cell {cell_execution_count} has no visible text output.")
            return f"Success: Cell {cell_execution_count} has no visible text output."
            
    except Exception as e:
        logger.error(f"PRECISE READER: Could not find cell {cell_execution_count}. Error: {e}")
        return f"Error: Could not find cell {cell_execution_count}."

async def read_code_of_cell_n(cell_execution_count: int) -> str:
    """Finds a Jupyter cell by its execution number and reads its source code using precise locators."""
    logger.info(f"--- PRECISE READER: Reading Code of Cell {cell_execution_count} ---")
    page = browser_manager.page
    if not page: return "Error: Browser not available."

    try:
        # Step 1: Find the unique input prompt. This is the stable anchor.
        prompt_locator = page.locator(f"div.jp-InputPrompt:has-text('[{cell_execution_count}]')")
        await prompt_locator.wait_for(state="visible", timeout=15000)
        
        # Step 2: From the anchor, find the parent cell container.
        cell_container = prompt_locator.locator("xpath=ancestor::div[contains(@class, 'jp-Cell')]")
        
        # Step 3: From the container, find the specific code editor area.
        input_area = cell_container.locator(".jp-Cell-inputWrapper .cm-content")
        await input_area.wait_for(state="visible", timeout=10000)

        code_text = await input_area.inner_text()
        logger.info(f"PRECISE READER: Successfully read code: {code_text}")
        return f"Success: Code of cell {cell_execution_count} is:\n---\n{code_text}\n---"
    except Exception as e:
        logger.error(f"PRECISE READER: Could not read code for cell {cell_execution_count}. Error: {e}")
        return f"Error: Could not find code for cell {cell_execution_count}."

async def find_and_click_cell_n(cell_execution_count: int) -> str:
    """Finds a Jupyter cell by its execution number and clicks it to make it active."""
    logger.info(f"--- NAVIGATION TOOL: Clicking Cell {cell_execution_count} ---")
    page = browser_manager.page
    if not page: return "Error: Browser not available."

    try:
        # Use a more specific approach to avoid strict mode violations
        # Find the input prompt first
        prompt_locator = page.locator(f"div.jp-InputPrompt:has-text('[{cell_execution_count}]')")
        await prompt_locator.wait_for(state="visible", timeout=15000)
        
        # Get the most specific cell container - the one with jp-CodeCell class
        cell_container = prompt_locator.locator("xpath=ancestor::div[contains(@class, 'jp-CodeCell')]").first
        
        # Click the input area specifically to make the cell active
        input_area = cell_container.locator(".jp-Cell-inputWrapper .cm-content")
        await input_area.wait_for(state="visible", timeout=5000)
        await input_area.click()
        
        logger.info(f"Successfully clicked on cell {cell_execution_count}.")
        return "Success"
    except Exception as e:
        logger.error(f"NAVIGATION TOOL: Could not find or click cell {cell_execution_count}. Error: {e}")
        return f"Error: Could not click cell {cell_execution_count}."