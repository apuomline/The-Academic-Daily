"""Integration tests for the full pipeline."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_paper_response():
    """Mock arXiv API response."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2304.12345v1</id>
    <updated>2026-04-11T10:30:00Z</updated>
    <published>2026-04-11T10:30:00Z</published>
    <title>Novel Method for Medical Image Segmentation</title>
    <summary>We present a novel deep learning approach for medical image segmentation that achieves state-of-the-art results on multiple benchmarks.</summary>
    <author><name>Test Author</name></author>
    <arxiv:primary_category term="cs.CV" />
    <category term="cs.CV" />
  </entry>
</feed>"""


class TestIntegration:
    """Integration tests for the complete pipeline."""

    @patch("src.summarizers.base.OpenAI")
    @patch("src.fetchers.arxiv.requests.get")
    def test_full_pipeline(
        self,
        mock_get,
        mock_openai,
        mock_paper_response,
    ):
        """Test the complete pipeline from fetch to report."""
        # Setup mocks
        mock_response = Mock()
        mock_response.content = mock_paper_response.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        mock_llm_response = Mock()
        mock_llm_response.choices = [Mock()]
        mock_llm_response.choices[0].message.content = """# 学术日报

## Novel Method for Medical Image Segmentation

**日期与版本**：2026-04-11 v1
**创新点概述**：
- 提出新颖的深度学习方法
- 在多个基准数据集上取得 SOTA 结果

**学术检索源**：arXiv
"""
        mock_instance = Mock()
        mock_instance.chat.completions.create.return_value = mock_llm_response
        mock_openai.return_value = mock_instance

        # Import and run pipeline components
        from src.fetchers import ArXivFetcher
        from src.parsers import PaperParser
        from src.summarizers import create_summarizer

        # Step 1: Fetch
        fetcher = ArXivFetcher()
        papers = fetcher.fetch("medical image segmentation")

        assert len(papers) > 0
        assert papers[0].title == "Novel Method for Medical Image Segmentation"

        # Step 2: Parse
        parser = PaperParser()
        processed = parser.parse_and_process(papers, merge_versions=True)

        assert len(processed) > 0

        # Step 3: Format
        papers_text = parser.format_for_llm(processed)

        assert "Novel Method" in papers_text

        # Step 4: Summarize
        summarizer = create_summarizer(provider="openai", api_key="test-key")
        report = summarizer.generate_report(papers_text)

        assert "Novel Method" in report
        assert "创新点概述" in report

    @patch("src.fetchers.arxiv.requests.get")
    def test_pipeline_with_versions(self, mock_get):
        """Test pipeline correctly handles multiple versions."""
        response_with_versions = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2304.11111v1</id>
    <updated>2026-04-11T10:00:00Z</updated>
    <published>2026-04-11T10:00:00Z</published>
    <title>Test Paper</title>
    <summary>Version 1</summary>
    <author><name>Author</name></author>
    <arxiv:primary_category term="cs.CV" />
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2304.11111v2</id>
    <updated>2026-04-12T10:00:00Z</updated>
    <published>2026-04-11T10:00:00Z</published>
    <title>Test Paper</title>
    <summary>Version 2 - Updated</summary>
    <author><name>Author</name></author>
    <arxiv:primary_category term="cs.CV" />
  </entry>
</feed>"""

        mock_response = Mock()
        mock_response.content = response_with_versions.encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        from src.fetchers import ArXivFetcher
        from src.parsers import PaperParser

        fetcher = ArXivFetcher()
        papers = fetcher.fetch("test")

        parser = PaperParser()
        processed = parser.parse_and_process(papers, merge_versions=True)

        # Should have only 1 paper after merging versions
        assert len(processed) == 1
        # Should be v2
        assert processed[0].version == "v2"

    @patch("src.fetchers.arxiv.requests.get")
    def test_pipeline_with_date_filtering(self, mock_get):
        """Test pipeline with date filtering."""
        mock_response = Mock()
        mock_response.content = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2304.11111v1</id>
    <updated>2026-04-10T10:00:00Z</updated>
    <published>2026-04-10T10:00:00Z</published>
    <title>Old Paper</title>
    <summary>Old</summary>
    <author><name>Author</name></author>
    <arxiv:primary_category term="cs.CV" />
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2304.22222v1</id>
    <updated>2026-04-12T10:00:00Z</updated>
    <published>2026-04-12T10:00:00Z</published>
    <title>New Paper</title>
    <summary>New</summary>
    <author><name>Author</name></author>
    <arxiv:primary_category term="cs.CV" />
  </entry>
</feed>""".encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        from src.fetchers import ArXivFetcher
        from src.parsers import PaperParser

        fetcher = ArXivFetcher()
        papers = fetcher.fetch("test")

        parser = PaperParser()
        # Filter to only 2026-04-12
        filtered = parser.filter_by_date(
            papers,
            start_date="2026-04-12",
            end_date="2026-04-12",
        )

        assert len(filtered) == 1
        assert filtered[0].title == "New Paper"
