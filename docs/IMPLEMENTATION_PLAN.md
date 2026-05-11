# ClawShell 2.0 云边协同 — 完整实施计划
## 版本: v2.0.0-plan | 日期: 2026-05-11

---

## 一、项目全景

```
                    ClawShell 2.0
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼─────┐   ┌──────▼──────┐   ┌────▼─────┐
   │  Cloud   │   │   Deploy    │   │  Local   │
   │  Server  │   │  & Config   │   │  Client  │
   │ (API+WS) │   │  (一键部署)  │   │ (自适配)  │
   └────┬─────┘   └──────┬──────┘   └────┬─────┘
        │                │                │
   ┌────▼─────┐   ┌──────▼──────┐   ┌────▼─────┐
   │Ecosystem│   │  Ecosystem  │   │Ecosystem │
   │ Manager │   │  Installer  │   │ Detector │
   │(阿里云)  │   │  (Terraform)│   │(OpenClaw │
   │         │   │             │   │ Hermes   │
   │         │   │             │   │ Wukong)  │
   └─────────┘   └─────────────┘   └──────────┘
```

## 二、目标架构

### Cloud Side (阿里云 ECS)
```
┌─────────────────────────────────────────────┐
│          Alibaba Cloud ECS (Ubuntu 22.04)    │
│                                              │
│  Docker Compose Stack:                       │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐ │
│  │ClawShell │ │  N8N     │ │ MemOS Cloud │ │
│  │Cloud API │ │ Workflow │ │ Sync Bridge │ │
│  │ :8000    │ │ :5678    │ │ (API Proxy) │ │
│  └────┬─────┘ └────┬─────┘ └──────┬──────┘ │
│       │            │              │         │
│  ┌────┴────────────┴──────────────┴───────┐ │
│  │         PostgreSQL + Redis             │ │
│  │    (TaskMarket + Session Store)        │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  Security: Nginx reverse proxy + Let's Encrypt│
│  Monitoring: Prometheus + Grafana (optional)  │
└──────────────────────────────────────────────┘
```

### Local Side (User Machine)
```
┌─────────────────────────────────────────────┐
│         User Machine (Windows/WSL/macOS)     │
│                                              │
│  install.sh:                                 │
│  ┌──────────────────────────────────────┐   │
│  │ 1. Detect Environment                │   │
│  │    ├── openclaw (.real/.openclaw)     │   │
│  │    ├── hermes  (~/.hermes)            │   │
│  │    └── wukong  (dingtalk-rewind)      │   │
│  │                                      │   │
│  │ 2. Install Edge Client               │   │
│  │    └── pip install clawshell-local   │   │
│  │                                      │   │
│  │ 3. Select Ecosystem                  │   │
│  │    ├── [ ] MemPalace (local memory)  │   │
│  │    ├── [ ] ChromaDB (vector search)  │   │
│  │    ├── [ ] N8N (workflow engine)     │   │
│  │    ├── [ ] MemOS Cloud (sync)        │   │
│  │    ├── [ ] Watchdog (fs monitor)     │   │
│  │    └── [ ] Browser Runtime (CDP)     │   │
│  │                                      │   │
│  │ 4. Configure + Start                │   │
│  └──────────────────────────────────────┘   │
│                                              │
│  clawshell-edge start → Cloud sync active   │
└──────────────────────────────────────────────┘
```

## 组件依赖矩阵 (MemPalace=本地, MemOS Cloud=云端)

### 记忆系统 (明确边界)
| 组件 | 定位 | 位置 | 说明 |
|------|------|------|------|
| **MemPalace** | 本地记忆宫殿 | 🏠 端侧 | SQLite + ChromaDB 向量搜索, 本地优先 |
| **MemOS Local** | 本地记忆插件 | 🏠 端侧 | Node/Bun, 本地记忆管理 |
| **MemOS Cloud** | 云端记忆同步 | ☁️ 云端 | API: memos.memtensor.cn, 跨设备同步 |

