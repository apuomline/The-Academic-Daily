"""Test fixtures and configuration."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def mock_paper_response():
    """Mock arXiv API response XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2304.12345v1</id>
    <updated>2026-04-11T10:30:00Z</updated>
    <published>2026-04-11T10:30:00Z</published>
    <title>Test Paper: Medical Image Segmentation with Deep Learning</title>
    <summary>This paper presents a novel approach to medical image segmentation using deep learning techniques. We propose a new architecture called TestNet that achieves state-of-the-art results on multiple benchmarks.</summary>
    <author>
      <name>John Doe</name>
    </author>
    <author>
      <name>Jane Smith</name>
    </author>
    <arxiv:primary_category term="cs.CV" />
    <category term="cs.CV" />
    <category term="cs.LG" />
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2304.12346v1</id>
    <updated>2026-04-12T14:20:00Z</updated>
    <published>2026-04-12T14:20:00Z</published>
    <title>Another Test Paper: Few-Shot Learning for Medical Imaging</title>
    <summary>We introduce a few-shot learning framework for medical image analysis that reduces the need for large annotated datasets.</summary>
    <author>
      <name>Alice Johnson</name>
    </author>
    <arxiv:primary_category term="cs.CV" />
    <category term="cs.CV" />
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2304.12345v2</id>
    <updated>2026-04-12T09:00:00Z</updated>
    <published>2026-04-11T10:30:00Z</published>
    <title>Test Paper: Medical Image Segmentation with Deep Learning</title>
    <summary>This paper presents a novel approach to medical image segmentation using deep learning techniques. We propose a new architecture called TestNet that achieves state-of-the-art results on multiple benchmarks. This version includes additional experiments.</summary>
    <author>
      <name>John Doe</name>
    </author>
    <author>
      <name>Jane Smith</name>
    </author>
    <arxiv:primary_category term="cs.CV" />
    <category term="cs.CV" />
  </entry>
</feed>"""


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = """## Test Paper: Medical Image Segmentation with Deep Learning

**日期与版本**：2026-04-11 v2
**创新点概述**：
- 提出 TestNet 架构，采用新颖的特征融合机制
- 在多个医学影像基准数据集上取得 SOTA 结果
- 引入新的损失函数，改善分割边界精度

**学术检索源**：arXiv

## Another Test Paper: Few-Shot Learning for Medical Imaging

**日期与版本**：2026-04-12 v1
**创新点概述**：
- 提出少样本学习框架，减少标注数据需求
- 采用元学习策略，提升模型泛化能力
- 在跨域医学影像任务上验证有效性

**学术检索源**：arXiv
"""
    return mock_response


@pytest.fixture
def sample_papers():
    """Sample Paper objects for testing."""
    from src.fetchers.arxiv import Paper

    return [
        Paper(
            arxiv_id="2304.12345v1",
            title="Test Paper 1",
            summary="Abstract 1",
            abstract="Abstract 1",
            published="2026-04-11T10:30:00Z",
            updated="2026-04-11T10:30:00Z",
            authors=["Author 1"],
            categories=["cs.CV"],
            source="arxiv",
        ),
        Paper(
            arxiv_id="2304.12346v1",
            title="Test Paper 2",
            summary="Abstract 2",
            abstract="Abstract 2",
            published="2026-04-12T14:20:00Z",
            updated="2026-04-12T14:20:00Z",
            authors=["Author 2"],
            categories=["cs.CV"],
            source="arxiv",
        ),
        Paper(
            arxiv_id="2304.12345v2",
            title="Test Paper 1",
            summary="Abstract 1 updated",
            abstract="Abstract 1 updated",
            published="2026-04-11T10:30:00Z",
            updated="2026-04-12T09:00:00Z",
            authors=["Author 1"],
            categories=["cs.CV"],
            source="arxiv",
        ),
    ]
