# File: session-bubble/aurora_agent/parsers/generic_parser.py
# in aurora_agent/parsers/generic_parser.py
from playwright.async_api import Page
from typing import List, Dict, Any
from .base_parser import BaseParser
import logging

logger = logging.getLogger(__name__)

class GenericParser(BaseParser):
    """
    A generic parser for finding common interactive elements on a webpage.
    """
    async def get_interactive_elements(self, page: Page) -> List[Dict[str, Any]]:
        """
        Finds all common interactive elements on the page.
        """
        logger.info("Using GenericParser to find interactive elements.")
        elements = []
        selectors = [
            'button',
            'a[href]',
            'input:not([type="hidden"])',
            'textarea',
            'select',
            '[role="button"]',
            '[role="link"]',
            '[role="menuitem"]',
            '[role="tab"]',
            '[role="checkbox"]',
            '[role="radio"]'
        ]

        for selector in selectors:
            try:
                locators = await page.locator(selector).all()
                for i, locator in enumerate(locators):
                    if await locator.is_visible() and await locator.is_enabled():
                        uid = f"generic-{selector}-{i}"
                        elements.append({
                            "uid": uid,
                            "selector": selector,
                            "text": await locator.inner_text(),
                            "aria_label": await locator.get_attribute('aria-label'),
                            "role": await locator.get_attribute('role'),
                            "locator": locator
                        })
            except Exception as e:
                logger.warning(f"Could not find elements for selector '{selector}': {e}")

        return elements
