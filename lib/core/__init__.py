"""
ClawShell Core Infrastructure - lib/core/
=========================================
包含事件总线( EventBus)、知识传承( Genome)、策略库( Strategy) 三大核心模块
"""

import sys
from pathlib import Path

# 自动添加ClawShell根目录到sys.path
_clawshell_root = Path(__file__).resolve().parent.parent.parent
if str(_clawshell_root) not in sys.path:
    sys.path.insert(0, str(_clawshell_root))

from lib.core import eventbus, genome, strategy

__all__ = ["eventbus", "genome", "strategy"]
