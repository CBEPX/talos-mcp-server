"""End-to-end boundaries for policy and subprocess execution."""

import asyncio
import ctypes
import json
import os
import stat
import sys
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any

import pytest
from loguru import logger
from pydantic import AnyUrl

from talos_mcp.core.artifacts import windows_private_acl
from talos_mcp.core.client import TalosClient, TalosExecutionError
from talos_mcp.handlers import MCPHandlers
from talos_mcp.prompts import TalosPrompts
from talos_mcp.registry import create_tool_registry
from talos_mcp.resources import TalosResources
from talos_mcp.tools.cluster import UpgradeSchema
from talos_mcp.tools.config import GenConfigSchema


def _wait_for_file(path: Path) -> None:
    """Wait for a child dispatch marker with a bounded synchronous poll."""
    deadline = time.monotonic() + 5
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert path.exists()


def fixture_handlers(tmp_path: Path, profile: str = "write") -> MCPHandlers:
    """Run actual child processes with a synthetic Talos config and argv reporter."""
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import json,sys\n"
        f"a=sys.argv[1:]\n"
        f"print('Client:\\nTalos v1.13.10\\nServer:\\n  Tag: v1.13.10' "
        f"if a[0]=='version' and '--short' in a else json.dumps(a))\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    client = TalosClient(str(config), profile=profile, talosctl=str(binary))
    catalog, tool_map = create_tool_registry(client)
    return MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)


def test_readonly_catalog_excludes_sensitive_and_mutating_tools(tmp_path: Path) -> None:
    client = TalosClient(profile="readonly")
    _, tools = create_tool_registry(client)
    assert "talos_version" in tools
    assert "talos_service" in tools
    for name in (
        "talos_cat",
        "talos_cp",
        "talos_reboot",
        "talos_gen_config",
        "talos_service_action",
    ):
        assert name not in tools


def test_tool_annotations_describe_operation_without_granting_rights() -> None:
    _, readonly = create_tool_registry(TalosClient(profile="readonly"))
    _, write = create_tool_registry(TalosClient(profile="write"))
    assert readonly["talos_version"].get_definition().annotations.readOnlyHint is True
    assert write["talos_reset"].get_definition().annotations.destructiveHint is True
    assert "talos_reset" not in readonly


def test_invalid_allowlist_is_startup_error() -> None:
    for value in ("talos_reboot", "talos_*", "talos_apply", "unknown"):
        with pytest.raises(ValueError):
            TalosClient(profile="readonly", allow_tools=[value])


def test_missing_selected_config_has_sanitized_startup_error(tmp_path: Path) -> None:
    missing = tmp_path / "SENTINEL_SECRET" / "talosconfig"
    with pytest.raises(ValueError, match="CONFIG_INVALID") as failure:
        TalosClient(str(missing))
    assert "SENTINEL_SECRET" not in str(failure.value)


def test_artifact_root_rejects_symlink_ancestor(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir(mode=0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)
    private = actual / "private"
    private.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="ARTIFACT_ROOT_INVALID"):
        TalosClient(profile="write", artifact_root=str(alias / "private"))


@pytest.mark.skipif(os.name != "posix", reason="POSIX owner check")
def test_artifact_root_requires_effective_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    assert TalosClient(profile="write", artifact_root=str(root)).artifact_root == root
    monkeypatch.setattr(os, "geteuid", lambda: root.stat().st_uid + 1)
    with pytest.raises(ValueError, match="ARTIFACT_ROOT_INVALID"):
        TalosClient(profile="write", artifact_root=str(root))


def test_artifact_limits_are_positive(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="INVALID_ARGUMENT"):
        TalosClient(profile="write", artifact_root=str(root), artifact_limit=0)


def test_configured_default_node_preserves_explicit_port(tmp_path: Path) -> None:
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [127.0.0.1:50001]\n")
    client = TalosClient(str(config), profile="readonly")
    assert client.get_nodes() == ["127.0.0.1:50001"]


