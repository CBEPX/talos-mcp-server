# Agent Guidelines & Rules

This document defines the coding standards, architectural patterns, and best practices for the Talos MCP Server project. All usage of AI agents should strictly adhere to these guidelines.

## 🐍 Python Development

- **Type Hinting**: All functions and methods must have type hints. Use `typing` module (include `List`, `Dict`, `Optional`, `Any`, etc. or standard collections in Python 3.9+).
  - *Example*: `def get_node_version(ip: str) -> Dict[str, Any]:`
- **Docstrings**: Use Google-style docstrings for all modules, classes, and public functions.
- **Pydantic**: Use Pydantic models for data validation and schema definition, especially for MCP tools.
- **AsyncIO**: Use `async/await` for all I/O bound operations. Use `anyio` for compatibility where appropriate.
- **Error Handling**: Use `try/except` blocks judiciously. Create custom exception classes for domain-specific errors.
- **Loguru**: Use `loguru` (imported as `logger`) for all logging. Do NOT use Python's standard `logging` module.
- **Read-Only Safety**:
  - All mutating tools (e.g., reboot, upgrade) MUST explicitly set `is_mutation = True` in their class definition.
  - The `TalosClient` and `server.py` enforce strict read-only mode validation based on this flag.
- **Black & Ruff**: Ensure code is formatted with Black and linted with Ruff.

## ☸️ Helm & Kubernetes

- **Chart Structure**: Follow standard Helm chart structure (`Chart.yaml`, `values.yaml`, `templates/`).
- **Values**: Use camelCase for values in `values.yaml`. Document all values with comments.
- **Templates**:
  - Use `{{ .Values.key | default "default" }}` pattern.
  - Avoid hardcoding namespaces or resource names; use helper templates (e.g., `_helpers.tpl`) for naming.
- **Resources**: Define `resources` (requests/limits) for all containers.
- **Labels**: Ensure standard Kubernetes labels (`app.kubernetes.io/name`, etc.) are applied to all resources.

## 🔌 API Design (MCP)

- **Tools Definition**:
  - Tools must have clear, descriptive names (e.g., `talos_cluster_health` not `health`).
  - Descriptions must be detailed enough for an LLM to understand *when* and *how* to use the tool.
  - Input schemas must be strict and validated.
- **Resources**:
  - Use URI schemes consistent with the domain (e.g., `talos://<node>/<resource>`).
  - Implement `read_resource` with proper error handling for invalid URIs.
- **Prompts**:
  - Prompt arguments should be self-explanatory.
  - Prompt templates should be flexible but guide the LLM towards a specific goal.

## 🧪 Testing

- **Framework**: Use `pytest`.
- **Async Testing**: Use `pytest-asyncio` for async tests.
- **Coverage**: Maintain high test coverage (target >70%).
- **Mocking**: Use `unittest.mock` or `pytest-mock` to mock external dependencies (e.g., `talosctl`, network calls).
  - *Do not* make real network calls in unit tests.
- **Standard Commands**:
  - Run Unit Tests: `make test`
  - Run Linters: `make lint`
  - Integration Tests: `make test-integration` (Requires sudo/Docker on local machine)
  - Manual Verification: `python tests/manual_verification.py`
- **Structure**:
  - `tests/unit/`: Fast, isolated tests.
  - `tests/integration/`: Slower tests that might require a local Talos env.

## 📚 Documentation

- **Keep it Current**: Always update `README.md`, `task.md`, and `walkthrough.md` when adding features or changing behavior.
- **Self-Documenting Code**: Code should be readable, but complex logic needs comments explaining *why*, not just *what*.
- **Examples**: Provide examples in docstrings for complex tool inputs.

## 🏗️ Backend Development & Clean Architecture

- **Separation of Concerns**:
  - **Core**: Business logic and domain models (`src/talos_mcp/core`).
  - **Tools**: Implementation of MCP tools (`src/talos_mcp/tools`).
  - **Server**: Protocol handling and entry points (`src/talos_mcp/server.py`).
- **Dependency Injection**: Pass dependencies (like configuration or clients) explicitly rather than using global state.
- **Immutability**: Prefer immutable data structures (Pydantic models with `frozen=True` where possible).
- **Configuration**: Use `pydantic-settings` for configuration management, supporting both env vars and CLI args.

## 🔨 Refactoring & Clean Code

- **Boy Scout Rule**: Always leave the code cleaner than you found it.
- **Small Functions**: Functions should do one thing. If it spans more than screen height, split it.
- **Descriptive Naming**: Variable and function names should explain *what* they do/store.
- **Dead Code**: Remove commented-out code and unused imports immediately.
