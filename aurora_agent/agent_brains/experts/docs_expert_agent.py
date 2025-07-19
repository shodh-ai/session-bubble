# in aurora_agent/agent_brains/experts/docs_expert_agent.py
from __future__ import annotations
import logging
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
logger = logging.getLogger(__name__)

# --- The Instruction Prompt (Shared and Constant) ---
DOCS_EXPERT_INSTRUCTION = """
You are a single-action tool-using agent for Google Docs. Your ONLY job is to execute the user's request by calling a single tool.

**CRITICAL CONTEXT:**
- The user's prompt will begin with the `document_id`.
- You MUST extract this `document_id` and pass it as the first argument to ANY tool you call.

**TOOL SELECTION RULES:**
- For FORMATTING tasks (headings, bold, italic, colors, styles): Use `perform_visual_ui_action`
- For CONTENT tasks (inserting text, reading content): Use the appropriate API tool
- Examples of formatting: "Make text Heading 1", "Change color to red", "Make text bold"
- Examples of content: "Insert text", "Get document content"

**CRITICAL DIRECTIVE:**
1.  Read the user's request (e.g., "document_id: 123xyz, Make the title a Heading 1").
2.  Determine if this is a FORMATTING task or CONTENT task.
3.  Choose the appropriate tool based on the rules above.
4.  Call the tool, providing the `document_id` and any other necessary parameters.

**YOU MUST NOT:**
- Ask clarifying questions or respond conversationally. Your ENTIRE response MUST be a single tool call.
"""

# --- 1. The "Live" Factory for Your Real Application ---
def create_docs_expert_agent(docs_api_tool, ui_interaction_tool):
    """
    Builds the docs_expert_agent with LIVE, REAL tool instances.
    It unpacks the methods from the DocsTool object.
    """
    # Wrap the provided UI tool so that the exposed function name matches the instruction
    async def perform_visual_ui_action(prompt: str):
        """Delegates to the real UI interaction tool to perform a visual Docs action."""
        return await ui_interaction_tool(prompt)

    agent_tools = [
        perform_visual_ui_action,  # Visual UI tool
        # API tools
        docs_api_tool.insert_text,
        docs_api_tool.get_document_content,
        docs_api_tool.get_document_formatting,
    ]
    
    agent_instance = Agent(
        name="google_docs_expert_agent",
        model="gemini-2.5-flash",
        description="A specialist agent for Google Docs.",
        instruction=DOCS_EXPERT_INSTRUCTION,
        tools=agent_tools
    )

    # Build and attach a quick lookup dict expected by some tests
    from types import SimpleNamespace
    tool_mapping = {}
    for tool in agent_tools:
        if isinstance(tool, AgentTool):
            tool_mapping[tool.name] = tool
        else:
            # Plain function / method. Create a lightweight wrapper exposing .func.
            tool_mapping[tool.__name__] = SimpleNamespace(func=tool)
    object.__setattr__(agent_instance, "tools_by_name", tool_mapping)

    return agent_instance

# --- 2. The "Stub" Agent for Simple Imports and Hierarchy Tests ---
async def _ui_stub(prompt: str) -> str:
    """Use this tool for any task that requires VISUAL demonstration."""
    logger.info(f"STUB UI TOOL CALLED with prompt: {prompt}")
    return "Success: UI interaction demonstrated."

async def _api_stub(prompt: str) -> str:
    """Use this tool for any EFFICIENT, NON-VISUAL manipulation."""
    logger.info(f"STUB API TOOL CALLED with prompt: {prompt}")
    return "Success: API operation completed."

# A simple, self-contained agent that uses the stubs above.
# It does NOT use the factory.
docs_expert_agent_stub = Agent(
    name="google_docs_expert_agent_stub",
    model="gemini-2.5-flash",
    description="A stubbed specialist agent for Google Docs.",
    instruction=DOCS_EXPERT_INSTRUCTION,
    tools=[_ui_stub, _api_stub]
)