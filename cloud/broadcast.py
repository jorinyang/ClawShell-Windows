"""
ClawShell Cloud — Broadcast Engine + CrossEdgeLearning v1.1
============================================================
一云多端的成果广播与跨端经验学习引擎。

核心能力:
  BroadcastScheduler — 定时向所有Edge广播优化成果
  CrossEdgeLearning  — 一端执行→提炼→他端参考的完整闭环
  BestPracticeRegistry — 最佳实践自动注册+版本管理+效果追踪

设计原则:
  - 零外部依赖 (stdlib only)
  - 线程安全 (threading.Lock)
  - JSON持久化
  - 与EventBus深度集成

Usage:
  from cloud.broadcast import BroadcastEngine
  engine = BroadcastEngine(data_dir=Path("data"))
"""

import json
import uuid
import time
import threading
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict

logger = logging.getLogger("CloudHub.Broadcast")

BROADCAST_INTERVAL = 60  # 1 minute check cycle


@dataclass
class BroadcastMessage:
    """A broadcast message sent to all edges."""
    broadcast_id: str = ""
    category: str = ""          # insight, skill_update, config_change, best_practice, global_announcement
    title: str = ""
    content: str = ""
    priority: str = "normal"    # low, normal, high, critical
    target_edges: List[str] = field(default_factory=list)  # Empty = all
    source: str = "cloud-hub"
    created_at: str = ""
    expires_at: Optional[str] = None
    delivered_count: int = 0
    read_count: int = 0


@dataclass
class BestPractice:
    """A registered best practice with versioning and effect tracking."""
    bp_id: str = ""
    name: str = ""
    description: str = ""
    category: str = ""          # deployment, optimization, error_handling, workflow, security
    version: int = 1
    source_node: str = ""       # Which edge discovered this
    source_insight_id: str = "" # Which insight led to this
    content: str = ""           # The actual practice/method
    tags: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    effect_metrics: Dict = field(default_factory=dict)  # Track effectiveness
    adoption_count: int = 0     # How many edges have adopted
    rating: float = 0.0
    status: str = "active"      # draft, active, deprecated, superseded
    created_at: str = ""
    updated_at: str = ""


# ═══════════════════════════════════════════════════════════
# BestPracticeRegistry
# ═══════════════════════════════════════════════════════════

