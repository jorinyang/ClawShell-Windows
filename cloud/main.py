#!/usr/bin/env python3
"""
ClawShell Cloud Hub — FastAPI Unified Entry Point v1.1
=======================================================
章鱼主脑：统一整合所有云枢引擎，提供REST API + WebSocket。

Components:
  - CloudEventBus   → 事件持久化/查询/广播
  - CloudTaskMarket → 任务状态机/优先级/分发
  - SwarmCoordinator→ 节点管理/心跳/负载
  - CronScheduler   → 定时任务调度
  - CapabilityRegistry → Edge注册/能力管理
  - TaskBoard       → 跨Edge任务共享
  - SkillMarket     → 技能发布/发现/同步
  - N8NBridge       → N8N工作流集成
  - VaultAPI        → Obsidian+OSS Vault

Usage:
  python cloud/main.py                     # Start with default config
  CLAWSHELL_CLOUD_PORT=8000 python cloud/main.py
"""

import os
import json
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# ── FastAPI ─────────────────────────────────────────────────
try:
    from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    print("[WARN] FastAPI/uvicorn not installed. Run: pip install fastapi uvicorn")

# ── Config ──────────────────────────────────────────────────
CLOUD_PORT = int(os.environ.get("CLAWSHELL_CLOUD_PORT", "8000"))
CLOUD_HOST = os.environ.get("CLAWSHELL_CLOUD_HOST", "0.0.0.0")
DATA_DIR = Path(os.environ.get("CLAWSHELL_DATA_DIR", Path(__file__).parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CloudHub] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("CloudHub")

# ── Cloud Engine Imports (stdlib-only, self-contained) ──────
# Each engine is a standalone Python module with zero external deps.
# They all follow the same pattern: thread-safe, JSON-persisted, daemon-cleanup.

_engines = {}

def _load_engine(name: str, module_path: str, class_name: str):
    """Lazy-load a cloud engine module."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, module_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls = getattr(mod, class_name)
        instance = cls(data_dir=DATA_DIR)
        logger.info(f"  ✅ {name} loaded ({class_name})")
        return instance
    except Exception as e:
        logger.warning(f"  ⚠️  {name} failed: {e}")
        return None


def init_engines():
    """Initialize all cloud engines."""
    base = Path(__file__).parent.parent
    lib_core = base / "lib" / "core"
    lib_services = base / "lib" / "services"

    engines_to_load = [
        ("EventBus",       lib_core / "eventbus_cloud.py",     "CloudEventBus"),
        ("TaskMarket",     lib_core / "task_market_cloud.py",  "CloudTaskMarket"),
        ("Swarm",          lib_core / "swarm_cloud.py",        "SwarmCoordinator"),
        ("Scheduler",      lib_core / "scheduler_cloud.py",    "CronScheduler"),
        ("CapRegistry",    lib_core / "capability_registry.py","CapabilityRegistry"),
        ("TaskBoard",      lib_core / "task_board.py",         "GlobalTaskBoard"),
        ("SkillMarket",    lib_core / "skill_market.py",       "SkillMarket"),
        ("N8NBridge",      lib_services / "n8n_bridge.py",     "N8NBridge"),
        ("VaultAPI",       lib_services / "vault_api.py",      "VaultAPI"),
    ]

    for name, path, cls_name in engines_to_load:
        if path.exists():
            _engines[name] = _load_engine(name, str(path), cls_name)
        else:
            logger.debug(f"  ⊘ {name} — module not found at {path}")

    loaded = sum(1 for v in _engines.values() if v is not None)
    logger.info(f"CloudHub initialized: {loaded}/{len(engines_to_load)} engines loaded")

# ── FastAPI App ─────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="ClawShell Cloud Hub",
        description="章鱼主脑 — 云边协同中枢",
        version="1.1.0"
    )
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    # ── Health ──────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": "1.1.0",
            "engines": {k: "loaded" if v else "down" for k, v in _engines.items()},
            "timestamp": datetime.now().isoformat()
        }

    # ── EventBus ────────────────────────────────────────────
    eb = _engines.get("EventBus")

    @app.post("/api/v1/events/batch")
    async def events_batch(request: Request):
        body = await request.json()
        events = body.get("events", [])
        if eb:
            results = []
            for ev in events:
                eid = eb.publish(ev.get("type", "unknown"), ev.get("payload", {}),
                                 source=ev.get("source", ""))
                results.append(eid)
            return {"status": "ok", "event_ids": results, "count": len(results)}
        return {"status": "engine_unavailable"}, 503

    @app.get("/api/v1/events/")
    async def events_query(q: str = "*", limit: int = 50):
        if eb:
            events = eb.query(q, limit=limit)
            return {"events": events, "count": len(events)}
        return {"status": "engine_unavailable"}, 503

    # ── TaskMarket ──────────────────────────────────────────
    tm = _engines.get("TaskMarket")

    @app.get("/api/v1/tasks/")
    async def tasks_list(status: str = "pending", limit: int = 20):
        if tm:
            tasks = tm.list_tasks(status=status, limit=limit)
            return {"tasks": tasks, "count": len(tasks)}
        return {"status": "engine_unavailable"}, 503

    @app.put("/api/v1/tasks/{task_id}")
    async def task_update(task_id: str, request: Request):
        body = await request.json()
        if tm:
            result = tm.update_task(task_id, body)
            return {"status": "ok", "task": result}
        return {"status": "engine_unavailable"}, 503

    @app.post("/api/v1/tasks/")
    async def task_create(request: Request):
        body = await request.json()
        if tm:
            tid = tm.create_task(body)
            return {"status": "ok", "task_id": tid}
        return {"status": "engine_unavailable"}, 503

    # ── Swarm / Nodes ───────────────────────────────────────
    swarm = _engines.get("Swarm")
    cr = _engines.get("CapRegistry")

    @app.get("/api/v1/nodes/")
    async def nodes_list():
        if cr:
            nodes = cr.list_edges()
            return {"nodes": nodes, "count": len(nodes)}
        return {"status": "engine_unavailable"}, 503

    @app.post("/api/v1/health/report")
    async def health_report(request: Request):
        body = await request.json()
        node_id = body.get("node_id", "unknown")
        if cr:
            cr.register(body)
            logger.info(f"Edge registered: {node_id}")
            return {"status": "ok", "node_id": node_id}
        return {"status": "engine_unavailable"}, 503

    # ── Skills Market ───────────────────────────────────────
    sm = _engines.get("SkillMarket")

    @app.get("/api/v1/skills/")
    async def skills_search(q: str = "", limit: int = 20):
        if sm:
            skills = sm.search(q, limit=limit)
            return {"skills": skills, "count": len(skills)}
        return {"status": "engine_unavailable"}, 503

    @app.post("/api/v1/skills/")
    async def skill_publish(request: Request):
        body = await request.json()
        if sm:
            sid = sm.publish(**body)
            logger.info(f"Skill published: {body.get('name', 'unknown')}")
            # Also broadcast via EventBus
            if eb:
                eb.publish("skill.published", {"name": body.get("name"), "id": sid},
                          source="cloud-hub")
            return {"status": "ok", "skill_id": sid}
        return {"status": "engine_unavailable"}, 503

    # ── WebSocket (real-time event push to edges) ───────────
    @app.websocket("/ws/events")
    async def ws_events(websocket: WebSocket):
        await websocket.accept()
        logger.info("WebSocket client connected")
        try:
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                if msg.get("type") == "subscribe":
                    logger.info(f"WS subscribe: {msg.get('patterns', '*')}")
                # Echo back for now — real push via EventBus polling
                await websocket.send_json({"status": "ok", "echo": msg})
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WS error: {e}")

    # ── Broadcast endpoint (cloud → all edges) ──────────────
    @app.post("/api/v1/events/broadcast")
    async def events_broadcast(request: Request):
        """Cloud-initiated broadcast to all edges (insights, skill updates, etc.)"""
        body = await request.json()
        if eb:
            eid = eb.publish(body.get("type", "broadcast"), body.get("payload", {}),
                            source="cloud-hub", broadcast=True)
            return {"status": "ok", "event_id": eid}
        return {"status": "engine_unavailable"}, 503

    return app


# ── Main ────────────────────────────────────────────────────

def main():
    print("""
    ╔════════════════════════════════════════════╗
    ║     ClawShell Cloud Hub v1.1.0            ║
    ║     章鱼主脑 — 云边协同中枢                ║
    ╚════════════════════════════════════════════╝
    """)

    init_engines()

    if not HAS_FASTAPI:
        print("[FATAL] FastAPI not installed. Run: pip install fastapi uvicorn")
        return

    app = create_app()
    logger.info(f"Starting CloudHub on {CLOUD_HOST}:{CLOUD_PORT}")
    logger.info(f"API Docs: http://{CLOUD_HOST}:{CLOUD_PORT}/docs")
    uvicorn.run(app, host=CLOUD_HOST, port=CLOUD_PORT, log_level="info")


if __name__ == "__main__":
    main()
