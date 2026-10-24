# Version 0.4.1 release and installation

[Issue 13](https://github.com/CBEPX/talos-mcp-server/issues/13) tracks publication and the existing read-only local/SSH installation update. The operator authorized both stages on 2026-10-24.

The source includes the diagnostic warning fix and both dependency follow-ups. PR 12 merged as 9a2f350642d8b0fa29084ee6c075b57c07c2700b. Main CI 40044538256 passed 37 jobs. Fresh GitHub readback reports all 43 tracked advisories fixed and zero open alerts. Issue 9 is closed. No alert was dismissed.

This change prepares version 0.4.1 metadata and release documentation. The application runtime and CI workflow remain unchanged from the qualified main commit. Test version assertions and Ansible example pins now match 0.4.1. The release PR, tag publication and deployed-client acceptance remain pending until their exact artifacts and runtime checks pass. Historical 0.4.0 and intermediate-candidate evidence below does not prove those stages.

## Earlier qualification records

## Version 0.4.0 delivery

The release candidate passed qualification on 2026-09-27. The final wheel SHA-256 is `8d2b09680f4180a340dcf1bbf7985d9a7338552030c3ca1c90a63918a59f5d66`.

- [x] Required Ruff, MyPy, Black, pytest, and uv lock checks passed.
- [x] Installed-wheel stdio, cancellation, and EOF cleanup passed on Linux, macOS, and Windows for Python 3.10 through 3.14, with minimum and current MCP SDK dependencies.
- [x] Windows native talosctl and private ACL acceptance, broad ACL rejection, and foreign owner rejection passed.
- [x] Checksum-verified amd64 and arm64 containers built and started.
- [x] Disposable amd64 Talos 1.13.10 to 1.14.1 lifecycle operations on earlier candidate wheels had independent node and cluster readbacks; worker reset had positive wipe evidence.
- [x] Codex and Claude Code local and strict SSH launches passed on the final wheel.
- [x] Ansible installation passed twice, with changed=0 on the second run, on the preceding POSIX-equivalent wheel.
- [x] Independent source and evidence reviews completed; findings were resolved or recorded as qualification limits and nonblocking follow-ups. The final Windows owner guard received a separate security review.

[Candidate CI](https://github.com/CBEPX/talos-mcp-server/actions/runs/36343968208) passed 37 jobs; tag-only PyPI publication was skipped. The full live lifecycle matrix used earlier candidate wheels. The final wheel additionally passed native client checks, private artifact readbacks, and read-only checks on five Talos 1.13.5 nodes.

Known qualification limits: ARM64 Talos VM lifecycle remains incomplete after guest kernel faults; ARM64 container checks passed. Omni-proxied lifecycle and live 1.13.5 mutations were not qualified. Vendor-encrypted support bundles were checked for format only. A single control-plane reset cannot prove a successful wipe when etcd refuses to remove its last member. Upgrade timeout outcomes require independent readback and manual recovery; they are not retried automatically.

Production installation is a separate operational decision. Private lab evidence and credentials are not release artifacts.

Candidate CI container manifest digests (run 36343968208; local CI images, not registry publications):

- `amd64`: `sha256:1b4ccee2406542a950c3fdb9316f6dbda5b47d2958d15a54fb028c28fee4371c`.
- `arm64`: `sha256:a6d0950a47e3ec3041983736549c733b237fa0e706fc8b69fa5148a01c25cdc2`.

### Diagnostic warning follow-up (unreleased)

[Issue 7](https://github.com/CBEPX/talos-mcp-server/issues/7) preserves version-skew warnings in the version resource, health resource, and events tool. Native-fixture regressions include matching-version controls. A real MCP stdio regression checks consumer-visible warnings. This follow-up changes response text only. It does not change operation policy, dependencies, event-window metadata, or credentials.

The 0.4.0 release evidence above belongs to that release.

Local macOS Python 3.12 checks passed: uv lock, Ruff, MyPy, Black, and 113 tests. The Windows native ACL test was skipped. Installed-wheel stdio checks passed with the minimum and current MCP SDK ranges. Independent Claude source review found no blocking issue. Its reviewer did not execute tests.

Release, installation, full platform CI, and deployed qualification are separate stages.

### Dependency hardening follow-up (unreleased)

[Issue 9](https://github.com/CBEPX/talos-mcp-server/issues/9) updates the lock for 41 advisories across 11 packages. The [triage record](docs/security/dependency-triage-20261024.md) lists each affected range, precondition, application path and selected fix. No alert was dismissed.

Local lock, Ruff, MyPy, Black and full-suite checks passed with 113 tests and one Windows-only skip. Installed-wheel stdio passed on Python 3.10 and 3.12 with locked dependencies, and on Python 3.12 with current resolution. Native cancellation and EOF cleanup passed. Independent Claude source review approved the source candidate without blocking findings. The reviewer did not execute tests or recheck all GHSA ranges. Platform CI is pending at this checkpoint. The 0.4.0 release evidence above does not qualify this dependency update. Release, deployment and installed-client checks remain separate.

### Dependency graph follow-up (unreleased)

PR 10 merged as 8f9d5d6f259caa93681e22f9017c30b0035b38c2, and main CI 40038485985 passed 37 jobs. All original 41 alerts became fixed. The refreshed graph also reported critical certifi alert 49 and high Black alert 50. [The follow-up record](docs/security/dependency-followup-20261024.md) documents their preconditions and selected fixes.

This candidate updates certifi to 2026.10.19 and Black to 26.10.1. The range check is clear for all 43 captured advisories. Local lock, Ruff, MyPy and Black checks passed, with 113 tests and one Windows-only skip. Locked Python 3.10/3.12 and current Python 3.12 installed-wheel stdio checks passed, including native cancellation and EOF cleanup. The affected emSign root is absent from the updated locked bundle. Independent Claude source review approved without blocking findings. The reviewer did not execute tests. Platform CI is pending at this local checkpoint. Issue 9 remains open until the follow-up merges and alerts are checked again. No release or installation occurred.
