from aurora_agent.browser_manager import browser_manager
from aurora_agent.parsers import get_parser_for_url
from .interaction_tool import generate_playwright_code, execute_interaction

async def live_ui_interaction_tool(prompt: str) -> str:
    """
    The complete, live tool for performing a visual UI interaction.
    It gets context, generates code, and executes it.
    """
    # 1. Get the current page from the browser manager
    page = browser_manager.page
    if not page:
        return "Error: Browser is not active."

    # 2. Get visual context using the parser framework
    parser = get_parser_for_url(page.url)
    element_info = await parser.get_interactive_elements(page)

    # 3. Generate the Playwright code using the brain
    interaction_code = await generate_playwright_code(page, prompt, element_info)
    if "Exception" in interaction_code:  # Simple check for generation failure
        return f"Error: Failed to generate interaction code. Reason: {interaction_code}"

    # 4. Execute the code using the hands
    result = await execute_interaction(page, interaction_code)
    
    return result["message"] if result["success"] else f"Error: {result['error']}"