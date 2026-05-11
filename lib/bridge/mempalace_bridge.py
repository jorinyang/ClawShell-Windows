#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MemPalace Bridge - ClawShell 记忆增强模块
===========================================
提供持久化记忆存储、语义搜索和上下文增强功能

Author: WuKong AI
Version: 0.1.0
"""

import os
import sys
import sqlite3
import json
import threading
import queue
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# ============================================================
# 配置
# ============================================================

# ClawShell 根目录
CLAWSHELL_ROOT = Path(os.path.expanduser("~")) / ".ClawShell"
STORAGE_DIR = CLAWSHELL_ROOT / "storage" / "mempalace"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# SQLite 数据库路径
DB_PATH = STORAGE_DIR / "memories.db"

# ONNX 模型配置
ONNX_CACHE_DIR = Path(os.path.expanduser("~")) / ".cache" / "chroma" / "onnx_models"
DEFAULT_MODEL = "all-MiniLM-L6-v2"

# ChromaDB 配置
CHROMA_PERSIST_DIR = STORAGE_DIR / "chroma_db"

# ============================================================
# ChromaDB / ONNX 初始化
# ============================================================

_chroma_client = None
_embedding_function = None
_chroma_collection = None
_vector_enabled = False


def _init_onnx_model():
    """初始化 ONNX Runtime Embedding"""
    global _chroma_client, _embedding_function, _chroma_collection, _vector_enabled
    
    try:
        import chromadb
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
        
        # 初始化 ChromaDB 客户端
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
        
        # 初始化 ONNX Embedding（使用 ChromaDB 内置的 ONNXMiniLM_L6_V2）
        _embedding_function = ONNXMiniLM_L6_V2()
        
        # 获取或创建集合
        try:
            _chroma_collection = _chroma_client.get_collection(
                name="memories",
                embedding_function=_embedding_function
            )
        except Exception:
            _chroma_collection = _chroma_client.create_collection(
                name="memories",
                embedding_function=_embedding_function
            )
        
        _vector_enabled = True
        print(f"[MemPalace] ✅ ChromaDB + ONNX 向量存储已激活")
        print(f"           模型: {DEFAULT_MODEL}")
        print(f"           记忆数量: {_chroma_collection.count()}")
        
    except ImportError as e:
        print(f"[MemPalace] ⚠️ ChromaDB 未安装，向量搜索不可用")
        print(f"           安装命令: pip install chromadb")
        _vector_enabled = False
    except Exception as e:
        print(f"[MemPalace] ⚠️ ONNX 模型初始化失败: {e}")
        _vector_enabled = False


def _ensure_db():
    """确保数据库表存在"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_key TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            metadata TEXT DEFAULT '{}'
        )
    """)
    conn.commit()
    conn.close()


# ============================================================
# MemPalaceBridge 核心类
# ============================================================

class MemPalaceBridge:
    """记忆宫殿桥接器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._db_lock = threading.Lock()
        self._db_queue = queue.Queue()
        self._async_worker_running = True
        
        # 初始化数据库
        _ensure_db()
        
        # 初始化 ONNX/ChromaDB（后台进行）
        _init_onnx_model()
        
        # 启动异步工作线程
        self._async_thread = threading.Thread(target=self._async_worker, daemon=True)
        self._async_thread.start()
        
        print(f"[MemPalace] ✅ 记忆宫殿初始化完成")
        print(f"           数据库: {DB_PATH}")
    
    def _async_worker(self):
        """异步数据库工作线程"""
        while self._async_worker_running:
            try:
                task = self._db_queue.get(timeout=1.0)
                if task is None:
                    break
                func, args, result_evt = task
                try:
                    result = func(*args)
                    if result_evt:
                        result_evt.put(result)
                except Exception as e:
                    if result_evt:
                        result_evt.put(e)
            except queue.Empty:
                continue
    
    def _sync_execute(self, func, *args):
        """同步执行数据库操作（带超时）"""
        result_evt = queue.Queue(maxsize=1)
        self._db_queue.put((func, args, result_evt))
        try:
            return result_evt.get(timeout=5.0)
        except queue.Empty:
            return None
    
    # --------------------------------------------------------
    # 记忆写入
    # --------------------------------------------------------
    
    def write(self, memory_key: str, content: str, tags: List[str] = None) -> bool:
        """
        写入记忆
        
        Args:
            memory_key: 记忆键名（唯一标识）
            content: 记忆内容
            tags: 标签列表
        
        Returns:
            bool: 是否成功
        """
        tags = tags or []
        now = datetime.now().isoformat()
        
        def _db_write():
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO memories 
                (memory_key, content, tags, created_at, updated_at)
                VALUES (?, ?, ?, 
                    COALESCE((SELECT created_at FROM memories WHERE memory_key = ?), ?),
                    ?)
            """, (memory_key, content, json.dumps(tags), memory_key, now, now))
            conn.commit()
            conn.close()
            return True
        
        # SQLite 写入
        result = self._sync_execute(_db_write)
        
        # ChromaDB 向量存储
        if _vector_enabled and _chroma_collection:
            try:
                _chroma_collection.upsert(
                    documents=[content],
                    ids=[memory_key],
                    metadatas=[{"tags": json.dumps(tags), "key": memory_key}]
                )
            except Exception as e:
                print(f"[MemPalace] ⚠️ 向量存储失败: {e}")
        
        return result is True
    
    # --------------------------------------------------------
    # 记忆搜索
    # --------------------------------------------------------
    
    def search(self, query: str, mode: str = "keyword", limit: int = 10) -> List[Dict]:
        """
        搜索记忆
        
        Args:
            query: 搜索查询
            mode: 搜索模式 - "keyword"(关键词) / "semantic"(语义) / "hybrid"(混合)
            limit: 返回数量限制
        
        Returns:
            List[Dict]: 记忆列表
        """
        if mode == "semantic" and _vector_enabled and _chroma_collection:
            # 语义搜索
            try:
                results = _chroma_collection.query(
                    query_texts=[query],
                    n_results=limit
                )
                memories = []
                for i, doc_id in enumerate(results.get("ids", [[]])[0]):
                    memories.append({
                        "key": doc_id,
                        "content": results.get("documents", [[]])[0][i],
                        "distance": results.get("distances", [[]])[0][i],
                        "metadata": results.get("metadatas", [[{}]])[0][i]
                    })
                return memories
            except Exception as e:
                print(f"[MemPalace] ⚠️ 语义搜索失败，回退到关键词: {e}")
        
        # 关键词搜索
        def _db_search():
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM memories 
                WHERE content LIKE ? OR memory_key LIKE ?
                ORDER BY updated_at DESC LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        
        return self._sync_execute(_db_search) or []
    
    # --------------------------------------------------------
    # 记忆读取
    # --------------------------------------------------------
    
    def recall(self, memory_key: str) -> Optional[Dict]:
        """
        读取单条记忆
        
        Args:
            memory_key: 记忆键名
        
        Returns:
            Optional[Dict]: 记忆内容或 None
        """
        def _db_recall():
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories WHERE memory_key = ?", (memory_key,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        
        return self._sync_execute(_db_recall)
    
    # --------------------------------------------------------
    # 记忆列表
    # --------------------------------------------------------
    
    def list_memories(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        列出记忆
        
        Args:
            limit: 数量限制
            offset: 偏移量
        
        Returns:
            List[Dict]: 记忆列表
        """
        def _db_list():
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT memory_key, content, tags, created_at, updated_at
                FROM memories ORDER BY updated_at DESC LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        
        return self._sync_execute(_db_list) or []
    
    # --------------------------------------------------------
    # 记忆删除
    # --------------------------------------------------------
    
    def delete(self, memory_key: str) -> bool:
        """
        删除记忆
        
        Args:
            memory_key: 记忆键名
        
        Returns:
            bool: 是否成功
        """
        def _db_delete():
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE memory_key = ?", (memory_key,))
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return affected > 0
        
        result = self._sync_execute(_db_delete)
        
        # ChromaDB 删除
        if _vector_enabled and _chroma_collection:
            try:
                _chroma_collection.delete(ids=[memory_key])
            except Exception:
                pass
        
        return result is True
    
    # --------------------------------------------------------
    # 统计信息
    # --------------------------------------------------------
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        def _db_stats():
            conn = sqlite3.connect(str(DB_PATH))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memories")
            total = cursor.fetchone()[0]
            conn.close()
            return total
        
        total = self._sync_execute(_db_stats) or 0
        
        return {
            "total_memories": total,
            "db_path": str(DB_PATH),
            "chroma_enabled": _vector_enabled,
            "vector_enabled": _vector_enabled,
            "onnx_model": DEFAULT_MODEL if _vector_enabled else None,
            "chroma_collection_count": _chroma_collection.count() if _vector_enabled and _chroma_collection else 0
        }
    
    def __del__(self):
        self._async_worker_running = False
        self._db_queue.put(None)


