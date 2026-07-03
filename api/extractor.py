"""Extract text from uploaded resume files (PDF, DOCX, TXT)."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text(content: bytes, filename: str) -> str:
    """Extract text from a resume file.

    Supported formats: ``.pdf``, ``.docx``, ``.txt``.

    Args:
        content: Raw file bytes.
        filename: Original filename used to determine the format.

    Returns:
        Extracted text string.

    Raises:
        ValueError: If the file format is unsupported or extraction fails.
    """
    ext = Path(filename).suffix.lower()

    if ext == ".txt":
        return content.decode("utf-8", errors="replace").strip()

    if ext == ".pdf":
        return _extract_pdf(content)

    if ext == ".docx":
        return _extract_docx(content)

    raise ValueError(f"Unsupported file format: '{ext}'. Accepted: .pdf, .docx, .txt")


def _extract_pdf(content: bytes) -> str:
    """Extract text from a PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ValueError("PyMuPDF is required for PDF extraction")

    try:
        doc = fitz.open(stream=content, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text.strip()
    except Exception as e:
        logger.error("PDF extraction failed: %s", e)
        raise ValueError(f"Failed to extract text from PDF: {e}")


def _extract_docx(content: bytes) -> str:
    """Extract text from a DOCX using python-docx."""
    try:
        from docx import Document
    except ImportError:
        raise ValueError("python-docx is required for DOCX extraction")

    try:
        import io
        doc = Document(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs)
        return text.strip()
    except Exception as e:
        logger.error("DOCX extraction failed: %s", e)
        raise ValueError(f"Failed to extract text from DOCX: {e}")