class BestPracticeRegistry:
    """Best practice registry with versioning and effect tracking."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "broadcast"
        self.bp_file = self.data_dir / "best_practices.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._practices: Dict[str, BestPractice] = {}
        self._load()

    def _load(self):
        if self.bp_file.exists():
            try:
                data = json.loads(self.bp_file.read_text())
                for bp_data in data.get("practices", []):
                    bp = BestPractice(**bp_data)
                    self._practices[bp.bp_id] = bp
            except:
                pass

    def _save(self):
        with self._lock:
            self.bp_file.write_text(json.dumps({
                "practices": [asdict(bp) for bp in self._practices.values()],
                "updated_at": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))

    def register(self, name: str, description: str, content: str,
                 category: str = "general", source_node: str = "cloud-hub",
                 tags: List[str] = None, prerequisites: List[str] = None) -> str:
        """Register a new best practice."""
        bp_id = str(uuid.uuid4())[:8]
        bp = BestPractice(
            bp_id=bp_id,
            name=name,
            description=description,
            content=content,
            category=category,
            source_node=source_node,
            tags=tags or [],
            prerequisites=prerequisites or [],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        with self._lock:
            self._practices[bp_id] = bp
            self._save()
        logger.info(f"BestPractice registered: {name} (id={bp_id})")
        return bp_id

    def update_effect(self, bp_id: str, metrics: Dict):
        """Update effect metrics after adoption."""
        with self._lock:
            if bp_id in self._practices:
                bp = self._practices[bp_id]
                bp.effect_metrics.update(metrics)
                bp.adoption_count += 1
                bp.updated_at = datetime.now().isoformat()
                self._save()

    def search(self, category: str = None, tags: List[str] = None,
               limit: int = 20) -> List[Dict]:
        """Search best practices."""
        with self._lock:
            results = []
            for bp in self._practices.values():
                if category and bp.category != category:
                    continue
                if tags and not any(t in bp.tags for t in tags):
                    continue
                if bp.status != "active":
                    continue
                results.append(asdict(bp))
            results.sort(key=lambda x: (x.get("adoption_count", 0), x.get("rating", 0)), reverse=True)
            return results[:limit]

    def get_all(self, limit: int = 50) -> List[Dict]:
        with self._lock:
            active = [asdict(bp) for bp in self._practices.values() if bp.status == "active"]
            return active[:limit]

    def get_stats(self) -> Dict:
        with self._lock:
            return {
                "total": len(self._practices),
                "active": sum(1 for bp in self._practices.values() if bp.status == "active"),
                "total_adoptions": sum(bp.adoption_count for bp in self._practices.values()),
                "by_category": {c: sum(1 for bp in self._practices.values() if bp.category == c)
                               for c in set(bp.category for bp in self._practices.values())},
            }


# ═══════════════════════════════════════════════════════════
# CrossEdgeLearning — Cross-edge experience propagation
# ═══════════════════════════════════════════════════════════

class CrossEdgeLearning:
    """一端执行→提炼→他端参考的完整闭环。

    Flow:
      1. Edge A executes task → sends execution record to Cloud
      2. Cloud analyzes result → extracts learnings
      3. Cloud broadcasts learnings → all other Edges receive
      4. Other Edges apply learnings in their next actions
    """

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "broadcast"
        self.learnings_file = self.data_dir / "cross_edge_learnings.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._learnings: List[Dict] = []
        self._edge_knowledge: Dict[str, List[str]] = defaultdict(list)  # edge_id → [learning_id]
        self._load()

    def _load(self):
        if self.learnings_file.exists():
            try:
                data = json.loads(self.learnings_file.read_text())
                self._learnings = data.get("learnings", [])
                self._edge_knowledge = defaultdict(list, data.get("edge_knowledge", {}))
            except:
                pass

    def _save(self):
        with self._lock:
            self.learnings_file.write_text(json.dumps({
                "learnings": self._learnings[-200:],
                "edge_knowledge": dict(self._edge_knowledge),
                "updated_at": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))

    def extract_learning(self, edge_id: str, task_result: Dict) -> Optional[Dict]:
        """Extract reusable learning from a completed task."""
        success = task_result.get("success", task_result.get("status") == "completed")
        duration = task_result.get("duration_seconds", 0)
        method = task_result.get("method", task_result.get("approach", ""))

        if not success or not method:
            return None

        learning = {
            "learning_id": str(uuid.uuid4())[:8],
            "source_edge": edge_id,
            "task_type": task_result.get("type", "unknown"),
            "method": method,
            "duration_seconds": duration,
            "key_insight": task_result.get("insight", task_result.get("takeaway", "")),
            "applicable_scenarios": task_result.get("tags", []),
            "confidence": task_result.get("confidence", 0.7),
            "extracted_at": datetime.now().isoformat(),
            "propagated_to": [],
        }

        with self._lock:
            self._learnings.append(learning)
            self._edge_knowledge[edge_id].append(learning["learning_id"])
            self._save()

        logger.info(f"Extracted learning from {edge_id}: {method[:50]}")
        return learning

    def get_learnings_for_edge(self, edge_id: str, exclude_own: bool = True,
                               limit: int = 10) -> List[Dict]:
        """Get learnings to propagate to a specific edge."""
        with self._lock:
            result = []
            for learning in reversed(self._learnings):
                if exclude_own and learning["source_edge"] == edge_id:
                    continue
                if edge_id in learning.get("propagated_to", []):
                    continue
                result.append(learning)
                if len(result) >= limit:
                    break
            return result

    def mark_propagated(self, learning_id: str, edge_id: str):
        """Mark a learning as propagated to an edge."""
        with self._lock:
            for learning in self._learnings:
                if learning["learning_id"] == learning_id:
                    if edge_id not in learning.get("propagated_to", []):
                        learning.setdefault("propagated_to", []).append(edge_id)
                    break
            self._save()

    def get_stats(self) -> Dict:
        with self._lock:
            return {
                "total_learnings": len(self._learnings),
                "edges_contributing": len(self._edge_knowledge),
                "avg_confidence": sum(l.get("confidence", 0) for l in self._learnings) / max(len(self._learnings), 1),
            }


# ═══════════════════════════════════════════════════════════
# BroadcastEngine — Unified broadcast engine
# ═══════════════════════════════════════════════════════════

class BroadcastEngine:
    """Unified broadcast + cross-edge learning engine."""

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = Path(data_dir)

        self.best_practices = BestPracticeRegistry(self.data_dir)
        self.cross_edge = CrossEdgeLearning(self.data_dir)

        self._running = False
        self._thread = None
        self._eventbus = None
        self._messages: List[BroadcastMessage] = []
        self._broadcast_file = self.data_dir / "broadcast" / "broadcasts.json"

        self.stats = {
            "cycles": 0,
            "broadcasts_sent": 0,
            "learnings_extracted": 0,
            "best_practices_registered": 0,
        }

    def set_eventbus(self, eventbus):
        self._eventbus = eventbus

    def broadcast(self, category: str, title: str, content: str,
                  priority: str = "normal", target_edges: List[str] = None) -> str:
        """Send a broadcast to all edges (or specific targets)."""
        msg = BroadcastMessage(
            broadcast_id=str(uuid.uuid4())[:8],
            category=category,
            title=title,
            content=content,
            priority=priority,
            target_edges=target_edges or [],
            created_at=datetime.now().isoformat(),
        )

        self._messages.append(msg)
        if len(self._messages) > 100:
            self._messages = self._messages[-80:]

        # Push via EventBus
        if self._eventbus:
            self._eventbus.publish("broadcast", {
                "broadcast_id": msg.broadcast_id,
                "category": category,
                "title": title,
                "content": content,
                "priority": priority,
            }, source="cloud-hub", broadcast=True)

        self.stats["broadcasts_sent"] += 1
        self._save_broadcasts()
        logger.info(f"Broadcast sent: [{category}] {title[:50]}")
        return msg.broadcast_id

    def promote_to_best_practice(self, pattern: Dict) -> Optional[str]:
        """Promote a mined pattern to a best practice."""
        bp_id = self.best_practices.register(
            name=pattern.get("title", "Unnamed Practice"),
            description=pattern.get("description", ""),
            content=pattern.get("suggested_action", ""),
            category=pattern.get("category", "general"),
            tags=["auto-promoted", pattern.get("category", "general")],
        )
        self.stats["best_practices_registered"] += 1

        # Broadcast the new best practice
        self.broadcast(
            category="best_practice",
            title=f"New Best Practice: {pattern.get('title', '')}",
            content=pattern.get("description", ""),
            priority="normal",
        )
        return bp_id

    def get_pending_broadcasts(self, limit: int = 20) -> List[Dict]:
        """Get recent broadcasts for edge consumption."""
        return [asdict(m) for m in self._messages[-limit:]]

    def _save_broadcasts(self):
        (self.data_dir / "broadcast").mkdir(parents=True, exist_ok=True)
        self._broadcast_file.write_text(json.dumps({
            "broadcasts": [asdict(m) for m in self._messages],
            "stats": self.stats,
        }, indent=2, ensure_ascii=False))

    def get_stats(self) -> Dict:
        return {
            **self.stats,
            "best_practices": self.best_practices.get_stats(),
            "cross_edge": self.cross_edge.get_stats(),
        }
