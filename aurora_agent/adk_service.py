# File: session-bubble/aurora_agent/adk_service.py
# in aurora_agent/adk_service.py (FINAL, DEFINITIVE VERSION)
import logging
import uuid
import json
import re
from typing import Dict, Any

from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai.types import Content, Part

from .agent_brains.root_agent import get_expert_agent # Simplified import
from .browser_manager import browser_manager
from .agent_brains.experts.sheets_expert_agent import set_extracted_sheet_name

logger = logging.getLogger(__name__)

async def execute_browser_mission(mission_payload: Dict[str, Any]) -> Dict[str, Any]:
    mission_prompt = mission_payload.get("mission_prompt")
    application = mission_payload.get("application")
    context = mission_payload.get("session_context", {})
    user_id = context.get("user_id", "default_user")

    if not mission_prompt or not application:
        return {"status": "ERROR", "result": "Payload must include 'application' and 'mission_prompt'."}

    logger.info(f"--- Starting Mission for app '{application}': {mission_prompt} ---")
    print(f"\n=== BROWSER STARTUP DEBUG ===")
    print(f"About to start browser with headless=False...")
    await browser_manager.start_browser(headless=False)  # Visible browser for debugging
    print(f"Browser startup completed. Browser instance: {browser_manager.browser_instance}")
    print(f"Browser context: {browser_manager.context}")
    
    # Navigate to the Google Sheets URL to make browser window visible
    sheets_url = context.get("current_url") if context else None
    if sheets_url:
        print(f"Navigating to Google Sheets URL: {sheets_url}")
        await browser_manager.navigate(sheets_url)
        print(f"Navigation completed. Browser should now be visible.")
    else:
        print(f"No sheets URL found in session context")
    print(f"==============================\n")
    
    try:
        expert_agent = get_expert_agent()
        
        # Debug: Log agent details
        print(f"\n=== AGENT DEBUG INFO ===")
        print(f"Agent name: {expert_agent.name}")
        print(f"Agent model: {expert_agent.model}")
        print(f"Agent tools count: {len(expert_agent.tools) if hasattr(expert_agent, 'tools') else 'No tools attr'}")
        if hasattr(expert_agent, 'tools'):
            tool_names = [getattr(tool, '__name__', str(tool)) for tool in expert_agent.tools]
            print(f"Tool names: {tool_names}")
        print(f"Agent instruction preview: {expert_agent.instruction[:100]}...")
        print(f"========================\n")
        
        runner = Runner(
            agent=expert_agent,
            app_name="aurora_agent",
            session_service=InMemorySessionService(),
        )
        session = await runner.session_service.create_session(app_name="aurora_agent", user_id=user_id)
        
        # Smart routing logic: distinguish between sheet creation and other missions
        import re
        
        # Check if this is a sheet creation mission vs using existing sheet for other actions
        is_sheet_creation = bool(re.search(r"create.*?(?:new\s+)?sheet|add.*?sheet|make.*?sheet", mission_prompt, re.IGNORECASE))
        is_chart_creation = bool(re.search(r"create.*?chart|insert.*?chart|add.*?chart|chart.*?via.*?menu", mission_prompt, re.IGNORECASE))
        is_using_existing_sheet = bool(re.search(r"using.*?sheet.*?named|in.*?sheet.*?named|from.*?sheet.*?named", mission_prompt, re.IGNORECASE))
        
        # Extract sheet name for sheet creation missions only
        extracted_sheet_name = None
        if is_sheet_creation and not is_chart_creation and not is_using_existing_sheet:
            sheet_name_match = re.search(r"sheet.*?named\s+['\"]([^'\"]+)['\"]|sheet.*?called\s+['\"]([^'\"]+)['\"]|create.*?['\"]([^'\"]+)['\"].*?sheet", mission_prompt, re.IGNORECASE)
            if sheet_name_match:
                extracted_sheet_name = sheet_name_match.group(1) or sheet_name_match.group(2) or sheet_name_match.group(3)
        
        if extracted_sheet_name:
            # Set the extracted sheet name in the agent context to bypass LLM parameter extraction
            set_extracted_sheet_name(extracted_sheet_name)
            imperative_prompt = f"""Please create a new sheet. The sheet name has been extracted and will be used automatically. Call create_new_sheet_in_spreadsheet() now."""
        else:
            # For all other missions (including chart creation), frame as direct user request
            imperative_prompt = f"Please help me with this task: {mission_prompt}"
        
        logger.info(f"Sending to agent: {imperative_prompt}")
        print(f"\n=== DEBUG: SENDING TO AGENT ===")
        print(f"Original mission prompt: {mission_prompt}")
        print(f"Extracted sheet name: {extracted_sheet_name}")
        print(f"Final user request to agent:")
        print(f"---")
        print(imperative_prompt)
        print(f"---")
        print(f"===============================\n")
        new_message_content = Content(parts=[Part(text=imperative_prompt)])
        
        final_agent_response = "Mission completed without a tool call."
        tool_was_called = False
        
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=new_message_content,
        ):
            logger.info(f"ADK Event: {event.author}")
            print(f"\n--- ADK EVENT DEBUG ---")
            print(f"Event author: {event.author}")
            print(f"Event has function calls: {bool(event.get_function_calls())}")
            if event.get_function_calls():
                print(f"Function calls: {event.get_function_calls()}")
            if event.content and event.content.parts:
                print(f"Event content parts count: {len(event.content.parts)}")
                if event.content.parts and hasattr(event.content.parts[0], 'text') and event.content.parts[0].text:
                    print(f"Event text: {event.content.parts[0].text[:200]}...")
                else:
                    print(f"Event has no text content (likely function call event)")
            print(f"----------------------\n")
            
            if event.get_function_calls():
                tool_was_called = True
                logger.info("Agent made a tool call.")
            if event.author != "tool" and event.content and event.content.parts and hasattr(event.content.parts[0], 'text') and event.content.parts[0].text:
                 final_agent_response = event.content.parts[0].text
        
        # The mission is only successful if a tool was actually used.
        if not tool_was_called:
            print(f"\n=== MISSION FAILURE DEBUG ===")
            print(f"Tool was called: {tool_was_called}")
            print(f"Final agent response: {final_agent_response}")
            print(f"==============================\n")
            return {"status": "ERROR", "result": f"Agent failed to call a tool. Final response: {final_agent_response}"}
        
        print(f"\n=== MISSION SUCCESS ===")
        print(f"Tool was called: {tool_was_called}")
        print(f"Final result: {final_agent_response}")
        print(f"========================\n")
        return {"status": "SUCCESS", "result": final_agent_response}

    except Exception as e:
        logger.error(f"An error occurred during the mission: {e}", exc_info=True)
        return {"status": "ERROR", "result": str(e)}
    finally:
        await browser_manager.close_browser()
        logger.info("--- Mission Complete: Browser closed. ---")


