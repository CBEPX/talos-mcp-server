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

    # User-friendly error messages mapped by error code
    USER_MESSAGES: dict[ErrorCode, str] = {
        ErrorCode.COMMAND_NOT_FOUND: (
            "talosctl not found in PATH. "
            "Please install talosctl from https://talos.dev/install"
        ),
        ErrorCode.CONNECTION_FAILED: (
            "Cannot connect to Talos node. "
            "Check if the node is online and network connectivity is available."
        ),
        ErrorCode.AUTHENTICATION_FAILED: (
            "Authentication failed. "
            "Check your talosconfig file has valid certificates and the node trusts your client."
        ),
        ErrorCode.PERMISSION_DENIED: (
            "Permission denied. "
            "Your credentials may not have permission to perform this operation."
        ),
        ErrorCode.TIMEOUT: (
            "Request timed out. "
            "The node may be overloaded or network latency is too high. Try again later."
        ),
        ErrorCode.RESOURCE_NOT_FOUND: (
            "Requested resource not found. "
            "Verify the resource name and that it exists on the target node."
        ),
        ErrorCode.READONLY_VIOLATION: (
            "Operation blocked in read-only mode. "
            "Set TALOS_MCP_READONLY=false or remove --readonly flag to enable write operations."
        ),
        ErrorCode.NODE_UNREACHABLE: (
            "Node is unreachable. "
            "Verify the node IP/hostname is correct and the node is running."
        ),
    }

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

        # Infer error code from return code and stderr if not specified
        code = self._infer_error_code(code)

        message = f"Command failed with code {returncode}: {stderr}"
        super().__init__(message, code)

    def _infer_error_code(self, code: ErrorCode) -> ErrorCode:
        """Infer error code from return code and stderr content."""
        if code != ErrorCode.COMMAND_FAILED:
            return code

        # Check return codes
        if self.returncode == 127:
            return ErrorCode.COMMAND_NOT_FOUND
        elif self.returncode == 126:
            return ErrorCode.PERMISSION_DENIED
        elif self.returncode in (124, 143):
            return ErrorCode.TIMEOUT

        # Check stderr content
        stderr_lower = self.stderr.lower()
        error_patterns = {
            "connection refused": ErrorCode.CONNECTION_FAILED,
            "connection reset": ErrorCode.CONNECTION_FAILED,
            "no route to host": ErrorCode.NODE_UNREACHABLE,
            "unreachable": ErrorCode.NODE_UNREACHABLE,
            "timeout": ErrorCode.TIMEOUT,
            "deadline exceeded": ErrorCode.TIMEOUT,
            "context deadline": ErrorCode.TIMEOUT,
            "not found": ErrorCode.RESOURCE_NOT_FOUND,
            "permission denied": ErrorCode.PERMISSION_DENIED,
            "unauthorized": ErrorCode.AUTHENTICATION_FAILED,
            "authentication failed": ErrorCode.AUTHENTICATION_FAILED,
            "certificate": ErrorCode.AUTHENTICATION_FAILED,
            "tls": ErrorCode.AUTHENTICATION_FAILED,
            "readonly": ErrorCode.READONLY_VIOLATION,
            "read-only": ErrorCode.READONLY_VIOLATION,
        }

        for pattern, error_code in error_patterns.items():
            if pattern in stderr_lower:
                return error_code

        return ErrorCode.COMMAND_FAILED

    def get_user_message(self) -> str:
        """Get user-friendly error message.

        Returns:
            Human-readable error message with remediation hints.
        """
        user_msg = self.USER_MESSAGES.get(self.code)
        if user_msg:
            return f"{user_msg}\n\nTechnical details: {self.stderr}"
        return f"Operation failed: {self.stderr}"

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
                "user_message": self.get_user_message(),
            }
        )
        return base_dict
