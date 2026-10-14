output "ami_id" {
  description = "NitroTPM-enabled AMI registered from the source snapshot."
  value       = aws_ami.nitrotpm.id
}

output "instance_id" {
  description = "ID of the TPM test instance."
  value       = aws_instance.enroller.id
}

output "public_ip" {
  description = "Public address of the TPM test instance."
  value       = aws_instance.enroller.public_ip
}

output "ssh_command" {
  description = "SSH command for the test instance."
  value       = "ssh -i ${local_sensitive_file.ssh_key.filename} ${var.ssh_user}@${aws_instance.enroller.public_ip}"
}

output "source_ami_id" {
  description = "RHEL AMI snapshotted to enable NitroTPM."
  value       = local.source_ami_id
}
