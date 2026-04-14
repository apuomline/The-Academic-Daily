"""FastAPI application for Academic Paper Pusher."""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import settings


# ==================== 日志配置 ====================
class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器."""

    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'

    def format(self, record):
        # 添加颜色
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)


def setup_logging():
    """配置日志系统."""
    # 创建根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))

    # 清除现有处理器
    root_logger.handlers.clear()

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))

    # 创建彩色格式化器
    formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    # 添加处理器
    root_logger.addHandler(console_handler)

    # 配置第三方库的日志级别
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.INFO)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

    return root_logger


# 初始化日志
logger = setup_logging()


# ==================== 请求日志中间件 ====================
async def log_requests(request: Request, call_next):
    """记录所有 HTTP 请求."""
    start_time = datetime.now()

    # 记录请求
    logger.info(f"➤ {request.method} {request.url.path}")

    # 处理请求
    response = await call_next(request)

    # 计算处理时间
    process_time = (datetime.now() - start_time).total_seconds()
    status_color = '\033[32m' if response.status_code < 400 else '\033[31m'
    status_reset = '\033[0m'

    logger.info(
        f"◯ {request.method} {request.url.path} - "
        f"{status_color}{response.status_code}{status_reset} - "
        f"{process_time:.3f}s"
    )

    return response


# ==================== 应用生命周期 ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events.

    Startup:
    - Initialize database connection
    - Validate configuration
    - Log startup info

    Shutdown:
    - Close database connections
    - Cleanup resources
    """
    # Startup
    logger.info("=" * 60)
    logger.info("🚀 启动学术论文推送助手 API 服务")
    logger.info("=" * 60)
    logger.info(f"📊 数据库: {settings.database_url}")
    logger.info(f"🤖 LLM 提供商: {settings.llm_provider}")
    logger.info(f"🧠 LLM 模型: {settings.llm_model}")
    logger.info(f"📧 邮件服务: {'已启用' if settings.email_enabled else '未启用'}")

    # Initialize database
    try:
        from src.database import db_manager
        db_manager.create_tables()
        logger.info("✅ 数据库初始化成功")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")

    logger.info("🌐 API 服务已启动，访问 http://localhost:8000")
    logger.info("=" * 60)

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info("🛑 正在关闭学术论文推送助手 API 服务...")
    logger.info("=" * 60)


# ==================== FastAPI 应用 ====================
# Create FastAPI application
app = FastAPI(
    title="Academic Paper Pusher API",
    description="Backend service for Academic Paper Pusher - Configuration and Pipeline Management",
    version="1.0.0",
    lifespan=lifespan,
)

# Add request logging middleware
app.middleware("http")(log_requests)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get paths
base_dir = Path(__file__).parent.parent.parent
static_dir = base_dir / "static"
templates_dir = base_dir / "templates"

# Ensure directories exist
static_dir.mkdir(exist_ok=True)
templates_dir.mkdir(exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(templates_dir))


# ==================== 路由 ====================
# Health check endpoint
@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


# System status endpoint
@app.get("/api/status", tags=["System"])
async def system_status():
    """Get system status."""
    try:
        from src.database import db_manager
        # Test database connection
        session = db_manager.get_session()
        session.close()
        db_connected = True
    except Exception:
        db_connected = False

    return {
        "status": "running" if db_connected else "degraded",
        "config_loaded": True,
        "database_connected": db_connected,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
    }


# Root endpoint - serve configuration page
@app.get("/", tags=["UI"])
async def root(request: Request):
    """Serve configuration management interface."""
    return templates.TemplateResponse("config.html", {"request": request})


# Include routers
from src.api.routes.config import router as config_router
from src.api.routes import pipeline_simple
pipeline_router = pipeline_simple.router

app.include_router(config_router, prefix="/api/config", tags=["Configuration"])
app.include_router(pipeline_router, prefix="/api/pipeline", tags=["Pipeline"])
