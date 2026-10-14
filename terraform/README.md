# Demo only

This stack is a lab for trying the `vault_tpm_enroller` role. It is not for production. It uses a public IP, a self-signed certificate, a single Shamir share, file storage, and a root token written to disk.

## What it builds

A RHEL 9 instance in the default VPC with NitroTPM. Public RHEL 9 images do not ship with TPM support, so Terraform launches the source image, snapshots the root volume, and registers an AMI with `tpm_support = v2.0`. SSH and port 8200 are open only to this machine's public IP, unless `allowed_cidr` is set.

`hashi_base_ami` defaults to `false`, which selects the current public RHEL 9 AMI (owner `309956199498`). Set it to `true` to start from the shared HashiCorp `hc-base` image instead.

The default AWS profile is `doormat`, region `us-east-1`, instance type `t3.medium`.

## Run

```bash
terraform init
terraform apply
```

HashiCorp base image:

```bash
terraform apply -var='hashi_base_ami=true'
```

`ssh_command` prints the SSH command. The private key is `vault-tpm-enroller.pem` in this directory.

Copy a Vault Enterprise 2.2 license onto the instance, then install Vault:

```bash
scp -i vault-tpm-enroller.pem vault.hclic ec2-user@<public-ip>:/tmp/vault.hclic
scp -i vault-tpm-enroller.pem setup-vault.sh ec2-user@<public-ip>:/tmp/setup-vault.sh
ssh -i vault-tpm-enroller.pem ec2-user@<public-ip> 'sudo bash /tmp/setup-vault.sh <public-ip>'
```

`setup-vault.sh` installs Vault `2.2.0-rc1+ent`, writes a self-signed certificate, initializes and unseals the server, and stores the init JSON at `/root/vault-init.json`. Copy `vault.crt` and the init JSON back to this directory. Pass the certificate to the role as `vault_tpm_ca_cert_src`, and set `vault_tpm_proxy_addr` to `https://127.0.0.1:8200`.

Do not commit the private key, `vault-init.json`, the license, `vault.crt`, or Terraform state.
