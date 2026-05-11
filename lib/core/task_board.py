"""
ClawShell Cloud — Global Task Board v1.1
=========================================
Cloud-side shared task board visible and claimable by ALL edge nodes.
Any edge can publish tasks, any edge can claim and complete them.

Data stored in: data/task_board.json
"""

import json
import uuid
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class TaskStatus(str, Enum):
    OPEN = "open"           # Available for any edge
    CLAIMED = "claimed"     # Claimed by an edge, in progress
    COMPLETED = "completed" # Done
    FAILED = "failed"       # Failed


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


PRIORITY_ORDER = {TaskPriority.CRITICAL: 0, TaskPriority.HIGH: 1,
                   TaskPriority.MEDIUM: 2, TaskPriority.LOW: 3}


@dataclass
class BoardTask:
    task_id: str = ""
    task_type: str = ""
    title: str = ""
    status: TaskStatus = TaskStatus.OPEN
    priority: TaskPriority = TaskPriority.MEDIUM
    created_by: str = ""        # node_id of creator
    claimed_by: str = ""         # node_id of claimer
    required_capability: str = "" # capability needed
    required_skill: str = ""     # skill needed
    payload: Dict = field(default_factory=dict)
    result: Optional[Dict] = None
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["priority"] = self.priority.value
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "BoardTask":
        data = dict(data)
        if isinstance(data.get("status"), str):
            data["status"] = TaskStatus(data["status"])
        if isinstance(data.get("priority"), str):
            data["priority"] = TaskPriority(data["priority"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class GlobalTaskBoard:
    """Cloud-side shared task board — all edges can see and interact."""

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.board_file = self.data_dir / "task_board.json"
        self._tasks: Dict[str, BoardTask] = {}
        self._lock = threading.Lock()
        self._load()

    def _save(self):
        with self._lock:
            data = {tid: t.to_dict() for tid, t in self._tasks.items()}
            self.board_file.write_text(json.dumps({
                "tasks": data,
                "updated_at": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))

    def _load(self):
        if self.board_file.exists():
            try:
                data = json.loads(self.board_file.read_text())
                with self._lock:
                    for tid, td in data.get("tasks", {}).items():
                        self._tasks[tid] = BoardTask.from_dict(td)
            except:
                pass

    # ═══ Task CRUD ═════════════════════════════════════════

    def publish(self, title: str, task_type: str = "general",
                priority: TaskPriority = TaskPriority.MEDIUM,
                created_by: str = "unknown",
                required_capability: str = "",
                required_skill: str = "",
                payload: Dict = None,
                tags: List[str] = None) -> BoardTask:
        """Publish a task to the global board — visible to all edges"""
        now = datetime.now().isoformat()
        task = BoardTask(
            task_id=str(uuid.uuid4())[:8],
            task_type=task_type, title=title,
            status=TaskStatus.OPEN, priority=priority,
            created_by=created_by,
            required_capability=required_capability,
            required_skill=required_skill,
            payload=payload or {},
            tags=tags or [],
            created_at=now, updated_at=now,
        )
        with self._lock:
            self._tasks[task.task_id] = task
            self._save()
        return task

    def claim(self, task_id: str, node_id: str) -> Optional[BoardTask]:
        """An edge claims a task from the board"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != TaskStatus.OPEN:
                return None
            task.status = TaskStatus.CLAIMED
            task.claimed_by = node_id
            task.updated_at = datetime.now().isoformat()
            self._save()
            return task

    def complete(self, task_id: str, result: Dict = None) -> Optional[BoardTask]:
        """Mark task as completed with result"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.status != TaskStatus.CLAIMED:
                return None
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now().isoformat()
            task.updated_at = datetime.now().isoformat()
            self._save()
            return task

    def fail(self, task_id: str, error: str = None) -> Optional[BoardTask]:
        """Mark task as failed"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            task.status = TaskStatus.FAILED
            task.result = {"error": error} if error else None
            task.updated_at = datetime.now().isoformat()
            self._save()
            return task

    # ═══ Query ═════════════════════════════════════════════

    def list(self, status: TaskStatus = None, priority: TaskPriority = None,
             created_by: str = None, claimed_by: str = None,
             required_capability: str = None,
             limit: int = 50) -> List[BoardTask]:
        """List tasks with filters — all edges see the same board"""
        with self._lock:
            tasks = list(self._tasks.values())
            if status:
                tasks = [t for t in tasks if t.status == status]
            if priority:
                tasks = [t for t in tasks if t.priority == priority]
            if created_by:
                tasks = [t for t in tasks if t.created_by == created_by]
            if claimed_by:
                tasks = [t for t in tasks if t.claimed_by == claimed_by]
            if required_capability:
                tasks = [t for t in tasks if t.required_capability == required_capability]

            tasks.sort(key=lambda t: (PRIORITY_ORDER.get(t.priority, 99), t.created_at))
            return tasks[:limit]

    def get_open_tasks(self, limit: int = 10) -> List[BoardTask]:
        """Get tasks available for claiming"""
        return self.list(status=TaskStatus.OPEN, limit=limit)

    def get_my_tasks(self, node_id: str) -> List[BoardTask]:
        """Get tasks claimed by a specific edge"""
        return self.list(claimed_by=node_id, limit=50)

    def get_task(self, task_id: str) -> Optional[BoardTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def stats(self) -> Dict:
        with self._lock:
            by_status = {}
            by_type = {}
            for t in self._tasks.values():
                by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
                by_type[t.task_type] = by_type.get(t.task_type, 0) + 1

            return {
                "total": len(self._tasks),
                "by_status": by_status,
                "by_type": by_type,
                "open_for_claim": by_status.get("open", 0),
            }
