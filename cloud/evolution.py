"""
ClawShell Cloud — Self-Evolution Engine v1.1
=============================================
一云多端分布式神经系统的自我进化闭环。

核心管道:
  InsightAggregator → PatternMiner → AutoSkillPublisher → EvolutionTracker
  聚合多端数据 → 挖掘可复用模式 → 自动封装Skill → 追踪进化历史

设计原则:
  - 零外部依赖 (stdlib only)
  - 线程安全 (threading.Lock)
  - JSON持久化 (data/evolution/)
  - 守护线程清理 (5s chunks)

Usage:
  from cloud.evolution import EvolutionEngine
  engine = EvolutionEngine(data_dir=Path("data"))
  engine.start()  # Start daemon
  engine.run_evolution_cycle()  # Manual one-shot
"""

import json
import uuid
import time
import threading
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import Counter

logger = logging.getLogger("CloudHub.Evolution")

# ── Constants ──────────────────────────────────────────────
EVOLUTION_INTERVAL = 300  # 5 minutes
PATTERN_MIN_OCCURRENCES = 3  # Minimum occurrences to form a pattern
SKILL_AUTO_PUBLISH_THRESHOLD = 0.6  # Confidence threshold for auto-publish


@dataclass
class InsightRecord:
    """An aggregated insight from edge execution data."""
    insight_id: str = ""
    source_node: str = ""
    category: str = ""          # pattern, optimization, warning, best_practice
    title: str = ""
    description: str = ""
    evidence: List[Dict] = field(default_factory=list)
    confidence: float = 0.0
    created_at: str = ""
    applied: bool = False
    applied_at: Optional[str] = None


@dataclass
class EvolutionEvent:
    """A record of an evolution action."""
    event_id: str = ""
    event_type: str = ""        # pattern_mined, skill_published, broadcast_sent
    description: str = ""
    source_data: Dict = field(default_factory=dict)
    result_data: Dict = field(default_factory=dict)
    timestamp: str = ""


# ═══════════════════════════════════════════════════════════
# InsightAggregator — Aggregates execution data from edges
# ═══════════════════════════════════════════════════════════

class InsightAggregator:
    """Aggregates raw execution events into structured insights."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "evolution"
        self.insights_file = self.data_dir / "insights.json"
        self.raw_file = self.data_dir / "raw_data.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._insights: List[InsightRecord] = []
        self._raw_events: List[Dict] = []
        self._load()

    def _load(self):
        if self.insights_file.exists():
            try:
                data = json.loads(self.insights_file.read_text())
                self._insights = [InsightRecord(**i) for i in data.get("insights", [])]
            except:
                pass
        if self.raw_file.exists():
            try:
                self._raw_events = json.loads(self.raw_file.read_text()).get("events", [])
            except:
                pass

    def _save(self):
        with self._lock:
            self.insights_file.write_text(json.dumps({
                "insights": [asdict(i) for i in self._insights],
                "updated_at": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))
            self.raw_file.write_text(json.dumps({
                "events": self._raw_events[-1000:],  # Keep last 1000
                "count": len(self._raw_events),
            }, indent=2, ensure_ascii=False))

    def ingest(self, events: List[Dict]) -> int:
        """Ingest raw edge events for aggregation."""
        with self._lock:
            count = 0
            for ev in events:
                ev["_ingested_at"] = datetime.now().isoformat()
                self._raw_events.append(ev)
                count += 1
            # Trim to 5000 max
            if len(self._raw_events) > 5000:
                self._raw_events = self._raw_events[-3000:]
            self._save()
            return count

    def aggregate(self) -> List[InsightRecord]:
        """Aggregate raw events into insights."""
        new_insights = []

        # 1. Categorize events by type
        by_type = {}
        for ev in self._raw_events[-500:]:
            etype = ev.get("type", "unknown")
            if etype not in by_type:
                by_type[etype] = []
            by_type[etype].append(ev)

        # 2. For each event type, look for patterns
        for etype, events in by_type.items():
            if len(events) < PATTERN_MIN_OCCURRENCES:
                continue

            # Find common error patterns
            errors = [e for e in events if "error" in str(e.get("payload", {})).lower()]
            if len(errors) >= PATTERN_MIN_OCCURRENCES:
                error_msgs = [str(e.get("payload", {}).get("error", "")) for e in errors]
                common_error = Counter(error_msgs).most_common(1)
                if common_error and common_error[0][1] >= PATTERN_MIN_OCCURRENCES:
                    insight = InsightRecord(
                        insight_id=str(uuid.uuid4())[:8],
                        source_node="cloud-hub",
                        category="pattern",
                        title=f"Recurring error: {common_error[0][0][:60]}",
                        description=f"Detected '{common_error[0][0][:100]}' occurring {common_error[0][1]} times across edges. Consider creating a self-repair rule.",
                        evidence=[{"type": etype, "count": len(errors), "sample": common_error[0][0]}],
                        confidence=min(common_error[0][1] / 10, 0.95),
                        created_at=datetime.now().isoformat()
                    )
                    new_insights.append(insight)

            # Find high-frequency patterns (potential optimization targets)
            if len(events) >= PATTERN_MIN_OCCURRENCES * 2:
                sources = Counter(e.get("source", "unknown") for e in events)
                for source, count in sources.most_common(3):
                    if count >= PATTERN_MIN_OCCURRENCES * 2:
                        insight = InsightRecord(
                            insight_id=str(uuid.uuid4())[:8],
                            source_node="cloud-hub",
                            category="optimization",
                            title=f"High-frequency pattern: {etype} from {source}",
                            description=f"'{etype}' events from '{source}' occurred {count} times. Consider optimizing or creating a dedicated handler.",
                            evidence=[{"type": etype, "source": source, "count": count}],
                            confidence=0.7,
                            created_at=datetime.now().isoformat()
                        )
                        new_insights.append(insight)

        # 3. Save new insights
        with self._lock:
            self._insights.extend(new_insights)
            if len(self._insights) > 200:
                self._insights = self._insights[-150:]
            self._save()

        return new_insights

    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get recent insights for edge consumption."""
        with self._lock:
            return [asdict(i) for i in self._insights[-limit:]]

    def get_stats(self) -> Dict:
        with self._lock:
            return {
                "total_insights": len(self._insights),
                "total_raw_events": len(self._raw_events),
                "categories": Counter(i.category for i in self._insights),
                "avg_confidence": sum(i.confidence for i in self._insights) / max(len(self._insights), 1),
            }


