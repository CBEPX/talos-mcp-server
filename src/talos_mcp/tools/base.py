"""Base classes for Talos MCP tools."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from mcp.types import TextContent, Tool
from pydantic import BaseModel

from talos_mcp.core.client import TalosClient
from talos_mcp.core.exceptions import TalosCommandError


class TalosTool(ABC):
    """Base class for all Talos MCP tools."""

    name: ClassVar[str]
    description: ClassVar[str]
    args_schema: ClassVar[type[BaseModel]]  # Renamed from input_schema to be explicit

    def __init__(self, client: TalosClient) -> None:
        """Initialize the tool.

        Args:
            client: The TalosClient instance.
        """
        self.client = client

    def get_definition(self) -> Tool:
        """Get the MCP Tool definition.

        Returns:
            The Tool object.
        """
        return Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.args_schema.model_json_schema(),
        )

    @abstractmethod
    async def run(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Run the tool.

        Args:
            arguments: Tool arguments.

        Returns:
            List of TextContent results.
        """
        pass

    async def execute_talosctl(self, args: list[str]) -> list[TextContent]:
        """Helper to execute talosctl and return TextContent.

        Args:
            args: Arguments for talosctl.

        Returns:
            Formatted TextContent.
        """
        try:
            result = await self.client.execute_talosctl(args)
            output = result["stdout"]
            if result.get("stderr"):
                if output:
                    output += "\n\n"
                output += result["stderr"]
            return [TextContent(type="text", text=f"```\n{output}\n```")]
        except TalosCommandError as e:
            return [TextContent(type="text", text=f"Error executing {self.name}:\n{e.stderr}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error executing {self.name}:\n{str(e)}")]

    def ensure_nodes(self, nodes: str | None) -> str:
        """Helper to ensure nodes are set, defaulting to all cluster nodes if None.
        
        Args:
            nodes: The provided nodes argument (comma-separated list or None).
            
        Returns:
            Comma-separated list of nodes.
        """
        if not nodes or nodes.lower() in ("all", "cluster"):
            all_nodes = self.client.get_nodes()
            return ",".join(all_nodes)
        return nodes
