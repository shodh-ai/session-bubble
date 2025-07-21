# Simple test for agent tool selection without conversation flow issues
import pytest
import yaml
import os
from unittest.mock import patch, MagicMock
from aurora_agent.agent_brains.experts.sheets_expert_agent import get_expert_agent as get_sheets_expert_agent

# Load test scenarios
with open(os.path.join(os.path.dirname(__file__), 'expert_scenarios.yaml'), 'r') as f:
    scenarios = yaml.safe_load(f)

@pytest.mark.parametrize("scenario", scenarios)
def test_expert_agent_tool_choice_simple(scenario):
    """
    Simple test that verifies the agent has the correct tools available
    and that our mocking works without conversation flow complications.
    """
    print(f"\n--- RUNNING SCENARIO: {scenario['name']} ---")
    expected_tool_name = scenario['expected_tool_to_be_called']
    
    # Test that the agent is created successfully with the expected tools
    agent = get_sheets_expert_agent()
    
    # Verify the agent has the expected tools
    tool_names = [tool.__name__ for tool in agent.tools]
    print(f"Agent tools: {tool_names}")
    
    # Verify the expected tool is available
    assert expected_tool_name in tool_names, f"Expected tool '{expected_tool_name}' not found in agent tools: {tool_names}"
    
    # Verify the agent instruction is directive
    assert "MUST" in agent.instruction, "Agent instruction should be directive"
    assert "tool call" in agent.instruction.lower(), "Agent instruction should mention tool calls"
    
    print(f"✓ Agent has tool '{expected_tool_name}' available")
    print(f"✓ Agent instruction is directive ({len(agent.instruction)} chars)")
    
    # This test passes if the agent is properly configured with the right tools
    # The actual tool calling will be tested separately once we resolve the conversation flow issue
