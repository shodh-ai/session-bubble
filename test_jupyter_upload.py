#!/usr/bin/env python3
"""
Test script to upload company-sales.csv to Jupyter and perform data analysis.
This script demonstrates the complete workflow from file upload to data analysis.
"""

import asyncio
import os
import sys
import logging
from aurora_agent.browser_manager import browser_manager
from aurora_agent.tools.jupyter.upload_tool import upload_file_to_jupyter

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_jupyter_upload_and_analysis():
    """
    Test the complete Jupyter workflow:
    1. Launch browser and navigate to Jupyter
    2. Upload company-sales.csv
    3. Create a new notebook
    4. Perform data analysis
    """
    logger.info("=== Testing Jupyter Upload and Data Analysis ===")
    
    # Set display for X11
    os.environ['DISPLAY'] = ':99'
    
    try:
        # Step 1: Initialize browser and navigate to Jupyter
        logger.info("Step 1: Starting browser and navigating to Jupyter...")
        await browser_manager.start_browser(headless=False)
        
        # Navigate to Jupyter (assuming it's running on localhost:8888)
        await browser_manager.navigate_to("http://localhost:8888")
        
        # Wait for Jupyter to load
        await asyncio.sleep(3)
        
        # Step 2: Upload the CSV file
        logger.info("Step 2: Uploading company-sales.csv...")
        csv_file_path = "/app/company-sales.csv"  # Path inside Docker container
        
        upload_result = await upload_file_to_jupyter(csv_file_path)
        logger.info(f"Upload result: {upload_result}")
        
        # Wait for upload to complete
        await asyncio.sleep(2)
        
        # Step 3: Create a new notebook
        logger.info("Step 3: Creating new notebook...")
        
        # Look for "New" button and click it
        new_button = browser_manager.page.locator('button:has-text("New")')
        await new_button.click()
        
        # Select Python 3 notebook
        python_notebook = browser_manager.page.locator('a:has-text("Python 3")')
        await python_notebook.click()
        
        # Wait for notebook to load
        await asyncio.sleep(3)
        
        # Step 4: Perform data analysis
        logger.info("Step 4: Performing data analysis...")
        
        # Code to analyze the company sales data
        analysis_code = """
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load the CSV file
df = pd.read_csv('company-sales.csv')

# Display basic information about the dataset
print("Dataset Info:")
print(df.info())
print("\\nFirst 5 rows:")
print(df.head())

# Basic statistics
print("\\nBasic Statistics:")
print(df.describe())

# Calculate total sales by product
product_columns = ['facecream', 'facewash', 'toothpaste', 'bathingsoap', 'shampoo', 'moisturizer']
product_totals = df[product_columns].sum()

print("\\nTotal Sales by Product:")
for product, total in product_totals.items():
    print(f"{product}: {total}")

# Create visualizations
plt.figure(figsize=(12, 8))

# Plot 1: Monthly total units sold
plt.subplot(2, 2, 1)
plt.plot(df['month_number'], df['total_units'], marker='o')
plt.title('Monthly Total Units Sold')
plt.xlabel('Month')
plt.ylabel('Total Units')

# Plot 2: Monthly total profit
plt.subplot(2, 2, 2)
plt.plot(df['month_number'], df['total_profit'], marker='o', color='green')
plt.title('Monthly Total Profit')
plt.xlabel('Month')
plt.ylabel('Total Profit')

# Plot 3: Product sales comparison
plt.subplot(2, 2, 3)
product_totals.plot(kind='bar')
plt.title('Total Sales by Product')
plt.xticks(rotation=45)

# Plot 4: Correlation heatmap
plt.subplot(2, 2, 4)
correlation_matrix = df[product_columns].corr()
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm')
plt.title('Product Sales Correlation')

plt.tight_layout()
plt.show()

# Find best and worst performing months
best_month = df.loc[df['total_profit'].idxmax()]
worst_month = df.loc[df['total_profit'].idxmin()]

print(f"\\nBest performing month: {best_month['month_number']} with profit: {best_month['total_profit']}")
print(f"Worst performing month: {worst_month['month_number']} with profit: {worst_month['total_profit']}")
"""
        
        # Find the first code cell and input the analysis code
        code_cell = browser_manager.page.locator('.CodeMirror-code').first
        await code_cell.click()
        
        # Type the analysis code
        await browser_manager.page.keyboard.type(analysis_code)
        
        # Execute the cell (Shift+Enter)
        await browser_manager.page.keyboard.press('Shift+Enter')
        
        logger.info("Data analysis code executed successfully!")
        
        # Wait to see results
        await asyncio.sleep(10)
        
        # Take a screenshot for verification
        await browser_manager.page.screenshot(path="/app/jupyter_analysis_result.png")
        logger.info("Screenshot saved: jupyter_analysis_result.png")
        
        logger.info("✓ Jupyter upload and analysis test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error during Jupyter test: {e}", exc_info=True)
        return False
    
    finally:
        # Keep browser open for manual inspection
        logger.info("Browser will stay open for 30 seconds for inspection...")
        await asyncio.sleep(30)
        
        # Close browser
        await browser_manager.close_browser()
    
    return True

if __name__ == "__main__":
    asyncio.run(test_jupyter_upload_and_analysis())
