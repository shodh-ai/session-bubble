# in aurora_agent/tools/sheets/tool.py
import logging
import json
from typing import Union
from .api_client import SheetsAPIClient
import inspect

logger = logging.getLogger(__name__)

class SheetsTool:
    """A comprehensive toolkit for interacting with a Google Sheet via its API."""

    def __init__(self, client: SheetsAPIClient):
        """Initializes the tool with a live, authenticated client."""
        self.client = client
        self._sheet_id_cache = {}

    async def read_cell(self, cell: str) -> str:
        """Reads and returns the value of a single cell (e.g., 'A1', 'Sheet2!B5')."""
        response = self.client.get_cell_value(cell)
        if response['status'] == 'SUCCESS':
            return f"Success: Cell '{cell}' has value: {response['data']}"
        return f"Error: {response['message']}"

    async def write_cell(self, cell: str, value: str) -> str:
        """Writes a new value into a single cell. Use for targeted updates."""
        response = self.client.set_cell_value(cell, value)
        if response['status'] == 'SUCCESS':
            return f"Success: Wrote '{value}' to cell '{cell}'."
        return f"Error: {response['message']}"
    
    async def get_cell_format(self, cell: str) -> str:
        """Gets the formatting of a cell, like bold status. Returns a JSON string."""
        # This uses a more advanced part of the Sheets API
        response = self.client.get_formatting(cell) # A new function you'll add to the client
        if response['status'] == 'SUCCESS':
            return json.dumps(response['data'])
        return f"Error: {response['message']}"
    
    async def clear_range(self, range_str: str) -> str:
        """Deletes all values within a specified range, leaving the cells empty."""
        response = self.client.clear_range(range_str)
        if response['status'] == 'SUCCESS':
            return f"Success: Cleared range '{range_str}'."
        return f"Error: {response['message']}"
