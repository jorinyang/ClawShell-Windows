"""Swarm protocol schema types"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class StrategyType(Enum):
    DEFAULT = "default"
    AGGRESSIVE = "aggressive" 
    CONSERVATIVE = "conservative"

class SwitchCondition(Enum):
    ON_ERROR = "on_error"
    ON_THRESHOLD = "on_threshold"
    MANUAL = "manual"

@dataclass
class Strategy:
    name: str
    type: StrategyType = StrategyType.DEFAULT
    config: Dict = None

@dataclass
class StrategyConfig:
    max_retries: int = 3
    timeout: int = 30
    fallback: Optional[str] = None
