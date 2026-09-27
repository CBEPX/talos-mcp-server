"""Portable CLI for the Talos MCP stdio server."""

import asyncio
import contextlib
import signal
import sys
from typing import TYPE_CHECKING

import typer
from loguru import logger
from mcp.server.stdio import stdio_server

from talos_mcp import __version__
from talos_mcp.core.client import TalosClient


if TYPE_CHECKING:
    from mcp.server import Server


cli = typer.Typer()


def version_callback(value: bool) -> None:
    """Print the installed package version and exit."""
    if value:
        typer.echo(f"talos-mcp-server {__version__}")
        raise typer.Exit()


def configure_logging(level: str, audit_log: str | None) -> None:
    """Send diagnostics only to stderr and opt-in audit records to a file."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=level.upper(),
        format="{level}: {message}",
        filter=lambda record: not record["extra"].get("audit"),
    )
    if audit_log:
        logger.add(
            audit_log,
            level="INFO",
            filter=lambda record: bool(record["extra"].get("audit")),
            format="{message}",
        )


def run_mcp_server(app: "Server", client: TalosClient) -> None:
    """Serve MCP until EOF or signal, then stop every owned child."""

    async def run() -> None:
        shutdown = asyncio.Event()
        loop = asyncio.get_running_loop()
        installed: list[signal.Signals] = []
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, shutdown.set)
                installed.append(sig)
            except (NotImplementedError, RuntimeError):
                pass
        try:
            async with stdio_server() as (reader, writer):
                running = asyncio.create_task(
                    app.run(reader, writer, app.create_initialization_options())
                )
                stopping = asyncio.create_task(shutdown.wait())
                done, pending = await asyncio.wait(
                    (running, stopping), return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
                if running in done:
                    await running
        finally:
            await client.close()
            for sig in installed:
                loop.remove_signal_handler(sig)

    asyncio.run(run())


@cli.command()
def main(
    version: bool = typer.Option(
        False, "--version", "-V", callback=version_callback, is_eager=True
    ),
    profile: str = typer.Option("readonly", "--profile", envvar="TALOS_MCP_PROFILE"),
    allow_tools: str | None = typer.Option(None, "--allow-tools", envvar="TALOS_MCP_ALLOW_TOOLS"),
    readonly: bool | None = typer.Option(
        None, "--readonly/--no-readonly", envvar="TALOS_MCP_READONLY"
    ),
    talosctl: str | None = typer.Option(None, "--talosctl", envvar="TALOS_MCP_TALOSCTL"),
    talosconfig: str | None = typer.Option(None, "--talosconfig", envvar="TALOS_MCP_TALOSCONFIG"),
    context: str | None = typer.Option(None, "--context", envvar="TALOS_MCP_CONTEXT"),
    artifact_root: str | None = typer.Option(
        None, "--artifact-root", envvar="TALOS_MCP_ARTIFACT_ROOT"
    ),
    timeout: float = typer.Option(60, "--timeout", envvar="TALOS_MCP_TIMEOUT"),
    artifact_timeout: float = typer.Option(
        600, "--artifact-timeout", envvar="TALOS_MCP_ARTIFACT_TIMEOUT"
    ),
    upgrade_timeout: float = typer.Option(
        600, "--upgrade-timeout", envvar="TALOS_MCP_UPGRADE_TIMEOUT"
    ),
    output_limit: int = typer.Option(256 * 1024, "--output-limit", envvar="TALOS_MCP_OUTPUT_LIMIT"),
    artifact_limit: int = typer.Option(
        512 * 1024 * 1024, "--artifact-limit", envvar="TALOS_MCP_ARTIFACT_LIMIT"
    ),
    root_limit: int = typer.Option(
        4 * 1024 * 1024 * 1024, "--root-limit", envvar="TALOS_MCP_ROOT_LIMIT"
    ),
    log_level: str = typer.Option("INFO", "--log-level", envvar="TALOS_MCP_LOG_LEVEL"),
    audit_log: str | None = typer.Option(None, "--audit-log", envvar="TALOS_MCP_AUDIT_LOG_PATH"),
    skip_health_check: bool = typer.Option(
        False, "--skip-health-check", envvar="TALOS_MCP_SKIP_HEALTH_CHECK"
    ),
) -> None:
    """Run Talos MCP over stdio with an explicit execution profile."""
    _ = (version, skip_health_check)
    configure_logging(log_level, audit_log)
    if readonly is True and profile == "write":
        raise typer.BadParameter("--readonly conflicts with --profile write")
    if readonly is False:
        logger.warning("--no-readonly is deprecated and leaves the readonly profile active")
    if readonly is True:
        profile = "readonly"
    names = [part.strip() for part in allow_tools.split(",")] if allow_tools is not None else None
    try:
        client = TalosClient(
            config_path=talosconfig,
            profile=profile,
            allow_tools=names,
            talosctl=talosctl,
            context=context,
            artifact_root=artifact_root,
            timeout=timeout,
            artifact_timeout=artifact_timeout,
            upgrade_timeout=upgrade_timeout,
            output_limit=output_limit,
            artifact_limit=artifact_limit,
            root_limit=root_limit,
            audit_enabled=bool(audit_log),
        )
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    from talos_mcp.server import create_server

    app = create_server(client)
    if sys.stdin.isatty():
        sys.stderr.write("Talos MCP expects a stdio MCP client.\n")
    run_mcp_server(app, client)
