"""Cgroups tool for Talos Linux."""

from typing import Any, Literal

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class CgroupsSchema(BaseModel):
    """Schema for cgroups arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    action: Literal["list", "get", "kill"] = Field(
        default="list", description="Action: list, get, or kill"
    )
    cgroup: str | None = Field(default=None, description="Cgroup path (for get/kill actions)")


class CgroupsTool(TalosTool):
    """Tool for managing cgroups in Talos Linux (Talos 1.9+)."""

    name = "talos_cgroups"
    description = (
        "Manage cgroups in Talos Linux nodes. "
        "Allows listing cgroups, getting stats, and killing cgroups."
    )
    args_schema = CgroupsSchema
    is_mutation = True  # Supports 'kill' action

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        args = CgroupsSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        action = args.action

        if action == "kill":
            return [
                TextContent(
                    type="text",
                    text="Error: 'kill' action not supported by talosctl CLI.",
                )
            ]

        # talosctl cgroups (no subcommand for list/get)
        cmd = ["cgroups"]

        cmd.extend(["--nodes", nodes])

        # Handle backward compatibility with older talosctl versions
        try:
            return await self.execute_talosctl(cmd)
        except Exception as e:
            if "unknown command" in str(e).lower():
                return [
                    TextContent(
                        type="text",
                        text="Error: 'cgroups' command not found. "
                        "This feature requires Talos 1.9+ and compatible talosctl.",
                    )
                ]
            raise
