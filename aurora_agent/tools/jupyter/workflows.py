# File: session-bubble/aurora_agent/tools/jupyter/workflows.py

import logging
import asyncio

# Import the two "primitive" tools that this workflow will use.
from aurora_agent.tools.ui_interaction.recorded_script_tool import run_recorded_ui_script
from aurora_agent.tools.ui_interaction.code_generator import generate_and_type_python_code

# --- THIS IS THE NEW IMPORT ---
# We now also import our new, powerful "reading" tool.
from aurora_agent.tools.jupyter.notebook_parser_tool import get_notebook_state

logger = logging.getLogger(__name__)

async def write_and_run_code(prompt_for_code_gen: str) -> str:
    """
    The complete "scientist" workflow. It generates code, types it,
    runs the cell, AND then immediately reads the output to report the result.
    """
    logger.info(f"--- WORKFLOW: Starting 'Write, Run, and Read' ---")
    
    # --- Step 1: Generate and Type the Code (No change) ---
    typing_result = await generate_and_type_python_code(prompt_for_code_gen)
    if "Error" in typing_result:
        return typing_result
    
    await asyncio.sleep(2) # Pedagogical pause
    
    # --- Step 2: Run the Cell (No change) ---
    run_result = await run_recorded_ui_script("jupyter_run_current_cell")
    if "Error" in run_result:
        return run_result
    
    # Give the kernel a moment to execute and render the output
    await asyncio.sleep(1)

    # --- Step 3: READ THE OUTPUT (The New, Critical Step) ---
    logger.info("WORKFLOW: Code executed. Now, reading the output...")
    read_result = await get_notebook_state()
    if "Error" in read_result:
        return read_result # Propagate the error if reading fails

    # In a real system, we would send this rich JSON back to an LLM for summarization.
    # For our MVP, we can just return the raw result.
    final_report = (
        "Success: The code was generated, typed, and the cell was executed.\n"
        f"Here is the new state of the notebook:\n{read_result}"
    )
    
    logger.info("WORKFLOW: 'Write, Run, and Read' completed successfully.")
    return final_report