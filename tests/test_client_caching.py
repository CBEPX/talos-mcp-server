"""Tests for TalosClient caching mechanisms."""

import tempfile
from pathlib import Path

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
