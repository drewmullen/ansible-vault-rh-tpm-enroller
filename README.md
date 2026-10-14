# vault_tpm_enroll and vault_tpm_proxy

Two roles for Vault Enterprise TPM auth on Red Hat hosts.

`vault_tpm_enroll` enrolls the host TPM and appends that TPM id to an auth role. `vault_tpm_proxy` installs Vault Proxy with TPM auto-auth and enables it under systemd.

Neither role enables `auth/tpm`, writes `auth/<mount>/config`, or writes an ACL policy. Do that before enroll. The [demo](demo/README.md) playbook does it for a lab Vault.

## Example Execution

1 run installs 2 roles
- tpm enroll
- tpm proxy setup

```bash
ansible-playbook -i examples/inventory.yml examples/enroll.yml
```

## Requirements

- Ansible 2.16 or newer, with facts gathered.
- The `hashicorp.vault` fork that ships `auth_method`, `tpm_auth_config`, `identity_tpm`, and `tpm_role`: `ansible-galaxy collection install -r requirements.yml`
- A Red Hat family host.
- Vault Enterprise 2.2 or newer over HTTPS.
- A Vault CA, as PEM text (`vault_tpm_ca_cert`) or a file on the controller (`vault_tpm_ca_cert_src`).
- For enroll: an admin token (`VAULT_TOKEN` or `vault_tpm_token`) or AppRole, plus `vault_tpm_token_policies` naming policies that already exist.

This repository holds both roles under `roles/`. `ansible.cfg` sets `roles_path`.

## vault_tpm_enroll

Required inputs: `vault_tpm_api_addr` (or `VAULT_ADDR`), `vault_tpm_role_name`, `vault_tpm_token_policies`, and a CA. `vault_tpm_host_addr` is the address the host uses for `vault tpm enroll` and defaults to the API address.

The auth role is created or updated after enroll because Vault requires `tpm_ids` on the role. A second host appends its id. The role does not remove ids.

## vault_tpm_proxy

Required inputs: `vault_tpm_proxy_addr`, `vault_tpm_role_name`, and a CA. The proxy user is `vault-proxy`. It is a system account in group `tss`, so it can open `/dev/tpmrm0`. The unit listens on `/run/vault-proxy/vault-proxy.sock` mode `0600`.

The same account, created by hand:

```bash
sudo useradd \
  --system \
  --create-home \
  --home-dir /var/lib/vault-proxy/vault-proxy \
  --shell /usr/sbin/nologin \
  --groups tss \
  vault-proxy

sudo install -d -o vault-proxy -g vault-proxy -m 0750 \
  /etc/vault-proxy \
  /var/lib/vault-proxy \
  /var/lib/vault-proxy/vault-proxy \
  /var/lib/vault-proxy/vault-proxy/tpm
```

`/run/vault-proxy` is created by the unit when the service starts.

## Example

`examples/group_vars/app_hosts.yml` holds the shared role name and policy names. `examples/host_vars/` holds each TPM.

```bash
ansible-playbook -i examples/inventory.yml examples/enroll.yml
```

## Demo

`demo/` builds a throwaway RHEL 9 instance and runs both roles. It is not for production. See [demo/README.md](demo/README.md).
