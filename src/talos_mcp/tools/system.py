"""System information tools."""

from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class NodesSchema(BaseModel):
    """Schema for node arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")


class GetVersionTool(TalosTool):
    """Get version."""

    name = "talos_version"
    description = "Get Talos Linux version information from nodes"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        return await self.execute_talosctl(["version", "-n", args.nodes])


class GetHealthTool(TalosTool):
    """Get health."""

    name = "talos_health"
    description = "Check health status of Talos cluster"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        return await self.execute_talosctl(["health", "-n", args.nodes])


class GetStatsTool(TalosTool):
    """Get stats."""

    name = "talos_stats"
    description = "Get container stats (CPU/Memory usage) from nodes"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        return await self.execute_talosctl(["stats", "-n", args.nodes])


class GetContainersTool(TalosTool):
    """Get containers."""

    name = "talos_containers"
    description = "List containers running on the node"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        return await self.execute_talosctl(["containers", "-n", args.nodes])


class GetProcessesTool(TalosTool):
    """Get processes."""

    name = "talos_processes"
    description = "List processes running on the node"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        return await self.execute_talosctl(["processes", "-n", args.nodes])


class DashboardTool(TalosTool):
    """Get dashboard."""

    name = "talos_dashboard"
    description = "Get a snapshot of the Talos dashboard"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        # Dashboard is interactive TUI. We can't really pipe it well unless we use specific flags.
        # It is not supported via MCP.
        # Actually `talosctl dashboard` is TUI.
        return [TextContent(type="text", text="Dashboard is a TUI and cannot be rendered in MCP.")]


class MemoryTool(TalosTool):
    """Get memory."""

    name = "talos_memory"
    description = "Get memory usage details"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        return await self.execute_talosctl(["memory", "-n", args.nodes])


class TimeTool(TalosTool):
    """Get time."""

    name = "talos_time"
    description = "Get system time"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        return await self.execute_talosctl(["time", "-n", args.nodes])
