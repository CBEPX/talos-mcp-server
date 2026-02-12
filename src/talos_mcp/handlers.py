"""MCP protocol handlers."""

from typing import Any

from loguru import logger
from mcp.types import (
    GetPromptResult,
    Prompt,
    Resource,
    ResourceTemplate,
    TextContent,
    Tool,
)
from pydantic import AnyUrl

from talos_mcp.core.settings import settings
from talos_mcp.prompts import TalosPrompts
from talos_mcp.resources import TalosResources
from talos_mcp.tools.base import TalosTool


class MCPHandlers:
    """Centralized MCP protocol handlers."""

    def __init__(
        self,
        prompts: TalosPrompts,
        resources: TalosResources,
        tools_list: list[TalosTool],
        tools_map: dict[str, TalosTool],
    ):
        """Initialize MCP handlers.

        Args:
            prompts: TalosPrompts instance.
            resources: TalosResources instance.
            tools_list: List of all available tools.
            tools_map: Dictionary mapping tool names to tool instances.
        """
        self.prompts = prompts
        self.resources = resources
        self.tools_list = tools_list
        self.tools_map = tools_map

    # Resource Handlers
    async def list_resources(self) -> list[Resource]:
        """List available resources.

        Returns:
            List of available resources.
        """
        return await self.resources.list_resources()

    async def list_resource_templates(self) -> list[ResourceTemplate]:
        """List available resource templates.

        Returns:
            List of resource templates.
        """
        return await self.resources.list_resource_templates()

    async def read_resource(self, uri: AnyUrl) -> str | bytes:
        """Read a resource.

        Args:
            uri: Resource URI to read.

        Returns:
            Resource content as string or bytes.
        """
        return await self.resources.read_resource(uri)

    # Prompt Handlers
    async def list_prompts(self) -> list[Prompt]:
        """List available prompts.

        Returns:
            List of available prompts.
        """
        return await self.prompts.list_prompts()

    async def get_prompt(
        self, name: str, arguments: dict[str, str] | None = None
    ) -> GetPromptResult:
        """Get a prompt by name.

        Args:
            name: Prompt name.
            arguments: Optional prompt arguments.

        Returns:
            Prompt result with messages.
        """
        messages = await self.prompts.get_prompt(name, arguments)
        return GetPromptResult(messages=messages)

    # Tool Handlers
    async def list_tools(self) -> list[Tool]:
        """List all available Talos tools.

        Returns:
            List of tool definitions.
        """
        return [tool.get_definition() for tool in self.tools_list]

    async def call_tool(self, name: str, arguments: Any) -> list[TextContent]:
        """Handle tool calls for Talos operations.

        Args:
            name: Tool name to execute.
            arguments: Tool arguments.

        Returns:
            List of TextContent results.
        """
        tool = self.tools_map.get(name)
        if not tool:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

        # Check if Talos config is available
        if not tool.client.config:
            return [
                TextContent(
                    type="text",
                    text=(
                        "Error: No Talos configuration found.\n\n"
                        "To use Talos MCP Server, you need:\n"
                        "1. A valid talosconfig file (usually at ~/.talos/config)\n"
                        "2. Set TALOSCONFIG environment variable to point to your config\n\n"
                        "To set up a new cluster:\n"
                        "  talosctl gen config <cluster-name> https://<control-plane-ip>:6443\n\n"
                        "For existing cluster:\n"
                        "  export TALOSCONFIG=/path/to/your/talosconfig"
                    ),
                )
            ]

        # Enforce read-only mode using is_mutation flag
        if settings.readonly and getattr(tool, "is_mutation", False):
            logger.warning(f"Blocked write operation in readonly mode: {name}")
            return [
                TextContent(
                    type="text",
                    text=f"Error: Tool '{name}' is blocked in read-only mode. "
                    "Set TALOS_MCP_READONLY=false or remove --readonly flag to enable.",
                )
            ]

        try:
            if not isinstance(arguments, dict):
                # Ensure arguments is a dict, MCP sometimes sends generic object?
                # Type hint says Any, but typically it's a dict.
                # If it's None, create empty dict.
                arguments = arguments or {}

            return await tool.run(arguments)
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return [TextContent(type="text", text=f"Error: {e!s}")]
