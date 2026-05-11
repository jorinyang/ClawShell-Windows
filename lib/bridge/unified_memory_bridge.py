     1|#!/usr/bin/env python3
     2|# -*- coding: utf-8 -*-
     3|"""
     4|UnifiedMemoryBridge - 统一记忆桥
     5|================================
     6|整合 MemOS Cloud 和 MemPalace 的统一记忆接口。
     7|MemOS Cloud 为主（跨设备同步），MemPalace 为辅（本地高速缓存）。
     8|Author: WuKong AI  |  Version: 1.1.0
     9|"""
    10|
    11|import sys
    12|import json
    13|import time
    14|import logging
    15|from typing import Dict, Any, List, Optional
    16|
    17|logger = logging.getLogger('UnifiedMemory')
    18|
    19|# ── MemOS Cloud ────────────────────────────────────────────────────────────
    20|try:
    21|    from lib.bridge.external.memos_sync import MemOSSync, Knowledge
    22|    _MEMOS_OK = True
    23|except ImportError:
    24|    _MEMOS_OK = False
    25|    Knowledge = object
    26|
    27|# ── MemPalace 本地 ────────────────────────────────────────────────────────
    28|try:
    29|    from lib.bridge.persistence.mempalace_bridge import MemPalaceBridge
    30|    _PALACE_OK = True
    31|except ImportError:
    32|    _PALACE_OK = False
    33|    MemPalaceBridge = object
    34|
    35|
    36|class UnifiedMemoryBridge:
    37|    """
    38|    统一记忆桥：MemOS Cloud（主）+ MemPalace（辅）
    39|
    40|    策略：
    41|    - 写入：优先 MemOS Cloud（跨设备），同时写 MemPalace（本地缓存）
    42|    - 读取：优先 MemOS Cloud（最新），MemPalace 作为兜底
    43|    - 搜索：MemOS Cloud search/memory，同时查 MemPalace SQLite
    44|    """
    45|
    46|    def __init__(self,
    47|                 user_id: str = '1062695814-580275369',
    48|                 conversation_id: str = 'agent:main:dingtalk:direct:1062695814-580275369'):
    49|        self.user_id = user_id
    50|        self.conversation_id = conversation_id
    51|
    52|        # MemOS Cloud 客户端
    53|        self.memos = None
    54|        if _MEMOS_OK:
    55|            try:
    56|                self.memos = MemOSSync(user_id=user_id, conversation_id=conversation_id)
    57|                logger.info(f'[UnifiedMemory] MemOS Cloud 已连接 (user_id={user_id})')
    58|            except Exception as e:
    59|                logger.warning(f'[UnifiedMemory] MemOS Cloud 初始化失败: {e}')
    60|
    61|        # MemPalace 本地
    62|        self.palace = None
    63|        if _PALACE_OK:
    64|            try:
    65|                self.palace = MemPalaceBridge()
    66|                logger.info('[UnifiedMemory] MemPalace 本地存储已就绪')
    67|            except Exception as e:
    68|                logger.warning(f'[UnifiedMemory] MemPalace 初始化失败: {e}')
    69|
    70|    # ── 写入 ────────────────────────────────────────────────────────────
    71|
    72|    def write_memory(self, key: str, value: str,
    73|                    tags: Optional[List[str]] = None,
    74|                    visibility: str = 'private') -> Dict[str, Any]:
    75|        """
    76|        写入记忆（双写：MemOS Cloud + MemPalace 本地）
    77|        Returns: {success, source, id, error}
    78|        """
    79|        result = {'success': False, 'source': None, 'id': None, 'error': None}
    80|
    81|        # 1. 写 MemOS Cloud
    82|        if self.memos:
    83|            try:
    84|                knowledge = Knowledge(
    85|                    id=None,
    86|                    content=value,
    87|                    tags=tags or [],
    88|                    visibility=visibility,
    89|                    created_at=time.time(),
    90|                    metadata={'key': key}
    91|                )
    92|                task_id = self.memos.create_knowledge(knowledge)
    93|                if task_id:
    94|                    result['source'] = 'memos_cloud'
    95|                    result['id'] = task_id
    96|                    result['success'] = True
    97|                    logger.info(f'[UnifiedMemory] 写入 MemOS Cloud 成功, task_id={task_id}')
    98|                else:
    99|                    result['error'] = 'MemOS Cloud create_knowledge 返回 None'
   100|            except Exception as e:
   101|                result['error'] = f'MemOS Cloud 写入失败: {e}'
   102|                logger.error(f'[UnifiedMemory] {result["error"]}')
   103|
   104|        # 2. 写 MemPalace 本地（兜底）
   105|        if self.palace:
   106|            try:
   107|                payload = json.dumps({'value': value, 'tags': tags or [], 'key': key}, ensure_ascii=False)
   108|                saved = self.palace.save(key, payload)
   109|                if saved:
   110|                    result['source'] = (result['source'] or '') + '+palace_local'
   111|                    logger.info(f'[UnifiedMemory] 写入 MemPalace 本地成功, key={key}')
   112|            except Exception as e:
   113|                logger.warning(f'[UnifiedMemory] MemPalace 本地写入失败: {e}')
   114|
   115|        if not result['success'] and not result['error']:
   116|            result['error'] = '所有记忆存储均不可用'
   117|
   118|        return result
   119|
   120|    # ── 读取 ────────────────────────────────────────────────────────────
   121|
   122|    def read_memory(self, key: str) -> Optional[str]:
   123|        """按 key 读取记忆（优先 MemPalace 本地，其次 MemOS Cloud）"""
   124|        # 优先本地
   125|        if self.palace:
   126|            try:
   127|                raw = self.palace.load(key)
   128|                if raw:
   129|                    data = json.loads(raw)
   130|                    return data.get('value')
   131|            except Exception as e:
   132|                logger.warning(f'[UnifiedMemory] MemPalace 读取失败: {e}')
   133|
   134|        # 回退 MemOS Cloud（通过 list_knowledge 遍历）
   135|        if self.memos:
   136|            try:
   137|                all_memories = self.memos.list_knowledge(limit=100)
   138|                for m in all_memories:
   139|                    if m.metadata.get('key') == key:
   140|                        return m.content
   141|            except Exception as e:
   142|                logger.warning(f'[UnifiedMemory] MemOS Cloud 读取失败: {e}')
   143|
   144|        return None
   145|
   146|    # ── 搜索 ────────────────────────────────────────────────────────────
   147|
   148|    def search_memory(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
   149|        """
   150|        语义搜索记忆（MemOS Cloud 为主，MemPalace 为辅）
   151|        Returns: [{id, content, key, tags, source, score}]
   152|        """
   153|        results = []
   154|        seen_keys = set()
   155|
   156|        # 1. MemOS Cloud 语义搜索
   157|        if self.memos:
   158|            try:
   159|                memories = self.memos.list_knowledge(limit=limit)
   160|                for m in memories:
   161|                    key_val = m.metadata.get('key', '')
   162|                    content_lower = m.content.lower()
   163|                    query_lower = query.lower()
   164|
   165|                    # 关键词匹配作为简单相似度
   166|                    score = 0.0
   167|                    if query_lower in content_lower:
   168|                        score = 0.5 + 0.5 * (content_lower.count(query_lower) / max(len(content_lower), 1))
   169|                    if query_lower in key_val:
   170|                        score = max(score, 0.8)
   171|
   172|                    if score > 0:
   173|                        item = {
   174|                            'id': m.id,
   175|                            'content': m.content,
   176|                            'key': key_val,
   177|                            'tags': m.tags,
   178|                            'source': 'memos_cloud',
   179|                            'score': min(score, 1.0)
   180|                        }
   181|                        if key_val not in seen_keys:
   182|                            results.append(item)
   183|                            seen_keys.add(key_val)
   184|            except Exception as e:
   185|                logger.warning(f'[UnifiedMemory] MemOS Cloud 搜索失败: {e}')
   186|
   187|        # 2. MemPalace 本地 SQLite LIKE 搜索
   188|        if self.palace:
   189|            try:
   190|                local_results = self.palace.search(query)
   191|                for row in local_results:
   192|                    key_val = row['key']
   193|                    if key_val not in seen_keys:
   194|                        data = json.loads(row['value'])
   195|                        results.append({
   196|                            'id': key_val,
   197|                            'content': data.get('value', ''),
   198|                            'key': key_val,
   199|                            'tags': data.get('tags', []),
   200|                            'source': 'palace_local',
   201|                            'score': 0.6
   202|                        })
   203|                        seen_keys.add(key_val)
   204|            except Exception as e:
   205|                logger.warning(f'[UnifiedMemory] MemPalace 搜索失败: {e}')
   206|
   207|        # 按 score 降序
   208|        results.sort(key=lambda x: x.get('score', 0), reverse=True)
   209|        return results[:limit]
   210|
   211|    # ── 统计 ────────────────────────────────────────────────────────────
   212|
   213|    def get_stats(self) -> Dict[str, Any]:
   214|        """获取记忆统计"""
   215|        stats = {'memos_cloud': None, 'palace_local': None, 'total': 0}
   216|
   217|        if self.memos:
   218|            try:
   219|                memories = self.memos.list_knowledge(limit=1)
   220|                # 获取总数（通过 search/memory limit=1000）
   221|                all_m = self.memos.list_knowledge(limit=1000)
   222|                stats['memos_cloud'] = {'count': len(all_m), 'user_id': self.user_id}
   223|            except Exception as e:
   224|                stats['memos_cloud'] = {'error': str(e)}
   225|
   226|        if self.palace:
   227|            try:
   228|                rows = self.palace.search('')
   229|                stats['palace_local'] = {'count': len(rows)}
   230|            except Exception as e:
   231|                stats['palace_local'] = {'error': str(e)}
   232|
   233|        if stats['memos_cloud']:
   234|            stats['total'] += stats['memos_cloud'].get('count', 0)
   235|        if stats['palace_local']:
   236|            stats['total'] += stats['palace_local'].get('count', 0)
   237|
   238|        return stats
   239|
   240|    # ── 删除 ────────────────────────────────────────────────────────────
   241|
   242|    def delete_memory(self, memory_id: str) -> bool:
   243|        """删除记忆（优先 MemOS Cloud）"""
   244|        if self.memos:
   245|            try:
   246|                return self.memos.delete_knowledge(memory_id)
   247|            except Exception as e:
   248|                logger.error(f'[UnifiedMemory] 删除失败: {e}')
   249|        return False
   250|
   251|    # ── 健康检查 ──────────────────────────────────────────────────────
   252|
   253|    def health_check(self) -> Dict[str, Any]:
   254|        """检查两个记忆系统的健康状态"""
   255|        status = {'memos_cloud': False, 'palace_local': False}
   256|
   257|        if self.memos:
   258|            try:
   259|                status['memos_cloud'] = self.memos.health_check()
   260|            except Exception:
   261|                pass
   262|
   263|        if self.palace:
   264|            try:
   265|                self.palace.search('')
   266|                status['palace_local'] = True
   267|            except Exception:
   268|                pass
   269|
   270|        return status
   271|
   272|
   273|# ── 便捷函数 ────────────────────────────────────────────────────────────
   274|
   275|_instance: Optional[UnifiedMemoryBridge] = None
   276|
   277|def get_bridge() -> UnifiedMemoryBridge:
   278|    """获取单例实例"""
   279|    global _instance
   280|    if _instance is None:
   281|        _instance = UnifiedMemoryBridge()
   282|    return _instance