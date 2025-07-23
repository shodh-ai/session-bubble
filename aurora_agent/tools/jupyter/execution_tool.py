import logging
from aurora_agent.browser_manager import browser_manager

logger = logging.getLogger(__name__)

async def execute_cell_and_wait_for_completion() -> str:
    """
    A powerful tool that runs the active cell AND then patiently waits for its
    execution to complete, whether it takes 1 second or 10 minutes.
    """
    logger.info("--- TOOL: Executing Cell and Waiting for Completion ---")
    page = browser_manager.page
    if not page: return "Error: Browser not available."

    try:
        # 1. Define locators for the cell's state.
        active_cell_selector = "div.jp-Notebook-cell.jp-mod-active"
        busy_indicator_selector = f"{active_cell_selector}.jp-mod-busy"
        run_button_selector = "[data-command='runmenu:run']"

        # 2. Find the elements.
        active_cell = page.locator(active_cell_selector)
        run_button = page.locator(run_button_selector)

        # 3. Click the Run button to start the execution.
        await run_button.click()
        logger.info("TOOL: Run command sent. Now monitoring for completion...")

        # 4. The "Smart Wait": Wait for the 'busy' indicator to appear,
        #    then wait for it to disappear.
        try:
            # Short wait for it to become busy
            await page.locator(busy_indicator_selector).wait_for(state="visible", timeout=5000)
            logger.info("TOOL: Cell is busy (execution started).")
        except Exception:
            # This is okay, it might have run too fast to catch the busy state.
            logger.warning("TOOL: Cell did not appear busy. Proceeding to wait for idle.")

        # The main, long wait. The timeout can be very long for model training.
        await page.locator(busy_indicator_selector).wait_for(state="hidden", timeout=3600000) # 1 hour
        
        logger.info("TOOL: Cell is no longer busy (execution finished).")
        return "Success: The cell executed completely."

    except Exception as e:
        logger.error(f"Error during cell execution or wait: {e}", exc_info=True)
        return f"Error: Failed to execute and wait for cell. Reason: {e}"