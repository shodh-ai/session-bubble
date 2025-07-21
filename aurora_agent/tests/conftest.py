# in aurora_agent/tests/conftest.py
import pytest
import os
from typing import Generator

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from aurora_agent.tools.docs.api_client import DocsAPIClient
from aurora_agent.tools.docs.api_tool import DocsTool

SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]
from dotenv import load_dotenv

@pytest.fixture(scope="session", autouse=True)
def load_env():
    """Automatically load environment variables from .env file for all tests."""
    print("\n--- Loading environment variables from .env for test session ---")
    # Try project root two levels up
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    dotenv_path = os.path.join(project_root, '.env')
    load_dotenv(dotenv_path=dotenv_path)
    
@pytest.fixture(scope="session")
def _creds() -> "service_account.Credentials":
    # Prefer a dedicated key for Docs if provided
    key_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_PATH_DOCS") or os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_PATH")
    if not key_path:
        pytest.skip("GOOGLE_SERVICE_ACCOUNT_KEY_PATH_DOCS or GOOGLE_SERVICE_ACCOUNT_KEY_PATH env var not set – skipping Docs tests")

    # Remove any accidental wrapping quotes that may come from .env files
    key_path = key_path.strip("'\" ")

    if not os.path.isabs(key_path):
        key_path = os.path.abspath(key_path)

    return service_account.Credentials.from_service_account_file(key_path, scopes=SCOPES)


@pytest.fixture(scope="session")
def docs_tool(_creds):
    client = DocsAPIClient.__new__(DocsAPIClient)  # bypass __init__ to inject creds
    client.service = build("docs", "v1", credentials=_creds, cache_discovery=False)
    client._execute_request = DocsAPIClient._execute_request.__get__(client, DocsAPIClient)  # type: ignore[attr-defined]
    docs_tool_instance = DocsTool(client=client)  # type: ignore[arg-type]
    return docs_tool_instance


@pytest.fixture()
def test_document_id(_creds) -> Generator[str, None, None]:
    """Yield a document ID for testing.

    If `TEST_DOC_ID` is supplied in the environment we will re-use that document
    (it must already be shared with the service account). Otherwise we create a
    temporary blank Google Doc and delete it afterwards.
    """
    pre_existing = os.getenv("TEST_DOC_ID")
    if pre_existing:
        yield pre_existing.strip("'\" ")
        return  # do not delete

    docs_service = build("docs", "v1", credentials=_creds, cache_discovery=False)
    doc = docs_service.documents().create(body={"title": "pytest-docs-tool"}).execute()
    doc_id = doc["documentId"]
    try:
        yield doc_id
    finally:
        # Clean up via Drive API for the temp doc
        drive_service = build("drive", "v3", credentials=_creds, cache_discovery=False)
        try:
            drive_service.files().delete(fileId=doc_id).execute()
        except HttpError:
            pass

@pytest.fixture(scope="function") # "function" scope means it runs ONCE PER TEST
async def browser_manager():
    """
    A fixture that provides a fully initialized and cleaned-up BrowserManager
    instance for the duration of a single test function.
    """
    from aurora_agent.browser_manager import BrowserManager
    
    manager = BrowserManager()
    
    # SETUP: Start the browser before the test runs
    auth_file = "auth_state.json"
    if not os.path.exists(auth_file):
        # We need to handle the auth file logic here now
        source_auth_file = "aurora_agent/auth.json"
        if not os.path.exists(source_auth_file):
             pytest.skip("auth.json not found.")
        import shutil
        shutil.copy2(source_auth_file, "auth.json")

    await manager.start_browser(storage_state_path=auth_file)
    
    # Yield the live manager to the test function
    yield manager
    
    # TEARDOWN: Close the browser after the test is finished
    print("\n--- Tearing down browser ---")
    await manager.close_browser()