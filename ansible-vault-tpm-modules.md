# Vault TPM enroller role

Ansible role that enrolls a host TPM with Vault Enterprise TPM auth, writes the auth role, installs Vault Proxy with TPM auto-auth, and enables that proxy under systemd.

One play targets many hosts. Hosts that should receive the same token share one auth role and one policy set. Each host enrolls its own TPM. The role does not create a demo policy, a demo secret, or a KV mount.

`hashicorp.vault` (https://github.com/ansible-collections/hashicorp.vault) covers ACL policies, token login, KV, the database secrets engine, PKI, and namespaces. It has no auth-mount module, no generic write, and no TPM module. `auth_login` has no `tpm` choice. Server-side Vault calls use collection modules where they exist. TPM, proxy config, and systemd run on the host with `ansible.builtin`.

## Required inputs

The role fails before it changes anything when one of these is missing.

| Variable | Purpose |
| --- | --- |
| `vault_tpm_api_addr` | Vault address used to enable auth and write the role. Falls back to `VAULT_ADDR`. |
| Admin credential | `vault_tpm_token`, or AppRole `vault_tpm_role_id` and `vault_tpm_secret_id`. The proxy's TPM token is a different credential and is not used here. |
| `vault_tpm_role_name` | Name of `auth/<mount>/role/<name>`. No default. Often set once in group vars and shared by every host. |
| Policy | `vault_tpm_policy_hcl`, `vault_tpm_token_policies`, or both. See below. |
| Vault CA | `vault_tpm_ca_cert` (PEM text) or `vault_tpm_ca_cert_src` (file on the controller). The proxy verifies Vault's certificate. |

## Policies

The role asks for a policy by failing with a message that names both variables when neither is set. It never writes a built-in policy.

| Variable | Default | Purpose |
| --- | --- | --- |
| `vault_tpm_policy_hcl` | `""` | ACL policy body. When non-empty, the role writes it with `hashicorp.vault.acl_policy`. |
| `vault_tpm_policy_name` | `vault_tpm_role_name` | Name of the policy created from `vault_tpm_policy_hcl`. Ignored when the HCL is empty. |
| `vault_tpm_token_policies` | `[]` | Names of policies that already exist in Vault. Appended to the HCL policy on the auth role. |

The auth role's `token_policies` is the HCL policy name, when HCL was provided, followed by `vault_tpm_token_policies`, with duplicates removed. Passing only the list attaches those policies and writes no new policy. Passing only HCL attaches the one policy it writes. Passing both writes the HCL policy and appends the list.

```yaml
vault_tpm_role_name: app-hosts
vault_tpm_policy_hcl: |
  path "secret/data/app/*" {
    capabilities = ["read"]
  }
vault_tpm_policy_name: app-read
vault_tpm_token_policies:
  - audit-read
  - metrics
```

That writes policy `app-read` and sets the auth role's `token_policies` to `app-read`, `audit-read`, and `metrics`.

## Shared settings and per-host overrides

Group vars hold the auth role. Host vars hold the TPM. Ansible precedence is the override mechanism: set the default in group vars, override it on the host or group that differs.

| Variable | Default | Override when |
| --- | --- | --- |
| `vault_tpm_auth_path` | `tpm` | The auth method is mounted somewhere other than `auth/tpm`. |
| `vault_tpm_auth_description` | `TPM auth` | The mount description should say something else. The role enables the mount if it is absent. |
| `vault_tpm_namespace` | `""` | The mount and role live in a namespace. |
| `vault_tpm_token_ttl` | `1h` | The issued token needs a different TTL. |
| `vault_tpm_token_max_ttl` | `""` | A max TTL should be set. Empty leaves Vault's mount default. |
| `vault_tpm_token_period` | `""` | The token should be periodic. Empty leaves it unset. |
| `vault_tpm_token_type` | `""` | `service`, `batch`, or `default`. Empty leaves Vault's default. |
| `vault_tpm_token_no_default_policy` | `false` | The `default` policy should not be added to issued tokens. |
| `vault_tpm_token_bound_cidrs` | `[]` | Issued tokens should be limited to CIDRs. |
| `vault_tpm_role_config` | `{}` | Extra keys to merge into the role write. Use this for TPM role fields this role does not model. |
| `vault_tpm_enroll_name` | `inventory_hostname` | The identity name should not be the inventory hostname. Unique per TPM. |
| `vault_tpm_device_path` | `/dev/tpmrm0` | The host uses a different TPM device, or a simulator socket. |
| `vault_tpm_enroll_metadata` | `{}` | Key-value metadata to pass to `vault tpm enroll`. |
| `vault_tpm_proxy_addr` | `vault_tpm_api_addr` | The host reaches Vault at a different address than the controller. |
| `vault_tpm_proxy_user` | `vault-proxy` | A different Unix account should own the socket. |
| `vault_tpm_proxy_config_path` | `/etc/vault-proxy/tpm.hcl` | The HCL should live elsewhere. |
| `vault_tpm_ca_cert_dest` | `/etc/vault-proxy/ca.pem` | The CA file should live elsewhere. |
| `vault_tpm_cert_dir` | `/var/lib/vault-proxy/<user>/tpm` | The `tpm_cert` destination directory should live elsewhere. |
| `vault_tpm_cert_name` | `host_identity` | The `tpm_cert` block label should change. |
| `vault_tpm_csr_cn` | `vault_tpm_enroll_name` | The CSR common name should differ from the enroll name. |
| `vault_tpm_renew_percent` | `20` | Renew earlier or later than 20 percent before expiry. |
| `vault_tpm_renew_min_backoff` | `5s` | |
| `vault_tpm_renew_max_backoff` | `5m` | |
| `vault_tpm_use_auto_auth_token` | `force` | The proxy should not force the auto-auth token. |
| `vault_tpm_socket_dir` | `/run/vault-proxy` | |
| `vault_tpm_socket_mode` | `"600"` | |
| `vault_tpm_service_name` | `vault-proxy` | |
| `vault_tpm_service_enabled` | `true` | |
| `vault_tpm_service_state` | `started` | |
| `vault_tpm_packages` | `tpm2-tss`, `tpm2-tools` | The host already has the TPM stack, or needs extra packages. Set `[]` to install nothing. |
| `vault_tpm_install_swtpm` | `false` | This host should run `swtpm` instead of a hardware TPM. Also set `vault_tpm_device_path` to the simulator socket. |
| `vault_tpm_version` | `""` | Install this Vault build under `vault_tpm_bin_path`. Empty means `vault` is already on the host. |
| `vault_tpm_bin_path` | `/usr/local/bin/vault` | |
| `vault_tpm_proxy_config` | `""` | Full proxy HCL. When set, it replaces the generated file. |
| `vault_tpm_verify_path` | `""` | After the proxy is up, read this path through the socket with `VAULT_TOKEN` unset. Empty skips the check. The role does not write that secret. |

`vault_tpm_install_swtpm` and a localhost port forward are off. They exist for a lab host whose TPM is `swtpm` and whose Vault certificate is for `127.0.0.1`. A fleet role leaves both off.

## What each host run does

1. Fail unless the role name, a policy source, the CA, and an admin credential are set.
2. Read `sys/health` with `ansible.builtin.uri`. Continue only when the listener is HTTPS and the version is Enterprise 2.2 or newer.
3. Enable `auth/<vault_tpm_auth_path>` with type `tpm` when it is absent.
4. When `vault_tpm_policy_hcl` is non-empty, write `vault_tpm_policy_name` with `hashicorp.vault.acl_policy`.
5. Write `auth/<mount>/role/<vault_tpm_role_name>` with the computed `token_policies`, the token defaults, and `vault_tpm_role_config`.
6. On the host, install `vault_tpm_packages` with `ansible.builtin.package`. Install Vault only when `vault_tpm_version` is set (`ansible.builtin.get_url` and `ansible.builtin.unarchive`, or `dnf` from the HashiCorp repo).
7. Create `vault_tpm_proxy_user` and the config, CA, and cert directories (`ansible.builtin.user`, `ansible.builtin.file`).
8. Copy the CA (`ansible.builtin.copy`) and render the proxy HCL (`ansible.builtin.template`), unless `vault_tpm_proxy_config` is set.
9. Enroll with `vault tpm enroll` on that host (`ansible.builtin.command`). The key is created inside the TPM, so this cannot be an HTTP call from the controller. Output that says the TPM is already enrolled is success.
10. Install and enable `vault-proxy.service` (`ansible.builtin.template`, `ansible.builtin.systemd_service`). The unit runs `vault proxy`.
11. When `vault_tpm_verify_path` is set, read it through the unix socket as `vault_tpm_proxy_user`.

Steps 3 and 5 run from the controller, once per play is enough when every host shares the role, but running them per host is safe if the writes are idempotent. Steps 6 through 11 run on the host and differ per TPM.

## Modules

| Step | Module |
| --- | --- |
| Health check | None. `ansible.builtin.uri` on `/v1/sys/health`. |
| Enable `auth/tpm` | None. An open change proposes `vault_auth_method`, which would only enable the mount. |
| Write policy HCL | `hashicorp.vault.acl_policy`, and only when HCL is set. |
| Write the auth role | None. No typed role module and no generic write. |
| Packages, user, dirs, CA, HCL, systemd | `ansible.builtin.package`, `user`, `file`, `copy`, `template`, `systemd_service`. |
| Enroll | None. `ansible.builtin.command` on the host. |

`community.hashi_vault.vault_write` can post the mount and the role. Enabling an auth method that already exists returns an error, so it is a weak stand-in for the missing modules.

Typed modules worth adding to `hashicorp.vault`:

1. `auth_method` enables and disables the TPM mount (`sys/auth/:path`).
2. `tpm_role` writes `auth/<mount>/role/:name`, including the computed `token_policies` and the token fields above.
3. `tpm_enroll` runs on the managed node, talks to the TPM device, and registers that host.

This role does not need a secrets-engine module or a KV module. It does not create secrets. `vault tpm enroll` creates the `identity/tpm` record, so a separate identity module is not part of enrollment. Unenroll, if a later role needs it, is `state=absent` on `tpm_enroll`.
