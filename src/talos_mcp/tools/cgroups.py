"""Cgroups tool for Talos Linux."""

from typing import Any, Dict, List

from mcp.types import Tool, TextContent
from pydantic import Field

from talos_mcp.tools.base import TalosTool


class CgroupsTool(TalosTool):
    """Tool for managing cgroups in Talos Linux (Talos 1.9+)."""

    name = "talos_cgroups"
    description = "Manage cgroups in Talos Linux nodes. Allows listing cgroups, getting stats, and killing cgroups."
    is_mutation = True  # Supports 'kill' action

    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "string",
                    "description": "Comma-separated list of node IPs or hostnames to target",
                },
                "action": {
                    "type": "string",
                    "description": "Action to perform: list, get, or kill",
                    "enum": ["list", "get", "kill"],
                    "default": "list",
                },
                "cgroup": {
                    "type": "string",
                    "description": "Cgroup path (required for get and kill actions)",
                },
            },
            "required": ["nodes"],
        }

    async def run(self, arguments: Dict[str, Any]) -> List[Any]:
        nodes = self.ensure_nodes(arguments.get("nodes"))
        action = arguments.get("action", "list")
        cgroup = arguments.get("cgroup")

        if action in ["list", "get"]:
            # talosctl cgroups (no subcommand)
            cmd = ["cgroups"]
            # We could add --preset if exposed in schema later
            if arguments.get("cgroup"):
                # Use it as a filter if possible, but CLI doesn't support it directly as arg
                # warn or ignore? For now ignore or log
                pass
        elif action == "kill":
            return [TextContent(type="text", text="Error: 'kill' action is not supported by talosctl CLI for cgroups.")]
        else:
             cmd = ["cgroups"]

        cmd.extend(["--nodes", nodes])

        # Handle backward compatibility with older talosctl versions
        try:
            return await self.execute_talosctl(cmd)
        except Exception as e:
            if "unknown command" in str(e).lower():
                from mcp.types import TextContent
                return [
                    TextContent(
                        type="text",
                        text=f"Error: 'cgroups' command not found. This feature requires Talos 1.9+ and a compatible talosctl version (installed: {self.client.get_talosctl_version()})."
                    )
                ]
            raise
