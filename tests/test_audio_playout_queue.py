"""
Tests for the Audio Broadcast / Playout Queue

Validates the BroadcastQueue publish-subscribe mechanism that carries
audio from capture adapters to EAS monitoring, Icecast streaming, and
web streaming consumers.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

def _load_broadcast_queue():
    """Load BroadcastQueue without triggering app_core package-level imports."""
    spec = importlib.util.spec_from_file_location(
        "broadcast_queue",
        ROOT / "app_core" / "audio" / "broadcast_queue.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.BroadcastQueue


BroadcastQueue = _load_broadcast_queue()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _chunk(values=(1.0, 2.0, 3.0)):
    return np.array(values, dtype=np.float32)


# ─────────────────────────────────────────────────────────────────────────────
# Subscribe / Unsubscribe
# ─────────────────────────────────────────────────────────────────────────────

class TestSubscribeUnsubscribe:
    def test_subscribe_returns_queue(self):
        q = BroadcastQueue("test-sub", max_queue_size=10)
        sq = q.subscribe("s1")
        assert sq is not None

    def test_subscribe_same_id_returns_same_queue(self):
        q = BroadcastQueue("test-same", max_queue_size=10)
        sq1 = q.subscribe("s1")
        sq2 = q.subscribe("s1")
        assert sq1 is sq2

    def test_unsubscribe_existing(self):
        q = BroadcastQueue("test-unsub", max_queue_size=10)
        q.subscribe("s1")
        result = q.unsubscribe("s1")
        assert result is True

    def test_unsubscribe_nonexistent(self):
        q = BroadcastQueue("test-unsub-missing", max_queue_size=10)
        result = q.unsubscribe("nobody")
        assert result is False

    def test_after_unsubscribe_subscriber_count_decreases(self):
        q = BroadcastQueue("test-count", max_queue_size=10)
        q.subscribe("s1")
        q.subscribe("s2")
        q.unsubscribe("s1")
        stats = q.get_stats()
        assert stats["subscribers"] == 1

    def test_multiple_subscribers(self):
        q = BroadcastQueue("test-multi", max_queue_size=10)
        for i in range(5):
            q.subscribe(f"sub{i}")
        assert q.get_stats()["subscribers"] == 5


# ─────────────────────────────────────────────────────────────────────────────
# Publish
# ─────────────────────────────────────────────────────────────────────────────

class TestPublish:
    def test_publish_single_subscriber_receives_chunk(self):
        q = BroadcastQueue("pub-single", max_queue_size=10)
        sq = q.subscribe("s1")
        chunk = _chunk()
        q.publish(chunk)
        received = sq.get_nowait()
        np.testing.assert_array_equal(received, chunk)

    def test_publish_returns_delivered_count(self):
        q = BroadcastQueue("pub-count", max_queue_size=10)
        q.subscribe("s1")
        q.subscribe("s2")
        delivered = q.publish(_chunk())
        assert delivered == 2

    def test_publish_no_subscribers_returns_zero(self):
        q = BroadcastQueue("pub-no-subs", max_queue_size=10)
        delivered = q.publish(_chunk())
        assert delivered == 0

    def test_publish_independent_copies(self):
        """Each subscriber must receive its own copy, not a shared reference."""
        q = BroadcastQueue("pub-copies", max_queue_size=10)
        sq1 = q.subscribe("s1")
        sq2 = q.subscribe("s2")
        q.publish(_chunk([1.0, 2.0]))
        r1 = sq1.get_nowait()
        r2 = sq2.get_nowait()
        # Mutate one copy; the other must be unaffected
        r1[0] = 99.0
        assert r2[0] != 99.0

    def test_publish_none_chunk_returns_zero(self):
        q = BroadcastQueue("pub-none", max_queue_size=10)
        q.subscribe("s1")
        delivered = q.publish(None)
        assert delivered == 0

    def test_publish_empty_array_returns_zero(self):
        q = BroadcastQueue("pub-empty", max_queue_size=10)
        q.subscribe("s1")
        delivered = q.publish(np.array([], dtype=np.float32))
        assert delivered == 0

    def test_multiple_chunks_queued_in_order(self):
        q = BroadcastQueue("pub-order", max_queue_size=10)
        sq = q.subscribe("s1")
        for i in range(5):
            q.publish(np.array([float(i)], dtype=np.float32))
        received = [sq.get_nowait()[0] for _ in range(5)]
        assert received == [0.0, 1.0, 2.0, 3.0, 4.0]

    def test_publish_increments_published_chunks_stat(self):
        q = BroadcastQueue("pub-stats", max_queue_size=10)
        q.subscribe("s1")
        for _ in range(7):
            q.publish(_chunk())
        assert q.get_stats()["published_chunks"] == 7


# ─────────────────────────────────────────────────────────────────────────────
# Queue-Full / Drop Behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestQueueFullBehaviour:
    def test_overflow_drops_oldest_chunk(self):
        """When the queue is full, the oldest chunk is dropped so the newest fits."""
        q = BroadcastQueue("overflow", max_queue_size=3)
        sq = q.subscribe("s1")
        for i in range(4):           # 4 chunks into a queue of size 3
            q.publish(np.array([float(i)], dtype=np.float32))
        items = [sq.get_nowait()[0] for _ in range(sq.qsize())]
        # Queue should NOT contain the very first chunk
        assert 0.0 not in items

    def test_drop_counter_increments(self):
        q = BroadcastQueue("drops", max_queue_size=2)
        q.subscribe("s1")
        for _ in range(5):           # fill and overflow repeatedly
            q.publish(_chunk())
        assert q.get_stats()["dropped_chunks"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# Clear Subscriber Queue
# ─────────────────────────────────────────────────────────────────────────────

class TestClearSubscriberQueue:
    def test_clear_removes_all_pending(self):
        q = BroadcastQueue("clear-test", max_queue_size=20)
        sq = q.subscribe("s1")
        for _ in range(5):
            q.publish(_chunk())
        cleared = q.clear_subscriber_queue("s1")
        assert cleared == 5
        assert sq.empty()

    def test_clear_nonexistent_subscriber_returns_zero(self):
        q = BroadcastQueue("clear-missing", max_queue_size=10)
        assert q.clear_subscriber_queue("nobody") == 0


# ─────────────────────────────────────────────────────────────────────────────
# Statistics
# ─────────────────────────────────────────────────────────────────────────────

class TestStats:
    def test_stats_keys_present(self):
        q = BroadcastQueue("stats-keys", max_queue_size=10)
        stats = q.get_stats()
        for key in ("name", "subscribers", "subscriber_ids",
                    "published_chunks", "dropped_chunks",
                    "max_queue_size", "average_utilization"):
            assert key in stats, f"Missing stat key: {key}"

    def test_utilization_zero_with_no_subscribers(self):
        q = BroadcastQueue("util-none", max_queue_size=10)
        assert q.get_average_utilization() == 0.0

    def test_utilization_nonzero_when_queue_has_items(self):
        q = BroadcastQueue("util-items", max_queue_size=10)
        q.subscribe("s1")
        for _ in range(5):
            q.publish(_chunk())
        util = q.get_average_utilization()
        assert util > 0.0

    def test_repr_contains_name(self):
        q = BroadcastQueue("my-queue", max_queue_size=10)
        assert "my-queue" in repr(q)


# ─────────────────────────────────────────────────────────────────────────────
# Thread Safety
# ─────────────────────────────────────────────────────────────────────────────

class TestThreadSafety:
    def test_concurrent_publish_and_subscribe(self):
        """Concurrent producers and a consumer must not raise."""
        q = BroadcastQueue("thread-safe", max_queue_size=1000)
        sq = q.subscribe("consumer")
        errors = []

        def producer(n):
            try:
                for i in range(n):
                    q.publish(np.array([float(i)], dtype=np.float32))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=producer, args=(50,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"

    def test_concurrent_subscribe_unsubscribe(self):
        """Rapid subscribe/unsubscribe from multiple threads must not raise."""
        q = BroadcastQueue("churn", max_queue_size=10)
        errors = []

        def churn(n):
            try:
                for i in range(n):
                    sid = f"sub-{threading.current_thread().ident}-{i}"
                    q.subscribe(sid)
                    q.publish(np.zeros(4, dtype=np.float32))
                    q.unsubscribe(sid)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=churn, args=(20,)) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
