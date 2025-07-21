# in tests/test_agent_hierarchy.py
import pytest
from unittest.mock import patch

# Import the agent definitions
from aurora_agent.agent_brains.root_agent import root_agent
from aurora_agent.agent_brains.experts.docs_expert_agent import docs_expert_agent_stub, create_docs_expert_agent


def test_root_agent_has_correct_expert_tools():
    """Verifies the root_agent's tools list is correctly configured."""
    # This test checks the live, imported root_agent
    agent_tool_names = [
        tool.agent.name for tool in root_agent.tools if hasattr(tool, 'agent')
    ]
    assert 'sheets_expert_agent' in agent_tool_names, "Sheets expert not found in root_agent tools!"
    assert 'google_docs_expert_agent_stub' in agent_tool_names, "Docs expert not found in root_agent tools!"
    print("\nSUCCESS: root_agent contains the correct expert agents.")


# CORRECTED PATCH TARGETS
@patch('aurora_agent.agent_brains.experts.docs_expert_agent._ui_stub', autospec=True)
@patch('aurora_agent.agent_brains.experts.docs_expert_agent._api_stub', autospec=True)
def test_docs_expert_chooses_ui_tool(mock_api_tool, mock_ui_tool):
    """Verifies the tool descriptions in the docs_expert_agent are correct."""
    # This test now focuses on verifying the prompts that guide the LLM.
    # The ADK wraps functions and uses their docstrings as descriptions.
    ui_tool_description = docs_expert_agent_stub.tools[0].__doc__
    api_tool_description = docs_expert_agent_stub.tools[1].__doc__
    
    assert "VISUAL demonstration" in ui_tool_description
    assert "NON-VISUAL" in api_tool_description
    print("\nSUCCESS: Docs expert tools have correct descriptions to guide the LLM.")


def test_factory_creates_agent_with_correct_tools():
    """
    Verify the factory correctly injects the provided tool instances
    into the created agent's tool list.
    """
    # Create mock objects that match what the factory expects
    from unittest.mock import Mock
    
    # Mock DocsTool object with the expected methods
    mock_docs_api_tool = Mock()
    mock_docs_api_tool.insert_text = Mock()
    mock_docs_api_tool.get_document_content = Mock()
    mock_docs_api_tool.get_document_formatting = Mock()
    
    # Mock UI interaction function
    async def mock_ui_interaction_func(): pass
    
    # Call the factory to build the agent
    agent = create_docs_expert_agent(
        docs_api_tool=mock_docs_api_tool, 
        ui_interaction_tool=mock_ui_interaction_func
    )
    
    assert agent is not None
    # Factory creates 4 tools: 1 UI tool + 3 API methods (insert_text, get_document_content, get_document_formatting)
    assert len(agent.tools) == 4
    
    # --- THIS IS THE CORRECTED ASSERTION ---
    # We now know that agent.tools[0] IS the function itself.
    assert agent.tools[0] == mock_ui_interaction_func
    # The remaining tools should be the API methods from the mock DocsTool
    assert agent.tools[1] == mock_docs_api_tool.insert_text
    assert agent.tools[2] == mock_docs_api_tool.get_document_content
    assert agent.tools[3] == mock_docs_api_tool.get_document_formatting
    
    print("\nSUCCESS: The agent factory correctly injected the functions into the agent.")