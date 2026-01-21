# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.9] - 2026-01-21

### Changed
- Version bump for PyPI release (no code changes from 0.3.8)

## [0.3.8] - 2026-01-21

### Added
- **Tool Auto-Discovery**:
  - Implemented automatic tool discovery system in `registry.py`.
  - Tools are now auto-discovered from `tools/` directory using reflection.
  - No need to manually import and register new tools.
  - Added 9 comprehensive tests in `test_registry.py`.
- **Structured Error Codes**:
  - Added `ErrorCode` enum with 20+ categorized error codes (1xx-5xx).
  - Enhanced `TalosError`, `TalosConnectionError`, and `TalosCommandError` with structured codes.
  - Automatic error code inference from return codes and stderr content.
  - Added `to_dict()` methods for structured logging.
  - Added 19 comprehensive tests in `test_exceptions.py`.
- **New Test Suites**:
  - `test_readonly.py`: 5 tests for readonly enforcement.
  - `test_client_caching.py`: 4 tests for caching and IPv6 parsing.
  - `test_registry.py`: 9 tests for tool discovery.
  - `test_exceptions.py`: 19 tests for error handling.
  - Total: 37 new test cases.

### Changed
- **Architecture Refactoring**:
  - Extracted CLI logic into `cli.py` module (180 lines).
  - Extracted MCP handlers into `handlers.py` module (140 lines).
  - Created tool registry in `registry.py` module (120 lines).
  - Reduced `server.py` from 432 to ~90 lines (79% reduction).
  - Better separation of concerns following Single Responsibility Principle.
- **Tool Standardization**:
  - Converted `CgroupsTool` and `VolumesTool` to use Pydantic schemas.
  - All tools now follow consistent pattern with `args_schema` class attribute.

### Fixed
- **Critical Bugs**:
  - Added `is_mutation = True` to all 13 mutating tool classes.
  - Removed duplicate `WRITE_TOOLS` definitions in `server.py`.
  - Fixed duplicate `name: ClassVar[str]` declaration in `base.py`.
  - Synced version numbers between `pyproject.toml` and code (0.3.8).
- **High Priority**:
  - Consolidated readonly enforcement to single mechanism using `is_mutation` flag.
  - Removed redundant readonly checks from `TalosClient.execute_talosctl()`.
  - Fixed IPv6 address parsing bug in `get_nodes()` to handle `[IPv6]:port` format.
  - Fixed IPv4:port parsing to use colon counting for reliability.
- **Security**:
  - Moved audit log from temp directory to current directory.
  - Added talosconfig path validation with security checks.
  - Added file permission warnings for world-readable configs.
  - Path validation in `TalosClient._load_config()`.
- **Performance**:
  - Implemented config file caching based on mtime.
  - Added LRU cache for `get_nodes()` method.
  - Cache automatically invalidates when config changes.
- **Documentation**:
  - Fixed typo "Deprogam" → "Defragment" in README.
  - Updated CONTRIBUTING.md with correct project structure.
  - Created comprehensive IMPLEMENTATION_SUMMARY.md.

## [0.4.0] - 2026-01-21

### Added
- **Talos 1.12+ Support**:
  - `talos_cgroups`: Manage cgroups (Talos 1.9+).
  - `talos_volumes`: Manage user volumes (Talos 1.12+).
  - `talos_support`: Generate support bundles.

### Changed
- **Refactoring**:
  - Merged `tools/new_features` into the core `tools/` structure.
  - Standardized tool location.
- **Documentation**:
  - Updated `AGENTS.md` with strict documentation maintenance rules.
  - Updated `README.md` with new tools.

## [0.3.8] - 2025-12-24

### Fixed
- Python 3.10 compatibility: removed `except*` syntax (requires Python 3.11+)
- Exception handling now works across Python 3.10-3.13

## [0.3.7] - 2025-12-24

## [0.3.6] - 2025-12-24

## [0.3.5] - 2025-12-24

## [0.3.4] - 2025-12-24

