"""Install a built wheel and exercise real stdio with a pinned native talosctl."""

import argparse
import asyncio
import csv
import ctypes
import hashlib
import json
import os
import platform
import queue
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import suppress
from ctypes import wintypes
from pathlib import Path

import anyio
import httpx
import yaml
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl


ROOT = Path(__file__).resolve().parents[1]


def run(*command: str) -> str:
    """Run one setup command and include its diagnostics on failure."""
    result = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    if result.returncode:
        raise RuntimeError(f"{command[0]} failed: {result.stdout}\n{result.stderr}")
    return result.stdout


def windows_user_sid() -> str:
    """Read the account SID used for private Windows test artifacts."""
    return next(csv.reader(run("whoami", "/user", "/fo", "csv", "/nh").splitlines()))[1]


def windows_default_owner() -> None:
    """Make this smoke process and its children create user-owned objects."""
    if os.name != "nt":
        return
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    pointer = ctypes.c_void_p

    class TokenOwner(ctypes.Structure):
        _fields_ = [("Owner", pointer)]

    advapi.ConvertStringSidToSidW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(pointer)]
    advapi.ConvertStringSidToSidW.restype = wintypes.BOOL
    advapi.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        pointer,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    advapi.SetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        pointer,
        wintypes.DWORD,
    ]
    advapi.SetTokenInformation.restype = wintypes.BOOL
    advapi.EqualSid.argtypes = [pointer, pointer]
    advapi.EqualSid.restype = wintypes.BOOL
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [pointer]
    kernel.LocalFree.restype = pointer

    user_sid = pointer()
    if not advapi.ConvertStringSidToSidW(windows_user_sid(), ctypes.byref(user_sid)):
        raise ctypes.WinError(ctypes.get_last_error())
    token = wintypes.HANDLE()
    try:
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 0x88, ctypes.byref(token)):
            raise ctypes.WinError(ctypes.get_last_error())

        def owner_is_user() -> bool:
            required = wintypes.DWORD()
            advapi.GetTokenInformation(token, 4, None, 0, ctypes.byref(required))
            if not required.value:
                raise ctypes.WinError(ctypes.get_last_error())
            buffer = ctypes.create_string_buffer(required.value)
            if not advapi.GetTokenInformation(token, 4, buffer, required, ctypes.byref(required)):
                raise ctypes.WinError(ctypes.get_last_error())
            owner_sid = pointer.from_buffer(buffer)
            return bool(advapi.EqualSid(owner_sid, user_sid))

        print(f"Windows smoke token owner is account before: {owner_is_user()}", flush=True)
        owner = TokenOwner(user_sid)
        if not advapi.SetTokenInformation(token, 4, ctypes.byref(owner), ctypes.sizeof(owner)):
            raise ctypes.WinError(ctypes.get_last_error())
        assert owner_is_user(), "Windows smoke token owner did not become the account SID"
        print("Windows smoke token owner is account after: True", flush=True)
    finally:
        if token.value:
            kernel.CloseHandle(token)
        kernel.LocalFree(user_sid)


def windows_acl_readback(path: Path) -> None:
    """Show the owner and full ACL of one task-owned Windows test directory."""
    quoted = str(path).replace("'", "''")
    owner = run("pwsh", "-NoProfile", "-Command", f"(Get-Acl -LiteralPath '{quoted}').Owner")
    print(f"Windows smoke {path.name} owner: {owner.strip()}", flush=True)
    print(f"Windows smoke {path.name} ACL:\n{run('icacls', str(path))}", flush=True)


def download_talosctl(version: str, directory: Path) -> Path:
    """Download one release asset and compare its digest with the source pin."""
    system = {"Darwin": "darwin", "Linux": "linux", "Windows": "windows"}[platform.system()]
    machine = {"x86_64": "amd64", "AMD64": "amd64", "aarch64": "arm64", "arm64": "arm64"}[
        platform.machine()
    ]
    asset = f"talosctl-{system}-{machine}" + (".exe" if system == "windows" else "")
    pins = {
        (parts[1], parts[2]): parts[0]
        for line in (ROOT / "talosctl-checksums.txt").read_text().splitlines()
        if (parts := line.split()) and not line.startswith("#")
    }
    expected = pins[(version, asset)]
    target = directory / ("talosctl.exe" if system == "windows" else "talosctl")
    url = f"https://github.com/siderolabs/talos/releases/download/{version}/{asset}"
    with httpx.stream("GET", url, follow_redirects=True, timeout=60) as source:
        source.raise_for_status()
        with target.open("wb") as output:
            for chunk in source.iter_bytes():
                output.write(chunk)
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual != expected:
        raise AssertionError(f"{asset}: checksum mismatch")
    target.chmod(target.stat().st_mode | stat.S_IXUSR)
    return target


