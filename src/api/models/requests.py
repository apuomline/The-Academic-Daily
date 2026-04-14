"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Literal


class LLMConfigRequest(BaseModel):
    """Request model for LLM configuration updates."""

    api_key: Optional[str] = Field(None, description="LLM API key")
    base_url: Optional[str] = Field(None, description="API base URL")
    provider: Optional[str] = Field(None, description="LLM provider (openai, anthropic, bigmodel, zhipu)")
    model: Optional[str] = Field(None, description="Model name")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature (0.0-2.0)")
    max_tokens: Optional[int] = Field(None, ge=1, le=128000, description="Max tokens")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: Optional[str]) -> Optional[str]:
        """Validate LLM provider."""
        if v is not None:
            valid_providers = {"openai", "anthropic", "bigmodel", "zhipu"}
            if v.lower() not in valid_providers:
                raise ValueError(f"Invalid provider. Must be one of: {', '.join(valid_providers)}")
            return v.lower()
        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate API key is not empty string."""
        if v == "":
            raise ValueError("API key cannot be empty")
        return v


class EmailConfigRequest(BaseModel):
    """Request model for email configuration updates."""

    enabled: Optional[bool] = Field(None, description="Enable/disable email")
    host: Optional[str] = Field(None, description="SMTP host")
    port: Optional[int] = Field(None, ge=1, le=65535, description="SMTP port")
    username: Optional[str] = Field(None, description="SMTP username")
    password: Optional[str] = Field(None, description="SMTP password")
    from_email: Optional[str] = Field(None, description="From email address")
    resend_api_key: Optional[str] = Field(None, description="Resend API key")

    @field_validator("from_email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Basic email validation."""
        if v is not None and v:
            if "@" not in v:
                raise ValueError("Invalid email address")
        return v


class TestConnectionRequest(BaseModel):
    """Request model for testing connections."""

    config_type: Literal["llm", "email"] = Field(..., description="Type of connection to test")


class ConfigResponse(BaseModel):
    """Response model for configuration operations."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str
    version: str


class StatusResponse(BaseModel):
    """Response model for system status."""

    status: str
    config_loaded: bool
    database_connected: bool


class PipelineRunRequest(BaseModel):
    """Request model for running pipeline."""

    keywords: list[str] = Field(default_factory=lambda: ["llm"], description="Search keywords")
    exclude_keywords: Optional[list[str]] = Field(None, description="Keywords to exclude")


class PipelineRunResponse(BaseModel):
    """Response model for pipeline execution."""

    success: bool
    message: str
    papers_fetched: Optional[int] = None
    report_path: Optional[str] = None
    errors: Optional[list[str]] = None
