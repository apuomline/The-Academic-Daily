"""Configuration manager service for .env file operations."""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import dotenv_values


@dataclass
class ConfigResult:
    """Result of a configuration operation."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class ConfigManager:
    """Manages .env file operations with safety mechanisms.

    Features:
    - Atomic write pattern (write to temp, then rename)
    - Automatic backup before modifications
    - Configuration validation
    - Sensitive data masking for API responses
    """

    # Sensitive keys that should be masked in responses
    SENSITIVE_KEYS = {
        "API_KEY",
        "PASSWORD",
        "SECRET",
        "TOKEN",
        "LLM_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "SMTP_PASSWORD",
        "RESEND_API_KEY",
    }

    # Valid LLM providers
    VALID_PROVIDERS = {"openai", "anthropic", "bigmodel", "zhipu"}

    def __init__(self, env_path: str = ".env"):
        """Initialize ConfigManager.

        Args:
            env_path: Path to .env file (relative to project root)
        """
        # Get project root (4 levels up from this file)
        self.root_dir = Path(__file__).parent.parent.parent.parent
        self.env_path = self.root_dir / env_path
        self.backup_path = self.root_dir / f"{env_path}.backup"

    def read_config(self) -> Dict[str, str]:
        """Read .env file and return as dictionary.

        Returns:
            Dictionary of environment variables
        """
        if not self.env_path.exists():
            return {}

        return dict(dotenv_values(self.env_path))

    def write_config(self, updates: Dict[str, str], create_backup: bool = True) -> ConfigResult:
        """Atomically write configuration updates to .env file.

        Args:
            updates: Dictionary of key-value pairs to update
            create_backup: Whether to create backup before writing

        Returns:
            ConfigResult with success status and message
        """
        try:
            # Read existing config
            existing_config = self.read_config()

            # Create backup if requested and file exists
            if create_backup and self.env_path.exists():
                self.backup_config()

            # Merge updates with existing config
            new_config = {**existing_config, **updates}

            # Validate configuration
            validation_result = self.validate_config(new_config)
            if not validation_result.success:
                return validation_result

            # Write to temporary file
            temp_path = self.root_dir / ".env.tmp"
            self._write_env_file(temp_path, new_config)

            # Atomic rename
            temp_path.replace(self.env_path)

            return ConfigResult(
                success=True,
                message="Configuration updated successfully",
                data=self.mask_sensitive(new_config),
            )

        except Exception as e:
            return ConfigResult(
                success=False,
                message=f"Failed to update configuration: {str(e)}",
            )

    def backup_config(self) -> bool:
        """Create backup of current .env file.

        Returns:
            True if backup successful, False otherwise
        """
        try:
            if self.env_path.exists():
                shutil.copy2(self.env_path, self.backup_path)
                return True
            return False
        except Exception:
            return False

    def restore_backup(self) -> ConfigResult:
        """Restore configuration from backup.

        Returns:
            ConfigResult with success status and message
        """
        try:
            if not self.backup_path.exists():
                return ConfigResult(
                    success=False,
                    message="No backup file found",
                )

            shutil.copy2(self.backup_path, self.env_path)
            return ConfigResult(
                success=True,
                message="Configuration restored from backup",
            )
        except Exception as e:
            return ConfigResult(
                success=False,
                message=f"Failed to restore backup: {str(e)}",
            )

    def validate_config(self, config: Dict[str, str]) -> ConfigResult:
        """Validate configuration values.

        Args:
            config: Configuration dictionary to validate

        Returns:
            ConfigResult with validation status
        """
        # Validate LLM provider
        provider = config.get("LLM_PROVIDER", "").lower()
        if provider and provider not in self.VALID_PROVIDERS:
            return ConfigResult(
                success=False,
                message=f"Invalid LLM provider: {provider}. Valid options: {', '.join(self.VALID_PROVIDERS)}",
            )

        # Validate email port
        port = config.get("SMTP_PORT")
        if port:
            try:
                port_num = int(port)
                if not (1 <= port_num <= 65535):
                    return ConfigResult(
                        success=False,
                        message=f"Invalid SMTP port: {port_num}. Must be between 1 and 65535",
                    )
            except ValueError:
                return ConfigResult(
                    success=False,
                    message=f"Invalid SMTP port: {port}. Must be a number",
                )

        # Validate temperature
        temperature = config.get("LLM_TEMPERATURE")
        if temperature:
            try:
                temp_val = float(temperature)
                if not (0.0 <= temp_val <= 2.0):
                    return ConfigResult(
                        success=False,
                        message=f"Invalid LLM temperature: {temp_val}. Must be between 0.0 and 2.0",
                    )
            except ValueError:
                return ConfigResult(
                    success=False,
                    message=f"Invalid LLM temperature: {temperature}. Must be a number",
                )

        return ConfigResult(success=True, message="Configuration valid")

    def mask_sensitive(self, config: Dict[str, str]) -> Dict[str, str]:
        """Mask sensitive values in configuration for API responses.

        Args:
            config: Configuration dictionary

        Returns:
            Configuration with sensitive values masked
        """
        masked = {}
        for key, value in config.items():
            if any(sensitive in key.upper() for sensitive in self.SENSITIVE_KEYS):
                # Show first 4 and last 4 characters, mask the rest
                if value and len(value) > 8:
                    masked[key] = f"{value[:4]}...{value[-4:]}"
                elif value:
                    masked[key] = "****"
                else:
                    masked[key] = ""
            else:
                masked[key] = value
        return masked

    def is_sensitive_key(self, key: str) -> bool:
        """Check if a key is considered sensitive.

        Args:
            key: Configuration key to check

        Returns:
            True if key is sensitive
        """
        return any(sensitive in key.upper() for sensitive in self.SENSITIVE_KEYS)

    def get_llm_config(self) -> Dict[str, str]:
        """Get LLM configuration with masked sensitive values.

        Returns:
            LLM configuration dictionary
        """
        config = self.read_config()
        llm_keys = {
            "LLM_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "LLM_BASE_URL",
            "LLM_PROVIDER",
            "LLM_MODEL",
            "LLM_TEMPERATURE",
            "LLM_MAX_TOKENS",
        }
        return self.mask_sensitive({k: v for k, v in config.items() if k in llm_keys})

    def get_email_config(self) -> Dict[str, str]:
        """Get email configuration with masked sensitive values.

        Returns:
            Email configuration dictionary
        """
        config = self.read_config()
        email_keys = {
            "EMAIL_ENABLED",
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USERNAME",
            "SMTP_PASSWORD",
            "SMTP_FROM_EMAIL",
            "RESEND_API_KEY",
        }
        return self.mask_sensitive({k: v for k, v in config.items() if k in email_keys})

    def _write_env_file(self, path: Path, config: Dict[str, str]) -> None:
        """Write configuration to .env file.

        Args:
            path: File path to write to
            config: Configuration dictionary
        """
        with open(path, "w", encoding="utf-8") as f:
            for key, value in sorted(config.items()):
                if value is not None:
                    f.write(f"{key}={value}\n")
