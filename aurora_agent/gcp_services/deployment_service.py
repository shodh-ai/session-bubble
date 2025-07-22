# in aurora_agent/gcp_services/deployment_service.py
import logging
import os
from typing import Dict, Any, List, Union, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .apps_script_template import APPS_SCRIPT_CODE

logger = logging.getLogger(__name__)
# The name of our spy script, so we can find it later
SCRIPT_FILENAME = "AuroraAgent_ImprinterSpy_v1"

class ImprinterDeploymentService:
    def __init__(self, user_credentials: Dict[str, Any]):
        """
        Initializes the service with the teacher's OAuth tokens.
        """
        # Create a Credentials object from the tokens stored in your database
        self.creds = Credentials.from_authorized_user_info(user_credentials)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.script_service = build('script', 'v1', credentials=self.creds)

    async def deploy_spy(self, spreadsheet_id: str) -> dict:
        """
        The main method. Deploys the spy script and trigger to a spreadsheet.
        This method is idempotent: if the spy is already deployed, it does nothing.
        """
        logger.info(f"Starting spy deployment for spreadsheet: {spreadsheet_id}")
        try:
            # Step 1: Find the script project bound to this sheet, if it exists.
            script_id = await self._find_bound_script_id(spreadsheet_id)

            if not script_id:
                # Step 2a: If no script exists, create one.
                logger.info("No existing spy script found. Creating a new one.")
                script_id = await self._create_bound_script(spreadsheet_id)
            else:
                logger.info(f"Found existing spy script project with ID: {script_id}")

            # Step 3: Push our latest code into the script file.
            webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:8000/webhook/sheets")
            script_content = APPS_SCRIPT_CODE.replace("{{WEBHOOK_URL}}", webhook_url)
            await self._update_script_content(script_id, script_content)

            # Step 4: Check for and create the trigger.
            await self._create_on_change_trigger(script_id, spreadsheet_id)
            
            logger.info("Spy deployment completed successfully.")
            return {
                "success": True, 
                "message": "Imprinter spy deployed successfully.",
                "script_id": script_id,
                "spreadsheet_id": spreadsheet_id
            }

        except Exception as e:
            logger.error(f"Spy deployment failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _find_bound_script_id(self, file_id: str) -> Optional[str]:
        """Finds a script file specifically created by our service for this sheet."""
        try:
            query = f"'{file_id}' in parents and name='{SCRIPT_FILENAME}' and mimeType='application/vnd.google-apps.script'"
            response = self.drive_service.files().list(q=query, fields="files(id)").execute()
            files = response.get('files', [])
            return files[0]['id'] if files else None
        except HttpError as e:
            logger.error(f"Error finding bound script: {e}")
            return None

    async def _create_bound_script(self, spreadsheet_id: str) -> str:
        """Creates a new Apps Script file bound to the spreadsheet."""
        try:
            file_metadata = {
                'name': SCRIPT_FILENAME,
                'parents': [spreadsheet_id],
                'mimeType': 'application/vnd.google-apps.script'
            }
            script_file = self.drive_service.files().create(body=file_metadata, fields='id').execute()
            script_id = script_file.get('id')
            logger.info(f"Created new bound script with ID: {script_id}")
            return script_id
        except HttpError as e:
            logger.error(f"Error creating bound script: {e}")
            raise

    async def _update_script_content(self, script_id: str, code: str):
        """Pushes code content into an Apps Script project."""
        try:
            request = {
                'files': [{
                    'name': 'Code',
                    'type': 'SERVER_JS',
                    'source': code
                }, {
                    'name': 'appsscript',
                    'type': 'JSON',
                    'source': '{"timeZone":"America/New_York","exceptionLogging":"STACKDRIVER","runtimeVersion":"V8"}'
                }]
            }
            self.script_service.projects().updateContent(
                scriptId=script_id,
                body=request
            ).execute()
            logger.info(f"Updated content for script ID: {script_id}")
        except HttpError as e:
            logger.error(f"Error updating script content: {e}")
            raise

    async def _create_on_change_trigger(self, script_id: str, spreadsheet_id: str):
        """Creates the 'onChange' trigger for our spy script if it doesn't already exist."""
        try:
            # 1. List existing triggers to avoid creating duplicates.
            response = self.script_service.projects().triggers().list(scriptId=script_id).execute()
            triggers = response.get('triggers', [])
            
            for trigger in triggers:
                if trigger.get('function') == 'onSpreadsheetChange':
                    logger.info("onChange trigger already exists. No action needed.")
                    return

            # 2. If no trigger was found, create one.
            logger.info("Creating new onChange trigger...")
            request = {
                'function': 'onSpreadsheetChange',
                'eventTrigger': {
                    'eventType': 'ON_CHANGE',
                    'resourceName': f'spreadsheets/{spreadsheet_id}'
                }
            }
            self.script_service.projects().triggers().create(
                scriptId=script_id,
                body=request
            ).execute()
            logger.info("Successfully created onChange trigger.")
        except HttpError as e:
            logger.error(f"Error creating trigger: {e}")
            raise

    async def remove_spy(self, spreadsheet_id: str) -> dict:
        """
        Removes the spy script from a spreadsheet.
        """
        logger.info(f"Starting spy removal for spreadsheet: {spreadsheet_id}")
        try:
            script_id = await self._find_bound_script_id(spreadsheet_id)
            
            if not script_id:
                return {"success": True, "message": "No spy script found to remove."}
            
            # Remove the script file
            self.drive_service.files().delete(fileId=script_id).execute()
            logger.info(f"Successfully removed spy script: {script_id}")
            
            return {
                "success": True,
                "message": "Spy script removed successfully.",
                "script_id": script_id
            }
        except Exception as e:
            logger.error(f"Spy removal failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_spy_status(self, spreadsheet_id: str) -> dict:
        """
        Checks if a spy script is deployed on the given spreadsheet.
        """
        try:
            script_id = await self._find_bound_script_id(spreadsheet_id)
            
            if not script_id:
                return {
                    "deployed": False,
                    "message": "No spy script found."
                }
            
            # Check if triggers exist
            response = self.script_service.projects().triggers().list(scriptId=script_id).execute()
            triggers = response.get('triggers', [])
            has_trigger = any(t.get('function') == 'onSpreadsheetChange' for t in triggers)
            
            return {
                "deployed": True,
                "script_id": script_id,
                "has_trigger": has_trigger,
                "message": f"Spy script found with {'active' if has_trigger else 'inactive'} trigger."
            }
        except Exception as e:
            logger.error(f"Error checking spy status: {e}", exc_info=True)
            return {"deployed": False, "error": str(e)}