# ═══════════════════════════════════════════════════════════
# PatternMiner — Mines reusable patterns from aggregated data
# ═══════════════════════════════════════════════════════════

class PatternMiner:
    """Mines reusable patterns and best practices from aggregated insights."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "evolution"
        self.patterns_file = self.data_dir / "patterns.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._patterns: List[Dict] = []
        self._load()

    def _load(self):
        if self.patterns_file.exists():
            try:
                self._patterns = json.loads(self.patterns_file.read_text()).get("patterns", [])
            except:
                pass

    def _save(self):
        with self._lock:
            self.patterns_file.write_text(json.dumps({
                "patterns": self._patterns,
                "updated_at": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))

    def mine(self, insights: List[InsightRecord], eventbus_history: List[Dict] = None) -> List[Dict]:
        """Mine patterns from insights + event history."""
        new_patterns = []

        for insight in insights:
            if insight.confidence < 0.5:
                continue

            # Check if similar pattern already exists
            existing = [p for p in self._patterns if p.get("category") == insight.category
                       and p.get("title", "")[:30] == insight.title[:30]]
            if existing:
                existing[0]["occurrences"] = existing[0].get("occurrences", 1) + 1
                existing[0]["last_seen"] = datetime.now().isoformat()
                continue

            pattern = {
                "pattern_id": str(uuid.uuid4())[:8],
                "category": insight.category,
                "title": insight.title,
                "description": insight.description,
                "confidence": insight.confidence,
                "evidence": insight.evidence,
                "suggested_action": self._suggest_action(insight),
                "occurrences": 1,
                "first_seen": insight.created_at,
                "last_seen": datetime.now().isoformat(),
                "promoted_to_skill": False,
                "promoted_to_best_practice": False,
            }
            new_patterns.append(pattern)

        with self._lock:
            self._patterns.extend(new_patterns)
            if len(self._patterns) > 100:
                self._patterns = self._patterns[-80:]
            self._save()

        return new_patterns

    def _suggest_action(self, insight: InsightRecord) -> str:
        """Generate suggested action based on insight category."""
        suggestions = {
            "pattern": "Create self-repair rule or error handler",
            "optimization": "Create performance optimization skill",
            "warning": "Add monitoring alert rule",
            "best_practice": "Register as best practice + broadcast",
        }
        return suggestions.get(insight.category, "Review and categorize")

    def get_unpromoted(self) -> List[Dict]:
        """Get patterns not yet promoted to skills."""
        with self._lock:
            return [p for p in self._patterns if not p.get("promoted_to_skill")]

    def mark_promoted(self, pattern_id: str):
        with self._lock:
            for p in self._patterns:
                if p.get("pattern_id") == pattern_id:
                    p["promoted_to_skill"] = True
                    p["promoted_at"] = datetime.now().isoformat()
                    break
            self._save()

    def get_all(self, limit: int = 20) -> List[Dict]:
        with self._lock:
            return self._patterns[-limit:]


# ═══════════════════════════════════════════════════════════
# AutoSkillPublisher — Auto-publishes patterns as skills
# ═══════════════════════════════════════════════════════════

class AutoSkillPublisher:
    """Automatically publishes high-confidence patterns as SkillMarket skills."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "evolution"
        self.published_file = self.data_dir / "auto_published_skills.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._published: List[Dict] = []
        self._load()

    def _load(self):
        if self.published_file.exists():
            try:
                self._published = json.loads(self.published_file.read_text()).get("skills", [])
            except:
                pass

    def _save(self):
        with self._lock:
            self.published_file.write_text(json.dumps({
                "skills": self._published,
                "updated_at": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))

    def publish(self, patterns: List[Dict], skill_market) -> List[str]:
        """Auto-publish high-confidence patterns as skills."""
        published_ids = []

        for pattern in patterns:
            if pattern.get("promoted_to_skill"):
                continue
            if pattern.get("confidence", 0) < SKILL_AUTO_PUBLISH_THRESHOLD:
                continue

            skill_content = f"""# {pattern['title']}

## Auto-generated by ClawShell Evolution Engine

**Category**: {pattern.get('category', 'general')}
**Confidence**: {pattern.get('confidence', 0):.0%}
**Source**: Pattern mined from {pattern.get('occurrences', 0)} occurrences

## Description
{pattern.get('description', '')}

## Suggested Action
{pattern.get('suggested_action', '')}

## Evidence
```json
{json.dumps(pattern.get('evidence', []), indent=2)}
```

## Usage
This skill was auto-generated based on recurring patterns detected across edge nodes.
Review and refine before deploying to production.
"""

            try:
                sid = skill_market.publish(
                    name=pattern["title"][:50],
                    content=skill_content,
                    description=pattern.get("description", "")[:200],
                    tags=["auto-generated", pattern.get("category", "general")],
                    author="cloud-hub-evolution",
                )
                pattern["promoted_to_skill"] = True
                pattern["skill_id"] = sid
                published_ids.append(sid)
                self._published.append({
                    "pattern_id": pattern.get("pattern_id"),
                    "skill_id": sid,
                    "published_at": datetime.now().isoformat(),
                })
                logger.info(f"Auto-published skill: {pattern['title'][:40]} (id={sid})")
            except Exception as e:
                logger.warning(f"Failed to auto-publish skill for pattern {pattern.get('pattern_id')}: {e}")

        self._save()
        return published_ids

    def get_published(self) -> List[Dict]:
        with self._lock:
            return list(self._published)


# ═══════════════════════════════════════════════════════════
# EvolutionTracker — Tracks evolution history + A/B comparison
# ═══════════════════════════════════════════════════════════

class EvolutionTracker:
    """Tracks evolution history with A/B effect comparison."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "evolution"
        self.history_file = self.data_dir / "history.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._events: List[EvolutionEvent] = []
        self._load()

    def _load(self):
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text())
                self._events = [EvolutionEvent(**e) for e in data.get("events", [])]
            except:
                pass

    def _save(self):
        with self._lock:
            self.history_file.write_text(json.dumps({
                "events": [asdict(e) for e in self._events],
                "total_events": len(self._events),
                "updated_at": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))

    def record(self, event_type: str, description: str,
               source_data: Dict = None, result_data: Dict = None) -> str:
        """Record an evolution event."""
        event = EvolutionEvent(
            event_id=str(uuid.uuid4())[:8],
            event_type=event_type,
            description=description,
            source_data=source_data or {},
            result_data=result_data or {},
            timestamp=datetime.now().isoformat(),
        )
        with self._lock:
            self._events.append(event)
            if len(self._events) > 500:
                self._events = self._events[-300:]
            self._save()
        return event.event_id

    def get_history(self, event_type: str = None, limit: int = 20) -> List[Dict]:
        """Get evolution history, optionally filtered by type."""
        with self._lock:
            events = self._events
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            return [asdict(e) for e in events[-limit:]]

    def get_stats(self) -> Dict:
        with self._lock:
            by_type = Counter(e.event_type for e in self._events)
            return {
                "total_events": len(self._events),
                "by_type": dict(by_type),
                "first_event": self._events[0].timestamp if self._events else None,
                "last_event": self._events[-1].timestamp if self._events else None,
            }


# ═══════════════════════════════════════════════════════════
# EvolutionEngine — Unified self-evolution daemon
# ═══════════════════════════════════════════════════════════

class EvolutionEngine:
    """Unified self-evolution engine.
    
    Pipeline: InsightAggregator → PatternMiner → AutoSkillPublisher → EvolutionTracker
    """

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = Path(data_dir)

        self.aggregator = InsightAggregator(self.data_dir)
        self.miner = PatternMiner(self.data_dir)
        self.publisher = AutoSkillPublisher(self.data_dir)
        self.tracker = EvolutionTracker(self.data_dir)

        self._running = False
        self._thread = None
        self._skill_market = None  # Set externally after init
        self._eventbus = None       # Set externally after init

        # Stats
        self.stats = {
            "cycles": 0,
            "insights_aggregated": 0,
            "patterns_mined": 0,
            "skills_published": 0,
            "events_recorded": 0,
            "started_at": None,
        }

    def set_skill_market(self, skill_market):
        """Inject SkillMarket reference for auto-publishing."""
        self._skill_market = skill_market

    def set_eventbus(self, eventbus):
        """Inject EventBus reference for broadcasting."""
        self._eventbus = eventbus

    def run_evolution_cycle(self) -> Dict:
        """Run one complete evolution cycle."""
        result = {"insights": 0, "patterns": 0, "skills": []}

        # Step 1: Aggregate raw events into insights
        new_insights = self.aggregator.aggregate()
        result["insights"] = len(new_insights)
        self.stats["insights_aggregated"] += len(new_insights)

        if new_insights:
            self.tracker.record("insights_aggregated",
                f"Aggregated {len(new_insights)} insights from raw events",
                result_data={"categories": [i.category for i in new_insights]})

        # Step 2: Mine patterns from insights
        new_patterns = self.miner.mine(new_insights)
        result["patterns"] = len(new_patterns)
        self.stats["patterns_mined"] += len(new_patterns)

        if new_patterns:
            self.tracker.record("patterns_mined",
                f"Mined {len(new_patterns)} patterns",
                source_data={"patterns": [p["pattern_id"] for p in new_patterns]})

        # Step 3: Auto-publish high-confidence patterns as skills
        if self._skill_market:
            unpromoted = self.miner.get_unpromoted()
            published = self.publisher.publish(unpromoted, self._skill_market)
            result["skills"] = published
            self.stats["skills_published"] += len(published)

            # Mark patterns as promoted
            for p in unpromoted:
                if p.get("promoted_to_skill"):
                    self.miner.mark_promoted(p["pattern_id"])

            if published:
                self.tracker.record("skills_published",
                    f"Auto-published {len(published)} skills",
                    source_data={"skill_ids": published})

                # Broadcast to all edges via EventBus
                if self._eventbus:
                    self._eventbus.publish("evolution.skills_published", {
                        "skill_ids": published,
                        "count": len(published),
                        "source": "evolution-engine",
                    }, source="cloud-hub", broadcast=True)

        # Step 4: Broadcast insights via EventBus
        if self._eventbus and new_insights:
            significant = [i for i in new_insights if i.confidence > 0.7]
            if significant:
                self._eventbus.publish("evolution.insights", {
                    "insights": [asdict(i) for i in significant],
                    "count": len(significant),
                }, source="cloud-hub", broadcast=True)

        self.stats["cycles"] += 1
        self.stats["events_recorded"] += 1
        return result

    def start(self):
        """Start the evolution daemon thread."""
        self._running = True
        self.stats["started_at"] = datetime.now().isoformat()
        self._thread = threading.Thread(target=self._daemon_loop, daemon=True)
        self._thread.start()
        logger.info("EvolutionEngine daemon started (interval=%ds)", EVOLUTION_INTERVAL)

    def _daemon_loop(self):
        while self._running:
            try:
                self.run_evolution_cycle()
            except Exception as e:
                logger.error(f"Evolution cycle error: {e}")
            # Sleep in 5s chunks for fast shutdown
            for _ in range(EVOLUTION_INTERVAL // 5):
                if not self._running:
                    break
                time.sleep(5)

    def shutdown(self):
        """Graceful shutdown."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("EvolutionEngine shutdown. Stats: %s", json.dumps(self.stats))

    def get_broadcast_insights(self, limit: int = 10) -> List[Dict]:
        """Get insights ready for broadcast to edges."""
        return self.aggregator.get_recent(limit=limit)

    def get_evolution_history(self, limit: int = 20) -> List[Dict]:
        """Get evolution history."""
        return self.tracker.get_history(limit=limit)
