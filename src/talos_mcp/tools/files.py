"""File management tools."""

from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class ListFilesSchema(BaseModel):
    """Schema for list files arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    path: str = Field(default="/", description="Directory path")


class ListFilesTool(TalosTool):
    """List files on a node."""

    name = "talos_ls"
    description = "List files and directories"
    args_schema = ListFilesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ListFilesSchema(**arguments)
        cmd = ["ls", args.path, "-n", args.nodes]
        return await self.execute_talosctl(cmd)


class ReadFileSchema(BaseModel):
    """Schema for read file arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    path: str = Field(description="File path to read")


class ReadFileTool(TalosTool):
    """Read a file."""

    name = "talos_cat"
    description = "Read file content"
    args_schema = ReadFileSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ReadFileSchema(**arguments)
        cmd = ["read", args.path, "-n", args.nodes]
        return await self.execute_talosctl(cmd)


class CopySchema(BaseModel):
    """Schema for copy arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
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
        if args.direction == "upload":
            cmd = ["cp", args.src, f"{args.nodes}:{args.dst}"]
        else:
            cmd = ["cp", f"{args.nodes}:{args.src}", args.dst]

        return await self.execute_talosctl(cmd)


class DiskUsageSchema(BaseModel):
    """Schema for disk usage arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    path: str = Field(default="/", description="Path to check")


class DiskUsageTool(TalosTool):
    """Disk Usage."""

    name = "talos_du"
    description = "Check disk usage"
    args_schema = DiskUsageSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = DiskUsageSchema(**arguments)
        cmd = ["usage", args.path, "-n", args.nodes]
        return await self.execute_talosctl(cmd)


class MountsSchema(BaseModel):
    """Schema for mounts arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")


class MountsTool(TalosTool):
    """List mounts."""

    name = "talos_mounts"
    description = "List mount points"
    args_schema = MountsSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = MountsSchema(**arguments)
        cmd = ["mounts", "-n", args.nodes]
        return await self.execute_talosctl(cmd)