## [0.3.3] - 2025-12-24

## [0.3.2] - 2025-12-24

### Added
- `--version` / `-V` option to show version and exit

## [0.3.1] - 2025-12-24

### Fixed
- **Critical**: Fixed server startup crash when installed via pip
  - Typer Option defaults now use literal values instead of Settings object
  - Entry point changed from `server:main` to `server:cli`
- Added `envvar` support for CLI options (`TALOS_MCP_LOG_LEVEL`, `TALOS_MCP_AUDIT_LOG_PATH`, `TALOS_MCP_READONLY`)

## [0.3.0] - 2025-12-24

### Added
- **GitHub CI/CD Pipeline**:
  - Lint job with ruff and mypy
  - Test matrix for Python 3.10, 3.11, 3.12, 3.13
  - Docker build with BuildX and GHA cache
  - **PyPI Trusted Publisher** for automated package publishing
- **Talosctl Version Management**:
  - `.talosctl-version` file for centralized version control
  - Makefile targets: `show-version`, `update-talosctl-version`, `check-talosctl-update`
  - Docker build reads version from `.talosctl-version`
- **Docker Support**:
  - `.dockerignore` for optimized build context
  - `docker-build` and `docker-run` Makefile targets
- **PyPI Package**: First public release on PyPI as `talos-mcp-server`

### Changed
- **Configuration Centralization**:
  - All logging settings moved to `Settings` class (Pydantic)
  - New settings: `log_format`, `audit_log_rotation`, `audit_log_retention`, `audit_log_serialize`
  - `configure_logging()` now uses settings instead of hardcoded values
- **Readonly Mode**:
  - Implemented enforcement in `call_tool()` - blocks 12 write operations when enabled
  - Affected tools: reboot, shutdown, reset, upgrade, apply, patch, bootstrap, etcd operations

### Fixed
- Broken import in `test_connection.py` (changed to `talos_mcp.core.client`)
- Missing `[tool.ruff.lint.isort]` section in `pyproject.toml`
- Updated Dockerfile talosctl from v1.9.1 to v1.12.0

### Documentation
- Updated `README.md` with 44+ tools listing
- Updated `QUICKSTART.md` with current tool count
- Regenerated `PROJECT_STRUCTURE.txt` with modular architecture

## [0.2.0] - 2025-12-24

### Added
- **New Tools (Gap Analysis & Parity):**
  - **Cluster Lifecycle**: `talos_bootstrap`, `talos_reset`, `talos_shutdown`, `talos_cluster_show`, `talos_image`.
  - **Configuration**: `talos_patch` (generic resource patch), `talos_machineconfig_patch`, `talos_gen_config`, `talos_validate_config`.
  - **Hardware & System**: `talos_disks`, `talos_devices` (PCI/USB/System), `talos_mounts`, `talos_du`, `talos_volume_status`, `talos_kernel_param_status`.
  - **Network**: `talos_pcap`, `talos_netstat`, `talos_routes`.
- **Integration Testing Framework**:
  - `make test-integration` for full-lifecycle testing against Docker-provisioned Talos clusters.
  - Automated cluster provisioning (`make cluster-up`) and teardown (`make cluster-down`).
  - Read-Only and Read-Write integration test suites.
- **Observability**:
  - Structured JSON audit logging (`talos_mcp_audit.log`).
  - Enhanced application logging with `loguru`.

### Changed
- **Architecture**:
  - Refactored monolithic code into modular `core` and `tools` packages.
  - `TalosClient` now prioritizes `TALOSCONFIG` environment variable config paths.
  - Improved `get_nodes` resolution to fallback to endpoints for dynamic clusters.
- **Tool Logic**:
  - `CopyTool`: Fixed `talosctl cp` execution to strictly require node flags.
  - `TalosTool`: specific error exception handling (`TalosCommandError`).
- **DevEx**:
  - Added comprehensive `Makefile` targets.
  - Strict type checking with `mypy` and linting with `ruff`.

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
