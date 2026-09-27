"""CLI startup and server-factory contracts."""

import subprocess
import sys

from talos_mcp import __version__, server
from talos_mcp.core.client import TalosClient
from talos_mcp.server import create_server


def test_version_flag() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "talos_mcp.server", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"talos-mcp-server {__version__}"


def test_help_lists_profile_and_pinned_inputs() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "talos_mcp.server", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0
    for option in (
        "--profile",
        "--allow-tools",
        "--talosctl",
        "--talosconfig",
        "--context",
        "--artifact-root",
    ):
        assert option in result.stdout


def test_invalid_option_fails_startup() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "talos_mcp.server", "--invalid-option"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode != 0
    assert "No such option" in result.stderr


def test_server_factory_constructs_without_global_runtime() -> None:
    assert not hasattr(server, "talos_client")
    assert not hasattr(server, "app_mcp")
    assert create_server(TalosClient(profile="readonly")).name == "talos-mcp-server"
