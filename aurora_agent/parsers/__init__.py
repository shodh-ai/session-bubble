# in aurora_agent/parsers/__init__.py
from .base_parser import BaseParser
from .generic_parser import GenericParser
from .sheets_parser import SheetsParser
from .docs_parser import DocsParser
import re
from urllib.parse import urlparse
from .jupyter_parser import JupyterParser

# The registry is a list of tuples: (url_keyword, parser_class)
# The first parser that matches the URL will be used.
PARSER_REGISTRY = [
    (re.compile(r"https://docs\.google\.com/spreadsheets/"), SheetsParser),
    (re.compile(r"https://docs\.google\.com/document/"), DocsParser),
    (re.compile(r"/lab$"), JupyterParser),
]
DEFAULT_PARSER = GenericParser

def get_parser_for_url(url: str) -> BaseParser:
    """
    Finds and instantiates the correct parser for a given URL by
    searching the registry for a matching regular expression.
    """
    # --- THIS IS THE CORRECTED LOGIC ---
    for url_pattern, parser_class in PARSER_REGISTRY:
        # Use the .search() method for regular expressions
        if url_pattern.search(url):
            print(f"DEBUG: URL '{url}' matched pattern for {parser_class.__name__}")
            return parser_class()
    
    # If the loop finishes without finding a match, return the default.
    print(f"DEBUG: URL '{url}' did not match any specific parser. Falling back to GenericParser.")
    return DEFAULT_PARSER()
