from .state import JupyterExpertState

# Import our powerful, high-level workflow tool.
# This is the "Captain" that knows the whole recipe.
from ....tools.jupyter.workflows import write_and_run_code

async def execute_mission_node(state: JupyterExpertState) -> dict:
    """
    This is now the ONLY node in our graph.
    It takes the mission prompt from the state and directly calls the
    powerful workflow tool to execute it, returning the final result.
    """
    mission = state["mission_prompt"]
    print(f"--- Jupyter Expert: Received mission. Executing 'write_and_run_code' workflow. ---")
    
    # We call our one powerful tool with the original mission.
    # The tool itself contains all the necessary steps and synchronization.
    result = await write_and_run_code(mission)
            
    # The result from the tool is the final output of the graph.
    return {"final_output": result}