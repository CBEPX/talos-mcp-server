import pytest

from talos_mcp.tools.cluster import BootstrapTool, ClusterShowTool
from talos_mcp.tools.config import GenConfigTool, MachineConfigPatchTool, PatchTool
from talos_mcp.tools.system import DevicesTool, DisksTool


@pytest.mark.asyncio
async def test_patch_tool(mock_talos_client):
    mock_talos_client.get_nodes.return_value = ["10.0.0.1", "10.0.0.2"]
    mock_talos_client.execute_talosctl.return_value = {"stdout": "patched", "stderr": ""}
    tool = PatchTool(mock_talos_client)
    # Test valid patch
    args = {
        "nodes": "10.0.0.1",
        "type": "MachineConfig",
        "patch": '{"machine": {"type": "worker"}}',
        "mode": "strategic"
    }
    await tool.run(args)
    mock_talos_client.execute_talosctl.assert_called_with(
        ["patch", "MachineConfig", "-n", "10.0.0.1", "--patch", '{"machine": {"type": "worker"}}', "--mode", "strategic"]
    )

@pytest.mark.asyncio
async def test_machineconfig_patch_tool(mock_talos_client):
    mock_talos_client.get_nodes.return_value = ["10.0.0.1", "10.0.0.2"]
    mock_talos_client.execute_talosctl.return_value = {"stdout": "patched", "stderr": ""}
    tool = MachineConfigPatchTool(mock_talos_client)
    args = {
        "nodes": "10.0.0.1",
        "patch": "machine:\n  type: worker",
        "mode": "no-reboot"
    }
    await tool.run(args)
    mock_talos_client.execute_talosctl.assert_called_with(
        ["machineconfig", "patch", "--patch", "machine:\n  type: worker", "-n", "10.0.0.1", "--mode", "no-reboot"]
    )

@pytest.mark.asyncio
async def test_gen_config_tool(mock_talos_client):
    mock_talos_client.execute_talosctl.return_value = {"stdout": "generated", "stderr": ""}
    tool = GenConfigTool(mock_talos_client)
    args = {
        "name": "test-cluster",
        "endpoint": "https://1.1.1.1:6443",
        "output_dir": "./out",
        "version": "v1.30.0"
    }
    await tool.run(args)
    mock_talos_client.execute_talosctl.assert_called_with(
        ["gen", "config", "test-cluster", "https://1.1.1.1:6443", "--output-dir", "./out", "--kubernetes-version", "v1.30.0"]
    )

@pytest.mark.asyncio
async def test_bootstrap_tool(mock_talos_client):
    mock_talos_client.get_nodes.return_value = ["10.0.0.1", "10.0.0.2"]
    mock_talos_client.execute_talosctl.return_value = {"stdout": "bootstrapped", "stderr": ""}
    tool = BootstrapTool(mock_talos_client)
    args = {"nodes": "10.0.0.1"}
    await tool.run(args)
    mock_talos_client.execute_talosctl.assert_called_with(
        ["bootstrap", "-n", "10.0.0.1"]
    )

@pytest.mark.asyncio
async def test_cluster_show_tool(mock_talos_client):
    mock_talos_client.execute_talosctl.return_value = {"stdout": "cluster status", "stderr": ""}
    tool = ClusterShowTool(mock_talos_client)
    args = {}
    await tool.run(args)
    mock_talos_client.execute_talosctl.assert_called_with(
        ["cluster", "show"]
    )

    # Test with nodes arg
    args_with_nodes = {"nodes": "10.0.0.1"}
    await tool.run(args_with_nodes)
    mock_talos_client.execute_talosctl.assert_called_with(
        ["cluster", "show", "-n", "10.0.0.1"]
    )

@pytest.mark.asyncio
async def test_disks_tool(mock_talos_client):
    mock_talos_client.get_nodes.return_value = ["10.0.0.1", "10.0.0.2"]
    mock_talos_client.execute_talosctl.return_value = {"stdout": "disks", "stderr": ""}
    tool = DisksTool(mock_talos_client)
    await tool.run({})
    mock_talos_client.execute_talosctl.assert_called_with(
        ["get", "disks", "-n", "10.0.0.1,10.0.0.2"]  # Default all nodes from mock
    )

@pytest.mark.asyncio
async def test_devices_tool(mock_talos_client):
    mock_talos_client.get_nodes.return_value = ["10.0.0.1", "10.0.0.2"]
    mock_talos_client.execute_talosctl.return_value = {"stdout": "devices", "stderr": ""}
    tool = DevicesTool(mock_talos_client)
    await tool.run({})
    mock_talos_client.execute_talosctl.assert_called_with(
        ["get", "devices", "-n", "10.0.0.1,10.0.0.2"]
    )
