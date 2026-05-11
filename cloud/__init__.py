"""
ClawShell Cloud Hub Package v1.1
=================================
章鱼主脑 — 云枢引擎统一入口。

Usage:
    from cloud import CloudEventBus, CloudTaskMarket, SwarmCoordinator
    from cloud.main import create_app

All engines are re-exported from their canonical locations in lib/.
"""

# ── Cloud Engines ───────────────────────────────────────────
from lib.core.eventbus_cloud import CloudEventBus
from lib.core.task_market_cloud import CloudTaskMarket
from lib.core.swarm_cloud import SwarmCoordinator
from lib.core.scheduler_cloud import CronScheduler
from lib.core.capability_registry import CapabilityRegistry, EdgeCapability
from lib.core.task_board import GlobalTaskBoard
from lib.core.skill_market import SkillMarket

# ── Cloud Services ──────────────────────────────────────────
from lib.services.n8n_bridge import N8NBridge
from lib.services.oss_vault import OSSVaultSync

__all__ = [
    # Engines
    "CloudEventBus",
    "CloudTaskMarket",
    "SwarmCoordinator",
    "CronScheduler",
    "CapabilityRegistry",
    "EdgeCapability",
    "GlobalTaskBoard",
    "SkillMarket",
    # Services
    "N8NBridge",
    "OSSVaultSync",
]

__version__ = "1.1.0"
