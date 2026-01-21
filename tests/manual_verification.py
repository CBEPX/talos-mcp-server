import asyncio
import logging
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from talos_mcp.core.client import TalosClient
from talos_mcp.tools.cgroups import CgroupsTool
from talos_mcp.tools.system import GetHealthTool, GetVersionTool
from talos_mcp.tools.volumes import VolumesTool


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("manual_verify")


async def main():
    print("🚀 Starting Manual Verification on Docker Cluster")
    print("=" * 50)

    # Initialize client with local config
    config_file = str(Path("talosconfig").absolute())
    print(f"📂 Using config: {config_file}")

    try:
        client = TalosClient(config_path=config_file)
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return

    # Get Nodes
    print("\n1️⃣  Discovering Nodes...")
    try:
        # We need to manually get nodes because the client might not auto-detect
        # correctly if specific endpoints aren't mapped to nodes in a way it expects
        # or just to be safe.
        # Actually client.get_nodes() parses the config.
        nodes = client.get_nodes()
        print(f"   Found nodes: {nodes}")
        if not nodes:
            # Fallback for docker provisioner often just uses the endpoint IP or 10.5.0.2
            # Let's try to grab endpoints from context
            info = client.get_context_info()
            if "endpoints" in info:
                # Docker provisioner usually exposes ports to localhost, but the node IP inside
                # the network is what talosctl expects if accessing directly?
                # Actually --nodes 127.0.0.1 might work if port forwarding is set up,
                # but usually we need the container IP.
                # Let's try the first node found or default to 10.5.0.2 (common for docker provider)
                # In the 'make cluster-up' output we saw: 10.5.0.2
                print("   Fallback: Using 10.5.0.2 as node")
                nodes = ["10.5.0.2"]
            else:
                print("❌ No nodes found in config and no endpoints.")
                return
    except Exception as e:
        print(f"❌ Error getting nodes: {e}")
        return

    target_node = nodes[0]
    print(f"   🎯 Target Node: {target_node}")

    # Helper to run tool
    async def run_tool(tool_cls, name, args):
        print(f"\n▶️  Running {name}...")
        try:
            tool = tool_cls(client)
            results = await tool.run(args)
            for res in results:
                print(res.text)
        except Exception as e:
            print(f"   ❌ Failed: {e}")

    # Test Version
    await run_tool(GetVersionTool, "talos_version", {"nodes": target_node})

    # Test Health
    await run_tool(GetHealthTool, "talos_health", {"nodes": target_node})

    # Test Cgroups (New Feature)
    await run_tool(CgroupsTool, "talos_cgroups", {"nodes": target_node, "action": "list"})

    # Test Volumes (New Feature)
    # Note: Volumes might be empty on a fresh cluster, but the command should succeed (return empty list or headers)
    await run_tool(VolumesTool, "talos_volumes", {"nodes": target_node, "action": "list"})

    print("\n" + "=" * 50)
    print("✅ Verification Complete")


if __name__ == "__main__":
    asyncio.run(main())
