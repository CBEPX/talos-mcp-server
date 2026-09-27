"""Talos configuration inspection, generation, validation, and apply tools."""

import base64
import binascii
import json
import re
import shutil
from typing import Any, Literal

from mcp.types import TextContent
from pydantic import Field, model_validator

from talos_mcp.tools.base import StrictSchema, TalosTool
from talos_mcp.tools.cluster import NodeSchema


class ConfigInfoSchema(StrictSchema):
    """No arguments for sanitized context information."""


class ConfigInfoTool(TalosTool):
    """Return non-secret context metadata."""

    name = "talos_config_info"
    description = "Show selected context name and whether a Talos config is loaded."
    args_schema = ConfigInfoSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        return [TextContent(type="text", text=json.dumps(self.client.get_context_info()))]


class ValidateConfigSchema(StrictSchema):
    """Offline validation of one reviewed file below artifact root."""

    file: str
    mode: Literal["metal", "cloud", "container"] = "metal"
    strict: bool = True


class ValidateConfigTool(TalosTool):
    """Validate a confined config locally without credentials or output files."""

    name = "talos_validate_config"
    description = "Validate a reviewed config under artifact root without cluster credentials."
    args_schema = ValidateConfigSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = ValidateConfigSchema(**arguments)
        path = self.client.artifact_input(args.file)
        command = ["validate", "-c", str(path), "--mode", args.mode]
        if args.strict:
            command.append("--strict")
        return await self.execute_talosctl(command)


class GenConfigSchema(StrictSchema):
    """Offline generation into a unique private server directory."""

    name: str = Field(min_length=1)
    endpoint: str = Field(pattern=r"^https://[^\s/]+:\d+$")
    kubernetes_version: str | None = None


class GenConfigTool(TalosTool):
    """Generate Talos config files beneath artifact root."""

    name = "talos_gen_config"
    description = "Generate private cluster configs offline; response contains file metadata only."
    args_schema = GenConfigSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = GenConfigSchema(**arguments)
        directory = self.client.new_artifact_dir()
        cmd = ["gen", "config", args.name, args.endpoint, "--output", str(directory)]
        if args.kubernetes_version:
            cmd.extend(["--kubernetes-version", args.kubernetes_version])
        try:
            await self.client.execute_talosctl(cmd, operation=self.name)
            files = [
                self.client.artifact_metadata(path)
                for path in directory.iterdir()
                if path.is_file()
            ]
            if not files:
                raise ValueError("Generation produced no files")
            return [TextContent(type="text", text=json.dumps(files))]
        except BaseException:
            shutil.rmtree(directory)
            raise


class ApplyConfigSchema(NodeSchema):
    """Apply reviewed config in one explicit native mode."""

    file: str
    mode: Literal["auto", "no-reboot", "staged", "try"]
    insecure: bool = False
    cert_fingerprint: str | None = None
    target_version: str | None = None

    @model_validator(mode="after")
    def maintenance(self) -> "ApplyConfigSchema":
        """Require pinned TLS fingerprint and declared minor for maintenance apply."""
        if self.insecure:
            try:
                decoded = base64.b64decode(self.cert_fingerprint or "", validate=True)
            except (ValueError, binascii.Error) as exc:
                raise ValueError(
                    "maintenance apply requires base64 SHA256 cert fingerprint"
                ) from exc
            if len(decoded) != 32:
                raise ValueError("maintenance apply requires base64 SHA256 cert fingerprint")
            if not self.target_version or not re.fullmatch(
                r"v?1\.(13|14)\.\d+", self.target_version
            ):
                raise ValueError("maintenance apply requires supported target_version")
        elif self.cert_fingerprint or self.target_version:
            raise ValueError("fingerprint and target_version require insecure=true")
        return self


class ApplyConfigTool(TalosTool):
    """Apply a reviewed file to one node."""

    name = "talos_apply_config"
    description = (
        "Apply reviewed config to one node; mode required. "
        "Maintenance requires fingerprint and target version."
    )
    args_schema = ApplyConfigSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = ApplyConfigSchema(**arguments)
        path = self.client.artifact_input(args.file)
        cmd = ["apply-config", "-f", str(path), "-n", args.node, "--mode", args.mode]
        if args.insecure:
            cmd.extend(["--insecure", "--cert-fingerprint", args.cert_fingerprint or ""])
        return await self.execute_talosctl(cmd, target_version=args.target_version)


class MachineConfigPatchSchema(NodeSchema):
    """Patch machineconfig from a reviewed file in one explicit mode."""

    file: str
    mode: Literal["auto", "no-reboot", "staged", "try"]


class MachineConfigPatchTool(TalosTool):
    """Apply a reviewed patch to one node's machineconfig."""

    name = "talos_machineconfig_patch"
    description = "Patch machineconfig on one node using a reviewed file and required apply mode."
    args_schema = MachineConfigPatchSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = MachineConfigPatchSchema(**arguments)
        path = self.client.artifact_input(args.file)
        return await self.execute_talosctl(
            [
                "patch",
                "machineconfig",
                "--patch-file",
                str(path),
                "-n",
                args.node,
                "--mode",
                args.mode,
            ]
        )


class KubeconfigSchema(NodeSchema):
    """Retrieve a kubeconfig into a private unique file."""


class GetKubeconfigTool(TalosTool):
    """Download one kubeconfig without merging user files."""

    name = "talos_kubeconfig"
    description = "Write kubeconfig to a new private artifact; never merge ~/.kube/config."
    args_schema = KubeconfigSchema
    is_mutation = True

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute this Talos tool."""
        args = KubeconfigSchema(**arguments)
        directory = self.client.new_artifact_dir()
        path = directory / "kubeconfig"
        try:
            await self.client.execute_talosctl(
                ["kubeconfig", str(path), "--merge=false", "-n", args.node], operation=self.name
            )
            return [TextContent(type="text", text=json.dumps(self.client.artifact_metadata(path)))]
        except BaseException:
            shutil.rmtree(directory)
            raise
