"""Tool registry for MCP server with auto-discovery."""

import importlib
import inspect
import pkgutil
from pathlib import Path

from loguru import logger

from talos_mcp.core.client import TalosClient
from talos_mcp.tools.base import TalosTool


def discover_tools(client: TalosClient) -> list[TalosTool]:
    """Auto-discover and instantiate all tool classes from tools package.

    Args:
        client: TalosClient instance to pass to tools.

    Returns:
        List of instantiated tool objects.
    """
    tools_list: list[TalosTool] = []
    tools_package = "talos_mcp.tools"

    # Get the tools package directory
    tools_module = importlib.import_module(tools_package)
    tools_path = Path(tools_module.__file__).parent

    # Discover all modules in the tools package
    for module_info in pkgutil.iter_modules([str(tools_path)]):
        if module_info.name == "base":  # Skip base module
            continue

        module_name = f"{tools_package}.{module_info.name}"

        try:
            # Import the module
            module = importlib.import_module(module_name)

            # Find all classes that are subclasses of TalosTool
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a TalosTool subclass (but not TalosTool itself)
                if (
                    issubclass(obj, TalosTool)
                    and obj is not TalosTool
                    and obj.__module__ == module_name  # Only from this module
                ):
                    try:
                        # Instantiate the tool
                        tool_instance = obj(client)
                        tools_list.append(tool_instance)
                        logger.debug(f"Discovered tool: {tool_instance.name}")
                    except Exception as e:
                        logger.error(f"Failed to instantiate tool {name} from {module_name}: {e}")
        except Exception as e:
            logger.error(f"Failed to import module {module_name}: {e}")

    logger.info(f"Discovered {len(tools_list)} tools")
    return tools_list


def create_tool_registry(
    client: TalosClient, use_discovery: bool = True
) -> tuple[list[TalosTool], dict[str, TalosTool]]:
    """Create and return the tool registry.

    Args:
        client: TalosClient instance to pass to tools.
        use_discovery: If True, use auto-discovery. If False, use manual registration.

    Returns:
        Tuple of (tools_list, tools_map) for easy access.
    """
    if use_discovery:
        tools_list = discover_tools(client)
    else:
        # Fallback to manual registration for backwards compatibility
        from talos_mcp.tools.cgroups import CgroupsTool
        from talos_mcp.tools.cluster import (
            BootstrapTool,
            ClusterShowTool,
            ImageTool,
            RebootTool,
            ResetTool,
            ShutdownTool,
            UpgradeTool,
        )
        from talos_mcp.tools.config import (
            ApplyConfigTool,
            ApplyTool,
            ConfigInfoTool,
            GenConfigTool,
            GetKubeconfigTool,
            MachineConfigPatchTool,
            PatchTool,
            ValidateConfigTool,
        )
        from talos_mcp.tools.etcd import (
            EtcdAlarmTool,
            EtcdDefragTool,
            EtcdMembersTool,
            EtcdSnapshotTool,
        )
        from talos_mcp.tools.files import (
            CopyTool,
            DiskUsageTool,
            ListFilesTool,
            MountsTool,
            ReadFileTool,
        )
        from talos_mcp.tools.network import (
            InterfacesTool,
            NetstatTool,
            PcapTool,
            RoutesTool,
        )
        from talos_mcp.tools.resources import (
            GetKernelParamStatusTool,
            GetResourceTool,
            GetVolumeStatusTool,
            ListDefinitionsTool,
        )
        from talos_mcp.tools.services import (
            DmesgTool,
            EventsTool,
            LogsTool,
            ServiceTool,
        )
        from talos_mcp.tools.support import SupportTool
        from talos_mcp.tools.system import (
            DashboardTool,
            DevicesTool,
            DisksTool,
            GetContainersTool,
            GetHealthTool,
            GetProcessesTool,
            GetStatsTool,
            GetVersionTool,
            MemoryTool,
            TimeTool,
        )
        from talos_mcp.tools.volumes import VolumesTool

        tools_list = [
            # System
            GetVersionTool(client),
            GetHealthTool(client),
            GetStatsTool(client),
            GetContainersTool(client),
            GetProcessesTool(client),
            DashboardTool(client),
            MemoryTool(client),
            TimeTool(client),
            DisksTool(client),
            DevicesTool(client),
            # Files
            ListFilesTool(client),
            ReadFileTool(client),
            CopyTool(client),
            DiskUsageTool(client),
            MountsTool(client),
            # Network
            InterfacesTool(client),
            RoutesTool(client),
            NetstatTool(client),
            PcapTool(client),
            # Services
            ServiceTool(client),
            LogsTool(client),
            DmesgTool(client),
            EventsTool(client),
            # Cluster
            RebootTool(client),
            ShutdownTool(client),
            ResetTool(client),
            UpgradeTool(client),
            ImageTool(client),
            BootstrapTool(client),
            ClusterShowTool(client),
            # Etcd
            EtcdMembersTool(client),
            EtcdSnapshotTool(client),
            EtcdAlarmTool(client),
            EtcdDefragTool(client),
            # Config
            ConfigInfoTool(client),
            GetKubeconfigTool(client),
            ApplyConfigTool(client),
            ApplyTool(client),
            ValidateConfigTool(client),
            PatchTool(client),
            MachineConfigPatchTool(client),
            GenConfigTool(client),
            # Resources
            GetResourceTool(client),
            ListDefinitionsTool(client),
            GetVolumeStatusTool(client),
            GetKernelParamStatusTool(client),
            # New Features (Talos 1.12+)
            CgroupsTool(client),
            VolumesTool(client),
            SupportTool(client),
        ]

    tools_map = {tool.name: tool for tool in tools_list}

    return tools_list, tools_map
