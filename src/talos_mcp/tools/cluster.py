"""Explicit single-node Talos lifecycle and image tools."""

import re
from typing import Any, Literal

from mcp.types import TextContent
from pydantic import Field, model_validator

from talos_mcp.core.client import TalosExecutionError
from talos_mcp.tools.base import StrictSchema, TalosTool


class NodeSchema(StrictSchema):
    """One explicit node for a disruptive operation."""

    node: str = Field(min_length=1)

    @model_validator(mode="after")
    def single_node(self) -> "NodeSchema":
        """Refuse implicit or fan-out targets."""
        if (
            self.node.lower() in {"all", "cluster", "default"}
            or "," in self.node
            or self.node.startswith("-")
            or "\x00" in self.node
        ):
            raise ValueError("one explicit node is required")
        return self


class RebootTool(TalosTool):
    """Request graceful reboot of one Talos node."""

    name = "talos_reboot"
    description = "Reboot one explicit node; accepted does not prove node recovery."
    args_schema = NodeSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = NodeSchema(**arguments)
        return await self.execute_talosctl(["reboot", "-n", args.node, "--wait=false"])


class ShutdownTool(TalosTool):
    """Request graceful shutdown of one Talos node."""

    name = "talos_shutdown"
    description = "Shut down one explicit node; external power-on is required."
    args_schema = NodeSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = NodeSchema(**arguments)
        return await self.execute_talosctl(["shutdown", "-n", args.node, "--wait=false"])


class ResetSchema(NodeSchema):
    """Constrained reset of named system partitions."""

    wipe_labels: list[Literal["STATE", "EPHEMERAL"]] = Field(min_length=1)


class ResetTool(TalosTool):
    """Reset one node with explicit wipe labels and graceful reboot."""

    name = "talos_reset"
    description = "Reset one explicit node; requires STATE and/or EPHEMERAL wipe labels."
    args_schema = ResetSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = ResetSchema(**arguments)
        return await self.execute_talosctl(
            [
                "reset",
                "-n",
                args.node,
                "--system-labels-to-wipe",
                ",".join(args.wipe_labels),
                "--graceful=true",
                "--reboot=true",
                "--wait=false",
            ]
        )


class UpgradeSchema(NodeSchema):
    """Digest-pinned installer request with declared target version."""

    target_version: str
    image: str
    schematic_id: str | None = None

    @model_validator(mode="after")
    def qualified_image(self) -> "UpgradeSchema":
        """Require supported target, sha256 digest and factory schematic identity."""
        match = re.fullmatch(r"v?(1\.(?:13|14)\.\d+)", self.target_version)
        if not match or not re.fullmatch(r"[^\s@]+@sha256:[a-fA-F0-9]{64}", self.image):
            raise ValueError("supported version and digest-pinned image required")
        reference = self.image.split("@", 1)[0]
        image_name = reference.rsplit("/", 1)[-1]
        if ":" in image_name and image_name.rsplit(":", 1)[1] != f"v{match.group(1)}":
            raise ValueError("image tag must match target_version when present")
        if reference.startswith("factory.talos.dev/"):
            factory_path = reference.removeprefix("factory.talos.dev/").split("/")
            schematic_segment = factory_path[-1].split(":", 1)[0]
            if (
                len(factory_path) != 2
                or not factory_path[0].endswith("-installer")
                or not self.schematic_id
                or not re.fullmatch(r"[a-fA-F0-9]{64}", self.schematic_id)
                or schematic_segment != self.schematic_id
            ):
                raise ValueError("factory schematic_id must match exact image path segment")
        elif self.schematic_id:
            raise ValueError("schematic_id requires a factory image")
        return self


class UpgradeTool(TalosTool):
    """Track one drain-enabled Talos upgrade within the bounded call deadline."""

    name = "talos_upgrade"
    description = (
        "Upgrade one explicit node with a digest-pinned image; "
        "read back version and health afterward."
    )
    args_schema = UpgradeSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = UpgradeSchema(**arguments)
        return await self.execute_talosctl(
            ["upgrade", "-n", args.node, "--image", args.image, "--wait=true", "--drain=true"],
            target_version=args.target_version,
        )


class ImageSchema(StrictSchema):
    """Read image list for one node."""

    node: str
    namespace: Literal["system", "cri", "inmem", "taloscontainers"] = "cri"


class ImageTool(TalosTool):
    """List images on one node."""

    name = "talos_image"
    description = "List node images; use talos_image_pull to pull one image."
    args_schema = ImageSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = ImageSchema(**arguments)
        if args.namespace == "taloscontainers" and await self.client.client_minor() != "1.14":
            raise TalosExecutionError("UNSUPPORTED_CAPABILITY")
        return await self.execute_talosctl(
            ["image", "list", "--namespace", args.namespace, "-n", args.node]
        )


class ImagePullSchema(NodeSchema):
    """Pull one named image."""

    image: str = Field(min_length=1)
    namespace: Literal["system", "cri", "inmem", "taloscontainers"] = "cri"


class ImagePullTool(TalosTool):
    """Pull an image on one node."""

    name = "talos_image_pull"
    description = "Pull one image on one explicit node."
    args_schema = ImagePullSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = ImagePullSchema(**arguments)
        if args.namespace == "taloscontainers" and await self.client.client_minor() != "1.14":
            raise TalosExecutionError("UNSUPPORTED_CAPABILITY")
        return await self.execute_talosctl(
            ["image", "pull", args.image, "--namespace", args.namespace, "-n", args.node]
        )


class BootstrapTool(TalosTool):
    """Bootstrap etcd using authenticated credentials on one node."""

    name = "talos_bootstrap"
    description = "Bootstrap one configured node after authenticated version readback."
    args_schema = NodeSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = NodeSchema(**arguments)
        return await self.execute_talosctl(["bootstrap", "-n", args.node])
