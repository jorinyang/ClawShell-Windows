# ═══════════════════════════════════════════════════════════
# ClawShell 2.0 — Terraform Outputs
# ═══════════════════════════════════════════════════════════

output "ecs_public_ip" {
  description = "ECS public IP address"
  value       = alicloud_eip.clawshell.ip_address
}

output "ecs_instance_id" {
  description = "ECS instance ID"
  value       = alicloud_instance.clawshell.id
}

output "oss_bucket_name" {
  description = "OSS bucket for Obsidian vault"
  value       = alicloud_oss_bucket.vault.bucket
}

output "oss_bucket_endpoint" {
  description = "OSS bucket endpoint"
  value       = "oss-${var.region}.aliyuncs.com"
}

output "cloud_api_url" {
  description = "ClawShell Cloud API URL"
  value       = "http://${alicloud_eip.clawshell.ip_address}:8000"
}

output "n8n_url" {
  description = "N8N workflow engine URL"
  value       = "http://${alicloud_eip.clawshell.ip_address}:5678"
}

output "ssh_command" {
  description = "SSH connection command"
  value       = "ssh root@${alicloud_eip.clawshell.ip_address}"
}

output "next_steps" {
  description = "Post-deployment steps"
  value = [
    "1. SSH into instance: ${"ssh root@${alicloud_eip.clawshell.ip_address}"}",
    "2. Check services: docker compose ps",
    "3. Test API: curl http://${alicloud_eip.clawshell.ip_address}:8000/",
    "4. Configure edge client with Cloud URL",
  ]
}
