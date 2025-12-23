"""Cluster lifecycle tools."""

from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class RebootSchema(BaseModel):
    """Schema for reboot arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    mode: str = Field(default="default", description="Reboot mode: default, powercycle, force")


class RebootTool(TalosTool):
    """Reboot nodes."""

    name = "talos_reboot"
    description = "Reboot node(s)"
    args_schema = RebootSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = RebootSchema(**arguments)
        cmd = ["reboot", "-n", args.nodes]
        if args.mode != "default":
            cmd.extend(["--mode", args.mode])
        return await self.execute_talosctl(cmd)


class ShutdownSchema(BaseModel):
    """Schema for shutdown arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    force: bool = Field(default=False, description="Force shutdown")


class ShutdownTool(TalosTool):
    """Shutdown nodes."""

    name = "talos_shutdown"
    description = "Shutdown node(s)"
    args_schema = ShutdownSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ShutdownSchema(**arguments)
        cmd = ["shutdown", "-n", args.nodes]
        if args.force:
            cmd.append("--force")
        return await self.execute_talosctl(cmd)


class ResetSchema(BaseModel):
    """Schema for reset arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    reboot: bool = Field(default=False, description="Reboot after reset")
    system_labels_to_wipe: str = Field(
        default="", description="System labels to wipe"
    )
    graceful: bool = Field(default=True, description="Graceful reset")


class ResetTool(TalosTool):
    """Reset nodes."""

    name = "talos_reset"
    description = "Reset node(s) to maintenance mode or factory"
    args_schema = ResetSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ResetSchema(**arguments)
        cmd = ["reset", "-n", args.nodes]
        if args.reboot:
            cmd.append("--reboot")
        if args.system_labels_to_wipe:
            cmd.extend(["--system-labels-to-wipe", args.system_labels_to_wipe])
        if not args.graceful:
            cmd.extend(["--graceful=false"])
        return await self.execute_talosctl(cmd)


class UpgradeSchema(BaseModel):
    """Schema for upgrade arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    image: str = Field(description="Installer image to use")
    preserve: bool = Field(default=True, description="Preserve data")


class UpgradeTool(TalosTool):
    """Upgrade nodes."""

    name = "talos_upgrade"
    description = "Upgrade Talos on node(s)"
    args_schema = UpgradeSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = UpgradeSchema(**arguments)
        cmd = ["upgrade", "-n", args.nodes, "--image", args.image]
        if args.preserve:
            cmd.append("--preserve")
        return await self.execute_talosctl(cmd)


class ImageSchema(BaseModel):
    """Schema for image arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    cmd: str = Field(
        default="list",
        description="Command: list, pull, default, cache-create, cache-serve"
    )
    image: str = Field(default="", description="Image name (for pull/cache-create)")
    layout: str = Field(default="", description="Layout for cache commands (oci, flat)")
    platform: str = Field(default="", description="Platform for cache-create")


class ImageTool(TalosTool):
    """Manage images."""

    name = "talos_image"
    description = "Manage container images on Talos (new in 1.12)"
    args_schema = ImageSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ImageSchema(**arguments)

        base_cmd = ["image"]

        if args.cmd == "pull":
            if not args.image:
                return [TextContent(type="text", text="Image name required for pull")]
            base_cmd.extend(["pull", args.image])
        elif args.cmd == "default":
            base_cmd.append("default")
        elif args.cmd == "cache-create":
            if not args.image:
                return [TextContent(type="text", text="Image name required for cache-create")]
            base_cmd.extend(["cache-create", args.image])
            if args.layout:
                base_cmd.extend(["--layout", args.layout])
            if args.platform:
                base_cmd.extend(["--platform", args.platform])
        elif args.cmd == "cache-serve":
            base_cmd.append("cache-serve")
            if args.layout:
                base_cmd.extend(["--layout", args.layout])
        else:
            base_cmd.append("list")

        base_cmd.extend(["-n", args.nodes])

        return await self.execute_talosctl(base_cmd)
