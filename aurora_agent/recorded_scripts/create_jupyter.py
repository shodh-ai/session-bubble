# Recorded actions for: create_jupyter

await page.locator('.view-line').click()
await page.get_by_role('textbox', name='Editor content;Press Alt+F1').fill('asdfasdfasdfasdfasdfsdaf')
await page.get_by_role('button', name='Run cell').click()
await page.get_by_role('button', name='Run anyway').click()
await page.get_by_text('asdfasdfasdfasdfasdfsdaf', exact=True).dblclick()