# Qualification walkthrough

Build one candidate wheel from the reviewed source. Record its SHA-256 and source revision. Run the required local checks:

~~~sh
make install
make lint
make test
uv build --wheel --out-dir dist
uv run --no-project --with "mcp>=1.30,<2" --with pyyaml python tests/wheel_stdio_smoke.py --wheel dist
~~~

The wheel smoke creates a clean environment and downloads an official talosctl asset. It compares the asset with talosctl-checksums.txt. The smoke then uses real MCP stdio to initialize, list, call, read a resource, fetch a prompt, generate private files, and validate a generated file. Each platform checks native child cleanup after cancellation and EOF. Windows also rejects a broad ACL.

The live runner requires an operator-owned disposable VM. Create a private JSON manifest with absolute paths and an exact node. The manifest must name its owner. Do not store credentials or private addresses in this repository.

~~~json
{
  "disposable": true,
  "owner": "operator-name",
  "node": "disposable-node",
  "context": "disposable-lab",
  "server": "/opt/talos-mcp/releases/reviewed/venv/bin/talos-mcp-server",
  "talosctl": "/opt/talos-mcp/releases/reviewed/talosctl",
  "talosconfig": "/path/to/private/talosconfig",
  "artifact_root": "/path/to/private/artifacts",
  "operation": {
    "tool": "talos_service_action",
    "arguments": {"node": "disposable-node", "service": "kubelet", "action": "restart"}
  },
  "readback": {
    "tool": "talos_service",
    "arguments": {"nodes": "disposable-node", "service": "kubelet"}
  }
}
~~~

Only run the manifest against the VM that its owner provisioned for this test. Enter the same node again on the command line:

~~~sh
make test-integration LAB_MANIFEST=/path/to/private/manifest.json LAB_NODE=disposable-node
~~~

The runner calls the readback before and after one operation. It never retries an uncertain mutation. It closes the MCP stdio process when the call ends. The VM owner controls VM creation, power-on, and cleanup. For reboot, shutdown, reset, and upgrade, make separate readbacks after the node returns. Check Kubernetes cordon state and cluster health before another operation.

Record the wheel digest, CLI digest, Talos node version, command result, independent readbacks, and unresolved failures. Keep private evidence outside the public source tree. See [task.md](task.md) for the completed 0.4.0 qualification and its limits. Windows Actions and ARM64 container checks passed; ARM64 Talos VM lifecycle remains incomplete.
