"""Discovery of canonical tools with fail-closed startup validation."""

import importlib
import inspect
import pkgutil
from pathlib import Path

from talos_mcp.core.client import TalosClient
from talos_mcp.core.policy import ALIASES, OPERATIONS, UNSUPPORTED
from talos_mcp.tools.base import TalosTool


def discover_tools(client: TalosClient) -> list[TalosTool]:
    """Import and instantiate enabled tool classes; invalid definitions abort startup."""
    package = importlib.import_module("talos_mcp.tools")
    if package.__file__ is None:
        raise ValueError("Tool package has no file path")
    path = Path(package.__file__).parent
    tools: list[TalosTool] = []
    for module_info in pkgutil.iter_modules([str(path)]):
        if module_info.name == "base":
            continue
        module = importlib.import_module(f"talos_mcp.tools.{module_info.name}")
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(cls, TalosTool)
                and cls is not TalosTool
                and cls.__module__ == module.__name__
            ):
                if cls.name in UNSUPPORTED:
                    continue
                if cls.name not in OPERATIONS:
                    raise ValueError(f"Unregistered operation: {cls.name}")
                if client.enabled(cls.name):
                    tools.append(cls(client))
    return tools


def create_tool_registry(
    client: TalosClient, use_discovery: bool = True
) -> tuple[list[TalosTool], dict[str, TalosTool]]:
    """Return a validated canonical catalog and hidden deprecated call aliases."""
    _ = use_discovery
    tools = discover_tools(client)
    names = [tool.name for tool in tools]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate canonical tool definition")
    for tool in tools:
        definition = tool.get_definition()
        if definition.inputSchema.get("additionalProperties") is not False:
            raise ValueError(f"Invalid input schema for {tool.name}")
    mapping = {tool.name: tool for tool in tools}
    for alias, canonical in ALIASES.items():
        if canonical in mapping:
            mapping[alias] = mapping[canonical]
    return tools, mapping