def private_artifact_root(root: Path) -> None:
    """Give the current Windows account a private ACL or set POSIX mode 0700."""
    root.mkdir()
    if os.name != "nt":
        root.chmod(0o700)
        return
    sid = windows_user_sid()
    run("icacls", str(root), "/inheritance:r")
    run("icacls", str(root), "/grant:r", f"*{sid}:(OI)(CI)F")
    windows_acl_readback(root)


def windows_process_ids() -> set[int]:
    """Read native talosctl PIDs on an isolated Windows CI runner."""
    rows = csv.reader(run("tasklist", "/FO", "CSV", "/NH").splitlines())
    return {int(row[1]) for row in rows if len(row) > 1 and row[0].lower() == "talosctl.exe"}


def native_process_ids(talosctl: Path) -> set[int]:
    """Find only this smoke's native CLI children on POSIX or Windows."""
    if os.name == "nt":
        return windows_process_ids()
    output = run("ps", "-axo", "pid=,command=")
    path = str(talosctl)
    return {
        int(pid)
        for line in output.splitlines()
        if len(parts := line.strip().split(None, 1)) == 2
        for pid, command in [parts]
        if command == path or command.startswith(path + " ")
    }


def native_pid_alive(pid: int) -> bool:
    """Check an exact spawned PID after cancellation or EOF."""
    if os.name == "nt":
        return pid in windows_process_ids()
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def wait_native_spawn(talosctl: Path, before: set[int]) -> set[int]:
    """Require a real new CLI process before testing its cleanup."""
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        spawned = native_process_ids(talosctl) - before
        if spawned:
            return spawned
        time.sleep(0.1)
    raise AssertionError("native talosctl did not start")


def wait_native_gone(pids: set[int]) -> None:
    """Require all observed native children to be reaped within ten seconds."""
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if not any(native_pid_alive(pid) for pid in pids):
            return
        time.sleep(0.1)
    raise AssertionError(f"native talosctl survived cancellation or EOF: {sorted(pids)}")


async def check_windows_artifact_rejection(
    session: ClientSession, controlplane: Path, reviewed: str
) -> None:
    """Reject broad access and a foreign owner on a generated native artifact."""
    run("icacls", str(controlplane), "/grant", "*S-1-1-0:R")
    try:
        rejected = await session.call_tool("talos_validate_config", {"file": reviewed})
        assert rejected.isError, rejected
        assert rejected.structuredContent["code"] == "ARTIFACT_INVALID"
    finally:
        run("icacls", str(controlplane), "/remove", "*S-1-1-0")
    run("icacls", str(controlplane), "/setowner", "*S-1-5-32-544")
    try:
        rejected = await session.call_tool("talos_validate_config", {"file": reviewed})
        assert rejected.isError, rejected
        assert rejected.structuredContent["code"] == "ARTIFACT_INVALID"
    finally:
        run("icacls", str(controlplane), "/setowner", f"*{windows_user_sid()}")


