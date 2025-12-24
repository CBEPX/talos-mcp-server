"""Configuration tools."""

import json
from typing import Any, Literal

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class ConfigInfoSchema(BaseModel):
    """Schema for config info arguments."""

    pass


class ConfigInfoTool(TalosTool):
    """Get config info."""

    name = "talos_config_info"
    description = "Get information about the current Talos configuration context"
    args_schema = ConfigInfoSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        # arguments is unused but required by signature
        _ = arguments
        info = self.client.get_context_info()
        return [TextContent(type="text", text=json.dumps(info, indent=2))]


class KubeconfigSchema(BaseModel):
    """Schema for kubeconfig arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    force: bool = Field(default=False, description="Force overwrite")


class GetKubeconfigTool(TalosTool):
    """Get kubeconfig."""

    name = "talos_kubeconfig"
    description = "Retrieve kubeconfig from the cluster"
    args_schema = KubeconfigSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = KubeconfigSchema(**arguments)
        cmd = ["kubeconfig", "-n", args.nodes]
        if args.force:
            cmd.append("--force")
        return await self.execute_talosctl(cmd)


class ApplyConfigSchema(BaseModel):
    """Schema for apply config arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    file: str = Field(description="Path to config file")
    mode: str = Field(default="auto", description="Mode: auto, reboot, no-reboot")


class ApplyConfigTool(TalosTool):
    """Apply configuration."""

    name = "talos_apply_config"
    description = "Apply a new configuration to node(s) - Deprecated in 1.12, use talos_apply"
    args_schema = ApplyConfigSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ApplyConfigSchema(**arguments)
        cmd = ["apply-config", "-f", args.file, "-n", args.nodes, "--mode", args.mode]
        return await self.execute_talosctl(cmd)


class ApplySchema(BaseModel):
    """Schema for generic apply arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    file: str = Field(description="Path to manifest file")
    mode: str = Field(default="auto", description="Mode: auto, reboot, no-reboot")


class ApplyTool(TalosTool):
    """Apply generic manifest."""

    name = "talos_apply"
    description = "Apply a manifest to node(s) (new in 1.12)"
    args_schema = ApplySchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ApplySchema(**arguments)
        cmd = ["apply", "-f", args.file, "-n", args.nodes, "--mode", args.mode]
        return await self.execute_talosctl(cmd)


class ValidateConfigSchema(BaseModel):
    """Schema for validate config arguments."""

    file: str = Field(description="Path to config file")
    mode: Literal["metal", "cloud", "container"] = Field(
        default="metal", description="Validation mode"
    )


class ValidateConfigTool(TalosTool):
    """Validate configuration."""

    name = "talos_validate_config"
    description = "Validate a Talos configuration file"
    args_schema = ValidateConfigSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ValidateConfigSchema(**arguments)
        cmd = ["validate", "-c", args.file, "--mode", args.mode]
        return await self.execute_talosctl(cmd)


class PatchSchema(BaseModel):
    """Schema for patch arguments."""

    nodes: str | None = Field(default=None, description="Comma-separated list of node IPs/hostnames")
    type: str = Field(description="Resource type (e.g., MachineConfig, Service)")
    id: str | None = Field(default=None, description="Resource ID")
    patch: str = Field(description="JSON or YAML patch content")
    mode: Literal["strategic", "json"] = Field(default="strategic", description="Patch mode")


class PatchTool(TalosTool):
    """Patch resource."""

    name = "talos_patch"
    description = "Apply a patch to a specific resource"
    args_schema = PatchSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = PatchSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        
        cmd = ["patch", args.type]
        if args.id:
            cmd.append(args.id)
            
        cmd.extend(["-n", nodes, "--patch", args.patch, "--mode", args.mode])
        return await self.execute_talosctl(cmd)


class MachineConfigPatchSchema(BaseModel):
    """Schema for machineconfig patch arguments."""

    nodes: str | None = Field(default=None, description="Comma-separated list of node IPs/hostnames")
    patch: str = Field(description="YAML patch content")
    mode: Literal["auto", "reboot", "no-reboot"] = Field(default="auto", description="Apply mode")


class MachineConfigPatchTool(TalosTool):
    """Patch machineconfig."""

    name = "talos_machineconfig_patch"
    description = "Patch the machine configuration directly"
    args_schema = MachineConfigPatchSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = MachineConfigPatchSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        
        # We need to pipe the patch content to stdin since talosctl expects a file or stdin
        # constructing command with --patch is supported in newer talosctl but stdin is safer for complex yaml
        # Actually checking CLI help: `talosctl machineconfig patch [flags]` read from stdin if no file
        # But we can also use `--patch` flag if supported. 
        # Standard way is `talosctl machineconfig patch --patch <content> -n <node>`
        
        cmd = ["machineconfig", "patch", "--patch", args.patch, "-n", nodes, "--mode", args.mode]
        return await self.execute_talosctl(cmd)


class GenConfigSchema(BaseModel):
    """Schema for gen config arguments."""

    name: str = Field(description="Cluster name")
    endpoint: str = Field(description="Cluster endpoint (https://VIP:6443)")
    output_dir: str = Field(default="./", description="Output directory")
    version: str | None = Field(default=None, description="Kubernetes version")


class GenConfigTool(TalosTool):
    """Generate configuration."""

    name = "talos_gen_config"
    description = "Generate a new cluster configuration (local operation)"
    args_schema = GenConfigSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = GenConfigSchema(**arguments)
        cmd = ["gen", "config", args.name, args.endpoint, "--output-dir", args.output_dir]
        if args.version:
            cmd.extend(["--kubernetes-version", args.version])
            
        # This runs locally, does not require nodes
        return await self.execute_talosctl(cmd)

