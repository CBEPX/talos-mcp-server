"""Volumes tool for Talos Linux."""

from typing import Any, Literal

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class VolumesSchema(BaseModel):
    """Schema for volumes arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    action: Literal["list", "status", "unmount"] = Field(
        default="list", description="Action: list, status, unmount"
    )
    volume: str | None = Field(default=None, description="Volume name (for unmount/status)")


class VolumesTool(TalosTool):
    """Tool for managing user volumes in Talos Linux (Talos 1.12+)."""

    name = "talos_volumes"
    description = (
        "Manage user volumes in Talos Linux nodes (Talos 1.12+). "
        "Allows listing, getting status, and unmounting volumes."
    )
    args_schema = VolumesSchema
    is_mutation = True  # Supports 'unmount' action

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        args = VolumesSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        action = args.action
        volume = args.volume

        cmd = ["volumes", action]
        if volume:
            cmd.append(volume)

        cmd.extend(["--nodes", nodes])

        return await self.execute_talosctl(cmd)