async def _execute_fallback_action(mission_prompt: str) -> dict:
    """Execute fallback action when ADK runner fails due to conversation flow issues."""
    import re
    from aurora_agent.tools.sheets import get_sheets_tool_instance
    
    logger.info(f"Executing fallback action for mission: {mission_prompt}")
    
    # Check if this is a sheet creation mission
    if "create" in mission_prompt.lower() and "sheet" in mission_prompt.lower():
        # Extract sheet name from the mission prompt - handle various formats
        match = re.search(r"sheet named ['\"]([^'\"]+)['\"]|named ['\"]([^'\"]+)['\"]|sheet ['\"]([^'\"]+)['\"]|create.*?['\"]([^'\"]+)['\"]|create.*?sheet\s+([A-Za-z0-9_]+)", mission_prompt, re.IGNORECASE)
        if match:
            # Get the first non-None group
            sheet_title = None
            for group in match.groups():
                if group:
                    sheet_title = group
                    break
            if sheet_title:
                sheet_title = sheet_title.strip()
                logger.info(f"Attempting to create sheet: {sheet_title}")
                
                # Use the sheets tool directly
                sheets_tool = get_sheets_tool_instance()
                if sheets_tool:
                    try:
                        result = await sheets_tool.create_sheet(sheet_title)
                        logger.info(f"Fallback sheet creation result: {result}")
                        
                        # Parse the result to check if it was successful
                        if "SUCCESS" in result or "successfully" in result.lower():
                            return {
                                "status": "SUCCESS", 
                                "result": f"Sheet '{sheet_title}' created successfully via fallback"
                            }
                        else:
                            return {
                                "status": "ERROR", 
                                "result": f"Fallback sheet creation failed: {result}"
                            }
                    except Exception as e:
                        logger.error(f"Fallback sheet creation error: {e}")
                        return {
                            "status": "ERROR", 
                            "result": f"Fallback sheet creation exception: {str(e)}"
                        }
    
    return {
        "status": "ERROR", 
        "result": "No suitable fallback action found for this mission"
    }