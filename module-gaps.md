# Modules to build

`vault_tpm_enroll` and the demo playbook call `auth_method`, `tpm_auth_config`, `identity_tpm`, and `tpm_role` from https://github.com/drewmullen/hashicorp.vault. Those modules are not in the published `hashicorp.vault` collection yet. The enroll role reads the auth role, appends this host's TPM id, and writes the other role fields back through `tpm_role`. It retries that write until the id is still present.

Build these three in `hashicorp.vault`. The enroller role needs all three. `acl_policy` already covers policy HCL. Packages, files, proxy config, and systemd stay on `ansible.builtin`.

Do not build a secrets-engine module, a KV module, or a `tpm_identity` module for this role. The role does not create secrets. `tpm_enroll` creates the `identity/tpm` record, and unenroll is `state=absent` on that module.

## `auth_method`

Enable, update, and disable an auth mount at `sys/auth/:path`.

The demo playbook mounts type `tpm` at `vault_tpm_auth_path` (default `tpm`) when the mount is absent. The enroll and proxy roles do not. A second run must leave an existing mount alone. `community.hashi_vault.vault_write` cannot do that: posting an enabled mount returns an error.

An open change in `hashicorp.vault` already sketches `vault_auth_method` for a generic enable. Finish that, including `state=absent`, rather than adding a TPM-only mount module. The same module mounts any auth method.

## `tpm_role`

Create, update, and delete `auth/<mount>/role/:name`.

The role writes `vault_tpm_role_name` with `vault_tpm_token_policies`, the token TTL fields, and `vault_tpm_role_config`. Fields the play leaves unset are copied from the current role because the module replaces the role body. Reads must be idempotent: the same parameters on a second run report no change.

No module in `hashicorp.vault` can write an arbitrary auth role. A generic write module would still hide the token-policy merge and the idempotency check this role depends on.

## `tpm_enroll`

Enroll and unenroll the TPM on the managed node.

The module runs where the TPM is. It talks to `vault_tpm_device_path` (default `/dev/tpmrm0`) and registers that host with Vault under `vault_tpm_enroll_name`. A controller-side HTTP call cannot create the key. A second run against an already enrolled TPM reports no change. `state=absent` removes that host's enrollment.

The enroll role calls `hashicorp.vault.identity_tpm` on the managed node. `state=absent` removes that host's enrollment.
