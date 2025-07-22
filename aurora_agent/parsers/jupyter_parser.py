# in aurora_agent/parsers/jupyter_parser.py
import logging
from playwright.async_api import Page
from .base_parser import BaseParser

logger = logging.getLogger(__name__)

class JupyterParser(BaseParser):
    """
    A specialized parser that understands the HTML structure of a standard
    JupyterLab interface.
    """
    async def get_interactive_elements(self, page: Page) -> list[dict]:
        logger.info("--- Using JupyterParser ---")
        search_scope = page.locator(scope_selector) if scope_selector else page
        run_button = search_scope.locator("[data-command='runmenu:run']")
        # ... and so on for all your other selectors ...
        # ...
        
        # Example for finding code cells within the scope:
        code_cells = await search_scope.locator("div.jp-Cell-inputWrapper div.cm-content").all()
        elements_info = []

        # 1. Find all visible code cells' editable areas
        try:
            # The '.cm-content' class is common for CodeMirror 6, used by modern JupyterLab
            cell_editors = await page.locator("div.jp-Cell-inputWrapper div.cm-content").all()
            for i, editor in enumerate(cell_editors):
                if await editor.is_visible():
                    elements_info.append({
                        "element_id": f"jupyter-code-cell-{i}",
                        "description": f"Code cell #{i+1}, ready for input.",
                        "playwright_locator": f"page.locator(\"div.jp-Cell-inputWrapper div.cm-content\").nth({i})"
                    })
        except Exception as e:
            logger.warning(f"Could not find Jupyter code cells: {e}")

        # 2. Find key toolbar buttons using reliable 'data-command' attributes
        try:
            run_button = page.locator("[data-command='runmenu:run']")
            if await run_button.is_visible():
                elements_info.append({
                    "element_id": "jupyter-run-button",
                    "description": "The 'Run selected cells and advance' button in the toolbar.",
                    "playwright_locator": "page.locator(\"[data-command='runmenu:run']\")"
                })

            add_cell_button = page.locator("[data-command='notebook:insert-cell-below']")
            if await add_cell_button.is_visible():
                elements_info.append({
                    "element_id": "jupyter-add-cell-button",
                    "description": "The 'Insert a cell below' button in the toolbar.",
                    "playwright_locator": "page.locator(\"[data-command='notebook:insert-cell-below']\")"
                })
        except Exception as e:
            logger.warning(f"Could not find Jupyter toolbar buttons: {e}")

        return elements_info