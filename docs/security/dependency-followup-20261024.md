# Dependency graph follow-up — 2026-10-24

[Issue 9](https://github.com/CBEPX/talos-mcp-server/issues/9) tracks this follow-up to PR 10. The source baseline is `8f9d5d6f259caa93681e22f9017c30b0035b38c2`.

Main CI 40038485985 passed all 37 jobs after PR 10 merged. Its dependency graph update marked the original 41 alerts as fixed. The refreshed graph also reported two additional alerts. No alert was dismissed.

## Advisory decisions

| Alert | Package and alerted version | Severity | Affected range | Selected fix | Preconditions and reviewed application path | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| [49 / GHSA-6q48-6c7w-9gw2](https://github.com/advisories/GHSA-6q48-6c7w-9gw2) | certifi 2025.11.12 | Critical | `>=2019.03.09, <2026.10.19` | 2026.10.19 | The bundle trusts `emSign ECC Root CA - G3`. An attacker with a compromised intermediate key and an intercepted connection can impersonate a TLS server. The app uses stdio and native talosctl, rather than Python HTTP/TLS. Python download tools and imported SDK HTTP consumers are separate surfaces. | Update the locked CA bundle. Do not dismiss the alert based on the app transport. |
| [50 / GHSA-cg8m-r9f2-5wm2](https://github.com/advisories/GHSA-cg8m-r9f2-5wm2) | Black 26.3.1 | High | `<26.10.1` | 26.10.1 | The bundled psf/black GitHub Action uses `use_pyproject: true` and reads an unvalidated `tool.black.required-version`. Repository CI invokes Black through uv and does not use that Action. It does not configure required-version. | Update the development lock. The reviewed repository does not configure the vulnerable Action path. |

The certifi advisory concerns Python clients that use its CA bundle. It does not assess the TLS implementation in native talosctl. Version 2026.10.18 removed all emSign roots. Version 2026.10.19 restored unaffected emSign roots and kept `emSign ECC Root CA - G3` excluded. This changes certificate trust for those Python clients. No credentials or Talos configuration are changed.

The separate pre-commit Black pin and permissive development minimum requirements remain outside this lock update. They retain the limitations recorded in the [initial triage](dependency-triage-20261024.md).

## Compatibility and qualification

Only two locked package versions change. The lock retains 64 packages and MCP 1.30.0 within `mcp>=1.30,<2`. The Python floor stays at 3.10. Official PyPI metadata supports Python >=3.7 for [certifi 2026.10.19](https://pypi.org/project/certifi/2026.10.19/) and >=3.10 for [Black 26.10.1](https://pypi.org/project/black/26.10.1/).

The captured set contains the original 41 advisories and both additional advisories. The executable range check found two affected pairs before this follow-up and zero afterward. This checks the captured ranges, rather than reproducing each exploit or establishing universal security.

Local lock, Ruff, MyPy and Black checks passed. The full suite passed 113 tests, with one Windows-only ACL test skipped. Installed-wheel stdio and native cancellation/EOF cleanup passed on Python 3.10.22 and 3.12.12 with locked runtime dependencies, and on Python 3.12.12 with current resolution. The locked wheel environments use certifi 2026.10.19. Current resolution uses certifi 2026.10.23. All three environments use MCP 1.30.0 and clear the captured advisory ranges. A bundle check found `emSign ECC Root CA - G3` in certifi 2025.11.12 and confirmed its absence in 2026.10.19. This check did not reproduce an intercepted TLS connection. Independent Claude source review approved without blocking findings. It checked the advisory facts and Python metadata, but did not execute tests or the bundle probe. Platform CI is pending at this local checkpoint. The existing platform CI matrix remains unchanged. A new merge decision and a fresh alert readback are required after publication. Release and deployed installation remain separate stages.
