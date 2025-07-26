# File: session-bubble/aurora_agent/agent_brains/experts/jupyter/graph.py
# in aurora_agent/agent_brains/experts/jupyter/graph.py
from langgraph.graph import StateGraph, END
from .state import JupyterExpertState

# We only need to import our one, powerful node.
from .nodes import execute_mission_node

def create_jupyter_expert_subgraph():
    """Creates the final, simplified LangGraph expert for Jupyter."""
    workflow = StateGraph(JupyterExpertState)

    # The graph is now just a single, powerful step.
    workflow.add_node("execute_mission", execute_mission_node)
    workflow.set_entry_point("execute_mission")
    workflow.add_edge("execute_mission", END)

    return workflow.compile()

# Create the singleton instance for the application to import.
jupyter_expert_graph = create_jupyter_expert_subgraph()