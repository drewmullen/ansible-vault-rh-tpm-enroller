# vault_tpm_enroller

Ansible role that enrolls a host TPM with Vault Enterprise TPM auth, writes the auth role and its policy, and runs Vault Proxy with TPM auto-auth under systemd.

One play targets many hosts. Hosts that should receive the same token share one auth role and one policy set. Each host enrolls its own TPM. The role does not create a demo policy, a demo secret, or a KV mount.

The behavior and the reason for each variable are in [ansible-vault-tpm-modules.md](ansible-vault-tpm-modules.md). Modules that `hashicorp.vault` does not ship yet are listed in [module-gaps.md](module-gaps.md). This role calls Vault's HTTP API with `ansible.builtin.uri` for the auth mount and the auth role, `hashicorp.vault.acl_policy` for policy HCL, and `vault tpm enroll` on the managed node.

## Requirements

- Ansible 2.16 or newer, with facts gathered (`gather_facts: true`).
- The `hashicorp.vault` collection, 1.2.0 or newer:

  ```bash
  ansible-galaxy collection install -r requirements.yml
  ```

- A managed node in the Red Hat family (`ansible_os_family=RedHat`).
- Vault Enterprise 2.2 or newer, reached over HTTPS.
- A Vault CA certificate, as PEM text or as a file on the controller.
- An admin token, or an AppRole role id and secret id. The proxy's TPM token is a different credential.
- `tpm2-tss` and `tpm2-tools` on the host, unless `vault_tpm_packages` is `[]`. The `vault` binary must already be installed unless `vault_tpm_version` is set.
- Privilege escalation so the role can install packages, write systemd units, and enroll as `vault_tpm_proxy_user`.

`vault_tpm_install_swtpm` defaults to false. Set it only on a lab host that should run `swtpm` instead of a hardware TPM, and point `vault_tpm_device_path` at the simulator socket. The `swtpm` package must be available to the host package manager.

## Role layout

This repository is the role. Content lives at the repository root (`tasks/`, `defaults/`, `vars/`, `meta/`), not under `roles/<name>/`. After Galaxy install the role name is `vault_tpm_enroller`.

`defaults/main.yml` holds overridable defaults. `vars/main.yml` holds three computed values callers do not set: the normalized auth path, the proxy socket path, and the combined `token_policies` list.

## Variable contract

`vault_tpm_role_name` has no default. The other required inputs have empty defaults so they can come from the environment or from group vars, and the role fails in `tasks/validate.yml` before it changes anything when one of them is still empty. The failure message names the missing variables.

| Variable | Required | Default |
| --- | --- | --- |
| `vault_tpm_api_addr` | yes | `VAULT_ADDR`, then empty. Must start with `https://`. |
| `vault_tpm_token` | one of token or AppRole | `VAULT_TOKEN`, then empty |
| `vault_tpm_role_id` | with `vault_tpm_secret_id`, when no token | empty |
| `vault_tpm_secret_id` | with `vault_tpm_role_id`, when no token | empty |
| `vault_tpm_role_name` | yes | none |
| `vault_tpm_policy_hcl` | one policy source | `""` |
| `vault_tpm_token_policies` | one policy source | `[]` |
| `vault_tpm_ca_cert` | one CA source | `""` |
| `vault_tpm_ca_cert_src` | one CA source | `""` |

Policy source means non-empty `vault_tpm_policy_hcl`, a non-empty `vault_tpm_token_policies` list, or both. CA source means PEM text or a controller file path.

| Variable | Default |
| --- | --- |
| `vault_tpm_policy_name` | `vault_tpm_role_name` |
| `vault_tpm_auth_path` | `tpm` |
| `vault_tpm_auth_description` | `TPM auth` |
| `vault_tpm_namespace` | `""` |
| `vault_tpm_token_ttl` | `1h` |
| `vault_tpm_token_max_ttl` | `""` |
| `vault_tpm_token_period` | `""` |
| `vault_tpm_token_type` | `""` |
| `vault_tpm_token_no_default_policy` | `false` |
| `vault_tpm_token_bound_cidrs` | `[]` |
| `vault_tpm_role_config` | `{}` |
| `vault_tpm_enroll_name` | `inventory_hostname` |
| `vault_tpm_device_path` | `/dev/tpmrm0` |
| `vault_tpm_enroll_metadata` | `{}` |
| `vault_tpm_proxy_addr` | `vault_tpm_api_addr` |
| `vault_tpm_proxy_user` | `vault-proxy` |
| `vault_tpm_proxy_config_path` | `/etc/vault-proxy/tpm.hcl` |
| `vault_tpm_ca_cert_dest` | `/etc/vault-proxy/ca.pem` |
| `vault_tpm_cert_dir` | `/var/lib/vault-proxy/<user>/tpm` |
| `vault_tpm_cert_name` | `host_identity` |
| `vault_tpm_csr_cn` | `vault_tpm_enroll_name` |
| `vault_tpm_renew_percent` | `20` |
| `vault_tpm_renew_min_backoff` | `5s` |
| `vault_tpm_renew_max_backoff` | `5m` |
| `vault_tpm_use_auto_auth_token` | `force` |
| `vault_tpm_socket_dir` | `/run/vault-proxy` |
| `vault_tpm_socket_mode` | `"600"` |
| `vault_tpm_proxy_config` | `""` |
| `vault_tpm_service_name` | `vault-proxy` |
| `vault_tpm_service_enabled` | `true` |
| `vault_tpm_service_state` | `started` |
| `vault_tpm_packages` | `tpm2-tss`, `tpm2-tools` |
| `vault_tpm_install_swtpm` | `false` |
| `vault_tpm_version` | `""` |
| `vault_tpm_bin_path` | `/usr/local/bin/vault` |
| `vault_tpm_verify_path` | `""` |

