# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-14

### Added
- Initial release of Talos MCP Server
- Core MCP server implementation with stdio transport
- TalosClient class for managing Talos API interactions
- 12 tools for Talos cluster management:
  - `talos_config_info` - Get configuration and context information
  - `talos_get_version` - Get Talos version from nodes
  - `talos_get_disks` - List disks on nodes
  - `talos_get_services` - Get service status
  - `talos_get_resources` - Query Talos resources
  - `talos_logs` - Get logs from services/containers
  - `talos_dashboard` - Get resource usage snapshot
  - `talos_health` - Check cluster health
  - `talos_list` - List files and directories
  - `talos_read` - Read file contents
  - `talos_etcd_members` - List etcd members
  - `talos_get_kubeconfig` - Retrieve kubeconfig
- Comprehensive documentation:
  - README with setup instructions
  - EXAMPLES with usage patterns
  - LICENSE (MIT)
- Setup automation:
  - Quickstart setup script
  - Connection test script
  - Example Claude Desktop configuration
- Development tools:
  - pyproject.toml with uv support
  - .gitignore for Python projects
  - Black and Ruff configuration

### Technical Details
- Built on MCP Python SDK
- Uses subprocess to execute talosctl commands
- Automatic talosconfig detection and loading
- Support for insecure connections (initial setup)
- YAML configuration parsing
- Async/await architecture

[0.1.0]: https://github.com/yourusername/talos-mcp-server/releases/tag/v0.1.0
