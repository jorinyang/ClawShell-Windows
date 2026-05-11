"""
ClawShell Cloud — Review Engine v1.1
=====================================
主动复盘引擎：周期性复盘→提炼洞察→生成优化建议→输出到SkillMarket。

核心组件:
  ReviewScheduler    — CronScheduler集成复盘任务(日/周/月)
  ReviewEngine       — 基于执行数据的自动化复盘分析
  ActionPlanGenerator — 复盘结果→优化建议→自动发布

设计原则:
  - 零外部依赖 (stdlib only)
  - 线程安全
  - JSON持久化
  - 可插拔策略 (日/周/月不同深度)

Usage:
  from cloud.review import ReviewEngine
  engine = ReviewEngine(data_dir=Path("data"))
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
from collections import Counter, defaultdict

logger = logging.getLogger("CloudHub.Review")

REVIEW_INTERVAL = 3600  # 1 hour check (actual execution based on schedule)


@dataclass
class Review:
    """A review/retrospective analysis."""
    review_id: str = ""
    review_type: str = ""       # daily, weekly, monthly, adhoc
    period_start: str = ""
    period_end: str = ""
    summary: str = ""
    key_findings: List[Dict] = field(default_factory=list)
    metrics: Dict = field(default_factory=dict)
    recommendations: List[Dict] = field(default_factory=list)
    action_plan: List[Dict] = field(default_factory=list)
    published_to_skillmarket: bool = False
    created_at: str = ""


@dataclass
class ActionPlan:
    """A generated action plan from review."""
    plan_id: str = ""
    review_id: str = ""
    action: str = ""
    priority: str = "medium"
    target_component: str = ""
    estimated_impact: str = ""
    assigned_to: str = ""
    status: str = "pending"
    created_at: str = ""


# ═══════════════════════════════════════════════════════════
# ReviewScheduler — Cron-based review scheduling
# ═══════════════════════════════════════════════════════════

class ReviewScheduler:
    """Determines when reviews should run based on schedule."""

    SCHEDULES = {
        "daily":   {"hour": 9,  "minute": 0},    # 09:00 daily
        "weekly":  {"hour": 10, "minute": 0, "weekday": 0},  # Monday 10:00
        "monthly": {"hour": 11, "minute": 0, "day": 1},      # 1st of month 11:00
    }

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "review"
        self.last_run_file = self.data_dir / "last_run.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._last_runs: Dict[str, str] = {}
        self._load()

    def _load(self):
        if self.last_run_file.exists():
            try:
                self._last_runs = json.loads(self.last_run_file.read_text())
            except:
                pass

    def _save(self):
        self.last_run_file.write_text(json.dumps(self._last_runs, indent=2))

    def should_run(self, review_type: str) -> bool:
        """Check if a review type should run now."""
        now = datetime.now()
        schedule = self.SCHEDULES.get(review_type)
        if not schedule:
            return False

        last_run = self._last_runs.get(review_type)
        if last_run:
            last_dt = datetime.fromisoformat(last_run)
        else:
            last_dt = None

        # Check time
        if now.hour != schedule["hour"] or now.minute != schedule["minute"]:
            return False

        # Check day constraints
        if review_type == "weekly" and now.weekday() != schedule.get("weekday", 0):
            return False
        if review_type == "monthly" and now.day != schedule.get("day", 1):
            return False

        # Check if already run today
        if last_dt and last_dt.date() == now.date():
            return False

        return True

    def mark_run(self, review_type: str):
        self._last_runs[review_type] = datetime.now().isoformat()
        self._save()

    def get_next_review_time(self) -> Dict[str, str]:
        """Get next scheduled review times for all types."""
        now = datetime.now()
        result = {}
        for rtype, schedule in self.SCHEDULES.items():
            next_run = now.replace(hour=schedule["hour"], minute=schedule["minute"], second=0)
            if rtype == "weekly":
                days_ahead = schedule.get("weekday", 0) - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                next_run += timedelta(days=days_ahead)
            elif rtype == "monthly":
                if now.day >= schedule.get("day", 1):
                    if now.month == 12:
                        next_run = next_run.replace(year=now.year + 1, month=1)
                    else:
                        next_run = next_run.replace(month=now.month + 1)
            if next_run < now:
                next_run += timedelta(days=1)
            result[rtype] = next_run.isoformat()
        return result


# ═══════════════════════════════════════════════════════════
# ReviewEngine — Automated review/retrospective analysis
# ═══════════════════════════════════════════════════════════

class ReviewEngine:
    """Analyzes execution data and generates review reports."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "review"
        self.reviews_file = self.data_dir / "reviews.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._reviews: List[Review] = []
        self._load()

    def _load(self):
        if self.reviews_file.exists():
            try:
                data = json.loads(self.reviews_file.read_text())
                self._reviews = [Review(**r) for r in data.get("reviews", [])]
            except:
                pass

    def _save(self):
        with self._lock:
            self.reviews_file.write_text(json.dumps({
                "reviews": [asdict(r) for r in self._reviews],
                "updated_at": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))

    def run_review(self, review_type: str, event_data: List[Dict],
                   task_data: List[Dict] = None,
                   edge_data: List[Dict] = None) -> Review:
        """Run a review analysis on collected data."""
        now = datetime.now()
        period_start = now - timedelta(days=1 if review_type == "daily" else
                                       7 if review_type == "weekly" else 30)

        # Analyze events
        event_types = Counter(e.get("type", "unknown") for e in event_data)
        error_events = [e for e in event_data if "error" in str(e).lower()]
        task_completions = task_data or []

        # Generate metrics
        metrics = {
            "total_events": len(event_data),
            "unique_event_types": len(event_types),
            "top_events": event_types.most_common(5),
            "error_count": len(error_events),
            "error_rate": f"{len(error_events) / max(len(event_data), 1) * 100:.1f}%",
            "tasks_completed": len([t for t in task_completions if t.get("status") == "completed"]),
            "tasks_failed": len([t for t in task_completions if t.get("status") == "failed"]),
            "active_edges": len([e for e in (edge_data or []) if e.get("status") == "online"]),
            "period": f"{period_start.isoformat()} → {now.isoformat()}",
        }

        # Key findings
        findings = []
        if error_events:
            error_sources = Counter(e.get("source", "unknown") for e in error_events)
            top_error_source = error_sources.most_common(1)
            findings.append({
                "finding": f"Top error source: {top_error_source[0][0]} ({top_error_source[0][1]} errors)",
                "severity": "high" if top_error_source[0][1] > 5 else "medium",
            })
        if len(event_types) < 3 and len(event_data) > 10:
            findings.append({
                "finding": f"Low event diversity: only {len(event_types)} types from {len(event_data)} events",
                "severity": "low",
            })

        # Recommendations
        recommendations = []
        if metrics["error_rate"] not in ["0.0%", "0%"]:
            recommendations.append({
                "action": "Investigate and create self-repair rules for recurring errors",
                "priority": "high",
                "target": "SelfHealing engine",
            })
        if metrics["tasks_failed"] > 0:
            recommendations.append({
                "action": f"Review {metrics['tasks_failed']} failed tasks for common failure patterns",
                "priority": "medium",
                "target": "TaskMarket",
            })

        # Action plan
        action_plan = []
        for i, rec in enumerate(recommendations):
            action_plan.append({
                "step": i + 1,
                "action": rec["action"],
                "priority": rec["priority"],
                "target": rec["target"],
                "status": "pending",
            })

        review = Review(
            review_id=str(uuid.uuid4())[:8],
            review_type=review_type,
            period_start=period_start.isoformat(),
            period_end=now.isoformat(),
            summary=self._generate_summary(review_type, metrics, findings),
            key_findings=findings,
            metrics=metrics,
            recommendations=recommendations,
            action_plan=action_plan,
            created_at=now.isoformat(),
        )

        with self._lock:
            self._reviews.append(review)
            if len(self._reviews) > 50:
                self._reviews = self._reviews[-30:]
            self._save()

        logger.info(f"Review completed: {review_type} (id={review.review_id})")
        return review

    def _generate_summary(self, review_type: str, metrics: Dict, findings: List[Dict]) -> str:
        """Generate human-readable summary."""
        return (
            f"[{review_type.upper()} REVIEW] "
            f"Processed {metrics.get('total_events', 0)} events "
            f"across {metrics.get('active_edges', 0)} active edges. "
            f"Error rate: {metrics.get('error_rate', 'N/A')}. "
            f"{metrics.get('tasks_completed', 0)} tasks completed, "
            f"{metrics.get('tasks_failed', 0)} failed. "
            f"Key findings: {len(findings)} issues identified."
        )

    def get_recent(self, limit: int = 10) -> List[Dict]:
        with self._lock:
            return [asdict(r) for r in self._reviews[-limit:]]

    def get_stats(self) -> Dict:
        with self._lock:
            by_type = Counter(r.review_type for r in self._reviews)
            return {
                "total_reviews": len(self._reviews),
                "by_type": dict(by_type),
                "last_review": self._reviews[-1].created_at if self._reviews else None,
            }


# ═══════════════════════════════════════════════════════════
# ActionPlanGenerator — Review → Action Plan → SkillMarket
# ═══════════════════════════════════════════════════════════

class ActionPlanGenerator:
    """Generates actionable plans from reviews and publishes to SkillMarket."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir / "review"
        self.plans_file = self.data_dir / "action_plans.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._plans: List[ActionPlan] = []
        self._load()

    def _load(self):
        if self.plans_file.exists():
            try:
                data = json.loads(self.plans_file.read_text())
                self._plans = [ActionPlan(**p) for p in data.get("plans", [])]
            except:
                pass

    def _save(self):
        with self._lock:
            self.plans_file.write_text(json.dumps({
                "plans": [asdict(p) for p in self._plans],
                "updated_at": datetime.now().isoformat()
            }, indent=2, ensure_ascii=False))

    def generate_from_review(self, review: Review) -> List[ActionPlan]:
        """Generate action plans from a review."""
        new_plans = []
        for rec in review.recommendations:
            plan = ActionPlan(
                plan_id=str(uuid.uuid4())[:8],
                review_id=review.review_id,
                action=rec.get("action", ""),
                priority=rec.get("priority", "medium"),
                target_component=rec.get("target", ""),
                estimated_impact=rec.get("impact", "待评估"),
                created_at=datetime.now().isoformat(),
            )
            new_plans.append(plan)

        with self._lock:
            self._plans.extend(new_plans)
            self._save()

        return new_plans

    def publish_to_skillmarket(self, plans: List[ActionPlan], skill_market) -> List[str]:
        """Publish high-priority action plans as skills."""
        published = []
        for plan in plans:
            if plan.priority not in ("high", "critical"):
                continue
            try:
                skill_content = f"""# Action Plan: {plan.action}

**Priority**: {plan.priority}
**Target**: {plan.target_component}
**Generated from**: Review {plan.review_id}

## Action
{plan.action}

## Expected Impact
{plan.estimated_impact}

---
*Auto-generated by ReviewEngine. Review before execution.*
"""
                sid = skill_market.publish(
                    name=f"Action: {plan.action[:40]}",
                    content=skill_content,
                    description=plan.action[:200],
                    tags=["action-plan", plan.priority, "auto-generated"],
                    author="cloud-hub-review",
                )
                plan.status = "published"
                plan.assigned_to = f"skill:{sid}"
                published.append(sid)
                logger.info(f"Published action plan as skill: {sid}")
            except Exception as e:
                logger.warning(f"Failed to publish action plan: {e}")

        self._save()
        return published

    def get_pending(self) -> List[Dict]:
        with self._lock:
            return [asdict(p) for p in self._plans if p.status == "pending"]

    def get_stats(self) -> Dict:
        with self._lock:
            return {
                "total_plans": len(self._plans),
                "pending": sum(1 for p in self._plans if p.status == "pending"),
                "published": sum(1 for p in self._plans if p.status == "published"),
            }


# ═══════════════════════════════════════════════════════════
# UnifiedReviewEngine — Unified review entry point
# ═══════════════════════════════════════════════════════════

class UnifiedReviewEngine:
    """Unified review engine: scheduler + analyzer + action generator."""

    def __init__(self, data_dir: Path = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = Path(data_dir)

        self.scheduler = ReviewScheduler(self.data_dir)
        self.engine = ReviewEngine(self.data_dir)
        self.planner = ActionPlanGenerator(self.data_dir)

        self._running = False
        self._thread = None
        self._skill_market = None
        self._eventbus = None
        self._event_data: List[Dict] = []
        self._task_data: List[Dict] = []
        self._edge_data: List[Dict] = []

        self.stats = {"reviews_run": 0, "plans_generated": 0, "plans_published": 0}

    def set_skill_market(self, skill_market):
        self._skill_market = skill_market

    def set_eventbus(self, eventbus):
        self._eventbus = eventbus

    def feed_data(self, events: List[Dict] = None, tasks: List[Dict] = None,
                  edges: List[Dict] = None):
        """Feed execution data for review analysis."""
        if events:
            self._event_data.extend(events)
            if len(self._event_data) > 2000:
                self._event_data = self._event_data[-1000:]
        if tasks:
            self._task_data.extend(tasks)
            if len(self._task_data) > 500:
                self._task_data = self._task_data[-300:]
        if edges:
            self._edge_data = edges

    def check_and_run(self) -> Optional[Review]:
        """Check if any review should run and execute it."""
        for review_type in ["daily", "weekly", "monthly"]:
            if self.scheduler.should_run(review_type):
                review = self.engine.run_review(
                    review_type,
                    self._event_data,
                    self._task_data,
                    self._edge_data,
                )
                self.scheduler.mark_run(review_type)
                self.stats["reviews_run"] += 1

                # Generate action plans
                plans = self.planner.generate_from_review(review)
                self.stats["plans_generated"] += len(plans)

                # Publish high-priority plans to SkillMarket
                if self._skill_market:
                    published = self.planner.publish_to_skillmarket(plans, self._skill_market)
                    self.stats["plans_published"] += len(published)

                # Broadcast review summary via EventBus
                if self._eventbus:
                    self._eventbus.publish("review.completed", {
                        "review_type": review_type,
                        "review_id": review.review_id,
                        "summary": review.summary,
                        "action_plans_count": len(plans),
                    }, source="cloud-hub", broadcast=True)

                return review
        return None

    def start(self):
        """Start review daemon."""
        self._running = True
        self._thread = threading.Thread(target=self._daemon_loop, daemon=True)
        self._thread.start()
        logger.info("ReviewEngine daemon started (check interval=%ds)", REVIEW_INTERVAL)

    def _daemon_loop(self):
        while self._running:
            try:
                self.check_and_run()
            except Exception as e:
                logger.error(f"Review cycle error: {e}")
            for _ in range(REVIEW_INTERVAL // 5):
                if not self._running:
                    break
                time.sleep(5)

    def shutdown(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("ReviewEngine shutdown. Stats: %s", json.dumps(self.stats))
