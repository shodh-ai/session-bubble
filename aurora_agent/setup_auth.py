# File: session-bubble/aurora_agent/setup_auth.py
# in aurora_agent/setup_auth.py
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # We use a persistent context to store session data
        context = await p.chromium.launch_persistent_context(
            user_data_dir="./playwright_user_data",
            headless=False, # We need to see the browser to log in
        )
        page = await context.new_page()
        
        # Go to Google to trigger the login.
        await page.goto("https://accounts.google.com")
        
        print("\n" + "*"*80)
        print("A browser window has been opened. Please log in to your Google account.")
        print("The script will automatically detect when you are logged in and save the session.")
        print("You do NOT need to close the browser window manually.")
        print("*"*80 + "\n")

        # Wait for navigation to a post-login page. This is more reliable than waiting for a close event.
        # We give a long timeout to allow for 2FA and other login steps.
        try:
            await page.wait_for_url("**/myaccount.google.com/**", timeout=120000) # 2 minute timeout
            print("Login successful! Proceeding to save authentication state.")
        except Exception as e:
            print(f"Did not detect a successful login within the time limit. Error: {e}")
            await context.close()
            return

        # Save the authentication state to a file.
        # This file will contain the cookies and local storage needed for future sessions.
        await context.storage_state(path="auth.json")
        print("Authentication state saved to auth.json")
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
