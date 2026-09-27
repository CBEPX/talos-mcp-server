"""Canonical tool catalog and fail-closed registry checks."""

from talos_mcp.core.client import TalosClient
from talos_mcp.core.policy import ALIASES, OPERATIONS
from talos_mcp.registry import create_tool_registry


def test_public_write_catalog_covers_every_canonical_operation() -> None:
    tools, mapping = create_tool_registry(TalosClient(profile="write"))
    expected = {name for name in OPERATIONS if not name.startswith("_")}
    assert {tool.name for tool in tools} == expected
    assert len({tool.name for tool in tools}) == len(tools)
    assert set(mapping) == expected | set(ALIASES)
    assert all(tool.get_definition().inputSchema["additionalProperties"] is False for tool in tools)


def test_readonly_catalog_contains_only_read_operations() -> None:
    tools, mapping = create_tool_registry(TalosClient(profile="readonly"))
    expected = {
        name
        for name, operation in OPERATIONS.items()
        if not name.startswith("_") and operation.kind == "READ"
    }
    assert {tool.name for tool in tools} == expected
    assert set(mapping) == expected
