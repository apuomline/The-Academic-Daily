"""PDF parser for extracting introduction and contributions from arXiv papers."""

import re
import hashlib
import requests
import fitz  # PyMuPDF
from typing import Optional, Dict, Tuple
from pathlib import Path
from datetime import datetime, timedelta


class PDFParser:
    """Parse PDF to extract introduction and contribution sections."""

    def __init__(self, download_dir: str = "cache/pdfs", cache_days: int = 7):
        """Initialize PDF parser.

        Args:
            download_dir: Directory to store downloaded PDFs
            cache_days: Number of days to keep cached PDFs
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.cache_days = cache_days

    def _get_cache_path(self, arxiv_id: str) -> Path:
        """Get cache path for a paper.

        Args:
            arxiv_id: arXiv ID for naming the file

        Returns:
            Path to cached PDF
        """
        return self.download_dir / f"{arxiv_id}.pdf"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cached file is still valid.

        Args:
            cache_path: Path to cached file

        Returns:
            True if cache is valid
        """
        if not cache_path.exists():
            return False

        # Check file age
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime
        return age < timedelta(days=self.cache_days)

    def download_pdf(self, pdf_url: str, arxiv_id: str) -> Optional[Path]:
        """Download PDF from arXiv with caching.

        Args:
            pdf_url: URL to the PDF
            arxiv_id: arXiv ID for naming the file

        Returns:
            Path to downloaded PDF or None if failed
        """
        cache_path = self._get_cache_path(arxiv_id)

        # Return cached version if valid
        if self._is_cache_valid(cache_path):
            return cache_path

        try:
            response = requests.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()

            # Download to temporary file first
            temp_path = cache_path.with_suffix('.tmp')
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Rename to final path
            temp_path.replace(cache_path)

            return cache_path

        except Exception as e:
            # Clean up temporary file if exists
            if temp_path.exists():
                temp_path.unlink()
            return None

    def extract_introduction(self, pdf_path: Path, max_pages: int = 4) -> Optional[str]:
        """Extract introduction section from PDF.

        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to search for introduction

        Returns:
            Introduction text or None if not found
        """
        try:
            doc = fitz.open(pdf_path)
            text = ""

            # Read first few pages (introduction is usually early)
            for page_num in range(min(max_pages, len(doc))):
                page = doc[page_num]
                text += f"\n--- Page {page_num + 1} ---\n"
                text += page.get_text()

            doc.close()

            # Try to find introduction section
            intro_match = self._find_introduction_section(text)
            if intro_match:
                return intro_match

            # If no clear section, return first portion
            return self._extract_first_portion(text)

        except Exception as e:
            return None

    def extract_contributions(self, intro_text: str) -> list:
        """Extract contribution points from introduction text.

        Args:
            intro_text: Introduction section text

        Returns:
            List of contribution points
        """
        contributions = []

        # Common patterns for contribution sections (expanded)
        patterns = [
            r"(?:Our\s+)?(?:main\s+)?contributions?(?:\s+(?:are|include|as follows))?\s*:?\s*(.*?)(?=\n\s*(?:\d+\.?[A-Z]?|\n\n|\Z))",
            r"(?:This\s+(?:paper|work)\s+(?:makes?|presents?)(?:\s+the\s+)?following\s+contributions?)\s*:?\s*(.*?)(?=\n\s*(?:\d+\.?[A-Z]?|\n\n|\Z))",
            r"(?:We\s+(?:make|have\s+made)\s+the\s+following\s+contributions?)\s*:?\s*(.*?)(?=\n\s*(?:\d+\.?[A-Z]?|\n\n|\Z))",
            r"(?:The\s+main\s+contributions?(?:\s+of\s+this\s+(?:paper|work))?\s+(?:are|include))\s*:?\s*(.*?)(?=\n\s*(?:\d+\.?[A-Z]?|\n\n|\Z))",
            r"Contributions?\s*:?\s*(.*?)(?=\n\s*(?:\d+\.?[A-Z]?|\n\n|\Z))",
        ]

        for pattern in patterns:
            try:
                match = re.search(pattern, intro_text, re.IGNORECASE | re.DOTALL)
                if match:
                    contrib_text = match.group(1)
                    # Split by common delimiters - use re.escape for safety
                    split_pattern = r'(?:;\s*\n?|\n\s*[-•]\s*|\n\s*\d+[).]\s*|\n\s*[a-z]\)\s*)'
                    points = re.split(split_pattern, contrib_text)
                    contributions = [p.strip() for p in points if p.strip() and len(p.strip()) > 10]
                    if contributions:
                        return contributions[:5]  # Limit to top 5
            except re.error as e:
                # If regex fails, skip this pattern and try the next one
                import logging
                logging.warning(f"Regex pattern failed: {e}")
                continue

        # If no explicit contributions found, return empty list for LLM to parse
        return []

    def _find_introduction_section(self, text: str) -> Optional[str]:
        """Find introduction section in text.

        Args:
            text: Full PDF text

        Returns:
            Introduction text or None
        """
        # Common introduction headers (expanded patterns)
        intro_patterns = [
            r"\n\s*1\s+\.?\s*Introduction\s*\n",
            r"\n\s*I\s+\.?\s*INTRODUCTION\s*\n",
            r"\n\s*INTRODUCTION\s*\n",
            r"\n\s*Introduction\s*\n",
            r"\n\s*1\s+\.?\s*INTRODUCTION\s*\n",
        ]

        for pattern in intro_patterns:
            try:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    start = match.start()
                    # Find end of introduction (next section or References)
                    end_patterns = [
                        r"\n\s*2\s+\.?\s*[A-Z][a-z]+\s*\n",  # Section 2
                        r"\n\s*II\s+\.?\s*[A-Z]+\s*\n",  # Section II
                        r"\n\s*[A-Z][A-Z]+\s*\n",  # All caps section
                        r"\n\s*R\s*elated\s+W\s*ork",  # Related Work
                        r"\n\s*R\s*elated\s+W\s*orks",
                        r"\n\s*M\s*ethod",
                    ]

                    best_end = None
                    for end_pattern in end_patterns:
                        try:
                            search_text = text[start+100:]
                            end_match = re.search(end_pattern, search_text, re.IGNORECASE)
                            if end_match:
                                end = start + 100 + end_match.start()
                                if best_end is None or end < best_end:
                                    best_end = end
                        except re.error:
                            # Skip this end pattern if it fails
                            continue

                    if best_end:
                        return text[start:best_end].strip()
                    else:
                        # Limit to ~4000 chars
                        return text[start:start+4000].strip()
            except re.error as e:
                # Skip this intro pattern if it fails
                import logging
                logging.warning(f"Intro pattern search failed: {e}")
                continue

        return None

    def _extract_first_portion(self, text: str, max_chars: int = 3000) -> str:
        """Extract first portion of text as fallback.

        Args:
            text: Full text
            max_chars: Maximum characters to extract

        Returns:
            First portion of text
        """
        # Skip header/abstract area
        lines = text.split('\n')

        # Look for start of main content
        start_idx = 0
        for i, line in enumerate(lines):
            # Skip very short lines and all uppercase headers
            if len(line) > 80 and not line.isupper():
                start_idx = i
                break

        result = '\n'.join(lines[start_idx:start_idx+80])
        return result[:max_chars]

    def parse_paper(self, arxiv_id: str, pdf_url: str) -> Dict[str, Optional[str]]:
        """Parse paper to extract introduction and contributions.

        Args:
            arxiv_id: arXiv ID
            pdf_url: URL to PDF

        Returns:
            Dictionary with intro_text and contributions.
            Returns None values if parsing fails.
        """
        # Download PDF
        pdf_path = self.download_pdf(pdf_url, arxiv_id)
        if not pdf_path:
            return {"intro_text": None, "contributions": None, "success": False}

        # Extract introduction
        intro_text = self.extract_introduction(pdf_path)
        if not intro_text:
            return {"intro_text": None, "contributions": None, "success": False}

        # Extract contributions
        contributions = self.extract_contributions(intro_text)

        return {
            "intro_text": intro_text,
            "contributions": contributions if contributions else None,
            "success": True,
        }

    def clean_old_cache(self) -> int:
        """Clean up old cached PDF files.

        Returns:
            Number of files removed
        """
        count = 0
        cutoff = datetime.now() - timedelta(days=self.cache_days)

        for pdf_file in self.download_dir.glob("*.pdf"):
            if pdf_file.is_file():
                mtime = datetime.fromtimestamp(pdf_file.stat().st_mtime)
                if mtime < cutoff:
                    pdf_file.unlink()
                    count += 1

        return count
