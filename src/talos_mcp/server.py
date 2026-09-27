"""Talos MCP stdio server factory; each CLI invocation owns its runtime state."""

from typing import Any, cast

from mcp.server import Server
from mcp.types import CallToolResult, GetPromptResult, Prompt, Resource, ResourceTemplate, Tool
from pydantic import AnyUrl

from talos_mcp import __version__
from talos_mcp.core.client import TalosClient
from talos_mcp.handlers import MCPHandlers
from talos_mcp.prompts import TalosPrompts
from talos_mcp.registry import create_tool_registry
from talos_mcp.resources import TalosResources


def create_server(client: TalosClient) -> Server:
    """Build an independent MCP server with one pinned client and policy."""
    app = Server("talos-mcp-server", version=__version__)
    tools_list, tools_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), tools_list, tools_map)

    @cast("Any", app.list_resources)()
    async def list_resources() -> list[Resource]:
        """List enabled static resources."""
        return await handlers.list_resources()

    @cast("Any", app.list_resource_templates)()
    async def list_resource_templates() -> list[ResourceTemplate]:
        """List enabled node resource templates."""
        return await handlers.list_resource_templates()

    @cast("Any", app.read_resource)()
    async def read_resource(uri: AnyUrl) -> str | bytes:
        """Read a policy-gated Talos resource."""
        return await handlers.read_resource(uri)

    @cast("Any", app.list_prompts)()
    async def list_prompts() -> list[Prompt]:
        """List diagnostic prompts."""
        return await handlers.list_prompts()

    @cast("Any", app.get_prompt)()
    async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
        """Render a diagnostic prompt."""
        return await handlers.get_prompt(name, arguments)

    @cast("Any", app.list_tools)()
    async def list_tools() -> list[Tool]:
        """List enabled canonical tools."""
        return await handlers.list_tools()

    @app.call_tool(validate_input=False)
    async def call_tool(name: str, arguments: Any) -> CallToolResult:
        """Run a tool with explicit outcome and error status."""
        return await handlers.call_tool(name, arguments)

    return app


# Preserve the historical python -m entry point without creating runtime globals.
from talos_mcp.cli import cli  # noqa: E402


if __name__ == "__main__":
    cli()
