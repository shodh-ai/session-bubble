# Recorded actions for: colab_run_current_cell.py

await page.get_by_text('Python (Pyodide)').first.click()
await page.get_by_role('button', name='Upload Files').click()
await page.get_by_role('listitem', name='Name: data Created: 7/2/25, 3').click()
page.once('dialog', lambda dialog: dialog.dismiss())
async with page.expect_popup() as page1_info:
    await page.get_by_text('Notebook', exact=True).click()
page1 = await page1_info.value
await page1.get_by_role('dialog').get_by_role('combobox').select_option('{"name":"python"}')
await page1.get_by_role('button', name='Select Kernel').click()
await page1.get_by_text('File', exact=True).click()
page1.once('dialog', lambda dialog: dialog.dismiss())
async with page1.expect_popup() as page2_info:
    await page1.get_by_text('Open…').click()
page2 = await page2_info.value
page1.once('dialog', lambda dialog: dialog.dismiss())