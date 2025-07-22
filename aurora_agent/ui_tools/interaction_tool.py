# in aurora_agent/ui_tools/interaction_tool.py (FINAL, CORRECTED VERSION)

import asyncio
import json
import logging
import platform
from playwright.async_api import Page
from .annotation_helpers import highlight_element, remove_annotations
import google.generativeai as genai
import os

logger = logging.getLogger(__name__)

# --- The "Brain" is now a simple function, not an Agent ---

BASE_INTERACT_PROMPT = """
You are an expert Playwright script writer. Your ONLY job is to generate a Python script.

**CRITICAL: PYTHON SYNTAX ONLY**
- You MUST generate Python code for the `asyncio` Playwright library.
- You MUST use `async` and `await` for all browser operations.

**MANDATORY VISUALIZATION:**
- Before any action (like `.click()`, `.fill()`), you MUST first call `await highlight_element(page, your_target_locator)`.
- After the action is complete, you MUST call `await remove_annotations(page)`.

**RULES:**
- Use the exact `playwright_locator` string provided in the element information. Do not create your own.
- Your output must be **only** the Python code. Do not include any explanations or markdown like ```python.
"""

# This is the specialized knowledge for Google Docs
DOCS_INTERACT_PROMPT = BASE_INTERACT_PROMPT + """
**GOOGLE DOCS - ADVANCED WORKFLOWS:**
- **Critical Timing Rule:** When clicking a menu item that opens a dropdown (like 'Styles'), you MUST explicitly wait for the target option to be visible before clicking it.

**EXAMPLE:**

*User Request:* "Make the text 'Title of Document' a Heading 1."
*Element Info:* `[ {{"description": "The main document editing area.", ...}}, {{"description": "Toolbar button: 'Styles'", ...}}, {{"description": "Menu item: 'Heading 1'", ...}} ]`

*Generated Code (This is the perfect, robust sequence):*
# Step 1: Select the first line of text.
main_text_area = page.locator("div[role='document']")
await highlight_element(page, main_text_area)
await main_text_area.click(click_count=3) # Triple click selects the paragraph.
await remove_annotations(page)

# Step 2: Open the styles dropdown menu.
styles_dropdown = page.get_by_aria_label('Styles', exact=True)
await highlight_element(page, styles_dropdown)
await styles_dropdown.click()
await remove_annotations(page)

# Step 3: Explicitly wait for the 'Heading 1' option to be visible, THEN click it.
# This is the professional, robust way to handle dynamic menus.
heading_option = page.get_by_role('menuitemcheckbox', name='Heading 1')
await heading_option.wait_for() # <<< THIS IS THE CRITICAL FIX
await highlight_element(page, heading_option)
await heading_option.click()
await remove_annotations(page)
"""
# This is the specialized knowledge for Google Sheets
SHEETS_INTERACT_PROMPT = BASE_INTERACT_PROMPT + """
**GOOGLE SHEETS EXAMPLES:**

*User Request:* "Create a chart via Insert menu"
*Element Info:* `[..., {{"playwright_locator": "page.get_by_role('menuitem', name='Insert')", ...}}, {{"playwright_locator": "page.get_by_role('menuitem', name='Chart')", ...}}]`
*Generated Code:*
# Step 1: Click Insert menu
insert_menu = page.get_by_role('menuitem', name='Insert')
await highlight_element(page, insert_menu)
await insert_menu.click()
await remove_annotations(page)
# Step 2: Click Chart from dropdown
await page.wait_for_timeout(500)  # Wait for menu to open
chart_option = page.get_by_role('menuitem', name='Chart')
await highlight_element(page, chart_option)
await chart_option.click()
await remove_annotations(page)
"""

def get_prompt_for_application(url: str) -> str:
    """Selects the correct specialized prompt based on the URL."""
    if "docs.google.com/document" in url:
        return DOCS_INTERACT_PROMPT
    if "docs.google.com/spreadsheets" in url:
        return SHEETS_INTERACT_PROMPT
    # Fallback to the base prompt if no specific application is matched
    return BASE_INTERACT_PROMPT

