"""Tests for tool documentation quality."""

import pytest

from talos_mcp.tools.base import TalosTool
from talos_mcp.tools.cluster import RebootTool, UpgradeTool
from talos_mcp.tools.etcd import EtcdMembersTool, EtcdSnapshotTool
from talos_mcp.tools.system import DashboardTool, GetHealthTool, GetVersionTool


class TestToolDocumentation:
    """Test that tools have proper documentation."""

    def test_version_tool_has_description(self, mock_talos_client):
        """Test GetVersionTool has detailed description."""
        tool = GetVersionTool(mock_talos_client)

        assert "version" in tool.description.lower()
        assert "example" in tool.description.lower()

    def test_version_tool_description_length(self, mock_talos_client):
        """Test GetVersionTool description is detailed enough."""
        tool = GetVersionTool(mock_talos_client)

        # Description should be reasonably detailed
        assert len(tool.description) > 100

    def test_health_tool_has_description(self, mock_talos_client):
        """Test GetHealthTool has detailed description."""
        tool = GetHealthTool(mock_talos_client)

        assert "health" in tool.description.lower()
        assert "example" in tool.description.lower()

    def test_reboot_tool_has_warning(self, mock_talos_client):
        """Test RebootTool has warning in description."""
        tool = RebootTool(mock_talos_client)

        assert "caution" in tool.description.lower() or "disrupt" in tool.description.lower()
        assert "example" in tool.description.lower()

    def test_upgrade_tool_has_image_format(self, mock_talos_client):
        """Test UpgradeTool documents image format."""
        tool = UpgradeTool(mock_talos_client)

        assert "ghcr.io" in tool.description.lower()
        assert "installer" in tool.description.lower()
        assert "example" in tool.description.lower()

    def test_etcd_snapshot_tool_has_path_info(self, mock_talos_client):
        """Test EtcdSnapshotTool documents path parameter."""
        tool = EtcdSnapshotTool(mock_talos_client)

        assert "backup" in tool.description.lower() or "snapshot" in tool.description.lower()
        assert "example" in tool.description.lower()

    def test_etcd_members_tool_has_permission_info(self, mock_talos_client):
        """Test EtcdMembersTool documents required permissions."""
        tool = EtcdMembersTool(mock_talos_client)

        assert "permission" in tool.description.lower() or "required" in tool.description.lower()

    def test_dashboard_tool_suggests_alternatives(self, mock_talos_client):
        """Test DashboardTool suggests alternative tools."""
        tool = DashboardTool(mock_talos_client)

        assert "not available" in tool.description.lower() or "tui" in tool.description.lower()

    def test_all_tools_have_description(self, mock_talos_client):
        """Test that all tools have non-empty descriptions."""
        from talos_mcp.server import tools_list

        for tool in tools_list:
            assert tool.description, f"{tool.name} has empty description"

    def test_mutating_tools_have_warnings(self, mock_talos_client):
        """Test that mutating tools have warning indicators."""
        mutating_tools = [
            RebootTool(mock_talos_client),
            UpgradeTool(mock_talos_client),
        ]

        warning_words = ["caution", "warning", "disrupt", "careful", "attention"]

        for tool in mutating_tools:
            has_warning = any(word in tool.description.lower() for word in warning_words)
            assert has_warning, f"{tool.name} should have warning in description"

    def test_tool_names_are_descriptive(self):
        """Test that tool names follow naming convention."""
        from talos_mcp.server import tools_list

        for tool in tools_list:
            # Name should start with talos_
            assert tool.name.startswith("talos_"), f"{tool.name} should start with 'talos_'"

            # Name should be lowercase with underscores
            assert tool.name == tool.name.lower(), f"{tool.name} should be lowercase"
            assert " " not in tool.name, f"{tool.name} should not contain spaces"
