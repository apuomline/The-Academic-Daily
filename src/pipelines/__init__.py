"""Pipelines module for automated processing."""

from .scheduler import PaperPipelineScheduler, create_scheduler
from .template_renderer import TemplateRenderer
from .daily import DailyReportPipeline

__all__ = [
    "PaperPipelineScheduler",
    "create_scheduler",
    "TemplateRenderer",
    "DailyReportPipeline",
]
