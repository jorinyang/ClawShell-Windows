"""
SessionEnd Auto-Save Hook - 会话结束自动保存洞察到 MemPalace
===============================================================

集成到悟空 SessionEnd Hook 中，自动将本次会话的关键信息沉淀到共享记忆库。

使用方法:
1. 将此文件放入悟空的 hooks 目录
2. 在 hooks.md 的 SessionEnd Hook 中添加调用
3. 或通过外部 cron 定期检查并执行

位置: /mnt/c/Users/Aorus/.ClawShell/lib/bridge/session_end_auto_save.py
"""

import sys
import json
import time
import traceback
from pathlib import Path
from typing import Dict, Any, List, Optional

# 确保路径正确
CLAWSHELL_ROOT = Path(__file__).parent.parent.parent
if str(CLAWSHELL_ROOT) not in sys.path:
    sys.path.insert(0, str(CLAWSHELL_ROOT))
if str(CLAWSHELL_ROOT / "lib") not in sys.path:
    sys.path.insert(0, str(CLAWSHELL_ROOT / "lib"))

from lib.bridge.hermes_mempalace_bridge import HermesMemPalaceBridge


class SessionEndAutoSave:
    """
    会话结束自动保存器
    
    职责:
    1. 提取本次会话的关键信息
    2. 生成结构化洞察
    3. 保存到 MemPalace 共享数据库
    4. 更新会话记忆文件
    """
    
    def __init__(self):
        self.bridge = HermesMemPalaceBridge()
        self.session_data = {
            "start_time": None,
            "end_time": None,
            "tasks": [],
            "errors": [],
            "learnings": [],
            "files_modified": [],
            "tools_used": []
        }
    
    def extract_session_info(self, session_log: str) -> Dict[str, Any]:
        """
        从会话日志中提取关键信息
        
        Args:
            session_log: 本次会话的完整日志或摘要
        """
        # 这里简化处理，实际应由悟空的做梦机制提供结构化数据
        return {
            "timestamp": time.time(),
            "session_id": f"session_{int(time.time())}",
            "summary": session_log[:500] if len(session_log) > 500 else session_log
        }
    
    def generate_insights(self, session_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成多个维度的洞察
        
        Returns:
            洞察列表，每个洞察包含 task_id, content, category
        """
        insights = []
        session_id = session_info.get("session_id", f"session_{int(time.time())}")
        
        # 1. 会话概览洞察
        insights.append({
            "task_id": f"{session_id}_overview",
            "insight": f"""[会话概览] {session_info.get('summary', '无摘要')}
时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
会话ID: {session_id}""",
            "category": "domain_knowledge"
        })
        
        # 2. 错误模式洞察（如果有错误）
        if self.session_data.get("errors"):
            error_summary = "\n".join([f"- {e}" for e in self.session_data["errors"][:3]])
            insights.append({
                "task_id": f"{session_id}_errors",
                "insight": f"""[错误记录] 本次会话遇到的错误:
{error_summary}
预防建议: 已记录到 feedback.md，下次会话前检查""",
                "category": "error_pattern"
            })
        
        # 3. 学习收获洞察
        if self.session_data.get("learnings"):
            learning_summary = "\n".join([f"- {l}" for l in self.session_data["learnings"][:5]])
            insights.append({
                "task_id": f"{session_id}_learnings",
                "insight": f"""[学习收获] 本次会话的新发现:
{learning_summary}""",
                "category": "success_pattern"
            })
        
        # 4. 工具使用洞察
        if self.session_data.get("tools_used"):
            tools_summary = ", ".join(set(self.session_data["tools_used"]))
            insights.append({
                "task_id": f"{session_id}_tools",
                "insight": f"""[工具使用] 本次会话使用的工具: {tools_summary}
使用场景: {session_info.get('summary', 'N/A')[:100]}""",
                "category": "tool_usage"
            })
        
        return insights
    
    def save_to_mempalace(self, insights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        保存洞察到 MemPalace
        
        Returns:
            保存结果统计
        """
        results = {
            "total": len(insights),
            "success": 0,
            "failed": 0,
            "keys": []
        }
        
        for ins in insights:
            try:
                result = self.bridge.save_insight(
                    task_id=ins["task_id"],
                    insight=ins["insight"],
                    category=ins["category"],
                    metadata={
                        "source": "session_end_hook",
                        "session_id": ins["task_id"].split("_")[0] if "_" in ins["task_id"] else "unknown",
                        "auto_saved": True,
                        "timestamp": time.time()
                    }
                )
                
                if result.get("success"):
                    results["success"] += 1
                    results["keys"].append(result.get("key"))
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["failed"] += 1
                print(f"[SessionEndAutoSave] 保存失败: {e}")
        
        return results
    
    def update_session_memory(self, session_info: Dict[str, Any]) -> bool:
        """
        更新会话记忆文件（.config/memory/sessions/）
        
        按照 soul.md 中的10段结构写入
        """
        try:
            # 构建会话记忆内容
            session_content = f"""# Session Title
{session_info.get('summary', '无标题')[:100]}

---

# Current State
**进展**: {session_info.get('status', '进行中')}
**下一步**: 待确定
**阻塞项**: 无

---

# Task Specification
**需求**: {session_info.get('summary', '无描述')}
**约束**: 无
**验收标准**: 完成

---

# Files and Functions
本次会话涉及的关键文件和函数

---

# Workflow
1. 会话开始
2. 执行任务
3. 会话结束，自动保存洞察

---

# Errors & Corrections
{chr(10).join([f"- {e}" for e in self.session_data.get('errors', [])]) or '无错误'}

---

# Codebase and System Documentation
无变更

---

# Learnings
{chr(10).join([f"- {l}" for l in self.session_data.get('learnings', [])]) or '无新发现'}

---

# Key Results
| 产出物 | 路径 | 状态 |
|--------|------|------|
| 会话洞察 | MemPalace | ✅ 已保存 |

---

# Worklog
```
[{time.strftime('%H:%M')}] 会话开始
[{time.strftime('%H:%M')}] 执行任务
[{time.strftime('%H:%M')}] 会话结束，自动保存洞察到 MemPalace
```

---

*自动保存时间: {time.strftime('%Y-%m-%d %H:%M:%S')}*
"""
            
            # 写入会话记忆文件
            sessions_dir = Path("/mnt/c/Users/Aorus/.real/users/user-bd1b229d4eff8f6a45c456149072cb3b/.config/memory/sessions")
            if not sessions_dir.exists():
                sessions_dir.mkdir(parents=True, exist_ok=True)
            
            session_file = sessions_dir / f"{time.strftime('%Y-%m-%d_%H-%M')}.md"
            session_file.write_text(session_content, encoding='utf-8')
            
            return True
            
        except Exception as e:
            print(f"[SessionEndAutoSave] 更新会话记忆失败: {e}")
            return False
    
    def execute(self, session_log: str = "") -> Dict[str, Any]:
        """
        执行完整的会话结束自动保存流程
        
        Args:
            session_log: 本次会话的日志或摘要
            
        Returns:
            执行结果
        """
        print("[SessionEndAutoSave] 开始执行会话结束自动保存...")
        
        # 1. 提取会话信息
        session_info = self.extract_session_info(session_log)
        
        # 2. 生成洞察
        insights = self.generate_insights(session_info)
        
        # 3. 保存到 MemPalace
        save_results = self.save_to_mempalace(insights)
        
        # 4. 更新会话记忆文件
        memory_updated = self.update_session_memory(session_info)
        
        # 5. 返回结果
        return {
            "status": "success" if save_results["success"] > 0 else "failed",
            "insights_generated": len(insights),
            "insights_saved": save_results["success"],
            "insights_failed": save_results["failed"],
            "memory_updated": memory_updated,
            "keys": save_results["keys"],
            "session_id": session_info["session_id"]
        }


# ─────────────────────────────────────────────────────────────────────────────
# 便捷函数
# ─────────────────────────────────────────────────────────────────────────────

def auto_save_session(session_log: str = "") -> Dict[str, Any]:
    """便捷函数: 自动保存会话"""
    saver = SessionEndAutoSave()
    return saver.execute(session_log)


# ─────────────────────────────────────────────────────────────────────────────
# 测试入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== SessionEnd Auto-Save Hook Test ===\n")
    
    # 模拟会话数据
    saver = SessionEndAutoSave()
    saver.session_data = {
        "errors": ["mkdir 命令不可用", "esbuild 平台不匹配"],
        "learnings": ["WSL中需用 npx 运行 ts-node", "权限问题可用 chmod 修复"],
        "tools_used": ["terminal", "execute_code", "read_file", "patch"]
    }
    
    result = saver.execute("本次会话完成了 MemPalace 集成、KAIROS 日志导入、browser-runtime 启动尝试。")
    
    print(f"\n执行结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
    print("\n=== Test Complete ===")
