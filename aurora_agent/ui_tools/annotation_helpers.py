# File: session-bubble/aurora_agent/ui_tools/annotation_helpers.py
# in aurora_agent/ui_tools/annotation_helpers.py
from playwright.async_api import Page, Locator
import logging

logger = logging.getLogger(__name__)
HIGHLIGHT_BOX_ID = "agent_highlight_box"

async def highlight_element(page: Page, locator: Locator):
    """
    Draws a temporary red highlight box around a Playwright Locator.
    """
    if not locator:
        logger.warning("highlight_element called with no locator.")
        return

    try:
        await locator.wait_for(state="visible", timeout=5000)
        await page.evaluate(f"""(element) => {{
            // First, remove any old highlight
            const old_box = document.getElementById('{HIGHLIGHT_BOX_ID}');
            if (old_box) {{
                old_box.remove();
            }}

            // Get the position and size of the element
            const rect = element.getBoundingClientRect();
            
            // Create the new highlight box
            const box = document.createElement('div');
            box.id = '{HIGHLIGHT_BOX_ID}';
            box.style.position = 'absolute';
            box.style.left = `${{rect.left + window.scrollX}}px`;
            box.style.top = `${{rect.top + window.scrollY}}px`;
            box.style.width = `${{rect.width}}px`;
            box.style.height = `${{rect.height}}px`;
            box.style.border = '3px solid red';
            box.style.boxSizing = 'border-box';
            box.style.zIndex = '9999';
            box.style.pointerEvents = 'none'; // Make it non-interactive
            
            document.body.appendChild(box);
        }}""", await locator.element_handle())
    except Exception as e:
        logger.error(f"Failed to highlight element: {e}")

async def remove_annotations(page: Page):
    """Removes any existing highlight boxes from the page."""
    try:
        await page.evaluate(f"""() => {{
            const box = document.getElementById('{HIGHLIGHT_BOX_ID}');
            if (box) {{
                box.remove();
            }}
        }}""")
    except Exception as e:
        logger.error(f"Failed to remove annotations: {e}")
