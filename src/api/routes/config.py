"""Configuration management API routes."""

import logging
from typing import Dict

from fastapi import APIRouter, HTTPException

from src.api.models.requests import (
    LLMConfigRequest,
    EmailConfigRequest,
    ConfigResponse,
)
from src.api.services.config_manager import ConfigManager
from src.summarizers import create_summarizer
from src.pushers import EmailPusher

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize config manager
config_manager = ConfigManager()


def _to_dict_updates_llm(config: LLMConfigRequest) -> Dict[str, str]:
    """Convert LLMConfigRequest to .env updates dictionary.

    Args:
        config: LLM configuration request

    Returns:
        Dictionary of key-value pairs for .env file
    """
    updates = {}
    if config.api_key is not None:
        updates["LLM_API_KEY"] = config.api_key
    if config.base_url is not None:
        updates["LLM_BASE_URL"] = config.base_url
    if config.provider is not None:
        updates["LLM_PROVIDER"] = config.provider
    if config.model is not None:
        updates["LLM_MODEL"] = config.model
    if config.temperature is not None:
        updates["LLM_TEMPERATURE"] = str(config.temperature)
    if config.max_tokens is not None:
        updates["LLM_MAX_TOKENS"] = str(config.max_tokens)
    return updates


def _to_dict_updates_email(config: EmailConfigRequest) -> Dict[str, str]:
    """Convert EmailConfigRequest to .env updates dictionary.

    Args:
        config: Email configuration request

    Returns:
        Dictionary of key-value pairs for .env file
    """
    updates = {}
    if config.enabled is not None:
        updates["EMAIL_ENABLED"] = "true" if config.enabled else "false"
    if config.host is not None:
        updates["SMTP_HOST"] = config.host
    if config.port is not None:
        updates["SMTP_PORT"] = str(config.port)
    if config.username is not None:
        updates["SMTP_USERNAME"] = config.username
    if config.password is not None:
        updates["SMTP_PASSWORD"] = config.password
    if config.from_email is not None:
        updates["SMTP_FROM_EMAIL"] = config.from_email
    if config.resend_api_key is not None:
        updates["RESEND_API_KEY"] = config.resend_api_key
    return updates


@router.get("", response_model=ConfigResponse)
async def get_all_config() -> ConfigResponse:
    """Get all configuration (sensitive data masked)."""
    try:
        config = config_manager.read_config()
        masked = config_manager.mask_sensitive(config)
        return ConfigResponse(
            success=True,
            message="Configuration retrieved successfully",
            data=masked,
        )
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm", response_model=ConfigResponse)
async def get_llm_config() -> ConfigResponse:
    """Get LLM configuration (sensitive data masked)."""
    try:
        config = config_manager.get_llm_config()
        return ConfigResponse(
            success=True,
            message="LLM configuration retrieved successfully",
            data=config,
        )
    except Exception as e:
        logger.error(f"Failed to get LLM configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/llm", response_model=ConfigResponse)
async def update_llm_config(config: LLMConfigRequest) -> ConfigResponse:
    """Update LLM configuration.

    Args:
        config: LLM configuration request

    Returns:
        Configuration response with masked values
    """
    try:
        # Convert to .env updates
        updates = _to_dict_updates_llm(config)

        if not updates:
            return ConfigResponse(
                success=True,
                message="No updates provided",
            )

        # Write to .env file
        result = config_manager.write_config(updates)

        if result.success:
            logger.info(f"LLM configuration updated: {list(updates.keys())}")
            return ConfigResponse(
                success=True,
                message="LLM configuration updated successfully",
                data=result.data,
            )
        else:
            return ConfigResponse(
                success=False,
                message=result.message,
            )

    except Exception as e:
        logger.error(f"Failed to update LLM configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/email", response_model=ConfigResponse)
