# in aurora_agent/tools/jupyter/lesson_player.py
import logging
import ast
import os
import re
import asyncio
from ...browser_manager import browser_manager, execute_interaction_on_page
from .reader_tool import read_output_of_cell_n, read_code_of_cell_n

logger = logging.getLogger(__name__)

async def animated_type(code_block: str):
    """A robust tool that clears a cell and types code line-by-line."""
    page = browser_manager.page
    active_cell_selector = "div.jp-Notebook-cell.jp-mod-active .cm-content"
    active_cell = page.locator(active_cell_selector)
    await active_cell.wait_for(state="visible", timeout=10000)
    # Use fill() which is atomic and robust. It clears and types in one step.
    await active_cell.fill(code_block)
    logger.info("TYPING-TOOL: Filled cell with code block.")

async def wait_for_run_to_complete(page):
    """A robust two-stage wait."""
    logger.info("WAIT-TOOL: Starting wait for cell completion.")
    busy_indicator = page.locator("div.jp-Notebook-cell.jp-mod-active.jp-mod-busy")
    try:
        await busy_indicator.wait_for(state="visible", timeout=5000)
        await busy_indicator.wait_for(state="hidden", timeout=360000)
        logger.info("WAIT-TOOL: Cell is now idle.")
    except Exception:
        logger.warning("WAIT-TOOL: Did not observe busy state; assuming fast execution.")

async def execute_lesson_script(script_name: str) -> str:
    """The final, correct implementation, using a precise reader and correct synchronization."""
    logger.info(f"--- FINAL INTERPRETER: Starting lesson '{script_name}' ---")
    page = browser_manager.page
    if not page: return "Error: Browser not available."

    try:
        script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'recorded_scripts', f"{script_name}.py")
        if not os.path.exists(script_path): return f"Error: Script '{script_name}' not found."
        
        with open(script_path, 'r') as f:
            full_script_content = f.read()
        tree = ast.parse(full_script_content)
        commands = [ast.unparse(node).strip() for node in tree.body]

        code_buffer = []
        cell_execution_count = 1
        last_output = "No output was read."

        for i, command_code in enumerate(commands):
            match = re.search(r"get_by_text\((['\"])(.*?)\1\)", command_code, re.DOTALL)
            if match:
                code_to_type = match.group(2)
                code_buffer.append(code_to_type)
            else:
                if code_buffer:
                    await animated_type("\n".join(code_buffer))
                    code_buffer = []

                if "Run this cell and advance" in command_code:
                    logger.info(f"Action: Executing 'Run' for cell {cell_execution_count}.")
                    result = await execute_interaction_on_page(page, command_code)
                    if not result["success"]: return result["error"]
                    
                    await wait_for_run_to_complete(page)
                    
                    # THE FINAL FIX: A small pause for the UI to render the output.
                    logger.info("Pausing for 1 second to allow UI to render output.")
                    await asyncio.sleep(1)
                    
                    last_output = await read_output_of_cell_n(cell_execution_count)
                    cell_execution_count += 1
                else:
                    logger.warning(f"Ignoring irrelevant command: {command_code}")
        
        logger.info(f"Final output from last executed cell was: {last_output}")
        return f"Success: Lesson script completed. Final state: {last_output}"

    except Exception as e:
        logger.error(f"Error during lesson execution: {e}", exc_info=True)
        return f"Error: An unexpected exception occurred: {e}"