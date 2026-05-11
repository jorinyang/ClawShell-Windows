# ClawShell 2.0

> **版本**: 1.1.0 (Cloud-Edge 分离架构)
> **定位**: 类OpenClaw架构的增强型外骨骼插件系统
> **架构**: 云边协同 — 1 云枢（主脑）+ N 端脑（副脑），章鱼式分布式神经系统

ClawShell 是一个基于工程控制论思想的多智能体操作系统增强层。1.0 以四层架构（自感知 × 自适应 × 自组织 × 多Agent集群）为类OpenClaw架构（悟空/Hermes/OpenClaw）提供外骨骼增强。2.0 引入云边协同架构，实现一端成长、多端共进。

---

## 2.0 云边架构全景

```
                        ┌─────────────────────────────────────────┐
                        │        ClawShell Cloud Hub (云枢)        │
                        │       阿里云 ECS + OSS + GitHub          │
                        │                                         │
                        │  ┌──────────────────────────────────┐  │
                        │  │ FastAPI Server (:8000)           │  │
                        │  │ ├─ EventBus Engine               │  │
                        │  │ ├─ TaskMarket Engine             │  │
                        │  │ ├─ Swarm Coordinator             │  │
                        │  │ ├─ Cron Scheduler                │  │
                        │  │ ├─ Capability Registry           │  │
                        │  │ ├─ Skill Market                  │  │
                        │  │ ├─ N8N Bridge                    │  │
                        │  │ └─ Vault API (Obsidian+OSS)      │  │
                        │  └──────────────────────────────────┘  │
                        │                                         │
                        │  职责: 架构规划 / 深度思考 / 洞察分析    │
                        │        复盘总结 / 整理优化 / 成果广播    │
                        │        终端管理 / 版本统一控制          │
                        └──────────────┬──────────────────────────┘
                                       │ HTTPS + WSS
                   ┌───────────────────┼───────────────────┐
                   │                   │                   │
        ┌──────────▼──────┐  ┌────────▼──────┐  ┌────────▼──────┐
        │   Edge A (WSL)  │  │ Edge B (macOS) │  │ Edge C (Linux)│
        │                 │  │               │  │               │
        │  ┌───────────┐  │  │ ┌───────────┐ │  │ ┌───────────┐ │
        │  │EdgeGateway│  │  │ │EdgeGateway│ │  │ │EdgeGateway│ │
        │  │├ SyncEngine│  │  │ │├ SyncEngine│ │  │ │├ SyncEngine│ │
        │  │├ Adapters  │  │  │ │├ Adapters  │ │  │ │├ Adapters  │ │
        │  └───────────┘  │  │ └───────────┘ │  │ └───────────┘ │
        │                 │  │               │  │               │
        │  Wukong/Hermes  │  │  OpenClaw     │  │  Hermes       │
        │  MCP Bridge     │  │  MCP Bridge   │  │  MCP Bridge   │
        │  Self-Repair    │  │  Self-Repair  │  │  Self-Repair  │
        └─────────────────┘  └───────────────┘  └───────────────┘
```

**云枢职责**: 架构规划、深度思考、洞察分析、复盘总结、整理优化、成果广播、终端管理
**端脑职责**: 自适应安装、注册云枢、嗅探加载插件、协同Agent调度、离线自治、自感知+自适应

---

## 核心能力

### 1.0 四层外骨骼（保留并增强）

