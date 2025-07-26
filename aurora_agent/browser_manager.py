# File: session-bubble/aurora_agent/browser_manager.py
# in aurora_agent/browser_manager.py (FINAL, CORRECTED VERSION)
import asyncio
import traceback
import logging
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from typing import Optional
import os

logger = logging.getLogger(__name__)

class BrowserManager:
    def __init__(self):
        self.playwright_instance = None
        self.browser_instance: Optional[Browser] = None
        # The manager should not hold a single page, but a context
        self.context: Optional[BrowserContext] = None
        self.last_sent_screenshot_bytes: Optional[bytes] = None
        # Store a reference to the most recently opened page so other modules can access it easily
        self.page: Optional[Page] = None

    async def start_browser(self, headless: bool = True):
        if self.browser_instance:
            logger.info("Browser is already running.")
            return

        logger.info(f"Initializing Playwright and launching browser (headless={headless})...")
        self.playwright_instance = await async_playwright().start()
        
        # Configure browser launch args for better VNC display
        launch_args = []
        if not headless:
            launch_args.extend([
                '--start-maximized',
                '--window-size=1280,720',
                '--window-position=0,0',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ])
        
        self.browser_instance = await self.playwright_instance.chromium.launch(
            headless=headless,
            args=launch_args
        )
        
        # Create a single, authenticated context if auth file exists
        auth_file_path = 'auth.json'
        context_options = {
            'viewport': {'width': 1280, 'height': 720} if not headless else None
        }
        
        if os.path.exists(auth_file_path):
            context_options['storage_state'] = auth_file_path
            
        self.context = await self.browser_instance.new_context(**context_options)
        
        logger.info("Browser and context started successfully.")

    async def get_page(self, url: str) -> Page:
        """Gets a new, navigated page from the managed browser context."""
        if not self.context:
            raise Exception("Browser context not started. Call start_browser() first.")
        
        page = await self.context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        self.page = page
        return page

    async def navigate(self, url: str, headless: bool = True) -> Page:
        """Convenience: ensure browser is running and navigate to URL.
        Stores page on the manager for later access.
        """
        if not self.browser_instance:
            await self.start_browser(headless=headless)
        page = await self.get_page(url)
        return page

    async def close_browser(self):
        if self.context:
            await self.context.close()
        if self.browser_instance:
            await self.browser_instance.close()
        if self.playwright_instance:
            await self.playwright_instance.stop()
        
        self.browser_instance = None
        self.context = None
        logger.info("Browser and context closed successfully.")

# A new, separate function for executing code. It is no longer part of the manager.
async def execute_interaction_on_page(page: Page, interaction_code: str) -> dict:
    """Executes a string of Playwright code on a given page object."""
    from aurora_agent.ui_tools.annotation_helpers import highlight_element, remove_annotations
    
    try:
        exec_scope = {
            'page': page, 
            'asyncio': asyncio,
            'highlight_element': highlight_element,
            'remove_annotations': remove_annotations,
        }
        
        code_to_exec = f"async def __interaction():\n" + "".join(f"    {line}\n" for line in interaction_code.splitlines())
        
        exec(code_to_exec, exec_scope)
        interaction_func = exec_scope['__interaction']
        await interaction_func()
        
        return {"success": True, "message": "Interaction executed successfully."}
    except Exception as e:
        error_msg = f"An error occurred during interaction: {traceback.format_exc()}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

# Create a singleton instance of the manager for the application to use
browser_manager = BrowserManager()
