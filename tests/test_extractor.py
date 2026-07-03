"""Tests for the resume file text extractor."""

from unittest.mock import patch

import pytest

from api.extractor import extract_text


class TestExtractor:
    """Tests for extract_text()."""

    def test_extract_txt(self):
        """TXT content should be decoded as UTF-8."""
        content = b"AI/ML Engineer with Python experience"
        result = extract_text(content, "resume.txt")
        assert result == "AI/ML Engineer with Python experience"

    def test_extract_txt_strips_whitespace(self):
        """TXT extraction should strip leading/trailing whitespace."""
        content = b"  \nResume text\n  "
        result = extract_text(content, "resume.txt")
        assert result == "Resume text"

    @patch("api.extractor._extract_pdf", return_value="PDF extracted text")
    def test_extract_pdf(self, mock_extract):
        """PDF extraction should delegate to _extract_pdf."""
        result = extract_text(b"fake pdf content", "resume.pdf")
        assert result == "PDF extracted text"
        mock_extract.assert_called_once_with(b"fake pdf content")

    @patch("api.extractor._extract_docx", return_value="DOCX extracted text")
    def test_extract_docx(self, mock_extract):
        """DOCX extraction should delegate to _extract_docx."""
        result = extract_text(b"fake docx content", "resume.docx")
        assert result == "DOCX extracted text"
        mock_extract.assert_called_once_with(b"fake docx content")

    def test_extract_unsupported_format(self):
        """Unsupported file extensions should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported file format"):
            extract_text(b"content", "resume.png")

    def test_extract_empty_txt(self):
        """Empty TXT file should return empty string."""
        result = extract_text(b"", "resume.txt")
        assert result == ""

    @patch("api.extractor._extract_pdf", side_effect=ValueError("PDF parse error"))
    def test_extract_pdf_failure_propagates(self, mock_extract):
        """PDF extraction failure should propagate as ValueError."""
        with pytest.raises(ValueError, match="PDF parse error"):
            extract_text(b"bad pdf", "resume.pdf")
