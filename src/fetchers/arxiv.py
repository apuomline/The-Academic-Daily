"""arXiv API fetcher module."""

import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional
from urllib.parse import quote

import requests

# arXiv API namespaces
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_NS = {"arxiv": "http://arxiv.org/schemas/atom"}
# Combined for easier lookup
NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


@dataclass
class Paper:
    """Represents an academic paper from arXiv."""

    arxiv_id: str
    title: str
    summary: str
    abstract: str
    published: str
    updated: str
    authors: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    pdf_url: Optional[str] = None
    source: str = "arxiv"

    @property
    def version(self) -> str:
        """Extract version from arXiv ID (e.g., 'v1' from '2304.12345v1')."""
        if "v" in self.arxiv_id:
            return f"v{self.arxiv_id.split('v')[-1]}"
        return "v1"

    @property
    def published_date(self) -> datetime:
        """Parse published date string to datetime object."""
        # Remove timezone suffix and parse
        date_str = self.published.replace("Z", "").replace("+00:00", "")
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            # Fallback for different date formats
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(date_str.split(".")[0], fmt)
                except ValueError:
                    continue
            return datetime.now()

    @property
    def updated_date(self) -> datetime:
        """Parse updated date string to datetime object."""
        date_str = self.updated.replace("Z", "").replace("+00:00", "")
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(date_str.split(".")[0], fmt)
                except ValueError:
                    continue
            return datetime.now()

    @property
    def display_date(self) -> str:
        """Return published date in YYYY-MM-DD format."""
        return self.published_date.strftime("%Y-%m-%d")

    def __hash__(self) -> int:
        """Hash based on arXiv ID for deduplication."""
        return hash(self.arxiv_id)

    def __eq__(self, other: object) -> bool:
        """Equality based on arXiv ID."""
        if not isinstance(other, Paper):
            return NotImplemented
        return self.arxiv_id == other.arxiv_id


