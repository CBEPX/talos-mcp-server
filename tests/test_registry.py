"""Tests for tool registry and auto-discovery."""

from talos_mcp.registry import create_tool_registry, discover_tools
from talos_mcp.tools.base import TalosTool


class TestToolDiscovery:
    """Test auto-discovery of tools."""

    def test_discover_tools_finds_all_tools(self, mock_talos_client):
        """Test that discover_tools finds all available tools."""
        tools = discover_tools(mock_talos_client)

        assert len(tools) > 0, "Should discover at least one tool"
        assert all(isinstance(tool, TalosTool) for tool in tools)

        # Check that we have tools from different modules
        tool_names = {tool.name for tool in tools}

        # Sample tools from different categories
        expected_tools = {
            "talos_version",  # system
            "talos_reboot",  # cluster
            "talos_config_info",  # config
            "talos_etcd_members",  # etcd
            "talos_ls",  # files
        }

        missing_tools = expected_tools - tool_names
        assert not missing_tools, f"Missing tools: {missing_tools}"

    def test_discover_tools_no_duplicates(self, mock_talos_client):
        """Test that discover_tools doesn't create duplicate tools."""
        tools = discover_tools(mock_talos_client)
        tool_names = [tool.name for tool in tools]

        # Check for duplicates
        unique_names = set(tool_names)
        assert len(tool_names) == len(
            unique_names
        ), f"Found duplicate tools: {[name for name in tool_names if tool_names.count(name) > 1]}"

    def test_discover_tools_all_have_required_attributes(self, mock_talos_client):
        """Test that all discovered tools have required attributes."""
        tools = discover_tools(mock_talos_client)

        for tool in tools:
            assert hasattr(tool, "name"), f"{tool.__class__.__name__} missing 'name'"
            assert hasattr(tool, "description"), f"{tool.__class__.__name__} missing 'description'"
            assert hasattr(tool, "args_schema"), f"{tool.__class__.__name__} missing 'args_schema'"
            assert hasattr(tool, "is_mutation"), f"{tool.__class__.__name__} missing 'is_mutation'"
            assert isinstance(
                tool.is_mutation, bool
            ), f"{tool.__class__.__name__}.is_mutation should be bool"

    def test_create_tool_registry_with_discovery(self, mock_talos_client):
        """Test create_tool_registry with auto-discovery enabled."""
        tools_list, tools_map = create_tool_registry(mock_talos_client, use_discovery=True)

        assert len(tools_list) > 0
        assert len(tools_map) == len(tools_list)

        # Verify map is correctly keyed by tool name
        for tool in tools_list:
            assert tool.name in tools_map
            assert tools_map[tool.name] is tool

    def test_create_tool_registry_manual_registration(self, mock_talos_client):
        """Test create_tool_registry with manual registration (fallback)."""
        tools_list, tools_map = create_tool_registry(mock_talos_client, use_discovery=False)

        assert len(tools_list) > 0
        assert len(tools_map) == len(tools_list)

    def test_discovery_vs_manual_same_count(self, mock_talos_client):
        """Test that discovery and manual registration find same number of tools."""
        tools_auto, _ = create_tool_registry(mock_talos_client, use_discovery=True)
        tools_manual, _ = create_tool_registry(mock_talos_client, use_discovery=False)

        # Should have same count
        assert len(tools_auto) == len(tools_manual), (
            f"Auto-discovery found {len(tools_auto)} tools, " f"manual found {len(tools_manual)}"
        )

        # Should have same tool names
        auto_names = {tool.name for tool in tools_auto}
        manual_names = {tool.name for tool in tools_manual}

        missing_in_auto = manual_names - auto_names
        extra_in_auto = auto_names - manual_names

        assert not missing_in_auto, f"Auto-discovery missing: {missing_in_auto}"
        assert not extra_in_auto, f"Auto-discovery has extra: {extra_in_auto}"


class TestToolRegistry:
    """Test tool registry functionality."""

    def test_tools_map_keys_match_tool_names(self, mock_talos_client):
        """Test that tools_map keys match the actual tool names."""
        _, tools_map = create_tool_registry(mock_talos_client)

        for key, tool in tools_map.items():
            assert key == tool.name, f"Map key '{key}' doesn't match tool name '{tool.name}'"

    def test_all_tools_have_unique_names(self, mock_talos_client):
        """Test that all tools have unique names."""
        tools_list, _ = create_tool_registry(mock_talos_client)

        names = [tool.name for tool in tools_list]
        unique_names = set(names)

        assert len(names) == len(
            unique_names
        ), f"Duplicate tool names found: {[n for n in names if names.count(n) > 1]}"

    def test_tool_count_expected_minimum(self, mock_talos_client):
        """Test that we have at least the expected number of tools."""
        tools_list, _ = create_tool_registry(mock_talos_client)

        # We should have at least 40 tools (as of current implementation)
        assert len(tools_list) >= 40, f"Expected at least 40 tools, found {len(tools_list)}"
