"""Tests for readonly enforcement mechanism."""

import pytest

from talos_mcp.core.settings import settings
from talos_mcp.tools.cluster import (
    BootstrapTool,
    RebootTool,
    ResetTool,
    ShutdownTool,
    UpgradeTool,
)
from talos_mcp.tools.config import (
    ApplyConfigTool,
    ApplyTool,
    MachineConfigPatchTool,
    PatchTool,
)
from talos_mcp.tools.etcd import EtcdAlarmTool, EtcdDefragTool
from talos_mcp.tools.files import CopyTool
from talos_mcp.tools.system import GetVersionTool


class TestReadonlyEnforcement:
    """Test readonly mode enforcement."""

    def test_mutating_tools_have_flag_set(self, mock_talos_client):
        """Verify all mutating tools have is_mutation = True."""
        mutating_tools = [
            RebootTool,
            ShutdownTool,
            ResetTool,
            UpgradeTool,
            BootstrapTool,
            ApplyConfigTool,
            ApplyTool,
            PatchTool,
            MachineConfigPatchTool,
            EtcdAlarmTool,
            EtcdDefragTool,
            CopyTool,
        ]

        for tool_class in mutating_tools:
            tool = tool_class(mock_talos_client)
            assert (
                getattr(tool, "is_mutation", False) is True
            ), f"{tool_class.__name__} should have is_mutation = True"

    def test_readonly_tools_dont_have_flag_set(self, mock_talos_client):
        """Verify readonly tools have is_mutation = False (default)."""
        readonly_tools = [
            GetVersionTool,
        ]

        for tool_class in readonly_tools:
            tool = tool_class(mock_talos_client)
            assert (
                getattr(tool, "is_mutation", False) is False
            ), f"{tool_class.__name__} should have is_mutation = False"

    @pytest.mark.asyncio
    async def test_readonly_mode_blocks_mutations(self, mock_talos_client):
        """Test that readonly mode blocks mutating tools."""
        # Enable readonly mode
        original_readonly = settings.readonly
        settings.readonly = True

        try:
            tool = RebootTool(mock_talos_client)

            # Simulate the check that happens in server.py call_tool()
            is_blocked = settings.readonly and getattr(tool, "is_mutation", False)

            assert is_blocked, "Mutating tool should be blocked in readonly mode"
        finally:
            settings.readonly = original_readonly

    @pytest.mark.asyncio
    async def test_readonly_mode_allows_read_operations(self, mock_talos_client):
        """Test that readonly mode allows read-only tools."""
        # Enable readonly mode
        original_readonly = settings.readonly
        settings.readonly = True

        try:
            tool = GetVersionTool(mock_talos_client)

            # Simulate the check that happens in server.py call_tool()
            is_blocked = settings.readonly and getattr(tool, "is_mutation", False)

            assert not is_blocked, "Read-only tool should not be blocked"
        finally:
            settings.readonly = original_readonly

    def test_all_tools_have_is_mutation_attribute(self, mock_talos_client):
        """Verify all tools have the is_mutation attribute defined."""
        from talos_mcp.server import tools_list

        for tool in tools_list:
            assert hasattr(tool, "is_mutation"), f"{tool.name} should have is_mutation attribute"
            assert isinstance(
                getattr(tool, "is_mutation", None), bool
            ), f"{tool.name}.is_mutation should be a boolean"
