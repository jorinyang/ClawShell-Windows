"""
ClawShell Cloud — TaskMarket Engine v2.0
=========================================
Cloud-side task orchestration with CRUD, state machine,
priority queue, agent matching, and assignment.

Tasks flow:
  pending → in_progress → completed / failed / cancelled
"""

import json
import uuid
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field, asdict


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


PRIORITY_ORDER = {
    TaskPriority.CRITICAL: 0,
    TaskPriority.HIGH: 1,
    TaskPriority.MEDIUM: 2,
    TaskPriority.LOW: 3,
}


@dataclass
class TaskRecord:
    task_id: str = ""
    task_type: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_by: str = ""
    assigned_to: str = ""
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["status"] = self.status.value
        d["priority"] = self.priority.value
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "TaskRecord":
        data = dict(data)
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TaskStatus(data["status"])
        if "priority" in data and isinstance(data["priority"], str):
            data["priority"] = TaskPriority(data["priority"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CloudTaskMarket:
    """
    Cloud-side TaskMarket — manages task lifecycle across edge nodes.

    Valid state transitions:
      pending → in_progress
      pending → cancelled
      in_progress → completed
      in_progress → failed
    """

    # Allowed transitions
    TRANSITIONS = {
        TaskStatus.PENDING: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
        TaskStatus.IN_PROGRESS: {TaskStatus.COMPLETED, TaskStatus.FAILED},
        TaskStatus.COMPLETED: set(),
        TaskStatus.FAILED: set(),
        TaskStatus.CANCELLED: set(),
    }

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.tasks_dir = self.data_dir / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        self._tasks: Dict[str, TaskRecord] = {}
        self._lock = threading.Lock()
        self._load_all()

    # ── Persistence ───────────────────────────────────────

    def _save(self, task: TaskRecord):
        filepath = self.tasks_dir / f"{task.task_id}.json"
        filepath.write_text(json.dumps(task.to_dict(), indent=2, ensure_ascii=False))

    def _load_all(self):
        with self._lock:
            for f in self.tasks_dir.glob("*.json"):
                try:
                    task = TaskRecord.from_dict(json.loads(f.read_text()))
                    self._tasks[task.task_id] = task
                except:
                    pass

    # ── CRUD ──────────────────────────────────────────────

    def create(self, task_type: str, priority: TaskPriority = TaskPriority.MEDIUM,
               created_by: str = "system", payload: Dict = None,
               tags: List[str] = None) -> TaskRecord:
        """Create a new task"""
        task = TaskRecord(
            task_id=str(uuid.uuid4())[:8],
            task_type=task_type,
            status=TaskStatus.PENDING,
            priority=priority,
            created_by=created_by,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            payload=payload or {},
            tags=tags or [],
        )
        with self._lock:
            self._tasks[task.task_id] = task
            self._save(task)
        return task

    def get(self, task_id: str) -> Optional[TaskRecord]:
        with self._lock:
            return self._tasks.get(task_id)

    def update(self, task_id: str, **kwargs) -> Optional[TaskRecord]:
        """Update task fields. Status changes validated via state machine."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            new_status = kwargs.get("status")
            if new_status and isinstance(new_status, str):
                new_status = TaskStatus(new_status)

            # Validate state transition
            if new_status and new_status not in self.TRANSITIONS.get(task.status, set()):
                raise ValueError(
                    f"Invalid transition: {task.status.value} → {new_status.value}. "
                    f"Allowed: {[s.value for s in self.TRANSITIONS.get(task.status, set())]}"
                )

            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)

            task.updated_at = datetime.now().isoformat()
            if task.status == TaskStatus.COMPLETED:
                task.completed_at = datetime.now().isoformat()

            self._save(task)
            return task

    def delete(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                filepath = self.tasks_dir / f"{task_id}.json"
                if filepath.exists():
                    filepath.unlink()
                return True
        return False

    # ── Query ─────────────────────────────────────────────

    def list(self, status: TaskStatus = None, priority: TaskPriority = None,
             task_type: str = None, assigned_to: str = None,
             limit: int = 50) -> List[TaskRecord]:
        """List tasks with optional filters"""
        with self._lock:
            tasks = list(self._tasks.values())

            if status:
                tasks = [t for t in tasks if t.status == status]
            if priority:
                tasks = [t for t in tasks if t.priority == priority]
            if task_type:
                tasks = [t for t in tasks if t.task_type == task_type]
            if assigned_to:
                tasks = [t for t in tasks if t.assigned_to == assigned_to]

            # Sort: priority DESC, created_at ASC
            tasks.sort(key=lambda t: (PRIORITY_ORDER.get(t.priority, 99), t.created_at))
            return tasks[:limit]

    def get_next_pending(self, task_type: str = None) -> Optional[TaskRecord]:
        """Get highest priority pending task"""
        pending = self.list(status=TaskStatus.PENDING, task_type=task_type, limit=1)
        return pending[0] if pending else None

    # ── Agent Matching & Assignment ───────────────────────

    def claim(self, agent_id: str, task_type: str = None) -> Optional[TaskRecord]:
        """Agent claims the highest priority available task"""
        task = self.get_next_pending(task_type=task_type)
        if task:
            self.update(task.task_id, status=TaskStatus.IN_PROGRESS, assigned_to=agent_id)
            task = self.get(task.task_id)
        return task

    def complete(self, task_id: str, result: Dict = None) -> Optional[TaskRecord]:
        """Mark task as completed with result"""
        return self.update(task_id, status=TaskStatus.COMPLETED, result=result)

    def fail(self, task_id: str, error: str = None) -> Optional[TaskRecord]:
        """Mark task as failed"""
        return self.update(task_id, status=TaskStatus.FAILED,
                          result={"error": error} if error else None)

    def cancel(self, task_id: str) -> Optional[TaskRecord]:
        """Cancel a pending task"""
        return self.update(task_id, status=TaskStatus.CANCELLED)

    # ── Stats ─────────────────────────────────────────────

    def stats(self) -> Dict:
        """Get TaskMarket statistics"""
        with self._lock:
            by_status = {}
            by_type = {}
            by_priority = {}
            for t in self._tasks.values():
                by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
                by_type[t.task_type] = by_type.get(t.task_type, 0) + 1
                by_priority[t.priority.value] = by_priority.get(t.priority.value, 0) + 1

            return {
                "total": len(self._tasks),
                "by_status": by_status,
                "by_type": by_type,
                "by_priority": by_priority,
            }
