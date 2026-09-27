"""Read-only cgroup diagnostics."""

from typing import Any, Literal

from mcp.types import TextContent

from talos_mcp.tools.base import StrictSchema, TalosTool


class CgroupsSchema(StrictSchema):
    """Read cgroups from explicit node selection."""

    nodes: str
    preset: Literal["cpu", "cpuset", "io", "memory", "process", "psi", "swap"] = "cpu"


class CgroupsTool(TalosTool):
    """Read the native cgroups diagnostic output."""

    name = "talos_cgroups"
    description = "List cgroup diagnostics; process kill and schema overrides are unavailable."
    args_schema = CgroupsSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = CgroupsSchema(**arguments)
        return await self.execute_talosctl(
            ["cgroups", "--nodes", args.nodes, "--preset", args.preset]
        )
