#!/usr/bin/env python3
"""Comprehensive test for ClawShell 2.0 new modules."""
import sys, os, json, tempfile, shutil
from pathlib import Path

sys.path.insert(0, "/mnt/c/Users/Aorus/.ClawShell")
sys.path.insert(0, "/mnt/c/Users/Aorus/.ClawShell/cloud")

tmpdir = Path(tempfile.mkdtemp(prefix="cs_test_"))
passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}: {detail}")

print("=" * 50)
print("ClawShell 2.0 — Module Test Suite")
print("=" * 50)

# ── TEST 1: Evolution Engine ──
print("\n📦 TEST 1: cloud/evolution.py")
from cloud.evolution import EvolutionEngine
evo = EvolutionEngine(data_dir=tmpdir / "evo")
check("EvolutionEngine instantiate", evo is not None)

events = [
    {"type":"task.error","source":"e1","payload":{"error":"timeout"}},
    {"type":"task.error","source":"e2","payload":{"error":"timeout"}},
    {"type":"task.error","source":"e3","payload":{"error":"timeout"}},
] + [{"type":"task.completed","source":"e1","payload":{"method":"fast"}}]*6

n = evo.aggregator.ingest(events)
check(f"ingest {n} events", n == 9)

insights = evo.aggregator.aggregate()
check(f"aggregate → {len(insights)} insights", len(insights) > 0)
if insights:
    check("insight has title", bool(insights[0].title))
    check("insight has confidence>0", insights[0].confidence > 0)

patterns = evo.miner.mine(insights)
check(f"mine {len(patterns)} patterns", len(patterns) >= 0)

class MockSM:
    skills = []
    def publish(self, name, content, description="", tags=None, author=""):
        sid = f"s{len(self.skills)}"
        self.skills.append({"id":sid,"name":name})
        return sid

mock = MockSM()
evo.set_skill_market(mock)
published = evo.publisher.publish(evo.miner.get_unpromoted(), mock)
check("publish skills", isinstance(published, list))

eid = evo.tracker.record("test","Testing")
check("tracker record", bool(eid))
check("tracker history", len(evo.tracker.get_history()) > 0)
check("broadcast insights", isinstance(evo.get_broadcast_insights(3), list))
check("evolution history", isinstance(evo.get_evolution_history(3), list))

# ── TEST 2: Broadcast Engine ──
print("\n📦 TEST 2: cloud/broadcast.py")
from cloud.broadcast import BroadcastEngine
bcast = BroadcastEngine(data_dir=tmpdir / "bcast")
check("BroadcastEngine instantiate", bcast is not None)

bp_id = bcast.best_practices.register("Test BP","description","content","deployment",tags=["test"])
check(f"register BP id={bp_id}", bool(bp_id) and len(bp_id)==8)
check("search by category", len(bcast.best_practices.search(category="deployment"))>0)
check("search by tags", len(bcast.best_practices.search(tags=["test"]))>0)

learning = bcast.cross_edge.extract_learning("edge-a",{
    "success":True,"type":"deploy","method":"blue-green",
    "duration_seconds":45,"insight":"80% faster","tags":["deploy"],"confidence":0.85
})
check("extract_learning", learning is not None)
check("exclude own", len(bcast.cross_edge.get_learnings_for_edge("edge-a",exclude_own=True))==0)
check("get for other", len(bcast.cross_edge.get_learnings_for_edge("edge-b"))>0)

bid = bcast.broadcast("insight","Test","content")
check("broadcast", bool(bid))
check("pending broadcasts", len(bcast.get_pending_broadcasts())>0)
check("best_practice stats", bcast.best_practices.get_stats()["total"]>0)
check("broadcast stats", bcast.get_stats()["broadcasts_sent"]>0)
check("cross_edge stats", bcast.cross_edge.get_stats()["total_learnings"]>0)

# ── TEST 3: Review Engine ──
print("\n📦 TEST 3: cloud/review.py")
from cloud.review import UnifiedReviewEngine, ReviewScheduler
rev = UnifiedReviewEngine(data_dir=tmpdir / "rev")
check("UnifiedReviewEngine instantiate", rev is not None)
check("scheduler 3 types", all(k in ReviewScheduler.SCHEDULES for k in ("daily","weekly","monthly")))

rev.feed_data(
    events=[{"type":"task.error","source":"e1"}] * 3 + [{"type":"task.completed"}]*5,
    tasks=[{"task_id":"t1","status":"completed"},{"task_id":"t2","status":"failed"}],
    edges=[{"node_id":"e1","status":"online"}]
)

review = rev.engine.run_review("daily",
    [{"type":"task.error","source":"e1"}]*3 + [{"type":"task.completed"}]*5,
    [{"task_id":"t1","status":"completed"},{"task_id":"t2","status":"failed"}],
    [{"node_id":"e1","status":"online"}]
)
check("run_review", review is not None)
check("has summary", bool(review.summary))
check("has metrics", "total_events" in review.metrics)
check("has findings", len(review.key_findings)>0)
check("has recommendations", len(review.recommendations)>0)
check("has action_plan", len(review.action_plan)>0)