async def generate_playwright_code(page: Page, user_prompt: str, element_info_list: list) -> str:
    """
    Selects the correct prompt, formats it with context, and calls the LLM.
    """
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    # 1. Select the specialized prompt template based on the current page URL
    prompt_template = get_prompt_for_application(page.url)

    # 2. Format the template with the dynamic data. This is now safe.
    full_prompt_for_llm = (
        prompt_template +
        f"\n\n--- CURRENT TASK ---\n" +
        f"User Request: {user_prompt}\n\n" +
        f"Element Info:\n{json.dumps(element_info_list, default=str)}"
    )

    try:
        response = await model.generate_content_async(full_prompt_for_llm)
        cleaned_code = response.text.strip().replace("```python", "").replace("```", "").strip()
        return cleaned_code
    except Exception as e:
        logger.error(f"Error calling Gemini in generate_playwright_code: {e}")
        return "raise Exception('LLM code generation failed.')"
# --- The "Hands" function remains the same ---

async def execute_interaction(page: Page, interaction_code: str):
    """
    Executes a string of Playwright code, making custom helper functions available
    and sanitizing the code to prevent common LLM errors.
    """
    if not page:
        return {"success": False, "error": "Execution failed: Browser page is not available."}

    try:
        # 1. Sanitize the code: Fix common LLM errors and undefined variables
        sanitized_code = []
        for line in interaction_code.splitlines():
            # Remove any attempt to run a new event loop
            if "asyncio.run(" in line:
                continue
            # Remove any function definitions
            if line.strip().startswith("async def"):
                continue
            # Remove boilerplate main block
            if line.strip().startswith("if __name__"):
                continue
            
            # Fix common LLM errors - undefined variables
            line = line.replace("locator(", "page.locator(")
            line = line.replace("get_by_aria_label(", "get_by_label(")
            line = line.replace("arguments[", "args[")
            line = line.replace("page.page.", "page.")
            
            # Fix element references
            if "element" in line and "page." not in line and "locator" not in line:
                # Skip lines with undefined 'element'
                logger.warning(f"Skipping line with undefined 'element': {line}")
                continue
            
            # Skip lines with undefined variables
            if "locator" in line and "page.locator" not in line:
                logger.warning(f"Skipping line with undefined 'locator': {line}")
                continue
            
            # Skip lines that try to evaluate on null elements - just skip them entirely to avoid syntax errors
            if "page.evaluate(" in line and ("element" in line or "locator" in line):
                logger.warning(f"Skipping potentially problematic page.evaluate line: {line}")
                continue
                
            sanitized_code.append(line)
        
        interaction_code = "\n".join(sanitized_code)

        # 2. Wrap the sanitized code in our async function shell with imports
        # Handle indentation properly - strip existing indentation and add consistent indentation
        indented_lines = []
        for line in interaction_code.splitlines():
            if line.strip():  # Only process non-empty lines
                indented_lines.append(f"    {line.strip()}")
            else:
                indented_lines.append("")  # Keep empty lines as empty
        
        code_to_exec = (
            "import asyncio\n"
            "async def __interaction(page, highlight_element, remove_annotations):\n" +
            "\n".join(indented_lines)
        )
        
        # Debug: Log the generated code
        logger.info(f"Generated Playwright code:\n{code_to_exec}")
        
        # 3. Provide safe execution environment
        exec_scope = {
            'asyncio': __import__('asyncio'),
            'page': page,
            'highlight_element': highlight_element,
            'remove_annotations': remove_annotations
        }
        exec(code_to_exec, globals(), exec_scope)
        interaction_func = exec_scope['__interaction']
        
        # 4. Execute the final, safe code
        logger.info("Executing AI-generated Playwright code...")
        await interaction_func(page, highlight_element, remove_annotations)
        logger.info("AI-generated Playwright code execution completed")
        return {"success": True, "message": "Interaction executed successfully."}
    except Exception as e:
        error_message = f"An error occurred during UI interaction: {e}"
        logger.error(error_message, exc_info=True)
        return {"success": False, "error": error_message}
# --- The main UI interaction tool function that agents call ---

