"""OpenAlex API fetcher module."""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests

from src.fetchers.arxiv import Paper


class OpenAlexFetcher:
    """Fetch papers from OpenAlex API.

    OpenAlex is a fully open catalog of the global research system.
    API docs: https://docs.openalex.org/
    """

    def __init__(
        self,
        api_url: str = "https://api.openalex.org/works",
        max_results: int = 100,
        request_delay: float = 1.0,
        email: Optional[str] = None,
    ):
        """Initialize OpenAlex fetcher.

        Args:
            api_url: OpenAlex API endpoint URL
            max_results: Maximum number of results per query
            request_delay: Delay between requests in seconds
            email: Email for polite API usage (OpenAlex recommends including this)
        """
        self.api_url = api_url
        self.max_results = max_results
        self.request_delay = request_delay
        self.email = email
        self._last_request_time: Optional[float] = None

    def _respect_rate_limit(self) -> None:
        """Ensure minimum delay between requests."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.request_delay:
                time.sleep(self.request_delay - elapsed)
        self._last_request_time = time.time()

    def _build_params(
        self,
        keywords: str,
        filter_date_from: Optional[str] = None,
        filter_date_to: Optional[str] = None,
    ) -> dict:
        """Build API request parameters.

        Args:
            keywords: Search keywords
            filter_date_from: Start date in YYYY-MM-DD format
            filter_date_to: End date in YYYY-MM-DD format

        Returns:
            Dictionary of query parameters
        """
        params = {
            "search": keywords,
            "per-page": min(self.max_results, 200),  # OpenAlex max is 200
            "sort": "publication_date:desc",
        }

        # Add mailto for polite API usage
        if self.email:
            params["mailto"] = self.email

        # Add date filters
        filters = []
        if filter_date_from:
            filters.append(f"from_publication_date:{filter_date_from}")
        if filter_date_to:
            filters.append(f"to_publication_date:{filter_date_to}")

        if filters:
            params["filter"] = ",".join(filters)

        return params

    def fetch(
        self,
        keywords: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> List[Paper]:
        """Fetch papers from OpenAlex.

        Args:
            keywords: Search keywords
            date_from: Start date in YYYY-MM-DD format
            date_to: End date in YYYY-MM-DD format
            max_results: Override default max_results

        Returns:
            List of Paper objects

        Raises:
            requests.RequestException: If API request fails
        """
        self._respect_rate_limit()

        params = self._build_params(keywords, date_from, date_to)
        if max_results:
            params["per-page"] = min(max_results, 200)

        try:
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch from OpenAlex API: {e}") from e

        # Parse JSON response
        data = response.json()
        papers = []

        for work in data.get("results", []):
            try:
                paper = self._parse_work(work)
                papers.append(paper)
            except (KeyError, ValueError, AttributeError) as e:
                # Skip malformed entries
                continue

        return papers

    def _parse_work(self, work: dict) -> Paper:
        """Parse a work from OpenAlex JSON.

        Args:
            work: Work dictionary from OpenAlex API

        Returns:
            Paper object
        """
        # Extract basic info
        title = work.get("title", "")
        paper_id = work.get("id", "")

        # Extract DOI
        doi = work.get("doi", None)
        if doi and doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")

        # Extract abstract (inverted index format)
        abstract = self._extract_abstract(work.get("abstract_inverted_index"))

        # Extract dates
        publication_date = work.get("publication_date")
        published = None
        if publication_date:
            try:
                published = datetime.fromisoformat(publication_date.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Extract authors
        authors = []
        for authorship in work.get("authorships", []):
            author = authorship.get("author", {})
            name = author.get("display_name", "")
            if name:
                authors.append(name)

        # Extract concepts (topics/keywords)
        categories = []
        for concept in work.get("concepts", [])[:5]:  # Top 5 concepts
            keyword = concept.get("display_name", "")
            if keyword:
                categories.append(keyword)

        # Build PDF URL (if available)
        pdf_url = None
        best_location = work.get("best_oa_location", {})
        if best_location:
            pdf_url = best_location.get("pdf_url")

        # Generate arXiv-like ID from OpenAlex ID
        arxiv_id = None
        if "arxiv" in paper_id.lower():
            # Extract arXiv ID if available
            arxiv_id = paper_id.split("/")[-1]

        return Paper(
            arxiv_id=arxiv_id,
            title=title,
            summary=abstract[:500] if abstract else "",  # First 500 chars as summary
            abstract=abstract,
            published=published.isoformat() if published else "",
            updated=published.isoformat() if published else "",
            authors=authors,
            categories=categories,
            pdf_url=pdf_url,
            source="openalex",
        )

    @staticmethod
    def _extract_abstract(inverted_index: Optional[dict]) -> str:
        """Extract abstract from OpenAlex inverted index format.

        Args:
            inverted_index: Inverted index dictionary

        Returns:
            Reconstructed abstract text
        """
        if not inverted_index:
            return ""

        # Reconstruct abstract from inverted index
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))

        # Sort by position and join words
        word_positions.sort(key=lambda x: x[0])
        abstract = " ".join([word for _, word in word_positions])

        return abstract


class SemanticScholarFetcher:
    """Fetch papers from Semantic Scholar API.

    Semantic Scholar is a free, AI-powered research tool.
    API docs: https://api.semanticscholar.org/api-docs/
    """

    def __init__(
        self,
        api_url: str = "https://api.semanticscholar.org/graph/v1/paper/search",
        max_results: int = 100,
        request_delay: float = 1.0,
        api_key: Optional[str] = None,
    ):
        """Initialize Semantic Scholar fetcher.

        Args:
            api_url: Semantic Scholar API endpoint URL
            max_results: Maximum number of results per query
            request_delay: Delay between requests in seconds
            api_key: Optional API key for higher rate limits
        """
        self.api_url = api_url
        self.max_results = max_results
        self.request_delay = request_delay
        self.api_key = api_key
        self._last_request_time: Optional[float] = None

    def _respect_rate_limit(self) -> None:
        """Ensure minimum delay between requests."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.request_delay:
                time.sleep(self.request_delay - elapsed)
        self._last_request_time = time.time()

    def fetch(
        self,
        keywords: str,
        year: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> List[Paper]:
        """Fetch papers from Semantic Scholar.

        Args:
            keywords: Search keywords
            year: Publication year filter
            max_results: Override default max_results

        Returns:
            List of Paper objects

        Raises:
            requests.RequestException: If API request fails
        """
        self._respect_rate_limit()

        params = {
            "query": keywords,
            "limit": min(max_results or self.max_results, 100),
            "fields": "paperId,title,abstract,authors,year,publicationDate,doi,openAccessPdf",
        }

        # Add year filter
        if year:
            params["year"] = year

        # Add API key if provided
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        try:
            response = requests.get(self.api_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch from Semantic Scholar API: {e}") from e

        # Parse JSON response
        data = response.json()
        papers = []

        for item in data.get("data", []):
            try:
                paper = self._parse_paper(item)
                papers.append(paper)
            except (KeyError, ValueError, AttributeError):
                continue

        return papers

    def _parse_paper(self, item: dict) -> Paper:
        """Parse a paper from Semantic Scholar JSON.

        Args:
            item: Paper dictionary from Semantic Scholar API

        Returns:
            Paper object
        """
        # Extract basic info
        title = item.get("title", "")
        paper_id = item.get("paperId", "")

        # Extract DOI
        doi = item.get("doi", None)

        # Extract abstract
        abstract = item.get("abstract", "")

        # Extract dates
        pub_date = item.get("publicationDate") or item.get("year")
        published = None
        if pub_date:
            try:
                if isinstance(pub_date, str) and len(pub_date) == 4:
                    published = datetime(int(pub_date), 1, 1)
                else:
                    published = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Extract authors
        authors = []
        for author in item.get("authors", []):
            name = author.get("name", "")
            if name:
                authors.append(name)

        # Build PDF URL
        pdf_url = None
        oa_info = item.get("openAccessPdf", {})
        if oa_info:
            pdf_url = oa_info.get("url")

        return Paper(
            arxiv_id=None,
            title=title,
            summary=abstract[:500] if abstract else "",
            abstract=abstract,
            published=published.isoformat() if published else "",
            updated=published.isoformat() if published else "",
            authors=authors,
            categories=[],  # Semantic Scholar doesn't provide categories
            pdf_url=pdf_url,
            source="semantic_scholar",
        )
