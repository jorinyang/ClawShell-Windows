#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UnifiedMemoryBridge - 统一记忆桥
================================
整合 MemOS Cloud 和 MemPalace 的统一记忆接口。
MemOS Cloud 为主（跨设备同步），MemPalace 为辅（本地高速缓存）。
Author: WuKong AI  |  Version: 1.2.0
"""

import sys
import json
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger('UnifiedMemory')

# ── MemOS Cloud ────────────────────────────────────────────────────────────
try:
    from lib.bridge.external.memos_sync import MemOSSync, Knowledge
    _MEMOS_OK = True
except ImportError:
    _MEMOS_OK = False
    Knowledge = object

# ── MemPalace 本地 ────────────────────────────────────────────────────────
try:
    from lib.bridge.persistence.mempalace_bridge import MemPalaceBridge
    _PALACE_OK = True
except ImportError:
    _PALACE_OK = False
    MemPalaceBridge = object


class UnifiedMemoryBridge:
    """
    统一记忆桥：MemOS Cloud（主）+ MemPalace（辅）

    策略：
    - 写入：优先 MemOS Cloud（跨设备），同时写 MemPalace（本地缓存）
    - 读取：优先 MemOS Cloud（最新），MemPalace 作为兜底
    - 搜索：MemOS Cloud search/memory，同时查 MemPalace SQLite
    """

    def __init__(self,
                 user_id: str = '1062695814-580275369',
                 conversation_id: str = 'agent:main:dingtalk:direct:1062695814-580275369'):
        self.user_id = user_id
        self.conversation_id = conversation_id

        # MemOS Cloud 客户端
        self.memos = None
        if _MEMOS_OK:
            try:
                self.memos = MemOSSync(user_id=user_id, conversation_id=conversation_id)
                logger.info(f'[UnifiedMemory] MemOS Cloud 已连接 (user_id={user_id})')
            except Exception as e:
                logger.warning(f'[UnifiedMemory] MemOS Cloud 初始化失败: {e}')

        # MemPalace 本地
        self.palace = None
        if _PALACE_OK:
            try:
                self.palace = MemPalaceBridge()
                logger.info('[UnifiedMemory] MemPalace 本地存储已就绪')
            except Exception as e:
                logger.warning(f'[UnifiedMemory] MemPalace 初始化失败: {e}')

    # ── 写入 ────────────────────────────────────────────────────────────

    def write_memory(self, key: str, value: str,
                    tags: Optional[List[str]] = None,
                    visibility: str = 'private') -> Dict[str, Any]:
        """
        写入记忆（双写：MemOS Cloud + MemPalace 本地）
        Returns: {success, source, id, error}
        """
        result = {'success': False, 'source': None, 'id': None, 'error': None}

        # 1. 写 MemOS Cloud
        if self.memos:
            try:
                knowledge = Knowledge(
                    id=None,
                    content=value,
                    tags=tags or [],
                    visibility=visibility,
                    created_at=time.time(),
                    metadata={'key': key}
                )
                task_id = self.memos.create_knowledge(knowledge)
                if task_id:
                    result['source'] = 'memos_cloud'
                    result['id'] = task_id
                    result['success'] = True
                    logger.info(f'[UnifiedMemory] 写入 MemOS Cloud 成功, task_id={task_id}')
                else:
                    result['error'] = 'MemOS Cloud create_knowledge 返回 None'
            except Exception as e:
                result['error'] = f'MemOS Cloud 写入失败: {e}'
                logger.error(f'[UnifiedMemory] {result["error"]}')

        # 2. 写 MemPalace 本地（兜底）
        if self.palace:
            try:
                payload = json.dumps({'value': value, 'tags': tags or [], 'key': key}, ensure_ascii=False)
                saved = self.palace.save(key, payload)
                if saved:
                    result['source'] = (result['source'] or '') + '+palace_local'
                    logger.info(f'[UnifiedMemory] 写入 MemPalace 本地成功, key={key}')
            except Exception as e:
                logger.warning(f'[UnifiedMemory] MemPalace 本地写入失败: {e}')

        if not result['success'] and not result['error']:
            result['error'] = '所有记忆存储均不可用'

        return result

    # ── 读取 ────────────────────────────────────────────────────────────

    def read_memory(self, key: str) -> Optional[str]:
        """按 key 读取记忆（优先 MemPalace 本地，其次 MemOS Cloud）"""
        # 优先本地
        if self.palace:
            try:
                raw = self.palace.load(key)
                if raw:
                    data = json.loads(raw)
                    return data.get('value')
            except Exception as e:
                logger.warning(f'[UnifiedMemory] MemPalace 读取失败: {e}')

        # 回退 MemOS Cloud（通过 list_knowledge 遍历）
        if self.memos:
            try:
                all_memories = self.memos.list_knowledge(limit=100)
                for m in all_memories:
                    if m.metadata.get('key') == key:
                        return m.content
            except Exception as e:
                logger.warning(f'[UnifiedMemory] MemOS Cloud 读取失败: {e}')

        return None

    # ── 搜索 ────────────────────────────────────────────────────────────

    def search_memory(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        语义搜索记忆（MemOS Cloud 为主，MemPalace 为辅）
        Returns: [{id, content, key, tags, source, score}]
        """
        results = []
        seen_keys = set()

        # 1. MemOS Cloud 语义搜索
        if self.memos:
            try:
                memories = self.memos.list_knowledge(limit=limit)
                for m in memories:
                    key_val = m.metadata.get('key', '')
                    content_lower = m.content.lower()
                    query_lower = query.lower()

                    # 关键词匹配作为简单相似度
                    score = 0.0
                    if query_lower in content_lower:
                        score = 0.5 + 0.5 * (content_lower.count(query_lower) / max(len(content_lower), 1))
                    if query_lower in key_val:
                        score = max(score, 0.8)

                    if score > 0:
                        item = {
                            'id': m.id,
                            'content': m.content,
                            'key': key_val,
                            'tags': m.tags,
                            'source': 'memos_cloud',
                            'score': min(score, 1.0)
                        }
                        if key_val not in seen_keys:
                            results.append(item)
                            seen_keys.add(key_val)
            except Exception as e:
                logger.warning(f'[UnifiedMemory] MemOS Cloud 搜索失败: {e}')

        # 2. MemPalace 本地 SQLite LIKE 搜索
        if self.palace:
            try:
                local_results = self.palace.search(query)
                for row in local_results:
                    key_val = row['key']
                    if key_val not in seen_keys:
                        data = json.loads(row['value'])
                        results.append({
                            'id': key_val,
                            'content': data.get('value', ''),
                            'key': key_val,
                            'tags': data.get('tags', []),
                            'source': 'palace_local',
                            'score': 0.6
                        })
                        seen_keys.add(key_val)
            except Exception as e:
                logger.warning(f'[UnifiedMemory] MemPalace 搜索失败: {e}')

        # 按 score 降序
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return results[:limit]

    # ── 统计 ────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计"""
        stats = {'memos_cloud': None, 'palace_local': None, 'total': 0}

        if self.memos:
            try:
                memories = self.memos.list_knowledge(limit=1)
                # 获取总数（通过 search/memory limit=1000）
                all_m = self.memos.list_knowledge(limit=1000)
                stats['memos_cloud'] = {'count': len(all_m), 'user_id': self.user_id}
            except Exception as e:
                stats['memos_cloud'] = {'error': str(e)}

        if self.palace:
            try:
                rows = self.palace.search('')
                stats['palace_local'] = {'count': len(rows)}
            except Exception as e:
                stats['palace_local'] = {'error': str(e)}

        if stats['memos_cloud']:
            stats['total'] += stats['memos_cloud'].get('count', 0)
        if stats['palace_local']:
            stats['total'] += stats['palace_local'].get('count', 0)

        return stats

    # ── 删除 ────────────────────────────────────────────────────────────

    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆（优先 MemOS Cloud）"""
        if self.memos:
            try:
                return self.memos.delete_knowledge(memory_id)
            except Exception as e:
                logger.error(f'[UnifiedMemory] 删除失败: {e}')
        return False

    # ── 健康检查 ──────────────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """检查两个记忆系统的健康状态"""
        status = {'memos_cloud': False, 'palace_local': False}

        if self.memos:
            try:
                status['memos_cloud'] = self.memos.health_check()
            except Exception:
                pass

        if self.palace:
            try:
                self.palace.search('')
                status['palace_local'] = True
            except Exception:
                pass

        return status


# ── 便捷函数 ────────────────────────────────────────────────────────────

_instance: Optional[UnifiedMemoryBridge] = None

def get_bridge() -> UnifiedMemoryBridge:
    """获取单例实例"""
    global _instance
    if _instance is None:
        _instance = UnifiedMemoryBridge()
    return _instance