"""Etcd management tools."""

from typing import Any, Literal

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class EtcdMembersSchema(BaseModel):
    """Schema for etcd members arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")


class EtcdMembersTool(TalosTool):
    """List etcd cluster members.

    Shows all etcd members with their ID, status, and peer URLs.
    Useful for verifying cluster membership and leader status.

    Examples:
        - List members from control plane: {"nodes": "192.168.1.10"}

    Common use cases:
        - Verify etcd cluster membership
        - Check which node is the leader
        - Troubleshoot etcd connectivity issues

    Required permissions: etcd:read (reader role)
    """

    name = "talos_etcd_members"
    description = (
        "List etcd cluster members with ID, status, and peer URLs. "
        "Use to verify cluster membership and identify the leader. "
        "Example: {\"nodes\": \"192.168.1.10\"} (use control plane node). "
        "Required: etcd:read permission."
    )
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
    """Create etcd backup snapshot.

    Creates a point-in-time snapshot of the etcd database for backup
    and disaster recovery purposes. The snapshot is saved to the specified
    path on the local machine (where MCP server runs).

    Examples:
        - Create snapshot: {"nodes": "192.168.1.10", "path": "/backup/etcd-$(date +%Y%m%d).db"}
        - Use default path: {"nodes": "192.168.1.10"}

    Common use cases:
        - Scheduled backups before upgrades
        - Pre-migration backups
        - Disaster recovery preparation

    Required permissions: etcd:backup (admin role)
    Note: Snapshot is taken from the specified node; ensure it's a control plane node.
    """

    name = "talos_etcd_snapshot"
    description = (
        "Create etcd backup snapshot for disaster recovery. "
        "Saves point-in-time backup to specified local path. "
        "Example: {\"nodes\": \"192.168.1.10\", \"path\": \"/backup/etcd.db\"}. "
        "Required: etcd:backup permission. Use control plane node."
    )
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
