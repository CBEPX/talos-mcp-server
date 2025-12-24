<img src="https://github.com/ry-ops/talos-mcp-server/blob/main/talos-mcp-server.png" width="100%">

# Talos MCP Server

An MCP (Model Context Protocol) server that provides seamless integration with Talos Linux clusters. This server enables Claude to interact with your Talos infrastructure through the native gRPC API.

## Features

- 🔌 **MCP Resources**: Direct access to node health, version, and config via URI
- 📝 **MCP Prompts**: Intelligent templates for diagnosing clusters and reviewing audits
- 🔧 **Cluster Management**: Bootstrap, upgrade, reset, and manage node lifecycle
- 💾 **Disk & Hardware**: Inspect disks, mounts, PCI, USB, and system devices
- 📊 **Monitoring**: Access logs, dmesg, services, and real-time dashboard data
- 🔍 **File System**: Browse and read files on Talos nodes
- 🔐 **etcd Integration**: Manage members, snapshots, alarms, and defragmentation
- ☸️ **Kubernetes Config**: Retrieve kubeconfig for cluster access
- ⚙️ **Configuration**: Patches, validation, and machine config management
- 📡 **Resource Inspection**: Query any Talos resource (similar to kubectl get)

## What is Talos Linux?

Talos Linux is a modern, secure, and immutable Linux distribution designed specifically for Kubernetes. Key features:

- **API-Managed**: Completely managed via a declarative gRPC API (no SSH)
- **Immutable**: Read-only root filesystem for enhanced security
- **Minimal**: Only includes components necessary to run Kubernetes
- **Secure by Default**: Kernel hardened following KSPP recommendations

## Prerequisites

1. **Python 3.10+**
2. **uv** - Fast Python package installer
3. **talosctl** - Talos CLI tool
4. **Talos Configuration** - A valid talosconfig file (usually at `~/.talos/config`)

## Installation

### 1. Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

### 2. Install talosctl

```bash
# macOS
brew install siderolabs/tap/talosctl

# Linux
curl -sL https://talos.dev/install | sh

# Or download directly
curl -Lo /usr/local/bin/talosctl https://github.com/siderolabs/talos/releases/latest/download/talosctl-$(uname -s | tr "[:upper:]" "[:lower:]")-amd64
chmod +x /usr/local/bin/talosctl
```

### 3. Clone and Setup

```bash
cd talos-mcp-server

# Create virtual environment and install dependencies using uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
uv pip install -e .
```

### 4. Docker Support

You can also run the server using Docker.

```bash
# Build the image
docker build -t talos-mcp-server .

# Run the container (make sure to mount your talos config)
docker run --rm -i \
  -v $HOME/.talos:/root/.talos:ro \
  -e TALOSCONFIG=/root/.talos/config \
  talos-mcp-server
```

Or using Docker Compose for development:

```bash
docker-compose up --build
```

## Configuration

### Talos Configuration

Ensure you have a valid Talos configuration file. This is typically created when you set up your Talos cluster:

```bash
# Generate config (if setting up new cluster)
talosctl gen config my-cluster https://<control-plane-ip>:6443

# Check your current config
talosctl config info

# View available contexts
talosctl config contexts
```

The MCP server will automatically use your default Talos configuration from `~/.talos/config`.

### Client Integration

#### Claude Desktop

