import asyncio
import re
from playwright.async_api import Playwright, async_playwright, expect


async def run(playwright: Playwright) -> None:
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context(storage_state="auth.json")
    page = await context.new_page()
    await page.goto("https://jupyter.org/try-jupyter/lab/")
    await page.get_by_text("Python (Pyodide)").first.click()
    await page.get_by_role("textbox").click()
    await page.locator(".lm-Widget.jp-CodeMirrorEditor").click()
    await page.get_by_role("textbox").locator("div").click()
    await page.locator("div").filter(has_text=re.compile(r"^hello$")).first.click()
    await page.get_by_text("hello").click()
    await page.get_by_text("hello").click()
    await page.get_by_role("textbox").click()
    await page.locator("div").filter(has_text=re.compile(r"^hello$")).first.click()
    await page.get_by_role("textbox").press("ArrowRight")
    await page.close()

    # ---------------------
    await context.close()
    await browser.close()


async def main() -> None:
    async with async_playwright() as playwright:
        await run(playwright)


asyncio.run(main())
