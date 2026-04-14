以下是经过细节修正和补充后的 CLAUDE.md 修订版模板。我保持了原有的结构和风格，仅针对之前提到的 7 个关键点进行了精准替换与增补（修改处无需特别标注，已直接融入文档）：
学术论文自动推送助手
项目代号：AcademicPaperPusher
创建日期：2026-04-12
当前阶段：规划期
项目概述
构建一个自动化系统，从多个学术源（arXiv、OpenReview、OpenAlex等）抓取最新论文，通过LLM进行智能总结，按用户订阅主题推送到指定渠道（邮件、企微、钉钉等）。
核心功能
多源数据抓取：支持 arXiv、OpenReview、OpenAlex、Semantic Scholar
智能总结：使用 LLM 提取论文创新点、方法细节、实验结果
版本追踪：识别论文的 v1/v2/v3 更新，合并同一条目
个性化订阅：用户可自定义关注主题、排除关键词
多渠道推送：支持邮件、企微、钉钉、Telegram 等
语义检索：基于向量数据库的语义匹配，突破关键词限制
五阶段开发路线图
第一阶段：单点突破（MVP 验证期）⏳ 当前阶段
周期：1-2 周
目标：实现"输入主题 → 输出 Markdown 日报"的最小闭环
技术栈
数据源：arXiv API (Atom XML)
HTTP 客户端：requests
XML 解析：xml.etree.ElementTree
LLM 接入：OpenAI SDK / Anthropic SDK / 百度千帆
输出：Markdown 文件
核心任务
1. 数据源接入
# arXiv API 查询示例（注意时区与时间余量）
# arXiv 使用 GMT 时区，格式为 [YYYYMMDDTTTT+TO+YYYYMMDDTTTT]
# 结束时间建议写到次日 0000，避免漏掉当日晚间提交的论文
# URL: http://export.arxiv.org/api/query?
# 参数：search_query=medical+image+segmentation
#      AND+submittedDate:[202604110000+TO+202604130000]
#      &sortBy=submittedDate&sortOrder=descending
2. 基础解析
提取字段：<title>, <summary>, <published>, <updated>, <id>
唯一标识：arXiv ID（如 2304.12345v1）
去重策略：使用 Set 或 Dict 按 ID 去重
3. LLM 总结
系统 Prompt 模板：
你是一个学术论文总结助手。请基于提供的论文标题和摘要，
生成一份结构化的日报，格式如下：
## 论文标题
**日期与版本**：YYYY-MM-DD vN
**创新点概述**：
- 创新点1
- 创新点2
- ...
**学术检索源**：arXiv / OpenReview
要求：
1. 提取具体的方法名/模块名（如 SQI、VTCT、C2Seg）
2. 用简洁语言概括核心贡献
3. 保持客观，不夸大
4. 输出
控制台打印或保存为 .md 文件
交付物
[ ] arxiv_fetcher.py - arXiv API 客户端
[ ] paper_parser.py - 论文解析与去重
[ ] llm_summarizer.py - LLM 总结模块
[ ] main.py - 主入口脚本
[ ] config.py - 配置文件（API keys 等）
第二阶段：基建搭设（自动化流水线期）
周期：2-3 周
目标：数据持久化、多源汇聚、定时任务、幂等与容错
技术栈
数据库：PostgreSQL + SQLAlchemy (ORM)
定时调度：APScheduler
模板引擎：Jinja2
新数据源：OpenAlex API, Semantic Scholar API
数据库设计
-- 论文表
CREATE TABLE papers (
    id SERIAL PRIMARY KEY,
    arxiv_id VARCHAR(50) UNIQUE,
    doi VARCHAR(100) UNIQUE,       -- 用于跨源去重
    title TEXT NOT NULL,
    abstract TEXT,
    source VARCHAR(50),  -- 'arxiv', 'openreview', 'openalex'
    published_date TIMESTAMP,
    updated_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 论文版本表
CREATE TABLE paper_versions (
    id SERIAL PRIMARY KEY,
    paper_id INTEGER REFERENCES papers(id),
    version VARCHAR(10),  -- 'v1', 'v2', etc.
    content TEXT,         -- LLM 总结内容
    model_name VARCHAR(50), -- 产生此总结的模型名（如 gpt-4o）
    prompt_id VARCHAR(50),  -- 使用的 prompt 版本标识
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 用户订阅表
-- 注意：若涉及多时区部署，建议应用层统一转为 UTC 存储，前端按用户时区展示
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255),
    keywords TEXT[],          -- PostgreSQL array
    exclude_keywords TEXT[],
    push_time TIME,           -- 用户本地推送时间
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 推送日志表（用于排查与防重）
CREATE TABLE push_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    channel VARCHAR(50),      -- 'email', 'wework', 'telegram'
    report_date DATE,         -- 推送的日报日期
    status VARCHAR(20),       -- 'success', 'failed'
    error_msg TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, channel, report_date) -- 幂等键：防止重复推送
);
核心任务
1. 多源数据源适配器
class SourceAdapter(ABC):
    @abstractmethod
    def fetch(self, query: str, date_range: tuple) -> List[Paper]:
        pass
