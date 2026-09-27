"""Explicit readonly checks against an operator-selected Talos node."""

import argparse
import asyncio
import sys
from pathlib import Path

from talos_mcp.core.client import TalosClient, TalosExecutionError
from talos_mcp.tools.cgroups import CgroupsTool
from talos_mcp.tools.system import GetHealthTool, GetVersionTool


async def check(config: Path, context: str, node: str, talosctl: Path) -> int:
    """Run three canonical readonly tools against the exact selected node."""
    try:
        client = TalosClient(
            config_path=str(config), context=context, profile="readonly", talosctl=str(talosctl)
        )
        for tool_type in (GetVersionTool, GetHealthTool, CgroupsTool):
            result = await tool_type(client).run({"nodes": node})
            print(f"{tool_type.name}:")
            for item in result:
                print(item.text)
    except (TalosExecutionError, ValueError) as exc:
        print(f"Manual check failed: {exc}", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    """Require all connection inputs explicitly; never guess a cluster target."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--talosconfig", type=Path, required=True)
    parser.add_argument("--context", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--talosctl", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(check(args.talosconfig, args.context, args.node, args.talosctl)))


if __name__ == "__main__":
    main()
