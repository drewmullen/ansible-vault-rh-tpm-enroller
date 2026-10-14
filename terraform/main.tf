data "aws_ami" "rhel" {
  most_recent = true
  owners      = ["309956199498"]

  filter {
    name   = "name"
    values = ["RHEL-9.*_HVM-*-x86_64-*-Hourly2-GP3"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

data "aws_ami" "hc_base" {
  count       = var.hashi_base_ami ? 1 : 0
  most_recent = true
  owners      = ["888995627335"]

  filter {
    name   = "name"
    values = ["hc-base-rhel-9-x86_64-20261012071828-v1.5"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }

  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

data "http" "my_ip" {
  url = "https://checkip.amazonaws.com"
}

resource "tls_private_key" "ssh" {
  algorithm = "ED25519"
}

resource "aws_key_pair" "ssh" {
  key_name   = var.name
  public_key = tls_private_key.ssh.public_key_openssh

  tags = local.tags
}

resource "local_sensitive_file" "ssh_key" {
  filename        = "${path.module}/${var.name}.pem"
  content         = tls_private_key.ssh.private_key_openssh
  file_permission = "0600"
}

resource "aws_security_group" "builder" {
  name        = "${var.name}-builder"
  description = "No inbound. Used only to snapshot the shared AMI."
  vpc_id      = data.aws_vpc.default.id

  egress {
    description = "Package metadata during first boot"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.tags, {
    Name = "${var.name}-builder"
  })
}

resource "aws_security_group" "enroller" {
  name        = var.name
  description = "SSH and Vault from the operator address only."
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [local.allowed_cidr]
  }

  ingress {
    description = "Vault API"
    from_port   = 8200
    to_port     = 8200
    protocol    = "tcp"
    cidr_blocks = [local.allowed_cidr]
  }

  egress {
    description = "Vault release download and package installs"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.tags
}

# Public RHEL 9 images and the shared hc-base image have no TpmSupport.
# Launch the source image, snapshot the root volume, and register that snapshot
# with NitroTPM.
resource "aws_instance" "builder" {
  ami                         = local.source_ami_id
  instance_type               = var.instance_type
  subnet_id                   = sort(data.aws_subnets.default.ids)[0]
  vpc_security_group_ids      = [aws_security_group.builder.id]
  associate_public_ip_address = false

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  tags = merge(local.tags, {
    Name = "${var.name}-builder"
  })
}

resource "terraform_data" "builder_ready" {
  input = aws_instance.builder.id

  provisioner "local-exec" {
    command = "aws ec2 wait instance-status-ok --profile ${var.aws_profile} --region ${var.aws_region} --instance-ids ${aws_instance.builder.id}"
  }
}

resource "aws_ebs_snapshot" "root" {
  volume_id   = aws_instance.builder.root_block_device[0].volume_id
  description = "Root volume of ${local.source_ami_name} for NitroTPM registration."

  tags = merge(local.tags, {
    Name = "${var.name}-root"
  })

  timeouts {
    create = "40m"
  }

  depends_on = [terraform_data.builder_ready]
}

resource "aws_ami" "nitrotpm" {
  name                = "${var.name}-${formatdate("YYYYMMDDhhmmss", timestamp())}"
  description         = "RHEL 9 with NitroTPM v2.0 enabled."
  architecture        = "x86_64"
  boot_mode           = "uefi"
  ena_support         = true
  imds_support        = "v2.0"
  root_device_name    = local.source_root_device_name
  tpm_support         = "v2.0"
  virtualization_type = "hvm"

  ebs_block_device {
    device_name           = local.source_root_device_name
    snapshot_id           = aws_ebs_snapshot.root.id
    volume_size           = 20
    volume_type           = "gp3"
    delete_on_termination = true
  }

  tags = local.tags

  lifecycle {
    ignore_changes = [name]
  }
}

resource "aws_instance" "enroller" {
  ami                         = aws_ami.nitrotpm.id
  instance_type               = var.instance_type
  subnet_id                   = sort(data.aws_subnets.default.ids)[0]
  vpc_security_group_ids      = [aws_security_group.enroller.id]
  key_name                    = aws_key_pair.ssh.key_name
  associate_public_ip_address = true

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  tags = local.tags

  depends_on = [local_sensitive_file.ssh_key]
}

resource "aws_ec2_instance_state" "builder" {
  instance_id = aws_instance.builder.id
  state       = "stopped"

  depends_on = [aws_instance.enroller]
}