class ArXivAdapter(SourceAdapter):
    # 需内置请求间隔（如 3 秒），遵守 arXiv 使用规范
    ...
class OpenAlexAdapter(SourceAdapter):
    # 使用 from_created_date / to_created_date 过滤
    ...
class SemanticScholarAdapter(SourceAdapter):
    ...
2. 跨源去重与幂等控制
使用 DOI 和 arXiv ID 进行联合去重。
每日流水线需结合 push_logs 表与时间窗口，确保任务失败重跑时不会导致数据库重复写入或用户收到重复邮件。
3. 定时调度与日志
import structlog
logger = structlog.get_logger()
from apscheduler.schedulers.blocking import BlockingScheduler
def daily_pipeline():
    logger.info("pipeline.start", date=datetime.now())
    try:
        # ... 流水线逻辑
        logger.info("pipeline.finish", papers_fetched=len(papers))
    except Exception as e:
        logger.error("pipeline.failed", error=str(e))
scheduler = BlockingScheduler()
scheduler.add_job(daily_pipeline, 'cron', hour=2, minute=0)
scheduler.start()
4. Jinja2 模板渲染
# 日报模板
# 学术日报 - {{ date }}
## 一、arXiv 预印本
{% for paper in arxiv_papers %}
{{ paper.summary }}
{% endfor %}
## 二、OpenReview 会议/期刊
{% for paper in openreview_papers %}
{{ paper.summary }}
{% endfor %}
交付物
[ ] PostgreSQL 数据库 schema
[ ] database.py - SQLAlchemy 模型定义
[ ] fetchers/ - 多源适配器目录（含速率限制逻辑）
[ ] scheduler.py - 定时任务与 structlog 日志配置
[ ] templates/ - Jinja2 模板目录
第三阶段：产品化（用户系统与多渠道推送期）
周期：3-4 周
目标：从"自用脚本"变为"可订阅的 SaaS"
技术栈
Web 框架：FastAPI
认证：JWT + OAuth2
邮件：Resend / SendGrid
即时通讯：企微/钉钉 Webhook, Telegram Bot API
API 设计
# FastAPI 路由示例
app = FastAPI()
# 用户管理
@app.post("/api/auth/register")
@app.post("/api/auth/login")
@app.get("/api/users/me")
# 订阅管理
@app.post("/api/subscriptions")
@app.get("/api/subscriptions")
@app.put("/api/subscriptions/{id}")
# 日报
@app.get("/api/daily-reports")
@app.get("/api/daily-reports/{date}")
多渠道推送
class PushChannel(ABC):
    @abstractmethod
    def send(self, user: User, content: str):
        pass
class EmailChannel(PushChannel):
    def send(self, user, content):
        # 使用 Resend API
        pass
class WeWorkChannel(PushChannel):
    def send(self, user, content):
        # 企微 Webhook
        pass
class TelegramChannel(PushChannel):
    def send(self, user, content):
        # Telegram Bot API
        pass
