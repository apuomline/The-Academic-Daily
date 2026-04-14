"""Tests for arXiv fetcher module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.fetchers.arxiv import ArXivFetcher, Paper


class TestPaper:
    """Test Paper dataclass."""

    def test_version_extraction(self):
        """Test version extraction from arXiv ID."""
        paper = Paper(
            arxiv_id="2304.12345v2",
            title="Test",
            summary="Test",
            abstract="Test",
            published="2026-04-11T10:30:00Z",
            updated="2026-04-11T10:30:00Z",
        )
        assert paper.version == "v2"

    def test_version_no_version(self):
        """Test version extraction when no version in ID."""
        paper = Paper(
            arxiv_id="2304.12345",
            title="Test",
            summary="Test",
            abstract="Test",
            published="2026-04-11T10:30:00Z",
            updated="2026-04-11T10:30:00Z",
        )
        assert paper.version == "v1"

    def test_display_date(self):
        """Test date formatting."""
        paper = Paper(
            arxiv_id="2304.12345",
            title="Test",
            summary="Test",
            abstract="Test",
            published="2026-04-11T10:30:00Z",
            updated="2026-04-11T10:30:00Z",
        )
        assert paper.display_date == "2026-04-11"

    def test_paper_equality(self):
        """Test paper equality based on arXiv ID."""
        paper1 = Paper(
            arxiv_id="2304.12345v1",
            title="Test",
            summary="Test",
            abstract="Test",
            published="2026-04-11T10:30:00Z",
            updated="2026-04-11T10:30:00Z",
        )
        paper2 = Paper(
            arxiv_id="2304.12345v2",
            title="Different Title",
            summary="Different",
            abstract="Different",
            published="2026-04-12T10:30:00Z",
            updated="2026-04-12T10:30:00Z",
        )
        # Same base ID, different versions
        assert paper1 != paper2

    def test_paper_hash(self):
        """Test paper hashing for use in sets."""
        paper1 = Paper(
            arxiv_id="2304.12345v1",
            title="Test",
            summary="Test",
            abstract="Test",
            published="2026-04-11T10:30:00Z",
            updated="2026-04-11T10:30:00Z",
        )
        paper2 = Paper(
            arxiv_id="2304.12345v1",
            title="Different",
            summary="Different",
            abstract="Different",
            published="2026-04-11T10:30:00Z",
            updated="2026-04-11T10:30:00Z",
        )
        assert hash(paper1) == hash(paper2)


class TestArXivFetcher:
    """Test ArXivFetcher class."""

    def test_init(self):
        """Test fetcher initialization."""
        fetcher = ArXivFetcher(max_results=50, request_delay=2.0)
        assert fetcher.max_results == 50
        assert fetcher.request_delay == 2.0
        assert fetcher._last_request_time is None

    def test_build_query_basic(self):
        """Test basic query building."""
        fetcher = ArXivFetcher()
        query = fetcher._build_query("medical image segmentation")
        assert "all:" in query
        assert "medical" in query or "segmentation" in query

    def test_build_query_with_date_range(self):
        """Test query building with date range."""
        fetcher = ArXivFetcher()
        query = fetcher._build_query("test", date_range=("20260411", "20260412"))
        # Now uses spaces instead of + (requests will handle URL encoding)
        assert "submittedDate:[202604110000 TO 202604122359]" in query

    def test_build_query_with_categories(self):
        """Test query building with categories."""
        fetcher = ArXivFetcher()
        query = fetcher._build_query("test", categories=["cs.CV", "cs.LG"])
        assert "cat:cs.CV" in query
        assert "cat:cs.LG" in query

    @patch("src.fetchers.arxiv.requests.get")
    def test_fetch_success(self, mock_get, mock_paper_response):
        """Test successful fetch from arXiv API."""
        mock_response = Mock()
        mock_response.content = mock_paper_response.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        fetcher = ArXivFetcher()
        papers = fetcher.fetch("test", max_results=10)

        assert len(papers) == 3
        assert papers[0].arxiv_id == "2304.12345v1"
        assert papers[0].title == "Test Paper: Medical Image Segmentation with Deep Learning"
        assert papers[0].authors == ["John Doe", "Jane Smith"]
        assert "cs.CV" in papers[0].categories

    @patch("src.fetchers.arxiv.requests.get")
    def test_fetch_api_error(self, mock_get):
        """Test API error handling."""
        mock_get.side_effect = requests.RequestException("API Error")

        fetcher = ArXivFetcher()
        with pytest.raises(requests.RequestException):
            fetcher.fetch("test")

    @patch("src.fetchers.arxiv.time.time")
    @patch("src.fetchers.arxiv.requests.get")
    def test_rate_limiting(self, mock_get, mock_time, mock_paper_response):
        """Test rate limiting between requests."""
        mock_response = Mock()
        mock_response.content = mock_paper_response.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # First call at time 0
        mock_time.return_value = 0.0

        fetcher = ArXivFetcher(request_delay=3.0)

        # First request
        fetcher.fetch("test")

        # Second call at time 1 (should sleep for 2 seconds)
        mock_time.return_value = 1.0
        with patch("src.fetchers.arxiv.time.sleep") as mock_sleep:
            fetcher.fetch("test")
            mock_sleep.assert_called_once()

    @patch("src.fetchers.arxiv.requests.get")
    @patch("src.fetchers.arxiv.time.time")
    def test_fetch_last_24h(self, mock_time, mock_get, mock_paper_response):
        """Test fetching papers from last 24 hours."""
        mock_response = Mock()
        mock_response.content = mock_paper_response.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        mock_time.return_value = 0.0

        # Mock datetime for consistent date
        with patch("src.fetchers.arxiv.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value.strftime.side_effect = lambda fmt: "20260412" if "%Y%m%d" in fmt else "2026-04-12"
            mock_datetime.utcnow.return_value.__sub__.return_value.strftime.side_effect = lambda fmt: "20260411"

            fetcher = ArXivFetcher()
            papers = fetcher.fetch_last_24h("test")

            assert len(papers) == 3
            # Verify the API was called with date range
            assert mock_get.called
