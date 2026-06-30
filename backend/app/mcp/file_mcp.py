import logging
from typing import Optional
from pathlib import Path
from pypdf import PdfReader

logger = logging.getLogger(__name__)

class FileMCP:
    """
    Model Context Protocol (MCP) layer for File operations.
    Allows agents to parse PDFs and read files.
    """
    def __init__(self):
        pass

    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extracts text from a local PDF file.
        """
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Not a PDF file: {file_path}")

        reader = PdfReader(str(path))
        text_content = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_content.append(text)
                
        return "\n".join(text_content)

file_mcp = FileMCP()
