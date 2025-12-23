"""File management tools."""

from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class ListFilesSchema(BaseModel):
    """Schema for list files arguments."""

    nodes: str | None = Field(default=None, description="Comma-separated list of node IPs/hostnames. Defaults to all nodes if not provided.")
    path: str = Field(default="/", description="Directory path")


class ListFilesTool(TalosTool):
    """List files on a node."""

    name = "talos_ls"
    description = "List files and directories"
    args_schema = ListFilesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ListFilesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        cmd = ["ls", args.path, "-n", nodes]
        return await self.execute_talosctl(cmd)


class ReadFileSchema(BaseModel):
    """Schema for read file arguments."""

    nodes: str | None = Field(default=None, description="Comma-separated list of node IPs/hostnames. Defaults to all nodes if not provided.")
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
    nodes: str | None = Field(default=None, description="Comma-separated list of node IPs/hostnames. Defaults to all nodes if not provided.")
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

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = CopySchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        if args.direction == "upload":
            cmd = ["cp", args.src, f"{nodes}:{args.dst}"]
        else:
            # Downloading from multiple nodes to same local path might overwrite?
            # talosctl might handle it (e.g. creating dirs per node).
            # But let's assume user knows what they are doing.
            cmd = ["cp", f"{nodes}:{args.src}", args.dst]

        return await self.execute_talosctl(cmd)


class DiskUsageSchema(BaseModel):
    """Schema for disk usage arguments."""

    nodes: str | None = Field(default=None, description="Comma-separated list of node IPs/hostnames. Defaults to all nodes if not provided.")
    path: str = Field(default="/", description="Path to check")


class DiskUsageTool(TalosTool):
    """Disk Usage."""

    name = "talos_du"
    description = "Check disk usage"
    args_schema = DiskUsageSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = DiskUsageSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        cmd = ["usage", args.path, "-n", nodes]
        return await self.execute_talosctl(cmd)


class MountsSchema(BaseModel):
    """Schema for mounts arguments."""

    nodes: str | None = Field(default=None, description="Comma-separated list of node IPs/hostnames. Defaults to all nodes if not provided.")


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
