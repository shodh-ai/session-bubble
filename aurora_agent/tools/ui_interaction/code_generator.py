# in aurora_agent/tools/ui_interaction/code_generator
import logging
import os
import google.generativeai as genai

# Import the shared browser_manager to interact with the browser
from aurora_agent.browser_manager import browser_manager

logger = logging.getLogger(__name__)

async def generate_and_type_python_code(prompt_for_code_gen: str) -> str:
    """
    Generates Python code based on a prompt and types it into the active
    Jupyter cell. This is the "Typing Hand".
    """
    logger.info(f"CODE-GEN TOOL: Generating Python code for prompt: '{prompt_for_code_gen}'")
    page = browser_manager.page
    if not page:
        return "Error: Browser page is not available."

    try:
        # 1. Generate the Code String with an LLM
        # This part happens invisibly on the server.
        code_gen_prompt = (
            "You are an expert Python data scientist. "
            "Your ONLY job is to write the Python code for the following task. "
            "Do not include explanations, markdown, or comments. Just the raw code.\n\n"
            f"Task: {prompt_for_code_gen}"
        )
        
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = await model.generate_content_async(code_gen_prompt)
        
        generated_code = response.text.strip().replace("```python", "").replace("```", "").strip()
        logger.info(f"CODE-GEN TOOL: Generated code to be typed:\n---\n{generated_code}\n---")
        
        # --- THIS IS THE MAGIC: TYPING THE CODE ---
        # 2. Find the currently active/focused cell in the Jupyter UI.
        #    The '.jp-mod-active' class is reliably on the selected cell.
        #    The '.cm-content' class is the editable text area.
        active_cell_selector = "div.jp-Notebook-cell.jp-mod-active .cm-content"
        
        print("CODE-GEN TOOL: Finding active cell to type into...")
        active_cell = page.locator(active_cell_selector)
        
        # Wait for the cell to be ready and click it to be 100% sure it has focus.
        await active_cell.wait_for(state="visible", timeout=10000)
        await active_cell.click()
        print("CODE-GEN TOOL: Active cell found and focused.")
        
        # 3. Use Playwright's keyboard to type the code, character by character.
        #    This is what makes the text appear on the student's screen.
        await page.keyboard.type(generated_code, delay=50) # A 50ms delay makes it watchable
        
        return "Success: The code was generated and typed into the cell."

    except Exception as e:
        logger.error(f"Error in generate_and_type_python_code: {e}", exc_info=True)
        return f"Error: Failed to generate or type code: {e}"