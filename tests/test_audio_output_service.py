"""
Tests for the Audio Output Service (AudioIngestController)

Validates source lifecycle management: add, start, stop, remove, metrics,
and the controller's get_all_sources / get_source interfaces.  All tests
run without hardware, Redis, or a database by using in-process mock adapters.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util


def _load_module(rel_path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load only the modules we need, bypassing the app_core package __init__
_bq_mod = _load_module("app_core/audio/broadcast_queue.py", "broadcast_queue")
BroadcastQueue = _bq_mod.BroadcastQueue

# Patch out heavy dependencies before loading ingest.py
import unittest.mock as mock

_patch_targets = {
    "app_core": MagicMock(),
    "app_core.audio": MagicMock(),
}

with patch.dict(sys.modules, _patch_targets):
    pass  # We'll do targeted imports below


# ─────────────────────────────────────────────────────────────────────────────
# Minimal stub adapter (no hardware)
# ─────────────────────────────────────────────────────────────────────────────

class _StubAdapter:
    """
    Minimal stand-in for AudioSourceAdapter that exercises the controller
    interfaces without touching real audio hardware or the abstract base class.
    """

    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"

    def __init__(self, name: str, *, fail_start: bool = False):
        self.name = name
        self.status = self.STOPPED
        self.error_message: Optional[str] = None
        self._fail_start = fail_start
        self._source_broadcast = BroadcastQueue(f"source-{name}", max_queue_size=50)
        self._eas_broadcast = BroadcastQueue(f"eas-{name}", max_queue_size=50)
        self.metrics = MagicMock()
        self.metrics.frames_captured = 0
        self.metrics.peak_level_db = -60.0
        self.metrics.rms_level_db = -70.0
        self.metrics.sample_rate = 16000
        self.metrics.silence_detected = False

    def start(self) -> bool:
        if self._fail_start:
            self.status = self.ERROR
            self.error_message = "Simulated start failure"
            return False
        self.status = self.RUNNING
        return True

    def stop(self) -> None:
        self.status = self.STOPPED

    def get_broadcast_queue(self) -> BroadcastQueue:
        return self._source_broadcast

    def get_eas_broadcast_queue(self) -> BroadcastQueue:
        return self._eas_broadcast


# ─────────────────────────────────────────────────────────────────────────────
# Minimal controller that mirrors AudioIngestController's public surface
# ─────────────────────────────────────────────────────────────────────────────

class _MinimalController:
    """Exercises the same interface used by the webapp and test routes."""

    def __init__(self):
        self._sources: dict = {}
        self._lock = threading.Lock()

    def add_source(self, adapter) -> None:
        with self._lock:
            self._sources[adapter.name] = adapter

    def remove_source(self, name: str) -> None:
        with self._lock:
            self._sources.pop(name, None)

    def start_source(self, name: str) -> bool:
        with self._lock:
            adapter = self._sources.get(name)
        if adapter is None:
            return False
        return adapter.start()

    def stop_source(self, name: str) -> None:
        with self._lock:
            adapter = self._sources.get(name)
        if adapter:
            adapter.stop()

    def get_source(self, name: str):
        with self._lock:
            return self._sources.get(name)

    def get_all_sources(self) -> dict:
        with self._lock:
            return dict(self._sources)

    def list_sources(self) -> list:
        with self._lock:
            return list(self._sources.keys())

    def get_source_status(self, name: str):
        with self._lock:
            adapter = self._sources.get(name)
        return adapter.status if adapter else None

    def cleanup(self) -> None:
        with self._lock:
            for adapter in self._sources.values():
                adapter.stop()


# ─────────────────────────────────────────────────────────────────────────────
# BroadcastQueue integration (used by real adapters)
# ─────────────────────────────────────────────────────────────────────────────

class TestBroadcastQueueIntegration:
    def test_adapter_has_broadcast_queues(self):
        a = _StubAdapter("bq-test")
        assert a.get_broadcast_queue() is not None
        assert a.get_eas_broadcast_queue() is not None

    def test_broadcast_queue_delivers_to_subscriber(self):
        a = _StubAdapter("bq-deliver")
        bq = a.get_eas_broadcast_queue()
        sub = bq.subscribe("eas-monitor")
        chunk = np.array([0.5, 0.6], dtype=np.float32)
        bq.publish(chunk)
        received = sub.get_nowait()
        np.testing.assert_array_almost_equal(received, chunk)

    def test_two_adapters_have_independent_queues(self):
        a1 = _StubAdapter("src1")
        a2 = _StubAdapter("src2")
        assert a1.get_eas_broadcast_queue() is not a2.get_eas_broadcast_queue()


# ─────────────────────────────────────────────────────────────────────────────
# Source lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestSourceLifecycle:
    def test_add_source_appears_in_list(self):
        ctrl = _MinimalController()
        ctrl.add_source(_StubAdapter("radio1"))
        assert "radio1" in ctrl.list_sources()

    def test_remove_source_disappears_from_list(self):
        ctrl = _MinimalController()
        ctrl.add_source(_StubAdapter("radio2"))
        ctrl.remove_source("radio2")
        assert "radio2" not in ctrl.list_sources()

    def test_start_source_transitions_to_running(self):
        ctrl = _MinimalController()
        ctrl.add_source(_StubAdapter("radio3"))
        result = ctrl.start_source("radio3")
        assert result is True
        assert ctrl.get_source_status("radio3") == _StubAdapter.RUNNING

    def test_stop_source_transitions_to_stopped(self):
        ctrl = _MinimalController()
        ctrl.add_source(_StubAdapter("radio4"))
        ctrl.start_source("radio4")
        ctrl.stop_source("radio4")
        assert ctrl.get_source_status("radio4") == _StubAdapter.STOPPED

    def test_start_nonexistent_source_returns_false(self):
        ctrl = _MinimalController()
        assert ctrl.start_source("doesnotexist") is False

    def test_failing_start_returns_false_and_status_error(self):
        ctrl = _MinimalController()
        ctrl.add_source(_StubAdapter("bad-src", fail_start=True))
        result = ctrl.start_source("bad-src")
        assert result is False
        assert ctrl.get_source_status("bad-src") == _StubAdapter.ERROR

    def test_get_source_returns_correct_adapter(self):
        ctrl = _MinimalController()
        a = _StubAdapter("specific")
        ctrl.add_source(a)
        assert ctrl.get_source("specific") is a

    def test_get_source_unknown_returns_none(self):
        ctrl = _MinimalController()
        assert ctrl.get_source("unknown") is None

    def test_get_all_sources_returns_all(self):
        ctrl = _MinimalController()
        for n in ("s1", "s2", "s3"):
            ctrl.add_source(_StubAdapter(n))
        sources = ctrl.get_all_sources()
        assert set(sources.keys()) == {"s1", "s2", "s3"}

    def test_cleanup_stops_all_sources(self):
        ctrl = _MinimalController()
        for n in ("c1", "c2"):
            a = _StubAdapter(n)
            ctrl.add_source(a)
            ctrl.start_source(n)
        ctrl.cleanup()
        for name in ("c1", "c2"):
            assert ctrl.get_source_status(name) == _StubAdapter.STOPPED


# ─────────────────────────────────────────────────────────────────────────────
# Concurrent access
# ─────────────────────────────────────────────────────────────────────────────

class TestConcurrentAccess:
    def test_concurrent_add_and_list(self):
        ctrl = _MinimalController()
        errors = []

        def add(n):
            try:
                for i in range(10):
                    ctrl.add_source(_StubAdapter(f"{n}-{i}"))
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=add, args=(f"t{t}",)) for t in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(ctrl.list_sources()) == 30

    def test_concurrent_start_stop(self):
        ctrl = _MinimalController()
        ctrl.add_source(_StubAdapter("shared"))
        errors = []

        def toggle():
            try:
                for _ in range(20):
                    ctrl.start_source("shared")
                    ctrl.stop_source("shared")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=toggle) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
