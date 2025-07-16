# in aurora_agent/browser_manager.py (CORRECTED AND FINAL VERSION)
import asyncio
import traceback
import logging
from playwright.async_api import async_playwright
from typing import Optional

logger = logging.getLogger(__name__)

class BrowserManager:
    def __init__(self):
        self.playwright_instance = None
        self.browser_instance = None
        self.last_sent_screenshot_bytes: Optional[bytes] = None

    async def start_browser(self):
        if self.browser_instance:
            logger.info("Browser is already running.")
            return

        logger.info("Initializing Playwright and launching browser...")
        try:
            self.playwright_instance = await async_playwright().start()
            self.browser_instance = await self.playwright_instance.chromium.launch(headless=False)
            logger.info("Browser started successfully.")
        except Exception as e:
            logger.error(f"CRITICAL: An unexpected error occurred during browser startup: {e}", exc_info=True)
            await self.close_browser()
            raise

    async def close_browser(self):
        if self.browser_instance:
            await self.browser_instance.close()
            logger.info("Browser instance closed.")
        if self.playwright_instance:
            await self.playwright_instance.stop()
            logger.info("Playwright instance stopped.")

    async def execute_interaction(self, url: str, interaction_code: str):
        """Creates a new page, navigates, and executes the interaction code."""
        if not self.browser_instance:
            return "Browser not started."
            
        page = await self.browser_instance.new_page()
        logger.info(f"Executing interaction on new page at URL: {url}")
        try:
            await page.goto(url, wait_until="networkidle")
            
            # This is where you would inject your annotation helpers
            from .ui_tools.annotation_helpers import highlight_element, remove_annotations
            
            exec_scope = {
                'page': page, 
                'asyncio': asyncio,
                'highlight_element': highlight_element,
                'remove_highlights': remove_annotations,
            }
            
            code_to_exec = f"async def __interaction():\n" + "".join(f"    {line}\n" for line in interaction_code.splitlines())
            
            exec(code_to_exec, exec_scope)
            interaction_func = exec_scope['__interaction']
            await interaction_func()
            
            # Take a final screenshot after the interaction
            self.last_sent_screenshot_bytes = await page.screenshot(type="jpeg", quality=70)
            
            return "Interaction executed successfully."
        except Exception as e:
            error_msg = f"An error occurred during interaction: {traceback.format_exc()}"
            logger.error(error_msg)
            return error_msg
        finally:
            await page.close()

    # NOTE: The browser_manager no longer needs get_elements_info or navigate.
    # Those tasks are now handled by the agent's internal logic, which generates
    # Playwright code that is then executed by execute_interaction.
    # The agent gets its visual context from the screenshot.

# Create a singleton instance for the application to use
browser_manager = BrowserManager()