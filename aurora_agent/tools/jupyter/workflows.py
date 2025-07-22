import logging
import asyncio
# Import the two "primitive" tools that this workflow will orchestrate.
from ..ui_interaction.recorded_script_tool import run_recorded_ui_script
from ..ui_interaction.code_generator import generate_and_type_python_code

logger = logging.getLogger(__name__)

async def write_and_run_code(prompt_for_code_gen: str) -> str:
    """
    The champion workflow. It narrates its actions, types the code,
    pauses, re-focuses the cell, and then executes it.
    """
    logger.info(f"--- WORKFLOW: Starting 'Write and Run Code' ---")
    
    # --- Step 1: Narrate the "Thinking" Time ---
    # This addresses the "it took so much time" feeling.
    # A real implementation would send this to the UI via WebSocket/RPC.
    # For now, we log it.
    print("AGENT NARRATION: 'Okay, I will write the Python code for that now. One moment...'")
    
    # --- Step 2: Generate and Type the Code ---
    typing_result = await generate_and_type_python_code(prompt_for_code_gen)
    
    # --- Step 3: VERIFY ---
    if "Error" in typing_result:
        logger.error(f"WORKFLOW FAILED at typing step. Aborting. Reason: {typing_result}")
        return typing_result
    
    # --- Step 4: Pedagogical Pause ---
    print("AGENT NARRATION: 'I've typed the code. Now, I will run the cell.'")
    await asyncio.sleep(2) # Pause so the student can see the code.
    
    # --- Step 5: Run the Cell ---
    run_result = await run_recorded_ui_script("jupyter_run_current_cell")
    
    # --- Step 6: FINAL VERIFICATION ---
    # This is the crucial fix for the silent failure.
    if "Error" in run_result:
        logger.error(f"WORKFLOW FAILED at run step. Reason: {run_result}")
        return run_result

    logger.info("WORKFLOW: 'Write and Run Code' completed successfully.")
    return "Success: The code was generated, typed, and the cell was executed."