"""Custom exceptions for Talos MCP Server."""

from enum import Enum


class ErrorCode(Enum):
    """Structured error codes for Talos MCP Server."""

    # General errors (1xx)
    UNKNOWN = 100
    INTERNAL_ERROR = 101
    CONFIGURATION_ERROR = 102

    # Connection errors (2xx)
    CONNECTION_FAILED = 200
    TIMEOUT = 201
    AUTHENTICATION_FAILED = 202
    NODE_UNREACHABLE = 203

    # Command errors (3xx)
    COMMAND_FAILED = 300
    COMMAND_NOT_FOUND = 301
    INVALID_ARGUMENTS = 302
    PERMISSION_DENIED = 303
    READONLY_VIOLATION = 304

    # Resource errors (4xx)
    RESOURCE_NOT_FOUND = 400
    RESOURCE_UNAVAILABLE = 401
    RESOURCE_BUSY = 402

    # Validation errors (5xx)
    VALIDATION_FAILED = 500
    INVALID_CONFIG = 501
    SCHEMA_VALIDATION_FAILED = 502


class TalosError(Exception):
    """Base exception for all Talos MCP errors."""

    def __init__(self, message: str, code: ErrorCode = ErrorCode.UNKNOWN):
        """Initialize TalosError.

        Args:
            message: Error message.
            code: Structured error code.
        """
        self.code = code
        self.message = message
        super().__init__(message)

    def to_dict(self) -> dict[str, str | int]:
        """Convert error to dictionary for structured logging.

        Returns:
            Dictionary with error details.
        """
        return {
            "error": self.message,
            "code": self.code.value,
            "code_name": self.code.name,
        }


class TalosConnectionError(TalosError):
    """Raised when unable to connect to a Talos node."""

    def __init__(self, message: str, code: ErrorCode = ErrorCode.CONNECTION_FAILED):
        """Initialize TalosConnectionError.

        Args:
            message: Error message.
            code: Specific connection error code.
        """
        super().__init__(message, code)


class TalosCommandError(TalosError):
    """Raised when a talosctl command fails."""

    def __init__(
        self,
        cmd: list[str],
        returncode: int,
        stderr: str,
        code: ErrorCode = ErrorCode.COMMAND_FAILED,
    ):
        """Initialize TalosCommandError.

        Args:
            cmd: Command that failed.
            returncode: Command return code.
            stderr: Standard error output.
            code: Specific error code.
        """
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr

        # Infer error code from return code if not specified
        if code == ErrorCode.COMMAND_FAILED:
            if returncode == 127:
                code = ErrorCode.COMMAND_NOT_FOUND
            elif returncode == 126:
                code = ErrorCode.PERMISSION_DENIED
            elif returncode == 124 or returncode == 143:
                code = ErrorCode.TIMEOUT
            elif "not found" in stderr.lower():
                code = ErrorCode.RESOURCE_NOT_FOUND
            elif "permission denied" in stderr.lower():
                code = ErrorCode.PERMISSION_DENIED
            elif "readonly" in stderr.lower():
                code = ErrorCode.READONLY_VIOLATION

        message = f"Command failed with code {returncode}: {stderr}"
        super().__init__(message, code)

    def to_dict(self) -> dict[str, str | int | list[str]]:
        """Convert error to dictionary for structured logging.

        Returns:
            Dictionary with error details including command.
        """
        base_dict = super().to_dict()
        base_dict.update(
            {
                "command": self.cmd,
                "returncode": self.returncode,
                "stderr": self.stderr,
            }
        )
        return base_dict
