"""
Hermes-MemPalace Bridge - Hermes 记忆互通桥接模块
====================================================

提供 Hermes 与悟空之间的共享记忆接口，基于 MemPalace 实现：
- 语义搜索（向量相似度）
- 关键词搜索（SQLite LIKE）
- 记忆写入/读取/删除
- 跨会话记忆持久化

位置: /mnt/c/Users/Aorus/.ClawShell/lib/bridge/hermes_mempalace_bridge.py
"""

import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# 确保路径正确
CLAWSHELL_ROOT = Path(__file__).parent.parent.parent
if str(CLAWSHELL_ROOT) not in sys.path:
    sys.path.insert(0, str(CLAWSHELL_ROOT))
if str(CLAWSHELL_ROOT / "lib") not in sys.path:
    sys.path.insert(0, str(CLAWSHELL_ROOT / "lib"))

from lib.bridge.mempalace_mcp import MemPalaceMCPTools

logger = logging.getLogger("HermesMemPalace")


class HermesMemPalaceBridge:
    """
    Hermes 专用记忆互通桥接器
    
    职责:
    1. 沉淀任务洞察到共享记忆库
    2. 检索悟空历史上下文
    3. 支持语义搜索获取相关经验
    4. 记忆版本管理与溯源
    """
    
    def __init__(self, mempalace_path: str = None):
        # MemPalace 数据库路径 (支持环境变量覆盖)
        if mempalace_path is None:
            mempalace_path = os.environ.get(
                "MEMPALACE_PATH",
                str(Path.home() / ".claude" / "palace")
            )
        self.mempalace_path = Path(mempalace_path)
        if not self.mempalace_path.exists():
            self.mempalace_path.mkdir(parents=True, exist_ok=True)
        self.tools = MemPalaceMCPTools()
        self.stats = self.tools._stats({})
        logger.info(f"[HermesMemPalace] Bridge ready: db={self.mempalace_path}/memories.db, "
                     f"vector={self.stats.get('vector_search_available')}, "
                     f"memories={self.stats.get('total_memories', 0)}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # 核心接口
    # ─────────────────────────────────────────────────────────────────────────
    
    def save_insight(self, task_id: str, insight: str, 
                     category: str = "general",
                     metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        保存任务洞察到共享记忆库
        
        Args:
            task_id: 任务标识符
            insight: 洞察内容（建议 200-500 字）
            category: 分类标签 (error_pattern, success_pattern, tool_usage, domain_knowledge)
            metadata: 附加元数据
        """
        key = f"insight_{category}_{task_id}_{int(time.time())}"
        enriched_content = f"[{category}] {insight}\n\nTask: {task_id}"
        
        merged_metadata = {
            "source": "hermes",
            "type": "insight",
            "category": category,
            "task_id": task_id,
            "created_at": time.time(),
            **(metadata or {})
        }
        
        return self.tools._write({
            "content": enriched_content,
            "key": key,
            "metadata": merged_metadata,
            "enable_vector": True
        })
    
    def recall_context(self, query: str, limit: int = 5,
                       mode: str = "semantic") -> List[Dict[str, Any]]:
        """
        语义检索相关历史上下文
        
        Args:
            query: 查询文本（当前任务描述或问题）
            limit: 返回结果数量
            mode: "semantic" 或 "keyword"
        """
        result = self.tools._search({
            "query": query,
            "limit": limit,
            "mode": mode
        })
        return result.get("results", [])
    
    def get_task_history(self, task_id: str) -> Optional[str]:
        """精确获取指定任务的历史记录"""
        # 尝试多种键名格式
        for prefix in ["insight_", "task_", "session_"]:
            result = self.tools._recall({"key": f"{prefix}{task_id}"})
            if result.get("found"):
                return result.get("content")
        return None
    
    def list_recent_insights(self, category: Optional[str] = None,
                             limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近的洞察记忆"""
        all_memories = self.tools._list({"limit": limit * 2})  # 多取一些用于过滤
        memories = all_memories.get("memories", [])
        
        if category:
            memories = [m for m in memories if f"[{category}]" in m.get("content", "")]
        
        # 只返回 Hermes 生成的洞察
        hermes_memories = []
        for m in memories:
            # 这里简化处理，实际可通过 metadata 过滤
            if m.get("key", "").startswith("insight_"):
                hermes_memories.append(m)
        
        return hermes_memories[:limit]
    
    def delete_memory(self, key: str) -> Dict[str, Any]:
        """删除指定记忆"""
        return self.tools._delete({"key": key})
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.tools._stats({})
        return {
            "status": "healthy" if stats.get("bridge_available") else "degraded",
            "vector_search": stats.get("vector_search_available", False),
            "total_memories": stats.get("total_memories", 0),
            "db_path": str(stats.get("palace_dir", "unknown"))
        }
    
    # ─────────────────────────────────────────────────────────────────────────
    # 高级接口: 模式识别与知识沉淀
    # ─────────────────────────────────────────────────────────────────────────
    
    def find_similar_errors(self, error_message: str, limit: int = 3) -> List[Dict[str, Any]]:
        """查找相似历史错误及解决方案"""
        results = self.recall_context(
            query=f"error: {error_message}",
            limit=limit,
            mode="semantic"
        )
        # 过滤出 error_pattern 类别的记忆
        return [r for r in results if "error" in r.get("metadata", {}).get("category", "")]
    
    def save_skill_evolution(self, skill_name: str, 
                             evolution_notes: str,
                             version: str = "1.0") -> Dict[str, Any]:
        """保存技能进化记录"""
        key = f"skill_{skill_name}_v{version}_{int(time.time())}"
        content = f"[skill_evolution] {skill_name} v{version}\n\n{evolution_notes}"
        
        return self.tools._write({
            "content": content,
            "key": key,
            "metadata": {
                "source": "hermes",
                "type": "skill_evolution",
                "skill_name": skill_name,
                "version": version,
                "created_at": time.time()
            },
            "enable_vector": True
        })
    
    def get_relevant_knowledge(self, task_description: str,
                                min_relevance: float = 0.7) -> List[Dict[str, Any]]:
        """
        获取与当前任务相关的知识（基于语义相似度过滤）
        
        Args:
            task_description: 当前任务描述
            min_relevance: 最小相似度阈值 (0-1, 越小越宽松)
        """
        results = self.recall_context(task_description, limit=10, mode="semantic")
        
        # 过滤低相关性结果（distance 越小越相似，ChromaDB 使用 cosine distance）
        filtered = []
        for r in results:
            distance = r.get("distance", 1.0)
            # cosine distance 范围 0-2，转换为相似度分数
            similarity = 1 - (distance / 2)
            if similarity >= min_relevance:
                r["similarity_score"] = round(similarity, 3)
                filtered.append(r)
        
        return filtered


# ─────────────────────────────────────────────────────────────────────────────
# 便捷函数（模块级接口）
# ─────────────────────────────────────────────────────────────────────────────

_bridge_instance: Optional[HermesMemPalaceBridge] = None

def get_bridge() -> HermesMemPalaceBridge:
    """获取桥接单例"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = HermesMemPalaceBridge()
    return _bridge_instance


def save_insight(task_id: str, insight: str, category: str = "general",
                 metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """便捷函数: 保存洞察"""
    return get_bridge().save_insight(task_id, insight, category, metadata)


def recall_context(query: str, limit: int = 5, mode: str = "semantic") -> List[Dict[str, Any]]:
    """便捷函数: 检索上下文"""
    return get_bridge().recall_context(query, limit, mode)


def health_check() -> Dict[str, Any]:
    """便捷函数: 健康检查"""
    return get_bridge().health_check()


# ─────────────────────────────────────────────────────────────────────────────
# 测试入口
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Hermes-MemPalace Bridge Test ===\n")
    
    bridge = HermesMemPalaceBridge()
    
    # 健康检查
    health = bridge.health_check()
    print(f"Health: {json.dumps(health, indent=2, ensure_ascii=False)}\n")
    
    # 保存测试洞察
    result = bridge.save_insight(
        task_id="test_001",
        insight="在 WSL 环境中，Hermes 运行在独立的 Python venv 中，需要单独安装 chromadb 和 mempalace 包。",
        category="tool_usage",
        metadata={"env": "wsl", "python_version": "3.11"}
    )
    print(f"Save result: {json.dumps(result, indent=2, ensure_ascii=False)}\n")
    
    # 语义搜索
    results = bridge.recall_context("WSL Python venv chromadb", limit=3)
    print(f"Search results ({len(results)}):")
    for r in results:
        print(f"  - [{r.get('id')}] score={r.get('distance', 0):.3f}: {r.get('content', '')[:80]}...")
    
    print("\n=== Test Complete ===")
