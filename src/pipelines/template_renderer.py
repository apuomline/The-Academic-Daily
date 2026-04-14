"""Template rendering module using Jinja2."""

from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.fetchers.arxiv import Paper


class TemplateRenderer:
    """Render reports using Jinja2 templates."""

    def __init__(self, template_dir: str = "templates"):
        """Initialize template renderer.

        Args:
            template_dir: Directory containing template files
        """
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
        )

        # Add custom filters
        self.env.filters['format_date'] = self._format_date

    @staticmethod
    def _format_date(value: datetime, fmt: str = "%Y-%m-%d") -> str:
        """Format datetime object.

        Args:
            value: Datetime object
            fmt: Format string

        Returns:
            Formatted date string
        """
        if isinstance(value, datetime):
            return value.strftime(fmt)
        return str(value)

    def render_markdown(
        self,
        papers: List[Paper],
        keywords: List[str],
        report_date: str,
        generation_time: str,
        template_name: str = "daily_report.md",
    ) -> str:
        """Render Markdown report.

        Args:
            papers: List of papers
            keywords: Search keywords
            report_date: Report date string
            generation_time: Generation time string
            template_name: Template file name

        Returns:
            Rendered Markdown content
        """
        # Group papers by source
        papers_by_source = self._group_by_source(papers)

        # Count papers by source
        source_counts = {source: len(ps) for source, ps in papers_by_source.items()}

        # Get all sources
        sources = list(papers_by_source.keys())

        template = self.env.get_template(template_name)
        return template.render(
            papers_by_source=papers_by_source,
            source_counts=source_counts,
            total_papers=len(papers),
            sources=sources,
            keywords=keywords,
            report_date=report_date,
            generation_time=generation_time,
        )

    def render_html_email(
        self,
        papers: List[Paper],
        keywords: List[str],
        report_date: str,
        generation_time: str,
        template_name: str = "email.html",
    ) -> str:
        """Render HTML email content.

        Args:
            papers: List of papers
            keywords: Search keywords
            report_date: Report date string
            generation_time: Generation time string
            template_name: Template file name

        Returns:
            Rendered HTML content
        """
        # Group papers by source
        papers_by_source = self._group_by_source(papers)

        # Count papers by source
        source_counts = {source: len(ps) for source, ps in papers_by_source.items()}

        # Get all sources
        sources = list(papers_by_source.keys())

        template = self.env.get_template(template_name)
        return template.render(
            papers_by_source=papers_by_source,
            source_counts=source_counts,
            total_papers=len(papers),
            sources=sources,
            keywords=keywords,
            report_date=report_date,
            generation_time=generation_time,
        )

    @staticmethod
    def _group_by_source(papers: List[Paper]) -> Dict[str, List[Paper]]:
        """Group papers by their source.

        Args:
            papers: List of papers

        Returns:
            Dictionary mapping source to list of papers
        """
        grouped = {}
        for paper in papers:
            source = paper.source
            if source not in grouped:
                grouped[source] = []
            grouped[source].append(paper)

        # Rename sources for display and use lowercase keys
        source_display_names = {
            "arxiv": "arxiv",
            "openalex": "openalex",
            "semantic_scholar": "semantic_scholar",
        }

        return {source_display_names.get(k, k).lower(): v for k, v in grouped.items()}

    def render_summary_text(
        self,
        papers: List[Paper],
        keywords: List[str],
    ) -> str:
        """Render simple text summary (for quick preview).

        Args:
            papers: List of papers
            keywords: Search keywords

        Returns:
            Summary text
        """
        lines = [
            f"学术日报摘要 - {datetime.now().strftime('%Y年%m月%d日')}",
            f"搜索关键词: {', '.join(keywords)}",
            f"共 {len(papers)} 篇论文",
            "",
        ]

        for i, paper in enumerate(papers[:10], 1):  # Limit to 10 papers
            lines.append(f"{i}. {paper.title}")
            lines.append(f"   来源: {paper.source} | 日期: {paper.display_date}")

        if len(papers) > 10:
            lines.append(f"\n... 还有 {len(papers) - 10} 篇论文")

        return "\n".join(lines)
