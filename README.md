# Talos MCP Server

Talos MCP Server runs as a Python stdio server. It calls a pinned talosctl binary. The server does not connect to Talos through a separate Python gRPC client.

Version 0.4.0 is a breaking repair release. Its default profile is readonly. A separate write profile enables standalone operations when the operator supplies suitable Talos credentials. An exact tool allowlist can restrict either profile.

## Install a reviewed build

Use Python 3.10 or newer. Install a talosctl release that matches the Talos minor version on the node. This repository pins the default CLI release in .talosctl-version and records official release checksums in talosctl-checksums.txt. Install a reviewed wheel into a dedicated environment:

~~~sh
uv build --wheel
python3 -m venv /opt/talos-mcp/venv
/opt/talos-mcp/venv/bin/python -m pip install dist/talos_mcp_server-0.4.0-py3-none-any.whl
/opt/talos-mcp/venv/bin/talos-mcp-server --version
~~~

The package version is static metadata. A source checkout needs an editable install or a rebuilt wheel after code changes. A wheel install includes Python dependencies. Install talosctl separately and supply its absolute path with --talosctl.

The server can start without a Talos configuration file. In that state, talos_config_info, offline validation, and talos_version with client_only=true work. Authenticated node tools return CONFIG_REQUIRED. Set --talosconfig and, if needed, --context for cluster calls. The CLI uses that context for the server lifetime and passes it to each authenticated child.

## Profiles and tools

The default readonly profile exposes diagnostic tools only. --profile write exposes all qualified canonical tools unless --allow-tools narrows the catalog. The comma-separated allowlist accepts exact canonical names. Unknown names, wildcards, aliases, and write tools in a readonly list stop startup. A Talos credential does not override the server profile or allowlist.

The main changed calls are:

| Purpose | Canonical tool | Profile |
| --- | --- | --- |
| Node and client version | talos_version | readonly |
| Cluster health | talos_health | readonly |
| Service status | talos_service | readonly |
| Service start, stop, or restart | talos_service_action | write |
| Image list | talos_image | readonly |
| Image pull | talos_image_pull | write |
| etcd alarm list | talos_etcd_alarm | readonly |
| etcd alarm disarm and defrag | talos_etcd_alarm_disarm, talos_etcd_defrag | write |
| Offline configuration validation | talos_validate_config | readonly |
| Offline configuration generation | talos_gen_config | write |
| Apply or patch machine configuration | talos_apply_config, talos_machineconfig_patch | write |
| Bootstrap, reboot, shutdown, reset, upgrade | talos_bootstrap, talos_reboot, talos_shutdown, talos_reset, talos_upgrade | write |

The full catalog is the response to tools/list for the selected profile. Old mixed service, image, and alarm actions return INVALID_ARGUMENT; use the separate read and write tools in the table above. talos_apply and talos_patch are call-only aliases for one minor release and do not appear in tools/list. talos_volumes, talos_pcap, talos_dashboard, and talos_cluster_show are unsupported. talos_get accepts only exact runtime/machinestatus and runtime/volumestatus. Logs, dmesg, and events return bounded snapshots.

The talos://{node}/version, talos://{node}/health, and talos://{node}/config resources appear only when their backing tool is enabled. The config resource returns sanitized context metadata. It does not return the full talosconfig.

## Local Codex and Claude Code

Set these values to absolute paths on the computer that starts the MCP server. Use a Talos os:reader credential for the readonly entry.

~~~sh
MCP_SERVER=/opt/talos-mcp/venv/bin/talos-mcp-server
TALOSCTL=/opt/talos-mcp/talosctl/v1.14.1/talosctl
READER_CONFIG=/path/to/reader-talosconfig
READ_TOOLS=talos_version,talos_health,talos_service,talos_logs,talos_dmesg,talos_events,talos_get,talos_config_info

codex mcp add talos-read -- "$MCP_SERVER" --profile readonly --talosctl "$TALOSCTL" --talosconfig "$READER_CONFIG" --allow-tools "$READ_TOOLS"
claude mcp add -s local talos-read -- "$MCP_SERVER" --profile readonly --talosctl "$TALOSCTL" --talosconfig "$READER_CONFIG" --allow-tools "$READ_TOOLS"
~~~

An operations entry is optional. Create it only for the reviewed action set and a separate credential. For a TALM-managed cluster, TALM keeps ownership of ordering, quorum, rollout, and rollback:

~~~sh
OPERATOR_CONFIG=/path/to/operator-talosconfig
OPERATIONS=talos_service_action,talos_image_pull,talos_etcd_alarm_disarm,talos_etcd_defrag

codex mcp add talos-ops -- "$MCP_SERVER" --profile write --talosctl "$TALOSCTL" --talosconfig "$OPERATOR_CONFIG" --allow-tools "$OPERATIONS"
claude mcp add -s local talos-ops -- "$MCP_SERVER" --profile write --talosctl "$TALOSCTL" --talosconfig "$OPERATOR_CONFIG" --allow-tools "$OPERATIONS"
~~~

This restricted operations entry is a deployment example. Standalone --profile write with no allowlist can expose all qualified canonical operations. Use a credential with the Talos role required by each operation. A Talos role alone does not restrict lifecycle actions inside this server.

