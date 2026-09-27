"""Run one explicit MCP operation against an operator-owned disposable node."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from talos_mcp.core.policy import OPERATIONS


def require_target(manifest: dict[str, Any], confirmation: str) -> None:
    """Reject implicit, shared, or fan-out targets before starting the server."""
    node = manifest.get("node")
    if manifest.get("disposable") is not True or not manifest.get("owner"):
        raise ValueError("manifest requires disposable=true and a named owner")
    if not isinstance(node, str) or not node or node != confirmation:
        raise ValueError("confirmation does not match disposable node")
    if not isinstance(manifest.get("context"), str) or not manifest["context"].strip():
        raise ValueError("manifest requires an explicit context")
    for key in ("operation", "readback"):
        item = manifest.get(key)
        if not isinstance(item, dict) or not isinstance(item.get("tool"), str):
            raise ValueError(f"manifest requires {key}.tool")
        arguments = item.get("arguments")
        if not isinstance(arguments, dict):
            raise ValueError(f"{key} must have arguments")
        if (arguments.get("node") or arguments.get("nodes")) != node:
            raise ValueError(f"{key} must target exactly the confirmed node")
    operation = OPERATIONS.get(manifest["operation"]["tool"])
    readback = OPERATIONS.get(manifest["readback"]["tool"])
    if operation is None or operation.kind != "CLUSTER_WRITE":
        raise ValueError("operation must be one canonical cluster-write tool")
    if readback is None or readback.kind != "READ":
        raise ValueError("readback must be a read tool")
    for key in ("server", "talosctl", "talosconfig", "artifact_root"):
        path = manifest.get(key)
        if not isinstance(path, str) or not Path(path).is_absolute() or not Path(path).exists():
            raise ValueError(f"{key} must be an existing absolute path")


async def execute(manifest: dict[str, Any]) -> dict[str, Any]:
    """Call one operation with independent before and after reads."""
    operation = manifest["operation"]
    readback = manifest["readback"]
    names = ",".join(dict.fromkeys((operation["tool"], readback["tool"])))
    server = StdioServerParameters(
        command=manifest["server"],
        args=[
            "--profile",
            "write",
            "--allow-tools",
            names,
            "--talosctl",
            manifest["talosctl"],
            "--talosconfig",
            manifest["talosconfig"],
            "--context",
            manifest["context"],
            "--artifact-root",
            manifest["artifact_root"],
        ],
    )
    async with stdio_client(server) as (reader, writer), ClientSession(reader, writer) as session:
        await session.initialize()
        catalog = {tool.name for tool in (await session.list_tools()).tools}
        if catalog != set(names.split(",")):
            raise ValueError("requested tools are not in the effective catalog")
        before = await session.call_tool(readback["tool"], readback["arguments"])
        if before.isError:
            raise RuntimeError(f"baseline readback failed: {before.structuredContent}")
        result = await session.call_tool(operation["tool"], operation["arguments"])
        after = await session.call_tool(readback["tool"], readback["arguments"])
        return {
            "node": manifest["node"],
            "operation": operation["tool"],
            "before": before.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
            "after": after.model_dump(mode="json"),
        }


def main() -> None:
    """Require a manifest and exact human-entered node before any subprocess."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--confirm-disposable", required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text())
        require_target(manifest, args.confirm_disposable)
    except (OSError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    report = asyncio.run(execute(manifest))
    sys.stdout.write(json.dumps(report, indent=2) + "\n")
    if report["result"]["isError"] or report["after"]["isError"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
