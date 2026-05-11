#!/usr/bin/env python3
"""
qa_context_memory.py - 智能问答上下文记忆
功能：与MemOS集成，实现持久化上下文记忆
"""

import json
import os
import requests
from datetime import datetime
from pathlib import Path

WORKSPACE = os.path.expanduser("~/.real/workspace")
SHARED_DIR = os.path.join(WORKSPACE, "shared")
QA_DIR = os.path.join(SHARED_DIR, "qa")
MEMORY_DIR = os.path.join(QA_DIR, "memory")

# MemOS配置
MEMOS_API_KEY = os.getenv("MEMOS_API_KEY", "mpg-Mr09NiR01Am1nBcXML21S5Kirm6dVYGsVSTxuNEQ")
MEMOS_BASE_URL = os.getenv("MEMOS_BASE_URL", "https://memos.memtensor.cn/api/openmem/v1")

class QAContextMemory:
    """上下文记忆管理器"""
    
    def __init__(self):
        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.memos_enabled = self._check_memos()
        
    def _check_memos(self) -> bool:
        """检查MemOS是否可用 (新版API)"""
        if not MEMOS_API_KEY or MEMOS_API_KEY == "your-memos-api-key":
            return False
        try:
            response = requests.post(
                f"{MEMOS_BASE_URL}/search/memory",
                headers={"Authorization": f"Bearer {MEMOS_API_KEY}", "Content-Type": "application/json"},
                json={"user_id": "default", "query": "test", "limit": 1},
                timeout=5
            )
            return response.status_code in [200, 201]
        except:
            return False
    
    def save_context(self, session_id: str, context: dict, user_id: str = "default") -> bool:
        """保存上下文到本地和MemOS"""
        # 1. 保存到本地
        self._save_local(session_id, context)
        
        # 2. 保存到MemOS
        if self.memos_enabled:
            return self._save_to_memos(session_id, context, user_id)
        return True
    
    def load_context(self, session_id: str) -> dict:
        """加载上下文"""
        # 1. 优先从MemOS加载
        if self.memos_enabled:
            memos_context = self._load_from_memos(session_id)
            if memos_context:
                # 同时更新本地缓存
                self._save_local(session_id, memos_context)
                return memos_context
        
        # 2. 从本地加载
        return self._load_local(session_id)
    
    def update_context(self, session_id: str, new_turn: dict, user_id: str = "default") -> bool:
        """增量更新上下文"""
        # 1. 加载现有上下文
        context = self.load_context(session_id)
        
        # 2. 添加新轮次
        if "turns" not in context:
            context["turns"] = []
        context["turns"].append(new_turn)
        context["last_updated"] = datetime.now().isoformat()
        
        # 3. 保存更新
        return self.save_context(session_id, context, user_id)
    
    def get_recent_memory(self, user_id: str = "default", hours: int = 24) -> list:
        """获取最近N小时的记忆 (新版API: search/memory)"""
        if not self.memos_enabled:
            return []
        
        try:
            from datetime import timedelta
            
            # 使用新版 search/memory API
            response = requests.post(
                f"{MEMOS_BASE_URL}/search/memory",
                headers={"Authorization": f"Bearer {MEMOS_API_KEY}", "Content-Type": "application/json"},
                json={
                    "user_id": "default",
                    "query": "QA conversation question answer",
                    "limit": 50,
                    "filters": {
                        "time_range": {
                            "from": (datetime.now() - timedelta(hours=hours)).isoformat()
                        }
                    }
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                results = response.json()
                memos = results.get("memories", []) if isinstance(results, dict) else results
                return memos
        except Exception as e:
            print(f"加载记忆失败: {e}")
        return []
    
    def search_related_context(self, query: str, user_id: str = "default") -> list:
        """搜索相关上下文 (新版API: search/memory)"""
        if not self.memos_enabled:
            return []
        
        try:
            response = requests.post(
                f"{MEMOS_BASE_URL}/search/memory",
                headers={"Authorization": f"Bearer {MEMOS_API_KEY}", "Content-Type": "application/json"},
                json={
                    "user_id": "default",
                    "query": query,
                    "limit": 10
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                results = response.json()
                return results.get("memories", []) if isinstance(results, dict) else results
        except:
            pass
        return []
    
    def clear_old_contexts(self, days: int = 30) -> int:
        """清理N天前的本地缓存"""
        if not os.path.exists(MEMORY_DIR):
            return 0
        
        cutoff = datetime.now().timestamp() - (days * 86400)
        removed = 0
        
        for filename in os.listdir(MEMORY_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(MEMORY_DIR, filename)
                mtime = os.path.getmtime(filepath)
                if mtime < cutoff:
                    os.remove(filepath)
                    removed += 1
        
        return removed
    
    def _save_local(self, session_id: str, context: dict):
        """保存到本地"""
        filepath = os.path.join(MEMORY_DIR, f"{session_id}.json")
        with open(filepath, 'w') as f:
            json.dump(context, f, ensure_ascii=False, indent=2)
    
    def _load_local(self, session_id: str) -> dict:
        """从本地加载"""
        filepath = os.path.join(MEMORY_DIR, f"{session_id}.json")
        if not os.path.exists(filepath):
            return {"session_id": session_id, "turns": [], "context": {}}
        
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def _save_to_memos(self, session_id: str, context: dict, user_id: str) -> bool:
        """保存到MemOS (新版API: add/message)"""
        try:
            # 构建消息数组
            messages = []
            turns = context.get("turns", [])
            for turn in turns[-10:]:  # 只保存最近10轮
                role = turn.get("role", "user")
                if role not in ["user", "assistant", "system"]:
                    role = "user"
                text = turn.get("content", "")[:500]
                messages.append({"role": role, "content": text})
            
            # 使用新版 add/message API (需要 conversation_id + messages 数组)
            response = requests.post(
                f"{MEMOS_BASE_URL}/add/message",
                headers={
                    "Authorization": f"Bearer {MEMOS_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "user_id": "default",
                    "conversation_id": f"qa_session_{session_id}",
                    "messages": messages,
                    "metadata": {
                        "type": "QA",
                        "session_id": session_id,
                        "tags": ["QA", "conversation", f"session-{session_id}"]
                    }
                },
                timeout=10
            )
            
            return response.status_code in [200, 201]
        except Exception as e:
            print(f"保存到MemOS失败: {e}")
            return False
    
    def _load_from_memos(self, session_id: str) -> dict:
        """从MemOS加载 (新版API: get/message 通过 conversation_id)"""
        try:
            response = requests.post(
                f"{MEMOS_BASE_URL}/get/message",
                headers={"Authorization": f"Bearer {MEMOS_API_KEY}", "Content-Type": "application/json"},
                json={
                    "user_id": "default",
                    "conversation_id": f"qa_session_{session_id}"
                },
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                data = result.get("data", {})
                messages = data.get("message_detail_list", [])
                if messages:
                    # 将消息列表转换为上下文格式
                    return self._parse_message_list(session_id, messages)
        except:
            pass
        return None
    
    def _parse_message_list(self, session_id: str, messages: list) -> dict:
        """将消息列表解析为上下文格式"""
        context = {
            "session_id": session_id,
            "turns": [],
            "context": {}
        }
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # 去除可能的引号包裹
            if content.startswith('"') and content.endswith('"'):
                content = content[1:-1]
            context["turns"].append({
                "role": role,
                "content": content
            })
        
        return context
    
    def _parse_memo_context(self, memo: dict) -> dict:
        """解析Memo为上下文格式"""
        content = memo.get("content", "")
        context = {
            "session_id": "",
            "turns": [],
            "context": {}
        }
        
        # 简单解析
        lines = content.split("\n")
        for line in lines:
            if line.startswith("[QA Session"):
                context["session_id"] = line.split()[2]
            elif line.startswith("- ["):
                # 解析对话轮次
                parts = line[2:].split("]", 1)
                if len(parts) == 2:
                    role = parts[0].strip()
                    content_text = parts[1].strip()
                    context["turns"].append({
                        "role": role,
                        "content": content_text
                    })
        
        return context


if __name__ == "__main__":
    # 测试上下文记忆
    memory = QAContextMemory()
    
    print(f"MemOS可用: {memory.memos_enabled}")
    
    # 测试保存
    test_context = {
        "session_id": "test123",
        "turns": [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么可以帮你的？"},
            {"role": "user", "content": "ClawShell是什么？"},
            {"role": "assistant", "content": "ClawShell是一个增强型外骨骼功能插件..."}
        ],
        "context": {"topic": "ClawShell介绍"}
    }
    
    if memory.save_context("test123", test_context):
        print("✅ 上下文保存成功")
    else:
        print("⚠️ 上下文保存失败（MemOS可能不可用）")
    
    # 测试加载
    loaded = memory.load_context("test123")
    print(f"加载上下文: {len(loaded.get('turns', []))} 轮对话")
    
    print("\n✅ 上下文记忆测试完成")
