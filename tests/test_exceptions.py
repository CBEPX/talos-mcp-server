"""Tests for custom exceptions and error codes."""

from talos_mcp.core.exceptions import (
    ErrorCode,
    TalosCommandError,
    TalosConnectionError,
    TalosError,
)


class TestErrorCode:
    """Test ErrorCode enum."""

    def test_error_codes_are_unique(self):
        """Test that all error codes have unique values."""
        codes = [code.value for code in ErrorCode]
        assert len(codes) == len(set(codes)), "Error codes should be unique"

    def test_error_code_values_are_integers(self):
        """Test that all error codes are integers."""
        for code in ErrorCode:
            assert isinstance(code.value, int)

    def test_error_code_categories(self):
        """Test that error codes are in expected ranges."""
        # General errors: 1xx
        assert 100 <= ErrorCode.UNKNOWN.value < 200

        # Connection errors: 2xx
        assert 200 <= ErrorCode.CONNECTION_FAILED.value < 300

        # Command errors: 3xx
        assert 300 <= ErrorCode.COMMAND_FAILED.value < 400

        # Resource errors: 4xx
        assert 400 <= ErrorCode.RESOURCE_NOT_FOUND.value < 500

        # Validation errors: 5xx
        assert 500 <= ErrorCode.VALIDATION_FAILED.value < 600


class TestTalosError:
    """Test TalosError base class."""

    def test_talos_error_default_code(self):
        """Test TalosError with default error code."""
        error = TalosError("Test error")
        assert error.code == ErrorCode.UNKNOWN
        assert error.message == "Test error"

    def test_talos_error_custom_code(self):
        """Test TalosError with custom error code."""
        error = TalosError("Config error", ErrorCode.CONFIGURATION_ERROR)
        assert error.code == ErrorCode.CONFIGURATION_ERROR
        assert error.message == "Config error"

    def test_talos_error_to_dict(self):
        """Test TalosError.to_dict() method."""
        error = TalosError("Test error", ErrorCode.INTERNAL_ERROR)
        error_dict = error.to_dict()

        assert "error" in error_dict
        assert "code" in error_dict
        assert "code_name" in error_dict

        assert error_dict["error"] == "Test error"
        assert error_dict["code"] == ErrorCode.INTERNAL_ERROR.value
        assert error_dict["code_name"] == "INTERNAL_ERROR"


class TestTalosConnectionError:
    """Test TalosConnectionError."""

    def test_connection_error_default_code(self):
        """Test default connection error code."""
        error = TalosConnectionError("Connection failed")
        assert error.code == ErrorCode.CONNECTION_FAILED

    def test_connection_error_custom_code(self):
        """Test connection error with custom code."""
        error = TalosConnectionError("Timeout", ErrorCode.TIMEOUT)
        assert error.code == ErrorCode.TIMEOUT


class TestTalosCommandError:
    """Test TalosCommandError."""

    def test_command_error_basic(self):
        """Test basic TalosCommandError."""
        cmd = ["talosctl", "version"]
        error = TalosCommandError(cmd, 1, "Error occurred")

        assert error.cmd == cmd
        assert error.returncode == 1
        assert error.stderr == "Error occurred"
        assert error.code == ErrorCode.COMMAND_FAILED

    def test_command_error_infers_not_found(self):
        """Test that return code 127 infers COMMAND_NOT_FOUND."""
        cmd = ["unknown_command"]
        error = TalosCommandError(cmd, 127, "command not found")

        assert error.code == ErrorCode.COMMAND_NOT_FOUND

    def test_command_error_infers_permission_denied(self):
        """Test that return code 126 infers PERMISSION_DENIED."""
        cmd = ["restricted_command"]
        error = TalosCommandError(cmd, 126, "permission denied")

        assert error.code == ErrorCode.PERMISSION_DENIED

    def test_command_error_infers_timeout(self):
        """Test that return code 124/143 infers TIMEOUT."""
        cmd = ["long_running_command"]
        error1 = TalosCommandError(cmd, 124, "timeout")
        error2 = TalosCommandError(cmd, 143, "terminated")

        assert error1.code == ErrorCode.TIMEOUT
        assert error2.code == ErrorCode.TIMEOUT

    def test_command_error_infers_from_stderr(self):
        """Test that error code is inferred from stderr content."""
        cmd = ["talosctl", "get", "resource"]

        # Resource not found
        error1 = TalosCommandError(cmd, 1, "Error: resource not found")
        assert error1.code == ErrorCode.RESOURCE_NOT_FOUND

        # Permission denied
        error2 = TalosCommandError(cmd, 1, "permission denied: insufficient rights")
        assert error2.code == ErrorCode.PERMISSION_DENIED

        # Readonly violation
        error3 = TalosCommandError(cmd, 1, "operation readonly mode")
        assert error3.code == ErrorCode.READONLY_VIOLATION

    def test_command_error_custom_code(self):
        """Test TalosCommandError with explicit custom code."""
        cmd = ["talosctl", "apply"]
        error = TalosCommandError(cmd, 1, "Invalid config", ErrorCode.INVALID_CONFIG)

        assert error.code == ErrorCode.INVALID_CONFIG

    def test_command_error_to_dict(self):
        """Test TalosCommandError.to_dict() method."""
        cmd = ["talosctl", "version"]
        error = TalosCommandError(cmd, 1, "Error occurred")
        error_dict = error.to_dict()

        assert "error" in error_dict
        assert "code" in error_dict
        assert "code_name" in error_dict
        assert "command" in error_dict
        assert "returncode" in error_dict
        assert "stderr" in error_dict

        assert error_dict["command"] == cmd
        assert error_dict["returncode"] == 1
        assert error_dict["stderr"] == "Error occurred"

    def test_command_error_message_format(self):
        """Test that error message has expected format."""
        cmd = ["talosctl", "version"]
        error = TalosCommandError(cmd, 1, "Error occurred")

        assert "Command failed with code 1" in str(error)
        assert "Error occurred" in str(error)


class TestErrorHierarchy:
    """Test exception inheritance hierarchy."""

    def test_talos_error_is_base_exception(self):
        """Test that TalosError inherits from Exception."""
        error = TalosError("test")
        assert isinstance(error, Exception)

    def test_connection_error_is_talos_error(self):
        """Test that TalosConnectionError inherits from TalosError."""
        error = TalosConnectionError("test")
        assert isinstance(error, TalosError)
        assert isinstance(error, Exception)

    def test_command_error_is_talos_error(self):
        """Test that TalosCommandError inherits from TalosError."""
        error = TalosCommandError(["cmd"], 1, "error")
        assert isinstance(error, TalosError)
        assert isinstance(error, Exception)