### 全组件矩阵
| 组件 | 定位 | 位置 | 安装 |
|------|------|------|------|
| ClawShell Cloud API | 云端服务 | ☁️ | pip + Docker |
| ClawShell Edge Client | 端侧客户端 | 🏠 | pip install |
| MemPalace | 本地记忆 | 🏠 | pip install chromadb |
| ChromaDB | 向量存储 | 🏠 | pip install |
| MemOS Local | 本地记忆 | 🏠 | npm install |
| MemOS Cloud | 云端记忆 | ☁️ | API Key |
| N8N | 工作流引擎 | ☁️ | npx/docker |
| PostgreSQL | 持久化存储 | ☁️ | Docker |
| Nginx | 反向代理 | ☁️ | apt/docker |
| Watchdog | 文件监听 | 🏠 | pip install |
| Browser Runtime | 浏览器控制 | 🏠 | Playwright |
| ONNX Runtime | ML推理 | 🏠 | pip install |
| psutil | 系统监控 | 🏠 | pip install |
| websockets | 实时通信 | 🏠 | pip install |

## 四、目录结构规划

```
clawshell2.0/
├── README.md                          # 项目总览
├── ARCHITECTURE.md                    # 架构文档
├── IMPLEMENTATION_PLAN.md             # 本文档
│
├── ClawShell Cloud/                   # ☁️ 云端服务
│   ├── src/
│   │   ├── main.py                    # FastAPI 入口 [✅ 已创建]
│   │   ├── api/                       # REST API 路由
│   │   │   ├── events.py              # [✅ 已创建]
│   │   │   ├── tasks.py               # [✅ 已创建]
│   │   │   ├── skills.py              # [✅ 已创建]
│   │   │   ├── memory.py              # [✅ 已创建]
│   │   │   └── health.py              # [✅ 已创建]
│   │   ├── core/
│   │   │   ├── config.py              # [✅ 已创建]
│   │   │   ├── auth.py                # [✅ 已创建]
│   │   │   ├── eventbus.py            # [ ] 云端EventBus引擎
│   │   │   ├── task_market.py         # [ ] 任务市场引擎
│   │   │   ├── swarm.py               # [ ] 集群协调器
│   │   │   └── scheduler.py           # [ ] 云端Cron调度
│   │   ├── services/
│   │   │   ├── n8n_bridge.py          # [ ] N8N工作流桥接
│   │   │   ├── memos_sync.py          # [ ] MemOS同步服务
│   │   │   └── skill_repo.py          # [ ] 技能仓库管理
│   │   └── websocket/
│   │       └── handler.py             # [✅ 已创建]
│   ├── Dockerfile                     # [✅ 已创建]
│   ├── docker-compose.yml             # [ ] Docker Compose部署
│   ├── requirements.txt               # [✅ 已创建]
│   └── config/
│       └── config.yaml                # [✅ 已创建]
│
├── ClawShell Local/                   # 💻 端侧客户端
│   ├── src/
│   │   ├── edge_client.py             # [✅ 已创建] 主客户端
│   │   ├── env_detector.py            # [ ] 环境检测器
│   │   ├── ecosystem_installer.py     # [ ] 生态系统安装器
│   │   ├── config_wizard.py           # [ ] 交互式配置向导
│   │   └── adapters/                  # 环境适配器
│   │       ├── openclaw_adapter.py    # [ ] OpenClaw/Wukong适配
│   │       ├── hermes_adapter.py      # [ ] Hermes Agent适配
│   │       └── standalone_adapter.py  # [ ] 独立模式适配
│   ├── scripts/
│   │   ├── install.sh                 # [ ] 一键安装脚本
│   │   ├── install.ps1                # [ ] Windows PowerShell
│   │   ├── start.sh                   # [ ] 启动脚本
│   │   └── uninstall.sh               # [ ] 卸载脚本
│   ├── requirements.txt               # [✅ 已创建]
│   └── config/
│       └── config.yaml                # [✅ 已创建]
│
├── shared/                            # 🔗 共享模块
│   ├── protocol.py                    # [✅ 已创建] 数据模型+认证
│   └── utils.py                       # [ ] 通用工具函数
│
├── deploy/                            # 🚀 部署配置
│   ├── cloud/
│   │   ├── docker-compose.yml         # [ ] 完整服务栈
│   │   ├── nginx.conf                 # [ ] 反向代理配置
│   │   ├── terraform/                 # [ ] 阿里云IaC
│   │   │   ├── main.tf                # [ ] ECS + VPC + SG
│   │   │   ├── variables.tf           # [ ] 变量定义
│   │   │   └── outputs.tf             # [ ] 输出(IP/域名)
│   │   └── ansible/                   # [ ] 配置管理
│   │       ├── playbook.yml           # [ ] 主playbook
│   │       └── inventory.ini          # [ ] 主机清单
│   └── local/
│       └── install.sh                 # [ ] 端侧总入口
│
└── docs/                              # 📚 文档
    ├── USER_GUIDE.md                  # [ ] 用户指南
    ├── API_REFERENCE.md               # [ ] API参考
    └── ECOSYSTEM.md                   # [ ] 生态系统说明
```

