# Hermes-MemPalace 记忆互通集成说明

## 状态: ✅ 已完成

Hermes 与悟空现已通过 MemPalace 实现记忆互通，共享同一 SQLite + ChromaDB 向量数据库。

---

## 数据库位置

| 平台 | 路径 | 说明 |
|------|------|------|
| Windows (悟空) | `C:\Users\Aorus\.claude\palace\memories.db` | 原生路径 |
| WSL (Hermes) | `/mnt/c/Users/Aorus/.claude/palace/memories.db` | WSL 挂载映射 |
| ChromaDB 向量库 | 内存中（由 `chromadb.Client()` 管理） | 启动时加载 |
| ONNX 模型 | `C:\Users\Aorus\.cache\chroma\onnx_models\all-MiniLM-L6-v2\` | 384维嵌入 |

---

## 核心文件

| 文件 | 路径 | 说明 |
|------|------|------|
| MemPalace MCP | `lib/bridge/mempalace_mcp.py` | 悟空原生，提供工具接口 |
| MemPalace Bridge | `lib/bridge/persistence/mempalace_bridge.py` | 悟空原生，SQLite 持久化 |
| **Hermes Bridge** | `lib/bridge/hermes_mempalace_bridge.py` | **新增**，Hermes 专用封装 |

---

## Hermes 使用方式

### 方式1: 直接调用桥接模块

```python
import sys
sys.path.insert(0, '/mnt/c/Users/Aorus/.ClawShell')
sys.path.insert(0, '/mnt/c/Users/Aorus/.ClawShell/lib')

from lib.bridge.hermes_mempalace_bridge import HermesMemPalaceBridge

bridge = HermesMemPalaceBridge()

# 保存任务洞察
bridge.save_insight(
    task_id="task_001",
    insight="发现的解决方案或模式...",
    category="success_pattern"  # 或 error_pattern, tool_usage, domain_knowledge
)

# 语义检索相关历史
results = bridge.recall_context("当前问题描述", limit=5)

# 获取相关知识（带相似度过滤）
knowledge = bridge.get_relevant_knowledge("任务描述", min_relevance=0.6)
```

### 方式2: 便捷函数

```python
from lib.bridge.hermes_mempalace_bridge import save_insight, recall_context, health_check

# 直接保存
save_insight("task_002", "重要发现...", category="error_pattern")

# 直接搜索
results = recall_context("Python 异常处理", limit=3)
```

---

## 记忆分类体系

| 分类标签 | 用途 | 示例 |
|----------|------|------|
| `success_pattern` | 成功经验沉淀 | "WSL 路径修复方案" |
| `error_pattern` | 错误模式识别 | "chromadb 导入失败原因" |
| `tool_usage` | 工具使用技巧 | "pip venv 安装方法" |
| `domain_knowledge` | 领域知识 | "MCP 协议工作原理" |
| `skill_evolution` | 技能进化记录 | "桥接模块 v2 改进" |

---

## API 参考

### HermesMemPalaceBridge 方法

| 方法 | 参数 | 返回 |
|------|------|------|
| `save_insight(task_id, insight, category, metadata)` | 任务ID, 洞察内容, 分类, 元数据 | 写入结果 |
| `recall_context(query, limit, mode)` | 查询文本, 数量, semantic/keyword | 记忆列表 |
| `get_task_history(task_id)` | 任务ID | 记忆内容或 None |
| `list_recent_insights(category, limit)` | 分类(可选), 数量 | 洞察列表 |
| `get_relevant_knowledge(task_desc, min_relevance)` | 任务描述, 最小相似度 | 过滤后的知识 |
| `find_similar_errors(error_msg, limit)` | 错误信息, 数量 | 相似错误记录 |
| `save_skill_evolution(skill, notes, version)` | 技能名, 进化笔记, 版本 | 写入结果 |
| `health_check()` | - | 健康状态字典 |
| `delete_memory(key)` | 记忆键名 | 删除结果 |

---

## 故障排除

### 问题: 向量搜索不可用

1. 检查 ONNX 模型是否存在:
   ```bash
   ls /mnt/c/Users/Aorus/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx/model.onnx
   ```

2. 检查 ChromaDB 版本:
   ```bash
   /home/aorus/.hermes/hermes-agent/venv/bin/python3 -c "import chromadb; print(chromadb.__version__)"
   ```

### 问题: 数据库路径错误

确保 `mempalace_bridge.py` 中的路径指向:
```python
windows_palace = Path("/mnt/c/Users/Aorus/.claude/palace")
```

### 问题: 悟空看不到 Hermes 写入的记忆

检查 Windows 文件权限:
```bash
ls -la /mnt/c/Users/Aorus/.claude/palace/memories.db
```

---

## 相关资源

- **MemPalace 文档**: https://github.com/mempalace/mempalace
- **ChromaDB 文档**: https://docs.trychroma.com/
- **悟空优化版文档**: https://github.com/jorinyang/wukong-optimized-ClawShell/tree/main/docs/mempalace-installation

---

*集成完成时间: 2026-05-02*
*维护者: Hermes Agent + 悟空(WuKong)*
