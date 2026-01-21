# Contributing to Talos MCP Server

Thank you for your interest in contributing to Talos MCP Server!

## Development Setup

### Prerequisites

- Python 3.10+
- `talosctl` CLI installed
- Access to a Talos Linux cluster (for integration testing)

### Installation

```bash
# Clone the repository
git clone https://github.com/CBEPX/talos-mcp-server.git
cd talos-mcp-server

# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install with dev dependencies
uv venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Code Quality

This project uses several tools to maintain code quality:

### Linting & Formatting

```bash
# Format code with Black
black src/ tests/

# Lint with Ruff (and auto-fix)
ruff check --fix src/ tests/

# Run all linters
pre-commit run --all-files
```

### Type Checking

```bash
# Type check with MyPy
mypy src/
```

### Security Scanning

```bash
# Run Bandit security scanner
bandit -r src/
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=talos_mcp --cov-report=html

# Run specific test file
pytest tests/test_server.py

# Run tests in parallel
pytest -n auto
```

## Project Structure

```
talos-mcp-server/
├── src/
│   └── talos_mcp/
│       ├── __init__.py       # Package initialization
│       ├── server.py         # Main MCP server
│       ├── prompts.py        # MCP prompts
│       ├── resources.py      # MCP resources
│       ├── py.typed          # PEP 561 marker
│       ├── core/             # Core modules
│       │   ├── __init__.py
│       │   ├── client.py     # TalosClient wrapper
│       │   ├── settings.py   # Configuration management
│       │   └── exceptions.py # Custom exceptions
│       └── tools/            # Tool implementations
│           ├── __init__.py
│           ├── base.py       # Base tool class
│           ├── system.py     # System inspection tools
│           ├── files.py      # File operation tools
│           ├── cluster.py    # Cluster lifecycle tools
│           ├── config.py     # Configuration tools
│           ├── etcd.py       # Etcd management tools
│           ├── network.py    # Network tools
│           ├── services.py   # Services tools
│           ├── resources.py  # Resource tools
│           ├── cgroups.py    # Cgroups tools
│           ├── volumes.py    # Volumes tools
│           └── support.py    # Support bundle tools
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── integration/          # Integration tests
│   └── test_*.py             # Test files
├── pyproject.toml            # Project configuration
├── .pre-commit-config.yaml   # Pre-commit hooks
└── README.md
```

## Code Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use [Google-style docstrings](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html)
- Maximum line length: 100 characters
- Use type hints for all public functions

### Example

```python
"""Module docstring."""

from typing import Any


def get_version(node: str, *, timeout: int = 30) -> dict[str, Any]:
    """Get the Talos version from a node.

    Args:
        node: The node IP address or hostname.
        timeout: Request timeout in seconds.

    Returns:
        A dictionary containing version information.

    Raises:
        TalosError: If the request fails.
    """
    ...
```

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new etcd snapshot tool
fix: handle connection timeout properly
docs: update README with new examples
chore: update dependencies
test: add integration tests for health check
refactor: extract common talosctl wrapper
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Ensure all tests pass: `pytest`
4. Ensure code quality checks pass: `pre-commit run --all-files`
5. Update documentation if needed
6. Submit a pull request

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
