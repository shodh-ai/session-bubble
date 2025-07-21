# in aurora_agent/parsers/jupyter_parser.py
from playwright.async_api import Page
from .base_parser import BaseParser
import logging

logger = logging.getLogger(__name__)

class JupyterParser(BaseParser):
    """
    A specialized parser that understands the HTML structure of Jupyter Notebooks
    (as run by `code-server` or similar environments).
    """
    async def get_interactive_elements(self, page: Page) -> list[dict]:
        logger.info("--- Using JupyterParser ---")
        elements_info = []

        # 1. Find all visible code cells
        try:
            # The '.cm-content' class is common for the editable area in CodeMirror 6 (used by modern Jupyter)
            code_cells = await page.locator("div.jp-Cell-inputWrapper div.cm-content").all()
            for i, cell in enumerate(code_cells):
                if await cell.is_visible():
                    elements_info.append({
                        "element_id": f"jupyter-code-cell-{i}",
                        "description": f"Code cell #{i+1}, ready for input.",
                        "playwright_locator": f"page.locator(\"div.jp-Cell-inputWrapper div.cm-content\").nth({i})"
                    })
        except Exception as e:
            logger.warning(f"Could not find Jupyter code cells: {e}")

        # 2. Find key toolbar buttons
        try:
            # Use data-command attribute for high reliability
            run_button = page.locator("[data-command='runmenu:run']")
            if await run_button.is_visible():
                elements_info.append({
                    "element_id": "jupyter-run-button",
                    "description": "The 'Run' button in the toolbar.",
                    "playwright_locator": "page.locator(\"[data-command='runmenu:run']\")"
                })
            
            add_cell_button = page.locator("[data-command='notebook:insert-cell-below']")
            if await add_cell_button.is_visible():
                elements_info.append({
                    "element_id": "jupyter-add-cell-button",
                    "description": "The '+' (Add Cell) button in the toolbar.",
                    "playwright_locator": "page.locator(\"[data-command='notebook:insert-cell-below']\")"
                })
        except Exception as e:
            logger.warning(f"Could not find Jupyter toolbar buttons: {e}")
        
        return elements_info