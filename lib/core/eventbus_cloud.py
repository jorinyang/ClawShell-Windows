"""
ClawShell Cloud — EventBus Engine v2.0
=======================================
Persistent event storage with query, dedup, expiry, and stats.

Storage layout:
  data/eventbus/
    YYYY-MM-DD/
      {timestamp}_{source}_{event_type}.json

Features:
  - JSON file per event, organized by date
  - In-memory index for fast queries
  - SHA256 deduplication
  - 30-day auto-expiry
  - Type/source/tag aggregation stats
"""

import json
import hashlib
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class EventRecord:
    event_id: str
    event_type: str
    source: str
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    edge_node_id: str = ""
    content_hash: str = ""

    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "source": self.source,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "tags": self.tags,
            "edge_node_id": self.edge_node_id,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "EventRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class CloudEventBus:
    """
    Cloud-side EventBus — the single source of truth for all events.

    Usage:
        bus = CloudEventBus(data_dir="/app/data")
        bus.store(event)
        results = bus.query(pattern="clawshell.task.*", limit=20)
        stats = bus.stats()
    """

    def __init__(self, data_dir: Path = None, retention_days: int = 30):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.eventbus_dir = self.data_dir / "eventbus"
        self.events_dir = self.eventbus_dir / "events"
        self.events_dir.mkdir(parents=True, exist_ok=True)

        self.retention_days = retention_days
        self._index: Dict[str, Dict] = {}  # event_id → {date, filename, type, source, ts}
        self._lock = threading.Lock()
        self._stats = defaultdict(int)
        self._build_index()
        self._expire_loop_running = False

    # ── Persistence ───────────────────────────────────────

    def store(self, event: EventRecord) -> str:
        """Store an event to disk and index"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%f")[:23]

        if not event.event_id:
            event.event_id = f"{ts}_{event.source}_{event.event_type.replace('.', '_')}"
        if not event.timestamp:
            event.timestamp = datetime.now().isoformat()

        # Dedup check
        event.content_hash = self._compute_hash(event.to_dict())
        if self._is_duplicate(event.content_hash):
            return "duplicate"

        date_dir = self.events_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{event.event_id}.json"
        filepath = date_dir / filename

        event_dict = event.to_dict()
        event_dict["content_hash"] = event.content_hash
        filepath.write_text(json.dumps(event_dict, ensure_ascii=False, indent=2))

        # Update index
        with self._lock:
            self._index[event.event_id] = {
                "date": date_str,
                "filename": filename,
                "event_type": event.event_type,
                "source": event.source,
                "timestamp": event.timestamp,
                "hash": event.content_hash,
            }
            self._stats["total"] += 1
            self._stats[f"type:{event.event_type}"] += 1
            self._stats[f"source:{event.source}"] += 1

        # Start expiry loop if not running
        if not self._expire_loop_running:
            self._start_expiry()

        return "stored"

    def _compute_hash(self, data: Dict) -> str:
        """SHA256 hash for dedup"""
        content = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content.encode()).hexdigest()

    def _is_duplicate(self, content_hash: str) -> bool:
        """Check if event with same hash already exists"""
        with self._lock:
            for entry in self._index.values():
                if entry.get("hash") == content_hash:
                    return True
        return False

    # ── Query ─────────────────────────────────────────────

    def query(
        self,
        pattern: str = None,
        source: str = None,
        event_type: str = None,
        start_time: str = None,
        end_time: str = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict]:
        """Query events with multiple filters"""
        results = []
        with self._lock:
            # Sort by timestamp descending
            sorted_events = sorted(
                self._index.items(),
                key=lambda x: x[1].get("timestamp", ""),
                reverse=True,
            )

            for event_id, meta in sorted_events:
                # Apply filters
                if pattern and not self._match_pattern(meta.get("event_type", ""), pattern):
                    continue
                if source and meta.get("source") != source:
                    continue
                if event_type and meta.get("event_type") != event_type:
                    continue
                if start_time and meta.get("timestamp", "") < start_time:
                    continue
                if end_time and meta.get("timestamp", "") > end_time:
                    continue

                results.append(self._load_event(meta["date"], meta["filename"]))

                if len(results) >= limit + offset:
                    break

        self._stats["queries"] += 1
        return results[offset:offset + limit] if offset else results[:limit]

    def _match_pattern(self, event_type: str, pattern: str) -> bool:
        """Simple wildcard pattern matching: clawshell.task.*"""
        import fnmatch
        return fnmatch.fnmatch(event_type, pattern)

    def _load_event(self, date_str: str, filename: str) -> Dict:
        """Load a single event from disk"""
        filepath = self.events_dir / date_str / filename
        if filepath.exists():
            try:
                return json.loads(filepath.read_text())
            except:
                pass
        return {}

    # ── Stats ─────────────────────────────────────────────

    def stats(self) -> Dict:
        """Get EventBus statistics"""
        with self._lock:
            type_counts = {}
            source_counts = {}
            for k, v in self._stats.items():
                if k.startswith("type:"):
                    type_counts[k[5:]] = v
                elif k.startswith("source:"):
                    source_counts[k[7:]] = v

            return {
                "total_events": self._stats["total"],
                "total_queries": self._stats.get("queries", 0),
                "by_type": dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
                "by_source": dict(sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
                "retention_days": self.retention_days,
                "storage_path": str(self.events_dir),
            }

    # ── Expiry ────────────────────────────────────────────

    def _start_expiry(self):
        """Start background expiry cleaner"""
        self._expire_loop_running = True
        t = threading.Thread(target=self._expire_loop, daemon=True)
        t.start()

    def _expire_loop(self):
        """Periodically clean expired events"""
        while self._expire_loop_running:
            try:
                self._clean_expired()
            except Exception as e:
                print(f"[EventBus] Expiry error: {e}")
            time.sleep(3600)  # Check every hour

    def _clean_expired(self):
        """Remove events older than retention_days"""
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        cutoff_str = cutoff.strftime("%Y-%m-%d")

        with self._lock:
            to_remove = []
            for event_id, meta in self._index.items():
                if meta["date"] < cutoff_str:
                    to_remove.append((event_id, meta["date"], meta["filename"]))

            for event_id, date_str, filename in to_remove:
                filepath = self.events_dir / date_str / filename
                if filepath.exists():
                    filepath.unlink()
                del self._index[event_id]

            if to_remove:
                # Clean empty date directories
                for date_str in set(d for _, d, _ in to_remove):
                    date_dir = self.events_dir / date_str
                    try:
                        if date_dir.exists() and not any(date_dir.iterdir()):
                            date_dir.rmdir()
                    except:
                        pass

                self._stats["expired"] += len(to_remove)
                print(f"[EventBus] Expired {len(to_remove)} events older than {cutoff_str}")

    # ── Index Management ──────────────────────────────────

    def _build_index(self):
        """Rebuild in-memory index from disk"""
        with self._lock:
            self._index.clear()
            for date_dir in sorted(self.events_dir.iterdir()):
                if not date_dir.is_dir():
                    continue
                for event_file in date_dir.iterdir():
                    if event_file.suffix != ".json":
                        continue
                    try:
                        ev = json.loads(event_file.read_text())
                        event_id = ev.get("event_id", event_file.stem)
                        self._index[event_id] = {
                            "date": date_dir.name,
                            "filename": event_file.name,
                            "event_type": ev.get("event_type", "unknown"),
                            "source": ev.get("source", "unknown"),
                            "timestamp": ev.get("timestamp", ""),
                            "hash": ev.get("content_hash", ""),
                        }
                        self._stats["total"] += 1
                        self._stats[f"type:{ev.get('event_type', 'unknown')}"] += 1
                        self._stats[f"source:{ev.get('source', 'unknown')}"] += 1
                    except:
                        pass

    def get_index_size(self) -> int:
        with self._lock:
            return len(self._index)

    def shutdown(self):
        self._expire_loop_running = False