```
┌─────────────────────────────────────────────────────┐
│  Layer 4: 多Agent集群                               │
│  ├─ SwarmDiscovery  集群发现                       │
│  ├─ TrustManager    信任评估                       │
│  ├─ EcologyMatcher  生态位匹配                     │
│  └─ SwarmProtocol   协作协议                       │
├─────────────────────────────────────────────────────┤
│  Layer 3: 自组织                                    │
│  ├─ Organizer       任务编排                       │
│  ├─ TaskMarket      任务市场                       │
│  ├─ DAGManager      依赖管理                       │
│  └─ N8NClient       工作流集成                      │
├─────────────────────────────────────────────────────┤
│  Layer 2: 自适应                                    │
│  ├─ SelfHealing     自修复系统                     │
│  ├─ Discovery       能力发现                       │
│  ├─ ConditionEngine 条件引擎                       │
│  └─ StrategyEval    策略评估                       │
├─────────────────────────────────────────────────────┤
│  Layer 1: 自感知                                    │
│  ├─ HealthMonitor   健康检测                       │
│  ├─ SystemMonitor   系统监控                       │
│  ├─ DiskMonitor     磁盘监控                       │
│  └─ ProcessMonitor  进程监控                       │
└─────────────────────────────────────────────────────┘
```

### 2.0 云边协同（新增）

| 能力 | 云端 | 端侧 |
|------|------|------|
| **事件同步** | CloudEventBus (持久化/去重/查询) | LocalEventBus → batch push |
| **任务调度** | CloudTaskMarket (状态机/优先级/匹配) | pull_tasks → claim → complete |
| **集群管理** | SwarmCoordinator (心跳/负载均衡) | HealthReporter (5s上报) |
| **技能共享** | SkillMarket (发布/发现/同步) | search_skills → install |
| **知识同步** | Vault API (OSS+Obsidian) | ossutil sync 双向 |
| **记忆同步** | MemOS Cloud API | edge_sync_daemon |
| **离线容灾** | — | OfflineQueue (500条/降级) |

---

## 设计原则

### 1.0 原则
| 原则 | 说明 |
|------|------|
| **异构同效** | 不同架构模块在同一机制下发挥同等效能 |
| **异步优先** | 长任务异步执行，避免阻塞主流程 |
| **低耦合** | 模块间通过 EventBus 和文件协议通信 |
| **高鲁棒** | 多层级错误恢复、守护进程保活、自动降级 |
| **高泛用** | 感知层抽象、适配器模式、标准化接口 |
| **高协同** | EventBus + ContextManager + TaskMarket + Swarm |
| **高扩展** | 新模块可感知、可适应、可协作 |

### 2.0 新增原则
| 原则 | 说明 |
|------|------|
| **可移植** | 同一安装脚本适配 WSL/macOS/Linux |
| **幂等性** | 重复安装不对已有配置产生副作用 |
| **版本解耦** | ClawShell 升级不影响已部署框架 |

---

## 安装

### 端脑安装（一键）

```bash
# Linux/WSL/macOS
curl -fsSL https://raw.githubusercontent.com/jorinyang/ClawShell-Windows/main/scripts/install.sh | bash

# Windows PowerShell
irm https://raw.githubusercontent.com/jorinyang/ClawShell-Windows/main/scripts/install.ps1 | iex
```

安装过程自动：
1. 检测当前类OpenClaw架构（悟空~/.real | OpenClaw~/.openclaw | Hermes~/.hermes）
2. 安装依赖生态组件
3. 向云枢注册终端（如配置了 CLAWSHELL_CLOUD_URL）
4. 启动 Edge Sync Daemon

### 云枢部署

```bash
cd deploy/cloud/terraform
terraform init && terraform apply
# 自动创建: ECS + VPC + OSS + Docker Compose
```

---

## 快速开始

### 端侧 CLI

```bash
# 查看同步状态
clawshell-edge status

# 拉取云枢任务
clawshell-edge pull

# 发布本地事件
clawshell-edge push

# 搜索云端技能
clawshell-edge skills search "deploy"
```

### 云侧 API

```bash
# 查看所有在线端脑
curl https://cloud.clawshell.online/api/v1/nodes/

# 广播事件到所有端脑
curl -X POST https://cloud.clawshell.online/api/v1/events/broadcast \
  -H "Content-Type: application/json" \
  -d '{"type": "insight.broadcast", "payload": {...}}'

# 发布技能
curl -X POST https://cloud.clawshell.online/api/v1/skills/ \
  -H "Content-Type: application/json" \
  -d '{"name": "auto-deploy", "content": "...", "tags": ["devops"]}'
```

