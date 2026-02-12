"""Tests for TalosClient caching mechanisms."""

import tempfile
from pathlib import Path

import pytest
import yaml

from talos_mcp.core.client import TalosClient


class TestClientCaching:
    """Test caching mechanisms in TalosClient."""

    def test_config_caching_on_same_mtime(self):
        """Test that config is cached when file hasn't changed."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config = {
                "context": "test-context",
                "contexts": {
                    "test-context": {
                        "target": "192.168.1.1",
                        "endpoints": ["192.168.1.1:6443"],
                        "nodes": ["192.168.1.1"],
                    }
                },
            }
            yaml.dump(config, f)
            config_path = f.name

        try:
            client = TalosClient(config_path=config_path)
            initial_config = client.config

            # Reload config without changing file
            client._load_config()

            # Config should be the same object (cached)
            assert client.config is initial_config
        finally:
            Path(config_path).unlink()

    def test_get_nodes_caching(self):
        """Test that get_nodes() results are cached."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config = {
                "context": "test-context",
                "contexts": {
                    "test-context": {
                        "target": "192.168.1.1",
                        "endpoints": ["192.168.1.1:6443", "192.168.1.2:6443"],
                        "nodes": ["192.168.1.1", "192.168.1.2"],
                    }
                },
            }
            yaml.dump(config, f)
            config_path = f.name

        try:
            client = TalosClient(config_path=config_path)

            # First call
            nodes1 = client.get_nodes()
            # Second call should use cache
            nodes2 = client.get_nodes()

            assert nodes1 == nodes2
            assert nodes1 == ["192.168.1.1", "192.168.1.2"]

            # Check that cache info shows hits
            cache_info = client._get_nodes_cached.cache_info()
            assert cache_info.hits > 0
        finally:
            Path(config_path).unlink()

    def test_ipv6_address_parsing(self):
        """Test that IPv6 addresses with ports are correctly parsed."""
        # Create a temporary config file with IPv6 endpoints
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config = {
                "context": "test-context",
                "contexts": {
                    "test-context": {
                        "target": "[::1]",
                        "endpoints": [
                            "[::1]:6443",
                            "[2001:db8::1]:6443",
                            "192.168.1.1:6443",
                            "[fe80::1]",  # IPv6 without port
                        ],
                    }
                },
            }
            yaml.dump(config, f)
            config_path = f.name

        try:
            client = TalosClient(config_path=config_path)
            nodes = client.get_nodes()

            # Should extract IPv6 addresses correctly
            assert "::1" in nodes
            assert "2001:db8::1" in nodes
            assert "192.168.1.1" in nodes
            assert "fe80::1" in nodes

            # Should not contain ports or brackets
            assert "[::1]:6443" not in nodes
            assert "192.168.1.1:6443" not in nodes
        finally:
            Path(config_path).unlink()

    def test_ipv4_with_port_parsing(self):
        """Test that IPv4 addresses with ports are correctly parsed."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config = {
                "context": "test-context",
                "contexts": {
                    "test-context": {
                        "endpoints": [
                            "192.168.1.1:6443",
                            "10.0.0.1:6443",
                            "172.16.0.1",  # No port
                        ],
                    }
                },
            }
            yaml.dump(config, f)
            config_path = f.name

        try:
            client = TalosClient(config_path=config_path)
            nodes = client.get_nodes()

            # Should extract addresses without ports
            assert "192.168.1.1" in nodes
            assert "10.0.0.1" in nodes
            assert "172.16.0.1" in nodes

            # Should not contain ports
            assert "192.168.1.1:6443" not in nodes
        finally:
            Path(config_path).unlink()


class TestHealthCheck:
    """Test health_check method."""

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_when_no_config(self):
        """Test health_check returns unhealthy when no config loaded."""
        client = TalosClient(config_path="/nonexistent/path/config")

        result = await client.health_check()

        assert result["healthy"] is False
        assert "No Talos configuration" in result["error"]

    @pytest.mark.asyncio
    async def test_health_check_uses_mocked_execute(self, mocker):
        """Test health_check uses execute_talosctl."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config = {
                "context": "test",
                "contexts": {"test": {"endpoints": ["192.168.1.1"]}},
            }
            yaml.dump(config, f)
            config_path = f.name

        try:
            client = TalosClient(config_path=config_path)

            # Mock execute_talosctl to return success
            mock_execute = mocker.patch.object(
                client,
                "execute_talosctl",
                return_value={"stdout": "Talos v1.12.0\nClient:...", "stderr": ""},
            )

            result = await client.health_check()

            assert result["healthy"] is True
            assert "Talos v1.12.0" in result.get("version", "")
            mock_execute.assert_called_once_with(["version", "--timeout", "5s"])
        finally:
            Path(config_path).unlink()

    @pytest.mark.asyncio
    async def test_health_check_returns_error_on_failure(self, mocker):
        """Test health_check returns error details on failure."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config = {
                "context": "test",
                "contexts": {"test": {"endpoints": ["192.168.1.1"]}},
            }
            yaml.dump(config, f)
            config_path = f.name

        try:
            from talos_mcp.core.exceptions import ErrorCode, TalosCommandError

            client = TalosClient(config_path=config_path)

            # Mock execute_talosctl to raise error
            error = TalosCommandError(
                ["talosctl", "version"],
                1,
                "connection refused",
                ErrorCode.CONNECTION_FAILED,
            )
            mocker.patch.object(client, "execute_talosctl", side_effect=error)

            result = await client.health_check()

            assert result["healthy"] is False
            assert "CONNECTION_FAILED" in result.get("code", "")
        finally:
            Path(config_path).unlink()
