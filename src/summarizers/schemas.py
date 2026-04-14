"""Pydantic schemas for structured paper summary output."""

from typing import Optional, List
from pydantic import BaseModel, Field


class PaperSummary(BaseModel):
    """Structured paper summary output.

    This schema ensures consistent LLM output for paper summaries.
    """

    # 基础信息
    title: str = Field(description="论文标题（保留英文原文）")
    title_zh: Optional[str] = Field(default=None, description="论文标题中文翻译（可选）")

    # 摘要翻译
    abstract_translation: str = Field(description="摘要的完整中文翻译")

    # 创新点总结（直接提取作者陈述的贡献点）
    innovations: List[str] = Field(
        description="作者在 Introduction 中陈述的贡献点列表，保留英文术语",
        min_length=1,
    )

    # 实验验证
    experimental_validation: Optional[str] = Field(
        default=None,
        description="实验验证场景和核心结论（从 Introduction 中提取）"
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "title": "Attention Is All You Need",
                "title_zh": "注意力机制就是你所需的全部",
                "abstract_translation": "本文提出了一种新的简单网络架构 Transformer...",
                "innovations": [
                    "提出 Transformer 架构，完全基于注意力机制，摒弃了循环和卷积",
                    "引入自注意力机制（Self-Attention），有效处理长距离依赖",
                    "采用多头注意力（Multi-Head Attention），捕捉不同子空间的表示",
                ],
                "experimental_validation": "在机器翻译任务上，Transformer 达到了新的 SOTA 结果，训练效率显著提升"
            }
        }


class SummaryResult(BaseModel):
    """Result of a paper summary operation."""

    success: bool
    summary: Optional[PaperSummary] = None
    error: Optional[str] = None
    model_used: str
    tokens_used: Optional[int] = None
    has_introduction: bool = Field(
        description="是否成功获取并使用了 Introduction 章节"
    )
