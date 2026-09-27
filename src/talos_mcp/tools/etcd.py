"""Etcd read, write, and artifact operations."""

import json
import shutil
from typing import Any

from mcp.types import TextContent
from pydantic import Field

from talos_mcp.tools.base import StrictSchema, TalosTool


class EtcdNodeSchema(StrictSchema):
    """One explicit etcd node."""

    node: str = Field(min_length=1)


class EtcdMembersTool(TalosTool):
    """List etcd members."""

    name = "talos_etcd_members"
    description = "List etcd members from one node."
    args_schema = EtcdNodeSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = EtcdNodeSchema(**arguments)
        return await self.execute_talosctl(["etcd", "members", "-n", args.node])


class EtcdAlarmTool(TalosTool):
    """List etcd alarms."""

    name = "talos_etcd_alarm"
    description = "List etcd alarms; use talos_etcd_alarm_disarm to disarm."
    args_schema = EtcdNodeSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = EtcdNodeSchema(**arguments)
        return await self.execute_talosctl(["etcd", "alarm", "list", "-n", args.node])


class EtcdAlarmDisarmTool(TalosTool):
    """Disarm etcd alarms on one node."""

    name = "talos_etcd_alarm_disarm"
    description = "Disarm etcd alarms on one explicit node."
    args_schema = EtcdNodeSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = EtcdNodeSchema(**arguments)
        return await self.execute_talosctl(["etcd", "alarm", "disarm", "-n", args.node])


class EtcdDefragTool(TalosTool):
    """Defragment one etcd member."""

    name = "talos_etcd_defrag"
    description = "Defragment etcd on one explicit node."
    args_schema = EtcdNodeSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = EtcdNodeSchema(**arguments)
        return await self.execute_talosctl(["etcd", "defrag", "-n", args.node])


class EtcdSnapshotTool(TalosTool):
    """Download one etcd snapshot into a private artifact."""

    name = "talos_etcd_snapshot"
    description = "Save a single-node etcd snapshot in a unique private artifact."
    args_schema = EtcdNodeSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = EtcdNodeSchema(**arguments)
        directory = self.client.new_artifact_dir()
        path = directory / "snapshot.db"
        try:
            await self.client.execute_talosctl(
                ["etcd", "snapshot", str(path), "-n", args.node], operation=self.name
            )
            return [TextContent(type="text", text=json.dumps(self.client.artifact_metadata(path)))]
        except BaseException:
            shutil.rmtree(directory)
            raise
