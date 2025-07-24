# in aurora_agent/agent_brains/root_agent.py
import logging
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from .experts.docs_expert_agent import docs_expert_agent_stub
# Import the specialist agent factory
from .experts.sheets_expert_agent import get_expert_agent
from google.adk.tools.agent_tool import AgentTool 
logger = logging.getLogger(__name__)
# Create instances of expert agents
sheets_expert_agent_instance = get_expert_agent()  # create agent instance
# Docs expert: using internal stub instance for import convenience.
# In production, build with live tools via the factory.
# (The stub agent object is already imported above as `docs_expert_agent_stub`).

# --- Tool Stubs (for navigation, these are simple) ---
async def navigate_to_url_stub(url: str) -> str:
    """Navigates the browser to the specified URL."""
    logger.info(f"--- ROOT AGENT called NAVIGATE_TO_URL (STUB) ---")
    logger.info(f"URL: {url}")
    return f"Navigation to {url} successful."

# --- The Agent's Prompt (Its "Brain") ---
ROOT_AGENT_INSTRUCTION = """
You are the master controller for a web browsing AI. Your primary job is to act as a router.
You will be given a user's request and the current URL of the web page.

Your ONLY task is to delegate the request to the correct specialist agent or tool:
- If the current URL is a Google Sheets page (`docs.google.com/spreadsheets`), you MUST use the `google_sheets_expert_agent`.
- If the current URL is a Google Docs page (`docs.google.com/document`), you MUST use the `google_docs_expert_agent`. 
- If the current URL contains '/vscode/workbench/notebook/', you MUST use the `jupyter_expert_agent`.
- If the user asks to go to a new website, you MUST use the `navigate_to_url_stub`.
- For any other website or task, respond that you do not yet have a specialized agent for it.
You are a high-level routing agent. Your ONLY job is to delegate a task to the correct specialist sub-agent based on the application context provided.

You will be given a JSON object containing the `application` and the `prompt`.
- If the `application` is 'google_sheets', you MUST call the `google_sheets_expert_agent` and pass the original `prompt` to it.
- If the task is to navigate, you MUST call `navigate_to_url`.

Do not respond conversationally. Your only output should be a tool call.
"""

# --- The Agent Definition ---
root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-flash",
    description="A high-level routing agent that delegates tasks to specialist sub-agents based on the application context.",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[
        AgentTool(sheets_expert_agent_instance),
        AgentTool(docs_expert_agent_stub),
        navigate_to_url_stub,  # simple function tool
    ]
)