plans = rev.planner.generate_from_review(review)
check("generate plans", len(plans)>0)
rev.set_skill_market(mock)
check("publish plans", isinstance(rev.planner.publish_to_skillmarket(plans,mock), list))
check("get recent reviews", len(rev.engine.get_recent(3))>0)

# ── TEST 4: Package exports ──
print("\n📦 TEST 4: cloud/__init__.py")
from cloud import (
    EvolutionEngine as EE, BroadcastEngine as BE, UnifiedReviewEngine as URE,
    InsightAggregator, PatternMiner, AutoSkillPublisher, EvolutionTracker,
    BestPracticeRegistry, CrossEdgeLearning,
    ReviewScheduler, ReviewEngine, ActionPlanGenerator,
)
check("all exports present", all([EE,BE,URE,InsightAggregator,PatternMiner,
    AutoSkillPublisher,EvolutionTracker,BestPracticeRegistry,CrossEdgeLearning,
    ReviewScheduler,ReviewEngine,ActionPlanGenerator]))
check("version=1.2.0", __import__('cloud').__version__=="1.2.0")

# ── TEST 5: Edge Adapters ──
print("\n📦 TEST 5: Edge ActionReferenceHook")
import importlib.util

spec_oc = importlib.util.spec_from_file_location('oc',"/mnt/c/Users/Aorus/.ClawShell/scripts/openclaw_adapter.py")
mod_oc = importlib.util.module_from_spec(spec_oc); spec_oc.loader.exec_module(mod_oc)

ad = tmpdir / "edge" / ".real"; ad.mkdir(parents=True)
(ad / "cloud_insights.json").write_text(json.dumps([
    {"title":"API timeout","category":"pattern","confidence":0.85,"description":"timeouts","suggested_action":"Add retry"}
]))
(ad / "cloud_broadcasts.json").write_text(json.dumps({"broadcasts":[{"category":"skill","title":"New skill"}]}))

adapter = mod_oc.OpenClawAdapter(real_path=str(ad))
check("OpenClawAdapter", adapter is not None)
check("has get_action_reference", hasattr(adapter,'get_action_reference'))
check("has inject_action_reference", hasattr(adapter,'inject_action_reference'))

ref = adapter.get_action_reference()
check("ref available", ref["available"]==True)
check("insights loaded", len(ref["insights"])>0)
check("broadcasts loaded", len(ref["broadcasts"])>0)

res = adapter.inject_action_reference()
check("inject status", res["status"]=="injected")
check("file exists", Path(res["file"]).exists())
c = Path(res["file"]).read_text()
check("file has insight", "API timeout" in c)
check("file has broadcast", "New skill" in c)
check("file has header", "ClawShell Cloud Action Reference" in c)

# Offline
(ad / "cloud_insights.json").unlink(); (ad / "cloud_broadcasts.json").unlink()
check("offline available=False", adapter.get_action_reference()["available"]==False)
res2 = adapter.inject_action_reference()
check("offline status=offline", res2["status"]=="offline")
check("offline autonomous msg", "autonomous mode" in Path(res2["file"]).read_text())

# Hermes
spec_hm = importlib.util.spec_from_file_location('hm',"/mnt/c/Users/Aorus/.ClawShell/scripts/hermes_adapter.py")
mod_hm = importlib.util.module_from_spec(spec_hm); spec_hm.loader.exec_module(mod_hm)

hh = tmpdir / ".hermes"; hh.mkdir()
(hh / "cloud_insights.json").write_text(json.dumps([
    {"title":"Memory opt","category":"optimization","confidence":0.9,"description":"30% less","suggested_action":"Use streaming"}
]))
ah = mod_hm.HermesAdapter(hermes_home=str(hh))
check("HermesAdapter", ah is not None)
check("has inject", hasattr(ah,'inject_action_reference'))
rh = ah.inject_action_reference()
check("hermes inject status", rh["status"]=="injected")
check("hermes file has insight", "Memory opt" in Path(rh["file"]).read_text())

# ── TEST 6: Persistence ──
print("\n📦 TEST 6: Data Persistence")
pd = tmpdir / "persist"
e1 = EvolutionEngine(data_dir=pd)
e1.aggregator.ingest([{"type":"test","payload":{"k":"v"}}])
e1.aggregator.aggregate()
e1.tracker.record("persist","test")
e2 = EvolutionEngine(data_dir=pd)
check("evo: raw events survive", e2.aggregator.get_stats()["total_raw_events"]>0)
check("evo: tracker survives", len(e2.tracker.get_history())>0)

b1 = BroadcastEngine(data_dir=pd)
b1.best_practices.register("Persist BP","d","c")
b2 = BroadcastEngine(data_dir=pd)
check("bcast: bp survives", len(b2.best_practices.search())>0)

r1 = UnifiedReviewEngine(data_dir=pd)
r1.engine.run_review("daily",[{"type":"test"}],[],[])
r2 = UnifiedReviewEngine(data_dir=pd)
check("review: survives reload", r2.engine.get_stats()["total_reviews"]>0)

# ── SUMMARY ──
print("\n" + "=" * 50)
print(f"🧪 RESULTS: {passed} ✅  {failed} ❌  ({100*passed//(passed+failed)}%)")
print("=" * 50)

shutil.rmtree(tmpdir, ignore_errors=True)
sys.exit(0 if failed == 0 else 1)
