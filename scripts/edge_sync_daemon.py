#!/usr/bin/env python3
"""
ClawShell Edge — Sync Daemon v1.1
==================================
Lightweight daemon that continuously syncs local events to Cloud,
pulls remote tasks, reports health, and manages offline queue.

Runs every 5 seconds. Minimal CPU (~0% idle).

Usage:
  python3 edge_sync_daemon.py              # Start daemon
  python3 edge_sync_daemon.py --once       # Run one sync cycle and exit
  python3 edge_sync_daemon.py --status     # Show status and exit
"""

import os
import sys
import json
import time
import signal
import socket
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ── Config ────────────────────────────────────────────────
REAL_BASE = Path(os.environ.get("REAL_BASE", "/mnt/c/Users/Aorus/.real"))
CLOUD_URL = os.environ.get("CLAWSHELL_CLOUD_URL", "http://127.0.0.1:17655")
NODE_ID = os.environ.get("CLAWSHELL_NODE_ID", socket.gethostname())
SYNC_INTERVAL = int(os.environ.get("CLAWSHELL_SYNC_INTERVAL", "5"))

EVENTBUS_DIR = REAL_BASE / "eventbus" / "events"
OFFLINE_QUEUE_FILE = REAL_BASE / "offline_events.json"
HEALTH_LOG = REAL_BASE / "logs" / "edge_sync.log"

EVENTBUS_DIR.mkdir(parents=True, exist_ok=True)
(REAL_BASE / "logs").mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [EdgeSync] %(message)s",
    handlers=[logging.FileHandler(HEALTH_LOG), logging.StreamHandler()]
)
logger = logging.getLogger("EdgeSync")


# ═══════════════════════════════════════════════════════════
# Cloud Client (minimal, no external deps)
# ═══════════════════════════════════════════════════════════

class CloudClient:
    def __init__(self, url: str, token: str = ""):
        self.url = url.rstrip("/")
        self.token = token

    def _req(self, method: str, path: str, data: dict = None) -> dict:
        import urllib.request
        try:
            body = json.dumps(data).encode() if data else None
            req = urllib.request.Request(
                f"{self.url}{path}", data=body,
                headers={"Content-Type": "application/json", "X-Edge-Token": self.token},
                method=method
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e)}

    def push_events(self, events: list) -> dict:
        return self._req("POST", "/api/v1/events/batch", {"events": events})

    def pull_tasks(self) -> dict:
        return self._req("GET", "/api/v1/tasks/?status=pending")

    def report_health(self, report: dict) -> dict:
        return self._req("POST", "/api/v1/health/report", report)


# ═══════════════════════════════════════════════════════════
# Offline Queue
# ═══════════════════════════════════════════════════════════

class OfflineQueue:
    def __init__(self):
        self.queue: List[dict] = self._load()

    def _load(self) -> list:
        if OFFLINE_QUEUE_FILE.exists():
            try:
                return json.loads(OFFLINE_QUEUE_FILE.read_text())
            except:
                pass
        return []

    def _save(self):
        OFFLINE_QUEUE_FILE.write_text(json.dumps(self.queue, indent=2))

    def enqueue(self, event: dict):
        self.queue.append(event)
        if len(self.queue) > 500:
            self.queue = self.queue[-300:]
        self._save()

    def flush(self, client: CloudClient) -> int:
        if not self.queue:
            return 0
        batch = self.queue[:50]
        result = client.push_events(batch)
        if "error" not in result:
            self.queue = self.queue[len(batch):]
            self._save()
            return len(batch)
        return 0

    def size(self) -> int:
        return len(self.queue)


# ═══════════════════════════════════════════════════════════
# Health Reporter
# ═══════════════════════════════════════════════════════════

class HealthReporter:
    def __init__(self):
        self.start_time = time.time()

    def check_services(self) -> dict:
        checks = {"mcp_bridge": 17655, "browser_runtime": 4240, "n8n": 5678}
        status = {}
        for name, port in checks.items():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1)
            r = s.connect_ex(('127.0.0.1', port))
            status[name] = "UP" if r == 0 else "DOWN"
            s.close()
        return status

    def get_report(self) -> dict:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
        except ImportError:
            cpu, mem, disk = 0, 0, 0

        return {
            "node_id": NODE_ID,
            "node_name": socket.gethostname(),
            "timestamp": datetime.now().isoformat(),
            "cpu_percent": cpu,
            "memory_percent": mem,
            "disk_percent": disk,
            "services": self.check_services(),
            "uptime_seconds": time.time() - self.start_time,
            "version": "1.1.0",
            "capabilities": ["eventbus", "mcp_bridge", "health", "self_repair", "obsidian"],
        }


