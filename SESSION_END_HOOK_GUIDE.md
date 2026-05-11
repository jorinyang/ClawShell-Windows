# SessionEnd Auto-Save Hook 集成指南

## 概述

本文档说明如何将 Hermes 的 `session_end_auto_save.py` 集成到悟空的 SessionEnd Hook 中，实现会话结束时的自动洞察保存。

## 集成方式

### 方式一：直接修改 hooks.md（推荐）

在 `hooks.md` 的 SessionEnd Hook 中，Turn 2 并行写入阶段添加 Hermes 调用：

```markdown
### SessionEnd Hook
**触发时机**：每次会话正常结束时

**执行动作（做梦机制）：**

**Turn 1：并行读取**
- 读取所有四类记忆文件（user/feedback/project/reference）
- 读取当前会话的完整对话摘要

**分析提炼：**
- 识别本次会话的新知识、新偏好、新错误
- 与现有记忆对比，识别冲突和更新点
- 生成会话记忆10段结构草稿

**Turn 2：并行写入**
- 更新 `memory/user.md`（如有新偏好）
- 更新 `memory/feedback.md`（记录本次纠正）
- 更新 `memory/project.md`（更新进度和决策）
- 更新 `memory/reference.md`（标记过时项）
- 写入 `memory/sessions/YYYY-MM-DD_HH-MM.md`（完整会话记忆）
- **调用 Hermes save_insight**（新增）
  ```bash
  python3 /mnt/c/Users/Aorus/.ClawShell/lib/bridge/session_end_auto_save.py
  ```
```

### 方式二：通过 ClawShell EventBus 触发

在悟空的 `wukong_clawshell_integration.py` 中添加事件监听：

```python
# 在事件处理器中添加
elif event_type == "session.end":
    # 触发 Hermes 自动保存
    subprocess.run([
        sys.executable,
        "/mnt/c/Users/Aorus/.ClawShell/lib/bridge/session_end_auto_save.py"
    ])
```

### 方式三：HTTP API 调用

通过 browser-runtime 的 HTTP API 触发：

```bash
curl -X POST http://127.0.0.1:4240/api/agent/act \
  -H "Content-Type: application/json" \
  -d '{
    "action": "save_insight",
    "session_summary": "本次会话...",
    "errors": [],
    "learnings": []
  }'
```

## 验证方法

1. 检查 MemPalace 数据库是否新增记录：
   ```python
   from hermes_mempalace_bridge import HermesMemPalaceBridge
   bridge = HermesMemPalaceBridge()
   health = bridge.health_check()
   print(f"总记忆数: {health['total_memories']}")
   ```

2. 检查会话记忆文件是否生成：
   ```bash
   ls -la ~/.real/users/.../.config/memory/sessions/
   ```

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| Hook 未触发 | SessionEnd 未被调用 | 检查 IDE/ClawShell 是否正确发送 session.end 事件 |
| 保存失败 | chromadb 未安装 | 确保 Hermes venv 中已安装 chromadb |
| 数据库锁定 | 悟空和 Hermes 同时写入 | 使用 WAL 模式，已自动处理 |
| 向量搜索失败 | ONNX 模型缺失 | 检查 C:\Users\Aorus\.cache\chroma\onnx_models |

## 文件位置

- Hook 模块：`/mnt/c/Users/Aorus/.ClawShell/lib/bridge/session_end_auto_save.py`
- 桥接模块：`/mnt/c/Users/Aorus/.ClawShell/lib/bridge/hermes_mempalace_bridge.py`
- 共享数据库：`C:\Users\Aorus\.claude\palace\memories.db`

## 更新记录

| 日期 | 内容 | 操作人 |
|------|------|--------|
| 2026-05-02 | 创建 SessionEnd Auto-Save Hook | Hermes |
| 2026-05-02 | 集成到 MemPalace 共享数据库 | Hermes |
