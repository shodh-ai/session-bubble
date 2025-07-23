import asyncio
import os
from dotenv import load_dotenv
import traceback

# --- Standard Setup ---
load_dotenv()
print(f"DEBUG: Loaded GOOGLE_API_KEY is: {os.getenv('GOOGLE_API_KEY')[:5]}...")
if not os.getenv('GOOGLE_API_KEY'):
    raise ValueError("ERROR: GOOGLE_API_KEY not found in environment variables.")

# --- Import Teacher AI Tools ---
from aurora_agent.browser_manager import browser_manager
from aurora_agent.tools.jupyter.reader_tool import read_code_of_cell_n, read_output_of_cell_n
from aurora_agent.tools.jupyter.annotation_tool import (
    annotate_and_click_cell_n,
    clear_all_annotations,
    get_cell_at_viewport_position,
    edit_cell_with_scaffolding,
    highlight_cell_for_doubt_resolution
)

async def main():
    """Test harness for Teacher AI annotation and scaffolding features."""
    try:
        print("\n--- STARTING TEACHER AI JUPYTER TEST ---")
        await browser_manager.start_browser(headless=False)
        page = await browser_manager.navigate("https://jupyter.org/try-jupyter/lab/")
        await page.get_by_label("Main Content").wait_for(state="visible", timeout=90000)
        await page.locator('div[data-category="Notebook"][title="Python (Pyodide)"]').click()
        await page.locator(".jp-NotebookPanel-notebook .jp-Cell-inputWrapper .cm-content").first.wait_for(state="visible", timeout=30000)
        print("Notebook is ready.")
        await asyncio.sleep(2)
        
        # --- SETUP: Create multiple cells for testing ---
        print("\n--- SETTING UP MULTIPLE CELLS FOR TEACHER AI DEMO ---")
        
        # Cell 1: Import statements
        first_cell = page.locator(".jp-NotebookPanel-notebook .jp-Cell-inputWrapper .cm-content").first
        await first_cell.click()
        await first_cell.fill("import numpy as np\nimport matplotlib.pyplot as plt\nprint('Libraries imported successfully!')")
        await page.keyboard.press("Shift+Enter")
        await asyncio.sleep(2)
        
        # Cell 2: Data creation
        second_cell = page.locator(".jp-NotebookPanel-notebook .jp-Cell-inputWrapper .cm-content").nth(1)
        await second_cell.wait_for(state="visible", timeout=10000)
        await second_cell.click()
        await second_cell.fill("# Create sample data\ndata = np.random.rand(10)\nprint(f'Generated data: {data[:5]}...')  # Show first 5 elements")
        await page.keyboard.press("Shift+Enter")
        await asyncio.sleep(3)
        
        # Cell 3: Analysis with intentional error
        third_cell = page.locator(".jp-NotebookPanel-notebook .jp-Cell-inputWrapper .cm-content").nth(2)
        await third_cell.wait_for(state="visible", timeout=10000)
        await third_cell.click()
        await third_cell.fill("# Analysis - this has an error!\nmean_value = np.mean(data)\nprint(f'Mean value: {mean_value}')\n# This will cause an error:\nresult = data / 0  # Division by zero!")
        await page.keyboard.press("Shift+Enter")
        await asyncio.sleep(3)
        
        print("✅ Multiple cells created successfully!")
        
        # --- TEST 1: Basic Cell Annotation ---
        print("\n--- TEST 1: BASIC CELL ANNOTATION ---")
        print("Annotating Cell 1 with red highlight...")
        result1 = await annotate_and_click_cell_n(1, "red", "📚 Modelling: Import statements")
        print(f"Annotation result: {result1}")
        await asyncio.sleep(3)
        
        print("Annotating Cell 2 with blue highlight...")
        result2 = await annotate_and_click_cell_n(2, "blue", "🔧 Practice: Data creation")
        print(f"Annotation result: {result2}")
        await asyncio.sleep(3)
        
        # --- TEST 2: Doubt Resolution Highlighting ---
        print("\n--- TEST 2: DOUBT RESOLUTION ---")
        print("Student expresses doubt about Cell 3...")
        doubt_result = await highlight_cell_for_doubt_resolution(3, "Why did this cell produce an error?")
        print(f"Doubt highlighting result: {doubt_result}")
        await asyncio.sleep(4)
        
        # --- TEST 3: Scaffolding - Edit Previous Cell ---
        print("\n--- TEST 3: SCAFFOLDING - EDITING PREVIOUS CELL ---")
        print("Teacher wants to go back and fix Cell 3 to demonstrate error handling...")
        
        # First, let's create a 4th cell to simulate being "further ahead"
        fourth_cell = page.locator(".jp-NotebookPanel-notebook .jp-Cell-inputWrapper .cm-content").nth(3)
        await fourth_cell.wait_for(state="visible", timeout=10000)
        await fourth_cell.click()
        await fourth_cell.fill("# We're now at cell 4\nprint('This is cell 4 - we are ahead now')")
        await page.keyboard.press("Shift+Enter")
        await asyncio.sleep(2)
        
        # Now scaffold back to cell 3 to fix the error
        print("Scaffolding back to Cell 3 to fix the division by zero error...")
        scaffold_content = """# Analysis - FIXED VERSION!
mean_value = np.mean(data)
print(f'Mean value: {mean_value}')

# Safe division with error handling:
try:
    result = data / 1  # Fixed: divide by 1 instead of 0
    print(f'Division result: {result[:3]}...')  # Show first 3 results
except ZeroDivisionError:
    print('Error: Cannot divide by zero!')
    result = None

print('✅ Error handling demonstrated!')"""
        
        scaffold_result = await edit_cell_with_scaffolding(
            3, 
            scaffold_content, 
            "🏗️ Scaffolding: Fixing the error"
        )
        print(f"Scaffolding result: {scaffold_result}")
        await asyncio.sleep(4)
        
        # --- TEST 4: Cell Detection at Position ---
        print("\n--- TEST 4: CELL DETECTION AT VIEWPORT POSITION ---")
        print("Testing cell detection at center of viewport...")
        position_result = await get_cell_at_viewport_position(50, 50)
        print(f"Cell detection result: {position_result}")
        
        print("Testing cell detection at top of viewport...")
        position_result2 = await get_cell_at_viewport_position(50, 20)
        print(f"Cell detection result (top): {position_result2}")
        await asyncio.sleep(3)
        
        # --- TEST 5: Reading Tools with Annotations ---
        print("\n--- TEST 5: READING ANNOTATED CELLS ---")
        
        # Read content from the scaffolded cell
        print("Reading content from the scaffolded Cell 3...")
        cell3_content = await read_code_of_cell_n(3)
        print(f"Cell 3 content after scaffolding:\n{cell3_content}")
        
        # Read output if available
        print("Reading output from Cell 3...")
        cell3_output = await read_output_of_cell_n(3)
        print(f"Cell 3 output:\n{cell3_output}")
        
        # --- TEST 6: Multiple Annotation Styles ---
        print("\n--- TEST 6: MULTIPLE ANNOTATION STYLES ---")
        print("Demonstrating different annotation colors for different pedagogical purposes...")
        
        # Green for success/completion
        await annotate_and_click_cell_n(1, "green", "✅ Completed: Imports")
        await asyncio.sleep(1)
        
        # Orange for attention/review
        await annotate_and_click_cell_n(2, "orange", "⚠️ Review: Data creation")
        await asyncio.sleep(1)
        
        # Purple remains for doubt (already applied)
        print("Cell 3 retains purple highlighting for doubt resolution")
        await asyncio.sleep(3)
        
        # --- DEMONSTRATION COMPLETE ---
        print("\n--- TEACHER AI DEMONSTRATION COMPLETE ---")
        print("✅ Cell annotation with colors and text")
        print("✅ Doubt resolution highlighting") 
        print("✅ Scaffolding with cross-cell navigation")
        print("✅ Cell detection at viewport positions")
        print("✅ Reading tools work with annotated cells")
        print("✅ Multiple annotation styles for different pedagogical contexts")
        
        print("\n🎓 Teacher AI features are ready for:")
        print("   • Modelling (demonstrate concepts)")
        print("   • Scaffolding (provide guided support)")
        print("   • Coaching (help with problem-solving)")
        
        # Keep annotations visible for a while
        await asyncio.sleep(10)
        
        # --- CLEANUP ---
        print("\n--- CLEANING UP ANNOTATIONS ---")
        cleanup_result = await clear_all_annotations()
        print(f"Cleanup result: {cleanup_result}")
        await asyncio.sleep(3)
        
    except Exception as e:
        traceback.print_exc()
        input("Test failed. Press Enter to close.")
    finally:
        await browser_manager.close_browser()
        print("--- TEACHER AI TEST FINISHED ---")

if __name__ == "__main__":
    asyncio.run(main())
