# Recorded actions for: colab_run_current_cell.py

await page.get_by_text('Python (Pyodide)').first.click()
await page.get_by_role('textbox').locator('div').click()
await page.get_by_role('button', name='Run this cell and advance').click()
await page.get_by_label('Code Cell Content', exact=True).get_by_role('textbox').click()
page.once('dialog', lambda dialog: dialog.dismiss())
await page.get_by_label('Main Content').get_by_text('Untitled.ipynb').click()