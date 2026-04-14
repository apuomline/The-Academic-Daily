# 学术论文自动推送助手

第二阶段（Phase 2）已实现完成。

## 功能

### 核心功能

- **多源数据抓取**：支持 arXiv、OpenAlex、Semantic Scholar
- **数据持久化**：PostgreSQL/SQLite 数据库存储
- **智能总结**：使用 LLM 提取论文创新点、方法细节、实验结果
- **版本追踪**：识别论文的 v1/v2/v3 更新，合并同一条目
- **模板渲染**：Jinja2 模板生成 Markdown/HTML 报告
- **邮件推送**：支持 SMTP 和 Resend API 发送邮件日报
- **定时调度**：APScheduler 支持定时自动执行
- **个性化订阅**：用户可自定义关注主题、排除关键词

### 第二阶段新增功能

- ✅ 数据库持久化（PostgreSQL/SQLite）
- ✅ 多数据源支持（arXiv、OpenAlex、Semantic Scholar）
- ✅ 邮件推送（SMTP、Resend）
- ✅ 定时任务调度
- ✅ Jinja2 模板渲染
- ✅ 日报生成和订阅管理

## 安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

## 配置

复制 `.env.example` 为 `.env` 并配置：

```bash
cp .env.example .env
```

### 环境变量配置

```bash
# LLM API 配置
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
LLM_PROVIDER=bigmodel
LLM_MODEL=glm-4-flash

# 数据库配置
DATABASE_URL=sqlite:///papers.db
# DATABASE_URL=postgresql://user:pass@localhost/paper_pusher

# 邮件配置
EMAIL_ENABLED=true
RESEND_API_KEY=re_xxx
SMTP_FROM_EMAIL=noreply@yourdomain.com
```

## 使用方法

### 基本使用

```bash
# 初始化数据库
python main.py --init-db

# 单次运行
python main.py "medical image segmentation" --max-results 10

# 多源抓取
python main.py "llm" --sources arxiv openalex --max-results 10

# 排除关键词
python main.py "segmentation" --exclude survey review --max-results 10
```

### 数据库模式

```bash
# 运行完整流水线（包含数据库操作）
python main.py "llm" --pipeline

# 不使用数据库
python main.py "llm" --no-db
```

### 定时调度

```bash
# 每天凌晨 2 点自动运行
python main.py "llm" --schedule --schedule-time 02:00

# 自定义调度时间
python main.py "llm" --schedule --schedule-time 08:30
```

### 邮件推送

```bash
# 发送测试邮件
python main.py "llm" --send-email --email your@email.com
```

### Web API 服务

```bash
# 启动 Web 服务（开发模式）
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 启动 Web 服务（生产模式）
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# 访问配置管理页面
http://localhost:8000

# 访问 API 文档
http://localhost:8000/api/docs
```

## 命令行选项

```
positional arguments:
  keywords              搜索关键词

数据源选项:
  --sources {arxiv,openalex,semantic_scholar,all}
                        数据源 (默认: arxiv)
  --last-24h            最近24小时
  --date-range START END 日期范围 (YYYYMMDD)
  --categories [CATEGORIES ...]
                        arXiv 分类
  --max-results MAX_RESULTS
                        最大结果数

LLM 选项:
  --provider {openai,anthropic,bigmodel,zhipu}
                        LLM 提供商
  --model MODEL         模型名称

输出选项:
  --output OUTPUT       输出文件路径
  --format {markdown,html,text,all}
                        输出格式

数据库选项:
  --init-db             初始化数据库
  --no-db                跳过数据库操作

邮件选项:
  --send-email           发送邮件
  --email EMAIL          测试邮件地址

调度选项:
  --schedule             定时模式
  --schedule-time HH:MM  运行时间
  --pipeline             运行完整流水线
```

## 项目结构