# ═══════════════════════════════════════════════════════════
# Local Event Scanner
# ═══════════════════════════════════════════════════════════

class LocalEventScanner:
    def __init__(self):
        self.last_scanned: Dict[str, str] = {}  # filename → timestamp

    def scan_new_events(self) -> List[dict]:
        """Find events created since last scan"""
        new_events = []
        for date_dir in sorted(EVENTBUS_DIR.iterdir()):
            if not date_dir.is_dir():
                continue
            for ef in sorted(date_dir.iterdir()):
                if ef.suffix != ".json":
                    continue
                mtime = str(ef.stat().st_mtime)
                if self.last_scanned.get(ef.name) != mtime:
                    try:
                        ev = json.loads(ef.read_text())
                        new_events.append(ev)
                        self.last_scanned[ef.name] = mtime
                    except:
                        pass
        return new_events


# ═══════════════════════════════════════════════════════════
# Edge Sync Daemon
# ═══════════════════════════════════════════════════════════

class EdgeSyncDaemon:
    def __init__(self, cloud_url: str = None, node_id: str = None):
        self.cloud = CloudClient(cloud_url or CLOUD_URL)
        self.queue = OfflineQueue()
        self.health = HealthReporter()
        self.scanner = LocalEventScanner()
        self.running = False
        self.stats = {"events_synced": 0, "tasks_pulled": 0, "health_reports": 0,
                       "cycles": 0, "errors": 0, "started_at": datetime.now().isoformat()}

    def start(self):
        self.running = True
        logger.info(f"Edge Sync Daemon started (node={NODE_ID}, cloud={self.cloud.url}, interval={SYNC_INTERVAL}s)")
        signal.signal(signal.SIGINT, lambda s, f: self.stop())
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())

        while self.running:
            try:
                self._sync_cycle()
                self.stats["cycles"] += 1
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"Cycle error: {e}")
            time.sleep(SYNC_INTERVAL)

    def _sync_cycle(self):
        # 1. Scan new local events → enqueue
        new_events = self.scanner.scan_new_events()
        for ev in new_events:
            self.queue.enqueue(ev)

        # 2. Flush offline queue → cloud
        synced = self.queue.flush(self.cloud)
        if synced > 0:
            self.stats["events_synced"] += synced
            logger.info(f"Synced {synced} events, {self.queue.size()} queued")

        # 3. Pull remote tasks
        tasks = self.cloud.pull_tasks()
        if "tasks" in tasks and tasks["tasks"]:
            self.stats["tasks_pulled"] += len(tasks["tasks"])
            logger.info(f"Pulled {len(tasks['tasks'])} pending tasks")

        # 4. Health report (every 10 cycles ≈ 50s)
        if self.stats["cycles"] % 10 == 0:
            self.cloud.report_health(self.health.get_report())
            self.stats["health_reports"] += 1

    def stop(self):
        self.running = False
        logger.info(f"Stopping. Stats: {json.dumps(self.stats, indent=2)}")
        sys.exit(0)

    def run_once(self):
        """Run a single sync cycle and exit"""
        self._sync_cycle()
        print(json.dumps(self.stats, indent=2))

    def status(self) -> dict:
        return {
            **self.stats,
            "node_id": NODE_ID,
            "cloud_url": self.cloud.url,
            "offline_queue": self.queue.size(),
            "services": self.health.check_services(),
        }


# ═══ CLI ══════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="ClawShell Edge Sync Daemon")
    parser.add_argument("--once", action="store_true", help="Run one sync cycle")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--cloud-url", type=str, default=CLOUD_URL)
    parser.add_argument("--interval", type=int, default=SYNC_INTERVAL)
    args = parser.parse_args()

    interval = args.interval
    daemon = EdgeSyncDaemon(cloud_url=args.cloud_url)

    if args.status:
        print(json.dumps(daemon.status(), indent=2))
    elif args.once:
        daemon.run_once()
    else:
        daemon.start()


if __name__ == "__main__":
    main()
