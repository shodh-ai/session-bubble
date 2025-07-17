# in aurora_agent/parsers/__init__.py
from .base_parser import BaseParser
from .generic_parser import GenericParser
from .sheets_parser import SheetsParser
from urllib.parse import urlparse

# The registry is a list of tuples: (url_keyword, parser_class)
# The first parser that matches the URL will be used.
PARSER_REGISTRY = [
    ("docs.google.com/spreadsheets", SheetsParser),
    # Add other specific parsers here
]

def get_parser_for_url(url: str) -> BaseParser:
    """
    Selects the appropriate parser for a given URL.

    Args:
        url: The URL of the page to parse.

    Returns:
        An instance of the appropriate parser class.
        Defaults to GenericParser if no specific parser is found.
    """
    for keyword, parser_class in PARSER_REGISTRY:
        if keyword in url:
            return parser_class()
    
    return GenericParser()