## 五、分阶段实施路线图

### Phase 0: 基础骨架 (当前已完成)
**时间**: Done | **文件**: 16 | **状态**: ✅

- [x] 目录结构创建
- [x] shared/protocol.py (数据模型+认证)
- [x] Cloud API 5个路由骨架
- [x] Cloud WebSocket handler
- [x] Cloud config/auth
- [x] Edge client 核心逻辑
- [x] Dockerfile + requirements

---

### Phase 1: 云端核心引擎 (第1-2周)
**目标**: Cloud API 完整可用，可通过 Docker Compose 部署

#### 1.1 Cloud EventBus Engine
- [ ] `core/eventbus.py` — 事件持久化+查询+过期清理
- [ ] 事件去重 (基于event_id)
- [ ] 事件保留策略 (30天自动清理)

#### 1.2 Cloud TaskMarket Engine
- [ ] `core/task_market.py` — 任务CRUD+匹配+分配
- [ ] 任务优先级队列
- [ ] 任务生命周期管理 (pending→in_progress→completed/failed)

#### 1.3 Cloud Swarm Coordinator
- [ ] `core/swarm.py` — 多Edge节点管理
- [ ] 节点注册/心跳/下线检测
- [ ] 任务负载均衡

#### 1.4 Cloud Scheduler
- [ ] `core/scheduler.py` — Cron任务调度
- [ ] 从 config 读取任务定义
- [ ] 执行日志记录

#### 1.5 N8N Bridge
- [ ] `services/n8n_bridge.py` — N8N工作流触发
- [ ] 事件→工作流映射

#### 1.6 Docker Compose
- [ ] `docker-compose.yml` — 完整服务栈
  - ClawShell Cloud API
  - N8N (可选)
  - PostgreSQL (可选, 持久化)
  - Nginx (反向代理+SSL)

**交付物**: 
- 可运行 `docker compose up -d` 一键启动
- Cloud API 全部endpoint可用
- 健康检查通过

---

### Phase 2: 端侧自适配 + 生态安装器 (第2-3周)
**目标**: 端侧一键安装，自动检测环境，可选安装生态组件

#### 2.1 环境检测器 `env_detector.py`
```python
class EnvironmentDetector:
    def detect_all() -> dict:
        return {
            "openclaw": {"found": True, "path": "/mnt/c/Users/Aorus/.real", "type": "wukong"},
            "hermes": {"found": True, "path": "/home/aorus/.hermes", "version": "latest"},
            "wukong": {"found": True, "path": "...", "users": ["user-xxx"]},
            "os": {"type": "wsl", "windows_home": "/mnt/c/Users/Aorus"},
            "python": {"version": "3.12", "venv": "~/.hermes/hermes-agent/venv"},
        }
```
- 检测 OpenClaw (.real / .openclaw)
- 检测 Hermes (~/.hermes)
- 检测 Wukong (dingtalk-rewind-server)
- 检测 WSL/Windows/macOS/Linux
- 检测 Python/Node.js/Bun 版本

#### 2.2 生态系统安装器 `ecosystem_installer.py`
```python
class EcosystemInstaller:
    COMPONENTS = {
        "mempalace": {
            "name": "MemPalace (本地记忆宫殿)",
            "required": False,
            "install": "pip install chromadb && clawshell-eco install mempalace",
            "check": lambda: Path("~/.claude/palace/memories.db").exists(),
            "config": {"db_path": "~/.claude/palace/memories.db"}
        },
        "chromadb": {
            "name": "ChromaDB (向量搜索)",
            "required": True,
            "install": "pip install chromadb",
        },
        "n8n": {
            "name": "N8N (工作流引擎)",
            "required": False,
            "install": "npm install -g n8n",
        },
        "memos_cloud": {
            "name": "MemOS Cloud (云端记忆同步)",
            "required": False,
            "install": "configure API key",
            "config": {"api_key": "${MEMOS_API_KEY}"}
        },
        "watchdog": {
            "name": "Watchdog (文件系统监听)",
            "required": False,
            "install": "pip install watchdog",
        },
        "browser_runtime": {
            "name": "Browser Runtime (CDP浏览器控制)",
            "required": False,
            "install": "npx playwright install chromium",
        },
    }
```
- 交互式选择组件 (checkbox菜单)
- 自动安装依赖
- 配置生成
- 安装后验证

