# Reviewed jump-host installation

This role installs one reviewed wheelhouse and one checksum-pinned talosctl. It does not install cluster credentials. It does not change a global talosctl installation or client configuration.

Prepare a wheelhouse on the Ansible controller. Include the reviewed Talos MCP wheel and all pinned dependency wheels. Record the project wheel SHA-256. Set a unique release ID for each build. Supply these variables through a private vars file:

~~~yaml
talos_mcp_release_id: v0.4.0-reviewed-build
talos_mcp_wheelhouse: /path/to/reviewed/wheelhouse
talos_mcp_wheel_file: talos_mcp_server-0.4.0-py3-none-any.whl
talos_mcp_wheel_sha256: REPLACE_WITH_64_HEX_DIGITS
talos_mcp_talosctl_sha256: REPLACE_WITH_MATCHING_RELEASE_AND_ARCH_SHA256
~~~

Use the talosctl digest for the target architecture from ../../talosctl-checksums.txt. The version comes from ../../.talosctl-version. The target needs Python 3, venv, and access to the official Talos release URL. The operator supplies an inventory group named talos_mcp_jump_hosts and reviewed SSH transport.

~~~sh
ansible-playbook -i /path/to/inventory examples/ansible/install.yml -e @/path/to/private-pins.yml
~~~

Run the same playbook again and require changed=0. The service account reads a separate credential after an operator installs it. Point MCP clients at the absolute release paths. SSH connection does not run this playbook.
