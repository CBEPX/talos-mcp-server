"""Custom exceptions for Talos MCP Server."""

class TalosError(Exception):
    """Base exception for all Talos MCP errors."""
    pass

class TalosConnectionError(TalosError):
    """Raised when unable to connect to a Talos node."""
    pass

class TalosCommandError(TalosError):
    """Raised when a talosctl command fails."""
    def __init__(self, cmd: list[str], returncode: int, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command failed with code {returncode}: {stderr}")