#### 2.3 配置向导 `config_wizard.py`
- 交互式输入: Cloud URL, Edge Token, Node ID
- 自动生成 config.yaml
- 测试云连接
- 保存配置

#### 2.4 安装脚本
- `install.sh` (Linux/macOS/WSL)
- `install.ps1` (Windows PowerShell)
- 自动检测OS并选择正确脚本
- 一键安装: `curl ... | bash`

**交付物**: 
- `curl -fsSL <url>/install.sh | bash` 一键安装
- 自动检测3种环境
- 可选安装6种生态组件
- 安装后自动连接云端

---

### Phase 3: 阿里云 ECS 自动部署 (第3-4周)
**目标**: Terraform 一键创建ECS + 自动部署Cloud服务

#### 3.1 Terraform 配置 `deploy/cloud/terraform/`

```hcl
# main.tf
resource "alicloud_instance" "clawshell" {
  instance_type = "ecs.c6.large"  # 2vCPU/4GB
  image_id      = "ubuntu_22_04_x64_20G_alibase_*.vhd"
  
  system_disk {
    category = "cloud_essd"
    size     = 40
  }
  
  security_groups = [alicloud_security_group.clawshell.id]
  
  user_data = file("${path.module}/user_data.sh")
}

resource "alicloud_security_group" "clawshell" {
  name = "clawshell-sg"
}

resource "alicloud_security_group_rule" "allow_8000" {
  type        = "ingress"
  ip_protocol = "tcp"
  port_range  = "8000/8000"
  cidr_ip     = "0.0.0.0/0"
}
```

#### 3.2 UserData 自动部署脚本
```bash
#!/bin/bash
# ECS 启动后自动执行
apt update && apt install -y docker.io docker-compose
git clone <clawshell2.0-repo> /opt/clawshell
cd /opt/clawshell/deploy/cloud
docker compose up -d
```

#### 3.3 Ansible Playbook (备选方案)
- 适合已有ECS的场景
- 配置管理/更新/回滚

**交付物**:
- `terraform apply` → ECS创建+服务部署
- 输出: ECS公网IP + 访问URL
- 5分钟内从零到可用

---

### Phase 4: 环境适配器 (第4-5周)
**目标**: 端侧无缝适配 OpenClaw/Hermes/Wukong

#### 4.1 OpenClaw/Wukong Adapter
```python
class OpenClawAdapter:
    def integrate(self, real_path: Path):
        # 1. 注册MCP服务器到 Wukong mcpServerConfig.json
        # 2. 配置 EventBus 路径到 ~/.real/eventbus/
        # 3. 添加 clawshell-edge 到 cron_tasks.json
        # 4. 配置双通道通信 (MCP + FileSystem)
        pass
```

#### 4.2 Hermes Adapter
```python
class HermesAdapter:
    def integrate(self, hermes_home: Path):
        # 1. 添加 clawshell-edge skill 到 ~/.hermes/skills/
        # 2. 配置 memory provider 指向 Cloud API
        # 3. 添加 cron job 定时同步
        pass
```

#### 4.3 Standalone Adapter
- 无 OpenClaw/Hermes 时的独立模式
- 仅启动 Edge Client + 选定生态组件

**交付物**:
- 3种环境自动适配
- 适配后无需手动配置
- 验证端到端通信

---

### Phase 5: 文档 + 测试 + 发布 (第5-6周)
**目标**: 完整的用户文档、API文档、部署指南

#### 5.1 文档
- [ ] USER_GUIDE.md — 用户安装使用指南
- [ ] API_REFERENCE.md — Cloud API完整参考
- [ ] ECOSYSTEM.md — 生态系统组件说明
- [ ] DEPLOY_GUIDE.md — 阿里云部署详细步骤
- [ ] TROUBLESHOOTING.md — 常见问题