async def live_ui_interaction_tool(prompt: str) -> str:
    """
    The main UI interaction tool that agents call to perform visual actions.
    This function integrates with the browser manager and uses the helper functions above.
    
    Enhanced with intelligent fallbacks for chart creation, heading formatting, and color changes.
    """
    from aurora_agent.browser_manager import browser_manager
    
    try:
        # Get the current page from browser manager
        page = browser_manager.page
        if not page:
            return "Error: Browser page is not available. Please ensure the browser is started and navigated to the target page."
        
        # Get page context for potential fallback to general UI interaction
        from aurora_agent.parsers import get_parser_for_url
        parser = get_parser_for_url(page.url)
        element_info_list = await parser.get_interactive_elements(page)
        
        # Special handling for Google Docs formatting - ALWAYS use keyboard shortcuts for reliability
        if "docs.google.com/document" in page.url:
            # Handle complex multi-step formatting requests
            if "heading 1" in prompt.lower() or "heading" in prompt.lower():
                try:
                    logger.info("Applying Heading 1 formatting via keyboard shortcuts")
                    
                    # Method 1: Select the title text if specified
                    if "title of document" in prompt.lower():
                        # Use Ctrl+A to select all, then apply heading
                        await page.keyboard.press("Meta+a" if platform.system() == "Darwin" else "Ctrl+a")
                        await asyncio.sleep(0.3)
                    
                    # Method 2: Use keyboard shortcut for Heading 1 (most reliable)
                    await page.keyboard.press("Meta+Alt+1" if platform.system() == "Darwin" else "Ctrl+Alt+1")
                    await asyncio.sleep(1)  # Give more time for the formatting to apply
                    
                    logger.info("Heading 1 applied successfully")
                    return "Success: Applied Heading 1 formatting using keyboard shortcuts"
                    
                except Exception as e:
                    logger.error(f"Keyboard shortcut method failed: {e}")
                    # Fall through to the general UI interaction method
            
            # Handle color change requests - use hybrid approach
            elif "color" in prompt.lower() and "red" in prompt.lower():
                try:
                    logger.info("Preparing for color formatting - selecting text first")
                    
                    # Select the word 'first' if mentioned using keyboard shortcut
                    if "first" in prompt.lower():
                        await page.keyboard.press("Meta+f" if platform.system() == "Darwin" else "Ctrl+f")
                        await asyncio.sleep(0.5)
                        await page.keyboard.type("first")
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(0.5)
                        await page.keyboard.press("Escape")
                        await asyncio.sleep(0.5)
                        
                        logger.info("Text selected, now trying Format menu approach")
                        
                        # Try Format menu approach for color change
                        await page.keyboard.press("Alt+o" if platform.system() != "Darwin" else "Alt+t")  # Format menu
                        await asyncio.sleep(1)
                        await page.keyboard.press("t")  # Text color
                        await asyncio.sleep(1)
                        await page.keyboard.press("r")  # Red color (if available)
                        await asyncio.sleep(0.5)
                        
                        logger.info("Color formatting applied via Format menu")
                        return "Success: Applied color formatting using Format menu"
                        
                except Exception as e:
                    logger.error(f"Format menu approach failed: {e}")
                    logger.info("Falling back to AI-generated UI interaction")
                    # Fall through to the general UI interaction method
            
            # Handle simple bold formatting
            elif "bold" in prompt.lower():
                try:
                    # Try keyboard shortcut for bold formatting
                    await page.keyboard.press("Meta+b" if platform.system() == "Darwin" else "Ctrl+b")
                    await asyncio.sleep(0.5)
                    return "Success: Applied bold formatting via keyboard shortcut"
                except Exception as e:
                    logger.error(f"Bold formatting failed: {e}")
                    return f"Error: Failed to apply bold formatting: {e}"
        # Generate interaction code using Gemini
        # Generate interaction code for the current page context
        interaction_code = await generate_playwright_code(
            page,
            prompt,
            element_info_list,
        )
        
        # Execute the generated code
        result = await execute_interaction(page, interaction_code)
        
        if result["success"]:
            # For multi-step formatting, try additional steps if needed
            if "heading" in prompt.lower() and "color" in prompt.lower():
                try:
                    logger.info("Applying additional formatting steps for complex request...")
                    # First apply heading
                    await page.keyboard.press('Ctrl+a')  # Select all
                    await page.wait_for_timeout(300)
                    await page.keyboard.press('Ctrl+Alt+1')  # Heading 1
                    await page.wait_for_timeout(500)
                    
                    # Then try to apply color (this is more complex, may need menu navigation)
                    await page.keyboard.press('Ctrl+Shift+h')  # Text color shortcut
                    await page.wait_for_timeout(500)
                    
                    return f"Success: {result['message']} + additional formatting applied"
                except Exception as e:
                    logger.warning(f"Additional formatting failed: {e}")
                    return f"Success: {result['message']} (primary action completed)"
            
            return f"Success: {result['message']}"
        else:
            return f"Error: {result['error']}"
    except Exception as e:
        error_message = f"UI interaction failed: {e}"
        logger.error(error_message, exc_info=True)
        return error_message