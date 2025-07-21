# Recorded actions for: create_chart_in_sheets

await page.get_by_role('menuitem', name='Insert').click()
await page.get_by_role('menuitem', name='Chart h', exact=True).locator('div').first.click()
page1 = await context.new_page()