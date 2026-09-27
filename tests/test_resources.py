"""Resource reads must share the enabled canonical operation boundary."""

import stat
import sys
from pathlib import Path

import pytest
from pydantic import AnyUrl

from talos_mcp.core.client import TalosClient
from talos_mcp.resources import TalosResources


@pytest.mark.asyncio
async def test_version_resource_uses_pinned_context_and_binary(tmp_path: Path) -> None:
    binary = tmp_path / "talosctl"
    binary.write_text(f"#!{sys.executable}\nimport sys\nprint(' '.join(sys.argv[1:]))\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    resources = TalosResources(TalosClient(str(config), profile="readonly", talosctl=str(binary)))
    result = await resources.read_resource(AnyUrl("talos://node/version"))
    assert result.startswith("version -n node")
    assert f"--talosconfig {config}" in result
    assert "--context lab" in result
    port_result = await resources.read_resource(AnyUrl("talos://127.0.0.1:50001/version"))
    assert port_result.startswith("version -n 127.0.0.1:50001")


@pytest.mark.asyncio
async def test_config_resource_contains_no_config_body(tmp_path: Path) -> None:
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    crt: SENTINEL_SECRET\n")
    resources = TalosResources(TalosClient(str(config), profile="readonly"))
    result = await resources.read_resource(AnyUrl("talos://node/config"))
    assert "lab" in result
    assert "SENTINEL_SECRET" not in result


@pytest.mark.asyncio
async def test_invalid_resource_uri_is_rejected() -> None:
    resources = TalosResources(TalosClient(profile="readonly"))
    for uri in ("http://node/version", "talos://node/unknown", "talos://node/config/extra"):
        with pytest.raises(ValueError):
            await resources.read_resource(AnyUrl(uri))
