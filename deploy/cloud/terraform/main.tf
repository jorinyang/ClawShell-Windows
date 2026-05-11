# ═══════════════════════════════════════════════════════════
# ClawShell 2.0 — Alibaba Cloud Terraform Configuration
# ═══════════════════════════════════════════════════════════
# Deploy ClawShell Cloud to Alibaba Cloud ECS in one command:
#   export ALICLOUD_ACCESS_KEY="..." ALICLOUD_SECRET_KEY="..."
#   terraform init && terraform apply
# ═══════════════════════════════════════════════════════════

terraform {
  required_version = ">= 1.0"
  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = "~> 1.230"
    }
  }
}

provider "alicloud" {
  region = var.region
}

# ═══ VPC Network ══════════════════════════════════════════

resource "alicloud_vpc" "clawshell" {
  vpc_name   = "clawshell-vpc"
  cidr_block = "10.0.0.0/16"
}

resource "alicloud_vswitch" "clawshell" {
  vswitch_name = "clawshell-vswitch"
  vpc_id       = alicloud_vpc.clawshell.id
  cidr_block   = "10.0.1.0/24"
  zone_id      = var.zone_id
}

# ═══ Security Group ═══════════════════════════════════════

resource "alicloud_security_group" "clawshell" {
  name        = "clawshell-sg"
  description = "ClawShell Cloud security group"
  vpc_id      = alicloud_vpc.clawshell.id
}

resource "alicloud_security_group_rule" "allow_ssh" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "22/22"
  security_group_id = alicloud_security_group.clawshell.id
  cidr_ip           = var.admin_cidr
}

resource "alicloud_security_group_rule" "allow_http" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "80/80"
  security_group_id = alicloud_security_group.clawshell.id
  cidr_ip           = "0.0.0.0/0"
}

resource "alicloud_security_group_rule" "allow_https" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "443/443"
  security_group_id = alicloud_security_group.clawshell.id
  cidr_ip           = "0.0.0.0/0"
}

resource "alicloud_security_group_rule" "allow_api" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "8000/8000"
  security_group_id = alicloud_security_group.clawshell.id
  cidr_ip           = "0.0.0.0/0"
}

resource "alicloud_security_group_rule" "allow_n8n" {
  type              = "ingress"
  ip_protocol       = "tcp"
  port_range        = "5678/5678"
  security_group_id = alicloud_security_group.clawshell.id
  cidr_ip           = var.admin_cidr
}

resource "alicloud_security_group_rule" "allow_egress" {
  type              = "egress"
  ip_protocol       = "all"
  port_range        = "-1/-1"
  security_group_id = alicloud_security_group.clawshell.id
  cidr_ip           = "0.0.0.0/0"
}

# ═══ ECS Instance ═════════════════════════════════════════

resource "alicloud_instance" "clawshell" {
  instance_name   = "clawshell-cloud"
  host_name       = "clawshell"
  instance_type   = var.instance_type
  image_id        = data.alicloud_images.ubuntu.images[0].id
  system_disk_category = "cloud_essd"
  system_disk_size     = var.disk_size

  vswitch_id  = alicloud_vswitch.clawshell.id
  security_groups = [alicloud_security_group.clawshell.id]

  internet_max_bandwidth_out = var.bandwidth
  internet_charge_type       = "PayByTraffic"

  password = var.ecs_password
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    clawshell_version = var.clawshell_version
    clawshell_secret  = var.clawshell_secret
  }))

  tags = {
    Project = "ClawShell"
    Version = var.clawshell_version
  }
}

# ═══ Ubuntu Image ═════════════════════════════════════════

data "alicloud_images" "ubuntu" {
  name_regex  = "^ubuntu_22.*_x64_20G_alibase"
  most_recent = true
  owners      = "system"
}

# ═══ OSS Bucket (Vault Storage) ═══════════════════════════

resource "alicloud_oss_bucket" "vault" {
  bucket = "clawshell-vault-${var.clawshell_version}"
  acl    = "private"

  versioning {
    status = "Enabled"
  }

  lifecycle {
    ignore_changes = [acl]
  }
}

# ═══ EIP (Public IP) ══════════════════════════════════════

resource "alicloud_eip" "clawshell" {
  bandwidth            = var.bandwidth
  internet_charge_type = "PayByTraffic"
}

resource "alicloud_eip_association" "clawshell" {
  allocation_id = alicloud_eip.clawshell.id
  instance_id   = alicloud_instance.clawshell.id
}
