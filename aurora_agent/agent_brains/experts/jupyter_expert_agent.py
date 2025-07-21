# in aurora_agent/agent_brains/experts/jupyter_expert_agent.py
import logging
from google.adk.agents import Agent

# We import the REAL tool functions/factories here
# from ....tools.ui.interaction_tool import run_recorded_ui_script # This will be the real one
# For now, we use a stub for structure.

# --- Tool Stubs (Placeholders) ---
async def run_recorded_ui_script_stub(script_name: str) -> str:
    """Use for complex UI actions like saving the notebook or navigating menus."""
    logging.info(f"JUPYTER AGENT: Called run_recorded_script with script: {script_name}")
    return "Success: Pre-recorded UI script executed."

async def generate_and_type_python_code_stub(prompt_for_code_generation: str) -> str:
    """Use this to write Python code into the currently active notebook cell."""
    logging.info(f"JUPYTER AGENT: Called code generator with prompt: {prompt_for_code_generation}")
    # In the real tool, this would call an LLM to generate the Python code,
    # then use Playwright's page.keyboard.type() to type it into the cell.
    return "Success: Python code generated and typed into the cell."

JUPYTER_EXPERT_INSTRUCTION = """
You are an expert Data Science instructor using Jupyter Notebooks. Your mission is to guide a student through a data analysis task.

You have two types of tools:
1.  `run_recorded_ui_script`: For any action involving the Jupyter UI, like running a cell, adding a new cell, or saving the notebook.
2.  `generate_and_type_python_code`: For writing the actual Python code (using Pandas, Matplotlib, etc.) into a cell.

Your workflow for a typical task is a two-step process:
1.  First, call `generate_and_type_python_code` to write the necessary Python script.
2.  Second, call `run_recorded_ui_script` with the script name 'run_current_cell' to execute the code you just wrote.
"""

jupyter_expert_agent = Agent(
    name="jupyter_expert_agent",
    model="gemini-2.5-flash",
    description="A specialist agent for teaching data science workflows in Jupyter Notebooks.",
    instruction=JUPYTER_EXPERT_INSTRUCTION,
    tools=[
        run_recorded_ui_script_stub,
        generate_and_type_python_code_stub,
    ]
)