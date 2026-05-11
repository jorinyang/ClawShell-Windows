#!/usr/bin/env python3
"""
ClawShell Cloud Hub — FastAPI Unified Entry Point v1.1
=======================================================
一云多端云边协同分布式神经系统 云枢：统一整合所有云枢引擎，提供REST API + WebSocket。

Components:
  - CloudEventBus       → 事件持久化/查询/广播
  - CloudTaskMarket     → 任务状态机/优先级/分发
  - SwarmCoordinator    → 节点管理/心跳/负载
  - CronScheduler       → 定时任务调度
  - CapabilityRegistry  → Edge注册/能力管理
  - TaskBoard           → 跨Edge任务共享
  - SkillMarket         → 技能发布/发现/同步
  - EvolutionEngine     → 自进化闭环 (v1.1 新增)
  - BroadcastEngine     → 成果广播+跨端学习 (v1.1 新增)
  - UnifiedReviewEngine → 主动复盘引擎 (v1.1 新增)
  - N8NBridge           → N8N工作流集成

Usage:
  python cloud/main.py                     # Start with default config
  CLAWSHELL_CLOUD_PORT=8000 python cloud/main.py
"""

import os
import sys
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

# Ensure cloud/ is on path for evolution/broadcast/review imports
_cloud_dir = Path(__file__).parent
if str(_cloud_dir.parent) not in sys.path:
    sys.path.insert(0, str(_cloud_dir.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CloudHub] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("CloudHub")

# ── Cloud Engine Imports ────────────────────────────────────
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
    cloud_dir = base / "cloud"

    # ── Core Infrastructure ─────────────────────────────────
    engines_to_load = [
        ("EventBus",       lib_core / "eventbus_cloud.py",     "CloudEventBus"),
        ("TaskMarket",     lib_core / "task_market_cloud.py",  "CloudTaskMarket"),
        ("Swarm",          lib_core / "swarm_cloud.py",        "SwarmCoordinator"),
        ("Scheduler",      lib_core / "scheduler_cloud.py",    "CronScheduler"),
        ("CapRegistry",    lib_core / "capability_registry.py","CapabilityRegistry"),
        ("TaskBoard",      lib_core / "task_board.py",         "GlobalTaskBoard"),
        ("SkillMarket",    lib_core / "skill_market.py",       "SkillMarket"),
        ("N8NBridge",      lib_services / "n8n_bridge.py",     "N8NBridge"),
    ]

    for name, path, cls_name in engines_to_load:
        if path.exists():
            _engines[name] = _load_engine(name, str(path), cls_name)
        else:
            logger.debug(f"  ⊘ {name} — not found")

    # ── v1.1 New Engines ────────────────────────────────────
    evolution_path = cloud_dir / "evolution.py"
    if evolution_path.exists():
        evo = _load_engine("Evolution", str(evolution_path), "EvolutionEngine")
        if evo:
            evo.set_skill_market(_engines.get("SkillMarket"))
            evo.set_eventbus(_engines.get("EventBus"))
            evo.start()
            _engines["Evolution"] = evo

    broadcast_path = cloud_dir / "broadcast.py"
    if broadcast_path.exists():
        bcast = _load_engine("Broadcast", str(broadcast_path), "BroadcastEngine")
        if bcast:
            bcast.set_eventbus(_engines.get("EventBus"))
            _engines["Broadcast"] = bcast

    review_path = cloud_dir / "review.py"
    if review_path.exists():
        rev = _load_engine("Review", str(review_path), "UnifiedReviewEngine")
        if rev:
            rev.set_skill_market(_engines.get("SkillMarket"))
            rev.set_eventbus(_engines.get("EventBus"))
            rev.start()
            _engines["Review"] = rev

    loaded = sum(1 for v in _engines.values() if v is not None)
    logger.info(f"CloudHub initialized: {loaded}/{len(_engines)} engines loaded")


# ── FastAPI App ─────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="ClawShell Cloud Hub",
        description="一云多端云边协同分布式神经系统 — 云端中枢",
        version="1.2.0"
    )
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    eb = _engines.get("EventBus")
    tm = _engines.get("TaskMarket")
    cr = _engines.get("CapRegistry")
    sm = _engines.get("SkillMarket")
    evo = _engines.get("Evolution")
    bcast = _engines.get("Broadcast")
    review = _engines.get("Review")

    # ── Health ──────────────────────────────────────────────
    @app.get("/health")
    async def health():
        engine_status = {k: "loaded" if v else "down" for k, v in _engines.items()}
        evolution_stats = evo.stats if evo else {}
        return {
            "status": "ok",
            "version": "1.2.0",
            "engines": engine_status,
            "evolution": evolution_stats,
            "timestamp": datetime.now().isoformat()
        }

    # ── EventBus ────────────────────────────────────────────
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
            # Feed raw events to evolution + review engines
            if evo:
                evo.aggregator.ingest(events)
            if review:
                review.feed_data(events=events)
            return {"status": "ok", "event_ids": results, "count": len(results)}
        return {"status": "engine_unavailable"}, 503

    @app.get("/api/v1/events/")
    async def events_query(q: str = "*", limit: int = 50):
        if eb:
            events = eb.query(q, limit=limit)
            return {"events": events, "count": len(events)}
        return {"status": "engine_unavailable"}, 503

    @app.post("/api/v1/events/broadcast")
    async def events_broadcast(request: Request):
        """Cloud-initiated broadcast to all edges."""
        body = await request.json()
        if eb:
            eid = eb.publish(body.get("type", "broadcast"), body.get("payload", {}),
                            source="cloud-hub", broadcast=True)
            return {"status": "ok", "event_id": eid}
        return {"status": "engine_unavailable"}, 503

    # ── TaskMarket ──────────────────────────────────────────
    @app.get("/api/v1/tasks/")
    async def tasks_list(status: str = "pending", limit: int = 20):
        if tm:
            tasks = tm.list_tasks(status=status, limit=limit)
            # Feed task data to review engine
            if review:
                review.feed_data(tasks=tasks)
            return {"tasks": tasks, "count": len(tasks)}
        return {"status": "engine_unavailable"}, 503

    @app.put("/api/v1/tasks/{task_id}")
    async def task_update(task_id: str, request: Request):
        body = await request.json()
        if tm:
            result = tm.update_task(task_id, body)
            # Feed to cross-edge learning
            if bcast and result:
                bcast.cross_edge.extract_learning(
                    body.get("claimed_by", "unknown"), result)
            return {"status": "ok", "task": result}
        return {"status": "engine_unavailable"}, 503

    @app.post("/api/v1/tasks/")
    async def task_create(request: Request):
        body = await request.json()
        if tm:
            tid = tm.create_task(body)
            return {"status": "ok", "task_id": tid}
        return {"status": "engine_unavailable"}, 503

    # ── Nodes ───────────────────────────────────────────────
    @app.get("/api/v1/nodes/")
    async def nodes_list():
        if cr:
            nodes = cr.list_edges()
            if review:
                review.feed_data(edges=nodes)
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

    # ── Skills ──────────────────────────────────────────────
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
            if eb:
                eb.publish("skill.published", {"name": body.get("name"), "id": sid},
                          source="cloud-hub", broadcast=True)
            return {"status": "ok", "skill_id": sid}
        return {"status": "engine_unavailable"}, 503

    # ── Insights (v1.1) ─────────────────────────────────────
    @app.get("/api/v1/insights/")
    async def insights_list(limit: int = 10):
        """Pull cloud insights. Called by edge before action execution."""
        if evo:
            insights = evo.get_broadcast_insights(limit=limit)
            return {"insights": insights, "count": len(insights)}
        return {"status": "engine_unavailable"}, 503

    # ── Broadcasts (v1.1) ──────────────────────────────────
    @app.get("/api/v1/broadcasts/")
    async def broadcasts_list():
        """Pull pending cloud broadcasts."""
        if bcast:
            pending = bcast.get_pending_broadcasts()
            return {"broadcasts": pending, "count": len(pending)}
        # Fallback: return evolution insights as broadcasts
        if evo:
            insights = evo.get_broadcast_insights(limit=10)
            return {"broadcasts": insights, "count": len(insights)}
        return {"status": "engine_unavailable"}, 503

    @app.post("/api/v1/broadcasts/")
    async def broadcast_create(request: Request):
        """Cloud-initiated broadcast creation."""
        body = await request.json()
        if bcast:
            bid = bcast.broadcast(
                category=body.get("category", "general"),
                title=body.get("title", ""),
                content=body.get("content", ""),
                priority=body.get("priority", "normal"),
            )
            return {"status": "ok", "broadcast_id": bid}
        return {"status": "engine_unavailable"}, 503

    # ── Best Practices (v1.1) ──────────────────────────────
    @app.get("/api/v1/best-practices/")
    async def best_practices_list(category: str = None, limit: int = 20):
        """Search best practices."""
        if bcast:
            practices = bcast.best_practices.search(category=category, limit=limit)
            return {"practices": practices, "count": len(practices)}
        return {"status": "engine_unavailable"}, 503

    @app.post("/api/v1/best-practices/")
    async def best_practice_register(request: Request):
        """Register a new best practice."""
        body = await request.json()
        if bcast:
            bp_id = bcast.best_practices.register(
                name=body.get("name", ""),
                description=body.get("description", ""),
                content=body.get("content", ""),
                category=body.get("category", "general"),
                source_node=body.get("source_node", "cloud-hub"),
                tags=body.get("tags", []),
            )
            return {"status": "ok", "bp_id": bp_id}
        return {"status": "engine_unavailable"}, 503

    # ── Reviews (v1.1) ────────────────────────────────────
    @app.get("/api/v1/reviews/")
    async def reviews_list(limit: int = 10):
        """Get recent review reports."""
        if review:
            revs = review.engine.get_recent(limit=limit)
            return {"reviews": revs, "count": len(revs)}
        return {"status": "engine_unavailable"}, 503

    @app.post("/api/v1/reviews/run")
    async def review_run_adhoc(request: Request):
        """Trigger an ad-hoc review."""
        body = await request.json()
        review_type = body.get("type", "daily")
        if review:
            result = review.scheduler.should_run(review_type)
            if not result:
                # Force run
                review.scheduler.mark_run(review_type)  # reset
                result = review.check_and_run()
            return {"status": "ok", "review_triggered": True}
        return {"status": "engine_unavailable"}, 503

    # ── Evolution History (v1.1) ──────────────────────────
    @app.get("/api/v1/evolution/history")
    async def evolution_history(limit: int = 20):
        """Get self-evolution history."""
        if evo:
            history = evo.get_evolution_history(limit=limit)
            return {"history": history, "count": len(history)}
        return {"status": "engine_unavailable"}, 503

    @app.get("/api/v1/evolution/stats")
    async def evolution_stats():
        """Get evolution engine statistics."""
        if evo:
            return {
                "evolution": evo.stats,
                "aggregator": evo.aggregator.get_stats(),
                "tracker": evo.tracker.get_stats(),
            }
        return {"status": "engine_unavailable"}, 503

    # ── Cross-Edge Learning (v1.1) ────────────────────────
    @app.get("/api/v1/learning/{edge_id}")
    async def cross_edge_learning(edge_id: str, limit: int = 10):
        """Get learnings for a specific edge (excludes own learnings)."""
        if bcast:
            learnings = bcast.cross_edge.get_learnings_for_edge(edge_id, limit=limit)
            return {"learnings": learnings, "count": len(learnings)}
        return {"status": "engine_unavailable"}, 503

    # ── WebSocket ────────────────────────────────────────────
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
                await websocket.send_json({"status": "ok", "echo": msg})
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error(f"WS error: {e}")

    return app


