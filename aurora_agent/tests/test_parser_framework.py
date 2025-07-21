# in tests/test_parser_framework.py
import pytest
from aurora_agent.parsers import get_parser_for_url
from aurora_agent.parsers.docs_parser import DocsParser
from aurora_agent.parsers.sheets_parser import SheetsParser
from aurora_agent.parsers.generic_parser import GenericParser

def test_registry_selects_docs_parser():
    """Verify that a Google Docs URL correctly yields a DocsParser instance."""
    docs_url = "https://docs.google.com/document/d/12345_abc/edit"
    parser = get_parser_for_url(docs_url)
    
    # Assert that the registry returned the correct type of object
    assert isinstance(parser, DocsParser)
    print(f"\nSUCCESS: Registry correctly selected DocsParser for URL: {docs_url}")

def test_registry_selects_sheets_parser():
    """Verify that a Google Sheets URL correctly yields a SheetsParser instance."""
    sheets_url = "https://docs.google.com/spreadsheets/d/67890_xyz/edit"
    parser = get_parser_for_url(sheets_url)
    
    assert isinstance(parser, SheetsParser)
    print(f"\nSUCCESS: Registry correctly selected SheetsParser for URL: {sheets_url}")

def test_registry_falls_back_to_generic_parser():
    """Verify that an unknown URL yields the GenericParser."""
    unknown_url = "https://www.wikipedia.org/"
    parser = get_parser_for_url(unknown_url)
    
    assert isinstance(parser, GenericParser)
    print(f"\nSUCCESS: Registry correctly fell back to GenericParser for URL: {unknown_url}")