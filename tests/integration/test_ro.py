import pytest
from talos_mcp.core.client import TalosClient
from talos_mcp.tools.system import GetVersionTool, GetHealthTool
from talos_mcp.tools.files import ListFilesTool

@pytest.mark.asyncio
async def test_version_integration():
    client = TalosClient()
    tool = GetVersionTool(client)
    results = await tool.run({})
    assert len(results) > 0
    assert "Tag" in results[0].text  # Should contain version info

@pytest.mark.asyncio
async def test_health_integration():
    client = TalosClient()
    tool = GetHealthTool(client)
    # Health checks might take a bit or return warnings on fresh clusters, 
    # but the command should succeed (exit 0)
    results = await tool.run({})
    assert len(results) > 0
    # Output should not be an error
    assert "Error:" not in results[0].text

@pytest.mark.asyncio
async def test_ls_integration():
    client = TalosClient()
    tool = ListFilesTool(client)
    # List root
    results = await tool.run({"path": "/"})
    assert len(results) > 0
    assert "etc" in results[0].text
    assert "bin" in results[0].text
