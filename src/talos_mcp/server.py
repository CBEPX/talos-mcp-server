"""Talos MCP Server."""

import asyncio
import signal
import sys
from typing import Any

import typer
import anyio
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


# New tools moved from new_features
from talos_mcp.tools.cgroups import CgroupsTool
from talos_mcp.tools.volumes import VolumesTool
from talos_mcp.tools.support import SupportTool
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

# Initialize Talos client
# Try to load config from defaults if not provided
talos_client = TalosClient(config_path=settings.talos_config_path)

# Initialize prompts
talos_prompts = TalosPrompts(talos_client)

# Initialize resources
talos_resources = TalosResources(talos_client)  # type: ignore


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
    # New Features (Talos 1.12+)
    CgroupsTool(talos_client),
    VolumesTool(talos_client),
    SupportTool(talos_client),
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
    # New Write Tools
    "talos_cgroups",  # has kill action
    "talos_volumes",  # has unmount action
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


__version__ = "0.4.0"


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        typer.echo(f"talos-mcp-server {__version__}")
        raise typer.Exit()


cli = typer.Typer()


@cli.command()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", callback=version_callback, is_eager=True,
        help="Show version and exit"
    ),
    log_level: str = typer.Option(
        "INFO", "--log-level", "-l", help="Log level (DEBUG, INFO, WARNING, ERROR)",
        envvar="TALOS_MCP_LOG_LEVEL"
    ),
    audit_log: str = typer.Option(
        None, "--audit-log", help="Path to audit log file",
        envvar="TALOS_MCP_AUDIT_LOG_PATH"
    ),
    readonly: bool = typer.Option(
        False, "--readonly", help="Enable read-only mode (prevents mutating commands)",
        envvar="TALOS_MCP_READONLY"
    ),
) -> None:
    """Run the Talos MCP Server."""
    # Update global settings from CLI args
    settings.log_level = log_level
    if audit_log:
        settings.audit_log_path = audit_log
    settings.readonly = readonly

    configure_logging()
    uvloop.install()
    logger.info(f"Starting Talos MCP Server with log level {settings.log_level}")

    # Hint for users running interactively
    if sys.stdin.isatty():
        sys.stderr.write(
            "\n⚠️  This server expects JSON-RPC input from MCP clients (e.g., Claude Desktop).\n"
            "    Press Ctrl+C to exit.\n\n"
        )

    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        """Handle shutdown signals gracefully."""
        logger.info("Received shutdown signal, stopping server...")
        shutdown_event.set()

    # List of tools that modify state
    WRITE_TOOLS = {
        "talos_reboot", "talos_shutdown", "talos_reset", "talos_upgrade",
        "talos_apply_config", "talos_apply", "talos_patch", "talos_machineconfig_patch",
        "talos_bootstrap", "talos_etcd_defrag", "talos_etcd_alarm", "talos_cp",
        "talos_image_pull", "talos_image_default", "talos_image_create_cache"
    }

    # Intercept tool calls to check for readonly mode
    original_call_tool = app_mcp.call_tool

    @app_mcp.call_tool()
    async def call_tool_wrapper(name: str, arguments: Any) -> list[TextContent]:
        tool = tools_map.get(name)
        
        # Robust Read-Only Check: Check the tool's is_mutation flag
        if settings.readonly:
            # Check explicit flag on the tool instance/class
            if tool and getattr(tool, "is_mutation", False):
                logger.warning(f"Blocked write operation in readonly mode: {name}")
                return [TextContent(type="text", text=f"Error: Tool '{name}' is blocked in read-only mode.")]
            
            # Fallback: Check safety list (Legacy support/Double check)
            if name in WRITE_TOOLS:
                logger.warning(f"Blocked write operation in readonly mode (legacy set): {name}")
                return [TextContent(type="text", text=f"Error: Tool '{name}' is blocked in read-only mode.")]

        return await original_call_tool(name, arguments)

    async def run_server() -> None:
        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

        try:
            async with stdio_server() as (read_stream, write_stream):
                # Run server with shutdown monitoring
                server_task = asyncio.create_task(
                    app_mcp.run(read_stream, write_stream, app_mcp.create_initialization_options())
                )
                shutdown_task = asyncio.create_task(shutdown_event.wait())

                done, pending = await asyncio.wait(
                    [server_task, shutdown_task],
                    return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                logger.info("Server stopped by user")
        finally:
            # Cleanup signal handlers
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass  # Already handled by signal handler
    except BaseException as e:
        # Handle ExceptionGroup (Python 3.11+) or regular exceptions
        # Filter out BrokenResourceError which is expected during shutdown
        if isinstance(e, anyio.BrokenResourceError):
            pass  # Expected during shutdown
        elif hasattr(e, 'exceptions'):
            # ExceptionGroup-like: filter out BrokenResourceError
            real_errors = [
                exc for exc in e.exceptions 
                if not isinstance(exc, anyio.BrokenResourceError)
            ]
            if real_errors:
                logger.exception(f"Server crashed: {e}")
                sys.exit(1)
        elif not isinstance(e, (SystemExit, KeyboardInterrupt)):
            logger.exception(f"Server crashed: {e}")
            sys.exit(1)


if __name__ == "__main__":
    cli()
