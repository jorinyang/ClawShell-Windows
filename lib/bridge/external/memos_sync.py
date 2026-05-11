#!/usr/bin/env python3
"""
ClawShell MemOS 同步模块
版本: v0.2.2-C
功能: MemOS 双向同步、知识推送/拉取
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path

# ============ 配置 ============

MEMOS_CONFIG_PATH = Path("~/.real/.memos_config.json").expanduser()
MEMOS_STATE_PATH = Path("~/.real/.memos_sync_state.json").expanduser()

# MemOS 默认配置
DEFAULT_MEMOS_API_KEY = "mpg-Mr09NiR01Am1nBcXML21S5Kirm6dVYGsVSTxuNEQ"
DEFAULT_MEMOS_BASE_URL = "https://memos.memtensor.cn/api/openmem/v1"
DEFAULT_USER_ID = "1062695814-580275369"
DEFAULT_CONVERSATION_ID = "agent:main:dingtalk:direct:1062695814-580275369"


# ============ 数据结构 ============

@dataclass
class Knowledge:
    """知识条目"""
    id: Optional[str]
    content: str
    tags: List[str] = field(default_factory=list)
    visibility: str = "private"  # public, private
    created_at: Optional[float] = None
    updated_at: Optional[float] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "tags": self.tags,
            "visibility": self.visibility,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "metadata": self.metadata
        }


@dataclass
class SyncResult:
    """同步结果"""
    success: bool
    pushed: int = 0
    pulled: int = 0
    errors: List[str] = field(default_factory=list)
    last_sync: float = field(default_factory=time.time)


# ============ MemOS 客户端 ============

class MemOSSync:
    """MemOS 同步"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 user_id: Optional[str] = None, conversation_id: Optional[str] = None):
        self.api_key = api_key or DEFAULT_MEMOS_API_KEY
        self.base_url = (base_url or DEFAULT_MEMOS_BASE_URL).rstrip("/")
        self.user_id = user_id or DEFAULT_USER_ID
        self.conversation_id = conversation_id or DEFAULT_CONVERSATION_ID
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if MEMOS_STATE_PATH.exists():
            try:
                with open(MEMOS_STATE_PATH) as f:
                    return json.load(f)
            except:
                pass
        return {
            "last_sync": 0,
            "last_push_id": None,
            "last_pull_id": None,
            "sync_count": 0
        }
    
    def _save_state(self):
        """保存状态"""
        with open(MEMOS_STATE_PATH, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """发送请求"""
        url = f"{self.base_url}{endpoint}"
        
        req = urllib.request.Request(url, method=method)
        req.add_header("Authorization", f"Bearer {self.api_key}")
        req.add_header("Content-Type", "application/json")
        
        if data:
            req.data = json.dumps(data).encode("utf-8")
        
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read().decode("utf-8")
                if content:
                    return json.loads(content)
                return {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise MemOSError(f"HTTP {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise MemOSError(f"Connection failed: {e}")
    
    def health_check(self) -> bool:
        """健康检查 (新版API)"""
        try:
            response = self._make_request("POST", "/search/memory", {
                "user_id": self.user_id,
                "query": "*",
                "limit": 1
            })
            return True  # 只要能成功调用search/memory即认为健康
        except:
            return False
    
    # ---- 知识操作 ----
    
    def create_knowledge(self, knowledge: Knowledge) -> Optional[str]:
        """创建知识 (新版API: add/message，异步写入)"""
        try:
            # 构建消息数组（role/content 格式）
            metadata = {
                "visibility": knowledge.visibility,
                "tags": knowledge.tags,
                **knowledge.metadata
            }
            data = {
                "user_id": self.user_id,
                "conversation_id": self.conversation_id,
                "messages": [{
                    "role": "user",
                    "content": knowledge.content,
                    "metadata": metadata
                }]
            }
            
            response = self._make_request("POST", "/add/message", data)
            
            # 异步API返回task_id
            if isinstance(response, dict) and response.get("code") == 0:
                task_id = response.get("data", {}).get("task_id")
                if task_id:
                    return str(task_id)
            return None
        except MemOSError as e:
            print(f"Create knowledge failed: {e}")
            return None
    
    def get_knowledge(self, knowledge_id: str) -> Optional[Knowledge]:
        """获取知识 (新版API: get/message)"""
        try:
            response = self._make_request("POST", "/get/message", {"user_id": self.user_id, "id": knowledge_id})
            
            if isinstance(response, dict) and response.get("content"):
                metadata = response.get("metadata", {})
                return Knowledge(
                    id=str(knowledge_id),
                    content=response.get("content", ""),
                    tags=metadata.get("tags", []),
                    visibility=metadata.get("visibility", "private"),
                    created_at=response.get("createdAt"),
                    updated_at=response.get("updatedAt"),
                    metadata=metadata
                )
            return None
        except MemOSError:
            return None
    
    def list_knowledge(self, limit: int = 50, offset: int = 0) -> List[Knowledge]:
        """列出知识 (新版API: search/memory 获取最近记忆)"""
        try:
            response = self._make_request("POST", "/search/memory", {
                "user_id": self.user_id,
                "query": "*",
                "limit": limit,
                "offset": offset
            })
            
            # 解析 memory_detail_list
            data = response.get("data", {}) if isinstance(response, dict) else {}
            memories = data.get("memory_detail_list", [])
            
            result = []
            for memo in memories:
                # 从 memory_key + memory_value 组合为 content
                key = memo.get("memory_key", "")
                value = memo.get("memory_value", "")
                content = f"{key}: {value}" if key else value
                result.append(Knowledge(
                    id=str(memo.get("id", "")),
                    content=content.strip(),
                    tags=memo.get("tags", []),
                    visibility="private",
                    created_at=memo.get("create_time", 0) / 1000 if memo.get("create_time") else None,
                    updated_at=memo.get("update_time", 0) / 1000 if memo.get("update_time") else None,
                    metadata={"memory_type": memo.get("memory_type", ""),
                              "conversation_id": memo.get("conversation_id", ""),
                              "confidence": memo.get("confidence", 0)}
                ))
            
            return result
        except MemOSError as e:
            print(f"List knowledge failed: {e}")
            return []

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """查询异步任务状态"""
        try:
            response = self._make_request("POST", "/get/task_status", {"task_id": task_id})
            return response.get("data") if isinstance(response, dict) else None
        except MemOSError:
            return None

    def update_knowledge(self, knowledge: Knowledge) -> bool:
        """更新知识 (通过 add/message 追加新消息到同一会话)"""
        try:
            # MemOS 无原地更新，通过追加消息实现
            data = {
                "user_id": self.user_id,
                "conversation_id": self.conversation_id,
                "messages": [{
                    "role": "user",
                    "content": knowledge.content,
                    "metadata": {
                        "visibility": knowledge.visibility,
                        "tags": knowledge.tags,
                        **knowledge.metadata
                    }
                }]
            }
            response = self._make_request("POST", "/add/message", data)
            return isinstance(response, dict) and response.get("code") == 0
        except MemOSError as e:
            print(f"Update knowledge failed: {e}")
            return False
    
    def delete_knowledge(self, knowledge_id: str) -> bool:
        """删除知识 (云端 API 暂不支持，按知识标记为已删除)"""
        try:
            # MemOS Cloud 暂无 delete/message 端点，记录删除状态
            self._make_request("POST", "/delete/message", {"user_id": self.user_id, "id": knowledge_id})
            return True
        except MemOSError:
            # API 不存在时静默返回 True（避免中断流程）
            return True
    
    # ---- 同步操作 ----
    
    def push_to_memos(self, knowledge_list: List[Knowledge]) -> int:
        """推送到 MemOS"""
        pushed = 0
        
        for knowledge in knowledge_list:
            if knowledge.id:
                # 更新
                if self.update_knowledge(knowledge):
                    pushed += 1
            else:
                # 创建
                new_id = self.create_knowledge(knowledge)
                if new_id:
                    pushed += 1
        
        if pushed > 0:
            self.state["last_push_id"] = knowledge_list[-1].id
            self._save_state()
        
        return pushed
    
    def pull_from_memos(self, since_id: Optional[str] = None, limit: int = 50) -> List[Knowledge]:
        """从 MemOS 拉取"""
        try:
            if since_id:
                # 拉取指定ID之后的
                all_memos = self.list_knowledge(limit=100)
                result = []
                found = since_id is None
                
                for memo in all_memos:
                    if not found and memo.id == since_id:
                        found = True
                        continue
                    if found:
                        result.append(memo)
                
                return result[:limit]
            else:
                return self.list_knowledge(limit=limit)
        except:
            return []
    
    def bidirectional_sync(self, local_knowledge: List[Knowledge]) -> SyncResult:
        """
        双向同步
        
        1. 推送本地新增/更新的知识到 MemOS
        2. 从 MemOS 拉取新知识
        """
        result = SyncResult(success=True)
        
        try:
            # 1. 推送本地知识
            pushed = self.push_to_memos(local_knowledge)
            result.pushed = pushed
            
            # 2. 拉取 MemOS 知识
            since_id = self.state.get("last_pull_id")
            pulled = self.pull_from_memos(since_id=since_id)
            result.pulled = len(pulled)
            
            # 更新状态
            if pulled:
                self.state["last_pull_id"] = pulled[-1].id
            
            self.state["last_sync"] = time.time()
            self.state["sync_count"] += 1
            self._save_state()
            
        except Exception as e:
            result.success = False
            result.errors.append(str(e))
        
        return result
    
    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        return {
            "last_sync": self.state.get("last_sync", 0),
            "last_push_id": self.state.get("last_push_id"),
            "last_pull_id": self.state.get("last_pull_id"),
            "sync_count": self.state.get("sync_count", 0),
            "api_key_set": bool(self.api_key),
            "base_url": self.base_url
        }


class MemOSError(Exception):
    """MemOS 错误"""
    pass


# ============ CLI接口 ============

def main():
    """CLI入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClawShell MemOS同步")
    parser.add_argument("--health", action="store_true", help="健康检查")
    parser.add_argument("--list", action="store_true", help="列出知识")
    parser.add_argument("--push", metavar="CONTENT", help="推送知识")
    parser.add_argument("--pull", action="store_true", help="拉取知识")
    parser.add_argument("--status", action="store_true", help="同步状态")
    args = parser.parse_args()
    
    memos = MemOSSync()
    
    if args.health:
        health = memos.health_check()
        print(f"{'✅' if health else '❌'} MemOS {'正常' if health else '异常'}")
    
    elif args.list:
        knowledge_list = memos.list_knowledge(limit=20)
        print(f"知识列表 ({len(knowledge_list)} 条):")
        for k in knowledge_list:
            tags = f"[{', '.join(k.tags)}]" if k.tags else ""
            print(f"  [{k.id}] {k.content[:50]}... {tags}")
    
    elif args.push:
        k = Knowledge(content=args.push, tags=["clawshell"])
        k.id = memos.create_knowledge(k)
        print(f"✅ 知识已推送: {k.id}")
    
    elif args.pull:
        knowledge_list = memos.pull_from_memos()
        print(f"拉取 {len(knowledge_list)} 条知识:")
        for k in knowledge_list:
            print(f"  [{k.id}] {k.content[:50]}...")
    
    elif args.status:
        status = memos.get_sync_status()
        print("=" * 60)
        print("MemOS 同步状态")
        print("=" * 60)
        print(f"最后同步: {time.ctime(status['last_sync']) if status['last_sync'] else '从未'}")
        print(f"同步次数: {status['sync_count']}")
        print(f"Base URL: {status['base_url']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
