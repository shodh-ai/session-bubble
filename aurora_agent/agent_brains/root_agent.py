# in aurora_agent/agent_brains/root_agent.py
import logging
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

# Import the specialist agent you just created
from .experts.sheets_expert_agent import sheets_expert_agent

logger = logging.getLogger(__name__)

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
- If the user asks to go to a new website, you MUST use the `navigate_to_url_stub`.
- For any other website or task, respond that you do not yet have a specialized agent for it.
"""

# --- The Agent Definition ---
root_agent = Agent(
    name="root_agent",
    model="gemini-1.5-flash",
    description="A high-level routing agent that delegates tasks to specialist sub-agents based on the application context.",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[
        # The most important tool is the specialist agent itself.
        AgentTool(sheets_expert_agent),
        
        # It also has the basic navigation tool.
        navigate_to_url_stub,
    ]
)
