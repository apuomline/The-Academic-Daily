"""Tests for paper parser module."""

import pytest
from datetime import datetime

from src.parsers.paper import PaperParser, PaperGroup
from src.fetchers.arxiv import Paper


class TestPaperParser:
    """Test PaperParser class."""

    def test_get_base_id_with_version(self):
        """Test extracting base ID from arXiv ID with version."""
        base_id = PaperParser.get_base_id("2304.12345v2")
        assert base_id == "2304.12345"

    def test_get_base_id_without_version(self):
        """Test extracting base ID from arXiv ID without version."""
        base_id = PaperParser.get_base_id("2304.12345")
        assert base_id == "2304.12345"

    def test_deduplicate_papers(self, sample_papers):
        """Test removing duplicate papers by arXiv ID."""
        # Add duplicate
        papers = sample_papers + [sample_papers[0]]
        assert len(papers) == 4

        unique = PaperParser.deduplicate_papers(papers)
        assert len(unique) == 3

    def test_group_by_base_id(self, sample_papers):
        """Test grouping papers by base ID."""
        groups = PaperParser.group_by_base_id(sample_papers)

        assert len(groups) == 2
        assert "2304.12345" in groups
        assert "2304.12346" in groups

        # Check that versions are grouped
        group_12345 = groups["2304.12345"]
        assert len(group_12345.papers) == 2
        assert group_12345.latest_version == "v2"

    def test_merge_versions(self, sample_papers):
        """Test merging different versions of same paper."""
        merged = PaperParser.merge_versions(sample_papers)

        # Should have 2 papers (2304.12345 merged to v2, 2304.12346 stays)
        assert len(merged) == 2

        # Check that v2 is kept for 2304.12345
        merged_ids = [p.arxiv_id for p in merged]
        assert "2304.12345v2" in merged_ids
        assert "2304.12345v1" not in merged_ids

    def test_filter_by_date(self, sample_papers):
        """Test filtering papers by date range."""
        filtered = PaperParser.filter_by_date(
            sample_papers,
            start_date="2026-04-12",
            end_date="2026-04-12",
        )

        # Only papers from 2026-04-12 (only 2304.12346v1)
        assert len(filtered) == 1
        assert filtered[0].arxiv_id == "2304.12346v1"

    def test_filter_by_keywords_include(self, sample_papers):
        """Test filtering papers by include keywords."""
        filtered = PaperParser.filter_by_keywords(
            sample_papers,
            include_keywords=["Test"],
        )

        # All papers have "Test" in title
        assert len(filtered) == 3

    def test_filter_by_keywords_exclude(self, sample_papers):
        """Test filtering papers by exclude keywords."""
        filtered = PaperParser.filter_by_keywords(
            sample_papers,
            exclude_keywords=["2"],
        )

        # Should exclude papers with "2" in title (Test Paper 2)
        # Leaves 2304.12345v1 and v2 (both "Test Paper 1")
        assert len(filtered) == 2
        assert all(p.arxiv_id.startswith("2304.12345") for p in filtered)

    def test_parse_and_process(self, sample_papers):
        """Test full processing pipeline."""
        parser = PaperParser()
        processed = parser.parse_and_process(
            sample_papers,
            merge_versions=True,
            filter_keywords=["Test"],
        )

        # Should have 2 papers after merging versions
        assert len(processed) == 2

    def test_format_for_llm(self, sample_papers):
        """Test formatting papers for LLM input."""
        parser = PaperParser()
        formatted = parser.format_for_llm(sample_papers[:2])

        assert "标题" in formatted
        assert "摘要" in formatted
        assert "Test Paper 1" in formatted
        assert "Test Paper 2" in formatted


class TestPaperGroup:
    """Test PaperGroup class."""

    def test_latest_paper(self):
        """Test getting latest paper from group."""
        from src.fetchers.arxiv import Paper

        group = PaperGroup(base_id="2304.12345", title="Test", source="arxiv")

        paper_v1 = Paper(
            arxiv_id="2304.12345v1",
            title="Test",
            summary="v1",
            abstract="v1",
            published="2026-04-11T10:30:00Z",
            updated="2026-04-11T10:30:00Z",
        )

        paper_v2 = Paper(
            arxiv_id="2304.12345v2",
            title="Test",
            summary="v2",
            abstract="v2",
            published="2026-04-11T10:30:00Z",
            updated="2026-04-12T10:30:00Z",
        )

        group.add_paper(paper_v1)
        group.add_paper(paper_v2)

        assert group.latest_paper.arxiv_id == "2304.12345v2"
        assert group.latest_version == "v2"

    def test_add_paper_no_duplicate(self):
        """Test adding paper without duplicates."""
        from src.fetchers.arxiv import Paper

        group = PaperGroup(base_id="2304.12345", title="Test", source="arxiv")

        paper = Paper(
            arxiv_id="2304.12345v1",
            title="Test",
            summary="Test",
            abstract="Test",
            published="2026-04-11T10:30:00Z",
            updated="2026-04-11T10:30:00Z",
        )

        group.add_paper(paper)
        group.add_paper(paper)  # Add same paper again

        assert len(group.papers) == 1
