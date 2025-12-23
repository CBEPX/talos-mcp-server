"""Test logging and error handling by provoking a failure."""

import asyncio
import logging
import sys


# Add src to path
sys.path.append("src")

from talos_mcp.core.client import TalosClient
from talos_mcp.core.exceptions import TalosCommandError


# Configure logging to show everything
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_logging")


async def main():
    client = TalosClient()

    logger.info("--- Testing successful command (should log debug) ---")
    # Using 'version --client' which should work locally without cluster
    try:
        await client.execute_talosctl(["version", "--client"])
    except Exception as e:
        logger.error(f"Version command failed: {e}")

    logger.info("\n--- Testing failed command (should log error) ---")
    # This command should fail
    try:
        await client.execute_talosctl(["invalid-command-xyz"])
        print("Unexpected success for invalid command!")
    except TalosCommandError as e:
        print(f"Correctly caught error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
