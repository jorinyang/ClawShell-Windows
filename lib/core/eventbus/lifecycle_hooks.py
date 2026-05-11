"""
Lifecycle Hooks - 生命周期钩子
================================

支持会话生命周期事件自动触发 MemPalace 记忆保存。
"""

import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable

try:
    from .core import EventBus, Event
    from .schema import EventType
except ImportError:
    from lib.core.eventbus.core import EventBus, Event
    from lib.core.eventbus.schema import EventType


class MemPalaceHookSubscriber:
    """
    MemPalace 自动记忆钩子订阅器
    
    当 EventBus 触发会话事件时，自动将对话内容写入 MemPalace。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self, eventbus: Optional[EventBus] = None, wing: str = "wukong", auto_init: bool = False):
        self._eventbus = eventbus
        self._wing = wing
        self._initialized = False
        self._palace_dir = Path.home() / ".mempalace" / wing
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._event_queue = []
        self._queue_lock = threading.Lock()
        
        if auto_init:
            self._init_async_worker()
    
    @classmethod
    def get_instance(cls, eventbus: Optional[EventBus] = None, wing: str = "wukong", auto_init: bool = False) -> 'MemPalaceHookSubscriber':
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(eventbus=eventbus, wing=wing, auto_init=auto_init)
        return cls._instance
    
    def _init_async_worker(self):
        """初始化异步工作线程"""
        self._palace_dir.mkdir(parents=True, exist_ok=True)
        self._worker_thread = threading.Thread(target=self._async_worker, daemon=True, name="MemPalaceHookWorker")
        self._worker_thread.start()
        self._initialized = True
    
    def _async_worker(self):
        """异步处理事件的 worker"""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        
        from lib.bridge.persistence.mempalace_bridge import MemPalaceBridge
        
        bridge = MemPalaceBridge()
        
        while not self._stop_event.is_set():
            with self._queue_lock:
                if not self._event_queue:
                    events_to_process = []
                else:
                    events_to_process = self._event_queue.copy()
                    self._event_queue.clear()
            
            for event in events_to_process:
                try:
                    self._process_event(event, bridge)
                except Exception as e:
                    print(f"[MemPalaceHook] 处理事件失败: {e}")
            
            time.sleep(0.5)
    
    def _process_event(self, event: Event, bridge: 'MemPalaceBridge'):
        """处理单个事件"""
        if event.type == EventType.CONVERSATION_END:
            self._save_conversation(event, bridge)
        elif event.type == EventType.SESSION_SUMMARY:
            self._save_summary(event, bridge)
        elif event.type == EventType.USER_MESSAGE:
            self._buffer_user_message(event)
    
    def _save_conversation(self, event: Event, bridge: 'MemPalaceBridge'):
        """保存完整对话"""
        payload = event.payload or {}
        messages = payload.get("messages", [])
        session_id = payload.get("session_id", "unknown")
        
        if messages:
            content = f"## 对话记录 [{session_id}]\n\n"
            for msg in messages[-20:]:  # 最近20条
                role = msg.get("role", "unknown")
                text = msg.get("content", "")[:500]
                content += f"**{role}**: {text}\n\n"
            
            key = f"conversation_{session_id}_{int(time.time())}"
            bridge.save(key, content)
    
    def _save_summary(self, event: Event, bridge: 'MemPalaceBridge'):
        """保存会话摘要"""
        payload = event.payload or {}
        summary = payload.get("summary", "")
        session_id = payload.get("session_id", "unknown")
        
        if summary:
            key = f"summary_{session_id}"
            bridge.save(key, summary)
    
    def _buffer_user_message(self, event: Event):
        """缓冲用户消息"""
        # 简单缓冲，不立即写入
        pass
    
    def register(self, eventbus: Optional[EventBus] = None) -> bool:
        """注册到 EventBus"""
        bus = eventbus or self._eventbus
        if not bus:
            return False
        
        try:
            bus.subscribe(EventType.CONVERSATION_END, self._on_conversation_end)
            bus.subscribe(EventType.SESSION_SUMMARY, self._on_session_summary)
            return True
        except Exception as e:
            print(f"[MemPalaceHook] 注册失败: {e}")
            return False
    
    def _on_conversation_end(self, event: Event):
        with self._queue_lock:
            self._event_queue.append(event)
    
    def _on_session_summary(self, event: Event):
        with self._queue_lock:
            self._event_queue.append(event)
    
    def shutdown(self):
        """关闭钩子"""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2)


__all__ = ["MemPalaceHookSubscriber"]
