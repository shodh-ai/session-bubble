# in aurora_agent/parsers/docs_parser.py (THE FINAL, UPGRADED VERSION)
from playwright.async_api import Page
from .base_parser import BaseParser

class DocsParser(BaseParser):
    """
    A specialized parser that understands the HTML structure of Google Docs
    to identify the main text canvas, toolbars, and menus.
    """
    async def get_interactive_elements(self, page: Page) -> list[dict]:
        print("--- Using Upgraded DocsParser ---")
        elements_info = []

        # --- THIS IS THE CRITICAL UPGRADE ---
        
        # 1. Find the main text area (as before)
        try:
            canvas_locator = "div[role='document']"
            await page.wait_for_selector(canvas_locator, timeout=3000)
            elements_info.append({
                "element_id": "docs-main-canvas",
                "description": "The main document editing area where text is typed.",
                "playwright_locator": f"page.locator(\"{canvas_locator}\")"
            })
        except Exception:
            pass

        # 2. Find ALL toolbar buttons and dropdowns by their aria-label
        # This will find "Bold", "Text color", and the crucial "Styles" dropdown.
        toolbar_buttons = await page.locator(".goog-toolbar-button, .goog-toolbar-menu-button").all()
        for i, button in enumerate(toolbar_buttons):
            label = await button.get_attribute("aria-label")
            if label:
                clean_label = label.split(" (")[0]
                elements_info.append({
                    "element_id": f"docs-toolbar-{i}",
                    "description": f"Toolbar button or dropdown: '{clean_label}'",
                    "playwright_locator": f"page.get_by_aria_label('{label}', exact=True)"
                })

        # 3. Find ALL visible menu items
        # This is for when a menu (like 'Styles') is already open. This will find "Heading 1".
        menu_items = await page.locator("[role^='menuitem']").all()
        for i, item in enumerate(menu_items):
            # is_visible() check is crucial here because many menu items exist but are hidden.
            if await item.is_visible():
                text = await item.text_content()
                if text:
                    elements_info.append({
                        "element_id": f"docs-menuitem-{i}",
                        "description": f"Menu item: '{text.strip()}'",
                        "playwright_locator": f"page.get_by_role('menuitemcheckbox', name='{text.strip()}')"
                    })

        return elements_info