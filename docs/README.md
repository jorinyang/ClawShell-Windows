     1|# ClawShell v1.0 - 自感知自适应自组织AI Agent编排系统
     2|
     3|## 概述
     4|
     5|ClawShell是基于钱学森《工程控制论》思想构建的增强型外骨骼AI Agent编排系统，具备**自感知**、**自适应**、**自组织**三大核心能力。
     6|
     7|## 架构
     8|
     9|```
    10|┌─────────────────────────────────────────────────────────────────┐
    11|│                         ClawShell v1.0                          │
    12|├─────────────────────────────────────────────────────────────────┤
    13|│  Layer4 (集群层)  │ Swarm │ Trust │ Ecology │ Protocol        │
    14|├─────────────────────────────────────────────────────────────────┤
    15|│  Layer3 (自组织层) │ DAG   │ TaskMarket │ Scheduler │ N8N     │
    16|├─────────────────────────────────────────────────────────────────┤
    17|│  Layer2 (自适应层) │ Self-Repair │ Discovery │ Condition │ ML  │
    18|├─────────────────────────────────────────────────────────────────┤
    19|│  Layer1 (自感知层) │ Health │ System │ Disk │ Process │ Agent │
    20|├─────────────────────────────────────────────────────────────────┤
    21|│  Core (核心设施)   │ EventBus │ Genome │ Strategy              │
    22|├─────────────────────────────────────────────────────────────────┤
    23|│  Bridge           │ Hermes │ Persistence │ External             │
    24|└─────────────────────────────────────────────────────────────────┘
    25|```
    26|
    27|## 目录结构
    28|
    29|```
    30|clawshell_v1/
    31|├── CLAWSHELL_VERSION      # 版本标识 (1.1.0)
    32|├── MANIFEST.json           # 能力清单
    33|├── bin/
    34|│   ├── clawshell          # 主入口CLI
    35|│   └── clawsync           # Hermes同步脚本
    36|├── lib/
    37|│   ├── core/              # 核心基础设施
    38|│   │   ├── eventbus/     # 事件总线
    39|│   │   ├── genome/       # 知识传承
    40|│   │   └── strategy/     # 策略库
    41|│   ├── layer1/           # 自感知层
    42|│   ├── layer2/           # 自适应层
    43|│   ├── layer3/           # 自组织层
    44|│   ├── layer4/           # 集群层
    45|│   ├── bridge/           # Bridge接口
    46|│   ├── detector/         # 检测模块
    47|│   └── utils/            # 工具函数
    48|├── scripts/              # 运维脚本
    49|├── config/               # 配置模板
    50|├── tests/                # 测试套件
    51|└── docs/                 # 文档
    52|```
    53|
    54|## 核心能力
    55|
    56|### Layer1 - 自感知层
    57|- 健康检查 (health_check)
    58|- 系统监控 (system_mon)
    59|- 磁盘监控 (disk_mon)
    60|- 进程监控 (process_mon)
    61|- Agent监控 (agent_mon)
    62|- 网关监控 (gateway_mon)
    63|- 服务监控 (service_mon)
    64|
    65|### Layer2 - 自适应层
    66|- 自修复 (self_repair)
    67|- 市场发现 (market_discovery)
    68|- 条件引擎 (condition)
    69|- 策略选择 (strategy)
    70|- 状态收集 (state_collector)
    71|- 分析响应 (analyzer/responder)
    72|- 紧急响应 (emergency)
    73|- ML引擎 (ml_engine)
    74|
    75|### Layer3 - 自组织层
    76|- DAG编排 (dag)
    77|- 任务市场 (task_market)
    78|- 任务注册 (task_registry)
    79|- 任务协调 (task_coordinator)
    80|- 调度器 (scheduler)
    81|- N8N集成 (n8n_client)
    82|- 上下文管理 (context_manager)
    83|
    84|### Layer4 - 集群层
    85|- Swarm管理 (swarm)
    86|- 信任评估 (trust)
    87|- 生态系统 (ecology)
    88|- 协议 (protocol)
    89|- 节点发现 (swarm_discovery)
    90|- 信任撤销 (trust_revocator)
    91|
    92|## 使用方法
    93|
    94|### CLI入口
    95|```bash
    96|# 查看状态
    97|clawshell status
    98|
    99|# 健康检查
   100|clawshell health
   101|
   102|# EventBus状态
   103|clawshell events
   104|
   105|# TaskMarket状态
   106|clawshell market
   107|
   108|# Swarm集群状态
   109|clawshell swarm
   110|
   111|# Hermes同步
   112|clawshell sync
   113|```
   114|
   115|### Python导入
   116|```python
   117|import sys
   118|sys.path.insert(0, '~/.悟空/clawshell_v1')
   119|
   120|from lib.core import eventbus, genome, strategy
   121|from lib.layer1 import HealthMonitor
   122|from lib.layer2 import SelfHealing, Discovery
   123|from lib.layer3 import DAG, TaskMarket
   124|from lib.layer4 import SwarmDiscovery
   125|```
   126|
   127|## 版本历史
   128|
   129|- v1.1.0 (2026-04-30) - 统一封装，整合v0.1-v0.9全部模块
   130|
   131|---
   132|*基于工程控制论原理构建 | 智询工作室*
   133|