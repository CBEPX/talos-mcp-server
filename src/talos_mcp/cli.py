"""CLI interface for Talos MCP Server."""

import asyncio
import contextlib
import signal
import sys

import anyio
import typer
import uvloop
from loguru import logger
from mcp.server.stdio import stdio_server

from talos_mcp.core.settings import settings


__version__ = "0.3.9"


def version_callback(value: bool) -> None:
    """Show version and exit.

    Args:
        value: True if version flag was provided.
    """
    if value:
        typer.echo(f"talos-mcp-server {__version__}")
        raise typer.Exit()


def configure_logging() -> None:
    """Configure logging with detailed formatting and auditing.

    Uses settings from Settings class for all configuration.
    """
    logger.remove()  # Remove default handler

    # Standard stderr logging
    logger.add(
        sys.stderr,
        format=settings.log_format,
        level=settings.log_level.upper(),
    )

    # Audit log to file
    logger.add(
        settings.audit_log_path,
        rotation=settings.audit_log_rotation,
        retention=settings.audit_log_retention,
        level="DEBUG",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | "
            "{name}:{function}:{line} | {message} | {extra}"
        ),
        serialize=settings.audit_log_serialize,
    )


def run_mcp_server(app_mcp: "Server") -> None:  # noqa: F821
    """Run the MCP server with proper signal handling.

    Args:
        app_mcp: Initialized MCP Server instance.
    """
    shutdown_event = asyncio.Event()

    def signal_handler() -> None:
        """Handle shutdown signals gracefully."""
        logger.info("Received shutdown signal, stopping server...")
        shutdown_event.set()

    async def run_server() -> None:
        """Async server runner with signal handling."""
        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

        try:
            async with stdio_server() as (read_stream, write_stream):
                # Run server with shutdown monitoring
                server_task = asyncio.create_task(
                    app_mcp.run(
                        read_stream,
                        write_stream,
                        app_mcp.create_initialization_options(),
                    )
                )
                shutdown_task = asyncio.create_task(shutdown_event.wait())

                _done, pending = await asyncio.wait(
                    [server_task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
                )

                for task in pending:
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task

                logger.info("Server stopped by user")
        finally:
            # Cleanup signal handlers
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.remove_signal_handler(sig)

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass  # Already handled by signal handler
    except BaseException as e:
        # Handle ExceptionGroup (Python 3.11+) or regular exceptions
        # Filter out BrokenResourceError which is expected during shutdown
        if isinstance(e, anyio.BrokenResourceError):
            pass  # Expected during shutdown
        elif hasattr(e, "exceptions"):
            # ExceptionGroup-like: filter out BrokenResourceError
            real_errors = [
                exc for exc in e.exceptions if not isinstance(exc, anyio.BrokenResourceError)
            ]
            if real_errors:
                logger.exception(f"Server crashed: {e}")
                sys.exit(1)
        elif not isinstance(e, (SystemExit, KeyboardInterrupt)):
            logger.exception(f"Server crashed: {e}")
            sys.exit(1)


cli = typer.Typer()


@cli.command()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        "-l",
        help="Log level (DEBUG, INFO, WARNING, ERROR)",
        envvar="TALOS_MCP_LOG_LEVEL",
    ),
    audit_log: str = typer.Option(
        None,
        "--audit-log",
        help="Path to audit log file",
        envvar="TALOS_MCP_AUDIT_LOG_PATH",
    ),
    readonly: bool = typer.Option(
        False,
        "--readonly",
        help="Enable read-only mode (prevents mutating commands)",
        envvar="TALOS_MCP_READONLY",
    ),
) -> None:
    """Run the Talos MCP Server."""
    # Import here to avoid circular imports
    from talos_mcp.server import app_mcp

    # Update global settings from CLI args
    settings.log_level = log_level
    if audit_log:
        settings.audit_log_path = audit_log
    settings.readonly = readonly

    configure_logging()
    uvloop.install()
    logger.info(f"Starting Talos MCP Server with log level {settings.log_level}")

    # Hint for users running interactively
    if sys.stdin.isatty():
        sys.stderr.write(
            "\n⚠️  This server expects JSON-RPC input from MCP clients "
            "(e.g., Claude Desktop).\n"
            "    Press Ctrl+C to exit.\n\n"
        )

    run_mcp_server(app_mcp)
