     1|# ClawShell
     2|
     3|> **版本**: 1.1.0
     4|> **定位**: 悟空 增强型外骨骼功能插件
     5|> **架构**: 自感知 × 自适应 × 自组织 × 多Agent集群
     6|
     7|ClawShell 是一个基于Harness Engineering思想，专为类 悟空 架构（包含Hermes、阿里悟空、easyclaw等）设计的增强型外骨骼插件，通过四层架构（自感知、自适应、自组织、集群层）为核心系统叠加新能力，实现无需侵入原有代码的功能增强。
     8|
     9|详情请查看[ClawShell系统生态全景文档](ARCHITECTURE.md)
    10|
    11|---
    12|
    13|## 目录
    14|
    15|- [特性](#特性)
    16|- [安装](#安装)
    17|- [快速开始](#快速开始)
    18|- [架构概览](#架构概览)
    19|- [模块详解](#模块详解)
    20|- [使用指南](#使用指南)
    21|- [配置参考](#配置参考)
    22|- [开发指南](#开发指南)
    23|- [故障排除](#故障排除)
    24|- [许可证](#许可证)
    25|
    26|---
    27|
    28|## 特性
    29|
    30|| 特性 | 说明 |
    31||------|------|
    32|| **四层增强架构** | 自感知 → 自适应 → 自组织 → 多Agent集群 |
    33|| **无侵入设计** | 不修改 悟空 核心代码，保持版本解耦 |
    34|| **低耦合通信** | 模块间通过 EventBus 和文件协议通信 |
    35|| **Hermes 双脑协同** | 悟空（后脑）+ Hermes（前脑）双向联动 |
    36|| **自修复系统** | 凌晨自动检测 + 分阶段修复，故障自愈 |
    37|| **多持久层支持** | Genome / MemOS / MemPalace / Obsidian / 知识图谱 |
    38|| **N8N 工作流集成** | 完整的工作流自动化编排 |
    39|| **幂等安装** | 重复安装无副作用，可随时回滚 |
    40|
    41|---
    42|
    43|## 安装
    44|
    45|### 环境要求
    46|
    47|| 依赖 | 最低版本 | 说明 |
    48||------|----------|------|
    49|| Python | 3.8+ | 主运行环境 |
    50|| psutil | 5.9.0 | 系统监控 |
    51|| pyyaml | 6.0 | 配置管理 |
    52|| requests | 2.28.0 | HTTP 请求 |
    53|| curl | - | Shell 工具 |
    54|| git | - | 版本控制 |
    55|
    56|### 安装步骤
    57|
    58|```bash
    59|# 1. 克隆仓库
    60|git clone https://github.com/jorinyang/ClawShell.git
    61|cd ClawShell
    62|
    63|# 2. 安装 Python 依赖
    64|pip install -r requirements.txt
    65|
    66|# 3. 安装系统工具（如缺少）
    67|# macOS
    68|brew install curl jq git
    69|# Ubuntu/Debian
    70|sudo apt-get install curl jq git
    71|
    72|# 4. 运行安装脚本
    73|bash install.sh
    74|
    75|# 5. 验证安装
    76|python -m clawshell.cli status
    77|```
    78|
    79|### 悟空用户安装
    80|
    81|悟空用户可以直接通过 skills 安装 ClawShell-Debug 技能进行自动化安装和调试。只需对悟空说：
    82|
    83|```
    84|帮我安装 ClawShell-Debug 技能
    85|```
    86|
    87|该技能支持以下功能：
    88|
    89|| 功能 | 说明 |
    90||------|------|
    91|| **自动化安装** | 克隆仓库、配置路径、验证导入 |
    92|| **模块诊断** | 42个模块导入验证，实时反馈问题 |
    93|| **Bug修复** | 自动修复已知导入路径错误（condition.py、task_market.py、hermes/） |
    94|| **健康检测** | Layer1-4 全链路功能测试 |
    95|
    96|**触发词示例**：
    97|
    98|- "ClawShell安装"
    99|- "ClawShell调试"
   100|- "ClawShell报错"
   101|- "无法导入 lib.layer2"
   102|- "bridge/hermes 模块问题"
   103|
   104|---
   105|
   106|### 验证安装
   107|
   108|```bash
   109|# 检查健康状态
   110|clawshell health
   111|
   112|# 检查版本
   113|clawshell version
   114|
   115|# 检查所有组件
   116|clawshell status
   117|```
   118|
   119|---
   120|
   121|## 快速开始
   122|
   123|### CLI 使用
   124|
   125|```bash
   126|# 查看状态
   127|clawshell status
   128|
   129|# 查看健康检查
   130|clawshell health
   131|
   132|# 查看事件总线
   133|clawshell events
   134|
   135|# 查看任务市场
   136|clawshell market
   137|
   138|# 查看集群状态
   139|clawshell swarm
   140|```
   141|
   142|### Python API 使用
   143|
   144|```python
   145|from lib.layer1 import HealthMonitor
   146|from lib.layer2 import SelfHealing, Discovery
   147|from lib.layer3 import DAG, TaskMarket
   148|from lib.layer4 import SwarmDiscovery
   149|from lib.bridge.hermes import HermesBridge
   150|
   151|# 健康检查
   152|monitor = HealthMonitor()
   153|report = monitor.check()
   154|
   155|# 任务市场
   156|market = TaskMarket()
   157|tasks = market.list_tasks()
   158|
   159|# Hermes 桥接
   160|bridge = HermesBridge()
   161|bridge.connect()
   162|```
   163|
   164|---
   165|
   166|## 架构概览
   167|
   168|### 系统定位
   169|
   170|ClawShell 以"外骨骼"的定位叠加于 悟空 之上，通过标准化接口与 悟空 交互，不修改其核心代码，实现能力增强的同时保持版本独立演进。
   171|
   172|### 四层架构
   173|
   174|```
   175|┌─────────────────────────────────────────────────────┐
   176|│                  ClawShell 外骨骼层                    │
   177|├─────────────────────────────────────────────────────┤
   178|│  Layer 4: 多Agent集群                               │
   179|│  ├─ SwarmDiscovery  集群发现                       │
   180|│  ├─ TrustManager    信任评估                       │
   181|│  ├─ EcologyMatcher   生态位匹配                     │
   182|│  └─ SwarmProtocol   协作协议                       │
   183|├─────────────────────────────────────────────────────┤
   184|│  Layer 3: 自组织                                    │
   185|│  ├─ Organizer       任务编排                       │
   186|│  ├─ TaskMarket      任务市场                       │
   187|│  ├─ DAGManager      依赖管理                       │
   188|│  └─ N8NClient       工作流集成                      │
   189|├─────────────────────────────────────────────────────┤
   190|│  Layer 2: 自适应                                    │
   191|│  ├─ SelfHealing     自修复系统                     │
   192|│  ├─ Discovery       能力发现                       │
   193|│  ├─ ConditionEngine  条件引擎                       │
   194|│  └─ StrategyEval     策略评估                       │
   195|├─────────────────────────────────────────────────────┤
   196|│  Layer 1: 自感知                                    │
   197|│  ├─ HealthMonitor   健康检测                       │
   198|│  ├─ SystemMonitor   系统监控                       │
   199|│  ├─ DiskMonitor     磁盘监控                       │
   200|│  ├─ ProcessMonitor  进程监控                       │
   201|│  └─ AgentMonitor    Agent监控                      │
   202|└─────────────────────────────────────────────────────┘
   203|                    ↕ EventBus ↕
   204|┌─────────────────────────────────────────────────────┐
   205|│                  悟空 核心层                      │
   206|│  ├─ Gateway        网关                           │
   207|│  ├─ Agents         Agent调度                       │
   208|│  ├─ Skills         技能加载                        │
   209|│  └─ Channels       通道管理                        │
   210|└─────────────────────────────────────────────────────┘
   211|```
   212|
   213|### 与 悟空 的关系
   214|
   215|```
   216|┌─────────────────────────────────────────────────────────┐
   217|│                      悟空                           │
   218|│  (后脑 - 执行引擎)                                     │
   219|│  ├─ Gateway        网关路由                         │
   220|│  ├─ Agent调度      任务分发                        │
   221|│  └─ Skills         技能执行                        │
   222|└───────────────────────┬───────────────────────────────┘
   223|                        │ EventBus 双向通信
   224|┌───────────────────────▼───────────────────────────────┐
   225|│                      ClawShell                          │
   226|│  (外骨骼 - 增强层)                                    │
   227|│  ├─ 自感知         环境信息收集                     │
   228|│  ├─ 自适应         参数调控优化                     │
   229|│  ├─ 自组织         任务编排协调                     │
   230|│  └─ 集群层         多节点协作                       │
   231|└───────────────────────┬───────────────────────────────┘
   232|                        │
   233|┌───────────────────────▼───────────────────────────────┐
   234|│                      Hermes                             │
   235|│  (前脑 - 进化引擎)                                    │
   236|│  ├─ 深度思考       洞察生成                         │
   237|│  ├─ 模式识别       趋势分析                         │
   238|│  └─ 自进化         能力迭代                         │
   239|└─────────────────────────────────────────────────────────┘
   240|```
   241|
   242|---
   243|
   244|## 模块详解
   245|
   246|### Layer 1 - 自感知层
   247|
   248|| 模块 | 文件 | 功能 |
   249||------|------|------|
   250|| HealthMonitor | `lib/layer1/health_check.py` | 27项健康检测 |
   251|| SystemMonitor | `lib/layer1/system_mon.py` | CPU/内存监控 |
   252|| DiskMonitor | `lib/layer1/disk_mon.py` | 磁盘使用监控 |
   253|| ProcessMonitor | `lib/layer1/process_mon.py` | 进程状态检测 |
   254|| AgentMonitor | `lib/layer1/agent_mon.py` | Agent会话监控 |
   255|| GatewayMonitor | `lib/layer1/gateway_mon.py` | Gateway状态监控 |
   256|| ServiceMonitor | `lib/layer1/service_mon.py` | 外部服务可用性 |
   257|
   258|### Layer 2 - 自适应层
   259|
   260|| 模块 | 文件 | 功能 |
   261||------|------|------|
   262|| SelfHealing | `lib/layer2/self_healing.py` | 自修复系统 |
   263|| Discovery | `lib/layer2/discovery.py` | 能力自发现 |
   264|| ConditionEngine | `lib/layer2/condition.py` | 事件条件过滤 |
   265|| StrategyEval | `lib/layer2/strategy.py` | 策略效果评估 |
   266|| StateCollector | `lib/layer2/state_collector.py` | 状态收集 |
   267|| Analyzer | `lib/layer2/analyzer.py` | 数据分析 |
   268|| Responder | `lib/layer2/responder.py` | 响应生成 |
   269|| Emergency | `lib/layer2/emergency.py` | 应急处理 |
   270|| MLEngine | `lib/layer2/ml_engine.py` | AI/ML 推理 |
   271|| MarketDiscovery | `lib/layer2/market_discovery.py` | 市场发现 |
   272|
   273|### Layer 3 - 自组织层
   274|
   275|| 模块 | 文件 | 功能 |
   276||------|------|------|
   277|| Organizer | `lib/layer3/organizer.py` | 任务编排引擎 |
   278|| DAGManager | `lib/layer3/dag.py` | 依赖关系管理 |
   279|| TaskMarket | `lib/layer3/task_market.py` | 任务分发市场 |
   280|| TaskRegistry | `lib/layer3/task_registry.py` | 任务注册表 |
   281|| TaskCoordinator | `lib/layer3/task_coordinator.py` | 任务协调 |
   282|| Scheduler | `lib/layer3/scheduler.py` | 调度器 |
   283|| N8NClient | `lib/layer3/n8n_client.py` | N8N 工作流 |
   284|| ContextManager | `lib/layer3/context_manager.py` | 上下文管理 |
   285|
   286|### Layer 4 - 集群层
   287|
   288|| 模块 | 文件 | 功能 |
   289||------|------|------|
   290|| SwarmDiscovery | `lib/layer4/swarm_discovery.py` | P2P 节点发现 |
   291|| TrustManager | `lib/layer4/trust_manager.py` | 信任评分管理 |
   292|| TrustEvaluator | `lib/layer4/trust_evaluator.py` | 信任评估计算 |
   293|| TrustRevocator | `lib/layer4/trust_revocator.py` | 信任动态撤销 |
   294|| EcologyMatcher | `lib/layer4/ecology.py` | 生态位匹配 |
   295|| FailureDetector | `lib/layer4/failure_detector.py` | 节点失败检测 |
   296|| MetricsCollector | `lib/layer4/metrics_collector.py` | 指标收集 |
   297|| WeightCalculator | `lib/layer4/weight_calculator.py` | 权重计算 |
   298|
   299|### Bridge - 接口层
   300|
   301|#### Hermes Bridge
   302|
   303|| 模块 | 文件 | 功能 |
   304||------|------|------|
   305|| HermesBridge | `lib/bridge/hermes/bridge.py` | EventBus 双向通信 |
   306|| ScenarioIntegrator | `lib/bridge/hermes/scenario_integrator.py` | 7大场景集成 |
   307|| TriggerConfig | `lib/bridge/hermes/trigger_config.py` | 分级触发配置 |
   308|| Classifier | `lib/bridge/hermes/classifier.py` | 优先级分类 |
   309|| Matcher | `lib/bridge/hermes/matcher.py` | 响应模式匹配 |
   310|
   311|#### Persistence Bridge
   312|
   313|| 模块 | 文件 | 功能 |
   314||------|------|------|
   315|| GenomeBridge | `lib/bridge/persistence/` | 知识传承 |
   316|| MemOSBridge | `lib/bridge/persistence/` | MemOS 云端 |
   317|| MemPalaceBridge | `lib/bridge/persistence/` | 记忆宫殿 |
   318|| ObsidianBridge | `lib/bridge/persistence/` | Obsidian 笔记 |
   319|| KnowledgeGraphBridge | `lib/bridge/persistence/` | 知识图谱 |
   320|
   321|#### External Bridge
   322|
   323|| 模块 | 文件 | 功能 |
   324||------|------|------|
   325|| N8NBridge | `lib/bridge/external/n8n_client.py` | N8N 工作流 |
   326|| DockerBridge | `lib/bridge/external/` | Docker 容器 |
   327|| AliyunBridge | `lib/bridge/external/` | 阿里云服务 |
   328|| GitHubBridge | `lib/bridge/external/` | GitHub API |
   329|| TrainBridge | `lib/bridge/external/` | 12306 车次 |
   330|| RedisBridge | `lib/bridge/external/` | Redis 队列 |
   331|| DiscordBridge | `lib/bridge/external/` | Discord 通知 |
   332|
   333|### Core - 核心基础设施
   334|
   335|| 模块 | 目录 | 功能 |
   336||------|------|------|
   337|| EventBus | `lib/core/eventbus/` | 事件总线 |
   338|| Genome | `lib/core/genome/` | 知识传承存储 |
   339|| Strategy | `lib/core/strategy/` | 策略库 |
   340|
   341|---
   342|
   343|## 使用指南
   344|
   345|### 事件总线
   346|
   347|```python
   348|from lib.core.eventbus import EventBus, Event
   349|
   350|# 创建事件
   351|event = Event(
   352|    event_type="task.completed",
   353|    payload={"task_id": "001", "agent": "lab"}
   354|)
   355|
   356|# 发布事件
   357|bus = EventBus()
   358|bus.publish(event)
   359|
   360|# 订阅事件
   361|def on_task_completed(event):
   362|    print(f"Task {event.payload['task_id']} completed")
   363|
   364|bus.subscribe("task.completed", on_task_completed)
   365|```
   366|
   367|### 任务市场
   368|
   369|```python
   370|from lib.layer3 import TaskMarket
   371|
   372|market = TaskMarket()
   373|
   374|# 注册任务
   375|market.register({
   376|    "task_id": "research-001",
   377|    "type": "analysis",
   378|    "priority": "high",
   379|    "budget_minutes": 60
   380|})
   381|
   382|# 认领任务
   383|task = market.claim(agent_id="lab")
   384|
   385|# 完成任务
   386|market.complete(task["task_id"])
   387|```
   388|
   389|### 自修复系统
   390|
   391|```python
   392|from lib.layer2 import SelfHealing
   393|
   394|healer = SelfHealing()
   395|
   396|# 运行自检
   397|issues = healer.detect()
   398|
   399|# 执行修复
   400|for issue in issues:
   401|    result = healer.repair(issue)
   402|    print(f"Repaired: {issue['type']} - {result}")
   403|```
   404|
   405|---
   406|
   407|## 配置参考
   408|
   409|### 环境配置
   410|
   411|```yaml
   412|# config/default.yaml
   413|clawshell:
   414|  version: "1.1.0"
   415|  
   416|  layer1:
   417|    health_check_interval: 300  # 5分钟
   418|    monitor_intervals:
   419|      system: 60
   420|      disk: 300
   421|      process: 30
   422|      agent: 300
   423|
   424|  layer2:
   425|    self_repair_enabled: true
   426|    self_repair_schedule: "0 5 * * *"  # 每日5点
   427|    discovery_auto_register: true
   428|
   429|  layer3:
   430|    task_budget_default: 30  # 分钟
   431|    market_matching_threshold: 0.7
   432|
   433|  layer4:
   434|    swarm_port: 7890
   435|    trust_initial: 0.5
   436|    trust_decay_rate: 0.95
   437|
   438|  bridge:
   439|    hermes:
   440|      enabled: true
   441|      sync_interval: 300
   442|    persistence:
   443|      genome_path: "~/.悟空/genome/"
   444|      memos_api_url: "https://memos.memtensor.cn/api/"
   445|```
   446|
   447|---
   448|
   449|## 开发指南
   450|
   451|### 添加新模块
   452|
   453|1. 在对应层级目录创建模块文件
   454|2. 在 `__init__.py` 中导出
   455|3. 添加单元测试到 `tests/`
   456|4. 更新 `MANIFEST.json`
   457|
   458|### 运行测试
   459|
   460|```bash
   461|# 运行所有测试
   462|python -m pytest tests/
   463|
   464|# 运行特定层级测试
   465|python -m pytest tests/test_layer1/
   466|python -m pytest tests/test_layer2/
   467|
   468|# 生成覆盖率报告
   469|python -m pytest tests/ --cov=lib --cov-report=html
   470|```
   471|
   472|---
   473|
   474|## 故障排除
   475|
   476|### 常见问题
   477|
   478|| 问题 | 解决方案 |
   479||------|----------|
   480|| 导入错误 | 检查 `PYTHONPATH` 是否包含项目根目录 |
   481|| 权限错误 | 确保 `bin/` 目录有执行权限 `chmod +x bin/*` |
   482|| 依赖缺失 | 运行 `pip install -r requirements.txt` |
   483|| EventBus 连接失败 | 检查 悟空 Gateway 是否运行 |
   484|| Hermes 同步失败 | 检查网络连通性和 API 配置 |
   485|
   486|### 日志位置
   487|
   488|```
   489|~/.悟空/logs/
   490|├── clawshell.log          # 主日志
   491|├── eventbus.log           # 事件总线日志
   492|├── hermes_bridge.log      # Hermes 桥接日志
   493|└── self_repair.log       # 自修复日志
   494|```
   495|
   496|---
   497|
   498|## 架构文档
   499|
   500|完整的系统架构文档请参考 [ARCHITECTURE.md](./ARCHITECTURE.md)，包含：
   501|
   502|- 第一章：系统概述与定位
   503|- 第二章：双脑协同系统生态全景图
   504|- 第三章：目录结构与组件分布
   505|- 第八章：双脑协同架构
   506|- 第九章：自修复系统
   507|- 第十三章：依赖关系与数据流
   508|
   509|---
   510|
   511|## 许可证
   512|
   513|MIT License
   514|
   515|Copyright (c) 2026 智询工作室
   516|
   517|Permission is hereby granted, free of charge, to any person obtaining a copy
   518|of this software and associated documentation files (the "Software"), to deal
   519|in the Software without restriction, including without limitation the rights
   520|to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
   521|copies of the Software, and to permit persons to whom the Software is
   522|furnished to do so, subject to the following conditions:
   523|
   524|The above copyright notice and this permission notice shall be included in all
   525|copies or substantial portions of the Software.
   526|
   527|THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
   528|IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
   529|FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
   530|