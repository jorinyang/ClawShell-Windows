     1|"""
     2|ClawShell Edge Brain Package v1.1
     3|==================================
     4|一云多端云边协同分布式神经系统 — 端脑组件统一入口。部署于各终端 (WSL/macOS/Linux)。
     5|
     6|Usage:
     7|    from edge import EdgeSyncDaemon, EnvDetector, EcosystemInstaller
     8|    from edge.adapters import OpenClawAdapter, HermesAdapter
     9|
    10|All edge components are re-exported from their canonical locations in scripts/.
    11|"""
    12|
    13|import sys
    14|import os
    15|
    16|# Ensure scripts/ is on path for edge components
    17|_scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
    18|if _scripts_dir not in sys.path:
    19|    sys.path.insert(0, _scripts_dir)
    20|
    21|# ── Edge Core Components ────────────────────────────────────
    22|# These are re-exported from scripts/ — they exist as standalone .py files.
    23|
    24|def _import_edge_module(name):
    25|    """Lazy import an edge module from scripts/"""
    26|    try:
    27|        mod = __import__(name, fromlist=[name])
    28|        return mod
    29|    except ImportError as e:
    30|        import logging
    31|        logging.getLogger("ClawShell.Edge").debug(f"Edge module '{name}' not available: {e}")
    32|        return None
    33|
    34|# ── Edge Daemon ─────────────────────────────────────────────
    35|def get_edge_sync_daemon():
    36|    """Get EdgeSyncDaemon class (lazy import)."""
    37|    return _import_edge_module("edge_sync_daemon")
    38|
    39|# ── Environment Detection ───────────────────────────────────
    40|def get_env_detector():
    41|    """Get EnvDetector class (lazy import)."""
    42|    return _import_edge_module("env_detector")
    43|
    44|# ── Ecosystem Installer ─────────────────────────────────────
    45|def get_ecosystem_installer():
    46|    """Get EcosystemInstaller class (lazy import)."""
    47|    return _import_edge_module("ecosystem_installer")
    48|
    49|# ── Config Wizard ───────────────────────────────────────────
    50|def get_config_wizard():
    51|    """Get ConfigWizard class (lazy import)."""
    52|    return _import_edge_module("config_wizard")
    53|
    54|# ── Obsidian Adapter ────────────────────────────────────────
    55|def get_obsidian_adapter():
    56|    """Get ObsidianAdapter class (lazy import)."""
    57|    return _import_edge_module("obsidian_adapter")
    58|
    59|__all__ = [
    60|    "get_edge_sync_daemon",
    61|    "get_env_detector",
    62|    "get_ecosystem_installer",
    63|    "get_config_wizard",
    64|    "get_obsidian_adapter",
    65|]
    66|
    67|__version__ = "1.1.0"
    68|