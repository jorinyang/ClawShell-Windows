# ClawShell 2.0 — 云边协同架构全景

> 版本：v1.1.0 (Cloud-Edge 分离)
> 更新：2026-05-12
> 指导思想：工程控制论

---

## 一、架构定位

ClawShell 2.0 = **章鱼式分布式神经系统**

```
                     ┌──────────────────────────┐
                     │      Cloud Hub (云枢)      │
                     │   阿里云 ECS + OSS         │
                     │   ┌──────────────────┐   │
                     │   │  FastAPI Server   │   │
                     │   │  EventBus/Task/   │   │
                     │   │  Swarm/Skill/     │   │
                     │   │  Vault/N8N        │   │
                     │   └──────────────────┘   │
                     │   规划/思考/洞察/广播      │
                     └───────────┬──────────────┘
                                 │ HTTPS + WSS
               ┌─────────────────┼─────────────────┐
               │                 │                 │
    ┌──────────▼──┐    ┌────────▼──┐    ┌────────▼──┐
    │  Edge A     │    │  Edge B   │    │  Edge C   │
    │  (WSL)      │    │  (macOS)  │    │  (Linux)  │
    │  Wukong     │    │  OpenClaw │    │  Hermes   │
    │  +Hermes    │    │           │    │           │
    └─────────────┘    └───────────┘    └───────────┘
        端脑: 自感知/自适应/离线自治/注册云枢/拉取洞察
```

---

## 二、云枢 (Cloud Hub)

### 2.1 职责
- **架构规划**: 根据全局信息制定优化策略
- **深度思考/洞察分析**: 聚合多端数据，Hermes协同深度分析
- **复盘总结**: 周期性review任务执行模式，提炼最佳实践
- **整理优化**: 将洞察转化为技能/共识，通过SkillMarket发布
- **成果广播**: EventBus向所有端脑推送优化成果
- **终端管理**: CapabilityRegistry管理所有注册Edge
- **仓库版本控制**: GitHub统一管理，一端成长多端共进

### 2.2 核心引擎

| 引擎 | 文件 | 功能 |
|------|------|------|
| **CloudEventBus** | `lib/core/eventbus_cloud.py` | 事件持久化/SHA256去重/通配符查询/30天过期/广播 |
| **CloudTaskMarket** | `lib/core/task_market_cloud.py` | 任务CRUD/状态机(pending→in_progress→completed)/优先级队列 |
| **SwarmCoordinator** | `lib/core/swarm_cloud.py` | 节点注册/心跳监控(30s超时)/最小负载分配 |
| **CronScheduler** | `lib/core/scheduler_cloud.py` | 标准5字段cron解析/执行日志 |
| **CapabilityRegistry** | `lib/core/capability_registry.py` | Edge注册/能力声明/主动调度 |
| **GlobalTaskBoard** | `lib/core/task_board.py` | 跨Edge任务共享看板 |
| **SkillMarket** | `lib/core/skill_market.py` | 技能发布/发现/安装/评分 |
| **N8NBridge** | `lib/services/n8n_bridge.py` | 事件→N8N Webhook映射/健康检查 |
| **VaultAPI** | `lib/services/vault_api.py` | Obsidian知识库CRUD/搜索/OSS同步 |

### 2.3 部署

```
阿里云 ECS (ecs.c6.large, ~¥120/月)
├── Docker Compose
│   ├── cloud-hub (FastAPI :8000)
│   ├── n8n (:5678)
│   └── Nginx (:80/:443)
├── OSS Bucket (clawshell-vault)
│   └── Obsidian Vault 文件
└── GitHub Actions CI/CD
```

---

## 三、端脑 (Edge Brain)

### 3.1 职责
- **自适应安装**: 检测环境 → 安装依赖 → 适配OpenClaw架构
- **向云枢注册**: 声明能力、上报健康、建立心跳
- **嗅探加载插件**: 自动发现本地MCP服务器/工具/技能
- **协同Agent调度**: 通过TaskMarket认领/执行/完成任务
- **拉取云信息作为行动参考**: 每次行动前pull最新洞察/技能
- **离线自治**: 云枢不可达时，本地EventBus+OfflineQueue独立运行

### 3.2 核心组件

| 组件 | 文件 | 功能 |
|------|------|------|
| **Edge Sync Daemon** | `scripts/edge_sync_daemon.py` | 5秒周期: scan→enqueue→flush→pull→health |
| **EnvDetector** | `scripts/env_detector.py` | 自动检测WSL/Win/macOS/Linux + OpenClaw路径 |
| **Ecosystem Installer** | `scripts/ecosystem_installer.py` | 10组件一键安装 (chromadb/psutil/websockets/mempalace/n8n/...) |
| **ConfigWizard** | `scripts/config_wizard.py` | 交互式配置Cloud URL/Token/Node ID |
| **OpenClaw Adapter** | `scripts/openclaw_adapter.py` | 写入MCP配置+注册cron任务+创建工作空间 |
| **Hermes Adapter** | `scripts/hermes_adapter.py` | 安装clawshell-edge技能+更新config.yaml |
| **Obsidian Adapter** | `scripts/obsidian_adapter.py` | Vault CRUD/知识图谱/OSS同步 |

