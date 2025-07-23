# Enhanced Jupyter tools for Teacher AI Application
# Supports annotation, highlighting, and cross-cell navigation for pedagogical purposes

import logging
import asyncio
from ...browser_manager import browser_manager

logger = logging.getLogger(__name__)

async def annotate_and_click_cell_n(cell_execution_count: int, annotation_color: str = "red", annotation_text: str = None) -> str:
    """
    Finds a Jupyter cell, highlights it with annotation, and makes it active.
    Perfect for teacher AI to visually indicate which cell is being discussed/edited.
    
    Args:
        cell_execution_count: The execution number of the cell to annotate
        annotation_color: Color for the annotation (red, blue, green, orange, etc.)
        annotation_text: Optional text to display as annotation
    """
    logger.info(f"--- ANNOTATION TOOL: Annotating and clicking Cell {cell_execution_count} ---")
    page = browser_manager.page
    if not page: return "Error: Browser not available."

    try:
        # Find the input prompt first
        prompt_locator = page.locator(f"div.jp-InputPrompt:has-text('[{cell_execution_count}]')")
        await prompt_locator.wait_for(state="visible", timeout=15000)
        
        # Get the cell container
        cell_container = prompt_locator.locator("xpath=ancestor::div[contains(@class, 'jp-CodeCell')]").first
        
        # Scroll the cell into view if needed
        await cell_container.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)  # Brief pause for smooth scrolling
        
        # Add visual annotation using CSS injection
        annotation_style = f"""
        border: 3px solid {annotation_color} !important;
        box-shadow: 0 0 10px {annotation_color} !important;
        background-color: {annotation_color}10 !important;
        transition: all 0.3s ease !important;
        """
        
        # Apply the annotation style
        await page.evaluate(f"""
        (element) => {{
            element.style.cssText += `{annotation_style}`;
            element.setAttribute('data-teacher-annotation', 'true');
            element.setAttribute('data-annotation-color', '{annotation_color}');
        }}
        """, await cell_container.element_handle())
        
        # Add text annotation if provided
        if annotation_text:
            await page.evaluate(f"""
            (element) => {{
                // Remove existing annotation if present
                const existingAnnotation = element.querySelector('.teacher-annotation-text');
                if (existingAnnotation) existingAnnotation.remove();
                
                // Create new annotation
                const annotation = document.createElement('div');
                annotation.className = 'teacher-annotation-text';
                annotation.style.cssText = `
                    position: absolute;
                    top: -25px;
                    left: 0;
                    background: {annotation_color};
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                    z-index: 1000;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                `;
                annotation.textContent = `{annotation_text}`;
                element.style.position = 'relative';
                element.appendChild(annotation);
            }}
            """, await cell_container.element_handle())
        
        # Click the input area to make the cell active
        input_area = cell_container.locator(".jp-Cell-inputWrapper .cm-content")
        await input_area.wait_for(state="visible", timeout=5000)
        await input_area.click()
        
        logger.info(f"Successfully annotated and clicked cell {cell_execution_count} with {annotation_color} highlight.")
        return f"Success: Cell {cell_execution_count} annotated with {annotation_color} and made active"
        
    except Exception as e:
        logger.error(f"ANNOTATION TOOL: Could not annotate cell {cell_execution_count}. Error: {e}")
        return f"Error: Could not annotate cell {cell_execution_count}."

async def clear_all_annotations() -> str:
    """Remove all teacher annotations from the notebook."""
    logger.info("--- ANNOTATION TOOL: Clearing all annotations ---")
    page = browser_manager.page
    if not page: return "Error: Browser not available."
    
    try:
        await page.evaluate("""
        () => {
            // Remove all annotation styles
            const annotatedCells = document.querySelectorAll('[data-teacher-annotation="true"]');
            annotatedCells.forEach(cell => {
                cell.style.border = '';
                cell.style.boxShadow = '';
                cell.style.backgroundColor = '';
                cell.removeAttribute('data-teacher-annotation');
                cell.removeAttribute('data-annotation-color');
                
                // Remove text annotations
                const textAnnotations = cell.querySelectorAll('.teacher-annotation-text');
                textAnnotations.forEach(annotation => annotation.remove());
            });
        }
        """)
        
        logger.info("Successfully cleared all annotations.")
        return "Success: All annotations cleared"
        
    except Exception as e:
        logger.error(f"Error clearing annotations: {e}")
        return f"Error: Could not clear annotations."

