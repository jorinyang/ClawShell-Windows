     1|# ClawShell 2.0 — 云边协同架构全景
     2|
     3|> 版本：v1.2.0 (Cloud-Edge 分离)
     4|> 更新：2026-05-12
     5|> 指导思想：工程控制论
     6|
     7|---
     8|
     9|## 一、架构定位
    10|
    11|ClawShell 2.0 = **一云多端云边协同分布式神经系统**
    12|
    13|```
    14|                     ┌──────────────────────────┐
    15|                     │      Cloud Hub (云枢)      │
    16|                     │   阿里云 ECS + OSS         │
    17|                     │   ┌──────────────────┐   │
    18|                     │   │  FastAPI Server   │   │
    19|                     │   │  EventBus/Task/   │   │
    20|                     │   │  Swarm/Skill/     │   │
    21|                     │   │  Vault/N8N        │   │
    22|                     │   └──────────────────┘   │
    23|                     │   规划/思考/洞察/广播      │
    24|                     └───────────┬──────────────┘
    25|                                 │ HTTPS + WSS
    26|               ┌─────────────────┼─────────────────┐
    27|               │                 │                 │
    28|    ┌──────────▼──┐    ┌────────▼──┐    ┌────────▼──┐
    29|    │  Edge A     │    │  Edge B   │    │  Edge C   │
    30|    │  (WSL)      │    │  (macOS)  │    │  (Linux)  │
    31|    │  Wukong     │    │  OpenClaw │    │  Hermes   │
    32|    │  +Hermes    │    │           │    │           │
    33|    └─────────────┘    └───────────┘    └───────────┘
    34|        端脑: 自感知/自适应/离线自治/注册云枢/拉取洞察
    35|```
    36|
    37|---
    38|
    39|## 二、云枢 (Cloud Hub)
    40|
    41|### 2.1 职责
    42|- **架构规划**: 根据全局信息制定优化策略
    43|- **深度思考/洞察分析**: 聚合多端数据，Hermes协同深度分析
    44|- **复盘总结**: 周期性review任务执行模式，提炼最佳实践
    45|- **整理优化**: 将洞察转化为技能/共识，通过SkillMarket发布
    46|- **成果广播**: EventBus向所有端脑推送优化成果
    47|- **终端管理**: CapabilityRegistry管理所有注册Edge
    48|- **仓库版本控制**: GitHub统一管理，一端成长多端共进
    49|
    50|### 2.2 核心引擎
    51|
    52|| 引擎 | 文件 | 功能 |
    53||------|------|------|
    54|| **CloudEventBus** | `lib/core/eventbus_cloud.py` | 事件持久化/SHA256去重/通配符查询/30天过期/广播 |
    55|| **CloudTaskMarket** | `lib/core/task_market_cloud.py` | 任务CRUD/状态机(pending→in_progress→completed)/优先级队列 |
    56|| **SwarmCoordinator** | `lib/core/swarm_cloud.py` | 节点注册/心跳监控(30s超时)/最小负载分配 |
    57|| **CronScheduler** | `lib/core/scheduler_cloud.py` | 标准5字段cron解析/执行日志 |
    58|| **CapabilityRegistry** | `lib/core/capability_registry.py` | Edge注册/能力声明/主动调度 |
    59|| **GlobalTaskBoard** | `lib/core/task_board.py` | 跨Edge任务共享看板 |
    60|| **SkillMarket** | `lib/core/skill_market.py` | 技能发布/发现/安装/评分 |
    61|| **N8NBridge** | `lib/services/n8n_bridge.py` | 事件→N8N Webhook映射/健康检查 |
    62|| **VaultAPI** | `lib/services/vault_api.py` | Obsidian知识库CRUD/搜索/OSS同步 |
    63|
    64|### 2.3 部署
    65|
    66|```
    67|阿里云 ECS (ecs.c6.large, ~¥120/月)
    68|├── Docker Compose
    69|│   ├── cloud-hub (FastAPI :8000)
    70|│   ├── n8n (:5678)
    71|│   └── Nginx (:80/:443)
    72|├── OSS Bucket (clawshell-vault)
    73|│   └── Obsidian Vault 文件
    74|└── GitHub Actions CI/CD
    75|```
    76|
    77|---
    78|
    79|## 三、端脑 (Edge Brain)
    80|
    81|### 3.1 职责
    82|- **自适应安装**: 检测环境 → 安装依赖 → 适配OpenClaw架构
    83|- **向云枢注册**: 声明能力、上报健康、建立心跳
    84|- **嗅探加载插件**: 自动发现本地MCP服务器/工具/技能
    85|- **协同Agent调度**: 通过TaskMarket认领/执行/完成任务
    86|- **拉取云信息作为行动参考**: 每次行动前pull最新洞察/技能
    87|- **离线自治**: 云枢不可达时，本地EventBus+OfflineQueue独立运行
    88|
    89|### 3.2 核心组件
    90|
    91|| 组件 | 文件 | 功能 |
    92||------|------|------|
    93|| **Edge Sync Daemon** | `scripts/edge_sync_daemon.py` | 5秒周期: scan→enqueue→flush→pull→health |
    94|| **EnvDetector** | `scripts/env_detector.py` | 自动检测WSL/Win/macOS/Linux + OpenClaw路径 |
    95|| **Ecosystem Installer** | `scripts/ecosystem_installer.py` | 10组件一键安装 (chromadb/psutil/websockets/mempalace/n8n/...) |
    96|| **ConfigWizard** | `scripts/config_wizard.py` | 交互式配置Cloud URL/Token/Node ID |
    97|| **OpenClaw Adapter** | `scripts/openclaw_adapter.py` | 写入MCP配置+注册cron任务+创建工作空间 |
    98|| **Hermes Adapter** | `scripts/hermes_adapter.py` | 安装clawshell-edge技能+更新config.yaml |
    99|| **Obsidian Adapter** | `scripts/obsidian_adapter.py` | Vault CRUD/知识图谱/OSS同步 |
   100|
   101|### 3.3 支持架构
   102|
   103|| 架构 | 检测路径 | 适配器 |
   104||------|----------|--------|
   105|| 悟空 | `~/.real/` | openclaw_adapter.py |
   106|| OpenClaw | `~/.openclaw/` | openclaw_adapter.py |
   107|| Hermes | `~/.hermes/` | hermes_adapter.py |
   108|
   109|---
   110|
   111|## 四、共享外骨骼层 (四层架构)
   112|
   113|### Layer 1: 自感知
   114|
   115|| 模块 | 功能 |
   116||------|------|
   117|| HealthMonitor | 27项健康检测 |
   118|| SystemMonitor | CPU/内存监控 |
   119|| DiskMonitor | 磁盘使用监控 |
   120|| ProcessMonitor | 进程状态检测 |
   121|| AgentMonitor | Agent会话监控 |
   122|| GatewayMonitor | Gateway状态监控 |
   123|| ServiceMonitor | 外部服务可用性 |
   124|
   125|### Layer 2: 自适应
   126|
   127|| 模块 | 功能 |
   128||------|------|
   129|| SelfHealing | 自修复系统 (凌晨检测+分阶段修复) |
   130|| Discovery | 能力自发现 |
   131|| ConditionEngine | 事件条件过滤 |
   132|| StrategyEval | 策略效果评估 |
   133|| AdaptiveController | 自适应控制器 |
   134|| RobustController | 鲁棒控制器 (工程控制论) |
   135|
   136|### Layer 3: 自组织
   137|
   138|| 模块 | 功能 |
   139||------|------|
   140|| Organizer | 任务编排引擎 |
   141|| DAGManager | 依赖关系管理 |
   142|| TaskMarket | 任务分发市场 |
   143|| Scheduler | 调度器 |
   144|| N8NClient | N8N工作流集成 |
   145|| ContextManager | 全局上下文管理 |
   146|
   147|### Layer 4: 多Agent集群
   148|
   149|| 模块 | 功能 |
   150||------|------|
   151|| SwarmDiscovery | P2P节点发现 |
   152|| TrustManager | 信任评分管理 |
   153|| EcologyMatcher | 生态位匹配 |
   154|| SwarmProtocol | 协作协议 |
   155|| FailureDetector | 节点失败检测 |
   156|
   157|---
   158|
   159|## 五、通信协议
   160|
   161|### Edge → Cloud (上报)
   162|```
   163|POST /api/v1/events/batch    批量推送本地事件
   164|POST /api/v1/tasks/{id}      任务状态更新
   165|POST /api/v1/health/report   健康上报 (含能力声明)
   166|Auth: Bearer <edge_token> (HMAC-SHA256)
   167|```
   168|
   169|### Cloud → Edge (下发)
   170|```
   171|WSS /ws/events               实时事件推送
   172|Webhook POST <edge>/inbox    任务/技能/记忆更新
   173|Auth: HMAC-SHA256 签名
   174|```
   175|
   176|### 数据流
   177|
   178|```
   179|Edge (本地事件) → scan → OfflineQueue → batch flush → Cloud EventBus
   180|Cloud TaskMarket → pull_tasks → claim → execute → complete → push result
   181|Edge HealthReport → Cloud CapabilityRegistry (5s心跳)
   182|Cloud SkillMarket → search_skills → pull → install → local Skills
   183|Obsidian Vault ← ossutil sync → OSS Bucket ← Vault API
   184|```
   185|
   186|---
   187|
   188|## 六、记忆边界 (硬约束)
   189|
   190|```
   191|🏠 本地 ONLY              ☁️ 云端同步
   192|──────────────────────────────────
   193|MemPalace (SQLite+ChromaDB)
   194|MemOS Local (Node/Bun)
   195|                          MemOS Cloud (memos.memtensor.cn)
   196|Obsidian Vault (本地编辑)  OSS Bucket (存储)
   197|```
   198|
   199|**MemPalace 绝不部署到云端** — 这是用户明确要求的硬边界。
   200|
   201|---
   202|
   203|## 七、设计原则
   204|
   205|| 原则 | 1.0 | 2.0新增 |
   206||------|-----|---------|
   207|| 异构同效 | ✅ | — |
   208|| 异步优先 | ✅ | — |
   209|| 低耦合 | ✅ | — |
   210|| 高鲁棒 | ✅ | — |
   211|| 高泛用 | ✅ | — |
   212|| 高协同 | ✅ | — |
   213|| 可移植 | — | ✅ (跨WSL/macOS/Linux) |
   214|| 幂等性 | — | ✅ (重复安装无副作用) |
   215|| 版本解耦 | — | ✅ (升级不影响已部署框架) |
   216|
   217|---
   218|
   219|## 八、版本历史
   220|
   221|| 版本 | 日期 | 内容 |
   222||------|------|------|
   223|| v1.2.0 | 2026-05-12 | 2.0云边架构矫正: 目录重组/CloudHub入口/README重写/MANIFEST更新 |
   224|| v1.0.0 | 2026-04-30 | 1.0插件封装: 四层架构/94项测试/一键安装 |
   225|| v0.9 | 2026-04-28 | 知识图谱 |
   226|| v0.7 | 2026-04-24 | Hermes双脑协同 |
   227|
   228|---
   229|
   230|*本文档随代码同步更新 | 维护者: ClawShell Cloud Hub*
   231|