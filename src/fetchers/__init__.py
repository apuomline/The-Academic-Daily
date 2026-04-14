"""Fetchers module for data source adapters."""

from .arxiv import ArXivFetcher, Paper
from .openalex import OpenAlexFetcher, SemanticScholarFetcher

__all__ = [
    "ArXivFetcher",
    "OpenAlexFetcher",
    "SemanticScholarFetcher",
    "Paper",
]
