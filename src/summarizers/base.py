"""Base and concrete implementations for LLM summarizers."""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI
from anthropic import Anthropic

from config.prompts import DAILY_REPORT_PROMPT, STRUCTURED_SUMMARY_PROMPT

# Legacy prompt for backward compatibility
LEGACY_SUMMARY_PROMPT = """你是一个学术论文总结助手。请根据提供的论文内容，用中文总结核心创新点。

标题：{title}
摘要：{abstract}
{intro_section}

请输出两部分内容：

【摘要翻译】
将上述英文摘要完整翻译成中文，保持专业术语准确，语言流畅。

【创新点概述】
用多段文字概述论文的核心创新点，每段描述一个创新层面。

现在请处理上述论文：
"""
from .schemas import PaperSummary, SummaryResult


@dataclass
class LegacySummaryResult:
    """Legacy result of a paper summary (for backward compatibility)."""

    title: str
    content: str
    model_used: str
    tokens_used: Optional[int] = None


class BaseSummarizer(ABC):
    """Abstract base class for LLM summarizers."""

    def __init__(self, model: str, temperature: float = 0.3, max_tokens: int = 2000):
        """Initialize the summarizer.

        Args:
            model: Model name/identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    def summarize(self, paper_info: str) -> str:
        """Generate a summary for a single paper (legacy method).

        Args:
            paper_info: Formatted paper information string

        Returns:
            Summary text
        """
        pass

    @abstractmethod
    def summarize_structured(
        self,
        title: str,
        abstract: str,
        intro_text: Optional[str] = None,
    ) -> SummaryResult:
        """Generate a structured summary for a single paper.

        Args:
            title: Paper title
            abstract: Paper abstract
            intro_text: Optional introduction section text

        Returns:
            SummaryResult with structured PaperSummary
        """
        pass

    @abstractmethod
    def generate_report(self, papers_text: str) -> str:
        """Generate a daily report from multiple papers.

        Args:
            papers_text: Formatted text containing multiple papers

        Returns:
            Complete daily report in Markdown format
        """
        pass

    @abstractmethod
    def _call_llm(self, prompt: str, **kwargs) -> str:
        """Call the LLM API.

        Args:
            prompt: The prompt to send

        Returns:
            LLM response text
        """
        pass


class OpenAISummarizer(BaseSummarizer):
    """OpenAI-based summarizer using GPT models.

    也支持智谱AI等兼容 OpenAI API 的服务。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ):
        """Initialize OpenAI summarizer.

        Args:
            api_key: OpenAI API key (defaults to LLM_API_KEY or OPENAI_API_KEY env var)
            base_url: API base URL (defaults to LLM_BASE_URL env var, for ZhipuAI etc.)
            model: Model name (default: gpt-4o-mini)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response

        智谱AI示例:
            api_key="your-zhipu-api-key"
            base_url="https://open.bigmodel.cn/api/paas/v4"
            model="glm-4-flash"
        """
        super().__init__(model, temperature, max_tokens)
        # Try multiple sources for api_key
        self.api_key = (
            api_key or
            os.getenv("LLM_API_KEY") or
            os.getenv("OPENAI_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "OpenAI API key must be provided or set in LLM_API_KEY or OPENAI_API_KEY environment variable"
            )

        self.base_url = base_url or os.getenv("LLM_BASE_URL")

        # Initialize client with optional base_url
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = OpenAI(**client_kwargs)

    def summarize(self, paper_info: str) -> str:
        """Generate a summary for a single paper (legacy method).

        Args:
            paper_info: Formatted paper information (may include intro section)

        Returns:
            Summary text
        """
        # Extract title, abstract, and optionally intro section
        lines = paper_info.strip().split("\n")
        title = ""
        abstract = ""
        intro_section = ""

        # Find abstract and intro section
        abstract_start = -1
        intro_start = -1

        for i, line in enumerate(lines):
            if line.startswith("标题："):
                title = line.replace("标题：", "").strip()
            elif line.startswith("摘要："):
                abstract_start = i
            elif "Introduction 节选" in line:
                intro_start = i

        # Extract abstract (from "摘要：" to intro or end)
        if abstract_start >= 0:
            if intro_start > abstract_start:
                abstract = "\n".join(lines[abstract_start + 1:intro_start]).strip()
            else:
                abstract = "\n".join(lines[abstract_start + 1:]).strip()

        # Extract intro section if present
        if intro_start >= 0:
            intro_section = "\n".join(lines[intro_start + 1:]).strip()
            intro_section = f"Introduction 节选：\n{intro_section}"

        # Format prompt
        prompt = LEGACY_SUMMARY_PROMPT.format(
            title=title,
            abstract=abstract,
            intro_section=intro_section
        )
        return self._call_llm(prompt)

    def summarize_structured(
        self,
        title: str,
        abstract: str,
        intro_text: Optional[str] = None,
    ) -> SummaryResult:
        """Generate a structured summary for a single paper.

        Uses OpenAI's native Structured Outputs (response_format with json_schema).
        This guarantees valid JSON matching the Pydantic schema.

        Args:
            title: Paper title
            abstract: Paper abstract
            intro_text: Optional introduction section text

        Returns:
            SummaryResult with structured PaperSummary
        """
        # Format intro section
        intro_section = ""
        if intro_text:
            intro_section = f"\nIntroduction 节选：\n{intro_text[:3000]}"

        # Format prompt
        prompt = STRUCTURED_SUMMARY_PROMPT.format(
            title=title,
            abstract=abstract,
            intro_section=intro_section
        )

        try:
            # Convert Pydantic model to JSON schema for structured output
            # Pydantic v2: use model_json_schema()
            # Pydantic v1: use schema()
            try:
                json_schema = PaperSummary.model_json_schema()
            except AttributeError:
                # Fallback for Pydantic v1
                json_schema = PaperSummary.schema()

            # Use OpenAI Structured Outputs (requires gpt-4o-mini or gpt-4o-2024-08-06+)
            # Note: OpenAI uses a simplified JSON Schema format
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的学术论文总结助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "paper_summary",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "论文标题（保留英文原文）"
                                },
                                "title_zh": {
                                    "type": ["string", "null"],
                                    "description": "论文标题中文翻译（可选）"
                                },
                                "abstract_translation": {
                                    "type": "string",
                                    "description": "摘要的完整中文翻译"
                                },
                                "innovations": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "作者在 Introduction 中陈述的贡献点列表"
                                },
                                "experimental_validation": {
                                    "type": ["string", "null"],
                                    "description": "实验验证场景和核心结论（可选）"
                                }
                            },
                            "required": ["title", "abstract_translation", "innovations"],
                            "additionalProperties": False
                        }
                    }
                },
            )

            content = response.choices[0].message.content or ""
            tokens_used = response.usage.total_tokens if response.usage else None

            # Parse JSON response (guaranteed valid by Structured Outputs)
            data = json.loads(content)

            # Create PaperSummary
            summary = PaperSummary(
                title=data.get("title", title),
                title_zh=data.get("title_zh"),
                abstract_translation=data.get("abstract_translation", ""),
                innovations=data.get("innovations", []),
                experimental_validation=data.get("experimental_validation"),
            )

            return SummaryResult(
                success=True,
                summary=summary,
                model_used=self.model,
                tokens_used=tokens_used,
                has_introduction=bool(intro_text),
            )

        except json.JSONDecodeError as e:
            return SummaryResult(
                success=False,
                summary=None,
                error=f"JSON 解析失败: {e}",
                model_used=self.model,
                tokens_used=None,
                has_introduction=bool(intro_text),
            )
        except Exception as e:
            # Fallback to basic JSON mode if structured outputs not supported
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的学术论文总结助手。请严格按照 JSON 格式输出。"},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"},
                )

                content = response.choices[0].message.content or ""
                data = json.loads(content)

                summary = PaperSummary(
                    title=data.get("title", title),
                    title_zh=data.get("title_zh"),
                    abstract_translation=data.get("abstract_translation", ""),
                    innovations=data.get("innovations", []),
                    experimental_validation=data.get("experimental_validation"),
                )

                return SummaryResult(
                    success=True,
                    summary=summary,
                    model_used=self.model,
                    tokens_used=response.usage.total_tokens if response.usage else None,
                    has_introduction=bool(intro_text),
                )
            except Exception as fallback_error:
                return SummaryResult(
                    success=False,
                    summary=None,
                    error=f"API 调用失败: {e} (fallback: {fallback_error})",
                    model_used=self.model,
                    tokens_used=None,
                    has_introduction=bool(intro_text),
                )

    def generate_report(self, papers_text: str) -> str:
        """Generate a daily report from multiple papers.

        Args:
            papers_text: Formatted text containing multiple papers

        Returns:
            Complete daily report in Markdown format
        """
        prompt = DAILY_REPORT_PROMPT.format(papers=papers_text)
        return self._call_llm(prompt)

    def _call_llm(self, prompt: str, **kwargs) -> str:
        """Call OpenAI API.

        Args:
            prompt: The prompt to send

        Returns:
            LLM response text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"OpenAI API call failed: {e}") from e


class AnthropicSummarizer(BaseSummarizer):
    """Anthropic-based summarizer using Claude models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ):
        """Initialize Anthropic summarizer.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model name (default: claude-3-5-sonnet-20241022)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        super().__init__(model, temperature, max_tokens)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key must be provided or set in ANTHROPIC_API_KEY environment variable")

        self.client = Anthropic(api_key=self.api_key)

    def summarize(self, paper_info: str) -> str:
        """Generate a summary for a single paper (legacy method).

        Args:
            paper_info: Formatted paper information (may include intro section)

        Returns:
            Summary text
        """
        # Extract title, abstract, and optionally intro section
        lines = paper_info.strip().split("\n")
        title = ""
        abstract = ""
        intro_section = ""

        # Find abstract and intro section
        abstract_start = -1
        intro_start = -1

        for i, line in enumerate(lines):
            if line.startswith("标题："):
                title = line.replace("标题：", "").strip()
            elif line.startswith("摘要："):
                abstract_start = i
            elif "Introduction 节选" in line:
                intro_start = i

        # Extract abstract (from "摘要：" to intro or end)
        if abstract_start >= 0:
            if intro_start > abstract_start:
                abstract = "\n".join(lines[abstract_start + 1:intro_start]).strip()
            else:
                abstract = "\n".join(lines[abstract_start + 1:]).strip()

        # Extract intro section if present
        if intro_start >= 0:
            intro_section = "\n".join(lines[intro_start + 1:]).strip()
            intro_section = f"Introduction 节选：\n{intro_section}"

        # Format prompt
        prompt = LEGACY_SUMMARY_PROMPT.format(
            title=title,
            abstract=abstract,
            intro_section=intro_section
        )
        return self._call_llm(prompt)

    def summarize_structured(
        self,
        title: str,
        abstract: str,
        intro_text: Optional[str] = None,
    ) -> SummaryResult:
        """Generate a structured summary for a single paper.

        Uses Anthropic's native Tool Use for structured output.
        This guarantees valid JSON matching the Pydantic schema.

        Args:
            title: Paper title
            abstract: Paper abstract
            intro_text: Optional introduction section text

        Returns:
            SummaryResult with structured PaperSummary
        """
        # Format intro section
        intro_section = ""
        if intro_text:
            intro_section = f"\nIntroduction 节选：\n{intro_text[:3000]}"

        # Build user prompt
        user_prompt = f"""请分析以下学术论文并提取结构化信息。

