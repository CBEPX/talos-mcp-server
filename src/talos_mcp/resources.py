"""MCP Resources implementation for Talos."""

from mcp.types import Resource, ResourceTemplate
from pydantic import AnyUrl

from talos_mcp.core.client import TalosClient
from talos_mcp.core.exceptions import TalosCommandError


class TalosResources:
    """Talos Resources handler."""

    def __init__(self, client: TalosClient) -> None:
        """Initialize TalosResources.

        Args:
            client: TalosClient instance
        """
        self.client = client

    async def list_resources(self) -> list[Resource]:
        """List available resources."""
        # Since resources are dynamic (per node), we use templates mostly.
        # But we can list some static ones if needed.
        return []

    async def list_resource_templates(self) -> list[ResourceTemplate]:
        """List available resource templates."""
        return [
            ResourceTemplate(
                uriTemplate="talos://{node}/health",
                name="Node Health",
                description="Get health status for a specific node",
                mimeType="text/plain",
            ),
            ResourceTemplate(
                uriTemplate="talos://{node}/version",
                name="Node Version",
                description="Get version information for a specific node",
                mimeType="text/plain",
            ),
            ResourceTemplate(
                uriTemplate="talos://{node}/config",
                name="Node Config Context",
                description="Get configuration context information",
                mimeType="text/plain",
            ),
        ]

    async def read_resource(self, uri: AnyUrl) -> str:
        """Read a Talos resource.

        Supported schemes:
        - talos://<node_ip>/health
        - talos://<node_ip>/version
        - talos://<node_ip>/config (Context info)
        """
        scheme = uri.scheme
        path = uri.path
        host = uri.host

        if scheme != "talos":
            raise ValueError(f"Unsupported scheme: {scheme}")

        if not host:
            # handle case where host might be empty or part of path depending on parsing
            pass

        # Normalize path
        resource_type = path.strip("/") if path else ""

        if resource_type == "health":
            return await self._get_health(host)
        elif resource_type == "version":
            return await self._get_version(host)
        elif resource_type == "config":
            # Config is cluster-wide usually, but we keep URI structure consistent
            return await self._get_config_info()
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")

    async def _get_health(self, node: str | None) -> str:
        """Get health status for a node."""
        args = ["health"]
        if node:
            args.extend(["--nodes", node])
        try:
            result = await self.client.execute_talosctl(args)
            return str(result["stdout"])
        except TalosCommandError as e:
            return f"Error getting health: {e.stderr}"
        except Exception as e:
            return f"Error getting health: {e!s}"

    async def _get_version(self, node: str | None) -> str:
        """Get version info for a node."""
        args = ["version"]
        if node:
            args.extend(["--nodes", node])
        try:
            result = await self.client.execute_talosctl(args)
            return str(result["stdout"])
        except TalosCommandError as e:
            return f"Error getting version: {e.stderr}"
        except Exception as e:
            return f"Error getting version: {e!s}"

    async def _get_config_info(self) -> str:
        """Get config info."""
        # Using context info as a proxy for "config" resource
        info = self.client.get_context_info()
        return str(info)
