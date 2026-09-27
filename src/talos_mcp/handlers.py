"""MCP protocol handlers."""

import asyncio
import json
import re
import time
from typing import Any, cast

from loguru import logger
from mcp.types import (
    CallToolResult,
    GetPromptResult,
    Prompt,
    Resource,
    ResourceTemplate,
    TextContent,
    Tool,
)
from pydantic import AnyUrl, ValidationError

from talos_mcp.core.client import TalosExecutionError
from talos_mcp.core.policy import ALIASES, OPERATIONS, UNSUPPORTED
from talos_mcp.prompts import TalosPrompts
from talos_mcp.resources import TalosResources
from talos_mcp.tools.base import TalosTool


class MCPHandlers:
    """Centralized MCP protocol handlers."""

    def __init__(
        self,
        prompts: TalosPrompts,
        resources: TalosResources,
        tools_list: list[TalosTool],
        tools_map: dict[str, TalosTool],
    ) -> None:
        """Initialize MCP handlers.

        Args:
            prompts: TalosPrompts instance.
            resources: TalosResources instance.
            tools_list: List of all available tools.
            tools_map: Dictionary mapping tool names to tool instances.
        """
        self.prompts = prompts
        self.resources = resources
        self.tools_list = tools_list
        self.tools_map = tools_map

    # Resource Handlers
    async def list_resources(self) -> list[Resource]:
        """List available resources.

        Returns:
            List of available resources.
        """
        return await self.resources.list_resources()

    async def list_resource_templates(self) -> list[ResourceTemplate]:
        """List available resource templates.

        Returns:
            List of resource templates.
        """
        return await self.resources.list_resource_templates()

    async def read_resource(self, uri: AnyUrl) -> str | bytes:
        """Read a resource.

        Args:
            uri: Resource URI to read.

        Returns:
            Resource content as string or bytes.
        """
        kind = uri.path.strip("/") if uri.path else ""
        tool = {
            "version": "talos_version",
            "health": "talos_health",
            "config": "talos_config_info",
        }.get(kind)
        started = time.monotonic()
        code = "OK"
        outcome = "complete"
        size = 0
        try:
            with self.resources.client.call_budget(tool or "UNKNOWN"):
                result = await self.resources.read_resource(uri)
            size = len(result.encode() if isinstance(result, str) else result)
            return result
        except asyncio.CancelledError:
            code, outcome = "CANCELLED", "unknown"
            raise
        except TalosExecutionError as exc:
            code, outcome = exc.code, exc.outcome
            raise
        except Exception as exc:
            code, outcome = type(exc).__name__, "failed"
            raise
        finally:
            if self.resources.client.audit_enabled:
                logger.bind(audit=True).info(
                    json.dumps(
                        {
                            "resource": kind,
                            "tool": tool or "UNKNOWN",
                            "profile": self.resources.client.profile,
                            "node": uri.host or "",
                            "class": OPERATIONS[tool].kind if tool else "UNKNOWN",
                            "phase": (
                                "complete"
                                if code == "OK"
                                else "cancelled" if code == "CANCELLED" else "error"
                            ),
                            "code": code,
                            "outcome": outcome,
                            "duration_ms": round((time.monotonic() - started) * 1000),
                            "response_bytes": size,
                        },
                        separators=(",", ":"),
                    )
                )

    # Prompt Handlers
    async def list_prompts(self) -> list[Prompt]:
        """List available prompts.

        Returns:
            List of available prompts.
        """
        return await self.prompts.list_prompts()

    async def get_prompt(
        self, name: str, arguments: dict[str, str] | None = None
    ) -> GetPromptResult:
        """Get a prompt by name.

        Args:
            name: Prompt name.
            arguments: Optional prompt arguments.

        Returns:
            Prompt result with messages.
        """
        messages = await self.prompts.get_prompt(name, arguments)
        return GetPromptResult(messages=messages)

    # Tool Handlers
    async def list_tools(self) -> list[Tool]:
        """List all available Talos tools.

        Returns:
            List of tool definitions.
        """
        return [tool.get_definition() for tool in self.tools_list]

    async def call_tool(self, name: str, arguments: Any) -> CallToolResult:
        """Handle tool calls for Talos operations.

        Args:
            name: Tool name to execute.
            arguments: Tool arguments.

        Returns:
            List of TextContent results.
        """
        started = time.monotonic()
        client = self.resources.client
        result: CallToolResult | None = None
        cancelled = False
        try:
            with client.call_budget(ALIASES.get(name, name)):
                result = await self._call_tool_impl(name, arguments)
            if not result.isError:
                result.structuredContent = {
                    **(result.structuredContent or {}),
                    "content": [
                        item.model_dump(mode="json", exclude_none=True) for item in result.content
                    ],
                }
            return result
        except asyncio.CancelledError:
            cancelled = True
            raise
        finally:
            if client.audit_enabled:
                canonical = ALIASES.get(name, name)
                operation = OPERATIONS.get(canonical)
                node = ""
                if isinstance(arguments, dict):
                    candidate = arguments.get("node") or arguments.get("nodes")
                    if isinstance(candidate, str) and re.fullmatch(
                        r"[A-Za-z0-9.:[\]_-]+(?:,[A-Za-z0-9.:[\]_-]+)*", candidate
                    ):
                        node = candidate
                data = result.structuredContent if result and result.structuredContent else {}
                record = {
                    "tool": canonical if operation else "UNKNOWN",
                    "profile": client.profile,
                    "node": node,
                    "class": operation.kind if operation else "UNKNOWN",
                    "phase": (
                        "cancelled"
                        if cancelled
                        else "complete" if result and not result.isError else "error"
                    ),
                    "code": "CANCELLED" if cancelled else data.get("code", "INTERNAL_ERROR"),
                    "outcome": (
                        "unknown"
                        if cancelled and operation and operation.kind == "CLUSTER_WRITE"
                        else data.get("outcome", "failed")
                    ),
                    "duration_ms": round((time.monotonic() - started) * 1000),
                    "exit_code": data.get("exit_code"),
                    "response_bytes": (
                        sum(
                            len(item.text.encode())
                            for item in result.content
                            if isinstance(item, TextContent)
                        )
                        if result
                        else 0
                    ),
                }
                logger.bind(audit=True).info(json.dumps(record, separators=(",", ":")))

    async def _call_tool_impl(self, name: str, arguments: Any) -> CallToolResult:
        """Execute one policy-gated tool without logging raw inputs or outputs."""
        canonical = ALIASES.get(name, name)
        if name in UNSUPPORTED:
            return self._error("UNSUPPORTED_TOOL")
        tool = self.tools_map.get(canonical)
        if not tool:
            return self._error("TOOL_NOT_ENABLED" if canonical in OPERATIONS else "UNKNOWN_TOOL")
        try:
            if not isinstance(arguments, dict):
                return self._error("INVALID_ARGUMENT")
            validated = tool.args_schema.model_validate(arguments)
            content = await tool.run(validated.model_dump(exclude_unset=True))
            if isinstance(content, CallToolResult):
                return content
            return CallToolResult(
                content=cast("list[Any]", content),
                isError=False,
                structuredContent={
                    "code": "OK",
                    "outcome": (
                        "accepted"
                        if canonical
                        in {
                            "talos_apply_config",
                            "talos_machineconfig_patch",
                            "talos_bootstrap",
                            "talos_reboot",
                            "talos_shutdown",
                            "talos_reset",
                            "talos_upgrade",
                        }
                        else "complete"
                    ),
                    "exit_code": 0,
                    "complete": True,
                    "truncated": False,
                },
            )
        except (ValidationError, ValueError, TypeError):
            result = self._error("INVALID_ARGUMENT")
        except TalosExecutionError as exc:
            result = self._error(
                exc.code, outcome=exc.outcome, exit_code=exc.exit_code, truncated=exc.truncated
            )
        except Exception as exc:
            logger.warning("Tool {} failed with {}", canonical, type(exc).__name__)
            result = self._error("INTERNAL_ERROR")
        return result

    @staticmethod
    def _error(
        code: str, *, outcome: str = "failed", exit_code: int | None = None, truncated: bool = False
    ) -> CallToolResult:
        """Return an explicit, sanitized MCP tool failure."""
        envelope = {
            "code": code,
            "outcome": outcome,
            "exit_code": exit_code,
            "complete": False,
            "truncated": truncated,
            "stderr_excerpt": "",
        }
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(envelope, separators=(",", ":")))],
            isError=True,
            structuredContent=envelope,
        )
