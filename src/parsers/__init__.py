"""Parsers module for processing and deduplicating papers."""

from .paper import PaperParser, PaperGroup
from .pdf_parser import PDFParser

__all__ = ["PaperParser", "PaperGroup", "PDFParser"]
