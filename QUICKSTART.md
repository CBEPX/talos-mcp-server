# Talos MCP Server - Quick Reference

## Project Structure

```
talos-mcp-server/
├── src/
│   └── talos_mcp/
│       ├── __init__.py           # Package initialization
│       └── server.py             # Main MCP server implementation
├── pyproject.toml                # Project configuration and dependencies
├── setup.sh                      # Automated setup script
├── test_connection.py            # Connection testing utility
├── README.md                     # Comprehensive documentation
├── EXAMPLES.md                   # Usage examples and patterns
├── CHANGELOG.md                  # Version history
├── LICENSE                       # MIT License
├── .gitignore                    # Git ignore rules
└── claude_desktop_config.example.json  # Claude Desktop configuration template
```

## Quick Setup

```bash
# 1. Run the setup script
./setup.sh

# 2. Test the connection
python test_connection.py

# 3. Configure Claude Desktop
# Add config from claude_desktop_config.example.json
```

## Available Tools (44+)

The server provides 44+ tools covering:

- **System**: version, health, stats, containers, processes, dashboard, memory, time, disks, devices
- **Files**: ls, cat, cp, du, mounts
- **Network**: interfaces, routes, netstat, pcap
- **Services**: service, logs, dmesg, events
- **Cluster**: reboot, shutdown, reset, upgrade, bootstrap, cluster_show, image
- **Config**: config_info, kubeconfig, apply, patch, machineconfig_patch, validate, gen_config
- **Etcd**: members, snapshot, alarm, defrag
- **Resources**: get, definitions, volume_status, kernel_param_status

See [README.md](README.md#available-tools) for the full list.

## Key Features

- ✅ Full Talos API integration via talosctl
- ✅ Async/await for performance
- ✅ Automatic config loading from ~/.talos/config
- ✅ Support for insecure mode (initial setup)
- ✅ Multiple output formats (JSON, YAML, table)
- ✅ Comprehensive error handling
- ✅ Claude Desktop integration ready

## Requirements

- Python 3.10+
- uv (fast Python package manager)
- talosctl (Talos CLI)
- Valid Talos cluster configuration

## Common Commands

```bash
# Setup
./setup.sh

# Test
python test_connection.py

# Run server directly
source .venv/bin/activate
python src/talos_mcp/server.py

# Check talosctl
talosctl version
talosctl config info
```

## Architecture

```
Claude Desktop
    ↓ (MCP Protocol)
MCP Server (Python)
    ↓ (subprocess)
talosctl CLI
    ↓ (gRPC + mTLS)
Talos Cluster (apid)
```

## Configuration Locations

- **Talos config**: `~/.talos/config` or `$TALOSCONFIG`
- **Claude Desktop config**:
  - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

## Example Queries to Claude

- "Check the health of my Talos cluster"
- "List disks on node 192.168.1.10"
- "Show me kubelet logs from my control plane"
- "Get the cluster version"
- "List all etcd members"

## Troubleshooting

| Issue | Solution |
|-------|----------|
| talosctl not found | Install: `curl -sL https://talos.dev/install \| sh` |
| Config not found | Check `$TALOSCONFIG` or `~/.talos/config` |
| Connection refused | Verify endpoints and network connectivity |
| Import errors | Run `uv pip install -e .` |

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Format code
black src/

# Lint
ruff check src/

# Test
pytest
```

## Resources

- [Talos Docs](https://www.talos.dev/)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [talosctl Reference](https://www.talos.dev/latest/reference/cli/)

## Support

For issues or questions:
1. Check README.md for detailed documentation
2. Review EXAMPLES.md for usage patterns
3. Test connection with test_connection.py
4. Check Claude Desktop logs for MCP errors

## License

MIT License - See LICENSE file for details
