# Locked dependency triage — 2026-10-24

[Issue 9](https://github.com/CBEPX/talos-mcp-server/issues/9) tracks this change. The reviewed source baseline is `8882de80c6c6e8c5b7b7d125c6efb4e769afee61`.

The GitHub API returned 41 open alerts in `uv.lock`: 2 critical, 14 high, 18 medium and 7 low. These alerts cover 11 normalized package names. Affected versions establish dependency exposure. They do not establish an exploitable application path. No alert was dismissed.

## Selected versions

The resolver changes the 11 affected packages and two dependencies required by Black. The package count remains 64. MCP remains at 1.30.0 within `mcp>=1.30,<2`. The Python floor remains 3.10. Each selected fix has PyPI metadata that supports this floor.

| Package | Previous lock | Selected lock |
| --- | --- | --- |
| anyio | 4.12.0 | 4.14.2 |
| black | 25.12.0 | 26.3.1 |
| cryptography | 46.0.3 | 50.0.0 |
| idna | 3.11 | 3.15 |
| pathspec | 0.12.1 | 1.1.1 |
| pydantic-settings | 2.12.0 | 2.14.2 |
| pygments | 2.19.2 | 2.20.0 |
| pyjwt | 2.10.1 | 2.15.0 |
| pytest | 9.0.2 | 9.0.3 |
| python-dotenv | 1.2.1 | 1.2.2 |
| python-multipart | 0.0.21 | 0.0.31 |
| pytokens | 0.3.0 | 0.4.1 |
| starlette | 0.50.0 | 1.3.1 |

Black 26.3.1 requires `pathspec>=1.0.0` and `pytokens~=0.4.0`. Its stable formatting conflicts with the explicit Ruff setting `lines-after-imports=2`. This change removes that setting and uses Ruff automatic spacing. All import rules remain enabled. Six files lose seven blank lines. Their parsed ASTs remain identical.

The lock controls repository builds and `uv sync --locked`. The wheel does not embed this lock or impose these transitive minimum versions. An existing installed environment requires a separate dependency update. A fresh wheel installation resolves dependencies from package metadata.

## Reviewed application paths

The source contains 26 production Python files. The application creates a low-level MCP Server and serves it through stdio in `cli.run_mcp_server`. Talos operations use a native talosctl subprocess. Native Go TLS is outside this Python dependency assessment.

The following codes describe the reviewed surface, rather than every possible use of the imported SDK:

| Code | Source evidence and applicability |
| --- | --- |
| JWT | No application JWT import or decode path. In the 110 MCP 1.30.0 Python files, JWT calls occur only in client/auth/extensions/client_credentials.py at lines 252 and 464. Both calls encode tokens. The app does not configure those OAuth client flows. |
| CRYPTO | No application cryptography import, certificate verifier, PKCS#7 decryptor or Python elliptic-curve key path. The SDK includes cryptography through PyJWT crypto support. Arbitrary SDK consumers remain outside this assessment. |
| BUNDLED | The dependency is present as a wheel, so its bundled OpenSSL must be updated. No application Python TLS or crypto path was found. This does not qualify OpenSSL linked by source builds or other programs. |
| TLS | No application Python HTTP client or domain conversion path. The reviewed stdio probe observed no TLSStream.wrap or connect_tcp call. Other transports and future HTTP use remain outside that probe. |
| POOL | TalosClient uses AnyIO CancelScope. It does not use anyio.to_process.run_sync or the AnyIO process pool. Native Talos processes use the application subprocess path. |
| HTTP | No application HTTP transport, Starlette endpoint, form parser or StaticFiles configuration. SDK imports alone do not activate these routes. Imported SDK HTTP consumers remain outside this review. |
| SETTINGS | core/settings.py configures BaseSettings with env_prefix only. It does not configure NestedSecretsSettingsSource, nested secret directories or a custom source loader. |
| DOTENV | No application set_key or unset_key call. Read-side settings loading does not perform the vulnerable rewrite. |
| DEV | Black is a development dependency. Repository checks supply fixed formatting arguments, without python-cell-magics input. Other developer invocations remain possible. The separate pre-commit hook still pins affected Black 24.4.2. Development minimum requirements also permit older versions outside the lock. |
| PYTEST | Tests use pytest temporary fixtures. Shared-host temporary-directory interference is relevant to development and CI, rather than the deployed stdio server. Update the test dependency. |
| LEXER | Rich and developer tools include Pygments. The application does not select AdlLexer or expose an arbitrary lexer service. Other local uses remain outside this review. |

A prior passive runtime probe used synthetic configuration and no live credentials. It exercised initialize, tool listing, version/health/config resources and bounded events through real stdio. It observed no JWT decode or Python TLS entry. Positive controls verified the observer. This bounded result does not prove universal non-exploitability.

## Per-advisory decisions

Each row records the official affected range, first fixed version, required input or configuration, and the application path above. **Update** means the selected lock removes the affected version. It does not mean the application reproduced the exploit. Advisory links are the primary sources.

| Alert / advisory | Package | Severity | Affected range / first fix | Preconditions | Path | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| #3 [GHSA-wp53-j4wj-2cfg](https://github.com/advisories/GHSA-wp53-j4wj-2cfg) | python-multipart | high | `< 0.0.22` / 0.0.22 | Multipart file handling enables UPLOAD_DIR and UPLOAD_KEEP_FILENAME, then flushes an attacker-named upload to disk. | HTTP | Update to 0.0.31 |
| #4 [GHSA-r6ph-v2qm-q3c2](https://github.com/advisories/GHSA-r6ph-v2qm-q3c2) | cryptography | high | `<= 46.0.4` / 46.0.5 | An untrusted SECT public key without subgroup validation enters ECDSA or ECDH operations. | CRYPTO | Update to 50.0.0 |
| #5 [GHSA-752w-5fwx-jx9f](https://github.com/advisories/GHSA-752w-5fwx-jx9f) | pyjwt | high | `<= 2.11.0` / 2.12.0 | JWT verification accepts a token with unsupported critical header extensions. | JWT | Update to 2.15.0 |
| #6 [GHSA-m959-cc7f-wv43](https://github.com/advisories/GHSA-m959-cc7f-wv43) | cryptography | low | `< 46.0.6` / 46.0.6 | The certificate verifier combines a wildcard certificate, excluded DNS subtree and disallowed peer name. | CRYPTO | Update to 50.0.0 |
| #7 [GHSA-5239-wwwm-4pmq](https://github.com/advisories/GHSA-5239-wwwm-4pmq) | pygments | low | `< 2.20.0` / 2.20.0 | Crafted local text reaches Pygments AdlLexer GUID matching. | LEXER | Update to 2.20.0 |
| #8 [GHSA-p423-j2cm-9vmq](https://github.com/advisories/GHSA-p423-j2cm-9vmq) | cryptography | medium | `>= 45.0.0, < 46.0.7` / 46.0.7 | A non-contiguous Python buffer enters a cryptography buffer API, such as Hash.update. | CRYPTO | Update to 50.0.0 |
| #9 [GHSA-6w46-j5rx-g56g](https://github.com/advisories/GHSA-6w46-j5rx-g56g) | pytest | medium | `< 9.0.3` / 9.0.3 | A local user interferes with predictable pytest temporary directories on UNIX. | PYTEST | Update to 9.0.3 |
| #10 [GHSA-mj87-hwqh-73pj](https://github.com/advisories/GHSA-mj87-hwqh-73pj) | python-multipart | medium | `< 0.0.26` / 0.0.26 | An untrusted multipart body contains a large preamble or epilogue. | HTTP | Update to 0.0.31 |
| #11 [GHSA-mf9w-mj56-hr94](https://github.com/advisories/GHSA-mf9w-mj56-hr94) | python-dotenv | medium | `< 1.2.2` / 1.2.2 | An attacker controls an env-file symlink and set_key or unset_key takes a cross-device rewrite fallback. | DOTENV | Update to 1.2.2 |
| #12 [GHSA-pp6c-gr5w-3c5g](https://github.com/advisories/GHSA-pp6c-gr5w-3c5g) | python-multipart | high | `< 0.0.27` / 0.0.27 | An untrusted multipart body contains oversized or numerous part headers. | HTTP | Update to 0.0.31 |
| #13 [GHSA-65pc-fj4g-8rjx](https://github.com/advisories/GHSA-65pc-fj4g-8rjx) | idna | medium | `< 3.15` / 3.15 | Large crafted domain-name input reaches IDNA conversion before length rejection. | TLS | Update to 3.15 |
| #14 [GHSA-86qp-5c8j-p5mr](https://github.com/advisories/GHSA-86qp-5c8j-p5mr) | starlette | medium | `<= 1.0.0` / 1.0.1 | A malformed Host header changes reconstructed URL path and application security relies on that path. | HTTP | Update to 1.3.1 |
| #15 [GHSA-jq35-7prp-9v3f](https://github.com/advisories/GHSA-jq35-7prp-9v3f) | pyjwt | medium | `>= 2.9.0, < 2.13.0` / 2.13.0 | Verification supplies a PyJWK key and an algorithm policy that differs from the key-bound algorithm. | JWT | Update to 2.15.0 |
| #16 [GHSA-xgmm-8j9v-c9wx](https://github.com/advisories/GHSA-xgmm-8j9v-c9wx) | pyjwt | high | `< 2.13.0` / 2.13.0 | A verifier mixes HMAC/asymmetric algorithms and supplies raw public-key JWK JSON as the key. | JWT | Update to 2.15.0 |
| #17 [GHSA-w7vc-732c-9m39](https://github.com/advisories/GHSA-w7vc-732c-9m39) | pyjwt | medium | `>= 2.8.0, <= 2.12.1` / 2.13.0 | Detached b64=false JWS verification parses an oversized unused compact payload before rejecting it. | JWT | Update to 2.15.0 |
| #18 [GHSA-537c-gmf6-5ccf](https://github.com/advisories/GHSA-537c-gmf6-5ccf) | cryptography | high | `>= 0.5.0, < 48.0.1` / 48.0.1 | A cryptography wheel includes the affected OpenSSL build. Source builds depend on the separately linked OpenSSL. | BUNDLED | Update to 50.0.0 |
| #19 [GHSA-x746-7m8f-x49c](https://github.com/advisories/GHSA-x746-7m8f-x49c) | starlette | medium | `< 1.1.0` / 1.1.0 | An HTTPEndpoint route omits explicit methods and an attacker names an internal callable as an HTTP method. | HTTP | Update to 1.3.1 |
| #20 [GHSA-wqp7-x3pw-xc5r](https://github.com/advisories/GHSA-wqp7-x3pw-xc5r) | starlette | high | `< 1.1.0` / 1.1.0 | Windows StaticFiles resolves an attacker-controlled UNC path and can make outbound SMB connections. | HTTP | Update to 1.3.1 |
| #21 [GHSA-vffw-93wf-4j4q](https://github.com/advisories/GHSA-vffw-93wf-4j4q) | python-multipart | low | `< 0.0.30` / 0.0.30 | An upstream inspector and multipart parser disagree about extended Content-Disposition parameters. | HTTP | Update to 0.0.31 |
| #22 [GHSA-6jv3-5f52-599m](https://github.com/advisories/GHSA-6jv3-5f52-599m) | python-multipart | low | `< 0.0.30` / 0.0.30 | An upstream inspector uses ampersands alone while QuerystringParser also treats semicolons as field separators. | HTTP | Update to 0.0.31 |
| #23 [GHSA-v9pg-7xvm-68hf](https://github.com/advisories/GHSA-v9pg-7xvm-68hf) | python-multipart | low | `< 0.0.31` / 0.0.31 | A bespoke handler forwards a negative Content-Length to parse_form without normalization. | HTTP | Update to 0.0.31 |
| #24 [GHSA-5rvq-cxj2-64vf](https://github.com/advisories/GHSA-5rvq-cxj2-64vf) | python-multipart | high | `< 0.0.30` / 0.0.30 | A urlencoded body contains many semicolon separators and enters QuerystringParser. | HTTP | Update to 0.0.31 |
| #25 [GHSA-jp82-jpqv-5vv3](https://github.com/advisories/GHSA-jp82-jpqv-5vv3) | starlette | low | `< 1.3.0` / 1.3.0 | An ASGI server forwards a path without a leading slash and code trusts reconstructed URL authority before routing. | HTTP | Update to 1.3.1 |
| #26 [GHSA-82w8-qh3p-5jfq](https://github.com/advisories/GHSA-82w8-qh3p-5jfq) | starlette | high | `>= 0.4.1, < 1.3.1` / 1.3.1 | HTTP request.form parses urlencoded fields while relying on max_fields or max_part_size limits. | HTTP | Update to 1.3.1 |
| #27 [GHSA-4xgf-cpjx-pc3j](https://github.com/advisories/GHSA-4xgf-cpjx-pc3j) | pydantic-settings | medium | `>= 2.12.0, < 2.14.2` / 2.14.2 | NestedSecretsSettingsSource uses nested directories and an attacker can place symlinks inside secrets_dir. | SETTINGS | Update to 2.14.2 |
| #31 [GHSA-fhv5-28vv-h8m8](https://github.com/advisories/GHSA-fhv5-28vv-h8m8) | pyjwt | low | `>= 2.0.0, <= 2.12.1` / 2.13.0 | Unknown token kid traffic triggers failed JWKS fetches that clear cached keys. | JWT | Update to 2.15.0 |
| #32 [GHSA-993g-76c3-p5m4](https://github.com/advisories/GHSA-993g-76c3-p5m4) | pyjwt | medium | `>= 2.0.0, <= 2.12.1` / 2.13.0 | An attacker influences the URI supplied to PyJWKClient and selects a non-HTTP(S) scheme. | JWT | Update to 2.15.0 |
| #33 [GHSA-3936-cmfr-pm3m](https://github.com/advisories/GHSA-3936-cmfr-pm3m) | black | high | `>= 24.3.0, < 26.3.1` / 26.3.1 | An attacker controls Black --python-cell-magics values used in a cache filename. | DEV | Update to 26.3.1 |
| #34 [GHSA-g6cj-pr64-35w5](https://github.com/advisories/GHSA-g6cj-pr64-35w5) | cryptography | high | `>= 44.0.0, < 50.0.0` / 50.0.0 | Untrusted PKCS#7 EnvelopedData reaches RSA decryption and an adaptive caller observes errors or timing. | CRYPTO | Update to 50.0.0 |
| #36 [GHSA-5p39-cfhj-2xmp](https://github.com/advisories/GHSA-5p39-cfhj-2xmp) | anyio | medium | `< 4.14.2` / 4.14.2 | AnyIO process-pool worker code fills its undrained stderr pipe. | POOL | Update to 4.14.2 |
| #37 [GHSA-82r6-8w77-94w6](https://github.com/advisories/GHSA-82r6-8w77-94w6) | anyio | critical | `< 4.14.2` / 4.14.2 | A redirected TLS connection uses a non-ASCII hostname that follows IDNA 2003 encoding. | TLS | Update to 4.14.2 |
| #38 [GHSA-jwv3-5hgf-82ww](https://github.com/advisories/GHSA-jwv3-5hgf-82ww) | cryptography | high | `>= 42.0.0, < 49.0.0` / 49.0.0 | The certificate verifier processes repeated self-signed intermediate candidates in an attacker-controlled chain. | CRYPTO | Update to 50.0.0 |
| #39 [GHSA-m2h6-j472-rp4c](https://github.com/advisories/GHSA-m2h6-j472-rp4c) | cryptography | medium | `>= 45.0.0, < 49.0.0` / 49.0.0 | The cryptography certificate verifier accepts a wildcard SAN outside a permitted DNS subtree. | CRYPTO | Update to 50.0.0 |
| #41 [GHSA-w6j9-cwv2-h6wq](https://github.com/advisories/GHSA-w6j9-cwv2-h6wq) | pyjwt | medium | `>= 2.9.0, <= 2.13.0` / 2.14.0 | A malformed RSA key enters a JWK Set and aborts parsing of the complete set. | JWT | Update to 2.15.0 |
| #42 [GHSA-2gx3-rcp4-g85q](https://github.com/advisories/GHSA-2gx3-rcp4-g85q) | pyjwt | medium | `<= 2.13.0` / 2.14.0 | Unknown token kid values repeatedly force JWKS refresh without an effective refresh bound. | JWT | Update to 2.15.0 |
| #43 [GHSA-p4g4-x82p-q773](https://github.com/advisories/GHSA-p4g4-x82p-q773) | pyjwt | high | `>= 2.4.0, < 2.14.0` / 2.14.0 | Mixed HMAC/asymmetric verification uses DER public-key bytes as a key. | JWT | Update to 2.15.0 |
| #44 [GHSA-9v7f-9g4p-ffgj](https://github.com/advisories/GHSA-9v7f-9g4p-ffgj) | pyjwt | high | `<= 2.13.0` / 2.14.0 | PyJWKClient follows an attacker-influenced JWKS redirect, with trusted headers or key material at risk. | JWT | Update to 2.15.0 |
| #45 [GHSA-ffc3-869f-jxw9](https://github.com/advisories/GHSA-ffc3-869f-jxw9) | pyjwt | critical | `<= 2.13.0` / 2.14.0 | Mixed HMAC/asymmetric algorithms and raw PEM formatting bypass the asymmetric-key guard. | JWT | Update to 2.15.0 |
| #46 [GHSA-hxm8-2xgr-2p9m](https://github.com/advisories/GHSA-hxm8-2xgr-2p9m) | pyjwt | medium | `<= 2.13.0` / 2.14.0 | A verifier accepts alternate signature serialization and revocation identifies tokens by raw serialized text. | JWT | Update to 2.15.0 |
| #47 [GHSA-jwrc-g2q2-pq5p](https://github.com/advisories/GHSA-jwrc-g2q2-pq5p) | pyjwt | medium | `<= 2.13.0` / 2.14.0 | Attacker-controlled malformed PEM input reaches is_pem_format. | JWT | Update to 2.15.0 |
| #48 [GHSA-42vr-xj54-vc7v](https://github.com/advisories/GHSA-42vr-xj54-vc7v) | pyjwt | medium | `>= 2.0.0a1, <= 2.14.0` / 2.15.0 | Untrusted recursive payload with signature verification disabled or PyJWKClient pre-verification parsing. | JWT | Update to 2.15.0 |

For GHSA-42vr-xj54-vc7v, the later maintainer release update supersedes the earlier statement that no fix existed. PyJWT 2.15.0 contains the payload-parser fix. The confirmed impact is a request-level uncaught exception. The maintainer did not establish process termination or persistent exhaustion.

For GHSA-g6cj-pr64-35w5, the distinguishable RSA failure channel depends on the linked backend. The advisory identifies OpenSSL 3.0/3.1, LibreSSL and BoringSSL as affected configurations. The update does not provide content authentication for PKCS#7.

## Qualification and remaining gates

An executable check compared every locked package version with each captured GitHub advisory range. It found 41 affected pairs before the update and zero afterward. This covers the captured advisory set, not undisclosed vulnerabilities or a complete exploit reproduction.

Local macOS Python 3.12 checks passed: lock consistency, Ruff, MyPy, Black and the full suite with 113 passed tests. One Windows native ACL test was skipped. Installed-wheel stdio passed with locked runtime constraints on Python 3.10.22 and 3.12.12. It also passed with current dependency resolution on Python 3.12.12. These checks included native talosctl cancellation and EOF cleanup.

The existing CI matrix remains unchanged: Linux, macOS and Windows, Python 3.10 through 3.14, and minimum/current MCP SDK resolution. Independent Claude source review approved the lock and application changes without blocking findings. It did not run tests or compare advisory ranges with GHSA. Its SDK check covered the two cited encode calls, rather than every SDK file. The coordinator performed the broader AST scan and range check. Platform CI is pending at this local checkpoint. Release, installation and live Talos qualification remain separate stages. Re-read Dependabot after merge before closing issue 9.
