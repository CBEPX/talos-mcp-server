"""Etcd management tools."""

from typing import Any, Literal

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class EtcdMembersSchema(BaseModel):
    """Schema for etcd members arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")


class EtcdMembersTool(TalosTool):
    """Etcd members."""

    name = "talos_etcd_members"
    description = "List etcd members"
    args_schema = EtcdMembersSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = EtcdMembersSchema(**arguments)
        cmd = ["etcd", "members", "-n", args.nodes]
        return await self.execute_talosctl(cmd)


class EtcdSnapshotSchema(BaseModel):
    """Schema for etcd snapshot arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    path: str = Field(
        default="/tmp/etcd.snapshot",  # noqa: S108
        description="Path to save snapshot locally",
    )


class EtcdSnapshotTool(TalosTool):
    """Etcd snapshot."""

    name = "talos_etcd_snapshot"
    description = "Take an etcd snapshot"
    args_schema = EtcdSnapshotSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = EtcdSnapshotSchema(**arguments)
        cmd = ["etcd", "snapshot", args.path, "-n", args.nodes]
        return await self.execute_talosctl(cmd)


class EtcdAlarmSchema(BaseModel):
    """Schema for etcd alarm arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    action: Literal["list", "disarm"] = Field(default="list", description="Action: list, disarm")


class EtcdAlarmTool(TalosTool):
    """Etcd alarms."""

    name = "talos_etcd_alarm"
    description = "List or disarm etcd alarms"
    args_schema = EtcdAlarmSchema
    is_mutation = True  # Can disarm alarms

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = EtcdAlarmSchema(**arguments)
        cmd = ["etcd", "alarm", args.action, "-n", args.nodes]
        return await self.execute_talosctl(cmd)


class EtcdDefragSchema(BaseModel):
    """Schema for etcd defrag arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")


class EtcdDefragTool(TalosTool):
    """Etcd defrag."""

    name = "talos_etcd_defrag"
    description = "Defragment etcd member"
    args_schema = EtcdDefragSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = EtcdDefragSchema(**arguments)
        cmd = ["etcd", "defrag", "-n", args.nodes]
        return await self.execute_talosctl(cmd)
