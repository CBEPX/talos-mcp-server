import asyncio
import time
from talos_mcp.core.client import TalosClient
from talos_mcp.tools.system import GetVersionTool

async def wait_for_cluster(timeout: int = 300):
    print(f"Waiting for cluster to be ready (timeout {timeout}s)...")
    start = time.time()
    client = TalosClient()
    tool = GetVersionTool(client)
    
    while True:
        try:
            # Try to get version
            results = await tool.run({})
            if results and "Tag" in results[0].text:
                print("Cluster is ready!")
                return
        except Exception as e:
            pass
            
        if time.time() - start > timeout:
            raise TimeoutError("Timed out waiting for cluster to be ready")
            
        await asyncio.sleep(2)

if __name__ == "__main__":
    try:
        asyncio.run(wait_for_cluster())
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
