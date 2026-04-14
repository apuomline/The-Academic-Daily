"""Tests for multi-source fetchers (Phase 2)."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.fetchers.openalex import OpenAlexFetcher, SemanticScholarFetcher


class TestOpenAlexFetcher:
    """Test OpenAlex fetcher."""

    def test_init(self):
        """Test fetcher initialization."""
        fetcher = OpenAlexFetcher(max_results=50)
        assert fetcher.max_results == 50
        assert fetcher.api_url == "https://api.openalex.org/works"

    def test_build_params_basic(self):
        """Test basic parameter building."""
        fetcher = OpenAlexFetcher()
        params = fetcher._build_params("test query")

        assert params["search"] == "test query"
        assert "per-page" in params

    def test_build_params_with_dates(self):
        """Test parameter building with date filters."""
        fetcher = OpenAlexFetcher()
        params = fetcher._build_params(
            "test",
            filter_date_from="2026-04-01",
            filter_date_to="2026-04-12"
        )

        assert "filter" in params
        assert "from_publication_date:2026-04-01" in params["filter"]
        assert "to_publication_date:2026-04-12" in params["filter"]

    @patch("src.fetchers.openalex.requests.get")
    def test_fetch_success(self, mock_get):
        """Test successful fetch from OpenAlex."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "https://openalex.org/W4123456789",
                    "title": "Test Paper",
                    "publication_date": "2026-04-12",
                    "doi": "10.1234/test",
                    "abstract_inverted_index": {"test": [0], "paper": [1]},
                    "authorships": [
                        {"author": {"display_name": "Test Author"}}
                    ],
                    "concepts": [
                        {"display_name": "Computer Science"}
                    ],
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = OpenAlexFetcher()
        papers = fetcher.fetch("test", max_results=10)

        assert len(papers) == 1
        assert papers[0].title == "Test Paper"
        assert papers[0].source == "openalex"

    @patch("src.fetchers.openalex.requests.get")
    def test_fetch_api_error(self, mock_get):
        """Test API error handling."""
        mock_get.side_effect = Exception("API Error")

        fetcher = OpenAlexFetcher()
        with pytest.raises(Exception):
            fetcher.fetch("test")


class TestSemanticScholarFetcher:
    """Test Semantic Scholar fetcher."""

    def test_init(self):
        """Test fetcher initialization."""
        fetcher = SemanticScholarFetcher()
        assert fetcher.max_results == 100
        assert fetcher.api_url == "https://api.semanticscholar.org/graph/v1/paper/search"

    @patch("src.fetchers.openalex.requests.get")
    def test_fetch_success(self, mock_get):
        """Test successful fetch from Semantic Scholar."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "paperId": "test-paper-id",
                    "title": "Test Paper",
                    "abstract": "Test abstract",
                    "authors": [{"name": "Test Author"}],
                    "year": "2026",
                    "publicationDate": "2026-04-12",
                    "doi": "10.1234/test",
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = SemanticScholarFetcher()
        papers = fetcher.fetch("test", max_results=10)

        assert len(papers) == 1
        assert papers[0].title == "Test Paper"
        assert papers[0].source == "semantic_scholar"

    def test_extract_abstract(self):
        """Test abstract extraction from inverted index."""
        inverted_index = {
            "this": [0],
            "is": [1],
            "a": [2],
            "test": [3],
        }

        abstract = OpenAlexFetcher._extract_abstract(inverted_index)
        assert abstract == "this is a test"
