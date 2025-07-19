"""Google Docs API client wrapper.

This module provides an easy-to-use wrapper around the Google Docs API. It mirrors the
behaviour and return-structure of `SheetsAPIClient` so that higher-level tools can interact
with either service interchangeably.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Required scope for full read / write access to a Google Doc
SCOPES = ["https://www.googleapis.com/auth/documents"]


class DocsAPIClient:  # pylint: disable=too-few-public-methods
    """A robust client for interacting with the Google Docs API."""

    def __init__(self, key_file_path: str):
        if not key_file_path:
            raise ValueError("`key_file_path` cannot be empty.")

        try:
            creds = service_account.Credentials.from_service_account_file(
                key_file_path, scopes=SCOPES
            )
            # The discovery cache is disabled to avoid needing a cache file on disk.
            self.service = build("docs", "v1", credentials=creds, cache_discovery=False)
            logger.info("Google Docs API client initialised successfully.")
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to initialise DocsAPIClient: %s", exc, exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_request(
        self, request: Any, *, error_message: str = "Google Docs API request failed"
    ) -> Dict[str, Any]:
        """Execute a google-api-python-client request handling common errors.

        The method matches the return structure of `SheetsAPIClient._execute_request` so
        that callers can rely on a consistent contract.
        """
        try:
            response = request.execute()
            return {"status": "SUCCESS", "data": response}
        except HttpError as err:  # pragma: no cover – requires network
            logger.error("%s: %s", error_message, err, exc_info=True)
            return {"status": "ERROR", "message": f"API Error: {err.reason}"}
        except Exception as exc:  # pragma: no cover – unexpected
            logger.error("%s: %s", error_message, exc, exc_info=True)
            return {"status": "ERROR", "message": str(exc)}

    # ------------------------------------------------------------------
    # Public API surface – mirrors endpoints of the Google Docs API we need
    # ------------------------------------------------------------------

    def get_document(self, document_id: str) -> Dict[str, Any]:
        """Retrieve the full document structure.

        Parameters
        ----------
        document_id:
            The id of the Google Doc.
        """
        request = self.service.documents().get(documentId=document_id)
        return self._execute_request(request, error_message="Failed to fetch document")

    def batch_update(self, document_id: str, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send a batchUpdate request.

        `requests` must follow the Google Docs *Requests* schema.
        """
        body = {"requests": requests}
        request = self.service.documents().batchUpdate(documentId=document_id, body=body)
        return self._execute_request(request, error_message="Batch update failed")
