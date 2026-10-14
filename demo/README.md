# Demo only

This lab is not for production. Terraform gives the instance a public IP. `setup-vault.sh` uses a self-signed certificate, one Shamir share, file storage, and writes the root token to disk.

## What Terraform builds

A RHEL 9 instance in the default VPC with NitroTPM. Public RHEL 9 images do not ship with TPM support, so Terraform snapshots the source image and registers an AMI with `tpm_support = v2.0`. SSH and port 8200 are open only to this machine's public IP, unless `allowed_cidr` is set.

`hashi_base_ami` defaults to `false` (current public RHEL 9 AMI, owner `309956199498`). Set it to `true` for the shared HashiCorp `hc-base` image.

Default AWS profile `doormat`, region `us-east-1`, instance type `t3.medium`.

## Run

```bash
cd demo/terraform
terraform init
terraform apply
```

HashiCorp base image:

```bash
terraform apply -var='hashi_base_ami=true'
```

`ssh_command` prints the SSH command. The private key is `vault-tpm-enroller.pem` in `demo/terraform`.

Copy a Vault Enterprise 2.2 license onto the instance, then install Vault. From `demo/terraform`:

```bash
IP="$(terraform output -raw public_ip)"
scp -i vault-tpm-enroller.pem vault.hclic "ec2-user@${IP}:/tmp/vault.hclic"
scp -i vault-tpm-enroller.pem setup-vault.sh "ec2-user@${IP}:/tmp/setup-vault.sh"
ssh -i vault-tpm-enroller.pem "ec2-user@${IP}" "sudo bash /tmp/setup-vault.sh ${IP}"
scp -i vault-tpm-enroller.pem "ec2-user@${IP}:/home/ec2-user/vault-init.json" ./vault-init.json
ssh -i vault-tpm-enroller.pem "ec2-user@${IP}" 'sudo cp /opt/vault/tls/vault.crt /tmp/vault.crt && sudo chmod 0644 /tmp/vault.crt'
scp -i vault-tpm-enroller.pem "ec2-user@${IP}:/tmp/vault.crt" ./vault.crt
```

`setup-vault.sh` installs Vault `2.2.0-rc1+ent`, writes the certificate, and initializes the server.

From the repository root, the playbook enables `auth/tpm`, writes the auth CA and the `app-read` policy, enrolls the TPM, and starts the proxy:

```bash
export VAULT_ADDR="https://${IP}:8200"
export VAULT_TOKEN="$(python3 -c 'import json; print(json.load(open("demo/terraform/vault-init.json"))["root_token"])')"
export ANSIBLE_HOST_KEY_CHECKING=False
ansible-playbook -i demo/inventory.yml demo/playbook.yml -e ansible_host="$IP"
```

The proxy on the host uses `https://127.0.0.1:8200`. `vault_tpm_verify_path` is `secret/tpm-test`.

Do not commit the private key, `vault-init.json`, the license, `vault.crt`, or Terraform state.