标题：{title}
摘要：{abstract}
{intro_section}

请提供完整的中文翻译和创新的总结。"""

        # Get JSON schema from Pydantic model
        try:
            json_schema = PaperSummary.model_json_schema()
        except AttributeError:
            json_schema = PaperSummary.schema()

        try:
            # Use Anthropic Tool Use for structured output
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                tools=[
                    {
                        "name": "output_paper_summary",
                        "description": "输出论文的结构化摘要",
                        "input_schema": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "论文标题（保留英文原文）"
                                },
                                "title_zh": {
                                    "type": "string",
                                    "description": "论文标题中文翻译（可选）"
                                },
                                "abstract_translation": {
                                    "type": "string",
                                    "description": "摘要的完整中文翻译"
                                },
                                "innovations": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "作者在 Introduction 中陈述的贡献点列表",
                                    "minItems": 1
                                },
                                "experimental_validation": {
                                    "type": "string",
                                    "description": "实验验证场景和核心结论（可选）"
                                }
                            },
                            "required": ["title", "abstract_translation", "innovations"]
                        }
                    }
                ],
                tool_choice={"type": "tool", "name": "output_paper_summary"},
            )

            # Extract tool use result
            content_block = response.content[0]
            if content_block.type == "tool_use" and content_block.name == "output_paper_summary":
                data = content_block.input
            else:
                # Find tool_use block
                for block in response.content:
                    if block.type == "tool_use":
                        data = block.input
                        break
                else:
                    raise ValueError("No tool_use block found in response")

            tokens_used = response.usage.input_tokens + response.usage.output_tokens if response.usage else None

            # Create PaperSummary
            summary = PaperSummary(
                title=data.get("title", title),
                title_zh=data.get("title_zh"),
                abstract_translation=data.get("abstract_translation", ""),
                innovations=data.get("innovations", []),
                experimental_validation=data.get("experimental_validation"),
            )

            return SummaryResult(
                success=True,
                summary=summary,
                model_used=self.model,
                tokens_used=tokens_used,
                has_introduction=bool(intro_text),
            )

        except Exception as e:
            return SummaryResult(
                success=False,
                summary=None,
                error=f"API 调用失败: {e}",
                model_used=self.model,
                tokens_used=None,
                has_introduction=bool(intro_text),
            )

    def generate_report(self, papers_text: str) -> str:
        """Generate a daily report from multiple papers.

        Args:
            papers_text: Formatted text containing multiple papers

        Returns:
            Complete daily report in Markdown format
        """
        prompt = DAILY_REPORT_PROMPT.format(papers=papers_text)
        return self._call_llm(prompt)

    def _call_llm(self, prompt: str, **kwargs) -> str:
        """Call Anthropic API.

        Args:
            prompt: The prompt to send

        Returns:
            LLM response text
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )
            return response.content[0].text or ""
        except Exception as e:
            raise RuntimeError(f"Anthropic API call failed: {e}") from e