### 3.3 支持架构

| 架构 | 检测路径 | 适配器 |
|------|----------|--------|
| 悟空 | `~/.real/` | openclaw_adapter.py |
| OpenClaw | `~/.openclaw/` | openclaw_adapter.py |
| Hermes | `~/.hermes/` | hermes_adapter.py |

---

## 四、共享外骨骼层 (四层架构)

### Layer 1: 自感知

| 模块 | 功能 |
|------|------|
| HealthMonitor | 27项健康检测 |
| SystemMonitor | CPU/内存监控 |
| DiskMonitor | 磁盘使用监控 |
| ProcessMonitor | 进程状态检测 |
| AgentMonitor | Agent会话监控 |
| GatewayMonitor | Gateway状态监控 |
| ServiceMonitor | 外部服务可用性 |

### Layer 2: 自适应

| 模块 | 功能 |
|------|------|
| SelfHealing | 自修复系统 (凌晨检测+分阶段修复) |
| Discovery | 能力自发现 |
| ConditionEngine | 事件条件过滤 |
| StrategyEval | 策略效果评估 |
| AdaptiveController | 自适应控制器 |
| RobustController | 鲁棒控制器 (工程控制论) |

### Layer 3: 自组织

| 模块 | 功能 |
|------|------|
| Organizer | 任务编排引擎 |
| DAGManager | 依赖关系管理 |
| TaskMarket | 任务分发市场 |
| Scheduler | 调度器 |
| N8NClient | N8N工作流集成 |
| ContextManager | 全局上下文管理 |

### Layer 4: 多Agent集群

| 模块 | 功能 |
|------|------|
| SwarmDiscovery | P2P节点发现 |
| TrustManager | 信任评分管理 |
| EcologyMatcher | 生态位匹配 |
| SwarmProtocol | 协作协议 |
| FailureDetector | 节点失败检测 |

---

## 五、通信协议

### Edge → Cloud (上报)
```
POST /api/v1/events/batch    批量推送本地事件
POST /api/v1/tasks/{id}      任务状态更新
POST /api/v1/health/report   健康上报 (含能力声明)
Auth: Bearer <edge_token> (HMAC-SHA256)
```

### Cloud → Edge (下发)
```
WSS /ws/events               实时事件推送
Webhook POST <edge>/inbox    任务/技能/记忆更新
Auth: HMAC-SHA256 签名
```

### 数据流

```
Edge (本地事件) → scan → OfflineQueue → batch flush → Cloud EventBus
Cloud TaskMarket → pull_tasks → claim → execute → complete → push result
Edge HealthReport → Cloud CapabilityRegistry (5s心跳)
Cloud SkillMarket → search_skills → pull → install → local Skills
Obsidian Vault ← ossutil sync → OSS Bucket ← Vault API
```

---

## 六、记忆边界 (硬约束)

```
🏠 本地 ONLY              ☁️ 云端同步
──────────────────────────────────
MemPalace (SQLite+ChromaDB)
MemOS Local (Node/Bun)
                          MemOS Cloud (memos.memtensor.cn)
Obsidian Vault (本地编辑)  OSS Bucket (存储)
```

**MemPalace 绝不部署到云端** — 这是用户明确要求的硬边界。

---

## 七、设计原则

| 原则 | 1.0 | 2.0新增 |
|------|-----|---------|
| 异构同效 | ✅ | — |
| 异步优先 | ✅ | — |
| 低耦合 | ✅ | — |
| 高鲁棒 | ✅ | — |
| 高泛用 | ✅ | — |
| 高协同 | ✅ | — |
| 可移植 | — | ✅ (跨WSL/macOS/Linux) |
| 幂等性 | — | ✅ (重复安装无副作用) |
| 版本解耦 | — | ✅ (升级不影响已部署框架) |

---

## 八、版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| v1.1.0 | 2026-05-12 | 2.0云边架构矫正: 目录重组/CloudHub入口/README重写/MANIFEST更新 |
| v1.0.0 | 2026-04-30 | 1.0插件封装: 四层架构/94项测试/一键安装 |
| v0.9 | 2026-04-28 | 知识图谱 |
| v0.7 | 2026-04-24 | Hermes双脑协同 |

---

*本文档随代码同步更新 | 维护者: ClawShell Cloud Hub*
