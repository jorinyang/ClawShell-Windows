"""
ClawShell Cloud — Cron Scheduler v2.0
======================================
Cloud-side task scheduler with cron expression support.
"""

import json
import time
import threading
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Callable

logger = logging.getLogger("CloudScheduler")


class CronScheduler:
    """
    Cloud cron scheduler — executes registered tasks on schedule.

    Cron format: minute hour day month weekday (standard 5-field)
    Supports: *, */N, comma-separated, ranges, exact values
    """

    def __init__(self):
        self._tasks: List[Dict] = []
        self._running = False
        self._thread = None
        self._execution_log: List[Dict] = []
        self._last_run: Dict[str, datetime] = {}

    def load_tasks(self, tasks: List[Dict]):
        """Load tasks from configuration"""
        self._tasks = [t for t in tasks if t.get("enabled", True)]
        logger.info(f"Loaded {len(self._tasks)} cron tasks")

    def add_task(self, name: str, schedule: str, handler: Callable, enabled: bool = True):
        """Add a single cron task"""
        self._tasks.append({
            "name": name,
            "schedule": schedule,
            "handler": handler,
            "enabled": enabled,
        })

    def start(self, interval: int = 60):
        """Start the scheduler loop"""
        self._running = True
        self._thread = threading.Thread(target=self._loop, args=(interval,), daemon=True)
        self._thread.start()
        logger.info(f"Cron scheduler started: {len(self._tasks)} tasks, {interval}s interval")

    def stop(self):
        self._running = False
        logger.info("Cron scheduler stopped")

    def _loop(self, interval: int):
        while self._running:
            try:
                self._check_and_execute()
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
            time.sleep(interval)

    def _check_and_execute(self):
        now = datetime.now()
        for task in self._tasks:
            if not task.get("enabled", True):
                continue
            if self._cron_matches(task["schedule"], now):
                task_name = task["name"]
                # Avoid re-execution within the same minute
                last = self._last_run.get(task_name)
                if last and (now - last).total_seconds() < 60:
                    continue

                self._last_run[task_name] = now
                try:
                    start = time.time()
                    result = task["handler"]()
                    elapsed = time.time() - start
                    self._log_execution(task_name, "success", elapsed)
                except Exception as e:
                    self._log_execution(task_name, "failed", 0, str(e))

    def _cron_matches(self, schedule: str, dt: datetime) -> bool:
        """Check if cron expression matches current time"""
        parts = schedule.strip().split()
        if len(parts) != 5:
            return False

        minute, hour, day, month, weekday = parts

        def _match(val: int, expr: str) -> bool:
            if expr == "*":
                return True
            if "/" in expr:
                _, step = expr.split("/")
                return val % int(step) == 0
            if "," in expr:
                return val in [int(x) for x in expr.split(",")]
            if "-" in expr:
                lo, hi = expr.split("-")
                return int(lo) <= val <= int(hi)
            return val == int(expr)

        return (
            _match(dt.minute, minute)
            and _match(dt.hour, hour)
            and _match(dt.day, day)
            and _match(dt.month, month)
            and _match(dt.weekday(), weekday)
        )

    def _log_execution(self, task_name: str, status: str, elapsed: float, error: str = ""):
        entry = {
            "task": task_name,
            "status": status,
            "elapsed_ms": round(elapsed * 1000),
            "timestamp": datetime.now().isoformat(),
        }
        if error:
            entry["error"] = error[:200]
        self._execution_log.append(entry)
        if len(self._execution_log) > 1000:
            self._execution_log = self._execution_log[-500:]

    def get_logs(self, limit: int = 20) -> List[Dict]:
        return self._execution_log[-limit:]
