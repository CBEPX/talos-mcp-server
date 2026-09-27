"""Real stdio discovery smoke test without a Talos cluster."""

import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool


async def _initialize_and_list(server: StdioServerParameters) -> tuple[str, list[Tool]]:
    with anyio.fail_after(15):
        async with (
            stdio_client(server) as (read, write),
            ClientSession(read, write) as session,
        ):
            initialized = await session.initialize()
            tools = (await session.list_tools()).tools
    return initialized.serverInfo.version, tools


def test_stdio_lists_every_registered_tool_without_talosconfig(tmp_path: Path) -> None:
    """All registered tool schemas must serialize in a real tools/list response."""
    env = {
        "HOME": str(tmp_path),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "talos_mcp.server", "--skip-health-check"],
        env=env,
        cwd=tmp_path,
    )
    _, tools = anyio.run(_initialize_and_list, server)

    names = {tool.name for tool in tools}
    assert len(names) >= 20
    assert "talos_support" not in names
    assert "talos_version" in names
    assert "talos_apply" not in names
    assert all(tool.inputSchema.get("type") == "object" for tool in tools)
    assert all(tool.inputSchema.get("additionalProperties") is False for tool in tools)


def test_installed_wheel_initializes_with_package_version(tmp_path: Path) -> None:
    """An isolated offline wheel install using prepared dependencies exposes MCP tools."""
    repo = Path(__file__).resolve().parents[1]
    wheels = tmp_path / "wheels"
    venv = tmp_path / "venv"
    scripts = venv / ("Scripts" if os.name == "nt" else "bin")
    uv = shutil.which("uv")
    assert uv is not None
    build_env = {
        name: os.environ[name]
        for name in ("PATH", "HOME", "XDG_CACHE_HOME", "UV_CACHE_DIR")
        if name in os.environ
    }
    build = subprocess.run(
        [
            uv,
            "build",
            "--offline",
            "--no-build-isolation",
            "--python",
            sys.executable,
            "--wheel",
            "--out-dir",
            str(wheels),
            str(repo),
        ],
        cwd=tmp_path,
        env=build_env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    built_wheels = list(wheels.glob("talos_mcp_server-*.whl"))
    assert len(built_wheels) == 1, built_wheels

    for command in (
        [uv, "venv", "--python", sys.executable, str(venv)],
        [
            uv,
            "pip",
            "install",
            "--offline",
            "--no-deps",
            "--python",
            str(scripts / ("python.exe" if os.name == "nt" else "python")),
            str(built_wheels[0]),
        ],
    ):
        result = subprocess.run(
            command,
            cwd=tmp_path,
            env=build_env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    # The nested venv does not inherit the parent's installed dependencies.
    # Add only that dependency path after the nested venv's own site-packages.
    site_dir = (
        "Lib/site-packages"
        if os.name == "nt"
        else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
    )
    venv_site = venv / site_dir
    (venv_site / "test-dependencies.pth").write_text(sysconfig.get_path("purelib") + "\n")

    executable = scripts / ("talos-mcp-server.exe" if os.name == "nt" else "talos-mcp-server")
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(tmp_path),
    }
    result = subprocess.run(
        [executable, "--version"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "talos-mcp-server 0.4.0"

    server = StdioServerParameters(
        command=str(executable), args=["--skip-health-check"], env=env, cwd=tmp_path
    )
    version, tools = anyio.run(_initialize_and_list, server)

    assert version == "0.4.0"
    assert len({tool.name for tool in tools}) >= 20
    assert "talos_support" not in {tool.name for tool in tools}
