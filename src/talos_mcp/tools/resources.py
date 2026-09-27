"""Resource management tools."""

from typing import Any, Literal

from mcp.types import TextContent
from pydantic import Field

from talos_mcp.tools.base import StrictSchema, TalosTool


class GetResourceSchema(StrictSchema):
    """Schema for get resource arguments."""

    nodes: str | None = Field(
        default=None,
        description=(
            "Comma-separated list of node IPs/hostnames. " "Defaults to all nodes if not provided."
        ),
    )
    resource: Literal["runtime/machinestatus", "runtime/volumestatus"] = Field(
        description="Exact safe runtime resource"
    )
    output: Literal["yaml", "json"] = Field(default="yaml", description="Output format")


class GetResourceTool(TalosTool):
    """Get any resource."""

    name = "talos_get"
    description = "Get a Talos resource definition"
    args_schema = GetResourceSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = GetResourceSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        cmd = [
            "get",
            args.resource.split("/", 1)[1],
            "--namespace",
            "runtime",
            "-n",
            nodes,
            "-o",
            args.output,
        ]
        return await self.execute_talosctl(cmd)


class ListDefinitionsSchema(StrictSchema):
    """Schema for list definitions arguments."""

    nodes: str | None = Field(
        default=None,
        description=(
            "Comma-separated list of node IPs/hostnames. " "Defaults to all nodes if not provided."
        ),
    )


class ListDefinitionsTool(TalosTool):
    """List generic definitions."""

    name = "talos_definitions"
    description = "List available resource definitions"
    args_schema = ListDefinitionsSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = ListDefinitionsSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        cmd = ["get", "rd", "-n", nodes]
        return await self.execute_talosctl(cmd)


class GetVolumeStatusSchema(StrictSchema):
    """Schema for volume status arguments."""

    nodes: str | None = Field(
        default=None,
        description=(
            "Comma-separated list of node IPs/hostnames. " "Defaults to all nodes if not provided."
        ),
    )
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
        nodes = self.ensure_nodes(args.nodes)
        cmd = ["get", "volumestatus", "-n", nodes, "-o", args.output]
        if args.volume:
            cmd.insert(2, args.volume)
        return await self.execute_talosctl(cmd)


class GetKernelParamStatusSchema(StrictSchema):
    """Schema for kernel param status arguments."""

    nodes: str | None = Field(
        default=None,
        description=(
            "Comma-separated list of node IPs/hostnames. " "Defaults to all nodes if not provided."
        ),
    )
    output: str = Field(default="yaml", description="Output format (yaml, json)")


class GetKernelParamStatusTool(TalosTool):
    """Get kernel param status."""

    name = "talos_kernel_param_status"
    description = "Get kernel param status (KSPP sysctl overrides) - new in 1.12"
    args_schema = GetKernelParamStatusSchema

    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool."""
        args = GetKernelParamStatusSchema(**arguments)
        nodes = self.ensure_nodes(args.nodes)
        cmd = ["get", "kernelparamstatus", "-n", nodes, "-o", args.output]
        return await self.execute_talosctl(cmd)