Set the auth role and policy in group vars. Override `vault_tpm_enroll_name` and `vault_tpm_device_path` in host vars. Argument types are in `meta/argument_specs.yml`.

Vault API tasks run on the controller (`delegate_to: localhost`, `become: false`) against `vault_tpm_api_addr`. Enroll and the proxy config on the managed node use `vault_tpm_proxy_addr`.

A second run with the same inputs does not enable an existing auth mount, does not rewrite an unchanged policy or auth role, and treats an already enrolled TPM as success with `changed=false`.

## Example

`examples/group_vars/app_hosts.yml` holds the shared role and policy. `examples/host_vars/` holds each host's enroll name and device path.

```yaml
# examples/group_vars/app_hosts.yml
vault_tpm_api_addr: https://vault.example.com:8200
vault_tpm_role_name: app-hosts
vault_tpm_policy_name: app-read
vault_tpm_policy_hcl: |
  path "secret/data/app/*" {
    capabilities = ["read"]
  }
vault_tpm_token_policies:
  - audit-read
vault_tpm_ca_cert_src: files/vault-ca.pem
```

```yaml
# examples/host_vars/host-a.example.yml
vault_tpm_enroll_name: host-a-tpm
vault_tpm_device_path: /dev/tpmrm0
```

```yaml
# examples/enroll.yml
- name: Enroll application hosts with Vault TPM auth
  hosts: app_hosts
  gather_facts: true
  become: true
  roles:
    - role: vault_tpm_enroller
```

```bash
ansible-playbook -i examples/inventory.yml examples/enroll.yml
```

Provide `VAULT_TOKEN`, or set `vault_tpm_role_id` and `vault_tpm_secret_id`. The admin token is not written to a token file.

Syntax-check the example from a checkout of this repository:

```bash
ansible-galaxy collection install -r requirements.yml
mkdir -p /tmp/vault-tpm-enroller-roles
ln -sfn "$PWD" /tmp/vault-tpm-enroller-roles/vault_tpm_enroller
ANSIBLE_ROLES_PATH=/tmp/vault-tpm-enroller-roles \
  ansible-playbook --syntax-check -i examples/inventory.yml examples/enroll.yml
```

## Demo

`terraform/` builds a RHEL 9 instance with NitroTPM. SSH and port 8200 are limited to this machine's public IP. The default image is the current public RHEL 9 AMI. Set `hashi_base_ami` to `true` to use the shared HashiCorp `hc-base` image.

```bash
cd terraform
terraform init
terraform apply
```

```bash
terraform apply -var='hashi_base_ami=true'
```

Copy a Vault Enterprise 2.2 license to the instance as `/tmp/vault.hclic`, then run `setup-vault.sh` with the public IP. The script installs Vault, writes a self-signed certificate, and initializes the server. Pass that certificate to the role as `vault_tpm_ca_cert_src`, and set `vault_tpm_proxy_addr` to `https://127.0.0.1:8200`. The Lab run section is the playbook command used against one of these instances.

## Lab run

This is the playbook invocation used against the NitroTPM test instance. The inventory host is `enroller` at `44.222.79.147`, user `ec2-user`, key `terraform/vault-tpm-enroller.pem`. `VAULT_TOKEN` is the admin token from `terraform/vault-init.json`. `ANSIBLE_ROLES_PATH` points at a symlink to this repository, and `ANSIBLE_COLLECTIONS_PATH` is a git checkout of `hashicorp.vault`.

The trailing `-e @...` is what the run used. It sets the same values as the flags above it, plus this policy:

```hcl
path "secret/data/tpm-test" {
  capabilities = ["read"]
}
```

```bash
export VAULT_TOKEN="hvs..."
export ANSIBLE_ROLES_PATH=/tmp/vault-tpm-enroller-run/roles
export ANSIBLE_COLLECTIONS_PATH=/tmp/vault-tpm-enroller-run/collections
export ANSIBLE_HOST_KEY_CHECKING=False

ansible-playbook \
  -i /tmp/vault-tpm-enroller-run/play/inventory.yml \
  /tmp/vault-tpm-enroller-run/play/enroll.yml \
  -e vault_tpm_api_addr=https://44.222.79.147:8200 \
  -e vault_tpm_proxy_addr=https://127.0.0.1:8200 \
  -e vault_tpm_role_name=app-hosts \
  -e vault_tpm_policy_name=app-read \
  -e vault_tpm_ca_cert_src=/Users/drew.mullen/git/ansible-vault-rh-tpm-enroller/terraform/vault.crt \
  -e vault_tpm_verify_path=secret/tpm-test \
  -e vault_tpm_enroll_name=vault-tpm-enroller \
  -e @/tmp/vault-tpm-enroller-run/play/group_vars.yml
```

## Proxy user

The role creates `vault-proxy` and gives it these permissions. The equivalent commands:

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

sudo touch /etc/vault-proxy/tpm.hcl /etc/vault-proxy/ca.pem
sudo chown vault-proxy:vault-proxy /etc/vault-proxy/tpm.hcl /etc/vault-proxy/ca.pem
sudo chmod 0640 /etc/vault-proxy/tpm.hcl
sudo chmod 0644 /etc/vault-proxy/ca.pem
```

`tss` comes from the `tpm2-tss` package and is what lets this user open `/dev/tpmrm0` (`crw-rw---- root:tss`). `useradd` also creates the primary group `vault-proxy`.

`/run/vault-proxy` is not created here. The unit's `RuntimeDirectory=vault-proxy` creates it at mode `0750` when the service starts, and the proxy then creates `vault-proxy.sock` at mode `0600`.