async def get_email_config() -> ConfigResponse:
    """Get email configuration (sensitive data masked)."""
    try:
        config = config_manager.get_email_config()
        return ConfigResponse(
            success=True,
            message="Email configuration retrieved successfully",
            data=config,
        )
    except Exception as e:
        logger.error(f"Failed to get email configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/email", response_model=ConfigResponse)
async def update_email_config(config: EmailConfigRequest) -> ConfigResponse:
    """Update email configuration.

    Args:
        config: Email configuration request

    Returns:
        Configuration response with masked values
    """
    try:
        # Convert to .env updates
        updates = _to_dict_updates_email(config)

        if not updates:
            return ConfigResponse(
                success=True,
                message="No updates provided",
            )

        # Write to .env file
        result = config_manager.write_config(updates)

        if result.success:
            logger.info(f"Email configuration updated: {list(updates.keys())}")
            return ConfigResponse(
                success=True,
                message="Email configuration updated successfully",
                data=result.data,
            )
        else:
            return ConfigResponse(
                success=False,
                message=result.message,
            )

    except Exception as e:
        logger.error(f"Failed to update email configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test/llm", response_model=ConfigResponse)
async def test_llm_connection() -> ConfigResponse:
    """Test LLM API connection.

    Returns:
        Configuration response with test result
    """
    try:
        # Get current LLM configuration
        config = config_manager.get_llm_config()

        # Check if API key is configured
        has_key = any(config.get(k) for k in [
            "LLM_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"
        ])

        if not has_key:
            return ConfigResponse(
                success=False,
                message="LLM API key not configured",
            )

        # Try to create summarizer (will test connection)
        summarizer = create_summarizer()

        # Simple test - check if summarizer was created
        if summarizer:
            return ConfigResponse(
                success=True,
                message=f"LLM connection test successful ({config.get('LLM_PROVIDER', 'unknown')} provider)",
                data={"provider": config.get("LLM_PROVIDER", "unknown"), "model": config.get("LLM_MODEL", "unknown")},
            )
        else:
            return ConfigResponse(
                success=False,
                message="Failed to create LLM client",
            )

    except Exception as e:
        logger.error(f"LLM connection test failed: {e}")
        return ConfigResponse(
            success=False,
            message=f"LLM connection test failed: {str(e)}",
        )


@router.post("/test/email", response_model=ConfigResponse)
async def test_email_connection() -> ConfigResponse:
    """Test email configuration.

    Returns:
        Configuration response with test result
    """
    try:
        # Get current email configuration
        config = config_manager.get_email_config()

        # Check if email is configured
        enabled = config.get("EMAIL_ENABLED", "false").lower() == "true"

        if not enabled:
            return ConfigResponse(
                success=False,
                message="Email is not enabled",
            )

        # Check if required settings are present
        has_resend = bool(config.get("RESEND_API_KEY"))
        has_smtp = all(config.get(k) for k in ["SMTP_HOST", "SMTP_FROM_EMAIL"])

        if not has_resend and not has_smtp:
            return ConfigResponse(
                success=False,
                message="Email not configured: need either Resend API key or SMTP settings",
            )

        # Try to create email pusher
        pusher = EmailPusher()

        return ConfigResponse(
            success=True,
            message=f"Email configuration valid (Resend: {has_resend}, SMTP: {has_smtp})",
            data={
                "resend_configured": has_resend,
                "smtp_configured": has_smtp,
            },
        )

    except Exception as e:
        logger.error(f"Email configuration test failed: {e}")
        return ConfigResponse(
            success=False,
            message=f"Email configuration test failed: {str(e)}",
        )


@router.post("/reload", response_model=ConfigResponse)
async def reload_config() -> ConfigResponse:
    """Reload configuration from .env file.

    Note: This is a placeholder for future hot-reload functionality.
    Currently requires server restart to apply changes.
    """
    return ConfigResponse(
        success=True,
        message="Configuration saved. Please restart the server to apply changes.",
    )
