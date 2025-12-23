#!/usr/bin/env python3
"""Test script for Talos MCP Server

This script verifies that the MCP server can communicate with your Talos cluster.
"""

import asyncio
import sys
from pathlib import Path


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from talos_mcp.client import TalosClient


async def test_connection():
    """Test connection to Talos cluster"""
    print("🔍 Testing Talos MCP Server Connection")
    print("=" * 50)
    print()

    # Initialize client
    client = TalosClient()

    # Test 1: Check config
    print("1️⃣  Checking Talos configuration...")
    config_info = client.get_context_info()

    if "error" in config_info:
        print(f"   ❌ {config_info['error']}")
        print()
        print("   Please ensure you have a valid talosconfig file.")
        print("   Run: talosctl config info")
        return False
    else:
        print("   ✅ Configuration loaded")
        print(f"      Context: {config_info.get('context', 'N/A')}")
        print(f"      Endpoints: {', '.join(config_info.get('endpoints', []))}")
        print()

    # Test 2: Check talosctl
    print("2️⃣  Testing talosctl command...")
    result = await client.execute_talosctl(["version", "--client"])

    if result["success"]:
        print("   ✅ talosctl is working")
        # Print first line of version output
        version_line = result["stdout"].split("\n")[0] if result["stdout"] else ""
        if version_line:
            print(f"      {version_line}")
        print()
    else:
        print(f"   ❌ talosctl failed: {result.get('stderr', 'Unknown error')}")
        print()
        return False

    # Test 3: Try to connect to cluster
    print("3️⃣  Testing cluster connection...")
    result = await client.execute_talosctl(["version"])

    if result["success"]:
        print("   ✅ Successfully connected to Talos cluster")
        print()
        # Print version info
        for line in result["stdout"].split("\n")[:5]:
            if line.strip():
                print(f"      {line}")
        print()
    else:
        print("   ⚠️  Could not connect to cluster")
        print(f"      {result.get('stderr', 'Unknown error')}")
        print()
        print("   This might be expected if your cluster is not running.")
        print("   The MCP server is configured correctly, but cluster is unreachable.")
        print()

    print("=" * 50)
    print("✅ Talos MCP Server is set up correctly!")
    print()
    print("You can now:")
    print("  1. Add this server to your Claude Desktop configuration")
    print("  2. Restart Claude Desktop")
    print("  3. Start asking Claude about your Talos cluster")
    print()
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_connection())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        sys.exit(1)
