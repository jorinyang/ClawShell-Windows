     1|#!/usr/bin/env python3
     2|"""
     3|ClawShell Cache Manager
     4|智能缓存管理器 - Phase 2
     5|版本: v1.1.0
     6|功能: LRU缓存+预取
     7|"""
     8|
     9|import time
    10|import threading
    11|from typing import Any, Dict, Optional, Callable
    12|from collections import OrderedDict
    13|from dataclasses import dataclass
    14|from datetime import datetime
    15|
    16|@dataclass
    17|class CacheEntry:
    18|    """缓存条目"""
    19|    key: str
    20|    value: Any
    21|    created_at: float
    22|    last_accessed: float
    23|    access_count: int = 0
    24|    ttl: float = 3600  # 默认1小时
    25|
    26|class SmartCache:
    27|    """
    28|    智能缓存管理器
    29|    
    30|    功能：
    31|    - LRU淘汰策略
    32|    - TTL过期
    33|    - 预取机制
    34|    - 统计监控
    35|    """
    36|    
    37|    def __init__(self, max_size: int = 1000, default_ttl: float = 3600):
    38|        self.max_size = max_size
    39|        self.default_ttl = default_ttl
    40|        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
    41|        self._lock = threading.RLock()
    42|        self._stats = {
    43|            "hits": 0,
    44|            "misses": 0,
    45|            "evictions": 0,
    46|            "prefetch": 0
    47|        }
    48|        self._prefetch_callbacks: Dict[str, Callable] = {}
    49|        
    50|    def get(self, key: str) -> Optional[Any]:
    51|        """获取缓存"""
    52|        with self._lock:
    53|            if key not in self._cache:
    54|                self._stats["misses"] += 1
    55|                return None
    56|            
    57|            entry = self._cache[key]
    58|            
    59|            # 检查TTL
    60|            if time.time() - entry.created_at > entry.ttl:
    61|                del self._cache[key]
    62|                self._stats["misses"] += 1
    63|                return None
    64|            
    65|            # 更新访问时间
    66|            entry.last_accessed = time.time()
    67|            entry.access_count += 1
    68|            self._cache.move_to_end(key)
    69|            
    70|            self._stats["hits"] += 1
    71|            return entry.value
    72|    
    73|    def set(self, key: str, value: Any, ttl: float = None):
    74|        """设置缓存"""
    75|        with self._lock:
    76|            if key in self._cache:
    77|                del self._cache[key]
    78|            
    79|            entry = CacheEntry(
    80|                key=key,
    81|                value=value,
    82|                created_at=time.time(),
    83|                last_accessed=time.time(),
    84|                ttl=ttl or self.default_ttl
    85|            )
    86|            
    87|            self._cache[key] = entry
    88|            self._cache.move_to_end(key)
    89|            
    90|            # LRU淘汰
    91|            while len(self._cache) > self.max_size:
    92|                self._cache.popitem(last=False)
    93|                self._stats["evictions"] += 1
    94|    
    95|    def prefetch(self, keys: list):
    96|        """预取缓存"""
    97|        for key in keys:
    98|            if key not in self._cache:
    99|                if key in self._prefetch_callbacks:
   100|                    value = self._prefetch_callbacks[key]()
   101|                    if value is not None:
   102|                        self.set(key, value)
   103|                        self._stats["prefetch"] += 1
   104|    
   105|    def register_prefetch(self, key: str, callback: Callable):
   106|        """注册预取回调"""
   107|        self._prefetch_callbacks[key] = callback
   108|    
   109|    def invalidate(self, key: str):
   110|        """使缓存失效"""
   111|        with self._lock:
   112|            if key in self._cache:
   113|                del self._cache[key]
   114|    
   115|    def clear(self):
   116|        """清空缓存"""
   117|        with self._lock:
   118|            self._cache.clear()
   119|    
   120|    def get_stats(self) -> Dict:
   121|        """获取统计"""
   122|        total = self._stats["hits"] + self._stats["misses"]
   123|        hit_rate = self._stats["hits"] / total if total > 0 else 0
   124|        
   125|        return {
   126|            "size": len(self._cache),
   127|            "max_size": self.max_size,
   128|            "hit_rate": hit_rate,
   129|            **self._stats
   130|        }
   131|    
   132|    def auto_prefetch(self, threshold: float = 0.7):
   133|        """自动预取 - 当命中率低于阈值时"""
   134|        stats = self.get_stats()
   135|        if stats["hit_rate"] < threshold:
   136|            # 触发预取
   137|            for key, callback in self._prefetch_callbacks.items():
   138|                if key not in self._cache:
   139|                    value = callback()
   140|                    if value:
   141|                        self.set(key, value)
   142|                        self._stats["prefetch"] += 1
   143|
   144|# 全局缓存实例
   145|_global_cache: Optional[SmartCache] = None
   146|
   147|def get_cache() -> SmartCache:
   148|    """获取全局缓存"""
   149|    global _global_cache
   150|    if _global_cache is None:
   151|        _global_cache = SmartCache(max_size=1000, default_ttl=3600)
   152|    return _global_cache
   153|
   154|if __name__ == "__main__":
   155|    cache = SmartCache(max_size=100, default_ttl=10)
   156|    
   157|    # 测试
   158|    print("=== 智能缓存测试 ===")
   159|    
   160|    cache.set("key1", "value1")
   161|    cache.set("key2", "value2")
   162|    
   163|    print(f"get key1: {cache.get('key1')}")
   164|    print(f"get key2: {cache.get('key2')}")
   165|    print(f"get key3: {cache.get('key3')}")
   166|    
   167|    print(f"\nStats: {cache.get_stats()}")
   168|