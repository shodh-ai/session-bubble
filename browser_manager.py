# in aurora_agent/browser_manager.py
import asyncio
import logging
import os
from playwright.async_api import async_playwright, Page, Browser
from .parsers import get_parser_for_url

logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Manages the Playwright browser instance, including pages, screenshots, and parsing.
    """
    def __init__(self):
        self.playwright = None
        self.browser: Browser | None = None
        self.page: Page | None = None
        self.last_sent_screenshot_bytes: bytes | None = None

    async def start_browser(self):
        """Launches a new browser instance and page."""
        if self.browser:
            logger.warning("Browser already launched.")
            return
        self.playwright = await async_playwright().start()
        # For general use, launch a non-persistent, headless browser.
        # The test environment will be responsible for creating its own authenticated context.
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        logger.info("Browser launched successfully.")

    async def close_browser(self):
        """Closes the browser instance and stops Playwright."""
        if self.browser:
            await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            self.browser = None
            self.page = None
            logger.info("Browser closed successfully.")

    async def navigate(self, url: str):
        """Navigates the current page to a new URL."""
        if not self.page:
            logger.error("Cannot navigate, no page is active.")
            return
        await self.page.goto(url, wait_until="networkidle", timeout=60000)
        # For complex apps like Google Sheets, wait for a specific element that indicates readiness.
        # The '.grid-container' is a good candidate for the main sheet view.
        try:
            await self.page.wait_for_selector('.grid-container', timeout=15000)
            logger.info("Google Sheets grid container is visible.")
        except Exception as e:
            logger.error(f"Failed to find the main grid container. The page may not have loaded correctly: {e}")
            # We can choose to raise the error or just log it, depending on desired strictness.
            raise
        logger.info(f"Navigated to {url}")

    async def get_screenshot(self):
        """Takes a screenshot of the current page."""
        if not self.page:
            logger.error("Cannot get screenshot, no page is active.")
            return None
        
        screenshot_data = await self.page.screenshot(type="jpeg", quality=70)
        self.last_sent_screenshot_bytes = screenshot_data
        return screenshot_data

    async def get_elements_info(self):
        """
        Gets interactive element information using the appropriate parser.
        This is the refactored method that uses the parser registry.
        """
        if not self.page:
            logger.error("Cannot get elements, no page is active.")
            return []

        parser = get_parser_for_url(self.page.url)
        elements = await parser.get_interactive_elements(self.page)
        return elements

# Note: The 'execute_interaction' logic has been moved to 'aurora_agent/ui_tools/interaction_tool.py'.
