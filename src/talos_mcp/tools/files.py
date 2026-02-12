"""File management tools."""

from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class ListFilesSchema(BaseModel):
    """Schema for list files arguments."""

    nodes: str | None = Field(
        default=None,
        description="Comma-separated list of node IPs/hostnames. Defaults to all nodes if not provided.",
    )
    path: str = Field(default="/", description="Directory path")


class ListFilesTool(TalosTool):
    """List files and directories on Talos nodes.

    Browse the read-only root filesystem of Talos nodes.
    Note: Talos has an immutable filesystem; most paths are read-only.

    Examples:
        - List root directory: {}
        - List specific path: {"path": "/etc"}
        - List on specific node: {"path": "/", "nodes": "192.168.1.10"}

    Common paths to explore:
        - /etc: Configuration files
        - /usr/local/etc: Local configuration
        - /var/log: Log files (if persisted)
    """

    name = "talos_ls"
    description = (
        "List files and directories on Talos nodes. "
        "Browse the immutable root filesystem. "
        "Example: {\"path\": \"/etc\"} to list config files. "
        "Note: Most paths are read-only due to Talos immutability."
    )
    args_schema = ListFilesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ListFilesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        cmd = ["ls", args.path, "-n", nodes]
        return await self.execute_talosctl(cmd)


class ReadFileSchema(BaseModel):
    """Schema for read file arguments."""

    nodes: str | None = Field(
        default=None,
        description="Comma-separated list of node IPs/hostnames. Defaults to all nodes if not provided.",
    )
    path: str = Field(description="File path to read")


class ReadFileTool(TalosTool):
    """Read a file."""

    name = "talos_cat"
    description = "Read file content"
    args_schema = ReadFileSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ReadFileSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        cmd = ["read", args.path, "-n", nodes]
        return await self.execute_talosctl(cmd)


class CopySchema(BaseModel):
    """Schema for copy arguments."""

    # Copying to/from multiple nodes is complex. `talosctl cp` might not support it for download.
    # Upload to multiple nodes works.
    # Let's support it, but behavior depends on talosctl.
    nodes: str | None = Field(
        default=None,
        description="Comma-separated list of node IPs/hostnames. Defaults to all nodes if not provided.",
    )
    src: str = Field(description="Source path")
    dst: str = Field(description="Destination path")
    direction: str = Field(
        default="download",
        description="Direction: upload (local->node) or download (node->local)",
    )


class CopyTool(TalosTool):
    """Copy files."""

    name = "talos_cp"
    description = "Copy files to/from node"
    args_schema = CopySchema
    is_mutation = True  # Can upload files to node

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = CopySchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)

        # talosctl cp requires -n <node> even if the target is specified as <node>:<path>
        # to ensure it knows which context/auth to use for that node IP.

        if args.direction == "upload":
            cmd = ["cp", args.src, f"{nodes}:{args.dst}"]
        else:
            cmd = ["cp", f"{nodes}:{args.src}", args.dst]

        cmd.extend(["-n", nodes])

        return await self.execute_talosctl(cmd)


class DiskUsageSchema(BaseModel):
    """Schema for disk usage arguments."""

    nodes: str | None = Field(
        default=None,
        description="Comma-separated list of node IPs/hostnames. Defaults to all nodes if not provided.",
    )
    path: str = Field(default="/", description="Path to check")


class DiskUsageTool(TalosTool):
    """Check disk usage on Talos nodes.

    Shows disk space usage for the specified path.
    Useful for monitoring ephemeral storage and persistent volumes.

    Examples:
        - Check root usage: {}
        - Check specific path: {"path": "/var"}
        - Check on specific node: {"nodes": "192.168.1.10"}

    Common use cases:
        - Monitor ephemeral storage consumption
        - Check persistent volume usage
        - Troubleshoot disk space issues
    """

    name = "talos_du"
    description = (
        "Check disk usage on Talos nodes. "
        "Monitor ephemeral storage and persistent volume space. "
        "Example: {\"path\": \"/var\"} to check usage. "
        "Use for storage monitoring and troubleshooting."
    )
    args_schema = DiskUsageSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = DiskUsageSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        cmd = ["usage", args.path, "-n", nodes]
        return await self.execute_talosctl(cmd)


class MountsSchema(BaseModel):
    """Schema for mounts arguments."""

    nodes: str | None = Field(
        default=None,
        description="Comma-separated list of node IPs/hostnames. Defaults to all nodes if not provided.",
    )


class MountsTool(TalosTool):
    """List mounts."""

    name = "talos_mounts"
    description = "List mount points"
    args_schema = MountsSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = MountsSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        cmd = ["mounts", "-n", nodes]
        return await self.execute_talosctl(cmd)
