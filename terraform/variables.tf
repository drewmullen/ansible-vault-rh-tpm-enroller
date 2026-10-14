variable "allowed_cidr" {
  description = "CIDR allowed to reach SSH and Vault. Empty uses the current public address of this machine."
  type        = string
  default     = ""
}

variable "aws_profile" {
  description = "AWS shared config profile. This stack stays in the doormat account."
  type        = string
  default     = "doormat"
}

variable "aws_region" {
  description = "Region for the test instance."
  type        = string
  default     = "us-east-1"
}

variable "hashi_base_ami" {
  description = "Use the shared HashiCorp hc-base RHEL image. False uses the current public RHEL 9 AMI."
  type        = bool
  default     = false
}

variable "instance_type" {
  description = "Nitro instance type. NitroTPM is not available on non-Nitro types."
  type        = string
  default     = "t3.medium"
}

variable "name" {
  description = "Name prefix for the test instance, AMI, and security group."
  type        = string
  default     = "vault-tpm-enroller"
}

variable "ssh_user" {
  description = "Login user on the RHEL image."
  type        = string
  default     = "ec2-user"
}
