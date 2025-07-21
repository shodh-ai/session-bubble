# in tests/test_agent_factory.py
import pytest
from unittest.mock import Mock
from aurora_agent.agent_brains.experts.docs_expert_agent import create_docs_expert_agent

def test_factory_creates_agent_with_correct_tools():
    """
    Verify that the factory correctly injects the provided tools
    into the created agent's tool list.
    """
    # Create a mock DocsTool-like object with the expected methods
    mock_docs_api_tool = Mock()
    mock_docs_api_tool.insert_text = Mock()
    mock_docs_api_tool.get_document_content = Mock()
    mock_docs_api_tool.get_document_formatting = Mock()
    
    # Create a mock UI interaction function
    mock_ui_interaction_tool = Mock()

    # Call the factory to build the agent
    agent = create_docs_expert_agent(
        docs_api_tool=mock_docs_api_tool,
        ui_interaction_tool=mock_ui_interaction_tool
    )

    # Verify the agent was created
    assert agent is not None, "Factory failed to create an agent."
    
    # The factory should create 4 tools:
    # 1. The UI interaction tool
    # 2. insert_text method
    # 3. get_document_content method
    # 4. get_document_formatting method
    assert len(agent.tools) == 4, f"Expected 4 tools, but found {len(agent.tools)}."
    
    # Verify the tools are correctly assigned
    assert agent.tools[0] == mock_ui_interaction_tool
    assert agent.tools[1] == mock_docs_api_tool.insert_text
    assert agent.tools[2] == mock_docs_api_tool.get_document_content
    assert agent.tools[3] == mock_docs_api_tool.get_document_formatting
    
    print("\nSUCCESS: The agent factory correctly created an agent with the injected mock functions.")