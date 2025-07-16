# in test_mission_executor.py
import asyncio
import os
from dotenv import load_dotenv

# Import the function you just created
from aurora_agent.app import execute_browser_mission

load_dotenv()

async def main():
    # 1. This is the "Placeholder Payload" that your LangGraph will provide.
    #    You can change this to test different scenarios.
    mock_langgraph_payload = {
      "application": "google_sheets",
      "mission_prompt": "Create a new sheet named 'Q3_Results' and then write the value 'Complete' into cell A1 of that new sheet.",
      "session_context": {
        "user_id": "brosuf_test_2",
        "current_url": "https://docs.google.com/spreadsheets/d/12345"
      }
    }
    
    session_id_from_langgraph = "test_session_12345"

    print("--- STARTING MISSION EXECUTOR TEST ---")

    # 2. Call your main function, pretending to be LangGraph
    result = await execute_browser_mission(mock_langgraph_payload, session_id_from_langgraph)

    print("\n--- MISSION EXECUTOR FINISHED ---")
    print(f"Final Status: {result.get('status')}")
    print(f"Final Result: {result.get('result')}")

    # In a real test, you'd add assertions here.
    # For now, we look at the logs to verify the flow.
    assert result.get('status') == "SUCCESS"

if __name__ == "__main__":
    # This is needed to gracefully shut down the browser manager
    from aurora_agent.browser_manager import browser_manager
    try:
        asyncio.run(main())
    finally:
        asyncio.run(browser_manager.close_browser())
