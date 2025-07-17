# in aurora_agent/parsers/sheets_parser.py
from playwright.async_api import Page
from typing import List, Dict, Any
from .base_parser import BaseParser
import logging

logger = logging.getLogger(__name__)

class SheetsParser(BaseParser):
    """
    A specialized parser for identifying interactive elements in Google Sheets.
    """
    async def get_interactive_elements(self, page: Page) -> List[Dict[str, Any]]:
        """
        Finds interactive elements in Google Sheets, focusing on the toolbar and grid cells.
        """
        logger.info("Using SheetsParser to find interactive elements.")
        elements = []

        # --- 1. Find Toolbar Elements ---
        toolbar_selector = '[role="toolbar"] [role="button"], [role="toolbar"] [role="menubutton"]'
        try:
            toolbar_locators = await page.locator(toolbar_selector).all()
            for i, locator in enumerate(toolbar_locators):
                if await locator.is_visible():
                    element_data = {
                        "uid": f"sheets-toolbar-{i}",
                        "text": await locator.inner_text(),
                        "aria_label": await locator.get_attribute('aria-label'),
                        "role": await locator.get_attribute('role'),
                    }

                    # Generate a more robust locator using the aria-label if it exists
                    aria_label = element_data.get("aria_label")
                    if aria_label:
                        # Escape single quotes in the aria-label for the locator string
                        escaped_aria_label = aria_label.replace("'", "\\'")
                        element_data["playwright_locator"] = f"page.locator('[role=\"toolbar\"] [aria-label=\"{escaped_aria_label}\"]')"
                    else:
                        element_data["playwright_locator"] = f"page.locator('{toolbar_selector}').nth({i})"
                    
                    elements.append(element_data)
        except Exception as e:
            logger.warning(f"Could not find Google Sheets toolbar elements: {e}")

        # --- 2. Find Grid Cell Elements ---
        # This is crucial for interacting with the sheet data itself.
        grid_cell_selector = "td.waffle-cell"
        try:
            cell_locators = await page.locator(grid_cell_selector).all()
            for i, locator in enumerate(cell_locators):
                if await locator.is_visible():
                    row = await locator.get_attribute('data-row')
                    col = await locator.get_attribute('data-col')
                    if row and col:
                        elements.append({
                            "uid": f"sheets-cell-R{row}-C{col}",
                            "selector": f"td.waffle-cell[data-row='{row}'][data-col='{col}']",
                            "text": await locator.inner_text(),
                            "aria_label": f"Cell R{row}C{col}",
                            "role": "gridcell",
                        })
        except Exception as e:
            logger.warning(f"Could not find Google Sheets cell elements: {e}")

        return elements
