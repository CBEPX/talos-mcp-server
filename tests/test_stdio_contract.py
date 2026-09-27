"""Real stdio MCP profile and typed failure boundary."""

import json
import os
import select
import signal
import stat
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl


def test_offline_readonly_stdio_catalog_and_errors(tmp_path: Path) -> None:
    """An offline launch exposes only explicit canonical tools and typed errors."""

    async def check() -> None:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(tmp_path),
            "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        }
        server = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "talos_mcp.server",
                "--profile",
                "readonly",
                "--allow-tools",
                "talos_version,talos_config_info",
                "--skip-health-check",
            ],
            env=env,
            cwd=tmp_path,
        )
        with anyio.fail_after(15):
            async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                assert {tool.name for tool in tools} == {"talos_version", "talos_config_info"}
                templates = (await session.list_resource_templates()).resourceTemplates
                assert {str(item.uriTemplate) for item in templates} == {
                    "talos://{node}/version",
                    "talos://{node}/config",
                }
                info = await session.call_tool("talos_config_info", {})
                assert info.isError is False
                assert info.structuredContent["content"][0]["text"] == info.content[0].text
                missing = await session.call_tool("talos_version", {"nodes": "node"})
                assert missing.isError is True
                assert missing.structuredContent["code"] == "CONFIG_REQUIRED"
                assert json.loads(missing.content[0].text) == missing.structuredContent
                disabled = await session.call_tool("talos_reboot", {"node": "node"})
                assert disabled.isError is True
                assert disabled.structuredContent["code"] == "TOOL_NOT_ENABLED"

    anyio.run(check)
    assert not list(tmp_path.glob("*audit*"))


def test_opt_in_audit_contains_only_metadata(tmp_path: Path) -> None:
    """An explicit audit sink records calls without arguments or response data."""

    async def check() -> None:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(tmp_path),
            "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        }
        server = StdioServerParameters(
            command=sys.executable,
            args=[
                "-m",
                "talos_mcp.server",
                "--allow-tools",
                "talos_config_info",
                "--audit-log",
                str(tmp_path / "audit.log"),
            ],
            env=env,
            cwd=tmp_path,
        )
        with anyio.fail_after(15):
            async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                await session.call_tool("talos_config_info", {"secret": "SENTINEL_SECRET"})
                await session.read_resource(AnyUrl("talos://node/config"))

    anyio.run(check)
    audit = (tmp_path / "audit.log").read_text()
    assert "talos_config_info" in audit
    assert "SENTINEL_SECRET" not in audit
    assert "duration_ms" in audit and "response_bytes" in audit
    records = [json.loads(line) for line in audit.splitlines()]
    assert any(record.get("code") == "INVALID_ARGUMENT" for record in records)
    assert any(
        record.get("resource") == "config" and record.get("outcome") == "complete"
        for record in records
    )


@pytest.mark.skipif(os.name != "posix", reason="POSIX process group EOF regression")
@pytest.mark.parametrize("mode", ["eof", "notification"])
# Keep the transport, cancellation, and child-readback in one lifecycle check.
def test_stdio_cancel_reaps_term_resistant_mutation(  # noqa: PLR0915
    tmp_path: Path, mode: str
) -> None:
    """Real JSON-RPC cancellation and EOF must wait for the owned child."""
    fixture = tmp_path / "talosctl"
    pidfile = tmp_path / "pid"
    fixture.write_text(
        f"#!{sys.executable}\n"
        f"import os,pathlib,signal,sys,time\n"
        f"if sys.argv[1]=='version': print('Client:\\nTalos v1.13.10\\n"
        f"Server:\\n  Tag: v1.13.10')\n"
        f"else:\n"
        f" signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
        f" pathlib.Path({str(pidfile)!r}).write_text(str(os.getpid()))\n"
        f" time.sleep(60)\n"
        f""
    )
    fixture.chmod(fixture.stat().st_mode | stat.S_IXUSR)
    config = tmp_path / "talosconfig"
    config.write_text("context: lab\ncontexts:\n  lab:\n    nodes: [node]\n")
    audit_log = tmp_path / "audit.log"
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "talos_mcp.server",
            "--profile",
            "write",
            "--allow-tools",
            "talos_reboot",
            "--talosctl",
            str(fixture),
            "--talosconfig",
            str(config),
            "--audit-log",
            str(audit_log),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    assert server.stdin is not None and server.stdout is not None
    child_pid = None
    try:

        def send(message: dict) -> None:
            server.stdin.write(json.dumps(message) + "\n")
            server.stdin.flush()

        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1"},
                },
            }
        )
        assert select.select([server.stdout], [], [], 5)[0]
        assert "result" in json.loads(server.stdout.readline())
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "talos_reboot", "arguments": {"node": "node"}},
            }
        )
        limit = time.monotonic() + 5
        while not pidfile.exists() and time.monotonic() < limit:
            time.sleep(0.02)
        assert pidfile.exists()
        child_pid = int(pidfile.read_text())
        if mode == "notification":
            send(
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/cancelled",
                    "params": {"requestId": 2, "reason": "test"},
                }
            )
            until = time.monotonic() + 8
            while time.monotonic() < until:
                try:
                    os.kill(child_pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.05)
        server.stdin.close()
        assert server.wait(timeout=10) == 0
        records = [json.loads(line) for line in audit_log.read_text().splitlines()]
        assert any(
            item.get("phase") == "dispatch" and item.get("tool") == "talos_reboot"
            for item in records
        )
        assert any(
            item.get("phase") == "cancelled" and item.get("tool") == "talos_reboot"
            for item in records
        )
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
    finally:
        if server.poll() is None:
            server.kill()
            server.wait(timeout=5)
        if server.stdin and not server.stdin.closed:
            server.stdin.close()
        if server.stdout:
            server.stdout.close()
        if server.stderr:
            server.stderr.close()
        if child_pid is not None:
            with suppress(ProcessLookupError):
                os.kill(child_pid, signal.SIGKILL)
