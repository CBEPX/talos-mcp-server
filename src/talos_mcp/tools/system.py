"""System information tools."""

from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import CachedTool, TalosTool


class NodesSchema(BaseModel):
    """Schema for node arguments."""

    nodes: str | None = Field(
        default=None,
        description="Comma-separated list of node IPs/hostnames. Defaults to all nodes if not provided.",
    )


class GetVersionTool(CachedTool):
    """Get Talos Linux version information.

    Returns version information for Talos OS, Kubernetes, and containerd.
    Useful for verifying cluster version consistency.

    Examples:
        - Get version from all nodes: {}
        - Get version from specific node: {"nodes": "192.168.1.10"}

    Common use cases:
        - Check if all nodes run the same Talos version
        - Verify Kubernetes version after upgrade
        - Audit cluster for version compliance
    """

    name = "talos_version"
    description = (
        "Get Talos Linux version information from nodes. "
        "Returns Talos OS version, Kubernetes version, and containerd version. "
        "Use to verify cluster version consistency after upgrades or for auditing. "
        "Example: {} for all nodes, or {\"nodes\": \"192.168.1.10\"} for specific node."
    )
    args_schema = NodesSchema
    cache_ttl = 300.0  # Cache for 5 minutes (version rarely changes)

    async def _run_impl(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        return await self.execute_talosctl(["version", "-n", nodes])


class GetHealthTool(TalosTool):
    """Check cluster health status.

    Performs comprehensive health checks including:
    - API server availability
    - etcd cluster health
    - Kubernetes components status
    - Node readiness

    Note: This is a cluster-wide check that uses the first available node
    as the endpoint. It does not check individual node health.

    Examples:
        - Check overall cluster health: {}
        - Use specific node as health endpoint: {"nodes": "192.168.1.10"}

    Common use cases:
        - Verify cluster is ready after bootstrap
        - Check health before performing maintenance
        - Monitor cluster recovery after node failure
    """

    name = "talos_health"
    description = (
        "Check health status of Talos cluster. "
        "Verifies API server, etcd, Kubernetes components, and node readiness. "
        "Note: Uses first available node as endpoint (cluster-wide check). "
        "Example: {} for cluster health, or {\"nodes\": \"192.168.1.10\"} for specific endpoint."
    )
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
    """Get container resource usage statistics.

    Returns CPU and memory usage for running containers across nodes.
    Useful for capacity planning and resource optimization.

    Examples:
        - Get stats from all nodes: {}
        - Get stats from specific node: {"nodes": "192.168.1.10"}

    Common use cases:
        - Identify resource-hungry containers
        - Monitor resource utilization trends
        - Capacity planning for cluster scaling
        - Troubleshoot OOM (Out of Memory) issues
    """

    name = "talos_stats"
    description = (
        "Get container stats (CPU/Memory usage) from nodes. "
        "Shows resource consumption of running containers. "
        "Use for capacity planning and identifying resource bottlenecks. "
        "Example: {} for all nodes, or {\"nodes\": \"192.168.1.10\"} for specific node."
    )
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
    """Dashboard (Not available in MCP).

    Note: The Talos dashboard is an interactive TUI (Terminal User Interface)
    that cannot be rendered through the MCP protocol. Use other tools like
    `talos_stats`, `talos_memory`, or `talos_processes` to get resource
    information in text format.

    Alternative tools:
        - talos_stats: Container CPU/Memory usage
        - talos_memory: System memory details
        - talos_processes: Running processes
        - talos_dmesg: Kernel logs
    """

    name = "talos_dashboard"
    description = (
        "Note: Dashboard is an interactive TUI and cannot be rendered in MCP. "
        "Use talos_stats, talos_memory, or talos_processes instead for resource information."
    )
    args_schema = NodesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        # Dashboard is interactive TUI. We can't really pipe it well unless we use specific flags.
        # It is not supported via MCP.
        # Actually `talosctl dashboard` is TUI.
        return [
            TextContent(
                type="text",
                text=(
                    "The Talos dashboard is an interactive TUI and cannot be rendered through MCP.\n\n"
                    "Alternative tools for monitoring:\n"
                    "- talos_stats: Container CPU/Memory usage\n"
                    "- talos_memory: System memory details\n"
                    "- talos_processes: Running processes\n"
                    "- talos_dmesg: Kernel logs"
                ),
            )
        ]


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


class DisksTool(CachedTool):
    """Get disks."""

    name = "talos_disks"
    description = "List disk drives and their properties"
    args_schema = NodesSchema
    cache_ttl = 60.0  # Cache for 1 minute (disk config rarely changes)

    async def _run_impl(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        return await self.execute_talosctl(["get", "disks", "-n", nodes])


class DevicesTool(CachedTool):
    """Get devices (PCI, USB, etc)."""

    name = "talos_devices"
    description = "List hardware devices (PCI, USB, System) via resource definitions"
    args_schema = NodesSchema
    cache_ttl = 60.0  # Cache for 1 minute (hardware rarely changes)

    async def _run_impl(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NodesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        return await self.execute_talosctl(["get", "devices", "-n", nodes])
