     1|"""
     2|ClawShell Cloud Hub Package v1.1
     3|=================================
     4|一云多端云边协同分布式神经系统 — 云枢引擎统一入口。
     5|
     6|Usage:
     7|    from cloud import CloudEventBus, CloudTaskMarket, SwarmCoordinator
     8|    from cloud.main import create_app
     9|
    10|All engines are re-exported from their canonical locations in lib/.
    11|"""
    12|
    13|# ── Cloud Engines ───────────────────────────────────────────
    14|from lib.core.eventbus_cloud import CloudEventBus
    15|from lib.core.task_market_cloud import CloudTaskMarket
    16|from lib.core.swarm_cloud import SwarmCoordinator
    17|from lib.core.scheduler_cloud import CronScheduler
    18|from lib.core.capability_registry import CapabilityRegistry, EdgeCapability
    19|from lib.core.task_board import GlobalTaskBoard
    20|from lib.core.skill_market import SkillMarket
    21|
    22|# ── Cloud Services ──────────────────────────────────────────
    23|from lib.services.n8n_bridge import N8NBridge
    24|from lib.services.oss_vault import OSSVaultSync
    25|
    26|__all__ = [
    27|    # Engines
    28|    "CloudEventBus",
    29|    "CloudTaskMarket",
    30|    "SwarmCoordinator",
    31|    "CronScheduler",
    32|    "CapabilityRegistry",
    33|    "EdgeCapability",
    34|    "GlobalTaskBoard",
    35|    "SkillMarket",
    36|    # Services
    37|    "N8NBridge",
    38|    "OSSVaultSync",
    39|]
    40|
    41|__version__ = "1.1.0"
    42|