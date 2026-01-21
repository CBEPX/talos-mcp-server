"""Talos MCP Server - Core initialization.

This module initializes the MCP server and registers all handlers.
For CLI functionality, see talos_mcp.cli module.
"""

from typing import Any

from mcp.server import Server
from mcp.types import (
    GetPromptResult,
    Prompt,
    Resource,
    ResourceTemplate,
    TextContent,
    Tool,
)
from pydantic import AnyUrl

# Backwards compatibility - re-export from cli module
from talos_mcp.cli import __version__, cli, main  # noqa: F401
from talos_mcp.core.client import TalosClient
from talos_mcp.core.settings import settings
from talos_mcp.handlers import MCPHandlers
from talos_mcp.prompts import TalosPrompts
from talos_mcp.registry import create_tool_registry
from talos_mcp.resources import TalosResources


# Initialize the MCP server
app_mcp = Server("talos-mcp-server")

# Initialize Talos client
# Try to load config from defaults if not provided
talos_client = TalosClient(config_path=settings.talos_config_path)

# Initialize prompts
talos_prompts = TalosPrompts(talos_client)

# Initialize resources
talos_resources = TalosResources(talos_client)  # type: ignore

# Register tools using registry
tools_list, tools_map = create_tool_registry(talos_client)

# Initialize handlers
mcp_handlers = MCPHandlers(talos_prompts, talos_resources, tools_list, tools_map)


# Register MCP protocol handlers
@app_mcp.list_resources()  # type: ignore
async def list_resources() -> list[Resource]:
    """List available resources."""
    return await mcp_handlers.list_resources()


@app_mcp.list_resource_templates()  # type: ignore
async def list_resource_templates() -> list[ResourceTemplate]:
    """List available resource templates."""
    return await mcp_handlers.list_resource_templates()


@app_mcp.read_resource()  # type: ignore
async def read_resource(uri: AnyUrl) -> str | bytes:
    """Read a resource."""
    return await mcp_handlers.read_resource(uri)


@app_mcp.list_prompts()  # type: ignore
async def list_prompts() -> list[Prompt]:
    """List available prompts."""
    return await mcp_handlers.list_prompts()


@app_mcp.get_prompt()  # type: ignore
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
    """Get a prompt by name."""
    return await mcp_handlers.get_prompt(name, arguments)


@app_mcp.list_tools()  # type: ignore
async def list_tools() -> list[Tool]:
    """List all available Talos tools."""
    return await mcp_handlers.list_tools()


@app_mcp.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls for Talos operations."""
    return await mcp_handlers.call_tool(name, arguments)


if __name__ == "__main__":
    cli()