async def check_mcp(executable: Path, talosctl: Path, root: Path, compatibility_only: bool) -> None:
    """Use the installed entry point and SDK to check native offline behavior."""
    tools = "talos_version,talos_config_info"
    if not compatibility_only:
        tools += ",talos_gen_config,talos_validate_config"
    env = os.environ.copy()
    env.pop("TALOSCONFIG", None)
    env["HOME"] = str(root)
    server = StdioServerParameters(
        command=str(executable),
        args=[
            "--profile",
            "write",
            "--allow-tools",
            tools,
            "--talosctl",
            str(talosctl),
            "--artifact-root",
            str(root),
            "--skip-health-check",
        ],
        env=env,
        cwd=root,
    )
    with anyio.fail_after(90):
        async with (
            stdio_client(server) as (reader, writer),
            ClientSession(reader, writer) as session,
        ):
            initialized = await session.initialize()
            assert initialized.serverInfo.version == "0.4.0"
            names = {item.name for item in (await session.list_tools()).tools}
            assert names == set(tools.split(","))
            assert (await session.list_prompts()).prompts
            assert (await session.get_prompt("diagnose_cluster")).messages
            templates = await session.list_resource_templates()
            assert {str(item.uriTemplate) for item in templates.resourceTemplates} == {
                "talos://{node}/version",
                "talos://{node}/config",
            }
            assert (await session.read_resource(AnyUrl("talos://node/config"))).contents
            disabled = await session.call_tool("talos_reboot", {"node": "node"})
            assert disabled.isError and disabled.structuredContent["code"] == "TOOL_NOT_ENABLED"
            assert json.loads(disabled.content[0].text) == disabled.structuredContent
            invalid = await session.call_tool("talos_version", {"client_only": True, "extra": 1})
            assert invalid.isError and invalid.structuredContent["code"] == "INVALID_ARGUMENT"
            version = await session.call_tool("talos_version", {"client_only": True})
            assert not version.isError, version
            assert version.structuredContent["content"][0]["text"] == version.content[0].text
            if compatibility_only:
                return
            generated = await session.call_tool(
                "talos_gen_config", {"name": "wheel-smoke", "endpoint": "https://127.0.0.1:6443"}
            )
            assert not generated.isError, generated
            assert generated.structuredContent["content"][0]["text"] == generated.content[0].text
            files = json.loads(generated.content[0].text)
            assert len(files) >= 3
            for item in files:
                file = Path(item["path"])
                assert file.is_file() and file.is_relative_to(root)
                assert item["locality"] == "server"
                assert item["size"] == file.stat().st_size
                assert item["sha256"] == hashlib.sha256(file.read_bytes()).hexdigest()
                if os.name != "nt":
                    assert stat.S_IMODE(file.stat().st_mode) == 0o600
            controlplane = next(
                Path(item["path"])
                for item in files
                if Path(item["path"]).name == "controlplane.yaml"
            )
            reviewed = str(controlplane.relative_to(root))
            validated = await session.call_tool("talos_validate_config", {"file": reviewed})
            assert not validated.isError, validated
            if os.name == "nt":
                await check_windows_artifact_rejection(session, controlplane, reviewed)


