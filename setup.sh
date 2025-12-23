#!/bin/bash
set -e

echo "🚀 Talos MCP Server - Quickstart Setup"
echo "======================================"
echo ""

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed"
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✅ uv installed"
else
    echo "✅ uv is already installed"
fi

# Check for talosctl
if ! command -v talosctl &> /dev/null; then
    echo "❌ talosctl is not installed"
    echo ""
    echo "Please install talosctl:"
    echo "  macOS: brew install siderolabs/tap/talosctl"
    echo "  Linux: curl -sL https://talos.dev/install | sh"
    echo ""
    exit 1
else
    echo "✅ talosctl is already installed"
    TALOSCTL_VERSION=$(talosctl version --client --short 2>/dev/null || echo "unknown")
    echo "   Version: $TALOSCTL_VERSION"
fi

# Check for talosconfig
TALOSCONFIG_PATH="${TALOSCONFIG:-$HOME/.talos/config}"
if [ -f "$TALOSCONFIG_PATH" ]; then
    echo "✅ talosconfig found at $TALOSCONFIG_PATH"
else
    echo "⚠️  talosconfig not found at $TALOSCONFIG_PATH"
    echo "   You'll need to configure Talos before using this server"
fi

echo ""
echo "📦 Setting up Python environment..."

# Create virtual environment
if [ ! -d ".venv" ]; then
    uv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
uv pip install -e .

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Ensure your Talos cluster is configured:"
echo "   $ talosctl config info"
echo ""
echo "2. Test the MCP server:"
echo "   $ python src/talos_mcp/server.py"
echo ""
echo "3. Configure Claude Desktop:"
echo "   Add the configuration from claude_desktop_config.example.json"
echo "   to your Claude Desktop config file"
echo ""
echo "4. Restart Claude Desktop to load the MCP server"
echo ""
echo "📚 For more information, see README.md"
