# in aurora_agent/app.py
import logging
import asyncio
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.events.event import Event
from google.genai.types import Content, Part
from aurora_agent.tools.sheets import get_sheets_tool_instance  # Factory function to get SheetsTool instance
from aurora_agent.ui_tools.interaction_tool import live_ui_interaction_tool # The real UI tool
# Import the brain you built
from .agent_brains.root_agent import root_agent

# Import the browser manager
from .browser_manager import browser_manager
from fastapi import FastAPI

app = FastAPI()


logger = logging.getLogger(__name__)

# --- Critical ADK Patch ---
# The google-adk library does not correctly add the user's first message to the request.
# We are patching the method responsible for calling the LLM (`_call_llm_async`)
# to ensure the user's content is added to the request payload before being sent.
from google.adk.flows.llm_flows import base_llm_flow


@app.post("/run-mission")
async def run_mission(payload: dict):
    session_id = payload.get("session_id", "default")
    return await execute_browser_mission(payload, session_id)

    
async def patched_call_llm_async(self, invocation_context):
    llm_request = self._build_llm_request(invocation_context)
    if invocation_context.new_message and invocation_context.new_message.content:
        llm_request.contents.append(invocation_context.new_message.content)
    async for llm_response in self._llm.generate_content_async(
        llm_request=llm_request, stream=self._stream
    ):
        yield self._build_event_from_llm_response(llm_response)

# Apply the patch
base_llm_flow.BaseLlmFlow._call_llm_async = patched_call_llm_async
# --- End of Patch ---


# --- Main Executor Function ---
async def execute_browser_mission(mission_payload: dict, session_id: str) -> dict:
    logger.info(f"--- ADK MISSION STARTING (Session: {session_id}) ---")

    try:
        await browser_manager.start_browser()
        logger.info("Browser is running.")
    except Exception as e:
        logger.error(f"CRITICAL: Failed to start browser: {e}", exc_info=True)
        return {"status": "ERROR", "result": f"Browser failed to start: {e}"}

    prompt = mission_payload.get("mission_prompt", "No prompt provided.")
    context = mission_payload.get("session_context", {})
    user_id = context.get("user_id", "default_user")
    current_url = context.get("current_url", "")

    prompt_with_context = f"Current Page URL: {current_url}\nUser's Mission: {prompt}"

    logger.info(f"Invoking root_agent with enriched prompt...")

    # Initialize the runner with a session service.
    session_service = InMemorySessionService()
    await session_service.create_session(session_id=session_id, user_id=user_id, app_name="aurora_agent")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="aurora_agent")

    # +++ THIS IS THE CRITICAL FIX +++
    # We build the structured Event object instead of passing a raw string.
    new_content = Content(parts=[Part(text=prompt_with_context)])
    new_message_event = MutableEvent(author="user", content=new_content)
    # The runner also expects a top-level 'parts' attribute, so we add it.
    new_message_event.parts = new_content.parts
    # +++ END OF FIX +++
    
    final_result = "No textual output from agent."
    try:
        # --- THIS IS THE CORRECTED LOOP ---
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message_event
        ):
            logger.info(f"[DEBUG] Raw event from runner: {event}")

            # The most robust way to check for the final response is to look for
            # an event that has content but is NOT a tool call.
            # The final textual response from the agent is a specific kind of event.
            
            is_tool_call = event.content and event.content.parts and hasattr(event.content.parts[0], 'tool_code')
            has_text = event.content and event.content.parts and hasattr(event.content.parts[0], 'text')

            if has_text and not is_tool_call:
                # This is likely the final conversational response from the agent.
                final_result = event.content.parts[0].text
                logger.info(f"Captured agent's final textual response: {final_result}")
            elif is_tool_call:
                # This is an intermediate step where the agent is using a tool.
                tool_call = event.content.parts[0].tool_code
                tool_name = tool_call.name
                tool_args = tool_call.args if hasattr(tool_call, 'args') else None
                logger.info(f"Agent is calling tool: {tool_name} with args: {tool_args}")
            
        # The loop finishes when the agent's run is complete.
        # The last captured text is our final result.
        # --- END OF CORRECTED LOOP ---
                    
        logger.info(f"ADK mission completed. Final result: {final_result}")
        return {"status": "SUCCESS", "result": final_result}

    except Exception as e:
        logger.error(f"An exception occurred during ADK agent execution: {e}", exc_info=True)
        return {"status": "ERROR", "result": f"Agent execution failed: {e}"}