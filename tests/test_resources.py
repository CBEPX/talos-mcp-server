"""Tests for resources module."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from pydantic import AnyUrl

from talos_mcp.resources import TalosResources
from talos_mcp.core.client import TalosClient
from talos_mcp.core.exceptions import TalosCommandError


@pytest.fixture
def mock_client() -> Mock:
    """Create a mock TalosClient."""
    client = Mock(spec=TalosClient)
    client.execute_talosctl = AsyncMock()
    client.get_context_info = Mock(return_value={"context": "test", "endpoints": ["10.0.0.1"]})
    return client


@pytest.fixture
def resources(mock_client: Mock) -> TalosResources:
    """Create TalosResources instance with mocked client."""
    return TalosResources(mock_client)


class TestTalosResources:
    """Tests for TalosResources class."""

    async def test_list_resources_empty(self, resources: TalosResources) -> None:
        """Test list_resources returns empty list (dynamic resources use templates)."""
        result = await resources.list_resources()
        assert result == []

    async def test_list_resource_templates(self, resources: TalosResources) -> None:
        """Test list_resource_templates returns expected templates."""
        result = await resources.list_resource_templates()
        assert len(result) == 3
        
        uris = [t.uriTemplate for t in result]
        assert "talos://{node}/health" in uris
        assert "talos://{node}/version" in uris
        assert "talos://{node}/config" in uris

    async def test_list_resource_templates_have_names(self, resources: TalosResources) -> None:
        """Test resource templates have proper names."""
        result = await resources.list_resource_templates()
        names = [t.name for t in result]
        assert "Node Health" in names
        assert "Node Version" in names
        assert "Node Config Context" in names


class TestReadResource:
    """Tests for read_resource method."""

    async def test_read_resource_health(
        self, resources: TalosResources, mock_client: Mock
    ) -> None:
        """Test reading health resource."""
        mock_client.execute_talosctl.return_value = {"stdout": "OK", "stderr": ""}
        
        uri = AnyUrl("talos://10.0.0.1/health")
        result = await resources.read_resource(uri)
        
        assert result == "OK"
        mock_client.execute_talosctl.assert_called_once()
        call_args = mock_client.execute_talosctl.call_args[0][0]
        assert "health" in call_args
        assert "--nodes" in call_args
        assert "10.0.0.1" in call_args

    async def test_read_resource_version(
        self, resources: TalosResources, mock_client: Mock
    ) -> None:
        """Test reading version resource."""
        mock_client.execute_talosctl.return_value = {"stdout": "v1.12.0", "stderr": ""}
        
        uri = AnyUrl("talos://10.0.0.1/version")
        result = await resources.read_resource(uri)
        
        assert "v1.12.0" in result

    async def test_read_resource_config(
        self, resources: TalosResources, mock_client: Mock
    ) -> None:
        """Test reading config resource."""
        uri = AnyUrl("talos://10.0.0.1/config")
        result = await resources.read_resource(uri)
        
        assert "context" in result
        assert "test" in result

    async def test_read_resource_unsupported_scheme(
        self, resources: TalosResources
    ) -> None:
        """Test reading resource with unsupported scheme raises."""
        uri = AnyUrl("http://10.0.0.1/health")
        with pytest.raises(ValueError, match="Unsupported scheme"):
            await resources.read_resource(uri)

    async def test_read_resource_unknown_type(
        self, resources: TalosResources
    ) -> None:
        """Test reading unknown resource type raises."""
        uri = AnyUrl("talos://10.0.0.1/unknown")
        with pytest.raises(ValueError, match="Unknown resource type"):
            await resources.read_resource(uri)

    async def test_read_resource_health_error(
        self, resources: TalosResources, mock_client: Mock
    ) -> None:
        """Test reading health with TalosCommandError returns error message."""
        mock_client.execute_talosctl.side_effect = TalosCommandError(
            1, "health", "connection refused"
        )
        
        uri = AnyUrl("talos://10.0.0.1/health")
        result = await resources.read_resource(uri)
        
        assert "Error" in result
        assert "connection refused" in result

    async def test_read_resource_version_generic_error(
        self, resources: TalosResources, mock_client: Mock
    ) -> None:
        """Test reading version with generic exception returns error message."""
        mock_client.execute_talosctl.side_effect = Exception("Network error")
        
        uri = AnyUrl("talos://10.0.0.1/version")
        result = await resources.read_resource(uri)
        
        assert "Error" in result
        assert "Network error" in result
