# File: session-bubble/aurora_agent/recorded_scripts/jupyter_full_lesson.py
# Recorded actions for: jupyter_run_current_cell.py
await page.get_by_title("Python (Pyodide)").first.click()
await page.get_by_role("textbox").locator("div").click()
await page.get_by_text("import numpy as np").click()
await page.get_by_role("button", name="Run this cell and advance").click()
await page.get_by_role("textbox").locator("div").click()
await page.get_by_text("np.random.rand(10)").click()
await page.get_by_role("button", name="Run this cell and advance").click()