交付物
[ ] FastAPI 后端服务
[ ] 用户注册/登录界面
[ ] 订阅管理页面
[ ] 多渠道推送模块（需包含失败重试机制）
[ ] API 文档
第四阶段：智能化（语义检索与个性化期）
周期：3-4 周
目标：实现语义级别的精准推送
技术栈
向量数据库：Qdrant / Milvus / pgvector
嵌入模型：BGE-m3 / SPECTER2 / OpenAI Embeddings
全文搜索：Elasticsearch (BM25)
前端：React / Vue
核心任务
1. 向量化与存储
# 论文入库时生成 embedding
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-m3-v2')
embedding = model.encode(paper.abstract)
# 存储到向量库（Qdrant 标准写法）
qdrant_client.upsert(
    collection_name="papers",
    points=[PointStruct(
        id=paper.id,
        vector=embedding,
        payload={"title": paper.title, "abstract": paper.abstract}
    )]
)
2. 混合检索（注意分数量纲与归一化）
def hybrid_search(query: str, query_vector: list, top_k: int = 10):
    # 1. 获取 BM25 分数（ES 返回结构含 _score 和 _id）
    es_results = elasticsearch.search(query, size=top_k * 2)
    # 2. 获取语义分数（Qdrant 返回结构含 score 和 id）
    qdrant_results = qdrant_client.search(query_vector, limit=top_k * 2)
    # 3. 分数融合（不能直接相加，因量纲不同）
    # 推荐使用倒数秩融合（Reciprocal Rank Fusion, RRF）或先 Min-Max 归一化再加权
    all_ids = set([r["_id"] for r in es_results] + [str(r.id) for r in qdrant_results])
    rrf_scores = {}
    k = 60  # RRF 常数
    for rank, r in enumerate(es_results):
        rrf_scores[r["_id"]] = rrf_scores.get(r["_id"], 0) + 1.0 / (k + rank + 1)
    for rank, r in enumerate(qdrant_results):
        rrf_scores[str(r.id)] = rrf_scores.get(str(r.id), 0) + 1.0 / (k + rank + 1)
    # 4. 按 RRF 分数排序并返回 top_k
    sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_ids[:top_k]
3. 个性化反馈闭环
# 用户行为记录
class UserFeedback:
    paper_id: int
    action: Literal["save", "hide", "click"]
    timestamp: datetime
# 动态调整用户画像
def update_user_profile(user_id: int, feedback: UserFeedback):
    if feedback.action == "hide":
        # 降低相似向量权重
        decrease_weight(user_id, feedback.paper_id)
    elif feedback.action == "save":
        # 提升相似向量权重
        increase_weight(user_id, feedback.paper_id)
