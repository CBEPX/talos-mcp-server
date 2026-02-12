"""Tests for configuration validation and graceful degradation."""

import pytest
from mcp.types import TextContent

from talos_mcp.handlers import MCPHandlers
from talos_mcp.prompts import TalosPrompts
from talos_mcp.resources import TalosResources
from talos_mcp.tools.system import GetVersionTool


class TestGracefulDegradation:
    """Test graceful degradation when config is missing."""

    @pytest.fixture
    def mock_client_no_config(self):
        """Create a mock client with no config."""
        from unittest.mock import MagicMock

        client = MagicMock()
        client.config = None
        return client

    @pytest.fixture
    def mock_client_with_config(self):
        """Create a mock client with config."""
        from unittest.mock import MagicMock

        client = MagicMock()
        client.config = {"context": "test"}
        return client

    @pytest.fixture
    def handlers_no_config(self, mock_client_no_config):
        """Create handlers with no config."""
        prompts = TalosPrompts(mock_client_no_config)
        resources = TalosResources(mock_client_no_config)
        tool = GetVersionTool(mock_client_no_config)
        tools_list = [tool]
        tools_map = {tool.name: tool}

        return MCPHandlers(prompts, resources, tools_list, tools_map)

    @pytest.fixture
    def handlers_with_config(self, mock_client_with_config):
        """Create handlers with config."""
        prompts = TalosPrompts(mock_client_with_config)
        resources = TalosResources(mock_client_with_config)
        tool = GetVersionTool(mock_client_with_config)
        tools_list = [tool]
        tools_map = {tool.name: tool}

        return MCPHandlers(prompts, resources, tools_list, tools_map)

    @pytest.mark.asyncio
    async def test_call_tool_returns_helpful_error_when_no_config(self, handlers_no_config):
        """Test that tool calls return helpful error when config is missing."""
        result = await handlers_no_config.call_tool("talos_version", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "No Talos configuration found" in result[0].text
        assert "TALOSCONFIG" in result[0].text
        assert "talosctl gen config" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_proceeds_when_config_exists(self, handlers_with_config, mock_client_with_config):
        """Test that tool calls proceed when config exists."""
        from unittest.mock import AsyncMock

        # Mock successful execution
        mock_client_with_config.execute_talosctl = AsyncMock(return_value={
            "stdout": "Talos v1.12.0",
            "stderr": ""
        })

        result = await handlers_with_config.call_tool("talos_version", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        # Should not have the config error message
        assert "No Talos configuration found" not in result[0].text
        # Should have the actual result
        assert "Talos v1.12.0" in result[0].text
