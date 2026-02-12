"""Talos Client module."""

import asyncio
import os
import shutil
from functools import lru_cache
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
            config_path
            or os.environ.get("TALOSCONFIG")
            or settings.talos_config_path
            or os.path.expanduser("~/.talos/config")
        )
        self.config: dict[str, Any] | None = None
        self.current_context: str | None = None
        self._config_mtime: float = 0
        self._load_config()

    def _load_config(self) -> None:
        """Load Talos configuration from file with caching based on mtime."""
        try:
            config_file = Path(self.config_path).expanduser().resolve()

            # Security: Validate path is within expected locations
            if not config_file.is_absolute():
                logger.warning(f"Config path is not absolute: {self.config_path}")

            if config_file.exists():
                # Security: Verify it's a regular file
                if not config_file.is_file():
                    logger.error(f"Config path is not a regular file: {config_file}")
                    return

                # Check if config has been modified since last load
                current_mtime = config_file.stat().st_mtime
                if self.config and current_mtime == self._config_mtime:
                    logger.debug("Using cached config (file unchanged)")
                    return

                # Security: Check file permissions (warn if world-readable)
                if os.name != "nt":  # Unix-like systems
                    stat_info = config_file.stat()
                    if stat_info.st_mode & 0o004:
                        logger.warning(
                            f"Talosconfig is world-readable: {config_file}. "
                            "Consider restricting permissions with: chmod 600"
                        )

                with config_file.open() as f:
                    self.config = yaml.safe_load(f)
                    self._config_mtime = current_mtime
                    if self.config:
                        self.current_context = self.config.get("context")
                        logger.info(f"Loaded Talos config with context: {self.current_context}")
                    # Clear the get_nodes cache when config changes
                    self._get_nodes_cached.cache_clear()
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

    @lru_cache(maxsize=1)
    def _get_nodes_cached(self, cache_key: float) -> list[str]:
        """Cached implementation of get_nodes.

        Args:
            cache_key: Timestamp used for cache invalidation (config mtime).

        Returns:
            List of node IPs/hostnames.
        """
        if not self.config or not self.current_context:
            return []

        contexts = self.config.get("contexts", {})
        context_data = contexts.get(self.current_context, {})

        nodes = context_data.get("nodes", [])
        if nodes:
            return nodes

        # Fallback to endpoints if nodes are not explicitly set
        # Endpoints might contain ports (e.g. 1.2.3.4:6443 or [::1]:6443)
        # Need to handle both IPv4:port and [IPv6]:port formats
        endpoints = context_data.get("endpoints", [])
        clean_nodes = []
        for ep in endpoints:
            # Handle [IPv6]:port format
            if ep.startswith("["):
                # Extract IPv6 address from [ipv6]:port format
                bracket_end = ep.find("]")
                if bracket_end != -1:
                    ep = ep[1:bracket_end]  # Remove brackets
                clean_nodes.append(ep)
            elif ":" in ep and ep.count(":") == 1:
                # IPv4:port format (only one colon)
                ep = ep.split(":")[0]
                clean_nodes.append(ep)
            else:
                # No port or IPv6 without brackets
                clean_nodes.append(ep)

        return clean_nodes

    def get_nodes(self) -> list[str]:
        """Get all nodes configured in the current context with caching.

        Returns:
            List of node IPs/hostnames.
        """
        # Use config mtime as cache key to invalidate when config changes
        return self._get_nodes_cached(self._config_mtime)

    async def health_check(self) -> dict[str, Any]:
        """Perform a health check by executing a lightweight talosctl command.

        Returns:
            Dictionary with health status information:
            - healthy: bool indicating if check passed
            - error: Error message if unhealthy (optional)
            - version: Brief version info if healthy (optional)
        """
        if not self.config:
            return {
                "healthy": False,
                "error": "No Talos configuration loaded",
            }

        try:
            # Use version command with short timeout as health check
            result = await self.execute_talosctl(["version", "--timeout", "5s"])
            stdout = result.get("stdout", "")

            # Extract version from output (first line typically contains it)
            version_line = stdout.split("\n")[0] if stdout else "Talos API reachable"

            return {
                "healthy": True,
                "version": version_line[:100],  # Truncate for brevity
            }
        except TalosCommandError as e:
            return {
                "healthy": False,
                "error": e.get_user_message(),
                "code": e.code.name,
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": f"Unexpected error during health check: {e!s}",
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
            logger.opt(exception=True).error(f"Error executing talosctl: {' '.join(cmd)}")
            # Wrap unknown errors in TalosCommandError for consistency
            raise TalosCommandError(cmd, 1, f"Execution failed: {e!s}")