@pytest.mark.asyncio
async def test_direct_spawn_rejects_write_even_with_safe_flag(tmp_path: Path) -> None:
    marker = tmp_path / "spawned"
    binary = tmp_path / "talosctl"
    binary.write_text(f"#!{sys.executable}\nopen({str(marker)!r}, 'w').close()\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    client = TalosClient(profile="readonly", talosctl=str(binary))
    with pytest.raises(TalosExecutionError):
        await client.execute_talosctl(
            ["reboot", "-n", "node", "--wait=false"], operation="talos_reboot"
        )
    assert not marker.exists()


@pytest.mark.asyncio
async def test_direct_read_operation_rejects_unreviewed_native_flags(tmp_path: Path) -> None:
    marker = tmp_path / "spawned"
    binary = tmp_path / "talosctl"
    binary.write_text(f"#!{sys.executable}\nopen({str(marker)!r}, 'w').close()\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    client = TalosClient(str(config), profile="readonly", talosctl=str(binary))
    for argv in (
        ["get", "runtime/machinestatus", "-n", "node", "--namespace", "secrets"],
        ["service", "kubelet", "restart", "-n", "node"],
        ["version", "-n", "node", "--talosconfig", str(tmp_path / "other")],
    ):
        with pytest.raises(Exception, match="INVALID_ARGUMENT"):
            await client.execute_talosctl(
                argv,
                operation={
                    "get": "talos_get",
                    "service": "talos_service",
                    "version": "talos_version",
                }[argv[0]],
            )
    assert not marker.exists()


@pytest.mark.asyncio
async def test_direct_diagnostics_cannot_bypass_numeric_caps(tmp_path: Path) -> None:
    binary = tmp_path / "talosctl"
    binary.write_text(f"#!{sys.executable}\nprint('ran')\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    client = TalosClient(str(config), profile="readonly", talosctl=str(binary))
    for operation, argv in (
        ("talos_logs", ["logs", "kubelet", "-n", "node", "--tail", "2001"]),
        ("talos_events", ["events", "-n", "node", "--tail", "501"]),
        ("talos_events", ["events", "-n", "node", "--duration", "3601s"]),
    ):
        with pytest.raises(Exception, match="INVALID_ARGUMENT"):
            await client.execute_talosctl(argv, operation=operation)


@pytest.mark.asyncio
async def test_child_output_limit_is_enforced_while_running(tmp_path: Path) -> None:
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys, time\n"
        f"sys.stdout.write('x'*300000); sys.stdout.flush(); time.sleep(30)\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    client = TalosClient(profile="readonly", talosctl=str(binary), output_limit=1024)
    with pytest.raises(Exception, match="OUTPUT_LIMIT"):
        await asyncio.wait_for(
            client.execute_talosctl(["version", "--client"], operation="talos_version"), 5
        )


@pytest.mark.asyncio
async def test_invalid_tool_arguments_produce_explicit_error_before_spawn(tmp_path: Path) -> None:
    client = TalosClient(profile="readonly")
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    result = await handlers.call_tool("talos_version", {"nodes": "node", "surprise": True})
    assert result.isError is True
    assert result.structuredContent["code"] == "INVALID_ARGUMENT"
    assert result.structuredContent["complete"] is False
    assert json.loads(result.content[0].text) == result.structuredContent
    assert tool_map["talos_version"].get_definition().inputSchema["additionalProperties"] is False


@pytest.mark.asyncio
async def test_success_structured_content_carries_public_version(tmp_path: Path) -> None:
    handlers = fixture_handlers(tmp_path, "readonly")
    result = await handlers.call_tool("talos_version", {"client_only": True})
    assert result.isError is False
    assert result.structuredContent["content"][0]["text"] == result.content[0].text
    assert "version" in result.structuredContent["content"][0]["text"]


@pytest.mark.asyncio
async def test_alias_cannot_bypass_allowlist() -> None:
    client = TalosClient(profile="write", allow_tools=["talos_version"])
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    result = await handlers.call_tool(
        "talos_apply", {"nodes": "node", "file": "config.yaml", "mode": "auto"}
    )
    assert result.isError is True
    assert result.structuredContent["code"] == "TOOL_NOT_ENABLED"


@pytest.mark.asyncio
async def test_mixed_actions_are_split_and_native_argv_is_exact(tmp_path: Path) -> None:
    handlers = fixture_handlers(tmp_path)
    old = await handlers.call_tool(
        "talos_service", {"nodes": "node", "service": "kubelet", "action": "restart"}
    )
    assert old.isError is True
    assert old.structuredContent["code"] == "INVALID_ARGUMENT"
    new = await handlers.call_tool(
        "talos_service_action", {"node": "node", "service": "kubelet", "action": "restart"}
    )
    assert new.isError is False
    assert json.loads(new.content[0].text.strip("`\n")) == [
        "service",
        "kubelet",
        "restart",
        "-n",
        "node",
        "--talosconfig",
        str(tmp_path / "talosconfig"),
        "--context",
        "lab",
    ]


@pytest.mark.asyncio
async def test_get_denies_secret_resource_before_spawn(tmp_path: Path) -> None:
    handlers = fixture_handlers(tmp_path, "readonly")
    denied = await handlers.call_tool("talos_get", {"resource": "machineconfig", "nodes": "node"})
    assert denied.isError is True
    assert denied.structuredContent["code"] == "INVALID_ARGUMENT"
    allowed = await handlers.call_tool(
        "talos_get", {"resource": "runtime/machinestatus", "nodes": "node"}
    )
    assert allowed.isError is False
    assert json.loads(allowed.content[0].text.strip("`\n"))[:8] == [
        "get",
        "machinestatus",
        "--namespace",
        "runtime",
        "-n",
        "node",
        "-o",
        "yaml",
    ]


@pytest.mark.asyncio
async def test_image_and_alarm_writes_use_separate_tools(tmp_path: Path) -> None:
    handlers = fixture_handlers(tmp_path)
    for name, arguments in (
        ("talos_image", {"nodes": "node", "cmd": "pull", "image": "example:v1"}),
        ("talos_etcd_alarm", {"nodes": "node", "action": "disarm"}),
    ):
        result = await handlers.call_tool(name, arguments)
        assert result.isError is True
        assert result.structuredContent["code"] == "INVALID_ARGUMENT"
    pull = await handlers.call_tool("talos_image_pull", {"node": "node", "image": "example:v1"})
    assert pull.isError is False
    assert json.loads(pull.content[0].text.strip("`\n"))[:6] == [
        "image",
        "pull",
        "example:v1",
        "--namespace",
        "cri",
        "-n",
    ]
    disarm = await handlers.call_tool("talos_etcd_alarm_disarm", {"node": "node"})
    assert disarm.isError is False
    assert json.loads(disarm.content[0].text.strip("`\n"))[:4] == ["etcd", "alarm", "disarm", "-n"]


@pytest.mark.asyncio
async def test_image_namespace_is_explicit_and_version_gated(tmp_path: Path) -> None:
    handlers = fixture_handlers(tmp_path)
    listed = await handlers.call_tool("talos_image", {"node": "node", "namespace": "system"})
    assert listed.isError is False
    assert json.loads(listed.content[0].text.strip("`\n"))[:6] == [
        "image",
        "list",
        "--namespace",
        "system",
        "-n",
        "node",
    ]
    pulled = await handlers.call_tool(
        "talos_image_pull", {"node": "node", "image": "example:v1", "namespace": "system"}
    )
    assert pulled.isError is False
    assert json.loads(pulled.content[0].text.strip("`\n"))[:7] == [
        "image",
        "pull",
        "example:v1",
        "--namespace",
        "system",
        "-n",
        "node",
    ]
    unsupported = await handlers.call_tool(
        "talos_image", {"node": "node", "namespace": "taloscontainers"}
    )
    assert unsupported.isError is True
    assert unsupported.structuredContent["code"] == "UNSUPPORTED_CAPABILITY"


@pytest.mark.asyncio
async def test_lifecycle_rejects_fanout_and_reboot_uses_nonwaiting_acceptance(
    tmp_path: Path,
) -> None:
    handlers = fixture_handlers(tmp_path)
    fanout = await handlers.call_tool("talos_reboot", {"nodes": "node,other"})
    assert fanout.isError is True
    assert fanout.structuredContent["code"] == "INVALID_ARGUMENT"
    reboot = await handlers.call_tool("talos_reboot", {"node": "node"})
    assert reboot.isError is False
    assert json.loads(reboot.content[0].text.strip("`\n"))[:3] == ["reboot", "-n", "node"]


@pytest.mark.asyncio
async def test_lifecycle_golden_argv_and_accepted_outcomes(tmp_path: Path) -> None:
    handlers = fixture_handlers(tmp_path)
    image = "factory.talos.dev/metal-installer/" + "b" * 64 + "@sha256:" + "a" * 64
    cases = (
        ("talos_bootstrap", {"node": "node"}, ["bootstrap", "-n", "node"], "accepted"),
        ("talos_reboot", {"node": "node"}, ["reboot", "-n", "node", "--wait=false"], "accepted"),
        (
            "talos_shutdown",
            {"node": "node"},
            ["shutdown", "-n", "node", "--wait=false"],
            "accepted",
        ),
        (
            "talos_reset",
            {"node": "node", "wipe_labels": ["STATE"]},
            [
                "reset",
                "-n",
                "node",
                "--system-labels-to-wipe",
                "STATE",
                "--graceful=true",
                "--reboot=true",
                "--wait=false",
            ],
            "accepted",
        ),
        (
            "talos_upgrade",
            {
                "node": "node",
                "target_version": "v1.13.10",
                "image": image,
                "schematic_id": "b" * 64,
            },
            ["upgrade", "-n", "node", "--image", image, "--wait=true", "--drain=true"],
            "accepted",
        ),
        ("talos_etcd_defrag", {"node": "node"}, ["etcd", "defrag", "-n", "node"], "complete"),
    )
    for name, arguments, expected, outcome in cases:
        result = await handlers.call_tool(name, arguments)
        assert result.isError is False, name
        assert result.structuredContent["outcome"] == outcome
        assert json.loads(result.content[0].text.strip("`\n"))[: len(expected)] == expected


@pytest.mark.asyncio
async def test_upgrade_uses_its_own_bounded_call_deadline(tmp_path: Path) -> None:
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys,time\n"
        f"if sys.argv[1]=='version': print('Client:\\nTalos v1.13.10\\n"
        f"Server:\\n  Tag: v1.13.10')\n"
        f"else: time.sleep(0.4)\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    client = TalosClient(
        str(config), profile="write", talosctl=str(binary), timeout=0.1, upgrade_timeout=5.0
    )
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    result = await handlers.call_tool(
        "talos_upgrade",
        {
            "node": "node",
            "target_version": "v1.13.10",
            "image": "ghcr.io/siderolabs/installer@sha256:" + "a" * 64,
        },
    )
    assert result.isError is False
    assert result.structuredContent["outcome"] == "accepted"


def test_artifact_input_rejects_traversal_symlink_and_public_root(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    (root / "config.yaml").write_text("machine: {}")
    (root / "link").symlink_to(tmp_path / "outside")
    client = TalosClient(profile="readonly", artifact_root=str(root))
    assert client.artifact_input("config.yaml") == root / "config.yaml"
    for name in ("../outside", str(tmp_path / "outside"), "link"):
        with pytest.raises(TalosExecutionError):
            client.artifact_input(name)
    root.chmod(0o755)
    with pytest.raises(ValueError):
        TalosClient(profile="readonly", artifact_root=str(root))


def test_quota_scan_ignores_only_disappearing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    call = root / "talos-mcp-one"
    call.mkdir(mode=0o700)
    completed = call / "snapshot"
    completed.write_bytes(b"done")
    racing = root / "racing"
    racing.write_bytes(b"temporary")
    original_lstat = Path.lstat
    seen = 0

    def disappearing(self: Path, *args: Any, **kwargs: Any) -> os.stat_result:
        nonlocal seen
        if self == racing:
            seen += 1
            if seen == 1:
                racing.unlink()
                raise FileNotFoundError(str(racing))
        return original_lstat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", disappearing)
    metadata = TalosClient(profile="write", artifact_root=str(root)).artifact_metadata(completed)
    assert seen >= 1
    assert metadata["size"] == 4
    assert completed.read_bytes() == b"done"


def test_quota_scan_preserves_completed_artifact_when_sibling_directory_disappears(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    completed_dir = root / "talos-mcp-completed"
    completed_dir.mkdir(mode=0o700)
    completed = completed_dir / "snapshot"
    completed.write_bytes(b"done")
    sibling = root / "talos-mcp-disappearing"
    sibling.mkdir(mode=0o700)
    (sibling / "temporary").write_bytes(b"x")
    original_scandir = os.scandir
    removed = False

    def disappearing(path: Any) -> Any:
        nonlocal removed
        if Path(path) == sibling and not removed:
            removed = True
            (sibling / "temporary").unlink()
            sibling.rmdir()
            raise FileNotFoundError(str(sibling))
        return original_scandir(path)

    monkeypatch.setattr(os, "scandir", disappearing)
    metadata = TalosClient(profile="write", artifact_root=str(root)).artifact_metadata(completed)
    assert removed
    assert metadata["size"] == 4
    assert completed.read_bytes() == b"done"


def test_quota_scan_propagates_permission_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    original_scandir = os.scandir

    def denied(path: Any) -> Any:
        if Path(path) == root:
            raise PermissionError(str(root))
        return original_scandir(path)

    monkeypatch.setattr(os, "scandir", denied)
    with pytest.raises(PermissionError):
        TalosClient._tree_size(root)


@pytest.mark.asyncio
async def test_readonly_validate_requires_no_cluster_config_and_creates_nothing(
    tmp_path: Path,
) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    (root / "config.yaml").write_text("machine: {}")
    binary = tmp_path / "talosctl"
    binary.write_text(f"#!{sys.executable}\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    client = TalosClient(profile="readonly", artifact_root=str(root), talosctl=str(binary))
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    result = await handlers.call_tool(
        "talos_validate_config", {"file": "config.yaml", "mode": "metal"}
    )
    assert result.isError is False
    argv = json.loads(result.content[0].text.strip("`\n"))
    assert str(root / "config.yaml") in argv
    assert "--strict" in argv
    lenient = await handlers.call_tool(
        "talos_validate_config", {"file": "config.yaml", "mode": "metal", "strict": False}
    )
    assert lenient.isError is False
    assert "--strict" not in json.loads(lenient.content[0].text.strip("`\n"))
    assert sorted(path.name for path in root.iterdir()) == ["config.yaml"]


@pytest.mark.asyncio
async def test_direct_validate_cannot_read_outside_artifact_root(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    outside = tmp_path / "outside.yaml"
    outside.write_text("secret")
    binary = tmp_path / "talosctl"
    binary.write_text(f"#!{sys.executable}\nprint('ran')\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    client = TalosClient(profile="readonly", artifact_root=str(root), talosctl=str(binary))
    with pytest.raises(Exception, match="INVALID_ARGUMENT"):
        await client.execute_talosctl(
            ["validate", "-c", str(outside), "--mode", "metal"], operation="talos_validate_config"
        )


@pytest.mark.asyncio
async def test_cat_content_is_private_artifact_and_not_model_text(tmp_path: Path) -> None:
    handlers = fixture_handlers(tmp_path)
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    handlers.tools_list[0].client.artifact_root = root
    result = await handlers.call_tool("talos_cat", {"node": "node", "path": "/var/log/test"})
    assert result.isError is False
    assert "--talosconfig" not in result.content[0].text
    metadata = json.loads(result.content[0].text)
    assert Path(metadata["path"]).is_file()
    assert Path(metadata["path"]).stat().st_mode & 0o077 == 0


@pytest.mark.asyncio
async def test_resource_catalog_and_read_obey_effective_tool_allowlist(tmp_path: Path) -> None:
    client = TalosClient(profile="readonly", allow_tools=["talos_version"])
    resources = TalosResources(client)
    templates = await resources.list_resource_templates()
    assert [template.uriTemplate for template in templates] == ["talos://{node}/version"]
    with pytest.raises(TalosExecutionError):
        await resources.read_resource(AnyUrl("talos://node/health"))


@pytest.mark.asyncio
async def test_write_checks_fresh_node_version_before_dispatch(tmp_path: Path) -> None:
    binary = tmp_path / "talosctl"
    marker = tmp_path / "dispatched"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys\n"
        f"a=sys.argv[1:]\n"
        f"if a[0]=='version': print('Client:\\nTalos v1.14.1\\nServer:\\n  Tag: v1.13.10')\n"
        f"else: open({str(marker)!r},'w').close()\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    client = TalosClient(str(config), profile="write", talosctl=str(binary))
    with pytest.raises(Exception, match="UNSUPPORTED_VERSION"):
        await client.execute_talosctl(
            ["reboot", "-n", "node", "--wait=false"], operation="talos_reboot"
        )
    assert not marker.exists()


@pytest.mark.asyncio
async def test_maintenance_apply_requires_real_fingerprint_and_matching_cli(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    (root / "config.yaml").write_text("machine: {}")
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys,json\n"
        f"a=sys.argv[1:]\n"
        f"print('Client:\\nTalos v1.13.10' if a[0]=='version' else json.dumps(a))\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    client = TalosClient(profile="write", talosctl=str(binary), artifact_root=str(root))
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    base = {
        "node": "127.0.0.1:50001",
        "file": "config.yaml",
        "mode": "auto",
        "insecure": True,
        "target_version": "v1.13.10",
    }
    invalid = await handlers.call_tool(
        "talos_apply_config", {**base, "cert_fingerprint": "not-a-fingerprint"}
    )
    assert invalid.isError is True
    valid = await handlers.call_tool(
        "talos_apply_config",
        {**base, "cert_fingerprint": "4F/lvxSEo7IXUVB8o6MGmgq9DJXhORF+AbXUyaA4Sr0="},
    )
    assert valid.isError is False
    assert valid.structuredContent["outcome"] == "accepted"
    argv = json.loads(valid.content[0].text.strip("`\n"))
    assert "--insecure" in argv and "--cert-fingerprint" in argv


def test_gen_endpoint_accepts_explicit_load_balancer_port() -> None:
    parsed = GenConfigSchema(name="lab", endpoint="https://lb.example.test:443")
    assert parsed.endpoint == "https://lb.example.test:443"


def test_upgrade_accepts_digest_only_and_exact_factory_schematic() -> None:
    digest = "a" * 64
    schematic = "b" * 64
    plain = UpgradeSchema(
        node="node", target_version="v1.14.1", image=f"ghcr.io/siderolabs/installer@sha256:{digest}"
    )
    assert plain.image.endswith(digest)
    factory = UpgradeSchema(
        node="node",
        target_version="v1.14.1",
        schematic_id=schematic,
        image=f"factory.talos.dev/metal-installer/{schematic}@sha256:{digest}",
    )
    assert factory.schematic_id == schematic
    with pytest.raises(ValueError):
        UpgradeSchema(
            node="node",
            target_version="v1.14.1",
            schematic_id="c" * 64,
            image=f"factory.talos.dev/metal-installer/{schematic}@sha256:{digest}",
        )


def test_malformed_talosconfig_does_not_echo_secret_source(tmp_path: Path) -> None:
    config = tmp_path / "talosconfig"
    config.write_text("SENTINEL_SECRET: [broken\n")
    with pytest.raises(ValueError) as raised:
        TalosClient(str(config))
    assert "SENTINEL_SECRET" not in str(raised.value)


@pytest.mark.asyncio
async def test_exited_child_with_inherited_pipe_cannot_hang_cleanup(tmp_path: Path) -> None:
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import subprocess,sys\n"
        f"subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)'])\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    client = TalosClient(profile="readonly", talosctl=str(binary), timeout=1)
    with pytest.raises(Exception, match="TIMEOUT"):
        await asyncio.wait_for(
            client.execute_talosctl(["version", "--client"], operation="talos_version"), 3
        )


@pytest.mark.asyncio
async def test_support_113_none_writes_private_artifact_without_encryption_flag(
    tmp_path: Path,
) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys,json,pathlib\n"
        f"a=sys.argv[1:]\n"
        f"if a[0]=='version': print('Client:\\nTalos v1.13.10\\nServer:\\n  Tag: v1.13.10')\n"
        f"else:\n"
        f" pathlib.Path(a[a.index('--output')+1]).write_text('bundle')\n"
        f" print(json.dumps(a))\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    client = TalosClient(
        str(config), profile="write", talosctl=str(binary), artifact_root=str(root)
    )
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    result = await handlers.call_tool("talos_support", {"node": "node", "encryption": "none"})
    assert result.isError is False
    metadata = json.loads(result.content[0].text)
    assert Path(metadata["path"]).read_text() == "bundle"
    assert json.loads(result.structuredContent["content"][0]["text"]) == metadata
    assert "--no-encryption" not in result.content[0].text


@pytest.mark.asyncio
async def test_snapshot_writes_only_unique_private_output(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys,pathlib\n"
        f"a=sys.argv[1:]\n"
        f"if a[0]=='version': print('Client:\\nTalos v1.13.10\\nServer:\\n  Tag: v1.13.10')\n"
        f"elif a[0]=='etcd': pathlib.Path(a[2]).write_bytes(b'snapshot')\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    client = TalosClient(
        str(config), profile="write", talosctl=str(binary), artifact_root=str(root)
    )
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    result = await handlers.call_tool("talos_etcd_snapshot", {"node": "node"})
    assert result.isError is False
    metadata = json.loads(result.content[0].text)
    assert metadata["size"] == 8
    assert Path(metadata["path"]).read_bytes() == b"snapshot"


@pytest.mark.asyncio
async def test_snapshot_quota_stops_child_during_creation(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys,pathlib,time\n"
        f"a=sys.argv[1:]\n"
        f"if a[0]=='version': print('Client:\\nTalos v1.13.10\\nServer:\\n  Tag: v1.13.10')\n"
        f"elif a[0]=='etcd':\n"
        f" pathlib.Path(a[2]).write_bytes(b'x'*4096)\n"
        f" time.sleep(30)\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    client = TalosClient(
        str(config),
        profile="write",
        talosctl=str(binary),
        artifact_root=str(root),
        artifact_limit=1024,
    )
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    result = await asyncio.wait_for(handlers.call_tool("talos_etcd_snapshot", {"node": "node"}), 5)
    assert result.isError is True
    assert result.structuredContent["code"] == "ARTIFACT_QUOTA"
    assert not list(root.rglob("*"))


@pytest.mark.asyncio
async def test_final_root_quota_rejects_fast_second_artifact_only(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys,pathlib\n"
        f"a=sys.argv[1:]\n"
        f"if a[0]=='version': print('Client:\\nTalos v1.13.10\\nServer:\\n  Tag: v1.13.10')\n"
        f"elif a[0]=='etcd': pathlib.Path(a[2]).write_bytes(b'x'*800)\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    client = TalosClient(
        str(config),
        profile="write",
        talosctl=str(binary),
        artifact_root=str(root),
        artifact_limit=900,
        root_limit=1000,
    )
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    first = await handlers.call_tool("talos_etcd_snapshot", {"node": "node"})
    second = await handlers.call_tool("talos_etcd_snapshot", {"node": "node"})
    assert first.isError is False
    assert second.isError is True
    assert second.structuredContent["code"] == "ARTIFACT_QUOTA"
    assert [path.stat().st_size for path in root.rglob("*") if path.is_file()] == [800]


@pytest.mark.skipif(os.name != "nt", reason="Windows native ACL check")
# Keep native ACL setup and acceptance in one Windows-only fixture.
def test_windows_private_artifact_root_can_be_selected(  # noqa: PLR0915
    tmp_path: Path,
) -> None:
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    advapi.SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    advapi.SetFileSecurityW.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p

    def set_dacl(path: Path, sddl: str, *, set_owner: bool = False) -> None:
        descriptor = ctypes.c_void_p()
        assert advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, 1, ctypes.byref(descriptor), None
        )
        try:
            assert advapi.SetFileSecurityW(str(path), 0x5 if set_owner else 0x4, descriptor)
        finally:
            kernel.LocalFree(descriptor)

    advapi.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    advapi.ConvertSidToStringSidW.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    token = wintypes.HANDLE()
    assert advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x8, ctypes.byref(token))
    try:
        length = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(length))
        info = ctypes.create_string_buffer(length.value)
        assert advapi.GetTokenInformation(token, 1, info, length, ctypes.byref(length))
        sid = ctypes.c_void_p.from_buffer(info).value
        sid_text = ctypes.c_void_p()
        assert advapi.ConvertSidToStringSidW(ctypes.c_void_p(sid), ctypes.byref(sid_text))
        try:
            user = ctypes.wstring_at(sid_text)
        finally:
            kernel.LocalFree(sid_text)
    finally:
        kernel.CloseHandle(token)
    root = tmp_path / "private"
    root.mkdir()
    # Python 3.12+ uses this OWNER RIGHTS DACL for mkdir(mode=0o700).
    set_dacl(root, f"O:{user}D:P(A;;FA;;;OW)(A;;FA;;;SY)(A;;FA;;;BA)", set_owner=True)
    assert windows_private_acl(root) is True
    set_dacl(root, f"D:P(A;;FA;;;{user})(A;;FA;;;SY)(A;;FA;;;BA)(A;;FA;;;OW)")
    assert windows_private_acl(root) is True
    client = TalosClient(profile="write", artifact_root=str(root))
    assert client.artifact_root == root
    set_dacl(root, f"D:P(A;;FA;;;{user})(A;;FA;;;WD)")
    assert windows_private_acl(root) is False


@pytest.mark.asyncio
async def test_events_observation_window_completes_without_timeout_error(tmp_path: Path) -> None:
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys,time\n"
        f"if sys.argv[1]=='version': print('Client:\\nTalos v1.13.10\\n"
        f"Server:\\n  Tag: v1.13.10')\n"
        f"else:\n"
        f" print('event',flush=True)\n"
        f" time.sleep(30)\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    client = TalosClient(str(config), profile="readonly", talosctl=str(binary))
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    result = await asyncio.wait_for(
        handlers.call_tool("talos_events", {"nodes": "node", "tail": 2, "window_seconds": 1}), 4
    )
    assert result.isError is False
    assert result.structuredContent["complete_window"] is True
    assert result.structuredContent["content"][0]["text"] == result.content[0].text
    assert "event" in result.content[0].text


@pytest.mark.asyncio
async def test_support_114_recipients_disable_vendor_defaults(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys,json,pathlib\n"
        f"a=sys.argv[1:]\n"
        f"if a[0]=='version': print('Client:\\nTalos v1.14.1\\nServer:\\n  Tag: v1.14.1')\n"
        f"else:\n"
        f" pathlib.Path(a[a.index('--output')+1]).write_text(json.dumps(a))\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    client = TalosClient(
        str(config), profile="write", talosctl=str(binary), artifact_root=str(root)
    )
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    result = await handlers.call_tool(
        "talos_support",
        {"node": "node", "encryption": "recipients", "recipients": ["age1a", "age1b"]},
    )
    assert result.isError is False
    argv = json.loads(Path(json.loads(result.content[0].text)["path"]).read_text())
    assert argv.count("--encryption-recipients") == 2
    assert "--encryption-no-default-recipients" in argv


@pytest.mark.asyncio
async def test_cgroups_fake_kill_is_invalid_argument(tmp_path: Path) -> None:
    handlers = fixture_handlers(tmp_path, "readonly")
    result = await handlers.call_tool(
        "talos_cgroups", {"nodes": "node", "action": "kill", "cgroup": "system.slice"}
    )
    assert result.isError is True
    assert result.structuredContent["code"] == "INVALID_ARGUMENT"


@pytest.mark.asyncio
async def test_cgroups_and_multinode_reads_preflight_each_node(tmp_path: Path) -> None:
    handlers = fixture_handlers(tmp_path, "readonly")
    cgroups = await handlers.call_tool("talos_cgroups", {"nodes": "node"})
    assert cgroups.isError is False
    assert json.loads(cgroups.content[0].text.strip("`\n"))[:5] == [
        "cgroups",
        "--nodes",
        "node",
        "--preset",
        "cpu",
    ]
    selected = await handlers.call_tool("talos_cgroups", {"nodes": "node", "preset": "memory"})
    assert selected.isError is False
    assert "memory" in json.loads(selected.content[0].text.strip("`\n"))
    stats = await handlers.call_tool("talos_stats", {"nodes": "node,other"})
    assert stats.isError is False
    assert "node,other" in stats.content[0].text


@pytest.mark.asyncio
async def test_total_call_deadline_covers_sequential_node_preflights(tmp_path: Path) -> None:
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys,time\n"
        f"time.sleep(0.2)\n"
        f"if sys.argv[1]=='version': print('Client:\\nTalos v1.13.10\\n"
        f"Server:\\n  Tag: v1.13.10')\n"
        f"else: print('stats')\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node, other]\n")
    client = TalosClient(str(config), profile="readonly", talosctl=str(binary), timeout=0.5)
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    started = asyncio.get_running_loop().time()
    result = await handlers.call_tool("talos_stats", {"nodes": "node,other"})
    elapsed = asyncio.get_running_loop().time() - started
    assert result.isError is True
    assert result.structuredContent["code"] == "TIMEOUT"
    assert elapsed < 0.65


@pytest.mark.asyncio
async def test_mutation_lock_wait_uses_same_deadline_and_does_not_replay(tmp_path: Path) -> None:
    marker = tmp_path / "dispatch"
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import pathlib,signal,sys,time\n"
        f"if sys.argv[1]=='version': print('Client:\\nTalos v1.13.10\\n"
        f"Server:\\n  Tag: v1.13.10')\n"
        f"else:\n"
        f" signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
        f" pathlib.Path({str(marker)!r}).write_text('one')\n"
        f" time.sleep(30)\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    client = TalosClient(str(config), profile="write", talosctl=str(binary), timeout=2.0)
    first = asyncio.create_task(
        client.execute_talosctl(["reboot", "-n", "node", "--wait=false"], operation="talos_reboot")
    )
    await asyncio.to_thread(_wait_for_file, marker)
    started = asyncio.get_running_loop().time()
    with pytest.raises(TalosExecutionError, match="TIMEOUT"):
        await client.execute_talosctl(
            ["reboot", "-n", "node", "--wait=false"], operation="talos_reboot"
        )
    assert asyncio.get_running_loop().time() - started < 2.4
    with pytest.raises(TalosExecutionError, match="OUTCOME_UNKNOWN"):
        await first
    assert marker.read_text() == "one"


@pytest.mark.asyncio
async def test_late_lock_acquisition_refuses_upgrade_before_dispatch(tmp_path: Path) -> None:
    marker = tmp_path / "dispatch"
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import pathlib,sys,time\n"
        f"if sys.argv[1]=='version': print('Client:\\nTalos v1.13.10\\n"
        f"Server:\\n  Tag: v1.13.10')\n"
        f"else:\n"
        f" with open({str(marker)!r},'a') as stream: stream.write(sys.argv[1]+'\\n')\n"
        f" time.sleep(0.25)\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    client = TalosClient(
        str(config), profile="write", talosctl=str(binary), timeout=0.6, upgrade_timeout=0.6
    )
    first = asyncio.create_task(
        client.execute_talosctl(["reboot", "-n", "node", "--wait=false"], operation="talos_reboot")
    )
    await asyncio.to_thread(_wait_for_file, marker)
    image = "ghcr.io/siderolabs/installer@sha256:" + "a" * 64
    with pytest.raises(TalosExecutionError, match="TIMEOUT") as failure:
        await client.execute_talosctl(
            ["upgrade", "-n", "node", "--image", image, "--wait=true", "--drain=true"],
            operation="talos_upgrade",
            target_version="v1.13.10",
        )
    assert failure.value.outcome == "failed"
    await first
    assert marker.read_text().splitlines() == ["reboot"]


@pytest.mark.asyncio
async def test_client_only_version_runs_without_talosconfig(tmp_path: Path) -> None:
    binary = tmp_path / "talosctl"
    binary.write_text(f"#!{sys.executable}\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    client = TalosClient(profile="readonly", talosctl=str(binary))
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    version = await handlers.call_tool("talos_version", {"client_only": True})
    assert version.isError is False
    assert json.loads(version.content[0].text.strip("`\n")) == ["version", "--client"]
    conflict = await handlers.call_tool("talos_version", {"client_only": True, "nodes": "node"})
    assert conflict.isError is True
    assert conflict.structuredContent["code"] == "INVALID_ARGUMENT"


@pytest.mark.asyncio
async def test_version_skew_warning_parses_native_full_output(tmp_path: Path) -> None:
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys\n"
        f"a=sys.argv[1:]\n"
        f"if '--short' in a: print('Client:\\nTalos v1.13.10\\nServer:\\n  Tag: v1.14.1')\n"
        f"else: print('Client:\\n  Tag: v1.13.10\\nServer:\\n  Tag: v1.14.1')\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    client = TalosClient(str(config), profile="readonly", talosctl=str(binary))
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    version = await handlers.call_tool("talos_version", {"nodes": "node"})
    assert version.isError is False
    assert "skew" in version.content[0].text.lower()


@pytest.mark.asyncio
async def test_health_native_wait_is_below_process_deadline(tmp_path: Path) -> None:
    handlers = fixture_handlers(tmp_path, "readonly")
    result = await handlers.call_tool("talos_health", {"nodes": "node"})
    assert result.isError is False
    argv = json.loads(result.content[0].text.strip("`\n"))
    assert "--wait-timeout" in argv
    assert (
        int(argv[argv.index("--wait-timeout") + 1].rstrip("s"))
        < handlers.tools_list[0].client.timeout
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("denial", ["permission denied", "PermissionDenied"])
async def test_permission_error_omits_secret_stderr(tmp_path: Path, denial: str) -> None:
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys\n"
        f"sys.stderr.write('SENTINEL_SECRET {denial}')\n"
        f"sys.exit(1)\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    client = TalosClient(str(config), profile="readonly", talosctl=str(binary))
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    messages: list[str] = []
    sink = logger.add(lambda message: messages.append(str(message)))
    try:
        result = await handlers.call_tool("talos_version", {"nodes": "node"})
    finally:
        logger.remove(sink)
    assert result.isError is True
    assert result.structuredContent["code"] == "PERMISSION_DENIED"
    assert "SENTINEL_SECRET" not in result.model_dump_json()
    assert "SENTINEL_SECRET" not in "".join(messages)
    assert "PERMISSION_DENIED" in "".join(messages)


@pytest.mark.asyncio
async def test_postdispatch_nonzero_mutation_has_unknown_outcome(tmp_path: Path) -> None:
    binary = tmp_path / "talosctl"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys\n"
        f"if sys.argv[1]=='version': print('Client:\\nTalos v1.13.10\\n"
        f"Server:\\n  Tag: v1.13.10')\n"
        f"else: sys.exit(3)\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    client = TalosClient(str(config), profile="write", talosctl=str(binary))
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    result = await handlers.call_tool("talos_reboot", {"node": "node"})
    assert result.isError is True
    assert result.structuredContent["code"] == "OUTCOME_UNKNOWN"
    assert result.structuredContent["outcome"] == "unknown"
    assert result.structuredContent["exit_code"] == 3
    assert json.loads(result.content[0].text) == result.structuredContent


@pytest.mark.asyncio
async def test_112_node_only_allows_transitional_diagnostics(tmp_path: Path) -> None:
    binary = tmp_path / "talosctl"
    marker = tmp_path / "stats-dispatched"
    binary.write_text(
        f"#!{sys.executable}\n"
        f"import sys\n"
        f"a=sys.argv[1:]\n"
        f"if a[0]=='version': print('Client:\\nTalos v1.13.10\\nServer:\\n  Tag: v1.12.9')\n"
        f"elif a[0]=='stats': open({str(marker)!r},'w').close()\n"
        f"else: print('safe result')\n"
        f""
    )
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    client = TalosClient(str(config), profile="readonly", talosctl=str(binary))
    catalog, tool_map = create_tool_registry(client)
    handlers = MCPHandlers(TalosPrompts(client), TalosResources(client), catalog, tool_map)
    blocked = await handlers.call_tool("talos_stats", {"nodes": "node"})
    assert blocked.isError is True
    assert blocked.structuredContent["code"] == "UNSUPPORTED_VERSION"
    assert not marker.exists()
    allowed = await handlers.call_tool(
        "talos_get", {"resource": "runtime/machinestatus", "nodes": "node"}
    )
    assert allowed.isError is False
    assert "skew" in allowed.content[0].text.lower()
