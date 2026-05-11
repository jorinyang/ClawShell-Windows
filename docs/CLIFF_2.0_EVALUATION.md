     1|# ClawShell 2.0 架构评估报告
     2|
     3|> 评估日期：2026-05-12
     4|> 评估范围：ClawShell-Windows + ClawShell-MacOS vs 2.0云边协同规划
     5|
     6|---
     7|
     8|## 一、2.0 规划核心要素回顾
     9|
    10|ClawShell 2.0 = **1个云枢（主脑）+ N个端脑（副脑）**，章鱼式分布式神经系统。
    11|
    12|| 角色 | 职责 | 部署位置 |
    13||------|------|----------|
    14|| **云枢 Cloud Hub** | 架构规划/深度思考/洞察分析/复盘总结/整理优化/成果广播/终端管理/仓库版本控制/自组织集群协作 | 阿里云ECS+OSS+GitHub+MemOS Cloud |
    15|| **端脑 Edge Brain** | 自适应安装/注册云枢/嗅探加载插件/协同Agent调度工具/拉取云信息作为行动参考/离线自治/自感知+自适应 | 各终端 (~/.real, ~/.openclaw, ~/.hermes) |
    16|
    17|**2.0新增原则**: 端侧可移植/幂等性/版本解耦
    18|**保留1.0原则**: 异构同效/异步优先/低耦合/高鲁棒/高泛用/高协同
    19|
    20|---
    21|
    22|## 二、ClawShell-Windows 评估
    23|
    24|### 2.1 基本信息
    25|- **仓库**: github.com/jorinyang/ClawShell-Windows
    26|- **本地路径**: ~/.ClawShell
    27|- **规模**: ~300+文件，~90脚本，~30核心模块
    28|- **版本**: CLAWSHELL_VERSION=1.1.0, git tag=v1.1.0
    29|- **演变历程**: v0.1(架构搭建) → v0.9(插件封装) → v1.0(云引擎) → v1.1(Edge Sync Daemon)
    30|
    31|### 2.2 能力匹配矩阵
    32|
    33|#### 云枢能力
    34|
    35|| 2.0要求 | 当前状态 | 实现模块 | 匹配度 |
    36||----------|----------|----------|--------|
    37|| 架构规划 | **部分** — 只有engine，没有planning agent | Cloud引擎集合 | 60% |
    38|| 深度思考/洞察分析 | **已实现** — Hermes双脑协同 | lib/bridge/hermes/ | 85% |
    39|| 复盘总结 | **部分** — edge_sync_daemon拉数据但缺主动复盘 | scripts/hermes_insight_consumer.py | 50% |
    40|| 整理优化 | **已实现** — SkillMarket + Skill发布/发现 | lib/core/skill_market.py | 75% |
    41|| 成果广播 | **已实现** — CloudEventBus | lib/core/eventbus_cloud.py | 80% |
    42|| 终端管理 | **已实现** — CapabilityRegistry + SwarmCoordinator | lib/core/capability_registry.py | 85% |
    43|| 共识信息部署云端 | **已实现** — 阿里云ECS/OSS/GitHub/MemOS Cloud配置就绪 | deploy/cloud/ | 70% |
    44|| 自我成长迭代 | **缺失** — 无CloudHub自进化闭环 | — | 20% |
    45|| 一端成长多端共进 | **部分** — SkillMarket有发布/发现但缺洞察广播 | lib/core/skill_market.py | 40% |
    46|| 仓库版本控制 | **已实现** — GitHub OAuth + CI/CD | .github/workflows/ | 90% |
    47|
    48|#### 端脑能力
    49|
    50|| 2.0要求 | 当前状态 | 实现模块 | 匹配度 |
    51||----------|----------|----------|--------|
    52|| 安装配置 | **已实现** — install.sh/ps1 | scripts/install.sh | 85% |
    53|| 自适应多架构 | **已实现** — 支持Wukong/Hermes/OpenClaw检测 | scripts/env_detector.py | 90% |
    54|| 向云枢注册 | **已实现** — register_edge() | scripts/edge_sync_daemon.py | 80% |
    55|| 嗅探加载插件 | **已实现** — 10组件生态安装器 | scripts/ecosystem_installer.py | 85% |
    56|| 各端独立插件/工具 | **已实现** — MCP Bridge + 三方工具 | scripts/mcp_bridge_daemon.py | 80% |
    57|| 协同Agent调度工具 | **已实现** — TaskMarket + TaskBoard | lib/core/task_market_cloud.py | 80% |
    58|| 拉取云信息作为参考 | **已实现** — pull_tasks() + search_skills() | edge_sync_daemon.py | 75% |
    59|| 离线自治 | **已实现** — OfflineQueue + 本地降级 | edge_sync_daemon.py | 85% |
    60|| 自感知+自适应 | **已实现** — 完整L1+L2层 | lib/layer1/, lib/layer2/ | 90% |
    61|| 工作流/容器管理 | **已实现** — docker-compose + N8N | docker-compose.yml, n8n_bridge | 80% |
    62|| 适配器写入调用脚本 | **已实现** — openclaw_adapter + hermes_adapter | scripts/*_adapter.py | 85% |
    63|
    64|### 2.3 关键问题
    65|
    66|1. **命名混乱**: 名为"ClawShell-Windows"实为全平台代码，且部署到 ~/.ClawShell 而非Windows特定路径
    67|2. **版本不一致**: CLAWSHELL_VERSION=1.1.0，git tag=v1.1.0，README=1.1.0，MANIFEST=1.1.0
    68|3. **云-端代码混杂**: Cloud引擎(lib/core/*_cloud.py)和Edge代码(scripts/)混在同一目录树，没有明确分层
    69|4. **无CloudHub主程序**: 各Cloud引擎独立存在，缺少统一的CloudHub FastAPI入口整合所有引擎
    70|5. **无CloudHub自进化**: 缺少云枢自我反思→优化→广播的闭环机制
    71|6. **README过期**: 仍然描述为"悟空 增强型外骨骼功能插件 v1.1.0"，未体现2.0云边架构
    72|7. **MANIFEST过期**: source_mapping指向~/.real/，但当前代码在~/.ClawShell/
    73|
    74|---
    75|
    76|## 三、ClawShell-MacOS 评估
    77|
    78|### 3.1 基本信息
    79|- **仓库**: github.com/jorinyang/ClawShell-MacOS
    80|- **创建时间**: 2026-05-11
    81|- **规模**: ~60文件，清晰的Cloud/Local分离
    82|- **描述**: "ClawShell 2.0 — 云端协同的多智能体操作系统（Cloud/Local 分离架构）"
    83|
    84|### 3.2 能力匹配矩阵
    85|
    86|| 评估维度 | 状态 | 说明 |
    87||----------|------|------|
    88|| Cloud/Local目录分离 | **优秀** ✅ | 根目录直接分为ClawShell Cloud/和ClawShell Local/ |
    89|| CloudHub入口 | **已设计** — cloud-hub/src/hub.py | FastAPI统一入口 |
    90|| 端脑Edge Gateway | **已设计** — edge-gateway/src/gateway.py | 统一网关模式 |
    91|| 协议定义 | **已设计** — protocol模块 | 通信协议标准化 |
    92|| 部署自动化 | **已设计** — Ansible + Docker | 比Terraform更轻量 |
    93|| 文档规范 | **优秀** ✅ | SPEC.md + PLANNING.md + IMPLEMENTATION.md |
    94|| **mempalace-cloud** | **违规** ❌ | MemPalace应该只在本地，不应出现在Cloud侧 |
    95|| SSL证书硬编码 | **风险** ⚠️ | nginx/ssl/目录包含server.crt/server.key |
    96|| 实际代码实现量 | **低** ⚠️ | 大部分是脚手架，核心逻辑尚未实现 |
    97|
    98|### 3.3 关键问题
    99|
   100|1. **mempalace-cloud违规**: 违反记忆边界规则(MemPalace=本地)，且无实际实现价值
   101|2. **代码架空**: cloud-hub/domain/各模块均为__init__.py空壳，缺少具体逻辑
   102|3. **与Windows仓库关系不清晰**: 两个repo谁为主？代码如何共享？
   103|4. **实施优先级不明**: PLANNING.md存在但未与Windows仓库的Phase对齐
   104|
   105|---
   106|
   107|## 四、双仓库对比总览
   108|
   109|| 维度 | ClawShell-Windows | ClawShell-MacOS | 胜者 |
   110||------|-------------------|-----------------|------|
   111|| 代码实现完整度 | **高** (30+模块, 90+脚本) | 低 (脚手架为主) | Windows |
   112|| Cloud/Edge分离 | 混杂 | **清晰** | MacOS |
   113|| 文档规范度 | 中等(过期) | **高** (SPEC/PLANNING) | MacOS |
   114|| 自感知/自适应实现 | **完整** (L1+L2层) | 无 | Windows |
   115|| CloudHub统一入口 | 无 (引擎各自独立) | **有** (hub.py设计) | MacOS |
   116|| Edge Gateway | 部分(edge_sync_daemon) | **有** (gateway.py设计) | MacOS |
   117|| 部署方案 | Terraform (ECS) | Ansible + Docker | 各有优劣 |
   118|| 版本管理 | 混乱 | 新建尚未发布 | — |
   119|| **总体成熟度** | **高** | 低 | **Windows** |
   120|
   121|---
   122|
   123|## 五、矫正建议
   124|
   125|### 核心策略：以 ClawShell-Windows 为主仓库，以 ClawShell-MacOS 的结构设计为参考
   126|
   127|1. **Windows仓库重命名**: ClawShell-Windows → ClawShell (或保留名但明确说明是全平台)
   128|2. **目录结构重组**: 引入清晰的 cloud/ edge/ 顶层分离
   129|3. **CloudHub入口实现**: 在cloud/下创建FastAPI main.py整合所有云引擎
   130|4. **Edge Gateway标准化**: edge_sync_daemon升级为Edge Gateway
   131|5. **版本统一**: CLAWSHELL_VERSION → 1.1.0，所有文档同步
   132|6. **MemPalace边界修正**: MacOS删除mempalace-cloud/
   133|7. **README/MANIFEST重写**: 体现2.0云边架构
   134|
   135|---
   136|
   137|*本报告基于设计文档(00-SYSTEM_ARCHITECTURE.md, CLAWSHELL_CORE_DEFINITION.md等)和两个GitHub仓库的实际代码分析生成。*
   138|