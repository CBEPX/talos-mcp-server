"""Volumes tool for Talos Linux."""

from typing import Any, Dict, List

from mcp.types import TextContent

from talos_mcp.tools.base import TalosTool


class VolumesTool(TalosTool):
    """Tool for managing user volumes in Talos Linux (Talos 1.12+)."""

    name = "talos_volumes"
    description = "Manage user volumes in Talos Linux nodes (Talos 1.12+). Allows listing, getting status, and unmounting volumes."
    is_mutation = True  # Supports 'unmount' action

    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "string",
                    "description": "Comma-separated list of node IPs or hostnames to target",
                },
                "action": {
                    "type": "string",
                    "description": "Action to perform: list, status, unmount",
                    "enum": ["list", "status", "unmount"],
                    "default": "list",
                },
                "volume": {
                    "type": "string",
                    "description": "Volume name (required for unmount, optional for status)",
                },
            },
            "required": ["nodes"],
        }

    async def run(self, arguments: Dict[str, Any]) -> List[TextContent]:
        nodes = self.ensure_nodes(arguments.get("nodes"))
        action = arguments.get("action", "list")
        volume = arguments.get("volume")

        cmd = ["volumes", action]
        if volume:
            cmd.append(volume)
        
        cmd.extend(["--nodes", nodes])

        return await self.execute_talosctl(cmd)
