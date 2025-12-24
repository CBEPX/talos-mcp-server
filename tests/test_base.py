import pytest
from pydantic import BaseModel, Field

from talos_mcp.core.exceptions import TalosCommandError
from talos_mcp.tools.base import TalosTool


class SchemaForTest(BaseModel):
    arg1: str = Field(description="Test argument")

class ToolForTest(TalosTool):
    name = "test_tool"
    description = "A test tool"
    args_schema = SchemaForTest

    async def run(self, arguments: dict):
        args = SchemaForTest(**arguments)
        return await self.execute_talosctl(["echo", args.arg1])

@pytest.mark.asyncio
async def test_talos_tool_definition(mock_talos_client):
    tool = ToolForTest(mock_talos_client)
    definition = tool.get_definition()
    assert definition.name == "test_tool"
    assert definition.description == "A test tool"
    assert "arg1" in definition.inputSchema["properties"]

@pytest.mark.parametrize(
    "name, mock_response, mock_side_effect, inputs, expected_output_contains, expected_error",
    [
        (
            "Success",
            {"stdout": "success output", "stderr": ""},
            None,
            {"arg1": "value"},
            "success output",
            None,
        ),
        (
            "Success with stderr (Health check style)",
            {"stdout": "standard output", "stderr": "warning message"},
            None,
            {"arg1": "value"},
            "warning message",
            None,
        ),
        (
            "Failure",
            None,
            TalosCommandError(cmd=["echo", "value"], returncode=1, stderr="error message"),
            {"arg1": "value"},
            "error message",
            "Error executing test_tool",
        ),
    ],
)
@pytest.mark.asyncio
async def test_talos_tool_execution(
    mock_talos_client,
    name,
    mock_response,
    mock_side_effect,
    inputs,
    expected_output_contains,
    expected_error,
):
    """Table-driven test for TalosTool execution."""
    if mock_side_effect:
        mock_talos_client.execute_talosctl.side_effect = mock_side_effect
    else:
        mock_talos_client.execute_talosctl.return_value = mock_response

    tool = ToolForTest(mock_talos_client)
    result = await tool.run(inputs)

    assert len(result) == 1
    text = result[0].text

    if expected_error:
        assert expected_error in text
    else:
        assert text.startswith("```\n")

    assert expected_output_contains in text
