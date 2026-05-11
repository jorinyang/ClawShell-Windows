#!/bin/bash
# ═══════════════════════════════════════════════════════════
# ClawShell 2.0 — ECS UserData Bootstrap Script
# ═══════════════════════════════════════════════════════════
# Runs on first boot to install Docker + deploy ClawShell
# ═══════════════════════════════════════════════════════════

set -e

CLW_VERSION="${clawshell_version}"
CLW_SECRET="${clawshell_secret}"

echo "=== ClawShell Cloud Bootstrap v$CLW_VERSION ==="

# ── System Update ─────────────────────────────────────
apt-get update -qq
apt-get install -y -qq docker.io docker-compose nginx curl git python3-pip

# ── Docker Setup ──────────────────────────────────────
systemctl enable docker
systemctl start docker

# ── Clone & Deploy ────────────────────────────────────
cd /opt
git clone https://github.com/jorinyang/ClawShell-Windows.git clawshell 2>/dev/null || \
  (cd clawshell && git pull origin main)

cd /opt/clawshell

# Write env
cat > .env <<EOF
CLAWSHELL_SECRET=$CLW_SECRET
CLAWSHELL_ENV=production
EOF

# Start services
docker compose up -d

# ── Health Check ──────────────────────────────────────
sleep 10
curl -s http://localhost:8000/ && echo "ClawShell Cloud ready" || echo "Starting..."

echo "=== Bootstrap complete ==="