def create_summarizer(
    provider: str = "openai",
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 2000,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> BaseSummarizer:
    """Factory function to create a summarizer.

    Args:
        provider: Either 'openai', 'anthropic', or any OpenAI-compatible provider (e.g., 'bigmodel', 'zhipu')
        model: Optional model override
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        api_key: Optional API key override
        base_url: Optional base URL override (for ZhipuAI etc.)

    Returns:
        Configured summarizer instance

    Raises:
        ValueError: If provider is not supported

    支持的提供商:
        - openai: OpenAI (GPT-4, etc.)
        - anthropic: Anthropic (Claude)
        - bigmodel/zhipu: 智谱AI (GLM-4, etc.) - 使用 OpenAI 兼容接口

    智谱AI示例:
        create_summarizer(
            provider="bigmodel",
            api_key="your-zhipu-api-key",
            base_url="https://open.bigmodel.cn/api/paas/v4",
            model="glm-4-flash"
        )
    """
    # Support for OpenAI-compatible providers (智谱AI, etc.)
    if provider in ("openai", "bigmodel", "zhipu", "deepseek"):
        return OpenAISummarizer(
            api_key=api_key,
            base_url=base_url,
            model=model or "gpt-4o-mini",
            temperature=temperature,
            max_tokens=max_tokens,
        )
    elif provider == "anthropic":
        return AnthropicSummarizer(
            api_key=api_key,
            model=model or "claude-3-5-sonnet-20241022",
            temperature=temperature,
            max_tokens=max_tokens,
        )
    else:
        raise ValueError(
            f"Unsupported provider: {provider}. "
            f"Supported providers: 'openai', 'anthropic', 'bigmodel', 'zhipu', 'deepseek'"
        )
