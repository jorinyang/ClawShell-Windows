"""
ClawShell Edge Brain Package v1.1
==================================
章鱼副脑 — 端脑组件统一入口。部署于各终端 (WSL/macOS/Linux)。

Usage:
    from edge import EdgeSyncDaemon, EnvDetector, EcosystemInstaller
    from edge.adapters import OpenClawAdapter, HermesAdapter

All edge components are re-exported from their canonical locations in scripts/.
"""

import sys
import os

# Ensure scripts/ is on path for edge components
_scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

# ── Edge Core Components ────────────────────────────────────
# These are re-exported from scripts/ — they exist as standalone .py files.

def _import_edge_module(name):
    """Lazy import an edge module from scripts/"""
    try:
        mod = __import__(name, fromlist=[name])
        return mod
    except ImportError as e:
        import logging
        logging.getLogger("ClawShell.Edge").debug(f"Edge module '{name}' not available: {e}")
        return None

# ── Edge Daemon ─────────────────────────────────────────────
def get_edge_sync_daemon():
    """Get EdgeSyncDaemon class (lazy import)."""
    return _import_edge_module("edge_sync_daemon")

# ── Environment Detection ───────────────────────────────────
def get_env_detector():
    """Get EnvDetector class (lazy import)."""
    return _import_edge_module("env_detector")

# ── Ecosystem Installer ─────────────────────────────────────
def get_ecosystem_installer():
    """Get EcosystemInstaller class (lazy import)."""
    return _import_edge_module("ecosystem_installer")

# ── Config Wizard ───────────────────────────────────────────
def get_config_wizard():
    """Get ConfigWizard class (lazy import)."""
    return _import_edge_module("config_wizard")

# ── Obsidian Adapter ────────────────────────────────────────
def get_obsidian_adapter():
    """Get ObsidianAdapter class (lazy import)."""
    return _import_edge_module("obsidian_adapter")

__all__ = [
    "get_edge_sync_daemon",
    "get_env_detector",
    "get_ecosystem_installer",
    "get_config_wizard",
    "get_obsidian_adapter",
]

__version__ = "1.1.0"
