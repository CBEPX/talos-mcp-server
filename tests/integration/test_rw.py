import pytest
from talos_mcp.core.client import TalosClient
from talos_mcp.tools.services import ServiceTool

@pytest.mark.asyncio
async def test_service_restart_integration():
    """Test a Write operation: Restarting a service."""
    client = TalosClient()
    tool = ServiceTool(client)
    
    # Restart kubelet (safe for test cluster)
    # We use 'restart' action on 'kubelet'
    results = await tool.run({
        "action": "restart",
        "service": "kubelet"
    })
    
    # talosctl service restart usually returns empty output on success, 
    # or just doesn't error out.
    assert len(results) > 0
    # On success, it might print confirmation or be empty. 
    # If it failed, it would raise or return error text.
    assert "Error" not in results[0].text
