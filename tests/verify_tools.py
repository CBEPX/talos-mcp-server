"""Verify that all tools are registered correctly."""

import asyncio
import logging
import sys


# Add src to path
sys.path.append("src")

from talos_mcp.server import list_tools


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_tools")


async def main():
    tools = await list_tools()
    logger.info(f"Found {len(tools)} tools registered.")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")

    expected_tools = [
        "talos_version",
        "talos_health",
        "talos_stats",
        "talos_containers",
        "talos_processes",
        "talos_dashboard",
        "talos_memory",
        "talos_time",
        "talos_ls",
        "talos_cat",
        "talos_cp",
        "talos_du",
        "talos_mounts",
        "talos_interfaces",
        "talos_routes",
        "talos_netstat",
        "talos_pcap",
        "talos_service",
        "talos_logs",
        "talos_dmesg",
        "talos_events",
        "talos_reboot",
        "talos_shutdown",
        "talos_reset",
        "talos_upgrade",
        "talos_image",
        "talos_etcd_members",
        "talos_etcd_snapshot",
        "talos_etcd_alarm",
        "talos_etcd_defrag",
        "talos_config_info",
        "talos_kubeconfig",
        "talos_apply_config",
        "talos_validate_config",
        "talos_get",
        "talos_definitions",
    ]

    missing = [t for t in expected_tools if not any(ft.name == t for ft in tools)]

    if missing:
        logger.error(f"Missing tools: {missing}")
        sys.exit(1)

    logger.info("All expected tools are registered successfully.")


if __name__ == "__main__":
    asyncio.run(main())
