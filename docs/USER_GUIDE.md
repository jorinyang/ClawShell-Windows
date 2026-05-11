# ClawShell 2.0 — User Guide

## Quick Start

### Edge Installation (1 minute)

```bash
# Linux / macOS / WSL
curl -fsSL https://raw.githubusercontent.com/jorinyang/ClawShell-Windows/main/scripts/install.sh | bash

# Windows PowerShell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/jorinyang/ClawShell-Windows/main/scripts/install.ps1" | Invoke-Expression
```

The installer will:
1. Detect your environment (OS, OpenClaw, Hermes, Wukong)
2. Install core dependencies (websockets, psutil)
3. Launch ecosystem selector (choose MemPalace, N8N, Obsidian+OSS, etc.)
4. Run configuration wizard (Cloud URL, Token, Node ID)

### Start Edge Client

```bash
clawshell-edge start     # Start with cloud sync
clawshell-edge status    # Check connection
clawshell-edge stop      # Stop client
```

### Ecosystem Components

| Component | Install | Purpose |
|-----------|---------|---------|
| MemPalace | `pip install chromadb` | Local memory with vector search |
| ChromaDB | Included | Vector database |
| N8N | `npx n8n` | Workflow automation |
| MemOS Cloud | API Key | Cloud memory sync |
| Watchdog | `pip install watchdog` | File system monitoring |
| Browser Runtime | `npx playwright install chromium` | CDP browser control |
| ONNX Runtime | `pip install onnxruntime` | ML inference acceleration |
| Obsidian + OSS | `ossutil` + AK/SK | Cloud vault sync |

### Environment Adapters

```bash
# Auto-integrate with OpenClaw/Wukong
python3 scripts/openclaw_adapter.py

# Auto-integrate with Hermes Agent
python3 scripts/hermes_adapter.py
```

## Cloud Deployment (Alibaba Cloud ECS)

```bash
# 1. Set credentials
export ALICLOUD_ACCESS_KEY="LTAI5t..."
export ALICLOUD_SECRET_KEY="..."

# 2. Deploy
cd deploy/cloud/terraform
terraform init
terraform apply -var="ecs_password=YourPassword123!"

# 3. Get connection info
terraform output
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Service status |
| POST | `/api/v1/events/batch` | Push events |
| GET | `/api/v1/events/query` | Query events |
| POST | `/api/v1/tasks/` | Create task |
| GET | `/api/v1/tasks/` | List tasks |
| PUT | `/api/v1/tasks/{id}` | Update task |
| GET | `/api/v1/skills/` | List skills |
| POST | `/api/v1/skills/` | Register skill |
| POST | `/api/v1/memory/sync` | Sync memories |
| POST | `/api/v1/health/report` | Health report |
| GET | `/api/v1/health/nodes` | List edge nodes |
| GET | `/vault/status` | Vault statistics |
| GET | `/vault/search?q=` | Search vault |
| POST | `/vault/sync/push` | Push vault to OSS |
| WS | `/ws/events` | Real-time events |

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Cloud connection failed | Check Cloud URL and token in `~/.clawshell_edge/config.yaml` |
| ossutil not found | Run `ecosystem_installer.py --install obsidian_oss` |
| MemPalace import error | `pip install chromadb` |
| N8N not starting | `npx n8n start` (first run downloads ~200MB) |
