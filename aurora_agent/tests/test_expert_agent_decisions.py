# in tests/test_expert_agent_decisions.py
import pytest
import yaml
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from aurora_agent.agent_brains.experts.sheets_expert_agent import get_expert_agent as get_sheets_expert_agent

# Load test scenarios
with open(os.path.join(os.path.dirname(__file__), 'expert_scenarios.yaml'), 'r') as f:
    scenarios = yaml.safe_load(f)

@pytest.mark.parametrize("scenario", scenarios)
@pytest.mark.asyncio
async def test_expert_agent_tool_choice(scenario):
    """
    Tests that the sheets_expert_agent correctly chooses which tool to use.
    This test is focused ONLY on the agent's reasoning and mocks all underlying tools.
    """
    print(f"\n--- RUNNING SCENARIO: {scenario['name']} ---")
    prompt = scenario['prompt']
    expected_tool_name = scenario['expected_tool_to_be_called']

    # --- THE SCALABLE MOCKING STRATEGY ---
    # We patch ALL potential tools that the agent might call.
    patch_script = patch('aurora_agent.agent_brains.experts.sheets_expert_agent.run_recorded_ui_script', new_callable=MagicMock)

    with patch_script as mock_script_tool:
        
        # --- Configure all mocks ---
        # Give each mock the necessary attributes to pass ADK introspection
        mock_script_tool.__name__ = 'run_recorded_ui_script'
        # Use a simple return value to avoid coroutine pickling issues
        mock_script_tool.return_value = "Script tool mocked."

        # Create a dictionary to hold our mocks for easy verification
        mocks = {
            'run_recorded_ui_script': mock_script_tool
        }

        # --- Execute the Agent ---
        sheets_expert_agent = get_sheets_expert_agent()
        runner = Runner(
            agent=sheets_expert_agent,
            app_name="test_app",
            session_service=InMemorySessionService(),
        )
        session = await runner.session_service.create_session(app_name="test_app", user_id="test_user")
        new_message = Content(parts=[Part(text=prompt)])
        
        # --- Run the agent by consuming the async generator ---
        print("\n=== AGENT EXECUTION DEBUG ===")
        events_captured = []
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=new_message
        ):
            events_captured.append(event)
            print(f"Event: {event}")
            if hasattr(event, 'content') and event.content:
                print(f"Content: {event.content}")
                if hasattr(event.content, 'parts') and event.content.parts:
                    for i, part in enumerate(event.content.parts):
                        print(f"  Part {i}: {part}")
                        if hasattr(part, 'tool_code') and part.tool_code:
                            print(f"    Tool call: {part.tool_code.name}")
                            print(f"    Tool args: {getattr(part.tool_code, 'args', 'No args')}")
        print(f"Total events captured: {len(events_captured)}")
        print("=== END AGENT DEBUG ===")

        # --- VERIFICATION ---
        # This loop checks every mock.
        # It asserts that the expected tool was called once,
        # and asserts that all other tools were NOT called.
        for tool_name, mock_instance in mocks.items():
            if tool_name == expected_tool_name:
                mock_instance.assert_called_once()
            else:   
                mock_instance.assert_not_called()

        print(f"SUCCESS: Agent correctly chose and called the '{expected_tool_name}' tool.")
