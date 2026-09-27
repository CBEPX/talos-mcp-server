# Version 0.4.0 delivery

The release candidate passed qualification on 2026-09-27. The final wheel SHA-256 is `8d2b09680f4180a340dcf1bbf7985d9a7338552030c3ca1c90a63918a59f5d66`.

- [x] Required Ruff, MyPy, Black, pytest, and uv lock checks passed.
- [x] Installed-wheel stdio, cancellation, and EOF cleanup passed on Linux, macOS, and Windows for Python 3.10 through 3.14, with minimum and current MCP SDK dependencies.
- [x] Windows native talosctl and private ACL acceptance, broad ACL rejection, and foreign owner rejection passed.
- [x] Checksum-verified amd64 and arm64 containers built and started.
- [x] Disposable amd64 Talos 1.13.10 to 1.14.1 lifecycle operations had independent node and cluster readbacks; worker reset had positive wipe evidence.
- [x] Codex and Claude Code local and strict SSH launches passed on the final wheel.
- [x] Ansible installation passed twice, with changed=0 on the second run, on the preceding POSIX-equivalent wheel.
- [x] Independent Claude reviews completed; the final Windows owner guard was approved by Opus.

[Candidate CI](https://github.com/CBEPX/talos-mcp-server/actions/runs/36343968208) passed 37 jobs; tag-only PyPI publication was skipped. The full live lifecycle matrix used earlier candidate wheels. The final wheel additionally passed native client checks, private artifact readbacks, and read-only checks on five Talos 1.13.5 nodes.

Known qualification limits: ARM64 Talos VM lifecycle remains incomplete after guest kernel faults; ARM64 container checks passed. Omni-proxied lifecycle and live 1.13.5 mutations were not qualified. Vendor-encrypted support bundles were checked for format only. A single control-plane reset cannot prove a successful wipe when etcd refuses to remove its last member. Upgrade timeout outcomes require independent readback and manual recovery; they are not retried automatically.

Production installation is a separate operational decision. Private lab evidence and credentials are not release artifacts.
