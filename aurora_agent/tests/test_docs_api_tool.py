"""Integration-style unit tests for :pymod:`aurora_agent.tools.docs.api_tool`.

These tests hit the live Google Docs & Drive APIs using the service account
specified via environment variables. They create a temporary document, perform
operations through :class:`DocsTool`, then clean up to leave no trace.
"""
from __future__ import annotations

import os
import asyncio
from typing import Generator

import pytest
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from aurora_agent.tools.docs.api_client import DocsAPIClient
from aurora_agent.tools.docs.api_tool import DocsTool

# Scopes required for both Docs manipulation and Drive file deletion
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]


# --------------------------------------------------------------
# Tests
# --------------------------------------------------------------

@pytest.mark.asyncio
async def test_insert_text_and_verify(docs_tool: DocsTool, test_document_id: str):
    """Insert text into a Google Doc then verify content via the tool."""
    test_text = "Hello, world!"

    insert_resp = await docs_tool.insert_text(test_document_id, test_text, index=1)
    assert insert_resp.startswith("Success"), insert_resp

    # Allow the Docs API a brief moment to process the update
    await asyncio.sleep(1.0)

    content = await docs_tool.get_document_content(test_document_id)
    assert test_text in content
