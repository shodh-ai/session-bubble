# in test_brains.py
import asyncio
import os
import logging
from dotenv import load_dotenv
from pydantic import ConfigDict
from google.adk.events.event import Event
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai.types import Content, Part

# Import your new root agent
from aurora_agent.agent_brains.root_agent import root_agent


# Create a mutable version of the Event class to allow monkey-patching.
class MutableEvent(Event):
    model_config = ConfigDict(extra='allow')

load_dotenv()

# Set up basic logging
logging.basicConfig(level=logging.INFO)

# This is the final, correct fix.
# The google-adk library does not correctly add the user's first message to the request.
# We are patching the method responsible for calling the LLM (`_call_llm_async`)
# to ensure the user's content is added to the request payload before being sent.
from google.adk.flows.llm_flows import base_llm_flow

async def patched_call_llm_async(self, invocation_context):
    # First, build the request as the library normally would (but it misses the user content).
    llm_request = self._build_llm_request(invocation_context)

    # Manually add the user's content to the request.
    if invocation_context.new_message and invocation_context.new_message.content:
        llm_request.contents.append(invocation_context.new_message.content)

    # Now, proceed with calling the LLM with the corrected request.
    async for llm_response in self._llm.generate_content_async(
        llm_request=llm_request, stream=self._stream
    ):
        yield self._build_event_from_llm_response(llm_response)

# Apply the patch.
base_llm_flow.BaseLlmFlow._call_llm_async = patched_call_llm_async


async def main():
    # This simulates the context coming from LangGraph
    mission_payload = {
        "application": "google_sheets",
        "mission_prompt": "In the sales data, find the total sales for the 'North' region and make that cell bold.",
        "session_context": { "user_id": "brosuf_test" }
    }

    prompt = mission_payload["mission_prompt"]
    user_id = mission_payload["session_context"]["user_id"]
    
    # We need to add the URL context to the prompt for the root_agent
    # This is how we tell it where we are.
    full_prompt_with_context = f"""
    Current URL is: https://docs.google.com/spreadsheets/d/12345
    User request is: {prompt}
    """

    session_service = InMemorySessionService()
    await session_service.create_session(session_id=user_id, user_id=user_id, app_name="aurora_agent_test")

    print("--- STARTING AGENT HIERARCHY TEST ---")

    runner = Runner(
        agent=root_agent,
        app_name="aurora_agent_test",
        session_service=session_service
    )
    new_content = Content(parts=[Part(text=full_prompt_with_context)])
    new_event = MutableEvent(author="user", content=new_content)
    # Monkey-patch the event object to add the 'parts' attribute the runner expects.
    new_event.parts = new_content.parts
    async for event in runner.run_async(user_id=user_id, session_id=user_id, new_message=new_event):
        # A more robust check for content
        if event.content and event.content.parts:
            # Check for text part
            if event.content.parts[0].text:
                print(f"AGENT FINAL RESPONSE: {event.content.parts[0].text}")
            # Check for tool_code part
            elif event.content.parts[0].tool_code:
                tool_name = event.content.parts[0].tool_code.name
                tool_args = event.content.parts[0].tool_code.args
                print(f"AGENT ACTION: Called tool '{tool_name}' with args: {tool_args}")

if __name__ == "__main__":
    # This is required for the ADK to work correctly
    # You might need to install `python-dotenv` and `nest_asyncio`
    # pip install python-dotenv nest_asyncio
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
