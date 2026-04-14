"""Paper parser for processing and deduplicating papers."""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.fetchers.arxiv import Paper


@dataclass
class PaperGroup:
    """Represents a group of papers with different versions of the same work."""

    base_id: str  # arXiv ID without version (e.g., "2304.12345")
    title: str
    papers: List[Paper] = field(default_factory=list)
    source: str = "arxiv"

    @property
    def latest_paper(self) -> Optional[Paper]:
        """Get the latest version of the paper."""
        if not self.papers:
            return None

        # Sort by version number (extract numeric part)
        def version_key(paper: Paper) -> int:
            version_str = paper.version.replace("v", "")
            try:
                return int(version_str)
            except ValueError:
                return 0

        return max(self.papers, key=version_key)

    @property
    def latest_version(self) -> str:
        """Get the latest version string (e.g., 'v2')."""
        if self.latest_paper:
            return self.latest_paper.version
        return "v1"

    def add_paper(self, paper: Paper) -> None:
        """Add a paper to the group if not already present."""
        arxiv_ids = [p.arxiv_id for p in self.papers]
        if paper.arxiv_id not in arxiv_ids:
            self.papers.append(paper)


class PaperParser:
    """Parser for processing and deduplicating papers."""

    def __init__(self):
        """Initialize the paper parser."""
        self._paper_map: Dict[str, PaperGroup] = {}

    @staticmethod
    def get_base_id(arxiv_id: str) -> str:
        """Extract base ID from arXiv ID (remove version suffix).

        Args:
            arxiv_id: arXiv ID with or without version (e.g., "2304.12345v1" or "2304.12345")

        Returns:
            Base arXiv ID without version (e.g., "2304.12345")
        """
        # Remove version suffix if present
        if "v" in arxiv_id:
            # Find the last 'v' that's followed by a number (version indicator)
            parts = arxiv_id.split("v")
            # Only keep the parts before the version
            # Handle cases like "cs.CV/2304.12345v1"
            base_parts = []
            for part in parts[:-1]:
                base_parts.append(part)
                if part.endswith("."):
                    # This might be part of the ID, not a version separator
                    continue
            return "v".join(base_parts) if base_parts else arxiv_id
        return arxiv_id

    @staticmethod
    def deduplicate_papers(papers: List[Paper]) -> List[Paper]:
        """Remove duplicate papers based on arXiv ID.

        Args:
            papers: List of papers that may contain duplicates

        Returns:
            List of unique papers (keeps the first occurrence of each ID)
        """
        seen_ids = set()
        unique_papers = []

        for paper in papers:
            if paper.arxiv_id not in seen_ids:
                seen_ids.add(paper.arxiv_id)
                unique_papers.append(paper)

        return unique_papers

    @staticmethod
    def group_by_base_id(papers: List[Paper]) -> Dict[str, PaperGroup]:
        """Group papers by their base ID (different versions of same paper).

        Args:
            papers: List of papers

        Returns:
            Dictionary mapping base_id to PaperGroup
        """
        groups: Dict[str, PaperGroup] = {}

        for paper in papers:
            base_id = PaperParser.get_base_id(paper.arxiv_id)

            if base_id not in groups:
                groups[base_id] = PaperGroup(
                    base_id=base_id,
                    title=paper.title,
                    source=paper.source,
                )

            groups[base_id].add_paper(paper)

        return groups

    @staticmethod
    def merge_versions(papers: List[Paper]) -> List[Paper]:
        """Merge different versions of the same paper, keeping only the latest.

        Args:
            papers: List of papers that may include multiple versions

        Returns:
            List of papers with only the latest version of each work
        """
        groups = PaperParser.group_by_base_id(papers)
        latest_papers = []

        for group in groups.values():
            latest = group.latest_paper
            if latest:
                latest_papers.append(latest)

        return latest_papers

    @staticmethod
    def filter_by_date(
        papers: List[Paper],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Paper]:
        """Filter papers by published date range.

        Args:
            papers: List of papers to filter
            start_date: Start date in YYYY-MM-DD format (inclusive)
            end_date: End date in YYYY-MM-DD format (inclusive)

        Returns:
            Filtered list of papers
        """
        filtered = []

        for paper in papers:
            paper_date = paper.display_date

            if start_date and paper_date < start_date:
                continue
            if end_date and paper_date > end_date:
                continue

            filtered.append(paper)

        return filtered

    @staticmethod
    def filter_by_keywords(
        papers: List[Paper],
        include_keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,
    ) -> List[Paper]:
        """Filter papers by keywords in title or abstract.

        Args:
            papers: List of papers to filter
            include_keywords: Papers must contain at least one of these keywords
            exclude_keywords: Papers must not contain any of these keywords

        Returns:
            Filtered list of papers
        """
        filtered = []

        for paper in papers:
            # Combine title and abstract for keyword search
            text = (paper.title + " " + paper.abstract).lower()

            # Check include keywords
            if include_keywords:
                if not any(keyword.lower() in text for keyword in include_keywords):
                    continue

            # Check exclude keywords
            if exclude_keywords:
                if any(keyword.lower() in text for keyword in exclude_keywords):
                    continue

            filtered.append(paper)

        return filtered

    def parse_and_process(
        self,
        papers: List[Paper],
        merge_versions: bool = True,
        filter_keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,
    ) -> List[Paper]:
        """Process papers with deduplication and filtering.

        Args:
            papers: Raw list of papers from fetcher
            merge_versions: Whether to merge different versions of same paper
            filter_keywords: Optional keywords to include
            exclude_keywords: Optional keywords to exclude

        Returns:
            Processed and filtered list of papers
        """
        # Step 1: Remove exact duplicates by arXiv ID
        unique_papers = self.deduplicate_papers(papers)

        # Step 2: Merge different versions of same paper
        if merge_versions:
            unique_papers = self.merge_versions(unique_papers)

        # Step 3: Apply keyword filters
        if filter_keywords or exclude_keywords:
            unique_papers = self.filter_by_keywords(
                unique_papers,
                include_keywords=filter_keywords,
                exclude_keywords=exclude_keywords,
            )

        return unique_papers

    def format_for_llm(self, papers: List[Paper]) -> str:
        """Format papers as text for LLM input.

        Args:
            papers: List of papers to format

        Returns:
            Formatted string with paper information
        """
        formatted = []

        for i, paper in enumerate(papers, 1):
            paper_text = f"""
论文 {i}:
标题：{paper.title}
arXiv ID：{paper.arxiv_id}
版本：{paper.version}
发布日期：{paper.display_date}
摘要：{paper.abstract}
"""
            formatted.append(paper_text)

        return "\n".join(formatted)
