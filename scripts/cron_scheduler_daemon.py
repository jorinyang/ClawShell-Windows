#!/usr/bin/env python3
"""
ClawShell Cron Scheduler Daemon
================================
Reads cron_tasks.json and executes scripts on schedule.
Runs as a lightweight background process with minimal CPU overhead.

Usage:
  python3 cron_scheduler_daemon.py            # Run in background
  python3 cron_scheduler_daemon.py --once      # Run all due tasks once and exit
"""

import os
import sys
import json
import time
import signal
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# ── Configuration ──────────────────────────────────────────
REAL_BASE = Path("/mnt/c/Users/Aorus/.real")
CRON_FILE = REAL_BASE / "cron_tasks.json"
CLAWSHELL_SRC = Path("/mnt/c/Users/Aorus/.ClawShell")
LOG_DIR = REAL_BASE / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CronScheduler] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "cron_scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cron_scheduler")

# ── Cron Expression Parser ─────────────────────────────────
def cron_matches(schedule: str, dt: datetime = None) -> bool:
    """Simple cron expression matcher (minute hour day month weekday)"""
    if dt is None:
        dt = datetime.now()
    
    parts = schedule.strip().split()
    if len(parts) != 5:
        return False
    
    minute, hour, day, month, weekday = parts
    
    def _match(val: int, expr: str) -> bool:
        if expr == "*":
            return True
        if "/" in expr:
            base, step = expr.split("/")
            step = int(step)
            return val % step == 0
        if "," in expr:
            return val in [int(x) for x in expr.split(",")]
        if "-" in expr:
            lo, hi = expr.split("-")
            return int(lo) <= val <= int(hi)
        return val == int(expr)
    
    return (_match(dt.minute, minute) and
            _match(dt.hour, hour) and
            _match(dt.day, day) and
            _match(dt.month, month) and
            _match(dt.weekday(), weekday))


# ── Task Execution ─────────────────────────────────────────
def execute_task(task: Dict) -> bool:
    """Execute a single cron task"""
    script = task.get("script", "")
    name = task.get("name", script)
    script_path = CLAWSHELL_SRC / script
    
    if not script_path.exists():
        logger.warning(f"Script not found: {script_path}")
        return False
    
    logger.info(f"Executing: {name} ({script})")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=300,
            cwd=str(CLAWSHELL_SRC)
        )
        if result.returncode == 0:
            logger.info(f"  OK: {name}")
            return True
        else:
            logger.error(f"  FAIL ({result.returncode}): {name}\n  {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"  TIMEOUT: {name}")
        return False
    except Exception as e:
        logger.error(f"  ERROR: {name} - {e}")
        return False


# ── Main Loop ──────────────────────────────────────────────
last_run: Dict[str, datetime] = {}

def run_due_tasks(tasks: List[Dict]):
    """Check and run all due tasks"""
    now = datetime.now()
    for task in tasks:
        if not task.get("enabled", True):
            continue
        
        task_id = task["id"]
        schedule = task.get("schedule", "")
        
        # Check if due since last check (within last 2 minutes)
        if cron_matches(schedule, now):
            # Avoid duplicate execution within same minute
            if task_id not in last_run or (now - last_run[task_id]) > timedelta(minutes=59):
                last_run[task_id] = now
                execute_task(task)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ClawShell Cron Scheduler")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    args = parser.parse_args()
    
    if not CRON_FILE.exists():
        logger.error(f"Cron file not found: {CRON_FILE}")
        return 1
    
    tasks = json.loads(CRON_FILE.read_text()).get("tasks", [])
    enabled = sum(1 for t in tasks if t.get("enabled", True))
    logger.info(f"Cron scheduler started: {enabled}/{len(tasks)} tasks enabled")
    for t in tasks:
        status = "ON" if t.get("enabled", True) else "OFF"
        logger.info(f"  [{status}] {t['name']}: {t.get('schedule','?')}")
    
    if args.once:
        logger.info("Run-once mode: executing due tasks...")
        run_due_tasks(tasks)
        logger.info("Done.")
        return 0
    
    # Daemon mode
    def shutdown(sig, frame):
        logger.info("Shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    logger.info(f"Daemon mode: checking every {args.interval}s")
    while True:
        try:
            run_due_tasks(tasks)
            # Reload tasks periodically
            if CRON_FILE.exists():
                tasks = json.loads(CRON_FILE.read_text()).get("tasks", [])
        except Exception as e:
            logger.error(f"Loop error: {e}")
        
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
