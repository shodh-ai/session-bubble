# in /session-bubble/test_jupyter_subgraph.py
import asyncio
import os
from dotenv import load_dotenv
import json

# Load environment variables from .env file in the current directory
load_dotenv()
print(f"DEBUG: Loaded GOOGLE_API_KEY is: {os.getenv('GOOGLE_API_KEY')[:5]}...") # Print first 5 chars

# Verify that the API key is loaded
if not os.getenv('GOOGLE_API_KEY'):
    print("ERROR: GOOGLE_API_KEY not found in environment variables")
    print(f"Looking for .env file in: {os.path.abspath('.')}")
    exit(1)

# Import and create the specific subgraph we want to test
from aurora_agent.agent_brains.experts.jupyter.graph import create_jupyter_expert_subgraph

# Create an instance of the Jupyter expert subgraph
jupyter_expert_graph = create_jupyter_expert_subgraph()

# Import the browser manager to set up the environment
from aurora_agent.browser_manager import browser_manager

async def main():
    """
    The definitive, robust test harness for the Jupyter expert subgraph.
    Its only job is to prepare a clean notebook environment for the agent.
    """
    print("--- STARTING JUPYTER SUBGRAPH TEST HARNESS ---")

    test_url = "https://jupyter.org/try-jupyter/lab/"
    mission_prompt = "Write Python code to import the pandas library as pd, and then run the cell to execute it."
    
    try:
        print("Starting browser (non-headless so you can watch)...")
        await browser_manager.start_browser(headless=False)

        print(f"Navigating to JupyterLab demo page: {test_url}")
        page = await browser_manager.navigate(test_url)
        
        print("Waiting for the main application content area to appear...")
        main_content_locator = page.get_by_label("Main Content")
        await main_content_locator.wait_for(state="visible", timeout=60000)
        
        # --- ADDING PAUSES FOR VISIBILITY ---
        print("Found main content area. Pausing for 2 seconds.")
        await asyncio.sleep(2)

        print("Preparing the notebook environment...")
        
        python_notebook_selector = 'div[data-category="Notebook"][title="Python (Pyodide)"]'
        python_notebook_card = main_content_locator.locator(python_notebook_selector)
        await python_notebook_card.click()
        
        print("Notebook creation clicked. Pausing for 3 seconds.")
        await asyncio.sleep(3)
        
        print("Waiting for the new notebook's first cell to be ready...")
        first_cell_selector = "div.jp-NotebookPanel-notebook .jp-Cell-inputWrapper .cm-content"
        first_cell_locator = page.locator(first_cell_selector).first
        await first_cell_locator.wait_for(state="visible", timeout=30000)
        
        await first_cell_locator.click()
        print("New notebook created and first cell is now active. Pausing for 2 seconds before starting agent.")
        await asyncio.sleep(2)
        # --- End of Setup ---

        print("\n--- INVOKING JUPYTER EXPERT SUBGRAPH ---")
        
        final_state = await jupyter_expert_graph.ainvoke({
            "mission_prompt": mission_prompt,
            "current_url": page.url 
        })

        print("\n--- SUBGRAPH EXECUTION COMPLETE ---")
        print("Final State from Graph:")
        print(json.dumps(final_state, indent=2))
        print("\n--- Mission complete. Admire your work for 5 seconds... ---")
        await asyncio.sleep(10)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        print("\n--- Closing browser ---")
        await browser_manager.close_browser()
        print("--- TEST HARNESS FINISHED ---")


if __name__ == "__main__":
    asyncio.run(main())