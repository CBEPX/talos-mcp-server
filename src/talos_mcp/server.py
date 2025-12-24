"""Talos MCP Server."""

import asyncio
import sys
from typing import Any

import typer
import uvloop
from loguru import logger
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    Resource,
    ResourceTemplate,
    TextContent,
    Tool,
)
from pydantic import AnyUrl

from talos_mcp.core.client import TalosClient
from talos_mcp.core.settings import settings
from talos_mcp.prompts import TalosPrompts
from talos_mcp.resources import TalosResources
from talos_mcp.tools.cluster import (
    BootstrapTool,
    ClusterShowTool,
    ImageTool,
    RebootTool,
    ResetTool,
    ShutdownTool,
    UpgradeTool,
)
from talos_mcp.tools.config import (
    ApplyConfigTool,
    ApplyTool,
    ConfigInfoTool,
    GenConfigTool,
    GetKubeconfigTool,
    MachineConfigPatchTool,
    PatchTool,
    ValidateConfigTool,
)
from talos_mcp.tools.etcd import (
    EtcdAlarmTool,
    EtcdDefragTool,
    EtcdMembersTool,
    EtcdSnapshotTool,
)
from talos_mcp.tools.files import (
    CopyTool,
    DiskUsageTool,
    ListFilesTool,
    MountsTool,
    ReadFileTool,
)
from talos_mcp.tools.network import (
    InterfacesTool,
    NetstatTool,
    PcapTool,
    RoutesTool,
)
from talos_mcp.tools.resources import (
    GetKernelParamStatusTool,
    GetResourceTool,
    GetVolumeStatusTool,
    ListDefinitionsTool,
)
from talos_mcp.tools.services import (
    DmesgTool,
    EventsTool,
    LogsTool,
    ServiceTool,
)
from talos_mcp.tools.system import (
    DashboardTool,
    DevicesTool,
    DisksTool,
    GetContainersTool,
    GetHealthTool,
    GetProcessesTool,
    GetStatsTool,
    GetVersionTool,
    MemoryTool,
    TimeTool,
)


# Configure logging
def configure_logging() -> None:
    """Configure logging with detailed formatting and auditing.
    
    Uses settings from Settings class for all configuration.
    """
    logger.remove()  # Remove default handler

    # Standard stderr logging
    logger.add(
        sys.stderr,
        format=settings.log_format,
        level=settings.log_level.upper(),
    )

    # Audit log to file
    logger.add(
        settings.audit_log_path,
        rotation=settings.audit_log_rotation,
        retention=settings.audit_log_retention,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message} | {extra}",
        serialize=settings.audit_log_serialize,
    )



# Initialize the MCP server
app_mcp = Server("talos-mcp-server")
talos_client = TalosClient()
talos_resources = TalosResources(talos_client)
talos_prompts = TalosPrompts(talos_client)


# Register Resources Handlers
@app_mcp.list_resources()  # type: ignore
async def list_resources() -> list[Resource]:
    """List available resources."""
    return await talos_resources.list_resources()


@app_mcp.list_resource_templates()  # type: ignore
async def list_resource_templates() -> list[ResourceTemplate]:
    """List available resource templates."""
    return await talos_resources.list_resource_templates()


@app_mcp.read_resource()  # type: ignore
async def read_resource(uri: AnyUrl) -> str | bytes:
    """Read a resource."""
    return await talos_resources.read_resource(uri)


# Register Prompts Handlers
@app_mcp.list_prompts()  # type: ignore
async def list_prompts() -> list[Prompt]:
    """List available prompts."""
    return await talos_prompts.list_prompts()


@app_mcp.get_prompt()  # type: ignore
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
    """Get a prompt by name."""
    messages = await talos_prompts.get_prompt(name, arguments)
    return GetPromptResult(messages=messages)

# Register tools
tools_list = [
    # System
    GetVersionTool(talos_client),
    GetHealthTool(talos_client),
    GetStatsTool(talos_client),
    GetContainersTool(talos_client),
    GetProcessesTool(talos_client),
    DashboardTool(talos_client),
    MemoryTool(talos_client),
    TimeTool(talos_client),
    DisksTool(talos_client),
    DevicesTool(talos_client),
    # Files
    ListFilesTool(talos_client),
    ReadFileTool(talos_client),
    CopyTool(talos_client),
    DiskUsageTool(talos_client),
    MountsTool(talos_client),
    # Network
    InterfacesTool(talos_client),
    RoutesTool(talos_client),
    NetstatTool(talos_client),
    PcapTool(talos_client),
    # Services
    ServiceTool(talos_client),
    LogsTool(talos_client),
    DmesgTool(talos_client),
    EventsTool(talos_client),
    # Cluster
    RebootTool(talos_client),
    ShutdownTool(talos_client),
    ResetTool(talos_client),
    UpgradeTool(talos_client),
    ImageTool(talos_client),
    BootstrapTool(talos_client),
    ClusterShowTool(talos_client),
    # Etcd
    EtcdMembersTool(talos_client),
    EtcdSnapshotTool(talos_client),
    EtcdAlarmTool(talos_client),
    EtcdDefragTool(talos_client),
    # Config
    ConfigInfoTool(talos_client),
    GetKubeconfigTool(talos_client),
    ApplyConfigTool(talos_client),
    ApplyTool(talos_client),
    ValidateConfigTool(talos_client),
    PatchTool(talos_client),
    MachineConfigPatchTool(talos_client),
    GenConfigTool(talos_client),
    # Resources
    GetResourceTool(talos_client),
    ListDefinitionsTool(talos_client),
    GetVolumeStatusTool(talos_client),
    GetKernelParamStatusTool(talos_client),
]

tools_map = {tool.name: tool for tool in tools_list}

# Tools that perform write/mutating operations
WRITE_TOOLS = {
    "talos_reboot",
    "talos_shutdown",
    "talos_reset",
    "talos_upgrade",
    "talos_apply_config",
    "talos_apply",
    "talos_patch",
    "talos_machineconfig_patch",
    "talos_bootstrap",
    "talos_etcd_defrag",
    "talos_etcd_alarm",
    "talos_cp",
}


@app_mcp.list_tools()  # type: ignore
async def list_tools() -> list[Tool]:
    """List all available Talos tools."""
    return [tool.get_definition() for tool in tools_list]


@app_mcp.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls for Talos operations."""
    # Enforce read-only mode
    if settings.readonly and name in WRITE_TOOLS:
        return [
            TextContent(
                type="text",
                text=f"Error: Tool '{name}' is blocked in read-only mode. "
                "Set TALOS_MCP_READONLY=false or remove --readonly flag to enable.",
            )
        ]

    tool = tools_map.get(name)
    if not tool:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

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



cli = typer.Typer()


@cli.command()
def main(
    log_level: str = typer.Option(
        settings.log_level, help="Log level (DEBUG, INFO, WARNING, ERROR)"
    ),
    audit_log: str = typer.Option(
        settings.audit_log_path, help="Path to audit log file"
    ),
    readonly: bool = typer.Option(
        settings.readonly, help="Enable read-only mode (prevents mutating commands)"
    ),
) -> None:
    """Run the Talos MCP Server."""
    # Update global settings from CLI args
    settings.log_level = log_level
    settings.audit_log_path = audit_log
    settings.readonly = readonly

    configure_logging()
    uvloop.install()
    logger.info(f"Starting Talos MCP Server with log level {settings.log_level}")

    async def run_server() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await app_mcp.run(read_stream, write_stream, app_mcp.create_initialization_options())

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception(f"Server crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
