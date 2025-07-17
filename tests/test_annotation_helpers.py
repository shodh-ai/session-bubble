# in aurora_agent/tests/test_annotation_helpers.py
import pytest
from playwright.async_api import async_playwright
from aurora_agent.ui_tools.annotation_helpers import highlight_element, remove_annotations, HIGHLIGHT_BOX_ID

@pytest.mark.asyncio
async def test_highlight_and_remove():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Navigate to a simple blank page for testing
        await page.goto("data:text/html,<h1>Test Page</h1>")
        
        # 1. Verify the highlight does NOT exist initially
        initial_box = await page.locator(f"#{HIGHLIGHT_BOX_ID}").count()
        assert initial_box == 0

        # 2. Highlight the <h1> element
        h1_locator = page.locator("h1")
        await highlight_element(page, h1_locator)
        
        # 3. Verify the highlight NOW EXISTS
        highlight_box = await page.locator(f"#{HIGHLIGHT_BOX_ID}")
        assert await highlight_box.count() == 1
        assert await highlight_box.is_visible()

        # 4. Remove the highlight
        await remove_annotations(page)
        
        # 5. Verify the highlight is GONE
        final_box = await page.locator(f"#{HIGHLIGHT_BOX_ID}").count()
        assert final_box == 0

        await browser.close()