# ── Shutdown ────────────────────────────────────────────────
def shutdown():
    """Graceful shutdown of all daemon engines."""
    for name in ["Evolution", "Review"]:
        engine = _engines.get(name)
        if engine and hasattr(engine, "shutdown"):
            engine.shutdown()
    logger.info("CloudHub shutdown complete.")


# ── Main ────────────────────────────────────────────────────
def main():
    print("""
    ╔══════════════════════════════════════════════════╗
    ║     ClawShell Cloud Hub v1.2.0                  ║
    ║     一云多端云边协同分布式神经系统                ║
    ║                                                  ║
    ║  12 Engines: EventBus/Task/Swarm/Scheduler        ║
    ║              CapRegistry/TaskBoard/SkillMarket    ║
    ║              Evolution/Broadcast/Review/N8N       ║
    ╚══════════════════════════════════════════════════╝
    """)

    init_engines()

    if not HAS_FASTAPI:
        print("[FATAL] FastAPI not installed. Run: pip install fastapi uvicorn")
        return

    app = create_app()
    logger.info(f"Starting CloudHub on {CLOUD_HOST}:{CLOUD_PORT}")
    logger.info(f"API Docs:     http://{CLOUD_HOST}:{CLOUD_PORT}/docs")
    logger.info(f"Insights:     http://{CLOUD_HOST}:{CLOUD_PORT}/api/v1/insights/")
    logger.info(f"BestPractices: http://{CLOUD_HOST}:{CLOUD_PORT}/api/v1/best-practices/")
    logger.info(f"Reviews:      http://{CLOUD_HOST}:{CLOUD_PORT}/api/v1/reviews/")
    logger.info(f"Evolution:    http://{CLOUD_HOST}:{CLOUD_PORT}/api/v1/evolution/stats")

    try:
        uvicorn.run(app, host=CLOUD_HOST, port=CLOUD_PORT, log_level="info")
    finally:
        shutdown()


if __name__ == "__main__":
    main()