---

## 项目结构

```
ClawShell/
├── cloud/                    # 云枢引擎 (部署到ECS)
│   ├── main.py              # FastAPI 统一入口
│   ├── eventbus_cloud.py    # CloudEventBus
│   ├── task_market_cloud.py # CloudTaskMarket
│   ├── swarm_cloud.py       # SwarmCoordinator
│   ├── scheduler_cloud.py   # CronScheduler
│   ├── capability_registry.py # Edge注册+调度
│   ├── task_board.py        # 跨Edge任务共享
│   ├── skill_market.py      # 技能发布/发现/同步
│   └── services/
│       ├── n8n_bridge.py    # N8N Bridge
│       ├── oss_vault.py     # OSS Vault
│       └── vault_api.py     # Vault API
│
├── edge/                     # 端脑组件 (部署到终端)
│   ├── edge_gateway.py      # Edge Gateway 统一入口
│   ├── sync_engine.py       # 同步引擎
│   ├── env_detector.py      # 环境自检测
│   ├── ecosystem_installer.py # 10组件生态安装
│   ├── config_wizard.py     # 交互式配置
│   ├── adapters/
│   │   ├── openclaw_adapter.py  # 悟空/OpenClaw适配
│   │   └── hermes_adapter.py    # Hermes适配
│   └── install.sh / install.ps1 # 一键安装
│
├── lib/                      # 共享引擎 (四层外骨骼)
│   ├── layer1/              # 自感知层
│   ├── layer2/              # 自适应层
│   ├── layer3/              # 自组织层
│   ├── layer4/              # 多Agent集群层
│   ├── core/                # EventBus/Genome/Strategy
│   └── bridge/              # Hermes/持久层/外部Bridge
│
├── deploy/cloud/             # 云部署配置
│   ├── terraform/           # 阿里云ECS IaC
│   ├── nginx.conf           # 反向代理
│   └── docker-compose.yml   # Docker栈
│
└── docs/                     # 文档
    ├── ARCHITECTURE.md      # 架构全景
    ├── USER_GUIDE.md        # 用户指南
    ├── INSTALL.md           # 安装指南
    └── CLIFF_2.0_EVALUATION.md # 2.0架构评估报告
```

---

## 与类OpenClaw架构的关系

ClawShell 以外骨骼定位叠加于类OpenClaw架构之上：

```
┌─────────────────────────────────────────┐
│           类OpenClaw 核心 (后脑)         │
│  (悟空 ~/.real / OpenClaw ~/.openclaw   │
│        / Hermes ~/.hermes)              │
│  ├─ Gateway/Agents/Skills/Channels     │
└──────────────────┬──────────────────────┘
                   │ EventBus 双向通信
┌──────────────────▼──────────────────────┐
│          ClawShell 外骨骼层              │
│  ├─ 自感知 / 自适应 / 自组织 / 集群     │
│  ├─ MCP Bridge / Edge Gateway          │
│  └─ N8N / MemOS / Obsidian 集成        │
└──────────────────┬──────────────────────┘
                   │ HTTPS/WSS
┌──────────────────▼──────────────────────┐
│          ClawShell Cloud Hub (云枢)      │
│  洞察分析 / 成果广播 / 一端成长多端共进  │
└─────────────────────────────────────────┘
```

---

## 指导思想

**工程控制论**: 信息反馈 → 动态调控 → 系统整体思维

ClawShell 的每个能力模块遵循反馈控制环：设定目标 → 执行动作 → 获取反馈 → 比较偏差 → 调整控制。

相关实践方法论：
- [Harness Engineering: Claude Code 实践](https://mp.weixin.qq.com/s/T9THtO_af-X1zTOHQYH9Bw)
- [M 方法论](https://mp.weixin.qq.com/s/GV83pvzAGyLRtZjy53e0Xg)

---

## 许可证

MIT License — 详见 [LICENSE](LICENSE)
