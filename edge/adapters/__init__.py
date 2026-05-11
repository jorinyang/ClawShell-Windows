"""
ClawShell Edge Adapters v1.1
=============================
端脑适配器层 — 自动适配不同类OpenClaw架构。

Adapters:
  - OpenClawAdapter: 悟空 (~/.real) + OpenClaw (~/.openclaw)
  - HermesAdapter:   Hermes Agent (~/.hermes)

Each adapter is responsible for:
  1. Detecting the target framework
  2. Writing integration configs (MCP, cron, env)
  3. Registering with Cloud Hub
  4. Creating workspace directories
"""

import sys
import os

_scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


def get_openclaw_adapter():
    """Get OpenClawAdapter for Wukong/OpenClaw integration."""
    try:
        from openclaw_adapter import OpenClawAdapter
        return OpenClawAdapter
    except ImportError:
        return None


def get_hermes_adapter():
    """Get HermesAdapter for Hermes Agent integration."""
    try:
        from hermes_adapter import HermesAdapter
        return HermesAdapter
    except ImportError:
        return None


__all__ = [
    "get_openclaw_adapter",
    "get_hermes_adapter",
]
