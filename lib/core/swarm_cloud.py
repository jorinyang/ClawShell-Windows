"""
ClawShell Cloud — Swarm Coordinator v2.0
=========================================
Multi-edge node management: registration, heartbeat,
offline detection, and task load balancing.
"""

import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class NodeStatus(str, Enum):
    ONLINE = "online"
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class EdgeNode:
    node_id: str
    node_name: str = ""
    hostname: str = ""
    version: str = "2.0.0"
    capabilities: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.ONLINE
    current_tasks: int = 0
    max_tasks: int = 5
    last_heartbeat: str = ""
    registered_at: str = ""
    ip_address: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "EdgeNode":
        data = dict(data)
        if "status" in data and isinstance(data["status"], str):
            data["status"] = NodeStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SwarmCoordinator:
    """
    Cloud-side swarm coordinator — manages the fleet of edge nodes.

    Features:
      - Node registration with capability declaration
      - Heartbeat monitoring (configurable timeout)
      - Automatic offline detection
      - Round-robin + least-loaded task assignment
    """

    HEARTBEAT_TIMEOUT = 30  # seconds
    CLEANUP_INTERVAL = 60   # seconds

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.registry_file = self.data_dir / "swarm_registry.json"
        self._nodes: Dict[str, EdgeNode] = {}
        self._lock = threading.Lock()
        self._running = False
        self._load()
        self._start_cleanup()

    def _save(self):
        with self._lock:
            nodes_dict = {nid: n.to_dict() for nid, n in self._nodes.items()}
            self.registry_file.write_text(json.dumps({
                "nodes": nodes_dict,
                "updated_at": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))

    def _load(self):
        if self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text())
                with self._lock:
                    for nid, nd in data.get("nodes", {}).items():
                        self._nodes[nid] = EdgeNode.from_dict(nd)
            except:
                pass

    # ── Registration ──────────────────────────────────────

    def register(self, node_id: str, node_name: str = "", capabilities: List[str] = None,
                 hostname: str = "", version: str = "2.0.0") -> EdgeNode:
        """Register a new edge node or update existing"""
        now = datetime.now().isoformat()
        with self._lock:
            if node_id in self._nodes:
                node = self._nodes[node_id]
                node.status = NodeStatus.ONLINE
                node.last_heartbeat = now
                if capabilities:
                    node.capabilities = capabilities
            else:
                node = EdgeNode(
                    node_id=node_id,
                    node_name=node_name or node_id,
                    hostname=hostname,
                    version=version,
                    capabilities=capabilities or [],
                    status=NodeStatus.ONLINE,
                    last_heartbeat=now,
                    registered_at=now,
                )
                self._nodes[node_id] = node
            self._save()
        return node

    def deregister(self, node_id: str) -> bool:
        with self._lock:
            if node_id in self._nodes:
                self._nodes[node_id].status = NodeStatus.OFFLINE
                self._save()
                return True
        return False

    # ── Heartbeat ─────────────────────────────────────────

    def heartbeat(self, node_id: str, current_tasks: int = 0,
                  cpu_percent: float = 0, memory_percent: float = 0) -> bool:
        """Receive heartbeat from edge node"""
        with self._lock:
            node = self._nodes.get(node_id)
            if not node:
                return False
            node.last_heartbeat = datetime.now().isoformat()
            node.current_tasks = current_tasks
            node.cpu_percent = cpu_percent
            node.memory_percent = memory_percent

            # Update status based on load
            if current_tasks >= node.max_tasks:
                node.status = NodeStatus.BUSY
            elif current_tasks > 0:
                node.status = NodeStatus.ONLINE
            else:
                node.status = NodeStatus.IDLE
            return True

    # ── Offline Detection ─────────────────────────────────

    def _start_cleanup(self):
        self._running = True
        t = threading.Thread(target=self._cleanup_loop, daemon=True)
        t.start()

    def _cleanup_loop(self):
        while self._running:
            try:
                self._detect_offline_nodes()
            except Exception as e:
                print(f"[Swarm] Cleanup error: {e}")
            # Check every 5s for faster shutdown
            for _ in range(int(self.CLEANUP_INTERVAL / 5)):
                if not self._running:
                    break
                time.sleep(5)

    def _detect_offline_nodes(self):
        """Mark nodes as offline if heartbeat timeout exceeded"""
        cutoff = datetime.now() - timedelta(seconds=self.HEARTBEAT_TIMEOUT)
        with self._lock:
            changed = False
            for node in self._nodes.values():
                if node.status != NodeStatus.OFFLINE:
                    try:
                        hb = datetime.fromisoformat(node.last_heartbeat)
                        if hb < cutoff:
                            node.status = NodeStatus.OFFLINE
                            changed = True
                    except:
                        pass
            if changed:
                self._save()

    # ── Task Assignment ───────────────────────────────────

    def get_available_nodes(self, capability: str = None) -> List[EdgeNode]:
        """Get nodes available for task assignment"""
        with self._lock:
            available = [
                n for n in self._nodes.values()
                if n.status in (NodeStatus.ONLINE, NodeStatus.IDLE)
                and n.current_tasks < n.max_tasks
            ]
            if capability:
                available = [n for n in available if capability in n.capabilities]
            return available

    def assign_task(self, capability: str = None) -> Optional[str]:
        """
        Pick the best node for a new task.
        Strategy: least-loaded first, then round-robin.
        """
        available = self.get_available_nodes(capability)
        if not available:
            return None

        # Sort by current_tasks ascending (least loaded first)
        available.sort(key=lambda n: n.current_tasks)
        return available[0].node_id

    # ── Query ─────────────────────────────────────────────

    def get_node(self, node_id: str) -> Optional[EdgeNode]:
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(self, status: NodeStatus = None) -> List[EdgeNode]:
        with self._lock:
            nodes = list(self._nodes.values())
            if status:
                nodes = [n for n in nodes if n.status == status]
            return sorted(nodes, key=lambda n: n.node_id)

    def stats(self) -> Dict:
        with self._lock:
            by_status = {}
            total_tasks = 0
            for n in self._nodes.values():
                by_status[n.status.value] = by_status.get(n.status.value, 0) + 1
                total_tasks += n.current_tasks

            return {
                "total_nodes": len(self._nodes),
                "by_status": by_status,
                "active_tasks": total_tasks,
                "available_for_assignment": len(self.get_available_nodes()),
            }

    def shutdown(self):
        self._running = False
