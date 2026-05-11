"""
ClawShell Cloud Hub Package v1.1
=================================
一云多端云边协同分布式神经系统 — 云枢引擎统一入口。

Usage:
    from cloud import CloudEventBus, EvolutionEngine, BroadcastEngine
    from cloud.main import create_app

All engines are re-exported from their canonical locations.
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

# ── Evolution Engine (v1.1 新增) ───────────────────────────
from cloud.evolution import (
    EvolutionEngine, InsightAggregator, PatternMiner,
    AutoSkillPublisher, EvolutionTracker
)

# ── Broadcast Engine (v1.1 新增) ───────────────────────────
from cloud.broadcast import (
    BroadcastEngine, BestPracticeRegistry, CrossEdgeLearning
)

# ── Review Engine (v1.1 新增) ──────────────────────────────
from cloud.review import (
    UnifiedReviewEngine, ReviewScheduler, ReviewEngine,
    ActionPlanGenerator
)

__all__ = [
    # Engines (1.0)
    "CloudEventBus", "CloudTaskMarket", "SwarmCoordinator",
    "CronScheduler", "CapabilityRegistry", "EdgeCapability",
    "GlobalTaskBoard", "SkillMarket",
    # Services
    "N8NBridge", "OSSVaultSync",
    # Evolution (1.1)
    "EvolutionEngine", "InsightAggregator", "PatternMiner",
    "AutoSkillPublisher", "EvolutionTracker",
    # Broadcast (1.1)
    "BroadcastEngine", "BestPracticeRegistry", "CrossEdgeLearning",
    # Review (1.1)
    "UnifiedReviewEngine", "ReviewScheduler", "ReviewEngine",
    "ActionPlanGenerator",
]

__version__ = "1.1.0"
