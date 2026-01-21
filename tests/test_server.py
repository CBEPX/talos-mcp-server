"""Tests for server module."""

import subprocess
import sys


class TestServerCLI:
    """Tests for CLI functionality."""

    def test_version_flag(self) -> None:
        """Test --version flag returns version and exits."""
        result = subprocess.run(
            [sys.executable, "-m", "talos_mcp.server", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "talos-mcp-server" in result.stdout
        assert "0.3" in result.stdout  # Version starts with 0.3.x

    def test_help_flag(self) -> None:
        """Test --help flag shows usage information."""
        import re

        result = subprocess.run(
            [sys.executable, "-m", "talos_mcp.server", "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Strip ANSI escape codes
        output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
        assert result.returncode == 0
        assert "Talos MCP Server" in output
        assert "log" in output.lower()  # --log-level option
        assert "readonly" in output.lower()

    def test_invalid_option(self) -> None:
        """Test invalid option returns error."""
        result = subprocess.run(
            [sys.executable, "-m", "talos_mcp.server", "--invalid-option"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0
        assert "No such option" in result.stderr


class TestServerImports:
    """Tests for module imports and configuration."""

    def test_server_module_imports(self) -> None:
        """Test that server module imports without errors."""
        from talos_mcp import server

        assert hasattr(server, "cli")
        assert hasattr(server, "main")
        assert hasattr(server, "__version__")

    def test_version_is_valid_semver(self) -> None:
        """Test that version follows semver pattern."""
        from talos_mcp.server import __version__

        parts = __version__.split(".")
        assert len(parts) >= 2
        assert all(p.isdigit() for p in parts[:2])

    def test_settings_module_imports(self) -> None:
        """Test that settings module imports correctly."""
        from talos_mcp.core.settings import Settings, settings

        assert isinstance(settings, Settings)
        assert hasattr(settings, "log_level")
        assert hasattr(settings, "readonly")

    def test_tools_registration(self) -> None:
        """Test that all tool modules import correctly."""
        from talos_mcp.tools import (
            base,
            cluster,
            config,
            etcd,
            files,
            network,
            resources,
            services,
            system,
        )

        # All modules should have classes inheriting from TalosTool
        assert hasattr(base, "TalosTool")
        assert hasattr(cluster, "RebootTool")
        assert hasattr(config, "ApplyTool")
        assert hasattr(etcd, "EtcdMembersTool")
        assert hasattr(files, "ReadFileTool")
        assert hasattr(network, "InterfacesTool")
        assert hasattr(resources, "GetResourceTool")
        assert hasattr(services, "ServiceTool")
        assert hasattr(system, "GetVersionTool")


class TestReadonlyMode:
    """Tests for readonly mode enforcement."""

    def test_write_tools_have_mutation_flag(self) -> None:
        """Test that write tools have is_mutation flag set."""
        from talos_mcp.server import tools_map

        # Known write operations should have is_mutation = True
        write_tools = ["talos_reboot", "talos_shutdown", "talos_apply"]
        for tool_name in write_tools:
            tool = tools_map.get(tool_name)
            assert tool is not None, f"Tool {tool_name} should exist"
            assert (
                getattr(tool, "is_mutation", False) is True
            ), f"Tool {tool_name} should have is_mutation = True"

    def test_readonly_setting_default(self) -> None:
        """Test that readonly defaults to False."""
        from talos_mcp.core.settings import Settings

        fresh_settings = Settings()
        assert fresh_settings.readonly is False