## Codex and Claude Code through SSH

Install the wheel, matching talosctl, and Talos credentials on the jump host before connecting. Use an SSH config with a verified host key. A Teleport user can generate a separate OpenSSH config with tsh config > /path/to/ssh_config. Inspect that file and use its ProxyCommand, identity, and known-hosts settings. Keep the file outside a public repository.

~~~sh
SSH_CONFIG=/path/to/ssh_config
SSH_TARGET=talos-jump
REMOTE_SERVER=/opt/talos-mcp/venv/bin/talos-mcp-server
REMOTE_TALOSCTL=/opt/talos-mcp/talosctl/v1.14.1/talosctl
REMOTE_READER_CONFIG=/var/lib/talos-mcp/reader-talosconfig
READ_TOOLS=talos_version,talos_health,talos_service,talos_logs,talos_dmesg,talos_events,talos_get,talos_config_info

codex mcp add talos-remote -- ssh -F "$SSH_CONFIG" -T -o BatchMode=yes -o StrictHostKeyChecking=yes "$SSH_TARGET" "$REMOTE_SERVER" --profile readonly --talosctl "$REMOTE_TALOSCTL" --talosconfig "$REMOTE_READER_CONFIG" --allow-tools "$READ_TOOLS"
claude mcp add -s local talos-remote -- ssh -F "$SSH_CONFIG" -T -o BatchMode=yes -o StrictHostKeyChecking=yes "$SSH_TARGET" "$REMOTE_SERVER" --profile readonly --talosctl "$REMOTE_TALOSCTL" --talosconfig "$REMOTE_READER_CONFIG" --allow-tools "$READ_TOOLS"
~~~

The remote command must print only MCP messages to stdout. SSH banners and remote shell output break stdio. A returned artifact path is on the jump host. Copy it with a separate reviewed scp or SFTP action. SSH connection does not install packages or alter the host.

## Artifacts and lifecycle

Use --artifact-root for reviewed input files and generated outputs. Input paths are relative to that root. The server rejects traversal, links, reparse points, overwrites, and unsafe permissions. It creates unique output directories. POSIX uses private 0700 directories and 0600 files. Windows requires a private ACL for the current account. An artifact response gives its path, size, SHA-256, and server locality. Ready artifacts have no automatic expiry.

Generation and validation work offline. talos_support requires an explicit encryption choice. On Talos 1.13, only none is qualified. Talos 1.14 supports none, siderolabs, and explicit recipients. The siderolabs mode does not give the operator a decryption key.

Each lifecycle call targets one explicit node. Apply and patch require mode=auto|no-reboot|staged|try. Reset requires explicit wipe labels from STATE and EPHEMERAL. Upgrade requires an explicit target version and digest-pinned image. It uses native --wait=true --drain=true and a bounded default deadline of 600 seconds. The host that runs this server must reach the Kubernetes API for drain.

A zero exit from reboot, shutdown, reset, or upgrade means the command was accepted. It does not prove that the node returned or that the cluster is healthy. If a child stops after dispatch or reaches its deadline, the result is OUTCOME_UNKNOWN. Do not retry automatically. Read back the node, Kubernetes readiness, cordon state, and cluster health before the operator acts. A timed-out drain can leave the node Ready but cordoned, with workloads pending. The server does not uncordon or roll back.

Use Talos 1.13 or 1.14 for qualified writes. Talos 1.12 has only transitional version, health, and safe-get diagnostics. A version mismatch can permit diagnostic reads with a warning. Authenticated writes and artifact or sensitive reads require the talosctl minor to match the node minor. For example, the pinned 1.14 CLI cannot run these operations against a 1.13 node. Offline config generation does not contact a node. After a 1.13 to 1.14 upgrade, restart the server with a pinned 1.14 CLI before further writes.

## Docker, Ansible, and qualification

The Dockerfile reads .talosctl-version and verifies the matching amd64 or arm64 asset against talosctl-checksums.txt during build. It keeps audit logging off by default. Build an architecture explicitly:

~~~sh
docker buildx build --platform linux/amd64 -t talos-mcp-server:v0.4.0-amd64 --load .
docker run --rm -i --mount type=bind,src=/path/to/reader-talosconfig,dst=/run/talosconfig,readonly -e TALOS_MCP_TALOSCONFIG=/run/talosconfig talos-mcp-server:v0.4.0-amd64
~~~

examples/ansible contains an idempotent, pinned installation example. It installs a reviewed wheelhouse and talosctl under a dedicated account. It does not copy credentials or connect client products.

Run make install, make lint, and make test for source checks. tests/wheel_stdio_smoke.py builds a clean install and exercises real MCP stdio with an official checksum-verified CLI. CI runs it on Linux, macOS, and Windows. The Talos 1.13.5, 1.13.10, and 1.14.1 CLI fixtures test offline behavior. A 1.12.1 CLI fixture tests transitional client-only behavior. These checks do not prove live cluster behavior. Live lifecycle qualification requires a separate disposable Talos VM, one explicit node, and independent readbacks. make test-integration LAB_MANIFEST=/path/to/manifest.json LAB_NODE=the-disposable-node runs one reviewed operation; the external lab owner provisions and reaps the VM.
