# ClawShell 2.0 — System Architecture
## Cloud-Edge Collaborative AI Agent Platform

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   ClawShell Cloud (阿里云 ECS)            │
│                                                         │
│  FastAPI Server (:8000)                                 │
│  ├── EventBus Engine (persist/query/dedup/expire)      │
│  ├── TaskMarket Engine (CRUD/state machine/matching)   │
│  ├── Swarm Coordinator (nodes/heartbeat/load balance)  │
│  ├── Cron Scheduler (8 tasks)                          │
│  ├── N8N Bridge (workflow automation)                  │
│  ├── Vault API (Obsidian + OSS sync)                   │
│  └── WebSocket (:8000/ws/events)                        │
│                                                         │
│  OSS Bucket: Obsidian vault storage                     │
│  N8N: Workflow engine (:5678)                          │
│  Nginx: Reverse proxy (:80/:443)                       │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTPS + WSS
         ┌────────────┼────────────┐
         │            │            │
┌────────▼───┐ ┌─────▼──────┐ ┌───▼──────────┐
│ Edge A     │ │ Edge B     │ │ Edge C       │
│ (WSL)      │ │ (macOS)    │ │ (Linux)      │
│            │ │            │ │              │
│ MCP Bridge │ │ MCP Bridge │ │ MCP Bridge   │
│ EventBus   │ │ EventBus   │ │ EventBus     │
│ Health Mon │ │ Health Mon │ │ Health Mon   │
│ Obsidian   │ │ Hermes     │ │ Wukong       │
│ Hermes     │ │            │ │              │
└────────────┘ └────────────┘ └──────────────┘
```

## Cloud Side

| Component | Port | Description |
|-----------|------|-------------|
| FastAPI Server | 8000 | REST API + WebSocket |
| EventBus Engine | — | Event persistence/query |
| TaskMarket | — | Task lifecycle management |
| Swarm Coordinator | — | Multi-node management |
| Cron Scheduler | — | Scheduled task execution |
| N8N Bridge | — | Workflow automation |
| Vault API | — | Obsidian + OSS sync |
| Nginx | 80/443 | Reverse proxy |

## Edge Side

| Component | Port | Description |
|-----------|------|-------------|
| MCP Bridge | 17655 | JSON-RPC EventBus bridge |
| Environment Detector | — | Auto-detect OS/OpenClaw/Hermes/Wukong |
| Ecosystem Installer | — | 10 components installable |
| Obsidian Adapter | — | Vault sync + knowledge graph |
| OpenClaw Adapter | — | Wukong runtime integration |
| Hermes Adapter | — | Hermes Agent integration |

## Data Flow

```
User → Hermes/Wukong → MCP Bridge → EventBus → Cloud API
                                              → TaskMarket
                                              → Swarm
                                              → N8N workflows
                                              → OSS Vault
Cloud → WSS push → Edge nodes (real-time)
Edge → Health Report → Cloud (every 5 min)
Obsidian → ossutil sync → OSS Bucket → Vault API
```

## Memory Architecture

```
🏠 Local (Edge)           ☁️ Cloud
─────────────────────────────────
MemPalace (SQLite+ChromaDB)
MemOS Local (Node/Bun)
                          MemOS Cloud (API sync)
Obsidian Vault             OSS Bucket (storage)
```

## Deployment

```
# Cloud (one command)
cd deploy/cloud/terraform
terraform init && terraform apply

# Edge (one command)
curl -fsSL https://raw.githubusercontent.com/jorinyang/ClawShell-Windows/main/scripts/install.sh | bash
```
