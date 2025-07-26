# File: session-bubble/aurora_agent/parsers/base_parser.py
# in aurora_agent/parsers/base_parser.py
from abc import ABC, abstractmethod
from playwright.async_api import Page
from typing import List, Dict, Any

class BaseParser(ABC):
    """
    Abstract base class for web page parsers.
    Parsers are responsible for identifying interactive elements on a page.
    """

    @abstractmethod
    async def get_interactive_elements(self, page: Page) -> List[Dict[str, Any]]:
        """
        Identifies and returns a list of interactive elements from the page.

        Args:
            page: The Playwright Page object to parse.

        Returns:
            A list of dictionaries, where each dictionary represents an
            interactive element and contains its metadata.
        """
        pass
