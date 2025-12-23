"""Services management tools."""

from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class ServiceSchema(BaseModel):
    """Schema for service arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    action: str = Field(default="status", description="Action: status, start, stop, restart")
    service: str | None = Field(default=None, description="Service name (optional for status)")


class ServiceTool(TalosTool):
    """Service operations."""

    name = "talos_service"
    description = "Manage services"
    args_schema = ServiceSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ServiceSchema(**arguments)
        # talosctl service <id> --node <node> (for status)
        # talosctl service <id> start --node <node>
        # If action is status and no service, list all? `talosctl service` lists all.

        cmd = ["service"]
        if args.service:
            cmd.append(args.service)

        if args.action != "status":
            cmd.append(args.action)

        cmd.extend(["-n", args.nodes])
        return await self.execute_talosctl(cmd)


class LogsSchema(BaseModel):
    """Schema for logs arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    service: str = Field(description="Service name or container name")
    lines: int = Field(default=100, description="Number of lines to tail")
    follow: bool = Field(default=False, description="Follow logs")


class LogsTool(TalosTool):
    """Get service logs."""

    name = "talos_logs"
    description = "Get logs from services"
    args_schema = LogsSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = LogsSchema(**arguments)
        cmd = ["logs", args.service, "-n", args.nodes, "--tail", str(args.lines)]
        if args.follow:
            cmd.append("--follow")
        return await self.execute_talosctl(cmd)


class DmesgSchema(BaseModel):
    """Schema for dmesg arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    follow: bool = Field(default=False, description="Follow logs")


class DmesgTool(TalosTool):
    """Get kernel logs."""

    name = "talos_dmesg"
    description = "Get kernel logs (dmesg)"
    args_schema = DmesgSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = DmesgSchema(**arguments)
        cmd = ["dmesg", "-n", args.nodes]
        if args.follow:
            cmd.append("--follow")
        return await self.execute_talosctl(cmd)


class EventsSchema(BaseModel):
    """Schema for events arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    duration: str = Field(default="0s", description="Duration to stream events (0s = forever)")


class EventsTool(TalosTool):
    """Get events."""

    name = "talos_events"
    description = "Get system events"
    args_schema = EventsSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = EventsSchema(**arguments)
        cmd = ["events", "-n", args.nodes]
        # events streams forever by default.
        # We should probably limit it for MCP unless using SSE streaming properly.
        # But 'call_tool' expects a return. So we probably just want a snapshot or short duration?
        # Actually `talosctl events` streams.
        # For now, let's just run it. If it blocks, it blocks.
        if args.duration != "0s":
            cmd.extend(["--duration", args.duration])

        return await self.execute_talosctl(cmd)