To use this MCP server with Claude Desktop, add it to your configuration:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "talos": {
      "command": "/path/to/talos-mcp-server/.venv/bin/python",
      "args": [
        "/path/to/talos-mcp-server/src/talos_mcp/server.py"
      ],
      "env": {
        "TALOSCONFIG": "/path/to/your/.talos/config",
        "TALOS_MCP_LOG_LEVEL": "INFO",
        "TALOS_MCP_AUDIT_LOG_PATH": "talos_mcp_audit.log"
      }
    }
  }
}
```

#### Cursor

1. Open **Cursor Settings**
2. Go to **Features** > **MCP Servers**
3. Click **+ Add New MCP Server**
4. Fill in the details:
   - **Name**: `talos`
   - **Type**: `stdio`
   - **Command**: `/absolute/path/to/venv/bin/python /absolute/path/to/server.py`
   - **Environment Variables**: Add `TALOSCONFIG` pointing to your config file

#### Google Antigravity / Generic JSON

For other clients supporting the Model Context Protocol (including Perplexity or generic integrations), use the standard server definition. You can configure the server using CLI arguments (Typer) or Environment Variables.

**Example using CLI arguments:**

```json
{
  "mcpServers": {
    "talos": {
      "command": "python",
      "args": [
        "src/talos_mcp/server.py",
        "--log-level", "DEBUG",
        "--readonly"
      ],
      "env": {
        "TALOSCONFIG": "${HOME}/.talos/config"
      }
    }
  }
}
```

**Example using Environment Variables:**

```json
{
  "mcpServers": {
    "talos": {
      "command": "python",
      "args": ["src/talos_mcp/server.py"],
      "env": {
        "TALOSCONFIG": "${HOME}/.talos/config",
        "TALOS_MCP_READONLY": "true",
        "TALOS_MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

#### Configuration Options

The server uses `Typer` for CLI arguments and `Pydantic Settings` for environment variables. You can mix and match, but CLI arguments take precedence.

| Environment Variable | CLI Argument | Description | Default |
|----------------------|--------------|-------------|---------|
| `TALOSCONFIG` | N/A | Path to talosconfig file | `~/.talos/config` |
| `TALOS_MCP_LOG_LEVEL` | `--log-level` | Logging verbosity (DEBUG, INFO, etc) | `INFO` |
| `TALOS_MCP_AUDIT_LOG_PATH` | `--audit-log` | Path to JSON audit log file | `talos_mcp_audit.log` |
| `TALOS_MCP_READONLY` | `--readonly` / `--no-readonly` | Enable/Disable read-only mode | `false` |

## Available Tools

### Cluster Lifecycle

- **talos_bootstrap**: Bootstrap the cluster on a node
- **talos_upgrade**: Upgrade Talos on a node
- **talos_reset**: Reset a node to maintenance mode
- **talos_reboot**: Reboot a node
- **talos_shutdown**: Shutdown a node
- **talos_cluster_show**: High-level cluster overview

### Configuration & Management

- **talos_config_info**: Get current Talos configuration and context
- **talos_apply_config** / **talos_apply**: Apply configuration
- **talos_patch**: Apply generic patches to resources
- **talos_machineconfig_patch**: Patch machine configuration
- **talos_validate_config**: Validate configuration files
- **talos_get_kubeconfig**: Retrieve kubeconfig

### System & Hardware

- **talos_get_version**: Get Talos Linux version
- **talos_health**: Check cluster health status
- **talos_get_disks**: List disks
- **talos_devices**: List PCI, USB, and System devices
- **talos_mounts**: List mount points
- **talos_du**: Disk usage analysis
- **talos_dashboard**: Real-time resource usage snapshot

### Network & Services

- **talos_get_services**: Service status
- **talos_interfaces**: List network interfaces
- **talos_routes**: List network routes
- **talos_netstat**: Network connections
- **talos_pcap**: Capture packet data
- **talos_logs**: Service/Container logs
- **talos_dmesg**: Kernel logs

### Resources & Etcd

- **talos_get_resources**: Query any Talos resource
- **talos_list**: List files
- **talos_read**: Read files
- **talos_etcd_members**: List etcd members
- **talos_etcd_snapshot**: Take etcd snapshot
- **talos_etcd_alarm**: Manage etcd alarms
- **talos_etcd_defrag**: Deprogam etcd storage

## Usage Examples

### With Claude Desktop

Once configured, you can ask Claude natural language questions:

```
"Show me the version of Talos running on my cluster"

"What services are running on node 192.168.1.10?"

"Get the logs from kubelet on my control plane nodes"

"List all disks on 192.168.1.10"

"Check the health of my Talos cluster"

"Show me the etcd members"
```

### Programmatic Usage

```python
from talos_mcp.server import TalosClient

# Initialize client
client = TalosClient()

# Get context info
info = client.get_context_info()
print(info)

# Execute talosctl commands
result = await client.execute_talosctl(["version"])
print(result["stdout"])
```

## Development

### Running Tests

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run unit tests
pytest

# Run integration tests (Requires Docker)
# This will provision a local Talos cluster in Docker
make test-integration
```

### Code Quality

We use a comprehensive set of tools to ensure code quality:

```bash
# Standard development workflow using Makefile
make install      # Install dependencies
make lint         # Run all linters (ruff, mypy, bandit)
make test         # Run tests
make verify       # Verify tool registration
```

### Logging and Auditing

The server uses `loguru` for structured logging.
- **Console**: INFO level logs for general feedback.
- **Audit Log**: `talos_mcp_audit.log` (rotating) containing detailed JSON logs for debugging and auditing commands.


## Architecture

```
┌─────────────────┐
│  Claude Desktop │
└────────┬────────┘
         │ MCP Protocol
         ↓
┌─────────────────┐
│  MCP Server     │
│  (Python)       │
└────────┬────────┘
         │ subprocess
         ↓
┌─────────────────┐
│   talosctl CLI  │
└────────┬────────┘
         │ gRPC + mTLS
         ↓
┌─────────────────┐
│  Talos Cluster  │
│   (apid API)    │
└─────────────────┘
```

## Security Considerations

1. **mTLS Authentication**: Talos API uses mutual TLS for authentication
2. **Certificate Management**: Keep your talosconfig and certificates secure
3. **Network Access**: Ensure your endpoints are properly firewalled
4. **Permissions**: The MCP server has the same permissions as your talosconfig

## Troubleshooting

### talosctl not found

```bash
# Check if talosctl is in PATH
which talosctl

# Install talosctl if missing
curl -sL https://talos.dev/install | sh
```

### Configuration not found

```bash
# Check config location
echo $TALOSCONFIG

# Verify config exists
ls -la ~/.talos/config

# Test connectivity
talosctl version
```

### Connection refused

```bash
# Verify endpoints in config
talosctl config info

# Check network connectivity
ping <control-plane-ip>

# Verify certificates are valid
talosctl version --nodes <node-ip>
```

### MCP Server Issues

```bash
# Test the server directly
python src/talos_mcp/server.py

# Check Claude Desktop logs
# macOS: ~/Library/Logs/Claude/
# Windows: %APPDATA%\Claude\logs\
```

## Resources

- [Talos Linux Documentation](https://www.talos.dev/)
- [Talos GitHub Repository](https://github.com/siderolabs/talos)
- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [talosctl CLI Reference](https://www.talos.dev/latest/reference/cli/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built for the [Model Context Protocol](https://modelcontextprotocol.io/)
- Integrates with [Talos Linux](https://www.talos.dev/) by Sidero Labs
- Uses [uv](https://github.com/astral-sh/uv) for fast Python package management
