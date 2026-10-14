# vault_tpm_enroll and vault_tpm_proxy

Two roles for Vault Enterprise TPM auth on Red Hat hosts.

`vault_tpm_enroll` enrolls the host TPM and appends that TPM id to an auth role. `vault_tpm_proxy` installs the API proxy config with TPM auto-auth and runs it under systemd as `vault agent`.

Neither role enables `auth/tpm`, writes `auth/<mount>/config`, or writes an ACL policy. Do that before enroll. The [demo](demo/README.md) playbook does it for a lab Vault.

## Example Execution

One playbook run applies both roles. Enroll runs one host at a time so each TPM id is appended to the shared auth role. The proxy install then runs across the group.

```bash
ansible-playbook -i examples/inventory.yml examples/enroll.yml
```

## Requirements

- Ansible 2.16 or newer, with facts gathered.
- The `hashicorp.vault` fork that ships `auth_method`, `tpm_auth_config`, `identity_tpm`, and `tpm_role`: `ansible-galaxy collection install -r requirements.yml`
- A Red Hat family host.
- Vault Enterprise 2.2 or newer over HTTPS.
- A Vault CA, as PEM text (`vault_tpm_ca_cert`) or a file on the controller (`vault_tpm_ca_cert_src`).
- For enroll: a Vault token (`VAULT_TOKEN` or `vault_tpm_token`), plus `vault_tpm_token_policies` naming policies that already exist.

This repository holds both roles under `roles/`. `ansible.cfg` sets `roles_path`.

## vault_tpm_enroll

Required inputs: `vault_tpm_api_addr` (or `VAULT_ADDR`), `vault_tpm_role_name`, `vault_tpm_token_policies`, and a CA. `vault_tpm_host_addr` is the address the host uses for `vault tpm enroll` and defaults to the API address.

The auth role is created or updated after enroll because Vault requires `tpm_ids` on the role. Each host appends its id and writes the other role fields back, so a field left unset keeps the value already stored. The role retries the write until its id is still on the role. It does not remove ids. `vault_tpm_role_config` passes extra `tpm_role` fields. `tpm_ids` in that dict are appended.

Run enroll for one host at a time. `examples/enroll.yml` sets `serial: 1` for that play.

## vault_tpm_proxy

Required inputs: `vault_tpm_role_name` and a CA. `vault_tpm_proxy_addr` defaults to `vault_tpm_api_addr`, then `VAULT_ADDR`. `vault_tpm_namespace`, when set, is written into the proxy `vault` block.

The proxy user is `vault-proxy`. It is a system account in group `tss` when the device is a hardware TPM or a socket outside `/dev`, so it can open `/dev/tpmrm0` or a `swtpm` socket owned by `tss`. The unit listens on `/run/vault-proxy/vault-proxy.sock` mode `0600`. Only `vault-proxy` can connect. Set `vault_tpm_socket_mode` to let other accounts use the socket. The unit creates `vault_tpm_socket_dir` on start. On Vault 2.2.0-rc1+ent the unit runs `vault agent` with that config, because `method "tpm"` is registered on the agent and not on `vault proxy`.

Config and the CA file are owned by root, group `vault-proxy`, mode `0640`. The certificate directory is owned by `vault-proxy`.

The same account, created by hand:

```bash
sudo useradd \
  --system \
  --create-home \
  --home-dir /var/lib/vault-proxy/vault-proxy \
  --shell /usr/sbin/nologin \
  --groups tss \
  vault-proxy

sudo install -d -o root -g vault-proxy -m 0750 \
  /etc/vault-proxy

sudo install -d -o vault-proxy -g vault-proxy -m 0750 \
  /var/lib/vault-proxy \
  /var/lib/vault-proxy/vault-proxy \
  /var/lib/vault-proxy/vault-proxy/tpm
```

## Example

`examples/group_vars/app_hosts.yml` holds the shared role name and policy names. `examples/host_vars/` holds each TPM.

```bash
ansible-playbook -i examples/inventory.yml examples/enroll.yml
```

## Demo

`demo/` builds a throwaway RHEL 9 instance and runs both roles. It is not for production. See [demo/README.md](demo/README.md).
