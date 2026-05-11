     1|#!/usr/bin/env python3
     2|"""
     3|ClawShell Cloud Hub — FastAPI Unified Entry Point v1.1
     4|=======================================================
     5|一云多端云边协同分布式神经系统 云枢：统一整合所有云枢引擎，提供REST API + WebSocket。
     6|
     7|Components:
     8|  - CloudEventBus   → 事件持久化/查询/广播
     9|  - CloudTaskMarket → 任务状态机/优先级/分发
    10|  - SwarmCoordinator→ 节点管理/心跳/负载
    11|  - CronScheduler   → 定时任务调度
    12|  - CapabilityRegistry → Edge注册/能力管理
    13|  - TaskBoard       → 跨Edge任务共享
    14|  - SkillMarket     → 技能发布/发现/同步
    15|  - N8NBridge       → N8N工作流集成
    16|  - VaultAPI        → Obsidian+OSS Vault
    17|
    18|Usage:
    19|  python cloud/main.py                     # Start with default config
    20|  CLAWSHELL_CLOUD_PORT=8000 python cloud/main.py
    21|"""
    22|
    23|import os
    24|import json
    25|import time
    26|import logging
    27|import threading
    28|from pathlib import Path
    29|from datetime import datetime
    30|from typing import Dict, List, Optional
    31|
    32|# ── FastAPI ─────────────────────────────────────────────────
    33|try:
    34|    from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
    35|    from fastapi.middleware.cors import CORSMiddleware
    36|    import uvicorn
    37|    HAS_FASTAPI = True
    38|except ImportError:
    39|    HAS_FASTAPI = False
    40|    print("[WARN] FastAPI/uvicorn not installed. Run: pip install fastapi uvicorn")
    41|
    42|# ── Config ──────────────────────────────────────────────────
    43|CLOUD_PORT = int(os.environ.get("CLAWSHELL_CLOUD_PORT", "8000"))
    44|CLOUD_HOST = os.environ.get("CLAWSHELL_CLOUD_HOST", "0.0.0.0")
    45|DATA_DIR = Path(os.environ.get("CLAWSHELL_DATA_DIR", Path(__file__).parent.parent / "data"))
    46|DATA_DIR.mkdir(parents=True, exist_ok=True)
    47|
    48|logging.basicConfig(
    49|    level=logging.INFO,
    50|    format="%(asctime)s [CloudHub] %(message)s",
    51|    handlers=[logging.StreamHandler()]
    52|)
    53|logger = logging.getLogger("CloudHub")
    54|
    55|# ── Cloud Engine Imports (stdlib-only, self-contained) ──────
    56|# Each engine is a standalone Python module with zero external deps.
    57|# They all follow the same pattern: thread-safe, JSON-persisted, daemon-cleanup.
    58|
    59|_engines = {}
    60|
    61|def _load_engine(name: str, module_path: str, class_name: str):
    62|    """Lazy-load a cloud engine module."""
    63|    try:
    64|        import importlib.util
    65|        spec = importlib.util.spec_from_file_location(name, module_path)
    66|        mod = importlib.util.module_from_spec(spec)
    67|        spec.loader.exec_module(mod)
    68|        cls = getattr(mod, class_name)
    69|        instance = cls(data_dir=DATA_DIR)
    70|        logger.info(f"  ✅ {name} loaded ({class_name})")
    71|        return instance
    72|    except Exception as e:
    73|        logger.warning(f"  ⚠️  {name} failed: {e}")
    74|        return None
    75|
    76|
    77|def init_engines():
    78|    """Initialize all cloud engines."""
    79|    base = Path(__file__).parent.parent
    80|    lib_core = base / "lib" / "core"
    81|    lib_services = base / "lib" / "services"
    82|
    83|    engines_to_load = [
    84|        ("EventBus",       lib_core / "eventbus_cloud.py",     "CloudEventBus"),
    85|        ("TaskMarket",     lib_core / "task_market_cloud.py",  "CloudTaskMarket"),
    86|        ("Swarm",          lib_core / "swarm_cloud.py",        "SwarmCoordinator"),
    87|        ("Scheduler",      lib_core / "scheduler_cloud.py",    "CronScheduler"),
    88|        ("CapRegistry",    lib_core / "capability_registry.py","CapabilityRegistry"),
    89|        ("TaskBoard",      lib_core / "task_board.py",         "GlobalTaskBoard"),
    90|        ("SkillMarket",    lib_core / "skill_market.py",       "SkillMarket"),
    91|        ("N8NBridge",      lib_services / "n8n_bridge.py",     "N8NBridge"),
    92|        ("VaultAPI",       lib_services / "vault_api.py",      "VaultAPI"),
    93|    ]
    94|
    95|    for name, path, cls_name in engines_to_load:
    96|        if path.exists():
    97|            _engines[name] = _load_engine(name, str(path), cls_name)
    98|        else:
    99|            logger.debug(f"  ⊘ {name} — module not found at {path}")
   100|
   101|    loaded = sum(1 for v in _engines.values() if v is not None)
   102|    logger.info(f"CloudHub initialized: {loaded}/{len(engines_to_load)} engines loaded")
   103|
   104|# ── FastAPI App ─────────────────────────────────────────────
   105|
   106|def create_app() -> FastAPI:
   107|    app = FastAPI(
   108|        title="ClawShell Cloud Hub",
   109|        description="一云多端云边协同分布式神经系统 — 云端中枢",
   110|        version="1.1.0"
   111|    )
   112|    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
   113|
   114|    # ── Health ──────────────────────────────────────────────
   115|    @app.get("/health")
   116|    async def health():
   117|        return {
   118|            "status": "ok",
   119|            "version": "1.1.0",
   120|            "engines": {k: "loaded" if v else "down" for k, v in _engines.items()},
   121|            "timestamp": datetime.now().isoformat()
   122|        }
   123|
   124|    # ── EventBus ────────────────────────────────────────────
   125|    eb = _engines.get("EventBus")
   126|
   127|    @app.post("/api/v1/events/batch")
   128|    async def events_batch(request: Request):
   129|        body = await request.json()
   130|        events = body.get("events", [])
   131|        if eb:
   132|            results = []
   133|            for ev in events:
   134|                eid = eb.publish(ev.get("type", "unknown"), ev.get("payload", {}),
   135|                                 source=ev.get("source", ""))
   136|                results.append(eid)
   137|            return {"status": "ok", "event_ids": results, "count": len(results)}
   138|        return {"status": "engine_unavailable"}, 503
   139|
   140|    @app.get("/api/v1/events/")
   141|    async def events_query(q: str = "*", limit: int = 50):
   142|        if eb:
   143|            events = eb.query(q, limit=limit)
   144|            return {"events": events, "count": len(events)}
   145|        return {"status": "engine_unavailable"}, 503
   146|
   147|    # ── TaskMarket ──────────────────────────────────────────
   148|    tm = _engines.get("TaskMarket")
   149|
   150|    @app.get("/api/v1/tasks/")
   151|    async def tasks_list(status: str = "pending", limit: int = 20):
   152|        if tm:
   153|            tasks = tm.list_tasks(status=status, limit=limit)
   154|            return {"tasks": tasks, "count": len(tasks)}
   155|        return {"status": "engine_unavailable"}, 503
   156|
   157|    @app.put("/api/v1/tasks/{task_id}")
   158|    async def task_update(task_id: str, request: Request):
   159|        body = await request.json()
   160|        if tm:
   161|            result = tm.update_task(task_id, body)
   162|            return {"status": "ok", "task": result}
   163|        return {"status": "engine_unavailable"}, 503
   164|
   165|    @app.post("/api/v1/tasks/")
   166|    async def task_create(request: Request):
   167|        body = await request.json()
   168|        if tm:
   169|            tid = tm.create_task(body)
   170|            return {"status": "ok", "task_id": tid}
   171|        return {"status": "engine_unavailable"}, 503
   172|
   173|    # ── Swarm / Nodes ───────────────────────────────────────
   174|    swarm = _engines.get("Swarm")
   175|    cr = _engines.get("CapRegistry")
   176|
   177|    @app.get("/api/v1/nodes/")
   178|    async def nodes_list():
   179|        if cr:
   180|            nodes = cr.list_edges()
   181|            return {"nodes": nodes, "count": len(nodes)}
   182|        return {"status": "engine_unavailable"}, 503
   183|
   184|    @app.post("/api/v1/health/report")
   185|    async def health_report(request: Request):
   186|        body = await request.json()
   187|        node_id = body.get("node_id", "unknown")
   188|        if cr:
   189|            cr.register(body)
   190|            logger.info(f"Edge registered: {node_id}")
   191|            return {"status": "ok", "node_id": node_id}
   192|        return {"status": "engine_unavailable"}, 503
   193|
   194|    # ── Skills Market ───────────────────────────────────────
   195|    sm = _engines.get("SkillMarket")
   196|
   197|    @app.get("/api/v1/skills/")
   198|    async def skills_search(q: str = "", limit: int = 20):
   199|        if sm:
   200|            skills = sm.search(q, limit=limit)
   201|            return {"skills": skills, "count": len(skills)}
   202|        return {"status": "engine_unavailable"}, 503
   203|
   204|    @app.post("/api/v1/skills/")
   205|    async def skill_publish(request: Request):
   206|        body = await request.json()
   207|        if sm:
   208|            sid = sm.publish(**body)
   209|            logger.info(f"Skill published: {body.get('name', 'unknown')}")
   210|            # Also broadcast via EventBus
   211|            if eb:
   212|                eb.publish("skill.published", {"name": body.get("name"), "id": sid},
   213|                          source="cloud-hub")
   214|            return {"status": "ok", "skill_id": sid}
   215|        return {"status": "engine_unavailable"}, 503
   216|
   217|    # ── WebSocket (real-time event push to edges) ───────────
   218|    @app.websocket("/ws/events")
   219|    async def ws_events(websocket: WebSocket):
   220|        await websocket.accept()
   221|        logger.info("WebSocket client connected")
   222|        try:
   223|            while True:
   224|                data = await websocket.receive_text()
   225|                msg = json.loads(data)
   226|                if msg.get("type") == "subscribe":
   227|                    logger.info(f"WS subscribe: {msg.get('patterns', '*')}")
   228|                # Echo back for now — real push via EventBus polling
   229|                await websocket.send_json({"status": "ok", "echo": msg})
   230|        except WebSocketDisconnect:
   231|            logger.info("WebSocket client disconnected")
   232|        except Exception as e:
   233|            logger.error(f"WS error: {e}")
   234|
   235|    # ── Broadcast endpoint (cloud → all edges) ──────────────
   236|    @app.post("/api/v1/events/broadcast")
   237|    async def events_broadcast(request: Request):
   238|        """Cloud-initiated broadcast to all edges (insights, skill updates, etc.)"""
   239|        body = await request.json()
   240|        if eb:
   241|            eid = eb.publish(body.get("type", "broadcast"), body.get("payload", {}),
   242|                            source="cloud-hub", broadcast=True)
   243|            return {"status": "ok", "event_id": eid}
   244|        return {"status": "engine_unavailable"}, 503
   245|
   246|    return app
   247|
   248|
   249|# ── Main ────────────────────────────────────────────────────
   250|
   251|def main():
   252|    print("""
   253|    ╔════════════════════════════════════════════╗
   254|    ║     ClawShell Cloud Hub v1.1.0            ║
   255|    ║     一云多端云边协同分布式神经系统                ║
   256|    ╚════════════════════════════════════════════╝
   257|    """)
   258|
   259|    init_engines()
   260|
   261|    if not HAS_FASTAPI:
   262|        print("[FATAL] FastAPI not installed. Run: pip install fastapi uvicorn")
   263|        return
   264|
   265|    app = create_app()
   266|    logger.info(f"Starting CloudHub on {CLOUD_HOST}:{CLOUD_PORT}")
   267|    logger.info(f"API Docs: http://{CLOUD_HOST}:{CLOUD_PORT}/docs")
   268|    uvicorn.run(app, host=CLOUD_HOST, port=CLOUD_PORT, log_level="info")
   269|
   270|
   271|if __name__ == "__main__":
   272|    main()
   273|