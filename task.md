# Version 0.4.0 delivery

The 0.4.0 source repairs the MCP profile, native command, and artifact contracts. The release remains unqualified until the required checks and live disposable Talos readbacks finish.

- [ ] Required Ruff, MyPy, Black, pytest, and uv lock checks pass on the final source.
- [ ] Installed-wheel stdio checks pass on Linux, macOS, and Windows for Python 3.10 through 3.14.
- [ ] Native subprocess cancellation and EOF cleanup pass on each platform; Windows also checks talosctl.exe and private ACL acceptance and rejection.
- [ ] Checksum-verified Docker images build and start on amd64 and arm64. Record each image digest.
- [ ] Disposable Talos 1.13 and 1.14 lifecycle results have independent node and cluster readbacks.
- [ ] Codex and Claude Code local and strict SSH launches use the same reviewed wheel.
- [ ] The Ansible installation role runs twice, with changed=0 on the second run.
- [ ] Independent review closes source and evidence findings before release.

The qualification branch triggers CI only. A passing source check or offline wheel smoke does not prove a live Talos operation. Production installation and public release remain separate gates.
