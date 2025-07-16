# in aurora_agent/agent_brains/experts/sheets_expert_agent.py
import logging
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

logger = logging.getLogger(__name__)

# --- Tool Stubs (Placeholders) ---
# These simulate the tools your colleague is building. They allow you to test your
# agent's logic without needing the real tools to be ready.
async def ui_interaction_tool_stub(prompt: str) -> str:
    """
    Use this tool for any task that requires VISUAL demonstration for the student.
    This includes clicking menus, formatting text, creating charts, or any step-by-step
    process that the user needs to learn by watching.
    Provide a clear, natural language prompt for the action to be performed.
    """
    logger.info(f"--- SHEETS EXPERT called UI_INTERACTION_TOOL (STUB) ---")
    logger.info(f"PROMPT: {prompt}")
    # In the real system, this would call the Playwright interaction tool.
    return "Success: The UI interaction was demonstrated successfully."

async def sheets_api_tool_stub(prompt: str) -> str:
    """
    Use this tool for any EFFICIENT, NON-VISUAL data manipulation.
    This is for tasks where the result is more important than the process.
    Examples: setting the value of thousands of cells, creating a new sheet,
    reading data quickly, or sorting a large dataset.
    Provide a clear, natural language prompt for the data operation.
    """
    logger.info(f"--- SHEETS EXPERT called SHEETS_API_TOOL (STUB) ---")
    logger.info(f"PROMPT: {prompt}")
    # In the real system, this would call your colleague's tested Sheets API tool.
    return "Success: The data operation was completed instantly via the API."

# --- The Agent's Prompt (Its "Brain") ---
# This is the most important part. It teaches the agent how to be a smart specialist.
SHEETS_EXPERT_INSTRUCTION = """
You are a world-class expert on Google Sheets. Your mission is to execute a user's request in the most effective way possible.
You have two primary tools at your disposal: a 'UI Interaction Tool' and a 'Sheets API Tool'.

Your decision-making process is critical:
1.  **Analyze the Goal:** First, understand the user's ultimate goal. Are they trying to LEARN a visual process, or are they trying to accomplish a DATA task efficiently?
2.  **Choose the Right Tool:**
    - If the goal is TEACHING or DEMONSTRATING a process on the screen (e.g., "show me how to make this bold", "create a pivot table step-by-step"), you MUST use the `ui_interaction_tool_stub`.
    - If the goal is a pure DATA operation where speed and reliability are key (e.g., "set all these values", "read the data from column C", "create a new tab"), you MUST use the `sheets_api_tool_stub`.
3.  **Formulate a Clear Prompt:** Once you've chosen a tool, formulate a clear, natural language prompt describing the specific action to be taken and pass it to the tool.
"""

# --- The Agent Definition ---
sheets_expert_agent = Agent(
    name="google_sheets_expert_agent",
    model="gemini-1.5-flash",
    description="A specialist agent that handles all tasks within Google Sheets by intelligently choosing between UI automation and direct API calls.",
    instruction=SHEETS_EXPERT_INSTRUCTION,
    tools=[
        ui_interaction_tool_stub,
        sheets_api_tool_stub,
    ]
)
