"""
CloudEventBus Unit Tests
"""
import json
import sys
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / ".ClawShell"))
from lib.core.eventbus_cloud import CloudEventBus, EventRecord


def test_store_and_query():
    """Test event storage and query"""
    with tempfile.TemporaryDirectory() as tmp:
        bus = CloudEventBus(data_dir=Path(tmp), retention_days=30)

        # Store events
        for i in range(5):
            event = EventRecord(
                event_id=f"test-{i}",
                event_type=f"clawshell.test.type_{i % 2}",
                source="test_runner",
                timestamp=datetime.now().isoformat(),
                payload={"index": i},
            )
            result = bus.store(event)
            assert result == "stored", f"Event {i} should be stored"

        assert bus.get_index_size() == 5

        # Query all
        results = bus.query(limit=10)
        assert len(results) == 5

        # Query by pattern
        type0 = bus.query(pattern="clawshell.test.type_0")
        assert len(type0) == 3  # indices 0,2,4

        # Query by source
        src = bus.query(source="test_runner")
        assert len(src) == 5

        print("✅ test_store_and_query passed")


def test_deduplication():
    """Test event dedup"""
    with tempfile.TemporaryDirectory() as tmp:
        bus = CloudEventBus(data_dir=Path(tmp))

        event = EventRecord(
            event_id="test-dup",
            event_type="clawshell.test.dedup",
            source="test",
            timestamp=datetime.now().isoformat(),
        )
        r1 = bus.store(event)
        r2 = bus.store(event)
        assert r1 == "stored"
        assert r2 == "duplicate"
        assert bus.get_index_size() == 1

        print("✅ test_deduplication passed")


def test_stats():
    """Test event statistics"""
    with tempfile.TemporaryDirectory() as tmp:
        bus = CloudEventBus(data_dir=Path(tmp))

        for t in ["task", "task", "health", "health", "health", "alert"]:
            event = EventRecord(
                event_type=f"clawshell.{t}",
                source="edge_1",
                timestamp=datetime.now().isoformat(),
            )
            bus.store(event)

        stats = bus.stats()
        assert stats["total_events"] == 6
        assert stats["by_type"]["clawshell.health"] == 3
        assert stats["by_type"]["clawshell.task"] == 2
        assert stats["by_source"]["edge_1"] == 6

        print("✅ test_stats passed")


def test_expiry():
    """Test event expiration"""
    with tempfile.TemporaryDirectory() as tmp:
        bus = CloudEventBus(data_dir=Path(tmp), retention_days=0)  # Expire all

        event = EventRecord(
            event_id="test-expire",
            event_type="clawshell.test",
            source="test",
            timestamp=datetime.now().isoformat(),
        )
        bus.store(event)
        assert bus.get_index_size() == 1

        bus._clean_expired()
        assert bus.get_index_size() == 0

        print("✅ test_expiry passed")


def test_pattern_matching():
    """Test wildcard pattern matching"""
    with tempfile.TemporaryDirectory() as tmp:
        bus = CloudEventBus(data_dir=Path(tmp))

        types = [
            "clawshell.task.created",
            "clawshell.task.completed",
            "clawshell.health.report",
            "clawshell.alert.triggered",
            "hermes.insight.generated",
        ]
        for t in types:
            bus.store(EventRecord(event_type=t, source="test", timestamp=datetime.now().isoformat()))

        # Wildcard
        assert len(bus.query(pattern="clawshell.task.*")) == 2
        assert len(bus.query(pattern="clawshell.*")) == 4
        assert len(bus.query(pattern="*.insight.*")) == 1

        print("✅ test_pattern_matching passed")


if __name__ == "__main__":
    test_store_and_query()
    test_deduplication()
    test_stats()
    test_expiry()
    test_pattern_matching()
    print("\n🎉 All CloudEventBus tests passed!")
