"""System information tools."""

from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class NodesSchema(BaseModel):
    """Schema for node arguments."""

    nodes: str | None = Field(default=None, description="Comma-separated list of node IPs/hostnames. Defaults to all nodes if not provided.")


class GetVersionTool(TalosTool):
    """Get version."""

    name = "talos_version"
    description = "Get Talos Linux version information from nodes"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        return await self.execute_talosctl(["version", "-n", nodes])


class GetHealthTool(TalosTool):
    """Get health."""

    name = "talos_health"
    description = "Check health status of Talos cluster"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        
        # talosctl health does not support multiple nodes.
        # It's a cluster-wide check, so we just pick the first node as the endpoint.
        node_list = nodes.split(",")
        target_node = node_list[0]
        
        return await self.execute_talosctl(["health", "-n", target_node])


class GetStatsTool(TalosTool):
    """Get stats."""

    name = "talos_stats"
    description = "Get container stats (CPU/Memory usage) from nodes"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        return await self.execute_talosctl(["stats", "-n", nodes])


class GetContainersTool(TalosTool):
    """Get containers."""

    name = "talos_containers"
    description = "List containers running on the node"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        return await self.execute_talosctl(["containers", "-n", nodes])


class GetProcessesTool(TalosTool):
    """Get processes."""

    name = "talos_processes"
    description = "List processes running on the node"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        return await self.execute_talosctl(["processes", "-n", nodes])


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
        nodes = self.ensure_nodes(args.nodes)
        return await self.execute_talosctl(["memory", "-n", nodes])


class TimeTool(TalosTool):
    """Get time."""

    name = "talos_time"
    description = "Get system time"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        return await self.execute_talosctl(["time", "-n", nodes])


class DisksTool(TalosTool):
    """Get disks."""

    name = "talos_disks"
    description = "List disk drives and their properties"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        return await self.execute_talosctl(["get", "disks", "-n", nodes])


class DevicesTool(TalosTool):
    """Get devices (PCI, USB, etc)."""

    name = "talos_devices"
    description = "List hardware devices (PCI, USB, System) via resource definitions"
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        return await self.execute_talosctl(["get", "devices", "-n", nodes])