交付物
[ ] 向量数据库部署
[ ] 嵌入服务 API
[ ] 基于 RRF 的混合检索引擎
[ ] 用户反馈收集接口
[ ] 前端搜索界面
第五阶段：深水区（深度解析与边缘场景攻克期）
周期：持续迭代
目标：达到示例级别的细节精度
技术栈
API 客户端：openreview-py (OpenReview 官方 Python 库)
爬虫框架：Scrapy (仅作辅助)
PDF 解析：PyMuPDF (fitz)
HTML 解析：BeautifulSoup4
LLM 编排：原生 SDK Tool Use / LangChain 封装
核心任务
1. 复杂站点对接（API 优先）
# OpenReview：优先使用官方 API 与 Python 客户端
import openreview
# 获取指定会议的投稿及更新情况，比爬虫更稳定
client = openreview.Client(baseurl='https://api2.openreview.net')
notes = client.get_all_notes(content={'venueid': 'ICLR.cc/2026/Conference'})
*注：仅在 API 无法获取特定前端渲染内容时，才使用 Scrapy 配合页面哈希/Last Modified 做增量爬取，并严格遵守 robots.txt 与频率限制。*
2. PDF/HTML 深度解析（LLM 辅助章节拆分）
import fitz  # PyMuPDF
def extract_method_section(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    full_text = "\n".join([page.get_text() for page in doc])
    # 现实情况：不同论文的章节命名千差万别，纯规则匹配极易误判
    # 推荐：先用 LLM 对全文做"章节级结构化拆分"，再提取 Method 部分
    chapters = llm_extract_chapters(full_text) 
    # 返回: [{"type": "method", "text": "..."}, {"type": "exp", "text": "..."}]
    method_text = "\n".join([c["text"] for c in chapters if c["type"] == "method"])
    return method_text
3. 防幻觉与事实锚定（基于模型原生结构化能力）
# 优先使用模型原生 Structured Outputs 能力保证格式
# 以下以 Anthropic Tool Use 或 OpenAI Structured Outputs 为底层，LangChain 作上层封装
from pydantic import BaseModel
class ModuleInnovation(BaseModel):
    module_name: str  # 具体模块名
    innovation: str   # 创新点描述
# 事后校验逻辑（防止 LLM 编造不存在的模块名）
def validate_summary(summary: ModuleInnovation, paper_text: str) -> bool:
    module_name = summary.module_name.lower()
    # 检查模块名是否在原文中真实出现（允许简单的单复数/连字符变形）
    return module_name in paper_text.lower() or module_name.replace("-", "") in paper_text.lower()
4. 多级 LLM 总结策略（降本增效）
# 成本优化的分级处理
def summarize_paper(paper: Paper) -> str:
    relevance = calculate_relevance(paper, user_keywords)
    if relevance < 0.3:
        # 低相关：简单规则提取（不调用 LLM）
        return rule_based_summary(paper)
    elif relevance < 0.7:
        # 中相关：小模型快速总结（仅用标题+摘要）
        return small_model_summarize(paper)
    else:
        # 高相关：强模型 + PDF 深度分析（提取 Method 段落）
        method_text = extract_method_section(paper.pdf_path)
        return large_model_deep_summarize(paper, method_text)
交付物
[ ] OpenReview API 对接模块
[ ] LLM 辅助的 PDF 章节拆分模块
[ ] 基于原生结构化输出的防幻觉校验系统
[ ] 多级 LLM 总结编排器
项目目录结构
AgentCodes/001/
├── CLAUDE.md                 # 本文件
├── README.md                 # 项目说明
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板
├── .gitignore
│
├── config/                   # 配置文件
│   ├── __init__.py
│   ├── settings.py           # 全局配置
│   └── prompts.py            # LLM Prompt 模板
│
├── src/
│   ├── __init__.py
│   │
│   ├── fetchers/             # 数据源适配器
│   │   ├── __init__.py
│   │   ├── base.py           # 抽象基类
│   │   ├── arxiv.py          # arXiv API
│   │   ├── openalex.py       # OpenAlex API
│   │   ├── openreview.py     # OpenReview API (openreview-py)
│   │   └── semantic_scholar.py
│   │
│   ├── parsers/              # 论文解析
│   │   ├── __init__.py
│   │   └── paper.py
│   │
│   ├── summarizers/          # LLM 总结
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── openai_client.py
│   │   └── anthropic_client.py
│   │
│   ├── database/             # 数据库层
│   │   ├── __init__.py
│   │   ├── models.py         # SQLAlchemy 模型
│   │   └── crud.py           # CRUD 操作
│   │
│   ├── pushers/              # 推送渠道
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── email.py
│   │   ├── wework.py
│   │   └── telegram.py
│   │
│   ├── vector/               # 向量检索
│   │   ├── __init__.py
│   │   ├── embeddings.py
│   │   └── search.py
│   │
│   ├── crawlers/             # 辅助爬虫（仅当 API 不支持时使用）
│   │   └── __init__.py
│   │
│   ├── pipelines/            # 处理流水线
│   │   ├── __init__.py
│   │   ├── daily.py          # 每日报表生成
│   │   └── scheduler.py      # 定时任务
│   │
│   └── api/                  # Web API（第三阶段）
│       ├── __init__.py
│       ├── main.py           # FastAPI 入口
│       └── routes/
│           ├── __init__.py
│           ├── auth.py
│           ├── subscriptions.py
│           └── reports.py
│
├── templates/                # Jinja2 模板
│   ├── daily_report.md
│   └── email.html
│
├── tests/                    # 测试
│   ├── __init__.py
│   ├── test_fetchers.py
│   └── test_summarizers.py
│
├── scripts/                  # 工具脚本
│   ├── init_db.py            # 初始化数据库
│   └── run_once.py           # 单次运行脚本
│
└── main.py                   # 主入口
环境变量配置
# .env 文件模板
# LLM API
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/paper_pusher
# 向量数据库
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=papers
# 推送渠道
RESEND_API_KEY=re_xxx
WEWORK_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
TELEGRAM_BOT_TOKEN=xxx
# 调度
SCHEDULER_TIMEZONE=Asia/Shanghai
DAILY_RUN_TIME=02:00
开发规范
Git 提交规范
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建/工具链相关
示例：
feat(arxiv): implement basic arXiv API fetcher
fix(parser): handle duplicate paper IDs
docs: update CLAUDE.md with phase 2 details
代码风格
Python：遵循 PEP 8，使用 black 格式化
类型注解：使用 typing 模块添加类型提示
文档字符串：使用 Google 风格 docstring
def fetch_papers(query: str, limit: int = 10) -> List[Paper]:
    """Fetch papers from arXiv API.
    Args:
        query: Search query string
        limit: Maximum number of papers to fetch
    Returns:
        List of Paper objects
    Raises:
        APIError: If the API request fails
    """
    ...
日志与可观测性
使用 structlog 或 loguru 记录结构化日志。
关键路径必须打点：API 请求耗时、LLM Token 消耗、抓取成功/失败数量、推送状态。
流水线需实现幂等性：通过唯一时间窗口或 Job ID 确保重复触发不产生副作用。
API 使用与频率限制
必须遵守各学术源的使用条款：arXiv 建议请求间隔不低于 3 秒；OpenAlex 无明确限制但需合理并发；Semantic Scholar 有 RPM（每分钟请求数）限制。
在 Adapter 实现中加入通用的 Rate Limiter（如 tenacity 的重试机制或令牌桶算法）。
当前待办事项
第一阶段任务
