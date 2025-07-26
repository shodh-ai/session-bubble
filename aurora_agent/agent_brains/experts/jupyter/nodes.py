# File: session-bubble/aurora_agent/agent_brains/experts/jupyter/nodes.py

from ....tools.jupyter.lesson_player import execute_lesson_script
from .state import JupyterExpertState

async def execute_mission_node(state: JupyterExpertState) -> dict:
    """
    This node triggers the smart interpreter to execute a full,
    pre-recorded lesson script.
    """
    # The mission name (e.g., "learn_pandas") can be mapped to a script file name.
    # For now, we hardcode the script we want to run.
    # The 'script_to_run' could come from the input state: state.get("script_to_run")
    script_name = "jupyter_full_lesson" 
    
    print(f"--- Starting mission: Running lesson script '{script_name}' ---")
    
    # The node now calls the intelligent lesson player.
    result = await execute_lesson_script(script_name)
    
    # The final result of the entire interpreted lesson is passed back.
    return {"final_output": result}