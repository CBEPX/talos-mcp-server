"""Base classes for Talos MCP tools."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from mcp.types import TextContent, Tool
from pydantic import BaseModel

from talos_mcp.core.cache import get_cache
from talos_mcp.core.client import TalosClient
from talos_mcp.core.exceptions import TalosCommandError


class TalosTool(ABC):
    """Base class for all Talos MCP tools."""

    name: ClassVar[str]
    description: ClassVar[str]
    args_schema: ClassVar[type[BaseModel]]  # Renamed from input_schema to be explicit
    is_mutation: ClassVar[bool] = False  # Set to True for tools that modify state

    def __init__(self, client: TalosClient) -> None:
        """Initialize the tool.

        Args:
            client: The TalosClient instance.
        """
        self.client = client

    def get_definition(self) -> Tool:
        """Get the MCP Tool definition.

        Returns:
            The Tool object.
        """
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.args_schema.model_json_schema(),
        )

    @abstractmethod
    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Run the tool.

        Args:
            arguments: Tool arguments.

        Returns:
            List of TextContent results.
        """
        pass

    async def execute_talosctl(self, args: list[str]) -> list[TextContent]:
        """Helper to execute talosctl and return TextContent.

        Args:
            args: Arguments for talosctl.

        Returns:
            Formatted TextContent.
        """
        try:
            result = await self.client.execute_talosctl(args)
            output = result["stdout"]
            if result.get("stderr"):
                if output:
                    output += "\n\n"
                output += result["stderr"]
            return [TextContent(type="text", text=f"```\n{output}\n```")]
        except TalosCommandError as e:
            # Use user-friendly message with technical details
            user_msg = e.get_user_message()
            return [TextContent(type="text", text=f"Error executing {self.name}:\n{user_msg}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error executing {self.name}:\n{e!s}")]

    def ensure_nodes(self, nodes: str | None) -> str:
        """Helper to ensure nodes are set, defaulting to all cluster nodes if None.

        Args:
            nodes: The provided nodes argument (comma-separated list or None).

        Returns:
            Comma-separated list of nodes.
        """
        if not nodes or nodes.lower() in ("all", "cluster"):
            all_nodes = self.client.get_nodes()
            return ",".join(all_nodes)
        return nodes


class CachedTool(TalosTool):
    """Base class for tools that support result caching.

    Cached tools store their results for a configurable TTL to avoid
    repeated expensive operations. This is suitable for read-only tools
    that return stable data (like version, health, stats).

    Subclasses should override `cache_ttl` to set the desired TTL.
    """

    cache_ttl: ClassVar[float] = 30.0  # Default TTL: 30 seconds

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Run the tool with caching.

        Args:
            arguments: Tool arguments.

        Returns:
            List of TextContent results (possibly cached).
        """
        cache = get_cache()

        # Try to get from cache
        cached_result = await cache.get(self.name, arguments, self.cache_ttl)
        if cached_result is not None:
            return cached_result

        # Execute and cache
        result = await self._run_impl(arguments)

        # Don't cache error results
        should_cache = True
        if result and isinstance(result[0], TextContent):
            text = result[0].text
            if text.startswith("Error") or "failed" in text.lower():
                should_cache = False

        if should_cache:
            await cache.set(self.name, arguments, result)

        return result

    @abstractmethod
    async def _run_impl(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Actual tool implementation.

        Args:
            arguments: Tool arguments.

        Returns:
            List of TextContent results.
        """
        pass


class MutatingTool(TalosTool):
    """Base class for tools that modify state.

    Mutating tools automatically invalidate the cache after successful
    execution to ensure read-only tools return fresh data.
    """

    is_mutation: ClassVar[bool] = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Run the tool and invalidate cache.

        Args:
            arguments: Tool arguments.

        Returns:
            List of TextContent results.
        """
        # Execute the tool
        result = await self._run_impl(arguments)

        # Invalidate cache after mutation
        cache = get_cache()
        await cache.invalidate_all()

        return result

    @abstractmethod
    async def _run_impl(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Actual tool implementation.

        Args:
            arguments: Tool arguments.

        Returns:
            List of TextContent results.
        """
        pass
