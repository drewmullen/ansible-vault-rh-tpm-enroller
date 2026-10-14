# Demo only

Instance build for the lab in [../README.md](../README.md). Not for production.

`hashi_base_ami` defaults to `false` (public RHEL 9). Set it to `true` for the shared HashiCorp `hc-base` image. SSH and port 8200 are limited to this machine's public IP.

```bash
terraform init
terraform apply
```

```bash
terraform apply -var='hashi_base_ami=true'
```

After apply, install Vault and run `demo/playbook.yml` as described in the parent README. Do not commit the private key, `vault-init.json`, the license, `vault.crt`, or Terraform state.
