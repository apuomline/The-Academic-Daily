"""Settings configuration module."""

import os
import sys
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Check if running in test mode
TEST_MODE = "pytest" in sys.modules or "unittest" in sys.modules


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # LLM API Keys - 支持多种配置方式
    # 优先使用 llm_api_key，如果没有则尝试特定提供商的 key
    llm_api_key: Optional[str] = field(default_factory=lambda: os.getenv("LLM_API_KEY"))
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))

    # LLM API Base URL (用于智谱AI等兼容 OpenAI 的服务)
    llm_base_url: Optional[str] = field(default_factory=lambda: os.getenv("LLM_BASE_URL"))

    # LLM Settings
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    llm_temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.3")))
    llm_max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "2000")))

    # arXiv Settings
    arxiv_api_url: str = "https://export.arxiv.org/api/query"
    arxiv_max_results: int = field(default_factory=lambda: int(os.getenv("ARXIV_MAX_RESULTS", "100")))
    arxiv_request_delay: float = 3.0  # Seconds between requests (arXiv recommends 3+ seconds)

    # Output Settings
    output_dir: str = field(default_factory=lambda: os.getenv("OUTPUT_DIR", "output"))
    report_filename: str = field(default_factory=lambda: os.getenv("REPORT_FILENAME", "daily_report.md"))

    # Database Settings
    database_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL",
        "sqlite:///papers.db"  # Default to SQLite for easy setup
    ))

    # Email Settings
    email_enabled: bool = field(default_factory=lambda: os.getenv("EMAIL_ENABLED", "true").lower() == "true")
    smtp_host: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_HOST"))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_username: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_USERNAME"))
    smtp_password: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_PASSWORD"))
    smtp_from_email: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_FROM_EMAIL"))
    resend_api_key: Optional[str] = field(default_factory=lambda: os.getenv("RESEND_API_KEY"))

    # Log Settings
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    def get_api_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Get API key for the specified provider.

        优先级：
        1. llm_api_key (通用 key)
        2. 特定提供商的 key (openai_api_key, anthropic_api_key)

        Args:
            provider: Provider name (openai/anthropic). If None, uses current llm_provider.

        Returns:
            API key string or None
        """
        if self.llm_api_key:
            return self.llm_api_key

        provider = provider or self.llm_provider
        if provider == "openai":
            return self.openai_api_key
        elif provider == "anthropic":
            return self.anthropic_api_key

        return None

    def get_base_url(self) -> Optional[str]:
        """Get the base URL for LLM API."""
        return self.llm_base_url

    def __post_init__(self):
        """Validate settings after initialization."""
        # Skip API key validation in test mode
        if not TEST_MODE:
            # Check if at least one API key is configured
            has_key = (
                self.llm_api_key or
                self.openai_api_key or
                self.anthropic_api_key
            )
            if not has_key:
                raise ValueError(
                    "At least one LLM API key must be set. "
                    "Please set LLM_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY in .env file."
                )

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)


# Global settings instance
settings = Settings()
