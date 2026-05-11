     1|#!/usr/bin/env python3
     2|"""
     3|ClawShell Enhanced Task Scheduler
     4|增强版任务调度器 - Phase 2
     5|版本: v1.1.0
     6|功能: 并发扩容(4→8)、记忆延长、快照优化
     7|"""
     8|
     9|import time
    10|import threading
    11|from typing import Dict, List, Optional, Set, Any
    12|from dataclasses import dataclass, field
    13|from datetime import datetime
    14|from enum import Enum
    15|
    16|class TaskState(Enum):
    17|    PENDING = "pending"
    18|    RUNNING = "running"
    19|    COMPLETED = "completed"
    20|    FAILED = "failed"
    21|    CANCELLED = "cancelled"
    22|
    23|@dataclass
    24|class Task:
    25|    """任务"""
    26|    id: str
    27|    name: str
    28|    state: TaskState = TaskState.PENDING
    29|    created_at: float = field(default_factory=time.time)
    30|    started_at: Optional[float] = None
    31|    completed_at: Optional[float] = None
    32|    result: Any = None
    33|    error: Optional[str] = None
    34|    retries: int = 0
    35|    max_retries: int = 3
    36|
    37|class EnhancedScheduler:
    38|    """
    39|    增强版任务调度器
    40|    
    41|    改进：
    42|    - 并发槽位: 4 → 8
    43|    - 记忆保留: 30min → 60min
    44|    - 快照间隔: 10s → 5s
    45|    """
    46|    
    47|    def __init__(
    48|        self,
    49|        max_concurrent: int = 8,  # 扩容: 4 → 8
    50|        memory_retention: int = 3600,  # 延长: 1800 → 3600秒
    51|        snapshot_interval: int = 5  # 优化: 10 → 5秒
    52|    ):
    53|        self.max_concurrent = max_concurrent
    54|        self.memory_retention = memory_retention
    55|        self.snapshot_interval = snapshot_interval
    56|        
    57|        self._tasks: Dict[str, Task] = {}
    58|        self._running: Set[str] = set()
    59|        self._completed: List[str] = []
    60|        self._lock = threading.RLock()
    61|        
    62|        self._last_snapshot = time.time()
    63|        self._snapshot_count = 0
    64|        
    65|    def submit(self, task_id: str, task_name: str) -> bool:
    66|        """提交任务"""
    67|        with self._lock:
    68|            if task_id in self._tasks:
    69|                return False
    70|            
    71|            task = Task(id=task_id, name=task_name)
    72|            self._tasks[task_id] = task
    73|            return True
    74|    
    75|    def can_execute(self) -> bool:
    76|        """检查是否可以执行"""
    77|        return len(self._running) < self.max_concurrent
    78|    
    79|    def start(self, task_id: str) -> bool:
    80|        """开始任务"""
    81|        with self._lock:
    82|            if task_id not in self._tasks:
    83|                return False
    84|            
    85|            if not self.can_execute():
    86|                return False
    87|            
    88|            task = self._tasks[task_id]
    89|            task.state = TaskState.RUNNING
    90|            task.started_at = time.time()
    91|            self._running.add(task_id)
    92|            
    93|            # 快照
    94|            self._maybe_snapshot()
    95|            
    96|            return True
    97|    
    98|    def complete(self, task_id: str, result: Any = None):
    99|        """完成任务"""
   100|        with self._lock:
   101|            if task_id not in self._tasks:
   102|                return
   103|            
   104|            task = self._tasks[task_id]
   105|            task.state = TaskState.COMPLETED
   106|            task.completed_at = time.time()
   107|            task.result = result
   108|            
   109|            if task_id in self._running:
   110|                self._running.remove(task_id)
   111|            
   112|            self._completed.append(task_id)
   113|            self._cleanup_old_tasks()
   114|    
   115|    def fail(self, task_id: str, error: str):
   116|        """任务失败"""
   117|        with self._lock:
   118|            if task_id not in self._tasks:
   119|                return
   120|            
   121|            task = self._tasks[task_id]
   122|            task.state = TaskState.FAILED
   123|            task.completed_at = time.time()
   124|            task.error = error
   125|            
   126|            if task_id in self._running:
   127|                self._running.remove(task_id)
   128|            
   129|            self._completed.append(task_id)
   130|    
   131|    def _maybe_snapshot(self):
   132|        """快照"""
   133|        now = time.time()
   134|        if now - self._last_snapshot >= self.snapshot_interval:
   135|            self._snapshot_count += 1
   136|            self._last_snapshot = now
   137|    
   138|    def _cleanup_old_tasks(self):
   139|        """清理旧任务"""
   140|        now = time.time()
   141|        to_remove = []
   142|        
   143|        for task_id, task in self._tasks.items():
   144|            if task.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED):
   145|                if task.completed_at and (now - task.completed_at) > self.memory_retention:
   146|                    to_remove.append(task_id)
   147|        
   148|        for task_id in to_remove:
   149|            del self._tasks[task_id]
   150|    
   151|    def get_stats(self) -> Dict:
   152|        """获取统计"""
   153|        total = len(self._tasks)
   154|        completed = sum(1 for t in self._tasks.values() if t.state == TaskState.COMPLETED)
   155|        running = len(self._running)
   156|        pending = total - completed - running
   157|        
   158|        return {
   159|            "max_concurrent": self.max_concurrent,
   160|            "memory_retention": self.memory_retention,
   161|            "snapshot_interval": self.snapshot_interval,
   162|            "total_tasks": total,
   163|            "running": running,
   164|            "pending": pending,
   165|            "completed": completed,
   166|            "snapshot_count": self._snapshot_count
   167|        }
   168|
   169|# 全局实例
   170|_scheduler: Optional[EnhancedScheduler] = None
   171|
   172|def get_scheduler() -> EnhancedScheduler:
   173|    """获取调度器"""
   174|    global _scheduler
   175|    if _scheduler is None:
   176|        _scheduler = EnhancedScheduler()
   177|    return _scheduler
   178|
   179|if __name__ == "__main__":
   180|    scheduler = EnhancedScheduler()
   181|    
   182|    print("=== 增强调度器测试 ===")
   183|    print(f"并发槽位: {scheduler.max_concurrent}")
   184|    print(f"记忆保留: {scheduler.memory_retention}s")
   185|    print(f"快照间隔: {scheduler.snapshot_interval}s")
   186|    
   187|    # 测试任务
   188|    scheduler.submit("task1", "测试任务1")
   189|    scheduler.submit("task2", "测试任务2")
   190|    
   191|    print(f"\n提交后: {scheduler.get_stats()}")
   192|    
   193|    scheduler.start("task1")
   194|    print(f"启动task1: {scheduler.get_stats()}")
   195|    
   196|    scheduler.complete("task1", "result1")
   197|    print(f"完成task1: {scheduler.get_stats()}")
   198|