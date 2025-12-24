"""Application settings."""

import os
import tempfile

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.
    
    All settings can be configured via environment variables with TALOS_MCP_ prefix.
    Example: TALOS_MCP_LOG_LEVEL=DEBUG
    """

    model_config = SettingsConfigDict(env_prefix="TALOS_MCP_")

    # Core settings
    talos_config_path: str | None = Field(default=None, description="Path to talosconfig")
    readonly: bool = Field(default=False, description="Read-only mode")

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR)")
    log_format: str = Field(
        default=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        description="Log format for console output"
    )

    # Audit log settings
    audit_log_path: str = Field(
        default_factory=lambda: os.path.join(tempfile.gettempdir(), "talos_mcp_audit.log"),
        description="Audit log file path"
    )
    audit_log_rotation: str = Field(default="10 MB", description="Audit log rotation size")
    audit_log_retention: str = Field(default="10 days", description="Audit log retention period")
    audit_log_serialize: bool = Field(default=True, description="Serialize audit logs as JSON")


settings = Settings()
