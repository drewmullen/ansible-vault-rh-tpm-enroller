# Modules to build

The playbook is split into `vault_tpm_enroll` and `vault_tpm_proxy`. Mount enable and the auth CA write stay in the demo. `tpm_role` is still the enroll role's missing module, because that role appends `tpm_ids` after enroll. `acl_policy` already covers policy HCL and is used by the demo, not by the host roles.

Build these three in `hashicorp.vault`. The enroller role needs all three. `acl_policy` already covers policy HCL. Packages, files, proxy config, and systemd stay on `ansible.builtin`.

Do not build a secrets-engine module, a KV module, or a `tpm_identity` module for this role. The role does not create secrets. `tpm_enroll` creates the `identity/tpm` record, and unenroll is `state=absent` on that module.

## `auth_method`

Enable, update, and disable an auth mount at `sys/auth/:path`.

The role mounts type `tpm` at `vault_tpm_auth_path` (default `tpm`) when the mount is absent. A second run must leave an existing mount alone. `community.hashi_vault.vault_write` cannot do that: posting an enabled mount returns an error.

An open change in `hashicorp.vault` already sketches `vault_auth_method` for a generic enable. Finish that, including `state=absent`, rather than adding a TPM-only mount module. The same module mounts any auth method.

## `tpm_role`

Create, update, and delete `auth/<mount>/role/:name`.

The role writes `vault_tpm_role_name` with a computed `token_policies` list (the policy created from HCL, then `vault_tpm_token_policies`), plus token TTL, max TTL, period, type, `token_no_default_policy`, bound CIDRs, and a passthrough dict for TPM role fields the caller sets. Reads must be idempotent: the same parameters on a second run report no change.

No module in `hashicorp.vault` can write an arbitrary auth role. A generic write module would still hide the token-policy merge and the idempotency check this role depends on.

## `tpm_enroll`

Enroll and unenroll the TPM on the managed node.

The module runs where the TPM is. It talks to `vault_tpm_device_path` (default `/dev/tpmrm0`) and registers that host with Vault under `vault_tpm_enroll_name`. A controller-side HTTP call cannot create the key. A second run against an already enrolled TPM reports no change. `state=absent` removes that host's enrollment.

`ansible.builtin.command` around `vault tpm enroll` is the stand-in until this exists. It cannot check current enrollment without parsing CLI output, and it cannot unenroll.