```
.
├── main.py                   # CLI 主入口脚本
├── config/                   # 配置模块
├── src/
│   ├── api/                  # FastAPI Web 服务
│   │   ├── main.py           # FastAPI 应用入口
│   │   ├── routes/           # API 路由
│   │   ├── models/           # Pydantic 模型
│   │   └── services/         # 业务服务
│   ├── database/             # 数据库层
│   │   ├── models.py         # SQLAlchemy 模型
│   │   └── crud.py           # CRUD 操作
│   ├── fetchers/             # 数据源适配器
│   │   ├── arxiv.py          # arXiv API
│   │   └── openalex.py       # OpenAlex/Semantic Scholar
│   ├── parsers/              # 论文解析
│   ├── summarizers/          # LLM 总结
│   ├── pushers/              # 推送渠道
│   │   └── email.py          # 邮件推送
│   └── pipelines/            # 处理流水线
│       ├── scheduler.py      # 定时调度
│       ├── template_renderer.py  # 模板渲染
│       └── daily.py          # 每日流水线
├── static/                   # 静态文件
│   ├── css/                  # 样式文件
│   └── js/                   # JavaScript 文件
├── templates/                # Jinja2 模板
│   ├── config.html           # 配置管理页面
│   ├── daily_report.md       # Markdown 报告模板
│   └── email.html            # HTML 邮件模板
├── tests/                    # 测试文件
└── output/                   # 输出目录
```

## 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_database.py -v
pytest tests/test_multisource.py -v

# 测试覆盖率
pytest tests/ --cov=src --cov-report=html
```

## 数据库模型

### Paper（论文表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| arxiv_id | String(50) | arXiv ID（唯一） |
| doi | String(100) | DOI（唯一） |
| title | Text | 论文标题 |
| abstract | Text | 摘要 |
| source | String(50) | 数据源 |
| published_date | DateTime | 发表日期 |
| updated_date | DateTime | 更新日期 |

### Subscription（订阅表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_email | String(255) | 用户邮箱 |
| keywords | JSON | 关注关键词 |
| exclude_keywords | JSON | 排除关键词 |
| push_time | String(10) | 推送时间 |
| timezone | String(50) | 时区 |
| is_active | Boolean | 是否激活 |

### PushLog（推送日志表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| subscription_id | Integer | 订阅 ID |
| channel | String(50) | 推送渠道 |
| report_date | DateTime | 日报日期 |
| status | String(20) | 状态 |
| error_msg | Text | 错误信息 |

## 第三阶段（已完成部分）

- ✅ Web 后端框架（FastAPI）
- ✅ 配置管理界面（LLM 和邮箱配置）
- ✅ 配置持久化（自动更新 .env 文件）
- ✅ API 端点（配置管理、流水线执行）
- ⏳ 用户系统（注册/登录）- 待实现
- ⏳ 多渠道推送（企微、钉钉、Telegram）- 待实现

## 常见问题

### Q: 如何配置 PostgreSQL？

A: 修改 `.env` 文件中的 `DATABASE_URL`：
```
DATABASE_URL=postgresql://user:password@localhost:5432/paper_pusher
```

### Q: 如何使用 Resend 发送邮件？

A: 在 `.env` 中配置：
```
EMAIL_ENABLED=true
RESEND_API_KEY=re_xxx
SMTP_FROM_EMAIL=noreply@yourdomain.com
```

### Q: 如何设置定时任务？

A: 使用 `--schedule` 参数：
```bash
python main.py "llm" --schedule --schedule-time 02:00
```

### Q: 测试状态？

A: 所有 60 个测试通过：
```
60 passed in 6.78s
```

### Q: 如何启动 Web 配置界面？

A: 使用 uvicorn 启动 FastAPI 服务：
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```
然后访问 http://localhost:8000 进行配置。

### Q: 配置保存后需要重启服务吗？

A: 是的，配置保存到 `.env` 文件后，需要重启服务才能生效：
```bash
# 按 Ctrl+C 停止服务，然后重新启动
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Q: Web API 有哪些端点？

A: 主要端点包括：
- `GET /` - 配置管理页面
- `GET /api/docs` - API 文档（Swagger UI）
- `GET /api/config/llm` - 获取 LLM 配置
- `PUT /api/config/llm` - 更新 LLM 配置
- `GET /api/config/email` - 获取邮箱配置
- `PUT /api/config/email` - 更新邮箱配置
- `POST /api/pipeline/run` - 运行完整流水线