async def get_cell_at_viewport_position(x_percent: float = 50, y_percent: float = 50) -> str:
    """
    Identify which cell is at a specific viewport position.
    Useful for determining which cell a student is referring to when they point or click.
    
    Args:
        x_percent: X position as percentage of viewport width (0-100)
        y_percent: Y position as percentage of viewport height (0-100)
    """
    logger.info(f"--- CELL DETECTION: Finding cell at position ({x_percent}%, {y_percent}%) ---")
    page = browser_manager.page
    if not page: return "Error: Browser not available."
    
    try:
        # Get viewport dimensions and calculate actual coordinates
        viewport_size = page.viewport_size
        x = int(viewport_size['width'] * x_percent / 100)
        y = int(viewport_size['height'] * y_percent / 100)
        
        # Find the element at the specified position
        element_info = await page.evaluate(f"""
        () => {{
            const element = document.elementFromPoint({x}, {y});
            if (!element) return null;
            
            // Find the closest cell container
            const cell = element.closest('.jp-CodeCell');
            if (!cell) return null;
            
            // Find the execution number
            const prompt = cell.querySelector('.jp-InputPrompt');
            if (!prompt) return null;
            
            const promptText = prompt.textContent.trim();
            const match = promptText.match(/\\[(\\d+)\\]/);
            
            return {{
                executionNumber: match ? parseInt(match[1]) : null,
                cellType: 'code',
                hasOutput: !!cell.querySelector('.jp-Cell-outputArea'),
                isActive: cell.classList.contains('jp-mod-active')
            }};
        }}
        """)
        
        if element_info and element_info['executionNumber']:
            execution_num = element_info['executionNumber']
            logger.info(f"Found cell {execution_num} at position ({x_percent}%, {y_percent}%)")
            return f"Success: Cell {execution_num} found at position"
        else:
            return "No cell found at specified position"
            
    except Exception as e:
        logger.error(f"Error detecting cell at position: {e}")
        return f"Error: Could not detect cell at position."

async def edit_cell_with_scaffolding(target_cell: int, new_content: str, scaffold_message: str = None) -> str:
    """
    Navigate to and edit a specific cell with scaffolding support.
    Perfect for when teacher wants to reference/edit a previous cell for teaching.
    
    Args:
        target_cell: The cell execution number to edit
        new_content: New content to add/replace in the cell
        scaffold_message: Optional message to display while scaffolding
    """
    logger.info(f"--- SCAFFOLDING TOOL: Editing cell {target_cell} with scaffolding ---")
    page = browser_manager.page
    if not page: return "Error: Browser not available."
    
    try:
        # First, annotate the target cell to draw attention
        annotation_result = await annotate_and_click_cell_n(
            target_cell, 
            "orange", 
            scaffold_message or f"Scaffolding: Editing Cell {target_cell}"
        )
        
        if "Error" in annotation_result:
            return annotation_result
        
        # Wait a moment for the annotation to be visible
        await asyncio.sleep(1)
        
        # Get the active cell input area
        active_cell_selector = "div.jp-Notebook-cell.jp-mod-active .cm-content"
        active_cell = page.locator(active_cell_selector)
        await active_cell.wait_for(state="visible", timeout=10000)
        
        # Add the new content (append or replace based on content)
        if new_content.startswith("APPEND:"):
            # Append to existing content
            content_to_add = new_content[7:]  # Remove "APPEND:" prefix
            current_content = await active_cell.inner_text()
            full_content = f"{current_content}\n{content_to_add}"
            await active_cell.fill(full_content)
        else:
            # Replace content entirely
            await active_cell.fill(new_content)
        
        # Brief pause to show the change
        await asyncio.sleep(0.5)
        
        logger.info(f"Successfully edited cell {target_cell} with scaffolding.")
        return f"Success: Cell {target_cell} edited with scaffolding support"
        
    except Exception as e:
        logger.error(f"Error in scaffolding edit: {e}")
        return f"Error: Could not edit cell {target_cell} with scaffolding."

async def highlight_cell_for_doubt_resolution(cell_execution_count: int, doubt_context: str = None) -> str:
    """
    Highlight a cell when a student expresses doubt about it.
    Uses a distinct visual style to indicate this is a doubt/question context.
    """
    logger.info(f"--- DOUBT RESOLUTION: Highlighting cell {cell_execution_count} for doubt ---")
    
    # Use a distinct color scheme for doubt resolution
    annotation_text = f"❓ Student Doubt: {doubt_context}" if doubt_context else "❓ Student has a question about this cell"
    
    result = await annotate_and_click_cell_n(
        cell_execution_count,
        "purple",  # Purple for doubt/question context
        annotation_text
    )
    
    if "Success" in result:
        logger.info(f"Cell {cell_execution_count} highlighted for doubt resolution.")
        return f"Success: Cell {cell_execution_count} highlighted for doubt resolution"
    else:
        return result
