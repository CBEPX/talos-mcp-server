"""Application settings."""

import os
import tempfile

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_prefix="TALOS_MCP_")

    log_level: str = Field(default="INFO", description="Logging level")
    audit_log_path: str = Field(
        default_factory=lambda: os.path.join(tempfile.gettempdir(), "talos_mcp_audit.log"),
        description="Audit log file path"
    )
    talos_config_path: str | None = Field(default=None, description="Path to talosconfig")
    readonly: bool = Field(default=False, description="Read-only mode")


settings = Settings()