# One native subprocess test owns the TLS stall, notification, EOF, and PID readback.
def check_native_cleanup(executable: Path, talosctl: Path, root: Path) -> None:  # noqa: PLR0915
    """Cancellation and EOF must each reap a real CLI blocked on local TLS."""
    controlplane = next(root.glob("talos-mcp-*/talosconfig"))
    data = yaml.safe_load(controlplane.read_text())
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(16)
    port = listener.getsockname()[1]
    context = data["context"]
    data["contexts"][context]["endpoints"] = [f"127.0.0.1:{port}"]
    config = root / "blocked-talosconfig"
    config.write_text(yaml.safe_dump(data))
    stopped = threading.Event()
    connections: list[socket.socket] = []

    def accept() -> None:
        listener.settimeout(0.2)
        while not stopped.is_set():
            try:
                connection, _ = listener.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            connections.append(connection)

    thread = threading.Thread(target=accept, daemon=True)
    thread.start()
    before = native_process_ids(talosctl)
    server = subprocess.Popen(
        [
            str(executable),
            "--profile",
            "readonly",
            "--allow-tools",
            "talos_version",
            "--talosctl",
            str(talosctl),
            "--talosconfig",
            str(config),
            "--timeout",
            "30",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env={**os.environ, "TALOSCONFIG": ""},
    )
    assert server.stdin and server.stdout and server.stderr
    responses: queue.Queue[dict[str, object]] = queue.Queue()

    def collect() -> None:
        for line in server.stdout:
            responses.put(json.loads(line))

    reader = threading.Thread(target=collect, daemon=True)
    reader.start()

    def send(message: dict[str, object]) -> None:
        assert server.stdin is not None
        server.stdin.write(json.dumps(message) + "\n")
        server.stdin.flush()

    def response(request_id: int) -> dict[str, object]:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                message = responses.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty as exc:
                raise AssertionError(f"MCP response {request_id} timed out") from exc
            if message.get("id") == request_id:
                return message
        raise AssertionError(f"MCP response {request_id} timed out")

    def version_call(request_id: int) -> None:
        send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {
                    "name": "talos_version",
                    "arguments": {"nodes": f"127.0.0.1:{port}"},
                },
            }
        )

    try:
        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "wheel-smoke", "version": "1"},
                },
            }
        )
        assert "result" in response(1)
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        version_call(2)
        cancelled = wait_native_spawn(talosctl, before)
        send(
            {
                "jsonrpc": "2.0",
                "method": "notifications/cancelled",
                "params": {"requestId": 2, "reason": "native smoke"},
            }
        )
        wait_native_gone(cancelled)
        send({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        listed = response(3)
        assert "result" in listed and "talos_version" in json.dumps(listed)
        after_cancel = native_process_ids(talosctl)
        version_call(4)
        eof_child = wait_native_spawn(talosctl, after_cancel)
        server.stdin.close()
        assert server.wait(timeout=15) == 0
        wait_native_gone(eof_child)
    finally:
        stopped.set()
        listener.close()
        for connection in connections:
            connection.close()
        thread.join(timeout=2)
        if server.poll() is None:
            server.kill()
            server.wait(timeout=5)
        for pid in native_process_ids(talosctl) - before:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/T", "/F"],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
            else:
                with suppress(ProcessLookupError):
                    os.kill(pid, signal.SIGKILL)
        if not server.stdin.closed:
            server.stdin.close()
        server.stdout.close()
        server.stderr.close()
        reader.join(timeout=2)


def main() -> None:
    """Build an isolated install from a wheel, then run the installed smoke."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--sdk", choices=("minimum", "current"), default="current")
    parser.add_argument("--talos-version", default=(ROOT / ".talosctl-version").read_text().strip())
    parser.add_argument("--inside", action="store_true")
    parser.add_argument("--server", type=Path)
    parser.add_argument("--talosctl", type=Path)
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    windows_default_owner()
    if args.inside:
        assert args.server and args.talosctl and args.artifacts
        asyncio.run(
            check_mcp(
                args.server, args.talosctl, args.artifacts, args.talos_version.startswith("v1.12.")
            )
        )
        if not args.talos_version.startswith("v1.12."):
            check_native_cleanup(args.server, args.talosctl, args.artifacts)
        print("wheel stdio native smoke passed")
        return
    assert args.wheel, "pass --wheel with one built wheel or wheel directory"
    if args.wheel.is_dir():
        wheels = list(args.wheel.glob("talos_mcp_server-*.whl"))
        assert len(wheels) == 1, wheels
        args.wheel = wheels[0]
    assert args.wheel.is_file(), args.wheel
    with tempfile.TemporaryDirectory(prefix="talos-mcp-wheel-") as temp:
        directory = Path(temp).resolve()
        talosctl = download_talosctl(args.talos_version, directory)
        venv = directory / "venv"
        run("uv", "venv", "--python", sys.executable, str(venv))
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        entry = venv / (
            "Scripts/talos-mcp-server.exe" if os.name == "nt" else "bin/talos-mcp-server"
        )
        run("uv", "pip", "install", "--python", str(python), str(args.wheel.resolve()))
        if args.sdk == "minimum":
            run("uv", "pip", "install", "--python", str(python), "mcp==1.30.0")
        else:
            run("uv", "pip", "install", "--python", str(python), "mcp>=1.30,<2")
        root = directory / "artifacts"
        private_artifact_root(root)
        if os.name == "nt":
            probe = Path(tempfile.mkdtemp(prefix="acl-probe-", dir=root))
            try:
                windows_acl_readback(probe)
            finally:
                probe.rmdir()
        run(
            str(python),
            str(Path(__file__).resolve()),
            "--inside",
            "--server",
            str(entry),
            "--talosctl",
            str(talosctl),
            "--artifacts",
            str(root),
            "--talos-version",
            args.talos_version,
        )


if __name__ == "__main__":
    main()
