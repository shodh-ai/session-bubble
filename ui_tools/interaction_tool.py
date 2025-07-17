# in aurora_agent/ui_tools/interaction_tool.py

import asyncio
import json
import logging
import re
from playwright.async_api import Page
from .annotation_helpers import highlight_element, remove_annotations

logger = logging.getLogger(__name__)

# --- ADK Agent Definition (The Real One) ---
# When you are ready to remove the placeholder, you will uncomment this
# and delete the placeholder classes.
# from google.adk.agents import Agent
#
# INTERACT_AGENT_PROMPT = """
# You are an expert Playwright script writer...
# MANDATORY VISUALIZATION: Before any action... you MUST first call `await highlight_element(page, your_target_locator)`.
# ... (the rest of your detailed prompt) ...
# """
#
# interact_agent = Agent(
#     name="interact_agent",
#     model="gemini-2.5-flash",
#     description="Generates a Playwright script to interact with a web page's UI.",
#     instruction=INTERACT_AGENT_PROMPT,
#     tools=[]
# )

# --- Placeholder Agent for Testing (Our Current Focus) ---

class MockAgentResponsePart:
    def __init__(self, text):
        self.text = text

class MockAgentResponseContent:
    def __init__(self, text):
        self.parts = [MockAgentResponsePart(text)]

class MockAgentResponse:
    def __init__(self, text):
        self.content = MockAgentResponseContent(text)

# in aurora_agent/ui_tools/interaction_tool.py

class PlaceholderInteractAgent:
    """
    A placeholder that intelligently simulates the real interact_agent.
    """
    async def run_async(self, user_prompt: str, element_info_list: list):
        logger.warning("Using a placeholder 'interact_agent'. It will dynamically find the locator.")
        
        target_locator_str = "page.locator('body')"  # Default fallback
        keyword_to_find = ""

        # --- This simulates the LLM's keyword extraction ---
        # Use regex to find the target element in prompts like "Click the 'Bold' button"
        match = re.search(r"click the '([^']*)' button", user_prompt, re.IGNORECASE)
        if match:
            keyword_to_find = match.group(1)
        elif "bold" in user_prompt.lower(): # Fallback for simpler prompts
            keyword_to_find = "Bold"

        if keyword_to_find:
            found_element = False
            # Now, search the structured list for the keyword
            for element in element_info_list:
                # Search in multiple fields for a more robust match
                search_text = (
                    str(element.get("description", "")) + " " +
                    str(element.get("aria_label", "")) + " " +
                    str(element.get("role", "")) + " " +
                    str(element.get("text", ""))
                ).lower()

                if keyword_to_find.lower() in search_text:
                    target_locator_str = element["playwright_locator"]
                    logger.info(f"Found target locator for '{keyword_to_find}' in element: {element}")
                    found_element = True
                    break
            
            if not found_element:
                logger.warning(f"Could not find an element matching keyword: '{keyword_to_find}'. Defaulting to body.")
        else:
             logger.error(f"Placeholder could not determine keyword from prompt: '{user_prompt}'")

        # Generate the final Playwright code
        generated_code = (
            f"# Code generated for prompt: '{user_prompt}'\n"
            f"target_locator = {target_locator_str}\n"
            f"await target_locator.wait_for(state='visible', timeout=10000)\n"
            f"await highlight_element(page, target_locator)\n"
            f"await target_locator.click()\n"
            f"await remove_annotations(page)"
        )
        
        return MockAgentResponse(generated_code)

# Instantiate the placeholder for use in tests
interact_agent = PlaceholderInteractAgent()

# --- End of Placeholder Section ---


async def execute_interaction(page: Page, interaction_code: str):
    """
    Executes a string of Playwright code, making custom helper functions available.
    """
    if not page:
        return {"success": False, "error": "Execution failed: Browser page is not available."}

    try:
        # This is the safe way to execute dynamic code, passing helpers as arguments.
        code_to_exec = (
            "async def __interaction(page, highlight_element, remove_annotations):\n" +
            "\n".join(f"    {line}" for line in interaction_code.splitlines())
        )
        
        exec_scope = {}
        exec(code_to_exec, exec_scope)
        interaction_func = exec_scope['__interaction']
        
        await interaction_func(page, highlight_element, remove_annotations)

        return {"success": True, "message": "Interaction executed successfully."}
    except Exception as e:
        error_message = f"An error occurred during UI interaction: {e}"
        logger.error(error_message)
        return {"success": False, "error": error_message}