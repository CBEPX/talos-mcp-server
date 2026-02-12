"""Cluster lifecycle tools."""

from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import MutatingTool, TalosTool


class RebootSchema(BaseModel):
    """Schema for reboot arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    mode: str = Field(default="default", description="Reboot mode: default, powercycle, force")


class RebootTool(MutatingTool):
    """Reboot Talos nodes.

    Gracefully reboots the specified nodes. Use with caution as this
    will temporarily disrupt workloads running on the node.

    Reboot modes:
        - default: Standard reboot
        - powercycle: Power cycle the machine (hard reboot)
        - force: Force reboot even if node is not ready

    Examples:
        - Reboot single node: {"nodes": "192.168.1.10"}
        - Reboot multiple nodes: {"nodes": "192.168.1.10,192.168.1.11"}
        - Force reboot: {"nodes": "192.168.1.10", "mode": "force"}

    Common use cases:
        - Apply kernel updates
        - Recover from node hang
        - Rolling restart during maintenance window

    Warning: Ensure proper pod disruption budgets and replica counts
    to maintain service availability during reboots.
    """

    name = "talos_reboot"
    description = (
        "Reboot Talos node(s). Disrupts workloads; use with caution. "
        "Modes: default, powercycle, force. "
        "Example: {\"nodes\": \"192.168.1.10\"} or {\"nodes\": \"10.0.0.1,10.0.0.2\"}. "
        "Warning: Ensure pod disruption budgets are set to maintain availability."
    )
    args_schema = RebootSchema

    async def _run_impl(self, arguments: dict[str, Any]) -> list[TextContent]:
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


class ShutdownTool(MutatingTool):
    """Shutdown Talos nodes.

    Gracefully shuts down the specified nodes. Use with extreme caution
    as this will completely stop the node and require manual power-on
    or IPMI to restart.

    Examples:
        - Shutdown single node: {"nodes": "192.168.1.10"}
        - Force shutdown: {"nodes": "192.168.1.10", "force": true}

    Common use cases:
        - Planned maintenance with physical access
        - Power management in data center
        - Emergency shutdown

    Warning: Node will NOT automatically restart. Ensure you have
    physical access or IPMI to power the node back on.
    """

    name = "talos_shutdown"
    description = (
        "Shutdown Talos node(s). EXTREME CAUTION: node will not auto-restart. "
        "Requires physical access or IPMI to power back on. "
        "Example: {\"nodes\": \"192.168.1.10\"}. "
        "Use force=true for unresponsive nodes."
    )
    args_schema = ShutdownSchema

    async def _run_impl(self, arguments: dict[str, Any]) -> list[TextContent]:
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
    system_labels_to_wipe: str = Field(default="", description="System labels to wipe")
    graceful: bool = Field(default=True, description="Graceful reset")


class ResetTool(MutatingTool):
    """Reset nodes."""

    name = "talos_reset"
    description = "Reset node(s) to maintenance mode or factory"
    args_schema = ResetSchema

    async def _run_impl(self, arguments: dict[str, Any]) -> list[TextContent]:
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


class UpgradeTool(MutatingTool):
    """Upgrade Talos OS on nodes.

    Upgrades Talos to a new version using the specified installer image.
    This is a disruptive operation that will reboot the node.

    Image format: ghcr.io/siderolabs/installer:v<VERSION>
    Example images:
        - ghcr.io/siderolabs/installer:v1.12.0
        - ghcr.io/siderolabs/installer:v1.11.3

    Examples:
        - Upgrade single node: {
            "nodes": "192.168.1.10",
            "image": "ghcr.io/siderolabs/installer:v1.12.0"
          }
        - Upgrade without preserving data: {
            "nodes": "192.168.1.10",
            "image": "ghcr.io/siderolabs/installer:v1.12.0",
            "preserve": false
          }

    Common use cases:
        - Security patch application
        - Feature updates
        - Bug fix deployment

    Warning:
        - Node will reboot during upgrade
        - Ensure workloads can tolerate disruption
        - Test upgrade in staging environment first
        - Preserve=true (default) keeps ephemeral data
    """

    name = "talos_upgrade"
    description = (
        "Upgrade Talos OS on node(s). DISRUPTIVE: node will reboot. "
        "Image format: ghcr.io/siderolabs/installer:v<VERSION>. "
        "Example: {\"nodes\": \"192.168.1.10\", \"image\": \"ghcr.io/siderolabs/installer:v1.12.0\"}. "
        "Warning: Test in staging first. Use preserve=true (default) to keep data."
    )
    args_schema = UpgradeSchema

    async def _run_impl(self, arguments: dict[str, Any]) -> list[TextContent]:
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
        default="list", description="Command: list, pull, default, cache-create, cache-serve"
    )
    image: str = Field(default="", description="Image name (for pull/cache-create)")
    layout: str = Field(default="", description="Layout for cache commands (oci, flat)")
    platform: str = Field(default="", description="Platform for cache-create")


class ImageTool(TalosTool):
    """Manage images."""

    name = "talos_image"
    description = "Manage container images on Talos (new in 1.12)"
    args_schema = ImageSchema
    is_mutation = True

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


class BootstrapSchema(BaseModel):
    """Schema for bootstrap arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames (usually just one)")


class BootstrapTool(MutatingTool):
    """Bootstrap cluster."""

    name = "talos_bootstrap"
    description = "Bootstrap the etcd cluster on the specified node"
    args_schema = BootstrapSchema

    async def _run_impl(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = BootstrapSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)

        # Bootstrap typically targets a single node
        # If multiple are provided, we should probably warn or just pass them (talosctl warns)
        cmd = ["bootstrap", "-n", nodes]
        return await self.execute_talosctl(cmd)


class ClusterShowSchema(BaseModel):
    """Schema for cluster show arguments."""

    nodes: str | None = Field(
        default=None, description="Comma-separated list of node IPs/hostnames (optional filter)"
    )


class ClusterShowTool(TalosTool):
    """Show cluster status."""

    name = "talos_cluster_show"
    description = "High-level view of cluster members and their status"
    args_schema = ClusterShowSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ClusterShowSchema(**arguments)

        # cluster show doesn't require nodes usually (uses context)
        # but if nodes are provided, we can pass them
        cmd = ["cluster", "show"]
        if args.nodes:
            cmd.extend(["-n", args.nodes])

        return await self.execute_talosctl(cmd)