#### 5.2 测试
- [ ] Cloud API 集成测试
- [ ] Edge Client 单元测试
- [ ] 环境检测器测试 (WSL/Windows/macOS)
- [ ] 生态系统安装器测试
- [ ] 端到端同步测试

#### 5.3 发布
- [ ] GitHub Release
- [ ] PyPI 发布 (clawshell-cloud, clawshell-local)
- [ ] Docker Hub 镜像

---

## 六、关键设计决策

### 6.1 为什么不用 Kubernetes?
> ClawShell 2.0 面向个人/小团队，Docker Compose 足够。
> K8s 留作 v2.1 (多租户/高可用)。

### 6.2 为什么用 Terraform 而不是 ROS?
> Terraform 跨云厂商，后续可迁移到 AWS/GCP。
> ROS (阿里云资源编排) 作为备选。

### 6.3 端侧为什么用 pip install 而不是 Docker?
> 端侧需要访问本地文件系统 (EventBus/Config/Logs)。
> Docker 增加复杂度，WSL环境Docker不可用。

### 6.4 配置文件格式?
> YAML — 人类可读，已有生态 (OpenClaw/Hermes都用YAML)。

### 6.5 认证方案?
> JWT-like token + HMAC签名。
> Phase 1 用预共享密钥，Phase 4 升级到OAuth2。

## 七、风险与缓解

| 风险 | 影响 | 概率 | 缓解 |
|------|------|------|------|
| 阿里云ECS成本超预期 | 用户放弃 | 低 | 提供低配方案 (ecs.c6.large ~¥120/月) |
| WSL环境Docker不可用 | 端侧部署失败 | 中 | 端侧用pip install,不用Docker |
| 网络延迟影响实时同步 | 体验下降 | 中 | WSS+本地缓存, 离线队列 |
| 多端记忆冲突 | 数据不一致 | 中 | LWW策略, 语义去重 |
| 生态组件版本冲突 | 安装失败 | 低 | 固定版本, 虚拟环境隔离 |

## 八、立即开始: Phase 1 任务分解

### 本周可交付 (Phase 1 核心)

| # | 任务 | 文件 | 预计时间 |
|----|------|------|---------|
| 1 | Cloud EventBus Engine | core/eventbus.py | 2h |
| 2 | Cloud TaskMarket Engine | core/task_market.py | 2h |
| 3 | Cloud Swarm Coordinator | core/swarm.py | 2h |
| 4 | Cloud Scheduler | core/scheduler.py | 1.5h |
| 5 | N8N Bridge Service | services/n8n_bridge.py | 1.5h |
| 6 | MemOS Sync Service | services/memos_sync.py | 1h |
| 7 | Skill Repository | services/skill_repo.py | 1h |
| 8 | Docker Compose | docker-compose.yml | 1h |
| 9 | Nginx Config | nginx.conf | 0.5h |
| 10 | Cloud API 集成测试 | tests/test_cloud_api.py | 1.5h |
| 11 | Environment Detector | env_detector.py | 2h |
| 12 | Ecosystem Installer | ecosystem_installer.py | 2h |
| 13 | Configuration Wizard | config_wizard.py | 1.5h |
| 14 | Install Script (Linux) | install.sh | 1.5h |
| 15 | Install Script (Windows) | install.ps1 | 1h |

**Phase 1 总计**: ~22小时 | **可并行执行**: 任务1-7 + 任务11-15 可并行

---

## 九、文件清单 (最终交付物)

```
clawshell2.0/
├── README.md                    (项目总览)
├── ARCHITECTURE.md              (架构全景)
├── IMPLEMENTATION_PLAN.md       (本文档)
├── ClawShell Cloud/             (15 files)
│   ├── src/ (10 files)
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── requirements.txt
│   └── config/config.yaml
├── ClawShell Local/             (14 files)
│   ├── src/ (7 files)
│   ├── scripts/ (4 files)
│   ├── requirements.txt
│   └── config/config.yaml
├── shared/                      (2 files)
├── deploy/                      (8 files)
│   ├── cloud/ (5 files)
│   └── local/ (3 files)
└── docs/                        (5 files)
─────────────────────────────────────
Total: ~44 files
```

---

**计划状态: READY FOR EXECUTION**

是否开始 Phase 1 执行？
