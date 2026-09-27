"""Policy-gated Talos MCP resources."""

import json
from typing import cast

from mcp.types import Resource, ResourceTemplate
from pydantic import AnyUrl

from talos_mcp.core.client import TalosClient, TalosExecutionError


RESOURCE_TO_TOOL = {
    "version": "talos_version",
    "health": "talos_health",
    "config": "talos_config_info",
}


class TalosResources:
    """Expose only resources backed by enabled canonical tools."""

    def __init__(self, client: TalosClient) -> None:
        """Store the policy-gated client for resource reads."""
        self.client = client

    async def list_resources(self) -> list[Resource]:
        """Return static resources; node resources are templates."""
        return []

    async def list_resource_templates(self) -> list[ResourceTemplate]:
        """List the enabled node resource templates."""
        return [
            ResourceTemplate(
                uriTemplate=f"talos://{{node}}/{kind}",
                name=f"Talos {kind}",
                description=f"Read {kind} through {tool}",
                mimeType="text/plain",
            )
            for kind, tool in RESOURCE_TO_TOOL.items()
            if self.client.enabled(tool)
        ]

    async def read_resource(self, uri: AnyUrl) -> str:
        """Read an enabled resource through its canonical operation."""
        if uri.scheme != "talos" or not uri.host or not uri.path:
            raise ValueError("INVALID_ARGUMENT")
        kind = uri.path.strip("/")
        tool = RESOURCE_TO_TOOL.get(kind)
        if not tool:
            raise ValueError("UNKNOWN_RESOURCE")
        if not self.client.enabled(tool):
            raise TalosExecutionError("TOOL_NOT_ENABLED")
        if kind == "config":
            return json.dumps(self.client.get_context_info())
        node = f"{uri.host}:{uri.port}" if uri.port is not None else uri.host
        command = [kind, "-n", node]
        if kind == "health":
            command.extend(["--wait-timeout", f"{max(1, int(self.client.timeout * 0.75))}s"])
        result = await self.client.execute_talosctl(command, operation=tool)
        return cast("str", result["stdout"])
