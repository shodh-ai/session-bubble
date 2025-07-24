# in aurora_agent/tools/jupyter/upload_tool.py
import logging
import os
from ...browser_manager import browser_manager

logger = logging.getLogger(__name__)

async def upload_file_to_jupyter(local_file_path: str) -> str:
    """
    Uploads a local file to the Jupyter environment by handling the file chooser.
    """
    logger.info(f"--- TOOL: Uploading file '{local_file_path}' to Jupyter ---")
    page = browser_manager.page
    if not page: return "Error: Browser not available."

    if not os.path.exists(local_file_path):
        return f"Error: Local file not found at '{local_file_path}'"

    try:
        # Step 1: Start listening for the 'filechooser' event BEFORE clicking.
        # This is critical. The listener must be active when the click happens.
        async with page.expect_file_chooser() as fc_info:
            # Step 2: Click the JupyterLab "Upload" button.
            # Try multiple selectors for different Jupyter versions/environments
            upload_selectors = [
                '[data-id="jp-id-upload"]',  # Standard JupyterLab
                'button[title="Upload Files"]',  # Alternative selector
                '.jp-ToolbarButtonComponent[title*="Upload"]',  # Toolbar button
                'input[type="file"]'  # Direct file input
            ]
            
            upload_clicked = False
            for selector in upload_selectors:
                try:
                    upload_button = page.locator(selector)
                    if await upload_button.count() > 0:
                        await upload_button.click()
                        upload_clicked = True
                        logger.info(f"Clicked upload button with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not upload_clicked:
                raise Exception("Could not find upload button with any known selector")
        
        # Step 3: Once the event is caught, set the file path.
        file_chooser = await fc_info.value
        await file_chooser.set_files(local_file_path)
        
        # After selecting, Jupyter often shows a dialog to confirm.
        # Let's assume we just click "OK" or "Upload". This selector might need adjustment.
        # For many modern interfaces, the upload starts automatically.
        
        logger.info(f"Successfully uploaded '{local_file_path}'.")
        return f"Success: File '{os.path.basename(local_file_path)}' uploaded."

    except Exception as e:
        logger.error(f"Error during file upload: {e}", exc_info=True)
        return f"Error: Could not upload file. Reason: {e}"
