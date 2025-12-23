"""Resource management tools."""

from typing import Any

from mcp.types import TextContent
from pydantic import BaseModel, Field

from talos_mcp.tools.base import TalosTool


class GetResourceSchema(BaseModel):
    """Schema for get resource arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    resource: str = Field(description="Resource type (e.g. members, services, machineconfig)")
    output: str = Field(default="yaml", description="Output format (yaml, json)")


class GetResourceTool(TalosTool):
    """Get any resource."""

    name = "talos_get"
    description = "Get a Talos resource definition"
    args_schema = GetResourceSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = GetResourceSchema(**arguments)
        cmd = ["get", args.resource, "-n", args.nodes, "-o", args.output]
        return await self.execute_talosctl(cmd)


class ListDefinitionsSchema(BaseModel):
    """Schema for list definitions arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")


class ListDefinitionsTool(TalosTool):
    """List generic definitions."""

    name = "talos_definitions"
    description = "List available resource definitions"
    args_schema = ListDefinitionsSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ListDefinitionsSchema(**arguments)
        cmd = ["get", "rd", "-n", args.nodes]
        return await self.execute_talosctl(cmd)


class GetVolumeStatusSchema(BaseModel):
    """Schema for volume status arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    volume: str = Field(description="Volume name (optional)", default="")
    output: str = Field(default="yaml", description="Output format (yaml, json)")


class GetVolumeStatusTool(TalosTool):
    """Get volume status."""

    name = "talos_volume_status"
    description = "Get volume status (PCRs for TPM encryption) - new in 1.12"
    args_schema = GetVolumeStatusSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = GetVolumeStatusSchema(**arguments)
        cmd = ["get", "volumestatus", "-n", args.nodes, "-o", args.output]
        if args.volume:
             cmd.insert(2, args.volume)
        return await self.execute_talosctl(cmd)


class GetKernelParamStatusSchema(BaseModel):
    """Schema for kernel param status arguments."""

    nodes: str = Field(description="Comma-separated list of node IPs/hostnames")
    output: str = Field(default="yaml", description="Output format (yaml, json)")


class GetKernelParamStatusTool(TalosTool):
    """Get kernel param status."""

    name = "talos_kernel_param_status"
    description = "Get kernel param status (KSPP sysctl overrides) - new in 1.12"
    args_schema = GetKernelParamStatusSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = GetKernelParamStatusSchema(**arguments)
        cmd = ["get", "kernelparamstatus", "-n", args.nodes, "-o", args.output]
        return await self.execute_talosctl(cmd)
