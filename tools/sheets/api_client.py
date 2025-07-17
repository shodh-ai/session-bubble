# in aurora_agent/tools/sheets/api_client.py
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure a logger for this module
logger = logging.getLogger(__name__)

# The specific permissions our service account needs
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

class SheetsAPIClient:
    """A robust client for interacting with the Google Sheets API."""

    def __init__(self, key_file_path: str, spreadsheet_id: str):
        if not spreadsheet_id:
            raise ValueError("spreadsheet_id cannot be empty.")
        
        self.spreadsheet_id = spreadsheet_id
        try:
            creds = service_account.Credentials.from_service_account_file(
                key_file_path, scopes=SCOPES
            )
            self.service = build('sheets', 'v4', credentials=creds)
            logger.info("Google Sheets API client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize SheetsAPIClient: {e}", exc_info=True)
            raise

    def _execute_request(self, request, error_message="Google Sheets API request failed"):
        """A helper method to execute requests and handle common errors."""
        try:
            response = request.execute()
            return {"status": "SUCCESS", "data": response}
        except HttpError as err:
            logger.error(f"{error_message}: {err}", exc_info=True)
            return {"status": "ERROR", "message": f"API Error: {err.reason}"}
        except Exception as e:
            logger.error(f"{error_message}: {e}", exc_info=True)
            return {"status": "ERROR", "message": str(e)}

    def get_cell_value(self, cell: str) -> dict:
        request = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=cell
        )
        response = self._execute_request(request, f"Failed to get value for cell {cell}")
        
        if response["status"] == "SUCCESS":
            values = response["data"].get('values', [])
            response["data"] = values[0][0] if values and values[0] else ""
            
        return response

    def set_cell_value(self, cell: str, value: str) -> dict:
        body = {'values': [[value]]}
        request = self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=cell,
            valueInputOption='USER_ENTERED',
            body=body
        )
        return self._execute_request(request, f"Failed to set value for cell {cell}")

    def get_range_values(self, range_name: str) -> dict:
        request = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name
        )
        response = self._execute_request(request, f"Failed to get values for range {range_name}")
        
        if response["status"] == "SUCCESS":
            response["data"] = response["data"].get('values', [])
            
        return response
    
    def set_range_values(self, range_name: str, values: list) -> dict:
        body = {'values': values}
        request = self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        )
        return self._execute_request(request, f"Failed to set values for range {range_name}")

    def clear_range(self, range_name: str) -> dict:
        request = self.service.spreadsheets().values().clear(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            body={}
        )
        return self._execute_request(request, f"Failed to clear range {range_name}")

    def get_formatting(self, cell: str) -> dict:
        """Gets the formatting of a cell."""
        request = self.service.spreadsheets().get(
            spreadsheetId=self.spreadsheet_id,
            ranges=cell,
            fields='sheets/data/rowData/values/effectiveFormat'
        )
        return self._execute_request(request, f"Failed to get format for cell {cell}")
