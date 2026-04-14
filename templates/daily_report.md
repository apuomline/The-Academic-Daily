# 学术日报 - {{ report_date }}

> 本日报由 Academic Paper Pusher 自动生成
> 搜索关键词: {{ keywords|join(', ') }}
> 生成时间: {{ generation_time }}
> 数据源: {{ sources|join(', ') }}

---

{% if papers_by_source.arxiv %}
## 📄 arXiv 预印本

{% for paper in papers_by_source.arxiv %}
### {{ paper.title }}

**日期与版本**：{{ paper.display_date }} {{ paper.version }}
**来源**：{{ paper.source }}

{% if paper.summary_structured %}
#### 📝 摘要翻译
{{ paper.summary_structured.abstract_translation }}

#### 💡 核心创新
{% for innovation in paper.summary_structured.innovations %}
{{ loop.index }}. {{ innovation }}
{% endfor %}

{% if paper.summary_structured.experimental_validation %}
#### 🧪 实验验证
{{ paper.summary_structured.experimental_validation }}
{% endif %}

{% else %}
#### 📄 摘要
{{ paper.abstract }}
{% endif %}

**链接**：{% if paper.pdf_url %}[PDF]({{ paper.pdf_url }}) | {% endif %}[arXiv](https://arxiv.org/abs/{{ paper.arxiv_id }})

---

{% endfor %}
{% endif %}

{% if papers_by_source.openalex %}
## 🔍 OpenAlex

{% for paper in papers_by_source.openalex %}
### {{ paper.title }}

**日期**：{{ paper.display_date }}
**作者**：{{ paper.authors|join(', ') }}
**主题**：{{ paper.categories|join(', ') }}
{% if paper.doi %}**DOI**：{{ paper.doi }}{% endif %}

{% if paper.summary %}
#### 摘要
{{ paper.summary }}
{% endif %}

**链接**：{% if paper.pdf_url %}[PDF]({{ paper.pdf_url }}) | {% endif %}{% if paper.doi %}[DOI](https://doi.org/{{ paper.doi }}){% endif %}

---

{% endfor %}
{% endif %}

{% if papers_by_source.semantic_scholar %}
## 📚 Semantic Scholar

{% for paper in papers_by_source.semantic_scholar %}
### {{ paper.title }}

**日期**：{{ paper.display_date }}
**作者**：{{ paper.authors|join(', ') }}
{% if paper.doi %}**DOI**：{{ paper.doi }}{% endif %}

{% if paper.summary %}
#### 摘要
{{ paper.summary }}
{% endif %}

**链接**：{% if paper.pdf_url %}[PDF]({{ paper.pdf_url }}) | {% endif %}{% if paper.doi %}[DOI](https://doi.org/{{ paper.doi }}){% endif %}

---

{% endfor %}
{% endif %}

## 📊 统计信息

| 数据源 | 论文数量 |
|--------|----------|
{% for source, count in source_counts.items() %}
| {{ source }} | {{ count }} |
{% endfor %}
| **总计** | **{{ total_papers }}** |

---

*本日报由 [Academic Paper Pusher](https://github.com/your-repo) 自动生成*
