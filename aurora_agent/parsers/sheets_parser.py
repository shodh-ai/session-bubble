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
        Finds interactive elements in Google Sheets, including toolbar, menus, dropdowns, and chart editor.
        """
        logger.info("--- Using Upgraded SheetsParser ---")
        elements = []

        # --- Selectors for different UI regions ---
        selectors = {
            "toolbar_button": '[role="toolbar"] [aria-label]',
            "menu_item": '[role="menubar"] [role="menuitem"]',
            "dropdown_item": 'div.goog-menu[role="menu"] [role="menuitemcheckbox"]',
            "chart_editor_field": 'div.chart-editor-section-header'
        }

        for element_type, selector in selectors.items():
            try:
                locators = await page.locator(selector).all()
                for locator in locators:
                    if await locator.is_visible():
                        # Use inner_text as a more reliable descriptor for menus
                        description = await locator.inner_text() or await locator.get_attribute('aria-label')
                        if description:
                            elements.append({
                                "uid": f"sheets-{element_type}-{description.replace(' ', '-')}",
                                "description": f"{element_type.replace('_', ' ').title()}: '{description}'",
                                # The locator the agent will use
                                "playwright_locator": f"page.get_by_text('{description.strip()}', exact=True)"
                            })
            except Exception:
                # This can happen if a menu is not open, which is fine
                continue

        # --- Find Grid Cell Elements for data selection ---
        grid_cell_selector = "td.waffle-cell"
        try:
            cell_locators = await page.locator(grid_cell_selector).all()
            for i, locator in enumerate(cell_locators[:20]):  # Limit to first 20 cells for performance
                if await locator.is_visible():
                    row = await locator.get_attribute('data-row')
                    col = await locator.get_attribute('data-col')
                    if row and col:
                        cell_text = await locator.inner_text()
                        elements.append({
                            "uid": f"sheets-cell-R{row}-C{col}",
                            "description": f"Grid Cell: '{cell_text}' at R{row}C{col}",
                            "playwright_locator": f"page.locator('td.waffle-cell[data-row=\"{row}\"][data-col=\"{col}\"]')"
                        })
        except Exception as e:
            logger.warning(f"Could not find Google Sheets cell elements: {e}")

        return elements
