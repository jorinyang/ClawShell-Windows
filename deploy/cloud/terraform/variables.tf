# ═══════════════════════════════════════════════════════════
# ClawShell 2.0 — Terraform Variables
# ═══════════════════════════════════════════════════════════

variable "region" {
  description = "Alibaba Cloud region"
  type        = string
  default     = "cn-hangzhou"
}

variable "zone_id" {
  description = "Availability zone"
  type        = string
  default     = "cn-hangzhou-h"
}

variable "instance_type" {
  description = "ECS instance type"
  type        = string
  default     = "ecs.c6.large"  # 2vCPU 4GB (~¥120/month)

  validation {
    condition     = can(regex("^ecs\\.", var.instance_type))
    error_message = "Must be a valid ECS instance type (ecs.*)."
  }
}

variable "disk_size" {
  description = "System disk size in GB"
  type        = number
  default     = 40
}

variable "bandwidth" {
  description = "Internet bandwidth in Mbps"
  type        = number
  default     = 5
}

variable "admin_cidr" {
  description = "Admin SSH access CIDR"
  type        = string
  default     = "0.0.0.0/0"
  sensitive   = false
}

variable "ecs_password" {
  description = "ECS root password"
  type        = string
  sensitive   = true
}

variable "clawshell_version" {
  description = "ClawShell version tag"
  type        = string
  default     = "2.0.0"
}

variable "clawshell_secret" {
  description = "ClawShell secret key for edge auth"
  type        = string
  sensitive   = true
  default     = "change-me-in-production"
}
