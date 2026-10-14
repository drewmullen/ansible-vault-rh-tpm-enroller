locals {
  allowed_cidr = var.allowed_cidr != "" ? var.allowed_cidr : "${chomp(data.http.my_ip.response_body)}/32"

  source_ami_id           = var.hashi_base_ami ? data.aws_ami.hc_base[0].id : data.aws_ami.rhel.id
  source_ami_name         = var.hashi_base_ami ? data.aws_ami.hc_base[0].name : data.aws_ami.rhel.name
  source_root_device_name = var.hashi_base_ami ? data.aws_ami.hc_base[0].root_device_name : data.aws_ami.rhel.root_device_name

  tags = {
    Name      = var.name
    ManagedBy = "Terraform"
    Purpose   = "vault-tpm-enroller-test"
  }
}
