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
