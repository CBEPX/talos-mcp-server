"""Base classes for Talos MCP tools."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations
from pydantic import BaseModel, ConfigDict

from talos_mcp.core.client import TalosClient
from talos_mcp.core.policy import OPERATIONS


class StrictSchema(BaseModel):
    """Forbid unknown MCP arguments at the protocol boundary."""

    model_config = ConfigDict(extra="forbid", strict=True)


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
            annotations=ToolAnnotations(
                readOnlyHint=OPERATIONS[self.name].kind == "READ",
                destructiveHint=self.name
                in {
                    "talos_apply_config",
                    "talos_machineconfig_patch",
                    "talos_reboot",
                    "talos_shutdown",
                    "talos_reset",
                    "talos_upgrade",
                },
                idempotentHint=OPERATIONS[self.name].kind == "READ",
                openWorldHint=OPERATIONS[self.name].authenticated,
            ),
        )

    @abstractmethod
    async def run(self, arguments: dict[str, Any]) -> list[TextContent] | CallToolResult:
        """Run the tool.

        Args:
            arguments: Tool arguments.

        Returns:
            List of TextContent results.
        """
        pass

    async def execute_talosctl(
        self, args: list[str], *, target_version: str | None = None
    ) -> list[TextContent]:
        """Helper to execute talosctl and return TextContent.

        Args:
            args: Arguments for talosctl.
            target_version: Declared target version for version-gated writes.

        Returns:
            Formatted TextContent.
        """
        try:
            result = await self.client.execute_talosctl(
                args, operation=self.name, target_version=target_version
            )
            output = result["stdout"]
            if result.get("warning"):
                output = f"{result['warning']}\n{output}"
            return [TextContent(type="text", text=f"```\n{output}\n```")]
        except Exception:
            raise

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
    """Compatibility base for existing read tools; responses are never cached."""

    cache_ttl: ClassVar[float] = 30.0  # Default TTL: 30 seconds

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Run the tool with caching.

        Args:
            arguments: Tool arguments.

        Returns:
            List of TextContent results (possibly cached).
        """
        return await self._run_impl(arguments)

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
    """Compatibility base for existing write tools; execution is serialized by client."""

    is_mutation: ClassVar[bool] = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Run the tool and invalidate cache.

        Args:
            arguments: Tool arguments.

        Returns:
            List of TextContent results.
        """
        return await self._run_impl(arguments)

    @abstractmethod
    async def _run_impl(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Actual tool implementation.

        Args:
            arguments: Tool arguments.

        Returns:
            List of TextContent results.
        """
        pass
