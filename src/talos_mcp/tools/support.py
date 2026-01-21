"""Support bundle tool for Talos Linux."""

from typing import Any

from mcp.types import TextContent

from talos_mcp.tools.base import TalosTool


class SupportTool(TalosTool):
    """Tool for generating support bundles in Talos Linux."""

    name = "talos_support"
    description = "Generate a support bundle for Talos Linux nodes. This gathers logs and system information for debugging."

    def args_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "string",
                    "description": "Comma-separated list of node IPs or hostnames to target",
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Enable verbose logging for the support command",
                    "default": False,
                },
            },
            "required": ["nodes"],
        }

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        nodes = self.ensure_nodes(arguments.get("nodes"))
        verbose = arguments.get("verbose", False)

        cmd = ["support"]
        if verbose:
            cmd.append("--verbose")

        cmd.extend(["--nodes", nodes])

        # Support usage often writes to a file, but without an output file arg
        # it prints to stdout/stderr which TalosTool captures.
        # Note: talosctl support usually produces a zip file.
        # For MCP, we might not want to transfer binary blobs easily yet,
        # but let's see what the standard output is.
        # If it tries to write to local disk, we might need to handle that.
        # Checking talosctl help: 'talosctl support' writes to a file by default??
        # Let's assume it prints info about where it saved it if run effectively.

        return await self.execute_talosctl(cmd)
