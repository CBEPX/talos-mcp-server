"""Bounded service and diagnostic tools."""

from typing import Any, Literal

from mcp.types import CallToolResult, TextContent
from pydantic import Field

from talos_mcp.tools.base import StrictSchema, TalosTool


class ServiceSchema(StrictSchema):
    """Read one service status, or list services when omitted."""

    nodes: str | None = None
    service: str | None = None


class ServiceTool(TalosTool):
    """Read service status only."""

    name = "talos_service"
    description = "Read service status. Use talos_service_action to start, stop, or restart."
    args_schema = ServiceSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = ServiceSchema(**arguments)
        cmd = ["service"]
        if args.service:
            cmd.append(args.service)
        cmd.extend(["-n", self.ensure_nodes(args.nodes)])
        return await self.execute_talosctl(cmd)


class ServiceActionSchema(StrictSchema):
    """One explicit service action on one node."""

    node: str
    service: str
    action: Literal["start", "stop", "restart"]


class ServiceActionTool(TalosTool):
    """Start, stop, or restart one service on one node."""

    name = "talos_service_action"
    description = "Mutate one service on one explicit node."
    args_schema = ServiceActionSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = ServiceActionSchema(**arguments)
        return await self.execute_talosctl(["service", args.service, args.action, "-n", args.node])


class LogsSchema(StrictSchema):
    """Finite service log snapshot."""

    nodes: str | None = None
    service: str
    lines: int = Field(default=100, ge=1, le=2000)


class LogsTool(TalosTool):
    """Read a finite service log snapshot."""

    name = "talos_logs"
    description = "Read 1..2000 past service log lines; streaming is unavailable."
    args_schema = LogsSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = LogsSchema(**arguments)
        return await self.execute_talosctl(
            ["logs", args.service, "-n", self.ensure_nodes(args.nodes), "--tail", str(args.lines)]
        )


class DmesgSchema(StrictSchema):
    """Finite kernel log snapshot."""

    nodes: str | None = None


class DmesgTool(TalosTool):
    """Read kernel logs once."""

    name = "talos_dmesg"
    description = "Read a bounded kernel log snapshot."
    args_schema = DmesgSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = DmesgSchema(**arguments)
        return await self.execute_talosctl(
            ["dmesg", "-n", self.ensure_nodes(args.nodes), "--follow=false"]
        )


class EventsSchema(StrictSchema):
    """Finite event observation with history or tail selection."""

    nodes: str | None = None
    tail: int | None = Field(default=None, ge=1, le=500)
    lookback_seconds: int | None = Field(default=None, ge=1, le=3600)
    window_seconds: int = Field(default=5, ge=1, le=30)


class EventsTool(TalosTool):
    """Observe Talos events for one short window."""

    name = "talos_events"
    description = "Observe events for 1..30 seconds with tail or history selection."
    args_schema = EventsSchema

    async def run(self, arguments: dict[str, Any]) -> CallToolResult:
        """Execute this Talos tool."""
        args = EventsSchema(**arguments)
        if (args.tail is None) == (args.lookback_seconds is None):
            raise ValueError("Exactly one of tail or lookback_seconds is required")
        cmd = ["events", "-n", self.ensure_nodes(args.nodes)]
        if args.tail is not None:
            cmd.extend(["--tail", str(args.tail)])
        else:
            cmd.extend(["--duration", f"{args.lookback_seconds}s"])
        result = await self.client.execute_talosctl(
            cmd, operation=self.name, observation_window=args.window_seconds
        )
        return CallToolResult(
            content=[TextContent(type="text", text=result["stdout"])],
            isError=False,
            structuredContent={
                "code": "OK",
                "outcome": "complete",
                "exit_code": 0,
                "complete": True,
                "truncated": False,
                "complete_window": result["complete_window"],
            },
        )
