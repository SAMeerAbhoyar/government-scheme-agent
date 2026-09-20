"""
Document Parser Stub (Phase 2 Placeholder).
Parses raw HTML and PDF documents into clean markdown and text segments.
"""
from typing import Dict, Any

class DocumentParser:
    def parse_document(self, content_bytes: bytes, mime_type: str) -> Dict[str, Any]:
        """
        Stub method to parse PDF / HTML content.
        """
        return {"text": "", "metadata": {}}