# ============================================================
# 全局实例（延迟初始化）
# ============================================================

_bridge_instance = None


def get_bridge() -> MemPalaceBridge:
    """获取全局 Bridge 实例"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MemPalaceBridge()
    return _bridge_instance


# ============================================================
# 便捷函数
# ============================================================

def write_memory(key: str, content: str, tags: List[str] = None) -> bool:
    """写入记忆"""
    return get_bridge().write(key, content, tags)


def search_memory(query: str, mode: str = "keyword", limit: int = 10) -> List[Dict]:
    """搜索记忆"""
    return get_bridge().search(query, mode, limit)


def recall_memory(key: str) -> Optional[Dict]:
    """读取记忆"""
    return get_bridge().recall(key)


def list_memories(limit: int = 50, offset: int = 0) -> List[Dict]:
    """列出记忆"""
    return get_bridge().list_memories(limit, offset)


def get_memory_stats() -> Dict[str, Any]:
    """获取统计"""
    return get_bridge().get_stats()


def delete_memory(key: str) -> bool:
    """删除记忆"""
    return get_bridge().delete(key)


if __name__ == "__main__":
    # 测试代码
    print("=" * 50)
    print("MemPalace Bridge 测试")
    print("=" * 50)
    
    bridge = get_bridge()
    stats = bridge.get_stats()
    
    print(f"\n📊 统计信息:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    # 写入测试
    print(f"\n✍️ 写入测试...")
    bridge.write("test_key", "这是一条测试记忆", ["测试", "示例"])
    
    # 读取测试
    print(f"\n📖 读取测试...")
    mem = bridge.recall("test_key")
    if mem:
        print(f"  ✅ 读取成功: {mem['memory_key']}")
    
    # 搜索测试
    print(f"\n🔍 搜索测试...")
    results = bridge.search("测试")
    print(f"  找到 {len(results)} 条记忆")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)