class ArXivFetcher:
    """Fetch papers from arXiv API."""

    def __init__(
        self,
        api_url: str = "http://export.arxiv.org/api/query",
        max_results: int = 100,
        request_delay: float = 3.0,
    ):
        """Initialize ArXiv fetcher.

        Args:
            api_url: arXiv API endpoint URL
            max_results: Maximum number of results per query
            request_delay: Delay between requests in seconds (arXiv recommends 3+ seconds)
        """
        self.api_url = api_url
        self.max_results = max_results
        self.request_delay = request_delay
        self._last_request_time: Optional[float] = None

    def _respect_rate_limit(self) -> None:
        """Ensure minimum delay between requests."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.request_delay:
                time.sleep(self.request_delay - elapsed)
        self._last_request_time = time.time()

    def _build_query(
        self,
        keywords: str,
        date_range: Optional[tuple[str, str]] = None,
        categories: Optional[List[str]] = None,
    ) -> str:
        """Build arXiv search query string.

        Args:
            keywords: Search keywords (e.g., "medical image segmentation")
            date_range: Tuple of (start_date, end_date) in YYYYMMDD format
            categories: List of arXiv categories (e.g., ["cs.CV", "cs.LG"])

        Returns:
            Formatted query string for arXiv API (will be URL-encoded by requests)
        """
        # Split keywords into individual terms and join with AND
        # This improves search results for multi-word queries
        terms = keywords.strip().split()
        if len(terms) == 1:
            keyword_query = f"all:{terms[0]}"
        else:
            # Use AND to combine terms for better precision
            # Use spaces between AND (requests will encode them properly)
            keyword_query = " AND ".join([f"all:{t}" for t in terms])

        query_parts = [keyword_query]

        # Add date range filter
        # Note: arXiv uses GMT timezone. End date should be next day 0000 to capture late submissions.
        if date_range:
            start_date, end_date = date_range
            query_parts.append(f"submittedDate:[{start_date}0000 TO {end_date}2359]")

        # Add category filter
        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query_parts.append(f"({cat_query})")

        # Join with AND (using spaces, requests will encode)
        query = " AND ".join(query_parts)
        return query

    def _parse_paper(self, entry: ET.Element) -> Paper:
        """Parse a single paper from XML entry element.

        Args:
            entry: XML Element representing a paper entry

        Returns:
            Paper object with parsed data
        """
        # Extract arXiv ID from the id URL
        id_url = entry.find("atom:id", NAMESPACES).text
        arxiv_id = id_url.split("/")[-1]

        # Extract title (remove newlines and extra spaces)
        title_elem = entry.find("atom:title", NAMESPACES)
        title = " ".join(title_elem.text.split()) if title_elem is not None and title_elem.text else ""

        # Extract summary (abstract)
        summary_elem = entry.find("atom:summary", NAMESPACES)
        summary = summary_elem.text.strip() if summary_elem is not None and summary_elem.text else ""
        abstract = summary  # Same content

        # Extract dates
        published = entry.find("atom:published", NAMESPACES).text
        updated = entry.find("atom:updated", NAMESPACES).text

        # Extract authors (support both arXiv and standard Atom formats)
        authors = []
        # Try arXiv format first
        for author in entry.findall("arxiv:author", NAMESPACES):
            name_elem = author.find("arxiv:name", NAMESPACES)
            if name_elem is not None and name_elem.text:
                authors.append(name_elem.text)
        # Fallback to standard Atom format
        if not authors:
            for author in entry.findall("atom:author", NAMESPACES):
                name_elem = author.find("atom:name", NAMESPACES)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text)

        # Extract categories (primary category first)
        categories = []
        primary_category = entry.find("arxiv:primary_category", NAMESPACES)
        if primary_category is not None:
            categories.append(primary_category.get("term"))
        for cat in entry.findall("atom:category", NAMESPACES):
            term = cat.get("term")
            if term and term not in categories:
                categories.append(term)

        # Build PDF URL
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

        return Paper(
            arxiv_id=arxiv_id,
            title=title,
            summary=summary,
            abstract=abstract,
            published=published,
            updated=updated,
            authors=authors,
            categories=categories,
            pdf_url=pdf_url,
        )

    def fetch(
        self,
        keywords: str,
        date_range: Optional[tuple[str, str]] = None,
        categories: Optional[List[str]] = None,
        max_results: Optional[int] = None,
    ) -> List[Paper]:
        """Fetch papers from arXiv.

        Args:
            keywords: Search keywords
            date_range: Optional tuple of (start_date, end_date) in YYYYMMDD format
            categories: Optional list of arXiv categories
            max_results: Override default max_results

        Returns:
            List of Paper objects

        Raises:
            requests.RequestException: If API request fails
        """
        self._respect_rate_limit()

        query = self._build_query(keywords, date_range, categories)
        limit = max_results or self.max_results

        params = {
            "search_query": query,
            "start": 0,
            "max_results": limit,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch from arXiv API: {e}") from e

        # Parse XML response
        root = ET.fromstring(response.content)

        # Extract papers from entries (use atom namespace for entry elements)
        papers = []
        for entry in root.findall("atom:entry", NAMESPACES):
            try:
                paper = self._parse_paper(entry)
                papers.append(paper)
            except (AttributeError, ValueError) as e:
                # Skip malformed entries but log warning
                print(f"Warning: Failed to parse paper entry: {e}")
                continue

        return papers

    def fetch_last_24h(
        self,
        keywords: str,
        categories: Optional[List[str]] = None,
    ) -> List[Paper]:
        """Fetch papers from the last 24 hours.

        Args:
            keywords: Search keywords
            categories: Optional list of arXiv categories

        Returns:
            List of Paper objects from the last 24 hours
        """
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)

        # Format dates as YYYYMMDD
        start_date = yesterday.strftime("%Y%m%d")
        # Use end of current day to capture late submissions
        end_date = (now + timedelta(days=1)).strftime("%Y%m%d")

        return self.fetch(keywords, date_range=(start_date, end_date), categories=categories)
