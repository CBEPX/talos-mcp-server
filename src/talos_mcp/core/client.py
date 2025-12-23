"""Talos Client module."""

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any

import arrow
import yaml
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from talos_mcp.core.exceptions import TalosCommandError
from talos_mcp.core.settings import settings


class TalosClient:
    """Client for interacting with Talos Linux API."""

    def __init__(self, config_path: str | None = None) -> None:
        """Initialize Talos client with configuration.

        Args:
            config_path: Path to talosconfig file. Defaults to ~/.talos/config.
        """
        self.config_path = (
            config_path or settings.talos_config_path or os.path.expanduser("~/.talos/config")
        )
        self.config: dict[str, Any] | None = None
        self.current_context: str | None = None
        self._load_config()

    def _load_config(self) -> None:
        """Load Talos configuration from file."""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with config_file.open() as f:
                    self.config = yaml.safe_load(f)
                    if self.config:
                        self.current_context = self.config.get("context")
                        logger.info(f"Loaded Talos config with context: {self.current_context}")
            else:
                logger.warning(f"Talos config not found at {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading Talos config: {e}")

    def get_context_info(self) -> dict[str, Any]:
        """Get information about the current context.

        Returns:
            Dictionary with context information or error.
        """
        if not self.config or not self.current_context:
            return {"error": "No Talos configuration loaded"}

        contexts = self.config.get("contexts", {})
        context_data = contexts.get(self.current_context, {})

        return {
            "context": self.current_context,
            "target": context_data.get("target"),
            "endpoints": context_data.get("endpoints", []),
            "nodes": context_data.get("nodes", []),
            "config_path": self.config_path,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
        retry=retry_if_exception_type(
            (OSError, TimeoutError)
        ),  # Only retry on system/network errors, not command failures
    )
    async def execute_talosctl(self, args: list[str]) -> dict[str, str]:
        """Execute talosctl command and return the output.

        Args:
            args: List of arguments for talosctl.

        Returns:
            Dictionary containing stdout and stderr.

        Raises:
            TalosCommandError: If the command fails.
        """
        talosctl_path = shutil.which("talosctl")
        if not talosctl_path:
            raise TalosCommandError(["talosctl"], 127, "talosctl not found in PATH")

        cmd = [talosctl_path, *args]

        # Add config file if it exists
        if Path(self.config_path).exists():
            cmd.extend(["--talosconfig", self.config_path])

        # Check for read-only mode via settings
        if settings.readonly:
            # Basic protection using simple string matching
            unsafe_commands = [
                "upgrade",
                "reset",
                "reboot",
                "shutdown",
                "apply-config",
                "bootstrap",
                "defrag",
            ]
            if any(cmd_part in args for cmd_part in unsafe_commands):
                 raise TalosCommandError(cmd, 1, "Operation not permitted in read-only mode")

        start_time = arrow.now()
        logger.debug(f"Executing: {' '.join(cmd)} at {start_time.format()}")

        try:
            logger.debug(f"Executing command: {' '.join(cmd)}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()
            duration = arrow.now() - start_time

            logger.debug(f"Command finished in {duration.total_seconds():.2f}s")

            if process.returncode != 0:
                logger.error(
                    f"Command failed with code {process.returncode}\n"
                    f"Cmd: {' '.join(cmd)}\n"
                    f"Stderr: {stderr_str}"
                )
                raise TalosCommandError(cmd, process.returncode, stderr_str)
            else:
                logger.debug(f"Command success: {' '.join(cmd)}")

            return {
                "stdout": stdout_str,
                "stderr": stderr_str,
            }

        except TalosCommandError:
            raise
        except Exception as e:
            # Tenacity will handle retries for specific exceptions,
            # but if we exhaust them or hit others:
            logger.opt(exception=True).error(
                f"Error executing talosctl: {' '.join(cmd)}"
            )
            # Wrap unknown errors in TalosCommandError for consistency
            raise TalosCommandError(cmd, 1, f"Execution failed: {str(e)}")
