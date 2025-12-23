"""Network tools."""

from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class InterfacesSchema(BaseModel):
    """Schema for interfaces arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")


class InterfacesTool(TalosTool):
    """List interfaces."""

    name = "talos_interfaces"
    description = "List network interfaces"
    args_schema = InterfacesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = InterfacesSchema(**arguments)
        # talosctl get links ?? Or specific command?
        # `talosctl get links` or `talosctl interfaces` (deprecated?)
        # Let's use `get addresses` which is common for "interfaces" alias in my analysis
        return await self.execute_talosctl(["get", "addresses", "-n", args.nodes])


class RoutesSchema(BaseModel):
    """Schema for routes arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")


class RoutesTool(TalosTool):
    """List routes."""

    name = "talos_routes"
    description = "List routing table"
    args_schema = RoutesSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = RoutesSchema(**arguments)
        cmd = ["get", "routes", "-n", args.nodes]
        return await self.execute_talosctl(cmd)


class NetstatSchema(BaseModel):
    """Schema for netstat arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")


class NetstatTool(TalosTool):
    """Netstat."""

    name = "talos_netstat"
    description = "List network connections"
    args_schema = NetstatSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = NetstatSchema(**arguments)
        cmd = ["netstat", "-n", args.nodes]
        return await self.execute_talosctl(cmd)


class PcapSchema(BaseModel):
    """Schema for pcap arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    interface: str = Field(description="Interface to capture on")
    duration: str = Field(default="10s", description="Duration to capture")


class PcapTool(TalosTool):
    """Paket capture."""

    name = "talos_pcap"
    description = "Capture packets (stub)"
    args_schema = PcapSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        _ = PcapSchema(**arguments)
        # Stub implementation as binary output handling is complex
        return [
            TextContent(
                type="text",
                text="Packet capture not fully implemented (requires binary streaming)",
            )
        ]
