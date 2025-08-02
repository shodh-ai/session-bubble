# File: session-bubble/aurora_agent/tools/jupyter/screenshot_feedback.py

import logging
import base64
import json
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class ScreenshotFeedbackSystem:
    """System to capture screenshots after actions and send them to LangGraph for feedback"""
    
    def __init__(self, langgraph_url: str = "http://host.docker.internal:8080"):
        self.langgraph_url = langgraph_url
        self.feedback_endpoint = f"{langgraph_url}/screenshot_feedback"
        
    async def capture_and_send_feedback(
        self, 
        page, 
        action_name: str, 
        action_result: str, 
        parameters: Dict[str, Any] = None
    ) -> bool:
        """
        Capture a screenshot after an action and send it to LangGraph with context
        
        Args:
            page: Playwright page object
            action_name: Name of the action that was performed
            action_result: Result/status of the action
            parameters: Parameters that were used for the action
            
        Returns:
            bool: True if feedback was sent successfully, False otherwise
        """
        try:
            # Capture screenshot
            screenshot_data = await self._capture_screenshot(page)
            if not screenshot_data:
                logger.warning("Failed to capture screenshot")
                return False
            
            # Prepare feedback payload
            feedback_payload = {
                "timestamp": datetime.now().isoformat(),
                "action": {
                    "name": action_name,
                    "result": action_result,
                    "parameters": parameters or {}
                },
                "screenshot": {
                    "data": screenshot_data,
                    "format": "png",
                    "encoding": "base64"
                },
                "page_info": await self._get_page_info(page)
            }
            
            # Send to LangGraph
            success = await self._send_to_langgraph(feedback_payload)
            
            if success:
                logger.info(f"Screenshot feedback sent for action: {action_name}")
            else:
                logger.warning(f"Failed to send screenshot feedback for action: {action_name}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error in screenshot feedback system: {e}", exc_info=True)
            return False
    
    async def _capture_screenshot(self, page) -> Optional[str]:
        """Capture a screenshot and return as base64 string"""
        try:
            # Capture screenshot as bytes
            screenshot_bytes = await page.screenshot(
                full_page=True,
                type='png'
            )
            
            # Convert to base64
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            logger.debug(f"Captured screenshot: {len(screenshot_base64)} characters")
            return screenshot_base64
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            return None
    
    async def _get_page_info(self, page) -> Dict[str, Any]:
        """Get current page information for context"""
        try:
            page_info = {
                "url": page.url,
                "title": await page.title(),
                "viewport": page.viewport_size
            }
            
            # Try to get Jupyter-specific info if we're on a Jupyter page
            if "jupyter" in page.url.lower():
                try:
                    # Get number of cells
                    cells_count = await page.locator(".jp-Notebook-cell").count()
                    page_info["jupyter_cells_count"] = cells_count
                    
                    # Get active cell info if any
                    active_cells = await page.locator(".jp-Notebook-cell.jp-mod-active").count()
                    page_info["jupyter_active_cells"] = active_cells
                    
                except Exception:
                    # Jupyter info is optional
                    pass
            
            return page_info
            
        except Exception as e:
            logger.error(f"Error getting page info: {e}")
            return {"error": str(e)}
    
    async def _send_to_langgraph(self, feedback_payload: Dict[str, Any]) -> bool:
        """Send feedback payload to LangGraph service"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.feedback_endpoint,
                    json=feedback_payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.debug("Screenshot feedback sent successfully")
                        return True
                    else:
                        logger.warning(f"LangGraph returned status {response.status}")
                        return False
                        
        except aiohttp.ClientError as e:
            logger.warning(f"Network error sending to LangGraph: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending to LangGraph: {e}")
            return False

# Global instance
screenshot_feedback = ScreenshotFeedbackSystem()

async def send_action_feedback(page, action_name: str, action_result: str, parameters: Dict[str, Any] = None):
    """
    Convenience function to send screenshot feedback after an action
    
    Args:
        page: Playwright page object
        action_name: Name of the action that was performed
        action_result: Result/status of the action
        parameters: Parameters that were used for the action
    """
    await screenshot_feedback.capture_and_send_feedback(
        page, action_name, action_result, parameters
    )
