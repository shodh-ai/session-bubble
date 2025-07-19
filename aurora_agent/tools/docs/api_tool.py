"""High-level, async-friendly wrapper around the Google Docs API client.

The goal of this module is to expose ergonomic coroutine functions that can be
used directly by an agent without worrying about low-level request payloads.
It intentionally mirrors the API surface and return style of the existing
`SheetsTool` so that expert agents can swap between the two services with
minimal branching logic.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import List, Dict, Any

from .api_client import DocsAPIClient

logger = logging.getLogger(__name__)


class DocsTool:  # pylint: disable=too-few-public-methods
    """Utility class offering common Google Docs operations.

    Parameters
    ----------
    client:
        A fully-initialised :class:`DocsAPIClient` instance.
    """

    def __init__(self, client: DocsAPIClient):
        self.client = client

    # ------------------------------------------------------------------
    # Public coroutine helpers
    # ------------------------------------------------------------------

    async def insert_text(self, document_id: str, text: str, index: int = 1) -> str:
        """Insert *text* at *index* in the specified *document*.

        The function returns a simple *Success* / *Error* string mirroring the
        convention established by `SheetsTool`.
        """
        requests: List[Dict[str, Any]] = [
            {
                "insertText": {
                    "location": {"index": index},
                    "text": text,
                }
            }
        ]

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, self.client.batch_update, document_id, requests
        )

        if response.get("status") == "SUCCESS":
            return "Success: Text inserted."
        return f"Error: {response.get('message', 'Unknown failure')}"

    async def get_document_formatting(self, document_id: str) -> str:
        """
        Returns a string describing the formatting of the document's text.
        (This is a simplified representation for testing).
        """
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, self.client.get_document, document_id)

        if response.get("status") != "SUCCESS":
            return f"Error: {response.get('message')}"

        content_elements = response["data"].get("body", {}).get("content", [])
        formatting_descriptions = []
        for elem in content_elements:
            paragraph = elem.get("paragraph")
            if paragraph:
                for para_elem in paragraph.get("elements", []):
                    text_run = para_elem.get("textRun")
                    if text_run:
                        text = text_run.get("content", "").strip()
                        is_bold = text_run.get("textStyle", {}).get("bold", False)
                        if text and is_bold:
                            formatting_descriptions.append(f"text '{text}' is bold")
        
        return ", ".join(formatting_descriptions)
    async def clear_document_content(self, document_id: str) -> str:
        """Deletes all the text content from the document body."""
        # First, get the document to find the end of the content
        content_str = await self.get_document_content(document_id)
        if "Error:" in content_str:
            return content_str
        
        end_index = len(content_str)
        if end_index <= 1:
            return "Success: Document is already empty."

        # Create a request to delete from index 1 (after title) to the end
        requests = [
            {
                "deleteContentRange": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": end_index,
                    }
                }
            }
        ]
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, self.client.batch_update, document_id, requests
        )

        if response.get("status") == "SUCCESS":
            return "Success: Document content cleared."
        return f"Error: {response.get('message', 'Failed to clear document')}"

    async def get_detailed_document_structure(self, document_id: str) -> list[dict]:
        """
        Returns a structured list representing the document's content and formatting.
        """
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, self.client.get_document, document_id)

        if response.get("status") != "SUCCESS":
            return [{"error": response.get("message")}]

        content_elements = response["data"].get("body", {}).get("content", [])
        structure = []
        for elem in content_elements:
            paragraph = elem.get("paragraph")
            if paragraph:
                style = paragraph.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
                for para_elem in paragraph.get("elements", []):
                    text_run = para_elem.get("textRun")
                    if text_run:
                        text = text_run.get("content", "").strip().replace('\n', '')
                        text_style = text_run.get("textStyle", {})
                        is_bold = text_style.get("bold", False)
                        color = text_style.get("foregroundColor", {}).get("color", {}).get("rgbColor")
                        
                        if text:
                            structure.append({
                                "text": text,
                                "paragraph_style": style,
                                "is_bold": is_bold,
                                "color_rgb": color
                            })
        return structure

    async def get_document_content(self, document_id: str) -> str:
        """Return the plain-text content of the document."""
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, self.client.get_document, document_id)

        if response.get("status") != "SUCCESS":
            return f"Error: {response.get('message', 'Failed to fetch document')}"

        document = response["data"]
        # The Docs API returns the document body as a series of structural
        # elements. We walk through them and extract any *textRun* content.
        content_elements = document.get("body", {}).get("content", [])
        full_text_parts: List[str] = []
        for elem in content_elements:
            paragraph = elem.get("paragraph")
            if not paragraph:
                continue
            for para_elem in paragraph.get("elements", []):
                text_run = para_elem.get("textRun")
                if text_run and "content" in text_run:
                    full_text_parts.append(text_run["content"])
        return "".join(full_text_parts).strip()

    # Convenience alias for agents that prefer snake_case naming similar to
    # `SheetsTool.read_cell`.
    async def read_document(self, document_id: str) -> str:  # pragma: no cover
        """Alias of :meth:`get_document_content`."""
        return await self.get_document_content(document_id)


__all__ = ["DocsTool"]
