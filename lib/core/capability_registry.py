"""
ClawShell Cloud — Capability Registry v1.1
============================================
Cloud-side edge registration hub. Edges register with their
capabilities, resources, and status. Cloud actively schedules
tasks based on edge capabilities.

Data stored in: data/capability_registry.json
"""

import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict


HEARTBEAT_TIMEOUT = 60  # seconds


@dataclass
class EdgeCapability:
    """An edge node's registered capabilities"""
    node_id: str
    node_name: str = ""
    hostname: str = ""
    version: str = "1.1.0"
    status: str = "online"  # online, busy, idle, offline
    capabilities: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    resources: Dict = field(default_factory=dict)
    current_tasks: int = 0
    max_tasks: int = 5
    registered_at: str = ""
    last_heartbeat: str = ""
    last_task_completed: Optional[str] = None
    total_tasks_completed: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "EdgeCapability":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CapabilityRegistry:
    """Cloud-side edge capability registry with active scheduling."""

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.registry_file = self.data_dir / "capability_registry.json"
        self._edges: Dict[str, EdgeCapability] = {}
        self._lock = threading.Lock()
        self._running = False
        self._load()
        self._start_cleanup()

    def _save(self):
        with self._lock:
            data = {nid: e.to_dict() for nid, e in self._edges.items()}
            self.registry_file.write_text(json.dumps({
                "edges": data,
                "updated_at": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))

    def _load(self):
        if self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text())
                with self._lock:
                    for nid, nd in data.get("edges", {}).items():
                        self._edges[nid] = EdgeCapability.from_dict(nd)
            except:
                pass

    # ═══ Registration ══════════════════════════════════════

    def register(self, node_id: str, node_name: str = "",
                 capabilities: List[str] = None, skills: List[str] = None,
                 resources: Dict = None, hostname: str = "",
                 version: str = "1.1.0") -> EdgeCapability:
        """Register or update an edge node with its capabilities"""
        now = datetime.now().isoformat()
        with self._lock:
            if node_id in self._edges:
                edge = self._edges[node_id]
                edge.last_heartbeat = now
                edge.version = version
                if capabilities:
                    edge.capabilities = capabilities
                if skills:
                    edge.skills = skills
                if resources:
                    edge.resources = resources
            else:
                edge = EdgeCapability(
                    node_id=node_id, node_name=node_name or node_id,
                    hostname=hostname, version=version,
                    capabilities=capabilities or [],
                    skills=skills or [],
                    resources=resources or {},
                    registered_at=now, last_heartbeat=now
                )
                self._edges[node_id] = edge
            self._save()
        return edge

    def heartbeat(self, node_id: str, current_tasks: int = 0) -> bool:
        """Receive heartbeat, update status"""
        with self._lock:
            edge = self._edges.get(node_id)
            if not edge:
                return False
            edge.last_heartbeat = datetime.now().isoformat()
            edge.current_tasks = current_tasks
            if current_tasks >= edge.max_tasks:
                edge.status = "busy"
            elif current_tasks > 0:
                edge.status = "online"
            else:
                edge.status = "idle"
            return True

    def task_completed(self, node_id: str):
        """Record task completion for an edge"""
        with self._lock:
            edge = self._edges.get(node_id)
            if edge:
                edge.total_tasks_completed += 1
                edge.last_task_completed = datetime.now().isoformat()
                edge.current_tasks = max(0, edge.current_tasks - 1)
                if edge.current_tasks == 0:
                    edge.status = "idle"

    # ═══ Active Scheduling ═════════════════════════════════

    def find_best_edge(self, required_capability: str = None,
                       required_skill: str = None) -> Optional[str]:
        """Find the best edge for a task based on capabilities"""
        with self._lock:
            candidates = []
            for edge in self._edges.values():
                if edge.status == "offline":
                    continue
                if edge.current_tasks >= edge.max_tasks:
                    continue
                if required_capability and required_capability not in edge.capabilities:
                    continue
                if required_skill and required_skill not in edge.skills:
                    continue
                candidates.append(edge)

            if not candidates:
                return None

            # Least-loaded first
            candidates.sort(key=lambda e: e.current_tasks)
            return candidates[0].node_id

    def assign_task(self, task_id: str, required_capability: str = None,
                    required_skill: str = None) -> Optional[str]:
        """Assign a task to the best available edge"""
        best = self.find_best_edge(required_capability, required_skill)
        if best:
            with self._lock:
                self._edges[best].current_tasks += 1
                if self._edges[best].current_tasks >= self._edges[best].max_tasks:
                    self._edges[best].status = "busy"
                else:
                    self._edges[best].status = "online"
            self._save()
        return best

    # ═══ Query ═════════════════════════════════════════════

    def get_edge(self, node_id: str) -> Optional[EdgeCapability]:
        with self._lock:
            return self._edges.get(node_id)

    def list_edges(self, status: str = None) -> List[EdgeCapability]:
        with self._lock:
            edges = list(self._edges.values())
            if status:
                edges = [e for e in edges if e.status == status]
            return sorted(edges, key=lambda e: e.node_id)

    def list_capabilities(self) -> Dict[str, List[str]]:
        """Get all unique capabilities and which edges have them"""
        caps = {}
        with self._lock:
            for edge in self._edges.values():
                for cap in edge.capabilities:
                    caps.setdefault(cap, []).append(edge.node_id)
                for skill in edge.skills:
                    caps.setdefault(f"skill:{skill}", []).append(edge.node_id)
        return caps

    def stats(self) -> Dict:
        with self._lock:
            by_status = {}
            total_caps = set()
            total_skills = set()
            for e in self._edges.values():
                by_status[e.status] = by_status.get(e.status, 0) + 1
                total_caps.update(e.capabilities)
                total_skills.update(e.skills)

            return {
                "total_edges": len(self._edges),
                "by_status": by_status,
                "unique_capabilities": len(total_caps),
                "unique_skills": len(total_skills),
                "total_tasks_completed": sum(e.total_tasks_completed for e in self._edges.values()),
            }

    # ═══ Cleanup ═══════════════════════════════════════════

    def _start_cleanup(self):
        self._running = True
        t = threading.Thread(target=self._cleanup_loop, daemon=True)
        t.start()

    def _cleanup_loop(self):
        while self._running:
            try:
                self._detect_offline()
            except:
                pass
            for _ in range(int(HEARTBEAT_TIMEOUT / 5)):
                if not self._running:
                    break
                time.sleep(5)

    def _detect_offline(self):
        cutoff = datetime.now() - timedelta(seconds=HEARTBEAT_TIMEOUT)
        changed = False
        with self._lock:
            for e in self._edges.values():
                if e.status != "offline":
                    try:
                        hb = datetime.fromisoformat(e.last_heartbeat)
                        if hb < cutoff:
                            e.status = "offline"
                            changed = True
                    except:
                        pass
        if changed:
            self._save()

    def shutdown(self):
        self._running = False
