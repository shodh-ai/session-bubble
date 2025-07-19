# in aurora_agent/tools/sheets/tool.py
import logging
import json
import asyncio
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
    
    async def delete_sheet(self, name: str) -> str:
        """Deletes a sheet (tab) from the spreadsheet."""
        sheet_id = await self._get_sheet_id(name)
        if sheet_id is None:
            # This is not an error, the sheet just doesn't exist to be deleted.
            return f"Info: Sheet '{name}' not found, no action taken."
        
        request = {
            'deleteSheet': {
                'sheetId': sheet_id
            }
        }
        
        # Clear the sheet ID from our cache after deleting it
        if name in self._sheet_id_cache:
            del self._sheet_id_cache[name]
            
        return await self._execute_batch_update([request], f"Deleted sheet '{name}'.")
    
    async def create_sheet(self, title: str) -> str:
        """Creates a new sheet (tab) with the given title."""
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, self.client.create_sheet, title
        )
        if response["status"] == "SUCCESS":
            return f"Successfully created sheet '{title}'."
        else:
            return f"Error creating sheet: {response['message']}"
    async def _get_sheet_id(self, sheet_name: str) -> Union[int, None]:
        """Gets the ID of a sheet by its name, caching the result."""
        if sheet_name in self._sheet_id_cache:
            return self._sheet_id_cache[sheet_name]
        
        try:
            loop = asyncio.get_running_loop()
            # The Google API client is synchronous, so we run it in an executor
            # to avoid blocking the async event loop.
            spreadsheet_metadata = await loop.run_in_executor(
                None, 
                lambda: self.client.service.spreadsheets().get(spreadsheetId=self.client.spreadsheet_id).execute()
            )
            
            sheets = spreadsheet_metadata.get('sheets', [])
            for sheet in sheets:
                props = sheet.get('properties', {})
                if props.get('title') == sheet_name:
                    sheet_id = props.get('sheetId')
                    self._sheet_id_cache[sheet_name] = sheet_id
                    return sheet_id
            
            logger.warning(f"Sheet '{sheet_name}' not found in spreadsheet.")
            return None
        except Exception as e:
            logger.error(f"API error while getting sheet ID for '{sheet_name}': {e}", exc_info=True)
            return None

    async def _execute_batch_update(self, requests: list, success_message: str) -> str:
        """The private workhorse method that sends batch requests to the API."""
        if not requests:
            return "Error: No requests to execute."
        try:
            body = {'requests': requests}
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.service.spreadsheets().batchUpdate(
                    spreadsheetId=self.client.spreadsheet_id, body=body
                ).execute()
            )
            logger.info(f"Batch update successful: {success_message}")
            return f"Success: {success_message}"
        except Exception as e:
            logger.error(f"Batch update failed: {e}", exc_info=True)
            return f"Error: {e}"
    async def remove_bold_format(self, cell: str) -> str:
        """
        Removes bold formatting from a cell by overwriting it with an unformatted value.
        A simple and effective reset method for testing.
        """
        # Get the current value first
        value_response = self.client.get_cell_value(cell)
        current_value = value_response.get("data", "")
        
        # Re-write the same value, which resets the format to default
        response = self.client.set_cell_value(cell, current_value)
        
        if response['status'] == 'SUCCESS':
            return f"Success: Reset format for cell '{cell}'."
        return f"Error: {response['message']}"
    
    async def clear_range(self, range_str: str) -> str:
        """Deletes all values within a specified range, leaving the cells empty."""
        response = self.client.clear_range(range_str)
        if response['status'] == 'SUCCESS':
            return f"Success: Cleared range '{range_str}'."
        return f"Error: {response['message']}"
    
    async def list_sheets(self) -> str:
        """Lists all sheet names in the spreadsheet."""
        try:
            loop = asyncio.get_running_loop()
            # Get spreadsheet metadata to list all sheets
            spreadsheet_metadata = await loop.run_in_executor(
                None, 
                lambda: self.client.service.spreadsheets().get(spreadsheetId=self.client.spreadsheet_id).execute()
            )
            
            sheets = spreadsheet_metadata.get('sheets', [])
            sheet_names = [sheet.get('properties', {}).get('title', 'Unknown') for sheet in sheets]
            
            return json.dumps({
                "status": "SUCCESS",
                "sheets": sheet_names,
                "count": len(sheet_names)
            })
        except Exception as e:
            logger.error(f"Error listing sheets: {e}", exc_info=True)
            return json.dumps({
                "status": "ERROR",
                "message": str(e)
            })
    
    async def get_sheet_charts(self, sheet_name: str) -> str:
        """Gets information about charts in a specific sheet for verification."""
        try:
            loop = asyncio.get_running_loop()
            # Get spreadsheet with charts field included
            spreadsheet_metadata = await loop.run_in_executor(
                None, 
                lambda: self.client.service.spreadsheets().get(
                    spreadsheetId=self.client.spreadsheet_id,
                    fields="sheets/charts,sheets/properties"
                ).execute()
            )
            
            sheets = spreadsheet_metadata.get('sheets', [])
            target_sheet = None
            
            # Find the target sheet
            for sheet in sheets:
                if sheet.get('properties', {}).get('title') == sheet_name:
                    target_sheet = sheet
                    break
            
            if not target_sheet:
                return json.dumps({
                    "status": "ERROR",
                    "message": f"Sheet '{sheet_name}' not found"
                })
            
            charts = target_sheet.get('charts', [])
            
            return json.dumps({
                "status": "SUCCESS",
                "charts": charts,
                "count": len(charts),
                "sheet_name": sheet_name
            })
            
        except Exception as e:
            logger.error(f"Error getting charts for sheet '{sheet_name}': {e}", exc_info=True)
            return json.dumps({
                "status": "ERROR",
                "message": str(e)
            })
    
    async def write_range(self, range_str: str, data_json: str) -> str:
        """Writes data to a range from JSON string (for test setup)."""
        try:
            data = json.loads(data_json)
            loop = asyncio.get_running_loop()
            
            body = {
                'values': data
            }
            
            await loop.run_in_executor(
                None,
                lambda: self.client.service.spreadsheets().values().update(
                    spreadsheetId=self.client.spreadsheet_id,
                    range=range_str,
                    valueInputOption='RAW',
                    body=body
                ).execute()
            )
            
            return f"Success: Wrote data to range '{range_str}'."
            
        except Exception as e:
            logger.error(f"Error writing to range '{range_str}': {e}", exc_info=True)
            return f"Error: {e}"
